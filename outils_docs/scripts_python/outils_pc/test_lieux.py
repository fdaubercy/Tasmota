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

tous_ids = lieux.identites(RACINE)
ids = [i for i in tous_ids if not i.get("sauvegarde")]
verifie([i["env"] for i in ids], cartes, "identites : les cartes, dans l'ordre")
verifie({"env": "tasmota32s3-garage-capteurs-cuve-modbus", "lieu": "garage", "hote": "CAPTEURS-CUVE", "topic": "jardin/cuve", "ip": ""} in ids,
        True, "identite de la cuve (esclave : ip vide)")
verifie(all(i["lieu"] in codes for i in ids), True, "identites : lieux dans la table")
verifie([i["hote"] for i in ids if i["env"] == "tasmota-pompe-piscine"], [""], "piscine sans hote")
verifie(lieux.pour_page_identites(RACINE)["lieux"][0], ["etage2", "2e étage"], "pour_page_identites : premier lieu")
verifie(lieux.pour_page_identites(RACINE)["cartes"], tous_ids, "pour_page_identites : cartes")
# cave : l'ancien code publie sous cave/serveur-rly-cave (dossier *-sauvegarde, ancien format), le persist actif dit -v2
cave = [i for i in tous_ids if i["topic"] == "cave/serveur-rly-cave"]
verifie(len(cave), 1, "sauvegarde de la cave : une identite de topic cave/serveur-rly-cave")
verifie((cave[0]["lieu"], cave[0]["hote"], cave[0]["ip"], cave[0].get("sauvegarde")) if cave else None,
        ("cave", "SERVEUR-RLY-CAVE", "", True), "sauvegarde de la cave : lieu, hote, sans IP, marquee")
verifie(any(i["topic"] == "cave/serveur-rly-cave-v2" and not i.get("sauvegarde") for i in tous_ids), True, "topic voulu -v2 des cartes actives conserve")
verifie(cave[0]["env"] in cartes if cave else None, True, "sauvegarde de la cave : env de la carte active")
import annuaire_registre
nb = {c: n for c, _, n in annuaire_registre.en_json(RACINE)["lieux"]}
verifie(nb["cave"], sum(1 for i in ids if i["lieu"] == "cave"), "annuaire : cartes de la cave non doublees par la sauvegarde")
# hostname et topic non textuels : convertis en chaine (toLowerCase() cote JS ne doit jamais lever), persist d'essai temporaire
import json, tempfile
with tempfile.TemporaryDirectory() as tmp:
    faux = Path(tmp) / "_persist.json"
    faux.write_text(json.dumps({"serveur": {"hostname": 1234, "mqtt": {"topic": 56}}}), encoding="utf-8")
    vrai = be.persist_carte
    be.persist_carte = lambda racine, nom: faux
    try:
        faux_ids = lieux.identites(RACINE)
    finally:
        be.persist_carte = vrai
verifie(all(i["hote"] == "1234" and i["topic"] == "56" for i in faux_ids if not i.get("sauvegarde")) and bool(faux_ids), True, "identites : hostname et topic numeriques en chaine")
for f in ("lieuDeHote(", "lieuDeTopic(", "lieuDemande(", "bandeauLieu("):
    verifie("function " + f in lieux.JS, True, "JS " + f)

print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
sys.exit(1 if ECHECS else 0)
