"""Sonde Chrome de la page de la synchro du fork (synchro_fork_page.PAGE + assistant) : la page s'execute-t-elle
vraiment, et l'assistant pas a pas mene-t-il un merge en conflit jusqu'au push ?

UTILISATION (a la main ; aucun pio, aucun reseau, jamais le vrai depot ; Chrome tourne ~1 min)
    python -u outils_docs/scripts_python/maintenance/test_synchro_fork_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la vraie page passe toutes les verifications ET le temoin (la meme page dont le SCRIPT de
l'assistant reference un id absent) est bien detecte. Sans temoin, un vert ne prouverait rien.

Pourquoi un vrai navigateur : un flux SSE ne se termine jamais (pas de --virtual-time-budget) ; Chrome est pilote
par DevTools (client WebSocket en stdlib, copie de outils_pc/test_build_page_chrome.py), erreurs captees par
Runtime.exceptionThrown, console.error et Log.entryAdded.

Montage : le serveur est ce script lui-meme (mode --serveur, processus fils, port libre) :
  - un FAUX depot (faux_depot_synchro) avec un conflit a.txt entre le fork (1 commit non pousse) et l'amont ;
  - une session dont le script de merge est un faux (imprime une ligne, sort en 0) ;
  - aucun build detecte (builds_en_cours -> []) et /etat factice (pas de GitHub).
Scenario : Diagnostic seul -> assistant, fusion_b courante -> Lancer le merge -> 1 conflit -> vue deux diffs ->
Prendre l'amont -> plus de conflit -> serveur redemarre + page rechargee en plein merge -> Terminer -> pousser.
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

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
CHROMES = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
           Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
           Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"]
FAUX_SCRIPT = 'print("diagnostic simule", flush=True)\n'
INJECTION_TEMOIN = '\n$("assistant-absent").onclick = null;   // TEMOIN : TypeError au chargement\n'
TITRE_HOSTILE = '<img src=x onerror="window.__xss=1">'
HOSTILE = "&lt;b&gt;x y.txt"      # AA (ajoute des deux cotes) ; commun.txt = UD (modifie ici, supprime par l'amont)
TEMOINS = {"script": "SCRIPT casse (id absent)", "echappe": "echappe() retire du titre de commit"}
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

def mode_serveur(port, travail, faux, temoin):
    import synchro_fork_session
    import synchro_fork_web    # ajoute outils_pc au chemin
    import synchro_fork_etat
    import synchro_fork_page
    import acces_web
    from http.server import ThreadingHTTPServer
    travail = Path(travail)
    if temoin == "script":
        import synchro_fork_page_assistant as pa
        assert synchro_fork_page.PAGE.count(pa.SCRIPT) == 1, "SCRIPT de l'assistant introuvable dans la page"
        synchro_fork_page.PAGE = synchro_fork_page.PAGE.replace(pa.SCRIPT, pa.SCRIPT + INJECTION_TEMOIN)
    elif temoin == "echappe":
        avant = "${echappe(c.titre)}</span>`))"
        assert synchro_fork_page.PAGE.count(avant) == 1, "echappe() du titre de commit introuvable dans la page"
        synchro_fork_page.PAGE = synchro_fork_page.PAGE.replace(avant, "${c.titre}</span>`))")
    # /etat factice : pas de GitHub ; seul operation_git lit le faux depot (c'est lui qui declenche l'assistant)
    synchro_fork_etat.etat = lambda: {
        "branche": "development", "origin": "banc/origin", "upstream": "banc/upstream", "avance": 1, "retard": 1,
        "commits": [], "non_pousses": 1, "fichiers": [], "non_suivis": 0, "journal_modifie": False,
        "operation_git": synchro_fork_etat.operation_git(travail), "erreur": ""}
    acces = acces_web.Acces(port, True, "sonde")
    session = synchro_fork_session.Session(dossier=faux, racine=travail)
    gest = synchro_fork_web.fabrique_gestionnaire(session, acces, racine=travail, builds_en_cours=lambda: [])
    serveur = ThreadingHTTPServer((acces.hote, port), gest)
    serveur.daemon_threads = True
    serveur.serve_forever()
    return 0


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
        self.t = Path(tempfile.mkdtemp(prefix="sonde_synchro_fork_"))
        self.serveur = self.chrome = None

    def demarre(self, temoin):
        import faux_depot_synchro as fd
        (self.t / "depot").mkdir()
        self.travail = fd.cree(self.t / "depot")
        # cas hostile : titre de commit en HTML, nom de fichier avec entites et espace (Windows refuse < > " dans un nom)
        fd.commit_amont(self.t / "depot", {"a.txt": "amont\n", HOSTILE: "amont\n", "commun.txt": None}, TITRE_HOSTILE)
        fd.commit_local(self.travail, {"a.txt": "local\n", HOSTILE: "local\n", "commun.txt": "local\n"}, "local change a")
        self.faux = self.t / "faux"
        self.faux.mkdir()
        (self.faux / "synchronise_fork_tasmota.py").write_text(FAUX_SCRIPT, encoding="utf-8")
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        self.commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port),
                          str(self.travail), str(self.faux)] + (["--temoin", temoin] if temoin else []))
        self.environ = dict(os.environ, PYTHONIOENCODING="utf-8", OUTILS_TASMOTA_DOSSIER=str(self.t / "outils"))
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
        """Serveur arrete en plein merge puis relance (meme port) : l'etat vit dans .git, pas dans le serveur."""
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
        time.sleep(2.0)                     # /etat, /aide, flux

    def ferme(self):
        tue_arbre(self.chrome)
        tue_arbre(self.serveur)
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


# -- verifications -----------------------------------------------------------------------------------

ASSISTANT = "document.getElementById('assistant')"


def visible(css):
    return f"(() => {{ const e = document.querySelector({json.dumps(css)}); return !!e && getComputedStyle(e).display !== 'none'; }})()"


def etape(identifiant, statut):
    return (f"(() => {{ const e = document.querySelector('#assistant li[data-etape=\"{identifiant}\"]');"
            f" return !!e && e.classList.contains('{statut}'); }})()")


def clique(texte, zone="document"):
    """Clique le premier bouton visible et actif dont le texte contient `texte` ; rend vrai s'il existe."""
    return (f"(() => {{ const z = {zone}; const b = z && [...z.querySelectorAll('button')].find(b => !b.disabled"
            f" && b.offsetParent !== null && b.textContent.includes({json.dumps(texte)})); if (b) b.click(); return !!b; }})()")


LIGNES_CONFLITS = "document.querySelectorAll('#assistant table.conflits tbody tr').length"


def erreurs(cdp):
    """Erreurs de la page, hors le 404 du favicon (le serveur n'en sert pas)."""
    return [e for e in cdp.erreurs() if "favicon.ico" not in e]


def sonde_page(m):
    cdp = m.cdp
    m.ouvre()
    verifie(cdp.js("!!document.querySelector('nav#onglets details#avance')"), True, "<details> « Avancé » dans la barre d'onglets")
    verifie(cdp.js("document.querySelector('#avance summary')?.textContent"), "Avancé", "résumé du <details> : Avancé")
    cdp.js("document.querySelector('button[data-onglet=\"rebase\"]').click()")
    verifie(cdp.js(visible("#onglet-rebase")), True, "onglet rebase accessible")
    verifie(cdp.js("document.querySelector('#onglet-rebase').textContent.includes('ne pas l\\'alterner avec le merge')"), True,
            "avertissement en tête de l'onglet rebase")
    cdp.js("document.querySelector('button[data-onglet=\"merge\"]').click()")
    verifie(cdp.js("!document.getElementById('assistant') || getComputedStyle(document.getElementById('assistant')).display === 'none'"),
            True, "avant tout diagnostic : assistant absent ou masqué")
    # 0. arbre sale : a.txt (touche aussi par l'amont) et un fichier sans recouvrement -> classes affichees, diff au clic
    (m.travail / "a.txt").write_text("sale\n", encoding="utf-8")
    (m.travail / "dossier é" / "fichier x.txt").write_text("sale aussi\n", encoding="utf-8")
    verifie(cdp.js(clique("Diagnostic seul")), True, "bouton « Diagnostic seul » cliquable")
    verifie(bool(attend(cdp, etape("arbre", "bloquee"), 25)), True, "arbre sale : étape arbre bloquée")
    lignes = "[...document.querySelectorAll('#assistant li[data-etape=\"arbre\"] li')].map(l => [l.querySelector('button').textContent, "             "l.querySelector('[data-classe]').dataset.classe, l.querySelector('[data-classe]').textContent])"
    verifie(cdp.js(lignes), [["a.txt", "amont", "touché aussi par l'amont"], ["dossier é/fichier x.txt", "libre", "sans recouvrement"]],
            "arbre : classement affiché (touché aussi par l'amont / sans recouvrement)")
    verifie(cdp.js("getComputedStyle(document.querySelector('[data-classe=\"amont\"]')).color"), "rgb(240, 120, 120)",
            "arbre : « touché aussi par l'amont » en rouge")
    cdp.js("document.querySelector('#assistant [data-diff=\"a.txt\"]').click()")
    verifie(bool(attend(cdp, "!!document.querySelector('#assistant li[data-etape=\"arbre\"] pre[data-diff-arbre]') && "
                             "document.querySelector('pre[data-diff-arbre]').textContent.includes('+sale')", 15)),
            True, "arbre : clic sur le chemin -> diff du fichier dans l'étape")
    # commit depuis la page : a.txt decoche, message tape (accents retires), seul le fichier sans recouvrement part
    verifie(cdp.js("document.querySelectorAll('#assistant input[data-coche]:checked').length"), 2, "arbre : tout coché par défaut")
    cdp.js("document.querySelector('#assistant input[data-coche=\"a.txt\"]').click()")
    cdp.js("(() => { const i = document.getElementById('messageCommit'); i.value = 'fix: sonde é';"
           " i.dispatchEvent(new Event('input', {bubbles: true})); })()")
    verifie(cdp.js(clique("Commiter la sélection (1)", ASSISTANT)), True, "arbre : bouton « Commiter la sélection (1) »")
    verifie(bool(attend(cdp, "document.getElementById('assistantMessage').textContent.startsWith('Commité')", 15)), True,
            "arbre : commit annoncé dans la page")
    journal = subprocess.run(["git", "-c", "core.quotePath=false", "log", "-1", "--format=%s", "--name-only"], cwd=m.travail, capture_output=True,
                             text=True, encoding="utf-8").stdout.split()
    verifie(journal, ["fix:", "sonde", "e", "dossier", "é/fichier", "x.txt"], "arbre : seul le fichier coché est commité")
    verifie(cdp.js("[...document.querySelectorAll('#assistant input[data-coche]')].map(c => c.dataset.coche)"), ["a.txt"],
            "arbre : reste a.txt, toujours bloquée")
    subprocess.run(["git", "checkout", "--", "a.txt"], cwd=m.travail, check=True, capture_output=True)
    verifie(cdp.js(clique("Revérifier", ASSISTANT)) or cdp.js(clique("Réanalyser", ASSISTANT)), True, "arbre rendu propre : nouvelle analyse")
    # 1. Diagnostic -> assistant, fusion_b courante
    verifie(bool(attend(cdp, etape("fusion_b", "courante"), 25)), True, "diagnostic : #assistant avec fusion_b courante")
    verifie(cdp.js("!document.querySelector('[data-fusion-en-cours]')"), True, "avant le merge : pas d'avertissement de merge en cours")
    verifie(cdp.js(visible("#assistant")), True, "#assistant visible")
    verifie(cdp.js(etape("prevision", "faite")) and cdp.js(etape("pousser", "attente")), True, "prévision faite, pousser en attente")
    verifie(cdp.js("(() => { const a = [...document.querySelectorAll('#assistant .act')];"
                   " return a.length > 0 && a.every(x => x.querySelector('code').textContent.trim() !== ''); })()"),
            True, "chaque bouton d'action affiche sa commande git")
    # 2. Lancer le merge -> un conflit
    verifie(cdp.js(clique("Lancer le merge", ASSISTANT)), True, "bouton « Lancer le merge »")
    verifie(bool(attend(cdp, LIGNES_CONFLITS + " === 3", 25)), True, "merge lancé : le tableau des conflits a 3 lignes")
    verifie(cdp.js("(document.querySelector('#assistant [data-fusion-en-cours]')?.textContent || '').includes('aucune autre session ni outil ne doit commiter, abandonner ou relancer de merge')"),
            True, "merge en cours : avertissement « aucune autre session ni outil... »")
    verifie(cdp.js("[...document.querySelectorAll('#assistant table.conflits tbody tr')].map(r => r.cells[0].textContent.trim())"),
            [HOSTILE, "a.txt", "commun.txt"], "lignes : fichier hostile, a.txt, commun.txt")
    # echappement : rien du titre ni du nom n'est interprete comme du HTML
    verifie(cdp.js("window.__xss === undefined"), True, "XSS : le titre de commit hostile n'exécute rien (window.__xss indéfini)")
    verifie(cdp.js("document.querySelector('#assistant li[data-etape=\"nouveautes\"]').textContent.includes(" + json.dumps(TITRE_HOSTILE) + ")"),
            True, "XSS : le titre hostile apparaît littéralement dans le texte")
    verifie(cdp.js("!document.querySelector('#assistant img, #assistant table.conflits b')"), True,
            "XSS : aucune balise <img> ni <b> créée par le titre ou le nom de fichier")
    verifie(cdp.js("document.querySelector('#assistant table.conflits tbody tr').querySelector('code').textContent.includes("
                   + json.dumps('"' + HOSTILE + '"') + ")"),
            True, "commande affichée : chemin avec espace entre guillemets")
    ligne_ud = "[...document.querySelectorAll('#assistant table.conflits tbody tr')].find(r => r.cells[0].textContent.trim() === 'commun.txt')"
    verifie(cdp.js(ligne_ud + ".textContent.includes('Garder mon fichier') && " + ligne_ud + ".textContent.includes(\"Le supprimer comme l'amont\")"),
            True, "UD (supprimé par l'amont) : « Garder mon fichier » / « Le supprimer comme l'amont »")
    verifie(cdp.js("!!document.querySelector('#assistant [data-demande=\"abandonne\"]')"), True, "« Abandonner le merge » visible")
    cdp.js("document.querySelector('#assistant [data-voies=\"a.txt\"]').click()")
    verifie(bool(attend(cdp, "document.querySelectorAll('#assistantVoies pre').length === 2 && "
                             "document.querySelector('#assistantVoies pre').textContent.includes('local')", 15)),
            True, "vue des deux diffs (base→mien, base→amont) au clic sur le fichier")
    # 3. Prendre l'amont -> la ligne disparait
    for restantes in (2, 1):
        verifie(cdp.js(clique("Prendre l'amont", ASSISTANT)), True, "bouton « Prendre l'amont »")
        verifie(bool(attend(cdp, LIGNES_CONFLITS + f" === {restantes}", 25)), True, f"amont pris : {restantes} ligne(s) de conflit")
    verifie(cdp.js(clique("Le supprimer comme l'amont", ASSISTANT)), True, "bouton « Le supprimer comme l'amont » (UD)")
    verifie(bool(attend(cdp, LIGNES_CONFLITS + " === 0 && " + etape("fusion_b", "courante"), 25)), True,
            "amont pris : plus de ligne de conflit, merge toujours en cours")
    # 4. serveur arrete en plein merge, page rouverte : l'assistant se montre sans diagnostic
    verifie(erreurs(cdp), [], "aucune erreur JS avant le redémarrage")
    m.redemarre_serveur()
    with cdp.condition:
        cdp.evenements.clear()                  # le flux SSE coupe par le redemarrage fait du bruit, c'est attendu
    m.ouvre()
    verifie(bool(attend(cdp, visible("#assistant") + " && " + etape("fusion_b", "courante"), 25)), True,
            "page rechargée en plein merge : assistant visible sans diagnostic")
    # 5. Terminer -> liste recalculee
    verifie(cdp.js(clique("Terminer", ASSISTANT)), True, "bouton « Terminer le merge »")
    verifie(bool(attend(cdp, etape("pousser", "courante") + " && !document.querySelector('#assistant li[data-etape=\"fusion_b\"]')", 25)),
            True, "merge terminé : liste recalculée, pousser courante")
    verifie(cdp.js(clique("Pousser", ASSISTANT)), True, "« Pousser » demande une confirmation")
    verifie(cdp.js("[...document.querySelectorAll('#assistant button')].some(b => b.textContent.includes('Confirmer'))"), True,
            "second bouton « Confirmer » (pas de dialogue)")
    verifie(erreurs(cdp), [], "aucune exception JS après rechargement")


def sonde_temoin(m, temoin):
    """Meme scenario sur une page volontairement cassee : il DOIT echouer (script : exception relevee ;
    echappe : la verification XSS en particulier)."""
    global ECHECS
    vrais, ECHECS = ECHECS, []
    try:
        sonde_page(m)
        echecs_temoin, exceptions = list(ECHECS), erreurs(m.cdp)
    finally:
        ECHECS = vrais
    print(f"     temoin {temoin} : {len(echecs_temoin)} verification(s) rouge(s), exceptions : {exceptions}", flush=True)
    if temoin == "script":
        detecte = bool(echecs_temoin) and any("setting 'onclick'" in e for e in exceptions)
    else:
        detecte = any(e.startswith("XSS") for e in echecs_temoin)
    verifie(detecte, True, f"TEMOIN ({TEMOINS[temoin]}) : la page est ROUGE")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page de la synchro du fork.")
    options.add_argument("--sans-temoin", action="store_true", help="ne pas rejouer la page avec une erreur volontaire")
    options.add_argument("--serveur", nargs=3, metavar=("PORT", "TRAVAIL", "FAUX"), help=argparse.SUPPRESS)
    options.add_argument("--temoin", default="", help=argparse.SUPPRESS)
    args = options.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.serveur[2], args.temoin)
    for temoin in ([""] if args.sans_temoin else ["", *TEMOINS]):
        print(f"\n=== {'TEMOIN ' + TEMOINS[temoin] if temoin else 'page reelle'} ===", flush=True)
        m = None
        try:
            m = Montage()
            m.demarre(temoin)
            sonde_temoin(m, temoin) if temoin else sonde_page(m)
        except Exception as erreur:
            verifie(f"{type(erreur).__name__}: {erreur}", "", "la sonde va au bout")
        finally:
            if m:
                m.ferme()
    print("\nVERT" if not ECHECS else f"\nROUGE : {len(ECHECS)} echec(s) : {ECHECS}")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
