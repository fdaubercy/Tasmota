# Jauges pour l'affichage des capteurs — catalogue

Recherche du 2026-10-31, faite pour le niveau de la cuve du garage, **à réutiliser pour tout
affichage de mesure** (niveau, température, tension, taux...). Huit modèles, chacun rendu à
62 % de la cuve (340 × 180 × 110 cm = 6 732 L, soit 68 cm et 4 174 L).

- Images : `jauge-A.png` à `jauge-H.png` (ce dossier).
- Code de chaque modèle, interactif (curseur commun, seuils de couleur) : `catalogue_jauges.html`,
  à ouvrir dans un navigateur. Les librairies A, B, C y viennent de jsDelivr (réseau requis).

## Choix retenu : A ou H

| | A — Liquide animé ECharts | H — Demi-cercle sobre |
|---|---|---|
| Image | `jauge-A.png` | `jauge-H.png` |
| Technique | extension `echarts-liquidfill` (MIT) sur ECharts | un seul arc SVG (`stroke-dasharray`), aucune librairie |
| Poids | ECharts (`data/sd/js/echarts.min.js.gz`, 368 Ko) + l'extension | ≈ 1 Ko |
| Où | page à part (comme `/graphiques`) ou script chargé hors de la zone rafraîchie | directement dans un gabarit `data/sd/html/webSensor*.html` |
| Point ouvert | `echarts-liquidfill` 3.x vise ECharts 5 ; les cartes ont ECharts 6 : compatibilité **non vérifiée** | la valeur substituée dans l'attribut doit être un nombre seul (sans « % ») |

Arbitrage entre les deux non tranché au 2026-10-31.

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
