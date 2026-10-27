"""Lectures et actions de la page synchro_fork_web.py en dehors des deux scripts de synchro : etat du
fork (bandeau), fichiers modifies et leur diff, journal des synchros, commit du journal, aide.

Les appels GitHub et la reconnaissance des commits marques ● sont ceux du script de merge
(synchronise_fork_tasmota : gh_api, analyser_commits, slug_depuis_remote) : une seule definition.
"""

import ast
import subprocess
from concurrent.futures import ThreadPoolExecutor

import synchronise_fork_tasmota as sft

REPO = sft.REPO
MAX_DIFF = 300 * 1024
MAX_JOURNAL = 300 * 1024


def _git(*args, racine=REPO):
    """Sortie brute (sans strip : `git status --porcelain` commence par un espace significatif)."""
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=racine, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def fichiers_modifies(racine=REPO):
    """Fichiers suivis modifies : [{"etat": "M", "chemin": ...}] (les non suivis sont comptes a part)."""
    _, sortie, _ = _git("status", "--porcelain", racine=racine)
    suivis, non_suivis = [], 0
    for ligne in sortie.splitlines():
        if not ligne.strip():
            continue
        if ligne.startswith("??"):
            non_suivis += 1
            continue
        chemin = ligne[3:].split(" -> ")[-1].strip().strip('"')
        suivis.append({"etat": ligne[:2].strip(), "chemin": chemin, "journal": chemin == sft.HISTORIQUE_REL})
    return suivis, non_suivis


def operation_git():
    """Merge ou rebase laisse en cours dans le depot (a terminer ou annuler avant toute synchro)."""
    git = REPO / ".git"
    if (git / "rebase-merge").exists() or (git / "rebase-apply").exists():
        return "rebase"
    if (git / "MERGE_HEAD").exists():
        return "merge"
    return ""


def etat():
    branche = sft.git_out("rev-parse", "--abbrev-ref", "HEAD")
    origin, upstream = sft.slug_depuis_remote("origin"), sft.slug_depuis_remote("upstream")
    suivis, non_suivis = fichiers_modifies()
    non_pousses = sft.git_out("rev-list", "--count", f"origin/{branche}..HEAD")
    resultat = {"branche": branche, "origin": origin, "upstream": upstream, "avance": None, "retard": None,
                "commits": [], "non_pousses": int(non_pousses) if non_pousses.isdigit() else None,
                "fichiers": [f for f in suivis if not f["journal"]], "non_suivis": non_suivis,
                "journal_modifie": any(f["journal"] for f in suivis), "operation_git": operation_git(),
                "erreur": ""}
    if not origin or not upstream:
        resultat["erreur"] = "remotes 'origin' et/ou 'upstream' introuvables"
        return resultat
    # Les deux comparaisons partent ensemble : chaque appel `gh` coute plusieurs secondes.
    with ThreadPoolExecutor(2) as pool:
        compare = pool.submit(sft.gh_api, f"repos/{upstream}/compare/{branche}...{origin.split('/')[0]}:{branche}")
        inverse = pool.submit(sft.gh_api, f"repos/{origin}/compare/{branche}...{upstream.split('/')[0]}:{branche}")
        (ok, d), (ok2, d2) = compare.result(), inverse.result()
    if not ok:
        resultat["erreur"] = f"comparaison GitHub impossible : {d}"
        return resultat
    resultat["avance"], resultat["retard"] = d.get("ahead_by", 0), d.get("behind_by", 0)
    if resultat["retard"]:
        if ok2 and isinstance(d2, dict):
            resultat["commits"] = [{"sha": sha, "titre": titre, "saillant": bool(touche),
                                    "url": f"https://github.com/{upstream}/commit/{sha}"}
                                   for sha, titre, touche in sft.analyser_commits(d2.get("commits", []))]
    return resultat


def diff(chemin):
    """Diff d'un fichier suivi modifie ; refuse tout autre chemin (pas de lecture arbitraire du disque)."""
    suivis, _ = fichiers_modifies()
    if chemin not in [f["chemin"] for f in suivis]:
        raise ValueError(f"pas un fichier suivi modifie : {chemin!r}")
    _, sortie, _ = _git("diff", "HEAD", "--", chemin)
    if len(sortie) > MAX_DIFF:
        sortie = sortie[:MAX_DIFF] + f"\n... (tronque a {MAX_DIFF // 1024} Ko)\n"
    return sortie


def historique():
    if not sft.HISTORIQUE.exists():
        return ""
    texte = sft.HISTORIQUE.read_text(encoding="utf-8", errors="replace")
    return texte if len(texte) <= MAX_JOURNAL else "... (debut omis)\n" + texte[-MAX_JOURNAL:]


def commit_journal():
    """Commite le SEUL journal (`git commit -- <journal>` ignore le reste de l'index). Jamais de push."""
    suivis, _ = fichiers_modifies()
    if not any(f["journal"] for f in suivis):
        raise ValueError("le journal n'a pas ete modifie : rien a commiter")
    code, sortie, erreur = _git("commit", "-m", "docs: synchro du fork", "--", sft.HISTORIQUE_REL)
    if code != 0:
        raise RuntimeError((sortie + erreur).strip()[:800] or f"git commit a echoue (code {code})")
    return sft.git_out("log", "-1", "--format=%h %s")


def aide():
    """Docstrings des deux scripts (= leur --help), lues sans les importer."""
    textes = {}
    for cle, nom in (("merge", "synchronise_fork_tasmota.py"), ("rebase", "synchronise_upstream_tasmota.py")):
        source = (sft.REPO / "outils_docs" / "scripts_python" / "maintenance" / nom).read_text(encoding="utf-8")
        textes[cle] = ast.get_docstring(ast.parse(source), clean=False) or ""
    return textes
