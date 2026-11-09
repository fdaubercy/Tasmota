---
chantier: atelier-graphiques
titre: Atelier des graphiques (page 7950) et moteur commun des pages de graphiques
objectif: Préparer sur le PC un graphique pour une carte, le voir avec ses vraies valeurs, puis écrire dans le dépôt la description qui le fait apparaître sur la carte, sans Berry écrit à la main
statut: clos
cree: 2026-11-03
maj: 2026-11-09
---
# Atelier des graphiques

## Contexte
Spec validée par l'utilisateur le 2026-11-03 : `docs/superpowers/specs/2026-11-03-atelier-graphiques-design.md`
(13 décisions §3, choix de Claude §7). Maquettes : `outils_docs/atelier_graphiques/` — **modèle B**, grille du modèle C
pour une page dédiée. Exécution : skill `superpowers:subagent-driven-development` ou `superpowers:executing-plans`,
action par action ; lire la spec avant chaque action.

**Architecture.** Sur la carte, un moteur commun écrit une fois : `data/fs/pagesGraphiques.be` (driver
`PAGES_GRAPHIQUES`, une seule route `/pages`) et `data/sd/js/pages_graphiques.js` (tracé), qui lisent
`/json/pages_graphiques.json` (source `data/<lieu>/<carte>/pages_graphiques.json`). Sur le PC, l'atelier
(`outils_pc/atelier_graphiques_*.py`, port 7950) lit les séries, conseille un style, montre l'aperçu par le MÊME
`pages_graphiques.js`, puis écrit description + autoexec + cenv en une transaction.

**Paliers** (spec §5) : 1 = A1 à A10 (page dédiée S3/P4) ; 2 = A11 (`/graphiques` étendue) ; 3 = A12 (encadré
d'accueil) ; 4 = A13 (ESP32 classiques). Les actions A11 à A13 seront détaillées (fichiers, interfaces, tests) au
début de leur palier, sur ce qui aura été appris au palier 1.

### Contraintes globales (valent pour chaque action)
- Fichiers sous 500 lignes ; aucune nouvelle dépendance Python ni JS (ECharts 6.1.0 et liquidfill 3.1.0 déjà au dépôt).
- Python des bancs `outils_pc/` : `"$USERPROFILE/.platformio/penv/Scripts/python.exe"` ; bancs `berry/` : `python`.
- Bancs sur copies temporaires, jamais le vrai dépôt ; aucune jonction ni lien vers le dépôt dans le scratchpad.
- Berry : charte des logs du `CLAUDE.md` (`logFonctions.log`, préfixe `PAGES_GRAPHIQUES:`, `_ERREUR` dans les `except`,
  constantes `LOG_LEVEL_*`, pas d'`info` dans `web_sensor`/callbacks fréquents) ; pièges de solidification
  (`outils_docs/SOLIDIFICATION_BERRY.md` : aucun état dans la table du module, `import pagesGraphiques` dans toute
  fonction qui se cite, appels par `pagesGraphiques.nom`). Le hook `verifie_berry_edition` compile chaque `.be` édité.
- **Juste avant chaque série d'éditions de `data/` ou de `build/`, dans la même commande : aucun `platformio`/`scons`
  en cours**, sinon s'arrêter (leçons des 2026-10-29 et 2026-10-31). Aucun `pio run` direct : compilations par la page Build.
- Formules : analyseur à liste blanche (`+ - * /`, parenthèses, nombres, chemins de série, `min max abs round`),
  jamais `eval`, `Function`, ni `compile` Berry.
- Commits en français, sans accents, préfixe conventionnel, **sans trailer Co-Authored-By** (CLAUDE.md du dépôt).
- Documents durables : renvois par `fichier::fonction`, contrôlés par `maintenance/verifie_references_docs.py`.

### À surveiller en relecture (cas non couverts par la spec, chacun pris par un test de l'action citée)
1. Description absente, tronquée ou invalide sur la carte (FS plein, édition à la main) → page « description
   invalide » avec le motif, les autres routes de la carte intactes, aucune exception non rattrapée (A2).
2. Série absente du SENSOR du moment (capteur débranché, esclave ModBus muet) → le graphique dit « série absente »,
   les autres graphiques de la page sont tracés (A3).
3. Carte injoignable en cours d'édition (esclave derrière le NAPT, carte éteinte) → bandeau « valeurs simulées »,
   l'édition et l'écriture restent possibles (A4).
4. cenv ou autoexec modifié par l'utilisateur entre le diff et l'écriture → refus, rien d'écrit, message (A6).
5. Identifiant de page en double, ou qui vaut une route existante (`cs`, `cm`, `graphiques`, `histo`, `cuve`,
   `energie`, `pages`…) → refusé à la saisie (A1).

## A1 — Schéma de la description et sa validation (Python)
Fichiers : créer `outils_docs/scripts_python/outils_pc/atelier_graphiques_description.py`, banc
`test_atelier_graphiques_description.py`, cas partagés avec le banc Berry
`outils_docs/scripts_python/berry/bouchons_berry/pages_graphiques/cas_description.json` (liste de
`{"nom", "description", "valide": bool, "motif"}`).
Produit : `STYLES` (tuple des styles du palier 1 : `courbe aire escalier barres barres-empilees barres-periode
deux-axes lies cadran anneau chaleur nuage radar liquide demi-cercle`), `valide(description: dict) -> list[str]`
(motifs, vide = valide), `BORNES = {"pages": 8, "graphiques": 8, "series": 12, "octets": 8192}`,
`ROUTES_RESERVEES` (frozenset).
- [x] Écrire `cas_description.json` : au moins une description valide par style ; invalides : version ≠ 1, id de page
  en double, id réservé (« À surveiller » 5), id hors `[a-z0-9-]{1,24}`, style inconnu, 9 pages, 9 graphiques,
  13 séries, plus de 8192 octets, zone hors [0, 1], min ≥ max d'un cadran, formule avec `eval(`, formule qui mêle
  série instantanée et série d'historique (spec §7.5), cumul sur une série instantanée — preuve : cas_description.json, 76 cas (commit 247c37e0f)
- [x] Banc rouge (module absent), puis `valide()` écrit, banc vert : chaque cas rend `[]` ou un motif qui contient `motif` — preuve : test_atelier_graphiques_description.py : rouge ModuleNotFoundError puis vert 0 echec, 76 cas (802df4ec6, 247c37e0f)
- [x] Témoin : copie mutée dans le scratchpad (une borne passée de 8 à 9) → banc rouge — preuve : copie mutee (borne 8->9, fullmatch, arite) -> banc rouge, 3 echecs (task-1-report)
- [x] Commit `feat(atelier): schema et validation de la description des pages de graphiques` — preuve : 802df4ec6 + correctif 247c37e0f, relecture et re-relecture vertes

## A2 — Moteur Berry `data/fs/pagesGraphiques.be`
Fichiers : créer `data/fs/pagesGraphiques.be`, `outils_docs/scripts_python/berry/banc_pages_graphiques.py` +
`banc_pages_graphiques.be`, bouchons dans `bouchons_berry/pages_graphiques/`.
Consomme : `cas_description.json` (A1) — le moteur doit donner le même verdict que `valide()`.
Produit : `pagesGraphiques.demarre()` (lit l'index de `/json/pages_graphiques.json` : id, titre, accès de chaque page,
rien d'autre en RAM) ; driver `PAGES_GRAPHIQUES` : `web_add_handler` → `webserver.on("/pages", …)`,
`web_add_main_button` → un bouton par page à `acces: "bouton"` ; route `/pages?p=<id>` (page HTML : gabarit
`/sd/html/pages_graphiques.html` + CSS + `pages_graphiques_formule.js` puis `pages_graphiques.js`, description de la
page dans `window.PAGE_GRAPHIQUES`), `/pages?f=valeurs&c=<chemins séparés par ,>` (`{"t", "valeurs": {chemin: valeur|null}}`
lu dans `tasmota.read_sensors()`, 12 chemins au plus), `/pages?f=sources` (`{"historique": bool, "flash": []}`),
`/pages?f=liquidfill.js.gz` (par morceaux de 2048 o, comme `graphiquesFonctions::envoieFichier`). ECharts reste servi par
`/graphiques?f=echarts.js.gz`. Indépendant de `historiqueFonctions` (spec §7.4).
- [x] Banc rouge : charge le module par `global.pagesGraphiques = module(...)` (piège de solidification visible), rejoue
  chaque cas de `cas_description.json` (même verdict qu'A1), description absente / JSON tronqué / FS illisible →
  réponse « description invalide » + log `_ERREUR`, sans exception (« À surveiller » 1) ; boutons = pages à bouton
  seulement ; `f=valeurs` : chemin absent → `null`, 13 chemins → refus — preuve : banc_pages_graphiques.py rouge avant module, vert ensuite : 76/76 verdicts = A1, description absente/tronquee/illisible -> Description invalide + _ERREUR, 12 chemins ok / 13 refuses (b51d52500)
- [x] Module écrit (aucun état dans la table, `import pagesGraphiques` dans toute fonction qui se cite), banc vert,
  `verifie_berry.py` sans écart de charte — preuve : pagesGraphiques.be + pagesGraphiquesValidation.be (b51d52500), verifie_berry.py 0 ecart, relecture Approved
- [x] Témoin : copie de `data/fs` mutée (appel `pagesGraphiques_route` par son nom global) → banc rouge — preuve : data/fs copie au scratchpad, route appelee par son nom global -> banc rouge (task-2-report)
- [x] Mesure RAM dans le banc : tas Berry avant/après `demarre()` avec 8 pages, noté en preuve — preuve : index de 8 pages = 1576 o retenus contre 6424 o pour la description complete (berry.exe 64 bits, task-2-report)
- [x] Commit `feat(berry): moteur commun des pages de graphiques` — preuve : b51d52500

## A3 — Tracé commun `data/sd/js/pages_graphiques.js`
Fichiers : créer `data/sd/js/pages_graphiques.js`, `pages_graphiques_formule.js`, `data/sd/html/pages_graphiques.html`,
`data/sd/css/pages_graphiques.css` ; bancs node `outils_docs/scripts_python/outils_pc/test_pages_graphiques.mjs` et sonde
Chrome `test_pages_graphiques_chrome.py`.
Produit (navigateur et node, sans DOM pour les deux premières) : `PagesFormule.analyse(texte) -> {ok, series, erreur}`,
`PagesFormule.calcule(arbre, valeurs) -> number|null` ; `PagesGraphiques.optionDe(graphique, donnees, theme) -> object`
(option ECharts, ou `{svg: "..."}` pour `demi-cercle`) ; `PagesGraphiques.page(element, description, lecteur)` où
`lecteur(chemins, periode) -> Promise<donnees>` (sur la carte : `/pages?f=valeurs` et `/histo` ; dans l'atelier : le
serveur PC). Chargement d'ECharts comme `cuve.js` (localStorage, clé `graphiquesFonctions.VERSION_BIBLIOTHEQUE`).
Thème : variables CSS de Tasmota (sombre lisible). Seuils/zones : `markLine`/`markArea` ou `axisLine` du cadran.
- [x] Banc node rouge : `analyse` refuse `eval(1)`, `a.b; x`, `constructor`, accepte `6732 - sensorsCuve.niveauCuve.volume` ;
  `calcule` rend `null` si une série vaut `null` ; `optionDe` rend pour chaque style de `STYLES` une option dont la
  série a le bon `type` ECharts (`line`, `bar`, `gauge`, `pie`, `heatmap`, `scatter`, `radar`, `liquidFill`) et les seuils
  demandés ; série absente → titre du graphique suffixé « série absente » (« À surveiller » 2) — preuve : test_pages_graphiques.mjs rouge module absent (code 1) puis vert 246 verifications, oracle Python valide_formule, cas [5, 6, null] (dee3e7cc7, b87c405c1)
- [x] Code écrit, banc node vert ; témoin (liste blanche élargie à `eval`) → rouge — preuve : pages_graphiques.js 496 lignes + pages_graphiques_formule.js ; temoins eval dans la liste blanche et correctif retire -> rouge (task-3-report)
- [x] Sonde Chrome : gabarit servi par un petit serveur local avec des valeurs fixes, capture d'une page de 5 graphiques
  en 1400 px et 380 px, thème sombre ; aucune erreur console ; largeur de la page ≤ largeur de la fenêtre — preuve : test_pages_graphiques_chrome.py 1400/380 px theme sombre : aucune erreur console, page <= fenetre, temoin largeur rouge (442 > 380)
- [x] Commit `feat(pages): trace commun des pages de graphiques` — preuve : dee3e7cc7 + correctif b87c405c1, relecture et re-relecture vertes

## A4 — Séries d'une carte (`atelier_graphiques_series.py`)
Consomme : `build_envs.lit_ip_ota`, `build_envs.adresse_par_maitre`, `build_ota_http._get` (lecture seule ; **ni
`RoutageRangeExtender` ni `Sleep 0`**, spec §7.3).
Produit : `series(racine, env, *, get=None) -> {"source": "carte"|"depot", "motif": str, "historique": bool,
"series": [{"chemin", "libelle", "unite", "historique": bool, "min"?, "max"?, "etat": bool}]}` ;
`valeurs(racine, env, chemins, periode, *, get=None) -> dict` (vraies valeurs, ou simulées si `source == "depot"`).
Sources : `/histo?p=liste`, `Status 10`, `/pages?f=sources` (routes privilégiées : en-tête `Referer` qui désigne la
carte, vérifier ce que pose `build_ota_http._get`) ; repli : persist du dépôt (`diverses.historique`,
blocs de modules) et `graphiques.json` (libellés, unités).
- [x] Banc `test_atelier_graphiques_series.py` rouge, `get` simulé : carte en ligne → `source: carte` ; `get` qui lève
  (« À surveiller » 3) → `source: depot`, motif « carte injoignable », séries du persist ; esclave (IP 0.0.0.0) →
  adresse `<ipMaitre>:<port>` demandée, aucune requête d'écriture (liste des URL appelées vérifiée) — preuve : test_atelier_graphiques_series.py rouge ModuleNotFoundError puis vert 28 cas : carte, repli depot « carte injoignable », esclave 192.168.0.9:8081, URL toutes en lecture (abfdfe060, 23cb7b779)
- [x] Code écrit, banc vert, témoin (repli supprimé) → rouge — preuve : atelier_graphiques_series.py, valeurs() aux formats de la carte (direct, jour, mois) ; temoins repli/validation/simulation retires -> rouge
- [x] Commit `feat(atelier): lecture des series d'une carte` — preuve : abfdfe060 + correctif 23cb7b779, relecture et re-relecture vertes

## A5 — Conseil de style (`atelier_graphiques_conseil.py`)
Produit : `INTENTIONS = ("evolution", "seuil", "comparaison", "repartition", "cumul", "lien", "habitudes")` ;
`propose(intention, series, destination, historique) -> {"proposes": [{"style", "raison"}], "ecartes": [{"style", "motif"}]}`,
3 à 5 proposés, chaque style de `STYLES` présent dans l'une des deux listes.
- [x] Banc rouge, cas figés à la main (jamais dérivés des règles) : `seuil` + 1 série bornée → `cadran` premier ;
  `evolution` + 2 unités → `deux-axes` premier ; `repartition` + 1 série → `anneau` écarté (motif « parts d'un
  total ») ; `habitudes` sans historique → `chaleur` écarté ; destination `accueil` → seul `demi-cercle` proposé — preuve : test_atelier_graphiques_conseil.py rouge ModuleNotFoundError puis vert : cadran premier, deux-axes premier, anneau ecarte « parts d'un total », chaleur ecartee sans historique, accueil = demi-cercle seul ; entrees invalides -> ValueError (291d98353, dead5408e)
- [x] Règles écrites, banc vert, témoin → rouge — preuve : atelier_graphiques_conseil.py (103 lignes) ; temoin regle anneau n < 1 -> rouge (task-5-report)
- [x] Commit `feat(atelier): conseil de style` — preuve : 291d98353 + correctif dead5408e, relecture et re-relecture vertes

## A6 — Écriture dans le dépôt (`atelier_graphiques_ecriture.py`)
Consomme : `valide()` (A1), `fichiers_berry_ini` (résolution des `${...}`), `fichiers_berry_sauvegarde.Transaction`,
`build_serie.builds_en_cours_defaut`.
Produit : `prevoit(racine, env, description, solidifier) -> {"fichiers": [{"chemin", "avant", "apres"}], "empreinte": str}` ;
`ecrit(racine, env, description, solidifier, empreinte_lue, builds_en_cours) -> list[str]` (chemins écrits).
Première page : ligne `demarrage.charge(["pagesGraphiques"])` (ou `demarrage.importe`, si le module est dans
`custom_berry_solidify` résolu) après `demarrage.historique()` s'il existe, sinon en fin de bloc ; liste
`pages_graphiques` dans `[berry_commun]` (moteur, gabarit, CSS, 2 JS) ; `${berry_commun.pages_graphiques}` au
`custom_files_upload` de l'env et au `custom_files_exclude` de chaque autre env (créé s'il manque) ; liquidfill ajouté
à l'env seulement si un graphique `liquide` existe ; `solidifier=True` : `data/fs/pagesGraphiques.be` ajouté au
`custom_berry_solidify` de l'env (et retiré de son `custom_files_upload`), signalé « firmware à recompiler ». Ensuite : `pages_graphiques.json` seul. Dernière page retirée :
ligne d'autoexec et listes retirées.
- [x] Banc `test_atelier_graphiques_ecriture.py` rouge, sur une copie temporaire (cenv, autoexec, data de 3 envs) :
  1re page → 4 fichiers, relus par `ProjectConfig` (os.chdir dans la copie, leçon du 2026-11-01) : l'env embarque, les
  2 autres excluent ; 2e modification → seul le JSON change ; solidifié → `importe` ; build en cours → refus ;
  empreinte périmée (« À surveiller » 4) → refus, copie inchangée octet pour octet ; exception au milieu → tout annulé ;
  commentaires du cenv gardés — preuve : rouge (module absent) puis vert, 12 tests / 55 contrôles ; 1re page = 3 fichiers (liste posée d'avance, décision 1)
- [x] Code écrit, banc vert, témoin → rouge — preuve : témoin (marqueur retiré) → 1 KO ; `banc_demarrage` vert sur les 6 cartes
- [x] Commit `feat(atelier): ecriture de la description, de l'autoexec et du cenv` — preuve : 0c9162b79 + fc98e82f1 (liste exclue de tous les envs), relecture approuvée

## A7 — Serveur et page de l'atelier (modèle B + grille C)
Fichiers : `atelier_graphiques_web.py` (serveur, `acces_web.py`, port 7950), `atelier_graphiques_page.py` (HTML/CSS),
`atelier_graphiques_page_js.py` (JS) ; banc `test_atelier_graphiques_web.py`, sonde `test_atelier_graphiques_page_chrome.py`.
Routes : `GET /` ; `GET /envs` (envs S3/P4 « Mes cartes ») ; `GET /series?env=` (A4) ; `GET /valeurs?env=&c=&p=` (A4) ;
`POST /conseil` (A5) ; `GET /description?env=` ; `POST /valide` (A1) ; `POST /diff` (A6 `prevoit`) ; `POST /ecrire`
(A6 `ecrit`) ; `GET /moteur/<nom>` (les 2 JS, le gabarit et le CSS de `data/sd/`, ECharts décompressé de
`data/sd/js/echarts.min.js.gz`). L'aperçu appelle `PagesGraphiques.page()` avec un `lecteur` sur `/valeurs`.
Disposition de `outils_docs/atelier_graphiques/modele-B.png` ; bascule « Page » → grille de `modele-C.png` (tuiles
déplaçables, largeur demi/pleine) ; bascules PC/téléphone/thème sombre ; bouton « Envoyer par la page Build ↗ » =
`http://127.0.0.1:7700/?env=<env>#fichiers`.
- [x] Banc HTTP rouge puis vert : chaque route, refus d'un POST sans l'en-tête de `acces_web`, `/ecrire` refusé pendant un
  build simulé, `/moteur/../` refusé — preuve : `test_atelier_graphiques_web.py` 61 OK (mutant de la liste blanche → 6 KO), c046db007 + c0958af6c
- [x] Sonde Chrome : capture 1400 px comparée à `modele-B.png` à l'œil par l'utilisateur ; un réglage changé (seuil)
  change l'aperçu (DOM vérifié) ; aucune erreur console — preuve : `test_atelier_graphiques_page_chrome.py` 32 OK, témoin détecté ; course au changement de carte prouvée et corrigée (c0958af6c)
- [x] Maquette montrée à l'utilisateur sur image avant de passer à A8 (leçon du 2026-11-02) — preuve : capture-a7.png montrée, accord de l'utilisateur le 2026-11-03 (« Oui, passer à A8 »)
- [x] Commit `feat(atelier): page de l'atelier des graphiques` — preuve : c046db007, correctifs c0958af6c, relecture et re-relecture approuvées
- [x] A7b — libellé, unité et couleur par série (spec §2, réponse 10) : champ `series` du schéma (A1) accepte aussi
  `{"chemin", "libelle", "unite", "couleur"}`, validé côté carte (`pagesGraphiquesValidation.be`), tracé par le moteur
  (`pages_graphiques.js` : légende, axe, couleur), réglé dans l'atelier ; bancs A1, A2, A3, A7 verts, témoin rouge — preuve : 9387a7bdb + 226244c08 (doublon de chemin refusé, unité connue écrite à l'ajout) ; Berry 105/105 même verdict que Python, node 280, sondes Chrome vertes ; relecture et re-relecture approuvées

## A8 — Annuaire, tâche VS Code, cible Custom
Fichiers : `annuaire_registre.py` (entrée `atelier_graphiques`, groupe `GROUPES[2]`, port 7950, arrêt libre),
`.vscode/tasks.json` (« Outil : atelier des graphiques (http://127.0.0.1:7950) »), `build/cible_atelier_graphiques.py`
(`NOM_CIBLE = "atelier_graphiques"`, page démarrée détachée comme `build/cible_build_web.py`),
`.claude/hooks/garde_build.py` (`CIBLES_OUTILS`), import dans `build/pre_utilitaires_platformio.py`.
- [x] Bancs `test_annuaire.py`, `build/test_garde_build.py` (liste = les `NOM_CIBLE`), nouveau
  `build/test_cible_atelier_graphiques.py` : verts — preuve : test_annuaire 144 OK (11 outils), test_garde_build VERT (témoin : ligne retirée → rouge), test_cible_atelier_graphiques VERT (autre service sur le port → pas l'atelier, témoin rouge) ; 13e63be84 + 2f377ac5d
- [x] Tuile vue dans l'annuaire (:7600), lancée et arrêtée par ses boutons (capture) — preuve : annuaire relancé (accord de l'utilisateur), POST /lance → 7950 sert « Atelier des graphiques », état « marche » ; POST /arrete → {"ok": true}, 7950 muet, état « arrete » ; captures capture-a8-annuaire-marche.png / -arrete.png (.superpowers, hors dépôt)
- [x] Commit `feat(annuaire): tuile de l'atelier des graphiques` — preuve : 13e63be84, relecture approuvée

## A9 — Première page réelle (cuve ou P4, au choix de l'utilisateur)
- [x] Page composée dans l'atelier avec les vraies séries, diff relu par l'utilisateur, écrite — preuve : cuve choisie, proposition de départ (courbe « Hauteur d'eau », cm, 24 h, page /tableau) diff montré puis « écris », POST /ecrire → 3 fichiers ; ca1ce699f
- [x] `banc_demarrage.py --carte <env>` : écart attendu (le module de plus) relu, instantané de CETTE carte seul enregistré — preuve : écart = driver PAGES_GRAPHIQUES + /pagesGraphiques.be, /pagesGraphiquesValidation.be ; --carte cuve --enregistre ; banc VERT sur les 6 cartes ; ca1ce699f
- [x] Place du FS vérifiée sur l'image construite (blocs de 4 Ko, leçon du 2026-11-02) ; envoi par la page Build
  (onglet Fichiers) lancé par l'utilisateur — preuve : image du 2026-11-04 07:50, 42 fichiers = 206 blocs de 4 Ko sur 11,3 Mo (7,1 %), 9 fichiers nouveaux aux tailles du dépôt, identité vérifiée ; envoi de 9 fichiers par l'utilisateur (onglet Fichiers, BrRestart) ; /pages?p=tableau 200
- [x] Sur la carte : journal web sans `_ERREUR`, tas mesuré page fermée puis ouverte, bouton d'accueil à la largeur des
  autres (mesure Chrome), capture de la page vue par l'utilisateur — preuve : aucun PAGES_GRAPHIQUES_ERREUR ni exception JS ; tas 184 Ko constant (frag 25) page fermée / servie 3 fois ; bouton « Tableau » 340 px = les 6 autres ; capture-a9-cuve-tableau.png, page vue par l'utilisateur le 2026-11-04
- [x] Modification d'un réglage dans l'atelier, renvoi, effet constaté sur la carte — preuve : 2026-11-04, séries Taux et Volume ajoutées dans l'atelier puis envoyées ; `/json/pages_graphiques.json` de la cuve identique au dépôt (3 séries, cadence 10) ; `/pages?p=tableau` sous Chrome : légende Hauteur d'eau / Taux / Volume, aucune exception JS (`.superpowers/sdd/atelier-graphiques/capture-a9-modif.png`)

## A10 — Documentation du palier 1
- [x] `outils_docs/README.md` § « Atelier des graphiques (page web) » ; `outils_docs/atelier_graphiques/README.md` :
  choix B noté ; `CLAUDE.md` : entrée dans la carte des documents ; skill `bancs` : lignes des nouveaux bancs — preuve : 1b4acaf86 (README § « Atelier des graphiques (page web) », atelier_graphiques/README.md modèle B réalisé, entrée CLAUDE.md, 2 lignes skill bancs)
- [x] `verifie_references_docs.py` code 0 ; agent `relecteur-berry` sur `pagesGraphiques.be` ; commit `docs: atelier des graphiques` — preuve : 18 documents, 0 défaut ; relecteur-berry prêt (charte et solidification conformes), 2 points d'entrée corrigés f1c075077 (banc rouge puis vert) ; 1b4acaf86

## A13 — Palier 4 : ESP32 classiques (à détailler au début du palier)
- [x] Moteur en rendu SVG seul, sans ECharts ni historique ; adaptateur `energieFonctions` (données en flash, spec §7.1) — preuve : remplacée par le plan `tasks/plans/energie-atelier.md` (clos le 2026-11-09) : rendu SVG de `data/sd/js/energie.js`, données en flash de `energieFonctions`
- [x] Tas et FS mesurés sur le différentiel avant de déclarer la cible tenable (leçon du 2026-11-02) — preuve : remplacée par le plan `tasks/plans/energie-atelier.md` (clos le 2026-11-09) : A7 (tas 60 Ko, UfsFree 36 Ko le 2026-11-09)

## Actions retirées (2026-11-04)
A11 (palier 2, `/graphiques` étendue) : remplacée par le plan `tasks/plans/atelier-destinations.md`
(spec `2026-11-04-atelier-destinations-televersement-design.md`). A12 (palier 3, encadré d'accueil) : abandonnée par
l'utilisateur le 2026-11-04 (trop de contraintes).

## Améliorations restantes
- [x] [projet] Après le palier 1 : proposer de formaliser un agent `.claude/agents/` de relecture des pages web générées si
  la même relecture revient — preuve : `.claude/agents/relecteur-pages-web.md` (2026-11-05, plan atelier-destinations)

## Vérification
Chaque action se coche sur preuve (sortie de banc, commit, capture). Le palier 1 est clos quand A9 est vue sur la vraie carte.
