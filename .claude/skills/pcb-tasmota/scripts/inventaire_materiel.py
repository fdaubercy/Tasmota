#!/usr/bin/env python3
"""Inventaire materiel d'une carte Tasmota a partir de son _persist.json.

Pour concevoir un PCB, il faut savoir QUOI est branche OU. Le persist le dit de
deux facons, qui doivent concorder :
  - `template.GPIO` : le gabarit Tasmota (un code par broche, rang = index de
    gabarit, PAS le numero de GPIO : sur S2/S3 les GPIO 22-32 sont sautes) ;
  - les blocs `environnement` des modules et drivers : chaque entree porte
    `pin` (numero de GPIO reel), `type` (code GPIO Tasmota) et `activation`.

L'environnement FAIT FOI : au demarrage, configModules.be (:131-146) reecrit
`template.GPIO` a partir de lui (code = type + id - 1 ; WS2812 : type + channel).
Le gabarit du depot peut donc etre perime ; un ecart est signale pour info.

Le script decode les codes (code = rang dans `UserSelectablePins` * 32 + index-1,
enum lue dans tasmota/include/tasmota_template.h ; code 1 = broche libre
"User") et signale : broche partagee par deux fonctions actives, ecart
gabarit/environnement, broche de strapping, broche PSRAM/flash.

ATTENTION : le persist decrit la CONFIGURATION logicielle, pas le cablage
physique. Une tension d'alimentation (`alimentation_V`), un composant `ON`,
un etat `POWER ON` ne prouvent rien sur ce qui est soude : toujours le faire
confirmer par l'utilisateur avant de dessiner (lecons du 2026-10-11).

Usage :
  python inventaire_materiel.py                      # tous les persists suivis
  python inventaire_materiel.py data/garage/tasmota32s3-capteurs-cuve-modbus
  python inventaire_materiel.py --json <persist|dossier>   # sortie machine
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
TEMPLATE_H = RACINE / "tasmota" / "include" / "tasmota_template.h"

# Broches a surveiller, par puce (fiches techniques Espressif).
STRAPPING = {"ESP32": {0, 2, 5, 12, 15}, "ESP32S3": {0, 3, 45, 46},
             "ESP32S2": {0, 45, 46}, "ESP32C3": {2, 8, 9}, "ESP32P4": {34, 35, 36, 37, 38}}
INTERDITES = {"ESP32": set(range(6, 12)), "ESP32S3": set(range(26, 33)),
              "ESP32S2": set(range(26, 33))}
PSRAM_OCTALE = {"ESP32S3": set(range(33, 38))}   # modules N8R8/N16R8 uniquement
ENTREE_SEULE = {"ESP32": {34, 35, 36, 37, 38, 39}}


def noms_gpio():
    """Liste des noms de l'enum UserSelectablePins, dans l'ordre."""
    src = TEMPLATE_H.read_text(encoding="utf-8", errors="replace")
    bloc = re.search(r"enum UserSelectablePins\s*\{(.*?)\};", src, re.S).group(1)
    bloc = re.sub(r"//[^\n]*", "", bloc)
    bloc = re.sub(r"/\*.*?\*/", "", bloc, flags=re.S)
    # Les seules directives de l'enum sont des `#ifdef ESP32` : on garde leur
    # contenu (toutes nos cartes sont des ESP32) et on retire les directives.
    bloc = "\n".join(l for l in bloc.splitlines() if not l.strip().startswith("#"))
    return [n.strip() for n in bloc.split(",") if n.strip()]


NOMS = noms_gpio()


def decode(code):
    """Code GPIO Tasmota -> 'GPIO_NOM' ou 'GPIO_NOM<n>'."""
    if not isinstance(code, int) or code <= 1:      # 0 = aucun, 1 = "User" (libre)
        return None
    rang, index = code >> 5, (code & 31) + 1
    nom = NOMS[rang] if rang < len(NOMS) else f"INCONNU_{rang}"
    return nom if index == 1 else f"{nom} #{index}"


def index_vers_gpio(puce, i):
    """Rang dans template.GPIO -> numero de GPIO physique."""
    if puce in ("ESP32S3", "ESP32S2"):
        return i if i < 22 else i + 11
    if puce == "ESP32":
        table = list(range(0, 6)) + [9, 10] + list(range(12, 28)) + [6, 7, 8, 11] + list(range(32, 40))
        return table[i] if i < len(table) else None
    return i            # P4, C3, C6 : identite


def parcours_environnements(o, chemin=()):
    """Toutes les entrees {pin, type} sous un bloc 'environnement'."""
    if isinstance(o, dict):
        if "pin" in o and "type" in o and not isinstance(o["pin"], (dict, list)):
            yield chemin, o
        for k, v in o.items():
            yield from parcours_environnements(v, chemin + (k,))


def peripheriques_i2c(d):
    """Composants I2C declares (adresse, driver, activation, champs utiles)."""
    env = d.get("drivers", {}).get("I2C", {}).get("environnement", {})
    for nom, bloc in env.items():
        if isinstance(bloc, dict) and "adresseI2C" in bloc:
            extra = {k: bloc[k] for k in ("alimentation_V", "voies") if k in bloc}
            yield nom, bloc.get("adresseI2C"), bloc.get("activation"), extra


def analyse(persist):
    d = json.loads(Path(persist).read_text(encoding="utf-8", errors="replace"))
    puce = d.get("diverses", {}).get("typeESP", "?")
    tpl = d.get("template", {})
    res = {"persist": str(persist), "puce": puce, "gabarit": tpl.get("NAME"),
           "broches": {}, "i2c": [], "modbus": None, "alertes": []}

    for i, code in enumerate(tpl.get("GPIO", [])):
        nom = decode(code)
        if nom:
            g = index_vers_gpio(puce, i)
            res["broches"].setdefault(g, {"gabarit": nom, "usages": []})

    for chemin, e in parcours_environnements(d):
        pin = e.get("pin")
        if not isinstance(pin, int) or pin < 0:
            continue
        actif = e.get("activation", "ON") == "ON" and _parents_actifs(d, chemin)
        virtuel = e.get("virtuel", "OFF") not in ("OFF", "", None)
        t = e.get("type")
        if isinstance(t, int):      # meme calcul que configModules.be::configDevicesByJon
            t = t + e.get("channel", 0) if t == 1376 else t + int(e.get("id", 1) or 1) - 1
        usage = {"ou": "/".join(chemin), "nom": e.get("nom") or e.get("name"),
                 "fonction": decode(t), "actif": actif, "virtuel": virtuel}
        res["broches"].setdefault(pin, {"gabarit": None, "usages": []})["usages"].append(usage)

    res["i2c"] = [{"composant": n, "adresse": a, "activation": act, **x}
                  for n, a, act, x in peripheriques_i2c(d)]
    mb = d.get("drivers", {}).get("ModBus")
    if mb:
        res["modbus"] = {k: mb.get(k) for k in ("activation", "id", "debit", "mode", "typeComm")}
    _alertes(res, puce)
    return res


def _parents_actifs(d, chemin):
    """Un bloc parent a activation OFF desactive tout ce qu'il contient."""
    o = d
    for k in chemin:
        if isinstance(o, dict) and o.get("activation") == "OFF":
            return False
        o = o.get(k, {}) if isinstance(o, dict) else {}
    return True


def _alertes(res, puce):
    for g, b in sorted(res["broches"].items(), key=lambda x: (x[0] is None, x[0])):
        actifs = [u for u in b["usages"] if u["actif"] and not u["virtuel"]]
        fonctions = {u["fonction"] for u in actifs}
        if len(fonctions) > 1:
            res["alertes"].append(f"GPIO{g} partage par {len(fonctions)} fonctions actives : "
                                  + ", ".join(f"{u['fonction']} ({u['ou']})" for u in actifs))
        if actifs and b["gabarit"] not in fonctions:
            res["alertes"].append(f"(info) GPIO{g} : gabarit du depot {b['gabarit'] or 'libre'} "
                                  f"!= environnement {sorted(fonctions)} (reecrit au boot)")
        if not actifs:
            continue
        if g in STRAPPING.get(puce, ()):
            res["alertes"].append(f"GPIO{g} est une broche de STRAPPING ({puce}) : niveau impose au boot")
        if g in INTERDITES.get(puce, ()):
            res["alertes"].append(f"GPIO{g} est reservee a la FLASH ({puce}) : inutilisable")
        if g in PSRAM_OCTALE.get(puce, ()):
            res["alertes"].append(f"GPIO{g} : prise par la PSRAM octale sur les modules N8R8/N16R8")
        if g in ENTREE_SEULE.get(puce, ()) and any(f and "RX" not in f for f in fonctions):
            res["alertes"].append(f"GPIO{g} : entree seule sur ESP32 (pas de sortie possible)")


def affiche(res):
    print(f"## {res['gabarit'] or '?'}  ({res['puce']})\n`{res['persist']}`\n")
    print("| GPIO | Gabarit | Fonction(s) environnement | Etat |")
    print("|---:|---|---|---|")
    for g, b in sorted(res["broches"].items(), key=lambda x: (x[0] is None, x[0])):
        us = [u for u in b["usages"] if u["actif"]]
        if not us and not b["gabarit"]:
            continue
        txt = "<br>".join(f"{u['fonction']} - {u['nom']} ({u['ou']})" for u in us) or "-"
        etat = ("virtuel" if all(u["virtuel"] for u in us) else "actif") if us else "gabarit seul"
        print(f"| {g} | {b['gabarit'] or '-'} | {txt} | {etat} |")
    if res["i2c"]:
        print("\n**I2C** : " + "; ".join(
            f"{c['composant']} @{c['adresse']} {c['activation']}"
            + (f" (alimentation_V={c['alimentation_V']} : A CONFIRMER)" if "alimentation_V" in c else "")
            for c in res["i2c"]))
    if res["modbus"]:
        print(f"\n**ModBus** : {res['modbus']}")
    if res["alertes"]:
        print("\n**Alertes**\n" + "\n".join(f"- {a}" for a in res["alertes"]))
    print()


def persists(cible):
    if cible:
        p = Path(cible)
        return [p / "_persist.json" if p.is_dir() else p]
    sortie = subprocess.run(["git", "ls-files", "*_persist.json"], cwd=RACINE,
                            capture_output=True, text=True).stdout.split()
    return [RACINE / s for s in sortie if "sauvegarde" not in s]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cible", nargs="?", help="_persist.json ou dossier de carte (defaut : tous)")
    ap.add_argument("--json", action="store_true", help="sortie JSON")
    a = ap.parse_args()
    resultats = [analyse(p) for p in persists(a.cible)]
    if a.json:
        json.dump(resultats, sys.stdout, ensure_ascii=False, indent=1, default=str)
    else:
        for r in resultats:
            affiche(r)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
