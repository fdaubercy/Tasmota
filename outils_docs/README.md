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
   `garage`, `cuve`, `rideau`, `leds`, `historique` (S3/P4 avec historique local).
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
3. envoi des fichiers, sous-dossiers compris ;
4. relecture du `_persist.json` de la carte, comparé octet pour octet à celui envoyé (différent : env en échec,
   **pas de restauration automatique**, le chemin de la sauvegarde est affiché) ;
5. rechargement des globales Berry (`Br import persist …`) ;
6. `Restart 1`, attente du retour de la carte (90 s), relecture du persist. Si le persist relu après le
   redémarrage diffère de celui envoyé, un **avertissement** est affiché avec le chemin de la sauvegarde (l'env
   n'échoue pas : les fichiers sont déjà envoyés et la carte est revenue) ; carte non revenue : env en échec.

### Onglet « Fichiers » : envoyer quelques fichiers du FS

Pour remplacer un ou deux fichiers sur une carte (un `.be` corrigé, un gabarit, le persist) sans renvoyer tout le
file system. Onglet **Fichiers**, en haut de la page (l'onglet ouvert est retenu au rechargement). Deux transports :
**HTTP** (adresse de la carte) ou **MQTT** (par le broker, voir plus bas).

1. **Carte destinataire** (colonne de gauche) : les envs « Mes cartes » envoyables en OTA. L'adresse et sa
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
chargé par l'autoexec de la carte (`demarrage.charge(["fsMqtt"])`) et présent sur son FS — à envoyer une première
fois en HTTP ou par câble. Sans lui, la page le dit (« aucune réponse sur fsmqtt/<topic> ») et rien n'est envoyé.

**Effacer tout le FS avant l'envoi** (MQTT seulement, confirmation) : la carte supprime TOUS ses fichiers et
dossiers (persist, autoexec et `fsMqtt.be` compris ; `/sd` de la flash aussi), par lots de 20 pour ne jamais
bloquer, puis toute l'image est envoyée. Le module reste en mémoire le temps de la session ; si la carte redémarre
entre les deux, elle repart sans Berry : la reprendre en HTTP (cet onglet) ou par câble. Bancs :
`berry/banc_fsmqtt.py` (module), `outils_pc/test_build_ota_mqtt.py` (PC) ; aucun essai sur carte à ce jour.

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
  compilé ; un `-t upload` seul recompilerait tout (`CFG_HOLDER` change à chaque `pio run`).
- **Attente** : le contrôle « build en cours » est refait avant chaque env. Si un build est apparu entre deux envs,
  la série attend (« en attente : build en cours ») et reprend à sa fin ; on peut l'arrêter.
- **Arrêt** : « Arrêter après cet env » (propre) ou arrêt immédiat, qui peut laisser une carte à moitié flashée et
  des copies temporaires dans `data/<lieu>/<carte>` (la page les signale, ne les efface pas). Un envoi OTA en
  cours n'est pas coupé, un envoi OTA pas encore commencé est annulé ; un upload fini avec succès reste un succès.
- **Arrêt de la page** (Ctrl+C dans sa console, fermeture) : un envoi vers une carte en cours (téléversement par
  câble, envoi OTA) va d'abord à son terme, puis le reste du lancement est tué ; un second Ctrl+C force l'arrêt.
  L'écriture du port COM est refusée pendant un lancement de la page **et** pendant un build lancé ailleurs.

### Journaux, mémoire de la page, fichiers réécrits

- Sortie complète de chaque `pio run` (codes ANSI retirés) : `%LOCALAPPDATA%\outils_tasmota\build\journaux\`,
  dépliable sur la page (« Journal complet »). Les journaux d'un env se lisent dans l'ordre de leur **date de
  modification** (pas l'heure écrite dans le nom, qui recule au passage à l'heure d'hiver). Au démarrage de la page,
  les journaux de **plus de 30 jours** sont supprimés (une suppression impossible est comptée dans la console) :
  seulement les journaux de la page (`date-heure-env-action.log`), et pas si une autre instance tient déjà le port.
- **Sortie de pio en direct** : sous chaque env du suivi, un panneau « Sortie de pio (en direct) », ouvert au départ
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

Une page qui pose des questions et en tire le `_persist.json` d'une **nouvelle carte**, avec l'`autoexec.be`, la
section du cenv et la section `#elif` de `tasmota/user_config_override.h` qui vont avec. Les questions et leurs règles
viennent d'un **modèle** (`outils_docs/schemas/modele_persist.json`) qui se met à jour à partir des persists du dépôt.
Le moteur d'écriture est celui de « Fichiers Berry par env » (créer un env), sans changement de comportement.
Conception : [spec](../docs/superpowers/specs/2026-10-27-assistant-persist-design.md) ; plan :
`tasks/plans/assistant-persist.md`.

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
   thermomètres, analogiques). Les broches proposées sont celles de la puce d'après `data/fs/configGlobal.be`.
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

### Limites connues

- L'éditeur ne règle que **activation, nom, broche et type**. `idModBus`, `virtuel`, `channel`, `nbLeds` se
  complètent à la main dans le `_persist.json` créé.
- Les broches de **SD, I2S, Ethernet et LoRa** ne sont pas contrôlées.
- Les éléments ne vont que sur le **bloc métier principal**.
- La **modification d'un env existant** (A10) est en pause : l'assistant ne sait que créer.
- Clés `adressMAC` / `adresseMAC` et `telePeriod` : tranché le 2026-10-28 — `telePeriod` de `serveur.udp` et `serveur.rangeExtender` retirées (jamais lues), MAC écrite dans `adresseMAC` dès le boot par `globalFonctions`, `adressMAC` retirée ;
  voir `outils_docs/ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md`.

### Bancs

Dans `outils_docs/scripts_python/outils_pc/`, avec le Python du penv PlatformIO (code de sortie 0 = vert) :
`test_assistant_persist_modele.py`, `_parc.py`, `_elements.py`, `_generation.py`, `_creation.py`, `_fidelite.py`,
`_web.py`, et la sonde Chrome `test_assistant_persist_page_chrome.py` ; cible Custom :
`build/test_cible_assistant_persist.py`. Les bancs travaillent sur un dépôt d'essai temporaire (lecture seule des
vrais persists) : aucun n'écrit dans le vrai dépôt ni dans le vrai dossier des sauvegardes.

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
