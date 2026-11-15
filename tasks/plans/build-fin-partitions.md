---
chantier: build-fin-partitions
titre: Pastille d'occupation des partitions à la fin d'une compilation (page Build)
statut: actif
cree: 2026-11-15
maj: 2026-11-15
objectif: Montrer dans la ligne de chaque env compilé « Flash 87 % · RAM 32 % » (orange dès 90 %, rouge dès 95 %), avec un détail complet des partitions au clic
famille: build
spec: aucune
liens: temps-compilation
---
# Pastille d'occupation en fin de compilation

## Contexte
Variante D choisie par l'utilisateur (maquettes `outils_docs/build_fin_partitions/`). Aucun changement serveur : la série
enregistre déjà l'analyse mémoire à la fin d'une compilation réussie (`build_serie.py`, appel de `build_memoire.enregistre`),
la page lit `GET /memoire?env=`. Code dans `outils_pc/build_page_fin_memoire.py`, 6 lignes ajoutées à `build_page.py`.

## A1 — Pastille et fenêtre de détail
- [x] Sonde Chrome écrite d'abord, rouge avant le code — preuve : test_build_page_fin_memoire_chrome.py, « sonde : deroulement » KO avant branchement
- [x] Module `build_page_fin_memoire.py` + branchement dans `build_page.py` — preuve : sonde VERT (13 contrôles)
- [x] Seuils, XSS, Échap, clic dehors, thèmes clair et sombre, env sans relevé — preuve : contrôles de la sonde, mutants rouges (seuil, innerHTML)
- [ ] Essai réel après une vraie compilation depuis la page :7700 (l'utilisateur, aucun build lancé ici)

## A2 — Retour au plan en cours avant ce chantier
- [ ] Reprendre le plan `build-reparations` : essai réel du diagnostic IA sur le journal `20261115-043620-tasmota-cave-lumiere-porte-compiler.log` (A6, dernière case), case « Relancer après réparation », puis A7 (documentation, relecteurs, essai hors série, commit) : `/suivi suivre build-reparations`

## Améliorations restantes
- [ ] [projet] Écart avec le build précédent (variante C : champ `avant` à enregistrer par `build_memoire.enregistre`)
- [ ] [projet] Accessibilité de la fenêtre : focus à l'ouverture, retour à la pastille, piège de Tab (relecteur-pages-web, 2026-11-15)
- [ ] [projet] Garder le relevé : ignorer un `date_build` antérieur au début de l'env, vérifier le bloc après l'`await`, rafale au rejeu
- [ ] [projet] Couleurs de `FM_COUL` et du voile : variables CSS du thème au lieu de valeurs en dur
- [ ] [projet] Sonde : filtre `ERR_CONNECTION_REFUSED` trop large, test de classe `fm-alerte` laxiste
