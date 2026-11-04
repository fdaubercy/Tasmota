#!/usr/bin/env python3
"""Lecture masquee et ecriture de l'autoexec.bat d'une carte (plan autoexec-bat, A3).

Onglet « autoexec.bat » de l'Assistant persist : la page recoit le fichier avec ses secrets en `***`, le modifie en
texte libre, voit le diff, puis l'ecrit. Aucun secret du fichier ne part vers la page (ni dans le texte, ni dans le
diff) ; ils sont remis ici, cote serveur.
  lit(racine, env)       {texte (secrets en ***), empreinte, chemin (relatif), existe}
  demasque(page, disque) chaque `***` d'une commande C reprend la k-ieme valeur de C du fichier sur disque (k = rang de
                         ce `***` parmi les `***` de C dans la page) ; `***` sans valeur d'origine : ValueError
  diff(racine, env, page)        {diff (unifie, cote disque masque), empreinte, rouges}
  ecrit(racine, env, page, empreinte, rouges_lus, builds_en_cours)   {ecrit, chemin}, dans une Transaction("autoexec")
Masquage : la valeur de toute commande dont le nom repond a autoexec_analyse.SECRETS, ligne en commentaire comprise ;
le reste de la ligne est garde octet pour octet. Le nom est lu comme support_command.ino::ExecuteCommand (lettres,
chiffres, `_`, prefixe `cmnd/x/`) ET comme autoexec_analyse.lignes (mot jusqu'a l'espace) : `Password1=x` est masque.
Empreinte : sha256 des octets du fichier, "" s'il n'existe pas. Rouges : avertissements rouges de
autoexec_analyse.analyse sur le texte DEMASQUE, avec le persist de la carte.
Fichier recrit : BOM garde s'il y en avait un, fins de ligne du fichier (CRLF si le fichier en contient, sinon LF),
presence ou absence de la fin de ligne finale gardee. Nouveau fichier : UTF-8 sans BOM, LF, texte tel que recu.
Banc : test_autoexec_fichier.py.
"""

import difflib
import hashlib
import json
import re
from pathlib import Path

import autoexec_analyse
import autoexec_commandes
import fichiers_berry_sauvegarde as fbs
from build_sauvegarde import CONFIG_PERSIST

MASQUE = "***"
BOM = b"\xef\xbb\xbf"
NOM = re.compile(r"[A-Za-z0-9_/]*")          # nom de commande pour le firmware (support_command.ino::ExecuteCommand)


def chemin(env):
    """Chemin relatif de l'autoexec.bat de l'env ; ValueError pour une base ou un nom sans tiret."""
    import fichiers_berry_etat       # ici : fichiers_berry_ini importe build_envs (cycle, comme build_sauvegarde._demarrage)

    dossier = fichiers_berry_etat.dossier_carte(env)
    if not dossier:
        raise ValueError(f"{env} est une base : pas de dossier de carte, pas d'autoexec.bat")
    return f"{dossier}/autoexec.bat"


def _valeurs(ligne):
    """[(nom ecrit, debut, fin)] des valeurs non vides des commandes a secret de la ligne, de gauche a droite."""
    i = len(ligne) - len(ligne.lstrip())
    if ligne[i:i + 1] == ";":                # commentaire : ses commandes sont masquees aussi
        i = len(ligne) - len(ligne.lstrip().lstrip(";").lstrip())
    m = NOM.match(ligne, i)
    if autoexec_analyse.BACKLOG.fullmatch(m.group().rsplit("/", 1)[-1]):
        morceaux, debut = [], m.end()
        for partie in ligne[m.end():].split(";"):
            morceaux.append((debut, debut + len(partie)))
            debut += len(partie) + 1
    else:
        morceaux = [(i, len(ligne))]
    res = []
    for debut, fin in morceaux:
        partie = ligne[debut:fin]
        debut += len(partie) - len(partie.lstrip())
        m = NOM.match(ligne, debut, fin)
        ecrit = m.group().rsplit("/", 1)[-1]
        mot = (ligne[debut:fin].split() or [""])[0]          # lecture de autoexec_analyse.lignes
        if autoexec_analyse.SECRETS.search(ecrit):
            v = m.end()
        elif autoexec_analyse.SECRETS.search(mot):
            ecrit, v = mot, debut + len(mot)
        else:
            continue
        while v < fin and (ligne[v].isspace() or ligne[v] == "="):
            v += 1
        f = v + len(ligne[v:fin].rstrip())
        if f > v:
            res.append((ecrit, v, f))
    return res


def masque(texte):
    """Texte avec la valeur de chaque commande a secret remplacee par ***, tout le reste intact."""
    sortie = []
    for ligne in texte.splitlines(True):
        for _, d, f in reversed(_valeurs(ligne)):
            ligne = ligne[:d] + MASQUE + ligne[f:]
        sortie.append(ligne)
    return "".join(sortie)


def demasque(texte_page, texte_disque):
    """Remet les valeurs d'origine a la place des *** (meme commande, ordre d'apparition) ; ValueError sinon."""
    origines = {}
    for ligne in texte_disque.splitlines(True):
        for ecrit, d, f in _valeurs(ligne):
            origines.setdefault(ecrit.lower(), []).append(ligne[d:f])
    rangs, sortie = {}, []
    for numero, ligne in enumerate(texte_page.splitlines(True), 1):
        morceaux, pos = [], 0
        for ecrit, d, f in _valeurs(ligne):
            if ligne[d:f] != MASQUE:
                continue                     # valeur saisie en clair : gardee telle quelle (analyse la signale)
            cle = ecrit.lower()
            k = rangs[cle] = rangs.get(cle, -1) + 1
            if k >= len(origines.get(cle, [])):
                raise ValueError(f"ligne {numero} : {ecrit} vaut *** mais le fichier n'a pas de {k + 1}e valeur "
                                 f"d'origine pour {ecrit} : saisir la valeur")
            morceaux += [ligne[pos:d], origines[cle][k]]
            pos = f
        sortie.append("".join(morceaux) + ligne[pos:])
    return "".join(sortie)


def _disque(racine, env):
    """(chemin relatif, octets ou None si le fichier n'existe pas)."""
    rel = chemin(env)
    p = Path(racine) / rel
    return rel, (p.read_bytes() if p.is_file() else None)


def _texte(octets):
    """Texte du fichier, BOM retire, fins de ligne en \\n (celles d'un textarea) ; "" si absent."""
    if octets is None:
        return ""
    try:
        texte = octets[len(BOM):].decode("utf-8") if octets.startswith(BOM) else octets.decode("utf-8")
    except UnicodeDecodeError as erreur:
        raise ValueError(f"autoexec.bat n'est pas en UTF-8 ({erreur.reason}, octet {erreur.start}) : le corriger a la main")
    return texte.replace("\r\n", "\n")


def _empreinte(octets):
    return "" if octets is None else hashlib.sha256(octets).hexdigest()


def _nouveau(texte_page, octets):
    """Texte a ecrire (\\n) : secrets remis, fin de ligne finale du fichier gardee."""
    texte = demasque(texte_page.lstrip("﻿").replace("\r\n", "\n"), _texte(octets))
    if octets and texte:
        fin = octets.endswith((b"\n", b"\r"))
        if fin and not texte.endswith("\n"):
            texte += "\n"
        elif not fin and texte.endswith("\n"):
            texte = texte[:-1]
    return texte


def _octets(texte, octets):
    """Octets a ecrire : fins de ligne et BOM du fichier d'origine.
    shortcut: un fichier a fins de ligne melangees est recrit tout en CRLF ; a traiter si un tel fichier apparait."""
    if octets and b"\r\n" in octets:
        texte = texte.replace("\n", "\r\n")
    return (BOM if octets and octets.startswith(BOM) else b"") + texte.encode("utf-8")


def _rouges(racine, env, texte):
    """Nombre d'avertissements rouges du texte demasque, avec le persist de la carte (vide s'il est illisible)."""
    racine = Path(racine)
    p = racine / chemin(env).rsplit("/", 1)[0] / "_persist.json"
    try:
        persist = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except ValueError:
        persist = {}
    config = racine / CONFIG_PERSIST
    texte_config = config.read_text(encoding="utf-8") if config.is_file() else ""
    avertissements = autoexec_analyse.analyse(texte, persist, autoexec_commandes.charge(racine), texte_config=texte_config)
    return sum(a["niveau"] == "rouge" for a in avertissements)


def lit(racine, env):
    rel, octets = _disque(racine, env)
    return {"texte": masque(_texte(octets)), "empreinte": _empreinte(octets), "chemin": rel, "existe": octets is not None}


def diff(racine, env, texte_page):
    rel, octets = _disque(racine, env)
    nouveau = _nouveau(texte_page, octets)
    # cote page : son propre texte (une valeur saisie en clair y reste visible) ; cote disque : masque
    lignes = difflib.unified_diff(masque(_texte(octets)).splitlines(), texte_page.replace("\r\n", "\n").splitlines(),
                                  "a/" + rel, "b/" + rel, lineterm="")
    return {"diff": "\n".join(lignes), "empreinte": _empreinte(octets), "rouges": _rouges(racine, env, nouveau)}


def ecrit(racine, env, texte_page, empreinte, rouges_lus, builds_en_cours):
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : ecriture refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : ecriture refusee")
    rel, octets = _disque(racine, env)
    if not (Path(racine) / rel).parent.is_dir():
        raise ValueError(f"dossier de la carte absent : {rel.rsplit('/', 1)[0]}")
    if _empreinte(octets) != empreinte:
        raise RuntimeError("autoexec.bat a change sur le disque depuis sa lecture : recharger le fichier")
    nouveau = _nouveau(texte_page, octets)
    rouges = _rouges(racine, env, nouveau)
    if not isinstance(rouges_lus, int) or rouges_lus < rouges:
        raise ValueError(f"{rouges} avertissement(s) rouge(s) : cocher « J'ai lu les {rouges} avertissements rouges »")
    with fbs.Transaction(racine, "autoexec") as tr:
        tr.ecrit(rel, _octets(nouveau, octets))
    return {"ecrit": True, "chemin": rel}
