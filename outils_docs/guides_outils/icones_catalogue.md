# Catalogue d'icônes

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

### Catalogue d'icônes (page web)

Page de consultation, **lecture seule** (aucune route POST, rien n'est écrit), http://127.0.0.1:7930 : tuile « Catalogue d'icônes »
de l'annuaire (groupe Dépôt et références), tâche VS Code « Outil : catalogue d'icones (http://127.0.0.1:7930) », cible Custom détachée
« Catalogue d'icones (page web) » (`build/cible_icones_catalogue.py`, `pio run` : jamais pendant un build) ou
`python outils_docs/scripts_python/outils_pc/icones_catalogue_web.py [--http 7930] [--local] [--sans-navigateur]`.
Plan `tasks/plans/atelier-ecrans.md` A18. Le catalogue est recalculé à chaque ouverture par `outils_pc/icones_catalogue.py::construit` :
les 120 glyphes de `outils_docs/schemas/icones_firmware.json` (dessinés par la police MDI locale, aucun CDN, aucune requête externe), les
PNG de `data/` et de `outils_docs/atelier_ecrans/images/` (taille lue dans l'en-tête, poids) et les sites de l'annuaire
`ICONES_IMAGES_SOURCES.md` (sections 1 à 3, avec licence). Recherche par nom, filtre par source (Firmware, PNG, Sites). Un clic sur un glyphe
ouvre sa fiche : code à copier pour l'attribut `text` (`\uE335`) avec le bouton Copier, nom et code MDI, lien pictogrammers.com, polices
(`montserrat-28` recommandé), et ses usages (fichiers de `ecran.json`, `pages.jsonl` et des `.be` de `data/` qui portent son code, 20 au plus).
« Absentes du firmware » : codes `U+E000` à `U+F8FF` utilisés dans ces fichiers mais absents du catalogue (carré vide à l'écran).
Pas de fontTools ici : la génération du catalogue reste `genere_icones_firmware.py`. Bancs `outils_pc/test_icones_catalogue.py` (mini-dépôt, mutants),
`test_icones_catalogue_web.py`, sonde Chrome `test_icones_catalogue_page_chrome.py` (témoins), `build/test_cible_icones_catalogue.py`.
