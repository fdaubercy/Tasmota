"""Cartes Tasmota SIMULEES pour le banc test_testeur_udp.py : faux port serie, carte qui repond aux commandes
du testeur (Status 5, ReglageLog, ModeConnexion, ReglageUDP, ReglageModbus...), faux reseau entre les deux."""

import json
import queue
import threading

import serial

D, E, R = "Données", "envoyées", "reçues"


class FauxSerie:
    def __init__(self, sim):
        self.sim, self.q, self.mort = sim, queue.Queue(), False
        self.tampon = ""

    def read(self, n):
        if self.mort:
            raise serial.SerialException("ClearCommError failed (simule)")
        try:
            return self.q.get(timeout=0.04)
        except queue.Empty:
            return b""

    def write(self, octets):
        if self.mort:
            raise serial.SerialException("port perdu (simule)")
        self.tampon += octets.decode("utf-8")
        *lignes, self.tampon = self.tampon.split("\n")
        for ligne in lignes:
            self.sim.recoit(ligne)

    def close(self):
        self.mort = True

    def sort(self, texte):
        self.q.put((texte + "\n").encode("utf-8"))


class Sim:
    """Une carte Tasmota simulee : repond aux commandes que le testeur envoie."""

    def __init__(self, role, reseau, ip, mode="RangeExtender"):
        self.role, self.reseau, self.ip, self.mode = role, reseau, ip, mode
        self.serie, self.absent, self.recus = None, False, []
        self.niveaux = {"udp": "info", "modbus": "info", "serie": "info (actif : debug)", "mqtt": "erreur"}
        self.ruban, self.bug_rs485 = True, False
        self.refuse_bascule = False                      # True : refuse ModeConnexion comme la vraie carte
        self.dits = []                                   # tout ce que la carte a ecrit sur son port
        self.sans_mode_connexion = False                 # True : firmware anterieur a ModeConnexion (2026-10-16)
        self.serie_coupee = False                        # True : log serie coupe par SERIALLOG_TIMER (600 s)
        self.reveils = 0                                 # SerialLog reappliques (COMMANDE_REVEIL_SERIE)
        self.muette = False                              # True : plus rien sur le port, commandes comprises (2026-10-17)

    def ouvre(self):
        if self.absent:
            raise serial.SerialException("could not open port 'COM_X': FileNotFoundError(2, 'introuvable', None, 3)")
        self.serie = FauxSerie(self)
        return self.serie

    def dit(self, texte):
        if self.serie and not self.serie.mort and not self.serie_coupee and not self.muette:
            self.dits.append(texte)
            self.serie.sort("12:34:56.789 " + texte)

    def redemarre(self, duree=1.0):
        """Le port disparait, la carte revient 'duree' s plus tard."""
        self.serie.mort, self.absent = True, True
        threading.Timer(duree, lambda: setattr(self, "absent", False)).start()

    def recoit(self, ligne):
        self.recus.append(ligne)
        mots = ligne.split(" ")
        if ligne.startswith("Br ") and 'tasmota.cmd("SerialLog"' in ligne:
            # Niveau REGLE reapplique : Tasmota arrete son compteur de 600 s et le log serie revient
            self.reveils += 1
            self.serie_coupee = False
            self.dit('RSL: RESULT = {"Br":"nil"}')
            return
        if ligne.startswith("ReglageGlobal ModeConnexion") and self.sans_mode_connexion:
            # Reponse reelle de la cuve flashee avant le 2026-10-16 (journal du 2026-10-17)
            self.dit("ReglageGlobal : sous-commande 'ModeConnexion' inconnue")
            self.dit(json.dumps({"ReglageGlobal": {"Erreur": "sous-commande inconnue",
                                                   "SousCommandes": ["afficheMemoire", "nbLogsFiles"]}}))
            return
        if ligne == "Status 5":
            self.dit('RSL: STATUS5 = {"StatusNET":{"Hostname":"%s","IPAddress":"%s","Mac":"AA:BB:CC"}}' % (self.role, self.ip))
        elif ligne == "ReglageLog":
            mods = {k: self.niveaux[k].split()[0] for k in ("udp", "modbus")}
            sor = {"serie": self.niveaux["serie"], "web": "info", "mqtt": self.niveaux["mqtt"], "syslog": "info"}
            self.dit(json.dumps({"ReglageLog": {"profil": "normal", "profils": ["normal"], "sorties": sor, "modules": mods}}))
        elif mots[0] == "ReglageLog" and len(mots) == 3:
            self.niveaux[mots[1]] = mots[2]
            self.dit(json.dumps({"ReglageLog": {mots[1]: mots[2]}}))
        elif ligne == "ReglageGlobal ModeConnexion":
            self.dit(json.dumps({"ReglageGlobal": {"modeConnexion": self.mode}}))
        elif ligne.startswith("ReglageGlobal ModeConnexion "):
            # Memes reponses que globalFonctions.reglageModeConnexion (data/fs/globalFonctions.be) :
            # bascule -> {"modeConnexion": <nouveau>, "redemarrage": true} puis Restart ;
            # refus (ex. retour sans reseaux memorises) -> {"modeConnexion": <actuel>, "erreur": ...}
            self.dit("CMD: " + ligne)                    # la carte journalise tout, mot de passe compris
            if self.refuse_bascule:
                self.dit(json.dumps({"ReglageGlobal": {"modeConnexion": self.mode,
                                                       "erreur": "aucun reseau memorise : rien a restaurer"}}))
                return
            self.mode = mots[2]
            self.dit(json.dumps({"ReglageGlobal": {"modeConnexion": self.mode, "redemarrage": True}}))
            # La vraie carte redemarre 1 s APRES sa reponse (tasmota.set_timer(1000, ... Restart 1))
            threading.Timer(1.0, lambda: self.redemarre(1.0)).start()
        elif mots[0] == "ReglageUDP" and mots[1] == "envoiUniCast":
            self.emet("UniCast", mots[2], " ".join(mots[3:]))
        elif ligne.startswith("ReglageUDP envoiMultiCast "):
            if self.role == "maitre" or self.mode == "RangeExtender":
                self.emet("MultiCast", "224.3.0.1", ligne[len("ReglageUDP envoiMultiCast "):])
        elif ligne == "ReglageUDP forceEnvoiParams ON":
            if self.mode == "RangeExtender":
                self.emet("MultiCast", "224.3.0.1", 'ImAlive {"id":2}')
        elif ligne.startswith("ReglageModbus envoiMessageUDP "):
            self.emet("UniCast", mots[2], " ".join(mots[3:]))
        elif ligne.startswith("Br "):
            if not self.ruban:
                self.dit("PAS_DE_RUBAN")
            else:
                self.dit("POUSSE_ETAT: registre 1376 = 3")
                if self.mode == "RangeExtender":
                    self.emet("MultiCast", "224.3.0.1", "ModbusPushUDP 5 AA55")

    def emet(self, mode, ip, msg):
        self.dit(f"ENVOI_MSG_UDP: {D} {mode} {E} vers '{ip}' >>>> {msg} >>>> OK")
        pair = self.reseau.pair(self)
        if not self.reseau.perte and pair:
            pair.recoit_udp(mode, self.ip if self.mode == "RangeExtender" or self.role == "maitre" else self.ip, msg)

    def recoit_udp(self, mode, ip_source, msg):
        self.dit(f"LIRE_UDP: {D} UDP {mode} {R} de '{ip_source}' sur le port 4000")
        self.dit(f"LIRE_UDP: msg = {msg}")
        if msg.startswith("ModbusUDP ") and self.role == "esclave":
            parties = msg.split(" ")
            tid = parties[1] if len(parties) == 3 else None
            rep = "ModbusUDP " + (tid + " " if tid else "") + "020101FF2A00"
            self.dit(f"REPOND_UDP: reponse a 192.168.4.1 : {rep}")
            if self.bug_rs485:
                self.dit("ENVOI_MSG_MODBUS: Message ModBus envoyé = 0x020101FF2A00")
            self.emet("UniCast", "192.168.4.1", rep)


class Reseau:
    def __init__(self):
        self.sims, self.perte = {}, False

    def pair(self, sim):
        return self.sims["esclave" if sim.role == "maitre" else "maitre"]


