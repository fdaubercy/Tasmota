"""Sonde Chrome de la page « Taches planifiees » : bandeau, deux voies, texte hostile (env, job, lien javascript:), gh hors ligne, mode sombre, telephone.

UTILISATION (a la main ; aucun gh, aucun schtasks, aucun reseau : faux executeurs ; Chrome ~15 s par passage)
    python outils_docs/scripts_python/outils_pc/test_taches_planifiees_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET chaque temoin (meme page, une ligne changee) est detecte par SON test.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_taches_planifiees_page_chrome.py
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
import taches_planifiees_page as page_mod                                       # noqa: E402
import taches_planifiees_web as tw                                              # noqa: E402
import test_taches_planifiees_web as banc                                       # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402

ECHECS = []
HOSTILE = banc.HOSTILE
PAGE_ORIGINALE = page_mod.PAGE
TEMOINS = {
    "innerHTML": ("if (texte != null) e.textContent = texte;", "if (texte != null) e.innerHTML = texte;", "hostile : env et job restent du texte"),
    "lien-js": ('url.indexOf("https://github.com/") !== 0', "false", "lien javascript: jamais pose en href"),
    "deux-temps": ("if (minuteur === null) {", "if (false) {", "lancer : le 1er clic arme seulement"),
    "double-clic": ("if (Date.now() - arme < 500) return;", "", "lancer : un double-clic reflexe ne confirme pas"),
    "relance": ("if (enCours) { if (frais) relance = true; return; }", "if (enCours) { return; }", "rechargement en cours : une relance memorisee"),
}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


class Montage:
    def __init__(self, page):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_taches_"))
        self.chrome = self.serveur = None
        donnees = self.t / "compilations_nuit"
        donnees.mkdir()
        (self.t / "build" / "journaux").mkdir(parents=True)
        res = {"debut": "2026-11-15T02:00:00", "port": 7700, "code": 1, "refus": None, "fin": "termine", "envs_prevus": ["a", HOSTILE],
               "envs": [{"env": "a", "resultat": "succes", "secondes": 60}, {"env": HOSTILE, "resultat": "echec", "secondes": 30}]}
        (donnees / "dernier.json").write_text(json.dumps(res), encoding="utf-8")
        (donnees / "resultat-20261115-020000.json").write_text(json.dumps(res), encoding="utf-8")
        self.mode = {"hors_ligne": False}
        jobs = [{"name": HOSTILE, "conclusion": "failure", "url": "javascript:window.__pwn3=1"},
                {"name": "bon job", "conclusion": "failure", "url": "https://github.com/fdaubercy/Tasmota/actions/runs/1/job/2"}]
        vrai = banc.faux_gh(jobs=jobs)
        mort = banc.faux_gh(code=124, sortie="delai depasse")
        page_mod.PAGE = page
        # Gestes de la page (A4) : depot TEMPORAIRE (cenv avec un env hostile), fausse page Build, faux processus. Un clic de la sonde
        # ne peut donc ni lancer une compilation, ni arreter celle de l'utilisateur, ni ecrire dans le vrai depot.
        self.racine = self.t / "depot"
        self.racine.mkdir()
        (self.racine / "platformio_tasmota_cenv.ini").write_text(f"[env:a]\n[env:{HOSTILE}]\n", encoding="utf-8")
        self.lances = []
        fausse_page = lambda port, chemin, corps=None, delai=30: (200, {"en_cours": False, "numero": 0}) if chemin == "/execution" else (200, {"ok": True})
        self.etat = tw.Etat(lambda a, delai=0: (mort if self.mode["hors_ligne"] else vrai)(a), banc.faux_schtasks(), donnees, self.t / "build" / "journaux",
                            cache_s=0, appel=fausse_page, lance=lambda c, **k: self.lances.append(c), racine=self.racine,
                            git=lambda a, r: (1, "git interdit dans la sonde"))
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        acces = acces_web.Acces(self.port, True, "Taches planifiees")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), tw.fabrique_gestionnaire(acces, self.etat))
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
    verifie(bool(attend(cdp, "document.querySelectorAll('#gh dl').length > 0", 15)), True, "page chargee, voie GitHub rendue")
    verifie(cdp.js("document.title"), "Tâches planifiées", "titre")
    verifie(cdp.js("document.getElementById('bandeau').className"), "bandeau orange", "bandeau orange (jobs en echec / derniere nuit en echec)")
    verifie(cdp.js("document.querySelectorAll('#pc .liste li').length >= 2"), True, "voie PC : envs en echec et historique listes")
    verifie(cdp.js("document.getElementById('pc').textContent.indexOf(" + json.dumps(HOSTILE) + ") >= 0"), True, "env hostile affiche tel quel, comme du texte")
    verifie(cdp.js("document.getElementById('gh').textContent.indexOf(" + json.dumps(HOSTILE) + ") >= 0"), True, "job hostile affiche tel quel, comme du texte")
    verifie(cdp.js("document.querySelectorAll('main img, main b').length === 0 && window.__pwn === undefined"), True, "hostile : aucune balise creee, aucun script")
    verifie(cdp.js("Array.prototype.every.call(document.querySelectorAll('a'), function(a){return a.href.indexOf('https://github.com/')===0 || a.href.indexOf('http://127.0.0.1')===0 || a.closest('#barre-outils')})"),
            True, "lien javascript: jamais pose en href")
    verifie(cdp.js("document.querySelectorAll('#gh a[href^=\"https://github.com/\"]').length >= 2"), True, "liens GitHub sains presents (job et run)")
    # -- gestes (A4) -------------------------------------------------------------------------------
    def bouton(voie, debut):
        return "Array.prototype.find.call(document.querySelectorAll('#" + voie + " .gestes button'), function(b){return b.textContent.indexOf(" + json.dumps(debut) + ") === 0;})"
    verifie(cdp.js("document.querySelectorAll('#pc .gestes button').length >= 5 && document.querySelectorAll('#gh .gestes button').length >= 6"), True,
            "gestes : boutons presents sur les deux voies")
    verifie(cdp.js("document.querySelectorAll('#pc .envs label').length"), 2, "gestes : une case par env du cenv (voie PC)")
    verifie(cdp.js("document.querySelector('#gh .envs').textContent.indexOf(" + json.dumps(HOSTILE) + ") >= 0"), True, "gestes : env hostile affiche comme du texte dans les cases")
    verifie(cdp.js("document.querySelectorAll('#gh .envs input:checked').length"), 2, "gestes : tous les envs coches quand rien n'est exclu")
    cdp.js(bouton("pc", "Lancer maintenant") + ".click()")
    verifie(cdp.js(bouton("pc", "Confirmer") + ".textContent.length > 10"), True, "lancer : le 1er clic arme seulement (bouton « Confirmer : ... »)")
    verifie(len(m.lances), 0, "lancer : le 1er clic ne lance rien")
    cdp.js(bouton("pc", "Confirmer") + ".click()")                 # double-clic reflexe, dans les 500 ms
    verifie(cdp.js("!!(" + bouton("pc", "Confirmer") + ")"), True, "lancer : un double-clic reflexe ne confirme pas (le bouton reste arme)")
    verifie(len(m.lances), 0, "lancer : un double-clic reflexe ne lance rien")
    time.sleep(0.7)
    cdp.js(bouton("pc", "Confirmer") + ".click()")
    verifie(bool(attend(cdp, "document.querySelector('#pc .msg').textContent.indexOf('Lancé') >= 0", 15)), True, "lancer : le 2e clic confirme et le dit")
    verifie(len(m.lances), 1, "lancer : un seul processus demarre, par la fausse commande")
    verifie(bool(attend(cdp, "!document.getElementById('actualiser').disabled", 15)), True, "lancer : le rechargement qui suit le geste est termine")
    verifie(cdp.js("enCours = true; charge(true); var r = relance; enCours = false; relance = false; r"), True, "rechargement en cours : un geste reussi memorise une relance")
    verifie(cdp.js("document.querySelector('#pc input[type=time]').getAttribute('aria-label')"), "Heure de la compilation de nuit", "champ d'heure : etiquette accessible")
    cdp.js(bouton("gh", "Aperçu") + ".click()")
    verifie(bool(attend(cdp, "document.querySelector('#gh .msg').textContent.indexOf('Aucun changement') >= 0", 15)), True, "apercu GitHub : annonce l'absence de changement")
    cdp.js("document.querySelector('#gh .envs input').click()")
    cdp.js(bouton("gh", "Aperçu") + ".click()")
    verifie(bool(attend(cdp, "document.querySelector('#gh .msg').textContent.indexOf('Exclus ajoutés') >= 0", 15)), True, "apercu GitHub : liste le changement")
    verifie((m.racine / "outils_docs").exists(), False, "apercu GitHub : rien n'est ecrit dans le depot")
    verifie(cdp.js(bouton("gh", "Écrire, commiter et pousser") + " != null"), True, "GitHub : le bouton annonce qu'il commite et pousse")
    m.mode["hors_ligne"] = True
    cdp.js("document.getElementById('actualiser').click()")
    verifie(bool(attend(cdp, "document.getElementById('bandeau').textContent.indexOf('injoignable') >= 0", 15)), True, "gh hors ligne : le bandeau le dit")
    verifie(cdp.js("document.getElementById('bandeau').className"), "bandeau orange", "gh hors ligne : orange, la page reste servie")
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
    verifie(cdp.js("getComputedStyle(document.body).backgroundColor"), "rgb(18, 20, 23)", "mode sombre : fond sombre")
    cdp.appel("Emulation.setDeviceMetricsOverride", width=390, height=800, deviceScaleFactor=2, mobile=True)
    time.sleep(0.5)
    verifie(cdp.js("document.documentElement.scrollWidth <= window.innerWidth"), True, "telephone : aucun defilement horizontal")


def passage(page, temoin=None):
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
            passage(PAGE_ORIGINALE.replace(ancien, nouveau), temoin=nom)
            detecte = bool(ECHECS)
            print(("OK   " if detecte else "KO   ") + f"temoin {nom} detecte")
            if not detecte:
                return 1
        ECHECS.clear()
    print("VERT : taches_planifiees_page_chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
