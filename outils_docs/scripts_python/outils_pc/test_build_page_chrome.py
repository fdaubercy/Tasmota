"""Sonde Chrome de la page Build et televersement (build_page.PAGE) : la page s'execute-t-elle vraiment ?

UTILISATION (a la main, hors de tout build : aucun pio n'est lance, mais Chrome tourne ~1 min)
    python outils_docs/scripts_python/outils_pc/test_build_page_chrome.py [--sans-temoin] [--capture DOSSIER]
Code de sortie 0 = vert : la vraie page passe toutes les verifications ET le temoin (la meme page avec une
erreur JS volontaire au chargement) est bien detecte. Sans temoin, un vert ne prouverait rien (lecon 7).

Pourquoi un vrai navigateur (lecons du 2026-10-16 et du 2026-10-17) : une page servie en 200 dont le JS
passe `node --check` peut mourir au chargement ; avec un flux SSE, `--virtual-time-budget` bloque et
`--dump-dom` capture trop tot. Chrome est donc pilote par DevTools (`--headless=new`,
`--remote-debugging-port`, client WebSocket en stdlib), erreurs captees par Runtime.exceptionThrown,
Runtime.consoleAPICalled (error) et Log.entryAdded (error).

Montage : le serveur est build_web.py lui-meme, lance dans un processus fils (mode --serveur de ce
script) sur un port libre, avec :
  - BUILD_WEB_PIO = build_faux_pio.py : le VRAI pio n'est JAMAIS lance (verifie avant le demarrage) ;
  - un depot d'essai temporaire (3 cartes, 1 base, envs amont des 4 sous-groupes) : aucun .ini reel lu
    ni ecrit (la sonde ecrit un port par la page) ;
  - OUTILS_TASMOTA_DOSSIER temporaire (journaux, derniers choix, fiche de presence) ;
  - la detection des builds externes neutralisee (c'est la page qu'on teste, pas garde_build) ;
  - la verification des ports COM neutralisee (toujours « libre ») : aucun vrai port n'est ouvert.
Scenario : 3 envs a compiler, dont le 2e en echec -> bandeau rouge sur lui seul, durees affichees,
barre a 100 % sur les 2 autres, journal depliable, rappel des fichiers modifies ; puis largeur telephone.
"""

import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

ICI = Path(__file__).resolve().parent
FAUX_PIO = ICI / "build_faux_pio.py"
CHROMES = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
           Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
           Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"]
A, B, C, BASE = "tasmota32-sonde-a", "tasmota32-sonde-b", "tasmota32s3-sonde-c", "tasmota32-sonde-base"
CENV = f"""\
[env:{BASE}]
extra_scripts           = pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py
custom_files_upload     = no_files

[env:{A}]
extends                 = env:{BASE}
upload_port             = COM12
custom_files_upload     = ${{env:{BASE}.custom_files_upload}}
                          data/essai/{A}

[env:{B}]
extends                 = env:{BASE}
upload_port             = COM13

[env:{C}]
extends                 = env:{BASE}
"""
ENV32 = """\
[env:tasmota32_base]
extra_scripts           = pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py

[env:tasmota32-safeboot]
extends                 = env:tasmota32_base

[env:tasmota32]
extends                 = env:tasmota32_base

[env:tasmota32-DE]
extends                 = env:tasmota32_base
"""
ENV8266 = """\
[env:tasmota]
build_flags             = -DFIRMWARE_TASMOTA
"""
COMPILE_LENT = ["Processing {env} (platform: espressif32)", "Compiling .pio/build/{env}/src/a.cpp.o", "@pause 1.2",
                "Compiling .pio\\build\\{env}\\src\\b.cpp.o", "Linking .pio/build/{env}/firmware.elf",
                "[SUCCESS] Took 2.10 seconds"]
SCENARIO = {
    A: {"build": {"lignes": COMPILE_LENT, "delai": 0.15}},
    B: {"build": {"code": 1, "delai": 0.15, "lignes": [
        "Processing {env} (platform: espressif32)", "Compiling .pio/build/{env}/src/a.cpp.o",
        "src/a.cpp:12:3: error: 'x' was not declared in this scope",
        "*** [.pio/build/{env}/src/a.cpp.o] Error 1", "[FAILED] Took 0.90 seconds"]}},
    C: {"build": {"lignes": COMPILE_LENT, "delai": 0.15}},
}
# A9 : sortie assez longue pour deborder du panneau, avertissement, erreur, puis esptool qui reecrit sa ligne
# (dans le journal : une ligne vide puis la barre, a chaque palier ; voir build_page, ajouteSortie)
SORTIE_A = (["Processing {env} (platform: espressif32)"] + [f"Compiling .pio/build/{{env}}/src/f{i}.cpp.o" for i in range(40)]
            + ["src/x.cpp:1:1: warning: unused variable 'v' [-Wunused-variable]",
               "src/y.cpp:2:2: error: 'z' was not declared in this scope", "@pause 2.5",
               "Writing 'C:\\x\\.pio\\build\\{env}\\firmware.bin' at 0x00010000...", "",
               "Writing at 0x00010000 [░░░░░░░░░░]  10.0% 16.00kB/160.00kB [0s] ", "",
               "Writing at 0x00020000 [█████░░░░░]  50.0% 80.00kB/160.00kB [1s] ", "",
               "Writing at 0x00030000 [██████████] 100.0% 160.00kB/160.00kB [2s] ",
               "Wrote 163840 bytes (81920 compressed) at 0x00010000 in 2.0 seconds (655.4 kbit/s).",
               "@pause 1.5", "[SUCCESS] Took 5.00 seconds"])
MARQUE_TEMOIN = "var aDessiner = {}, minuterie = null;"
INJECTION_TEMOIN = '\n$("bouton-qui-n-existe-pas").onclick = null;   // TEMOIN : TypeError au chargement\n'
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def tue_arbre(proc):
    if proc and proc.poll() is None:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)


# -- mode serveur (processus fils) ------------------------------------------------------------------

def mode_serveur(port, depot, temoin):
    pio = os.environ.get("BUILD_WEB_PIO", "")
    if Path(pio).resolve() != FAUX_PIO.resolve():            # garde : jamais le vrai pio
        print(f"REFUS : BUILD_WEB_PIO doit designer {FAUX_PIO}, recu {pio!r}", flush=True)
        return 2
    sys.path.insert(0, str(ICI))
    import build_page
    if temoin:
        assert build_page.PAGE.count(MARQUE_TEMOIN) == 1, "marque du temoin introuvable dans la page"
        build_page.PAGE = build_page.PAGE.replace(MARQUE_TEMOIN, MARQUE_TEMOIN + INJECTION_TEMOIN)
    import build_serie
    import build_web
    build_serie.garde_build = lambda: SimpleNamespace(builds_en_cours=lambda: [])
    # jamais de vrai port COM : la verification par defaut ouvrirait le port de la carte (COM12 = la cuve sur ce PC)
    serie_reelle = build_serie.Serie
    build_serie.Serie = lambda *a, **k: serie_reelle(*a, **dict(k, port_libre=lambda port: "libre"))
    build_web.DEPOT = Path(depot)
    sys.argv = ["build_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return build_web.principal()


# -- client DevTools minimal (WebSocket RFC 6455, stdlib) ----------------------------------------

class Cdp:
    def __init__(self, url_ws):
        hote_port, chemin = url_ws[len("ws://"):].split("/", 1)
        hote, port = hote_port.split(":")
        self.sock = socket.create_connection((hote, int(port)), timeout=30)
        cle = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{chemin} HTTP/1.1\r\nHost: {hote_port}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {cle}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        reponse = b""
        while b"\r\n\r\n" not in reponse:
            reponse += self.sock.recv(4096)
        if b" 101 " not in reponse.split(b"\r\n")[0]:
            raise RuntimeError(f"poignee de main WebSocket refusee : {reponse[:200]!r}")
        self.reste = reponse.split(b"\r\n\r\n", 1)[1]
        self.numero = 0
        self.reponses = {}
        self.evenements = []
        self.condition = threading.Condition()
        threading.Thread(target=self._lit, daemon=True).start()

    def _octets(self, n):
        while len(self.reste) < n:
            morceau = self.sock.recv(65536)
            if not morceau:
                raise ConnectionError("WebSocket ferme")
            self.reste += morceau
        donnees, self.reste = self.reste[:n], self.reste[n:]
        return donnees

    def _trame(self):
        b0, b1 = self._octets(2)
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack(">H", self._octets(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", self._octets(8))[0]
        masque = self._octets(4) if b1 & 0x80 else None
        charge = self._octets(n)
        if masque:
            charge = bytes(c ^ masque[i % 4] for i, c in enumerate(charge))
        return b0 & 0x80, b0 & 0x0F, charge

    def _lit(self):
        try:
            message = b""
            while True:
                fin, code, charge = self._trame()
                if code == 0x9:
                    self._envoie(charge, 0xA)
                    continue
                if code == 0x8:
                    return
                message += charge
                if not fin:
                    continue
                donnees, message = json.loads(message.decode("utf-8")), b""
                with self.condition:
                    if "id" in donnees:
                        self.reponses[donnees["id"]] = donnees
                    else:
                        self.evenements.append(donnees)
                    self.condition.notify_all()
        except (OSError, ConnectionError, ValueError):
            pass

    def _envoie(self, charge, code=0x1):
        masque = os.urandom(4)
        n = len(charge)
        entete = bytes([0x80 | code])
        if n < 126:
            entete += bytes([0x80 | n])
        elif n < 65536:
            entete += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            entete += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.sock.sendall(entete + masque + bytes(c ^ masque[i % 4] for i, c in enumerate(charge)))

    def appel(self, methode, delai=30, **params):
        with self.condition:
            self.numero += 1
            n = self.numero
        self._envoie(json.dumps({"id": n, "method": methode, "params": params}).encode("utf-8"))
        limite = time.monotonic() + delai
        with self.condition:
            while n not in self.reponses:
                reste = limite - time.monotonic()
                if reste <= 0:
                    raise TimeoutError(f"pas de reponse DevTools a {methode}")
                self.condition.wait(reste)
            reponse = self.reponses.pop(n)
        if "error" in reponse:
            raise RuntimeError(f"{methode} : {reponse['error']}")
        return reponse.get("result", {})

    def js(self, expression):
        """Valeur JSON d'une expression evaluee dans la page (promesses attendues)."""
        r = self.appel("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            return {"_exception_sonde": r["exceptionDetails"].get("text", "") + " " +
                    str(r["exceptionDetails"].get("exception", {}).get("description", ""))}
        return r.get("result", {}).get("value")

    def erreurs(self):
        """Erreurs de la page : exceptions non rattrapees, console.error, journal Chrome de niveau error."""
        trouvees = []
        with self.condition:
            evenements = list(self.evenements)
        for e in evenements:
            p = e.get("params", {})
            if e.get("method") == "Runtime.exceptionThrown":
                d = p.get("exceptionDetails", {})
                trouvees.append("exception : " + str(d.get("exception", {}).get("description") or d.get("text")))
            elif e.get("method") == "Runtime.consoleAPICalled" and p.get("type") == "error":
                trouvees.append("console.error : " + " ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", [])))
            elif e.get("method") == "Log.entryAdded" and p.get("entry", {}).get("level") == "error":
                trouvees.append("journal Chrome : " + p["entry"].get("text", "") + " " + p["entry"].get("url", ""))
        return trouvees

    def capture(self, chemin):
        mesures = self.appel("Page.getLayoutMetrics")
        taille = mesures.get("cssContentSize") or mesures.get("contentSize")
        r = self.appel("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                       clip={"x": 0, "y": 0, "width": taille["width"], "height": taille["height"], "scale": 1})
        Path(chemin).write_bytes(base64.b64decode(r["data"]))
        print(f"     capture : {chemin}", flush=True)


def attend(cdp, expression, delai, pas=0.25):
    """Attend qu'une expression JS soit vraie ; renvoie sa derniere valeur."""
    limite = time.monotonic() + delai
    valeur = None
    while time.monotonic() < limite:
        valeur = cdp.js(expression)
        if valeur and not (isinstance(valeur, dict) and "_exception_sonde" in valeur):
            return valeur
        time.sleep(pas)
    return valeur


# -- montage : serveur + Chrome ---------------------------------------------------------------------

class Montage:
    def __init__(self):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_build_page_"))
        self.serveur = self.chrome = None

    def demarre(self, temoin):
        self.depot = self.t / "depot"
        self.depot.mkdir()
        (self.depot / "platformio_tasmota_cenv.ini").write_text(CENV, encoding="utf-8")
        (self.depot / "platformio_tasmota_env32.ini").write_text(ENV32, encoding="utf-8")
        (self.depot / "platformio_tasmota_env.ini").write_text(ENV8266, encoding="utf-8")
        # mention « FS aussi flashe » : A embarque des fichiers (custom_files_upload), SANS littlefs.bin
        # (apres une purge de .pio/build, post_esp32 le reconstruira quand meme a l'upload)
        scenario = self.t / "scenario.json"
        scenario.write_text(json.dumps(SCENARIO), encoding="utf-8")
        environ = dict(os.environ, BUILD_WEB_PIO=str(FAUX_PIO), BUILD_WEB_FAUX_SCENARIO=str(scenario),
                       OUTILS_TASMOTA_DOSSIER=str(self.t / "outils"), PYTHONIOENCODING="utf-8")
        environ.pop("BUILD_WEB_FAUX_JOURNAL", None)
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        self.commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port), str(self.depot)]
                         + (["--temoin"] if temoin else []))
        self.environ = environ
        self.lance_serveur()
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
        self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                        "--window-size=1280,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend_http(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        page = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(page["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)

    def lance_serveur(self):
        self.serveur = subprocess.Popen(self.commande, env=self.environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend_http(self.url + "execution", 20)

    def redemarre_serveur(self):
        """Comme l'outil tue avec VS Code puis relance par l'annuaire : meme port, numerotation repartie de 1."""
        tue_arbre(self.serveur)
        self.serveur.wait(10)
        self.lance_serveur()

    def _attend_http(self, url, delai):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            if self.serveur.poll() is not None:
                raise RuntimeError("le serveur s'est arrete : " + self.serveur.stdout.read().decode("utf-8", "replace"))
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    return r.read().decode("utf-8")
            except OSError:
                time.sleep(0.2)
        raise TimeoutError(f"{url} ne repond pas en {delai} s")

    def ouvre(self):
        self.cdp.appel("Page.navigate", url=self.url)
        time.sleep(2.5)                     # /envs + /execution + premiers evenements du flux

    def ferme(self):
        tue_arbre(self.chrome)
        tue_arbre(self.serveur)
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


# -- verifications -----------------------------------------------------------------------------------

JS_CHARGEMENT = """(() => {
  const fam = [...document.querySelectorAll('details.famille')];
  return {familles: fam.map(d => d.querySelector('summary').firstChild.textContent),
          ouvertes: fam.map(d => d.open),
          sous_groupes: [...document.querySelectorAll('details.sous-groupe > summary')].map(s => s.firstChild.textContent),
          lignes: document.querySelectorAll('.env').length,
          bouton: document.getElementById('lancer').textContent};
})()"""


def coche(cdp, selecteur, valeur=True):
    return cdp.js(f"""(() => {{ const c = document.querySelector({json.dumps(selecteur)});
      if (!c) return 'absent'; if (c.checked !== {str(valeur).lower()}) c.click(); return c.checked; }})()""")


def sonde_page(m, capture):
    cdp = m.cdp
    m.ouvre()
    etat = cdp.js(JS_CHARGEMENT)
    verifie(cdp.erreurs(), [], "chargement : aucune erreur JS")
    if not isinstance(etat, dict) or "familles" not in etat:
        verifie(etat, "etat de la page", "chargement : page lisible")
        return
    verifie(etat["familles"], ["Mes cartes", "Mes bases", "Tasmota (amont)"], "chargement : 3 familles")
    verifie(etat["ouvertes"], [True, True, False], "chargement : amont repliee, les deux autres ouvertes")
    verifie(etat["sous_groupes"], ["Safeboot", "ESP32", "Langues", "ESP8266"], "chargement : 4 sous-groupes amont")
    verifie(etat["lignes"], 8, "chargement : une ligne par env (4 perso + 4 amont)")
    cdp.js("document.querySelector('details[data-famille=amont] > summary').click()")
    cdp.js("document.querySelector('details[data-sous-groupe=esp8266] > summary').click()")
    verifie(cdp.js("""[document.querySelector('details[data-famille=amont]').open,
                       document.querySelector('details[data-sous-groupe=esp8266]').open,
                       document.querySelector('.env[data-env=tasmota] .methode button:nth-child(2)').disabled]"""),
            [True, True, True], "familles depliables ; OTA grise pour l'ESP8266")

    # mention « le FS sera aussi flashe » : A (custom_files_upload avec fichiers), upload coche, methode COM
    coche(cdp, f"#env-{A}")
    coche(cdp, f"#env-{C}")
    coche(cdp, 'input[name=action][value="upload"]')
    verifie(cdp.js(f"document.querySelector('.env[data-env=\"{A}\"] .notes').textContent.includes('sera aussi flashé')"),
            True, "mention : le file system (persist compris) sera aussi flashe (sans littlefs.bin)")
    verifie(cdp.js(f"document.querySelector('.env[data-env=\"{C}\"] .notes').textContent.includes('sera aussi flashé')"),
            False, "mention : temoin, env sans fichiers (no_files) -> pas de mention")
    coche(cdp, f"#env-{C}", False)
    coche(cdp, 'input[name=action][value="upload"]', False)
    verifie(cdp.js(f"document.querySelector('.env[data-env=\"{A}\"] .notes').textContent.includes('sera aussi flashé')"),
            False, "mention : disparait quand upload est decoche (temoin)")

    # OTA sans IP connue : champ requis
    cdp.js(f"document.querySelector('.env[data-env=\"{C}\"] .methode button:nth-child(2)').click()")
    verifie(cdp.js(f"document.querySelector('.env[data-env=\"{C}\"] .champ').classList.contains('requis')"), True,
            "OTA sans IP : champ signale requis")
    cdp.js(f"document.querySelector('.env[data-env=\"{C}\"] .methode button:nth-child(1)').click()")

    # port d'un env ecrivable : POST /port puis « repartira de zero » (depot d'essai)
    cdp.js(f"""(() => {{ const c = document.querySelector('.env[data-env="{C}"] .champ');
      c.focus(); c.value = 'com21'; c.dispatchEvent(new Event('input')); c.dispatchEvent(new Event('change')); c.blur(); }})()""")
    note = attend(cdp, f"(() => {{ const n = document.querySelector('.env[data-env=\"{C}\"] .notes');"
                       " return n && n.textContent.includes('repartira de zéro') ? n.textContent : ''; })()", 8)
    verifie(bool(note), True, "port : note « le prochain build repartira de zero »")
    texte_ini = (m.depot / "platformio_tasmota_cenv.ini").read_text(encoding="utf-8")
    verifie("upload_port             = COM21" in texte_ini, True, "port : ecrit dans le cenv du depot d'essai")

    # lancement du scenario : 3 envs, compiler, B en echec
    for env in (A, B, C):
        coche(cdp, f"#env-{env}")
    coche(cdp, 'input[name=action][value="compiler"]')
    verifie(cdp.js("document.getElementById('lancer').textContent"), "Lancer (3 env, l'un après l'autre)",
            "lancement : libelle du bouton")
    cdp.js("document.getElementById('lancer').click()")
    attend(cdp, f"!!document.querySelector('.bloc[data-bloc=\"{A}\"] .durees')", 10, 0.1)
    if capture:
        cdp.capture(Path(capture) / "build-page-en-cours.png")
    verifie(cdp.js("document.getElementById('arret-immediat').disabled"), False, "lancement : arret immediat actif pendant la serie")
    fin = attend(cdp, "document.getElementById('etat').textContent.startsWith('terminé') && document.getElementById('recap').textContent", 40)
    verifie(bool(fin), True, "lancement : fin recue")
    time.sleep(0.4)
    r = cdp.js(f"""(() => {{
      const bloc = e => document.querySelector('.bloc[data-bloc="' + e + '"]');
      const larg = e => bloc(e).querySelector('.rang[data-action=compiler] .barre span').style.width;
      return {{bandeaux: [...document.querySelectorAll('.bandeau.echec')].map(b => b.dataset.env),
              texte_bandeau: (document.querySelector('.bandeau.echec') || {{}}).textContent || '',
              barres: [larg('{A}'), larg('{B}'), larg('{C}')],
              durees: [bloc('{A}').querySelectorAll('.durees').length, bloc('{C}').querySelectorAll('.durees').length],
              texte_durees: bloc('{A}').querySelector('.durees').textContent,
              bloc_echec: bloc('{B}').classList.contains('echec'),
              extrait: (bloc('{B}').querySelector('pre.extrait') || {{}}).textContent || '',
              recap: document.getElementById('recap').textContent,
              bouton_actif: !document.getElementById('lancer').disabled}};
    }})()""")
    verifie(r.get("bandeaux"), [B], "suivi : un seul bandeau rouge, sur l'env en echec")
    verifie("Compiler le firmware" in r.get("texte_bandeau", ""), True, "suivi : le bandeau nomme l'action")
    barres = r.get("barres") or ["?", "100%", "?"]
    verifie((barres[0], barres[1] != "100%", barres[2]), ("100%", True, "100%"),
            f"suivi : barre a 100 % sur les envs reussis, pas sur l'echec ({barres})")
    verifie([n > 0 for n in r.get("durees", [0, 0])], [True, True], "suivi : durees affichees")
    verifie("Compilation" in r.get("texte_durees", ""), True, "suivi : duree de compilation affichee")
    verifie((r.get("bloc_echec"), "error:" in r.get("extrait", "")), (True, True), "suivi : bloc en echec et extrait d'erreur")
    verifie("Fichiers réécrits par le build" in r.get("recap", ""), True, "suivi : rappel final des fichiers modifies")
    verifie(r.get("bouton_actif"), True, "suivi : bouton Lancer reactive a la fin")
    cdp.js(f"document.querySelector('.bloc[data-bloc=\"{B}\"] details.journal > summary').click()")
    journal = attend(cdp, f"(() => {{ const p = document.querySelector('.bloc[data-bloc=\"{B}\"] details.journal pre');"
                          f" return p.textContent.includes('pio run -e {B}') ? p.textContent : ''; }})()", 8)
    verifie(bool(journal) and "error:" in journal, True, "journal : deplie, texte du journal de l'env")
    if capture:
        cdp.capture(Path(capture) / "build-page-fin.png")

    # reprise du flux : rechargement de la page -> meme etat reconstruit depuis le flux rejoue
    m.ouvre()
    verifie(attend(cdp, "[...document.querySelectorAll('.bandeau.echec')].map(b => b.dataset.env).join()", 8), B,
            "rechargement : l'etat du dernier lancement est reconstruit depuis le flux")

    sonde_redemarrage(m)
    sonde_sortie(m)
    sonde_effacement(m)
    sonde_synthetique(cdp)

    # largeur telephone : colonnes empilees, pas de defilement horizontal
    cdp.appel("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=True)
    time.sleep(0.8)
    tel = cdp.js("""(() => { const l = document.getElementById('liste').getBoundingClientRect(),
      a = document.querySelector('aside.commandes').getBoundingClientRect();
      return {empile: a.top >= l.bottom - 1, large: document.documentElement.scrollWidth}; })()""")
    verifie((tel.get("empile"), tel.get("large") <= 390), (True, True), f"telephone : colonnes empilees, largeur {tel.get('large')} px")
    if capture:
        cdp.capture(Path(capture) / "build-page-telephone.png")
    # seules erreurs admises : les coupures du flux, et des lectures de /sortie en vol, pendant le redemarrage VOULU
    # du serveur (sonde_redemarrage)
    coupures = [e for e in cdp.erreurs() if e.startswith("journal Chrome") and ("/flux" in e or "/sortie?" in e)
                and ("ERR_CONNECTION_RESET" in e or "ERR_CONNECTION_REFUSED" in e)]
    verifie([e for e in cdp.erreurs() if e not in coupures], [], "fin : aucune erreur JS pendant toute la sonde")
    verifie(bool(coupures), True, "fin : les coupures du flux pendant le redemarrage ont bien ete vues (temoin du filtre)")


# Evenements injectes dans traite() (fonction globale de la page) : chemins que le faux pio ne produit pas
# (OTA par la page, preparation du FS, avertissement, attente d'un build externe). Sans numero `n` :
# la garde de reprise du flux ne les filtre pas.
SYNTHETIQUES = [
    {"type": "debut", "env": None, "actions": ["compiler", "upload", "uploadfs"],
     "lignes": [{"env": "D", "methode": "ota", "port": "", "ip": "192.168.0.99"},
                {"env": "E", "methode": "com", "port": "COM5", "ip": ""}]},
    {"type": "debut", "env": "D", "actions": ["compiler", "upload", "uploadfs"], "methode": "ota", "ip": "192.168.0.99"},
    {"type": "etape", "env": "D", "action": "upload", "etape": "Pré-build", "pourcent": None, "detail": "", "commande": "pio run -e D"},
    {"type": "etape", "env": "D", "action": "upload", "etape": "Compilation", "pourcent": 50, "detail": "1/2 fichiers"},
    {"type": "duree", "env": "D", "action": "upload", "etape": "Pré-build", "secondes": 1.0},
    {"type": "etape", "env": "D", "action": "upload", "etape": "Édition des liens", "pourcent": 100, "detail": "terminé"},
    {"type": "duree", "env": "D", "action": "upload", "etape": "Édition des liens", "secondes": 2.0},
    {"type": "etape", "env": "D", "action": "upload", "etape": "Téléversement", "pourcent": None, "detail": "vers 192.168.0.99"},
    {"type": "duree", "env": "D", "action": "upload", "etape": "Téléversement", "secondes": 3.0},
    {"type": "etape", "env": "D", "action": "buildfs", "etape": "Construction du FS", "pourcent": None, "detail": ""},
    {"type": "duree", "env": "D", "action": "buildfs", "etape": "Construction du FS", "secondes": 4.0},
    {"type": "etape", "env": "D", "action": "uploadfs", "etape": "Vérification après redémarrage", "pourcent": None,
     "detail": "AVERTISSEMENT : _persist.json relu différent ; sauvegarde du persist d'avant : X"},
    {"type": "fin_env", "env": "D", "resultat": "succes", "secondes": 30,
     "statuts": {"compiler": "succes", "upload": "succes", "uploadfs": "succes"}},
    {"type": "attente", "env": "E", "builds": ["détection impossible"]},
]
JS_SYNTHETIQUE = """(() => {
  const d = document.querySelector('.bloc[data-bloc="D"]');
  const rang = a => d.querySelector('.rang[data-action=' + a + ']');
  const at = document.querySelector('.bandeau.attente');
  return {rangs: [...d.querySelectorAll('.rang')].map(r => r.dataset.action),
          compiler: (rang('compiler').querySelector('.durees') || {}).textContent || '',
          upload: (rang('upload').querySelector('.durees') || {}).textContent || '',
          uploadfs: (rang('uploadfs').querySelector('.durees') || {}).textContent || '',
          avert: document.querySelectorAll('.bandeau.avertissement').length,
          echecs: document.querySelectorAll('.bandeau.echec').length,
          attente: at ? at.textContent : ''};
})()"""


def injecte(cdp, evenements):
    cdp.js("(() => { const ev = " + json.dumps(evenements, ensure_ascii=False) + "; ev.forEach(e => traite(e)); return true; })()")
    time.sleep(0.4)                          # rendu groupe (60 ms)


def sonde_synthetique(cdp):
    injecte(cdp, SYNTHETIQUES)
    r = cdp.js(JS_SYNTHETIQUE)
    verifie(r.get("rangs"), ["compiler", "upload", "uploadfs"], "synthetique : preparation buildfs sans ligne fantome")
    verifie(("Pré-build" in r.get("compiler", ""), "Pré-build" in r.get("upload", ""), "Téléversement" in r.get("upload", "")),
            (True, False, True), "synthetique : compilation d'un upload affichee sur la ligne compiler")
    verifie("préparation : Construction du FS" in r.get("uploadfs", ""), True, "synthetique : duree de preparation sur la ligne uploadfs")
    verifie((r.get("avert"), r.get("echecs")), (1, 0), "synthetique : AVERTISSEMENT = bandeau orange, pas un echec")
    verifie("Détection des builds en cours impossible" in r.get("attente", ""), True, "synthetique : attente, detection impossible")
    injecte(cdp, [{"type": "attente", "env": "E", "builds": ["pio run -e x (VS Code)"]}])
    verifie("Un build tourne ailleurs (pio run -e x (VS Code))" in cdp.js(JS_SYNTHETIQUE).get("attente", ""), True,
            "synthetique : attente, build nomme")
    injecte(cdp, [{"type": "attente", "env": "E", "builds": []}])
    verifie((cdp.js(JS_SYNTHETIQUE).get("attente"),
             cdp.js("document.querySelector('.bloc[data-bloc=\"E\"]').textContent.includes('Reprise')")), ("", True),
            "synthetique : builds=[] -> bandeau retire, reprise notee")
    # M4 : « FS aussi flashe avec le firmware » seulement pour un upload par cable (ligne post_esp32)
    ligne = "Utilisera une commande de téléchargement personnalisée au lieu de esptool"
    aussi = "(() => [...document.querySelectorAll('.bloc')].filter(b => b.textContent.includes("             "'aussi flashé avec le firmware')).map(b => b.dataset.bloc).join())()"
    injecte(cdp, [{"type": "ligne", "env": "E", "action": "compiler", "texte": ligne},
                  {"type": "ligne", "env": "D", "action": "upload", "texte": ligne},
                  {"type": "ligne", "env": "D", "action": "uploadfs", "texte": ligne}])
    verifie(cdp.js(aussi), "", "synthetique : ligne post_esp32 pendant compiler (COM) ou en OTA -> pas de mention FS")
    injecte(cdp, [{"type": "ligne", "env": "E", "action": "upload", "texte": ligne}])
    verifie(cdp.js(aussi), "E", "synthetique : temoin, upload par cable -> mention FS aussi flashe")


def rgb(texte):
    """(r, g, b) d'une couleur calculee « rgb(r, g, b) » ; (0, 0, 0) sinon."""
    try:
        return tuple(int(float(x)) for x in texte[texte.index("(") + 1:texte.index(")")].split(",")[:3])
    except ValueError:
        return (0, 0, 0)


def sonde_sortie(m):
    """A9 : panneau « Sortie » de l'env en cours, rempli pendant le pio run (journal lu par increments)."""
    cdp = m.cdp
    (m.t / "scenario.json").write_text(json.dumps({A: {"build": {"lignes": SORTIE_A, "delai": 0.03}}}), encoding="utf-8")
    for env in (A, B, C):
        coche(cdp, f"#env-{env}", env == A)
    for action in ("compiler", "upload", "buildfs", "uploadfs"):
        coche(cdp, f'input[name=action][value="{action}"]', action == "compiler")
    cdp.js("document.getElementById('lancer').click()")
    console = f"document.querySelector('.bloc[data-bloc=\"{A}\"] details.sortie .console')"
    attend(cdp, f"(() => {{ const c = {console}; return !!c && document.getElementById('etat').textContent === "
                f"'lancement en cours' && c.textContent.includes(\"'z' was not declared\"); }})()", 10, 0.1)
    r = cdp.js(f"""(() => {{ const c = {console}; if (!c) return {{}};
      const ligne = t => [...c.children].find(x => x.textContent.includes(t));
      const coul = x => x ? getComputedStyle(x).color : '';
      return {{ouvert: c.closest('details').open, lignes: c.children.length, deborde: c.scrollHeight > c.clientHeight + 20,
              en_bas: c.scrollTop + c.clientHeight >= c.scrollHeight - 2, en_cours: document.getElementById('etat').textContent,
              erreur: coul(ligne("'z' was not declared")), avert: coul(ligne('warning: unused')), normal: coul(ligne('f3.cpp.o')),
              chasse: getComputedStyle(c).fontFamily, fond: getComputedStyle(c).backgroundColor,
              processing: [...c.children].filter(x => x.textContent.startsWith('Processing')).length}}; }})()""") or {}
    verifie((r.get("ouvert"), r.get("deborde"), r.get("en_bas"), r.get("en_cours")), (True, True, True, "lancement en cours"),
            f"sortie : panneau ouvert et rempli PENDANT le pio run, defile seul tant qu'on est en bas ({r.get('lignes')} lignes)")
    rouge, orange, normal = rgb(r.get("erreur", "")), rgb(r.get("avert", "")), rgb(r.get("normal", ""))
    verifie((rouge[0] > 200 and rouge[1] < 140, orange[0] > 200 and 110 < orange[1] < 200 and orange[2] < 110, normal[0] < 240),
            (True, True, True), f"sortie : erreur en rouge, avertissement en orange, le reste neutre ({rouge}, {orange}, {normal})")
    verifie(("monospace" in r.get("chasse", "") or "Consolas" in r.get("chasse", ""), sum(rgb(r.get("fond", ""))) < 150),
            (True, True), "sortie : chasse fixe sur fond sombre")
    verifie(r.get("processing"), 1, "sortie : rien n'est rajoute deux fois (lecture par increments)")
    cdp.js(f"(() => {{ const c = {console}; c.scrollTop = 0; c.dispatchEvent(new Event('scroll')); return true; }})()")
    attend(cdp, f"{console}.textContent.includes('Wrote 163840')", 8, 0.1)
    r2 = cdp.js(f"""(() => {{ const c = {console}; const l = [...c.children];
      const prog = l.filter(x => /^\\s*Writing at 0x/.test(x.textContent));
      return {{haut: c.scrollTop, lignes: l.length, prog: prog.length, texte: prog.map(x => x.textContent).join('|'),
              vides: l.filter(x => !x.textContent.trim()).length}}; }})()""") or {}
    verifie((r2.get("haut"), r2.get("lignes", 0) > r.get("lignes", 0)), (0, True),
            "sortie : remonte par l'utilisateur -> plus de defilement auto, les lignes arrivent quand meme")
    verifie((r2.get("prog"), "100.0%" in r2.get("texte", ""), r2.get("vides")), (1, True, 0),
            f"sortie : esptool qui reecrit sa ligne -> une ligne par zone, derniere valeur, sans lignes vides ({r2.get('texte')})")
    brut = cdp.js(f"fetch('/journal?env={A}').then(r => r.text()).then(t => (t.match(/Writing at 0x/g) || []).length)")
    verifie(brut, 3, "sortie : temoin, le journal brut porte bien 3 lignes de progression d'esptool")
    cdp.js(f"(() => {{ const c = {console}; c.scrollTop = c.scrollHeight; c.dispatchEvent(new Event('scroll')); return true; }})()")
    attend(cdp, "document.getElementById('etat').textContent.startsWith('terminé')", 15)
    fin = attend(cdp, f"(() => {{ const c = {console}; return c.textContent.includes('code de sortie 0') && "
                      "c.scrollTop + c.clientHeight >= c.scrollHeight - 2; })()", 5, 0.1)
    verifie(fin, True, "sortie : revenu en bas -> defilement auto repris, journal lu jusqu'au bout apres la fin")


EFFACEMENT_A = ["Processing {env} (platform: espressif32)", "Compiling .pio/build/{env}/src/a.cpp.o",
                "Linking .pio/build/{env}/firmware.elf",
                "Utilisera une commande de téléchargement personnalisée pour l'opération de flashage afin d'ajouter le "
                "système de fichiers défini pour cette cible de compilation.",
                "Looking for upload port...", "Erasing...", "esptool v5.4.0", "Erasing flash memory (this may take a while)...",
                "@pause 0.6", "Flash memory erased successfully in 0.6 seconds.", "Uploading .pio/build/{env}/firmware.bin",
                "Writing at 0x00010000 (50 %)", "Writing at 0x00020000 (100 %)", "[SUCCESS] Took 1.20 seconds"]


def sonde_effacement(m):
    """A10 : « Effacer puis téléverser » : exclusive avec upload, COM seulement, confirmation, etape d'effacement."""
    cdp = m.cdp
    (m.t / "scenario.json").write_text(json.dumps({A: {"erase_upload": {"lignes": EFFACEMENT_A}}}), encoding="utf-8")
    case = lambda a: f'input[name=action][value="{a}"]'
    etat = lambda: cdp.js("['upload', 'erase_upload'].map(a => document.querySelector('input[name=action][value=\"' + a + '\"]').checked)")
    ota = lambda env: f"document.querySelector('.env[data-env=\"{env}\"] .methode button:nth-child(2)')"
    for env in (A, B, C):
        coche(cdp, f"#env-{env}", env in (A, C))
    for action in ("compiler", "upload", "erase_upload", "buildfs", "uploadfs"):
        coche(cdp, case(action), action == "upload")
    coche(cdp, case("erase_upload"))
    verifie(etat(), [False, True], "effacer : cocher « Effacer puis téléverser » décoche « Téléverser le firmware »")
    coche(cdp, case("upload"))
    verifie(etat(), [True, False], "effacer : et inversement")
    coche(cdp, case("erase_upload"))
    verifie([cdp.js(f"document.querySelector('.env[data-env=\"{e}\"] .notes').textContent.includes('sera aussi flashé')") for e in (A, C)],
            [True, False], "effacer : mention « FS aussi flashé » selon l'env (temoin : env sans fichiers)")
    verifie(cdp.js(f"{ota(C)}.disabled"), True, "effacer : OTA grise sur les lignes tant que l'action est cochee")
    coche(cdp, case("erase_upload"), False)
    cdp.js(f"{ota(C)}.click()")
    verifie(cdp.js(f"document.querySelector('{case('erase_upload')}').disabled"), True,
            "effacer : action grisee quand une ligne cochee est en OTA")
    cdp.js(f"document.querySelector('.env[data-env=\"{C}\"] .methode button:nth-child(1)').click()")
    verifie(cdp.js(f"document.querySelector('{case('erase_upload')}').disabled"), False, "effacer : temoin, ligne revenue en COM -> action disponible")
    coche(cdp, f"#env-{C}", False)
    coche(cdp, case("erase_upload"))
    cdp.js("window.confirm = t => { window._confirmation = t; return false; }")      # l'utilisateur refuse
    cdp.js("document.getElementById('lancer').click()")
    time.sleep(0.8)
    texte = cdp.js("window._confirmation || ''") or ""
    derniers = cdp.js("fetch('/envs').then(r => r.json()).then(d => (d.derniers.actions || []).join())")
    verifie(("remplacés par ceux du dépôt" in texte, "persist" in texte, A in texte, derniers), (True, True, True, "compiler"),
            "effacer : confirmation (persist et reglages remplaces par ceux du depot) ; refusee -> rien lance")
    cdp.js("window.confirm = t => true")
    cdp.js("document.getElementById('lancer').click()")
    # attendre le statut final sur la ligne elle-meme : l'etat « terminé » est pose avant le rendu groupe du bloc (60 ms)
    rang = attend(cdp, f"(() => {{ const r = document.querySelector('.bloc[data-bloc=\"{A}\"] .rang[data-action=erase_upload]');"
                       " return r && /réussi|échec|annulée/.test(r.textContent) ? r.textContent : ''; })()", 15)
    rang = rang if isinstance(rang, str) else ""
    verifie(("Effacer puis téléverser" in rang, "Effacement de la flash" in rang, "réussi" in rang), (True, True, True),
            f"effacer : acceptee -> ligne « Effacer puis téléverser », duree d'effacement, reussi ({rang[:120]})")
    verifie(cdp.js(f"document.querySelector('.bloc[data-bloc=\"{A}\"]').textContent.includes('aussi flashé avec le firmware')"), True,
            "effacer : FS aussi flashe signale dans le bloc (ligne post_esp32 d'un erase_upload)")


def sonde_redemarrage(m):
    """Outil redemarre sous la page ouverte, en plein lancement : la page doit suivre le lancement suivant."""
    cdp = m.cdp
    cdp.js("document.getElementById('lancer').click()")
    verifie(bool(attend(cdp, "document.getElementById('etat').textContent === 'lancement en cours' && "
                             f"!!document.querySelector('.bloc.encours')", 10, 0.1)), True,
            "redemarrage : un lancement est en cours avant de tuer le serveur")
    m.redemarre_serveur()
    libre = attend(cdp, "!document.getElementById('lancer').disabled && document.getElementById('etat').textContent", 20)
    verifie(libre, "au repos", "redemarrage : apres reconnexion, lancement coupe constate, bouton Lancer reactive")
    verifie(attend(cdp, "[...document.querySelectorAll('.bandeau.avertissement')].some(b => b.textContent.includes('interrompu'))",
                   3, 0.1), True,                    # rendu groupe : bandeaux dessines ~60 ms apres le bouton
            "redemarrage : bandeau « lancement interrompu »")
    cdp.js("document.getElementById('lancer').click()")
    fin = attend(cdp, "document.getElementById('etat').textContent.startsWith('terminé') && document.getElementById('recap').textContent", 40)
    verifie(bool(fin), True, "redemarrage : le lancement suivant est suivi jusqu'a fin")
    time.sleep(0.4)
    r = cdp.js(f"""(() => ({{echecs: [...document.querySelectorAll('.bandeau.echec')].map(b => b.dataset.env),
      barre: document.querySelector('.bloc[data-bloc="{A}"] .rang[data-action=compiler] .barre span').style.width}}))()""")
    verifie((r.get("echecs"), r.get("barre")), ([B], "100%"), "redemarrage : bandeau rouge et barre a 100 % du nouveau lancement")


def sonde_temoin(m):
    m.ouvre()
    erreurs = m.cdp.erreurs()
    print("     erreurs vues sur le temoin : " + (" | ".join(erreurs) or "aucune"), flush=True)
    verifie(any("TypeError" in e for e in erreurs), True, "temoin : l'erreur JS volontaire est detectee")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page Build et televersement.")
    options.add_argument("--sans-temoin", action="store_true", help="ne pas rejouer la page avec une erreur volontaire")
    options.add_argument("--capture", help="dossier ou ecrire les captures PNG")
    options.add_argument("--serveur", nargs=2, metavar=("PORT", "DEPOT"), help=argparse.SUPPRESS)
    options.add_argument("--temoin", action="store_true", help=argparse.SUPPRESS)
    args = options.parse_args()
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.temoin)

    for temoin in ([False] if args.sans_temoin else [False, True]):
        print(f"\n=== {'TEMOIN (erreur JS volontaire)' if temoin else 'page reelle'} ===", flush=True)
        m = None
        try:
            m = Montage()
            m.demarre(temoin)
            sonde_temoin(m) if temoin else sonde_page(m, args.capture)
        except FileNotFoundError as erreur:
            print(f"BLOQUE : {erreur}")
            return 3
        except Exception as erreur:
            verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
        finally:
            if m:
                m.ferme()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
