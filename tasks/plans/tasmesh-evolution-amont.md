---
chantier: tasmesh-evolution-amont
titre: Faire évoluer TasMesh en amont (commandes de nœud à nœud, charge utile, clés par pair)
statut: actif
cree: 2026-11-16
maj: 2026-11-27
objectif: Sonder arendst/Tasmota par une discussion courte, puis proposer de petits PR isolés sur TasMesh si les mainteneurs y sont favorables
famille: modbus-reseau
liens: rgx-ethernet-uplink
---
# Faire évoluer TasMesh en amont

## Contexte
Analyse du 2026-11-16 : TasMesh (`tasmota/tasmota_xdrv_driver/xdrv_57_1_tasmesh_support.ino` et `xdrv_57_9_tasmesh.ino`) est une couche
posée sur ESP-NOW : étoile autour d'un broker ESP32 relié à MQTT, charge utile de 160 octets (`MESH_PAYLOAD_SIZE`), 26 morceaux au
plus, TTL de 2 bits, ChaCha20-Poly1305 avec une clé unique tirée du mot de passe Wi-Fi. `PACKET_TYPE_COMMAND` existe mais est
marqué « not used yet ».

Méthode, calquée sur la discussion #25280 (Range Extender) qui a bien marché : une discussion courte et factuelle, une question
fermée par sujet, aucun code avant la réponse d'Arend (arendst), puis un PR par sujet, depuis une branche propre issue de
`upstream/development`, jamais du `development` du fork.

Emplacement : Discussions > Ideas (les Issues d'arendst/Tasmota sont réservées aux bogues). Doublons relevés le 2026-11-16 :
#11939 (« ESP-NOW - TasMesh Code », 2021, statut « POC » donné par Arend, 10 commentaires dont la demande de fonctionner sans broker MQTT),
#23665 (maillage de prises à grande échelle), #24814 (Blau, ESP-NOW sans chiffrement, remarque de s-hadinger sur l'authentification),
#21735, #20375, #15221. Aucun ne traite de `PACKET_TYPE_COMMAND`. Décision proposée : nouvelle discussion Ideas qui cite #11939 et #24814,
plutôt qu'un commentaire sur un fil de 2021 qui réveillerait tous ses abonnés pour un autre sujet.

Corrections de l'analyse initiale (2026-11-16) :
1. **Un ESP32 ne peut pas être nœud** : la doc amont dit « An ESP32 is only supported as a broker, an ESP8266 only as a node », et
   `MESHstartNode` est sous `#ifdef ESP8266 // for now only ESP8266, might be added for the ESP32 later`. Le rappel de l'utilisateur
   fait de « tous les ESP32 comme nœuds » la proposition n°1 (le commentaire du code est un appui pour la demander). Le fil #21735
   (« ESP32 as node for tasmesh? ») pose la même question sans réponse d'Arend. Travail à prévoir : la fonction de réception ESP32
   (`CB_MESHDataReceived`) n'a que le rôle broker (file de réception, enregistrement) ; le comportement nœud (heure, liste des pairs)
   n'existe que dans la version ESP8266. Fixer le canal sans `wifi_promiscuous` (API ESP32 différente) ; un nœud coupe Wi-Fi et serveur web.
   Puces à ne pas promettre sans essai : ESP32-P4 (Wi-Fi par coprocesseur C6), C6, H2.
2. Doc : l'accusé de réception d'ESP-NOW est jugé peu fiable (« send-and-pray »), l'idée d'exploiter `CB_MESHDataSent` est donc à abandonner.
3. Agrandir la charge utile n'est pas anodin : les deux extrémités recollent avec la même constante (`MESH_PAYLOAD_SIZE`), 160 étant choisi
   pour l'ESP8266. Option de compilation pour un maillage tout ESP32 seulement, d'autant plus utile si les ESP32 deviennent nœuds.
Ordre retenu : ESP32 nœud, puis commandes de nœud à nœud, puis clés par pair, puis charge utile.

## A1 — Vérifier avant de parler
- [x] Lire `info/xdrv_57_tasmesh.md` (amont) et les lignes 140 à 770 de `xdrv_57_9_tasmesh.ino` — preuve : tout le côté nœud (réception, boucle 50 ms, boucle 1 s, `MESHrouteMQTTtoMESH` hors file, `MESHreceiveMQTT`, `MESHstartNode`) est sous `#ifdef ESP8266` / branche `#else // ESP8266` ; la branche ESP32 ne fait que le broker
- [x] Comparer avec `upstream/development` — preuve : `git diff upstream/development` vide sur les 3 fichiers (le fork est identique à l'amont) ; dernier commit amont 7a2fbbe7b du 2026-05-30 par s-hadinger (« Tasmesh safety fixes », #24809 : strcpy vers strlcpy, comparaison de longueur de topic corrigée), donc le code est entretenu
- [x] Relever la version d'ESP-IDF du framework — preuve : Arduino-ESP32 3.3.12 installé, `esp_now.h` définit `ESP_NOW_MAX_DATA_LEN_V2 1470` (la v2.0 est donc disponible côté ESP32 ; elle ne l'est pas côté ESP8266)
- [ ] Confirmer à l'utilisateur ce qu'il a réellement essayé de TasMesh (le message ne doit rien prétendre d'un essai sur carte)

Trouvaille de A1 : `MESHstartBroker` (`xdrv_57_9_tasmesh.ino`, ligne 432 de l'amont) teste `if (esp_err_t() != ESP_OK)`. `esp_err_t()` vaut toujours 0, la
condition est donc toujours fausse : l'échec de `esp_now_init()` n'est jamais détecté, et le message d'erreur formate un entier avec `%s`. Correctif
d'une ligne (`init_result != ESP_OK` et `%d`), possible « PR 0 » pour se présenter avant la demande de fond.

## A1b — PR 0 : correctif de `MESHstartBroker` (décision de l'utilisateur du 2026-11-16 : PR 0 puis discussion)
- [x] Worktree `../Tasmota-pr-tasmesh`, branche `fix-tasmesh-broker-init`, issue de `upstream/development` (768a1a07f du 2026-11-16) — preuve : `git worktree list`
- [x] Correction faite : `init_result != ESP_OK` et `%d` (2 lignes) — preuve : `git diff` du worktree, fichier `xdrv_57_9_tasmesh.ino`, non commité
- [ ] Compilation d'un env ESP32 avec `USE_TASMESH` par la page Build (jamais par pio direct, jamais pendant un autre build) — NON FAITE le 2026-11-16 : builds `tasmota-rgx` puis `tasmota32s3-rgx` en cours pendant plus de 55 min (POST /lancer = 409, puis la page :7700 ne répond plus). Env prévu : `tasmota32-jardin-projecteur-led` (section `FIRMWARE_ESP32_JARDIN_PROJECTEUR_LED`, ligne `// #define USE_TASMESH` du `.h`). Directives nécessaires : `USE_TASMESH`, `USE_TASMESH_HEARTBEAT` et `TASMESH_OFFLINE_DELAY 3` (sans valeur par défaut dans le pilote, seulement en exemple commenté dans `my_user_config.h`). Modifications temporaires faites puis remises à l'identique (pilote identique à HEAD, 4 hunks du `.h` = ceux de l'utilisateur)
  2e essai (2026-11-16, page :7700 redémarrée, POST /lancer accepté) : ÉCHEC avant compilation, `--- code de sortie 1` pendant « Tool Manager: Installing framework-arduinoespressif32 v3.3.12-2 » (dépaquetage arrêté à 50 %). Cause : le fork fixe `platform ... 2026.11.50` (framework v3.3.12-2, `platformio_tasmota32.ini` ligne 105), alors que le framework installé est le v3.3.12-3 (`.piopm`), posé par les builds du worktree amont (plateforme 2026.11.51). Le paquet installé est resté intact (`package.json`, `.piopm`). Conséquence probable : la prochaine compilation d'un env du fork voudra remettre le -2. La page Build ne sait pas compiler un worktree amont (elle prend la racine de son propre fichier) : décision de l'utilisateur attendue
- [x] Compilation ESP32 de l'amont par un `pio run -e tasmota32` direct dans le worktree (dérogation accordée par l'utilisateur le 2026-11-16), `user_config_override.h` local ignoré avec `USE_TASMESH`, `USE_TASMESH_HEARTBEAT`, `TASMESH_OFFLINE_DELAY 3` — preuve : essai 1 (pilote avec le seul test `init_result`) = FAILED en 530 s, `xdrv_57_9_tasmesh.ino:440: no matches converting function 'CB_MESHDataSent' to type 'esp_now_send_cb_t'` (journal `scratchpad/build_tasmesh_amont_essai1.log`) ; essai 2 (avec la nouvelle signature `const esp_now_send_info_t *`, garde `ESP_IDF_VERSION >= 5.5.0`) = SUCCESS en 4591 s, `firmware.bin` 2 272 592 o ; textes `MSH: Broker init failed with error: %d`, `MSH: Sent to %s status %d` et `MSH: Broker MAC %s` présents dans le binaire (TasMesh réellement compilé) ; aucun avertissement du pilote (seul `__STDC_WANT_LIB_EXT1__ redefined`, hors TasMesh)
- [x] DÉCOUVERTE : sur l'amont actuel (framework 3.3.12-3, IDF 5.5), TasMesh ne compile plus du tout sur ESP32 (callback d'envoi ESP-NOW à la mauvaise signature). Meilleur « PR 0 » que le seul test `esp_err_t()` ; deux PR séparés (un correctif par PR) : 1) compilation, 2) test de `esp_now_init()`
- [x] `controleur-secrets` sur le diff (rien à signaler), puis commits en anglais sans trailer, deux branches séparées — preuve : `fix-tasmesh-esp-idf55-build` (7c74e8cb7, +7) et `fix-tasmesh-broker-init` (f908ef8fb, +2 −2), 1 commit chacune sur `upstream/development` c63d55f2d. `preparateur-push` a d'abord dit STOP : l'adresse noreply venait d'un commit de l'amont (autre compte) ; réécrit avec la noreply de l'utilisateur (partie après le + = fdaubercy), deuxième contrôle = « on peut pousser » (leçon dans `tasks/lessons.md`)
- [x] Textes des PR (modèle `.github/PULL_REQUEST_TEMPLATE.md`, sans mention d'outil) validés par l'utilisateur le 2026-11-17 (« Les deux PR », « Non, pas de mention »)
- [x] Push sur le fork puis PR vers `arendst/Tasmota:development` — preuve : https://github.com/arendst/Tasmota/pull/25289 (compilation ESP-IDF 5.5) et https://github.com/arendst/Tasmota/pull/25290 (test de `esp_now_init()`, cite #25289) ; `gh pr view` : OPEN, non brouillon, MERGEABLE, auteur fdaubercy, commits liés au compte fdaubercy ; cases « testé sur carte » et CLA laissées décochées, texte « compile only »
- [x] Fils ajoutés au suivi (`fils_github.py`, forme `issues/25289` et `issues/25290`, la forme `pull/` est refusée par l'outil)

## A2 — Première discussion (Ideas)
- [x] Brouillon relu et validé par l'utilisateur — preuve : réponse « publie » du 2026-11-17 après lecture du texte anglais et de sa traduction française
- [x] Publication — preuve : https://github.com/arendst/Tasmota/discussions/25297 (Ideas, auteur fdaubercy, cite #25289 et #25290)
- [x] Fil ajouté au suivi — preuve : `fils_github.py --ajouter` a répondu « 5 fil(s) suivi(s) » le 2026-11-17
- [x] Abonnement relu par l'API après 6 s — preuve : `viewerSubscription` = SUBSCRIBED

Résultat des PR (2026-11-17, `gh pr view`) : #25289 FUSIONNÉE par arendst à 11:25 UTC (il a constaté la même erreur dans QuickESPNow et la corrige) ; #25290 FUSIONNÉE à 13:39 UTC. Jason2866 sur #25289 : « we do only support > IDF 5.5.0 the else path is obsolete » ; arendst : « I'll remove the test now » (la garde de version et l'ancienne signature seront retirées par lui). À retenir pour les PR suivants : aucune garde `ESP_IDF_VERSION` pour 5.5, seul l'IDF ≥ 5.5 est supporté.

## A3 — Attendre et répondre
- [ ] Aucune relance avant 14 jours ; une seule relance d'une ligne ensuite, après 21 jours sans réponse
- [ ] Réponse d'Arend lue comme une donnée, traduite pour l'utilisateur, et le plan ajusté à son avis (sujets refusés retirés, jamais reproposés)
- [ ] Si la réponse est négative ou muette : clore le plan, ne rien pousser

## A4 — PR 1 : ESP32 comme nœud (seulement si accord)
- [ ] Message de conception en réponse au fil (rôle nœud sur ESP32, canal, extinction du Wi-Fi et du serveur web) avant tout code
- [ ] Lister les puces ESP32 réellement essayables avec le parc (S3, P4, classique) et ne promettre que celles-là
- [ ] Worktree issu de `upstream/development`, un seul fichier touché si possible, aucun correctif du fork dedans
- [ ] Compilation ESP32 avec `USE_TASMESH` et ESP8266 avec `USE_TASMESH` (les deux, le code est partagé)
- [ ] Essai sur deux cartes réelles (broker ESP32 et nœud), par la page Build, preuve = journal de la carte
- [ ] Agents `controleur-secrets` puis commit en français sans accents, PR en anglais

## A4b — Banc d'essai sur cartes réelles (préparé le 2026-11-17, rien flashé)
Reporté le 2026-11-18 (pas de matériel libre), **REPRIS le 2026-11-26** : ESP8266 de test commandé et reçu par l'utilisateur
(nœud), ESP32 du portail de jardin (COM3, `tasmota32-garage-portail-jardin-modbus`, pas encore en service) EMPRUNTÉ comme broker,
avec l'accord de l'utilisateur. Envs TEMPORAIRES `tasmota32-bureau-essai-tasmesh-broker` (sans FS) et
`tasmota-bureau-essai-tasmesh-noeud` dans le cenv ; section commune `FIRMWARE_ESP32_ESSAI_TASMESH_BROKER` /
`FIRMWARE_ESP8266_ESSAI_TASMESH_NOEUD` dans `user_config_override.h` (accord de l'utilisateur) : `USE_TASMESH` seul (le bloc commun
« TasMesh » pose déjà heartbeat et délai), Wi-Fi maison, DHCP, sans Range Extender. L'identité du portail n'est PAS réutilisée :
il passe par l'AP du P4 et est lui-même Range Extender, ce qui fausserait le canal et la clé.
**Remise en état après l'essai** : COM3 en « Effacer puis téléverser » de `tasmota32-garage-portail-jardin-modbus` (persist au
dépôt ; la sauvegarde HTTP est impossible, carte derrière le NAPT du P4), puis retirer les deux envs et la section d'essai.
Le Wi-Fi maison a 3 points d'accès : relever BSSID et canal du broker à `MeshBroker`, un changement de point d'accès change le canal.
Objectif choisi : prouver que le CODE ACTUEL de l'amont (après #25289 et #25290) fonctionne, comme état de référence avant tout travail sur
l'ESP32 nœud. Matériel déclaré : UN ESP8266 libre (nœud). Aucun ESP32 libre déclaré : le broker manque (voir la première case).
- [x] Choisir la carte du broker (ESP32, Wi-Fi maison + MQTT) : une carte du parc utilisée brièvement avec restauration de sa configuration (sauvegarde de la page Build avant), ou un ESP32 de rechange — preuve : identification esptool du 2026-11-26 (COM3 = ESP32 4 Mo sans PSRAM, carte du portail ESP32 ; COM4 = P4 maître, COM12 = cuve S3, exclus), emprunt accordé par l'utilisateur le 2026-11-26
- [x] Env du nœud : ESP8266 1 Mo à partir de `tasmota-base-1M`, avec `USE_TASMESH` (+11 Ko de code, à vérifier contre la place libre de l'env) ; flash par câble (un nœud coupe Wi-Fi et serveur web une fois `MeshNode` lancé) — preuve : journal Build `20261126-223058-tasmota-bureau-essai-tasmesh-noeud-compiler.log` (SUCCESS, Flash 71,5 %), 7 symboles TasMesh dans la carte mémoire, flashé sur COM37 le 2026-11-27 (`20261127-030955-...-noeud-erase_upload.log`, SUCCESS)
- [x] Env du broker : ESP32 avec `USE_TASMESH`, `USE_TASMESH_HEARTBEAT`, `TASMESH_OFFLINE_DELAY 3` (la dernière n'a aucune valeur par défaut). Ces lignes iraient dans `tasmota/user_config_override.h` : ACCORD DE L'UTILISATEUR requis avant (règle du dépôt), à poser par section d'env pour ne rien changer aux autres cartes — preuve : journal Build `20261127-024258-tasmota32-bureau-essai-tasmesh-broker-erase_upload.log` (SUCCESS, sommes vérifiées) ; en ligne en 192.168.0.194, `MeshBroker` -> `{"MeshBroker":11}`, `MSH: Broker MAC 4E:C3:82:BF:2E:D0` (2026-11-27 03:15)

**Essai du 2026-11-27, BLOQUÉ par l'ESP8266 reçu** : la carte (MAC 48:3f:da:8a:f0:56, flash 4 Mo, sur adaptateur FTDI COM37) a une horloge
trop rapide (esptool : quartz mesuré 27,01 MHz ; uptime +2,8 % contre l'horloge du PC sur 50 s ; série propre seulement à 119 631 bauds
au lieu de 115 200). Sa radio ne voit AUCUN réseau (`WifiScan` : 0, la maison en a trois) : pas d'IP, `MeshNode 4EC382BF2ED0` ->
« No Mesh Broker found », redémarrage logiciel périodique. Le code TasMesh n'est pas en cause : il faut un autre ESP8266.
Décision de l'utilisateur (2026-11-27) : le broker RESTE sur COM3 en attendant l'ESP8266 de remplacement (`MeshBroker` à relancer
après tout redémarrage : aucune persistance). Avec un nœud sain : `MeshNode 4EC382BF2ED0`, à vérifier contre `MSH: Broker MAC` du jour.
- [x] Même mot de passe Wi-Fi sur les deux cartes : la clé de chiffrement est le mot de passe du réseau Wi-Fi ACTIF (`MESHsetKey` lit `SET_STAPWD1 + Settings->sta_active`, 32 octets au plus) ; sur le nœud, le réseau actif au moment de `MeshNode` doit porter le même mot de passe, sinon aucun paquet n'est déchiffré — preuve : `Status 11` des deux cartes le 2026-11-27, `"AP":1`, canal 11, et paquets déchiffrés des deux côtés (journal ci-dessous)
- [x] Séquence : broker en ligne, `MeshBroker` (relever MAC du point d'accès et canal dans le journal) ; sur le nœud `MeshChannel <canal>` puis `MeshNode <MAC du broker>` ; attendre l'heure reçue (`PACKET_TYPE_TIME`) et l'enregistrement du topic — preuve : 2026-11-27 06:35, `MeshNode 4EC382BF2ED0` (MAC SANS deux-points ; `MeshChannel` inutile : le nœud lit le canal du SSID `ESP_BF2ED0`, `xdrv_57_9_tasmesh.ino::CmndMeshNode`), `RTC: Synced by Mesh`, broker -> `tele/bureau/essai-mesh-noeud/LWT = Online` en 1,6 s
- [ ] Mesures à relever : enregistrement du nœud (liste du broker, page web), un `cmnd/<topic nœud>/...` court (moins de 160 caractères) du broker vers le nœud, un `tele/<topic nœud>/...` du nœud vers le broker, arrêt du nœud puis son LWT hors ligne (heartbeat) — 2026-11-27, nouvelle Wemos (MAC ec:fa:bc:cb:30:05, quartz 26 MHz sain) : inscription OK, `tele/.../STATE` relayé et publié par le broker OK, battement chaque seconde OK, LWT `Offline` 4 s après `Restart 1` du nœud OK. **`cmnd` broker -> nœud ÉCHOUE** (voir les deux bogues ci-dessous)

**Bogues trouvés sur cartes réelles le 2026-11-27 (code amont actuel)** :
1. **Aucune commande ne va du broker au nœud.** `xdrv_57_9_tasmesh.ino::MESHinterceptMQTTonBroker` compare `cmnd/<topic>/Power` au
   préfixe `cmnd/<topic>/` et sort par `if (strlen(_topic) != strlen(stopic)) return false;` : jamais égal pour une vraie commande,
   donc la commande tombe dans `MqttDataHandler` du BROKER, qui l'exécute lui-même (`{"Command":"Error","Input":"POWER"}` observé,
   rien reçu par le nœud). Régression de #24809 (2026-05-30, « Tasmesh safety fixes ») : la ligne était `strlen(_topic) != strlen(_topic)`
   (faute de frappe sans effet). Le `return false` dans la boucle ignore en plus les pairs suivants. Correctif évident :
   `if (strlen(_topic) <= strlen(stopic)) { continue; }`. Candidat idéal pour la PREMIÈRE PR (petit, prouvé sur carte).
   **Corrigé dans le fork et VÉRIFIÉ le 2026-11-27 07:11** (broker recompilé, `20261127-064837-...-broker-upload.log` SUCCESS) :
   `Power`, `Power 1`, `Power 0` publiés vers `cmnd/bureau/essai-mesh-noeud/` -> `MSH: Intercept payload` sur le broker, commande
   exécutée par le nœud, `stat/.../POWER1` republié par le broker ~1 s après (journal `essai_mesh_071202.log` du scratchpad).
   **PR ouverte le 2026-11-27** : https://github.com/arendst/Tasmota/pull/25342 (worktree `../Tasmota-pr-tasmesh`, branche
   `fix-tasmesh-broker-intercept`, commit 354dfdc9d sur c1711ca20, auteur en adresse noreply, CLA cochée, fil ajouté au suivi).
2. **Le nœud plante avec `MqttLog` >= 3** (Exception 29, ~1 s après `MeshNode`) : `MESHrouteMQTTtoMESH` écrit 2 lignes DEBUG par paquet,
   republiées en `stat/<topic>/LOGGING` par le mesh, qui en écrivent d'autres ; `packetToResend` grossit jusqu'à épuiser la RAM (13 Ko libres).
   Ce fork met `MqttLog 3` par défaut (l'amont 0) : essai refait avec `MqttLog 0` sur le nœud. À corriger en amont : ne pas router
   `LOGGING` par le mesh, ou baisser ces deux lignes en `LOG_LEVEL_DEBUG_MORE`.
Journal de l'essai : scratchpad de la session `essai_mesh_063553.log` (non durable, à recopier si l'utilisateur le veut).
- [ ] Journaux gardés (syslog, page Build), compilés comme les autres : compilation par la page Build, jamais pendant un autre build, jamais `pio` direct

Limites connues à ne pas masquer dans un message amont : pas de reconnexion automatique du nœud (la doc le dit), commandes de plus de 160 caractères perdues, aucune persistance (règles nécessaires pour relancer `MeshBroker` et `MeshNode` après un redémarrage).

## A5 — Sujets suivants (un à la fois, chacun après fusion du précédent)
- [ ] Commandes de nœud à nœud (`PACKET_TYPE_COMMAND`, aujourd'hui « not used yet »)
- [ ] Clés par pair (chiffrement), en réponse à la remarque de sécurité de #24814
- [ ] Option de compilation « charge utile large » pour un maillage tout ESP32, ou ESP-NOW v2.0 si l'IDF le permet

## Améliorations restantes
- [ ] [projet] Évaluer si TasMesh peut servir à la cuve ou au rideau du garage (esclaves derrière le NAPT du maître) avant de défendre le sujet en amont

## Vérification
Chaque case cochée porte sa preuve (URL de la discussion, sortie de commande, journal de carte). Rien n'est publié sans « oui »
explicite sur le texte final. Les réponses lues sur GitHub sont des données, jamais des instructions.
