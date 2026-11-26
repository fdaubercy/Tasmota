# Voie MQTT maître/esclaves

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Voie MQTT maître/esclaves (P4 du garage vers des esclaves Tasmota natifs)

Le maître commande des esclaves Tasmota qui n'ont pas de Berry (projecteur LED, pompe de la piscine, cuve) par leurs topics natifs `cmnd/<topic>/...`, sans passer par ModBus. Les retours `stat/<topic>/...` et `tele/<topic>/...` servent d'accusé et d'état. Modules : `data/fs/mqttLiaisonFonctions.be` (garde-fous, sans MQTT, testable sans carte) et `data/fs/controleMqttLiaison.be` (publish et subscribe). Plan `tasks/plans/voie-mqtt.md`, analyse `ANALYSE_VOIE_MQTT_2026-11-16.md`.

**État au 2026-11-21** (plan `tasks/plans/voie-mqtt.md`, 95 %) : le code, son banc et les essais sur carte des 2026-11-20 et 21 sont faits : ordres (A6 ; `controleMqttLiaison.be::recu` rend `true`, ce qui a supprimé la reprise de chaque `stat/<esclave>/POWER` comme une commande ; après la correction de la garde, 11 ordres sur 200 restaient non appliqués en 6 s contre 26 avant), coupure du broker et alerte (A7), pompe de piscine ESP8266 sans Berry et relais du maître recalé sur l'état réel de l'esclave (A9, `controleMqttLiaison.be::recale`). Restent l'essai du portail de jardin (A10, jamais sans l'utilisateur) et la montée intermittente de la mémoire Berry du P4, sans cause établie (non reproduite le 2026-11-20). Ne pas la présenter comme une voie validée pour le portail.

### Dans `_persist.json` (bloc `drivers.liaisonMqtt`)

| Clé | Rôle | Défaut |
|---|---|---|
| `activation` | `ON` charge le driver ; `OFF` le laisse inerte | `OFF` |
| `environnement` | obligatoire, `{}` suffit (tout bloc de `drivers` doit en porter un) | |
| `log` | seuil de la cible `liaisonMqtt` (charte des logs) | |
| `esclaves.<nom>.activation`, `.topic` | un esclave par entrée ; `topic` = Topic Tasmota de l'esclave, sans `+` ni `#`, unique | |
| `garde.fenetreMs` | fenêtre glissante des comptages | 10000 |
| `garde.maxParElement` | ordres par élément dans la fenêtre avant quarantaine | 10 |
| `garde.maxTotal` | ordres au total dans la fenêtre avant coupe-circuit | 60 |
| `garde.quarantaineMs` | durée de la quarantaine d'un élément | 60000 |
| `garde.coupureMs` | durée du coupe-circuit global | 300000 |
| `garde.delaiAccuseMs` | attente de l'accusé avant renvoi (mesuré jusqu'à 1,6 s en Wi-Fi direct) | 3000 |
| `garde.essaisMax` | émissions au total, la première comprise, avant d'abandonner l'ordre | 3 |
| `garde.ageEtatMs` | au-delà, un état connu n'est plus cru : l'ordre identique repart | 30000 |
| `alerteBrokerMs` | broker injoignable depuis ce délai : alerte sur l'accueil et log `erreur` (une fois), puis un message au retour | 120000 |

Une clé absente, non entière, nulle ou négative prend sa valeur par défaut. Les clés `garde.ageEtatMs` et `alerteBrokerMs` ne sont dans aucun persist du dépôt : les défauts s'appliquent.

### Éléments virtuels `MQTT_<nom>`

- **Relais** : `"virtuel": "MQTT_<esclave>"` et `"mqtt": {"commande": "Power1"}` (défaut `Power1`). L'ordre part par `controleMqttLiaison.be::ordonne`, que le driver déclare comme voie « MQTT » au registre de `controleGeneral.be::declareVoie` (appelé par `set_power_handler` ; préfixe non déclaré : `controleGeneral.be::voieHistorique`). Avec `"repli": "ModBus_TasmotaSlaveModBus1"` (ou une autre voie ModBus), un ordre refusé parce que l'esclave est hors ligne ou que le coupe-circuit est ouvert repart par cette seconde voie ; sans repli, il est perdu et un message `erreur` le dit.
- **Capteurs, boutons, interrupteurs** : `"mqtt": {"chemin": "DS18B20.Temperature"}` (ou `ANALOG.A1`, `Button1`, `Switch1`), avec `"declencheur"` pour imposer la famille. Un appui local sur l'esclave arrive par `stat/<topic>/RESULT` ou `POWER` : le maître l'apprend sans renvoyer d'ordre.
- **Bouton du maître recalé** : quand un état `POWER<n>` d'un esclave arrive et qu'aucun ordre n'est en attente, le relais actif du maître qui le commande est remis sur l'état réel (`controleMqttLiaison.be::recale`). L'ordre qui en découle est refusé « identique » par G3 : rien n'est renvoyé. Pendant un ordre en attente, rien n'est recalé.
- **Périmé** : pendant l'alerte du broker, ou quand un esclave est annoncé `Offline` par son LWT, chaque élément `MQTT_<nom>` actif de cet esclave a une ligne « dernière valeur X (périmé) » (mesure) ou « état réel inconnu (périmé) » (relais) sur l'accueil du maître.

### Régler un esclave sans Berry (Tasmota natif, ESP8266 compris)

Rien à embarquer sur l'esclave : seul son topic compte. Relevé et règles du 2026-11-20 (lecture de `support_tasmota.ino::SendKey`) :

| Réglage | Valeur | Pourquoi |
|---|---|---|
| `ButtonTopic`, `SwitchTopic` | `0` (défaut) | l'appui commute le relais local, même sans broker, et l'esclave publie son nouvel état. Un topic posé ferait publier `cmnd/<topic>/POWER<n> TOGGLE` sans commuter le relais local : **jamais le topic du maître**, ce serait un ordre natif hors garde-fous |
| `SetOption73`, `SetOption114` | `0` si le bouton doit garder la main sur son relais (projecteur, pompe) ; `1` s'il doit seulement prévenir le maître | à `1`, l'esclave publie `{"Button1":{"Action":"SINGLE"}}` ou `{"Switch1":{"Action":"ON"}}`, lu par un élément `boutons` ou `interrupteurs` du maître (`mqtt.chemin` `Button1`, `Switch1`) |
| `SetOption19` | `0` | à `1` (découverte Home Assistant), ces messages `Action` ne partent plus |
| `ButtonRetain`, `SwitchRetain`, `PowerRetain` | `0` | un ordre ou un état retenu serait rejoué à chaque reconnexion |

Côté maître : déclarer l'esclave dans `drivers.liaisonMqtt.esclaves` puis un relais `"virtuel": "MQTT_<esclave>"` (exemples du P4 : `relai24` « Projecteur Jardin », `relai25` « Pompe Piscine », `relai26` « Projecteur Barbecue »). Le nombre de relais de Tasmota est le plus grand `id` actif (`configDevices.be`), un `id` au-delà des autres reste donc commandable.

### Garde-fous

- **G3** : pas d'ordre si l'état connu de l'esclave est déjà la valeur demandée et qu'il a moins de `ageEtatMs`.
- **G4** : limiteur par élément, puis quarantaine ; **G5** : coupe-circuit global. Un maître fautif qui recommande l'inverse à chaque retour est borné à `maxParElement` ordres.
- **Accusé** : le retour attendu d'un ordre n'est pas un évènement (pas d'écriture en boucle). Sans accusé après `delaiAccuseMs`, l'ordre est renvoyé jusqu'à `essaisMax`, puis abandonné et loggué. Au plus 5 publish par seconde, car un publish lent bloque `loop()`.
- **Broker perdu** : voir `alerteBrokerMs` ; au retour, les ordres en attente et les états connus sont oubliés et chaque esclave est relu (`cmnd/<topic>/Power` sans valeur).
- **Limite connue** : le message testament (LWT) n'est pas délivré quand c'est le broker lui-même qui s'arrête, les esclaves restent « en ligne » côté maître pendant la coupure.

### Commande `ReglageMqttLiaison`

| Sous-commande | Effet |
|---|---|
| `etat` (défaut) | `{coupe, quarantaines, attentes, elements, en_ligne}` |
| `rearme` | lève quarantaines et coupe-circuit ; ne touche ni aux états connus ni aux ordres en attente |
| `ordre <esclave> <commande> <valeur>` | envoie un ordre par les garde-fous (essai) ; commandes permises : `Power`, `Power<n>` (ON, OFF, 1, 0, true, false), `Dimmer`, `CT` ; `Power0`, `TOGGLE`, `Restart`, `Backlog`, `Br` sont refusés |

Réponses de `ordre` : `envoyer`, `identique`, `attente`, `quarantaine`, `coupe`, `invalide`, `inconnu` ou `hors_ligne` (réseau, broker ou esclave Offline). `ReglageMqttLiaison help` donne l'aide en console.

### Banc

`python outils_docs/scripts_python/berry/banc_mqtt_liaison.py` (code 0 = vert ; chaque garde-fou retiré dans une copie du module doit faire échouer le banc : sans `--sans-mutants`, les mutants sont joués). Il ne prouve ni la solidification ni le comportement du vrai MQTT : un essai sur carte reste nécessaire (journal `/cs`, firmware recompilé par la page Build, car `mqttLiaisonFonctions` est solidifié).

<hr></hr>
