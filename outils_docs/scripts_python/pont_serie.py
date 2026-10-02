"""Pont generique port serie -> 127.0.0.1 (TCP brut + page HTTP), pour n'importe quelle carte.

Principe : ce script ouvre un port serie et sert son flux sur 127.0.0.1:<tcp>, a la fois :
  - en TCP brut : extension VS Code « Serial Monitor » (mode TCP), PuTTY (Raw), ncat... ;
  - en HTTP, SUR LE MEME PORT : http://127.0.0.1:<tcp> dans un navigateur (pont_serie_web.py :
    logs en direct, filtre, choix du port et de la vitesse, bouton Demarrer/Arreter du port
    serie ; envoi en Texte (fin de ligne au choix), Hex ou Binaire (CRC ModBus en option) et
    reception affichee en Texte ou en Hex, sur le modele du moniteur serie de VS Code).
    Une requete HTTP est reconnue a ses premiers octets.
Ce que tapent les clients repart vers la carte. Plusieurs clients peuvent etre connectes a la fois.

Le serveur reste en marche quand le port serie est ferme : « Arreter » sur la page LIBERE le
port (pour un flash) sans couper la page ; « Demarrer » le rouvre, eventuellement sur un autre
port ou a une autre vitesse. Si le port ne peut pas etre ouvert au lancement, le pont demarre
port ferme, a ouvrir depuis la page.

Couleurs : les lignes sont colorees avec les regles Tasmota de monitor/filter_couleurs_tasmota.py
(niveau de log, module Berry emetteur). Sur un autre flux, --sans-couleurs ; si le fichier de
regles est absent, le pont passe seul en mode sans couleurs.

Usage (Python de PlatformIO, qui fournit pyserial) :
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/pont_serie.py
    options : --port auto|COM11|loop://|aucun  --vitesse 115200  --tcp 7000  --journal fichier.log
              --sans-couleurs  --lister (affiche les ports serie et sort)
    --port auto (defaut) : prend le SEUL port USB present ; sinon demarre port ferme.
    Deux cartes en meme temps : deux ponts, avec deux --tcp differents (7000, 7001...).

Depuis VS Code : pioarduino > Project Tasks > <env> > Custom > « Pont serie (TCP/HTTP 127.0.0.1) »
(cible_pont_serie.py : port et debit lus dans monitor_port / monitor_speed de l'env).
Arret du pont : Ctrl+C dans le terminal de la tache (ou la corbeille).

Le port serie n'accepte qu'un programme : FERMER LE PORT (bouton Arreter) AVANT UN FLASH.
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
VITESSES = [9600, 19200, 38400, 57600, 74880, 115200, 230400, 250000, 460800, 500000,
            921600, 1000000, 1500000, 2000000]   # 74880 : messages du ROM de demarrage ESP8266/ESP32


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


def liste_ports():
    """Ports serie presents : [{'port', 'description', 'usb'}], USB d'abord."""
    from serial.tools import list_ports
    ports = sorted(list_ports.comports(), key=lambda p: (p.vid is None, p.device))
    return [{"port": p.device, "description": p.description, "usb": p.vid is not None} for p in ports]


def choisit_port(demande):
    """'auto' -> le seul port USB present, sinon None (pont demarre port FERME, a choisir sur la page)."""
    if demande.lower() != "auto":
        return demande
    usb = [p for p in liste_ports() if p["usb"]]
    if len(usb) == 1:
        print(f"port auto : {usb[0]['port']} ({usb[0]['description']})")
        return usb[0]["port"]
    detail = "aucun port USB detecte" if not usb else "plusieurs ports USB (" + ", ".join(p["port"] for p in usb) + ")"
    print(f"port auto : {detail} -> port serie FERME, a choisir sur la page web")
    return None


class Pont:
    def __init__(self, coloriseur, journal, port_tcp, vitesse):
        self.serie = None                                   # objet pyserial ; None = port ferme
        self.nom_port = None
        self.vitesse = vitesse
        self.verrou_serie = threading.Lock()                # ouverture / fermeture / ecriture
        self.coloriseur = coloriseur
        self.journal = journal
        self.port_tcp = port_tcp
        self.clients = []                                   # clients TCP bruts (Serial Monitor...)
        self.clients_web = []                               # navigateurs (flux SSE)
        self.historique = collections.deque(maxlen=1500)    # derniers evenements SSE (texte, notes, octets),
                                                            # rejoues a un nouveau navigateur
        self.verrou = threading.Lock()

    # ------------------------------------------------------------------ port serie
    def ouvre(self, nom_port, vitesse):
        """Ouvre (ou rouvre) le port serie. Renvoie (ok, message)."""
        with self.verrou_serie:
            self._ferme_sans_verrou()
            try:
                serie = serial.serial_for_url(nom_port, do_not_open=True, baudrate=int(vitesse), timeout=0.2)
                serie.dtr, serie.rts = False, False   # ne pas resetter l'ESP32
                serie.open()
            except (serial.SerialException, ValueError, OSError) as erreur:
                ok, message = False, f"impossible d'ouvrir {nom_port} : {erreur} (moniteur ou flash en cours ?)"
            else:
                self.serie, self.nom_port, self.vitesse = serie, nom_port, int(vitesse)
                ok, message = True, f"port {nom_port} ouvert a {vitesse} bauds"
        print(message)
        self.annonce(message)
        return ok, message

    def _ferme_sans_verrou(self):
        if self.serie is not None:
            serie, self.serie = self.serie, None
            try:
                serie.close()
            except (serial.SerialException, OSError):
                pass

    def ferme(self):
        with self.verrou_serie:
            ouvert = self.serie is not None
            self._ferme_sans_verrou()
        message = f"port {self.nom_port} ferme : libre pour un flash" if ouvert else "port deja ferme"
        print(message)
        self.annonce(message)
        return True, message

    def ecrit(self, octets):
        """Commande -> carte. False si le port est ferme."""
        with self.verrou_serie:
            if self.serie is None:
                return False
            try:
                self.serie.write(octets)
                return True
            except (serial.SerialException, OSError):
                return False

    def etat(self):
        return {"ouvert": self.serie is not None, "port": self.nom_port, "vitesse": self.vitesse,
                "vitesses": VITESSES, "ports": liste_ports(), "tcp": self.port_tcp}

    def lit_serie(self):
        while True:
            serie = self.serie
            if serie is None:
                time.sleep(0.2)
                continue
            try:
                brut = serie.read(4096)
            except (serial.SerialException, OSError, TypeError, AttributeError):
                # Port ferme depuis la page pendant la lecture, ou carte debranchee
                if self.serie is serie:
                    with self.verrou_serie:
                        self._ferme_sans_verrou()
                    self.annonce(f"port {self.nom_port} perdu (carte debranchee ?) : port ferme")
                time.sleep(0.2)
                continue
            if not brut:
                continue
            self.diffuse_octets(brut)
            texte = brut.decode("utf-8", "replace")
            if self.journal:
                self.journal.write(texte)
                self.journal.flush()
            colore = self.coloriseur.morceau(texte)
            if colore:
                self.diffuse(colore)

    # ------------------------------------------------------------------ diffusion
    @staticmethod
    def _envoie(liste, octets):
        for client in list(liste):
            try:
                client.sendall(octets)
            except OSError:
                liste.remove(client)

    def diffuse(self, colore, note=False):
        """Texte -> clients TCP bruts et pages. note=True : message du pont, visible dans les deux vues de la page."""
        # xterm.js veut CR+LF pour revenir en debut de ligne ; le navigateur recoit le texte tel quel
        brut = colore.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        evenement = (pont_serie_web.evenement_note if note else pont_serie_web.evenement_sse)(colore)
        with self.verrou:
            self.historique.append(evenement)
            self._envoie(self.clients, brut)
            self._envoie(self.clients_web, evenement)

    def diffuse_octets(self, octets):
        """Octets bruts recus -> pages seulement (vue Reception = Hex) ; les clients TCP les ont deja en texte."""
        evenement = pont_serie_web.evenement_octets(octets)
        with self.verrou:
            self.historique.append(evenement)
            self._envoie(self.clients_web, evenement)

    def annonce(self, message):
        """Message du pont (hors flux de la carte) + nouvel etat pousse a toutes les pages ouvertes."""
        self.diffuse(f"\x1b[1m\x1b[96m[pont] {message}\x1b[0m\n", note=True)
        etat = pont_serie_web.evenement_etat(self.etat())
        with self.verrou:
            self._envoie(self.clients_web, etat)

    def inscrit_web(self, client):
        etat = pont_serie_web.evenement_etat(self.etat())
        with self.verrou:
            client.sendall(etat)
            if self.historique:
                client.sendall(b"".join(self.historique))
            self.clients_web.append(client)

    def desinscrit_web(self, client):
        with self.verrou:
            if client in self.clients_web:
                self.clients_web.remove(client)

    # ------------------------------------------------------------------ clients
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
                self.ecrit(donnees)   # commandes tapees -> carte (ignorees si port ferme)
        except OSError:
            pass
        with self.verrou:
            if client in self.clients:
                self.clients.remove(client)
        client.close()
        print(f"client deconnecte : {adresse[0]}:{adresse[1]}")


def main():
    options = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    options.add_argument("--port", default="auto", help="port serie : auto (seul port USB), COM11, /dev/ttyUSB0, loop://, aucun")
    options.add_argument("--vitesse", type=int, default=115200)
    options.add_argument("--tcp", type=int, default=7000, help="port TCP local (TCP brut ET HTTP)")
    options.add_argument("--journal", help="copie brute (sans couleurs) du flux dans ce fichier")
    options.add_argument("--sans-couleurs", action="store_true", help="flux transmis tel quel (carte non Tasmota)")
    options.add_argument("--lister", action="store_true", help="affiche les ports serie et sort")
    args = options.parse_args()

    if args.lister:
        for p in liste_ports():
            print(f"{p['port']:8} {'USB ' if p['usb'] else '    '} {p['description']}")
        return

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

    journal = open(args.journal, "a", encoding="utf-8") if args.journal else None
    pont = Pont(coloriseur, journal, args.tcp, args.vitesse)
    # Port serie ouvert si possible ; sinon le pont demarre quand meme, port FERME, a ouvrir
    # depuis la page web (bouton Demarrer, choix du port et de la vitesse).
    nom_port = None if args.port.lower() == "aucun" else choisit_port(args.port)
    if nom_port:
        pont.ouvre(nom_port, args.vitesse)
    threading.Thread(target=pont.lit_serie, daemon=True).start()

    print(f"Pont -> 127.0.0.1:{args.tcp}  (Ctrl+C pour arreter)")
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
        with pont.verrou_serie:
            pont._ferme_sans_verrou()
        time.sleep(0.1)


if __name__ == "__main__":
    main()
