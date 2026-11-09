---
chantier: energie-differentiel
titre: Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie » (disposition B)
statut: actif
cree: 2026-10-31
maj: 2026-11-09
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
- [x] Firmware du fork de l'env `tasmota32-bureau-interrupteur-energie` compilé (page build, aucun autre build en cours) ; taille ≤ 2 880 Ko — preuve : journal `20261102-005657-…-compiler.log` : SUCCESS, code de sortie 0, Flash 87,8 % (2 589 735 o sur 2 949 120), RAM statique 76 476 o
- [x] Image du FS ≤ 320 Ko avec marge pour les données (place libre mesurée, à comparer à `energieFonctions.SEUIL_KO`) : à relever au `buildfs` de A7, `littlefs.bin` du build ci-dessus n'existant plus — preuve : `buildfs` du 2026-11-02 (journal `20261102-072240`) : 26 fichiers, 155 988 o, soit 224 Ko en blocs de 4 Ko ; ~96 Ko libres estimés sur 320 (métadonnées non comptées), à relire par `UfsFree` à A8 ; seuil de purge 40 Ko
- [x] Compatibilité ESP32-U4WDH (mono ou double cœur) du firmware du fork vérifiée (doc Espressif/Tasmota, `CONFIG_FREERTOS_UNICORE`, build `tasmota32` actuel de la carte) — preuve : `Status 2` de la carte = `release-tasmota32` (binaire bi-cœur, que la doc Tasmota dit inopérant sur une puce mono-cœur) et matériel « ESP32-U4WDH-D v3.1 » ; Espressif PCN-2021-021 : U4WDH passée en bi-cœur fin 2021 → build `esp32` standard de l'env valable
- [x] Unités confirmées sur la carte : `UfsFree` (Ko), `EnergyTotal` (Wh ou kWh) et sa relecture — preuve : `UfsFree` → 300, `UfsSize` → 320 (Ko) ; `xdrv_03_esp32_energy.ino` : `EnergyTotal <v>` divise par 1000 (Wh → kWh), 2e paramètre = date de début ; relecture `EnergyTotal` → `{"Total":564.205}`

## A2 — Persist du différentiel (E1 à E5)
- [x] Groupe de broches techniques dans `modules.differentiel.environnement` : TX GPIO14 (3200), RX GPIO13 (8160), 2e fil du relais bistable GPIO12 (9313) ; `capteurs.capteur1` et `relais.relai2` retirés — preuve : `_persist.json` groupe `pinsTechniques` (relaiBistable2 GPIO12/9312 id 2, rxBL0942 GPIO13/8160, txBL0942 GPIO14/3200) ; relai2 retiré, capteur1 neutralisé (OFF, pin -1)
- [x] `capteur2` désactivé (pin -1) ; `bouton1.relaisLie` = relai1 en bascule ; `channel`/`nbLeds` retirés de `relai1` — preuve : `capteur2` OFF pin -1 ; `bouton1.relaisLie` = `ids [1]`, `delai 0`, `type Switch` ; `relai1` sans `channel`/`nbLeds`
- [x] Gabarit reconstruit à blanc (banc ou script) identique au gabarit réel de la carte — preuve : banc de démarrage avec impression du gabarit → `[32,1,9312,1,1,320,1,1,9313,8160,3200,544,1,…,4736,…]` = `Template` relevé sur la carte ; témoin sur l'ancien persist : index 10 → 1 au lieu de 3200
- [x] `banc_demarrage` : écart de l'instantané du différentiel relu (plus de `Switch1/2#Action`) puis ré-enregistré — preuve : instantané ré-enregistré (règles `Button1#Action, Mqtt, Mqtt, System, System, Time, Wifi, Wifi`, plus de `Switch1/2#Action`) ; `banc_demarrage.py --carte tasmota32-bureau-interrupteur-energie` → VERT
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
- [x] Minuteries actives (`Timers`), bouton et relais bistable essayés, tas libre (`Status 4`) noté et > 40 Ko — preuve : `Timers` ON, identiques au relevé d'avant flash ; bouton et relais bistable essayés par l'utilisateur (confirmé le 2026-11-02) ; `Status 4` Heap 52 Ko, `Status 11` 58 Ko à 21:26
- [x] Page `/energie` et bouton d'accueil vérifiés par capture ; première heure pleine notée dans `/energie/` — preuve : captures `accueil.png` et `energie.png` (`avant-flash-20261102-192551\`) ; `/energie/etat.json` : 27 Wh notés sur l'heure 20, compteur 564246 Wh, note à 21:00 du 2026-11-02

## Points ouverts de la mise en service
- [x] [conversation] Relais trouvé ouvert deux fois (19:46, avant 20:07) sans cause trouvée ; pas revu depuis 20:08 — preuve : recherche arrêtée à la demande de l'utilisateur (2026-11-02), cause non trouvée
- [x] [conversation] Essai physique du bouton (relais lié) et du relais bistable par l'utilisateur, puis cocher l'étape des minuteries — preuve : confirmé par l'utilisateur le 2026-11-02
- [x] [conversation] Décision : `discovery` reste OFF sur cette carte (sans PSRAM, rafale MQTT = échecs d'allocation et redémarrages) ; page `/discovery` perdue ici — preuve : décision de l'utilisateur du 2026-11-02

## A9 — Documentation et commit
- [x] `outils_docs/README.md` (mode d'emploi de la page, restauration du calibrage), carte des documents de `CLAUDE.md`, exception consignée dans `tasks/lessons.md` ; `verifie_references_docs.py` code 0 — preuve : section « La page Énergie » du README, carte de `CLAUDE.md`, `verifie_references_docs.py` code 0 (exception consignée dans le plan, le contexte en tête)
- [x] Relecture `relecteur-berry` des `.be` modifiés ; commit — preuve : relecture du 2026-11-02 sans défaut bloquant, 3 points mineurs corrigés (etat.json abîmé mis de côté, date contrôlée, fermeture de réponse) ; `banc_energie.py` COMPLET OK ; commit de ce même jour

## A10 — Retour au plan « jauges-cuve »
- [ ] Reprendre `tasks/plans/jauges-cuve.md` : icône B envoyée aux deux cartes (FS), registre 4708, captures de l'accueil et de `/cuve`, bouton Retour

## A11 — Remarques de l'utilisateur du 2026-11-02 (soir)
- [x] Prix : ligne, liste des tarifs et saisie déplacées dans une sous-partie de la page Configuration (bouton « Tarifs de l'électricité ») ; sous la liste, en plus petit, la ligne du prix en vigueur ; sur `/energie`, seulement l'alerte et, en petit, l'endroit où régler le prix ; banc vert, capture sur la carte — preuve : bouton « Tarifs de l'électricité » sur `/cn`, liste et prix en petit sur `/energie?f=tarifs`, lieu en petit sur `/energie` (captures du 2026-11-02 23:42) ; `banc_energie.py` COMPLET OK
- [x] Saisie d'un tarif à une date : abonnement Base (un prix) ou HC/HP (les 2 tarifs, et les heures creuses, sans lesquelles l'heure n'a pas de prix) ; chaque heure notée valorisée au tarif de son heure ; anciens tarifs inchangés ; banc avec témoins rouges — preuve : `banc_energie.py` COMPLET OK (4 nouveaux témoins rouges) ; sur la carte, POST avec plages invalides refusé (400) et `prix.json` intact. Formulaire HC/HP non enregistré sur la vraie carte, pour ne pas changer le vrai tarif
- [x] Date du prix au format jj/mm/aaaa, vue sur la carte (code et banc faits : `energie.js`, `banc_energie.py`) — preuve : « Prix : 0,1823 €/kWh depuis le 02/11/2026 » sur la carte (capture)
- [x] « ADC1 Température » remplacée par « Température ambiante », vue sur la carte (code fait : `controleEnergie.be::web_sensor`, `WebSensor2 0` dans `autoexec.bat`) — preuve : `Température ambiante{m}15,0 °C` sur l'accueil de la carte
- [ ] Thermomètre corrigé (« n'oublie pas la correction des paramètres ») : GPIO34 lit ~2,2 V au lieu de 0,64 V depuis l'envoi du FS (15 °C au lieu de 27 °C) ; `AdcParam1` rétabli (B 15000), `SetOption146` écarté ; cause inconnue, il faut la température réelle près du boîtier
- [x] Espace libre du FS revu (la page affichait 0 Ko) — preuve : 52 Ko libres, confirmés par une écriture réelle ; le 0 venait d'une saturation mémoire
- [x] `discovery` reste OFF sur cette carte — preuve : décision de l'utilisateur, `_persist.json`
- [x] Recherche des 2 ouvertures de relais arrêtée — preuve : demande de l'utilisateur, cause non trouvée
- [x] `implicit_cache` : correctif prouvé sur un vrai build (cause trouvée : `gen-berry-structures` réécrit `lib/libesp32/berry/generate/` après le LDF, date déjà mémorisée ; `clear_memoized_values()` dans `build/post_lto_parallele.py` ; `build/test_scons_cache.py` vert) ; reste : `be_string` recompilé sans purge, aucun `undefined reference` — preuve : build du 2026-11-02 sans purge : `be_string.c.o` recompilé, édition de liens réussie, aucun `undefined reference`
- [x] Outil `.drvset003` de la page build éprouvé sur la vraie carte (code et banc faits : `build_drvset.py`, `test_build_drvset.py` ; mode d'emploi au README) — preuve : copie (536 o) puis rétablissement sur la carte, `Restart 99`, relu 310/15963/124194, Total 564,246 ; l'essai a révélé un défaut (`Restart 99` ne répond pas), corrigé et ajouté au banc. Le passage complet par un vrai flash série n'a pas été fait
- [x] Env et dossier renommés, le D3T n'étant pas un différentiel 30 mA — preuve : env `tasmota32-bureau-interrupteur-energie`, dossier `data/bureau/tasmota32-interrupteur-energie`
- [x] Envoi OTA coupé (`WinError 10054`) juste après la bascule en safeboot, carte laissée en safeboot — preuve : cause = délai (3 fois sur 3 à 0,1 s de la bascule, même envoi réussi 1 min après, `fsz` hors de cause) ; 4 essais espacés de 10 s dans `build_ota_firmware.py::envoie_firmware_ota`, `test_build_ota_fs.py` VERT. Pas encore éprouvé sur la vraie carte
- [x] Commentaire de la section du `.h` encore à l'ancien nom (« firmware tasmota32-interrupteur-differentiel-bureau ») corrigé hors build — preuve : « Options for firmware tasmota32-bureau-interrupteur-energie » dans `user_config_override.h`, et l'en-tête de l'env dans le cenv (2026-11-03)
- [x] Tarif HC/HP essayé par l'utilisateur sur la carte — preuve : « Tarif HC/HP ==> OK » (utilisateur, 2026-11-03)
- [x] 0 W relais ON : normal — preuve : appareil arrêté par l'utilisateur (2026-11-03)
- [x] Noms raccourcis (le SSID du point d'accès faisait 39 caractères pour 32 permis) : nom d'hôte, `PROJECT` et client MQTT `DISJONCTEUR-DIFF-BUREAU`, SSID du Range Extender `DISJONCTEUR-DIFF-BUREAU-GATEWAY` (31 caractères) ; topic `bureau/pc` inchangé — preuve : `user_config_override.h` et `_persist.json` du différentiel (2026-11-03). Pas encore sur la carte : il faut le prochain envoi du firmware et du FS
- [x] `banc_demarrage` vert malgré le chantier Ethernet : seul écart, la règle `Eth` ajoutée à toutes les cartes par `controleGeneral.be` — preuve : instantanés ré-enregistrés à la demande de l'utilisateur, une ligne par carte, `banc_demarrage.py` VERT (2026-11-03). Instantanés à commiter avec le chantier Ethernet
- [x] Inventaire des `.drvset*` retenu dans un fichier — preuve : `outils_docs/FICHIERS_DRVSET.md`, `verifie_references_docs.py` 0 défaut
- [x] Explication de `.drvset003` (données, rôle, chargement, paramétrage) et rapport Extension Manager (intérêt, outil possible par l'annuaire, existant, à mettre en place) rendus à l'utilisateur — preuve : compte rendu du 2026-11-02 ; `FICHIERS_DRVSET.md`, onglet Aide
- [x] Banc `test_assistant_persist_generation.py` vert : bloc énergie nommé dans ses tolérances, seul reste l'écart `drivers.Ethernet` de l'autre chantier (cave) — preuve : tolérance `drivers.Ethernet.*` étendue à la cave S3 (seule carte à W5500, ON) ; `test_assistant_persist_generation.py` VERT (2026-11-03)

## A12 — Onglet « Sauvegarde configuration » de la page build
- [x] Modèle choisi par l'utilisateur parmi les maquettes `outils_docs/sauvegarde_config/` (A, B, C) — preuve : modèle **B** choisi le 2026-11-03
- [x] Nom de l'onglet : « Sauvegarde configuration » plutôt que « Sauvegardes » ou « Sauvegarde drvsetXXX » (une sauvegarde `/dl` porte les Settings ET les `.drvset*`) — preuve : demande de l'utilisateur du 2026-11-03
- [x] Lecture des paramètres d'un `.dmp` par `decode-config` (tasmota/decode-config, LGPL-3.0, PyPI 16.0.0.0) plutôt qu'un décodeur maison : sait lire un `.dmp`, prendre un JSON modifié et écrire un nouveau `.dmp` hors ligne. Disposition de Settings inchangée depuis 15.6.0.3 (`tasmota_types.h` identique entre 16.0.0.1 et 16.0.0.2, vérifié le 2026-11-03) : `--ignore-warnings` seulement pour les versions vérifiées — preuve : `outils_pc/decode_config.py`, commit `6e15fc934` ; suite dans `tasks/plans/sauvegarde-config-cartes.md`
- [x] Sauvegarder la configuration d'une carte de la liste des envs (`/dl`), dans `outils_docs/sauvegardes_cartes/<env>/`, ignoré par git (mots de passe, dépôt public) — preuve : repris et fait dans `tasks/plans/sauvegarde-config-cartes.md` (commit `6e15fc934`) ; essai de restauration sur la vraie carte suivi là-bas (A7)
- [x] Restaurer une sauvegarde sur la carte, après une nouvelle sauvegarde et la confirmation des écarts — preuve : repris et fait dans `tasks/plans/sauvegarde-config-cartes.md` (commit `6e15fc934`) ; essai de restauration sur la vraie carte suivi là-bas (A7)
- [x] Modifier une sauvegarde paramètre par paramètre et l'enregistrer dans un nouveau fichier ; mots de passe masqués ; version inconnue = restaurable mais pas éditable — preuve : repris et fait dans `tasks/plans/sauvegarde-config-cartes.md` (commit `6e15fc934`) ; essai de restauration sur la vraie carte suivi là-bas (A7)
- [x] Bancs (format `/dl` : XOR, CRC, tar ; carte simulée) et sonde Chrome ; essai sur la vraie carte ; mode d'emploi au README — preuve : repris et fait dans `tasks/plans/sauvegarde-config-cartes.md` (commit `6e15fc934`) ; essai de restauration sur la vraie carte suivi là-bas (A7)

## A13 — Onglet « Aide » de la page build
- [x] Onglet Aide : fichiers `.drvset*` (rôle, contenu, chargement, paramétrage), `.drvset003` et calibrage autour d'un flash ; sonde Chrome verte — preuve : `build_page_aide.py`, `test_build_page_defaut_chrome.py` et `test_build_page_chrome.py` VERT
- [x] Explications renvoyées aussi dans `outils_docs/FICHIERS_DRVSET.md` et au README — preuve : `FICHIERS_DRVSET.md`, renvoi dans `outils_docs/README.md`
- [x] Commentaire de la tuile « Build et téléversement » de l'annuaire à jour des nouvelles compétences (fait pour l'existant : `annuaire_registre.py` ; à compléter quand l'onglet Sauvegardes existera) ; visible après redémarrage de l'annuaire — preuve : `annuaire_registre.py` : onglet « Sauvegarde configuration » complété (fenêtre des écarts, avancement, liaison MQTT, marques de démarrage, purge à case) et onglet « Env par défaut (Platformio override) » ; `test_annuaire.py` VERT ; visible au prochain redémarrage de l'annuaire

## A14 — Outil d'édition de l'`autoexec.bat` (demande du 2026-11-03)
- [x] Conception à faire après A12 : Claude cherche l'endroit le plus approprié (page build, page Fichiers Berry, page à part…) puis pose ses questions à l'utilisateur (demande du 2026-11-03) ; outil pour modifier facilement ou ajouter des lignes dans l'`autoexec.bat` d'une carte — preuve : réponses de l'utilisateur du 2026-11-03 : **nouvel onglet de l'Assistant persist (7900)** ; après « Enregistrer », fichier du dépôt écrit (diff confirmé) **puis envoi proposé** à la carte en OTA (moteur de l'onglet Fichiers de la page build) ; avertissements : **redémarrage à répétition** (liste tirée du code Tasmota, `restart_flag = 2` : 24 fichiers, `CmndHostname` sans condition, + cas vécus), **doublon avec le persist** (`build_sauvegarde::POSEES`), **secret en clair** (dépôt public), **commande inconnue** ; **banque de commandes dans un fichier JSON du dépôt** (valeurs secrètes masquées)
- [x] Spec et plan détaillés de l'onglet (brainstorming puis plan suivi), avant tout code — en cours : maquettes `outils_docs/autoexec_bat/` (modèle C + ajout du A retenus), spec `docs/superpowers/specs/2026-11-03-onglet-autoexec-bat-design.md` relue par un constructeur ; rouges = confirmation explicite, commandes perso = modèle à champs, redémarrages tirés de la doc et du code de Tasmota ; spec validée le 2026-11-03 ; plan de réalisation : `tasks/plans/autoexec-bat.md` — preuve : réalisé par `tasks/plans/autoexec-bat.md` (A1 à A9, A11)
- [x] Analyse de chaque commande ajoutée : avertir à l'ajout de celles qui peuvent causer des redémarrages à répétition (cas vécus : boucles du différentiel, commit `b87e5cc1b`) — preuve : `autoexec_analyse.py::analyse`, plan `tasks/plans/autoexec-bat.md` A1, A2
- [x] Banque de commandes ajoutables ou modifiables proposée à l'utilisateur ; chaque commande personnalisée ajoutée par l'utilisateur complète la banque — preuve : `outils_docs/schemas/banque_autoexec.json`, plan `tasks/plans/autoexec-bat.md` A4

## Échanges du 2026-11-02 : Extension Manager
Demande : expliquer l'intérêt de l'« Extension Manager », évaluer quel outil mettre en place par l'annuaire pour créer et installer des extensions, lister l'existant et ce qui serait intéressant ici.
- Ce que c'est : module solidifié `extension_manager.be` (~790 lignes, ~11 Ko de flash), actif si `USE_EXTENSION_MANAGER`, défaut de `my_user_config.h` (compilé chez nous d'après les `.h`, non vérifié sur `.elf`). Gère des `.tapp` (zip : `manifest.json`, `autoexec.be`, `.be`) dans `/.extensions/` ; page `/ext`, bouton sur Configuration ; dépôt `https://ota.tasmota.com/extensions/` ou `<hôte OtaUrl>/extensions/`. Activer ou désactiver = renommer `.tapp` / `.tapp_` ; lancement à chaud ; le module `tapp` lance les extensions au démarrage, avant `/autoexec.be`.
- Intérêt ici : modéré à faible. Pour : pages optionnelles sans occuper le FS de toutes les cartes, activation à chaud, version. Contre : bytecode en RAM (la solidification est à coût RAM nul), place sur le FS, dépôt en ligne inutile, envoi du FS et contrôle d'identité ignorant `/.extensions/`, dépendances à `data/fs`.
- Existant au dépôt : `tasmota/berry/extensions/` : Devices_Online, Leds_Panel, LoRaWan_Decoders (108 Ko), LVGL_Panel, Partition_Wizard, Wifi_Heap_Sticker ; `tasmota/berry/modules/` : Antiburn, DisplayCalibrate, Partition_Manager, Webui_Status, bootloader, h-bridge, partition ; aussi ArtNet.tapp, drivers (PN532, ftp, ssh, tm1637, AXP), gpio_viewer, haspmota, zigbee, alexa. Côté fork : `berry/gen_tapp.py`, `data/fs/gestionFileFolder.be` sait déposer un `.tapp`. Aucun `.tapp` installé constaté.
- Intéressants : Wifi_Heap_Sticker (3 Ko) ; Devices_Online (43 Ko, limité par le NAPT) ; Leds_Panel et LVGL_Panel (37 Ko, S3/P4, redondants) ; Partition_Wizard déjà couvert par la page build. À éviter : LoRaWan_Decoders.
- Outil par l'annuaire : recommandation de ne pas le créer maintenant (~600-800 lignes). À court terme, un bouton « envoyer ce .tapp » dans l'onglet Fichiers vers `/.extensions/`. Plus tard si besoin : créer un squelette, construire le zip, installer par `/ufsu`, lister et retirer par `Br extension_manager.list_installed_ext()` / `delete_ext`.
- Non vérifié : documentation publique (404), FS réel des cartes, `.elf`, `.tapp` compressé par `gen_tapp.py` (la doc amont parle de zip non compressé).
- Décision de l'utilisateur : en attente.

## Améliorations restantes
- [ ] [projet] Étendre la page Énergie aux autres cartes à bloc `ENERGY` (module déjà générique)
- [x] [projet] Extension Manager : pas d'outil annuaire pour l'instant ; à décider : bouton « envoyer ce .tapp » dans l'onglet Fichiers vers `/.extensions/` — preuve : fait par `tasks/plans/autoexec-mqtt-tapp.md` (clos le 2026-11-09) : page « Fabrique d'extensions » de l'annuaire (création, fabrication, envoi HTTP ou MQTT vers `/.extensions/`, boutique locale de `/ext`), `fsMqtt.tapp` essayé sur la cuve
- [x] [projet] Le D3T n'est pas un différentiel 30 mA : renommer l'env et le dossier (`interrupteur-differentiel`) si l'utilisateur le souhaite — preuve : env `tasmota32-bureau-interrupteur-energie`, dossier `data/bureau/tasmota32-interrupteur-energie`, hostname et topic gardés (2026-11-02)

## Vérification
- Bancs : `banc_energie.py`, banc du calibrage, `banc_demarrage.py` (instantané du différentiel), `test_assistant_persist_modele.py`, `verifie_berry.py` (hook) ; témoins rouges sur mutants.
- Build de l'env (A1, A4) ; jamais en parallèle d'un build de l'utilisateur.
- Sur la carte (A8) : `Status 2/4/10`, `VoltageCal/CurrentCal/PowerCal`, `EnergyTotal`, `Timers`, page `/energie` en capture, fichiers `/energie/` après une heure pleine.
