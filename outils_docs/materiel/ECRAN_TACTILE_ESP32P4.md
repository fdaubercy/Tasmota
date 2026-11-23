# Écran tactile MIPI-DSI sur ESP32-P4 sous Tasmota

Recherche du 2026-11-11, menée pour l'écran du serveur du garage (maître ModBus P4). Rien n'a été compilé ni essayé
sur un écran : ce document rassemble des sources et des constats de code, pas des essais.

Question posée : brancher un écran tactile sur le P4 (connecteur MIPI-DSI du kit Waveshare), Tasmota le sait-il, et
existe-t-il des kits P4 avec écran et/ou relais ?

## 1. Ce que Tasmota sait faire (code de ce dépôt, fork à jour de l'amont au 2026-11-11)

- Pilote : uDisplay, interface `DSI` (`lib/lib_display/UDisplay/src/uDisplay_DSI_panel.cpp`, classe `DSIPanel`),
  compilé seulement si `SOC_MIPI_DSI_SUPPORTED` (P4). L'en-tête `uDisplay_DSI_panel.h` porte encore
  « WIP - NOT REALLY IMPLEMENTED!!! », mais deux descriptions d'écran l'utilisent. LVGL et HASPmota s'y posent.
- Descriptions existantes (`tasmota/displaydesc/`) : `EK79007_P4ev_DSI.ini` (carte Espressif P4 Function-EV,
  1024x600) et `JD9165_DSI.ini` (1024x600, cartes Guition). Toutes deux avec tactile GT911 en 0x5D, par script
  (`:UTI`, `:UTT`, `:UTX`, `:UTY`). Aucune pour ILI9881C, JD9365, HX8394 (dalles Waveshare vendues seules).
- Ligne `:H` d'un écran DSI : nom, largeur, hauteur, bpp, `DSI`, voies, TE, rétro-éclairage, reset, canal LDO, mV LDO,
  horloge pixel, débit des voies (Mbps), ordre RGB, endian. `:V` = hfp, vfp, hbp, hsw, vsw, vbp. Alimentation du PHY
  DSI : LDO canal 3 à 2500 mV (commande `Ldo<n>` ajoutée par #25128).
- Doc : https://tasmota.github.io/docs/Universal-Display-Driver/ cite `DSI` et l'option `:B,<lignes>,32` « pour les
  écrans MIPI-DSI haute résolution du P4 », sans exemple. https://tasmota.github.io/docs/ESP32/ : support P4
  « qui commence à peine ».
- **Nos envs P4 ne compilent pas l'affichage.** `USE_LVGL` et `USE_UNIVERSAL_DISPLAY` ne sont définis que sous
  `FIRMWARE_LVGL` (`tasmota/include/tasmota_configurations_ESP32.h`) ; dans `platformio_tasmota_cenv.ini`, seul
  `tasmota32s3-base-N16R8` pose `-D FIRMWARE_LVGL`. `tasmota32p4-garage-serveur-modbus` (via `tasmota32p4-base-devkit`)
  ne l'a pas : à ajouter pour un écran.

## 2. Retour d'expérience : discussion arendst/Tasmota #24448

https://github.com/arendst/Tasmota/discussions/24448 « Tasmota on ESP32-P4 with MIPI-DSI: performance notes +
sdkconfig/LVGL tips » (ouverte le 2026-02-13, réponses du 2026-08-09, dont s-hadinger qui n'a pas de P4).

- Cartes essayées : Guition à dalle MIPI-DSI ; puis un 1024x600 (LesNewell).
- `custom_sdkconfig` proposé : `CONFIG_COMPILER_OPTIMIZATION_PERF=y` (+ correctif de l'éditeur de liens avec
  framework 3.3.6), `CONFIG_LCD_DSI_ISR_IRAM_SAFE=y` et `CONFIG_LCD_DSI_ISR_CACHE_SAFE=y` (« crucial » contre les
  artefacts pendant les écritures en flash), `CONFIG_CACHE_L2_CACHE_128KB=y` (~128 Ko de RAM interne rendus), ISR
  tactile/I2C en IRAM. Second avis : l'effet des réglages sdkconfig est peu sensible à l'usage.
- **Piège principal : la RAM interne.** En 1024x600, ~57 Ko libres sans page ni script, ~42 Ko avec des scripts Berry
  et un `pages.jsonl` conséquent : plantages intermittents, d'abord pendant un envoi de fichiers. Sous ~50 Ko libres,
  risque de plantage. `:B,60,01` -> `:B,34,01` rend ~50 Ko, au prix de rafraîchissements plus lents.
- Solution trouvée : tampons LVGL en PSRAM **et** `:B,<hauteur>,01` (ex. `:B,600,01`) : ~120 Ko de RAM interne
  rendus, défilement fluide (diff joint à la discussion). Exige le correctif de `DSIPanel::pushColors` publié dans la
  discussion (attendre la fin du DMA précédent : réessai sur `ESP_ERR_INVALID_STATE`), sinon bandes non mises à jour.
  Le correctif de `pushColors` est DÉJÀ dans l'amont (`uDisplay_DSI_panel.cpp::DSIPanel::pushColors`, réessai jusqu'à
  300 fois) ; le passage des tampons LVGL en PSRAM n'a pas été vérifié dans le code (à regarder avant un essai).
- Bluetooth gourmand en mémoire : le couper aide. Réglages LVGL suggérés (`tasmota_lv_conf.h`) :
  `LV_DRAW_LAYER_SIMPLE_BUF_SIZE`, `LV_IMG_CACHE_DEF_SIZE_PSRAM`, `LV_OBJ_STYLE_CACHE`.

Pour nous : le maître P4 porte déjà ModBus, UDP, Range Extender et beaucoup de Berry. Un écran 1024x600 dessus
demande de mesurer la RAM interne libre (`BRY: GC`, `Status 4`) avant de conclure.

## 3. Carte retenue en piste : Waveshare ESP32-P4-WIFI6-Touch-LCD-7B

Doc : https://docs.waveshare.com/ESP32-P4-WIFI6-Touch-LCD-7B ; exemples :
https://github.com/waveshareteam/ESP32-P4-WIFI6-Touch-LCD-7B ; schéma :
https://files.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-7B/ESP32-P4-WIFI6-Touch-LCD-7B.pdf. SKU 32510 et 32511.

Ne pas confondre avec l'**ESP32-S3**-Touch-LCD-7B (écran RGB, fiche `WAVESHARE_ESP32-S3-Touch-LCD-7B.md` du dossier
de l'écran des débits) : même taille, autre puce, autre interface.

- ESP32-P4NRW32X, 32 Mo PSRAM, 32 Mo flash ; Wi-Fi 6 et BLE par ESP32-C6-MINI-1 en SDIO (même schéma que notre kit :
  surveiller la version du C6, voir le blocage 2.6.6 du P4 du garage).
- Écran 7" 1024x600 paysage, MIPI-DSI 2 voies. Contrôleur : **EK79007** (lu dans
  `examples/arduino/libraries/displays/displays_config.h` du dépôt Waveshare, profil tiré du BSP
  `waveshare/esp32_p4_wifi6_touch_lcd_7b` 3.0.1). Tactile **GT911** en 0x5D, sans broche reset ni interruption.
- RS485 sur connecteur PH2.0 4 broches : TX GPIO27, RX GPIO26 (exemple `11_RS485_Echo`) ; puce et gestion du sens
  non lues (voir le schéma). CAN, I2C, UART en PH2.0 ; 17 GPIO sur 2 x 12 broches.
- Audio ES8311 + ES7210, deux micros, sortie haut-parleur ; caméra MIPI-CSI ; carte TF ; USB OTG HS.
- Alimentation par USB-C (tension d'entrée non indiquée) ; Ethernet non indiqué ; prix non relevé.

**Écart avec `EK79007_P4ev_DSI.ini`** : la séquence `:I` (B2, 80 à 86, 11) et les timings `:V,160,12,160,10,1,23`
sont identiques au profil Waveshare. Diffèrent :

| Champ | `EK79007_P4ev_DSI.ini` | 7B (profil Waveshare) |
|---|---|---|
| Rétro-éclairage | GPIO26 | GPIO32, **actif à l'état bas** (LEDC 5 kHz inversé) |
| Reset de la dalle | GPIO27 | GPIO33 |
| Débit des voies | 900 Mbps | 1000 Mbps |
| I2C du tactile | bus 1 (broches non fixées) | SDA GPIO7, SCL GPIO8, 100 kHz |

Une description 7B serait donc une copie de l'`.ini` Espressif avec ces quatre valeurs. Non vérifié : la façon dont
uDisplay gère un rétro-éclairage actif à l'état bas, et le conflit GPIO26/27 (RS485 sur la 7B, rétro-éclairage et
reset sur la carte Espressif) qui confirme qu'on ne peut pas reprendre l'`.ini` tel quel.

## 4. Dalles DSI pour notre kit ESP32-P4-Module-DEV-KIT (maître du garage)

Connecteur DSI 2 voies (broches et pas du connecteur non trouvés). Waveshare vend le kit avec écran : DEV-KIT-B =
7-DSI-TOUCH-A (7" 720x1280, ILI9881C, GT9271), DEV-KIT-C = 10.1-DSI-TOUCH-A (10,1" 800x1280, JD9365, GT9271), nappe
12 cm fournie. Testées par le BSP Espressif `cfscn/esp32_p4_module_dev_kit` 1.1.8 : ces deux-là, 8-DSI-TOUCH-A
(JD9365), 5-DSI-TOUCH-A (HX8394, GT911) et une quinzaine d'écrans « DSI LCD » Raspberry. Absentes de la liste testée :
7-DSI-TOUCH-C, modèles « -B ». Écran officiel Raspberry Pi 7" (pont TC358762) : aucune preuve, à éviter.

Sous Tasmota, aucune de ces dalles n'a de description : il faudrait l'écrire d'après le pilote Waveshare ESP-IDF,
dalles en portrait (rotation en DSI non vérifiée), tactile GT9271 non prouvé avec le script GT911.

## 5. Kits du commerce (P4 + écran, P4 + relais)

- **P4 + 8 relais : aucune carte trouvée.** Le plus proche : Waveshare ESP32-P4-86-Panel-ETH-2RO (4" 720x720 DSI,
  Ethernet, RS485 isolé, 2 relais 10 A, 6 à 30 V, format 86 mm ; contrôleur de dalle non identifié).
- P4 + écran : Waveshare ESP32-P4-WIFI6-Touch-LCD-7B (§3), Elecrow CrowPanel Advance 7" (1024x600, ~46 $),
  M5Stack Tab5 (5" 1280x720, RS485 SIT3088, batterie), Guition JC1060P470 (7" 1024x600, JD9165 + GT911 d'après
  ESPHome, donc proche de `JD9165_DSI.ini`). Documentées ESPHome / ESP-IDF, aucun template Tasmota trouvé.
- 8 relais en S3 : Waveshare ESP32-S3-ETH-8DI-8RO (template blakadder pour la variante POE ; voir `MODELES_ESP.md`),
  KinCony F8.

## 6. Conclusion provisoire (2026-11-11)

Décision de l'utilisateur (2026-11-12) : l'écran du garage sera relié par **Wi-Fi**, pas par RS485.

Deux voies DSI à faible risque, toutes deux sur le contrôleur déjà décrit dans Tasmota :
1. **ESP32-P4-WIFI6-Touch-LCD-7B** (EK79007 + GT911, RS485 intégré) : remplacerait le kit comme maître du garage avec
   écran ; description = `EK79007_P4ev_DSI.ini` adaptée (§3).
2. Guition JC1060P470 (JD9165 + GT911) : `JD9165_DSI.ini` ; RS485 non confirmé.

Une dalle Waveshare sur le kit actuel demande d'écrire une description sur un pilote marqué « WIP ». Dans tous les
cas : ajouter l'affichage à l'env P4 (`FIRMWARE_LVGL` ou les `USE_*`), mesurer la RAM interne libre, et prévoir les
réglages de la discussion #24448 (tampons LVGL en PSRAM). L'écran RGB de l'ESP32-S3-Touch-LCD-7B (écran des débits du bureau) reste la voie
déjà maîtrisée dans ce dépôt.
