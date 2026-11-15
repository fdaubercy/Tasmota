"""Contre-verification des propositions de menage par git, faite par la page et non par l'agent (plan tasks/plans/menage-page.md, A9).

L'agent cherche des renvois avec ses propres `Grep` : rien ne dit qu'il n'en a pas oublie. Ici chaque proposition est recontrolee :
le chemin existe-t-il et est-il suivi, est-il modifie ou non suivi (donc « en cours »), qui le cite (documents, code ou configuration),
la destination existe-t-elle deja. Le risque est releve si un renvoi vit dans du code ou une configuration ; celui de l'agent est garde
dans `risque_agent`. Lecture seule : seulement `git ls-files`, `git status` et `git grep` (`--no-optional-locks` : aucun verrou d'index pris
pendant que l'utilisateur travaille), jamais de shell, jamais de chemin pris pour une option ou un motif (`--`, `-e`, `:(literal)`).

Une erreur de git (code de sortie inattendu, delai, depot illisible) rend la verification « indisponible » pour la proposition : jamais
« aucun renvoi ». Un delai global borne l'ensemble. Limite connue : un fichier ignore par `.gitignore` sort « non suivi » sans etre « en cours »
(l'agent ne doit de toute facon jamais proposer un fichier ignore).

Banc : test_menage_verification.py.
"""
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath

DELAI = 60            # par commande git
DELAI_TOTAL = 240     # pour toutes les propositions
MAX_RENVOIS = 30
DOCUMENTS = {".md", ".markdown", ".txt", ".rst", ".docx", ".pdf"}
ORDRE = {"faible": 0, "moyen": 1, "eleve": 2}
ACTIONS_A_RISQUE = ("supprimer", "deplacer", "archiver")


def est_document(chemin):
    return PurePosixPath(chemin).suffix.lower() in DOCUMENTS


def nom_distinctif(nom, racine):
    """Le nom court (sans extension) n'est cherche que pour un FICHIER dont le nom ne peut pas etre un mot courant : au moins 8 caracteres
    avec un tiret, un souligne, un chiffre ou une majuscule interne. Pas pour un dossier (« partitions » trouvait 66 fichiers pour 2 vrais renvois)."""
    return (len(nom.stem) >= 8 and not os.path.isdir(os.path.join(str(racine), str(nom)))
            and bool(re.search(r"[_\-0-9]|[a-z][A-Z]", nom.stem)))


def force_en_cours(proposition, verif):
    """Un fichier modifie ou non suivi est du travail en cours, quoi qu'ait dit l'agent."""
    if verif.get("modifie"):
        proposition["en_cours"] = True


def _git(racine, args, delai, codes=(0,)):
    """Sortie de git ; leve subprocess.SubprocessError si le code n'est pas attendu (une erreur ne doit jamais passer pour « rien trouve »)."""
    r = subprocess.run(["git", "--no-optional-locks", "-c", "core.quotepath=off"] + args, cwd=racine, capture_output=True, timeout=max(1, delai),
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode not in codes:
        raise subprocess.SubprocessError(f"git {args[0]} : code {r.returncode}")
    return r.stdout.decode("utf-8", "replace")


def _noms(sortie):
    return [n for n in sortie.split("\0") if n]


def _depot_git(racine, delai):
    try:
        return os.path.samefile(_git(racine, ["rev-parse", "--show-toplevel"], delai).strip(), racine)
    except (OSError, subprocess.SubprocessError):
        return False


def _sur(chemin):
    p = PurePosixPath(str(chemin).replace("\\", "/"))
    return bool(chemin) and "\0" not in chemin and not p.is_absolute() and ".." not in p.parts and not str(chemin)[1:2] == ":"


def _verifie_une(racine, p, delai, limite):
    chemin = p["chemin"]
    if not _sur(chemin):
        return {"disponible": False, "erreur": "chemin refuse"}
    litteral = ":(literal)" + chemin
    nom = PurePosixPath(chemin)
    motifs = [chemin] + ([nom.stem] if nom_distinctif(nom, racine) else [])
    cmd = ["grep", "-I", "-l", "-z", "-F"] + [x for m in motifs for x in ("-e", m)] + ["--", ".", ":(exclude,literal)" + chemin]

    def restant():
        return min(delai, limite - time.monotonic())
    try:
        if restant() <= 0:
            raise subprocess.SubprocessError("delai global depasse")
        suivi = bool(_noms(_git(racine, ["ls-files", "-z", "--", litteral], restant())))
        modifie = bool(_noms(_git(racine, ["status", "--porcelain", "-z", "--", litteral], restant())))
        trouves = _noms(_git(racine, cmd, restant(), codes=(0, 1)))         # 1 = aucune correspondance
    except (OSError, subprocess.SubprocessError) as e:
        return {"disponible": False, "erreur": str(e)[:120] or type(e).__name__}
    docs = sorted(f for f in trouves if est_document(f))
    code = sorted(f for f in trouves if not est_document(f))
    vers = p.get("vers")
    existe = os.path.lexists(os.path.join(racine, chemin))
    return {"disponible": True, "erreur": None, "existe": existe, "suivi": suivi, "modifie": modifie, "perimee": not existe,
            "destination_existe": bool(vers) and _sur(vers) and os.path.lexists(os.path.join(racine, vers)),
            "n_docs": len(docs), "n_code": len(code), "renvois_docs": docs[:MAX_RENVOIS], "renvois_code": code[:MAX_RENVOIS]}


def _applique(p, verif):
    p["verif"] = verif
    if not verif.get("disponible"):
        return p
    force_en_cours(p, verif)
    if p["action"] in ACTIONS_A_RISQUE:
        cible = "eleve" if verif["n_code"] else "moyen" if verif["n_docs"] else None
        if cible and ORDRE[cible] > ORDRE.get(p["risque"], 0):
            p["risque_agent"] = p["risque"]
            p["risque"] = cible
    return p


def enrichit(propositions, racine, delai=DELAI, travailleurs=4, delai_total=DELAI_TOTAL):
    """Rend les propositions (copies) enrichies de `verif`, dans le meme ordre."""
    racine = str(racine)
    copies = [dict(p) for p in propositions]
    if not copies:
        return copies
    if not _depot_git(racine, delai):
        return [_applique(p, {"disponible": False, "erreur": "depot git introuvable"}) for p in copies]
    limite = time.monotonic() + delai_total
    with ThreadPoolExecutor(max_workers=travailleurs) as pool:
        verifs = list(pool.map(lambda p: _verifie_une(racine, p, delai, limite), copies))
    return [_applique(p, v) for p, v in zip(copies, verifs)]
