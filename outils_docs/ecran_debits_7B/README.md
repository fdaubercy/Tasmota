# Écran des débits sur le Waveshare 7B : maquettes

Maquettes du 2026-11-11 pour la page principale de la carte d'affichage `tasmota32s3-bureau-ecran-debits-pac` (Waveshare
ESP32-S3-Touch-LCD-7B, 1024 × 600, tactile). Plan `tasks/plans/debits-deux-cartes.md`, action A8 ; fiche du module :
`outils_docs/Schémas de branchement - Attribution des PINS des modules/bureau/tasmota32s3-bureau-ecran-debits-pac/WAVESHARE_ESP32-S3-Touch-LCD-7B.md`.

- Images : `modele-A.png` à `modele-D.png` (taille réelle de l'écran).
- Code : `maquettes_ecran_7B.html`, à ouvrir dans un navigateur (`?m=A` pour une seule maquette). Rendu des images :
  Chrome sans tête, `--window-size=1024,600 --screenshot`.
- Palette de l'écran actuel (`pages.jsonl` : fond `#10161E`, bleu `#3FA7FF`) ; états montrés partout : normal, imprécis
  (< 1 L/min, orange), muet (rouge), inconnu (gris, pas de relevé depuis 2 fenêtres). En-tête : total et âge du relevé ModBus.

| | Disposition | HASPmota | LVGL pur en Berry |
|---|---|---|---|
| A | Six lignes : nom, barre, débit, part du total | `label` + `bar` (l'écran actuel, agrandi) | `lv.label` + `lv.bar` |
| B | Six tuiles 3 × 2, gros chiffres, cadre coloré selon l'état | `obj` (cadre) + `label` + `bar` | `lv.obj` + `lv.label` + `lv.bar` |
| C | Six arcs 270° (0 à 10 L/min) | `arc` | `lv.arc` |
| D | Valeurs à gauche, courbe des 30 dernières minutes à droite | `chart` : 2 séries natives ; les 6 demandent l'objet LVGL dessous (`_lv_obj.add_series`) | `lv.chart`, 6 séries |

Toutes gardent un pied de page tactile : « Débits », « Courbes » (A, C), « Réglages » (fenêtre, veille, luminosité). B ouvre
la courbe d'une voie par appui long sur sa tuile. Choix en attente.
