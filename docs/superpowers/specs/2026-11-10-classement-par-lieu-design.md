# Classement des cartes par lieu dans les pages des outils PC

Date : 2026-11-10. Maquettes et choix : `outils_docs/filtre_lieu/` (README, `maquettes_filtre_lieu.html`, `modele-A.png`
à `modele-I.png`).

## 1. Intention

Le parc compte 11 cartes réparties dans six lieux de la maison. Les pages des outils PC les listent à plat ou par
famille (« Mes cartes », « Mes bases », amont) : pour retrouver « les cartes du garage », il faut lire chaque nom d'env.
L'utilisateur veut pouvoir classer ces listes par emplacement dans la maison, sur la page Build d'abord, puis sur les
autres pages de l'annuaire qui font choisir une carte.

## 2. Objectifs, non-objectifs, anti-objectifs

Objectifs :
- Onglet Build de la page Build (7700) : bascule « Classer par » Famille / Lieu / Puce (modèle D).
- Onglet Fichiers de la page Build : intertitres de lieu dans la liste des cartes destinataires (modèle F).
- Listes déroulantes de carte des autres pages : un `<optgroup>` par lieu (modèle H).
- Une seule table des lieux, partagée par toutes ces pages.

Non-objectifs :
- Onglet « Env par défaut » de la page Build : il reste classé par puce, comme le bloc `default_envs` du fichier.
- Syslog (7200), sniffeur MQTT (7100), sniffeur I2C (7350), sniffeur ModBus (7300), testeur UDP (7400), pont série
  (7000), synchro du fork (7500) : aucun changement (justification dans le README des maquettes).
- Pas de plan de la maison, pas de lieu transmis d'une page à l'autre, pas de filtre par lieu sur les bases ni sur
  l'amont.

Anti-objectifs (ce qui ferait échouer le travail même si « ça marche ») :
- Changer de classement modifie ce qui est coché, le choix COM/OTA, un port ou une IP saisis, ou ce qui part au
  lancement. Le classement est un affichage, jamais un état.
- Un env coché devient invisible sans que la page le dise.
- Le lieu se déclare à plusieurs endroits (un libellé dans chaque page).
- Un champ ajouté au cenv ou au `_persist.json` pour porter le lieu.

## 3. Source du lieu

Le lieu est le 2e segment du nom d'env, règle de `pre_utilitaires_platformio.py::transform_name` déjà recopiée dans
`fichiers_berry_etat.py::dossier_carte` : `tasmota32s3-garage-capteurs-cuve-modbus` donne `garage`.

Table décidée avec l'utilisateur (libellés et ordre validés le 2026-11-10) :

| Code | Libellé | Ordre |
|---|---|---|
| `etage2` | 2e étage | 1 |
| `rdc` | Rez-de-chaussée | 2 |
| `cave` | Cave | 3 |
| `garage` | Garage | 4 |
| `bureau` | Bureau | 5 |
| `exterieur` | Extérieur | 6 |

Exception unique : `tasmota-pompe-piscine` (ESP8266, sans dossier `data/`) donnerait « pompe » ; elle est rangée en
`exterieur` par une table d'exceptions nom d'env → lieu.

Un segment inconnu de la table (futur lieu non déclaré) : groupe « Autres », en dernier, libellé = le code brut. Les
bases (`fichiers_berry_etat.py::est_base`) et l'amont n'ont pas de lieu.

## 4. Le module partagé (décision de Claude)

Nouveau module `outils_docs/scripts_python/outils_pc/lieux.py` (même dossier que toutes les pages concernées : import
direct, règle du dépôt) :

- `LIEUX` : la table ci-dessus, liste ordonnée `(code, libellé)`.
- `EXCEPTIONS` : `{"tasmota-pompe-piscine": "exterieur"}`.
- `lieu(env)` : code du lieu d'une CARTE (famille `cartes` de `liste_envs`, ou env personnel non base). Le nom seul ne
  distingue pas l'amont (`tasmota-FR` donnerait `FR`) : les appelants ne l'appellent que sur les cartes, et elle rend
  `None` pour une base (`est_base`) ou un nom sans tiret.
- `puce(env)` : `ESP32`, `ESP32-S3`, `ESP32-P4` (`tasmota32p4` et `tasmota32p4r3`), `ESP8266` (préfixe `tasmota` seul),
  d'après le 1er segment. Sert à la page Build seulement ; `assistant_persist_parc.PREFIXES` (autres libellés) reste
  tel quel pour l'assistant (décision de Claude : ne pas toucher un module qui marche pour unifier deux libellés).
- `pour_page()` : `{"lieux": [[code, libellé], ...]}` à joindre aux réponses JSON, pour que le JavaScript n'ait aucun
  libellé en dur.

Banc `test_lieux.py` : les 11 cartes réelles du cenv (lu par `build_envs.liste_envs`) ont chacune un lieu de la table,
la piscine sort en `exterieur`, les 6 bases sortent `None`, un segment inconnu sort tel quel ; `puce()` sur les 11
cartes et les 6 bases.

Chaque serveur ajoute `lieu` (et `puce` pour la page Build) à chaque env qu'il sert, et `lieux` à la réponse. Routes
concernées : `build_web.py` `GET /envs`, `fichiers_berry_web.py` `GET /envs`, `assistant_persist_web.py` `GET /parc`,
`atelier_graphiques_web.py` `GET /envs`, `tapp_web.py` `GET /cartes`.

## 5. Onglet Build : modèle D

- Une barre au-dessus de la liste : « Classer par » [Famille | Lieu | Puce] (boutons segmentés, même style que le
  COM/OTA de chaque ligne), puis un champ « Filtrer par nom… ».
- **Famille** : la vue d'aujourd'hui, inchangée.
- **Lieu** : les cartes (famille `cartes`) en un groupe repliable `details` par lieu, dans l'ordre de la table, groupe
  « Autres » en dernier s'il existe ; puis « Mes bases » et « Tasmota (amont) » tels qu'aujourd'hui.
- **Puce** : les cartes en un groupe par puce (ESP32, ESP32-S3, ESP32-P4, ESP8266, groupes vides omis) ; puis « Mes
  bases » et l'amont tels qu'aujourd'hui.
- En-tête de chaque groupe de lieu ou de puce : une case qui coche ou décoche toutes les cartes VISIBLES du groupe
  (celles que le filtre par nom laisse voir) ; son état (cochée, décochée, à moitié `indeterminate`) se calcule sur ces
  mêmes cartes visibles, pour qu'aucun env ne soit coché à l'insu de l'utilisateur (décision de Claude) ; compteur au
  format actuel `(4 · 3 cochés)`, sur toutes les cartes du groupe. Cliquer la case ne replie ni ne déplie le groupe.
- Ouverture des groupes de lieu et de puce à l'arrivée (choix de l'utilisateur du 2026-11-10) : ouvert si le groupe
  contient une carte cochée, fermé sinon. Pas de mémoire d'ouverture d'une visite à l'autre. « Mes bases » et
  l'amont gardent leur règle d'aujourd'hui (`build_page.py` `FAMILLES` : bases toujours ouvertes, amont ouvert s'il
  contient un coché). En classement Famille, rien ne change.
- Les lignes `.env` sont les mêmes dans les trois classements. Redessiner la liste à la bascule est permis (décision de
  Claude) : `construitListe` la recrée déjà à chaque `chargeEnvs` et l'état (case, COM/OTA, port, IP, notes) vit dans
  `choix`, qui survit ; il suffit que la bascule passe par ce même chemin.
- Filtre par nom : sous-chaîne, sans casse, sur le nom d'env, dans les trois classements, bases et amont compris ;
  un groupe sans ligne visible est masqué. Un env coché masqué par le filtre : ligne d'avertissement orange sous la
  barre, « N envs cochés masqués par le filtre partiront au lancement » (modèle A, transposé).
- Le classement choisi est gardé dans `localStorage` (enveloppé de try/catch) ; première visite = Famille. Le filtre
  texte n'est pas gardé.
- Le compteur de « Lancer (N envs) » et la requête `POST /lancer` ne changent pas.

## 6. Onglet Fichiers : modèle F

Dans `build_page_fichiers.py::fichiersCartes` : la liste des cartes destinataires (radios `.f-carte`, IP sous le nom)
reçoit un intertitre par lieu (`LIBELLÉ · N`, petites capitales, couleur `--doux`), dans l'ordre de la table, « Autres »
en dernier. Aucun filtre, aucun clic de plus. La carte choisie, l'IP saisie et l'arrivée depuis l'atelier
(`build_page_atelier.py`, `?env=&depuis=atelier`) se comportent comme aujourd'hui.

## 7. Autres pages : modèle H

Chaque liste déroulante de carte devient : un `<optgroup label="Libellé">` par lieu, dans l'ordre de la table, puis
« Autres », puis le groupe « Mes bases » là où il existe déjà. Listes concernées :

| Page | Liste |
|---|---|
| Build, onglet Mémoire et partitions | `#m-env` (`build_page_memoire.py::mEnvs`) : aujourd'hui à plat, bases d'abord ; devient lieux puis un `<optgroup label="Mes bases">` en bas (décision de Claude, comme le modèle H) |
| Build, onglet Sauvegarde configuration | `#s-env` (`build_page_sauvegarde.py::sEnvs`) |
| Fichiers Berry (7800) | `#env` et `c-modele` (`fichiers_berry_page.py::chargeEnvs`), « Mes bases » gardé ; `c-base` (bases seules) inchangé |
| Assistant persist (7900) | `#f-env` (`dessineListeEnv`) et `#a-env` (onglet autoexec.bat) |
| Atelier des graphiques (7950) | `#env` (rempli en fin de `atelier_graphiques_page_js.py`) ; la carte du différentiel y est une carte comme les autres (rangée en Bureau) ; `#r-page` et son entrée « Énergie » ne bougent pas |
| Fabrique d'extensions (7980) | `#e-carte` (`tapp_page.py`) |

La valeur sélectionnée, l'ordre des cartes à l'intérieur d'un lieu (celui d'aujourd'hui) et le comportement au
changement ne bougent pas. `#f-maitre` de l'assistant (liste des maîtres) n'est pas touché.

## 8. Contraintes

- Fichiers à exception de taille : `build_page.py` (1223 lignes, exception assumée dans `CLAUDE.md`) ; le code du
  modèle D va dans un module neuf `build_page_lieux.py` (CSS + JS), branché dans `build_page.PAGE` comme les autres
  onglets ; la ligne de `CLAUDE.md` qui suit la taille de `build_page.py` est à mettre à jour s'il grandit.
- Thèmes clair et sombre (variables de `build_page.py`), sans couleur en dur.
- Bancs et sondes existants à garder verts : `test_build_page_chrome.py`, `test_build_page_fichiers_chrome.py`,
  `test_build_page_memoire_chrome.py`, `test_build_page_sauvegarde_chrome.py`, `test_fichiers_berry_page_chrome.py`,
  `test_assistant_persist_page_chrome.py`, `test_atelier_graphiques_page_chrome.py`, `test_tapp_page_chrome.py`, et les
  `test_*_web.py` des routes modifiées. Bancs Python avec le Python de PlatformIO.
- Nouvelle sonde Chrome pour le modèle D (bascule, case de lieu à moitié cochée, ligne déplacée qui garde son champ
  saisi, avertissement des cochés masqués, mémoire du classement), dans `test_build_page_chrome.py` ou une sonde voisine.
- Relecture `relecteur-pages-web` avant commit. Aucun build PlatformIO n'est nécessaire (outils PC seulement).
- Mode d'emploi : une ligne par page dans `outils_docs/README.md`, aux sections existantes.

## 9. Laissé au constructeur

Ordre des actions, découpage en commits, noms des fonctions JS, emplacement exact de la barre « Classer par » et du
champ de filtre, tri interne des groupes de puce, texte exact des info-bulles.
