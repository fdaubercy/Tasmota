# Atelier des graphiques — maquettes (2026-11-03)

Outil PC (tuile de l'annuaire, page 7950, mode d'emploi : `outils_docs/README.md` § « Atelier des graphiques ») : préparer un graphique pour une carte, voir l'aperçu avec ses vraies
valeurs, puis écrire dans le dépôt le Berry, les gabarits et le cenv qui le font apparaître sur la carte.
**Modèle B retenu (avec la grille du modèle C), réalisé (palier 1).**

- Images : `modele-A.png` (assistant pas à pas), `modele-B.png` (atelier trois colonnes),
  `modele-C.png` (constructeur de page, aperçu dans le thème de Tasmota).
- Code : `maquettes_atelier.html?m=A|B|C` ; ECharts lu dans `echarts.min.js` à côté du fichier
  (`gzip -dc data/sd/js/echarts.min.js.gz`), sinon jsDelivr. Valeurs et tailles des maquettes fictives.

## Réponses de l'utilisateur (2026-11-03)

1. Destinations : page dédiée, page `/graphiques` existante, encadré de l'accueil, ESP32 classiques (SVG pur).
2. Données : séries de l'historique, toute valeur du JSON SENSOR, valeurs calculées, données en flash d'un module.
3. Séries et aperçu : carte en ligne (IP du cenv ou par le maître), sinon persist du dépôt et valeurs simulées, signalé.
4. Conseil : intention de l'utilisateur croisée avec la nature des séries, 3 à 5 styles classés avec leur raison.
5. Écriture : diff puis écriture atomique du dépôt (refus pendant un build), envoi par la page Build (onglet Fichiers).
6. Module de page : sur le FS par défaut, case « Solidifier » (code toujours conforme aux pièges de solidification).
7. Modification : pages et encadrés créés par l'outil (décrits dans un JSON par carte) et la composition de
   `/graphiques` ; jamais les pages écrites à la main (`/cuve`, `/energie`).
8. Pages dédiées : plusieurs par carte, accès choisi par page (bouton d'accueil ou lien icône d'un encadré).
9. `/graphiques` : à étendre au-delà de courbe, barres, escalier, aire (`graphiques_trace.js`, `valideComposition`).
10. Réglages : titre, libellés, unités, couleurs ; seuils et zones ; période et cadence ; taille et disposition ;
    l'aperçu montre l'effet de chaque réglage.
