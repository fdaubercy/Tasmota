"""Emulation des esclaves du bus pour le sniffeur ModBus (sniffeur_modbus.py) : tester le maitre P4 sans eux.

Les esclaves emulables sont ceux du persist du maitre (decodeur_modbus.charge_carte) :
  - carte 16 relais (driver 'conn16') : test_rs485_pc.CarteRelaisEmulee ;
  - esclave ESP32 Tasmota (driver 'esp32') : EsclaveEsp32Emule ci-dessous, qui repond comme
    modbusFonctions.executeCmdModbus cote esclave :
      0x01 relais (224, 256)               -> 1 octet, bit 0 = Power
      0x02 interrupteurs, boutons, capteurs -> 1 octet, bit 0 : SwitchMode 1 -> 1 = ON ; 2 -> 1 = OFF
      0x04 thermometres (1312 : 1 float ; 1216 DHT22 : temperature + humidite), analogiques et
           compteurs (uint32) ; float et uint32 gros-boutiens, 2 registres par valeur
      0x05 FF00 = Power ON ; 0x06 octet fort 02 = Power ON, 01 = OFF, octet faible = delai (s) avant
           inversion ; 0x10 LEDs WS2812 (1376) : teinte, saturation, luminosite. Echo de la requete.
    Un registre inconnu ne recoit AUCUNE reponse (l'esclave reel journalise et se tait).
Valeurs editables depuis la page (choix du 2026-10-06) ; les commandes recues les mettent a jour.
Le SwitchMode utilise est celui de la copie du maitre : la page montre donc l'etat que le maitre lira.
"""

import struct
import time

import decodeur_modbus as dm
import test_rs485_pc as rs

DEFAUTS = {"thermometres": 21.5, "analogiques": 500, "compteurs": 0}


class EsclaveEsp32Emule:
    def __init__(self, esclave):
        self.id, self.nom = esclave["id"], esclave["nom"]
        self.appareils = {}                 # registre -> {nom, famille, type, switchMode, valeur(s)}
        for reg, a in esclave["appareils"].items():
            v = dict(a)
            if a["famille"] == "relais" and a["type"] in (224, 256):
                v.update(power=False, inverse_a=None)
            elif a["type"] == 1376:
                v.update(hsb=[0, 0, 0])
            elif a["famille"] in ("interrupteurs", "boutons", "capteurs"):
                v.update(etat="OFF")
            elif a["famille"] in DEFAUTS:
                v.update(valeur=DEFAUTS[a["famille"]], humidite=55.0)
            self.appareils[reg] = v

    def _power(self, a):
        """Power courant, inversion programmee (delai d'une commande 0x06) comprise."""
        if a["inverse_a"] is not None and time.monotonic() >= a["inverse_a"]:
            a["power"], a["inverse_a"] = not a["power"], None
        return a["power"]

    def etat(self):
        """Pour la page : un appareil par ligne, avec ce qui est editable."""
        lignes = []
        for reg, a in sorted(self.appareils.items()):
            ligne = {"registre": reg, "nom": a["nom"], "famille": a["famille"], "type": a["type"]}
            if "power" in a:
                ligne.update(champ="power", valeur="ON" if self._power(a) else "OFF")
            elif "etat" in a:
                ligne.update(champ="etat", valeur=a["etat"], switchMode=a["switchMode"])
            elif "hsb" in a:
                ligne.update(champ="hsb", valeur=a["hsb"])
            elif "valeur" in a:
                ligne.update(champ="valeur", valeur=a["valeur"])
                if a["type"] == 1216:
                    ligne["humidite"] = a["humidite"]
            lignes.append(ligne)
        return {"id": self.id, "nom": self.nom, "driver": "esp32", "appareils": lignes}

    def modifie(self, reg, champ, valeur):
        a = self.appareils.get(reg)
        if a is None or champ not in a:
            raise ValueError(f"registre {reg} : champ {champ!r} non modifiable")
        if champ == "power":
            a["power"], a["inverse_a"] = valeur == "ON", None
        elif champ == "etat":
            a["etat"] = "ON" if valeur == "ON" else "OFF"
        elif champ in ("valeur", "humidite"):
            a[champ] = float(valeur) if a["famille"] == "thermometres" else int(valeur)

    def reponse(self, trame):
        """Reponse a une requete, ou None."""
        if not dm.crc_ok(trame) or trame[0] != self.id or len(trame) < 8:
            return None
        fc, reg = trame[1], trame[2] << 8 | trame[3]
        a = self.appareils.get(reg)
        if a is None:
            return None
        if fc == 1 and "power" in a:
            return rs.avec_crc(bytes((self.id, 1, 1, 1 if self._power(a) else 0)))
        if fc == 2 and "etat" in a:
            actif = (a["etat"] == "ON") != (a["switchMode"] == 2)     # executeCmdModbus : 0xFF / 0x00
            return rs.avec_crc(bytes((self.id, 2, 1, 1 if actif else 0)))
        if fc == 4 and "valeur" in a:
            if a["famille"] == "thermometres":
                donnees = struct.pack(">f", a["valeur"]) + (struct.pack(">f", a["humidite"]) if a["type"] == 1216 else b"")
            else:
                donnees = (int(a["valeur"]) & 0xFFFFFFFF).to_bytes(4, "big")
            return rs.avec_crc(bytes((self.id, 4, len(donnees))) + donnees)
        if fc == 5 and "power" in a and len(trame) == 8:
            a["power"], a["inverse_a"] = trame[4] == 0xFF, None
            return bytes(trame)
        if fc == 6 and "power" in a and len(trame) == 8:
            a["power"] = trame[4] == 2
            a["inverse_a"] = time.monotonic() + trame[5] if trame[5] else None
            return bytes(trame)
        if fc == 16 and "hsb" in a and len(trame) >= 15:
            a["hsb"] = [trame[7 + 2 * k] << 8 | trame[8 + 2 * k] for k in range(3)]
            return rs.avec_crc(bytes(trame[:6]))
        return None


class CarteRelaisEmuleeVue(rs.CarteRelaisEmulee):
    """La carte 16 relais emulee, avec l'etat attendu par la page."""

    def __init__(self, esclave, debit):
        super().__init__(esclave["id"], debit)
        self.nom, self.noms = esclave["nom"], {r: a["nom"] for r, a in esclave["appareils"].items()}

    def etat(self):
        return {"id": self.id, "nom": self.nom, "driver": "conn16",
                "appareils": [{"registre": k + 1, "nom": self.noms.get(k + 1, f"canal {k + 1}"), "famille": "sortie",
                               "champ": "sortie", "valeur": "open" if s else "close"} for k, s in enumerate(self.sorties)]}

    def modifie(self, reg, champ, valeur):
        if champ != "sortie" or not 1 <= reg <= 16:
            raise ValueError("sortie 1..16")
        self.sorties[reg - 1] = 1 if valeur == "open" else 0


class Emulation:
    """Les esclaves emules, par adresse. Une diffusion (0xFF) ne s'adresse qu'a la carte relais."""

    def __init__(self, carte, debit):
        self.carte, self.debit, self.actifs = carte, debit, {}

    def active(self, ident, actif):
        if not actif:
            self.actifs.pop(ident, None)
            return
        e = self.carte.get(ident)
        if e is None:
            raise ValueError(f"adresse {ident} absente du persist du maitre")
        if ident not in self.actifs:
            self.actifs[ident] = CarteRelaisEmuleeVue(e, self.debit) if e["driver"] == "conn16" else EsclaveEsp32Emule(e)

    def reponse(self, trame):
        if len(trame) < 2:
            return None
        if trame[0] == 0xFF:
            cartes = [x for x in self.actifs.values() if isinstance(x, CarteRelaisEmuleeVue)]
            return cartes[0].reponse(trame) if len(cartes) == 1 else None
        x = self.actifs.get(trame[0])
        return x.reponse(trame) if x else None

    def modifie(self, ident, reg, champ, valeur):
        x = self.actifs.get(ident)
        if x is None:
            raise ValueError(f"esclave {ident} non emule")
        x.modifie(reg, champ, valeur)

    def etat(self):
        """Tous les esclaves emulables, actifs ou non (la page les liste)."""
        return [dict(self.actifs[i].etat(), actif=True) if i in self.actifs else
                {"id": i, "nom": e["nom"], "driver": e["driver"], "actif": False, "appareils": []}
                for i, e in sorted(self.carte.items())]
