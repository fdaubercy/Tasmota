"""Banc de l'acces web du serveur syslog (syslog_tasmota.py + acces_web.py). Code de sortie 0 = vert.

Lance le VRAI syslog_tasmota.py (main compris) en sous-processus, sur des ports libres :
HTTP tire au hasard (jamais 7200), UDP tire au hasard et ecoute sur 127.0.0.1 seulement (jamais 514 :
le vrai serveur syslog de l'utilisateur peut tourner), journal dans un dossier temporaire.
« Autre appareil » = appel par l'IP reseau de ce PC (acces_web.ips_reseau()[0]) : le client n'est
plus 127.0.0.1. Sans adresse reseau, ces cas sont sautes et le banc le dit.

Cas : depuis le reseau, page / etat / flux SSE sans jeton -> 403 ; mauvais jeton -> 403 ; bon jeton ->
303 + cookie ; avec le cookie -> 200, et le flux SSE livre un message syslog envoye a l'ecoute de test.
Depuis ce PC : inchange (200 sans jeton). Aucune route POST (501). --local : rien sur le reseau.
TEMOIN : une copie de syslog_tasmota.py SANS l'appel acces.controle DOIT faire echouer les refus.
"""

import http.client
import os
import queue
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import acces_web        # noqa: E402

SCRIPT = os.path.join(ICI, "syslog_tasmota.py")
LIGNE_CONTROLE = "            if not acces.controle(self):"
RE_LIEN = re.compile(r"http://([\d.]+):(\d+)/\?jeton=(\S+)")


def port_libre(type_socket):
    with socket.socket(socket.AF_INET, type_socket) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def requete(hote, port, chemin="/", entetes=None, methode="GET"):
    c = http.client.HTTPConnection(hote, port, timeout=5)
    c.request(methode, chemin, body=b"" if methode == "POST" else None, headers=entetes or {})
    r = c.getresponse()
    corps = r.read()
    c.close()
    return r.status, dict(r.getheaders()), corps


def lit_flux(hote, port, entetes, attendu, delai=6.0):
    """Ouvre /flux (SSE) et lit jusqu'a voir 'attendu'. Rend (statut, vu)."""
    c = http.client.HTTPConnection(hote, port, timeout=delai)
    c.request("GET", "/flux", headers=entetes or {})
    r = c.getresponse()
    if r.status != 200:
        r.read()
        c.close()
        return r.status, False
    vu, tampon, fin = False, b"", time.time() + delai
    try:
        while time.time() < fin and not vu:
            morceau = r.fp.read1(4096) if hasattr(r.fp, "read1") else r.read(1)
            if not morceau:
                break
            tampon += morceau
            vu = attendu.encode("utf-8") in tampon
    except OSError:
        pass
    c.close()
    return 200, vu


class Outil:
    """Un syslog_tasmota.py lance en sous-processus ; sa console est lue dans une file."""

    def __init__(self, script, local=False):
        self.http, self.udp = port_libre(socket.SOCK_STREAM), port_libre(socket.SOCK_DGRAM)
        self.dossier = tempfile.mkdtemp(prefix="banc_syslog_")
        self.journal = os.path.join(self.dossier, "journal.log")
        commande = [sys.executable, "-u", script, "--port", str(self.udp), "--ecoute", "127.0.0.1",
                    "--http", str(self.http), "--journal", self.journal, "--sans-navigateur"]
        if local:
            commande.append("--local")
        env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=ICI)
        self.proc = subprocess.Popen(commande, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                     text=True, encoding="utf-8", errors="replace")
        self.lignes, self.file = [], queue.Queue()
        threading.Thread(target=self._lit, daemon=True).start()

    def _lit(self):
        for ligne in self.proc.stdout:
            self.file.put(ligne.rstrip("\n"))

    def attend_annonce(self, delai=10.0):
        """Lignes de console jusqu'a l'annonce complete (lien reseau, ou mention --local / sans reseau)."""
        fin = time.time() + delai
        while time.time() < fin:
            try:
                ligne = self.file.get(timeout=0.2)
            except queue.Empty:
                if self.proc.poll() is not None:
                    break
                continue
            self.lignes.append(ligne)
            if RE_LIEN.search(ligne) or "--local" in ligne or "aucune adresse reseau" in ligne:
                time.sleep(0.3)                     # les autres lignes de l'annonce suivent aussitot
                while not self.file.empty():
                    self.lignes.append(self.file.get())
                return True
        return False

    def envoie_syslog(self, texte):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(f"<134>1 2026-10-17T10:00:00.000000+02:00 BANC-SYSLOG tasmota - - - {texte}".encode(),
                     ("127.0.0.1", self.udp))

    def arrete(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def cas_acces(outil, ip):
    """Tous les cas d'acces ; rend [(libelle, obtenu, attendu)]. Ne verifie rien lui-meme."""
    port, res = outil.http, []
    lien = next((m for m in map(RE_LIEN.search, outil.lignes) if m), None)
    res.append(("console : lien reseau avec jeton affiche", lien is not None, True))
    res.append(("console : ecoute UDP et journal annonces",
                any(f"ecoute UDP 127.0.0.1:{outil.udp}" in l and outil.journal in l for l in outil.lignes), True))
    jeton = lien.group(3) if lien else "?"
    if lien:
        res.append(("console : le lien vise l'IP reseau et le port HTTP", (lien.group(1), int(lien.group(2))),
                    (ip, port)))
    nom = f"jeton_{port}"
    # -- autre appareil : refus
    for chemin in ("/", "/etat", "/modules"):
        res.append((f"reseau : GET {chemin} sans jeton refuse", requete(ip, port, chemin)[0], 403))
    res.append(("reseau : flux SSE sans jeton refuse", lit_flux(ip, port, {}, "x", 3)[0], 403))
    res.append(("reseau : mauvais jeton refuse", requete(ip, port, "/?jeton=faux")[0], 403))
    res.append(("reseau : cookie faux refuse", requete(ip, port, "/", {"Cookie": f"{nom}=faux"})[0], 403))
    # -- autre appareil : jeton -> cookie -> acces
    statut, entetes, _ = requete(ip, port, f"/?jeton={jeton}")
    res.append(("reseau : bon jeton -> 303", statut, 303))
    res.append(("... vers / sans jeton", entetes.get("Location"), "/"))
    cookie = entetes.get("Set-Cookie", "")
    res.append(("... cookie HttpOnly SameSite=Strict pose",
                cookie.startswith(f"{nom}={jeton};") and "HttpOnly" in cookie and "SameSite=Strict" in cookie, True))
    avec = {"Cookie": f"{nom}={jeton}"}
    statut, _, corps = requete(ip, port, "/", avec)
    res.append(("reseau : page avec le cookie", (statut, b"Syslog Tasmota" in corps), (200, True)))
    statut, _, corps = requete(ip, port, "/etat", avec)
    res.append(("reseau : /etat avec le cookie", (statut, f'"127.0.0.1:{outil.udp}"'.encode() in corps), (200, True)))
    res.append(("reseau : POST -> 501 (le syslog n'a aucune route POST)",
                requete(ip, port, "/", dict(avec, Origin=f"http://{ip}:{port}"), "POST")[0], 501))
    # -- message syslog -> flux SSE (reseau, avec cookie) et /modules (ce PC), journal
    marque = f"BRY: banc acces {time.time():.0f}"
    resultat = {}
    lecteur = threading.Thread(target=lambda: resultat.update(r=lit_flux(ip, port, avec, marque)))
    lecteur.start()
    time.sleep(0.8)
    outil.envoie_syslog(marque)
    lecteur.join()
    res.append(("reseau : flux SSE avec cookie livre le message syslog recu", resultat.get("r"), (200, True)))
    statut, _, corps = requete("127.0.0.1", port, "/modules")
    res.append(("ce PC : /modules sans jeton liste le module de test", (statut, b"BANC-SYSLOG" in corps), (200, True)))
    try:
        journal = open(outil.journal, encoding="utf-8").read()
    except OSError:
        journal = ""
    res.append(("journal temporaire : message ecrit", marque in journal, True))
    # -- ce PC : inchange
    statut, _, corps = requete("127.0.0.1", port, "/")
    res.append(("ce PC : page sans jeton", (statut, b"Syslog Tasmota" in corps), (200, True)))
    res.append(("ce PC : flux SSE sans jeton", lit_flux("127.0.0.1", port, {}, "event: etat", 4), (200, True)))
    return res


def affiche(resultats, prefixe=""):
    echecs = 0
    for libelle, obtenu, attendu in resultats:
        ok = obtenu == attendu
        echecs += not ok
        print(prefixe + ("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    return echecs


def copie_mutee():
    """syslog_tasmota.py sans l'appel acces.controle (2 lignes) ; rend le chemin, ou None si introuvable."""
    source = open(SCRIPT, encoding="utf-8").read().split("\n")
    i = next((k for k, l in enumerate(source) if l.startswith(LIGNE_CONTROLE)), None)
    if i is None or source[i + 1].strip() != "return":
        return None
    del source[i:i + 2]
    chemin = os.path.join(tempfile.mkdtemp(prefix="banc_syslog_mute_"), "syslog_tasmota.py")
    open(chemin, "w", encoding="utf-8").write("\n".join(source))
    return chemin


def principal():
    ips = acces_web.ips_reseau()
    echecs = 0
    if not ips:
        print("SAUTE  autre appareil : aucune adresse reseau sur ce PC (seul --local est verifie)")
    else:
        ip = ips[0]
        print(f"-- vrai syslog_tasmota.py, client reseau = {ip}")
        outil = Outil(SCRIPT)
        try:
            pret = outil.attend_annonce()
            echecs += affiche([("demarrage et annonce en console", pret, True)])
            echecs += affiche(cas_acces(outil, ip) if pret else [])
        finally:
            outil.arrete()
        if not pret:
            print("\n".join("   | " + l for l in outil.lignes))

        print("-- TEMOIN : copie sans acces.controle (les refus DOIVENT tomber)")
        mute = copie_mutee()
        echecs += affiche([("mutation appliquee (ligne acces.controle retiree)", mute is not None, True)])
        if mute:
            outil = Outil(mute)
            try:
                pret = outil.attend_annonce()
                echecs_temoin = affiche(cas_acces(outil, ip), "   temoin ") if pret else 0
            finally:
                outil.arrete()
            echecs += affiche([("TEMOIN : la copie mutee fait echouer des cas", pret and echecs_temoin > 0, True)])

    print("-- --local")
    outil = Outil(SCRIPT, local=True)
    try:
        pret = outil.attend_annonce()
        res = [("--local : demarrage, aucun lien reseau", (pret, any(RE_LIEN.search(l) for l in outil.lignes)),
                (True, False)),
               ("--local : ce PC sert la page", requete("127.0.0.1", outil.http)[0] if pret else None, 200)]
        if ips:
            try:
                joint = requete(ips[0], outil.http)[0]
            except OSError:
                joint = "refuse"
            res.append(("--local : injoignable par l'IP reseau", joint, "refuse"))
        echecs += affiche(res)
    finally:
        outil.arrete()

    print()
    print("VERT" if not echecs else f"ROUGE : {echecs} echec(s)")
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(principal())
