"""Liste des cartes joignables par FTP (page « Navigateur FTP des cartes »). Aucune ecriture, aucun acces reseau.

Une carte est proposee si son env est de la famille « cartes », de puce ESP32, ESP32-S3 ou ESP32-P4, si la section de
son firmware dans tasmota/user_config_override.h ne retire pas USE_FTP, et si elle n'est pas esclave du Range Extender
(derriere le NAPT du maitre, son FTP n'est pas joignable). DOUTE = CARTE EXCLUE : persist illisible, condition du .h
qu'on ne sait pas evaluer autour de USE_FTP.

Les identifiants FTP (USER_FTP / PW_FTP) ne sortent que par `identifiants()`, appelee par la session FTP : `liste()`
n'en renvoie aucun. Spec : docs/superpowers/specs/2026-11-20-navigateur-ftp-cartes-design.md §8 et §9.
Banc : test_ftp_cartes_liste.py.
"""
import json
import re
from pathlib import Path

import build_envs
import lieux

PUCES_FTP = ("ESP32", "ESP32-S3", "ESP32-P4")
SUIVIS = ("USE_FTP", "USER_FTP", "PW_FTP")                 # macros dont on suit l'etat dans le .h
# Gardes de structure du .h : toujours vraies dans une compilation de firmware personnalise
STRUCTURE = ("USER_CONFIG_OVERRIDE_SECTION1", "USER_CONFIG_OVERRIDE_SECTION2", "USER_CONFIG_OVERRIDE_SECTION3",
             "USER_CONFIG_OVERRIDE_FIRMWARES_PERSONNALISES")
# -D FIRMWARE_* des bases et options amont (un env peut en porter plusieurs) : leur presence est inconnue ici
GENERIQUES = ("FIRMWARE_BLUETOOTH", "FIRMWARE_DISPLAYS", "FIRMWARE_IR", "FIRMWARE_KNX_NO_EMULATION", "FIRMWARE_LITE",
              "FIRMWARE_LVGL", "FIRMWARE_MINIMAL", "FIRMWARE_NSPANEL", "FIRMWARE_RANGE_EXTENDER", "FIRMWARE_SAFEBOOT",
              "FIRMWARE_SENSORS", "FIRMWARE_SERVEUR_RLY_CAVE", "FIRMWARE_TASMOTA", "FIRMWARE_TASMOTA32", "FIRMWARE_WEBCAM",
              "FIRMWARE_ZBBRDGPRO", "FIRMWARE_ZBBRIDGE")
JETONS = re.compile(r"defined\s*\(\s*\w+\s*\)|defined\s+\w+|&&|\|\||!|\(|\)|[^\s()!&|]+")
DIRECTIVE = re.compile(r"#\s*(ifdef|ifndef|if|elif|else|endif|define|undef)\b(.*)")


class _Doute(Exception):
    """Condition du .h qu'on ne sait pas lire."""


def _non(a):
    return None if a is None else not a


def _et(a, b):
    return False if a is False or b is False else (None if a is None or b is None else True)


def _ou(a, b):
    return True if a is True or b is True else (None if a is None or b is None else False)


def _defini(nom, firmware, suivi):
    """Tri-etat de defined(nom) : True, False ou None (inconnu)."""
    if nom in suivi:
        return suivi[nom]["etat"]
    if nom == firmware or nom in STRUCTURE:
        return True
    if nom == "_USER_CONFIG_OVERRIDE_H_" or (nom.startswith("FIRMWARE_") and nom not in GENERIQUES):
        return False        # firmware d'une autre carte
    return None


def _evalue(expr, firmware, suivi):
    """Tri-etat d'une condition `#if` (defined, !, &&, ||, parentheses) ; None si autre chose."""
    jetons = JETONS.findall(re.sub(r"//.*", "", expr))
    pos = [0]

    def suivant():
        return jetons[pos[0]] if pos[0] < len(jetons) else None

    def prend():
        pos[0] += 1
        return jetons[pos[0] - 1]

    def ou_():
        v = et_()
        while suivant() == "||":
            prend()
            v = _ou(v, et_())
        return v

    def et_():
        v = non_()
        while suivant() == "&&":
            prend()
            v = _et(v, non_())
        return v

    def non_():
        if suivant() == "!":
            prend()
            return _non(non_())
        return atome()

    def atome():
        j = suivant()
        if j is None:
            raise _Doute
        prend()
        if j == "(":
            v = ou_()
            if suivant() != ")":
                raise _Doute
            prend()
            return v
        m = re.fullmatch(r"defined\s*\(\s*(\w+)\s*\)|defined\s+(\w+)", j)
        if not m:
            raise _Doute
        return _defini(m.group(1) or m.group(2), firmware, suivi)

    try:
        v = ou_()
        return v if pos[0] == len(jetons) else None
    except _Doute:
        return None


def _parcourt(texte_h, firmware):
    """Etat final de USE_FTP, USER_FTP et PW_FTP pour le firmware : {nom: {"etat": True|False|None, "valeur": str}}.

    Parcours du .h comme le preprocesseur, en tri-etat : une branche dont la condition est inconnue est « peut-etre
    active », et un #define/#undef suivi qu'elle contient rend l'etat inconnu (None).
    """
    suivi = {n: {"etat": False, "valeur": ""} for n in SUIVIS}
    pile = []                     # [parent_actif, branche_deja_prise (tri-etat), actif]
    commentaire = False
    for brut in texte_h.splitlines():
        ligne = brut
        if commentaire:
            if "*/" not in ligne:
                continue
            ligne, commentaire = ligne.split("*/", 1)[1], False
        ligne = re.sub(r"/\*.*?\*/", " ", ligne)
        if "/*" in ligne:
            ligne, commentaire = ligne.split("/*", 1)[0], True
        m = DIRECTIVE.match(ligne.strip())
        if not m:
            continue
        mot, reste = m.group(1), m.group(2).strip()
        courant = pile[-1][2] if pile else True
        if mot in ("if", "ifdef", "ifndef"):
            if mot == "if":
                c = _evalue(reste, firmware, suivi)
            else:
                c = _defini(reste.split("//")[0].split()[0] if reste else "", firmware, suivi)
                c = _non(c) if mot == "ifndef" else c
            pile.append([courant, c, _et(courant, c)])
        elif mot in ("elif", "else"):
            if not pile:
                return None
            parent, pris, _ = pile[-1]
            c = True if mot == "else" else _evalue(reste, firmware, suivi)
            pile[-1] = [parent, _ou(pris, c), _et(parent, _et(_non(pris), c))]
        elif mot == "endif":
            if not pile:
                return None
            pile.pop()
        else:                     # define / undef
            nom = reste.split("//")[0].split()[0] if reste.split("//")[0].split() else ""
            if nom not in suivi or courant is False:
                continue
            valeur = re.match(r'"((?:[^"\\]|\\.)*)"', reste.split(None, 1)[1].strip()) if " " in reste.strip() else None
            if courant is None:
                suivi[nom]["etat"], suivi[nom]["valeur"] = None, ""
            elif mot == "define":
                suivi[nom]["etat"], suivi[nom]["valeur"] = True, valeur.group(1) if valeur else ""
            else:
                suivi[nom]["etat"], suivi[nom]["valeur"] = False, ""
    return None if pile or commentaire else suivi


def est_esclave_rgx(persist):
    """True si le persist declare la carte esclave d'un Range Extender (activation ON, id >= 1, ipMaitre), False sinon,
    None si le persist est absent ou illisible. Lecture `strict=False` : les persist du P4 et de la cuve ont un
    caractere de controle dans une chaine. NE PAS remplacer par build_envs.adresse_par_maitre (strict, et un persist
    illisible y donne « pas esclave », l'inverse de la regle voulue)."""
    try:
        d = json.loads(Path(persist).read_text(encoding="utf-8"), strict=False)
        bloc = (d.get("serveur") or (d.get("parametres") or {}).get("serveur") or {}).get("rangeExtender") or {}
        ident, maitre = int(bloc.get("id") or 0), str(bloc.get("ipMaitre") or "")
        return str(bloc.get("activation", "")).upper() == "ON" and ident >= 1 and bool(maitre)
    except (OSError, ValueError, AttributeError, TypeError):
        return None


def ftp_retire(texte_h, firmware):
    """True si le .h retire USE_FTP pour ce firmware, False s'il le garde, None s'il y a doute."""
    suivi = _parcourt(texte_h, firmware)
    if suivi is None or suivi["USE_FTP"]["etat"] is None:
        return None
    return not suivi["USE_FTP"]["etat"]


def _lit_h(racine):
    chemin = Path(racine) / "tasmota" / "user_config_override.h"
    try:
        return chemin.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def identifiants(racine, firmware):
    """(utilisateur, mot de passe) FTP du firmware : partie commune du .h, remplacee par la section de l'env si elle
    les redefinit. ("", "") si absents ou douteux. A n'utiliser que cote serveur : jamais renvoye a la page."""
    suivi = _parcourt(_lit_h(racine), firmware)
    if suivi is None:
        return "", ""
    return suivi["USER_FTP"]["valeur"], suivi["PW_FTP"]["valeur"]


def _hote(persist):
    """serveur.hostname du persist (strict=False), "" si illisible."""
    try:
        d = json.loads(Path(persist).read_text(encoding="utf-8"), strict=False)
        return str((d.get("serveur") or (d.get("parametres") or {}).get("serveur") or {}).get("hostname") or "")
    except (OSError, ValueError, AttributeError, TypeError):
        return ""


def liste(racine):
    """{"cartes": [{env, lieu, nom, hote, adresse, puce, firmware}], "exclues": [{env, raison}]}. Sans identifiants."""
    racine = Path(racine)
    texte_h = _lit_h(racine)
    cartes, exclues = [], []
    for e in build_envs.liste_envs(racine):
        if e.famille != "cartes":
            continue
        puce = lieux.puce(e.nom)
        persist = build_envs.persist_carte(racine, e.nom)
        esclave = est_esclave_rgx(persist) if persist else None
        retire = ftp_retire(texte_h, e.firmware)
        raison = ""
        if puce not in PUCES_FTP:
            raison = f"puce {puce} : pas de serveur FTP"
        elif persist is None:
            raison = "persist absent au depot : on ne sait pas si la carte est esclave"
        elif esclave is None:
            raison = "persist illisible : on ne sait pas si la carte est esclave"
        elif esclave:
            raison = "esclave du Range Extender : derriere le NAPT du maitre, FTP injoignable"
        elif retire is None:
            raison = "doute sur USE_FTP dans user_config_override.h"
        elif retire:
            raison = "USE_FTP retire par user_config_override.h"
        if raison:
            exclues.append({"env": e.nom, "raison": raison})
            continue
        hote = _hote(persist)
        adresse = e.ip if e.ip and e.ip_source == "h" else (f"{hote}.local" if hote else "")
        if not adresse:
            exclues.append({"env": e.nom, "raison": "ni IP au .h ni nom d'hote au persist"})
            continue
        cartes.append({"env": e.nom, "lieu": lieux.lieu(e.nom), "nom": e.nom, "hote": hote, "adresse": adresse,
                       "puce": puce, "firmware": e.firmware})
    return {"cartes": cartes, "exclues": exclues}
