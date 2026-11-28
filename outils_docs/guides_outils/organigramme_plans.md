# Organigramme des plans

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Organigramme des plans (page web et PowerPoint)

**Adresse en ligne : <https://fdaubercy.github.io/Tasmota/organigramme.html>** (GitHub Pages, branche `etiquettes`).

Un arbre par famille des plans de `tasks/plans/` : statut, avancement, dates de création et de dernière modification, plans
voisins ; un clic sur un plan affiche son détail avec les liens vers le plan et son spec.

### Les trois versions

| Version | Où | Mise à jour |
|---|---|---|
| Fichiers du dépôt | `outils_docs/organigramme_plans/` : `index.html`, `plans.json`, `organigramme-plans.pptx` | Automatique : le hook `index_plans_edition.sh` relance le générateur à chaque modification d'un plan |
| Annuaire | tuile « Organigramme des plans », page http://127.0.0.1:7990 | Automatique : la page est refaite à chaque ouverture |
| En ligne (GitHub Pages) | l'adresse ci-dessus | **Manuelle** : elle ne change que si on la publie |

### Mettre à jour la version en ligne

- **Depuis l'annuaire** : ouvrir la tuile « Organigramme des plans », cliquer sur « Publier sur GitHub Pages », puis cliquer une seconde fois pour confirmer.
- **En ligne de commande** : `python outils_docs/scripts_python/maintenance/organigramme_plans.py --publier` (affiche « publié » avec l'adresse, ou « déjà à jour »).

La publication pousse sans forcer la branche `etiquettes` et masque les adresses IPv4 ; l'arbre de travail et `development` ne bougent pas. La page
en ligne peut mettre une minute à refléter une publication. Les fiches des étiquettes QR partagent cette branche et gardent `organigramme.html`.

### Changer le contenu

Éditer l'en-tête du plan concerné dans `tasks/plans/<plan>.md` (format : `tasks/plans/_FORMAT.md`) :

- `statut:` : `actif`, `en-pause` ou `clos` ;
- `famille:` : `build`, `methode`, `modbus-reseau`, `cave`, `debits-energie` ou `graphiques-ecrans` ;
- `parent:` : le plan dont celui-ci découle (même famille), sinon rien ;
- `liens:` : les plans voisins, toutes familles ;
- `spec:` : le ou les specs de `docs/superpowers/specs/`.

L'avancement et les dates viennent des cases cochées et de l'historique git, rien à saisir. L'avancement est celui
du parseur des plans, comme dans le panneau VS Code et `tasks/README.md` : seules comptent les cases des sections
d'action (`## A1`, `## A1b`…), et le % est la moyenne des actions. Les « Améliorations restantes » ne comptent pas.
Les totaux de famille et le total général sont des parts d'étapes terminées. Node est nécessaire.

### Commandes

```
python outils_docs/scripts_python/maintenance/organigramme_plans.py             # régénère données, page web et PowerPoint
python outils_docs/scripts_python/maintenance/organigramme_plans.py --verifier  # code 1 si les fichiers sont en retard
python outils_docs/scripts_python/maintenance/organigramme_plans.py --publier   # met la page en ligne
```

Le PowerPoint demande Node et `pptxgenjs` (hors dépôt) : `cd %LOCALAPPDATA%\outils_tasmota\organigramme && npm install pptxgenjs@3.12.0`.
Sans lui, le générateur affiche un avertissement et écrit quand même les données et la page. Son rendu n'a jamais été vérifié visuellement (pas de
LibreOffice sur le poste) : à ouvrir avant de le présenter.

### Bancs

`outils_pc/test_organigramme_plans_web.py` (page de la tuile, routes, publication refusée sans l'en-tête de sécurité ; ne publie jamais pour de vrai).
