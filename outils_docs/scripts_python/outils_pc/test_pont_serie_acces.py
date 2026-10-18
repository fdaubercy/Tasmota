"""Banc de l'acces reseau du pont serie (pont_serie.py + acces_web.py), et de la relance du log serie
Tasmota (case de la page, option --relance-log). Code de sortie 0 = vert.

Le VRAI pont_serie.py est lance en loop:// (ce qui est ecrit revient), sur un port TCP libre,
--sans-navigateur. « Autre appareil » = connexion par l'IP reseau de ce PC : le pont ne voit plus
127.0.0.1. Sans adresse reseau (PC hors ligne), ces cas sont sautes et le banc le dit.
Temoins : copie du pont dans un dossier temporaire, d'abord verte intacte, puis mutee (refus du TCP
brut distant retire ; controle du jeton retire) : le cas correspondant DOIT alors echouer.
N'ouvre aucun port COM, ne touche pas aux ports 7000/7001.
"""

import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

import acces_web

ICI = os.path.dirname(os.path.abspath(__file__))
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def port_libre():
    with socket.socket() as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]


class PontLance:
    """pont_serie.py (du dossier donne) en loop://, sortie console capturee (pour y lire le jeton)."""
    def __init__(self, dossier=ICI, options=()):
        self.port = port_libre()
        self.lignes = []
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        env.pop("PONT_SERIE_JETON", None)
        self.proc = subprocess.Popen([sys.executable, "-u", os.path.join(dossier, "pont_serie.py"), "--port", "loop://",
                                      "--tcp", str(self.port), "--sans-couleurs", "--sans-navigateur", *options],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        threading.Thread(target=self._lit, daemon=True).start()
        self.jeton = None
        limite = time.time() + 15
        while time.time() < limite:
            if self.proc.poll() is not None:
                raise RuntimeError("pont arrete au demarrage :\n" + "".join(self.lignes))
            trouve = re.search(r"\?jeton=([\w-]+)", "".join(self.lignes))
            if trouve and "Serial Monitor" in "".join(self.lignes):
                self.jeton = trouve.group(1)
            if "Serial Monitor" in "".join(self.lignes) and requete("127.0.0.1", self.port, chemin="/etat")[0] == 200:
                return
            time.sleep(0.1)
        raise RuntimeError("pont muet :\n" + "".join(self.lignes))

    def _lit(self):
        for ligne in iter(self.proc.stdout.readline, b""):
            self.lignes.append(ligne.decode("utf-8", "replace"))

    def arrete(self):
        self.proc.terminate()
        self.proc.wait(5)


def requete(hote, port, methode="GET", chemin="/", entetes=None, corps=b""):
    try:
        c = http.client.HTTPConnection(hote, port, timeout=5)
        c.request(methode, chemin, body=corps if methode == "POST" else None, headers=entetes or {})
        r = c.getresponse()
        donnees = r.read() if chemin.split("?")[0] != "/flux" or r.status != 200 else b""
        c.close()
        return r.status, dict(r.getheaders()), donnees
    except OSError:
        return None, {}, b""


class Espion:
    """Client TCP brut LOCAL : recoit le flux de la carte (loop:// -> ce qui est ecrit revient)."""
    def __init__(self, port):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.recu = b""
        time.sleep(0.5)            # silence > 0,3 s : le pont le classe TCP brut
        threading.Thread(target=self._lit, daemon=True).start()

    def _lit(self):
        self.s.settimeout(None)
        try:
            while True:
                morceau = self.s.recv(4096)
                if not morceau:
                    break
                self.recu += morceau
        except OSError:
            pass

    def attend(self, motif, delai=3.0):
        limite = time.time() + delai
        while time.time() < limite:
            if motif in self.recu:
                return True
            time.sleep(0.05)
        return motif in self.recu

    def ferme(self):
        self.s.close()


def brut_local(port):
    """Ce PC, TCP brut : ce qu'on tape part sur le port serie (loop://) et revient. -> True."""
    espion = Espion(port)
    espion.s.sendall(b"PING-LOCAL-123\n")
    ok = espion.attend(b"PING-LOCAL-123")
    espion.ferme()
    return ok


def brut_distant(ip, port, espion=None):
    """Autre appareil, TCP brut : -> (connexion fermee par le pont, octets parvenus au port serie)."""
    marque = f"INTRUS-{port}".encode()
    s = socket.create_connection((ip, port), timeout=5)
    time.sleep(0.5)                # ne parle pas d'abord : c'est un client TCP brut, pas du HTTP
    try:
        s.sendall(marque + b"\n")
        s.settimeout(2)
        ferme = s.recv(4096) == b""
    except socket.timeout:
        ferme = False
    except OSError:                # ConnectionReset / Aborted : fermee
        ferme = True
    s.close()
    return ferme, bool(espion and espion.attend(marque, 1.5))


def cookie_de(entetes):
    return entetes.get("Set-Cookie", "").split(";")[0]


def cas_local(pont):
    p = pont.port
    statut, _, corps = requete("127.0.0.1", p)
    verifie((statut, b"Pont serie" in corps), (200, True), "ce PC : page sans jeton")
    verifie(brut_local(p), True, "ce PC : TCP brut -> port serie (loop://) -> retour")
    verifie(requete("127.0.0.1", p, "POST", "/cmd", corps=b"x")[0], 403, "ce PC : POST sans X-Pont refuse")
    verifie(requete("127.0.0.1", p, "POST", "/cmd", {"X-Pont": "1", "Origin": f"http://evil.example:{p}",
                                                     "Host": f"evil.example:{p}"}, b"x")[0], 403,
            "ce PC : POST d'origine etrangere refuse meme si Host concorde (DNS rebinding)")
    statut, _, corps = requete("127.0.0.1", p, "POST", "/terminal", {"X-Pont": "1"})
    url = json.loads(corps or b"{}").get("url", "") if statut == 200 else ""
    verifie(bool(re.fullmatch(r"http://127\.0\.0\.1:\d+/", url)), True, f"ce PC : /terminal -> URL locale sans jeton ({url})")


def cas_distant(pont, ip):
    p, jeton = pont.port, pont.jeton
    verifie(jeton is not None and len(jeton) >= 16, True, "jeton lu dans le lien « reseau » de la console")
    espion = Espion(p)
    verifie(brut_distant(ip, p, espion), (True, False), f"autre appareil ({ip}) : TCP brut ferme, rien vers le port serie")
    statut, _, corps = requete(ip, p)
    verifie((statut, b"Acces refuse" in corps), (403, True), "autre appareil : page sans jeton -> 403")
    verifie(requete(ip, p, chemin="/etat")[0], 403, "autre appareil : /etat sans jeton -> 403")
    verifie(requete(ip, p, chemin="/flux")[0], 403, "autre appareil : /flux sans jeton -> 403")
    verifie(requete(ip, p, "POST", "/cmd", {"X-Pont": "1"}, b"SANS-JETON-1")[0], 403, "autre appareil : POST sans jeton -> 403")
    verifie(requete(ip, p, chemin="/?jeton=faux")[0], 403, "autre appareil : mauvais jeton -> 403")
    statut, entetes, _ = requete(ip, p, chemin=f"/?jeton={jeton}")
    verifie((statut, entetes.get("Location")), (303, "/"), "autre appareil : ?jeton= valide -> 303 vers /")
    cookie = cookie_de(entetes)
    verifie((cookie == f"jeton_{p}={jeton}", "HttpOnly" in entetes.get("Set-Cookie", "")), (True, True),
            "... jeton pose en cookie HttpOnly")
    avec = {"Cookie": cookie}
    statut, _, corps = requete(ip, p, entetes=avec)
    verifie((statut, b"Pont serie" in corps), (200, True), "autre appareil : page avec le cookie -> 200")
    statut, _, corps = requete(ip, p, chemin="/etat", entetes=avec)
    verifie((statut, json.loads(corps or b"{}").get("port")), (200, "loop://"), "autre appareil : /etat avec le cookie")
    origine = {"Origin": f"http://{ip}:{p}", "X-Pont": "1"}
    verifie(requete(ip, p, "POST", "/cmd", dict(avec, **origine), b"REMOTE-CMD-789")[0], 204,
            "autre appareil : POST /cmd avec cookie, X-Pont et origine = hote vise -> 204")
    verifie(espion.attend(b"REMOTE-CMD-789"), True, "... la commande est bien partie sur le port serie")
    verifie(requete(ip, p, "POST", "/cmd", dict(avec, Origin=f"http://{ip}:{p}"), b"x")[0], 403,
            "autre appareil : POST sans X-Pont refuse (meme avec cookie)")
    verifie(requete(ip, p, "POST", "/cmd", dict(avec, **{"X-Pont": "1", "Origin": "http://evil.example"}), b"x")[0], 403,
            "autre appareil : POST d'origine etrangere refuse")
    verifie(espion.attend(b"SANS-JETON-1", 0.5), False, "... rien d'un POST refuse n'est parti sur le port serie")
    espion.ferme()

    # Terminal supplementaire demande depuis le reseau : hote vise + meme jeton, memes regles
    statut, _, corps = requete(ip, p, "POST", "/terminal", dict(avec, **origine))
    url = json.loads(corps or b"{}").get("url", "") if statut == 200 else ""
    trouve = re.fullmatch(rf"http://{re.escape(ip)}:(\d+)/\?jeton={re.escape(jeton)}", url)
    verifie(bool(trouve), True, f"autre appareil : /terminal -> URL avec l'hote vise et le jeton ({url})")
    if not trouve:
        return
    p2 = int(trouve.group(1))
    verifie(requete(ip, p2)[0], 403, "terminal supplementaire : sans jeton -> 403")
    statut, entetes, _ = requete(ip, p2, chemin=f"/?jeton={jeton}")
    verifie((statut, cookie_de(entetes)), (303, f"jeton_{p2}={jeton}"), "terminal supplementaire : meme jeton -> 303 + cookie")
    verifie(requete(ip, p2, entetes={"Cookie": cookie_de(entetes)})[0], 200, "terminal supplementaire : avec cookie -> 200")
    verifie(brut_distant(ip, p2)[0], True, "terminal supplementaire : TCP brut distant ferme")
    verifie(requete("127.0.0.1", p2)[0], 200, "terminal supplementaire : ce PC sans jeton -> 200")


ANNONCE = "00:10:00.001 APP: Journalisation série désactivée\r\n".encode("utf-8")
REVEIL = b'tasmota.cmd("SerialLog", true)'


def poste_json(p, chemin, objet, entetes=None):
    return requete("127.0.0.1", p, "POST", chemin, {"X-Pont": "1"} if entetes is None else entetes,
                   json.dumps(objet).encode())[0]


def attend_relances(espion, n, delai=3.0):
    """Nombre de SerialLog parvenus (loop:// : ce que le pont ecrit revient) une fois n atteint ou le delai passe."""
    limite = time.time() + delai
    while time.time() < limite and espion.recu.count(REVEIL) < n:
        time.sleep(0.05)
    return espion.recu.count(REVEIL)


def mesure_relance(pont):
    """Case cochee puis annonce de coupure : -> nombre de SerialLog envoyes (2 attendus, 1 sans detection)."""
    espion = Espion(pont.port)
    poste_json(pont.port, "/relance", {"actif": True})
    attend_relances(espion, 1)
    espion.s.sendall(ANNONCE)
    n = attend_relances(espion, 2, 1.5)
    espion.ferme()
    return n


def cas_relance(pont):
    """Relance du log serie Tasmota : en loop://, l'annonce ecrite revient comme si la carte l'avait emise."""
    p = pont.port
    etat = lambda: json.loads(requete("127.0.0.1", p, chemin="/etat")[2] or b"{}").get("relance")  # noqa: E731
    espion = Espion(p)
    verifie(etat(), False, "relance : case decochee par defaut")
    espion.s.sendall(ANNONCE)
    verifie(attend_relances(espion, 1, 1.0), 0, "relance decochee : annonce lue, rien envoye a la carte")
    verifie(poste_json(p, "/relance", {"actif": "oui"}), 400, "relance : actif non booleen -> 400")
    verifie(poste_json(p, "/relance", {"actif": True}, {}), 403, "relance : POST sans X-Pont refuse")
    verifie(poste_json(p, "/relance", {"actif": True}), 200, "relance : case cochee -> 200")
    verifie((attend_relances(espion, 1), etat()), (1, True), "... port ouvert : SerialLog envoye aussitot, etat relance=true")
    coupe = ANNONCE.index(b"\xc3") + 1           # annonce coupee au milieu du « é » : deux lectures du port
    espion.s.sendall(ANNONCE[:coupe])
    time.sleep(0.6)
    espion.s.sendall(ANNONCE[coupe:])
    verifie(attend_relances(espion, 2), 2, "annonce (francais) a cheval sur deux lectures -> SerialLog renvoye")
    time.sleep(0.5)
    verifie(espion.recu.count(REVEIL), 2, "... une seule relance par annonce")
    espion.s.sendall(b"APP: Serial logging disabled\r\n")
    verifie(attend_relances(espion, 3), 3, "annonce (anglais) -> SerialLog renvoye")
    verifie(poste_json(p, "/ouvrir", {"port": "loop://", "vitesse": 115200}), 200, "port rouvert (case cochee)")
    verifie(attend_relances(espion, 4), 4, "... SerialLog envoye a l'ouverture du port")
    verifie(poste_json(p, "/relance", {"actif": False}), 200, "relance : case decochee -> 200")
    espion.s.sendall(ANNONCE)
    verifie(attend_relances(espion, 5, 1.0), 4, "case decochee : annonce lue, rien envoye")
    espion.ferme()


def cas_relance_lancement():
    """--relance-log : relance active des le lancement (port ouvert), imposee a la page, non heritee par « + Terminal »."""
    pont = PontLance(options=["--relance-log"])
    try:
        p = pont.port
        etat = json.loads(requete("127.0.0.1", p, chemin="/etat")[2] or b"{}")
        verifie((etat.get("relance"), etat.get("relanceImposee")), (True, True), "--relance-log : etat relance et relanceImposee")
        console = "".join(pont.lignes)
        verifie("log serie Tasmota relance (SerialLog, port ouvert)" in console, True,
                "--relance-log : SerialLog envoye a l'ouverture du port au lancement")
        espion = Espion(p)
        espion.s.sendall(ANNONCE)
        verifie(attend_relances(espion, 1), 1, "--relance-log : annonce de coupure -> SerialLog renvoye")
        espion.ferme()
        statut, _, corps = requete("127.0.0.1", p, "POST", "/terminal", {"X-Pont": "1"})
        url = json.loads(corps or b"{}").get("url", "") if statut == 200 else ""
        trouve = re.fullmatch(r"http://127\.0\.0\.1:(\d+)/", url)
        etat2 = json.loads(requete("127.0.0.1", int(trouve.group(1)), chemin="/etat")[2] or b"{}") if trouve else {}
        verifie((etat2.get("relance"), etat2.get("relanceImposee")), (False, False),
                "+ Terminal : le terminal supplementaire n'herite pas de --relance-log")
    finally:
        pont.arrete()
    pont = PontLance()
    try:
        etat = json.loads(requete("127.0.0.1", pont.port, chemin="/etat")[2] or b"{}")
        verifie((etat.get("relance"), etat.get("relanceImposee")), (False, False), "sans --relance-log : relance coupee, non imposee")
    finally:
        pont.arrete()


def temoin_relance():
    """Copie du pont : intacte -> 2 SerialLog ; detection de l'annonce retiree -> 1 seul (celui du cochage)."""
    dossier = tempfile.mkdtemp(prefix="banc_pont_relance_")
    try:
        for nom in ("pont_serie.py", "pont_serie_web.py", "acces_web.py"):
            shutil.copy(os.path.join(ICI, nom), dossier)
        for etape, attendu in (("reference : copie intacte", 2), ("detection de l'annonce retiree", 1)):
            if attendu == 1:
                chemin = os.path.join(dossier, "pont_serie.py")
                with open(chemin, encoding="utf-8") as f:
                    texte = f.read()
                motif = "        if any(annonce in fenetre for annonce in ANNONCES_COUPURE):\n"
                verifie(texte.count(motif), 1, "TEMOIN : motif de mutation present une fois dans pont_serie.py")
                with open(chemin, "w", encoding="utf-8") as f:
                    f.write(texte.replace(motif, "        if False:\n"))
            pont = PontLance(dossier)
            try:
                verifie(mesure_relance(pont), attendu, f"TEMOIN relance {etape} -> {attendu} SerialLog")
            finally:
                pont.arrete()
    finally:
        shutil.rmtree(dossier, ignore_errors=True)


def temoins(ip):
    """Copie du pont : intacte -> refus ; mutee -> le cas de refus correspondant echoue."""
    dossier = tempfile.mkdtemp(prefix="banc_pont_acces_")
    try:
        for nom in ("pont_serie.py", "pont_serie_web.py", "acces_web.py"):
            shutil.copy(os.path.join(ICI, nom), dossier)

        def mesure():
            pont = PontLance(dossier)
            try:
                espion = Espion(pont.port)
                brut = brut_distant(ip, pont.port, espion)
                espion.ferme()
                return brut, requete(ip, pont.port)[0]
            finally:
                pont.arrete()

        verifie(mesure(), ((True, False), 403), "TEMOIN reference : copie intacte -> TCP brut ferme, page 403")

        def mute(nom, avant, apres):
            chemin = os.path.join(dossier, nom)
            with open(chemin, encoding="utf-8") as f:
                texte = f.read()
            verifie(texte.count(avant), 1, f"TEMOIN : motif de mutation present une fois dans {nom}")
            with open(chemin, "w", encoding="utf-8") as f:
                f.write(texte.replace(avant, apres))

        mute("pont_serie.py", "        if not acces_web.est_local(adresse):\n", "        if False:\n")
        brut, page = mesure()
        verifie(brut, (False, True), "TEMOIN refus du TCP brut distant retire : connexion gardee, octets sur le port serie")
        mute("pont_serie_web.py", "    if not pont.acces.controle(echange):", "    if False:")
        verifie(mesure()[1], 200, "TEMOIN controle du jeton retire : page distante sans jeton servie (200)")
    finally:
        shutil.rmtree(dossier, ignore_errors=True)


def principal():
    verifie(acces_web.Acces(7000, True).hote, "127.0.0.1", "--local : ecoute sur 127.0.0.1 seulement")
    pont = PontLance()
    try:
        cas_local(pont)
        cas_relance(pont)
        ips = acces_web.ips_reseau()
        if not ips:
            print("SAUTE  autre appareil et temoins : aucune adresse reseau sur ce PC")
        else:
            cas_distant(pont, ips[0])
    finally:
        pont.arrete()
    cas_relance_lancement()
    temoin_relance()
    if ips:
        temoins(ips[0])
    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
