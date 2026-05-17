Import('env')


import os
import pathlib
import shutil
from colorama import Fore, Back, Style

# S'assurer que le répertoire des variantes est correctement formaté selon l'OS
# Nécessaire pour éviter des problèmes de gestion des chemins dans différents environnements
variants_dir = env.BoardConfig().get("build.variants_dir", "")
if variants_dir:
    if os.name == "nt":
        variants_dir = variants_dir.replace("/", "\\")
        env.BoardConfig().update("build.variants_dir", variants_dir)
    else:
        variants_dir = variants_dir.replace("\\", "/")
        env.BoardConfig().update("build.variants_dir", variants_dir)

project_dir = os.path.normpath(env["PROJECT_DIR"])
if " " in project_dir:
    print(Fore.RED + "*** Espace(s) dans le chemin du projet, des problèmes/erreurs inattendus peuvent survenir ***")

# copier tasmota/user_config_override_sample.h vers tasmota/user_config_override.h
uc_override = pathlib.Path(os.path.normpath("tasmota/user_config_override.h"))
uc_override_sample = pathlib.Path(os.path.normpath("tasmota/user_config_override_sample.h"))
if uc_override.is_file():
    print(Fore.GREEN + "*** utilise le user_config_override.h fourni comme prévu ***")
else:
    shutil.copy(str(uc_override_sample), str(uc_override))

# copier platformio_override_sample.ini vers platformio_override.ini
pio_override = pathlib.Path(os.path.normpath("platformio_override.ini"))
pio_override_sample = pathlib.Path(os.path.normpath("platformio_override_sample.ini"))
if pio_override.is_file():
    print(Fore.GREEN + "*** utilise le platformio_override.ini fourni comme prévu ***")
else:
    shutil.copy(str(pio_override_sample), str(pio_override))

# copier platformio_tasmota_cenv_sample.ini vers platformio_tasmota_cenv.ini
pio_cenv = pathlib.Path(os.path.normpath("platformio_tasmota_cenv.ini"))
pio_cenv_sample = pathlib.Path(os.path.normpath("platformio_tasmota_cenv_sample.ini"))
if pio_cenv.is_file():
    print(Fore.GREEN + "*** utilise le platformio_tasmota_cenv.ini fourni comme prévu ***")
else:
    shutil.copy(str(pio_cenv_sample), str(pio_cenv))
