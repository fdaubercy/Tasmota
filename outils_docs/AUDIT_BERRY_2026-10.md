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

## A3 — Chaîne de solidification

*À faire.*

## A4 — Architecture et chargement des scripts Berry

*À faire.*

## A5 — Simplification des modules et drivers

*À faire.*

## A6 — Niveaux de log : le mécanisme

*À faire.*

## A7 — Niveaux de log : conformité et sorties

*À faire.*

## A8 — Communications entre modules et ESP-NOW

*Inventaire des voies en place, identification des esclaves, mesures UDP et recherche GitHub : à faire.
Les deux analyses ci-dessous ont été faites le 2026-10-21, à la demande de l'utilisateur.*

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

## A9 — Utilisation de la RAM

*À faire.*

## A10 — Autres points relevés en cours d'audit

*À faire.*

## Synthèse des propositions

*À remplir en fin d'audit (A11).*
