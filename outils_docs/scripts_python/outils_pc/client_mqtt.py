"""Client MQTT 3.1.1 minimal, en Python pur (aucune dependance : paho-mqtt n'est pas dans le
Python de PlatformIO, et l'y installer pendant qu'un 'pio' tourne a deja casse le penv).

Couvre ce dont le sniffeur a besoin, et rien de plus :
    CONNECT (utilisateur / mot de passe, keepalive, TLS optionnel), SUBSCRIBE / UNSUBSCRIBE en QoS 0,
    PUBLISH en QoS 0 (avec ou sans retain), reception des PUBLISH, PINGREQ.
Abonne en QoS 0, le broker livre au plus en QoS 0 : pas d'acquittement a gerer. Un PUBLISH
recu en QoS 1 est tout de meme acquitte (PUBACK), par prudence.

Usage :
    c = ClientMQTT("192.168.0.5", 1883, "sniffeur-pc", "user", "mdp")
    c.connecte()                       # leve OSError / ErreurMQTT
    c.abonne(["#"])
    while True:
        message = c.recoit()            # None si rien pendant ~1 s ; leve OSError si coupe
        c.entretient()                  # PINGREQ quand il le faut
"""

import socket
import ssl
import struct
import threading
import time

CODES_CONNACK = {1: "version de protocole refusee", 2: "identifiant client refuse", 3: "broker indisponible",
                 4: "utilisateur ou mot de passe incorrect", 5: "non autorise"}


class ErreurMQTT(Exception):
    pass


def _chaine(texte):
    octets = texte.encode("utf-8") if isinstance(texte, str) else texte
    return struct.pack("!H", len(octets)) + octets


def _longueur_restante(n):
    sortie = bytearray()
    while True:
        octet, n = n % 128, n // 128
        sortie.append(octet | (0x80 if n else 0))
        if not n:
            return bytes(sortie)


class Message:
    """Un PUBLISH recu."""
    __slots__ = ("topic", "payload", "qos", "retain", "instant")

    def __init__(self, topic, payload, qos, retain):
        self.topic, self.payload, self.qos, self.retain = topic, payload, qos, retain
        self.instant = time.time()


class ClientMQTT:
    def __init__(self, hote, port, client_id, utilisateur="", mot_de_passe="", keepalive=30,
                 tls=False, verifier_certificat=True):
        self.hote, self.port, self.client_id = hote, int(port), client_id
        self.utilisateur, self.mot_de_passe, self.keepalive = utilisateur, mot_de_passe, keepalive
        self.tls, self.verifier_certificat = tls, verifier_certificat     # MQTT sur TLS (port 8883 en general)
        self.sock = None
        self._verrou = threading.Lock()     # envois depuis plusieurs fils (HTTP + boucle MQTT)
        self._tampon = b""
        self._dernier_envoi = 0.0
        self._id_paquet = 0

    # ------------------------------------------------------------------ connexion
    def connecte(self):
        self.ferme()
        sock = socket.create_connection((self.hote, self.port), timeout=10)
        if self.tls:
            contexte = ssl.create_default_context()
            if not self.verifier_certificat:          # certificat auto-signe d'un broker local
                contexte.check_hostname = False
                contexte.verify_mode = ssl.CERT_NONE
            try:
                sock = contexte.wrap_socket(sock, server_hostname=self.hote)
            except (OSError, ssl.SSLError):
                sock.close()
                raise
        self.sock = sock
        self._tampon = b""
        drapeaux = 0x02                                         # clean session
        charge = _chaine(self.client_id)
        if self.utilisateur:
            drapeaux |= 0x80
            charge += _chaine(self.utilisateur)
            if self.mot_de_passe:
                drapeaux |= 0x40
                charge += _chaine(self.mot_de_passe)
        variable = _chaine("MQTT") + bytes((4, drapeaux)) + struct.pack("!H", self.keepalive)
        self._envoie(0x10, variable + charge)
        type_paquet, corps = self._lit_paquet(attente=10)
        if type_paquet != 0x20 or len(corps) < 2:
            raise ErreurMQTT("reponse inattendue a CONNECT")
        if corps[1]:
            raise ErreurMQTT(f"connexion refusee : {CODES_CONNACK.get(corps[1], corps[1])}")
        self.sock.settimeout(1.0)

    def ferme(self):
        if self.sock is not None:
            try:
                self._envoie(0xE0, b"")                        # DISCONNECT
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    # ------------------------------------------------------------------ commandes
    def _nouvel_id(self):
        self._id_paquet = self._id_paquet % 65535 + 1
        return self._id_paquet

    def abonne(self, filtres):
        if filtres:
            corps = struct.pack("!H", self._nouvel_id()) + b"".join(_chaine(f) + b"\x00" for f in filtres)
            self._envoie(0x82, corps)

    def desabonne(self, filtres):
        if filtres:
            self._envoie(0xA2, struct.pack("!H", self._nouvel_id()) + b"".join(_chaine(f) for f in filtres))

    def publie(self, topic, payload, retain=False):
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self._envoie(0x30 | (0x01 if retain else 0), _chaine(topic) + payload)

    def entretient(self):
        """PINGREQ si rien n'a ete envoye depuis la moitie du keepalive."""
        if self.sock is not None and time.time() - self._dernier_envoi > self.keepalive / 2:
            self._envoie(0xC0, b"")

    # ------------------------------------------------------------------ reception
    def recoit(self):
        """Prochain PUBLISH recu (Message), ou None si rien pendant ~1 s. Leve OSError si la liaison tombe."""
        try:
            type_paquet, corps, drapeaux = self._lit_paquet(attente=1.0, avec_drapeaux=True)
        except socket.timeout:
            return None
        if type_paquet != 0x30:
            return None                                         # SUBACK, UNSUBACK, PINGRESP...
        qos, retain = (drapeaux >> 1) & 0x03, bool(drapeaux & 0x01)
        longueur = struct.unpack("!H", corps[:2])[0]
        topic = corps[2:2 + longueur].decode("utf-8", "replace")
        position = 2 + longueur
        if qos:
            id_paquet = corps[position:position + 2]
            position += 2
            if qos == 1:
                self._envoie(0x40, id_paquet)                   # PUBACK
        return Message(topic, corps[position:], qos, retain)

    def _lit_paquet(self, attente, avec_drapeaux=False):
        fin = time.time() + attente
        while True:
            paquet = self._extrait()
            if paquet is not None:
                octet, corps = paquet
                return (octet & 0xF0, corps, octet & 0x0F) if avec_drapeaux else (octet & 0xF0, corps)
            if time.time() > fin:
                raise socket.timeout()
            morceau = self.sock.recv(65536)
            if not morceau:
                raise ConnectionError("le broker a ferme la connexion")
            self._tampon += morceau

    def _extrait(self):
        """Un paquet complet du tampon -> (octet d'en-tete, corps), sinon None."""
        if len(self._tampon) < 2:
            return None
        longueur, multiplicateur, i = 0, 1, 1
        while True:
            if i >= len(self._tampon):
                return None
            octet = self._tampon[i]
            longueur += (octet & 0x7F) * multiplicateur
            multiplicateur *= 128
            i += 1
            if not octet & 0x80:
                break
            if i > 4:
                raise ErreurMQTT("longueur de paquet invalide")
        if len(self._tampon) < i + longueur:
            return None
        entete, corps = self._tampon[0], self._tampon[i:i + longueur]
        self._tampon = self._tampon[i + longueur:]
        return entete, corps

    def _envoie(self, entete, corps):
        if self.sock is None:
            raise ConnectionError("non connecte")
        with self._verrou:
            self.sock.sendall(bytes((entete,)) + _longueur_restante(len(corps)) + corps)
            self._dernier_envoi = time.time()
