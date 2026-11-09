#!/usr/bin/env python3
"""Lecture masquee et ecriture de l'autoexec.bat d'une carte (plan autoexec-bat, A3).

Onglet « autoexec.bat » de l'Assistant persist : la page recoit le fichier avec ses secrets en `***`, le modifie en
texte libre, voit le diff, puis l'ecrit. Aucun secret du fichier ne part vers la page (ni dans le texte, ni dans le
diff) ; ils sont remis ici, cote serveur.
  lit(racine, env)       {texte (secrets en ***), empreinte, chemin (relatif), existe}
  demasque(page, disque) la k-ieme apparition de C dans la page, si elle vaut `***`, reprend la valeur de la k-ieme
                         apparition de C sur le disque ; `***` sans origine, ou apparitions de C ajoutees ou retirees
                         alors que C a un `***` : ValueError
  diff(racine, env, page)        {diff (unifie, cote disque masque), empreinte, rouges}
  ecrit(racine, env, page, empreinte, rouges_lus, builds_en_cours)   {ecrit, chemin}, dans une Transaction("autoexec")
  avertissements(racine, env, texte_demasque)   la liste d'autoexec_analyse.analyse (persist de la carte, banque,
                         gardes de compilation de l'env par autoexec_gardes) ; carte_verifiee(racine, env) : ces gardes sont lues
Masquage : apres le premier mot qui repond a autoexec_analyse.SECRETS (nom de commande, ou mot du corps d'une Rule, d'un
Br, d'un commentaire), tout le reste de la partie (ligne, ou morceau de Backlog) : on masque trop plutot que pas assez ;
le debut de la ligne est garde octet pour octet. Le nom est lu comme support_command.ino::ExecuteCommand (lettres,
chiffres, `_`, prefixe `cmnd/x/`) ET comme autoexec_analyse.lignes (mot jusqu'a l'espace) : `Password1=x` est masque.
Empreinte : HMAC-sha256 des octets du fichier, cle tiree une fois par processus (un redemarrage de la page
oblige a relire) ; "" s'il n'existe pas. Rouges : avertissements rouges de
autoexec_analyse.analyse sur le texte DEMASQUE, avec le persist de la carte.
Fichier recrit : BOM garde s'il y en avait un, fins de ligne du fichier (CRLF si le fichier en contient, sinon LF),
presence ou absence de la fin de ligne finale gardee. Nouveau fichier : UTF-8 sans BOM, LF, texte tel que recu.
Banc : test_autoexec_fichier.py.
"""

import difflib
import hashlib
import hmac
import json
import re
import secrets
from pathlib import Path

import autoexec_analyse
import autoexec_banque
import autoexec_berry
import autoexec_commandes
import autoexec_gardes
import fichiers_berry_sauvegarde as fbs
from build_sauvegarde import CONFIG_PERSIST

MASQUE = "***"
BOM = b"\xef\xbb\xbf"
NOM = re.compile(r"[A-Za-z0-9_/]*")          # nom de commande pour le firmware (support_command.ino::ExecuteCommand)
MOT = re.compile(r"[^\s=]+")
_CLE = secrets.token_bytes(32)                # empreinte : HMAC, pas de recherche hors ligne d'un mot de passe faible


def chemin(env):
    """Chemin relatif de l'autoexec.bat de l'env ; ValueError pour une base ou un nom sans tiret."""
    import fichiers_berry_etat       # ici : fichiers_berry_ini importe build_envs (cycle, comme build_sauvegarde._demarrage)

    dossier = fichiers_berry_etat.dossier_carte(env)
    if not dossier:
        raise ValueError(f"{env} est une base : pas de dossier de carte, pas d'autoexec.bat")
    return f"{dossier}/autoexec.bat"


def _valeurs(ligne):
    """[(nom, debut, fin)] de gauche a droite, une par partie (ligne, ou morceau de Backlog entre deux `;`) : apres le
    premier mot a secret de la partie (nom de commande, ou mot du corps d'une Rule, d'un Br, d'un commentaire...), tout
    le reste de la partie jusqu'a sa fin (une valeur peut contenir des espaces). fin == debut : rien a masquer, mais
    l'apparition compte pour la remise."""
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
        mots = MOT.finditer(ligne, debut, fin)
        for mot in mots:
            m = NOM.match(ligne, mot.start(), mot.end())     # Password1:x -> Password1, valeur :x (comme le firmware)
            nom = m.group().rsplit("/", 1)[-1]
            if autoexec_analyse.SECRETS.search(nom):
                v = m.end()
            elif autoexec_analyse.SECRETS.search(mot.group()):     # {"password":"x"} : masque des la fin du mot a secret
                v = mot.start() + autoexec_analyse.SECRETS.search(mot.group()).end()
                nom = ligne[mot.start():v]                         # sans la valeur collee : meme cle sur disque et page
            else:
                continue
            while v < fin and (ligne[v].isspace() or ligne[v] == "="):
                v += 1
            res.append((nom, v, v + len(ligne[v:fin].rstrip())))
            break
    return res


def masque(texte):
    """Texte avec chaque valeur a secret remplacee par ***, tout le reste intact."""
    sortie = []
    for ligne in texte.splitlines(True):
        for _, d, f in reversed(_valeurs(ligne)):
            if f > d:
                ligne = ligne[:d] + MASQUE + ligne[f:]
        sortie.append(ligne)
    return "".join(sortie)


def _apparitions(lignes):
    res = {}
    for ligne in lignes:
        for nom, d, f in _valeurs(ligne):
            res.setdefault(nom.lower(), []).append(ligne[d:f])
    return res


def demasque(texte_page, texte_disque):
    """La k-ieme apparition de C dans la page, si elle vaut ***, reprend la valeur de la k-ieme apparition de C sur le
    disque. ValueError si C n'a pas de valeur d'origine, si le nombre d'apparitions de C a change, ou si une ligne
    garderait un *** sans exister telle quelle sur le disque (mot a secret ajoute devant, par exemple : *** serait ecrit
    tel quel ; une ligne du disque qui contenait deja *** passe)."""
    origines, lignes = _apparitions(texte_disque.splitlines(True)), texte_page.splitlines(True)
    page, rangs, sortie = _apparitions(lignes), {}, []
    for numero, ligne in enumerate(lignes, 1):
        morceaux, pos = [], 0
        for nom, d, f in _valeurs(ligne):
            cle = nom.lower()
            k = rangs[cle] = rangs.get(cle, -1) + 1
            if ligne[d:f] != MASQUE:
                continue                     # valeur saisie en clair : gardee telle quelle (analyse la signale)
            avant = origines.get(cle, [])
            if avant and len(avant) != len(page[cle]):
                raise ValueError(f"ligne {numero} : lignes portant {nom} ajoutees ou retirees : retaper la valeur ou annuler")
            if not avant or not avant[k]:
                raise ValueError(f"ligne {numero} : {nom} vaut *** mais le fichier n'a pas de valeur d'origine pour "
                                 f"cette apparition : saisir la valeur")
            morceaux += [ligne[pos:d], avant[k]]
            pos = f
        sortie.append("".join(morceaux) + ligne[pos:])
    texte = "".join(sortie)
    connues = set(texte_disque.splitlines())
    for n, l in enumerate(texte.splitlines(), 1):
        if MASQUE in l and l not in connues:
            raise ValueError(f"ligne {n} : *** sans valeur d'origine (ligne changee devant le secret) : retaper la valeur ou annuler")
    return texte


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
    return "" if octets is None else hmac.new(_CLE, octets, hashlib.sha256).hexdigest()


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


def texte_disque(racine, env):
    """Texte du fichier sur le disque, en clair (CÔTÉ SERVEUR seulement : ne jamais le renvoyer a la page)."""
    return _texte(_disque(racine, env)[1])


def avertissements(racine, env, texte):
    """Avertissements d'autoexec_analyse.analyse sur le texte DEMASQUE, avec le persist de la carte (vide s'il est
    illisible), configGlobal.be et les noms de la banque. Les messages ne citent jamais une valeur."""
    racine = Path(racine)
    p = racine / chemin(env).rsplit("/", 1)[0] / "_persist.json"
    try:
        persist = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except ValueError:
        persist = {}
    config = racine / CONFIG_PERSIST
    texte_config = config.read_text(encoding="utf-8") if config.is_file() else ""
    try:  # banque absente ou invalide : seulement des oranges en plus, jamais un refus d'editer
        noms = [e["nom"] for e in autoexec_banque.charge(racine)]
    except ValueError:
        noms = []
    return autoexec_analyse.analyse(texte, persist, autoexec_commandes.charge(racine), noms, texte_config=texte_config,
                                    gardes_env=autoexec_gardes.etat(racine, env), berry_env=autoexec_berry.non_chargees(racine, env))


def marques_banque(racine, env):
    """{nom d'entree de la banque: raison} des commandes qui declencheraient l'alerte « absente » sur cette carte (memes
    calculs que l'analyse : gardes du firmware, modules Berry non charges) ; vide si rien n'est verifiable."""
    gardes, berry, commandes = autoexec_gardes.etat(racine, env), autoexec_berry.non_chargees(racine, env), autoexec_commandes.charge(racine)
    res = {}
    for e in autoexec_banque.charge(racine):
        m = re.match(r"[A-Za-z]\w*", e["modele"])               # « Timer{n} ... » -> Timer
        if not m:                                               # modele qui commence par un champ : commande inconnue d'avance
            continue
        ecrit = m[0]
        a =autoexec_analyse.absente(ecrit, autoexec_analyse.commande(ecrit) or ecrit.upper(), commandes, gardes, berry)
        if a:
            res[e["nom"]] = a[0]
    return res


def carte_verifiee(racine, env):
    """Faux si le preprocesseur manque : l'analyse ne peut pas dire qu'une commande est absente de la carte."""
    return autoexec_gardes.etat(racine, env) is not None


def _rouges(racine, env, texte):
    return sum(a["niveau"] == "rouge" for a in avertissements(racine, env, texte))


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
    if isinstance(rouges_lus, bool) or not isinstance(rouges_lus, int) or rouges_lus < rouges:
        raise ValueError(f"{rouges} avertissement(s) rouge(s) : cocher « J'ai lu les {rouges} avertissements rouges »")
    with fbs.Transaction(racine, "autoexec") as tr:
        tr.ecrit(rel, _octets(nouveau, octets))
    return {"ecrit": True, "chemin": rel}
