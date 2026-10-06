"""Surveillance du bus pour le sniffeur ModBus (sniffeur_modbus.py) : ecarts commande / releve, collisions.

Appelee pour chaque trame vue (CRC juste ou faux) ; rend des alertes {type, niveau, texte} que la
page affiche dans le fil des trames.

ECARTS (choix du 2026-10-06 : signales au 1er releve contraire). Meme logique que le maitre
(etatConstate, MODBUS_TASMOTA_SLAVE_ECART) :
  - une commande ne compte qu'une fois ACCUSEE (echo de l'esclave) ;
  - carte 16 relais : 0x06 Open / Close / Latch / Open all / Close all fixent l'etat attendu des
    sorties ; Toggle l'inverse s'il est connu ; Delay = open puis close apres la tempo ; Momentary
    n'est pas suivi. Releve = reponse 0x03 (registre a 1 = open = sortie basse) ;
  - esclave ESP32 : 0x06 (octet fort 02 = Power ON, 01 = OFF ; octet faible = delai avant inversion)
    et 0x05 (FF00 = ON). Releve = reponse 0x01 (bit 0 = Power) ;
  - a +-MARGE s d'une inversion programmee, pas de verdict ;
  - un ecart n'est signale qu'une fois ; le retour a la conformite l'est aussi.
COLLISIONS / ANOMALIES :
  - requete alors qu'une autre attend sa reponse depuis moins de 'delai' (hors rafale du PC lui-meme) :
    deux maitres sur le bus (PC + P4), ou renvoi premature ;
  - reponse sans requete en attente, ou d'un autre esclave que celui interroge : esclave qui parle
    sans y etre invite, ou requete perdue ;
  - rafale de CRC faux (au moins 2 en FENETRE_KO s) : collision, parasite, debit ou A/B.
"""

MARGE = 1.0             # s autour d'une inversion programmee (delai, Delay)
FENETRE_KO = 2.0        # s : deux CRC faux dans cette fenetre = rafale


class Surveillance:
    def __init__(self, carte, delai):
        self.carte, self.delai = carte, delai
        self.attendus = {}          # (id, registre) -> {"etat": 0|1, "inverse_a": instant|None}
        self.signales = set()       # (id, registre) dont l'ecart est deja signale
        self.en_cours = None        # {"trame", "t", "source", "repondue"} : derniere requete vue
        self.ko, self.t_alerte_ko = [], -1e9

    # ------------------------------------------------------------------ etat attendu
    def _attendu(self, cle, t):
        a = self.attendus.get(cle)
        if a is None:
            return None
        if a["inverse_a"] is None:
            return a["etat"]
        if abs(t - a["inverse_a"]) < MARGE:
            return None
        return 1 - a["etat"] if t > a["inverse_a"] else a["etat"]

    def _fixe(self, cle, etat, t, delai=0):
        self.attendus[cle] = {"etat": etat, "inverse_a": (t + delai) if delai else None}

    def _applique_conn16(self, ident, canal, ordre, tempo, t):
        canaux = range(1, 17) if canal == 0 else [canal]
        if ordre in (7, 8):
            canaux, ordre = range(1, 17), (1 if ordre == 7 else 2)
        for c in canaux:
            cle = (ident, c)
            if ordre == 1:
                self._fixe(cle, 1, t)
            elif ordre == 2:
                self._fixe(cle, 0, t)
            elif ordre == 3:
                avant = self._attendu(cle, t)
                self._fixe(cle, 1 - avant, t) if avant is not None else self.attendus.pop(cle, None)
            elif ordre == 4 and canal:
                for autre in range(1, 17):
                    self._fixe((ident, autre), 1 if autre == canal else 0, t)
            elif ordre == 6:
                self._fixe(cle, 1, t, tempo)
            else:                                   # Momentary, ordre inconnu : plus suivi
                self.attendus.pop(cle, None)

    def _applique(self, cmd, t):
        """Commande accusee -> etat attendu."""
        e = self.carte.get(cmd[0])
        if e is None or len(cmd) != 8:
            return
        fc, reg = cmd[1], cmd[2] << 8 | cmd[3]
        if e["driver"] == "conn16" and fc == 6 and reg <= 16:
            self._applique_conn16(cmd[0], reg, cmd[4], cmd[5], t)
        elif e["driver"] == "esp32" and fc == 6 and cmd[4] in (1, 2):
            self._fixe((cmd[0], reg), 1 if cmd[4] == 2 else 0, t, cmd[5])
        elif e["driver"] == "esp32" and fc == 5:
            self._fixe((cmd[0], reg), 1 if cmd[4] == 0xFF else 0, t)

    # ------------------------------------------------------------------ releves
    def _nom(self, e, reg):
        a = e["appareils"].get(reg)
        if e["driver"] == "conn16":
            return f"carte relais, canal {reg}" + (f" '{a['nom']}'" if a else "")
        return (f"'{a['nom']}'" if a else f"registre {reg}") + f" sur {e['nom']} (Power{reg - 223 if reg < 256 else reg - 255})"

    def _sens(self, e, reg, etat):
        """Etat brut releve -> libelle, avec l'etat du relai cote maitre (Relais_i : logique inverse)."""
        a = e["appareils"].get(reg)
        inverse = (a["type"] == 256) if a else False
        if e["driver"] == "conn16":
            return f"{'open' if etat else 'close'} (relai {'ON' if etat == inverse else 'OFF'})" if a else ("open" if etat else "close")
        return f"Power {'ON' if etat else 'OFF'}" + (f" (etat maitre {'ON' if etat != inverse else 'OFF'})" if inverse else "")

    def _compare(self, ident, reg, releve, t, alertes):
        e, cle = self.carte[ident], (ident, reg)
        attendu = self._attendu(cle, t)
        if attendu is None:
            return
        if attendu != releve and cle not in self.signales:
            self.signales.add(cle)
            alertes.append({"type": "ecart", "niveau": "alerte",
                            "texte": f"ECART {self._nom(e, reg)} : commande {self._sens(e, reg, attendu)}, releve {self._sens(e, reg, releve)}"})
        elif attendu == releve and cle in self.signales:
            self.signales.discard(cle)
            alertes.append({"type": "ecart", "niveau": "info",
                            "texte": f"Retour conforme : {self._nom(e, reg)} = {self._sens(e, reg, releve)}"})

    def _releve(self, trame, requete, t, alertes):
        e = self.carte.get(trame[0])
        if e is None or requete is None or len(requete) < 8:
            return
        fc, depart = trame[1], requete[2] << 8 | requete[3]
        if e["driver"] == "conn16" and fc == 3 and depart <= 16:
            for k in range(trame[2] // 2):
                self._compare(trame[0], depart + k, 1 if (trame[3 + 2 * k] << 8 | trame[4 + 2 * k]) else 0, t, alertes)
        elif e["driver"] == "esp32" and fc == 1 and trame[2] >= 1:
            self._compare(trame[0], depart, trame[3] & 1, t, alertes)

    # ------------------------------------------------------------------ point d'entree
    def observe(self, trame, nature, source, t):
        """Une trame vue (source bus|pc|emul) a l'instant t -> liste d'alertes."""
        alertes = []
        if nature == "ko":
            self.ko = [x for x in self.ko if t - x < FENETRE_KO] + [t]
            if len(self.ko) >= 2 and t - self.t_alerte_ko > FENETRE_KO:
                self.t_alerte_ko = t
                alertes.append({"type": "collision", "niveau": "alerte",
                                "texte": f"{len(self.ko)} trames au CRC faux en moins de {FENETRE_KO:.0f} s : collision "
                                         "(deux emetteurs), parasite, debit ou A/B inverses"})
            return alertes
        c = self.en_cours
        if nature == "requete":
            if (c and not c["repondue"] and t - c["t"] < self.delai and c["trame"][0] != 0
                    and not (c["source"] == "pc" and source == "pc")):
                alertes.append({"type": "collision", "niveau": "alerte",
                                "texte": f"requete {source.upper()} emise {round((t - c['t']) * 1000)} ms apres une requete "
                                         f"{c['source'].upper()} encore sans reponse : deux maitres sur le bus ?"})
            self.en_cours = {"trame": bytes(trame), "t": t, "source": source, "repondue": False}
        elif nature in ("reponse", "exception"):
            if c is None or c["repondue"]:
                alertes.append({"type": "collision", "niveau": "alerte",
                                "texte": f"reponse de l'id {trame[0]} sans requete en attente : esclave qui parle seul, "
                                         "ou requete non vue (CRC faux, debut d'ecoute)"})
            elif c["trame"][0] not in (trame[0], 0xFF):
                alertes.append({"type": "collision", "niveau": "alerte",
                                "texte": f"reponse de l'id {trame[0]} alors que l'id {c['trame'][0]} etait interroge"})
            else:
                c["repondue"] = True
                if nature == "reponse" and trame[1] in (5, 6) and trame == c["trame"]:
                    self._applique(c["trame"], t)
                elif nature == "reponse":
                    self._releve(trame, c["trame"], t, alertes)
        return alertes
