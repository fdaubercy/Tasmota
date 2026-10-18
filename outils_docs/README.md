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
- [SOLIDIFICATION_BERRY.md](SOLIDIFICATION_BERRY.md) — la solidification Berry : fonctionnement, **vérification**, paramètres, 11 pièges.
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
   `garage`, `cuve`.
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

<hr></hr>

## Les graphiques des mesures (cartes S3/P4)

Les cartes ESP32-S3 et P4 tiennent un historique de leurs mesures (`data/fs/historiqueFonctions.be`) :
24 h en RAM au pas de 5 min, et min/moy/max horaires en flash, un fichier par mois. Le bouton
**Graphiques** de la page d'accueil ouvre `/graphiques`, qui les trace avec uPlot. Les ESP32 classiques
n'ont ni l'historique ni la page (fichiers exclus de leur LittleFS) : leurs courbes sont dans Grafana.

- **Vues** : « 24 dernières heures », puis un mois par entrée du sélecteur (moyenne horaire et bande
  min-max). Un mois marqué « ancienne liste de séries » date d'avant un changement des séries du persist.
- **Séries** : une case par série, mémorisée dans le navigateur. Deux axes Y, attribués aux unités les
  plus partagées. Un trou dans une courbe = pas de mesure (carte arrêtée, esclave muet, capteur absent).
- **Historique long** : le bouton « Historique long (Grafana) » ouvre le tableau du Pi.
- uPlot est servi **par la carte** (`/sd/js/uPlot.iife.min.js`, 49 Ko), sans Internet : il est gardé
  dans le `localStorage` du navigateur et n'est redemandé qu'à un changement de version.

### Dans `_persist.json`

```json
"diverses": {
    "historique": {
        "activation": "ON",
        "series": { ... },
        "affichage": {
            "tauxRemplissage":  {"libelle": "Remplissage", "unite": "%", "facteur": 100},
            "temperatureESP32": {"libelle": "Température ESP32", "unite": "°C"}
        },
        "grafana": "http://192.168.0.5:3000/d/historique-cuve?var-appareil=%topic%"
    }
}
```

`affichage` et `grafana` sont facultatifs. Sans `affichage`, libellé = nom de la série et unité devinée
d'après le nom (`temperature` → °C, `hauteur` → cm, `volume` → L, `taux` → %). `facteur` multiplie la
valeur affichée (0-1 → %). `%topic%` est remplacé par le topic de la carte ; sans `grafana`, pas de bouton.

**Carte sans historique local** (ESP32 classique, ou historique à `OFF`) : la même clé `grafana`, dans un bloc
`"historique": {"grafana": "…"}`, ajoute à la page d'accueil un bouton **Historique (Grafana)** qui ouvre
directement le tableau (`controleWeb.boutonGrafana`, commun à toutes les cartes ; module solidifié : il faut
le firmware recompilé). Il n'apparaît pas là où l'historique est actif, le bouton « Graphiques » y menant
déjà. Clé non posée sur la cave et le bureau (décidé le 2026-10-18) : le tableau `historique-cuve` n'a que
des panneaux de cuve, leurs courbes y seraient vides.

### Vérifier

- `/histo?p=liste`, `/histo?p=jour`, `/histo?p=mois&m=AAAA-MM` donnent le JSON brut. En `curl`, ajouter
  `-H "Referer: http://<ip>/"` : sans lui, Tasmota coupe la connexion sans réponse (`curl: (52)`).
- Banc hors carte : `python outils_docs/scripts_python/berry/banc_graphiques.py` (code de sortie 0 = vert).
- Sur le P4, les mesures de la cuve sont écartées de l'historique tant que l'esclave ne les donne pas
  pour valides (`controleGarage.filtreHistorique`) : une cuve sans capteur donne des trous, pas des zéros.

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
>####    - HSBCOLOR1 &lt;teinte&gt; | HSBCOLOR2 &lt;saturation&gt; ; DIMMER&lt;id&gt; &lt;luminosité&gt; : sur un module à LEDS WS2812 pilotées en ModBus, remplacent les commandes Tasmota et envoient la valeur à l'esclave (DIMMER 0 = POWER OFF)<br>
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
