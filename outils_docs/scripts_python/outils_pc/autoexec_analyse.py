#!/usr/bin/env python3
"""Analyse d'un autoexec.bat : un avertissement par probleme, ligne par ligne (plan autoexec-bat, A2).

`lignes` decoupe le fichier (Backlog compris) ; `analyse` rend les avertissements affiches sous l'editeur de l'onglet
« autoexec.bat » de l'Assistant persist. Aucun acces fichier ni sous-processus dans `analyse` (appelee a chaque frappe) :
l'appelant passe le persist de la carte et le resultat de `autoexec_commandes.charge`.
  redemarrage  rouge (« toujours », boucle de redemarrage) ou orange (« si-change »)
  secret       rouge, mot de passe en clair, y compris dans une ligne en commentaire ; la valeur n'est jamais citee
  doublon      orange, la commande est deja reposee au demarrage par data/fs/configGlobal.be d'apres le persist
  inconnue     orange, avec la commande la plus proche (difflib)
  absente      orange, la commande n'est pas compilee pour la carte : toutes ses gardes sont fausses (A4) ; ou commande Berry
               dont AUCUN module declarant n'est charge par l'autoexec.be de la carte (autoexec_berry.py, memes couleur et type)
  longueur     orange, plus de 510 octets : le firmware tronque (xdrv_50_filesystem.ino::UfsExecuteCommandFileLoop)
Un commentaire n'est analyse que pour les secrets. Banc : test_autoexec_analyse.py.
"""

import difflib
import json
import re
from pathlib import Path

from build_sauvegarde import CONFIG_PERSIST, INDEXEES, _v, commande, commandes_posees

LIMITE = 510
SECRETS = re.compile(r"pwd|password|pwassword|token|secret|apikey|^key|precfgkey", re.I)   # noms de commandes
RACINE = Path(__file__).resolve().parents[3]
_CONFIG = []                         # texte de configGlobal.be, lu une fois (pas a chaque frappe)
BACKLOG = re.compile(r"backlog\d*", re.I)


def lignes(texte):
    """[{numero, brut, commentaire, commandes: [(nom ecrit, valeur)]}] ; un commentaire garde ses commandes (secrets)."""
    res = []
    for numero, brut in enumerate(texte.splitlines(), 1):
        corps = brut.strip()
        commentaire = corps.startswith(";")
        if commentaire:
            corps = corps.lstrip(";").strip()
        mots = corps.split(None, 1)
        parties = [corps]
        if mots and BACKLOG.fullmatch(mots[0]):
            parties = (mots[1] if len(mots) > 1 else "").split(";")
        cmds = []
        for partie in parties:
            m = re.split(r"[\s=]+", partie.strip(), maxsplit=1)     # Password1=x : = separe aussi (ExecuteCommand)
            if m and re.match(r"[A-Za-z]\w*$", m[0]):
                cmds.append((m[0], m[1].strip() if len(m) > 1 else ""))
        res.append({"numero": numero, "brut": brut, "commentaire": commentaire, "commandes": cmds})
    return res


def _texte_config():
    if not _CONFIG:
        _CONFIG.append((RACINE / CONFIG_PERSIST).read_text(encoding="utf-8"))
    return _CONFIG[0]


def _cle_persist(texte_config, ecrit):
    """Chemin « a.b.c » du persist que configGlobal.be lit pour cette commande, None si on ne sait pas le nommer."""
    lignes_cfg = texte_config.splitlines()
    for i, ligne in enumerate(lignes_cfg):
        m = re.search(r'testeParam\(\s*"(\w+)"', ligne)
        if not m or (m.group(1).lower() != ecrit.lower() and commande(m.group(1)) != commande(ecrit)):
            continue
        reste = ligne[m.end():]
        e = re.search(r'\bdata((?:\["\w+"\])*)(?:\.find\("(\w+)")?', reste)
        if not e:
            continue
        base = ""
        for avant in reversed(lignes_cfg[:i]):
            b = re.match(r'\s*data = (\w+)((?:\["\w+"\])*)', avant)
            if b:
                base = b.group(1) + b.group(2)
                break
        cles = re.findall(r'\w+', base) + re.findall(r'\w+', e.group(1)) + ([e.group(2)] if e.group(2) else [])
        return ".".join(cles) if base else None
    return None


def _sans_effet(redemarre, valeur):
    """Vrai si la source note « redemarre seulement si la valeur est N » et que la ligne pose une autre valeur."""
    m = re.search(r"seulement si la valeur est (\d+)", redemarre["source"])
    v = {"ON": "1", "OFF": "0", "TOGGLE": "2"}.get(valeur.split()[0].upper(), valeur.split()[0])
    return bool(m) and v.isdigit() and v != m.group(1)


def _raison(chemin):
    """Premiere condition fausse du chemin : `defined(X)` -> « X non defini », `!defined(X)` -> « X defini »."""
    cond = next(c for c, v in chemin if v is False).strip()
    m = re.fullmatch(r"(!?)\s*defined\s*\(?\s*(\w+)\s*\)?", cond)
    return cond if not m else f"{m.group(2)} {'defini' if m.group(1) else 'non defini'}"


def _casse(ecrit, cible):
    """Cible (MAJUSCULES) ecrite avec la casse de l'utilisateur : WebSesnor -> WebSensor, WEBSESNOR -> WEBSENSOR."""
    if ecrit.isupper():
        return cible
    res = []
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, ecrit.upper(), cible).get_opcodes():
        res.append(ecrit[a1:a2] if op == "equal" else cible[b1:b2].lower())
    return "".join(res)


def absente(ecrit, nom, commandes, gardes_env=None, berry_env=None):
    """(message, correction) si la commande n'existe pas sur la carte, sinon None. Firmware : toutes les gardes fausses ;
    Berry : aucun module declarant charge (une commande Berry de meme nom qu'une commande C existe toujours : ignoree)."""
    chemins = gardes_env and (gardes_env(nom) or gardes_env(ecrit.upper()))
    if chemins and all(any(v is False for _, v in ch) for ch in chemins):
        return (f"{ecrit} n'est pas compilee pour cette carte ({_raison(chemins[0])}).",
                "Retirer la ligne, ou compiler la carte avec cette option (user_config_override.h).")
    modules = berry_env and (berry_env.get(nom) or berry_env.get(ecrit.upper()))
    source = commandes["connues"].get(nom) if isinstance(commandes["connues"], dict) else None
    if modules and not str(source or "").startswith("tasmota/"):
        return (f"{ecrit} est une commande Berry du module {', '.join(modules)}, que l'autoexec.be de cette carte ne charge pas.",
                "Retirer la ligne, ou charger le module dans l'autoexec.be de la carte.")
    return None


def analyse(texte, persist, commandes, banque_noms=(), texte_config=None, gardes_env=None, berry_env=None):
    """Avertissements du fichier : [{ligne, type, niveau, message, correction, commande}], dans l'ordre des lignes
    (commande : nom a enlever par le bouton de la page, doublon, redemarrage et absente ; sinon None).
    gardes_env : `nom -> [chemin, ...]` d'autoexec_gardes.etat (chemin = [(condition, vrai|faux|None)]) ; None = pas
    d'alerte `absente`. Alerte seulement si TOUS les chemins ont une condition FAUSSE ; incertain (None) ne compte pas.
    berry_env : `NOM -> [modules]` d'autoexec_berry.non_chargees ; None = pas d'alerte Berry."""
    connues = set(commandes["connues"]) | set(banque_noms)
    redemarrent = commandes["redemarrent"]
    posees = None
    res = []

    def ajoute(l, type_, niveau, message, correction=None, cmd=None):
        res.append({"ligne": l["numero"], "type": type_, "niveau": niveau, "message": message, "correction": correction,
                    "commande": cmd})

    for l in lignes(texte):
        if not l["commentaire"] and len(l["brut"].encode("utf-8")) > LIMITE:
            ajoute(l, "longueur", "orange", f"Ligne de plus de {LIMITE} octets : le firmware la tronque.",
                   "Couper la ligne en plusieurs lignes.")
        for ecrit, valeur in l["commandes"]:
            if SECRETS.search(ecrit) and valeur:
                ajoute(l, "secret", "rouge", f"Secret en clair ({ecrit}) : il serait lisible dans le fichier et dans le depot.",
                       "Poser ce reglage dans le persist, ou garder la valeur hors du fichier.")
            if l["commentaire"]:
                continue
            nom = commande(ecrit) or ecrit.upper()
            a = absente(ecrit, nom, commandes, gardes_env, berry_env)
            if a:
                ajoute(l, "absente", "orange", a[0], a[1], ecrit)
            if not valeur:
                continue             # sans argument, une commande interroge : ni redemarrage ni reglage pose
            if nom in redemarrent and not _sans_effet(redemarrent[nom], valeur):
                if redemarrent[nom]["quand"] == "toujours":
                    ajoute(l, "redemarrage", "rouge", f"{ecrit} redemarre la carte a chaque demarrage : boucle de redemarrage.",
                           "Retirer la ligne ; regler cette valeur autrement (persist, console).", ecrit)
                else:
                    ajoute(l, "redemarrage", "orange", f"{ecrit} redemarre la carte quand sa valeur change.", None, ecrit)
            if posees is None:
                posees = commandes_posees(persist or {}, texte_config if texte_config is not None else _texte_config())
            if nom in posees:
                if nom not in INDEXEES or ecrit.lower() in [e.strip().lower() for e in posees[nom].split(",")]:
                    cfg = texte_config if texte_config is not None else _texte_config()
                    cle = _cle_persist(cfg, ecrit)
                    if cle and not SECRETS.search(cle + ecrit):
                        v = _v(persist or {}, cle)
                        cle_txt = f" (`{cle}` = {json.dumps(v, ensure_ascii=False)})" if v is not None else f" (`{cle}`)"
                    else:
                        cle_txt = ""
                    ajoute(l, "doublon", "orange", f"{ecrit} est deja reposee a chaque demarrage par le persist{cle_txt}.",
                           "Retirer la ligne, ou changer le persist.", ecrit)
            if nom not in connues and ecrit.upper() not in connues and re.match(r"[A-Za-z]", ecrit):
                chiffres = "" if nom.startswith("SETOPTION") else (re.search(r"\d+$", ecrit) or [""])[0]
                proche = difflib.get_close_matches(nom, sorted(connues), 1)
                ajoute(l, "inconnue", "orange", f"Commande inconnue : {ecrit}.",
                       _casse(ecrit.rstrip("0123456789") if chiffres else ecrit, proche[0]) + chiffres if proche else None)
    return res
