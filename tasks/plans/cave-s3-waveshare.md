---
chantier: cave-s3-waveshare
titre: Env S3 relais cave adapté à la carte Waveshare ESP32-S3-ETH-8DI-8RO
statut: actif
cree: 2026-10-31
maj: 2026-10-31
source: concurrent-crafting-knuth.md
objectif: Faire tourner les entrées-sorties actuelles du persist de la cave S3 sur la carte Waveshare 8DI-8RO, relais par le TCA9554
---
# Env S3 relais cave adapté à la carte Waveshare ESP32-S3-ETH-8DI-8RO

## Contexte
La cave S3 (`[env:tasmota32s3-cave-serveur-rly]`, `data/cave/tasmota32s3-serveur-rly/`) supposait un DevKit S3
N16R8 avec un module relais câblé sur des GPIO. La carte retenue (plan `relais-cave-s3`, README
`outils_docs/cartes_relais_cave/`) est la **Waveshare ESP32-S3-ETH-8DI-8RO** :
- module WROOM-1U-N16R8 : même base PlatformIO `tasmota32s3-base-N16R8` ;
- **relais sur un TCA9554 en I2C** (0x20, SDA GPIO42, SCL GPIO41), pas sur des GPIO ;
- entrées DI1 à DI8 isolées sur les GPIO 4 à 11, actives à l'état bas (Button Tasmota standard) ;
- BOOT sur le GPIO0 ;
- en-tête GPIO : 21, 45, 47, 48 ;
- GPIO occupés : W5500 12-16, RS485 17/18, WS2812 38, RTC 40-42, TF 45/47/48, buzzer 46.

Décision de l'utilisateur : **les mêmes entrées-sorties que le persist actuel, seuls les GPIO changent.**
Choix posés le 2026-10-31 : entrées sur DI1-DI4 avec le bouton 2 sur BOOT ; LED témoin sur le GPIO 48 ;
capteurs de niveau **réactivés** sur la Waveshare (demande de l'utilisateur : relance et alerte de la pompe de nouveau possibles ;
le persist ESP32 reste aligné sur la carte en ligne, capteurs OFF).

| Élément du persist | Avant (DevKit) | Waveshare |
|---|---|---|
| relai1 Pompe Vide-Cave (id 1) | GPIO 5 | TCA9554 EXIO1 / CH1 |
| relai1 Ventilation Cave (id 2) | GPIO 6 | EXIO2 / CH2 |
| relai1 LED Machines (id 3) | GPIO 7 | EXIO3 / CH3 |
| relai2 Pompe Cuve (id 4) | GPIO 16 | EXIO4 / CH4 |
| relai3 Lavage (id 5) | GPIO 17 | EXIO5 / CH5 |
| bouton1 Pompe Cave | GPIO 4 | **DI1 / GPIO 4** |
| bouton2 | GPIO 0 | **BOOT / GPIO 0** |
| bouton3 (autres) | GPIO 18 (RS485 RX sur la Waveshare) | **DI2 / GPIO 5** |
| capteur1 niveau bas (**ON**, Switch1) | GPIO 2 | **DI3 / GPIO 6** |
| capteur2 niveau haut (**ON**, Switch2) | GPIO 15 (ETH SCLK sur la Waveshare) | **DI4 / GPIO 7** |
| thermomètre AM2301 (ON) | GPIO 11 (DI8 sur la Waveshare) | **GPIO 21** (en-tête) |
| Led1 témoin | GPIO 21 | **GPIO 48** (en-tête) |
| ledRGB (OFF) | GPIO 48 | **GPIO 38** (WS2812 de la carte) |
| bus I2C (OFF) | SDA 9 / SCL 8 | **ON**, SDA 42 / SCL 41 |

**Le seul code à toucher : les relais sans GPIO.** `configModules.be::configModules_configDevicesByJon` écrit le
`pin` de chaque relais dans le template ; un relais à `pin: -1` sans `virtuel` est ignoré par
`diversFonctions.be::diversFonctions_deviceActif`. Le framework a déjà le cas d'un expandeur I2C :
`virtuel: "I2C_MCP23017"`, compté dans `configDevices.be` après un `I2CScan` sur l'adresse du bloc
`drivers.I2C.environnement.MCP23017`. On étend cette branche à `I2C_TCA9554`, avec un bloc
`drivers.I2C.environnement.TCA9554` (0x20, I2CDriver 81). Les relais eux-mêmes sont créés par le driver Tasmota
`xdrv_69_pca9557.ino` (`USE_TCA9554`), qui lit `/tca9554.dat` au démarrage (`TfsLoadString`).
Ils deviennent POWER1 à 5 : `set_power_handler`, PowerOnState et WebButton fonctionnent comme pour des relais à GPIO.

`configDevices.be` est solidifié (`berry_commun.socle`) et partagé par toutes les cartes : la modification se
limite à la condition et à la clé d'adresse, sans changement de comportement pour le MCP23017.

Hors périmètre (rien que les GPIO) : Ethernet W5500, RS485, RTC PCF85063, buzzer, identité, `upload_port`.
Le plan `relais-cave-s3` garde l'étape `.h` de l'ESP32 ; ses étapes `.h` et cenv de la S3 sont remplacées par ce plan.

## A1 — Persist S3 aux GPIO de la Waveshare
- [x] Aucun `pio run`/scons en cours juste avant les éditions (Win32_Process) — preuve : 08:54, seul le build de la CUVE tourne (data_dir garage, n'utilise pas data/cave) ; data/fs, .h et cenv reportés après lui
- [x] `data/cave/tasmota32s3-serveur-rly/_persist.json` : chaque `pin` du tableau ci-dessus (Edit, texte d'origine conservé) ; les 5 relais en `pin: -1` + `virtuel: "I2C_TCA9554"` — preuve : git diff du persist (5 relais -1/I2C_TCA9554, boutons 4/0/5, capteurs 6/7 ON (réactivés), AM2301 21, led1 48, ledRGB 38)
- [x] Bloc `drivers.I2C` : `activation: ON`, `pinsI2C1` (SDa, 640) pin 42 ON, `pinsI2C2` (SCl, 608) pin 41 ON, nouveau bloc `TCA9554` `{activation: ON, name, adresseI2C: "0x20", I2CDriver: 81}` — preuve : contrôle « I2C: ON {... 0x20, I2CDriver 81} », pins 42/41 ON
- [x] `template` du persist = template Waveshare (`NAME` « ESP32S3 Waveshare 8DI-8RO Cave ») : — preuve : template décodé {0 Bouton2, 4 Bouton1, 5 Bouton3, 6 Switch1, 7 Switch2, 21 AM2301, 41 SCL, 42 SDA, 48 Led1}, 38 cases (capteurs réactivés le 2026-10-31)
  `[33,1,1,1,32,34,160,161,1,1,1,1,1,1,1,1,1,1,1,1,1,1216,0,0,0,0,0,1,1,1,608,640,1,1,1,1,1,288]`
- [x] Contrôle (script du scratchpad, comme `verif_cave.py`) : JSON valide, aucun doublon de `pin` actif, aucune broche prise par la carte (12-18, 38 actif, 40, 45-47, 33-37), template décodé = tableau ci-dessus — preuve : « doublons: [] », « sur broches de la carte: [] » (led_temoin VR GPIO39 : driver voletRoulants OFF)

## A2 — Relais du TCA9554 reconnus par le framework
- [x] `data/fs/configDevices.be` : la branche `virtuel == "I2C_MCP23017"` traite aussi `"I2C_TCA9554"`, avec l'adresse lue dans `drivers.I2C.environnement[<suffixe>]` ; commentaire d'une ligne sur le pourquoi — preuve : branche I2C_MCP23017 || I2C_TCA9554, puce = suffixe de `virtuel` ; témoin Berry 5 relais actifs avec la branche, 0 avec le configDevices.be de HEAD
- [x] Hook `verifie_berry_edition` vert sur `configDevices.be` (syntaxe et charte des logs) — preuve : hook sans erreur à l'édition (10:13)
- [x] `data/cave/tasmota32s3-serveur-rly/tca9554.dat` : `{"NAME":"TCA9554","GPIO":[224,225,226,227,228,0,0,0]}` (relais 1-5 = CH1-CH5, CH6-8 libres) — preuve : fichier créé
- [x] Le `.dat` part bien sur le FS : dossier listé dans `custom_files_upload` de l'env ; vérifier qu'aucun filtre n'exclut l'extension `.dat` (pre-script) — preuve : pio-tools/post_esp32.py copie le dossier entier (shutil.copytree), sans filtre d'extension

## A3 — Firmware : template et drivers
- [x] Juste avant l'édition, aucun build en cours (le `.h` est réécrit par chaque build) — preuve : 10:12:28, 0 processus pio run/scons (build de la cuve fini à 10:11:49)
- [x] `tasmota/user_config_override.h`, branche `FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY` : `USER_TEMPLATE` = template de A1 ; commentaire de brochage réécrit pour la Waveshare ; `#define USE_TCA9554` (et `USE_I2C` s'il n'est pas déjà actif pour cet env) — preuve : USER_TEMPLATE S3 = template du persist (comparaison scriptée : True), USE_TCA9554 ajouté ; USE_I2C déjà actif (my_user_config.h, aucun #undef)
- [x] `platformio_tasmota_cenv.ini` : commentaire de l'env S3 réécrit (carte Waveshare, relais TCA9554, tableau des GPIO, GPIO occupés par la carte) ; aucune option changée — preuve : git diff du cenv : 12 lignes de commentaire, aucune option

## A4 — Vérifications
- [x] `banc_demarrage.py` sur les **6 cartes** (code partagé) : seule la cave S3 peut changer ; écarts relus puis enregistrés — preuve : cave S3, P4, cuve, bureau OK ; rideau et grenier KO sur « sources » seulement, identique avec le data/fs de HEAD (référence périmée depuis 91bbae69a, pas de ce chantier, non réenregistrée)
- [x] Témoin : dans le faux firmware, le template final de la cave S3 contient 608/640 aux GPIO 41/42, 1216 au 21, 288 au 48, aucun relais ; et `nbIOActivesJSON.relais.actives.nb` = 5 (script du scratchpad qui charge `banc_demarrage.be` puis lit le gabarit) ; mutant : `virtuel` MCP23017 sur la cave -> 5 relais aussi, `I2C_XXX` inconnu -> 0 — preuve : gabarit final [33,1,1,1,32,34,160,161,…,1216,…,608,640,…,288], 5 relais actifs ; mutant MCP23017 5 ; adresse absente 0x27 -> 0
- [x] Agent `relecteur-berry` sur `configDevices.be` avant commit — preuve : verdict « prêt », aucun défaut (MCP23017 inchangé, string importé, charte respectée)

## A5 — Commit
- [ ] `git commit -- <chemins de ce plan>`, message en français sans accents ; changements de build du `.h` (CFG_HOLDER) montrés avant de les inclure
- [ ] `git show --stat HEAD` relu ; `tasks/README.md` régénéré

## Améliorations restantes
- [ ] [projet] Compiler l'env S3 (page build) une fois le build du P4 fini : prouve `USE_TCA9554` et la taille (audit P1)
- [ ] [projet] `upload_port`/`monitor_port` = COM3, port de la cuve (audit P2) : à poser au branchement de la Waveshare
- [ ] [projet] Câblage des capteurs de niveau (actifs) sur DI3/DI4 (COM, DGND) à valider sur la carte reçue, avant de compter sur la relance de la pompe
- [ ] [projet] Ethernet W5500 (Wi-Fi faible à la cave) : option possible plus tard, hors « seuls les GPIO changent »
- [ ] [projet] Brochage de l'en-tête (21, 48) à confirmer à réception : aucun schéma PDF publié

## Vérification
- Persist : script du scratchpad (JSON, doublons, broches réservées, template décodé dans l'ordre S3 0-21 puis 33-48).
- Framework : `banc_demarrage.py` (6 cartes) + témoin sur le faux firmware (template final, nombre de relais actifs) + mutants.
- Berry : hook `verifie_berry_edition` à l'édition, agent `relecteur-berry` avant commit.
- Pas de compilation ni de flash dans ce plan (build du P4 en cours, carte pas encore reçue).
