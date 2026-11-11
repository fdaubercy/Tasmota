"""Sonde Chrome des puces de lieu et des etiquettes de la page syslog (syslog_tasmota_web.py, modele M).

UTILISATION (a la main, hors de tout build : aucun pio, Chrome ~20 s)
    python outils_docs/scripts_python/outils_pc/test_syslog_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la vraie page passe tout ET le temoin (la meme page sans l'appel a /lieux) echoue.
Le VRAI syslog_tasmota.py tourne dans un processus fils sur un port UDP et un port HTTP libres, a l'ecoute de
127.0.0.1 seulement ; les datagrammes de test partent de la sonde vers ce port (jamais 514, jamais une carte).
Identites des cartes lues dans le vrai depot, en lecture seule. Le cas « hote inconnu reconnu par l'IP » ne peut pas
etre emis d'ici (IP source 127.0.0.1) : il reste au banc Node de lieux.JS.
Montage de Chrome et client CDP : test_build_page_chrome.py.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import test_build_page_chrome as t

ICI = Path(__file__).resolve().parent
verifie = t.verifie
HOTES = [("CAPTEURS-CUVE", 6, "BRY: niveau cuve"), ("RIDEAU-GARAGE", 3, "BRY: rideau bloque"),
         ("SERVEUR-GRENIER-2EME", 6, "BRY: grenier ok"), ("tasmota-4F2A1C", 6, "BRY: carte inconnue"),
         ("<b>x</b>", 6, "BRY: piege <i>html</i>")]
JS_PUCES = """(() => [...document.querySelectorAll('#lieux .puce')].map(b =>
  [b.dataset.lieu, b.querySelector('.n').textContent, b.querySelector('.e').textContent.trim(), b.classList.contains('choisi')]))()"""
JS_LIGNES = """[...document.querySelectorAll('#liste .l')].map(d => d.querySelector('.lieu') ? d.querySelector('.lieu').textContent : null)"""
JS_MODULES = """[...document.querySelectorAll('#modules .mod')].map(d => d.firstChild.textContent.trim())"""
JS_RANGEE_PRETE = "document.querySelectorAll('#lieux .puce').length >= 8"


def mode_serveur(args, sans_lieux):
    sys.path.insert(0, str(ICI))
    import syslog_tasmota
    import syslog_tasmota_web
    if sans_lieux:                                           # temoin : la page sans l'appel a /lieux
        assert 'fetch("/lieux")' in syslog_tasmota_web.PAGE
        syslog_tasmota_web.PAGE = syslog_tasmota_web.PAGE.replace('fetch("/lieux")', "Promise.reject()")
    sys.argv = ["syslog_tasmota.py"] + args
    return syslog_tasmota.main()


def port_libre_udp():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Montage:
    def __init__(self, sans_lieux):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_syslog_lieux_"))
        self.sans_lieux = sans_lieux
        self.serveur = self.chrome = None

    def demarre(self):
        self.http, self.udp = t.port_libre(), port_libre_udp()
        self.url = f"http://127.0.0.1:{self.http}/"
        args = ["--port", str(self.udp), "--ecoute", "127.0.0.1", "--http", str(self.http), "--local",
                "--journal", str(self.t / "journal.log"), "--sans-navigateur"]
        commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur"]
                    + (["--sans-lieux"] if self.sans_lieux else []) + ["--"] + args)
        self.serveur = subprocess.Popen(commande, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        env={**os.environ, "PYTHONIOENCODING": "utf-8", "OUTILS_TASMOTA_DOSSIER": str(self.t)},
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend(self.url + "etat", 20)
        for hote, sev, texte in HOTES:
            self.envoie(hote, sev, texte)
        self._attend_lignes(len(HOTES))
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

    def envoie(self, hote, sev, texte):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(f"<{128 + sev}>1 2026-11-11T10:00:00.000000+01:00 {hote} tasmota - - - {texte}".encode(),
                     ("127.0.0.1", self.udp))

    def _attend_lignes(self, n):
        limite = time.monotonic() + 10
        while time.monotonic() < limite:
            if json.loads(self._attend(self.url + "etat", 5)).get("recus", 0) >= n:
                return
            time.sleep(0.2)
        raise TimeoutError("datagrammes non recus")

    def _attend(self, url, delai, serveur=True):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            if serveur and self.serveur.poll() is not None:
                raise RuntimeError("serveur arrete : " + self.serveur.stdout.read().decode("utf-8", "replace"))
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    return r.read().decode("utf-8")
            except OSError:
                time.sleep(0.2)
        raise TimeoutError(url)

    def ouvre(self, requete=""):
        if self.cdp.js("document.readyState") is not None:       # marque l'ancien document : l'attente ne doit pas le lire
            self.cdp.js("window.__ancien = true; 1")
        self.cdp.appel("Page.navigate", url=self.url + requete)
        t.attend(self.cdp, f"!window.__ancien && document.querySelectorAll('#liste .l').length >= {len(HOTES)}", 15)

    def ferme(self):
        t.tue_arbre(self.chrome)
        t.tue_arbre(self.serveur)
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


def clique(cdp, code):
    cdp.js(f"document.querySelector('#lieux .puce[data-lieu=\"{code}\"]').click()")


def filtre(cdp, valeur):
    cdp.js(f"(() => {{ const f = document.getElementById('filtre'); f.value = '{valeur}'; f.dispatchEvent(new Event('input')); }})()")


def nb_lignes(cdp, n, delai=5):
    return t.attend(cdp, f"document.querySelectorAll('#liste .l').length === {n}", delai) is True


def sonde(m):
    cdp = m.cdp
    m.ouvre()
    t.attend(cdp, JS_RANGEE_PRETE + f" && document.querySelector('#lieux .puce .n').textContent === '{len(HOTES)}'", 10)
    if not verifie(bool(cdp.js(JS_RANGEE_PRETE)), True, "puces : rangee Tous + 6 lieux + Autres presente"):
        return
    p = {c: (n, e) for c, n, e, _ in cdp.js(JS_PUCES)}
    verifie(p["tous"], (str(len(HOTES)), "1 err"), "puce Tous : lignes et erreurs")
    verifie(p["garage"], ("2", "1 err"), "puce Garage : 2 lignes et 1 erreur")
    verifie(p["etage2"], ("1", ""), "puce 2e etage : 1 ligne")
    verifie(p["autres"], ("2", ""), "puce Autres : tasmota-4F2A1C et l'hote piege")
    verifie(p["cave"], ("0", ""), "puce Cave : lieu sans ligne, compteur 0")
    verifie(cdp.js(JS_LIGNES), ["Garage", "Garage", "2e étage", "Autres", "Autres"], "etiquettes en tete des lignes")
    verifie(cdp.js("document.querySelectorAll('#liste b, #liste i, #modules b').length"), 0,
            "hote et texte pieges : aucune balise creee")
    verifie(cdp.js("document.querySelector('.bandeau-lieu')"), None, "sans ?lieu= : aucun bandeau")
    verifie(cdp.js("document.querySelector('#lieux .puce.choisi').dataset.lieu"), "tous", "sans ?lieu= : Tous choisi")
    clique(cdp, "garage")
    verifie(nb_lignes(cdp, 2), True, "clic Garage : 2 lignes")
    verifie(sorted(cdp.js(JS_MODULES)), ["CAPTEURS-CUVE", "RIDEAU-GARAGE"], "clic Garage : barre des modules reduite au garage")
    filtre(cdp, "cuve")
    verifie(nb_lignes(cdp, 1), True, "lieu + filtre texte : 1 ligne")
    filtre(cdp, "")
    clique(cdp, "autres")
    verifie(nb_lignes(cdp, 2), True, "clic Autres : 2 lignes")
    m.envoie("SERVEUR-GRENIER-2EME", 6, "BRY: direct")           # ligne recue en direct : comptee sans rechargement
    verifie(t.attend(cdp, "document.querySelector('#lieux .puce[data-lieu=etage2] .n').textContent === '2'", 5), True,
            "ligne en direct : puce 2e etage a 2")
    clique(cdp, "")
    m.ouvre("?lieu=garage")
    t.attend(cdp, "document.querySelector('.bandeau-lieu')", 5)
    verifie(cdp.js("document.querySelector('#lieux .puce.choisi').dataset.lieu"), "garage", "?lieu=garage : puce Garage active")
    verifie(cdp.js("document.querySelector('.bandeau-lieu').textContent"),
            "Lieu : Garage (depuis l’annuaire) · Tous les lieux ✕", "?lieu=garage : bandeau")
    verifie(nb_lignes(cdp, 2), True, "?lieu=garage : 2 lignes des l'ouverture")
    cdp.js("document.querySelector('.bandeau-lieu button').click()")
    verifie(cdp.js("[document.querySelector('.bandeau-lieu'), location.search]"), [None, ""],
            "croix : bandeau et parametre retires")
    verifie(t.attend(cdp, "document.querySelector('#lieux .puce.choisi').dataset.lieu === 'tous' && "
                          "document.querySelectorAll('#liste .l').length === Number(document.querySelector('#lieux .puce[data-lieu=tous] .n').textContent) && "
                          "document.querySelectorAll('#liste .l').length > 2", 5) is True,
            True, "croix : puce Tous choisie, toutes les lignes affichees")
    m.ouvre()                                                    # reouverture sans parametre : Tous (vigilance 5)
    t.attend(cdp, JS_RANGEE_PRETE, 15)
    verifie(cdp.js("document.querySelector('#lieux .puce.choisi').dataset.lieu"), "tous", "reouverture sans parametre : Tous")
    verifie(cdp.js("document.querySelector('.bandeau-lieu')"), None, "reouverture sans parametre : pas de bandeau")
    m.ouvre("?lieu=" + urllib.parse.quote("<b>x</b>"))
    t.attend(cdp, JS_RANGEE_PRETE, 15)
    verifie(cdp.js("[document.querySelector('.bandeau-lieu'), document.querySelectorAll('body b').length, "
                   "document.querySelector('#lieux .puce.choisi').dataset.lieu]"),
            [None, 0, "tous"], "?lieu=<b>x</b> : ignore, aucune balise, Tous")
    verifie([e for e in cdp.erreurs() if "favicon" not in e], [], "aucune erreur JS")


def principal():
    args = sys.argv[1:]
    if args and args[0] == "--serveur":
        i = args.index("--")
        return mode_serveur(args[i + 1:], "--sans-lieux" in args[:i])
    for temoin in ([False] if "--sans-temoin" in args else [False, True]):
        print(f"\n=== {'TEMOIN (sans /lieux)' if temoin else 'page reelle'} ===", flush=True)
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
            verifie(echecs >= 1, True, "temoin : la sonde echoue sans /lieux")
    print("\n" + ("VERT" if not t.ECHECS else f"ROUGE : {t.ECHECS}"))
    return 1 if t.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
