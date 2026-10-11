# ADS1115 — câblage des 4 voies et choix des résistances

Note de référence (2026-10-11). Le code qui applique ces règles est `data/fs/i2c_ads1115.be`
(méthodes `montage()`, `rappel()`, `mesureValide()`) ; les réglages passent par `ReglageAna`
(module cuve, `cuveFonctions.reglageVoies`).

## 1. La règle qui prime sur tout le reste

**Une entrée de l'ADS1115 ne doit jamais dépasser sa tension d'alimentation VDD (+0,3 V maxi).**

La plage `Sensor12` (±6,144 V, ±4,096 V…) règle seulement le **calibre de mesure** : elle
n'autorise **pas** à appliquer 6 V sur un ADS1115 alimenté en 3,3 V. Au-delà de VDD + 0,3 V,
les diodes de protection internes conduisent : la mesure est fausse, et la puce peut être détruite
si le courant injecté dépasse 10 mA.

> ⚠️ L'ancien commentaire de `controleCuve.be` (« pont diviseur 10 V vers 6 V, plage 6,144 V ») est
> **dangereux** si l'ADS1115 est alimenté en 3,3 V. C'est le pont de cette note qu'il faut poser.

Le code vise donc une **tension cible** à pleine échelle, avec une marge sous VDD :

| VDD de l'ADS1115 | Tension cible à l'entrée | Calibre `Sensor12` |
|---|---|---|
| 3,3 V | **3,0 V** | `S1` (±4,096 V) |
| 5 V | **4,0 V** | `S1` (±4,096 V) |

À régler : `ReglageAna alimentation 3.3` (ou `5`). La valeur est enregistrée dans
`drivers.I2C.environnement.ADS1115.alimentation_V`.

**L'ADS1115 de la cuve est alimenté en 3,3 V** (`"alimentation_V": 3.3` dans son persist). Ce
choix date du 2026-10-11, après un passage par le 5 V. C'est le montage le plus répandu avec un
ESP32 : SDA et SCL se branchent en direct, sans convertisseur. Avec un pont diviseur, le 5 V
n'apportait presque rien.

Il y a deux schémas complets, en `.svg` (source) et en `.png` :
- `montages_ADS1115_3V3` : **la cuve**, liaison directe à l'ESP32 ;
- `montages_ADS1115_5V` : avec le convertisseur de niveau I²C.

**Si un ADS1115 est un jour alimenté en 5 V, un convertisseur de niveau I²C est obligatoire
entre l'ESP32 et l'ADS1115**, pour deux raisons :
- les modules ADS1115 ont des résistances de rappel I²C (10 kΩ) reliées à **leur** VDD : SDA et
  SCL montent donc à 5 V, ce que les GPIO de l'ESP32 (3,3 V) ne tolèrent pas ;
- l'ADS1115 reconnaît un « 1 » logique à partir de 0,7 × VDD, soit 3,5 V : le 3,3 V de l'ESP32
  est hors spécification.

Il faut un module à 2 MOSFET (BSS138 ou 2N7000) : côté LV au 3V3 de l'ESP32, côté HV au 5 V de
l'ADS1115, GND commun. Voir `../Bi-Directional-Logic-Level_HookupGuide.pdf` et
`../convertisseur tension 2N7000.jpg`. Sans ce module, le bus peut fonctionner, tomber en panne par
intermittence, ou l'ADS1115 peut **ne pas être détecté du tout**.

En 3,3 V, ce problème disparaît (et les résistances changent, voir les tableaux).

## 2. Mesurer une tension (A0, A1) : le pont diviseur

```
 signal capteur ──[ R1 ]──┬──[ 1 kΩ ]── A0   (la 1 kΩ est optionnelle, voir § 4)
                          │
                        [ R2 ] 10 kΩ
                          │
 GND capteur ─────────────┴──────────── GND ADS1115
```

`V_entrée = V_capteur × R2 / (R1 + R2)`

### Comment choisir R1 et R2

1. **R2 est fixée à 10 kΩ.** Cette valeur est assez basse devant l'impédance d'entrée de l'ADS1115
   (plusieurs MΩ) : l'erreur reste sous 0,2 %. Elle est aussi assez haute pour ne pas charger le
   capteur. Une sortie 0-10 V industrielle accepte en général une charge d'au moins 2 à 10 kΩ, et
   le pont en fait 34 kΩ.
2. **R1 = R2 × (V_max / V_cible − 1).** Exemple : 0-10 V à 3,3 V, soit
   10 kΩ × (10 / 3,0 − 1) = 23,3 kΩ.
3. **Arrondir R1 à la valeur normalisée E24 supérieure** (ici 24 kΩ). En arrondissant vers le haut,
   la pleine échelle tombe un peu **sous** la cible, jamais au-dessus. On perd un peu de résolution
   (2,94 V au lieu de 3,0 V, soit 2 %), mais on ne dépasse jamais VDD.
4. **Si V_max ≤ V_cible, pas de pont** : le capteur se branche en direct, par exemple un 0-3 V sur
   un ADS1115 alimenté en 5 V.
5. Choisir des résistances **à couche métallique à 1 %**. La puissance est négligeable :
   24 V dans 85 kΩ donne 7 mW, une 1/4 W suffit largement.

### Valeurs calculées (celles que rappelle `ReglageAna cablage`)

| Plage | VDD 3,3 V : R1 / R2 → pleine échelle | VDD 5 V : R1 / R2 → pleine échelle |
|---|---|---|
| 0-5 V | 6,8 kΩ / 10 kΩ → 2,98 V | 2,7 kΩ / 10 kΩ → 3,94 V |
| 0-10 V | 24 kΩ / 10 kΩ → 2,94 V | 15 kΩ / 10 kΩ → 4,00 V |
| 0-24 V | 75 kΩ / 10 kΩ → 2,82 V | 51 kΩ / 10 kΩ → 3,93 V |

## 3. Mesurer un courant 0-20 mA / 4-20 mA (A2, A3) : le shunt

Le capteur fait circuler un courant dans la boucle. Une résistance de shunt le convertit en
tension : `V = I × R_shunt`.

```
 + alim boucle (12-24 V) ───► (+) capteur 2 fils (−) ──┬──[ 1 kΩ ]── A2
                                                        │
                                                    [ R_shunt ]
                                                        │
 − alim boucle ─────────────────────────────────────────┴─────────── GND ADS1115
```

**Le − de l'alimentation de boucle doit être relié au GND de l'ADS1115**, sinon la mesure flotte.
Un capteur 3 ou 4 fils a sa propre alimentation : sa sortie courant va au shunt de la même façon,
et son 0 V va au GND de l'ADS1115.

### Comment choisir le shunt

1. **R_shunt = V_cible / I_max.** Exemple à 3,3 V : 3,0 V / 20 mA = 150 Ω.
   Exemple à 5 V : 4,0 V / 20 mA = 200 Ω.
2. **Arrondir à la valeur E24 inférieure.** Ici, les valeurs tombent juste.
3. **Puissance** : 20 mA² × 150 Ω = 60 mW. Une 1/4 W à 1 % (ou 0,1 % pour la précision) suffit.
4. **Tension de boucle** : l'alimentation doit couvrir la tension minimale du capteur (souvent
   8 à 12 V, voir sa fiche) **plus** les 3 V du shunt. En 24 V, aucun souci. En 12 V, c'est juste.

| Plage | VDD 3,3 V | VDD 5 V |
|---|---|---|
| 0-20 mA / 4-20 mA | 150 Ω → 3,00 V | 200 Ω → 4,00 V |

## 4. La résistance série de 1 kΩ (recommandée)

Un capteur courant en défaut peut pousser 25 mA, et plus encore si un câble touche le + de la boucle.
À 3,3 V, 25 mA dans 150 Ω font 3,75 V, au-dessus de VDD + 0,3 V = 3,6 V. À 5 V, 25 mA dans 200 Ω
font 5,0 V : c'est juste sous la limite de 5,3 V, sans marge. Une résistance de **1 kΩ entre le
point de mesure et l'entrée A2/A3** ramène ce défaut à moins de 1 mA injecté dans les diodes de
protection.

Elle ne couvre pas un court-circuit franc du 24 V sur le shunt. Le shunt tirerait alors 120 mA
(2,9 W) et brûlerait, et 1 kΩ laisserait encore 19 mA dans l'entrée, au-dessus de la limite de
10 mA. Contre ce cas, il faut une alimentation de boucle limitée en courant, ou passer la
résistance série à 4,7 kΩ (moins de 4 mA injectés, erreur de mesure sous 0,2 %). Elle est sans effet sur la
mesure : 1 kΩ devant plusieurs MΩ donne moins de 0,02 %.

Côté pont diviseur, R1 joue déjà ce rôle. Même un 24 V branché par erreur sur une voie prévue pour
0-10 V n'injecte que (24 − 3,6) / 24 kΩ ≈ 0,85 mA, ce qui n'est pas destructeur.

Un condensateur de 100 nF entre l'entrée et GND, optionnel, filtre les parasites de longues
lignes.

## 5. Détecter un capteur débranché ou un ADS1115 perdu

Ce que fait `mesureValide()` :

| Situation | Ce que voit le code | Détection |
|---|---|---|
| ADS1115 absent **au démarrage** | pas de clé `ADS1115` dans le message SENSOR | aucune mesure → erreur de fraîcheur (ModBus, voyant rouge) |
| ADS1115 perdu **après** le démarrage | une lecture I²C ratée rend 0 sans erreur (`support_a_i2c.ino:123`) | **les 4 voies exactement à 0** → `I2C_ADS1115_MUET` |
| Capteur 4-20 mA débranché ou boucle coupée | moins de 3,6 mA (le 4 mA du « zéro vivant » a disparu) | automatique en plage `4-20mA` |
| Capteur tension débranché | R2 tire l'entrée à 0 V | **seulement** si `seuilMin` est réglé |

### Pourquoi pas une résistance de tirage pour détecter un fil coupé ?

Je l'avais suggéré, mais c'était une fausse bonne idée **avec un pont diviseur**. Une résistance de
tirage vers VDD assez faible pour se voir quand le fil est coupé fausse la mesure en permanence.
Une résistance assez forte pour ne pas fausser la mesure (1 MΩ) ne fait monter l'entrée que de
quelques dizaines de mV quand le fil est coupé, ce qui ne se distingue pas d'un vrai 0.

Les bonnes solutions :
- **Préférer un capteur 4-20 mA** (ou 2-10 V) : le zéro vivant rend la coupure détectable.
- Si le capteur ne descend jamais sous un certain niveau en fonctionnement normal, régler
  **`seuilMin`** juste en dessous, avec une valeur en mV mesurée **à l'entrée** de l'ADS1115,
  donc après le pont. Exemple : `ReglageAna seuilMin A0 50`.
- Surveiller **l'alimentation de la sonde** sur une voie libre, à travers un pont diviseur.

## 6. Les commandes

| Commande | Effet |
|---|---|
| `ReglageAna cablage` | Journalise et renvoie le montage des 4 voies (également au démarrage) |
| `ReglageAna voie A0 tension 0-10V` | A0, A1 : `0-5V`, `0-10V`, `0-24V` |
| `ReglageAna voie A2 courant 4-20mA` | A2, A3 : `0-20mA`, `4-20mA` |
| `ReglageAna seuilMin A0 50` | Erreur sous 50 mV à l'entrée ; `0` = désactivé |
| `ReglageAna alimentation 3.3` | VDD de l'ADS1115 : change les résistances conseillées |
| `ReglageAna aide <sujet>` | Aide détaillée |

Le persist correspondant se trouve dans `drivers.I2C.environnement.ADS1115` :

```json
"alimentation_V": 3.3,
"voies": {
    "A0": {"mesure": "tension", "plage": "0-10V",  "seuilMin_mV": 0},
    "A1": {"mesure": "tension", "plage": "0-10V",  "seuilMin_mV": 0},
    "A2": {"mesure": "courant", "plage": "0-20mA", "seuilMin_mV": 0},
    "A3": {"mesure": "courant", "plage": "0-20mA", "seuilMin_mV": 0}
}
```

Après le pont, **le code ne remonte pas à la tension du capteur** : la cuve travaille en mV à
l'entrée, et son étalonnage `valeurMin`/`valeurMax` absorbe le rapport du pont. Si le pont change,
il faut **refaire l'étalonnage**.
