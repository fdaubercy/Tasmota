# Électronique des cartes Tasmota de ce dépôt

## 1. Du persist au schéma

- `python scripts/inventaire_materiel.py data/<lieu>/<carte>` : tableau GPIO → fonction,
  périphériques I2C, ModBus, alertes (strapping, flash, PSRAM, ports partagés).
- **L'environnement fait foi**, pas `template.GPIO` (réécrit au boot par `configModules.be`).
  Code GPIO Tasmota = rang dans `UserSelectablePins` × 32 + (index − 1) ; dans un bloc
  `environnement`, code réel = `type + id − 1` (WS2812 : `type + channel`).
- **Le persist ne dit rien du câblage réel.** Avant de dessiner, faire confirmer :
  tensions d'alimentation de chaque module, modules réellement achetés (lien ou photo),
  capteurs branchés sur chaque voie, ce qui est soudé ou non.
- Code Berry, commandes `ReglageXxx`, `autoexec.be`, solidification :
  **REQUIRED SUB-SKILL : tasmota-berry**. Docs du dépôt :
  `outils_docs/Electronique/ADS1115/CABLAGE_ADS1115.md`, `CABLAGE_RUBAN_LED.md`,
  `outils_docs/PROTOCOLE_MODBUS.md` (§8 carte 16 relais).

## 2. ESP32-S3 DevKitC-1 (WeAct, LED RGB sur GPIO48)

| Broches | Règle |
|---|---|
| 0, 3, 45, 46 | strapping : ne rien y imposer au démarrage |
| 19, 20 | USB natif |
| 26-32 | flash : inexistantes sur le connecteur |
| 33-37 | PSRAM octale sur N8R8/N16R8 : à éviter |
| 38 | LED RGB sur la **v1.1** Espressif (48 sur v1.0 et WeAct) |
| 43, 44 | UART0 (console de flashage) |

Ordre des broches (vu de dessus, antenne en haut) :
- J1 gauche : 3V3 3V3 RST 4 5 6 7 15 16 17 18 8 3 46 9 10 11 12 13 14 5V GND
- J3 droite : GND TX(43) RX(44) 1 2 42 41 40 39 38 37 36 35 0 45 48 47 21 20 19 GND GND
- **Entraxe des deux rangées : à mesurer** (25,4 mm mesuré par un utilisateur KiCad ; 22,86 mm
  dans la bibliothèque Espressif). Paramètre `ECART_DEVKIT` du générateur, **25,4 par défaut**.
  Mesure au pied à coulisse : du bord gauche d'une broche de la rangée 1 au bord gauche de la
  broche en face sur la rangée 2 (bord à bord du même côté = entraxe, sans soustraire
  l'épaisseur des broches). Vérifier : 25,4 ou 22,86, rien d'autre. Ou plus simple : piquer
  le DevKit dans une plaque d'essai et compter les rangées d'écart (10 → 25,4 ; 9 → 22,86).
- Alimenter par la broche 5V **à travers une Schottky** (anti-retour quand l'USB est branché).

## 3. Interfaces

| Fonction | Montage retenu | Pourquoi |
|---|---|---|
| Ruban WS2812B/WS2815 | 74AHCT125 alimenté en 5 V, 1OE à la masse, 330 Ω série près du bornier ; entrées inutilisées à la masse, OE inutilisés au 5 V ; 100 nF | VIH du ruban = 0,7 × VDD : le 3,3 V est hors spécification |
| WS2815 (12 V) | +12 V du ruban **direct depuis l'alimentation** (2-3 A), pas à travers la carte ; BI du 1er pixel à la masse ; 470-1000 µF au ruban ; jamais de 12 V sur DI/BI | courant |
| ADS1115 en 3,3 V | I2C en direct ; ADDR à la masse (0x48) | pas de conversion de niveau |
| ADS1115 en 5 V | convertisseur I2C à BSS138 obligatoire | tirages du module à 5 V, VIH 3,5 V |
| 0-10 V → ADS 3,3 V | 24 kΩ / 10 kΩ 1 % → 2,94 V ; 100 nF | voir CABLAGE_ADS1115.md |
| 0-20 mA → ADS 3,3 V | shunt 150 Ω 1 % + 1 kΩ série | protège l'entrée d'un défaut |
| DS18B20 | rappel 4,7 kΩ au 3V3 ; bornier 3V3/DQ/0V | 1-Wire |
| RS485 | module à direction automatique sur GPIO TX/RX ; VCC par cavalier 3V3 (défaut) / 5V | un module en 5 V renvoie un RX à 5 V vers l'ESP32 |
| TX/RX inversés | se corrige dans le persist (échanger les `pin`), pas sur la carte | souplesse |
| Voyants | GPIO → R → LED → masse (`GPIO_LEDLNK`/`GPIO_LED1` non inversés) ; R = (3,3 − Vf) / 2 mA : rouge/jaune 680 Ω, verte 560 Ω, **bleue/blanche 150-220 Ω** (Vf ≈ 2,9 V : avec 1 kΩ elle ne reçoit que 0,3 mA) | ~2 mA, visible |
| Entrée TOR, contact sec (fin de course, `GPIO_SWT1`) | rappel 10 kΩ au 3V3 + 1 kΩ série + 100 nF à la masse ; bornier 2 bornes (entrée / 0V) ; `SwitchMode` dans le persist | anti-rebond, câble long |
| Entrée TOR 12-24 V (capteur inductif PNP…) | optocoupleur (PC817 : 2,2-4,7 kΩ côté LED) ou pont diviseur + Zener 3,3 V ; bornier +V / signal / 0V | jamais plus de 3,3 V sur un GPIO |
| Sortie relais : module du commerce | barrette vers le module ; vérifier tension de bobine (5 ou 12 V) et niveau actif (beaucoup sont actifs à l'état bas → `GPIO_REL1_INV`) | un module 5 V « high level trigger » tolère le 3,3 V, pas tous |
| Sortie relais soudé | transistor NPN (BC337) ou MOSFET logique (2N7000 jusqu'à 200 mA), 1 kΩ de base, **diode de roue libre** (1N4148) sur la bobine, voyant ; bornier COM/NO/NC | protection contre la surtension de coupure |
| Contact sec vers une motorisation (portail, rideau) | relais en contact sec NO, bornier dédié éloigné de la logique | la motorisation garde son alimentation |

## 4. Entrée d'alimentation 12 V (bloc type)

Bornier → **fusible réarmable** (PTC radial MF-R, pas 5,1 mm) → **Schottky série** (1N5819 :
inversion de polarité) → **TVS** (P6KE18CA) + 100 µF/25 V + 100 nF → **TSR 1-2450** (abaisseur
à découpage 1 A, brochage 7805, ~90 %, sans réglage) → 47 µF → 5 V.
Capteurs alimentés par la carte : **PTC séparé** (bornier « +12 »), dimensionné ≥ 2 × leur
somme (le maintien d'un PTC baisse d'environ 20 % à 50 °C dans un boîtier).

## 5. Bilan d'alimentation (méthode + exemple cuve)

Automatisé par `scripts/bilan_alimentation.py` (schéma + `bilan.json`) : le lancer plutôt que
refaire le calcul à la main ; la méthode ci-dessous explique ce qu'il fait.

1. Lister chaque consommateur par rail, au **pire cas** (pics Wi-Fi, LED pleine puissance).
2. Ramener au 12 V : P(5 V) / rendement (0,9 pour TSR 1) / 12.
3. Marge ≥ 25 % ; choisir une alimentation chargée à ≤ 75-80 % en régime (boîtier fermé =
   déclassement thermique).

| Consommateur (cuve) | Rail | Pire cas | Au 12 V |
|---|---|---|---|
| DevKit ESP32-S3 (pics Wi-Fi) + LED RGB | 5 V | 0,40 A | |
| 74AHCT125, 3 voyants, RS485, ADS1115, DS18B20 | 5 V / 3V3 | 0,03 A | |
| **Sous-total 5 V** | | 0,43 A ≈ 2,2 W | **0,20 A** |
| 2 boucles 4-20 mA (25 mA en défaut) + 2 capteurs 0-10 V (~20 mA) | 12 V | | **0,09 A** |
| Ruban WS2815, 131 pixels × 15 mA (blanc plein) | 12 V | | **1,97 A** |
| **Total** | | | **2,26 A ≈ 27 W** |

Avec 25 % de marge : 2,8 A → **alimentation 12 V ≥ 3,5 A ; recommandé 12 V 5 A (60 W)**,
chargée à ~45 %, donc froide et durable en boîtier. Exemples : Mean Well IRM-60-12ST
(encapsulée, bornier à vis, à vérifier chez le revendeur) ou HDR-60-12 (rail DIN, 4,5 A).
Fusible côté ruban : 3,15 A temporisé entre l'alimentation et le ruban. Côté carte : le PTC
0,5 A (0,30 A consommés). Si le ruban ne s'allume jamais en blanc plein, la charge réelle est
plus proche de 1,5 A, mais on dimensionne au pire cas.

## 6. Masse, CEM, sécurité

- Plans de masse sur les 2 faces + vias de couture (pas ~5 mm) ; zone d'exclusion sous
  l'antenne ; pistes de puissance ≥ 0,8-1 mm.
- Câbles de capteurs longs : 100 nF sur chaque entrée ADS, série 1 kΩ (ou 4,7 kΩ si un court-
  circuit du 24 V est possible).
- **230 V : jamais sur une carte porteuse.** Si une sortie commute du secteur : module relais du
  commerce certifié, câblé hors carte, ou carte de puissance dédiée (isolement ≥ 6 mm entre
  secteur et TBTS, fente fraisée sous le relais, pistes ≥ 2 mm, fusible). Le dire à l'utilisateur
  et le laisser choisir ; ne pas dessiner de 230 V sans son accord explicite.
- Bilan d'un module à relais : bobine 5 V ≈ 70-90 mA par relais (12 V ≈ 30-40 mA), à compter
  au pire cas tous relais collés ; charges impulsionnelles (moteur) : jamais par la carte.
