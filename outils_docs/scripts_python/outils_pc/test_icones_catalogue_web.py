"""Banc de icones_catalogue_web (routes, lecture seule, Host hostile, CSP). Code de sortie 0 = vert.

Serveur reel sur 127.0.0.1, port libre, mini-depot temporaire (le vrai depot n'est pas lu).
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_icones_catalogue_web.py
"""
import http.client
import json
import socket
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import acces_web
import icones_catalogue_web as web
from test_icones_catalogue import monte

ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def principal():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
        racine = Path(t)
        monte(racine)
        ttf = racine / "lib/libesp32_lvgl/LVGL_assets/fonts/Symbols/materialdesignicons-webfont.ttf"
        ttf.parent.mkdir(parents=True)
        ttf.write_bytes(b"FAUXTTF")
        port = port_libre()
        acces = acces_web.Acces(port, True, "Catalogue d'icones")
        serveur = ThreadingHTTPServer(("127.0.0.1", port), web.fabrique_gestionnaire(acces, racine))
        serveur.daemon_threads = True
        threading.Thread(target=serveur.serve_forever, daemon=True).start()

        def req(methode, chemin, entetes=None, corps=None):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
            c.request(methode, chemin, body=corps, headers=entetes or {})
            r = c.getresponse()
            donnees = r.read()
            h = {k.lower(): v for k, v in r.getheaders()}
            c.close()
            return r.status, h, donnees

        try:
            s, h, d = req("GET", "/")
            verifie((s, h.get("content-type", "").startswith("text/html"), b"<title>Catalogue d'ic" in d), (200, True, True), "GET / : la page")
            verifie(("default-src 'none'" in h.get("content-security-policy", ""), h.get("x-content-type-options")), (True, "nosniff"), "page : CSP et nosniff")
            s, h, d = req("GET", "/catalogue")
            cat = json.loads(d)
            verifie((s, sorted(cat), len(cat["glyphes"])), (200, ["absentes", "glyphes", "pngs", "sources"], 4), "GET /catalogue : JSON du mini-depot")
            verifie(h.get("x-content-type-options"), "nosniff", "catalogue : nosniff")
            s, h, d = req("GET", "/lib/mdi.ttf")
            verifie((s, d, h.get("content-type")), (200, b"FAUXTTF", "font/ttf"), "GET /lib/mdi.ttf : la police du depot")
            verifie(req("GET", "/inconnu")[0], 404, "route inconnue : 404")
            for m in ("POST", "PUT", "DELETE", "PATCH"):
                verifie(req(m, "/catalogue", {"Content-Type": "application/json", "Content-Length": "2"}, b"{}")[0], 405, f"{m} : refuse 405, lecture seule")
            verifie(req("GET", "/", {"Host": "evil.example:80"})[0], 403, "Host hostile : refuse")
            verifie(req("GET", "/catalogue", {"Host": f"localhost:{port}"})[0], 200, "Host localhost : admis")
            ttf.unlink()
            verifie(req("GET", "/lib/mdi.ttf")[0], 404, "police absente : 404 net")
        finally:
            serveur.shutdown()
            serveur.server_close()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
