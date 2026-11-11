# Lieu partagé depuis l'annuaire, lieu dans le syslog et le sniffeur MQTT

Date : 2026-11-11. Suite de `2026-11-10-classement-par-lieu-design.md` (ses deux « améliorations restantes »). Maquettes
et choix : `outils_docs/filtre_lieu/` (section « Suite », `maquettes_lieu_suite.html`, `modele-J.png` à `modele-O.png`).

## 1. Intention

Le classement par lieu existe dans les pages de maintenance (7700 à 7980). Deux manques restent :
- on choisit le lieu dans chaque page ; l'utilisateur veut le choisir UNE fois, dans l'annuaire (7600), et que la page
  ouverte depuis l'annuaire le reprenne ;
- le syslog (7200) et le sniffeur MQTT (7100) ne savent rien des lieux : un nom d'hôte (`CAPTEURS-CUVE`) ou un topic
  (`jardin/cuve`) ne dit pas où est la carte.

## 2. Objectifs, non-objectifs, anti-objectifs

Objectifs (choix de l'utilisateur du 2026-11-11) :
- Annuaire, modèle J : puces « Lieu de travail » ; chaque « Ouvrir ↗ » d'un outil qui sait l'utiliser porte `?lieu=`.
- À l'arrivée sur une page avec `?lieu=` : **mettre en avant**, jamais cacher ni cocher.
- Syslog, modèle M : puces de lieu (filtre, lignes et erreurs par lieu), étiquette de lieu sur chaque ligne.
- Sniffeur MQTT, modèles N et O : puces de lieu (filtre d'affichage) et étiquette sur chaque message ; arborescence
  rangée par lieu ; listes « module » des panneaux Logs et Commande groupées par lieu.

Non-objectifs :
- Modèle K (fiches par carte dans l'annuaire), modèle L (barre des modules du syslog rangée par lieu) : écartés.
- Lieu transmis d'une page de maintenance à une autre : les liens existants portent déjà la carte (`?env=` de la page
  Build vers 7800, de l'atelier vers 7700), qui donne son lieu (décision de Claude).
- Sniffeur ModBus, I2C, testeur UDP, pont série, synchro du fork : aucun changement.
- Pas de table hôte → lieu ou topic → lieu écrite à la main ni stockée (voir §3).

Anti-objectifs :
- Un `?lieu=` coche, décoche, change un port, une IP, ou bascule une page en mode modification (assistant 7900).
- Une page ouverte sans `?lieu=` (à la main, favori) change de comportement.
- Le classement Lieu imposé par `?lieu=` remplace le classement mémorisé de la page Build (il vaut pour la visite).
- Un filtre de lieu du sniffeur MQTT change les abonnements au broker.
- Le lieu se déclare à un nouvel endroit : la seule table reste `lieux.LIEUX`.

## 3. Identité d'une carte : nom d'hôte, IP, topic

Le `_persist.json` de chaque carte porte `serveur.hostname` (le « module » d'une ligne syslog) et `serveur.mqtt.topic`
(lus aujourd'hui par `build_ota_fs.py::_identite`). Le nom d'env donne le lieu (`lieux.lieu`). Rien n'est à tenir à la
main.

Nouveau dans `lieux.py` : `identites(racine)` → liste de `{env, lieu, hote, topic, ip}` pour chaque carte (famille
`cartes` de `build_envs.liste_envs`), persist lu par `build_envs.persist_carte`, `ip` = `Env.ip` seulement si `Env.ip_source == "h"` (WIFI_IP_ADDRESS du
`.h`) : pour un esclave du range extender, `Env.ip` vaut `<ip du maître>:<port>` (`build_envs.py::adresse_par_maitre`),
qui n'identifie pas la carte ; `ip` vaut alors "" (décision de Claude, relevée par la relecture). Persist absent ou illisible : `hote` et `topic` vides (la carte reste reconnue par son IP). Banc dans
`test_lieux.py` : sur le vrai dépôt, la cuve donne `CAPTEURS-CUVE`, `jardin/cuve`, lieu `garage`.

Correspondance, faite dans le navigateur par deux fonctions ajoutées à `lieux.JS` (une seule implémentation pour les deux
pages) :
- `lieuDeHote(module, ipSource, cartes)` : égalité sans casse du `module` (nom d'hôte de la ligne) avec `hote`, sinon
  égalité de l'IP source du datagramme (`fiche["ip"]` de `syslog_tasmota.py::analyse`, `ip` de `/modules`) avec `ip` ;
  sinon `null` (« Autres »). Le nom d'hôte passe d'abord : un esclave derrière le NAPT arrive avec l'IP du maître mais
  avec son propre nom d'hôte. Les deux cartes sans persist (`tasmota32-rdc-vr-porte`, `tasmota-pompe-piscine`) ne sont
  reconnues que par l'IP source (décision de Claude, relevée par la relecture).
  Deux cartes au même nom d'hôte (`SERVEUR-RLY-CAVE`, `SERVEUR-GARAGE`) ont le même lieu : pas d'ambiguïté aujourd'hui ;
  si deux lieux différents partageaient un hôte, le premier dans l'ordre des envs gagne (décision de Claude, à signaler
  au banc par un avertissement côté Python).
- `lieuDeTopic(topic, cartes)` : premier segment retiré (`tele`, `stat`, `cmnd`, `fsmqtt`…), puis le `topic` de carte le
  plus long qui égale le reste ou en est un préfixe suivi de `/` (`garage/niveau/STATE` va à `garage/niveau`, pas à
  `garage`) ; sinon `null`. Les listes `#logModule` et `#cmdModule` portent des topics nus (`garage/niveau`) : pour
  elles, comparaison sans retirer de segment (option de la fonction ou seconde fonction : laissé au constructeur).

Routes : `GET /lieux` ajoutée au syslog (`syslog_tasmota.py`) et au sniffeur MQTT (`sniffeur_mqtt.py`) →
`{"lieux": [[code, libellé], ...], "cartes": identites(racine)}`. Lecture seule, même contrôle d'accès que les autres GET.
L'annuaire reçoit le nombre de cartes par lieu par la même voie (route `GET /lieux` ou ajout à une réponse existante :
laissé au constructeur).

## 4. Annuaire : modèle J

- Sous le titre, une rangée « Lieu de travail » : `Tous`, puis une puce par lieu de la table avec son nombre d'envs de cartes (deux envs
  pour une même carte physique comptent deux, comme dans la page Build) ;
  pas de puce « Autres ». Le choix est gardé dans `localStorage` (try/catch) ; première visite = Tous.
- Outils qui reçoivent `?lieu=` : Build (7700), Fichiers Berry (7800), Assistant persist (7900), Atelier (7950),
  Fabrique (7980), syslog (7200), sniffeur MQTT (7100). Marque portée par le registre (`annuaire_registre.py`, champ
  booléen de `Outil`) plutôt qu'une liste dans le JS (décision de Claude). Les autres tuiles ne changent pas.
- Le lien « Ouvrir ↗ » d'un outil marqué reçoit `lieu=<code>` (`?` ou `&` selon que le lien porte déjà `?jeton=`) ;
  `Tous` = lien inchangé. Le lien affiché change dès qu'on change de puce, sans recharger.
- `annuaire_page.py` fait 468 lignes : le code de la rangée va dans un module neuf `annuaire_page_lieux.py`, branché
  comme les autres modules de page.

## 5. Arrivée sur une page avec `?lieu=`

Commun, dans `lieux.JS` : `lieuDemande(lieux)` lit `?lieu=` et ne le rend que s'il est un code de la table (sinon
`null`, la page fait comme sans paramètre). Le lieu ne joue qu'au PREMIER chargement de la page : un rechargement de
liste plus tard (7800 rappelle `chargeEnvs` après une création, un renommage, une suppression) ne le réapplique pas ; `bandeauLieu(conteneur, libellé, surFermeture)` pose le bandeau
« Lieu : Garage (depuis l'annuaire) · Tous les lieux ✕ » (texte par `textContent`, couleurs par variables). « ✕ » retire
`lieu` de l'adresse (`history.replaceState`) et le bandeau, sans rechargement. Il ne change AUCUNE liste ni carte
choisie (revenir en arrière relancerait `choisitEnv` de l'atelier ou `chargeEtat` de 7800 et pourrait perdre un travail
non écrit) ; seule exception, la page Build revient à son classement mémorisé (dessin seulement, l'état vit dans `choix`).
Décision de Claude, relevée par la relecture.

Par page :

| Page | Effet de `?lieu=garage` |
|---|---|
| Build, onglet Build | Classement Lieu pour cette visite (le classement mémorisé n'est pas réécrit) ; groupe Garage ouvert, les autres groupes de lieu fermés (leur compteur « (n · m cochés) » reste visible) ; défilement jusqu'au groupe. « ✕ » : retour au classement mémorisé, règle d'ouverture habituelle. |
| Build, onglet Fichiers | Si aucune carte n'est choisie et que la page n'arrive pas de l'atelier (`?env=` gagne) : 1re carte du lieu choisie. |
| Build, Mémoire et Sauvegarde | Valeur initiale de la liste : la 1re carte cochée du lieu, sinon la 1re carte du lieu (au lieu de la 1re carte cochée tout court). |
| Fichiers Berry (7800) | `#env` initial = 1re carte du lieu, sauf `?env=` qui gagne. `c-modele` et `c-base` inchangés. |
| Assistant persist (7900) | Bandeau seul : `#f-env` et `#a-env` restent sur leur option de tête (choisir une carte fait passer en modification ou lit un fichier : geste à laisser à l'utilisateur, décision de Claude). |
| Atelier (7950) | `#env` initial = 1re carte S3/P4 du lieu, sauf `?env=` ; lieu sans carte S3/P4 : liste inchangée, bandeau « aucune carte de ce lieu ici ». |
| Fabrique (7980) | Bandeau seul : `#e-carte` reste sur « (choisir une carte) » (destination d'un envoi : geste explicite). |
| Syslog (7200) | Puce du lieu active (§6). |
| Sniffeur MQTT (7100) | Puce du lieu active dans les messages (§7). |

## 6. Syslog : modèle M

- Une rangée de puces entre la barre et la barre des modules : `Lieu`, `Tous`, une puce par lieu de la table, puis
  `Autres`. Chaque puce : nombre de lignes reçues depuis l'ouverture de la page, et nombre d'erreurs (sévérité 3 ou
  moins) en rouge s'il y en a. Lieu sans ligne : puce affichée, compteur 0.
- Un clic choisit le lieu (un seul à la fois, `Tous` = sans filtre). Le lieu choisi n'est PAS mémorisé d'une visite à
  l'autre : une page ouverte sans `?lieu=` démarre sur `Tous`, pour qu'aucune erreur d'une autre carte ne soit masquée
  à l'insu de l'utilisateur ; `?lieu=` règle la puce pour la visite (décision de Claude ; vaut aussi pour le sniffeur MQTT). Le filtre s'ajoute aux filtres existants (module,
  sévérités, texte) ; la barre des modules ne montre plus que les modules du lieu ; « Autres » = modules sans lieu.
- Chaque ligne affichée commence par une étiquette du lieu (libellé de la table, ou « Autres »).
- La pause, l'export, le journal disque et `/modules` ne changent pas. La table des cartes est chargée une fois
  (`GET /lieux`) ; échec de chargement : pas de puces, page d'aujourd'hui.

## 7. Sniffeur MQTT : modèles N et O

- Vue des messages (O) : rangée de puces `Lieu`, `Tous`, lieux, `Autres`, avec le nombre de messages reçus. Filtre
  d'affichage seulement (les abonnements ne bougent pas), combiné au filtre texte et aux favoris ; étiquette de lieu en
  tête de chaque message.
- Arborescence (N) : premier niveau = le lieu (ordre de la table, « Autres » en dernier), puis l'arbre d'aujourd'hui des
  topics de ce lieu ; un topic de carte affiche son env entre parenthèses ; ouverture des nœuds gardée comme
  aujourd'hui, en mémoire le temps de la page (`Set` `arbreOuvert` de `sniffeur_mqtt_panneaux.py::dessineArbre`, clé de
  chemin préfixée du lieu) ; clic sur un topic = filtre, comme aujourd'hui.
- Listes `#logModule` et `#cmdModule` : un `<optgroup>` par lieu, comme le modèle H (leurs valeurs ne changent pas).
- `sniffeur_mqtt_web.py` (287 lignes) et `sniffeur_mqtt_panneaux.py` (186) peuvent grandir sous 500 lignes ; au-delà, un
  module voisin.

## 8. Contraintes

- XSS : nom d'hôte, topic, payload et libellés posés par `textContent` ou propriétés ; les deux pages construisent
  aujourd'hui des lignes par chaînes HTML échappées (`echappe`) : toute étiquette ajoutée passe par le même échappement.
- Thèmes : syslog et sniffeur MQTT ont leur palette propre (style terminal) ; les puces suivent cette palette.
- Bancs : `test_lieux.py` (identites), `test_annuaire*.py`, `test_syslog_acces.py`, `test_sniffeur_mqtt_acces.py` (la
  route `/lieux` sous le même contrôle d'accès), et les sondes de pages existantes (Build, Fichiers, Mémoire, Sauvegarde,
  7800, 7900, 7950, 7980) qui doivent rester vertes. Nouvelles sondes Chrome : annuaire (puces, lien `?lieu=`, mémoire),
  syslog (lignes injectées par un faux émetteur UDP vers un port de test, puces, compteurs, étiquettes, `?lieu=`), sniffeur
  MQTT (messages injectés sans broker réel si le serveur le permet, sinon `/flux` simulé ; puces, arborescence,
  `?lieu=`). Une vérification `?lieu=` par page de maintenance, ajoutée à sa sonde. Bancs avec le Python de PlatformIO.
- Aucune émission vers un vrai broker ni vers le vrai syslog pendant les sondes ; aucun build PlatformIO.
- Relecture `relecteur-pages-web` avant le dernier commit. Mode d'emploi : une phrase par page dans
  `outils_docs/README.md`.

## 9. Laissé au constructeur

Découpage en commits, noms des fonctions et des modules neufs, voie exacte du compte de cartes par lieu vers
l'annuaire, place exacte du bandeau dans chaque page, texte des info-bulles, moyen d'injecter des messages dans les
sondes du syslog et du sniffeur MQTT.
