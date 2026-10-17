"""Essais du testeur UDP (testeur_udp.py) : commandes a envoyer, preuves a chercher, verdicts.

Aucun acces serie ici : un Essai recoit les lignes de log des deux cartes (observe) puis rend un
verdict (conclut). Tout est donc testable sans carte (test_testeur_udp.py).

Formats de log reconnus (ceux des modules Berry udpFonctions / modbusFonctions) :
  emission  ENVOI_MSG_UDP: Donnees <UniCast|MultiCast> envoyees vers '<ip>' >>>> <message> >>>> <OK|Echec|nil>
            ENVOI_MSG_UDP: Reseau non connecte, '<message>' non envoye !
  reception LIRE_UDP: Donnees UDP <UniCast|MultiCast> recues de '<ip>' sur le port <n>   (ligne 1)
            LIRE_UDP: msg = <message>                                                   (ligne 2)
  reponse   REPOND_UDP: reponse a <ip> : ModbusUDP <tid> <hexa>      (esclave, trame ModBus E1)
  RS485     ENVOI_MSG_MODBUS: Message ModBus envoye = 0x...          (ne doit PAS apparaitre sur l'esclave)
  push      POUSSE_ETAT: registre 1376 = ...   ou   PAS_DE_RUBAN
Les accents sont decodes en « ? » si la liaison les abime : les motifs acceptent 1 a 3 caracteres.
"""

import re
import time

RECU, EMIS_NON_RECU, NON_EMIS, ECHEC, PAS_DE_RUBAN = "RECU", "EMIS NON RECU", "NON EMIS", "ECHEC", "PAS DE RUBAN"

RE_ENVOI = re.compile(r"ENVOI_MSG_UDP: Donn.{1,3}es (UniCast|MultiCast) envoy.{1,3}es vers '([^']*)' "
                      r">>>> (.*) >>>> (OK|Echec|nil)\s*$")
RE_NON_RESEAU = re.compile(r"ENVOI_MSG_UDP: Reseau non connecte, '(.*)' non envoye")
RE_ENTETE = re.compile(r"LIRE_UDP: Donn.{1,3}es UDP (UniCast|MultiCast) re.{1,3}ues de '([^']*)' sur le port (\d+)")
RE_MSG = re.compile(r"LIRE_UDP: msg = (.*?)\s*$")
RE_REPOND = re.compile(r"REPOND_UDP: reponse a (\S+) : (ModbusUDP.*?)\s*$")
RE_RS485 = re.compile(r"ENVOI_MSG_MODBUS: Message ModBus envoy.{1,3} = 0x([0-9A-Fa-f]+)")
RE_POUSSE = re.compile(r"POUSSE_ETAT: registre 1376 = ")
RE_SANS_TID = re.compile(r"^ModbusUDP [0-9A-Fa-f]{8,}$")
RE_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

COMMANDE_PUSH = ('Br var h = modbusFonctions.etatRuban(1376) if h != nil modbusFonctions.pousseEtat(1376, "uint16", h) '
                 'else print("PAS_DE_RUBAN") end')
TYPES = ("texte", "modbus", "imalive", "push")
CAS_CONNU_MULTICAST = ("cas connu : depuis la correction C4 (2026-10-17), l'esclave emet son multicast aussi en Wi-Fi "
                       "classique ; NON EMIS ici veut dire que la carte porte un firmware ANTERIEUR (a reflasher)")


def crc16(donnees):
    """CRC16 ModBus (polynome 0xA001, depart 0xFFFF), valeur entiere."""
    crc = 0xFFFF
    for octet in donnees:
        crc ^= octet
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def trame_lecture_relai(adresse):
    """Trame 0x01 (lecture du relai 1, registre 0x00E0, 1 bit) pour l'esclave d'adresse donnee, en hexa.
    Adresse 2 -> 020100E00001FC0F (CRC poids faible en premier)."""
    corps = bytes([adresse, 0x01, 0x00, 0xE0, 0x00, 0x01])
    crc = crc16(corps)
    return (corps + bytes([crc & 0xFF, crc >> 8])).hex().upper()


def contient_marqueur(message, marqueur):
    """Le marqueur doit etre un mot entier : TESTUDP-1 ne reconnait pas TESTUDP-12."""
    return re.search(r"(?<![\w-])" + re.escape(marqueur) + r"(?![\w-])", message or "") is not None


class Essai:
    """Un essai : une commande sur la carte emettrice, des preuves cherchees dans les deux logs."""

    def __init__(self, numero, type_essai, emetteur, recepteur, mode, commande, message, mode_connexion=None,
                 tid=None, avec_tid=True):
        self.numero, self.type, self.emetteur, self.recepteur = numero, type_essai, emetteur, recepteur
        self.mode, self.commande, self.message = mode, commande, message   # mode : UniCast / MultiCast
        self.mode_connexion, self.tid, self.avec_tid = mode_connexion, tid, avec_tid
        self.t0 = time.time()
        self.emissions, self.non_reseau, self.receptions, self.reponses = [], [], [], []
        self.rs485, self.pousse, self.pas_ruban = [], [], []
        self._entete = {}                       # role -> derniere ligne d'entete LIRE_UDP (le msg suit)

    # ------------------------------------------------------------------ ce que l'essai cherche
    def msg_emis(self, msg):
        if self.type == "texte":
            return contient_marqueur(msg, self.message.split(" ", 1)[0])
        if self.type == "imalive":
            return "ImAlive" in msg
        if self.type == "push":
            return msg.startswith("ModbusPushUDP ")
        return msg.startswith("ModbusUDP")

    def msg_recu(self, msg):
        if self.type == "texte":
            return contient_marqueur(msg, self.message.split(" ", 1)[0])
        if self.type == "imalive":
            return "ImAlive" in msg
        if self.type == "push":
            return msg.startswith("ModbusPushUDP ")
        if self.avec_tid:
            return msg.startswith(f"ModbusUDP {self.tid} ")
        return RE_SANS_TID.match(msg) is not None

    # ------------------------------------------------------------------ observation
    def observe(self, role, texte, t):
        """Une ligne de log de la carte 'role'. Les lignes anterieures a l'envoi sont ignorees."""
        if t < self.t0 - 0.05:
            return
        m = RE_ENVOI.search(texte)
        if m:
            self.emissions.append({"role": role, "mode": m.group(1), "ip": m.group(2), "msg": m.group(3),
                                   "resultat": m.group(4), "t": t})
            return
        m = RE_NON_RESEAU.search(texte)
        if m:
            self.non_reseau.append({"role": role, "msg": m.group(1), "t": t})
            return
        m = RE_ENTETE.search(texte)
        if m:
            self._entete[role] = (m.group(1), m.group(2), int(m.group(3)))
            return
        m = RE_MSG.search(texte)
        if m:
            mode, ip, port = self._entete.pop(role, (None, None, None))
            self.receptions.append({"role": role, "mode": mode, "ip": ip, "port": port, "msg": m.group(1), "t": t})
            return
        m = RE_REPOND.search(texte)
        if m:
            self.reponses.append({"role": role, "ip": m.group(1), "msg": m.group(2), "t": t})
        elif RE_RS485.search(texte):
            self.rs485.append({"role": role, "t": t, "hexa": RE_RS485.search(texte).group(1).upper()})
        elif RE_POUSSE.search(texte):
            self.pousse.append({"role": role, "t": t})
        elif "PAS_DE_RUBAN" in texte and role == self.emetteur:
            self.pas_ruban.append({"role": role, "t": t})

    def termine(self):
        """Verdict acquis sans attendre la fin de la fenetre (les essais ModBus attendent toute la fenetre :
        l'absence de trame RS485 ne se prouve qu'a la fin)."""
        if self.type == "modbus":
            return False
        if self.type == "push" and self.pas_ruban:
            return True
        return any(r["role"] == self.recepteur and self.msg_recu(r["msg"]) for r in self.receptions)

    # ------------------------------------------------------------------ verdict
    def conclut(self):
        """-> {verdict, delai (s ou None), source ('ip:port' ou ''), details (liste de phrases)}."""
        if self.type == "modbus":
            return self._conclut_modbus()
        if self.type == "push" and self.pas_ruban:
            return self._res(PAS_DE_RUBAN, None, "", ["pas de ruban sur cet esclave (etatRuban a rendu nil)"])
        details = []
        recues = [r for r in self.receptions if r["role"] == self.recepteur and self.msg_recu(r["msg"])]
        if recues:
            r = recues[0]
            if r["mode"] and r["mode"] != self.mode:
                details.append(f"type vu cote recepteur : {r['mode']} (attendu {self.mode})")
            return self._res(RECU, r["t"] - self.t0, self._source(r), details)
        emises = [e for e in self.emissions if e["role"] == self.emetteur and self.msg_emis(e["msg"])
                  and e["mode"] == self.mode]
        if any(e["resultat"] == "OK" for e in emises):
            e = next(e for e in emises if e["resultat"] == "OK")
            return self._res(EMIS_NON_RECU, None, "", [f"emis vers '{e['ip']}' (OK) mais aucune ligne LIRE_UDP "
                                                       f"correspondante cote {self.recepteur}"])
        if emises:
            details.append("resultat de l'emission : " + ", ".join(sorted({e["resultat"] for e in emises})))
        elif any(self._meme_message(n["msg"]) for n in self.non_reseau):
            details.append("reseau non connecte sur l'emetteur (ENVOI_MSG_UDP: Reseau non connecte)")
        else:
            details.append(f"aucune ligne ENVOI_MSG_UDP cote {self.emetteur}")
        if self.mode == "MultiCast" and self.emetteur == "esclave" and self.mode_connexion == "WifiClassique":
            details.append(CAS_CONNU_MULTICAST)
        return self._res(NON_EMIS, None, "", details)

    def _conclut_modbus(self):
        details = []
        reponses = [r for r in self.reponses if r["role"] == self.recepteur and self._reponse_attendue(r["msg"])]
        recues = [r for r in self.receptions if r["role"] == self.emetteur and self.msg_recu(r["msg"])]
        # Seule une trame RS485 IDENTIQUE a la reponse UDP prouve le defaut : le cable reste branche pendant la
        # mise au point et l'esclave continue de repondre, sur le RS485, au releve serie du maitre (constate le
        # 2026-10-17 : reponse a 0203056000058528 dans la fenetre -> faux ECHEC).
        hexas = {r["msg"].split(" ")[-1].upper() for r in reponses}
        esclave_rs485 = [r for r in self.rs485 if r["role"] == self.recepteur]
        rs485 = [r for r in esclave_rs485 if r["hexa"] in hexas]
        demandes = [r for r in self.receptions if r["role"] == self.recepteur and r["msg"].startswith("ModbusUDP")]
        emises = [e for e in self.emissions if e["role"] == self.emetteur and e["msg"].startswith("ModbusUDP")]
        if rs485:
            details.append(f"l'esclave a aussi ecrit la reponse 0x{rs485[0]['hexa']} sur le RS485 (ENVOI_MSG_MODBUS) : "
                           "elle ne doit partir que par UDP")
            return self._res(ECHEC, None, "", details)
        if len(esclave_rs485) > len(rs485):
            details.append(f"{len(esclave_rs485)} trame(s) RS485 de l'esclave pendant la fenetre, autres que la reponse "
                           "UDP (releve serie du maitre) : ignorees")
        if reponses and recues:
            r = recues[0]
            details.append(f"reponse de l'esclave : {reponses[0]['msg']}")
            details.append("aucune copie de la reponse sur le RS485 pendant la fenetre")
            return self._res(RECU, r["t"] - self.t0, self._source(r), details)
        if reponses:
            details.append(f"l'esclave a repondu ({reponses[0]['msg']}) mais le maitre n'a rien recu de "
                           f"'ModbusUDP {self.tid} ...' : reponse perdue ou attendue sur un autre tid")
            return self._res(EMIS_NON_RECU, None, "", details)
        if demandes or any(e["resultat"] == "OK" for e in emises):
            details.append("requete emise (ou recue par l'esclave) mais aucune ligne REPOND_UDP avec ce tid")
            return self._res(EMIS_NON_RECU, None, "", details)
        details.append(f"aucune ligne ENVOI_MSG_UDP ModbusUDP cote {self.emetteur}, aucune reception cote {self.recepteur}")
        return self._res(NON_EMIS, None, "", details)

    def _reponse_attendue(self, msg):
        return msg.startswith(f"ModbusUDP {self.tid} ") if self.avec_tid else RE_SANS_TID.match(msg) is not None

    def _meme_message(self, msg):
        return self.msg_emis(msg)

    @staticmethod
    def _source(r):
        return f"{r['ip']}:{r['port']}" if r.get("ip") else ""

    def _res(self, verdict, delai, source, details):
        return {"verdict": verdict, "delai": None if delai is None else round(delai, 3), "source": source,
                "details": details}


def valide_ip(ip):
    if not RE_IPV4.match(ip or "") or any(int(p) > 255 for p in ip.split(".")):
        raise ValueError(f"adresse IP invalide : {ip!r}")
    return ip


def construit_essai(numero, demande, mode_connexion):
    """Demande JSON de la page -> Essai pret a envoyer. ValueError si la demande est invalide.

    demande : type (texte|modbus|imalive|push), sens (esclave>maitre | maitre>esclave), mode (UniCast|MultiCast),
    texte, ip_maitre (destination des envois de l'esclave), ip_esclave, adresse, tid, avec_tid.
    """
    type_essai = str(demande.get("type", ""))
    if type_essai not in TYPES:
        raise ValueError(f"type d'essai inconnu : {type_essai!r}")
    sens = str(demande.get("sens", "esclave>maitre"))
    if sens not in ("esclave>maitre", "maitre>esclave"):
        raise ValueError(f"sens inconnu : {sens!r}")
    emetteur, recepteur = sens.split(">")
    mode = str(demande.get("mode", "UniCast"))
    if mode not in ("UniCast", "MultiCast"):
        raise ValueError(f"mode d'envoi inconnu : {mode!r}")
    tid, avec_tid = None, True
    if type_essai == "texte":
        texte = " ".join(str(demande.get("texte", "")).split())[:120]
        message = f"TESTUDP-{numero} {texte}".strip()
        if mode == "UniCast":
            ip = valide_ip(str(demande.get("ip_maitre" if recepteur == "maitre" else "ip_esclave", "")).strip())
            commande = f"ReglageUDP envoiUniCast {ip} {message}"
        else:
            commande = f"ReglageUDP envoiMultiCast {message}"
    elif type_essai == "modbus":
        emetteur, recepteur, mode = "maitre", "esclave", "UniCast"
        ip = valide_ip(str(demande.get("ip_esclave", "")).strip())
        adresse = int(demande.get("adresse", 2))
        if not 1 <= adresse <= 247:
            raise ValueError("adresse ModBus de l'esclave : 1 a 247")
        avec_tid = bool(demande.get("avec_tid", True))
        trame = trame_lecture_relai(adresse)
        if avec_tid:
            tid = int(demande.get("tid", 17))
            if not 0 <= tid <= 65535:
                raise ValueError("tid : 0 a 65535")
            message = f"ModbusUDP {tid} {trame}"
        else:
            message = f"ModbusUDP {trame}"
        commande = f"ReglageModbus envoiMessageUDP {ip} {message}"
    elif type_essai == "imalive":
        emetteur, recepteur, mode = "esclave", "maitre", "MultiCast"
        message, commande = "ImAlive", "ReglageUDP forceEnvoiParams ON"
    else:
        emetteur, recepteur, mode = "esclave", "maitre", "MultiCast"
        message, commande = "ModbusPushUDP", COMMANDE_PUSH
    return Essai(numero, type_essai, emetteur, recepteur, mode, commande, message, mode_connexion, tid, avec_tid)
