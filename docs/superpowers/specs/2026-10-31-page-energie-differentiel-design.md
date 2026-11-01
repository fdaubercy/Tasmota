# Page « Énergie » du différentiel — conception

Date : 2026-10-31. Décisions de l'utilisateur prises en conversation ; les choix marqués
*(choix du concepteur)* n'ont pas été discutés et restent révisables.

## 1. Intention

Suivre la consommation électrique mesurée par la carte du différentiel (bureau) sur une page
dédiée de la carte : combien par heure aujourd'hui, par jour ce mois-ci, par mois sur un an, et ce
que cela coûte. La page doit fonctionner **sans le Raspberry Pi** : la carte garde elle-même son
historique. Le dispositif doit pouvoir resservir plus tard à d'autres cartes qui ont un bloc
`ENERGY` dans leur JSON SENSOR (« les cartes comme le différentiel »).

## 2. Ce qui existe (vérifié sur la carte le 2026-10-31)

- Carte : interrupteur différentiel Nous D3T, **ESP32 classique sans PSRAM**, flash 4 Mo,
  système de fichiers de **320 Ko** (300 Ko libres sous le firmware actuel), IP 192.168.0.49,
  topic MQTT `bureau/pc`, `telePeriod` 300 s, redémarrage quotidien à 01:00 (persist).
- Mesure : puce **BL0942** en UART 4800 bauds (GPIO13 = `GPIO_BL0942_RX`, code 8160, « capteur1
  Consommation Electrique » du persist ; GPIO14 = `GPIO_TXD`, code 3200, **absent du persist** :
  sans lui la puce n'est pas interrogée, voir l'audit). Calibrage propre à la carte (phase 1,
  fichier `/.drvset003` du système de fichiers) : PowerCal 310, VoltageCal 15963, CurrentCal
  124194 ; sauvegardé le 2026-10-31 dans `%LOCALAPPDATA%\outils_tasmota\differentiel\`. JSON SENSOR réel :
  `ENERGY: {TotalStartTime: "2024-08-26T06:48:48", Total: 564.205, Yesterday, Today, Power,
  ApparentPower, ReactivePower, Factor, Frequency, Voltage, Current}`.
- La carte tourne sous **Tasmota 15.0.1 d'origine** (release-tasmota32, 2025-06-14), Berry
  presque vide : le firmware du fork n'y est **pas** installé. Env du fork :
  `[env:tasmota32-bureau-interrupteur-differentiel]` (`platformio_tasmota_cenv.ini`), dossier
  `data/bureau/tasmota32-interrupteur-differentiel/`, section `FIRMWARE_ESP32_BUREAU_DISJONCTEUR_DIFFERENTIEL`
  de `tasmota/user_config_override.h` (même gabarit GPIO que la carte).
- Dans le fork : `historiqueFonctions.be` / `graphiquesFonctions.be` / ECharts sont **exclus** de
  cet env (conçus pour S3/P4 avec PSRAM). ECharts compressé pèse 368 Ko : il **ne tient pas** dans
  320 Ko.

## 3. Décisions de l'utilisateur

1. **Valeurs suivies** : consommation (kWh), puissance (W), courant (A), facteur de puissance,
   fréquence. **Pas** la tension.
2. **Historique gardé par la carte**, en flash, page utilisable sans le Pi.
3. **Disposition B** (maquette `outils_docs/jauges/dispositions_page_energie.html`) : en haut 4
   tuiles (puissance, courant, facteur en cadran, fréquence), puis empilés : *aujourd'hui par
   heure* (24 barres), *ce mois par jour* (barres), *12 derniers mois* (12 barres), chacun avec
   son total en kWh ; en bas la ligne du prix.
4. **Abonnement de base**, sans heures creuses : une seule couleur de barres.
5. **Prix du kWh saisi à la main** sur la page, **avec sa date d'effet** ; la carte garde la
   liste des prix successifs et calcule chaque période **au prix en vigueur à cette période** (le
   passé n'est jamais recalculé au nouveau prix). **Rappel** visible sur la page si le dernier
   prix a plus de 6 mois. Pas de mise à jour automatique en ligne.
6. **Saturation du système de fichiers** : avant d'écrire, si la place libre approche de la
   saturation, effacer d'abord les relevés les plus anciens.
7. Règle de graphique : quantité sur une période → barres ; grandeur instantanée → courbe ;
   rapport borné → cadran ; valeur quasi constante → simple valeur.

## 4. Comment la consommation est calculée

- Source unique : **`ENERGY.Total`** (kWh cumulés, croissant, gardé par Tasmota dans ses
  réglages, survit aux redémarrages). Consommation d'une période = `Total` à la fin − `Total` au
  début. `Today`/`Yesterday` ne sont pas utilisés (remise à zéro à minuit, piégée par un
  redémarrage à cette heure-là).
- La carte note `Total` à chaque **changement d'heure** (heure locale) ; l'écart avec la note
  précédente donne la consommation de l'heure écoulée, versée aussi au jour et au mois en cours.
- **Redémarrage ou coupure** : la dernière note est relue en flash ; si une ou plusieurs heures
  manquent, l'écart couvre l'intervalle entier et il est **porté à l'heure où la carte le
  constate** *(choix du concepteur : pas de répartition fictive sur les heures manquées ; la
  journée et le mois restent justes)*.
- **`Total` qui baisse** (remise à zéro par `EnergyTotal 0`, réglages perdus) : l'écart négatif
  n'est pas compté, la note repart de la nouvelle valeur, et un log `erreur` le signale.
- Les valeurs instantanées (puissance, courant, facteur, fréquence) viennent du même JSON
  SENSOR, lues à l'affichage.
- **Lecture vivante** *(choix du concepteur)* : la note est prise par `tasmota.read_sensors()` au
  moment du changement d'heure (cron à hh:00:00), jamais dans le dernier message MQTT
  (`telePeriod` 300 s, jusqu'à 5 min de retard).
- **Heure** *(choix du concepteur)* : aucune note tant que l'heure n'est pas valide (NTP) ; les
  périodes sont en **heure locale** (ce que lit l'utilisateur). Passage à l'heure d'hiver : l'heure
  répétée est versée dans la même case ; passage à l'heure d'été : l'heure sautée reste vide.
- **Redémarrages** : le redémarrage quotidien de 01:00 est logiciel, Tasmota garde alors `Total`
  dans sa mémoire RTC : pas de perte attendue (à vérifier sur la carte). Une coupure secteur peut
  faire perdre la consommation non encore sauvegardée par Tasmota : elle est absente de
  l'historique, sans correction *(choix du concepteur)*.
- **Coût** *(choix du concepteur)* : chaque consommation notée est valorisée au prix en vigueur
  à cet instant, et le coût en € est **gardé à côté des kWh** pour l'heure, le jour et le mois :
  un changement de prix ne touche jamais le passé, et un mois à cheval sur deux prix est juste.
  Avant le premier prix saisi, le coût s'affiche « — ». Prix en € TTC par kWh.

## 5. Ce qui est gardé, où

| Donnée | Profondeur | Support |
|---|---|---|
| consommation par heure | les 24 heures d'aujourd'hui | flash |
| consommation par jour | le mois en cours (≤ 31) | flash |
| consommation par mois | 12 derniers mois | flash |
| dernière note de `Total` (valeur, date) | 1 | flash |
| liste des prix (date d'effet, €/kWh) | toutes | flash (persist ou fichier) |
| courbe de puissance des 24 h | 24 h glissantes, sous les trois graphiques de consommation (décision de l'utilisateur) ; repart vide après le redémarrage de 01:00 | RAM |

Quelques centaines d'octets en tout. Écritures limitées (usure) : une par heure au plus.
Purge (décision 6) : les mois les plus anciens partent d'abord ; seuil, mesure de la place
libre et format des fichiers laissés au constructeur.

## 6. La page

- Route dédiée de la carte (modèle : `/cuve`, `data/fs/cuvePageFonctions.be`), module Berry
  **solidifié**, page en `data/sd/{html,css,js}/` (règle du dépôt : Berry solidifié, HTML dans
  `data/sd`), fichiers embarqués **seulement** dans les envs qui s'en servent
  (`custom_files_exclude` des autres, comme `page_cuve`).
- **Sans ECharts** : graphiques en SVG dessinés par un petit script de la page (barres, courbe,
  cadran façon modèle H du catalogue) *(choix du concepteur, imposé par les 320 Ko)*.
- Rafraîchissement des tuiles toutes les 10 s par une petite route JSON *(choix du concepteur)*.
- Saisie d'un prix : formulaire sur la page (montant, date d'effet), enregistré par un POST
  contrôlé (`check_privileged_access`), refus des valeurs aberrantes.
- Accès *(choix du concepteur)* : page et route JSON soumises à `check_privileged_access`, comme
  `/cuve`.
- Réutilisation *(choix du concepteur)* : module générique qui lit le bloc `ENERGY` du JSON
  SENSOR ; fichiers de données nommés par instance ; activé sur le seul différentiel.

## 7. Mise en service sur la carte (étape à risque)

Passer la carte du Tasmota d'origine au firmware du fork change les réglages de Tasmota
(`CFG_HOLDER` différent) : **le compteur `Total` (564 kWh) et le calibrage de la BL0942
risquent d'être remis à zéro**. Avant le flash : relever `EnergyTotal`, `PowerCal`,
`VoltageCal`, `CurrentCal` (et `PowerSet`/`VoltageSet`/`CurrentSet` s'ils servent), sauvegarder
la configuration ; après : les rétablir et comparer une mesure (puissance d'une charge connue)
avant/après. Le flash et le rétablissement se font avec l'utilisateur, jamais seuls.

Première étape du plan *(choix du concepteur)* : compiler l'env du différentiel et vérifier que
le firmware du fork tient dans la partition (OTA comprise) et ce qu'il laisse au système de
fichiers, avant d'écrire la page.

## 8. Hors champ

Tension ; heures creuses ; mise à jour automatique du prix ; abonnement (part fixe) ; Pi,
InfluxDB, Grafana ; export de données ; autres cartes que le différentiel (le module est écrit
pour être réutilisable, mais n'est activé que sur lui).

## 9. Laissé au constructeur

Format exact des fichiers, noms des routes et du module, seuil de purge, découpage du script de
page, bancs de test (sur le modèle de `banc_cuve_page.py` : Berry + rendu Chrome), lien depuis
l'accueil (bouton ou icône, à montrer à l'utilisateur avant de le poser).
