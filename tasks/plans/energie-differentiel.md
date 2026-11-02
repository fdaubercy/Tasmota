---
chantier: energie-differentiel
titre: Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie » (disposition B)
statut: actif
cree: 2026-10-31
maj: 2026-11-02
source: squishy-imagining-raven.md
objectif: Passer le différentiel sur le firmware du fork sans perdre calibrage, compteur ni minuteries, et lui donner une page Énergie (kWh par heure/jour/mois, coût, puissance 24 h)
---
# Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie »

## Contexte
Demande du 2026-10-31 : une page dédiée de graphiques de consommation pour les cartes à mesure
d'énergie, en commençant par le différentiel du bureau. Conception :
`docs/superpowers/specs/2026-10-31-page-energie-differentiel-design.md` (valeurs suivies :
consommation kWh, puissance, courant, facteur, fréquence ; pas la tension ; historique gardé par
la carte en flash ; disposition **B** de `outils_docs/jauges/dispositions_page_energie.html` ;
courbe de puissance 24 h conservée ; abonnement de base ; prix saisi avec date d'effet, rappel à
6 mois ; purge des plus anciens si le FS approche la saturation).

Établi sur la carte (192.168.0.49) et dans le dépôt :
- Nous D3T = relais DIN 25 A avec puce **BL0942** (RX GPIO13, TX GPIO14, 4800 bauds), ESP32-U4WDH
  160 MHz, flash 4 Mo, programme 2 880 Ko (compatible avec l'env), FS 320 Ko ; tourne sous
  **Tasmota 15.0.1 d'origine** (CfgHolder 4617), sans le framework du fork.
- **Calibrage propre** (phase 1, fichier `/.drvset003` du FS) : PowerCal 310, VoltageCal 15963,
  CurrentCal 124194 (défauts BL0942 : 596 / 15187 / 251213) ; compteur 564,205 kWh. Sauvegardés
  (relevé + config `/dl` décodée) dans `%LOCALAPPDATA%\outils_tasmota\differentiel\`.
- Audit (décisions de l'utilisateur : corriger E1-E5, protéger le calibrage, minuteries dans le
  dépôt, nettoyer le `.h`) :
  E1 TXD GPIO14 non déclaré → `configGlobal.configGlobalByJson` remet à 1 tout GPIO non déclaré par
  un groupe actif : la BL0942 deviendrait muette ; E2 `capteur2` (GPIO16, Switch2 fantôme) ;
  E3 BL0942 RX rangée dans `capteurs` (règle `Switch1#Action`, `SwitchMode`) ; E4 bouton non lié
  au relais ; E5 clés LED héritées dans `relai1`. Le 2e fil du relais bistable (GPIO12, 9313) est
  compté comme un 2e relais.
- Mécanismes existants : tout groupe d'`environnement` est posé dans le gabarit par
  `configModules.configDevicesByJon` sans logique s'il n'a pas un nom connu ; `autoexec.bat`
  (natif, rejoué à chaque démarrage, déjà embarqué) porte Timer1-11 mais diverge de la carte
  (Timer2 23:30 au dépôt, 01:00 fenêtre 5 sur la carte ; Timer3 en double ; `Timers 1` absent ;
  `Template` et `SwitchMode` contraires au persist).
- **Exception à une règle du dépôt** (`tasks/lessons.md`, 2026-10-13 : pas d'enregistrement sur
  ESP32 classique) : décidée par l'utilisateur le 2026-10-31 pour cette carte ; justifiée par
  des écritures de quelques octets par heure, sans tampon en RAM hors courbe 24 h (~600 o).

## A1 — Vérifications préalables (lecture seule)
- [x] Firmware du fork de l'env `tasmota32-bureau-interrupteur-differentiel` compilé (page build, aucun autre build en cours) ; taille ≤ 2 880 Ko — preuve : journal `20261102-005657-…-compiler.log` : SUCCESS, code de sortie 0, Flash 87,8 % (2 589 735 o sur 2 949 120), RAM statique 76 476 o
- [x] Image du FS ≤ 320 Ko avec marge pour les données (place libre mesurée, à comparer à `energieFonctions.SEUIL_KO`) : à relever au `buildfs` de A7, `littlefs.bin` du build ci-dessus n'existant plus — preuve : `buildfs` du 2026-11-02 (journal `20261102-072240`) : 26 fichiers, 155 988 o, soit 224 Ko en blocs de 4 Ko ; ~96 Ko libres estimés sur 320 (métadonnées non comptées), à relire par `UfsFree` à A8 ; seuil de purge 40 Ko
- [x] Compatibilité ESP32-U4WDH (mono ou double cœur) du firmware du fork vérifiée (doc Espressif/Tasmota, `CONFIG_FREERTOS_UNICORE`, build `tasmota32` actuel de la carte) — preuve : `Status 2` de la carte = `release-tasmota32` (binaire bi-cœur, que la doc Tasmota dit inopérant sur une puce mono-cœur) et matériel « ESP32-U4WDH-D v3.1 » ; Espressif PCN-2021-021 : U4WDH passée en bi-cœur fin 2021 → build `esp32` standard de l'env valable
- [x] Unités confirmées sur la carte : `UfsFree` (Ko), `EnergyTotal` (Wh ou kWh) et sa relecture — preuve : `UfsFree` → 300, `UfsSize` → 320 (Ko) ; `xdrv_03_esp32_energy.ino` : `EnergyTotal <v>` divise par 1000 (Wh → kWh), 2e paramètre = date de début ; relecture `EnergyTotal` → `{"Total":564.205}`

## A2 — Persist du différentiel (E1 à E5)
- [x] Groupe de broches techniques dans `modules.differentiel.environnement` : TX GPIO14 (3200), RX GPIO13 (8160), 2e fil du relais bistable GPIO12 (9313) ; `capteurs.capteur1` et `relais.relai2` retirés — preuve : `_persist.json` groupe `pinsTechniques` (relaiBistable2 GPIO12/9312 id 2, rxBL0942 GPIO13/8160, txBL0942 GPIO14/3200) ; relai2 retiré, capteur1 neutralisé (OFF, pin -1)
- [x] `capteur2` désactivé (pin -1) ; `bouton1.relaisLie` = relai1 en bascule ; `channel`/`nbLeds` retirés de `relai1` — preuve : `capteur2` OFF pin -1 ; `bouton1.relaisLie` = `ids [1]`, `delai 0`, `type Switch` ; `relai1` sans `channel`/`nbLeds`
- [x] Gabarit reconstruit à blanc (banc ou script) identique au gabarit réel de la carte — preuve : banc de démarrage avec impression du gabarit → `[32,1,9312,1,1,320,1,1,9313,8160,3200,544,1,…,4736,…]` = `Template` relevé sur la carte ; témoin sur l'ancien persist : index 10 → 1 au lieu de 3200
- [x] `banc_demarrage` : écart de l'instantané du différentiel relu (plus de `Switch1/2#Action`) puis ré-enregistré — preuve : instantané ré-enregistré (règles `Button1#Action, Mqtt, Mqtt, System, System, Time, Wifi, Wifi`, plus de `Switch1/2#Action`) ; `banc_demarrage.py --carte tasmota32-bureau-interrupteur-differentiel` → VERT
- [x] Nouveau groupe et nouvelles clés déclarés dans `outils_docs/schemas/modele_persist.json` ; schéma regénéré ; `test_assistant_persist_modele.py` vert — preuve : `"pinsTechniques": {}` dans `modele_persist.json` ; `genere_schema_persist.py --valide` → 8 OK ; `test_assistant_persist_modele.py` rouge sur le seul `drivers.I2C.environnement.TCA9554` du serveur-rly (écart antérieur, commit `8cb16a3a2`, hors chantier)

## A3 — `autoexec.bat` aligné sur la carte
- [x] Minuteries recopiées du relevé de la carte (Timer2 01:00 fenêtre 5…), doublon Timer3 retiré, `Timers 1` ajouté — preuve : `autoexec.bat` : `Timers 1` ajouté, Timer2 01:00 fenêtre 5, Timer3 en un seul exemplaire ; Timer1-11 = `Timers` du relevé du 2026-10-31
- [x] Lignes contraires au persist retirées (`Template`, `SwitchMode1/2`, `SetOption73`), réglages gardés listés — preuve : `Template`, `SetOption73 OFF`, `SwitchMode1/2` retirés (posés par `configGlobal.be`, `configDevices.be`, `configModules.be`) ; gardés : SetOption1/31/55/56/57/141/146, Latitude/Longitude, Timezone/TimeStd/TimeDst, DeviceName, Hostname, IPAddress1-4, LedPower/LedState, SerialLog 3/WebLog 3

## A4 — Nettoyage de la section du `.h`
- [x] `USE_I2C`, `USE_DS18x20`, `USE_LIGHT`/WS2812 retirés de la section du différentiel ; `#ifdef/#undef USER_TEMPLATE` — preuve : `user_config_override.h` (commit `379c515f0`) : `#undef USE_I2C`, `#undef USE_DS18x20`, `#ifdef/#undef USER_TEMPLATE` ; écart : `USE_LIGHT`/`USE_WS2812` GARDÉS, car `configDevices.be` (`light.set`) et `ledsPanelFonctions.be` (`Leds()`) les citent (commentaire dans la section)
- [x] Build de l'env réussi, taille du firmware notée avant/après — preuve : après = 2 589 735 o (journal `20261102-005657-…-compiler.log`) ; pas de mesure d'avant : le seul build antérieur (`20261101-035949`) s'est arrêté sans rien produire

## A5 — Calibrage protégé
- [x] Clé persist `diverses.energie` (activation, calibrage PowerCal/VoltageCal/CurrentCal) ; modèle d'assistant et schéma mis à jour — preuve : `_persist.json` (310/15963/124194), `modele_persist.json`, `genere_schema_persist.py --valide` 8 OK, `test_assistant_persist_modele.py` VERT
- [x] Au démarrage différé (`controleGeneral` `demarrageDiffere`), si les trois valeurs lues sont les défauts BL0942 → réapplication du calibrage du persist + log `info` ; sinon rien (un recalibrage manuel est respecté) — preuve : `energieFonctions.verifieCalibrage`, appelé 60 s après le chargement par `controleEnergie.be` ; ÉCART : minuterie du driver au lieu de `controleGeneral.demarrageDiffere`, pour ne pas toucher au socle
- [x] Banc Berry : défauts → réappliqué ; valeurs propres → intact ; clé absente → rien ; témoin rouge sur un mutant — preuve : `banc_energie.py` : défauts, valeurs propres, une seule valeur propre, clé et bloc absents ; témoin « calibrage écrasé » rouge

## A6 — Module `energieFonctions` (relevés et stockage)
- [x] `data/fs/energieFonctions.be` solidifié (import du module dans ses propres fonctions) : note de `ENERGY.Total` par `tasmota.read_sensors()` à chaque heure pleine (cron armé à `Time#Initialized`, garde heure valide) — preuve : `solidifie_et_compile_berry.py` rc 0 sur `energieFonctions.be` et `controleEnergie.be` ; ÉCART : cron toutes les 5 min (rattrape une heure manquée) au lieu d'heure pleine + `Time#Initialized` seul
- [x] kWh et € par heure (aujourd'hui), par jour (mois en cours, archives des mois clos), par mois (24 mois glissants) en petits fichiers `/energie/*.json` écrits de façon atomique ; dernière note relue après redémarrage ; `Total` en baisse ignoré avec log `erreur` — preuve : `banc_energie.py` vert ; ÉCART : un seul `etat.json` (heures, jours, mois, note) écrit atomiquement, pour qu'une coupure ne compte pas deux fois une heure ; Wh et dix-millièmes d'euro entiers
- [x] Prix : liste (date d'effet, €/kWh TTC) dans `/energie/prix.json`, chaque période valorisée au prix en vigueur au moment de la note — preuve : `energieFonctions.ajoutePrix`, `prixA`, banc : prix futur, antidaté, remplacement, passé intact ; témoin rouge
- [x] Purge : avant écriture, si `UfsFree` sous le seuil, effacement des archives les plus anciennes ; borne dure du nombre d'archives — preuve : `energieFonctions.purge` ; banc : plus ancien d'abord, arrêt quand la place revient, borne 24, prix jamais purgés ; témoin rouge
- [x] Courbe de puissance 24 h en RAM dans un `bytes` (pas 5 min, 2 o par point) — preuve : `courbeVide`/`notePuissance`, 576 o ; banc vert
- [x] Banc Berry (faux horloge et faux SENSOR) : heure pleine, changement de jour/mois, redémarrage, Total en baisse, changement de prix, heure d'été/hiver, purge ; témoins rouges — preuve : `banc_energie.py` : 8 témoins rouges, heures d'été et d'hiver, coupure, compteur en baisse ET compteur rétabli à la main (écart invraisemblable non compté, ajout)

## A7 — Page `/energie` (disposition B)
- [x] Maquette du bouton ou lien de l'accueil montrée à l'utilisateur, choix noté — preuve : `outils_docs/jauges/bouton_energie_accueil.png` (vraie page de la carte + bouton) ; choix de l'utilisateur du 2026-11-02 : bouton « Énergie » au-dessus de « Configuration »
- [x] Route GET et POST (prix) déclarées par `controleWeb` si `diverses.energie.activation` ; `check_privileged_access` ; page `data/sd/{html,css,js}/energie.*` en SVG (4 tuiles, 3 barres, courbe 24 h, prix + rappel > 6 mois) ; rafraîchissement 10 s par une petite route JSON — preuve : `banc_energie.py` COMPLET OK (accès refusé sur GET et POST, témoins rouges « acces non controle » et « acces au prix non controle », POST du prix, rappel, valeurs tracées) ; `energie.js` : `setInterval(direct, 10000)` sur `?f=direct` ; ÉCART : routes déclarées par `controleEnergie::CONTROLE_ENERGIE.web_add_handler`, pas `controleWeb`, pour ne rien ajouter aux autres cartes ; garde d'activation dans `controleEnergie_init`. Sur banc seulement : l'essai sur la carte relève de A8
- [x] Fichiers embarqués sur le seul différentiel (liste `page_energie` dans `[berry_commun]`, exclue des autres envs) ; module ajouté à `custom_berry_solidify` de l'env — preuve : `[berry_commun] page_energie`, ajoutée aux exclusions des autres envs (P4 et cuve compris) ; modules dans `custom_berry_solidify` du différentiel ; `banc_demarrage` du différentiel VERT
- [x] Banc `banc_energie.py` (Berry + rendu Chrome à 340 px et téléphone) : valeurs tracées = valeurs servies ; témoin rouge — preuve : `banc_energie.py` COMPLET OK : valeurs tracées = servies, comparaison à l'accueil réel relevé le 2026-11-02 (0 W, 0,000 A, 0,00, 50 Hz, Wh sous 1 kWh, heure en cours = Today), témoin rouge ; capture à 340 px relue

## A8 — Mise en service sur la carte (avec l'utilisateur)
- [x] AVANT tout flash (demande de l'utilisateur, 2026-11-02) : sauvegarde relue dans `%LOCALAPPDATA%\outils_tasmota\differentiel\` : firmware officiel `release-15.0.1/tasmota32-FR.bin` (2 096 272 o, celui de retour arrière en OTA), config `/dl`, fichiers du FS (`/.drvset003`, `/.settings`, `/.settings.lkg`, `/_persist.json`) ; PAS de lecture série : l'utilisateur ne peut pas brancher la carte en USB (2026-11-02), donc copie du firmware NON exacte et aucun secours série si la carte ne redémarre plus ; retour arrière par OTA écrit avant le flash — preuve : `sauvegarde-20261102-184319\` : binaire 2 096 272 o (0xE9), `config.dmp` 4 672 o, `.drvset003` 536 o contenant 310, 15963 et 124194, `SHA256.txt`, `releve.txt` (Total 564,207), `RETOUR_ARRIERE.txt`. Sauvegarde de 18:43 : à refaire pour la config et le relevé juste avant l'envoi (étape suivante)
- [x] Juste avant : `Restart 1` (Total écrit en flash), nouveau relevé `EnergyTotal`/calibrage/minuteries, config `/dl` sauvegardée — preuve : `avant-flash-20261102-192551\` : charge 37-41 W, 0,18 A, facteur 0,99, Total 564,209 ; config et FS relus. Manque : `AdcParam1` absent du relevé (retrouvé dans `.settings`, voir lessons)
- [x] Partitions de la carte = celles de l'env, safeboot présent — preuve : capture de l'assistant de partitions par l'utilisateur (2026-11-02) : safeboot 832 Ko (97 %), app0 2 880 Ko (71 %), fs 320 Ko, disposition Safeboot = `esp32_partition_app2880k_fs320k.csv` (0xD0000 / 0x2D0000 / 0x50000) ; démarrage réel du safeboot NON éprouvé
- [x] Firmware puis FS envoyés en OTA par la page build ; carte revenue sur 192.168.0.49 — preuve : 16.0.0.2 du 2026-11-02 20:57 sur 192.168.0.49, FS envoyé par la page. ÉCARTS : boucle `Hostname` de `autoexec.bat`, `partition_wizard`, tas à 24-32 Ko avec `discovery` (mis à OFF) ; un envoi coupé (WinError 10054) a laissé la carte en safeboot, relancé à la main par `/up` + `/u2`
- [x] Calibrage réappliqué (automatique A5, sinon `Backlog VoltageCal…`) et `EnergyTotal` rétabli puis relu ; mesure d'une charge connue comparée à avant — preuve : 310/15963/124194 et Total conservés sans rejeu (564,246) ; sous 37-39 W : 0,172-0,18 A, facteur 0,99 = avant
- [ ] Minuteries actives (`Timers`), bouton et relais bistable essayés, tas libre (`Status 4`) noté et > 40 Ko
- [ ] Page `/energie` et bouton d'accueil vérifiés par capture ; première heure pleine notée dans `/energie/`

## Points ouverts de la mise en service
- [ ] [conversation] Thermomètre : GPIO34 lit ~2,2 V au lieu de 0,64 V depuis l'envoi du FS (15 °C au lieu de 27 °C) ; `AdcParam1` rétabli (B 15000), `SetOption146` écarté, cause inconnue
- [ ] [conversation] Relais trouvé ouvert deux fois (19:46, avant 20:07) sans cause trouvée ; pas revu depuis 20:08
- [ ] [conversation] Essai physique du bouton (relais lié) et du relais bistable par l'utilisateur, puis cocher l'étape des minuteries
- [ ] [conversation] Décision : `discovery` reste OFF sur cette carte (sans PSRAM, rafale MQTT = échecs d'allocation et redémarrages) ; page `/discovery` perdue ici
- [ ] [projet] `implicit_cache` : `be_string.c.o` repris du cache alors que `be_const_strtab_def.h` avait changé ; cause exacte à trouver dans `build/test_scons_cache.py`

## A9 — Documentation et commit
- [x] `outils_docs/README.md` (mode d'emploi de la page, restauration du calibrage), carte des documents de `CLAUDE.md`, exception consignée dans `tasks/lessons.md` ; `verifie_references_docs.py` code 0 — preuve : section « La page Énergie » du README, carte de `CLAUDE.md`, `verifie_references_docs.py` code 0 (exception consignée dans le plan, le contexte en tête)
- [x] Relecture `relecteur-berry` des `.be` modifiés ; commit — preuve : relecture du 2026-11-02 sans défaut bloquant, 3 points mineurs corrigés (etat.json abîmé mis de côté, date contrôlée, fermeture de réponse) ; `banc_energie.py` COMPLET OK ; commit de ce même jour

## A10 — Retour au plan « jauges-cuve »
- [ ] Reprendre `tasks/plans/jauges-cuve.md` : icône B envoyée aux deux cartes (FS), registre 4708, captures de l'accueil et de `/cuve`, bouton Retour

## Améliorations restantes
- [ ] [projet] Étendre la page Énergie aux autres cartes à bloc `ENERGY` (module déjà générique)
- [ ] [projet] Outil de la page build : sauvegarder et rétablir `/.drvset003` (calibrage + compteur) autour d'un flash série
- [ ] [projet] Le D3T n'est pas un différentiel 30 mA : renommer l'env et le dossier (`interrupteur-differentiel`) si l'utilisateur le souhaite

## Vérification
- Bancs : `banc_energie.py`, banc du calibrage, `banc_demarrage.py` (instantané du différentiel), `test_assistant_persist_modele.py`, `verifie_berry.py` (hook) ; témoins rouges sur mutants.
- Build de l'env (A1, A4) ; jamais en parallèle d'un build de l'utilisateur.
- Sur la carte (A8) : `Status 2/4/10`, `VoltageCal/CurrentCal/PowerCal`, `EnergyTotal`, `Timers`, page `/energie` en capture, fichiers `/energie/` après une heure pleine.
