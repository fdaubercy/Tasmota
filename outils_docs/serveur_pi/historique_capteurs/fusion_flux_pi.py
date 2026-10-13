#!/usr/bin/env python3
"""Fusionne l'onglet 'Historique capteurs' dans le fichier de flux Node-RED (Node-RED ARRETE).
Idempotent : refuse si l'onglet est deja present. Le broker du flux livre est remplace par le
broker existant (identifiants deja en place). Ecriture atomique (fichier temporaire + rename)."""
import json
import os
import sys

FLUX = "/home/pi/.node-red/flows_SERVEUR-BUREAU.json"
AJOUT = "/tmp/flow-historique-capteurs.json"
BROKER_EXISTANT = "af2f0082.9c6d9"

flux = json.load(open(FLUX, encoding="utf-8"))
ajout = json.load(open(AJOUT, encoding="utf-8"))
ids = {n["id"] for n in flux}

if "tab_hist" in ids:
    sys.exit("DEJA PRESENT : onglet tab_hist deja dans le fichier, rien n'est fait")
if not any(n["id"] == BROKER_EXISTANT and n["type"] == "mqtt-broker" for n in flux):
    sys.exit("ERREUR : broker " + BROKER_EXISTANT + " introuvable")

nouveaux = []
for n in ajout:
    if n["type"] == "mqtt-broker":
        continue                                   # on reutilise le broker existant
    if n.get("broker") == "broker_hist":
        n["broker"] = BROKER_EXISTANT
    if n["id"] in ids:
        sys.exit("ERREUR : collision d'identifiant " + n["id"])
    nouveaux.append(n)

flux.extend(nouveaux)
tmp = FLUX + ".tmp-historique"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(flux, f, ensure_ascii=False, indent=4)
os.replace(tmp, FLUX)
print("AJOUTES", len(nouveaux), "noeuds ; total", len(flux))
