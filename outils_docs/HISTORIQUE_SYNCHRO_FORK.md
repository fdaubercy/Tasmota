# Historique des synchronisations du fork

Genere automatiquement par `outils_docs/scripts_python/synchronise_fork_tasmota.py`
a chaque synchronisation reussie du fork avec upstream (arendst/Tasmota).

Append uniquement — ne jamais supprimer d'entree existante.
Les commits marques ● ont un titre qui mentionne Berry / ESP32-S3 / nos sujets.

---

## 2026-07-15 19:25 — 13 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**3 commit(s) ● a lire de pres.**

-   `846490ece` Add logging for Hosted MCU SDIO connection (#24864)
-   `5b212c1d9` Create ST7789_320x240.ini (#24868)
-   `a1720a9d7` Fix *float* output in EQ3 mqtt messages (#24869)
-   `d87c17af2` Update change logs
-   `a3ac5bab3` Fix default button/switch actions on builds without rules (#24871)
-   `989866fe6` Update change logs
- ● `aec8e2395` HASPmota ability to set default screen background on `p0b0` object (#24874)
- ● `0e4f4c7a9` HASPmota new style for demo (#24875)
-   `ff1548f68` Create SH1107_128x128_display.ini (#24877)
- ● `5acc4a368` Add Matter virtual IR HVAC thermostat support (#24821)
-   `a6454b745` Update Changelog
-   `a1639507d` Udisp SPI fix for mono color display (#24899)
-   `61fe447df` Update default .clangd with new compile flags and includes (#24897)

## 2026-09-20 11:47 — 142 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**21 commit(s) ● a lire de pres.**

-   `2bceaa043` Committing new ST7567 display (#24903)
- ● `5614aaec2` HASPmota and LVGL `stripes` widget (#24907)
- ● `3dd46b0b4` Fix ESP8266 crash-loop on PZEM/Modbus: move stray delay() inside rx-enable guard (#24886)
-   `4383a8673` MagicSwitch: add configurable masking window (fixing problems with multiple false triggering) (#24888)
-   `453b8ad13` Update change logs
-   `c144ac963` TLS support for EC P-384 curve in server certificate (#24909)
-   `23ed46def` Update change logs
-   `70fa0c5ad` Include USE_TCP_BRIDGE with tasmota-zigbee build (#24912)
-   `2d340102a` `PubSub` lib renamed `TasmotaPubSub`, hardening fixes and comprehensive non-regression tests (#24916)
-   `2f136a329` Bump version v15.5.0.2
-   `6fbf62697` MQTT more hardening and fixes from pubsub3 (#24920)
-   `2eda5214c` MAX7219 matrix: add positioned text support for multi-row displays (#24917)
-   `3725d6eb4` Fix Can sniffer functionality (#18287)
-   `63c2a3b46` Add support for baudrate 74880 replacing 74700 ((#24924)
-   `4b8de3251` Reset BLE scan flag on new operation (#24925)
-   `9c5b81f1d` Update change logs
-   `fabc35f03` Minor fixes in `LList` (#24927)
-   `f13988e67` Fix regression from last merge
-   `c24a1e426` Fix MI BLE decryption log message formatting (#24929)
-   `b6590fef1` TLS fix public key fingerprint for ECDSA certificates (#24928)
-   `640b6c2d1` Update changelogs
-   `0e12192a8` Add LList README (#24930)
-   `49f9be888` Add support for WiZ compatible IoTorero ESP-Now Remote Control additional buttons P5 to P7
- ● `6f7f91f1b` Fix potential race condition in UdpListener (#24932)
-   `ecb7c82e7` Adapt `BLEDebug` to common command syntax (#24931)
-   `2113a7d8f` Add BTHOme V2 WIP support (#20763)
-   `a154c3b2a` Add BLE MI32 BTHome decryption
-   `771cf97e2` Update BLE MI32 version to V0.9.3.0
-   `e8da90ade` Possibility to set all BLE log levels at once (#24937)
-   `4be02fc83` [EQ3-TRV] Use `atof` instead of  `sscanf` for float values (#24936)
-   `6637b637b` Extent BTHome support (v0.9.3.1)
-   `2093a23da` BLE BTHome add undecoded logging
-   `4764987f1` [EQ3-TRV] Update parsing and logging (#24941)
-   `81bf04983` Fix AddLog(0 regression
-   `d5a127fe7` Fix AddLog(0 regression
-   `552ddc5b1` Restructure source file header
-   `bb8ce1773` Add limited support for BLE BTHome (#20763)
-   `351a1e64e` Add some more checks
- ● `7e2157d59` HASPmota better support for `textarea` (#24946)
-   `58907cf57` Update change logs
-   `6a7ac34ea` [EQ3-TRV] Add command names to log (#24944)
-   `53b5911ce` Prep BTHome more sensor decoding
-   `d8578c5a3` add remote devices via MQTT (#24951)
- ● `650d52569` Berry `json.dump()` works with subclasses of `map` and `list` (#24954)
-   `b626d38df` Fixes broken sensor table layout when HTTP/MQTT bridges run alongside local sensors (#24953)
- ● `db56cd62a` Berry extend `sortedmap` constructor (#24955)
-   `1e769b93c` [EQ3-TRV] Code refactor (#24956)
-   `4999f2bd5` Update change logs
-   `0d651080b` Extend BTHome decoding with pressure and voltage
-   `b20522054` Clean up and sync messages
-   `deb9a42ad` BTHome disable event on button none
-   `52b2d232e` Fix build error: use #ifdef for USE_UNIVERSAL_TOUCH in UDSP_DEBUG block (#24957)
-   `ed3650b7f` Add chk for duplicates
-   `7c5a9104e` Add BTHome max 8 button support
-   `0e940c955` Add BTHome acceleration decoding
-   `1d682c823` NeoPool fix issue with localized JSON key (#24962)
-   `63e278de7` Update change logs
-   `3e9ebb7d5` Fix intermittent lost ble webpage
-   `88c6ec4df` Make BLE GUI look nicer
- ● `fc2b58652` Berry make `sortedmap` subclass of `map` (#24961)
- ● `ff8130c59` Berry fix `sortedmap` to act like a `map` (#24964)
-   `168ec0de5` NeoPool delocalize all JSON outputs (#24965)
-   `997845971` Update change logs
- ● `c9087e48b` MI32: Harden Berry BLE buffer handling (#24966)
-   `e4e56b6ba` BTHome: fix decryption counter issue
-   `cc310d0a3` Reduce code size and add support from Mi32Block
-   `9e05c4440` MI32: Harden packet parsing and BLE operation state (#24967)
-   `68760f2a6` Add more BTHome decodes
-   `40276f2a9` Merge branch 'development' of https://github.com/arendst/Tasmota into development
- ● `03d9c9347` MI32: harden Berry BLE client and server handling (#24970)
-   `dafc19ba8` [EQ3-TRV] More code refactoring (#24969)
-   `c988ddfc2` Add Shelly emulation for ESP32 (#24952)
-   `accf05b21` Fix Zigbee multi-endpoint attribute suffix using insertion order instead of endpoint (#24948)
-   `48393544b` MI32: improve dashboard and widget handling (#24972)
-   `37fed605b` MI32: improve logging and BLE.info (#24974)
-   `76a450080` Add BTHome unparsed to JSON and redesign button and events JSON
-   `3c184e43d` Update change logs
-   `c69d88e8a` BTHome fix initial last button
-   `5dfbd59be` Update meta data
-   `a46e750b2` Keep the first panic in the ESP32 crash recorder (#24976)
-   `8ce646231` Update change logs
-   `d3cadb4cd` Bump version v15.6.0.1
-   `0422f8d61` [EQ3-TRV] Next part of code refactoring (#24978)
-   `44a652652` Update change logs
-   `d220daf37` Update it_IT.h (#24980)
-   `fc2bdd40a` Add support for tooltips on touch media
-   `cfb0f171a` Add optional icon display of sensors (WIP)
-   `a95a6f99a` Fix zigbee compilation
- ● `46794883a` Add Modbus RTU slave to MiEL HVAC driver (xdrv_44) (#24982)
-   `9aa935c23` Update change logs
-   `2f08cd2fc` Add support for TFA Marbella pool thermometer (#24959)
-   `41964bb72` Update change logs
-   `2faea5078` Add HVAC control panel to the MiEL HVAC web UI (xdrv_44) (#24984)
-   `89ef175a3` Update change logs
-   `98868dea1` Fix BLE MI32 rssi graph
-   `b4e24df39` BLE MI32 display icons instead of data lines. disable by removing `#define USE_SENSOR_ICON`
-   `d29d3a65c` Update Italian language (#24988)
-   `2b0f5fd65` MiEL HVAC: fix duplicate GPIO name entry, accept fan_only alias (#24992)
-   `4b9247479` Update change log
- ● `559a9e027` Fix berry I2C driver message
-   `5f80f3a19` Prep buttons for late addition of virtual buttons
- ● `079718527` Add Berry virtual button support
-   `d6bc8bf10` Missed addition
-   `d5f33ec1b` Update pi4ioe5v6408_M5Stack_UnitC6L.be
- ● `da3e0d12c` Simplify berry virtual buttons
-   `e37f4c017` refactor add virtual button
- ● `a3c97ad00` Berry `sortedmap` support for `json.dump` (#24999)
-   `a0656a911` Update change logs
-   `4b9530255` NeoPool add AuxMode (#24998)
-   `f5b34a26b` BTHome (re)set button when updated state is received (#25002)
-   `a9d4c3425` Update version, disable debug
- ● `141c0ad6f` MiEL HVAC Modbus: length-based framing, queue writes, FC03 sensor mirror (#24993)
-   `40c24e193` Update change logs
- ● `e17a83c51` Matter: fix autoconfiguration after configuration reset (#24997)
-   `6ec914b19` Fix Zigbee deferred timer use after free, and the truncated backtrace that hid it (#24979)
-   `143409151` Update change logs
- ● `9fac74bac` Berry rare register allocation bug (#25010)
-   `a24518980` Fix BLE MI32 unwanted dot/comma replacement (#25009)
-   `da3bbf365` Add BLE pairing to support newer EQ3 TRV firmware (#25008)
-   `af0aa1eb9` MiEL HVAC: fix HVACSetProhibit, add it to the web panel, apply sent changes optimistically (#25004)
-   `633895a28` MiEL HVAC: hide the redundant power toggle from the web UI (#25005)
- ● `76eafebb5` MiEL HVAC: add 0x62 0x04 Get Error State to SENSOR and the Modbus slave (#25011)
-   `7e51b9e87` Add SSD1306 SPI support
-   `213d4e43b` MiEL HVAC: publish HVACSettings after an optimistic settings apply (#25017)
- ● `cb836456a` MiEL HVAC: add a web config page for the Modbus RTU slave (#25018)
-   `211691d5f` [MI32BLE] Change RSSI to general format (#25014)
-   `bf5d60e3d` Use Tasmota seperator function
-   `d96c10dba` Fix Config Backup for Shutters on ESP32 (#25016)
- ● `9068fd731` Store BLE security bonds in UfsJsonSettings (#25015)
-   `130d5342b` [MI32BLE] Improve logging and command responses (#25021)
-   `5ef80a538` [MI32BLE] Add LYWSD02MMC unit/battery support (#25022)
-   `50d9e8a13` Add support for M5Stack Unit6CL display
-   `5e329df15` Add SSD1306 SPI display description
-   `946ba2710` Fix MI32 battery polling and period handling (#25024)
-   `cde8e6207` Restore default hostname `%s` functionality using topic name only, regression from v15.4.0.2 (#24731)
-   `85d3e55c7` Fix regression from PR #25024 and enhance WiFi status line (#25026)
-   `22079e531` Add uDisplay I2C contast control (DisplayDimmer)
-   `957634346` Add static hashCheck variable to LwDecoDrgSN50v3L class (#25031)
-   `2ff79d3fd` Add hashCheck variable to LwDecoSE01L class (#25032)
-   `aa73fd62a` Add static hashCheck variable to LwDecoPSLI5 class (#25033)
-   `e03a1b39b` Add static variable hashCheck to LwDecoLHT65 class (#25034)
-   `1180a5b99` Change default behaviour to hashCeck = disabled (#25037)
