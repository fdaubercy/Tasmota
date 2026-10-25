"""Page web « Build et televersement » : compiler, televerser (COM ou OTA), construire le FS, en serie.

UTILISATION
    python outils_docs/scripts_python/outils_pc/build_web.py [--http 7700] [--local] [--sans-navigateur]
    L'annuaire des outils (port 7600) la lance ; la console affiche le lien (Ctrl+clic) et ouvre la page.
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Les `pio run` sont lances en serie par build_serie.Serie ; ici, seulement le serveur HTTP.

Routes (les POST exigent l'en-tete X-Build: 1 et la meme origine) :
    GET  /           la page (A6 : build_page.PAGE ; a defaut, une page provisoire)
    GET  /envs       {envs: [champs de Env, dont fs_avec_firmware], derniers: derniers choix}
    GET  /execution  {en_cours: bool, numero: dernier numero d'evenement, pause: {env, port, precedent} | null}
                     (numero : la page sait quand le rejeu du flux est fini ; l'annuaire ne lit que en_cours)
    GET  /flux       Server-Sent Events de la serie (rejoues depuis Last-Event-ID ou ?depuis=n ; un numero
                     superieur au dernier de la serie vaut 0 : page restee ouverte sur un outil redemarre)
    GET  /journal    ?env=<env> : texte du journal pio du dernier lancement de cet env
    GET  /sortie     ?env=<env>&octet=n : suite de ce journal a partir de l'octet n, lignes entieres
                     {texte, octet, reste, lancement} (panneau « Sortie » de la page, lu par increments)
    POST /lancer     {lignes: [{env, methode, port, ip}], actions: [...]}   409 = refus (motifs)
    POST /port       {env, port} : ecrit upload_port (409 pendant un lancement ou un build lance ailleurs,
                     400 si invalide)
    POST /arreter    {immediat: bool}
    POST /continuer  {env, choix: continuer | passer} : reponse a la pause « rebranchez la carte » (409 si
                     aucune pause en cours ou si elle attend un autre env, 400 si choix invalide)
"""

import argparse
import atexit
import json
import os
import re
import sys
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import build_envs
import build_serie

PORT_DEFAUT = 7700
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 64 * 1024
MAX_SORTIE = 128 * 1024                                   # octets de journal au plus par reponse de /sortie

PAGE_PROVISOIRE = ("<!doctype html><html lang=fr><meta charset=utf-8><title>Build et téléversement</title>"
                   "<body style='font-family:sans-serif;margin:2em'><h1>Build et téléversement</h1>"
                   "<p>Page en cours d'écriture (action A6). Le serveur répond déjà : /envs, /execution, /flux.</p>")


def page():
    try:
        import build_page                       # A6 : remplace la page provisoire
        return build_page.PAGE
    except ImportError:
        return PAGE_PROVISOIRE


def lit_derniers(dossier):
    try:
        donnees = json.loads((Path(dossier) / "derniers.json").read_text(encoding="utf-8"))
        return donnees if isinstance(donnees, dict) else {}
    except (OSError, ValueError):
        return {}


def ecrit_derniers(dossier, lignes, actions):
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    provisoire = dossier / "derniers.json.tmp"
    provisoire.write_text(json.dumps({"lignes": lignes, "actions": actions}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    os.replace(provisoire, dossier / "derniers.json")


def liste_envs_json(racine, dossier):
    # fs_avec_firmware (annonce « le FS sera aussi flashe ») vient des .ini, pas de la presence de
    # littlefs.bin : post_esp32 le reconstruit a chaque compilation, meme apres une purge (spec, choix 9).
    envs = [asdict(env) for env in build_envs.liste_envs(racine)]
    return {"envs": envs, "derniers": lit_derniers(dossier)}


def journaux_env(dossier, env, depuis):
    """Journaux de `env` ecrits depuis `depuis` (heure epoch du lancement), dans l'ordre ou ils ont ete ecrits.

    Nom exact des journaux de build_serie.Serie._journal : <AAAAMMJJ>-<HHMMSS>-<env>-<action>[-n].log. Un
    simple motif *-<env>-*.log prendrait aussi ceux d'un env dont le nom prolonge celui-ci (x-a / x-a-b).
    Ordre : heure, puis rang de l'action dans build_serie.ORDRE (deux pio run du meme env dans la meme seconde,
    upload puis buildfs, que l'ordre alphabetique inverserait), puis n. Un nouveau journal vient donc toujours
    apres les autres : la position d'un octet dans les journaux mis bout a bout ne bouge pas (sortie_env).
    Aucun lancement depuis le demarrage de l'outil (`depuis` infini) : le dernier journal de CET env.
    """
    if not build_serie.NOM_ENV.fullmatch(env or ""):
        raise ValueError(f"nom d'environnement invalide : {env!r}")
    nom = re.compile(rf"(\d{{8}}-\d{{6}})-{re.escape(env)}-({'|'.join(build_serie.ORDRE)})(?:-(\d+))?\.log")
    trouves = []
    for f in (Path(dossier) / "journaux").glob("*.log"):
        m = nom.fullmatch(f.name)
        if m:
            trouves.append(((m.group(1), build_serie.ORDRE.index(m.group(2)), int(m.group(3) or 1)), f))
    fichiers = [f for _, f in sorted(trouves)]
    if depuis == float("inf"):
        return fichiers[-1:]
    return [f for f in fichiers if f.stat().st_mtime >= depuis]


def journal_env(dossier, env, depuis):
    """Texte des journaux de `env` du dernier lancement (voir journaux_env)."""
    return "".join(f.read_text(encoding="utf-8", errors="replace") for f in journaux_env(dossier, env, depuis))


def sortie_env(dossier, env, depuis, octet, plafond=MAX_SORTIE):
    """Suite de la sortie de pio de `env` (panneau « Sortie » de la page), a partir de l'octet `octet` de ses
    journaux du lancement mis bout a bout : {texte, octet (position suivante), reste (encore a lire)}.

    Seulement des lignes entieres, au plus `plafond` octets par appel : rien de deja servi n'est renvoye, et
    une ligne en cours d'ecriture attend l'appel suivant. Les tailles sont lues une fois par appel : seul le
    dernier journal grandit (un pio a la fois), les precedents sont fermes.
    """
    lu, total = b"", 0
    for f in journaux_env(dossier, env, depuis):
        taille = f.stat().st_size
        if octet < total + taille and len(lu) <= plafond:
            debut = max(0, octet - total)
            with open(f, "rb") as fichier:
                fichier.seek(debut)
                lu += fichier.read(min(taille - debut, plafond + 1 - len(lu)))
        total += taille
    fin = lu[:plafond].rfind(b"\n") + 1
    if not fin and len(lu) > plafond:                     # ligne plus longue que le plafond : servie en morceaux
        fin = plafond
        while fin and lu[fin] & 0xC0 == 0x80:             # sans couper un caractere UTF-8
            fin -= 1
    suivant = octet + fin if octet <= total else octet
    return {"texte": lu[:fin].decode("utf-8", errors="replace"), "octet": suivant, "reste": suivant < total}


def ligne_de(donnee):
    if not isinstance(donnee, dict):
        raise ValueError("ligne attendue sous forme d'objet")
    return build_serie.Ligne(*(str(donnee.get(k) or "") for k in ("env", "methode", "port", "ip")))


def fabrique_gestionnaire(serie, acces, racine, dossier):
    etat = {"debut": float("inf")}                        # heure du dernier lancement accepte (inf : aucun, repli sur le dernier journal)

    def traite_post(chemin, demande):
        if chemin == "/lancer":
            lignes, actions = demande.get("lignes"), demande.get("actions")
            if not isinstance(lignes, list) or not isinstance(actions, list):
                raise ValueError("lignes et actions attendues sous forme de listes")
            objets = [ligne_de(d) for d in lignes]
            actions = [str(a) for a in actions]
            ancien, etat["debut"] = etat["debut"], time.time()
            try:
                serie.lance(objets, actions)              # RuntimeError (409) : motifs de controle
            except RuntimeError:
                etat["debut"] = ancien                    # un refus ne change pas le lancement en cours
                raise
            ecrit_derniers(dossier, [asdict(o) for o in objets], actions)
            return {"ok": True}
        if chemin == "/port":
            if serie.en_cours():
                raise RuntimeError("un lancement est en cours : modifier le port apres")
            builds = serie.builds_en_cours()             # spec 13 bis : refusee aussi pendant un build
            if builds is None:
                raise RuntimeError("détection des builds en cours impossible (PowerShell) : réessayer")
            if builds:
                raise RuntimeError(f"un build est en cours ({', '.join(builds)}) : modifier le port après")
            build_envs.ecrit_port(racine, str(demande.get("env", "")), str(demande.get("port", "")))
            return {"ok": True}
        if chemin == "/arreter":
            serie.arrete(bool(demande.get("immediat")))
            return {"ok": True}
        if chemin == "/continuer":                         # ValueError (400) ou RuntimeError (409)
            serie.reprend(str(demande.get("env") or ""), str(demande.get("choix") or ""))
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

        def _json(self, donnees, statut=200):
            self._envoie(statut, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def _flux(self, depuis):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                while True:
                    evenements = serie.depuis(depuis)
                    for e in evenements:
                        self.wfile.write(f"id: {e['n']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n".encode("utf-8"))
                        depuis = e["n"]
                    if not evenements:
                        self.wfile.write(b": veille\n\n")     # detecte un onglet ferme
                    self.wfile.flush()
            except OSError:
                pass

        def do_GET(self):
            if not acces.controle(self):
                return
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            try:
                if url.path == "/":
                    self._envoie(200, page().encode("utf-8"), "text/html; charset=utf-8")
                elif url.path == "/envs":
                    self._json(liste_envs_json(racine, dossier))
                elif url.path == "/execution":
                    self._json({"en_cours": serie.en_cours(), "numero": serie.numero, "pause": serie.pause_en_cours()})
                elif url.path == "/flux":
                    depuis = self.headers.get("Last-Event-ID") or params.get("depuis", ["0"])[0]
                    depuis = int(depuis) if str(depuis).isdigit() else 0
                    if depuis > serie.numero:             # onglet reste ouvert sur un outil redemarre : nouvelle
                        depuis = 0                        # numerotation repartie de 1, rejouer depuis le debut
                    self._flux(depuis)
                elif url.path == "/journal":
                    self._envoie(200, journal_env(dossier, params.get("env", [""])[0], etat["debut"]).encode("utf-8"))
                elif url.path == "/sortie":
                    octet = params.get("octet", ["0"])[0]
                    if not octet.isdigit():
                        raise ValueError(f"octet invalide : {octet!r}")
                    debut = etat["debut"]
                    reponse = sortie_env(dossier, params.get("env", [""])[0], debut, int(octet))
                    self._json(dict(reponse, lancement=repr(debut)))   # change a chaque lancement : la page repart de 0
                else:
                    self._envoie(404, b"introuvable")
            except ValueError as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))

        def do_POST(self):
            if not acces.controle(self):
                return
            if self.headers.get("X-Build") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if longueur > MAX_CORPS:
                    self.close_connection = True              # corps non lu : la connexion ne doit pas resservir
                    self._envoie(413, "corps trop gros (64 Ko au plus)".encode("utf-8"))
                    return
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                self._json(traite_post(urlsplit(self.path).path, demande))
            except LookupError:
                self._envoie(404, b"introuvable")
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except RuntimeError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))

    return Gestionnaire


def arrete_serie(serie, attente=15.0):
    """A la fermeture : un lancement en cours est arrete, arbre du fils pio compris (pas de pio orphelin).

    Un envoi vers une carte (upload ou uploadfs par cable en phase Televersement, envoi OTA) va d'abord
    a son terme : le couper laisserait une carte a moitie flashee (anti-objectif de la spec). Plus aucun
    env n'est lance ; une fois l'envoi fini, le reste est tue. Un second Ctrl+C force l'arret.
    """
    if not serie.en_cours():
        return
    serie.arrete(immediat=False)                          # aucun env suivant
    signale = False
    try:
        while serie.en_cours() and serie.envoi_en_cours():
            if not signale:
                print("envoi en cours vers une carte : attente de sa fin avant d'arreter "
                      "(Ctrl+C de nouveau pour forcer)...", flush=True)
                signale = True
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("arret force : l'envoi en cours est coupe (carte peut-etre a moitie flashee)", flush=True)
    serie.arrete(immediat=True)
    limite = time.monotonic() + attente
    while serie.en_cours() and time.monotonic() < limite:
        time.sleep(0.1)


def principal():
    options = argparse.ArgumentParser(description="Page web de build et televersement des cartes Tasmota.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()

    # Nom de la fiche de presence, en litteral : identique a nom_acces de l'outil « build »
    # (annuaire_registre.py), sinon la tuile ne retrouve pas l'outil ; test_annuaire le verifie sur cette ligne.
    acces = acces_web.Acces(args.http, args.local, "Build et téléversement")
    dossier = acces_web.dossier_donnees() / "build"
    serie = build_serie.Serie(DEPOT, dossier)
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(serie, acces, DEPOT, dossier))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    atexit.register(arrete_serie, serie)
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (un lancement en cours est alors arrete, arbre pio compris ; un envoi vers "
          "une carte va d'abord a son terme).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
        if serie.en_cours():
            print("lancement en cours : arret (un envoi vers une carte va a son terme)...", flush=True)
            arrete_serie(serie)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
