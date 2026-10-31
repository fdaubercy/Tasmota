"""Decodage des transactions I2C du sniffeur (sniffeur_i2c.py) : puce visee, registre, valeur traduite.

Deux puces peuvent partager une adresse (MCP23017 et TCA9554 en 0x20, DS3231 et MPU6050 en 0x68) : la
carte observee, choisie dans la page, leve l'ambiguite. Ses puces sont lues dans son _persist.json :
blocs de puce (cle = nom de la puce, « activation » ON, « adresseI2C »), cles « virtuel »: « I2C_<PUCE> »,
bloc « inclinaison » (MPU6050 d'un volet). Sans carte, ou si l'adresse n'y est pas declaree, toutes les
puces possibles sont proposees et la trame est marquee « ambigu » : jamais de nom devine.

Pointeur de registre : une ecriture commence par le registre vise ; une lecture repart du DERNIER pointeur
ecrit a cette adresse, meme dans une transaction precedente terminee par STOP (pilote ADS1115 de Tasmota).
"""

import glob
import json
import os

from decodeur_i2c_puces import PUCES

RACINE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def liste_cartes(racine=RACINE):
    """Chemins relatifs « data/<lieu>/<carte> » des cartes du depot (dossiers *sauvegarde* exclus)."""
    trouves = glob.glob(os.path.join(racine, "data", "*", "*", "_persist.json"))
    return sorted(os.path.relpath(os.path.dirname(f), racine).replace("\\", "/")
                  for f in trouves if "sauvegarde" not in f)


def _adresse(texte):
    try:
        return int(str(texte), 0)
    except ValueError:
        return None


def puces_carte(persist):
    """_persist.json (dict) -> {puce: [adresses]} des puces I2C declarees ACTIVES sur la carte."""
    puces = {}

    def ajoute(puce, adresse=None):
        adresses = puces.setdefault(puce, [])
        if adresse is not None and adresse not in adresses:
            adresses.append(adresse)

    def parcourt(noeud):
        if isinstance(noeud, dict):
            for cle, valeur in noeud.items():
                if cle in PUCES and isinstance(valeur, dict) and valeur.get("activation") == "ON":
                    ajoute(cle, _adresse(valeur.get("adresseI2C", "")))
                elif cle == "virtuel" and isinstance(valeur, str) and valeur[4:] in PUCES and valeur.startswith("I2C_"):
                    ajoute(valeur[4:])
                elif cle == "inclinaison" and isinstance(valeur, dict) and valeur.get("activation", "ON") != "OFF":
                    ajoute("MPU6050", _adresse(valeur.get("adresse", "0x68")))
                parcourt(valeur)
        elif isinstance(noeud, list):
            for valeur in noeud:
                parcourt(valeur)

    parcourt(persist)
    return {p: a or list(PUCES[p]["adresses"]) for p, a in puces.items()}


def charge_carte(racine, carte):
    """« data/<lieu>/<carte> » -> puces_carte ; ValueError si le chemin sort de data/ ou n'est pas une carte."""
    if carte not in liste_cartes(racine):
        raise ValueError(f"carte inconnue : {carte}")
    with open(os.path.join(racine, carte, "_persist.json"), encoding="utf-8") as f:
        return puces_carte(json.load(f))


def candidats(adresse, puces=None):
    """(puces possibles, ambigu). puces : resultat de puces_carte, ou None (aucune carte choisie)."""
    if puces is not None:
        retenues = [p for p, adresses in puces.items() if adresse in adresses]
        if len(retenues) == 1:
            return retenues, False
    toutes = [p for p, fiche in PUCES.items() if adresse in fiche["adresses"]]
    return toutes, len(toutes) != 1 or puces is not None   # non declaree sur la carte : a confirmer


class Decodeur:
    def __init__(self, puces=None):
        self.puces = puces              # None = aucune carte choisie
        self.memoire = {}               # adresse -> {ptr, pga, afs, gfs...}

    def decode(self, tr):
        """Transaction (sniffeur_i2c_protocole.lit_ligne, type X) -> {puce, ambigu, candidats, registre, texte}."""
        possibles, ambigu = candidats(tr["a"], self.puces)
        res = {"puce": possibles[0] if len(possibles) == 1 else "", "ambigu": ambigu,
               "candidats": possibles, "registre": "", "texte": ""}
        if tr["nack"] == 0:
            res["texte"] = "adresse non acquittee (rien ne repond)"
            return res
        if len(possibles) != 1:
            if possibles:
                res["texte"] = "puce ambigue : " + " ou ".join(possibles) + " (choisir la carte observee)"
            else:
                res["texte"] = "puce inconnue a cette adresse"
            return res
        fiche, mem = PUCES[possibles[0]], self.memoire.setdefault(tr["a"], {})
        d = tr["d"]
        if tr["rw"] == "W":
            if not d:
                res["texte"] = "sonde (adresse seule)"
                return res
            mem["ptr"], donnees, sens = d[0], d[1:], "ecrit"
        else:
            if "ptr" not in mem:
                res["texte"] = "lecture, registre inconnu (pointeur ecrit avant le debut de l'ecoute)"
                return res
            donnees, sens = d, "lu"
        ptr = mem["ptr"]
        res["registre"] = fiche["registres"].get(ptr, f"REG_0x{ptr:02X}")
        if not donnees:
            res["texte"] = f"pointeur -> {res['registre']}"
            return res
        res["texte"] = f"{sens} " + self._valeurs(fiche, ptr, donnees, mem)
        if fiche["auto_inc"]:
            mem["ptr"] = (ptr + len(donnees)) & 0xFF
        return res

    @staticmethod
    def _valeurs(fiche, ptr, d, mem):
        taille, morceaux = fiche["taille"], []
        resume = fiche.get("resume")
        texte_resume = resume(ptr, d, mem) if resume else None
        for i in range(0, len(d) - taille + 1, taille):
            reg = ptr + (i // taille if fiche["auto_inc"] else 0)
            v = int.from_bytes(d[i:i + taille], "big")
            valeur = fiche["valeur"](reg, v, mem) if "valeur" in fiche else f"0x{v:0{2 * taille}X}"
            morceaux.append(f"{fiche['registres'].get(reg, f'REG_0x{reg:02X}')}={valeur}")
            if not fiche["auto_inc"]:
                break                   # registre unique relu (TCA9554, ADS1115)
        if len(d) % taille:
            morceaux.append(f"(+{len(d) % taille} octet incomplet)")
        if texte_resume:
            return texte_resume + " [" + " ; ".join(morceaux) + "]"
        return " ; ".join(morceaux)
