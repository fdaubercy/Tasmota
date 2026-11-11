"""Banc de lieux (lieu et puce tires du nom d'env, table pour la page). Code de sortie 0 = vert."""

import os
import sys
from pathlib import Path

import build_envs as be
import lieux

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")


envs = be.liste_envs(RACINE)
codes = {c for c, _ in lieux.LIEUX}
cartes = [e.nom for e in envs if e.famille == "cartes"]
verifie(len(cartes) >= 11, True, "au moins les 11 cartes du 2026-11-10")      # le parc grandit (12 le 2026-11-11)
for n in cartes:
    verifie(lieux.lieu(n) in codes, True, f"lieu de {n} dans la table")
for n in [e.nom for e in envs if e.famille == "bases"]:
    verifie(lieux.lieu(n), None, f"base {n} sans lieu")
verifie(lieux.lieu("tasmota32s3-garage-capteurs-cuve-modbus"), "garage", "garage")
verifie(lieux.lieu("tasmota-pompe-piscine"), "exterieur", "exception piscine")
verifie(lieux.lieu("tasmota32s3-jardin-essai"), "jardin", "lieu hors table")
verifie(lieux.lieu("sanstiret"), None, "sans tiret")
verifie(lieux.puce("tasmota32-rdc-vr-porte"), "ESP32", "puce ESP32")
verifie(lieux.puce("tasmota32s3-etage2-grenier"), "ESP32-S3", "puce S3")
verifie(lieux.puce("tasmota32p4r3-base-devkit"), "ESP32-P4", "puce P4r3")
verifie(lieux.puce("tasmota32p4-garage-x"), "ESP32-P4", "puce P4")
verifie(lieux.puce("tasmota-pompe-piscine"), "ESP8266", "puce ESP8266")
verifie(lieux.puce("inconnu-a-b"), "inconnu", "puce inconnue")
verifie(lieux.pour_page()["lieux"][0], ["etage2", "2e étage"], "premier lieu")
verifie(len(lieux.pour_page()["lieux"]), 6, "6 lieux")
verifie("function remplitParLieu(" in lieux.JS, True, "JS fonction")
verifie("innerHTML" in lieux.JS, False, "JS sans innerHTML")

ids = lieux.identites(RACINE)
verifie([i["env"] for i in ids], cartes, "identites : les cartes, dans l'ordre")
verifie({"env": "tasmota32s3-garage-capteurs-cuve-modbus", "lieu": "garage", "hote": "CAPTEURS-CUVE", "topic": "jardin/cuve", "ip": ""} in ids,
        True, "identite de la cuve (esclave : ip vide)")
verifie(all(i["lieu"] in codes for i in ids), True, "identites : lieux dans la table")
verifie([i["hote"] for i in ids if i["env"] == "tasmota-pompe-piscine"], [""], "piscine sans hote")
verifie(lieux.pour_page_identites(RACINE)["lieux"][0], ["etage2", "2e étage"], "pour_page_identites : premier lieu")
verifie(lieux.pour_page_identites(RACINE)["cartes"], ids, "pour_page_identites : cartes")
for f in ("lieuDeHote(", "lieuDeTopic(", "lieuDemande(", "bandeauLieu("):
    verifie("function " + f in lieux.JS, True, "JS " + f)

print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
sys.exit(1 if ECHECS else 0)
