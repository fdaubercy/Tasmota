---
chantier: voie-mqtt
titre: Voie de communication MQTT maître/esclaves (architecture A, MQTT natif Tasmota)
statut: actif
cree: 2026-11-16
maj: 2026-11-17
objectif: Commander des esclaves, lire leurs capteurs et être averti de leurs changements d'état par MQTT, à côté de ModBus série et UDP, avec garde-fous anti-boucle et repli
famille: modbus-reseau
liens: rgx-ethernet-uplink, alerte-firmware-c6
---
# Voie MQTT maître/esclaves (architecture A)

## Contexte
Analyse complète : `outils_docs/ANALYSE_VOIE_MQTT_2026-11-16.md` (le plan y figure aussi au §13 ; ce fichier est la copie suivie).

Décisions de l'utilisateur du 2026-11-16 :
- Architecture **A seule** (cmnd / stat / tele natifs). L'étape A8 (trames ModBus dans MQTT) est **abandonnée** : la numérotation saute volontairement de A7 à A9 pour rester alignée sur le rapport.
- Repli **automatique** sur Serial ou UDP quand le broker est injoignable.
- Broker : le **Pi actuel seul**.
- Premiers essais : cuve, projecteur LED du jardin (`tasmota32-jardin-projecteur-led`, ESP32, relais non critique), pompe de piscine (ESP8266), portail de jardin (en dernier).
- Type virtuel : `MQTT_<nom>` par défaut (non tranché par l'utilisateur).

Règles transversales :
- Jamais de compilation hors de la page Build (:7700), jamais pendant un build en cours.
- Accord de l'utilisateur avant toute modification d'un `_persist.json` ou de `user_config_override.h`.
- Avant chaque commit : `controleur-secrets`, puis `verificateur-solidification` et `relecteur-berry` pour les `.be` de `data/`.
- Sur un esclave derrière le NAPT : sortie de log MQTT jamais au-dessus d'`erreur`, pendant tous les essais.
- Garde-fous G1 à G8 du rapport (§6) livrés avec la voie, pas après.

Réponses du 2026-11-17 : l'éclairage et la pompe de piscine n'ont **pas** de fiche ModBus, donc **pas de repli** pour eux ; seuls la cuve et le portail (esclaves ModBus) en bénéficient. Pour l'état d'un élément sans repli quand le broker est HS, l'utilisateur ne sait pas : défaut proposé en A2, à confirmer.

## A1 — Mesures préalables, sans écrire de code
- [ ] Mesurer l'aller-retour `cmnd/<topic>/Status 10` puis réponse sur la cuve (via le NAPT du P4) : 20 essais, médiane et maximum. Critère : maximum inférieur à 1 s. **Pas fait** : la cuve et le P4 sont hors ligne le 2026-11-17 (`tele/jardin/cuve/LWT` et `tele/garage/LWT` retenus à Offline). Mesures faites à la place, SANS NAPT (Wi-Fi direct) : projecteur LED 20/20 reçus, min 122 ms, médiane 198 ms, **max 1567 ms** (3 réponses au-dessus de 1 s : 1004, 1331, 1567 ms) ; pompe de piscine 18/20 reçus, médiane 105 ms, max 836 ms, 2 pertes. Conséquence : même sans NAPT le critère de 1 s n'est pas tenu sur l'ESP32 ; prévoir des timeouts d'accusé d'au moins 3 s et un nouvel essai, jamais compter sur une réponse immédiate
- [ ] Mesurer le tas interne libre du P4 et de la cuve avant et après 1 h d'abonnement à `tele/+/SENSOR`. Critère : pente nulle. **P4 et cuve hors ligne** : mesure faite à la place sur le projecteur LED (ESP32 sans PSRAM, la cible de l'essai A6) : `Status 4` toutes les 60 s pendant 1 h, lancée le 2026-11-17 ; départ 103 Ko libres puis 102 Ko à 1 minute. CSV dans `%LOCALAPPDATA%\outils_tasmota\mesures_mqtt\tas_jardin_projecteur_led_1794889009.csv`. Résultat final à relever à la fin de l'heure. Le tas du P4 et de la cuve reste à mesurer
- [ ] Mesurer le blocage de `loop()` quand le broker est coupé 2 minutes (un esclave observé). Critère : aucun redémarrage
- [x] Relever les valeurs par défaut de `MqttRetry` et `MqttTimeout` — preuve : `MQTT_RETRY_SECS` = 10 s (tasmota.h), délai multiplié jusqu'à 120 fois (`xdrv_02_9_mqtt.ino`, `retry_counter_multiplier`), `MQTT_WIFI_CLIENT_TIMEOUT` = 200 ms et `MQTT_SOCKET_TIMEOUT` = 4 s (tasmota_globals.h), aucun des trois redéfini dans `user_config_override.h`. Écart à expliquer : les 4,5 s de blocage mesurés en octobre dépassent ces 200 ms ; à recouper avec la mesure de blocage ci-dessous
- [ ] Relever le comportement de `SwitchTopic` / `ButtonTopic` dans `xdrv_02_9_mqtt.ino` (pas encore lu)
- [ ] Outil de mesure prêt : `outils_docs/scripts_python/outils_pc/mesures_mqtt_a1.py` (sous-commandes `rtt`, `tas`, `so`, `veille`, lecture seule, autotest `--autotest` vert le 2026-11-17 ; reste à lancer sur carte avec l'accord de l'utilisateur)
- [ ] Vérifier sur les cartes du premier lot que `SetOption73` et `SetOption114` valent `ON` (`Status`). **Mesuré le 2026-11-17 : NON** sur le projecteur LED (`SetOption73` OFF, `SetOption114` OFF) ni sur la pompe de piscine (OFF, OFF). Cuve non vérifiable (hors ligne). Les boutons et interrupteurs de ces deux cartes ne sont donc pas détachés ; le projecteur n'a probablement aucun bouton ou switch activé dans son persist, la pompe (ESP8266) n'a pas le framework Berry. À corriger à l'étape A6 (projecteur : ses éléments actifs passent par `configDevices.be`) et A9 (pompe : `SetOption73 1` et `SetOption114 1` à poser à la main). Mesure `MqttRetry` = 10 s, `MqttTimeout` = 4 (soit 400 ms) sur les deux cartes
- [x] Vérifier si l'éclairage et la pompe de piscine ont une fiche ModBus (conditionne le repli) — preuve : réponse de l'utilisateur du 2026-11-17, ni l'un ni l'autre n'en a ; ils n'auront donc pas de repli

## A2 — Décisions de conception figées
- [x] Réponses aux questions du rapport inscrites dans le rapport — preuve : outils_docs/ANALYSE_VOIE_MQTT_2026-11-16.md §14
- [ ] Table des topics validée (natifs `cmnd/stat/tele`, aucun `retain` sur les ordres)
- [ ] Nom du type virtuel confirmé (`MQTT_<nom>`) et table d'esclaves du persist décrite
- [ ] Seuils par défaut de G4 (limiteur par élément) et G5 (coupe-circuit) fixés d'après A1
- [ ] État affiché par un élément virtuel sans seconde voie quand le broker est HS : l'utilisateur ne sait pas (2026-11-17). Défaut proposé, à confirmer : état « inconnu » (dernière valeur gardée mais marquée périmée), aucun ordre envoyé, alerte `erreur` une seule fois, retour automatique à la reconnexion avec relecture de l'état réel avant toute action

## A3 — Module et garde-fous (banc d'abord, aucune carte)
- [x] Banc `outils_docs/scripts_python/berry/banc_mqtt_liaison.{py,be}` avec temps simulé et cas de boucle : écho d'un ordre, rafale, rafale sur tous les éléments, doublon, ordres sans accusé, maître fautif — preuve : `python outils_docs/scripts_python/berry/banc_mqtt_liaison.py` code 0, 41 cas OK le 2026-11-17 (le module est pur : pas de faux `mqtt`, le driver A4 le branchera)
- [x] `data/fs/mqttLiaisonFonctions.be` : état en globale, limiteur G4, coupe-circuit G5, comparaison avant d'agir G3, accusé et renvois bornés, arguments invalides refusés, temps comparé par différence (dépassement 32 bits). G1 (`src` / `seq`) n'est plus utile : il visait l'architecture B abandonnée ; l'anti-écho de l'architecture A est l'accusé (retour attendu = pas un évènement) — preuve : `verifie_berry.py` 0 erreur 0 avertissement ; maître fautif : 10 ordres sur 200 tentatives
- [x] Cible de log `liaisonMqtt` ajoutée à `logFonctions.be` (`CIBLES`, `DESCRIPTIONS`, `logFonctions_lieu`) — preuve : `banc_test_modbus.py` 386/386 PASS. Attention : `logFonctions.be` est dans le socle, donc tous les envs du socle sont à recompiler
- [x] Banc vert avec mutants : chaque garde-fou retiré fait rougir au moins un cas — preuve : 13 mutants sur 13 rouges (limiteur, coupe-circuit, ordre identique, accusé, renvois, ancien état, doublon, quarantaine, coupe jamais refermé, renvoi bloqué, arguments invalides, conversion en texte, premier retour)
- [x] `verificateur-solidification` et `relecteur-berry` sans bloquant — preuve : solidification : aucun bloquant (compilation stricte `berry -s -c` OK) ; relecteur : aucun bloquant, 3 écarts + 4 réserves traités (log du renvoi bloqué, clé ou valeur invalide, 1 et "1", premier retour sans état connu, dépassement 32 bits). Reste non prouvé : la solidification réelle (page Build) et le dépassement 32 bits sur carte (berry.exe PC est en 64 bits)
- [ ] Réserve pour A4 : le driver ne doit transmettre au module que des éléments déclarés (sinon `etats` grossit avec les topics reçus) ; `etats` n'est mis à jour que par `recoit`, donc un `tele/` périodique est nécessaire pour que G3 ne réponde pas « identique » à tort

## A4 — Driver, commande et persist
- [x] `data/fs/controleMqttLiaison.be` : abonnements par esclave déclaré (`stat/<topic>/+`, `tele/<topic>/LWT`, jamais de joker global), pas de règle `Mqtt#Connected` (`mqtt.subscribe` se réabonne seul), refus d'émettre sans `mqtt.connected()` ni `tasmota.is_network_up()` (G8), liste blanche de commandes (Power, Dimmer, CT), valeurs normalisées, renvois plafonnés à 5 par seconde — preuve : `banc_mqtt_liaison.py` code 0, 79 cas OK et 33 mutants rouges sur 33 le 2026-11-17 ; `verifie_berry.py` 0 erreur 0 avertissement
- [x] Commande `ReglageMqttLiaison` (`etat`, `rearme`, `ordre`, aide par `traiteAide`) — preuve : cas « commande » du banc (etat avec en_ligne, ordre envoyer puis attente, syntaxe, rearme). Pas de `persist.save` : rien de persistant n'est modifié
- [x] Revue `relecteur-berry` : 2 bloquants corrigés (renvois d'ordres non idempotents, commande `ordre` ouverte à `Br`, `Restart`, `Backlog`) et 6 réserves traitées (nom avec slash, topic en double ou à joker, LWT, plafond de publish, log debug gardé, message du driver absent) — preuve : cas correspondants du banc
- [x] Revue `verificateur-solidification` : aucun bloquant ; réserve traitée : `import mqttLiaisonFonctions` dans `reglage` (le nom global du module n'existe pas une fois solidifié) — preuve : rapport de l'agent (compilation stricte `berry -g -s` OK sur les deux fichiers, témoin `var format` rouge) ; `import` ajouté dans `mqttLiaisonFonctions.be::mqttLiaisonFonctions_reglage`, banc relancé vert
- [ ] Clés du rapport §7.2 : `persist.schema.json` régénéré par `berry/genere_schema_persist.py` (contient `drivers.liaisonMqtt`, mais la régénération réécrit aussi ≈ 460 lignes de dérive déjà présente : à commiter à part) ; reste `outils_docs/schemas/modele_persist.json` à compléter (non fait)
- [x] Modules ajoutés à `custom_berry_solidify` du seul P4 pilote — preuve : contrôle `ProjectConfig` des 20 envs à FS, 0 écart. `banc_demarrage.py` reste ROUGE pour le P4, mais pour une cause antérieure : instantané du 2026-11-14 en retard sur le portail de jardin (Shutter2/3, DeviceAddress==4) ; à réenregistrer en A5 avec `--enregistre`
- [x] Bloc `drivers.liaisonMqtt` ajouté dans le persist du P4 pilote seulement, accord de l'utilisateur du 2026-11-17, `activation` à OFF, 3 esclaves déclarés (projecteur, pompe, cuve) — preuve : JSON valide, +27 lignes
- [x] PRIORITAIRE : exclure les modules de TOUS les envs sauf le pilote (liste `liaison_mqtt` de `[berry_commun]`) — preuve : 19 `custom_files_exclude` complétés dans `platformio_tasmota_cenv.ini`, +24 lignes, contrôle `ProjectConfig` sur 20 envs à FS : 0 écart. Constat du 2026-11-17 : le pré-script copie tout `data/fs` dans le FS, donc le module commité en A3 serait parti sur chaque carte
- [x] Simplification de l'architecture A (constat du 2026-11-17) : seul le MAÎTRE charge le module et le driver ; un esclave Tasmota natif (projecteur, pompe, cuve) n'a rien à embarquer pour la voie, hors `SetOption73` et `SetOption114` ; le « maître pilote » est le P4 du garage (hors ligne le 2026-11-17, donc validé par banc puis compilé) — preuve : liste `liaison_mqtt` et persist du seul P4
- [ ] Non prouvé : solidification réelle des deux modules (seule la page Build :7700 la valide) et comportement de `ReglageMqttLiaison` après solidification

## A5 — Éléments virtuels `MQTT_<nom>` en lecture seule
- [x] Type `MQTT_` branché dans `configDevices.be` pour capteurs, thermomètres, compteurs, analogiques — preuve : seule la branche des analogiques manquait (thermomètres et compteurs comptent déjà tout virtuel actif et ignorent un groupe inconnu), ajoutée à `configDevices.be` ; capteurs (Switch) viennent en A6 ; chaque élément porte `virtuel: MQTT_<nom>` et `mqtt.chemin` (ex. `DS18B20.Temperature`, `ANALOG.A1`)
- [x] Alimentation depuis `tele/<topic>/SENSOR` (par esclave déclaré, pas de joker) — preuve : `controleMqttLiaison.be::mesures` appelle `globalFonctions.changementEtatCapteur` avec le chemin en déclencheur ; `stat/+/RESULT` ne porte pas les mesures, donc non utilisé ; driver chargé par l'autoexec du P4 sous la garde `drivers.liaisonMqtt` (OFF), `banc_demarrage.py` vert après `--enregistre`
- [x] Banc : un JSON `SENSOR` simulé met à jour l'élément ; un JSON mal formé est rejeté et loggué en `erreur` — preuve : `banc_mqtt_liaison.py` VERT, 37 mutants rouges (4 pour SENSOR) ; relecteur-berry et verificateur-solidification sans bloquant, persist mal typé durci
- [ ] Essai sur carte : une mesure de la cuve visible sur le maître pendant 1 h, tas stable

## A6 — Commande, boutons et interrupteurs
- [ ] Type `MQTT_` branché dans `controleGeneral.be` (aiguillage des ordres) et `configDevices.be` (relais, boutons, interrupteurs)
- [ ] Ordre `cmnd/<topic>/Power<n>` sans retain, avec accusé applicatif (republication limitée à N fois)
- [ ] Évènement bouton ou interrupteur lu dans `stat/<topic>/RESULT` puis action `relaisLie` du maître
- [ ] Banc : un ordre produit un message ; l'écho du `stat/` n'en produit aucun ; la quarantaine se déclenche sur rafale
- [ ] Essai sur carte avec l'éclairage d'essai `tasmota32-jardin-projecteur-led` (ESP32 sans PSRAM, choisi le 2026-11-17 ; mesurer son tas avant), 100 cycles, zéro boucle, zéro redémarrage. Le « Projecteur de Garage » (relai5 du P4, carte 16 relais en ModBus) n'est pas retenu : il n'a pas d'ESP derrière lui

## A7 — Coupe-circuit, alerte broker et repli automatique
- [ ] Alerte sur l'accueil du maître et log `erreur` quand le broker est injoignable plus de N minutes
- [ ] Repli automatique sur Serial ou UDP pour un esclave qui a une seconde voie ; état « inconnu » sinon
- [ ] Banc : le broker disparaît en plein ordre, l'élément n'est pas laissé dans un état faux
- [ ] Essai réel : Mosquitto coupé 5 minutes, aucune carte ne redémarre, ModBus continue

## A9 — Esclave sans Berry (pompe de piscine, ESP8266)
- [ ] Fiche de réglage : `SetOption73 1`, `SetOption114 1`, `Rule` de `Publish`, `ButtonTopic` / `SwitchTopic` selon le cas
- [ ] Esclave déclaré dans la table du maître avec ses éléments `MQTT_<nom>`
- [ ] Essai sur la pompe de piscine, puis relevé du tas de l'ESP8266

## A10 — Portail de jardin et clôture
- [ ] Essai sur le portail de jardin (en dernier, le plus sensible), garde-fous actifs
- [ ] `PROTOCOLE_MODBUS.md`, `outils_docs/README.md`, `CARTE_MODULES_BERRY.md` (`carte_modules_berry.py`) et `CLAUDE.md` du dépôt mis à jour
- [ ] `verifie_references_docs.py` à 0 défaut
- [ ] Firmware recompilé par la page Build puis validé sur carte (journal `/cs`), pas seulement par le banc PC
- [ ] Leçons consignées dans `tasks/lessons.md`

## Améliorations restantes
- [ ] [projet] Architecture B (trames ModBus dans MQTT) : abandonnée, à rouvrir seulement sur demande
- [ ] [projet] Second broker de secours si la voie devient critique

## Vérification
Chaque case se coche avec sa preuve (banc, commit, mesure). Un banc PC ne prouve ni la solidification, ni la RAM, ni la latence derrière le NAPT : ces trois points se valident sur carte.
