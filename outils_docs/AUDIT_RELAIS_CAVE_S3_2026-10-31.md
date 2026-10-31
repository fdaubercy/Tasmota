# Audit de l'env `tasmota32s3-cave-serveur-rly` — 2026-10-31

> **Audit en lecture seule** : rien n'a été modifié (ni code, ni config, ni build, ni `data/`), aucun `pio run`, aucune commande envoyée aux cartes. L'utilisateur décide de la suite (plan `tasks/plans/audit-relais-cave-s3.md`, statut `en-pause`).

## Résumé

- **Verdict : presque prêt, pas encore remplaçable les yeux fermés.** Le code, le persist, l'autoexec et la pompe sont cohérents ; le banc de démarrage de la cave S3 est **VERT**. Mais l'env **n'a aucune trace de compilation** (`.pio/build` ne contient que le P4) : taille du firmware et tas libre ne sont pas prouvés.
- **Bloquant** : P1 (jamais compilé). **Importants** : P2 (port COM3 = port de la cuve), P3 (consommateurs de l'ancien topic), P4 (état des relais à la bascule), P5 (la cave S3 se déclare 2e « maître » et ouvre un AP).
- Le plan d'alerte (relance + Telegram) est **dormant** tant que les capteurs de niveau (GPIO 2/15) sont désactivés, comme sur la carte en ligne (P6).
- Les écarts de broches du 2026-10-31 (capteurs OFF, AM2301 GPIO 11, template 38 cases) ne sont pas repris ici.

## Méthode

Relu : `platformio_tasmota_cenv.ini` (section de l'env, `berry_commun`, bases S3), `tasmota/user_config_override.h` (section cave), `data/cave/tasmota32s3-serveur-rly/` (autoexec, pompe, persist), `data/fs/demarrage.be`, `data/fs/controleGeneral.be`, `outils_docs/node-red/flow-telegram-pompe.json`, `outils_docs/schemas/modele_persist.json`, copie du persist de la carte en ligne (scratchpad). Banc lancé : `banc_demarrage.py --carte tasmota32s3-cave-serveur-rly` (n'écrit rien sans `--enregistre`).

---

## 1. Section du cenv `[env:tasmota32s3-cave-serveur-rly]`

**En place**
- Hérite de `env:tasmota32s3-base-N16R8` : carte `esp32s3-qio_opi` (`boards/esp32s3-qio_opi.json` : `-DBOARD_HAS_PSRAM`, mémoire `qio_opi`), partition `partitions/esp32_partition_app3904k_fs11584k.csv` (app 3,9 Mo, FS 11,3 Mo), flash 16 Mo.
- `custom_berry_solidify` = `berry_commun.socle` + `historique` + `leds` ; `custom_files_exclude_solidified = ON`.
- `custom_files_exclude` : liste noire des modules ModBus, LoRa, volets, ES8311, coprocesseur, I2C + `page_cuve`.
- `custom_files_upload` : dossier propre `data/cave/tasmota32s3-serveur-rly`.
- `upload_port`/`monitor_port` = `COM3` ; OTA commenté (liste `custom_ota_files` limitée à la pompe).

**Cohérence exclusions / autoexec (vérifiée)** : chaque module chargé par l'autoexec est soit solidifié (socle, historique), soit sur le FS (`controlePompeVideCave`, non exclu). Aucun module chargé n'est exclu : pas de panne de ce type. Aucun module embarqué sur le FS n'est inutilisé, sauf les points ci-dessous.

**Avantages** : liste d'exclusion alignée sur la carte ESP32 ; `page_cuve` exclue (règle du 2026-10-31) ; partition standard du parc (identique au P4) ; PSRAM bien activée.

**Inconvénients**
- Jamais compilé (aucun dossier `.pio/build/tasmota32s3-cave-serveur-rly`) : aucune mesure de taille ni de RAM.
- `upload_port`/`monitor_port` = **COM3**, port de la **cuve** (leçon du 2026-10-14) : un téléversement série lancé branché sur la cuve écraserait la cuve avec le firmware cave.
- Base `…-N16R8` **avec LVGL + OpenHASP** alors que la cave n'a pas d'écran ; le parc a une base `tasmota32s3-base-N16R8-sans-ecran` (audit P2.1) pour cela. Passer à cette base impose `SET_ESP32_STACK_SIZE (24 * 1024)` dans la section du `.h` (comme les trois cartes du garage), car `FIRMWARE_LVGL` le fixait.
- `ledsFonctions`/`controleLeds` sont solidifiés (liste `leds`) alors que ruban et LED RGB sont OFF : du flash pour rien (l'autoexec ne les charge pas).
- `fsMqtt` (socle) n'est pas chargé par l'autoexec de la cave : le téléversement de fichiers par MQTT (A16) n'y est pas utilisable ; l'OTA HTTP reste possible.
- Commentaire d'en-tête périmé : « NE JAMAIS faire tourner les deux cartes en même temps (même IP, même client MQTT) » — la carte en ligne est en `.48` / `SERVEUR-RLY-CAVE`, la S3 en `.243` / `-V2` : seul le **hostname** `SERVEUR-RLY-CAVE` et le groupe `tasmotas/cave` sont communs.

**Propositions** : P1, P2, P7, P8, P9.

---

## 2. `tasmota/user_config_override.h` — section cave

**En place** : section commune `FIRMWARE_ESP32_CAVE_SERVEUR_RLY || FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY` : identité (IP `.243`, client `SERVEUR-RLY-CAVE-V2`, topic `cave/serveur-rly-cave-v2`, groupe `tasmotas/cave`), Range Extender (`WIFI_RGX_SSID` `SERVEUR-RLY-CAVE-GATEWAY`), `USER_BACKLOG "Module 0; Hostname SERVEUR-RLY-CAVE"`, animation Berry retirée, `USE_FTP` retiré **sauf sur la S3**, `USE_SPI`/`USE_SDCARD` (CS 5), règles activées.

**Avantages** : une seule section pour les deux puces ; FTP bien conservé sur S3 (PSRAM) ; identités du `.h` et du persist S3 identiques (`-V2`), donc pas de `Topic` corrigé par Berry (qui redémarrerait la carte).

**Inconvénients**
- Spécifique ESP32 mais inoffensif sur S3 : `USE_SPI` « GPIO12/13/14 », `SDCARD_CS_PIN 5` (GPIO 5 = relais 1 de la S3) — sans broche `SDCard CS` configurée, `UfsCheckSDCardInit` ne fait rien (`xdrv_50_filesystem.ino`), donc aucun conflit constaté ; reste un piège si quelqu'un active la SD.
- `USE_BERRY_ANIMATION` retiré : correct tant que le ruban reste OFF (`ledsFonctions` n'utilise que `light` / `Scheme`) ; à revoir si un ruban est ajouté.
- Pas de `SET_ESP32_STACK_SIZE` (hérité de LVGL via la base actuelle) : à ajouter si la base change (P7).

**Propositions** : P7, P8.

---

## 3. Dossier `data/cave/tasmota32s3-serveur-rly/`

### 3.1 `autoexec.be`
**En place** : 23 lignes, liste ordonnée des modules sur `data/fs/demarrage.be` (`prologue`, `importe`, `compileSocle`, `compile`, `charge`, `chargeFichier`, `leds`, `historique`). Même structure que `data/garage/tasmota32s3-capteurs-cuve-modbus/autoexec.be` ; différences attendues seulement (pas de ModBus, cuve, fsMqtt, discovery compilé).
**Avantages** : minimal ; conditions par clés de persist (`serveur.udp`, `serveur.tcp`, `serveur.rangeExtender`, `serveur.discovery`, `modules.pompeVideCave`). Banc de démarrage : drivers `CONTROLE_GENERAL`, `CONTROLE_WEB`, `CONTROLE_UDP`, `CONTROLE_RANGE_EXTENDER`, `CONTROLE_DISCOVERY`, `CONTROLE_POMPE_VIDE_CAVE`, `HISTORIQUE_WEB` ; commandes `EtatPompe`, `AcquittePompe`, `Reglage*` ; `erreurs (0)`.
**Inconvénients** : le commentaire « Service réseau NON activé -> ni compilé ni chargé » est vrai pour le mécanisme mais, sur S3, UDP, Range Extender et discovery sont **ON** dans le persist (voir P5). `compile(["udpFonctions"])`, `tcpFonctions`, `rangeExtenderFonctions` sont solidifiés : appels sans effet utile (même motif dans les autres autoexec).

### 3.2 `controlePompeVideCave.be`
**En place** : diff exact avec `data/cave/tasmota32-serveur-rly/controlePompeVideCave.be` : **identique**, sauf 5 lignes d'en-tête « CARTE REMPLACÉE, NON MAINTENU » présentes sur la copie ESP32 uniquement.
**Avantages** : aucune divergence de logique ; la copie ESP32 est gelée, la S3 est la référence.
**Inconvénients** : deux copies d'un même fichier (risque de dérive si on corrige l'une seule) ; aucun banc ne couvre la relance de sécurité (`controleGeneral.be::finTimerRelai`, `relanceRelai`, `niveauHautActif`, `publieAlerteRelance`) ni les commandes `EtatPompe` / `AcquittePompe` (recherche dans `outils_docs/scripts_python` : seul l'instantané de démarrage cite la pompe).
**Propositions** : P10.

### 3.3 `_persist.json`
**En place** : comparé au persist ESP32 du dépôt (même dossier voisin) et au modèle `outils_docs/schemas/modele_persist.json` (par aplatissement des clés).
- Écarts S3 / ESP32 voulus : `typeESP` `ESP32S3`, broches relais 5/6/7/16/17 (ESP32 : 32/33/25/26/27), AM2301 pin 11 (ESP32 : 22), LED pin 21 (23), template 38 cases, `ledRGB` (OFF) ajoutée, `historique` ON (24 h, 5 min, 12 séries), `udp`/`rangeExtender`/`serveurFTP`/`discovery` ON (OFF sur ESP32).
- Écarts de **format** : le persist S3 est au format récent (`relaisLie` = `modules`/`ids`/`type`/`delai`, `capteurs`, `SwitchMode`), le persist ESP32 du dépôt au format ancien (`etatSiON`/`delaiSiON`…). La carte **en ligne** est dans un troisième format (clé racine `parametres`, `capteursPosition`, `modele`).
- Clés du socle du modèle absentes de la S3 : `diverses.historique.grafana` seulement. Clés en trop : `drivers.ModBus.environnement.TasmotaSlaveModBus.TasmotaSlaveModBus2.*` (reliquat, ModBus OFF).
- Cohérence : topic d'alerte `tele/cave/serveur-rly-cave-v2/ALERTE_POMPE` = celui attendu par le flux Node-RED ; broches toutes autorisées S3 (aucune dans 19-20, 26-37, 43-46) et sans doublon ; `thermometre1` ON pin 11 type 1216, règles `Tele#AM2301#…` présentes au démarrage.
- Différences avec la carte en ligne à connaître : `ledPower` OFF (en ligne : ON), `web.url_serveur` / `url_sauvegarde_json` de l'ancienne carte (NAS 192.168.0.2, éteint) non repris : normal ; modules en `log: detail` (seuil par module, filtré par le profil `normal`).

**Avantages** : persist complet et à jour du schéma ; secrets au niveau habituel du dépôt (décision connue) ; historique actif pour la page `/graphiques`.
**Inconvénients** : reliquat `TasmotaSlaveModBus2` ; `grafana` absent (sans effet tant que l'historique est ON) ; l'état des relais du persist (`etat: OFF`, `timestamp` à 0) ne reprend rien de la carte en ligne (voir P4).
**Propositions** : P4, P11.

---

## 4. Écarts de fonctions : carte en ligne contre env S3

| Fonction | Carte en ligne (ancien code, ESP32 `.48`) | Env S3 |
|---|---|---|
| Topic / client MQTT | `cave/serveur-rly-cave` / `SERVEUR-RLY-CAVE` | `cave/serveur-rly-cave-v2` / `SERVEUR-RLY-CAVE-V2` |
| Qui écoute | non déterminable dans le dépôt pour l'ancien topic | flux Telegram `outils_docs/node-red/flow-telegram-pompe.json` (variable `TOPIC_CAVE` = `-v2`, `tele/…/ALERTE_POMPE`, `stat/…/RESULT`) ; flux historique `outils_docs/serveur_pi/historique_capteurs/` sur `tele/#` (tout topic) |
| Commandes | commandes de l'ancien `controleGlobal.be` | `EtatPompe`, `AcquittePompe`, `ReglageGlobal/Log/UDP/RangeExtender/Discovery`, `RoutageRangeExtender` |
| Capteurs | AM2301 GPIO 22 ON ; niveaux 2/15 OFF | AM2301 GPIO 11 ON ; niveaux 2/15 OFF (aligné) |
| Pages web | page de gestion ancienne (`gestionWeb.be`) | pages `controleWeb`, `/graphiques` (historique), pas `/cuve` |
| Relance de la pompe | absente de l'ancien code | `controleGeneral.be::finTimerRelai` (3 relances, pause 10 s, alerte MQTT) — **inerte** : `niveauHautActif` renvoie faux si le capteur est désactivé |
| Alerte | aucune | `publieAlerteRelance` -> `…/ALERTE_POMPE` -> Telegram ; ne peut pas partir sans capteur de niveau haut actif |
| Réseau | UDP / Range Extender / discovery OFF | UDP, Range Extender (AP `SERVEUR-RLY-CAVE-GATEWAY`, `192.168.4.1`), discovery ON, FTP ON |

**Avantages** : la S3 apporte les alertes Telegram, l'historique et les graphiques, la supervision par `EtatPompe` ; le flux Telegram est **déjà** écrit pour le topic `-v2`.
**Inconvénients** : tout ce qui consomme l'ancien topic (Node-RED, Grafana, tableaux de bord) cessera de voir la cave à la bascule ; la minuterie de 120 s reste la seule sécurité de la pompe tant que les capteurs de niveau sont OFF ; `cave` devient « maître » id 0, comme le P4 (`discoveryFonctions.be::discoveryFonctions_roleLocal`), avec un AP de plus.
**Propositions** : P3, P4, P5, P6.

---

## 5. Mémoire

**En place** : base `esp32s3-qio_opi` (`-DBOARD_HAS_PSRAM`, OPI), 8 Mo de PSRAM ; Berry utilise la PSRAM quand elle existe (`xdrv_52_3_berry_tasmota.ino`, `UsePSRAM`). Embarqué : socle solidifié + historique (3 modules) + leds (2 modules) en flash ; FS : `data/fs` (1,1 Mo), pages `/graphiques` (`echarts.min.js.gz` 368 Ko + scripts ~46 Ko), `jsParam.js`, dossier de la carte (44 Ko). LVGL + OpenHASP + ULP Berry compilés (base avec écran). La carte en ligne : tas libre 50-54 Ko, stable 16 jours (ESP32 sans PSRAM).
**Avantages** : PSRAM activée et déclarée dans la carte et les drapeaux ; énorme marge (8 Mo) par rapport au 50 Ko de l'ancienne carte ; partition de 3,9 Mo pour l'application.
**Inconvénients** : aucune mesure possible sans build (P1) ; LVGL inutile consomme du flash et un peu de RAM interne (P7) ; FS de 11,3 Mo pour 1,7 Mo de contenu (image de FS plus longue à écrire, sans effet fonctionnel).
**Propositions** : P1, P7.

---

## 6. Bancs

- `outils_docs/scripts_python/berry/banc_demarrage.py` couvre la cave S3 (`CARTES["tasmota32s3-cave-serveur-rly"]`), instantané `bouchons_berry/demarrage/tasmota32s3-cave-serveur-rly.txt`. Lancé : **VERT** (`OK P3.3`, `OK tasmota32s3-cave-serveur-rly`).
- L'instantané apparaît **modifié** (non commité, 2 lignes) pendant l'audit : modification faite par une autre session, non par cet audit. Il décrit déjà AM2301 (règles `Tele#AM2301#…`) et aucun capteur de niveau.
- Pas de banc pour la relance de la pompe ni pour `EtatPompe` / `AcquittePompe` (P10).
- Les bancs de page (`banc_graphiques.py`) ne ciblent pas la cave.

---

## Tableau des propositions

| N° | Proposition | Importance |
|---|---|---|
| **P1** | Compiler l'env (hors build de l'utilisateur) et relever : taille du firmware / partition, tas libre et PSRAM au démarrage ; aucune trace de build à ce jour | **bloquant** |
| **P2** | Remplacer `upload_port`/`monitor_port` = `COM3` (port de la cuve) par le port réel de la carte S3 de la cave, ou les commenter ; rappel dans le commentaire de l'env | important |
| **P3** | Avant la bascule : inventorier les consommateurs de `cave/serveur-rly-cave` sur le Pi (Node-RED, Grafana, Influx, autres appareils), les faire passer en `-v2`, puis effacer les messages retenus (LWT `Offline` du `-v2`, ancien topic) ; importer le flux Telegram | important |
| **P4** | Relever l'état réel des relais de la carte en ligne (copie du 31/10 : LED Machines, Pompe Cuve, Lavage à ON) et décider de leur état au premier démarrage de la S3, qui part de `etat: OFF` ; choisir l'heure de la bascule | important |
| **P5** | Décider si la cave doit être « maître » UDP / Range Extender / discovery / FTP : sinon passer ces 4 blocs à OFF dans le persist (pas d'AP ni de 2e fiche `maitre` sur le réseau) ; si oui, noter pourquoi (réseau des cartes du garage, `192.168.4.1/24` déjà pris par le P4) | important |
| **P6** | Consigner que relance + alerte + Telegram sont inertes tant que les capteurs de niveau (GPIO 2/15) sont OFF ; le jour où ils sont câblés : activer, puis essayer `EtatPompe` et `ALERTE_POMPE` sur carte | important |
| **P7** | Passer l'env sur `tasmota32s3-base-N16R8-sans-ecran` et ajouter `SET_ESP32_STACK_SIZE (24 * 1024)` dans la section cave du `.h` (comme les cartes du garage) | confort |
| **P8** | Corriger les commentaires de l'env : identité différente de la carte en ligne (hostname et groupe `tasmotas/cave` seuls communs) ; vérifier que la carte en ligne n'écoute pas le groupe `tasmotas/cave` | confort |
| **P9** | Retirer `leds` de `custom_berry_solidify` tant que ruban et LED RGB sont OFF (ou le garder par choix) ; charger `fsMqtt` dans l'autoexec si l'envoi de fichiers par MQTT doit marcher à la cave | confort |
| **P10** | Banc de la relance de sécurité (`finTimerRelai`, `relanceRelai`, `acquitteRelance`) et des commandes `EtatPompe` / `AcquittePompe` ; décider d'une seule copie de `controlePompeVideCave.be` | confort |
| **P11** | Nettoyer le persist S3 : clé `TasmotaSlaveModBus2` en trop, `diverses.historique.grafana` absente ; choisir `ledPower` ON ou OFF | confort |

## Non vérifié

Taille réelle du firmware et RAM (aucun build) ; consommateurs de l'ancien topic hors dépôt (Pi) ; groupe MQTT de la carte en ligne ; effet réel d'un 2e « maître » sur la table discovery du P4.
