---
chantier: envs-grenier-rdc-sonoff-cave
titre: Deux envs, serveur du grenier du RDC (volets) et Sonoff de la porte de la cave ; identité de la cave S3
objectif: Paramétrer deux environnements, la carte Waveshare 8DI-8RO du grenier du rez-de-chaussée qui commande les volets et le Sonoff ESP8285 de la porte de la cave, préparer le retour en production de la cave S3, lui ajouter l'écran 7B et en faire le maître range extender du Sonoff
statut: actif
cree: 2026-11-11
maj: 2026-11-11 (2e demande : écran, range extender de la cave, porte de cave esclave)
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

Deuxième demande de l'utilisateur (2026-11-11) :
- Ajouter le même écran que celui acheté pour les débits (Waveshare ESP32-S3-Touch-LCD-7B, 1024 × 600) au serveur relais
  de la cave ; l'écran est côté serveur (maître range extender), PAS sur le module de la porte de la cave (A9).
- Activer le range extender maître sur la cave S3 (A10).
- Faire du module de la porte de la cave un esclave de ce range extender, pour le lien bidirectionnel sur les lampes que
  chacun commande ; évaluer d'abord si ce petit module le permet (A11).
- Décision après évaluation (2026-11-11) : le module de la porte (.45) RESTE sur le Wi-Fi de la maison (pas d'esclave
  du range extender) ; lien en MQTT par Rules, avec un garde-fou contre la boucle d'écho (A11).

Relevé du module de la porte de la cave (2026-11-11, lecture seule HTTP de 192.168.0.45) : ce n'est PAS un ESP32 mais un
**ESP8285**, flash 1 Mo (programme 620 Ko, 380 Ko libres), tas libre 21 Ko, **Tasmota 12.0.2** (2022), `CfgHolder` 4617.
Hôte `PORTE-CAVE`, topic `cave/lumiere`, client MQTT `PORTE-CAVE`, broker 192.168.0.5, syslog vers 192.168.0.3, Wi-Fi
`SSId1` MAISON (`SSId2` vide). Template « Contacteur Cave » (BASE 2) : bouton GPIO0, Switch2 GPIO3 (contact de porte),
relais 1 GPIO12 (« Lumière de Cave »), relais 2 GPIO4 (« Porte de Cave »), LED GPIO13. `UfsSize` inconnue : pas de système
de fichiers, donc ni Berry, ni `autoexec.bat`. Rule1 (576 car., 242 libres) : bouton -> `POWER1 TOGGLE` ; `Power1` ->
`Publish cmnd/cave/serveur-rly-cave/POWER3 ON|OFF` et `stat/cave/lumiere/RESULT` ; porte ouverte (`Switch2#state=1`) ->
`POWER1 ON`, `POWER2 ON`, minuterie de 900 s qui éteint `POWER1` ; porte fermée -> les deux éteints. Le lien vers le
serveur passe donc aujourd'hui par MQTT, dans le sens porte -> serveur ; le sens retour reste à relever côté serveur (A11).

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
  essai Ethernet, en-tête 21/48) à la réception de la carte. Attention : en maître range extender (A10), la cave a besoin
  de son Wi-Fi pour le point d'accès ; l'essai Ethernet ne doit pas le couper (même remarque que pour le grenier du RDC).

## A7 — Retour en production de la cave S3
- [ ] Le jour du remplacement, sur ordre de l'utilisateur : passer l'identité de la cave S3 à 192.168.0.48 et
  `cave/serveur-rly-cave` dans le `_persist.json` du dossier S3 et dans la section du `.h` (client MQTT compris), diff
  montré avant écriture.
- [ ] Ancienne carte ESP32 éteinte AVANT la mise sous tension de la S3 (même IP, même client MQTT).
- [ ] Contrôle : Node-RED, Telegram et le Sonoff .45 (A8) voient la cave comme avant ; `lieux.py` range ses messages
  en Cave sans passer par le dossier `-sauvegarde`.

## A8 — Sonoff ESP8285 de la porte de la cave, lumières de la cave (192.168.0.45)
- [x] Analyse en lecture seule (Status 0, Template, Rules, UfsSize) — preuve : relevé HTTP du 2026-11-11 recopié au Contexte
  (ESP8285, 1 Mo, Tasmota 12.0.2, `UfsSize` inconnue, Rule1). Rien n'a été écrit sur la carte. Le modèle commercial
  exact reste à lire sur le boîtier (BASE 2 = famille Sonoff Dual).
- [ ] Créer un env de BASE `tasmota-base-esp8285` (demande de l'utilisateur du 2026-11-11 : d'autres Sonoff du parc ont
  la même puce et seront paramétrés plus tard), sur le modèle de nom de `tasmota32-base` / `tasmota32s3-base-N16R8` :
  `extends = env:tasmota`, carte PlatformIO `esp8285` (1 Mo, flash en DOUT), réglages communs aux Sonoff ESP8285 seulement ;
  bloc de commentaire en tête comme les autres bases. La pompe de piscine (`tasmota-pompe-piscine`, Sonoff S2X, `extends =
  env:tasmota`) n'est PAS rebasculée sans vérifier sa puce (`Status 2` / `Status 4`).
- [ ] Créer son env (proposition : `tasmota-cave-sonoff-porte`, lieu Cave), SANS Berry : `extends =
  env:tasmota-base-esp8285` (et non `tasmota32`), sans système de fichiers ni `custom_files_upload` ; section `#elif` du `.h` avec l'identité relevée sur la
  carte (IP .45, hôte, topic, client, template) ; nom et contenu validés par l'utilisateur. Pas de dossier `data/` (ni
  persist, ni `autoexec.bat` : pas de FS sur 1 Mo). Classement par `lieux.py` : par l'IP .45 tant qu'il est sur le Wi-Fi
  maison (il y reste, décision du 2026-11-11).
- [ ] Compilation par la page Build : taille de l'image comparée aux 1 Mo (une mise à jour depuis 12.0.2 sur 1 Mo passe
  par `tasmota-minimal`, en deux temps : à ne faire qu'avec l'accord de l'utilisateur, la carte en service n'en a pas besoin).
- [ ] Relever le sens retour côté serveur : ce que la cave S3 (et l'ancienne carte en service) fait de
  `cmnd/cave/serveur-rly-cave/POWER3`, et ce qu'elle envoie au Sonoff (`cave/lumiere`).
- [ ] Réglages du Sonoff par `Backlog` et `Rule` en console seulement (pas d'`autoexec.bat` possible), proposés puis
  validés par l'utilisateur ; garder de la place dans Rule1 (242 car. libres) ou passer à Rule2.

## A9 — Écran Waveshare 7B pour le serveur relais de la cave
Contrainte matérielle : le 7B (ESP32-S3-Touch-LCD-7B) est une carte complète, avec son propre S3 et une dalle RGB
parallèle (une vingtaine de broches). La 8DI-8RO de la cave n'a que GPIO21 et GPIO48 de libres : elle ne peut pas piloter
cette dalle. « L'écran sur le serveur de la cave » veut donc dire un 7B posé à côté du serveur, avec son propre env,
qui affiche et commande ce que porte le serveur (relais, lumières, température, pompe).
- [ ] Faire trancher par l'utilisateur le lien entre le 7B et le serveur de la cave. Proposition de Claude : esclave du
  range extender de la cave (A10, Wi-Fi sur son point d'accès) avec la pile Berry d'esclave (ModBus UDP, push, `ImAlive`),
  comme les débits mais dans l'autre sens (là-bas, l'écran est le maître). Autres voies : ModBus série sur le RS485 17/18
  de la cave (le 7B a un RS485 sur 16/15), ou MQTT seul.
- [ ] Env du 7B (proposition : `tasmota32s3-cave-ecran`, dossier `data/cave/tasmota32s3-ecran`) créé à partir de
  `tasmota32s3-bureau-ecran-debits-pac` (même carte : expandeur I2C 0x24, `preinit.be`, `custom_interface_ecran`) ;
  identité validée par l'utilisateur, IP du range extender (0.0.0.0, adresse `<ipMaitre>:<8080 + id - 1>`).
- [ ] Dépend du plan `debits-deux-cartes` A8 : le code d'écran générique (`ecranFonctions`, veille, luminosité, polices)
  n'y est pas encore validé sur carte ni solidifié. Reprendre ce module tel quel ; ne pas le recopier dans ce plan.
- [ ] Maquette des vues de la cave (lumières, relais, température et humidité, pompe) proposée puis validée par
  l'utilisateur (skill `lvgl-haspmota`), interface HASPmota ou LVGL selon le choix fait pour les débits.
- [ ] Boutons physiques du serveur de la cave remplacés par ceux de l'écran ? (idée de l'utilisateur, 2026-11-11). À
  trancher avec lui, entrée DI par entrée DI. Réserve de Claude : l'écran est une autre carte, reliée par le réseau ;
  s'il tombe, on ne commande plus rien sur place. Garder au moins un bouton physique pour la pompe de la cave et pour
  la lumière ; les entrées DI libérées restent câblables plus tard. Si des boutons sont retirés : persist et brochage
  de la cave mis à jour, `banc_demarrage.py`.
- [ ] `banc_demarrage.py`, `verifie_berry.py`, agent `relecteur-berry`, compilation par la page Build ; essai sur carte.

## A10 — Range extender maître sur la cave S3
Déjà en place dans le dépôt (relevé du 2026-11-11) : `USE_WIFI_RANGE_EXTENDER` et `WIFI_RGX_SSID
"SERVEUR-RLY-CAVE-GATEWAY"` dans la section cave du `.h` ; bloc `rangeExtender` du persist S3 (`activation: ON`, `id: 0`,
AP 192.168.4.1/24). Mais `routeNAPT: OFF` : sans NAPT, un esclave n'atteint ni le broker (192.168.0.5) ni le syslog.
- [ ] Passer `rangeExtender.AP.routeNAPT` à `ON` dans le `_persist.json` du dossier S3 (accord de l'utilisateur, diff
  montré), en reprenant les réglages du P4 du garage ; vérifier que la section du `.h` active aussi le NAPT
  (`USE_WIFI_RANGE_EXTENDER_NAPT` ou équivalent du P4).
- [ ] Ports d'accès aux esclaves : `<ip cave>:<8080 + id - 1>` par `RoutageRangeExtender` ; id réservé pour l'écran 7B
  si A9 retient le range extender, noté dans le persist et dans `discovery`. Le Sonoff de la porte n'en fait plus partie
  (décision du 2026-11-11) : sans l'écran, A10 n'a plus d'objet.
- [ ] Le point d'accès exige le Wi-Fi : la voie Ethernet (A6, améliorations) ne doit pas le couper.
- [ ] `banc_demarrage.py` ; compilation par la page Build ; essai sur carte (AP visible, NAPT : un client du point
  d'accès joint le broker), d'abord avec l'identité d'essai .243, avant le retour en production (A7).

## A11 — Lien MQTT entre la porte de la cave et le serveur de la cave, garde-fou contre l'écho
Évaluation (2026-11-11) : la pile d'esclave de ce dépôt (ModBus UDP, push, `ImAlive`, discovery) est du Berry, ~400 Ko de
sources : IMPOSSIBLE sur l'ESP8285 (pas de Berry, 1 Mo, 21 Ko de tas). Voies natives : (1) MQTT + Rules, retenue ;
(2) `WebSend`, bloquant si l'autre carte ne répond pas ; (3) Device Groups, multicast. Décision de l'utilisateur : le .45
reste sur le Wi-Fi MAISON (92 %, -54 dBm), lien en MQTT par Rules.

Aujourd'hui, les deux sens existent déjà, sans garde : la Rule1 du Sonoff publie `cmnd/cave/serveur-rly-cave/POWER3` à
chaque `Power1#State`, et le serveur S3 publie `cmnd/cave/lumiere/POWER1` à chaque changement de son relais id 3
(`publishMQTT` de `relais.relai1` « LED Machines » dans le persist, appliqué par `controleGeneral.be`, bloc « emission
d'un message MQTT »). Dans l'amont, `Power<n>#State` ne part que sur un VRAI changement
(`xdrv_10_system_events.ino::SystemEventsEvery50msPowerDimmerEvent` compare l'ancien et le nouvel état bit à bit) : un
aller-retour s'arrête donc de lui-même. La boucle reste possible quand les deux côtés changent en même temps dans des
sens opposés (oscillation ON/OFF entretenue par la latence du broker), ou si un côté republie sans changement.

Garde-fou retenu, identique des deux côtés, en Rules seulement (`USE_RULES` existe sur l'ESP8285 et sur la cave :
section cave du `.h`, avec `USE_EXPRESSION`) :
- les ordres de l'autre carte arrivent par un `Event`, jamais par un `POWER` direct ;
- `Var1` garde le dernier état reçu de l'autre carte ;
- un changement n'est renvoyé que s'il diffère de `Var1`. Un état appliqué sur ordre de l'autre carte est donc égal à
  `Var1` et ne repart pas.

```
Sonoff (Rule2) :
ON Event#lumSrv DO Backlog Var1 %value%; Power1 %value% ENDON
ON Power1#State!=%var1% DO Backlog Var1 %value%; Publish cmnd/<topic cave>/Event lumPorte=%value% ENDON
Serveur de la cave (Rule1) :
ON Event#lumPorte DO Backlog Var1 %value%; Power3 %value% ENDON
ON Power3#State!=%var1% DO Backlog Var1 %value%; Publish cmnd/cave/lumiere/Event lumSrv=%value% ENDON
```
Croisement (les deux changent en même temps) : chacun applique l'ordre de l'autre sans le renvoyer, donc pas
d'oscillation. Au pire, les deux lampes restent un temps dans des états différents, jusqu'à l'action suivante.

- [ ] Faire valider le garde-fou et la table des relais (Sonoff : `POWER1` lumière, `POWER2` porte ; serveur : `POWER3`
  lumière de la cave), et dire si `POWER2` doit aussi être relayé.
- [ ] Vérifier sur le Tasmota 12.0.2 du Sonoff qu'un déclencheur compare bien à `%var1%` (`Power1#State!=%var1%`) :
  essai en console, sans brancher l'autre côté (`Var1 1`, `Power1 1` -> aucune publication ; `Power1 0` -> une).
- [ ] Sonoff : retirer de la Rule1 les deux règles `Power1#State` qui publient `POWER3` (la Rule1 garde le bouton, la
  porte et la minuterie) et poser la Rule2 ci-dessus. Commandes proposées puis lancées en console avec l'accord de
  l'utilisateur, sans `Restart`.
- [ ] Serveur de la cave : retirer le `publishMQTT` de `relais.relai1` du `_persist.json` du dossier S3 (sinon le Berry
  publie en double, hors garde-fou ; accord de l'utilisateur, diff montré) et poser la Rule1 ci-dessus par l'`autoexec.bat`
  de la carte (fichier du dossier S3, sans commande qui redémarre). Topic en vigueur : `cave/serveur-rly-cave-v2`
  pendant les essais en .243, `cave/serveur-rly-cave` après A7 (cette bascule remplace l'ancienne étape « prévoir la
  bascule au retour en production »).
- [ ] Essai, avec preuve dans le sniffeur MQTT (:7100) : allumage depuis la porte, depuis la cave (bouton, puis écran si
  A9) et depuis la porte qui s'ouvre ; une seule publication par action, aucune en retour ; double appui rapide des deux
  côtés à la fois : pas d'oscillation.

## Améliorations restantes
- [ ] [projet] Ethernet W5500 de la carte du grenier du RDC (`ReglageGlobal VoieReseau ethernet`) si un câble arrive au grenier.
- [ ] [projet] Alias Berry lisible par volet (`VoletPorte`, `VoletCuisine`) si l'utilisateur le veut (A4).
- [ ] [projet] Resynchroniser les deux lampes de la cave à la reconnexion MQTT d'une des cartes (`Mqtt#Connected`).
  Aujourd'hui, un ordre perdu pendant une coupure du broker n'est jamais rattrapé.

## Vérification
`test_lieux.py`, `banc_demarrage.py`, `verifie_berry.py`, compilation par la page Build ; essais sur carte à la réception.
