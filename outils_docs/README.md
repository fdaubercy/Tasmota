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
(toutes les secondes, à chaque trame reçue).

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
  affiché dans la console (comme les autres outils). Pas de cible PlatformIO Custom : une cible est un `pio run`,
  elle ne peut pas en piloter d'autres.

### Les environnements et les actions

- **Classement** : *Mes cartes* (envs de `platformio_tasmota_cenv.ini`), *Mes bases* (`tasmota32-base`,
  `tasmota32s3-base-N16R8`, `tasmota32p4-base-*`) et *Tasmota (amont)*, replié par défaut, en sous-groupes
  (safeboot, ESP32, langues, ESP8266).
- **Quatre actions**, combinables, appliquées à tous les envs cochés : compiler, téléverser le firmware,
  construire le file system, téléverser le file system. Dans un env, l'ordre est toujours compiler, téléverser,
  construire le FS, téléverser le FS, en ne lançant que ce qui est coché. Un échec arrête **cet env** (étapes
  suivantes « annulées ») ; les autres envs continuent.
- **COM ou OTA par ligne.** Le port COM est lu dans le `upload_port` de l'env (y compris hérité par `extends`),
  vide s'il n'y en a pas. L'IP OTA est lue dans `WIFI_IP_ADDRESS` de `tasmota/user_config_override.h`, bloc du
  firmware de l'env. L'OTA est grisée pour les envs qui ne chargent pas `pre_utilitaires_platformio.py` (ESP8266).

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

### L'IP de l'OTA

Lue dans `WIFI_IP_ADDRESS`. Si elle vaut `0.0.0.0` (DHCP) ou manque, la ligne demande une IP à saisir : elle ne
vaut que pour ce lancement (rien n'est réécrit) et la ligne est refusée tant que le champ est vide.

### OTA du firmware

La page lance `pio run -e X` (compilation), puis envoie elle-même `.pio/build/<env>/firmware.bin.gz` (à défaut
`firmware.bin`) par `/up` puis `/u2` (protocole de `pio-tools/espupload.py`). Si la carte n'a qu'une partition OTA (image
`0xE9`), la page la bascule d'abord en safeboot par `/u4`. Succès **prouvé par `Status 2`** : la carte doit
revenir (90 s maximum) avec une version et une date de compilation changées ; le texte de la réponse seul ne
suffit pas. Aucun script de build n'est modifié et il n'y a plus de variable `TASMOTA_OTA_IP`.

### OTA du file system

Tasmota n'accepte pas d'image LittleFS en OTA : la page envoie le **contenu de `.pio/build/<env>/littlefs_data`**
(exactement ce que contiendrait l'image), fichier par fichier par `/ufsu`, `_persist.json` compris. Déroulé :

1. construction du FS si elle n'est pas déjà cochée ;
2. **sauvegarde du `_persist.json` de la carte** dans `%LOCALAPPDATA%\outils_tasmota\build\persist\<env>-<horodatage>.json`.
   Impossible à télécharger : **rien n'est envoyé**, l'env est en échec ;
3. envoi des fichiers, sous-dossiers compris ;
4. relecture du `_persist.json` de la carte, comparé octet pour octet à celui envoyé (différent : env en échec,
   **pas de restauration automatique**, le chemin de la sauvegarde est affiché) ;
5. rechargement des globales Berry (`Br import persist …`) ;
6. `Restart 1`, attente du retour de la carte (90 s), relecture du persist. Si le persist relu après le
   redémarrage diffère de celui envoyé, un **avertissement** est affiché avec le chemin de la sauvegarde (l'env
   n'échoue pas : les fichiers sont déjà envoyés et la carte est revenue) ; carte non revenue : env en échec.

### Téléversement série : il emporte `littlefs.bin`

« Téléverser le firmware » **par câble** flashe aussi le file system (persist compris) si
`.pio/build/<env>/littlefs.bin` existe, c.-à-d. si un `buildfs` a eu lieu depuis la dernière purge
(`pio-tools/post_esp32.py`). Comportement gardé par choix ; la ligne l'annonce avant le lancement.

### Refus, attente, arrêt

- **Refus avant lancement** : un build tourne déjà (VS Code, cible Custom, même logique que le hook `garde_build`) ;
  un port COM tenu par un autre outil (pont série, sniffeur, testeur) ou absent, pour une action d'envoi ; **deux
  lignes avec envoi par COM sur le même port** (une seule carte branchée par port ; compiler seul plusieurs envs au
  port partagé reste permis).
- **Attente** : le contrôle « build en cours » est refait avant chaque env. Si un build est apparu entre deux envs,
  la série attend (« en attente : build en cours ») et reprend à sa fin ; on peut l'arrêter.
- **Arrêt** : « Arrêter après cet env » (propre) ou arrêt immédiat, qui peut laisser une carte à moitié flashée et
  des copies temporaires dans `data/<lieu>/<carte>` (la page les signale, ne les efface pas).

### Journaux, mémoire de la page, fichiers réécrits

- Sortie complète de chaque `pio run` (codes ANSI retirés) : `%LOCALAPPDATA%\outils_tasmota\build\journaux\`,
  dépliable sur la page.
- Derniers choix : à chaque lancement, la page
  écrit les lignes lancées (env, COM ou OTA, port, IP saisie) et les actions cochées dans `derniers.json` (dans
  `%LOCALAPPDATA%\outils_tasmotauild\`, hors dépôt, écriture atomique) ; à l'ouverture suivante elle recoche ces lignes et ces actions. Le port
  mémorisé ne sert que pour un env dont le port n'est pas réécrit dans un `.ini` (envs de l'amont), l'IP mémorisée
  que si aucune IP n'est lue dans `user_config_override.h`.
- Références de progression (nombre de `.o` du dernier
  build réussi de chaque env, base du % de compilation) : `references.json` dans
  `%LOCALAPPDATA%\outils_tasmota\build\`, hors dépôt.
- Chaque `pio run` réécrit `platformio_override.ini` et `tasmota/user_config_override.h` (`CFG_HOLDER`) :
  **fichiers à commiter** après un lancement (la page le rappelle en fin de lancement), et à sauvegarder avant
  une série d'essais.
- Banc : `test_build_*.py` dans `outils_docs/scripts_python/outils_pc/` (faux `pio`, carte simulée ; code de sortie
  0 = vert), à lancer avec le Python du penv PlatformIO.

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
>####    - ReglageGarage, ReglageDiscovery, ReglageRangeExtender, ReglageConn16Channel, ReglageTCP, ReglageVolets, ReglageLoRaWan : aucune sous-commande (seulement help ; leurs logs se règlent avec ReglageLog)

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
