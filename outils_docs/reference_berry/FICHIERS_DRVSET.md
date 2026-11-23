# Fichiers caches de reglages du FS : `/.drvsetNNN`, `/.snssetNNN`

Releve du code du 2026-11-02 (`tasmota/`). Renvois au code par `fichier::fonction`.
Ce qui n'est pas prouve dans le code est marque **(non verifie)**.

## Mecanisme commun

- Noms : `tasmota/include/tasmota_globals.h` -> `TASM_FILE_DRIVER` = `/.drvset%03d`, `TASM_FILE_SENSOR` = `/.snsset%03d`
  (le numero est celui du driver, `XDRV_nn` / `XSNS_nn`). Fichiers binaires = la structure C du driver, 1er champ `crc32`, 2e `version`.
- Disponibles seulement avec `USE_UFILESYS`, force pour tout firmware non minimal (`tasmota_configurations.h`, section
  « Mandatory defines »). Donc present sur toutes nos cartes ESP32 (hors safeboot/minimal).
- Chargement : au demarrage, `FUNC_PRE_INIT` (ou `FUNC_INIT`) du driver -> `TfsLoadFile`. Defauts poses avant ; fichier absent = defauts.
- Sauvegarde : `FUNC_SAVE_SETTINGS`, appele par `settings.ino::SettingsSave` (donc a chaque `SaveData` et au restart via
  `SettingsSaveAll`). Le driver ne reecrit que si le CRC de la structure a change.
- Sauvegarde `/dl` : `settings.ino::SettingsConfigBackup` ajoute au `.dmp` une archive de type tar : un en-tete de 16 octets
  + contenu pour chaque `/.drvset000` a `/.drvset128` present. Si le driver est actif (`FUNC_RESTORE_SETTINGS` rend vrai) la
  copie vient de la RAM (valeur la plus recente), sinon du fichier. **Les `/.snsset*` ne sont PAS dans la sauvegarde** : la boucle
  ne lit que `TASM_FILE_DRIVER`.
- Restauration `/rs` : `settings.ino::SettingsConfigRestore`. Pour chaque fichier, CRC verifie (sauf `.drvset000`) ; driver actif =
  copie dans la structure vive, CRC volontairement invalide pour forcer la mise a niveau au restart ; driver inactif = `TfsSaveFile`.
  Taille tronquee a celle de la structure du build.
- Reset (`support_tasmota.ino::` boucle restart_flag, `CmndReset` dans `support_command.ino`) :
  - `Reset 1` (211) : `SettingsDefault` seulement. **Aucun** `FUNC_RESET_SETTINGS` : les `.drvset*` sont conserves.
  - `Reset 4/5/6` : `SettingsDefault` puis `XdrvCall(FUNC_RESET_SETTINGS)` -> chaque driver ACTIF appelle son `...SettingsLoad(1)` qui
    **supprime** son fichier (`TfsDeleteFile`) et revient aux defauts ; le fichier est recree avec les defauts a la sauvegarde du restart.
    Un driver inactif garde son fichier. `/.snsset*` : seuls ceux dont le capteur gere `erase` (NeoPool, AMSx915) suppriment ; leur appel
    par `FUNC_RESET_SETTINGS` n'est pas present dans leur `Xsns*` : **(non verifie)** qu'un `Reset 4` les efface.
  - `Reset 2/3/5/6` : `support_esp32.ino::SettingsErase` ne supprime que `/.settings` (+ NVS `main`, `qpc`), jamais les `.drvset*`.
- `CFG_HOLDER` (`my_user_config.h`, surcharge dans `user_config_override.h`) : s'il differe de `Settings->cfg_holder`,
  `settings.ino::SettingsLoad` recharge `/.settings.lkg` ou `SettingsDefault`. N'appelle **pas** `FUNC_RESET_SETTINGS` : les `.drvset*`
  survivent a un changement de `CFG_HOLDER` (nos reglages d'energie ne sont donc pas remis a zero par lui).

## Tableau

| Fichier | Source | Role | Compile sous | Sur nos cartes |
|---|---|---|---|---|
| `/.drvset000` | `xdrv_50_filesystem.ino::UfsJsonSettingsRead/Write/Delete` | **JSON partage** : une cle par driver (`drvset03`, `drvset73`, `drvset75`, `drvset79`, `drvset122`) | `USE_UFILESYS` | existe des qu'un driver JSON ecrit |
| `/.drvset003` | `xdrv_03_esp32_energy.ino::EnergySettingsLoad/Save` | Energie : calibrations, seuils, cumuls kWh, tarifs | `ESP32` + `USE_ENERGY_SENSOR` | **differentiel : actif** (536 o) ; S3/P4 : fichier seulement si un pilote d'energie est detecte |
| `/.drvset027` | `xdrv_27_esp32_shutter.ino::ShutterSettingsLoad/Save` | Volets natifs : positions, courses, calibration | `ESP32` + `USE_SHUTTER` | compile dans les envs qui `#define USE_SHUTTER` ; fichier ecrit seulement si `version > 0` |
| `/.drvset042` | `xdrv_42_0_i2s_audio_idf51.ino::I2SSettingsLoad/Save` (nom `AUDIO_CONFIG_FILENAME`) | Audio I2S : horloge, DMA, gains, bits | `USE_I2S_AUDIO` + IDF >= 5 | P4 (`USE_I2S_ALL`) ; cree seulement si une broche I2S est configuree |
| `/.drvset086` | `xdrv_86_esp32_sonoff_spm.ino::Xdrv86SettingsLoad/Save` | Sonoff SPM : affichage, relais, surcharge | `USE_ENERGY_SENSOR` + `USE_SONOFF_SPM` | `USE_SONOFF_SPM` est defini pour tout ESP32 dans l'override, mais actif seulement si `Sspm` initialise (materiel SPM) : inactif chez nous |
| `/.drvset087` | `xdrv_87_esp32_sonoff_tm1621.ino::Xdrv87SettingsLoad/Save` | Afficheur TM1621 Sonoff | `USE_DISPLAY_TM1621_SONOFF` | non defini : absent |
| `/.drvset122` | `xdrv_122_file_settings_demo.ino` (binaire) ; `xdrv_122_file_json_settings_demo.ino` (cle JSON `drvset122`) | Drivers de demonstration | `USE_DRV_FILE_DEMO` / `USE_DRV_FILE_JSON_DEMO` | non definis : absent |
| `/.snsset083` | `xsns_83_neopool.ino::NeoPoolSettingsLoad/Save` | NeoPool (piscine) | `USE_NEOPOOL` | non defini : absent |
| `/.snsset114` | `xsns_114_amsx915.ino::Amsx915SettingsLoad/Save` | Capteur de pression AMSx915 (pmin/pmax) | `USE_I2C` + `USE_AMSX915` | non defini : absent |

Cles JSON de `/.drvset000` : `drvset03` = Domoticz (`xdrv_07_ufs_domoticz.ino`, cle volontairement « 03 » : commentaire du code
« Should have been drvset07 » ; compile avec `USE_DOMOTICZ` + `USE_UFILESYS`, `USE_DOMOTICZ` n'est pas retire de nos envs : **(non verifie)**
sur le `.elf`) ; `drvset73` = LoRa et `drvset73_N` = noeuds LoRaWAN (`xdrv_73_9_lora.ino`, `xdrv_73_8_lorawan_bridge.ino`, `USE_SPI_LORA`) ;
`drvset75` = DALI (`xdrv_75_dali.ino`, `USE_DALI`, defini dans la section tasmota32 de `tasmota_configurations_ESP32.h`) ;
`drvset79` = BLE (`xdrv_79_esp32_ble.ino`, `USE_BLE_ESP32` en commentaire chez nous : absent). Pour ce fichier, `UfsJsonSettingsDelete`
retire UNE cle ; la reecriture passe par un fichier temporaire `/settmp`.

Autres fichiers caches **hors** `drvset` : `/.settings` (blob `TSettings`, tete de la sauvegarde), `/.settings.lkg` (copie « last known
good » 30 min apres la derniere modification, `support_tasmota.ino`), `/tlskey` (cle TLS, `xdrv_02_9_mqtt.ino`), `/zbv4`, `/zbdata`
(Zigbee, `xdrv_23_zigbee_4c_devices.ino`, `xdrv_23_zigbee_4b_data.ino`), `/autoexec.bat`, `/config.sys`. Ni zigbee ni tlskey ne sont
dans la sauvegarde `/dl` par ce mecanisme.

## `/.drvset003` (energie) en detail

Source : `tasmota/tasmota_xdrv_driver/xdrv_03_esp32_energy.ino`. Structure `tEnergySettings`, version `XDRV_03_VERSION` = 0x0102,
**536 octets** (verifie par le calcul : en-tete 32 o, 4 tableaux de calibration 8x4 o, 4 tableaux kWh 8x4 o, `power_delta` 16 o,
`tariff` 16 o, `tEnergyUsage` 40 o, 8 `tPhase` de 22 o = 536 ; `ENERGY_MAX_PHASES` = 8).

Champs : `crc32` (CRC de ce qui suit, sert a detecter un changement) ; `version` ; `energy_kWhdoy` (jour de l'annee du dernier cumul) ;
`energy_kWhtotal_time` ; `flag` (bits libres) ; `gui_display`, `gui_cols` (affichage web, v0x0102) ; `power/voltage/current/frequency_calibration[8]` ;
`energy_today/yesterday/total/export_kWh[8]` (float) ; `power_delta[8]` ; `tariff[4][2]` ; `energy_usage` (cumuls import/export par tarif) ;
`phase[8]` (`min/max_voltage`, `min/max_current`, `min/max_power`, `max_power_limit` + `hold` + `window`, `max_energy` + `start`).

Commandes qui la modifient (`kEnergyCommands`) : `PowerCal`, `VoltageCal`, `CurrentCal`, `FrequencyCal`, `PowerSet`, `VoltageSet`,
`CurrentSet`, `FrequencySet`, `PowerDelta`, `PowerLow/High`, `VoltageLow/High`, `CurrentLow/High`, `MaxPower`, `MaxPowerHold`, `MaxPowerWindow`,
`MaxEnergy`, `MaxEnergyStart`, `EnergyToday`, `EnergyYesterday`, `EnergyTotal`, `EnergyExportActive`, `EnergyUsage`, `EnergyExport`, `Tariff`,
`EnergyDisplay`, `EnergyCols`. Les `...Set` recalculent la calibration depuis la mesure courante.

Cycle de vie :
- Charge : `EnergyDrvInit` (`FUNC_PRE_INIT`) -> `EnergySettingsLoad(0)` **seulement si un pilote d'energie est trouve** (`TasmotaGlobal.energy_driver`).
  Defauts d'abord (remplis depuis les champs `Settings->energy_*` du blob `/.settings`, pour la compatibilite), puis `TfsLoadFile`. Si la
  version du fichier est plus ancienne, correctifs de delta puis resauvegarde.
- Sauvegarde : `FUNC_SAVE_SETTINGS` -> `EnergySettingsSave` (si CRC change) + `EnergyRtcSettingsSave` (copie en RTC, pour survivre
  a un redemarrage logiciel). `FUNC_SAVE_BEFORE_RESTART` -> `EnergySaveState` (`Xsns03`).
- Sauvegarde `/dl` : `FUNC_RESTORE_SETTINGS` -> `EnergySettingsRestore` : le `.dmp` embarque la structure VIVE.
- `Reset 4/5/6` : `FUNC_RESET_SETTINGS` -> `EnergySettingsLoad(1)` : fichier supprime, defauts (calibrations et cumuls perdus,
  recrees a la sauvegarde). `Reset 1` et `CFG_HOLDER` : **intacts**.
- Piege : le fichier n'existe que si le driver energie est actif ; un `/rs` d'une sauvegarde faite sur la carte A vers la carte B
  ecrase aussi les calibrations de B (c'est le but, mais B doit etre du meme materiel).

## `/.drvset000` (observe sur une carte)

Ce n'est PAS une structure binaire : c'est le JSON `{"drvsetNN":{...},...}` de `xdrv_50_filesystem.ino` (commentaire d'en-tete du bloc
« File JSON settings support using file /.drvset000 »). Il est cree par le premier driver JSON qui ecrit (`UfsJsonSettingsWrite`), puis
modifie cle par cle. Dans la sauvegarde `/dl`, il est copie tel quel (pas de CRC, pas d'ecrasement RAM). Sur nos cartes la cle la plus
probable est `drvset03` (Domoticz) ou `drvset75` (DALI) : **(non verifie)**, a lire en `/ufsd` ou dans le `.dmp` pour confirmer. `Reset 4/5/6`
supprime la cle de chaque driver actif, pas le fichier.

## Limites de cette etude

- Pas de verification sur `.elf` des `#define` effectifs de chaque env (lecture des `.h` seule).
- Comportement de `Reset 4` sur `/.snsset*` et sur drivers JSON inactifs : non teste.
