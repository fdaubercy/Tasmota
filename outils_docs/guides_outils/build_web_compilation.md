# Build : ce qui fait recompiler

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

### Ce qui fait recompiler (et ce qui ne le fait plus)

- **Purge de `.pio/build`** (tous envs) : PlatformIO la fait dès que l'empreinte du projet change. Or elle change à
  chaque **changement d'env** (le `data_dir` de `platformio_override.ini` et les `_temp_be_*.c` de `berry_custom`
  dépendent de l'env), à chaque **changement de port COM** dans la page, et à toute édition d'un `.ini`. Après une
  purge, l'essentiel est recopié depuis le **cache objet** `.cache` (option `build_cache_dir`) au lieu d'être recompilé.
- **`tasmota.ino.cpp` et tout Berry** (175 fichiers sur la cuve : `berry_conf.h` inclut `my_user_config.h`, donc
  `user_config_override.h`) : depuis le 2026-11-01, un `CFG_HOLDER` inchangé les laisse reprendre du cache. `CFG_HOLDER` n'est plus
  incrémenté à chaque `pio run`, seulement si `user_config_override.h` (hors ligne `CFG_HOLDER`) a changé depuis le
  dernier incrément. Une carte qui a sa section `#elif defined(FIRMWARE_...)` dans ce fichier y porte son propre
  `CFG_HOLDER` (posé au premier incrément) : seule la partie commune du fichier ou sa section le font changer ; modifier la
  section d'une autre carte ne recharge pas ses réglages SECTION1 (le fichier ayant changé, elle recompile quand même). La sortie de pio l'annonce (« CFG_HOLDER inchangé : … » ou « CFG_HOLDER incrémenté : … »).
  Conséquence : un flash ne recharge les réglages SECTION1 (Wi-Fi, MQTT, syslog…) que si ce fichier a changé ; un
  « Effacer puis téléverser » les recharge toujours. Modifier un `_persist.json` ne recompile rien : il part avec le FS.
- **Le cache grossit sans fin** (17 Go le 2026-11-01) :
  `python outils_docs/scripts_python/maintenance/purge_cache_build.py --dry-run` montre ce que libérerait la
  suppression des objets inutilisés depuis 30 jours ; sans `--dry-run`, il les supprime (refus pendant un build).
  Le critère est la date de modification du fichier : SCons (`CacheDir.py::CacheRetrieveFunc`) la remet à jour à chaque
  reprise depuis le cache, donc elle vaut « dernière utilisation » (plan `temps-compilation`, 2026-11-01).
  Même purge sur la page Build (:7700), onglet Build : bouton « Purger le cache de compilation », avec confirmation.
- **Windows Defender** : `outils_docs/scripts_python/maintenance/exclusions_defender.ps1`, en administrateur,
  exclut `.pio`, `.cache` et `~/.platformio` de l'analyse en temps réel.
  Mesures et décisions de temps de build : `outils_docs/environnement/VIGILANCES_BUILD.md`.

### Le dossier `data_dir` : posé avant chaque `pio run`

Avant de lancer pio pour un env personnel, la page pose `data_dir` de `platformio_override.ini` sur le dossier de
l'env (`data/<lieu>/<carte>`), et le signale dans la sortie (« data_dir = … (posé par la page avant pio) ») quand il
change. PlatformIO lit ce fichier **avant** le pré-script qui le réécrit : sans cela, un « Construire le FS » lancé
seul prenait le dossier de l'env construit juste avant (le 2026-10-26, le P4 a reçu en OTA le FS de la cuve). Le
pré-script corrige aussi le lancement en cours (`PROJECT_DATA_DIR`), ce qui protège les `pio run` lancés depuis VS Code.
Pour le vérifier dans un journal : la ligne `copy_fs_image([... littlefs.bin], ["data\<lieu>\<carte>"])` doit
nommer le dossier de l'env construit.
