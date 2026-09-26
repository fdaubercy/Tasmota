"""
Parallelise l'etape LTRANS de l'edition de liens LTO.

Le framework pioarduino compile avec `-flto=auto` mais LIE avec un `-flto` nu
(tools/esp32-arduino-libs/<mcu>/pioarduino-build.py, LINKFLAGS). Sans nombre de jobs,
GCC fait l'optimisation de lien en serie :
    lto-wrapper.exe: warning: using serial compilation of 33 LTRANS jobs
soit l'essentiel des ~25 min d'un build incremental de Tasmota.

Ce script remplace ce `-flto` par `-flto=auto` (un job par coeur). Il doit etre charge
en `post:` : les LINKFLAGS du framework n'existent qu'une fois le builder principal passe,
et pour GCC c'est la DERNIERE option `-flto` qui l'emporte.

N'affecte que la ligne de lien : aucun .o n'est recompile, seul le premier lien est refait.
Pour revenir en arriere : retirer la ligne `post:` de platformio_override.ini.
"""
Import("env")

from colorama import Fore

avant = list(env.get("LINKFLAGS", []))
apres = ["-flto=auto" if f == "-flto" else f for f in avant]

if apres != avant:
    env.Replace(LINKFLAGS=apres)
    print(Fore.GREEN + "✔ LTO : edition de liens parallelisee (-flto -> -flto=auto)")
