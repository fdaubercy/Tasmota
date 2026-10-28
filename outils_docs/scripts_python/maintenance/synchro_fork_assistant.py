"""Analyse de l'assistant pas a pas de la synchro du fork : l'etat REEL du depot local (branche, arbre, retard,
commits non pousses, fichiers touches des deux cotes, prevision du merge) puis la liste d'etapes qui en decoule.

Lecture seule : seuls le `git fetch` et l'effacement d'une marque perimee de l'assistant ecrivent (dans .git,
jamais dans l'arbre). Aucune fonction n'agit sur l'arbre.
Toutes travaillent sur `racine` (le depot reel par defaut, un faux depot dans le banc).
`analyse` rend un dict, `etapes` en tire la liste (fonction pure), `trois_voies` rend les deux diffs d'un fichier.
"""

import os
import subprocess
from pathlib import Path

import synchro_fork_etat as sfe
import synchronise_fork_tasmota as sft

REPO = sfe.REPO
DELAI_FETCH = 60
FICHIERS_BUILD = ("platformio_override.ini", "tasmota/user_config_override.h",
                  "lib/libesp32/berry_custom/src/modules.h", "tasmota/tasmota_defines_for_berry.be",
                  "tasmota/tasmota_defines_for_berry.h")
ENV = {**os.environ, "GIT_EDITOR": "true", "GIT_TERMINAL_PROMPT": "0"}


def _git(racine, *args, delai=None):
    """(code, sortie, erreur). Delai seulement pour le fetch (reseau) ; les lectures locales n'en ont pas.
    Delai depasse -> code -1 (jamais de kill d'un merge : aucun n'est lance ici)."""
    try:
        r = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=racine, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=ENV, timeout=delai)
    except subprocess.TimeoutExpired:
        return -1, "", f"délai de {delai} s dépassé : git {' '.join(args[:2])}"
    return r.returncode, r.stdout, r.stderr


def _lignes(racine, *args):
    code, sortie, _ = _git(racine, *args)
    return [ligne for ligne in sortie.splitlines() if ligne] if code == 0 else []


def _entier(racine, *args):
    code, sortie, _ = _git(racine, *args)
    return int(sortie.strip()) if code == 0 and sortie.strip().isdigit() else None


def dossier_git(racine):
    """Dossier .git reel (--absolute-git-dir : marche aussi dans un worktree) ; A2 y ecrit sa marque."""
    code, sortie, erreur = _git(racine, "rev-parse", "--absolute-git-dir")
    if code != 0 or not sortie.strip():
        raise RuntimeError(f"dossier .git introuvable : {erreur.strip()[:300]}")
    return Path(sortie.strip())


OPERATIONS = (("MERGE_HEAD", "merge"), ("CHERRY_PICK_HEAD", "cherry-pick"), ("REVERT_HEAD", "revert"),
              ("BISECT_LOG", "bisect"))


def operation(racine):
    """"rebase", "merge", "cherry-pick", "revert", "bisect" ou "" ; RuntimeError si le dossier .git est
    introuvable (jamais « rien en cours » par defaut)."""
    git = dossier_git(racine)
    if (git / "rebase-merge").exists() or (git / "rebase-apply").exists():
        return "rebase"
    return next((nom for fichier, nom in OPERATIONS if (git / fichier).exists()), "")


def recupere(racine):
    """fetch upstream development puis origin ; "" si tout va bien, sinon le message d'erreur."""
    for args in (("fetch", "-q", "upstream", "development"), ("fetch", "-q", "origin")):
        code, sortie, erreur = _git(racine, *args, delai=DELAI_FETCH)
        if code != 0:
            return (erreur or sortie).strip()[:400] or f"git {args[0]} {args[-1]} a échoué (code {code})"
    return ""


def commits_locaux(racine):
    """[(sha[:9], titre, mots saillants)] de HEAD..upstream/development, le plus ancien d'abord."""
    code, sortie, _ = _git(racine, "log", "--reverse", "--format=%H%x09%s", "HEAD..upstream/development")
    resultat = []
    for ligne in sortie.splitlines() if code == 0 else []:
        sha, _, titre = ligne.partition("\t")
        bas = titre.lower()
        resultat.append((sha[:9], titre, [m for m in sft.MOTS_SAILLANTS if m in bas]))
    return resultat


def prevision(racine):
    """merge-tree sans rien ecrire dans l'arbre : {"possible": bool, "conflits": [chemins]}."""
    code, sortie, _ = _git(racine, "merge-tree", "--write-tree", "--name-only", "--no-messages",
                           "HEAD", "upstream/development")
    if code == 0:
        return {"possible": True, "conflits": []}
    if code == 1:
        return {"possible": True, "conflits": sorted(sortie.splitlines()[1:])}
    return {"possible": False, "conflits": []}


def _voie(retard, non_pousses, prev, retard_origin=0):
    if not retard:
        return ""
    if prev["conflits"] or non_pousses or retard_origin:   # la voie B propose l'avance rapide sur origin
        return "B"
    return "A"


def analyse(racine=REPO, fetch=True):
    import synchro_fork_fusion as fusion   # ici : fusion importe ce module (import circulaire)
    a = {"branche": "", "operation": "", "merge_assistant": False, "retard": 0, "non_pousses": 0,
         "retard_origin": 0, "commits": [], "touches_amont": [], "touches_deux": [],
         "prevision": {"possible": False, "conflits": []}, "fichiers": [], "non_suivis": 0, "conflits": [],
         "journal_modifie": False, "voie": "", "etapes": [], "erreur": ""}
    try:
        a["operation"] = operation(racine)
        fusion.oublie_marque_perimee(racine)   # seule ecriture hors fetch : la marque d'un merge abandonne
        a["merge_assistant"] = fusion.merge_assistant_en_cours(racine)
        if a["merge_assistant"]:
            a["conflits"] = fusion.conflits(racine)
    except RuntimeError as e:
        a["erreur"] = str(e)
        return a
    if fetch:
        a["erreur"] = recupere(racine)
        if a["erreur"]:
            return a
    code, sortie, erreur = _git(racine, "rev-parse", "--abbrev-ref", "HEAD")
    a["branche"] = sortie.strip()
    retard = _entier(racine, "rev-list", "--count", "HEAD..upstream/development")
    non_pousses = _entier(racine, "rev-list", "--count", "origin/development..HEAD")
    retard_origin = _entier(racine, "rev-list", "--count", "HEAD..origin/development")
    if None in (retard, non_pousses, retard_origin):
        a["erreur"] = "branches upstream/development ou origin/development introuvables"
        return a
    a["retard"], a["non_pousses"], a["retard_origin"] = retard, non_pousses, retard_origin
    a["commits"] = [{"sha": s, "titre": t, "saillant": bool(m)} for s, t, m in commits_locaux(racine)]
    amont, a["touches_deux"] = touches(racine)
    a["touches_amont"] = amont
    a["prevision"] = prevision(racine)
    suivis, a["non_suivis"] = sfe.fichiers_modifies(racine)
    a["journal_modifie"] = any(f["journal"] for f in suivis)
    # Pendant le merge de l'assistant, les fichiers modifies sont ceux du merge : ils ne salissent pas l'arbre.
    a["fichiers"] = [] if a["merge_assistant"] else [
        {"etat": f["etat"], "chemin": f["chemin"], "classe": "amont" if f["chemin"] in amont else "libre",
         "build": f["chemin"] in FICHIERS_BUILD} for f in suivis if not f["journal"]]
    a["voie"] = "B" if a["merge_assistant"] else _voie(retard, non_pousses, a["prevision"], retard_origin)
    a["etapes"] = etapes(a)
    return a


def touches(racine):
    """([fichiers que l'amont a touches], [ceux touches aussi par le fork]) depuis la base commune."""
    amont = _lignes(racine, "diff", "--name-only", "HEAD...upstream/development")
    fork = set(_lignes(racine, "diff", "--name-only", "upstream/development...HEAD"))
    return sorted(amont), sorted(set(amont) & fork)


def autorises(racine):
    """Fichiers dont /trois-voies rend les diffs : touches des deux cotes + en conflit (sans analyse complete)."""
    import synchro_fork_fusion as fusion
    en_conflit = [c["chemin"] for c in fusion.conflits(racine)] if fusion.merge_assistant_en_cours(racine) else []
    return touches(racine)[1] + en_conflit


def _etape(id_, titre, statut, detail=""):
    return {"id": id_, "titre": titre, "statut": statut, "detail": detail}


def etapes(a):
    """Liste ordonnee des etapes du cas (fonction pure). Les etapes d'information (nouveautes, deux_cotes,
    prevision) sont `faite` quand elles s'affichent ; la premiere etape d'action non faite est `courante`,
    les suivantes `attente`. Une analyse en erreur ne propose aucune etape."""
    if a.get("erreur"):
        return []
    retard, voie, prev = a["retard"], a["voie"], a["prevision"]
    rien = not a.get("merge_assistant") and not retard and not a["non_pousses"] and not a["journal_modifie"]
    liste = []   # (id, titre, detail, information ?, bloquee ?)
    if a["operation"] and not a["merge_assistant"]:
        liste.append(("operation", f"Un {a['operation']} est déjà en cours",
                      "Termine-le ou abandonne-le avant toute synchro (bloqué tant qu'il est en cours).", False, True))
    if rien:
        if a.get("retard_origin") and a["branche"] == "development":   # « a jour » serait faux : origin a avance
            liste.append(("ff_origin", "Rattraper origin", f"{a['retard_origin']} commit(s) de retard sur origin.",
                          False, False))
    else:
        if a["branche"] != "development":
            detail = f"Branche actuelle : {a['branche'] or 'inconnue'}. La synchro ne vise que development."
            if a["fichiers"]:
                detail += " Bouton actif seulement sur un arbre propre : commite d'abord les fichiers modifies."
            liste.append(("branche", "Passer sur development", detail, False, bool(a["fichiers"])))
        if a["fichiers"]:
            liste.append(("arbre", "Arbre de travail propre", f"{len(a['fichiers'])} fichier(s) suivi(s) modifié(s) :"
                          " bloquée tant qu'ils ne sont pas commités (/commite).", False, True))
        if retard:
            liste.append(("nouveautes", "Nouveautés de l'amont", f"{retard} commit(s) de retard.", True, False))
            if a["touches_deux"]:
                liste.append(("deux_cotes", "Fichiers touchés des deux côtés", ", ".join(a["touches_deux"]),
                              True, False))
            if not prev["possible"]:
                texte = "prévision impossible (git trop ancien ou commande en échec)"
            elif prev["conflits"]:
                texte = f"{len(prev['conflits'])} fichier(s) en conflit"
            else:
                texte = "sans conflit"
            liste.append(("prevision", "Prévision du merge", texte, True, False))
        if voie == "A":
            liste.append(("synchro_a", "Synchroniser (en ligne puis local)", "Lance le script de merge.", False, False))
        elif voie == "B":
            detail = "Merge local guidé, fichier par fichier."
            if a.get("merge_assistant"):
                detail = f"Merge en cours : {len(a.get('conflits', []))} fichier(s) encore en conflit."
            liste.append(("fusion_b", "Merger en local et résoudre", detail, False, False))
        if a["journal_modifie"]:
            liste.append(("journal", "Commiter le journal", "Le journal des synchros a été complété.", False, False))
        if a["non_pousses"]:
            liste.append(("pousser", "Pousser vers origin", f"{a['non_pousses']} commit(s) non poussé(s).",
                          False, False))
    resultat, bloque, courante_posee = [], False, False
    for id_, titre, detail, info, bloquante in liste:
        if info:
            statut = "faite"
        elif bloquante:
            statut, bloque = "bloquee", True
        elif bloque or courante_posee:
            statut = "attente"
        else:
            statut, courante_posee = "courante", True
        resultat.append(_etape(id_, titre, statut, detail))
    return resultat


def trois_voies(racine, chemin, autorises):
    """Diffs base->HEAD (« mien ») et base->upstream/development (« amont ») d'un fichier de la liste."""
    if chemin not in autorises:
        raise ValueError(f"fichier hors de la liste : {chemin!r}")
    code, base, erreur = _git(racine, "merge-base", "HEAD", "upstream/development")
    if code != 0:
        raise RuntimeError(f"base commune introuvable : {erreur.strip()[:300]}")
    base = base.strip()
    sorties = []
    for cible in ("HEAD", "upstream/development"):
        _, texte, _ = _git(racine, "diff", base, cible, "--", chemin)
        if len(texte) > sfe.MAX_DIFF:
            texte = texte[:sfe.MAX_DIFF] + f"\n... (tronqué à {sfe.MAX_DIFF // 1024} Ko)\n"
        sorties.append(texte)
    return {"mien": sorties[0], "amont": sorties[1]}
