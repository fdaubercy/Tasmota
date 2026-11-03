"""Lance par le Python de decode-config (decode_config.disposition) : groupes et textes de la derniere disposition connue.

  groupes  {cle: groupe} : chaque parametre porte son groupe (Wifi, Mqtt, Timer, Management...) ; une cle a sous-cles
           (flag, flag2...) prend le groupe le plus frequent de ses sous-cles ;
  textes   {cle: [indice, nombre]} : textes de la reserve (Settings->text_pool), indice ESP32 de SettingsTextIndex,
           nombre d'elements (null pour un texte seul). Seuls les textes sans conversion (ou mot de passe) y sont ;
  noms     SettingsTextIndex ESP32 connu du paquet (le banc le compare a tasmota.h) ;
  commandes {cle: [commande...]} : commandes Tasmota qui reposent le parametre (SO56 -> SETOPTION56, Timer{} -> TIMER),
           sous-cles comprises (flag3 : les SetOption de ses 30 drapeaux).
"""

import collections
import importlib.util
import json
import re
import sys

COMMANDE = re.compile(r'"([A-Z][A-Za-z_]*?)(\d*)(?=\{|[ ",])')    # majuscule : pas @["timer"]


def groupe(definition):
    """Groupe d'une definition (hardware?, format, adresse, (tableau, masque, (groupe, commande)), conversion)."""
    if isinstance(definition, dict):
        compte = collections.Counter(g for d in definition.values() if (g := groupe(d)))
        return compte.most_common(1)[0][0] if compte else None
    if isinstance(definition, tuple):
        for element in definition:
            if isinstance(element, tuple) and len(element) == 3 and isinstance(element[2], tuple) \
                    and element[2] and isinstance(element[2][0], str):
                return element[2][0]
        for element in definition:
            if isinstance(element, (tuple, dict)) and (g := groupe(element)):
                return g
    return None


def texte(definition, indices, materiels):
    """[indice, nombre] d'un texte de la reserve ecrit tel quel, None sinon."""
    if not (isinstance(definition, tuple) and len(definition) >= 4 and definition[0] in materiels
            and definition[1] == "699s" and isinstance(definition[2], tuple) and definition[2][0] == 0x017):
        return None
    conversion = definition[4] if len(definition) > 4 else None
    if conversion is not None and [getattr(f, "__name__", "") for f in conversion] != ["passwordread", "passwordwrite"]:
        return None
    nom, tableau = definition[2][1], definition[3][0]
    if nom not in indices:
        return None
    return [indices.index(nom), tableau[0] if tableau else None]


def commandes(definition):
    """Commandes Tasmota d'une definition, normalisees comme build_sauvegarde.commande (sous-cles comprises)."""
    noms = set()
    if isinstance(definition, dict):
        for d in definition.values():
            noms |= commandes(d)
    elif isinstance(definition, tuple):
        for element in definition:
            if isinstance(element, tuple) and len(element) == 3 and isinstance(element[2], tuple) \
                    and len(element[2]) == 2 and isinstance(element[2][1], str):
                s = element[2][1]
                # 1er mot de la chaine ("SO56 {}", list("WebSensor{}...")), sinon une liste ["EthIPAddress",...],
                # sinon tous ("{cmnd}" de toffset) ;
                # pas les mots des arguments de .format("Token" if ... else "Password")
                tete = COMMANDE.match(s, len("list(") if s.startswith("list(") else 0)
                trouves = [tete.groups()] if tete else \
                    [m for liste in re.findall(r"\[[^\]]*\]", s) for m in COMMANDE.findall(liste)] or COMMANDE.findall(s)
                for nom, numero in trouves:
                    nom = "SETOPTION" if nom.upper() == "SO" else nom.upper()
                    noms.add(nom + numero if nom == "SETOPTION" else nom)
            elif isinstance(element, (tuple, dict)):
                noms |= commandes(element)
    return noms


spec = importlib.util.spec_from_file_location("decode_config", sys.argv[1])
assert spec and spec.loader
dc = importlib.util.module_from_spec(spec)
sys.argv = ["decode-config"]
spec.loader.exec_module(dc)
disposition = sorted(dc.SETTINGS, key=lambda s: s[0], reverse=True)[0][2]
indices = disposition[dc.SETTINGVAR][dc.HARDWARE.hstr(dc.HARDWARE.ESP32)]
materiels = (dc.HARDWARE.ESP, dc.HARDWARE.ESP32)
cles = [c for c in disposition if isinstance(c, str) and c != dc.SETTINGVAR]
print(json.dumps({"groupes": {c: groupe(disposition[c]) or "Divers" for c in cles},
                  "textes": {c: t for c in cles if (t := texte(disposition[c], indices, materiels))},
                  "noms": indices[:indices.index("SET_MAX")],
                  "commandes": {c: sorted(n) for c in cles if (n := commandes(disposition[c]))}}))
