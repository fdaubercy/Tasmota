# Ruban LED adressable (WS2812B 5 V / WS2815 12 V) — alimentation et câblage sur ESP32-S3

Note de référence (2026-10-11). Les schémas sont dans ce dossier, en `.svg` (source) et en `.png` :
- `montage_ruban_LED_5V` : ruban **WS2812B 5 V** ;
- `montage_ruban_LED_5V_pixel_sacrifie` : ruban **WS2812B 5 V** sans 74AHCT125 (§ 3 bis) ;
- `montage_ruban_LED_12V` : ruban **WS2815 12 V**.

## 1. Ce que dit le persist de la cuve

`data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json`, bloc `modules.cuve.environnement.relais.relai1` :

| Clé | Valeur | Sens |
|---|---|---|
| `nbLeds` | **131** | nombre de pixels du ruban |
| `pin` | 6 | **GPIO6** de l'ESP32-S3 |
| `type` | 1376 | `WS2812` dans le template Tasmota (`template.GPIO[6] = 1376`) |
| `channel` | 0 | canal `light` piloté par `cuveFonctions` |

Le persist ne dit **pas** la tension du ruban : elle reste à confirmer sur le ruban lui-même (marquage
`5V` / `12V` et nombre de fils : 3 pour un WS2812B, 4 pour un WS2815). À 60 LED/m, 131 LED font
environ **2,2 m**.

Le firmware n'a rien à changer pour l'un ou l'autre : les deux puces parlent le même protocole (GRB, 800 kHz).
Pour le WS2815, voir la réserve sur la durée de reset au § 4.

## 2. Calculer l'alimentation

```
I_alim = N × I_pixel × k_couleur × (luminosité / 100) × 1,2      P = U × I_alim
```

- `N` : nombre de LED (131 ici) ;
- `I_pixel` : courant d'un pixel en blanc à 100 % (tableau ci-dessous) ;
- `k_couleur` : part des 3 canaux allumés (blanc = 1 ; teinte pure saturée = 2/3 au plus ; rouge seul = 1/3) ;
- `luminosité` : `Dimmer` de Tasmota, en % ;
- `1,2` : marge de 20 % (une alimentation ne doit pas tourner en permanence à son maximum).

| Ruban | Tension | I_pixel (blanc 100 %) | Source |
|---|---|---|---|
| WS2812B ancien ou clone | 5 V | **60 mA** (3 × 20 mA) | règle Adafruit, pire cas |
| WS2812B-V5 | 5 V | **48 mA** (3 × 16 mA) | fiche WS2812B-V5 |
| WS2815B | 12 V | **15 mA** (0,18 W / 12 V) | fiche WS2815B-V1 |

**Dimensionner pour le blanc à 100 %**, même si la cuve n'affiche que des teintes : Tasmota ne limite
pas le courant, et un `Color FFFFFF` ou un `White 100` reste toujours possible.

### Application aux 131 LED de la cuve

| Ruban | Calcul | Courant | Alimentation à acheter |
|---|---|---|---|
| 5 V, pire cas | 131 × 60 mA × 1,2 | 9,4 A | **5 V 10 A (50 W)** |
| 5 V, WS2812B-V5 | 131 × 48 mA × 1,2 | 7,5 A | 5 V 8 A (40 W) |
| 5 V, usage cuve (teinte, k = 2/3) | 131 × 32 mA × 1,2 | 5,0 A | (ne pas descendre sous 8 A) |
| 12 V, WS2815 | 131 × 15 mA × 1,2 | 2,4 A | **12 V 3 A (36 W)** |

Ajouter l'ESP32-S3 : environ 0,5 A sous 5 V (pointes Wi-Fi). En 12 V, il passe par l'abaisseur et
ne prend qu'environ 0,25 A sur le 12 V.

**Consommation au repos** (ruban alimenté, LED éteintes) : environ 1 mA par pixel en WS2812B (0,7 W
pour 131 LED) et jusqu'à 2 mA en WS2815 (fiche : < 2 mA, soit 3 W). Pour un ruban éteint la
plupart du temps, couper son alimentation par un relais.

**Section des fils** : 1,5 mm² jusqu'à 10 A (5 V) ; 0,75 mm² pour 3 A (12 V). **Fusible** juste
après l'alimentation, calibré au courant de l'alimentation.

## 3. Le niveau du signal de données : la vraie différence

L'ESP32-S3 sort **3,3 V** sur ses GPIO et ne tolère pas plus de 3,6 V en entrée.

| Ruban | Seuil « 1 » logique sur DIN (VIH) | Avec 3,3 V en direct |
|---|---|---|
| WS2812B sous 5 V | 0,7 × VDD = **3,5 V** | **hors spécification** : marche souvent, scintille parfois |
| WS2815B sous 12 V | **2,7 V** (fixe, régulateur interne) ; 5,7 V maxi | dans la spécification, marge de 0,6 V |

Solution retenue sur les deux schémas : un **74AHCT125** (ou 74HCT125, SN74AHCT1G125) alimenté en
**5 V**. Son entrée est à seuil TTL (≈ 2 V) : il accepte le 3,3 V de l'ESP32 et ressort un 5 V
franc, sans peine à 800 kHz. Puis une **résistance de 330 Ω en série**, au plus près du ruban.

> ⚠️ **Ne pas réutiliser le convertisseur de niveau à BSS138 / 2N7000** (celui de l'I²C de
> l'ADS1115) : avec ses rappels de 10 kΩ, les fronts sont trop lents pour 800 kHz.

Câblage du 74AHCT125 : VCC (14) = 5 V, GND (7), 1OE (1) = GND, 1A (2) = GPIO6, 1Y (3) = vers la
330 Ω ; entrées inutilisées 2A–4A à GND, 2OE–4OE à 5 V ; 100 nF entre VCC et GND.

En 12 V, le 74AHCT125 est **recommandé** et seulement facultatif si le fil de données fait moins de
30 cm et ne longe pas de câbles de puissance (relais, pompe).

En 5 V, « obligatoire » veut dire : obligatoire **pour rester dans la spécification**. Beaucoup de
rubans acceptent le 3,3 V en pratique, mais sans garantie (scintillements intermittents avec un fil
long, une alimentation réglée haut ou des clones). Le § 3 bis donne une solution sans puce.

## 3 bis. Variante 5 V sans 74AHCT125 : la LED sacrifiée

Schéma : `montage_ruban_LED_5V_pixel_sacrifie.png`.

Un pixel WS2812B, découpé du ruban, est alimenté à travers une **diode au silicium** : il reçoit
5,0 − 0,7 = **4,3 V**. Il sert de convertisseur de niveau :

| Étage | Seuil « 1 » (0,7 × VDD) | Signal reçu | Marge |
|---|---|---|---|
| LED sacrifiée, VDD = 4,3 V | 3,0 V | 3,3 V (GPIO6) | 0,3 V |
| Ruban, VDD = 5 V | 3,5 V | ≈ 4,3 V (DO de la LED sacrifiée, signal régénéré) | 0,8 V |

Branchement :
1. **Découper un pixel** au bout du ruban, sur le trait de coupe, en gardant ses plots +5V, DIN, DO, GND.
2. **Diode** 1N4001 (ou 1N4148 : le pixel tire 60 mA au plus) : anode sur le +5 V de l'alimentation,
   cathode (côté bague) sur le plot +5V du pixel découpé. Seul ce pixel passe par la diode.
3. **GPIO6 → DIN du pixel** par un fil le plus court possible (< 10 cm) : le pixel se loge dans le
   boîtier de l'ESP32.
4. **DO du pixel → 330 Ω → DIN du ruban** : ce fil peut être long, le signal y est déjà à ≈ 4,3 V.
5. **GND** du pixel relié au GND commun.
6. **Persist** : la LED sacrifiée devient le pixel n° 1, donc `relai1.nbLeds` passe de 131 à **132**
   (`data/fs/configModules.be:119-122` envoie `Pixels <nbLeds>`). Elle s'allume comme le reste du
   ruban et sert de témoin dans le boîtier ; sa couleur est un peu fausse (le bleu manque de tension
   à 4,3 V), sans conséquence.
7. **Vérifier** : 4,2 à 4,4 V sur le plot +5V du pixel ; ruban en blanc 100 % quelques minutes puis en
   animation, sans scintillement.

Limites :
- **Pas de diode Schottky** (1N5819…) : sa chute de 0,3 V donne 4,7 V au pixel, donc un seuil de
  3,3 V : aucun gain.
- Avec une alimentation réglée à 5,25 V, le pixel reçoit 4,55 V (seuil 3,2 V) : ça tient encore. Au-delà,
  non.
- La marge à l'entrée est de 0,3 V, contre 1,3 V avec le 74AHCT125 (seuil TTL 2,0 V). Le 74AHCT125
  reste la solution de référence ; la LED sacrifiée est la solution sans composant à commander.

## 4. Points propres à chaque montage

**5 V (WS2812B)** — `montage_ruban_LED_5V.png`
- 1000 µF ≥ 10 V aux bornes d'entrée du ruban (appel de courant à l'allumage).
- Le +5 V du ruban ne traverse **jamais** l'ESP32 : la carte prend son 5 V en dérivation du rail.
- Au-delà d'environ 1,5 m allumé en blanc, la fin du ruban jaunit (chute de tension) : réinjecter
  +5 V et GND à l'autre bout, depuis l'alimentation.
- Flashage par USB : débrancher le fil +5 V de la carte (garder le GND) si le dev-kit n'a pas de
  diode entre son 5 V USB et sa broche 5V.

**12 V (WS2815)** — `montage_ruban_LED_12V.png`
- 4 fils : +12V, **DI**, **BI** (ligne de secours), GND. **BI du premier pixel à GND.**
- Un pixel mort est sauté grâce à BI (deux pixels morts consécutifs coupent la suite).
- L'ESP32 est alimenté par un **abaisseur à découpage** 12 → 5 V ≥ 1 A (MP1584, LM2596…), réglé à
  5,0 V **avant** d'y brancher la carte. Pas de 7805 : 3,5 W perdus en chaleur.
- 470 à 1000 µF ≥ 25 V aux bornes du ruban. Une seule arrivée suffit sur 5 m.
- **Jamais de 12 V sur DI ni BI** (5,7 V maxi).
- **Réserve firmware** : la fiche WS2815B exige un reset > 280 µs ; `TasmotaLED` (timing WS2812)
  envoie 80 µs (`lib/lib_basic/TasmotaLED/src/TasmotaLED.cpp:46`). Sans effet tant que deux trames
  ne se suivent pas à moins de 280 µs, ce qui est le cas normal (une trame toutes les ≥ 50 ms). Si
  le ruban montre un jour une trame décalée, c'est la première piste.

Dans les deux cas : **GND commun** entre alimentation, ESP32, 74AHCT125 et ruban ; brancher GND
d'abord, puis l'alimentation, puis les données.

## 5. 5 V ou 12 V : comparatif

| Critère | WS2812B 5 V | WS2815 12 V |
|---|---|---|
| Courant pour 131 LED (blanc) | 6,3 à 7,9 A | 2,0 A |
| Alimentation | 5 V 8–10 A, encombrante | 12 V 3 A, courante et compacte |
| Chute de tension | forte : fin du ruban jaunie au-delà de ~1,5 m, réinjection | négligeable sur 5 m, une seule arrivée |
| Fils | 1,5 mm² | 0,75 mm² |
| Signal DIN depuis l'ESP32 | 3,3 V hors spécification : 74AHCT125 **obligatoire** | 3,3 V dans la spécification : 74AHCT125 **recommandé** |
| Pixel défaillant | coupe toute la suite du ruban | sauté grâce à la ligne BI |
| Alimentation de l'ESP32 | directement sur le 5 V du ruban | abaisseur 12 → 5 V à ajouter |
| Consommation au repos | ≈ 1 mA/pixel → 0,7 W | < 2 mA/pixel → jusqu'à 3 W |
| Rendement | ≈ 31 W en blanc | ≈ 24 W en blanc |
| Luminosité par LED | même boîtier 5050 ; 16 mA par canal (V5), un peu plus fort au début du ruban | 12 mA par canal (R 310 / V 800 / B 190 mcd) ; légèrement moins fort, mais **uniforme** sur toute la longueur |
| Découpe | à chaque LED | à chaque LED (à ne pas confondre avec le WS2811 12 V : 1 puce pour 3 LED) |
| Prix du ruban (5 m, 60 LED/m) | **≈ 11 à 30 €** | **≈ 35 à 55 €** (≈ 2 fois plus cher) |
| Compatibilité Tasmota | native (timing WS2812) | protocole identique ; reset un peu court (§ 4) |

**Pour la cuve (131 LED, ≈ 2,2 m)** : les deux conviennent. Le 5 V est moins cher et alimente
l'ESP32 sans abaisseur, au prix d'une alimentation de 10 A, de fils plus gros et d'une réinjection
si le ruban est allumé en blanc. Le 12 V est plus robuste (ligne de secours, pas de chute de tension,
signal 3,3 V dans la spécification) pour environ 25 € de plus.

## 6. Cas d'un ambilight de TV

Un ambilight fait le tour de l'écran : ≈ 3,8 m pour une 55″, ≈ 4,5 m pour une 65″, soit 230 à
270 LED à 60 LED/m. Sur ces longueurs, l'avantage passe au **12 V (WS2815)** :

- en 5 V, il faut 11 à 16 A en blanc et **deux ou trois points de réinjection** derrière la TV, sinon
  le dernier côté du cadre vire au jaune, ce qui se voit justement sur un ambilight (blanc et gris
  fréquents) ;
- en 12 V, 4 à 5 A, une seule arrivée et une teinte identique sur les quatre côtés ;
- une LED morte derrière une TV fixée au mur est pénible à remplacer : la ligne BI la contourne.

Le 5 V garde l'avantage pour un écran ≤ 50″ (≤ 3,5 m), où la réinjection reste simple, et pour le
budget. Dans les deux cas :
- **ne pas prendre de WS2811 12 V** (une puce pour trois LED : ambilight trop grossier) ;
- **ne pas alimenter le ruban par le port USB de la TV** (0,5 à 1,5 A : insuffisant) ;
- couper l'alimentation du ruban quand la TV est éteinte (relais) : au repos, 270 pixels WS2815
  consomment jusqu'à 6,5 W en permanence.

## 7. Sources

- WS2815B-V1, fiche Worldsemi (VIH 2,7 V, 0,18 W/pixel, repos < 2 mA, reset > 280 µs) :
  https://www.ledyilighting.com/wp-content/uploads/2025/02/WS2815B-datasheet.pdf
- WS2812B-V5, fiche (VIH 0,7 VDD, 16 mA par canal) : https://learn.watterott.com/kb/ws281x/WS2812B-v5.pdf
- Adafruit, « Powering NeoPixels » (60 mA/pixel, 1000 µF, 0,7 × VDD, injection) :
  https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels
- 74AHCT125 pour WS2812B depuis un ESP32 : https://forum.arduino.cc/t/ws2812b-level-shifter-is-worse-why/1439196
- Niveau logique 5 V et WS2815 (WLED) : https://wled.discourse.group/t/voltage-drop-logic-level-shifter/8588
- WS2815 et WS2812B comparés : https://www.superlightingled.com/blog/ws2815-vs-ws2812b/
- Prix (relevés le 2026-10-11) : WS2812B 5 m 60 LED/m, 10,99 € (https://www.domadoo.fr/fr/esphome/7546-smlight-ruban-led-5m-ws2812b-compatible-wled-slwf-03-slwf-09-esphome.html) ;
  WS2815 BTF-Lighting 5 m 30 LED/m, 30,99 € (https://www.amazon.fr/BTF-LIGHTING-WS2812B-30pixels-Individuellement-adressable/dp/B07LG6KH6L) ;
  WS2815 60 LED/m IP68, 53,99 $ (https://www.btf-lighting.com/products/ws2815-dual-signal-led-strip-waterproof-dc12v).
