# Annuaire des outils PC — design

Date : 2026-10-17
Statut : relu (contrôle constructeur fait), en attente de validation, non implémenté

## Intention

Les outils PC du dépôt (pont série, sniffeurs ModBus et MQTT, serveur syslog, testeur UDP, synchro du
fork) ont chacun leur page web, leur port, leur tâche VS Code et leur cible PlatformIO « Custom ». Pour
en lancer un, il faut se souvenir de son nom, le chercher dans `Run Task` ou dans le groupe Custom d'un
env, puis retrouver son port. L'annuaire est **une page d'accueil unique** qui montre lesquels tournent,
emmène sur leur page, permet de les lancer et de les arrêter, et explique leur usage — depuis ce PC
**et depuis le téléphone** (au garage, sur le Wi-Fi maison).

## Objectifs

1. Une page, deux onglets : **Outils** et **Aide**.
2. Onglet Outils : des **tuiles groupées par usage** (maquette « option A » retenue) :
   - *Bus et cartes* : pont série, sniffeur ModBus, testeur UDP ;
   - *Réseau et journaux* : sniffeur MQTT, serveur syslog ;
   - *Maintenance* : synchro du fork.
   Chaque tuile : nom, une ligne d'intérêt, pastille d'état (vert = en marche, gris = arrêté,
   orange = bloqué, p. ex. port COM tenu par un autre outil), port, heure de démarrage, et les boutons :
   - **Ouvrir ↗** si l'outil tourne (nouvel onglet, lien muni du jeton depuis un autre appareil) ;
   - **Lancer** s'il est arrêté ;
   - **Arrêter** seulement s'il a été lancé **par l'annuaire** ; sinon la mention « lancé ailleurs ».
3. **Lancer** :
   - outil sans port COM (MQTT, syslog, synchro) : lancement direct ;
   - outil avec port COM (pont série, sniffeur ModBus, testeur UDP) : une **petite fenêtre** pré-remplie
     avec les réglages habituels, à vérifier avant de confirmer.
4. **Depuis un autre appareil** (téléphone) : mêmes droits que sur ce PC — voir, ouvrir, lancer, arrêter.
5. Onglet **Aide** : usage de la page ; comment lancer un outil ; l'intérêt de chaque outil ; les
   paramètres utilisés par chacun ; comment arrêter un outil ; où trouver les journaux.
6. Démarrage **avec VS Code** (à l'ouverture du dossier), arrêt à sa fermeture. La page s'ouvre dans le
   navigateur à chaque ouverture de VS Code (révisé le 2026-10-17 à la demande de l'utilisateur ; la
   version initiale ne l'ouvrait pas).

## Non-objectifs

- Remplacer les pages des outils : l'annuaire ne fait que les lister, les lancer, les arrêter.
- Démarrer avec la session Windows ou tourner VS Code fermé (choix de l'utilisateur : avec VS Code ;
  les outils lancés par l'annuaire s'arrêtent avec lui, sauf la synchro du fork).
- Arrêter un outil lancé ailleurs (tâche VS Code, cible Custom, terminal).
- Supprimer les tâches VS Code ou les cibles Custom existantes : elles restent.

## Anti-objectifs (échec même si « ça marche »)

- **Lancer un outil par `pio run`** (cible Custom). Un `pio run` pendant un build peut supprimer tout
  `.pio/build` (CLAUDE.md, « Vigilances de build », piège du 2026-10-10) et réécrire `modules.h`.
  L'annuaire lance **toujours** `python <script>` directement, comme les tâches VS Code.
- Un démarrage automatique qui **fait du bruit** : erreur de port occupé quand une deuxième fenêtre
  VS Code s'ouvre sur le dépôt, terminal qui vole le focus.
- Un processus qui **consomme** au repos (cible mesurée : un serveur `http.server` Python au repos
  = 12,7 Mo privés, 0 s de CPU sur 15 s). Pas de sondage quand aucune page n'est ouverte.
- Une Aide qui **dérive** du réel (paramètres ou ports périmés).
- Un accès réseau **sans jeton**, ou un jeton/mot de passe écrit dans le dépôt.
- Un processus orphelin après « Arrêter ».

## Contraintes du dépôt

- Code Python sous `outils_docs/scripts_python/outils_pc/` (les outils s'importent entre eux, règle
  « même dossier » de CLAUDE.md). Fichiers < 500 lignes.
- Accès web : réutiliser `outils_pc/acces_web.py` (`AccesWeb`, `ajoute_options` : `--local`,
  `--sans-navigateur`). Depuis ce PC : sans jeton (en-tête `X-...` + origine). Depuis un autre appareil :
  jeton tiré au lancement (`acces_web.py:79`), cookie HttpOnly SameSite=Strict, un nom par port.
- Python lancé : celui du penv PlatformIO, comme les tâches existantes. Sous Windows, le `python.exe`
  du venv est un **lanceur qui crée un processus enfant** (mesuré : PID lanceur + PID python réel) :
  « Arrêter » doit tuer l'**arbre** de processus (`taskkill /T` ou équivalent), sinon l'outil survit.
- `.vscode/tasks.json` : ajouter la tâche ici (fichier propre au fork, absent de l'amont ; suivi par
  `git add -f`). **Ne jamais toucher `.vscode/settings.json`.** Chemin d'exécutable : `${env:USERPROFILE}`
  ou `${workspaceFolder}`, jamais `${userHome}` (leçon du 2026-10-13) ; la tâche se lance au moins une
  fois avant d'être annoncée.
- Page vérifiée **dans un vrai navigateur** avant d'être annoncée (leçons du 2026-10-16 et 2026-10-17 :
  Chrome piloté par DevTools, flux SSE compris ; un HTTP 200 ne prouve rien).
- Ne pas lancer de banc ni d'outil qui écrit dans `lib/libesp32/berry_custom` pendant un build.

## Décisions de conception

### Une fiche par outil, source unique

Un registre Python (une fiche par outil) porte : identifiant, nom, groupe, intérêt (une ligne), texte
d'aide, script, port de page par défaut, option du port de page, paramètres de lancement (nom, option
CLI, défaut, s'il s'agit d'un port COM, option `custom_*` du `.ini` qui le fixe), ressource tenue
(port COM, UDP 514, multicast 224.3.0.1:4000), emplacement des journaux. **Les tuiles et l'onglet Aide
sont générés depuis ce registre** : ajouter un outil = ajouter sa fiche.

Relevé des 6 outils (argparse et cibles Custom actuels) :

| Outil | Script | Page | Paramètres de lancement (défaut) | `.ini` lu par la cible Custom |
|---|---|---|---|---|
| Pont série | `outils_pc/pont_serie.py` | TCP+HTTP 7000 | `--port auto`, `--vitesse 115200`, `--tcp 7000`, `--journal` | `monitor_port`/`upload_port`, `monitor_speed`, `custom_pont_tcp` |
| Sniffeur ModBus | `outils_pc/sniffeur_modbus.py` | 7300 | `--port auto` (seul CH343), `--debit 19200`, `--http 7300` | `custom_sniffeur_modbus_port`, `_debit`, `_http` |
| Testeur UDP | `outils_pc/testeur_udp.py` | 7400 | `--port-maitre`, `--port-esclave` (vides = fermés), `--vitesse 115200`, `--http 7400` | `custom_testeur_udp_port_maitre`, `_port_esclave`, `_http` |
| Sniffeur MQTT | `outils_pc/sniffeur_mqtt.py` | 7100 | `--http 7100` ; broker lu par l'outil dans `user_config_override.h` | `custom_sniffeur_http` |
| Serveur syslog | `outils_pc/syslog_tasmota.py` | 7200 | `--port 514` (UDP), `--http 7200` | `custom_syslog_http` |
| Synchro du fork | `maintenance/synchro_fork_web.py` | 7500 | `--http 7500` | `custom_synchro_fork_http` |

L'annuaire **ne passe jamais** `--mot-de-passe` ni `--utilisateur` au sniffeur MQTT : l'outil les lit
lui-même. Aucun secret ne transite par l'annuaire ni par sa page.

### Savoir qui tourne : la fiche de présence

Modification de `acces_web.py`, module commun à tous les outils : au démarrage du serveur, l'outil
écrit une **fiche de présence** dans un dossier propre au compte Windows, **hors dépôt**
(`%LOCALAPPDATA%\outils_tasmota\presence\<port>.json`) : nom de l'outil, port, PID, heure de démarrage,
jeton. Il l'efface à l'arrêt (sortie normale, Ctrl+C, `atexit`).

L'annuaire lit ces fiches et **contrôle** chacune : PID vivant **et** port qui répond. Une fiche dont
le PID est mort est périmée (arrêt brutal) : ignorée et supprimée. Un port qui répond sans fiche
(ancienne version d'un outil) : « en marche », sans lien jeton depuis le téléphone.

Effet : l'état et le lien muni du jeton sont connus **quelle que soit la voie de lancement** (annuaire,
tâche VS Code, cible Custom, terminal).

### État « bloqué » (orange)

Un outil arrêté est orange si une ressource dont il a besoin est déjà tenue par un outil en marche
(d'après les fiches de présence et les paramètres de lancement connus), ou si son port de page est
occupé par autre chose. La tuile dit pourquoi (« COM3 tenu par le pont série »). « Lancer » reste
possible : la fenêtre de lancement permet de choisir un autre port.

### La fenêtre de lancement (outils à port COM)

Constat (vérifié le 2026-10-17) : **aucun `.ini` ne définit d'option `custom_*`** des outils ; les
cibles Custom tournent sur leurs défauts, et ces options se lisent par env, notion absente de
l'annuaire. L'annuaire **ne lit donc pas les `.ini`**. Pré-remplissage : les **dernières valeurs
lancées depuis l'annuaire** pour cet outil (mémorisées hors dépôt, à côté des fiches de présence),
sinon les défauts de l'outil (tableau ci-dessus).

La liste des ports série nomme le matériel (« COM7 — CH343 ») et marque un port tenu par un outil en
marche. Pour le testeur UDP, si le pont série tourne, la liste propose aussi `pont:<port>` (sa valeur
documentée) ; ce choix ne compte pas comme « COM tenu ».

**Validation stricte côté serveur** (la page est utilisable depuis le téléphone) : un port série doit
appartenir à la liste détectée (ou `auto`, ou `pont:<port>` d'un pont en marche) ; débits et ports
HTTP sont des entiers bornés (débits pris dans une liste fixe) ; aucun autre argument n'est accepté ;
la commande est une liste d'arguments, jamais une chaîne passée à un shell.

### Lancer, arrêter, console

- Lancement : `python -u <script> <paramètres> --sans-navigateur`, `cwd` = racine du dépôt,
  `PYTHONUTF8=1` (comme `tasks.json`).
- L'annuaire garde la sortie console de chaque outil qu'il a lancé : un lien **« console »** sur la
  tuile affiche les dernières lignes. C'est la seule console visible depuis le téléphone.
- « Arrêter » : arbre de processus tué (voir Contraintes), puis la fiche de présence disparaît.
- **Synchro du fork** : « Arrêter » est **refusé** tant qu'une opération (merge, rebase, push) tourne
  dans son processus enfant (`synchro_fork_session.py:76`) — un merge tué en plein vol laisse un
  `MERGE_HEAD` et un index à moitié écrit (CLAUDE.md, « Synchro du fork »). `synchro_fork_web` doit
  exposer cet état (à ajouter s'il n'existe pas).
- Un outil lancé par l'annuaire le note dans sa fiche de présence (variable d'environnement posée par
  l'annuaire, lue par `acces_web`) : un annuaire redémarré **retrouve** les outils qu'il avait lancés
  et garde leur bouton « Arrêter ». La console, elle, n'est conservée que pour les outils lancés depuis
  le démarrage courant de l'annuaire.
- **À la fermeture de VS Code, les outils lancés par l'annuaire s'arrêtent avec lui** (décision de
  l'utilisateur). VS Code tue souvent ses tâches sans laisser `atexit` s'exécuter : la garantie passe
  par un **Job Object** Windows (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, via `ctypes`) auquel l'annuaire
  rattache chaque outil qu'il lance ; la mort de l'annuaire, même brutale, emporte tout l'arbre.
  **Exception : la synchro du fork** est lancée **hors** du Job Object, pour qu'aucune fermeture ne
  coupe un merge ; elle survit donc à VS Code, et l'annuaire la retrouve à son prochain démarrage.
  Témoin obligatoire au banc : tuer l'annuaire par `taskkill /F` et vérifier que l'outil lancé est mort
  (et que la synchro, elle, tourne encore).

### Accès depuis un autre appareil

L'annuaire est un serveur `acces_web` comme les autres : écoute sur tout le réseau, jeton obligatoire
depuis un autre appareil. Son jeton est donné par le lien de sa console **et par un encadré « depuis
un autre appareil »** de la page ouverte sur le PC (lien copiable). Pas de QR code en v1 : la
bibliothèque standard n'en génère pas, `qrcode` imposerait de modifier le penv PlatformIO, et une lib
JS par CDN échouerait hors Internet ; à ajouter plus tard si le besoin se confirme. Le jeton change à
chaque démarrage (donc à chaque ouverture de VS Code).

Fiche de présence d'un outil lancé en `--local` : sans jeton, et la tuile n'offre pas « Ouvrir ↗ »
depuis le téléphone. Le pont série n'a qu'**un** serveur `acces_web` sur son port 7000 (TCP brut et
HTTP partagent ce numéro) : une seule fiche. Depuis le téléphone, « Ouvrir ↗ » construit `http://<IP du PC>:<port>/?jeton=<jeton>`
d'après la fiche de présence de l'outil. Le premier lancement demandera d'autoriser Python dans le
pare-feu Windows (réseaux privés), comme pour les autres outils.

### Démarrage avec VS Code

Une tâche « Outil : annuaire des outils (http://127.0.0.1:7600) » dans `.vscode/tasks.json`, avec
`runOptions.runOn = folderOpen`, `presentation.reveal = never` (même modèle que la surveillance Berry).
Lancée **sans** `--sans-navigateur` : la page s'ouvre (révisé le 2026-10-17). Port **7600** (libre ; les
outils occupent 7000 à 7500). Si le port est déjà tenu par un annuaire (deuxième fenêtre VS Code, cible
Custom), le second ouvre seulement la page puis sort en **code 0** ; avec `--sans-navigateur`, il sort sans rien.
Lancée par le `python.exe` du penv PlatformIO (comme les tâches des outils PC : pyserial y est) ; si
pyserial manque, l'annuaire démarre quand même, sans liste de ports (champ libre, validé `COM\d+`).

### Rafraîchissement

L'état est recalculé à la demande de la page (toutes les ~3 s, seulement pendant qu'une page est
ouverte). Au repos, aucune page ouverte : aucun travail.

## Laissé au constructeur

- Découpage en modules (serveur, registre, page HTML/JS, Aide), dans la limite des 500 lignes.
- Forme exacte de la fiche de présence et de la lecture des `.ini` (`configparser` en lecture seule).
- Détection « port qui répond » (connexion TCP courte suffit).
- Style de la page, cohérent avec les pages d'outils existantes.
- Banc de test à la manière de `test_testeur_udp.py` : registre, fiches de présence (vivante, périmée,
  absente), lancement/arrêt d'un faux outil avec **témoin** (un arbre non tué doit être détecté),
  contrôle d'accès (PC sans jeton, autre appareil sans jeton refusé), double démarrage (sortie 0).

## Choix de conception (pris par Claude, à vérifier)

- Fiche de présence écrite par `acces_web.py` dans `%LOCALAPPDATA%\outils_tasmota\presence\`.
- Port 7600.
- Lien « console » sur la tuile.
- Pas de QR code en v1 ; lien copiable à la place.
- Pas de lecture des `.ini` ; pré-remplissage = dernières valeurs lancées, sinon défauts.
- Validation stricte des paramètres de lancement (liste blanche).
- « Arrêter » refusé pendant une opération de la synchro du fork.
- L'annuaire retrouve, après redémarrage, les outils qu'il avait lancés (en pratique : la synchro).
- Synchro du fork hors du Job Object.
- Rafraîchissement ~3 s, seulement page ouverte.
