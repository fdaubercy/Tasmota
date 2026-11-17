# Voie de communication MQTT entre maître et esclaves : analyse de faisabilité

Date : 2026-11-16. Statut : **analyse, rien n'est codé ni modifié**. Les questions ouvertes sont en §14.

Légende des sources : **[lu]** = lu dans le code ou le persist du dépôt ; **[déduit]** = raisonnement à partir de ce qui est lu ; **[estimé]** = ordre de grandeur de connaissance générale, à mesurer sur carte ; **[non vérifié]** = non regardé.

Périmètre : un maître (P4 du garage, maître de la cave, maître de l'écran des débits) qui commande des esclaves, lit leurs capteurs et est averti d'un changement d'état de bouton ou de capteur. Les esclaves sont en Wi-Fi classique ou derrière le Range Extender (NAPT) du maître. **ESP-NOW est exclu** (décision de l'utilisateur). Les voies comparées sont ModBus série, ModBus UDP et MQTT.

---

## 1. Verdict

- **Faisable**, avec un travail modeste côté Berry : un module de fonctions, un driver de contrôle, trois points de branchement dans le code ModBus existant, quelques clés de persist.
- **Une partie du chemin existe déjà** : la fiche de présentation des esclaves circule déjà par MQTT (`tasmota/discovery/<MAC>/<rôle>`), le maître republie déjà les push reçus (`tele/<topic>/MODBUSPUSH`), la cave lit déjà des topics Tasmota natifs, et la clé `drivers.ModBus.typeComm.MQTT` est déjà dans tous les persist (elle vaut `OFF` partout).
- **Le risque principal n'est pas le code, c'est le broker** : un seul broker (le Pi du bureau), et un `publish` lent bloque `loop()` de l'ESP32 jusqu'au chien de garde de 5 s. Une voie de commande qui dépend du broker doit donc rester **optionnelle, avec repli** sur ModBus série ou UDP.
- **Un esclave non ESP32 est possible** : un ESP8266 sous Tasmota sans Berry se pilote en MQTT natif sans rien installer dessus (§11).
- **Le coût processeur et RAM est faible** si la voie réutilise la connexion MQTT déjà ouverte (aucune socket de plus). Il devient élevé seulement dans deux cas : un broker embarqué sur le maître, ou des publications trop fréquentes (§9).

## 2. Vos deux conditions de départ : vérifiées

### 2.1 Boutons et interrupteurs détachés des relais : oui

`data/fs/configDevices.be` pose `SetOption73` (boutons) et `SetOption114` (interrupteurs et capteurs) dès qu'un bouton ou un switch est activé dans le persist **[lu]**. Sans détachement, Tasmota couplerait `SwitchN` à `PowerN` et n'émettrait pas `SwitchN#Action` : les règles Berry ne verraient rien.

Deux nuances :
- Le réglage est **global à la carte**, pas par bouton : tous les boutons d'une carte sont détachés ensemble **[lu]**.
- Seules les cartes qui chargent ce framework (`configDevices.be`) sont concernées. D'après la mémoire du projet, le **différentiel (ESP32 du bureau)** ne le charge pas, et les **ESP8266** n'ont pas de Berry : leurs boutons ne sont détachés que si vous posez vous-même `SetOption73` / `SetOption114` (§11).

Le lien bouton vers relais se fait ensuite par le bloc `relaisLie` du persist (`modules`, `ids`, `etatSiON`, `delaiSiON`, `type`), traité par Berry **[lu]**. C'est exactement ce qu'il faut : le bouton ne commande plus son relais localement, il émet un évènement que le maître décide d'exploiter.

### 2.2 Déclarer des éléments « virtuels » sur le maître : le mécanisme existe

Chaque relais, bouton, interrupteur, capteur, thermomètre, compteur et entrée analogique du persist porte déjà une clé **`virtuel`** **[lu]** :

| Valeur de `virtuel` | Sens | Où c'est lu |
|---|---|---|
| `"OFF"` | élément réel, branché sur une broche du module | `configDevices.be` (chaque famille) |
| `"I2C_ADS1115"`, `"I2C_MCP23017"`, `"I2C_TCA9554"` | élément porté par une puce I2C | `configDevices.be` |
| `"ModBus_Conn16channel…"`, `"ModBus_TasmotaSlaveModBus<N>"` | élément porté par un esclave ModBus | `configDevices.be`, `controleGeneral.be` (aiguillage des ordres) |

La forme est `<TYPE>_<module>` ; le code découpe sur `_` (`string.split(...)[0]` = type de liaison, `[1]` = module). Un élément virtuel n'a pas de broche, n'a pas de `SwitchN` dans les sensors et n'est pas compté parmi les devices réels **[lu]**.

## 3. État de l'existant (ce qui se branche où)

### 3.1 Les voies actuelles n'ont pas de couche de transport abstraite **[lu]**

L'aiguillage se fait par une chaîne `voie` (`"Serial"` ou `"UDP"`) à trois endroits de `data/fs/modbusFonctions.be` :
1. `voieDe` / `voieFiche` / `ipDe` : choisissent la voie d'après la fiche de `/json/discovery.json` (cache 60 s).
2. `envoiMsgModbus` : sur le maître, tout message passe par la file FIFO (`enfileMsg`, `pompeQueue`, `envoieTete`). Un seul message en vol, 3 tentatives, esclave déclaré « muet » après 2 abandons. **Pas de repli automatique** si la voie est coupée : le message est rejeté et journalisé.
3. `envoieTete` : Serial par `ModBusSend` natif ; UDP par `envoieTeteUDP` (`"ModbusUDP <tid> <hexa>"` en unicast).

Réception : `udpFonctions.be::lireUDP` (appelé toutes les 100 ms par `controleUDP.be`) reconnaît `ModbusPushUDP` et `ModbusUDP`, puis `modbusFonctions.lireMsgModbus("ModbusReceivedUDP", …)`. La règle `ModbusReceivedUDP#DeviceAddress==N` est prise par `modBus_TasmotaSlaveModBus.be::recupereReponseModBus`.

Push esclave vers maître : `modbusFonctions.be::pousseEtat` émet toujours en **UDP multicast**, appelé par `globalFonctions.be::changementEtatCapteur` (switch, interrupteurs, boutons, DS18B20), `surveilleRubans`, `debitsFonctions.be`, `ecranCaveFonctions.be`. Le maître filtre par `accepteSeq` (fenêtre de 16, détecte le redémarrage de l'esclave).

### 3.2 Ce qui parle déjà MQTT **[lu]**

| Élément | Rôle | Fichier |
|---|---|---|
| Fiche de présentation retenue | `tasmota/discovery/<MAC>/<rôle>` ; le maître s'abonne à `tasmota/discovery/+/#` et `tele/+/LWT` | `discoveryFonctions.be::changementEtatDemarrage`, `controleDiscovery.be` |
| Relais des push | le maître republie chaque `ModbusPushUDP` sur `tele/<topic>/MODBUSPUSH` = `{"ip","msg"}` (clé `drivers.ModBus.relaisPushMQTT`, observation seulement) | `modbusFonctions.be::relaiePushMQTT` |
| Cave : lecture d'esclave | abonnement à `tele/<x>/SENSOR`, `tele/<x>/STATE`, `stat/<x>/RESULT`, `stat/<x>/STATUS10` ; publication de `cmnd/<x>/STATE` à chaque `Mqtt#Connected` | `controleEcranCave.be` |
| Relais avec `publishMQTT.topic` | un relais peut publier son état sur un topic | `controleGeneral.be` |
| Transfert de fichiers | patron complet d'un récepteur MQTT (classe, `Mqtt#Connected`, instance hors module) | `fsMqtt.be` (295 lignes, solidifié) |
| Ordres en texte | `lireUDP` accepte déjà `cmnd/<topic>/Cmd args` et l'exécute par `tasmota.cmd` | `udpFonctions.be::lireUDP` |

Ce qui **n'existe pas** : l'abonnement du maître aux topics d'esclaves pour alimenter des éléments virtuels, et l'émission de `pousseEtat` en MQTT.

### 3.3 Capacités du firmware **[lu]** sauf mention

- Client Berry solidifié (`lib/libesp32/berry_tasmota/src/embedded/mqtt.be`) : `mqtt.subscribe(topic, fn)` avec jokers `+` et `#`, `unsubscribe`, `publish`, `connected()` ; re-souscription automatique sur la règle `Mqtt#Connected`.
- QoS : PubSubClient accepte 0 ou 1 en abonnement, **pas de QoS 2** (`lib/default/TasmotaPubSub/src/PubSubClient_311.cpp`). Une pile MQTT 5 est aussi présente dans le fork.
- Tailles : paquet MQTT 1200 octets par défaut, **2048 chez vous** pour les ESP32 ; `MESSZ` 2000 (`user_config_override.h`, noms de defines seulement).
- **Aucun broker n'est embarqué dans le firmware** (aucun `USE_MQTT_BROKER` trouvé ; la recherche globale a expiré, donc recherche partielle) **[non vérifié pour une extension `.tapp` tierce]**.

## 4. Deux architectures possibles

### Architecture A : MQTT natif Tasmota (cmnd / stat / tele)

Le maître parle le JSON natif de Tasmota :
- Commander : `cmnd/<topic esclave>/Power1 ON` (`mqtt.publish`).
- Lire un capteur : abonnement à `tele/+/SENSOR` (périodique, selon `TelePeriod`) ou `cmnd/<topic>/Status 10` à la demande.
- Être averti : règle sur l'esclave `on Switch1#State do Publish …` ou `ButtonTopic` / `SwitchTopic` ; côté Berry, `stat/<topic>/RESULT {"Button1":{"Action":…}}` existe déjà.
- Présence : `tele/<topic>/LWT` (Online / Offline retenu).

Avantages : aucun code sur l'esclave pour un ESP8266, vocabulaire standard, outils existants (sniffeur MQTT, Node-RED). Inconvénients : pas de file ni de `tid` ni de `seq`, donc pas d'accusé de réception ni de détection de doublon par construction ; le mappage vers les éléments virtuels est à écrire.

### Architecture B : trames ModBus transportées dans MQTT

On garde les trames ModBus (en hexadécimal) comme charge utile et on ajoute une voie `"MQTT"` à côté de `"Serial"` et `"UDP"` :
- Maître vers esclave : `liaison/<topic esclave>/cmd`.
- Esclave vers maître : `liaison/<topic esclave>/rep` (réponse, avec `tid`) et `liaison/<topic esclave>/push` (changement d'état, avec `seq`).
- Présence : `liaison/<topic esclave>/etat` (retenu, `pret` republié à chaque `Mqtt#Connected`, comme `fsMqtt`).
- Le maître s'abonne à **un seul joker** `liaison/+/rep` et `liaison/+/push`, pas à N abonnements.

Avantages : on garde **tout** ce qui est déjà éprouvé (file FIFO, `tid`, timeouts, 3 tentatives, muet, `accepteSeq`, mappage `idModBus` / `type`, chien de garde, relevé des esclaves). Les éléments virtuels existants (`ModBus_TasmotaSlaveModBusN`) n'ont **pas** besoin de changer de nom. Inconvénients : réservé aux esclaves Berry ; un ESP8266 ne peut pas parler ce dialecte.

Le tableau de comparaison :

| Critère | A : MQTT natif | B : trames ModBus sur MQTT |
|---|---|---|
| Code sur l'esclave Berry | aucun ou presque | un module (émission push, réception cmd) |
| Esclave ESP8266 (sans Berry) | oui | non |
| Accusé de réception, `tid`, retries | à écrire | déjà là (file FIFO) |
| Anti-doublon | à écrire | `accepteSeq` existant |
| Éléments virtuels | nouveau type `MQTT_<nom>` | inchangés (`ModBus_TasmotaSlaveModBusN`) |
| Charge à écrire | moyenne | modeste |
| Lisible par un outil tiers | oui | non (hexadécimal) |

**Recommandation [déduit] :** commencer par **A** pour les capteurs et les ordres simples, parce qu'elle couvre aussi les ESP8266 et ne demande presque aucun code ; puis ajouter **B** seulement pour les esclaves Berry où l'on veut la même robustesse que ModBus. Les deux peuvent coexister, car elles n'utilisent pas les mêmes topics.

## 5. Déclarer les éléments virtuels sur le maître

### 5.1 Nomenclature proposée

Pour l'architecture A, un nouveau type de liaison dans la clé `virtuel` :

```
"virtuel": "MQTT_<nomEsclave>"        exemples : "MQTT_Portail", "MQTT_PompePiscine"
```

Choix de `MQTT` (et non `Mqtt` ou `MQTTLiaison`) : `<TYPE>` reprend la casse de `I2C` et `ModBus`, le découpage sur `_` du code existant reste valable, et `<nomEsclave>` est la clé d'une table d'esclaves du persist (§7). Éviter un `_` dans `<nomEsclave>`, car le code découpe sur ce caractère.

Pour l'architecture B, on garde `"ModBus_TasmotaSlaveModBusN"` ; la voie MQTT est choisie par la fiche de l'esclave (`voieCommandes`), pas par le nom de l'élément.

### 5.2 Où le code lit `virtuel` et devra connaître le type `MQTT_`

| Fichier | Familles à brancher |
|---|---|
| `data/fs/configDevices.be` | relais (≈ lignes 45 à 112), capteurs, interrupteurs, boutons, analogiques, thermomètres, compteurs : chaque famille a une branche par type de liaison |
| `data/fs/controleGeneral.be` | aiguillage des ordres d'un relais virtuel (type, module, groupe extraits par `string.split` et une regex) |
| `data/fs/diversFonctions.be` | le prédicat « actif » : un virtuel est actif sans broche, déjà valable pour `MQTT_` |

Les numéros de ligne sont approximatifs ; au codage, repartir de `fichier::fonction`.

### 5.3 Ce qu'un élément virtuel MQTT porte dans le persist

Même bloc que les virtuels ModBus (`activation`, `nom`, `id`, `type`, `etat`, `relaisLie`), plus :
- `virtuel: "MQTT_<nomEsclave>"` ;
- `topicEtat` et `topicCommande` optionnels si l'esclave n'est pas un Tasmota standard ;
- pour un relais : `idRelais` sur l'esclave (le `1` de `Power1`).

## 6. Garde-fous anti-boucle (demande de l'utilisateur)

Une boucle naît ainsi : le maître commande, l'esclave change d'état, publie son état, le maître voit ce changement et re-commande. Il existe déjà un précédent sur ce parc : `MqttLog debug` sur la cuve (≈ 40 publications par requête) la faisait redémarrer toutes les 6 minutes **[lu, mémoire du projet]**.

| # | Garde-fou | Où | Effet |
|---|---|---|---|
| G1 | Champ `src` (émetteur) et `seq` dans chaque message de la voie B | émission et réception | ignorer un message dont `src` est le récepteur lui-même ou dont `seq` est déjà vu (`accepteSeq`) |
| G2 | Séparer ordre et état : ordres sur `cmnd/` ou `…/cmd`, retours sur `stat/` ou `…/push` | conception des topics | le maître ne réagit qu'aux retours, jamais à l'écho de son ordre |
| G3 | Comparer avant d'agir : ne republier que si l'état demandé diffère de l'état connu | maître et esclave | un ordre `ON` sur un relais déjà `ON` ne produit aucun message |
| G4 | Limiteur par élément : au plus N messages par seconde et par élément virtuel | émission | au-delà, quarantaine de l'élément, log `erreur`, réarmement par délai ou commande |
| G5 | Coupe-circuit global : total de messages sur une fenêtre glissante | émission | au-delà, la voie MQTT s'arrête seule ; ModBus et UDP continuent |
| G6 | Jamais de `retain` sur les ordres | publication | un ordre ancien n'est pas rejoué à la reconnexion |
| G7 | Sortie de log MQTT d'un esclave derrière le NAPT jamais au-dessus d'`erreur` | `ReglageLog profil normal` | évite la boucle de logs déjà constatée |
| G8 | Pas d'émission avant `mqtt.connected()` et `tasmota.is_network_up()` | émission | évite l'accumulation et le plantage mesuré à l'ouverture d'une socket avant la pile réseau |

Les seuils (N, taille de fenêtre, durée de quarantaine) iront dans le persist avec des valeurs prudentes par défaut. Chaque déclenchement d'un garde-fou est loggué en `erreur`, car c'est la seule chose qu'on doit retrouver une fois le debug éteint (charte des logs du dépôt).

## 7. Persist : ce qui existe, ce qu'il faut ajouter

### 7.1 Déjà présent **[lu]**

- `serveur.mqtt` : `activation`, `hote`, `port`, `client`, `utilisateur`, `mdp`, `topic`, `groupTopic1..3` (les mots de passe ne sont jamais recopiés dans ce document).
- `drivers.ModBus` : `typeComm` { `Serial`, `UDP`, **`MQTT`**, `TCP` }, `voieCommandes` (`"Serial"` ou `"UDP"`), `timeoutReponseUDP`, `relaisPushMQTT`.
- Le schéma `outils_docs/schemas/persist.schema.json` déclare déjà `typeComm.MQTT`, `relaisPushMQTT` et `voieCommandes` (énumération Serial | UDP à étendre).

### 7.2 À ajouter **[déduit, noms dans le style camelCase français du dépôt]**

| Clé | Valeur par défaut | Rôle |
|---|---|---|
| `drivers.ModBus.typeComm.MQTT` | `"ON"` là où la voie est voulue | existe, passer à `ON` |
| `drivers.ModBus.voieCommandes` | accepter `"MQTT"` | côté esclave, annoncée dans sa fiche |
| `drivers.ModBus.timeoutReponseMQTT` | 3000 ms | le NAPT et la veille Wi-Fi ajoutent de la latence |
| `drivers.liaisonMqtt` { `activation`, `log`, `base`, `qos`, `retenu` } | `base:"liaison"`, `qos:0`, `retenu:"OFF"` | bloc propre à la voie (ou `serveur.mqtt.liaison`) |
| `drivers.liaisonMqtt.garde` { `msgParSeconde`, `fenetreCoupeCircuit`, `seuilCoupeCircuit`, `quarantaine` } | à fixer à l'essai | garde-fous G4 et G5 |
| `drivers.liaisonMqtt.esclaves.<nom>` { `activation`, `topic`, `nom`, `famille` } | | nécessaire seulement pour l'architecture A ou un esclave hors ModBus ; en B, la table `TasmotaSlaveModBus` existante suffit |

Conséquences à ne pas oublier : régénérer le schéma (`berry/genere_schema_persist.py`), vérifier `outils_docs/schemas/modele_persist.json`, ajouter la cible `liaisonMqtt` dans `logFonctions.be` (`CIBLES` et `DESCRIPTIONS`). **Toute modification d'un `_persist.json` demande d'abord l'accord de l'utilisateur** (règle du dépôt).

## 8. Travail côté Berry

### 8.1 Modules à créer **[déduit]**

- `data/fs/mqttLiaisonFonctions.be` (module solidifié) : émission, réception, garde-fous, limiteur, coupe-circuit, état dans une **globale** `global._etatMqttLiaison` (comme `udpFonctions_etat`).
- `data/fs/controleMqttLiaison.be` (driver) : abonnements, règle `Mqtt#Connected`, commande `ReglageMqttLiaison`.
- Patron à copier : `fsMqtt.be` (classe récepteur, `mqtt.subscribe` avec callback `(topic, idx, payload, bytes)`, republication de l'état à chaque reconnexion).

### 8.2 Points de branchement dans l'existant (architecture B)

1. `modbusFonctions.be::voieFiche` et `::voieDe` : reconnaître `"MQTT"`.
2. `modbusFonctions.be::envoieTete` : branche `envoieTeteMQTT` à côté de `envoieTeteUDP` (même file, même `tid`, mêmes timeouts).
3. `modbusFonctions.be::pousseEtat` : émettre aussi en MQTT quand la fiche de l'esclave le demande.
4. Réception : callback qui appelle `lireMsgModbus("ModbusReceivedMQTT", …)` ; ajouter la règle `ModbusReceivedMQTT#DeviceAddress==N` et une branche dans `modBus_TasmotaSlaveModBus.be::recupereReponseModBus` (aujourd'hui trois branches `string.find(trigger, …)`).
5. **Repli** : décider si `envoiMsgModbus` bascule sur Serial ou UDP quand MQTT échoue (aujourd'hui « plus de repli silencieux »). Voir question Q3.

### 8.3 Règles du dépôt à respecter **[lu]**

- Solidification : ajouter les deux modules à `custom_berry_solidify` (liste dans `[berry_commun]` de `platformio_tasmota_cenv.ini` et dans les envs concernés), `import` du module dans toute fonction qui le cite, nouvelle globale ajoutée à `globs` de `solidify_all_python.be`. Chargement dans l'autoexec par `demarrage.compile([...])` puis `demarrage.charge(["controleMqttLiaison"], "serveur.xxx")`.
- Logs : `logFonctions.log(msg, LOG_LEVEL_*, "liaisonMqtt")`, préfixe `LIAISON_MQTT: …`, jamais d'`info` dans un callback fréquent, messages coûteux gardés par `logFonctions.actif`.
- Commande `ReglageMqttLiaison` : déclarée par `tasmota.add_cmd`, aide via `diversFonctions.traiteAide`, sauvegarde par `persist.save(true)`.
- Réception événementielle (callback), **pas de scrutation** `every_100ms` comme pour l'UDP.
- Ne jamais masquer un builtin (panne du 2026-11-13).
- Après codage : agents `verificateur-solidification`, `relecteur-berry`, `controleur-secrets`, banc dans `outils_docs/scripts_python/berry/`, firmware à recompiler par la page Build (:7700), validation sur carte.

### 8.4 Règles personnalisées Tasmota

Pour l'architecture A seulement, et seulement sur les esclaves **sans Berry** (ESP8266) : une règle `Rule1 on Switch1#State do Publish stat/<topic>/BTN %value% endon` suffit à émettre un changement de bouton. Sur un esclave Berry, aucune règle nouvelle n'est nécessaire : `changementEtatCapteur` sait déjà détecter le changement, il suffit d'y ajouter l'émission MQTT.

## 9. Charge processeur et RAM

| Poste | Estimation | Statut |
|---|---|---|
| Socket supplémentaire | **aucune** : la connexion MQTT existe déjà sur toutes les cartes | [lu] |
| Fuite de socket UDP (précédent) | ≈ 97 octets perdus par envoi avant correction (`udpFonctions.emet`, commit 8405be219, corrigé et vérifié sur carte) | [lu] |
| Session MQTT en clair | quelques Ko : client TCP + tampon de paquet (2048 o chez vous) | [estimé] |
| Module Berry (2 fichiers) | quelques Ko de tas ; sur S3 et P4 le tas Berry est en PSRAM | [estimé] |
| TLS sur ESP8266 (BearSSL) | +34,5 Ko de code, +7 Ko de RAM, +4,8 Ko à la poignée de main | [lu, `my_user_config.h`] |
| TLS sur ESP32 (mbedTLS) | 40 à 50 Ko environ | [estimé] ; non utilisé chez vous (MQTT en clair) |
| NAPT du maître | 3 Ko à 128 entrées, 12,5 Ko à 512 | [lu, `xdrv_58_range_extender.ino`] |
| Broker embarqué sur le maître | supplémentaire et non négligeable ; RAM interne du P4 déjà sous surveillance (fuite ≈ 0,6 Ko/min mesurée avant correction) | [déduit] |
| CPU, réception | **moindre** que l'UDP actuel : callback événementiel contre `lireUDP` appelé 20 fois par seconde (2 instances × 100 ms) | [lu] |
| CPU, émission | un envoi TCP avec accusé, plus coûteux qu'un datagramme UDP | [déduit] |
| Débit mesuré MQTT vers la cuve via NAPT | 14 à 18 Ko/s | [lu] |

**Réponse à votre question « moins cher que les autres modes sans fil ? »** :

| | ModBus UDP | MQTT (broker externe) | MQTT (broker sur le maître) |
|---|---|---|---|
| RAM esclave | une socket UDP + tampons | ≈ 0 de plus (connexion déjà là) | idem |
| RAM maître | une socket par voie | ≈ 0 de plus | **élevée** (sessions, abonnements, files) |
| CPU de réception | scrutation 20 fois/s | à l'évènement | à l'évènement, plus le broker |
| CPU d'émission | le plus bas | un peu plus haut (TCP) | idem |
| Risque de blocage de `loop()` | faible | **réel** si le broker est lent (mesuré jusqu'à 2,8 s sur une écriture via NAPT) | plus faible vers un esclave, mais le broker entre dans le maître |

Donc : en RAM et en CPU de réception, MQTT sur broker externe coûte **moins** que l'UDP maison. En CPU d'émission et en latence, il coûte un peu plus. Ce qui coûte vraiment cher n'est pas le protocole mais le **blocage** quand le broker traîne.

## 10. Avantages, inconvénients, éléments de réussite

### 10.1 Avantages

- Les esclaves sont déjà connectés au broker : pas de socket supplémentaire.
- Plus de résolution d'adresse IP : on adresse un topic. La table `/json/discovery.json` et ses défauts de résolution d'IP en UDP disparaissent pour cette voie.
- La présence arrive gratuitement (LWT Online / Offline retenu).
- Diagnostic facile : le sniffeur MQTT (:7100) et le journal montrent tout le trafic.
- Fonctionne à travers le NAPT, ce qui n'est pas le cas du multicast (le multicast des push n'atteint jamais le PC ni le broker de l'extérieur).
- Couvre aussi des esclaves sans Berry (architecture A).

### 10.2 Inconvénients

- **Point de défaillance unique** : un seul broker (le Pi du bureau). S'il tombe, la voie s'arrête (ANALYSE_BERRY_MODBUS_DISCOVERY.md §1.8 le déconseillait déjà pour la télémétrie seule).
- Blocage de `loop()` par une opération MQTT lente : chien de garde de 5 s que l'utilisateur interdit de modifier (`USE_ESP32_WDT`).
- Latence et pertes derrière le NAPT : le P4 en `Sleep 50` perdait 27 à 35 % des paquets (corrigé par `SetOption127 1`, perdu par un `erase_upload`).
- QoS 0 par défaut : un message peut se perdre sans retour. QoS 1 existe, pas QoS 2.
- Ordre des messages garanti sur une connexion, pas entre deux topics.
- Les esclaves dépendent du maître pour MQTT, syslog et OTA (le NAPT passe par le P4).
- Le P4 a son Wi-Fi sur un coprocesseur C6 bloqué en esp-hosted 2.6.6 (non mis à jour).

### 10.3 Éléments de réussite

1. **Voie optionnelle, jamais seule** : ModBus série ou UDP reste le chemin de secours.
2. Repli automatique à décider (Q3), avec bascule documentée.
3. Garde-fous G1 à G8 (§6) livrés **avec** la voie, pas après.
4. Pas de `retain` sur les ordres ; `retain` réservé aux états et à la présence.
5. Accusé applicatif pour les ordres critiques : le maître republie tant qu'il n'a pas vu le retour attendu.
6. Sortie de log MQTT des esclaves limitée à `erreur`.
7. Surveillance du broker : alerte si les LWT ne reviennent pas, et `MqttRetry` / `MqttTimeout` réglés pour qu'un broker éteint ne bloque pas longtemps.
8. Mesure du tas sur carte avant de valider (une rafale de messages retenus a déjà fait tomber le tas à 24-32 Ko sur un ESP32 sans PSRAM, leçon du 2026-11-02).
9. Option de secours matérielle : un second broker (ou un broker sur le NAS) à étudier si la voie devient critique.

### 10.4 Options de broker

| Option | RAM / CPU | Fiabilité | Remarque |
|---|---|---|---|
| Mosquitto sur le Pi du bureau (existant) | nul pour les ESP | un seul Pi | déjà utilisé, sniffeur compatible |
| Mosquitto sur NAS ou PC | nul pour les ESP | dépend de la machine | le NAS est éteint, le PC n'est pas toujours allumé |
| Broker Berry (`.tapp`) sur le maître | RAM interne du P4 | pas de dépendance au Pi | **[non vérifié]** : existence et maturité à confirmer en amont ; à écarter tant que la fuite de RAM interne n'est pas close |
| Pas de broker (UDP actuel) | le plus bas | pas de point unique | c'est l'alternative, pas une option MQTT |

## 11. Esclave qui n'est pas un ESP32

| Cas | Faisable | Comment | Limites |
|---|---|---|---|
| ESP8266 / ESP8285 sous Tasmota (sans Berry) | **oui, architecture A** | `cmnd/<topic>/Power1`, `stat/<topic>/RESULT`, `tele/<topic>/SENSOR`, règles + `Publish` pour les évènements, `SetOption73` / `SetOption114` posés à la main pour détacher boutons et switchs | pas de voie B, pas de garde-fous Berry ; garde-fous côté maître seulement |
| ESP8266 comme esclave du Range Extender | oui | exige `PIO_FRAMEWORK_ARDUINO_LWIP2_HIGHER_BANDWIDTH` (côté maître ESP32 uniquement ; l'esclave est un simple client Wi-Fi) | ESP8266 déconseillé comme maître |
| Raspberry Pi Pico W, Arduino, autre MCU | oui, **à la main** | n'importe quelle bibliothèque MQTT 3.1.1 ; respecter la convention de topics choisie | aucune présentation `ImAlive` ni discovery : à déclarer à la main dans le persist du maître |
| Shelly, Zigbee2MQTT, passerelle Zigbee | oui | ils parlent déjà MQTT avec leurs propres topics | topics à décrire dans la table d'esclaves ; format JSON propre à chaque produit |
| Derrière le NAPT du maître | oui vers un broker externe | le NAPT traduit les connexions sortantes (c'est déjà le cas pour la cuve) | un service hébergé **sur** le maître n'est pas joignable sans routage dédié |

La charge RAM d'un ESP8266 reste modeste en MQTT clair (environ 25 à 40 Ko libres sous Tasmota **[estimé]**). TLS est à éviter sur ESP8266.

## 12. Tableaux par puce

### 12.1 Capacités

| Puce | RAM | Berry | Rôle possible | Voie A | Voie B | Remarque |
|---|---|---|---|---|---|---|
| ESP32-P4 | 768 Ko + PSRAM | oui | maître ou esclave | oui | oui | Wi-Fi par coprocesseur C6 ; veille modem : `SetOption127 1` |
| ESP32-S3 (N16R8) | 512 Ko + 8 Mo PSRAM | oui | maître ou esclave | oui | oui | tas Berry en PSRAM |
| ESP32 classique (sans PSRAM) | 520 Ko | oui | **esclave de préférence** | oui | oui, avec réserve | tas Berry 18 à 29 Ko libres mesurés sur l'ancienne cave : mesurer avant |
| ESP32-C3 / C6 | ≈ 400 Ko | à confirmer par env | esclave | oui | à confirmer | pas dans le parc actuel |
| ESP8266 / 8285 (1 Mo) | ≈ 80 Ko dont 25-40 libres | **non** | esclave | **oui** | non | MQTT natif seulement |

### 12.2 Cartes du parc (état du dépôt)

| Carte (env) | Puce | Rôle actuel | Candidate MQTT |
|---|---|---|---|
| `tasmota32p4-garage-serveur-modbus` | P4 | maître garage, NAPT | maître |
| `tasmota32s3-garage-capteurs-cuve-modbus` | S3 | esclave id 2 (voie UDP) | esclave A et B |
| `tasmota32s3-garage-rideau-garage-modbus` | S3 | esclave id 3 | esclave A et B |
| `tasmota32s3-garage-portail-jardin-modbus` | S3 | esclave id 4 | esclave A et B |
| `tasmota32s3-cave-serveur-rly` | S3 | maître cave | maître |
| `tasmota32s3-cave-ecran` | S3 | esclave id 1, lit déjà `tele/` | esclave A (déjà en partie) |
| `tasmota32s3-bureau-serveur-debits-pac` | S3 | esclave id 1 derrière l'écran | esclave A et B |
| `tasmota32s3-bureau-ecran-debits-pac` | S3 | maître, Range Extender | maître |
| `tasmota32s3-rdc-grenier`, `…-etage2-grenier` | S3 | en sommeil | à voir si réactivés |
| `tasmota32-cave-serveur-rly` | ESP32 | remplacée, gardée | esclave possible, tas à mesurer |
| `tasmota32-bureau-interrupteur-energie` | ESP32 | différentiel, sans framework Berry du dépôt | architecture A seulement |
| `tasmota32-jardin-projecteur-led` | ESP32 | actif | à étudier |
| `tasmota-jardin-pompe-piscine`, `tasmota-cave-lumiere-porte`, `tasmota-rdc-tv-salon` | ESP8266 | en service | **architecture A, MQTT natif** |

### 12.3 Voies comparées

| Critère | ModBus série (RS485) | ModBus UDP | MQTT, architecture A | MQTT, architecture B |
|---|---|---|---|---|
| Fil à tirer | oui | non | non | non |
| Traverse le NAPT | n/a | oui en unicast, **non en multicast** | oui | oui |
| Dépendance | bus RS485 | Wi-Fi | **broker + Wi-Fi** | **broker + Wi-Fi** |
| Accusé, retries | oui | oui | non (à écrire) | oui |
| Anti-doublon | non utile | `accepteSeq` | à écrire | `accepteSeq` |
| Esclave ESP8266 | non | non | **oui** | non |
| CPU de réception | faible | scrutation 20/s | évènement | évènement |
| Visible dans un outil standard | sniffeur ModBus | sniffeur ModBus | **sniffeur MQTT, Node-RED** | sniffeur MQTT (hexa) |
| Statut | éprouvé | validé le 2026-10-17 | à construire | à construire |

## 13. Plan de réalisation proposé (à valider)

**À n'engager que si la décision de mise en place est prise** (questions §14). Si oui, ce plan est à recopier dans `tasks/plans/voie-mqtt.md` au format `_FORMAT.md` (en-tête `objectif:`, `famille:`, `liens:`), avec une case cochée seulement après vérification et `— preuve : …`.

Règles transversales à tout le plan :
- Jamais de compilation hors de la page Build (:7700), jamais pendant un build en cours.
- Accord de l'utilisateur avant toute modification d'un `_persist.json` ou de `user_config_override.h`.
- Avant chaque commit : `controleur-secrets`, puis `verificateur-solidification` et `relecteur-berry` pour les `.be` de `data/`.
- Sur un esclave derrière le NAPT : sortie de log MQTT jamais au-dessus d'`erreur`, pendant tous les essais.

### A1. Mesures préalables, sans écrire de code
Objectif : lever les deux inconnues qui décident de tout (latence derrière le NAPT, tenue d'un joker).
- [ ] Mesurer l'aller-retour `cmnd/<topic>/Status 10` puis réponse sur la cuve (via le NAPT du P4) : 20 essais, médiane et maximum. Critère : maximum inférieur à 1 s, sinon voie B déconseillée pour les ordres.
- [ ] Mesurer le tas interne libre du P4 et de la cuve avant et après 1 h d'abonnement à `tele/+/SENSOR` (même méthode que la fuite de RAM). Critère : pente nulle.
- [ ] Mesurer le temps de blocage de `loop()` quand le broker est coupé (arrêt volontaire de Mosquitto 2 minutes, un esclave observé). Critère : aucun redémarrage de la carte.
- [ ] Relever dans le firmware (`xdrv_02_9_mqtt.ino`) les valeurs par défaut de `MqttRetry`, `MqttTimeout` et le comportement de `SwitchTopic` / `ButtonTopic`.
- [ ] Vérifier carte par carte que `SetOption73` et `SetOption114` valent bien `ON` (`Status`), pour les cartes du premier lot.

### A2. Décisions de conception figées
- [ ] Réponses aux questions §14 inscrites dans ce document.
- [ ] Table des topics validée (A : natifs ; B : `liaison/<topic>/{cmd,rep,push,etat}`), avec la règle « pas de `retain` sur les ordres ».
- [ ] Nom du type virtuel arrêté (`MQTT_<nom>`) et table d'esclaves du persist décrite.
- [ ] Seuils par défaut des garde-fous G4 et G5 fixés d'après les mesures de A1.

### A3. Squelette du module et garde-fous (banc d'abord, aucune carte)
- [ ] Écrire le banc `outils_docs/scripts_python/berry/banc_mqtt_liaison.{py,be}` avec un faux `mqtt` (publish / subscribe simulés) et des cas de boucle : écho d'un ordre, deux maîtres, rafale, doublon de `seq`.
- [ ] Créer `data/fs/mqttLiaisonFonctions.be` : état dans une globale, limiteur par élément (G4), coupe-circuit global (G5), comparaison avant d'agir (G3), `src` / `seq` (G1). Aucun `import` ni instanciation au niveau fichier.
- [ ] Ajouter la cible `liaisonMqtt` à `logFonctions.be` (`CIBLES`, `DESCRIPTIONS`).
- [ ] Banc vert, **avec mutants** : chaque garde-fou retiré fait rougir au moins un cas (preuve que le banc voit la boucle).
- [ ] `verificateur-solidification` et `relecteur-berry` sans bloquant.

### A4. Driver, commande et persist
- [ ] Créer `data/fs/controleMqttLiaison.be` : abonnements en un joker, règle `Mqtt#Connected`, attente de `mqtt.connected()` et `tasmota.is_network_up()` avant toute émission (G8).
- [ ] Commande `ReglageMqttLiaison` (aide, `traiteAide`, `persist.save(true)`).
- [ ] Ajouter les clés de §7.2 au modèle (`modele_persist.json`), régénérer `persist.schema.json` par `berry/genere_schema_persist.py`.
- [ ] Ajouter les deux modules à `custom_berry_solidify` (liste dans `[berry_commun]` de `platformio_tasmota_cenv.ini`, puis envs concernés) ; mettre à jour `banc_demarrage.py` (`--enregistre` seulement sans autre session en cours).
- [ ] Bloc `drivers.liaisonMqtt` ajouté **après accord** dans le persist du maître et de **un seul** esclave pilote.

### A5. Éléments virtuels `MQTT_<nom>` (lecture seule)
- [ ] Brancher le type `MQTT_` dans `configDevices.be` famille par famille (capteurs, thermomètres, compteurs, analogiques) ; les relais et boutons viennent en A6.
- [ ] Alimenter ces éléments depuis `tele/+/SENSOR` et `stat/+/RESULT`.
- [ ] Banc : un JSON `SENSOR` simulé met à jour l'élément virtuel ; un JSON mal formé est rejeté et loggué en `erreur`.
- [ ] Essai sur carte : une mesure de la cuve visible sur le maître pendant 1 h, tas stable (critère de A1).

### A6. Commande, boutons et interrupteurs (architecture A)
- [ ] Brancher `MQTT_` dans `controleGeneral.be` (aiguillage des ordres d'un relais virtuel) et dans `configDevices.be` (relais, boutons, interrupteurs).
- [ ] Ordre = `mqtt.publish("cmnd/<topic>/Power<n>", …)` sans retain, avec accusé applicatif (le maître republie tant que le `stat/` attendu n'est pas vu, N fois au plus).
- [ ] Évènement bouton ou interrupteur de l'esclave : lecture de `stat/<topic>/RESULT` (`Button<n>`, `Switch<n>`) côté maître, puis action `relaisLie` du maître.
- [ ] Banc : un ordre produit **un** message ; l'écho du `stat/` ne produit **aucun** message (preuve anti-boucle) ; quarantaine déclenchée par une rafale simulée.
- [ ] Essai sur carte avec un relais non critique (un éclairage, pas le portail ni le rideau), 100 cycles, zéro boucle, zéro redémarrage.

### A7. Coupe-circuit, alerte broker et repli
- [ ] Alerte sur l'accueil du maître et ligne de log `erreur` quand le broker est injoignable plus de N minutes.
- [ ] Repli selon la décision Q3 : soit aucun (la voie est déclarée indisponible et l'élément passe en état inconnu), soit bascule sur Serial / UDP.
- [ ] Banc : le broker disparaît en plein ordre, l'élément n'est pas laissé dans un état faux.
- [ ] Essai réel : couper Mosquitto 5 minutes, vérifier qu'aucune carte ne redémarre et que ModBus continue.

### A8. Architecture B : ABANDONNÉE (décision Q1 du 2026-11-16, architecture A seule)
Conservée pour mémoire, à ne rouvrir que sur demande de l'utilisateur.
- [ ] `voieFiche` / `voieDe` : reconnaître `"MQTT"`.
- [ ] `envoieTeteMQTT` à côté de `envoieTeteUDP` (même file, même `tid`, `timeoutReponseMQTT`).
- [ ] `pousseEtat` en MQTT et réception `ModbusReceivedMQTT` avec la règle et la branche de `recupereReponseModBus`.
- [ ] Bancs ModBus existants (`banc_test_modbus.py`) toujours verts, plus les cas MQTT.
- [ ] Essai sur la cuve : une grille de 7 tests comme `AUDIT_MODBUS_2026-09-29.md` §6, en voie MQTT.

### A9. Esclaves sans Berry (ESP8266), si Q5 les retient
- [ ] Fiche de réglage à poser sur la carte : `SetOption73 1`, `SetOption114 1`, `Rule` de `Publish`, `ButtonTopic` / `SwitchTopic` selon le cas.
- [ ] Déclaration de l'esclave dans la table du maître et des éléments `MQTT_<nom>`.
- [ ] Essai sur la pompe de piscine (hors période de risque), puis relevé du tas de l'ESP8266.

### A10. Clôture
- [ ] Mise à jour de `PROTOCOLE_MODBUS.md` (nouvelle voie, topics, garde-fous), de `outils_docs/README.md`, de `CARTE_MODULES_BERRY.md` (`carte_modules_berry.py`) et du `CLAUDE.md` du dépôt (carte des documents).
- [ ] Contrôle `verifie_references_docs.py` à 0 défaut.
- [ ] Firmware recompilé par la page Build puis validé sur carte (journal `/cs`), jamais seulement par le banc PC (leçon du 2026-10-31).
- [ ] Leçons consignées dans `tasks/lessons.md`.

Ordre et dépendances : A1 puis A2 sont bloquants ; A3 à A7 s'enchaînent ; A8 et A9 sont indépendants l'un de l'autre et facultatifs ; A10 clôt.

## 14. Zones floues et décisions à prendre

Réponses de l'utilisateur du 2026-11-16 :

- Q1. Architecture : **A seule** (MQTT natif Tasmota). Conséquence : **l'étape A8 (architecture B) est abandonnée**, la file ModBus n'est pas modifiée, et les éléments virtuels portent le type `MQTT_<nom>`.
- Q2. Rôle de MQTT : voie parmi d'autres, jamais seule (implicite dans la réponse Q3).
- Q3. Repli : **automatique sur Serial ou UDP** quand MQTT échoue. Conséquence : l'étape A7 doit livrer ce repli. Il suppose que l'élément ait une seconde voie déclarée ; un esclave ESP8266 n'en a pas (il reste en MQTT seul, état « inconnu » si le broker tombe).
- Q4. Broker : **le Pi actuel seul**, sans second broker. Le point de défaillance unique est couvert par le repli (Q3) et par le coupe-circuit G5.
- Q5. Premiers essais : **cuve, un éclairage (relais non critique), pompe de piscine (ESP8266), portail de jardin**. Ordre conseillé : cuve (lecture), éclairage (commande), pompe de piscine (sans Berry), portail en dernier (le plus sensible).
- Q6. Nom du type virtuel : non tranché par l'utilisateur ; **`MQTT_<nom>` retenu par défaut**, à corriger si besoin avant A2.

Réponses du 2026-11-17 :
- L'éclairage et la pompe de piscine **n'ont pas de fiche ModBus** : pas de repli pour eux. Seuls la cuve et le portail (esclaves ModBus) en bénéficient.
- État d'un élément sans repli quand le broker est HS : l'utilisateur ne sait pas. **Défaut proposé, à confirmer** : état « inconnu » (dernière valeur gardée mais marquée périmée), aucun ordre envoyé, une seule alerte `erreur`, et à la reconnexion relecture de l'état réel avant toute action.

Conséquence : la pompe et l'éclairage sont commandés par MQTT **seul** ; s'ils pilotent quelque chose d'important, leur bouton physique local reste leur secours. À garder en tête pour le choix de l'éclairage d'essai.

## 15. Ce qui n'a pas été vérifié

- Aucun test sur carte ; aucune mesure de latence MQTT de bout en bout à travers le NAPT.
- Firmware C++ : limites de `mqtt.subscribe`, nombre maximal d'abonnements, comportement des callbacks sous charge.
- Valeurs par défaut exactes de `MqttRetry` et `MqttTimeout`, comportement de `SwitchTopic` / `ButtonTopic` dans ce fork.
- Existence d'un broker `.tapp` tiers.
- Disponibilité de la pile MQTT 5 dans les envs réels (présente dans les sources, utilisation non vérifiée).
- Le Range Extender sur P4 (dépend de l'AP géré par le C6).
- `data/sd` et les plans de `tasks/plans/` n'ont pas été relus pour cette analyse.
- Le détachement des boutons n'a été vérifié que dans `configDevices.be` ; l'état réel de chaque carte en ligne n'a pas été relevé.
