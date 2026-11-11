#!/usr/bin/env python3
"""Interface d'ecran choisie a la compilation, et retrait des fichiers exclus de l'image du FS (2026-11-11).

Plan tasks/plans/debits-deux-cartes.md, A8. Dans la section de l'env (platformio_tasmota_cenv.ini) :

    custom_interface_ecran          = haspmota
    custom_interface_ecran_haspmota = <fichiers de cette interface>
    custom_interface_ecran_lvgl     = <fichiers de cette interface>

Toute option `custom_interface_ecran_<nom>` declare une interface : rien n'est code en dur ici. Les fichiers des
AUTRES interfaces sont ajoutes a `custom_files_exclude` pour le lancement en cours seulement, dans la config du
projet en memoire (ProjectConfig.set ; env.GetProjectConfig rend la meme instance a tous les lecteurs tant que
platformio.ini n'est pas modifie) : copy_fs_image du pre-script et pio-tools/post_esp32.py relisent cette liste.
Option absente : rien. Valeur sans option `custom_interface_ecran_<valeur>` : le build s'arrete (deux interfaces
ou aucune sur le FS donneraient un ecran noir sans autre message).

`custom_files_exclude` ne retirait pas un fichier du dossier de la CARTE de l'image du buildfs : la plateforme
emballe tout le data_dir (builder/main.py : DataToBin). `retire_exclus`, post-action de littlefs.bin, l'en retire,
avec la regle de post_esp32 (nom de base, a la racine de l'image).

Banc : test_interface_ecran.py (meme dossier).
"""
import os

OPTION = "custom_interface_ecran"
# Geometrie de builder/main.py::build_fs_image (plateforme espressif32)
REGLAGES = {"block_size": 4096, "read_size": 1, "prog_size": 1, "cache_size": 4096, "lookahead_size": 32,
            "block_cycles": 500, "name_max": 64}


def _lignes(config, section, option):
    return [l.strip() for l in config.get(section, option).splitlines() if l.strip()]


def exclusions(config, section):
    """(interface choisie, fichiers des autres interfaces) ; (None, []) sans l'option ; ValueError si inconnue."""
    options = config.options(section)                  # suit extends
    if OPTION not in options:
        return None, []
    choix = config.get(section, OPTION).strip()
    listes = {o[len(OPTION) + 1:]: _lignes(config, section, o) for o in options if o.startswith(OPTION + "_")}
    if choix not in listes:
        connues = ", ".join(sorted(listes)) or f"aucune option {OPTION}_<nom> dans la section"
        raise ValueError(f"{OPTION} = {choix!r} inconnue (interfaces declarees : {connues})")
    gardes = {os.path.basename(f) for f in listes[choix]}
    return choix, [f for nom, fichiers in sorted(listes.items()) if nom != choix
                   for f in fichiers if os.path.basename(f) not in gardes]


def applique(env):
    """Pre-script : ajoute les fichiers des autres interfaces a custom_files_exclude ; valeur inconnue -> arret."""
    config, section = env.GetProjectConfig(), "env:" + env["PIOENV"]
    try:
        choix, exclus = exclusions(config, section)
    except ValueError as e:
        print(f"✗ Interface d'ecran : {e}. Corriger la section [{section}] de platformio_tasmota_cenv.ini")
        env.Exit(1)
        return
    if choix is None:
        return
    try:
        deja = _lignes(config, section, "custom_files_exclude")
    except Exception:                                   # noqa: BLE001 - option absente
        deja = []
    config.set(section, "custom_files_exclude", deja + exclus)
    relus = {os.path.basename(l.strip()) for l in env.GetProjectOption("custom_files_exclude").splitlines()}
    noms = [os.path.basename(f) for f in exclus]
    if not set(noms) <= relus:                          # controle : ce que post_esp32 relira
        print(f"✗ Interface d'ecran : exclusions non relues dans custom_files_exclude ({', '.join(noms)})")
        env.Exit(1)
        return
    print(f"✔ Interface d'ecran : {choix} ; exclus : {', '.join(noms) or 'rien'}")


def retire_de_image(chemin, noms):
    """Retire de l'image LittleFS les fichiers de la racine dont le nom est dans noms ; rend les noms retires."""
    from littlefs import LittleFS, UserContext
    with open(chemin, "rb") as f:
        donnees = bytearray(f.read())

    def monte(version):
        fs = LittleFS(context=UserContext(buffer=donnees), block_count=len(donnees) // REGLAGES["block_size"],
                      mount=False, disk_version=version, **REGLAGES)
        fs.mount()
        return fs

    fs = monte(0)
    version = fs.fs_stat().disk_version
    fs.unmount()
    fs = monte(version)                                 # monte en 0, un retrait passerait l'image de 2.0 a 2.1
    retires = sorted(n for n in fs.listdir("/") if n in noms and fs.stat(n).type == fs.stat(n).TYPE_REG)
    if not retires:
        return []
    for n in retires:
        fs.remove(n)
    fs.unmount()
    with open(chemin, "wb") as f:
        f.write(donnees)
    return retires


def retire_exclus(target, source, env):
    """Post-action de littlefs.bin : meme retrait que post_esp32 (custom_files_exclude, nom de base, racine)."""
    try:
        brut = env.GetProjectOption("custom_files_exclude")
    except Exception:                                   # noqa: BLE001 - option absente
        return None
    noms = {os.path.basename(l.strip()) for l in brut.splitlines() if l.strip()}
    for n in retire_de_image(str(target[0]), noms):
        print(f"  → Liste noire (custom_files_exclude), retire de l'image du FS : {n}")
    return None
