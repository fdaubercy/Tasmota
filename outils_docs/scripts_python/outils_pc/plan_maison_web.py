"""Plan de la maison (page web, port 7915) : cartes par piece, liens, maitres/esclaves, vue reseau et Wi-Fi. LECTURE SEULE.

UTILISATION
    python outils_docs/scripts_python/outils_pc/plan_maison_web.py [--http 7915] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Routes (GET seulement ; client de ce PC : Host local, parade au DNS rebinding) :
    GET /   la page, regeneree a chaque appel par outils_docs/plan_maison/genere_plan_maison.py::construit
            (persist et placement.json relus ; aucun fichier ecrit, aucune requete reseau)
Tout autre verbe : 405. Banc : test_plan_maison_web.py.
"""

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import acces_web
from annuaire_outils import hote_autorise

PORT_DEFAUT = 7915
DEPOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(DEPOT / "outils_docs" / "plan_maison"))
# La page lance un fetch no-cors vers les IP des cartes (bouton « Tester les cartes ») : connect-src les autorise.
CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self' http:; manifest-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'none'")


def fabrique_gestionnaire(acces):
    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if not acces.controle(self):
                return
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            if urlsplit(self.path).path != "/":
                self._envoie(404, b"introuvable")
                return
            try:
                import genere_plan_maison
                page, _ = genere_plan_maison.construit()
                self._envoie(200, acces.habille(page).encode("utf-8"), "text/html; charset=utf-8")
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def _refuse(self):
            self.close_connection = True
            self._envoie(405, b"lecture seule")

        do_POST = do_PUT = do_DELETE = do_PATCH = _refuse

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Plan de la maison : cartes, liens, maitres, Wi-Fi (lecture seule).")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Plan de la maison")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit dans le depot).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
