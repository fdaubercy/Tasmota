"""Atelier des ecrans (page web, port 7960) : ecrans HASPmota / LVGL des cartes, d'apres une description neutre.

UTILISATION
    python outils_docs/scripts_python/outils_pc/atelier_ecrans_web.py [--http 7960] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Spec : docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md (§ 5.5 page, § 5.8 securite) ; plan atelier-ecrans A6.
Ecritures : /ecrire, /ecran/changer, /polices/importer, /remarques*, /display/enregistrer, /display/notes (refus pendant un build). Env = une carte du cenv (« Mes cartes »),
jamais un chemin ; adresse de la carte = celle du cenv / du maitre (atelier_graphiques_series._adresses), jamais celle
de la requete (SSRF).

Routes (les POST exigent l'en-tete X-Atelier-Ecrans: 1 et la meme origine ; corps JSON) :
    GET  /             la page (atelier_ecrans_page.PAGE)
    GET  /cartes       {cartes: [{nom, lieu, ip, ecran (cle du catalogue | null), interface (custom_interface_ecran | null),
                       description (ecran.json present)}], lieux}
    GET  /catalogue    outils_docs/schemas/catalogue_ecran.json tel quel
    GET  /description  ?env= : {description | null, empreinte (sha256 des octets du fichier) | null, erreurs, ecran, build}
    GET  /valeurs      ?env=[&simule=1] : {simule, motif, sensor (StatusSNS de Status 10) | null, modele {cle: exemple}} ;
                       carte muette : simule true, et les lectures des SILENCE s suivantes n'attendent pas la carte
    GET  /police       ?nom= : .ttf d'une police `source: sd` du catalogue (font/ttf), cherche par son nom de fichier
                       du catalogue dans data/*/*/ ; rien d'autre (404)
    POST /apercu       {env, description} -> {erreurs, fichiers: [{nom, chemin, contenu, diff, ajouts, retraits}]} ;
                       pages.jsonl, ecranLvgl.be (dossier de la carte), ecran.json ; diff avec le depot ; rien n'est ecrit
    POST /capture      {env} -> 200 image/bmp (octets de lv.screenshot()) ou 409 texte (refus : carte injoignable, sans
                       LVGL, fichier tronque, capture deja en cours)
    POST /diff         {env, description} -> {fichiers (comme /apercu, seulement ceux qui changent), empreinte}
    POST /ecrire       {env, description, empreinte, empreinte_description[, remarques]} -> {ecrits, empreinte_description, build
                       [, remarques]} ; `remarques` = identifiants appliques sur le canevas, marques « appliquee » apres l'ecriture
                       (409 : build en cours, fichiers ou ecran.json changes depuis le diff ou le chargement)
    POST /ecran/diff   {env, ecran, description} -> {description a l'echelle, avertissements, refus, fichiers, empreinte}
    POST /ecran/changer {env, ecran, description, empreinte, empreinte_description} -> {ecrits, avertissements, build}
    POST /polices/analyse  {nom, contenu (base64)} -> {nom, fichier, famille, licence, url_licence, libre, manque, poids, sites}
    POST /polices/importer {env, nom, contenu, licence_confirmee} -> {ecrits, analyse} (police dans le dossier de la carte,
                       licence hors de ce dossier, catalogue regenere) ; corps jusqu'a MAX_POLICE
    GET  /remarques    ?env= : {remarques (remarques.json), traitement (etat)} ; GET /remarques/etat : etat du traitement
    POST /remarques    {env, action: epingle|repond|refuse, ...} -> {remarques} (ecrit remarques.json, atelier_ecrans_remarques)
    POST /remarques/appliquer {env, id, description} -> {description modifiee | null, erreurs, remarques} (rien n'est ecrit)
    POST /remarques/traiter   {env} -> etat ; claude -p en lecture seule, depuis ce PC seulement (403 sinon), 409 si en cours
  Onglet « display.ini » (A15, atelier_ecrans_display_fichiers ; source = carte | perso | amont, nom = env, nom de la
  bibliotheque sans .ini, ou nom du fichier amont) :
    GET  /display/liste      {fichiers: [{source, nom, rel, envs, pilote, largeur, hauteur, bpp, bus, tactile}]}
    GET  /display/reference  outils_docs/schemas/display_ini_parametres.json tel quel
    GET  /display/lire       ?source=&nom= : {texte, empreinte, analyse, notes, modifiable...} (404 si absent)
    POST /display/analyse    {texte} -> analyse (atelier_ecrans_display.analyse) ; rien n'est ecrit
    POST /display/inserer    {texte, ligne} -> {texte, analyse} : ligne `:X` de la reference ajoutee a sa place
    POST /display/diff       {nom, texte} -> {rel, diff, ajouts, retraits, change, empreinte} (bibliotheque seulement)
    POST /display/enregistrer {nom, texte, empreinte} -> {ecrits} (409 : build en cours, fichier change depuis le diff)
    POST /display/notes      {nom, carte?, texte} -> {notes} : observation datee dans <nom>.notes.md
Refus : 400 (env inconnu, saisie, Content-Length hors 0..MAX_CORPS ou MAX_POLICE, JSON trop imbrique), 403 (en-tete, origine, jeton),
404 (route, police), 409 (capture refusee), 500 (inattendu, avec le message).
"""

import argparse
import base64
import binascii
import difflib
import json
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import atelier_ecrans_capture as aec
import atelier_ecrans_catalogue as cat
import atelier_ecrans_description as aed
import atelier_ecrans_display as adi
import atelier_ecrans_display_fichiers as adf
import atelier_ecrans_ecran as aecr
import atelier_ecrans_ecriture as aee
import atelier_ecrans_haspmota as ah
import atelier_ecrans_lvgl as al
import atelier_ecrans_polices as aep
import atelier_ecrans_remarques as aer
import atelier_graphiques_series as ags
import build_ota_http
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import lieux

PORT_DEFAUT = 7960
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 256 * 1024                  # ecran.json des debits : 24 Ko
MAX_POLICE = aep.TAILLE_MAX * 4 // 3 + 64 * 1024    # police .ttf en base64 dans le JSON (routes /polices/*)
ENTETE = "X-Atelier-Ecrans"
DELAI = 4
SILENCE = 30                            # s sans rappeler une carte muette (la page relit les valeurs en boucle)
INTERFACE = "custom_interface_ecran"


def noms_cartes(racine):
    return [e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "cartes"]


def env_atelier(racine, env):
    if not isinstance(env, str) or env not in noms_cartes(racine):
        raise ValueError(f"env inconnu (cartes du cenv seulement) : {env!r}")
    return env


def _interface(ini, env):
    section = ini.definie_dans(env, INTERFACE)
    morceaux = ini.sections[section][INTERFACE].morceaux if section else []
    return (morceaux[0][1].strip() or None) if morceaux else None


def cartes(racine):
    ini, ecrans, ips = fbi.lit_sections(racine), cat.ecrans_des_envs(racine), ags._adresses(racine)
    return [{"nom": n, "lieu": lieux.lieu(n), "ip": ips.get(n, ""), "ecran": ecrans.get(n), "interface": _interface(ini, n),
             "description": aed.chemin(racine, n).is_file()} for n in noms_cartes(racine)]


def _valide(d, catalogue):
    try:
        return aed.valide(d, catalogue)
    except (AttributeError, TypeError, KeyError, ValueError) as e:     # description de forme inattendue
        return [f"description mal formee : {type(e).__name__} : {e}"]


def description_de(racine, env):
    ecran = cat.ecrans_des_envs(racine).get(env)
    try:
        octets = aed.chemin(racine, env).read_bytes()
    except FileNotFoundError:
        return {"description": None, "empreinte": None, "erreurs": [], "ecran": ecran}
    try:
        d = json.loads(octets.decode("utf-8"))
        if not isinstance(d, dict):
            raise ValueError("objet JSON attendu")
    except (ValueError, RecursionError) as e:
        return {"description": None, "empreinte": aed.empreinte(octets), "erreurs": [f"ecran.json illisible : {e}"], "ecran": ecran}
    return {"description": d, "empreinte": aed.empreinte(octets), "erreurs": _valide(d, cat.charge(racine)), "ecran": ecran}


def diff_fichier(nom, rel, avant, contenu):
    """Entree de fichier pour la page : contenu, diff unifie avec le depot, lignes ajoutees et retirees."""
    lignes = list(difflib.unified_diff((avant or "").splitlines(), (contenu or "").splitlines(), "a/" + rel, "b/" + rel, lineterm=""))
    return {"nom": nom, "chemin": rel, "contenu": contenu, "diff": "\n".join(lignes),
            "ajouts": sum(1 for l in lignes[2:] if l.startswith("+")), "retraits": sum(1 for l in lignes[2:] if l.startswith("-"))}


def _fichiers_prevus(prevus):
    return [diff_fichier(f["rel"].rsplit("/", 1)[-1], f["rel"], f["avant"], f["apres"]) for f in prevus]


def apercu(racine, env, desc):
    if not isinstance(desc, dict):
        raise ValueError("description : objet attendu")
    erreurs = _valide(desc, cat.charge(racine))
    if erreurs:
        return {"erreurs": erreurs, "fichiers": []}
    dossier = fbe.dossier_carte(env)
    try:
        generes = [("pages.jsonl", f"{dossier}/pages.jsonl", ah.genere(desc)),
                   ("ecranLvgl.be", f"{dossier}/ecranLvgl.be", al.genere(desc)),
                   ("ecran.json", f"{aed.DOSSIER}/{env}/ecran.json", aed.texte(desc))]
    except ValueError as e:                     # ce que le generateur LVGL ne sait pas ecrire en Berry
        return {"erreurs": [str(e)], "fichiers": []}
    fichiers = []
    for nom, rel, contenu in generes:
        try:
            avant = (Path(racine) / rel).read_text(encoding="utf-8")
        except FileNotFoundError:
            avant = ""
        fichiers.append(diff_fichier(nom, rel, avant, contenu))
    return {"erreurs": [], "fichiers": fichiers}


def valeurs(racine, env, simule, get, muettes):
    d = aed.charge(racine, env) or {}
    modele = d.get("modele")
    modele = {m.get("cle"): m.get("exemple") for m in modele if isinstance(m, dict)} if isinstance(modele, list) else {}
    ip = ags._adresses(racine).get(env, "")
    if simule:
        motif = "valeurs simulees demandees"
    elif not ip:
        motif = "adresse de la carte inconnue"
    elif time.monotonic() - muettes.get(env, float("-inf")) < SILENCE:
        motif = "carte muette a la derniere lecture"
    else:
        try:
            sns = json.loads(get(ip, "/cm?cmnd=" + urllib.parse.quote("Status 10", safe=""), DELAI).decode("utf-8", "replace"))
            sns = sns.get("StatusSNS") if isinstance(sns, dict) else None
            if not isinstance(sns, dict):
                raise ValueError("StatusSNS absent")
            muettes.pop(env, None)
            return {"simule": False, "motif": "", "sensor": sns, "modele": modele}
        except Exception as e:                  # OSError, HTTPException, JSON tronque : meme repli
            muettes[env] = time.monotonic()
            motif = f"carte injoignable ({e})"
    return {"simule": True, "motif": motif, "sensor": None, "modele": modele}


def police(racine, nom):
    """Octets du .ttf de la police `nom` du catalogue ; le fichier vient du catalogue, jamais de la requete."""
    for p in cat.charge(racine)["polices"]:
        if p.get("source") == "sd" and p.get("nom") == nom and p.get("fichier"):
            for f in sorted(Path(racine).glob("data/*/*/*.ttf")):
                if f.name == p["fichier"]:
                    return f.read_bytes()
    raise LookupError(f"police inconnue du catalogue : {nom!r}")


def depuis_ce_pc(handler):
    return acces_web.est_local(handler.client_address)


def _octets_police(demande):
    try:
        return base64.b64decode(demande.get("contenu") or "", validate=True)
    except (binascii.Error, TypeError) as e:
        raise ValueError(f"contenu de la police : base64 attendu ({e})")


def _builds_defaut():
    import build_serie
    return build_serie.builds_en_cours_defaut()


def fabrique_gestionnaire(acces, racine, get=None, traitement=None, builds_en_cours=None):
    get = get or build_ota_http._get
    builds_en_cours = builds_en_cours or _builds_defaut
    traitement = traitement or aer.Traitement(racine)
    muettes = {}                                # env -> instant du dernier echec de lecture
    une_capture = threading.Lock()

    def capture(env):
        ip = ags._adresses(racine).get(env, "")
        if not ip:
            raise RuntimeError("adresse de la carte inconnue (cenv) : capture impossible")
        if not une_capture.acquire(blocking=False):
            raise RuntimeError("une capture est deja en cours")
        try:
            return aec.capture(ip, get)
        finally:
            une_capture.release()

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

        def _traite(self, action):
            try:
                action()
            except (KeyError, IndexError) as erreur:   # LookupError, mais un bogue : pas un « introuvable »
                self._inattendue(erreur)
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except (ValueError, TypeError, RecursionError) as erreur:     # RecursionError : JSON trop imbrique
                self._envoie(400, (str(erreur) or type(erreur).__name__).encode("utf-8"))
            except RuntimeError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
            except Exception as erreur:
                self._inattendue(erreur)

        def _inattendue(self, erreur):
            self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def do_GET(self):
            if not acces.controle(self):
                return
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            un = lambda k: params.get(k, [""])[0]

            def route():
                if url.path == "/":
                    import atelier_ecrans_page
                    self._envoie(200, atelier_ecrans_page.PAGE.encode("utf-8"), "text/html; charset=utf-8")
                elif url.path == "/cartes":
                    self._json({"cartes": cartes(racine), **lieux.pour_page()})
                elif url.path == "/catalogue":
                    self._json(cat.charge(racine))
                elif url.path == "/description":
                    env = env_atelier(racine, un("env"))
                    self._json({**description_de(racine, env), "build": aee.url_build(racine, env)})
                elif url.path == "/valeurs":
                    self._json(valeurs(racine, env_atelier(racine, un("env")), un("simule") == "1", get, muettes))
                elif url.path == "/remarques":
                    env = env_atelier(racine, un("env"))
                    self._json({"remarques": aer.charge(racine, env), "traitement": traitement.etat()})
                elif url.path == "/remarques/etat":
                    self._json(traitement.etat())
                elif url.path == "/display/liste":
                    self._json({"fichiers": adf.liste(racine)})
                elif url.path == "/display/reference":
                    self._json(adi.charge_reference(racine))
                elif url.path == "/display/lire":
                    self._json(adf.lire(racine, un("source"), un("nom"), adi.charge_reference(racine)))
                elif url.path == "/police":
                    self._envoie(200, police(racine, un("nom")), "font/ttf")
                else:
                    raise LookupError("introuvable")
            self._traite(route)

        def do_POST(self):
            if not acces.controle(self):
                return
            if self.headers.get(ENTETE) != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return

            def route():
                chemin = urlsplit(self.path).path
                limite = MAX_POLICE if chemin.startswith("/polices/") else MAX_CORPS
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if not 0 <= longueur <= limite:               # negatif : read(-1) lirait jusqu'a la fermeture
                    self.close_connection = True              # corps non lu : la connexion ne doit pas resservir
                    raise ValueError(f"Content-Length hors 0..{limite}")
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                if chemin == "/polices/analyse":
                    self._json({**aep.analyse(demande.get("nom"), _octets_police(demande)), "sites": aep.SITES})
                elif chemin == "/polices/importer":
                    env = env_atelier(racine, demande.get("env"))
                    self._json(aep.importe(racine, env, demande.get("nom"), _octets_police(demande),
                                           demande.get("licence_confirmee") is True, builds_en_cours))
                elif chemin == "/display/analyse":
                    self._json(adi.analyse(adf.texte_valide(demande.get("texte")), adi.charge_reference(racine)))
                elif chemin == "/display/inserer":
                    ref = adi.charge_reference(racine)
                    if demande.get("ligne") not in {s["ligne"] for s in ref["sections"]}:
                        raise ValueError(f"parametre inconnu de la reference : {demande.get('ligne')!r}")
                    texte = adi.insere(adf.texte_valide(demande.get("texte")), demande["ligne"], ref)
                    self._json({"texte": texte, "analyse": adi.analyse(texte, ref)})
                elif chemin == "/display/diff":
                    self._json(adf.diff(racine, demande.get("nom"), demande.get("texte")))
                elif chemin == "/display/enregistrer":
                    self._json(adf.enregistre(racine, demande.get("nom"), demande.get("texte"), demande.get("empreinte"),
                                              builds_en_cours))
                elif chemin == "/display/notes":
                    carte = demande.get("carte") and env_atelier(racine, demande.get("carte"))
                    self._json(adf.ajoute_note(racine, demande.get("nom"), carte, demande.get("texte"), builds_en_cours))
                elif chemin == "/apercu":
                    self._json(apercu(racine, env_atelier(racine, demande.get("env")), demande.get("description")))
                elif chemin == "/diff":
                    env = env_atelier(racine, demande.get("env"))
                    p = aee.prevu(racine, env, demande.get("description"))
                    self._json({"fichiers": _fichiers_prevus(p["fichiers"]), "empreinte": p["empreinte"]})
                elif chemin == "/ecrire":
                    env = env_atelier(racine, demande.get("env"))
                    ecran = cat.ecrans_des_envs(racine).get(env)
                    d = demande.get("description")
                    if ecran and isinstance(d, dict) and d.get("ecran") != ecran:   # changer d'ecran : /ecran/changer
                        raise ValueError(f"description pour l'ecran {d.get('ecran')!r}, la carte a {ecran!r} : "
                                         "passer par le changement d'ecran")
                    ids = aer.valide_ids(demande.get("remarques"))
                    r = aee.ecrit(racine, env, demande.get("description"), demande.get("empreinte"),
                                  demande.get("empreinte_description"), builds_en_cours)
                    if ids:
                        r["remarques"] = aer.marque_appliquees(racine, env, ids)
                    self._json({**r, "build": aee.url_build(racine, env)})
                elif chemin == "/ecran/diff":
                    env = env_atelier(racine, demande.get("env"))
                    c = aecr.changement(racine, env, demande.get("ecran"), demande.get("description"))
                    self._json({k: c[k] for k in ("description", "avertissements", "refus", "empreinte")}
                               | {"fichiers": _fichiers_prevus(c["fichiers"])})
                elif chemin == "/ecran/changer":
                    env = env_atelier(racine, demande.get("env"))
                    r = aecr.change(racine, env, demande.get("ecran"), demande.get("description"), demande.get("empreinte"),
                                    demande.get("empreinte_description"), builds_en_cours)
                    self._json({**r, "build": aee.url_build(racine, env)})
                elif chemin == "/remarques":
                    self._json({"remarques": aer.agit(racine, env_atelier(racine, demande.get("env")), demande)})
                elif chemin == "/remarques/appliquer":
                    self._json(aer.applique_remarque(racine, env_atelier(racine, demande.get("env")), demande.get("id"),
                                                     demande.get("description")))
                elif chemin == "/remarques/traiter":
                    env = env_atelier(racine, demande.get("env"))
                    if not depuis_ce_pc(self):     # spec 5.8 : claude -p lance depuis ce PC seulement
                        self._envoie(403, "lancement de Claude permis depuis ce PC seulement".encode("utf-8"))
                        return
                    traitement.lance(env)
                    self._json(traitement.etat())
                elif chemin == "/capture":
                    self._envoie(200, capture(env_atelier(racine, demande.get("env"))), "image/bmp")
                else:
                    raise LookupError("introuvable")
            self._traite(route)

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Atelier des ecrans : ecrans HASPmota / LVGL des cartes.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Atelier des écrans")
    try:
        ThreadingHTTPServer.request_queue_size = 128   # la page lance plusieurs requetes d'un coup (voir atelier des graphiques)
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit dans le depot par cette version).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
