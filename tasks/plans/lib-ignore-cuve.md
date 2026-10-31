---
chantier: lib-ignore-cuve
titre: Accélérer le scan des dépendances (LDF) — essai lib_ignore sur l'env de la cuve
objectif: Réduire le temps du scan LDF et de la compilation de l'env cuve en ignorant les bibliothèques qu'il n'utilise pas, mesuré avant et après
statut: actif
cree: 2026-10-31
maj: 2026-10-31
---
# Essai lib_ignore sur l'env de la cuve

## Contexte
« Scanning dependencies... » = LDF de PlatformIO, mode `chain` (`platformio.ini`, `lib_ldf_mode`).
Ce mode ne lit pas les `#ifdef` : tout `#include` présent dans le code tire sa bibliothèque, même si la
fonction est désactivée. Journal cuve du 2026-10-31 10:21 : 138 bibliothèques compatibles, ~120 dans le
graphe, dont `lvgl`, `HASPmota`, `IRremoteESP8266`, `RadioLib`, `LoRa`, `ESP Mail Client`, `ESP KNX IP`…
Le LDF tourne à chaque `pio run` (upload et buildfs compris), sans cache ; les bibliothèques du graphe
sont aussi compilées.

Décisions : `lib_ldf_mode = off` écarté (liste de ~120 bibliothèques à tenir à la main) ; `chain+`/`deep`
écartés (plus lents). Essai sur UN env (`tasmota32s3-garage-capteurs-cuve-modbus`) avant toute extension.

Pièges :
- Toute modification du cenv change l'empreinte du projet → `pio run` vide TOUT `.pio/build` (tous envs) :
  le premier build après l'édition repart de zéro.
- Ignorer une bibliothèque dont la fonction est active (`USE_xxx` défini) → erreur « No such file » ou
  édition de liens en échec : la liste se vérifie contre les defines actifs de l'env.
- `lib_ignore` de l'env REMPLACE celui hérité : repartir de `${env:tasmota32s3-base-N16R8.lib_ignore}`.
- Contrôle « aucun build » dans la MÊME commande que l'édition du cenv (lessons.md, 2026-10-31).
- Mesures sous `PYTHONIOENCODING=utf-8` (sinon la sortie de pio est perdue).

## A1 — Mesure de référence (avant)
- [x] Aucun build en cours, puis `pio run -e tasmota32s3-garage-capteurs-cuve-modbus` (compilation seule) avec sortie horodatée ligne par ligne — preuve : journal `avant_1.log` (scratchpad de la session), 12:56:59 → 14:19:45, SUCCESS ; `.pio/build` vide au départ (purgé par mon lancement fautif de 12:43, voir lessons.md)
- [x] Noter : durée du scan (« Scanning dependencies » → fin du « Dependency Graph »), durée totale, nombre de bibliothèques du graphe — preuve : scan 335 → 1637 s = **21 min 42** (Defender actif) ; total **1 h 22 min 17** ; 138 compatibles, 122 au 1er niveau du graphe
- [x] Noter la taille du firmware (`firmware.bin`, RAM/Flash du résumé) — preuve : `firmware.bin` 2 934 912 o ; Flash 2 934 339 o (73,4 %) ; RAM 71 484 o (21,8 %)

## A2 — Essai exclusion Defender (avant lib_ignore)
- [x] Exclusions posées par l'utilisateur (PowerShell admin) : dépôt + `~/.platformio` — preuve : `Add-MpPreference -ExclusionPath …` lancé le 2026-10-31 vers 14:04, pendant la mesure 1 (scan de la mesure 1 fait AVEC Defender)
- [ ] Mesure incrémentale avec exclusion : durée du scan comparée aux 21 min 42 de la mesure 1, durée totale
- [ ] Bilan rapporté ; exclusions gardées ou retirées (`Remove-MpPreference -ExclusionPath …`) selon la décision de l'utilisateur

## A3 — Liste des bibliothèques à ignorer
- [x] Defines actifs de l'env relevés (sortie de `pio-tools/dump-defines.py` ou `tasmota/tasmota_defines_for_berry.h`) — preuve : `tasmota/tasmota_defines_for_berry.h` régénéré par le build de la cuve (14:53:33, 3 170 lignes)
- [x] Candidats du graphe croisés avec ces defines : ne garder que ceux dont la fonction est INACTIVE sur la cuve — preuve : include de chaque bibliothèque cherché dans `tasmota/` et sa garde `USE_xxx` lue. Fonction absente (lib_ignore seul) : lvgl, LVGL_assets, Berry mapping to LVGL, HASPmota (USE_LVGL) ; ESP8266Audio, ESP8266SAM, mp3_shine_esp32 (I2S) ; JPEGDEC (USE_BERRY_IMAGE) ; Adafruit Fingerprint (AS608) ; MFRC522 ; RF24 ; KeeloqLib ; OpenTherm ; LibTeleinfo ; esp_wireguard_tasmota ; QuickEspNow (WIZMOTE) ; MLX90640 ; SevenSegmentTM1637, LedControl (TM1637) ; LiquidCrystal_I2C (LCD) ; Adafruit GFX, LED Backpack (MATRIX/SEVENSEG) ; universal display, Display renderer (DISPLAY). Fonction ACTIVE (exigerait un `#undef` dans `user_config_override.h`, donc un firmware différent) : Berry Matter (MATTER_DEVICE), IRremoteESP8266, ESP KNX IP, ESP Mail Client (SENDMAIL), TasmotaDali, TM1638plus, RadioLib + LoRa (SPI_LORA, SX126X/127X), esp-nimble-cpp (IBEACON), Berry Animation, SEN5X
- [x] Liste validée par l'utilisateur avant édition — preuve : réponse du 2026-10-31 « Les 22 seulement » (lib_ignore seul, firmware identique ; les 10 à fonction active restent, décision ultérieure)

## A4 — Édition du cenv
- [x] `lib_ignore = ${env:tasmota32s3-base-N16R8.lib_ignore}` + la liste, dans la section de la cuve, avec un commentaire daté (contrôle « aucun build » dans la même commande) — preuve : `git diff platformio_tasmota_cenv.ini` +29 lignes après `-D FIRMWARE_ESP32S3_CAPTEURS_CUVE_MODBUS` ; 24 noms vérifiés contre le graphe de la mesure 1 ; copie avant édition dans le scratchpad
- [x] `pio project config` relu : le `lib_ignore` résolu de l'env contient l'hérité ET la liste — preuve : `ProjectConfig('platformio.ini').get(...)` = 31 entrées (7 héritées + 24) ; rideau inchangé (7) ; build_flags de la cuve intacts

## A5 — Mesure après et validation
- [ ] Premier `pio run` (repart de zéro) : compilation sans erreur ; sinon retirer de la liste la bibliothèque fautive et recommencer
- [ ] Durée du scan et nombre de bibliothèques du graphe relevés
- [ ] Taille du firmware comparée à A1 (écart attendu faible ; un écart fort se justifie)
- [ ] Second `pio run` : durée incrémentale comparée à A2 (même état Defender)
- [ ] Carte flashée (OTA ou série) puis vérifiée en fonctionnement : Berry chargé, ModBus esclave répond, capteurs de la cuve publiés

## A6 — Bilan et suite
- [ ] Gains chiffrés consignés dans ce plan (Vérification) et rapportés à l'utilisateur
- [ ] Décision de l'utilisateur : étendre au P4 et au rideau, ou en rester là
- [ ] Commit du cenv et de ce plan (message en français sans accents, sans trailer)

## Améliorations restantes
- [ ] [projet] Couper par `#undef` (section de la cuve dans `user_config_override.h`) les 10 fonctions actives inutiles (Matter, IR, KNX, SendMail, DALI, TM1638, LoRa, iBeacon, Berry Animation, SEN5X) puis ignorer leurs bibliothèques : firmware plus petit, à valider sur la carte
- [ ] [projet] Si concluant : même essai sur `tasmota32p4-garage-serveur-modbus` et `tasmota32s3-garage-rideau-garage-modbus`
- [ ] [projet] Si concluant sur plusieurs envs : liste commune dans une section `[lib_inutiles]` du cenv, réutilisée par les envs

## Vérification
À remplir : tableau avant/après (scan, total, incrémental, nombre de bibliothèques, taille du firmware).

Mesures du 2026-10-31 (machine en manque de mémoire : 12 Go, ~1,5 Go libres, 4,2 Go d'échange utilisés ;
Claude 4,6 Go, VS Code 2,7 Go ; scons à ~20 % d'un cœur pendant le scan, PowerShell > 2 min) :

| Mesure | Pré-scripts | Scan LDF | Total |
|---|---|---|---|
| 1 — Defender actif, `.pio/build` vide | 5 min 35 | 21 min 42 | 1 h 22 min 17 |
| 2 — exclusion Defender, incrémental | 2 min 29 | > 29 min 30 (arrêtée à 14:53) | — |

Conclusion provisoire : l'exclusion Defender ne raccourcit pas le scan ; le manque de mémoire domine.
À remesurer après un redémarrage (mémoire propre, seuls VS Code et la conversation ouverts).
