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
   - effacer la flash puis téléverser (`erase_upload`, ajout du 2026-10-25, voir plus bas) ;
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
  PowerShell `Get-CimInstance Win32_Process`, regex `pio|platformio … run`, ou `scons`). Révisé le 2026-10-25 :
  un `pio run` dont toutes les cibles sont des cibles d'outils (les `NOM_CIBLE` des `build/cible_*.py` : annuaire,
  pont série, sniffeurs, syslog, testeur UDP, synchro du fork, page de build), et son scons (cibles en fin de
  ligne), ne sont **pas** des builds : l'outil vit tant que la cible vit, la page l'aurait attendu sans fin
  (constaté avec `platformio.exe run --target annuaire`). `__idedata`, une cible mêlée ou un scons sans cible
  lisible restent des builds (banc `build/test_garde_build.py`). Révisé encore le 2026-10-25 : une cible d'outil
  qui **démarre** peut purger `.pio/build` (empreinte) dans ses premières secondes ; elle compte donc comme un
  build pendant ses **30 premières secondes** (âge du processus par `CreationDate` de `Win32_Process`, lu dans la
  même requête PowerShell ; âge inconnu → build), ignorée ensuite. Formes collées `-tupload` / `-eenv` reconnues.

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
    - ~~si deux lignes cochées **avec une action d'envoi par COM** ont le même port~~ : **révisé le 2026-10-25,
      pause au lieu du refus** (ci-dessous).
    Le contrôle « build en cours » est **refait avant chaque env** : si un build est apparu ailleurs entre
    deux envs, la série se met en attente (« en attente : build en cours dans VS Code ») et reprend quand
    il est fini ; l'utilisateur peut arrêter.
    **Pause « rebranchez la carte »** (amélioration du plan, 2026-10-25, remplace le refus « même port ») : le
    lancement est accepté quand deux lignes COM partagent un port. Pour un env dont un envoi COM (upload,
    erase_upload, uploadfs) passe par un port déjà servi par un env **précédent** de la série : la compilation (si
    cochée) se fait d'abord, en un `pio run` à part ; quand elle a réussi, l'envoi qui suit la pause part en
    **`-t nobuild -t upload`** (resp. `-t nobuild -t erase_upload`) : le pré-script incrémente `CFG_HOLDER` dans
    `user_config_override.h` (inclus partout) à chaque `pio run`, un `-t upload` seul recompilerait tout ; `nobuild`
    reprend `$BUILD_DIR/${PROGNAME}.bin` (`builder/main.py` de la plateforme espressif32) sans `ConvertInoToCpp`
    (`piobuild.py`). Compilation non cochée : `-t upload` normal. Juste avant son premier envoi COM, la série émet
    `attente_carte` (env, port, env précédent, actions déjà faites `fait`, message `erreur`), sous la même prise du
    verrou que la pose de la pause, et attend. La page affiche « Branchez la carte <env> sur <COMn> puis cliquez Continuer » avec
    **Continuer** et **Passer cet env** (`POST /continuer {env, choix}`, protégé comme `/arreter` ; refus si aucune
    pause ou autre env). Après une réponse acceptée, les deux boutons restent désactivés jusqu'à la suite
    (`reprise_carte` ou nouvelle `attente_carte`). Continuer : un build apparu pendant la pause est attendu, puis
    le port est revérifié ; absent ou tenu → **la pause reste ouverte** (nouvelle `attente_carte` avec le message
    « COM12 absent : rebranchez puis Continuer », ou tenu par un autre outil), l'utilisateur réessaie ou passe.
    Passer : actions restantes « annulée », env « passé », la série continue. Les deux arrêts et le Ctrl+C du
    serveur mettent fin à la pause (aucun envoi n'est en vol) : env « arrêté », rangé dans `arretes` (ni échec ni
    récapitulatif rouge pour ce seul motif). Si aucun env n'a abouti (tous passés), l'état de fin n'est pas le
    « terminé » vert. Le rejeu du flux remontre le bandeau tant que la pause dure. Les autres refus avant
    le lancement (port tenu, absent) restent.
12. **Progression** :
    - étapes affichées : *Pré-build* (pré-script, solidification Berry) → *Compilation* → *Édition des
      liens* → *Téléversement* (ou *Construction du FS* / *Envoi des fichiers*) ;
    - % de compilation = lignes `Compiling …` comptées / nombre de `.o` du dernier build réussi de cet env
      (mémorisé dans le dossier de données de l'outil ; ~1680 aujourd'hui) ; sans référence, total
      emprunté au plus grand env de la même puce, affiché « ≈ » (ajout du 2026-10-25) ; à défaut, afficher le
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
    méthodes, IP saisies) mémorisés dans ce même dossier, hors dépôt. (2026-10-25) Journaux d'un env lus dans
    l'ordre de leur date de modification, pas de l'heure du nom (qui recule au passage à l'heure d'hiver) ;
    journaux de plus de 30 jours supprimés au démarrage de l'outil : seulement les fichiers au motif des
    journaux de la série (`date-heure-env-action[-n].log`), et une fois le port d'écoute obtenu (une seconde
    instance lancée par erreur ne purge rien).
15. **Fichiers modifiés par un lancement** : chaque `pio run` réécrit `platformio_override.ini` et
    `user_config_override.h` (CFG_HOLDER) — comportement existant. La page le rappelle en fin de
    lancement (fichiers à commiter par l'utilisateur, cf. leçon du 2026-10-13).
16. **Exécution** : `pio` du penv (`%USERPROFILE%\.platformio\penv\Scripts\pio.exe`), `cwd` = racine du
    dépôt, `PYTHONIOENCODING=utf-8` et `PYTHONUTF8=1` (sinon la sortie est perdue sur le `✔` du
    pré-script). Arbre de processus tué par `taskkill /T /F /PID`.
17. Une tâche VS Code « Outil : build et téléversement (http://127.0.0.1:7700) » sur le modèle des
    autres. Cible PlatformIO Custom (révisé le 2026-10-25, demande de l'utilisateur) : une cible est un
    `pio run` et ne peut pas piloter des `pio run` tant qu'elle vit (la page la verrait comme un build en
    cours) ; la cible `build_web` (`build/cible_build_web.py`) ouvre donc la page si elle répond, sinon la
    **démarre détachée** (hors job, sans fenêtre, console dans `consoles/build.log`) et rend la main dès
    qu'elle répond.

## Évolution du 2026-10-25 : sortie en direct et `erase_upload`

Demandée après les premiers essais réels (compilation, upload COM de la cuve, port modifié : validés).

### Décisions de l'utilisateur

- **Voir la sortie du script lancé comme dans le terminal de VS Code** : les lignes de pio au fil de
  l'eau (fichiers en cours de compilation, édition des liens, écritures d'esptool, erreurs), y compris
  pendant un `pio run -t erase_upload -e X`.
- **`erase_upload` possible**, pour une carte dans un état bancal (partitions changées, réglages ou
  persist corrompus) : tout effacer et repartir d'une flash propre avec le firmware et le FS du dépôt.
- **« Téléverser le firmware » (`-t upload`) et « Effacer puis téléverser » (`-t erase_upload`) sont deux
  actions distinctes**, côte à côte : l'utilisateur lance l'une **ou** l'autre (correction de
  l'utilisateur : la seconde ne remplace pas la première).

### Choix faits par Claude (présentés à l'utilisateur, acceptés le 2026-10-25)

18. **Panneau « Sortie » par env** : dépliable sous la ligne de l'env dans le suivi, police à chasse fixe
    sur fond sombre ; défile seul tant que l'utilisateur est en bas, s'arrête de défiler s'il remonte pour
    lire ; erreurs en rouge, avertissements en orange (pas les couleurs exactes de VS Code : les journaux
    sont écrits sans ANSI). Source : le journal que l'outil écrit déjà pour chaque `pio run` (choix 14),
    lu **par incréments** pendant l'exécution (rien de plus stocké) ; la sortie d'un env terminé reste
    relisible tant que la page est ouverte. Les lignes d'esptool qui se réécrivent (`
`) ne doivent pas
    noyer le panneau (une ligne par zone et par palier, ou la dernière seulement : au constructeur).
    (2026-10-25) Le panneau ouvert par la page au départ de l'env se referme quand l'env réussit, sauf si
    l'utilisateur l'a ouvert ou fermé lui-même ; il reste ouvert en échec ou arrêt ; au rechargement, un env
    réussi ne rouvre pas le sien et ne lit pas `/sortie`.
19. **`erase_upload`** : commande `pio run -e X -t erase_upload --upload-port COMn` ; **COM seulement**
    (grisée sur une ligne en OTA, refusée côté serveur) ; cocher « Effacer puis téléverser » décoche
    « Téléverser le firmware » et inversement (les enchaîner flasherait deux fois) ; combinable avec
    compiler, construire le FS, téléverser le FS ; même place que l'upload dans l'ordre du choix 8 ; une
    **confirmation** avant le lancement rappelle que le persist et les réglages de la carte seront
    effacés et remplacés par ceux du dépôt. Même suivi que l'upload (étapes, %, zones esptool, mention
    « FS aussi flashé » selon `fs_avec_firmware`), plus une étape **« Effacement de la flash »** (texte
    exact d'esptool à lire dans le paquet installé, pas à deviner). Compte comme un envoi pour le refus
    « port tenu ou absent » (choix 11), pour la pause « rebranchez la carte » quand deux lignes COM partagent
    un port (choix 11 révisé : envoi en `-t nobuild -t erase_upload` après une compilation réussie) et pour
    l'attente de M7 (Ctrl+C).

## Évolution du 2026-10-28 : OTA des esclaves derrière le range extender du maître (A11)

L'utilisateur a demandé de commencer sans questions (« démarre tout de suite sans questions ») ; les choix
ci-dessous sont ceux de Claude.

20. **Adresse OTA par env**, dans cet ordre : IP fixe de `WIFI_IP_ADDRESS` (provenance « h ») ; sinon, pour une
    carte du cenv dont le persist au dépôt a `serveur.rangeExtender` à `activation` ON, `id` ≥ 1 et un
    `ipMaitre`, l'adresse `<ipMaitre>:<8080 + id - 1>` (provenance « maitre », même règle que `routagePort` de
    `discoveryFonctions`) ; sinon, une adresse à saisir. Le maître lui-même a `id` 0 : pas de redirection.
    La page montre la provenance sous la ligne, et accepte la saisie `IPv4` ou `IPv4:port`.
21. **Avant tout envoi vers une adresse `IP:port`** : `RoutageRangeExtender` sur le maître (port 80 de l'IP)
    pour qu'il pose ses redirections (sa table `RgxPort` se vide à chaque redémarrage), puis `Status 5` sur
    l'adresse : le `Hostname` doit être celui du persist de l'env au dépôt (sans casse). Maître injoignable,
    commande inconnue (Berry arrêté), rien derrière le port ou une autre carte : refus, rien n'est envoyé.
    Sans persist au dépôt (adresse saisie pour un env de l'amont) : carte jointe dite, identité non contrôlée.
    Le reste de l'envoi (firmware, FS) est inchangé : `http://<IP:port>/…` passe par la redirection.
22. **`Sleep 0` sur le maître le temps de l'envoi** (accepté par l'utilisateur le 2026-10-28, après l'échec du
    premier essai réel) : valeur lue avant, remise à la fin, même sur échec ; non remise -> dite dans la ligne
    de l'env. Cause mesurée : à `Sleep 50`, pauses du relais NAPT jusqu'à 7,8 s, au-delà des 5 s
    (`HTTP_MAX_POST_WAIT`) où l'esclave abandonne ; à `Sleep 0`, 74 à 102 Ko/s sans pause.
23. **Carte déjà en safeboot** (même date) : le safeboot répond « Unknown » à `Status`, `Status 2` et `Status 5`,
    et `/u4?api=` dit « true » pour toute partition OTA unique. La page reconnaît le safeboot à sa page
    d'accueil (`<h3>SAFEBOOT</h3>`) : identité = titre (`DeviceName`) comparé à `serveur.nom` du persist,
    puis envoi sans bascule ; après l'envoi, une carte encore en safeboot est dite comme telle.

## Évolution du 2026-10-29 : onglet « Fichiers » (A15)

24. **Onglet « Fichiers » de la page 7700 : envoyer des fichiers choisis du dépôt à une carte choisie, en HTTP.**
    Choix de l'utilisateur : onglet de cette page ; fichiers DU DÉPÔT seulement ; options après envoi choisies à
    l'envoi ; disposition « C + colonne destinataire de B » (maquette E, comparée dans le navigateur à quatre
    autres le 2026-10-29) :
    - à gauche, **Carte destinataire** : une carte par ligne (bouton radio), avec son adresse OTA et sa provenance
      (IP fixe du `.h`, « par le maître », ou adresse à saisir), comme la liste du Build ;
    - en haut à droite, la carte choisie, **Préparer la liste** (buildfs de cet env, refusé pendant un build ou un
      envoi) et la date de l'image du FS ;
    - dessous, trois colonnes : **Dossiers** de l'image (avec le nombre de fichiers), **tableau** du dossier choisi
      (case, fichier, taille, date dans le dépôt, « plus récent que l'image », « sauvegardé avant » pour
      `_persist.json`), **panier « À envoyer »** (fichiers cochés, tous dossiers confondus, options « recharger
      Berry » cochée d'office si un `.be` ou le persist part et « redémarrer » décochée, bouton « Envoyer N
      fichiers ») ;
    - le panneau **Suivi** existant, partagé avec l'onglet Build ; sur écran étroit, les colonnes s'empilent.
    La liste vient de l'image `littlefs.bin` du buildfs (chemins exacts du FS, identité contrôlée par
    `verifie_identite`) ; l'envoi reprend celui de l'OTA du FS (dossiers créés, persist sauvegardé puis relu,
    esclave par le maître avec `Sleep 0`). Transport MQTT poussé : plus tard (A16).

## Évolution du 2026-10-29 : transport « MQTT poussé » et effacement du FS (A16)

Décision de l'utilisateur (2026-10-29, fin de A14) : « utilisons la voie poussée par mqtt », dans l'onglet
« Fichiers », après le transport HTTP ; la page doit aussi pouvoir **effacer totalement** le FS de la carte par MQTT.
L'utilisateur a passé les questions de conception (« passons ») : tout ce qui suit est **choix de Claude**, à relire.

25. **Protocole** (repris de l'essai A14, prouvé sur le maître et la cuve par le maître : morceaux de 1900 o, 4 à 8 en
    vol, aucune coupure malgré des pauses du relais de 14 s).
    - Topics, sous le topic MQTT du persist de la carte (`serveur.mqtt.topic`, celui que la page connaît et que
      `verifie_identite` contrôle) : le PC publie sur `fsmqtt/<topic>/ordre` (JSON) et `fsmqtt/<topic>/morceau`
      (binaire) ; la carte répond sur `fsmqtt/<topic>/etat` (JSON) et `fsmqtt/<topic>/lu` (binaire). Préfixe propre,
      hors `cmnd/` : rien ne passe par l'analyseur de commandes de Tasmota, et le binaire passe tel quel.
    - Ordres (`{"op": …, "id": n}`, `id` rendu dans chaque réponse ; réponse `{"id", "op", "ok": true, …}` ou
      `{"id", "op", "ok": false, "erreur": "…"}`) :
      `debut {chemin, taille, md5}` ouvre `/fsmqtt.tmp` en écriture, crée les dossiers du chemin ;
      chaque **morceau** = 4 octets de position (gros-boutiste) + données ; la carte n'ajoute que le morceau dont la
      position est celle attendue, et accuse le CUMUL (`{"op": "morceau", "octets": n}`) ; un morceau perdu ou en
      double ne casse rien : le PC, sans progrès de l'accusé pendant 5 s, renvoie à partir de `octets`
      (« retour arrière », au plus 3 fois de suite) ;
      `fin` contrôle taille et MD5 (`crypto.MD5`, compilé sans condition), supprime l'ancien fichier puis renomme
      le temporaire : jamais de fichier à moitié écrit à sa place ;
      `abandon` ferme et supprime le temporaire ;
      `lit {chemin}` renvoie le fichier sur `…/lu` en morceaux (position + données), 4 par rappel enchaînés par
      `tasmota.set_timer(0)` (un `publish` peut attendre derrière le NAPT du maître), puis `{"op": "lit", "octets",
      "md5"}` : sert à **sauvegarder le persist avant de le remplacer**, comme en HTTP ;
      `recharge` = `persist.load()` et les globales (même chose que `BR_RECHARGE`) ;
      `berry` = `BrRestart` et `redemarre` = `Restart 1`, passés par `Backlog` APRÈS la réponse : `BrRestart` détruit
      la VM (`BerryInit`), il ne peut pas tourner dans un rappel Berry ; `Backlog` l'exécute depuis la boucle principale ;
      `efface` : voir 26.
    - Au chargement du module (démarrage de la carte, ou `BrRestart`), la carte publie `{"op": "pret", "version"}`
      sur `…/etat` : c'est ce que le PC attend après `redemarre` ou `berry` (90 s), et la preuve que le module est là.
    - Chemins refusés : hors `/`, avec `..`, plus de 49 caractères (limite `UFS_FILENAME_SIZE` de Tasmota), le
      temporaire. `/sd/…` est accepté : Berry n'écrit que dans le LittleFS de la flash (`be_port.cpp`, `ffsp`), où
      `/sd` est un dossier ordinaire, celui de l'image (`sd/html`, `sd/js`…) ; une carte SD montée est hors de portée ;
      chemin finissant par `/` ou d'un dossier existant ; taille au plus 1 Mo ; un seul transfert à la fois (un
      `debut` pendant un autre l'abandonne d'abord), une seule lecture, un seul effacement (le second est refusé).
      Toute exception (écriture, lecture, suppression) est rattrapée : fichier fermé, temporaire supprimé, refus
      répondu au PC et journalisé en erreur.
26. **Effacement total** — RÉVISÉ par l'utilisateur le 2026-10-29 (« formater se fera par script berry ») : `efface`
    FORMATE le LittleFS par `path.format(true)` (`be_port.cpp::be_format_fs` -> `LittleFS.format()`), `/sd` de la
    flash compris (pas une carte SD), `_persist.json` et autoexec compris ; refusé pendant une lecture, transfert en
    cours abandonné ; une seule réponse `{"op": "efface", "ok": true}`, refus si le firmware rend `false`. La première
    version (fichier par fichier, lots de 20) est abandonnée. RISQUE : le formatage est BLOQUANT ; `LittleFS.format()`
    ne coupe que le watchdog du cœur 0, celui de la boucle (`USE_ESP32_WDT`, 5 s, actif sur toutes les cartes ESP32 :
    `user_config_override.h`) redémarre la carte s'il dure plus -> FS vide, à reprendre en HTTP (`/ufsu` ne dépend pas
    de Berry) ou par câble. Durée à mesurer au premier essai. Le module, SOLIDIFIÉ (27), survit au formatage ;
    l'autoexec non : le PC envoie TOUT le FS juste après, dans la même session Berry. Le persist en RAM est réécrit
    par le System#Save d'un redémarrage : la page envoie donc toujours le persist après un effacement. Page :
    confirmation explicite, comme `erase_upload` ; essai réel d'abord sur une carte hors service.
27. **Module récepteur** : `data/fs/fsMqtt.be` (nouveau fichier, A16 lancée par l'utilisateur), SOLIDIFIÉ dans
    `berry_commun.socle` (décision de l'utilisateur, 2026-10-29 : présent sur toutes les cartes), chargé par
    `demarrage.charge(["fsMqtt"])` dans l'autoexec du maître P4 et de la cuve ; `import` appelle `fsMqtt_init(m)`
    (instance dans `global.fsMqttRecepteur`, constantes en membres statiques : table du module constante, piège 12).
    Ces deux cartes ont besoin d'un firmware recompilé (module en flash), puis de leur nouvel autoexec. Abonnements par
    `mqtt.subscribe` (comme `controleDiscovery.be`), rappels courts, charte des logs (cible `general` :
    `logFonctions` n'a pas de bloc `fsmqtt`, l'ajouter toucherait un module protégé), RAM : un
    morceau à la fois, fichier ouvert en ajout, rien de gardé en mémoire.
28. **Côté PC** : `build_ota_mqtt.py::envoie_fs_mqtt`, même signature que `envoie_fs_ota` (mêmes `fichiers=`,
    `recharger_berry=`, `redemarrer=`, plus `effacer=`), client `client_mqtt.py`, broker de
    `user_config_override.h` (`sniffeur_mqtt.lit_config_broker`). Même déroulé que l'HTTP : identité de l'image
    vérifiée, persist de la carte sauvegardé (par `lit`) s'il part, envoyé en dernier, `recharge` toujours s'il
    part, puis `redemarre` ou `berry`. Esclave du range extender : rien de spécial (sortie NAPT du maître vers le
    broker, sans redirection ni `Sleep 0`). Avancement : un `%` par fichier et global, comme l'HTTP.
    Pas de relecture du persist après redémarrage (la carte le réécrit à son démarrage : différence toujours
    signalée, A11). Onglet : choix « HTTP / MQTT » dans les options, case « Effacer tout le FS avant l'envoi »
    (MQTT seulement), envoi au topic du persist de l'env.

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
