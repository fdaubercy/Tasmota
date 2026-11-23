# Logs Berry : charte et réglages

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

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
   `garage`, `cuve`, `rideau`, `leds`, `historique` (S3/P4 avec historique local), `ecranCave`,
   `ecranDebits` et `ecranSysteme` (cartes à écran ; `ecranCave` aussi sur le serveur de la cave, pour ses touches),
   `liaisonMqtt` (voie MQTT du P4) et `emulationHue` (émulation Hue pour Alexa). Un binôme peut aussi déclarer
   sa propre cible (`logFonctions.declare`).
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
