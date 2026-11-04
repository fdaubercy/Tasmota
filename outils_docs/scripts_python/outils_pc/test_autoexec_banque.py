#!/usr/bin/env python3
"""Banc de la banque de commandes de l'onglet « autoexec.bat » (plan autoexec-bat, A4) : rendu d'une ligne depuis les
champs, validation, ajout d'une commande perso en transaction, contenu de la banque initiale (chaque commande connue
de A1, aucun secret). Temoins : des mutants du module (copie modifiee en dossier temporaire, banc relance avec
AUTOEXEC_MUTANT=<dossier>) doivent rendre le banc ROUGE. Aucune ecriture dans le vrai depot. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_banque.py
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if os.environ.get("AUTOEXEC_MUTANT"):
    sys.path.insert(0, os.environ["AUTOEXEC_MUTANT"])

import autoexec_analyse as aa
import autoexec_banque as ab
import autoexec_commandes as ac
from build_sauvegarde import commande
from test_build_sauvegarde import ECHECS, leve, verifie

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
TIMER = 'Timer12 {"Enable":1,"Mode":0,"Time":"22:30","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}'
PERSO = {"nom": "Ma minuterie", "categorie": "Perso", "description": "essai", "modele": "Timer{n} {etat}",
         "champs": [{"cle": "n", "type": "nombre", "libelle": "Numero", "defaut": 1, "min": 1, "max": 16},
                    {"cle": "etat", "type": "texte", "libelle": "Reglage", "defaut": ""}],
         "origine": "perso", "ajoutee": "2026-01-01"}


def copie_racine(tmp):
    cible = Path(tmp) / "depot"
    (cible / ab.FICHIER).parent.mkdir(parents=True)
    shutil.copy(RACINE / ab.FICHIER, cible / ab.FICHIER)
    return cible


def banc():
    banque = ab.charge(RACINE)
    par_nom = {e["nom"]: e for e in banque}
    timer = next(e for e in banque if e["modele"].startswith("Timer{n}"))

    # --- rendu
    verifie(ab.rend(timer, {"n": 12, "heure": "22:30", "jours": "1111111", "relais": 1, "action": 0}), TIMER, "rend Timer")
    verifie(ab.rend(timer, {"n": "12", "heure": "22:30", "jours": "1111111", "relais": "1", "action": "0"}), TIMER,
            "rend Timer, valeurs en texte (formulaire)")
    verifie(json.loads(ab.rend(timer, {}).split(" ", 1)[1])["Enable"], 1, "rend Timer par defauts : JSON valide")
    for cle, val, lib in [("heure", "25:00", "heure 25:00"), ("heure", "22:60", "heure 22:60"), ("heure", "9:30", "heure 9:30"),
                          ("jours", "111111", "jours : 6 caracteres"), ("jours", "11111a1", "jours : lettre"),
                          ("relais", 0, "relais 0"), ("relais", "x", "relais texte"), ("n", 99, "nombre au-dessus du max"),
                          ("n", 0, "nombre sous le min"), ("action", 9, "action hors des choix")]:
        leve(lambda: ab.rend(timer, {cle: val}), ValueError, f"refus : {lib}")
    leve(lambda: ab.rend(PERSO, {"etat": "a\nb"}), ValueError, "refus : saut de ligne dans un texte")
    verifie(ab.rend(PERSO, {"n": 3, "etat": "ON"}), "Timer3 ON", "rend perso : nombre et texte")
    verifie(ab.rend(par_nom["Latitude"], {"valeur": "50.5"}), "Latitude 50.5", "rend nombre decimal")
    leve(lambda: ab.rend(par_nom["Latitude"], {"valeur": 95}), ValueError, "refus : latitude 95")
    leve(lambda: ab.rend(PERSO, {"n": True}), ValueError, "refus : booleen pour un nombre")
    sans_defaut = copy.deepcopy(PERSO)
    sans_defaut["champs"][0].pop("defaut")
    leve(lambda: ab.rend(sans_defaut, {"etat": "x"}), ValueError, "refus : champ sans valeur ni defaut")

    # --- validation
    verifie(ab.valide_entree(copy.deepcopy(PERSO))["nom"], "Ma minuterie", "valide_entree : entree correcte")
    leve(lambda: ab.valide_entree(dict(PERSO, modele="Power 1", champs=[])), ValueError, "refus : entree perso sans champ")
    leve(lambda: ab.valide_entree(dict(PERSO, modele="Timer{n} {inconnu}")), ValueError, "refus : champ du modele inconnu")
    leve(lambda: ab.valide_entree(dict(PERSO, modele="Timer{n}")), ValueError, "refus : champ jamais utilise")
    leve(lambda: ab.valide_entree(dict(PERSO, modele="Timer{n} {etat}\nPower 1")), ValueError, "refus : modele sur 2 lignes")
    leve(lambda: ab.valide_entree(dict(PERSO, origine="autre")), ValueError, "refus : origine inconnue")
    leve(lambda: ab.valide_entree(dict(PERSO, ajoutee="demain")), ValueError, "refus : date invalide")
    leve(lambda: ab.valide_entree(dict(PERSO, nom="")), ValueError, "refus : nom vide")
    leve(lambda: ab.valide_entree(dict(PERSO, bidon=1)), ValueError, "refus : cle inconnue")
    mauvais = copy.deepcopy(PERSO)
    mauvais["champs"][0]["type"] = "couleur"
    leve(lambda: ab.valide_entree(mauvais), ValueError, "refus : type de champ inconnu")
    mauvais = copy.deepcopy(PERSO)
    mauvais["champs"][0]["defaut"] = 99
    leve(lambda: ab.valide_entree(mauvais), ValueError, "refus : defaut hors bornes")
    mauvais = copy.deepcopy(timer)
    mauvais["champs"][4]["defaut"] = 7
    leve(lambda: ab.valide_entree(mauvais), ValueError, "refus : defaut hors des choix")
    secret = dict(PERSO, nom="Mot de passe", modele="MqttPassword {mdp}",
                  champs=[{"cle": "mdp", "type": "texte", "libelle": "Mot de passe", "defaut": "abc"}])
    leve(lambda: ab.valide_entree(secret), ValueError, "refus : valeur par defaut secrete")
    secret["champs"][0]["defaut"] = ""
    verifie(ab.valide_entree(secret)["champs"][0]["defaut"], "", "secret SANS defaut : accepte")

    # --- banque initiale
    connues = ac.charge(RACINE)["connues"]
    noms = [e["nom"].casefold() for e in banque]
    verifie(len(noms), len(set(noms)), "banque : noms uniques")
    for e in banque:
        mot = e["modele"].split()[0]
        c = commande(mot.replace("{n}", "1"))
        verifie(c in connues, True, f"banque : {e['nom']} -> {c} connue de A1")
        verifie(e["origine"], "proposee", f"banque : {e['nom']} proposee")
        if aa.SECRETS.search(mot):
            verifie(all(not ch.get("defaut") for ch in e["champs"]), True, f"banque : {e['nom']} sans defaut secret")
        try:
            ligne = ab.rend(e, {})
            json.loads(ligne.split(" ", 1)[1]) if '{"' in e["modele"] else None
            verifie(True, True, f"banque : {e['nom']} rend par defauts")
        except Exception as erreur:
            verifie(str(erreur), "", f"banque : {e['nom']} rend par defauts")
    modeles = [e["modele"].split()[0].replace("{n}", "") for e in banque]
    for attendu in ["Timer", "Timers", "AdcParam", "WebSensor", "Latitude", "Longitude", "PowerOnState", "Timezone",
                    "TimeStd", "TimeDst", "SerialLog", "WebLog", "MqttLog", "SysLog", "LedState", "LedPower"]:
        verifie(attendu in modeles, True, f"banque : {attendu} presente")
    for so in (1, 31, 55, 56, 57, 141, 146):
        verifie(f"SetOption{so}" in modeles, True, f"banque : SetOption{so} presente")
    verifie(any(aa.SECRETS.search(e["modele"]) for e in banque), False, "banque : aucun modele a secret")

    # --- ajout
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(tmp) / "donnees")
        depot = copie_racine(tmp)
        avant = (depot / ab.FICHIER).read_bytes()
        leve(lambda: ab.ajoute(depot, copy.deepcopy(PERSO), lambda: None), RuntimeError, "refus : build indetectable")
        leve(lambda: ab.ajoute(depot, copy.deepcopy(PERSO), lambda: ["pio"]), RuntimeError, "refus : build en cours")
        verifie((depot / ab.FICHIER).read_bytes() == avant, True, "refus : rien d'ecrit")
        ajoutee = ab.ajoute(depot, dict(copy.deepcopy(PERSO), origine="proposee", ajoutee="2000-01-01"), lambda: [])
        verifie(ajoutee["origine"], "perso", "ajoute : origine forcee a perso")
        verifie(ajoutee["ajoutee"] == "2000-01-01", False, "ajoute : date du jour, pas celle recue")
        relu = ab.charge(depot)
        verifie(relu[-1], ajoutee, "ajoute : relu par charge")
        verifie(len(relu), len(banque) + 1, "ajoute : une entree de plus")
        brut = (depot / ab.FICHIER).read_bytes()
        verifie(brut.startswith(b"\xef\xbb\xbf") or b"\r\n" in brut, False, "ajoute : UTF-8 sans BOM, LF")
        leve(lambda: ab.ajoute(depot, copy.deepcopy(PERSO), lambda: []), ValueError, "refus : nom deja dans la banque")
        leve(lambda: ab.ajoute(depot, dict(copy.deepcopy(PERSO), nom="ma MINUTERIE"), lambda: []), ValueError,
             "refus : nom deja pris, casse differente")
        leve(lambda: ab.ajoute(depot, dict(copy.deepcopy(PERSO), nom=banque[0]["nom"]), lambda: []), ValueError,
             "refus : nom d'une entree proposee")
        leve(lambda: ab.ajoute(depot, dict(copy.deepcopy(PERSO), nom="Autre", champs=[]), lambda: []), ValueError,
             "refus : ajout sans champ")
        verifie(len(ab.charge(depot)), len(banque) + 1, "refus : banque inchangee")
        (depot / ab.FICHIER).write_text("{ pas du json", encoding="utf-8")
        try:
            ab.charge(depot)
            verifie("aucune exception", "ValueError", "charge : fichier invalide")
        except ValueError as erreur:
            verifie("banque_autoexec.json" in str(erreur), True, "charge : fichier invalide, l'erreur cite le fichier")
        (depot / ab.FICHIER).write_text(json.dumps({"entrees": [PERSO, PERSO]}), encoding="utf-8")
        leve(lambda: ab.charge(depot), ValueError, "charge : nom en double dans le fichier")


MUTANTS = [
    ("validation de l'heure retiree", "HEURE.fullmatch(texte)", "True"),
    ("minutes de l'heure non verifiees", "[0-5]\\d", "\\d\\d"),
    ("doublon de nom accepte", "if nom in {e[\"nom\"].casefold() for e in existantes}:", "if False:"),
    ("doublon insensible a la casse perdu", "nom = entree[\"nom\"].casefold()", "nom = entree[\"nom\"]"),
    ("defaut secret accepte", "if aa.SECRETS.search(e[\"modele\"]) and any", "if False and any"),
    ("build indetectable ignore", "if builds is None:", "if False:"),
    ("build en cours ignore", "    if builds:", "    if False:"),
    ("origine non forcee", 'dict(entree, origine="perso"', "dict(entree"),
    ("jours non verifies", "JOURS.fullmatch(texte)", "True"),
    ("bornes du nombre ignorees", "if not (haut is None or n <= haut) or not (bas is None or n >= bas):", "if False:"),
    ("entree sans champ acceptee", "or not champs:", ":"),
    ("saut de ligne dans un texte accepte", '"\\n" in texte or "\\r" in texte', "False"),
    ("choix non verifie", "if texte not in valeurs:", "if False:"),
]


def temoins():
    source = (ICI / "autoexec_banque.py").read_text(encoding="utf-8")
    for nom, ancien, nouveau in MUTANTS:
        verifie(ancien in source, True, f"mutant {nom} : motif present")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "autoexec_banque.py").write_text(source.replace(ancien, nouveau), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, AUTOEXEC_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(p.returncode != 0, True, f"temoin rouge : mutant {nom}")


if __name__ == "__main__":
    banc()
    if not os.environ.get("AUTOEXEC_MUTANT"):
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
