"""Banc de plan_maison_web.py : la page est servie, regeneree, en lecture seule. Code de sortie 0 = vert."""
import json
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
# /debits : lecture de la carte remplacee, jamais de reseau ; cible fixe, erreur propre
appels = []
w.lit_url = lambda u: (appels.append(u), json.dumps({"StatusSNS": {"Time": "2026-11-15T20:00:00", "DEBITS": {"D1": 1.5, "D2": 2.0, "D3": None, "D4": 0.4, "D5": 1.1, "D6": 0.9,
                                                                                                 "Total": 5.9, "Imprecis": [4], "Muets": [3]}}}))[1]
s, corps, _ = requete("/debits")
j = json.loads(corps)
verifie("GET /debits : 200, six debits, total, voies a signaler", s == 200 and j["debits"] == [1.5, 2.0, None, 0.4, 1.1, 0.9] and j["total"] == 5.9 and j["imprecis"] == [4] and j["muets"] == [3])
verifie("GET /debits : une seule requete, vers la carte d'acquisition (Status 10), query du client ignoree", len(appels) == 1 and appels[0].endswith(":8080/cm?cmnd=Status%2010"))
requete("/debits?url=http://evil/")
verifie("GET /debits?url= : la cible ne vient jamais du client", all("evil" not in a for a in appels))
w.lit_url = lambda u: (_ for _ in ()).throw(OSError("timed out"))
s, corps, _ = requete("/debits")
verifie("GET /debits : carte muette -> 502 avec un message court", s == 502 and "timed out" in json.loads(corps)["erreur"] and "192.168" not in corps)
w.lit_url = lambda u: "{}"
verifie("GET /debits : reponse sans bloc DEBITS -> 502", requete("/debits")[0] == 502)
verifie("POST /debits : 405", requete("/debits", "POST")[0] == 405)
serveur.shutdown()
print("\n%d echec(s)" % len(ECHECS))
sys.exit(1 if ECHECS else 0)
