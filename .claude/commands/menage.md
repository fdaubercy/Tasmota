---
description: Audit de ménage du dépôt Tasmota (orphelins, restes, doublons, reclassements), en proposition seulement
argument-hint: "[zone ou dossier à examiner]"
---

Lance l'agent `auditeur-menage` sur ce dépôt. Zone demandée : `$ARGUMENTS` (vide = tout le périmètre du fork).

1. Vérifie qu'aucun `pio`/`scons` ne tourne (lecture seule, mais les listes de fichiers bougent pendant un build).
2. Lance `auditeur-menage` avec cette zone, `anciennete_jours` = 3 et la liste `gardes` (lue dans sa mémoire), et rends son rapport tel quel,
   sans rien déplacer ni supprimer. Le travail en cours (modifié, non suivi, moins de 3 jours) et les plans actifs ne sont jamais proposés.
   Lancé par la page « Ménage du dépôt » (plan `tasks/plans/menage-page.md`), la consigne demande en plus le JSON de
   `outils_docs/schemas/menage_rapport.schema.json`, validé par `outils_pc/menage_rapport.py::valide`.
3. Demande à l'utilisateur quelles propositions appliquer. Pour celles qu'il garde, dis-lui que l'agent les
   mémorise (« à garder ») pour ne plus les reproposer.
4. Si l'utilisateur valide un lot : l'appliquer par `git mv` ou `git rm`, puis lancer
   `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` et le banc concerné (skill `bancs`).
   Ne commiter qu'à sa demande, selon `/commite`.
