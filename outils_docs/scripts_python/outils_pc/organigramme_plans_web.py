"""Page « Organigramme des plans » (http://127.0.0.1:7990) : lecture seule, tuile de l'annuaire.

Sert la meme page que outils_docs/organigramme_plans/index.html, mais regeneree a chaque ouverture d'apres
les plans de tasks/plans/ (statut, % et dates a jour sans attendre le hook). Rien n'est ecrit, aucun POST.
Donnees : maintenance/organigramme_plans.py (importe par un sys.path explicite, comme synchro_fork_web.py).
Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).
Banc : test_organigramme_plans_web.py.
"""

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import acces_web
from annuaire_outils import hote_autorise

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "maintenance"))
import organigramme_plans as org          # noqa: E402

PORT_DEFAUT = 7990


def fabrique_gestionnaire(acces):
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
                return self._envoie(403, b"refuse")
            if urlsplit(self.path).path != "/":
                return self._envoie(404, b"introuvable")
            try:
                page = acces.habille(org.page_html(org.donnees()))
            except Exception as erreur:      # git absent, plan illisible : le message, pas une trace
                return self._envoie(500, f"organigramme impossible : {type(erreur).__name__} : {erreur}".encode("utf-8"))
            self._envoie(200, page.encode("utf-8"), "text/html; charset=utf-8")

        do_POST = do_GET                    # lecture seule : un POST recoit la meme reponse qu'un GET (aucun effet)

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Organigramme des plans (lecture seule).")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Organigramme des plans")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (lecture seule : rien n'est ecrit).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
