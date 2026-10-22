# Audit Berry, environnements, solidification, logs, communications et RAM — octobre 2026

> Audit **en lecture seule**, ouvert le 2026-10-21. Rien n'est modifié par l'audit : il trace ce qui est
> en place, en donne les avantages et les inconvénients, et formule des propositions. L'utilisateur est
> seul juge de leur mise en place ; elles lui sont remises par le plan d'action
> `tasks/plans/actions-audit-berry.md` (fin d'audit). Suivi de l'audit : `tasks/plans/audit-berry.md`.

## Grille de cotation

| Cote | Sens |
|---|---|
| **B** | Bloquant : casse un build ou un démarrage, ou perd une donnée |
| **G** | Gênant : défaut actif aujourd'hui |
| **L** | Latent : défaut sur un chemin non emprunté aujourd'hui |
| **S** | Simplification possible sans perte de fonction |
| **D** | Documentation à aligner |

Chaque section suit le même ordre : *Ce qui est en place* · *Avantages* · *Inconvénients / défauts
constatés* · *Propositions*. Chaque constat cite sa preuve (`fichier:ligne`, sortie d'outil).

---

## A1 — Cadrage et référentiel (2026-10-21)

### Statut des cartes (confirmé par l'utilisateur le 2026-10-21)

| Env | Carte | Statut | Poids dans l'audit |
|---|---|---|---|
| `tasmota32p4-garage-serveur-modbus` | maître P4 du garage | en service | prioritaire |
| `tasmota32s3-garage-capteurs-cuve-modbus` | cuve | en service | prioritaire |
| `tasmota32s3-garage-rideau-garage-modbus` | rideau | en service | prioritaire |
| `tasmota32s3-cave-serveur-rly` | cave (S3 N16R8) | en service | prioritaire |
| `tasmota32-bureau-interrupteur-differentiel` | différentiel (ESP32 sans PSRAM) | en service | prioritaire |
| `tasmota-pompe-piscine` | pompe de piscine | en service | prioritaire (aucun dossier `data/` : à examiner en A2) |
| `tasmota32s3-garage-serveur-modbus` | ancien maître S3 du garage | remplacé par le P4, gardé en archive / secours | basse |
| `tasmota32-cave-serveur-rly` | cave (ESP32 sans PSRAM) | remplacée par la S3 | basse |
| `tasmota32s3-etage2-grenier` | grenier | en sommeil | basse |
| `tasmota32-rdc-vr-porte` | volet de la porte du RDC | hors service | constat seulement |

> **Correction du 2026-10-22, d'après l'observation passive de A7.** La carte de cave réellement en
> service (192.168.0.48, `SERVEUR-RLY-CAVE`) **n'exécute pas** le code de
> `data/cave/tasmota32s3-serveur-rly`, et pas davantage celui de `data/cave/tasmota32-serveur-rly`.
> - Son topic MQTT est `cave/serveur-rly-cave`, alors que les deux persists de la cave déclarent
>   `cave/serveur-rly-cave-v2`, et que ce `-v2` est annoncé `Offline`.
> - Elle tourne en firmware 13.3.0.3, avec le modèle « ESP32 Relay x8 ».
> - Elle émet des messages qui n'existent que dans `data/cave/tasmota32-serveur-rly-sauvegarde/`
>   (`controleGlobal.be:346`).
> - Le persist de ce dossier porte justement le topic `serveur-rly-cave`, dans l'ancienne structure
>   `parametres`.
>
> **Le statut « cave S3 en service » est donc à confirmer** : soit la S3 n'est pas encore déployée, soit
> elle a été réinstallée avec l'ancien code. Les constats « cave S3 » de cet audit portent sur le code du
> dépôt, pas sur la carte en place.
>
> Même vérification pour les autres cartes, d'après les messages de discovery retenus le 2026-10-22 :
>
> | Carte | Firmware | Exécute le code du dépôt ? |
> |---|---|---|
> | P4 | 16.0.0.1 | oui |
> | cuve | 16.0.0.1 | oui |
> | rideau | 15.4.0.2 | `Offline` pendant l'observation : non vérifié |
> | différentiel (192.168.0.49, `tongou SY2`) | 15.0.1 | **non** : tas Berry de 3 Ko pour 42 objets, uptime de 22 jours. Le framework Berry du dépôt n'y est pas chargé. |

### Ligne de base des bancs

Lancés le 2026-10-21 vers 20:40, pendant un build de l'utilisateur (`erase_upload` cuve + P4 + rideau).
Les bancs Berry ont donc tourné sur une **copie complète** de `data/fs`, identique au dépôt à HEAD
`70600a844` (`diff -rq` vide, `git status data/fs` vide). Résultat valable pour ce commit.

| Banc | Verdict | Contrôles |
|---|---|---|
| `berry/banc_test_modbus.py` | `BANC_MODBUS: OK` (code 0) | 309 / 309, 0 bug connu |
| `berry/banc_leds.py` | `BANC_LEDS: OK` (code 0) | 36 ok |
| `berry/test_discovery.be` | `TEST_DISCOVERY: OK` | 216 tests, 0 échec |
| `berry/banc_veille_drivers.be` | `BANC_VEILLE_DRIVERS: OK` | 19 ok |
| `berry/banc_graphiques.be` (partie Berry) | `BANC_GRAPHIQUES: OK` | 95 ok |
| `berry/banc_historique.be` | `BANC_HISTORIQUE: OK` | 63 ok |
| `berry/verifie_berry.py` (tout `data/`) | code 0 | 54 fichiers, 0 erreur ; témoin `var x = = 3` rejeté (code 1) |

Pas encore couvert : le rendu navigateur de `banc_graphiques.py`, qui lance Chrome. Il n'a pas été
lancé pendant le build. À passer hors build si l'on veut une ligne de base complète.

### Carte des modules

`berry/carte_modules_berry.py --sortie <scratchpad>` : 43 modules, 8 cartes, **14 incohérences**,
29 informations. Contenu **identique** à `outils_docs/CARTE_MODULES_BERRY.md` (version du 2026-10-20) à
l'ordre près de quelques lignes du graphe : l'ordre de sortie du générateur n'est pas stable d'une
exécution à l'autre (cote **S**, constat sur l'outil).

Ces 14 incohérences sont des **pistes pour A3/A4**, pas encore des constats :
- des `controleXxx` (TCP, UDP, Discovery, Range Extender, LED témoin) solidifiés sur des cartes dont
  l'autoexec ne les charge pas, ou ne les cite qu'en commentaire : différentiel, P4, cuve, rideau,
  cave ESP32 ;
- `data/etage2/tasmota32s3-grenier/controleGrenier.be` : fichier vide ;
- **faux positif de l'outil** : « `controleRideau` dans custom_berry_solidify mais `data/fs/controleRideau.be`
  n'existe pas ». Le module est solidifié depuis le dossier de la carte, par son chemin complet
  (`platformio_tasmota_cenv.ini:633`), et il existe bien
  (`data/garage/tasmota32s3-rideau-garage-modbus/controleRideau.be:4`). C'est `carte_modules_berry.py:427`
  qui ne cherche que dans `data/fs` (cote **L**, sur l'outil).

## A2 — Construction des environnements (2026-10-21)

Méthode : configuration **résolue** de chaque env par `ProjectConfig` de PlatformIO (Python de `penv`,
lecture seule, sans `pio run`). S'y ajoutent la lecture de `pre_utilitaires_platformio.py`, de
`pio-tools/post_esp32.py` et de `user_config_override.h`, et une reproduction de `copy_fs_image`
pour chiffrer le contenu du LittleFS. Scripts : scratchpad `a2/dump_envs.py` et `a2/taille_fs.py`.

### Ce qui est en place

- **15 envs** dans `platformio_tasmota_cenv.ini` :
  - 5 bases : `tasmota32-base`, `tasmota32s3-base-N16R8`, `tasmota32p4-base-wifi6`,
    `tasmota32p4-base-devkit`, `tasmota32p4r3-base-devkit` ;
  - 10 cartes, chacune avec un seul niveau d'héritage (`extends`) vers sa base, sauf
    `tasmota-pompe-piscine`, qui hérite directement de l'env amont `tasmota` (ESP8266).
- `default_envs` (dans `platformio_override.ini`) : cuve, rideau, cave S3, P4.
- **Identité de chaque firmware** : un `-D FIRMWARE_<CARTE>` dans `build_flags` sélectionne une section
  `#elif defined(FIRMWARE_…)` de `tasmota/user_config_override.h` (3161 lignes) : IP, topic, template,
  options `USE_*`, `USER_BACKLOG`. La cave ESP32 et la cave S3 partagent une section (`:708`).
- **Pre-script** `outils_docs/scripts_python/build/pre_utilitaires_platformio.py`, sur tous les envs
  ESP32 :
  - réécrit `data_dir` dans `platformio_override.ini`, après une sauvegarde `.bak` ;
  - incrémente `CFG_HOLDER` dans `user_config_override.h` (aujourd'hui 1531, `:51`) ;
  - avant `firmware.bin` et `littlefs.bin`, copie `data/fs` (à plat), `data/json` et `data/sd` dans
    le dossier de la carte, puis les retire à la sortie (`atexit`) ;
  - enregistre les 7 cibles Custom (pont série, sniffeurs, syslog, testeur UDP, synchro, annuaire),
    qui ne déclenchent ni réécriture ni copie, et `__idedata` non plus.
- **Image LittleFS** construite par `pio-tools/post_esp32.py:140-181` depuis `custom_files_upload` (le
  dossier de la carte, plus `partition_wizard.bec` sur S3/P4), avec les exclusions
  `custom_files_exclude_solidified` / `custom_files_exclude`. Elle est jointe au flash lors d'un
  `upload` / `erase_upload` par esptool (`:405-425`).
- **Pompe de piscine** : ESP8266 1 Mo, donc pas de Berry ; ni pre-script ni dossier `data/` (normal).
  Seule la cible du pont série lui est ajoutée.

### Occupation du LittleFS (contenu reproduit d'après `copy_fs_image`, HEAD `70600a844`)

| Env | Contenu embarqué | Partition FS | Occupation |
|---|---|---|---|
| P4 garage | 605 Ko (31 fichiers) | 11 584 Ko | 5 % |
| cuve | 615 Ko | 11 584 Ko | 5 % |
| rideau | 604 Ko | 11 584 Ko | 5 % |
| cave S3 | 619 Ko | 11 584 Ko | 5 % |
| différentiel (ESP32) | 144 Ko | 320 Ko (table par défaut) | 45 % |
| cave ESP32 (remplacée) | 160 Ko | 448 Ko (table perso) | 36 % |
| grenier (en sommeil) | 604 Ko | 11 584 Ko | 5 % |
| rdc-vr-porte (hors service) | 1 429 Ko | 320 Ko | **446 %** |

Sur les S3 et le P4, 519 Ko viennent de `data/sd` (ECharts compressé et pages des graphiques). Sur le
P4 et la cuve, plus rien de `data/fs` n'est copié : tout y est solidifié ou exclu.

### Avantages

- Héritage simple et lisible (une base par famille de puce, un niveau). Les listes de solidification
  sont partagées dans `[berry_commun]` (A3) : un module ne s'ajoute qu'à un endroit.
- **Chaîne de build défensive :**
  - sauvegarde `.bak` avant réécriture ;
  - safeboot reconnu et isolé ;
  - cibles hors build listées, IntelliSense compris ;
  - une erreur de copie fait échouer la cible (`raise`) au lieu de flasher un LittleFS incomplet ;
  - le nettoyage ne supprime rien sans inventaire préalable (`liste_fichiers_exclus is None`) ;
  - le statut réel du build est lu par `GetBuildFailures`.
- **Constat du 2026-10-21** : aucun fichier temporaire ne reste dans les 8 dossiers de carte, y compris
  celui de la cuve, déjà construite dans le build en cours de l'utilisateur.
- Le LittleFS des S3/P4 est très largement dimensionné (5 %), ce qui laisse la place à l'historique en flash.
- `CFG_HOLDER` incrémenté à chaque build : chaque flash repart de réglages Tasmota connus, puis Berry
  réapplique le persist. Le comportement est donc **déterministe**, quel que soit l'état antérieur de la carte.
- `pio-tools/solidify-from-url.py` est revenu à la version amont (`260991cd2`) : plus de divergence sur
  ce script critique.

### Inconvénients et défauts constatés

| # | Constat | Preuve | Cote |
|---|---|---|---|
| E1 | **LVGL et tout le profil « écran » sont compilés sur toutes les S3**, cuve, rideau et cave compris : `USE_LVGL`, `USE_LVGL_OPENHASP`, `USE_DISPLAY`, `USE_UNIVERSAL_DISPLAY`/`TOUCH`, `USE_I2S`, `USE_SDCARD`, `USE_TUYA_MCU`, `USE_MATTER_DEVICE`, `USE_BM8563`, `USE_MPU_ACCEL`. La base N16R8 pose `-D FIRMWARE_LVGL` et `-D USE_LVGL_OPENHASP`. Les sections de carte ne font que *commenter* `USE_DISPLAY`, ce qui ne désactive rien. Coût en flash et peut-être en RAM, chiffré en A9. | `platformio_tasmota_cenv.ini:121-122` ; `tasmota_configurations_ESP32.h:292` et suivantes ; defines du build cuve figés par `70600a844` (`tasmota_defines_for_berry.h` : `USE_LVGL`, `FIRMWARE_LVGL 1`, `USE_LVGL_OPENHASP 1`…) | G (à confirmer : aucune S3 n'a d'écran ?) |
| E2 | `USER_TEMPLATE` du rideau **invalide** : le tableau GPIO se termine par `1,1s]`. Il n'est lu qu'à la réinitialisation des réglages (`settings.ino:1474`, donc à chaque flash, puisque `CFG_HOLDER` change). L'effet est compensé : `configGlobal.be:289-292` réapplique ensuite le template du persist. | `user_config_override.h:2474`, présent depuis `04dbda1a7` (2026-05-17) | L |
| E3 | **8 sections orphelines** dans `user_config_override.h`, sans env dans aucun `.ini` : `TELEINFO_CONSO`, `TELEINFO_PROD`, `SERVEUR_RLY_RDC`, `SERVEUR_DEBITMETRES_PAC`, `ESP32S3_SERVEUR_DEBITMETRES_PAC`, `ESP32S3_LCD_SERVEUR_DEBITMETRES_PAC`, `DEBITMETRES_PAC1`, `ESP32S3_DEBITMETRES_PAC1`. Environ 925 lignes, plus la section `ESP32_VR_PORTE` (env hors service). | `user_config_override.h:872-1688`, `:1829-1984` ; recherche de chaque nom dans `platformio*.ini` : aucun résultat | S |
| E4 | **Sections actives presque identiques** : cuve et rideau ne diffèrent que de 33 lignes sur 174 (identité, template, `USE_SHUTTER`, `USE_ADS1115`, DS18x20). Toute option commune se modifie en 5 à 10 exemplaires. | `diff` des sections `:2277-2450` et `:2451-2619` | S |
| E5 | `increment_config_holder` : au rebouclage (65535), `new_value` n'est jamais affecté et la fonction lèverait `UnboundLocalError`, ce qui casserait le build. Lointain (1531 aujourd'hui). | `pre_utilitaires_platformio.py:394-399` | L |
| E6 | État global muté dans `copy_fs_image` : `ignore_dirs` et `dossiers_a_copier` sont des **tuples par virgule finale** (`:69-70`), « déballés » par `[0]` à chaque appel (`:534-540`). La fonction est accrochée deux fois par build (`firmware.bin` et `littlefs.bin`, `:778-779`). Un second appel réel itérerait sur la chaîne `"fs"` et ré-inventorierait le dossier déjà rempli, laissant les copies temporaires en place. Sans effet observé (aucun résidu le 2026-10-21) : fragile, pas défaillant. **Tuples corrigés le 2026-10-22 à la demande de l'utilisateur** (listes réelles, `[0]` supprimés ; banc hors dépôt : un appel identique avant/après). Reste le ré-inventaire au second appel (`:531`), qui laisserait les copies : P2.6. | `pre_utilitaires_platformio.py:69-70`, `:534-541`, `:778-779` | L |
| E7 | Code mort dans le pre-script : `change_data_dir_in_platformio_ini` (`:408-447`, appel commenté `:663`), deux blocs de `AddPreAction`/`AddPostAction` en commentaire. | `pre_utilitaires_platformio.py:408-447`, `:663-685`, fin de fichier | S |
| E8 | `data_dir` est réécrit dans `platformio_override.ini` (fichier suivi) à **chaque build**, alors que l'image LittleFS se construit depuis `custom_files_upload`. Son seul usage restant est celui des outils PlatformIO natifs. Le prix : un fichier suivi modifié à chaque build, d'où les commits `chore` récurrents. | `pre_utilitaires_platformio.py:289-335` ; `post_esp32.py:140-181` | D |
| E9 | **Divergences de `pio-tools/` avec l'amont** : 13 fichiers, 254 lignes ajoutées et 205 supprimées, dont environ 90 % de **traduction de commentaires et de messages** (par exemple `post_esp32.py`, 160 lignes changées dont environ 16 de code, et `tasmotapiolib.py`, 122 dont environ 22). Chaque synchro du fork risque un conflit sans gain fonctionnel. Changements fonctionnels : exclusions du LittleFS (`post_esp32.py`), en-tête `Referer` (`espupload.py`), hôte en dur `192.168.0.43` (`espupload_legacy.py`). | `git diff --stat upstream/development -- pio-tools/` | G (coût de maintenance) |
| E10 | **Double mécanisme d'exclusion du LittleFS** : `copy_fs_image` n'envoie jamais les solidifiés ni la liste noire (sans garde), puis `post_esp32.py` les retire encore (solidifiés si `custom_files_exclude_solidified = ON`). Le `ON` n'a d'effet propre que pour un module solidifié **depuis le dossier de la carte** (`controleRideau.be`). Détail en A3. | `pre_utilitaires_platformio.py:486-512`, `:560-565` ; `post_esp32.py:190-220` | S |
| E11 | Le nom de la table S3 trompe : `esp32_partition_app3997k_fs11862k.csv` contient une app de 0x3D0000 (3904 Kio) et un FS de 0xB50000 (11 584 Kio), soit exactement la table P4 `app3904k_fs11584k`. De même, `board_upload.maximum_size = 16777216` est trompeur, mais sans danger : la plateforme le recale sur la partition app (`builder/main.py`, `_update_max_upload_size`). | `partitions/esp32_partition_app3997k_fs11862k.csv` ; `platformio_tasmota_cenv.ini:136-138` | D |
| E12 | `data/test.mp3` (3,3 Mo) suivi dans le dépôt depuis `04dbda1a7`, jamais embarqué (seuls `fs`, `json` et `sd` sont copiés). | `git ls-files data/test.mp3` ; `pre_utilitaires_platformio.py:70` | S |
| E13 | Ports COM versionnés dans le `.ini` partagé, donc propres à un poste alors que le dépôt sert sur deux postes. Doublons : `COM11` (base S3 et cave ESP32), `COM34` (bases P4 et différentiel). | `platformio_tasmota_cenv.ini:114, 153, 177, 201, 244, 327, 384, 436, 487, 576, 616` | D |
| E14 | `FIRMWARE_TASMOTA32` est défini deux fois sur les S3 (`-DFIRMWARE_TASMOTA32` par l'amont, `-D FIRMWARE_TASMOTA32` par la base N16R8). Sans effet. | `platformio_tasmota_cenv.ini` (base N16R8, `build_flags`) | D |
| E15 | `rdc-vr-porte` (hors service) : 1,4 Mo de contenu pour un LittleFS de 320 Ko, sans liste noire, et son build créerait un dossier `data/rdc/tasmota32-vr-porte` vide. | reproduction `copy_fs_image` ; `transform_name` + `ensure_path` (`:256-286`) | L |

*Choix de conception, pas un défaut : `CFG_HOLDER` incrémenté à chaque build réinitialise tous les
réglages Tasmota à chaque flash. Tout réglage qui ne vient ni des defines, ni de `USER_BACKLOG`, ni du
persist appliqué par Berry est donc perdu au flash suivant.*

### Propositions

- **P2.1** — Confirmer qu'aucune S3 n'a d'écran. Dans ce cas, retirer `-D FIRMWARE_LVGL` et
  `-D USE_LVGL_OPENHASP` de la base N16R8, ou créer une base S3 « sans écran ». Le gain en flash et en
  RAM est à mesurer en A9. *(effort faible, risque moyen : build complet et essai sur carte)*
- **P2.2** — Corriger la coquille du `USER_TEMPLATE` du rideau (un caractère). *(faible, faible)*
- **P2.3** — Corriger le rebouclage de `increment_config_holder`. *(faible, faible)*
- **P2.4** — Retirer ou archiver les 8 sections orphelines et la section du volet RDC. Ensuite,
  envisager un bloc commun « garage » et ne garder par carte que l'identité, le template et les `USE_*`
  propres. *(moyen, risque faible si l'on compare les defines produits avant et après)*
- **P2.5** — Remettre la version amont des fichiers de `pio-tools/` dont l'écart n'est que de la
  traduction ; regrouper les changements fonctionnels dans `post_esp32.py`, ou les déplacer dans un
  script du fork. *(moyen, risque faible : réduit les conflits de synchro)*
- **P2.6** — Assainir le pre-script : vraies listes au lieu des tuples, garde « déjà copié » contre le
  double accrochage, suppression du code mort. *(faible, faible)*
- **P2.7** — Renommer la table S3 d'après son contenu, ou la remplacer par la table P4 identique ; retirer
  le `maximum_size` trompeur. *(faible, faible)*
- **P2.8** — Sortir `data/test.mp3` du dépôt s'il ne sert plus. *(faible, nul)*
- **P2.9** — Décider où vivent les ports COM propres à chaque poste (hors du `.ini` partagé, par exemple
  dans un fichier local non suivi). *(faible, décision)*
- **P2.10** — Ne garder qu'un seul mécanisme d'exclusion du LittleFS (voir A3). *(moyen, moyen)*

## A3 — Chaîne de solidification (2026-10-22)

Méthode : listes **résolues** de `custom_berry_solidify` (A2) croisées avec la carte des modules (A1).
Contrôles statiques scriptés (scratchpad `a3/controles.py`, `dispo.py`, `nom_global.py`). Enfin,
**passage de la vraie chaîne sur les 37 modules solidifiés** : `berry/solidifie_et_compile_berry.py`
enchaîne solidification stricte (`globs`), `coc` et compilation C par `xtensa-esp-elf-gcc`. Lancé hors
build, avec un témoin.

### Ce qui est en place

- **Trois listes partagées** dans `[berry_commun]` (`platformio_tasmota_cenv.ini`) : `socle` (20 modules,
  toutes les cartes), `modbus` (6, garage), `historique` (3, S3/P4). Chaque env les compose et ajoute
  ses modules propres : `controleRideau` depuis le dossier de la carte ; ES8311, volets et LoRaWan selon
  les cartes. Au total, **37 modules distincts**, de 20 (différentiel, cave ESP32) à 33 (ancien maître S3)
  par env.
- **Convention de fichier** : directive `#@ solidify:<nom>`, `var <nom> = module("<nom>")` sans slash.
  Les `controleXxx` sont chargés par `import` + `init()`. Un module natif l'emporte sur le fichier
  (`be_module.c`, `load_native` avant `load_package`). `compileModule` d'un module solidifié devient un
  no-op silencieux puisque son `.be` n'est pas copié (`gestionFileFolder.be:451`, `else return true`) :
  l'autoexec n'a rien à changer.
- **État modifiable hors du module**, dans une globale cachée lue par `member()` et écrite par
  `setmember()` : `logFonctions` (`logFonctions_etat`), `historiqueFonctions` (`:50-82`), `ledsFonctions`
  (`:45-92`).
- **Solidifieur du build** : `lib/libesp32/berry_custom/solidify_all_python.be`, mode strict, liste
  `globs` étendue par le fork de 15 noms du framework (58 lignes ajoutées, 2 supprimées par rapport à
  l'amont). `pio-tools/solidify-from-url.py` et `gen-berry-structures.py` sont **identiques à l'amont**.

### Résultats de la vérification

| Contrôle | Résultat | Preuve |
|---|---|---|
| Solidification + `coc` + compilation C des 37 modules | **37 / 37 `rc=0`, 0 closure anonyme**. Les plus gros `.h` : `modbusFonctions` 654 Ko de source C (65 closures), `modBus_TasmotaSlaveModBus` 312 Ko, `udpFonctions` 162 Ko, `ledsFonctions` 161 Ko | `a3/compile/resume.txt`, 2026-10-22 |
| Témoin : module qui appelle une globale inconnue | **refusé** : `'globaleInconnueDuTemoin' undeclared` (`rc=1`) | `a3/compile/zzzTemoin.log` |
| Directive = nom du fichier = nom lu par la regex de `addEntryToModtab` (`solidify-from-url.py:36`) | 37 / 37, aucun motif `module(` dans un commentaire | `a3/controles.py` |
| Piège 12, écriture dans un module en flash | 2 modules écrivent dans leur propre module (`historiqueFonctions`, `ledsFonctions`), **tous deux par `setmember`** : conforme | `historiqueFonctions.be:77-82`, `ledsFonctions.be:87-92` |
| Piège 13, `return controleXxx` final | seul `controleLeds` est chargé depuis le LittleFS (cave S3, grenier, rideau) et il l'a. Les 11 autres `controleXxx` n'en ont pas mais sont solidifiés partout où ils sont chargés | matrice A1 + `a3/controles.py` |
| Noms ajoutés par le fork à `globs` | les 15 sont encore utilisés par des modules solidifiés (de 4 à 354 occurrences) | recherche dans les 37 fichiers |
| Listes de solidification et listes noires | aucune entrée vers un fichier absent ; aucune redondance, sauf 4 modules sur l'ancien maître S3 (archive, sans effet) | `a3` (croisement par env) |

*Note de méthode : un premier passage avait donné 36 échecs. La cause était mon lanceur, pas les
modules : la liste produite par Python sous Windows portait des `\r` en fin de chemin (« introuvable »).
Corrigé, puis relancé ; seul le second passage est retenu ci-dessus.*

### Avantages

- **La chaîne est saine et prouvée** : les 37 modules passent la même chaîne que le build. La
  convention (directive, `module()` sans slash, fonctions nommées) est respectée partout, et le
  mécanisme `setmember` règle proprement l'état des modules en flash.
- Listes partagées : un module de `data/fs` ne s'ajoute qu'une fois. L'oubli du 2026-09-27 n'est plus
  possible.
- Le fork n'a plus d'écart sur `solidify-from-url.py`. Le seul écart restant, `globs`, est commenté
  ligne par ligne et ne sert qu'à nos noms.
- Rien à changer dans les autoexec quand on solidifie un module (`compileModule` devient un no-op).
- `solidifie_et_compile_berry.py` vérifie un module en environ 10 s au lieu d'un build de deux heures.

### Inconvénients et défauts constatés

| # | Constat | Preuve | Cote |
|---|---|---|---|
| S1 | **Différentiel : le persist déclare `drivers.ModBus.activation = ON`** (maître `id 0`, `log: detail`), avec une entrée analogique virtuelle `ModBus_TasmotaSlaveModBus1`. Or la pile ModBus n'est **pas** embarquée : `modbusFonctions` n'est ni solidifié ni copié, et `autoexec.be:61` et `:87` sont commentés. Les chemins sont gardés aujourd'hui (l'analogique est `OFF`, aucun relais virtuel, `globalFonctions.be:161` et `:226` exigent `id > 0`). Mais activer cette entrée ou ajouter un relais virtuel ModBus ferait échouer un `import modbusFonctions` à l'exécution. | `data/bureau/tasmota32-interrupteur-differentiel/_persist.json` ; `controleGeneral.be:600-628` | L |
| S2 | Modules **importés mais absents** de la carte (ni flash ni LittleFS), sans incident tant que leurs gardes restent fausses : `modbusFonctions` sur la cave S3 et le grenier (ModBus `OFF`), `ledsFonctions` sur le P4 (ruban `OFF`, appel réservé à l'esclave : `modbusFonctions.be:2075-2095`). Les réceptions TCP et UDP sont protégées par `try` (`tcpFonctions.be:208`, `udpFonctions.be:788`). | `a3/dispo.py` ; sites lus un par un | L |
| S3 | **Modules solidifiés jamais chargés** sur leur carte, donc du coût en flash sans usage : différentiel (`controleLedTemoin`, `controleDiscovery`, `controleRangeExtender`, `controleTCP`, `controleUDP`, `discoveryFonctions`), P4 (`controleTCP`), cuve et rideau (`controleRangeExtender`, `controleTCP`), cave ESP32 (`discoveryFonctions`). Conséquence du `socle` commun : simplicité contre quelques Ko de flash par carte. | incohérences de la carte des modules (A1) | S |
| S4 | **Deux conventions** pour atteindre un module par son nom : un nom global créé par un `import` de niveau fichier dans l'autoexec (la plupart des modules), ou un `import` local en tête de chaque fonction (`ledsPanelFonctions`, et beaucoup d'appelants). La seconde ne dépend pas de l'autoexec. La première a déjà coûté un boot raté (leçon du 2026-09-27). | `ledsPanelFonctions.be` (chaque fonction) ; autoexec | S |
| S5 | `custom_files_exclude_solidified = ON` n'a d'effet propre que pour un module solidifié **depuis le dossier de la carte** (`controleRideau`). Ailleurs, `copy_fs_image` a déjà écarté les solidifiés (voir E10). | `pre_utilitaires_platformio.py:560-565` ; `post_esp32.py:190-220` | S |
| S6 | Le `return controleXxx` final manque à 11 `controleXxx`. Sans effet tant qu'ils restent solidifiés ; si l'un d'eux cesse de l'être sur une carte, son driver ne démarrera pas, **sans erreur** (piège 13). | `a3/controles.py` | L |
| S7 | `carte_modules_berry.py` signale à tort `controleRideau` comme absent : il ne cherche les modules solidifiés que dans `data/fs` (`:427`). La docstring de `modules_solidifies()` cite `gestionFileFolder.be:378` pour le no-op, une ligne aujourd'hui en `:451`. | `carte_modules_berry.py:427` ; `pre_utilitaires_platformio.py:486-502` | D |
| S8 | La liste `globs` diverge de l'amont : à chaque synchro du fork, le fichier peut entrer en conflit, et un nom ajouté en amont peut être perdu si le conflit est mal résolu. | `git diff upstream/development -- lib/libesp32/berry_custom/solidify_all_python.be` | L |

### Modules candidats à la solidification

Sur les cartes en service, ces modules sont encore compilés en RAM au démarrage depuis le LittleFS :

| Module | Carte | Taille `.be` | Obstacles | Effort |
|---|---|---|---|---|
| `garageFonctions` | P4 | 5 Ko | module ; environ 7 fonctions anonymes à nommer (`nomme_fonctions_berry.py`) ; solidification depuis le dossier de la carte, comme `controleRideau` | faible |
| `cuveFonctions` | cuve | 30 Ko | module ; environ 19 fonctions anonymes, 2 écritures du module à l'exécution (passer par `setmember`) | moyen |
| `controleCuve`, `controleGarage`, `controlePompeVideCave` | cuve, P4, cave S3 | 19 Ko, 21 Ko, 10 Ko | scripts de driver (`tasmota.add_driver`), sans module : conversion au modèle « module + `init` » de `controleRideau` | moyen |
| `controleLeds`, `ledsFonctions` | cave S3, rideau | — | garde `OFF` sur ces cartes : pas chargés, donc aucun gain | — |

Le gain en RAM (bytecode compilé au démarrage contre structures en flash) reste à mesurer en A9.

### Propositions

- **P3.1** — Différentiel : remettre `drivers.ModBus.activation` à `OFF` dans le persist, ou embarquer
  la pile ModBus si elle doit servir. *(faible, décision)*
- **P3.2** — Généraliser l'`import` local en tête de fonction pour l'auto-appel d'un module (convention
  S4), afin de ne plus dépendre du nom global posé par l'autoexec. *(moyen, risque faible ; vérifiable
  module par module avec `solidifie_et_compile_berry.py` et un boot)*
- **P3.3** — Ajouter `return controleXxx` à la fin de chaque `controleXxx`, même solidifié, pour qu'il
  reste chargeable depuis le LittleFS. *(faible, nul)*
- **P3.4** — Solidifier `garageFonctions`, puis `cuveFonctions` ; plus tard, convertir les trois scripts
  de driver de carte. À mesurer d'abord en A9. *(faible à moyen)*
- **P3.5** — Accepter les modules solidifiés inutiles (S3) comme prix de la simplicité, ou découper le
  `socle` en `socle` et `reseau`. *(décision ; faible)*
- **P3.6** — Corriger `carte_modules_berry.py` pour les modules solidifiés hors de `data/fs`, et mettre à
  jour le numéro de ligne de la docstring. *(faible)*
- **P3.7** — Réduire à un seul mécanisme d'exclusion du LittleFS : soit `copy_fs_image` traite aussi les
  modules de carte, soit `post_esp32.py` seul (voir P2.10). *(moyen)*

*Effet de bord de la vérification : l'étape `coc` a régénéré `lib/libesp32/berry/generate/` (dossier
ignoré par git), que le prochain build régénère de toute façon. Aucun fichier suivi n'a changé.*

## A4 — Architecture et chargement des scripts Berry (2026-10-22)

Périmètre : les 8 `autoexec.be` de `data/<lieu>/<carte>/` (hors `*sauvegarde*`), les `controleXxx` de
carte, `data/fs/gestionFileFolder.be`, et les `_persist.json` des 5 cartes Berry en service (P4, cuve,
rideau, cave S3, différentiel). Recherches faites sur `data/` entier, pages `data/sd` comprises.
Scripts de mesure : `scratchpad/a4/fonctions_mortes.py`, `scratchpad/a4/cles_persist.py`.

### Ce qui est en place

**Le contrat de chargement.** Chaque autoexec suit les mêmes étapes :

1. Imports et globales du persist (`serveur`, `diverses`, `modules`, `drivers`).
2. `gestionFileFolder.compileModule("/x", activation)` sur les utilitaires puis les services
   (`udp`, `tcp`, `rangeExtender`, `discovery`, `modbus`…), chacun sous la garde de son bloc du persist.
3. `gestionFileFolder.loadBerryFile("/controleCarte", activation, "ON")` pour le script de la carte.
4. LEDs et historique en fin de fichier.

Chaque `controleXxx` enregistre ensuite son driver (`tasmota.add_driver`) et ses commandes
(`tasmota.add_cmd('ReglageXxx', …)` : 25 appels pour 22 noms), puis appelle ses `xxxFonctions`.

**Les deux fonctions de chargement** (`gestionFileFolder.be`) :

- **`compileModule(chemin, paramDeleteBe)`** (`:419-453`) :
  - `"OFF"` avec un `.bec` présent : le `.be` est supprimé et rien n'est compilé ;
  - sinon le `.be` est compilé en `.bec`, puis supprimé ;
  - un module solidifié n'a pas de `.be` sur le LittleFS : la fonction ne fait rien (`:451`).
- **`loadBerryFile(chemin, paramDeleteBe, compileBe)`** (`:377-415`) : même traitement du `.be`, puis
  `load(chemin)`.
  - Le test qui devait réserver ce chargement aux modules actifs est **commenté** (`:410-414`) : le
    fichier est chargé **quelle que soit l'activation**.

**Les autoexec en service** :

| Carte | Lignes | Script de carte chargé | Particularités |
|---|---|---|---|
| P4 | 133 | `controleGarage` (`:124`) | `garageFonctions` (`:75`), discovery |
| cuve | 140 | `controleCuve` (`:131`) | `cuveFonctions` (`:77`), LEDs |
| rideau | 133 | aucun : `controleRideau` est solidifié | LEDs |
| cave S3 | 135 | `controlePompeVideCave` (`:107`) | LEDs, historique |
| différentiel | 114 | aucun | **ancien modèle** (voir D2) |

Environ 50 lignes sont communes aux 8 autoexec : en-tête, globales, sept `compileModule` d'utilitaires,
services réseau.

### Avantages

- Un seul modèle de démarrage pour toutes les cartes : on lit un autoexec et on sait lire les autres.
- L'activation est portée par le persist : une carte change de rôle sans toucher à son code.
- Chaque service ne se charge que si son bloc est actif. Les services absents ne coûtent pas de RAM.
- Les réglages passent par `ReglageXxx`, un nom par domaine, sans collision avec le firmware. Seules
  exceptions, et elles sont voulues : `HSBCOLOR`, `DIMMER` et `SCHEME` remplacent les commandes du
  firmware sur un esclave dont le ruban est déporté (`modBus_TasmotaSlaveModBus.be:82-86`).
- La compilation en `.bec` au premier démarrage évite de recompiler le source à chaque redémarrage.

### Inconvénients et défauts constatés

| # | Constat | Preuve | Cote |
|---|---|---|---|
| D1 | **`loadBerryFile` charge le fichier même si son activation est `OFF`.** Le test est commenté (`:410-414`). Avec `OFF` et un `.bec` présent, le `.be` est supprimé, puis le `.bec` est chargé : le driver démarre quand même. Sont concernés `controleGarage`, `controleCuve` et `controlePompeVideCave`, dont la seule garde est cet argument. Aucun de ces trois scripts ne teste l'activation avant `tasmota.add_driver` (`controleGarage.be:382`, `controleCuve.be:353`, `controlePompeVideCave.be:153`). Aujourd'hui les trois modules sont `ON` : chemin non emprunté. | `gestionFileFolder.be:377-415` | L |
| D2 | **Trois générations d'autoexec coexistent**. Différentiel : ancien modèle (`var controleGeneral`, `import partition_wizard`, pas de `controleLedTemoin`, `compileModule("/webFonctions", "ON")` sans garde `serveur`). Ancien maître S3 du garage : `log (` avec une espace, compile `leds_panel` et `partition_wizard` (`:78-79`). Grenier : services compilés sans le `if … == "ON"` des autres cartes (`:64-66`) et `compileModule("/vrFonctions")` **sans activation** (`:69`), donc toujours compilé. Une correction faite dans un autoexec doit être reportée à la main dans les 7 autres. | autoexec cités | S |
| D3 | **`paramDeleteBe` porte deux sens** : « module actif » pour l'appelant, « supprimer le source » pour la fonction. Avec `OFF`, le `.be` est effacé de la carte. Le module ne pourra plus être modifié sur place sans téléverser à nouveau son source. | `gestionFileFolder.be:424-428` | D |
| D4 | `LOG_LEVEL_NONE = 0` n'est défini que dans l'autoexec du P4 (`:9`) et n'est lu nulle part. | recherche `LOG_LEVEL_NONE` sur `data/` | S |
| D5 | **Doublons de cartes** : `controlePompeVideCave.be` est identique sur la cave ESP32 et la cave S3 ; `controleGarage.be` S3/P4 diffère de 216 lignes, `garageFonctions.be` de 61. Les versions S3 sont celles d'une carte remplacée mais gardée (A1) : elles ne sont plus tenues à jour et divergeront davantage. | `diff` des fichiers | S |
| D6 | `data/cave/tasmota32-serveur-rly-sauvegarde/` : 7 fichiers suivis, 96 Ko. Aucun env ne l'utilise, mais c'est le **seul** endroit où vivent encore `typeAction`, `delaiSiON` et `delaiSiOFF` (voir D9). **Correctif A7 (2026-10-22) : c'est le code qui tourne sur la carte de cave en service** (voir la note du statut des cartes, A1). Ce n'est donc pas un dossier mort, mais la seule source de la carte réelle, et aucun env ne sait la reconstruire. | `git ls-files` ; `transform_name` ; syslog du 2026-10-22 | G |
| D7 | `controleGrenier.be` fait **0 octet** et reste chargé par l'autoexec du grenier (`:102`). Le grenier est en sommeil : sans effet aujourd'hui. | `wc -c` | S |
| D8 | **5 fonctions publiques sans appelant**, environ 180 lignes compilées ou solidifiées pour rien : `diversFonctions.afficheDateTime` (`:5-32`), `diversFonctions.getRandomInt` (`:35-54`), `gestionFileFolder.supprimeBerryFile` (`:303-337`), `webFonctions.reglageWeb` (`:10-42`, la commande `ReglageWeb` n'est enregistrée par aucun `add_cmd`), `webFonctions.clientWeb` (`:92-156`). | `fonctions_mortes.py` : 0 appel dans le code, 0 citation en chaîne, 0 dans `data/sd` ; liste des 25 `add_cmd` | S |
| D9 | **Clés du persist sans lecteur**. Chaque `relaisLie` porte `delaiSiON`, `delaiSiOFF`, `etatSiON` et `etatSiOFF`, et chaque bouton porte `typeAction` : 58 `relaisLie` sur les 5 cartes. Le code n'en lit que `modules`, `ids`, `type` et **`delai`** (`globalFonctions.be:219-222`, et 4 sites identiques jusqu'à `:364`). `etatSiON`/`etatSiOFF` ne sont cités que dans la liste d'élagage des listes vides (`diversFonctions.be:239`). Ces clés pèsent de 367 o (cuve) à 1 468 o (cave S3) sur des persists de 10 à 18 Ko, persists qui restent en RAM en permanence. | `cles_persist.py` ; recherche sur `data/`, `data/sd` et `outils_docs/scripts_python` | S |
| D10 | **Le schéma du persist inverse l'obligatoire et l'optionnel** : `persist.schema.json` déclare `delaiSiON`, `delaiSiOFF`, `etatSiON` et `etatSiOFF` **requis** (`:960-967`), et `delai`, la seule clé lue, **facultatif** (`:956`). Le schéma est produit par inférence (une clé présente dans au moins 50 % des exemples devient requise, `genere_schema_persist.py:21-23`). Il décrit l'existant, pas le contrat du code. Lecteur de clé absente : aucun cas trouvé. Les 58 `relaisLie` dont `ids` n'est pas vide portent tous `delai`. Mais une entrée nouvelle écrite d'après le schéma, avec un `ids` non vide et sans `delai`, lèverait `key_error` à la première commutation. | `persist.schema.json:956-967` ; contrôle des 5 persists | L |

Faux positifs écartés :
- Blocs `drivers.KNX`, `SD`, `ecran`, `Ethernet` et groupes `pinsXxx` : lus par itération
  (`diversFonctions.be:151`, `controleWeb.be:107`, `controleGeneral.be:596`).
- `diverses.logs.profils.normal` : lu par le nom du profil actif (`logFonctions.be:190`).
- `template.CMND` : objet transmis entier au firmware (`configGlobal.be:57`).
- Commandes `Reglage*` : toutes enregistrées par `add_cmd` dans leur `controleXxx`, sauf `ReglageWeb`.

Limite : `fonctions_mortes.py` ne couvre que les fonctions de module (`M.f = M_f`), pas les méthodes de
classe des drivers, que traitera A5.

### Propositions

- **P4.1** — Rétablir la garde de `loadBerryFile` : ne pas appeler `load()` si l'activation vaut `OFF`.
  Ou tester l'activation dans chaque script de carte avant `add_driver`. Corrige D1.
  *(faible ; risque faible : les trois modules sont `ON` ; essai : passer une carte à `OFF`, vérifier
  que le driver ne démarre pas, puis remettre `ON`)*
- **P4.2** — Factoriser le bloc commun des autoexec dans un module `demarrage` solidifié, par exemple
  `demarrage.socle()`. Chaque autoexec ne garderait que ses lignes propres (une quinzaine). Remettre au
  passage le différentiel et le grenier au modèle courant. Corrige D2 et D4.
  *(moyen ; risque moyen : c'est le chemin de boot ; une carte à la fois, en commençant par une carte
  remplacée)*
- **P4.3** — Séparer les deux sens de `paramDeleteBe` : un argument d'activation (charger ou non), et une
  option distincte et explicite pour supprimer le source. Corrige D3. *(faible)*
- **P4.4** — Décider du sort des fichiers des cartes remplacées. Soit les geler (en-tête « carte
  remplacée, non maintenu »), soit les retirer du dépôt, puisque git en garde l'historique. Corrige D5
  et D7. **Ne PAS retirer le dossier `*sauvegarde*` de la cave** : il porte le code de la carte en
  service (correctif A7). Pour lui, la décision est autre : déployer la S3 avec le code courant, ou
  donner à ce code un env qui sache le reconstruire. Corrige D6. *(faible ; décision)*
- **P4.5** — Supprimer les 5 fonctions sans appelant, ou les marquer « réservées » si elles doivent
  resservir (`reglageWeb` serait alors à enregistrer par `add_cmd`). Corrige D8.
  *(faible ; vérification : `verifie_berry.py` puis boot d'une carte)*
- **P4.6** — Nettoyer les clés mortes de `relaisLie` et `typeAction` dans les 5 persists. Dès
  maintenant à la main ; à terme par un script qui sauvegarde avant d'écrire. Gain attendu : 0,4 à
  1,5 Ko de RAM par carte. Corrige D9.
  *(faible ; risque faible ; prérequis : confirmer qu'aucun outil PC, page web ou sauvegarde ne les
  relit — recherche faite sur `outils_docs/scripts_python` et `data/sd`, à refaire au moment de
  l'action)*
- **P4.7** — Rendre le schéma normatif pour `relaisLie` : `delai` requis dès que `ids` n'est pas vide,
  clés mortes retirées. Soit par une surcharge manuelle dans `genere_schema_persist.py`, soit par un
  `find("delai", 0)` dans les 5 sites de `globalFonctions.be`. Corrige D10. *(faible)*

## A5 — Simplification des modules et drivers (2026-10-22)

Périmètre : les 22 drivers (`tasmota.add_driver`), la pile ModBus, les modules réseau, les utilitaires
transverses et les scripts des cartes en service. L'analyse a été faite en quatre parties parallèles,
en lecture seule. Chaque constat retenu ici a été **relu dans le code** depuis le fil principal. Les
deux bugs de N1 sont prouvés par un test Berry avec témoin (`scratchpad/a5/lambda.be`).

### Ce qui est en place

| Domaine | Fichiers (lignes) | Organisation |
|---|---|---|
| Pile ModBus | `modbusFonctions` (3242), `modBus_TasmotaSlaveModBus` (1463), `modBus_Conn16channels` (557), `controleModbus` (388) | Un module en 21 blocs : file FIFO, 3 transports, trame, CRC, esclave, push, carte 16 relais. Plus deux drivers d'esclave. Commentaires : 25 % du module. |
| Réseau | `udpFonctions` (914), `discoveryFonctions` (722), `rangeExtenderFonctions` (428), `tcpFonctions` (268) et leurs `controleXxx` | Table `/json/discovery.json` (8 lecteurs, 8 écrivains), ImAlive, routage RgxPort |
| Transverses | `globalFonctions` (706), `controleGeneral` (709), `configDevices` (459), `controleWeb` (474), `webFonctions` (345), `diversFonctions` (364), `gestionFileFolder` (515) | Parcours `modules → environnement → groupe → device` dans presque chaque fonction |
| Drivers périodiques | `every_100ms` : `controleModbus`, `controleUDP` (×2 instances) ; `every_250ms` : `controleTCP` ; `every_second` : général, LEDs, ModBus, UDP, cuve | Aucun `every_50ms`. Seul `controleLedTemoin` se retire (`remove_driver`). Les autres sont gardés à l'`init` et jamais retirés. |

Filets existants :
- `banc_test_modbus` : 309 contrôles sur 309, relancé pendant A5. Il charge `modbusFonctions`,
  l'esclave et `controleModbus`, mais **pas** `modBus_Conn16channels`.
- `test_discovery` : 213 contrôles, sur UDP, discovery et Range Extender. Il ne charge ni TCP, ni les
  drivers `controleUDP`/`controleTCP`, ni les commandes `ReglageDiscovery`/`RangeExtender`/`TCP`.
- Aucun banc pour `globalFonctions`, `configDevices`, `controleGeneral`, `controleWeb` et les scripts de
  carte : seule leur syntaxe est vérifiée.

### Avantages

- La pile ModBus est entièrement couverte par un banc vert, sauf la carte 16 relais : une
  simplification y est vérifiable en quelques secondes.
- **Aucune fonction de module morte dans `modbusFonctions`** : tout ce qui y est déclaré sert.
- Les drivers sont gardés à l'`init` : un bloc `OFF` n'enregistre pas son driver et ne coûte aucun tick.
- Les chemins chauds (`every_100ms`) sont peu nombreux et justifiés : 100 ms reste nécessaire pour la
  latence de réception UDP et série.
- Les correctifs passés sont commentés sur place (date et raison) : l'historique des décisions se lit
  dans le code.

### Inconvénients et défauts constatés

**Défauts de fonctionnement**

| # | Constat | Preuve | Cote |
|---|---|---|---|
| N1 | **Les redémarrages programmés ne s'exécutent jamais.** Les deux crons passent `/-> introspect.get(controleGeneral, "heureReboot")` : la lambda **renvoie** la méthode sans l'appeler. Sont concernés : le redémarrage quotidien (`heureReboot`, à 00:00 sur 4 cartes et 01:00 sur le différentiel), et le redémarrage si le Wi-Fi est perdu (`timerRebootSansWifi` à 300 sur le P4, la cave S3 et le différentiel). Les corriger **ferait démarrer** des redémarrages nocturnes qui n'ont jamais eu lieu. À vérifier aussi : `*/300` dans le champ des secondes de cron. | `globalFonctions.be:145`, `controleGeneral.be:97` ; test : 0 appel après la lambda, 1 avec le témoin | G |
| N2 | **Chaque ImAlive reçu réécrit `/json/discovery.json` en flash**, sans comparer le contenu : une écriture par esclave et par période de télémétrie. Les autres écrivains comparent d'abord avec `memeValeur` (correctif de l'incident du 2026-10-05). `writeFile` ne compare rien. | `udpFonctions.be:308-327` ; `gestionFileFolder.be:232-242` ; `discoveryFonctions.be:330-339` | G |
| N3 | **Cuve : `_Scheme` est appelé deux fois par seconde.** Une fois par `ledsFonctions.maj` (`ledsFonctions.be:444`), une fois par `surveilleRubans` → `etatRuban` (`modbusFonctions.be:2041`, `:2108`). La cuve est la seule carte avec le ruban `ON`. | persists ; lignes citées | G |
| N4 | **P4 : la page d'accueil relit `/sd/css/webSensor.css` sur la carte SD** à chaque rafraîchissement (environ toutes les 2 s, par page ouverte). | `controleGarage.be:94` | G |
| N5 | **Deux instances `CONTROLE_UDP`** (unicast et multicast) lisent chacune **les deux** sockets en `every_100ms` : 20 lectures par seconde pour 10 utiles, et une `map` allouée à chaque tick. | `controleUDP.be:138-147`, `:188-191` | S |
| N6 | **TCP est forcé `ON` sans être utilisé.** `controleModbus.be:159-169` et `controleRangeExtender.be:77-90` remettent `serveur.tcp.activation` à `ON`. Or `typeComm.TCP` est `OFF` dans les 8 persists. Le P4, la cuve et le rideau ne chargent pas TCP (lignes commentées). **La cave S3 le charge** (`autoexec.be:101`) : un client TCP et un `every_250ms` sans usage. | lignes citées | L |
| N7 | **Carte 16 relais : la réception n'est protégée par aucun `try`.** Une exception entre `:343` et `:397` empêche l'acquittement `termineEnVol` (`:402`). La file reste alors bloquée jusqu'au délai de garde. Chez l'esclave ESP32, le même chemin est protégé (G5 de l'audit ModBus). Ce driver n'a **aucun banc**. | `modBus_Conn16channels.be:318-402` | L |
| N8 | P4 : pour un thermomètre de type 1216, l'humidité affichée est la **température** (`thermoJson["value"]` lu deux fois). La cuve lit bien `AM2301.Humidity` (`controleCuve.be:264`). Le seul thermomètre de ce type sur le P4 est `OFF`. | `controleGarage.be:204-208` | L |
| N9 | **Déballage de `value` : deux versions coexistent.** La version correcte est `globalFonctions.be:197-208` (gère `Action`, lève l'ambiguïté). L'ancienne est recopiée 4 fois : `globalFonctions.be:424-428`, `cuveFonctions.be:436-440`, `garageFonctions.be:94-98`, `webFonctions.be:55-59`. Avec une `map` de plusieurs clés, elle indexe un scalaire. | lignes citées | L |
| N10 | Compteur des entrées analogiques réelles **toujours à 0** : il n'est incrémenté que s'il est déjà `> 0`. Le log de `controleGeneral.be:130` affiche en plus les `compteurs.actives` à la place des `réels`. `%i` appliqué à `"ON"` affiche `0` (`configDevices.be:419`, `:424`, `:449`). | `configDevices.be:232-234` | L |
| N11 | `controleWeb.etatCapteurs` est cassée (`self.parametres` non déclaré, `pageModifCapteurs.html` et `jsModifCapteurs.js` absents de `data/sd`). La route `/wss` et sa page `htmlWebSocket` codent une IP en dur. | `controleWeb.be:282-346`, `:450` ; `webFonctions.be:159-204` | L |

**Code mort** (recherche sur `data/` entier, `data/sd` compris ; commandes citées dans les comptes
rendus d'analyse)

| Domaine | Éléments | Lignes |
|---|---|---|
| Réseau | Fonctions sans appelant : `udpFonctions.sendTasmotaClientUDP` (`:861-883`), `tcpFonctions.envoiMsgTCP` (`:245-266`, corps commenté), `rangeExtenderFonctions.afficheBoutonsModulesEsclaves` (`:285-353`, seul appel dans un bloc `#- -#`, `controleRangeExtender.be:122-134`). Branches d'événements jamais branchées dans les `changementEtatDemarrage` UDP, TCP, discovery et Range Extender. Commandes coquilles `ReglageDiscovery`, `ReglageRangeExtender`, `ReglageTCP` (elles journalisent puis répondent `OK`). Blocs commentés et notes périmées (`controleUDP.be:1-56` : port 3000, au lieu de 4000). | environ 330 sans risque, et 150 pour les commandes (décision) |
| ModBus | Branches maître de `envoiMsgModbusSerial`, `TCP` et `UDP`, inatteignables : le maître quitte `envoiMsgModbus` à `:1488` pour tout message qui n'est pas une `Reponse`. Lectures de démarrage de l'esclave construites puis jamais envoyées (`modBus_TasmotaSlaveModBus.be:1153-1219`, avec un `tasmota.cmd` sur `teleperiod` à chaque boot). Constantes sans lecteur (`:70`, `:97-99`, `:102`, `:185`). `ReglageConn16Channel` sans sous-commande. `tabFonctionsName` reconstruite à chaque trame UDP (`controleModbus.be:274-283`). | environ 150 |
| Transverses | 109 lignes commentées dans `webFonctions.be` (`tcpServeur` `:206-258`, ancien `traiteCommandeHTTP` `:286-341`). `controleGeneral.any_key` (`:672-691`), qui ne fait que journaliser. `gestionFileFolder.supprBerryFS` (appelant commenté). `cuveFonctions.voltageMin`. Trois `changementEtatDemarrage` de carte jamais branchés (`garageFonctions.be:83-119`, `cuveFonctions.be:430-467`). Les 5 fonctions mortes de A4 (D8). | environ 330 |
| Callbacks vides | `controleWeb.every_second` (`:43`) ; `controleVoletRoulants` : `every_second`, `web_sensor`, `json_append` (`:98-110`) ; `controleRideau` : 3 callbacks et `enregistreLogs` (`:30-46`, squelette assumé) | environ 25 |

**Duplications** (simplifiables sans perte de fonction)

| # | Motif | Occurrences | Économie estimée |
|---|---|---|---|
| N12 | Bloc `relaisLie` (lecture, boucle sur `ids`, `modifEtatRelai`) | 6 copies, `globalFonctions.be:219-386`, seul le 6ᵉ argument varie | environ 16 lignes |
| N13 | Blocs capteurs / interrupteurs / boutons copiés, avec le même push ModBus de 13 lignes | `globalFonctions.be:210-310` ; `configDevices.be:126-193` | 60 + 45 lignes |
| N14 | Prédicat « device actif » | 16 copies (`globalFonctions`, `configDevices`, `configModules`, `controleGeneral`) | environ 16 lignes |
| N15 | Parcours `modules → environnement → devices` avec 8 à 12 lignes de gardes | 14 dans la pile ModBus, 5 dans `controleGeneral` | environ 140 lignes |
| N16 | `json.load(gestionFileFolder.readFile(x))` inline alors que `discoveryFonctions.lisTable` existe ; MAC normalisée par `string.replace` | 14 sites ; 17 sites | environ 30 lignes |
| N17 | Boucles sur les fiches `esclaveN` de la discovery, regex recompilée à chaque fois | 5 boucles, 6 regex | environ 70 lignes |
| N18 | `prepareTrame` : branches 0x03/0x04, 0x05/0x06 et `raw`/`hex`/`int8` identiques ; contrôle de longueur triplé dans `decrypteMSG` ; branches série et réseau de `lireMsgModbus` | `modbusFonctions.be:2706-2816`, `:2563-2615`, `:1943-2007` | environ 75 lignes |
| N19 | Drivers esclave ESP32 et carte 16 relais : pose des règles, réception/acquittement, constat ECART, remise des relais au boot, `_init` | tableau des deux plages dans le compte rendu ModBus | environ 150 lignes |
| N20 | Préambule des commandes `Reglage*` (découpage + 9 logs) | 8 fichiers | environ 45 lignes |
| N21 | Scripts de carte : couleur du niveau (`garageFonctions.be:14-28` = `cuveFonctions.be:25-41`), hauteur → volume (×3), pages thermomètres P4/cuve, initialisation des logs (×3) | lignes citées | environ 45 lignes |
| N22 | Données en double : l'`id` vit à 4 endroits forcés égaux, `IPAddress` est écrite 3 fois dans la fiche, `routagePort` se déduit de l'`id`, le `lwt` a 3 écrivains | `discoveryFonctions.be:254-283` ; `controleRangeExtender.be:44-90` | — |

Seize logs `detail` de `prepareTrame` (`:2935-2950`) et le `json.dump` de chaque réception côté
esclave (`:1029`) ne sont pas gardés par `logFonctions.actif`, contrairement à la règle 5 de la charte.
Ils sont traités en A7.

**Ordre de grandeur** : environ 2 000 lignes supprimables ou factorisables sur les ~20 500 de `data/`,
fichier en double de la cave compris (186 lignes). Environ 800 d'entre elles sont à risque nul ou faible.

**Gain en RAM** : la plupart de ces lignes sont dans des modules **solidifiés** (ModBus, réseau,
transverses). Les supprimer libère surtout de la **flash**. La RAM ne gagne vraiment qu'à quatre
endroits :
- les scripts chargés depuis le LittleFS (`cuveFonctions`, `garageFonctions`, `controleGarage`,
  `controleCuve`, `controlePompeVideCave`) ;
- les tables reconstruites à chaque tick ou à chaque trame (N5, `tabFonctionsName`) ;
- le driver TCP de la cave S3 (N6) ;
- les clés mortes du persist (A4, D9).

Ces gains seront chiffrés en A9.

### Propositions

Chaque proposition suppose d'abord son filet : banc existant, ou banc à écrire, avec un témoin négatif
qui doit échouer si la simplification casse quelque chose.

| # | Proposition | Corrige | Effort / risque | Filet | Témoin négatif |
|---|---|---|---|---|---|
| P5.1 | **Décider d'abord** si les redémarrages programmés sont voulus. Si oui, appeler la méthode (`/-> controleGeneral.heureReboot()`) et vérifier la syntaxe `*/300`. Si non, supprimer les deux crons et les clés du persist. | N1 | faible ; **décision** : comportement nouveau sur toutes les cartes | essai sur une carte remplacée | un `heureReboot` vide n'arme aucun cron |
| P5.2 | ImAlive : ranger la fiche par une fonction commune de `discoveryFonctions`, avec `memeValeur`, et n'écrire que si elle change | N2 | faible / moyen | `test_discovery` §1, 2, 7, 11 | un ImAlive identique ne réécrit pas le fichier |
| P5.3 | Cuve : lire `_Scheme` une seule fois par seconde et partager le résultat entre `ledsFonctions` et `surveilleRubans` | N3 | moyen | `banc_leds`, `banc_test_modbus` | une animation lancée par la page web est toujours poussée au maître |
| P5.4 | P4 : garder le CSS en mémoire après la première lecture, ou le servir comme fichier statique | N4 | faible | aucun (page web) | page affichée sans carte SD : message clair |
| P5.5 | Une socket par instance `CONTROLE_UDP` (lire `self.typeComm`) | N5 | faible / moyen (timing du maître) | **à écrire** : driver à 2 instances avec fausses sockets | un unicast n'est traité qu'une fois |
| P5.6 | Ne plus forcer `tcp.activation`, ne plus charger TCP sur la cave S3. Variante lourde, sur décision : retirer tout le transport TCP (environ 500 lignes avec ModBus-TCP). | N6 | faible ; lourde = moyen | `test_discovery` §14 (à adapter) ; `banc_test_modbus` §6 | `typeComm.TCP = ON` → refus journalisé, pas d'exception |
| P5.7 | Protéger la réception de la carte 16 relais par `try` avec acquittement en `except`, et **écrire son banc** | N7 | faible | **à écrire** | réponse 0x03 malformée → exception journalisée **et** file libérée |
| P5.8 | Un seul `diversFonctions.valeurScalaire(value)` pour les 5 sites ; corriger l'humidité du P4 | N8, N9 | faible / moyen | aucun ; banc `globalFonctions` à écrire | `map` à 2 clés → refus journalisé |
| P5.9 | Corriger les compteurs et logs de `configDevices` | N10 | faible | aucun | carte avec une analogique réelle → `reels = 1` |
| P5.10 | **Lot « code mort »** : fonctions sans appelant, branches inatteignables, blocs commentés, callbacks vides, `etatCapteurs`, `/wss`, `any_key`. Chaque suppression est précédée d'une recherche à 0 résultat sur `data/`. | N11 et code mort | faible (environ 800 lignes) | `banc_test_modbus`, `test_discovery`, `verifie_berry` | les deux bancs restent verts ; `/wss` → 404 |
| P5.11 | **Lot « petits helpers »** : `relaisLie`, `deviceActif`, `gestionFileFolder.readJson`, `macSansDeuxPoints`, `decoupeCommande` | N12, N14, N16, N20 | faible | bancs partiels ; banc `globalFonctions` à écrire | fichier JSON absent → `nil` ; commande sans espace → paramètres vides |
| P5.12 | **Lot « factorisations »** : groupes de `changementEtatCapteur` et `configDevices`, itérateur de devices, itérateur de fiches, `prepareTrame`/`decrypteMSG` | N13, N15, N17, N18 | moyen (fort pour `configDevices`) | `banc_test_modbus` §2-31 ; reste à écrire | vecteurs CRC de `PROTOCOLE_MODBUS.md` §8 ; `SwitchMode` 2 inversé |
| P5.13 | Base commune aux deux drivers d'esclave, **seulement après** le banc de P5.7 | N19 | fort | P5.7 | trame hors séquence → pas d'acquittement ; M0 connecté → ordre inversé |
| P5.14 | Module commun pour les cartes cuve et P4 (couleur, volume, page thermomètre, logs) | N21 | moyen | aucun (cartes réelles) | niveau en erreur → bordure rouge clignotante |
| P5.15 | Une seule source pour chaque donnée de la fiche : `routagePort` et `rangeExtender.id` déduits de l'`id`, `IPAddress` écrite une fois | N22 | moyen ; décision (format lu par les outils PC) | `test_discovery` | page `/discovery` et sniffeur MQTT inchangés |

Ordre conseillé :
1. P5.1 (décision), P5.2, P5.3, P5.4 et P5.7 : de vrais défauts, à faible coût.
2. P5.10 et P5.11 : beaucoup de lignes en moins, risque faible.
3. Écrire les bancs manquants (carte 16 relais, `globalFonctions`, driver UDP).
4. Ensuite seulement P5.12 à P5.15.

## A6 — Niveaux de log : le mécanisme (2026-10-22)

Lecture de `data/fs/logFonctions.be` et de ses appelants. Les comportements marqués (T) sont prouvés par
un test Berry sur le vrai `logFonctions.be`, avec un persist simulé (`scratchpad/a6/t.be`). Les
lignes clés ont été relues dans le fil principal.

### Ce qui est en place

**Chemin d'un message.** `logFonctions.log(msg, niveau, cible)` (`:136-143`) :

1. Un message `erreur` (1) passe toujours.
2. Sinon, il est comparé au seuil de sa cible : `general` par défaut.
3. Un `detail` (4) est ramené à 3, puis transmis à `log()` du firmware.

Chaque sortie du firmware (série, web, MQTT, syslog) filtre ensuite avec son propre seuil.
`logFonctions.actif(niveau, cible)` (`:148-151`) combine le seuil du module et `tasmota.loglevel()`.
Ce dernier répond vrai si **au moins une** sortie accepte le message.

**Seuils des modules.**
- `seuil(cible)` (`:107-131`) lit la clé `log` du bloc trouvé par `lieu(cible)`, et met le résultat
  en cache dans `etat()["seuils"]`.
- Seul `regle()` invalide ce cache, c'est-à-dire la commande `ReglageLog`.
- Une cible que `lieu()` ne connaît pas reçoit le seuil `info` (2), lui aussi mis en cache.

**Seuils des sorties.**
- `appliqueProfil()` (`:197-215`) est appelé une fois au démarrage (`configGlobal.be:236`), puis à
  chaque `ReglageLog profil|<sortie>`.
- Il n'envoie `SerialLog N`, `WebLog N`, `MqttLog N` ou `SysLog N` que si la valeur diffère de celle
  du firmware.

**`ReglageLog`** (`:397-418`, `regle` `:265-319`) :

| Forme | Effet |
|---|---|
| sans argument | état : sorties, modules, profils. Lecture seule. |
| `profil <nom>` | change le profil actif puis l'applique |
| `<sortie> <niveau>` | modifie le profil **actif** |
| `<cible> <niveau>` | règle le seuil d'un module |
| `tous <niveau>` | règle toutes les cibles de `CIBLES` présentes sur la carte |

Toute écriture est suivie de `persist.dirty()` puis `persist.save()` : le réglage survit au
redémarrage (T). Une cible, un niveau ou un profil inconnus donnent une réponse d'erreur explicite (T).

**Fichiers de log.**
- `diverses.logs.nbLogsFiles` (0 sur les 5 cartes) déclenche `FileLog N` au démarrage
  (`configGlobal.be:240-243`).
- `modules.<x>.logs.nbLogsFiles` (15 partout) n'est lu que par `controleGarage` et `controleCuve`. Ces
  deux scripts arment chacun un cron de 60 s pour `gestionFileFolder.enregistreLogs`.

**Profils des persists du dépôt** : le profil actif est `debug` sur les 5 cartes, avec tous les modules
à `detail`.

| Carte | `normal` (série / web / MQTT / syslog) | `debug` (série / web / MQTT / syslog) |
|---|---|---|
| P4, cave S3, différentiel | info / info / erreur / info | debug / debug / **debug** / debug |
| cuve, rideau | info / info / erreur / info | debug / debug / erreur / debug |

### Avantages

- Un seul point de passage, deux filtres simples : le comportement est prévisible et testable.
- `detail` est ramené à 3 : le niveau 4 du firmware reste réservé à ses propres traces (`BRY: GC`).
- `ReglageLog` règle tout depuis une seule commande, persiste ses réglages et explique ses erreurs.
- Les profils séparent ce qu'on veut **voir** (sorties) de ce que chaque module **produit** (seuils).
  Passer de `normal` à `debug` tient en une commande.
- `appliqueProfil` n'émet de commande que si la valeur change : pas d'écriture inutile en flash.
- Le cache évite de relire le persist à chaque log, sur les chemins chauds (`every_100ms`).

### Inconvénients et défauts constatés

| # | Constat | Preuve | Cote |
|---|---|---|---|
| L1 | **La cible de l'historique est inconnue** : `historiqueFonctions` passe `nom`/`self.nom`, qui vaut `"mesures"` (`:131`, `:239`, `:248`, `:286` ; instance `:409`). Cette cible n'est pas dans `CIBLES`, et `lieu()` renvoie `nil`. Le seuil est donc figé à `info`, les messages `debug` sont perdus, et `ReglageLog` refuse de régler cette cible. | (T) ; `logFonctions.be:100`, `:113-129` | G |
| L2 | **6 clés `log` sans cible** : `drivers.KNX.log`, et `modules.<x>.log` pour `rideau`, `pompeVideCave`, `Thermo-Hygrometre`, `autres` et `differentiel`. Elles valent `detail` mais ne règlent rien, et `ReglageLog tous` les ignore : il ne parcourt que `CIBLES`. Leurs modules loguent sans cible, donc au seuil `general`. | grep des appels ; persists | G |
| L3 | **Le cache des seuils n'est invalidé que par `ReglageLog`.** Une modification du persist par une autre voie (éditeur web du persist `controleWeb.be:208-227`, `ReglageGlobal`) n'agit qu'après redémarrage. | (T) | L |
| L4 | **Le défaut `info` d'un bloc absent est mis en cache.** Si le bloc apparaît plus tard, par exemple un driver réveillé après la veille de `hiberneDriversInactifs`, le seuil reste à `info`. | `logFonctions.be:113-129` (lecture) | L |
| L5 | **Une faute de frappe dans une cible passe en silence** : elle reçoit `info`, sans le moindre avertissement. | (T) | L |
| L6 | **Un réglage manuel d'une sortie (`SerialLog 4`…) est écrasé** au redémarrage suivant, ou au prochain `ReglageLog`, par le profil du persist. C'est voulu, mais ce n'est écrit nulle part. Interaction avec `SERIALLOG_TIMER`, en constat seulement : quand `appliqueProfil` envoie un `SerialLog` différent, `SetTasConlog` remet le compte à rebours à zéro (`support.ino:2463-2466`). Sinon, la coupure à 600 s a lieu. | lecture du firmware | D |
| L7 | **`actif()` répond « au moins une sortie »** : un message gardé par `actif` est quand même construit si seule la série est à `debug`, même quand on ne regarde que syslog. C'est correct, mais l'économie est moindre qu'annoncé. | `:148-151` | D |
| L8 | `modules.<x>.logs.nbLogsFiles` et `fileLogName` sans lecteur sur la cave et le différentiel. Le rideau les lit, mais son `enregistreLogs` est vide. Deux conventions de sauvegarde : `ReglageGlobal nbLogsFiles` fait `persist.save(true)`, `ReglageLog` fait `dirty()` puis `save()`. | grep | S |
| L9 | `regle("profil","NORMAL")` appelé directement plante : `trouveCle` ne passe pas en minuscules. Par la commande, aucun problème, puisque tout est mis en minuscules avant. | (T) | L |

### Propositions

- **P6.1** — Donner une cible réglable à l'historique : ajouter `historique` à `CIBLES`, avec un
  `lieu` sur `diverses.historique`, et la passer à la place de `self.nom`. Corrige L1.
  *(faible ; banc : `banc_historique.be`, témoin : `ReglageLog historique debug` doit faire apparaître le
  message de `:131`)*
- **P6.2** — Choisir pour les 6 clés orphelines : soit créer leurs cibles (et passer la cible dans les
  modules concernés), soit retirer les clés des persists. Corrige L2. *(faible ; décision)*
- **P6.3** — Vider `etat()["seuils"]` après toute écriture du persist faite hors `ReglageLog`, et ne
  pas mettre en cache le défaut d'un bloc absent. Corrige L3 et L4. *(faible ; une ou deux lignes ;
  test Berry existant à réutiliser)*
- **P6.4** — Journaliser une fois en `erreur` toute cible inconnue de `lieu()`, au premier appel.
  Corrige L5. *(faible ; témoin : une cible connue ne produit aucun message)*
- **P6.5** — Documenter dans `README.md` § logs que le profil du persist fait foi sur les sorties, avec
  l'effet sur `SERIALLOG_TIMER`, et que `actif()` regarde la sortie la plus bavarde. Corrige L6 et L7.
  *(documentation)*
- **P6.6** — Harmoniser la sauvegarde du persist (`dirty()` + `save()` partout), et retirer les clés
  `nbLogsFiles`/`fileLogName` sans lecteur. Corrige L8. *(faible)*

## A7 — Niveaux de log : conformité et sorties (2026-10-22)

Deux sources :
- **Le code** : analyse statique des 54 `.be` hors `*sauvegarde*`, par un script reproductible
  (`scratchpad/a7/audit_logs.py`, sortie exhaustive dans `rapport_logs.txt`).
- **Les cartes** : **observation passive** de 10 min 36 s, le 2026-10-22 : lancée à 04:00:44, analysée à 04:11:27 sur les 636 s reçues.
  Serveur syslog et sniffeur MQTT lancés hors PlatformIO, en `--local`, puis arrêtés. Rien n'a été
  envoyé aux cartes. La lecture `ReglageLog` des cartes, prévue en lecture seule, a été **refusée par
  le classifieur de permissions** : elle reste à faire par l'utilisateur (voir P7.7).

### Ce qui est en place

**Volume dans le code** : 850 appels de log, dont 746 dans `data/fs`.

| Niveau | Appels | Part |
|---|---|---|
| `erreur` | 111 | 13 % |
| `info` | 76 | 9 % |
| `debug` | 260 | 31 % |
| `detail` | 400 | 47 % |

Fichiers les plus bavards : `modbusFonctions` (141), `modBus_TasmotaSlaveModBus` (73),
`globalFonctions` (57) et `discoveryFonctions` (50).

**Chaîne syslog** :
- `SYS_LOG_HOST` = 192.168.0.3 (ce PC), port 514, `SYS_LOG_LEVEL` = debug à la compilation.
- `syslog_tasmota.py` range les messages par **nom d'hôte** et confond `debug` et `detail` (PRI 135),
  comme le firmware.

**Ce que les cartes ont réellement émis pendant l'observation** :

| Carte | Syslog | MQTT `stat/<topic>/LOGGING` | Remarque |
|---|---|---|---|
| P4 (`SERVEUR-GARAGE`) | 292 lignes/min (44,8 Ko/min), 98 % `debug` | **316 messages/min (30,4 Ko/min)** | profil `debug` avec MQTT à `debug`, comme dans le persist |
| cuve (`CAPTEURS-CUVE`) | 276 lignes/min (37,9 Ko/min), 97 % `debug` | aucun | MQTT à `erreur` : conforme au persist et à la leçon NAPT |
| cave (`SERVEUR-RLY-CAVE`) | 54 lignes/min, tout en `INFO`, dont `GC` Berry et échos MQTT | aucun | ancien code (voir A1) ; capteur `Pin22 timeout`, 163 fois |
| différentiel | rien | aucun | framework du dépôt non chargé (voir A1) |
| rideau | — | — | `Offline` |

- Aucun message de sévérité `ERR` en 10 minutes.
- Sur le P4 comme sur la cuve, environ 30 % du syslog vient de `PREPARE_TRAME_MODBUS`, 20 % de
  `DECRYPTE_MSG_MODBUS` et 12 % de `EXECUTE_CMD_MODBUS` : les traces de **chaque** échange ModBus en
  UDP.
- Chaque réception ModBus/UDP est aussi publiée en `tele/<topic>/RESULT` (`ModbusReceivedUDP`, environ
  6 par minute et par carte). Chaque publication est elle-même renvoyée en syslog par le firmware
  (`MQT:`).

### Avantages

- Le contournement de la charte est **rare** :
  - un seul `log()` direct (`controleES8311.be:373`) ;
  - aucune constante de niveau étrangère au jeu de 4 ;
  - aucun appel sans niveau.
- 13 % des appels sont des erreurs, toujours émises : on les retrouve même log éteint.
- Les préfixes sont conformes à 96 % : le filtrage par texte dans la page syslog fonctionne.
- La cuve respecte la leçon des esclaves derrière le NAPT (MQTT à `erreur`) : pas de plantage par
  `MqttLog`.
- Le syslog a tenu le débit observé (près de 10 lignes/s cumulées) sans perte visible.

### Inconvénients et défauts constatés

| # | Constat | Preuve | Cote |
|---|---|---|---|
| C1 | **Le P4 publie environ 316 logs par minute sur le broker** (`MqttLog` à `debug` dans son profil actif) : 30 Ko/min, environ 43 Mo/jour, à travers le Wi-Fi qui porte aussi le ModBus/UDP. Les esclaves s'en gardent (leçon du 2026-10-11) ; le maître non. | observation ; persist du P4 | G |
| C2 | **Toutes les cartes tournent en profil `debug`**, avec tous les modules à `detail`, alors que l'exploitation voulue est `normal` partout (réponse de l'utilisateur du 2026-10-22). Un échange ModBus produit à lui seul environ 45 lignes de trace. | persists ; observation | G |
| C3 | **6 `print('Erreur: ', e, " -> ", m)` dans des `except`** (`modbusFonctions.be:224`, `:2248`, `:2422` ; `udpFonctions.be:281`, `:365`, `:378`) : ils ne passent par aucun seuil, n'ont pas de préfixe, ne vont qu'en série, et **n'atteignent donc ni le syslog ni MQTT**. Les autres `print` actifs (10) sont l'aide des commandes : légitimes. | lignes relues | G |
| C4 | **La règle 5 est presque ignorée** : 152 messages `debug`/`detail` coûteux ne sont pas gardés par `actif()`, dont 52 sur un chemin fréquent. Une vingtaine sont lourds (`tohex`, `json.dump`, `format` à 4 arguments ou plus) : `lireMsgModbus` (`:1935`, `:1977`), `lireUDP` (`:832-834`), `recupereReponseModBus` (`modBus_TasmotaSlaveModBus.be:988`, `:1029`), `executeCmdModbus` (`:2274`). Seuls `historiqueSeries.be:152` et `modbusFonctions.be:2449` appliquent la garde. En profil `normal`, ces chaînes sont construites puis jetées. | `rapport_logs.txt` §E | G |
| C5 | **Règle 4, sur le P4 en service** : deux `info` dans `web_sensor` (`controleGarage.be:215`, `:248`), une ligne par valeur à chaque rafraîchissement de page. La charte ne cite pas `web_sensor` parmi les callbacks fréquents. `cuveFonctions.be:580` (`sensorsCuve=%s`, `info`) n'est pas apparu en 10 minutes : le chemin est donc rare. | lignes relues ; observation | G |
| C6 | **Échecs logués trop bas** : l'échec d'initialisation de l'ES8311 en `debug` (`controleES8311.be:23`, `:38`, `:210`), et le `tasmota.log` direct de `:373`. Fiche absente de discovery, donc ImAlive non envoyé, en `debug` (`udpFonctions.be:268`). À arbitrer selon le bruit du bus : trame reçue avec erreur en `detail` (`modbusFonctions.be:1945`, `:1984`), réponse hors séquence rejetée en `debug` (`:1405`, `:1419`), délai de réponse isolé en `debug` (`:963`). | `rapport_logs.txt` §C | L |
| C7 | **8 `except` sans `_ERREUR` dans le préfixe**, tous au bon niveau `erreur` : `discoveryFonctions.be:345`, `:373`, `:442`, `:507`, `:574`, `:717`, `modBus_TasmotaSlaveModBus.be:1227`, `ledsFonctions.be:171`. Une recherche de `_ERREUR` dans le syslog ne les trouve pas. | §B | L |
| C8 | Préfixes non conformes : `ReglageUDP:` en CamelCase (`udpFonctions.be:233`, `:247`), messages ES8311 en anglais (7), un message sans préfixe (`modbusFonctions.be:509`). | §B | D |
| C9 | Le syslog est le seul relais permanent des logs, et il dépend du **PC de développement allumé**, à une IP qui doit rester 192.168.0.3 (bail DHCP fixe, à poser). Le firmware confond `debug` et `detail` dans la sévérité : le filtre de la page ne les sépare pas. | `user_config_override.h:142` ; `syslog_tasmota.py:8` | D |
| C10 | La charte ne dit ni comment écrire un niveau variable (3 cas dans `modbusFonctions`, `:899`, `:1209`, `:2334`), ni que `web_sensor`/`json_append` comptent parmi les chemins fréquents. | charte | D |

### Propositions

- **P7.1** — Passer les cartes au profil `normal`, comme décidé : `ReglageLog profil normal` sur
  chaque carte, puis aligner les persists du dépôt (`diverses.logs.profil`). Le P4 en premier
  (C1). Repasser en `debug` seulement le temps d'une mise au point. Corrige C1 et C2.
  *(nul ; une commande par carte ; témoin : `stat/garage/LOGGING` doit tomber à 0 message/min, le syslog à
  quelques lignes `info`)*
- **P7.2** — Ramener aussi les seuils des modules à `info` (`ReglageLog tous info`). Le profil seul
  garde les sorties à `info`, mais les modules à `detail` continuent de construire leurs chaînes
  (C4). *(nul)*
- **P7.3** — Remplacer les 6 `print` d'`except` par `xxxFonctions.log("…_ERREUR: …", LOG_LEVEL_ERREUR)`.
  Corrige C3. *(faible ; bancs : `banc_test_modbus`, `test_discovery`)*
- **P7.4** — Garde de coût sur les chemins chauds : une variable `var detail =
  logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, cible)` en tête de `lireMsgModbus`, `lireUDP`,
  `executeCmdModbus` et `recupereReponseModBus`, sur le modèle de `modbusFonctions.be:2449`. Corrige
  C4. *(moyen ; risque moyen, chemin chaud ; banc ModBus ; RAM et charge à mesurer avant/après en A9)*
- **P7.5** — Corrections ponctuelles : `info` → `detail` dans `controleGarage.web_sensor` ; ES8311 en
  `erreur`, avec préfixe français et sans `tasmota.log` ; `_ERREUR` dans les 8 `except` ; préfixes
  `REGLAGE_UDP:`. Trancher la politique « trame rejetée / délai isolé » (`debug` ou `erreur`). Corrige
  C5 à C8. *(faible ; une décision)*
- **P7.6** — Contrôle automatique de la charte dans `verifie_berry.py` (donc dans le hook d'édition),
  en **avertissements** (code de sortie 0) et non en erreurs : `print`/`log()` direct, préfixe, `_ERREUR`
  dans `except`, `info` dans un callback fréquent, `json.dump`/`tohex` non gardés. Le script d'audit
  `audit_logs.py` en fournit la base. Compléter la charte (C10). *(moyen ; risque faible)*
- **P7.7** — **À faire par l'utilisateur** (lecture seule, refusée à Claude) : envoyer `ReglageLog`
  sans argument à chaque carte et relever le profil et les seuils réellement en vigueur. Depuis le
  sniffeur MQTT (:7100) : topic `cmnd/garage/ReglageLog`, payload vide. Faire de même pour
  `jardin/cuve`, et `garage/rideau` une fois en ligne.
- **P7.8** — Fixer l'IP du PC syslog par un bail DHCP. Ou, pour ne plus dépendre du PC, envoyer le
  syslog au Pi `SERVEUR-BUREAU`, qui fait déjà tourner Node-RED/InfluxDB. Corrige C9.
  *(faible ; décision)*

## A7 — Niveaux de log : conformité et sorties

*À faire.*

## A8 — Communications entre modules et ESP-NOW

*A8.1 et A8.2 : le 2026-10-21, à la demande de l'utilisateur. A8.3 à A8.6 : le 2026-10-22, par lecture du
code et des documents, plus une recherche web. Les constats locaux et l'issue Espressif ont été vérifiés
dans le fil principal.*

### A8.1 — TasMesh, la maille ESP-NOW du firmware Tasmota

#### Ce qui est en place

- Driver amont `xdrv_57` : `tasmota/tasmota_xdrv_driver/xdrv_57_1_tasmesh_support.ino` (400 lignes) et
  `xdrv_57_9_tasmesh.ino` (914 lignes). Écrit en 2020-2021 (version 0.9.5.1), depuis lors retouché
  seulement pour l'entretien ; dernier correctif le 2026-05-30 (`7a2fbbe7b`, « Tasmesh safety fixes »).
- Activé par `#define USE_TASMESH` (+11 Ko de code), option `USE_TASMESH_HEARTBEAT`. **Désactivé partout**
  dans ce fork : la ligne est commentée dans les 7 sections de `tasmota/user_config_override.h`
  (`:1117`, `:1741`, `:2046`, `:2188`, `:2356`, `:2530`, `:2702`).
- Aucun script Berry du dépôt ne l'utilise.

#### Ce qu'elle peut réaliser

TasMesh est un **relais MQTT par ESP-NOW** : il n'échange pas de données entre modules, il transporte
leurs messages MQTT.

- Un **broker** (forcément un ESP32) reste connecté au Wi-Fi et au serveur MQTT (`MeshBroker`).
- Des **nœuds** se passent du Wi-Fi : leurs publications MQTT sont détournées juste avant l'envoi
  (`MESHrouteMQTTtoMESH`, appelé par `xdrv_02_9_mqtt.ino:598`) et confiées au broker par ESP-NOW. Le broker
  les publie à leur place (`xdrv_57_9_tasmesh.ino:557`).
- Le broker s'abonne à `cmnd/<topic du nœud>/#` pour chaque nœud et lui relaie ces commandes
  (`MESHinterceptMQTTonBroker`, appelé par `xdrv_02_9_mqtt.ino:980`).
- Les nœuds « complets » réémettent ce qu'ils entendent (durée de vie de 2 sauts) : petite maille.
- Le broker distribue l'heure (toutes les 30 s, ou à la demande) et, avec `USE_TASMESH_HEARTBEAT`,
  publie le LWT `Online`/`Offline` des nœuds.
- Charge utile chiffrée (ChaCha20-Poly1305).
- Commandes : `MeshBroker`, `MeshNode <MAC du broker>`, `MeshPeer <MAC>`, `MeshChannel`, `MeshInterval`.
  La page d'accueil du broker liste les nœuds (MAC, âge du dernier message, topic), et la télémétrie
  porte un bloc `MESH`.

Usage visé par ses auteurs : des capteurs **ESP8266** sur batterie ou hors de portée du Wi-Fi, qui
remontent en MQTT par l'intermédiaire d'un ESP32.

#### Avantages

- Déjà dans le firmware : un `#define`, deux commandes et une règle suffisent pour son usage prévu.
- Transparent pour MQTT : le nœud publie et reçoit comme s'il était connecté.
- Pas d'association Wi-Fi ni d'adresse IP pour les nœuds : démarrage rapide, consommation réduite.
- Charge utile chiffrée et authentifiée.

#### Inconvénients et limites constatés

| # | Constat | Preuve | Cote |
|---|---|---|---|
| T1 | **Un ESP32 ne peut être que broker. Le rôle de nœud n'existe que sur ESP8266.** Aucune carte du parc (ESP32, ESP32-S3, ESP32-P4) ne peut donc être nœud. | `xdrv_57_9_tasmesh.ino:382` (`#ifdef ESP8266 // for now only ESP8266`), `:794` (`#ifndef ESP32 // only ESP8266 current supported as node`), `:786` | rédhibitoire pour le parc |
| T2 | **Le P4 n'a pas ESP-NOW** avec le framework installé : il ne pourrait même pas être broker. Le P4 n'a pas de radio, et la bibliothèque qui relaie le Wi-Fi vers son coprocesseur C6 n'exporte aucune fonction `esp_now_*`. | Aucune bibliothèque de `esp32-arduino-libs/esp32p4/lib` n'exporte `esp_now_send` (`nm`) ; `libespressif__esp_wifi_remote.a` n'expose que des `esp_wifi_*`. Témoin : `esp32s3/lib/libespnow.a` exporte `esp_now_send` | rédhibitoire pour le maître du garage |
| T3 | Toujours en **diffusion** (broadcast) : pas d'accusé de réception au niveau radio, pas de réémission. Une trame perdue l'est en silence. | `xdrv_57_1_tasmesh_support.ino:333` (`esp_now_send(NULL, …) //NULL -> broadcast`) | G |
| T4 | Charge utile de **160 octets, topic compris**. Du broker vers le nœud : un seul fragment, abandon au-delà. Côté nœud, la réception en plusieurs fragments n'est pas gérée. | `xdrv_57_1_tasmesh_support.ino:38` ; `xdrv_57_9_tasmesh.ino:254` (`Intercept payload oversized`), `:283` (`Multiple chunks … not supported yet`) | G |
| T5 | Anti-doublon limité aux 3 derniers paquets reçus. | `xdrv_57_1_tasmesh_support.ino:41` (`MESH_MAX_PACKETS 3`) | L |
| T6 | La clé de chiffrement est le **mot de passe Wi-Fi** (ses 32 premiers caractères) : quiconque le connaît lit et forge les trames. *Constat seulement : le choix du mot de passe n'est pas remis en cause.* | `xdrv_57_1_tasmesh_support.ino:336-337` | constat |
| T7 | Le broker force le mode AP+STA et démarre un point d'accès ; les pairs sont déclarés sur l'interface AP. L'interaction avec le point d'accès du Range Extender n'est ni documentée ni testée. | `xdrv_57_9_tasmesh.ino:425` (`WiFi.AP.begin()`), `xdrv_57_1_tasmesh_support.ino:274` (`ESP_IF_WIFI_AP`) | L |
| T8 | Tout passe par le **serveur MQTT externe** : aucun échange direct entre modules. Si le serveur MQTT tombe, plus rien ne circule. | `xdrv_57_9_tasmesh.ino:557`, `:220-:270` | G |
| T9 | **Aucune interface Berry** : on ne peut ni envoyer ni recevoir une trame ESP-NOW quelconque depuis un script, seulement passer par les commandes `Mesh…` et les règles. | Pas de module `espnow` dans `lib/libesp32/berry_tasmota` ni `berry_mapping` (recherche `esp_now`/`espnow`) | G |
| T10 | **Régression probable du correctif du 2026-05-30** : la garde compare la longueur du topic reçu complet (`cmnd/<nœud>/<Commande>`) à celle de `cmnd/<nœud>/`. Elles diffèrent toujours, donc la fonction renvoie `false` et les commandes ne seraient plus jamais relayées vers les nœuds. Ce `return` sort aussi de la boucle dès le premier nœud. *Déduit du code (le topic reçu est le topic complet, `xdrv_02_9_mqtt.ino:970`), non vérifié par un essai : pas d'ESP8266 au parc.* | `xdrv_57_9_tasmesh.ino:247-249`, diff de `7a2fbbe7b` (avant : `strlen(_topic) != strlen(_topic)`, condition toujours fausse) | L (amont) |
| T11 | Un nœud qui n'entend plus le broker pendant 70 s quitte la maille et relance le Wi-Fi. | `xdrv_57_9_tasmesh.ino:683` | constat |

#### Difficulté de mise en place

- **Pour son usage prévu** (nœuds ESP8266 → broker ESP32) : **faible** (un `#define`, un build,
  `MeshBroker` dans une règle `System#Boot`, `MeshNode <MAC>` sur chaque nœud).
- **Pour les cartes de ce parc** : **impossible en l'état** (T1, T2). Il faudrait porter le rôle de nœud
  sur ESP32 dans un driver amont : effort **moyen à élevé**, en C++, avec un conflit à chaque
  synchronisation du fork. On garderait en plus toutes les limites T3, T4, T8 et T9.

#### TasMesh peut-il porter le ModBus entre les modules ?

**Non, pas dans ce parc.**

- *En théorie*, le maître publierait `cmnd/<nœud>/ModBusSend …`. Le broker relaierait cette commande au
  nœud, qui l'exécuterait sur son bus série, et la réponse (`ModbusReceived`) remonterait par MQTT.
- *En pratique*, cinq obstacles :
  1. les nœuds ne peuvent être que des ESP8266 (T1), et le maître P4 n'a pas ESP-NOW (T2) ;
  2. chaque échange fait l'aller-retour par le serveur MQTT externe (T8) : latence, dépendance au
     serveur, et c'est précisément le chemin qui a déjà fait planter un esclave derrière le NAPT
     (MqttLog de la cuve, octobre 2026) ;
  3. 160 octets topic compris, en diffusion sans accusé (T3, T4) ;
  4. le sens maître → nœud serait aujourd'hui bloqué par T10 ;
  5. le ModBus maison (`ModbusUDP`, `ModbusPushUDP`, numéros de séquence et `accepteSeq`) n'a aucun
     moyen de passer : pas d'interface Berry (T9).

#### Propositions

- **P8.1** — Ne pas retenir TasMesh pour les communications du garage. *(S, effort nul)*
- **P8.2** — Si l'on veut un jour des capteurs ESP8266 sur batterie remontés par MQTT, TasMesh est la
  bonne brique, sur un broker **ESP32 ou S3** (pas le P4). Contrôler alors T10 dès le premier essai.
  *(effort faible, risque faible)*
- **P8.3** — Signaler T10 à l'amont (issue arendst/Tasmota) une fois confirmé par un essai.
  *(D, effort faible)*

### A8.2 — Un ESP32 ou un ESP32-S3 peut-il être esclave ESP-NOW ?

#### Ce que permettent la puce et le SDK installé

**Oui.** Côté matériel et SDK, rien ne s'y oppose :

- `libespnow.a` est présent pour l'ESP32 et l'ESP32-S3 dans `framework-arduinoespressif32/tools/esp32-arduino-libs/`
  (`esp32s3/lib/libespnow.a` exporte `esp_now_send`).
- ESP-NOW **coexiste avec le Wi-Fi** (STA et AP), à une condition : tous les pairs émettent sur **le même
  canal**. Un esclave connecté au point d'accès du maître Range Extender est automatiquement sur le canal
  de ce maître : la condition est remplie d'elle-même.
- En envoi **unicast**, la radio fait un accusé de réception et des réémissions, et le programme reçoit
  l'état de chaque envoi par une fonction de rappel.
- Limites du SDK (`esp32s3/include/esp_wifi/include/esp_now.h`) : 20 pairs au plus
  (`ESP_NOW_MAX_TOTAL_PEER_NUM`, `:32`), dont 7 chiffrés (`CONFIG_ESP_WIFI_ESPNOW_MAX_ENCRYPT_NUM=7`,
  `esp32s3/sdkconfig:1868`). Une trame porte 250 octets en v1 et jusqu'à 1470 octets en v2
  (`ESP_NOW_MAX_DATA_LEN_V2`, `:37`). Les deux bouts doivent être en v2 pour en profiter : à vérifier
  avant de s'y fier.

#### Ce qui manque dans ce dépôt

- Aucune commande Tasmota ni interface Berry pour un ESP-NOW générique. TasMesh ne propose pas le rôle de
  nœud sur ESP32 (A8.1, T1, T9).
- La bibliothèque Arduino `ESP_NOW` (classes de pairs, core Arduino 3.x) n'est **pas** fournie par le
  framework utilisé par Tasmota : `framework-arduinoespressif32/libraries/` n'en contient pas.
- **Le maître du garage est le P4, qui n'a pas ESP-NOW** (T2).

#### Avantages attendus pour ce parc

- **On sort d'IP** : ni NAPT, ni multicast, ni chevauchement du sous-réseau 192.168.4.1/24. Ce sont
  précisément les causes des défauts UDP diagnostiqués le 2026-10-17 (`DIAGNOSTIC_UDP_2026-10-17.md`).
  L'adresse d'un esclave devient sa MAC, que la table discovery connaît déjà.
- Accusé radio et réémissions en unicast, là où l'UDP multicast n'en a pas.
- Latence de l'ordre de la milliseconde, sans association ni pile TCP/IP. *Ordre de grandeur annoncé par
  Espressif, à mesurer.*
- Les trames du ModBus maison sont petites : une requête fait 8 octets, une réponse de registres quelques
  dizaines. Elles tiennent dans une trame v1, avec leur numéro de séquence.

#### Inconvénients et risques

- Il faut du **C++** dans le fork : un driver, ou une liaison Berry. C'est du code à maintenir et à
  garder compatible à chaque synchronisation avec l'amont.
- Canal imposé : si le maître change de canal (la box en change), tous les pairs doivent suivre. Un
  esclave Range Extender suit, puisqu'il est associé au point d'accès du maître ; un pair qui ne serait
  pas associé, non.
- Pas de garantie de livraison au-delà des réémissions radio : la reprise reste à la charge du protocole
  (le mécanisme seq/`accepteSeq` existant s'y prête).
- 7 pairs chiffrés au plus.
- Le **P4 ne peut pas y participer** sans intermédiaire.

#### Voies possibles et difficulté

| Voie | Principe | Difficulté | Remarque |
|---|---|---|---|
| a | Porter le rôle de nœud de TasMesh sur ESP32 | moyenne à élevée | On resterait sur un modèle de relais MQTT, avec T3, T4, T8 et T9 : peu d'intérêt |
| b | **Petit driver C++ propre au fork**, dans un fichier dédié (pas dans un fichier amont) : `EspNowPeer <MAC>`, `EspNowSend <MAC> <hexa>`, réception remontée à Berry par un événement de règle | moyenne | Maîtrise totale ; transporterait les trames `ModbusUDP`/`ModbusPushUDP` presque telles quelles ; peu de conflits de synchro |
| c | Module Berry natif `espnow` (liaison C) : `espnow.send(mac, bytes)` et une fonction de rappel de réception | moyenne à élevée | Le plus propre côté Berry ; plus de code de liaison à écrire et maintenir |
| d | Ne rien ajouter : garder l'UDP corrigé (C1 à C6, validés le 2026-10-17) | nulle | Référence de comparaison |

Avec un maître P4, deux montages se présentent : (i) une carte S3 « passerelle ESP-NOW », reliée au P4 par
une liaison qui existe déjà, ce qui ajoute un saut ; (ii) ESP-NOW limité aux échanges entre S3, le P4
restant en UDP et en ModBus filaire. Une troisième piste reste à confirmer par la recherche GitHub d'A8 :
un firmware `esp_hosted` du C6 qui relaierait ESP-NOW au P4.

#### Propositions

- **P8.4** — Avant tout développement, un **essai de faisabilité borné** sur deux S3 (la cuve et une S3
  de banc) avec la voie b : latence, pertes, coexistence avec le point d'accès Range Extender, effet sur
  le tas. Comparer aux mesures UDP. ModBus filaire conservé, retour arrière par simple réglage.
  *(effort moyen, risque faible)*
- **P8.5** — Trancher la question du P4 (passerelle S3, ou ESP-NOW réservé aux S3) seulement après
  P8.4 et la recherche GitHub. *(décision)*

### A8.3 — Les voies en place

Garage seulement. La cave en service exécute l'ancien code (A1), le grenier est en sommeil.

| Voie | Sens | Déclencheur | Accusé / reprise | Code | État |
|---|---|---|---|---|---|
| ModBus RTU (RS485) | P4 → carte 16 relais | relevé toutes les 30 s, commandes | un message en vol, délai de 5 s, 3 essais puis abandon ; environ 2 ms par échange | `modbusFonctions`, `modBus_Conn16channels` | en service |
| ModBus RTU (RS485) | P4 → rideau | idem | idem ; esclave déclaré muet après 3 × 30 s | `modBus_TasmotaSlaveModBus` | en service (rideau `Offline` le 2026-10-22) |
| `ModbusUDP <tid> <hexa>` | P4 → cuve en unicast, réponse en unicast | commandes et relevés (`voieCommandes: UDP`) | `tid` renvoyé, délai de 2000 ms, renvoi au même `tid` ; pas de repli série | `udpFonctions.envoiUDP`, `modbusFonctions.repondUDP` | en service pour la cuve depuis le 2026-10-21 |
| `ModbusPushUDP <seq> <hexa>` | esclave → maître, multicast 224.3.0.1:4000 | changement d'état | aucun accusé ; filtre `accepteSeq` ; une perte est réparée par le relevé suivant (moins de 30 s) | `udpFonctions.be:784-806` | en service |
| `ImAlive` | esclave → maître, multicast | démarrage, puis toutes les `telePeriod` (300 s) | aucun accusé ; le maître répond `Timestamp` et `ipMaitre` en unicast | `udpFonctions.be:288-350` | en service |
| Discovery MQTT | chaque carte → broker → maître (`tasmota/discovery/<MAC>/…`, retenu) | `Mqtt#Connected` | conservé par le broker | `discoveryFonctions.be:357-370` | en service |
| LWT MQTT | broker → maître | perte de session | retenu | `discoveryFonctions.be:515` | en service |
| HTTP par RgxPort (8080 + id − 1) | navigateur → P4 → esclave:80 (NAPT) | `RoutageRangeExtender` au boot du maître | table de 10 cases | `rangeExtenderFonctions.be:35`, `:263` | en service |
| `tele/<topic>/MODBUSPUSH` | maître → PC | push reçu, si `RelaisPushMQTT ON` | observation seule | `modbusFonctions.be:3114-3127` | codé, `OFF` par défaut, jamais observé sur carte |
| ModBus TCP | — | — | — | `typeComm.TCP = OFF` | mort (A5 N6) |

**Mesures disponibles** (`PROTOCOLE_MODBUS.md` §9, `tasks/reprise-chantier-modbus-grenier.md`) :

*Range Extender, 2026-10-17 :*

| Mesure | Résultat |
|---|---|
| Unicast P4 → cuve | 5/5 au diagnostic, puis 6/6 à l'essai 1 |
| Unicast cuve → P4 | 11/11 ; aller-retour mesuré par le testeur : 0,33 à 0,49 s |
| Multicast | 2/2 dans chaque sens |

*Wi-Fi classique :* multicast P4 → cuve 11/12 après le correctif `197af338b`.

*Liaison filaire RS485 :*

| Mesure | Résultat |
|---|---|
| Échange avec la carte relais | environ 2 ms |
| Échange avec la cuve | environ 141 ms |
| 62 minutes en continu | 126/126 et 375/376, sans trou de plus de 5 min |

**Jamais mesurés :** la latence aller simple, la perte sur la durée en Range Extender, les doublons
(`accepteSeq` les écarte sans les compter), le délai de découverte après le démarrage d'un esclave, le
comportement sans broker.

### A8.4 — Comment le maître Range Extender identifie ses esclaves

**Chemin nominal :**
1. À la connexion Wi-Fi, l'esclave construit sa fiche : MAC, IP, rôle, routage, bloc ModBus
   (`discoveryFonctions.be:240-340`).
2. À `System#Boot`, il envoie un `ImAlive` en multicast (`udpFonctions.be:443-446`) et réarme un timer de
   `telePeriod`.
3. Le maître range la fiche sous `discovery.json[MAC][role]` avec `lwt: Online` (`:308-327`).
4. En parallèle, la fiche arrive par MQTT, retenue sur le broker.

Le délai de découverte est de quelques secondes après la connexion MQTT de l'esclave. Il n'a jamais été
chronométré.

**`RgxClients`** (`xdrv_58_range_extender.ino:178-211`) renvoie
`{"RgxClients":{"<MAC>":{"IPAddress":…,"RSSI":…}}}` : les stations associées au point d'accès, lues
localement, sans trafic. On l'appelle depuis Berry par `tasmota.cmd("RgxClients")`, qui renvoie une `map`,
et `test_discovery.be:72` sait déjà la simuler. Sa clé MAC est celle de la fiche discovery. Elle donne la
**vérité d'association Wi-Fi**, que la discovery ne connaît pas. Elle n'est appelée que par
`afficheBoutonsModulesEsclaves`, une fonction morte (A5).

**Lu sur le P4 le 2026-10-22 à 06:41** :
`{"RgxClients":{"DCB4D91BCAF0":{"IPAddress":"192.168.4.2","RSSI":-22}}}`.
- Une seule station est associée : la cuve.
- **Le rideau n'est pas associé au point d'accès.** C'est donc une panne Wi-Fi ou d'alimentation, pas une
  panne UDP, ce que la discovery seule ne permet pas de distinguer.
- Le format, la clé MAC sans deux-points et l'appel par MQTT sont confirmés.

| # | Constat | Preuve | Cote |
|---|---|---|---|
| R1 | **Aucune péremption des fiches.** `resetClientsConnectes` (tout passer `Offline`) ne s'exécute **qu'une fois**, `telePeriod` secondes après le démarrage du maître (`udpFonctions.be:448`). Ensuite, un esclave qui s'éteint reste `Online` tant que le broker ne publie pas son LWT, et **indéfiniment sans broker**. Aucune règle ne regarde l'âge du dernier `ImAlive`. | lignes relues | G |
| R2 | **Sans MQTT, un esclave ne se présente jamais** : `forceEnvoiParams` et le timer du maître sont dans la branche `System#Boot` (`:441-449`). Le secours C7 rouvre l'écoute mais ne relance pas ce cycle. | `:441-449`, `:478-529` | G |
| R3 | **Pendant les `telePeriod` secondes qui suivent le reset, tout est `Offline`** : `RoutageRangeExtender` (appelé seulement au démarrage) et `esclavesBox` ne retiennent que les fiches `Online`. | `rangeExtenderFonctions.be:119` ; `udpFonctions.be:684` | L |
| R4 | **Le cas « même IP, autre MAC » (carte remplacée) n'est pas détecté** : les deux fiches coexistent. `purgeAnciennes` dépend de `sensors.Time`, qui vient du broker. | `discoveryFonctions.be:85-148` | L |
| R5 | `RgxClients` lit le RSSI dans `wifi_sta_list.sta[i]` avec l'indice de l'**autre** liste (`_with_ip`). L'IDF construit les deux dans le même ordre, donc l'effet est probablement nul, mais ce n'est pas garanti. Le fichier vient de l'amont. | `xdrv_58_range_extender.ino:186-195` | L |
| R6 | L'en-tête de `udpFonctions.be:74` présente `RgxClients` comme utilisé : c'est faux. | | D |

### A8.5 — ESP-NOW et autres voies sans fil : recherche et grille

**Recherche** (2026-10-22) :
- **Aucun binding Berry `espnow`** : dans le dépôt, `espnow` et `esp_now` n'apparaissent que dans
  `xdrv_57_*` (TasMesh) et `xdrv_77_wizmote.ino`.
- Aucun fork Tasmota proposant un ESP-NOW générique, aucune discussion récente chez arendst sur ESP-NOW
  avec le P4 ou `esp_hosted`.
- WizMote utilise la bibliothèque **QuickEspNow**, embarquée dans `lib/lib_div/QuickESPNow`, mais en
  réception seule (`xdrv_77_wizmote.ino:290`). Elle fournit un `send` : c'est un bon socle pour un driver
  C++ propre au fork, la voie b de A8.2.
- **Pour le P4** : l'issue Espressif
  [esp-hosted-mcu#19 « Support for ESP Now »](https://github.com/espressif/esp-hosted-mcu/issues/19) est
  **ouverte** depuis le 2024-11-14. Le mainteneur l'a dite « on our roadmap » le 2025-12-31 ; la dernière
  relance, le 2026-08-14, est restée sans réponse (vérifié le 2026-10-22). Sur le P4, `esp_now.h` est
  injecté par `esp_wifi_remote`, mais aucune implémentation n'existe.
- ESPHome a écrit sa propre couche (`esp_now_hosted.cpp`, avec le firmware C6 `esphome/esp-hosted-firmware`).
  Elle prouve la faisabilité, au prix d'un **C6 reflashé** et d'un portage hors dépôt.
- Ponts ESP-NOW ↔ MQTT tiers (par exemple `4DERT/espnow-mqtt-gateway`) : des firmwares autonomes, sans
  intégration Tasmota.

**Contraintes ESP-NOW** (IDF 5.5.5 du fork) :
- trame de 250 octets en v1 et 1 470 en v2 (`esp_now.h:37`, P4 et S3), la v2 étant nécessaire aux deux
  bouts ;
- 20 pairs au plus, dont 7 chiffrés (`CONFIG_ESP_WIFI_ESPNOW_MAX_ENCRYPT_NUM=7`) ;
- **canal imposé** : celui du point d'accès du P4, lui-même aligné sur la box ;
- en unicast, un accusé MAC mais aucune garantie de remise à l'application : il faut garder un `seq`
  applicatif.

| Voie | Latence | Accusé natif | Coût (option) | P4 (C6 hosted) | Avec le point d'accès Range Extender | Verdict |
|---|---|---|---|---|---|---|
| UDP actuel | ms à dizaines de ms | non (`seq` applicatif) | déjà compilé | oui | oui (défauts C1-C7 corrigés) | à garder |
| MQTT local | dizaines de ms | QoS 1 | déjà compilé | oui | oui ; dépend du broker | relevés |
| ModBus TCP | 10 à 50 ms | oui (TCP) | `USE_MODBUS_BRIDGE(_TCP)` +6,5 k | oui | oui | sans gain sur l'UDP corrigé |
| TasMesh | ms, relais par MQTT | non | `USE_TASMESH` +11 k | **non** | force AP+STA | écarté (A8.1) |
| ESP-NOW générique (QuickEspNow) | ~ms | MAC seulement | driver C++, quelques Ko | **non** (sauf C6 reflashé) | même canal | S3 ↔ S3 seulement |
| BLE | 50 à 500 ms | en GATT | +9 k RAM, +292 k flash | non vérifié | radio partagée, ralentit le Wi-Fi | écarté |
| LoRa (`xdrv_73`) | 100 ms à plusieurs s | non | +5 à 16 k, plus un **module SPI à acheter** | oui | sans interférence | seulement pour une cible lointaine |
| WizMote | — | — | — | — | — | télécommande, hors sujet |

Les latences du tableau sont des ordres de grandeur, pas des mesures du parc.

### A8.6 — Propositions

**Voie recommandée par usage :**
- **commande en temps réel** : ModBus filaire, ou UDP unicast avec `tid` (déjà en place). ESP-NOW ne
  ferait gagner que quelques millisecondes, et seulement entre S3 tant que l'issue #19 reste ouverte ;
- **relevé périodique** : push UDP ou MQTT. C'est le meilleur candidat pour l'essai ESP-NOW de P8.4 ;
- **découverte** : `ImAlive` + discovery, complétée par `RgxClients`.

**Propositions :**
- **P8.6** — Péremption des fiches : passer une fiche à `Offline` quand aucun `ImAlive` n'est arrivé
  depuis 2 × `telePeriod`, au lieu du reset unique. Corrige R1 et R3. *(0,5 j ; risque moyen : un
  `Offline` à tort coupe le routage, donc garder un seuil large ; filet : `test_discovery.be` avec
  horloge simulée ; témoin : un esclave qui émet reste `Online`)*
- **P8.7** — Sans broker : lancer `forceEnvoiParams` depuis le secours C7. Corrige R2. *(0,25 j ; faible ;
  `test_discovery.be` §21)*
- **P8.8** — `etatReseau()` : croiser `RgxClients` et les fiches par MAC, puis classer chaque esclave
  (Wi-Fi associé et UDP vivant, Wi-Fi associé mais UDP muet, fiche fantôme, IP divergente). Afficher le
  résultat sur la page `/discovery`. Corrige R4 et R6. *(0,5 j ; risque nul, lecture seule ; banc : stub
  `rgxClients` existant)*
- **P8.9** — Mesurer ce qui ne l'a jamais été : latence aller simple (horodatage `tasmota.millis()`),
  perte sur 1 h en Range Extender, délai de découverte. *(0,5 j ; testeur UDP :7400)*
- **P8.10** — Attendre l'issue esp-hosted-mcu#19 avant tout ESP-NOW côté P4. Le reflashage du C6 avec un
  firmware ESPHome n'est pas recommandé : il entre en conflit avec le C6 de Tasmota. *(décision)*

## A9 — Utilisation de la RAM (2026-10-22)

Deux sources :
- **Le code** : mesures sous `berry.exe` (Berry 64 bits sur le PC, ramenées à 32 bits par un modèle
  calé sur la mesure), scripts dans `scratchpad/a9/`.
- **Les cartes** : relevés **passifs** des `tele/<topic>/STATE` publiés par les cartes, sur deux
  fenêtres d'observation (04:00 à 04:11, puis 06:20 à 06:36), sans rien leur envoyer
  (`scratchpad/a9/memoire_state.py`).

Complément du 2026-10-22 à 06:41, à la demande de l'utilisateur : `Status 4`, `Status 1` et
`Br tasmota.memory()` ont été envoyés par MQTT (commandes de lecture seule). Toutes les cartes ont répondu.

| Carte | Tas libre | Fragmentation | Pile (minimum restant / taille) | PSRAM libre / max | Dernier redémarrage |
|---|---|---|---|---|---|
| P4 (16.0.0.1) | **100 Ko** | 37 % | **2,3 Ko / 8 Ko** | 32,5 Mo / 32 Mo | `Software reset CPU`, 2026-10-22 00:30 UTC ; 2 démarrages depuis le flash de 21:27 |
| cuve (16.0.0.1) | **109 Ko** | 37 % | 19 Ko / 24 Ko | 4,5 Mo / 4,6 Mo (*) | `Software reset CPU`, 01:55 UTC ; 2 démarrages depuis 22:15 |
| cave (13.3.0.3, ancien code) | 53 à 58 Ko | 15 % | 3,6 Ko / 8 Ko | — | uptime 7 jours ; `BootCount` 7 518, `SaveCount` 673 382 |
| différentiel (15.0.1) | 147 Ko | 28 % | 3,9 Ko / 8 Ko | — | `Vbat power on reset`, 22 jours |

(*) Sur la cuve, la PSRAM annoncée fait 4,6 Mo pour une puce de 8 Mo. Les 3,5 Mo restants correspondent
probablement au programme copié en PSRAM (`ProgramSize` 3 566 Ko) : c'est une interprétation, non vérifiée.

### Ce qui est en place

**Le fait qui structure tout le reste.** `USE_BERRY_PSRAM` (`user_config_override.h:614`) envoie tout le
tas Berry en **PSRAM** (`xdrv_52_9_berry.ino:79-81`, `special_malloc`). Au-delà de 4 Ko, un `malloc` C y
part aussi. Sur le P4 et les S3, la RAM interne n'est donc pas consommée par Berry. Seuls les ESP32
**sans PSRAM** (cave ESP32, différentiel) sont contraints par le framework.

| | P4 | cuve / rideau (S3 N16R8) | ESP32 sans PSRAM (cave, différentiel) |
|---|---|---|---|
| RAM | 768 Ko de SRAM + PSRAM | 512 Ko + 8 Mo de PSRAM OPI | environ 320 Ko, sans PSRAM |
| Partitions | app 3,9 Mo / fs 11,6 Mo | app 4 Mo / fs 11,9 Mo | app 2,7 à 2,9 Mo / fs 320 à 448 Ko |
| Options qui pèsent | MQTT 2048 o, `MESSZ` 2000, tampon de log de 6 Ko, `USE_BERRY_DEBUG`, animation, Telegram, FTP, WSSERVER, Rules, UFILESYS + SD, I2S, LoRa | les mêmes, plus LVGL, OpenHASP, Matter | cave : animation et FTP retirés ; **différentiel : FTP et animation toujours compilés** |

**Consommateurs Berry estimés** (tas vivant, 32 bits) :

| Consommateur | P4 | cuve | rideau |
|---|---|---|---|
| Persist chargé entier, après veille des drivers inactifs | **≈ 54 Ko** (30 Ko de JSON) | ≈ 25 Ko | ≈ 26 Ko |
| Scripts chargés depuis le LittleFS | ≈ 12 Ko (`controleGarage` + `garageFonctions`) | ≈ 25 Ko (`controleCuve` + `cuveFonctions`) | 0 |
| Tampon de l'historique (`historiqueFonctions.be:119-123`) | ≤ 13,8 Ko | 4,6 Ko | ≤ 13,8 Ko |
| File ModBus (`MAX_FILE` 32) | 0 à 1,5 Ko en temps normal, 15 Ko au maximum | — | — |
| Caches (`seuils`, `rubansPousses`, `derniersSeq`, `routesFiches`…) | < 2 Ko, tous bornés | idem | idem |
| **Total estimé** | **≈ 95 à 110 Ko** | **≈ 70 à 75 Ko** | ≈ 45 à 50 Ko |
| **Mesuré** (`Berry.HeapUsed`, `tele/STATE`) | **100 Ko**, 1 616 objets | **76 Ko**, 1 105 objets | `Offline` |

Le modèle tombe juste. Le persist représente **plus de la moitié** du tas Berry.

**Relevés passifs du tas interne libre (`Heap`, en Ko) :**

| Carte | 04:00-04:11 | 06:20 | 06:25 | 06:30 | 06:35 | Berry (Ko / objets) |
|---|---|---|---|---|---|---|
| P4 (uptime 1 h 35 à 04:05) | 194 → 192 | — | 110 | 107 | 104 | 100 / 1 616, constant |
| cuve (redémarrée à 03:55) | 203 → 197 | 122 | 119 | 116 | — | 76 / 1 105, constant |
| cave (ancien code, uptime 7 jours) | 48 à 58 | 48 à 58 | | | | 76 / 1 477, constant |
| différentiel (sans framework) | 150 | 150 | | | | 3 / 42 |

### Avantages

- Sur les cartes à PSRAM, le choix `USE_BERRY_PSRAM` met le framework **à l'abri** de la RAM interne : le
  tas Berry du P4 (100 Ko) ne coûte rien au Wi-Fi ni à lwIP.
- Les caches Berry sont tous bornés, par cible, adresse ou MAC : aucune croissance sans fin repérée côté
  Berry. `HeapUsed` et `Objects` sont restés **strictement constants** pendant 2 h 30.
- La solidification paie déjà : `modbusFonctions` coûterait à lui seul ≈ 70 Ko en RAM, l'esclave ≈ 33 Ko,
  `udpFonctions` ≈ 20 Ko.
- Le tampon MQTT de 2048 o est justifié : la fiche `config` Tasmota reçue fait 1 à 1,4 Ko. Les envois sont
  découpés en flux.
- L'historique utilise un `bytes` compact (4 octets par point), pas des listes de réels.

### Inconvénients et défauts constatés

| # | Constat | Preuve | Cote |
|---|---|---|---|
| M1 | **Le tas interne du P4 et de la cuve baisse d'environ 0,6 Ko/min (≈ 36 Ko/h), régulièrement, pendant que le tas Berry reste constant.** Au rythme mesuré, le P4 (104 Ko libres à 06:35) serait à court en moins de 3 heures. Confirmé par `Status 4` à 06:41 : 100 Ko pour le P4, 109 Ko pour la cuve, soit la même pente. Les deux cartes avaient redémarré dans la nuit (P4 à 02:30, cuve à 03:55). `Status 1` donne `Software reset CPU` : un redémarrage **logiciel** (une commande `Restart` ou un redémarrage du firmware lui-même), et non une exception ou un chien de garde. Le lien avec la fuite n'est donc pas établi. La cave (ancien code) et le différentiel sont stables. La fuite est donc côté **C** (firmware 16.0.0.1, lwIP, sockets, MQTT…), déclenchée par un usage que le code courant est seul à faire. **Hypothèses, non prouvées** : création d'une socket `udp()` à chaque émission (`udpFonctions.be:738-741`), publication `ModbusReceivedUDP` à chaque trame, logs MQTT/syslog en `debug` (C1), firmware 16.0.0.1 lui-même. | 9 relevés `STATE` en 2 fenêtres ; `Berry.HeapUsed` constant | **G** (à confirmer) |
| M2 | **Concaténation quadratique dans `/histo`** : `morceau +=` dans la boucle des points (`historiqueFonctions.be:512-516` pour le jour, `:616-621` pour le mois). Estimation : environ 3 Mo copiés pour une page jour à 12 séries, jusqu'à **environ 75 Mo** pour une page mois, pour 21 à 165 Ko réellement envoyés. Le délai de garde n'est pas dépassé grâce à `yield`, mais le processeur et le ramasse-miettes sont fortement sollicités. | lignes relues ; estimation | S |
| M3 | **`discovery.json` relu en entier à chaque message discovery ou LWT** (11 Ko de texte et ≈ 28 Ko d'objets par lecture), avec une lecture triple à `discoveryFonctions.be:366-367` et `:622-623`. À chaque reconnexion MQTT : une rafale de 25 à 35 lectures, soit ≈ 1 Mo de déchets en quelques secondes. | estimation | S |
| M4 | **Allocations à chaque tick de 100 ms** : une `map` par instance `CONTROLE_UDP` (2 instances, `controleUDP.be:144`), et `bytes` + concaténation côté esclave (`modbusFonctions.be:1916-1917`). Environ 2 à 4 Ko de déchets par seconde. Les logs `detail` actifs (A7 C2) en ajoutent 10 à 20 Ko/s : un passage du ramasse-miettes toutes les 5 à 10 s. | estimation | S |
| M5 | **Pics trop gros pour un ESP32 sans PSRAM** : `envoiJson` du persist complet (`controleWeb.be:96-114`, ≈ 36 Ko de pic) et lecture de la discovery (30 à 45 Ko) contre 18 à 29 Ko de tas libre. Sans effet aujourd'hui : aucun ESP32 sans PSRAM n'exécute le framework courant (A1). | estimation | L |
| M6 | **Différentiel** : FTP et animation toujours compilés, `serveurFTP` à `ON` dans son persist. C'est le scénario qui faisait planter la cave (`user_config_override.h:762`). Latent tant que le framework n'y est pas déployé. | `user_config_override.h:753-772` | L |
| M7 | `fichesModbus()` sans cache en mode repli, quand la liaison série est coupée : ≈ 40 Ko par trame. | `modbusFonctions.be:1800` | L |
| M8 | **Pile du P4 presque à sec** : il ne reste au minimum que 2,3 Ko sur les 8 Ko de la boucle principale (`stack_low`). La cuve en a 24 Ko (19 Ko restants). Un appel Berry profond ou un gros `string.format` dans un callback du P4 approche du débordement. | `Br tasmota.memory()` du 2026-10-22 | L |
| M9 | Cave (ancien code) : `SaveCount` de 673 382 pour un `BootCount` de 7 518 : environ 90 sauvegardes des réglages par démarrage. L'usure de la flash est à surveiller. | `Status 1` | L |

### Propositions

| # | Proposition | Gain attendu | Effort / risque | Mesure avant / après |
|---|---|---|---|---|
| P9.1 | **Confirmer puis localiser la fuite M1.** D'abord une longue observation passive (`Heap` du `STATE` sur 12 h, et la raison du redémarrage dans `Status 1` après coup). Puis bissection, un réglage à la fois avec retour arrière : profil `normal` (P7.1), `RelaisPushMQTT`, ModBus en série au lieu de l'UDP. À traiter avec `superpowers:systematic-debugging`. | éviter les redémarrages, environ 36 Ko/h | moyen / faible | courbe `Heap` du `STATE` ; `Status 1` (RestartReason) |
| P9.2 | `/histo` : accumuler les morceaux dans une liste puis `concat()`, ou envoyer chaque point | de 75 Mo à moins de 0,3 Mo de copies ; réponse 5 à 10 fois plus rapide | faible / faible (`banc_graphiques.py`) | `curl -w %{time_total}` sur `/histo?p=mois` |
| P9.3 | `lisTable()` à la place des lectures triples, et cache de la table invalidé à l'écriture | −22 Ko de pic par appel, rafales évitées | faible / nul (`test_discovery.be`) | nombre de `BRY: GC` à la reconnexion MQTT |
| P9.4 | Réutiliser la `map` et les `bytes` de tick, et sortir tôt si rien n'est disponible (avec A5 P5.5) | −2 à 4 Ko/s de déchets | faible / faible (banc ModBus) | `BRY: GC` sur 10 min |
| P9.5 | Profil de log `normal` (A7 P7.1, P7.2) | ramasse-miettes 5 à 10 fois moins fréquent | nul | idem |
| P9.6 | Persist : retirer les clés mortes (A4 P4.6), alléger `modules.garage` (9,8 Ko de JSON à lui seul) | 4 à 5 Ko par carte | faible | `Berry.HeapUsed` |
| P9.7 | Solidifier `cuveFonctions` + `controleCuve`, puis les scripts du P4 (A3 P3.4) | ≈ 25 Ko et ≈ 12 Ko de **PSRAM**, gain faible ; démarrage plus rapide | moyen / moyen | `Berry.HeapUsed` |
| P9.8 | Avant tout déploiement du framework sur un ESP32 sans PSRAM : retirer FTP et animation du différentiel, découper `envoiJson` par clé (`content_send`), et passer la discovery à `OFF` | évite un plantage au démarrage, −18 Ko de pic | faible | `Status 4` |

## A10 — Autres points relevés en cours d'audit (2026-10-22)

Trois volets : la couverture des bancs, la documentation confrontée au code, et la robustesse du
démarrage. Analyse en lecture seule, constats graves relus dans le fil principal. Les bancs ont été
relancés le 2026-10-22 et sont tous verts :
- `BANC_VEILLE_DRIVERS: OK` ;
- `TEST_DISCOVERY: OK (216 tests, 0 echec(s))` ;
- `BANC_MODBUS: OK` ;
- `BANC_LEDS: OK`.

### Ce qui est en place

**Couverture des bancs.** Un module est compté comme couvert si un banc charge le **vrai** fichier, pas
un bouchon.

| Couverture | Modules |
|---|---|
| bonne | `modbusFonctions` (logique), `logFonctions`, `udpFonctions`, `discoveryFonctions`, `rangeExtenderFonctions`, `ledsFonctions`, `graphiquesFonctions`, `historiqueFonctions`, `historiqueSeries` |
| partielle | `modBus_TasmotaSlaveModBus`, `controleModbus` (règle UDP seule), `globalFonctions` (2 fonctions ; ailleurs un bouchon de 5 lignes), `controleRangeExtender`, `diversFonctions` (veille seule), `controleWeb` et `controleGarage` (environ 5 %) |
| **aucune** (syntaxe seule) | `modBus_Conn16channels` (557 l.), `gestionFileFolder` (toujours bouchonné), `configGlobal`, `configDevices`, `configModules`, `controleGeneral` (709 l.), les 3 `autoexec.be`, `controleCuve`, `cuveFonctions`, `controleRideau`, `garageFonctions`, et les drivers `controleUDP`, `controleLeds`, `controleLedTemoin`, `controleDiscovery`, `controleTCP`… |

Chemins réels jamais exercés, même dans les modules couverts :
- aucun banc n'ouvre de socket, de client TCP ni de port série ;
- aucun n'exécute un `autoexec`, `configGlobalByJson`, `configDevicesByRules` ou `controleGeneral.init` ;
- aucun ne construit une classe `controleXxx` du parc, sauf `CONTROLE_RANGE_EXTENDER` ;
- aucun ne teste la livraison (copie sur le LittleFS, solidification du parc entier) ;
- seule la page `/graphiques` est rendue.

**Démarrage.** L'autoexec lit les globales du persist, importe `logFonctions` et `diversFonctions`, met en
veille les drivers inactifs, puis compile et importe les `controleXxx` dans un ordre fixe : `controleGeneral`
(qui appelle `configDevicesByRules` puis `configGlobalByJson`), LEDs, I2C, ModBus, Web, UDP, Range Extender,
volets, discovery, ES8311, historique, et enfin le script de la carte.

### Avantages

- Les quatre bancs rapides tournent en moins d'une seconde chacun, avec des témoins négatifs : une
  régression de la logique ModBus, discovery, LEDs ou veille est visible tout de suite.
- Les modules récents sont écrits défensivement : `graphiquesFonctions`, `historiqueFonctions` et
  `hiberneDriversInactifs` (qui gère même l'absence de `/json`) utilisent `find` et `try/except` journalisés.
- `configDevices` sait se réparer : sur un échec d'écriture dans `/json`, il écrit à la racine et relance la
  répartition des fichiers (`configDevices.be:352-358`).
- La « Carte des documents » de `CLAUDE.md` est fiable : sur environ 90 chemins, un seul est mal rangé.
- La charte des logs de `CLAUDE.md` est identique au code.

### Inconvénients et défauts constatés

**Démarrage**

| # | Constat | Preuve | Cote |
|---|---|---|---|
| B1 | **Un persist vide, corrompu ou sans `diverses` bloque tout le démarrage sans laisser de trace.** `diverses.find("cmdMute")` est exécuté à la ligne 19, **avant** la garde `if (persist._p != nil && persist._p.size() != 0)` de la ligne 56, et avant l'import de `logFonctions`. Le `else` final (« fichier de paramétrage absent », `:132`) est donc inatteignable dans ce cas. Prouvé par un test Berry : `attribute_error: 'nil' value has no method 'find'`. | P4 `autoexec.be:15-19`, `:56`, `:132` ; `scratchpad/a10/t1.be` | G |
| B2 | **Aucun `try` dans les 3 autoexec** : une exception dans un `controleXxx` empêche le démarrage de tous les suivants. Sur le P4, un incident dans `controleModbus` priverait la carte du Range Extender, de la discovery, de l'historique et de `controleGarage`. | `grep -c try` = 0 | G |
| B3 | **`ReglageGlobal` et `ReglageLog` ne sont enregistrées qu'après `configGlobalByJson`** (`controleGeneral.be:133-137`). Une clé manquante dans `serveur.wifi`, `IP`, `mqtt` ou `localisation` (15 accès directs relevés, `configGlobal.be:76-195`) empêche leur enregistrement : la carte ne peut plus être réglée à distance pour réparer son persist. | lignes relues | L |
| B4 | **`listeEtRepartitLesFichiers` se rappelle elle-même après `path.mkdir("/sd")`** sans vérifier le résultat. Si le `mkdir` échoue (LittleFS plein), la récursion est infinie jusqu'au débordement de pile, déjà serrée sur le P4 (A9 M8). | `gestionFileFolder.be:76-78` | L |
| B5 | Un driver actif dont l'`environnement` est vide (veille sans fichier de restauration) lève `key_error` à l'import de `modBus_Conn16channels` (`:197`) ou de `modBus_TasmotaSlaveModBus` (`:56`), ce qui arrête l'autoexec (B2). | lignes citées | L |
| B6 | `try/except` qui avalent l'erreur : `ReglageGlobal nbLogsFiles` répond « réussie » même en cas d'échec (`globalFonctions.be:619-626`) ; `litVeille` perd le diagnostic (`diversFonctions.be:127-129`). | | L |
| B7 | Cron `*/300` dans le champ des **secondes** pour `timerRebootSansWifi` : le pas dépasse 59. Le comportement réel du parseur reste à vérifier (une fois par minute ?). Aujourd'hui sans effet, puisque la lambda n'appelle pas la méthode (A5 N1). Mais corriger N1 sans corriger ce cron pourrait provoquer un redémarrage par minute sur une carte sans Wi-Fi. | `controleGeneral.be:97` | L |

**Bancs**

| # | Constat | Cote |
|---|---|---|
| B8 | Le **chemin de démarrage n'a aucun banc** : autoexec, `configGlobal`, `configDevices`, `controleGeneral`, soit environ 1 800 lignes protégées par la seule vérification de syntaxe. | G |
| B9 | `modBus_Conn16channels` (carte 16 relais, en service) n'a **aucun banc** (déjà noté en A5 N7). | G |
| B10 | Les scripts de carte (`controleCuve`, `cuveFonctions`, `garageFonctions`, `controleRideau`) ne sont pas couverts. Or ce sont eux qui portent la logique métier (niveau, volume, couleurs). | L |

**Documentation** : environ 45 écarts sur environ 300 affirmations vérifiées, dont 9 trompeurs. Les numéros
de ligne dérivent à chaque édition ; les noms de fonction, eux, sont tous justes.

| # | Document | Écart | Cote |
|---|---|---|---|
| B11 | `SOLIDIFICATION_BERRY.md` §7 (`:544-557`) | Affirme « aucun build ne solidifiera les modules de `data/fs` ». C'est **contraire à la chaîne réelle** : `custom_berry_solidify` + `solidify-from-url.py` (A3), décrite au §6bis du même fichier. L'exemple du `:405-412` (« P4 : rien à ajouter ») est lui aussi périmé. | G |
| B12 | `SOLIDIFICATION_BERRY.md`, `README.md:25`, `CLAUDE.md` | Annoncent « 11 pièges » alors que le document en contient 13 (pièges 12 et 13, `:312`, `:335`). Une dizaine de numéros de ligne périmés (`copy_fs_image`, `compileModule`, `xdrv_52_9_berry.ino`…). | D |
| B13 | `ANALYSE_BERRY_MODBUS_DISCOVERY.md` (22 septembre) | Tous ses numéros de ligne sont faux. Ses « défauts bloquants » sont **corrigés** depuis le 30 septembre (`modbusFonctions.be:1791`), mais restent affichés comme actuels. | G |
| B14 | `PROTOCOLE_MODBUS.md` §8-§9 | 13 numéros de ligne périmés sur environ 25 (`modbusFonctions` est passé à 3 242 lignes). Les noms cités existent tous. | D |
| B15 | `README.md` § logs | La cible `leds` manque à la liste des cibles (`:78-80`). Les commandes `ReglageAutres`, `ReglageDHT22`, `ReglagePompe`, `ReglageAna`, `ReglageCuve`, `ReglageGarage` et `SCHEME` sont absentes de la liste des commandes. | D |
| B16 | `CARTE_MODULES_BERRY.md` | Régénérée sans différence de fond. Elle garde le faux diagnostic sur `controleRideau` (A3 S7), et l'ordre des arêtes du graphe change d'une génération à l'autre, ce qui crée du bruit dans les diffs. | D |
| B17 | Skill `tasmota-berry` (hors dépôt, `~/.claude/skills/`) | Les modèles `references/debug-et-deploiement.md:43-68` et `nouveau-module.md` enseignent encore `logActivation`, **supprimé**. D'autres références sont fausses : `i2c_ads1115.be:6`, `post_esp32.py:385-392`. | G |
| B18 | Skill `bancs` | `hiberneDriversInactifs` « ligne 31 des autoexec » : c'est la ligne 32 sur le P4. Le reste est exact. | D |
| B19 | Carte des documents de `CLAUDE.md` | Les 3 `cible_*.py` des sniffeurs et du syslog sont rangés sous `outils_pc/`, alors qu'ils sont dans `build/`. | D |

### Propositions

- **P10.1** — Garde de tête dans les autoexec : tester `persist._p` et `diverses` **avant** toute lecture, et
  journaliser par `print` (avant `logFonctions`) puis par syslog. Corrige B1.
  *(faible ; banc : `banc_boot.be` ci-dessous, avec un persist `{}` qui doit sortir proprement)*
- **P10.2** — Entourer chaque `import controleXxx as _ctrl` d'un `try/except` journalisé
  (`AUTO_EXE_ERREUR: <module>`), puis continuer. Enregistrer `ReglageGlobal`/`ReglageLog` **avant**
  `configGlobalByJson`. Corrige B2 et B3. *(moyen ; risque moyen : change l'ordre des échecs. À combiner avec
  A4 P4.2, l'autoexec commun)*
- **P10.3** — **Écrire `banc_boot.be`** : vrais `autoexec`, `configGlobal`, `configDevices` et
  `controleGeneral` avec un faux `tasmota`, sur trois persists :
  1. le persist réel du P4, la référence ;
  2. `{}`, rouge aujourd'hui (B1) ;
  3. le persist réel privé d'une clé, avec un témoin qui doit échouer.

  Corrige B8. **Premier banc à écrire**, avant P10.2 et A4 P4.2. *(moyen)*
- **P10.4** — Écrire le banc de la carte 16 relais (déjà demandé par A5 P5.7), puis un banc des scripts de la
  cuve (`cuveFonctions` : niveau → volume → couleur). Corrige B9 et B10. *(moyen)*
- **P10.5** — `listeEtRepartitLesFichiers` : vérifier le résultat de `mkdir` avant de se rappeler. Valider la
  syntaxe `*/300` sur un banc, ou la remplacer par un timer Berry avant de corriger N1. Corrige B4 et B7.
  *(faible)*
- **P10.6** — Documentation :
  - réécrire `SOLIDIFICATION_BERRY.md` §7 d'après A3 ;
  - marquer `ANALYSE_BERRY_MODBUS_DISCOVERY.md` comme « historique (2026-09-22) » ;
  - passer à « 13 pièges » ;
  - ajouter `leds` et les commandes manquantes au README ;
  - retirer `logActivation` des modèles du skill `tasmota-berry`.

  Corrige B11 à B15 et B17. *(faible)*
- **P10.7** — Contre la dérive : remplacer les `fichier:ligne` des documents durables par
  `fichier::fonction`. Ajouter un contrôle automatique (hook ou banc) qui vérifie que chaque chemin et chaque
  fonction cités existent. Rendre `carte_modules_berry.py` déterministe et corriger son `:427`. Corrige B12,
  B14, B16 et B19. *(moyen ; risque nul)*

## Synthèse des propositions (A11, 2026-10-22)

**109 constats** relevés de A2 à A10 : 23 G, 37 L, 30 S (dont les 11 duplications N12-N22), 15 D, 4 constats descriptifs non cotés (A8.1) ; **aucun B** : rien ne casse aujourd'hui un build ou un démarrage. Les défauts actifs sont une fuite de RAM interne, des fonctions jamais exécutées (redémarrages programmés), une usure de flash et un volume de logs démesuré.

**78 propositions** (P2.1 à P10.7), cotées d'après le constat le plus grave qu'elles corrigent : 24 G, 16 L, 27 S, 11 D.

*Cote d'une proposition = cote la plus grave des constats qu'elle corrige. Risque `dec` : une décision de l'utilisateur précède toute action.*

**Les 10 actions à plus fort rapport bénéfice/effort**, dans l'ordre conseillé :

1. **P7.1** — −43 Mo/jour sur le broker, GC moins fréquent *(corrige C1, C2 ; nul / nul)*
2. **P9.1** — Évite l'épuisement du tas du P4 en ~3 h *(corrige M1 ; moyen / faible)*
3. **P5.1** — Comportement conforme à l'intention *(corrige N1, B7 ; faible / dec)*
4. **P10.3** — Chemin de boot (1 800 l.) enfin couvert *(corrige B8, B1 ; moyen / nul)*
5. **P5.2** — Fin d'une écriture flash par esclave toutes les 300 s *(corrige N2 ; faible / moyen)*
6. **P5.7** — Plus de file ModBus bloquée *(corrige N7, B9 ; faible / faible)*
7. **P7.3** — Erreurs visibles en syslog/MQTT *(corrige C3 ; faible / faible)*
8. **P9.2** — 75 Mo → <0,3 Mo de copies, réponse 5 à 10× plus rapide *(corrige M2 ; faible / faible)*
9. **P10.1** — Boot dégradé journalisé au lieu d'un silence *(corrige B1 ; faible / faible)*
10. **P8.6** — Présence des esclaves fiable *(corrige R1, R3 ; moyen / moyen)*

Le plan d'action complet, sans exécution, est `tasks/plans/actions-audit-berry.md` (statut `en-pause`). Ses lots reprennent ceux du tableau ci-dessous.

### A1 — Décisions à prendre (aucun code)

Questions que l'audit ne peut pas trancher. Chaque réponse débloque ou annule des propositions des lots suivants.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P5.1 | Redémarrages programmés (heureReboot, timerRebootSansWifi) : voulus ou non ? S'ils le sont, corriger les lambdas ET le cron `*/300` (P10.5) ; sinon supprimer crons et clés | N1, B7 | G | faible | dec | comportement conforme à l'intention |
| P2.1 | Une S3 a-t-elle un écran ? Sinon retirer LVGL/OpenHASP de la base N16R8 (ou base S3 « sans écran ») | E1 | G | faible | moyen | flash et RAM sur 3 S3 |
| P4.4 | Cartes remplacées : geler ou retirer leurs fichiers ; cave : déployer la S3 ou donner un env à l'ancien code (ne PAS retirer le dossier *sauvegarde*) ; confirmer le statut réel de la cave et du différentiel (A1) | D5, D6, D7 | G | faible | dec | dépôt aligné sur le parc réel |
| P6.2 | 6 clés `log` orphelines : créer leurs cibles ou retirer les clés | L2 | G | faible | dec | réglages de log qui agissent |
| P8.5 | ESP-NOW côté P4 : passerelle S3, ou ESP-NOW réservé aux S3 (après P8.4) | T2 | G | — | dec | orientation radio |
| P8.10 | Attendre esp-hosted-mcu#19 avant tout ESP-NOW sur le P4 ; pas de C6 reflashé | T2 | G | nul | dec | évite un chantier sans issue |
| P3.1 | Différentiel : `drivers.ModBus.activation` à OFF, ou embarquer la pile ModBus | S1 | L | faible | dec | supprime un import impossible |
| P3.5 | Modules solidifiés inutiles : accepter, ou découper `socle` en `socle` + `reseau` | S3 | S | faible | dec | quelques Ko de flash par carte |
| P5.15 | Une seule source pour chaque donnée de la fiche discovery (routagePort, id, IPAddress) | N22 | S | moyen | dec | moins d'incohérences possibles |
| P2.9 | Ports COM propres à chaque poste : hors du `.ini` partagé | E13 | D | faible | dec | deux postes sans conflit |
| P7.8 | IP fixe du PC syslog, ou syslog vers le Pi SERVEUR-BUREAU | C9 | D | faible | dec | logs conservés PC éteint |

### A2 — Réglages sur carte, sans code

Effet immédiat, réversible par une commande. À faire en premier : réduit le bruit qui gêne le diagnostic de A3.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P7.1 | `ReglageLog profil normal` sur chaque carte (P4 d'abord), puis aligner les persists du dépôt | C1, C2 | G | nul | nul | −43 Mo/jour sur le broker, GC moins fréquent |
| P7.2 | `ReglageLog tous info` : seuils des modules à info | C2, C4 | G | nul | nul | chaînes de log non construites |
| P9.5 | Mesurer l'effet de P7.1/P7.2 sur le ramasse-miettes (`BRY: GC` sur 10 min) | M4 | S | nul | nul | GC 5 à 10 fois moins fréquent |
| P7.7 | Relever `ReglageLog` (sans argument) sur chaque carte : profil et seuils réellement en vigueur | — | D | nul | nul | état réel connu |

### A3 — Diagnostic de la fuite de RAM interne

Le seul défaut qui peut faire tomber le P4 en quelques heures. Méthode : superpowers:systematic-debugging.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P9.1 | Fuite de RAM interne (~0,6 Ko/min, P4 + cuve) : observation 12 h, puis bissection un réglage à la fois (profil normal, RelaisPushMQTT, ModBus série/UDP, socket udp() par émission), retour arrière à chaque pas | M1 | G | moyen | faible | évite l'épuisement du tas du P4 en ~3 h |

### A4 — Bancs manquants (avant toute refonte)

Filets à poser AVANT les lots A7, A10 et A11 : chaque banc avec son témoin négatif.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P10.3 | Écrire `banc_boot.be` : vrais autoexec/configGlobal/configDevices/controleGeneral, persists réel, `{}`, et privé d'une clé (témoin) | B8, B1 | G | moyen | nul | chemin de boot (1 800 l.) enfin couvert |
| P5.7 | Banc de la carte 16 relais + `try` autour de sa réception avec acquittement en `except` | N7, B9 | G | faible | faible | plus de file ModBus bloquée |
| P10.4 | Banc des scripts de la cuve (niveau → volume → couleur) | B10 | L | moyen | nul | logique métier couverte |

### A5 — Défauts actifs : petits correctifs

Défauts constatés en service (cotés G), correctifs locaux, filet existant.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P5.2 | ImAlive : ranger la fiche via discoveryFonctions avec `memeValeur`, n'écrire que si elle change | N2 | G | faible | moyen | fin d'une écriture flash par esclave toutes les 300 s |
| P5.3 | Cuve : un seul `_Scheme` par seconde partagé entre LEDs et surveilleRubans | N3 | G | moyen | moyen | −1 commande/s |
| P5.4 | P4 : CSS de la page d'accueil gardé en mémoire ou servi en statique | N4 | G | faible | faible | fin des lectures SD toutes les 2 s |
| P7.3 | 6 `print('Erreur…')` d'`except` → `xxxFonctions.log("…_ERREUR", LOG_LEVEL_ERREUR)` | C3 | G | faible | faible | erreurs visibles en syslog/MQTT |
| P7.5 | Logs ponctuels : info→detail dans `web_sensor` du P4, ES8311 en erreur, `_ERREUR` dans 8 `except`, préfixes ; trancher « trame rejetée / délai isolé » | C5, C6, C7, C8 | G | faible | faible | logs conformes à la charte |
| P6.1 | Cible réglable `historique` (dans CIBLES, lieu `diverses.historique`) | L1 | G | faible | faible | logs debug de l'historique récupérés |
| P9.2 | `/histo` : morceaux dans une liste puis `concat()` | M2 | S | faible | faible | 75 Mo → <0,3 Mo de copies, réponse 5 à 10× plus rapide |
| P9.3 | `lisTable()` à la place des lectures triples de discovery.json, cache invalidé à l'écriture | M3 | S | faible | nul | −22 Ko de pic par appel |

### A6 — Défauts latents : petits correctifs

Chemins non empruntés aujourd'hui mais qui casseraient au premier changement de configuration.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P8.7 | Sans broker : `forceEnvoiParams` lancé depuis le secours C7 | R2 | G | faible | faible | esclave présenté même sans MQTT |
| P4.1 | `loadBerryFile` : ne pas charger si l'activation vaut OFF | D1 | L | faible | faible | un OFF arrête vraiment le driver |
| P5.8 | `diversFonctions.valeurScalaire(value)` pour les 5 sites ; humidité du P4 | N8, N9 | L | faible | moyen | fin d'un bug sur map multi-clés |
| P5.9 | configDevices : compteur analogique « réels », `%i` sur "ON", log des compteurs | N10 | L | faible | faible | compteurs justes |
| P6.3 | Cache des seuils vidé après toute écriture du persist ; défaut d'un bloc absent non mis en cache | L3, L4 | L | faible | faible | réglages pris sans redémarrage |
| P6.4 | Cible inconnue de `lieu()` journalisée une fois en erreur | L5 | L | faible | nul | fautes de frappe détectées |
| P10.5 | `listeEtRepartitLesFichiers` : vérifier `mkdir` ; valider ou remplacer le cron `*/300` | B4, B7 | L | faible | faible | pas de récursion infinie, pas de reboot par minute |
| P2.2 | Coquille du `USER_TEMPLATE` du rideau (`1,1s]`) | E2 | L | faible | faible | template valide après reset |
| P2.3 | Rebouclage de `increment_config_holder` à 65535 | E5 | L | faible | faible | build qui ne casse pas |

### A7 — Démarrage robuste

Après le banc de démarrage (A4). Touche le chemin de boot : une carte à la fois, en commençant par une carte de banc.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P10.1 | Garde de tête des autoexec : `persist._p` et `diverses` testés avant toute lecture, avec trace | B1 | G | faible | faible | boot dégradé journalisé au lieu d'un silence |
| P10.2 | `try/except` journalisé autour de chaque `import controleXxx` ; `ReglageGlobal`/`ReglageLog` enregistrées avant `configGlobalByJson` | B2, B3, B5 | G | moyen | moyen | un module en échec n'emporte plus les suivants |
| P4.2 | Autoexec commun : module `demarrage` solidifié, ~15 lignes propres par carte ; différentiel et grenier remis au modèle | D2, D4 | S | moyen | moyen | une correction au lieu de huit |
| P4.3 | Séparer « charger ou non » et « supprimer le source » dans `compileModule`/`loadBerryFile` | D3 | D | faible | faible | API lisible |

### A8 — Découverte des esclaves

Péremption des fiches, présentation sans broker, vérité Wi-Fi par RgxClients, mesures jamais faites.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P8.6 | Péremption : Offline si aucun ImAlive depuis 2 × telePeriod, au lieu du reset unique | R1, R3 | G | moyen | moyen | présence des esclaves fiable |
| P8.8 | `etatReseau()` : RgxClients × fiches par MAC, affiché sur `/discovery` | R4, R6 | L | moyen | nul | panne Wi-Fi distinguée d'une panne UDP |
| P8.9 | Mesurer latence aller simple, perte sur 1 h, délai de découverte (testeur :7400) | A8.3 | D | moyen | nul | chiffres jamais mesurés |

### A9 — Nettoyage : code mort et données mortes

Beaucoup de lignes en moins pour peu de risque. Chaque suppression précédée d'une recherche à 0 résultat sur data/.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P5.10 | Lot code mort : fonctions sans appelant, branches inatteignables, blocs commentés, callbacks vides, `etatCapteurs`, `/wss`, `any_key` | N11 et code mort | L | faible | faible | ~800 lignes en moins |
| P4.7 | Schéma du persist normatif pour `relaisLie` (`delai` requis) | D10 | L | faible | nul | schéma qui protège au lieu de tromper |
| P5.6 | Ne plus forcer `tcp.activation` ; ne plus charger TCP sur la cave S3 (variante lourde : retirer le transport TCP, sur décision) | N6 | L | faible | faible | client TCP et every_250ms en moins |
| P4.5 | 5 fonctions sans appelant de A4 | D8 | S | faible | faible | ~180 lignes en moins |
| P4.6 | Clés mortes de `relaisLie`/`typeAction` retirées des persists | D9 | S | faible | faible | 0,4 à 1,5 Ko de RAM par carte |
| P9.6 | Alléger `modules.garage` (9,8 Ko de JSON) | D1 (A9) | S | faible | faible | 4 à 5 Ko par carte |
| P6.6 | Sauvegarde du persist harmonisée ; clés `nbLogsFiles`/`fileLogName` sans lecteur retirées | L8 | S | faible | faible | une seule convention |
| P2.4 | 8 sections orphelines de `user_config_override.h` ; bloc commun garage | E3, E4 | S | moyen | faible | fichier plus court, moins de copies |
| P2.6 | Pre-script : listes (FAIT le 2026-10-21, `e26ff49d0`), garde contre le double accrochage, code mort | E6, E7 | S | faible | faible | pre-script assaini |
| P2.8 | `data/test.mp3` (3,3 Mo) sorti du dépôt | E12 | S | faible | nul | dépôt plus léger |
| P2.7 | Table de partitions S3 renommée d'après son contenu | E11 | D | faible | faible | nom qui ne trompe plus |

### A10 — Factorisations (après les bancs de A4)

Gains de lisibilité et de maintenance ; risque moyen, d'où l'exigence d'un banc vert avant ET après.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P7.4 | Garde `logFonctions.actif()` sur les chemins chauds ModBus/UDP | C4 | G | moyen | moyen | chaînes coûteuses non construites |
| P3.3 | `return controleXxx` en fin de chaque `controleXxx` | S6 | L | faible | nul | chargeable depuis le LittleFS |
| P5.11 | Petits helpers : `relaisLie`, `deviceActif`, `readJson`, `macSansDeuxPoints`, `decoupeCommande` | N12, N14, N16, N20 | S | faible | faible | ~110 lignes |
| P5.12 | Factorisations : groupes de `changementEtatCapteur`/configDevices, itérateurs devices et fiches, `prepareTrame`/`decrypteMSG` | N13, N15, N17, N18 | S | moyen | moyen | ~430 lignes |
| P5.13 | Base commune aux drivers esclave ESP32 et carte 16 relais (après P5.7) | N19 | S | fort | fort | ~150 lignes |
| P5.14 | Module commun cuve/P4 : couleur, volume, page thermomètres, logs | N21 | S | moyen | moyen | ~45 lignes, une source |
| P5.5 | Une socket par instance `CONTROLE_UDP` | N5 | S | faible | moyen | lectures de socket divisées par 2 |
| P9.4 | Map et bytes de tick réutilisés, sortie précoce si rien à lire | M4 | S | faible | faible | −2 à 4 Ko/s de déchets |
| P3.2 | `import` local en tête de fonction pour l'auto-appel des modules | S4 | S | moyen | faible | plus de dépendance au nom global |

### A11 — Build et solidification

Environnements, pio-tools, exclusions du LittleFS, solidification des scripts de carte.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P2.5 | `pio-tools/` : revenir à l'amont pour les écarts de pure traduction | E9 | G | moyen | faible | moins de conflits de synchro |
| P9.8 | Avant de déployer le framework sur un ESP32 sans PSRAM : FTP/animation retirés, `envoiJson` découpé, discovery OFF | M5, M6 | L | faible | faible | évite un plantage au boot |
| P2.10 | Un seul mécanisme d'exclusion du LittleFS | E10 | S | moyen | moyen | une seule règle à comprendre |
| P3.7 | Idem P2.10 côté solidification : `copy_fs_image` ou `post_esp32.py` seul | S5 | S | moyen | moyen | (fusionner avec P2.10) |
| P3.4 | Solidifier `garageFonctions` puis `cuveFonctions`, puis les scripts de driver de carte | candidats A3 | S | moyen | moyen | démarrage plus rapide |
| P9.7 | Mesurer le gain de P3.4 (`Berry.HeapUsed`) | A9 | S | faible | nul | ≈25 Ko (cuve) et ≈12 Ko (P4) de PSRAM |
| P3.6 | `carte_modules_berry.py` : modules de carte solidifiés, docstring | S7 | D | faible | nul | fin d'un faux diagnostic |

### A12 — Outillage et documentation

Contrôles automatiques contre la dérive (charte des logs, chemins et fonctions cités) et documents à corriger.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P10.6 | Docs : §7 de SOLIDIFICATION réécrit, ANALYSE marquée historique, « 13 pièges », README (leds, commandes), skill sans `logActivation` | B11, B13, B15, B17 | G | faible | nul | docs justes |
| P7.6 | Contrôle automatique de la charte des logs dans `verifie_berry.py` (avertissements) | C10 | D | moyen | faible | la dérive est signalée à l'édition |
| P10.7 | `fichier::fonction` au lieu de `fichier:ligne` ; contrôle des chemins et fonctions cités ; carte des modules déterministe | B12, B14, B16, B19 | D | moyen | nul | docs qui ne dérivent plus |
| P6.5 | README : le profil fait foi sur les sorties, SERIALLOG_TIMER, portée de `actif()` | L6, L7 | D | faible | nul | comportement documenté |

### A13 — Radio : ESP-NOW et TasMesh (exploration)

Rien d'urgent : à n'engager qu'après les lots de fiabilité.

| Prop. | Proposition | Corrige | Cote | Effort | Risque | Bénéfice |
|---|---|---|---|---|---|---|
| P8.1 | Ne pas retenir TasMesh pour le garage | T1, T2 | S | nul | nul | évite une impasse |
| P8.2 | TasMesh seulement pour de futurs capteurs ESP8266 sur batterie, broker ESP32/S3 | T1 | S | faible | faible | option documentée |
| P8.4 | Essai borné ESP-NOW entre deux S3 (QuickEspNow) : latence, pertes, coexistence, tas | T3-T9 | S | moyen | faible | décision radio fondée sur des mesures |
| P8.3 | Signaler la régression T10 à l'amont après un essai | T10 | D | faible | nul | contribution amont |
