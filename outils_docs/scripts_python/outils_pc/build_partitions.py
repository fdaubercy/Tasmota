"""Table de partitions d'un env : validation, CSV propre a l'env, ecriture dans le cenv, OTA bloquee
(plan temps-compilation, A9, 2026-11-01).

Regles (celles de la maquette outils_docs/partitions/, modele B) :
  - nvs (0x9000, 0x5000) puis otadata (0xE000, 0x2000) en tete, inchangees : boot_app0.bin est ecrit en 0xE000 ;
  - app0 (ota_0) obligatoire ; les autres partitions par pas de 64 Ko, la premiere en 0x10000 ;
  - aucune partition plus petite que ce qu'elle contient (derniere analyse de build_memoire) ;
  - le FS (spiffs) en dernier (partition_core.be::resize_fs_to_max) ; la table finit a la fin de la flash ;
  - safeboot (factory) en 0x10000 s'il existe : le JSON de la carte y pose son image (upload.arduino.flash_extra_images),
    et cette option est videe dans la section de l'env si la table n'a pas de safeboot ;
  - 4 ou 6 partitions permises, mais post_esp32.py::patch_partitions_bin ecrit la taille du FS dans la 5e entree et le
    hachage en 0xA0 : sur une cible `upload` exacte (jamais `erase_upload`) dont la flash detectee depasse celle declaree,
    il abimerait une table a FS qui n'a pas 5 partitions. `motifs_envoi` refuse donc cet envoi (build_serie.py::controle).
    shortcut: un `pio run -t upload` hors de la page n'est pas controle, a garder dans le pre-script si cela arrive.
Deux temps comme la page Fichiers Berry : `prepare` (diff, rien n'est ecrit), `ecrit` (refait le calcul, empreinte,
aucun build en cours, Transaction). Nom du fichier : `nom` donne par l'utilisateur, sinon env_<env>. Table identique a un
fichier de partitions/, env_* compris : `prepare` le propose (`proposition`), l'env pointe vers lui et rien n'est cree, sauf
`doublon` (l'utilisateur a refuse la proposition). Un fichier nomme existant n'est jamais reecrit, ni l'env_ d'un autre env
s'il sert aussi ailleurs. Dans tous les cas `board_build.partitions` est pose dans la section de l'env (les autres envs ne
changent pas). Table identique a celle de l'env : rien a ecrire. Une table ecrite BLOQUE l'OTA de l'env (firmware et
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
NOM_FICHIER = re.compile(r"(?!env_)(?!(?:CON|PRN|AUX|NUL|COM\d|LPT\d)$)[A-Za-z0-9_-]{1,64}", re.IGNORECASE)
SOUS_TYPES = {"app": {"factory", "ota_0", "ota_1", "test"}, "data": {"spiffs", "coredump", "fat", "littlefs"}}
IMAGES = "board_upload.arduino.flash_extra_images"
FICHIER_BLOCAGE = "partitions_modifiees.json"
OPTION = "board_build.partitions"


def valide(parts, flash, occupes=None):
    """(table avec les adresses, erreurs) ; parts = [{nom, type, sous_type, taille}] dans l'ordre de la table."""
    occupes, erreurs, table, debut = occupes or {}, [], [], 0x9000
    noms = [p.get("nom", "") for p in parts]
    if noms[:2] != ["nvs", "otadata"]:
        erreurs.append("nvs puis otadata doivent rester en tête de la table")
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
    if any(p["sous_type"] == "factory" and p["debut"] != PAS for p in table):
        erreurs.append(f"le safeboot doit rester en {PAS:#x} : le JSON de la carte y pose son image")
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


def _existantes(racine, env_aussi=False):
    """[(chemin relatif, partitions)] des tables de partitions/ ; les env_<env>.csv, propres a un env, seulement si demande."""
    res = []
    for chemin in sorted((Path(racine) / "partitions").glob("*.csv")):
        if chemin.name.startswith("env_") and not env_aussi:
            continue
        try:
            res.append((f"partitions/{chemin.name}", build_memoire.lit_csv(_lit(chemin))))
        except ValueError:                            # CSV illisible : simplement pas propose
            continue
    return res


def _parts_env(racine, env):
    """Partitions de la table de l'env (sans journal ni analyse), [] si illisible."""
    try:
        opt = build_memoire._options(racine, env)
        csv = opt(OPTION) or build_memoire._board(racine, opt("board")).get("build", {}).get("partitions", "")
        return build_memoire.lit_csv(_lit(Path(racine) / csv)) if csv else []
    except (LookupError, ValueError):
        return []


def motifs_envoi(racine, env, actions, methode):
    """Ce que la table de l'env interdit dans ce lancement (texte sans le nom de l'env)."""
    parts, motifs = _parts_env(racine, env), []
    if not parts:
        return motifs
    a_fs = any(p["sous_type"] == "spiffs" for p in parts)
    if "upload" in actions and methode == "com" and a_fs and len(parts) != 5:
        motifs.append(f"table de {len(parts)} partitions : par câble, « Effacer puis téléverser » seulement "
                      "(post_esp32.py::patch_partitions_bin suppose 5 partitions)")
    if "upload" in actions and methode == "ota" and not any(p["sous_type"] == "factory" for p in parts):
        motifs.append("table sans safeboot : OTA du firmware impossible, câble seulement")
    if not a_fs and set(actions) & {"buildfs", "uploadfs", "fichiers"}:
        motifs.append("table sans FS : rien à construire ni à envoyer")
    return motifs


def lit_import(racine, dossier, env, texte):
    """(partitions, erreurs) d'un CSV importe : memes regles que `valide`, adresses du fichier comprises."""
    try:
        parts = build_memoire.lit_csv(texte)
    except ValueError as erreur:
        return [], [str(erreur)]
    if not parts:
        return [], ["aucune partition dans ce fichier"]
    drapeaux = [c[0] for c in (l.split("#", 1)[0].split(",") for l in texte.splitlines()) if len(c) > 5 and c[5].strip()]
    mem = build_memoire.analyse(racine, env, Path(dossier) / "journaux")     # LookupError : env inconnu
    occupes = {p["nom"]: p["utilise"] for p in mem["partitions"] if p.get("utilise")}
    table, erreurs = valide(parts, mem["flash"], occupes)
    if not erreurs and _forme(table) != _forme(parts):
        erreurs.append("adresses non contiguës dans ce fichier : la page ne sait pas garder de trou")
    if drapeaux:
        erreurs.append("drapeaux non pris en charge (colonne Flags) : " + ", ".join(d.strip() for d in drapeaux))
    return parts, erreurs


def tables(racine, dossier, env):
    """Tables existantes a la taille de la flash de l'env : [{csv, partitions, erreurs}] (erreurs : ne convient pas)."""
    mem = build_memoire.analyse(racine, env, Path(dossier) / "journaux")     # LookupError : env inconnu
    occupes = {p["nom"]: p["utilise"] for p in mem["partitions"] if p.get("utilise")}
    return [{"csv": rel, "partitions": parts, "erreurs": valide(parts, mem["flash"], occupes)[1]}
            for rel, parts in _existantes(racine) if parts and parts[-1]["debut"] + parts[-1]["taille"] == mem["flash"]]


def _cible(racine, toutes, env, nom, heritiers):
    """(chemin relatif du fichier a creer, erreurs) d'apres le nom saisi."""
    nom = nom.strip()
    if nom.lower().endswith(".csv"):
        nom = nom[:-4]
    if nom and not NOM_FICHIER.fullmatch(nom):
        return f"partitions/env_{env}.csv", [f"nom de fichier invalide : {nom!r} (lettres, chiffres, _ et -, 64 au plus, sans env_ devant)"]
    rel = f"partitions/{nom or 'env_' + env}.csv"
    if not (Path(racine) / rel).is_file():
        return rel, []
    if nom:
        return rel, [f"{rel} existe déjà avec une autre table : choisir un autre nom"]
    autres = sorted(s[4:] for s in toutes if s.startswith("env:") and s != f"env:{env}" and s[4:] not in heritiers
                    and build_envs._valeur(toutes, s, OPTION) == rel)
    return rel, [f"{rel} sert aussi à {', '.join(autres)} : donner un nom à cette table"] if autres else []


def prepare(racine, dossier, env, parts, nom="", doublon=False):
    """Diff du cenv et du CSV, erreurs, avertissements et table identique deja enregistree ; rien n'est ecrit."""
    racine = Path(racine)
    mem = build_memoire.analyse(racine, env, Path(dossier) / "journaux")     # LookupError : env inconnu
    occupes = {p["nom"]: p["utilise"] for p in mem["partitions"] if p.get("utilise")}
    table, erreurs = valide(parts, mem["flash"], occupes)
    inchange = not erreurs and _forme(table) == _forme(mem["partitions"])
    toutes, _ = build_envs._sections(racine)
    heritiers = sorted(s[4:] for s in toutes if f"env:{env}" in build_envs._chaine(toutes, s)[1:])
    identiques = [] if erreurs else [r for r, t in _existantes(racine, True) if _forme(t) == _forme(table)]
    nom_saisi = nom.strip()
    cible = f"partitions/{nom_saisi[:-4] if nom_saisi.lower().endswith('.csv') else nom_saisi or 'env_' + env}.csv"
    existante = cible if cible in identiques else "" if doublon or not identiques else identiques[0]
    if not inchange and not existante:
        cible, refus = _cible(racine, toutes, env, nom, heritiers)
        erreurs.extend(refus)
    rel = mem["csv"] if inchange else existante or cible
    cenv_avant = _lit(racine / build_envs.FICHIER_CENV)
    try:
        cenv_apres = cenv_avant
        if not inchange:
            sans_safeboot = not erreurs and not any(p["sous_type"] == "factory" for p in table)
            cenv_apres = build_envs.pose_option(cenv_avant, env, OPTION, rel)
            cenv_apres = build_envs.pose_option(cenv_apres, env, IMAGES, "", vide=sans_safeboot)
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
    avertissements = [] if inchange else [
        "le flash série (« Effacer puis téléverser ») remplace le persist et les réglages de la carte par ceux du dépôt",
        f"{build_envs.FICHIER_CENV} change : le prochain build repart de zéro (.pio/build purgé)",
        "l'OTA de cet env (firmware et FS) est bloquée jusqu'au prochain « Effacer puis téléverser » réussi"]
    if not inchange and not any(p["sous_type"] == "factory" for p in table):
        avertissements.append("sans safeboot : plus d'OTA du firmware, ni par Tasmota ni par la page. Seul le câble reste")
    if not inchange and not any(p["sous_type"] == "spiffs" for p in table):
        avertissements.append("sans FS : ni persist, ni autoexec, ni Berry non solidifié. Le module démarre sans son programme")
    if not inchange and len(table) != 5 and any(p["sous_type"] == "spiffs" for p in table):
        avertissements.append(f"{len(table)} partitions : par câble, « Effacer puis téléverser » seulement "
                              "(post_esp32.py::patch_partitions_bin suppose 5 partitions)")
    if heritiers and not inchange:
        avertissements.append("hérite aussi de cette table : " + ", ".join(heritiers))
    vus = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    empreinte = hashlib.sha256((cenv_avant + "\0" + csv_avant + "\0" + rel + "\0" + vus).encode("utf-8", "surrogateescape")).hexdigest()
    return {"env": env, "csv": rel, "cible": cible, "proposition": existante if existante != cible and not inchange else "",
            "cree_csv": not (inchange or existante), "inchange": inchange, "texte_csv": csv_apres, "cenv": cenv_apres, "table": table, "diff": diff,
            "erreurs": erreurs, "avertissements": avertissements, "empreinte": empreinte}


def ecrit(racine, dossier, env, parts, empreinte_lue, builds_en_cours, nom="", doublon=False):
    """Ecrit le CSV et le cenv en une Transaction, puis bloque l'OTA de l'env. RuntimeError (-> 409) : build en cours
    ou indetectable, fichiers changes depuis le diff, table invalide."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : écriture refusée")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : écriture refusée")
    p = prepare(racine, dossier, env, parts, nom, doublon)
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
