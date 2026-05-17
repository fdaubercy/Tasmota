# From: https://github.com/letscontrolit/ESPEasy/blob/mega/tools/pio/post_esp32.py
# Thanks TD-er :)

# Thanks @staars for safeboot and auto resizing LittleFS code and enhancements

# Combine des fichiers bin séparés avec leurs décalages respectifs en un seul fichier
# Ce fichier unique doit ensuite être flashé sur un nœud ESP32 au décalage 0.
#
# Implémentation originale : Bartłomiej Zimoń (@uzi18)
#
# Remerciements spéciaux à @Jason2866 pour l'aide au débogage du flashage >4MB
# Merci à @jesserockz (esphome) pour l'adaptation à l'utilisation de esptool.py avec merge_bin
#
# Disposition typique du fichier généré :
#    Décalage | Fichier
# -  0x1000 | ~\.platformio\packages\framework-arduinoespressif32\tools\sdk\esp32\bin\bootloader_dout_40m.bin
# -  0x8000 | ~\Tasmota\.pio\build\<env name>\partitions.bin
# -  0xe000 | ~\.platformio\packages\framework-arduinoespressif32\tools\partitions\boot_app0.bin
# - 0x10000 | ~\Tasmota\<variants_dir>/<env name>-safeboot.bin
# - 0xe0000 | ~\Tasmota\.pio\build\<env name>/firmware.bin
# - 0x3b0000| ~\Tasmota\.pio\build\<env name>/littlefs.bin

from genericpath import exists
import os
from os.path import join, getsize
import re
import csv
from littlefs import LittleFS
import requests
import shutil
import subprocess
import codecs
from pathlib import Path
from colorama import Fore
from SCons.Script import COMMAND_LINE_TARGETS

env = DefaultEnvironment()
platform = env.PioPlatform()
config = env.GetProjectConfig()
variants_dir = env.BoardConfig().get("build.variants_dir", "")
variant = env.BoardConfig().get("build.variant", "")
sections = env.subst(env.get("FLASH_EXTRA_IMAGES"))
chip = env.get("BOARD_MCU")
mcu_build_variant = env.BoardConfig().get("build.variant", "").lower()
flag_custom_sdkconfig = config.has_option("env:"+env["PIOENV"], "custom_sdkconfig")
flag_board_sdkconfig = env.BoardConfig().get("espidf.custom_sdkconfig", "")

# Copie les firmwares safeboot en place lors de l'exécution dans Github
github_actions = os.getenv('GITHUB_ACTIONS')

FRAMEWORK_DIR = platform.get_package_dir("framework-arduinoespressif32")
if github_actions and os.path.exists(os.path.normpath(os.path.join(".", "firmware", "firmware"))):
    dest_dir = os.path.normpath(os.path.join(os.sep, "home", "runner", ".platformio", "packages", "framework-arduinoespressif32", "variants", "tasmota"))
    shutil.copytree(os.path.normpath(os.path.join(".", "firmware", "firmware")), dest_dir, dirs_exist_ok=True)
    if variants_dir:
        shutil.copytree(os.path.normpath(os.path.join(".", "firmware", "firmware")), os.path.normpath(variants_dir), dirs_exist_ok=True)

# Copie pins_arduino.h dans le dossier des variantes
if variants_dir:
    mcu_build_variant_path = os.path.normpath(join(FRAMEWORK_DIR, "variants", mcu_build_variant, "pins_arduino.h"))
    custom_variant_build = os.path.normpath(join(env.subst("$PROJECT_DIR"), variants_dir , mcu_build_variant, "pins_arduino.h"))
    os.makedirs(os.path.normpath(join(env.subst("$PROJECT_DIR"), variants_dir , mcu_build_variant)), exist_ok=True)
    shutil.copy(mcu_build_variant_path, custom_variant_build)

if not variants_dir:
    variants_dir = os.path.normpath(join(FRAMEWORK_DIR, "variants", "tasmota"))
    env.BoardConfig().update("build.variants_dir", variants_dir)

def normalize_paths(cmd):
    for i, arg in enumerate(cmd):
        if isinstance(arg, str) and '/' in arg:
            cmd[i] = os.path.normpath(arg)
    return cmd

# Détecte la taille du flash ESP32 et met à jour la configuration de la carte si nécessaire
def esp32_detect_flashsize():
    uploader = env.subst("$UPLOADER")
    if not "upload" in COMMAND_LINE_TARGETS:
        return "4MB",False
    if not "esptool" in uploader:
        return "4MB",False
    else:
        esptool_flags = ["flash-id"]
        esptool_cmd = [env.subst("$OBJCOPY")] + esptool_flags
        try:
            output = subprocess.run(esptool_cmd, capture_output=True).stdout.splitlines()
            for l in output:
                if l.decode().startswith("Taille de la mémoire flash détectée: "):
                    size = (l.decode().split(": ")[1])
                    print("Taille du flash obtenue :", size)
                    stored_flash_size_mb = env.BoardConfig().get("upload.flash_size")
                    stored_flash_size = int(stored_flash_size_mb.split("MB")[0]) * 0x100000
                    detected_flash_size = int(size.split("MB")[0]) * 0x100000
                    if detected_flash_size > stored_flash_size:
                        env.BoardConfig().update("upload.flash_size", size)
                        return size, True
            return "4MB",False
        except subprocess.CalledProcessError as exc:
            print(Fore.YELLOW + "Les informations sur le processeur ont échoué. " + str(exc))
            return "4MB",False

flash_size_from_esp, flash_size_was_overridden = esp32_detect_flashsize()

# Modifier le fichier partitions.bin pour mettre à jour la taille de la partition spiffs
def patch_partitions_bin(size_string):
    partition_bin_path = os.path.normpath(join(env.subst("$BUILD_DIR"), "partitions.bin"))
    with open(partition_bin_path, 'r+b') as file:
        binary_data = file.read(0xb0)
        import hashlib
        bin_list = list(binary_data)
        size_string = int(size_string[2:],16)
        size_string = f"{size_string:08X}"
        size = codecs.decode(size_string, 'hex_codec') # 0xc50000 -> [00,c5,00,00]
        bin_list[0x89] = size[2]
        bin_list[0x8a] = size[1]
        bin_list[0x8b] = size[0]
        result = hashlib.md5(bytes(bin_list[0:0xa0]))
        partition_data = bytes(bin_list) + result.digest()
        file.seek(0)
        file.write(partition_data)
        print("Nouveau hachage de partition:",result.digest().hex())

# Crée le nom du fichier en fonction de la puce
def esp32_create_chip_string(chip):
    tasmota_platform_org = env.subst("$BUILD_DIR").split(os.path.sep)[-1]
    tasmota_platform = tasmota_platform_org.split('-')[0]
    if "tasmota" + chip[3:] not in tasmota_platform: # check + fix for a valid name like 'tasmota' + '32c3'
        tasmota_platform = "tasmota" + chip[3:]
        if "-DUSE_USB_CDC_CONSOLE" not in env.BoardConfig().get("build.extra_flags"):
            print(Fore.YELLOW + "Convention d'appellation inattendue dans cet environnement de compilation :" + Fore.RED, tasmota_platform_org)
            print(Fore.YELLOW + "Nom attendu de l'environnement de compilation, par exemple : " + Fore.GREEN + "'tasmota" + chip[3:] + "-ce-que-vous-voulez'")
            print(Fore.YELLOW + "Veuillez corriger votre environnement de compilation actuel afin d'éviter tout comportement indéfini lors du processus de compilation !!")
    return tasmota_platform

# Créer le système de fichiers après la compilation du firmware ESP32
def esp32_build_filesystem(fs_size):
    files = env.GetProjectOption("custom_files_upload").splitlines()
    num_entries = len([f for f in files if f.strip()])
    filesystem_dir = os.path.normpath(join(env.subst("$BUILD_DIR"), "littlefs_data"))
    if not os.path.exists(filesystem_dir):
        os.makedirs(filesystem_dir)
        # print("-------------------" + env.subst("$BUILD_DIR") + "-------------------")
    if num_entries > 1:
        print()
        print(Fore.GREEN + "Nous allons créer le système de fichiers avec les fichiers suivants: ")
        print()
        
    for file in files:
        # Remove leading and trailing whitespace, ignore empty lines
        file = file.strip()
        if not file:
            continue

        if "no_files" in file:
            print(Fore.RED + "Pas de fichiers dans le dossier '" + file + "' !")
            continue
        # Remote URL
        if file.startswith(("http://", "https://")):
            response = requests.get(file.split(" ")[0])
            if response.ok:
                target = os.path.normpath(join(filesystem_dir, file.split(os.path.sep)[-1]))
                if len(file.split(" ")) > 1:
                    target = os.path.normpath(join(filesystem_dir, file.split(" ")[1]))
                    print("Renomme",(file.split(os.path.sep)[-1]).split(" ")[0],"en",file.split(" ")[1])
                else:
                    print(file.split(os.path.sep)[-1])
                open(target, "wb").write(response.content)
            else:
                print(Fore.RED + "Echec du download: ",file)
            continue
        # Local path (relative to PROJECT_DIR or absolute)
        file = file if os.path.isabs(file) else os.path.normpath(join(env.subst("$PROJECT_DIR"), file))
        if os.path.isdir(file):
            print(f"{file}/ (répertoire)")
            shutil.copytree(file, filesystem_dir, dirs_exist_ok=True)
        else:
            print(file)
            shutil.copy(file, filesystem_dir)
            
    if not os.listdir(filesystem_dir):
        print(Fore.RED + "Pas de fichiers ajoutés -> Nous ne créerons pas 'littlefs.bin' & n'écraserons pas le fs de partition!")
        return False
    
    # Utilise littlefs-python
    output_file = join(env.subst("$BUILD_DIR"), "littlefs.bin")

    # Analyser fs_size (peut être une chaîne hexadécimale comme "0x2f0000")
    if isinstance(fs_size, str):
        if fs_size.startswith("0x"):
            fs_size_bytes = int(fs_size, 16)
        else:
            fs_size_bytes = int(fs_size)
    else:
        fs_size_bytes = int(fs_size)
    
    # Paramètres LittleFS pour ESP32
    block_size = 4096
    block_count = fs_size_bytes // block_size

    # Créer une instance LittleFS avec la version disque 2.0 pour Tasmota
    fs = LittleFS(
        block_size=block_size,
        block_count=block_count,
        disk_version=0x00020000,
        mount=True
    )
    
    # Ajouter tous les fichiers depuis filesystem_dir
    source_path = Path(filesystem_dir)
    for item in source_path.rglob("*"):
        rel_path = item.relative_to(source_path)
        if item.is_dir():
            fs.makedirs(rel_path.as_posix(), exist_ok=True)
        else:
            # S'assurer que les répertoires parents existent
            if rel_path.parent != Path("."):
                fs.makedirs(rel_path.parent.as_posix(), exist_ok=True)
            # Copier le fichier
            with fs.open(rel_path.as_posix(), "wb") as dest:
                dest.write(item.read_bytes())
    
    # Écrire l'image du système de fichiers
    with open(output_file, "wb") as f:
        f.write(fs.context.buffer)

    print()
    print(Fore.GREEN + f"Image LittleFS créée : {output_file}")
    return True

def esp32_fetch_safeboot_bin(tasmota_platform):
    safeboot_fw_url = "http://ota.tasmota.com/tasmota32/release/" + tasmota_platform + "-safeboot.bin"
    safeboot_fw_name = os.path.normpath(join(variants_dir, tasmota_platform + "-safeboot.bin"))
    if(exists(safeboot_fw_name)):
        print(Fore.GREEN + "Le fichier binaire safeboot existe déjà dans le répertoire des variantes !")
        return True
    print()
    print(Fore.GREEN + "Téléchargement du fichier binaire safeboot depuis l'URL :")
    print(Fore.BLUE + safeboot_fw_url)
    try:
        response = requests.get(safeboot_fw_url)
        open(safeboot_fw_name, "wb").write(response.content)
        print(Fore.GREEN + "Binaire Safeboot écrit dans le chemin des variantes :")
        print(Fore.BLUE + safeboot_fw_name)
        return True
    except:
        print(Fore.RED + "Le téléchargement du fichier binaire safeboot a échoué. Veuillez vérifier votre connexion Internet.")
        print(Fore.RED + "Creation de " + tasmota_platform + "-factory.bin impossible !")
        print(Fore.YELLOW + "Sans Internet " + Fore.GREEN + tasmota_platform + "-safeboot.bin" + Fore.YELLOW + " doit être compilé avant " + Fore.GREEN + tasmota_platform)
        return False

def esp32_copy_new_safeboot_bin(tasmota_platform,new_local_safeboot_fw):
    print("Copie du nouveau firmware safeboot local dans le répertoire des variantes -> utilisé pour les opérations de flashage ultérieures")
    safeboot_fw_name = os.path.normpath(join(variants_dir, tasmota_platform + "-safeboot.bin"))
    if os.path.exists(variants_dir):
        try:
            shutil.copy(new_local_safeboot_fw, safeboot_fw_name)
            return True
        except:
            return False

# Lit et affiche les partitions depuis le fichier CSV
# Construit le binaire combiné pour le flashage en série
def esp32_create_combined_bin(source, target, env):
    #print("Generating combined binary for serial flashing")
    # The offset from begin of the file where the app0 partition starts
    # This is defined in the partition .csv file
    # factory_offset = -1      # error code value - currently unused
    app_offset = 0x10000     # default value for "old" scheme
    fs_offset = -1           # error code value

    with open(env.BoardConfig().get("build.partitions")) as csv_file:
        print()
        print("Lit les partitions depuis ",env.BoardConfig().get("build.partitions"))
        print("--------------------------------------------------------------------")
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                print(f'{",  ".join(row)}')
                line_count += 1
            else:
                print(f'{row[0]}   {row[1]}   {row[2]}   {row[3]}   {row[4]}')
                line_count += 1
                if(row[0] == 'app0'):
                    app_offset = int(row[3],base=16)
                # elif(row[0] == 'factory'):
                #     factory_offset = int(row[3],base=16)
                elif(row[0] == 'spiffs'):
                    partition_size = row[4]
                    if flash_size_was_overridden:
                        print(f"Remplacera la taille fixe de la partition FS à partir de {env.BoardConfig().get('build.partitions')}: {partition_size} ...")
                        partition_size =  hex(int(flash_size_from_esp.split("MB")[0]) * 0x100000 - int(row[3],base=16))
                        print(f"... avec une taille maximale calculée à partir des connexions {env.get('BOARD_MCU')}: {partition_size}")
                        patch_partitions_bin(partition_size)
                    if esp32_build_filesystem(partition_size):
                        fs_offset = int(row[3],base=16)

    print()
    new_file_name = os.path.normpath(env.subst("$BUILD_DIR/${PROGNAME}.factory.bin"))
    firmware_name = os.path.normpath(env.subst("$BUILD_DIR/${PROGNAME}.bin"))
    tasmota_platform = esp32_create_chip_string(chip)

    if not os.path.exists(variants_dir):
        os.makedirs(variants_dir)
    if "safeboot" in firmware_name:
        s_flag = esp32_copy_new_safeboot_bin(tasmota_platform,firmware_name)
    else:
        s_flag = esp32_fetch_safeboot_bin(tasmota_platform)

    if s_flag:  # vérifier si le firmware safeboot existe
        flash_size = env.BoardConfig().get("upload.flash_size", "4MB")
        flash_mode = env["__get_board_flash_mode"](env)
        flash_freq = env["__get_board_f_flash"](env)

        cmd = [
            "--chip",
            chip,
            "merge-bin",
            "-o",
            new_file_name,
            "--flash-mode",
            flash_mode,
            "--flash-freq",
            flash_freq,
            "--flash-size",
            flash_size,
        ]
        # Platformio estime l'espace flash utilisé pour stocker le firmware.
        # Cette estimation est inexacte. Obtenir l'utilisation exacte du flash du firmware
        # depuis l'outil size (même valeur que la ligne "Flash:" de PlatformIO)
        max_size = env.BoardConfig().get("upload.maximum_size", 1)
        elf_file = os.path.normpath(env.subst("$BUILD_DIR/${PROGNAME}.elf"))
        fw_size = 0
        size_cmd = env.subst("$SIZETOOL") + " -A -d " + elf_file
        size_output = subprocess.check_output(size_cmd, shell=True, text=True)
        size_regexp = re.compile(env.get("SIZEPROGREGEXP"))
        for line in size_output.splitlines():
            m = size_regexp.match(line)
            if m:
                fw_size += int(m.group(1))
        if (fw_size > max_size):
            raise Exception(Fore.RED + "Fichier firmware trop lourd: %d > %d" % (fw_size, max_size))

        print()
        print("    Décalage | Fichier")
        for section in sections:
            sect_adr, sect_file = section.split(" ", 1)
            print(f" -  {sect_adr.ljust(8)} | {sect_file}")
            cmd += [sect_adr, sect_file]

        # firmware "principal" vers app0 - obligatoire, sauf si on vient de compiler un nouveau safeboot localement
        if ("safeboot" not in firmware_name):
            print(f" -  {hex(app_offset).ljust(8)} | {firmware_name}")
            cmd += [hex(app_offset), firmware_name]

        else:
            print()
            print(Fore.GREEN + "Téléversez uniquement le nouveau binaire safeboot")

        upload_protocol = env.subst("$UPLOAD_PROTOCOL")
        if(upload_protocol == "esptool") and (fs_offset != -1):
            fs_bin = os.path.normpath(join(env.subst("$BUILD_DIR"), "littlefs.bin"))
            if exists(fs_bin):
                before_reset = env.BoardConfig().get("upload.before_reset", "default-reset")
                after_reset = env.BoardConfig().get("upload.after_reset", "hard-reset")
                print(f" -  {hex(fs_offset).ljust(8)} | {fs_bin}")
                print()
                cmd += [hex(fs_offset), fs_bin]
                env.Replace(
                UPLOADERFLAGS=[
                "--chip", chip,
                "--port", '"$UPLOAD_PORT"',
                "--baud", "$UPLOAD_SPEED",
                "--before", before_reset,
                "--after", after_reset,
                "write-flash", "-z",
                "--flash-mode", "${__get_board_flash_mode(__env__)}",
                "--flash-freq", "${__get_board_f_flash(__env__)}",
                "--flash-size", flash_size
                ],
                UPLOADCMD='"$OBJCOPY" $UPLOADERFLAGS ' + " ".join(normalize_paths(cmd[7:]))
                )
                print(Fore.GREEN + "Utilisera une commande de téléchargement personnalisée pour l'opération de flashage afin d'ajouter le système de fichiers défini pour cette cible de compilation.")
                print()

        if("safeboot" not in firmware_name):
            cmdline = [env.subst("$OBJCOPY")] + normalize_paths(cmd)
            # print('Command Line: %s' % cmdline)
            result = subprocess.run(cmdline, text=True, check=False, stdout=subprocess.DEVNULL)
            if result.returncode != 0:
                print(Fore.RED + f"La création du firmware par esptool a échoué avec le code de sortie: {result.returncode}")

silent_action = env.Action(esp32_create_combined_bin)
silent_action.strfunction = lambda target, source, env: '' # hack to silence scons command output
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", silent_action)
