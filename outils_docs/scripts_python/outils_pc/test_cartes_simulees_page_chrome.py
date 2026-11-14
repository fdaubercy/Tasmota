"""Sonde Chrome de la page « Cartes simulees » (cartes_simulees_page.PAGE) : liste, lancer, arreter, carte en ligne refusee, texte hostile, theme sombre, telephone.

UTILISATION (a la main ; aucun pio, aucune carte, aucun berry.exe : fausses simulations ; Chrome tourne ~20 s par passage)
    python outils_docs/scripts_python/outils_pc/test_cartes_simulees_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET chaque temoin (meme page, une ligne changee) est detecte par SON test.

Serveur reel dans ce processus (127.0.0.1, port libre) ; le lancement d'une carte demarre un faux serveur sur un port libre (jamais 8082).
Chrome headless arrete a la fin. Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> <ce fichier>
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

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import acces_web                                                                # noqa: E402
import cartes_simulees as cs                                                    # noqa: E402
import cartes_simulees_page as page_mod                                         # noqa: E402
import cartes_simulees_web as web                                               # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402

ECHECS = []
RIDEAU = "tasmota32s3-garage-rideau-garage-modbus"
CUVE = "tasmota32s3-garage-capteurs-cuve-modbus"
HOSTILE = "<img src=x onerror=window.__pwn=1> & <b>gras</b>"
PAGE_ORIGINALE = page_mod.PAGE
PROFIL_ORIGINAL = cs.profil_reseau
TEMOINS = {       # nom -> (texte de la page, remplacement, verification qui doit echouer)
    "innerHTML": ("b.textContent=c.nom", "b.innerHTML=c.nom", "hostile : le nom reste du texte, aucune balise creee"),
    "bouton-arreter": ("c.lancee?'Arrêter':'Lancer'", "'Lancer'", "carte lancee : le bouton devient Arrêter"),
    "message-rouge": ("m.className=ko?'ko':''", "m.className=''", "refus : message affiche en rouge"),
}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


LIGNE = ("Array.prototype.filter.call(document.querySelectorAll('.carte'),function(d){var s=d.querySelector('.nom span');"
         "return s&&s.textContent.indexOf(%s)===0})[0]")


def ligne_js(env):
    return LIGNE % json.dumps(env)


def clic_bouton(cdp, env, texte):
    return cdp.js("(function(){var d=" + ligne_js(env) + ";if(!d) return 'ligne absente';var b=Array.prototype.filter.call(d.querySelectorAll('button'),"
                  "function(x){return x.textContent===" + json.dumps(texte) + "})[0];if(!b) return 'bouton absent';b.click();return 'ok'})()")


class FauxHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"faux")

    def log_message(self, format, *args):  # noqa: A002
        pass


class Montage:
    def __init__(self, page):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_cartes_"))
        self.chrome = self.serveur = self.etat = None
        page_mod.PAGE = page
        cs.profil_reseau = lambda env: dict(PROFIL_ORIGINAL(env), nom=HOSTILE) if env == RIDEAU else PROFIL_ORIGINAL(env)
        adresses_en_ligne = {cs.inventaire()[CUVE]["adresse"]}
        self.etat = web.Etat(test_en_ligne=lambda a: a in adresses_en_ligne, fabrique=lambda env, port: ThreadingHTTPServer(("127.0.0.1", 0), FauxHandler))
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        self.acces = acces_web.Acces(self.port, True, "Cartes simulees")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), web.fabrique_gestionnaire(self.acces, self.etat))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable")
        self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}", "--remote-allow-origins=*",
                                        f"--user-data-dir={self.t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                        "--disable-extensions", "--window-size=1280,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        page_cdp = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(page_cdp["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)

    @staticmethod
    def _attend(url, delai):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    return r.read().decode("utf-8")
            except OSError:
                time.sleep(0.2)
        raise TimeoutError(f"{url} ne repond pas")

    def ferme(self):
        if self.chrome:
            tue_arbre(self.chrome)
        if self.t:           # Chrome laisse des processus fils, parfois relances : on balaie par le profil de cette sonde
            commande = ("$p = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*" + self.t.name
                        + "*' }); $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $p.Count")
            for _ in range(8):
                r = subprocess.run(["powershell", "-NoProfile", "-Command", commande], capture_output=True, text=True)
                if r.stdout.strip() == "0":
                    break
                time.sleep(0.7)
        if self.etat:
            self.etat.arrete_tout()
        if self.serveur:
            self.serveur.shutdown()
            self.serveur.server_close()
        page_mod.PAGE = PAGE_ORIGINALE
        cs.profil_reseau = PROFIL_ORIGINAL
        shutil.rmtree(self.t, ignore_errors=True)


def scenario(m, temoin):
    cdp = m.cdp
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    cdp.appel("Page.navigate", url=m.url)
    verifie(bool(attend(cdp, "document.querySelectorAll('.carte').length > 0", 15)), True, "page chargee, cartes listees")
    verifie(cdp.js("document.querySelectorAll('.carte').length >= 13"), True, "au moins 13 cartes")
    verifie(cdp.js("document.title"), "Cartes simulées", "titre")
    verifie(cdp.js("document.querySelectorAll('.badge.on').length"), 0, "aucune carte simulee au depart")

    # texte hostile : du texte, jamais du HTML
    verifie(cdp.js("document.querySelectorAll('.carte img, .carte b b').length === 0 && window.__pwn === undefined"), True,
            "hostile : le nom reste du texte, aucune balise creee")

    # lancer le rideau
    verifie(clic_bouton(cdp, RIDEAU, "Lancer"), "ok", "clic sur Lancer (rideau)")
    verifie(bool(attend(cdp, "!!(" + ligne_js(RIDEAU) + ") && !!" + ligne_js(RIDEAU) + ".querySelector('.badge.on')", 15)), True, "rideau lance : badge « simulée »")
    verifie(cdp.js("(function(){var a=" + ligne_js(RIDEAU) + ".querySelector('a.btn');return !!a && /^http:\\/\\/127\\.0\\.0\\.1:\\d+\\/$/.test(a.getAttribute('href'))})()"),
            True, "lien « Ouvrir » vers 127.0.0.1")
    verifie(cdp.js("(function(){var b=Array.prototype.map.call(" + ligne_js(RIDEAU) + ".querySelectorAll('button'),function(x){return x.textContent});return b.join()})()"),
            "Arrêter", "carte lancee : le bouton devient Arrêter")

    # carte en ligne : refus, message rouge
    verifie(clic_bouton(cdp, CUVE, "Lancer"), "ok", "clic sur Lancer (carte en ligne)")
    verifie(bool(attend(cdp, "!document.getElementById('msg').hidden", 15)), True, "refus : message affiche")
    verifie("ne se simule pas" in (cdp.js("document.getElementById('msg').textContent") or ""), True, "refus : texte du serveur")
    verifie(cdp.js("document.getElementById('msg').className"), "ko", "refus : message affiche en rouge")
    verifie(cdp.js("!!" + ligne_js(CUVE) + ".querySelector('.badge.on')"), False, "carte en ligne : toujours pas simulee")

    # arreter le rideau
    verifie(clic_bouton(cdp, RIDEAU, "Arrêter"), "ok", "clic sur Arrêter")
    verifie(bool(attend(cdp, "!" + ligne_js(RIDEAU) + ".querySelector('.badge.on')", 15)), True, "rideau arrete : badge disparu")
    verifie(cdp.js(ligne_js(RIDEAU) + ".querySelector('a.btn') === null"), True, "rideau arrete : plus de lien « Ouvrir »")

    # theme sombre : le fond change avec le theme du systeme
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
    time.sleep(0.4)
    clair = cdp.js("getComputedStyle(document.body).backgroundColor")
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
    time.sleep(0.4)
    sombre = cdp.js("getComputedStyle(document.body).backgroundColor")
    verifie([clair, sombre], ["rgb(246, 247, 249)", "rgb(18, 20, 23)"], "theme : fond clair puis sombre selon le systeme")
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])

    # telephone : pas de defilement horizontal
    cdp.appel("Emulation.setDeviceMetricsOverride", width=375, height=800, deviceScaleFactor=1, mobile=True)
    time.sleep(0.5)
    verifie(cdp.js("document.documentElement.scrollWidth <= window.innerWidth + 1"), True, "telephone : pas de defilement horizontal")

    if not temoin:
        # le 409 du refus « carte en ligne » est voulu : Chrome le journalise en erreur
        verifie([e for e in cdp.erreurs() if "409" not in e], [], "aucune erreur de page (exception, console.error)")


def passage(page, temoin=None):
    m = Montage.__new__(Montage)          # ferme() nettoie meme si __init__ plante apres avoir lance Chrome
    m.t = m.chrome = m.serveur = m.etat = None
    try:
        m.__init__(page)
        scenario(m, temoin)
    finally:
        m.ferme()


def main():
    opt = argparse.ArgumentParser()
    opt.add_argument("--sans-temoin", action="store_true")
    args = opt.parse_args()
    print("== passage normal")
    passage(PAGE_ORIGINALE)
    if ECHECS:
        print(f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}")
        return 1
    if not args.sans_temoin:
        for nom, (ancien, nouveau, libelle) in TEMOINS.items():
            if PAGE_ORIGINALE.count(ancien) != 1:
                print(f"KO   temoin {nom} : texte a changer introuvable ou multiple")
                return 1
            print(f"== temoin {nom} (doit echouer sur : {libelle})")
            ECHECS.clear()
            passage(PAGE_ORIGINALE.replace(ancien, nouveau), temoin=nom)
            detecte = libelle in ECHECS
            print(("OK   " if detecte else "KO   ") + f"temoin {nom} detecte par son test")
            if not detecte:
                return 1
        ECHECS.clear()
    print("VERT : cartes_simulees_page_chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
