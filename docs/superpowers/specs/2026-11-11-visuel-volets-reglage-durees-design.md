# Visuel des volets sur la page d'accueil et réglage des durées par les boutons

Date : 2026-11-11. Plan : `tasks/plans/envs-grenier-rdc-sonoff-cave.md`, actions A12 (visuel) et A13 (durées).
Maquettes validées par l'utilisateur : `outils_docs/volets_visuels/`.

## 1. Pourquoi

L'utilisateur commande ses volets à distance depuis la page d'accueil de la carte, sans les voir. Le curseur natif
de Tasmota donne un nombre, rien de plus. Il veut voir sous ces curseurs un dessin de la façade où chaque volet
bouge **en direct** pendant la course, avec son pourcentage : c'est sa preuve que le volet a obéi et jusqu'où il
est allé.

Les durées de montée et de descente (`tempsMontee`, `tempsDescente`) se règlent aujourd'hui à la main dans le
persist. Sans elles justes, la position affichée (curseur et dessin) est fausse. Il veut les régler simplement, sur
place, avec les boutons qu'il a déjà.

## 2. Objectifs, non-objectifs, anti-objectifs

Objectifs :
- une façade dessinée sous les curseurs des volets, sur chaque carte à volets, dont les tabliers suivent la position
  réelle et bougent pendant la course ;
- un mode de réglage des durées, lancé depuis la page « Configuration », qui mesure la course avec les boutons
  existants et écrit les durées dans le persist.

Non-objectifs :
- commander un volet depuis le dessin (les curseurs et boutons natifs restent les seules commandes de l'accueil) ;
- mesurer la course par les butées (fins de course, inclinomètre) : idée écartée par l'utilisateur ;
- les cartes sans volets, et le Sonoff ESP8285 de la cave (pas de Berry).

Anti-objectifs (échec même si « ça marche ») :
- un dessin qui saute de 2 s en 2 s au lieu de bouger ;
- un dessin qui montre une autre position que le curseur, ou l'inverse du réel (fermé dessiné ouvert) ;
- une requête de plus vers la carte à chaque rafraîchissement, ou du code de dessin envoyé aux cartes qui n'ont pas
  de volet ;
- un réglage qui écrit une durée fausse sans le dire (course interrompue, mauvais sens, délai dépassé).

## 3. Les façades, carte par carte

| Carte (env) | Façade | Volets |
|---|---|---|
| Grenier du RDC (`tasmota32s3-rdc-grenier`) | maison à deux pans, élargie ; fenêtre de la cuisine à gauche, trappe au milieu, porte d'entrée à droite | Shutter1 porte (2 boutons), Shutter2 cuisine (2 boutons), Shutter3 trappe (1 bouton) |
| P4 du garage (`tasmota32p4-garage-serveur-modbus`) | bâtiment à un seul pan, légèrement incliné vers la droite ; une grande porte de garage à lames | Shutter1, la porte du garage (relais virtuels du P4), sans bouton déclaré |
| Grenier du 2e étage (`tasmota32s3-etage2-grenier`) | plafond vu de face, sans maison | trappe (1 bouton) |

Rendu de chaque type d'ouverture (référence : les maquettes) :
- **fenêtre** et **porte** : tablier à lames qui descend depuis le coffre et couvre la vitre ou la porte ;
- **porte de garage** : même tablier à lames, plus large ;
- **trappe du RDC** : dans le plancher du grenier, sous le toit ; son panneau se baisse face à l'observateur ;
- **trappe du 2e étage** : le panneau se baisse face à l'observateur, puis l'échelle descend depuis le **haut de la
  trappe, devant le panneau**, et vient reposer sur un **escalier en bois fixe** qui descend de gauche à droite.

Chaque ouverture porte son pourcentage d'ouverture à côté d'elle (100 % = ouvert). Le dessin suit le thème sombre de
la page Tasmota.

Le module du rideau (`tasmota32s3-garage-rideau-garage-modbus`) n'a PAS de visuel (décision de l'utilisateur) : il
ne fait pas tourner le driver des volets (`vrFonctions.be` et `controleVoletRoulants.be` sont dans son
`custom_files_exclude`, c'est le P4 qui pilote la porte) ; il reste tel qu'il est.

## 4. Visuel : comportement

### 4.1 Source de la position

Aucune requête nouvelle. Pendant une course, la page d'accueil reçoit déjà à chaque rafraîchissement (environ 2 s)
une ligne `eb('s27<n>').value='<v>';` par volet qui bouge (`xdrv_01_9_webserver.ino`, bloc `USE_SHUTTER` de la
réponse de rafraîchissement). Le dessin lit la valeur du curseur `s27<n>`.

Attention, la valeur du curseur dépend de `ShutterInvert` : Tasmota envoie `100 - position` quand le bit 1 de
`ShutterGetOptions` est posé. Le dessin doit montrer le **pourcentage d'ouverture réel**, dessin ET chiffre. Sur
les cartes `inverse 1` (P4 du garage, 2e étage), le curseur natif affiche donc l'inverse du chiffre du dessin
(porte ouverte : curseur à 0, dessin à 100 %) ; c'est voulu (décision de Claude, d'après la demande « position
réelle »). L'anti-objectif « autre position que le curseur » se lit comme la position physique, pas le nombre. La correspondance
curseur -> ouverture se déduit de la clé persist `inverse` du volet (1 par défaut, 0 sur le grenier du RDC), et se
vérifie sur carte : volet ouvert, le dessin doit être ouvert, sur une carte `inverse 1` (garage) comme sur une carte
`inverse 0` (grenier du RDC).

### 4.1 bis Trappe avec inclinomètre MPU6050 actif (décision de l'utilisateur, 2026-11-11)

Quand `capteursPosition.inclinaison.activation` vaut `"ON"` dans le persist, le dessin suit **l'angle mesuré** en direct,
converti en pourcentage d'ouverture comme `vrFonctions.positionReelle` (entre `angleFerme` et `angleOuvert`, borné à
0 et 100). L'angle est lu dans la ligne « inclinaison » que la carte envoie déjà à chaque rafraîchissement : aucune
requête de plus. Sans angle lu (capteur muet), le dessin reprend le curseur. Un blocage ou un sens inverse signalé par
le MPU6050 passe l'ouverture en rouge, avec « bloqué » ou « sens inverse », en plus de la ligne d'inclinaison actuelle.

### 4.2 Mouvement fluide

Poursuite (décision de Claude après relecture du 2026-11-11, elle remplace l'extrapolation d'abord prévue) : la cible
est la dernière valeur lue (curseur converti en % d'ouverture, ou angle du MPU6050 pour une trappe) ; le dessin la
rejoint à la vitesse du volet, `100 / tempsMontee` %/s quand il monte, `100 / tempsDescente` %/s quand il descend, sans
jamais la dépasser, puis s'arrête. Au chargement de la page, il prend la cible directement. Le dessin a donc au plus un
rafraîchissement de retard sur la position réelle, mais ne montre jamais une position que le volet n'a pas atteinte.
Raisons : l'extrapolation dépassait la position finale à chaque fin de course (jusqu'à 1,5 rafraîchissement), et Tasmota
n'envoie une valeur que si elle diffère de la dernière envoyée (`Web.shutter_slider`), ce qui rendait faux tout
traitement à part d'un curseur tiré à la main : la poursuite le traite comme une valeur ordinaire.

### 4.3 Description de la façade dans le persist

Chaque carte décrit sa façade dans son persist, à côté des volets (décision de Claude ; nom et forme exacts laissés
au constructeur) : forme du toit (`deuxPans`, `unPan`, `aucun`), et pour chaque volet son type (`fenetre`, `porte`,
`garage`, `trappe`, `trappeEchelle`) et sa place de gauche à droite. Sans ce bloc, ou bloc inactif, rien n'est dessiné
et rien n'est envoyé à la page. Le modèle `outils_docs/schemas/modele_persist.json` et le schéma suivent.

### 4.4 Où vit le code

- Code commun, partagé par les cartes à volets, dans `data/fs` (accord de l'utilisateur à demander avant
  l'écriture, comme pour tout `data/fs`) ; la partie page (dessin, animation) dans `data/sd/js` (et CSS si besoin),
  comme les autres pages des cartes.
- Le dessin s'ajoute à la page d'accueil par le driver des volets (`controleVoletRoulants.be`), et se place **sous
  les curseurs des volets**. Si l'emplacement natif de l'ajout n'est pas sous eux, le script le déplace dans la page
  (comme `controleGeneral.be` réorganise déjà ses boutons).
- Les fichiers de page ne partent que sur les cartes à volets : une liste de `[berry_commun]` exclue dans
  `custom_files_exclude` des autres envs (règle du dépôt).

## 5. Réglage des durées

### 5.1 Déroulé (validé par l'utilisateur)

1. L'utilisateur amène le volet en **butée basse** (fermé) par une commande habituelle.
2. Page « Configuration » -> bouton « Réglage des volets » -> page de réglage : il choisit le volet et clique sur
   « Régler les durées ». La carte allonge provisoirement la course autorisée (`ShutterOpenDuration` et
   `ShutterCloseDuration` à 120 s) pour que le moteur ne s'arrête pas avant la vraie butée.
3. Un appui sur un bouton du volet (le bouton unique, l'un ou l'autre des deux boutons, ou le bouton de la page de
   réglage) : le volet **monte**, la carte lance le chronomètre.
4. Un appui à l'arrivée en haut : la carte arrête le volet et retient `tempsMontee`.
5. Un appui : le volet **descend** ; un appui à l'arrivée en bas : arrêt, `tempsDescente` retenu.
6. La carte écrit les deux durées dans le persist, remet les durées normales de Tasmota, recale la position (ouvert
   après la montée, fermé après la descente), sort du mode et affiche le résultat.

### 5.2 Règles

- Pendant le mode, **le sens est imposé par l'étape**, pas par le bouton : un appui sur n'importe quel bouton du
  volet vaut « étape suivante ». C'est indispensable pour un bouton unique en `toggle`, qui choisirait sinon le sens
  d'après le dernier mouvement, et pour un bouton `down` pressé à l'étape de montée. Le comportement natif des
  boutons de ce volet (`ShutterButton`) est donc suspendu le temps du mode et remis à la sortie.
- Les autres volets de la carte gardent leurs boutons normaux. Un seul volet en réglage à la fois.
- Les fins de course du volet (trappe du RDC, trappe du 2e étage) sont **neutralisées** pendant la mesure : leur
  recalage (`changementEtatCapteur` -> `commandeArret` -> `ShutterSetOpen/Close`) remettrait la direction à 0 sans
  couper le moteur en pleine mesure (décision de Claude ; l'utilisateur a écarté les butées pour le réglage).
- Inclinomètre MPU6050 actif : **garde-fou seul** (décision de l'utilisateur). La mesure reste faite par les appuis.
  Pendant le mode, l'arrêt automatique en butée et le recalage de la position par l'angle sont coupés ; la détection
  du blocage et du sens inverse reste active : elle coupe le moteur, le réglage s'arrête sans rien écrire et la page en
  donne la cause. Si le MPU6050 a mesuré la même course d'une butée à l'autre, la page affiche sa durée à côté de la
  mesure de l'utilisateur, pour comparer ; c'est la mesure de l'utilisateur qui est écrite.
- Mauvais sens : la page affiche, à chaque départ, « le volet monte-t-il ? Sinon, Annuler » (« descend » à l'étape
  2) ; le délai de 120 s reste le dernier garde-fou (décision de Claude : seul l'utilisateur voit le sens réel des
  volets sans capteur).
- Les boutons natifs ▲ ▼ de la page d'accueil ne sont pas interceptés ; le bouton de la page de réglage remplace
  l'appui physique (décision de Claude, d'après « on peut aussi utiliser les boutons de l'interface web »).

### 5.3 Porte de garage : chronomètre seul (décision de l'utilisateur)

La porte du garage a une motorisation à impulsions (mode 3, `PulseTime` 5 : `xdrv_27_esp32_shutter.ino`, cas
`SHT_PULSE` et `SHT_TIME_GARAGE`) : c'est elle qui choisit le sens, et une impulsion d'arrêt pourrait la relancer si
elle s'est déjà arrêtée en butée. Aucun bouton n'est déclaré pour elle. Pour ce volet, le mode ne commande RIEN :
1. l'utilisateur ouvre le mode sur la page de réglage du P4, porte fermée ;
2. il lance la porte comme d'habitude (télécommande, curseur, bouton) et clique « Départ » sur la page ;
3. il clique « Arrivée » quand la porte est en haut : `tempsMontee` retenu ; même chose dans l'autre sens ;
4. la carte écrit les deux durées dans le persist du P4. Pas de course allongée, pas d'arrêt envoyé, fins de course
   laissées telles quelles (la porte s'arrête seule).
Le type de volet (moteur direct ou impulsions) se lit du mode du persist (`mode` 3 = garage).

### 5.4 Garde-fous (validés)

- Sans second appui avant 120 s : arrêt du moteur, rien n'est enregistré, sortie du mode avec un message.
- Bouton « Annuler » : arrêt du moteur s'il tourne, rien n'est enregistré, durées et boutons d'avant remis.
- L'état du mode vit en RAM : un redémarrage le perd sans rien écrire ; au démarrage suivant, `configVRByJson`
  réapplique les durées du persist comme d'habitude.

### 5.5 La page de réglage

- Les **explications pas à pas destinées à l'utilisateur figurent sur la page** (demande explicite) : préparation
  (volet en bas), ce que fait chaque appui, comment annuler, ce qui est écrit à la fin.
- Elle montre l'étape en cours, le chronomètre, puis les deux durées mesurées et celles d'avant.
- Elle dit que les durées sont écrites dans le persist DE LA CARTE, et qu'un flash série ou un envoi du FS les
  remplacera par celles du dépôt : elle affiche les valeurs à recopier dans `data/<lieu>/<carte>/_persist.json`
  (décision de l'utilisateur ; Claude peut faire la recopie à sa demande).
- Les ordres de la page passent par des requêtes POST protégées comme les autres pages des cartes du dépôt.

## 6. Contraintes

- Cartes visées : S3 et P4 seulement (toutes les cartes à volets le sont).
- Charte des logs Berry du dépôt (`CLAUDE.md`, `logFonctions`) ; pas d'`info` dans un callback fréquent.
- RAM : rien de permanent en plus côté carte pour le visuel (le dessin est fait par le navigateur) ; le mode réglage
  ne garde que son petit état.
- `vrFonctions.be` et `controleVoletRoulants.be` sont solidifiés sur les envs à volets : toute fonction nouvelle est
  appelée par `vrFonctions.nom`, et la solidification de chaque env concerné est revue (banc de démarrage).
- Aucun build lancé en parallèle de ceux de l'utilisateur ; compilation par la page Build (:7700).
- Les sondes Chrome lancées pour les essais arrêtent leurs Chrome en fin d'usage.

## 7. Laissé au constructeur

- nom et forme exacts du bloc de façade du persist, et des routes de la page de réglage ;
- découpage entre `data/fs` et `data/sd`, et nom des fichiers ;
- moyen technique de suspendre puis remettre les boutons natifs d'un volet pendant le réglage ;
- précision des durées écrites (entier ou dixième de seconde), selon ce que `configVRByJson` et Tasmota acceptent ;
- détail du dessin (proportions, couleurs) dans l'esprit des maquettes.

## 8. Vérification attendue

- Banc Berry du mode réglage (déroulé complet, annulation, délai dépassé, bouton unique en `toggle`, sens imposé),
  avec un témoin qui rougit sans le code.
- Sonde Chrome hermétique du dessin : position lue d'un curseur simulé, sens correct en `inverse` 0 et 1, mouvement
  entre deux valeurs ; Chrome arrêté en fin de sonde.
- `banc_demarrage.py` vert ; `verifie_berry.py` ; agents `relecteur-berry` et `relecteur-pages-web`.
- Banc du chronomètre seul de la porte de garage (aucune commande envoyée au volet).
- Essai sur carte : grenier du RDC à sa mise en service, puis P4 du garage et 2e étage.
