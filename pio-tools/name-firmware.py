Import("env")

import os
import shutil
import pathlib
import tasmotapiolib
from os.path import join
from colorama import Fore, Back, Style


def bin_map_copy(source, target, env):
    firsttarget = pathlib.Path(target[0].path)

    # récupérer les emplacements et noms de fichiers selon la variante
    map_file = os.path.normpath(str(tasmotapiolib.get_final_map_path(env)))
    bin_file = os.path.normpath(str(tasmotapiolib.get_final_bin_path(env)))
    one_bin_file = bin_file
    firmware_name = env.subst("$BUILD_DIR/${PROGNAME}.bin")
    if env["PIOPLATFORM"] == "espressif32":
        if("safeboot" in firmware_name):
            SAFEBOOT_SIZE = firsttarget.stat().st_size
            if SAFEBOOT_SIZE > 851967:
                print(Fore.RED + "!!! La taille du safeboot Tasmota est trop grande : {} octets. Taille maximum : 851967 octets !!! ".format(
                        SAFEBOOT_SIZE
                    )
                )
        if("safeboot" not in firmware_name):
            factory_tmp = pathlib.Path(firsttarget).with_suffix("")
            factory = os.path.normpath(str(factory_tmp.with_suffix(factory_tmp.suffix + ".factory.bin")))
            one_bin_tmp = pathlib.Path(bin_file).with_suffix("")
            one_bin_file = os.path.normpath(str(one_bin_tmp.with_suffix(one_bin_tmp.suffix + ".factory.bin")))

    # vérifier si les nouveaux fichiers cibles existent et les supprimer si nécessaire
    for f in [map_file, bin_file, one_bin_file]:
        f_path = pathlib.Path(f)
        if f_path.is_file():
            f_path.unlink()

    # copier firmware.bin et map vers la destination finale
    shutil.copy(str(firsttarget), bin_file)
    if env["PIOPLATFORM"] == "espressif32":
        # le fichier map est nécessaire ultérieurement pour firmware-metrics.py
        shutil.copy(os.path.normpath(str(tasmotapiolib.get_source_map_path(env))), map_file)
        if("safeboot" not in firmware_name):
            shutil.copy(factory, one_bin_file)
    else:
        map_firm = os.path.normpath(join(env.subst("$BUILD_DIR"), "firmware.map"))
        shutil.copy(os.path.normpath(str(tasmotapiolib.get_source_map_path(env))), map_firm)
        shutil.move(os.path.normpath(str(tasmotapiolib.get_source_map_path(env))), map_file)

silent_action = env.Action(bin_map_copy)
silent_action.strfunction = lambda target, source, env: '' # astuce pour taire la sortie de commande scons
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", silent_action)
