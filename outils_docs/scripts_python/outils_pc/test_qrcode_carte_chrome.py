"""Sonde Chrome de la page /qrcode de la carte (data/fs/qrcodePage.be, plan etiquettes-qrcode A6).

UTILISATION (a la main ; Python de PlatformIO)
    python outils_docs/scripts_python/outils_pc/test_qrcode_carte_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert, 1 = rouge, 3 = Chrome ou berry.exe introuvable.

La page est celle que produit le VRAI module dans le banc Berry (berry/banc_qrcode_page.py --garde) ; un serveur local
imite la carte : /qrcode (cette page), ?f=lib.js.gz (le .gz du depot), ?f=reglage et ?f=etat (un scenario par
chargement). Chrome headless (profil « sonde_qrc_* », arrete a la fin) et client DevTools de test_build_page_chrome.
Verifie : QR code dessine et texte affiche ; nombre de modules (optionsQR + bibliotheque recue de la carte) = verdict de
l'outil ; couleur du style dans le SVG ; IP inscrite differente -> avertissement ; IP:port (esclave joint par le maitre)
ou meme IP -> aucun ; reglage absent -> message d'erreur ; texte hostile affiche en texte ; bibliotheque demandee une
seule fois (cache localStorage) ; theme sombre de Tasmota lisible ; aucune erreur JS.
Ne teste pas : le serveur web de Tasmota (Referer), la RAM, le scan au telephone (essai sur carte de l'A6).
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import etiquettes_qr_verdict as verdict
import test_build_page_chrome as s

RACINE = Path(__file__).resolve().parents[3]
GZ = RACINE / "data/sd/js/qr-code-styling.min.js.gz"
IP = "192.168.0.60"
TEXTE = "Hostname : tasmota-tv-salon · IP : 192.168.0.60 · Lieu : Salon été"
ETAT = """(() => { const t = id => document.getElementById(id), a = t('q_avert'), st = e => getComputedStyle(e);
  return {svg: !!t('q_code').querySelector('svg'), largeur: (t('q_code').querySelector('svg') || {}).getAttribute
          ? t('q_code').querySelector('svg').getAttribute('width') : null, texte: t('q_texte').textContent,
          msg: t('q_msg').textContent, msg_cache: t('q_msg').hidden, erreur: t('q_msg').className,
          avert: a.hidden ? null : a.textContent, img: document.querySelectorAll('#q_zone img').length,
          pirate: window.pirate === 1, svg_html: t('q_code').innerHTML,
          fond: st(document.body).backgroundColor, encre: st(t('q_texte')).color, fond_qr: st(t('q_code')).backgroundColor,
          avert_couleurs: [st(a).color, st(a).backgroundColor]}; })()"""
MODULES = "new QRCodeStyling(optionsQR(%s, {}, %s, null, 100, 0))._qr.getModuleCount()"


class Carte:
    """Serveur qui imite la carte ; `scenario` = {"reglage": dict | None (404), "etat": dict}."""

    def __init__(self, page):
        self.page, self.scenario, self.demandes = page, {}, []
        carte = self

        class Gestionnaire(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                u = urlparse(self.path)
                f = parse_qs(u.query).get("f", [""])[0]
                carte.demandes.append(f or u.path)
                if u.path == "/favicon.ico":                # la carte en sert un : pas d'erreur 404 de Chrome
                    return self.repond(200, "image/x-icon", b"")
                if u.path != "/qrcode":
                    return self.repond(404, "text/plain", b"absent")
                if f == "lib.js.gz":
                    if carte.scenario.get("sans_lib"):
                        return self.repond(404, "text/plain", b"Fichier absent : /sd/js/qr-code-styling.min.js.gz")
                    return self.repond(200, "application/octet-stream", GZ.read_bytes())
                if f in ("reglage", "etat"):
                    v = carte.scenario.get(f)
                    if v is None:
                        return self.repond(404, "text/plain", b"Fichier absent : /json/qrcode.json")
                    return self.repond(200, "application/json", json.dumps(v, ensure_ascii=False).encode("utf-8"))
                return self.repond(200, "text/html; charset=utf-8", carte.page)

            def repond(self, code, mime, corps):
                self.send_response(code)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(corps)))
                self.end_headers()
                self.wfile.write(corps)

        self.serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gestionnaire)
        self.port = self.serveur.server_address[1]
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()


def reglage(texte=TEXTE, ip_inscrite=IP, **style):
    correction = "M"
    return {"version": 1, "texte": texte, "style": style, "image": None, "correction": correction,
            "modules": verdict.verdict(texte, 25, correction)["modules"], "ip_inscrite": ip_inscrite, "entre_lignes": " · "}


def charge(cdp, carte, url, scenario, attente):
    carte.scenario = scenario
    cdp.appel("Page.navigate", url=url)
    s.attend(cdp, attente, 60)
    time.sleep(0.5)                                   # f=etat suit le dessin : laisser l'avertissement arriver
    return cdp.js(ETAT)


def sonde(cdp, carte, capture):
    url = f"http://127.0.0.1:{carte.port}/qrcode"
    dessine = "document.querySelector('#q_code svg') !== null"
    etat = {"ip": IP, "hostname": "tasmota-tv-salon"}

    e = charge(cdp, carte, url, {"reglage": reglage(couleur="#123456", points="rounded"), "etat": etat}, dessine)
    s.verifie((e["svg"], e["largeur"], e["texte"], e["msg_cache"]), (True, "260", TEXTE.replace(" · ", "\n"), True),
              "QR code dessine (260 px), texte affiche une ligne par champ (« · » -> retour a la ligne), plus de message")
    s.verifie("#123456" in e["svg_html"], True, "couleur du style (#123456) dans le SVG")
    s.verifie(e["avert"], None, "meme IP que la carte : aucun avertissement")
    attendu = verdict.verdict(TEXTE, 25, "M")["modules"]
    s.verifie(cdp.js(MODULES % (json.dumps(TEXTE), "'M'")), attendu,
              f"optionsQR + bibliotheque de la carte : {attendu} modules = verdict de l'outil")
    s.verifie(cdp.js(MODULES % (json.dumps("a" * 100), "'H'")), 57, "100 octets en H : 57 modules (version 10)")
    s.verifie((e["fond"], e["encre"], e["fond_qr"]), ("rgb(37, 37, 37)", "rgb(234, 234, 234)", "rgb(255, 255, 255)"),
              "theme sombre de Tasmota : texte clair sur fond sombre, QR code sur fond blanc")
    if capture:
        cdp.capture(Path(capture) / "qrcode_carte.png")

    e = charge(cdp, carte, url, {"reglage": reglage(ip_inscrite="192.168.0.61"), "etat": etat},
               "!document.getElementById('q_avert').hidden")
    s.verifie(e["avert"] is not None and "192.168.0.61" in e["avert"] and IP in e["avert"], True,
              "IP inscrite 192.168.0.61, carte en .60 : avertissement avec les deux IP")
    s.verifie(e["avert_couleurs"], ["rgb(0, 0, 0)", "rgb(232, 162, 0)"], "avertissement lisible : noir sur ambre")

    e = charge(cdp, carte, url, {"reglage": reglage(ip_inscrite="192.168.0.51:8081"), "etat": etat}, dessine)
    s.verifie((e["svg"], e["avert"]), (True, None), "IP inscrite 192.168.0.51:8081 (esclave par le maitre) : aucun avertissement")

    ancien = {k: v for k, v in reglage(ip_inscrite=None).items() if k != "entre_lignes"}   # qrcode.json d'avant la cle
    e = charge(cdp, carte, url, {"reglage": ancien, "etat": {"ip": "", "hostname": ""}}, dessine)
    s.verifie((e["svg"], e["avert"]), (True, None), "ni IP inscrite ni IP connue : QR code, aucun avertissement")
    s.verifie(e["texte"], TEXTE, "qrcode.json sans entre_lignes : texte affiche tel quel")

    hostile = "Note : </script><img src=x onerror=window.pirate=1>"
    e = charge(cdp, carte, url, {"reglage": reglage(texte=hostile), "etat": etat}, dessine)
    s.verifie((e["texte"], e["img"], e["pirate"]), (hostile, 0, False), "texte hostile affiche en texte, aucune image creee")

    s.verifie(carte.demandes.count("lib.js.gz"), 1, "bibliotheque demandee une seule fois en 5 chargements (cache localStorage)")
    s.verifie(cdp.erreurs(), [], "aucune erreur JS")

    # cas d'echec (les 404 voulus remplissent le journal de Chrome : plus de controle « aucune erreur » apres)
    e = charge(cdp, carte, url, {"reglage": reglage(ip_inscrite="192.168.0.61"), "etat": None}, dessine)
    s.verifie((e["svg"], e["avert"], e["msg_cache"]), (True, None, True), "f=etat en erreur : QR code affiche, sans avertissement ni erreur")
    erreur = "document.getElementById('q_msg').className === 'erreur'"
    e = charge(cdp, carte, url, {"reglage": None, "etat": etat}, erreur)
    s.verifie((e["svg"], e["erreur"], "404" in e["msg"]), (False, "erreur", True), "reglage absent : message d'erreur (HTTP 404), pas de QR code")
    e = charge(cdp, carte, url, {"reglage": {"version": 1, "style": {}}, "etat": etat}, erreur)
    s.verifie((e["svg"], "invalide" in e["msg"]), (False, True), "reglage sans texte : « Réglage du QR code invalide », pas de page vide")
    cdp.js("localStorage.clear()")
    e = charge(cdp, carte, url, {"reglage": reglage(), "etat": etat, "sans_lib": True}, erreur)
    s.verifie((e["svg"], "Bibliothèque absente" in e["msg"], "404" in e["msg"]), (False, True, True),
              "bibliotheque absente de la carte, cache vide : message (HTTP 404)")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page /qrcode de la carte.")
    options.add_argument("--capture", help="dossier ou ecrire la capture PNG")
    args = options.parse_args()
    chrome = next((c for c in s.CHROMES if c.is_file()), None)
    if chrome is None:
        print("BLOQUE : chrome.exe introuvable")
        return 3
    t = Path(tempfile.mkdtemp(prefix="sonde_qrc_"))
    proc, carte = None, None
    try:
        banc = subprocess.run([sys.executable, str(RACINE / "outils_docs/scripts_python/berry/banc_qrcode_page.py"),
                               "--garde", str(t / "banc")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if banc.returncode != 0 or not (t / "banc/page.html").is_file():
            print(banc.stdout[-2000:] + banc.stderr[-2000:])
            print("BLOQUE : la page n'a pas ete produite par le banc Berry")
            return 3
        carte = Carte((t / "banc/page.html").read_bytes())
        port_cdp = s.port_libre()
        proc = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={port_cdp}", "--remote-allow-origins=*",
                                 f"--user-data-dir={t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                 "--disable-extensions", "--window-size=800,900", "about:blank"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        limite, cibles = time.monotonic() + 20, None
        while cibles is None and time.monotonic() < limite:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port_cdp}/json/list", timeout=2) as r:
                    cibles = json.loads(r.read())
            except OSError:
                time.sleep(0.2)
        cdp = s.Cdp(next(c for c in cibles if c.get("type") == "page")["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            cdp.appel(domaine)
        sonde(cdp, carte, args.capture)
    except Exception as erreur:                              # noqa: BLE001
        s.verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
    finally:
        s.tue_arbre(proc)                                    # jamais de Chrome headless orphelin : l'arbre, puis tout le profil
        for _ in range(3):
            try:                                             # machine chargee : WMI peut depasser le delai, le verdict reste lisible
                subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -match '%s' }"
                                " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" % t.name],
                               capture_output=True, timeout=120)
            except subprocess.TimeoutExpired:
                print(f"     nettoyage : Chrome du profil {t.name} a verifier a la main", flush=True)
            time.sleep(0.5)
        if carte:
            carte.serveur.shutdown()
        shutil.rmtree(t, ignore_errors=True)
    print("\n" + ("VERT" if not s.ECHECS else f"ROUGE : {len(s.ECHECS)} echec(s) : {s.ECHECS}"))
    return 1 if s.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
