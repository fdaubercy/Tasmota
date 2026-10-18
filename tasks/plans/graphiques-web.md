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
- `historiqueFonctions.be` fait 489 lignes : la page va dans un **nouveau module** pour rester sous 500 lignes.
- Le P4 est aussi la carte du plan `modbus-garage` (A4 : observation d'1 h sans abandon). Un flash du P4 relance
  cette observation : il faut caler les flashs avec l'utilisateur.
- Pas de build en parallèle de celui de l'utilisateur, pas de cible PlatformIO pendant un build (`garde_build`).

## A1 — Valider le socle /histo sur le maître P4 (prérequis)
- [ ] LittleFS du P4 téléversé par l'utilisateur, au moment convenu avec le plan modbus-garage
- [ ] Log `HISTORIQUE: Series enregistrees : [...]` relevé sur le P4, avec les 7 séries du persist
- [ ] `/histo?p=liste` et `/histo?p=jour` répondent en JSON valide : 7 séries, 288 points, `t0` cohérent avec l'heure UTC
- [ ] Une heure plus tard, `/histo?p=mois&m=<mois courant>` contient au moins une ligne
- [ ] Heap libre relevé avant et après une requête `p=jour`, sans chute durable

## A2 — Servir uPlot depuis la carte
- [ ] Choix tranché entre `UFILESYS_STATIC_SERVING` + `UfsServe` et une route Berry : taille du firmware P4 avec et sans le define, essai de `UfsServe` (gzip, cache, accès sans mot de passe ou non)
- [ ] uPlot 1.6.30 (`.js` compressé en gzip et `.css`) placé dans un dossier du LittleFS protégé de `gestionFileFolder` ; source dans le dépôt, hors du `data_dir` d'une carte
- [ ] Fichiers exclus du LittleFS des ESP32 classiques (`custom_files_exclude` de `platformio_tasmota_cenv.ini`, comme `historiqueFonctions.be`)
- [ ] Vérifié dans le navigateur : uPlot reçu avec `200`, gzip et cache, `uPlot` défini

## A3 — Page /graphiques et bouton d'accueil
- [ ] Nouveau module `data/fs/graphiquesFonctions.be` : driver avec `web_add_main_button` (bouton « Graphiques ») et route `/graphiques` (`check_privileged_access`), démarré par `historiqueFonctions.demarre` sous la même condition `activation`
- [ ] Page au gabarit Tasmota (`content_start`, `content_send_style`, `content_stop`) ; logique dans `data/sd/js/graphiques.js`, envoyée par `gestionFileFolder.readFileByLineAndContentSend` (comme `main.js`, `controleWeb.be:368`)
- [ ] La page lit `/histo?p=liste`, puis la vue demandée ; un historique absent (404) ou des séries vides affichent un message clair
- [ ] Logs du module conformes à la charte (`logFonctions.log`, préfixe `GRAPHIQUES:`, pas d'`info` dans un callback fréquent)

## A4 — Les quatre vues
- [ ] Vue 24 h : abscisses `t0 + i*pas`, `null` tracé comme un trou, heure locale (Intl fr-FR)
- [ ] Vue mois : sélecteur rempli par `p=liste`, moyenne + bande min/max (modèle : `apercus_graphiques/uplot.html`), mois `-a` lus avec `seriesFichier`
- [ ] Choix des séries : cases à cocher mémorisées dans `localStorage` (lecture et écriture sous try/catch), deux axes Y répartis par unité
- [ ] Libellés et unités : bloc facultatif `diverses.historique.affichage` (`{"serie": {"libelle", "unite"}}`) ; à défaut, déduits du nom (temperature → °C, hauteur → cm, volume → L, taux → %)
- [ ] Lien Grafana : clé facultative `diverses.historique.grafana` (URL), bouton masqué si elle est absente ; posée dans les persists du P4 et de la cuve
- [ ] Mise en page utilisable sur téléphone (largeur du graphique recalculée au redimensionnement)
- [ ] `outils_docs/schemas/persist.schema.json` régénéré (`berry/genere_schema_persist.py`) pour les nouvelles clés

## A5 — Bancs et relecture avant l'essai réel
- [ ] Banc hors carte : petit serveur Python qui sert la page et des JSON `/histo` fictifs (24 h avec trous, mois, mois `-a`, 404, séries vides) ; rendu vérifié dans Chrome headless (`--dump-dom`, sans `--virtual-time-budget`)
- [ ] `verifie_berry.py` vert sur les `.be` touchés (hook `verifie_berry_edition`)
- [ ] Agent `relecteur-berry` passé sur le diff Berry, remarques traitées

## A6 — Essai réel sur le P4, puis les autres S3
- [ ] P4 : bouton visible, `/graphiques` affiche la vue 24 h, la vue mois, les cases et le lien Grafana — preuve : capture ou sortie
- [ ] P4 : heap libre relevé pendant le chargement de la page ; l'accueil (`/?m=1`) ne charge toujours pas uPlot
- [ ] Déployé sur les autres cartes S3 (cave serveur-rly, grenier, rideau, serveur-modbus S3, cuve) ; cuve vide attendue tant que ses capteurs ne sont pas branchés
- [ ] Documentation : section « Graphiques » dans `outils_docs/README.md`, ligne dans la carte des documents de `CLAUDE.md`, mémoire `project_historique_capteurs` mise à jour

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
