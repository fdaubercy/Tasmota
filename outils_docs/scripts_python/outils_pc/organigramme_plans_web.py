"""Page « Organigramme des plans » (http://127.0.0.1:7990)  : tuile de l'annuaire.

Sert la meme page que outils_docs/organigramme_plans/index.html, mais regeneree a chaque ouverture d'apres
les plans de tasks/plans/ (statut, % et dates a jour sans attendre le hook). Seule ecriture : le bouton « Publier sur GitHub Pages » (POST /publier, double clic de confirmation).
Donnees : maintenance/organigramme_plans.py (importe par un sys.path explicite, comme synchro_fork_web.py).
Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).
Banc : test_organigramme_plans_web.py.
"""

import argparse
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import acces_web
from annuaire_outils import hote_autorise

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "maintenance"))
import organigramme_plans as org          # noqa: E402

PORT_DEFAUT = 7990
VERROU = threading.Lock()                 # une publication a la fois
BOUTON = (
    "<p><button id='pub'>Publier sur GitHub Pages</button> <span id='pubm'></span></p>"
    "<script>document.getElementById('pub').onclick=function(){var b=this,m=document.getElementById('pubm');"
    "if(!confirm_pub())return;b.disabled=true;m.textContent='publication en cours...';"
    "fetch('/publier',{method:'POST',headers:{'X-Organigramme':'1'}}).then(function(r){return r.text()}).then(function(t){"
    "m.textContent=t;b.disabled=false}).catch(function(e){m.textContent='erreur : '+e;b.disabled=false})};"
    "function confirm_pub(){var m=document.getElementById('pubm');if(m.dataset.ok==='1'){m.dataset.ok='';return true}"
    "m.textContent='Cliquez encore pour confirmer la publication (page publique, adresses IP masquees).';m.dataset.ok='1';return false}</script>")


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

        def _admis(self):
            if not acces.controle(self):
                return False
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return False
            return True

        def do_GET(self):
            if not self._admis():
                return
            if urlsplit(self.path).path != "/":
                return self._envoie(404, b"introuvable")
            try:
                page = acces.habille(org.page_html(org.donnees()).replace('<div class="bar"', BOUTON + '<div class="bar"', 1))
            except Exception as erreur:      # git absent, plan illisible : le message, pas une trace
                return self._envoie(500, f"organigramme impossible : {type(erreur).__name__} : {erreur}".encode("utf-8"))
            self._envoie(200, page.encode("utf-8"), "text/html; charset=utf-8")

        def do_POST(self):
            """Seule ecriture : /publier = `organigramme_plans.py --publier` (en-tete X-Organigramme, meme origine)."""
            if not self._admis():
                return
            if urlsplit(self.path).path != "/publier" or self.headers.get("X-Organigramme") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                return self._envoie(403, b"refuse")
            if not VERROU.acquire(blocking=False):
                return self._envoie(409, "une publication est deja en cours".encode("utf-8"))
            try:
                sha = org.publie_pages()
                texte = "deja a jour" if not sha else f"publie ({sha[:9]}) : {org.URL_PAGES}"
                self._envoie(200, texte.encode("utf-8"))
            except Exception as erreur:      # reseau, branche qui a bouge : le message, pas une trace
                self._envoie(500, f"publication impossible : {type(erreur).__name__} : {erreur}".encode("utf-8"))
            finally:
                VERROU.release()

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Organigramme des plans (publication sur demande).")
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
    print("Ctrl+C pour arreter (rien n'est publie sans un clic de confirmation dans la page).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
