# Envs par défaut : maquettes de l'onglet

Étude du 2026-11-01 pour un onglet de la page « Build et téléversement », qui modifie le bloc `default_envs` de
`platformio_override.ini`. Plan : `tasks/plans/default-envs-page.md`.

**Choix retenu : modèle B**, avec dessous « Modifications en attente », le futur fichier entier (réalisé :
`outils_pc/build_page_defaut.py`).

- `maquettes_default_envs.html` : les 4 modèles (`?m=A` à `?m=D`), avec les vrais envs. Rien n'est écrit.
- `modele-A.png` à `modele-D.png` : une image par modèle.

| Modèle | Principe |
|---|---|
| A | Cases par groupe de puce, résumé et actions à droite (mise en page de l'onglet Build) |
| B | Une colonne par puce, tout visible sans défiler |
| C | Deux listes « Non compilés » et « Compilés », boutons Ajouter et Retirer |
| D | Les lignes du bloc telles que dans le fichier, diff en direct à droite |
