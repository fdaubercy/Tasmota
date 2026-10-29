# Format des plans suivis (`tasks/plans/<chantier>.md`)

Référence lue par Claude, par le mod `suivi-plan` (`.claude/mods/suivi-plan/`) et par l'extension
VS Code `fdaubercy.suivi-plan` (`outils_docs/vscode/suivi-plan/`). Les fichiers dont le nom commence
par `_` (comme celui-ci) ne sont pas des plans.

## Squelette

```markdown
---
chantier: voie-modbus          # nom court, = nom du fichier sans .md
titre: Fin des correctifs « voie ModBus »
objectif: Une phrase : le but principal du plan   # repris dans tasks/README.md (pas de « # » dans le texte)
statut: actif                  # actif | en-pause | clos
cree: 2026-10-18
maj: 2026-10-18
source: reprendre-serialized-firefly.md   # plan d'origine dans ~/.claude/plans (facultatif)
reprise: tasks/reprise-chantier-modbus-grenier.md                 # (facultatif)
---
# Fin des correctifs « voie ModBus »

## Contexte
Texte libre : pourquoi ce plan, décisions prises. Non compté.

## A1 — Titre de l'action correctrice
- [x] Sous-étape faite — preuve : banc_test_modbus.py 309/309
- [ ] Sous-étape à faire
  - [ ] Sous-étape imbriquée (compte comme une étape)

## A2 — Autre action
- [ ] …

## Améliorations restantes
- [ ] [conversation] À faire dans cette conversation
- [ ] [projet] À faire plus tard dans le projet (sans étiquette = projet)

## Vérification
Texte libre. Non compté.
```

## Règles de calcul

- Une **action** est un titre `## A<n> — titre` (séparateurs acceptés : `—`, `–`, `-`, `.`, `:`).
- Une **étape** est une case `- [ ]` ou `- [x]` placée sous une action, imbrication comprise.
- **% d'une action** = étapes cochées / étapes. Une action sans étape vaut 0 % et lève une alerte.
- **% global** = moyenne des % des actions (chaque action pèse autant).
- Les cases des autres sections (Contexte, Améliorations restantes, Vérification) ne comptent pas.
- Tout ce qui est dans un bloc de code est ignoré.

## Règles d'usage

- **Cocher une étape seulement après l'avoir vérifiée**, avec sa preuve après ` — preuve : `
  (commit, `fichier:ligne`, sortie d'un banc). Pas de coche sans preuve (même règle que `/fin-de-session`).
- Mettre à jour `maj:` à chaque modification.
- **Index des plans** : `tasks/README.md` liste chaque plan (objectif, statut, %). Son tableau est
  régénéré par `node .claude/hooks/index_plans.mjs` — automatiquement quand Claude édite un plan (hook
  `index_plans_edition.sh`), à la main après une édition hors Claude. `--verifier` : code 1 s'il est en retard.
- Ce qui reste hors du plan va dans « Améliorations restantes », avec son étiquette.
- Plan fini (100 %) : `statut: clos`. Plusieurs plans peuvent être `actif` ; la ligne
  d'avancement montre le plus récemment modifié.
- **Plan d'une conversation** : une conversation suit le plan qu'elle a validé (ExitPlanMode), édité
  ou ouvert (`/suivi ouvrir`) ; `/suivi suivre <chantier>` la rattache à la main, `/suivi detacher`
  la libère (le plan reste intact). Quand l'onglet actif est une conversation Claude, la vue de droite
  montre SON plan, ou « aucun plan » ; un onglet de fichier ne change rien ; « Choisir le plan » vaut
  jusqu'au prochain passage sur une conversation. Rattachements : `%USERPROFILE%\.claude\suivi-plan\conversations\<session>.json`.
