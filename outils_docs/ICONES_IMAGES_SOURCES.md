# Icônes, images et logos : où les chercher (annuaire)

Demande de l'utilisateur du 2026-11-13 : pour toute icône, image ou logo d'un écran (HASPmota, LVGL) ou d'une page web
de carte, **chercher d'abord dans ces sources**, dans cet ordre, en partant du nom de l'appareil ou de sa fonction.
Dessiner soi-même seulement si rien ne convient, et le dire. Si l'usage d'un appareil n'est pas clair (« Lavage » :
lave-linge ou lave-vaisselle ?), **demander** à l'utilisateur avant de choisir.

Licences vérifiées le 2026-11-13 sur les fichiers `LICENSE` des dépôts, sauf mention « à revérifier ».

## 0. Déjà dans le firmware : rien à télécharger

| Où | Quoi | Comment s'en servir |
|---|---|---|
| Polices `montserrat-10`, `-14`, `-20`, `-28` et `icons-10` à `icons-28` de HASPmota | ~130 icônes Material Design (MDI) + symboles Font Awesome de LVGL | `"text": "\uE335", "text_font": "montserrat-28"`, couleur par `text_color` |
| `lib/libesp32_lvgl/LVGL_assets/gen.sh` | **la liste exacte** des glyphes embarqués : `'0xf0335=>0xE335'` = icône MDI `F0335` servie en `\uE335` | chercher le code `F0xxx` de l'icône sur pictogrammers.com, vérifier qu'il est dans `gen.sh` |
| Objet `img` de HASPmota, `"src": "tasmota_logo"` | logo Tasmota noir | `image_recolor` + `image_recolor_opa: 255` pour le passer en blanc |

Glyphes MDI vérifiés dans `gen.sh` (2026-11-13) :

| Appareil ou fonction | Icône MDI | Glyphe |
|---|---|---|
| Lumière éteinte / allumée | `lightbulb` / `lightbulb-on` | `\uE335` / `\uE6E8` |
| Lampe | `lamp` | `\uE6B5` |
| Lave-linge | `washing-machine` | `\uE72A` |
| Pompe (cuve, vide-cave, piscine) | `water-pump` | `\uE58F` |
| Ventilation, ventilateur | `fan` | `\uE210` |
| Eau | `water` | `\uE58C` |
| Humidité (eau en %) | `water-percent` | `\uE58E` |
| Température | `thermometer` | `\uE50F` |
| Marche / arrêt | `power` | `\uE425` |

Limite : l'aperçu de l'atelier des écrans (page 7960) ne dessine pas ces glyphes (police du navigateur). La capture de
la maquette de la cave les montre en chargeant la police MDI officielle (`@mdi/font@7.4.47`), sans toucher à l'atelier.

## 1. Collections libres, sans attribution exigée à l'écran

| Site | Licence | Formats | Remarque |
|---|---|---|---|
| [Pictogrammers, Material Design Icons](https://pictogrammers.com/library/mdi/) | Pictogrammers Free License (Apache 2.0) | SVG, PNG, police | **Premier choix** : c'est la collection du firmware et de Home Assistant ; noms anglais par appareil |
| [Google Material Symbols](https://fonts.google.com/icons) | Apache 2.0 | SVG, PNG, police variable | graisse, remplissage, taille réglables |
| [Tabler Icons](https://tabler.io/icons) | MIT (garder la notice de licence avec les fichiers) | SVG, PNG, police | trait fin, cohérent |
| [Lucide](https://lucide.dev/icons/) | ISC (proche du MIT) | SVG, PNG | trait fin |
| [Phosphor](https://phosphoricons.com/) | MIT | SVG, PNG, police | 6 graisses, dont « fill » et « duotone » |
| [Simple Icons](https://simpleicons.org/) | CC0 pour les fichiers ; les marques restent à leurs propriétaires | SVG | **logos de marques** |
| [Dashboard Icons](https://dashboardicons.com/) | à revérifier par logo | SVG, PNG, WEBP | logos de services (dont Tasmota) |

## 2. Moteurs de recherche multi-collections

| Site | Remarque |
|---|---|
| [Iconify](https://icon-sets.iconify.design/) et [Icônes](https://icones.js.org/) | cherchent dans 200 collections à la fois ; **la licence est celle de la collection**, affichée sur sa page |

## 3. À éviter par défaut : attribution obligatoire ou licences mêlées

| Site | Pourquoi |
|---|---|
| Font Awesome Free | icônes sous CC BY 4.0 (attribution), police SIL OFL, code MIT (à revérifier) ; déjà en partie dans le firmware |
| Flaticon, Icons8 | gratuit seulement avec attribution visible, sinon payant |
| The Noun Project | CC BY (attribution) ou abonnement |
| SVG Repo | licences différentes d'une icône à l'autre : lire celle de chaque icône |

## Formats selon la cible

| Cible | Format | Notes |
|---|---|---|
| HASPmota, icône simple | glyphe de police (§ 0) | rien sur le FS, couleur par `text_color`, change d'icône par le `text` |
| HASPmota, icône hors firmware | PNG du FS, objet `img`, `"src"` | décodeur `USE_LVGL_PNG_DECODER` (+16 Ko) ; fichiers sous `/sd/images` (préférence de l'utilisateur, rangés par `gestionFileFolder.be::listeEtRepartitLesFichiers`) ; PNG blanc sur fond transparent, à la taille d'affichage, coloré par `image_recolor` + `image_recolor_opa` ; ou `raw` en base64 |
| LVGL pur (Berry) | même PNG, `lv.image`, source `A:/sd/images/<nom>.png` | |
| Police d'icônes sur mesure | `lv_font_conv` comme `gen.sh` (sous-ensemble MDI) ; ou une `.ttf` du FS par `text_font` (`<fichier>.ttf-<taille>`, demande beaucoup de PSRAM) | |
| Conversion SVG vers PNG ou tableau C | [LVGL Image Converter](https://lvgl.io/tools/imageconverter) (BMP, JPG, PNG, SVG vers tableau C ou binaire, LVGL 8 et 9), ou Inkscape en ligne de commande | |
| Pages web des cartes (`data/sd`) | SVG en ligne dans le HTML | pas de requête de plus |

Garder la licence de la collection à côté de tout fichier copié dans le dépôt (même règle que les polices de
`outils_docs/atelier_ecrans/polices/`).
