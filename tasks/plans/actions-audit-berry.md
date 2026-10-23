---
chantier: actions-audit-berry
titre: Plan d'action de l'audit Berry (propositions P2.1 à P10.7)
statut: actif
cree: 2026-10-22
maj: 2026-10-23
---
# Plan d'action de l'audit Berry (propositions P2.1 à P10.7)

## Contexte
Issu de l'audit `tasks/plans/audit-berry.md`, rapport `outils_docs/AUDIT_BERRY_2026-10.md` (constats,
preuves, filets et témoins de chaque proposition). **Rien n'est engagé** : l'utilisateur est seul juge
de ce qui sera mis en place (décision du 2026-10-21). Ce plan reste `en-pause` tant qu'il ne l'a pas
activé, et un lot n'est commencé que sur sa demande.

Règles pour chaque étape, une fois décidée :
- lire la proposition et son constat dans le rapport (identifiant entre parenthèses) ;
- poser d'abord le filet (banc existant, ou banc du lot A4) et son témoin négatif ;
- cocher seulement avec « — preuve : » (commit, banc vert + témoin rouge, relevé de carte) ;
- une étape refusée par l'utilisateur se coche avec « — preuve : refusée le AAAA-MM-JJ (raison) ».

Ordre conseillé : A1 → A2 → A3 → A4, puis A5/A6 ; A7, A10 et A11 seulement après les bancs de A4.

## A1 — Décisions à prendre (aucun code)
- [ ] P5.1 — Redémarrages programmés (heureReboot, timerRebootSansWifi) : voulus ou non ? S'ils le sont, corriger les lambdas ET le cron `*/300` (P10.5) ; sinon supprimer crons et clés (corrige N1, B7 ; cote G, effort faible, risque dec)
  - [x] Décision — preuve : voulus (« normalement ces deux timers fonctionnent… rends-les fonctionnels », 2026-10-23)
  - [x] Code — preuve : `globalFonctions.be` (lambda `/-> controleGeneral.heureReboot()`, `remove_cron` avant), `controleGeneral.be` (`surveilleWifi()` dans `every_second` au lieu du cron `*/300`) ; test `test_timers.be` du scratchpad 10/10, mutant (délai /10) rouge 4 échecs ; relecteur-berry : prêt, banc ModBus 309/309
  - [x] Désactivables sans redémarrer (demande du 2026-10-23) — preuve : `ReglageGlobal heureReboot [HH:MM|OFF]`, `ReglageGlobal timerRebootSansWifi [s|OFF]` (60 s minimum), `globalFonctions.armeRebootQuotidien`/`reglageReboot` ; test `test_reglage_reboot.be` du scratchpad 28/28, mutant (24:00 accepté, minimum 1 s) rouge 7 échecs ; README § commandes
  - [ ] Sur carte — modules solidifiés : build + flash du P4 nécessaires ; vérifier le reboot de 00:00 (`Status 1`, RestartReason) le lendemain
- [ ] P2.1 — Une S3 a-t-elle un écran ? Sinon retirer LVGL/OpenHASP de la base N16R8 (ou base S3 « sans écran ») (corrige E1 ; cote G, effort faible, risque moyen)
- [ ] P3.1 — Différentiel : `drivers.ModBus.activation` à OFF, ou embarquer la pile ModBus (corrige S1 ; cote L, effort faible, risque dec)
- [ ] P3.5 — Modules solidifiés inutiles : accepter, ou découper `socle` en `socle` + `reseau` (corrige S3 ; cote S, effort faible, risque dec)
- [ ] P4.4 — Cartes remplacées : geler ou retirer leurs fichiers ; cave : déployer la S3 ou donner un env à l'ancien code (ne PAS retirer le dossier *sauvegarde*) ; confirmer le statut réel de la cave et du différentiel (A1) (corrige D5, D6, D7 ; cote G, effort faible, risque dec)
- [ ] P6.2 — 6 clés `log` orphelines : créer leurs cibles ou retirer les clés (corrige L2 ; cote G, effort faible, risque dec)
- [ ] P2.9 — Ports COM propres à chaque poste : hors du `.ini` partagé (corrige E13 ; cote D, effort faible, risque dec)
- [ ] P5.15 — Une seule source pour chaque donnée de la fiche discovery (routagePort, id, IPAddress) (corrige N22 ; cote S, effort moyen, risque dec)
- [ ] P7.8 — IP fixe du PC syslog, ou syslog vers le Pi SERVEUR-BUREAU (corrige C9 ; cote D, effort faible, risque dec)
- [ ] P8.5 — ESP-NOW côté P4 : passerelle S3, ou ESP-NOW réservé aux S3 (après P8.4) (corrige T2 ; cote G, effort —, risque dec)
- [ ] P8.10 — Attendre esp-hosted-mcu#19 avant tout ESP-NOW sur le P4 ; pas de C6 reflashé (corrige T2 ; cote G, effort nul, risque dec)

## A2 — Réglages sur carte, sans code
- [x] P7.1 — `ReglageLog profil normal` sur chaque carte (P4 d'abord), puis aligner les persists du dépôt (corrige C1, C2 ; cote G, effort nul, risque nul)
  - [x] P4 — preuve : réponse `"profil":"normal"`, sorties serie/web/syslog info, mqtt erreur (2026-10-23 05:35) ; témoin : `stat/garage/LOGGING` muet depuis 05:35:09 (11 min sans message, sniffeur :7100)
  - [x] Cuve — preuve : réponse `"profil":"normal"`, mêmes sorties (2026-10-23 05:35)
  - [x] Rideau — hors ligne au relevé du 2026-10-23 (pas de réponse) : envoyer `ReglageLog profil normal` puis `ReglageLog tous info` à son retour
  - [x] Persists du dépôt des 3 cartes du garage — preuve : `diverses.logs.profil` = normal dans `data/garage/{tasmota32p4-serveur-modbus,tasmota32s3-capteurs-cuve-modbus,tasmota32s3-rideau-garage-modbus}/_persist.json` (41 lignes, JSON vérifié = effet des 2 commandes) ; puis, à la demande du 2026-10-23, les 5 autres persists à bloc de logs (différentiel, cave ESP32 et S3, grenier, ancien maître S3 : 64 lignes, même vérification) ; `cave/tasmota32-serveur-rly-sauvegarde` non touché (ancien code, sans `diverses.logs`)
- [x] P7.2 — `ReglageLog tous info` : seuils des modules à info (corrige C2, C4 ; cote G, effort nul, risque nul)
  - [x] P4 et cuve — preuve : réponse ReglageLog, les 14 (P4) et 13 (cuve) cibles à info (2026-10-23) ; mêmes clés dans les persists du dépôt (clés orphelines `drivers.KNX.log`, `modules.rideau.log` non touchées, comme sur la carte : voir P6.2)
  - [x] Rideau — avec P7.1, à son retour en ligne
- [x] P9.5 — Mesurer l'effet de P7.1/P7.2 sur le ramasse-miettes (`BRY: GC` sur 10 min) (corrige M4 ; cote S, effort nul, risque nul) — preuve : SerialLog 4 le temps de la mesure, lignes `GC from` comptées sur le pont (:7000 P4, :7001 cuve) ; avant : P4 16,7/min, cuve 13,0/min ; après : P4 18,8/min, cuve 14,4/min. **Pas de baisse** : le gain annoncé (5 à 10×) est réfuté. Les chaînes de log sont construites avant le filtre de seuil ; le gain viendra de P7.4 (garde `actif()` sur les chemins chauds)
- [x] P7.7 — Relever `ReglageLog` (sans argument) sur chaque carte : profil et seuils réellement en vigueur (corrige — ; cote D, effort nul, risque nul) — preuve : relevé du 2026-10-23 05:16 ; P4 : profil debug, 4 sorties debug, modules detail (leds info) ; cuve : profil debug mais mqtt à erreur, serie coupée, modules detail ; rideau : hors ligne

## A3 — Diagnostic de la fuite de RAM interne
- [ ] P9.1 — Fuite de RAM interne (~0,6 Ko/min, P4 + cuve) : observation 12 h, puis bissection un réglage à la fois (profil normal, RelaisPushMQTT, ModBus série/UDP, socket udp() par émission), retour arrière à chaque pas (corrige M1 ; cote G, effort moyen, risque faible)

## A4 — Bancs manquants (avant toute refonte)
- [x] P10.3 — Écrire `banc_boot.be` : vrais autoexec/configGlobal/configDevices/controleGeneral, persists réel, `{}`, et privé d'une clé (témoin) (corrige B8, B1 ; cote G, effort moyen, risque nul) — preuve : `python outils_docs/scripts_python/berry/banc_boot.py` code 0, 72 contrôles (64 ok, 8 CONNU : B1, B2, B3, MAC, ES8311), autoexec du P4 ENTIER ; témoin du cas 3 (30 échecs vus) ; mutant « ancienne lambda heureReboot » sur copie de data/fs → `BANC_BOOT: ECHEC`, code 1 (2026-10-23)
  - [ ] Défaut trouvé par le banc : ES8311 absent du bus I2C → `self.I2C` nil, `write_reg` lève `attribute_error`, l'autoexec s'arrête (historique et controleGarage non chargés) — `controleES8311.be:20-24`, `:77`, `:376-377` (même nature que B2)
  - [ ] Défaut trouvé par le banc : `serveur.adressMAC` jamais rempli (`globalFonctions.be:87-88` : `insert` ne remplace pas la clé vide `""` des 8 persists)
  - [x] Fragilité vue par le banc : `controleGarage.be:242` `["COUNTER"]["C1"]` sans garde (key_error dans web_sensor/json_append si le compteur manque) — preuve : COUNTER lu une fois et gardé, compteur cherché par son `id` (`C<id>`, avant toujours C1), « indisponible » affiché, erreur journalisée une fois jusqu'au retour ; `banc_boot` cas 5 (5 contrôles) vert, rouge sur l'ancienne version (`key_error - COUNTER`) (2026-10-23)
- [ ] P5.7 — Banc de la carte 16 relais + `try` autour de sa réception avec acquittement en `except` (corrige N7, B9 ; cote G, effort faible, risque faible)
- [ ] P10.4 — Banc des scripts de la cuve (niveau → volume → couleur) (corrige B10 ; cote L, effort moyen, risque nul)

## A5 — Défauts actifs : petits correctifs
- [ ] P5.2 — ImAlive : ranger la fiche via discoveryFonctions avec `memeValeur`, n'écrire que si elle change (corrige N2 ; cote G, effort faible, risque moyen)
- [ ] P5.3 — Cuve : un seul `_Scheme` par seconde partagé entre LEDs et surveilleRubans (corrige N3 ; cote G, effort moyen, risque moyen)
- [ ] P5.4 — P4 : CSS de la page d'accueil gardé en mémoire ou servi en statique (corrige N4 ; cote G, effort faible, risque faible)
- [ ] P9.2 — `/histo` : morceaux dans une liste puis `concat()` (corrige M2 ; cote S, effort faible, risque faible)
- [ ] P9.3 — `lisTable()` à la place des lectures triples de discovery.json, cache invalidé à l'écriture (corrige M3 ; cote S, effort faible, risque nul)
- [ ] P7.3 — 6 `print('Erreur…')` d'`except` → `xxxFonctions.log("…_ERREUR", LOG_LEVEL_ERREUR)` (corrige C3 ; cote G, effort faible, risque faible)
- [ ] P7.5 — Logs ponctuels : info→detail dans `web_sensor` du P4, ES8311 en erreur, `_ERREUR` dans 8 `except`, préfixes ; trancher « trame rejetée / délai isolé » (corrige C5, C6, C7, C8 ; cote G, effort faible, risque faible)
- [ ] P6.1 — Cible réglable `historique` (dans CIBLES, lieu `diverses.historique`) (corrige L1 ; cote G, effort faible, risque faible)

## A6 — Défauts latents : petits correctifs
- [ ] P4.1 — `loadBerryFile` : ne pas charger si l'activation vaut OFF (corrige D1 ; cote L, effort faible, risque faible)
- [ ] P5.8 — `diversFonctions.valeurScalaire(value)` pour les 5 sites ; humidité du P4 (corrige N8, N9 ; cote L, effort faible, risque moyen)
- [ ] P5.9 — configDevices : compteur analogique « réels », `%i` sur "ON", log des compteurs (corrige N10 ; cote L, effort faible, risque faible)
- [ ] P6.3 — Cache des seuils vidé après toute écriture du persist ; défaut d'un bloc absent non mis en cache (corrige L3, L4 ; cote L, effort faible, risque faible)
- [ ] P6.4 — Cible inconnue de `lieu()` journalisée une fois en erreur (corrige L5 ; cote L, effort faible, risque nul)
- [ ] P8.7 — Sans broker : `forceEnvoiParams` lancé depuis le secours C7 (corrige R2 ; cote G, effort faible, risque faible)
- [ ] P10.5 — `listeEtRepartitLesFichiers` : vérifier `mkdir` ; valider ou remplacer le cron `*/300` (corrige B4, B7 ; cote L, effort faible, risque faible)
- [ ] P2.2 — Coquille du `USER_TEMPLATE` du rideau (`1,1s]`) (corrige E2 ; cote L, effort faible, risque faible)
- [ ] P2.3 — Rebouclage de `increment_config_holder` à 65535 (corrige E5 ; cote L, effort faible, risque faible)

## A7 — Démarrage robuste
- [ ] P10.1 — Garde de tête des autoexec : `persist._p` et `diverses` testés avant toute lecture, avec trace (corrige B1 ; cote G, effort faible, risque faible)
- [ ] P10.2 — `try/except` journalisé autour de chaque `import controleXxx` ; `ReglageGlobal`/`ReglageLog` enregistrées avant `configGlobalByJson` (corrige B2, B3, B5 ; cote G, effort moyen, risque moyen)
- [ ] P4.2 — Autoexec commun : module `demarrage` solidifié, ~15 lignes propres par carte ; différentiel et grenier remis au modèle (corrige D2, D4 ; cote S, effort moyen, risque moyen)
- [ ] P4.3 — Séparer « charger ou non » et « supprimer le source » dans `compileModule`/`loadBerryFile` (corrige D3 ; cote D, effort faible, risque faible)

## A8 — Découverte des esclaves
- [ ] P8.6 — Péremption : Offline si aucun ImAlive depuis 2 × telePeriod, au lieu du reset unique (corrige R1, R3 ; cote G, effort moyen, risque moyen)
- [ ] P8.8 — `etatReseau()` : RgxClients × fiches par MAC, affiché sur `/discovery` (corrige R4, R6 ; cote L, effort moyen, risque nul)
- [ ] P8.9 — Mesurer latence aller simple, perte sur 1 h, délai de découverte (testeur :7400) (corrige A8.3 ; cote D, effort moyen, risque nul)

## A9 — Nettoyage : code mort et données mortes
- [ ] P5.10 — Lot code mort : fonctions sans appelant, branches inatteignables, blocs commentés, callbacks vides, `etatCapteurs`, `/wss`, `any_key` (corrige N11 et code mort ; cote L, effort faible, risque faible)
- [ ] P4.5 — 5 fonctions sans appelant de A4 (corrige D8 ; cote S, effort faible, risque faible)
- [ ] P4.6 — Clés mortes de `relaisLie`/`typeAction` retirées des persists (corrige D9 ; cote S, effort faible, risque faible)
- [ ] P4.7 — Schéma du persist normatif pour `relaisLie` (`delai` requis) (corrige D10 ; cote L, effort faible, risque nul)
- [ ] P9.6 — Alléger `modules.garage` (9,8 Ko de JSON) (corrige D1 (A9) ; cote S, effort faible, risque faible)
- [ ] P6.6 — Sauvegarde du persist harmonisée ; clés `nbLogsFiles`/`fileLogName` sans lecteur retirées (corrige L8 ; cote S, effort faible, risque faible)
- [ ] P5.6 — Ne plus forcer `tcp.activation` ; ne plus charger TCP sur la cave S3 (variante lourde : retirer le transport TCP, sur décision) (corrige N6 ; cote L, effort faible, risque faible)
- [ ] P2.4 — 8 sections orphelines de `user_config_override.h` ; bloc commun garage (corrige E3, E4 ; cote S, effort moyen, risque faible)
- [ ] P2.6 — Pre-script : listes (FAIT le 2026-10-21, `e26ff49d0`), garde contre le double accrochage, code mort (corrige E6, E7 ; cote S, effort faible, risque faible)
- [ ] P2.7 — Table de partitions S3 renommée d'après son contenu (corrige E11 ; cote D, effort faible, risque faible)
- [ ] P2.8 — `data/test.mp3` (3,3 Mo) sorti du dépôt (corrige E12 ; cote S, effort faible, risque nul)

## A10 — Factorisations (après les bancs de A4)
- [ ] P5.11 — Petits helpers : `relaisLie`, `deviceActif`, `readJson`, `macSansDeuxPoints`, `decoupeCommande` (corrige N12, N14, N16, N20 ; cote S, effort faible, risque faible)
- [ ] P5.12 — Factorisations : groupes de `changementEtatCapteur`/configDevices, itérateurs devices et fiches, `prepareTrame`/`decrypteMSG` (corrige N13, N15, N17, N18 ; cote S, effort moyen, risque moyen)
- [ ] P5.13 — Base commune aux drivers esclave ESP32 et carte 16 relais (après P5.7) (corrige N19 ; cote S, effort fort, risque fort)
- [ ] P5.14 — Module commun cuve/P4 : couleur, volume, page thermomètres, logs (corrige N21 ; cote S, effort moyen, risque moyen)
- [ ] P5.5 — Une socket par instance `CONTROLE_UDP` (corrige N5 ; cote S, effort faible, risque moyen)
- [ ] P9.4 — Map et bytes de tick réutilisés, sortie précoce si rien à lire (corrige M4 ; cote S, effort faible, risque faible)
- [ ] P7.4 — Garde `logFonctions.actif()` sur les chemins chauds ModBus/UDP (corrige C4 ; cote G, effort moyen, risque moyen)
- [ ] P3.2 — `import` local en tête de fonction pour l'auto-appel des modules (corrige S4 ; cote S, effort moyen, risque faible)
- [ ] P3.3 — `return controleXxx` en fin de chaque `controleXxx` (corrige S6 ; cote L, effort faible, risque nul)

## A11 — Build et solidification
- [ ] P2.5 — `pio-tools/` : revenir à l'amont pour les écarts de pure traduction (corrige E9 ; cote G, effort moyen, risque faible)
- [ ] P2.10 — Un seul mécanisme d'exclusion du LittleFS (corrige E10 ; cote S, effort moyen, risque moyen)
- [ ] P3.7 — Idem P2.10 côté solidification : `copy_fs_image` ou `post_esp32.py` seul (corrige S5 ; cote S, effort moyen, risque moyen)
- [ ] P3.4 — Solidifier `garageFonctions` puis `cuveFonctions`, puis les scripts de driver de carte (corrige candidats A3 ; cote S, effort moyen, risque moyen)
- [ ] P9.7 — Mesurer le gain de P3.4 (`Berry.HeapUsed`) (corrige A9 ; cote S, effort faible, risque nul)
- [ ] P3.6 — `carte_modules_berry.py` : modules de carte solidifiés, docstring (corrige S7 ; cote D, effort faible, risque nul)
- [ ] P9.8 — Avant de déployer le framework sur un ESP32 sans PSRAM : FTP/animation retirés, `envoiJson` découpé, discovery OFF (corrige M5, M6 ; cote L, effort faible, risque faible)

## A12 — Outillage et documentation
- [ ] P7.6 — Contrôle automatique de la charte des logs dans `verifie_berry.py` (avertissements) (corrige C10 ; cote D, effort moyen, risque faible)
- [ ] P10.7 — `fichier::fonction` au lieu de `fichier:ligne` ; contrôle des chemins et fonctions cités ; carte des modules déterministe (corrige B12, B14, B16, B19 ; cote D, effort moyen, risque nul)
- [ ] P10.6 — Docs : §7 de SOLIDIFICATION réécrit, ANALYSE marquée historique, « 13 pièges », README (leds, commandes), skill sans `logActivation` (corrige B11, B13, B15, B17 ; cote G, effort faible, risque nul)
- [ ] P6.5 — README : le profil fait foi sur les sorties, SERIALLOG_TIMER, portée de `actif()` (corrige L6, L7 ; cote D, effort faible, risque nul)

## A13 — Radio : ESP-NOW et TasMesh (exploration)
- [ ] P8.1 — Ne pas retenir TasMesh pour le garage (corrige T1, T2 ; cote S, effort nul, risque nul)
- [ ] P8.2 — TasMesh seulement pour de futurs capteurs ESP8266 sur batterie, broker ESP32/S3 (corrige T1 ; cote S, effort faible, risque faible)
- [ ] P8.3 — Signaler la régression T10 à l'amont après un essai (corrige T10 ; cote D, effort faible, risque nul)
- [ ] P8.4 — Essai borné ESP-NOW entre deux S3 (QuickEspNow) : latence, pertes, coexistence, tas (corrige T3-T9 ; cote S, effort moyen, risque faible)

## Améliorations restantes
- [ ] [projet] Ré-audit ciblé après les lots retenus (même grille, mêmes preuves), à noter dans `tasks/plans/audit-berry.md`

## Vérification
Chaque lot fini : `git status` ne montre que les fichiers du lot ; les bancs concernés (skill `bancs`) sont
verts avec leur témoin ; pour un lot qui touche une carte, relevé `Status 4` / `tele/STATE` avant et après.
