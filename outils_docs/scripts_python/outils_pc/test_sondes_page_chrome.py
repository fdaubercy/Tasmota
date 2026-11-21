"""Sonde Chrome de la page « Sondes en cours » : cartes, avancement reel qui bouge entre deux releves, texte hostile, bouton a deux temps, mode sombre, telephone.

UTILISATION (a la main ; AUCUN vrai processus lu ni arrete : faux scan, faux arret, dossier de suivi temporaire ; Chrome ~15 s par passage)
    python outils_docs/scripts_python/outils_pc/test_sondes_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET chaque temoin (meme page, une ligne changee) est detecte par SON test.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_sondes_page_chrome.py
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
from http.server import ThreadingHTTPServer
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import acces_web                                                                # noqa: E402
import sonde_hermetique                                                         # noqa: E402
import sondes_page as page_mod                                                  # noqa: E402
import sondes_web as sw                                                         # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402

ECHECS = []
HOSTILE = '<img src=x onerror="window.__pwn=1"><b>gras</b>'
PAGE_ORIGINALE = page_mod.PAGE
TEMOINS = {
    "innerHTML": ("if (texte != null) e.textContent = texte;", "if (texte != null) e.innerHTML = texte;", "hostile : nom, phase et echecs restent du texte"),
    "deux-temps": ("if (!armes[cle]) {", "if (false) {", "arreter : le 1er clic arme seulement"),
    "detail-clic": ("t.onclick = function () { if (ouvertes[s.pid])", "t.onclick = function () { if (false)", "detail : un clic sur la carte deplie le journal"),
    "en-tete": ('"X-Sondes": "1"', '"X-Autre": "1"', "arreter : l'en-tete X-Sondes part avec le POST"),
}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def fichier(pid, nom, faits, echecs=(), etat="en_cours", phase="phase 1", dernier="OK   dernier cas"):
    return {"pid": pid, "parent": 1, "nom": nom, "script": "", "debut": time.time() - 50, "maj": time.time(), "total": 10, "faits": faits,
            "echecs": list(echecs), "phase": phase, "dernier": dernier, "etat": etat}


class Montage:
    def __init__(self, page):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_sondes_"))
        self.chrome = self.serveur = None
        self.suivi = self.t / "suivi"
        self.suivi.mkdir()
        self.ecrit(fichier(20, "test_alpha", 4, ["KO   premier echec"], phase=HOSTILE, dernier=HOSTILE))
        self.ecrit(fichier(30, HOSTILE, 10, etat="termine"))
        self.procs = [{"pid": 10, "parent": 5, "nom": "chrome.exe", "ligne": "chrome.exe --user-data-dir=C:\\T\\sonde_orph --headless", "debut": 1},
                      {"pid": 20, "parent": 6, "nom": "python.exe", "ligne": "python.exe test_alpha.py", "debut": 1},
                      {"pid": 21, "parent": 6, "nom": "python.exe", "ligne": "python.exe banc_beta.py", "debut": 1}]
        self.tues = []
        page_mod.PAGE = page
        self.etat = sw.Etat(ps=lambda: self.procs, vivant=lambda pid: pid in (6, 10, 20, 21), dossier=self.suivi, cache_s=0,
                            tue=lambda pid: (self.tues.append(pid) or True, "ok"),
                            relit=lambda pid: next((dict(p) for p in self.procs if p["pid"] == pid), None))   # relecture neuve avant arret : la liste du banc, jamais PowerShell
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        sonde_hermetique.neutralise_barre()   # la barre de habille() ne lit ni les vraies fiches ni :7700
        acces = acces_web.Acces(self.port, True, "Sondes en cours")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), sw.fabrique_gestionnaire(acces, self.etat))
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
        liste = self._attend(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        self.cdp = Cdp(next(c for c in json.loads(liste) if c.get("type") == "page")["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)

    def ecrit(self, f):
        (self.suivi / f"{f['pid']}.json").write_text(json.dumps(f), encoding="utf-8")

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
        if self.t:           # Chrome relance des fils pendant son arret : balayage par le profil de CETTE sonde
            commande = ("$p = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*" + self.t.name
                        + "*' }); $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $p.Count")
            for _ in range(8):
                r = subprocess.run(["powershell", "-NoProfile", "-Command", commande], capture_output=True, text=True)
                if r.stdout.strip() == "0":
                    break
                time.sleep(0.7)
        if self.serveur:
            self.serveur.shutdown()
            self.serveur.server_close()
        page_mod.PAGE = PAGE_ORIGINALE
        shutil.rmtree(self.t, ignore_errors=True)


def scenario(m):
    cdp = m.cdp
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    cdp.appel("Page.navigate", url=m.url)
    verifie(bool(attend(cdp, "document.querySelectorAll('.sonde').length >= 4", 20)), True, "page chargee : 4 cartes (orpheline, 2 en cours/sans suivi, 1 terminee)")
    verifie(cdp.js("document.title"), "Sondes en cours", "titre")
    verifie(cdp.js("document.getElementById('bandeau').className"), "bandeau rouge", "bandeau rouge (Chrome orphelin, sonde en cours avec un echec)")
    verifie(cdp.js("document.querySelectorAll('.sonde.orpheline').length"), 1, "la carte orpheline est mise en evidence")
    verifie(cdp.js("document.getElementById('orph').children.length"), 1, "bouton « Arreter les orphelines » present")
    carte20 = "Array.prototype.find.call(document.querySelectorAll('.sonde'), function(c){return c.textContent.indexOf('test_alpha') >= 0;})"
    verifie(cdp.js(carte20 + ".querySelector('.barre > i').style.width"), "40%", "avancement reel : barre a 40 % (4 / 10)")
    verifie(cdp.js(carte20 + ".textContent.indexOf('4 / 10') >= 0 && " + carte20 + ".textContent.indexOf('premier echec') >= 0"), True, "faits, total et echec listes")
    verifie(cdp.js("document.body.textContent.indexOf(" + json.dumps(HOSTILE) + ") >= 0"), True, "hostile (nom, phase, dernier cas) affiche tel quel, comme du texte")
    verifie(cdp.js("document.querySelectorAll('main img, main b').length === 0 && window.__pwn === undefined"), True, "hostile : aucune balise creee, aucun script")
    # -- une sonde qui avance entre deux releves --------------------------------------------------
    f20 = fichier(20, "test_alpha", 9, ["KO   premier echec", "KO   second echec"], phase="phase 2", dernier="OK   cas neuf")
    f20["phases"] = [{"nom": "phase 1", "t": 1, "faits": 4, "echecs": 1}, {"nom": "phase 2", "t": 70, "faits": 5, "echecs": 1}]
    f20["journal"] = [[1, "phase", "== phase 1"], [2, "ok", "OK   cas un"], [3, "ko", "KO   " + HOSTILE], [70, "phase", "== phase 2"]]
    m.ecrit(f20)
    verifie(bool(attend(cdp, carte20 + ".textContent.indexOf('9 / 10') >= 0", 15)), True, "la page se rafraichit seule : 9 / 10")
    verifie(cdp.js(carte20 + ".querySelector('.barre > i').style.width + '|' + " + carte20 + ".querySelectorAll('ul.echecs li').length"), "90%|2", "barre a 90 %, deux echecs")
    verifie(cdp.js(carte20 + ".textContent.indexOf('phase 2') >= 0 && " + carte20 + ".textContent.indexOf('cas neuf') >= 0"), True, "phase et dernier cas a jour")
    # -- detail au clic ---------------------------------------------------------------------------
    verifie(cdp.js(carte20 + ".querySelector('.detail')"), None, "detail : replie par defaut")
    cdp.js(carte20 + ".querySelector('.tete').click()")
    verifie(bool(attend(cdp, carte20 + ".querySelectorAll('.journal > div').length === 4", 15)), True, "detail : un clic sur la carte montre les 4 lignes du journal")
    verifie(cdp.js(carte20 + ".querySelectorAll('table.phases tr').length"), 3, "detail : tableau des phases (en-tete + 2)")
    verifie(cdp.js(carte20 + ".querySelector('.journal .ko').textContent.indexOf(" + json.dumps(HOSTILE) + ") >= 0 && !" + carte20 + ".querySelector('.journal img')"), True,
            "detail : ligne hostile du journal en texte, sans balise")
    time.sleep(2.6)       # un rafraichissement passe : le detail reste deplie
    verifie(cdp.js(carte20 + ".querySelectorAll('.journal > div').length"), 4, "detail : reste deplie apres le rafraichissement de 2 s")
    cdp.js(carte20 + ".querySelector('.tete').click()")
    verifie(bool(attend(cdp, carte20 + ".querySelector('.detail') === null", 15)), True, "detail : un second clic le replie")
    # -- bouton a deux temps ----------------------------------------------------------------------
    btn = lambda c: "(" + c + ").querySelector('button')"
    cdp.js(btn(carte20) + ".click()")
    verifie(cdp.js(btn(carte20) + ".textContent.indexOf('Confirmer') === 0"), True, "arreter : le 1er clic arme seulement")
    verifie(len(m.tues), 0, "arreter : le 1er clic n'arrete rien")
    time.sleep(2.6)       # un rafraichissement passe : l'armement survit
    verifie(cdp.js(btn(carte20) + ".textContent.indexOf('Confirmer') === 0"), True, "arreter : l'armement survit au rafraichissement de 2 s")
    cdp.js(btn(carte20) + ".click()")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('Arrêtés : 20') >= 0", 15)), True, "arreter : le 2e clic confirme et le dit")
    verifie(m.tues, [20], "arreter : un seul arret, du pid de la carte")
    cdp.js("document.querySelector('#orph button').click()")
    verifie(len(m.tues), 1, "orphelines : le 1er clic n'arrete rien")
    cdp.js("document.querySelector('#orph button').click()")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('10') >= 0", 15)), True, "orphelines : le 2e clic arrete le Chrome orphelin")
    verifie(m.tues, [20, 10], "orphelines : seul le pid 10 s'ajoute")
    # -- thème et telephone -------------------------------------------------------------------------
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
    verifie(cdp.js("getComputedStyle(document.body).backgroundColor"), "rgb(18, 20, 23)", "mode sombre : fond sombre")
    cdp.appel("Emulation.setDeviceMetricsOverride", width=390, height=800, deviceScaleFactor=2, mobile=True)
    time.sleep(0.5)
    verifie(cdp.js("document.documentElement.scrollWidth <= window.innerWidth"), True, "telephone : aucun defilement horizontal")


def passage(page):
    m = Montage(page)
    try:
        scenario(m)
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
            passage(PAGE_ORIGINALE.replace(ancien, nouveau))
            detecte = bool(ECHECS)
            print(("OK   " if detecte else "KO   ") + f"temoin {nom} detecte")
            if not detecte:
                return 1
        ECHECS.clear()
    print("VERT : sondes_page_chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
