"""Banc de cible_build_web.py (cible Custom « Build et televersement ») sans PlatformIO ni vrai build_web.

Code de sortie 0 = vert. Un faux build_web (serveur HTTP de la stdlib, ecrit dans un dossier temporaire)
remplace la vraie page ; ports pris au hasard sur 127.0.0.1, jamais 7700 ; navigateur simule.
Lancer : "%USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe" -u test_cible_build_web.py
"""

import http.server
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import cible_build_web as cible

ECHECS = []

FAUX_SERVEUR = r'''
import http.server, sys
port = int(sys.argv[sys.argv.index("--http") + 1])
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"en_cours": false}')
    def log_message(self, *a): pass
print("faux build_web sur", port, flush=True)
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
'''

FAUX_MORT = 'import sys\nprint("faux build_web : erreur au demarrage", flush=True)\nsys.exit(3)\n'


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_deja_lancee():
    port = port_libre()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"en_cours": false}')

        def log_message(self, *a):
            pass

    serveur = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    ouverts, lances = [], []
    with tempfile.TemporaryDirectory() as t:
        code = cible.lance_page(sys.executable, Path(t), port, Path(t) / "donnees", Path(t) / "absent.py",
                                ouvre=ouverts.append, demarre=lambda *a, **k: lances.append(a))
    serveur.shutdown()
    verifie((code, ouverts, lances), (0, [f"http://127.0.0.1:{port}/"], []),
            "deja lancee : ouvre seulement la page, ne relance rien")


def test_demarre_detachee():
    port = port_libre()
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        script = t / "faux_build_web.py"
        script.write_text(FAUX_SERVEUR, encoding="utf-8")
        ouverts = []
        debut = time.monotonic()
        code = cible.lance_page(sys.executable, t, port, t / "donnees", script, ouvre=ouverts.append)
        duree = time.monotonic() - debut
        repond = cible.repond(port)
        console = (t / "donnees" / "consoles" / "build.log").read_text(encoding="utf-8", errors="replace")
        verifie((code, repond, ouverts), (0, True, []),
                "absente : demarree detachee, repond, la cible rend la main (la page ouvre le navigateur elle-meme)")
        verifie(duree < 10, True, f"absente : la cible rend la main vite ({duree:.1f} s)")
        verifie("faux build_web sur" in console, True, "absente : console de la page dans consoles/build.log")
        cible.DERNIER.kill()
        cible.DERNIER.wait(5)


def test_demarrage_rate():
    port = port_libre()
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        script = t / "faux_mort.py"
        script.write_text(FAUX_MORT, encoding="utf-8")
        code = cible.lance_page(sys.executable, t, port, t / "donnees", script, ouvre=lambda u: None, attente=3)
        verifie((code, cible.repond(port)), (1, False), "demarrage rate : code 1, rien n'ecoute")


def principal():
    for t in (test_deja_lancee, test_demarre_detachee, test_demarrage_rate):
        try:
            t()
        except Exception as erreur:          # un test qui plante est un echec, pas un arret du banc
            verifie(repr(erreur), None, f"{t.__name__} : exception")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
