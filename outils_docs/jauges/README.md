# Jauges pour l'affichage des capteurs — catalogue

Recherche du 2026-10-31, faite pour le niveau de la cuve du garage, **à réutiliser pour tout
affichage de mesure** (niveau, température, tension, taux...). Huit modèles, chacun rendu à
62 % de la cuve (340 × 180 × 110 cm = 6 732 L, soit 68 cm et 4 174 L).

- Images : `jauge-A.png` à `jauge-H.png` (ce dossier).
- Code de chaque modèle, interactif (curseur commun, seuils de couleur) : `catalogue_jauges.html`,
  à ouvrir dans un navigateur. Les librairies A, B, C y viennent de jsDelivr (réseau requis).
- Autour des jauges (2026-10-31) : `liens_vers_jauges.html` (signaler le lien vers une page de
  jauges) et `dispositions_page_energie.html` (organiser une page de graphiques), voir plus bas.

## Choix retenu : A ou H

| | A — Liquide animé ECharts | H — Demi-cercle sobre |
|---|---|---|
| Image | `jauge-A.png` | `jauge-H.png` |
| Technique | extension `echarts-liquidfill` (MIT) sur ECharts | un seul arc SVG (`stroke-dasharray`), aucune librairie |
| Poids | ECharts (`data/sd/js/echarts.min.js.gz`, 368 Ko) + l'extension | ≈ 1 Ko |
| Où | page à part (comme `/graphiques`) ou script chargé hors de la zone rafraîchie | directement dans un gabarit `data/sd/html/webSensor*.html` |
| Point ouvert | `echarts-liquidfill` 3.x vise ECharts 5 ; rendu vérifié avec l'ECharts 6.1.0 des cartes le 2026-10-31 | dans un gabarit `webSensor*`, la valeur substituée dans l'attribut doit être un nombre seul (sans « % ») |

**En service (premier essai, 2026-10-31)** : les deux, sur la page `/cuve` de la cuve et du P4 — A pour le
volume en litres, H pour le taux en %. Compatibilité de l'extension avec ECharts 6.1.0 vérifiée (rendu et mise à
jour). Mode d'emploi : `outils_docs/README.md` § « Les jauges du niveau de la cuve » ; code :
`data/fs/cuvePageFonctions.be`, `data/sd/js/cuve.js`.

## Tous les modèles

| Lettre | Modèle | Technique | Poids | Page d'accueil Tasmota |
|---|---|---|---|---|
| A | Liquide animé (vagues) | echarts-liquidfill | ECharts + extension | non (script) |
| B | Cadran à aiguille, zones aux seuils | série `gauge` native d'ECharts | 0 Ko de plus si ECharts est déjà là | non (script) |
| C | Règle graduée verticale | canvas-gauges `LinearGauge` (MIT) | ≈ 45 Ko | non (script) |
| D | Coupe de la cuve à l'échelle, cm et litres | SVG | ≈ 2 Ko | oui |
| E | Bulle à vague, chiffre bicolore | SVG + animation CSS (D3 Liquid Fill Gauge refait sans D3) | ≈ 2 Ko | oui, mais la vague repart à chaque rafraîchissement |
| F | Tube à flotteur gradué | SVG | ≈ 2 Ko | oui |
| G | Barre de 10 segments façon LED | CSS | < 1 Ko | oui |
| H | Demi-cercle sobre | SVG | ≈ 1 Ko | oui |

Seuils de couleur utilisés partout : rouge sous 20 %, orange sous 40 %, bleu au-delà.

## La contrainte de la page d'accueil

Un gabarit `webSensor*.html` est inséré dans la page d'accueil de Tasmota, que le navigateur
**remplace toutes les ~2 s** (rafraîchissement de la zone des capteurs par `innerHTML`). Deux
conséquences :

1. un `<script>` placé dans le gabarit **n'est jamais exécuté** : seuls SVG et CSS purs (D à H)
   s'y posent tels quels, la valeur étant substituée dans les attributs par les `#...#` du gabarit ;
2. une animation CSS **repart de zéro** à chaque rafraîchissement (E, l'ondulation de D).

Pour A, B ou C : page dédiée servie par un module Berry (modèle : `/graphiques`), ou script chargé
une seule fois hors de la zone rafraîchie qui redessine après chaque remplacement (non essayé).

## Signaler le lien vers une page de jauges

`liens_vers_jauges.html` : 8 façons d'annoncer, dans un encadré de l'accueil, la page dédiée
(maquettes de l'encadré de la cuve à 340 px, HTML et CSS seuls, compatibles avec la contrainte
ci-dessus). **Retenu le 2026-10-31 pour la cuve : B, icône de cadran seule** (SVG en ligne dans la
`<legend>` de `data/sd/html/webSensorNiveauCuve.html`, infobulle « Jauges du volume et du taux »).

| Lettre | Forme | Coût sur l'encadré |
|---|---|---|
| A | texte « (jauges) » dans le titre | aucun |
| B | icône de cadran seule dans le titre | aucun |
| C | petit bouton bleu « Jauges › » dans le titre | allonge la ligne du titre |
| D | titre entier cliquable avec ↗ | aucun |
| E | bouton « Voir les jauges » en bas | une ligne de plus (~40 px) |
| F | barre d'aperçu du taux, cliquable | une ligne ; taux numérique dans le gabarit |
| G | puce icône + « Jauges » | allonge la ligne du titre |
| H | valeurs (taux, volume) cliquables | aucun |

`bouton_energie_accueil.png` : maquette du bouton « Énergie » sur la vraie page d'accueil du différentiel, **retenue le
2026-11-02** (l'encadré d'énergie est généré par Tasmota, sans gabarit où poser une icône).

## Disposer une page de graphiques

`dispositions_page_energie.html` : 3 façons d'organiser une page de mesures avec des
consommations par heure, par jour et par mois (exemple : énergie du différentiel). **Retenu le
2026-10-31 pour la page Énergie : B, les trois graphiques empilés.**

| Lettre | Disposition | Pour |
|---|---|---|
| A | onglets Jour / Mois / Année, un seul graphique en barres | page courte, téléphone |
| B | les trois périodes empilées, plus petites | tout voir sans cliquer |
| C | exploration par clic (année → mois → jour), fil pour remonter | revoir un jour passé ; demande de garder les heures de chaque jour |

Règle de choix du graphique selon la donnée : une **quantité sur une période** (kWh d'une heure,
d'un jour, d'un mois) en **barres** ; une **grandeur instantanée** (puissance, courant) en
**courbe** ; un **rapport borné** (facteur de puissance 0..1) en **cadran** ; une valeur quasi
constante (fréquence) en **simple valeur**.

## Défauts connus des images

- C : graduation affichée jusqu'à 100 cm au lieu de 110.
- F : les chiffres 110 et 100 se touchent presque.

## Sources

- D3 Liquid Fill Gauge : https://gist.github.com/brattonc/5e5ce9beee483220e2f6
- echarts-liquidfill : https://github.com/ecomfe/echarts-liquidfill
- canvas-gauges : https://github.com/Mikhus/canvas-gauges
- JustGage (style de H) : https://github.com/toorshia/justgage
- ThingsBoard, Analog Water Level Meter (style de F) :
  https://thingsboard.io/docs/reference/widgets/scada/traditional-fluid-system/right-analog-water-level-meter/
- Node-RED, niveau de cuve en SVG : https://discourse.nodered.org/t/svg-animation-tank-level/86360
