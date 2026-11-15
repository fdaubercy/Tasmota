"""Taches planifiees (page web, port 7920) : etat des compilations de nuit, voie PC et voie GitHub, et leurs gestes (plan compilations-nuit A3 et A4).

UTILISATION
    python outils_docs/scripts_python/outils_pc/taches_planifiees_web.py [--http 7920] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

La lecture (GET) n'ecrit rien. Les gestes (POST /geste, taches_planifiees_actions.py) exigent l'en-tete X-Taches: 1, la meme origine et un
client de CE PC (403 sinon, pas de jeton distant : ils touchent la tache Windows, le depot et GitHub). Sources : taches_planifiees_pc.py (tache Windows + resultats),
taches_planifiees_github.py (CLI gh, controle de sante a chaque ouverture, resultat garde CACHE_S secondes), taches_planifiees_sante.py (bandeau).
Routes :
    GET /        la page (taches_planifiees_page.PAGE)
    GET /etat[?frais=1]   {niveau: vert|orange|rouge, phrase, pc, github, instant, envs, github_exclus}
    POST /geste  {voie, geste, valeur} : active, desactive, heure, lancer, arreter, envs, envs_apercu (voir taches_planifiees_actions.py)
Banc : test_taches_planifiees_web.py.
"""

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import subprocess

import acces_web
from annuaire_outils import hote_autorise
import taches_planifiees_actions as ta
import taches_planifiees_github as tg
import taches_planifiees_pc as tp
import taches_planifiees_sante as ts
import taches_planifiees_gestes as tgest

PORT_DEFAUT = 7920
CACHE_S = 45
MAX_CORPS = 64 * 1024


class Etat:
    def __init__(self, gh=tg.gh, schtasks=tp.tache.schtasks, dossier=None, journaux=None, cache_s=CACHE_S,
                 appel=tgest.nuit.appel, lance=subprocess.Popen, racine=tgest.matrice.RACINE, eteinte=tgest.page_eteinte):
        self.gh, self.schtasks, self.dossier, self.journaux, self.cache_s = gh, schtasks, dossier, journaux, cache_s
        self.eteinte, self.verrou_gestes = eteinte, threading.Lock()
        self.appel, self.lance, self.racine = appel, lance, racine           # injectables : le banc n'atteint jamais la vraie page Build ni le vrai depot
        self._cache = (0.0, None)
        self._verrou = threading.Lock()

    def github(self, frais=False):
        with self._verrou:                          # un seul appel a gh a la fois : les ouvertures simultanees partagent le resultat
            t, v = self._cache
            if frais or v is None or time.monotonic() - t > self.cache_s:
                v = tg.sante(self.gh)
                self._cache = (time.monotonic(), v)
            return v

    def invalide(self):
        with self._verrou:
            self._cache = (0.0, None)

    def envs(self):
        """Envs du cenv et exclusions GitHub (fichier du depot) ; un fichier illisible est signale, jamais une exception."""
        try:
            exclus, erreur = tgest.matrice.lit_exclus(self.racine), None
        except (OSError, ValueError) as e:
            exclus, erreur = [], f"envs_github.json illisible : {e}"
        return {"envs": tgest.matrice.envs_cenv(self.racine), "github_exclus": exclus, "github_exclus_erreur": erreur}

    def complet(self, frais=False):
        pc = tp.lit_pc(self.dossier, self.schtasks, self.journaux)
        gh = self.github(frais)
        niveau, phrase = ts.bandeau(pc, gh)
        return {"niveau": niveau, "phrase": phrase, "pc": pc, "github": gh, "instant": time.strftime("%Y-%m-%d %H:%M:%S"), **self.envs()}


def fabrique_gestionnaire(acces, etat):
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

        def do_GET(self):
            if not acces.controle(self):
                return
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                u = urlsplit(self.path)
                if u.path == "/":
                    import taches_planifiees_page
                    self._envoie(200, acces.habille(taches_planifiees_page.PAGE).encode("utf-8"), "text/html; charset=utf-8")
                elif u.path == "/etat":
                    frais = parse_qs(u.query).get("frais", ["0"])[0] == "1"
                    self._envoie(200, json.dumps(etat.complet(frais), ensure_ascii=False).encode("utf-8"), "application/json")
                else:
                    self._envoie(404, b"introuvable")
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def do_POST(self):
            if not acces.controle(self):
                return
            if (not hote_autorise(self, acces.port) or self.headers.get("X-Taches") != "1" or not acces.origine_autorisee(self)
                    or not acces_web.est_local(self.client_address)):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            if urlsplit(self.path).path != "/geste":
                self._envoie(404, b"introuvable")
                return
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if longueur < 0:
                    raise ValueError("Content-Length invalide")
                if longueur > MAX_CORPS:
                    self.close_connection = True                      # corps non lu : la connexion ne doit pas resservir
                    self._envoie(413, "corps trop gros (64 Ko au plus)".encode("utf-8"))
                    return
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                self._envoie(200, json.dumps(ta.executer(demande, etat), ensure_ascii=False).encode("utf-8"), "application/json")
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except RuntimeError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Taches planifiees : compilations de nuit PC et GitHub.")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Taches planifiees")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, Etat()))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit sans geste explicite dans la page).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
