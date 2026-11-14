"""Sonde Chrome de la page de repli d'un outil arrete (acces_repli.py, habille() de acces_web.py).

UTILISATION (a la main, hors de tout build : aucun pio, aucun outil reel lance, Chrome ~20 s)
    ~/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/outils_pc/test_acces_repli_chrome.py
Code de sortie 0 = vert. Scenario : un faux outil (serveur local sur un port libre, page habillee par acces_web) est
ouvert dans Chrome ; le service worker s'active ; le serveur est ARRETE ; la navigation vers l'outil affiche
« <nom> est arrete » au lieu de l'erreur du navigateur ; le serveur est RELANCE sur le meme port ; la page se
recharge seule. Temoin : le meme faux outil servi SANS habille() (donc sans worker) ne montre aucun repli.
Montage de Chrome et client CDP : test_build_page_chrome.py.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import acces_web
import test_build_page_chrome as t

verifie = t.verifie
PAGE = "<!doctype html><html><head><title>Outil d'essai</title></head><body><p id=x>page de l'outil</p></body></html>"
NOM = "Outil d'essai"


def serveur(port, habille):
    acces = acces_web.Acces(port, True, NOM)

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"          # connexions fermees : un arret de serveur est un vrai arret

        def log_message(self, format, *args):
            pass

        def do_GET(self):
            if not acces.controle(self):
                return
            corps = (acces.habille(PAGE) if habille else PAGE).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

    class S(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    srv = S(("127.0.0.1", port), H)
    Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def arrete(srv):
    srv.shutdown()
    srv.server_close()


def lance_chrome(dossier):
    chrome = next((c for c in t.CHROMES if c.is_file()), None)
    if chrome is None:
        raise FileNotFoundError("chrome.exe introuvable")
    port_cdp = t.port_libre()
    proc = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={port_cdp}",
                             "--remote-allow-origins=*", f"--user-data-dir={dossier / 'profil'}", "--no-first-run",
                             "--no-default-browser-check", "--disable-extensions", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    limite = time.monotonic() + 20
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port_cdp}/json/list", timeout=2) as r:
                page = next(c for c in json.loads(r.read().decode("utf-8")) if c.get("type") == "page")
                break
        except (OSError, StopIteration):
            time.sleep(0.2)
    else:
        raise TimeoutError("Chrome ne repond pas")
    cdp = t.Cdp(page["webSocketDebuggerUrl"])
    for domaine in ("Runtime.enable", "Page.enable"):
        cdp.appel(domaine)
    return proc, cdp


def titre(cdp):
    return cdp.js("document.title")


def attend_titre(cdp, contient, delai):
    return t.attend(cdp, f"document.title.indexOf({json.dumps(contient)}) >= 0", delai)


def scenario_repli(cdp):
    port = t.port_libre()
    url = f"http://127.0.0.1:{port}/"
    srv = serveur(port, True)
    cdp.appel("Page.navigate", url=url)
    attend_titre(cdp, "Outil d'essai", 10)
    verifie(cdp.js("!!document.getElementById('barre-outils')"), True, "repli : page servie, barre presente")
    verifie(t.attend(cdp, "!!navigator.serviceWorker.controller", 15), True, "repli : service worker actif et maitre de la page")
    arrete(srv)
    cdp.appel("Page.navigate", url=url)
    attend_titre(cdp, "est arrêté", 10)
    verifie(titre(cdp), NOM + " est arrêté", "repli : serveur arrete -> page « est arrete » (et non l'erreur du navigateur)")
    verifie(cdp.js("document.getElementById('a').getAttribute('href')"), "http://127.0.0.1:7600/",
            "repli : lien vers l'annuaire (port 7600)")
    srv = serveur(port, True)
    ok = t.attend(cdp, f"document.title === {json.dumps(NOM)}", 15)        # exact : le titre du repli contient le nom
    verifie((ok, titre(cdp)), (True, NOM), "repli : serveur relance -> la page se recharge toute seule")
    arrete(srv)


def scenario_temoin(cdp):
    port = t.port_libre()
    url = f"http://127.0.0.1:{port}/"
    srv = serveur(port, False)
    cdp.appel("Page.navigate", url=url)
    attend_titre(cdp, "Outil d'essai", 10)
    arrete(srv)
    cdp.appel("Page.navigate", url=url)
    time.sleep(2)
    verifie("est arrêté" in str(titre(cdp)), False, "TEMOIN sans worker : aucun repli (le navigateur garde son erreur)")


def principal():
    dossier = Path(tempfile.mkdtemp(prefix="sonde_repli_"))
    proc = None
    try:
        proc, cdp = lance_chrome(dossier)
        scenario_repli(cdp)
        scenario_temoin(cdp)
    finally:
        if proc is not None:
            t.tue_arbre(proc)
        time.sleep(0.5)
        shutil.rmtree(dossier, ignore_errors=True)
    print()
    print("VERT" if not t.ECHECS else f"ROUGE : {len(t.ECHECS)} echec(s)")
    return 0 if not t.ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
