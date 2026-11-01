"""Table de partitions d'un env : validation, CSV propre a l'env, ecriture dans le cenv, OTA bloquee
(plan temps-compilation, A9, 2026-11-01).

Regles (celles de la maquette outils_docs/partitions/, modele B) :
  - nvs (0x9000, 0x5000) puis otadata (0xE000, 0x2000) en tete, inchangees : boot_app0.bin est ecrit en 0xE000 ;
  - app0 (ota_0) obligatoire ; les autres partitions par pas de 64 Ko, la premiere en 0x10000 ;
  - aucune partition plus petite que ce qu'elle contient (derniere analyse de build_memoire) ;
  - le FS (spiffs) en dernier (partition_core.be::resize_fs_to_max) ; la table finit a la fin de la flash ;
  - exactement 5 partitions : post_esp32.py::patch_partitions_bin ecrit la taille du FS dans la 5e entree.
Deux temps comme la page Fichiers Berry : `prepare` (diff, rien n'est ecrit), `ecrit` (refait le calcul, empreinte,
aucun build en cours, Transaction). Table identique a un fichier de partitions/ (`tables` les propose) : l'env pointe
vers ce fichier, rien n'est cree ; sinon partitions/env_<env>.csv. Dans les deux cas `board_build.partitions` est pose
dans la section de l'env (les autres envs ne changent pas). Table identique a celle de l'env : rien a ecrire. Une table ecrite BLOQUE l'OTA de l'env (firmware et
FS : une OTA n'ecrit jamais la table en 0x8000) jusqu'au prochain « Effacer puis televerser » reussi (build_serie.py).
Banc : test_build_partitions.py.
"""

import difflib
import hashlib
import json
import re
import time
from pathlib import Path

import build_envs
import build_memoire
import fichiers_berry_sauvegarde as fbs

PAS = 0x10000
TETE = {"nvs": (0x9000, 0x5000, "nvs,      data, nvs,     0x9000,  0x5000,"),
        "otadata": (0xE000, 0x2000, "otadata,  data, ota,     0xe000,  0x2000,")}
ENTETE = "# Name,   Type, SubType, Offset,  Size, Flags"
NOM = re.compile(r"[A-Za-z0-9_]{1,16}")
SOUS_TYPES = {"app": {"factory", "ota_0", "ota_1", "test"}, "data": {"spiffs", "coredump", "fat", "littlefs"}}
CONSEQUENCES = {"safeboot": "plus d'OTA du firmware (la page envoie par le safeboot)",
                "spiffs": "plus de FS : ni persist, ni autoexec, ni Berry non solidifie"}
FICHIER_BLOCAGE = "partitions_modifiees.json"
OPTION = "board_build.partitions"


def valide(parts, flash, occupes=None):
    """(table avec les adresses, erreurs) ; parts = [{nom, type, sous_type, taille}] dans l'ordre de la table."""
    occupes, erreurs, table, debut = occupes or {}, [], [], 0x9000
    noms = [p.get("nom", "") for p in parts]
    if noms[:2] != ["nvs", "otadata"]:
        erreurs.append("nvs puis otadata doivent rester en tête de la table")
    if len(parts) != 5:
        manque = "".join(f" ; {n} supprimée : {effet}" for n, effet in CONSEQUENCES.items() if n not in noms)
        erreurs.append(f"{len(parts)} partitions : seules les tables de 5 sont acceptées (post_esp32.py"
                       f"::patch_partitions_bin écrit la taille du FS dans la 5e entrée){manque}")
    for p in parts:
        nom, type_, st, sz = p.get("nom", ""), p.get("type", ""), p.get("sous_type", ""), p.get("taille")
        if not NOM.fullmatch(nom) or noms.count(nom) > 1:
            erreurs.append(f"nom invalide ou en double : {nom!r}")
        if st not in SOUS_TYPES.get(type_, ()) and nom not in TETE:
            erreurs.append(f"{nom} : type {type_!r} / sous-type {st!r} non pris en charge")
        if not isinstance(sz, int) or isinstance(sz, bool) or sz <= 0:
            erreurs.append(f"{nom} : taille invalide {sz!r}")
            continue
        if nom in TETE:
            if (debut, sz) != TETE[nom][:2]:
                erreurs.append(f"{nom} doit rester en {TETE[nom][0]:#x}, taille {TETE[nom][1]:#x}")
        elif sz % PAS or debut % PAS:
            erreurs.append(f"{nom} : adresse {debut:#x} et taille {sz:#x} doivent être des multiples de 64 Ko")
        if sz < (occupes.get(nom) or 0):
            erreurs.append(f"{nom} : {sz // 1024} Ko, moins que les {-(-occupes[nom] // 1024)} Ko qu'elle contient")
        table.append({"nom": nom, "type": type_, "sous_type": st, "debut": debut, "taille": sz})
        debut += sz
    if not any(p.get("sous_type") == "ota_0" for p in parts):
        erreurs.append("app0 (ota_0) est obligatoire")
    if any(p.get("sous_type") == "spiffs" for p in parts) and parts[-1].get("sous_type") != "spiffs":
        erreurs.append("le FS (spiffs) doit être la dernière partition")
    if not flash:
        erreurs.append("taille de la flash inconnue (board_upload.flash_size de l'env)")
    elif debut != flash:
        erreurs.append(f"la table finit en {debut:#x}, la flash fait {flash:#x} : répartir {abs(flash - debut) // 1024} Ko")
    return table, erreurs


def texte_csv(table, eol="\n"):
    """CSV au format de partitions/ (colonnes alignees comme esp32_partition_app3904k_fs11584k.csv)."""
    lignes = [ENTETE]
    for p in table:
        if p["nom"] in TETE:
            lignes.append(TETE[p["nom"]][2])
            continue
        adresse = f"0x{p['debut']:X},"
        lignes.append(f"{p['nom'] + ',':<10}{p['type'] + ',':<6}{p['sous_type'] + ',':<9}{adresse:<9}0x{p['taille']:X},")
    return eol.join(lignes) + eol


def _lit(chemin):
    return chemin.read_bytes().decode("utf-8", errors="surrogateescape") if chemin.is_file() else ""


def _forme(parts):
    return [(p["nom"], p["type"], p["sous_type"], p["debut"], p["taille"]) for p in parts]


def _existantes(racine):
    """[(chemin relatif, partitions)] des tables de partitions/ ; les env_<env>.csv, propres a un env, n'en sont pas."""
    res = []
    for chemin in sorted((Path(racine) / "partitions").glob("*.csv")):
        if chemin.name.startswith("env_"):
            continue
        try:
            res.append((f"partitions/{chemin.name}", build_memoire.lit_csv(_lit(chemin))))
        except ValueError:                            # CSV illisible : simplement pas propose
            continue
    return res


def tables(racine, dossier, env):
    """Tables existantes a la taille de la flash de l'env : [{csv, partitions, erreurs}] (erreurs : ne convient pas)."""
    mem = build_memoire.analyse(racine, env, Path(dossier) / "journaux")     # LookupError : env inconnu
    occupes = {p["nom"]: p["utilise"] for p in mem["partitions"] if p.get("utilise")}
    return [{"csv": rel, "partitions": parts, "erreurs": valide(parts, mem["flash"], occupes)[1]}
            for rel, parts in _existantes(racine) if parts and parts[-1]["debut"] + parts[-1]["taille"] == mem["flash"]]


def prepare(racine, dossier, env, parts):
    """Diff du cenv et du CSV, erreurs et avertissements ; rien n'est ecrit."""
    racine = Path(racine)
    mem = build_memoire.analyse(racine, env, Path(dossier) / "journaux")     # LookupError : env inconnu
    occupes = {p["nom"]: p["utilise"] for p in mem["partitions"] if p.get("utilise")}
    table, erreurs = valide(parts, mem["flash"], occupes)
    inchange = not erreurs and _forme(table) == _forme(mem["partitions"])
    existante = "" if erreurs else next((r for r, t in _existantes(racine) if _forme(t) == _forme(table)), "")
    rel = mem["csv"] if inchange else existante or f"partitions/env_{env}.csv"
    cenv_avant = _lit(racine / build_envs.FICHIER_CENV)
    try:
        cenv_apres = cenv_avant if inchange else build_envs.pose_option(cenv_avant, env, OPTION, rel)
    except ValueError as erreur:                      # env hors du cenv : ni ecrivable, ni modifiable ici
        erreurs.append(str(erreur))
        cenv_apres = cenv_avant
    eol = "\r\n" if "\r\n" in cenv_avant else "\n"
    csv_avant = _lit(racine / mem["csv"]) if mem["csv"] else ""
    csv_apres = "" if erreurs else _lit(racine / rel) if inchange or existante else texte_csv(table, eol)
    diff = "\n".join(difflib.unified_diff(cenv_avant.splitlines(), cenv_apres.splitlines(), build_envs.FICHIER_CENV,
                                          build_envs.FICHIER_CENV, lineterm="", n=1))
    if csv_apres and not inchange:
        diff += "\n" + "\n".join(difflib.unified_diff(csv_avant.splitlines(), csv_apres.splitlines(),
                                                      mem["csv"] or "(aucune)", rel, lineterm="", n=5))
    toutes, _ = build_envs._sections(racine)
    heritiers = sorted(s[4:] for s in toutes if f"env:{env}" in build_envs._chaine(toutes, s)[1:])
    avertissements = [] if inchange else [
        "le flash série (« Effacer puis téléverser ») remplace le persist et les réglages de la carte par ceux du dépôt",
        f"{build_envs.FICHIER_CENV} change : le prochain build repart de zéro (.pio/build purgé)",
        "l'OTA de cet env (firmware et FS) est bloquée jusqu'au prochain « Effacer puis téléverser » réussi"]
    if heritiers and not inchange:
        avertissements.append("hérite aussi de cette table : " + ", ".join(heritiers))
    vus = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    empreinte = hashlib.sha256((cenv_avant + "\0" + csv_avant + "\0" + vus).encode("utf-8", "surrogateescape")).hexdigest()
    return {"env": env, "csv": rel, "cree_csv": not (inchange or existante), "inchange": inchange, "texte_csv": csv_apres, "cenv": cenv_apres, "table": table, "diff": diff,
            "erreurs": erreurs, "avertissements": avertissements, "empreinte": empreinte}


def ecrit(racine, dossier, env, parts, empreinte_lue, builds_en_cours):
    """Ecrit le CSV et le cenv en une Transaction, puis bloque l'OTA de l'env. RuntimeError (-> 409) : build en cours
    ou indetectable, fichiers changes depuis le diff, table invalide."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : écriture refusée")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : écriture refusée")
    p = prepare(racine, dossier, env, parts)
    if p["erreurs"]:
        raise RuntimeError("table refusée : " + " ; ".join(p["erreurs"]))
    if p["inchange"]:
        raise RuntimeError("c'est déjà la table de cet env : rien à écrire")
    if p["empreinte"] != empreinte_lue:
        raise RuntimeError("le cenv, la table ou les réglages ont changé depuis le diff : refaire « Voir le diff »")
    with fbs.Transaction(racine, "partitions") as tr:
        if p["cree_csv"]:
            tr.ecrit(p["csv"], p["texte_csv"].encode("utf-8"))
        tr.ecrit(build_envs.FICHIER_CENV, p["cenv"].encode("utf-8", errors="surrogateescape"))
    _blocages(dossier, lambda b: b.__setitem__(env, {"csv": p["csv"], "date": time.time()}))
    return {"ecrit": True, "csv": p["csv"], "diff": p["diff"], "sauvegarde": str(tr.dossier)}


def _blocages(dossier, change=None):
    """{env: {csv, date}} des envs dont l'OTA est bloquee ; `change(blocages)` les modifie et reecrit le fichier."""
    chemin = Path(dossier) / FICHIER_BLOCAGE
    try:
        blocages = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        blocages = {}
    if change:
        change(blocages)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        provisoire = chemin.with_suffix(".tmp")
        provisoire.write_text(json.dumps(blocages, ensure_ascii=False, indent=1), encoding="utf-8")
        provisoire.replace(chemin)
    return blocages


def ota_bloquee(dossier, env):
    """Motif du blocage de l'OTA de l'env, "" si permise."""
    b = _blocages(dossier).get(env)
    return (f"table de partitions changée ({b['csv']}) : OTA bloquée jusqu'au prochain « Effacer puis téléverser » "
            "réussi, une OTA n'écrit pas la table") if b else ""


def libere(dossier, env):
    """Apres un « Effacer puis televerser » reussi : la table flashee est celle du depot, l'OTA redevient permise."""
    if env in _blocages(dossier):
        _blocages(dossier, lambda b: b.pop(env, None))
