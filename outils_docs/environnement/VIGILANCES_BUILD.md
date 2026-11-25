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

## Temps de compilation : mesures et decisions

Chantier `temps-compilation` (2026-11-01), sans le recit. Le plan source est cite sur chaque puce.

- **Ce que coute un build de la cuve** (journaux de la page Build, 2026-11-01, `temps-compilation`) : 51 min quand `CFG_HOLDER`
  change (175 fichiers recompiles, 584 repris du cache) ; 23 min 24 s sans changement ; 14 min 57 s au retour sur la cuve apres
  le P4 (1 fichier compile, le reste repris de `.cache`) ; 29 min 39 s pour le P4 apres la cuve (177 compiles : ses propres
  defines). Le « 655 s pour 1 fichier » ecrit d'abord venait d'un build ECHOUE : ne pas retenir un chiffre d'un build coupe.
- **Dossier de build par env : decision « ne pas faire »** (2026-11-01, `temps-compilation`). La purge de `.pio/build` au
  changement d'env ne coute rien de mesurable, le cache objet rendant 771 objets sur 772. A rouvrir si un retour d'env
  depasse de 10 min un build sans changement ; il faudrait alors un `PLATFORMIO_BUILD_DIR` par env, pose par la page
  (~18 fichiers, dont le pre-build, qui code `.pio/build` en dur pour `copy_fs_image`).
- **Rejete** (2026-11-01, `temps-compilation`) : deux compilations en parallele (fichiers partages, 4 coeurs deja satures) et
  la coupure de la LTO (le firmware ne serait plus celui livre). Le port COM reste dans le cenv : le changer purge, c'est accepte.
- **Lien LTO** (2026-11-01, `temps-compilation`) : `build/post_lto_parallele.py` appelle bien `make -j4`, mais jamais plus
  d'un `lto1` n'a ete releve (~130 releves, liens de 338 a 556 s, `firmware.bin` identique). `make` a ete retire du build faute
  de gain ; la cause n'est pas trouvee.
- **Ce qui reste dans un build sans changement** (2026-11-01, `temps-compilation` ; preparation de 229 a 255 s) : LDF 110-180 s,
  solidification de `berry_custom` 46-100 s, controle `lib_ignore` 5-11 s a chaud et 49 s a froid, `dump-defines` et les 6
  solidifications en cache ~20 s. Tout sert, rien n'est a retirer. Le lien LTO s'y ajoute (5 a 9 min).
- **`buildfs`, `uploadfs` et `erase` ne passent pas par le LDF** (`builder/main.py::switch_off_ldf` de la plateforme 2026.10.50,
  2026-11-01, `temps-compilation`). Le controle `lib_ignore` est donc saute pour eux, et pour un `nobuild` : voir
  `verifie_lib_ignore.py::compile_rien`. La ligne « lib_ignore de <env> : controle saute… » le dit. Banc `test_verifie_lib_ignore.py`.

## lib_ignore : scan des dependances (LDF)

Chantiers `lib-ignore-cuve` (2026-10-31) et `lib-ignore-envs` (2026-10-31 au 2026-11-02) ; le plan source est cite sur chaque puce.

- **Pourquoi** (`lib-ignore-cuve`) : le LDF est en mode `chain` (`platformio.ini`, `lib_ldf_mode`) : il ne lit pas les `#ifdef`,
  tout `#include` present tire sa bibliotheque, meme si la fonction est desactivee, et les bibliotheques du graphe sont aussi
  compilees. `lib_ldf_mode = off` est ecarte (liste de ~120 bibliotheques a tenir a la main), `chain+` et `deep` sont plus lents.
- **Ou** (`lib-ignore-envs`) : section `[lib_inutiles]` du cenv (`commun`, `sans_ecran`, listes propres a quelques envs), reprise
  par les 9 envs ESP32 personnels. Le `lib_ignore` d'un env REMPLACE celui qu'il herite : repartir de l'herite. Piscine (ESP8266) hors champ.
- **Garde** (`lib-ignore-envs`) : `build/verifie_lib_ignore.py` tourne au pre-build, avant le scan, et ne controle que ce que le
  cenv ajoute au premier ancetre de l'amont. Il refuse une bibliotheque incluse sous une garde vraie ou incertaine ;
  `--propose <env>` donne la liste ignorable. Un defaut du controle lui-meme ne bloque jamais le build (un build du
  differentiel avait ete coupe pendant une edition du script, importe par le pre-script). Cout releve : 7 a 57 s (168 s sur
  la cave ESP32, cause non cherchee).
- **Piege paye plusieurs fois** (`lib-ignore-cuve`, `lib-ignore-envs`, 2026-10-31) : l'en-tete d'une bibliotheque « inutile »
  peut etre inclus par un AUTRE module sous une garde active : `esp_wireguard_tasmota` par Berry crypto
  (`xdrv_52_3_berry_crypto.ino`), `ESPFtpServer` (FTP actif sur 7 cartes), `ESP8266SAM` et `mp3_shine_esp32` (audio I2S du P4).
  Verifier les inclusions de TOUS ses en-tetes, pas seulement de son pilote. Piege du controle lui-meme : retirer les
  commentaires en deux passes laissait `//*****` effacer la suite d'un fichier (`lecture_gardes.py::sans_commentaires`, un seul
  passage) ; une macro du framework (`ESP_IDF_VERSION_MAJOR`) n'est pas fausse.
- **Matter, SendMail et KNX restent actifs** (`lib-ignore-cuve`, decision du 2026-10-31) : jamais dans un `lib_ignore`, jamais
  coupes par `#undef`. Les autres fonctions actives mais inutiles (IR, DALI, TM1638, LoRa, iBeacon, Berry Animation, SEN5X)
  n'ont pas ete coupees.
- **Mesures** (`lib-ignore-cuve`, `lib-ignore-envs`) : cuve, 138 → 80 bibliotheques compatibles, scan 21 min 42 → 7 min 36,
  pre-build 27 min 17 → 14 min 12 (puis 3 min 40 a 10 min 51 avec les reglages SCons du 2026-11-01) ; firmware identique
  (−80 o, RAM egale). Gain non isole : le temoin P4 sans `lib_ignore` gagnait −21 % le meme soir, et l'etat de la machine
  (memoire, cache) pese autant ; le gain n'est prouve que sur la cuve. Les 6 autres envs n'avaient aucun journal « avant ».
- **Ce que `lib_ignore` ne touche pas** (`lib-ignore-cuve`, mesure du 2026-10-31) : la solidification Berry (~5 min) et la LTO (~7 min 30).
- **Windows Defender** (`lib-ignore-cuve`, 2026-10-31) : l'exclusion n'a pas raccourci le scan (plus de 29 min avec exclusion,
  sur une machine a 1,5 Go libres : la memoire dominait). Gain non demontre ; le script reste fourni (`NOUVEAU_POSTE.md`).
- **Editer le cenv** (`lib-ignore-cuve`) : verifier qu'aucun build ne tourne dans la MEME commande que l'edition.
