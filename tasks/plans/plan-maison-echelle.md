---
chantier: plan-maison-echelle
titre: Plan de la maison à l'échelle, étage par étage, avec éditeur web
statut: actif
cree: 2026-11-18
maj: 2026-11-19
objectif: Remplacer les pièces schématiques du plan de la maison par un vrai plan à l'échelle (en mètres), un étage par onglet, éditable dans une page web, avec les équipements placés dessus
famille: modbus-reseau
parent: plan-maison
liens: plan-maison, cartes-simulees, debits-deux-cartes
---
# Plan de la maison à l'échelle, étage par étage, avec éditeur web

## Contexte
Suite de l'amélioration « Plan à l'échelle des pièces » de `plan-maison` (restée ouverte : elle attendait des dimensions). L'utilisateur fournira des mesures prises au mètre ou au laser et des photos annotées. Choix du 2026-11-18 : éditeur web par étage, niveau de détail maximal (murs, ouvertures, escaliers, cartes, prises, éclairages, câblage ModBus et réseau).

Décisions de conception (mes choix, à corriger) :
- Tout est stocké en **mètres** dans un JSON du dépôt (`outils_docs/plan_maison/echelle.json`) ; les pixels ne sont qu'un affichage. Hors flash, jamais dans `data/`.
- Le plan actuel (`placement.json`, liens dérivés des persist, vues réseau, Wi-Fi, chauffage) **reste la source des cartes et des liens** : le plan à l'échelle ne remplace que la géométrie des pièces. Chaque carte garde sa pièce et reçoit en plus des coordonnées en mètres (facultatives : sans coordonnées, la carte est placée au centre de sa pièce).
- Montée progressive : on commence par les pièces qui portent des cartes (garage, cave, grenier), le reste se complète au fil des mesures. Un étage sans mesure garde l'ancien dessin.
- Écriture de l'éditeur réservée à ce PC (en-tête `X-...` comme les autres ateliers), atomique, avec copie horodatée, refusée pendant un build.
- Photo ou plan importé : fond calé à l'échelle par deux points et une distance connue, pour décalquer ; facultatif.

## A1 — Collecte des mesures (l'utilisateur)
- [x] Gabarit de saisie : pièces, ouvertures, escaliers, équipements, généré dans `outils_docs/plan_maison/` — preuve : `outils_docs/plan_maison/mesures_a_saisir.md` (14 pièces du plan actuel préremplies, tableaux d'ouvertures, d'escaliers et d'équipements)
- [ ] Mesures du garage, de la cave et du grenier (pièces à cartes) reçues
- [ ] Mesures du RDC, du 1er et du 2e étage reçues (peut se faire par morceaux)
- [ ] Escaliers et trémies (position, dimensions) reçus
- [ ] Photos annotées rangées dans `outils_docs/plan_maison/sources/`, une cote de repère lue par photo

## A2 — Modèle de données
- [ ] Schéma `echelle.json` : étages, pièces (rectangle ou polygone), murs, ouvertures, escaliers, équipements, origine et nord
- [ ] Validation Python : pièces qui se chevauchent, ouverture hors du mur, étage sans escalier, cote nulle, carte inconnue du `placement.json`
- [ ] Migration de `placement.json` : chaque carte garde sa pièce, coordonnées en mètres facultatives
- [ ] Banc `test_plan_maison_echelle.py` avec témoins négatifs (un cas par refus)

## A3 — Rendu à l'échelle
- [ ] `genere_plan_maison.py` dessine les pièces d'un étage mesuré en SVG à l'échelle (cotes, échelle graphique, nord), ancien dessin conservé pour les étages sans mesure
- [ ] Murs, portes (arc d'ouverture), fenêtres, escaliers
- [ ] Cartes, liens et surbrillance existants repositionnés sur la géométrie réelle sans régression (mêmes 18 cartes, mêmes traits)
- [ ] Onglet par étage et vue d'ensemble, export PNG et PDF à l'échelle (thème clair)

## A4 — Éditeur web par étage
- [ ] Routes d'écriture (ce PC seulement, atomique, copie horodatée, refus pendant un build, empreinte contre l'écrasement)
- [ ] Dessin et déplacement des pièces à la souris, accrochage à la grille, saisie des cotes au clavier
- [ ] Murs, portes, fenêtres, escaliers : ajout, déplacement, suppression
- [ ] Annuler, rétablir, diff avant enregistrement
- [ ] Fond image calé à l'échelle (deux points et une distance), opacité réglable
- [ ] Glisser une carte à sa position réelle dans la pièce

## A5 — Équipements et câblage
- [ ] Prises, éclairages, volets, capteurs : symboles, hauteur, mur
- [ ] Tracé du bus RS485 et du réseau sur le plan, longueur de câble mesurée à l'échelle
- [ ] Couche à activer ou masquer, comme les vues chauffage et Wi-Fi existantes

## A6 — Qualité et documentation
- [ ] Sonde Chrome hermétique de l'éditeur (dessin, cote, enregistrement, annulation, témoins)
- [ ] Section du `outils_docs/README.md` et entrée de la carte des documents de `CLAUDE.md`
- [ ] Contrôle de secrets puis commit en français sans accents

## Améliorations restantes
- [ ] [projet] Clic sur une pièce pour ouvrir la façade animée ou la page de la carte (reprise de l'amélioration de `plan-maison`)
- [ ] [projet] Export DXF ou SVG pour un logiciel d'architecte, si le besoin apparaît
- [ ] [conversation] Recevoir les premières mesures (garage, cave, grenier) pour lancer A2 sur de vraies données

## Vérification
Régénérer la page, relire chaque étage en capture Chrome et dans un navigateur : cotes cohérentes avec les mesures saisies, mêmes cartes et mêmes liens qu'avant, aucun avertissement du générateur, bancs et sonde au vert. Aucune compilation, aucun fichier de `data/` touché.
