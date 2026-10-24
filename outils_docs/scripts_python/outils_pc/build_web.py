"""Page web « Build et televersement » : compiler, televerser (COM ou OTA), construire le FS, en serie.

UTILISATION
    python outils_docs/scripts_python/outils_pc/build_web.py [--http 7700] [--local] [--sans-navigateur]
    L'annuaire des outils (port 7600) la lance ; la console affiche le lien (Ctrl+clic) et ouvre la page.
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Les `pio run` sont lances en serie par build_serie.Serie ; ici, seulement le serveur HTTP.

Routes (les POST exigent l'en-tete X-Build: 1 et la meme origine) :
    GET  /           la page (A6 : build_page.PAGE ; a defaut, une page provisoire)
    GET  /envs       {envs: [champs de Env + littlefs], derniers: derniers choix}
    GET  /execution  {en_cours: bool}
    GET  /flux       Server-Sent Events de la serie (rejoues depuis Last-Event-ID ou ?depuis=n)
    GET  /journal    ?env=<env> : texte du journal pio du dernier lancement de cet env
    POST /lancer     {lignes: [{env, methode, port, ip}], actions: [...]}   409 = refus (motifs)
    POST /port       {env, port} : ecrit upload_port (409 pendant un lancement, 400 si invalide)
    POST /arreter    {immediat: bool}
"""

import argparse
import atexit
import json
import os
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
NOM_OUTIL = "Build et téléversement"          # lu tel quel par la tuile de l'annuaire
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 64 * 1024

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
    envs = []
    for env in build_envs.liste_envs(racine):
        champs = asdict(env)
        champs["littlefs"] = (Path(racine) / ".pio" / "build" / env.nom / "littlefs.bin").is_file()
        envs.append(champs)
    return {"envs": envs, "derniers": lit_derniers(dossier)}


def journal_env(dossier, env, depuis):
    """Texte des journaux de `env` ecrits depuis `depuis` (heure epoch) ; a defaut, le dernier."""
    if not build_serie.NOM_ENV.fullmatch(env or ""):
        raise ValueError(f"nom d'environnement invalide : {env!r}")
    fichiers = sorted((Path(dossier) / "journaux").glob(f"*-{env}-*.log"), key=lambda f: f.name)
    recents = [f for f in fichiers if f.stat().st_mtime >= depuis]
    return "".join(f.read_text(encoding="utf-8", errors="replace") for f in (recents or fichiers[-1:]))


def ligne_de(donnee):
    if not isinstance(donnee, dict):
        raise ValueError("ligne attendue sous forme d'objet")
    return build_serie.Ligne(*(str(donnee.get(k) or "") for k in ("env", "methode", "port", "ip")))


def fabrique_gestionnaire(serie, acces, racine, dossier):
    etat = {"debut": 0.0}                                 # heure du dernier lancement accepte

    def traite_post(chemin, demande):
        if chemin == "/lancer":
            lignes, actions = demande.get("lignes"), demande.get("actions")
            if not isinstance(lignes, list) or not isinstance(actions, list):
                raise ValueError("lignes et actions attendues sous forme de listes")
            objets = [ligne_de(d) for d in lignes]
            actions = [str(a) for a in actions]
            etat["debut"] = time.time()
            try:
                serie.lance(objets, actions)              # RuntimeError (409) : motifs de controle
            except RuntimeError:
                etat["debut"] = 0.0
                raise
            ecrit_derniers(dossier, [asdict(o) for o in objets], actions)
            return {"ok": True}
        if chemin == "/port":
            if serie.en_cours():
                raise RuntimeError("un lancement est en cours : modifier le port apres")
            build_envs.ecrit_port(racine, str(demande.get("env", "")), str(demande.get("port", "")))
            return {"ok": True}
        if chemin == "/arreter":
            serie.arrete(bool(demande.get("immediat")))
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
                    self._json({"en_cours": serie.en_cours()})
                elif url.path == "/flux":
                    depuis = self.headers.get("Last-Event-ID") or params.get("depuis", ["0"])[0]
                    self._flux(int(depuis) if str(depuis).isdigit() else 0)
                elif url.path == "/journal":
                    self._envoie(200, journal_env(dossier, params.get("env", [""])[0], etat["debut"]).encode("utf-8"))
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
    """A la fermeture : si un lancement est en cours, tue l'arbre du fils pio (pas de pio orphelin)."""
    if not serie.en_cours():
        return
    serie.arrete(immediat=True)
    limite = time.monotonic() + attente
    while serie.en_cours() and time.monotonic() < limite:
        time.sleep(0.1)


def principal():
    options = argparse.ArgumentParser(description="Page web de build et televersement des cartes Tasmota.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()

    acces = acces_web.Acces(args.http, args.local, NOM_OUTIL)
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
    print("Ctrl+C pour arreter (un lancement en cours est alors tue, arbre pio compris).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
        if serie.en_cours():
            print("lancement en cours : arret immediat...", flush=True)
            arrete_serie(serie)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
