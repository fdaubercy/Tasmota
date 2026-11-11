"""Sonde Chrome des puces de lieu, etiquettes, arborescence et listes groupees du sniffeur MQTT (modeles N et O).

UTILISATION (a la main, hors de tout build : aucun pio, Chrome ~20 s)
    python outils_docs/scripts_python/outils_pc/test_sniffeur_mqtt_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la vraie page passe tout ET le temoin (la meme page sans l'appel a /lieux) echoue.
Le VRAI sniffeur tourne dans un processus fils sur un port HTTP libre, 127.0.0.1 seulement, SANS boucle MQTT :
aucun broker n'est contacte, rien n'est publie. Les messages sont injectes par Sniffeur.recu (lignes JSON sur son
entree standard). Configuration de test dans un dossier temporaire (jamais %APPDATA%\\sniffeur_mqtt\\config.json).
Identites des cartes lues dans le vrai depot, en lecture seule. Montage de Chrome et client CDP : test_build_page_chrome.py.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import test_build_page_chrome as t

ICI = Path(__file__).resolve().parent
verifie = t.verifie
DEPART = [("tele/jardin/cuve/SENSOR", '{"niveau": 12}'), ("stat/garage/rideau/RESULT", '{"POWER": "ON"}'),
          ("tele/etage2/grenier/STATE", '{"Heap": 99}'), ("zigbee2mqtt/bridge/state", "online")]
PIEGE = ("tele/<b>x</b>/STATE", "<i>p</i>")
CUVE = "tasmota32s3-garage-capteurs-cuve-modbus"
JS_PUCES = """(() => [...document.querySelectorAll('#lieux .puce')].map(b =>
  [b.dataset.lieu, b.querySelector('.n').textContent, b.classList.contains('choisi')]))()"""
JS_ETIQUETTES = "[...document.querySelectorAll('#liste .m')].map(d => d.querySelector('.lieu') ? d.querySelector('.lieu').textContent : null)"
JS_RANGEE_PRETE = "document.querySelectorAll('#lieux .puce').length >= 8"
JS_NB = "document.querySelectorAll('#liste .m').length"
JS_RACINES = "[...document.querySelectorAll('#secArbre > details > summary .tp')].map(s => s.textContent)"
JS_GROUPES = ("(id => [...document.getElementById(id).querySelectorAll('optgroup')]"
              ".map(g => [g.label, [...g.querySelectorAll('option')].map(o => o.value)]))")
JS_FILTRE = "(() => {{ const f = document.getElementById('filtre'); f.value = '{}'; f.dispatchEvent(new Event('input')); }})()"


def mode_serveur(args, sans_lieux):
    sys.path.insert(0, str(ICI))
    import acces_web
    import client_mqtt
    import sniffeur_mqtt
    import sniffeur_mqtt_config
    import sniffeur_mqtt_web
    from http.server import ThreadingHTTPServer
    if sans_lieux:                                           # temoin : la page sans l'appel a /lieux
        assert "fetch('/lieux')" in sniffeur_mqtt_web.PAGE
        sniffeur_mqtt_web.PAGE = sniffeur_mqtt_web.PAGE.replace("fetch('/lieux')", "Promise.reject()")
    dossier, http = args
    chemin = os.path.join(dossier, "config.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"brokers": [], "actif": "tasmota", "abonnements": {}, "favoris": []}, f)
    configuration = sniffeur_mqtt_config.Configuration(
        {"nom": "Tasmota (sonde)", "hote": "127.0.0.1", "port": 1, "tls": False, "verifierCertificat": True,
         "utilisateur": "", "motDePasse": ""}, chemin)
    options = argparse.Namespace(abonnement=["#"], journal=None, historique=500, http=int(http), local=True)
    sniffeur = sniffeur_mqtt.Sniffeur(options, configuration)        # pas de boucle_mqtt : aucun broker contacte
    acces = acces_web.Acces(int(http), True, "Sniffeur MQTT (sonde)")
    serveur = ThreadingHTTPServer((acces.hote, int(http)), sniffeur_mqtt.fabrique_gestionnaire(sniffeur, acces))
    serveur.daemon_threads = True

    def lit_stdin():
        for ligne in sys.stdin:
            ligne = ligne.strip()
            if ligne:
                m = json.loads(ligne)
                sniffeur.recu(client_mqtt.Message(m["topic"], m["payload"].encode("utf-8"), 0, False))
    threading.Thread(target=lit_stdin, daemon=True).start()
    print("pret", flush=True)
    serveur.serve_forever()


class Montage:
    def __init__(self, sans_lieux):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_sniffeur_lieux_"))
        self.sans_lieux = sans_lieux
        self.serveur = self.chrome = None

    def demarre(self):
        self.http = t.port_libre()
        self.url = f"http://127.0.0.1:{self.http}/"
        commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur"]
                    + (["--sans-lieux"] if self.sans_lieux else []) + ["--", str(self.t), str(self.http)])
        self.serveur = subprocess.Popen(commande, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        env={**os.environ, "PYTHONIOENCODING": "utf-8", "OUTILS_TASMOTA_DOSSIER": str(self.t)},
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend(self.url + "etat", 20)
        for topic, payload in DEPART:
            self.envoie(topic, payload)
        self._attend_recus(len(DEPART))
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

    def envoie(self, topic, payload):
        self.serveur.stdin.write((json.dumps({"topic": topic, "payload": payload}) + "\n").encode("utf-8"))
        self.serveur.stdin.flush()

    def etat(self):
        return json.loads(self._attend(self.url + "etat", 5))

    def _attend_recus(self, n):
        limite = time.monotonic() + 10
        while time.monotonic() < limite:
            if self.etat().get("recus", 0) >= n:
                return
            time.sleep(0.2)
        raise TimeoutError("messages non recus")

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

    def ouvre(self, requete="", attendus=len(DEPART)):
        if self.cdp.js("document.readyState") is not None:       # marque l'ancien document : l'attente ne doit pas le lire
            self.cdp.js("window.__ancien = true; 1")
        self.cdp.appel("Page.navigate", url=self.url + requete)
        t.attend(self.cdp, f"!window.__ancien && {JS_NB} >= {attendus}", 15)

    def ferme(self):
        t.tue_arbre(self.chrome)
        t.tue_arbre(self.serveur)
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


def clique(cdp, code):
    cdp.js(f"document.querySelector('#lieux .puce[data-lieu=\"{code}\"]').click()")


def puces(cdp):
    return {c: (n, ch) for c, n, ch in cdp.js(JS_PUCES)}


def attend_puce(cdp, code, n, delai=5):
    return t.attend(cdp, f"document.querySelector('#lieux .puce[data-lieu={code}] .n').textContent === '{n}'", delai) is True


def nb(cdp, n, delai=5):
    return t.attend(cdp, f"{JS_NB} === {n}", delai) is True


def sonde(m):
    cdp = m.cdp
    m.ouvre()
    t.attend(cdp, JS_RANGEE_PRETE + " && document.querySelector('#lieux .puce .n').textContent === '4'", 10)
    if not verifie(bool(cdp.js(JS_RANGEE_PRETE)), True, "puces : rangee Tous + 6 lieux + Autres presente"):
        return
    p = puces(cdp)
    verifie(p["tous"][0], "4", "puce Tous : 4 messages")
    verifie(p["garage"][0], "2", "puce Garage : 2 messages (cuve jardin/cuve et rideau)")
    verifie(p["etage2"][0], "1", "puce 2e etage : 1 message")
    verifie(p["autres"][0], "1", "puce Autres : zigbee2mqtt")
    verifie(p["cave"][0], "0", "puce Cave : lieu sans message, compteur 0")
    verifie(cdp.js(JS_ETIQUETTES), ["Garage", "Garage", "2e étage", "Autres"], "etiquettes en tete des messages")
    verifie(cdp.js("document.querySelector('.bandeau-lieu')"), None, "sans ?lieu= : aucun bandeau")
    verifie(p["tous"][1], True, "sans ?lieu= : Tous choisi")
    abos = m.etat()["abonnements"]
    # -- message dont le topic et la charge sont du HTML : jamais interprete
    m.envoie(*PIEGE)
    verifie(attend_puce(cdp, "autres", 2), True, "message en direct : puce Autres a 2")
    verifie(cdp.js("document.querySelectorAll('#liste b, #liste i').length"), 0, "topic et charge pieges : aucune balise dans la liste")
    # -- clic Garage : filtre d'affichage seulement
    clique(cdp, "garage")
    verifie(nb(cdp, 2), True, "clic Garage : 2 messages")
    verifie(cdp.js(JS_ETIQUETTES), ["Garage", "Garage"], "clic Garage : etiquettes Garage")
    verifie(m.etat()["abonnements"], abos, "clic Garage : abonnements inchanges")
    cdp.js(JS_FILTRE.format("rideau"))
    verifie(nb(cdp, 1), True, "lieu + filtre texte : 1 message")
    cdp.js(JS_FILTRE.format(""))
    verifie(nb(cdp, 2), True, "filtre texte vide : 2 messages")
    m.envoie("tele/garage/rideau/LWT", "Online")                 # direct dans le lieu choisi : affiche
    verifie(nb(cdp, 3), True, "message en direct du lieu choisi : affiche")
    m.envoie("zigbee2mqtt/autre", "x")                           # direct hors lieu : compte mais cache
    verifie(attend_puce(cdp, "autres", 3), True, "message en direct hors lieu : compte")
    verifie(cdp.js(JS_NB), 3, "message en direct hors lieu : non affiche")
    clique(cdp, "garage")                                        # 2e clic = retour a Tous
    # -- arborescence (N)
    cdp.js("document.getElementById('btArbre').click()")
    t.attend(cdp, "document.querySelectorAll('#secArbre > details').length >= 3", 5)
    verifie(cdp.js(JS_RACINES), ["2e étage", "Garage", "Autres"], "arbre : 1er niveau 2e etage, Garage, Autres dans cet ordre")
    verifie(cdp.js("document.querySelector('#secArbre > details[data-chemin=garage] details[data-chemin=\"garage/tele/jardin/cuve\"] > summary')"
                   ".textContent.indexOf('(" + CUVE + ")') > 0"), True, "arbre : jardin/cuve sous Garage avec son env entre parentheses")
    verifie(cdp.js("document.querySelectorAll('#secArbre b, #secArbre i').length"), 0, "arbre : topic piege, aucune balise")
    cdp.js("document.querySelector('#secArbre details[data-chemin=garage]').open = true")
    t.attend(cdp, "document.querySelector('#secArbre details[data-chemin=garage]').open", 3)
    m.envoie("tele/etage2/grenier/LWT", "Online")                # redessine l'arbre (1 s) : l'ouverture est gardee
    time.sleep(1.8)
    verifie(cdp.js("document.querySelector('#secArbre details[data-chemin=garage]').open"), True, "arbre : ouverture de Garage gardee au redessin")
    clique(cdp, "garage")
    verifie(cdp.js(JS_RACINES), ["2e étage", "Garage", "Autres"], "arbre : puce Garage choisie, arbre non filtre")
    clique(cdp, "garage")
    # -- listes groupees (O) : logs de carte, commande
    cdp.js("document.getElementById('btLogs').click()")
    t.attend(cdp, "document.getElementById('logModule')", 5)
    m.envoie("stat/garage/rideau/LOGGING", "10:00:00 BRY: ok")
    m.envoie("stat/zigbee2mqtt/LOGGING", "11:00:00 autre")
    t.attend(cdp, "document.querySelectorAll('#logModule optgroup').length >= 2", 5)
    g = cdp.js(JS_GROUPES + "('logModule')")
    verifie([x[0] for x in g], ["Garage", "Autres"], "#logModule : groupes Garage puis Autres")
    verifie(dict((a, b) for a, b in g)["Garage"], ["garage/rideau"], "#logModule : garage/rideau dans le groupe Garage")
    verifie(cdp.js("document.getElementById('logModule').options[0].value"), "", "#logModule : option vide gardee en tete")
    cdp.js("document.getElementById('btLogs').click()")
    m.envoie("tasmota/discovery/AABBCCDDEEFF/config",
             json.dumps({"dn": "Rideau", "t": "garage/rideau", "ft": "%prefix%/%topic%/", "tp": ["cmnd", "stat", "tele"]}))
    cdp.js("document.getElementById('btCmd').click()")
    t.attend(cdp, "document.querySelectorAll('#cmdModule optgroup').length >= 1", 5)
    g = cdp.js(JS_GROUPES + "('cmdModule')")
    verifie([x[0] for x in g], ["Garage"], "#cmdModule : groupe Garage")
    verifie(dict((a, b) for a, b in g)["Garage"], ["garage/rideau"], "#cmdModule : garage/rideau dans le groupe Garage")
    verifie(cdp.js("document.getElementById('cmdModule').options[0].value"), "", "#cmdModule : option « topic libre » gardee en tete")
    cdp.js("document.getElementById('btCmd').click()")
    # -- ?lieu=
    m.ouvre("?lieu=garage", attendus=1)
    t.attend(cdp, "document.querySelector('.bandeau-lieu')", 5)
    verifie(cdp.js("document.querySelector('#lieux .puce.choisi').dataset.lieu"), "garage", "?lieu=garage : puce Garage active")
    verifie(cdp.js("document.querySelector('.bandeau-lieu').textContent"),
            "Lieu : Garage (depuis l’annuaire) · Tous les lieux ✕", "?lieu=garage : bandeau")
    verifie(t.attend(cdp, f"{JS_NB} >= 1 && [...document.querySelectorAll('#liste .m .lieu')].every(e => e.textContent === 'Garage')", 5) is True,
            True, "?lieu=garage : seuls les messages du garage")
    n = cdp.js(JS_NB)
    cdp.js("document.querySelector('.bandeau-lieu button').click()")
    verifie(cdp.js("[document.querySelector('.bandeau-lieu'), location.search]"), [None, ""], "croix : bandeau et parametre retires")
    verifie(t.attend(cdp, "document.querySelector('#lieux .puce.choisi').dataset.lieu === 'tous' && "
                          + JS_NB + " > " + str(n), 5) is True,
            True, "croix : puce Tous choisie, plus de messages qu'avec Garage")
    m.ouvre(attendus=1)                                          # reouverture sans parametre : Tous (vigilance 5)
    t.attend(cdp, JS_RANGEE_PRETE, 15)
    verifie(cdp.js("document.querySelector('#lieux .puce.choisi').dataset.lieu"), "tous", "reouverture sans parametre : Tous")
    verifie(cdp.js("document.querySelector('.bandeau-lieu')"), None, "reouverture sans parametre : pas de bandeau")
    m.ouvre("?lieu=" + urllib.parse.quote("<b>x</b>"), attendus=1)
    t.attend(cdp, JS_RANGEE_PRETE, 15)
    verifie(cdp.js("[document.querySelector('.bandeau-lieu'), document.querySelectorAll('body b').length, "
                   "document.querySelector('#lieux .puce.choisi').dataset.lieu]"),
            [None, 0, "tous"], "?lieu=<b>x</b> : ignore, aucun bandeau, Tous")
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
