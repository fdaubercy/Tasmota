"""Ecoute du push UDP des esclaves ModBus, pour le sniffeur (sniffeur_modbus.py).

Le plan telemetrie (PROTOCOLE_MODBUS.md section 9) ne passe pas par le RS485 : sur un changement
d'interrupteur, de bouton, de capteur ou de compteur, l'esclave envoie en UDP multicast
    "ModbusPushUDP <seq> <trame en hexa>"     (ou "ModbusPushUDP <trame>" avant le numero d'ordre)
vers 224.3.0.1:4000 (controleUDP.be). La trame est une 0x10 standard dont l'adresse est celle de
l'esclave EMETTEUR. Ce module rejoint le groupe (ecoute seule, rien n'est emis) et juge chaque push
comme le maitre (modbusFonctions.accepteSeq) :
    - seq plus grand que le dernier accepte -> accepte (un ecart > 1 = push perdus entre-temps) ;
    - seq == 1 apres un plus grand, ou recul de plus de FENETRE_SEQ -> redemarrage de l'esclave, accepte ;
    - sinon -> doublon ou datagramme en retard, ECARTE par le maitre.
Les autres messages du groupe (ImAlive, Timestamp, ipMaitre...) sont comptes et montres a part.
Pare-feu Windows : il doit laisser entrer l'UDP vers python.exe, sinon rien n'arrive.

RELAIS MQTT DU MAITRE (EcouteRelaisMQTT) : les esclaves sont clients du point d'acces du maitre
(NAPT, 192.168.4.0/24) ; leur multicast n'en sort pas et le PC, sur le Wi-Fi maison, ne le voit
jamais. Avec ReglageModbus RelaisPushMQTT ON, le maitre republie chaque push recu, brut, sur
tele/<topic>/MODBUSPUSH = {"ip": ..., "msg": "ModbusPushUDP <seq> <hexa>"} (modbusFonctions.
relaiePushMQTT). Ce module s'y abonne (lecture seule, rien n'est publie) ; chaque push est juge
comme les autres, avec sa propre table de numeros d'ordre (une copie UDP et une copie MQTT du meme
push ne sont pas des doublons). Ne montre que ce que le MAITRE a recu.
"""

import json
import socket
import struct
import threading
import time

FENETRE_SEQ = 16            # comme modbusFonctions.FENETRE_SEQ
GROUPE, PORT = "224.3.0.1", 4000
TOPICS_RELAIS = ["tele/+/MODBUSPUSH", "tele/+/+/MODBUSPUSH"]     # un topic Tasmota peut contenir un '/'


def juge_seq(derniers, ident, seq):
    """Verdict du maitre sur un numero d'ordre : (accepte, texte). Met 'derniers' a jour comme lui."""
    if seq is None:
        return True, "sans numero d'ordre (esclave ancien) : accepte sans filtrage"
    dernier = derniers.get(ident)
    if dernier is None or seq > dernier:
        derniers[ident] = seq
        if dernier is not None and seq > dernier + 1:
            return True, f"seq {seq} accepte - {seq - dernier - 1} push perdu(s) depuis {dernier}"
        return True, f"seq {seq} accepte"
    if (seq == 1 and dernier > 1) or dernier - seq > FENETRE_SEQ:
        derniers[ident] = seq
        return True, f"seq {seq} apres {dernier} : redemarrage de l'esclave, accepte"
    return False, f"seq {seq} ECARTE par le maitre (dernier accepte {dernier}) : doublon ou datagramme en retard"


def analyse(texte):
    """'ModbusPushUDP [seq] hexa' -> (seq ou None, bytes) ; autre message -> None."""
    mots = texte.split()
    if not mots or mots[0] != "ModbusPushUDP" or len(mots) < 2:
        return None
    seq = int(mots[1]) if len(mots) >= 3 and mots[1].isdigit() else None
    try:
        return seq, bytes.fromhex("".join(mots[2:] if seq is not None else mots[1:]))
    except ValueError:
        return seq, b""


def fiche(texte, ip, carte, types, derniers, horodatage, via="udp"):
    """Datagramme -> (fiche pour le fil de la page, alertes, id de l'esclave ou None, push accepte ?).
    via : "udp" (multicast entendu directement) ou "mqtt" (relais du maitre)."""
    import decodeur_modbus as dm
    base = {"t": horodatage, "dt": None, "sens": via, "lat": None, "fc": None}
    if via == "mqtt":
        ip = f"{ip}, relaye par le maitre en MQTT"
    p = analyse(texte)
    if p is None:
        return dict(base, hex="", crc=True, nature="udp", id=None, texte=f"UDP de {ip} : {texte[:200]}"), [], None, None
    seq, trame = p
    if len(trame) < 4:
        return dict(base, hex=trame.hex(" ").upper(), crc=False, nature="ko", id=None,
                    texte=f"ModbusPushUDP illisible de {ip} : {texte[:200]}"), [], None, None
    dec = dm.decode(trame, None, carte, types)
    accepte, verdict = juge_seq(derniers, trame[0], seq) if dm.crc_ok(trame) else (False, "CRC faux : ecarte")
    alertes = []
    if "perdu" in verdict:
        alertes.append({"type": "push", "niveau": "alerte", "texte": f"id {trame[0]} : {verdict}"})
    elif not accepte:
        alertes.append({"type": "push", "niveau": "info", "texte": f"id {trame[0]} : {verdict}"})
    texte_fiche = f"PUSH {dec['metier'] or dec['norme']} [{verdict}] (de {ip})"
    return (dict(base, hex=dm.hx(trame), crc=dm.crc_ok(trame), nature="push", id=trame[0], fc=trame[1],
                 texte=texte_fiche, norme=dec["norme"], metier=dec["metier"], champs=dec["champs"]),
            alertes, trame[0], accepte)


class EcouteUDP:
    def __init__(self, recoit, groupe=GROUPE, port=PORT, interface="0.0.0.0"):
        """recoit(texte, ip) est appelee pour chaque datagramme (depuis le fil d'ecoute)."""
        self.recoit, self.groupe, self.port, self.interface = recoit, groupe, port, interface
        self.sock, self.erreur = None, ""

    def demarre(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            # Partage du port : sous Windows, chaque socket membre du groupe recoit sa copie.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", self.port))
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                         struct.pack("4s4s", socket.inet_aton(self.groupe), socket.inet_aton(self.interface)))
        except OSError as erreur:
            self.erreur = f"ecoute UDP {self.groupe}:{self.port} impossible : {erreur}"
            return False
        self.sock = s
        threading.Thread(target=self._boucle, daemon=True).start()
        return True

    def _boucle(self):
        while self.sock is not None:
            try:
                octets, (ip, _port) = self.sock.recvfrom(2048)
            except OSError:
                continue                # WinError 10054 (ICMP) ou socket ferme : sans objet
            try:
                self.recoit(octets.decode("utf-8", errors="replace").strip(), ip)
            except Exception as erreur:     # un datagramme mal forme ne doit jamais arreter l'ecoute
                print(f"datagramme UDP de {ip} ignore : {erreur!r}")

    def arrete(self):
        s, self.sock = self.sock, None
        if s:
            s.close()


def lit_relais(payload):
    """Charge de tele/<topic>/MODBUSPUSH -> (texte du push, ip de l'esclave), ou None si illisible."""
    try:
        d = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
        return (d["msg"], str(d.get("ip", "?"))) if isinstance(d, dict) and isinstance(d.get("msg"), str) else None
    except (ValueError, UnicodeDecodeError):
        return None


class EcouteRelaisMQTT:
    """Abonnement aux push relayes par le maitre ; reconnexion automatique. 'etat' : texte pour la page."""

    def __init__(self, recoit, hote, port=1883, utilisateur="", mot_de_passe="", change=None):
        """recoit(texte, ip, "mqtt") pour chaque push ; change() a chaque changement d'etat."""
        import client_mqtt
        self.client_mqtt, self.recoit, self.change = client_mqtt, recoit, change or (lambda: None)
        self.client = client_mqtt.ClientMQTT(hote, port, f"sniffeur-modbus-{socket.gethostname()}-{id(self) % 10000}",
                                             utilisateur, mot_de_passe)
        self.etat, self.actif = f"{hote}:{port} : connexion...", False

    def demarre(self):
        if not self.client.hote:
            self.etat = "aucun broker (MQTT_HOST absent de user_config_override.h, ou --mqtt-hote)"
            return False
        self.actif = True
        threading.Thread(target=self._boucle, daemon=True).start()
        return True

    def _note(self, etat):
        if etat != self.etat:
            self.etat = etat
            print(f"relais MQTT : {etat}")
            self.change()

    def _boucle(self):
        attente, c = 2, self.client
        while self.actif:
            try:
                c.connecte()
                c.abonne(TOPICS_RELAIS)
                self._note(f"{c.hote}:{c.port} connecte, abonne a {TOPICS_RELAIS[0]}")
                attente = 2
                while self.actif:
                    m = c.recoit()
                    if m is not None and m.topic.endswith("/MODBUSPUSH"):
                        relais = lit_relais(m.payload)
                        if relais:
                            try:
                                self.recoit(relais[0], relais[1], "mqtt")
                            except Exception as erreur:     # un message mal forme ne doit jamais arreter l'ecoute
                                print(f"relais MQTT {m.topic} ignore : {erreur!r}")
                    c.entretient()
            except (OSError, self.client_mqtt.ErreurMQTT) as erreur:
                c.ferme()
                if self.actif:
                    self._note(f"{c.hote}:{c.port} indisponible ({erreur or erreur.__class__.__name__}), nouvel essai")
                    time.sleep(attente)
                    attente = min(attente * 2, 30)

    def arrete(self):
        self.actif = False
        self.client.ferme()


def options_relais(options):
    """Options --mqtt* du sniffeur ; broker par defaut = celui des modules (user_config_override.h)."""
    from sniffeur_mqtt import lit_config_broker
    b = lit_config_broker()
    options.add_argument("--mqtt", choices=("oui", "non"), default="oui",
                         help="ecoute des push relayes par le maitre (ReglageModbus RelaisPushMQTT ON)")
    options.add_argument("--mqtt-hote", dest="mqtt_hote", default=b.get("MQTT_HOST", ""))
    options.add_argument("--mqtt-port", dest="mqtt_port", type=int, default=int(b.get("MQTT_PORT", 1883)))
    options.add_argument("--mqtt-utilisateur", dest="mqtt_utilisateur", default=b.get("MQTT_USER", ""))
    options.add_argument("--mqtt-mdp", dest="mqtt_mdp", default=b.get("MQTT_PASS", ""))
