# Puces Espressif (ESP32 et autres ESP) : mémoire, processeur, compétences, usages, Tasmota

Recherche du 2026-11-11. Sources : pages produit et documentation Espressif (liens en fin de document), et pour la
compatibilité Tasmota **le code de ce dépôt** (envs de `platformio_tasmota32.ini` / `platformio_tasmota_env.ini`,
`boards/*.json`, `tasmota/tasmota_support/support_esp32.ino::GetDeviceHardware`). Le fork a 38 commits de retard sur
l'amont à cette date : l'état amont peut avoir un peu avancé.

Fiabilité : les chiffres des puces récentes (C5, C61, H4, H21, P4, S31, E22) ont été lus sur les pages Espressif ce
jour. Ceux des puces anciennes (ESP32, S2, S3, C2, C3, C6, H2, ESP8266) viennent des datasheets connues et n'ont pas
été relus un par un : à confirmer sur la datasheet avant un choix de conception. « ? » = information non trouvée.

Ce document parle des **puces** (SoC). Un module (WROOM, WROVER, MINI, PICO) ou une carte (DevKit) ajoute flash et
PSRAM autour de la puce : une puce « sans flash intégrée » est presque toujours vendue en module avec flash.

## 1. Tableau général

Légende Tasmota : **Oui** = env officiel dans l'amont, binaire publié · **Oui (exp.)** = env amont expérimental ·
**Non** = aucun env, puce inutilisable comme nœud Tasmota.

| Puce | Processeur | SRAM interne | Flash intégrée (variantes) | PSRAM | Radio | Compétences spécifiques | Usage principal | Rôle sur un typon à plusieurs ESP | Tasmota |
|---|---|---|---|---|---|---|---|---|---|
| **ESP32** (D0WD-V3, D0WDR2-V3, U4WDH, S0WD, PICO-D4, PICO-V3, PICO-V3-02) | Xtensa LX6, 2 cœurs 240 MHz (S0WD, U4WDH-S : 1 cœur 160 MHz), ULP FSM | 520 Ko | U4WDH, PICO-D4, PICO-V3 : 4 Mo ; PICO-V3-02 : 8 Mo | D0WDR2-V3 et PICO-V3-02 : 2 Mo intégrés ; externe Quad jusqu'à 8 Mo (4 Mo mappés) | Wi-Fi 4 2,4 GHz, **Bluetooth Classic** + BLE 4.2 | MAC Ethernet RMII, 2 DAC 8 bits, touch, TWAI (CAN), hôte SD/SDIO, MCPWM, PCNT, 34 GPIO | IoT généraliste, relais, passerelles | Nœud autonome ; seul à offrir le **Bluetooth Classic** (audio A2DP, SPP) avec le S31 ; esclave esp-hosted possible | **Oui** : `tasmota32` (+ `-solo1` pour 1 cœur, `-zbbrdgpro`, `-nspanel`, `-webcam`…). PSRAM des puces v1/v2 : correctifs requis |
| **ESP32-S2** (S2, S2R2, S2FH2, S2FH4, S2FN4R2) | Xtensa LX7, **1 cœur** 240 MHz, ULP RISC-V + FSM | 320 Ko | FH2 : 2 Mo ; FH4, FN4R2 : 4 Mo | R2, FN4R2 : 2 Mo intégrés ; externe possible | Wi-Fi 4 seul, **pas de Bluetooth** | USB OTG pleine vitesse, 2 DAC, touch 14, LCD/caméra parallèle, 43 GPIO | Wi-Fi + USB à bas coût | Esclave esp-hosted possible ; peu utilisé | **Oui** : `tasmota32s2`, `tasmota32s2cdc` (BLE retiré à la compilation) |
| **ESP32-S3** (S3, S3FN8, S3FH4R2, S3R2, S3R8, S3R8V, S3R16V, S3-PICO-1) | Xtensa LX7, 2 cœurs 240 MHz, instructions vectorielles (IA, DSP), ULP RISC-V + FSM | 512 Ko | FH4R2 : 4 Mo ; FN8 : 8 Mo | intégrée 2 Mo (R2), 8 Mo Octal (R8, R8V en 1,8 V), 16 Mo (R16V) ; externe Quad/Octal | Wi-Fi 4 2,4 GHz, BLE 5.0 | USB OTG + USB Serial/JTAG, LCD RGB et i8080, caméra DVP, TWAI, touch 14, 45 GPIO ; pas de DAC ni de MAC Ethernet (W5500 en SPI) | AIoT, écrans tactiles, caméra, **cartes du parc** | Hôte du Thread Border Router (avec un H2) ; maître d'un bus RS485 ; esclave esp-hosted possible | **Oui** : `tasmota32s3` ; puce de référence du fork (PSRAM = historique, LVGL, HASPmota) |
| **ESP32-C2** = **ESP8684** quand la flash est intégrée | RISC-V, 1 cœur 120 MHz | 272 Ko | ESP8684H2 : 2 Mo ; H4 : 4 Mo | **aucune** | Wi-Fi 4 2,4 GHz, BLE 5.0 | Boîtier 4x4 mm, 14 GPIO, très bas coût | Ampoules, prises, objets simples | Module Wi-Fi AT ou esclave esp-hosted pour un microcontrôleur hôte | **Oui** : `tasmota32c2` (RAM serrée, Berry limité) |
| **ESP32-C3** = **ESP8685** quand la flash est intégrée | RISC-V, 1 cœur 160 MHz | 400 Ko | FH4 / ESP8685H4 : 4 Mo ; FH8 : 8 Mo | **aucune** | Wi-Fi 4 2,4 GHz, BLE 5.0 | USB Serial/JTAG, TWAI, 22 GPIO, sécurité (secure boot, chiffrement flash) | Remplaçant bon marché de l'ESP8266 | **Module Wi-Fi AT** (esp-at : commandes sur UART1) ; esclave esp-hosted | **Oui** : `tasmota32c3` |
| **ESP32-C5** (C5HF4, C5HR2, C5HR8, C5NF8R2) | RISC-V, 1 cœur 240 MHz, cœur LP RISC-V | 384 Ko | HF4 : 4 Mo ; NF8 : 8 Mo | HR2 : 2 Mo, HR8 : 8 Mo intégrés ; externe possible | **Wi-Fi 6 bi-bande 2,4 + 5 GHz**, BLE 5, 802.15.4 (Thread, Zigbee) | TEE (APM + PMP), Key Manager, chiffrement flash et PSRAM, 29 GPIO | Wi-Fi 5 GHz (réseau 2,4 GHz saturé), Matter | **Coprocesseur radio 5 GHz** d'un P4 (esp-hosted) | **Oui** : `tasmota32c5` (board amont sans PSRAM déclarée) ; 802.15.4 non exploité |
| **ESP32-C6** (C6, C6FH4, C6FH8) | RISC-V 160 MHz + cœur LP RISC-V 20 MHz | 512 Ko + 16 Ko LP | FH4 : 4 Mo ; FH8 : 8 Mo | **aucune** | **Wi-Fi 6** 2,4 GHz, BLE 5.3, 802.15.4 (Thread, Zigbee) | 2 TWAI, USB Serial/JTAG, esclave SDIO, TEE, 30 GPIO | Matter, Thread, Wi-Fi 6 basse conso | **Coprocesseur Wi-Fi de référence du P4** (esp-hosted par SDIO) : cas du maître P4 du garage | **Oui** : `tasmota32c6` ; 802.15.4 non exploité par Tasmota |
| **ESP32-C61** (C61HF4, C61HR2, C61HR8, C61NF8R8) | RISC-V, 1 cœur 160 MHz | 320 Ko | HF4 : 4 Mo ; NF8 : 8 Mo | intégrée Quad 2 Mo (HR2), 8 Mo (HR8, NF8R8) | Wi-Fi 6 2,4 GHz (20 MHz), BLE 5 ; **pas de 802.15.4** | TEE, ECDSA, comparateur analogique | C6 « avec PSRAM, sans Thread » | Esclave esp-hosted, module AT | **Oui** : `tasmota32c61` (board avec PSRAM) |
| **ESP32-H2** (H2FH2S, H2FH4S) | RISC-V, 1 cœur 96 MHz | 320 Ko | 2 ou 4 Mo | aucune | **pas de Wi-Fi** ; BLE 5, 802.15.4 | USB Serial/JTAG, 19 GPIO | Capteurs Thread/Zigbee sur pile | **RCP 802.15.4** du Thread Border Router ou de la passerelle Zigbee (relié en UART 460800 bauds à un S3) | **Non** : cité dans le code, aucun env ni board (pas de Wi-Fi) |
| **ESP32-H21** (H21HF4) | RISC-V 96 MHz (nombre de cœurs ?) | ? | 4 Mo | ? | pas de Wi-Fi ; BLE 5, 802.15.4 ; DC-DC intégré | Évolution du H2 (20 dBm) | Objets Thread/Zigbee | RCP 802.15.4 | **Non** |
| **ESP32-H4** (H4HR2, H4HF4) | RISC-V, 2 cœurs 96 MHz, extensions DSP | 384 Ko | HF4 : 4 Mo | HR2 : 2 Mo intégrés ; externe possible | pas de Wi-Fi ; **BLE 5.4 (LE Audio)**, 802.15.4 | USB OTG, TWAI, 15 touch, 40 GPIO, DC-DC intégré | Audio BLE, objets sur pile | RCP, coprocesseur BLE (esp-hosted) | **Non** : `TASMOTA_ARCH` défini, aucun env |
| **ESP32-P4** v1.x (amont : `esp32p4`, « ES ») et **v3.x** (`esp32p4r3`) — voir § 4 | RISC-V, 2 cœurs **360 MHz (v1) / 400 MHz (v3)**, FPU, extensions IA ; cœur LP 40 MHz | 768 Ko + 8 Ko TCM | aucune (flash externe) | intégrée **16 ou 32 Mo** (NRW16, NRW32), bus 16 lignes | **aucune radio** | MIPI-CSI + ISP, MIPI-DSI, H.264 1080p30, JPEG, PPA, 2D-DMA, **USB 2.0 haute vitesse**, MAC Ethernet, hôte SDIO 3.0, TWAI, 55 GPIO | Écrans, caméra, vidéo, IA embarquée | **Hôte sans radio** : Wi-Fi/BLE fournis par un C6 (ou C5, C61…) en esp-hosted sur SDIO/SPI/UART | **Oui** : `tasmota32p4` et `tasmota32p4r3` ; Wi-Fi par `xdrv_84_esp32_hosted.ino` (commande `HostedOta`) |
| **ESP32-S31** (S31NRV16, S31NRV32) — annoncée 2026-03, production fin juillet 2026 | RISC-V, 2 cœurs 320 MHz, SIMD 128 bits, MMU | 512 Ko | ? (flash externe) | intégrée 16 ou 32 Mo (DDR 8 bits, 250 MHz) | Wi-Fi 6 2,4 GHz, **BT 5.4 Classic + LE (LE Audio)**, 802.15.4 | **MAC Ethernet 1 Gbit/s**, caméra DVP, LCD RGB/i8080, JPEG, PPA, PUF, TEE, 60 GPIO | Successeur du S3 : HMI, audio, passerelles multiprotocoles | Puce unique « tout radio » ; esclave esp-hosted possible | **Oui (exp.)** : `tasmota32s31` sur la plateforme IDF 6.1 (branche `Jason2866/platform-espressif32#IDF61`), board 16 Mo flash + 16 Mo PSRAM Octal |
| **ESP32-E22** — annoncée 2026-01, échantillons | RISC-V, 2 cœurs 500 MHz | ~1 Mo (presse) | ? | ? | **Wi-Fi 6E tri-bande 2,4/5/6 GHz**, 2x2 MU-MIMO, BT Classic + LE 5.4 | Hôte en **PCIe 2.1** ou SDIO 3.0, pilote Linux | Carte Wi-Fi de PC, tablette, box | **Coprocesseur radio d'un hôte Linux** (pas d'un ESP : absent d'esp-hosted-mcu) | **Non** |
| **ESP8266EX** | Tensilica L106, 1 cœur 80/160 MHz | ~80 Ko de données utilisateur (+ 32 Ko IRAM) | aucune (flash SPI externe, 1 à 16 Mo) | aucune | Wi-Fi 4 2,4 GHz ; pas de Bluetooth | 1 ADC 10 bits, 17 GPIO (≈ 11 utilisables) | Prises, relais, Sonoff : la puce d'origine de Tasmota | Rarement plusieurs ; jadis module AT d'un Arduino | **Oui** : `tasmota`, `-lite`, `-minimal`, `-sensors`, `-display`, `-ir`, `-knx`, `-4M`, `-zbbridge` ; 1 Mo minimum ; pas de Berry |
| **ESP8285** | ESP8266 avec flash intégrée | idem ESP8266 | 1 Mo (ESP8285H08) ou 2 Mo (H16) | aucune | idem ESP8266 | Boîtier plus petit | Sonoff Basic R2, Mini, prises compactes | — | **Oui** : builds 1 Mo (`tasmota`, `-lite`, `-minimal`) |
| **ESP8089** | (puce Wi-Fi seule, sans programme utilisateur) | — | — | — | Wi-Fi 4 2,4 GHz | Esclave SDIO piloté par un hôte Linux/Android | Tablettes et box anciennes | Carte Wi-Fi d'un processeur applicatif | **Non** |

## 2. Classement par processeur

| Architecture | Puces | À retenir |
|---|---|---|
| Tensilica L106 (1 cœur) | ESP8266, ESP8285 | Ancienne génération, RAM très juste, pas de Berry dans Tasmota |
| Xtensa LX6 (2 cœurs, ou 1) | ESP32 | Bluetooth Classic, Ethernet RMII, DAC ; plus de nouvelles fonctions |
| Xtensa LX7 (1 cœur) | ESP32-S2 | Wi-Fi seul + USB OTG |
| Xtensa LX7 (2 cœurs) | ESP32-S3 | Le plus répandu ; dernier Xtensa d'Espressif |
| RISC-V 1 cœur | C2 (120 MHz), C3 (160), C6 (160), C61 (160), C5 (240), H2 (96), H21 (96) | Radio et connectivité ; C5/C6 ajoutent un cœur LP |
| RISC-V 2 cœurs | H4 (96), S31 (320), P4 (360 / 400), E22 (500) | Nouvelle génération ; P4 sans radio, E22 coprocesseur pur |

## 3. Classement par mémoire et présence de PSRAM

| Groupe | Puces | Conséquence pour Tasmota + Berry |
|---|---|---|
| **PSRAM intégrée possible** | ESP32 (D0WDR2-V3, PICO-V3-02), S2 (R2, FN4R2), S3 (R2, R8, R8V, R16V), C5 (HR2, HR8), C61 (HR2, HR8), H4 (HR2), P4 (16 / 32 Mo, toujours), S31 (16 / 32 Mo) | Historique, LVGL, HASPmota, gros persist : réservé à ce groupe (règle du dépôt : enregistrement sur S3 et P4 seulement) |
| PSRAM externe seulement | ESP32 (autres variantes), S2, S3 sans R, C5 | Selon le module (WROVER, N8R2…) : lire la référence du module |
| **Aucune PSRAM possible** | ESP8266, ESP8285, C2, C3, C6, H2, H21 | Berry à l'étroit (C3, C6 : ~400-500 Ko de SRAM) ; C2 et ESP8266 : fonctions de base seulement |

Tasmota détecte la PSRAM au démarrage (`support_esp32.ino::FoundPSRAM`) : sur ESP32 v1/v2 (puces avant la v3), elle
n'est utilisable qu'avec les correctifs de compilation `-mfix-esp32-psram-cache-issue` (`support_esp32.ino::CanUsePSRAM`).

## 4. ESP32-P4 : v1.x et v3.x (« P4 » et « P4R3 »)

Deux générations de silicium **incompatibles au niveau du binaire** : il faut le firmware de la bonne révision.

| | P4 v1.x (v1.0, v1.1, v1.3) | P4 v3.x (v3.0, v3.1) |
|---|---|---|
| Env Tasmota amont | `tasmota32p4` (board `esp32p4`, nommé « ESP32-P4 ES », define `ESP32P4ES`) | `tasmota32p4r3` (board `esp32p4r3`, define `ESP32P4R3`) |
| Fréquence max | 360 MHz | **400 MHz** |
| Broche 54 | NC (non connectée) | **VDD_HP_1** (nouvelle alimentation) |
| Schéma | 1 MΩ sur USB_DP | 1 MΩ retiré ; 2 x 499 kΩ + 22 pF ajoutés sur le DC-DC |
| Circuit imprimé | — | Nouveau PCB en principe ; une carte v3 accepterait une puce v1 (avis FAE rapporté, non officiel) |
| Nouveautés | — | 32 entrées PMP, extension Zb, ECDSA P-384, clés HMAC/RSA_DS dans le Key Manager, RNG séparé, veille légère plus sobre, horloge I2S 160 MHz |
| Errata | MSPI-749 à 751, ROM-764, DMA-767, etc. | Corrigés (MSPI-749 seulement en v3.1) |
| ESP-IDF | `CONFIG_ESP32P4_SELECTS_REV_LESS_V3=y` | `=n` (défaut) ; IDF ≥ 5.5.3 ou ≥ 6.0 |
| Statut | **Non recommandé** pour de nouveaux designs | Recommandé |
| Références | P4NRW16, P4NRW32 | P4NRW16**X**, P4NRW32**X** |

Dans Tasmota, la différence de registres est gérée par `CONFIG_ESP_REV_MIN_FULL >= 300`
(`tasmota/include/xdrv_126_hwdump_esp32p4.h`).

**Comment savoir laquelle on a :**

1. **Carte en marche sous Tasmota** : `Status 2` -> `"Hardware":"ESP32-P4 v1.3"` ou `"ESP32-P4 v3.1"` (révision lue
   dans les eFuses, `support_esp32.ino::GetDeviceHardwareRevision`) ; même texte sur la page Informations.
   `"CpuFrequency":360` trahit aussi une v1.
2. **Carte branchée en USB, sans firmware connu** : esptool l'affiche à la connexion
   (`Chip is ESP32-P4 (revision v3.1)`), par exemple `esptool.py --chip esp32p4 chip_id`.
3. **À l'œil** : référence du module se terminant par **X** (NRW16X, NRW32X) = v3.x ; code de fabrication
   gravé **XFXX** = v3.0, **XGXX** = v3.1. Une carte qui laisse la broche 54 non connectée a été dessinée pour la v1.
4. **Symptôme** : un binaire de la mauvaise révision ne se télécharge pas ou ne démarre pas.

Dans le fork : le maître du garage (`tasmota32p4-garage-serveur-modbus`) hérite de `tasmota32p4-base-devkit` ->
`tasmota32p4` (v1.x) ; une base `tasmota32p4r3-base-devkit` existe pour une future carte v3. Avant de flasher une
nouvelle carte P4, lire `Status 2` ou la sortie d'esptool pour choisir la base.

## 5. Plusieurs ESP sur le même circuit imprimé : les montages types

| Montage | Puces | Liaison | Logiciel | Exemple |
|---|---|---|---|---|
| Hôte sans radio + coprocesseur Wi-Fi/BLE | P4 + C6 (ou C5, C61, C3, C2, S3, ESP32) | SDIO (le plus rapide), SPI, UART | **esp-hosted-mcu** : l'hôte voit une interface Wi-Fi normale | Waveshare ESP32-P4-Module-DEV-KIT du garage ; mise à jour du C6 par `HostedOta` |
| Passerelle Thread / Matter | S3 (hôte, Wi-Fi amont) + H2 (RCP 802.15.4) | UART 460800 bauds (ou SPI) + broches RESET/BOOT + 3 fils de coexistence radio | ESP Thread Border Router (OpenThread), certifié Thread 1.4 | Carte ESP Thread Border Router d'Espressif |
| Passerelle Zigbee | S3 + H2, ou ESP32/ESP8266 + EFR32 (Silicon Labs) | UART | esp-zigbee-sdk ; dans Tasmota : Zigbee2Tasmota avec un EFR32 ou un CC2652 | Sonoff ZBBridge (ESP8266 + EFR32, env `tasmota-zbbridge`), ZBBridge Pro (ESP32 + EFR32, `tasmota32-zbbrdgpro`) |
| Microcontrôleur quelconque + module Wi-Fi | STM32, AVR… + C3/C2/ESP32 | UART (commandes AT) | **esp-at** | Ancien couple Arduino + ESP-01 |
| Hôte Linux + carte Wi-Fi | Processeur Linux + E22 (Wi-Fi 6E) ou C5/C6 | PCIe / SDIO / SPI | pilote Linux, esp-hosted (version Linux) | Raspberry Pi + C6 ; futurs PC et tablettes avec E22 |
| Plusieurs nœuds Tasmota sur un même produit | ESP32 + ESP32, S3 + ESP32 | RS485 ModBus, UART, I2C, UDP | Tasmota + Berry | Architecture maître/esclaves ModBus de ce dépôt (`outils_docs/PROTOCOLE_MODBUS.md`) |

Règles de choix qui en découlent :

- **Besoin de radio sur un P4** : prévoir un coprocesseur, il n'y en a pas d'intégré. Le C6 est la référence ; le C5
  apporte le 5 GHz.
- **Besoin de Thread ou Zigbee natif** : H2 (ou C6/C5) en RCP à côté d'un S3. Tasmota n'exploite pas le 802.15.4
  intégré des C5/C6/H2 (aucune référence à `esp_ieee802154` dans `tasmota/`) : avec Tasmota, Zigbee passe par un
  EFR32 ou un CC2652 externe.
- **Besoin de Bluetooth Classic** (audio, SPP) : ESP32 d'origine ou S31.
- **Besoin d'Ethernet** : MAC intégré sur ESP32, P4 et S31 (PHY externe) ; sinon W5500 en SPI (S3).

## 6. Cartes du commerce compatibles Tasmota : où chercher, et le Waveshare 8DI

La liste des appareils vendus avec leur modèle (template) Tasmota est le **Tasmota Device Templates Repository**
(<https://templates.blakadder.com>, sources sur GitHub dans `blakadder/templates`). Le dépôt `arendst/Tasmota` ne porte
que les modules intégrés au firmware (`tasmota/include/tasmota_template.h`), où aucune carte Waveshare n'apparaît.

**Waveshare ESP32-S3-(POE-)ETH-8DI-8RO** (8 entrées optocouplées, 8 relais) : modèle présent,
<https://templates.blakadder.com/waveshare_ESP32-S3-POE-ETH-8DI-8RO.html>.

```
{"NAME":"ESP32S3-POE-ETH-8DI-8RO","GPIO":[40,1,1,1,32,33,34,35,36,37,38,39,5600,704,672,736,5568,1,1,1,1,1,0,0,0,0,0,1376,1,1,608,640,1,1,1,480,1,1],"FLAG":0,"BASE":1}
```

- Relais derrière un expandeur **TCA9554PWR** (I2C 0x20) : compiler avec `USE_TCA9554` (pas `USE_PCA9557`, les deux
  s'excluent) ; driver réécrit par arendst en décembre 2025 (discussion
  <https://github.com/arendst/Tasmota/discussions/24205>). Relais déclarés par une règle :
  `rule3 on file#tca9554.dat do {"NAME":"TCA9554","GPIO":[224,225,226,227,228,229,230,231]} endon`.
- Horloge : `USE_RTC_CHIPS` + `USE_PCF85063` ; Ethernet W5500 : `EthType 8` ; LED WS2812 : `SetOption37 24` ;
  buzzer : `BuzzerPwm 1`.
- Par défaut chaque entrée commute son relais ; `SetOption73 1` les découple (entrées publiées en messages).
- Même modèle pour les variantes sans PoE et **-C** (CAN isolé au lieu du RS485), d'après arendst.
- Fiche comparative déjà faite pour la cave : `outils_docs/cartes_relais_cave/README.md` (carte A recommandée).

**Waveshare ESP32-S3-POE-ETH-8DI-8DO** (8 entrées, 8 sorties transistor à collecteur ouvert, 500 mA, au lieu des
relais) : **aucun modèle Tasmota trouvé** (ni blakadder, ni discussion GitHub) ce jour. Le wiki Waveshare
(<https://www.waveshare.com/wiki/ESP32-S3-POE-ETH-8DI-8DO>) et la fiche ESPHome
(<https://devices.esphome.io/devices/waveshare-esp32-s3-eth-8di-8do/>) donnent le brochage pour en écrire un ; à
vérifier sur la carte avant de s'y fier (sorties sur l'expandeur, entrées sur GPIO).

## Sources

- Liste des puces : <https://www.espressif.com/en/products/socs>
- C5 : <https://www.espressif.com/en/products/socs/esp32-c5> · C61 : <https://www.espressif.com/en/products/socs/esp32-c61>
- H4 : <https://www.espressif.com/en/products/socs/esp32-h4> · H21 : <https://www.espressif.com/en/products/socs/esp32-h21>
- P4 : <https://www.espressif.com/en/products/socs/esp32-p4> ; révision v3.x :
  <https://documentation.espressif.com/esp32-p4-chip-revision-v3.x_user_guide_en.html>,
  <https://www.cnx-software.com/2026/03/23/esp32-p4-revision-3-0-gains-new-power-rail-requires-new-pcb-design-and-firmware/>,
  errata <https://docs.espressif.com/projects/esp-chip-errata/en/latest/esp32p4/>
- S31 : <https://www.espressif.com/en/products/socs/esp32-s31>, <https://www.espressif.com/en/news/ESP32_S31_Mass_Production>
- E22 : <https://www.espressif.com/en/news/ESP32_E22_Announcement>
- esp-hosted-mcu : <https://github.com/espressif/esp-hosted-mcu> · esp-at : <https://docs.espressif.com/projects/esp-at/>
- Thread Border Router : <https://docs.espressif.com/projects/esp-thread-br/en/latest/hardware_platforms.html>
