# Inclinaison d'un volet ou d'une trappe (MPU6050)

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Inclinaison d'un volet ou d'une trappe (MPU6050)

Un MPU6050 fixé sur une trappe (ou un volet) qui pivote autour d'une charnière horizontale donne son angle réel :
l'accéléromètre mesure la gravité, `atan2` en tire l'angle. Il sert de **capteur de position** du volet, sous le
nom `"Inclinaison"`, comme un fin de course : au franchissement d'une butée, le Shutter de Tasmota est recalé
(`vrFonctions.changementEtatCapteur`). Gain principal : la position est connue dès le démarrage. Une trappe qui
coulisse à plat, sans changer d'inclinaison, ne peut pas être suivie ainsi.

**Ce n'est pas une sécurité** : la lecture se fait en Berry, toutes les 250 ms au mieux. Les fins de course
physiques qui coupent le moteur restent indispensables.

### Le capteur

- Bus I2C de la carte (SDA/SCL déclarés dans le gabarit), adresse `0x68` (`104`), ou `0x69` (`105`) si AD0 est au
  +3,3 V. Fil court et souple : l'I2C supporte mal plus d'un mètre, et un câble qui se plie à chaque manœuvre casse.
- Lu en Berry (`tasmota.wire_scan`, registres `0x6B` et `0x3B`) pour la course du volet. Le pilote C de Tasmota
  (`USE_MPU6050`) est compilé sur les deux greniers seulement (leurs sections de `user_config_override.h` ; les autres
  envs ignorent sa bibliothèque par `lib_inutiles.sans_mpu6050`) : il ne lit le capteur qu'une fois par TelePeriod,
  pour le JSON SENSOR, et la lecture rapide reste celle de `vrFonctions.be`. Ne pas le compiler sur une carte qui
  n'a pas de capteur.
- Sans `"activation": "ON"`, rien n'est lu : ni bus, ni minuterie, ni ligne sur la page. Tous les persists du
  dépôt portent le bloc, désactivé.

### Dans `_persist.json`

Sous `drivers.voletRoulants.environnement.VRs.<VR>.capteursPosition` :

```json
"capteurOuvert": "Inclinaison",
"capteurFerme": "Switch2",
"inclinaison": {
    "activation": "ON",
    "adresse": 104,
    "axes": "YZ",
    "angleOuvert": 85.0,
    "angleFerme": 3.0,
    "marge": 3,
    "blocage": 5,
    "blocageDegres": 1,
    "sensInverse": 3,
    "surveillance": 0,
    "positionReelle": "OFF"
}
```

- `capteurOuvert` / `capteurFerme` : `"Inclinaison"` pour que l'angle recale cette butée. Les deux types se
  mélangent : un fin de course physique d'un côté, l'inclinaison de l'autre.
- `axes` : les 2 axes de l'accéléromètre dans le plan de rotation (l'angle vaut `atan2` du 1er sur le 2e).
- `angleOuvert` / `angleFerme` : les butées, en degrés. `angleOuvert` peut être plus petit que `angleFerme`
  (selon le montage).
- `marge` : hystérésis en degrés pour QUITTER une butée (pas de rebond au seuil).
- `blocage` / `blocageDegres` : détection de blocage (ci-dessous). `blocage` à 0 la désactive.
- `sensInverse` : seuil en degrés de la détection de sens inverse (ci-dessous) ; 0 la désactive.
- `surveillance` : période en secondes de la lecture à l'arrêt (0 = aucune).
- `positionReelle` : `"ON"` pour que l'angle donne la position en % à Tasmota, volet arrêté.
- `filtre` (facultatif, 6 par défaut) : filtre passe-bas du MPU6050 (registre `0x1A`, 0 à 6 ; 6 = ~5 Hz) contre
  les vibrations du moteur. Écrit une fois, au réveil du capteur.

### Détection de blocage

Pendant la course, si l'angle bouge de moins de `blocageDegres` (1° par défaut) pendant `blocage` secondes
(5 par défaut) alors que le moteur tourne, la carte envoie `ShutterStop<id>` et logue une erreur
`VR_INCLINAISON: Volet 1 bloque a 40.0 degres (entre) depuis 5 s : moteur arrete !`. Cas couverts : trappe
coincée, moteur qui force contre une butée parce que la position estimée était fausse. Le délai repart à chaque
mouvement et à chaque nouvelle course : un départ lent ne déclenche rien tant qu'il dure moins de `blocage`
secondes. Régler `blocage` au-dessus du temps de démarrage réel du moteur.
Angle figé sur la butée vers laquelle va le volet, quand cette butée n'est pas désignée `"Inclinaison"` : c'est une
arrivée, pas un blocage. Le moteur qui force est arrêté de la même façon, sans erreur ni alerte.

Un blocage s'affiche aussi sur la page d'accueil (« BLOQUÉ » sur la ligne du volet) et part en MQTT, **retenu**, sur
`tele/<topic>/INCLINAISON<id>` : `{"Volet": 1, "Bloque": true, "Angle": 40.0, "Etat": "entre"}`. La course suivante
efface l'alerte (`"Bloque": false` publié). Rien n'est publié en dehors de ces deux changements.

### Sens inverse

Pendant la course, si l'angle s'éloigne de `sensInverse` degrés (3 par défaut) de son angle de départ dans le sens
OPPOSÉ à celui demandé, la carte arrête le moteur (`ShutterStop<id>`) et logue une erreur : moteur câblé à l'envers,
ou `ShutterInvert` faux. L'alerte est la même que pour un blocage (« BLOQUÉ (sens inverse) » sur la page,
`"Cause": "sens inverse"` en MQTT ; `"Cause": "blocage"` pour un blocage).

### Durées de course

Une course partie d'une butée et arrivée à l'autre est chronométrée. `ReglageVolets Inclinaison <id>` la donne avec la
valeur proposée, en secondes entières arrondies au-dessus : `tempsMontee` pour l'ouverture, `tempsDescente` pour la
fermeture. Rien n'est appliqué seul : `configVRByJson` réécrit `ShutterOpenDuration` / `ShutterCloseDuration` depuis
ces clés du persist à chaque démarrage, c'est donc le persist qu'il faut corriger. La mesure va du départ de la course
au franchissement de l'angle de butée : elle ne compte ni le temps de démarrage du moteur avant la règle `Direction`,
ni la fin de course mécanique au-delà de l'angle. Une course que Tasmota coupe avant la butée (durée trop courte) ne
donne pas de mesure : allonger d'abord la durée, puis mesurer.

### Surveillance à l'arrêt

Avec `surveillance` > 0 (30 s par exemple), le volet arrêté est relu toutes les `surveillance` secondes : la page
d'accueil suit une trappe bougée à la main, une ligne `info` signale un mouvement hors manœuvre (au moins `marge`
degrés), et une butée atteinte ainsi recale la position. Aucune lecture pendant une course (le suivi de 250 ms s'en
charge). La position réelle n'y est corrigée qu'après un vrai mouvement (au moins `marge` degrés) : un moteur qui
vient de démarrer, avant que la règle `Direction` n'arrive, n'a pas encore bougé. Capteur muet : une erreur par
lecture, et la période double à chaque échec (jusqu'à 128 fois), puis revient à la normale dès qu'il répond.

### Position réelle

Avec `positionReelle` à `"ON"`, l'angle est converti en % d'ouverture entre `angleFerme` et `angleOuvert`, et donné à
Tasmota par `ShutterSetPosition<id>` : à l'arrêt d'une course, au démarrage et à chaque lecture de surveillance. Avec
`ShutterInvert 1` (posé par `configVRByJson`), la position Tasmota vaut 100 − % d'ouverture. **Jamais pendant une
course** : `ShutterSetPosition` remet la direction du Shutter à 0 sans couper le moteur. Un écart de moins de 2 % ne
renvoie rien, pour ne pas réécrire les réglages à chaque lecture ; après une course, la position est toujours renvoyée
(l'estimation au temps de Tasmota a pu dériver).

Les commandes `ShutterSetOpen/Close/Position` envoyées moins de `ShutterMotorStop` (500 ms par défaut) + 100 ms après
un arrêt partent en différé : dans ce délai, Tasmota attend la fin de l'arrêt moteur en bouclant sur `loop()`, ce
qu'il ne faut pas provoquer depuis Berry. Une commande différée est abandonnée si une course a repris entre-temps.

### Arrêt en butée

Un volet en course vers une butée désignée `"Inclinaison"` (`capteurOuvert` en ouverture, `capteurFerme` en
fermeture) est arrêté dès qu'il l'atteint : `ShutterStop<id>`, puis recalage de la position. Il l'est aussi aussitôt
s'il y est déjà et qu'on le commande encore vers elle. L'arrêt passe AVANT le recalage : `ShutterStop` coupe le moteur
sur-le-champ, alors que `ShutterSetOpen/Close` seul ne le coupe pas (`xdrv_27_esp32_shutter.ino`). Une butée tenue
par un fin de course physique (`SwitchN`) n'est pas arrêtée par l'inclinaison.

### Apprentissage des butées

Plutôt que de régler `axes` et les angles à la main :

1. amener le volet en butée **ouverte** (commande habituelle), puis `ReglageVolets Apprentissage 1 ouvert` ;
2. amener le volet en butée **fermée**, puis `ReglageVolets Apprentissage 1 ferme`.

Les 2 butées relevées, la carte choisit les axes (l'axe de rotation est celui qui varie le moins) et l'ordre qui
évite la coupure ±180° de l'angle, écrit `axes`, `angleOuvert` et `angleFerme` dans le persist et l'enregistre.
L'apprentissage **ne commande jamais le moteur**. Il est refusé, sans rien écrire, si les butées sont à moins de
10° l'une de l'autre, ou si l'arc traverse la coupure dans les deux ordres (tourner le capteur d'un quart de tour).
Un redémarrage entre les 2 temps efface la 1re butée : recommencer. L'apprentissage marche aussi avec l'inclinaison
désactivée, ce qui permet de régler avant d'activer.

`ReglageVolets Inclinaison 1` affiche l'angle mesuré et l'état qu'il donne, sans recaler le volet.

### Sur la page d'accueil

Une ligne `<nom du volet> : inclinaison  85.3 ° (ouvert)` par volet dont l'inclinaison est active. Elle montre le
**dernier angle relevé** (au démarrage, pendant la course, à l'arrêt), sans relire le bus à chaque rafraîchissement :
une trappe bougée à la main n'y apparaît qu'à la prochaine manœuvre. « capteur muet » après une panne du capteur.

### Banc

`python outils_docs/scripts_python/berry/banc_inclinaison.py` : le vrai `vrFonctions.be` sous `berry.exe`, avec un
faux bus I2C et une horloge simulée (garde d'activation, angles, hystérésis, recalage, suivi pendant la course, pannes,
apprentissage, blocage, ligne web). Code de sortie 0 = vert. Ne teste ni le vrai bus, ni le vrai Shutter, ni le capteur physique.
