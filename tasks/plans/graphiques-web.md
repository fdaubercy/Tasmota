---
chantier: graphiques-web
titre: Graphiques des mesures dans les pages web des cartes S3/P4 (uPlot)
objectif: Afficher l'historique et le temps réel des mesures en graphiques dans les pages web des cartes S3/P4
statut: clos
cree: 2026-10-18
maj: 2026-10-20
source: resilient-soaring-stearns.md
---
# Graphiques des mesures dans les pages web des cartes S3/P4 (uPlot)

## Contexte
Suite de la réflexion du 2026-10-13 (mémoire `project_historique_capteurs`) :
- **Étage D (sur la carte)** : `data/fs/historiqueFonctions.be` (commit `cf53d7322`) est écrit et branché sur les
  6 cartes S3/P4 (bloc `diverses.historique` des persists, démarré par leurs `autoexec.be`). Il sert `/histo`
  en JSON : `p=liste` (mois disponibles), `p=jour` (24 h en RAM au pas de 5 min : `pas`, `t0`, `valeurs[série][point]`),
  `p=mois&m=AAAA-MM[-a]` (`lignes` : `[t, min1, moy1, max1, …]`). **Jamais exercé sur une carte.**
- **Étage E (sur le Pi)** : InfluxDB + Grafana installés, tableau `http://192.168.0.5:3000/d/historique-cuve`.
- **uPlot retenu** (commit `57dfc5d9f`, `outils_docs/apercus_graphiques/` : `uPlot.iife.min.js` 1.6.30, 49 Ko,
  `uPlot.min.css`, et `uplot.html` qui trace déjà moyenne + bande min/max sur deux axes).
- **Il manque tout l'affichage** : aucune page ne trace rien et uPlot n'est pas sur les cartes.

Décisions de l'utilisateur (2026-10-18) :
- une **page dédiée `/graphiques`**, ouverte par un **bouton** de la page d'accueil ; l'accueil, rafraîchi toutes les ~2 s, ne charge pas uPlot ;
- **uPlot servi par la carte** (LittleFS), sans dépendre d'Internet : les esclaves sont derrière le NAPT ;
- quatre vues : **24 h**, **mois (min/moy/max)**, **choix des séries** (deux axes Y), **lien Grafana** ;
- **premier essai réel sur le maître P4** : il a des mesures réelles (`ESP32.Temperature`, valeurs de la cuve relayées).
  La cuve n'a pas de capteurs branchés : ses courbes seront vides.

Contraintes techniques relevées :
- Berry ne peut pas poser d'en-tête de réponse (`webserver.header` lit la requête ; `content_open` n'accepte qu'un
  code et un type MIME). Le gzip passe donc par l'option amont **`UFILESYS_STATIC_SERVING`**
  (`tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino:950-1262` : commande `UfsServe <dossier>,<url>`, sert le
  `.gz` avec `Content-Encoding`, en-tête de cache ; +2,5 Ko de code). Solution de repli : une route Berry qui
  envoie le fichier non compressé, par morceaux.
- **Piège** : `gestionFileFolder.be:52-72` déplace tout fichier dont le nom contient `.js` vers `/sd/js/`, en le
  relisant **en mode texte**, quand une carte SD est présente. Un `uPlot.iife.min.js.gz` serait corrompu.
  Il faut un dossier et un nom à l'abri de cette règle.
- `historiqueFonctions.be` fait 489 lignes : la page va dans un **fichier de fonctions séparé** pour rester sous 500 lignes.
- **Décidé le 2026-10-18 : pas d'intégration à `controleWeb`/`webFonctions`.** Ils sont solidifiés (liste `socle`,
  `platformio_tasmota_cenv.ini:38-50`) : chaque retouche demanderait un firmware pour les 8 environnements. Ils sont
  aussi embarqués sur les ESP32 classiques, qui n'ont pas d'historique, et `controleWeb` est déjà à 447 lignes. Le
  partage entre environnements vient de `data/fs/` (commun à toutes les cartes) ; la page est générique : séries
  lues dans `/histo`, libellés, unités et lien Grafana lus dans le persist de chaque carte.
- Le P4 est aussi la carte du plan `modbus-garage` (A4 : observation d'1 h sans abandon). Un flash du P4 relance
  cette observation : il faut caler les flashs avec l'utilisateur.
- Pas de build en parallèle de celui de l'utilisateur, pas de cible PlatformIO pendant un build (`garde_build`).
- **Constaté le 2026-10-18 (A1)** : `/histo`, `/cm`, `/in`, `/cs` (toutes les routes à accès privilégié) exigent
  un en-tête `Referer` qui désigne la carte (`xdrv_01_9_webserver.ino:787-808`, `SetOption128` à 0). Sans lui,
  Tasmota coupe **sans rien répondre** (curl : code 52, « Empty reply »). Pour les essais en ligne de commande :
  `curl -H "Referer: http://192.168.0.43/" ...`. Un navigateur qui ouvre la page sur la carte envoie ce `Referer` :
  la page `/graphiques` n'est pas concernée. Ne pas passer `SO128 1` pour autant.

## A1 — Valider le socle /histo sur le maître P4 (prérequis)
- [x] LittleFS du P4 téléversé par l'utilisateur, au moment convenu avec le plan modbus-garage — preuve : déjà en place, rien à téléverser ; `/histo?p=liste` → 200 (P4 redémarré à 11:36:48, sans intervention de cette conversation)
- [x] Log `HISTORIQUE: Series enregistrees : [...]` relevé sur le P4, avec les 7 séries du persist — preuve : relevé par `/histo?p=liste` à la place (syslog arrêté, journalisation série désactivée) : `capteurHauteur_mV, compteur, hauteurEau, tauxRemplissage, temperature, temperatureESP32, volume`
- [x] `/histo?p=liste` et `/histo?p=jour` répondent en JSON valide : 7 séries, 288 points, `t0` cohérent avec l'heure UTC — preuve : `p=jour` 200, 10 268 o, 0,3-0,6 s ; 7 × 288 points ; t0 = 2026-10-17 09:55 UTC, dernier point 09:50 UTC pour une requête à 11:56 heure locale
- [x] Une heure plus tard, `/histo?p=mois&m=<mois courant>` contient au moins une ligne — preuve : `p=mois&m=2026-10` → 1 ligne (2026-10-18 08:00 UTC, temperatureESP32 28,4 / 29,32 / 29,4) ; l'heure en cours au redémarrage de 11:36 est perdue, comme prévu
- [x] Heap libre relevé avant et après une requête `p=jour`, sans chute durable — preuve : `Status 11` heap 235 Ko avant, après 3 requêtes `p=jour` et 6 s plus tard ; Berry HeapUsed 116-117 Ko
- [x] Faux zéros de la cuve écartés de l'historique du P4 : sans mesure, `sensorsCuve` publie `0` (`controleGarage.be:297-310`) — preuve : sous-étapes ci-dessous
  - [x] Filtre `controleGarage.filtreHistorique` : séries `sensorsCuve.*` à nil tant que la mesure de l'esclave 1 n'est pas `valide` (`defaillant`, `inconnu` ou pas encore relue) — preuve : `verifie_berry.py` 0 erreur ; banc jetable berry.exe (scratchpad `banc_filtre/test.be`) 5/5 OK
  - [x] Observé sur le P4 après téléversement du LittleFS : `/histo?p=jour` donne `null` (et non 0) pour les séries `sensorsCuve.*` et `temperature` — preuve : 1er pas clos après le redémarrage (17:00:09) : `hauteurEau`, `tauxRemplissage`, `volume`, `capteurHauteur_mV`, `temperature` = `null` alors que `Status 10` publie 0 ; `temperatureESP32` = 29,2 ; `compteur` = 0.0 (vrai compteur natif `COUNTER.C1`, non filtré). Les heures 10 h-15 h du 18/10 en flash gardent les zéros d'avant le filtre
- [x] `DS18B20.Temperature` du P4 à 0.0 (id `C1041600F6FBFF28`) : sonde réelle ou absente ? À trancher par l'utilisateur ; si elle est absente, retirer la série `temperature` du persist du P4 ou la filtrer — preuve : c'est le thermomètre virtuel « T° Eau de Cuve » (`thermometre1`, 1312, relayé de la cuve, publié par `controleGarage.json_append`) ; sonde non branchée, à garder dans le persist (décision de l'utilisateur) → filtrée comme `sensorsCuve.*` (`controleGarage.mesureVirtuelleValide`), banc jetable `banc_filtre` 7/7

## A2 — Servir uPlot depuis la carte
- [x] Choix tranché entre `UFILESYS_STATIC_SERVING` + `UfsServe` et une route Berry : taille du firmware P4 avec et sans le define, essai de `UfsServe` (gzip, cache, accès sans mot de passe ou non) — preuve : **route Berry retenue**, sans build. `UFSServe` trouve le `.gz` mais l'envoie sans `Content-Encoding` (`xdrv_50_filesystem.ino:1163-1205` ; seul `xsns_62_esp32_mi.ino:2925` pose cet en-tête), sans `Cache-Control` (`nullptr`, l. 1240-1243) et active CORS pour tout le serveur. Gzip impossible sans modifier du C amont ; pas de cache HTTP depuis Berry (`WSHeaderSend` pose no-cache) → cache dans le `localStorage` (A3)
- [x] uPlot 1.6.30 (`.js` et `.css`, non compressés) placé dans un dossier du LittleFS protégé de `gestionFileFolder` ; source dans le dépôt, hors du `data_dir` d'une carte — preuve : `data/sd/js/uPlot.iife.min.js` (49 672 o) et `data/sd/css/uPlot.min.css` → `/sd/js/`, `/sd/css/` (`gestionFileFolder` ne trie que la racine) ; route `/graphiques?f=uplot.js|uplot.css` dans `data/fs/graphiquesFonctions.be`, déclarée par `HISTORIQUE_WEB` ; banc jetable berry.exe (`banc_envoi`) : fichier reçu identique (`cmp`), 25 morceaux de 2 Ko, 404 pour un fichier inconnu ou absent
- [x] Fichiers exclus du LittleFS des ESP32 classiques (`custom_files_exclude` de `platformio_tasmota_cenv.ini`, comme `historiqueFonctions.be`) — preuve : uPlot (js, css) et `graphiquesFonctions.be` ajoutés aux listes de `tasmota32-cave-serveur-rly` et `tasmota32-bureau-interrupteur-differentiel` ; la liste noire s'applique désormais aussi au `copytree` de `data/sd` et `data/json` (`pre_utilitaires_platformio.py`, `ignore_exclus`), essai à part : copie « classique » sans uPlot, copie S3 avec
- [x] Vérifié sur le P4 après téléversement du LittleFS : `curl -H "Referer: http://192.168.0.43/" "http://192.168.0.43/graphiques?f=uplot.js"` → 200, 49 672 o identiques ; puis `uPlot` défini dans le navigateur — preuve : 200, 49 672 o en 0,34 s, `cmp` IDENTIQUE ; vue mois tracée par uPlot dans Chrome headless (page réelle, relais local qui ajoute le `Referer`)

## A3 — Page /graphiques et bouton d'accueil
- [x] Pas de nouveau driver : le driver existant `HISTORIQUE_WEB` (`historiqueFonctions.be:255`) reçoit `web_add_main_button` (bouton « Graphiques ») et la route `/graphiques` ; le bouton n'apparaît donc que là où l'historique est actif, quel que soit l'environnement — preuve : `historiqueFonctions.be` (route + `web_add_main_button`, 496 lignes), `verifie_berry.py` 0 erreur ; bouton à voir sur la carte en A6
- [x] Fichier de fonctions `data/fs/graphiquesFonctions.be` (non solidifié, S3/P4 seulement, déjà exclu des ESP32 classiques), importé seulement par la route `/graphiques` (`check_privileged_access`) : aucune RAM tant que la page n'est pas ouverte ; il sert déjà uPlot (A2), il lui reste la page — preuve : `graphiquesFonctions.page` (102 lignes) ; `graphiques.js` ajouté aux listes noires des 2 ESP32 classiques
- [x] uPlot mis en cache dans le `localStorage` (clé versionnée `uPlot-1.6.30`, lecture et écriture sous try/catch) : redemandé à la carte seulement au changement de version ou si le stockage est indisponible — preuve : banc headless (scratchpad `banc_page`) : 2 chargements du même profil → 1 seule requête `f=uplot.js` ; anciennes clés `uPlot-*` purgées à l'écriture ; cache illisible → clé oubliée
- [x] Page au gabarit Tasmota (`content_start`, `content_send_style`, `content_stop`) ; logique dans `data/sd/js/graphiques.js`, envoyée par `gestionFileFolder.readFileByLineAndContentSend` (comme `main.js`, `controleWeb.be:368`) — preuve : page générée par le vrai `graphiquesFonctions.page()` dans berry.exe (faux webserver), rendue par Chrome headless : axes lisibles en thème sombre (variable `--c_txt`), trou de mesure visible ; `node --check` OK
- [x] La page lit `/histo` (`p=jour` ; `p=liste` viendra avec le sélecteur de mois en A4) ; un historique absent (404) ou des séries vides affichent un message clair — preuve : banc headless, 5 scénarios : JSON réel du P4 (7 séries tracées), synthétique avec trou, 404 « historique pas encore démarré », `t0` null « aucun pas clos », uPlot absent « HTTP 404 » ; `fetch` envoie bien le `Referer` exigé par Tasmota
- [x] Logs du module conformes à la charte (`logFonctions.log`, préfixe `GRAPHIQUES:`, pas d'`info` dans un callback fréquent) — preuve : `GRAPHIQUES:` en `debug` à l'ouverture de la page, `GRAPHIQUES_ERREUR:` en `erreur` (fichier absent, échec d'envoi) ; relecture `relecteur-berry` en A5

## A4 — Les quatre vues
- [x] Vue 24 h : abscisses `t0 + i*pas`, `null` tracé comme un trou, heure locale (Intl fr-FR) — preuve : banc headless (scratchpad `banc_page`, page générée par le vrai `graphiquesFonctions.page()`) : axe « 12:00 / sam. 17/10 », légende « Heure », valeurs au format fr ; JSON réel du P4 tracé
- [x] Vue mois : sélecteur rempli par `p=liste`, moyenne + bande min/max (modèle : `apercus_graphiques/uplot.html`), mois `-a` lus avec `seriesFichier` — preuve : banc headless (scratchpad `banc_page`, page générée par le vrai `graphiquesFonctions.page()`) : mois réel du P4 (2026-10), mois fabriqué avec trou de 30 h (coupure visible, bande min-max), « Août 2026 (ancienne liste de séries) » tracé avec sa propre série ; sélecteur « 24 dernières heures / Octobre / Septembre / Août »
- [x] Choix des séries : cases à cocher mémorisées dans `localStorage` (lecture et écriture sous try/catch), deux axes Y répartis par unité — preuve : banc headless (scratchpad `banc_page`, page générée par le vrai `graphiquesFonctions.page()`) : 3 séries pré-décochées absentes du tracé, 7 cases ; axes aux unités les plus partagées (°C à gauche, mV à droite sur le P4), « sans unité » en dernier ; couleurs stables par série
- [x] Libellés et unités : bloc facultatif `diverses.historique.affichage` (`{"serie": {"libelle", "unite"}}`) ; à défaut, déduits du nom (temperature → °C, hauteur → cm, volume → L, taux → %) — preuve : `affichage` (+ `facteur`, pour `tauxRemplissage` 0-1 → %) posé dans les persists du P4 et de la cuve ; légende du banc « Remplissage (%) », « Température de l'eau (°C) »… ; série sans réglage (`ancienneSerie`) affichée sous son nom
- [x] Lien Grafana : clé facultative `diverses.historique.grafana` (URL), bouton masqué si elle est absente ; posée dans les persists du P4 et de la cuve — preuve : `http://192.168.0.5:3000/d/historique-cuve?var-appareil=%topic%` dans les 2 persists, `%topic%` remplacé par le topic de la carte (`graphiquesFonctions.urlGrafana`, banc : `var-appareil=garage`) ; bouton visible même si l'historique n'a pas démarré
- [x] Mise en page utilisable sur téléphone (largeur du graphique recalculée au redimensionnement) — preuve : capture dans un cadre de 412 px (Chrome headless ne descend pas sous 500 px de fenêtre) : barre repliée, deux axes, légende repliée, hauteur 240 px ; `setSize` au redimensionnement (temporisé 200 ms)
- [x] `outils_docs/schemas/persist.schema.json` régénéré (`berry/genere_schema_persist.py`) pour les nouvelles clés — preuve : +25 lignes (`affichage`, `grafana`) ; `--valide` : cuve 0 erreur ; P4 1 erreur préexistante sans rapport (`drivers.leds.environnement.leds` : `ledRGB` manquante)

## A5 — Bancs et relecture avant l'essai réel
- [x] Banc hors carte : petit serveur Python qui sert la page et des JSON `/histo` fictifs (24 h avec trous, mois, mois `-a`, 404, séries vides) ; rendu vérifié dans Chrome headless (`--dump-dom`, sans `--virtual-time-budget`) — preuve : `outils_docs/scripts_python/berry/banc_graphiques.py` + `.be` + `bouchons_berry/graphiques/` : 42 contrôles, code de sortie 0 (Berry : envoi d'uPlot identique octet par octet, 404, accès refusé, exception en plein envoi, Grafana `%topic%`, page et `window.GRAPHIQUES` échappé, filtre P4 8 cas ; Chrome : 8 scénarios). `--virtual-time-budget` gardé : pas de flux SSE ici. Mutants détectés (`%topic%` non remplacé → 3 ECHEC ; réponse non fermée après exception → 1 ECHEC). Ajouté à la skill `bancs`
- [x] `verifie_berry.py` vert sur les `.be` touchés (hook `verifie_berry_edition`) — preuve : `graphiquesFonctions.be`, `historiqueFonctions.be`, `controleGarage.be` : 3 fichiers, 0 erreur
- [x] Agent `relecteur-berry` passé sur le diff Berry, remarques traitées — preuve : aucun bloquant ; 2 « à corriger » traités (réponse fermée après exception, cible de log `serveurWeb` et style « … ! ») ; suggestions appliquées : `</` échappé dans `window.GRAPHIQUES`, `modules.find(...)` dans le filtre (plus d'exception qui ferait perdre la mesure de la minute) ; chacune couverte par un contrôle du banc

## A6 — Essai réel sur le P4, puis les autres S3
- [x] Mesures de la cuve simulées pendant les essais (sa sonde et son ADS1115 ne sont pas branchés) : émulation de l'esclave 1 par le sniffeur ModBus (http://127.0.0.1:7300, `emulation_modbus.py` : thermomètre 1312 et analogique, valeurs éditables), **cuve retirée du bus RS485** pendant l'essai (deux esclaves à l'adresse 1 = collisions) ; la cuve passe à `valide`, les courbes se remplissent, puis repassent à `null` à l'arrêt de l'émulation — preuve : cuve à l'adresse ModBus **2** (la 1 est la carte relais), débranchée et éteinte ; émulation 22:02-22:25 et 22:35-23:00 : P4 `valide`, valeurs émulées reprises (ex. 23,6 °C / 1 500 mV / 48 cm / 2 894 L) ; arrêt → `inconnu` en ~130 s (22:27:18, 23:02:19) ; `/histo?p=jour` (version « séries découvertes ») : pas de 23:00 rempli, 23:05-23:20 à `null` pour `DS18B20.Temperature` et `sensorsCuve.*`, 23:25 rempli à la reprise. Défaut trouvé : 2 séries découvertes brutes (`TasmotaSlaveModBus.TasmotaSlaveModBus1.ANALOG.A1`, `…Temperatures.DS18B20-1.Temperature`), doublons non filtrés, gardaient des valeurs périmées → `"exclues": ["TasmotaSlaveModBus"]` dans le persist du P4 (dépôt + carte, à chaud à 23:38) : 5 séries, pas de 23:35/23:40 remplis
- [x] P4 : bouton visible, `/graphiques` affiche la vue 24 h, la vue mois, les cases et le lien Grafana — preuve : accueil avec `action='/graphiques'` ; vue 24 h juste après le redémarrage : « Aucun pas de mesure encore clos… » (attendu) ; vue mois « Octobre 2026 (moyenne horaire, bande min-max) », 7 cases, axes °C / mV (capture scratchpad `a6/page_p4_mois.png`) ; `window.GRAPHIQUES.grafana` = `…var-appareil=garage`, bouton affiché. Passé par 2 redémarrages : ancien `.bec` en cache puis persist réécrit par `System#Save` (lessons.md 2026-10-18), autoexec du P4 et de la cuve corrigés
- [x] P4 : heap libre relevé pendant le chargement de la page ; l'accueil (`/?m=1`) ne charge toujours pas uPlot — preuve : `Status 11` heap 239 Ko avant, 206 Ko pendant l'envoi simultané de la page, du CSS et d'uPlot, 239 Ko juste après et 5 s plus tard ; `/` et `/?m=1` : 0 occurrence de « uplot »
- [x] Déployé sur les autres cartes S3 (cave serveur-rly, grenier, rideau, serveur-modbus S3, cuve) ; cuve vide attendue tant que ses capteurs ne sont pas branchés — preuve : déployé et coché par l'utilisateur (2026-10-18)
- [x] Documentation : section « Graphiques » dans `outils_docs/README.md`, ligne dans la carte des documents de `CLAUDE.md`, mémoire `project_historique_capteurs` mise à jour — preuve : `outils_docs/README.md` § « Les graphiques des mesures (cartes S3/P4) » + entrée d'index ; `CLAUDE.md` ligne « Graphiques des cartes S3/P4 » ; mémoire et `MEMORY.md` à jour

## A7 — Bouton Grafana sur les ESP32 classiques
Les ESP32 classiques (`tasmota32-cave-serveur-rly`, `tasmota32-bureau-interrupteur-differentiel`) n'ont ni historique
local ni page `/graphiques`, mais Grafana historise déjà leurs mesures (Node-RED, abonnement `tele/#`). Il leur manque
seulement un accès depuis leur page d'accueil. Ancienne amélioration « Courbes pour les ESP32 classiques », passée en
étape le 2026-10-18.
- [x] Vérifier dans Grafana que la variable `appareil` du tableau `historique-cuve` liste les classiques, et sous quel nom (topic seul ou chemin complet) ; en déduire le motif d'URL (`%topic%` ou autre) — preuve : `SHOW TAG VALUES ... WITH KEY = "appareil"` (InfluxDB `Iot`) : `bureau/pc`, `cave/serveur-rly-cave`, `garage`, `jardin/cuve`… = topic complet → motif `%topic%` inchangé. Mais les panneaux du tableau ne lisent que des champs de cuve (`sensorsCuve_*`, `DS18B20_Temperature`) : vides pour la cave et le bureau
- [x] Choisir l'accroche du bouton, sur un module chargé par les classiques : de préférence non solidifié ; `controleWeb` (solidifié) demande l'accord de l'utilisateur et une recompilation — décision de l'utilisateur — preuve : `controleWeb` retenu par l'utilisateur le 2026-10-18 (le bureau ne charge aucun module non solidifié) : bouton commun à toutes les cartes, actif après recompilation de leur firmware
- [x] Choisir la clé du persist qui porte l'URL (`diverses.historique.grafana` des S3/P4 réutilisée, ou une clé hors `historique`) ; bouton masqué si elle est absente ; pas de doublon avec le bouton de `/graphiques` sur les S3/P4 — preuve : `diverses.historique.grafana` réutilisée (déjà au schéma) ; bouton seulement si `historique.activation` ≠ `ON` ; banc : clé absente, vide, bloc `null` ou non-map → rien ; persists réels du P4 et de la cuve → pas de bouton en double
- [x] Bouton « Historique (Grafana) » sur l'accueil (`web_add_main_button`), `%topic%` remplacé par le topic de la carte, sans RAM ajoutée tant que la clé est absente — preuve : `controleWeb.boutonGrafana` (`data/fs/controleWeb.be`), appelée en fin de `web_add_main_button` ; sortie immédiate sans import tant que la clé est absente ; `'` et `<` neutralisés dans `onclick` ; `verifie_berry.py` 0 erreur ; relecteur-berry : aucun bloquant, 1 « à corriger » traité (bloc `historique` `null` ou non-map cassait l'accueil : cas ajouté au banc, rouge puis vert)
- [x] Clé posée dans les persists de la cave et du bureau ; `outils_docs/schemas/persist.schema.json` régénéré — abandonnée : clé NON posée (décision de l'utilisateur du 2026-10-18, « mécanisme seul ») : le tableau `historique-cuve` n'a que des panneaux de cuve, leurs courbes y seraient vides ; schéma inchangé, la clé y figure déjà (A4)
- [x] Vérifié : banc (Berry) et essai sur une carte classique (bouton visible, lien qui ouvre le bon appareil dans Grafana) ; README § « Les graphiques des mesures » complété — preuve : sous-étapes ci-dessous (banc vert, essai sur le P4 : même module solidifié que sur les classiques)
  - [x] Banc et README — preuve : `banc_graphiques.py` code 0, 51 contrôles (9 pour le bouton) ; témoin `controleWeb.be` de HEAD → 3 ECHEC, mutant sans la condition d'activation → 2, sans neutralisation → 1 ; README § « Carte sans historique local » ; skill `bancs` à jour
  - [x] Essai sur carte : firmware recompilé (n'importe quelle carte : le module est solidifié) + clé posée à la main le temps de l'essai sur une carte sans historique actif ; bouton visible, lien vers le bon appareil — preuve : 2026-10-19, P4 192.168.0.43 (firmware du 2026-10-19 05:00, après le commit 15a3985cd ; les classiques cave et bureau étaient muets) ; historique rendu inactif EN RAM le temps de l'essai (`Br diverses['historique']['activation']='OFF'`, seul `demarre` lit cette clé), puis remis à `ON` (relu : `{"Br":"ON"}`) ; accueil actif : 0 bouton Grafana, 1 « Graphiques » ; inactif : `window.open("http://192.168.0.5:3000/d/historique-cuve?var-appareil=garage")` ; `garage` = valeur de la variable `appareil` dans InfluxDB `Iot` ; tableau derrière la connexion Grafana (302 vers /login), affichage non vu par Claude

## A8 — Séries génériques : chaque carte trace ses propres capteurs, sans liste écrite à la main
Demande de l'utilisateur (2026-10-18) : le module doit s'adapter seul à la carte et à ses capteurs. On trace seulement
les **mesures** : analogiques, températures, humidité…, qu'elles viennent de capteurs réels ou de capteurs virtuels
(valeurs reçues par ModBus). **Relais et entrées numériques ne doivent jamais apparaître.**

Décisions de l'utilisateur (2026-10-18) :
- **Source = le JSON SENSOR filtré** (`tasmota.read_sensors()`, mode auto actuel), sans s'appuyer sur les
  déclarations `modules.*.environnement` du persist.
- **Compteurs** : un **débitmètre** est tracé en **débit** (variation par unité de temps) ; un **compteur d'énergie**
  (type compteur électrique) est tracé en **valeur corrigée dans l'unité calculée** (impulsions → kWh…).
- **Mesures internes de la carte** (température ESP32, RSSI, mémoire libre) : **aucune par défaut**. On les ajoute
  à la main dans le persist (`@rssi`, `@heap`, `ESP32.Temperature`).
- **Réglages** (exclure, renommer, unité, facteur, type de compteur) : dans le **bloc central `diverses.historique`**
  (prolongement de `affichage`), et non sur l'entrée de chaque capteur ni dans la page web.
- **RAM (décision de l'utilisateur, 2026-10-18)** : le persist est chargé entier et en permanence en RAM (31 Ko sur
  disque pour le P4). Il ne garde donc que ce que la relève de chaque minute utilise : `exclues`, `ajouts`,
  `compteurs`, `seriesMax`. Ce qui ne sert qu'à la page (`affichage`, `groupes`, et les compositions de l'A9) va
  dans **`/json/graphiques.json`** de la carte (source : `data/<lieu>/<carte>/graphiques.json`, rangé dans `/json/`
  au démarrage), lu seulement à l'ouverture de la page. Exception : `grafana` reste dans le persist, car le bouton
  des ESP32 classiques (A7, `controleWeb`, solidifié) le lit à cet endroit.
- **Page dans des fichiers (remarque de l'utilisateur, 2026-10-18)** : le squelette HTML et le style quittent
  `graphiquesFonctions.page()` pour `/sd/html/graphiques.html` et `/sd/css/graphiques.css`, comme les autres pages
  du dépôt (moins de chaînes en RAM dans le module).

Ce qui s'y oppose aujourd'hui (constaté le 2026-10-18) :
- `historiqueFonctions.nombre()` convertit `ON`/`OFF` en 1/0 (`historiqueFonctions.be:283`). Le mode auto retient donc
  les `Switch<n>` et les états de boutons que `controleGeneral.json_append` (`controleGeneral.be:377`) ajoute au JSON.
- Sur le maître, le bloc `TasmotaSlaveModBus` (`modBus_TasmotaSlaveModBus.be:648`) mélange `ANALOG`, `COUNTER`,
  `Temperatures` (mesures) et `Switchs` (entrées des esclaves).
- `IGNORES` n'exclut que 6 clés. `ESP32.Temperature` passe le filtre, alors que les internes doivent être exclues par défaut.
- Les séries sont figées 2 min après le démarrage : une valeur ModBus qui arrive plus tard n'est jamais retenue.
- Les unités sont devinées côté navigateur, d'après le nom (`graphiques.js:107`). En mode auto, ce nom est un chemin
  (`AM2301.Humidity`) : il faut le deviner d'après la **dernière clé** (`Temperature`, `Humidity`, `Pressure`,
  `Illuminance`, `A<n>`…).
- `historiqueFonctions.be` fait 496 lignes : la découverte ira dans un fichier séparé si elle déborde. Le code ne doit
  jamais être comprimé pour tenir sous les 500 lignes (lessons.md, 2026-10-18).

- [x] Points ouverts tranchés par l'utilisateur — preuve : sous-étapes ci-dessous, réponses du 2026-10-18
  - [x] Compteur sans réglage : **exclu**. Il n'apparaît qu'une fois son type précisé — preuve : décision de l'utilisateur, 2026-10-18
  - [x] Type et conversion d'un compteur : **bloc `diverses.historique.compteurs`** = `{"COUNTER.C1": {"type": "debit"|"energie", "impulsionsParUnite": n, "unite": "L/min"|"kWh"}}` — preuve : décision de l'utilisateur, 2026-10-18
  - [x] P4 et cuve : **passage en auto**. La liste `series` explicite disparaît des deux persist ; `affichage` et le filtre des faux zéros de la cuve (`controleGarage.filtreHistorique`) sont conservés — preuve : décision de l'utilisateur, 2026-10-18
  - [x] Séries apparues après le démarrage : **nouvelle découverte à chaque fin d'heure**. Si la liste change, le fichier du mois repart avec le nouvel en-tête et l'ancien est mis de côté en `-a` (mécanisme existant). Les 24 h en RAM repartent à vide — preuve : décision de l'utilisateur, 2026-10-18
  - [x] Valeurs calculées par les modules (`sensorsCuve.niveauCuve.*` : hauteur, volume, taux) : retenues, mais **dans un graphique à part sur la même page**, et **seulement sur la cuve et sur son maître** (le P4, qui reçoit aussi ces données) — preuve : décision de l'utilisateur, 2026-10-18 (corrige ma proposition de les mêler aux autres mesures)
- [x] Graphiques par défaut : clé `groupes` = `{"Cuve": ["sensorsCuve.niveauCuve"]}` (titre → préfixes de chemins), dans `graphiques.json` (décision RAM). Les séries d'un groupe ont leur propre graphique ; toutes les autres vont dans le graphique « Mesures ». La clé n'est posée que pour la cuve et le P4 ; ailleurs, la page n'affiche qu'un graphique. Le mV brut du capteur (`sensorsCuve.valeursAnalogiques.*`) reste dans « Mesures » (choix de Claude : c'est la valeur du capteur analogique, pas une valeur calculée). C'est la composition de départ, que l'utilisateur peut ensuite modifier depuis la page (A9) — preuve : `graphiques.json` du P4 et de la cuve (`groupes` : `Cuve`) ; banc Chrome « jour » : 2 graphiques « Mesures » (sonde, ANALOG de l'esclave, mV) et « Cuve » (hauteur, remplissage, volume) ; « mois -a » : un seul graphique non vide, sans titre de bloc
- [x] Filtre de découverte : seules les feuilles numériques (`int`/`real`) sont retenues ; `ON`/`OFF` et le texte ne sont plus convertis. Sont exclus `Switch*`, `Button*`, `POWER*`, `Switchs`, `relais`, `Id`, les unités (`TempUnit`…), les internes (`ESP32`, `@rssi`, `@heap`) et les compteurs sans réglage — preuve : `historiqueSeries.be` (`admissible`, `decouvre`) ; `banc_historique.be` §1-2 : 11 + 9 contrôles, dont le JSON SENSOR RÉEL du P4 (Status 10, 18/10 19:12) → `DS18B20.Temperature` + 4 séries `sensorsCuve.*`. Ajout de **`Shutter*`** aux exclus (choix de Claude : `Shutter1.Position/Direction/Target/Tilt` du P4 = état du volet, un actionneur)
- [x] Exclusion par l'utilisateur : clé `diverses.historique.exclues` (liste de chemins ou de préfixes). Ajout explicite d'une série que le filtre écarte (interne : `ESP32.Temperature`, `@rssi`, `@heap`) par une clé `diverses.historique.ajouts` (choix de Claude : la liste `series` disparaît avec le passage en auto). **Le P4 perd sa série `temperatureESP32` sauf si elle est ajoutée ainsi**. `@power<n>` est refusé (relais) — preuve : `banc_historique.be` §1-2 : `exclues` par segment entier, `ajouts` (internes, `Shutter1.Position`), `@power1` refusé. Le P4 n'a PAS `ESP32.Temperature` dans `ajouts` (internes : aucune par défaut, décision de l'utilisateur)
- [x] Compteurs : conversion débit / énergie appliquée à la mesure avant enregistrement ; une remise à zéro du compteur (redémarrage) ne doit pas produire de pic de débit négatif — preuve : `historiqueSeries.convertit` ; `banc_historique.be` §3 : énergie 2500/1000 = 2,5 ; débit 1 L/min puis 0,5 L/min (2 min) ; remise à zéro → nil ; mutant sans garde → ECHEC. `COUNTER.C1` du P4 (« Consommation électrique ») non réglé → exclu : `impulsionsParUnite` à fournir par l'utilisateur
- [x] Redécouverte à chaque fin d'heure : liste comparée à la précédente, nouvel historique créé seulement si elle change ; log `info` du changement (ajouts et retraits) — preuve : `historiqueFonctions.choisitSeries` / `releve` ; `banc_historique.be` §4 : même heure → liste inchangée ; heure suivante → AM2301 ajouté, nouvel historique, log info « Nouvelles series » ; série disparue → gardée ; séries déjà dans le fichier du mois reprises au démarrage ; fichier mis de côté en `-b` quand `-a` existe. Mutants sans redécouverte / sans anciens / suffixe fixe → ECHEC
- [x] Capteurs virtuels ModBus du maître : mesures de `TasmotaSlaveModBus.*.ANALOG`, `.COUNTER` et `.Temperatures` retenues, `Switchs` exclus ; libellé par défaut tiré du `name` de l'esclave dans le persist — preuve : `banc_historique.be` §1-2 : `ANALOG.A1` et `Temperatures.DS18B20-1.Temperature` d'un esclave retenus, `Switchs.*` et `COUNTER` non réglé écartés ; banc Chrome : libellé « Capteurs Cuve ModBus ANALOG A1 » (`name` de `TasmotaSlaveModBus1`, `graphiquesFonctions.nomsEsclaves`)
- [x] Unités devinées d'après la dernière clé du chemin (Temperature → °C, Humidity → %, Pressure → hPa, Illuminance → lx, `A<n>` → mV…), le bloc `affichage` restant prioritaire — preuve : 2026-10-19, décision de l'utilisateur : `A<n>` → mV SEULEMENT relayé par ModBus (`TasmotaSlaveModBus.*.ANALOG.A<n>`), l'ANALOG natif (ADC brut) reste sans unité ; `devineUnite` (`data/sd/js/graphiques.js`) ; scénario Chrome « unites » (8 séries : °C, %HR imposé par `affichage`, hPa, lx, sans unité, mV, V, cm) vert ; témoin (version commitée) et mutants « affichage ignoré », « Illuminance retirée » détectés ; README complété
- [x] Nouvelles clés dans tous les `_persist.json` qui portent `diverses.historique` (valeur explicite, fins de ligne conservées) ; `persist.schema.json` régénéré — preuve : 6 persist (cave S3, grenier, rideau, S3 serveur-modbus, P4, cuve) : `series` → `exclues: []`, `ajouts: []`, `compteurs: {}` ; `affichage` du P4 et de la cuve déplacé dans leur `graphiques.json` ; fins de ligne LF conservées ; `genere_schema_persist.py` régénéré, `--valide` P4, cuve, cave S3 : 0 erreur
- [x] Bancs : découverte sur des JSON SENSOR réels de chaque carte (P4, cuve, rideau, cave S3, grenier), témoin négatif (un `Switch1`, un `POWER`, un `Switchs` d'esclave, `ESP32.Temperature` ne doivent PAS sortir), compteur débit/énergie, mutants ; `banc_graphiques.py` vert — preuve : `banc_graphiques.py` code 0, 100 contrôles (dont `banc_historique.be` 40) ; témoin HEAD de `historiqueFonctions.be` → 5 ECHEC ; ancien `graphiques.js` → 12 ECHEC ; 5 mutants détectés sur copie ENTIÈRE de `data/fs` (copie intacte verte). JSON réels : P4 seulement (cuve et rideau derrière le NAPT du P4) ; les autres cartes sont couvertes par l'essai réel
- [x] `relecteur-berry` sur le diff, puis essai réel : la liste des séries relevée sur chaque carte S3/P4 ne contient ni relais ni entrée — preuve : 2026-10-19, relecture de `de0bd5dd3` : 5 « à corriger » traités, chacun avec son contrôle dans `banc_historique.be`, rouge avant (6 ECHEC + plantage) et vert après : filtre insensible à la casse et étendu (Relais, Relays, relay<n>, Power<n>, Entrees, inputs, switch, PWM, Dimmer ; ENERGY.Power et PowerFactor restent des mesures), `exclues` prioritaire sur `ajouts`, sources internes limitées à @rssi/@heap, `seriesMax` mal typé → 12, allocation impossible → `chemins` remis à nil et historique recréé à la relève suivante ; `banc_graphiques.py` vert ; suggestions non appliquées (log à 64 feuilles, garde NTP, carte sans capteur relue chaque minute) ; essai réel = celui du P4 et de la cuve ci-dessus
  - [x] Relecture `relecteur-berry` — preuve : aucun bloquant ; 2 « à corriger » traités (fichier de `graphiques.json` refermé après une exception, `nomsEsclaves` sans exception si un niveau du persist n'est pas une map) ; suggestions appliquées : réglages mal typés → `{}`, `seriesMax` borné à 1, séries déjà enregistrées prioritaires à la troncature, log « au-delà de seriesMax » en debug, ancien historique lâché avant d'allouer le nouveau ; chacune couverte par un contrôle (`banc_graphiques.py` code 0, 100 contrôles)
  - [x] Essai réel : LittleFS téléversé sur le P4 puis les S3 ; log `HISTORIQUE: Series enregistrees` de chaque carte sans relais, entrée, volet ni interne ; page à deux graphiques sur le P4 et la cuve — preuve : sous-étapes ci-dessous, P4 et cuve vérifiés ; rideau et autres S3 écartés par décision de l'utilisateur (2026-10-19)
  - [x] P4 (192.168.0.43) — preuve : 2026-10-19, `Br import historiqueFonctions return historiqueFonctions.chemins` = `DS18B20.Temperature` + 4 `sensorsCuve.*` (ni relais, entrée, volet ni interne ; `TasmotaSlaveModBus` exclu par réglage de l'utilisateur) ; page servie avec `groupes` « Cuve » → « Mesures » + « Cuve »
  - [x] Cuve (COM12, 192.168.4.2 derrière le NAPT du P4) — preuve : 2026-10-19 18:41, LittleFS téléversé par l'utilisateur (uptime 8 min 45) ; par le pont série 7001 : séries = 4 `sensorsCuve.*` (DS18B20 non branchée : absente, normal) ; `/sd/js/graphiques.js` 28 263 o = dépôt, `echarts.min.js.gz` présent, uPlot absent, `/json/graphiques.json` avec le groupe « Cuve » → deux graphiques (« Mesures » : capteur de hauteur ; « Cuve » : hauteur, remplissage, volume). Log `Series enregistrees` émis avant la connexion (même liste que `chemins`) ; page non vue (joignable seulement depuis le Wi-Fi du P4)
  - [x] Rideau, S3 serveur-modbus, S3 serveur-rly (grenier en sommeil) : LittleFS téléversé, séries sans relais, entrée, volet ni interne — abandonnée : écartés par décision de l'utilisateur (2026-10-19, « oui coche ») ; NON vérifiés sur carte, leur LittleFS n'a pas été téléversé avec l'A8 ; l'exclusion du volet est vérifiée en réel sur le P4 (`Shutter1`)

## A10 — Page qui suit l'heure réelle, échelles Y ajustées, passage à ECharts
Demandes de l'utilisateur (2026-10-18) :
- l'échelle des temps ne suit pas l'heure réelle, il faut recharger la page pour voir les dernières données : le
  graphique doit se mettre à jour régulièrement ;
- les échelles Y doivent s'adapter aux valeurs min et max de chaque capteur ;
- **utiliser ECharts au lieu d'uPlot, version complète** (décision de l'utilisateur, 2026-10-18, préférée à une
  version réduite et au maintien d'uPlot). Elle remplace le choix d'uPlot du 2026-10-13 et prépare l'A9 (types
  courbe, barres, escalier, aire et combiné fournis par ECharts).

Causes mesurées sur le P4 (2026-10-18, 22:35:42) : dernier point daté 22:30. Un pas (5 min) n'est livré qu'à sa
clôture, et le point porte l'heure de son début. La page ne lit `/histo` qu'au chargement : aucune relecture.

- [x] Carte : `/histo?p=jour` livre aussi le pas en cours (`tEncours`, `encours` = moyenne des mesures déjà reçues, `null` sans mesure) — preuve : `historiqueFonctions.jsonEnCours` ; `banc_historique.be` §5 rouge avant (3 ECHEC), vert après
- [x] ECharts complet, version épinglée, empreinte SHA-256 notée, stocké **compressé** (gzip) dans `data/sd/js/` ; — preuve : `data/sd/js/echarts.min.js.gz` (ECharts 6.1.0, 368 202 o, sha256 en tête de `graphiquesFonctions.be`), uPlot retiré (`git rm`), cenv mis à jour ; banc Berry : envoi en 180 morceaux, reçu identique octet par octet ; Chrome : « ECharts demandé une seule fois (localStorage) », « ECharts absent : message HTTP 404 »
  servi tel quel par la route `/graphiques?f=` (Berry ne peut pas poser `Content-Encoding`), décompressé par le
  navigateur (`DecompressionStream`) et gardé dans le `localStorage` (clé versionnée). uPlot retiré. Fichiers exclus
  du LittleFS des 2 ESP32 classiques
- [x] `graphiques.js` réécrit pour ECharts : « Mesures » + groupes ; axe des temps jusqu'à maintenant ; pas en cours — preuve : `banc_graphiques.py` vert (jour, mois, mois_a, masquees : titres, séries, légende, axe X jusqu'à l'heure du navigateur, axes Y par unité ajustés, plancher à zéro, bande min-max) ; mutants « axe X figé » et « échelle sans plancher » détectés
  en dernier point ; un axe Y par unité ajusté au min/max des valeurs (`scale: true`), pas sous zéro si tout est
  positif ; trous = pas sans mesure ; vue mois avec bande min-max ; libellés, unités, facteurs, esclaves ModBus comme
  aujourd'hui ; séries masquées mémorisées ; zoom et infobulle ; thème clair/sombre de Tasmota
- [x] Relecture périodique (`rafraichissement` de `graphiques.json`, 60 s par défaut, 10 s au minimum ; mois en — preuve : scénario Chrome « rafraichi » (≥ 2 lectures de p=jour sans recharger) ; mutant « relecture coupée » détecté ; banc Berry : `periode` bornée
  cours toutes les 15 min), mise à jour sans recréer le graphique, rien quand l'onglet est caché, une lecture à la fois
- [x] **Tous les graphiques en temps réel** (décision de l'utilisateur, 2026-10-18 : valeurs instantanées, interrogation — preuve : `banc_historique.be` §6 vert (valeurs, énergie, null, filtre et lecture en exception, cache 4 s, cache lâché au changement de séries) ; Chrome : défaut 10 s (1 lecture en 8 s), « arrêt » et 2 s mémorisés, valeur directe en dernier point ; mutants « direct jamais ajouté » et « cadence ignorée » détectés. Temps réel limité à la vue 24 h et au mois en cours (un mois clos n'a pas de présent)
  de la carte toutes les **10 s** par défaut, **cadence modifiable dans la page par une liste déroulante** : 2, 5, 10,
  30, 60 s ou « arrêt » ; choix de Claude : mémorisée dans le navigateur, défaut `direct` de `graphiques.json`) : route `/histo?p=direct` → `{"t", "valeurs"}`, valeur actuelle de chaque série (mêmes chemins, filtres des
  modules et conversion « énergie » appliqués ; débit = celui du pas en cours, la conversion à état n'est pas rejouée) ;
  `read_sensors()` mis en cache 4 s (il appelle le `json_append` de chaque driver : coûteux) ; la page ajoute ces points
  au bout de chaque courbe, dans toutes les vues, et les remplace par l'historique à sa relecture ; rien n'est stocké
  en plus sur la carte
- [x] Banc Chrome adapté (ECharts dessine dans un canvas : état lu par des attributs `data-` posés par la page) ; — preuve : `banc_graphiques.py` : 28 contrôles de rendu + 100 Berry, BANC_GRAPHIQUES: OK en 2 min 11 ; 5 mutants de `graphiques.js` tous détectés (MUTANTS: OK) ; blocage de Chrome = processeur saturé par un build, bancs lancés hors build
  blocage de Chrome sans interface avec une page qui relit en boucle compris et contourné ; témoin (ancienne page)
  et mutants
- [x] README, `CLAUDE.md`, mémoire, skill `bancs` à jour ; `relecteur-berry` sur le Berry touché — preuve : README § graphiques (temps réel, liste Direct, ECharts compressé), `CLAUDE.md` carte des documents, skill bancs, mémoire `project_historique_capteurs` ; relecteur : 3 défauts de `historiqueFonctions.be` corrigés, chacun avec son contrôle rouge puis vert
- [x] Essai réel sur le P4 : premier chargement (durée, heap), courbe qui avance seule, échelles ajustées — preuve : 2026-10-19, P4 192.168.0.43 : ECharts 200, 368 202 o en 1,37 s, `cmp` identique au dépôt ; page = `graphiques.js` du dépôt, `bibliotheque` echarts-6.1.0, `direct` 10, liste `g_direct` présente ; `/histo?p=direct` répond (5 séries, valeurs actuelles), `p=jour` porte `tEncours`/`encours` ; heap 203 Ko après chargement ; page validée à l'écran par l'utilisateur

## A9 — Page composable : l'utilisateur crée, modifie et supprime ses graphiques
Demande de l'utilisateur (2026-10-18) : sur la page `/graphiques`, l'utilisateur ajoute autant de graphiques qu'il
le souhaite, choisit leur type et les séries qu'il y place. Dépend de A8 : les séries proposées sont celles que la
découverte a retenues.

Décisions de l'utilisateur (2026-10-18) :
- **La composition est enregistrée sur la carte**, dans son persist, par un bouton « Enregistrer ». Le PC et le
  téléphone voient donc les mêmes graphiques.
- **Types** : courbes, barres, escalier, aires, et **graphique combiné**, c'est-à-dire un type par série dans le même
  graphique (par exemple des barres pour un compteur et une courbe pour une température).
- **Tous les graphiques sont modifiables**, y compris ceux prévus par le persist (« Mesures », « Cuve ») : ils ne
  servent que de point de départ. Un bouton « Rétablir » revient à la composition par défaut.
- **La période (24 h ou un mois) est propre à chaque graphique.**

Choix de Claude (à contester), revus le 2026-10-19 pour ECharts et le temps réel (A10) :
- Clé `graphiques` de **`/json/graphiques.json`** (et non du persist : décision RAM de l'A8) = liste de
  `{"titre", "periode", "type", "series"}` :
  - `periode` : `"jour"` (24 h glissantes, temps réel), `"mois"` (mois en cours, temps réel, suit le changement de
    mois) ou `"AAAA-MM"` (un mois figé, éventuellement `-a`, `-b`) ;
  - `type` : `"courbe"`, `"barres"`, `"escalier"` ou `"aire"` ;
  - `series` : `"autres"` (toutes les séries placées dans aucun autre graphique : un graphique ainsi réglé reçoit seul
    les séries découvertes plus tard) ou liste de `{"chemin", "type"?}` ; le `type` d'une série prime sur celui du
    graphique (graphique combiné).
  Clé absente = composition par défaut : « Mesures » (`autres`) + un graphique par groupe de `groupes` (A8), en 24 h et
  en courbes ; « Rétablir » supprime la clé. À la première modification, les groupes deviennent des listes explicites.
- Envoi par `POST /graphiques`, champ de formulaire `composition` (JSON ; `null` = Rétablir) : Tasmota découpe déjà un
  corps de formulaire en paramètres (`webserver.arg`).
- Une série peut figurer dans plusieurs graphiques. Ordre changé par des boutons monter/descendre (pas de glisser-déposer :
  plus lourd sur téléphone).
- En vue mois : bande min-max pour les courbes et les aires ; barres et escalier sur la moyenne horaire seule.
- Lectures mutualisées : une lecture de `/histo` par période affichée, une seule lecture `p=direct` pour tous les
  graphiques qui suivent l'heure ; la liste « Direct » (A10) reste commune à la page.
- Limites contrôlées par la carte (frontière système) : corps de 8 Ko au plus, au plus 8 graphiques et 12 séries par
  graphique, titre de 1 à 60 caractères, chemins de 120 caractères au plus, types et périodes validés, clés inconnues
  écartées. Un chemin inconnu est gardé, la page le signale par « absente ».
- `graphiques.js` dépasse déjà 500 lignes : l'édition va dans un fichier à part, `data/sd/js/graphiques_edition.js`.

- [x] Route d'écriture `POST /graphiques` (accès privilégié, `check_privileged_access`) : champ `composition` validé — preuve : 2026-10-20, `graphiquesFonctions.enregistre`/`traiteComposition`/`valideComposition`/`ecrisReglages` + route POST dans `historiqueFonctions.web_add_handler` (GET et POST coexistent : emplacements indexés par chemin ET méthode, `xdrv_52_3_berry_webserver.ino:99-106`, 10/32 utilisés) ; `banc_graphiques.be` §6 rouge avant (31 ECHEC + plantage) puis vert : corps valide, clés inconnues écartées, 20 refus (taille, JSON, limites, types, périodes), accès refusé, Rétablir, exception au renommage et AVANT la réponse (500, témoin rouge), fichier illisible non écrasé, `</script>` échappé
  puis écrit dans la clé `graphiques` de `/json/graphiques.json`, autres clés (`affichage`, `groupes`...) conservées,
  **sans toucher au persist** (fichier temporaire puis renommage : une coupure ne laisse pas un fichier à moitié écrit).
  Réponse JSON `{"ok", "graphiques"}` ou `{"erreur"}` ; rien n'est écrit si le corps est invalide ou trop gros ; log
  `info` de l'enregistrement
- [x] Page en mode lecture : un bloc par graphique (titre, sélecteur de période propre, légende), lectures de `/histo` — preuve : `graphiques.js` + `graphiques_trace.js` ; Chrome : « composition » (4 graphiques, ordre, périodes propres, une lecture p=jour et une du mois pour 4 graphiques), « mois » (composition enregistrée), « mois_a » (période changée dans le graphique), « jour » (une lecture p=jour pour 2 graphiques)
  mutualisées (une seule lecture par période, même si plusieurs graphiques l'utilisent), temps réel partagé
- [x] Types de tracé ECharts : courbe, barres, escalier (`step`), aire (`areaStyle`), combiné (type par série) ; axes Y — preuve : Chrome « composition » : rendu réel `bar`, `bar`+`line` (combiné), `line:area`, `line:step` ; bande min-max pour l'aire en mois, pas pour l'escalier ni en 24 h ; mutants « type de série ignoré », « barres en ligne », « bande pour l'escalier » détectés
  par unité dans chaque graphique ; bande min-max en vue mois pour courbes et aires
- [x] Mode édition (bouton « Modifier ») : ajouter un graphique, le renommer, le supprimer, le monter ou le descendre, — preuve : `graphiques_edition.js` ; Chrome « edition » (Ajouter, titre, type, série, Enregistrer → POST exact de la composition explicite, Referer, page redessinée, message gardé), « retablir » (POST null → défaut) ; mutants « message effacé par le temps réel », « autres ne retire pas » détectés
  choisir son type, sa période, ses séries (séries découvertes, avec leur libellé) et le type de chaque série ;
  « Enregistrer » (POST), « Annuler », « Rétablir » (composition par défaut)
- [x] Erreurs visibles : carte injoignable, refus d'écriture, composition invalide renvoyée par la carte ; la page — preuve : Chrome « refus » (message de la carte, édition ouverte), « injoignable » (connexion coupée → « Carte injoignable »), « invalide » (titre vide : rien n'est envoyé ; mutant détecté), « absent » (pas de bouton Modifier) ; réponse 500 de la carte sur exception
  reste utilisable en lecture
- [x] RAM et heap de la carte relevés pendant un enregistrement, sans chute durable — preuve : P4 le 2026-10-20, 2 séries de 10 POST /graphiques (essai / Rétablir) : 1re série Berry après GC 127,7 -> 141,8 Ko = chargement unique de graphiquesFonctions.be (non solidifié, 22 Ko de source), 2e série 142,2 -> 142,7 Ko (bruit) ; heap interne 204,0 -> 205,4 Ko après GC ; creux pendant l'envoi 194,6 Ko ; un POST à 3,4 s sur 20 (autres 0,2-0,5 s) ; composition par défaut restaurée (clé absente)
- [x] Bancs : Berry (validation de la route : corps valide, trop gros, types inconnus, trop de graphiques, accès refusé, — preuve : `banc_graphiques.py` vert (Berry + Chrome, 18 scénarios de rendu) ; 6 mutants de la page tous détectés (MUTANTS: OK) ; témoin Berry de la réponse 500 rouge
  autres clés conservées, Rétablir, témoin négatif) ; Chrome sans interface (composition à 3 graphiques de types
  différents, graphique combiné, périodes différentes, lectures mutualisées, édition puis enregistrement simulé,
  Rétablir) ; mutants ; `banc_graphiques.py` vert
- [x] Essai réel sur le P4 : un graphique ajouté depuis le PC apparaît sur le téléphone, persiste après un redémarrage — preuve : P4 le 2026-10-20, « Graphique 3 » (valeurCapteurHauteur) ajouté depuis le PC, relu dans /json/graphiques.json (3 graphiques), puis Restart 1 (StartupUTC 16:32:07, BootCount 2) : visible sur le téléphone après le redémarrage, puis supprimé depuis le téléphone (fichier réécrit 2 min 25 après le démarrage, 2 graphiques)
- [x] Documentation : `outils_docs/README.md` § « Les graphiques des mesures », `CLAUDE.md`, skill `bancs` ; — preuve : README § graphiques (composer ses graphiques, périodes par graphique, clé `graphiques`), `CLAUDE.md`, skill `bancs` ; `relecteur-berry` : 1 « à corriger » traité (fichier illisible écrasé → refus 500, contrôle rouge puis vert), échappement `</script>` désormais prouvé par le banc
  `relecteur-berry` sur le Berry touché

## Améliorations restantes
- [x] [projet] Mini-courbe 24 h sur la page d'accueil (écartée le 2026-10-18 pour garder l'accueil léger) — abandonnée : l'accueil se rafraîchit toutes les ~2 s et doit rester léger ; le bouton « Graphiques » y mène en un clic (décision de l'utilisateur, 2026-10-18)
- [x] [projet] CDN en secours si le fichier local manque — abandonnée : les esclaves derrière le NAPT n'ont pas Internet, uPlot est gardé dans le `localStorage` ; un secours masquerait un déploiement incomplet, que le message « HTTP 404 » signale (décision de l'utilisateur, 2026-10-18)
- [x] [projet] Export CSV d'une vue depuis la page — abandonnée : Grafana l'offre déjà (Inspect → Data → Download CSV), sur un historique plus long (décision de l'utilisateur, 2026-10-18)

## Vérification
- Socle : requêtes `/histo` sur le P4 (curl ou navigateur), JSON validé, contrôlé contre les logs `HISTORIQUE:`.
- Hors carte : le banc Python de A5 (code de sortie 0 = vert) et le rendu headless.
- Sur carte : page `/graphiques` du P4 ouverte depuis le PC et depuis un téléphone ; heap suivi
  (`ReglageLog` + sortie `detail` pour les `BRY: GC`) ; logs lus par la skill `logs-cartes`.
- Avant commit : `relecteur-berry`, puis `/commite`.
