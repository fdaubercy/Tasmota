"""Banc de plan_maison_web.py : la page est servie, regeneree, en lecture seule. Code de sortie 0 = vert."""
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_maison_web as w  # noqa: E402

ECHECS = []


def verifie(nom, ok):
    print(("OK   " if ok else "KO   ") + nom)
    if not ok:
        ECHECS.append(nom)


class AccesTest:
    """Acces de ce PC : rien a controler, port connu."""
    def __init__(self, port):
        self.port = port

    def controle(self, h):
        return True

    def habille(self, page):
        return page


serveur = ThreadingHTTPServer(("127.0.0.1", 0), w.fabrique_gestionnaire(AccesTest(0)))
port = serveur.server_address[1]
w.hote_autorise = lambda h, p: True
threading.Thread(target=serveur.serve_forever, daemon=True).start()


def requete(chemin, methode="GET"):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{chemin}", method=methode, data=b"x" if methode != "GET" else None)
    try:
        with urllib.request.urlopen(r, timeout=30) as rep:
            return rep.status, rep.read().decode("utf-8"), dict(rep.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


s, corps, ent = requete("/")
verifie("GET / : 200 et page du plan", s == 200 and "Plan de la maison" in corps and 'class="carte' in corps)
verifie("GET / : CSP presente, pas de cache", "default-src 'none'" in ent.get("Content-Security-Policy", "") and ent.get("Cache-Control") == "no-store")
verifie("GET /autre : 404", requete("/autre")[0] == 404)
verifie("POST / : 405 lecture seule", requete("/", "POST")[0] == 405)
verifie("PUT / : 405 lecture seule", requete("/", "PUT")[0] == 405)
serveur.shutdown()
print("\n%d echec(s)" % len(ECHECS))
sys.exit(1 if ECHECS else 0)
