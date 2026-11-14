---
chantier: menage-page
titre: Page « Ménage du dépôt » dans l'annuaire des outils (lancer et lire un audit de rangement)
objectif: Une page de l'annuaire lance l'agent auditeur-menage avec des paramètres choisis, affiche ses propositions avec la preuve et ce qu'elles casseraient, et mémorise celles que l'utilisateur garde
statut: actif
cree: 2026-11-14
maj: 2026-11-14
famille: methode
liens: build-reparations, atelier-visuels
---
# Page « Ménage du dépôt »

> Pour l'exécutant : skill `superpowers:subagent-driven-development` (recommandé) ou `superpowers:executing-plans`.
> Les étapes se cochent avec `— preuve : …` (voir `_FORMAT.md`). Lancer les bancs avec le Python de PlatformIO
> (`~/.platformio/penv/Scripts/python.exe`) depuis la racine du dépôt. Aucun `pio run` pendant ce chantier.

## Contexte

Demande de l'utilisateur du 2026-11-14, après la création de l'agent `.claude/agents/auditeur-menage.md` et de la commande
`/menage` (lecture seule, `memory: local`). Une page évite de taper les consignes à chaque audit et rend le rapport lisible.

Décisions prises :
- **Version 1 = lecture seule.** La page lance l'audit, affiche le rapport, mémorise « garder ». Elle n'écrit RIEN dans le dépôt
  (aucun `git mv`, `git rm`). L'application d'un lot est la **version 2**, à décider après avoir jugé la fiabilité des
  propositions sur au moins deux audits réels (action A7).
- **Deux consignes toujours passées à l'agent**, aussi dans `auditeur-menage.md` : (1) tout fichier modifié ou non suivi par git,
  ou touché depuis moins de N jours (N réglable, 3 par défaut), est « en cours, à ne pas toucher » et n'est jamais proposé ;
  (2) un plan `statut: actif` n'est jamais proposé à l'archivage et les fichiers qu'il cite ne sont pas des orphelins.
- Modèle d'outil : le même que les autres pages (tuile de l'annuaire, `acces_web.py`, cible Custom détachée, tâche VS Code).
  Précédent pour lancer Claude depuis une page : l'atelier des écrans (`atelier_ecrans_remarques.py`, `claude -p` en LECTURE
  SEULE : outils de lecture, hooks coupés, jamais `bypassPermissions`, depuis ce PC seulement).
- Port : 7995 proposé (7500, 7700, 7800, 7900, 7950, 7960, 7970, 7980, 7990 sont pris) ; à vérifier par `PORT_DEFAUT` des `*_web.py`.
- Refus de lancer pendant un build (`pio`/`scons` vivant) : les listes de fichiers bougent, et la règle du dépôt interdit d'y ajouter de la charge.

Fichiers prévus (modules neufs, chacun sous 500 lignes) : `outils_pc/menage_web.py` (serveur, routes), `menage_page.py` (HTML/CSS/JS),
`menage_lancement.py` (commande `claude -p`, rapport structuré), `menage_rapport.py` (validation du JSON de l'agent, filtre des
secrets), `menage_memoire.py` (liste « à garder »), `build/cible_menage.py`.

## A1 — Contrat du rapport et consignes de l'agent
- [x] Format JSON du rapport de l'agent : liste de propositions `{id, categorie, chemin, constat, preuve, action, casserait, risque, en_cours}` + `resume` + `non_verifie`, validé par un schéma `outils_docs/schemas/menage_rapport.schema.json` — preuve : outils_docs/schemas/menage_rapport.schema.json + outils_pc/menage_rapport.py::valide
- [x] `auditeur-menage.md` : produire ce JSON (en plus du texte), ajouter les deux consignes (en cours, plans actifs) et le paramètre « ancienneté en jours » — preuve : .claude/agents/auditeur-menage.md (paramètres, deux consignes, FORMAT DE SORTIE)
- [x] `commands/menage.md` : passer les paramètres (zone, catégories, ancienneté) et décrire le JSON — preuve : .claude/commands/menage.md étape 2 (zone, anciennete_jours, gardes, JSON)
- [x] Banc `outils_pc/test_menage_rapport.py` : rapports valides et invalides (champ manquant, chemin hors dépôt, `..`, risque inconnu), avec mutants (validation retirée) — preuve : test_menage_rapport.py VERT (code 0), 2 mutants (chemin_sur, masque) acceptent le cas hostile, banc rouge sur un premier masquage incomplet corrigé

## A2 — Lancement de l'audit par la page
- [ ] `menage_lancement.py::lance` : `claude -p` en lecture seule (outils Read, Grep, Glob, Bash restreint ; hooks coupés ; jamais `bypassPermissions`), paramètres validés contre une liste blanche (dossiers, catégories, entier borné pour l'ancienneté, modèle parmi sonnet/opus/haiku)
- [ ] Refus si un build tourne (appel de la vraie détection de `build_serie`, jamais un `builds_en_cours` factice), refus si un audit est déjà en cours, délai maximal avec arrêt propre du processus fils
- [ ] Rapport lu, validé (A1), chemins ramenés au dépôt, valeurs ressemblant à des secrets masquées avant d'aller à la page
- [ ] Banc `test_menage_lancement.py` avec un faux `claude` (processus qui rend un JSON fixe) : succès, JSON invalide, délai dépassé, build en cours, double lancement

## A3 — Mémoire « à garder »
- [ ] `menage_memoire.py` : liste des chemins gardés dans `%LOCALAPPDATA%\outils_tasmota\menage\garde.json` (hors dépôt, écriture atomique, sauvegarde horodatée)
- [ ] L'agent reçoit cette liste en entrée et ne repropose pas ces chemins ; un chemin gardé qui n'existe plus est retiré à la lecture
- [ ] Banc `test_menage_memoire.py` : ajout, retrait, fichier corrompu, écriture interrompue

## A4 — Serveur et routes
- [ ] `menage_web.py` : `GET /` (page), `GET /etat`, `POST /lancer`, `GET /rapport`, `POST /garder`, `POST /ignorer` ; règle d'accès de `acces_web.py` (en-tête `X-Menage: 1`, même origine, jeton depuis un autre appareil) ; exception inattendue = 500 avec son message
- [ ] Fiche de présence de l'outil pour l'annuaire, `--sans-navigateur`, `--local`
- [ ] Banc `test_menage_web.py` : refus sans en-tête, mauvaise origine, paramètre hors liste blanche, client distant sans jeton

## A5 — Page
- [ ] Paramètres : périmètre (cases par dossier), catégories de contrôles, ancienneté du « en cours », modèle et effort ; valeurs précédentes mémorisées dans le navigateur (`localStorage` gardé par try/catch)
- [ ] Rapport : tableau trié par risque, une ligne par proposition (chemin, constat, preuve, ce que ça casserait, avantages/inconvénients), filtres par catégorie et par risque, lignes « en cours » repliées
- [ ] Actions de version 1 : « Garder » (A3), « Ignorer cette fois », « Copier la liste » ; aucun bouton qui écrit dans le dépôt
- [ ] Textes de la page échappés (aucun `innerHTML` sur une valeur du rapport), mode sombre, avancement et bouton Arrêter pendant l'audit
- [ ] Sonde Chrome hermétique `test_menage_page_chrome.py` (faux `claude`), Chrome headless `sonde_*` arrêtés après coup (compter les `HasExited` faux 15 s après)

## A6 — Branchement dans l'annuaire et dans les outils
- [ ] Tuile de l'annuaire (groupe « Maintenance »), tâche VS Code « Outil : ménage du dépôt », cible Custom détachée `build/cible_menage.py` (`NOM_CIBLE` ajouté à `CIBLES_OUTILS` de `.claude/hooks/garde_build.py`, `garde_build` vérifie la liste)
- [ ] Banc `build/test_cible_menage.py`, `test_garde_build.py` vert
- [ ] Entrée dans la Carte des documents de `CLAUDE.md`, section dans `outils_docs/README.md`, ligne dans `outils_docs/SOUS_AGENTS.md`
- [ ] Relecture par `relecteur-outils-python` et `relecteur-pages-web` avant commit
- [ ] Commit (avec `controleur-secrets` puis `preparateur-push` avant le push)

## A7 — Essais réels et décision sur la version 2
- [ ] Deux audits réels (travail en cours dans l'arbre) : combien de propositions, combien de faux positifs, combien de « en cours » correctement écartés
- [ ] Décision de l'utilisateur sur la version 2 (appliquer un lot par `git mv` et `git rm` : diff d'abord, refus pendant un build, refus sur fichier modifié, `verifie_references_docs.py` ensuite) ; si oui, nouveau plan

## Améliorations restantes
- [ ] [projet] Version 2 : application d'un lot depuis la page (selon A7)
- [ ] [projet] Planifier l'audit une fois par mois (tâche Windows `claude -p`, rapport déposé dans `tasks/`), si les premiers rapports sont utiles

## Vérification
Tous les bancs verts avec le Python de PlatformIO ; sonde Chrome verte et Chrome orphelins arrêtés ; `verifie_references_docs.py` code 0 ;
`node .claude/hooks/index_plans.mjs --verifier` code 0 ; la page n'écrit rien dans le dépôt (aucune route d'écriture hors la liste
« à garder » hors dépôt) ; un audit lancé pendant un build est refusé.
