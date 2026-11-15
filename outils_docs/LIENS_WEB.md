# Liens web du depot

> Fichier GENERE par `outils_docs/scripts_python/outils_pc/genere_liens_web.py` : ne pas l'editer a la main,
> relancer le script (`--verifier` = code 1 si ce fichier est en retard). Les liens viennent des fichiers du fork
> (`tasks/`, `outils_docs/`, `docs/`, `.claude/`, `data/`, `CLAUDE.md`, les deux `.ini`), jamais de l'amont Tasmota.
> Sont ecartes : bancs, bibliotheques tierces, persist, adresses IP du parc, adresses fictives de test.

## 1. Outils du depot (pages locales, a lancer depuis l'annuaire)

Annuaire : http://127.0.0.1:7600 (tuile de chaque outil, lance et arrete). Adresse `127.0.0.1` depuis ce PC.

| Port | Outil |
|---|---|
| 7000 | http://127.0.0.1:7000 : Pont serie |
| 7100 | http://127.0.0.1:7100 : Sniffeur / publieur MQTT |
| 7200 | http://127.0.0.1:7200 : Serveur syslog |
| 7300 | http://127.0.0.1:7300 : Sniffeur ModBus |
| 7350 | http://127.0.0.1:7350 : Sniffeur I2C |
| 7400 | http://127.0.0.1:7400 : Testeur UDP maitre/esclave |
| 7500 | http://127.0.0.1:7500 : Synchro du fork |
| 7600 | http://127.0.0.1:7600 : Annuaire des outils |
| 7700 | http://127.0.0.1:7700 : Build et televersement |
| 7800 | http://127.0.0.1:7800 : Fichiers Berry par env |
| 7900 | http://127.0.0.1:7900 : Assistant persist |
| 7905 | http://127.0.0.1:7905 : Liens web |
| 7910 | http://127.0.0.1:7910 : Sondes en cours |
| 7920 | http://127.0.0.1:7920 : Taches planifiees |
| 7915 | http://127.0.0.1:7915 : Plan de la maison |
| 7930 | http://127.0.0.1:7930 : Catalogue d'icones |
| 7940 | http://127.0.0.1:7940 : Cartes simulees |
| 7950 | http://127.0.0.1:7950 : Atelier des graphiques |
| 7960 | http://127.0.0.1:7960 : Atelier des ecrans |
| 7970 | http://127.0.0.1:7970 : Etiquettes QR code |
| 7980 | http://127.0.0.1:7980 : Fabrique d'extensions |
| 7985 | http://127.0.0.1:7985 : Atelier des visuels d'accueil |
| 7990 | http://127.0.0.1:7990 : Organigramme des plans |
| 7995 | http://127.0.0.1:7995 : Menage du depot |

## 2. Liens externes cites dans le depot

### Ce fork (fdaubercy) (3)

- <https://fdaubercy.github.io/Tasmota/organigramme.html>  
  cite dans `CLAUDE.md` (+2)
- <https://github.com/fdaubercy/Tasmota.git>  
  cite dans `outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py`
- <https://github.com/fdaubercy/Tasmota/blob/development/>  
  cite dans `outils_docs/scripts_python/maintenance/organigramme_plans.py`

### Tasmota amont : depot, documentation, OTA (29)

- <http://ota.tasmota.com/tasmota/release>  
  cite dans `outils_docs/README.md`
- <http://ota.tasmota.com/tasmota32/release/tasmota32-FR.bin>  
  cite dans `platformio_tasmota_cenv.ini`
- <http://ota.tasmota.com/tasmota32/release/tasmota32s3.bin>  
  cite dans `platformio_tasmota_cenv.ini`
- <https://forum.tasmota.com/>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://github.com/arendst/Tas>  
  cite dans `outils_docs/schemas/commandes_tasmota.json`
- <https://github.com/arendst/Tasmota>  
  cite dans `outils_docs/HISTORIQUE_SYNCHRO_FORK.md` (+1)
- <https://github.com/arendst/Tasmota.git>  
  cite dans `outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py` (+2)
- <https://github.com/arendst/Tasmota/discussions/16226#discussioncomment-15318199>  
  cite dans `outils_docs/CHANGELOG.md`
- <https://github.com/arendst/Tasmota/discussions/22851>  
  cite dans `outils_docs/README.md`
- <https://github.com/arendst/Tasmota/discussions/24205>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://github.com/arendst/Tasmota/discussions/24448>  
  cite dans `outils_docs/ECRAN_TACTILE_ESP32P4.md`
- <https://github.com/arendst/Tasmota/pull/23206>  
  cite dans `outils_docs/CHANGELOG.md`
- <https://github.com/arendst/Tasmota/releases/latest>  
  cite dans `outils_docs/README.md`
- <https://ota.tasmota.com/extensions/>  
  cite dans `outils_docs/EXTENSIONS_TAPP.md` (+1)
- <https://ota.tasmota.com/tasmota32/coprocessor>  
  cite dans `data/fs/controleCoprocesseur.be` (+3)
- <https://ota.tasmota.com/tasmota32/coprocessor/network_adapter_esp32c6.bin>  
  cite dans `outils_docs/CHANGELOG.md`
- <https://tasmota.github.io/docs/>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://tasmota.github.io/docs/Berry/>  
  cite dans `outils_docs/SOLIDIFICATION_BERRY.md`
- <https://tasmota.github.io/docs/Berry/#low-level-access-to-tasmota-globals-and-settings>  
  cite dans `outils_docs/CHANGELOG.md`
- <https://tasmota.github.io/docs/Blinds-and-Shutters/>  
  cite dans `outils_docs/TASMOTA_VOLETS_ROULANTS.md`
- <https://tasmota.github.io/docs/Bluetooth_ESP32/>  
  cite dans `outils_docs/README.md`
- <https://tasmota.github.io/docs/Bluetooth_MI32/>  
  cite dans `outils_docs/README.md`
- <https://tasmota.github.io/docs/Bluetooth_MI32/#tasmota-and-ble-sensors>  
  cite dans `outils_docs/README.md`
- <https://tasmota.github.io/docs/Commands/>  
  cite dans `outils_docs/TASMOTA_VOLETS_ROULANTS.md`
- <https://tasmota.github.io/docs/ESP32/>  
  cite dans `outils_docs/ECRAN_TACTILE_ESP32P4.md`
- <https://tasmota.github.io/docs/Universal-Display-Driver/>  
  cite dans `outils_docs/ECRAN_TACTILE_ESP32P4.md`
- <https://templates.blakadder.com>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://templates.blakadder.com/lilygo_T-Relay-S3.html>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://templates.blakadder.com/waveshare_ESP32-S3-POE-ETH-8DI-8RO.html>  
  cite dans `outils_docs/MODELES_ESP.md` (+1)

### Depots et projets GitHub tiers (29)

- <https://cli.github.com/>  
  cite dans `outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py`
- <https://gist.github.com/brattonc/5e5ce9beee483220e2f6>  
  cite dans `outils_docs/jauges/README.md` (+1)
- <https://github.com/>  
  cite dans `outils_docs/scripts_python/outils_pc/taches_planifiees_page.py`
- <https://github.com/aklofas/kicad-happy>  
  cite dans `.claude/skills/pcb-tasmota/references/outils_externes.md`
- <https://github.com/Arnold-n/P1P2MQTT>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://github.com/arnold-n/P1P2Serial>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://github.com/ecomfe/echarts-liquidfill>  
  cite dans `outils_docs/jauges/README.md` (+1)
- <https://github.com/espressif/esp-box/blob/master/docs/hardware_overview/esp32_s3_box_3/hardware_overview_for_box_3.md>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://github.com/espressif/esp-hosted-mcu>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://github.com/espressif/esp-hosted-mcu/issues/143>  
  cite dans `data/sd/html/coprocesseur.html` (+1)
- <https://github.com/espressif/esp-hosted-mcu/issues/19>  
  cite dans `outils_docs/AUDIT_BERRY_2026-10.md`
- <https://github.com/freerouting/freerouting/releases/download/v2.5.0/freerouting-2.5.0.jar>  
  cite dans `.claude/skills/pcb-tasmota/scripts/routeur_freerouting.py`
- <https://github.com/ikatyang/emoji-cheat-sheet/blob/github-actions-auto-update/README.md#table-of-contents>  
  cite dans `outils_docs/CHANGELOG.md` (+1)
- <https://github.com/Jason2866/platform-espressif32.git#Arduino/IDF55>  
  cite dans `platformio_override.ini`
- <https://github.com/Jason2866/platform-espressif32.git#Arduino/IDF55_gcc152>  
  cite dans `platformio_override.ini`
- <https://github.com/leeoniya/uPlot>  
  cite dans `outils_docs/apercus_graphiques/uPlot.iife.min.js`
- <https://github.com/Mikhus/canvas-gauges>  
  cite dans `outils_docs/jauges/README.md` (+1)
- <https://github.com/raomin/ESPAltherma>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://github.com/tasmota/arduino-esp32/releases/download/v3.3.12/framework-arduinoespressif32.tar.xz>  
  cite dans `outils_docs/firmware_sniffeur_i2c/platformio.ini`
- <https://github.com/tasmota/arduino-esp32/releases/download/v3.3.8/framework-arduinoespressif32.tar.xz>  
  cite dans `platformio_override.ini`
- <https://github.com/tasmota/esp-idf>  
  cite dans `platformio_tasmota_cenv.ini`
- <https://github.com/tasmota/platform-espressif32/releases/download/2026.09.50/platform-espressif32.zip>  
  cite dans `outils_docs/scripts_python/outils_pc/build_sortie_reelle_cuve.txt`
- <https://github.com/tasmota/platform-espressif32/releases/download/2026.10.50/platform-espressif32.zip>  
  cite dans `outils_docs/firmware_sniffeur_i2c/platformio.ini`
- <https://github.com/toorshia/justgage>  
  cite dans `outils_docs/jauges/README.md` (+1)
- <https://github.com/waveshareteam/ESP32-P4-WIFI6-Touch-LCD-7B>  
  cite dans `outils_docs/ECRAN_TACTILE_ESP32P4.md`
- <https://github.com/wjohn007/TasmoView>  
  cite dans `outils_docs/README.md`
- <https://raw.githubusercontent.com/tasmota/docs/master/docs/Commands.md>  
  cite dans `outils_docs/schemas/commandes_tasmota.json` (+1)
- <https://thelastoutpostworkshop.github.io/microcontroller_devkit/esp32partitionbuilder/>  
  cite dans `platformio_tasmota_cenv.ini`
- <https://www.github.com/Arnold-n/P1P2Serial/issues/41>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`

### Espressif (puces, ESP-IDF, esp-hosted) (16)

- <https://docs.espressif.com/projects/esp-at/>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://docs.espressif.com/projects/esp-chip-errata/en/latest/esp32p4/>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://docs.espressif.com/projects/esp-thread-br/en/latest/hardware_platforms.html>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://documentation.espressif.com/esp32-p4-chip-revision-v3.x_user_guide_en.html>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espboards.dev/esp32/cyd-esp32-8048s043/>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.espboards.dev/esp32/esp32s3box/>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.espboards.dev/esp32/lilygo-t-display-s3/>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.espressif.com/en/news/ESP32_E22_Announcement>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/news/ESP32_S31_Mass_Production>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/products/socs>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/products/socs/esp32-c5>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/products/socs/esp32-c61>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/products/socs/esp32-h21>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/products/socs/esp32-h4>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/products/socs/esp32-p4>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.espressif.com/en/products/socs/esp32-s31>  
  cite dans `outils_docs/MODELES_ESP.md`

### Fabricants, boutiques, fiches materiel (30)

- <http://crccalc.com/>  
  cite dans `outils_docs/Electronique/Connecteur ModBus/On-line CRC calculation/On-line CRC calculation 1/URL.txt`
- <https://crccalc.com/?crc=030201FF&method=CRC-16&datatype=hex&outtype=hex>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://devices.esphome.io/devices/KinCony-KC868-A8v3>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://devices.esphome.io/devices/waveshare-esp32-s3-eth-8di-8do/>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://devices.esphome.io/devices/Waveshare-ESP32-S3-ETH-8DI-8RO>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://docs.waveshare.com/ESP32-P4-WIFI6-Touch-LCD-7B>  
  cite dans `outils_docs/ECRAN_TACTILE_ESP32P4.md`
- <https://docs.waveshare.com/ESP32-S3-Touch-LCD-4.3B>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://files.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-7B/ESP32-P4-WIFI6-Touch-LCD-7B.pdf>  
  cite dans `outils_docs/ECRAN_TACTILE_ESP32P4.md`
- <https://fr.aliexpress.com/w/wholesale-esp32-s3-n16r8-devkitc-1.html>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://fr.aliexpress.com/w/wholesale-oled-0.96-ssd1306-i2c.html>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://openelab.com/products/elecrow-crowpanel-advance-3-5-hmi-esp32-s3-ai-touch-screen>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://openelab.io/fr/>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://openelab.io/fr/products/waveshare-8-ch-relay-board>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://openelab.io/fr/products/waveshare-industrial-8-channel-esp32-s3-wifi-relay-eth-8di-8ro-module-rs485>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://ozeki.hu/p_5846-appendix.html>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://ozeki.hu/p_5858-modbus-tcp.html>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://www.aliexpress.com/item/1005008046317499.html>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.amazon.com/eletechsup-ESP32-S3-DevKitC-1-Expansion-Terminals-Bluetooth/dp/B0GCXMCQ1T>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.amazon.fr/BTF-LIGHTING-WS2812B-30pixels-Individuellement-adressable/dp/B07LG6KH6L>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://www.amazon.fr/DollaTek-SSD1306-embases-Broches-Arduino/dp/B07QJWHVDH>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.amazon.fr/s?k=ESP32-S3+N16R8+DevKitC-1>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.atomic14.com/esp32/boards/guition-jc3248w535/>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.atomic14.com/esp32/boards/guition-jc4827w543/>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.cnx-software.com/2023/05/05/60-m5stack-cores3-esp32-s3-iot-controller-comes-with-2-inch-display-vga-camera-multiple-sensors/?amp=1>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.cnx-software.com/2026/03/23/esp32-p4-revision-3-0-gains-new-power-rail-requires-new-pcb-design-and-firmware/>  
  cite dans `outils_docs/MODELES_ESP.md`
- <https://www.waveshare.com/esp32-s3-eth-8di-8ro-c.htm>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://www.waveshare.com/esp32-s3-eth-8di-8ro.htm>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://www.waveshare.com/wiki/ESP32-S3-ETH-8DI-8RO>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://www.waveshare.com/wiki/ESP32-S3-ETH-8DI-8RO-C>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://www.waveshare.com/wiki/ESP32-S3-POE-ETH-8DI-8DO>  
  cite dans `outils_docs/MODELES_ESP.md`

### PCB, fabrication, KiCad (4)

- <https://docs.kicad.org/10.0/en/cli/cli.html>  
  cite dans `.claude/skills/pcb-tasmota/references/fabrication.md`
- <https://jlcpcb.com/capabilities/pcb-capabilities>  
  cite dans `.claude/skills/pcb-tasmota/references/fabrication.md`
- <https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad>  
  cite dans `.claude/skills/pcb-tasmota/references/fabrication.md`
- <https://www.pcbway.com/capabilities.html>  
  cite dans `.claude/skills/pcb-tasmota/references/fabrication.md`

### Icones, polices, images, design (13)

- <https://api.iconify.design>  
  cite dans `outils_docs/scripts_python/outils_pc/atelier_visuels_icones_web.py` (+1)
- <https://fonts.google.com>  
  cite dans `outils_docs/scripts_python/outils_pc/atelier_ecrans_page_polices.py` (+1)
- <https://fonts.google.com/icons>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md` (+1)
- <https://fonts.googleapis.com>  
  cite dans `data/bureau/tasmota32s3-serveur-debits-pac/equilibrage.html` (+1)
- <https://icon-sets.iconify.design/>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md` (+1)
- <https://lucide.dev/icons/>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md` (+1)
- <https://lvgl.io/tools/fontconverter>  
  cite dans `outils_docs/scripts_python/outils_pc/atelier_ecrans_polices.py`
- <https://lvgl.io/tools/imageconverter>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md`
- <https://phosphoricons.com/>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md` (+1)
- <https://pictogrammers.com/library/mdi/>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md` (+1)
- <https://pictogrammers.com/library/mdi/icon/>  
  cite dans `outils_docs/scripts_python/outils_pc/icones_catalogue_page.py`
- <https://simpleicons.org/>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md` (+1)
- <https://tabler.io/icons>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md` (+1)

### IA et fournisseurs de modeles (8)

- <https://aistudio.google.com/docs/rate-limits>  
  cite dans `outils_docs/visuels_accueil/FOURNISSEURS_IA.md`
- <https://api.mistral.ai/v1/chat/completions>  
  cite dans `outils_docs/visuels_accueil/FOURNISSEURS_IA.md`
- <https://docs.mistral.ai/capabilities/vision/>  
  cite dans `outils_docs/visuels_accueil/FOURNISSEURS_IA.md`
- <https://generativelanguage.googleapis.com/v1beta/openai/chat/completions>  
  cite dans `outils_docs/visuels_accueil/FOURNISSEURS_IA.md`
- <https://openrouter.ai/api/v1/chat/completions>  
  cite dans `outils_docs/visuels_accueil/FOURNISSEURS_IA.md`
- <https://openrouter.ai/docs/api-reference/limits>  
  cite dans `outils_docs/visuels_accueil/FOURNISSEURS_IA.md`
- <https://openrouter.ai/docs/guides/privacy/data-collection>  
  cite dans `outils_docs/visuels_accueil/FOURNISSEURS_IA.md`
- <https://www.google.com/>  
  cite dans `data/cave/tasmota32-serveur-rly-sauvegarde/controleGlobal.be`

### Wikipedia et references (1)

- <https://en.wikipedia.org/wiki/Modbus>  
  cite dans `outils_docs/Aide/MODBUS.md`

### Pages Claude (artifacts publies) (1)

- <https://claude.ai/artifact/6oyWDPZEAhjo5btUxs6BL7>  
  cite dans `tasks/plans/debitmetres-chauffage.md` (+1)

### Autres sites (54)

- <http://docs.platformio.org/en/stable/projectconf.html>  
  cite dans `platformio_override.ini`
- <http://fdaubercy.freeboxos.fr>  
  cite dans `data/fs/discoveryFonctions.be`
- <https://assets.danfoss.com/documents/DOC131186404734/DOC131186404734.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://blog.claudiupersoiu.ro/2024/11/10/adding-a-slider-to-tasmota-using-berryscript/>  
  cite dans `outils_docs/exemples de scripts BERRY/exemple_slider.be`
- <https://community.openenergymonitor.org/t/daikin-altherma-3-pump-limitation/29714>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://dashboardicons.com/>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md`
- <https://discord.gg/Ks2Kzd4>  
  cite dans `outils_docs/README.md`
- <https://discourse.nodered.org/t/svg-animation-tank-level/86360>  
  cite dans `outils_docs/jauges/README.md`
- <https://docs.m5stack.com/en/core/CoreS3>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://done.land/components/microcontroller/families/esp/esp32/developmentboards/esp32-s3/guitionjc3248w535/>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://eduscol.education.fr/sti/sites/eduscol.education.fr.sti/files/ressources/pedagogiques/13734/13734-tp5-mise-en-service-equilibrage-2021.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://eletechsup.com/products/dndins3-esp32-s3-din-rail-mounting-expansion-board-all-pinout-3-96-screw-terminal-module-usb-otg-n16r8-n8r8-for-wi-fi-bluetooth-le>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://elty.pl/en_US/p/8-Channel-Relay-Module-with-ESP32-S3-WiFi-Ethernet-W5500-and-RS485/3980>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://emariete.com/en/esp32-relay-board-x8/>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://forum.arduino.cc/t/ws2812b-level-shifter-is-worse-why/1439196>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://forum.heatinghelp.com/discussion/203632/how-to-properly-balance-a-hot-water-radiator-system>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://forums.futura-sciences.com/habitat-bioclimatique-isolation-chauffage/943762-conso-debit-daikin-altherma-3-a.html>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://icones.js.org/>  
  cite dans `outils_docs/ICONES_IMAGES_SOURCES.md`
- <https://ie.rs-online.com/web/p/development-tool-accessories/0839059>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://ipc2u.com/articles/knowledge-base/modbus-rtu-made-simple-with-detailed-descriptions-and-examples/>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://learn.watterott.com/kb/ws281x/WS2812B-v5.pdf>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://manualshive.com/en/manual/daikin/altherma-3-r-f/501204?page=185>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://merkblatt.suissetec.ch/fr-CH/HEIZ203/file/HEIZ203.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://modbus.org/specs.php>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://pypi.org/project/tqdm/#manual>  
  cite dans `outils_docs/scripts_python/reseau/envoi_message_udp.py`
- <https://res.cloudinary.com/sonepar-fr/raw/upload/s--ayUiJ1AJ--/v1/documents/121/RTD-W_Installation_Instructions_20670-1.07_FR.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://shop.kincony.com/products/kc868-a8v3-esp32-s3-8-channel-relay-module>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://static.giacomini.com/fr.giacomini.com/catalog/technical_documentation/R553M.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://sti-monge.fr/maintenancesystemes/wp-content/uploads/2013/06/protocole-modbus.pdf>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://thepihut.com/products/8-channel-esp32-s3-wifi-relay-module-with-rs485-poe-option>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://thingsboard.io/docs/reference/widgets/scada/traditional-fluid-system/right-analog-water-level-meter/>  
  cite dans `outils_docs/jauges/README.md` (+1)
- <https://wiki.lilygo.cc/products/t-relay-series/t-relay-s3/>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://wled.discourse.group/t/voltage-drop-logic-level-shifter/8588>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://www.bitsandparts.nl/en/esp32-s3-display-crowpanel-advance-3-5-inch-ips-touch-screen-elecrow-p1933583>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.btf-lighting.com/products/ws2815-dual-signal-led-strip-waterproof-dc12v>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://www.caleffi.com/sites/default/files/media/external-file/01346_FR.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://www.domadoo.fr/fr/esphome/7546-smlight-ruban-led-5m-ws2812b-compatible-wled-slwf-03-slwf-09-esphome.html>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://www.elecrow.com/wiki/CrowPanel_Advance_3.5-HMI_ESP32_AI_Display.html>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.energie-environnement.ch/fichiers/info_pdf/ausculter_les_radiateurs.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://www.fontsquirrel.com>  
  cite dans `outils_docs/scripts_python/outils_pc/atelier_ecrans_page_polices.py` (+1)
- <https://www.itap.it/cat_files/pdf/471FL_2594_IST_fr.pdf>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://www.kincony.com/esp32-s3-8-channel-relay-module.html>  
  cite dans `outils_docs/cartes_relais_cave/README.md`
- <https://www.lammertbies.nl/comm/info/crc-calculation.html>  
  cite dans `outils_docs/Electronique/Connecteur ModBus/On-line CRC calculation/On-line CRC calculation 2/On-line CRC calculation and free library.txt`
- <https://www.ledyilighting.com/wp-content/uploads/2025/02/WS2815B-datasheet.pdf>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://www.manualslib.fr/manual/452290/Daikin-Altherma-3-H-Ht-Ech2Oetsh16P30D.html?page=33>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://www.modbustools.com/modbus.html>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://www.printables.com/model/350540-sunton-esp32s3-8048s043c-43-screen-case>  
  cite dans `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`
- <https://www.quechoisir.org/conseils-bricolage-comment-debloquer-un-robinet-thermostatique-n100728>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://www.simplymodbus.ca/FC01.htm>  
  cite dans `outils_docs/Aide/MODBUS.md`
- <https://www.superlightingled.com/blog/ws2815-vs-ws2812b/>  
  cite dans `outils_docs/Electronique/ADS1115/CABLAGE_RUBAN_LED.md`
- <https://www.tado.com/fr/blog/how-to-balance-radiators>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://www.totalenergies.fr/particuliers/parlons-energie/dossiers-energie/chauffage-et-climatisation/radiateur-qui-ne-chauffe-pas-quelles-causes-et-quelles-solutions>  
  cite dans `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`
- <https://yutec.fr/automatisme/protocole-de-communication/fonctions-modbus/>  
  cite dans `outils_docs/Aide/MODBUS.md`

## 3. Documents telecharges ou fournis (dans le depot)

Fiches constructeur, manuels, outils Windows : a retrouver sous `outils_docs/`.

### `outils_docs/Electronique/`

- Bi-Directional-Logic-Level_HookupGuide.pdf
- ESP32_4Relais_4Ana_Modbus.pdf
- berry_short_manual.pdf

### `outils_docs/Electronique/Connecteur ModBus/`

- 16 Channel  Multifunction RS485 Module Manual.docx
- 16 Channel  Multifunction RS485 Module commamd.docx
- 2CH RS485 Relay Modbus Poll Enter.wmv
- 2CH RS485 Relay Serial HyperTerminal Enter.wmv
- 8 Channel Rail RS485 Relay Manual.docx
- 8 Channel Rail RS485 Relay commamd.docx
- Manuel Connecteur ModBus Analogique.pdf
- SerialPortTester.exe

### `outils_docs/Electronique/Connecteur ModBus/On-line CRC calculation/On-line CRC calculation 1/`

- URL.txt

### `outils_docs/Electronique/Connecteur ModBus/modbus poll/`

- ModbusPollSetup.exe

### `outils_docs/Electronique/Debitmetre YF-B2/`

- YF-B2_fiche_technique.pdf

### `outils_docs/chauffage/`

- Analyse debitmetres chauffage 2026-11-08.docx
- Comparatif modules ESP32-S3 ecran tactile.docx
- Plan debitmetres chauffage.docx

### `outils_docs/exemples de scripts BERRY/`

- tasmota_berry_github-repositories.pdf

Raccourci `outils_docs/Electronique/Connecteur ModBus/On-line CRC calculation/On-line CRC calculation 1/URL.txt` : URL : http://crccalc.com/
