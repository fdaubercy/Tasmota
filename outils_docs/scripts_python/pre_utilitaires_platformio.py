#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportUndefinedVariable=false, reportMissingModuleSource=false
"""
Script PlatformIO pre-build — utilitaires automatiques avant chaque compilation.

Déclenché automatiquement par PlatformIO via `extra_scripts = pre:...` dans platformio.ini.
S'appuie sur l'environnement actif (`$PIOENV`) pour adapter dynamiquement la configuration
du projet. Regroupe les fonctions suivantes :

ADAPTATION DU PROJET (adapteParametresPlatformio_override)
    À chaque build, déduit le chemin `data_dir` depuis le nom de l'environnement actif
    (ex. `garage-tasmota32p4-serveur-modbus` → `data/garage/tasmota32p4-serveur-modbus`),
    met à jour `platformio_override.ini` en préservant commentaires et indentation,
    et crée le dossier cible s'il n'existe pas. Un backup `.bak` est créé avant modification.

SYNCHRONISATION IDF55 (update_idf55_platform_packages)
    Uniquement pour ESP32-P4 (environnement contenant `32p4`) avec le flag
    `UPDATE_IDF55_PLATFORM` dans les build_flags : délègue la synchronisation du
    framework IDF55 au script externe `update_idf55_framework.py` afin d'éviter les
    conflits de cache entre framework S3 et P4.

INCRÉMENT CFG_HOLDER (increment_config_holder)
    Incrémente automatiquement la valeur de `CFG_HOLDER` dans `user_config_override.h`
    pour forcer Tasmota à recharger sa configuration SECTION1 depuis la flash.
    Sans effet si `CFG_HOLDER` est déjà fixé dans les build_flags. Cycle 0–65535.

COPIE TEMPORAIRE DES FICHIERS GÉNÉRIQUES (copy_fs_image / remove_backup_data)
    Avant la construction du filesystem (buildfs/uploadfs/upload/erase_upload),
    copie les dossiers génériques partagés (`data/fs`, `data/json`, `data/sd`) dans
    le dossier `data_dir` du module courant — les fichiers de `data/fs` sont posés
    directement à la racine. Après le build (via `atexit`), tous les fichiers temporaires
    ainsi copiés sont supprimés, laissant uniquement les fichiers propres au module.

AFFICHAGE DE LA VERSION TASMOTA (afficher_version_tasmota)
    Lit `tasmota/include/tasmota_version.h` et affiche la version courante de Tasmota
    (format `X.Y.Z.W` et valeur hex) dans la console au démarrage du build.

UTILITAIRES INI (apply_rules_to_section / apply_rules_to_entire_file / ...)
    Moteur générique de modification de fichiers `.ini` par règles (`replace`, `append`,
    `remove`). Préserve commentaires inline, indentation et alignement d'origine.
"""

Import("env")  # type: ignore[name-defined]  # SCons/PlatformIO global, injected at runtime
platform = env["PIOPLATFORM"]  # type: ignore[name-defined]

import configparser
import re
import shutil
import os
import sys
import subprocess
import json
from os.path import isfile, join
from enum import Enum
from colorama import Back, Fore, Style, deinit, init
import atexit

# Initialise colorama
# init(autoreset=True)

# ============================================================
# ✨ CLASS VARIABLES GLOBALES ...
# ============================================================
class Global:
    environnement = env.subst('$PIOENV')
    liste_fichiers_exclus = [],                     # Fichiers déjà présents avant la copie des fichiers temporaires
    ignore_dirs = ["fs"],                           # Dossier pour lequel les fichiers sont copiés à la racine
    dossiers_a_copier = ["fs", "json", "sd"],       # Dossiers globaux à copie temporairement avant upload
    build_success = False

# Détection environnement safeboot — désactive les fonctions non pertinentes
is_safeboot = "-safeboot" in Global.environnement
if is_safeboot:
    print(Fore.CYAN + Style.BRIGHT + f"ℹ Environnement safeboot détecté ('{Global.environnement}') :")
    print(Fore.CYAN + "  → adapteParametresPlatformio_override  : ignorée")
    print(Fore.CYAN + "  → update_idf55_platform_packages       : ignorée")
    print(Fore.CYAN + "  → increment_config_holder              : ignorée")
    print(Fore.CYAN + "  → copy_fs_image / remove_backup_data   : ignorées")
    print(Fore.CYAN + "  → afficher_version_tasmota             : active")
    print(Fore.CYAN + "  → USE_CONFIG_OVERRIDE                  : supprimé")
    build_flags = env.get("BUILD_FLAGS", [])
    filtered = [f for f in build_flags if "USE_CONFIG_OVERRIDE" not in f]
    env.Replace(BUILD_FLAGS=filtered)

# ============================================================
# ✨ OUTILS DE BACKUP, GESTION DES INDENTATIONS ...
# ============================================================
def create_backup(file, fileBackup):
    """Crée une sauvegarde .bak du fichier original."""
    if os.path.exists(file):
        shutil.copyfile(file, fileBackup)
        print(Fore.GREEN + f"✔ Sauvegarde créée : {fileBackup}")

def load_ini_with_comments(path):
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    parser = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    parser.optionxform = str
    parser.read(path, encoding="utf-8")

    return raw_lines, parser

def detect_indent(line):
    return re.match(r"(\s*)", line).group(1)

def format_aligned_option(line, key, values, comment):
    m = re.match(r"(\s*)(" + re.escape(key) + r")(\s*)=(\s*)(.*)", line)

    if not m:
        indent = detect_indent(line)
        return [f"{indent}{key} = {values[0]} {comment}".rstrip() + "\n"] + \
               [f"{indent}{v}\n" for v in values[1:]]

    indent_before = m.group(1)
    key_part = m.group(2)
    spaces_before_eq = m.group(3)
    spaces_after_eq = m.group(4)

    formatted = [
        f"{indent_before}{key_part}{spaces_before_eq}={spaces_after_eq}{values[0]} {comment}".rstrip() + "\n"
    ]

    indent_next = indent_before + \
        " " * (len(key_part) + len(spaces_before_eq) + 1 + len(spaces_after_eq))

    for v in values[1:]:
        formatted.append(f"{indent_next}{v}\n")

    return formatted

def remove_parameter_from_option(line, key, values_to_remove, following_lines):
    m = re.match(r"(\s*)(" + re.escape(key) + r")(\s*)=(\s*)(.*)", line)
    if not m:
        return [line] + [l + "\n" for l in following_lines]

    indent_before = m.group(1)
    key_part = m.group(2)
    spaces_before_eq = m.group(3)
    spaces_after_eq = m.group(4)
    first_value = m.group(5).strip().split(";", 1)[0]

    values = [first_value] + [l.strip() for l in following_lines]
    filtered = [v for v in values if v not in values_to_remove]
    if not filtered:
        filtered = [""]

    formatted = [
        f"{indent_before}{key_part}{spaces_before_eq}={spaces_after_eq}{filtered[0]}\n"
    ]

    indent_next = indent_before + \
        " " * (len(key_part) + len(spaces_before_eq) + 1 + len(spaces_after_eq))

    for v in filtered[1:]:
        formatted.append(f"{indent_next}{v}\n")

    return formatted

def apply_rules_to_section(section_name, lines, rules):
    new_lines = []
    in_section = False
    options_done = {opt: False for opt in rules}

    i = 0
    while i < len(lines):
        line = lines[i]

        sec_match = re.match(r"\s*\[(.+?)\]\s*", line)
        if sec_match:
            current = sec_match.group(1)

            if in_section and current != section_name:
                new_lines.extend(insert_missing_options(rules, options_done))
                in_section = False

            in_section = (current == section_name)
            new_lines.append(line)
            i += 1
            continue

        if in_section and "=" in line and not line.strip().startswith(("#", ";")):
            key = line.split("=", 1)[0].strip()

            if key in rules:
                rule = rules[key]
                options_done[key] = True

                indent = detect_indent(line)

                # Commentaire inline
                comment = ""
                if ";" in line:
                    comment = ";" + line.split(";", 1)[1].rstrip("\n")

                # lignes multi-lignes
                following = []
                j = i + 1
                while (
                    j < len(lines)
                    and lines[j].startswith(indent + " ")
                    and not re.match(r"\s*\[", lines[j])
                ):
                    following.append(lines[j].rstrip("\n"))
                    j += 1

                if "replace" in rule:
                    new_lines.extend(format_aligned_option(line, key, rule["replace"], comment))

                elif "append" in rule:
                    current_val = [line.split("=", 1)[1].split(";", 1)[0].strip()]
                    merged = current_val + following + rule["append"]
                    new_lines.extend(format_aligned_option(line, key, merged, comment))

                elif "remove" in rule:
                    new_lines.extend(remove_parameter_from_option(line, key, rule["remove"], following))

                i = j
                continue

        new_lines.append(line)
        i += 1

    if in_section:
        new_lines.extend(insert_missing_options(rules, options_done))

    return new_lines

def insert_missing_options(rules, options_done):
    out = []
    indent = "    "
    for key, done in options_done.items():
        if not done:
            rule = rules[key]
            if "replace" in rule:
                vals = rule["replace"]
            elif "append" in rule:
                vals = rule["append"]
            else:
                continue

            out.append(f"{indent}{key}           = {vals[0]}\n")
            for v in vals[1:]:
                out.append(f"{indent}{v}\n")
    return out

def apply_rules_to_entire_file(lines, rules):
    for section, opts in rules.items():
        lines = apply_rules_to_section(section, lines, opts)
    return lines

# Crée le chemin d'accès au dossier data spécifique à chaque module à partir de l'environnement
# ex Transforme 'garage-tasmota32p4-serveur-modbus' -> 'data/garage/tasmota32p4-serveur-modbus'
def transform_name(name: str) -> str:
    # Vérifie qu'il y a au moins 2 segments
    parts = name.split("-")
    if len(parts) < 2:
        raise ValueError("Le nom doit contenir au moins un tiret.")

    first = parts[0]          # tasmota32p4
    second = parts[1]         # garage
    rest = parts[2:]          # ['serveur', 'modbus']

    # Reconstruit "tasmota32p4-serveur-modbus"
    new_tail = "-".join([first] + rest) if rest else first

    return f"data/{second}/{new_tail}"

# Vérifie si chaque dossier du chemin donné en paramétre existe.
# Sinon, il le crée
def ensure_path(path: str) -> None:
    """
    Vérifie si chaque dossier du chemin existe.
    Si non, il le crée.
    """
    # Supprime un éventuel slash final
    normalized = path.rstrip("/")

    # Création récursive
    if not os.path.exists(normalized):
        print(Fore.GREEN + f"✔ Création du chemin : {normalized}")
        os.makedirs(normalized, exist_ok=True)
    else:
        print(Fore.YELLOW + f"⚠ Le chemin existe déjà : {normalized}")


def adapteParametresPlatformio_override():
    # Uniquement pour les environnements au format "module-type-..." (avec tiret)
    parts = Global.environnement.split("-")
    if len(parts) < 2:
        print(Fore.YELLOW + f"⚠ Environnement '{Global.environnement}' sans tiret : adaptation platformio_override ignorée.")
        return

    # Fichier INI unique
    FILE = "platformio_override.ini"
    BACKUP = FILE + ".bak"
    create_backup(FILE, BACKUP)

    # Crée le répertoire s'il n'existe pas
    # repertoire = os.path.dirname(ini_path)
    new_data_dir = transform_name(Global.environnement)
    ensure_path(new_data_dir)
    print(Fore.GREEN + f"✔ La valeur de 'data_dir' mise à jour à '{new_data_dir}' dans '{FILE}'.")

    # ============================================================
    # CONFIGURATION DES RÈGLES
    # ============================================================
    RULES = {
        "env:tasmota32_base": {
            # "extra_scripts": {
                # "replace": ["${esp_defaults.extra_scripts}","pre:mon_nouveau_script.py"],
                # "remove": ["pre:outils_docs/scripts_python/utilitaires_upload.py"],
                # "append": ["pre:ajout_auto.py"]
            # }
        },
        "platformio": {
            "data_dir": {
                "replace": [new_data_dir],
                # "remove": ["pre:outils_docs/scripts_python/utilitaires_upload.py"],
                # "append": ["pre:ajout_auto.py"]
            }
        }
    }
    # ============================================================

    raw_lines, parser = load_ini_with_comments(FILE)

    updated = apply_rules_to_entire_file(raw_lines, RULES)

    with open(FILE, "w", encoding="utf-8") as f:
        f.writelines(updated)

    print(Fore.GREEN + f"✔ Modifications appliquées avec succès dans {FILE}")

# Synchronise platform_packages IDF55: Si c'est un ESP32-P4) et que le flag 'UPDATE_IDF55_PLATFORM' est défini
# dans platformio_tasmota32.ini. Évite le conflit de cache entre framework S3 et P4.
# Note : si la valeur est modifiée, elle sera effective au prochain build.
def update_idf55_platform_packages():
    script = os.path.join(env.subst("$PROJECT_DIR"), "outils_docs", "scripts_python", "update_idf55_framework.py")
    if not os.path.isfile(script):
        print(Fore.YELLOW + f"⚠ Script introuvable, synchronisation IDF55 ignorée : {script}")
        return
    result = subprocess.run(
        [sys.executable, script],
        cwd=env.subst("$PROJECT_DIR"),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0 and result.stderr:
        print(Fore.RED + result.stderr, end="")

# ============================================================
# ✨ FONCTIONS PERSONNALISEES ...
# ============================================================
# Fonction chargée d'incrémenter le paramètre CONFIG_HOLDER dans le fichier user_config_override.h
def increment_config_holder():
    # Vérifie si CFG_HOLDER est déjà défini dans les build_flags
    for flag in env.get("BUILD_FLAGS"):
        match = re.match(r"-D\s*CFG_HOLDER=(\d+)", flag)
        if match:
            cfg_holder_value = int(match.group(1))
            print(Fore.RED + f"Paramètre CFG_HOLDER (valeur={cfg_holder_value}) trouvé dans les build_flags")
            return

    user_config_path = os.path.join(env.subst("$PROJECT_SRC_DIR"), "user_config_override.h")

    if not os.path.isfile(user_config_path):
        print(Fore.RED + "Le fichier user_config_override.h n'existe pas dans le répertoire source du projet.")
        return

    with open(user_config_path, "r") as file:
        lines = file.readlines()

    config_holder_line_index = None
    for index, line in enumerate(lines):
        if "#define CFG_HOLDER" in line:
            config_holder_line_index = index
            break

    if config_holder_line_index is None:
        print(Fore.RED + "La ligne #define CFG_HOLDER n'a pas été trouvée dans user_config_override.h.")
        return

    current_value_match = re.search(r"#define CFG_HOLDER\s+(\d+)", lines[config_holder_line_index])
    if not current_value_match:
        print(Fore.RED + "Impossible d'extraire la valeur actuelle de CFG_HOLDER.")
        return

    current_value = int(current_value_match.group(1))
    if current_value == 65535:
        current_value = 0
        print(Fore.RED + "La valeur de CFG_HOLDER a atteint la limite maximale de 65535 et ne peut pas être incrémentée davantage.")
    else:
        new_value = current_value + 1
    lines[config_holder_line_index] = f"\t\t#define CFG_HOLDER \t\t{new_value}\t\t\t// [Reset 1] Change this value to load SECTION1 configuration parameters to flash\n"

    with open(user_config_path, "w") as file:
        file.writelines(lines)

    print(Fore.GREEN + f"✔ Le paramètre 'CFG_HOLDER' incrémenté de {current_value} à {new_value} dans user_config_override.h.")

# Fonction chargée de changer la valeur de data_dir dans platformio.ini
def change_data_dir_in_platformio_ini(path_tasmota_cenv, new_data_dir, boolModifDataDir=False):
    ini_path = os.path.join(env.subst("$PROJECT_DIR"), path_tasmota_cenv)

    # Crée le répertoire s'il n'existe pas
    # repertoire = os.path.dirname(ini_path)
    if not os.path.exists(new_data_dir):
        os.makedirs(new_data_dir)

    if not os.path.isfile(ini_path):
        print(Fore.RED + f"Le fichier {path_tasmota_cenv} n'existe pas dans le répertoire du projet.")
        return
        
    if not boolModifDataDir:
        print(Fore.YELLOW + f"La modification de 'data_dir' dans '{path_tasmota_cenv}' est désactivée.")
        return

    with open(ini_path, "r") as file:
        lines = file.readlines()

    data_dir_line_index = None
    for index, line in enumerate(lines):
        if line.strip().startswith("data_dir") or line.strip().startswith("; data_dir"):
            data_dir_line_index = index
            break

    if data_dir_line_index is not None:
        if line.strip().startswith("data_dir"):
            lines[data_dir_line_index] = f"data_dir = {new_data_dir}\n"
        elif line.strip().startswith("; data_dir"):
            lines[data_dir_line_index] = f"; data_dir = {new_data_dir}\n"
    else:
        lines.append(f"data_dir = {new_data_dir}\n")

    with open(ini_path, "w") as file:
        file.writelines(lines)

    print(Fore.GREEN + f"*** La valeur de 'data_dir' mise à jour à '{new_data_dir}' dans '{path_tasmota_cenv}'. ***")

"""    
    Les differntes possibilités de récupération des build_flags: 
    env.get("BUILD_FLAGS", [])
    env.get("$PLATFORMIO_BUILD_FLAGS")
    env.subst(env.get("BUILD_FLAGS"))
    env.GetProjectOption("build_flags")
    print(env.GetProjectOption("build_flags"))

    Ajouter un build_flag pour tester
    env.Append(BUILD_FLAGS=["-D DYNAMIC_FLAG=1"]) 
"""

# Liste les fichiers déjà présent dans le dossier avant ajout des fichiers génériques
def list_files_recursive(folder):
    files_list = []

    for root, dirs, files in os.walk(folder):
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, folder)
            files_list.append(relative_path)

    return files_list

def modules_solidifies():
    """Noms de fichiers déclarés dans `custom_berry_solidify` pour CET environnement.

    Ces modules-là sont compilés DANS le firmware (structures C en flash). Les envoyer
    aussi sur le LittleFS ne sert à rien :
      - `import` sert le module natif et ignore le fichier
        (lib/libesp32/berry/src/be_module.c:285-288 : load_native avant load_package) ;
      - mais `gestionFileFolder.compileModule()` compilerait quand même le .be en .bec
        au démarrage — du temps de boot et des écritures flash pour rien.

    En ne copiant pas le fichier, `compileModule` devient un no-op silencieux
    (data/fs/gestionFileFolder.be:378 : `else return true` si le .be est absent).
    Aucune ligne de Berry à modifier, aucune double comptabilité : la déclaration
    `custom_berry_solidify` de l'env commande tout.

    L'option est absente de la plupart des envs : GetProjectOption lève alors, d'où le
    try/except — c'est ce que fait aussi pio-tools/solidify-from-url.py:154.
    """
    try:
        brut = env.GetProjectOption("custom_berry_solidify")
    except Exception:
        return set()            # env sans solidification : le cas courant
    if not brut:
        return set()
    lignes = brut.splitlines() if isinstance(brut, str) else list(brut)
    return {os.path.basename(l.strip()) for l in lignes if l.strip()}


def copy_fs_image(source, target, env):
    # print(Fore.BLUE + ">>>>>>>>>>>>>>>>> copy_fs_image")
    # Ne faire la suite que si la target est compris dans ce tableau
    optimized_targets = ["buildfs", "uploadfs", "erase_upload", "upload"]
    argv_string = " ".join(sys.argv)

    is_optimized_targets = any(target in argv_string for target in optimized_targets)
    if is_optimized_targets:
        try:
            source_dir = "data"
            source_dir = os.path.abspath(source_dir)

            # Liste les fichiers déjà présents dans 'dest_dir'
            dest_root = transform_name(Global.environnement)
            dest_dir = os.path.abspath(dest_root)

            Global.liste_fichiers_exclus = list_files_recursive(dest_dir)

            # Liste des dossiers à ignorer lors de la copie
            Global.ignore_dirs = ["fs"]
            Global.ignore_dirs = Global.ignore_dirs[0]

            # Crée le dossier destination s'il n'existe pas
            os.makedirs(dest_dir, exist_ok=True)

            Global.dossiers_a_copier = Global.dossiers_a_copier[0]
            for item in Global.dossiers_a_copier:
                source_dir_path = os.path.join(source_dir, item)
                dest_dir_path = os.path.join(dest_dir, item)

                # Ignorer un dossier si demandé
                if os.path.isdir(source_dir_path) and item in Global.ignore_dirs :
                    print(Fore.GREEN + f"✔ Dossier ignoré (mais fichiers copiés à la racine) : {source_dir_path}")

                    # Modules déjà dans le firmware : inutile de les envoyer aussi sur le FS
                    solidifies = modules_solidifies()

                    # Copier uniquement les fichiers directement dans ce dossier
                    for subitem in os.listdir(source_dir_path):
                        sub_src = os.path.join(source_dir_path, subitem)

                        if os.path.isfile(sub_src):
                            if subitem in solidifies:
                                print(Fore.CYAN + f"  → Solidifié dans le firmware, non copié sur le LittleFS : {subitem}")
                                continue

                            flat_dst = os.path.join(dest_root, subitem)
                            print(Fore.GREEN + f"  → Copie du fichier temporaire ignoré : {sub_src} → {flat_dst}")

                            # S'assurer que le dossier racine existe
                            os.makedirs(dest_dir, exist_ok=True)

                            # Copie
                            shutil.copy2(sub_src, flat_dst)

                    continue  # on n'entre pas dans le dossier pour copie standard

                # Copier les dossiers
                if os.path.isdir(source_dir_path):
                    print(Fore.GREEN + f"  → Copie du dossier temporaire : {source_dir_path} → {dest_dir_path}")
                    shutil.copytree(source_dir_path, dest_dir_path, dirs_exist_ok=True)

                # Copier les fichiers à la racine
                elif os.path.isfile(source_dir_path):
                    print(Fore.GREEN + f"  → Copie du fichier temporaire : {source_dir_path} → {dest_dir_path}")
                    shutil.copy2(source_dir_path, dest_dir_path)

        except Exception as e:
            print(Fore.RED + f"✗ Erreur lors de la copie: {e}")

def remove_backup_data(source, target, env):
    # Ne faire la suite que si la target est compris dans ce tableau
    optimized_targets = ["buildfs", "uploadfs", "erase_upload", "upload", "factory_flash", "sortie_script"]
    argv_string = " ".join(sys.argv)

    is_optimized_targets = any(target in argv_string for target in optimized_targets)
    if is_optimized_targets:
        try:
            # Normaliser les chemins (séparateurs, .., etc.) des fichiers à conserver
            keep_set = {os.path.normpath(p) for p in Global.liste_fichiers_exclus}

            dest_dir = transform_name(Global.environnement)
            for root, dirs, files in os.walk(dest_dir, topdown=False):
                root_rel = os.path.relpath(root, dest_dir)

                # === 1. Suppression des fichiers ===
                for f in files:
                    file_rel = os.path.normpath(os.path.join(root_rel, f)) if root_rel != "." else f
                    if file_rel not in keep_set:
                        full_path = os.path.join(root, f)
                        print(Fore.GREEN + f"✔ Suppression du fichier temporaire : {full_path}")
                        os.remove(full_path)

                # === 2. Suppression des dossiers vides ===
                # On supprime un dossier s’il n’est pas nécessaire pour un élément dans keep_list
                if root_rel != ".":
                    # Vérifier si un chemin gardé se trouve dans ce dossier
                    needs_folder = any(
                        k.startswith(root_rel + os.sep) or k == root_rel
                        for k in keep_set
                    )

                    if not needs_folder:
                        print(Fore.GREEN + f"✔ Suppression dossier temporaire : {root}")
                        shutil.rmtree(root, ignore_errors=True)

            # Marque le succès du script
            Global.build_success = True
            print(Fore.GREEN + "✔ Build/upload réussi")

        except Exception as e:
            print(Fore.RED + f"✗ Erreur lors de la suppression: {e}")

# Change la valeur de data_dir dans platformio_tasmota_cenv.ini (Remplacée par 'adapteParametresPlatformio_override()')
# change_data_dir_in_platformio_ini(path_tasmota_cenv="platformio_tasmota_cenv.ini", new_data_dir=f"{Global.environnement.replace('tasmota','data-tasmota')}", boolModifDataDir=True)

# Fonctions déclenchées par l'appui sur 'Build Filesystem Image' ou 'Upload Filesystem Image OTA' dans les fonction 'Platform' de Platformio
""" 
    # Déclenche avant l'évènement en paramètre
    env.AddPreAction(os.path.join(".pio", "build", Global.environnement, "littlefs.bin"), lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: build_littlefs.bin"))
    env.AddPreAction(os.path.join(".pio", "build", Global.environnement, "firmware.bin"), lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: build_firmware.bin"))
    env.AddPreAction(os.path.join(".pio", "build", Global.environnement, "firmware.elf"), lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: build_firmware.elf"))
    env.AddPreAction("factory_flash", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: factory_flash"))
    env.AddPreAction("upload", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: upload"))
    env.AddPreAction("erase_upload", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: erase_upload"))
    env.AddPreAction("uploadfs", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: uploadfs"))
    env.AddPreAction("buildfs", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> avant: buildfs"))

    # Déclenche après l'évènement en paramètre
    env.AddPostAction(os.path.join(".pio", "build", Global.environnement, "littlefs.bin"), lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: build_littlefs.bin"))
    env.AddPostAction(os.path.join(".pio", "build", Global.environnement, "firmware.bin"), lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: build_firmware.bin"))
    env.AddPostAction(os.path.join(".pio", "build", Global.environnement, "firmware.elf"), lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: build_firmware.elf"))
    env.AddPostAction("factory_flash", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: factory_flash"))
    env.AddPostAction("upload", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: upload"))
    env.AddPostAction("erase_upload", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: erase_upload"))
    env.AddPostAction("uploadfs", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: uploadfs"))
    env.AddPostAction("buildfs", lambda source, target, env: print(Fore.BLUE + ">>>>>>>>>>>>>>>>> apres: buildfs")) 
"""

# ============================================================
# ✨ VERSION TASMOTA ...
# ============================================================
def afficher_version_tasmota():
    """Lit et affiche la version Tasmota depuis tasmota/include/tasmota_version.h."""
    version_file = os.path.join(env.subst("$PROJECT_DIR"), "tasmota", "include", "tasmota_version.h")
    if not os.path.isfile(version_file):
        print(Fore.YELLOW + "⚠ tasmota_version.h introuvable, version non affichée.")
        return

    with open(version_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Format attendu : TASMOTA_VERSION = 0x0F040001;   // 15.4.0.1
    m = re.search(r'TASMOTA_VERSION\s*=\s*(0x[0-9A-Fa-f]+)\s*;\s*//\s*([\d.]+)', content)
    if m:
        hex_val = m.group(1)
        version_str = m.group(2)
    else:
        # Fallback : décode le hex sans commentaire
        m = re.search(r'TASMOTA_VERSION\s*=\s*(0x([0-9A-Fa-f]{8}))', content)
        if not m:
            print(Fore.YELLOW + "⚠ Version Tasmota introuvable dans tasmota_version.h.")
            return
        hex_val = m.group(1)
        val = int(m.group(2), 16)
        version_str = f"{(val >> 24) & 0xFF}.{(val >> 16) & 0xFF}.{(val >> 8) & 0xFF}.{val & 0xFF}"

    print(Fore.CYAN + f"✔ Version Tasmota : {version_str}  ({hex_val})")

afficher_version_tasmota()

# ============================================================
# ✨ FONCTIONS ACTIVES UNIQUEMENT HORS SAFEBOOT ...
# ============================================================
if not is_safeboot:
    adapteParametresPlatformio_override()

    if ("32p4" in Global.environnement) and (any("UPDATE_IDF55_PLATFORM" in f for f in env.get("BUILD_FLAGS", []))):
        print(Fore.CYAN + "⚠ Synchronisation IDF55 en cours... (ESP32-P4 détecté et flag 'UPDATE_IDF55_PLATFORM' présent)")
        update_idf55_platform_packages()
    else:
        print(Fore.YELLOW + "⚠ Synchronisation IDF55 ignorée (non applicable pour cet environnement ou flag non défini)")

    increment_config_holder()

    atexit.register(remove_backup_data, "", "sortie_script", "")

    env.AddPreAction(os.path.join(".pio", "build", Global.environnement, "firmware.bin"), copy_fs_image)
    env.AddPreAction(os.path.join(".pio", "build", Global.environnement, "littlefs.bin"), copy_fs_image)

print(Fore.GREEN + "✔ Script pre-utilitaires_platformio.py chargé")

# Déclenche après l'évènement en paramètre ==> Remplacé par 'atexit.register(remove_backup_data)'
# env.AddPostAction("erase_upload", remove_backup_data)
# env.AddPostAction("upload", remove_backup_data)
# env.AddPostAction("factory_flash", remove_backup_data)
# env.AddPostAction("buildfs", remove_backup_data)
# env.AddPostAction("uploadfs", remove_backup_data)