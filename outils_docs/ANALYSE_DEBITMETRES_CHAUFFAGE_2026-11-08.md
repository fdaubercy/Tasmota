# Mesurer les 6 débits de la nourrice de chauffage avec Tasmota

> Analyse du 2026-11-08, en lecture seule : rien n'a été modifié dans le dépôt, rien n'a été essayé sur une carte.
> Les numéros de ligne cités sont ceux du jour (document daté).

## En bref

- **Un seul ESP32 suffit pour les 6 débits.** La limite de 2 débitmètres ne concerne que le pilote
  `FlowRateMeter` ; d'autres mécanismes de Tasmota couvrent les 4 autres.
- Une liaison vers un maître n'est utile que si l'affichage doit se trouver **ailleurs** qu'à la nourrice.
- Pour trancher, il faut deux réponses (voir § 7) : le **type de sortie** des débitmètres et
  l'**endroit** de l'affichage.

---

## 1. D'abord : quelle sortie ont les débitmètres ?

Tout dépend du type de signal, et « analogique » peut désigner trois choses :

| Type de sortie | Exemples | Ce qu'il faut dans Tasmota |
|---|---|---|
| **Impulsions** (fréquence proportionnelle au débit) | YF-B5, YF-S201, capteurs à effet Hall | Le pilote `FlowRateMeter`, limité à 2, ou les compteurs (§ 3) |
| **Tension ou courant** (0-10 V, 4-20 mA, 0,5-3,5 V) | Grundfos VFS, débitmètres industriels | Une entrée analogique (ADC ou ADS1115). **La limite de 2 ne s'applique pas** |
| **Mécanique à lecture visuelle** | Débitmètres à flotteur intégrés aux nourrices | Rien n'est mesurable : il faut les remplacer |

---

## 2. Pourquoi 2 débitmètres au maximum

La limite est inscrite à trois endroits du code :

- `tasmota/include/tasmota_template.h:541` : `#define MAX_FLOWRATEMETER 2`.
- `tasmota/tasmota_xsns_sensor/xsns_96_flowratemeter.ino` : deux routines d'interruption écrites en dur,
  `FlowRateMeter1IR` et `FlowRateMeter2IR`.
- `tasmota/include/tasmota_types.h:923` : `flowratemeter_calibration[2]`. L'étalonnage est rangé dans la
  structure des réglages du firmware (`Settings`).

On pourrait passer à 6 dans le fork, mais il faudrait toucher à cette structure de réglages : conflit à
chaque synchronisation avec l'amont, et risque de décaler les réglages déjà enregistrés sur les cartes.
**Non recommandé.**

---

## 3. Les solutions

### Solution 1 — un seul module, débitmètres à impulsions (recommandée)

- Débits 1 et 2 : `FlowRateMeter`, sans écrire de code (débit instantané, cumul du jour, étalonnage par
  `Sensor96 1 <facteur × 1000>` et `Sensor96 2 <facteur × 1000>` ; unité L/min ou m³/h par `Sensor96 0 0|1`).
  **Retenu (2026-11-08)** : le module Berry de la carte force `Sensor96 0 0` et un calibrage neutre (1000), et applique
  le facteur K de chaque voie, réglé par `ReglageDebits k <voie> <K>` : un seul étalonnage pour les 6 voies.
- Débits 3 à 6 : les **compteurs** de Tasmota (`Counter1` à `Counter4`). Il y en a 4 au maximum
  (`tasmota/include/tasmota.h:74`, `MAX_COUNTERS = 4`), chacun déclenché par interruption
  (`xsns_01_counter.ino:177`, `attachInterruptArg`).
- Un petit module Berry lit `gpio.counter_read(n)` (exposé par `be_gpio_lib.c`) chaque seconde et calcule :
  **L/min = impulsions par seconde ÷ facteur K du capteur** (K donné par le fabricant, en Hz par L/min).

Points de vigilance :

- Un débit de radiateur est faible, souvent 0,5 à 3 L/min. Avec un capteur à 7,5 Hz par L/min, compter
  sur 1 s donne une résolution de 0,13 L/min : trop grossier. Calculer sur une **fenêtre glissante de 5 à
  10 s**.
- Poser `CounterDebounce 0`, sinon les impulsions rapides sont filtrées.
- Les deux méthodes (pilote et compteurs) donnent des JSON différents : le module Berry peut publier les
  6 débits dans un seul bloc homogène.
- Berry ne sait pas gérer une interruption GPIO lui-même : lire les entrées en boucle depuis Berry ne
  suffirait pas. D'où l'usage des compteurs du firmware.

### Solution 2 — un seul module, débitmètres à sortie en tension ou en courant

- Deux **ADS1115** sur le bus I2C donnent 8 voies : c'est le montage déjà utilisé sur la cuve. Tasmota en
  gère jusqu'à 4, aux adresses 0x48 à 0x4B (`xsns_12_ads1115.ino:46-49`).
- Capteur 4-20 mA : lu à travers une résistance de 165 Ω (0,66 à 3,3 V).
- Capteur 0-10 V : lu à travers un pont diviseur.
- Le module Berry convertit la tension en L/min (droite d'étalonnage du capteur).
- Les entrées ADC internes de l'ESP32 existent aussi (`MAX_ADCS`, `tasmota.h:157-170`) mais sont moins
  précises et peu linéaires : l'ADS1115 est préférable.

### Solution 3 — 3 modules de 2 débitmètres chacun, avec un maître

- Aucun code côté capteurs : chaque module utilise le pilote natif.
- En contrepartie : 3 alimentations, 3 cartes à maintenir, et une liaison qui peut tomber.
- Rentable seulement si les départs sont éloignés les uns des autres, ce qui n'est pas le cas sur une
  nourrice.

### Écartée — modifier le pilote pour 6 débitmètres

Voir § 2 : divergence avec l'amont dans la structure des réglages.

---

## 4. Si plusieurs modules : quelle communication vers le maître ?

| Liaison | Adaptée ? | Pourquoi |
|---|---|---|
| **I2C** entre deux ESP32 | ❌ | Tasmota ne sait pas faire d'un ESP32 un esclave I2C (rien de tel dans le code). Et l'I2C ne tient que sur environ 1 m. Il sert à **ajouter des entrées à un module** (ADS1115, écran), pas à relier des modules. |
| **Filaire RS485 / ModBus RTU** | ✅ le plus robuste | Le code `TasmotaSlaveModBus` du dépôt existe déjà, côté maître P4 et côté esclaves. Fonctionne sans Wi-Fi ni broker, supporte de longs câbles. Inconvénient : un câble à tirer jusqu'au maître. |
| **ModBus UDP** (transport maison du dépôt) | ✅ si pas de câble possible | Même code, transporté par le Wi-Fi. |
| **Range Extender** | ⚠️ | Topologie de réseau, pas un protocole : les esclaves sont derrière le point d'accès du maître, et ModBus UDP passe par lui. À retenir seulement si la chaufferie est hors de portée de la box. Pièges connus : le multicast n'atteint pas le PC, le sniffeur reste muet. |
| **MQTT** | ✅ le plus simple | Natif : chaque module publie déjà ses mesures (`tele/<topic>/SENSOR`), le maître s'abonne en Berry. Mais tout dépend du broker : s'il tombe, plus d'affichage. |

---

## 5. Affichage

| Où | Matériel | Remarques |
|---|---|---|
| **Page web du module** | aucun | Les débits apparaissent nativement dans le tableau des mesures. Sur un S3, le framework `/graphiques` et l'historique du dépôt s'appliquent tels quels. |
| **Écran local, économique** | LCD I2C 20×4 | Pilote `tasmota_xdsp_display/xdsp_01_lcd.ino`, `USE_DISPLAY_LCD` (adresses 0x27 ou 0x3F). 3 débits par ligne, piloté par `DisplayText`. |
| **Écran local, plus lisible** | OLED 128×64 | 8 lignes : une ligne par départ. Le pilote SSD1306 dédié a été retiré au profit de `USE_UNIVERSAL_DISPLAY` (`xdsp_17_universal.ino`). |
| **Écran graphique** | TFT avec LVGL | Sur S3 ou P4. Le P4 du dépôt a déjà `USE_LVGL` (`user_config_override.h:2108`). Si le maître est le P4, l'écran de son kit peut tout afficher. |

L'écran local se branche sur le **même bus I2C** que les ADS1115 éventuels : aucune broche supplémentaire.

---

## 6. Recommandation

**Un ESP32-S3 posé à côté de la nourrice** :

- solution 1 (2 `FlowRateMeter` + 4 compteurs + Berry) si les capteurs sortent des impulsions ;
- solution 2 (2 ADS1115) s'ils sortent une tension ou un courant ;
- affichage : sa page web, plus un LCD 20×4 ou un OLED sur le bus I2C.

Pas de liaison nécessaire. Si les débits doivent **aussi** apparaître sur le P4 du garage, la carte les
envoie en ModBus UDP, comme la cuve, ou en MQTT.

---

## 6 bis. Un ESP32-S3 est-il assez rapide pour 6 voies ?

Oui : la puissance de calcul n'est pas la limite. Les vraies limites sont ailleurs (tableau ci-dessous).

**Charge processeur (estimation, non mesurée)** : une impulsion = une interruption courte (lire l'heure,
comparer, incrémenter), de l'ordre de quelques µs.

| Cas | Fréquence par voie | Interruptions/s (6 voies) | Charge d'un cœur à ~5 µs |
|---|---|---|---|
| Capteur YF-S201 (K ≈ 7,5 Hz par L/min), 3 L/min | ~23 Hz | ~140 | < 0,1 % |
| Petit capteur à K ≈ 100 Hz par L/min, 3 L/min | ~300 Hz | ~1 800 | < 1 % |

Le pilote `FlowRateMeter` est annoncé de 1 Hz à 5 kHz (en-tête de `xsns_96_flowratemeter.ino`). Les
débits de chauffage restent très loin de ce plafond.

**Les vraies limites :**

| Limite | Où dans le code | Effet | Parade |
|---|---|---|---|
| Sous 1 Hz, `FlowRateMeter` affiche 0 | `xsns_96_flowratemeter.ino:29`, `FLOWRATEMETER_MIN_FREQ 1` | Avec K = 7,5 : un débit < 0,13 L/min s'affiche 0 (vanne thermostatique presque fermée) | Les compteurs + Berry sur une fenêtre de 10 s n'ont pas ce seuil |
| Compteurs suspendus pendant une écriture des réglages en flash | `settings.ino:769` à `797` | Une impulsion perdue au plus, rarement (les compteurs ne sont sauvés qu'à minuit et au redémarrage : `xsns_01_counter.ino:330-332`) | Négligeable sur une moyenne |
| Interruptions GPIO non placées en IRAM | `esp32-hal.h:74-79` du framework (`ARDUINO_ISR_FLAG` = 0 par défaut) | Pendant toute écriture flash (persist, historique, OTA), les fronts sont retardés ; plusieurs fronts dans la fenêtre comptent pour un | Négligeable sous 25 Hz ; à mesurer sur banc si l'historique écrit souvent |
| Parasites et rebonds sur des câbles longs | — | Impulsions fantômes : bien plus probable qu'un manque de vitesse | Câble blindé, pull-up, filtre RC, `CounterDebounce` réglé selon la fréquence max |
| Température de l'eau de chauffage | — | Beaucoup de capteurs Hall en plastique ont une température max limitée | Vérifier la fiche du capteur avant achat |

---

## 6 ter. Fréquence d'impulsions maximale pour que l'écran LCD ne soit pas gêné

### Critères d'acceptabilité retenus (à valider)

1. L'écran est mis à jour chaque seconde, avec un retard d'au plus **10 %** (imperceptible).
2. Aucune impulsion perdue en fonctionnement normal.
3. Le reste de Tasmota (page web, MQTT, Berry) garde au moins 90 % du cœur qu'il partage avec les comptages.

### Ce que coûte l'écran (lu dans le code)

- Le LCD 20×4 est piloté par un PCF8574 sur l'I2C à **100 kHz**, valeur par défaut de Tasmota
  (`support_a_i2c.ino:83`) et vitesse maximale du PCF8574 : on ne peut pas accélérer le bus.
- Un caractère = 2 demi-octets ; chaque demi-octet = 3 transactions I2C + 51 µs d'attente
  (`LiquidCrystal_I2C.cpp`, `send`, `write4bits`, `pulseEnable`). Une transaction (adresse + donnée) dure
  environ 0,2 ms à 100 kHz.
- **Un caractère ≈ 1,3 ms. Un écran 20×4 complet (4 positionnements + 80 caractères) ≈ 110 ms**, peut-être
  150 ms avec les frais du pilote I2C (estimation).
- Cette écriture est **bloquante**, dans la boucle principale de Tasmota (`xdsp_01_lcd.ino::LcdRefresh`,
  appelée chaque seconde).
- En n'écrivant que les 6 valeurs (≈ 6 caractères chacune + positionnement), la mise à jour tombe à ≈ 55 ms.

### Ce que coûtent les impulsions

- Les interruptions GPIO s'exécutent sur le cœur qui les a installées : celui de la boucle de Tasmota,
  donc **le même cœur que l'écran** (le Wi-Fi est sur l'autre). C'est la seule concurrence réelle.
- Durée d'une interruption (entrée, lecture de l'heure, comparaison, incrément, sortie) : **≈ 5 µs**, et
  10 µs en hypothèse pessimiste (estimation, non mesurée).
- Le calcul des débits en Berry (6 soustractions et divisions par seconde) coûte moins de 2 ms par seconde :
  négligeable.

**Une interruption ne peut pas corrompre l'affichage.** Elle ne fait qu'allonger les attentes. Or les
temps du HD44780 sont des minimums, et l'I2C est synchrone. L'écran est seulement ralenti.

### Calcul

Si les impulsions prennent une part `f` du cœur, l'écran met `T / (1 − f)` au lieu de `T`.
Critère 1 (retard ≤ 10 %) ⇒ `f ≤ 0,09`. Avec `f = R × t` (R = impulsions par seconde, toutes voies ;
t = durée d'une interruption) :

| Hypothèse | R max (6 voies) | **Par voie** | Écran 20×4 complet |
|---|---|---|---|
| t = 5 µs | 18 000 /s | **3 000 Hz** | 110 → 121 ms |
| t = 10 µs (pessimiste) | 9 000 /s | **1 500 Hz** | 110 → 121 ms |

Deux plafonds supplémentaires, plus bas selon les réglages :

- Pilote `FlowRateMeter` : 5 kHz (en-tête de `xsns_96_flowratemeter.ino`). Il ne limite donc rien ici.
- Compteurs avec anti-rebond : la fréquence maximale vaut `1 / CounterDebounce`
  (`xsns_01_counter.ino`, `debounce_time > Settings->pulse_counter_debounce * 1000`). Avec 1 ms :
  **1 000 Hz par voie**. Avec 2 ms : 500 Hz.

**Limite retenue : 1 000 Hz par voie** (l'hypothèse pessimiste, arrondie, et compatible avec un
anti-rebond de 1 ms). Pour que l'écran prenne plus de 10 % de retard, il faudrait environ 1 500 Hz
sur chacune des 6 voies en même temps, dans l'hypothèse pessimiste.

### Ce que cela veut dire pour le choix des capteurs

Fréquence = K × débit. Un circuit de radiateur dépasse rarement 5 L/min :

| Capteur | K | À 5 L/min | Marge sous 1 000 Hz |
|---|---|---|---|
| YF-S201 | ≈ 7,5 Hz par L/min | ≈ 38 Hz | × 26 |
| Capteur fin | ≈ 100 Hz par L/min | ≈ 500 Hz | × 2 |

L'autre bout compte autant : la **précision aux petits débits**. Sur une fenêtre de 10 s, il faut au moins
50 impulsions pour une erreur de comptage de 2 %, donc **≥ 5 Hz au plus petit débit utile**.
Avec un YF-S201 à 0,5 L/min : 3,75 Hz, donc ≈ 2,7 % d'erreur. C'est acceptable, ou bien allonger la fenêtre.

**Règle de choix** : K tel que `K × débit min ≥ 5 Hz` et `K × débit max ≤ 1 000 Hz`, soit pour 0,5 à 5 L/min :
**10 ≤ K ≤ 200 Hz par L/min**.

### À vérifier sur banc avant d'y croire

- Injecter 6 signaux de fréquence connue (sorties PWM d'un second ESP32 : `PwmFrequency`), et mesurer :
  durée d'une mise à jour de l'écran (`tasmota.millis()` autour du `DisplayText`), impulsions comptées
  contre impulsions envoyées.
- Monter la fréquence par paliers (100, 500, 1 000, 2 000 Hz par voie) jusqu'au premier critère dépassé.

---

## 7. Questions ouvertes (à trancher avant tout plan)

1. **Référence ou type de sortie des 6 débitmètres** : impulsions, tension/courant, ou mécaniques ?
2. **Où doit être l'affichage** : à la nourrice, sur le P4, sur une page web seulement ?

---

## 7 bis. Décisions prises le 2026-11-08 (réponses aux questions du § 7)

| Sujet | Décision | Raison |
|---|---|---|
| Capteur | Débitmètre à effet Hall G1/2, 1-25 L/min, modèle probable **YF-B2** (référence à lire sur l'étiquette) | Fiche : `outils_docs/Electronique/Debitmetre YF-B2/YF-B2_fiche_technique.pdf` |
| Caractéristiques (fiche) | F = 11 × Q (± 3 %), 5-15 V, 15 mA, liquide ≤ 120 °C, électronique 0-80 °C, ≤ 1,75 MPa, **sortie haute > 4,7 V sous 5 V** | 11 Hz à 1 L/min, 275 Hz à 25 L/min : sous la limite de 1 000 Hz |
| Plage | Validée : radiateurs ≥ 1 400 W, PAC air-eau (ΔT ≈ 5 K) → ≈ 1,4 à 1,9 L/min pour le plus petit | Le radiateur ne rend que 500-650 W avec de l'eau à 45-50 °C ; débit imposé par la pompe |
| Variante | **V1 : un seul ESP32-S3** (2 `FlowRateMeter` + 4 compteurs + Berry) | V2 sans objet (impulsions), V3 inutilement complexe |
| Puce | **ESP32-S3**, pas de P4 | Besoin très en dessous du S3 ; Wi-Fi du P4 par coprocesseur C6 (soucis connus) |
| Affichage | **OLED 128×64 SSD1306** + page web ; pas d'affichage sur le P4 | Pilote universel + `SSD1306_128x64_display.ini` ; ≈ 110 ms par trame à 100 kHz |
| Identité | Bureau, « Serveur Débits de PAC », 192.168.0.50, topic `chauffage/pac/debits` | IP absente du dépôt, sans réponse au ping le 2026-11-08 |

Point de vigilance PAC : les 6 turbines ajoutent une perte de charge non chiffrée par la fiche ; relever le débit
de la PAC avant et après la pose (une PAC se met en défaut sous son débit minimal).

---

## 7 ter. Choix du matériel (recherche du 2026-11-08)

### Critère déterminant

Les 6 voies doivent arriver sur des **broches reliées directement à l'ESP32** (interruption à chaque impulsion).
Les cartes « industrielles » qui font passer leurs entrées par un expandeur I2C (PCF8574 sans ligne d'interruption,
cas des KinCony) ne peuvent pas compter. Aucun kit ne fait l'adaptation 5 V → 3,3 V des capteurs.

### Kits comparés

| Kit | Écran | Tactile | Boîtier | Bornier à vis | 6 entrées directes | PSRAM | Prix relevé |
|---|---|---|---|---|---|---|---|
| **A. DevKitC-1 N16R8 + bornier DIN DNDINS3 + OLED SSD1306** (retenu) | OLED 0,96″ 128×64 | Non | ✅ rail DIN (DNDINS3) | ✅ 3,96 mm | ✅ | ✅ 8 Mo | DevKitC ≈ 11 £ ; autres non relevés |
| B. Heltec WiFi Kit 32 V3 | OLED 0,96″ intégré | Non | Non | Non | ✅ probable | Probablement aucune (S3FN8, à vérifier) | ≈ 13 $ à 23 $ |
| C. diymore MINI ESP32-S3-N16R8 + OLED | OLED 0,96″ intégré | Non | Non | Non | ? (brochage non publié) | ✅ | Non relevé |
| D. Seeed XIAO ESP32S3 + carte d'extension | OLED 0,96″ sur l'extension | Non | Non | Non (Grove) | ⚠️ trop peu de broches | ✅ | XIAO ≈ 9,55 € + extension ≈ 17 à 30 € |
| E. KinCony KC868-A16v3 | SSD1306 intégré | Non | ✅ rail DIN | ✅ | ⚠️ 16 entrées par expandeur I2C ; 6 broches directes détournables (GPIO 47, 48, 38, 39, 40, 41, d'après le forum) | ? | 55 à 75 $ (revendeur tiers) |
| F. M5Stack CoreS3 | LCD 2″ (pas OLED) | ✅ | ✅ | Non (Grove) | ❌ ≈ 4 broches | ✅ | ≈ 57,60 £ HT |
| G. LilyGO T-Display-S3 | LCD 1,9″ (pas OLED) | En option | Coque ≈ 7 € (pas pour la version tactile) | Non | ✅ probable | ✅ | 15 à 23 $ |

### Matériel retenu (option A)

| Pièce | Où l'acheter | Remarque |
|---|---|---|
| ESP32-S3-DevKitC-1 **N16R8** (44 broches) | [amazon.fr, diymore lot de 2](https://www.amazon.fr/diymore-DevKitC-1-dexpansion-d%C3%A9veloppement-connectable/dp/B0FKBLR2KF) · [recherche amazon.fr](https://www.amazon.fr/s?k=ESP32-S3+N16R8+DevKitC-1) · [recherche AliExpress](https://fr.aliexpress.com/w/wholesale-esp32-s3-n16r8-devkitc-1.html) | Même carte que le parc |
| Bornier rail DIN **Eletechsup DNDINS3** (toutes les broches, 3,96 mm, coque 95 × 61 × 35 mm) | [fabricant](https://eletechsup.com/products/dndins3-esp32-s3-din-rail-mounting-expansion-board-all-pinout-3-96-screw-terminal-module-usb-otg-n16r8-n8r8-for-wi-fi-bluetooth-le) · [amazon.com](https://www.amazon.com/eletechsup-ESP32-S3-DevKitC-1-Expansion-Terminals-Bluetooth/dp/B0GCXMCQ1T) · [AliExpress](https://www.aliexpress.com/item/1005008046317499.html) | Vérifier la largeur de la carte S3 (25,4 ou 28 mm) avant commande |
| OLED 0,96″ 128×64 **SSD1306 I2C** (0x3C) | [amazon.fr IZOKEE lot de 3](https://www.amazon.fr/IZOKEE-Affichage-Afficheur-Raspberry-Microcontr%C3%B4leur/dp/B076PDVFQD) · [amazon.fr DollaTek lot de 2](https://www.amazon.fr/DollaTek-SSD1306-embases-Broches-Arduino/dp/B07QJWHVDH) · [recherche AliExpress](https://fr.aliexpress.com/w/wholesale-oled-0.96-ssd1306-i2c.html) | 3,3 à 5 V |
| 6 débitmètres YF-B2 | AliExpress (annonce de l'utilisateur) | En acheter 1 d'abord : banc de charge (plan A6) avant les 5 autres |
| Adaptation 5 V → 3,3 V (6 voies) | Composants courants | Voir ci-dessous |
| Alimentation 5 V rail DIN | — | 6 capteurs × 15 mA + S3 + OLED : < 500 mA |

Les prix Amazon et AliExpress ne sont pas lisibles par une requête automatique : à relever sur les annonces.
Les sites Funduino et OpenELAB refusent aussi les requêtes automatiques (code 429) ; leurs liens n'ont pas pu être vérifiés.

### Proposition d'adaptation du signal (à valider)

La résistance de rappel interne du capteur (vers son 5 V) n'est pas donnée par la fiche : un simple pont diviseur
donnerait un niveau haut qui dépend de cette valeur inconnue. Proposition indépendante de cette valeur, par voie :

```
capteur (fil jaune) ──|◄── GPIO        diode Schottky BAT85 (cathode côté capteur)
                            │
                  4,7 kΩ ── 3,3 V      rappel vers le 3,3 V de l'ESP32
                            │
                     1 nF ── GND       filtre des parasites (τ ≈ 5 µs, sans effet à 275 Hz)
```

Capteur à l'état haut (5 V) : la diode est bloquée, la broche voit 3,3 V par la résistance. Capteur à l'état bas
(≈ 0,2 V) : la diode conduit, la broche voit ≈ 0,5 V (< 0,8 V, seuil bas de l'ESP32), courant ≈ 0,6 mA (le capteur
en accepte 10). Alternative déjà documentée dans le dépôt : convertisseur de niveau à 2N7000
(`outils_docs/Electronique/convertisseur tension 2N7000.jpg`).

### Proposition de brochage (à valider)

Broches choisies hors démarrage (0, 3, 45, 46), hors PSRAM octale (35, 36, 37), hors USB (19, 20) et console (43, 44),
hors LED RGB de la DevKitC (48). I2C sur les broches du parc (cuve, cave : SCL 8, SDA 9).

| Fonction | GPIO |
|---|---|
| Débit 1 et 2 (`FlowRateMeter` 1-2) | 4, 5 |
| Débit 3 à 6 (`Counter` 1-4) | 6, 7, 15, 16 |
| I2C SCL / SDA (OLED) | 8 / 9 |

---

## 8. Ce qui n'est pas vérifié

- Le calcul du débit sur les compteurs est à écrire en Berry et à valider sur banc puis sur carte.
- La coexistence de 2 `FlowRateMeter` et 4 compteurs sur un S3 vient de la lecture du code, pas d'un essai.
- La résolution réelle aux faibles débits dépend du facteur K des capteurs choisis.
