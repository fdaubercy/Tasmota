---
chantier: energie-differentiel
titre: Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie » (disposition B)
statut: actif
cree: 2026-10-31
maj: 2026-11-01
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
- [ ] Firmware du fork de l'env `tasmota32-bureau-interrupteur-differentiel` compilé (page build, aucun autre build en cours) ; taille ≤ 2 880 Ko, image du FS ≤ 320 Ko avec marge pour les données
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
- [ ] `USE_I2C`, `USE_DS18x20`, `USE_LIGHT`/WS2812 retirés de la section du différentiel ; `#ifdef/#undef USER_TEMPLATE`
- [ ] Build de l'env réussi, taille du firmware notée avant/après

## A5 — Calibrage protégé
- [ ] Clé persist `diverses.energie` (activation, calibrage PowerCal/VoltageCal/CurrentCal) ; modèle d'assistant et schéma mis à jour
- [ ] Au démarrage différé (`controleGeneral` `demarrageDiffere`), si les trois valeurs lues sont les défauts BL0942 → réapplication du calibrage du persist + log `info` ; sinon rien (un recalibrage manuel est respecté)
- [ ] Banc Berry : défauts → réappliqué ; valeurs propres → intact ; clé absente → rien ; témoin rouge sur un mutant

## A6 — Module `energieFonctions` (relevés et stockage)
- [ ] `data/fs/energieFonctions.be` solidifié (import du module dans ses propres fonctions) : note de `ENERGY.Total` par `tasmota.read_sensors()` à chaque heure pleine (cron armé à `Time#Initialized`, garde heure valide)
- [ ] kWh et € par heure (aujourd'hui), par jour (mois en cours, archives des mois clos), par mois (24 mois glissants) en petits fichiers `/energie/*.json` écrits de façon atomique ; dernière note relue après redémarrage ; `Total` en baisse ignoré avec log `erreur`
- [ ] Prix : liste (date d'effet, €/kWh TTC) dans `/energie/prix.json`, chaque période valorisée au prix en vigueur au moment de la note
- [ ] Purge : avant écriture, si `UfsFree` sous le seuil, effacement des archives les plus anciennes ; borne dure du nombre d'archives
- [ ] Courbe de puissance 24 h en RAM dans un `bytes` (pas 5 min, 2 o par point)
- [ ] Banc Berry (faux horloge et faux SENSOR) : heure pleine, changement de jour/mois, redémarrage, Total en baisse, changement de prix, heure d'été/hiver, purge ; témoins rouges

## A7 — Page `/energie` (disposition B)
- [ ] Maquette du bouton ou lien de l'accueil montrée à l'utilisateur, choix noté
- [ ] Route GET et POST (prix) déclarées par `controleWeb` si `diverses.energie.activation` ; `check_privileged_access` ; page `data/sd/{html,css,js}/energie.*` en SVG (4 tuiles, 3 barres, courbe 24 h, prix + rappel > 6 mois) ; rafraîchissement 10 s par une petite route JSON
- [ ] Fichiers embarqués sur le seul différentiel (liste `page_energie` dans `[berry_commun]`, exclue des autres envs) ; module ajouté à `custom_berry_solidify` de l'env
- [ ] Banc `banc_energie.py` (Berry + rendu Chrome à 340 px et téléphone) : valeurs tracées = valeurs servies ; témoin rouge

## A8 — Mise en service sur la carte (avec l'utilisateur)
- [ ] Juste avant : `Restart 1` (Total écrit en flash), nouveau relevé `EnergyTotal`/calibrage/minuteries, config `/dl` sauvegardée
- [ ] Firmware puis FS envoyés en OTA par la page build ; carte revenue sur 192.168.0.49
- [ ] Calibrage réappliqué (automatique A5, sinon `Backlog VoltageCal…`) et `EnergyTotal` rétabli puis relu ; mesure d'une charge connue comparée à avant
- [ ] Minuteries actives (`Timers`), bouton et relais bistable essayés, tas libre (`Status 4`) noté et > 40 Ko
- [ ] Page `/energie` et bouton d'accueil vérifiés par capture ; première heure pleine notée dans `/energie/`

## A9 — Documentation et commit
- [ ] `outils_docs/README.md` (mode d'emploi de la page, restauration du calibrage), carte des documents de `CLAUDE.md`, exception consignée dans `tasks/lessons.md` ; `verifie_references_docs.py` code 0
- [ ] Relecture `relecteur-berry` des `.be` modifiés ; commit

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
