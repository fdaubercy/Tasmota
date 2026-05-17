# Script PlatformIO extra_script (post)
# Lit WIFI_IP_ADDRESS depuis tasmota/user_config_override.h pour le firmware courant,
# configure UPLOAD_PORT automatiquement, configure UPLOADCMD pour upload HTTP (après post_esp32.py),
# puis téléverse les fichiers Berry via /ufsd après redémarrage OTA.
# Ignoré en mode série (aucune IP trouvée dans user_config_override.h ou WIFI_IP_ADDRESS = 0.0.0.0).
#
# Utilisation dans platformio_tasmota_cenv.ini (doit être listé APRÈS les scripts de tasmota32_base) :
#
#   [env:mon-environnement]
#   extra_scripts = ${env:tasmota32_base.extra_scripts}
#                   post:outils_docs/scripts_python/ota-files-uploader.py

Import("env")

import os
import re
import time
from pathlib import Path

try:
    import requests
    from colorama import Fore
except ImportError as exc:
    print(f"ota-files-uploader : dépendance manquante ({exc}) — installation recommandée via pip")
    requests = None
    class _Fore:
        RED = YELLOW = GREEN = ""
    Fore = _Fore()


# ---------------------------------------------------------------------------
# Lecture de l'IP depuis user_config_override.h
# ---------------------------------------------------------------------------

def _firmware_define(env) -> str | None:
    """Retourne le define FIRMWARE_* le plus spécifique (dernier) dans les build_flags.

    Le flag hérité de l'environnement de base (ex. FIRMWARE_TASMOTA32) apparaît
    en premier ; le define propre à l'environnement est toujours ajouté après.
    """
    flags = " ".join(env.get("BUILD_FLAGS", []))
    matches = re.findall(r"-D\s*(FIRMWARE_\w+)", flags)
    return matches[-1] if matches else None


def _lire_ip_override(project_dir: str, firmware_define: str) -> str | None:
    """
    Parcourt tasmota/user_config_override.h et retourne WIFI_IP_ADDRESS
    définie dans le bloc #elif defined(<firmware_define>).
    Retourne None si le define ou l'IP est absent.
    """
    header = Path(project_dir) / "tasmota" / "user_config_override.h"
    if not header.is_file():
        return None

    lines = header.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_section = False
    depth = 0  # profondeur des #if/#ifdef imbriqués à l'intérieur du bloc cible

    for line in lines:
        s = line.strip()

        if not in_section:
            # Accepter #if defined(...) ou #elif defined(...)
            if re.match(
                rf"#\s*(?:el)?if\s+defined\s*\(\s*{re.escape(firmware_define)}\s*\)",
                s,
            ):
                in_section = True
                depth = 0
            continue

        # À l'intérieur du bloc cible ----------------------------------------
        if re.match(r"#\s*(?:ifdef|ifndef|if)\b", s):
            depth += 1
        elif re.match(r"#\s*endif\b", s):
            if depth == 0:
                break  # fin du bloc cible
            depth -= 1
        elif re.match(r"#\s*elif\b", s) and depth == 0:
            break  # branche suivante au même niveau

        ip_m = re.match(r'#\s*define\s+WIFI_IP_ADDRESS\s+"([\d.]+)"', s)
        if ip_m:
            return ip_m.group(1)

    return None


def _configurer_upload_ota(env) -> str | None:
    """
    Lit l'IP depuis user_config_override.h et configure UPLOAD_PORT.
    Retourne l'IP si trouvée et valide, None sinon.
    """
    define = _firmware_define(env)
    if not define:
        print(Fore.YELLOW + "ota-files-uploader : aucun define FIRMWARE_* dans build_flags, UPLOAD_PORT inchangé.")
        return None

    project_dir = env.subst("$PROJECT_DIR")
    ip = _lire_ip_override(project_dir, define)

    if not ip:
        print(Fore.YELLOW + f"ota-files-uploader : WIFI_IP_ADDRESS introuvable pour {define}.")
        return None

    if ip == "0.0.0.0":
        print(Fore.YELLOW + f"ota-files-uploader : WIFI_IP_ADDRESS = 0.0.0.0 (DHCP) pour {define}, UPLOAD_PORT inchangé.")
        return None

    upload_port = f"{ip}:80/u2?fsz="
    env.Replace(UPLOAD_PORT=upload_port)
    print(Fore.GREEN + f"ota-files-uploader : IP lue depuis user_config_override.h → UPLOAD_PORT = {upload_port}")
    return ip


# ---------------------------------------------------------------------------
# Téléversement des fichiers Berry après OTA
# ---------------------------------------------------------------------------

def _attendre_module(ip: str, timeout: int = 90) -> bool:
    """Attend que le module soit de nouveau disponible après redémarrage OTA."""
    url = f"http://{ip}/cm?cmnd=Status"
    print(Fore.YELLOW + f"  Attente du redémarrage de {ip} (timeout {timeout}s)...")
    time.sleep(15)
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                print(Fore.GREEN + f"  Module {ip} de nouveau disponible.")
                return True
        except Exception:
            pass
        time.sleep(2)
    print(Fore.RED + f"  Timeout : {ip} n'a pas répondu après {timeout}s.")
    return False


def _televerser_fichier(ip: str, chemin_local: str, nom_distant: str) -> bool:
    """Envoie un fichier unique vers http://<ip>/ufsd via POST multipart."""
    url = f"http://{ip}/ufsd"
    try:
        with open(chemin_local, "rb") as f:
            r = requests.post(
                url,
                files={"FS1": (nom_distant, f, "application/octet-stream")},
                timeout=20,
            )
        if r.status_code == 200:
            taille = Path(chemin_local).stat().st_size
            print(Fore.GREEN + f"    ✓ {nom_distant}  ({taille} octets)")
            return True
        else:
            print(Fore.RED + f"    ✗ {nom_distant}  — HTTP {r.status_code}")
            return False
    except Exception as exc:
        print(Fore.RED + f"    ✗ {nom_distant}  — {exc}")
        return False


def _extraire_ip(upload_port: str) -> str | None:
    """Extrait l'adresse IP depuis upload_port (ex. '192.168.0.43:80/u2?fsz=')."""
    m = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", upload_port or "")
    return m.group(1) if m else None


def upload_fichiers_berry(source, target, env):
    """Action post-upload : téléverse les fichiers Berry vers le module via /ufsd."""
    if requests is None:
        print(Fore.RED + "ota-files-uploader : module 'requests' introuvable, abandon.")
        return

    upload_port = env.get("UPLOAD_PORT", "")
    ip = _extraire_ip(upload_port)
    if not ip:
        return  # mode série, rien à faire

    try:
        option = env.GetProjectOption("custom_files_upload")
    except Exception:
        print(Fore.YELLOW + "ota-files-uploader : aucune entrée custom_files_upload, rien à téléverser.")
        return

    # Filtrer les entrées valides (ignorer no_files, URLs HTTP, lignes vides)
    entrees = []
    for ligne in option.splitlines():
        entree = ligne.split(";")[0].strip()
        if not entree or "no_files" in entree or re.match(r"https?://", entree):
            continue
        entrees.append(entree)

    if not entrees:
        return

    if not _attendre_module(ip):
        print(Fore.RED + "ota-files-uploader : module non disponible, abandon.")
        return

    print(Fore.GREEN + f"\nTéléversement des fichiers Berry vers http://{ip}/ufsd :")
    projet_dir = Path(env.subst("$PROJECT_DIR"))
    ok, ko = 0, 0

    for entree in entrees:
        chemin = Path(entree) if os.path.isabs(entree) else projet_dir / entree

        if chemin.is_dir():
            fichiers = sorted(f for f in chemin.rglob("*") if f.is_file())
            if not fichiers:
                print(Fore.YELLOW + f"    - {entree} : dossier vide, ignoré")
                continue
            for fichier in fichiers:
                if _televerser_fichier(ip, str(fichier), fichier.name):
                    ok += 1
                else:
                    ko += 1

        elif chemin.is_file():
            if _televerser_fichier(ip, str(chemin), chemin.name):
                ok += 1
            else:
                ko += 1

        else:
            print(Fore.YELLOW + f"    - {entree} : introuvable, ignoré")

    print()
    if ko == 0:
        print(Fore.GREEN + f"  {ok} fichier(s) Berry téléversé(s) avec succès.")
    else:
        couleur = Fore.YELLOW if ok > 0 else Fore.RED
        print(couleur + f"  {ok} succès, {ko} échec(s).")


# ---------------------------------------------------------------------------
# Configuration de UPLOADCMD pour upload HTTP (post-build, après post_esp32.py)
# ---------------------------------------------------------------------------

def _configurer_http_uploadcmd(_source, _target, env):
    """Configure UPLOADCMD pour l'upload HTTP OTA après le callback de post_esp32.py.

    Ce callback s'exécute après que post_esp32.py ait pu surcharger UPLOADCMD avec
    la commande esptool série. Si UPLOAD_PORT est une IP, on re-configure pour HTTP.
    """
    upload_port = env.subst("$UPLOAD_PORT")
    ip = _extraire_ip(upload_port)
    if not ip:
        return  # mode série, ne pas modifier UPLOADCMD

    try:
        import sys
        pio_tools = os.path.join(env.subst("$PROJECT_DIR"), "pio-tools")
        if pio_tools not in sys.path:
            sys.path.insert(0, pio_tools)
        import tasmotapiolib
        bin_file = tasmotapiolib.get_final_bin_path(env)
        bin_gz_file = bin_file.with_suffix(".bin.gz")
        uploader = os.path.join("pio-tools", "espupload.py")

        env.Replace(UPLOADERFLAGS="")
        env.Replace(UPLOADER=uploader)

        if bin_gz_file.exists():
            env.Replace(UPLOADCMD="$PYTHONEXE $UPLOADER -u $UPLOAD_PORT -f {}".format(bin_gz_file))
        elif bin_file.exists():
            env.Replace(UPLOADCMD="$PYTHONEXE $UPLOADER -u $UPLOAD_PORT -f {}".format(bin_file))
        else:
            env.Replace(UPLOADCMD="$PYTHONEXE $UPLOADER -u $UPLOAD_PORT -f $SOURCES")

        print(Fore.GREEN + f"ota-files-uploader : UPLOADCMD configuré pour upload HTTP OTA → {upload_port}")
    except Exception as exc:
        print(Fore.RED + f"ota-files-uploader : erreur configuration UPLOADCMD — {exc}")


# ---------------------------------------------------------------------------
# Point d'entrée : configuration de l'environnement + enregistrement des hooks
# ---------------------------------------------------------------------------

_configurer_upload_ota(env)
# Enregistré EN DERNIER sur $BUILD_DIR/${PROGNAME}.bin → s'exécute après post_esp32.py
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", _configurer_http_uploadcmd)
env.AddPostAction("upload", upload_fichiers_berry)
