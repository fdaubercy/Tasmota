---
chantier: rgx-ethernet-uplink
titre: PR amont Range Extender, Ethernet comme liaison montante (discussion arendst/Tasmota#25280)
statut: actif
cree: 2026-11-16
maj: 2026-11-26
source: compiled-sprouting-waffle.md
objectif: Faire démarrer l'AP du Range Extender quand seul l'Ethernet a une IP, en un PR propre accepté par arendst
famille: modbus-reseau
liens: alerte-firmware-c6
---
# PR amont : Range Extender avec Ethernet comme liaison montante

## Contexte
Discussion #25280 (ouverte le 15/11/2026 par fdaubercy). Theo (arendst) : « A PR is welcomed », bascule automatique acceptable,
commande `Rgx...` souhaitée pour désactiver cette bascule. Décision de l'utilisateur : **deux PR**.
- PR 1 (ce plan) : comportement automatique seul, aucun nouveau réglage, aucune commande.
- PR 2 (plan à part, après fusion du PR 1) : commande Rgx pour couper la bascule (touche `Settings`, à valider avec Theo).

Fichier visé : `tasmota/tasmota_xdrv_driver/xdrv_58_range_extender.ino` (C++ Arduino, ESP32 seulement pour la partie Ethernet).
**Branche propre** : worktree séparé issu de `upstream/development`, jamais depuis le `development` du fork. Le fork porte déjà
un correctif DNS IPv6 (lignes 409-418) absent de l'amont ; il ne doit PAS entrer dans le PR 1 (à proposer à part, ou plus tard).

Trois verrous dans le fichier amont (numéros de ligne du fork, à relire sur la base amont) :
1. `FUNC_EVERY_SECOND` (507, 520, 531) : l'AP ne démarre et n'est surveillée que si `Wifi.status == WL_CONNECTED`.
2. `rngxSetup` (403-408) : le DNS offert aux clients est lu sur `esp_netif_STA`.
3. `CmndRgxPortMap` (295) : l'adresse de passerelle est `WiFi.localIP()`.

Existant à réutiliser : `EthernetHasIPv4()` (`support_wifi.ino`, ~856), `EthernetHasIP()` et `ETH.localIP()` (`xdrv_82_esp32_ethernet.ino`),
garde `#if defined(ESP32) && defined(USE_ETHERNET)` déjà utilisée par `HasIP()` (`support_wifi.ino`, ~1155), `RgxApUp()` qui protège l'AP dans `WifiBegin`.

## A1 — Branche propre
- [x] Synchroniser le fork (`synchronise_fork_tasmota.py`, sur `development` propre) ou au minimum `git fetch upstream` — preuve : fetch fait, upstream/development = b83f8fa55 (16/11/2026), synchro du fork laissée à l'utilisateur
- [x] Créer un worktree `rgx-ethernet-uplink` depuis `upstream/development` (arbre de travail principal intact) — preuve : `git worktree add ../Tasmota-pr-rgx`, branche sur b83f8fa55, 0 occurrence de « Fork : DNS »
- [x] Relire le fichier amont : repérer les lignes exactes des trois verrous (elles diffèrent du fork) — preuve : amont lignes 295, 403-408, 497, 510, 521

## A2 — Code C++ (PR 1)
- [x] Ajouter un petit assistant `RgxUplinkUp()` (+ `RgxUplinkIP()`) — preuve : git diff du worktree, `EthernetHasIPv4()` déjà sans garde dans support_wifi.ino : `Wifi.status == WL_CONNECTED`, ou (ESP32 + `USE_ETHERNET`) `EthernetHasIPv4()` ; version ESP8266 = WiFi seul
- [x] `FUNC_EVERY_SECOND` : remplacer deux des trois `Wifi.status == WL_CONNECTED` par `RgxUplinkUp()` (le 3e, surveillance du mode avec redémarrage, reste Wi-Fi seul : risque de boucle de redémarrages) — preuve : git diff du worktree
- [ ] Mode Wi-Fi au démarrage : accepter `WIFI_STA` ou `WIFI_OFF` quand l'uplink est l'Ethernet (à confirmer par un log du mode sur carte)
- [x] `rngxSetup` : choisir le netif d'uplink (STA si connecté, sinon Ethernet via `esp_netif_get_handle_from_ifkey("ETH_DEF")`) pour lire le DNS
- [x] `CmndRgxPortMap` : passerelle = `RgxUplinkIP()` (WiFi.localIP() si STA connectée, sinon EthernetLocalIP()) — preuve : git diff du worktree
- [x] Station connectée : comportement strictement identique à avant (relecture du diff pour le prouver) — preuve : si Wifi.status est connecté, RgxUplinkUp() vrai, RgxUplinkIP() = WiFi.localIP(), netif = STA ; seul changement de branche : mode WIFI_OFF accepté en plus
- [x] Garde `#ifdef` : l'ESP8266 ne voit aucun symbole Ethernet — preuve : b2_tasmota-rgx.log SUCCESS, 0 erreur

## A3 — Vérifications
- [x] Compiler ESP32 avec `USE_WIFI_RANGE_EXTENDER` + `USE_ETHERNET` (+ NAPT), pour S3, P4 et ESP32 classique — preuve : journaux %TEMP%
gx2_*.log, SUCCESS : tasmota32s3-rgx flash 72,4 %, tasmota32p4-rgx flash 56,3 %, tasmota32-rgx flash 75,9 %
- [x] Compiler ESP32 sans Ethernet, et ESP8266 avec Range Extender (garde `#ifdef`) — preuve : b4_sans_eth.log SUCCESS (flash 74,0 %), firmware.map : EthernetInit 0, ETHClass 0, RgxUplinkUp 1 ; ESP8266 : b2 tasmota-rgx SUCCESS ; (la C3 ne convenait pas : Ethernet present)
- [x] Avant tout flash de la S3 : sauvegarde de la carte (page Build, onglet Sauvegarde configuration), envoi du firmware SANS effacement ; AP configuree par commandes Backlog RgxSSID/RgxPassword/RgxAddress/RgxSubnet/RgxState/RgxNAPT (valeurs fournies par l'utilisateur, jamais ecrites dans un fichier du worktree) — preuve : 17/11/2026, lecture complete de la flash par esptool (16 Mo, md5 4ecf4f01..., outils_docs/sauvegardes_cartes/tasmota32s3-rdc-grenier/, ignore par git) au lieu de la page Build (carte injoignable en reseau), puis write-flash app0 seule a 0xE0000, hash verifie, persist garde (Status 5 : hostname et IP inchanges)
- [ ] Essai carte 1 : S3 + W5500, câble branché, Wi-Fi STA non configuré ou hors de portée : l'AP s'ouvre, un esclave reçoit un bail DHCP avec le bon DNS
- [ ] Essai carte 2 : l'esclave sort sur Internet par le NAPT (ping, résolution DNS, MQTT)
- [ ] Essai carte 3 : `RgxPort` ajoute une redirection avec l'IP Ethernet
- [ ] Essai carte 4 : câble débranché puis rebranché, l'AP revient sans redémarrage inutile
- [ ] Essai carte 5 : Ethernet ET Wi-Fi connectés, route de sortie du NAPT notée (priorité STA 100 / ETH 50) ; aucune régression
- [ ] Noter la limite de double liaison dans le PR si le trafic sort par le Wi-Fi
- [ ] Essai ESP32-P4 (Ethernet interne RMII + PHY, Wi-Fi par le C6 esp-hosted) : repeter les essais 1 a 4 ; relever le mode Wi-Fi reel au demarrage (WIFI_OFF ou STA) et le DNS offert (IPv4 attendu, le P4 est en double pile)

## A4 — Préparation du PR
- [ ] Mettre à jour `CHANGELOG.md` (section « Changed ») et le commentaire d'en-tête du `.ino`
- [ ] Commits en anglais, sans trailer `Co-Authored-By`, un seul sujet
- [ ] Agent `controleur-secrets` sur le diff, lire son rapport
- [ ] Agent `preparateur-push` avant tout push
- [ ] Rédiger le texte du PR en anglais (+ traduction française), en citant #25280 ; skill `poste-message-github`

## A5 — Publication (uniquement sur accord explicite)
- [ ] Poster ce plan résumé dans la discussion #25280 (texte validé par l'utilisateur d'abord)
- [ ] Pousser la branche sur `origin` après « oui »
- [ ] Ouvrir le PR vers `arendst/Tasmota:development` après « oui »
- [ ] Suivre les réponses (skill `fils-github`) et répondre aux retours de relecture

## Améliorations restantes
- [ ] [projet] PR 2 : commande Rgx pour désactiver la bascule (demander à Theo où stocker le réglage : bit libre de `sbflag1` ou autre)
- [ ] [projet] Proposer à part le correctif DNS IPv6 du fork (lignes 409-418), avec un cas reproductible
- [ ] [projet] Épingler le NAPT sur l'Ethernet avec `esp_netif_set_default_netif` si l'essai 5 montre une sortie par le Wi-Fi

## Vérification
Banc de preuve = les essais A3 sur les cartes du garage, journaux `RGX:` lus par le syslog (:7200). Rien n'est coché sans sa preuve.
