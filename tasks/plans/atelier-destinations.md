---
chantier: atelier-destinations
titre: Atelier des graphiques — destination « Graphiques » et bouton « Téléverser »
objectif: Poser un graphique de l'atelier sur une page dédiée, sur /graphiques ou sur une nouvelle page, puis l'envoyer à la carte par la page Build qui prépare tout et attend le clic Envoyer
statut: actif
cree: 2026-11-04
maj: 2026-11-05
---
# Atelier des graphiques — destination « Graphiques » et bouton « Téléverser »

## Contexte
Spec validée par l'utilisateur le 2026-11-04 : `docs/superpowers/specs/2026-11-04-atelier-destinations-televersement-design.md`
(décisions du rédacteur §7, à appliquer telles quelles). Elle complète `2026-11-03-atelier-graphiques-design.md` et
remplace son palier 2 ; l'encadré d'accueil (palier 3) est abandonné. Palier 1 clos (plan `atelier-graphiques.md`, A9).
Exécution : `superpowers:subagent-driven-development` (choix de l'utilisateur), une action = une tâche ; lire la spec
avant chaque action.

**Architecture.** `/graphiques` garde son tracé pour ses 4 types ; un graphique marqué `"moteur": "pages"` (schéma des
pages dédiées) est validé par `pagesGraphiquesValidation.be` et tracé par `PagesGraphiques.optionDe`, réutilisés tels
quels. L'atelier écrit soit `pages_graphiques.json` (pages dédiées), soit la clé `graphiques` de `graphiques.json` (les
autres clés de ce fichier intactes). Le bouton « Téléverser » ouvre `http://127.0.0.1:7700/?env=&depuis=atelier&fichiers=` ;
la page Build construit le FS, coche, affiche le bandeau et n'envoie rien.

### Contraintes globales (valent pour chaque action)
- Fichiers ≤ 500 lignes. `data/sd/js/graphiques.js` est à **500** : sa délégation au moteur va dans un fichier neuf
  (`data/sd/js/graphiques_moteur.js`), `graphiques.js` ne gagne aucune ligne nette. `atelier_graphiques_page_js.py`
  (470) : le JS neuf de l'atelier va dans un module neuf. `build_page.py` est une exception listée au CLAUDE.md :
  tout ajout y est reporté dans cette exception (nombre de lignes et raison).
- Aucune dépendance nouvelle. Python des bancs `outils_pc/` : `"$USERPROFILE/.platformio/penv/Scripts/python.exe"` ;
  bancs `berry/` : `python`. Bancs sur copies temporaires, jamais le vrai dépôt.
- Berry : charte des logs (CLAUDE.md « Logs Berry ») ; `data/fs/graphiquesFonctions.be`, `pagesGraphiques*.be` :
  modification accordée pour ce chantier ; aucun autre `data/fs/*.be`.
- Jamais de `pio run` par Claude : builds par la page Build ; jamais pendant un build de l'utilisateur.
- Anti-CSRF des outils (`acces_web.py`) sur toute route POST nouvelle ; aucun envoi à une carte sans clic.
- Commits en français sans accents ; ne pas commiter `modules.h`, `tasmota_defines_for_berry.*`, `lessons.md`.

### Points d'attention (Review Focus)
1. Composition `/graphiques` existante (P4 : 4 types, `series: "autres"`) : rendu inchangé — attendus du banc
   `banc_graphiques.py` non modifiés.
2. Composition modifiée sur la carte depuis le dernier envoi : jamais écrasée sans le choix explicite (spec §4.3).
3. URL de la page Build forgée (`env` inconnu, `fichiers` avec `..`, chemin hors image, liste vide) : rien coché,
   message, aucun `pio` lancé pour un env inconnu.
4. Build déjà en cours à l'ouverture du lien : pas de second `pio` ; la construction démarre à la fin du build.
5. Carte sans historique : « Graphiques » absent du menu ; carte hors ligne : bandeaux « non vérifiée » (§4.3, §7.2).

## A1 — Cenv : liste `pages_graphiques_moteur` et écriture de l'atelier
- [x] Banc rouge (`test_atelier_graphiques_ecriture.py`) : un env à historique sans page n'exclut plus
  `pages_graphiques_moteur` ; un env sans historique ni page l'exclut ; première page dédiée d'un env sans historique
  → les deux exclusions levées ; dernière page retirée → état exclu octet pour octet (spec §7.3) — preuve : 14 échecs avant le code (rapport A1), `test_historique_sans_page`
- [x] `platformio_tasmota_cenv.ini` : scission une fois (`pages_graphiques_moteur` = `pages_graphiques.js`,
  `pages_graphiques_formule.js`, `pagesGraphiquesValidation.be` ; `pages_graphiques` = le reste), exclusion par env
  selon la règle ; `atelier_graphiques_ecriture.py` gère les deux listes (`_exclut`, `_leve`, `_retire`, `_controle`) — preuve : 3edb8792e, 3a683093d
- [x] Banc vert, `--exclusions` sur le vrai dépôt sans écart, `berry/banc_demarrage.py` vert — preuve : banc « 0 echec(s) : VERT », `--exclusions` « rien a faire », 4 références de banc_demarrage (ligne `sources` seule) mises à jour dans 3edb8792e

## A2 — Carte : validation des graphiques « moteur pages » dans `/graphiques`
- [x] Banc rouge (`berry/banc_graphiques.py` + `.be`) : composition mixte acceptée ; graphique `"moteur": "pages"`
  invalide refusé avec le motif du validateur des pages ; compositions existantes du banc acceptées à l'identique — preuve : 2 ECHEC avant le code (rapport A2)
- [x] `graphiquesFonctions::valideComposition` : forme atelier validée par `pagesGraphiquesValidation` (chargé le temps
  de la validation, puis relâché) et recopiée telle que validée ; forme actuelle inchangée — preuve : 4c33b1ab6, e81cb8286, aace5733e ; écart : validateur gardé par `import` (Berry ne décharge pas un module), décision du 2026-11-05
- [x] Banc vert ; `verifie_berry.py` sans erreur ni écart de charte — preuve : `BANC_GRAPHIQUES: OK` (Chrome compris), `BANC_PAGES_GRAPHIQUES: OK`, verifie_berry 0 erreur

## A3 — Carte : tracé et mode édition des graphiques « moteur pages »
- [ ] Banc rouge (sonde Chrome de `banc_graphiques.py`, ou sonde dédiée sur le modèle de `test_pages_graphiques_chrome.py`) :
  composition mixte → les graphiques actuels rendus comme avant (attendus inchangés), un graphique « cadran » et une
  « courbe » forme atelier tracés par le moteur, aucune exception JS ; en mode édition, tuile atelier déplaçable et
  retirable, réglages non éditables avec la mention « réglages dans l'atelier »
- [ ] `data/sd/js/graphiques_moteur.js` : données `/histo` (jour, mois, `?p=direct`) mises à la forme `{t, valeurs}`,
  `calc:` par `PagesFormule`, appel `PagesGraphiques.optionDe` ; chargement de `pages_graphiques.js` et
  `pages_graphiques_formule.js` par la page `/graphiques` seulement si un graphique atelier est présent ;
  `graphiques.js` et `graphiques_edition.js` : point d'accroche minimal (aucune ligne nette pour `graphiques.js`)
- [ ] Bancs verts (`banc_graphiques.py`, `test_pages_graphiques.mjs`, `test_pages_graphiques_chrome.py`)

## A4 — Atelier : écriture vers `/graphiques` et composition de la carte
- [ ] Banc rouge (`test_atelier_graphiques_ecriture.py`, `_web.py`) : destination `graphiques` → seule la clé
  `graphiques` de `data/<lieu>/<carte>/graphiques.json` change (autres clés et forme du texte gardées) ; graphique
  ajouté en forme atelier `"moteur": "pages"` ; retrait d'un graphique ; empreinte périmée → 409 ; carte sans
  historique → 400
- [ ] Lecture de la composition de la carte en ligne, comparaison normalisée (clés triées) avec le dépôt, réponse
  `{identique | differente (diff) | non_verifiee}` ; « Partir de la version de la carte » recopie sa composition
  (validée par le validateur du dépôt, sinon indisponible avec le motif) avant l'ajout (spec §4.3, §7.6)
- [ ] Bancs verts

## A5 — Atelier : menu « Page » et choix carte/dépôt dans la page
- [ ] Banc rouge (`test_atelier_graphiques_page_chrome.py`) : menu = pages dédiées, « Graphiques (/graphiques) »
  (si historique), « Autre… (nouvelle page) » ; bouton « + Page » retiré ; destination Graphiques → Adresse, Titre page,
  Accès, Solidifier masqués ; composition différente → diff et les deux choix, « Garder celle du dépôt » dit la perte
- [ ] Module JS neuf de l'atelier (le 470 lignes ne grossit pas au-delà de 500) ; mode sombre respecté
- [ ] Sonde verte, captures clair et sombre relues

## A6 — Atelier : bouton « Téléverser »
- [ ] Banc rouge : liste des fichiers calculée (description touchée ; `autoexec.be` si modifié ; fichiers du moteur
  entrés dans le FS de l'env, plus ceux absents de la carte en ligne, spec §7.2) ; drapeau « redémarrer » selon §7.8 ;
  URL `http://127.0.0.1:7700/?env=&depuis=atelier&fichiers=&redemarrer=` ; page Build arrêtée → message « lancer la
  page Build par l'annuaire »
- [ ] Bouton visible seulement après une écriture réussie ; ouvre un nouvel onglet ; chemins dans le FS de la carte
- [ ] Bancs verts

## A7 — Page Build : arrivée depuis l'atelier
- [ ] Banc rouge (`test_build_web.py`, `test_build_page_fichiers_chrome.py`) : `depuis=atelier` → env sélectionné,
  onglet « Fichiers », bandeau exact de la spec §5, `buildfs` lancé par `POST /lancer` (en-têtes habituels), à la fin
  de l'image : cochés exactement les fichiers de la liste, « Redémarrer » selon le paramètre, **aucun envoi** ;
  fichier de la liste absent de l'image → signalé ; paramètres hostiles → ignorés avec message, rien de lancé ;
  build en cours → attente puis lancement (flux `/flux`)
- [ ] Code dans `build_page_fichiers.py` (ou module neuf) ; exception de `build_page.py` au CLAUDE.md mise à jour si
  ce fichier grossit
- [ ] Bancs verts (`test_build_*.py` concernés + sondes Chrome)

## A8 — Documentation
- [ ] `outils_docs/README.md` § « Atelier des graphiques » : menu Page, destination Graphiques, composition carte /
  dépôt, bouton Téléverser ; § page Build : arrivée depuis l'atelier
- [ ] `CLAUDE.md` (carte des documents : atelier, page Build, listes du cenv) ; `.claude/skills/bancs/SKILL.md` si
  un banc est ajouté ; `verifie_references_docs.py` sans défaut

## A9 — Validation sur les cartes
- [ ] Place du FS mesurée sur les 6 cartes à historique avec les fichiers du moteur (blocs de 4 Ko) ; arrêt et
  question à l'utilisateur sous 10 % libres (spec §7.10)
- [ ] P4 : composition existante intacte + un graphique atelier (style hors des 4) envoyé par « Téléverser » ;
  `/graphiques` sous Chrome sans exception JS, capture ; journal web sans `_ERREUR`
- [ ] Cuve : modification d'une page dédiée envoyée par « Téléverser » (redémarrage non coché), effet constaté

## A10 — Retour au plan précédent non terminé
- [ ] Plan `tasks/plans/atelier-graphiques.md` (palier 1 clos, A13 restante) : A11 cochée « remplacée par
  atelier-destinations », renvoi vérifié ; ce plan-ci passé en `statut: clos`, index régénéré
- [ ] Conversation rattachée de nouveau à `atelier-graphiques` (`/suivi suivre atelier-graphiques`) ; prochaine action
  proposée à l'utilisateur : A13 (palier 4, ESP32 classiques, à détailler au début du palier)

## Améliorations restantes
- [ ] [projet] Proposer un agent `.claude/agents/` de relecture des pages web générées si la même relecture revient

## Vérification
Chaque étape se coche sur preuve (sortie de banc, commit, capture). Le plan est clos quand A9 est vue sur le P4 et la
cuve.
