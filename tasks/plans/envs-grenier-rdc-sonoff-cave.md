---
chantier: envs-grenier-rdc-sonoff-cave
titre: Deux envs, serveur du grenier du RDC (volets) et Sonoff de la porte de la cave ; identité de la cave S3
objectif: Paramétrer deux environnements, la carte Waveshare 8DI-8RO du grenier du rez-de-chaussée qui commande les volets et le Sonoff ESP32 de la porte de la cave, et préparer le retour en production de la cave S3
statut: actif
cree: 2026-11-11
maj: 2026-11-11
---
# Deux envs : serveur du grenier du RDC et Sonoff de la porte de la cave ; cave S3

> Ce plan se suit dans une NOUVELLE conversation : y taper `/suivi suivre envs-grenier-rdc-sonoff-cave`, puis commencer par A0.
> Cocher chaque étape dès qu'elle est vérifiée, avec « — preuve : … ».

## Contexte

Demande du 2026-11-11, posée pendant le plan `lieu-partage-syslog-mqtt`.

Carte : Waveshare ESP32-S3-ETH-8DI-8RO (WROOM-1U-N16R8, 8 Mo de PSRAM, 7-36 V), la même que la cave S3. Tout ce qu'il
faut savoir de la carte est déjà écrit pour la cave : commentaire de `[env:tasmota32s3-cave-serveur-rly]` dans
`platformio_tasmota_cenv.ini`, plan clos `tasks/plans/cave-s3-waveshare.md`, `outils_docs/cartes_relais_cave/README.md`,
image `outils_docs/Schémas de branchement - Attribution des PINS des modules/cave/Waveshare-ESP32-S3-ETH-8DI-8RO.jpg`.
En bref : relais CH1-CH8 par le TCA9554 (I2C 0x20, SDA 42, SCL 41, `tca9554.dat`, `USE_TCA9554`), entrées isolées
DI1-DI8 (DI1 GPIO4, DI2 GPIO5, DI3 GPIO6, DI4 GPIO7…), RS485 17/18, W5500 (INT 12, MOSI 13, MISO 14, SCLK 15, CS 16),
en-tête GPIO 21 et 48 ; GPIO interdits 19-20, 26-37, 43-46.

Décisions de l'utilisateur (2026-11-11) :
- Cave S3 (`tasmota32s3-cave-serveur-rly`, déjà adaptée à la Waveshare) : identité d'essai 192.168.0.243 et topic
  `cave/serveur-rly-cave-v2` pendant les essais ; reprise de 192.168.0.48 et `cave/serveur-rly-cave` le jour du
  remplacement, par une action « Retour en production » (A7). La carte en service tourne l'ancien code
  (`data/cave/tasmota32-serveur-rly-sauvegarde/`), en 192.168.0.48, topic `cave/serveur-rly-cave`.
- Nouvelle carte du grenier du rez-de-chaussée : nom d'hôte `SERVEUR-GRENIER-RDC`, topic `rdc/grenier`, en Wi-Fi
  (le range extender maître a besoin de son point d'accès ; l'Ethernet reste possible plus tard). Fonctions : MQTT,
  ModBus maître, range extender maître, ModBus UDP, volets roulants, température et humidité par un DHT22.
- Volet de la porte d'entrée : moteur recâblé sur 2 relais de la Waveshare (montée, descente, interverrouillés) ; le
  Sonoff Dual R3 actuel (`tasmota32-rdc-vr-porte`, 192.168.0.46, topic `volet/entree`) est retiré. Volet de la cuisine :
  n'existe pas encore, préparé sur 2 autres relais.
- Commandes locales : 2 boutons par volet (montée, descente ; un nouvel appui arrête) sur les entrées DI.

Proposition de Claude, à valider en A1 : env `tasmota32s3-rdc-grenier`, dossier `data/rdc/tasmota32s3-grenier`, define
`FIRMWARE_ESP32S3_RDC_GRENIER`, client MQTT `SERVEUR-GRENIER-RDC`, IP 192.168.0.44 (libre dans `user_config_override.h`,
à vérifier sur le réseau), point d'accès `SERVEUR-GRENIER-RDC-GATEWAY`. Brochage proposé : volet porte CH1 (montée) CH2
(descente), volet cuisine CH3 CH4, boutons porte DI1 DI2, boutons cuisine DI3 DI4, DHT22 (AM2301) sur GPIO21 comme la
cave, LED WS2812 GPIO38.

Identification des volets sur MQTT (question de l'utilisateur, réponse de Claude à valider en A4) : `vrFonctions.be`
configure les volets NATIFS de Tasmota (`ShutterMode`, `ShutterRelay`, `ShutterButton`, durées). Sur le réseau, un
volet est donc « carte + numéro » : `cmnd/rdc/grenier/ShutterPosition1 50`, `cmnd/rdc/grenier/ShutterOpen2`, état dans
`stat/rdc/grenier/RESULT` et `tele/rdc/grenier/SENSOR` (`"Shutter1": {"Position": …}`), et la découverte Home Assistant
(`tasmota/discovery/<MAC>`) les publie comme deux volets de la même carte. Shutter1 = porte d'entrée, Shutter2 = cuisine,
nommés dans le persist et par `FriendlyName`. Si un nom lisible est voulu dans le topic, une commande Berry d'alias
(`cmnd/rdc/grenier/VoletPorte 50`) est possible en plus.

## A0 — Retour au plan d'origine

Plan d'origine : [tasks/plans/lieu-partage-syslog-mqtt.md](lieu-partage-syslog-mqtt.md), lui-même suite de
[tasks/plans/classement-par-lieu.md](classement-par-lieu.md).

- [ ] Ouvrir une nouvelle conversation et y taper `/suivi suivre envs-grenier-rdc-sonoff-cave` ; pour revoir le plan d'origine :
  `/suivi suivre lieu-partage-syslog-mqtt`, puis revenir par `/suivi suivre envs-grenier-rdc-sonoff-cave`. À cocher quand
  l'aller-retour a été fait une fois et que la vue a basculé dans les deux sens.

## A1 — Identité et création de l'env du grenier du RDC
- [ ] Valider avec l'utilisateur le nom d'env, le dossier, l'IP (vérifier qu'aucun appareil ne répond sur 192.168.0.44)
  et le brochage proposés au Contexte.
- [ ] Créer l'env à partir de la carte modèle `tasmota32s3-cave-serveur-rly` (même carte) par la page « Fichiers Berry
  par env » (7800, création d'env) ou l'assistant persist (7900) : section du cenv, dossier `data/rdc/tasmota32s3-grenier`,
  section `#elif defined(FIRMWARE_ESP32S3_RDC_GRENIER)` du `.h` (accord de l'utilisateur donné par sa demande du
  2026-11-11) ; identité remplacée (hôte, topic, client, IP, point d'accès).
- [ ] `lieux.py` range la carte en « Rez-de-chaussée » (`test_lieux.py`).

## A2 — Fonctions de la carte : MQTT, ModBus, range extender, ModBus UDP, volets, DHT22
- [ ] Persist : MQTT actif ; ModBus maître (`drivers.ModBus`) ; range extender maître ; ModBus UDP ; bloc des volets
  (2 volets) ; capteur AM2301/DHT22. Partir des blocs des cartes qui les ont déjà (P4 du garage pour ModBus et range
  extender maître, `tasmota32-rdc-vr-porte` pour les volets, cave S3 pour l'AM2301 et le TCA9554).
- [ ] Cenv : `custom_berry_solidify` (socle + modules ModBus, UDP, range extender, volets), `custom_files_exclude`
  (rien de la cave : pompe, LoRaWAN, ES8311, coprocesseur, pages cuve et énergie), `custom_files_upload`, `lib_ignore`.
- [ ] Autoexec : ordre de chargement (un module importé par un `controleXxx` compilé avant lui) ; chaque import existe
  dans l'image de l'env.
- [ ] `banc_demarrage.py` : instantané du nouvel env enregistré ; `verifie_berry.py` vert ; agent `relecteur-berry`.

## A3 — Brochage et volets
- [ ] Relais CH1-CH4 par le TCA9554 (`tca9554.dat` du dossier de la carte), interverrouillage montée/descente par volet.
- [ ] Boutons DI1-DI4, DHT22 sur GPIO21 ; classeur `Brochage GPIO - tasmota32s3-rdc-grenier.xlsx` par
  `genere_brochage_horizontal.py` (Waveshare 8DI-8RO déjà connue), complété à la main.
- [ ] Durées d'ouverture et de fermeture du volet de la porte reprises du Sonoff Dual R3 (lecture seule de .46 :
  `ShutterOpenDuration1`, `ShutterCloseDuration1`), à remesurer après le recâblage.

## A4 — Identification des volets sur MQTT
- [ ] Faire valider par l'utilisateur la réponse du Contexte (volets natifs Shutter1/Shutter2 sous `rdc/grenier`, noms,
  alias Berry facultatif).
- [ ] Recenser ce qui vise `volet/entree` aujourd'hui (Node-RED du Pi, Alexa, Home Assistant) et la liste des
  automatisations à basculer vers `rdc/grenier` Shutter1.

## A5 — Compilation et mise en service
- [ ] Compilation par la page Build (:7700), SUCCESS lu en fin de journal, taille de l'image et du FS.
- [ ] À la réception de la carte : flash série, `Status 5`, volets en marche à vide (relais seuls), puis moteur recâblé.
- [ ] Sonoff Dual R3 (.46) éteint et retiré ; automatisations basculées ; env `tasmota32-rdc-vr-porte` gardé ou
  supprimé selon l'utilisateur.

## A6 — Cave S3 : identité d'essai
- [ ] Vérifier que l'env `tasmota32s3-cave-serveur-rly` porte bien .243 et `cave/serveur-rly-cave-v2` (section commune
  `FIRMWARE_ESP32_CAVE_SERVEUR_RLY || FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY` du `.h` et `_persist.json` du dossier S3).
- [ ] Reprendre les améliorations restantes du plan `cave-s3-waveshare` (compilation, port COM, câblage DI3/DI4,
  essai Ethernet, en-tête 21/48) à la réception de la carte.

## A7 — Retour en production de la cave S3
- [ ] Le jour du remplacement, sur ordre de l'utilisateur : passer l'identité de la cave S3 à 192.168.0.48 et
  `cave/serveur-rly-cave` dans le `_persist.json` du dossier S3 et dans la section du `.h` (client MQTT compris), diff
  montré avant écriture.
- [ ] Ancienne carte ESP32 éteinte AVANT la mise sous tension de la S3 (même IP, même client MQTT).
- [ ] Contrôle : Node-RED, Telegram et le Sonoff .45 (A8) voient la cave comme avant ; `lieux.py` range ses messages
  en Cave sans passer par le dossier `-sauvegarde`.

## A8 — Sonoff ESP32 de la porte de la cave, lumières de la cave (192.168.0.45)
- [ ] Analyse en lecture seule : `Status 0`, `Module`, `Template`, `Rules`, `SetOption` utiles, place du système de
  fichiers (`UfsSize`, `UfsFree`), version ; modèle exact du Sonoff. Rien n'est écrit sur la carte.
- [ ] Créer son env (proposition : `tasmota32-cave-sonoff-porte`, lieu Cave), SANS Berry : section du cenv (taille de
  flash et partitions du Sonoff, aucun module Berry ni `custom_berry_solidify`), section `#elif` du `.h` avec l'identité
  relevée sur la carte (IP .45, hôte, topic, client, template), dossier `data/cave/tasmota32-sonoff-porte` réduit à
  l'`autoexec.bat` (pas de `_persist.json` : la carte ne lit pas le persist) ; nom et contenu validés par
  l'utilisateur. `lieux.py` le range en Cave par son IP (syslog), comme les cartes sans persist.
- [ ] Compilation par la page Build ; taille du FS de l'image comparée à la place libre relevée sur la carte.
- [ ] Recenser comment il échange avec le serveur relais de la cave par MQTT pour allumer et éteindre les 2 lumières
  (topics, règles des deux côtés).
- [ ] Proposer un `autoexec.bat` (pas de Berry : place trop faible) : réglages seulement, sans aucune commande qui
  redémarre la carte (`Module`, `Template`, `Gpio`, `Hostname`, `Topic`, `SetOption` à redémarrage, `Restart`…), pour
  éviter une boucle de redémarrage ; décision de l'utilisateur avant tout envoi.
- [ ] Prévoir la bascule de ce lien au retour en production de la cave (A7) si le topic change entre-temps.

## Améliorations restantes
- [ ] [projet] Ethernet W5500 de la carte du grenier du RDC (`ReglageGlobal VoieReseau ethernet`) si un câble arrive au grenier.
- [ ] [projet] Alias Berry lisible par volet (`VoletPorte`, `VoletCuisine`) si l'utilisateur le veut (A4).

## Vérification
`test_lieux.py`, `banc_demarrage.py`, `verifie_berry.py`, compilation par la page Build ; essais sur carte à la réception.
