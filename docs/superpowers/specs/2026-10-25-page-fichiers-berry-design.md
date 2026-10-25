# Page web « Fichiers Berry par env » — conception

Date : 2026-10-25. Statut : en revue par l'utilisateur.
Outil voisin et modèle : la page « Build et téléversement » (`outils_pc/build_web.py`, spec
`2026-10-24-page-build-televersement-design.md`).

## 1. Intention

Aujourd'hui, décider ce que devient un fichier Berry pour une carte (embarqué sur le LittleFS, exclu,
ou solidifié dans le firmware) oblige à éditer à la main `platformio_tasmota_cenv.ini` : trouver la
section de l'env, comprendre ce qu'il hérite (`${berry_commun.socle}`, `${env:<base>...}`), écrire la
ligne dans la bonne option, sans oublier qu'une liste partagée touche d'autres cartes. La page fait ce
réglage, env par env, en montrant l'état complet et l'origine de chaque entrée.

## 2. Ce que fait la page

### 2.1 Les trois états d'un fichier, et ce que la page écrit

Fait établi dans le code (à ne pas re-décider) : un `.be` de `data/fs` est **déjà** sur le LittleFS par
défaut. `copy_fs_image` (`build/pre_utilitaires_platformio.py:540-566`) recopie `data/fs` dans le dossier
de la carte, et `custom_files_upload` désigne ensuite ce dossier entier. On ne retire un fichier du FS
que par `custom_files_exclude` (toujours appliquée, `pio-tools/post_esp32.py:207-219`) ou par
`custom_berry_solidify` + `custom_files_exclude_solidified = ON` (`post_esp32.py:191-205`).

| État choisi | Fichier de `data/` (data/fs ou dossier de la carte) | Module de l'amont (`tasmota/berry/modules/`) |
|---|---|---|
| **Sur le FS** | aucune ligne (retiré de `custom_files_exclude` et de `custom_berry_solidify` s'il y était) | ligne ajoutée à `custom_files_upload` |
| **Exclu** | ligne ajoutée à `custom_files_exclude` | (s'appelle **Absent**) : ligne retirée de `custom_files_upload` |
| **Solidifié** | ligne ajoutée à `custom_berry_solidify` | non proposé |

- `autoexec.be` de la carte : figé sur « Sur le FS » (non solidifiable, indispensable au démarrage).
- Si l'env n'a pas `custom_files_exclude_solidified = ON`, la page l'indique : un fichier « Solidifié »
  y reste **aussi** sur le FS.
- Un fichier à la fois dans deux listes (ex. exclu ET solidifié) est montré comme une incohérence.

### 2.2 Les fichiers proposés — recensés à chaque chargement

À chaque chargement de la page (et par un bouton « Revérifier les fichiers ») :
- les `.be` de `data/fs` (37 aujourd'hui) ;
- les `.be` du dossier de la carte de l'env (`data/<lieu>/<carte>/`, calculé comme `transform_name`,
  `pre_utilitaires_platformio.py`) ; aucun pour un env de base ;
- les modules de l'amont sous `tasmota/berry/modules/` (`.bec`, `.tapp`, `.be` de premier niveau).

Dossiers `*sauvegarde*` ignorés. Une entrée du `.ini` qui désigne un fichier **disparu** du disque est
signalée (et peut être retirée), jamais retirée en silence.

### 2.3 Disposition (retenue : variante B de la maquette)

1. En haut : choix de l'env (tous les `[env:]` de `platformio_tasmota_cenv.ini`, les seuls écrivables,
   comme `build_envs.ecrit_port`), bouton « Revérifier les fichiers ».
2. Ligne d'action : liste déroulante des fichiers (nom + dossier d'origine), trois boutons radio
   « Sur le FS / Exclu / Solidifié » (libellés adaptés pour un module de l'amont), bouton « Appliquer ».
3. Trois colonnes : **Sur le FS** · **Exclu** · **Solidifié**, avec l'état complet de l'env. Chaque
   entrée héritée porte un badge de son origine : `socle`, `modbus`, `historique` (listes de
   `[berry_commun]`) ou l'env de base (`${env:...}`). Les modifications en attente sont marquées.
4. Sous les colonnes : « Voir le diff puis enregistrer ».

### 2.4 Listes partagées

Si le fichier choisi vient d'une liste partagée (`[berry_commun]` ou une option héritée d'un autre env),
« Appliquer » ouvre un avertissement : le fichier est dans la liste partagée `<nom>`, la modifier touche
**N envs** (liste nommée, calculée par la résolution des `${...}`). Deux issues seulement :
**« Modifier la liste partagée (N envs) »** ou **« Annuler »**. Pas de « détacher cet env » (recopie de
la liste en dur) : c'est le piège que `[berry_commun]` existe pour éviter (leçon du 2026-09-27).

### 2.5 Enregistrement

- Deux temps : diff du `.ini` affiché, puis écriture sur confirmation. Copie `.bak` avant d'écrire (comme
  `build_envs.ecrit_port`). Fins de ligne et encodage du fichier conservés.
- **Refusé pendant un build** (même détection que `garde_build` : `platformio run` ou `scons` actif).
- Rappel affiché : l'écriture change l'empreinte du projet, **le build suivant repart de zéro**.
- **Commentaires** : la page ne modifie ni ne supprime jamais un commentaire existant. Dans le diff, elle
  signale les commentaires de la section qui citent le fichier déplacé (ils risquent de devenir faux).
  À l'ajout d'une ligne, un champ facultatif « raison » : écrit en fin de ligne `; <raison> (AAAA-MM-JJ)`
  (PlatformIO lit les `;` en fin de ligne comme commentaires : `ConfigParser(inline_comment_prefixes=("#", ";"))`,
  `platformio/project/config.py:97`).
- Passage à « Solidifié » : rappel des conditions du dépôt (vérifier par
  `berry/solidifie_et_compile_berry.py` ; globale nouvelle → `globs` de `solidify_all_python.be` ;
  module qui s'appelle par son nom → import de niveau fichier dans l'autoexec). La page **n'exécute pas**
  ce script (il écrit dans `lib/libesp32/berry_custom`).

### 2.6 Créer un nouvel env à partir d'une carte modèle (demande du 2026-10-25)

L'utilisateur part d'une carte existante. Un bouton « Créer un env à partir de… » ouvre un formulaire.

**Champs demandés** (liste validée par l'utilisateur) :
- carte modèle (un env de carte du cenv), base (préremplie avec celle du modèle, modifiable), lieu, nom ;
- identité, préremplie d'après le nouveau nom et modifiable : `CODE_IMAGE_STR`, `PROJECT`,
  `WIFI_IP_ADDRESS` (défaut `0.0.0.0`, DHCP), `WIFI_RGX_SSID`, `MQTT_CLIENT_ID`, `MQTT_TOPIC`
  (défaut `<lieu>/<nom>`), `MQTT_GRPTOPIC`, `FRIENDLY_NAME`.

**Ce que la page produit** (les trois morceaux sont indispensables : sans dossier, la carte démarre
sans autoexec ni persist, leçon du 2026-09-27 ; sans section `.h`, le `-D FIRMWARE_...` ne sert à rien) :
1. **Section `[env:<puce>-<lieu>-<nom>]`** dans `platformio_tasmota_cenv.ini`, recopiée de celle du
   modèle : `extends` = la base choisie, `build_flags` avec `-D FIRMWARE_<NOUVEAU>` à la place de celui du
   modèle, mêmes `custom_berry_solidify` / `custom_files_exclude` / `custom_files_exclude_solidified`,
   `custom_files_upload` = celui de la base + le nouveau dossier. Les chemins qui désignent le dossier du
   modèle (ex. `data/garage/<modèle>/controleRideau.be` dans `custom_berry_solidify`) sont réécrits vers
   le nouveau dossier. `upload_port`/`monitor_port` du modèle NON recopiés (port d'une autre carte).
2. **Dossier `data/<lieu>/<puce>-<nom>`**, nom calculé par `transform_name`
   (`pre_utilitaires_platformio.py:256`) — jamais saisi à la main. Contenu = copie du dossier du modèle
   (`autoexec.be`, `_persist.json`, `controleXxx.be`...), hors `*sauvegarde*`. Dans le `_persist.json`
   copié, seules les valeurs d'identité sont remplacées : `serveur.nom`, `serveur.hostname`,
   `serveur.IP.IPAddress`, `serveur.mqtt.client`, `serveur.mqtt.topic`, `serveur.mqtt.groupTopic1`,
   `serveur.rangeExtender.AP.SSID`, `template.NAME`. Remplacement **ciblé dans le texte**, le reste du
   fichier gardé octet pour octet (encodage, fins de ligne, ordre des clés) : pas de re-sérialisation JSON.
3. **Section `#elif defined(FIRMWARE_<NOUVEAU>)`** dans `tasmota/user_config_override.h` : copie de la
   section du modèle, insérée juste après elle, avec les defines d'identité remplacés — y compris le
   `Hostname` de `USER_BACKLOG` (= `PROJECT`) et le `NAME` du `USER_TEMPLATE` (= `CODE_IMAGE_STR`),
   qui portent aussi l'identité.

**Refus et garde-fous**
- Refus si l'env, le dossier ou le define existent déjà, ou si l'IP (hors `0.0.0.0`), le topic ou le
  client MQTT sont déjà utilisés par une autre section de `user_config_override.h` ou un autre
  `_persist.json` (deux cartes de même identité se déconnectent mutuellement : avertissement de la cave
  S3 dans le cenv).
- Refus pendant un build (le build réécrit `user_config_override.h`, `increment_config_holder`).
- Même parcours qu'un enregistrement : diff des trois morceaux, puis écriture, `.bak` des deux fichiers
  modifiés. **Valeurs secrètes masquées dans le diff** (`STA_PASS*`, mots de passe du persist) : ces
  fichiers contiennent des mots de passe (AUDIT_MODBUS_2026-09-29.md S1).
- Rien n'est commité.

**Mes choix (Claude)** : nom du define proposé `FIRMWARE_<PUCE>_<LIEU>_<NOM>` (majuscules, `-` → `_`),
modifiable ; section du cenv insérée sous le bandeau `; LOCALISATION: <LIEU>` existant, sinon en fin de
fichier avec un nouveau bandeau ; si la section `.h` du modèle est partagée (`#if defined(A) ||
defined(B)`, cas de la cave), la copie ne garde que le nouveau define et la page signale les conditions
internes qui citent l'ancien (à revoir à la main). La nouvelle carte apparaît ensuite d'elle-même dans
la page build (`build_envs.liste_envs` relit le cenv) : à vérifier au banc.

## 3. Accès

1. **Tuile de l'annuaire**, groupe Maintenance, comme « Build et téléversement » (`annuaire_registre.py`).
   Port **7800** (mon choix). Arrêt NON bloqué : rien n'est écrit avant « Enregistrer ».
2. **Cible Custom « Fichiers Berry par env (page web) »**, sur le modèle exact de
   `build/cible_build_web.py` : démarre la page **détachée** puis rend la main (une cible vivante serait
   vue comme un build par `garde_build`). Rappel : c'est un `pio run`, jamais pendant un build. Plus une
   tâche VS Code « Outil : fichiers Berry par env » (lancer la tâche au moins une fois avant de l'annoncer).
3. **Liens croisés avec la page build** : sur chaque env de la page build, un lien « Régler ses fichiers »
   ouvre cette page avec l'env présélectionné (`?env=<nom>`) ; après un enregistrement, cette page propose
   « Construire / téléverser le FS » qui ouvre la page build avec cet env présélectionné.

Accès réseau, jeton, lien cliquable, ouverture du navigateur, fiche de présence : `outils_pc/acces_web.py`,
comme les autres outils.

## 4. Non-objectifs

- Éditer le **contenu** des fichiers (`_persist.json`, `.be`), hors le remplacement ciblé des valeurs
  d'identité à la création d'un env (§2.6).
- Toucher aux autres options du `.ini` d'un env existant (ports, `build_flags`, partitions...).
- Supprimer ou renommer un env.
- Lancer un build, une solidification ou `carte_modules_berry.py`.
- Gérer les fichiers non Berry de `data/sd`, `data/json` (même si `custom_files_exclude` s'y applique).

## 5. Anti-objectifs (échec même si « ça marche »)

- Un `.ini` réécrit qui perd des commentaires, l'ordre des lignes ou les fins de ligne.
- Une liste partagée modifiée sans que l'utilisateur ait vu la liste des envs touchés.
- Une écriture pendant un build.
- Une page annoncée prête sans avoir tourné dans un vrai navigateur (leçon du 2026-10-16).

## 6. Contraintes du dépôt

- Python stdlib, dans `outils_docs/scripts_python/outils_pc/`, comme les autres pages ; réutiliser la
  lecture du `.ini` de `build_envs.py` (`_lit_ini`, `_sections`, `_valeur`) plutôt qu'un 2e parseur.
- Bancs : un banc par module (`test_*.py`, code de sortie 0 = vert), dont un banc d'écriture du `.ini`
  sur une copie (jamais le vrai fichier) avec témoins : liste partagée, commentaire conservé, CRLF,
  build en cours → refus ; et une sonde Chrome de la page (comme `test_build_page_chrome.py`).
- Le `.ini` réécrit doit être relu par les trois lecteurs réels (`GetProjectOption` dans
  `post_esp32.py`, `_noms_fichiers_option` de `pre_utilitaires_platformio.py`, `carte_modules_berry.py`)
  sans changement de sens : à prouver au banc via `ProjectConfig` du penv.
- Fichiers < 500 lignes (exception à demander, pas à compresser).
- Doc : section dans `outils_docs/README.md`, entrée dans la carte des documents de `CLAUDE.md`.

## 7. Précisions issues de la relecture (choix de Claude, à valider par l'utilisateur)

1. **Option héritée, non définie dans l'env.** PlatformIO prend l'option de la première section de la
   chaîne `extends` qui la définit, sans fusion. Pour AJOUTER une entrée dans un env qui hérite de
   l'option, la page écrit `option = ${env:<base>.option}` puis la nouvelle ligne : l'héritage est gardé.
   Créer l'option avec la seule nouvelle ligne écraserait l'héritage en silence : interdit. RETIRER
   une entrée héritée relève du cas « liste partagée » (§2.4) : la base est modifiée, avec la liste des
   envs touchés.
2. **Résolveur à écrire.** `build_envs._valeur` ne résout que `${env:X.opt}`. Code neuf : résolution de
   `${section.option}` (dont `[berry_commun]`) et `${env:X.opt}`, en profondeur illimitée avec garde
   contre les cycles, chaque entrée gardant sa provenance (badge). Envs touchés par une section
   partagée = tous ceux dont la valeur résolue la traverse, directement ou en cascade.
3. **Entrées hors périmètre** (`data/sd/js/*.js`, `*.gz`, `*.html` dans `custom_files_exclude`) : montrées
   dans la colonne « Exclu », en lecture seule, marquées « hors périmètre », jamais modifiées. Une ligne
   dont le fichier n'existe plus sur le disque est signalée « disparue », quel que soit son type ; seule
   une ligne Berry disparue peut être retirée par la page.
4. **Chemins écrits** : relatifs à la racine du dépôt, comme aujourd'hui
   (`data/fs/x.be`, `data/<lieu>/<carte>/x.be`, `tasmota/berry/modules/...`). « Solidifié » est proposé
   pour les `.be` du dossier de la carte (précédent : `controleRideau.be`), sauf `autoexec.be`. « Sur le
   FS » pour un fichier de la carte = aucune ligne, comme pour `data/fs`.
5. **États mixtes** : un changement d'état retire le fichier de TOUTES les listes où il figure. Si l'une
   d'elles est partagée, un seul avertissement liste tous les envs touchés, et le diff montre les
   écritures partagées et locales ensemble, en une seule étape. `custom_files_exclude_solidified`
   absent ou OFF : avertissement seulement, la page ne propose pas de le poser.
6. **Modifications en attente** : gardées côté navigateur (plusieurs « Appliquer » avant
   « Enregistrer ») ; le serveur reçoit l'ensemble au moment du diff puis de l'écriture. Le diff porte
   une empreinte (hachage) du `.ini` lu ; l'écriture est refusée si le fichier a changé entre-temps
   (par exemple par la page build qui réécrit `upload_port`), avec invitation à recharger.
7. **Envs proposés** : tous les `[env:]` ESP32 de `platformio_tasmota_cenv.ini`, bases comprises (une
   modification de base est toujours une liste partagée, §2.4). `tasmota-pompe-piscine` (ESP8266, sans
   Berry) n'est pas proposé. Un env sans `custom_files_upload` propre (ex. `tasmota32-rdc-vr-porte`) est
   proposé : il hérite de sa base.

## 8. Laissé au constructeur

Découpage en modules, routes HTTP, forme exacte du diff, style visuel (aligné sur la page build),
emplacement des nouvelles lignes dans une liste (en fin de liste par défaut).
