# Analyse — ModBus en Berry & table de découverte `discovery.json`

> Document créé le **2026-09-22**. Consigne deux analyses menées à la suite :
> 1. **Comment fonctionnent les programmes ModBus en Berry** (les 3 transports, la carte
>    16 relais, la communication ESP32↔ESP32, le push esclave→maître).
> 2. **Audit de la table de découverte** `/json/discovery.json` : construction, lecture,
>    paramètres manquants, et le tableau des éléments restant à paramétrer.
>
> Complément technique : `outils_docs/PROTOCOLE_MODBUS.md` (§8 carte 16 relais, §9 synchro
> maître/esclave). Ce document-ci ne le remplace pas : il le **prolonge** côté découverte.
>
> **Méthode** : toute affirmation ci-dessous est référencée par `fichier:ligne`. Les
> constats issus d'une lecture de code sont marqués ✅ ; les points de conception
> (jugements) sont marqués 💡.

---

# PARTIE 1 — Les programmes ModBus en Berry

## 1.1 Architecture d'ensemble

Le framework pose une surcouche Berry sur la pile ModBus native de Tasmota et gère
**trois transports en parallèle**, choisis par `_persist.json → drivers.ModBus.typeComm`
(`Serial` / `TCP` / `UDP` ; `MQTT` est déclaré mais **jamais implémenté**).

| Fichier | Rôle |
|---|---|
| `data/fs/modbusFonctions.be` (1574 l.) | Cœur logique : file FIFO, envoi/réception, appariement, encodage/décodage, CRC16 |
| `data/fs/controleModbus.be` (338 l.) | Driver : ouvre les ports, enregistre les règles de réception, aiguille maître/esclave |
| `data/fs/modBus_Conn16channels.be` (550 l.) | Pilotage de la carte 16 relais RS485 |
| `data/fs/modBus_TasmotaSlaveModBus.be` (851 l.) | Communication ESP32 ↔ ESP32 (devices virtuels) |
| `data/fs/tcpFonctions.be` / `udpFonctions.be` | Transports TCP et UDP bas niveau |
| `data/fs/globalFonctions.be` | Émet le push spontané d'état capteur/bouton vers le maître |

- **Émission** : tout part de `envoiMsgModbus()` (`modbusFonctions.be:573`), qui dispatche
  vers `envoiMsgModbusSerial` / `...TCP` / `...UDP`.
- **Réception** : règles Tasmota `ModbusReceived` / `...TCP` / `...UDP`, enregistrées
  conditionnellement dans `controleModbus.init()`, vers `recupereReponseModBus*()`.

## 1.2 File FIFO du maître (`modbusFonctions.be:424-500`)

L'ancien booléen distribué `attenteReponse` (posé/levé depuis 11 endroits) a été remplacé
par une file à **un seul message en vol** :

- `enfileMsg()` empile `{paramMSG, typeMsg, tentatives}` puis `pompeQueue()`.
- `pompeQueue()` : si `enVol == nil`, dépile la tête, envoie via `tasmota.cmd("ModBusSend …")`,
  arme **un** timer de timeout à **nom unique** (`"modbus_timeout"`) — fin des collisions
  de noms par `StartAddress`.
- `termineEnVol(ok)` : point de sortie unique (réception ou `surTimeout()`), retry borné à
  `MAX_TENTATIVES = 3`, puis abandon **journalisé** — jamais de perte muette.
- `armeTimer`/`desarmeTimer` basculent sur `add_cron` si `typeESP == "ESP32P4"` (le maître
  garage), sinon `set_timer`.

## 1.3 Appariement réponse↔requête (`modbusFonctions.be:524`)

Une trame RTU de **lecture** ne porte ni `StartAddress`, ni `Count`, ni `type`.
`apparieReponse()` les réinjecte depuis `enVol`, **mais seulement après** avoir vérifié la
correspondance `DeviceAddress` + `FunctionCode` (rejet strict, 2026-07-24). Elle écarte
aussi les trames marquées `Automatique` : les acquitter volerait sa réponse à la vraie
requête.

## 1.4 Le bit 0x80 — télémétrie spontanée

`decrypteMSG()` calcule `codeBase = FunctionCode & 0x7F` ; si le bit était posé, la trame
est marquée `Automatique = true` (`modbusFonctions.be:1256-1263`). La liste blanche des
codes fonction (`:1293`) teste `codeBase`, ce qui laisse passer `0x82` sans le confondre
avec un code invalide.

> ⚠️ **Point de protocole** ✅ : en ModBus standard, `FunctionCode | 0x80` signale une
> **réponse d'exception (erreur)**. Ici le bit est détourné pour dire « télémétrie
> spontanée ». Sans danger tant qu'on reste entre nos propres nœuds sur le dialecte
> maison (la carte 16 relais n'émet jamais 0x80), mais ambigu face à un équipement tiers.

## 1.5 Transports TCP et UDP

**Ce n'est pas du ModBus TCP standard** : pas d'en-tête MBAP, pas de `Transaction Id`.
La PDU RTU (CRC compris) est envoyée **préfixée d'un texte** `"ModbusTCP "` / `"ModbusUDP "`.
Choix assumé le 2026-07-24 (besoin d'interop tiers absent).

- **TCP** (`modbusFonctions.be:730`) — maître : un client par esclave dans
  `modbusFonctions.clients[id]` ; esclave : écrit sur `tcpFonctions.connexionAsync`
  (connexion acceptée venant du maître). C'est ce canal persistant qui porte le **push
  esclave→maître**. Port réel : **502** (`controleTCP.be:107` → `CONTROLE_TCP(502)`).
- **UDP** (`modbusFonctions.be:666`) — ports 2000 (UniCast) / 4000 (MultiCast). L'envoi
  réel est en **MultiCast avec IP en dur** (`192.168.4.1` côté maître) ; l'UniCast est
  commenté. Voir la partie 2 : la résolution d'IP par `discovery.json` y est cassée.

## 1.6 Carte 16 relais (`modBus_Conn16channels.be`)

**Protocole conforme à la doc constructeur** ✅ (`outils_docs/Electronique/Connecteur ModBus/`) :

- **Écriture 0x06** : `[id][06][canal 2o][ordre 1o][tempo 1o][CRC]`, ordres Open=0x01,
  Close=0x02, etc.
- **Relecture 0x03** : `sondeEtats()` (`:73`) demande les 16 registres en une trame.
- **Table d'inversion Open/Close centralisée** (`:21-45`) : « Open » = sortie **basse** ;
  avec des relais inversés (type 256) un registre lu à 0x0001 = relai **ON**. Le cavalier
  **M0** inverse toute la table (`sortieInversee()` en XOR).
- **Sondage périodique + chien de garde + réconciliation** (phase 4, active) : cron `*/30 s`,
  sondage de boot différé de 15 s, passage des états constatés à **« inconnu »** au-delà de
  3×T, écart commande/constaté **journalisé et non corrigé** (éviter la boucle de
  rétroaction).

## 1.7 ESP32 ↔ ESP32 (`modBus_TasmotaSlaveModBus.be`)

Tourne **sur le maître** et matérialise les devices des esclaves comme devices virtuels.

Ce qui reste à paramétrer, constaté dans le code :

1. ✅ **Le polling périodique des esclaves est DÉSACTIVÉ** : les crons `majInter` /
   `majAnalogiques` / `majCompteurs` / `majThermo` sont **tous commentés** (`:762-812`).
   Seul le boot émet une demande unique.
2. ✅ `0x11 ISALIVE_ESCLAVE` est réservé, en liste blanche, mais **jamais émis** (pas de
   heartbeat).
3. ✅ **Pas de compteur `seq`** : le complément anti-désordre du §9 n'existe pas.
4. ✅ Sauvegarde de `logActivation` sur un chemin de persist erroné (`:130-133`, triple
   `["TasmotaSlaveModBus"]`).

## 1.8 Push spontané esclave → maître — état réel

**Commencé et partiellement fonctionnel.** Chemin **événementiel** : sur changement d'état
d'un switch/interrupteur/bouton, `globalFonctions.be` bâtit une trame `0x02 | 0x80` et la
pousse (`globalFonctions.be:190, 232, 276, 371`) :

```berry
trameModBus["FunctionCode"] = 0x02 | 0x80   # marque « retour automatique »
if(drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON")
    modbusFonctions.envoiMsgModbusTCP(modbusFonctions.prepareTrame(trameModBus, "Reponse"), "Reponse")
end
```

Écarts par rapport au design §9 de `PROTOCOLE_MODBUS.md` :

- ✅ **TCP uniquement** — rien en UDP depuis `globalFonctions`.
- ✅ **Différentiel, pas instantané** — l'état d'un seul capteur, pas le snapshot.
- ✅ **Pas de `seq`** — aucune protection contre désordre/duplication.
- ✅ Températures/DHT/DS18B20 volontairement exclues (« varie trop souvent »).

### 💡 Jugement — quel protocole pour les réponses spontanées

Deux besoins distincts, deux transports :

1. **Garantie de convergence** → **UDP, instantané périodique + `seq`.** Connectionless,
   fire-and-forget assumé : un datagramme perdu est réparé par le suivant puisqu'il porte
   l'état entier (idempotent). Le `seq` neutralise le réordonnancement propre à UDP.
   Coût mesuré négligeable (~2 datagrammes / 30 s).
2. **Latence sur événement** → le push TCP actuel convient **comme simple optimisation**,
   jamais comme source de vérité (si le socket tombe, l'événement est perdu).

**MQTT** est techniquement le plus robuste (broker, QoS, *retained* = dernier état connu),
mais **déconseillé ici** : tout le framework vise une communication device-à-device
autonome sur le LAN. Passer la télémétrie par MQTT réintroduit un point de défaillance
unique (broker HS = garage aveugle) pour un gain nul à ce débit. À réserver en
**complément**, si ces états doivent aussi alimenter Node-RED/InfluxDB.

## 1.9 Configuration réelle des 3 modules garage

| Module | id | Serial | TCP | UDP | MQTT | timeout |
|---|---|---|---|---|---|---|
| `tasmota32p4-serveur-modbus` (**maître**) | 0 | ON | **ON** | OFF | OFF | 5000 |
| `tasmota32s3-capteurs-cuve-modbus` | 2 | ON | **ON** | OFF | OFF | 5000 |
| `tasmota32s3-rideau-garage-modbus` | 3 | ON | **OFF** | OFF | OFF | 5000 |

⚠️ Le **rideau a TCP OFF** : son push spontané (qui n'existe qu'en TCP) **ne part pas**.
Asymétrie à trancher.

---

# PARTIE 2 — Audit de `/json/discovery.json`

## 2.1 Le fichier et ses quatre voies d'écriture

Le fichier de référence est **`/json/discovery.json`** (graine versionnée :
`data/json/discovery.json`, actuellement `{}` — il est peuplé à l'exécution).

**Forme canonique** (celle que construisent 3 des 4 voies) :

```json
{
  "<MAC sans ':'>": {
      "config":  { "dn": …, "ip": …, "hn": … },     // MQTT discovery natif Tasmota
      "sensors": { … },                              // MQTT discovery natif Tasmota
      "lwt": "Online" | "Offline",
      "maitre" | "esclaveN" | "moduleXX": {
          "id", "nom", "IPAddress", "adresseMAC", "host", "topic", "typeReglageHeure",
          "typeConnection",
          "rangeExtender": { "activation", "id", "routagePort", "ipMaitre" },
          "ModBus": {
              "activation", "id",
              "Serial": { "activation", "timeoutReponse", "debit", "mode" },
              "TCP":    { "activation", "port": 502, "IPAddress" },
              "UDP":    { "activation", "IPAddress" },
              "MQTT":   { "activation" }
          }
      }
  }
}
```

| # | Voie d'écriture | Emplacement | Forme produite | Verdict |
|---|---|---|---|---|
| A | MQTT discovery natif (`config` / `sensors`) | `discoveryFonctions.be:300-355` | `{MAC: {config, sensors, lwt:"Online"}}` | ✅ canonique |
| B | `Wifi#Connected` — rôles et blocs ModBus/RangeExtender | `discoveryFonctions.be:88-211` | `{MAC: {maitre\|esclaveN: {...}}}` | ✅ canonique |
| C | Mise à jour `lwt` via topic LWT | `discoveryFonctions.be:396-428` | `{MAC: {lwt}}` | ✅ canonique |
| D | **UDP `ImAlive` reçu par le maître** | `udpFonctions.be:167-180` | **`{esclaveN: {...}}` à la racine** | ❌ **hors forme** |

## 2.2 Les lecteurs

| Lecteur | Emplacement | Profondeur supposée | Verdict |
|---|---|---|---|
| Routage NAPT RangeExtender | `rangeExtenderFonctions.be:47-64` | `[MAC][role]`, `[MAC]["lwt"]` | ✅ correct |
| Boutons RangeExtender | `rangeExtenderFonctions.be:252-267` | `[MAC][role]`, `[MAC]["lwt"]` | ✅ correct |
| Page web « Modules connectés » | `discoveryFonctions.be:490-530` | `[MAC]["config"]["dn"/"ip"/"hn"]` + rôles | ⚠️ suppose `config` présent |
| `resetClientsConnectes` (/300 s) | `udpFonctions.be:505-518` | `[racine]["lwt"]` | ⚠️ dépend de la forme |
| **Résolution d'IP ModBus UDP** | `modbusFonctions.be:677-704` | mauvais fichier + mauvaise profondeur | ❌ **cassé** |

## 2.3 Les trois défauts structurants

### ❌ Défaut 1 — mauvais nom de fichier (`modbusFonctions.be:677`)

```berry
var paramDiscovery = json.load(gestionFileFolder.readFile("/json/paramDiscovery.json")).find(…)
```

**Aucune voie n'écrit `paramDiscovery.json`** — tout le monde écrit `discovery.json`, et
`gestionFileFolder.readFile()` retourne **`false`** pour un fichier absent
(`gestionFileFolder.be:151-153`). La chaîne `json.load(false)` → `nil` → `.find(...)`
lève une exception, **dans le chemin d'envoi ModBus**, sans `try`.

Non déclenché aujourd'hui car `typeComm.UDP = OFF` sur les 3 modules — mais il le sera
**exactement le jour où l'UDP sera activé**, c'est-à-dire la recommandation de la partie 1.

### ❌ Défaut 2 — lecture une couche trop profonde + filtre sur sa propre MAC

`modbusFonctions.be:677` fait `.find(<sa propre MAC>, {})` **avant** de boucler. On obtient
déjà `{maitre: {...}}`. Ensuite (`:685-689`) `item` parcourt `"maitre"/"esclaveN"` et `cle`
parcourt `"id"/"nom"/"IPAddress"...` — **aucune** de ces clés ne peut matcher
`^(maitre|esclave[0-9]+)$`. `IP_ModBus` reste donc **toujours** à son défaut `192.168.4.2`.

Double erreur : (a) une couche de trop — comparer avec `rangeExtenderFonctions.be:47`, qui
ne pré-descend pas et matche à la bonne profondeur ; (b) **erreur d'intention** — filtrer
sur sa propre MAC empêche par construction de trouver l'IP d'un **autre** module, ce qui
est pourtant le but.

### ❌ Défaut 3 — la voie UDP `ImAlive` écrit une forme incompatible

L'esclave n'envoie que le sous-dictionnaire de son rôle (`udpFonctions.be:136-151` : `result`
= `{"esclave2": {...}}`). Le maître fait ensuite (`:173-176`) :

```berry
for item: tmp.keys()    device = item   end          # device = "esclave2", PAS la MAC
paramDiscovery.insert(device, tmp[device])           # racine keyée par le ROLE
```

Le même fichier finit donc avec **deux formes incompatibles**. Conséquences en cascade :
- les lecteurs `[MAC][role]` mal-interprètent ces entrées ;
- `resetClientsConnectes` (`udpFonctions.be:513`) écrit `lwt` **à l'intérieur du dict de la
  device** au lieu du niveau MAC — la santé devient illisible ;
- la page web plante sur `jsonDiscovery[item]['config']['dn']` (`:494`, sans `.find()`)
  pour toute entrée sans bloc `config` — l'exception est avalée par le `try` (`:478`), la
  page est donc silencieusement tronquée.

## 2.4 Paramètres présents / manquants pour le besoin ModBus

| Paramètre | Présent ? | Nécessaire à |
|---|---|---|
| `ModBus.id` (0 = maître) | ✅ `discoveryFonctions.be:147` | Identifier la cible d'une trame |
| `ModBus.activation` | ✅ `:146` | Savoir si le nœud parle ModBus |
| `IPAddress` (niveau rôle) | ✅ `:125` | Résolution d'IP (UniCast) |
| `ModBus.TCP.port` | ✅ `:162` (502, conforme à `controleTCP.be:107`) | Ouvrir le client TCP |
| `ModBus.TCP.IPAddress` | ✅ `:163` | Idem |
| `ModBus.Serial.debit/mode/timeoutReponse` | ✅ `:153-155` | Diagnostic de désaccord de débit |
| **`ModBus.UDP.port`** | ❌ **absent** (`:166-168` : activation + IPAddress seuls) | Envoi UniCast UDP (2000/4000 en dur) |
| **Horodatage de fraîcheur** (`derniereVue`) | ❌ absent | Juger la péremption autrement que par le reset global 300 s |
| **`lwt` par transport** | ❌ absent (un seul `lwt` par module) | Savoir si le canal ModBus TCP est tombé alors que le module est en ligne |
| **`seq`** (n° de séquence télémétrie) | ❌ absent | Rejeter un instantané périmé (§9) |

## 2.5 Tableau des éléments restant à paramétrer

Échelles — **Importance** : Critique / Élevée / Moyenne / Faible. **Priorité** : P1 (avant
d'activer l'UDP) / P2 (avant la mise en service complète) / P3 (confort, dette).
**Difficulté** : Triviale (1-2 lignes) / Faible (~10 lignes, 1 fichier) / Moyenne
(plusieurs fichiers ou changement de forme) / Élevée (conception).

| # | Élément à paramétrer / corriger | Emplacement | Importance | Priorité | Difficulté |
|---|---|---|---|---|---|
| 1 | Corriger le nom de fichier `paramDiscovery.json` → `discovery.json` | `modbusFonctions.be:677` | **Critique** | **P1** | Triviale |
| 2 | Supprimer le `.find(<sa MAC>)` et boucler sur **toutes** les MAC à la bonne profondeur | `modbusFonctions.be:677-704` | **Critique** | **P1** | Faible |
| 3 | Uniformiser la forme écrite par `ImAlive` en `{MAC: {role: …}}` | `udpFonctions.be:167-180` | **Critique** | **P1** | Moyenne |
| 4 | Protéger la lecture (fichier absent/vide → `{}` au lieu d'une exception) | `modbusFonctions.be:677` | **Élevée** | **P1** | Triviale |
| 5 | Ajouter `ModBus.UDP.port` (2000 UniCast / 4000 MultiCast) à la structure | `discoveryFonctions.be:166-168` | Élevée | P2 | Faible |
| 6 | Utiliser réellement `IP_ModBus` (UniCast) au lieu du MultiCast en dur `192.168.4.1` | `modbusFonctions.be:707-712` | Élevée | P2 | Faible |
| 7 | Ajouter un horodatage de fraîcheur `derniereVue` par entrée | `discoveryFonctions.be` + `udpFonctions.be:513` | Élevée | P2 | Faible |
| 8 | Durcir la page web : `.find("config", …)` au lieu de l'accès direct | `discoveryFonctions.be:494` | Moyenne | P2 | Triviale |
| 9 | Fiabiliser `resetClientsConnectes` (n'écrire `lwt` qu'au niveau MAC) | `udpFonctions.be:513` | Moyenne | P2 | Faible |
| 10 | Ajouter `lwt` / santé **par transport** (Serial / TCP / UDP) | `discoveryFonctions.be:143-175` | Moyenne | P3 | Moyenne |
| 11 | Ajouter le compteur `seq` (lié au design §9, partie 1) | `modbusFonctions.be` + `globalFonctions.be` | Élevée | P2 | Moyenne |
| 12 | Corriger la garde `&&` → `||` (ne protège rien aujourd'hui) | `modbusFonctions.be:673`, `:736` | Faible | P3 | Triviale |
| 13 | Mettre à jour le commentaire d'en-tête périmé (port TCP « 8888 » ≠ 502 réel) | `controleModbus.be:19-20` | Faible | P3 | Triviale |
| 14 | Implémenter ou retirer `typeComm.MQTT` (déclaré partout, jamais codé) | `controleModbus.be:16`, `discoveryFonctions.be:172-175` | Faible | P3 | Élevée (si implémenté) |

### Ordre d'attaque conseillé 💡

**Lot 1 (P1, avant toute activation UDP)** : items 1 → 4. Ils se tiennent : sans le 3,
corriger le 2 ne suffit pas (la table contient des entrées mal formées) ; sans le 4, la
moindre absence de fichier casse l'envoi ModBus. C'est un lot cohérent et petit, donc
commitable d'un bloc (règle « ne pas accumuler avant le premier commit »).

**Lot 2 (P2)** : items 5 → 9, puis 11 avec le passage du push en instantané.

⚠️ **Rappel de méthode** : aucun de ces correctifs ne doit être appliqué avant que le
chantier en cours n'ait franchi son verrou — `tasks/reprise-chantier-modbus-grenier.md`
impose de **flasher et observer** les 3 modules garage avant d'écrire du nouveau code,
sans quoi tout échec devient indécidable (règle 7 de `tasks/lessons.md`).

---

## Références

- `outils_docs/PROTOCOLE_MODBUS.md` — ModBus RTU/TCP, implémentation maison, §8 carte
  16 relais, §9 synchronisation maître/esclave.
- `tasks/reprise-chantier-modbus-grenier.md` — état du chantier, prochaine action.
- `tasks/lessons.md` — journal des erreurs et règles de méthode.
- `outils_docs/Electronique/Connecteur ModBus/` — docs constructeur de la carte 16 relais.
