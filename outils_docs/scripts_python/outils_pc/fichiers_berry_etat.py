"""Etat des fichiers Berry d'un env pour la page « Fichiers Berry par env » : recensement et etats.

Trois etats pour un fichier de data/ (data/fs ou dossier de la carte), deux pour un module de l'amont
(tasmota/berry/modules) :
  - fs        : sur le LittleFS. Pour data/ c'est le DEFAUT, sans aucune ligne : copy_fs_image
                (pre_utilitaires_platformio.py:540) recopie data/fs dans le dossier de la carte, que
                custom_files_upload designe en entier. Pour l'amont : une ligne de custom_files_upload.
  - exclu     : une ligne de custom_files_exclude (toujours appliquee, post_esp32.py:207).
  - solidifie : une ligne de custom_berry_solidify (retire du FS si custom_files_exclude_solidified = ON).
  - absent    : module de l'amont hors de custom_files_upload.
Le recensement est refait a chaque appel : la page le demande a chaque chargement.
"""

from pathlib import Path

import fichiers_berry_ini as fbi

UPLOAD, EXCLUDE, SOLIDIFY = "custom_files_upload", "custom_files_exclude", "custom_berry_solidify"
OPTIONS = (UPLOAD, EXCLUDE, SOLIDIFY)
EXCLUDE_SOLIDIFIES = "custom_files_exclude_solidified"
DOSSIER_FS = "data/fs"
DOSSIER_AMONT = "tasmota/berry/modules"
EXTENSIONS_AMONT = (".tapp", ".be")     # au premier niveau ; les .bec, dans les sous-dossiers des modules
FIGES = ("autoexec.be",)                # non solidifiable, indispensable au demarrage de la carte


def est_base(env):
    return "-base" in env              # meme regle que build_envs.liste_envs


def dossier_carte(env):
    """Dossier data/ de l'env : regle de transform_name (pre_utilitaires_platformio.py:256), recopiee car
    ce module importe SCons. None pour une base. ValueError si le nom n'a pas de tiret."""
    morceaux = env.split("-")
    if len(morceaux) < 2:
        raise ValueError(f"nom d'env sans tiret : {env!r}")
    if est_base(env):
        return None
    return f"data/{morceaux[1]}/" + "-".join([morceaux[0]] + morceaux[2:])


def recense(racine, env):
    """Fichiers proposes pour l'env : [{"chemin", "groupe": "fs"|"carte"|"amont"}], tries par groupe.
    Pas de sous-dossier de data/fs ni du dossier de la carte (copy_fs_image n'en copie que le premier
    niveau a plat). Amont : les .bec des sous-dossiers, jamais leurs autoexec.be, qui ecraseraient celui
    de la carte a la racine du FS."""
    racine = Path(racine)
    res = []
    for groupe, dossier in (("fs", DOSSIER_FS), ("carte", dossier_carte(env))):
        if dossier and (racine / dossier).is_dir():
            res += [{"chemin": f"{dossier}/{p.name}", "groupe": groupe}
                    for p in sorted((racine / dossier).glob("*.be")) if p.is_file()]
    amont = racine / DOSSIER_AMONT
    if amont.is_dir():
        trouves = [p for p in amont.iterdir() if p.is_file() and p.suffix in EXTENSIONS_AMONT]
        trouves += [p for p in amont.glob("*/*.bec") if p.is_file()]
        res += [{"chemin": p.relative_to(racine).as_posix(), "groupe": "amont"}
                for p in sorted(trouves, key=lambda p: p.relative_to(racine).as_posix().lower())]
    return res


def _exclude_solidifies(ini, env):
    definie = ini.definie_dans(env, EXCLUDE_SOLIDIFIES)
    opt = ini.sections[definie][EXCLUDE_SOLIDIFIES] if definie else None
    return bool(opt and opt.morceaux and opt.morceaux[0][1].upper() == "ON")


def _provenance(ini, env, option, e):
    # partagee : la ligne touche d'autres envs que celui-ci ([berry_commun], option d'une base, y compris
    # l'option propre d'une base vue depuis la base elle-meme : ses cartes en heritent)
    envs = fbi.envs_touches(ini, e.section, e.option, option)
    return {"option": option, "section": e.section, "option_ecrite": e.option, "fichier": e.fichier,
            "ligne": e.ligne, "commentaire": e.commentaire, "partagee": bool(set(envs) - {env}),
            "amont": e.fichier != fbi.FICHIER_CENV, "envs": envs or [env]}


def _entree(e):
    return {"chemin": e.chemin, "section": e.section, "option": e.option, "fichier": e.fichier, "ligne": e.ligne}


def etat_env(racine, env):
    """Etat complet de l'env (voir la spec §2.1, §2.2, §7.3, §7.4). LookupError si l'env n'est pas
    un env propose (ESP32 du cenv)."""
    racine = Path(racine)
    if env not in [e["nom"] for e in envs_proposes(racine)]:
        raise LookupError(f"env inconnu ou non modifiable : {env!r}")
    ini = fbi.lit_sections(racine)
    listes = {o: fbi.resout(ini, env, o) for o in OPTIONS}
    fichiers = recense(racine, env)
    connus = {f["chemin"] for f in fichiers}
    noms = {}
    for f in fichiers:
        if f["groupe"] != "amont":
            noms.setdefault(Path(f["chemin"]).name, []).append(f["chemin"])

    for f in fichiers:
        prov = [_provenance(ini, env, o, e) for o in OPTIONS for e in listes[o] if e.chemin == f["chemin"]]
        dans = {p["option"] for p in prov}
        if f["groupe"] == "amont":
            etat = "fs" if UPLOAD in dans else "absent"
            incoherent = bool(dans - {UPLOAD})
        else:
            etat = "solidifie" if SOLIDIFY in dans else "exclu" if EXCLUDE in dans else "fs"
            incoherent = {SOLIDIFY, EXCLUDE} <= dans
        autres = [c for c in noms.get(Path(f["chemin"]).name, []) if c != f["chemin"]]
        f.update(etat=etat, provenances=prov, incoherent=incoherent,
                 figes=f["groupe"] == "carte" and Path(f["chemin"]).name in FIGES,
                 homonyme=autres[0] if autres else None)

    hors, disparus = [], []
    for o in OPTIONS:
        for e in listes[o]:
            cible = racine / e.chemin
            if e.chemin in connus or e.chemin.startswith(("http://", "https://")) or cible.is_dir():
                continue
            if cible.is_file():
                hors.append(_entree(e))
            else:                                # provenance : une ligne Berry disparue peut etre retiree
                disparus.append(dict(_entree(e), provenance=_provenance(ini, env, o, e)))
    return {"env": env, "dossier_carte": dossier_carte(env), "exclude_solidified": _exclude_solidifies(ini, env),
            "fichiers": fichiers, "hors_perimetre": hors, "disparus": disparus,
            "heritiers": {o: fbi.heritiers(ini, env, o) for o in OPTIONS}}    # envs touches par un AJOUT


def envs_proposes(racine):
    """Envs ESP32 du cenv (une section `env:tasmota32*` dans leur chaine), dans l'ordre du fichier."""
    ini = fbi.lit_sections(racine)
    res = []
    for env in ini.envs_cenv():
        if any(s.startswith("env:tasmota32") for s in ini.chaine(env)):
            res.append({"nom": env, "famille": "bases" if est_base(env) else "cartes"})
    return res
