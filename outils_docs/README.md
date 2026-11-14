![Tasmota logo](/tools/logo/TASMOTA_FullLogo_Vector.svg#gh-light-mode-only)![Tasmota logo](/tools/logo/TASMOTA_FullLogo_Vector_White.svg#gh-dark-mode-only)

[![GitHub version](https://img.shields.io/github/release/arendst/Tasmota.svg)](http://ota.tasmota.com/tasmota/release)
[![GitHub download](https://img.shields.io/github/downloads/arendst/Tasmota/total.svg)](https://github.com/arendst/Tasmota/releases/latest)
[![License](https://img.shields.io/github/license/arendst/Tasmota.svg)](../LICENSE.txt)
[![Discord](https://img.shields.io/discord/479389167382691863.svg?logo=discord&logoColor=white&color=5865F2&label=Discord)](https://discord.gg/Ks2Kzd4)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-Ready--to--Code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/arendst/Tasmota)

<hr></hr>

**Vous trouverez ici la méthodologie de développement de scripts en langage BERRY pour tasmota.<br/> Les différents devices développéespour la domotique du domicile sont des forks de Tasmota personnalisés.**

<hr></hr>

> [!TIP]
> ## Index de la documentation du dépôt
> Point d'entrée unique : chaque document du fork est listé ici. Les documents restent à
> l'endroit qu'impose leur outil (Claude Code, scripts qui les génèrent) ; seul cet index les réunit.
> Les fichiers marqués *(généré)* se régénèrent par leur script : ne pas les éditer à la main.

### Règles et chantiers
- [CLAUDE.md](../CLAUDE.md) — règles du dépôt, synchro du fork, montage d'un nouveau poste, vigilances de build, charte des logs.
- [tasks/lessons.md](../tasks/lessons.md) — journal des erreurs commises et règles qui en découlent (à relire avant de coder).
- [tasks/reprise-chantier-modbus-grenier.md](../tasks/reprise-chantier-modbus-grenier.md) — chantier ModBus (⚠️ cibles = les 3 modules du **garage**, malgré le nom).
- [tasks/reprise-solidification-berry.md](../tasks/reprise-solidification-berry.md) — chantier de solidification Berry.

### Berry
- [SOLIDIFICATION_BERRY.md](SOLIDIFICATION_BERRY.md) — la solidification Berry : fonctionnement, **vérification**, paramètres, 13 pièges.
  À retenir : la ligne `Berry solidification: …` d'un build **ne prouve rien** (§5).
- [CARTE_MODULES_BERRY.md](CARTE_MODULES_BERRY.md) *(généré)* — module × carte : solidifié, importé, dépendance, garde du persist, incohérences.
- [Les logs Berry : charte et réglages](#les-logs-berry--charte-et-réglages) — plus bas dans ce fichier.
- [Inclinaison d'un volet ou d'une trappe (MPU6050)](#inclinaison-dun-volet-ou-dune-trappe-mpu6050) — capteur de position par l'angle, apprentissage des butées.
- Conception de la solidification : [design](../docs/superpowers/specs/2026-07-15-solidification-berry-design.md),
  [verdict](../docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md),
  [plan de la phase 1](../docs/superpowers/plans/2026-07-15-solidification-berry-phase1.md).

### ModBus et réseau
- [PROTOCOLE_MODBUS.md](PROTOCOLE_MODBUS.md) — référence de **conception** : TCP, 3 transports, file d'envoi, registres de la carte 16 relais (§8), synchronisation maître/esclave (§9).
- [Aide/MODBUS.md](Aide/MODBUS.md) — **mode d'emploi** : commandes d'exemple (carte 16 relais, esclaves Tasmota), trames détaillées par code de fonction, activation dans Tasmota.
- [ANALYSE_BERRY_MODBUS_DISCOVERY.md](ANALYSE_BERRY_MODBUS_DISCOVERY.md) — programmes ModBus Berry et table `/json/discovery.json`.
- [AUDIT_MODBUS_2026-09-29.md](AUDIT_MODBUS_2026-09-29.md) — audit ModBus du garage (défauts, améliorations par priorité).

### Configuration des cartes et électronique
- [schemas/persist.schema.json](schemas/persist.schema.json) *(généré)* — schéma des `_persist.json` (autocomplétion et contrôle dans VS Code).
- [Electronique/ADS1115/CABLAGE_ADS1115.md](Electronique/ADS1115/CABLAGE_ADS1115.md) — câblage de l'ADS1115 (cuve).
- [Electronique/ADS1115/CABLAGE_RUBAN_LED.md](Electronique/ADS1115/CABLAGE_RUBAN_LED.md) — câblage du ruban LED.
- PCB : la skill [pcb-tasmota](../.claude/skills/pcb-tasmota/SKILL.md) et ses agents
  [placeur-pcb](../.claude/agents/placeur-pcb.md) / [relecteur-pcb](../.claude/agents/relecteur-pcb.md).

### Outils et historique
- [scripts_python/](scripts_python/) — outillage PC, rangé par usage : `build/`, `outils_pc/`, `berry/`, `maintenance/`, `sauvegarde/`, `reseau/` (détail dans [CLAUDE.md](../CLAUDE.md)).
- [HISTORIQUE_SYNCHRO_FORK.md](HISTORIQUE_SYNCHRO_FORK.md) *(généré)* — journal des synchronisations du fork.
- [CHANGELOG.md](CHANGELOG.md) — historique des évolutions.
- [Les graphiques des mesures](#les-graphiques-des-mesures-cartes-s3p4) — page `/graphiques` des cartes S3/P4, plus bas dans ce fichier.
- [Build et téléversement (page web)](#build-et-téléversement-page-web) — compiler et téléverser les cartes (COM ou OTA) depuis http://127.0.0.1:7700, plus bas dans ce fichier.
- [Fichiers Berry par env (page web)](#fichiers-berry-par-env-page-web) — sur le FS, exclu ou solidifié, et création d'un env, depuis http://127.0.0.1:7800, plus bas dans ce fichier.
- [Synchro du fork (page web)](#synchro-du-fork-page-web) — diagnostic et assistant pas à pas pour rattraper l'amont, depuis http://127.0.0.1:7500, plus bas dans ce fichier.
- [Sniffeur I2C (page web)](#sniffeur-i2c-page-web) — voir le trafic d'un bus I2C, décodé jusqu'au registre, par un ESP32-S3 dédié, depuis http://127.0.0.1:7350, plus bas dans ce fichier.

<hr></hr>

## Les logs Berry : charte et réglages

Le mécanisme vit dans `data/fs/logFonctions.be`, qui porte la même charte en tête.

### Les 4 niveaux

| Mot | Constante | Quand l'utiliser |
|---|---|---|
| `erreur` | `LOG_LEVEL_ERREUR` (1) | Un échec qui demande d'agir : exception, trame rejetée, abandon après N tentatives. **Toujours affiché**, quel que soit le réglage du module. |
| `info` | `LOG_LEVEL_INFO` (2) | Un événement ou un changement d'état, une ligne par événement : relais commuté, esclave connecté, configuration appliquée. |
| `debug` | `LOG_LEVEL_DEBUG` (3) | Le déroulé d'un traitement : étapes, décisions, valeurs clés. |
| `detail` | `LOG_LEVEL_DEBUG_PLUS` (4) | Le brut : trames, JSON complets, paramètres reçus. Sort au niveau 3 de Tasmota, sans les `BRY: GC`. |

Dans le code : toujours `logFonctions.log(msg, niveau [, cible])`, jamais `log()` directement.
Un échec se logue en `erreur`, jamais en `debug`. Pas d'`info` dans un traitement répété
(toutes les secondes, à chaque trame reçue, à chaque affichage de la page : `web_sensor`, `json_append`).
Un message coûteux (`json.dump`, `tohex`) se construit seulement si `logFonctions.actif(...)` est vrai.
Le niveau s'écrit par sa constante `LOG_LEVEL_*`, jamais en chiffre ; un niveau variable passe par
l'enrobeur du module (`xxxFonctions.log(msg, niveau)`) ou par une ternaire entre constantes.
`verifie_berry.py` signale les écarts à ces règles en avertissements, sans bloquer.

### Deux filtres successifs

Un message n'est affiché que s'il passe les deux :

1. **Le réglage de son module** (la *cible*) : `general`, `serveurWeb`, `udp`, `tcp`, `rangeExtender`,
   `discovery`, `modbus`, `conn16channels`, `slaveModbus`, `lorawan`, `volets`, `es8311`,
   `garage`, `cuve`, `rideau`, `leds`, `historique` (S3/P4 avec historique local), `ecranCave` et
   `ecranDebits` (cartes à écran ; `ecranCave` aussi sur le serveur de la cave, pour ses touches).
   (`web` désigne la **sortie** console web ; le module des pages web est `serveurWeb`.)
2. **Le réglage de la sortie** : `serie`, `web`, `mqtt` (topic `stat/<topic>/LOGGING`),
   `syslog` (le PC, `syslog_tasmota.py`). Ces réglages forment un **profil**.

Exemple : pour voir les trames ModBus dans la console, il faut `ReglageLog modbus detail`
**et** un profil dont la sortie `serie` est au moins à `debug`.

### Les commandes

```
ReglageLog                          affiche le profil actif, les sorties et le réglage de chaque module
ReglageLog help                     liste les sous-commandes (aide affichée en console)
ReglageLog help modbus              détail d'une sous-commande, avec le réglage actuel (help niveaux : la charte)
ReglageLog profil debug             applique le profil « debug » (ou « normal ») aux sorties
ReglageLog modbus debug             règle le module ModBus : erreur | info | debug | detail
ReglageLog tous detail              règle d'un coup tous les modules présents sur la carte
ReglageLog syslog info              règle une sortie du profil actif : aucun | erreur | info | debug | detail
```

Tout est enregistré dans `_persist.json`. Une sortie à `detail` affiche aussi les lignes
`BRY: GC` de Tasmota : c'est l'outil pour mesurer la RAM.

### Dans `_persist.json`

```json
"diverses": {
    "logs": {
        "profil": "normal",
        "profils": {
            "normal": {"serie": "info",  "web": "info",  "mqtt": "erreur", "syslog": "info"},
            "debug":  {"serie": "debug", "web": "debug", "mqtt": "debug",  "syslog": "debug"}
        },
        "general": "info",
        "nbLogsFiles": 0
    }
},
"drivers": {
    "ModBus": { "activation": "ON", "log": "debug", ... }
}
```

La sortie la plus bavarde fixe le coût : Tasmota met en mémoire tout message accepté par au
moins une sortie. Un profil « normal » sobre allège donc vraiment la carte.

### Ce que le profil écrase, et ce que `actif()` économise

- **Le profil fait foi sur les sorties.** Un réglage tapé à la main (`SerialLog 4`, `WebLog`, `MqttLog`,
  `SysLog`) est écrasé au redémarrage suivant, ou au prochain `ReglageLog`, par le profil du persist.
  Pour qu'un réglage tienne : `ReglageLog serie detail` (il modifie le profil actif et l'enregistre).
- **La console série se coupe 600 s après le démarrage** (`SERIALLOG_TIMER`, réglage par défaut de
  Tasmota, gardé par choix). Quand le profil envoie un `SerialLog` différent du réglage en cours, le compte
  à rebours repart de zéro ; sinon la coupure a lieu. Pour suivre une carte au-delà : MQTT, console web
  ou syslog.
- **`logFonctions.actif(niveau, cible)` répond « au moins une sortie ».** Il est vrai si le seuil du
  module laisse passer le niveau **et** si une sortie au moins le reçoit (`detail` compté au niveau 3).
  Un message gardé par `actif()` est donc construit dès que la série est à `debug`, même si l'on ne
  regarde que le syslog. C'est correct, mais l'économie dépend de la sortie la plus bavarde.

<hr></hr>

## Les graphiques des mesures (cartes S3/P4)

Les cartes ESP32-S3 et P4 tiennent un historique de leurs mesures (`data/fs/historiqueFonctions.be`) :
24 h en RAM au pas de 5 min, et min/moy/max horaires en flash, un fichier par mois. Le bouton
**Graphiques** de la page d'accueil ouvre `/graphiques`, qui les trace avec ECharts, en temps réel. Les ESP32 classiques
n'ont ni l'historique ni la page (fichiers exclus de leur LittleFS) : leurs courbes sont dans Grafana.

- **Séries découvertes** (2026-10-18) : la carte trace **ses** capteurs sans liste écrite à la main. Sont
  retenues toutes les valeurs numériques de son JSON SENSOR (celui de `tele/<topic>/SENSOR`) : capteurs
  réels (DS18B20, ADS1115, AM2301…) comme virtuels (valeurs reçues par ModBus, valeurs calculées par un
  module comme `sensorsCuve`). **Jamais** les relais, entrées, boutons et volets (`POWER*`, `Switch*`,
  `Button*`, `Shutter*`, ON/OFF), ni les mesures internes de la carte (température de l'ESP32, RSSI,
  mémoire), ni un compteur dont le type n'est pas réglé. Découverte 2 min après le démarrage, puis à chaque
  nouvelle heure : un capteur apparu plus tard (esclave ModBus en retard) s'ajoute ; une série déjà
  enregistrée ce mois-ci reste (trou si elle ne mesure plus). Une série s'appelle par son chemin dans le
  JSON, ex. `DS18B20.Temperature`. Choix et règles : `data/fs/historiqueSeries.be`.
- **Graphiques par défaut** : « Mesures », plus un graphique par groupe déclaré dans `graphiques.json` (ex.
  « Cuve » pour la hauteur, le volume et le remplissage, sur la cuve et le P4).
- **Composer ses graphiques** (2026-10-19) : bouton **Modifier les graphiques**. Ajouter, renommer, supprimer,
  monter ou descendre un graphique ; choisir son type (courbes, barres, escalier, aires), sa période et ses
  séries, et au besoin un type par série (graphique **combiné** : barres pour un compteur, courbe pour une
  température). « Toutes les séries placées dans aucun autre graphique » reçoit aussi les séries découvertes
  plus tard. **Enregistrer sur la carte** : la composition est écrite dans `/json/graphiques.json` (clé
  `graphiques`), le PC et le téléphone voient donc la même page ; **Rétablir** revient aux graphiques par
  défaut. La carte contrôle ce qu'elle reçoit : 8 graphiques, 12 séries chacun, titre de 1 à 60 caractères.
  Une série enregistrée qui n'existe plus est signalée « absente » sous son graphique.
- **Périodes** : chaque graphique a la sienne, dans son en-tête : « 24 dernières heures », « Mois en cours »,
  puis un mois par entrée (moyenne horaire ; bande min-max pour les courbes et les aires). Un mois marqué
  « ancienne liste de séries » date d'avant un changement des séries (fichier mis de côté en `-a`, `-b`…).
  Deux graphiques sur la même période ne coûtent qu'une lecture à la carte.
- **Temps réel** (vue 24 h et mois en cours) : la page lit les valeurs actuelles de la carte
  (`/histo?p=direct`) et les ajoute au bout des courbes ; l'axe des temps va jusqu'à l'heure actuelle. Cadence
  choisie dans la liste **Direct** de la page : arrêt, 2, 5, 10, 30 s ou 1 min (10 s par défaut, ou la clé
  `direct` de `graphiques.json`) ; le choix est gardé par le navigateur. L'historique affiché est relu
  toutes les `rafraichissement` secondes (60 par défaut ; mois en cours : 15 min), et rien n'est lu quand
  l'onglet est caché. La carte relit ses capteurs au plus toutes les 4 s, quel que soit le nombre de pages
  ouvertes.
- **Légende** : un clic masque ou affiche une série, choix gardé par le navigateur. Un axe Y par unité,
  ajusté au minimum et au maximum des valeurs tracées (sans descendre sous zéro si toutes sont
  positives) ; molette ou pincement pour zoomer sur le temps. Un trou dans une courbe = pas de mesure
  (carte arrêtée, esclave muet, capteur absent).
- **Historique long** : le bouton « Historique long (Grafana) » ouvre le tableau du Pi.
- ECharts 6 est servi **par la carte**, compressé (`/sd/js/echarts.min.js.gz`, 368 Ko), sans Internet :
  le navigateur le décompresse, le garde dans son `localStorage` et ne le redemande qu'à un changement de
  version. Il faut un navigateur récent (`DecompressionStream` : Chrome 80, Firefox 113, Safari 16.4).

### Dans `_persist.json` : ce que la relève de chaque minute utilise

Le persist est chargé **entier et en permanence** en RAM : il ne porte que les réglages de la relève.

```json
"diverses": {
    "historique": {
        "activation": "ON", "pasMinutes": 5, "dureeHeures": 24, "moisConserves": 24, "seriesMax": 12,
        "exclues": ["sensorsCuve.valeursAnalogiques"],
        "ajouts": ["ESP32.Temperature", "@rssi"],
        "compteurs": {
            "COUNTER.C1": {"type": "energie", "impulsionsParUnite": 1000, "unite": "kWh"},
            "COUNTER.C2": {"type": "debit", "impulsionsParUnite": 450, "unite": "L/min"}
        },
        "grafana": "http://192.168.0.5:3000/d/historique-cuve?var-appareil=%topic%"
    }
}
```

- `exclues` : chemins (ou débuts de chemin, par segment entier) à ne pas tracer.
- `ajouts` : séries que le filtre écarte mais que l'on veut quand même (internes : `ESP32.Temperature`,
  `@rssi`, `@heap` ; position d'un volet `Shutter1.Position`). `@power<n>` (relais) est refusé.
- `compteurs` : un compteur n'est tracé qu'une fois réglé. `energie` = cumul ÷ `impulsionsParUnite` ;
  `debit` = impulsions depuis la relève précédente ÷ `impulsionsParUnite`, **par minute** (rien à la
  première relève ni après une remise à zéro du compteur).
- `grafana` : `%topic%` est remplacé par le topic de la carte ; sans clé, pas de bouton. Elle reste dans le
  persist car le bouton des ESP32 classiques (ci-dessous) la lit à cet endroit.

### Dans `graphiques.json` : ce que seule la page utilise

`data/<lieu>/<carte>/graphiques.json`, rangé dans `/json/` au démarrage et lu à l'ouverture de la page
seulement (rien en RAM le reste du temps). Facultatif.

```json
{
    "affichage": {
        "sensorsCuve.niveauCuve.tauxRemplissage": {"libelle": "Remplissage", "unite": "%", "facteur": 100},
        "DS18B20.Temperature": {"libelle": "Température de l'eau", "unite": "°C"}
    },
    "groupes": {"Cuve": ["sensorsCuve.niveauCuve"]},
    "rafraichissement": 60,
    "direct": 10,
    "graphiques": [{"titre": "Cuve", "periode": "jour", "type": "courbe",
                    "series": [{"chemin": "sensorsCuve.niveauCuve.volume", "type": "barres"},
                               {"chemin": "sensorsCuve.niveauCuve.hauteurEau"}]},
                   {"titre": "Mesures", "periode": "mois", "type": "aire", "series": "autres"}]
}
```

Sans `affichage`, libellé = chemin de la série (esclave ModBus remplacé par son nom du persist) et unité
devinée de sa dernière clé (`Temperature` → °C, `Humidity` → %, `Pressure` → hPa…) ou de son nom
(`hauteur` → cm, `volume` → L, `taux` → %) ; une entrée analogique relayée par ModBus
(`TasmotaSlaveModBus.<esclave>.ANALOG.A<n>`) est en mV, l'`ANALOG` natif de la carte (valeur brute de l'ADC)
reste sans unité ; l'unité d'un compteur réglé vient de `compteurs`. `facteur`
multiplie la valeur affichée (0-1 → %). `groupes` : titre → débuts de chemin ; chaque groupe a son
graphique, les autres séries vont dans « Mesures ». `rafraichissement` : relecture de l'historique affiché, en
secondes (10 au minimum). `direct` : cadence par défaut du temps réel (0 = arrêt, 2, 5, 10, 30 ou 60 s).
`graphiques` : la composition écrite par le bouton « Enregistrer » de la page (inutile de l'écrire à la main) ;
`periode` = `jour`, `mois` (mois en cours) ou `AAAA-MM` ; sans cette clé, graphiques par défaut.

**Carte sans historique local** (ESP32 classique, ou historique à `OFF`) : la même clé `grafana`, dans un bloc
`"historique": {"grafana": "…"}`, ajoute à la page d'accueil un bouton **Historique (Grafana)** qui ouvre
directement le tableau (`controleWeb.boutonGrafana`, commun à toutes les cartes ; module solidifié : il faut
le firmware recompilé). Il n'apparaît pas là où l'historique est actif, le bouton « Graphiques » y menant
déjà. Clé non posée sur la cave et le bureau (décidé le 2026-10-18) : le tableau `historique-cuve` n'a que
des panneaux de cuve, leurs courbes y seraient vides.

### Vérifier

- `/histo?p=liste`, `/histo?p=jour`, `/histo?p=direct`, `/histo?p=mois&m=AAAA-MM` donnent le JSON brut. En `curl`, ajouter
  `-H "Referer: http://<ip>/"` : sans lui, Tasmota coupe la connexion sans réponse (`curl: (52)`).
- Banc hors carte : `python outils_docs/scripts_python/berry/banc_graphiques.py` (code de sortie 0 = vert ;
  inclut `banc_historique.be` : découverte des séries, compteurs, redécouverte horaire).
- Séries retenues par une carte : log `HISTORIQUE: Series enregistrees : [...]` (puis `Nouvelles series`),
  ou `/histo?p=liste`.
- Sur le P4, les mesures de la cuve sont écartées de l'historique tant que l'esclave ne les donne pas
  pour valides (`controleGarage.filtreHistorique`) : une cuve sans capteur donne des trous, pas des zéros.

<hr></hr>

## La page Énergie (page `/energie`, différentiel du bureau)

Bouton **Énergie** de l'accueil, page gardée par la carte elle-même, sans le Pi. En haut : puissance, courant, facteur
de puissance en cadran, fréquence (relus toutes les 10 s, mêmes précisions que l'accueil). Puis, en barres, les
consommations **d'aujourd'hui par heure**, **du mois par jour**, des **12 derniers mois**, chacune avec son total en kWh
(en Wh sous 1 kWh) et son coût ; enfin la courbe de puissance sur 24 h. En bas, en petit, l'endroit où régler le prix.

- **Calcul** : écart de `ENERGY.Total` à chaque changement d'heure locale ; l'heure en cours est ajoutée à l'affichage
  (le total du jour suit donc « Énergie aujourd'hui » de l'accueil, sauf heure non notée après une coupure). Un compteur
  qui baisse, ou un écart impossible (`EnergyTotal` rétabli à la main), n'est pas compté : log `erreur`.
- **Prix** : Configuration > « Tarifs de l'électricité » (`/energie?f=tarifs`) : liste des tarifs et, en petit dessous,
  le tarif en vigueur. On saisit une date d'effet, en € TTC par kWh, et **Base** (un prix) ou **HC/HP** (deux prix et les
  plages d'heures creuses, par exemple `22-6` ou `2-7,14-17`). Plages en heures entières : le compteur est noté une fois
  par heure, une heure compte en entier au tarif de son début. Chaque consommation garde le coût du tarif en vigueur à sa
  date et à son heure : un nouveau tarif ne touche jamais le passé. Même date = tarif remplacé. `/energie` alerte si
  aucun prix n'est saisi ou s'il a plus de 6 mois.
- **Fichiers de la carte**, dans `/energie/` : `etat.json` (une écriture par heure), `mois-AAAA-MM.json` (mois clos, 24
  au plus ; les plus anciens sont effacés si le FS passe sous 16 Ko libres), `prix.json`, `courbe.bin` (copie horaire de
  la courbe : une coupure en perd au plus 1 h).
- **Calibrage** : `diverses.energie.calibrage` du persist. Une minute après le démarrage, si les trois valeurs lues sont
  les défauts de la BL0942 (596 / 15187 / 251213), celles du persist sont rejouées ; sinon rien, un recalibrage manuel est
  respecté. Le compteur `Total` n'est PAS rétabli seul : avant un flash, le relever, puis `EnergyTotal <Wh>`.
- **Disposition pilotée par une description** (2026-11-08, palier 4 de l'atelier) : si `/json/energie_page.json` existe, la page
  se dessine d'après elle (`data/sd/js/energie.js`, `Energie.valide` puis `Energie.trace`) ; la carte la relaie sans jamais la
  parser (`/energie?f=description`, 404 si absente). **Repli** : description absente, au-delà de 4 096 octets, tronquée ou
  refusée par `Energie.valide` = la page d'avant, plus une ligne « Description ignorée : <motif> ». Un élément mal formé est
  ignoré seul, avec sa ligne. Un graphique « jour » sur un mois fixe dont l'archive a été purgée reste vide (« archive
  effacée ») sans arrêter la page ; un champ absent du bloc ENERGY donne une tuile « -- ». Routes de lecture ajoutées :
  `f=description`, `f=mois&m=AAAA-MM` (JSON `{"d","de"}`, 404 si pas d'archive, 400 si mois illisible) et `f=direct` élargi
  (puissance, courant, facteur, fréquence et les autres champs ENERGY sous leur nom Tasmota). Comptage et stockage inchangés.
  La description s'écrit par l'atelier (voir « Atelier des graphiques > Destination Énergie »), pas à la main.
- **Code** : `data/fs/energieFonctions.be`, `data/fs/controleEnergie.be`, `data/sd/{html,css,js}/energie.*`, sur le seul
  différentiel (liste `page_energie` de `[berry_commun]`, exclue des autres envs). Bancs :
  `outils_docs/scripts_python/berry/banc_energie.py` (page d'avant), `banc_energie_routes.py` (routes de lecture),
  `banc_energie_description.py` (page pilotée par sa description, rendu Chrome) et
  `outils_pc/test_energie_rendu.mjs` (validation JS = Python). Conception :
  `docs/superpowers/specs/2026-10-31-page-energie-differentiel-design.md`.
- **Poser la page sur une autre carte** (aucune autre carte du parc n'en a l'usage au 2026-11-09). Le module ne lit que le
  bloc `ENERGY` du JSON SENSOR : il vaut pour tout capteur d'énergie MONOPHASÉ, à une seule voie. Un compteur à plusieurs
  voies ou phases (`Total` en liste) n'est pas compté : la page s'affiche, avec un compteur illisible et rien d'écrit en
  flash (banc `banc_energie.be`, « plusieurs voies »). La protection du calibrage ne joue que pour une BL0942 ; avec une
  autre puce, ou sans `calibrage` au persist, elle ne fait rien. Pour une nouvelle carte, dans cet ordre :
  1. `platformio_tasmota_cenv.ini`, section de l'env : retirer `${berry_commun.page_energie}` de son `custom_files_exclude`
     (ou de celui de la base dont il hérite, en le redéfinissant) ; ajouter `data/fs/energieFonctions.be` et
     `data/fs/controleEnergie.be` à son `custom_berry_solidify`, comme l'env `tasmota32-bureau-interrupteur-energie`.
  2. `autoexec.be` de la carte : `demarrage.charge(["controleEnergie"], "diverses.energie")`, après `controleWeb`.
  3. `_persist.json` de la carte : `"energie": {"activation": "ON"}` sous `diverses` (plus `calibrage` pour une BL0942).
  4. `banc_demarrage.py` (instantané de la carte relu, seul écart attendu), puis compilation et envoi du firmware ET du
     FS par la page Build : le module est solidifié, un envoi du FS seul ne suffit pas.
  5. Sur la carte : bouton **Énergie** sur l'accueil, `/energie` affiche la puissance ; la première note horaire apparaît au
     changement d'heure suivant. Saisir un prix dans Configuration > « Tarifs de l'électricité ».

## Les jauges du niveau de la cuve (page `/cuve`, cuve et P4)

Premier essai du 2026-10-31. L'**icône de cadran** dans le titre de l'encadré du niveau de la cuve, sur la page
d'accueil de la cuve et du maître P4, ouvre `/cuve` : une **jauge liquide** pour le volume disponible en litres
(modèle A du catalogue `outils_docs/jauges/`, ECharts + extension echarts-liquidfill), un **demi-cercle** pour
le taux de remplissage en % (modèle H, SVG) et un **cadran des tensions** (modèle B, ECharts) : anneau extérieur =
tension de la sonde **recalculée** (0-10 V), anneau intérieur = tension **brute** à l'entrée de l'ADS1115, après le
pont diviseur. Rouge sous 20 %, orange sous 40 %, bleu au-delà.

- **Tensions** : la cuve recalcule la tension de la sonde (mV d'entrée × rapport du pont, tiré du montage de la voie,
  `ReglageAna cablage`) dans `sensorsCuve.valeursAnalogiques.tensionSonde_V`. L'encadré de l'accueil montre les deux
  lignes « Tension brute (ADS1115) » et « Tension sonde (recalculée) », même en erreur de mesure (elles servent à la
  diagnostiquer). Le P4 reçoit la tension recalculée **par ModBus** (registre 4708 de la cuve, voir
  `PROTOCOLE_MODBUS.md`) : il ne connaît pas le pont ; « -,-- V » tant que la cuve ne l'a pas servie.

- **Valeurs** : celles de l'historique de la carte, `/histo?p=direct`, relues toutes les 10 s. Sans historique
  actif (`diverses.historique.activation`), la page le dit et n'affiche rien ; dans les 2 min qui suivent un
  démarrage, elle attend l'historique. Volume maximal tiré des dimensions de la cuve : `modules.cuve.dimensions`
  sur la cuve, `dimensions` de l'entrée analogique de la cuve (esclave ModBus 1) sur le P4.
- **Bibliothèques** : ECharts vient de `/graphiques?f=echarts.js.gz`, avec la même clé de cache que la page des
  graphiques (pas de second téléchargement) ; l'extension (3,4 Ko compressée) de `/cuve?f=liquidfill.js.gz`.
  Sans elle, le taux reste affiché.
- **Fichiers** : `data/fs/cuvePageFonctions.be` (importé à la première ouverture), `data/sd/html/cuve.html`,
  `data/sd/css/cuve.css`, `data/sd/js/cuve.js`, `data/sd/js/echarts-liquidfill.min.js.gz`. Ils ne partent **que**
  sur la cuve et le P4 : liste `page_cuve` de `[berry_commun]`, ajoutée au `custom_files_exclude` de tous les
  autres envs. Une nouvelle carte qui en aurait besoin la retire de sa liste.
- **Vérifier** : banc hors carte `python outils_docs/scripts_python/berry/banc_cuve_page.py` (code 0 = vert).

<hr></hr>

## Les débits de la nourrice de chauffage (carte Serveur Débits PAC)

Carte ESP32-S3 `tasmota32s3-bureau-serveur-debits-pac` (dossier `data/bureau/tasmota32s3-serveur-debits-pac/`), à la
nourrice de la PAC : elle mesure le débit des **6 départs de radiateur** par leurs débitmètres à impulsions (YF-B2,
K = 11 Hz par L/min) et les publie sur sa page web, dans son JSON SENSOR et par ModBus. L'écran est sur une seconde
carte, la carte d'affichage (ci-dessous). Plans `tasks/plans/debitmetres-chauffage.md` et `tasks/plans/debits-deux-cartes.md`,
analyse `outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`. **Pas encore essayées sur des cartes réelles** (2026-11-11).

**Deux cartes depuis le 2026-11-09** : l'acquisition compte et calcule, la carte d'affichage montre les débits sur son écran.

- **Acquisition** `tasmota32s3-bureau-serveur-debits-pac` : esclave ModBus id 1, Range Extender id 1, derrière le point
  d'accès de l'affichage (`ECRAN-DEBITS-PAC-GATEWAY`), sans écran (`drivers.ecran` OFF). Elle sert les 6 débits et un
  mot d'états aux registres 4704 à 4710 (`modules.debits.modbus` ON) et les pousse en UDP à chaque fin de fenêtre. Sa
  page et sa page d'équilibrage se joignent depuis le Wi-Fi maison par le relais de l'affichage :
  `http://192.168.0.51:8080/` et `http://192.168.0.51:8080/equilibrage`.
- **Affichage** `tasmota32s3-bureau-ecran-debits-pac` (dossier `data/bureau/tasmota32s3-ecran-debits-pac/`, IP
  192.168.0.51, topic `chauffage/pac/ecran`) : module Waveshare ESP32-S3-Touch-LCD-7B (écran 7″ 1024 × 600, tactile
  GT911, RS485 intégré), maître ModBus et Range Extender id 0 (`ecranDebitsFonctions.be`, `controleEcranDebits.be`). Il
  relit les 7 valeurs en une requête toutes les 10 s par RS485 (RX GPIO16, TX GPIO15, 19 200 bauds) et reçoit le push.
  Une voie sans nouvelles depuis 2 fenêtres est affichée « inconnu ». Brochage, expandeur d'E/S, `display.ini` et choix
  HASPmota ou LVGL : fiche `WAVESHARE_ESP32-S3-Touch-LCD-7B.md` du dossier de la carte dans
  `outils_docs/Schémas de branchement - Attribution des PINS des modules/bureau/` (plan `debits-deux-cartes`, A8, en cours).
  Interface de l'écran choisie à la compilation : `custom_interface_ecran = haspmota` (ou `lvgl`) dans la section de
  l'env de `platformio_tasmota_cenv.ini`. Les fichiers de chaque interface sont listés sous `custom_interface_ecran_<nom>`,
  et seuls ceux de l'interface choisie partent sur le LittleFS. Le build l'annonce par une ligne
  « Interface d'ecran : … ; exclus : … » et s'arrête sur une valeur inconnue.
- **Réglages de l'affichage** : `ReglageEcranDebits fenetre <s>` (la même que `ReglageDebits fenetre` sur
  l'acquisition, à recopier à la main), `ReglageEcranDebits veille <min>`.
- **Réglages ModBus** : `ReglageModbus PeriodeReleve <s>` sur l'affichage (5 à 300 s, 10 posé ; exacte si elle divise
  60 ; prise en compte au redémarrage) ; `ReglageModbus LectureGroupee ON` sur l'acquisition. Détail du protocole :
  `PROTOCOLE_MODBUS.md` § « Lecture groupée et push multi-valeurs ».
- **Déploiement** : flasher l'acquisition AVANT l'affichage.
- **Sniffeur** sur le bus des débits : `sniffeur_modbus.py --persist affichage`.

**Où changer les noms des voies.**
- Affichage : `data/bureau/tasmota32s3-ecran-debits-pac/_persist.json`, `modules.ecranDebits.environnement.analogiques`,
  `analogique1` à `analogique6`, champ `nom` (« Débit 1 » à « Débit 6 » aujourd'hui), relu par `ecranDebitsFonctions.be`
  à chaque rafraîchissement. Libellés affichés avant le premier rafraîchissement : `pages.jsonl` du même dossier.
- Acquisition : `data/bureau/tasmota32s3-serveur-debits-pac/_persist.json`, `modules.debits.environnement.debitmetres`
  (voies 1-2) et `compteurs` (voies 3-6), champ `nom` : JSON SENSOR, historique, page d'équilibrage. Les `nom` de
  `analogique1` à `analogique7` du même module sont les libellés des registres servis au maître.
- Sur une carte en service : modifier le persist, l'envoyer (page Build, onglet Fichiers), puis `Restart 1`.

**L'acquisition en détail :**

- **Voies** : voies 1-2 = `FlowRateMeter` de Tasmota (GPIO4, GPIO5 ; groupe `debitmetres` du persist, entrées
  `debitmetre1-2`) ; voies 3-6 = compteurs `Counter1-4` (GPIO6, 7, 15, 16 ; groupe `compteurs`), débit calculé en Berry
  sur une fenêtre glissante (10 s par défaut). Nom et K de chaque voie dans son entrée du persist (`nom`, `k`).
- **Sorties** : bloc `DEBITS` du JSON SENSOR (`D1` à `D6` et `Total` en L/min, `Imprecis` = voies entre 0 et 1 L/min, sous
  la plage du YF-B2 (1 à 25 L/min), en orange sur l'écran ; `Muets`) ; une ligne par départ sur la page d'accueil ; écran : page 1 = 6 barres, débit
  et part du total, page 2 = K de chaque voie (bouton « Détails »). Description de l'écran : `pages.jsonl` de la carte,
  lancée par le module (`haspmota.start("/json/pages.jsonl")`).
- **Capteur muet** : une voie à 0 L/min pendant 10 min (`modules.debits.muet`, en min) est signalée « muet » en rouge sur
  l'écran, « capteur muet ? » sur la page, et par `CAPTEUR_MUET_ERREUR` au journal (au passage seulement). Un départ
  fermé plus de 10 min est donc signalé lui aussi.
- **Écran** : le code d'écran de `debitsFonctions.be` (pages, veille `modules.debits.veille`) ne sert plus depuis que
  l'écran est sur la carte d'affichage (`drivers.ecran` OFF sur l'acquisition). Veille de l'écran : `ReglageEcranDebits
  veille` sur l'affichage.
- **Réglages**, tous gardés au persist :

  | Commande | Effet |
  |---|---|
  | `ReglageDebits` | état : fenêtre, veille, voies (nom, K), débits, capteurs muets, durée de la dernière écriture de l'écran (`ecran_ms`) |
  | `ReglageDebits k <voie> <Hz par L/min>` | facteur K d'une voie (0,1 à 1000). Étalonnage : K corrigé = K × débit affiché ÷ débit réel |
  | `ReglageDebits nom <voie> <texte>` | nom du départ (24 caractères au plus), repris par l'écran et la page |
  | `ReglageDebits fenetre <s>` | durée de mesure, 2 à 60 s ; plus longue = plus précise aux petits débits |
  | `ReglageDebits veille <min>` | veille de l'écran, 0 à 120 min, appliquée sans redémarrer |
  | `ReglageDebits aide [sujet]` | aide de la commande |

- **Historique** : actif (relevé toutes les 5 min, 24 h affichées) ; courbes des 6 débits et du total sur `/graphiques`,
  libellés et groupes dans `graphiques.json` de la carte (libellés à refaire si un départ est renommé). Voir
  « Les graphiques des mesures ».
- **Essai de charge** (avant la pose) : un second ESP32 sous Tasmota standard envoie des impulsions sur les 6 entrées ;
  `python outils_docs/scripts_python/outils_pc/essai_charge_debits.py --generateur <ip> --carte <ip>` compte ce que la
  carte a reçu à chaque palier (écart < 0,5 % attendu) ; montage et câblage dans sa docstring (`--help`).
- **Équilibrer la nourrice** : guide `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`, et sa version animée pas
  à pas (estimateur des puissances, calculateur des débits cibles), `data/bureau/tasmota32s3-serveur-debits-pac/equilibrage.html` :
  servie par la carte (bouton « Équilibrage » de l'accueil, `/equilibrage`, débits lus sur la carte), ou ouverte seule
  sur un téléphone ou un PC (débits tapés à la main). Sur la carte, la page reçoit en plus le code
  `equilibrage_carte.js` du même dossier. Avec « Suivre en direct », le schéma animé montre les débits réels, colorés selon
  les cibles du calculateur. Le bouton « Garder les puissances sur la carte » enregistre l'estimateur et les puissances
  dans `/json/equilibrage.json` (hors persist, effacé par un envoi du FS en image : à réenregistrer). Un favori du téléphone
  vers `/equilibrage` fonctionne : sans Referer, la carte renvoie une page vide qui se recharge, et le contrôle d'accès
  habituel s'applique.
- **Vérifier** : bancs hors carte `python outils_docs/scripts_python/berry/banc_debits.py` (calcul, JSON, écran, capteur
  muet, réglages, veille ; témoins) et `banc_demarrage.py --carte tasmota32s3-bureau-serveur-debits-pac` (code 0 = vert).

<hr></hr>

## L'écran de la cave (écran 7B esclave du serveur de la cave)

L'écran tactile Waveshare ESP32-S3-Touch-LCD-7B de la cave (env `tasmota32s3-cave-ecran`) montre l'état de la cave
et commande ses appareils. Il est l'**esclave** du serveur relais de la cave (`tasmota32s3-cave-serveur-rly`) :
les **touches** partent par ModBus (RS485 16/15 et push UDP par le point d'accès de la cave), l'**affichage** arrive
par MQTT. Plan `tasks/plans/ecran-cave-vues-commandes.md`, spec
`docs/superpowers/specs/2026-11-12-ecran-cave-vues-commandes-design.md`.

### Les pages

| Page | Ce qu'elle montre |
|---|---|
| Accueil | À gauche les capteurs : température, humidité, cuve (taux et volume), niveau du vide-cave. À droite les appareils, une tuile par touche avec son icône : lumières, lave-linge, pompe de la cuve, pompe du vide-cave, et la ventilation, dont l'icône tourne quand elle marche |
| Graphiques | Température et humidité des 30 dernières minutes |
| Cuve | Jauge de la cuve, flotteurs haut et bas du vide-cave, pompe du vide-cave (« Forcer la marche » / « Arrêter la marche ») |
| Réglages | Mise en veille, extinction, luminosité, par des boutons − et + |

Le bouton ☰ ouvre le menu : « Redémarrer le serveur » demande une confirmation avant d'agir. Une alerte (pannes des
flotteurs, marche forcée) s'affiche dans un bandeau rouge au-dessus de la navigation.

### Ce que fait une touche

| Touche | Appareil | Relais du serveur |
|---|---|---|
| 1 | Lumières | 3 |
| 2 | Lave-linge (relais « Lavage ») | 5 |
| 3 | Pompe de la cuve | 4 |
| 4 | Pompe du vide-cave, marche manuelle | 1 |
| 5 | Redémarrer le serveur (menu) | `Restart 1` |

- Une touche envoie l'**état voulu** (l'inverse de l'état affiché), jamais une bascule : un appui répété ou relancé
  ne fait pas clignoter le relais.
- **Valeur grisée = touche refusée** : tant que l'état de l'appareil n'est pas à jour, l'écran refuse l'appui et
  l'écrit dans la barre du haut (« touche refusée : état inconnu »).
- L'écran relance l'ordre toutes les 2 s, 5 fois au plus, jusqu'à ce que l'état reçu par MQTT confirme le relais.
  La touche 5 n'est **jamais** relancée : le serveur oublie ses ordres en redémarrant, une relance le ferait
  redémarrer en boucle.
- Pompe du vide-cave : un appui la force en marche et met les flotteurs en pause ; un second appui l'arrête, la
  minuterie de 120 s aussi ; les flotteurs reprennent à l'arrêt. Le forçage est permis même flotteurs « à sec ».

### Ce qui est grisé, et pourquoi

Chaque valeur garde l'heure de sa réception ; au-delà de 15 min sans message (`modules.ecranCave.peremption`,
900 s par source), elle est grisée. Sans broker MQTT, tout est grisé et l'horloge de la barre du haut est barrée.

### Pannes des flotteurs (serveur de la cave)

Le serveur publie une alerte (topic d'alerte de la pompe, effacée par `AcquittePompe`) quand :
- le flotteur haut est fermé alors que le bas est ouvert, pendant plus de `pompeVideCave.pannes.antiRebond` s ;
- la minuterie arrête la pompe `pompeVideCave.pannes.maxArretsMinuterie` fois de suite alors que le flotteur bas
  reste fermé (flotteur bas probablement bloqué).

### Mettre l'écran en service

1. Compiler et flasher `tasmota32s3-cave-ecran` par la page Build (le FS part avec le firmware).
2. Sur le **serveur de la cave**, passer à `ON` `drivers.ModBus.environnement.TasmotaSlaveModBus.TasmotaSlaveModBus1.activation` (l'esclave
   « ECRAN-CAVE ») et `modules.ecranCave.activation` : tant qu'ils sont à `OFF`, le serveur ne relève pas l'écran et
   n'exécute aucune touche (un esclave actif sans carte ferait tomber le relevé en timeout).
3. Vérifier sur l'écran : valeurs non grisées, une touche allume son relais, la tuile passe au bleu.

Fichiers : `data/cave/tasmota32s3-ecran/` (`ecranCaveFonctions.be` : modèle MQTT et touches ; `controleEcranCave.be` :
abonnements, veille, rafraîchissement ; `ecranCaveHaspmota.be` + `pages.jsonl` : interface HASPmota),
`data/cave/tasmota32s3-serveur-rly/controleCommandesEcran.be` (exécution des touches) et `controlePompeVideCave.be`
(pannes des flotteurs, état publié). La maquette se modifie dans l'atelier des écrans (page 7960), description
`outils_docs/atelier_ecrans/cartes/tasmota32s3-cave-ecran/ecran.json`. Icônes : glyphes Material Design du firmware
(`outils_docs/ICONES_IMAGES_SOURCES.md`). Bancs : `berry/banc_ecran_cave.py`, `banc_commandes_ecran.py`,
`banc_pompe_cave.py`.

## Inclinaison d'un volet ou d'une trappe (MPU6050)

Un MPU6050 fixé sur une trappe (ou un volet) qui pivote autour d'une charnière horizontale donne son angle réel :
l'accéléromètre mesure la gravité, `atan2` en tire l'angle. Il sert de **capteur de position** du volet, sous le
nom `"Inclinaison"`, comme un fin de course : au franchissement d'une butée, le Shutter de Tasmota est recalé
(`vrFonctions.changementEtatCapteur`). Gain principal : la position est connue dès le démarrage. Une trappe qui
coulisse à plat, sans changer d'inclinaison, ne peut pas être suivie ainsi.

**Ce n'est pas une sécurité** : la lecture se fait en Berry, toutes les 250 ms au mieux. Les fins de course
physiques qui coupent le moteur restent indispensables.

### Le capteur

- Bus I2C de la carte (SDA/SCL déclarés dans le gabarit), adresse `0x68` (`104`), ou `0x69` (`105`) si AD0 est au
  +3,3 V. Fil court et souple : l'I2C supporte mal plus d'un mètre, et un câble qui se plie à chaque manœuvre casse.
- Lu en Berry (`tasmota.wire_scan`, registres `0x6B` et `0x3B`), **pas** par le pilote C de Tasmota : ne pas
  compiler `USE_MPU6050`. Ce pilote ne lit le capteur qu'une fois par TelePeriod et se le disputerait avec Berry.
- Sans `"activation": "ON"`, rien n'est lu : ni bus, ni minuterie, ni ligne sur la page. Tous les persists du
  dépôt portent le bloc, désactivé.

### Dans `_persist.json`

Sous `drivers.voletRoulants.environnement.VRs.<VR>.capteursPosition` :

```json
"capteurOuvert": "Inclinaison",
"capteurFerme": "Switch2",
"inclinaison": {
    "activation": "ON",
    "adresse": 104,
    "axes": "YZ",
    "angleOuvert": 85.0,
    "angleFerme": 3.0,
    "marge": 3,
    "blocage": 5,
    "blocageDegres": 1,
    "sensInverse": 3,
    "surveillance": 0,
    "positionReelle": "OFF"
}
```

- `capteurOuvert` / `capteurFerme` : `"Inclinaison"` pour que l'angle recale cette butée. Les deux types se
  mélangent : un fin de course physique d'un côté, l'inclinaison de l'autre.
- `axes` : les 2 axes de l'accéléromètre dans le plan de rotation (l'angle vaut `atan2` du 1er sur le 2e).
- `angleOuvert` / `angleFerme` : les butées, en degrés. `angleOuvert` peut être plus petit que `angleFerme`
  (selon le montage).
- `marge` : hystérésis en degrés pour QUITTER une butée (pas de rebond au seuil).
- `blocage` / `blocageDegres` : détection de blocage (ci-dessous). `blocage` à 0 la désactive.
- `sensInverse` : seuil en degrés de la détection de sens inverse (ci-dessous) ; 0 la désactive.
- `surveillance` : période en secondes de la lecture à l'arrêt (0 = aucune).
- `positionReelle` : `"ON"` pour que l'angle donne la position en % à Tasmota, volet arrêté.
- `filtre` (facultatif, 6 par défaut) : filtre passe-bas du MPU6050 (registre `0x1A`, 0 à 6 ; 6 = ~5 Hz) contre
  les vibrations du moteur. Écrit une fois, au réveil du capteur.

### Détection de blocage

Pendant la course, si l'angle bouge de moins de `blocageDegres` (1° par défaut) pendant `blocage` secondes
(5 par défaut) alors que le moteur tourne, la carte envoie `ShutterStop<id>` et logue une erreur
`VR_INCLINAISON: Volet 1 bloque a 40.0 degres (entre) depuis 5 s : moteur arrete !`. Cas couverts : trappe
coincée, moteur qui force contre une butée parce que la position estimée était fausse. Le délai repart à chaque
mouvement et à chaque nouvelle course : un départ lent ne déclenche rien tant qu'il dure moins de `blocage`
secondes. Régler `blocage` au-dessus du temps de démarrage réel du moteur.
Angle figé sur la butée vers laquelle va le volet, quand cette butée n'est pas désignée `"Inclinaison"` : c'est une
arrivée, pas un blocage. Le moteur qui force est arrêté de la même façon, sans erreur ni alerte.

Un blocage s'affiche aussi sur la page d'accueil (« BLOQUÉ » sur la ligne du volet) et part en MQTT, **retenu**, sur
`tele/<topic>/INCLINAISON<id>` : `{"Volet": 1, "Bloque": true, "Angle": 40.0, "Etat": "entre"}`. La course suivante
efface l'alerte (`"Bloque": false` publié). Rien n'est publié en dehors de ces deux changements.

### Sens inverse

Pendant la course, si l'angle s'éloigne de `sensInverse` degrés (3 par défaut) de son angle de départ dans le sens
OPPOSÉ à celui demandé, la carte arrête le moteur (`ShutterStop<id>`) et logue une erreur : moteur câblé à l'envers,
ou `ShutterInvert` faux. L'alerte est la même que pour un blocage (« BLOQUÉ (sens inverse) » sur la page,
`"Cause": "sens inverse"` en MQTT ; `"Cause": "blocage"` pour un blocage).

### Durées de course

Une course partie d'une butée et arrivée à l'autre est chronométrée. `ReglageVolets Inclinaison <id>` la donne avec la
valeur proposée, en secondes entières arrondies au-dessus : `tempsMontee` pour l'ouverture, `tempsDescente` pour la
fermeture. Rien n'est appliqué seul : `configVRByJson` réécrit `ShutterOpenDuration` / `ShutterCloseDuration` depuis
ces clés du persist à chaque démarrage, c'est donc le persist qu'il faut corriger. La mesure va du départ de la course
au franchissement de l'angle de butée : elle ne compte ni le temps de démarrage du moteur avant la règle `Direction`,
ni la fin de course mécanique au-delà de l'angle. Une course que Tasmota coupe avant la butée (durée trop courte) ne
donne pas de mesure : allonger d'abord la durée, puis mesurer.

### Surveillance à l'arrêt

Avec `surveillance` > 0 (30 s par exemple), le volet arrêté est relu toutes les `surveillance` secondes : la page
d'accueil suit une trappe bougée à la main, une ligne `info` signale un mouvement hors manœuvre (au moins `marge`
degrés), et une butée atteinte ainsi recale la position. Aucune lecture pendant une course (le suivi de 250 ms s'en
charge). La position réelle n'y est corrigée qu'après un vrai mouvement (au moins `marge` degrés) : un moteur qui
vient de démarrer, avant que la règle `Direction` n'arrive, n'a pas encore bougé. Capteur muet : une erreur par
lecture, et la période double à chaque échec (jusqu'à 128 fois), puis revient à la normale dès qu'il répond.

### Position réelle

Avec `positionReelle` à `"ON"`, l'angle est converti en % d'ouverture entre `angleFerme` et `angleOuvert`, et donné à
Tasmota par `ShutterSetPosition<id>` : à l'arrêt d'une course, au démarrage et à chaque lecture de surveillance. Avec
`ShutterInvert 1` (posé par `configVRByJson`), la position Tasmota vaut 100 − % d'ouverture. **Jamais pendant une
course** : `ShutterSetPosition` remet la direction du Shutter à 0 sans couper le moteur. Un écart de moins de 2 % ne
renvoie rien, pour ne pas réécrire les réglages à chaque lecture ; après une course, la position est toujours renvoyée
(l'estimation au temps de Tasmota a pu dériver).

Les commandes `ShutterSetOpen/Close/Position` envoyées moins de `ShutterMotorStop` (500 ms par défaut) + 100 ms après
un arrêt partent en différé : dans ce délai, Tasmota attend la fin de l'arrêt moteur en bouclant sur `loop()`, ce
qu'il ne faut pas provoquer depuis Berry. Une commande différée est abandonnée si une course a repris entre-temps.

### Arrêt en butée

Un volet en course vers une butée désignée `"Inclinaison"` (`capteurOuvert` en ouverture, `capteurFerme` en
fermeture) est arrêté dès qu'il l'atteint : `ShutterStop<id>`, puis recalage de la position. Il l'est aussi aussitôt
s'il y est déjà et qu'on le commande encore vers elle. L'arrêt passe AVANT le recalage : `ShutterStop` coupe le moteur
sur-le-champ, alors que `ShutterSetOpen/Close` seul ne le coupe pas (`xdrv_27_esp32_shutter.ino`). Une butée tenue
par un fin de course physique (`SwitchN`) n'est pas arrêtée par l'inclinaison.

### Apprentissage des butées

Plutôt que de régler `axes` et les angles à la main :

1. amener le volet en butée **ouverte** (commande habituelle), puis `ReglageVolets Apprentissage 1 ouvert` ;
2. amener le volet en butée **fermée**, puis `ReglageVolets Apprentissage 1 ferme`.

Les 2 butées relevées, la carte choisit les axes (l'axe de rotation est celui qui varie le moins) et l'ordre qui
évite la coupure ±180° de l'angle, écrit `axes`, `angleOuvert` et `angleFerme` dans le persist et l'enregistre.
L'apprentissage **ne commande jamais le moteur**. Il est refusé, sans rien écrire, si les butées sont à moins de
10° l'une de l'autre, ou si l'arc traverse la coupure dans les deux ordres (tourner le capteur d'un quart de tour).
Un redémarrage entre les 2 temps efface la 1re butée : recommencer. L'apprentissage marche aussi avec l'inclinaison
désactivée, ce qui permet de régler avant d'activer.

`ReglageVolets Inclinaison 1` affiche l'angle mesuré et l'état qu'il donne, sans recaler le volet.

### Sur la page d'accueil

Une ligne `<nom du volet> : inclinaison  85.3 ° (ouvert)` par volet dont l'inclinaison est active. Elle montre le
**dernier angle relevé** (au démarrage, pendant la course, à l'arrêt), sans relire le bus à chaque rafraîchissement :
une trappe bougée à la main n'y apparaît qu'à la prochaine manœuvre. « capteur muet » après une panne du capteur.

### Banc

`python outils_docs/scripts_python/berry/banc_inclinaison.py` : le vrai `vrFonctions.be` sous `berry.exe`, avec un
faux bus I2C et une horloge simulée (garde d'activation, angles, hystérésis, recalage, suivi pendant la course, pannes,
apprentissage, blocage, ligne web). Code de sortie 0 = vert. Ne teste ni le vrai bus, ni le vrai Shutter, ni le capteur physique.

## Visuel des volets et réglage de leurs durées (cartes à volets)

Deux ajouts au driver des volets (`data/fs/controleVoletRoulants.be`), sur les cartes dont le persist décrit une façade : le grenier du RDC, le P4 du garage et le grenier du 2e étage. Le rideau du garage dessine aussi la porte, avec la position lue chez le P4 (§ « La façade du rideau du garage »). Spec : `docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md` ; plan : `tasks/plans/visuel-reglage-volets.md`. Maquettes : `outils_docs/volets_visuels/`.

### La façade sous les curseurs

Sur la page d'accueil, sous les curseurs des volets, un dessin de la façade (`data/sd/js/volets.js`, inséré par `data/fs/vrPages.be::accueil`). Chaque ouverture porte son pourcentage d'ouverture (100 % = ouvert). Le dessin ne commande rien : les curseurs et boutons natifs restent les seules commandes.

- Il lit la valeur du curseur `s27<n>` que Tasmota met déjà à jour à chaque rafraîchissement : aucune requête de plus. Sur un volet `inverse 1`, le curseur affiche l'inverse du dessin (porte ouverte : curseur à 0, dessin à 100 %). C'est voulu, le dessin montre la position physique.
- Il rejoint la dernière valeur lue à la vitesse du volet (`100 / tempsMontee` %/s en montée, `100 / tempsDescente` en descente), sans la dépasser. Il a donc au plus un rafraîchissement de retard et ne montre jamais une position non atteinte.
- Trappe avec MPU6050 actif : le dessin suit l'angle mesuré (balise `data-vi` de la ligne d'inclinaison, `vrFonctions.be::ligneWebInclinaison`), converti comme `positionReelle`. Capteur muet : retour au curseur. Un blocage ou un sens inverse détecté passe l'ouverture en rouge avec « bloqué » ou « sens inverse ».
- Types d'ouverture : `fenetre`, `porte`, `garage` (tablier à lames), `trappe` (panneau qui se baisse), `trappeEchelle` (panneau, puis échelle posée sur un escalier fixe).

### Décrire la façade dans le persist

Dans le bloc `drivers.voletRoulants` :

```json
"facade": { "activation": "ON", "toit": "deuxPans" },
...
"VR1": { "activation": "ON", "inverse": 0, "facade": { "type": "fenetre", "place": 1 }, ... }
```

- `facade.activation` : `"ON"` pour dessiner. `"OFF"` ou bloc absent : rien n'est dessiné, rien n'est envoyé à la page, et le module `vrPages` n'est pas chargé.
- `facade.toit` : `deuxPans`, `unPan` ou `aucun` (plafond vu de face, sans maison).
- `facade` de chaque VR : `type` (`fenetre`, `porte`, `garage`, `trappe`, `trappeEchelle`) et `place`, rang de gauche à droite. Un VR actif sans cette clé n'est pas dessiné.
- Modèle : `outils_docs/schemas/modele_persist.json`. Exemples : `data/rdc/tasmota32s3-grenier/_persist.json`, `data/garage/tasmota32p4-serveur-modbus/_persist.json`, `data/etage2/tasmota32s3-grenier/_persist.json`.

Les fichiers de la page ne partent que sur les cartes à volets : liste `volets_pages` de `[berry_commun]` dans `platformio_tasmota_cenv.ini` (`vrReglage.be`, `vrPages.be`, `volets.js`, `reglageVolets.html`, `.js`, `.css`), exclue des autres envs. `vrFonctions`, `vrReglage` et `vrPages` sont solidifiés sur les envs à façade : firmware à recompiler par la page Build.

### Décor, fins de course et caméra : les clés du persist (2026-11-13)

Plan `tasks/plans/facade-garage-capteurs.md`. Toutes ces clés sont facultatives : sans elles, le dessin reste celui d'avant.

| Clé | Où | Rôle |
|---|---|---|
| `facade.decor` | bloc du driver | Liste. Garage (toit `unPan`) : `chevrefeuille`, `porte`, `pergola`. Rez-de-chaussée : `maison` (toit, briques, porte d'entrée, boîte aux lettres... ; `toit` est alors ignoré). |
| `facade.camera` | bloc du driver | `{"module": "<module>", "id": <id du relais>}` : caméra dessinée sur la maison, avec son voyant. Le relais doit être actif dans son module. |
| `facade.finsDeCourse` | bloc `facade` d'un VR de type `garage` | `{"module": "<module>", "ouverture": <id>, "fermeture": <id>}` : ids des deux interrupteurs dans `modules.<module>.environnement.interrupteurs`. |
| `facade.place` | bloc `facade` de chaque VR | Avec `maison`, l'abscisse vient du type (fenêtre, trappe, porte) ; `place` ne fixe plus que l'ordre. |

Le rythme de lecture n'est pas une clé du persist : c'est le `WebRefresh` de Tasmota.

Réglages actuels : P4 du garage et carte du rideau, `decor: ["chevrefeuille", "porte", "pergola"]` et `finsDeCourse` (ouverture = interrupteur 2, fermeture = interrupteur 1) ; grenier du RDC, `decor: ["maison"]` et `camera: {"module": "autres", "id": 7}` (relais CH7 « Caméra de façade »).

**Fins de course** (P4 et carte du rideau). Deux pastilles sur le rail droit du rideau : ouverture en haut, fermeture en bas. Vert : contact fermé (état `ON`) ; rouge : contact ouvert ; gris : état inconnu ou lecture en échec. Un petit levier bascule avec l'état (fondu de 0,3 s). Une pastille clignote si la position du rideau la contredit plus de 6 s.
- Sur le P4, l'état vient des interrupteurs virtuels tenus à jour par ModBus (`modules.garage`), lus par `GET /volets?f=capteurs`. Le P4 ne sait pas si la carte du rideau est muette : la pastille garde le dernier état reçu.
- Sur la carte du rideau, il est lu sur la broche de l'interrupteur (`modules.rideau`, SwitchMode 1 ou 2), sinon dans sa clé `etat`, et arrive dans la réponse de `/rideau?f=position`.
- Changer de capteur : mettre dans `ouverture` ou `fermeture` l'`id` de l'interrupteur (pas son nom). Pastilles inversées (rideau fermé et pastille du haut verte) : échanger les deux ids.

**Caméra de façade** (grenier du RDC). Voyant vert avec halo si le relais est allumé, gris sinon, relu au rythme du rafraîchissement. Un clic sur la caméra demande confirmation puis l'allume ou l'éteint (`POST /volets`, `action=camera`, réservé à un client autorisé par `webserver.check_privileged_access`).
- Le relais d'`id` N est le `Power<N>` de Tasmota. Sur le grenier du RDC, le relais doit aussi être déclaré dans `tca9554.dat` : `230` (Relay7) en 7e position.
- Changer de relais : modifier `facade.camera.id` (et `module`), activer ce relais dans son module, et le déclarer dans `tca9554.dat` s'il passe par l'expandeur.
- Avec `"afficheWeb": "ON"` sur le relais, l'accueil garde aussi le bouton natif de Tasmota.

**Trappe du RDC**. Pas de fins de course : un rapporteur à droite de la trappe montre l'angle mesuré par le MPU6050 (0° fermée, 90° verticale), lu dans la ligne d'inclinaison de l'accueil. Tant que `capteursPosition.inclinaison.activation` vaut `"OFF"`, il affiche « ?° ».

**Que faut-il renvoyer ?**
- Une clé du persist ou `tca9554.dat` : envoyer le FS de la carte (onglet « Fichiers » de la page Build), puis redémarrer.
- `volets.js` seul : envoyer le FS, sans recompiler.
- `vrPages.be` ou `controleRideau.be` : solidifiés, firmware à recompiler par la page Build (P4 du garage, grenier du RDC, grenier du 2e étage, carte du rideau).
- L'ordre ne casse rien : un ancien firmware ignore les nouvelles clés, un ancien `volets.js` ignore celles qu'il ne connaît pas.

### Régler les durées pas à pas

Page « Configuration » -> bouton **Réglage des volets** (`/volets`, `data/fs/vrReglage.be` et `vrPages.be::route`). Les explications sont aussi sur la page.

1. Préparation : amener le volet en butée basse (fermé) par une commande habituelle. Un seul volet à la fois ; refus si un réglage est déjà en cours, si le volet roule, s'il vient de s'arrêter (moins de `ShutterMotorStop` + 100 ms), ou si un autre volet de la carte roule (le réglage réinitialise tous les volets ; sauf la porte du garage).
2. Choisir le volet, cliquer « Régler les durées ». La carte suspend les boutons natifs de ce volet (les autres gardent les leurs) et autorise une course de 130 s.
3. Un appui : le volet monte, le chronomètre part. Un appui à l'arrivée en haut : arrêt, `tempsMontee` retenu. Un appui : il descend. Un appui à l'arrivée en bas : arrêt, `tempsDescente` retenu.
4. La carte écrit les deux durées (secondes entières) dans son persist, remet les durées et boutons normaux, recale la position (ouvert après la montée, fermé après la descente) et affiche le résultat.

Un appui peut venir du bouton unique, de l'un ou l'autre des deux boutons du volet, ou du bouton « Étape suivante » de la page. Le sens est imposé par l'étape, jamais par la fonction du bouton. Un second appui moins de 1 s après le premier est ignoré. La page demande à chaque départ si le volet va dans le bon sens ; sinon, « Annuler ». Le bouton envoie l'étape qu'il affiche : si l'étape a changé entre-temps (appui physique), la carte répond 409 et la page se resynchronise.

- Annuler : le moteur est arrêté s'il tourne, rien n'est écrit, durées et boutons d'avant remis.
- Délai : 120 s sans appui, même sortie sans rien écrire. Une mesure de moins de 2 s est refusée, de même qu'une arrivée alors que le volet n'a pas bougé (aucun départ rapporté par Tasmota). Si l'écriture du persist échoue, les durées d'avant sont gardées.
- Fins de course et MPU6050 (sauf la porte du garage, en chronomètre : ses fins de course recalent comme d'habitude) : leur recalage et l'arrêt en butée sont coupés pendant la mesure. Le MPU6050 reste garde-fou : un blocage ou un sens inverse coupe le moteur, le réglage s'arrête sans rien écrire et la page donne la cause. S'il a mesuré la course, sa durée s'affiche à côté de la vôtre ; la vôtre est écrite.
- Porte du garage (`mode` 3) : chronomètre seul. La carte ne commande rien. Porte fermée, lancer la porte comme d'habitude (télécommande, curseur) et cliquer « Départ », puis « Arrivée » quand elle est en haut ; même chose pour la descente.
- Un redémarrage pendant le mode le perd sans rien écrire.

### La façade du rideau du garage

Le rideau ne fait pas tourner le driver des volets : c'est le P4 qui pilote la porte. Sa page d'accueil dessine pourtant la même porte (2026-11-12), par `data/garage/tasmota32s3-rideau-garage-modbus/controleRideau.be` et le même `volets.js` :

- Description : la clé `facade` du bloc `drivers.voletRoulants` du persist du rideau et de son VR, comme sur le P4. Ce bloc ne sert qu'à la façade (durées et `capteursPosition`) : il doit suivre celui du P4.
- Position : la page interroge `GET /rideau?f=position&id=1` à chaque rafraichissement (`WebRefresh`), et la carte demande alors `Status 10` au P4 (`serveur.rangeExtender.ipMaitre`). Aucune requête sans page ouverte.
- P4 muet : position tirée des fins de course de la carte (état des interrupteurs désignés par `capteursPosition`, celui que le P4 reçoit par ModBus) : 100 % en butée haute, 0 % en butée basse, « ? » entre les deux. Le dessin est grisé avec « (maître muet) », et une ligne `CONTROLE_RIDEAU_ERREUR` est écrite au passage en muet (une seule, puis une ligne info au retour).
- Pas de page de réglage sur le rideau : les durées se règlent sur le P4.

### Recopier les durées dans le dépôt

Les durées sont écrites dans le persist **de la carte**. Un flash série ou un envoi du FS remet celles du dépôt. La page affiche, en fin de réglage, les deux lignes à recopier dans `data/<lieu>/<carte>/_persist.json` (`drivers.voletRoulants.environnement.VRs.<VR>.tempsMontee` et `tempsDescente`).

### Bancs

- Berry : `python outils_docs/scripts_python/berry/banc_reglage_volets.py` (déroulé complet, annulation, délai, bouton unique en `toggle`, porte en chronomètre ; code 0 = vert) et `python outils_docs/scripts_python/berry/banc_inclinaison.py`.
- Dessin : `node outils_docs/scripts_python/outils_pc/test_volets.mjs` (fonctions pures), puis les sondes Chrome avec le Python de PlatformIO :
  `%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/test_volets_chrome.py` et `.../test_reglage_volets_chrome.py`. Elles arrêtent leur Chrome en fin d'usage ; jamais pendant un build.
- Rideau du garage : `python outils_docs/scripts_python/berry/banc_rideau_facade.py` (route, P4 muet, fins de course ; mutants) ; scénario « rideau » de `test_volets_chrome.py`.
- Démarrage des cartes à façade : `python outils_docs/scripts_python/berry/banc_demarrage.py`.
- Ces bancs ne remplacent pas l'essai sur carte (vrai Shutter, vrais boutons, moteur).

<hr></hr>

## Firmware du coprocesseur Wi-Fi des P4 (ESP32-C6)

Sur le P4, le Wi-Fi passe par un ESP32-C6 (esp_hosted). Son firmware se met à jour à part, par `HostedOta` ; rien ne
le signalait. `data/fs/controleCoprocesseur.be` (solidifié sur le P4, exclu des autres cartes) le fait :

- **Version visée** : celle de la bibliothèque compilée dans le firmware du P4 (champ `Host` de la commande `Hosted`).
  Le C6 doit avoir la même. Le fichier sans numéro de version du serveur n'est pas suivi : il était en 2.12.6 quand
  l'hôte était en 2.12.13 (26/10/2026). La version visée est lue dans `…/coprocessor/v<Host>/network_adapter_<MCU>.bin`.
- **Quand** : au démarrage seulement, car les deux versions ne changent qu'au redémarrage. 20 s après le chargement,
  lecture locale de `Hosted`. C6 à jour : fin, **aucun accès réseau**. C6 en retard : une ligne d'alerte apparaît sur
  l'accueil, puis une seule requête est envoyée 3 min après le démarrage. Elle lit les 512 premiers octets du fichier
  (`Range`), dont l'en-tête d'image donne la version réellement publiée. En cas d'échec réseau, nouvel essai toutes
  les heures, 6 au plus.
- **Page `/coprocesseur`** (lien de la ligne d'alerte) : versions, état sur le serveur, URL. Le bouton « Mettre à jour
  le coprocesseur » (avec confirmation) lance `HostedOta <URL complète>`. Le Wi-Fi du P4 et le point d'accès des
  esclaves sont coupés une à deux minutes, puis le P4 redémarre. L'alerte disparaît si la mise à jour a réussi.
- **Échec et nouvel essai** : le module suit le résultat de `HostedOta` (et de `HostedLoad`, même tapées en console)
  par une règle. Sur `Failed <code>`, la ligne d'accueil indique « échec de la mise à jour ». La page affiche le code et
  sa cause (-1 = téléchargement impossible), puis le bouton revient sous le nom « Réessayer la mise à jour ». Le C6
  garde son firmware et le Wi-Fi marche comme avant. L'échec est journalisé en `erreur`.
- **C6 bloqué (`Failed 5379`)** : `ESP_ERR_OTA_VALIDATE_FAILED`, l'image arrive en entier mais le C6 la refuse. C'est le
  bug [esp-hosted-mcu #143](https://github.com/espressif/esp-hosted-mcu/issues/143) : programme de démarrage d'usine
  en DIO + application 2.1 à 2.8 en QIO reçue par le réseau (cas du P4 du garage, en 2.6.6). Plus aucune mise à jour
  par le réseau ne passe : seul un **flash série du C6** (C6_U0TXD, C6_U0RXD, C6_IO9 à la masse au démarrage, P4 en
  mode téléchargement) avec une version 2.9 ou plus le débloque. Le module note la version bloquée dans le persist
  (`serveur.coprocesseur.bloque`) : ensuite, ni bouton ni requête au serveur, et la ligne d'accueil ne s'affiche que
  pendant la **première minute après le démarrage**. La page `/coprocesseur` (explication, lien du ticket) et le MQTT
  (`"Bloque": true`) gardent l'information. Une autre version lue sur le C6 (flash série fait) efface la clé.
  La clé est **écrite dans le `_persist.json` du dépôt** (P4 du garage, et toute nouvelle carte P4) : une clé
  apprise sur la carte seule serait perdue au flash série suivant, qui réécrit le FS, persist compris.
- **Réglage** : bloc `serveur.coprocesseur` du persist,
  `{"activation": "ON", "url": "https://ota.tasmota.com/tasmota32/coprocessor", "mqtt": "ON"}`.
  Logs sur la cible `general`, préfixe `COPROCESSEUR`.
- **MQTT** (`"mqtt": "ON"`, absent = OFF ; ON sur le P4 du garage) : `tele/<topic>/COPROCESSEUR`, message **retenu**,
  publié à chaque changement d'état (versions lues, réponse du serveur, mise à jour lancée ou ratée) et à chaque
  connexion au broker : `{"MCU": "esp32c6", "Version": "2.6.6", "Attendue": "2.12.13", "AJour": false, "Publiee": true,
  "Lancee": false, "Echec": "Failed 5379", "Bloque": true}` (`Publiee` vaut `null` tant que le serveur n'a pas répondu ;
  `Echec` vaut `null` sans échec). C'est un topic à part : le JSON `SENSOR`, lu par
  Influx et Node-RED sur le Pi et par l'historique, n'est pas modifié.
- **Nouvelle carte P4** : la page « Fichiers Berry par env » pose l'alerte selon la **puce de la base**, quel que soit
  le modèle (`fichiers_berry_coprocesseur.py`). Sur une base P4, elle ajoute le bloc au persist (avec
  `"bloque": "2.6.6"`, ajoutée aussi à un bloc qui ne l'a pas, voir « C6 bloqué »), ajoute la ligne
  `demarrage.charge` à l'autoexec et retire le module des exclusions. Pour une carte d'une autre puce créée depuis le
  P4, elle passe `activation` à `OFF`, retire le module de la solidification et l'exclut du LittleFS. Chaque
  ajustement est annoncé dans la page et visible dans le diff.
- **Banc** : `python outils_docs/scripts_python/berry/banc_coprocesseur.py` (code 0 = vert ; inclut le rendu de la
  page dans Chrome ; `--sans-navigateur` pour la partie Berry seule).

<hr></hr>

## Sniffeur I2C (page web)

Voir en direct ce qui passe sur le bus I2C de n'importe quelle carte du parc, décodé jusqu'au registre des puces
connues, et lire ou écrire un registre. Tasmota ne sait pas écouter un bus I2C (son contrôleur est maître, ou
esclave d'une seule adresse) : l'écoute est faite par un **ESP32-S3 DevKit dédié** (pas une carte du parc) qui
fait tourner un petit firmware et envoie une ligne par transaction sur son USB. Conception :
[docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md](../docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md).

### Matériel et câblage

| Sniffeur (ESP32-S3) | Bus observé |
|---|---|
| GPIO4 | SDA |
| GPIO5 | SCL |
| GND | GND (indispensable) |

- **Bus en 3,3 V seulement** : les entrées de l'S3 ne supportent pas 5 V.
- Le sniffeur n'ajoute aucune résistance de tirage et n'émet rien en écoute : il ne change rien au bus.
- Au PC : le port **USB natif** du DevKit (marqué « USB »), pas le port « UART ».
- Broches à changer : `build_flags` (`BROCHE_SDA`, `BROCHE_SCL`) de
  [firmware_sniffeur_i2c/platformio.ini](firmware_sniffeur_i2c/platformio.ini).

### Flasher le firmware (une fois)

```
pio run -d outils_docs/firmware_sniffeur_i2c -t upload --upload-port COMn
```

Projet PlatformIO **autonome** (même plateforme et même framework que Tasmota, déjà installés), mais c'est un
`pio run` : **jamais pendant un build Tasmota** (le hook `garde_build` le refuse). Le cœur 1 de l'S3 lit les
broches en continu, sans interruption ; c'est pourquoi le firmware coupe le chien de garde des interruptions du
cœur 1, et le commentaire de tête de `src/main.cpp` dit pourquoi. La machine à états I2C (`src/machine_i2c.h`)
a son banc sur PC : `python outils_docs/firmware_sniffeur_i2c/banc/lance_banc.py` (code 0 = vert ; g++ ou Build
Tools Visual Studio).

### Lancer la page

Tuile « Sniffeur I2C » de l'annuaire (groupe « Bus et cartes »), tâche VS Code « Outil : sniffeur I2C », cible
Custom « Sniffeur I2C (HTTP 127.0.0.1) », ou :

```
%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/sniffeur_i2c.py
```

`--port auto` (défaut) interroge par `?` les ports USB Espressif et Raspberry Pi, et ne garde que celui qui
répond comme un sniffeur : une carte Tasmota branchée en USB est écartée. Le port s'ouvre sans DTR/RTS.

### Vitesse

- **100 kHz** (défaut de Tasmota) : garanti.
- **400 kHz** : dépend de la vitesse d'échantillonnage affichée dans la barre du haut (en MHz ; il faut environ
  4 MHz). À vérifier sur le bus réel. Si des transactions sont **perdues** ou **tronquées** en nombre, l'S3 ne suit
  pas : rester à 100 kHz (le Pico, plus tard, tiendra 400 kHz avec le même protocole).

### Ce que montre la page

- **Fil** : adresse, W/R, octets, NACK, fin (STOP, RESTART, TRONQUE), fréquence de SCL, puce, registre et valeur
  traduite. Puces décodées : ADS1115, MCP23017, TCA9554, DS3231, MPU6050, ES8311 (noms seuls).
- **Carte observée** : deux puces partagent 0x20 (MCP23017, TCA9554) et 0x68 (DS3231, MPU6050). La carte choisie
  donne ses puces actives, lues dans son `_persist.json`. Sans carte, la trame est marquée ambiguë, jamais mal nommée.
- **Filtres** (adresse, écritures, lectures, NACK seuls, texte), **pause**, **inventaire** par adresse (transactions,
  NACK, fréquence), **alertes** (NACK répétés, trame tronquée, pertes du sniffeur, bus bloqué).
- **Journal** continu : `%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\sniffeur_i2c_<date>.log` (30 jours) ;
  **export** .txt / .json.

### Lire ou écrire un registre (onglet « Envoi »)

- **Par la carte** (bus en service) : la carte, seul maître du bus, reçoit par HTTP ou par MQTT
  `Br (wire1.detect(0x48) ? wire1 : wire2).read(0x48, 0x01, 2)` (ou `.write(...)`). `wire1`/`wire2` plutôt que
  `tasmota.wire_scan`, qui rend `nil` pour une puce déjà prise par un pilote C de Tasmota. L'IP est proposée
  d'après le dépôt (`WIFI_IP_ADDRESS`, ou `<ip du maître>:<port>` pour un esclave du range extender, qui exige le
  `RoutageRangeExtender` du maître). **Voie MQTT** (liste « par ») : `cmnd/<topic>/Br`, réponse lue sur
  `stat/<topic>/RESULT`, par le broker de `user_config_override.h` ; topic proposé d'après le `_persist.json` de la
  carte observée, et voie choisie d'office pour un esclave (il joint le broker par la sortie du maître). La commande
  est **montrée avant l'envoi**, une seule à la fois, et toute écriture demande une confirmation. Le fil dit
  ensuite « trame vue » ou « trame NON VUE » (sniffeur branché sur un autre bus).
- **Par le sniffeur** (au banc) : le sniffeur devient maître à 100 kHz, **uniquement sur un composant débranché de
  sa carte** (case à cocher). Le firmware refuse si le bus a vécu dans les 2 dernières secondes.

### Bancs

- `outils_pc/test_sniffeur_i2c.py` (Python de PlatformIO, code 0 = vert) : protocole, décodeur, alertes,
  rapprochement, mode maître, port perdu, journal, HTTP. Les trames du décodeur viennent des fiches techniques
  (marquées PROVISOIRE) en attendant des captures réelles.
- `outils_pc/test_sniffeur_i2c_page_chrome.py` : la page dans un vrai Chrome (faux sniffeur, aucun port COM).
- `firmware_sniffeur_i2c/banc/lance_banc.py` : la machine à états du firmware.

<hr></hr>

## Lieu de travail : annuaire, syslog et sniffeur MQTT

Le lieu (garage, cave, bureau...) vient de la seule table `outils_pc/lieux.py`. Les noms d'hôte, les topics et les adresses IP
des cartes sont lus dans les `_persist.json` du dépôt (`lieux.py::identites`), jamais saisis à la main.

- **Annuaire (7600)** : la rangée de puces « Lieu de travail » (Tous, puis un lieu par puce) ajoute `?lieu=<code>` au lien
  « Ouvrir » des outils qui s'en servent (Build, Fichiers Berry, Assistant persist, Atelier des graphiques, Fabrique d'extensions,
  syslog, sniffeur MQTT). Rien n'est caché ni arrêté ; le choix est retenu par le navigateur.
- **Syslog (7200)** : des puces de lieu (Tous, un par lieu, Autres) comptent les lignes et les erreurs de chaque lieu et filtrent
  la liste, la barre et la liste des modules. Chaque ligne porte l'étiquette de son lieu, tiré du nom d'hôte (casse ignorée) puis,
  à défaut, de l'IP de l'émetteur ; un hôte inconnu va dans « Autres ». Le lieu choisi n'est pas mémorisé d'une visite à l'autre.
- **Sniffeur MQTT (7100)** : mêmes puces et même étiquette sur les messages (lieu tiré du topic de la carte), sans toucher aux
  abonnements. L'arborescence des topics est rangée par lieu, l'env de la carte entre parenthèses sur son nœud ; les listes de
  cartes des panneaux « Logs » et « Commande » sont groupées par lieu. Le lieu choisi n'est pas mémorisé.
- **Arrivée avec `?lieu=`** : la page ouverte met le lieu en avant une seule fois, avec un bandeau « Lieu : X (depuis l'annuaire) »
  et une croix « Tous les lieux ». La croix retire le paramètre et le bandeau ; sur le syslog et le sniffeur MQTT,
  elle remet aussi la puce « Tous ». Ailleurs, elle ne change aucune liste. Un code inconnu est ignoré.
  Pour la page Build, voir « Arrivée avec `?lieu=` » plus bas.

<hr></hr>

## Build et téléversement (page web)

Une page pour compiler et téléverser plusieurs cartes d'un seul écran, sans éditer les `.ini` :
on coche des environnements PlatformIO et des actions, on choisit COM ou OTA **ligne par ligne**, et
la page enchaîne les `pio run` en montrant l'étape, le pourcentage, les durées et les échecs en direct.
Conception : [spec](../docs/superpowers/specs/2026-10-24-page-build-televersement-design.md) ; plan :
`tasks/plans/page-build-televersement.md`.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Maintenance » : « Build et téléversement ». La page
  ne s'arrête pas avec l'annuaire pendant un lancement, et l'annuaire refuse de l'arrêter tant qu'un lancement
  est en cours.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : build et téléversement (http://127.0.0.1:7700) ».
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/build_web.py` (`--http 7700`,
  `--local` pour n'écouter que ce PC, `--sans-navigateur`). Depuis un autre appareil du réseau : le lien à jeton
  affiché dans la console (comme les autres outils).
- **Cible PlatformIO** « Build et téléversement (page web) » dans *Project Tasks > <env> > Custom* (n'importe quel
  env ESP32) : ouvre la page si elle tourne, sinon la démarre **détachée** (console dans
  `%LOCALAPPDATA%\outils_tasmota\consoles\build.log`) et rend la main en quelques secondes — une cible est un
  `pio run`, encore vivante elle serait prise pour un build en cours. La page survit à la cible : l'arrêter par
  l'annuaire. Comme toute cible, **jamais pendant un build** (risque de purge de `.pio/build`).

### Les environnements et les actions

- **Classement** : *Mes cartes* (envs de `platformio_tasmota_cenv.ini`), *Mes bases* (`tasmota32-base`,
  `tasmota32s3-base-N16R8`, `tasmota32p4-base-*`) et *Tasmota (amont)*, replié par défaut, en sous-groupes
  (safeboot, ESP32, langues, ESP8266).
- **Classer par** Famille / Lieu / Puce (barre au-dessus de la liste) : en Lieu, les cartes sont rangées par
  emplacement dans la maison (2e segment du nom d'env, table de `outils_pc/lieux.py`), en Puce par ESP32, ESP32-S3,
  ESP32-P4, ESP8266 ; « Mes bases » et l'amont restent en dessous. La case d'un groupe coche ou décoche ses cartes
  visibles ; un groupe s'ouvre à l'arrivée s'il contient une carte cochée. Le classement est retenu par le navigateur
  et ne change rien à ce qui est coché ni à ce qui part. **Filtrer par nom** réduit la liste ; un env coché caché par
  le filtre est signalé en orange, il part quand même au lancement.
- **Arrivée avec `?lieu=`** (lien de l'annuaire) : la page passe en classement Lieu pour cette visite seulement (le classement
  retenu par le navigateur n'est pas réécrit), ouvre le groupe du lieu, affiche le bandeau « Lieu : X (depuis l'annuaire) » et
  ne coche rien. La croix du bandeau rend le classement retenu. Les onglets Fichiers, Mémoire et Sauvegardes choisissent
  la première carte du lieu si rien n'est déjà choisi.
- **Cinq actions**, combinables, appliquées à tous les envs cochés : compiler, téléverser le firmware, effacer puis
  téléverser (voir plus bas), construire le file system, téléverser le file system. Dans un env, l'ordre est
  toujours compiler, téléverser (ou effacer puis téléverser), construire le FS, téléverser le FS, en ne lançant que
  ce qui est coché. Un échec arrête **cet env** (étapes
  suivantes « annulées ») ; les autres envs continuent.
- **Solidification contrôlée dès la fin du pré-build** (compiler, téléverser, effacer puis téléverser) : si un
  module ou une classe inscrit dans `lib/libesp32/berry_custom/src/modules.h` n'a aucune définition dans les `.h`
  solidifiés, la page arrête `pio` aussitôt, avec le motif « solidification vide : <module> (cause) », au lieu
  de laisser l'édition des liens échouer une heure plus tard sur `undefined reference to be_native_module_<module>`.
  Cause habituelle : le `.be` déclare `module("X")` sans la ligne `#@ solidify:X` (cas de `demarrage.be` le
  2026-10-26).
- **COM ou OTA par ligne.** Le port COM est lu dans le `upload_port` de l'env (y compris hérité par `extends`),
  vide s'il n'y en a pas. L'IP OTA est lue dans `WIFI_IP_ADDRESS` de `tasmota/user_config_override.h`, bloc du
  firmware de l'env. L'OTA est grisée pour les envs qui ne chargent pas `pre_utilitaires_platformio.py` (ESP8266)
  et pour les safeboot de l'amont.

### Le port COM : lu, et réécrit dans le `.ini`

Un port modifié sur la page d'un env **personnel** est réécrit dans la section `[env:…]` de
`platformio_tasmota_cenv.ini` (le `.ini` reste la référence : un `pio run` lancé depuis VS Code prend le même
port) : commentaires et alignement gardés, ligne ajoutée dans la section de l'env même si la valeur venait d'un
`extends` (une ligne `; upload_port` n'est jamais décommentée), champ vidé = ligne active supprimée. Une copie
`platformio_tasmota_cenv.ini.bak` est faite avant chaque écriture ; l'écriture est refusée pendant un lancement ou
un build.

> [!WARNING]
> Réécrire le `.ini` change l'empreinte du projet : le **build suivant repart de zéro** (PlatformIO supprime
> alors tout `.pio/build`, tous envs compris). La page le rappelle à côté du champ. Pour un env de l'amont, un
> port saisi vaut pour le lancement seulement (`--upload-port`) : aucun fichier n'est écrit.

### Ce qui fait recompiler (et ce qui ne le fait plus)

- **Purge de `.pio/build`** (tous envs) : PlatformIO la fait dès que l'empreinte du projet change. Or elle change à
  chaque **changement d'env** (le `data_dir` de `platformio_override.ini` et les `_temp_be_*.c` de `berry_custom`
  dépendent de l'env), à chaque **changement de port COM** dans la page, et à toute édition d'un `.ini`. Après une
  purge, l'essentiel est recopié depuis le **cache objet** `.cache` (option `build_cache_dir`) au lieu d'être recompilé.
- **`tasmota.ino.cpp` et tout Berry** (175 fichiers sur la cuve : `berry_conf.h` inclut `my_user_config.h`, donc
  `user_config_override.h`) : depuis le 2026-11-01, un `CFG_HOLDER` inchangé les laisse reprendre du cache. `CFG_HOLDER` n'est plus
  incrémenté à chaque `pio run`, seulement si `user_config_override.h` (hors ligne `CFG_HOLDER`) a changé depuis le
  dernier incrément. Une carte qui a sa section `#elif defined(FIRMWARE_...)` dans ce fichier y porte son propre
  `CFG_HOLDER` (posé au premier incrément) : seule la partie commune du fichier ou sa section le font changer ; modifier la
  section d'une autre carte ne recharge pas ses réglages SECTION1 (le fichier ayant changé, elle recompile quand même). La sortie de pio l'annonce (« CFG_HOLDER inchangé : … » ou « CFG_HOLDER incrémenté : … »).
  Conséquence : un flash ne recharge les réglages SECTION1 (Wi-Fi, MQTT, syslog…) que si ce fichier a changé ; un
  « Effacer puis téléverser » les recharge toujours. Modifier un `_persist.json` ne recompile rien : il part avec le FS.
- **Le cache grossit sans fin** (17 Go le 2026-11-01) :
  `python outils_docs/scripts_python/maintenance/purge_cache_build.py --dry-run` montre ce que libérerait la
  suppression des objets inutilisés depuis 30 jours ; sans `--dry-run`, il les supprime (refus pendant un build).
  Même purge sur la page Build (:7700), onglet Build : bouton « Purger le cache de compilation », avec confirmation.
- **Windows Defender** : `outils_docs/scripts_python/maintenance/exclusions_defender.ps1`, en administrateur,
  exclut `.pio`, `.cache` et `~/.platformio` de l'analyse en temps réel.

### Le dossier `data_dir` : posé avant chaque `pio run`

Avant de lancer pio pour un env personnel, la page pose `data_dir` de `platformio_override.ini` sur le dossier de
l'env (`data/<lieu>/<carte>`), et le signale dans la sortie (« data_dir = … (posé par la page avant pio) ») quand il
change. PlatformIO lit ce fichier **avant** le pré-script qui le réécrit : sans cela, un « Construire le FS » lancé
seul prenait le dossier de l'env construit juste avant (le 2026-10-26, le P4 a reçu en OTA le FS de la cuve). Le
pré-script corrige aussi le lancement en cours (`PROJECT_DATA_DIR`), ce qui protège les `pio run` lancés depuis VS Code.
Pour le vérifier dans un journal : la ligne `copy_fs_image([... littlefs.bin], ["data\<lieu>\<carte>"])` doit
nommer le dossier de l'env construit.

### L'IP de l'OTA

Lue dans `WIFI_IP_ADDRESS`. Si elle vaut `0.0.0.0` (DHCP) ou manque, la ligne demande une IP à saisir : elle ne
vaut que pour ce lancement (rien n'est réécrit) et la ligne est refusée tant que le champ est vide.

**Esclaves derrière le range extender du maître** (cuve, rideau) : sans IP fixe, la page propose
`<IP du maître>:<8080 + id - 1>` (`192.168.0.43:8081` pour la cuve, `192.168.0.43:8082` pour le rideau), tiré de
`serveur.rangeExtender` du persist de la carte au dépôt (`activation` ON, `id` ≥ 1, `ipMaitre`). La note sous la
ligne dit d'où vient l'adresse (« par le maître », ou « IP fixe de user_config_override.h »). Le champ accepte
aussi une saisie `IP:port`. Avant d'envoyer quoi que ce soit à une adresse `IP:port`, la page (étape
« Connexion par le maître ») :

1. envoie `RoutageRangeExtender` au maître, qui pose ses redirections d'après sa table de découverte (la table
   des redirections se vide à chaque redémarrage du maître) ;
2. demande `Status 5` à la carte jointe par ce port, et compare son nom d'hôte à celui du persist de l'env.

Maître injoignable, Berry du maître arrêté, esclave hors ligne pour le maître (rien derrière le port) ou autre
carte derrière le port : **refus, rien n'est envoyé**. Ensuite, firmware et FS passent par la redirection comme
pour une carte jointe directement.

Pendant tout l'envoi, la page met le maître en `Sleep 0`, puis remet sa valeur, même en cas d'échec : à `Sleep 50`,
le relais du maître marque des pauses de plusieurs secondes et l'esclave abandonne l'envoi au bout de 5 s
(mesure du 2026-10-28 : coupé à 3 % ; à `Sleep 0`, 74 à 102 Ko/s sans pause). Si la valeur n'a pas pu être
remise, la ligne de l'env le dit : la remettre à la main (`Sleep 50` dans la console du maître).

Une carte restée **en safeboot** par un envoi coupé ne connaît plus `Status` : la page la reconnaît à sa page
d'accueil (« SAFEBOOT », titre = `serveur.nom` du persist) et relance l'envoi du firmware sans autre geste.

### OTA du firmware

La page lance `pio run -e X` (compilation), puis envoie elle-même `.pio/build/<env>/firmware.bin.gz` (à défaut, ou
s'il est plus ancien que `firmware.bin` : `firmware.bin`) par `/up` puis `/u2` (protocole de `pio-tools/espupload.py`).
Si la carte n'a qu'une partition OTA (image `0xE9`), la page la bascule d'abord en safeboot par `/u4` ; si l'envoi
échoue ensuite, le message dit que la carte est restée en safeboot (renvoyer un firmware par `http://<ip>/up`).
Succès **prouvé par `Status 2`** : la carte doit
revenir (90 s maximum) avec une version et une date de compilation changées ; le texte de la réponse seul ne
suffit pas. Aucun script de build n'est modifié et il n'y a plus de variable `TASMOTA_OTA_IP`.

### OTA du file system

Tasmota n'accepte pas d'image LittleFS en OTA : la page envoie le **contenu de `.pio/build/<env>/littlefs.bin`**,
l'image que le `buildfs` vient d'écrire (celle qu'un `uploadfs` par câble flasherait), fichier par fichier par
`/ufsu`, `_persist.json` compris. Elle lit l'image avec littlefs-python (Python du penv PlatformIO), avec les
paramètres du `buildfs`, et en extrait les fichiers dans un dossier temporaire. **Pas `littlefs_data`** : ce dossier
est rempli par `post_esp32.py` après chaque édition des liens du firmware, n'est jamais vidé, et ne reçoit
`data/fs`, `data/json`, `data/sd` que pour certaines cibles : il porterait les restes d'un ancien build. Déroulé :

1. construction du FS si elle n'est pas déjà cochée, puis lecture de `littlefs.bin` (absente ou illisible : **rien
   n'est envoyé**, l'env est en échec). **Contrôle d'identité** : le nom d'hôte (`serveur.hostname`, sans casse) et
   le topic (`serveur.mqtt.topic`) du `_persist.json` de l'image doivent être ceux du `_persist.json` de l'env au
   dépôt (`data/<lieu>/<carte>/`). Sinon, ou si l'image n'a pas de persist lisible, **rien n'est envoyé** et le motif
   nomme les deux identités (le 2026-10-26, le P4 avait reçu le FS de la cuve). Sans persist de l'env au dépôt,
   l'étape affiche « identité non contrôlée » ;
2. **sauvegarde du `_persist.json` de la carte** dans `%LOCALAPPDATA%\outils_tasmota\build\persist\<env>-<horodatage>.json`.
   Impossible à télécharger, ou pas du JSON valide : **rien n'est envoyé**, l'env est en échec ;
3. **comparaison avec la carte**, avant toute écriture : place libre (`UfsFree`) et taille de chaque fichier déjà
   présent (pages `/ufsd` des dossiers concernés). Un fichier de même taille est relu et comparé octet pour octet :
   **identique, il n'est pas renvoyé**. Bilan de place, en blocs de 4 Ko : les nouveaux fichiers moins ceux qu'ils
   remplacent. S'il dépasse la place libre, **rien n'est envoyé** et le motif donne les Ko libres et les Ko nécessaires.
   Le FS n'est jamais vidé : `/.settings` (réglages Tasmota), `/.drvset*` (calibrages) et les données des modules
   (`/energie/`…) n'ont pas de copie au dépôt ;
4. envoi des fichiers, sous-dossiers compris, `_persist.json` en dernier. Tasmota refuse un fichier plus gros que sa
   place libre, même s'il en remplace un (« Fichier trop grand ») : dans ce cas l'ancien est **supprimé juste avant**
   d'envoyer le nouveau. Jamais le persist : s'il ne tient pas, l'env est en échec et le persist de la carte reste
   intact. Un refus de la carte affiche sa raison (le texte qui suit « Échoué »). Cas réel du 2026-11-09 : différentiel
   (FS de 320 Ko), arrêt sur `jsParam.js` (37 Ko pour 32 Ko libres) alors que les 4 derniers fichiers étaient identiques ;
5. relecture du `_persist.json` de la carte, comparé octet pour octet à celui envoyé (différent : env en échec,
   **pas de restauration automatique**, le chemin de la sauvegarde est affiché) ;
6. rechargement des globales Berry (`Br import persist …`) ;
7. `Restart 1`, attente du retour de la carte (90 s), relecture du persist. Si le persist relu après le
   redémarrage diffère de celui envoyé, un **avertissement** est affiché avec le chemin de la sauvegarde (l'env
   n'échoue pas : les fichiers sont déjà envoyés et la carte est revenue) ; carte non revenue : env en échec.

### Onglet « Fichiers » : envoyer quelques fichiers du FS

Pour remplacer un ou deux fichiers sur une carte (un `.be` corrigé, un gabarit, le persist) sans renvoyer tout le
file system. Onglet **Fichiers**, en haut de la page (l'onglet ouvert est retenu au rechargement). Deux transports :
**HTTP** (adresse de la carte) ou **MQTT** (par le broker, voir plus bas).

1. **Carte destinataire** (colonne de gauche) : les envs « Mes cartes » envoyables en OTA, sous un intertitre par
   lieu (« GARAGE · 3 »). L'adresse et sa
   provenance sont celles de l'onglet Build (IP fixe de `user_config_override.h`, ou `IP du maître:port` pour un
   esclave du range extender) ; une adresse saisie ici vaut aussi pour l'onglet Build, pour ce lancement seulement.
2. **Préparer la liste** : construit l'image du FS de la carte (`pio run -t buildfs`, comme « Construire le file
   system ») à partir des fichiers **du dépôt**, puis la relit. Refusé pendant un build, comme tout lancement.
3. La liste montre les fichiers **de l'image** (pas ceux de la carte), par dossier : taille, date du fichier au
   dépôt, et « dépôt plus récent que l'image » quand un fichier a été modifié depuis (préparer à nouveau). Cocher
   dans le tableau (la case d'en-tête coche le dossier affiché) ; le panier « À envoyer » les reprend, avec
   « retirer » et le total.
4. **Options**, choisies à chaque envoi :
   - **Recharger Berry** (`BrRestart`) : cochée d'office dès qu'un `.be` ou le persist part (décochable) ;
   - **Redémarrer la carte** (`Restart 1`, puis attente de son retour) : recharge aussi Berry, l'autre case est
     alors grisée. Sans aucune des deux, les fichiers sont seulement écrits.
5. **Envoyer N fichiers**. Le bouton dit pourquoi il est grisé (carte, adresse, liste, fichiers, lancement en cours).
   Si un fichier à envoyer est « dépôt plus récent que l'image », une **confirmation** le nomme : il partirait dans son
   ancienne version (Annuler, puis « Préparer la liste »). Les fichiers de `data/sd` et `data/json` comptent aussi.

Déroulé côté serveur (`build_ota_fs.py::envoie_fs_ota` avec `fichiers=`) :

- l'image envoyée doit être **celle de la liste** : si un `buildfs` l'a réécrite entre-temps, l'envoi est refusé
  (« préparer à nouveau ») ;
- **même contrôle d'identité** que l'OTA du FS : une image d'une autre carte n'est jamais envoyée (la liste
  s'affiche quand même, avec le motif) ; par le maître, même redirection et vérification du nom d'hôte, et maître en
  `Sleep 0` le temps de l'envoi ;
- **si `_persist.json` est coché** (annoncé « sauvegardé avant l'envoi ») : sauvegarde du persist de la carte,
  persist envoyé en dernier, relu et comparé, puis **toujours** rechargé (`persist.load()`) avant tout redémarrage
  (le persist vit en RAM : un redémarrage sans rechargement réécrirait l'ancien par-dessus le nouveau) ; après
  `Restart 1`, relecture comme pour l'OTA du FS. Sans persist coché, rien de tout cela.

L'avancement s'affiche **dans l'onglet** : barre en pourcentage, étape en cours et journal des étapes avec leur
détail (« 2/3 /controleCuve.be »), pour l'envoi comme pour la préparation de la liste. Le Suivi commun, sous les
deux onglets, montre la même chose sur la ligne « Envoyer des fichiers ». Les lancements partis de cet onglet ne
modifient pas les derniers choix mémorisés de l'onglet Build.

**Transport MQTT** (A16) : choisi dans le panier « À envoyer ». Les fichiers passent par le broker de
`user_config_override.h`, en morceaux de 1 900 octets (4 en vol, accusé cumulé, renvoi si un morceau se perd), vers le
module **`data/fs/fsMqtt.be` de la carte**, sous le topic de son persist (`fsmqtt/<serveur.mqtt.topic>/…`).
L'adresse de la carte est inutile : un esclave du range extender joint le broker par la sortie de son maître, sans
redirection ni `Sleep 0`. Débit mesuré : 14 à 18 Ko/s vers la cuve, sans coupure (HTTP : 74 à 102 Ko/s, mais coupé
quand le relais du maître marque une pause). Chaque fichier s'écrit dans `/fsmqtt.tmp` et ne remplace le vrai
qu'après contrôle de sa taille et de son MD5. Même déroulé que l'HTTP (persist sauvegardé par MQTT s'il part, envoyé
en dernier, rechargé ; redémarrage ou `BrRestart`, puis attente du « prêt » du module). **Prérequis** : `fsMqtt.be`
est solidifié dans le socle (toutes les cartes, firmware recompilé) et chargé par l'autoexec de la carte
(`demarrage.charge(["fsMqtt"])` : maître P4 et cuve à ce jour). Sans lui, la page le dit (« aucune réponse sur
fsmqtt/<topic> ») et rien n'est envoyé.

**Effacer tout le FS avant l'envoi** (MQTT seulement, confirmation) : la carte FORMATE son FS (`path.format`,
persist et autoexec compris ; `/sd` de la flash aussi), puis toute l'image est envoyée, **persist en premier** (sans
effacement, il part en dernier) : un échec en cours d'envoi laisse au moins à la carte son persist, celui de l'image ;
celui d'avant reste dans la sauvegarde faite par la page. Le module, solidifié, survit.
Le formatage bloque la carte : s'il dépasse les 5 s du watchdog de la boucle, elle redémarre avec un FS vide, donc
sans autoexec ni Berry : la reprendre en HTTP (cet onglet) ou par câble. Idem si elle redémarre entre les deux. Bancs :
`berry/banc_fsmqtt.py` (module), `outils_pc/test_build_ota_mqtt.py` (PC) ; aucun essai sur carte à ce jour.

#### Arrivée depuis l'atelier des graphiques

Le bouton « Téléverser » de l'atelier des graphiques (voir « Atelier des graphiques ») ouvre la page à l'adresse
`/?env=<env>&depuis=atelier&fichiers=<chemins séparés par des virgules>&redemarrer=<0|1>`. Le code est dans
`build_page_atelier.py::arriveeAtelier` (JS de la page, branché sur l'onglet Fichiers). Avec une liste **vide**
(`fichiers=`, lien « Envoyer par la page Build ↗ » de l'atelier, toujours visible), la page choisit la carte et construit
l'image sans rien cocher : bandeau « cochez les fichiers à envoyer ». Déroulé avec une liste :

1. La page sélectionne l'env, bascule sur l'onglet « Fichiers » et affiche un **bandeau** : « Fichiers sélectionnés
   automatiquement par l'Atelier des graphiques, pour téléverser un graphique nouveau ou modifié. Vérifiez puis cliquez
   sur « Envoyer ». »
2. Elle lance seule la **construction du FS** de l'env (le `buildfs` de « Préparer la liste », par `POST /lancer` avec ses
   en-têtes habituels : un lien ouvert par un tiers ne peut lancer que cela, qui ne touche aucune carte).
3. À la fin réussie de **ce** `buildfs`, elle relit la liste et **coche exactement les fichiers de la liste** présents dans
   l'image neuve. « Redémarrer » est coché si `redemarrer=1`.
4. Elle **n'envoie rien** : l'utilisateur vérifie la sélection puis clique « Envoyer ».

Cas limites :

- **Fichier absent de l'image** : jamais ignoré en silence, le bandeau écrit « Absent de l'image du FS, non coché : ... ».
- **Paramètres hostiles ou invalides** : env inconnu, absent des cartes envoyables en OTA ou de l'amont, chemin avec `..`,
  absolu, `\`, `:` ou caractère de contrôle, liste vide ou de plus de 1 Ko, `redemarrer` autre que 0 ou 1. Chacun est
  signalé par un message, rien n'est coché, et pour un env refusé ou une liste sans chemin valide **aucun `pio` ne part**.
- **Build déjà en cours** : si c'est un lancement de la page, rien n'est envoyé ; le `buildfs` part à la fin du build en
  cours (flux `/flux`). Si le serveur refuse parce qu'un build tourne **hors de la page**, nouvel essai **toutes les 5 s,
  1 h au plus**, avec un message. Toute autre réponse 409 abandonne avec un message.
- **Changement de carte** avant la fin, ou **redémarrage de l'outil** (flux coupé) : la sélection automatique est
  **abandonnée avec un message**. Un `buildfs` en échec ou arrêté ne coche rien et le dit.
- **Rechargement de la page** : l'adresse est ramenée à `?env=<env>` dès que le `buildfs` est accepté, donc un rechargement
  ne relance jamais la construction ; pendant l'attente d'un autre build, il reprend l'attente sans doublon.

### Onglet « Mémoire et partitions » : occupation et table de chaque env

L'onglet s'ouvre sur l'env coché dans l'onglet Build (sinon la première carte) ; la liste en haut (cartes groupées par
lieu, bases en dernier) en choisit un autre sans toucher aux cases.

- **Occupation** : une jauge par partition de la flash et par zone RAM du journal (DIRAM, IRAM, RTC, LP RAM...),
  orange à 85 %, rouge à 95 %. Elle est relevée seule après chaque compilation réussie ; « Analyser » relit le dernier
  build sans rien compiler. La taille du FS est estimée (`≈`) d'après les fichiers de l'image ; PSRAM et tas ne se
  lisent que sur la carte (pas encore dans l'onglet).
- **Table** : un curseur et un champ en Ko par partition, par pas de 64 Ko ; le FS (sinon app0) compense pour que toute
  la flash reste répartie. `nvs`, `otadata` et `app0` ne se suppriment pas. « Voir le diff » fait valider la table par
  le serveur (`build_partitions.py`), puis « Écrire » pose `partitions/env_<env>.csv` et `board_build.partitions` dans
  la section de l'env : la table par défaut, partagée, n'est jamais modifiée. « Partir d'une table existante » règle les
  curseurs sur une table de `partitions/` à la taille de la flash ; si la table finale est identique à un de ces fichiers,
  l'env pointe vers lui et aucun CSV n'est créé (c'est aussi le retour à la table par défaut) (copie d'origine dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`).
- **Importer, exporter, ajouter** : « Importer un CSV » passe par les mêmes contrôles (adresses contiguës, pas de colonne
  Flags), « Exporter en CSV » télécharge la table réglée, « Ajouter la partition » l'insère avant le FS, 64 Ko pris sur lui.
- **Résumé dans l'onglet Build** : sous le nom de chaque env déjà analysé, `app0`, `FS` et `DIRAM` en %, en orange à 85 %, en
  rouge à 95 % comme les jauges. Un clic ouvre cet onglet sur l'env.
- **Lire sur la carte** : interroge la carte par le réseau, en lecture seule (`Status 4`, `Status 5`, `UfsSize`, `UfsFree`), à
  l'adresse de sa ligne dans l'onglet Build : FS réel (le `≈` du dessus est une estimation), PSRAM, tas libre, nom de la carte
  lue. Rien n'est enregistré. Carte muette : un message. Esclave joint par le maître : redirection posée et identité vérifiée
  d'abord. Refusé pendant un envoi.
- **Nom du fichier** : facultatif. Vide, la table part dans `partitions/env_<env>.csv` ; saisi, dans `partitions/<nom>.csv`.
  Un fichier nommé qui existe déjà n'est jamais réécrit, ni un `env_` qui sert aussi à un autre env. « Voir le diff » compare
  la table à TOUS les fichiers de `partitions/` : si elle est identique à l'un d'eux, la page le propose ; OK = l'env pointe
  vers lui, Annuler = un nouveau fichier est créé quand même.
- **4 ou 6 partitions** : acceptées, le FS restant dernier et un safeboot restant en 0x10000. Sans safeboot, l'env reçoit
  `board_upload.arduino.flash_extra_images =` (vide) et l'OTA du firmware est refusée. Avec un FS, le « Téléverser le
  firmware » par câble est refusé, seul « Effacer puis téléverser » passe : `post_esp32.py::patch_partitions_bin` suppose
  5 partitions. ⚠️ La page ne contrôle pas un `pio run -t upload` lancé hors d'elle ; une telle table n'a pas encore été
  essayée sur une carte.
- **Après l'écriture** : la nouvelle table ne part qu'avec un « Effacer puis téléverser » par câble, qui remplace aussi
  le persist de la carte par celui du dépôt. D'ici là, toute OTA de l'env est refusée (une OTA n'écrit jamais la
  table). Le prochain build repart de zéro (le cenv a changé).

### Téléversement série : il emporte `littlefs.bin`

« Téléverser le firmware » **par câble** flashe aussi le file system (persist compris) **à chaque upload par câble**
pour tout env ESP32 dont `custom_files_upload` contient des fichiers (pas seulement `no_files`) : c'est le cas des
cartes et des bases personnelles. `pio-tools/post_esp32.py` reconstruit `littlefs.bin` à chaque édition des liens
(toujours, puisque `CFG_HOLDER` change à chaque `pio run`), même après une purge de `.pio/build`, et l'ajoute à la
commande esptool. Comportement gardé par choix ; la ligne l'annonce avant le lancement (d'après les `.ini`, pas
d'après la présence de `littlefs.bin`), et le suivi le redit au téléversement.

Conséquence (2026-10-26) : « Construire le file system » et « Téléverser le file system » n'apportent rien à un tel
envoi. Si **tous** les envs cochés sont en COM, embarquent des fichiers et « Téléverser le firmware » ou « Effacer
puis téléverser » est coché, les deux cases sont décochées et grisées (infobulle). Dans une série mixte (un env en
OTA ou sans fichiers), elles restent actives : le serveur ne lance alors ni `buildfs` ni `uploadfs` pour les envs
déjà servis par leur envoi, qui prennent le statut de cet envoi (la ligne le dit). `buildfs` lirait d'ailleurs le
`data_dir` du lancement précédent (défaut A12 du plan de la page).

### Calibrage d'énergie gardé autour d'un flash par câble

Avant un envoi du firmware par câble (ou « Effacer puis téléverser »), la page copie `/.drvset003` de la carte par le
réseau (calibrage et compteurs ; rôle des fichiers `.drvset` : onglet « Aide » de la page et `FICHIERS_DRVSET.md`). Après un envoi réussi, elle le renvoie, redémarre par
`Restart 99` (`Restart 1` réécrirait le fichier avec la RAM de la carte neuve) et relit le calibrage. Étape
« Calibrage » sur la ligne de l'env. Carte injoignable ou sans ce fichier : le flash a lieu quand même, sans
rétablissement. Échec du rétablissement : le message donne le chemin de la copie, sous
`%LOCALAPPDATA%\outils_tasmota\build\drvset\`. La même étape prend aussi une sauvegarde de toute la configuration,
d'origine « avant flash », visible dans l'onglet « Sauvegarde configuration ».

### Effacer puis téléverser (`erase_upload`)

Pour une carte dans un état bancal (partitions changées, réglages ou persist corrompus) : la page lance
`pio run -e X -t erase_upload --upload-port COMn`, qui efface **toute** la flash (`esptool erase-flash`) puis
téléverse le firmware, et le file system comme un upload par câble (`post_esp32.py` ajoute `littlefs.bin` à la
commande quelle que soit la cible ; même mention « FS aussi flashé » sur la ligne).

- **Par câble seulement** : la case est grisée si une ligne cochée est en OTA, et le bouton OTA des lignes est grisé
  tant qu'elle est cochée ; le serveur refuse aussi une ligne OTA.
- **L'une ou l'autre** avec « Téléverser le firmware » : cocher l'une décoche l'autre (les enchaîner flasherait deux
  fois) ; le serveur refuse les deux ensemble. Combinable avec compiler ; construire et téléverser le FS sont grisés
  pour un env qui embarque des fichiers (voir plus haut).
- **Confirmation** avant le lancement : le persist (`_persist.json`) et les réglages de la carte (Wi-Fi, MQTT,
  réglages faits sur la carte) sont effacés et remplacés par ceux du dépôt ; un réglage non reporté dans le dépôt
  est perdu. Un env sans file system dans le dépôt repart sans persist (la confirmation le nomme).
- Suivi : étape **« Effacement de la flash »** (recherche du port puis effacement) avant « Téléversement ». C'est un
  envoi comme l'upload : refus si le port est tenu ou absent, pause « rebranchez la carte » s'il est partagé avec un
  env précédent, et un arrêt de la page attend la fin de l'effacement et du téléversement.

### Refus, attente, arrêt

- **Refus avant lancement** : un build tourne déjà (VS Code, cible Custom, même logique que le hook `garde_build`,
  qui ne compte pas les cibles d'outils : un annuaire ou un pont série lancé par sa cible Custom n'est pas un
  build, sauf pendant ses 30 premières secondes, où son démarrage peut encore purger `.pio/build`) ; un port COM tenu par un autre outil (pont série, sniffeur, testeur) ou absent, pour une action d'envoi.
- **Plusieurs cartes sur le même port COM** (pause « rebranchez la carte ») : le lancement est accepté. Pour un env
  dont l'envoi passe par un port déjà servi par un env précédent de la série, la compilation (si cochée) se fait
  d'abord, en un `pio run` à part ; juste avant son premier envoi, la série s'arrête et la page affiche
  « **Branchez la carte X sur COMn puis cliquez Continuer** », avec **Continuer** et **Passer cet env**. Continuer :
  la page attend un éventuel build lancé ailleurs pendant la pause, revérifie le port, puis envoie ; port absent ou
  tenu : **la pause reste ouverte** avec le message dans le bandeau (« COM12 absent : rebranchez puis Continuer »,
  ou tenu par un autre outil), on réessaie ou on passe. Après un clic accepté, les boutons restent grisés jusqu'à la
  suite. Passer : les actions restantes de l'env sont « annulée », l'env est « passé », la série continue. Les deux
  arrêts et le Ctrl+C de la page mettent fin à la pause (rien n'est en cours d'envoi) : l'env est « arrêté », compté
  à part dans le récapitulatif, pas comme un échec. Recharger la page remontre le bandeau tant que la pause dure. La
  ligne cochée au port partagé l'annonce avant le lancement. **Sans recompiler** : quand la compilation a réussi
  avant la pause, l'envoi part en `pio run -t nobuild -t upload` (ou `erase_upload`), qui reprend le firmware déjà
  compilé. Un env dont l'envoi série joint le FS reçoit ensuite son FS par `pio run -t nobuild -t uploadfs` : en
  `nobuild`, la jointure du FS de `post_esp32.py` ne tourne pas (corrigé le 2026-11-01 ; avant, la carte recevait le
  firmware SANS le FS, et un « effacer puis téléverser » la laissait avec un FS vide).
- **Attente** : le contrôle « build en cours » est refait avant chaque env. Si un build est apparu entre deux envs,
  la série attend (« en attente : build en cours ») et reprend à sa fin ; on peut l'arrêter.
- **Arrêt** : « Arrêter après cet env » (propre) ou arrêt immédiat, qui peut laisser une carte à moitié flashée et
  des copies temporaires dans `data/<lieu>/<carte>` (la page les signale, ne les efface pas). Un envoi OTA en
  cours n'est pas coupé, un envoi OTA pas encore commencé est annulé ; un upload fini avec succès reste un succès.
- **Arrêt de la page** (Ctrl+C dans sa console, fermeture) : un envoi vers une carte en cours (téléversement par
  câble, envoi OTA) va d'abord à son terme, puis le reste du lancement est tué ; un second Ctrl+C force l'arrêt.
  L'écriture du port COM est refusée pendant un lancement de la page **et** pendant un build lancé ailleurs.

### Onglet « Env par défaut (Platformio override) » : ce que compile un simple `pio run`

Le bloc `default_envs` de `platformio_override.ini` fixe les envs compilés par un `pio run` sans `-e`. L'onglet le
modifie sans ouvrir le fichier ; il ne lance rien.

- **Colonnes** : une par puce (Safeboot, ESP32, ESP32-S3, ESP32-P4, Autres), avec les lignes du bloc. Vos cartes et bases
  qui n'y sont pas apparaissent aussi, marquées « absent du bloc » : cochées, elles y sont ajoutées dans le groupe de
  leur puce (sinon à la fin du bloc) ; non cochées, rien n'est écrit pour elles.
- **Modifications en attente** : le futur fichier entier, recalculé à chaque case, lignes changées surlignées. Rien
  n'est écrit avant « Enregistrer ». Seul l'état commenté ou actif d'une ligne change : commentaires, indentation et
  fins de ligne restent. Copie d'origine dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`.
- **« Cocher ces envs dans l'onglet Build »** remplace la sélection de cet onglet, sans toucher aux actions : on lance
  ensuite par le bouton habituel. Les cases non enregistrées sont reportées aussi.
- **À la création d'un env** (pages Fichiers Berry par env et Assistant persist) : la case « Ajouter à `default_envs` »,
  décochée par défaut, l'y rend actif du même coup, en une seule écriture ; le diff le montre avant « Créer ».
- **Refus** : liste vide (un `pio run` construirait tous les envs), env inconnu, ligne `default_envs = x` ou ligne à
  plusieurs envs à corriger à la main, écriture pendant un lancement ou un build, fichier changé depuis l'aperçu.
- **À savoir** : enregistrer change l'empreinte du projet, donc le `pio run` suivant vide `.pio/build` (les objets
  inchangés reviennent du cache `.cache`). L'ordre des lignes n'a aucun effet : `pio run` suit l'ordre des sections
  des `.ini`, c'est pourquoi l'onglet ne propose pas de réordonner.

### Onglet « Sauvegarde configuration » : sauvegarder, comparer, modifier, restaurer

Une sauvegarde est le fichier `/dl` de la carte, celui de « Sauvegarder la configuration » de sa page web : ses
Settings (Wi-Fi, MQTT, minuteries, gabarit, règles, `AdcParam`...) **et** ses fichiers `.drvset*` (calibrage,
compteurs ; voir l'onglet « Aide »). Fichiers `AAAAMMJJ-HHMMSS_<origine>.dmp` dans `outils_docs/sauvegardes_cartes/<env>/`,
**ignoré par git** : un `.dmp` porte les mots de passe Wi-Fi et MQTT en clair, et le dépôt est public.

- **Carte** en haut (liste groupée par lieu), avec l'adresse de sa ligne dans l'onglet Build (méthode OTA). Un esclave derrière le Range
  Extender est joint par le maître (`IP:port`), redirection posée et identité vérifiée d'abord, comme pour un envoi.
- **« Sauvegarder maintenant »** : nouvelle sauvegarde « manuelle ». Une sauvegarde « avant flash » est prise seule
  avant un envoi du firmware par câble, une « avant restauration » avant chaque restauration.
  ESP8266 (Sonoff) : Rules, timers et `Mem` sont dans la sauvegarde (Settings). Juste après la prise, la carte est
  interrogée sur ce qu'elle garde ailleurs (fichiers d'un système de fichiers, appareils Zigbee) et sur son firmware ;
  le message de la page (ou le journal, avant flash) dit ce qu'il faudrait récupérer autrement.
- **Paramètres** de la sauvegarde choisie, repliés par thème, avec un filtre (nom ou valeur). Mots de passe affichés
  `***` : laissés ainsi, ils gardent leur valeur. Une valeur changée est surlignée ; « Enregistrer la copie » écrit
  une **nouvelle** sauvegarde « modifiée », l'originale n'est jamais réécrite. La copie est relue et comparée à
  l'attendu : au moindre écart, rien n'est gardé.
- **Origine** de chaque sauvegarde : fixée par l'action qui l'a prise (« manuelle », « avant flash », « avant
  restauration », « modifiée ») et écrite dans le nom du fichier et sa fiche `.json`.
- **Supprimer** : cocher les sauvegardes dans l'historique, puis « Supprimer la sélection » (confirmation ; `.dmp` et
  fiche effacés).
- **« Comparer »** : écarts avec la carte en ligne (rien n'est enregistré) ou avec une autre sauvegarde ; les
  paramètres en écart sont mis en couleur.
- **« Restaurer : <date · origine> »** (la sauvegarde choisie d'un clic dans l'historique ; les cases servent à supprimer) : une fenêtre liste les écarts
  (paramètre, valeur sur la carte, valeur après restauration, marque « ↻ démarrage ») et alerte si le nom d'hôte de la
  carte jointe diffère ; « Restaurer » ou « Annuler » (Échap). Puis un bloc d'avancement suit les étapes du serveur
  (sauvegarde de la carte d'abord, envoi, redémarrage, relecture) et donne le résultat : sauvegarde d'avant, écarts
  relus, et ceux reposés au démarrage. Refusée pendant un envoi de la série, et pour une sauvegarde d'une autre puce.
- **À savoir** : au démarrage, le persist et l'`autoexec.bat` reposent leurs réglages ; ils l'emportent sur une
  valeur restaurée. Ces paramètres portent la marque **« ↻ démarrage »** ; son survol nomme la source et la commande
  (`autoexec.bat (SerialLog)`, `persist (Hostname)`). La marque vient de la commande Tasmota de chaque paramètre
  (decode-config) comparée aux lignes de l'`autoexec.bat` de la carte et aux commandes que `data/fs/configGlobal.be`
  pose depuis le persist (`build_sauvegarde::reposes`). Une commande de `configGlobal.be` ne compte que si le persist de
  la carte la fait poser : clé remplie, MQTT actif pour `MqttHost`/`Topic`..., voie Ethernet pour `EthIPAddress`...
  (table `build_sauvegarde::POSEES`, tenue à la main ; le banc exige une ligne par commande de `configGlobal.be`).
  Les niveaux de logs du profil actif (`SerialLog`, `WebLog`, `MqttLog`, `SysLog`) sont comptés aussi.
- **Liaison** : « HTTP (adresse) » par défaut ; **« MQTT (broker) »** pour une carte que ce PC ne joint pas en HTTP.
  La carte est jointe par le broker de `user_config_override.h` et le topic de son persist au dépôt, par les commandes
  `FileDownload` / `FileUpload` de Tasmota (`build_sauvegarde_mqtt.py`) : même fichier que `/dl`, même déroulé
  (sauvegarde d'avant, envoi, relecture une fois la carte revenue sur le broker). Le `MqttPassword` de la carte doit
  être le `MQTT_PASS` du `.h`. Essai réel du 2026-11-03 sur le différentiel : lecture en 2 s.
- **Purge automatique** (case sous l'historique, cochée par défaut, commune à toutes les cartes, mémorisée dans
  le fichier « reglages.json » du dossier des sauvegardes ; décochée, rien n'est effacé seul) : à chaque sauvegarde « avant flash » ou « avant restauration », celles de ces deux origines
  de **plus de 90 jours** sont effacées, en gardant toujours les **5 plus récentes** de chaque origine. Une sauvegarde
  « manuelle » ou « modifiée » n'est jamais effacée seule (`build_sauvegarde::purge`).
- **decode-config** (tasmota/decode-config) lit et écrit les paramètres. Il vit hors du dépôt et du Python de
  PlatformIO, dans `%LOCALAPPDATA%\outils_tasmota\decode_config\` : `python outils_docs/scripts_python/outils_pc/decode_config.py`
  l'installe (`--verifier` pour contrôler). Sans lui, sauvegarde et restauration restent possibles, pas la lecture des
  paramètres. Une version de Tasmota plus récente que la sienne n'est lisible qu'une fois sa disposition comparée
  (`decode_config.VERSIONS_VERIFIEES`) ; sinon la sauvegarde reste restaurable mais pas modifiable. Les textes
  (nom d'hôte, textes des boutons...) sont écrits par l'outil lui-même : decode-config 16.0.0.0 tronque la réserve de
  textes d'un ESP32 en les écrivant.

### Journaux, mémoire de la page, fichiers réécrits

- Sortie complète de chaque `pio run` (avec ses codes de couleur ANSI, retirés par « Journal complet ») : `%LOCALAPPDATA%\outils_tasmota\build\journaux\`,
  dépliable sur la page (« Journal complet »). Les journaux d'un env se lisent dans l'ordre de leur **date de
  modification** (pas l'heure écrite dans le nom, qui recule au passage à l'heure d'hiver). Au démarrage de la page,
  les journaux de **plus de 30 jours** sont supprimés (une suppression impossible est comptée dans la console) :
  seulement les journaux de la page (`date-heure-env-action.log`), et pas si une autre instance tient déjà le port.
- **Sortie de pio en direct** : mêmes couleurs que le terminal de VS Code (`PLATFORMIO_FORCE_ANSI`, palette du thème sombre par défaut, `build_page_couleurs.py`) ; sous chaque env du suivi, un panneau « Sortie de pio (en direct) », ouvert au départ
  de l'env, montre les lignes de pio au fil de l'eau comme le terminal de VS Code (chasse fixe, fond sombre, erreurs
  en rouge, avertissements en orange). Il défile seul tant qu'on est en bas, et s'arrête si on remonte pour lire.
  Il se **referme quand l'env réussit**, sauf si on l'a ouvert ou fermé soi-même ; il reste ouvert en échec ou arrêt.
  Au rechargement de la page, les envs réussis ne rouvrent pas le leur.
  Les barres d'esptool qui se réécrivent tiennent sur **une ligne par zone**, mise à jour (bootloader, firmware,
  `littlefs.bin`…). La page lit le journal de **cet** env par morceaux (`GET /sortie?env=…&octet=…` : seulement la
  suite, en lignes entières) ; la sortie d'un env terminé reste lisible tant que la page est ouverte.
- **Sons** (interrupteur en haut à droite, à côté de « Mode sombre », coché par défaut, mémorisé dans le
  navigateur) : à la fin d'un lancement, la page joue deux notes **montantes** si tous les envs ont réussi, deux
  notes **descendantes** en cas d'échec, d'arrêt ou si aucun env n'a abouti ; **trois bips aigus** quand elle se met en
  pause « Branchez la carte X sur COMn » (le lancement attend votre geste). Le son sort du PC qui affiche la page
  (Web Audio, sans fichier), même si l'onglet est en arrière-plan. Le navigateur ne laisse sonner une page qu'après
  un geste de l'utilisateur : le clic sur « Lancer » suffit. Après un rechargement de la page en plein lancement,
  cliquer une fois n'importe où dans la page. Une fin ou une pause déjà passée, rejouée au rechargement, ne sonne pas.
- Derniers choix : à chaque lancement accepté, la page
  écrit les lignes lancées (env, COM ou OTA, port, IP saisie) et les actions cochées dans `derniers.json` (dans
  `%LOCALAPPDATA%\outils_tasmota\build\`, hors dépôt, écriture atomique) ; à l'ouverture suivante elle recoche ces
  lignes et ces actions, sauf « Effacer puis téléverser », jamais recochée. Le port
  mémorisé ne sert que pour un env dont le port n'est pas réécrit dans un `.ini` (envs de l'amont), l'IP mémorisée
  que si aucune IP n'est lue dans `user_config_override.h`.
- Références de progression (nombre de `.o` du dernier
  build réussi de chaque env, base du % de compilation ; durée de chaque zone du dernier envoi par câble, base du
  % de l'envoi) : `references.json` dans
  `%LOCALAPPDATA%\outils_tasmota\build\`, hors dépôt. Un env jamais compilé par la page emprunte le total
  du plus grand env de la même puce (`tasmota32s3`, `tasmota32p4`…), affiché « 337/≈1682 fichiers » ;
  sans env de la même puce, seul le nombre de fichiers s'affiche.
- **Pourcentage pendant l'envoi** (ligne « Téléversement » de l'env) :
  - **par câble** : esptool écrit plusieurs zones (bootloader, partitions, boot_app0, safeboot, firmware,
    `littlefs.bin`). Dès le deuxième envoi du même env, la barre donne **un seul %** pour l'envoi entier, pondéré par
    la durée de chaque zone au dernier envoi (le FS, effacé avant d'être écrit, pèse plus que sa taille), avec
    « littlefs.bin 40 % · zone 6/6 ». Au premier envoi, ou si les zones ont changé, le % reste celui de la zone en cours ;
  - **OTA du firmware** : le % de l'envoi HTTP, un point à la fois ;
  - **OTA du FS** : le % des **octets** envoyés (pas du nombre de fichiers), mis à jour pendant chaque fichier, avec
    « 3/17 js/echarts.min.js.gz ».
- Chaque `pio run` réécrit `platformio_override.ini` et `tasmota/user_config_override.h` (`CFG_HOLDER`) :
  **fichiers à commiter** après un lancement (la page le rappelle en fin de lancement), et à sauvegarder avant
  une série d'essais.
- Banc : `test_build_*.py` dans `outils_docs/scripts_python/outils_pc/` (faux `pio`, carte simulée ; code de sortie
  0 = vert), à lancer avec le Python du penv PlatformIO ; détection des builds (cibles d'outils ignorées après leurs
  30 premières secondes) :
  `outils_docs/scripts_python/build/test_garde_build.py`.

<hr></hr>

## Fichiers Berry par env (page web)

Une page pour décider, carte par carte, ce que devient chaque fichier Berry : **sur le file system**, **exclu** ou
**solidifié** dans le firmware. Elle écrit les listes de `platformio_tasmota_cenv.ini` (`custom_files_upload`,
`custom_files_exclude`, `custom_berry_solidify`) à la place d'une édition à la main, et crée un nouvel env à partir
d'une carte existante, renomme ou supprime un env. Conception : [spec](../docs/superpowers/specs/2026-10-25-page-fichiers-berry-design.md) ;
plans : `tasks/plans/fichiers-berry-env.md`, `tasks/plans/fichiers-berry-suppression.md`.

Les listes de cartes (env affiché, carte modèle d'une création) sont groupées par lieu de la maison, « Mes bases » en
dernier (table de `outils_pc/lieux.py`, commune aux pages des outils). Ouverte avec `?lieu=` (lien de l'annuaire), la page choisit
la première carte du lieu (sauf si `?env=` est donné) et affiche le bandeau du lieu, sans rien cocher.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Maintenance » : « Fichiers Berry par env ». L'annuaire
  peut l'arrêter à tout moment : rien n'est écrit avant « Enregistrer ».
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : fichiers Berry par env (http://127.0.0.1:7800) ». Ce
  n'est pas un `pio run` : utilisable pendant un build (l'écriture, elle, y est refusée).
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/fichiers_berry_web.py` (`--http 7800`,
  `--local`, `--sans-navigateur`) ; lien à jeton dans la console pour un autre appareil, comme les autres outils.
- **Cible PlatformIO** « Fichiers Berry par env (page web) » dans *Project Tasks > <env> > Custom* : démarre la page
  **détachée** (console dans `%LOCALAPPDATA%\outils_tasmota\consoles\fichiers_berry.log`) puis rend la main.
  Comme toute cible, **jamais pendant un build**.
- **Depuis la page build** : le lien « fichiers » de chaque env de *Mes cartes* / *Mes bases* ouvre cette page sur
  cet env (`?env=<nom>`) ; après un enregistrement, le lien « Construire / téléverser le FS » ouvre la page build
  avec l'env coché.

### Les trois états

Un `.be` de `data/fs` est **déjà sur le FS par défaut** (`copy_fs_image` recopie `data/fs` dans le dossier de la
carte) : on ne l'en retire que par `custom_files_exclude`, ou par `custom_berry_solidify` avec
`custom_files_exclude_solidified = ON`.

| État | Fichier de `data/fs` ou du dossier de la carte | Module de l'amont (`tasmota/berry/modules/`) |
|---|---|---|
| **Sur le FS** | aucune ligne (retiré des autres listes) | ligne dans `custom_files_upload` |
| **Exclu** (« Absent » pour l'amont) | ligne dans `custom_files_exclude` | ligne retirée de `custom_files_upload` |
| **Solidifié** | ligne dans `custom_berry_solidify` | non proposé |

- Fichiers proposés, **recensés à chaque chargement** (et par « Revérifier les fichiers ») : les `.be` de `data/fs`,
  ceux du dossier de la carte (`data/<lieu>/<carte>/`, aucun pour une base), les modules de l'amont (`.tapp`,
  `.be` de premier niveau, `.bec`). Dossiers `*sauvegarde*` ignorés.
- **Pendant un build**, `copy_fs_image` recopie `data/fs` dans le dossier de la carte : un `.be` de ce dossier
  identique octet pour octet à `data/fs/<même nom>` est une **copie temporaire**, ni proposée ni signalée comme
  homonyme ; la page la liste en avertissement (aussi après un build interrompu, qui en laisse). Un bandeau rouge
  dit qu'un build est en cours (toute écriture refusée) ou que la détection est impossible.
- `autoexec.be` est figé sur « Sur le FS ». Un fichier présent dans deux listes, ou deux fois dans la même (socle ET liste propre), est signalé comme incohérent ; « Appliquer » sur l'état affiché le nettoie (la ligne en double de l'env part, celle du socle reste) ; une
  ligne du `.ini` dont le fichier a disparu du disque est signalée, jamais retirée en silence. Les entrées non
  Berry (`.js`, `.gz`, `.html` de `custom_files_exclude`) sont montrées en lecture seule (« hors périmètre »).
- Les listes sont résolues comme PlatformIO les lit (`walk_options` : l'env, ses `extends` en commençant par le
  DERNIER cité, puis la section `[env]` ; `opt =;x` vaut `;x`) : le banc le compare à son `ProjectConfig`.
- Sans `custom_files_exclude_solidified = ON`, la page avertit : un fichier solidifié reste **aussi** sur le FS.
- Passer à « Solidifié » ne vérifie rien : avant de builder, `berry/solidifie_et_compile_berry.py <fichier>` (voir
  [SOLIDIFICATION_BERRY.md](SOLIDIFICATION_BERRY.md)).

### Disposition et enregistrement

1. Choisir l'env ; choisir un fichier dans la liste, son état (boutons radio), une raison facultative, puis
   « Appliquer ». Plusieurs « Appliquer » s'accumulent avant d'enregistrer (marqués « en attente »).
2. Les trois colonnes **Sur le FS · Exclu · Solidifié** montrent l'état complet de l'env ; chaque entrée héritée
   porte un badge de son origine (`socle`, `modbus`, `historique` de `[berry_commun]`, ou l'env de base).
3. « Voir le diff » puis « Enregistrer » : sauvegarde horodatée avant d'écrire (voir « Sauvegardes » plus bas),
   fins de ligne et encodage gardés, **refus pendant un build** et si le fichier a changé depuis le diff.

- **Liste partagée** : si le fichier vient d'une liste partagée (`[berry_commun]`, ou option héritée d'un autre env),
  la page nomme les envs touchés ; deux issues : « Modifier la liste partagée (N envs) » ou « Annuler ».
- **Option héritée** : pour ajouter une ligne dans un env qui hérite de l'option, la page écrit
  `option = ${env:<base>.option}` puis la ligne : l'héritage est gardé.
- **Commentaires** : jamais modifiés ni supprimés ; le diff signale ceux de la section qui citent le fichier déplacé.
  La raison saisie est écrite en fin de ligne : `; <raison> (AAAA-MM-JJ)`.

> [!WARNING]
> Réécrire le `.ini` change l'empreinte du projet : le **build suivant repart de zéro** (PlatformIO supprime tout
> `.pio/build`). Rien n'est commité par la page.

### Créer un env à partir d'une carte modèle

« Créer un env à partir de… » : carte modèle, base (celle du modèle par défaut), lieu, nom, puis les champs
d'identité préremplis (« Proposer ») et modifiables : `CODE_IMAGE_STR`, `PROJECT`, `WIFI_IP_ADDRESS` (`0.0.0.0` =
DHCP), `WIFI_RGX_SSID`, `MQTT_CLIENT_ID`, `MQTT_TOPIC`, `MQTT_GRPTOPIC`, `FRIENDLY_NAME`, et le define
(`FIRMWARE_ESP<puce>_<LIEU>_<NOM>`). Après le diff des trois morceaux, la page écrit :

1. la section `[env:<puce>-<lieu>-<nom>]` du cenv, copiée du modèle (`extends` = la base, define remplacé,
   `custom_files_upload` = celui de la base + le nouveau dossier, chemins du dossier du modèle réécrits, **ports COM
   non recopiés**), sous le bandeau `; LOCALISATION:` du lieu, sinon en fin de fichier ;
2. le dossier `data/<lieu>/<puce>-<nom>` (nom calculé comme `transform_name`), copie de celui du modèle ; dans le
   `_persist.json`, seules les valeurs d'identité sont remplacées, dans le texte, le reste octet pour octet ;
3. la section `#elif defined(FIRMWARE_…)` de `tasmota/user_config_override.h`, après celle du modèle, defines
   d'identité remplacés (dont le `Hostname` de `USER_BACKLOG` et le `NAME` du `USER_TEMPLATE`). Les conditions
   internes qui citent encore l'ancien define sont signalées, à revoir à la main.

Refus si l'env, le dossier ou le define existent (un define seulement cité en commentaire ne compte pas), si un
champ d'identité est vide ou contient `"`, `\`, `;` (une commande de plus dans `USER_BACKLOG`), un espace (`PROJECT`,
`MQTT_CLIENT_ID`, `MQTT_TOPIC`, `MQTT_GRPTOPIC`, `WIFI_IP_ADDRESS`) ou un joker MQTT `+`/`#`, ou pendant un build.
Une IP (hors `0.0.0.0`), un topic ou un client MQTT déjà portés par une autre carte ne sont qu'un **avertissement** :
c'est normal pour une carte qui en remplace une autre (P4 après l'ancien maître S3, caves) ; sinon les deux cartes se
déconnecteront l'une l'autre. **Mots de passe masqués** dans le diff. Le dossier de la nouvelle
carte ne reçoit ni les `*sauvegarde*` du modèle, ni ses copies temporaires d'un build (fichiers identiques à
`data/fs`, sous-dossiers `fs`, `json`, `sd`). La nouvelle carte apparaît ensuite d'elle-même dans la page build.

### Renommer un env

« Renommer cet env… » (cartes seulement, pas les bases) : nouveau lieu et/ou nouveau nom, puis « Proposer » :
l'identité (les 8 champs de la création) et le define sont **reproposés d'après le nouveau nom**, modifiables. Après
le diff, « Renommer » (grisé si la saisie change après le diff) écrit, en une seule opération :

1. la section `[env:<puce>-<lieu>-<nom>]` du cenv, copie de l'ancienne (même base, chemins du dossier et define
   remplacés), placée comme à la création ; l'ancienne est retirée ;
2. la section du `.h` avec la nouvelle identité ; l'ancienne est retirée ;
3. le dossier de la carte **déplacé** (pas copié) vers son nouveau nom, `_persist.json` aux nouvelles valeurs
   d'identité (le reste octet pour octet) ;
4. dans `platformio_override.ini`, la ligne de `default_envs` garde son état (active ou commentée) sous le nouveau
   nom, et `data_dir` suit le dossier.

Garder son IP, son topic ou son client MQTT est permis ; une identité portée par une AUTRE carte est signalée,
comme à la création. Un commentaire de section du `.h` qui ne cite pas l'env est signalé (à revoir). Refus si un autre env référence celui-ci (`extends`, `${env:<env>…}`), si le nouvel env, dossier ou
define existe déjà, ou pendant un build. Ce qui cite encore l'ancien nom (commentaires, scripts, bancs) est signalé,
jamais modifié. Renommer puis revenir à l'ancien nom redonne des fichiers identiques.

### Supprimer un env

« Supprimer cet env » : pour un env qui ne sert plus, ou pour défaire une création ratée. Après le diff,
« Supprimer » :

1. retire la section `[env:…]` du cenv ; le bandeau `; LOCALISATION:` juste au-dessus part aussi s'il ne couvre plus
   rien (lieu créé puis vidé : créer puis supprimer redonne le cenv d'origine) ;
2. retire la section du `.h` (commentaire `// -- Options for …` compris ; si c'était le `#if` de tête, la suivante
   devient `#if`). Section partagée par deux envs (`#if defined(A) || defined(B)`) : seul `defined(<env>)` est
   retiré de la condition ;
3. renomme le dossier `data/<lieu>/<carte>` en `<carte>-sauvegarde` (`-sauvegarde-2`, `-3`… si le nom est pris) :
   rien n'est effacé, les builds et la page l'ignorent. À retirer à la main quand on est sûr ;
4. retire l'env de `default_envs` (ligne active ou commentée, dans le seul bloc `default_envs`) ; un `data_dir` qui
   désignait le dossier est signalé, et aussi un `default_envs` sans plus aucun env actif (`pio run` sans `-e`
   construirait alors tous les envs).

Les commentaires `// -- Options for …` de la section du `.h`, et ceux qui les suivent jusqu'au `#if`, partent avec elle.

Refus pour une base dont d'autres envs héritent ou qu'ils référencent (envs nommés), pour un env de l'amont, ou
pendant un build. Les citations de l'env ailleurs sont signalées. Créer puis supprimer un env redonne un cenv, un
`.h` et un `platformio_override.ini` identiques à l'origine.

### Sauvegardes

Chaque écriture (enregistrement, création, renommage, suppression) est **atomique** : si un fichier ne peut pas
être écrit en route, ce qui a déjà été fait est défait (fichiers remis, dossier copié retiré, dossier renommé
remis). Avant d'écrire, chaque fichier modifié est copié dans
`%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\<date-heure>-<nature>\` (chemins du dépôt gardés),
**gardé 30 jours** ; la page affiche ce dossier après l'opération. Plus de `.bak` commun avec la page build.
Une erreur inattendue (fichier verrouillé…) est affichée avec son message (réponse 500), sans rien laisser à moitié.
Si l'annulation elle-même échoue, le message dit ce qui reste à remettre à la main. Chaque fichier est écrit par
remplacement (jamais tronqué), et les écritures passent une par une (double clic, deux onglets). Si la page est
arrêtée en pleine opération (annuaire, Ctrl+C), la sauvegarde garde sa marque `en_cours.json` : au chargement suivant,
la page affiche un bandeau rouge « Opération interrompue » avec les étapes à vérifier ; « J'ai vérifié » retire la
marque, la sauvegarde reste.

### Bancs

Dans `outils_docs/scripts_python/outils_pc/`, avec le Python du penv PlatformIO (code de sortie 0 = vert) :
`test_fichiers_berry_ini.py`, `_etat.py`, `_ecriture.py` (relecture par `ProjectConfig` de PlatformIO),
`_creation.py` (copie du dépôt dans un dossier temporaire), `_suppression.py`, `_renommage.py`, `_sauvegarde.py`,
`_web.py`, et la sonde Chrome
`test_fichiers_berry_page_chrome.py` ; cible Custom : `build/test_cible_fichiers_berry.py`. Aucun banc n'écrit
dans le vrai dépôt ni dans le vrai dossier des sauvegardes.

## Assistant persist (page web)

Une page qui pose des questions et en tire le `_persist.json` d'une **nouvelle carte** (elle sait aussi **modifier ou
supprimer un env existant**, voir plus bas), avec l'`autoexec.be`, la
section du cenv et la section `#elif` de `tasmota/user_config_override.h` qui vont avec. Les questions et leurs règles
viennent d'un **modèle** (`outils_docs/schemas/modele_persist.json`) qui se met à jour à partir des persists du dépôt.
Le moteur d'écriture est celui de « Fichiers Berry par env » (créer un env), sans changement de comportement.
Conception : [spec](../docs/superpowers/specs/2026-10-27-assistant-persist-design.md) ; plan :
`tasks/plans/assistant-persist.md`.

Les listes de cartes du parc (env à modifier, carte de l'onglet autoexec.bat) sont groupées par lieu de la maison
(`outils_pc/lieux.py`).

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Maintenance » : « Assistant persist ». Rien n'est écrit
  avant « Créer l'env » : on peut l'arrêter à tout moment.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : assistant persist (http://127.0.0.1:7900) ».
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/assistant_persist_web.py` (`--http 7900`,
  `--local`, `--sans-navigateur`).
- **Cible PlatformIO** « Assistant persist (page web) » dans *Project Tasks > <env> > Custom* : démarre la page
  détachée (console dans `%LOCALAPPDATA%\outils_tasmota\consoles\assistant_persist.log`) puis rend la main.
  Comme toute cible, **jamais pendant un build**.

Port **7900**. Depuis un autre appareil : lien à jeton affiché dans la console, comme les autres outils
(`acces_web.py`) ; depuis ce PC, aucun jeton.

### Les étapes de la page

1. **Questions** : identité de la carte (puce, lieu, nom, topic, IP), réseau, fonctions à activer.
2. **Entrées et sorties du bloc métier** : un éditeur par groupe (boutons, interrupteurs, relais, capteurs, compteurs,
   thermomètres, analogiques, `pinsTechniques`, `debitmetres`). Les broches proposées sont celles de la puce d'après `data/fs/configGlobal.be`.
   `pinsTechniques` porte les broches du gabarit qui ne sont ni relais ni capteurs (UART de la BL0942 et 2e bobine du
   relais bistable du différentiel) ; `debitmetres` porte les `FlowRateMeter` et leur facteur `k` (carte Serveur Débits de
   PAC) ; vide, un de ces deux groupes n'est pas écrit. Un élément relu garde sa clé (`analogique5`,
   `rxBL0942`) ; un élément ajouté prend le premier numéro libre.
   La page **refuse** une broche en double, une broche déjà prise par ModBus, I2C ou LEDs, ou hors plage.
   Un élément **OFF** n'est pas contrôlé : il n'occupe pas sa broche.
3. **Aperçu** du `_persist.json` en direct, mots de passe masqués (`***`).
4. **Diff** de chaque fichier touché (nouveau dossier `data/<lieu>/<puce>-<nom>`, cenv, `.h`).
5. **Création** en **une transaction** : si un fichier ne peut pas être écrit, tout est défait. Sauvegardes
   horodatées dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`, gardées 30 jours. Refusée pendant un
   build, et si la saisie a changé depuis « Voir le diff » (le bouton se grise, le serveur répond 409).

Après la création, la page affiche un **résumé à copier** et deux liens : la page build (7700, env coché) et
« Fichiers Berry par env » (7800, `?env=<nom>`) pour choisir ce qui est sur le FS, exclu ou solidifié.

### Les mots de passe

**Ils ne sont jamais envoyés à la page.** Le serveur les recopie : mots de passe Wi-Fi des familles « maison » prises
dans les persists du parc, et mot de passe commun mqtt / point d'accès / FTP. L'aperçu, le diff, le résumé et les
erreurs montrent `***` ou rien. Si deux persists donnent deux mots de passe pour le même nom de réseau, ou si le
réseau est inconnu du parc, la création est refusée en nommant le réseau (sans valeur). Le modèle n'en contient
aucun : ses valeurs sont `@secret:<famille>`.

### Le modèle `modele_persist.json`

- **À l'ouverture**, les clés **nouvelles** du parc (présentes dans un persist du dépôt, absentes du modèle) sont
  **fusionnées automatiquement** ; un bandeau orange « à compléter » liste celles qu'il faut documenter (texte de
  question, valeur par défaut).
- **« Mettre à jour le modèle »** : le bouton affiche le diff de la mise à jour proposée, puis la valide.
- **« Relue »** (une par clé du bandeau « à compléter », avec son chemin et sa valeur par défaut, `***` si secret) : retire cette seule clé de `a_completer` après diff et validation ; le modèle n'est écrit que si l'empreinte du diff est encore la bonne (409 sinon).
- Chaque écriture du modèle est précédée d'une **sauvegarde horodatée**, au même endroit que les autres.
- Modèle **cassé à la main** (JSON invalide) : la page s'ouvre avec un bandeau rouge qui donne l'erreur et sa ligne ;
  ni fusion ni réécriture, et la création est refusée.
- Persist du dépôt illisible : ignoré avec un avertissement.

### Modifier ou supprimer un env existant

Conception : spec §10 ; plan `tasks/plans/assistant-persist-modification.md`. Code : `assistant_persist_texte.py`
(édition du texte sans le reformater), `assistant_persist_delta.py` (écart A -> B), `assistant_persist_modification.py`
(application aux fichiers), `assistant_persist_page_js_env.py` (page).

**Charger.** La liste des cartes du parc (`cartes` dans `/parc`) permet de choisir un env : `GET /env` relit son
`_persist.json` (plus la base et le define tirés du cenv) et remplit les questions avec ces réponses. L'autoexec et
les sections du cenv et du `.h` ne sont lus qu'à la préparation de la modification.

**Modifier.** L'assistant ne régénère jamais une carte. Il génère **A** (les réponses relues) et **B** (les réponses de
la page), puis applique au vrai fichier le **seul écart A -> B** ; tout le reste (retouches à la main, ordre,
commentaires) ne bouge pas d'un octet. Écart vide : rien n'est écrit et « Modifier » est grisé. Même cheminement que
la création : « Voir le diff » (`/modification/prepare`), puis « Modifier » (`/modification`) en une transaction.

- **Persist** : l'écart est calculé par chemin JSON et appliqué dans le texte. Un `remplace` garde la forme de la valeur
  (compacte sur une ligne ou indentée) ; un ajout se pose après sa clé soeur ; les objets compacts sont gérés.
  *Limite* : un bloc objet **entier** retiré puis ré-ajouté est réécrit en indentation uniforme (sa mise en forme mixte
  d'origine est perdue ; le JSON reste valide).
- **Autoexec, section du cenv, section du `.h`** : écart ligne à ligne. Si une ligne de A est introuvable telle quelle
  (retouchée à la main), **toute** la modification est refusée (409) ; le refus cite le fichier et les lignes, mots de
  passe masqués. Ancre d'un ajout : la ligne précédente si elle est unique (ajout après elle) ; absente, refus ;
  présente plusieurs fois, la paire précédente + suivante, puis la suivante seule, sinon refus. Une ligne qui deviendrait
  double (par exemple un module déjà ajouté à la main) est refusée.
- **Figés** : lieu, nom, puce et base. Renommer se fait dans la page 7800 « Fichiers Berry par env » ; changer de base
  ou de puce revient à créer une autre carte.
- **Esclave** : le bloc `rangeExtender` n'est pas relu (voulu). Cocher la case sur un esclave qui a déjà ces lignes est
  refusé comme doublon.
- **Métiers 2 à N** : leurs éléments sont conservés mais non éditables.
- Mots de passe, build et empreinte comme à la création : jamais envoyés à la page, `***` dans le diff, les refus et
  les erreurs ; refus pendant un build ; empreinte périmée -> refaire « Voir le diff ».

**Supprimer.** Réservé aux **cartes du parc** listées par l'assistant (une base, ou un env sans `_persist.json` :
page 7800). `/suppression/prepare` affiche le panneau des éléments retirés : section du cenv, section du `.h` et son
define, `default_envs` et `data_dir` de `platformio_override.ini`, dossier renommé en `...-sauvegarde`. Il faut cocher
« J'ai vérifié ces éléments » avant que « Supprimer » (`/suppression`) s'active.

### Onglet « autoexec.bat »

Deuxième onglet de la page : modifier l'`autoexec.bat` d'une carte du parc, ou y ajouter des lignes, sans en connaître
la syntaxe. Le fichier s'exécute **à chaque démarrage** de la carte. Choisir la carte en haut ; rien n'est écrit avant
« Écrire dans le dépôt », rien n'est envoyé avant « Envoyer ».

- **Le texte, à gauche**, se modifie librement. Les mots de passe y sont remplacés par `***` : la page ne les reçoit
  jamais, le serveur les remet à l'écriture. Retirer ou ajouter une ligne portant une commande à `***`, alors qu'il en
  reste une autre de la même commande, est refusé au diff (message explicite) : retaper la valeur ou annuler.
- **« Supprimer la ligne N »**, sous le texte : la ligne du curseur, ou celle de l'avertissement cliqué.
- **Les avertissements**, sous le texte et en points dans la marge (survol = détail, clic sur la liste = la ligne) :

  | Niveau | Avertissement | Ce qu'il faut faire |
  |---|---|---|
  | Rouge | Redémarrage à répétition (`Hostname`…) | Retirer la ligne, régler la valeur autrement (bouton « Enlever ») |
  | Rouge | Secret en clair, même en commentaire | Le dépôt est public : garder la valeur hors du fichier |
  | Orange | Redémarrage si la valeur change | Vérifier (bouton « Enlever ») |
  | Orange | Doublon : le persist repose déjà la commande au démarrage | Retirer la ligne (bouton « Enlever ») ou changer le persist |
  | Orange | Commande inconnue | « Corriger » propose la plus proche |
  | Orange | Commande absente : pas compilée pour cette carte (`USE_…` non défini dans son env) | Retirer la ligne, ou compiler la fonction dans le firmware de la carte |
  | Orange | Commande absente (Berry) : `ReglageXxx` d'un module que l'`autoexec.be` de la carte ne charge pas | Retirer la ligne, ou charger le module dans l'`autoexec.be` |
  | Orange | Ligne de plus de 510 octets : le firmware la tronque | Couper la ligne |

  Les rouges demandent de cocher « J'ai lu les N avertissements rouges » à l'écriture et à l'envoi.

  « Commande absente » ne sort que si c'est **certain** : les macros de l'env sont lues sans compiler (quelques secondes au
  premier passage, puis en mémoire tant que le cenv et `user_config_override.h` ne changent pas), et une garde que la lecture ne
  tranche pas ne donne rien. Une commande définie à plusieurs endroits du firmware (`Subscribe` : règles ou script)
  n'est signalée que si **tous** sont exclus. Si la lecture échoue, une ligne discrète « Vérification par carte
  indisponible » s'affiche et aucune alerte n'est donnée. Limite : les commandes BLE et MI32 ne sont jamais signalées
  (leurs gardes passent par des macros que la lecture ne pose pas) ; les `SetOption` ne sont pas concernées.

  Pour les commandes Berry (`tasmota.add_cmd` dans `data/fs` ou le dossier de la carte), même règle de certitude : l'alerte ne
  sort que si **aucun** des modules qui la déclarent n'est chargé par l'`autoexec.be` (nom entre guillemets ou après `import`,
  module importé par un module chargé, `demarrage.leds()`, `demarrage.historique()`). Un nom cité dans un commentaire ou chargé
  sous une condition `OFF` du persist compte comme chargé : on se trompe du côté du silence. `autoexec.be` absent, vide ou de
  forme non comprise : aucune alerte. Une commande Berry qui porte le nom d'une commande du firmware (`Dimmer`) n'est jamais
  signalée (code `autoexec_berry.py`, banc `test_autoexec_berry.py`).
- **« Ajouter », à droite** : chercher dans la banque (`outils_docs/schemas/banque_autoexec.json`), remplir le
  formulaire, vérifier l'aperçu, insérer sous la ligne du curseur. Une commande qui déclencherait l'alerte « absente »
  pour la carte choisie (non compilée, ou module Berry non chargé) est **en pointillés**, avec la raison en infobulle et sous
  son titre ; elle reste sélectionnable. Sans vérification possible (préprocesseur indisponible), rien n'est marqué. « Nouveau modèle… » et « En faire un modèle »
  ajoutent une commande à la banque (« Tes commandes »).
- **Si la commande est déjà dans le fichier** : la page donne sa ligne et propose « Remplacer par la nouvelle » ou
  « Enlever l'existante » ; « Insérer quand même » reste possible pour une commande qui se répète (`Delay`, `Publish`).
  Dans une `Backlog`, seule la commande visée part ; une `Backlog` vidée disparaît. `SO146` et `SetOption146` sont la
  même commande (seul alias court du firmware) ; les autres alias (`Power` = `Power1`) ne sont pas reconnus à cet endroit. Une ligne en commentaire ne compte pas.
- **« Enregistrer… (diff) »** montre les changements, puis **« Écrire dans le dépôt »** écrit le fichier (refusé pendant un
  build, ou si le fichier a changé sur le disque depuis sa lecture ; copie dans
  `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`). Le fichier n'est pas commité : à faire à la main.
- **« Puis envoyer à la carte (OTA)… »** envoie **le fichier du dépôt**, sans toucher au firmware ni au persist, par l'une
  des deux voies choisies dans le panneau : **Wi-Fi (HTTP)**, par défaut (`/ufsu`), ou **MQTT**, pour une carte sans
  adresse IP joignable (esclave derrière son maître). Changer de voie relance la lecture de la carte. Grisé tant qu'une
  modification n'est pas écrite. La page lit d'abord la carte (`Status 5`) et
  refuse si son nom d'hôte diffère du `serveur.hostname` du persist du dépôt. Elle montre le fichier de la carte s'il
  diffère et demande de cocher son remplacement ; la copie de l'ancien fichier part dans `autoexec_cartes\<env>\` du
  même dossier. « Redémarrer la carte ensuite » est décochée : sinon la carte l'exécute au prochain démarrage. Pour une
  carte derrière le maître (cuve, rideau), le maître passe en `Sleep 0` le temps de l'envoi.

**Voie MQTT** : broker du dépôt (celui de `user_config_override.h`), topic lu dans `serveur.mqtt.topic` du persist du
dépôt, identité par `cmnd/<topic>/Status 5`, fichier transmis par le module `fsMqtt` de la carte (`fsmqtt/<topic>/…`, contrôle
MD5). La carte doit avoir chargé `fsMqtt` : c'est le cas du P4, de la cuve et du rideau (ligne `demarrage.charge(["fsMqtt"])`
de leur autoexec ; le rideau ne l'a qu'après l'envoi de son nouveau FS). Sinon : refus « aucune réponse de fsMqtt.be ». Une
carte qui n'a pas d'autoexec chargeant `fsMqtt` peut le recevoir par l'extension `fsMqtt.tapp` (voir « Fabrique
d'extensions »). Si l'`autoexec.bat` de la carte ne peut pas être relu par MQTT, rien n'est envoyé (fichier absent : envoi
normal).

Autres voies : un envoi série de la page Build écrit aussi ce fichier, mais il réécrit tout le système de fichiers,
persist compris. Un refus « répond X à Status 5, pas Y »
veut dire que la carte n'a pas encore reçu le persist du dépôt : l'envoyer depuis la page Build, puis réessayer.

Si Tasmota évolue, régénérer la liste des commandes : `autoexec_commandes.py --verifier` (écarts), `--generer` (mise à jour de
`outils_docs/schemas/commandes_tasmota.json`). Conception : [spec](../docs/superpowers/specs/2026-11-03-onglet-autoexec-bat-design.md) ;
plans : `tasks/plans/autoexec-bat.md`, `tasks/plans/autoexec-mqtt-tapp.md` (voie MQTT, alerte « absente »). Bancs :
`test_autoexec_analyse.py`, `test_autoexec_banque.py`, `test_autoexec_commandes.py`, `test_autoexec_envoi.py`,
`test_autoexec_fichier.py`, `test_autoexec_gardes.py`, `test_assistant_persist_autoexec.py`, sonde
`test_assistant_persist_autoexec_chrome.py`.

### Limites connues

- L'éditeur ne règle que **activation, nom, broche et type**. `idModBus`, `virtuel`, `channel`, `nbLeds` se
  complètent à la main dans le `_persist.json` créé.
- Les broches de **SD, I2S, Ethernet et LoRa** ne sont pas contrôlées.
- Les éléments ne vont que sur le **bloc métier principal**.
- Les éléments des **métiers 2 à N** sont conservés lors d'une modification, mais non éditables (voir « Modifier ou supprimer un env existant »).
- Une carte dont la section du `.h` (ou l'autoexec, ou la section du cenv) a été retouchée à la main au point qu'une ligne générée ne s'y retrouve plus est **refusée à la modification** (le refus cite le fichier et la ligne) : c'est le cas aujourd'hui de plusieurs cartes anciennes du parc — les reprendre à la main ou les recréer.
- Clés `adressMAC` / `adresseMAC` et `telePeriod` : tranché le 2026-10-28 — `telePeriod` de `serveur.udp` et `serveur.rangeExtender` retirées (jamais lues), MAC écrite dans `adresseMAC` dès le boot par `globalFonctions`, `adressMAC` retirée ;
  voir `outils_docs/ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md`.

### Bancs

Dans `outils_docs/scripts_python/outils_pc/`, avec le Python du penv PlatformIO (code de sortie 0 = vert) :
`test_assistant_persist_modele.py`, `_parc.py`, `_elements.py`, `_generation.py`, `_creation.py`, `_fidelite.py`,
`_texte.py`, `_delta.py`, `_modification.py` (lent : plusieurs minutes, rejeu du parc), `_web.py`, et la sonde Chrome `test_assistant_persist_page_chrome.py` ; cible Custom :
`build/test_cible_assistant_persist.py`. Les bancs travaillent sur un dépôt d'essai temporaire (lecture seule des
vrais persists) : aucun n'écrit dans le vrai dépôt ni dans le vrai dossier des sauvegardes.

## Fabrique d'extensions (page web)

Page http://127.0.0.1:7980 pour fabriquer une extension Tasmota (`.tapp`) et l'envoyer à une carte. Ce qu'est une
extension, quand s'en servir et ses pièges : [EXTENSIONS_TAPP.md](EXTENSIONS_TAPP.md). Lancement : tuile « Fabrique
d'extensions » de l'annuaire (groupe Maintenance), tâche VS Code « Outil : fabrique d'extensions », ou cible Custom
« Fabrique d'extensions (page web) » (`build/cible_tapp.py`, page démarrée détachée ; `pio run` : jamais pendant un build).
Arrêt libre : rien n'est écrit ni envoyé sans un geste dans la page, aucune source n'est supprimée. La liste des
cartes destinataires est groupée par lieu de la maison (`outils_pc/lieux.py`).

Quatre étapes :

1. **Créer depuis un modèle** : un dossier `data/extensions/<nom>/` (31 caractères au plus, lettres sans accent,
   chiffres, `-` et `_`). Modèle A : charger un module déjà dans le firmware (exemple : `fsMqtt`) ; modèle B : un module
   embarqué, qu'on peut arrêter depuis `/ext`. Un dossier existant n'est jamais écrasé.
2. **Manifeste** : nom, version, description, `min_tasmota` ; les autres clés du fichier sont gardées.
3. **Vérifier puis fabriquer** : noms des fichiers, manifeste, compilation Berry (avec la charte des logs en
   avertissements), point par point. « Fabriquer le .tapp » écrit `data/extensions/<nom>.tapp` à côté du dossier (archive
   sans compression, comme l'exige le firmware ; non versionnée). En ligne de commande : `berry/gen_tapp.py <dossier>`.
   **Piège** : l'extension est compilée par la carte avant `/autoexec.be`, quand `LOG_LEVEL_*` et `logFonctions`
   n'existent pas encore. Un `LOG_LEVEL_INFO` nu empêche l'extension de se lancer : écrire `global.LOG_LEVEL_INFO`, et
   `import logFonctions` dans la fonction. La vérification le refuse en le disant.
4. **Envoyer à une carte** : choisir la carte et la voie (Wi-Fi HTTP ou MQTT, comme l'onglet « autoexec.bat »), vers
   `/.extensions/<nom>.tapp`. Nom d'hôte de la carte comparé au persist du dépôt, refus pendant un build, case à cocher
   avant « Envoyer », pas de redémarrage par défaut (l'extension se lance au démarrage suivant, ou par `/ext`). En MQTT,
   la carte n'est lue qu'au clic sur « Lire la carte » : une lecture ouvre un échange avec `fsMqtt`, qui annulerait un
   transfert en cours.
5. **Boutique locale de `/ext`** : tant que la page tourne, elle sert les `.tapp` fabriqués et à jour comme un dépôt
   d'extensions (`/extensions/extensions.jsonl` et `/extensions/tapp/<nom>.tapp`, publics car une carte n'a pas de jeton,
   lecture seule). Une carte les propose dans sa boutique (`/ext`, « Online Store ») si son `OtaUrl` pointe sur ce PC,
   par exemple `OtaUrl http://192.168.0.3:7980/` : la carte en déduit `http://192.168.0.3:7980/extensions/`. Elle revient
   au dépôt officiel si la page ne répond pas ; sinon, seules nos extensions y figurent. **Attention** : `OtaUrl` sert
   aussi à `Upgrade` par URL, qui ne trouverait plus le firmware officiel sur cette carte. À poser carte par carte, à la
   main ; la page doit écouter sur le réseau (pas `--local`), et le pare-feu Windows autoriser Python sur le réseau privé.

Un `.tapp` envoyé n'est pas dans l'image du FS : un formatage ou un flash série l'efface. Envoi MQTT, chargement avant
`/autoexec.be`, Running/Stop et désinstallation **essayés sur la cuve le 2026-11-09** (`EXTENSIONS_TAPP.md` § 9) ; la
boutique locale et l'envoi HTTP ne l'ont pas encore été (plan `tasks/plans/autoexec-mqtt-tapp.md`). Bancs (`outils_pc/`, Python de PlatformIO) : `test_tapp_web.py`,
`test_tapp_envoi.py`, sonde Chrome `test_tapp_page_chrome.py` ; `berry/test_gen_tapp.py`, `berry/banc_tapp_fsmqtt.py`
(l'exemple) ; cible : `build/test_cible_tapp.py`.

## Atelier des graphiques (page web)

Une page qui prépare des **pages de graphiques** pour une carte S3/P4 : on choisit la carte, ses séries (courbes de
l'historique, valeurs du JSON SENSOR, valeurs calculées), un style conseillé, et l'aperçu est tracé par **le vrai moteur
de la carte** avec les vraies valeurs. « Écrire dans le dépôt » pose ensuite la description et ce qu'il faut pour que la
page apparaisse sur la carte. C'est le palier 1 (page dédiée avec bouton d'accueil), complété le 2026-11-05 par la
destination « Graphiques » et le bouton « Téléverser » ; modèle B de
`outils_docs/atelier_graphiques/` (trois colonnes) avec la grille du modèle C.
Conception : [spec](../docs/superpowers/specs/2026-11-03-atelier-graphiques-design.md) et
[spec destinations](../docs/superpowers/specs/2026-11-04-atelier-destinations-televersement-design.md) ; plans :
`tasks/plans/atelier-graphiques.md`, `tasks/plans/atelier-destinations.md`.

La liste des cartes S3/P4 est groupée par lieu de la maison (`outils_pc/lieux.py`) ; la carte du différentiel y est
rangée en Bureau.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Maintenance » : « Atelier des graphiques ». Rien n'est écrit
  avant « Écrire dans le dépôt » : on peut l'arrêter à tout moment.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : atelier des graphiques (http://127.0.0.1:7950) ».
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/atelier_graphiques_web.py` (`--http 7950`,
  `--local`, `--sans-navigateur`).
- **Cible PlatformIO** « Atelier des graphiques (page web) » dans *Project Tasks > <env> > Custom* : démarre la page
  détachée puis rend la main. Comme toute cible, **jamais pendant un build**.

Port **7950**. Depuis un autre appareil : lien à jeton de la console, comme les autres outils (`acces_web.py`).
Le commutateur « Mode sombre » règle la page ; la case « thème sombre » de l'aperçu est indépendante (thème de la carte).

### Utilisation

1. **Carte** : liste des cartes S3/P4 du cenv. Séries et valeurs viennent de la carte **en ligne** ; muette ou hors
   ligne, la page se rabat sur le persist du dépôt et sur des **valeurs simulées**, et le dit.
2. **Séries** : par graphique, de 1 à 12, chacune une chaîne (chemin du SENSOR, ou `calc:<nom>` d'une valeur calculée) ou
   un objet `{chemin, libelle, unite, couleur}`. Un même chemin n'apparaît qu'une fois dans un graphique.
3. **Conseil** : l'intention (texte) croisée avec la nature des séries donne 3 à 5 styles classés avec leur raison.
   Styles : courbe, aire, escalier, barres, barres-empilees, barres-periode, deux-axes, lies, cadran, anneau, chaleur,
   nuage, radar, liquide, demi-cercle.
4. **Réglages** : titre, libellés, unités, couleurs, min / max, zones de couleur, période (direct, jour, mois), cadence (sans effet sous `/graphiques` : la cadence y est celle de la liste « Direct » de la page),
   largeur (demi ou pleine) et hauteur ; l'aperçu montre l'effet de chaque réglage. Jusqu'à 8 pages, 8 graphiques par
   page ; la description compacte tient en 8 Ko.
5. **Diff** de chaque fichier touché, puis **écriture** atomique (copie horodatée).

### Ce qui est écrit

- `data/<lieu>/<carte>/pages_graphiques.json` : la description (validée par `atelier_graphiques_description.py::valide`) ;
- l'`autoexec.be` de la carte : la ligne `demarrage.charge(["pagesGraphiques"])` ;
- le cenv : la liste `pages_graphiques` de `[berry_commun]` est exclue du FS de **tous** les envs sans page ; une carte
  qui reçoit sa première page la voit levée pour elle seule. La case « Solidifier » ajoute les 2 `.be` du moteur au
  `custom_berry_solidify` (firmware à recompiler).

Refusé pendant un build, et si l'empreinte a changé depuis « Voir le diff ». Retirer la dernière page remet le dépôt
dans son état exclu, octet pour octet. En ligne de commande : `atelier_graphiques_ecriture.py --exclusions [--ecrit]`.
Après écriture, lancer `berry/banc_demarrage.py` (jamais `--enregistre`).

### Côté carte

Le moteur est `data/fs/pagesGraphiques.be` (+ `pagesGraphiquesValidation.be`, même verdict que le validateur Python) ;
route `/pages?p=<id>` (page), `?f=valeurs&c=` (valeurs), `?f=sources`, `?f=liquidfill.js.gz`. Gabarits dans `data/sd`
(`html/pages_graphiques.html`, `css/pages_graphiques.css`, `js/pages_graphiques.js` et `pages_graphiques_formule.js`).
Au démarrage seul l'index des pages reste en RAM ; les graphiques ne sont relus qu'à l'ouverture d'une page.
`?f=valeurs` applique les mêmes filtres que le Direct de `/graphiques` (`historiqueFonctions.ajouteFiltre`) : une mesure en
erreur ou un esclave muet donne `null`, pas un faux 0.

### Le menu « Page » : où poser le graphique

Le menu **Page** de la colonne de réglages propose, dans cet ordre :

- les **pages dédiées** déjà décrites pour la carte (`/pages?p=<id>`) ;
- **« Graphiques (/graphiques) »**, la page composable existante de la carte, **seulement si l'historique de la carte
  est actif** (`diverses.historique.activation` = ON dans son persist du dépôt) : sans historique, `/graphiques`
  n'existe pas sur elle ;
- **« Autre… (nouvelle page) »**, qui remplace l'ancien bouton « + Page » : crée une page dédiée (champs « Adresse » et
  « Titre page », mêmes règles).

Avec la destination « Graphiques », les champs sans objet sont **masqués** : « Adresse », « Titre page », « Accès » et la
case « Solidifier » (ainsi que « Retirer la page »). Les autres réglages restent. Le graphique est écrit dans la clé
`graphiques` de `data/<lieu>/<carte>/graphiques.json` avec `"moteur": "pages"` : `/graphiques` le valide et le trace avec
le même moteur que les pages dédiées, donc **tous les styles de l'atelier** y sont disponibles, pas seulement ses
4 types d'origine. Les autres clés du fichier (`affichage`, `groupes`...) et les graphiques déjà là ne sont pas touchés ;
8 graphiques au plus, corps compact de 8 Ko au plus. Une **réécriture** du même graphique le **remplace** (la page retient
son rang et vérifie qu'il n'a pas changé entre-temps) : jamais de doublon.

**Tant que la composition ne contient que des graphiques de l'atelier, `/graphiques` garde ses graphiques automatiques**
(« Mesures » et un par groupe) et y ajoute ceux de l'atelier (décision du 2026-11-07). Une tuile de l'atelier ne retire pas
sa série de « Mesures ». « Enregistrer » depuis le mode édition rend tout explicite : la composition ne contient alors plus
seulement des graphiques de l'atelier, et ce qui a été retiré reste retiré. Retirer tous les graphiques automatiques demande
donc d'en garder au moins un qui ne vient pas de l'atelier.

**Composition de la carte comparée au dépôt.** La composition a pu être modifiée **sur la carte** (mode édition de
`/graphiques`) depuis le dernier envoi. Avant d'écrire, l'atelier relit `/json/graphiques.json` sur la carte en ligne
(lecture seule, `atelier_graphiques_graphiques.py::etat_carte`) et compare les deux JSON normalisés :

- **identique** : une mention discrète, rien à décider ;
- **différente** : bandeau, diff dépôt vers carte, et un choix obligatoire (rien n'est écrit et « Écrire » reste grisé
  tant qu'il n'est pas fait) :
  - **« Partir de la version de la carte »** : ses graphiques sont recopiés dans le dépôt avant d'y ajouter le
    nouveau. Ce que ce choix fait perdre : **les graphiques écrits dans le dépôt et pas encore téléversés**. Indisponible
    (avec le motif) si la composition de la carte n'est pas valide pour le validateur du dépôt ;
  - **« Garder celle du dépôt »** : ce que ce choix fait perdre : **les changements faits sur la carte**, écrasés à
    l'envoi ;
- **non vérifiée** (carte hors ligne, muette, ou fichier absent chez elle) : bandeau « Composition de la carte non
  vérifiée » avec son motif. L'écriture reste possible, mais sans garantie sur ce que la carte porte.

Une composition de la carte modifiée entre « Voir le diff » et l'écriture fait refuser l'écriture (empreinte périmée).

Deux limites propres à la destination « Graphiques » :

- le style **`liquide`** est **refusé** sur une carte dont le FS n'embarque pas `echarts-liquidfill.min.js.gz`
  (exclu de son env) ; la page le dit à l'écriture ;
- le réglage **`largeur: demi`** reste **sans effet** sur `/graphiques` (décision : c'est `/graphiques` qui fait la mise en
  page de ses tuiles). Sur la carte, en **mode édition**, un graphique de l'atelier se **déplace et se retire**, mais ses
  réglages (série, style, titre...) ne s'éditent **que dans l'atelier** ; la tuile le dit.

### Envoyer sur la carte : le bouton « Téléverser »

Après une **écriture réussie** dans le dépôt, le bouton **« Téléverser »** apparaît à côté de « Écrire dans le dépôt »
(il disparaît à la modification suivante, et se perd au rechargement de la page). Un clic ouvre la page Build dans un
nouvel onglet : `http://127.0.0.1:7700/?env=<env>&depuis=atelier&fichiers=<liste>&redemarrer=<0|1>`. La liste, calculée
par `atelier_graphiques_televerse.py::plan`, contient les chemins **tels qu'ils sont dans l'image du FS** :

- toujours le fichier de description écrit (`pages_graphiques.json` ou `graphiques.json`) ;
- `autoexec.be` s'il a été écrit ;
- les fichiers du **moteur** qui viennent d'entrer dans le FS de l'env (exclusion levée dans le cenv), et, si la carte
  est en ligne, ceux dont elle manque (`Br (def() import path return path.exists("/...") end)()`, par `/cm?cmnd=`, lecture seule ; la forme sans fonction rend `nil`). Destination « Graphiques » : sonde du firmware (`graphiquesFonctions.FICHIERS` doit contenir `pages_graphiques.js`) ; firmware d'avant, aucun bouton et le message « compilez et envoyez le firmware et le FS par la page Build » ; moteur absent de la carte, `graphiques.js` et `graphiques_edition.js` sont joints aussi. À l'envoi partiel, un `.json` de la racine de l'image (hors persist) est posé dans `json/`, comme le fait `gestionFileFolder.be` au démarrage. Sous « Graphiques », la page liste les graphiques de la composition : « Modifier » (remplace au même rang, avec témoin) et « Retirer » pour la forme atelier, lecture seule pour la forme actuelle. Carte hors
  ligne ou réponse illisible : seule la première règle s'applique, et la note le dit. Un fichier toujours exclu n'est
  jamais proposé ;
- `redemarrer=1` si `autoexec.be` change ou si l'index des pages dédiées change (id, titre, accès) ; `0` pour un simple
  réglage de graphique, et toujours `0` pour la destination « Graphiques ».

Rien n'est envoyé par l'atelier. Si la page Build ne tourne pas (sondée au clic par `GET /build_actif`), aucun onglet
ne s'ouvre : un message rouge propose de la lancer par l'annuaire. Pour l'arrivée côté Build, voir « Arrivée depuis
l'atelier des graphiques » dans la page Build.

### Destination « Énergie (/energie) » : la page du différentiel

Le menu **Page** propose « Énergie (/energie) » pour la carte `tasmota32-bureau-interrupteur-energie` (toute carte dont le FS
embarque `energie.js`). L'atelier reprend la disposition de la page `/energie` et la modifie sans toucher au comptage.

1. **Choisir** la carte différentiel. Si la description de la carte diffère de celle du dépôt, le choix « carte / dépôt » est
   exigé avant toute modification (jamais d'écrasement implicite).
2. **Éditer** la liste d'éléments : type (`valeur`, `cadran`, `demi-cercle`, `barres`, `courbe`, `aire`, `escalier`), source
   (champ « direct » de ENERGY, total jour/mois/an, ou historique flash minutes/heure/jour/mois/an en kWh ou euros), titre,
   unité, couleur, largeur (demi/pleine), hauteur, min/max des jauges ; ajout (16 au plus), retrait, place dans la liste (en tête, monter, descendre). Échelle de temps d'un graphique « jour » : mois
   relatif (décalage 0 à 23) ou **mois fixe** (`AAAA-MM`) ; si l'archive de ce mois a été purgée, l'atelier le signale avant
   l'écriture. L'aperçu est tracé par le vrai `energie.js`, avec les données de la carte en ligne, sinon des valeurs simulées.
3. **Écrire dans le dépôt** (diff puis écriture atomique, refusée pendant un build ou sur empreinte périmée) : seul
   `data/<lieu>/<carte>/energie_page.json` est écrit, en JSON compact ; la carte le déplace vers `/json/` au démarrage.
4. **Téléverser** : ouvre la page Build avec les 4 fichiers (`energie_page.json`, `energie.js`, `energie.html`,
   `energie.css`), `redemarrer=0`. Rien n'est envoyé par l'atelier.

**Firmware à recompiler une fois.** `energieFonctions.be` est solidifié : les routes `f=description` et `f=mois` n'existent
qu'après un firmware recompilé et envoyé **par la page Build**. Sur une carte à l'ancien firmware (`f=description` rend la page
HTML en 200), « Téléverser » est bloqué avec le message du firmware requis.

**Ne jamais envoyer ce firmware par le port série.** Le différentiel a `custom_files_upload` : un upload série réécrit TOUT
le FS, donc `/energie/etat.json`, `mois-*.json` et `courbe.bin` (jusqu'à 24 mois d'archives) seraient perdus. Procédure :
firmware par OTA (ligne OTA de la page Build ; l'OTA du firmware n'écrit que la partition applicative, `build_ota_firmware.py`,
le FS est une autre partition), puis les 4 fichiers par « Téléverser » ou par l'onglet Fichiers ; jamais d'upload série sauf
après sauvegarde de `/energie/`. Si la description a été écrite quand la carte avait l'ancien firmware, « Écrire » n'a plus
rien à écrire et le bouton « Téléverser » n'apparaît pas : envoyer les 4 fichiers (`energie_page.json`, `sd/js/energie.js`,
`sd/html/energie.html`, `sd/css/energie.css`) par l'onglet Fichiers de la page Build.

Limites (validées par `atelier_energie_description.py::valide` et `Energie.valide`, mêmes cas dans
`outils_pc/cas_energie.json`) : 16 éléments, 4 096 octets de description, titres de 40 caractères, couleur `#rrggbb`.
Conception : [spec](../docs/superpowers/specs/2026-11-08-atelier-energie-differentiel-design.md) ; plan
`tasks/plans/energie-atelier.md`.

### Première page : la cuve

Env `tasmota32s3-garage-capteurs-cuve-modbus` : page `/pages?p=tableau`, bouton d'accueil « Tableau », courbe
« Hauteur d'eau » (cm, 24 h).

### Essayer sans sonde : `ReglageCuve simulation`

`ReglageCuve simulation <ON|OFF|minutes>` (`cuveFonctions.be::reglageCuve`, relevé fabriqué par
`cuveFonctions.be::releveSimule`) fait onduler la hauteur d'eau entre 20 et 90 % de la cuve, une ondulation par période
donnée en minutes. **RAM seulement** : un redémarrage l'arrête. La valeur est enregistrée dans l'historique et dans
Influx comme une vraie mesure. Fonctionne **sans ADS1115** sur le bus (le relevé suppose ±6,144 V et ajoute la lecture
de la minute).

### Bancs

Dans `outils_docs/scripts_python/outils_pc/` (Python de PlatformIO) : `test_atelier_graphiques_description.py`,
`_series.py`, `_conseil.py`, `_ecriture.py`, `_graphiques.py` (destination « Graphiques », composition de la carte),
`_televerse.py` (liste du bouton « Téléverser »), `_web.py`, puis la sonde Chrome `test_atelier_graphiques_page_chrome.py` ;
`build/test_cible_atelier_graphiques.py`. Destination Énergie : `test_atelier_energie_description.py`,
`test_atelier_graphiques_energie.py`, sonde Chrome `test_atelier_energie_page_chrome.py` (mutants `absent`, `archive`,
`mobile`, `vol`). Côté carte : `node outils_docs/scripts_python/outils_pc/test_pages_graphiques.mjs`,
`test_pages_graphiques_chrome.py` et `berry/banc_pages_graphiques.py` (cas partagés avec le validateur Python :
`berry/bouchons_berry/pages_graphiques/cas_description.json`). Commandes exactes : skill `bancs`.

## Atelier des écrans (page web)

Une page qui dessine l'écran tactile d'une carte (HASPmota ou LVGL pur) d'après **une description neutre** : on place
les objets sur un canevas à la taille de l'écran, et la page génère les deux interfaces, `pages.jsonl` (HASPmota) et
`ecranLvgl.be` (LVGL pur). La carte n'en charge qu'une, celle que choisit `custom_interface_ecran` dans son cenv.
Premier palier : sept objets, libellé (`label`), bouton (`btn`), barre (`bar`), cadre (`obj`), courbe (`chart`), arc
(`arc`) et curseur (`slider`). Première carte : l'écran des débits (`tasmota32s3-bureau-ecran-debits-pac`, Waveshare
ESP32-S3-Touch-LCD-7B).
Conception : [spec](../docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md) ; plan `tasks/plans/atelier-ecrans.md` ;
maquettes `outils_docs/atelier_ecrans/` ; savoir-faire HASPmota / LVGL : skill `lvgl-haspmota`.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Maintenance » : « Atelier des écrans ». Rien n'est écrit
  avant « Écrire dans le dépôt », l'arrêt est libre.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : atelier des écrans (http://127.0.0.1:7960) ».
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/atelier_ecrans_web.py` (`--http 7960`, `--local`,
  `--sans-navigateur`).
- **Cible PlatformIO** « Atelier des écrans (page web) » dans *Project Tasks > <env> > Custom* : démarre la page détachée
  puis rend la main. Comme toute cible, **jamais pendant un build**.

Port **7960**. Depuis un autre appareil : lien à jeton de la console (`acces_web.py`). Bascule Sombre / Clair mémorisée
dans le navigateur.

### Utilisation

1. **Carte** : liste des cartes à écran, groupée par lieu. L'en-tête montre l'écran déclaré (présélectionné), l'état en
   ligne de la carte et l'interface envoyée.
2. **Canevas** : glisser un objet depuis la palette, le déplacer (grille aimantée à 8 px), le redimensionner ; zoom − / + /
   100 % ; annuler / rétablir (`Ctrl+Z`, `Ctrl+Y`). L'onglet « Tableau des objets » donne une ligne par objet, cases
   modifiables. Seules les polices du catalogue sont proposées ; une taille absente est refusée avec les tailles possibles.
3. **Aperçu** : dessiné par le navigateur avec les vraies polices `.ttf`, valeurs liées simulées ou lues sur la carte en
   ligne (`Status 10`). « Capture de la carte » affiche l'écran réel (`lv.screenshot()` par la commande `Br`) ; refusée si
   la carte est hors ligne. Pas encore essayée sur la carte.
4. **Fichiers générés** : onglets `pages.jsonl`, `ecranLvgl.be`, `ecran.json`, avec leurs différences au dépôt.
5. **Écrire dans le dépôt** : confirmation avec la liste des fichiers, écriture atomique (copie horodatée). Refusée pendant
   un build, et si un fichier a changé depuis le chargement ou le diff. Le message donne le lien « Envoyer par la page
   Build ↗ » (`?env=` et fichier de l'interface coché).

### Changer d'écran

Choisir dans la liste un écran autre que celui de la carte ouvre une **proposition** : la description est mise à
l'échelle (positions et tailles au rapport des résolutions, police ramenée à la taille compilée la plus proche), les
boutons trop petits pour le doigt et les textes qui débordent sont signalés. Le diff montre aussi le `display.ini` de la
carte, repris d'un env qui porte déjà cet écran ; broches de l'écran en conflit avec le persist = refus motivé. Revenir à
l'écran de la carte annule la proposition. Après écriture : firmware à recompiler et téléverser par la page Build.

La liste des écrans (écrans couleur seulement) a trois groupes, par ordre de priorité : **écrans des cartes** (le
`display.ini` d'un env, sauf s'il est exclu de son FS), **bibliothèque personnelle** (`outils_docs/atelier_ecrans/display/*.ini`)
et **fournis par Tasmota** (`tasmota/displaydesc/*.ini`, lus sans jamais être modifiés). Un même écran trouvé plus loin
prend la clé `<pilote>_<l>x<h>@<fichier>`. Un écran de la bibliothèque ou de Tasmota part sur la carte tel quel, avec un
avertissement : il n'a jamais tourné sur une carte du dépôt. Une carte sans écran peut aussi en recevoir un (description
vierge). Le catalogue se régénère par `python outils_docs/scripts_python/outils_pc/atelier_ecrans_catalogue.py --generer`.

### Remarques et Claude

L'outil « Remarque » épingle un texte sur un objet, une zone tracée ou une page (`remarques.json`). « Traiter les
remarques (Claude) » lance `claude -p` **en lecture seule** (outils de lecture seulement, hooks coupés, jamais
`bypassPermissions`), depuis ce PC seulement : Claude rend des propositions, la page les valide puis les range dans
`remarques.json`. Un fichier du dépôt changé pendant le traitement est signalé, sans rejet (d'autres conversations
travaillent en même temps). « Appliquer » rejoue une proposition sur la description en mémoire ; l'écriture reste celle
du bouton « Écrire dans le dépôt », et c'est elle qui fait passer la remarque à « appliquée » (annulée sur le canevas
avant l'écriture, elle reste « proposée »). Un traitement à la fois, 10 min au plus, journal dans
`%LOCALAPPDATA%\outils_tasmota\atelier_ecrans\`.

### Importer une police

Panneau « Importer une police (.ttf) » sous la palette, avec des liens vers Google Fonts et Font Squirrel. Le fichier
choisi est analysé : famille, licence lue dans la police (table `name`), caractères français manquants. Import refusé si
le Latin-1 est incomplet, tant que la case « J'ai vérifié la licence » n'est pas cochée, pendant un build, ou si une
police du même nom existe déjà dans le dépôt. L'import écrit la police dans le dossier de la carte choisie
(`data/<lieu>/<carte>/<nom>.ttf`, rangée au démarrage sous `/sd/polices/` par `ecranFonctions.rangePolices`), son texte de
licence dans `outils_docs/atelier_ecrans/polices/` (hors du dossier de la carte, qui part en flash) et régénère le
catalogue. Polices `.bin` de LVGL : pas encore importables.

### Images

Une image `.png`, `.jpg` ou `.bmp` posée à la racine du FS est rangée au démarrage dans un dossier par format :
`/sd/images/PNG/`, `/sd/images/JPG/`, `/sd/images/BMP/` (`gestionFileFolder.be::listeEtRepartitLesFichiers`, casse de
l'extension indifférente). Un écran la cite en `A:sd/images/PNG/<nom>`. Le firmware ne décode que le PNG (LodePNG) :
`.jpg` et `.bmp` sont rangés mais pas affichables par un écran. Le module est solidifié : la règle n'agit qu'après
recompilation du firmware de la carte.

### Objets du palier 2

La palette propose aussi **image** (un PNG du dossier de la carte, cité en `A:sd/images/PNG/<nom>`), **liste
déroulante** et **roue** (une option par ligne), **interrupteur** et **QR code** (toujours carré, sa taille est sa
largeur). L'aperçu dessine le PNG réel et le QR code du texte saisi. L'action d'une liste, d'une roue ou d'un
interrupteur part au changement de valeur et reçoit la valeur choisie : dernier argument d'une fonction Berry, `%val%`
dans une commande, 1 ou 0 pour un interrupteur. Ceci vaut pour l'interface LVGL pur : dans un `pages.jsonl`, une
fonction ou une commande n'a pas de clé `action`, c'est le Berry de la carte qui réagit à l'événement HASPmota.
Une roue ne prend pas de texte.

### Barre de navigation construite

Sur la page 0, le panneau « Barre de navigation construite » remplace les boutons de page posés à la main : position,
hauteur, écart, couleurs des boutons et de la page courante. Un bouton par page, dans l'ordre des pages, avec le titre
de la page ; sa largeur suit la longueur du titre. Une page sort de la barre par sa case « Dans la barre de navigation »
(page de confirmation). Les boutons sont générés dans les deux interfaces (ids 201 à 254, réservés : un objet de la
page 0 ne peut pas les prendre) ; ils sont dessinés en pointillés sur l'écran et ne se sélectionnent pas. Une barre plus
large ou plus haute que l'écran est refusée avec sa taille. Au changement d'écran, la barre est mise à l'échelle.

### Page « Système » construite

Une page de la description peut porter `"modele": "systeme"` (une seule, numéro 1 ou plus, aucun objet saisi à la main
dessus) : l'atelier la dessine lui-même d'après la table `CHAMPS` de `data/fs/ecranSysteme.be` (mémoire, flash, charge,
redémarrages, réseau, ModBus, écran, firmware, cinq dernières erreurs) et ajoute les boutons « Lancer le GC » et
« Redémarrer ». La mise en page occupe la zone libre entre l'en-tête de la page 0 et la barre de navigation, en colonnes
de groupes. Il suffit d'ajouter `{"n": 4, "titre": "Système", "modele": "systeme"}` aux pages de la description d'une
carte à écran, puis « Écrire » ; le module Berry ne pose que les valeurs sur les ids de la table. Un champ ajouté à
`CHAMPS` hors des groupes connus, un écran trop petit pour la page (changement d'écran refusé avec le motif) ou un objet
posé à la main sur la page sont refusés par le validateur. Pas d'icônes pour l'instant (A15 et A18 du plan).

### Page « QR code » d'une carte à écran

Même contenu que la page web `/qrcode` de la carte : le QR code du texte réglé par l'outil des étiquettes (« Page sur la
carte » activée, port 7970), l'IP réelle de la carte, l'IP inscrite sur l'étiquette, le nom d'hôte, et une pastille qui
dit si les deux IP concordent (verte si oui, orange si elles diffèrent, grise si l'une manque). Sur l'écran des débits
c'est la page 5 de `ecran.json` : un objet `qrcode` lié à `qr.texte` (attribut `qr_text`), quatre libellés liés à `qr.ip`,
`qr.ipInscrite`, `qr.hostname`, `qr.accord`, la pastille liée à `qr.etat`. Les valeurs viennent de
`ecranDebitsFonctions.qr`, sous-table `qr` du modèle : `/json/qrcode.json` (8 Ko au plus) et `Status 5` sont relus au
plus une fois par 10 minutes, toutes les minutes tant que l'IP reste inconnue, jamais à chaque seconde. Sans réglage de
l'outil des étiquettes, la page affiche « Aucun réglage ». Un fichier trop gros ou illisible est journalisé en erreur
(cible `ecranDebits`). La barre de navigation gagne son sixième bouton toute seule (A17). La cave n'a pas encore sa page :
son écran appartient à une autre session. Pas essayée sur la carte (A20) ; le firmware est à recompiler par la page Build.

### Panneau « Icônes »

Onglet « Icônes » du panneau de droite : la grille des 120 glyphes Material Design embarqués dans le firmware, avec
recherche par nom. Un clic pose le glyphe en `montserrat-28` dans l'objet choisi (libellé ou bouton), sinon dans un
nouveau libellé. L'aperçu dessine ces glyphes par la police locale `materialdesignicons-webfont.ttf` (aucun CDN) ; les
symboles Font Awesome du firmware restent des carrés vides. Sous la grille : le parcours pour une icône absente du
firmware (PNG blanc sur fond transparent, couleur par `image_recolor`) et les sites de l'annuaire avec leur licence.
Sous la grille, « Importer un PNG » : on choisit un fichier .png (512 x 512 px et 300 Ko au plus, avertissement au-delà de
160 px ou sans transparence), la page affiche ses dimensions, on indique l'origine (site ou URL) et on confirme la
licence ; le PNG est écrit dans le dossier de la carte choisie (il part sur le FS, `gestionFileFolder.be` le range sous
`/sd/images/PNG/` au démarrage et l'objet `img` le propose) et la note de licence dans `outils_docs/atelier_ecrans/images/<env>/`.
Refusé pendant un build, sans origine, sans licence confirmée, ou si le nom existe déjà dans le dossier de la carte.
Le catalogue `outils_docs/schemas/icones_firmware.json` vient de `lib/libesp32_lvgl/LVGL_assets/gen.sh` : après une
synchro du fork, `python outils_docs/scripts_python/outils_pc/genere_icones_firmware.py --verifier` (Python système,
fontTools) dit s'il est à refaire, sans `--verifier` il le réécrit.

### Importer un pages.jsonl écrit à la main

Une carte dont le dossier a un `pages.jsonl` montre, sous « + page », le bouton **Importer le pages.jsonl de la carte**.
Le fichier est lu comme HASPmota le lit : une ligne sans clé `page` appartient à la page courante, les lignes vides sont
ignorées. Une ligne d'un objet du palier 1, avec `x`, `y`, `w`, `h` entiers, des attributs connus du catalogue et une
`action` `p<n>` vers une page du fichier devient un objet **éditable**. Le premier commentaire d'une page devient son
titre, son `{"id":0,...}` placé avant tout objet devient ses réglages. Tout le reste reste **brut** : classe hors
catalogue, attribut inconnu, `val_rule`, `text_rule`, `berry_run`, `parentid`, autre `action`, objet hors de l'écran,
ligne non JSON (signalée). Une ligne brute est réécrite à l'identique dans le `pages.jsonl`, hachurée sur l'écran si elle
porte une position, grisée dans la liste ; elle n'est ni éditable ni présente dans `ecranLvgl.be` (signalée en tête de
ce fichier). Aucune liaison n'est importée : un écran écrit à la main est rempli par son Berry.

L'import remplace la description de la page (« Annuler » la rend) et n'écrit rien : « Écrire dans le dépôt » montre ensuite
le diff de `ecran.json`, `pages.jsonl` et `ecranLvgl.be`. Garantie vérifiée par `test_atelier_ecrans_import.py` sur les
six `pages.jsonl` du dépôt : le `pages.jsonl` régénéré porte les mêmes objets que la source, dans le même ordre.

### Onglet « display.ini »

Bascule « Interface | display.ini » en haut de la page. À gauche, les `display.ini` en trois groupes : **cartes**
(lecture seule), **ma bibliothèque** (`outils_docs/atelier_ecrans/display/<nom>.ini`, suivie par git, hors flash) et
**Tasmota** (`tasmota/displaydesc/`, lecture seule : la synchro du fork les remplace). Au centre, le texte du fichier et
son analyse ligne par ligne, lue comme le pilote la lit (`uDisplay.cpp::uDisplay::uDisplay`) : section, arguments nommés
(explication, valeurs, défaut au survol), erreurs et avertissements. L'analyse suit la frappe. À droite, le panneau
**Paramètres** liste les lignes `:X` valables pour le bus de `:H`, avec leurs arguments et leurs pièges ; « Ajouter »
insère la ligne à sa place (ordre de lecture du pilote) avec ses valeurs par défaut, à régler ensuite.

Contrôles (référence `outils_docs/schemas/display_ini_parametres.json`) : `:H` en première ligne, bus connu, nombre de
broches par bus, espace dans une ligne de valeurs (le pilote coupe la ligne à chaque espace), ligne de 256 caractères ou
plus, `#` final, `:F` avant `:A`, `:I` avant `:f` avant `:p`, `:B` sans drapeaux (255 : tous les bits), base
hexadécimale ou décimale, `*` dans une broche RGB, QSPI ou DSI, mot `I2C`/`SPI`/`PAR` dans un commentaire. Les
tolérances du pilote ne sont que des avertissements (commentaire en fin de ligne, `0;`, fréquence RGB absente). Le banc
`test_atelier_ecrans_display.py` vérifie que la référence couvre toutes les sections lues par le code : après une synchro
du fork qui ajoute un paramètre, il devient rouge.

« Enregistrer dans ma bibliothèque » montre le diff puis écrit (refus pendant un build, ou si le fichier a changé depuis
le diff). Pour partir d'un fichier Tasmota ou d'une carte : l'ouvrir, choisir un nom, enregistrer. Un fichier de la
bibliothèque a ses **notes de terrain** (`<nom>.notes.md`) : observations datées, avec la carte choisie en haut.
« Appliquer à la carte » passe par le changement d'écran (diff, broches du persist, lien vers la page Build).

### Ce qui est écrit

| Fichier | Où |
|---|---|
| `ecran.json` (description), `remarques.json` | `outils_docs/atelier_ecrans/cartes/<env>/` (hors flash) |
| `<nom>.ini`, `<nom>.notes.md` | `outils_docs/atelier_ecrans/display/` (onglet « display.ini ») |
| `pages.jsonl`, `ecranLvgl.be` | dossier de la carte `data/<lieu>/<carte>/` |
| `display.ini` | dossier de la carte, au changement d'écran seulement |
| police `.ttf` + licence + `outils_docs/schemas/catalogue_ecran.json` | à l'import d'une police |

Les fichiers de l'interface non choisie sont exclus du FS par `build/interface_ecran.py::applique`.

### Bancs

`outils_pc/test_atelier_ecrans_catalogue.py`, `_description.py`, `_haspmota.py`, `_lvgl.py`, `_ecriture.py`, `_ecran.py`,
`_remarques.py`, `_polices.py`, `_import.py`, `_display.py`, `_display_fichiers.py`, `_web.py`, puis la sonde Chrome `test_atelier_ecrans_page_chrome.py` (copie du dépôt,
carte et `claude` simulés) ; `build/test_cible_atelier_ecrans.py` ; rangement des images : `berry/banc_repartition_fichiers.py`.
Commandes exactes : skill `bancs`.

## Étiquettes QR code (page web)

Page http://127.0.0.1:7970 pour composer, carte par carte, un QR code qui affiche l'identité de la carte au téléphone,
l'imprimer en étiquette ou en planche A4, et le montrer sur une page de la carte. Par défaut, le QR code contient du
texte et aucun lien : le téléphone l'affiche sans réseau, ce qui sert quand une carte ne répond plus (mode lien : voir
« Fiche en ligne » plus bas). Lancement : tuile « Étiquettes QR
code » de l'annuaire (groupe Maintenance), tâche VS Code « Outil : étiquettes QR code », ou cible Custom « Étiquettes QR
code (page web) » (`build/cible_etiquettes_qr.py`, page démarrée détachée ; `pio run` : jamais pendant un build). Arrêt
libre : rien n'est écrit sans « Écrire dans le dépôt », après le diff. Spec :
`docs/superpowers/specs/2026-11-12-etiquettes-qrcode-design.md` ; plan : `tasks/plans/etiquettes-qrcode.md`.

**Contenu.** Une ligne par information, dans l'ordre voulu, chacune avec son libellé :
- un champ standard du dépôt : `hostname`, `ip`, `topic`, `env`, `puce`, `lieu`, `range_extender` (point d'accès de la
  carte maître) ;
- une clé choisie dans le persist de la carte : les clés de mot de passe ne sont jamais proposées, ni une valeur qui
  contient celle d'une clé secrète du même persist (une URL avec jeton, par exemple) ;
- un texte libre (120 caractères au plus).

Une ligne standard ou persist accepte un texte avant et après sa valeur (20 caractères chacun). Exemple : la ligne
`hostname` avec `http://` avant et `.local` après donne l'adresse mDNS de la carte. Elle ne s'ouvre que si le firmware a
`USE_DISCOVERY` et `WEBSERVER_ADVERTISE`, si la carte a `SetOption55 1` (persist `"mDNS": "ON"`), et depuis le même
réseau : un esclave derrière le NAPT du maître n'est pas joignable ainsi.

**Style et gabarit.** Points, coins, couleurs, image au centre (PNG, JPEG ou SVG de 8 Ko au plus, rangée dans
`outils_docs/etiquettes_qr/images/`). Le gabarit commun (`outils_docs/etiquettes_qr/gabarit.json`) vaut pour toutes les
cartes ; une carte qui s'en écarte garde son réglage dans `outils_docs/etiquettes_qr/cartes/<env>.json` (pastille
« réglage propre »). Pour fixer des valeurs par défaut, régler une carte puis « Faire du réglage de cette carte le gabarit commun… » (onglet Gabarit commun) : lignes, style, taille, contenu texte ou lien et « petit nom sous le code » sont alors chargés à l'ouverture et repris par les autres programmes (build, atelier des écrans). Ces fichiers restent hors du FS des cartes.

**Verdict de lisibilité.** Il dépend du nombre d'octets du texte (UTF-8, accents compris), de la taille imprimée et de
l'image (une image au centre impose la correction H, qui grossit le code). Seuils calés le 2026-11-12 sur un essai réel :
un carré élémentaire de 0,45 mm au moins est « lisible », de 0,40 à 0,45 mm « limite », en dessous « illisible ». Un texte
court se lit encore à 15 mm, un texte long demande 20 mm.

**Impression.** « Imprimer » ouvre la fenêtre du navigateur avec le QR code seul : imprimer à 100 %, sans
ajustement à la page, puis vérifier sur la règle imprimée qu'elle mesure bien 50 mm. La planche A4 rassemble les cartes
cochées dans la liste, à une taille de 10 à 100 mm, avec un petit nom sous chaque code en option. Une carte sans ligne
lisible, ou au texte trop long, en est écartée avec sa raison ; une carte « limite » ou trop dense à cette taille est
signalée. « Planche d'essai » imprime la carte affichée à 15, 20, 25 et
30 mm, avec un texte court et un texte long, pour caler la taille sur votre imprimante et votre téléphone (non notée).
Exports PNG et SVG. Chaque impression est notée (empreinte du texte seulement, dans
`outils_docs/etiquettes_qr/impressions.json`) ; « Annuler la note » la retire.

**Page `/qrcode` de la carte** (ESP32 seulement). Case « page sur la carte » : l'écriture ajoute la liste `etiquette_qr`
au FS de l'env et solidifie `qrcodePage.be` (cenv), ajoute `demarrage.charge(["qrcodePage"])` à l'autoexec, et écrit
`data/<lieu>/<carte>/qrcode.json` (texte déjà résolu, style, image). La carte le range dans `/json/` au démarrage. Le
bouton « QR code » apparaît dans le menu Outils de la carte ; la page dessine le même QR code que l'outil (même
bibliothèque, `data/sd/js/qrcode_options.js`), avec le texte dessous, un retour à la ligne à chaque séparateur. Elle
avertit si l'IP inscrite diffère de celle de la carte (comparaison seulement pour une IP sans port, pas pour un esclave
en `IP:port`). Il faut recompiler le firmware une fois (module solidifié), puis envoyer le FS par la page Build.

**Suivi.** Dans la liste des cartes, des badges signalent :
- « à réimprimer » : le texte a changé depuis la dernière impression notée ;
- « à régénérer » : le `qrcode.json` du dépôt ne correspond plus au réglage, au persist et au `.h` du moment.

À l'ouverture d'une carte qui a la page, la page interroge la carte (2 s au plus) : « carte à jour », « carte à mettre à
jour » ou « carte injoignable ». Dans le cas « à mettre à jour », le lien « Téléverser » ouvre la page Build sur cette
carte, `qrcode.json` coché et le redémarrage demandé (le fichier n'est rangé dans `/json/` qu'au démarrage).
Ailleurs :
- chaque `pio run` d'une carte qui a un réglage recalcule son `qrcode.json` avant l'image du FS et le réécrit s'il a
  changé (ligne « QR code de … : régénéré » dans la sortie de pio ; `build/qrcode_build.py`) ;
- après le renommage d'un env (page Fichiers Berry), le réglage suit le nouveau nom ;
- après un renommage, ou une modification par l'assistant persist qui change le texte, un lien « Étiquette QR à
  refaire » ouvre cette page.

**Fiche en ligne (mode lien).** Le menu « le QR code contient » propose, carte par carte, le texte (par défaut, lu
sans réseau) ou un lien vers une fiche HTML PUBLIQUE, `https://<propriétaire>.github.io/<dépôt>/<env>.html` (adresse
tirée de `remote.origin.url`, sans le jeton qu'elle porterait). Le lien se lit partout (4G, carte éteinte, ESP8266) et
la fiche se met à jour sans réimprimer l'étiquette. Les lignes du réglage deviennent le contenu de la fiche ; le titre
est le nom de l'env.

Avant de paraître, chaque ligne entière (libellé, texte avant et après, valeur, ligne libre) passe deux filtres :
- celui des secrets du persist : aucune valeur d'une clé de mot de passe ou de jeton, même recopiée dans un texte libre ;
- celui des valeurs publiques (`etiquettes_qr_filtre_public.py`) : pas d'identifiants dans une URL, de paramètre
  `token=` ou `key=`, d'IPv4 publique, d'IPv6 globale, de nom de domaine joignable (`.local`, `.lan`, `.home.arpa` et
  noms sans point acceptés), de chaîne à allure de clé, ni de mot qui annonce un secret (mot de passe, mdp, WPA…).

L'aperçu signale chaque ligne refusée par son numéro, sans la recopier ; une seule ligne refusée bloque toute la
publication. Faux positifs connus : un numéro de version à quatre nombres (15.1.0.1), un nom de fichier (autoexec.be).

« Publier les fiches… » montre le diff des fiches, puis pousse la branche orpheline `etiquettes` du dépôt, sans
forcer. Seuls les réglages ÉCRITS comptent. Toutes les cartes en mode lien sont publiées ; une carte repassée en texte voit
sa fiche retirée. L'arbre de travail, l'index et `development` ne sont jamais touchés (plomberie git). Refus pendant un
build, si la branche a bougé ailleurs depuis le diff, ou sans réponse de GitHub en 120 s. Une fiche dont seul le jour
change n'est pas renvoyée. Mise en service, une fois : bouton « Activer GitHub Pages… » de la page (affiché tant que
Pages est inactif ; il passe par `gh`, connecté au compte), ou sur GitHub, Settings > Pages, source « Deploy from a
branch », branche `etiquettes`, dossier `/ (root)`. Jusqu'à la première publication, le QR code d'une carte en mode
lien mène à une page introuvable.

Trois aides à ne pas oublier de republier :
- après « Écrire » d'une carte en mode lien, la page enchaîne sur le diff des fiches : un clic « Publier » suffit ;
- le badge « fiche à republier » de la liste compare chaque fiche à la dernière version connue de la branche, sans
  réseau ;
- chaque `pio run` d'une carte en mode lien dont la fiche a changé écrit « Fiche QR de … : à republier » dans sa sortie
  (`build/qrcode_build.py::fiche`, rien n'est envoyé).

Enfin, la case « Publier les fiches QR à la fin (public) » de la page Build publie toutes les fiches après une série
réussie, sans diff (confirmation au lancement) ; le résultat, ou la raison d'un refus, s'affiche dans le récapitulatif
de la série, qui reste réussie même si la publication échoue.

### Bancs

`outils_pc/test_etiquettes_qr_modele.py`, `_verdict.py`, `_ecriture.py`, `_suivi.py`, `_web.py`, `_filtre_public.py`,
`_publication.py` (dépôt temporaire dont l'origin est un dépôt nu local : rien ne part sur le réseau), puis les sondes Chrome
`test_etiquettes_qr_page_chrome.py` (page de l'outil) et `test_qrcode_carte_chrome.py` (page de la carte, servie par un
serveur local qui imite la carte) ; `berry/banc_qrcode_page.py` (module de la carte) ; `build/test_qrcode_build.py`
(régénération au build) et `build/test_cible_etiquettes_qr.py`. Commandes exactes : skill `bancs`.

## Synchro du fork (page web)

La page lance les scripts de synchro (`maintenance/synchronise_fork_tasmota.py`, merge, et sa variante rebase) tels
qu'au terminal ; leurs questions deviennent des boutons. Depuis le 2026-10-27, elle propose en plus un **assistant pas
à pas**. Conception : [spec](../docs/superpowers/specs/2026-10-27-assistant-synchro-fork-design.md) ; plan :
`tasks/plans/assistant-synchro-fork.md`.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Maintenance ».
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : synchro du fork ».
- **Cible PlatformIO** « Synchro du fork (page web) » dans *Custom* (jamais pendant un build).

Port **7500**, lien à jeton depuis un autre appareil, comme les autres outils (`acces_web.py`).

### L'assistant

Il s'affiche **après un « Diagnostic seul » réussi** (ou dès le chargement si un merge lancé par lui est en cours),
sous la sortie du diagnostic. Il travaille sur le **dépôt local** : `git fetch` de l'amont et d'origin, puis une liste
d'étapes verticale, une seule dépliée à la fois. Après chaque action, tout est recalculé à partir du dépôt.

1. **Pas d'opération git en cours** : un merge ou un rebase qui n'est pas le sien bloque (merge : « Abandonner » proposé ;
   rebase : à finir au terminal).
2. **Branche `development`** : bouton « Basculer » si l'arbre est propre.
3. **Arbre propre** : fichiers modifiés classés — **rouge** « touché aussi par l'amont », « sans recouvrement »,
   « réécrit par le build ». Chaque fichier a une case (toutes cochées au départ) : un message, puis
   « Commiter la sélection » (`git commit -m <message> -- <fichiers cochés>`, le reste de l'index ne part pas ;
   accents retirés du message, règle du dépôt). Ou `/commite`, puis « Revérifier ».
4. **Nouveautés de l'amont** (information) : commits et fichiers touchés.
5. **Fichiers touchés des deux côtés** (information) : vue trois colonnes base / mon fork / l'amont.
6. **Prévision du merge** (`git merge-tree`) : sans conflit, ou la liste des fichiers en conflit. Elle choisit la voie.
7. **Voie A** (sans conflit et rien à pousser) : lance le script de merge réel ; ses questions « Synchroniser ? » et
   « Pousser ? » restent les siennes.
   **Voie B** (conflit prévu, ou commits locaux non poussés) : « Rattraper origin » si besoin (avance rapide), puis
   « Lancer le merge » (`git merge --no-ff --no-commit`), et pour chaque fichier en conflit : *Garder le mien*,
   *Prendre l'amont*, *Ouvrir dans VS Code* puis *Marquer résolu* (refusé s'il reste des marqueurs). Conflit de
   suppression : *Garder le fichier* / *Le supprimer*. « Terminer le merge » commite et écrit le journal ;
   « Abandonner » (confirmé) remet le dépôt dans son état d'avant.
8. **Commiter le journal** (`HISTORIQUE_SYNCHRO_FORK.md`), puis **Pousser** : confirmation, `git push origin development`,
   délai de 120 s.

Retard nul et rien à pousser : une ligne « fork à jour », les commits d'avance sont normaux.

### Ce qu'il ne fait jamais

- `--force`, `stash`, `reset`, `rebase` (le rebase est replié dans la section **Avancé**, à lancer soi-même).
- Une action sans clic, hormis le fetch ; chaque bouton affiche la commande git exacte.
- Commiter autre chose que le merge en cours, le journal ou les fichiers cochés à l'étape « Arbre propre » ; jamais
  de commit pendant un merge.
- Agir pendant un build (refus, et refus aussi si la détection est impossible), pendant qu'un script tourne, ou sur
  un merge qu'il n'a pas lancé (marque `.git/synchro-fork-assistant`, datée par `MERGE_HEAD`).
- Tuer un merge en plein vol : un délai dépassé est signalé, rien n'est arrêté.

**Pendant un merge de l'assistant, aucune autre session (Claude ou terminal) ne doit commiter ni abandonner le
merge** : un commit emporterait le merge à moitié résolu. La page le verrait ensuite comme un état étranger.

### Bancs

Dans `outils_docs/scripts_python/maintenance/` (code de sortie 0 = vert) : `test_synchro_fork_assistant.py`,
`test_synchro_fork_fusion.py`, `test_synchro_fork_fusion_suite.py`, `test_synchro_fork_web.py`, et la sonde Chrome
`test_synchro_fork_page_chrome.py`. Ils travaillent sur un faux dépôt temporaire (`faux_depot_synchro.py`) ; les
commandes git d'écriture sont limitées par `liste_blanche_git_synchro.py`.

<hr></hr>

## Les devices Tasmota développées :

```
    - Un Serveur de garage en cours: 
            * capteur de niveau de cuve d'eau
            * DS18B20 de cuve
            * DHT22 de Garage
            * 16 relais ModBus
    - Un module de Trappe de Grenier 2eme étage
    - Un serveur Relais de Cave
    - Un module SONOFF de lumière de porte
    - Un module SONOFF TV de Salon
    - Un module SONOFF VR
```

<hr></hr>

> [!WARNING]
> Urgent info that needs immediate user attention to avoid problems.

> [!CAUTION]
> La Freebox doit pouvoir rediriger les ports pour une connexion extérieure aux modules Tasmota
>   - Projecteur de jardin:
>       * IP: 192.168.0.40
>       * redirection de port TCP: 10040 -> 192.168.0.40:80
>   - Prise de piscine:
>       * IP: 192.168.0.41
>       * redirection de port TCP: 10041 -> 192.168.0.41:80
>   - TV de Salon:
>       * IP: 192.168.0.42
>       * redirection de port TCP: 10042 -> 192.168.0.42:80
>   - Serveur de Garage:
>       * IP: 192.168.0.43
>       * redirection de port TCP: 10043 -> 192.168.0.43:80
>   - Capteurs de cuve d'eau:
>       * IP: 192.168.4.1
>       * redirection de port TCP: 18123 -> 192.168.0.43:8080
>   - Rideau de Garage:
>       * IP: 192.168.0.43
>       * redirection de port TCP: 10043 -> 192.168.0.43:8081
>   - Serveur de Grenier RDC:
>       * IP: 192.168.0.44
>       * redirection de port TCP: 10044 -> 192.168.0.44:80
>   - Porte de Cave:
>       * IP: 192.168.0.45
>       * redirection de port TCP: 10045 -> 192.168.0.45:80
>   - Volet Roulant d'entrée:
>       * IP: 192.168.0.46
>       * redirection de port TCP: 10046 -> 192.168.0.46:80
>   - Trappe de Grenier 2eme Etage:
>       * IP: 192.168.0.47
>       * redirection de port TCP: 10047 -> 192.168.0.47:80
>   - Serveur de Cave:
>       * IP: 192.168.0.48
>       * redirection de port TCP: 10048 -> 192.168.0.48:80
>   - Disjoncteur Différentiel de PC de bureau:
>       * IP: 192.168.0.49
>       * redirection de port TCP: 10049 -> 192.168.0.49:80

<hr></hr>

> [!IMPORTANT]
>## TODO Liste :
>### Reste à faire pour le serveur de cuve d'eau :
>#####    🚩- Intégrer la gestion du bluetooth & Mi32 :
>#####          * En cours .....
>######         * https://tasmota.github.io/docs/Bluetooth_MI32/
>######         * https://tasmota.github.io/docs/Bluetooth_ESP32/
>######         * https://tasmota.github.io/docs/Bluetooth_MI32/#tasmota-and-ble-sensors
>#####    🚩- Pour le Driver 'controleUDP' et le module 'udpFonctions':
>######         * A TERMINER: 
>######             . Gestion de l'API Tasmota ou TasmotaClient dans la formule d'envoi et de réception des messages UDP
>######             . exemples dans le dossier suivant: tools\fw_TasmotaClient_arduino\TasmotaClient\examples
>#####    🚩- Paramétrer les grahiques avec : https://github.com/wjohn007/TasmoView
>######         * Cf. discussion : https://github.com/arendst/Tasmota/discussions/22851

> [!TIP]
>## Voici les commandes Tasmota personnalisées activées:
>####    - Toute commande ci-dessous accepte help (ou aide, ?) : &lt;Commande&gt; help liste ses sous-commandes, &lt;Commande&gt; help &lt;sous-commande&gt; en donne le détail<br>
>
>####    - ReglageGlobal afficheMemoire: Affiche l'utilisation des mémoires ROM, RAM & Garbage collector du module
>####    - ReglageGlobal nbLogsFiles 14<br>
>####    - ReglageGlobal heureReboot 03:30 | OFF : redémarrage quotidien à heure fixe, ou désactivé (sans valeur : état)
>####    - ReglageGlobal VoieReseau wifi | ethernet : choisit la voie réseau (`serveur.voieReseau` du persist), puis redémarre. Les deux voies s'excluent et gardent l'IP de `serveur.IP` ; en Ethernet, la surveillance du Wi-Fi et le Range Extender sont désactivés. Sans lien Ethernet, la carte ne répond plus que sur sa console série (sans valeur : état)<br>
>####    - ReglageGlobal timerRebootSansWifi 300 | OFF : redémarrage après N s sans Wi-Fi d'affilée (60 s minimum), ou désactivé<br>
>
>####    - ReglageLog : affiche le profil de logs actif, les sorties et le réglage de chaque module
>####    - ReglageLog help | help <sous-commande> | help niveaux : aide en console
>####    - ReglageLog profil normal|debug : applique un profil aux sorties (série, web, mqtt, syslog)
>####    - ReglageLog modbus debug : règle les logs d'un module (erreur, info, debug, detail)
>####    - ReglageLog tous detail : règle d'un coup les logs de tous les modules de la carte
>####    - ReglageLog syslog aucun : règle une sortie du profil actif (aucun, erreur, info, debug, detail)<br>
>####      (seule commande de réglage des logs : voir « Les logs Berry : charte et réglages » plus haut)
>
>####    - ReglageLeds : état du ruban WS2812 (mode AUTO/MANUEL, minutes restantes, couleur de la palette)
>####    - ReglageLeds rubanAuto | rubanManuel | rubanSuivante : retour en AUTO, couleur figée, couleur suivante de la palette
>####    - ReglageLeds rubanDuree 30 : durée du mode MANUEL en minutes (0 = jusqu'au double appui)
>####    - ReglageLeds rubanAppuiLong 15 : durée d'un appui long en dixièmes de s (SetOption32, commun à tous les boutons)
>####    - ReglageLeds rubanBouton : mode d'emploi du bouton (court = allume/éteint, long = couleur suivante, double = AUTO)<br>
>####      (persist : drivers.leds.environnement.leds.ruban ; pastille ⓘ dans le coin du bouton du ruban sur la page d'accueil)
>
>####    - RubanEsclave1 etat | auto | suivante : sur le maître, mode du ruban de l'esclave (POWER1), retour en AUTO, couleur suivante<br>
>####      (bouton du maître : clé "bouton" du relai virtuel du ruban ; protocole : PROTOCOLE_MODBUS.md, fin du §9)
>
>####    - ReglageUDP envoiUniCast 192.168.0.43 Salut Ca gaz ! OU ReglageUDP envoiUniCast 192.168.4.3 Salut Ca gaz ! : envoie un message UDP en unicast (test)
>####    - ReglageUDP envoiMultiCast Salut Ca gaz ! : envoie un message UDP en multicast (test, RangeExtender)
>####    - ReglageUDP telePeriodClients 300: Règle la téléPériode de scan des esclaves UDP
>####    - ReglageUDP forceEnvoiParams ON: Force l'envoi par un esclave UDP, des ses paramètres au maitre
>####    - (internes, envoyées entre modules : ReglageUDP ImAlive &lt;json&gt; | Timestamp &lt;secondes&gt; | ipMaitre &lt;ip&gt;)<br>
>
>####    - RoutageRangeExtender1 : pose les redirections NAPT (RgxPort) vers l'esclave 1 (esclave&lt;idx&gt; de discovery.json) => équivalent: RgxPort tcp, 8080, 10.99.0.2, 80<br>
>
>####    - ReglageCuve etalonnageCapteur ON: Augmente la frequence de mesure pendant 10min (frequence=1mesure/10s)
>####    - Backlog ReglageCuve hauteurCuve 110; ReglageCuve largeurCuve 180; ReglageCuve longueurCuve 340: Force et enregistre les dimensions de la cuve<br>
>
>####    - ReglageAna voltageMax 3.3 : règle la tension maximale admissible de l'ADS1115 (module cuve)
>####    - ReglageAna cablage : rappelle le câblage des 4 voies de l'ADS1115 (pont diviseur ou shunt à poser, valeurs E24)
>####    - ReglageAna voie A0 tension 0-10V : A0/A1 en tension 0-5V | 0-10V | 0-24V ; ReglageAna voie A2 courant 4-20mA : A2/A3 en courant 0-20mA | 4-20mA (boucle coupée détectée sous 3,6 mA)
>####    - ReglageAna seuilMin A0 50 : en dessous de 50 mV à l'entrée de l'ADS1115, la lecture est une erreur (sonde débranchée) ; 0 = désactivé
>####    - ReglageAna alimentation 3.3 : tension d'alimentation (VDD) de l'ADS1115, 3.3 ou 5 : change les résistances conseillées<br>
>####      (câblage et choix des résistances : outils_docs/Electronique/ADS1115/CABLAGE_ADS1115.md)<br>
>
>####    - ReglageModbus envoiMessageUDP 192.168.4.2 TEST : test, envoie le message en UDP unicast à l'IP
>####    - ReglageModbus envoiMessagTCP 192.168.4.2 TEST : test, ouvre une connexion TCP et y écrit le message<br>
>####    - ReglageModbus BaudrateModbus 9600
>####    - ReglageModbus RecupereBaudrateConn16channels 0x01
>####    - ReglageModbus ReglageBaudrateConn16channels 0x01 19200 (ou usine)
>####    - ReglageModbus TesteDebitConn16channels 0x01 9600 : teste la carte 16 relais à un débit donné, puis revient au bus
>####    - ReglageModbus VerifieConn16channels [corrige] [&lt;carte&gt;] : retrouve l'ID et le débit de la carte 16 relais, compare au persist, corrige si demandé
>####    - ReglageModbus ActivationReponseCMD ON|OFF': (Des)active la réponse de l'esclave aux commandes ModBus
>####    - ReglageModbus RelaisPushMQTT ON|OFF : (maître) recopie les push UDP des esclaves sur tele/&lt;topic&gt;/MODBUSPUSH, pour les observer depuis le réseau maison (OFF par défaut)
>
>####    - (interne : ReglageModbus ImAlive ON|OFF force le maître à connecter ses clients ModBus TCP)
>
>####    - ReglageSlaveModBus1 id 0x02   => Change le l'adresse ModBus de l'esclave ModBus_TasmotaSlaveModBus1
>####    - HSBCOLOR1 &lt;teinte&gt; | HSBCOLOR2 &lt;saturation&gt; ; DIMMER&lt;id&gt; &lt;luminosité&gt; : sur un module à LEDS WS2812 pilotées en ModBus, remplacent les commandes Tasmota et envoient la valeur à l'esclave (DIMMER 0 = POWER OFF)
>####    - SCHEME 0..14 : (maître) animation des rubans WS2812 des esclaves ModBus (0 = une seule couleur) ; sans paramètre : la valeur mémorisée
>####    - RubanEsclave1 etat | auto | suivante : (maître) mode du ruban de l'esclave du relai virtuel POWER1 (AUTO, ou MANUEL et minutes restantes), retour en AUTO, couleur suivante<br>
>
>####    - EtatPompe : (cave) affiche l'état de la pompe vide-cave, des niveaux et de l'alerte
>####    - AcquittePompe : (cave) efface l'alerte et le compteur de relances, puis affiche l'état<br>
>
>####    - ReglageVolets Inclinaison &lt;id&gt; : angle mesuré par le MPU6050 du volet ; ReglageVolets Apprentissage &lt;id&gt; ouvert|ferme : apprend ses butées (voir « Inclinaison d'un volet ou d'une trappe »)<br>
>
>####    - ReglageGarage, ReglageDiscovery, ReglageRangeExtender, ReglageConn16Channel, ReglageTCP, ReglageLoRaWan : aucune sous-commande (seulement help ; leurs logs se règlent avec ReglageLog)

<hr></hr>

>## Modifications du code C++ en dur
>### Dans 'tasmota/tasmota_xdrv_driver/xdrv_01_9_webserver.ino':
>####   - Modification de la ligne 1228 & 427:
>####       * Remplacement de: WSContentSend_P(HTTP_END, TasmotaGlobal.version, TasmotaGlobal.image_name);
>####           par: WSContentSend_P(HTTP_END, TasmotaGlobal.version);
>####       * Remplacement de: 
```javascript
"<p></p><div style='text-align:right;font-size:11px;'><hr><a href='https://github.com/arendst/Tasmota' target='_blank' style='color:#aaa;'>Tasmota %s %s " D_BY " Theo Arends</a></div>"
```
>####           par: 
```javascript
"<p></p><div style='text-align:right;font-size:11px;'><hr><a href='https://github.com/arendst/Tasmota' target='_blank' style='color:#aaa;'>Tasmota %s " D_BY " Au Bonheur des Asturies</a></div>"
```

$\textsf{\color{#f5750e}{Emoji possibles dans README.md}}$  
[Cliquez ici!](https://github.com/ikatyang/emoji-cheat-sheet/blob/github-actions-auto-update/README.md#table-of-contents)

🔴🟠🟡🟢🔵🟣🟤⚫⚪🔘🛑⭕
🟥🟧🟨🟩🟦🟪🟫⬛⬜🔲🔳⏹☑✅❎
❤️🧡💛💚💙💜🤎🖤🤍♥️💔💖💘💝💗💓💟💕❣️♡
🔺🔻🔷🔶🔹🔸♦💠💎💧🧊
🏴🏳🚩🏁
◻️◼️◾️◽️▪️▫️
