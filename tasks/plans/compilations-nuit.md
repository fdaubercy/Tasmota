---
chantier: compilations-nuit
titre: Compilations de nuit (GitHub et PC) et tuile « Tâches planifiées » de l'annuaire
objectif: Vérifier chaque nuit que tous les envs du fork compilent, sur GitHub et/ou sur ce PC, et piloter (activer, désactiver, paramétrer, lancer) ces tâches depuis une page de l'annuaire
statut: clos
cree: 2026-11-15
maj: 2026-11-15
famille: build
liens: build-reparations, build-fin-partitions, menage-page
---
# Compilations de nuit et tuile « Tâches planifiées »

> Plan de conception, rien n'est encore fait. Aucun `pio run` lancé pendant l'écriture.

## Contexte

Demande du 2026-11-15. Constats : `.github/workflows/build_custom.yml` existe (cron 2 h UTC) mais compile 12 envs perso sur 25,
avec `platformio_override_sample.ini` (pas la config locale), et ses lancements planifiés sont irréguliers (échecs 10 au
15 septembre, rien du 15 septembre au 3 novembre, rien depuis le 4 novembre : GitHub suspend les crons d'un fork inactif).
Décisions de l'utilisateur : les DEUX voies (GitHub + tâche Windows pilotant la page Build :7700), alerte par mail GitHub et
par la tuile, tuile pour VOIR et PARAMÉTRER, avec activation et désactivation des compilations programmées sur PC et/ou GitHub.
Port retenu : 7920 (libre dans `annuaire_registre.py`).

## A1 — Voie GitHub fiable
- [x] Diagnostiquer l'absence de lancements et réactiver — preuve : Actions désactivées sur le fork par GitHub (bandeau « Workflows on this fork have been disabled »), bouton cliqué le 2026-11-15, `gh workflow run` accepté ensuite
- [x] `build_custom.yml` : matrice des 25 envs — preuve : commit 9d4637049 (13 envs ajoutés), run 43695356628 = 25 envs verts
- [x] `build_custom.yml` : contrôle qui échoue si un env du cenv manque dans la matrice — preuve : job `verifie-matrice`, 25/25 en local ; témoin négatif : retirer tasmota-rdc-tv-salon le fait nommer et sortir en code 1 (le 1er jet lisait 0 env : il se coupait sur sa propre chaîne, corrigé par une ancre de début de ligne)
- [x] Vérifier que le build GitHub reflète la config réelle — preuve : journal du run 43695356628 (rideau-garage) : « Will solidify … », donc le pré-script tourne sur GitHub ; écarts connus de l'échantillon, sans effet sur les envs du cenv : `default_envs` et `data_dir` (inutiles pour `-e`), `extra_scripts` de `tasmota32_idf55_base` seulement. Le CFG_HOLDER, le cache objet et `data_dir` du FS ne sont pas ceux du PC : GitHub prouve que le code COMPILE, pas que le FS est identique
- [x] Débloquer `workflow_dispatch` (422 « Actions has been disabled ») — preuve : cause = désactivation automatique des workflows d'un fork, réactivée par l'utilisateur ; `permissions` renvoyait `enabled: true` à tort, d'où le contrôle de santé de A3
- [x] Un lancement `workflow_dispatch` complet, lu jusqu'au bout — preuve : run 43695356628, 29 jobs success (1er run 43692897852 : rdc-vr-porte en échec, dossier vide non suivi par git, corrigé par 775f8b227 ; safeboot retirés)

## A2 — Voie PC (tâche Windows qui pilote la page Build)
- [x] Script `maintenance/compilation_nuit.py` : refuse si un build tourne (garde existante), démarre la page Build si absente, `POST /lancer` (compiler seulement, sans port), attend la fin, écrit un résumé JSON par env — preuve : banc 15/15, 2 mutants rouges, `--dry-run` réel sur :7700 = 25 envs écrivables ; démarrage détaché de la page NON essayé (page déjà lancée)
- [x] Journal et résultat dans `%LOCALAPPDATA%\outils_tasmota\compilations_nuit\` (30 jours) — preuve : `resultat-*.json` + `dernier.json` atomiques, purge à 30 jours (compilation_nuit.py::execute, banc « dernier.json écrit »)
- [x] Enregistrement de la tâche planifiée Windows (`schtasks`, sans droits administrateur) — preuve : `compilation_nuit_tache.py` (créer, état, activer, désactiver, supprimer), banc 14 vérifications + mutant ; tâche réelle `Tasmota-CompilationNuit` créée DÉSACTIVÉE à 02:00, état relu (existe, inactif, prochaine N/A) ; réveil du PC et rattrapage non réglés (valeurs par défaut de schtasks)
- [x] Banc `test_compilation_nuit.py` (faux serveur de build : refus pendant un build, échec d'un env, reprise) — preuve : exit 0, 15 vérifications (nominal, échec, exclusion, refus 409, désactivé, dry-run, Ctrl+C, config)

## A3 — Tuile « Tâches planifiées » (page 7920, v1 lecture)
- [x] `taches_planifiees_web.py` + `_page.py` + cible Custom détachée + tuile de l'annuaire (groupe Déploiement) + tâche VS Code — preuve : `outils_pc/taches_planifiees_{web,page,github,pc,sante}.py`, `build/cible_taches_planifiees.py` (enregistrée dans `pre_utilitaires_platformio.py` et `.claude/hooks/garde_build.py::CIBLES_OUTILS`), entrée `taches_planifiees` du registre (groupe Déploiement, port 7920), tâche `.vscode/tasks.json` ; `test_cible_taches_planifiees.py` VERT, `test_garde_build.py` VERT (liste alignée), `test_annuaire.py` VERT (20 outils)
- [x] Liste des deux voies : activée ou non, prochaine exécution, dernier résultat, durée, envs en échec avec lien vers le journal — preuve : `test_taches_planifiees_web.py::cas_pc` (tâche désactivée lue, durée 95 s, une entrée par env en échec avec le chemin du journal local de `build/journaux`), lien vers le job GitHub en échec (`jobs_en_echec`), rendu vérifié par la sonde Chrome
- [x] Lecture GitHub par `gh` (derniers runs), lecture PC par le dossier de résultats ; sondes hors ligne tolérées — preuve : banc avec faux `gh` et `schtasks` (gh absent, hors ligne, non connecté, JSON corrompu, dossier vide) ; essai réel du 2026-11-15 avec GitHub injoignable (TLS timeout) : bandeau orange « GitHub non vérifié », aucune exception
- [x] Contrôle de santé GitHub à CHAQUE ouverture de la page : `gh api repos/fdaubercy/Tasmota/actions/permissions`, `gh workflow list --all` (repérer `disabled_inactivity`) et ancienneté du dernier run planifié (alerte rouge au-delà de 36 h). Constat du 2026-11-15 : les permissions disent `enabled: true` alors que `gh workflow run` répond 422 « Actions has been disabled », donc le premier contrôle seul ne suffit pas — preuve : `taches_planifiees_github.py::sante` (trois appels en parallèle, délai 12 s, cache 45 s, `?frais=1` pour forcer) ; banc : workflow `disabled_inactivity` avec permissions `enabled: true` = rouge, run planifié de 40 h = rouge, aucun run planifié = rouge ; 7 témoins négatifs (un contrôle retiré rend le banc rouge) détectés ; lecture réelle `gh workflow list --all` : Build_custom `active`, stale `disabled_inactivity`
- [x] Bancs et sonde Chrome — preuve : `test_taches_planifiees_web.py` exit 0 (29 vérifications + 7 témoins), `test_taches_planifiees_page_chrome.py` exit 0 (40 vérifications, 2 témoins détectés : innerHTML, lien javascript:), Chrome `sonde_*` arrêtés (0 restant)

## A4 — Tuile : activer, désactiver, paramétrer
- [x] Bouton activer / désactiver pour GitHub (`gh workflow enable|disable`) et pour le PC (`schtasks /change /enable|/disable`), état relu après chaque geste — preuve : `taches_planifiees_gestes.py::github_active`, `pc_active`, route `POST /geste`, `test_taches_planifiees_gestes.py` (28 vérifications, 4 mutants) et `test_taches_planifiees_post.py` (34) ; faux `gh` et faux `schtasks` seulement, essai réel en A5
- [x] Paramètres : heure (PC, `schtasks /change /st`, état conservé) et envs cochés par voie, avec aperçu avant écriture pour GitHub — preuve : `pc_heure`, `ecrit_exclus_pc`, `apercu_exclus_github` / `ecrit_exclus_github`, bancs ci-dessus ; la liste GitHub est un fichier du depot (`outils_docs/compilations_nuit/envs_github.json`) lu par un job `choix` du workflow, qui REMPLACE la matrice écrite à la main (`maintenance/matrice_github.py`, banc 9 vérifications + mutant)
- [x] Valider le job `choix` du workflow sur GitHub, matrice complète — preuve : push 49e72d52a puis `workflow_dispatch`, run 43708168486 : `choix` success, 25 jobs `custom-images` + 4 `base-images`, 30 jobs sur 30 success
- [x] Valider sur GitHub qu'un env EXCLU (`envs_github.json` poussé avec un seul nom) disparaît de la matrice, puis remettre la liste vide — preuve : run 43711767872 (2026-11-15), job `choix` vert, 24 jobs `custom-images` sans `tasmota32-rdc-vr-porte` ; liste remise à vide au commit 5f03db194, poussé
- [x] Bouton « Lancer maintenant » (GitHub : `workflow_dispatch`, PC : refus si un build tourne) — preuve : `pc_lancer` (409 si la page Build a une série en cours, aucun processus démarré), `github_lancer`, confirmation en DEUX TEMPS dans la page ; sonde Chrome : 1er clic n'arme que le bouton, 2e lance une seule fois (fausse commande)
- [x] Écritures atomiques, accès comme les autres outils (`acces_web.py`) — preuve : `ecrit_atomique` (.tmp puis os.replace), POST refusé sans `X-Taches: 1`, hors origine, hors Host, et pour un client distant même muni d'un jeton (3 mutants sur 3 détectés) ; diff préalable pour GitHub seulement (le PC écrit hors dépôt) ; « refus pendant un build » : seulement pour lancer, la config PC est relue au prochain lancement
- [x] Bancs des gestes (faux `gh` et faux `schtasks`) et sonde Chrome — preuve : `test_taches_planifiees_gestes.py` 0, `test_taches_planifiees_post.py` 0 (dépôt et fausse page Build temporaires, vrai fichier d'exclusions vérifié intact), `test_taches_planifiees_page_chrome.py` 0 (24 vérifications au passage normal, 3 témoins détectés, aucun Chrome `sonde_*` restant)

## A4b — Choix des envs, arrêt en cours, synchro nocturne du fork
- [x] Case par env et par voie (GitHub / PC) dans la tuile : un env décoché n'est plus compilé la nuit — preuve : cases de `taches_planifiees_page_gestes.py`, PC = `envs_exclus` de `config.json` lu par `compilation_nuit.py`, GitHub = `envs_github.json` ; sonde Chrome (une case par env, nom hostile en texte). Effet sur GitHub à valider avec l'étape du job `choix` (A4)
- [x] Bouton « Arrêter la compilation en cours » (PC : `POST /arreter {immediat}` de la page Build ; GitHub : `gh run cancel` des runs en cours ET en file) — preuve : `pc_arreter`, `github_arreter`, mutants « sans vérifier la série » et « runs en file oubliés » détectés ; il arrête aussi une série lancée à la main, dit dans le bouton
Écarté le 2026-11-15 par l'utilisateur : pas de synchro nocturne du fork, même en diagnostic seul (la synchro reste manuelle, hook de détection au démarrage).

## A5 — Documentation et mémoire
- [x] Carte des documents de `CLAUDE.md`, mode d'emploi dans `outils_docs/README.md`, vérification `verifie_references_docs.py` — preuve : commit des docs, `verifie_references_docs.py` = 30 documents, 0 défaut ; aucun caractère de contrôle dans les 3 fichiers
- [x] Essai réel d'une nuit complète sur chaque voie, résultat relu le matin — preuve : PARTIELLE, cochée à la demande de l'utilisateur le 2026-11-15 ; run manuel 43711767872 (matrice calculée par `choix`, 24 envs avec une exclusion), run 43708168486 (30/30 success) ; bouton « Écrire, commiter et pousser » essayé sur le vrai dépôt (commits 01dab2668, 018e950c2). RESTE À RELIRE : la première nuit planifiée sur GitHub (02:00 UTC) et le premier passage de la tâche PC (désactivée, à activer et lancer par l'utilisateur) ; aucun run `schedule` depuis le 2026-11-04

## Améliorations restantes
- [ ] [projet] Alerte Telegram si le plugin se connecte
- [ ] [projet] Comparer la taille Flash/RAM d'une nuit à l'autre

## Vérification
Une nuit réelle sur GitHub et sur le PC, puis lecture de la tuile le matin.
