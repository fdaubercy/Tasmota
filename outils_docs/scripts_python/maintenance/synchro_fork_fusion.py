"""Actions de la voie B de l'assistant de synchro du fork : merge LOCAL de upstream/development, resolution
fichier par fichier, commit du merge, journal, push. Appelees par les routes de synchro_fork_web.py.

Garde-fous (spec docs/superpowers/specs/2026-10-27-assistant-synchro-fork-design.md, §6 et §7) :
- chaque action qui modifie l'arbre verifie d'abord qu'aucun build ne tourne (`builds_en_cours`, injecte :
  liste non vide ou None = refus) ;
- le merge lance par l'assistant laisse une marque dans .git (`MARQUE`, JSON : sha fusionne, HEAD au lancement,
  date de MERGE_HEAD, commits a noter au journal) ; resolution et fin du merge reverifient a CHAQUE appel branche
  development et marque = merge en cours, sinon refus « merge étranger » ;
- seules commandes git qui ecrivent : switch development, merge (--ff-only, --no-ff --no-commit, --abort),
  checkout --ours/--theirs, add, rm, commit --no-edit, commit -m <msg> -- <fichiers coches>, push origin
  development (liste blanche verifiee au banc).
  Aucun forcage, aucune reecriture d'historique ; aucun delai sur les commandes qui ecrivent (jamais de kill d'un
  git en plein vol) ; chemins toujours litteraux (--literal-pathspecs : `a[1].txt` n'est pas un motif).

Les textes des exceptions sont affiches dans la page : francais avec accents.
"""

import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import synchro_fork_assistant as asst
import synchro_fork_etat as sfe
import synchronise_fork_tasmota as sft

MARQUE = "synchro-fork-assistant"
AMONT = "upstream/development"
BRANCHE = "development"
TYPE_MERGE = "merge local (conflits résolus)"
DELAI_PUSH = 120                               # s : un push (jamais un merge) peut etre arrete
CHOIX = ("mien", "amont", "garder", "supprimer", "resolu")
AVEC_MARQUEURS = ("UU", "AA")                  # mien, amont, resolu
GARDER = ("DU", "UD", "AU", "UA")              # present d'un seul cote : garder ou supprimer
SUPPRIMER = GARDER + ("DD",)
CARACTERES_CMD = '&|%^<>"'                     # interpretes par cmd.exe, que traverse code.cmd


# -- lectures ----------------------------------------------------------------------------------------------------

def _git(racine, *args, delai=None):
    """Toute commande git de ce module : chemins litteraux, sans delai sauf demande (cf. asst._git)."""
    return asst._git(racine, "--literal-pathspecs", *args, delai=delai)


def _git_ok(racine, *args):
    """Commande git qui doit reussir : sortie (stdout + stderr) ou RuntimeError avec le texte de git."""
    code, sortie, erreur = _git(racine, *args)
    texte = (sortie + erreur).strip()
    if code != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} a échoué (code {code}) : {texte[:800]}")
    return texte


def _liste_z(racine, *args):
    code, sortie, erreur = _git(racine, *args)
    if code != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} a échoué : {(sortie + erreur).strip()[:400]}")
    return [c for c in sortie.split("\0") if c]


def _branche(racine):
    return _git(racine, "rev-parse", "--abbrev-ref", "HEAD")[1].strip()


def _head(racine):
    return _git(racine, "rev-parse", "HEAD")[1].strip()


def _marque(racine):
    return asst.dossier_git(racine) / MARQUE


def _lit_marque(racine):
    try:
        contenu = json.loads(_marque(racine).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return contenu if isinstance(contenu, dict) else None


def _efface_marque(racine):
    _marque(racine).unlink(missing_ok=True)


def oublie_marque_perimee(racine):
    """Marque sans merge en cours (abandonne au terminal) : effacee, elle ne doit pas adopter un merge futur."""
    if not (asst.dossier_git(racine) / "MERGE_HEAD").exists():
        _efface_marque(racine)


def merge_assistant_en_cours(racine):
    """Le merge en cours est celui de l'assistant : MERGE_HEAD = sha note, HEAD = HEAD au lancement, et MERGE_HEAD
    est le fichier ecrit par CE merge (date a la nanoseconde : un merge relance a la main le reecrit)."""
    merge_head = asst.dossier_git(racine) / "MERGE_HEAD"
    marque = _lit_marque(racine)
    if not marque or not merge_head.exists():
        return False
    return (merge_head.read_text(encoding="utf-8", errors="replace").strip() == marque.get("sha")
            and merge_head.stat().st_mtime_ns == marque.get("date") and _head(racine) == marque.get("head"))


def _types(racine):
    """{chemin: code a deux lettres} des entrees non fusionnees de `git status --porcelain -z`."""
    types, entrees = {}, _liste_z(racine, "status", "--porcelain", "-z")
    i = 0
    while i < len(entrees):
        code, chemin = entrees[i][:2], entrees[i][3:]
        i += 2 if code[0] in "RC" else 1          # un renommage porte l'ancien nom a l'entree suivante
        if "U" in code or code in ("AA", "DD"):
            types[chemin] = code
    return types


def _binaires(racine, chemins):
    """Parmi `chemins`, ceux dont `git diff --numstat` entre HEAD et MERGE_HEAD donne « - » comme compteur."""
    binaires = set()
    for ligne in _liste_z(racine, "diff", "--numstat", "--no-renames", "-z", "HEAD", "MERGE_HEAD", "--", *chemins):
        ajouts, _, reste = ligne.partition("\t")
        if ajouts == "-":
            binaires.add(reste.partition("\t")[2])
    return binaires


def conflits(racine):
    """Fichiers encore en conflit, lus dans le DEPOT (`--diff-filter=U`), jamais dans la prevision."""
    chemins = sorted(set(_liste_z(racine, "diff", "--name-only", "-z", "--diff-filter=U")))
    if not chemins:
        return []
    types, binaires = _types(racine), _binaires(racine, chemins)
    return [{"chemin": c, "type": types.get(c, "UU"), "binaire": c in binaires} for c in chemins]


def _etiquette(racine, remote):
    """« proprietaire/depot » pour une URL GitHub, sinon le nom du remote (faux depot du banc)."""
    url = _git(racine, "remote", "get-url", remote)[1].strip()
    m = re.search(r"github\.com[:/]+([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else remote


# -- garde-fous --------------------------------------------------------------------------------------------------

def _verifie_build(builds_en_cours):
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de vérifier qu'aucun build ne tourne : action refusée.")
    if builds:
        raise RuntimeError(f"build en cours ({', '.join(builds)[:300]}) : action refusée, un merge réécrirait"
                           " des fichiers lus par pio. Attends la fin du build.")


def _verifie_propre(racine):
    """Fichiers suivis modifies, journal excepte. Un `git status` en echec leve (jamais « arbre propre »)."""
    entrees, sales, i = _liste_z(racine, "status", "--porcelain", "-z", "--untracked-files=no"), [], 0
    while i < len(entrees):
        code, chemin = entrees[i][:2], entrees[i][3:]
        i += 2 if code[0] in "RC" else 1
        if chemin != sft.HISTORIQUE_REL:
            sales.append(chemin)
    if sales:
        raise RuntimeError(f"arbre de travail non propre ({len(sales)} fichier(s) : {', '.join(sales[:5])}) :"
                           " commite-les d'abord (/commite).")


def _verifie_sans_operation(racine):
    op = asst.operation(racine)
    if op:
        raise RuntimeError(f"un {op} est déjà en cours dans le dépôt : termine-le ou abandonne-le d'abord.")


def _verifie_branche(racine):
    branche = _branche(racine)
    if branche != BRANCHE:
        raise RuntimeError(f"branche actuelle : {branche or 'inconnue'} ; la synchro ne vise que {BRANCHE}.")


def _verifie_merge(racine):
    """Reverification a chaque clic de la voie B : jamais d'action sur un merge que l'assistant n'a pas lance."""
    if _branche(racine) != BRANCHE or not merge_assistant_en_cours(racine):
        raise RuntimeError("merge étranger : aucun merge lancé par l'assistant n'est en cours sur development."
                           " Abandonne-le ou termine-le au terminal.")


def _verifie_index(racine):
    """Rien d'indexe hors des fichiers que l'amont a changes depuis la base commune (HEAD...MERGE_HEAD) : un
    fichier propre au fork, indexe pendant le merge par une autre session, ne part pas avec le merge."""
    indexes = set(_liste_z(racine, "diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD"))
    du_merge = set(_liste_z(racine, "diff", "--name-only", "--no-renames", "-z", "HEAD...MERGE_HEAD"))
    etrangers = sorted(indexes - du_merge)
    if etrangers:
        raise RuntimeError(f"fichier(s) indexé(s) hors du merge : {', '.join(etrangers[:5])}. Retire-les de"
                           " l'index (git restore --staged -- <fichier>) avant de terminer.")


def _a_des_marqueurs(fichier):
    """Marqueurs de conflit en debut de ligne. « ======= » seulement s'il fait la ligne entiere : un soulignement
    de titre plus long (fichiers texte de lib/) n'est pas un marqueur."""
    for ligne in fichier.read_bytes().splitlines():
        if ligne.startswith((b"<<<<<<<", b">>>>>>>")) or ligne.rstrip() == b"=======":
            return True
    return False


def _verifie_choix(chemin, conflit, choix, racine):
    type_ = conflit["type"]
    if choix in ("mien", "amont", "resolu") and type_ not in AVEC_MARQUEURS:
        raise RuntimeError(f"{chemin} ({type_}) n'existe pas des deux côtés : choisis « garder » ou « supprimer ».")
    if choix == "garder" and type_ not in GARDER:
        raise RuntimeError(f"« garder » ne vaut que pour un fichier présent d'un seul côté ({chemin} : {type_}).")
    if choix == "supprimer" and type_ not in SUPPRIMER:
        raise RuntimeError(f"« supprimer » ne vaut que pour un fichier absent d'un côté ({chemin} : {type_}).")
    if choix == "resolu":
        fichier = Path(racine) / chemin
        if conflit["binaire"] or not fichier.exists():
            raise RuntimeError(f"{chemin} ne se marque pas résolu (binaire ou absent) : garde le mien ou prends l'amont.")
        if _a_des_marqueurs(fichier):
            raise RuntimeError(f"{chemin} contient encore des marqueurs de conflit (<<<<<<<, =======, >>>>>>>).")


# -- actions -----------------------------------------------------------------------------------------------------

def bascule(racine, builds_en_cours):
    _verifie_build(builds_en_cours)
    _verifie_sans_operation(racine)
    if _branche(racine) == BRANCHE:
        return f"Déjà sur {BRANCHE}."
    _verifie_propre(racine)
    return _git_ok(racine, "switch", BRANCHE) or f"Branche {BRANCHE} active."


def ff_origin(racine, builds_en_cours):
    _verifie_build(builds_en_cours)
    _verifie_sans_operation(racine)
    _verifie_branche(racine)
    _verifie_propre(racine)
    return _git_ok(racine, "merge", "--ff-only", "origin/development")


def commite(racine, chemins, message, builds_en_cours):
    """Etape « arbre » : commite les fichiers cochés dans la page. `git commit -- <chemins>` ignore le reste de
    l'index ; chaque chemin doit etre dans la liste des fichiers modifies (jamais un chemin libre), journal exclu
    (il a son etape). Jamais pendant un merge : le commit emporterait le merge a moitie resolu."""
    _verifie_build(builds_en_cours)
    _verifie_sans_operation(racine)
    if not isinstance(chemins, list) or not chemins or not all(isinstance(c, str) for c in chemins):
        raise ValueError("aucun fichier coché")
    # Regle du depot : messages sans accents (precedent d'encodage casse) ; « é » devient « e ».
    message = unicodedata.normalize("NFKD", str(message)).encode("ascii", "ignore").decode().strip()
    if not message:
        raise ValueError("message de commit vide")
    modifies = {f["chemin"] for f in sfe.fichiers_modifies(racine)[0] if not f["journal"]}
    hors = [c for c in chemins if c not in modifies]
    if hors:
        raise ValueError(f"fichier(s) absent(s) de la liste des fichiers modifiés : {', '.join(hors[:5])}")
    _git_ok(racine, "commit", "-m", message, "--", *dict.fromkeys(chemins))
    return "Commité : " + _git_ok(racine, "log", "-1", "--format=%h %s")


def _ecrit_marque(racine, marque):
    """Ecriture atomique : une analyse concurrente ne lit jamais une marque a moitie ecrite."""
    cible = _marque(racine)
    temporaire = cible.with_name(MARQUE + ".tmp")
    temporaire.write_text(json.dumps(marque, ensure_ascii=False), encoding="utf-8")
    os.replace(temporaire, cible)


def lance_merge(racine, builds_en_cours):
    """`git merge --no-ff --no-commit upstream/development` ; un conflit n'est pas une erreur (code 1)."""
    _verifie_build(builds_en_cours)
    _verifie_sans_operation(racine)
    _verifie_branche(racine)
    _verifie_propre(racine)
    retard_origin = asst._entier(racine, "rev-list", "--count", "HEAD..origin/development")
    if retard_origin is None or asst._entier(racine, "rev-list", "--count", f"HEAD..{AMONT}") is None:
        raise RuntimeError(f"branches origin/development ou {AMONT} introuvables.")
    if retard_origin:
        raise RuntimeError(f"le dépôt local a {retard_origin} commit(s) de retard sur origin/development :"
                           " fais d'abord l'avance rapide (ff-origin).")
    commits = asst.commits_locaux(racine)
    if not commits:
        raise RuntimeError(f"rien à fusionner : aucun commit de {AMONT} absent de {BRANCHE}.")
    head = _head(racine)
    _efface_marque(racine)                     # une marque restee d'un merge abandonne au terminal
    code, sortie, erreur = _git(racine, "merge", "--no-ff", "--no-commit", AMONT)
    merge_head = asst.dossier_git(racine) / "MERGE_HEAD"
    if not merge_head.exists():
        raise RuntimeError(f"git merge a échoué (code {code}) : {(sortie + erreur).strip()[:800]}")
    marque = {"sha": merge_head.read_text(encoding="utf-8").strip(), "head": head,
              "date": merge_head.stat().st_mtime_ns, "commits": [list(c) for c in commits]}
    try:
        _ecrit_marque(racine, marque)
    except OSError as e:
        raise RuntimeError(f"merge lancé mais marque non écrite ({e}) : il apparaîtra comme étranger,"
                           " abandonne-le.") from e
    restants = conflits(racine)
    if restants:
        return f"Merge lancé : {len(restants)} fichier(s) en conflit à résoudre."
    return "Merge lancé sans conflit : il reste à le terminer."


def resout(racine, chemin, choix, builds_en_cours):
    _verifie_build(builds_en_cours)
    _verifie_merge(racine)
    if choix not in CHOIX:
        raise ValueError(f"choix inconnu : {choix!r}")
    conflit = {c["chemin"]: c for c in conflits(racine)}.get(chemin)
    if conflit is None:
        raise ValueError(f"pas un fichier en conflit : {chemin!r}")
    _verifie_choix(chemin, conflit, choix, racine)
    if choix in ("mien", "amont"):
        _git_ok(racine, "checkout", "--ours" if choix == "mien" else "--theirs", "--", chemin)
    if choix == "supprimer":
        _git_ok(racine, "rm", "-q", "--", chemin)
    else:
        _git_ok(racine, "add", "--", chemin)
    return f"{chemin} : résolu ({choix})."


def ouvre(racine, chemin):
    """Ouvre un fichier en conflit dans VS Code (`code -r`) ; sans `code`, l'erreur donne le chemin."""
    if chemin not in [c["chemin"] for c in conflits(racine)]:
        raise ValueError(f"pas un fichier en conflit : {chemin!r}")
    absolu = Path(racine).resolve() / chemin
    if any(c in str(absolu) for c in CARACTERES_CMD):
        raise RuntimeError(f"chemin avec un caractère spécial ({CARACTERES_CMD}) : ouverture refusée, ouvre le"
                           f" fichier à la main : {absolu}")
    code = shutil.which("code")
    if not code:
        raise RuntimeError(f"commande « code » introuvable : ouvre le fichier à la main : {absolu}")
    subprocess.Popen([code, "-r", str(absolu)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return f"{chemin} ouvert dans VS Code."


def termine(racine, builds_en_cours, historique=None):
    """Commit du merge (message par defaut de git) puis entree au journal des synchros (non commite)."""
    _verifie_build(builds_en_cours)
    _verifie_merge(racine)
    restants = conflits(racine)
    if restants:
        raise RuntimeError(f"{len(restants)} fichier(s) encore en conflit : "
                           f"{', '.join(c['chemin'] for c in restants[:5])}.")
    _verifie_index(racine)
    commits = (_lit_marque(racine) or {}).get("commits") or []
    _git_ok(racine, "commit", "--no-edit")
    _efface_marque(racine)
    journal = Path(historique or Path(racine) / sft.HISTORIQUE_REL)
    avant = journal.stat().st_size if journal.exists() else 0
    sft.noter_historique([tuple(c) for c in commits], _etiquette(racine, "origin"), _etiquette(racine, "upstream"),
                         BRANCHE, TYPE_MERGE, historique=journal)
    texte = "Merge commité : " + _git_ok(racine, "log", "-1", "--format=%h %s")
    if not journal.exists() or journal.stat().st_size <= avant:   # noter_historique avale l'OSError (print)
        texte += " Attention : le journal des synchros n'a pas pu être écrit (le merge, lui, est commité)."
    return texte


def abandonne(racine, builds_en_cours):
    """`git merge --abort` pour tout merge en cours (assistant ou non) ; aucune autre operation n'est touchee."""
    _verifie_build(builds_en_cours)
    op = asst.operation(racine)
    if op and op != "merge":
        raise RuntimeError(f"un {op} est en cours, pas un merge : il se termine (ou s'annule) au terminal.")
    if not op:
        _efface_marque(racine)
        raise RuntimeError("aucun merge en cours : rien à abandonner.")
    _git_ok(racine, "merge", "--abort")
    _efface_marque(racine)
    return "Merge abandonné : dépôt rendu à son état d'avant."


def pousse(racine):
    """`git push origin development` ; la sortie de git est rendue telle quelle, un refus leve RuntimeError."""
    _verifie_sans_operation(racine)
    code, sortie, erreur = _git(racine, "push", "origin", BRANCHE, delai=DELAI_PUSH)
    if code == -1:
        raise RuntimeError(f"git push n'a pas fini en {DELAI_PUSH} s (fenêtre d'identifiants en attente ?) : il a été"
                           " arrêté, rien n'est perdu, tes commits sont toujours en local. Réessaie.")
    texte = (sortie + erreur).strip()
    if code != 0:
        raise RuntimeError(f"push refusé par git (code {code}) : {texte[:800]}")
    return texte or "Poussé."
