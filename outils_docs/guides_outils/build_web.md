# Build et téléversement

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

Autres fichiers Build : `build_web_compilation.md` (ce qui fait recompiler : cache, `CFG_HOLDER`, `data_dir`), `build_web_ota.md` (IP de l'OTA, OTA du firmware et du FS), `build_web_fichiers.md` (onglet « Fichiers », transport MQTT, arrivée depuis un atelier), `build_web_memoire_defaut.md` (onglets « Mémoire et partitions » et « Env par défaut »), `build_web_sauvegardes.md` (onglet « Sauvegarde configuration »), `build_web_reparations.md` (réparation automatique des pannes).

## Build et téléversement (page web)

Une page pour compiler et téléverser plusieurs cartes d'un seul écran, sans éditer les `.ini` :
on coche des environnements PlatformIO et des actions, on choisit COM ou OTA **ligne par ligne**, et
la page enchaîne les `pio run` en montrant l'étape, le pourcentage, les durées et les échecs en direct.
Conception : [spec](../../docs/superpowers/specs/2026-10-24-page-build-televersement-design.md) ; plan :
`tasks/plans/page-build-televersement.md`.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Déploiement » : « Build et téléversement ». La page
  ne s'arrête pas avec l'annuaire pendant un lancement, et l'annuaire refuse de l'arrêter tant qu'un lancement
  est en cours.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : build et televersement (http://127.0.0.1:7700) » (sans accent dans `.vscode/tasks.json`).
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/build_web.py` (`--http 7700`,
  `--local` pour n'écouter que ce PC, `--sans-navigateur`). Depuis un autre appareil du réseau : le lien à jeton
  affiché dans la console (comme les autres outils).
- **Cible PlatformIO** « Build et téléversement (page web) » dans *Project Tasks > <env> > Custom* (n'importe quel
  env ESP32) : ouvre la page si elle tourne, sinon la démarre **détachée** (console dans
  `%LOCALAPPDATA%\outils_tasmota\consoles\build.log`) et rend la main en quelques secondes — une cible est un
  `pio run`, encore vivante elle serait prise pour un build en cours. La page survit à la cible : l'arrêter par
  l'annuaire. Comme toute cible, **jamais pendant un build** (risque de purge de `.pio/build`).

### Les environnements et les actions

- **Classement** : *Mes cartes* (envs de `platformio_tasmota_cenv.ini`), *Mes bases* (`tasmota32-base`,
  `tasmota32s3-base-N16R8`, `tasmota32p4-base-*`) et *Tasmota (amont)*, replié par défaut, en sous-groupes
  (safeboot, ESP32, langues, ESP8266).
- **Classer par** Famille / Lieu / Puce (barre au-dessus de la liste) : en Lieu, les cartes sont rangées par
  emplacement dans la maison (2e segment du nom d'env, table de `outils_pc/lieux.py`), en Puce par ESP32, ESP32-S3,
  ESP32-P4, ESP8266 ; « Mes bases » et l'amont restent en dessous. La case d'un groupe coche ou décoche ses cartes
  visibles ; un groupe s'ouvre à l'arrivée s'il contient une carte cochée. Le classement est retenu par le navigateur
  et ne change rien à ce qui est coché ni à ce qui part. **Filtrer par nom** réduit la liste ; un env coché caché par
  le filtre est signalé en orange, il part quand même au lancement.
- **Arrivée avec `?lieu=`** (lien de l'annuaire) : la page passe en classement Lieu pour cette visite seulement (le classement
  retenu par le navigateur n'est pas réécrit), ouvre le groupe du lieu, affiche le bandeau « Lieu : X (depuis l'annuaire) » et
  ne coche rien. La croix du bandeau rend le classement retenu. Les onglets Fichiers, Mémoire et Sauvegardes choisissent
  la première carte du lieu si rien n'est déjà choisi.
- **Cinq actions**, combinables, appliquées à tous les envs cochés : compiler, téléverser le firmware, effacer puis
  téléverser (voir plus bas), construire le file system, téléverser le file system. Dans un env, l'ordre est
  toujours compiler, téléverser (ou effacer puis téléverser), construire le FS, téléverser le FS, en ne lançant que
  ce qui est coché. Un échec arrête **cet env** (étapes
  suivantes « annulées ») ; les autres envs continuent.
- **Solidification contrôlée dès la fin du pré-build** (compiler, téléverser, effacer puis téléverser) : si un
  module ou une classe inscrit dans `lib/libesp32/berry_custom/src/modules.h` n'a aucune définition dans les `.h`
  solidifiés, la page arrête `pio` aussitôt, avec le motif « solidification vide : <module> (cause) », au lieu
  de laisser l'édition des liens échouer une heure plus tard sur `undefined reference to be_native_module_<module>`.
  Cause habituelle : le `.be` déclare `module("X")` sans la ligne `#@ solidify:X` (cas de `demarrage.be` le
  2026-10-26). Le contrôle ne s'applique qu'à un env Berry, c'est-à-dire quand la sortie de pio a montré « Will solidify » :
  `modules.h` garde les entrées du dernier env Berry et `solidify/` est vide pour un ESP8266, d'où un faux positif le
  2026-11-15 (`build_serie.py::_lance_pio`, plan `build-reparations`).
- **COM ou OTA par ligne.** Le port COM est lu dans le `upload_port` de l'env (y compris hérité par `extends`),
  vide s'il n'y en a pas. L'IP OTA est lue dans `WIFI_IP_ADDRESS` de `tasmota/user_config_override.h`, bloc du
  firmware de l'env. L'OTA est grisée pour les envs qui ne chargent pas `pre_utilitaires_platformio.py` (ESP8266)
  et pour les safeboot de l'amont.

### Le port COM : lu, et réécrit dans le `.ini`

Un port modifié sur la page d'un env **personnel** est réécrit dans la section `[env:…]` de
`platformio_tasmota_cenv.ini` (le `.ini` reste la référence : un `pio run` lancé depuis VS Code prend le même
port) : commentaires et alignement gardés, ligne ajoutée dans la section de l'env même si la valeur venait d'un
`extends` (une ligne `; upload_port` n'est jamais décommentée), champ vidé = ligne active supprimée. Une copie
`platformio_tasmota_cenv.ini.bak` est faite avant chaque écriture ; l'écriture est refusée pendant un lancement ou
un build.

> [!WARNING]
> Réécrire le `.ini` change l'empreinte du projet : le **build suivant repart de zéro** (PlatformIO supprime
> alors tout `.pio/build`, tous envs compris). La page le rappelle à côté du champ. Pour un env de l'amont, un
> port saisi vaut pour le lancement seulement (`--upload-port`) : aucun fichier n'est écrit.
### Téléversement série : il emporte `littlefs.bin`

« Téléverser le firmware » **par câble** flashe aussi le file system (persist compris) **à chaque upload par câble**
pour tout env ESP32 dont `custom_files_upload` contient des fichiers (pas seulement `no_files`) : c'est le cas des
cartes et des bases personnelles. `pio-tools/post_esp32.py` reconstruit `littlefs.bin` à chaque édition des liens
(toujours, puisque le pré-script force la refabrication de `firmware.bin` par `env.AlwaysBuild`, dont `post_esp32.py::esp32_create_combined_bin` est la post-action ; `CFG_HOLDER` n'y est pour rien depuis le 2026-11-01), même après une purge de `.pio/build`, et l'ajoute à la
commande esptool. Comportement gardé par choix ; la ligne l'annonce avant le lancement (d'après les `.ini`, pas
d'après la présence de `littlefs.bin`), et le suivi le redit au téléversement.

Conséquence (2026-10-26) : « Construire le file system » et « Téléverser le file system » n'apportent rien à un tel
envoi. Si **tous** les envs cochés sont en COM, embarquent des fichiers et « Téléverser le firmware » ou « Effacer
puis téléverser » est coché, les deux cases sont décochées et grisées (infobulle). Dans une série mixte (un env en
OTA ou sans fichiers), elles restent actives : le serveur ne lance alors ni `buildfs` ni `uploadfs` pour les envs
déjà servis par leur envoi, qui prennent le statut de cet envoi (la ligne le dit). `buildfs` lirait d'ailleurs le
`data_dir` du lancement précédent (défaut A12 du plan de la page).

### Calibrage d'énergie gardé autour d'un flash par câble

Avant un envoi du firmware par câble (ou « Effacer puis téléverser »), la page copie `/.drvset003` de la carte par le
réseau (calibrage et compteurs ; rôle des fichiers `.drvset` : onglet « Aide » de la page et `FICHIERS_DRVSET.md`). Après un envoi réussi, elle le renvoie, redémarre par
`Restart 99` (`Restart 1` réécrirait le fichier avec la RAM de la carte neuve) et relit le calibrage. Étape
« Calibrage » sur la ligne de l'env. Carte injoignable ou sans ce fichier : le flash a lieu quand même, sans
rétablissement. Échec du rétablissement : le message donne le chemin de la copie, sous
`%LOCALAPPDATA%\outils_tasmota\build\drvset\`. La même étape prend aussi une sauvegarde de toute la configuration,
d'origine « avant flash », visible dans l'onglet « Sauvegarde configuration ».

### Effacer puis téléverser (`erase_upload`)

Pour une carte dans un état bancal (partitions changées, réglages ou persist corrompus) : la page lance
`pio run -e X -t erase_upload --upload-port COMn`, qui efface **toute** la flash (`esptool erase-flash`) puis
téléverse le firmware, et le file system comme un upload par câble (`post_esp32.py` ajoute `littlefs.bin` à la
commande quelle que soit la cible ; même mention « FS aussi flashé » sur la ligne).

- **Par câble seulement** : la case est grisée si une ligne cochée est en OTA, et le bouton OTA des lignes est grisé
  tant qu'elle est cochée ; le serveur refuse aussi une ligne OTA.
- **L'une ou l'autre** avec « Téléverser le firmware » : cocher l'une décoche l'autre (les enchaîner flasherait deux
  fois) ; le serveur refuse les deux ensemble. Combinable avec compiler ; construire et téléverser le FS sont grisés
  pour un env qui embarque des fichiers (voir plus haut).
- **Confirmation** avant le lancement : le persist (`_persist.json`) et les réglages de la carte (Wi-Fi, MQTT,
  réglages faits sur la carte) sont effacés et remplacés par ceux du dépôt ; un réglage non reporté dans le dépôt
  est perdu. Un env sans file system dans le dépôt repart sans persist (la confirmation le nomme).
- Suivi : étape **« Effacement de la flash »** (recherche du port puis effacement) avant « Téléversement ». C'est un
  envoi comme l'upload : refus si le port est tenu ou absent, pause « rebranchez la carte » s'il est partagé avec un
  env précédent, et un arrêt de la page attend la fin de l'effacement et du téléversement.

### Refus, attente, arrêt

- **Refus avant lancement** : un build tourne déjà (VS Code, cible Custom, même logique que le hook `garde_build`,
  qui ne compte pas les cibles d'outils : un annuaire ou un pont série lancé par sa cible Custom n'est pas un
  build, sauf pendant ses 30 premières secondes, où son démarrage peut encore purger `.pio/build`) ; un port COM tenu par un autre outil (pont série, sniffeur, testeur) ou absent, pour une action d'envoi.
- **Plusieurs cartes sur le même port COM** (pause « rebranchez la carte ») : le lancement est accepté. Pour un env
  dont l'envoi passe par un port déjà servi par un env précédent de la série, la compilation (si cochée) se fait
  d'abord, en un `pio run` à part ; juste avant son premier envoi, la série s'arrête et la page affiche
  « **Branchez la carte X sur COMn puis cliquez Continuer** », avec **Continuer** et **Passer cet env**. Continuer :
  la page attend un éventuel build lancé ailleurs pendant la pause, revérifie le port, puis envoie ; port absent ou
  tenu : **la pause reste ouverte** avec le message dans le bandeau (« COM12 absent : rebranchez puis Continuer »,
  ou tenu par un autre outil), on réessaie ou on passe. Après un clic accepté, les boutons restent grisés jusqu'à la
  suite. Passer : les actions restantes de l'env sont « annulée », l'env est « passé », la série continue. Les deux
  arrêts et le Ctrl+C de la page mettent fin à la pause (rien n'est en cours d'envoi) : l'env est « arrêté », compté
  à part dans le récapitulatif, pas comme un échec. Recharger la page remontre le bandeau tant que la pause dure. La
  ligne cochée au port partagé l'annonce avant le lancement. **Sans recompiler** : quand la compilation a réussi
  avant la pause, l'envoi part en `pio run -t nobuild -t upload` (ou `erase_upload`), qui reprend le firmware déjà
  compilé. Un env dont l'envoi série joint le FS reçoit ensuite son FS par `pio run -t nobuild -t uploadfs` : en
  `nobuild`, la jointure du FS de `post_esp32.py` ne tourne pas (corrigé le 2026-11-01 ; avant, la carte recevait le
  firmware SANS le FS, et un « effacer puis téléverser » la laissait avec un FS vide).
- **Attente** : le contrôle « build en cours » est refait avant chaque env. Si un build est apparu entre deux envs,
  la série attend (« en attente : build en cours ») et reprend à sa fin ; on peut l'arrêter.
- **Arrêt** : « Arrêter après cet env » (propre) ou arrêt immédiat, qui peut laisser une carte à moitié flashée et
  des copies temporaires dans `data/<lieu>/<carte>` (la page les signale, ne les efface pas). Un envoi OTA en
  cours n'est pas coupé, un envoi OTA pas encore commencé est annulé ; un upload fini avec succès reste un succès.
- **Arrêt de la page** (Ctrl+C dans sa console, fermeture) : un envoi vers une carte en cours (téléversement par
  câble, envoi OTA) va d'abord à son terme, puis le reste du lancement est tué ; un second Ctrl+C force l'arrêt.
  L'écriture du port COM est refusée pendant un lancement de la page **et** pendant un build lancé ailleurs.
### Journaux, mémoire de la page, fichiers réécrits

- Sortie complète de chaque `pio run` (avec ses codes de couleur ANSI, retirés par « Journal complet ») : `%LOCALAPPDATA%\outils_tasmota\build\journaux\`,
  dépliable sur la page (« Journal complet »). Les journaux d'un env se lisent dans l'ordre de leur **date de
  modification** (pas l'heure écrite dans le nom, qui recule au passage à l'heure d'hiver). Au démarrage de la page,
  les journaux de **plus de 30 jours** sont supprimés (une suppression impossible est comptée dans la console) :
  seulement les journaux de la page (`date-heure-env-action.log`), et pas si une autre instance tient déjà le port.
- **Sortie de pio en direct** : mêmes couleurs que le terminal de VS Code (`PLATFORMIO_FORCE_ANSI`, palette du thème sombre par défaut, `build_page_couleurs.py`) ; sous chaque env du suivi, un panneau « Sortie de pio (en direct) », ouvert au départ
  de l'env, montre les lignes de pio au fil de l'eau comme le terminal de VS Code (chasse fixe, fond sombre, erreurs
  en rouge, avertissements en orange). Il défile seul tant qu'on est en bas, et s'arrête si on remonte pour lire.
  Il se **referme quand l'env réussit**, sauf si on l'a ouvert ou fermé soi-même ; il reste ouvert en échec ou arrêt.
  Au rechargement de la page, les envs réussis ne rouvrent pas le leur.
  Les barres d'esptool qui se réécrivent tiennent sur **une ligne par zone**, mise à jour (bootloader, firmware,
  `littlefs.bin`…). La page lit le journal de **cet** env par morceaux (`GET /sortie?env=…&octet=…` : seulement la
  suite, en lignes entières) ; la sortie d'un env terminé reste lisible tant que la page est ouverte.
- **Sons** (interrupteur en haut à droite, à côté de « Mode sombre », coché par défaut, mémorisé dans le
  navigateur) : à la fin d'un lancement, la page joue deux notes **montantes** si tous les envs ont réussi, deux
  notes **descendantes** en cas d'échec, d'arrêt ou si aucun env n'a abouti ; **trois bips aigus** quand elle se met en
  pause « Branchez la carte X sur COMn » (le lancement attend votre geste). Le son sort du PC qui affiche la page
  (Web Audio, sans fichier), même si l'onglet est en arrière-plan. Le navigateur ne laisse sonner une page qu'après
  un geste de l'utilisateur : le clic sur « Lancer » suffit. Après un rechargement de la page en plein lancement,
  cliquer une fois n'importe où dans la page. Une fin ou une pause déjà passée, rejouée au rechargement, ne sonne pas.
- Derniers choix : à chaque lancement accepté, la page
  écrit les lignes lancées (env, COM ou OTA, port, IP saisie) et les actions cochées dans `derniers.json` (dans
  `%LOCALAPPDATA%\outils_tasmota\build\`, hors dépôt, écriture atomique) ; à l'ouverture suivante elle recoche ces
  lignes et ces actions, sauf « Effacer puis téléverser », jamais recochée. Le port
  mémorisé ne sert que pour un env dont le port n'est pas réécrit dans un `.ini` (envs de l'amont), l'IP mémorisée
  que si aucune IP n'est lue dans `user_config_override.h`.
- Références de progression (nombre de `.o` du dernier
  build réussi de chaque env, base du % de compilation ; durée de chaque zone du dernier envoi par câble, base du
  % de l'envoi) : `references.json` dans
  `%LOCALAPPDATA%\outils_tasmota\build\`, hors dépôt. Un env jamais compilé par la page emprunte le total
  du plus grand env de la même puce (`tasmota32s3`, `tasmota32p4`…), affiché « 337/≈1682 fichiers » ;
  sans env de la même puce, seul le nombre de fichiers s'affiche.
- **Pourcentage pendant l'envoi** (ligne « Téléversement » de l'env) :
  - **par câble** : esptool écrit plusieurs zones (bootloader, partitions, boot_app0, safeboot, firmware,
    `littlefs.bin`). Dès le deuxième envoi du même env, la barre donne **un seul %** pour l'envoi entier, pondéré par
    la durée de chaque zone au dernier envoi (le FS, effacé avant d'être écrit, pèse plus que sa taille), avec
    « littlefs.bin 40 % · zone 6/6 ». Au premier envoi, ou si les zones ont changé, le % reste celui de la zone en cours ;
  - **OTA du firmware** : le % de l'envoi HTTP, un point à la fois ;
  - **OTA du FS** : le % des **octets** envoyés (pas du nombre de fichiers), mis à jour pendant chaque fichier, avec
    « 3/17 js/echarts.min.js.gz ».
- Chaque `pio run` réécrit `platformio_override.ini` ; `tasmota/user_config_override.h` ne l'est (`CFG_HOLDER`) que si
  son contenu hors ligne `CFG_HOLDER` a changé depuis le dernier incrément (`build/cfg_holder.py::doit_incrementer`) :
  **fichiers à commiter** après un lancement (la page cite les deux en fin de lancement, `build_serie.py::FICHIERS_MODIFIES`), et à sauvegarder avant
  une série d'essais.
- Banc : `test_build_*.py` dans `outils_docs/scripts_python/outils_pc/` (faux `pio`, carte simulée ; code de sortie
  0 = vert), à lancer avec le Python du penv PlatformIO ; détection des builds (cibles d'outils ignorées après leurs
  30 premières secondes) :
  `outils_docs/scripts_python/build/test_garde_build.py`.

<hr></hr>
