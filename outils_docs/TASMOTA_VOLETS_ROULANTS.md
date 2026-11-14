# Volets roulants Tasmota : traduction française et vérification dans ce dépôt

- Source : https://tasmota.github.io/docs/Blinds-and-Shutters/ (page « Shutters and Blinds »), complétée par la table « Shutters » de https://tasmota.github.io/docs/Commands/ (la page dédiée `Blinds-Shutters-Commands` et le source Markdown sur `raw.githubusercontent.com` ont répondu 404 le jour de la consultation).
- Date de consultation : 2026-11-14.
- Licence : le projet Tasmota est sous GPL-3.0 ; cette traduction est une adaptation de sa documentation, elle suit la même licence.
- Traduit : fonctionnement, modes, commandes, étalonnage, boutons, règles, moteurs à impulsions. Résumés en une ligne : servos, moteurs pas à pas, lamelles orientables. Laissés de côté : schémas de câblage, nomenclatures, modèle Sonoff Dual R2, exemple Jarolift.

## Ce qui est vérifié dans le firmware de ce dépôt

Les cartes ESP32 de ce fork (S3, P4) compilent `tasmota/tasmota_xdrv_driver/xdrv_27_esp32_shutter.ino` (bloc `#ifdef ESP32` + `USE_SHUTTER`, défini dans `tasmota/my_user_config.h`). `xdrv_27_shutter.ino` ne sert qu'aux ESP8266. Écarts constatés entre la documentation ci-dessous et ce code :

1. **`USE_SHUTTER_ESP32` n'existe pas ici.** La doc annonce une option de compilation pour le nouveau pilote ESP32 ; dans ce dépôt le pilote ESP32 est choisi par `#ifdef ESP32`, rien à activer.
2. **Numérotation des modes.** La page principale dit « cinq modes » et en décrit six ; la table des commandes donne « 1..7 » avec « 6 = autodétection » puis « 7 = autodétection ». Dans le code (`enum Shutterposition_mode`) : 0 = non défini (ancien comportement), 1 = relais haut/bas, 2 = alimentation + sens, 3 = garage, 4 = pas à pas, 5 = servo en position, 6 = servo en vitesse, 7 = autodétection. `ShutterMode` accepte 0 à 8 (`MAX_MODES = 8`, `xdrv_27_esp32_shutter.ino::CmndShutterMode`).
3. **Le mode est UN seul réglage par carte**, pas par volet : `ShutterGlobal.position_mode`, posé par `CmndShutterMode` et relu par `ShutterInit`. Tous les volets d'une carte partagent le même mode. C'est la contrainte la plus lourde pour le portail (voir la dernière section).
4. **Mode 3 (garage).** La page principale décrit deux relais impulsionnels (OFF/DOWN PULSE et OFF/UP PULSE) ; la table des commandes dit « one relay garage mode ». Le code ne pulse que le relais de départ (`ShutterRelay<x>`) et, si le sens demandé est celui du dernier mouvement, envoie deux impulsions de suite (`CmndShutterPosition`, branche `SHT_TIME_GARAGE`). Le relais suivant est seulement réservé dans le masque des relais du volet.
5. **Mode 1 sans Interlock.** La doc parle d'un « état d'erreur ». Le code désactive tous les volets (`TasmotaGlobal.shutters_present = 0`) avec le journal `SHT: ERROR: Shtr%d Relays are not in INTERLOCK`, jusqu'au redémarrage suivant le correctif.
6. **Autodétection (modes 0 et 7).** Sans Interlock sur la paire de relais, l'ancien mode 0 donne le mode 2 ; avec PWM et compteur définis, le mode 4 ; sinon mode 1 (`xdrv_27_esp32_shutter.ino::ShutterInit`).
7. **Raccourcis de `ShutterButton`.** `up` : 100 / 50 / 75 (la doc écrit 74), `down` : 0 / 50 / 25 (la doc écrit 24), `updown` : 100 / 0 / 50, `toggle` : bascule / 50 (`CmndShutterButton`).
8. **`ShutterInvert`.** Le code n'inverse pas les ordres venant de la console série, de la page web et des commandes web ; il inverse ceux des boutons physiques et des règles (`CmndShutterPosition`). La table de la doc ne le dit pas.
9. **Temps de fin de course.** `ShutterEnableEndStopTime<x>` (cité par la page des commandes) n'existe pas dans le pilote ESP32 ; seuls `ShutterOpenEndStopTime<x>` et `ShutterCloseEndStopTime<x>` existent (`kShutterCommands`).
10. **Noms des commandes** (`tasmota/include/i18n.h`, `D_CMND_SHUTTER_*`) : `ShutterOpen`, `Close`, `Toggle`, `ToggleDir`, `Stop`, `Position`, `OpenDuration`, `CloseDuration`, `Relay`, `Mode`, `PWMRange`, `SetHalfway`, `SetClose`, `SetOpen`, `SetPosition`, `Invert`, `Calibration`, `MotorDelay`, `Frequency`, `Button`, `Lock`, `OpenEndStopTime`, `CloseEndStopTime`, `InvertWebButtons`, `StopOpen`, `StopClose`, `StopToggle`, `StopToggleDir`, `StopPosition`, `Change`, `TiltConfig`, `Tilt`, `TiltChange`, `MotorStop`, `Setup`, `StopRelay` (tous préfixés `Shutter`).
11. **Toggle et ToggleDir** (`ShutterToggle`) : `Toggle` choisit selon la position (plus de 50 % : ferme, sinon ouvre) ; `ToggleDir` choisit selon le DERNIER SENS (il inverse). Aucun des deux ne « reprend dans le même sens » après un arrêt au milieu.
12. **Arrêt par appui de bouton.** Le pilote arrête un volet en mouvement quand le bouton est relâché (`ShutterButtonHandler`, test `direction != 0` et `hold_timer > 0`). Chemin de code lu, jamais essayé sur carte ici.
13. **Un bouton ne pilote qu'un volet** (`shutter_button[].shutter_number`). La diffusion MQTT (`<mqtt>`, `<mi>`) publie `ShutterPosition<i>` pour tous les volets sur le sujet de groupe (`ShutterButtonHandlerMulti`).

Non vérifié : modes 4 à 6 (servos, pas à pas), lamelles, `ShutterSetup` (Shelly), étalonnage matriciel au-delà de la lecture de `ShutterCalibration`.

### Ce que fait le pilote Berry de ce dépôt

- `drivers.voletRoulants.mode` du persist devient `ShutterMode` (UNE valeur pour tous les volets de la carte) : `data/fs/vrFonctions.be::vrFonctions_configVRByJson`, appelée par `data/fs/controleVoletRoulants.be`.
- Mode 3 : la même fonction envoie `PulseTime<relais1> 5` pour chaque volet (5 = 0,5 s dans Tasmota ; le message de journal dit « 5s », il est inexact).
- Mode 1 : un groupe `Interlock <relais1>,<relais1+1>` par volet, envoyé en UNE commande après la boucle, puis `Interlock ON`.
- Autres modes (2 notamment) : aucun réglage complémentaire (pas d'Interlock OFF, pas de PulseTime).
- Par volet : `ShutterRelay<id> <relais1>`, `ShutterInvertWebButtons<id> 0`, `ShutterInvert<id>` (clé `inverse`, 1 par défaut), `ShutterOpenDuration<id>` et `ShutterCloseDuration<id>` (clés `tempsMontee`, `tempsDescente`, entiers en secondes), puis `ShutterButton<id> <bouton> <function> <mqtt>` pour chaque bouton actif (`vrFonctions_configBoutons`). L'id du volet sert de numéro de volet Tasmota, sans trou.

Comparaison des exemples réels (lus dans les persist, rien de modifié) :

| Carte | `drivers.voletRoulants.mode` | Volets | `relais1` | Boutons |
|---|---|---|---|---|
| `data/rdc/tasmota32s3-grenier` (porte d'entrée, cuisine, trappe) | 1 | VR1, VR2, VR3 | 1, 3, 5 | VR1 : bouton 1 `up`, bouton 2 `down` ; VR3 : `toggle` |
| `data/garage/tasmota32p4-serveur-modbus` (rideau, côté maître) | 3 | VR1 | 2 (relais virtuel d'un esclave) | aucun |
| `data/garage/tasmota32s3-rideau-garage-modbus` (rideau, côté esclave) | 3 | VR1 | 1 | aucun |
| `data/etage2/tasmota32s3-grenier` (trappe) | 1 | VR1 | 2 | `toggle` |

- Volet de la porte d'entrée en mode 1 : CONFIRMÉ, mais au niveau du driver de la carte (les trois volets du RDC partagent ce mode).
- Rideau de garage en mode 2 : INFIRMÉ. Les persist du P4 et du S3 portent `mode: 3` (garage, un relais impulsionnel). La note de tête de `controleVoletRoulants.be` le dit aussi (« mode de fonctionnement 3, VR de garage »).
- Il n'existe ni mode par volet, ni « mode de bouton » autre que le paramètre `function` (`up`, `down`, `updown`, `toggle`) passé à `ShutterButton`.

---

# Traduction

## Volets et stores

Commande de stores et de volets roulants branchés sur des moteurs ordinaires (marche/arrêt), des moteurs pas à pas ou des servos de position. Avant tout, il faut activer la prise en charge avec `SetOption80 1`.

Le pilote ESP32 amélioré apporte : jusqu'à 16 volets, jusqu'à 32 boutons de volet, orientation de lamelles par boutons, configuration enregistrée dans le système de fichiers, et (Shelly Plus 2PM) mesure automatique des durées d'ouverture et de fermeture.

## Modes de fonctionnement

Le mode définit comment les relais sont pilotés. Vous pouvez en plus régler `PulseTime` sur un relais pour en faire un relais à impulsion (l'impulsion démarre ou arrête). Au moins pour le mode 1, un Interlock est obligatoire. Exemples pour `ShutterRelay1 1` (relais 1 et 2).

- **Mode 1, normal.** Relais 1 : HAUT/arrêt, relais 2 : BAS/arrêt. `Interlock 1,2` puis `Interlock ON`.
- **Mode 2, sans court-circuit (à régler à la main).** Relais 1 : marche/arrêt (alimentation), relais 2 : HAUT/BAS (sens). Interlock OFF.
- **Mode 3, moteurs de garage (à régler à la main).** Voir l'écart 4 : dans ce dépôt, un seul relais impulsionnel.
- **Mode 4, moteurs pas à pas.** Relais 1 : marche/arrêt, relais 2 : sens ; PWM : signal de pas, COUNTER : retour de position (autodétecté si PWM et COUNTER sont définis).
- **Mode 5, servos en position (PWM).** `PWMfrequency 200` obligatoire, `SetOption15 0`.
- **Mode 6, servos 360 degrés (PWM en vitesse).** Mêmes réglages que le mode 5.

Les câblages normal, pas à pas et sans court-circuit sont sur la page d'origine. Même sans deux moteurs, trois fils sont à raccorder.

Remarques :
- Après avoir réglé le mode, redémarrer. Sinon les curseurs n'apparaissent pas dans l'interface web et `ShutterOpenDuration<x>` / `ShutterCloseDuration<x>` répondent « Shutter unknown ».
- `ShutterMode` affiche le mode retenu ; `Status 13` montre la définition des volets.
- Mode 1 sans Interlock sur les relais : le pilote passe en erreur (voir l'écart 5). Définir l'Interlock sur la paire, le mettre à ON, puis redéfinir `ShutterRelay1`.
- Exemple de ligne de `Status 13` : `Shutter 0 (Relay:1): Init. Pos: 20000 [100 %], Open Vel.: 100 Close Vel.: 100, Max Way: 20000, Opentime 10.0 [s], Closetime 10.0 [s], ..., is inverted 1, ShutterMode 0, motordelay 0`.

## Fonctionnement

Agir directement sur un relais (`Power`) déplace aussi le volet. En mode impulsion (moteurs pas à pas), les relais démarrent ou arrêtent le moteur ; le pilote gère le sens et tient la position à jour.

Le volet rend compte de sa position et peut être envoyé à une position. `ShutterPosition 0` = fermé, `ShutterPosition 100` = ouvert. Pour inverser (0 = ouvert, 100 = fermé), définir et étalonner le volet puis `ShutterInvert<x> 1` : les calculs internes sont identiques, seule l'interaction avec l'utilisateur et les systèmes extérieurs change.

| Fonction | ShutterInvert 0 | ShutterInvert 1 |
|---|---|---|
| Relais 1 | ouvre | ouvre |
| Relais 2 | ferme | ferme |
| Bouton web HAUT / BAS | ouvre / ferme | ouvre / ferme |
| Curseur OUVERT / FERMÉ | ouvre / ferme | ouvre / ferme |
| ShutterOpen / ShutterClose | ouvre / ferme | ouvre / ferme |
| ShutterPosition 100 | ouvre | ferme |
| ShutterPosition 0 | ferme | ouvre |
| Position rapportée, ouvert | 100 | 0 |
| Position rapportée, fermé | 0 | 100 |

L'indice 0 vise tous les volets (`ShutterPosition0 30`) et fonctionne pour tous les réglages.

Avec `SetOption80 1`, définir `ShutterRelay1 <valeur>` pour commencer. Pour éviter tout mouvement imprévu au redémarrage, tous les relais doivent démarrer à l'arrêt : `PowerOnState 0`.

Quatre volets au plus sur ESP8266, 16 sur ESP32 (32 relais). Il peut falloir un expandeur de GPIO. Pour ajouter un volet : `ShutterRelay<x> <valeur>`, en numérotant sans trou (2, puis 3, puis 4). Désactiver un volet au milieu désactive tous les suivants ; les rétablir rétablit les suivants. Au changement, la liste des volets actifs et leurs paramètres sont écrits dans le journal. Pour en retirer plusieurs, commencer par le plus grand numéro.

Avec quatre volets, huit relais. Des interrupteurs manuels (paires `Switch<x>` ou `Button<x>`) demandent des GPIO en plus. Pour une paire d'interrupteurs, `SwitchMode<x> 2` (suit en inverse) est en général le bon réglage.

`ShutterLock<x> 1` verrouille le positionnement : un mouvement en cours se termine, puis `ShutterOpen`, `ShutterClose`, `ShutterStop`, `ShutterPosition`, les boutons et curseurs web et les boutons de volet sont désactivés (utile par grand vent). `ShutterLock<x> 0` déverrouille. Le volet reste commandable par `Power<x>` direct ou par des interrupteurs physiques ; utiliser `ShutterButton<x>` avant `ShutterLock` pour que les boutons soient verrouillables.

## Étalonnage

1. Partir de préférence volet fermé. `ShutterSetClose<x>` fixe la position interne à « fermé ».
2. `ShutterOpenDuration<x>` : temps pour ouvrir entièrement.
3. Si le volet ouvre plus que nécessaire : le ramener à la position voulue par `ShutterSetPosition<x>`, puis `ShutterSetOpen<x>` pour le déclarer ouvert (100), et diminuer le temps d'ouverture.
4. `ShutterCloseDuration<x>` : temps pour fermer entièrement.
5. S'il ne ferme pas complètement : rouvrir et ajuster le temps de fermeture. S'il tourne trop longtemps : le remonter à la position voulue, `ShutterSetClose<x>`, puis diminuer le temps.
6. Alterner ouverture et fermeture jusqu'à retrouver les mêmes positions à chaque fois.

Pour garantir les butées malgré les imprécisions, on peut ajouter un mouvement moteur supplémentaire aux positions 0 % et 100 % : `ShutterOpenEndStopTime<x> <secondes>` et `ShutterCloseEndStopTime<x> <secondes>` (depuis 15.6.0.2). Avant 15.6.0.2 : `ShutterEnableEndStopTime<x> <secondes>`. Remettre à 0 avant de mesurer à nouveau les durées.

### Retard de démarrage du moteur

Certains moteurs mettent jusqu'à une seconde à démarrer après la mise sous tension. Symptôme : ouvrir et fermer d'un coup fonctionne, mais en petites étapes la position dérive. Procédure :
1. `ShutterPosition<x> 30`, mesurer : position de référence.
2. `ShutterPosition<x> 80`, mesurer : position maximale.
3. `ShutterPosition<x> 30` : on doit retrouver la référence, sinon ajuster `ShutterCloseDuration`.
4. `ShutterPosition<x> 50`, puis 70, puis 80. Si la position maximale n'est pas atteinte, mesurer la position réelle `real_max`.
5. `ShutterMotorDelay<x> <délai>` avec `délai = ((max_position - real_max) / 2) / (((100/80) * max_position) / ShutterOpenDuration)` ; affiner par pas de 0,05 s. Fermer et recommencer jusqu'à un bon réglage.

Constante compilée : attente de 0,1 s du relais de direction avant d'alimenter le relais principal (`SHUTTER_RELAY_OPERATION_TIME 100`, modifiable seulement en recompilant).

### Position de mi-course (réglage grossier)

Certains volets mettent du temps à décoller du bas : à 50 % du temps écoulé ils sont ouverts de moins de la moitié. `ShutterSetHalfway<x>` corrige :
1. `ShutterClose<x>` (vérifier la fermeture complète) ; `ShutterSetHalfway<x> 50` (valeur par défaut).
2. Amener le volet à la vraie mi-ouverture, lire `ShutterPosition<x>` (ex. 63).
3. `ShutterClose<x>`, `ShutterSetHalfway<x> 63`, puis `Restart 1`.

### Réglage fin (matrice d'étalonnage)

Pour que le pourcentage affiché colle à l'ouverture réelle : `ShutterSetHalfway<x> 50`, `ShutterCalibration<x> 30 50 70 90 100` (valeurs par défaut), `ShutterClose<x>`, puis amener le volet à 30, 50, 70, 90 et 100 % par `ShutterPosition<x>` et mesurer chaque ouverture (dans une même unité : cm, pas, etc.). Enfin saisir les mesures, par exemple `ShutterCalibration<x> 15 50 100 150 180`. `ShutterCalibration` prend des mesures de position, pas des durées. Il n'y a pas de point à 10 % : les 10 % premiers du temps ne bougent souvent pas, ce qui causerait une division par zéro.

### Temps d'arrêt du moteur

Un changement de sens immédiat peut causer un court-circuit ou de forts couples. Délai par défaut entre un ARRÊT et le DÉMARRAGE suivant : 0,5 s. `ShutterMotorStop 500` (millisecondes, valeur commune à tous les volets, depuis la version 12.3). Attention : si un relais est piloté DIRECTEMENT par un bouton ou un interrupteur, sans `ShutterButton` ni règle, ce délai ne joue pas.

## Commandes de boutons : ShutterButton

En mode 1, interrupteurs et boutons de la configuration du module peuvent déjà commander les relais. En mode 2, la commande directe des relais est peu pratique (un bouton pour le sens, un autre pour l'alimentation). Les boutons utilisent les appuis multiples : vérifier que l'action immédiate est coupée (`SetOption13 0`, par défaut).

`ShutterButton<x> <bouton> <fonction> <mqtt>` assigne un bouton Tasmota (déjà configuré dans le module) au volet `<x>`. Plusieurs boutons par volet, mais un bouton ne commande qu'un volet (hors diffusion `<mqtt>`). Tout appui pendant un mouvement arrête le volet. `ShutterButton<x> 0` retire tous les boutons du volet.

- `up` : appui simple 100 %, double 50 %, triple 75 % (la doc écrit 74). Maintenu plus longtemps que `SetOption32` : tous les volets du même `GroupTopic` à 100 % si `<mqtt>` vaut 1 ; sinon comme un appui simple.
- `down` : simple 0 %, double 50 %, triple 25 % (la doc écrit 24). Maintien : comme `up`, vers 0 %.
- `updown` : simple 100 %, double 0 %, triple 50 %. Pas de maintien ni de diffusion.
- `toggle` : simple = bascule (selon la position : au-delà de 50 % ferme, sinon ouvre), double = 50 %. Pas de maintien ni de diffusion.

Syntaxe avancée : `ShutterButton<x> <bouton> <p1> <p2> <p3> <ph> <m1> <m2> <m3> <mh> <mi>`
- `<bouton>` 1..32 (ESP32), 0 ou `-` : coupe les boutons de ce volet.
- `<p1>` simple, `<p2>` double, `<p3>` triple, `<ph>` maintien : 0..100 position, `t` bascule, `-` désactivé, `--n` ou `++n` pas relatif.
- `<m1>`, `<m2>`, `<m3>`, `<mh>` : 1 diffuse la position en MQTT, 0 ou `-` non. `<mi>` : 1 diffuse à tous les indices de volet.
- Les paramètres manquants désactivent les suivants. Sur ESP32, une position peut être suivie de l'orientation des lamelles après `/` (exemple : `shutterbutton1 1 100/-90 50/0 75/-90 100 - - 1 1`).
- Pour que le maintien déclenche quelque chose, `SetOption32` doit valoir plus de 5 (0,6 s minimum).
- Équivalences : `ShutterButton<x> <b> 100 50 74 100 0 0 0 1 1` = `up 1` ; `... 0 50 24 0 0 0 0 1 1` = `down 1` ; `... 100 0 50 - 0 0 0 0 0` = `updown 0` ; `... t 50 - - 0 0 0 0 0` = `toggle 0`. (Le firmware de ce dépôt met 75 et 25 pour les raccourcis.)
- Un appui long sur tous les boutons d'un volet (ou 5, 6, 7 appuis simultanés) active les fonctions réseau (Wi-Fi, redémarrage, mise à jour, réinitialisation) sans `SetOption1`.

La diffusion MQTT publie `cmnd/<grouptopic>/ShutterPosition<x>`. Avec `<mi>` à 1, c'est pour tous les indices (1 à 16), le volet de la carte compris : à éviter sur une carte qui porte aussi un autre volet.

## Télécommande

Un autre appareil Tasmota muni d'un bouton peut piloter un volet par règle. `ShutterStopClose`, `ShutterStopOpen`, `ShutterStopToggle`, `ShutterStopPosition` arrêtent le volet s'il bouge et, sinon, ferment, ouvrent, basculent ou positionnent. `ShutterStopToggleDir` arrête puis, à l'arrêt, inverse le dernier sens. Exemple : `rule1 on switch1#state=2 do publish cmnd/%shutter-topic%/ShutterStopToggle endon`.

## Règles

Pendant les mouvements, les données de tous les volets sont envoyées chaque seconde (position, cible, sens, lamelles). Exemples :
- `rule1 on shutter1#direction=0 do <echo shutter1 stopped> endon`
- `rule1 on shutter2#position do var1 = %value% endon`
- `rule1 on shutter#moving do ... endon` (au moins un volet part), `rule1 on shutter#moved do ... endon` (un volet vient de s'arrêter)
- Toute commande est aussi un événement : `rule1 on shutterposition1=0 do <echo volet 1 se ferme> endon`

Déclencheurs :
- `Shutter<x>#Position` : au départ, pendant et à la fin, position 0..100.
- `Shutter<x>#Direction` : -1 direction fermeture, 0 arrêt, 1 direction ouverture.
- `Shutter<x>#Target` : cible 0..100.
- `Shutter#Moving` : pendant le mouvement et juste avant (tous volets). Si `VAR<x>` vaut 99, il s'exécute AVANT le démarrage : on peut démarrer ensuite en mettant `VAR<x>` à 0, sinon un délai de 10 s s'applique ; après le mouvement (`shutter#moved`) remettre `VAR` à 99 et réactiver la règle (à exécuter une seule fois).
- `Shutter#Moved` : fin de mouvement (tous volets).
- `Shutter<x>#Button<b>=0` maintien ; `=<n>` n appuis ; `Shutter<x>#Button0=0` ou `=<n>` : tous les boutons du volet simultanément.
- Exemple : `Rule1 ON Shutter1#Position DO ShutterPosition2 %value%" ENDON` recopie la position du volet 1 sur le volet 2.

## Moteurs à impulsion

Certains volets ont deux ou trois relais mais n'attendent qu'une impulsion : selon la situation elle arrête ou lance un sens précis. Définir `PulseTime` sur chaque relais (minimum fiable : 2 ; 1 ne marche pas ; si le volet va trop vite pour réagir à l'arrêt, 3 ou 4). Avec un relais d'arrêt dédié (les autres seulement pour OUVRIR et FERMER) : `ShutterStopRelay1 1` envoie l'arrêt au troisième relais (RELAY3), RELAY1 ouvrant et RELAY2 fermant. Pour la liste de contrôle, définir `PulseTime<x> 2` sur les deux relais d'un moteur à impulsions.

## Autres moteurs (résumé)

- Moteurs pas à pas : un seul volet sur ESP8266, jusqu'à 4 sur ESP32 ; pilote A4988, DRV8825 ou TMC2208 ; signaux EN (relais inversé), DIR (relais), STP (PWM) et un COUNTER relié au PWM ; `ShutterFrequency` (1000 par défaut, jusqu'à 10 000 Hz) ; `ShutterMotorDelay` donne une rampe ; `SetOption15 0`.
- Servos : EN et DIR sur les relais 1 et 2, signal PLS sur PWM ; `PWMfrequency 200`, `ShutterPWMRange<x> min,max` (dépend du servo), durées d'ouverture et de fermeture = vitesse, `ShutterMotorDelay` = rampe.
- Lamelles orientables (moteurs temporisés) : `ShutterTiltConfig<x> <min> <max> <durée en 1/20 s> <angle ouvert> <angle fermé>`, `ShutterTilt<x>`, `ShutterTiltChange<x>`. L'orientation est rétablie après un mouvement, pas aux butées.

## Liste de contrôle

1. Le premier relais ouvre le volet. 2. Le second le ferme. 3. `ShutterRelay<x>`. 4. `ShutterOpenDuration<x>`. 5. `ShutterCloseDuration<x>`. 6. `ShutterSetHalfway<x>` (facultatif). 7. `ShutterInvert<x>` (facultatif). 8. `ShutterInvertWebButtons<x>` (facultatif, par exemple pour un store horizontal). 9. Moteur à impulsion : `PulseTime<x> 2` sur les deux relais.

---

# Porte de garage : un seul relais (rideau VR1, mode 3)

Besoin : la motorisation est actionnée par un poussoir direct qui alterne à chaque impulsion (1re : monte, 2e : arrête, 3e : descend, 4e : arrête...). C'est la logique du mode 3, vérifiée dans `xdrv_27_esp32_shutter.ino::CmndShutterPosition` (branche `SHT_TIME_GARAGE`) :

- Seul le relais de départ (`ShutterRelay<x>`) est pulsé. Aucune commande `ShutterPulse` n'existe ; les réglages utiles sont `PulseTime<relais>` (impulsion automatique, 5 = 0,5 s dans Tasmota) et `ShutterMotorStop` (pause entre deux impulsions, 500 ms par défaut, commune à tous les volets).
- Sens demandé différent du dernier sens (`lastdirection`) : UNE impulsion (la motorisation change d'état comme prévu).
- Sens demandé identique au dernier sens : le moteur est « en retard d'un état ». Avec `PulseTime` (mode impulsion), DEUX impulsions de mise en phase (démarre en sens inverse, puis arrête) puis l'impulsion de départ, soit trois impulsions ; sans `PulseTime`, une seule impulsion de mise en phase. Les pauses valent `ShutterMotorStop`.
- Arrêt en cours de course : une impulsion sur le même relais (`ShutterPowerOff`, branche `SHT_PULSE`).
- La fin de course temporisée émet elle aussi cette impulsion d'arrêt (commentaire du code : « pulse après la fin »). Si la motorisation s'arrête seule en butée, cette impulsion la ferait repartir en sens inverse : à vérifier sur carte avec les durées réelles.
- Fragilité : le pilote ignore une impulsion donnée par la télécommande d'origine ; un appui extérieur désynchronise `lastdirection`.

Configuration actuelle de VR1 sur le P4 (`relais1: 2`, persist non modifié) :
- `vrFonctions.be::vrFonctions_configVRByJson` pose `PulseTime2 5` et, en mode 3, AUCUN Interlock (il n'est posé qu'en mode 1). Rien ne bloque donc le relais 3.
- Le relais 3 (« Relai 2 », type 256, esclave id 3) n'est piloté par personne : `activationSiOuvert` et `activationSiFerme` ont des `tabRelais` vides.
- Mais le firmware RÉSERVE `relais1 + 1` dans le masque des relais du volet (`RelayShutterMask |= 3 << (relais - 1)`) : un changement manuel du relais 3 compterait comme un ordre sur le volet. Un seul relais suffit côté matériel ; l'indice `relais1 + 1` reste réservé tant que le volet existe.
- Retrait du relais 3 du persist du P4 : NON, voir plus bas (il fait partie du comptage `devices_present`). À essayer sur carte : l'impulsion de fin de course et le premier mouvement après redémarrage (`lastdirection` vient de la position mémorisée : plus de 50 % = dernier sens « monte »).

---

# Application au portail (architecture du 2026-11-14, version finale)

## Abandonné

Les versions précédentes de cette section sont abandonnées : « voie A » (Shutter mode 1 sur l'esclave 4), « 4 relais » (haut et bas par vantail), VR droit et VR gauche, « un seul moteur » (un Shutter à 2 relais sur l'esclave). Raison : le portail réel est un ensemble de 2 moteurs géré par une carte électronique qui choisit la manoeuvre selon l'entrée activée, et l'utilisateur veut sur l'interface web du P4 le comportement d'un Shutter (curseur, position, barre de progression), comme le rideau. Aucun Shutter ne tourne sur l'esclave 4 ; le P4 reste en mode 3 pour tout (rideau ET portail).

## Chaîne de commande (6 maillons)

1. Poussoir 1 (entrée réelle du P4, `bouton3`, GPIO 1) : ouverture d'UN vantail. Poussoir 2 (`bouton4`, GPIO 2) : ouverture des DEUX vantaux.
2. `ShutterButton` du VR concerné (VR2 pour le poussoir 1, VR3 pour le poussoir 2), fonction `toggle`.
3. Shutter 2 ou 3 du P4, mode 3 (un relais impulsionnel), qui pulse son relais virtuel.
4. Relais virtuel du P4 : 20 (« Portail 1 vantail ») ou 22 (« Portail 2 vantaux »), de l'esclave ModBus id 4 (`ModBus_TasmotaSlaveModBus3`).
5. Relais réel 1 ou 2 de l'esclave 4 (GPIO 41 et 42), à auto-extinction de 1 s (`timer: 1`).
6. Entrée 1 ou 2 de la carte électronique du portail.

Persists écrits : `data/garage/tasmota32s3-portail-jardin-modbus/_persist.json` (esclave sans Shutter : `drivers.voletRoulants.activation` OFF, aucun VR, relais 1 et 2 réels avec `timer: 1`, interrupteur de fermeture `Switch1`, template GPIO identique à celui du rideau) et `data/garage/tasmota32p4-serveur-modbus/_persist.json` (166 lignes ajoutées, 0 retirée).

## Numérotation retenue des relais virtuels du P4

| Relais | Rôle | `idModBus` | Pourquoi |
|---|---|---|---|
| 20 | ordre « 1 vantail » (`relais1` du VR2) | 1 | relais réel 1 de l'esclave |
| 21 | bouche-trou : réservé par le Shutter du VR2 (`relais1 + 1`) | aucun | jamais commandé |
| 22 | ordre « 2 vantaux » (`relais1` du VR3) | 2 | relais réel 2 de l'esclave |
| 23 | bouche-trou : réservé par le Shutter du VR3 | aucun | jamais commandé |

- Le firmware réserve `relais1 + 1` (`RelayShutterMask |= 3 << (relais - 1)`) et, en mode 3, éteint ce relais à l'arrêt (`ShutterPowerOff`, branche pulsée). Un relais de ce rang doit donc exister.
- Le comptage (`configDevices.be`, `tasmota.global.devices_present = nombre de relais actifs`) ne dépend pas des id mais du nombre : relais 1 à 19 existants + 4 = 23 une fois l'esclave ON. Rien n'est réservé de plus : 2 ordres et 2 bouche-trous, c'est le minimum avec deux Shutters distincts.
- Ce que fait le rideau : son relais 3 (« Relai 2 ») est le relais réel 2 de l'esclave rideau, jamais commandé, qui sert de bouche-trou. Il reste en place (retrait impossible : le nombre de relais passerait de 19 à 18 et `Power19` disparaîtrait).
- Les bouche-trous n'ont PAS de `idModBus` : `modBus_TasmotaSlaveModBus.be` ignore les relais sans `idModBus` à l'envoi comme à la lecture, donc aucune trame vers un registre inexistant. Ils comptent quand même, parce que le comptage ne regarde que le champ `virtuel` et l'état de l'esclave.
- Variante écartée : `relais1` 20 et 21 (le « relais1 + 1 » du VR2 serait l'ordre du VR3) économise un relais, mais les masques se recouvrent et le firmware éteindrait l'ordre du VR3 à l'arrêt du VR2. Non essayé, non retenu.

## Boutons : ce qui est lié automatiquement

- Lié par le code existant, sans rien écrire : `vrFonctions.be::vrFonctions_configBoutons` envoie `ShutterButton<id> <bouton> toggle 0` pour chaque bouton de VR actif. VR2 : `bouton1` → id 3 ; VR3 : `bouton1` → id 4. Les deux boutons sont déjà déclarés dans les modules du P4 (`SetOption73 ON` posé par `configDevices.be` : ils ne basculent donc aucun `Power<n>`).
- Comportement de `toggle` (firmware) : appui simple = bascule selon la position (plus de 50 % : ferme, sinon ouvre) ; appui double = 50 % ; tout appui pendant un mouvement arrête le volet ; l'appui suivant repart selon la position, pas dans le même sens.
- Non lié, donc manquant : poussoir 2 n'ouvre pas « aussi » le vantail du poussoir 1 (aucun couplage entre VR2 et VR3). Les deux Shutters ont chacun sa position ; rien ne les synchronise si l'on actionne l'un puis l'autre.
- Limite du mode 3 : si le sens demandé est celui du dernier mouvement, le firmware envoie deux impulsions de mise en phase avant l'impulsion de départ (trois pulsations, voir la section du rideau). Pour un portail dont l'entrée n'a qu'un sens (ouverture), c'est inadapté : à vérifier avec la carte électronique (une même entrée sert-elle aussi à fermer ?).

## PulseTime : 1 s n'est pas configurable par VR

`vrFonctions.be::vrFonctions_configVRByJson` envoie `PulseTime<relais1> 5` (5 = 0,5 s) : la valeur 5 est écrite en dur dans le code, aucune clé du persist ni du VR ne la change. Pour 1 s (`PulseTime 10`) il faut modifier `data/fs/vrFonctions.be` (par exemple une clé `impulsion` du VR, non existante) ; non fait ici, `data/fs` est intact. En attendant, le P4 coupe le relais virtuel à 0,5 s ; le `timer: 1` de l'esclave est un filet : un OFF reçu à temps annule ce timer (`controleGeneral.be`, arrêt du timer à OFF).

## Mise en service : tout est OFF ensemble

`TasmotaSlaveModBus3`, les relais 20 à 23, `interrupteur3`, VR2 et VR3 sont en activation OFF dans le persist du P4 tant que l'esclave n'existe pas (sinon relevés sans réponse sur le bus, relais comptés pour rien, Shutters sur des relais absents). À passer à ON ensemble une fois l'esclave en ligne. `tempsMontee` et `tempsDescente` valent 30 s, provisoires. VR2 et VR3 n'ont pas de bloc `facade` (le type `portail` de `volets.js` sera écrit plus tard). Le capteur de fermeture (`Interrupteur3`, virtuel, relais d'entrée de l'esclave) est désigné `capteurFerme` sur les deux VR : il recale les deux à « fermé » (hypothèse : contact fermé = portail entièrement fermé).

## Ce qui reste à faire

1. Env PlatformIO, autoexec et `user_config_override.h` de l'esclave (à la charge de l'utilisateur).
2. `PulseTime 10` configurable par VR dans `vrFonctions.be`.
3. Façade `portail` dans `volets.js` ; lecture de la position inutile (les Shutters sont sur le P4).
4. Mesure des durées et vérification sur la carte électronique du portail : sens de chaque entrée, effet des impulsions multiples, fermeture.

## Non vérifié sur carte

Tout : démarrage de l'esclave avec ce persist, ordre des relais par ModBus UDP, impulsion de 0,5 s comprise par la carte électronique, `timer: 1` effectif, comptage à 23 relais, comportement de Shutters dont `relais1 + 1` est un relais virtuel sans `idModBus`, `ShutterButton` sur `bouton3` et `bouton4`, polarité du capteur de fermeture, modèle GPIO du P4 avec les deux boutons.
