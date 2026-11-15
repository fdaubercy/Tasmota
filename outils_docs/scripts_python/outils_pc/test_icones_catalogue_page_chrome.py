"""Sonde Chrome de la page « Catalogue d'icones » (icones_catalogue_page.PAGE) : grille, recherche, fiche, copie, filtres, texte hostile, theme, telephone.

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~20 s par passage)
    python outils_docs/scripts_python/outils_pc/test_icones_catalogue_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET chaque temoin (meme page, une ligne changee) est detecte par SON test.

Serveur reel dans ce processus (127.0.0.1, port libre) sur un mini-depot temporaire (police MDI reelle copiee). Chrome headless arrete a la fin.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_icones_catalogue_page_chrome.py
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
import atelier_ecrans_icones as ic                                              # noqa: E402
import icones_catalogue_page as page_mod                                        # noqa: E402
import icones_catalogue_web as web                                              # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402
from test_icones_catalogue import monte                                         # noqa: E402

DEPOT = ICI.parents[2]
ECHECS = []
HOSTILE = "<img src=x onerror=window.__pwn=1>"
CODE = "\\uE335"
PAGE_ORIGINALE = page_mod.PAGE
TEMOINS = {       # nom -> (texte de la page, remplacement, verification qui doit echouer)
    "innerHTML": ("if (texte != null) e.textContent = texte;", "if (texte != null) e.innerHTML = texte;", "hostile : le texte reste du texte, aucune balise creee"),
    "recherche-nom": ("norme(g.nom).indexOf(f.q) >= 0 ||", "true ||", "recherche : « lamp » ne garde que la lampe"),
    "copie-code": ("copie(codeServi(i))", "copie(i.nom)", "copie : le code est copie"),
}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


class Montage:
    def __init__(self, page):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_icones_"))
        self.chrome = self.serveur = None
        racine = self.t / "depot"
        monte(racine)
        md = racine / "outils_docs" / "ICONES_IMAGES_SOURCES.md"
        md.write_text(md.read_text(encoding="utf-8") + f"\n## 3. Hostile\n\n| Site | Pourquoi |\n|---|---|\n| {HOSTILE} | texte <b>gras</b> |\n", encoding="utf-8")
        police = racine / ic.TTF
        police.parent.mkdir(parents=True)
        shutil.copyfile(DEPOT / ic.TTF, police)
        page_mod.PAGE = page
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        acces = acces_web.Acces(self.port, True, "Catalogue d'icones")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), web.fabrique_gestionnaire(acces, racine))
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
        cible = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(cible["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable", "Network.enable"):
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
        if self.t:           # Chrome relance des fils pendant son arret : on balaie par le profil de cette sonde
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
        if self.t:
            shutil.rmtree(self.t, ignore_errors=True)


def saisit(cdp, ident, valeur):
    cdp.js("(function(){var e=document.getElementById(" + json.dumps(ident) + "); e.value=" + json.dumps(valeur)
           + "; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));})()")


def visibles(cdp):
    return cdp.js("[document.getElementById('s-png').hidden, document.getElementById('s-firmware').hidden, document.getElementById('s-sites').hidden].join()")


def scenario(m):
    cdp = m.cdp
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    cdp.appel("Page.navigate", url=m.url)
    verifie(bool(attend(cdp, "document.querySelectorAll('#grille button').length > 0", 15)), True, "page chargee, grille remplie")
    verifie(cdp.js("document.title"), "Catalogue d'icônes", "titre")
    verifie(cdp.js("document.querySelectorAll('#grille button').length"), 4, "une case par glyphe du catalogue")
    verifie(bool(attend(cdp, "document.fonts.check('28px MDI')", 10)), True, "police MDI locale chargee")
    verifie(cdp.js("document.getElementById('s-fiche').hidden"), True, "fiche cachee au depart")
    verifie(cdp.js("document.getElementById('n-absentes').textContent"), "(2)", "absentes : 2 codes hors catalogue")

    # recherche par nom
    saisit(cdp, "recherche", "lamp")
    verifie(cdp.js("Array.prototype.map.call(document.querySelectorAll('#grille button'),function(b){return b.getAttribute('data-nom')}).join(',')"), "lamp",
            "recherche : « lamp » ne garde que la lampe")
    saisit(cdp, "recherche", "")
    verifie(cdp.js("document.querySelectorAll('#grille button').length"), 4, "recherche videe : tout revient")

    # fiche et copie
    cdp.js("document.querySelector('#grille button[data-nom=lightbulb]').click()")
    verifie(cdp.js("document.getElementById('s-fiche').hidden"), False, "clic : la fiche s'ouvre")
    verifie(cdp.js("[document.getElementById('f-code').textContent, document.getElementById('f-nom').textContent, document.getElementById('f-mdi').textContent].join(' ')"),
            CODE + " lightbulb F0335", "fiche : code a copier, nom et code MDI")
    verifie(cdp.js("document.querySelectorAll('#f-usages li').length"), 3, "fiche : 3 usages")
    verifie(cdp.js("document.getElementById('f-lien').getAttribute('href')"), "https://pictogrammers.com/library/mdi/icon/lightbulb/", "fiche : lien pictogrammers")
    verifie(cdp.js("document.getElementById('f-polices').textContent.indexOf('montserrat-28') >= 0"), True, "fiche : police recommandee")
    cdp.js("window.__copie=null; Object.defineProperty(navigator,'clipboard',{value:{writeText:function(t){window.__copie=t;return Promise.resolve();}},configurable:true})")
    cdp.js("document.getElementById('f-copie').click()")
    verifie(bool(attend(cdp, "window.__copie !== null", 5)), True, "copie : writeText appele")
    verifie(cdp.js("window.__copie"), CODE, "copie : le code est copie")
    verifie(bool(attend(cdp, "document.getElementById('f-copie-etat').textContent.indexOf('Copié') === 0", 5)), True, "copie : confirmation affichee")

    # filtres par source
    saisit(cdp, "source", "png")
    verifie(visibles(cdp), "false,true,true", "source PNG : seule la liste des PNG")
    verifie(cdp.js("document.querySelectorAll('#pngs tr').length"), 3, "PNG : en-tete et 2 fichiers")
    verifie(cdp.js("document.querySelector('#pngs tr:nth-child(2)').textContent.indexOf('16 × 32') >= 0"), True, "PNG : taille affichee")
    saisit(cdp, "source", "sites")
    verifie(visibles(cdp), "true,true,false", "source Sites : seule la liste des sites")
    verifie(cdp.js("document.querySelector('#sites a').getAttribute('href')"), "https://pictogrammers.com/library/mdi/", "sites : lien externe cliquable")
    verifie(cdp.js("document.querySelector('#sites a').getAttribute('rel')"), "noopener noreferrer", "sites : rel sur le lien externe")
    verifie(cdp.js("document.querySelectorAll('#sites img, #sites b').length === 0 && window.__pwn === undefined"), True,
            "hostile : le texte reste du texte, aucune balise creee")
    verifie(cdp.js("document.getElementById('sites').textContent.indexOf(" + json.dumps(HOSTILE) + ") >= 0"), True, "hostile : affiche tel quel")
    saisit(cdp, "source", "")
    verifie(visibles(cdp), "false,false,false", "source toutes : tout est visible")

    # aucune requete hors de ce serveur
    with cdp.condition:
        urls = [e["params"]["request"]["url"] for e in cdp.evenements if e.get("method") == "Network.requestWillBeSent"]
    externes = [u for u in urls if not (u.startswith(m.url.rstrip("/")) or u.startswith("data:"))]
    verifie(externes, [], "aucune requete externe")
    verifie(len(urls) >= 3, True, "requetes observees (page, catalogue, police)")

    # theme : sombre si le systeme le demande, choix memorise
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
    cdp.js("try{localStorage.clear()}catch(e){}")
    cdp.appel("Page.reload")
    attend(cdp, "document.querySelectorAll('#grille button').length > 0", 15)
    verifie(cdp.js("document.documentElement.getAttribute('data-theme')"), "sombre", "theme : sombre quand le systeme est sombre")
    cdp.js("var c=document.getElementById('theme'); c.checked=false; c.dispatchEvent(new Event('change',{bubbles:true}))")
    cdp.appel("Page.reload")
    attend(cdp, "document.querySelectorAll('#grille button').length > 0", 15)
    verifie(cdp.js("document.documentElement.getAttribute('data-theme')"), "clair", "theme : choix memorise au rechargement")

    # telephone
    cdp.appel("Emulation.setDeviceMetricsOverride", width=375, height=800, deviceScaleFactor=1, mobile=True)
    verifie(bool(attend(cdp, "document.documentElement.scrollWidth <= window.innerWidth + 1", 5)), True, "telephone : pas de defilement horizontal")
    verifie(cdp.erreurs(), [], "aucune erreur de page (exception, console.error, CSP)")


def passage(page):
    m = Montage.__new__(Montage)          # ferme() nettoie meme si __init__ plante apres avoir lance Chrome
    m.t = m.chrome = m.serveur = None
    try:
        m.__init__(page)
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
            detecte = libelle in ECHECS
            print(("OK   " if detecte else "KO   ") + f"temoin {nom} detecte par son test")
            if not detecte:
                return 1
        ECHECS.clear()
    print("VERT : icones_catalogue_page_chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
