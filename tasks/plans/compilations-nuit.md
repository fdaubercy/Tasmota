---
chantier: compilations-nuit
titre: Compilations de nuit (GitHub et PC) et tuile « Tâches planifiées » de l'annuaire
objectif: Vérifier chaque nuit que tous les envs du fork compilent, sur GitHub et/ou sur ce PC, et piloter (activer, désactiver, paramétrer, lancer) ces tâches depuis une page de l'annuaire
statut: actif
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
- [ ] Enregistrement de la tâche planifiée Windows (`schtasks`, réveil du PC optionnel), sans droits administrateur
- [x] Banc `test_compilation_nuit.py` (faux serveur de build : refus pendant un build, échec d'un env, reprise) — preuve : exit 0, 15 vérifications (nominal, échec, exclusion, refus 409, désactivé, dry-run, Ctrl+C, config)

## A3 — Tuile « Tâches planifiées » (page 7920, v1 lecture)
- [ ] `taches_planifiees_web.py` + `_page.py` + cible Custom détachée + tuile de l'annuaire (groupe Déploiement) + tâche VS Code
- [ ] Liste des deux voies : activée ou non, prochaine exécution, dernier résultat, durée, envs en échec avec lien vers le journal
- [ ] Lecture GitHub par `gh` (derniers runs), lecture PC par le dossier de résultats ; sondes hors ligne tolérées
- [ ] Contrôle de santé GitHub à CHAQUE ouverture de la page : `gh api repos/fdaubercy/Tasmota/actions/permissions`, `gh workflow list --all` (repérer `disabled_inactivity`) et ancienneté du dernier run planifié (alerte rouge au-delà de 36 h). Constat du 2026-11-15 : les permissions disent `enabled: true` alors que `gh workflow run` répond 422 « Actions has been disabled », donc le premier contrôle seul ne suffit pas
- [ ] Bancs et sonde Chrome

## A4 — Tuile : activer, désactiver, paramétrer
- [ ] Bouton activer / désactiver pour GitHub (`gh workflow enable|disable`) et pour le PC (`schtasks /change /enable|/disable`), état relu après chaque geste
- [ ] Paramètres : heure, envs cochés (ceux de la page Build), modification écrite dans le workflow (diff puis commit demandé) et dans la tâche Windows
- [ ] Bouton « Lancer maintenant » (GitHub : `workflow_dispatch`, PC : refus si un build tourne)
- [ ] Écritures atomiques avec diff préalable, refus pendant un build, accès comme les autres outils (`acces_web.py`)
- [ ] Bancs des gestes (faux `gh` et faux `schtasks`) et sonde Chrome

## A4b — Choix des envs, arrêt en cours, synchro nocturne du fork
- [ ] Case par env et par voie (GitHub / PC) dans la tuile : un env décoché n'est plus compilé la nuit ; liste mémorisée dans un fichier du dépôt lu par le workflow (GitHub) et dans `%LOCALAPPDATA%` (PC)
- [ ] Bouton « Arrêter la compilation en cours » (PC) : `POST /arreter {immediat}` de la page Build, y compris au milieu d'un env ; GitHub : `gh run cancel`
- [ ] Synchro nocturne du fork avec l'amont : tâche séparée activable, qui ne fait QUE `synchronise_fork_tasmota.py --dry-run` (diagnostic, retard, conflits prévus) et l'affiche dans la tuile ; la synchro réelle reste manuelle (décision du 2026-07-24 : confirmation humaine requise)

## A5 — Documentation et mémoire
- [ ] Carte des documents de `CLAUDE.md`, mode d'emploi dans `outils_docs/README.md`, vérification `verifie_references_docs.py`
- [ ] Essai réel d'une nuit complète sur chaque voie, résultat relu le matin

## Améliorations restantes
- [ ] [projet] Alerte Telegram si le plugin se connecte
- [ ] [projet] Comparer la taille Flash/RAM d'une nuit à l'autre

## Vérification
Une nuit réelle sur GitHub et sur le PC, puis lecture de la tuile le matin.
