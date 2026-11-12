---
chantier: envs-grenier-rdc-sonoff-cave
titre: Deux envs, serveur du grenier du RDC (volets) et Sonoff de la porte de la cave ; identité de la cave S3
objectif: Paramétrer deux environnements, la carte Waveshare 8DI-8RO du grenier du rez-de-chaussée qui commande les volets et le Sonoff ESP8285 de la porte de la cave, préparer le retour en production de la cave S3, lui ajouter l'écran 7B et en faire le maître range extender du Sonoff ; ajouter la pompe de la piscine (192.168.0.40) le projecteur du jardin (192.168.0.41) et celui du barbecue : sauvegarde, env, mise en service
statut: actif
cree: 2026-11-11
maj: 2026-11-12 (A16 : pompe renommée tasmota-jardin-pompe-piscine, lieu Jardin)
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

- [x] Ouvrir une nouvelle conversation et y taper `/suivi suivre envs-grenier-rdc-sonoff-cave` ; pour revoir le plan d'origine :
  `/suivi suivre lieu-partage-syslog-mqtt`, puis revenir par `/suivi suivre envs-grenier-rdc-sonoff-cave`. À cocher quand
  l'aller-retour a été fait une fois et que la vue a basculé dans les deux sens.

## A1 — Identité et création de l'env du grenier du RDC
- [x] Valider avec l'utilisateur le nom d'env, le dossier, l'IP (vérifier qu'aucun appareil ne répond sur 192.168.0.44) — preuve : 2026-11-11, .44 sans réponse (ping 100 % perdus, HTTP 000, absente de l'ARP, absente du dépôt) ; identité et brochage du Contexte validés tels quels par l'utilisateur
  et le brochage proposés au Contexte.
- [x] Créer l'env à partir de la carte modèle `tasmota32s3-cave-serveur-rly` (même carte) par la page « Fichiers Berry par env » — preuve : moteur `fichiers_berry_creation.cree` (diff lu, empreinte dff8be29…, aucun refus), copie de sécurité `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\20261111-160453-258612-creation` ; section `[env:tasmota32s3-rdc-grenier]` du cenv, dossier `data/rdc/tasmota32s3-grenier`, section `FIRMWARE_ESP32S3_RDC_GRENIER` du `.h`
  (7800, création d'env) ou l'assistant persist (7900) : section du cenv, dossier `data/rdc/tasmota32s3-grenier`,
  section `#elif defined(FIRMWARE_ESP32S3_RDC_GRENIER)` du `.h` (accord de l'utilisateur donné par sa demande du
  2026-11-11) ; identité remplacée (hôte, topic, client, IP, point d'accès). Repris à la main après la création : les
  deux conditions internes `FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY` du `.h` (branche S3 seule gardée, FTP gardé ; #if/#endif
  15/15) ; base **sans écran** (`tasmota32s3-base-N16R8-sans-ecran`, `${lib_inutiles.sans_ecran}`, pile de 24 Ko dans le
  `.h`), car l'écran sera une AUTRE carte ESP32, comme pour les débitmètres (décision de l'utilisateur du 2026-11-11).
- [x] `lieux.py` range la carte en « Rez-de-chaussée » (`test_lieux.py`) — preuve : `lieux.lieu('tasmota32s3-rdc-grenier')` = `rdc` ; `lieux.identites` : hôte SERVEUR-GRENIER-RDC, topic rdc/grenier, IP 192.168.0.44 ; `test_lieux.py` VERT (code 0)

Décisions de l'utilisateur pendant A2 (2026-11-11) : le grenier du RDC prend l'IP du volet de la porte,
**192.168.0.46** (et non plus .44 : `.h` et persist corrigés), et se connecte aux mêmes réseaux que lui (`STA_SSID1`
MAISON puis `STA_SSID2` « Relai Wifi 2.4G KuWFi », réseaux communs du `.h` ; le persist copié de la cave avait « Relai
Wifi Cave » puis MAISON). Le Sonoff Dual R3 (.46) doit donc être éteint AVANT la mise sous tension du grenier (A5).

## A2 — Fonctions de la carte : MQTT, ModBus, range extender, ModBus UDP, volets, DHT22
- [x] Persist : MQTT actif ; ModBus maître (`drivers.ModBus`) ; range extender maître ; ModBus UDP ; bloc des volets — preuve : `data/rdc/tasmota32s3-grenier/_persist.json` (MQTT, ModBus maître Serial+UDP, range extender id 0 + routeNAPT ON, UDP, 3 volets : porte DI1/DI2, cuisine DI3/DI4, trappe DI5 toggle + fins de course DI6/DI7, `inverse` 0, AM2301 GPIO21, Ethernet OFF, pompe retirée) ; `genere_schema_persist.py --valide` : 11 persists à 0 erreur
  (2 volets) ; capteur AM2301/DHT22. Partir des blocs des cartes qui les ont déjà (P4 du garage pour ModBus et range
  extender maître, `tasmota32-rdc-vr-porte` pour les volets, cave S3 pour l'AM2301 et le TCA9554).
- [x] Écran déporté (décision de l'utilisateur du 2026-11-11) : l'écran sera une autre carte ESP32, comme pour les — preuve : grenier MAÎTRE (choix de l'utilisateur), esclave `TasmotaSlaveModBus1` id 1 « ECRAN-GRENIER-RDC (carte à venir) » inactif dans `drivers.ModBus` ; côté range extender rien à déclarer (l'esclave se présente par ImAlive)
  débitmètres (`tasmota32s3-bureau-ecran-debits-pac` et son acquisition) ; les deux cartes communiquent par leurs range
  extenders, tous deux activés. Ici, configuration SEULEMENT, aucun GPIO d'écran : préparer le persist pour accueillir
  cette carte (id réservé dans le range extender et dans ModBus, lecture groupée et push multi-valeurs comme
  `drivers.ModBus.lectureGroupee` des débits). Rôle de chaque carte à trancher avec l'utilisateur : aux débits, l'écran
  est le maître (id 0) et l'acquisition l'esclave (id 1) ; ici, le grenier est déjà prévu maître.
- [x] Cenv : `custom_berry_solidify` (socle + modules ModBus, UDP, range extender, volets), `custom_files_exclude` — preuve : `[env:tasmota32s3-rdc-grenier]` (socle + modbus + historique + leds + vrFonctions + controleVoletRoulants ; liste noire réduite) ; `controlePompeVideCave.be` supprimé ; liste `lib_inutiles.sans_mpu6050` pour les 8 autres envs (USE_MPU6050 des 2 greniers) ; banc_demarrage VERT
  (rien de la cave : pompe, LoRaWAN, ES8311, coprocesseur, pages cuve et énergie), `custom_files_upload`, `lib_ignore`.
  La création a recopié la liste noire de la cave, qui EXCLUT `modbusFonctions`, `vrFonctions`, `controleModbus`,
  `controleVoletRoulants`, `modBus_*` : à retirer de la liste. Le dossier de la carte contient encore
  `controlePompeVideCave.be` (pompe de la cave) : à retirer, avec son chargement dans l'autoexec.
- [x] `.h` : retirer le `#undef USE_SHUTTER` recopié de la cave (les volets en ont besoin) et relire les commentaires — preuve : section `FIRMWARE_ESP32S3_RDC_GRENIER` : `#define USE_SHUTTER`, USER_TEMPLATE identique au template du persist (vérifié par script), `USE_MPU6050` (ici et au 2e étage), commentaires corrigés
  hérités de la cave (animation LED, MQTT « V2 »).
- [x] Autoexec : ordre de chargement (un module importé par un `controleXxx` compilé avant lui) ; chaque import existe — preuve : ordre du P4 (`fsMqtt` compris), relu par l'agent relecteur-berry (aucun défaut bloquant) ; banc_demarrage VERT
  dans l'image de l'env.
- [x] `banc_demarrage.py` : instantané du nouvel env enregistré ; `verifie_berry.py` vert ; agent `relecteur-berry`. — preuve : `bouchons_berry/demarrage/tasmota32s3-rdc-grenier.txt`, banc VERT (9 cartes) ; verifie_berry 0 erreur ; relecteur-berry sans défaut bloquant ; `banc_inclinaison.be` sections 17-18 (inverse 0, Interlock unique) vertes, rouges avec l'ancien vrFonctions.be

## A3 — Brochage et volets
- [ ] Relais CH1-CH4 par le TCA9554 (`tca9554.dat` du dossier de la carte), interverrouillage montée/descente par volet. Fait en A2 sur le papier (CH1-CH6, `Interlock 1,2 3,4 5,6` corrigé dans `vrFonctions.be`) : à cocher après l'essai à vide sur la carte.
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
- [ ] Sonoff Dual R3 (.46) éteint et retiré AVANT la mise sous tension du grenier (même IP .46) ; automatisations basculées ; env `tasmota32-rdc-vr-porte` gardé ou
  supprimé selon l'utilisateur.

## A6 — Cave S3 : identité d'essai
- [x] Vérifier que l'env `tasmota32s3-cave-serveur-rly` porte bien .243 et `cave/serveur-rly-cave-v2` — preuve : 2026-11-12, `.h` `WIFI_IP_ADDRESS "192.168.0.243"`, `MQTT_TOPIC "cave/serveur-rly-cave-v2"`, `MQTT_CLIENT_ID "SERVEUR-RLY-CAVE-V2"` ; `data/cave/tasmota32s3-serveur-rly/_persist.json` : `serveur.IP.IPAddress` .243, `serveur.mqtt.topic`/`client` identiques, hôte `SERVEUR-RLY-CAVE`. Le persist de `data/cave/tasmota32-serveur-rly` (env ESP32, même section du `.h`) porte la même identité d'essai ; la carte en service tourne le code du dossier `-sauvegarde` (.48), qui n'est pas touché. Hostname : `USER_BACKLOG` du `.h` passé à `SERVEUR-RLY-CAVE-V2` pour `FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY` seul (accord du 2026-11-12), égal à `serveur.hostname` du persist ; l'env ESP32 garde `SERVEUR-RLY-CAVE`.
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
- [x] Configuration actuelle décodée et rangée dans le dépôt (demande du 2026-11-12 : paramétrer sans Berry, par le fichier de configuration) — preuve : /dl de .45 (12.0.2, CRC valide) et de la TV du salon .42 (13.1.0, **ESP8266EX** 1 Mo DOUT, hôte `TV`, topic `salon/tv`) décodés par decode-config 16.0.0.0 ; `data/cave/tasmota-lumiere-porte/config_decodee.json` (295 clés) et `data/rdc/tasmota-tv-salon/config_decodee.json` (304 clés), `mqtt_pwd`/`sta_pwd` masqués (`build_sauvegarde._masque`), témoin : aucun secret en clair.
- [x] Onglet « Sauvegarde configuration » prêt pour l'ESP8266 (accord de l'utilisateur du 2026-11-12) — preuve : `decode_config.py::ecrit_copie` laisse decode-config écrire les textes d'une config `config_version` 0 (indices décalés après `SET_ADC_PARAM1`, `tasmota.h::SettingsTextIndex`) ; `test_build_sauvegarde.py` VERT (62 OK), cas ESP8266 rouge avant (`telegram_fingerprint` en 125 au lieu de 98, copie refusée), vert après ; page : MQTT masquée et désactivée pour un env sans `fichiers_berry` (`build_page_sauvegarde.py::sCharge`), sonde `test_build_page_sauvegarde_chrome.py` VERTE. Aucune clé à risque dans les configs 12.0.2 et 13.1.0 relevées.
- Noms validés par l'utilisateur (2026-11-12) : base `tasmota-base-1M` (la .42 est un ESP8266EX : le nom `tasmota-base-esp8285` de l'étape suivante est remplacé), envs `tasmota-cave-lumiere-porte` et `tasmota-rdc-tv-salon`. Questions et essais propres à ces modules : A15.
- [x] Créer un env de BASE `tasmota-base-esp8285`, nommé `tasmota-base-1M` — preuve : `platformio_tasmota_cenv.ini` `[env:tasmota-base-1M]` (`extends = env:tasmota`, carte `esp8266_1M` résolue par `ProjectConfig`, `custom_files_upload = no_files` amont), 2026-11-12 (demande de l'utilisateur du 2026-11-11 : d'autres Sonoff du parc ont
  la même puce et seront paramétrés plus tard), sur le modèle de nom de `tasmota32-base` / `tasmota32s3-base-N16R8` :
  `extends = env:tasmota`, carte PlatformIO `esp8285` (1 Mo, flash en DOUT), réglages communs aux Sonoff ESP8285 seulement ;
  bloc de commentaire en tête comme les autres bases. La pompe de piscine (`tasmota-pompe-piscine`, Sonoff S2X, `extends =
  env:tasmota`) n'est PAS rebasculée sans vérifier sa puce (`Status 2` / `Status 4`).
- [x] Créer son env, nommé `tasmota-cave-lumiere-porte` (et `tasmota-rdc-tv-salon` pour la .42) — preuve : cenv + sections `#elif defined(FIRMWARE_ESP8266_CAVE_LUMIERE_PORTE)` / `FIRMWARE_ESP8266_RDC_TV_SALON` du `.h` ; `build_envs.liste_envs` : IP .45 / .42 lues du `.h`, `fichiers_berry` et `fs_avec_firmware` faux ; Rule1 laissée dans la config de la carte (A11, A15). SANS Berry : `extends =
  env:tasmota-base-esp8285` (et non `tasmota32`), sans système de fichiers ni `custom_files_upload` ; section `#elif` du `.h` avec l'identité relevée sur la
  carte (IP .45, hôte, topic, client, template) ; nom et contenu validés par l'utilisateur. Dossier `data/cave/tasmota-lumiere-porte/` réduit à `config_decodee.json` (choix du 2026-11-12 ; ni
  persist, ni `autoexec.bat` : pas de FS sur 1 Mo). Classement par `lieux.py` : par l'IP .45 tant qu'il est sur le Wi-Fi
  maison (il y reste, décision du 2026-11-11).
- [x] Compilation par la page Build — preuve : journaux `20261112-045639-tasmota-cave-lumiere-porte-compiler.log` et `20261112-051515-tasmota-rdc-tv-salon-compiler.log`, SUCCESS, code 0 ; Flash 70,1 % (718 095 et 717 795 o sur 1 023 984), RAM 52,7 / 52,5 %, `.bin.gz` 514 Ko dans `build_output/firmware/`. Taille de l'image comparée aux 1 Mo (une mise à jour depuis 12.0.2 sur 1 Mo passe
  par `tasmota-minimal`, en deux temps : à ne faire qu'avec l'accord de l'utilisateur, la carte en service n'en a pas besoin).
- [x] Relever le sens retour côté serveur — preuve : lecture du code le 2026-11-12. `cmnd/cave/serveur-rly-cave/POWER3` est une commande
  Tasmota native (pas de Berry) : elle commute le relais 3 « LED Machines » (TCA9554) de la carte au topic `cave/serveur-rly-cave`. À chaque
  changement d'état de ce relais, `controleGeneral.be` (boucle `publishMQTT`) publie `cmnd/cave/lumiere/POWER1 ON|OFF` vers le Sonoff :
  entrée `relai1` du persist de la S3 (`data/cave/tasmota32s3-serveur-rly/_persist.json`) et de l'ancienne carte en service
  (`data/cave/tasmota32-serveur-rly-sauvegarde/_persist.json`). Pendant les essais, la S3 a le topic `…-v2` : la Rule1 du Sonoff ne
  joint que l'ancienne carte, la S3 lui envoie quand même `POWER1`. Boucle d'écho possible des deux côtés : A11.
  Relever le sens retour côté serveur : ce que la cave S3 (et l'ancienne carte en service) fait de
  `cmnd/cave/serveur-rly-cave/POWER3`, et ce qu'elle envoie au Sonoff (`cave/lumiere`).
- [ ] Réglages du Sonoff par `Backlog` et `Rule` en console seulement (pas d'`autoexec.bat` possible), proposés puis
  validés par l'utilisateur ; garder de la place dans Rule1 (242 car. libres) ou passer à Rule2.
  Décisions de l'utilisateur (2026-11-12) : (1) minuterie annulée à la fermeture de la porte (`RuleTimer1 0`), sinon une
  lumière rallumée au bouton dans les 15 min s'éteignait seule ; (2) lien avec le serveur par le groupe `tasmotas/cave` et le
  garde-fou de A11 (`Event lumPorte` / `lumSrv`, `Var1`), à la place des envois directs à `POWER3` ; (3) messages de la porte
  sur un seul topic `stat/cave/porte/RESULT`, `{"SWITCH":"ON"}` porte ouverte (`Switch2` = 1), `"OFF"` fermée (avant :
  `SENSOR` d'un côté, `RESULT` de l'autre, valeurs inversées) ; (4) `stat/cave/lumiere/RESULT {"POWER":…}` CONSERVÉ.
  Rule1 = comportement local (bouton, porte, minuterie), Rule2 = état de la lumière et lien au serveur (322 et 317 car.).
  Texte exact : `USER_RULE1` / `USER_RULE2` de la section `FIRMWARE_ESP8266_CAVE_LUMIERE_PORTE` du `.h`, posées par Tasmota à
  chaque remise à zéro de la config (`settings.ino::SettingsDefaultSet3`), avec `Rule1 1; Rule2 1` dans `USER_BACKLOG`.
  Tous les déclencheurs vrais d'une même Rule s'exécutent (`xdrv_10_rules.ino::RuleSetProcess`, seul `BREAK` arrête).
  Chaque carte reçoit aussi son propre `Event` du groupe, sans règle chez elle, donc sans effet ; pendant les essais,
  l'ancienne carte ET la S3 sont dans le groupe : les deux suivent la porte.
  Ordre : côté serveur d'abord (A11 : Rule `Event#lumPorte`, `publishMQTT` retiré), sinon la lumière du serveur ne suit
  plus. `Var1` vide au démarrage vaut 0 dans la comparaison : le premier `OFF` après un redémarrage n'est pas renvoyé.
  `%VAR1%` dans un déclencheur : lu dans `xdrv_10_rules.ino::RulesRuleMatch` (code actuel), à vérifier sur la 12.0.2 (A11).
  Envoi à la carte en service : en console (`Rule1 …`, `Rule2 …`, `Rule2 1`), avec l'accord de l'utilisateur, sans `Restart`.
  Écrit dans le `.h` le 2026-11-12 (`USER_RULE1` 322 car., `USER_RULE2` 317 car.) ; reste l'envoi en console, après le serveur.

## A9 — Écran Waveshare 7B pour le serveur relais de la cave
Contrainte matérielle : le 7B (ESP32-S3-Touch-LCD-7B) est une carte complète, avec son propre S3 et une dalle RGB
parallèle (une vingtaine de broches). La 8DI-8RO de la cave n'a que GPIO21 et GPIO48 de libres : elle ne peut pas piloter
cette dalle. « L'écran sur le serveur de la cave » veut donc dire un 7B posé à côté du serveur, avec son propre env,
qui affiche et commande ce que porte le serveur (relais, lumières, température, pompe).
- [x] Faire trancher par l'utilisateur le lien entre le 7B et le serveur de la cave. Proposition de Claude : esclave du — preuve : décision de l'utilisateur du 2026-11-12 = ModBus par RS485 ET range extender (UDP) ; rôles selon l'avis de Claude (serveur maître, écran esclave id 1 réservé inactif) consigné dans `PROTOCOLE_MODBUS.md` §10 ; persist, cenv (`${berry_commun.modbus}`) et autoexec de la cave S3 mis à jour ; `banc_demarrage.py` : seule la cave diffère (CONTROLE_MODBUS, ModbusReceivedUDP, ReglageModbus), instantané à réenregistrer
  range extender de la cave (A10, Wi-Fi sur son point d'accès) avec la pile Berry d'esclave (ModBus UDP, push, `ImAlive`),
  comme les débits mais dans l'autre sens (là-bas, l'écran est le maître). Autres voies : ModBus série sur le RS485 17/18
  de la cave (le 7B a un RS485 sur 16/15), ou MQTT seul.
- [x] Env du 7B (proposition : `tasmota32s3-cave-ecran`, dossier `data/cave/tasmota32s3-ecran`) créé à partir de — preuve : `fichiers_berry_creation.cree` le 2026-11-12 à 11:00 (sauvegarde `20261112-110026-632465-creation`), puis rôle d'esclave posé ; `verifie_berry.py` 0 erreur, `genere_schema_persist.py --valide` 0 erreur, `test_interface_ecran.py` VERT
  `tasmota32s3-bureau-ecran-debits-pac` (même carte : expandeur I2C 0x24, `preinit.be`, `custom_interface_ecran`) ;
  identité validée par l'utilisateur, IP du range extender (0.0.0.0, adresse `<ipMaitre>:<8080 + id - 1>`).
  Fait : identité ECRAN-CAVE, topic `cave/ecran`, groupe `tasmotas/cave`, nom « Écran cave », IP 0.0.0.0. ESCLAVE :
  ModBus id 1 (RS485 GPIO 16/15 en « Série Rx/Tx » 3232/3200, et UDP), range extender id 1 client de
  SERVEUR-RLY-CAVE-GATEWAY (`.h` : passerelle 192.168.4.1, `STA_SSID1` = point d'accès de la cave, MAISON en secours),
  `ipMaitre` 192.168.0.243, découverte ON (`controleDiscovery` chargé : l'`ImAlive` alimente le `RoutageRangeExtender` du
  maître), `timerRebootSansWifi` 0. Retirés de la copie : le métier des débits (`modules.ecranDebits`, ses deux `.be`,
  `ecranHaspmota.be`, `ecranFonctions.be`, `pages.jsonl`, `graphiques.json`, police) et `custom_interface_ecran` du cenv,
  en attendant la maquette. Restent : `_persist.json`, `autoexec.be`, `display.ini`, `preinit.be` (propre au 7B).
  Bloc `modules.ecranCave` vide et OFF, réservé aux vues : sans aucun bloc dans `modules`,
  `configDevices.be::configDevices_configDevicesByRules` ne crée pas ses compteurs et `controleGeneral` tombe en
  `key_error switchs` (vu par `banc_demarrage.py --dossier data/cave/tasmota32s3-ecran --env tasmota32s3-cave-ecran` :
  ROUGE sans le bloc, VERT avec, 0 erreur).
  Côté cave, `TasmotaSlaveModBus1` « ECRAN-CAVE » (id 1) reste OFF : à passer à ON au flash de l'écran (décision de
  l'utilisateur), sinon le maître relève un esclave absent.
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
- [x] Passer `rangeExtender.AP.routeNAPT` à `ON` dans le `_persist.json` du dossier S3 (accord de l'utilisateur, diff
  montré), en reprenant les réglages du P4 du garage ; vérifier que la section du `.h` active aussi le NAPT
  (`USE_WIFI_RANGE_EXTENDER_NAPT` ou équivalent du P4). — preuve : `routeNAPT: "ON"` dans `data/cave/tasmota32s3-serveur-rly/_persist.json` (2026-11-12) ; `.h` : rien à ajouter, NAPT défini pour toute carte à `USE_WIFI_RANGE_EXTENDER` (`user_config_override.h`, bloc POST_PROCESS_COMPILE_OPTIONS)
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
ON Power1#State!=%var1% DO Backlog Var1 %value%; Publish cmnd/tasmotas/cave/Event lumPorte=%value% ENDON
Serveur de la cave (Rule1) :
ON Event#lumPorte DO Backlog Var1 %value%; Power3 %value% ENDON
ON Power3#State!=%var1% DO Backlog Var1 %value%; Publish cmnd/tasmotas/cave/Event lumSrv=%value% ENDON
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
- [x] Serveur de la cave : retirer le `publishMQTT` de `relais.relai1` du `_persist.json` du dossier S3 (sinon le Berry
  publie en double, hors garde-fou ; accord de l'utilisateur, diff montré) et poser la Rule1 ci-dessus par l'`autoexec.bat`
  de la carte (fichier du dossier S3, sans commande qui redémarre). Topic en vigueur : `cave/serveur-rly-cave-v2`
  pendant les essais en .243, `cave/serveur-rly-cave` après A7 (cette bascule remplace l'ancienne étape « prévoir la
  bascule au retour en production »).
  — preuve : `data/cave/tasmota32s3-serveur-rly/_persist.json` `"topic": []` (diff d'une ligne, `genere_schema_persist.py --valide`
  0 erreur) ; `data/cave/tasmota32s3-serveur-rly/autoexec.bat` (Rule1 `Event#lumPorte` / `Power3#State!=%var1%`, `Rule1 1`,
  aucun `Restart`). Compilation et buildfs de la S3 faits le 2026-11-12 par la page Build (journaux
  `20261112-075318-…-compiler.log` SUCCESS 10 842 s, Flash 86,5 %, `20261112-105412-…-buildfs.log` SUCCESS 247 s) ;
  `autoexec.bat` dans l'image (`build_fichiers.liste` : 1 009 o). Reste : envoi du FS à la S3 (A6/A7).
- [ ] Essai, avec preuve dans le sniffeur MQTT (:7100) : allumage depuis la porte, depuis la cave (bouton, puis écran si
  A9) et depuis la porte qui s'ouvre ; une seule publication par action, aucune en retour ; double appui rapide des deux
  côtés à la fois : pas d'oscillation.

## A12 — Visuel des volets sur la page d'accueil (toutes les cartes à volets)
Demande de l'utilisateur (2026-11-11) : sous les curseurs natifs des volets, une façade dessinée où le tablier de
chaque ouverture bouge EN DIRECT pendant la course, avec son pourcentage, pour voir à distance que le volet a obéi.
Maquettes validées (scratchpad de la conversation, serveur de maquettes) : grenier du RDC = maison à deux pans,
fenêtre de la cuisine à gauche, trappe au milieu (panneau qui se baisse face à nous), porte d'entrée à droite ;
garage (P4 et rideau, même porte) = toit à un seul pan légèrement incliné vers la droite, grande porte à lames ;
grenier du 2e étage = trappe de face sous le plafond, panneau puis échelle qui descend et repose sur un escalier en
bois fixe (gauche vers droite). Le curseur natif est déjà mis à jour à chaque rafraîchissement
(`xdrv_01_9_webserver.ino`, `eb('s27<n>').value=`) : le dessin le lit, sans requête de plus.
- [x] Spec écrite puis plan : code commun dans `data/fs` (accord de l'utilisateur nécessaire), description de la façade
  par carte dans le persist — preuve : spec `docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md`
  (commit ceae81a41, validée par l'utilisateur le 2026-11-11), plan `tasks/plans/visuel-reglage-volets.md`
- [ ] Réalisation, bancs, sondes, essais sur carte : par A14 (plan dédié)

## A13 — Réglage des durées de montée et de descente par les boutons
Demande de l'utilisateur (2026-11-11) : `tempsMontee` / `tempsDescente` se règlent aujourd'hui à la main dans le
persist (réappliqués à chaque démarrage par `vrFonctions_configVRByJson`). Il faut un mode de réglage simple, pour
TOUS les volets, avec les boutons existants : simple appui pour les volets à un seul bouton ; appui sur l'un ou
l'autre bouton pour les volets à deux boutons ; ou les boutons de la page web. Pas de réglage par les butées (fins
de course, inclinomètre) : idée abandonnée par l'utilisateur. La durée mesurée est écrite dans le persist.
  Déroulé validé par l'utilisateur (2026-11-11) : (1) volet amené en butée basse ; (2) page « Configuration » ->
  réglage des volets : choix du volet, « Régler les durées » ; la course autorisée est allongée provisoirement (120 s) ;
  (3) un appui sur l'un de ses boutons (bouton unique, l'un des deux, ou ▲ de la page) : le volet monte, chronomètre
  lancé ; (4) un appui à l'arrivée en haut : arrêt, `tempsMontee` retenu ; (5) idem en descente -> `tempsDescente` ;
  (6) durées écrites dans le persist, durées normales remises, sortie du mode, résultat affiché. Garde-fous validés :
  sans second appui avant la course maximale, arrêt et rien n'est enregistré ; bouton « Annuler » qui sort sans rien
  changer. Les explications pas à pas destinées à l'utilisateur doivent figurer SUR la page de réglage.
- [x] Concevoir avec l'utilisateur : entrée et sortie du mode, déroulé d'une mesure, retour visible, garde-fous — preuve : déroulé et garde-fous ci-dessus, validés par l'utilisateur le 2026-11-11
- [x] Spec et plan — preuve : même spec et même plan que A12
- [ ] Réalisation, bancs, essais sur carte : par A14 (plan dédié)

## A14 — Réaliser le visuel et le réglage des durées (plan dédié `visuel-reglage-volets`)
Le travail d'A12 et d'A13 se suit dans `tasks/plans/visuel-reglage-volets.md`. Sa dernière action ramène ici.
- [ ] Taper `/suivi suivre visuel-reglage-volets` et exécuter ce plan de A1 à sa dernière action
- [ ] Plan `visuel-reglage-volets` clos (100 %, `statut: clos`), puis retour ici : cocher les étapes restantes d'A12 et d'A13

## A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais
Demande de l'utilisateur (2026-11-12) : réunir ici toutes les questions posées sur ces processeurs pour ne rien oublier.
Modules : porte de la cave (.45, ESP8285, 12.0.2, `tasmota-cave-lumiere-porte`) et TV du salon (.42, ESP8266EX, 13.1.0,
`tasmota-rdc-tv-salon`). Pas de système de fichiers : ni Berry, ni persist, ni `autoexec.bat`, ni discovery Berry.
- [x] Envs créés (2026-11-12) — preuve : `test_build_envs.py` VERT, `test_lieux.py` VERT, lieux `cave` / `rdc` par le nom ; `ota_possible` faux comme la piscine ; base `tasmota-base-1M` (`extends = env:tasmota`, carte `esp8266_1M` de `[common]`, déjà 1 Mo DOUT sans FS ;
  cible « Pont série » chargée directement comme la piscine), les deux envs, et leur section `#elif` du `.h` (identité de
  `config_decodee.json` : IP, hôte, topic, client, groupe, FriendlyName, DeviceName ; template « Contacteur Cave » BASE 2
  pour .45, module Sonoff Basic pour .42). Hors build en cours (cenv et `.h`). `test_build_envs.py`, `test_lieux.py`.
- [ ] Aucun fichier de FS ajouté à la compilation ni à l'envoi (demande de l'utilisateur) : pas de pré-script ni de
  `post_esp32.py` (ESP32 seulement), pas de `custom_files_upload`, `build_envs.py::_fs_avec_firmware` faux. À constater
  dans le journal de la 1re compilation (pas de `littlefs.bin` : constaté le 2026-11-12, 0 ligne `littlefs.bin`/`mklittlefs`/`post_esp32` dans les deux journaux ; reste la page) et dans la page Build (actions FS grisées ou refusées
  pour ces envs ? sinon à corriger).
- [ ] `config_decodee.json` est dans le dossier de la carte (choix de l'utilisateur) : il ne doit jamais partir en flash.
  Vrai tant que ces envs n'ont pas de FS ; à revoir si un env ESP8266 à FS apparaît.
- [ ] Taille de l'image comparée au 1 Mo ; mise à jour en OTA (tasmota.bin ~620 Ko ne tient pas à côté de l'ancien) :
  `tasmota-minimal` puis l'image, ou le port série. Comportement de la page Build en OTA pour ces envs (OTA grisée pour
  les ESP8266 amont : et pour les nôtres ?). Rien de flashé sans l'accord de l'utilisateur.
- [x] `CFG_HOLDER` — preuve : 2026-11-12, cartes à 4617 (défaut amont), envs à 1608 (`.h`, bloc `CFG_HOLDER == 4617`) : le 1er
  flash remet la config à zéro, puis Tasmota repose l'identité, les Rules de la porte et les timers de la TV (`USER_RULE1/2`,
  `USER_BACKLOG`). Une restauration par l'onglet tient : `settings.ino::SettingsConfigRestore` ne recopie pas les 16 premiers
  octets (le `cfg_holder` du firmware reste). La sauvegarde « avant flash » couvre un envoi COM de tout env
  (`build_serie.py::_sauve_drvset`). Sauvegardes manuelles prises par l'onglet (HTTP) : `20261112-054550_manuelle.dmp` (.45),
  `20261112-054552_manuelle.dmp` (.42).
  `CFG_HOLDER` : un firmware compilé ici remet la config aux valeurs du `.h` (Rules effacées). Avant tout flash,
  sauvegarde par l'onglet (« Sauvegarder maintenant », HTTP), restauration après ; vérifier si la sauvegarde
  « avant flash » de la page couvre un ESP8266.
- [x] Onglet « Sauvegarde configuration » : HTTP seul, textes à l'indice ESP8266 — preuve : A8 (banc et sonde verts).
- [x] Sauvegarde d'un ESP8266 : la carte en ligne est interrogée sur ce qui reste hors de Settings (demande de l'utilisateur,
  2026-11-12) — preuve : `outils_pc/build_sauvegarde_esp8266.py::controle` (`Status 2` firmware, `Ufs` FS, `Status 4` pilote
  Zigbee 23), appelé par `build_sauvegarde.py::prend`, rangé dans la fiche (`hors_config`), affiché dans la page et le journal
  avant flash ; Rules, timers, `Mem` sont dans le /dl (la `Rule1` de .45 lue par /cm revient même tronquée) ;
  `test_build_sauvegarde.py` VERT (9 cas ESP8266), sonde `test_build_page_sauvegarde_chrome.py` VERTE ; essai réel en
  lecture seule : .45 (12.0.2 ESP8285) et .42 (13.1.0 ESP8266EX), rien hors configuration.
- [ ] Essai réel sur .45 puis .42, avec l'accord de l'utilisateur : sauvegarde, copie modifiée (un texte, une Rule),
  comparaison, restauration, relecture des écarts. Les Rules (`rules` du JSON) s'éditent-elles par la copie ?
- [ ] Classement par lieu des messages : `lieux.py::identites` ne lit que les persists ; sans persist, ces cartes ne sont
  rangées que par le nom d'env. Hôte `PORTE-CAVE`/`TV`, topic `cave/lumiere`/`salon/tv` et IP à lire dans le `.h` (ou dans
  `config_decodee.json`) pour le syslog (:7200) et le sniffeur MQTT (:7100).
- [ ] Lien avec les autres cartes : MQTT et Rules seulement (A11 pour la porte) ; la discovery Berry est impossible.
- [ ] Timers de la TV (demande de l'utilisateur, 2026-11-12 : « il faut sauvegarder les timers ») : 1 à 9 armés, tous les
  jours, `POWER` OFF à 00:00, 00:30 … 04:00 ; 10 à 12 désarmés (non repris). Dans la sauvegarde de l'onglet ET dans le
  `USER_BACKLOG` de la section TV (`Timers 1; Timer1 {…}` … `Timer9`). À vérifier après le 1er flash : `Timers` en console.
  Écrit dans le `.h` le 2026-11-12 (`USER_BACKLOG` de 772 car.) ; la sauvegarde de l'onglet les contient déjà.
- [ ] Langue (anglais aujourd'hui) et version : passer en français et à jour ? Décision de l'utilisateur, taille à vérifier.

## A16 — Pompe de la piscine (192.168.0.40) : sauvegarde, env, mise en service
Demande de l'utilisateur (2026-11-12). Ce que le dépôt sait : un env `tasmota-pompe-piscine` existe (cenv, « LOCALISATION :
JARDIN », `extends = env:tasmota`, cible « Pont série ») avec sa section `FIRMWARE_ESP8266_POMPE_PISCINE` du `.h`, mais ni dossier
dans `data/`, ni `config_decodee.json`, ni sauvegarde ; `lieux.py::EXCEPTIONS` la range en `exterieur`.
Relevé du 2026-11-12, en lecture seule : syslog (`%TEMP%/syslog_tasmota.log`, 77 lignes) : hôte `POMPE-PISCINE`, topic
`jardin/pompe_piscine`, Heap 23 Ko (ESP8266), `Sleep 50` dynamique, Wi-Fi par le répéteur « Relai Wifi 2.4G KuWFi »
(BSSID 44:D1:FA:88:0B:6C, signal -70 dBm), firmware en français, émulation active (`UPP: Multicast (re)joint` : Wemo/Hue,
Alexa probablement) ; dernier message le 2026-11-10 à 08:08 (41 jours de marche), `POWER` OFF. Ce jour : HTTP muet sur .40,
LWT `tele/jardin/pompe_piscine/LWT` = `Offline` (retenu), ping d'abord répondu puis `Unreachable` : carte éteinte pour l'hiver ?
Défauts déjà visibles dans la section du `.h` : `#define USE_MQTT_TLS` alors que son commentaire dit « désactivé » (TLS
compilé, image plus grosse sur 1 Mo) ; `MODULE 1` (Sonoff Basic) sous des commentaires « Sonoff S26 / S2X / S20 » ; modèles
P4 commentés recopiés d'une autre section ; ni `MQTT_TOPIC`, ni `MQTT_CLIENT_ID`, ni `MQTT_GRPTOPIC`, ni `FRIENDLY_NAME`, ni
`USER_BACKLOG` (Hostname, émulation, timers). Après une remise à zéro de la config (1er flash, `CFG_HOLDER` 1608), la carte
chercherait les réseaux Wi-Fi du `.h`, pas le répéteur : elle serait perdue si la maison ne la couvre pas.
- [ ] Faire dire par l'utilisateur pourquoi la carte est muette (éteinte pour l'hiver, prise coupée, répéteur KuWFi
  éteint ?) et la faire rallumer ; contrôle : `Status 0` en HTTP sur .40, LWT `Online`.
  Réponse de l'utilisateur (2026-11-12) : répéteur KuWFi éteint. Reste : répéteur rallumé, carte de retour.
- [x] Processeur confirmé : ESP8266EX, pas un ESP32 — preuve : relevé HTTP en lecture seule du 2026-11-12 à 09:03 (répéteur
  rallumé) : `Status 2` `"Hardware":"ESP8266EX"`, `"Version":"15.5.0(release-tasmota)"` (binaire officiel, `OtaUrl`
  `tasmota-FR.bin`) ; `Status 4` flash 1 Mo, programme 652 Ko ; `Module` 8 « Sonoff S2X » (template Generic BASE 18, GPIO
  tous à 1) ; `Emulation` 1 (Belkin WeMo) ; `PowerOnState` 3 ; groupe `tasmotas/jardin` ; DeviceName et FriendlyName
  « Pompe de piscine » ; Timer1 08:00 ON et Timer2 20:00 OFF tous les jours, DÉSARMÉS, `Timers` ON ; Rules vides ; serveur
  web actif (Admin). Le `MODULE 1` du `.h` est faux (8 sur la carte). Nom `tasmota32-` à revoir avec l'utilisateur.
- [x] Nom revu avec l'utilisateur puisque la carte est un ESP8266 — preuve : réponses du 2026-11-12,
  « `tasmota-jardin-pompe-piscine` ==> OK » et « « Jardin » le remplace ==> OK » : base `tasmota-base-1M`, section
  `FIRMWARE_ESP8266_JARDIN_POMPE_PISCINE`, dossier `data/jardin/tasmota-pompe-piscine/`, lieu `("jardin", "Jardin")` à la
  place de `("exterieur", "Extérieur")` dans `lieux.LIEUX`, exception de la pompe retirée de `lieux.EXCEPTIONS`.
- [ ] Sauvegarde par l'onglet « Sauvegarde configuration » (HTTP ; MQTT masqué pour un ESP8266), page Build redémarrée
  avant pour charger le contrôle hors configuration (A15) : fiche avec firmware, FS et Zigbee ; `.dmp` dans
  `outils_docs/sauvegardes_cartes/tasmota-pompe-piscine/`, ignoré par git.
- [ ] Relevé de la carte en lecture seule : `Status 0`, `Template`, `Module`, `GPIO`, `Timers`, `Rule1` à `Rule3`, `Emulation`,
  `SetOption` utiles, `Status 2` (version, ESP8266EX ou ESP8285), `Status 4` (taille de flash : 1 Mo ?) ; `.dmp` décodé en
  `config_decodee.json` (mots de passe masqués), comme .42 et .45. Matériel réel (S20, S26, Basic, autre) vu sur le relevé.
- [x] Dossier de la carte et nom de l'env, décision de l'utilisateur — preuve : réponse du 2026-11-12, « on le renomme en
  `tasmota32-jardin-pompe-piscine`, avec un dossier `data/jardin/` ».
- [x] Renommage : env `tasmota-jardin-pompe-piscine` dans le cenv, `#elif` du `.h`
  (`FIRMWARE_ESP8266_JARDIN_POMPE_PISCINE`), dossier `data/jardin/tasmota-pompe-piscine/` (convention
  `transform_name`), ligne `jardin` dans `lieux.LIEUX` si absente, exception `tasmota-pompe-piscine` retirée de
  `lieux.py::EXCEPTIONS` ; `default_envs` de `platformio_override.ini` relu ; hors build en cours ; `test_lieux.py`,
  `test_build_envs.py`.
  — preuve : 2026-11-12, cenv `[env:tasmota-jardin-pompe-piscine]` (`extends = env:tasmota-base-1M`), `.h`
  `#elif defined(FIRMWARE_ESP8266_JARDIN_POMPE_PISCINE)`, `lieux.LIEUX` `("jardin", "Jardin")`, `EXCEPTIONS` vide ;
  `test_lieux.py`, `test_build_envs.py`, `test_lieux_js.mjs`, sonde `test_build_page_lieux_chrome.py` VERTS ;
  `platformio_override.ini` ne citait pas l'env. Dossier `data/jardin/tasmota-pompe-piscine/` créé avec le relevé.
- [ ] Env aligné sur les deux Sonoff (A15) : `extends = env:tasmota-base-1M` ; section du `.h` récrite d'après le relevé et
  avec l'accord de l'utilisateur (diff montré) : `USE_MQTT_TLS` retiré, `MODULE` ou `USER_TEMPLATE` du vrai matériel,
  topic, client, groupe, FriendlyName, `USER_BACKLOG` (Hostname, émulation, timers de la pompe, comme ceux de la TV),
  Rules éventuelles en `USER_RULE1/2`. Accès Wi-Fi par le répéteur : à reprendre de la sauvegarde (restauration) ou à poser
  dans le `.h` ; mot de passe jamais affiché ni commité hors des fichiers que l'utilisateur commite lui-même.
- [ ] Compilation par la page Build (:7700), SUCCESS lu en fin de journal, taille de l'image comparée au 1 Mo (les deux
  Sonoff : 718 Ko) ; mise à jour en OTA par `tasmota-minimal` si l'image ne tient pas à côté de l'ancienne (A15).
- [ ] Recenser ce qui vise `jardin/pompe_piscine` (Node-RED du Pi, Alexa par l'émulation, Home Assistant, Telegram) avant
  tout changement de topic, d'hôte ou d'émulation.
- [ ] Mise en service, avec l'accord de l'utilisateur : sauvegarde « avant flash », envoi, `Status 0`, timers et Rules relus,
  pompe commandée une fois (`Power` ON puis OFF) ; restauration de la sauvegarde si un réglage manque.

## A17 — Projecteur du jardin (192.168.0.41) : sauvegarde, env, mise en service
Demande de l'utilisateur (2026-11-12) : « fais la même chose pour le projecteur de jardin ». Aucun env, aucune section du
`.h`, aucun dossier dans `data/` pour cette carte. Relevé HTTP en lecture seule du 2026-11-12 à 09:28 :
`PROJECTEUR-JARDIN`, topic `jardin/projecteur_led`, groupe `tasmotas/jardin`, DeviceName « Projecteur de jardin »,
FriendlyName « Tasmota » (jamais réglé) ; ESP32-U4WDH-D rev.3, flash 4 Mo, Heap 101 Ko, sans PSRAM ; Tasmota 13.1.0
officiel (`OtaUrl` `tasmota32.bin`, `CfgHolder` 4617) ; template « NOUS B2T » (BASE 1, relais, bouton, interrupteur, mesure
d'énergie : `ENERGY` dans `Status 8`, 0,021 kWh depuis le 2026-07-18) ; `PowerOnState` 3, `SetOption0` ON ; Rules vides,
timers désarmés (`Timers` OFF), émulation 0 ; FS de 320 Ko (`Ufs` type 3) : `/.settings`, `/.settings.lkg`, `/.drvset003`,
`/_persist.json`. Le `/dl` d'un ESP32 porte Settings et les `.drvset*`, PAS `/_persist.json` : à récupérer à part.
Balayage du réseau du même jour (HTTP `/` et `Status 0` sur 192.168.0.1 à 254, LWT retenus du broker) : Tasmota en .40
(pompe), .41 (projecteur), .42 (TV), .45 (porte de la cave), .48 (`SERVEUR-RLY-CAVE`, ESP32-D0WD-V3, 13.3.0.3), .49
(différentiel du bureau, 16.0.0.2) ; LWT `Offline` : `etage2/grenier`, `garage`, `garage/rideau`, `jardin/cuve`,
`volet/entree` (Sonoff Dual R3 .46, A3) et `cave/serveur-rly-cave-v2` (pas encore en service).
Relevé complet du 2026-11-12 (demandes de l'utilisateur : « l'analyser totalement car il gère l'énergie », broches et
infos par l'interface web « comme pour le différentiel », persist et fichier de configuration), tout en lecture seule,
copies dans le scratchpad de la conversation (`nous_*.html`, `nous_persist.json`, `nous_config.dmp`,
`nous_config_decodee.json` masqué) :
  - broches du template (page `/md`, codes décodés par la liste de la page) : GPIO0 LedLink (544), GPIO1 Serial Tx (3200),
    GPIO3 BL0942 Rx (8160), GPIO4 Button1 (32), GPIO5 Switch1 (160), GPIO12 Relay1 (224) ; même schéma que le différentiel
    (BL0942 sur liaison série) ; console série prise par la BL0942 ; autres GPIO libres (2, 9, 10, 15 à 17, 19, 21 à 23,
    25 à 27, 32 à 34, 36, 39) ;
  - `/_persist.json` de la carte : `{}` (vide, aucune valeur personnalisée) ;
  - configuration (`/dl`, 4 496 o = Settings + `/.drvset003`, décodée par decode-config) : MQTT `192.168.0.5:1883`, client
    `PROJECTEUR-JARDIN`, Wi-Fi « Relai Wifi 2.4G KuWFi » et « Repeteur Wifi 2.4G KuWFi » (le jardin dépend du répéteur),
    syslog `192.168.0.3` niveau 2, `TelePeriod` 300, `Sleep` 0, `TimeZone` 99, FriendlyName « Tasmota » (à corriger),
    calibrage énergie 12530 / 1950 / 3500 (puissance, tension, courant) dans la sauvegarde.
Demandes de l'utilisateur (2026-11-12) : firmware du dépôt avec persist personnalisé et fichiers Berry ; range extender et
discovery activés ; valeurs du persist reprises de l'interface web de la carte.
- [ ] Contrôle de faisabilité AVANT l'env : aucun ESP32 classique du dépôt ne compile `USE_WIFI_RANGE_EXTENDER` (S3 de la
  cave et du grenier du RDC seulement ; commenté dans la section du différentiel) ; le différentiel, même puce, avec le
  cadre Berry et la page `/energie`, n'a plus que 63 Ko de tas et 36 Ko libres sur son FS de 320 Ko. Mesurer la RAM d'un
  range extender NAPT sur ESP32 classique (`Status 4` après essai), choisir les modules Berry chargés, vérifier la taille
  de l'image (≤ 2 880 Ko) et du FS. Rôle du point d'accès à faire préciser : remplacer le répéteur KuWFi pour la pompe (.40,
  ESP8266 officiel, cliente du NOUS, joignable par `<ip NOUS>:<8080 + id - 1>`) ?
  Réponse de l'utilisateur (2026-11-12) : le point d'accès sert à se connecter DIRECTEMENT au NOUS avec le téléphone si le
  Wi-Fi de la maison ne marche plus. Donc point d'accès permanent SANS routage : `rangeExtender.AP.routeNAPT` = `OFF`
  (`RgxNAPT`, `rangeExtenderFonctions.be`), moins de RAM qu'un NAPT ; pas d'esclave derrière. À vérifier sur carte : page
  web du NOUS ouverte depuis le téléphone sur l'adresse du point d'accès, Wi-Fi de la maison coupé (box ou SSID absent).
  Alternative native à comparer : `WifiConfig 2` (gestionnaire Wi-Fi ouvert seulement quand le réseau est perdu ; limité à
  la page de configuration Wi-Fi, à vérifier dans `support_wifi.ino`).
- [x] Page `/energie` et enregistrement de la consommation sur cette carte — preuve : décision de l'utilisateur du
  2026-11-12, « Crée la page '/energie' mais sans activer les enregistrements » (la règle « pas d'enregistrement sur ESP32
  classique » est donc respectée).
- [ ] Clé `diverses.energie.enregistrement` (`ON` par défaut, absente = `ON` : le différentiel ne change pas) : à `OFF`,
  `controleEnergie.be::cycle` garde la courbe de 24 h en RAM (`notePuissance`, ~600 o, perdue au redémarrage) mais ne lit ni
  n'écrit rien en flash (`lisCourbe`, `releve`, `sauveCourbe` sautés) ; `energieFonctions.be::envoieDonnees` ajoute
  `"enregistrement"` ; `data/sd/js/energie.js` affiche « Enregistrement désactivé » au lieu de « Aucun relevé pour
  l'instant » ; clé ajoutée à `outils_docs/schemas/modele_persist.json`, schéma regénéré. Modules solidifiés : firmware du
  différentiel à recompiler aussi (comportement inchangé). Bancs `berry/banc_energie.py` (cas `OFF` : aucun fichier écrit,
  avec témoin) et `outils_pc/test_energie_rendu.mjs` ; `energieFonctions.be` passe au-delà de 598 lignes (exception du
  CLAUDE.md à mettre à jour). Écrit hors build en cours.
- [ ] Env du NOUS : liste `page_energie` retirée de son `custom_files_exclude`, `energieFonctions` et `controleEnergie` dans
  son `custom_berry_solidify`, `demarrage.charge(["controleEnergie"], "diverses.energie")` dans son autoexec, bloc
  `diverses.energie` (`activation` ON, `enregistrement` OFF, `calibrage` repris de la carte : 12530 / 1950 / 3500 à
  confirmer contre `/.drvset003`) ; `banc_demarrage.py`.
- [ ] Sauvegarde par l'onglet « Sauvegarde configuration » (HTTP), page Build redémarrée avant ; `/_persist.json` de la
  carte téléchargé à côté (`/ufsd?download=/_persist.json`, lecture seule) ; décider s'il faut étendre le contrôle hors
  configuration (`build_sauvegarde_esp8266.py`, A15) aux ESP32 sans dossier dans le dépôt, pour qu'il signale leurs fichiers.
- [ ] `.dmp` décodé en `config_decodee.json` (mots de passe masqués), comme .42 et .45 ; template « NOUS B2T » vérifié
  contre la base des modèles (bornes : relais, bouton, interrupteur, puce de mesure d'énergie).
- [ ] Nom, dossier et firmware, décision de l'utilisateur. Proposition de Claude : `tasmota32-jardin-projecteur-led`
  (convention `tasmota32-<lieu>-<nom>`), dossier `data/jardin/tasmota32-projecteur-led/`. Firmware à choisir : celui de
  l'amont (`tasmota32`, sans le cadre Berry du dépôt, comme aujourd'hui) ou le cadre du dépôt (persist, autoexec, logs
  par `logFonctions` ; pas d'historique : ESP32 classique). Lieu « Jardin » dans `lieux.LIEUX` (même question que A16).
  Firmware décidé le 2026-11-12 : cadre du dépôt (persist personnalisé, Berry, range extender, discovery). Nom accepté le
  2026-11-12 (« Pour son nom : OK ») : `tasmota32-jardin-projecteur-led`, dossier `data/jardin/tasmota32-projecteur-led/`.
- [ ] Env créé (cenv et section `#elif` du `.h`) d'après le relevé, avec l'accord de l'utilisateur (diff montré) : IP,
  hôte, topic, client, groupe, `USER_TEMPLATE` « NOUS B2T », FriendlyName, `USER_BACKLOG` ; calibrage de la mesure
  d'énergie gardé (`/.drvset003` sauvegardé et rétabli autour d'un flash série par `build_drvset.py`) ; hors build en cours.
- [ ] Compilation par la page Build (:7700), SUCCESS lu en fin de journal, taille comparée à la partition de 4 Mo.
- [ ] Recenser ce qui vise `jardin/projecteur_led` (Node-RED, Alexa, Home Assistant) avant tout changement d'identité.
- [ ] Mise en service, avec l'accord de l'utilisateur : sauvegarde « avant flash », envoi (OTA possible sur 4 Mo),
  `Status 0`, relais commandé une fois, mesure d'énergie relue ; restauration si un réglage manque.

## A18 — Projecteur du barbecue : copie de l'env du NOUS du jardin (A17)
Demande de l'utilisateur (2026-11-12) : « dupliquer le module NOUS pour un projecteur de barbecue » et proposer les
paramètres qui doivent changer. Aucune carte de ce nom sur le réseau (balayage du 2026-11-12, A17), rien dans le dépôt.
Se fait APRÈS A17 (env du NOUS créé et essayé), par la création d'env à partir d'une carte modèle (page « Fichiers Berry par
env », `fichiers_berry_creation.py` : identité remplacée, refus si IP, topic ou client déjà pris).
Proposition de Claude, paramètres qui CHANGENT (le reste est copié du NOUS du jardin) :
  - env `tasmota32-jardin-projecteur-barbecue`, `FIRMWARE_ESP32_JARDIN_PROJECTEUR_BARBECUE`, dossier
    `data/jardin/tasmota32-projecteur-barbecue/` ;
  - IP `192.168.0.44` (libre : le `.h` et les persists prennent .40, .42, .43, .45 à .49, .51, .243 ; .41 = NOUS du jardin) ;
    IP validée par l'utilisateur le 2026-11-12 (« IP: .44 »).
  - hôte et client MQTT `PROJECTEUR-BARBECUE`, topic `jardin/projecteur_barbecue`, DeviceName et FriendlyName
    « Projecteur de barbecue » ; groupe `tasmotas/jardin` GARDÉ (même lieu) ;
  - point d'accès de secours : SSID propre (`PROJECTEUR-BARBECUE-AP` par exemple), sinon le téléphone ne sait pas lequel
    des deux il rejoint ; mot de passe au choix de l'utilisateur, jamais affiché ;
  - calibrage de l'énergie (`diverses.energie.calibrage`, `/.drvset003`) : celui de CETTE carte, jamais celui du NOUS
    du jardin (chaque BL0942 a le sien) : relevé sur la carte avant le flash, ou calibrage à refaire ;
  - clés liées au matériel (MAC, s'il y en a dans le persist) retirées ou relevées sur la carte.
Paramètres GARDÉS : template « NOUS B2T » (si même matériel), page `/energie` sans enregistrement, discovery, range extender
sans NAPT, broker, syslog, `TelePeriod`, `PowerOnState`, modules Berry.
- [x] Liste validée par l'utilisateur — preuve : réponses du 2026-11-12, « IP: .44 », « environnement validé », « je viens
  juste de la commander », « c'est bien un NOUS B2T » : env, topic et SSID proposés retenus ; carte pas encore reçue.
- [ ] À la réception (firmware d'origine du vendeur, Tasmota ou Tuya ?) : connexion au point d'accès de la carte,
  relevé en lecture seule (comme A17 : `/md`, `/_persist.json`, `/dl` décodé) et sauvegarde par l'onglet AVANT tout flash ;
  calibrage relevé (OBLIGATOIRE, demande de l'utilisateur du 2026-11-12 : « il faudra prévoir une sauvegarde pour récupérer
  le calibrage » ; sur ESP32 il est dans `/.drvset003`, que le `/dl` contient et que `build_drvset.py` rétablit autour d'un
  flash série ; valeurs reportées dans `diverses.energie.calibrage` du persist). Sans Tasmota d'origine : flash série (adaptateur USB-série 3,3 V) et calibrage à refaire avec une
  charge connue (`PowerSet`, `VoltageSet`, `CurrentSet`).
- [ ] Env créé par copie du NOUS du jardin (diff montré, accord de l'utilisateur), hors build en cours ; `test_lieux.py`,
  `test_build_envs.py`, `banc_demarrage.py`.
- [ ] Compilation par la page Build, SUCCESS lu en fin de journal.
- [ ] Mise en service, avec l'accord de l'utilisateur : sauvegarde « avant flash », envoi, `Status 0`, relais commandé une
  fois, mesure d'énergie relue, point d'accès de secours vu depuis le téléphone.

## Améliorations restantes
- [ ] [projet] Ethernet W5500 de la carte du grenier du RDC (`ReglageGlobal VoieReseau ethernet`) si un câble arrive au grenier.
- [ ] [projet] Alias Berry lisible par volet (`VoletPorte`, `VoletCuisine`) si l'utilisateur le veut (A4).
- [ ] [projet] Resynchroniser les deux lampes de la cave à la reconnexion MQTT d'une des cartes (`Mqtt#Connected`).
  Aujourd'hui, un ordre perdu pendant une coupure du broker n'est jamais rattrapé.

## Vérification
`test_lieux.py`, `banc_demarrage.py`, `verifie_berry.py`, compilation par la page Build ; essais sur carte à la réception.
