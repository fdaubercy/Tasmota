"""Sonde Chrome de la page « Menage du depot » (menage_page.PAGE) : parametres, audit, rapport, filtres, garder / ignorer, texte hostile, theme, telephone.

UTILISATION (a la main ; aucun pio, aucune carte, faux `claude` ; Chrome tourne ~30 s par passage)
    python outils_docs/scripts_python/outils_pc/test_menage_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET chaque temoin (meme page, une ligne changee) est detecte par SON test.

Serveur reel dans ce processus (127.0.0.1, port libre), depot et dossier de donnees temporaires, faux `claude`. Chrome headless arrete a la fin.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_menage_page_chrome.py
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
import menage_page                                                              # noqa: E402
import menage_web as mw                                                         # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402

ECHECS = []
HOSTILE = "<img src=x onerror=window.__pwn=1> & <b>gras</b>"
PAGE_ORIGINALE = menage_page.PAGE
TEMOINS = {       # nom -> (texte de la page, remplacement, verification qui doit echouer)
    "innerHTML": ("if (texte != null) e.textContent = texte;", "if (texte != null) e.innerHTML = texte;", "hostile : le texte reste du texte, aucune balise creee"),
    "en-cours-actions": ("if (!p.en_cours) {", "if (true) {", "en cours : aucun bouton Garder ni Ignorer"),
    "pas-de-filtre-risque": ("(!risque || p.risque === risque)", "true", "filtre risque : seule la proposition du risque choisi"),
}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def clic(cdp, ident):
    return cdp.js(f"(function(){{var e=document.getElementById({json.dumps(ident)}); if(!e) return 'absent'; e.click(); return 'ok';}})()")


def clic_bouton(cdp, zone, texte, rang=0):
    """Clique le `rang`-ieme bouton de `texte` dans `zone` (selecteur CSS)."""
    return cdp.js("(function(){var b=Array.prototype.filter.call(document.querySelectorAll(" + json.dumps(zone + " button") + "),"
                  "function(x){return x.textContent===" + json.dumps(texte) + "});if(!b[" + str(rang) + "]) return 'absent'; b[" + str(rang) + "].click(); return 'ok';})()")


def faux_claude(dossier):
    f = dossier / "faux_claude.py"
    props = [
        {"id": "M1", "categorie": "reste", "chemin": "tasks/README.md", "constat": HOSTILE, "preuve": "git log", "action": "archiver",
         "casserait": "rien", "risque": "faible", "en_cours": False},
        {"id": "M2", "categorie": "orphelin", "chemin": "tasks/autre.md", "constat": "second", "preuve": "grep", "action": "supprimer",
         "casserait": "le cenv", "risque": "eleve", "en_cours": False},
        {"id": "M3", "categorie": "doublon", "chemin": "tasks/encours.md", "constat": "travail en cours", "preuve": "git status",
         "action": "supprimer", "casserait": "tout", "risque": "moyen", "en_cours": True},
    ]
    rapport = json.dumps({"resume": "3 propositions", "non_verifie": "rien de grave", "propositions": props})
    f.write_text("import json, sys\nsys.stdin.buffer.read()\nprint(json.dumps({'is_error': False, 'result': " + repr(rapport) + "}))\n", encoding="utf-8")
    return f


class Montage:
    def __init__(self, page):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_menage_"))
        self.chrome = self.serveur = None
        racine = self.t / "depot"
        (racine / "tasks").mkdir(parents=True)
        for n in ("README.md", "autre.md", "encours.md"):
            (racine / "tasks" / n).write_text("x", encoding="utf-8")
        menage_page.PAGE = page
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        self.acces = acces_web.Acces(self.port, True, "Menage du depot")
        etat = mw.Etat(racine, lambda: [], programme=[sys.executable, str(faux_claude(self.t))], dossier=self.t / "donnees", delai=30)
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), mw.fabrique_gestionnaire(self.acces, etat))
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
            for _ in range(8):      # jusqu'a ce qu'un balayage ne trouve plus rien (Chrome relance des fils pendant son arret)
                r = subprocess.run(["powershell", "-NoProfile", "-Command", commande], capture_output=True, text=True)
                if r.stdout.strip() == "0":
                    break
                time.sleep(0.7)
        if self.serveur:
            self.serveur.shutdown()
            self.serveur.server_close()
        menage_page.PAGE = PAGE_ORIGINALE
        shutil.rmtree(self.t, ignore_errors=True)


def scenario(m, temoin):
    cdp = m.cdp
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    cdp.appel("Page.navigate", url=m.url)
    verifie(bool(attend(cdp, "document.querySelectorAll('#p-zone input').length > 0", 15)), True, "page chargee, options remplies")
    verifie(cdp.js("document.querySelectorAll('#p-zone input').length"), len(mw.ml.ZONES), "une case par dossier")
    verifie(cdp.js("document.querySelectorAll('#p-cat input').length"), 7, "une case par controle")
    verifie(cdp.js("document.title"), "Ménage du dépôt", "titre")
    verifie(cdp.js("document.getElementById('b-copie').disabled"), True, "copier grise sans rapport")

    cdp.js("document.querySelectorAll('#p-zone input').forEach(function(c){c.checked=false})")
    clic(cdp, "b-lance")
    verifie("Cochez" in (cdp.js("document.getElementById('etat').textContent") or ""), True, "aucun dossier coche : refus cote page")
    cdp.js("document.querySelectorAll('#p-zone input').forEach(function(c){c.checked=true})")

    clic(cdp, "b-lance")
    verifie(bool(attend(cdp, "document.getElementById('etat').textContent.indexOf('terminé') >= 0", 40)), True, "audit termine")
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length > 0", 15)), True, "rapport affiche apres l'audit")
    verifie(cdp.js("document.querySelectorAll('#props .prop').length"), 2, "2 propositions actives")
    verifie(cdp.js("document.getElementById('n-props').textContent"), "(2)", "compteur des propositions")
    verifie(cdp.js("document.querySelector('#props .prop .chemin').textContent"), "tasks/README.md", "tri par risque : la faible d'abord")
    verifie(cdp.js("document.getElementById('resume').textContent"), "3 propositions", "resume affiche")
    verifie(cdp.js("document.getElementById('b-copie').disabled"), False, "copier actif avec un rapport")

    # texte hostile : du texte, jamais du HTML
    verifie(cdp.js("document.querySelectorAll('#props img, #props b').length === 0 && window.__pwn === undefined"), True,
            "hostile : le texte reste du texte, aucune balise creee")
    verifie(cdp.js("document.querySelector('#props .prop p').textContent"), HOSTILE, "hostile : affiche tel quel")

    # en cours : replie, sans boutons
    verifie(cdp.js("document.getElementById('encours').hidden"), False, "bloc « en cours » visible")
    verifie(cdp.js("document.querySelectorAll('#props-encours .prop').length"), 1, "1 proposition en cours")
    verifie(cdp.js("document.querySelectorAll('#props-encours button').length"), 0, "en cours : aucun bouton Garder ni Ignorer")

    # filtres
    cdp.js("var s=document.getElementById('f-risque'); s.value='eleve'; s.dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(cdp.js("Array.prototype.map.call(document.querySelectorAll('#props .chemin'),function(e){return e.textContent}).join(',')"),
            "tasks/autre.md", "filtre risque : seule la proposition du risque choisi")
    cdp.js("var s=document.getElementById('f-risque'); s.value=''; s.dispatchEvent(new Event('change',{bubbles:true}))")
    cdp.js("var s=document.getElementById('f-cat'); s.value='reste'; s.dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(cdp.js("document.querySelectorAll('#props .prop').length"), 1, "filtre categorie")
    cdp.js("var s=document.getElementById('f-cat'); s.value=''; s.dispatchEvent(new Event('change',{bubbles:true}))")

    # ignorer, garder, retirer
    clic_bouton(cdp, "#props", "Ignorer cette fois", 0)
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length === 1", 10)), True, "ignorer : la proposition disparait")
    clic_bouton(cdp, "#props", "Garder", 0)
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length === 0", 10)), True, "garder : la proposition disparait")
    verifie(bool(attend(cdp, "document.getElementById('gardes').textContent.indexOf('tasks/autre.md') >= 0", 10)), True, "garder : listee dans « Gardes »")
    verifie(cdp.js("document.getElementById('n-gardes').textContent"), "(1)", "compteur des gardes")
    clic_bouton(cdp, "#gardes", "Retirer", 0)
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length === 1", 10)), True, "retirer : la proposition revient")

    # theme
    cdp.js("var c=document.getElementById('theme'); c.checked=!c.checked; c.dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(cdp.js("document.documentElement.getAttribute('data-theme')") in ("clair", "sombre"), True, "theme pose")
    avant = cdp.js("document.documentElement.getAttribute('data-theme')")
    cdp.appel("Page.reload")
    attend(cdp, "document.querySelectorAll('#p-zone input').length > 0", 15)
    verifie(cdp.js("document.documentElement.getAttribute('data-theme')"), avant, "theme memorise au rechargement")

    # telephone : pas de defilement horizontal
    cdp.appel("Emulation.setDeviceMetricsOverride", width=375, height=800, deviceScaleFactor=1, mobile=True)
    time.sleep(0.5)
    verifie(cdp.js("document.documentElement.scrollWidth <= window.innerWidth + 1"), True, "telephone : pas de defilement horizontal")

    verifie(cdp.erreurs(), [], "aucune erreur de page (exception, console.error)") if not temoin else None


def passage(page, temoin=None):
    m = Montage.__new__(Montage)          # ferme() nettoie meme si __init__ plante apres avoir lance Chrome
    m.t = m.chrome = m.serveur = None
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
    print("VERT : menage_page_chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
