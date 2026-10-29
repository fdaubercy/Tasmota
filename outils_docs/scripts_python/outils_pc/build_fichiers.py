"""Onglet « Fichiers » de la page 7700 (A15, spec choix 24) : fichiers de l'image du FS d'un env.

La liste vient de `.pio/build/<env>/littlefs.bin`, l'image ecrite par le dernier buildfs (bouton « Preparer
la liste ») : memes fichiers et memes chemins que l'OTA complete du FS. Le `jeton` (date de l'image en ns) part
avec l'envoi : build_serie refuse d'envoyer si l'image a ete reconstruite depuis la liste. Date « dans le
depot » d'un fichier : la plus recente des sources de meme nom (dossier de la carte, `custom_files_upload` de
l'env) ; aucune carte n'est contactee.
"""

import tempfile
from pathlib import Path

import build_envs
import build_ota_fs
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi


def image(racine, env):
    return Path(racine) / ".pio" / "build" / env / "littlefs.bin"


def jeton(chemin):
    """Identifiant de la version de l'image (date de modification en ns), "" si elle est absente."""
    chemin = Path(chemin)
    return str(chemin.stat().st_mtime_ns) if chemin.is_file() else ""


def sources(racine, env):
    """{nom de fichier: [fichiers du depot de ce nom]} : dossier de la carte (tout), `custom_files_upload` de
    l'env (fichiers, et premier niveau des dossiers : copy_fs_image les copie a plat)."""
    racine, trouves = Path(racine), []
    try:
        dossier = fbe.dossier_carte(env)
    except ValueError:
        dossier = None
    if dossier and (racine / dossier).is_dir():
        trouves += [p for p in (racine / dossier).rglob("*") if p.is_file()]
    try:
        entrees = fbi.resout(fbi.lit_sections(racine), env, fbe.UPLOAD)
    except (OSError, ValueError, KeyError):
        entrees = []
    for e in entrees:
        cible = racine / e.chemin
        if cible.is_file():
            trouves.append(cible)
        elif cible.is_dir():
            trouves += [p for p in cible.iterdir() if p.is_file()]
    index = {}
    for p in trouves:
        index.setdefault(p.name, []).append(p)
    return index


def liste(racine, env):
    """Etat de l'image de l'env pour l'onglet : voir la docstring du module. LookupError : env inconnu."""
    racine = Path(racine)
    if env not in {e.nom for e in build_envs.liste_envs(racine)}:
        raise LookupError(f"environnement inconnu : {env!r}")
    chemin = image(racine, env)
    res = {"env": env, "image": {"chemin": str(chemin), "present": chemin.is_file(), "jeton": jeton(chemin),
                                 "date": chemin.stat().st_mtime if chemin.is_file() else None},
           "identite": "", "erreur": "", "fichiers": [], "dossiers": {}}
    if not chemin.is_file():
        res["erreur"] = "pas d'image du FS : cliquer « Préparer la liste » (construction du FS)"
        return res
    date_image = res["image"]["date"]
    index = sources(racine, env)
    with tempfile.TemporaryDirectory(prefix=f"fichiers-{env}-", ignore_cleanup_errors=True) as provisoire:
        dossier_fs = Path(provisoire) / "fs"
        try:
            build_ota_fs.extrait_image(chemin, dossier_fs)
        except RuntimeError as erreur:
            res["erreur"] = str(erreur)
            return res
        try:
            res["identite"] = build_ota_fs.verifie_identite(dossier_fs, build_envs.persist_carte(racine, env), env)
        except RuntimeError as erreur:
            res["erreur"] = str(erreur)       # liste quand meme affichee ; l'envoi refusera la meme image
        for p in sorted(dossier_fs.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(dossier_fs).as_posix()
            dates = [s.stat().st_mtime for s in index.get(p.name, [])]
            depot = max(dates) if dates else None
            res["fichiers"].append({"chemin": rel, "taille": p.stat().st_size, "depot": depot,
                                    "plus_recent": depot is not None and depot > date_image})
            parent = rel.rpartition("/")[0]
            res["dossiers"][parent] = res["dossiers"].get(parent, 0) + 1
    return res
