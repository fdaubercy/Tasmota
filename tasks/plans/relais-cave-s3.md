---
chantier: relais-cave-s3
titre: Cave — envs ESP32/S3 alignés sur la carte en ligne, audit de l'env S3, carte Waveshare 8DI-8RO de remplacement
statut: actif
cree: 2026-10-31
maj: 2026-11-23
source: concurrent-crafting-knuth.md
objectif: Remplacer la carte ESP32 de la cave en ligne par une S3 8 relais (Waveshare 8DI-8RO) : envs alignés, audit de l'env S3 suivi, entrées-sorties du persist portées sur la Waveshare
famille: cave
liens: envs-grenier-rdc-sonoff-cave, voie-reseau-ethernet
---
# Cave — envs ESP32/S3 alignés sur la carte en ligne, audit S3, carte Waveshare de remplacement

## Contexte
Fusion du 2026-11-23 (décision de l'utilisateur) de trois plans en un seul : A1 à A5 sont le plan d'origine `relais-cave-s3`,
A6 à A11 viennent du plan d'action `audit-relais-cave-s3` (en pause), A12 à A16 du plan `cave-s3-waveshare` (clos le 2026-11-02).
Les deux plans absorbés sont archivés dans `tasks/archive/`. Chaque case et chaque preuve est reprise telle quelle ;
seules les actions sont renumérées (ancien A<n> de l'audit = A<n+5> ; ancien A<n> de la Waveshare = A<n+11>).

### Contexte de la comparaison des envs (A1 à A5)
La carte de la cave en ligne (192.168.0.48) est un ESP32-D0WD-V3 sans PSRAM, 4 Mo, alimenté en
**DC 7-30 V sur bornier**, avec le modèle « ESP32 Relay x8 ». Elle tourne en firmware 13.3.0.3 du
13/01/2024, avec l'ancien code (`data/cave/tasmota32-serveur-rly-sauvegarde/`, autoexec identique
octet pour octet). Son persist et son template ont été relus le 31/10 (`/ufsd?download=`, `/cm?cmnd=Template`) :

| Fonction | GPIO en ligne | Dépôt aujourd'hui |
|---|---|---|
| Relais 1-5 (pompe vide-cave, ventilation, LED machines, pompe cuve, lavage) | 32, 33, 25, 26, 27 | identique (S3 : 5, 6, 7, 16, 17) |
| Boutons 1-3 | 4, 0, 18 | identique |
| LED témoin | 23 | identique (S3 : 21) |
| Thermomètre AM2301 | 22, **ON** | **OFF** dans les deux persists |
| Capteurs de niveau bas / haut | 2 / 15, **OFF**, pas de Switch dans le template | **ON**, Switch1/Switch2 ajoutés au template |

Template en ligne : `[33,1,1,1,32,1,1,1,1,1,1,1,1,1,34,1,1,1,1216,288,1,226,227,228,1,1,1,1,224,225,1,1,1,1,1,1]`.

Décisions prises :
- seules les **broches et les templates** sont alignés ; l'identité (IP .243, topic `-v2`) n'est pas touchée ;
- sur la S3, le GPIO 22 n'existe pas : **AM2301 sur le GPIO 11** (choix de l'utilisateur) ;
- la carte de remplacement est alimentée en DC 7-30 V, comme l'actuelle ;
- l'audit est en **lecture seule** : rapport + plan d'action `en-pause`, rien n'est corrigé ;
- les propositions de cartes sont livrées en **photos PNG**, une par carte, nommées par lettre, avec leurs liens.

Contraintes : un build du P4 (`erase_upload`) tourne → `tasmota/user_config_override.h` n'est édité
qu'après sa fin (un build réécrit ce fichier). Jamais de `pio run` de ma part pendant un build de l'utilisateur.

### Contexte des suites de l'audit (A6 à A11)
Plan d'action issu de `outils_docs/AUDIT_RELAIS_CAVE_S3_2026-10-31.md` (audit en lecture seule). Rien n'est décidé :
l'utilisateur choisit les actions. Règles : aucun `pio run` pendant un build de l'utilisateur, `git commit -- <chemins>`,
pas de `Co-Authored-By`, messages de commit en français sans accents.

### Contexte de la carte Waveshare (A12 à A16)
La cave S3 (`[env:tasmota32s3-cave-serveur-rly]`, `data/cave/tasmota32s3-serveur-rly/`) supposait un DevKit S3
N16R8 avec un module relais câblé sur des GPIO. La carte retenue (A4 de ce plan, README
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
Ce bloc garde l'étape `.h` de l'ESP32 (A1) ; ses étapes `.h` et cenv de la S3 (A2) sont remplacées par A14.

## A1 — Env ESP32 `tasmota32-cave-serveur-rly` aligné sur la carte en ligne
- [x] Aucun `pio run`/scons en cours juste avant les éditions (garde_build / Win32_Process) — preuve : 10:12:28, 0 processus pio run/scons
- [x] `user_config_override.h` (branche `#else` du `USER_TEMPLATE` de la section cave) : 160 et 161 retirés → template identique octet pour octet à celui de la carte en ligne — preuve : template ESP32 du .h = persist ESP32 = carte en ligne (comparaison scriptée : True)
- [x] `data/cave/tasmota32-serveur-rly/_persist.json` : `pompeVideCave.capteurs.capteur1/2` en `activation: OFF` (broches 2/15 gardées), `Thermo-Hygrometre.thermometre1` en `activation: ON` (GPIO 22, type 1216) ; template du bloc `modele` du persist aligné s'il en porte un ; édition par Edit, texte d'origine conservé (pas de réécriture par `json.dump`) — preuve : git diff du persist (5 valeurs), relance de pompe sans effet sur capteur désactivé (controleGeneral.be::niveauHautActif)
- [x] Contrôle : JSON relu par `json.load` ; template décodé GPIO par GPIO = celui de la carte en ligne (script du scratchpad) — preuve : verif_cave.py « identique a la carte en ligne : True », aucun doublon

## A2 — Env S3 `tasmota32s3-cave-serveur-rly` aligné (même logique, broches S3)
- [x] `user_config_override.h` (branche S3 du `USER_TEMPLATE`) : 160 (GPIO 2) et 161 (GPIO 15) retirés, 1216 (AM2301) posé à l'index du GPIO 11 — preuve : remplacé par l'action A14 de ce plan (Waveshare, ex-A3) : template de la Waveshare
- [x] `data/cave/tasmota32s3-serveur-rly/_persist.json` : capteurs de niveau OFF, `thermometre1` ON sur le **pin 11** ; template du bloc `modele` aligné — preuve : verif_cave.py (template S3 38 cases, AM2301 au GPIO 11 ; l'ancien était le tableau ESP32 de 36 cases)
- [x] Commentaire de l'env S3 dans `platformio_tasmota_cenv.ini` mis à jour (AM2301 sur le GPIO 11, capteurs de niveau inactifs comme sur la carte en ligne) — preuve : remplacé par l'action A14 de ce plan (Waveshare, ex-A3) : commentaire réécrit pour la Waveshare
- [x] Contrôle : JSON valide ; aucune broche interdite S3 (19-20, 26-37, 43-46) ; aucun doublon de broche dans le persist — preuve : verif_cave.py « interdits S3: [] », « doublons: [] »
- [x] `banc_demarrage.py` (skill `bancs`) : si l'instantané de la cave S3 change, la différence = exactement ces broches, puis instantané mis à jour — preuve : écart règles Switch1/2 -> Tele#AM2301 ; écart « sources 3 -> 1 » antérieur (témoin HEAD identique, référence non réenregistrée depuis 91bbae69a) ; --enregistre puis VERT

## A3 — Audit en lecture seule de l'env S3 relais cave
- [x] Périmètre relu : — preuve : outils_docs/AUDIT_RELAIS_CAVE_S3_2026-10-31.md (cenv, .h, data/cave S3, écarts de fonctions)
  - section du cenv (solidification, `custom_files_exclude`, pages embarquées, partitions N16R8, ports) ;
  - section `#if` du `.h` (identité, Range Extender, options) ;
  - `data/cave/tasmota32s3-serveur-rly/` : autoexec, `controlePompeVideCave.be` comparé à la copie ESP32, persist comparé au modèle du parc ;
  - écarts de fonctions avec la carte en ligne (topic `cave/serveur-rly-cave` contre `-v2`, Node-RED et Telegram, capteurs).
- [x] Rapport `outils_docs/AUDIT_RELAIS_CAVE_S3_2026-10-31.md` : pour chaque point, ce qui est en place, ses avantages, ses inconvénients, une proposition — preuve : P1-P11 ; P2 (COM3) et P5 (UDP/RangeExtender ON sur S3) revérifiés dans le cenv et le persist
- [x] Plan d'action (actions A6 à A11 de ce plan, ex-`tasks/archive/audit-relais-cave-s3.md`), statut `en-pause` (l'utilisateur décide) — preuve : fichier créé, 6 actions, aucune cochée
- [x] Aucun fichier de code, de config ni de build modifié par l'audit (`git status` avant/après) — preuve : git status avant/après de l'audit, seuls ses 2 livrables en plus (les autres écarts sont de cette conversation)

## A4 — Cartes ESP32-S3 à 8 relais capables de remplacer la carte en ligne
- [x] Critères écrits — preuve : outils_docs/cartes_relais_cave/README.md § Critères (7 critères)
  - ESP32-S3 avec PSRAM (N16R8 de préférence : c'est la cause du remplacement) ;
  - 8 relais d'au moins 10 A ;
  - alimentation DC qui couvre 7-30 V ;
  - assez d'entrées libres pour 3 boutons, 2 capteurs de niveau et l'AM2301 ;
  - relais pilotés par GPIO direct ou par un expandeur que Tasmota sait piloter (vérifié dans `tasmota/tasmota_xdrv_driver/`) ;
  - fixation et encombrement comparés à la carte actuelle ;
  - prix et disponibilité en France ou dans l'UE.
- [x] Recherche web : au moins 3 candidates — preuve : README, 4 cartes (A Waveshare 8DI-8RO, B variante -C, C KinCony KC868-A8v3 incompatible PCF8575, D LilyGO T-Relay S3 hors critère 6 relais)
- [x] Photos téléchargées dans `outils_docs/cartes_relais_cave/` (`carte-A.png`, `carte-B.png`…), chacune regardée (Read) avant livraison — preuve : carte-A..D.png ouvertes le 2026-10-31, bonne carte sur chacune
- [x] `outils_docs/cartes_relais_cave/README.md` : tableau comparatif selon les critères, lien vers chaque site, recommandation motivée, incompatibilités nommées (expandeur, entrées optocouplées, alimentation) — preuve : README (liens curl 200, sauf 2 OpenELab en 429 signalés) ; driver TCA9554 vérifié : tasmota/tasmota_xdrv_driver/xdrv_69_pca9557.ino (cite la Waveshare 8DI-8RO)

## A5 — Commit
- [ ] `git commit -- <chemins de ce plan seulement>`, message en français sans accents. ⚠️ `user_config_override.h` porte déjà des changements de build (CFG_HOLDER) : les montrer à l'utilisateur avant de les inclure.
- [ ] `git show --stat HEAD` relu

## A6 — Prouver que l'env compile et tient en mémoire (P1)
- [ ] Aucun `pio run`/scons en cours juste avant (garde_build, Win32_Process)
- [ ] Env compilé via la page « Build et téléversement » (7700), sans téléversement
- [ ] Taille du firmware relevée contre la partition app de 3 904 Kio
- [ ] Après un premier flash : tas libre interne et PSRAM relevés (`Status 4`, `BRY: GC`)

## A7 — Ports et état de la bascule (P2, P4)
- [ ] `upload_port`/`monitor_port` de l'env changés (COM3 est la cuve) ou commentés
- [ ] État réel des relais de la carte en ligne relevé juste avant la bascule
- [ ] État voulu des relais au premier démarrage de la S3 décidé et appliqué après le flash

## A8 — Topics, consommateurs et messages retenus (P3, P8)
- [ ] Consommateurs de `cave/serveur-rly-cave` inventoriés sur le Pi (Node-RED, Grafana, Influx, autres)
- [ ] Flux Telegram importé et réglé (token, broker) pour `cave/serveur-rly-cave-v2`
- [ ] Messages retenus de l'ancien topic et LWT `-v2` effacés après la bascule
- [ ] Groupe `tasmotas/cave` : carte en ligne vérifiée ; commentaires de l'env corrigés

## A9 — Rôle réseau de la cave (P5)
- [ ] Décision : la cave est-elle « maître » UDP / Range Extender / discovery / FTP ?
- [ ] Si non : les 4 blocs à OFF dans `data/cave/tasmota32s3-serveur-rly/_persist.json`, banc de démarrage mis à jour
- [ ] Si oui : raison consignée dans le commentaire de l'env

## A10 — Alerte de la pompe (P6, P10)
- [ ] Capteurs de niveau câblés et activés (GPIO 2/15), ou limite consignée
- [ ] `EtatPompe`, `AcquittePompe` et `ALERTE_POMPE` essayés sur la carte
- [ ] Banc de la relance de sécurité écrit (`finTimerRelai`, `relanceRelai`, `acquitteRelance`)
- [ ] Une seule copie de `controlePompeVideCave.be` retenue

## A11 — Allègement de l'env (P7, P9, P11)
- [ ] Base `tasmota32s3-base-N16R8-sans-ecran` et `SET_ESP32_STACK_SIZE` essayés, taille comparée à A6
- [ ] `leds` retiré de la solidification, ou conservé par choix
- [ ] `fsMqtt` chargé par l'autoexec de la cave si l'envoi de fichiers par MQTT est voulu
- [ ] Persist nettoyé : `TasmotaSlaveModBus2`, `diverses.historique.grafana`, `ledPower`

## A12 — Persist S3 aux GPIO de la Waveshare
- [x] Aucun `pio run`/scons en cours juste avant les éditions (Win32_Process) — preuve : 08:54, seul le build de la CUVE tourne (data_dir garage, n'utilise pas data/cave) ; data/fs, .h et cenv reportés après lui
- [x] `data/cave/tasmota32s3-serveur-rly/_persist.json` : chaque `pin` du tableau ci-dessus (Edit, texte d'origine conservé) ; les 5 relais en `pin: -1` + `virtuel: "I2C_TCA9554"` — preuve : git diff du persist (5 relais -1/I2C_TCA9554, boutons 4/0/5, capteurs 6/7 ON (réactivés), AM2301 21, led1 48, ledRGB 38)
- [x] Bloc `drivers.I2C` : `activation: ON`, `pinsI2C1` (SDa, 640) pin 42 ON, `pinsI2C2` (SCl, 608) pin 41 ON, nouveau bloc `TCA9554` `{activation: ON, name, adresseI2C: "0x20", I2CDriver: 81}` — preuve : contrôle « I2C: ON {... 0x20, I2CDriver 81} », pins 42/41 ON
- [x] `template` du persist = template Waveshare (`NAME` « ESP32S3 Waveshare 8DI-8RO Cave ») : — preuve : template décodé {0 Bouton2, 4 Bouton1, 5 Bouton3, 6 Switch1, 7 Switch2, 21 AM2301, 41 SCL, 42 SDA, 48 Led1}, 38 cases (capteurs réactivés le 2026-10-31)
  `[33,1,1,1,32,34,160,161,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1216,0,0,0,0,0,1,1,1,608,640,1,1,1,1,1,288]`
- [x] Contrôle (script du scratchpad, comme `verif_cave.py`) : JSON valide, aucun doublon de `pin` actif, aucune broche prise par la carte (12-18, 38 actif, 40, 45-47, 33-37), template décodé = tableau ci-dessus — preuve : « doublons: [] », « sur broches de la carte: [] » (led_temoin VR GPIO39 : driver voletRoulants OFF)

## A13 — Relais du TCA9554 reconnus par le framework
- [x] `data/fs/configDevices.be` : la branche `virtuel == "I2C_MCP23017"` traite aussi `"I2C_TCA9554"`, avec l'adresse lue dans `drivers.I2C.environnement[<suffixe>]` ; commentaire d'une ligne sur le pourquoi — preuve : branche I2C_MCP23017 || I2C_TCA9554, puce = suffixe de `virtuel` ; témoin Berry 5 relais actifs avec la branche, 0 avec le configDevices.be de HEAD
- [x] Hook `verifie_berry_edition` vert sur `configDevices.be` (syntaxe et charte des logs) — preuve : hook sans erreur à l'édition (10:13)
- [x] `data/cave/tasmota32s3-serveur-rly/tca9554.dat` : `{"NAME":"TCA9554","GPIO":[224,225,226,227,228,0,0,0]}` (relais 1-5 = CH1-CH5, CH6-8 libres) — preuve : fichier créé
- [x] Le `.dat` part bien sur le FS : dossier listé dans `custom_files_upload` de l'env ; vérifier qu'aucun filtre n'exclut l'extension `.dat` (pre-script) — preuve : pio-tools/post_esp32.py copie le dossier entier (shutil.copytree), sans filtre d'extension

## A14 — Firmware : template et drivers
- [x] Juste avant l'édition, aucun build en cours (le `.h` est réécrit par chaque build) — preuve : 10:12:28, 0 processus pio run/scons (build de la cuve fini à 10:11:49)
- [x] `tasmota/user_config_override.h`, branche `FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY` : `USER_TEMPLATE` = template de A12 ; commentaire de brochage réécrit pour la Waveshare ; `#define USE_TCA9554` (et `USE_I2C` s'il n'est pas déjà actif pour cet env) — preuve : USER_TEMPLATE S3 = template du persist (comparaison scriptée : True), USE_TCA9554 ajouté ; USE_I2C déjà actif (my_user_config.h, aucun #undef)
- [x] `platformio_tasmota_cenv.ini` : commentaire de l'env S3 réécrit (carte Waveshare, relais TCA9554, tableau des GPIO, GPIO occupés par la carte) ; aucune option changée — preuve : git diff du cenv : 12 lignes de commentaire, aucune option

## A15 — Vérifications
- [x] `banc_demarrage.py` sur les **6 cartes** (code partagé) : seule la cave S3 peut changer ; écarts relus puis enregistrés — preuve : cave S3, P4, cuve, bureau OK ; rideau et grenier KO sur « sources » seulement, identique avec le data/fs de HEAD (référence périmée depuis 91bbae69a, pas de ce chantier, non réenregistrée)
- [x] Témoin : dans le faux firmware, le template final de la cave S3 contient 608/640 aux GPIO 41/42, 1216 au 21, 288 au 48, aucun relais ; et `nbIOActivesJSON.relais.actives.nb` = 5 (script du scratchpad qui charge `banc_demarrage.be` puis lit le gabarit) ; mutant : `virtuel` MCP23017 sur la cave -> 5 relais aussi, `I2C_XXX` inconnu -> 0 — preuve : gabarit final [33,1,1,1,32,34,160,161,…,1216,…,608,640,…,288], 5 relais actifs ; mutant MCP23017 5 ; adresse absente 0x27 -> 0
- [x] Agent `relecteur-berry` sur `configDevices.be` avant commit — preuve : verdict « prêt », aucun défaut (MCP23017 inchangé, string importé, charte respectée)

## A16 — Commit (carte Waveshare)
- [x] `git commit -- <chemins de ce plan>`, message en français sans accents ; changements de build du `.h` (CFG_HOLDER) montrés avant de les inclure — preuve : 8cb16a3a2 (persist, tca9554.dat) et 72b2aef87 (configDevices, .h, cenv), poussés sur development
- [x] `git show --stat HEAD` relu ; `tasks/README.md` régénéré — preuve : stat relue pour chaque commit ; index régénéré par node .claude/hooks/index_plans.mjs

## Améliorations restantes
- [ ] [projet] Une fois la carte choisie : nouveau template, nouvelles broches du persist S3 et section du cenv pour CETTE carte (l'env S3 actuel suppose un DevKit + module relais câblé)
- [ ] [projet] Compiler les deux envs (page build) une fois le build du P4 fini, sur décision de l'utilisateur
- [ ] [projet] Si la S3 remplace la carte en ligne : topic `-v2` contre `cave/serveur-rly-cave` côté Node-RED et Telegram (pris en charge par l'audit)
- [ ] [projet] Vérifier si un 2e « maître » (id 0) perturbe la table discovery du P4
- [ ] [projet] Réduire la partition FS (11,3 Mo) pour la cave si l'écriture de l'image gêne
- [ ] [projet] Compiler l'env S3 (page build) une fois le build du P4 fini : prouve `USE_TCA9554` et la taille (audit P1)
- [ ] [projet] `upload_port`/`monitor_port` = COM3, port de la cuve (audit P2) : à poser au branchement de la Waveshare
- [ ] [projet] Câblage des capteurs de niveau (actifs) sur DI3/DI4 (COM, DGND) à valider sur la carte reçue, avant de compter sur la relance de la pompe
- [x] [projet] Ethernet W5500 (Wi-Fi faible à la cave), demandé le 2026-11-02 — preuve : persist (`drivers.Ethernet` ON, INT 12, MOSI 13, MISO 14, SCLK 15, CS 16), template et `ETH_TYPE 8` du `.h`, `banc_demarrage.py` ; ni compilé ni essayé sur carte
- [x] [projet] Voie réseau au choix (demande du 2026-11-02 : Wi-Fi prioritaire) — preuve : `ReglageGlobal VoieReseau wifi|ethernet`, `configGlobal.be::configGlobal_voieReseau`, `banc_boot.py` cas 6 à 8 verts, mutants détectés ; sur Ethernet : même IP (`serveur.IP`), `surveilleWifi` et Range Extender désactivés
- [ ] [projet] À la réception : compiler, puis essayer `ReglageGlobal VoieReseau ethernet` sur la carte (`Status 5`, IP .243 sur le câble, retour au Wi-Fi par la console série)
- [ ] [projet] Brochage de l'en-tête (21, 48) à confirmer à réception : aucun schéma PDF publié

## Vérification
- Templates : un script du scratchpad décode les tableaux GPIO (ordre ESP32 : 0-5, 9, 10, 12-27, 6-8, 11, 32-39 ; ordre S3 : 0-21, 33-48) et compare celui de l'ESP32 au template relu sur 192.168.0.48.
- Persists : `json.load`, recherche de doublons de `pin` actifs, comparaison des clés `activation/pin/type` avec le persist en ligne (copie dans le scratchpad).
- `banc_demarrage.py` vert, instantanés relus.
- Audit : `git status` identique avant et après.
- Photos : chaque PNG ouvert et regardé ; chaque lien du README répond (curl, code HTTP).
- Suites de l'audit (A6 à A11) : `python outils_docs/scripts_python/berry/banc_demarrage.py --carte tasmota32s3-cave-serveur-rly` (code 0 = vert), puis
  `node .claude/hooks/index_plans.mjs --verifier`. Une étape ne se coche qu'avec sa preuve (sortie de banc, commit, mesure sur carte).
- Waveshare (A12 à A16) : persist par script du scratchpad (JSON, doublons, broches réservées, template décodé dans l'ordre S3 0-21 puis 33-48) ;
  framework par `banc_demarrage.py` (6 cartes) + témoin sur le faux firmware (template final, nombre de relais actifs) + mutants ;
  Berry par le hook `verifie_berry_edition` à l'édition et l'agent `relecteur-berry` avant commit. Pas de compilation ni de flash dans cette partie
  (build du P4 en cours à l'époque, carte pas encore reçue).
