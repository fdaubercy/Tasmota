---
description: Audit de ménage du dépôt Tasmota (orphelins, restes, doublons, reclassements), en proposition seulement
argument-hint: "[zone ou dossier à examiner]"
---

Lance l'agent `auditeur-menage` sur ce dépôt. Zone demandée : `$ARGUMENTS` (vide = tout le périmètre du fork).

1. Vérifie qu'aucun `pio`/`scons` ne tourne (lecture seule, mais les listes de fichiers bougent pendant un build).
2. Lance `auditeur-menage` avec cette zone et rends son rapport tel quel, sans rien déplacer ni supprimer.
3. Demande à l'utilisateur quelles propositions appliquer. Pour celles qu'il garde, dis-lui que l'agent les
   mémorise (« à garder ») pour ne plus les reproposer.
4. Si l'utilisateur valide un lot : l'appliquer par `git mv` ou `git rm`, puis lancer
   `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` et le banc concerné (skill `bancs`).
   Ne commiter qu'à sa demande, selon `/commite`.
