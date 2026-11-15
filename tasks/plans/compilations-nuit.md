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
- [ ] Diagnostiquer l'absence de lancements (`gh api repos/fdaubercy/Tasmota/actions/workflows`, état « disabled_inactivity » ?) et réactiver
- [ ] `build_custom.yml` : matrice des 25 envs (liste lue de `platformio_tasmota_cenv.ini`), ajouter un contrôle qui échoue si un env manque
- [ ] Vérifier que le build GitHub reflète la config réelle (`platformio_override.ini` de l'échantillon vs dépôt) et noter l'écart
- [ ] Un lancement `workflow_dispatch` complet, lu jusqu'au bout (SUCCESS/FAILED par env)

## A2 — Voie PC (tâche Windows qui pilote la page Build)
- [ ] Script `maintenance/compilation_nuit.py` : refuse si un build tourne (garde existante), démarre la page Build si absente, `POST /lancer` (compiler seulement, sans port), attend la fin, écrit un résumé JSON par env
- [ ] Journal et résultat dans `%LOCALAPPDATA%\outils_tasmota\compilations_nuit\` (30 jours)
- [ ] Enregistrement de la tâche planifiée Windows (`schtasks`, réveil du PC optionnel), sans droits administrateur
- [ ] Banc `test_compilation_nuit.py` (faux serveur de build : refus pendant un build, échec d'un env, reprise)

## A3 — Tuile « Tâches planifiées » (page 7920, v1 lecture)
- [ ] `taches_planifiees_web.py` + `_page.py` + cible Custom détachée + tuile de l'annuaire (groupe Déploiement) + tâche VS Code
- [ ] Liste des deux voies : activée ou non, prochaine exécution, dernier résultat, durée, envs en échec avec lien vers le journal
- [ ] Lecture GitHub par `gh` (derniers runs), lecture PC par le dossier de résultats ; sondes hors ligne tolérées
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
