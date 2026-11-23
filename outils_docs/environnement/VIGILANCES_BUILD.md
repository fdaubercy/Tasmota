# Vigilances de build

Tire de `CLAUDE.md` le 2026-11-23 (plan `binomes-berry`, A11). Les regles qui s'appliquent a chaque session
restent resumees dans `CLAUDE.md` § Vigilances de build ; ici, le detail et les mesures.

## Vigilances de build

- `tasmota.ino.cpp` portait en ligne 1 un nom de fichier temporaire aleatoire, donc n'etait jamais repris du cache :
  `build/ino_stable.py` rend ce nom fixe (mesure du 2026-11-01 sur la cuve, rien de modifie : 355 s au lieu de 771 s).
- Le pre-script pose `env.Decider("content-timestamp")` et `SetOption("implicit_cache", 1)` : ~20 s au lieu de ~230 s de
  parcours SCons sans rien compiler (mesure du 2026-11-01). Limite d'`implicit_cache` : un NOUVEL en-tete qui en masque un
  autre de meme nom plus loin dans les `-I` n'est vu qu'a la modification d'un fichier de la chaine (banc `build/test_scons_cache.py`).
- `gen-berry-structures` reecrit `lib/libesp32/berry/generate/` APRES le LDF : avec `implicit_cache`, SCons gardait la date lue avant et reprenait du cache un `be_string.c.o` sans les nouveaux textes (`undefined reference to be_const_str_...`, 2026-11-02 ; masque jusque-la par le `CFG_HOLDER` qui changeait a chaque build). Corrige par `clear_memoized_values()` dans `build/post_lto_parallele.py`, banc `build/test_scons_cache.py`.
- `firmware.elf` ne passe pas par le cache objet : repris du cache, il arrive sans `firmware.map`, et
  `pio-tools/name-firmware.py` echoue par `*** [firmware.bin]` sans message. Un retour sur un env refait donc son edition de liens.
- Un build reecrit `platformio_override.ini` (`adapteParametresPlatformio_override`), et
  `tasmota/user_config_override.h` (`increment_config_holder`) **seulement** si ce `.h` (hors ligne `CFG_HOLDER`) a
  change depuis le dernier increment, et pour un `pio run` qui compile le firmware (`build/cfg_holder.py`, decide le
  2026-11-01 ; etat par env dans `%LOCALAPPDATA%\outils_tasmota\build\cfg_holder.json` ; le `_persist.json`
  n'y entre pas, retire a la demande de l'utilisateur). Depuis le soir du 2026-11-01, une carte qui a sa section
  `#elif defined(FIRMWARE_...)` y porte SON `CFG_HOLDER` (lignes `#undef`/`#define` posees par
  `cfg_holder.py::incremente_section`) et n'incremente que si la partie commune du `.h` ou SA section a change : modifier
  la section d'une carte ne recharge plus SECTION1 sur les autres (elles recompilent quand meme, le fichier a change). Avant, `CFG_HOLDER` changeait a chaque run : `tasmota.ino.cpp` et
  tout Berry, soit 175 fichiers sur la cuve, n'etaient jamais repris du cache objet (`.cache`, `build_cache_dir`), car
  `berry_conf.h` inclut `my_user_config.h`. Le pre-script force aussi la
  refabrication de `firmware.bin` (`AlwaysBuild`) : sinon la post-action de `pio-tools/post_esp32.py` ne joindrait plus
  le FS a l'upload serie. Sauvegarder avant une serie de builds experimentaux.
- **Ne jamais lancer un build en parallele de celui de l'utilisateur** : deux `pio` ecrivant
  `tasmota/tasmota.ino.cpp` se plantent mutuellement.
- **IntelliSense ne doit jamais se reconstruire pendant un build** (constate le 2026-10-01) :
  `scons __idedata`, lance par l'extension PlatformIO/pioarduino quand `platformio_override.ini`
  change, execute `pio-tools/solidify-from-url.py`, dont `cleanFolder()` efface les
  `_temp_be_*.c` et reecrit `modules.h` de `lib/libesp32/berry_custom` pour l'env actif de
  l'IDE. Symptome : `TypeError : unsupported operand type(s) for -: 'float' and 'NoneType'`
  sur un `_temp_be_<module>_lib.c` ; pire, un build peut reussir avec la table de modules d'un
  autre env. Parade : `"platformio-ide.autoRebuildAutocompleteIndex": false` dans le **profil
  VS Code actif** (non versionne, voir `outils_docs/environnement/NOUVEAU_POSTE.md`). Index a reconstruire a la
  main, hors build.
- Pour surveiller un build en redirigeant la sortie, poser `PYTHONIOENCODING=utf-8` :
  sinon Python passe en cp1252, le `✔` du script pre-build tue le thread de recopie de pio,
  et **toute** la sortie est perdue. Ne pas « corriger » le script de l'utilisateur pour ca.
- **Aucune cible PlatformIO pendant un build, meme un outil** (constate le 2026-10-10) : les
  cibles Custom « Sniffeur ModBus », « Sniffeur MQTT », « Serveur syslog » sont des `pio run`.
  Avant toute chose, `pio run` compare l'empreinte du projet a `.pio/build/project.checksum`
  et, si elle differe, **supprime tout `.pio/build`**, tous envs compris
  (`platformio/run/helpers.py::clean_build_dir`). L'empreinte inclut la liste des `.c/.h` de `lib/`
  (`project/helpers.py::compute_project_checksum`), or le pre-build regenere les `_temp_be_*.c` de
  `berry_custom` **selon l'env** : changer d'env change l'empreinte. Symptome : un
  `erase_upload` P4 lance a 15:14, la cible sniffeur (env cave) a 15:37:31, `.pio/build`
  vide a 15:37:39, puis `*** [.pio\build\<env>\libXXX] ... Le chemin d'acces specifie est
  introuvable`. Le pre-build du sniffeur reecrit aussi `modules.h` en plein build (piege
  IntelliSense ci-dessus). Parade : pendant un build, lancer ces outils **hors PlatformIO**,
  directement par `python outils_docs/scripts_python/outils_pc/<outil>.py` (ex. `sniffeur_modbus.py
  --port auto --debit 19200 --http 7300`).
