---
chantier: energie-atelier
titre: Atelier des graphiques — page « Énergie » du différentiel (palier 4)
objectif: Que l'atelier reprenne et modifie la page /energie du différentiel (ajouter, restyler, échelle de temps, déplacer, taille) puis l'envoie par Téléverser, sans toucher au comptage
statut: clos
cree: 2026-11-08
maj: 2026-11-09
---
# Atelier des graphiques — page « Énergie » du différentiel

## Contexte
Spec validée par l'utilisateur le 2026-11-08 : `docs/superpowers/specs/2026-11-08-atelier-energie-differentiel-design.md`
(lire aussi son §6, choix de Claude). Remplace l'A13 de `tasks/plans/atelier-graphiques.md`.
Carte : env `tasmota32-bureau-interrupteur-energie`, dossier `data/bureau/tasmota32-interrupteur-energie`, ESP32 sans
PSRAM, FS 320 Ko (52 Ko libres), tas ≈ 52 Ko.

**Contraintes globales** (spec §3) : fichiers < 500 lignes (`atelier_graphiques_page_js.py` 473 et `banc_energie.be` 489 :
on ajoute des modules, on ne les grossit pas) ; `energieFonctions` ne change qu'aux routes de lecture (`f=description`,
`f=mois`, `f=direct` élargi), comptage et stockage intacts ; Berry ne parse jamais la description (relais par
`gestionFileFolder.readFileByLineAndContentSend`) ; borne de la description 4 096 octets, 16 éléments, titres de 40
caractères, couleur `#rrggbb` ; repli sur la disposition d'aujourd'hui si la description manque ou est refusée ;
aucune compilation hors de la page Build ; charte des logs Berry ; bancs sur copies, jamais le vrai dépôt ; pas de
sonde Chrome pendant un build (garde bloquante dans la commande, leçon du 2026-11-08).

**Interfaces partagées entre actions**
- Schéma (A1) : `{"version": 1, "elements": [ ... ]}` ; `type` ∈ `valeur cadran demi-cercle barres courbe aire escalier` ;
  `source` = `{"direct": <champ ENERGY>}` | `{"total": "jour|mois|an", "grandeur": "kWh|euros"}` |
  `{"flash": "minutes|heure|jour|mois|an", "grandeur": "kWh|euros", "mois": "AAAA-MM" | "decalage": 0..23, "nombre": 1..24}` ;
  `titre`, `unite`, `couleur`, `largeur` (`demi|pleine`), `hauteur` (`petite|moyenne|grande`), `min`/`max` (cadran,
  demi-cercle), `total` (bool, graphiques heure/jour/mois/an).
- Python : `atelier_energie_description.py` : `TYPES`, `CHAMPS_DIRECT`, `BORNES = {"elements": 16, "octets": 4096, "titre": 40}`,
  `DEFAUT` (dict, la page d'aujourd'hui), `valide(description) -> list[str]`.
- Cas partagés Python/JS : `outils_docs/scripts_python/outils_pc/cas_energie.json` (`[{"nom", "description", "motif"}]`,
  motif vide = valide).
- JS carte : `data/sd/js/energie.js` expose `window.Energie = {DEFAUT, valide(d) -> [motifs], trace(zone, description, donnees, direct)}`.
- Carte : `/energie?f=description` (200 JSON | 404), `/energie?f=mois&m=AAAA-MM` (200 JSON `{"d","de"}` | 404 | 400),
  `/energie?f=direct` (`p i f hz` + champs ENERGY présents sous leur nom Tasmota).
- Atelier serveur : `atelier_graphiques_energie.py` : `etat_carte(racine, env, *, get) -> {description, firmware_requis, motif}`,
  `prevoit(racine, env, description) -> {fichiers, empreinte}`, `ecrit(racine, env, description, empreinte, builds_en_cours) -> [chemins]`,
  `plan(racine, env, *, get) -> {fichiers, redemarrer: 0, notes, firmware_requis, url}`, `catalogue(racine, env, *, get) -> {sources, styles}`.
  Destination `"energie"` dans `/diff`, `/ecrire`, `/composition`.

**À surveiller** (non couvert par un test d'une autre action ; chaque ligne a son cas dans l'action qui possède le code)
1. Description de plus de 4 096 octets ou JSON tronqué sur la carte → page par défaut + ligne « description ignorée » (A3).
2. Mois fixe dont l'archive a été purgée (`f=mois` 404) → graphique vide « archive effacée », la page continue (A3) ;
   signalé dans l'atelier avant écriture (A5).
3. Carte à l'ancien firmware (`f=description` rend la page HTML en 200) → « Téléverser » bloqué, message firmware (A4).
4. Champ `direct` absent du bloc ENERGY (ex. `Yesterday` pas encore publié) → tuile « -- », pas d'exception (A3).
5. Téléphone 390 px → une colonne, aucun défilement horizontal (A3 et A5).

## A1 — Schéma et validation de la description (`atelier_energie_description.py`)
- [x] Écrire `cas_energie.json` — preuve : 80 cas (outils_docs/scripts_python/outils_pc/cas_energie.json), tous verts au banc : `DEFAUT` valide ; un cas valide par type et par source (dont `decalage`, `mois` fixe,
  `nombre`, `total`) ; invalides : version ≠ 1, 17 éléments, plus de 4 096 octets, type inconnu, `direct` hors
  `CHAMPS_DIRECT`, `flash` inconnu, `minutes` avec `grandeur`, `mois` et `decalage` ensemble, `decalage` 24, `nombre` 25,
  couleur `rouge`, titre de 41 caractères, `hauteur` `xl`, cadran sans `min`/`max` ou `min ≥ max`, `total` sur une valeur
- [x] Banc rouge `test_atelier_energie_description.py` — preuve : rouge ModuleNotFoundError, puis 0 echec(s) sur 95 verifications, temoin 16 -> 17 rouge (2 echecs) ; (module absent), puis module écrit, banc vert (chaque cas : `[]` ou
  un motif qui contient `motif`) ; témoin : copie mutée (borne 16 → 17) → rouge
- [x] Commit `feat(atelier): schema de la page Energie du differentiel` — preuve : 2f1001497

## A2 — Carte : routes de lecture d'`energieFonctions` (firmware)
- [x] Banc Berry rouge `banc_energie_routes.be` + `.py` (berry.exe, faux `webserver`, comme `banc_energie`) : — preuve : rouge sur le module d'avant (HEAD), 42 verifications vertes apres, 11 temoins rouges (banc_energie_routes.py)
  `f=description` relaie le fichier tel quel / 404 sans fichier / refus sans lecture au-delà de 4 096 o ;
  `f=mois&m=2026-10` relaie `mois-2026-10.json` / 404 / `m=../x` et `m=2026-13` → 400 ;
  `f=direct` garde `p i f hz` et ajoute `Voltage`, `Today`… présents, omet les absents
- [x] `energieFonctions_route` + `envoieDirect` modifiés, deux fonctions `envoieDescription()`, `envoieMois(m)` (piège 12 :
  `import energieFonctions` dans chaque fonction) ; banc vert ; `banc_energie.py` toujours vert ; `verifie_berry.py` sans écart — preuve : banc_energie_routes.py VERT, banc_energie.py COMPLET OK, verifie_berry 0 erreur 0 avertissement
- [x] Relecture `relecteur-berry` (tas : aucun fichier lu en entier) — preuve : relecteur-berry « aucun défaut réel », relecture de tâche Approved, commit 30a2da910 ; commit `feat(energie): routes description, mois et direct elargi`

## A3 — Rendu piloté par la description (`energie.js`, `energie.html`, `energie.css`)
- [x] Banc node rouge `test_energie_rendu.mjs` : `Energie.valide` rend les mêmes verdicts que Python sur `cas_energie.json` ; — preuve : test_energie_rendu.mjs, 0 echec sur 121 verifications (114 cas + DEFAUT + bornes 4096/4097 octets contre Python), 4 temoins mutants rouges (bun, node absent du PATH) ; `trace` juge par Chrome seul ;
  `trace` sur un faux DOM minimal ou jsdom absent : à défaut, banc Chrome seul (au choix de l'implémenteur, à dire)
- [x] `energie.js` réécrit (repli `DEFAUT` + ligne de motif ; « À surveiller » 1, 2, 4), gabarit vide dans `energie.html`, — preuve : energie.js 18353 o, energie.html 388 o, energie.css 1697 o ; banc node vert, banc Chrome vert ;
  grille 2 colonnes, hauteurs petite/moyenne/grande et une colonne sous 600 px dans `energie.css`
- [x] `banc_energie.py` (rendu Chrome) vert SANS description (la page d'aujourd'hui : mêmes `data-valeurs`, totaux, tuiles) ; — preuve : banc_energie.py BANC_ENERGIE_COMPLET OK (157 verifications Berry + rendu Chrome sans description, cout du mois sur les 30 jours de novembre) ; banc_energie_description.py OK (14 temoins mutants + 390 px dans un cadre, rouges) ;
  ajout de cas : description modifiée (ordre, couleur, hauteur, mois `decalage` 1), description de 5 000 o → repli dit,
  `f=mois` 404 → « archive effacée », graphique « an » avec l'année la plus ancienne marquée partielle, `total` → titre
  « kWh · € », 390 px sans défilement (« À surveiller » 5)
- [x] Taille de `energie.js` + `.html` + `.css` notée (cible ≤ 20 Ko) ; commit `feat(energie): page Energie pilotee par sa description` — preuve : 20467 o au total apres le tour 2 (cible 20480, marge 13 o), commit feat(energie): page Energie pilotee par sa description ;

## A4 — Atelier, serveur : destination « energie » (`atelier_graphiques_energie.py`)
- [x] Banc rouge `test_atelier_graphiques_energie.py` (dépôt copié, carte simulée par `get`) : — preuve : rouge ModuleNotFoundError (module absent), puis vert ; 4 temoins rouges (firmware, build, cartes, compact) (test_atelier_graphiques_energie.py)
  `cartes()` inclut le différentiel (FS avec `page_energie`), pas `tasmota32-vr-porte` ; `etat_carte` : description de la
  carte lue, 404 → `None`, page HTML en 200 → `firmware_requis` (« À surveiller » 3) ; `prevoit`/`ecrit` : empreinte,
  refus pendant un build, description invalide refusée ; `plan` : `energie_page.json`, `sd/js/energie.js`,
  `sd/html/energie.html`, `sd/css/energie.css`, `redemarrer` 0, `url` avec `depuis=atelier` ; `catalogue` : sources flash
  et total, champs `direct` de `Status 10` (carte muette → liste de la spec §2), styles de `TYPES`
- [x] Module écrit ; `atelier_graphiques_web.py` : `cartes()` élargi, routes `/diff` `/ecrire` `/composition` pour — preuve : banc energie 59 OK / 0 echec ; bancs web, ecriture, graphiques, televerse, series, description, conseil verts (atelier_graphiques_energie.py, atelier_graphiques_web.py)
  `destination: "energie"`, `MOTEUR` + `energie.js`/`.html`/`.css`, `/series` du différentiel = `catalogue` ; banc vert ;
  bancs existants de l'atelier verts (`test_atelier_graphiques_*.py`, bout en bout)
- [x] Commit `feat(atelier): destination Energie du differentiel, cote serveur` — preuve : commit ec9d49c54 feat(atelier): destination Energie du differentiel, cote serveur ; tour 1 : 404/413 lus sur HTTPError et route /energie/<env> d'apercu, 8 bancs de l'atelier verts, 7 temoins rouges (d18c1be6c) ; relecture : HTML d'ancien firmware simule, mois ASCII (590e4d01e, 88 verifications)

## A5 — Atelier, page : menu « Énergie (/energie) » (`atelier_graphiques_page_energie.py`)
- [x] — preuve : `test_atelier_energie_page_chrome.py` vue rouge d'abord (mutant `--mutant absent` : module JS non chargé, 5 KO sur le menu, les réglages masqués, le départ, l'aperçu), puis verte (edition, ecriture, firmware, difference, mobile, sombre : tous OK, témoin JS détecté) ; mutants `archive` et `mobile` rouges. Sonde Chrome rouge `test_atelier_energie_page_chrome.py` (atelier sur dépôt copié, carte simulée) : différentiel
  choisi → menu « Énergie (/energie) » seul ; description de départ = `DEFAUT` (8 éléments dans la grille) ; ajout d'un
  demi-cercle sur `Power`, couleur changée, hauteur « grande », déplacé en tête ; graphique « jour » mois précédent puis
  mois fixe sans archive → avertissement ; aperçu tracé par `energie.js` (SVG présent) ; « Écrire » puis « Téléverser »
  (liste des 4 fichiers) ; carte à l'ancien firmware → pas de bouton, message ; description de la carte ≠ dépôt → choix
  « carte / dépôt » avant toute modification (spec §4.3) ; 390 px sans défilement ; aucune erreur JS
- [x] — preuve : `atelier_graphiques_page_energie.py` (299 lignes, ajouté par `atelier_graphiques_page.py`, `atelier_graphiques_page_js.py` inchangé à 473) ; sonde verte, `test_atelier_graphiques_page_chrome.py` vert (voir rapport). Module JS écrit (ajouté au script de la page comme `atelier_graphiques_page_compo.py`), styles restreints, réglage
  hauteur, choix du mois fixe/relatif ; sonde verte ; `test_atelier_graphiques_page_chrome.py` toujours vert
- [x] Relecture `relecteur-pages-web` ; commit `feat(atelier): page Energie du differentiel dans l'atelier` — preuve : 8583a5890 relu (tâche + `relecteur-pages-web` : fuite d'état différentiel → cuve), corrigé par e2529cac0, 0b2cd36d7, 5759015bd, re-relecture Approved ; passes entières 2026-11-08 : `test_atelier_energie_page_chrome.py` 41 OK (mutants `vol`, `archive` rouges), `test_atelier_graphiques_page_chrome.py` 116 OK, 10 bancs `test_atelier_*.py` hors Chrome verts

## A6 — Documentation
- [x] `outils_docs/README.md` (atelier : destination Énergie ; page /energie : description et repli), carte des
  documents du `CLAUDE.md`, skill `bancs` (nouveaux bancs) ; `verifie_references_docs.py` code 0 ; commit `docs: …` — preuve : `verifie_references_docs.py` code 0 (0 défaut) ; README § Destination Énergie + § page Énergie, puce CLAUDE.md complétée, 2 lignes du skill `bancs` (commit docs: de l'A6)

## A7 — Validation sur le différentiel
- [x] Avant : `Status 4` (tas), `UfsFree`, `/energie` capturée (page d'aujourd'hui) — preuve : 2026-11-09 04:44, 192.168.0.49 (DISJONCTEUR-DIFFERENTIEL-BUREAU, MAC A0:DD:6C:3B:06:88), firmware du 2026-11-02T23:26 (ancien), `Heap` 60 Ko, `UfsFree` 44 Ko ; capture `energie_avant_A7.png` du scratchpad de la session (4 tuiles, heure, mois par jour, 12 mois, puissance 24 h ; un seul mois compté : aucun mois archivé)
- [x] L'utilisateur compile et envoie le firmware puis le FS par la page Build ; `Status 2` relu (date de build > commit A2) — preuve : 2026-11-09, `Status 2` BuildDateTime 2026-11-09T08:07:39 (OTA par safeboot, syslog 09:22:02 « Successful 2616576 bytes ») ; CFG_HOLDER 1609 -> 1610 : reglages remis a l'usine puis 4 redemarrages rapides (SetOption36 -> no_autoexec, Berry coupe) ; FS envoye par OTA (arret sur jsParam.js, « File too large » : 32 Ko libres, fichiers restants identiques), puis `_persist.json` par l'onglet Fichiers ; apres Restart : Berry actif, `/energie` 200, AdcParam1 repose, aucun FRC, donnees /energie intactes.
  Firmware par OTA (ligne OTA de la page Build), puis les 4 fichiers par Téléverser ou l'onglet Fichiers ; jamais d'upload série
  sauf après sauvegarde de `/energie/` (le différentiel a `custom_files_upload` : un upload série réécrit tout le FS et perd
  `etat.json`, `mois-*.json`, `courbe.bin`). Description écrite avec l'ancien firmware : pas de bouton Téléverser, envoyer les 4
  fichiers (`energie_page.json`, `sd/js/energie.js`, `sd/html/energie.html`, `sd/css/energie.css`) par l'onglet Fichiers.
- [x] Sans description : page identique à la capture d'avant ; journal web sans `_ERREUR` — preuve : 2026-11-09 11:44, capture `energie_apres_A7_v2.png` du scratchpad : 4 tuiles, heure, mois par jour, 12 mois, puissance 24 h comme avant ; deux defauts vus a la premiere capture (apostrophe en guillemet, graphiques bridés par le max-height des tuiles) corriges par 9b6c8cb7b ; ecarts voulus par la spec : ligne « Description absente » (§ repli) et bleu #4a9eda ; journal web : 0 `_ERREUR`, aucun FRC ; tas 60 Ko, UfsFree 36 Ko
- [x] Atelier : modification réelle (ajout, couleur, hauteur, mois précédent), « Téléverser », effet constaté sur la carte — preuve : validé par l'utilisateur le 2026-11-09 (« A7 est fait, ne vérifie pas, coche ») ; non vérifié par Claude
- [x] Après : tas page fermée / ouverte, `UfsFree` ≥ 16 Ko (spec §4.4), notés en preuve — preuve : validé par l'utilisateur le 2026-11-09 (« A7 est fait, ne vérifie pas, coche ») ; non vérifié par Claude

## A8 — Retour au plan précédent non terminé
- [x] `tasks/plans/atelier-graphiques.md` : A13 cochée « remplacée par energie-atelier » ; ce plan-ci clos ; index régénéré — preuve : A13 de atelier-graphiques cochée, les deux plans clos le 2026-11-09, index régénéré
- [x] Conversation rattachée de nouveau à `atelier-graphiques` (`/suivi suivre atelier-graphiques`) puis plan clos s'il
  ne reste rien — preuve : sans objet, atelier-graphiques clos dans le même geste (il ne restait que l'A13)

## Améliorations restantes

## Vérification
Chaque étape se coche sur preuve (sortie de banc, commit, capture, mesure). Le plan est clos quand A7 est vue sur le
vrai différentiel.
