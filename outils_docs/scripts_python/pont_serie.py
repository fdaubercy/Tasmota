"""Pont generique port serie -> 127.0.0.1 (TCP brut + page HTTP), pour n'importe quelle carte.

Principe : ce script ouvre un port serie et sert son flux sur 127.0.0.1:<tcp>, a la fois :
  - en TCP brut : extension VS Code « Serial Monitor » (mode TCP), PuTTY (Raw), ncat... ;
  - en HTTP, SUR LE MEME PORT : http://127.0.0.1:<tcp> dans un navigateur (pont_serie_web.py :
    logs en direct, filtre, envoi de commandes). Une requete HTTP est reconnue a ses premiers octets.
Ce que tapent les clients repart vers la carte. Plusieurs clients peuvent etre connectes a la fois.

Couleurs : les lignes sont colorees avec les regles Tasmota de monitor/filter_couleurs_tasmota.py
(niveau de log, module Berry emetteur). Sur un autre flux, --sans-couleurs ; si le fichier de
regles est absent, le pont passe seul en mode sans couleurs.

Usage (Python de PlatformIO, qui fournit pyserial) :
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/pont_serie.py
    options : --port auto|COM11|loop://  --vitesse 115200  --tcp 7000  --journal fichier.log
              --sans-couleurs  --lister (affiche les ports serie et sort)
    --port auto (defaut) : prend le SEUL port USB present ; s'il y en a plusieurs, les liste et sort.
    Deux cartes en meme temps : deux ponts, avec deux --tcp differents (7000, 7001...).

Depuis VS Code : pioarduino > Project Tasks > <env> > Custom > « Pont serie (TCP/HTTP 127.0.0.1) »
(cible_pont_serie.py : port et debit lus dans monitor_port / monitor_speed de l'env).
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).

Le port serie n'accepte qu'un programme : ARRETER CE PONT AVANT UN FLASH.
Le port est ouvert sans basculer DTR/RTS : pas de reset de l'ESP32 a l'ouverture.
"""

import argparse
import collections
import importlib.util
import os
import socket
import sys
import threading
import time

import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pont_serie_web  # noqa: E402  (module voisin : page et routes HTTP)

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEBUTS_HTTP = (b"GET ", b"POST", b"HEAD")


class SansCouleurs:
    """Remplace le coloriseur Tasmota : texte transmis tel quel."""
    def morceau(self, texte):
        return texte


def charge_coloriseur(sans_couleurs):
    chemin = os.path.join(RACINE, "monitor", "filter_couleurs_tasmota.py")
    if sans_couleurs:
        return SansCouleurs()
    if not os.path.exists(chemin):
        print(f"(regles de couleurs absentes : {chemin} -> flux sans couleurs)")
        return SansCouleurs()
    spec = importlib.util.spec_from_file_location("filter_couleurs_tasmota", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Coloriseur()


def ports_usb():
    from serial.tools import list_ports
    return [p for p in sorted(list_ports.comports(), key=lambda p: p.device) if p.vid is not None]


def choisit_port(demande):
    """'auto' -> le seul port USB present ; sinon le port demande tel quel."""
    if demande.lower() != "auto":
        return demande
    ports = ports_usb()
    if len(ports) == 1:
        print(f"port auto : {ports[0].device} ({ports[0].description})")
        return ports[0].device
    if not ports:
        sys.exit("Aucun port serie USB detecte : carte branchee ? (sinon --port COMx)")
    liste = "\n".join(f"  {p.device:8} {p.description}" for p in ports)
    sys.exit(f"Plusieurs ports USB : preciser --port.\n{liste}")


def ouvre_port(url, vitesse):
    port = serial.serial_for_url(url, do_not_open=True, baudrate=vitesse, timeout=0.2)
    port.dtr, port.rts = False, False   # ne pas resetter l'ESP32
    port.open()
    return port


class Pont:
    def __init__(self, port, coloriseur, journal, port_tcp):
        self.port = port
        self.coloriseur = coloriseur
        self.journal = journal
        self.port_tcp = port_tcp
        self.clients = []                                   # clients TCP bruts (Serial Monitor...)
        self.clients_web = []                               # navigateurs (flux SSE)
        self.historique = collections.deque(maxlen=500)     # derniers morceaux colores, pour un nouveau navigateur
        self.verrou = threading.Lock()

    @staticmethod
    def _envoie(liste, octets):
        for client in list(liste):
            try:
                client.sendall(octets)
            except OSError:
                liste.remove(client)

    def diffuse(self, colore):
        # xterm.js veut CR+LF pour revenir en debut de ligne ; le navigateur recoit le texte tel quel
        brut = colore.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        with self.verrou:
            self.historique.append(colore)
            self._envoie(self.clients, brut)
            if self.clients_web:
                self._envoie(self.clients_web, pont_serie_web.evenement_sse(colore))

    def inscrit_web(self, client):
        with self.verrou:
            if self.historique:
                client.sendall(pont_serie_web.evenement_sse("".join(self.historique)))
            self.clients_web.append(client)

    def desinscrit_web(self, client):
        with self.verrou:
            if client in self.clients_web:
                self.clients_web.remove(client)

    def lit_serie(self):
        while True:
            brut = self.port.read(4096)
            if not brut:
                continue
            texte = brut.decode("utf-8", "replace")
            if self.journal:
                self.journal.write(texte)
                self.journal.flush()
            colore = self.coloriseur.morceau(texte)
            if colore:
                self.diffuse(colore)

    @staticmethod
    def _est_http(client):
        """Un navigateur parle en premier ("GET ..."), un client TCP brut attend : 0,3 s pour trancher."""
        client.settimeout(0.3)
        try:
            debut = client.recv(4, socket.MSG_PEEK)     # PEEK : les octets restent a lire
        except (socket.timeout, OSError):
            debut = b""
        client.settimeout(None)
        return debut in DEBUTS_HTTP

    def sert_client(self, client, adresse):
        if self._est_http(client):
            try:
                pont_serie_web.traite(self, client, self.port_tcp)
            except OSError:
                pass
            client.close()
            return
        print(f"client connecte : {adresse[0]}:{adresse[1]}")
        with self.verrou:
            self.clients.append(client)
        try:
            while True:
                donnees = client.recv(1024)
                if not donnees:
                    break
                self.port.write(donnees)   # commandes tapees -> carte
        except OSError:
            pass
        with self.verrou:
            if client in self.clients:
                self.clients.remove(client)
        client.close()
        print(f"client deconnecte : {adresse[0]}:{adresse[1]}")


def main():
    options = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    options.add_argument("--port", default="auto", help="port serie : auto (seul port USB), COM11, /dev/ttyUSB0, loop://...")
    options.add_argument("--vitesse", type=int, default=115200)
    options.add_argument("--tcp", type=int, default=7000, help="port TCP local (TCP brut ET HTTP)")
    options.add_argument("--journal", help="copie brute (sans couleurs) du flux dans ce fichier")
    options.add_argument("--sans-couleurs", action="store_true", help="flux transmis tel quel (carte non Tasmota)")
    options.add_argument("--lister", action="store_true", help="affiche les ports serie et sort")
    args = options.parse_args()

    if args.lister:
        from serial.tools import list_ports
        for p in sorted(list_ports.comports(), key=lambda p: p.device):
            print(f"{p.device:8} {'USB ' if p.vid is not None else '    '} {p.description}")
        return

    nom_port = choisit_port(args.port)
    coloriseur = charge_coloriseur(args.sans_couleurs)

    # Le port TCP d'abord : si un autre pont l'occupe, on sort SANS avoir pris le port serie.
    serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):   # Windows : SO_REUSEADDR laisserait 2 ponts sur le meme port
        serveur.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        serveur.bind(("127.0.0.1", args.tcp))   # local uniquement : jamais expose au reseau
    except OSError as erreur:
        sys.exit(f"Port TCP {args.tcp} deja utilise ({erreur}) : un autre pont tourne ? (sinon --tcp 7001)")
    serveur.listen()

    try:
        port = ouvre_port(nom_port, args.vitesse)
    except serial.SerialException as erreur:
        serveur.close()
        sys.exit(f"Impossible d'ouvrir {nom_port} : {erreur}\n(un moniteur serie ou un flash l'utilise deja ?)")
    journal = open(args.journal, "a", encoding="utf-8") if args.journal else None
    pont = Pont(port, coloriseur, journal, args.tcp)
    threading.Thread(target=pont.lit_serie, daemon=True).start()

    print(f"Pont {nom_port} ({args.vitesse} bauds) -> 127.0.0.1:{args.tcp}  (Ctrl+C pour arreter)")
    print(f"  navigateur : http://127.0.0.1:{args.tcp}   |   Serial Monitor : mode TCP, 127.0.0.1, port {args.tcp}")
    serveur.settimeout(0.5)   # Windows : un accept() bloquant ne laisse jamais passer Ctrl+C
    try:
        while True:
            try:
                client, adresse = serveur.accept()
            except socket.timeout:
                continue
            client.settimeout(None)
            threading.Thread(target=pont.sert_client, args=(client, adresse), daemon=True).start()
    except KeyboardInterrupt:
        print("\narret du pont, port serie libere")
    finally:
        serveur.close()
        port.close()
        time.sleep(0.1)


if __name__ == "__main__":
    main()
