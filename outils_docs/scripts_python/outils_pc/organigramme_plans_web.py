"""Page « Organigramme des plans » (http://127.0.0.1:7990)  : tuile de l'annuaire.

Sert la meme page que outils_docs/organigramme_plans/index.html, mais regeneree a chaque ouverture d'apres
les plans de tasks/plans/ (statut, % et dates a jour sans attendre le hook). Seule ecriture : le bouton « Publier sur GitHub Pages » (POST /publier, double clic de confirmation).
Donnees : maintenance/organigramme_plans.py (importe par un sys.path explicite, comme synchro_fork_web.py).
Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).
Banc : test_organigramme_plans_web.py.
"""

import argparse
import json
import time
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
_RETARD = {"t": 0.0, "v": None}          # /retard : un fetch git au plus toutes les 60 s
BOUTON = (
    "<style>.publ{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 12px}"
    ".publ .pbtn{display:inline-flex;align-items:center;justify-content:center;gap:7px;height:34px;padding:0 14px;font:inherit;font-weight:600;"
    "color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:8px;cursor:pointer;text-decoration:none;"
    "transition:background .15s,border-color .15s,transform .05s}"
    ".publ .pbtn:hover{border-color:var(--f0);color:var(--f0)}.publ .pbtn:active{transform:translateY(1px)}"
    ".publ .pbtn:focus-visible{outline:2px solid var(--f0);outline-offset:2px}"
    ".publ .pbtn.prim{background:var(--f0);border-color:var(--f0);color:#fff}.publ .pbtn.prim:hover{filter:brightness(1.1);color:#fff}"
    ".publ .pbtn.pico{width:34px;padding:0}.publ .pbtn:disabled{opacity:.55;cursor:progress}"
    "#pubm{color:var(--mut);font-size:13px}</style>"
    "<p class='publ'><button id='pub' class='pbtn prim'>"
    "<svg viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
    "stroke-linejoin='round' aria-hidden='true'><path d='M12 16V4'/><path d='m6 10 6-6 6 6'/><path d='M4 20h16'/></svg>"
    "Publier sur GitHub Pages</button>"
    "<a class='pbtn pico' href='" + org.URL_PAGES + "' target='_blank' rel='noopener' title='Ouvrir la version en ligne' aria-label='Ouvrir la version en ligne'>"
    "<svg viewBox='0 0 24 24' width='17' height='17' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
    "stroke-linejoin='round' aria-hidden='true'><circle cx='12' cy='12' r='10'/><path d='M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20'/>"
    "<path d='M2 12h20'/></svg></a><span id='pubm'></span></p>"
    "<p id='ret' role='status' style='display:none;margin:0 0 10px;padding:6px 10px;border:1px solid #c27400;border-radius:6px;color:#c27400'></p>"
    "<script>document.getElementById('pub').onclick=function(){var b=this,m=document.getElementById('pubm');"
    "if(!confirm_pub())return;b.disabled=true;m.textContent='publication en cours...';"
    "fetch('/publier',{method:'POST',headers:{'X-Organigramme':'1'}}).then(function(r){return r.text()}).then(function(t){"
    "m.textContent=t;b.disabled=false;retard()}).catch(function(e){m.textContent='erreur : '+e;b.disabled=false})};"
    "function retard(){fetch('/retard',{cache:'no-store'}).then(function(r){return r.ok?r.json():null}).then(function(d){"
    "var e=document.getElementById('ret');if(!d){e.style.display='none';return}"
    "if(d.n===0){e.style.display='none';return}"
    "e.textContent='La version en ligne est en retard de '+d.n+' plan'+(d.n>1?'s':'')+' : '+d.noms.slice(0,6).join(', ')+(d.n>6?'...':'');"
    "e.style.display=''}).catch(function(){})}retard();"
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
            if urlsplit(self.path).path == "/retard":
                if time.monotonic() - _RETARD["t"] > 60 or "frais" in self.path:
                    try:
                        _RETARD["v"] = org.retard_publication()
                    except Exception:      # hors ligne, git absent : pas de bandeau
                        _RETARD["v"] = None
                    _RETARD["t"] = time.monotonic()
                return self._envoie(200, json.dumps(_RETARD["v"]).encode("utf-8"), "application/json")
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
                _RETARD["t"] = 0.0
                texte = "deja a jour" if not sha else f"publiee ({sha[:9]})"
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
