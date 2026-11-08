---
chantier: debitmetres-chauffage
titre: Mesure des 6 débits de la nourrice de chauffage, écran TFT et page web
statut: actif
cree: 2026-11-08
maj: 2026-11-08
source: graceful-orbiting-pudding.md
objectif: Mesurer et afficher les débits des 6 départs de radiateur avec un ESP32-S3 Tasmota, sans gêner l'écran
---
# Mesure des 6 débits de la nourrice de chauffage, écran TFT et page web

## Contexte
Analyse de référence : `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md` (commit `18ec1fc7e`).
Le pilote `FlowRateMeter` de Tasmota est limité à 2 débitmètres ; on ne modifie pas le pilote (la structure
`Settings` divergerait de l'amont).

**Décisions du 2026-11-08** : variante **V1, un seul ESP32-S3** à la nourrice : 2 `FlowRateMeter` + 4 compteurs
(`Counter1-4`), débit calculé en Berry (fenêtre 10 s). Les variantes V2 (ADS1115) et V3 (trois modules + maître)
sont écartées. Affichage : **écran OLED 128×64 + page web de la carte** ; pas d'affichage sur le P4, donc pas de
liaison vers un maître.

Capteur : débitmètre à effet Hall G1/2, 1-25 L/min (AliExpress), sortie **à impulsions**. Modèle probable **YF-B2**
(laiton + POM), fiche : `outils_docs/Electronique/Debitmetre YF-B2/YF-B2_fiche_technique.pdf` (référence à confirmer
sur l'étiquette à réception) : **F = 11 × Q** (Hz, Q en L/min, ±3 %), alimentation **5-15 V** (4,5 V mini, 15 mA),
liquide ≤ 120 °C, électronique 0-80 °C, ≤ 1,75 MPa, **sortie haute > 4,7 V sous 5 V** (adaptation à 3,3 V
obligatoire), rapport cyclique 50 % ± 10 %.
Conséquences : 11 Hz à 1 L/min, 55 Hz à 5 L/min, 275 Hz à 25 L/min → sous la limite de 1 000 Hz.

Radiateurs : **≥ 1 400 W** ; générateur : **PAC air-eau**, ΔT de conception ≈ 5 K. Un radiateur de 1 400 W nominal
(à ΔT 50 K) ne rend qu'environ 500 à 650 W avec de l'eau à 45-50 °C ; à ΔT 5 K, cela donne **1,4 à 1,9 L/min**
pour le plus petit, au-dessus du minimum du capteur (plage validée par l'utilisateur). La pompe impose un débit à
peu près constant ; seul un robinet thermostatique qui ferme peut le faire passer sous 1 L/min : affichage
« < 1 » plutôt qu'une valeur fausse (A5).
Risque propre à la PAC : 6 turbines ajoutent de la perte de charge (non donnée par la fiche) ; une PAC exige un
débit minimal, sinon elle se met en défaut (A7).

Écran OLED (lu dans le code) : le pilote SSD1306 dédié a été retiré de Tasmota (`my_user_config.h`, ligne
« REMOVED - USE_DISPLAY_SSD1306 ») ; l'écran passe par le **pilote universel** (`USE_UNIVERSAL_DISPLAY`) et le
descripteur `tasmota/displaydesc/SSD1306_128x64_display.ini` (I2C, adresse 0x3C), posé en `display.ini` sur le FS.
Une mise à jour renvoie **toute la trame** (`uDisplay_I2C_panel.cpp`, 8 pages × (3 commandes + 8 paquets de
16 octets)) : ≈ 1 220 octets, soit **≈ 110 ms à 100 kHz** (vitesse I2C par défaut de Tasmota) et ≈ 30 ms à
400 kHz (vitesse admise par le SSD1306, réglage à trouver). Même ordre que le LCD de l'analyse : la limite de
1 000 Hz par voie tient. Police par défaut : 21 caractères × 8 lignes, une ligne par départ.

Identité (2026-11-08) : lieu **bureau** ; nom affiché « Serveur Débits de PAC » ; IP **192.168.0.50** ; topic
**`chauffage/pac/debits`**. Proposés pour l'assistant persist (à confirmer en A3) : env et dossier
`tasmota32s3-serveur-debits-pac` (`data/bureau/tasmota32s3-serveur-debits-pac`), nom d'hôte ASCII
`serveur-debits-pac` (sans accent), define `FIRMWARE_ESP32S3_SERVEUR_DEBITS_PAC`.

Puce recommandée : **ESP32-S3** plutôt que P4. Le besoin (8 broches, I2C, ~0,1 % d'un cœur) est loin des limites du S3 ; le P4
n'a pas de Wi-Fi intégré (coprocesseur C6 par esp-hosted : OTA du C6 bloquée et pertes en veille modem déjà
vécues sur le P4 du garage), coûte plus cher, et ses atouts (Ethernet, écran MIPI) ne servent pas ici. Le S3 a
le même framework Berry (historique, `/graphiques`).

Patrons à réutiliser (rien à réinventer) :
- module de carte : `data/garage/tasmota32s3-capteurs-cuve-modbus/controleCuve.be` + `cuveFonctions.be`
  (commande `ReglageCuve` par `tasmota.add_cmd`, aide via `diversFonctions.traiteAide`) ;
- création d'env : page « Assistant persist » (:7900) ; fichiers par env : page :7800 ; builds : page :7700 ;
- logs : charte du `CLAUDE.md` (`logFonctions.log`, `LOG_LEVEL_*`).

Limites retenues par l'analyse (§ 6 ter) : **≤ 1 000 Hz par voie** ; mise à jour de l'écran ≤ 1,1 × sa durée
sans impulsions.

## A1 — Décisions à prendre par l'utilisateur
- [x] Référence des 6 débitmètres et type de sortie (impulsions, 0-10 V, 4-20 mA, mécanique) ; K ou courbe constructeur ; température max de l'eau admise — preuve : réponse de l'utilisateur du 2026-11-08 (Hall G1/2, 1-25 L/min, impulsions) ; fiche YF-B2 : K = 11, liquide ≤ 120 °C, électronique 0-80 °C ; référence exacte à confirmer en A2
- [x] Plage du capteur (≥ 1 L/min) comparée aux débits réels des radiateurs : acceptée, ou capteur à petit débit choisi — preuve : calcul PAC (1,4 à 1,9 L/min pour 1 400 W, Contexte), validé par l'utilisateur le 2026-11-08
- [x] Variante retenue (V1 ou V3) ; étapes de l'autre variante supprimées du plan — preuve : V1 (un seul module) choisie par l'utilisateur le 2026-11-08, mentions V3 retirées
- [x] Affichage : LCD 20×4 I2C, OLED 128×64, page web seule, et/ou P4 du garage — preuve : OLED 128×64 + page web, choix de l'utilisateur du 2026-11-08 ; pas de P4, action « liaison vers un maître » supprimée
- [x] Lieu et nom de la carte (`data/<lieu>/tasmota32s3-<nom>`), adresse IP et topic MQTT — preuve : réponse de l'utilisateur du 2026-11-08 (bureau, « Serveur Débits de PAC », 192.168.0.50, `chauffage/pac/debits`) ; IP absente du dépôt et sans réponse au ping le 2026-11-08
- [x] Puce : ESP32-S3 ou ESP32-P4 — preuve : S3 confirmé par l'utilisateur le 2026-11-08 (comparaison dans le Contexte)

## A2 — Matériel et câblage
- [x] Liste du matériel : ESP32-S3 N16R8, 6 capteurs, OLED 128×64 SSD1306 I2C (0x3C), alimentation 5 V, filtre RC par voie, câble blindé — preuve : § 7 ter de `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md` (DevKitC-1 N16R8 + bornier rail DIN Eletechsup DNDINS3 + OLED SSD1306, liens d'achat), retenu par l'utilisateur le 2026-11-08
- [x] Adaptation du signal à 3,3 V validée par l'utilisateur (proposition § 7 ter : diode Schottky BAT85 + rappel 4,7 kΩ vers 3,3 V + 1 nF, indépendante de la résistance interne inconnue du capteur ; alternative 2N7000) — preuve : « ok on y va » de l'utilisateur, 2026-11-08
- [ ] Niveaux mesurés à réception sur une voie montée (haut ≈ 3,3 V, bas < 0,8 V)
- [x] Brochage validé par l'utilisateur (proposition § 7 ter : `FlowRateMeter` GPIO 4-5, `Counter` GPIO 6, 7, 15, 16, I2C SCL 8 / SDA 9 comme le parc) — preuve : « ok on y va » de l'utilisateur, 2026-11-08
- [x] Brochage écrit dans le persist et le modèle de GPIO de la carte (A3) — preuve : `data/bureau/tasmota32s3-serveur-debits-pac/_persist.json`, `modules.debits.environnement` (compteurs 1-4 GPIO 6, 7, 15, 16 type 352 ; pinsTechniques 1-2 GPIO 4, 5 type 8992) ; drivers.I2C SDA 9 / SCL 8
- [ ] Largeur de la carte S3 achetée compatible avec le bornier DNDINS3 (25,4 ou 28 mm, 44 broches)
- [x] Fiche technique ajoutée au dépôt — preuve : `outils_docs/Electronique/Debitmetre YF-B2/YF-B2_fiche_technique.pdf` (page 4 : F = 11 × Q, 1-25 L/min)
- [ ] PAC = **Daikin Altherma haute température** (utilisateur, 2026-11-08 ; photo : 1re génération grise, `EKHBRD` + `EKHTS` + `ERRQ`/`ERSQ` probable, guide § 2.1 ter) : modèle exact lu sur la plaque ; débit minimal de la notice (12 L/min sur Altherma 3 H HT, 20 L/min sur ETBH/ETBX16) et ΔT réglé (radiateurs : 10 K fixe, 8 K si `[2-0C]` = 2 ; la pompe module son débit pour le tenir). Plage du capteur à reconfirmer : part de chaque radiateur × débit minimal de la PAC ≥ 1 L/min (≈ 1,7 L/min pour 1 400 W sur ~10 kW) ; seul un robinet thermostatique qui ferme passe sous le seuil (guide `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`, § 2.1 bis)
- [ ] Facteur K confirmé à réception (référence lue sur l'étiquette ; volume connu passé dans un capteur : impulsions / litres × 60)

## A3 — Création de l'env de la carte
- [x] Env, `_persist.json`, `autoexec.be`, section du cenv créés par l'assistant persist (:7900), diff relu — preuve : POST /creation → `"cree": true`, env `tasmota32s3-bureau-serveur-debits-pac`, dossier `data/bureau/tasmota32s3-serveur-debits-pac` (2026-11-08) ; exclusions `page_cuve`, `page_energie`, `pages_graphiques`, `pages_graphiques_moteur` ajoutées à la main (oubliées par l'assistant)
- [x] Section `#elif` de `user_config_override.h` : **accord de l'utilisateur demandé avant écriture** ; `USE_FLOWRATEMETER` (absent par défaut, `my_user_config.h:1198`) ; `USE_I2C`, `USE_DISPLAY`, `USE_UNIVERSAL_DISPLAY` — preuve : accord « oui » du 2026-11-08 ; section `FIRMWARE_ESP32S3_BUREAU_SERVEUR_DEBITS_PAC`, `git diff` : 144 lignes ajoutées, aucune supprimée
- [x] `display.ini` (copie de `tasmota/displaydesc/SSD1306_128x64_display.ini`) dans le dossier de la carte, embarqué sur le FS — preuve : `data/bureau/tasmota32s3-serveur-debits-pac/display.ini` ; lu en `/display.ini` (`xdsp_17_universal.ino:63`)
- [x] Modèle de GPIO : `FlowRateMeter` 1-2, `Counter` 1-4 ; I2C SDA/SCL — preuve : posé au démarrage depuis le persist (`configModules.be:125`, fonction = `type + id - 1`) ; `USER_TEMPLATE` du `.h` vide comme prévu par l'assistant
- [x] Compilation par la page Build (:7700), SUCCESS lu en fin de journal — preuve : journal `20261108-075514-tasmota32s3-bureau-serveur-debits-pac-compiler.log`, `[SUCCESS] Took 14055.04 seconds`, RAM 22,9 %, Flash 70,8 % (2 829 879 o)
- [ ] `banc_demarrage.py` relancé, instantané de la nouvelle carte enregistré (sans travail d'une autre session en cours) — `--dossier` VERT le 2026-11-08 (3 drivers, 0 erreur) ; carte pas encore dans CARTES ni enregistrée

## A4 — Module Berry des débits
- [x] `controleDebits.be` + `debitsFonctions.be` dans le dossier de la carte, sur le patron de la cuve ; bloc persist `debits` (nom des 6 départs, K par voie, fenêtre en s) — preuve : `debitsFonctions.be::debitsFonctions_entree` et `debitsFonctions_voie` : nom et K lus dans l'entrée qui porte la broche (décision du 2026-11-08 : `environnement.debitmetres.debitmetre1-2`, ex-`pinsTechniques`, et `environnement.compteurs.compteur1-4`, clé `k` ajoutée au `_persist.json` du dépôt), `fenetre` dans le bloc `debits` (défaut 10 s) ; banc « ReglageDebits » sur le vrai persist de la carte, 56 vérifications OK, 19 témoins rouges ; `banc_demarrage.py --dossier … --env …` VERT (0 erreur)
- [x] Lecture : voies 1-2 depuis le JSON `FlowRateMeter`, voies 3-6 par `gpio.counter_read(n)` sur une fenêtre fixe de `fenetre` s (n part de 0 : `counter_read(0)` = `Counter1`, `xdrv_52_3_berry_gpio.ino::gp_counter_read` ; rend nil si le compteur n'est pas configuré) — preuve : `debitsFonctions.be::debitsFonctions_mesure`, `debitsFonctions_rates` (clé `Débit` de fr_FR.h ou `Flowrate`), banc « mesure » et « JSON des capteurs » verts
- [x] Sortie homogène : bloc `DEBITS` des 6 débits dans le JSON SENSOR (`json_append`) — preuve : `debitsFonctions.be::debitsFonctions_json` (D1-D6, Total, null sans mesure), lignes de page `debitsFonctions_lignesWeb` (débit + part du total) ; banc vert
- [x] Commande `ReglageDebits` (K, nom, fenêtre par voie) et son aide — preuve : `debitsFonctions.be::debitsFonctions_reglageDebits`, `debitsFonctions_aideReglageDebits` ; banc « ReglageDebits » vert (refus voie 7, K non numérique, fenêtre 1)
- [x] Logs conformes à la charte (aucun `info` dans `every_second`), `verifie_berry.py` sans erreur ni écart — preuve : `verifie_berry.py` sur les 2 fichiers : « 0 erreur(s), 0 avertissement(s) de charte » (2026-11-08)
- [x] Banc `berry/banc_debits.py` (+ `.be`, bouchons de `gpio` et `tasmota`) : débit calculé contre impulsions injectées, voie à l'arrêt = 0, débordement de compteur, témoin qui échoue — preuve : `python outils_docs/scripts_python/berry/banc_debits.py` → 34 vérifications OK, 10 témoins rouges, « VERT », code 0 (2026-11-08)
- [x] Relecture par l'agent `relecteur-berry`, remarques traitées — preuve : aucun bloquant ; corrigés : nom échappé (`debitsFonctions_lignesWeb`), nombres stricts et virgule française (`debitsFonctions_nombre`), espaces doublés, `fenetre()` sans map par seconde ; banc 38 vérifications OK, 14 témoins rouges, VERT, code 0 (2026-11-08). Restent à voir sur carte : décimales du Rate (`FrequencyResolution`), Rate instantané contre moyenne de fenêtre (A6)

## A5 — Affichage sur l'écran TFT et page web
- [x] Écran retenu (2026-11-08, utilisateur) : TFT SPI ILI9488 480×320 + tactile XPT2046, comme le P4, par la bibliothèque UDisplay de Tasmota + LVGL/HASPmota — preuve : persist `drivers.ecran` actif (Option A3 GPIO 21, SPI CS 10 / MOSI 11 / CLK 12 / MISO 13 / DC 14, XPT2046 CS 41, rétroéclairage 40, reset 42), `#define USE_ILI9488` dans la section de la carte, env sur la base `tasmota32s3-base-N16R8` (FIRMWARE_LVGL, USE_LVGL_OPENHASP), `display.ini` = `ILI9488_XPT2046_display.ini` avec `:TS,*` ; `banc_demarrage.py --dossier … --env …` VERT (3 drivers, 0 erreur)
- [x] Compilation sur la nouvelle base (LVGL + HASPmota, ~+530 Ko : flash attendue ~86 %), SUCCESS lu en fin de journal — preuve : journal de la page Build du 2026-11-08, `[SUCCESS] Took 5782.80 seconds`, RAM 23.7 %, Flash 87.3 % (3 489 211 / 3 997 696 o) ; FlowRateMeterIR (0x40374f34) et CounterIsrArg en IRAM malgre les 3 avertissements IRAM_ATTR de xsns_96 (nm du firmware.elf)
- [x] Page HASPmota `pages.jsonl` : maquettes PNG proposées (`outils_docs/chauffage/ecran/modele-A|B|C.png`), **modèle B retenu** (utilisateur, 2026-11-08 : liste avec barres) ; page 1 = nom, barre relative à la plus forte voie, débit, part, total ; page 2 « Détails » = K de chaque voie et fenêtre. Objets écrits directement par `debitsFonctions.be::debitsFonctions_ecran` (couleur selon l'état : imprécis, arrêt, absent — impossible par `text_rule`), HASPmota démarré sur `/json/pages.jsonl` par `debitsFonctions_demarreEcran` — preuve : `banc_debits.py` 54 vérifications OK, 20 témoins rouges, VERT ; `verifie_berry.py` 0 erreur 0 avertissement. Rendu LVGL réel non vu (à juger sur carte)
- [x] Débit mesuré entre 0 et 1 L/min (hors plage du capteur) affiché « < 1 » sur l'écran et la page web, et signalé comme tel dans le JSON — preuve : `debitsFonctions.be::debitsFonctions_imprecis` (écran « <1 », page « < 1 : imprécis », JSON `Imprecis`) ; banc 45 vérifications OK, 18 témoins rouges, VERT (2026-11-08)
- [ ] Page web de la carte : 6 lignes nommées (`web_sensor`) ; lignes natives des compteurs bruts et du `FlowRateMeter` jugées sur la vraie page (gardées ou masquées), avec l'utilisateur
- [ ] Durée d'une mise à jour de l'écran mesurée sur carte (`tasmota.millis()` autour de l'écriture), consignée ; fréquence SPI du `display.ini` à essayer si l'écran est lent
- [ ] Message « capteur muet » si une voie ne donne plus d'impulsion (débit 0 prolongé, délai au choix de l'utilisateur)

## A6 — Essai de charge sur banc
- [ ] Générateur : second ESP32 en `PwmFrequency` sur 6 sorties câblées aux entrées de la carte (fait AVANT l'achat des 5 autres capteurs)
- [ ] Paliers 11, 55, 275 Hz (1, 5 et 25 L/min), puis 1 000 et 2 000 Hz par voie : impulsions comptées contre envoyées (écart < 0,5 %)
- [ ] À chaque palier : durée de mise à jour de l'écran ≤ 1,1 × la référence sans impulsions ; seuil réel relevé
- [ ] Résultats reportés au § 6 ter de l'analyse (estimation remplacée par la mesure)

## A7 — Pose, étalonnage et documentation
- [ ] Débit affiché par la PAC relevé AVANT la pose des capteurs (référence)
- [ ] Pose sur la nourrice, 6 voies affichées et nommées
- [ ] Débit de la PAC relevé APRÈS la pose : au-dessus de son minimum constructeur, aucun défaut de débit sur une semaine
- [ ] Contrôle de cohérence : somme des 6 débits contre le débit de la PAC, K corrigé par `ReglageDebits` si besoin
- [ ] Mode d'emploi dans `outils_docs/README.md` et carte des documents du `CLAUDE.md` mis à jour
- [ ] Commit par `/commite`

## Améliorations restantes
- [ ] [projet] Carte porteuse PCB pour la nourrice (skill `pcb-tasmota`)
- [ ] [projet] Historique et page `/graphiques` des 6 débits (S3 : framework existant)
- [ ] [projet] Assistant persist : reprendre `page_cuve`, `page_energie`, `pages_graphiques`, `pages_graphiques_moteur` dans le `custom_files_exclude` d'un env créé (oubli constaté le 2026-11-08)
- [ ] [projet] Vidéo guidée du réglage de l'équilibrage (guide `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`), si l'utilisateur la demande
- [ ] [projet] Lire la PAC (EKHBRD probable, photo du 2026-11-08) : passerelle RTD-W en Modbus RS485 ou pont P1P2MQTT, lecture seule ; pas de voie X10A prouvee (guide § 2.1 ter)
- [ ] [projet] Bloc `drivers.ecran` du P4 (et modèle de l'assistant persist à vérifier) : rétroéclairage et reset rangés dans `relais`, lus comme de vrais relais par `configDevicesByRules` dès que l'écran est activé (`key_error - timestamp`, constaté le 2026-11-08 sur la carte des débits) ; les mettre dans `pinsEcrans`
- [ ] [projet] Températures départ et retour (DS18B20) pour la puissance par radiateur : P (W) ≈ 1,16 × Q (L/h) × ΔT (K)

## Vérification
- Banc PC : `banc_debits.py` vert, avec témoin négatif lu ; `banc_demarrage.py` vert.
- Sur carte : 6 débits présents dans `Status 10` (JSON SENSOR), sur la page web et sur l'écran OLED.
- Charge : A6 mesuré, pas estimé ; aucune impulsion perdue jusqu'à 1 000 Hz par voie.
- Réel : somme des 6 débits cohérente avec le débit de la PAC, circuit chaud ; PAC sans défaut de débit.
