---
chantier: audit-berry
titre: Audit complet — scripts Berry, environnements de build, solidification, logs et communications
statut: actif
cree: 2026-10-21
maj: 2026-10-21
source: partitioned-hatching-key.md
---
# Audit complet — scripts Berry, environnements de build, solidification, logs et communications

## Contexte

Demande du 2026-10-21 : évaluer l'ensemble du codage Berry du fork et de la mise en place des
environnements, puis proposer des améliorations ou modifications. Volets demandés : (1) les scripts
Berry et les modules/drivers simplifiables sans perte de fonction, (2) la construction des
environnements, (3) la solidification, (4) les niveaux de log (série, web, MQTT, syslog),
(5) les communications entre modules : identification des esclaves par un maître Range Extender,
voies sans fil plus efficaces que l'UDP, recherche GitHub sur ESP-NOW entre modules Tasmota,
(6) l'utilisation de la RAM et les actions d'amélioration.

**Nature de l'audit — décidée par l'utilisateur le 2026-10-21**
- **C'est un audit, pas un chantier.** Claude ne modifie AUCUN fichier de code, de configuration ou de
  build, ni aucun réglage de carte de sa propre initiative. Il lit, mesure, trace et propose.
- L'audit **trace chaque élément en place** avec ses **avantages** et ses **inconvénients**, puis
  formule des **propositions** (corrections, simplifications, améliorations).
- **L'utilisateur est seul juge** de ce qui sera mis en place. Tout lui est rendu par un **plan d'action**
  (format `tasks/plans/_FORMAT.md`) qu'il exécutera, ou fera exécuter, lot par lot s'il le décide.

**Livrables (les seuls fichiers écrits par l'audit)**
- Le rapport `outils_docs/AUDIT_BERRY_2026-10.md` : une section par action A2 à A10, chacune en quatre
  parties — *Ce qui est en place* · *Avantages* · *Inconvénients / défauts constatés* · *Propositions*.
- Le plan d'action des propositions `tasks/plans/actions-audit-berry.md` (A11), non engagé.
- Ce plan-ci, coché au fil de l'audit. Aucun commit sans demande explicite.

**Grille de cotation des constats** : **B** bloquant (casse un build/boot ou perd une donnée) ·
**G** gênant (défaut actif) · **L** latent (chemin non emprunté aujourd'hui) · **S** simplification ·
**D** documentation. Chaque proposition porte aussi un effort estimé et un risque.

**Terrain mesuré avant d'écrire ce plan**
- ~20 500 lignes de Berry dans `data/` (hors `*sauvegarde*`) : 39 fichiers dans `data/fs/`, le reste dans
  `data/<lieu>/<carte>/`. Gros modules : `modbusFonctions.be` (3242 l.), `modBus_TasmotaSlaveModBus.be`
  (1463), `udpFonctions.be` (854), `discoveryFonctions.be` (722).
- 15 `[env:]` dans `platformio_tasmota_cenv.ini` (5 bases + 10 cartes), 8 dossiers de carte.
- Solidification par 3 listes partagées `[berry_commun]` (socle, modbus, historique) ; lecteurs :
  `solidify-from-url.py:98`, `post_esp32.py:197`, `pre_utilitaires_platformio.py:483`.
- Doublons visibles : `controlePompeVideCave.be` identique sur les 2 cartes cave ; `controleGarage.be`
  S3/P4 (216 lignes de diff) ; 8 `autoexec.be` voisins mais divergents ; `controleGrenier.be` vide mais
  chargé par l'autoexec du grenier (`autoexec.be:102`).
- Logs : 319 appels `logFonctions.log`, 10 `log()` directs, ~36 `print()` ; les 8 persists du dépôt en
  profil `debug` ; l'historique logue avec la cible `self.nom`, absente de `logFonctions.CIBLES`
  (piste, pas encore un défaut).
- Communications : `RgxClients` (`xdrv_58_range_extender.ino:179`, MAC + IP + RSSI des stations du point
  d'accès) non utilisée par le Berry ; TasMesh sur ESP-NOW (`xdrv_57_9_tasmesh.ino`, commenté dans
  `user_config_override.h:1117`) ; WizMote (`xdrv_77`), BLE (`xdrv_79`), LoRa (`xdrv_73_*`). Rien n'est jugé.

**Règles de conduite**
- Preuve exigée pour tout constat : `fichier:ligne`, sortie d'un banc, ou observation horodatée d'une carte.
  Une conclusion d'absence (« jamais appelé », « sans lecteur ») cite la recherche faite et son périmètre.
- Recherche de lecteurs/appelants sur `data/` entier (hors `*sauvegarde*`), jamais sur `data/fs` seul.
- Toute conclusion de sous-agent est relue dans le fil principal avant d'entrer au rapport.
- Mesures sur carte (logs, UDP, `RgxClients`) : seulement avec l'accord de l'utilisateur, en lecture ou
  avec réglage restauré à l'identique ; jamais d'émission de test vers 224.3.0.1:4000.
- Aucun `pio run` (même `--list-targets`) ; `solidifie_et_compile_berry.py` (qui écrit dans
  `lib/libesp32/berry_custom`) seulement sur accord et hors build.
- Ne PAS reproposer (choix de l'utilisateur) : AP Range Extender en 192.168.4.1/24, RgxPort périodique,
  bouton esclave du maître, mot de passe Wi-Fi public, `SERIALLOG_TIMER`, `USE_ESP32_WDT`, historique sur
  ESP32 sans PSRAM, longueur de `synchronise_fork_tasmota.py` / `test_liaison_modbus.be`.

## A1 — Cadrage et référentiel
- [x] Squelette du rapport `outils_docs/AUDIT_BERRY_2026-10.md` créé (sections A2 à A10 en quatre parties, grille de cotation) — preuve : outils_docs/AUDIT_BERRY_2026-10.md (créé le 2026-10-21)
- [x] Statut de chaque carte confirmé avec l'utilisateur : active / en sommeil / remplacée (grenier, cave ESP32 vs S3, garage S3 `serveur-modbus` vs P4, `pompe-piscine`, `rdc-vr-porte`) — preuve : réponses de l'utilisateur du 2026-10-21, tableau AUDIT_BERRY_2026-10.md § A1
- [x] Carte des modules produite par `berry/carte_modules_berry.py` vers le scratchpad (sans écraser `CARTE_MODULES_BERRY.md`) et comparée à la version suivie — preuve : rc 0, 43 modules / 8 cartes / 14 incohérences ; diff trié vide avec la version suivie ; `git status` du fichier suivi vide
- [x] Bancs existants lancés une fois en lecture, résultats consignés comme ligne de base (`banc_test_modbus.py`, `banc_leds.py`, `banc_graphiques.py`, `test_discovery.be`, `banc_veille_drivers.be`, `verifie_berry.py`) — preuve : AUDIT_BERRY_2026-10.md § A1 (309/309, 36, 216, 19, 95, 63 ok ; 54 fichiers 0 erreur, témoin rejeté rc 1) ; rendu Chrome de `banc_graphiques.py` non lancé (build en cours)

## A2 — Construction des environnements
- [x] Arbre d'héritage `extends` des 15 envs tracé ; options redéfinies sans raison ou perdues relevées — preuve : ProjectConfig résolu (scratchpad a2/envs.json) ; AUDIT § A2 « Ce qui est en place », E1 (LVGL hérité, cenv:121-122), E14
- [x] Chaque `-D FIRMWARE_*` rapproché de sa section dans `tasmota/user_config_override.h`, et inversement (sections orphelines) — preuve : AUDIT § A2 E3 (8 sections orphelines, user_config_override.h:872-1688 et :1829-1984 ; aucune occurrence dans platformio*.ini) et E4
- [x] `data_dir` calculé par `transform_name()` (`pre_utilitaires_platformio.py:256`) confronté aux dossiers existants ; envs sans dossier relevés — preuve : 8 dossiers = custom_files_upload de chaque env ; aucun résidu ; image FS construite depuis custom_files_upload (post_esp32.py:140-181) ; AUDIT § A2 E8, E15
- [x] Tables de partitions : taille du LittleFS de chaque carte comparée au contenu réellement embarqué — preuve : scratchpad a2/taille_fs.py ; tableau d'occupation AUDIT § A2 (5 % S3/P4, 45 % différentiel, 446 % rdc-vr-porte) ; E11
- [x] Ports, variantes OTA commentées et `custom_ota_files` : cohérence et risques d'écrasement du persist — preuve : aucun custom_ota_files actif (ProjectConfig) ; ports cenv:114…616 ; AUDIT § A2 E13
- [x] Réécritures du build tracées (`adapteParametresPlatformio_override`, `increment_config_holder`, `change_data_dir_in_platformio_ini`) : effets de bord, idempotence, sauvegardes — preuve : pre_utilitaires_platformio.py:289-335, :361-406, :408-447 (mort), :778-779 ; AUDIT § A2 E5, E6, E7, E8
- [x] `extra_scripts` de chaque env (pre/post, ordre) et divergences des `pio-tools/` du fork avec l'amont (`git diff upstream/development -- pio-tools/`) — preuve : extra_scripts résolus (a2/envs.json) ; git diff --stat upstream/development -- pio-tools/ : 13 fichiers, ~90 % traduction ; AUDIT § A2 E9
- [x] Section A2 du rapport rédigée : en place · avantages · inconvénients · propositions — preuve : outils_docs/AUDIT_BERRY_2026-10.md § A2 (15 constats E1-E15, 10 propositions P2.1-P2.10)

## A3 — Chaîne de solidification
- [ ] Pour chaque env : liste résolue de `custom_berry_solidify` vs modules réellement importés par son `autoexec.be` et ses `controleXxx`
- [ ] Directive `#@ solidify:` et `module("nom")` sans slash sur chaque module listé ; aucun commentaire ne reproduit le motif lu par `addEntryToModtab()` (`solidify-from-url.py:56`)
- [ ] `globs` de `lib/libesp32/berry_custom/solidify_all_python.be` vs globales réellement appelées par nom dans les modules solidifiés
- [ ] Modules solidifiés appelés par leur propre nom : présence d'un `import` de niveau fichier dans un script chargé en `.be`, ou d'un `global.X = X`
- [ ] État mutable hors du module (piège 12) et `return controleXxx` en fin de fichier (piège 13), module par module
- [ ] Exclusions du LittleFS (`custom_files_exclude_solidified`, `custom_files_exclude`, `modules_solidifies()`, `modules_exclus()`, `copy_fs_image()`) confrontées aux listes de solidification de chaque env
- [ ] Divergences de `pio-tools/solidify-from-url.py` et `post_esp32.py` avec l'amont et risque à chaque synchro du fork
- [ ] `solidifie_et_compile_berry.py` passé sur les modules solidifiés (sur accord, hors build) — compilation C réelle
- [ ] Modules non solidifiés candidats (`ledsFonctions`, `vrFonctions`, `cuveFonctions`, `garageFonctions`, `controleLeds`…) : gain attendu et obstacles
- [ ] Section A3 du rapport rédigée : en place · avantages · inconvénients · propositions

## A4 — Architecture et chargement des scripts Berry
- [ ] Contrat `autoexec.be` → `controleXxx` → `xxxFonctions` tracé pour chaque carte : ordre de chargement, gardes d'activation (`loadBerryFile(..., activation)`)
- [ ] Les 8 `autoexec.be` comparés bloc par bloc : partie commune, écarts voulus, dérives
- [ ] Doublons de cartes (`controlePompeVideCave.be` ×2, `controleGarage.be`/`garageFonctions.be` S3 vs P4, autoexec cave ESP32 vs S3) qualifiés selon le statut A1
- [ ] Fichiers vides ou morts chargés au boot (`controleGrenier.be`, modules d'envs en sommeil)
- [ ] Fonctions sans appelant (recherche sur `data/` entier, `tasmota.add_cmd`, routes web, `add_rule`), par module
- [ ] Clés du `_persist.json` sans lecteur et lecteurs de clés absentes, par analyse JSON + chemin complet (cohérence avec `persist.schema.json`)
- [ ] Section A4 du rapport rédigée : en place · avantages · inconvénients · propositions

## A5 — Simplification des modules et drivers
- [ ] Chaque driver (`tasmota.add_driver`) : callbacks `every_50ms`/`every_100ms`/`every_second`/`web_*` utiles ou non, travail fait à vide, veille quand le bloc est inactif
- [ ] `modbusFonctions.be` (3242 l.) : responsabilités (trame, file, transports Série/UDP/TCP, esclave), code mort, branches redondantes ; gain estimé
- [ ] `modBus_TasmotaSlaveModBus.be` et `modBus_Conn16channels.be` : logique commune (relevé, comparaison commande/état)
- [ ] `udpFonctions.be`, `discoveryFonctions.be`, `rangeExtenderFonctions.be`, `tcpFonctions.be` : chevauchements, formes de données dupliquées
- [ ] `globalFonctions.be`, `diversFonctions.be`, `gestionFileFolder.be`, `webFonctions.be`/`controleWeb.be` : utilitaires en double
- [ ] Pour chaque simplification proposée : filet existant (banc, skill `bancs`) ou banc à prévoir, et témoin négatif à prévoir
- [ ] Gain RAM de chaque simplification estimé à partir des mesures de A9
- [ ] Section A5 du rapport rédigée : en place · avantages · inconvénients · propositions

## A6 — Niveaux de log : le mécanisme
- [ ] `logFonctions.be` tracé : les deux filtres, cache des seuils, cible inconnue (cas `historique` et `self.nom`), émission de `detail` au niveau 3 du firmware
- [ ] `logFonctions.CIBLES` vs cibles réellement passées et vs blocs du persist portant une clé `log`
- [ ] `ReglageLog` (`<cible>`, `tous`, `profil`, `<sortie>`) : comportement et persistance après redémarrage, par lecture du code puis, sur accord, essai sur carte avec réglage restauré
- [ ] Application des seuils de sortie : `SerialLog`/`WebLog`/`MqttLog`/`SysLog` au boot et au changement de profil ; interaction avec `SERIALLOG_TIMER` (constat seulement)
- [ ] Les deux clés `nbLogsFiles` (`diverses.logs` → `FileLog` ; `modules.<x>.logs` → rotation `enregistreLogs`) tracées jusqu'à leur lecteur
- [ ] Section A6 du rapport rédigée : en place · avantages · inconvénients · propositions

## A7 — Niveaux de log : conformité et sorties
- [ ] Les 10 `log()` directs et ~36 `print()` classés (contraires à la charte / légitimes)
- [ ] Préfixes `NOM_MAJ_SNAKE:`, suffixe `_ERREUR` dans les `except`, échecs logués en `debug` au lieu d'`erreur`
- [ ] `info` dans un callback fréquent (règle 4) et messages coûteux non gardés par `logFonctions.actif` (règle 5)
- [ ] Profils des 8 persists (tous `debug` dans le dépôt) : profil voulu en exploitation demandé à l'utilisateur ; risque MqttLog des esclaves derrière le NAPT rappelé
- [ ] Sortie syslog : `SYS_LOG_HOST` 192.168.0.3, dépendance au PC allumé, lecture par `syslog_tasmota.py` (module, sévérité) cohérente avec les préfixes
- [ ] Sortie MQTT : volume en profil `debug` observé (sniffeur MQTT :7100, `stat/<topic>/LOGGING`), effet sur le broker et le tas
- [ ] Sur accord, essai réel sur une carte : matrice seuil du module × seuil de sortie, témoin qui doit rester muet, réglages restaurés
- [ ] Section A7 du rapport rédigée : en place · avantages · inconvénients · propositions

## A8 — Communications entre modules et ESP-NOW
- [ ] Inventaire des voies en place, par paire de cartes (P4 ↔ cuve, P4 ↔ rideau, P4 ↔ carte 16 relais, cave, grenier) : ModBus RTU filaire, ModBus sur UDP (`ModbusUDP`, `ModbusPushUDP`), TCP, multicast 224.3.0.1:4000, MQTT, HTTP (`/json?commande=`), discovery/`ImAlive` — sens, déclencheur, accusé, reprise sur perte
- [ ] Identification des esclaves par un maître Range Extender : chemin actuel (`forceEnvoiParams` → `ImAlive` → `/json/discovery.json`, `ANALYSE_BERRY_MODBUS_DISCOVERY.md` §2.6), délai de découverte, esclave éteint, carte réaffectée, entrées périmées
- [ ] Commande firmware `RgxClients` (`xdrv_58_range_extender.ino:179-205`) évaluée comme source complémentaire : appel depuis Berry, coût sur le P4, rapprochement MAC ↔ fiche discovery (lecture seule sur carte, sur accord)
- [ ] Mesures UDP actuelles relues (testeur :7400, grille ModBus, `DIAGNOSTIC_UDP_2026-10-17.md`) : latence, pertes, doublons, en Range Extender et Wi-Fi classique
- [ ] Alternatives présentes dans le dépôt comparées sur une même grille (latence, accusé, portée, RAM/flash, compatibilité P4, coexistence avec le point d'accès) : TasMesh/ESP-NOW (`xdrv_57_*`), WizMote (`xdrv_77`), BLE (`xdrv_79`), LoRa (`xdrv_73_*`, `controleLoRaWan.be`), MQTT local, ModBus TCP
- [ ] Contraintes ESP-NOW vérifiées (code + doc Espressif) : canal commun imposé par le point d'accès du maître, chiffrement et nombre de pairs, taille de trame, P4 sans radio propre (coprocesseur C6 via esp_hosted)
- [x] Analyse de TasMesh (`xdrv_57_*`) : capacités, avantages, inconvénients, difficulté, limites, et transport du ModBus — preuve : AUDIT_BERRY_2026-10.md § A8.1 (T1 `xdrv_57_9_tasmesh.ino:382`/`:794` nœud ESP8266 seul ; T2 aucune lib esp32p4 n'exporte `esp_now_send`, témoin `esp32s3/lib/libespnow.a` ; T10 `:247` vs `xdrv_02_9_mqtt.ino:970`)
- [x] Faisabilité d'un ESP32 / ESP32-S3 esclave ESP-NOW (SDK, coexistence Wi-Fi/Range Extender, voies de mise en œuvre, cas du maître P4) — preuve : AUDIT_BERRY_2026-10.md § A8.2 (`esp32s3/include/esp_wifi/include/esp_now.h:32,37`, `esp32s3/sdkconfig:1868`, absence de `libraries/ESP_NOW`)
- [ ] Recherche GitHub : implémentations ESP-NOW pour Tasmota (TasMesh amont, issues/discussions, module Berry éventuel, forks, drivers tiers) — liens, maintenance, compatibilité avec la version du fork
- [ ] Section A8 du rapport rédigée : en place · avantages · inconvénients · propositions (voie recommandée par usage : commande temps réel, relevé, découverte ; prototype éventuel avec retour arrière par réglage)

## A9 — Utilisation de la RAM
- [ ] Profil mémoire de chaque carte active tracé : puce, PSRAM ou non (ESP32 classiques cave/différentiel sans PSRAM ; S3 N16R8 ; P4), partitions, options de `user_config_override.h` qui pèsent sur le tas
- [ ] Relevés sur carte, sur accord et en lecture seule (`tasmota.memory()`, `Status 4`, `BRY: GC` en sortie `detail`) : tas libre, plus gros bloc (fragmentation), PSRAM, tas Berry — après boot, en régime établi, et au pic (page web, discovery, historique)
- [ ] Consommateurs Berry recensés et chiffrés : persist chargé entier en RAM (≈31 Ko sur le P4) et globales `serveur`/`diverses`/`modules`/`drivers`, `discovery.json`, files ModBus, tampons de l'historique, chaînes de pages web, closures et drivers enregistrés
- [ ] Modules chargés depuis le LittleFS (bytecode en RAM) vs solidifiés (en flash) : écart mesuré ou estimé par module (lien avec A3)
- [ ] Pics transitoires : lectures de fichiers d'un bloc, `json.dump`/`json.load` de gros objets, `string.format` de grandes chaînes, concaténations en boucle ; carte sans PSRAM traitée par mesure côté PC, jamais par lecture console d'un gros fichier
- [ ] Tampons du firmware : `MQTT_MAX_PACKET_SIZE`, tampons web/série, avec le plus gros message réellement produit (`mqtt.publish`, `publish_result`) avant toute proposition de réduction
- [ ] Comportement du ramasse-miettes : fréquence et durée des `BRY: GC`, objets retenus par des globales ou caches jamais purgés
- [ ] Section A9 du rapport rédigée : en place · avantages · inconvénients · propositions (gain attendu par proposition, en Ko)

## A10 — Autres points relevés en cours d'audit
- [ ] Couverture des bancs : modules sans banc, bancs qui ne couvrent pas le chemin réel (livraison, transport)
- [ ] Docs de référence confrontées au code (`SOLIDIFICATION_BERRY.md`, `CARTE_MODULES_BERRY.md`, `README.md` § logs, charte de `CLAUDE.md`, skill `tasmota-berry`)
- [ ] Robustesse des chemins de boot : `try/except` sur fichiers/JSON/réseau, persist incomplet
- [ ] Section A10 du rapport rédigée : en place · avantages · inconvénients · propositions

## A11 — Synthèse et remise à l'utilisateur
- [ ] Rapport relu de bout en bout : chaque constat coté (B/G/L/S/D) avec sa preuve et sa proposition
- [ ] Tableau de synthèse des propositions (cotation × effort × risque × bénéfice)
- [ ] Plan d'action `tasks/plans/actions-audit-berry.md` rédigé au format `_FORMAT.md`, statut `en-pause` : une action par proposition, sans aucune exécution
- [ ] Remise à l'utilisateur : rapport + plan d'action présentés ; décisions laissées à l'utilisateur

## Améliorations restantes
- [ ] [projet] Après décision de l'utilisateur seulement : exécution des propositions qu'il aura retenues, lot par lot
- [ ] [projet] Ré-audit ciblé après les lots retenus (même grille, même preuves)

## Vérification
Chaque étape se coche avec « — preuve : … » : `fichier:ligne` lu, sortie d'un banc (code de sortie ou
décompte vert/rouge), recherche citée avec son périmètre, ou observation horodatée d'une carte
(syslog :7200, sniffeur MQTT :7100, pont série :7000). Un test vert n'est retenu qu'avec son témoin négatif.
Contrôle final de non-intervention : `git status` en fin d'audit ne montre que les livrables
(rapport, plan d'action, ce plan), rien d'autre.
Exécution conseillée : une action par conversation ; A2+A3 et la recherche GitHub de A8 peuvent partir en
parallèle sur des sous-agents en lecture seule ; A6, A7 et les mesures de A8 et A9 demandent des cartes
branchées (A9 gagne à précéder A5 pour chiffrer les gains).
