# Page « Build et téléversement » — design

Date : 2026-10-24
Statut : relu (contrôle constructeur fait), en attente de validation, non implémenté

## Intention

Aujourd'hui, compiler ou téléverser une carte du parc passe par VS Code : choisir l'env dans la barre
PlatformIO, lancer la tâche, et pour l'OTA **éditer le `.ini`** (commenter `upload_port`, décommenter
`ota-files-uploader.py` et `custom_ota_files`). Enchaîner plusieurs cartes, l'une en OTA (le P4 au fond
du garage), les autres par câble (cuve, rideau sur le PC), demande de répéter ces manipulations et de
surveiller chaque build.

La nouvelle page fait tout cela d'un seul écran : on coche des environnements, on coche des actions, on
choisit COM ou OTA **ligne par ligne**, on lance ; la page enchaîne les `pio run` l'un après l'autre et
montre l'étape en cours, le pourcentage, les durées et les échecs. On y accède par une **tuile de
l'annuaire des outils** (http://127.0.0.1:7600).

## Objectifs

1. **Une tuile dans l'annuaire** qui mène à la page (même mécanique que les autres outils : registre,
   fiche de présence, lien « Ouvrir ↗ »).
2. **Liste de tous les environnements du dépôt**, classés (demande de l'utilisateur) en :
   - **environnements personnels** : ceux de `platformio_tasmota_cenv.ini` ;
   - **environnements de base de Tasmota** : ceux de l'amont (`platformio_tasmota_env32.ini`,
     `platformio_tasmota_env.ini`, ~106 envs : safeboot, `tasmota32*`, langues, ESP8266).
3. **Sélection multiple** : une case à cocher par environnement.
4. **Actions combinables** (une ou plusieurs à la fois, pour tous les environnements cochés) :
   - compiler le firmware ;
   - téléverser le firmware ;
   - construire le file system ;
   - téléverser le file system.
5. **Méthode d'envoi par environnement** (maquette « B » retenue par l'utilisateur) : sur chaque ligne,
   un interrupteur **COM / OTA**, avec le champ correspondant :
   - **port COM** : prérempli à l'ouverture de la page avec le `upload_port` lu dans le `.ini` de
     l'env (y compris hérité par `extends`) ; **vide** si l'env n'en a pas. Modifiable sur la page ;
     **une modification est réécrite dans la section `[env:…]` concernée du `.ini`** (décision de
     l'utilisateur : le `.ini` reste la référence, un `pio run` lancé depuis VS Code prend le même port) ;
   - **adresse IP (OTA)** : lue dans `WIFI_IP_ADDRESS` de `tasmota/user_config_override.h`, dans le
     bloc `#if/#elif defined(FIRMWARE_X)` du firmware de l'env (même lecture que
     `ota-files-uploader.py`, `_firmware_define` + `_lire_ip_override`).
6. **Téléversement du file system en OTA** (décision de l'utilisateur) : envoyer **tout** le contenu du
   file system de la carte, **`_persist.json` compris**, fichier par fichier par `/ufsu` (Tasmota
   n'accepte pas d'image LittleFS en OTA).
7. **Exécution en série** : les environnements cochés passent l'un après l'autre, jamais deux `pio` en
   même temps (contrainte PlatformIO et règle du dépôt).
8. **Suivi en direct** (demandes de l'utilisateur) :
   - **étape en cours** et **progression en %** pour chaque environnement ;
   - **durée de compilation** affichée **dès la fin** de la compilation de chaque env (puis durée du
     téléversement, durée totale) ;
   - **échec signalé à l'utilisateur** : bandeau rouge nommant l'env et l'étape, extrait de l'erreur,
     journal complet dépliable.

## Non-objectifs

- Remplacer VS Code / PlatformIO : la page lance les mêmes `pio run`, avec les mêmes pré-scripts.
- Modifier le contenu des envs (build_flags, modules Berry, `custom_*`) : seul `upload_port` est écrit.
- Moniteur série après téléversement (le pont série :7000 existe pour cela).
- Builds parallèles.

## Anti-objectifs (ce qui en ferait un échec même si ça « marche »)

- Lancer un `pio run` **pendant un autre build** (celui de l'utilisateur dans VS Code, ou une cible
  Custom) : deux `pio` qui écrivent `tasmota/tasmota.ino.cpp` se plantent, et un changement d'env purge
  `.pio/build` en plein build de l'autre (`CLAUDE.md`, « Vigilances de build »).
- Couper un téléversement en vol (carte à moitié flashée) parce que l'annuaire ou VS Code se ferme.
- Téléverser un firmware qui n'a pas compilé.
- En OTA, écraser le persist d'une carte **sans en garder une copie**, ou le voir réécrasé par l'ancien
  au redémarrage (piège consigné le 2026-10-18).
- Une action qui fait **plus** que ce qui est coché **sans le dire** (seule exception assumée : le
  téléversement série qui emporte `littlefs.bin`, choix 9, signalé sur la ligne).
- Annoncer la page prête sans l'avoir exécutée dans un vrai navigateur (leçon du 2026-10-16).

## Contraintes (mesurées par la reconnaissance du 2026-10-24)

### Ce que fait chaque `pio run` du dépôt

Tout `pio run` (build, upload, buildfs, uploadfs) d'un env personnel passe par
`outils_docs/scripts_python/build/pre_utilitaires_platformio.py`, qui :

- réécrit `platformio_override.ini` (`[platformio] data_dir`, déduit du nom de l'env par
  `transform_name`) et incrémente `CFG_HOLDER` dans `tasmota/user_config_override.h` ;
- copie temporairement `data/fs/*`, `data/json`, `data/sd` dans `data/<lieu>/<type>-<reste>` avant
  `buildfs`/`upload`, et les retire par `atexit` — **un `pio` tué par `taskkill /F` laisse ces copies**.

### Empreinte du projet et purge de `.pio/build`

`compute_project_checksum` (PlatformIO, `project/helpers.py:131-175`) inclut `config.to_json()` : **le
contenu de tous les `.ini`**. Si l'empreinte change, `run/helpers.py:35-50` supprime **tout**
`.pio/build`, tous envs compris.

- Construire l'env A puis l'env B change `data_dir`, donc purge : dans une série multi-envs, chaque env
  est reconstruit à fond (déjà le cas aujourd'hui).
- Réécrire `upload_port` dans le `.ini` (objectif 5) change aussi l'empreinte : le build suivant, même
  du même env, repartira de zéro. Coût accepté avec la décision de l'utilisateur ; la page le dit en une
  ligne à côté du champ quand on modifie un port.
- `--upload-port` / `-p` en ligne de commande **n'entre pas** dans l'empreinte. Les variables
  `PLATFORMIO_UPLOAD_PORT`, `PLATFORMIO_EXTRA_SCRIPTS`… **y entrent** : ne pas les utiliser.

### OTA

- L'OTA du firmware passe par `ota-files-uploader.py` (post-script) qui remplace `UPLOAD_PORT` par
  `<ip>:80/u2?fsz=` et `UPLOADCMD` par `pio-tools/espupload.py`. Il n'est activé que par `extra_scripts`
  dans le `.ini` (commenté partout aujourd'hui). `--upload-port <ip>` seul ne suffit pas (esptool serait
  lancé avec une IP en guise de port).
- `/ufsu` : `GET /ufsd` puis `POST http://<ip>/ufsu` multipart champ `ufsu`, en-tête
  `Referer: http://<ip>/` obligatoire (SetOption128=0) ; réponse toujours 200, succès jugé sur le texte.

### Divers

- Ports déjà pris : 7000 à 7600. **7700 est libre.**
- Plusieurs envs partagent un port (COM34 : 4 envs ; COM11 : 2 envs, dont un par héritage).
- Le pont série (:7000), le sniffeur ModBus et le testeur UDP peuvent **tenir un port COM** ; l'annuaire
  sait le détecter (`annuaire_presence.py`, `_com_tenu`).
- Détection d'un build en cours : logique de `.claude/hooks/garde_build.py` (`builds_en_cours()`,
  PowerShell `Get-CimInstance Win32_Process`, regex `pio|platformio … run`, ou `scons`).

## Décisions de l'utilisateur (telles qu'il les a prises)

| Sujet | Décision |
|---|---|
| Accès | Tuile dans l'annuaire des outils |
| Classement | Environnements de base de Tasmota / environnements personnels |
| Actions | Compiler, téléverser le firmware, construire le FS, téléverser le FS ; une ou plusieurs à la fois ; sur un ou plusieurs envs |
| Méthode d'envoi | Port COM ou OTA, choisie par l'utilisateur, **par environnement** (maquette B) |
| Port COM | Lu dans le `.ini` à l'ouverture ; vide si absent ; modifiable ; modification **réécrite dans l'env concerné** |
| IP OTA | Lue dans `WIFI_IP_ADDRESS` |
| FS en OTA | Tout le file system, `_persist.json` compris |
| Échec | L'utilisateur doit en être averti |
| Durées | Temps de compilation de chaque env dès la fin de celle-ci |
| Progression | Étape en cours et % sur la page |
| Téléversement série du firmware | Garde le comportement actuel : emporte aussi `littlefs.bin` s'il existe |

## Choix faits par Claude (à vérifier par l'utilisateur à la lecture)

1. **Outil autonome sur le port 7700**, script `outils_docs/scripts_python/outils_pc/build_web.py`
   (+ modules voisins), même squelette que `maintenance/synchro_fork_web.py` : `ThreadingHTTPServer`,
   `acces_web.Acces(port, local, nom)`, flux SSE `/flux` rejouable (`Last-Event-ID`), POST avec en-tête
   personnalisé + `origine_autorisee`. Nom d'accès identique dans le registre et dans `Acces(...)`.
   Nouvelle entrée `OUTILS` dans `annuaire_registre.py`, groupe **« Maintenance »**.
2. **Accès depuis un autre appareil** : mêmes droits que l'annuaire (jeton obligatoire, cookie
   HttpOnly), donc lancement possible depuis le téléphone.
3. **Ne meurt pas avec l'annuaire pendant un lancement** : `dans_job=False` et
   `route_occupe="/execution"` (modèle de la synchro du fork) ; l'annuaire refuse de l'arrêter tant
   qu'un lancement est en cours.
4. **Trois familles affichées** : *Mes cartes* (envs personnels dont le nom ne contient pas `-base`),
   *Mes bases* (`tasmota32-base`, `tasmota32s3-base-N16R8`, `tasmota32p4-base-*`), *Tasmota (amont)*,
   repliée par défaut, avec sous-groupes (safeboot, ESP32, langues, ESP8266). Les sections non-env
   (`[env:tasmota32_base]`, `[env:tasmota32_idf55_base]` de `platformio_override.ini`) sont des
   modèles hérités, pas des cibles : non listées.
5. **Envs amont** : pas de `upload_port` → champ vide ; un port saisi vaut **pour le lancement
   seulement** (passé par `--upload-port`), sans réécriture d'un fichier amont. Pas d'IP OTA connue →
   champ à remplir, pour le lancement seulement.
6. **IP à `0.0.0.0` (DHCP) ou absente** sur un env personnel : OTA impossible tel quel ; la ligne affiche
   un champ IP à saisir, valable pour ce lancement seulement (pas de réécriture de
   `user_config_override.h`). Lancement refusé pour cette ligne tant que le champ est vide.
7. **OTA du firmware faite par la page, sans toucher au `.ini` ni aux scripts de build** (révisé le
   2026-10-24 : la première version passait l'IP par une variable `TASMOTA_OTA_IP` lue par un
   pré-script ; la mise en œuvre a prouvé que `post_esp32.py` réécrase `UPLOADCMD` après tout script
   exécuté depuis un pré-script — ordre `builder/main.py:167/173/180` — donc impasse). La page lance
   `pio run -e X` (compilation), puis envoie elle-même `.pio/build/<env>/firmware.bin.gz` (seulement
   s'il n'est pas plus ancien que `firmware.bin`, sinon `firmware.bin`) : `GET /up` d'abord (sans lui,
   `/u2` répond « Successful » sans rien écrire), bascule safeboot si la carte en a un (`/u4`), puis
   `POST http://<ip>/u2?fsz=`, multipart champ `file`, `Referer: http://<ip>/` — le
   protocole de `pio-tools/espupload.py`, déjà utilisé par l'OTA actuelle du dépôt. Pourcentage =
   octets envoyés / taille ; succès prouvé par la version et la date de `Status 2` avant/après
   (retour de la carte attendu 90 s). Échec après la bascule : le message dit que la carte est restée
   en safeboot et qu'il faut renvoyer un firmware par `http://<ip>/up`. Pas d'OTA proposée pour les envs
   safeboot de l'amont. `pre_utilitaires_platformio.py` et `ota-files-uploader.py` ne sont pas
   modifiés.
8. **Ordre des actions dans un env** : compiler → téléverser le firmware → construire le FS → téléverser
   le FS, en ne lançant que les actions cochées. Un échec arrête **cet env** (étapes suivantes sautées et
   marquées « annulée ») ; **les autres envs continuent** (cartes indépendantes).
9. **Commandes par action** (PlatformIO natif, pas d'appel direct à esptool) :
   - compiler : `pio run -e X` ;
   - téléverser le firmware : `pio run -e X -t upload` (recompile si besoin — comportement natif ; si
     « compiler » est aussi coché, la compilation n'est pas lancée deux fois : seul `upload` part, et la
     page affiche ses étapes *Compilation* puis *Téléversement*) ;
   - construire le FS : `pio run -e X -t buildfs` ;
   - téléverser le FS par câble : `pio run -e X -t uploadfs` ; en OTA : voir le choix 10.
   **Fait mesuré** (révisé le 2026-10-24 à la relecture finale) : `pio-tools/post_esp32.py:419-440`
   ajoute `littlefs.bin` à la commande esptool d'un `upload` série dès que ce fichier existe dans
   `.pio/build/<env>/`, **et** `esp32_build_filesystem` (`post_esp32.py:139-245`, action post-link du
   firmware) le reconstruit à **chaque** édition des liens dès que `custom_files_upload` contient une
   entrée autre que `no_files` ; or `CFG_HOLDER` change à chaque `pio run`, donc le firmware est toujours
   relié. → pour un env ESP32 dont `custom_files_upload` résolu n'est ni vide ni `no_files` (cartes et
   bases personnelles), « téléverser le firmware » par câble **flashe aussi le FS (persist compris) à
   chaque upload par câble**, même après une purge de `.pio/build` (et non « si un `buildfs` a eu lieu »).
   Conduite retenue (**décision de l'utilisateur, 2026-10-24**) : **garder ce comportement** (firmware +
   file system). La page ne le masque pas : quand « téléverser le firmware » par câble est coché pour un
   tel env (champ `fs_avec_firmware` calculé par `build_envs` depuis les `.ini`, pas d'après la présence
   de `littlefs.bin`), la ligne affiche « le file system (persist compris) sera aussi flashé », et le
   panneau de suivi le redit au téléversement (ligne `post_esp32` « Utilisera une commande de
   téléchargement personnalisée… », lue seulement pour l'action upload par câble).
   L'OTA est proposée seulement pour les envs qui chargent `pre_utilitaires_platformio.py` (envs
   personnels ESP32 et envs amont qui étendent `[env:tasmota32_base]`, surchargé dans
   `platformio_override.ini`) ; ailleurs (ESP8266 notamment) l'interrupteur OTA est grisé. Si un
   pré-script ne peut pas reproduire le post-script `ota-files-uploader.py` (remplacement de `UPLOADCMD`
   après `post_esp32.py`), le constructeur le signale avant de coder.
10. **Téléversement du FS en OTA, déroulé** :
    1. construire le FS (`pio run -e X -t buildfs`) si ce n'est pas déjà une action cochée du même
       lancement ; le contenu envoyé est **celui de l'image `.pio/build/<env>/littlefs.bin`** que ce
       `buildfs` vient d'écrire (cible AlwaysBuild, `builder/main.py:1761-1765` de la plateforme) — celle
       qu'un `uploadfs` par câble flasherait : dossier de la carte + `data/fs`, `data/json`, `data/sd`, moins
       les exclus et les solidifiés. La page en extrait les fichiers dans un dossier temporaire avec
       littlefs-python (penv), aux paramètres de `build_fs_image` (`builder/main.py:549-560` : block_size
       4096, block_count = taille / 4096, name_max 64), par un montage explicite (une image vierge, tronquée
       ou écrite par `post_esp32` est refusée, jamais formatée en silence) ; `littlefs.bin` absent après le
       `buildfs` → échec, rien n'est envoyé. (Révisé le 2026-10-24 à la relecture finale : la première
       version envoyait `.pio/build/<env>/littlefs_data`, qui n'est **pas** produit par `buildfs` mais par
       `esp32_build_filesystem` de `post_esp32.py:139-180` après chaque édition des liens du firmware, n'est
       jamais vidé, et ne reçoit les copies de `data/` que pour buildfs/uploadfs/upload/erase_upload
       (`pre_utilitaires_platformio.py:520-524`) : il aurait porté les restes d'un ancien build.)
    2. **télécharger le `_persist.json` de la carte** et le ranger dans
       `%LOCALAPPDATA%\outils_tasmota\build\persist\<env>-<horodatage>.json` ;
    3. envoyer chaque fichier par `/ufsu`, sous-dossiers compris (`json/`, `sd/`…) ;
    4. relire le `_persist.json` de la carte et le comparer à celui envoyé ;
    5. recharger les globales : `Br import persist persist.load() serveur = persist.serveur diverses = persist.diverses modules = persist.modules drivers = persist.drivers` ;
    6. `Restart 1`, attendre le retour de la carte (`/cm?cmnd=Status`), relire son persist.
    Toute commande HTTP vers la carte porte `Referer: http://<ip>/`.
    En cas d'échec : persist de la carte impossible à télécharger (étape 2) → **rien n'est envoyé**, env
    en échec (garder une copie est un anti-objectif) ; relecture différente (étape 4, comparaison exacte
    des octets, faite avant le rechargement) → env en échec, **pas de restauration automatique**, le
    chemin de la sauvegarde est affiché ; carte pas revenue 90 s après `Restart 1` (délai de
    `ota-files-uploader.py`) → env en échec.
11. **Avant de lancer**, la page refuse (avec message) :
    - si un build tourne déjà (logique de `garde_build`) ;
    - pour une ligne COM avec une action d'envoi, si le port est tenu par un autre outil (pont série,
      sniffeur, testeur) ou absent ;
    - si deux lignes cochées **avec une action d'envoi par COM** ont le même port (une seule carte branchée
      par port) ; compiler seul plusieurs envs au port partagé reste permis.
    Le contrôle « build en cours » est **refait avant chaque env** : si un build est apparu ailleurs entre
    deux envs, la série se met en attente (« en attente : build en cours dans VS Code ») et reprend quand
    il est fini ; l'utilisateur peut arrêter.
12. **Progression** :
    - étapes affichées : *Pré-build* (pré-script, solidification Berry) → *Compilation* → *Édition des
      liens* → *Téléversement* (ou *Construction du FS* / *Envoi des fichiers*) ;
    - % de compilation = lignes `Compiling …` comptées / nombre de `.o` du dernier build réussi de cet env
      (mémorisé dans le dossier de données de l'outil ; ~1680 aujourd'hui) ; sans référence, afficher le
      compte sans % ;
    - % de téléversement série = celui d'esptool (`Writing at 0x… (NN %)`) ; OTA firmware : pas de % fourni
      par `espupload.py` → indéterminé ; envoi FS en OTA : fichiers envoyés / total ;
    - durées mesurées par la page (horloge locale), affichées à la fin de chaque étape.
13. **Arrêt** : un bouton « Arrêter après cet env » (propre) ; un arrêt immédiat existe mais avertit
    qu'il peut laisser une carte à moitié flashée et des copies temporaires dans `data/<lieu>/<carte>`.
    La page **ne nettoie pas** ces copies elle-même (risque d'effacer le travail de l'utilisateur) : elle
    les signale.
13 bis. **Écriture de `upload_port`** : seulement pour les envs de `platformio_tasmota_cenv.ini` ; refusée
    pendant un lancement ou un build ; sauvegarde `platformio_tasmota_cenv.ini.bak` avant chaque écriture ;
    la ligne est écrite **dans la section de l'env lui-même**, même si la valeur venait d'un `extends`
    (« synchronisation sur l'environnement concerné ») ; vider le champ **supprime la ligne active** de
    cette section (l'env retombe alors sur la valeur héritée, ou sur rien). Pas de détection d'un fichier
    ouvert et modifié dans VS Code (VS Code recharge seul un fichier non modifié).
14. **Journal** : sortie complète de chaque `pio run` gardée (codes ANSI retirés) dans
    `%LOCALAPPDATA%\outils_tasmota\build\journaux\`, dépliable sur la page ; derniers choix (envs cochés,
    méthodes, IP saisies) mémorisés dans ce même dossier, hors dépôt.
15. **Fichiers modifiés par un lancement** : chaque `pio run` réécrit `platformio_override.ini` et
    `user_config_override.h` (CFG_HOLDER) — comportement existant. La page le rappelle en fin de
    lancement (fichiers à commiter par l'utilisateur, cf. leçon du 2026-10-13).
16. **Exécution** : `pio` du penv (`%USERPROFILE%\.platformio\penv\Scripts\pio.exe`), `cwd` = racine du
    dépôt, `PYTHONIOENCODING=utf-8` et `PYTHONUTF8=1` (sinon la sortie est perdue sur le `✔` du
    pré-script). Arbre de processus tué par `taskkill /T /F /PID`.
17. Une tâche VS Code « Outil : build et téléversement (http://127.0.0.1:7700) » sur le modèle des
    autres. **Pas de cible PlatformIO Custom** (une cible est un `pio run` : elle ne peut pas piloter des
    `pio run`).

## Laissé au constructeur

- Découpage en modules (registre des envs, lecture/écriture du `.ini`, exécution, OTA, page), sans
  dépasser l'esprit de la règle des 500 lignes.
- Lecture des `.ini` : analyseur de PlatformIO ou `configparser` avec résolution d'`extends` ; l'écriture
  de `upload_port` doit **préserver** le reste du fichier (commentaires, alignement), modifier la ligne
  active de la section visée, ou l'ajouter s'il n'y en a pas (pas de décommentage d'une ligne `; upload_port`).
- Expressions exactes de suivi de la sortie pio — **à établir sur une vraie sortie** (aucun journal dans le
  dépôt) ; ignorer les codes ANSI.
- Création des sous-dossiers sur la carte avant `/ufsu` (mécanisme du gestionnaire de fichiers de Tasmota).
- Mise en page (s'inspirer des pages d'outils existantes ; maquettes de la conversation : liste à gauche,
  actions à droite, panneau de suivi par env avec barre de progression).
- Bancs : un banc Python sur le modèle de `test_annuaire.py` (pio simulé par un faux exécutable qui rejoue
  une sortie enregistrée, carte simulée pour `/ufsu`), mise à jour de `test_annuaire.py:43,181`, et une
  exécution réelle de la page dans Chrome (DevTools, flux SSE : leçon du 2026-10-17).
- Documentation : `CLAUDE.md` (carte des documents) et `outils_docs/README.md`.
