"""Sonde Chrome de la rangee « Lieu de travail » de l'annuaire (annuaire_page_lieux.py, modele J).

UTILISATION (a la main, hors de tout build : aucun pio, aucun outil lance, Chrome ~20 s)
    python outils_docs/scripts_python/outils_pc/test_annuaire_lieux_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la vraie page passe tout ET le temoin (la meme page sans le module) echoue sur la
rangee. L'annuaire est lance dans un processus fils, sur un port libre, avec un dossier de presence temporaire
(OUTILS_TASMOTA_DOSSIER) : l'annuaire reel (7600) n'est ni touche ni interroge. Deux fiches de presence simulees
(syslog : outil marque ; pont serie : outil non marque) donnent des liens « Ouvrir ».
Montage de Chrome et client CDP : test_build_page_chrome.py.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import test_build_page_chrome as t

ICI = Path(__file__).resolve().parent
verifie = t.verifie

JS_RANGEE = """(() => [...document.querySelectorAll('#lieux .puce')].map(b =>
  [b.firstChild.textContent, b.querySelector('.n') ? b.querySelector('.n').textContent : '', b.getAttribute('aria-pressed')]))()"""
JS_LIENS = """(() => { const r = {};
  for (const id of ['syslog', 'pont_serie']) { const a = document.querySelector('.tuile[data-id=' + id + '] a.btn');
    r[id] = a ? a.getAttribute('href') : null; } return r; })()"""
PRET = "document.querySelectorAll('.tuile a.btn').length >= 2"
SYSLOG = "http://127.0.0.1:47201/"


def mode_serveur(port, sans_lieux):
    sys.path.insert(0, str(ICI))
    import annuaire_outils
    import annuaire_page_lieux as m
    if sans_lieux:                                     # temoin : la page d'avant le module
        p = annuaire_outils.PAGE
        for morceau in (m.CSS, m.HTML, m.JS):
            assert morceau in p, "morceau du module introuvable dans la page"
            p = p.replace(morceau, "")
        annuaire_outils.PAGE = p
    sys.argv = ["annuaire_outils.py", "--http", str(port), "--local", "--sans-navigateur"]
    return annuaire_outils.principal()


class Montage:
    def __init__(self, sans_lieux):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_annuaire_lieux_"))
        self.sans_lieux = sans_lieux
        self.serveur = self.chrome = None

    def demarre(self):
        presence = self.t / "presence"
        presence.mkdir()
        maintenant = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        for nom, port in (("Serveur syslog", 47201), ("Pont serie", 47000)):
            (presence / f"{port}.json").write_text(json.dumps(
                {"nom": nom, "port": port, "pid": os.getpid(), "debut": maintenant, "jeton": "x", "lance_par": "annuaire"}),
                encoding="utf-8")
        environ = dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(self.t), PYTHONIOENCODING="utf-8")
        self.port = t.port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        commande = [sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port)]
        self.serveur = subprocess.Popen(commande + (["--sans-lieux"] if self.sans_lieux else []), env=environ,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend(self.url + "registre", 20)
        chrome = next((c for c in t.CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable")
        self.port_cdp = t.port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                        "--window-size=1280,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend(f"http://127.0.0.1:{self.port_cdp}/json/list", 20, serveur=False)
        page = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = t.Cdp(page["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)

    def _attend(self, url, delai, serveur=True):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            if serveur and self.serveur.poll() is not None:
                raise RuntimeError("serveur arrete : " + self.serveur.stdout.read().decode("utf-8", "replace"))
            try:
                # 15 s et non 2 : le 1er /registre prend 1,5 a 4,5 s a froid ; abandonner puis relancer toutes les 0,2 s
                # empilait des calculs concurrents qui se ralentissaient entre eux (mesure du 2026-11-14).
                with urllib.request.urlopen(url, timeout=15) as r:
                    return r.read().decode("utf-8")
            except OSError:
                time.sleep(0.2)
        raise TimeoutError(url)

    def ouvre(self):
        self.cdp.appel("Page.navigate", url=self.url)
        t.attend(self.cdp, PRET, 15)

    def ferme(self):
        t.tue_arbre(self.chrome)
        t.tue_arbre(self.serveur)
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


def clique(cdp, code):
    cdp.js(f"document.querySelector('#lieux .puce[data-lieu=\"{code}\"]').click()")


def recharge(m):
    m.cdp.appel("Page.navigate", url=m.url)
    t.attend(m.cdp, PRET, 15)


def sonde(m):
    cdp = m.cdp
    sys.path.insert(0, str(ICI))
    import lieux
    codes = [c for c, _ in lieux.LIEUX]
    garage = sum(1 for c in lieux.identites(ICI.parents[2]) if c["lieu"] == "garage" and not c.get("sauvegarde"))
    m.ouvre()
    rangee = cdp.js(JS_RANGEE)
    noms = [r[0] for r in rangee] if isinstance(rangee, list) else rangee
    if not verifie(noms, ["Tous"] + [lib for _, lib in lieux.LIEUX], "rangee : Tous + 6 puces dans l'ordre de la table"):
        return
    verifie(rangee[0][2], "true", "rangee : Tous choisi a la premiere visite")
    verifie(garage > 0, True, "depot : le garage compte des cartes")
    verifie(rangee[1 + codes.index("garage")][1], str(garage), "rangee : compte du Garage en envs")
    verifie(cdp.js(JS_LIENS), {"syslog": SYSLOG, "pont_serie": "http://127.0.0.1:47000/"}, "Tous : liens inchanges")
    clique(cdp, "garage")
    liens = cdp.js(JS_LIENS)
    verifie(liens["syslog"], SYSLOG + "?lieu=garage", "Garage : lien d'un outil marque")
    verifie(liens["pont_serie"], "http://127.0.0.1:47000/", "Garage : outil non marque inchange")
    verifie(cdp.js("lienLieu({lieu: true}, 'http://h:1/?jeton=x')"), "http://h:1/?jeton=x&lieu=garage",
            "Garage : lien a jeton -> &lieu=")
    verifie(cdp.js("lienLieu({lieu: false}, 'http://h:1/?jeton=x')"), "http://h:1/?jeton=x", "outil non marque : jeton seul")
    recharge(m)
    verifie([r[2] for r in cdp.js(JS_RANGEE)], ["false"] + ["true" if c == "garage" else "false" for c in codes],
            "rechargement : Garage toujours choisi")
    verifie(cdp.js(JS_LIENS)["syslog"], SYSLOG + "?lieu=garage", "rechargement : le lien porte le lieu")
    clique(cdp, "")
    verifie(cdp.js(JS_LIENS)["syslog"], SYSLOG, "Tous : retour au lien nu")
    cdp.js("localStorage.setItem('annuaire-lieu', '<b>x</b>')")       # memoire inconnue : ignoree
    recharge(m)
    verifie(cdp.js(JS_RANGEE)[0][2], "true", "memoire inconnue : Tous")
    verifie(cdp.js("document.querySelectorAll('#lieux b').length"), 0, "memoire inconnue : aucune balise creee")
    cdp.appel("Page.addScriptToEvaluateOnNewDocument",
              source="Storage.prototype.getItem = function () { throw new Error('bloque'); };"
                     "Storage.prototype.setItem = function () { throw new Error('bloque'); };")
    recharge(m)
    verifie(cdp.js(JS_RANGEE)[0][2], "true", "stockage bloque : Tous")
    clique(cdp, "garage")
    verifie(cdp.js(JS_LIENS)["syslog"], SYSLOG + "?lieu=garage", "stockage bloque : le clic marche quand meme")
    verifie([e for e in cdp.erreurs() if "favicon" not in e], [], "aucune erreur JS")


def principal():
    args = sys.argv[1:]
    if args and args[0] == "--serveur":
        return mode_serveur(int(args[1]), "--sans-lieux" in args)
    for temoin in ([False] if "--sans-temoin" in args else [False, True]):
        print(f"\n=== {'TEMOIN (sans le module)' if temoin else 'page reelle'} ===", flush=True)
        avant = len(t.ECHECS)
        m = Montage(sans_lieux=temoin)
        try:
            m.demarre()
            sonde(m)
        except FileNotFoundError as e:
            print("BLOQUE :", e)
            return 3
        except Exception as e:
            verifie(repr(e), "pas d'exception de la sonde", "sonde : deroulement")
        finally:
            m.ferme()
        if temoin:                       # le temoin DOIT echouer : ses echecs ne comptent pas
            echecs = len(t.ECHECS) - avant
            del t.ECHECS[avant:]
            verifie(echecs >= 1, True, "temoin : la sonde echoue sans le module")
    print("\n" + ("VERT" if not t.ECHECS else f"ROUGE : {t.ECHECS}"))
    return 1 if t.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
