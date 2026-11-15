"""Sondes en cours (page web, port 7910) : les bancs et sondes Chrome qui tournent sur ce PC, avec leur avancement reel (plan sondes-en-cours A3).

UTILISATION
    python outils_docs/scripts_python/outils_pc/sondes_web.py [--http 7910] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Sources : sondes_scan.py (processus par PowerShell + fichiers de suivi ecrits par suivi_sondes.py). Releve garde CACHE_S secondes.
Routes :
    GET /        la page (sondes_page.PAGE)
    GET /etat    {niveau: vert|orange|rouge, phrase, instant, erreur, sondes: [...]}
    POST /arreter {pid} ou {orphelines: true} : exige X-Sondes: 1, la meme origine, un client de CE PC (403 sinon, jamais de jeton distant) ;
                  pid hors du dernier releve : 404 (sondes_actions.py)
Banc : test_sondes_web.py.
"""

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import acces_web
from annuaire_outils import hote_autorise
import sondes_actions
import sondes_scan
import suivi_sondes

PORT_DEFAUT = 7910
CACHE_S = 3
MAX_CORPS = 4 * 1024


def bandeau(sondes, erreur=None):
    en_cours = [s for s in sondes if s["etat"] in ("en_cours", "sans_suivi", "orpheline")]
    orph = [s for s in sondes if s["etat"] == "orpheline"]
    rouges = [s for s in sondes if s["etat"] == "en_cours" and s["echecs"]]
    if orph or rouges:
        return "rouge", (f"{len(orph)} Chrome de sonde orphelin(s) à arrêter" if orph else f"{len(rouges)} sonde(s) en cours avec déjà un échec")
    if erreur or any(s["etat"] == "disparue" or s["verdict"] == "rouge" for s in sondes):
        return "orange", (f"Relevé des processus impossible : {erreur}" if erreur else "Une sonde récente a échoué ou a disparu")
    return "vert", (f"{len(en_cours)} sonde(s) en cours" if en_cours else "Aucune sonde en cours")


class Etat:
    def __init__(self, ps=sondes_scan.lance_ps, vivant=suivi_sondes.vivant, dossier=None, cache_s=CACHE_S, tue=sondes_actions.taskkill,
                 relit=sondes_scan.relit_processus):
        self.relit = relit
        self.ps, self.vivant, self.dossier, self.cache_s, self.tue = ps, vivant, dossier, cache_s, tue      # injectables : le banc ne lance ni PowerShell ni taskkill
        self._cache = (0.0, None)
        self._verrou = threading.Lock()

    def complet(self):
        with self._verrou:                          # un seul releve PowerShell a la fois
            t, v = self._cache
            if v is None or time.monotonic() - t > self.cache_s:
                erreur = None
                try:
                    procs = sondes_scan.processus(self.ps)
                except Exception as e:
                    procs, erreur = [], f"{type(e).__name__} : {e}"[:200]
                sondes = sondes_scan.releve(procs, sondes_scan.lit_fichiers(self.dossier or suivi_sondes.dossier_sondes()), self.vivant)
                niveau, phrase = bandeau(sondes, erreur)
                v = {"niveau": niveau, "phrase": phrase, "instant": time.strftime("%Y-%m-%d %H:%M:%S"), "erreur": erreur, "sondes": sondes}
                self._cache = (time.monotonic(), v)
            return v

    def arrete(self, demande):
        with self._verrou:
            releve = (self._cache[1] or {}).get("sondes", [])      # le dernier releve montre a la page, jamais un releve neuf
        r = sondes_actions.arrete(demande, releve, self.tue, self.relit)
        with self._verrou:
            self._cache = (0.0, None)
        return r


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
                chemin = urlsplit(self.path).path
                if chemin == "/":
                    import sondes_page
                    self._envoie(200, acces.habille(sondes_page.PAGE).encode("utf-8"), "text/html; charset=utf-8")
                elif chemin == "/etat":
                    self._envoie(200, json.dumps(etat.complet(), ensure_ascii=False).encode("utf-8"), "application/json")
                else:
                    self._envoie(404, b"introuvable")
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def do_POST(self):
            if not acces.controle(self):
                return
            if (not hote_autorise(self, acces.port) or self.headers.get("X-Sondes") != "1" or not acces.origine_autorisee(self)
                    or not acces_web.est_local(self.client_address)):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            if urlsplit(self.path).path != "/arreter":
                self._envoie(404, b"introuvable")
                return
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if longueur > MAX_CORPS:
                    self.close_connection = True
                    self._envoie(413, "corps trop gros".encode("utf-8"))
                    return
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                self._envoie(200, json.dumps(etat.arrete(demande), ensure_ascii=False).encode("utf-8"), "application/json")
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Sondes en cours : bancs et sondes Chrome de ce PC, avancement reel.")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Sondes en cours")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, Etat()))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est arrete sans geste explicite dans la page).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
