"""Etiquettes QR code (page web, port 7970) : QR code d'identite de chaque carte, apercu, verdict, ecriture au depot.

UTILISATION
    python outils_docs/scripts_python/outils_pc/etiquettes_qr_web.py [--http 7970] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Plan tasks/plans/etiquettes-qrcode.md (A4) ; modele (A2) et ecriture (A3). Rien n'est ecrit sans « Ecrire dans le depot ».

Routes (les POST exigent l'en-tete X-Etiquettes-QR: 1 et la meme origine ; JSON) :
    GET  /                 la page (etiquettes_qr_page.PAGE)
    GET  /lib.js           outils_docs/etiquettes_qr/lib/qr-code-styling.min.js
    GET  /cartes           {cartes: [{nom, lieu, puce, esp32, regle, page}], lieux}
    GET  /gabarit          {gabarit}
    GET  /reglage?env=     {reglage, regle (surcharge presente), page (page /qrcode installee), esp32}
    GET  /persist?env=     {arbre} : cles du persist proposees (jamais un secret ; vide pour une carte sans persist)
    GET  /images           {images} : noms du dossier outils_docs/etiquettes_qr/images/
    GET  /suivi            {suivi: {env: {a_reimprimer, a_regenerer}}} : badges de la liste, sans interroger les cartes
    GET  /etat?env=        {a_reimprimer, a_regenerer, carte} : la carte est lue (etiquettes_qr_suivi.etats, 2 s au plus)
    POST /apercu           {env, reglage} -> {texte, lignes, avertissements, verdict, image, correction, erreurs}
    POST /diff             {env, reglage, page_carte} -> {fichiers: [{chemin, avant, apres, diff, ajouts, retraits}], empreinte, signaux}
    POST /ecrire           {env, reglage, page_carte, empreinte} -> {ecrits} ; 409 si build ou empreinte perimee
    POST /gabarit/diff     {gabarit} -> {fichiers, empreinte} ;  POST /gabarit/ecrire {gabarit, empreinte} -> {ecrits}
    POST /impression       {impressions: [{env, reglage}], taille_mm} -> {notees} (texte resolu ici, seule son empreinte est gardee)
    POST /impression/annule {env} -> {ok}
Refus : 400 (saisie), 403 (anti-CSRF), 404 (env inconnu), 409 (build, empreinte), 500 (inattendu, avec le message).
"""

import argparse
import difflib
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import build_envs
import etiquettes_qr_ecriture as eqe
import etiquettes_qr_modele as modele
import etiquettes_qr_suivi as suivi_qr
import etiquettes_qr_verdict as verdict
import lieux

PORT_DEFAUT = 7970
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 256 * 1024
CACHE_S = 30                                     # liste_envs coute plusieurs secondes : relue au plus toutes les 30 s
ENTETE = "X-Etiquettes-QR"


def builds_en_cours_defaut():
    import build_serie                          # meme detection que la page build (garde_build du depot)
    return build_serie.builds_en_cours_defaut()


def avec_diffs(prevu):
    for f in prevu["fichiers"]:
        lignes = list(difflib.unified_diff((f["avant"] or "").splitlines(), (f["apres"] or "").splitlines(),
                                           "a/" + f["chemin"], "b/" + f["chemin"], lineterm=""))
        f["diff"] = "\n".join(lignes)
        f["ajouts"] = sum(1 for l in lignes[2:] if l.startswith("+"))
        f["retraits"] = sum(1 for l in lignes[2:] if l.startswith("-"))
    return prevu


def apercu(racine, env, reglage, envs):
    """Texte lu, verdict et image d'un reglage non encore ecrit ; erreurs de validation rendues, pas levees."""
    erreurs = modele.valide_reglage(reglage, racine)
    if erreurs:
        return {"erreurs": erreurs}
    resolu = modele.resout_avec(reglage, modele.champs_standards(racine, env, envs), modele.persist_de(racine, env))
    f = modele.fichier_carte(racine, reglage, resolu)
    return {**resolu, "image": f["image"], "correction": f["correction"], "erreurs": [],
            "verdict": verdict.verdict(resolu["texte"], reglage.get("taille_mm", 25), f["correction"])}


def fabrique_gestionnaire(acces, racine, builds_en_cours):
    verrou = threading.Lock()
    cache = {"t": 0.0, "envs": []}
    precedentes = {}       # shortcut: notes remplacees gardees en memoire ; perdues si l'outil redemarre avant l'annulation

    def envs():
        if time.monotonic() - cache["t"] > CACHE_S:
            cache["envs"], cache["t"] = build_envs.liste_envs(racine), time.monotonic()
        return cache["envs"]

    def cartes():
        return [e for e in envs() if e.famille == "cartes"]

    def env_ok(valeur):
        if not isinstance(valeur, str) or valeur not in {e.nom for e in cartes()}:
            raise LookupError(f"carte inconnue : {valeur!r}")
        return valeur

    def esp32(env):
        return env in eqe.age._envs(eqe.fbi.lit_sections(racine))

    def reglage_de(demande, cle="reglage"):
        r = demande.get(cle)
        if not isinstance(r, dict):
            raise ValueError(f"{cle} : objet attendu")
        return r

    def page_installee(env):
        auto = Path(racine) / eqe.fbe.dossier_carte(env) / "autoexec.be"
        return auto.is_file() and eqe.LIGNE_AUTOEXEC in auto.read_text(encoding="utf-8", errors="replace")

    def liste_cartes():
        ini = eqe.fbi.lit_sections(racine)
        e32 = set(eqe.age._envs(ini))
        return [{"nom": e.nom, "lieu": lieux.lieu(e.nom), "puce": lieux.puce(e.nom), "esp32": e.nom in e32,
                 "regle": modele.chemin_surcharge(racine, e.nom).is_file(), "page": e.nom in e32 and page_installee(e.nom)}
                for e in cartes()]

    def traite_get(chemin, params):
        un = lambda k: params.get(k, [""])[-1]
        if chemin == "/cartes":
            return {"cartes": liste_cartes(), **lieux.pour_page()}
        if chemin == "/gabarit":
            return {"gabarit": modele.charge_gabarit(racine)}
        if chemin == "/reglage":
            env = env_ok(un("env"))
            champs = modele.champs_standards(racine, env, envs())
            return {"reglage": modele.charge_reglage(racine, env), "regle": modele.chemin_surcharge(racine, env).is_file(),
                    "page": esp32(env) and page_installee(env), "esp32": esp32(env),
                    # champs proposes a l'ajout : le range extender seulement s'il est actif sur la carte
                    "champs": [c for c in modele.CHAMPS if c != "range_extender" or champs.get(c)]}
        if chemin == "/suivi":                       # badges de la liste : local, la carte n'est pas interrogee
            suivi = {}
            for e in cartes():
                try:
                    s = suivi_qr.etats(racine, e.nom, envs=envs(), interroger=False)
                except (LookupError, ValueError, OSError):
                    continue                         # carte illisible : pas de badge, la liste reste utilisable
                suivi[e.nom] = {k: s[k] for k in ("a_reimprimer", "a_regenerer")}
            return {"suivi": suivi}
        if chemin == "/etat":                        # une carte : lit sa page /qrcode (2 s au plus)
            return suivi_qr.etats(racine, env_ok(un("env")), envs=envs())
        if chemin == "/persist":
            return {"arbre": modele.arbre_persist(modele.persist_de(racine, env_ok(un("env"))))}
        if chemin == "/images":
            d = Path(racine) / modele.DOSSIER / "images"
            return {"images": sorted(p.name for p in d.iterdir() if p.suffix.lower() in modele.TYPES_IMAGE) if d.is_dir() else []}
        raise LookupError(chemin)

    def traite_post(chemin, demande):
        if chemin == "/apercu":
            return apercu(racine, env_ok(demande.get("env")), reglage_de(demande), envs())
        if chemin in ("/diff", "/ecrire"):
            env, reglage, page = env_ok(demande.get("env")), reglage_de(demande), demande.get("page_carte")
            if not isinstance(page, bool):
                raise ValueError("page_carte : vrai ou faux attendu")
            with verrou:
                if chemin == "/diff":
                    return avec_diffs(eqe.prevoit(racine, env, reglage, page))
                if not isinstance(demande.get("empreinte"), str):
                    raise ValueError("empreinte : chaîne attendue")
                return {"ecrits": eqe.ecrit(racine, env, reglage, page, demande["empreinte"], builds_en_cours)}
        if chemin == "/gabarit/diff":
            return avec_diffs(eqe.prevoit_gabarit(racine, reglage_de(demande, "gabarit")))
        if chemin == "/gabarit/ecrire":
            if not isinstance(demande.get("empreinte"), str):
                raise ValueError("empreinte : chaîne attendue")
            with verrou:
                return {"ecrits": eqe.ecrit_gabarit(racine, reglage_de(demande, "gabarit"), demande["empreinte"], builds_en_cours)}
        if chemin == "/impression":
            liste, taille = demande.get("impressions"), demande.get("taille_mm")
            if not isinstance(liste, list) or not liste or isinstance(taille, bool) or not isinstance(taille, (int, float)):
                raise ValueError("impressions : liste non vide et taille_mm attendues")
            textes = {}
            for i in liste:
                if not isinstance(i, dict):
                    raise ValueError("impressions : objets {env, reglage} attendus")
                env = env_ok(i.get("env"))
                a = apercu(racine, env, reglage_de(i), envs())
                if a["erreurs"]:
                    raise ValueError(f"{env} : " + " ; ".join(a["erreurs"]))
                textes[env] = a["texte"]
            with verrou:
                precedentes.update(eqe.note_impression(racine, textes, taille))
            return {"notees": sorted(textes)}
        if chemin == "/impression/annule":
            env = env_ok(demande.get("env"))
            with verrou:                                 # remet la note d'une impression anterieure, s'il y en avait une
                eqe.annule_impression(racine, env, precedentes.pop(env, None))
            return {"ok": True}
        raise LookupError(chemin)

    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees):
            self._envoie(200, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def _erreur(self, erreur):
            if isinstance(erreur, (KeyError, IndexError)):     # LookupError, mais un bogue : pas un « introuvable »
                statut = 500
            elif isinstance(erreur, LookupError):
                statut = 404
            elif isinstance(erreur, (ValueError, TypeError, RecursionError)):
                statut = 400
            elif isinstance(erreur, RuntimeError):
                statut = 409
            else:
                statut = 500
            message = str(erreur) or type(erreur).__name__
            self._envoie(statut, (f"erreur inattendue : {type(erreur).__name__} : {message}" if statut == 500 else message).encode("utf-8"))

        def do_GET(self):
            if not acces.controle(self):
                return
            url = urlsplit(self.path)
            try:
                if url.path == "/":
                    import etiquettes_qr_page
                    self._envoie(200, etiquettes_qr_page.PAGE.encode("utf-8"), "text/html; charset=utf-8")
                elif url.path == "/lib.js":
                    lib = Path(racine) / modele.DOSSIER / "lib" / "qr-code-styling.min.js"
                    if not lib.is_file():
                        raise LookupError("bibliothèque qr-code-styling absente du dépôt")
                    self._envoie(200, lib.read_bytes(), "application/javascript; charset=utf-8")
                else:
                    self._json(traite_get(url.path, parse_qs(url.query)))
            except Exception as erreur:
                self._erreur(erreur)

        def do_POST(self):
            if not acces.controle(self):
                return
            if self.headers.get(ENTETE) != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if not 0 <= longueur <= MAX_CORPS:        # negatif : read(-1) lirait jusqu'a la fermeture
                    self.close_connection = True
                    self._envoie(400, f"Content-Length hors 0..{MAX_CORPS}".encode("utf-8"))
                    return
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                self._json(traite_post(urlsplit(self.path).path, demande))
            except Exception as erreur:
                self._erreur(erreur)

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Etiquettes QR code : QR code d'identite des cartes, impression, page /qrcode.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Étiquettes QR code")
    try:
        ThreadingHTTPServer.request_queue_size = 128
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT, builds_en_cours_defaut))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit sans « Ecrire dans le depot »).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
