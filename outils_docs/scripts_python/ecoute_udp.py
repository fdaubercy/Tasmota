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
"""

import socket
import struct
import threading

FENETRE_SEQ = 16            # comme modbusFonctions.FENETRE_SEQ
GROUPE, PORT = "224.3.0.1", 4000


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


def fiche(texte, ip, carte, types, derniers, horodatage):
    """Datagramme -> (fiche pour le fil de la page, alertes, id de l'esclave ou None, push accepte ?)."""
    import decodeur_modbus as dm
    base = {"t": horodatage, "dt": None, "sens": "udp", "lat": None, "fc": None}
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
