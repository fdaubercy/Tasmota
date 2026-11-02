#!/usr/bin/env python3
"""Banc de build_drvset.py sur la carte simulee (aucune vraie carte). Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_build_drvset.py
"""
import struct
import sys
import tempfile

import build_drvset as bd
from build_ota_carte_simulee import Carte

ECHECS = []
RAPIDE = {"delai_retour": 5.0, "attente_min": 0.0, "sondage": 0.05}
CHEMIN = "/" + bd.FICHIER


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def fichier(power=310, voltage=15963, current=124194):
    d = bytearray(536)
    for nom, v in (("PowerCal", power), ("VoltageCal", voltage), ("CurrentCal", current)):
        struct.pack_into("<I", d, bd.OFFSETS[nom], v)
    return bytes(d)


with tempfile.TemporaryDirectory() as t:
    carte = Carte()
    carte.flash[CHEMIN] = fichier()
    copie = bd.sauvegarde("env-essai", carte.ip, t)
    verifie(copie.read_bytes(), fichier(), "sauvegarde : copie identique")
    verifie(copie.parent.name, "drvset", "sauvegarde : dans le dossier drvset")

    del carte.flash[CHEMIN]                      # le flash serie a remplace le FS
    verifie(bd.sauvegarde("env-essai", carte.ip, t), None, "sauvegarde : carte sans le fichier -> None")
    verifie(bd.retablit(carte.ip, copie, **RAPIDE), bd.calibrage(fichier()), "retablit : calibrage relu")
    verifie(carte.flash.get(CHEMIN), fichier(), "retablit : fichier sur la carte")
    commandes = [r[1] for r in carte.journal if "Restart" in r[1]]
    verifie(any("Restart%2099" in c for c in commandes), True, "retablit : Restart 99, sans sauvegarde")
    verifie(any("Restart%201" in c and "Restart%2099" not in c for c in commandes), False, "retablit : jamais Restart 1")

    carte.flash.pop(CHEMIN)
    carte.restart_muet = True
    verifie(bd.retablit(carte.ip, copie, **RAPIDE), bd.calibrage(fichier()), "retablit : carte qui redemarre sans repondre")
    carte.restart_muet = False

    # La carte ecrase le fichier en redemarrant (fenetre SaveData) : la relecture doit le voir
    carte.flash.pop(CHEMIN)
    carte.apres_commande_restart = lambda: carte.flash.__setitem__(CHEMIN, fichier(596, 15187, 251213))
    try:
        bd.retablit(carte.ip, copie, **RAPIDE)
        erreur = ""
    except RuntimeError as e:
        erreur = str(e)
    verifie("relu différent" in erreur and str(copie) in erreur, True, "retablit : ecrasement detecte, copie indiquee")
    carte.ferme()

    verifie(bd.sauvegarde("env-essai", "127.0.0.1:9", t, delai=0.5), None, "sauvegarde : carte injoignable -> None")
    try:
        bd.retablit("127.0.0.1:9", copie, delai_retour=0.3, attente_min=0.0, sondage=0.05, delai_http=0.2)
        erreur = ""
    except RuntimeError as e:
        erreur = str(e)
    verifie(str(copie) in erreur, True, "retablit : carte injoignable -> erreur avec la copie")

print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
sys.exit(1 if ECHECS else 0)
