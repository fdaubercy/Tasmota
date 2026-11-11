# Carte d'affichage des débits : Waveshare ESP32-S3-Touch-LCD-7B

Module acheté le 2026-11-10 pour l'env `tasmota32s3-bureau-ecran-debits-pac` (plan `tasks/plans/debits-deux-cartes.md`, action A8).
Sources : wiki Waveshare `ESP32-S3-Touch-LCD-7B`, schéma et démo Arduino officielle (`io_extension.*`, `rgb_lcd_port.*`, lus le
2026-11-11). Documents constructeur dans `doc-waveshare-7B/` (schéma, plan 3D, ST7262, GT911, CH422G, TJA1051, WROOM-1).

## 1. Matériel

| Élément | Valeur |
|---|---|
| Module | ESP32-S3-WROOM-1-N16R8 : 16 Mo de flash, 8 Mo de PSRAM octale |
| Dalle | 7″ IPS 1024 × 600, RGB parallèle 16 bits (RGB565), contrôleur ST7262, 235 cd/m² |
| Tactile | Capacitif 5 points, GT911 en I2C, adresse 0x5D, interruption GPIO4, reset par l'expandeur (EXIO1) |
| Expandeur d'E/S | Microcontrôleur Waveshare « IO EXTENSION » en I2C, adresse **0x24** (ce n'est PAS un CH422G : protocole à registres) |
| RS485 | SP3485, sens d'émission automatique (pas de broche DE), bornier, interrupteur de terminaison 120 Ω |
| CAN | TJA1051, partage GPIO19/20 avec l'USB (choix par EXIO5) |
| Alimentation | USB-C 5 V, 350 mA annoncés ; prise batterie Li-ion 3,7 V (PH2.0, CS8501). Pas d'entrée 7-36 V |

## 2. GPIO de l'ESP32-S3

### Utilisés par la carte

| GPIO | Rôle | GPIO | Rôle |
|---|---|---|---|
| 0 | LCD G3 | 21 | LCD G7 |
| 1 | LCD R3 | 38 | LCD B4 |
| 2 | LCD R4 | 39 | LCD G2 |
| 3 | LCD VSYNC | 40 | LCD R7 |
| 4 | Tactile INT | 41 | LCD R6 |
| 5 | LCD DE | 42 | LCD R5 |
| 7 | LCD PCLK | 45 | LCD G4 |
| 8 | I2C SDA (tactile, expandeur, bornier I2C) | 46 | LCD HSYNC |
| 9 | I2C SCL | 47 | LCD G6 |
| 10 | LCD B7 | 48 | LCD G5 |
| 11, 12, 13 | Carte SD (MOSI, SCK, MISO ; CS = EXIO4) | 14 | LCD B3 |
| 15 | RS485 TXD | 16 | RS485 RXD |
| 17 | LCD B6 | 18 | LCD B5 |
| 19, 20 | USB D-/D+ ou CAN RX/TX (EXIO5) | 26 à 37 | Flash et PSRAM octale (interdits) |
| 43, 44 | UART0 (console, CH343 / bornier UART selon l'interrupteur) | | |

### Libres

| Ressource | Usage possible |
|---|---|
| **GPIO6** | Seule broche de l'ESP32 laissée libre, sur le connecteur « GPIO » (3,3 V, GND, GPIO6). Entrée ADC1 possible. |
| Bus I2C (GPIO8/9, bornier) | Capteurs I2C, en évitant 0x5D et 0x24 (et 0x20-0x27 par prudence) |
| Expandeur : EXIO0, EXIO7, ADC (registre 0x06) | Sorties lentes ou une mesure analogique, par I2C |
| Carte SD (si non montée) | GPIO11/12/13 restent câblés au support SD, sans connecteur : pas réellement réutilisables |
| CAN (si EXIO5 = CAN) | Inutilisé dans ce projet |

Conséquence : les 6 voies de comptage RESTENT sur la carte d'acquisition (architecture à deux cartes, inchangée).

## 3. Expandeur d'E/S (adresse 0x24)

Registres (démo `io_extension.h`) : `0x02` mode (0xFF = toutes en sortie), `0x03` sorties (un bit par EXIO), `0x04` entrées,
`0x05` PWM du rétroéclairage (0-255 ; la démo plafonne à 97 %), `0x06` ADC (mot 16 bits).

| EXIO | Rôle | État voulu en service |
|---|---|---|
| 1 | Reset du tactile (TP_RST) | 1 |
| 2 | Rétroéclairage (DISP) | 1 (0 = écran noir) |
| 3 | Reset de la dalle (LCD_RST) | 1 |
| 4 | CS de la carte SD (actif bas) | 1 |
| 5 | USB (0) ou CAN (1) | 0 |
| 6 | Alimentation de la dalle (LCD_VDD_EN) | 1 |

Écriture faite par `preinit.be` de la carte (`data/bureau/tasmota32s3-ecran-debits-pac/`, banc `berry/banc_preinit_7b.py`) :
`0x02 ← 0xFF`, puis `0x03 ← 0xDD` (tactile en reset), GPIO4 (INT) à 0, puis `0x03 ← 0xDF` : toutes les sorties à 1 comme la
démo, sauf EXIO5 (USB). Délais de la démo : 100, 100 et 200 ms. Sans ce pilote, l'écran reste noir même si Tasmota
initialise la dalle. Chaque écriture est contrôlée (pas d'ACK : erreur au journal). `BrRestart` ou « Restart VM » rejouent
`preinit.be` : écran coupé et tactile réinitialisé pendant 400 ms, sans autre effet.

PWM (registre 0x05) : la démo plafonne la valeur à 97 « pour ne pas éteindre l'écran » (`io_extension.cpp::IO_EXTENSION_Pwm_Output`) ;
le registre serait donc inversé (valeur haute = écran sombre). À vérifier sur la carte avant d'écrire la veille.

Moment de l'écriture : dans `preinit.be`, avant l'initialisation de l'écran. Ordre lu dans `tasmota/tasmota.ino` : `GpioInit()`
(démarre l'I2C, `support_tasmota.ino`), puis `BerryInit()` (exécute `preinit.be`), puis `XdrvXsnsCall(FUNC_PRE_INIT)`, où
`xdrv_13_display.ino` appelle `DisplayInitDriver()`. Après l'autoexec, il serait trop tard : le GT911 serait initialisé en reset et
la dalle sans alimentation. À vérifier sur la carte : l'adresse 0x5D du GT911 dépend du niveau de GPIO4 pendant son reset.

## 4. Ébauche du `display.ini` (descripteur uDisplay de Tasmota)

Ordre lu par `lib/lib_display/UDisplay/src/uDisplay.cpp` (interface RGB) : DE, VSYNC, HSYNC, PCLK, rétroéclairage, puis les
données 8 à 15, puis 0 à 7, puis la fréquence pixel en MHz. Données Waveshare : 0-4 = B3-B7, 5-10 = G2-G7, 11-15 = R3-R7.

```
:H,ST7262,1024,600,16,RGB,5,3,46,7,-1,48,47,21,1,2,42,41,40,14,38,18,17,10,39,0,45,30
:S,2,1,1,0,40,20
:V,1,48,162,152,1,3,45,13,1
:0,00
:1,01
:2,02
:3,03
:UTI,GT911,I1,5d,4,-1
(script tactile GT911 repris de tasmota/displaydesc/ST7262_rgb16_display.ini)
```

`:V` = polarité HSYNC, porche avant 48, impulsion 162, porche arrière 152, polarité VSYNC, 3, 45, 13, horloge active sur front
descendant (valeurs de la démo Waveshare). À valider sur la carte : polarités, fréquence (30 MHz ; descendre vers 16-21 MHz si
l'image glisse quand le Wi-Fi travaille), rotation et inversion des axes du tactile.

## 5. HASPmota ou LVGL pur dans Tasmota

Les deux reposent sur le même moteur LVGL compilé dans le firmware (base `tasmota32s3-base-N16R8`, `FIRMWARE_LVGL`) et sur Berry.

| | HASPmota | LVGL pur en Berry |
|---|---|---|
| Description de l'écran | Fichier `pages.jsonl` (objets `p<page>b<id>`) | Code Berry (`import lv`, `lv.label(...)`, styles) |
| Mise à jour des valeurs | Berry local (`global.p1b13.text = ...`), comme aujourd'hui ; MQTT facultatif | Berry local, références aux objets |
| Modifier la disposition | Éditer le JSONL et l'envoyer sur le FS, sans recompiler | Éditer le `.be` (sans recompiler s'il n'est pas solidifié) |
| Possibilités | Sous-ensemble de LVGL : boutons, barres, jauges, labels, pages ; graphiques limités | Tout LVGL 9 : `lv.chart` (courbes), échelles, animations, thèmes |
| Code à écrire | Faible | Plus important (création et placement de chaque objet) |
| Éditeurs visuels | openHASP Designer (compatibilité partielle : HASPmota ne lit qu'une partie des attributs openHASP) | SquareLine ou EEZ Studio pour placer, puis recopie en Berry |
| RAM | Un peu plus (couche JSON et objets Berry) | Un peu moins |

Corrections à la conversation Gemini du 2026-11-10 :

- « HASPmota dépend fortement de MQTT / Home Assistant » : faux ici. HASPmota tourne en local, nos valeurs viennent de ModBus et
  sont posées par Berry.
- Les options `-DUSE_DISP_ST7262`, `-DUSE_TOUCH_GT911`, `LV_HOR_RES_MAX`, `-mfix-esp32-psram-cache-issue` et le bloc
  `platform = espressif32 @ 6.3.2` n'existent pas dans Tasmota ou ne s'appliquent pas au S3. Le firmware se construit par le cenv
  du dépôt (base N16R8 avec LVGL).
- Le `display.ini` proposé (`:H,ST7262,1024,600,16,RGB`, `:I,GT911,0x5D`, `:M,...`) n'a pas la syntaxe d'uDisplay : il manque les
  23 valeurs de broches, la ligne `:V` des timings et le script tactile `:UTI`.
- L'expandeur 0x24 (rétroéclairage, alimentation de la dalle, reset du tactile) n'est pas mentionné : c'est pourtant le point qui
  conditionne l'allumage.
- Le modèle 7″ « standard » est en 800 × 480 ; le 1024 × 600 est le **7B**.

## 6. Remarques

- Le persist actuel de l'affichage décrit un S3 DevKit + ILI9488 en SPI + XY-017 sur 17/18 : sur le 7B, les GPIO 10 à 14, 17, 18,
  21 et 40 à 42 sont pris par la dalle. Tout le bloc `drivers.ecran`, le RS485 et la section `.h` sont à refaire (plan A8).
- RS485 : le bornier du 7B remplace le XY-017 côté affichage. Terminaison 120 Ω à mettre sur ON (l'affichage est en bout de bus).
- Alimentation : 5 V par USB-C seulement. Prévoir un bloc 5 V ≥ 1 A près de la nourrice, ou le 5 V de l'acquisition s'il est assez
  costaud (rétroéclairage 7″ + Wi-Fi + Range Extender).
- Mémoire : une image 1024 × 600 en RGB565 fait 1,2 Mo, placée en PSRAM ; avec LVGL et HASPmota le firmware approche 3,5 Mo, la
  flash de 16 Mo laisse l'OTA possible.
- Le rétroéclairage dépend de l'expandeur : tant que son pilote Berry n'a pas tourné, l'écran reste noir. Un plantage Berry au
  démarrage donnera donc un écran noir, sans que la carte soit morte (page web et console restent joignables).

## 7. Améliorations proposées

- Veille par gradation (registre PWM 0x05) au lieu de l'extinction, réveil au toucher.
- La surface 1024 × 600 permet d'ajouter une courbe des débits des 10 à 30 dernières minutes par voie (`lv.chart` en LVGL pur ;
  plus limité en HASPmota) et un témoin de liaison (âge du dernier relevé ModBus).
- Luminosité automatique par une photorésistance sur GPIO6 (ADC) ou sur l'ADC de l'expandeur.
- Une page « Réglages » tactile : fenêtre, veille, luminosité (`ReglageEcranDebits`), sans passer par la console.

## 8. Décisions (2026-11-11) et questions ouvertes

Décidé par l'utilisateur :

1. Alimentation : bloc USB-C 5 V dédié, près de la nourrice.
2. Veille : gradation (10 % après 5 min) puis extinction (30 min), réveil au toucher, par le PWM de l'expandeur.
3. Tactile : changement de page et page « Réglages » (fenêtre, veille, luminosité).
4. Choix HASPmota / LVGL : option `custom_interface_ecran = haspmota|lvgl` dans la section de l'env du cenv ; seuls les
   fichiers de l'interface choisie partent sur le FS.
5. Polices (2026-11-11) : les tailles 12, 16 et 24 de Roboto Condensed restent compilées (`tasmota_lv_conf.h`) ; les autres (20,
   28, 32, 36) viennent de `RobotoCondensed-Regular.ttf` (copie de `lib/libesp32_lvgl/LVGL_assets/fonts/roboto/ttf/`, licence
   `OFL.txt` du même dossier, non copiée sur la flash), rendue par FreeType. Le fichier part à plat du dossier de la carte, `ecranFonctions.rangePolices` le range au démarrage
   dans `/sd/polices/` par `gestionFileFolder.deplaceFichier` (sur la carte SD si elle est montée, sinon dans `/sd` de la flash) ;
   `pages.jsonl` le cite en `"text_font":"A:sd/polices/RobotoCondensed-Regular.ttf-36"`. Il sert aux deux interfaces : il n'est
   dans aucune liste `custom_interface_ecran_*`. **Essai sur carte à faire AVEC et SANS carte SD** : chemin vu par LVGL
   (`lvbe_fopen` -> `lv_zip_ufsp`), RAM et PSRAM prises par FreeType (4 tailles), rendu des chiffres. Une police introuvable
   ne plante pas : `lv.load_freetype_font` rend nil et HASPmota garde la police du thème (texte trop petit).

Encore ouvert : montage (paysage ou portrait, boîtier, longueur du câble RS485) et usage de GPIO6 (laissé libre en attendant).

## 9. Où changer les noms des voies

Affichage : `_persist.json` de la carte, `modules.ecranDebits.environnement.analogiques.analogique1` à `analogique6`, champ `nom`
(« Débit 1 » à « Débit 6 » depuis le 2026-11-11). Acquisition : `modules.debits.environnement.debitmetres` (voies 1-2) et `compteurs`
(voies 3-6), champ `nom`. Sur une carte en service : modifier le persist, l'envoyer (page Build, onglet Fichiers), puis `Restart 1`.
