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
- [x] `menage_lancement.py::lance` : `claude -p` en lecture seule (outils Read, Grep, Glob, Bash restreint ; hooks coupés ; jamais `bypassPermissions`), paramètres validés contre une liste blanche (dossiers, catégories, entier borné pour l'ancienneté, modèle parmi sonnet/opus/haiku) — preuve : outils_pc/menage_lancement.py::parametres, ::OPTIONS (Read,Grep,Glob,Bash limite, Write/Edit refuses, dontAsk, sans hooks, budget 3 $) ; banc : 10 cas de parametres hostiles refuses, options lues par un faux claude
- [x] Refus si un build tourne (appel de la vraie détection de `build_serie`, jamais un `builds_en_cours` factice), refus si un audit est déjà en cours, délai maximal avec arrêt propre du processus fils — preuve : menage_lancement.py::Audit.lance (builds_en_cours injecte, double lancement), ::arrete, delai ; banc : refus pendant un build, 2e audit refuse, arret propre, delai de 2 s depasse, aucun processus orphelin
- [x] Rapport lu, validé (A1), chemins ramenés au dépôt, valeurs ressemblant à des secrets masquées avant d'aller à la page — preuve : menage_lancement.py::_traite passe par menage_rapport.valide ; banc : rapport invalide (chemin ..) et sortie sans JSON refuses, erreur claude et code 1 propres
- [x] Banc `test_menage_lancement.py` avec un faux `claude` (processus qui rend un JSON fixe) : succès, JSON invalide, délai dépassé, build en cours, double lancement — preuve : test_menage_lancement.py VERT (code 0) ; mutants : sans garde de build et sans liste blanche acceptent le cas hostile

## A3 — Mémoire « à garder »
- [x] `menage_memoire.py` : liste des chemins gardés dans `%LOCALAPPDATA%\outils_tasmota\menage\garde.json` (hors dépôt, écriture atomique, sauvegarde horodatée) — preuve : outils_pc/menage_memoire.py::Memoire (garde.json hors depot, ecriture atomique par fichier temporaire + os.replace, copie garde-<date>.json, 20 au plus, fichier illisible mis de cote)
- [x] L'agent reçoit cette liste en entrée et ne repropose pas ces chemins ; un chemin gardé qui n'existe plus est retiré à la lecture — preuve : menage_memoire.py::charge retire les chemins disparus et reecrit le fichier ; menage_lancement.py::Audit(gardes=...) les met dans la consigne (test_menage_lancement.py : « data/vieux.txt » present dans l'entree du faux claude) ; branchement sur Memoire.charge fait en A4
- [x] Banc `test_menage_memoire.py` : ajout, retrait, fichier corrompu, écriture interrompue — preuve : test_menage_memoire.py VERT (code 0) : ajout, doublon, anti-slash, .. et absolu refuses, retrait, disparu retire, fichier corrompu, forme inattendue, ecriture interrompue (ancien contenu intact, aucun .tmp), liste pleine ; mutant sans controle de chemin vu

## A4 — Serveur et routes
- [x] `menage_web.py` : `GET /` (page), `GET /etat`, `POST /lancer`, `GET /rapport`, `POST /garder`, `POST /ignorer` ; règle d'accès de `acces_web.py` (en-tête `X-Menage: 1`, même origine, jeton depuis un autre appareil) ; exception inattendue = 500 avec son message — preuve : outils_pc/menage_web.py : routes GET / /options /etat /rapport /gardes, POST /lancer /arreter /garder /degarder /ignorer ; X-Menage, origine, hote_autorise, corps borne a 16 Ko ; page provisoire menage_page.py (A5) ; banc : 40 verifications OK
- [x] Fiche de présence de l'outil pour l'annuaire, `--sans-navigateur`, `--local` — preuve : fiche de presence ecrite par acces_web.Acces.annonce (meme mecanisme que les autres outils), options --sans-navigateur et --local par acces_web.ajoute_options ; tuile de l'annuaire en A6
- [x] Banc `test_menage_web.py` : refus sans en-tête, mauvaise origine, paramètre hors liste blanche, client distant sans jeton — preuve : test_menage_web.py VERT (code 0) : sans en-tete 403, autre origine 403, Host etranger 403, client distant sans jeton 403 (avec jeton 303), parametres hostiles 400, build en cours 409, 2e lancement 409, mutant sans controle d'origine vu

## A5 — Page
- [x] Paramètres : périmètre (cases par dossier), catégories de contrôles, ancienneté du « en cours », modèle et effort ; valeurs précédentes mémorisées dans le navigateur (`localStorage` gardé par try/catch) — preuve : menage_page.py : zones, contrôles, ancienneté, modèle, effort ; mémorisés par localStorage (try/catch) ; sonde : une case par dossier (6) et par contrôle (7), refus côté page sans dossier coché
- [x] Rapport : tableau trié par risque, une ligne par proposition (chemin, constat, preuve, ce que ça casserait, avantages/inconvénients), filtres par catégorie et par risque, lignes « en cours » repliées — preuve : menage_page.py::rend : tri faible → élevé, filtres catégorie et risque, bloc « en cours » replié ; sonde : 2 actives + 1 en cours, filtres OK, témoin sans filtre de risque détecté
- [x] Actions de version 1 : « Garder » (A3), « Ignorer cette fois », « Copier la liste » ; aucun bouton qui écrit dans le dépôt — preuve : menage_page.py : Garder / Ignorer cette fois / Retirer / Copier la liste, aucun bouton qui écrit dans le dépôt ; sonde : ignorer, garder, liste « Gardes », retirer, en cours sans bouton (témoin en-cours-actions détecté)
- [x] Textes de la page échappés (aucun `innerHTML` sur une valeur du rapport), mode sombre, avancement et bouton Arrêter pendant l'audit — preuve : textContent partout (el()), thème clair/sombre mémorisé, avancement + Arrêter, S.gen contre les réponses dépassées ; sonde : texte hostile <img onerror> reste du texte (témoin innerHTML détecté), thème mémorisé, téléphone 375 px sans défilement horizontal
- [x] Sonde Chrome hermétique `test_menage_page_chrome.py` (faux `claude`), Chrome headless `sonde_*` arrêtés après coup (compter les `HasExited` faux 15 s après) — preuve : test_menage_page_chrome.py VERT (code 0), 3 témoins détectés chacun par son test, Chrome orphelins 0 apres 15 s (nettoyage par profil dans Montage.ferme) ; un timeout DevTools isolé au 1er essai après la modification du nettoyage, non reproduit au 2e

## A6 — Branchement dans l'annuaire et dans les outils
- [x] Tuile de l'annuaire (groupe « Ateliers »), tâche VS Code « Outil : menage du depot », cible Custom détachée `build/cible_menage.py` (`NOM_CIBLE` ajouté à `CIBLES_OUTILS` de `.claude/hooks/garde_build.py`, `garde_build` vérifie la liste) — preuve : annuaire_registre.py entrée « menage » (7995), tâche .vscode/tasks.json, build/cible_menage.py, 'menage' dans CIBLES_OUTILS ; test_annuaire.py VERT (16 outils, 2 passes) ; garde_build vérifié par test_garde_build.py
- [x] Banc `build/test_cible_menage.py`, `test_garde_build.py` vert — preuve : test_cible_menage.py VERT (4 cas : autre service, déjà lancée, démarrage détaché, démarrage raté), test_garde_build.py VERT
- [x] Entrée dans la Carte des documents de `CLAUDE.md`, section dans `outils_docs/README.md`, ligne dans `outils_docs/SOUS_AGENTS.md` — preuve : CLAUDE.md (menage_web.py), outils_docs/README.md § Ménage du dépôt, SOUS_AGENTS.md ; verifie_references_docs.py : 0 défaut
- [x] Relecture par `relecteur-outils-python` et `relecteur-pages-web` avant commit — preuve : relecteur-outils-python : rien de bloquant (2 renvois corriges) ; relecteur-pages-web : XSS/CSRF/Host sains, 3 points corriges (Chrome orphelins, couleurs en variables, rapport efface apres POST reussi), sonde VERT x2, 0 Chrome sonde_ a +15 s
- [x] Commit (avec `controleur-secrets` puis `preparateur-push` avant le push) — preuve : commits A6 + correctifs, controleur-secrets sans rien a signaler avant chacun ; preparateur-push reste a lancer avant le push (aucun push fait)

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
