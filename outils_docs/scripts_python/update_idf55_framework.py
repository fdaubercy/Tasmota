#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportMissingModuleSource=false
"""
update_idf55_framework.py
─────────────────────────
Lit la version de la plateforme IDF55 (ESP32-P4) dans platformio_tasmota32.ini,
trouve l'URL du framework correspondant dans les plateformes installées PlatformIO
(ou télécharge temporairement le platform.json si besoin),
puis met à jour platform_packages dans platformio_override.ini.

Usage :
    python outils_docs/scripts_python/update_idf55_framework.py
    (à lancer depuis la racine du projet Tasmota)
"""

import configparser
import glob
import io
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile

from colorama import Back, Fore, Style, deinit, init

# init(autoreset=True)

# Fix encodage Windows (cp1252 ne supporte pas les caractères UTF-8 comme [OK])
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TASMOTA32_INI       = "platformio_tasmota32.ini"
OVERRIDE_INI        = "platformio_override.ini"
SECTION_IDF55       = "core32_IDF55"
SECTION_OVERRIDE    = "env:tasmota32_idf55_base"
OPTION_PLATFORM     = "platform"
OPTION_PACKAGES     = "platform_packages"
FRAMEWORK_NAME      = "framework-arduinoespressif32"
PIO_PLATFORMS_DIR   = os.path.expanduser("~/.platformio/platforms")


# ─────────────────────────────────────────────
# LECTURE DU FICHIER INI SANS PERTE DE COMMENTAIRES
# ─────────────────────────────────────────────
def lire_lignes(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()

def ecrire_lignes(path: str, lignes: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lignes)


# ─────────────────────────────────────────────
# EXTRACTION DE L'URL DE LA PLATEFORME IDF55
# ─────────────────────────────────────────────
def lire_url_plateforme_idf55(tasmota32_ini: str) -> str:
    """Lit l'URL de la plateforme IDF55 dans platformio_tasmota32.ini."""
    parser = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    parser.optionxform = str

    with open(tasmota32_ini, "r", encoding="utf-8") as f:
        content = f.read()

    # configparser n'accepte pas les sections sans [DEFAULT] au-dessus
    parser.read_string("[__root__]\n" + content)

    section = SECTION_IDF55
    if not parser.has_section(section):
        raise ValueError(f"Section [{section}] introuvable dans {tasmota32_ini}")

    url = parser.get(section, OPTION_PLATFORM, fallback="").strip()
    if not url:
        raise ValueError(f"Option '{OPTION_PLATFORM}' vide dans [{section}]")

    return url


# ─────────────────────────────────────────────
# RECHERCHE DU FRAMEWORK DANS LES PLATEFORMES INSTALLÉES
# ─────────────────────────────────────────────
def extraire_version_depuis_url(url: str) -> str:
    """Ex: '.../2026.04.50/platform-espressif32.zip' → '2026.04.50'"""
    m = re.search(r"/(\d{4}\.\d{2}\.\d{2,3})/", url)
    return m.group(1) if m else ""

def trouver_framework_dans_installe(version_idf55: str) -> str | None:
    """Cherche dans ~/.platformio/platforms/ la plateforme dont la version correspond."""
    pattern = os.path.join(PIO_PLATFORMS_DIR, "espressif32@src-*", "platform.json")
    for f in glob.glob(pattern):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            if data.get("version", "") == version_idf55:
                fw = data.get("packages", {}).get(FRAMEWORK_NAME, {}).get("version", "")
                if fw:
                    return fw
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────
# TÉLÉCHARGEMENT DU PLATFORM.JSON SI NON INSTALLÉ
# ─────────────────────────────────────────────
def telecharger_framework_url(platform_url: str) -> str:
    """Télécharge le ZIP de la plateforme et extrait l'URL du framework depuis platform.json."""
    print(Fore.YELLOW + f"  Plateforme non trouvée localement, téléchargement de platform.json depuis :")
    print(Fore.YELLOW + f"  {platform_url}")

    with urllib.request.urlopen(platform_url, timeout=30) as resp:
        data = resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Cherche platform.json à la racine ou dans un sous-dossier
        candidats = [n for n in zf.namelist() if n.endswith("platform.json")]
        if not candidats:
            raise FileNotFoundError("platform.json absent dans le ZIP de la plateforme")
        with zf.open(candidats[0]) as pf:
            platform_data = json.load(pf)

    fw = platform_data.get("packages", {}).get(FRAMEWORK_NAME, {}).get("version", "")
    if not fw:
        raise ValueError(f"'{FRAMEWORK_NAME}' absent de platform.json")
    return fw


# ─────────────────────────────────────────────
# MISE À JOUR DE PLATFORMIO_OVERRIDE.INI
# ─────────────────────────────────────────────
def mettre_a_jour_platform_packages(override_ini: str, framework_url: str) -> bool:
    """
    Remplace ou ajoute platform_packages dans [env:tasmota32_idf55_base].
    Conserve tous les commentaires et l'indentation.
    Retourne True si une modification a été faite.
    """
    lignes = lire_lignes(override_ini)
    nouvelle_valeur = f"framework-arduinoespressif32 @ {framework_url}"

    in_section = False
    idx_option  = None   # ligne où se trouve platform_packages (active ou commentée)
    idx_section = None   # ligne où commence la section

    for i, ligne in enumerate(lignes):
        sec = re.match(r"\s*\[(.+?)]\s*", ligne)
        if sec:
            if in_section:
                break  # on a quitté la section sans trouver l'option
            if sec.group(1) == SECTION_OVERRIDE:
                in_section = True
                idx_section = i
            continue

        if not in_section:
            continue

        # Ligne active
        if re.match(r"\s*platform_packages\s*=", ligne):
            idx_option = i
            break

        # Ligne commentée (pour détecter une ancienne valeur mise en commentaire)
        if re.match(r"\s*;platform_packages\s*=", ligne):
            idx_option = i  # on la remplacera par une ligne active

    # ── Vérifie si la valeur est déjà à jour ──
    if idx_option is not None and lignes[idx_option].lstrip().startswith("platform_packages"):
        valeur_actuelle = lignes[idx_option].split("=", 1)[1].strip().rstrip("\n")
        if valeur_actuelle == nouvelle_valeur:
            print(Fore.GREEN + "  platform_packages est déjà à jour, aucune modification nécessaire.")
            return False

    # ── Sauvegarde avant modification ──
    backup = override_ini + ".bak"
    shutil.copyfile(override_ini, backup)
    print(Fore.CYAN + f"  Sauvegarde créée : {backup}")

    nouvelle_ligne = f"platform_packages       = {nouvelle_valeur}\n"

    if idx_option is not None:
        # Supprime les éventuelles lignes de continuation (indentées)
        j = idx_option + 1
        while j < len(lignes) and lignes[j].startswith((" ", "\t")) and not re.match(r"\s*\[", lignes[j]):
            j += 1
        lignes[idx_option:j] = [nouvelle_ligne]
    elif idx_section is not None:
        # Insère après la ligne de section (et le commentaire éventuel qui suit)
        insert_at = idx_section + 1
        while insert_at < len(lignes) and lignes[insert_at].lstrip().startswith(";"):
            insert_at += 1
        lignes.insert(insert_at, nouvelle_ligne)
    else:
        print(Fore.RED + f"  Section [{SECTION_OVERRIDE}] introuvable dans {override_ini}")
        return False

    ecrire_lignes(override_ini, lignes)
    return True


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────
def main():
    print(Fore.CYAN + Style.BRIGHT + "\n=== Mise à jour platform_packages IDF55 (ESP32-P4) ===")

    # 1. Vérifie qu'on est bien à la racine du projet
    for f in (TASMOTA32_INI, OVERRIDE_INI):
        if not os.path.isfile(f):
            print(Fore.RED + f"Fichier introuvable : {f}")
            print(Fore.RED + "Lance ce script depuis la racine du projet Tasmota.")
            sys.exit(1)

    # 2. URL de la plateforme IDF55
    print(f"Lecture de [{SECTION_IDF55}] dans {TASMOTA32_INI}...")
    platform_url = lire_url_plateforme_idf55(TASMOTA32_INI)
    version_idf55 = extraire_version_depuis_url(platform_url)
    print(Fore.GREEN + f"  Plateforme IDF55 : {version_idf55}")
    print(Fore.GREEN + f"  URL              : {platform_url}")

    # 3. URL du framework (plateformes installées en priorité)
    print(f"\nRecherche du framework dans {PIO_PLATFORMS_DIR}...")
    framework_url = trouver_framework_dans_installe(version_idf55)

    if framework_url:
        print(Fore.GREEN + f"  Framework trouvé localement : {framework_url}")
    else:
        print(Fore.YELLOW + "  Non trouvé localement, téléchargement...")
        try:
            framework_url = telecharger_framework_url(platform_url)
            print(Fore.GREEN + f"  Framework récupéré : {framework_url}")
        except Exception as e:
            print(Fore.RED + f"  Erreur lors du téléchargement : {e}")
            sys.exit(1)

    # 4. Mise à jour de platformio_override.ini
    print(f"\nMise à jour de {OVERRIDE_INI}...")
    modifie = mettre_a_jour_platform_packages(OVERRIDE_INI, framework_url)

    if modifie:
        print(Fore.GREEN + Style.BRIGHT + f"\n[OK] {OVERRIDE_INI} mis à jour avec succès.")
        print(Fore.GREEN + f"  platform_packages = framework-arduinoespressif32 @ {framework_url}")
    else:
        print(Fore.GREEN + Style.BRIGHT + "\n[OK] Aucune mise à jour nécessaire.")

    print(Fore.CYAN + Style.BRIGHT + "\n======================================================\n")


if __name__ == "__main__":
    main()
