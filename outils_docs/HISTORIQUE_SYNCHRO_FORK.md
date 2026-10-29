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

## 2026-09-27 22:27 — 15 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**4 commit(s) ● a lire de pres.**

- ● `f151ad814` Fix Matter commissioning mDNS announcements (#25069)
-   `830cb206c` Doc detailed (#25071)
-   `a8d91f4ac` MQTT tolerate delayed PINGRESP (#25067)
-   `4bdce61d9` RC522: throttle idle polling and add self-healing watchdog (#25052)
-   `a3394ba0a` Shutter: Split EnableEndStopTime into OpenEndStopTime and CloseEndStopTime (#25020)
-   `e0ee732ba` Bump version v15.6.0.2
-   `300b3bfb9` Platform 2026.09.50 Tasmota Arduino Core 3.3.12 based on IDF 5.5.5 (#25072)
- ● `a622f395d` fix: be_matter_module.c:280:19: error: #if with no expression (#25075)
-   `cadd9a561` Update change logs
-   `b0c8e4f53` DALI-2 push button bindings to control gear targets (DaliBind) (#25073)
- ● `c683ec3bc` Matter: add Electrical Power Measurement cluster to On/Off Plug-in Unit (#24922)
-   `40ed9e48e` Update change logs
- ● `35bf395e5` Update security policy
-   `7cd71e06e` [MI32-BLE] Add age of battery reading to battery icon (#25074)
-   `4ee20e1a0` feat(ir): accept raw IR data as JSON, with a channel (#25062)

## 2026-09-29 03:14 — 4 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

> Entree ajoutee a la main : le fork distant etait deja synchronise (merge `90db7808c`),
> le depot local a ete avance par `git merge --ff-only origin/development`, sans le script.

**3 commit(s) ● a lire de pres.**

-   `1972dab6d` IR accept raw data in JSON (#25077)
- ● `f93502ca5` Matter update specs to 1.6.1 (to be used by AI) (#25083)
- ● `be0c2e2b6` Clarify solidification for AI (#25085)
- ● `c4327653d` feat(matter): Phase 1 - Update Root Node for Matter 1.6.0 (#25078)

## 2026-10-12 22:26 — 13 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**3 commit(s) ● a lire de pres.**

-   `1b13a45ee` Update it_IT.h (#25133)
-   `87c972451` BMx280: re-init sensor after it lost its config, skip invalid reads (#25131)
-   `24e00fc33` Update Italian language (#25134)
-   `bf2afdc7f` Fix Zigbee cluster specific command decoding with uninitialized values (#25124)
- ● `bcc37a50a` Matter add Wi-Fi Network Diagnostics cluster (0x0036) (#25126)
- ● `f1244e5bb` Matter: report HTTP bridged-device reachability changes (#25115)
-   `68157a262` support for ESP32-C61 (#25135)
- ● `df1d8d5aa` Matter: clean up incomplete initial subscriptions (#25137)
-   `3dc69ff8c` Enable tasmota32c61 in build workflow
-   `71216f04e` Fix ESP32 model number in README
-   `19c9d2c9c` Update change logs
-   `54a1527f8` Correct and normalize eQ3/MI battery percentage calculation (#25136)
-   `5c295fbcf` Merge commit from fork

## 2026-10-17 10:02 — 21 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**3 commit(s) ● a lire de pres.**

-   `bffbbeca1` Fix possible buffer overflow
-   `b8eb9a578` Shutter: fix ShutterButton MQTT flag parameters on ESP32 (#25116)
-   `4336cd06c` Add define EMAIL_DISABLE_CHUNKING for ESP32 mail
-   `ad60406a3` Update change logs
- ● `1bb26b29c` Fix Matter MQTT subscription when Matter is disabled (#25140)
-   `c95c241fa` HttpClientLight: time out reading a body when the server goes silent (#25139)
-   `31aa390c4` Update change logs
-   `770960cec` Add BTHome events to GUI
-   `90754c5b9` AsyncHttpClientLight: finish a chunked body at the empty line after the last chunk (#25142)
- ● `a2f0c8714` LVGL library from v9.5.0 to v9.6.0 (#25144)
-   `fbe55333e` Update change logs
-   `3da77ba04` Update change logs
-   `0edebb90a` Fix BTHome binary event handling
-   `ece53a64f` AsyncHttpClientLight: end a body read when the server goes silent or closes (#25141)
- ● `47f3dbc09` Berry webclient.connected() was implemented but not exposed (#25145)
-   `8402d7d47` Update change logs
-   `a0ff1cdc5` Bump version v16.0.0.1
-   `db29ff1f1` Fix buffer overflow
-   `dad74600a` Fix possible OOB
-   `2289c619b` Fix SR04 serial checksum for AJ-SR04M (#25147)
-   `c00ece868` Fix hostByName returning negative values when lookup failed

## 2026-10-18 17:15 — 2 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**1 commit(s) ● a lire de pres.**

-   `ba3ead1af` Support OUI wildcard for command MI32Keys in case multiple devices use same bindkey like IoTorero: `mi32keys 0C3D5EFFFFFF=48656c6c6f204254486f6d65210d0a00`
- ● `6776e2ea9` Fix Modbus OOB

## 2026-10-21 20:20 — 16 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**8 commit(s) ● a lire de pres.**

-   `fb629eddb` uDisplay support for SPI QSPI displays (#25156)
- ● `6389d75c6` LVGL/HASPmota visual touch pointer (dot under finger) (#25158)
- ● `81fdbb0bb` Matter: list Window Covering commands in AcceptedCommandList (#25149)
- ● `185e41c27` Matter: fix stale host test fixtures (#25161)
- ● `7ecd858fb` MiEL HVAC Modbus: serve the RS485 slave from its own task (#25157)
-   `c47ffbe6a` Update change logs
-   `fb1929565` BTHome clarify binary state GUI display
-   `d1358faff` Fix ble eq3 bthome decryption regression
- ● `872daa869` Berry webclient: log the time of a connection timeout, not its code (#25163)
- ● `a42b45810` LVGL Mirror extension crash (#25165)
-   `00791eb3a` Fix formatting of D9 value in SH1106_display.ini
-   `38a0a4193` Fix ESP32 PWMFrequency < 8 result in WDT restart (#25155)
-   `1176980ad` Merge branch 'development' of https://github.com/arendst/Tasmota into development
-   `43c6ca368` Update change logs
- ● `da51c9b1d` LVGL add logging before crash when heap allocation fails (#25170)
- ● `5ce1f1204` LVGL Panel improved click handling (#25171)

## 2026-10-25 06:17 — 12 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge local, commit `217c9b384`)

Synchro distante refusee par GitHub (« There are merge conflicts ») : conflit dans
`.gitignore`, chaque cote ayant ajoute un bloc en fin de fichier (#25174 contre les
regles `.claude/` et defines Berry du fork). Merge fait a la main, les deux blocs
gardes ; entree ecrite a la main, pas par le script.

**4 commit(s) ● a lire de pres.**

- ● `fd390ea34` LVGL touch more responsive (#25172)
-   `d8fe06cfe` Add BLE timeout and eQ3 TRV enhancements (#25173)
-   `9515f82b2` Fix VEML7700 lux/white rounding, add new command (#25150)
-   `805fc7cb0` WifiManager: name the setup AP as it is turned on (#25169)
-   `2418be974` TuyaMCU: pace outgoing frames so the MCU is never written to back-to-back (#25151)
-   `a19e0c658` Update change logs
-   `c13305125` Remove root sdkconfig.defaults and CMakeLists.txt and ignore them (#25174)
- ● `e1325dd29` LVGL Panel update version
- ● `06d51e8fc` Matter: encode strings longer than 255 bytes (#25185)
-   `4df6fa1d4` HttpClientLight: keep read timeouts longer than 65 s (#25180)
- ● `0ad5879ab` Heap Map optional feature fur detailed memory usage at boot (#25186)
-   `4d76e1530` wpa3 variant names changed with IDF 6.x (#25190)

## 2026-10-29 04:01 — 7 commit(s) recupere(s) d'upstream

`arendst/Tasmota:development` → `fdaubercy/Tasmota:development` (merge_type : merge)

**2 commit(s) ● a lire de pres.**

- ● `d309da183` Berry `lv.start()` raises an error instead of crashing when the display can't start (#25193)
- ● `63c38614e` ESP32-S3 RGB display: fix permanent image shift after flash writes (DMA sync guard) (#25194)
-   `18ded7dc9` Platform 2026.10.50 Tasmota Arduino Core 3.3.12-1 based on IDF 5.5.5 (#25196)
-   `20b034694` Fix SML ESP8266 serial mode (#25201)
-   `8eace7eeb` Fix MPR121 sizeof (#25203)
-   `44356df05` ESP32: steady 38 kHz IR carrier (fixes #25168) (#25176)
-   `3fd043055` Boot loop when using a literal WIFI_DEFAULT_HOSTNAME (#25205)
