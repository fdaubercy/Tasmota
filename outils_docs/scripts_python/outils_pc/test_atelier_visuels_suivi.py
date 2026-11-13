"""Banc de atelier_visuels_suivi : les quatre etats (identique, differente, absente, inconnue). Code de sortie 0 = vert.

    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_visuels_suivi.py
"""

import json
import sys
import tempfile
from pathlib import Path

import atelier_visuels_suivi as avs
import fichiers_berry_etat as fbe

ENV = "tasmota32s3-garage-capteurs-cuve-modbus"
DEPOT_JSON = {"version": 1, "fond": {"type": "svg", "largeur": 480, "hauteur": 360}, "elements": []}
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def leve(env, chemin):
    raise OSError("carte muette")


with tempfile.TemporaryDirectory(prefix="visuels_suivi_") as d:
    racine = Path(d)
    vus = []
    verifie(avs.etat(racine, ENV, lambda e, c: vus.append(c) or b"{}"), {"carte": "absente"}, "pas de visuel.json au depot : absente")
    verifie(vus, [], "absente : la carte n'est pas interrogee")
    dossier = racine / fbe.dossier_carte(ENV)
    dossier.mkdir(parents=True)
    (dossier / "visuel.json").write_text(json.dumps(DEPOT_JSON, indent=1), encoding="utf-8")
    verifie(avs.etat(racine, ENV, lambda e, c: json.dumps(DEPOT_JSON).encode()), {"carte": "identique"}, "meme contenu : identique")
    verifie(vus, [], "(lecteur precedent sans effet)")
    appels = []
    avs.etat(racine, ENV, lambda e, c: appels.append((e, c)) or b"{}")
    verifie(appels, [(ENV, "/json/visuel.json")], "le lecteur recoit l'env et /json/visuel.json")
    verifie(avs.etat(racine, ENV, lambda e, c: b'{"version": 2}'), {"carte": "differente"}, "contenu different : differente")
    verifie(avs.etat(racine, ENV, lambda e, c: None), {"carte": "differente"}, "fichier absent de la carte : differente")
    verifie(avs.etat(racine, ENV, lambda e, c: b"<html>404"), {"carte": "differente"}, "reponse illisible : differente")
    verifie(avs.etat(racine, ENV, leve), {"carte": "inconnue"}, "lecteur qui leve : inconnue")

print("BANC_VISUELS_SUIVI:", f"ECHEC {len(ECHECS)} : " + " ; ".join(ECHECS) if ECHECS else "OK")
sys.exit(1 if ECHECS else 0)
