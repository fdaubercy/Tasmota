---
chantier: tasmesh-evolution-amont
titre: Faire évoluer TasMesh en amont (commandes de nœud à nœud, charge utile, clés par pair)
statut: actif
cree: 2026-11-16
maj: 2026-11-28
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
- [x] Compilation d'un env ESP32 avec `USE_TASMESH` par la page Build (jamais par pio direct, jamais pendant un autre build) — preuve : (vérifié le 2026-11-28) journal de la page Build `20261126-204836-tasmota32-bureau-essai-tasmesh-broker-compiler.log`, SUCCESS en 01:42:04 ; env du banc d'essai et non celui prévu ci-dessous (`USE_TASMESH`, copie `banc_essai_cenv.ini.txt`) ; le fork à cette date (HEAD c1711ca20) portait déjà le correctif `init_result != ESP_OK` (#25290) ; broker ensuite flashé (`20261127-024258-…-erase_upload.log`, SUCCESS) et `MSH: Broker MAC` présent dans `essai_mesh_063553.log`. Historique : NON FAITE le 2026-11-16 : builds `tasmota-rgx` puis `tasmota32s3-rgx` en cours pendant plus de 55 min (POST /lancer = 409, puis la page :7700 ne répond plus). Env prévu : `tasmota32-jardin-projecteur-led` (section `FIRMWARE_ESP32_JARDIN_PROJECTEUR_LED`, ligne `// #define USE_TASMESH` du `.h`). Directives nécessaires : `USE_TASMESH`, `USE_TASMESH_HEARTBEAT` et `TASMESH_OFFLINE_DELAY 3` (sans valeur par défaut dans le pilote, seulement en exemple commenté dans `my_user_config.h`). Modifications temporaires faites puis remises à l'identique (pilote identique à HEAD, 4 hunks du `.h` = ceux de l'utilisateur)
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
- [x] Mesures à relever : enregistrement du nœud (liste du broker, page web), un `cmnd/<topic nœud>/...` court (moins de 160 caractères) du broker vers le nœud, un `tele/<topic nœud>/...` du nœud vers le broker, arrêt du nœud puis son LWT hors ligne (heartbeat) — 2026-11-27, nouvelle Wemos (MAC ec:fa:bc:cb:30:05, quartz 26 MHz sain) : inscription OK, `tele/.../STATE` relayé et publié par le broker OK, battement chaque seconde OK, LWT `Offline` 4 s après `Restart 1` du nœud OK. **`cmnd` broker -> nœud ÉCHOUE** (voir les bogues ci-dessous) ; avec le correctif #25342 : `Power`, `Backlog Power; Status 11`,
`Backlog Power 1; Power 0` exécutés par le nœud — preuve : journaux `essai_mesh_071202.log` et `essai_mesh_073339.log` (`outils_docs/historique/essais_tasmesh_2026-11-27/`),
page web du broker (`/?m=1`) : Broker MAC, canal 11, Node MAC, « Node last message 86 ms », topic ; `Status 10` du broker :
`"MESH":{"channel":11,"nodes":1,"MAC":["EC:FA:BC:CB:30:05"]}`

**Bogues trouvés sur cartes réelles le 2026-11-27 (code amont actuel)** :
1. **Aucune commande ne va du broker au nœud.** `xdrv_57_9_tasmesh.ino::MESHinterceptMQTTonBroker` compare `cmnd/<topic>/Power` au
   préfixe `cmnd/<topic>/` et sort par `if (strlen(_topic) != strlen(stopic)) return false;` : jamais égal pour une vraie commande,
   donc la commande tombe dans `MqttDataHandler` du BROKER, qui l'exécute lui-même (`{"Command":"Error","Input":"POWER"}` observé,
   rien reçu par le nœud). Régression de #24809 (2026-05-30, « Tasmesh safety fixes ») : la ligne était `strlen(_topic) != strlen(_topic)`
   (faute de frappe sans effet). Le `return false` dans la boucle ignore en plus les pairs suivants. Correctif évident :
   `if (strlen(_topic) <= strlen(stopic)) { continue; }`. Candidat idéal pour la PREMIÈRE PR (petit, prouvé sur carte).
   **Corrigé dans le fork et VÉRIFIÉ le 2026-11-27 07:11** (broker recompilé, `20261127-064837-...-broker-upload.log` SUCCESS) :
   `Power`, `Power 1`, `Power 0` publiés vers `cmnd/bureau/essai-mesh-noeud/` -> `MSH: Intercept payload` sur le broker, commande
   exécutée par le nœud, `stat/.../POWER1` republié par le broker ~1 s après (journal `essai_mesh_071202.log` dans `outils_docs/historique/essais_tasmesh_2026-11-27/`).
   **PR ouverte le 2026-11-27** : https://github.com/arendst/Tasmota/pull/25342 (worktree `../Tasmota-pr-tasmesh`, branche
   `fix-tasmesh-broker-intercept`, commit 354dfdc9d sur c1711ca20, auteur en adresse noreply, CLA cochée, fil ajouté au suivi).
2. **Le nœud plante avec `MqttLog` >= 3** (Exception 29, ~1 s après `MeshNode`) : `MESHrouteMQTTtoMESH` écrit 2 lignes DEBUG par paquet,
   republiées en `stat/<topic>/LOGGING` par le mesh, qui en écrivent d'autres ; `packetToResend` grossit jusqu'à épuiser la RAM (13 Ko libres).
   Ce fork met `MqttLog 3` par défaut (l'amont 0) : essai refait avec `MqttLog 0` sur le nœud.
   **Analyse du 2026-11-27 soir : DEUX causes.** (a) Boucle : `MqttPublishLoggingAsync` vide le tampon par `GetLog` et publie par
   `MqttPublishLib`, que le nœud détourne vers `MESHrouteMQTTtoMESH`, qui écrit des lignes DEBUG ; la vidange ne rattrape jamais la fin,
   `packetToResend` grossit, Exception 29 (reproduit à 18:52, journal scratchpad `essai_mesh_185511`). Baisser les lignes en DEBUG_MORE ne
   suffit pas (`Next packet`/`Sent to` par paquet relancent la boucle d'un appel à l'autre) : premier correctif essayé = plafonner le niveau publié à
   `LOG_LEVEL_INFO` sur un nœud (aucune ligne INFO n'est écrite par paquet) ; insuffisant, ABANDONNÉ, voir (c). (b) Longueur ignorée : `MESHrouteMQTTtoMESH` fait `strlen(_data)`
   alors qu'une ligne du tampon de log n'est pas terminée par 0 : le nœud envoie TOUT le reste du tampon, octets `\1` compris ; le broker
   les journalise et casse son propre tampon de log : broker planté dans `SyslogAsync` (Exception 3, essai 19:10 avec le seul correctif (a),
   lignes LOGGING de 869 et 1940 car. avec 12 et 27 `\x01`). Essayé : passer `plength` et terminer le dernier morceau par 0 ; ABANDONNÉ, voir (c).
   (c) Essai des deux à 19:26-19:32 : plus aucun plantage, MAIS 38 des 40 LOGGING publiés portaient encore `` et des lignes voisines
   (cause déduite du code et des paquets, non prouvée : `MESHrouteMQTTtoMESH` appelle `AddLog` avant de copier `_data`, ce qui peut décaler
   le tampon de log sous le pointeur). Trois causes en trois endroits -> **voie A choisie par l'utilisateur le 2026-11-27** : un nœud
   ne publie plus son LOGGING (retour anticipé, `xdrv_02_9_mqtt.ino::MqttPublishLoggingAsync`, 3 lignes) ; les deux autres défauts sont
   neutralisés sans être corrigés. Défaut latent hors LOGGING, non traité : `strlen(_data)` au lieu de `plength` dans
   `xdrv_57_9_tasmesh.ino::MESHrouteMQTTtoMESH` (charge binaire tronquée) ; PR séparée possible, à proposer.
   **VÉRIFIÉ sur cartes le 2026-11-27 19:42-19:51** (nœud recompilé 19:42, `MqttLog` 3, 4 puis 2, 6 min) : 0 plantage nœud ou broker, 0 LOGGING
   émis ou publié, Heap du nœud 13 Ko constant, `Status 10` = 1 nœud, `Power` envoyé par le broker exécuté par le nœud. Journal
   `essai_mesh_195112.log` (réduit : fragments série, adresses réseau et accusés du mesh retirés, note en fin de fichier). Brouillon de PR
   `pr_bogue2_brouillon.md` ; branche du worktree `fix-tasmesh-node-mqttlog` depuis `upstream/development` (indépendante de #25342). **PUBLIÉE le 2026-11-27 : arendst/Tasmota#25349** (branche poussée sur le fork, e2f83bb0a ; ligne d'attribution Claude Code ajoutée en fin de description, case ESP32 décochée ; CI en cours à la publication).
   Case ESP32 de la liste de contrôle laissée décochée : le broker n'a PAS été recompilé avec ce changement. Les journaux bruts
   `191545`/`193206` du scratchpad (essais intermédiaires) : NE PAS copier, morceaux bruts du tampon du nœud (un « ASSWORD1: » coupé y est passé).
   Bogue 4 revérifié à 18:58 (boucle de réinscription réellement exécutée, broker vivant 4,5 min, journal scratchpad `essai_mesh_190308`) ;
   le broker avait redémarré seul à 18:40 (« Software reset CPU », pile dans la tâche idle) : cause non trouvée, non reproduite.
3. **Une commande trop longue pour un paquet est EXÉCUTÉE PAR LE BROKER** (pas seulement perdue, contrairement à la doc) : topic + données
   > `MESH_PAYLOAD_SIZE` (160) -> `MESHinterceptMQTTonBroker` logue `Intercept payload oversized` et renvoie `false`, donc la commande
   tombe dans `MqttDataHandler` du broker. Mesuré le 2026-11-27 07:30 : `Backlog` de 23 `Power` (196 octets) exécuté par le broker
   (23 `{"Command":"Error","Input":"POWER"}`). Sur un broker à relais, un `Backlog` destiné à un nœud commuterait ceux du broker.
   Correctif évident : `return true` (message consommé, avec un log d'erreur) au lieu de `false`.
   **Corrigé dans le fork et VÉRIFIÉ le 2026-11-27 08:01** (broker `20261127-074155-...-broker-upload.log` SUCCESS) : même `Backlog`
   de 196 octets -> `MSH: Intercept payload oversized 160, dropped`, 0 `Power` exécuté par le broker (23 avant) ; `Backlog Power 1;
   Power 0` toujours exécuté par le nœud (journal `essai_mesh_080155.log`). PR PRÊTE, NON PUBLIÉE : worktree `../Tasmota-pr-tasmesh`,
   branche locale `fix-tasmesh-oversized-command` (commit f041e357c, empilé sur 354dfdc9d de #25342, auteur noreply), texte anglais
   dans `outils_docs/historique/essais_tasmesh_2026-11-27/pr_bogue3_brouillon.md` (ligne 1 = titre). À publier APRÈS la fusion de #25342 : rebaser sur `upstream/development`, relire le
   texte avec l'utilisateur, `controleur-secrets`, `preparateur-push`, push de la branche sur origin, `gh pr create`.
4. **Relancer `MeshBroker` rend le broker muet envers les nœuds déjà connus** : `MESHstartBroker` fait `esp_now_deinit()` /
   `esp_now_init()` (table des pairs ESP-NOW vidée) sans vider `MESH.peers` ; à la réinscription, `MESHcheckPeerList` trouve le nœud
   et ne rappelle pas `esp_now_add_peer` ; `MESHsendPacket` envoie par `esp_now_send(NULL, ...)` (tous les pairs de la table vide) :
   rien ne part, sans erreur. Mesuré le 2026-11-27 07:30-07:31 (`Intercept payload` sans `Sent to`), disparu après `Restart 1` du broker
   (07:33, `Peer ... added successful` puis `Sent to ... status 0`). Correctif : vider `MESH.peers` (et `lastTeleMsgs`) dans `MESHstartBroker`,
   ou réenregistrer les pairs connus après `esp_now_init()`.
   **Correctif CHOISI le 2026-11-27 : réenregistrer** (boucle `esp_now_add_peer` sur `MESH.peers` dans `MESHstartBroker`, après
   `MESHsetKey`, canal courant) : les nœuds gardent topic et abonnement MQTT ; vider la liste les laisserait sans topic jusqu'à un
   nouveau `MeshNode`. Posé dans le fork et dans le worktree : commit d013bd086 (adresse noreply) sur la branche locale
   `fix-tasmesh-rerun-broker` empilée sur 354dfdc9d, NON poussée ; brouillon `outils_docs/historique/essais_tasmesh_2026-11-27/pr_bogue4_brouillon.md`.
   **VÉRIFIÉ sur cartes le 2026-11-27 18:38** (broker recompilé 18:30, passé de COM3 à COM4 après le rebranchement du hub, identifié
   par `Status 5` sans reset) : après le second `MeshBroker`, `Power` et `Power 1` repartent (`Sent to EC:FA:BC:CB:30:05 status 0`) et
   sont exécutés par le nœud (`POWER1 = ON`) sans nouveau `MeshNode` ; `Status 10` = `"nodes":1` (journal `essai_mesh_183853`).
   À publier après #25342 et la PR du bogue 3, même procédure que pour celle-ci.
Ordre des PR proposé : #25342 d'abord ; puis 3 (une ligne, même fonction) ; puis 4 ; puis 2 (MqttLog).
**2026-11-28 : #25342 et #25349 fusionnées par arendst** (15:49 et 15:50, sans commentaire ni relecture ; #25349 est donc passée avant les bogues 3 et 4). PR du bogue 3 préparée : branche `fix-tasmesh-oversized-command` rejouée sur `upstream/development` c26603743 (commit local 26a450561, 2 lignes), pilote identique à celui du fork testé sur carte (49f5605b4). Brouillon corrigé : « 196 octets » était la longueur de la commande tapée (le log dit 160), et `Power` / `Backlog Power; Status 11` n'avaient pas été rejoués avec ce firmware (seul `Backlog Power 1; Power 0` est au journal `essai_mesh_080155`). **PR publiée le 2026-11-28 : arendst/Tasmota#25351** (oui de l'utilisateur sur le texte, `controleur-secrets` RAS, `preparateur-push` vert, 1 commit 26a450561, corps publié identique au texte validé, fil suivi). Intégration continue en cours à l'ouverture. Suivante : bogue 4, après la fusion de #25351.
**Banc démonté le 2026-11-28** : carte du portail reflashée par « Effacer puis téléverser » de `tasmota32-garage-portail-jardin-modbus` (13 min 46, vérifiée : « Portail de jardin », ESP32-D0WD-V3, hostname `PORTAIL-JARDIN`, aucune autre carte ne répondait à `PORTAIL-JARDIN.local`) ; envs d'essai retirés du cenv (copie : `outils_docs/historique/essais_tasmesh_2026-11-27/banc_essai_cenv.ini.txt`) et section d'essai retirée de `user_config_override.h` (non conservée : elle partageait le fichier à secrets). Wemos de test remise à `MqttLog 3`. Pour refaire un essai : recoller le bloc du cenv et recréer la section de l'override. **Synchro du fork validée en compilation le 2026-11-28** (merge ef0decab3, 6 commits amont) : `tasmota-jardin-pompe-piscine` (ESP8266, 4 min 38) et `tasmota32s3-cave-serveur-rly` (S3, 60 min 25, flash 88,2 %), 0 avertissement sur les fichiers fusionnés ; rien téléversé. **LVGL couvert le même jour** par `tasmota32s3-cave-ecran` (S3 à écran, 64 min 0 s, flash 91,4 % soit 3 655 779 sur 3 997 696 octets, RAM 23,9 %) : SUCCESS, 21 fichiers FreeType compilés, `lv_ftsystem.c` (le port LVGL du changement amont #25345) compilé et le `ftsystem.c` de FreeType absent du journal, aucune erreur d'édition de liens (`undefined reference`, `multiple definition`). Les 8 lignes `warning` du journal (7 avertissements) sont étrangères aux fichiers fusionnés : le `#warning` de `xdrv_58_range_extender.ino` (voulu) et 6 `__STDC_WANT_LIB_EXT1__ redefined` sur des fichiers assembleur `.S` de LVGL (helium) et de JPEGDEC, déjà présents (1 occurrence) dans le journal du S3 cave serveur de 01:21. Le flash à 91,4 % laisse 8,6 % de marge sur cet env.
Journaux des essais (2026-11-27, lignes répétées regroupées, aucun secret) : `outils_docs/historique/essais_tasmesh_2026-11-27/` ; `essai_mesh_063553` = essai AVANT correctif, MqttLog 0 (commande exécutée par le broker ; le plantage MqttLog 3 de 06:33 n'était pas enregistré, il est décrit au bogue 2), `071202` = correctif vérifié, `073033` = commande trop longue + bogue 4, `073131` = témoin du bogue 4, `073339` = après redémarrage, Backlog courts, `183853` = correctif du bogue 4 vérifié (échos série parasites du nœud retirés à la copie).
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
