"""Analyse de l'assistant pas a pas de la synchro du fork : l'etat REEL du depot local (branche, arbre, retard,
commits non pousses, fichiers touches des deux cotes, prevision du merge) puis la liste d'etapes qui en decoule.

Lecture seule : seul le `git fetch` ecrit (dans .git, jamais dans l'arbre). Aucune fonction n'agit sur l'arbre.
Toutes travaillent sur `racine` (le depot reel par defaut, un faux depot dans le banc).
`analyse` rend un dict, `etapes` en tire la liste (fonction pure), `trois_voies` rend les deux diffs d'un fichier.
"""

import os
import subprocess

import synchro_fork_etat as sfe
import synchronise_fork_tasmota as sft

REPO = sfe.REPO
DELAI_FETCH = 60
DELAI_GIT = 60
FICHIERS_BUILD = ("platformio_override.ini", "tasmota/user_config_override.h",
                  "lib/libesp32/berry_custom/src/modules.h", "tasmota/tasmota_defines_for_berry.be",
                  "tasmota/tasmota_defines_for_berry.h")
ENV = {**os.environ, "GIT_EDITOR": "true", "GIT_TERMINAL_PROMPT": "0"}


def _git(racine, *args, delai=DELAI_GIT):
    """(code, sortie, erreur). Delai depasse -> code -1 (le processus n'est pas tue : subprocess.run le fait
    pour ses seules lectures, aucun merge n'est lance ici)."""
    try:
        r = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=racine, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=ENV, timeout=delai)
    except subprocess.TimeoutExpired:
        return -1, "", f"delai de {delai} s depasse : git {' '.join(args[:2])}"
    return r.returncode, r.stdout, r.stderr


def _lignes(racine, *args):
    code, sortie, _ = _git(racine, *args)
    return [ligne for ligne in sortie.splitlines() if ligne] if code == 0 else []


def _entier(racine, *args):
    code, sortie, _ = _git(racine, *args)
    return int(sortie.strip()) if code == 0 and sortie.strip().isdigit() else None


def operation(racine):
    git = os.path.join(racine, ".git")
    if os.path.exists(os.path.join(git, "rebase-merge")) or os.path.exists(os.path.join(git, "rebase-apply")):
        return "rebase"
    return "merge" if os.path.exists(os.path.join(git, "MERGE_HEAD")) else ""


def recupere(racine):
    """fetch upstream development puis origin ; "" si tout va bien, sinon le message d'erreur."""
    for args in (("fetch", "-q", "upstream", "development"), ("fetch", "-q", "origin")):
        code, sortie, erreur = _git(racine, *args, delai=DELAI_FETCH)
        if code != 0:
            return (erreur or sortie).strip()[:400] or f"git {args[0]} {args[2]} a echoue (code {code})"
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


def _voie(retard, non_pousses, prev):
    if not retard:
        return ""
    if prev["conflits"] or non_pousses:
        return "B"
    return "A"


def analyse(racine=REPO, fetch=True):
    a = {"branche": "", "operation": operation(racine), "merge_assistant": False, "retard": 0, "non_pousses": 0,
         "retard_origin": 0, "commits": [], "touches_amont": [], "touches_deux": [],
         "prevision": {"possible": False, "conflits": []}, "fichiers": [], "non_suivis": 0,
         "journal_modifie": False, "voie": "", "etapes": [], "erreur": ""}
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
    amont = _lignes(racine, "diff", "--name-only", "HEAD...upstream/development")
    fork = set(_lignes(racine, "diff", "--name-only", "upstream/development...HEAD"))
    a["touches_amont"] = sorted(amont)
    a["touches_deux"] = sorted(set(amont) & fork)
    a["prevision"] = prevision(racine)
    suivis, a["non_suivis"] = sfe.fichiers_modifies(racine)
    a["journal_modifie"] = any(f["journal"] for f in suivis)
    a["fichiers"] = [{"etat": f["etat"], "chemin": f["chemin"],
                      "classe": "amont" if f["chemin"] in amont else "libre",
                      "build": f["chemin"] in FICHIERS_BUILD} for f in suivis if not f["journal"]]
    a["voie"] = _voie(retard, non_pousses, a["prevision"])
    a["etapes"] = etapes(a)
    return a


def _etape(id_, titre, statut, detail=""):
    return {"id": id_, "titre": titre, "statut": statut, "detail": detail}


def etapes(a):
    """Liste ordonnee des etapes du cas (fonction pure). Les etapes d'information (nouveautes, deux_cotes,
    prevision) sont `faite` quand elles s'affichent ; la premiere etape d'action non faite est `courante`,
    les suivantes `attente`. Une analyse en erreur ne propose aucune etape."""
    if a.get("erreur"):
        return []
    retard, voie, prev = a["retard"], a["voie"], a["prevision"]
    liste = []   # (id, titre, detail, information ?)
    if a["operation"] and not a["merge_assistant"]:
        liste.append(("operation", f"Un {a['operation']} est deja en cours",
                      "Termine-le ou abandonne-le avant toute synchro.", False))
    if a["branche"] != "development":
        liste.append(("branche", "Passer sur development",
                      f"Branche actuelle : {a['branche'] or 'inconnue'}. La synchro ne vise que development.", False))
    if a["fichiers"]:
        liste.append(("arbre", "Arbre de travail propre", f"{len(a['fichiers'])} fichier(s) suivi(s) modifie(s) : "
                      "a commiter avant la synchro (/commite).", False))
    if retard:
        liste.append(("nouveautes", "Nouveautes de l'amont", f"{retard} commit(s) de retard.", True))
        if a["touches_deux"]:
            liste.append(("deux_cotes", "Fichiers touches des deux cotes", ", ".join(a["touches_deux"]), True))
        if not prev["possible"]:
            texte = "prevision impossible (git trop ancien ou commande en echec)"
        elif prev["conflits"]:
            texte = f"{len(prev['conflits'])} fichier(s) en conflit"
        else:
            texte = "sans conflit"
        liste.append(("prevision", "Prevision du merge", texte, True))
    if voie == "A":
        liste.append(("synchro_a", "Synchroniser (en ligne puis local)", "Lance le script de merge.", False))
    elif voie == "B":
        liste.append(("fusion_b", "Merger en local et resoudre", "Merge local guide, fichier par fichier.", False))
    if a["non_pousses"]:
        liste.append(("pousser", "Pousser vers origin", f"{a['non_pousses']} commit(s) non pousse(s).", False))
    if a["journal_modifie"]:
        liste.append(("journal", "Commiter le journal", "Le journal des synchros a ete complete.", False))
    resultat, courante_posee = [], False
    for id_, titre, detail, info in liste:
        if info:
            statut = "faite"
        elif not courante_posee:
            statut, courante_posee = "courante", True
        else:
            statut = "attente"
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
            texte = texte[:sfe.MAX_DIFF] + f"\n... (tronque a {sfe.MAX_DIFF // 1024} Ko)\n"
        sorties.append(texte)
    return {"mien": sorties[0], "amont": sorties[1]}
