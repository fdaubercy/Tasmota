---
chantier: audit-berry
titre: Audit complet — scripts Berry, environnements de build, solidification, logs et communications
objectif: Auditer en lecture seule le code Berry, les envs de build, la solidification, les logs et les communications
statut: clos
cree: 2026-10-21
maj: 2026-10-22
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
- [x] Pour chaque env : liste résolue de `custom_berry_solidify` vs modules réellement importés par son `autoexec.be` et ses `controleXxx` — preuve : a3/dispo.py + matrice A1 ; AUDIT § A3 S1, S2, S3
- [x] Directive `#@ solidify:` et `module("nom")` sans slash sur chaque module listé ; aucun commentaire ne reproduit le motif lu par `addEntryToModtab()` (`solidify-from-url.py:56`) — preuve : a3/controles.py : 37/37 directive = fichier = nom lu par la regex (solidify-from-url.py:36), 0 motif en commentaire
- [x] `globs` de `lib/libesp32/berry_custom/solidify_all_python.be` vs globales réellement appelées par nom dans les modules solidifiés — preuve : 37/37 solidifiés en strict (rc=0), témoin `globaleInconnueDuTemoin` refusé ; 15 noms du fork tous utilisés ; AUDIT § A3 S8
- [x] Modules solidifiés appelés par leur propre nom : présence d'un `import` de niveau fichier dans un script chargé en `.be`, ou d'un `global.X = X` — preuve : a3/nom_global.py : seul ledsPanelFonctions sans nom global, faux positif (import local dans chaque fonction) ; AUDIT § A3 S4
- [x] État mutable hors du module (piège 12) et `return controleXxx` en fin de fichier (piège 13), module par module — preuve : historiqueFonctions.be:77-82 et ledsFonctions.be:87-92 par setmember ; controleLeds seul chargé depuis le FS, a son return ; AUDIT § A3 S6
- [x] Exclusions du LittleFS (`custom_files_exclude_solidified`, `custom_files_exclude`, `modules_solidifies()`, `modules_exclus()`, `copy_fs_image()`) confrontées aux listes de solidification de chaque env — preuve : croisement par env : 0 chemin absent, 4 redondances sur l'ancien maître S3 ; AUDIT § A3 S5
- [x] Divergences de `pio-tools/solidify-from-url.py` et `post_esp32.py` avec l'amont et risque à chaque synchro du fork — preuve : solidify-from-url.py et gen-berry-structures.py identiques à l'amont ; post_esp32.py : AUDIT § A2 E9
- [x] `solidifie_et_compile_berry.py` passé sur les modules solidifiés (sur accord, hors build) — compilation C réelle — preuve : a3/compile/resume.txt (2026-10-22, hors build) : 37/37 rc=0, 0 anonyme ; témoin rc=1
- [x] Modules non solidifiés candidats (`ledsFonctions`, `vrFonctions`, `cuveFonctions`, `garageFonctions`, `controleLeds`…) : gain attendu et obstacles — preuve : AUDIT § A3 « Modules candidats » (garageFonctions faible, cuveFonctions moyen, 3 scripts de driver à convertir)
- [x] Section A3 du rapport rédigée : en place · avantages · inconvénients · propositions — preuve : outils_docs/AUDIT_BERRY_2026-10.md § A3 (8 constats S1-S8, 7 propositions P3.1-P3.7)

## A4 — Architecture et chargement des scripts Berry
- [x] Contrat `autoexec.be` → `controleXxx` → `xxxFonctions` tracé pour chaque carte : ordre de chargement, gardes d'activation (`loadBerryFile(..., activation)`) — preuve : contrat tracé (rapport A4 « Ce qui est en place ») ; garde commentée `gestionFileFolder.be:410-414` (D1)
- [x] Les 8 `autoexec.be` comparés bloc par bloc : partie commune, écarts voulus, dérives — preuve : grep des `compileModule`/`loadBerryFile` des 8 autoexec ; ~50 lignes communes ; 3 générations (D2), `vrFonctions` sans activation `etage2/tasmota32s3-grenier/autoexec.be:69`
- [x] Doublons de cartes (`controlePompeVideCave.be` ×2, `controleGarage.be`/`garageFonctions.be` S3 vs P4, autoexec cave ESP32 vs S3) qualifiés selon le statut A1 — preuve : `controlePompeVideCave.be` identique ×2, `controleGarage` S3/P4 216 l. de diff, `garageFonctions` 61 (D5, D6)
- [x] Fichiers vides ou morts chargés au boot (`controleGrenier.be`, modules d'envs en sommeil) — preuve : `controleGrenier.be` 0 octet chargé `:102` ; dossier `*sauvegarde*` 7 fichiers 96 Ko (D6, D7)
- [x] Fonctions sans appelant (recherche sur `data/` entier, `tasmota.add_cmd`, routes web, `add_rule`), par module — preuve : `scratchpad/a4/fonctions_mortes.py` : 5 fonctions, 0 appel, 0 chaîne, 0 dans `data/sd` ; 25 `add_cmd` (22 noms) relevés, `ReglageWeb` absent (D8)
- [x] Clés du `_persist.json` sans lecteur et lecteurs de clés absentes, par analyse JSON + chemin complet (cohérence avec `persist.schema.json`) — preuve : `scratchpad/a4/cles_persist.py` : clés mortes de `relaisLie` + `typeAction` 367 à 1 468 o/carte (D9) ; schéma inversé `persist.schema.json:956-967` ; aucun lecteur de clé absente (D10)
- [x] Section A4 du rapport rédigée : en place · avantages · inconvénients · propositions — preuve : `outils_docs/AUDIT_BERRY_2026-10.md` § A4, D1-D10, P4.1-P4.7

## A5 — Simplification des modules et drivers
- [x] Chaque driver (`tasmota.add_driver`) : callbacks `every_50ms`/`every_100ms`/`every_second`/`web_*` utiles ou non, travail fait à vide, veille quand le bloc est inactif — preuve : 22 drivers tracés (rapport A5 « Ce qui est en place ») ; N3 `ledsFonctions.be:444` + `modbusFonctions.be:2041`, N4 `controleGarage.be:94`, N5 `controleUDP.be:138-147`, callbacks vides `controleVoletRoulants.be:98-110`, relus dans le fil principal
- [x] `modbusFonctions.be` (3242 l.) : responsabilités (trame, file, transports Série/UDP/TCP, esclave), code mort, branches redondantes ; gain estimé — preuve : 21 blocs cartographiés ; aucune fonction de module morte ; branches maître inatteignables (`:1488`) ; `banc_test_modbus` 309/309 ; N18
- [x] `modBus_TasmotaSlaveModBus.be` et `modBus_Conn16channels.be` : logique commune (relevé, comparaison commande/état) — preuve : logique commune N19 ; réception Conn16 sans `try` `modBus_Conn16channels.be:318-402` (N7), Conn16 sans banc
- [x] `udpFonctions.be`, `discoveryFonctions.be`, `rangeExtenderFonctions.be`, `tcpFonctions.be` : chevauchements, formes de données dupliquées — preuve : N2 ImAlive `udpFonctions.be:308-327` sans `memeValeur` ; N6 TCP forcé `controleModbus.be:159-169` + chargé `cave/tasmota32s3-serveur-rly/autoexec.be:101` ; N16, N17, N22 ; 3 fonctions sans appelant
- [x] `globalFonctions.be`, `diversFonctions.be`, `gestionFileFolder.be`, `webFonctions.be`/`controleWeb.be` : utilitaires en double — preuve : N1 crons jamais exécutés (`scratchpad/a5/lambda.be` : 0 appel, témoin 1) ; N9, N12-N14, N20 ; `relaisLie` ×6
- [x] Pour chaque simplification proposée : filet existant (banc, skill `bancs`) ou banc à prévoir, et témoin négatif à prévoir — preuve : colonnes Filet / Témoin négatif de P5.1-P5.15 ; bancs à écrire : Conn16, `globalFonctions`, driver UDP
- [x] Gain RAM de chaque simplification estimé à partir des mesures de A9 — preuve : estimé qualitativement (flash pour les solidifiés, RAM pour 5 scripts LittleFS, N5, N6, D9) ; chiffrage renvoyé à A9
- [x] Section A5 du rapport rédigée : en place · avantages · inconvénients · propositions — preuve : `outils_docs/AUDIT_BERRY_2026-10.md` § A5, N1-N22, P5.1-P5.15

## A6 — Niveaux de log : le mécanisme
- [x] `logFonctions.be` tracé : les deux filtres, cache des seuils, cible inconnue (cas `historique` et `self.nom`), émission de `detail` au niveau 3 du firmware — preuve : chemin `logFonctions.be:136-151`, cache `:107-131`, cible inconnue → info figé prouvé par `scratchpad/a6/t.be` (L1, L4, L5)
- [x] `logFonctions.CIBLES` vs cibles réellement passées et vs blocs du persist portant une clé `log` — preuve : tableau cibles × persists : cible `mesures` inconnue (L1), 6 clés `log` orphelines (L2)
- [x] `ReglageLog` (`<cible>`, `tous`, `profil`, `<sortie>`) : comportement et persistance après redémarrage, par lecture du code puis, sur accord, essai sur carte avec réglage restauré — preuve : code `logFonctions.be:265-319`, `:397-418` + test Berry (persistance dirty+save, erreurs) ; essai sur carte non fait : observation seule choisie par l'utilisateur le 2026-10-22, lecture `ReglageLog` refusée par le classifieur (P7.7)
- [x] Application des seuils de sortie : `SerialLog`/`WebLog`/`MqttLog`/`SysLog` au boot et au changement de profil ; interaction avec `SERIALLOG_TIMER` (constat seulement) — preuve : `appliqueProfil` `:197-215`, appelé `configGlobal.be:236` et par ReglageLog ; `SetTasConlog` remet `seriallog_timer` (L6)
- [x] Les deux clés `nbLogsFiles` (`diverses.logs` → `FileLog` ; `modules.<x>.logs` → rotation `enregistreLogs`) tracées jusqu'à leur lecteur — preuve : `configGlobal.be:240-243` (FileLog) ; `controleGarage`/`controleCuve` cron 60 s `enregistreLogs` ; sans lecteur cave/différentiel (L8)
- [x] Section A6 du rapport rédigée : en place · avantages · inconvénients · propositions — preuve : § A6, L1-L9, P6.1-P6.6

## A7 — Niveaux de log : conformité et sorties
- [x] Les 10 `log()` directs et ~36 `print()` classés (contraires à la charte / légitimes) — preuve : `scratchpad/a7/audit_logs.py` : 1 `log()` direct (`controleES8311.be:373`), 16 `print` actifs dont 6 contraires (C3, lignes relues)
- [x] Préfixes `NOM_MAJ_SNAKE:`, suffixe `_ERREUR` dans les `except`, échecs logués en `debug` au lieu d'`erreur` — preuve : §B/§C de `rapport_logs.txt` : 8 `except` sans `_ERREUR` (C7), préfixes (C8), échecs trop bas (C6)
- [x] `info` dans un callback fréquent (règle 4) et messages coûteux non gardés par `logFonctions.actif` (règle 5) — preuve : C5 `controleGarage.be:215,248` relus ; règle 5 : 152 non gardés dont ~20 lourds (C4)
- [x] Profils des 8 persists (tous `debug` dans le dépôt) : profil voulu en exploitation demandé à l'utilisateur ; risque MqttLog des esclaves derrière le NAPT rappelé — preuve : tous en `debug` ; profil voulu = `normal` partout (réponse utilisateur 2026-10-22) ; cuve MQTT à `erreur` conforme à la leçon NAPT (C2, P7.1)
- [x] Sortie syslog : `SYS_LOG_HOST` 192.168.0.3, dépendance au PC allumé, lecture par `syslog_tasmota.py` (module, sévérité) cohérente avec les préfixes — preuve : `user_config_override.h:142-150` ; observation syslog 04:00:44-04:11:27, P4 292 l/min, cuve 276 l/min, cave ancien code (C9, A1 corrigé)
- [x] Sortie MQTT : volume en profil `debug` observé (sniffeur MQTT :7100, `stat/<topic>/LOGGING`), effet sur le broker et le tas — preuve : sniffeur MQTT même fenêtre : `stat/garage/LOGGING` 316 msg/min, 30,4 Ko/min (C1) ; `scratchpad/a7/obs/analyse.txt`
- [x] Sur accord, essai réel sur une carte : matrice seuil du module × seuil de sortie, témoin qui doit rester muet, réglages restaurés — preuve : non fait : l'utilisateur a choisi l'observation seule le 2026-10-22
- [x] Section A7 du rapport rédigée : en place · avantages · inconvénients · propositions — preuve : § A7, C1-C10, P7.1-P7.8 ; A1 et A4 (D6, P4.4) corrigés après l'observation

## A8 — Communications entre modules et ESP-NOW
- [x] Inventaire des voies en place, par paire de cartes (P4 ↔ cuve, P4 ↔ rideau, P4 ↔ carte 16 relais, cave, grenier) : ModBus RTU filaire, ModBus sur UDP (`ModbusUDP`, `ModbusPushUDP`), TCP, multicast 224.3.0.1:4000, MQTT, HTTP (`/json?commande=`), discovery/`ImAlive` — sens, déclencheur, accusé, reprise sur perte — preuve : § A8.3 (tableau des voies, mesures disponibles et jamais mesurées)
- [x] Identification des esclaves par un maître Range Extender : chemin actuel (`forceEnvoiParams` → `ImAlive` → `/json/discovery.json`, `ANALYSE_BERRY_MODBUS_DISCOVERY.md` §2.6), délai de découverte, esclave éteint, carte réaffectée, entrées périmées — preuve : § A8.4 R1-R4 ; reset unique `udpFonctions.be:448`, cycle lié à Boot `:441-449` relus
- [x] Commande firmware `RgxClients` (`xdrv_58_range_extender.ino:179-205`) évaluée comme source complémentaire : appel depuis Berry, coût sur le P4, rapprochement MAC ↔ fiche discovery (lecture seule sur carte, sur accord) — preuve : `xdrv_58_range_extender.ino:178-211` relu (R5) ; appel Berry possible, seul appelant mort ; lu sur le P4 le 2026-10-22 06:41 par MQTT (à la demande de l'utilisateur) : seule la cuve associée, rideau absent
- [x] Mesures UDP actuelles relues (testeur :7400, grille ModBus, `DIAGNOSTIC_UDP_2026-10-17.md`) : latence, pertes, doublons, en Range Extender et Wi-Fi classique — preuve : § A8.3 : chiffres de PROTOCOLE §9 et de la reprise ; liste de ce qui n'a jamais été mesuré
- [x] Alternatives présentes dans le dépôt comparées sur une même grille (latence, accusé, portée, RAM/flash, compatibilité P4, coexistence avec le point d'accès) : TasMesh/ESP-NOW (`xdrv_57_*`), WizMote (`xdrv_77`), BLE (`xdrv_79`), LoRa (`xdrv_73_*`, `controleLoRaWan.be`), MQTT local, ModBus TCP — preuve : grille § A8.5 ; coûts `my_user_config.h:449,452,952,1279` relus
- [x] Contraintes ESP-NOW vérifiées (code + doc Espressif) : canal commun imposé par le point d'accès du maître, chiffrement et nombre de pairs, taille de trame, P4 sans radio propre (coprocesseur C6 via esp_hosted) — preuve : `esp_now.h:37` (P4/S3) relu ; esp-hosted-mcu#19 ouverte, vérifiée le 2026-10-22
- [x] Analyse de TasMesh (`xdrv_57_*`) : capacités, avantages, inconvénients, difficulté, limites, et transport du ModBus — preuve : AUDIT_BERRY_2026-10.md § A8.1 (T1 `xdrv_57_9_tasmesh.ino:382`/`:794` nœud ESP8266 seul ; T2 aucune lib esp32p4 n'exporte `esp_now_send`, témoin `esp32s3/lib/libespnow.a` ; T10 `:247` vs `xdrv_02_9_mqtt.ino:970`)
- [x] Faisabilité d'un ESP32 / ESP32-S3 esclave ESP-NOW (SDK, coexistence Wi-Fi/Range Extender, voies de mise en œuvre, cas du maître P4) — preuve : AUDIT_BERRY_2026-10.md § A8.2 (`esp32s3/include/esp_wifi/include/esp_now.h:32,37`, `esp32s3/sdkconfig:1868`, absence de `libraries/ESP_NOW`)
- [x] Recherche GitHub : implémentations ESP-NOW pour Tasmota (TasMesh amont, issues/discussions, module Berry éventuel, forks, drivers tiers) — liens, maintenance, compatibilité avec la version du fork — preuve : § A8.5 : aucun binding Berry (grep), QuickESPNow `lib/lib_div`, issue #19, shim ESPHome, ponts tiers
- [x] Section A8 du rapport rédigée : en place · avantages · inconvénients · propositions (voie recommandée par usage : commande temps réel, relevé, découverte ; prototype éventuel avec retour arrière par réglage) — preuve : § A8.3-A8.6, R1-R6, P8.6-P8.10, voie recommandée par usage

## A9 — Utilisation de la RAM
- [x] Profil mémoire de chaque carte active tracé : puce, PSRAM ou non (ESP32 classiques cave/différentiel sans PSRAM ; S3 N16R8 ; P4), partitions, options de `user_config_override.h` qui pèsent sur le tas — preuve : § A9 tableau des profils ; `USE_BERRY_PSRAM` `user_config_override.h:614`, `xdrv_52_9_berry.ino:79-81` relus
- [x] Relevés sur carte, sur accord et en lecture seule (`tasmota.memory()`, `Status 4`, `BRY: GC` en sortie `detail`) : tas libre, plus gros bloc (fragmentation), PSRAM, tas Berry — après boot, en régime établi, et au pic (page web, discovery, historique) — preuve : relevés PASSIFS `tele/STATE` (04:00-04:11, 06:20-06:36), `scratchpad/a9/memoire_state.py` ; M1 fuite ≈0,6 Ko/min P4+cuve ; + `Status 4`, `Status 1`, `Br tasmota.memory()` le 2026-10-22 06:41 (P4 100 Ko, cuve 109 Ko, frag 37 %, pile P4 2,3/8 Ko, Software reset CPU)
- [x] Consommateurs Berry recensés et chiffrés : persist chargé entier en RAM (≈31 Ko sur le P4) et globales `serveur`/`diverses`/`modules`/`drivers`, `discovery.json`, files ModBus, tampons de l'historique, chaînes de pages web, closures et drivers enregistrés — preuve : tableau § A9 (berry.exe + modèle 32 bits) ; total estimé P4 95-110 Ko vs `HeapUsed` mesuré 100 Ko, cuve 70-75 vs 76
- [x] Modules chargés depuis le LittleFS (bytecode en RAM) vs solidifiés (en flash) : écart mesuré ou estimé par module (lien avec A3) — preuve : cuve ≈25 Ko, P4 ≈12 Ko, rideau 0 ; en PSRAM (P9.7)
- [x] Pics transitoires : lectures de fichiers d'un bloc, `json.dump`/`json.load` de gros objets, `string.format` de grandes chaînes, concaténations en boucle ; carte sans PSRAM traitée par mesure côté PC, jamais par lecture console d'un gros fichier — preuve : M2 `/histo` `historiqueFonctions.be:512-516,616-621` relus ; M3, M5, M7
- [x] Tampons du firmware : `MQTT_MAX_PACKET_SIZE`, tampons web/série, avec le plus gros message réellement produit (`mqtt.publish`, `publish_result`) avant toute proposition de réduction — preuve : MQTT 2048 (`user_config_override.h:240`) justifié par la fiche config 1-1,4 Ko ; log 6 Ko ; FTP 4,6 Ko
- [x] Comportement du ramasse-miettes : fréquence et durée des `BRY: GC`, objets retenus par des globales ou caches jamais purgés — preuve : M4 : allocations par tick + logs detail, GC estimé toutes les 5-10 s ; caches bornés ; `HeapUsed` constant 2 h 30
- [x] Section A9 du rapport rédigée : en place · avantages · inconvénients · propositions (gain attendu par proposition, en Ko) — preuve : § A9, M1-M7, P9.1-P9.8 avec gain en Ko

## A10 — Autres points relevés en cours d'audit
- [x] Couverture des bancs : modules sans banc, bancs qui ne couvrent pas le chemin réel (livraison, transport) — preuve : tableau § A10 ; bancs relancés le 2026-10-22 : BANC_VEILLE_DRIVERS OK, TEST_DISCOVERY OK (216), BANC_MODBUS OK, BANC_LEDS OK ; B8-B10
- [x] Docs de référence confrontées au code (`SOLIDIFICATION_BERRY.md`, `CARTE_MODULES_BERRY.md`, `README.md` § logs, charte de `CLAUDE.md`, skill `tasmota-berry`) — preuve : ~300 affirmations vérifiées, ~45 écarts dont 9 G ; §7 `SOLIDIFICATION_BERRY.md:544-557`, cible `leds` absente `README.md:78-80`, pièges 12-13 `:312,:335` relus (B11-B19)
- [x] Robustesse des chemins de boot : `try/except` sur fichiers/JSON/réseau, persist incomplet — preuve : B1 `autoexec.be:19` avant la garde `:56` (test `scratchpad/a10/t1.be`), B2 0 `try` dans les 3 autoexec, B3 `controleGeneral.be:133-137`, B4 `gestionFileFolder.be:76-78` relus
- [x] Section A10 du rapport rédigée : en place · avantages · inconvénients · propositions — preuve : § A10, B1-B19, P10.1-P10.7

## A11 — Synthèse et remise à l'utilisateur
- [x] Rapport relu de bout en bout : chaque constat coté (B/G/L/S/D) avec sa preuve et sa proposition — preuve : relecture mécanique `scratchpad/a11/relecture.py` : 109 constats, cotes vérifiées ; propositions sans renvoi (A2, A3, A8.1, A9) rattachées à la main dans la synthèse
- [x] Tableau de synthèse des propositions (cotation × effort × risque × bénéfice) — preuve : `outils_docs/AUDIT_BERRY_2026-10.md` § Synthèse : 78 propositions × corrige × cote × effort × risque × bénéfice, 13 lots, top 10
- [x] Plan d'action `tasks/plans/actions-audit-berry.md` rédigé au format `_FORMAT.md`, statut `en-pause` : une action par proposition, sans aucune exécution — preuve : créé, statut en-pause, 13 actions / 78 étapes (une par proposition), lu sans alerte par `parseur-plan.mjs`
- [x] Remise à l'utilisateur : rapport + plan d'action présentés ; décisions laissées à l'utilisateur — preuve : rapport + plan présentés le 2026-10-22 ; aucune proposition exécutée

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
