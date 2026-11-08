---
chantier: energie-atelier
titre: Atelier des graphiques — page « Énergie » du différentiel (palier 4)
objectif: Que l'atelier reprenne et modifie la page /energie du différentiel (ajouter, restyler, échelle de temps, déplacer, taille) puis l'envoie par Téléverser, sans toucher au comptage
statut: actif
cree: 2026-11-08
maj: 2026-11-08
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
- [x] `energie.js` réécrit (repli `DEFAUT` + ligne de motif ; « À surveiller » 1, 2, 4), gabarit vide dans `energie.html`, — preuve : energie.js 18256 o, energie.html 388 o, energie.css 1697 o ; banc node vert, banc Chrome vert ;
  grille 2 colonnes, hauteurs petite/moyenne/grande et une colonne sous 600 px dans `energie.css`
- [x] `banc_energie.py` (rendu Chrome) vert SANS description (la page d'aujourd'hui : mêmes `data-valeurs`, totaux, tuiles) ; — preuve : banc_energie.py BANC_ENERGIE_COMPLET OK (157 verifications Berry + rendu Chrome sans description, cout du mois sur les 30 jours de novembre) ; banc_energie_description.py OK (14 temoins mutants + 390 px dans un cadre, rouges) ;
  ajout de cas : description modifiée (ordre, couleur, hauteur, mois `decalage` 1), description de 5 000 o → repli dit,
  `f=mois` 404 → « archive effacée », graphique « an » avec l'année la plus ancienne marquée partielle, `total` → titre
  « kWh · € », 390 px sans défilement (« À surveiller » 5)
- [x] Taille de `energie.js` + `.html` + `.css` notée (cible ≤ 20 Ko) ; commit `feat(energie): page Energie pilotee par sa description` — preuve : 20341 o au total (cible 20480), commit feat(energie): page Energie pilotee par sa description ;

## A4 — Atelier, serveur : destination « energie » (`atelier_graphiques_energie.py`)
- [ ] Banc rouge `test_atelier_graphiques_energie.py` (dépôt copié, carte simulée par `get`) :
  `cartes()` inclut le différentiel (FS avec `page_energie`), pas `tasmota32-vr-porte` ; `etat_carte` : description de la
  carte lue, 404 → `None`, page HTML en 200 → `firmware_requis` (« À surveiller » 3) ; `prevoit`/`ecrit` : empreinte,
  refus pendant un build, description invalide refusée ; `plan` : `energie_page.json`, `sd/js/energie.js`,
  `sd/html/energie.html`, `sd/css/energie.css`, `redemarrer` 0, `url` avec `depuis=atelier` ; `catalogue` : sources flash
  et total, champs `direct` de `Status 10` (carte muette → liste de la spec §2), styles de `TYPES`
- [ ] Module écrit ; `atelier_graphiques_web.py` : `cartes()` élargi, routes `/diff` `/ecrire` `/composition` pour
  `destination: "energie"`, `MOTEUR` + `energie.js`/`.html`/`.css`, `/series` du différentiel = `catalogue` ; banc vert ;
  bancs existants de l'atelier verts (`test_atelier_graphiques_*.py`, bout en bout)
- [ ] Commit `feat(atelier): destination Energie du differentiel, cote serveur`

## A5 — Atelier, page : menu « Énergie (/energie) » (`atelier_graphiques_page_energie.py`)
- [ ] Sonde Chrome rouge `test_atelier_energie_page_chrome.py` (atelier sur dépôt copié, carte simulée) : différentiel
  choisi → menu « Énergie (/energie) » seul ; description de départ = `DEFAUT` (8 éléments dans la grille) ; ajout d'un
  demi-cercle sur `Power`, couleur changée, hauteur « grande », déplacé en tête ; graphique « jour » mois précédent puis
  mois fixe sans archive → avertissement ; aperçu tracé par `energie.js` (SVG présent) ; « Écrire » puis « Téléverser »
  (liste des 4 fichiers) ; carte à l'ancien firmware → pas de bouton, message ; description de la carte ≠ dépôt → choix
  « carte / dépôt » avant toute modification (spec §4.3) ; 390 px sans défilement ; aucune erreur JS
- [ ] Module JS écrit (ajouté au script de la page comme `atelier_graphiques_page_compo.py`), styles restreints, réglage
  hauteur, choix du mois fixe/relatif ; sonde verte ; `test_atelier_graphiques_page_chrome.py` toujours vert
- [ ] Relecture `relecteur-pages-web` ; commit `feat(atelier): page Energie du differentiel dans l'atelier`

## A6 — Documentation
- [ ] `outils_docs/README.md` (atelier : destination Énergie ; page /energie : description et repli), carte des
  documents du `CLAUDE.md`, skill `bancs` (nouveaux bancs) ; `verifie_references_docs.py` code 0 ; commit `docs: …`

## A7 — Validation sur le différentiel
- [ ] Avant : `Status 4` (tas), `UfsFree`, `/energie` capturée (page d'aujourd'hui)
- [ ] L'utilisateur compile et envoie le firmware puis le FS par la page Build ; `Status 2` relu (date de build > commit A2)
- [ ] Sans description : page identique à la capture d'avant ; journal web sans `_ERREUR`
- [ ] Atelier : modification réelle (ajout, couleur, hauteur, mois précédent), « Téléverser », effet constaté sur la carte
- [ ] Après : tas page fermée / ouverte, `UfsFree` ≥ 16 Ko (spec §4.4), notés en preuve

## A8 — Retour au plan précédent non terminé
- [ ] `tasks/plans/atelier-graphiques.md` : A13 cochée « remplacée par energie-atelier » ; ce plan-ci clos ; index régénéré
- [ ] Conversation rattachée de nouveau à `atelier-graphiques` (`/suivi suivre atelier-graphiques`) puis plan clos s'il
  ne reste rien

## Améliorations restantes

## Vérification
Chaque étape se coche sur preuve (sortie de banc, commit, capture, mesure). Le plan est clos quand A7 est vue sur le
vrai différentiel.
