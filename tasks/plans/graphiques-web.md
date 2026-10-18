---
chantier: graphiques-web
titre: Graphiques des mesures dans les pages web des cartes S3/P4 (uPlot)
statut: actif
cree: 2026-10-18
maj: 2026-10-18
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
- [ ] Mesures de la cuve simulées pendant les essais (sa sonde et son ADS1115 ne sont pas branchés) : émulation de l'esclave 1 par le sniffeur ModBus (http://127.0.0.1:7300, `emulation_modbus.py` : thermomètre 1312 et analogique, valeurs éditables), **cuve retirée du bus RS485** pendant l'essai (deux esclaves à l'adresse 1 = collisions) ; la cuve passe à `valide`, les courbes se remplissent, puis repassent à `null` à l'arrêt de l'émulation
- [x] P4 : bouton visible, `/graphiques` affiche la vue 24 h, la vue mois, les cases et le lien Grafana — preuve : accueil avec `action='/graphiques'` ; vue 24 h juste après le redémarrage : « Aucun pas de mesure encore clos… » (attendu) ; vue mois « Octobre 2026 (moyenne horaire, bande min-max) », 7 cases, axes °C / mV (capture scratchpad `a6/page_p4_mois.png`) ; `window.GRAPHIQUES.grafana` = `…var-appareil=garage`, bouton affiché. Passé par 2 redémarrages : ancien `.bec` en cache puis persist réécrit par `System#Save` (lessons.md 2026-10-18), autoexec du P4 et de la cuve corrigés
- [x] P4 : heap libre relevé pendant le chargement de la page ; l'accueil (`/?m=1`) ne charge toujours pas uPlot — preuve : `Status 11` heap 239 Ko avant, 206 Ko pendant l'envoi simultané de la page, du CSS et d'uPlot, 239 Ko juste après et 5 s plus tard ; `/` et `/?m=1` : 0 occurrence de « uplot »
- [x] Déployé sur les autres cartes S3 (cave serveur-rly, grenier, rideau, serveur-modbus S3, cuve) ; cuve vide attendue tant que ses capteurs ne sont pas branchés
- [x] Documentation : section « Graphiques » dans `outils_docs/README.md`, ligne dans la carte des documents de `CLAUDE.md`, mémoire `project_historique_capteurs` mise à jour — preuve : `outils_docs/README.md` § « Les graphiques des mesures (cartes S3/P4) » + entrée d'index ; `CLAUDE.md` ligne « Graphiques des cartes S3/P4 » ; mémoire et `MEMORY.md` à jour

## Améliorations restantes
- [ ] [projet] Mini-courbe 24 h sur la page d'accueil (écartée le 2026-10-18 pour garder l'accueil léger)
- [ ] [projet] CDN en secours si le fichier local manque
- [ ] [projet] Export CSV d'une vue depuis la page
- [ ] [projet] Courbes pour les ESP32 classiques (sans historique local) : passer par Grafana sur le Pi

## Vérification
- Socle : requêtes `/histo` sur le P4 (curl ou navigateur), JSON validé, contrôlé contre les logs `HISTORIQUE:`.
- Hors carte : le banc Python de A5 (code de sortie 0 = vert) et le rendu headless.
- Sur carte : page `/graphiques` du P4 ouverte depuis le PC et depuis un téléphone ; heap suivi
  (`ReglageLog` + sortie `detail` pour les `BRY: GC`) ; logs lus par la skill `logs-cartes`.
- Avant commit : `relecteur-berry`, puis `/commite`.
