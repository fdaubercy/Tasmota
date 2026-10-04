![Tasmota logo](/tools/logo/TASMOTA_FullLogo_Vector.svg#gh-light-mode-only)![Tasmota logo](/tools/logo/TASMOTA_FullLogo_Vector_White.svg#gh-dark-mode-only)

[![GitHub version](https://img.shields.io/github/release/arendst/Tasmota.svg)](http://ota.tasmota.com/tasmota/release)
[![GitHub download](https://img.shields.io/github/downloads/arendst/Tasmota/total.svg)](https://github.com/arendst/Tasmota/releases/latest)
[![License](https://img.shields.io/github/license/arendst/Tasmota.svg)](LICENSE.txt)
[![Discord](https://img.shields.io/discord/479389167382691863.svg?logo=discord&logoColor=white&color=5865F2&label=Discord)](https://discord.gg/Ks2Kzd4)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-Ready--to--Code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/arendst/Tasmota)

<hr></hr>

**Vous trouverez ici la méthodologie de développement de scripts en langage BERRY pour tasmota.<br/> Les différents devices développéespour la domotique du domicile sont des forks de Tasmota personnalisés.**

<hr></hr>

> [!TIP]
>## Documentation technique de ce dossier :
>####    - [SOLIDIFICATION_BERRY.md](SOLIDIFICATION_BERRY.md) : la solidification Berry — comment ça marche, comment **vérifier** qu'elle a eu lieu, les paramètres, et 11 pièges documentés.
>####       * À retenir : elle est **active par défaut** à chaque build ; les modules de `data/fs/` ne sont **jamais** solidifiés ; la ligne `Berry solidification: …` d'un build **ne prouve rien** (§5).

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
>####    - ReglageUDP envoiMessage 192.168.0.43 Salut Ca gaz !: Envoi un message par UDP
>####    - ReglageUDP telePeriodClients 300: Règle la téléPériode de scan des esclaves UDP
>####    - ReglageUDP forceEnvoiParams ON: Force l'envoi par un esclave UDP, des ses paramètres au maitre<br>
>
>####    - RoutageRangeExtender esclave1: Active RgxNAPT => équivalent: RgxPort tcp, 8080, 10.99.0.2, 80<br>
>
>####    - ReglageCuve etalonnageCapteur ON: Augmente la frequence de mesure pendant 10min (frequence=1mesure/10s)
>####    - Backlog ReglageCuve hauteurCuve 110; ReglageCuve largeurCuve 180; ReglageCuve longueurCuve 340: Force et enregistre les dimensions de la cuve<br>
>
>####    - ReglageModbus envoiMessageUDP 0x01 TEST<br>
>####    - ReglageModbus BaudrateModbus 9600
>####    - ReglageModbus RecupereBaudrateConn16channels 0x01
>####    - ReglageModbus ReglageBaudrateConn16channels 0x01 19200
>####    - ReglageModbus ActivationReponseCMD ON|OFF': (Des)active la réponse de l'esclave aux commandes ModBus
>
>####    - ReglageSlaveModBus1 id 0x02   => Change le l'adresse ModBus de l'esclave ModBus_TasmotaSlaveModBus1<br>
>
>####    - ReglageUDP envoiUniCast 192.168.0.43 Salut Ca gaz ! OU ReglageUDP envoiUniCast 192.168.4.3 Salut Ca gaz !
>####    - ReglageUDP envoiMultiCast Salut Ca gaz ! OU ReglageUDP envoiMultiCast 192.168.4.3 Salut Ca gaz !
>####    - ReglageUDP forceEnvoiParams ON

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
