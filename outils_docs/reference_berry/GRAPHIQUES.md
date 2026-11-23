# Graphiques des mesures (S3, P4)

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Les graphiques des mesures (cartes S3/P4)

Les cartes ESP32-S3 et P4 tiennent un historique de leurs mesures (`data/fs/historiqueFonctions.be`) :
24 h en RAM au pas de 5 min, et min/moy/max horaires en flash, un fichier par mois. Le bouton
**Graphiques** de la page d'accueil ouvre `/graphiques`, qui les trace avec ECharts, en temps réel. Les ESP32 classiques
n'ont ni l'historique ni la page (fichiers exclus de leur LittleFS) : leurs courbes sont dans Grafana.

- **Séries découvertes** (2026-10-18) : la carte trace **ses** capteurs sans liste écrite à la main. Sont
  retenues toutes les valeurs numériques de son JSON SENSOR (celui de `tele/<topic>/SENSOR`) : capteurs
  réels (DS18B20, ADS1115, AM2301…) comme virtuels (valeurs reçues par ModBus, valeurs calculées par un
  module comme `sensorsCuve`). **Jamais** les relais, entrées, boutons et volets (`POWER*`, `Switch*`,
  `Button*`, `Shutter*`, ON/OFF), ni les mesures internes de la carte (température de l'ESP32, RSSI,
  mémoire), ni un compteur dont le type n'est pas réglé. Découverte 2 min après le démarrage, puis à chaque
  nouvelle heure : un capteur apparu plus tard (esclave ModBus en retard) s'ajoute ; une série déjà
  enregistrée ce mois-ci reste (trou si elle ne mesure plus). Une série s'appelle par son chemin dans le
  JSON, ex. `DS18B20.Temperature`. Choix et règles : `data/fs/historiqueSeries.be`.
- **Graphiques par défaut** : « Mesures », plus un graphique par groupe déclaré dans `graphiques.json` (ex.
  « Cuve » pour la hauteur, le volume et le remplissage, sur la cuve et le P4).
- **Composer ses graphiques** (2026-10-19) : bouton **Modifier les graphiques**. Ajouter, renommer, supprimer,
  monter ou descendre un graphique ; choisir son type (courbes, barres, escalier, aires), sa période et ses
  séries, et au besoin un type par série (graphique **combiné** : barres pour un compteur, courbe pour une
  température). « Toutes les séries placées dans aucun autre graphique » reçoit aussi les séries découvertes
  plus tard. **Enregistrer sur la carte** : la composition est écrite dans `/json/graphiques.json` (clé
  `graphiques`), le PC et le téléphone voient donc la même page ; **Rétablir** revient aux graphiques par
  défaut. La carte contrôle ce qu'elle reçoit : 8 graphiques, 12 séries chacun, titre de 1 à 60 caractères.
  Une série enregistrée qui n'existe plus est signalée « absente » sous son graphique.
- **Périodes** : chaque graphique a la sienne, dans son en-tête : « 24 dernières heures », « Mois en cours »,
  puis un mois par entrée (moyenne horaire ; bande min-max pour les courbes et les aires). Un mois marqué
  « ancienne liste de séries » date d'avant un changement des séries (fichier mis de côté en `-a`, `-b`…).
  Deux graphiques sur la même période ne coûtent qu'une lecture à la carte.
- **Temps réel** (vue 24 h et mois en cours) : la page lit les valeurs actuelles de la carte
  (`/histo?p=direct`) et les ajoute au bout des courbes ; l'axe des temps va jusqu'à l'heure actuelle. Cadence
  choisie dans la liste **Direct** de la page : arrêt, 2, 5, 10, 30 s ou 1 min (10 s par défaut, ou la clé
  `direct` de `graphiques.json`) ; le choix est gardé par le navigateur. L'historique affiché est relu
  toutes les `rafraichissement` secondes (60 par défaut ; mois en cours : 15 min), et rien n'est lu quand
  l'onglet est caché. La carte relit ses capteurs au plus toutes les 4 s, quel que soit le nombre de pages
  ouvertes.
- **Légende** : un clic masque ou affiche une série, choix gardé par le navigateur. Un axe Y par unité,
  ajusté au minimum et au maximum des valeurs tracées (sans descendre sous zéro si toutes sont
  positives) ; molette ou pincement pour zoomer sur le temps. Un trou dans une courbe = pas de mesure
  (carte arrêtée, esclave muet, capteur absent).
- **Historique long** : le bouton « Historique long (Grafana) » ouvre le tableau du Pi.
- ECharts 6 est servi **par la carte**, compressé (`/sd/js/echarts.min.js.gz`, 368 Ko), sans Internet :
  le navigateur le décompresse, le garde dans son `localStorage` et ne le redemande qu'à un changement de
  version. Il faut un navigateur récent (`DecompressionStream` : Chrome 80, Firefox 113, Safari 16.4).

### Dans `_persist.json` : ce que la relève de chaque minute utilise

Le persist est chargé **entier et en permanence** en RAM : il ne porte que les réglages de la relève.

```json
"diverses": {
    "historique": {
        "activation": "ON", "pasMinutes": 5, "dureeHeures": 24, "moisConserves": 24, "seriesMax": 12,
        "exclues": ["sensorsCuve.valeursAnalogiques"],
        "ajouts": ["ESP32.Temperature", "@rssi"],
        "compteurs": {
            "COUNTER.C1": {"type": "energie", "impulsionsParUnite": 1000, "unite": "kWh"},
            "COUNTER.C2": {"type": "debit", "impulsionsParUnite": 450, "unite": "L/min"}
        },
        "grafana": "http://<ip>:3000/d/historique-cuve?var-appareil=%topic%"
    }
}
```

- `exclues` : chemins (ou débuts de chemin, par segment entier) à ne pas tracer.
- `ajouts` : séries que le filtre écarte mais que l'on veut quand même (internes : `ESP32.Temperature`,
  `@rssi`, `@heap` ; position d'un volet `Shutter1.Position`). `@power<n>` (relais) est refusé.
- `compteurs` : un compteur n'est tracé qu'une fois réglé. `energie` = cumul ÷ `impulsionsParUnite` ;
  `debit` = impulsions depuis la relève précédente ÷ `impulsionsParUnite`, **par minute** (rien à la
  première relève ni après une remise à zéro du compteur).
- `grafana` : `%topic%` est remplacé par le topic de la carte ; sans clé, pas de bouton. Elle reste dans le
  persist car le bouton des ESP32 classiques (ci-dessous) la lit à cet endroit.

### Dans `graphiques.json` : ce que seule la page utilise

`data/<lieu>/<carte>/graphiques.json`, rangé dans `/json/` au démarrage et lu à l'ouverture de la page
seulement (rien en RAM le reste du temps). Facultatif.

```json
{
    "affichage": {
        "sensorsCuve.niveauCuve.tauxRemplissage": {"libelle": "Remplissage", "unite": "%", "facteur": 100},
        "DS18B20.Temperature": {"libelle": "Température de l'eau", "unite": "°C"}
    },
    "groupes": {"Cuve": ["sensorsCuve.niveauCuve"]},
    "rafraichissement": 60,
    "direct": 10,
    "graphiques": [{"titre": "Cuve", "periode": "jour", "type": "courbe",
                    "series": [{"chemin": "sensorsCuve.niveauCuve.volume", "type": "barres"},
                               {"chemin": "sensorsCuve.niveauCuve.hauteurEau"}]},
                   {"titre": "Mesures", "periode": "mois", "type": "aire", "series": "autres"}]
}
```

Sans `affichage`, libellé = chemin de la série (esclave ModBus remplacé par son nom du persist) et unité
devinée de sa dernière clé (`Temperature` → °C, `Humidity` → %, `Pressure` → hPa…) ou de son nom
(`hauteur` → cm, `volume` → L, `taux` → %) ; une entrée analogique relayée par ModBus
(`TasmotaSlaveModBus.<esclave>.ANALOG.A<n>`) est en mV, l'`ANALOG` natif de la carte (valeur brute de l'ADC)
reste sans unité ; l'unité d'un compteur réglé vient de `compteurs`. `facteur`
multiplie la valeur affichée (0-1 → %). `groupes` : titre → débuts de chemin ; chaque groupe a son
graphique, les autres séries vont dans « Mesures ». `rafraichissement` : relecture de l'historique affiché, en
secondes (10 au minimum). `direct` : cadence par défaut du temps réel (0 = arrêt, 2, 5, 10, 30 ou 60 s).
`graphiques` : la composition écrite par le bouton « Enregistrer » de la page (inutile de l'écrire à la main) ;
`periode` = `jour`, `mois` (mois en cours) ou `AAAA-MM` ; sans cette clé, graphiques par défaut.

**Carte sans historique local** (ESP32 classique, ou historique à `OFF`) : la même clé `grafana`, dans un bloc
`"historique": {"grafana": "…"}`, ajoute à la page d'accueil un bouton **Historique (Grafana)** qui ouvre
directement le tableau (`controleWeb.boutonGrafana`, commun à toutes les cartes ; module solidifié : il faut
le firmware recompilé). Il n'apparaît pas là où l'historique est actif, le bouton « Graphiques » y menant
déjà. Clé laissée vide (`"grafana": ""`, donc pas de bouton) sur la cave et le bureau (décidé le 2026-10-18) : le tableau `historique-cuve` n'a que
des panneaux de cuve, leurs courbes y seraient vides.

### Vérifier

- `/histo?p=liste`, `/histo?p=jour`, `/histo?p=direct`, `/histo?p=mois&m=AAAA-MM` donnent le JSON brut. En `curl`, ajouter
  `-H "Referer: http://<ip>/"` : sans lui, Tasmota coupe la connexion sans réponse (`curl: (52)`).
- Banc hors carte : `python outils_docs/scripts_python/berry/banc_graphiques.py` (code de sortie 0 = vert ;
  inclut `banc_historique.be` : découverte des séries, compteurs, redécouverte horaire).
- Séries retenues par une carte : log `HISTORIQUE: Series enregistrees : [...]` (puis `Nouvelles series`),
  ou `/histo?p=liste`.
- Sur le P4, les mesures de la cuve sont écartées de l'historique tant que l'esclave ne les donne pas
  pour valides (`controleGarage.filtreHistorique`) : une cuve sans capteur donne des trous, pas des zéros.

<hr></hr>
