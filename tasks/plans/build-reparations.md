---
chantier: build-reparations
titre: Réparation automatique des pannes de la page Build
objectif: La page Build reconnaît une panne de compilation connue, la corrige, le dit sur la page et relance ; panne inconnue : diagnostic par l'IA et catalogue qui s'enrichit
statut: actif
cree: 2026-11-14
maj: 2026-11-14
famille: build
liens: ecran-cave-vues-commandes, facade-garage-capteurs
spec: 2026-11-14-build-reparations-design.md
---
# Réparation automatique des pannes de la page Build

> Pour l'exécutant : skill `superpowers:subagent-driven-development` (recommandé) ou `superpowers:executing-plans`.
> Les étapes se cochent avec `— preuve : …` (voir `_FORMAT.md`). Lancer les bancs avec le Python de PlatformIO
> (`~/.platformio/penv/Scripts/python.exe`) depuis la racine du dépôt.

**Spec** : `docs/superpowers/specs/2026-11-14-build-reparations-design.md` (lire en entier, dont « Précisions après relecture »).

## Contexte

Déclencheur : deux échecs de la compilation du P4 du garage sur `PermissionError ... modules.h` (verrou passager).
Branchement : `outils_docs/scripts_python/outils_pc/build_serie.py::Serie._execute_env`, quand `_lance_pio` rend
`ok` faux (avant l'événement `echec`). Code neuf dans des modules neufs (`build_serie.py`, `build_page.py` et `build_web.py`
dépassent 500 lignes, exceptions du CLAUDE.md : ne pas les faire grossir de plus de quelques lignes chacun).

Contraintes globales (valeurs de la spec) :
- 2 relances au plus par étape et par env ; la même règle ne s'applique pas deux fois si la panne revient identique
  (signature = id de règle + dernière ligne d'erreur) ; un arrêt demandé prime.
- Étapes relancées : seulement un fils `pio` raté (compilation, liens, buildfs). Jamais `upload` / `erase_upload` par COM,
  jamais OTA ; un « Permission denied » sur un port COM n'entre pas dans le motif de base (seul un chemin du dépôt compte).
- Liste fermée d'actions de règle : `attendre {secondes}`, `libere_verrou {}`, `vide_build {}`. Aucune commande libre.
- Fermeture de processus : liste blanche `cpptools-srv.exe`, `cpptools.exe` ; jamais la page, le `pio`/`scons`/`python`
  de la série, `claude` ; un `pio`/`scons`/`python` d'une autre origine : on attend sa fin (`_attend_builds`), on ne le ferme
  jamais ; tout autre processus : demande Fermer / Attendre / Annuler. Sans réponse en 10 min : env en échec, série continue.
- Règles de base : `outils_docs/schemas/reparations_build.json` (suivi par git, jamais écrit par la page). Règles IA, compteurs,
  suppressions : `%LOCALAPPDATA%\outils_tasmota\build\reparations.json`.
- Clients distants (jeton) : lecture seule ; fermer un processus, lancer ou appliquer un diagnostic IA = ce PC seulement.
- Aucun mot de passe dans l'extrait envoyé à l'IA ni dans le catalogue. Rien n'est écrit dans `data/`.
- Commits en français, sans accents, sans trailer ; `git add` par chemins explicites. Pas de build en parallèle : les bancs
  n'utilisent que le faux `pio` (`build_faux_pio.py`).

## Review Focus

Entrées que la spec laisse ouvertes et qui peuvent gêner, avec le test attendu dans la tâche indiquée :
- Journal vide ou tronqué, ou chemin du motif absent : aucune règle ne s'applique, comportement actuel (A1, A3).
- Motif de règle à retour arrière catastrophique sur un journal de 100 000 lignes : la correspondance se fait sur la fin
  du journal (50 lignes) avec expression compilée et validée à l'ajout (A1).
- Processus mort entre le repérage et la fermeture : pas d'exception, on relance (A2).
- Réponse au choix après expiration des 10 min ou deux fois : 409, état inchangé (A3, A4).
- Rechargement de la page pendant une réparation ou un choix : l'état se reconstruit par les événements rejoués (A5).
- Réponse de l'IA qui n'est pas du JSON, ou une règle dont le motif ne correspond pas au journal fourni : rien n'est
  proposé à appliquer (A6).

## A1 — Catalogue et correspondance (`build_reparations.py`)
- [x] Écrire d'abord `test_build_reparations.py` (rouge) : `charge_catalogue(base, local)` fusionne règles de base et locales, — preuve : test_build_reparations.py rouge (ModuleNotFoundError) puis vert, commit 48b887f18
  refuse une action hors liste, un motif qui ne compile pas, une action sans paramètre requis (`attendre` sans `secondes`) ;
  `cherche(regles, journal, etape, env)` rend la règle dont le motif correspond à la fin du journal (50 dernières lignes)
  et dont `etapes` contient l'étape ; journal vide -> `None` ; `filtre_secrets(texte)` masque la valeur d'une ligne
  `STA_PASS`, `PASSWORD`, `MQTT_PASS`, `OTA_PASS`, `token` (modèles du filtre de `etiquettes_qr_filtre_public.py`)
- [x] Créer `outils_docs/scripts_python/outils_pc/build_reparations.py` : `Regle` (dataclass : id, titre, motif, etapes, actions, — preuve : build_reparations.py (115 lignes), signatures du plan, commits 48b887f18 et 2bf943390
  origine, ajoutee_le), `charge_catalogue(chemin_base: Path, chemin_local: Path) -> list[Regle]`,
  `cherche(regles: list[Regle], journal: str, etape: str, env: str) -> Regle | None`, `filtre_secrets(texte: str) -> str`
- [x] Créer `outils_docs/schemas/reparations_build.json` avec la règle de base `verrou_fichier` : motif sur — preuve : outils_docs/schemas/reparations_build.json, regle verrou_fichier (chemin du depot, pas COM)
  `PermissionError: \[Errno 13\] Permission denied: '[A-Za-z]:\\\\Users\\\\...\\\\Tasmota\\\\` (chemin du dépôt, pas `COM\d+`),
  actions `libere_verrou`, `attendre 5`
- [x] Banc vert, avec mutants (action hors liste acceptée, motif non borné à la fin du journal, secrets non filtrés) — preuve : banc vert, 3 mutants tues ; correctifs de relecture 2bf943390 (regle locale fautive ignoree, filtre par cle) ; sortie « tout est vert »

## A2 — Verrou de fichier (`build_reparations_verrou.py`)
- [x] Écrire d'abord `test_build_reparations_verrou.py` (rouge) : un processus Python de test ouvre un fichier temporaire en — preuve : test_build_reparations_verrou.py rouge (module absent) puis vert, commit 883d86260
  partage exclusif ; `processus_du_fichier(chemin)` le retrouve par son pid ; `classe(proc, pid_serie, liste_blanche)` rend
  `"ferme"` (nom en liste blanche), `"attend"` (`pio`/`scons`/`python` d'une autre origine), `"demande"` (autre), `"jamais"`
  (pid de la page ou de la série, `claude`) ; `libere(chemin, liste_blanche, pid_serie, demande)` ferme le processus de la
  liste blanche (liste de test = le processus de test) et rend `{"libre": True, "ferme": [...], "attend": [], "demande": []}` ;
  processus mort entre le repérage et la fermeture : pas d'exception
- [x] Créer `outils_docs/scripts_python/outils_pc/build_reparations_verrou.py` : `processus_du_fichier(chemin: str) -> list[dict]` — preuve : build_reparations_verrou.py, signatures du plan + cles refuse/erreur, commits 883d86260 et 0335ce9cc (Restart Manager par ctypes, noms par Toolhelp32 : Get-CimInstance trop lent, 15-25 s)
  (clés `pid`, `nom`, `ligne`, par le Restart Manager `RmStartSession`/`RmRegisterResources`/`RmGetList` en `ctypes`, nom et
  ligne de commande par `Win32_Process`), `classe(...)`, `libere(...)` comme ci-dessus ; attente jusqu'à 5 s que `open` exclusif
  réussisse
- [x] Banc vert, mutant : retirer la liste blanche ou le garde du pid de la série doit rendre le banc rouge — preuve : banc vert (12 s), 4 mutants rouges (liste blanche, garde pid serie, heure de debut, fermeture ratee) ; corrections de relecture 0335ce9cc ; controleur : banc relance, tout vert

## A3 — Moteur et branchement dans la série
- [x] Écrire d'abord les tests dans `test_build_serie.py` (nouveau groupe, faux `pio` qui échoue avec un journal de verrou puis — preuve : tests de la serie (groupe test_reparations) rouges puis verts, commit e796b82eb ; test_build_serie 205 OK, 0 KO
  réussit) : la série relance la même étape, l'env réussit, l'événement `reparation` (états `en_cours` puis `reussie`) est émis
  et une ligne `[réparation] …` entre dans le journal de l'env ; deuxième échec identique : pas de boucle (2 relances au plus) ;
  règle absente : comportement actuel (`echec`, env suivant) ; étape `upload` COM : jamais relancée ; arrêt demandé pendant la
  réparation : env `arrete` ; `choix_reparation` émis pour un processus « demande », `repond_choix(env, choix)` le résout, 409 si
  déjà résolu ou expiré, expiration à 10 min (horloge injectée) = env en échec et série qui continue
- [x] Étendre `build_reparations.py` : `Reparateur(serie, regles, horloge=time.monotonic)` avec — preuve : Reparateur dans build_reparations.py (traite, repond_choix, ajoute_regle_locale), commits e796b82eb et 710dfae4e
  `traite(ligne, action, cible, etape, journal, extrait) -> bool` (vrai = relancer l'étape) et `repond_choix(env, choix) -> None`
  (`ValueError` choix inconnu, `RuntimeError` aucune demande ouverte) ; exécute les actions de la règle (`attendre` en boucle courte
  sensible à l'arrêt, `libere_verrou` via A2 sur le chemin extrait du motif, `vide_build` = `.pio/build/<env>` de l'env raté seulement)
- [x] Brancher dans `build_serie.py::Serie._execute_env` (quelques lignes) : boucle de relance autour de `_lance_pio` — preuve : build_serie.py +19 lignes (_execute_env, repond_reparation, reparations()), evenements dans la docstring
  pour les genres `pio`, avant l'événement `echec` ; ajouter les événements `reparation` (env, action, regle, etat, message) et
  `choix_reparation` (env, regle, texte, boutons) à la docstring du module ; `Serie.repond_reparation(env, choix)`
- [x] Bancs `test_build_serie.py` et `test_build_reparations.py` verts, mutants (limite de relances retirée, boucle sans signature, — preuve : mutants (limite de relances, signature, relance d'un envoi) rouges dans les deux bancs ; relecture A3 sans Critical ni Important ; 4 mineurs corriges en 710dfae4e ; controleur : bancs relances verts
  relance d'un upload) rouges

## A4 — Routes de la page (`build_web.py`)
- [ ] Écrire d'abord les tests dans `test_build_web.py` : `GET /reparations` rend règles (base + locales) et historique de la
  série ; `POST /reparation {env, choix}` (réponse au choix) ; `POST /reparations/supprime {id}` (règles locales seulement,
  jamais une règle de base) ; les trois écrivains (`/reparation`, `/reparations/supprime`, et plus tard A6) refusés (403) pour un
  client distant, lecture permise ; mêmes protections que `/continuer` (en-tête `X-Build`, origine)
- [ ] Ajouter les routes dans `build_web.py` (quelques lignes, logique dans `build_reparations.py`) — preuve : banc vert

## A5 — Page : bandeau, choix, panneau « Réparations »
- [ ] Écrire d'abord la sonde `test_build_page_reparations_chrome.py` (rouge ; pas de pause fixe, attendre des conditions) :
  bandeau « Réparation en cours : <titre> » sur l'env, boutons Fermer / Attendre / Annuler d'un `choix_reparation` qui
  envoient `POST /reparation`, état reconstruit au rechargement par les événements rejoués, panneau « Réparations » avec la
  liste des règles, bouton Supprimer sur une règle locale seulement
- [ ] Créer `build_page_reparations.py` (CSS, HTML, JS du bandeau, des boutons et du panneau, inséré dans `build_page.PAGE` par
  quelques lignes) ; brancher les événements `reparation` et `choix_reparation` dans le gestionnaire d'événements de `build_page.py`
- [ ] Sonde verte ; Chrome `sonde_*` orphelins arrêtés après coup (compter les `HasExited` faux 15 s après) — preuve : …

## A6 — Diagnostic par l'IA et catalogue qui s'enrichit (`build_reparations_ia.py`)
- [ ] Écrire d'abord `test_build_reparations_ia.py` (rouge, `claude` remplacé par un faux programme injecté, comme le test de
  `atelier_ecrans_remarques.py`) : la consigne contient la fin du journal filtrée des secrets et l'étape ; sortie qui n'est pas du
  JSON -> aucune proposition ; `regle` dont le motif ne correspond pas au journal fourni -> refusée, texte manuel seulement ; `regle`
  avec une action hors liste -> refusée ; `regle` valide -> proposition `{cause, explication, regle}` ; appliquer = actions puis
  relance puis, si la relance réussit, règle ajoutée dans le fichier local avec `origine: "ia"` ; échec de la relance : rien ajouté
- [ ] Créer `build_reparations_ia.py` : `diagnostique(racine, env, etape, journal, programme=None) -> dict` (`claude -p` en lecture
  seule, mêmes options et mêmes gardes que l'atelier des écrans, ce PC seulement), `valide_proposition(proposition, journal) -> dict`
- [ ] Routes `POST /reparations/diagnostic {env}` et `POST /reparations/appliquer {env, regle}` (ce PC seulement) ; « Appliquer et
  relancer » lance une série d'un seul env avec les actions non réussies, ou attend la fin de la série en cours ; bouton « Faire
  diagnostiquer par l'IA » sur un env en échec sans règle (résumé de la série), dans `build_page_reparations.py`
- [ ] Bancs verts, un essai réel de diagnostic sur un journal d'échec archivé (lecture seule, rien appliqué) — preuve : …

## A7 — Documentation, essai et commit
- [ ] `outils_docs/README.md` (§ « Build et téléversement (page web) » : réparations, catalogue, liste blanche, panneau), `CLAUDE.md`
  (carte des documents : les modules neufs), `tasks/README.md` régénéré ; `verifie_references_docs.py` sans renvoi faux
- [ ] Relecteurs `relecteur-pages-web` (page et routes, sécurité : fermeture de processus, clients distants, XSS du journal) puis
  correction des défauts ; mutants des bancs relus
- [ ] Essai réel hors série de production : un fichier du dépôt tenu ouvert par un script de test pendant un faux build (pas de vrai
  `pio`) ; la page annonce, libère, relance
- [ ] Commit par chemins explicites (module neufs, bancs, plan, spec, README) — preuve : `git show --stat HEAD`

## A8 — Retour au plan en cours avant ce chantier
- [ ] Reprendre le plan `facade-garage-capteurs` : A3 (envoi des firmwares compilés le 2026-11-14 et essais sur les cartes : rideau fermé = pastille du bas verte, camera, fins de course) : `/suivi suivre facade-garage-capteurs`
- [ ] Puis, à l'issue de ce plan, le plan `ecran-cave-vues-commandes` (A9, essai sur carte de l'écran de la cave), comme le prévoit l'action A4 de `facade-garage-capteurs`

## Améliorations restantes
- [ ] [projet] Étendre les réparations aux échecs d'envoi OTA (HTTP, MQTT) et série (port COM tenu)
- [ ] [projet] Promouvoir une règle IA éprouvée dans `reparations_build.json` (commit de l'utilisateur)

## Vérification
Bancs `test_build_reparations*.py`, `test_build_serie.py`, `test_build_web.py`, sonde `test_build_page_reparations_chrome.py` ;
`verifie_references_docs.py` ; `node .claude/hooks/index_plans.mjs --verifier`.
