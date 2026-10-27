"""Faux depot pour les bancs de l'assistant de synchro du fork : deux depots nus (« amont » et « origin »)
et un clone de travail avec les remotes `upstream` et `origin`. Aucun reseau, jamais le vrai depot.

    travail = cree(dossier)                      # dossier/amont.git, dossier/origin.git, dossier/travail
    commit_amont(dossier, {"a.txt": "x\\n"}, "msg") # commit dans l'amont (clone jetable) ; None = suppression
    commit_local(travail, {"b.txt": "y\\n"}, "msg") # commit dans le clone de travail (non pousse)
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ENV = {**os.environ, "GIT_EDITOR": "true", "GIT_TERMINAL_PROMPT": "0"}
FICHIER_ACCENT = "dossier é/fichier x.txt"
COMMUN = "".join(f"ligne {i}\n" for i in range(1, 11))


def git(cwd, *args):
    """Lance git (chemins non quotes) ; leve en cas d'echec ; rend la sortie sans retour final."""
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} (dans {cwd}) : {r.stdout}{r.stderr}")
    return r.stdout.strip()


def _identite(dossier):
    git(dossier, "config", "user.name", "Banc")
    git(dossier, "config", "user.email", "banc@example.invalid")


def _ecrit(racine, fichiers):
    for chemin, contenu in fichiers.items():
        cible = Path(racine) / chemin
        if contenu is None:
            git(racine, "rm", "-q", "--", chemin)
            continue
        cible.parent.mkdir(parents=True, exist_ok=True)
        with open(cible, "w", encoding="utf-8", newline="\n") as f:
            f.write(contenu)
        git(racine, "add", "--", chemin)


def _commit(racine, fichiers, message):
    _ecrit(racine, fichiers)
    git(racine, "commit", "-q", "-m", message)
    return git(racine, "rev-parse", "HEAD")


def cree(dossier: Path) -> Path:
    dossier = Path(dossier)
    amont, origin, travail = dossier / "amont.git", dossier / "origin.git", dossier / "travail"
    for nu in (amont, origin):
        git(dossier, "init", "-q", "--bare", "-b", "development", str(nu))
    with tempfile.TemporaryDirectory() as tmp:
        germe = Path(tmp) / "germe"
        git(tmp, "init", "-q", "-b", "development", str(germe))
        _identite(germe)
        _commit(germe, {"commun.txt": COMMUN, "a.txt": "a\n", FICHIER_ACCENT: "x\n"}, "commit commun")
        for nu in (amont, origin):
            git(germe, "push", "-q", str(nu), "development")
    git(dossier, "clone", "-q", str(origin), str(travail))
    git(travail, "remote", "add", "upstream", str(amont))
    git(travail, "fetch", "-q", "upstream")
    _identite(travail)
    return travail


def copie(modele: Path, dossier: Path) -> Path:
    """Copie d'un depot cree par `cree` (git est lent sous Windows : un modele, N copies). Rend `travail/`."""
    modele, dossier = Path(modele), Path(dossier)
    shutil.copytree(modele, dossier, dirs_exist_ok=True)
    travail = dossier / "travail"
    git(travail, "remote", "set-url", "upstream", str(dossier / "amont.git"))
    git(travail, "remote", "set-url", "origin", str(dossier / "origin.git"))
    return travail


def commit_amont(dossier: Path, fichiers: dict, message: str) -> str:
    """Commit dans l'amont par un clone jetable. Rend le sha."""
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "c"
        git(tmp, "clone", "-q", str(Path(dossier) / "amont.git"), str(clone))
        _identite(clone)
        sha = _commit(clone, fichiers, message)
        git(clone, "push", "-q", "origin", "development")
    return sha


def commit_local(travail: Path, fichiers: dict, message: str) -> str:
    """Commit dans le clone de travail (non pousse). Rend le sha."""
    return _commit(travail, fichiers, message)
