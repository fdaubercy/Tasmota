# Fichiers Berry par env

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Fichiers Berry par env (page web)

Une page pour décider, carte par carte, ce que devient chaque fichier Berry : **sur le file system**, **exclu** ou
**solidifié** dans le firmware. Elle écrit les listes de `platformio_tasmota_cenv.ini` (`custom_files_upload`,
`custom_files_exclude`, `custom_berry_solidify`) à la place d'une édition à la main, et crée un nouvel env à partir
d'une carte existante, renomme ou supprime un env. Conception : [spec](../../docs/superpowers/specs/2026-10-25-page-fichiers-berry-design.md) ;
plans : `tasks/plans/fichiers-berry-env.md`, `tasks/plans/fichiers-berry-suppression.md`.

Les listes de cartes (env affiché, carte modèle d'une création) sont groupées par lieu de la maison, « Mes bases » en
dernier (table de `outils_pc/lieux.py`, commune aux pages des outils). Ouverte avec `?lieu=` (lien de l'annuaire), la page choisit
la première carte du lieu (sauf si `?env=` est donné) et affiche le bandeau du lieu, sans rien cocher.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Configuration des cartes » : « Fichiers Berry par env ». L'annuaire
  peut l'arrêter à tout moment : rien n'est écrit avant « Enregistrer ».
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : fichiers Berry par env (http://127.0.0.1:7800) ». Ce
  n'est pas un `pio run` : utilisable pendant un build (l'écriture, elle, y est refusée).
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/fichiers_berry_web.py` (`--http 7800`,
  `--local`, `--sans-navigateur`) ; lien à jeton dans la console pour un autre appareil, comme les autres outils.
- **Cible PlatformIO** « Fichiers Berry par env (page web) » dans *Project Tasks > <env> > Custom* : démarre la page
  **détachée** (console dans `%LOCALAPPDATA%\outils_tasmota\consoles\fichiers_berry.log`) puis rend la main.
  Comme toute cible, **jamais pendant un build**.
- **Depuis la page build** : le lien « fichiers » de chaque env de *Mes cartes* / *Mes bases* ouvre cette page sur
  cet env (`?env=<nom>`) ; après un enregistrement, le lien « Construire / téléverser le FS » ouvre la page build
  avec l'env coché.

### Les trois états

Un `.be` de `data/fs` est **déjà sur le FS par défaut** (`copy_fs_image` recopie `data/fs` dans le dossier de la
carte) : on ne l'en retire que par `custom_files_exclude`, ou par `custom_berry_solidify` avec
`custom_files_exclude_solidified = ON`.

| État | Fichier de `data/fs` ou du dossier de la carte | Module de l'amont (`tasmota/berry/modules/`) |
|---|---|---|
| **Sur le FS** | aucune ligne (retiré des autres listes) | ligne dans `custom_files_upload` |
| **Exclu** (« Absent » pour l'amont) | ligne dans `custom_files_exclude` | ligne retirée de `custom_files_upload` |
| **Solidifié** | ligne dans `custom_berry_solidify` | non proposé |

- Fichiers proposés, **recensés à chaque chargement** (et par « Revérifier les fichiers ») : les `.be` de `data/fs`,
  ceux du dossier de la carte (`data/<lieu>/<carte>/`, aucun pour une base), les modules de l'amont (`.tapp`,
  `.be` de premier niveau, `.bec`). Dossiers `*sauvegarde*` ignorés.
- **Pendant un build**, `copy_fs_image` recopie `data/fs` dans le dossier de la carte : un `.be` de ce dossier
  identique octet pour octet à `data/fs/<même nom>` est une **copie temporaire**, ni proposée ni signalée comme
  homonyme ; la page la liste en avertissement (aussi après un build interrompu, qui en laisse). Un bandeau rouge
  dit qu'un build est en cours (toute écriture refusée) ou que la détection est impossible.
- `autoexec.be` est figé sur « Sur le FS ». Un fichier présent dans deux listes, ou deux fois dans la même (socle ET liste propre), est signalé comme incohérent ; « Appliquer » sur l'état affiché le nettoie (la ligne en double de l'env part, celle du socle reste) ; une
  ligne du `.ini` dont le fichier a disparu du disque est signalée, jamais retirée en silence. Les entrées non
  Berry (`.js`, `.gz`, `.html` de `custom_files_exclude`) sont montrées en lecture seule (« hors périmètre »).
- Les listes sont résolues comme PlatformIO les lit (`walk_options` : l'env, ses `extends` en commençant par le
  DERNIER cité, puis la section `[env]` ; `opt =;x` vaut `;x`) : le banc le compare à son `ProjectConfig`.
- Sans `custom_files_exclude_solidified = ON`, la page avertit : un fichier solidifié reste **aussi** sur le FS.
- Passer à « Solidifié » ne vérifie rien : avant de builder, `berry/solidifie_et_compile_berry.py <fichier>` (voir
  [SOLIDIFICATION_BERRY.md](../reference_berry/SOLIDIFICATION_BERRY.md)).

### Disposition et enregistrement

1. Choisir l'env ; choisir un fichier dans la liste, son état (boutons radio), une raison facultative, puis
   « Appliquer ». Plusieurs « Appliquer » s'accumulent avant d'enregistrer (marqués « en attente »).
2. Les trois colonnes **Sur le FS · Exclu · Solidifié** montrent l'état complet de l'env ; chaque entrée héritée
   porte un badge de son origine (`socle`, `modbus`, `historique` de `[berry_commun]`, ou l'env de base).
   Dans chaque colonne, les fichiers sont **regroupés par bloc du manifeste** (`blocs` de `outils_docs/schemas/modele_persist.json`),
   sous un en-tête qui donne le coût du bloc entier : « voletRoulants · 37,2 Ko solidifié, 51,9 Ko en .bec » (le survol donne le
   libellé). Deux blocs qui portent les mêmes fichiers forment un seul groupe (« ruban, ledRGB »), et tout fichier hors manifeste
   (socle, fichiers de la carte, modules de l'amont) est sous « Sans bloc ». Lecture seule : les lignes et leurs boutons sont
   inchangés, et si le manifeste est illisible la colonne redevient une liste à plat. Code : `fichiers_berry_blocs.py`.
   Une carte qui dépasse le **budget de RAM Berry de sa puce** (`puces.<puce>.budget` du manifeste) reçoit une ligne rouge
   « RAM Berry : env estimé à … » en tête des avertissements ; calcul partagé avec l'assistant persist : `budget_ram_berry.py`.
3. « Voir le diff » puis « Enregistrer » : sauvegarde horodatée avant d'écrire (voir « Sauvegardes » plus bas),
   fins de ligne et encodage gardés, **refus pendant un build** et si le fichier a changé depuis le diff.

- **Liste partagée** : si le fichier vient d'une liste partagée (`[berry_commun]`, ou option héritée d'un autre env),
  la page nomme les envs touchés ; deux issues : « Modifier la liste partagée (N envs) » ou « Annuler ».
- **Option héritée** : pour ajouter une ligne dans un env qui hérite de l'option, la page écrit
  `option = ${env:<base>.option}` puis la ligne : l'héritage est gardé.
- **Commentaires** : jamais modifiés ni supprimés ; le diff signale ceux de la section qui citent le fichier déplacé.
  La raison saisie est écrite en fin de ligne : `; <raison> (AAAA-MM-JJ)`.

> [!WARNING]
> Réécrire le `.ini` change l'empreinte du projet : le **build suivant repart de zéro** (PlatformIO supprime tout
> `.pio/build`). Rien n'est commité par la page.

### Créer un env à partir d'une carte modèle

« Créer un env à partir de… » : carte modèle, base (celle du modèle par défaut), lieu, nom, puis les champs
d'identité préremplis (« Proposer ») et modifiables : `CODE_IMAGE_STR`, `PROJECT`, `WIFI_IP_ADDRESS` (`0.0.0.0` =
DHCP), `WIFI_RGX_SSID`, `MQTT_CLIENT_ID`, `MQTT_TOPIC`, `MQTT_GRPTOPIC`, `FRIENDLY_NAME`, et le define
(`FIRMWARE_ESP<puce>_<LIEU>_<NOM>`). Après le diff des trois morceaux, la page écrit :

1. la section `[env:<puce>-<lieu>-<nom>]` du cenv, copiée du modèle (`extends` = la base, define remplacé,
   `custom_files_upload` = celui de la base + le nouveau dossier, chemins du dossier du modèle réécrits, **ports COM
   non recopiés**), sous le bandeau `; LOCALISATION:` du lieu, sinon en fin de fichier ;
2. le dossier `data/<lieu>/<puce>-<nom>` (nom calculé comme `transform_name`), copie de celui du modèle ; dans le
   `_persist.json`, seules les valeurs d'identité sont remplacées, dans le texte, le reste octet pour octet ;
3. la section `#elif defined(FIRMWARE_…)` de `tasmota/user_config_override.h`, après celle du modèle, defines
   d'identité remplacés (dont le `Hostname` de `USER_BACKLOG` et le `NAME` du `USER_TEMPLATE`). Les conditions
   internes qui citent encore l'ancien define sont signalées, à revoir à la main.

Refus si l'env, le dossier ou le define existent (un define seulement cité en commentaire ne compte pas), si un
champ d'identité est vide ou contient `"`, `\`, `;` (une commande de plus dans `USER_BACKLOG`), un espace (`PROJECT`,
`MQTT_CLIENT_ID`, `MQTT_TOPIC`, `MQTT_GRPTOPIC`, `WIFI_IP_ADDRESS`) ou un joker MQTT `+`/`#`, ou pendant un build.
Une IP (hors `0.0.0.0`), un topic ou un client MQTT déjà portés par une autre carte ne sont qu'un **avertissement** :
c'est normal pour une carte qui en remplace une autre (P4 après l'ancien maître S3, caves) ; sinon les deux cartes se
déconnecteront l'une l'autre. **Mots de passe masqués** dans le diff. Le dossier de la nouvelle
carte ne reçoit ni les `*sauvegarde*` du modèle, ni ses copies temporaires d'un build (fichiers identiques à
`data/fs`, sous-dossiers `fs`, `json`, `sd`). La nouvelle carte apparaît ensuite d'elle-même dans la page build.

### Renommer un env

« Renommer cet env… » (cartes seulement, pas les bases) : nouveau lieu et/ou nouveau nom, puis « Proposer » :
l'identité (les 8 champs de la création) et le define sont **reproposés d'après le nouveau nom**, modifiables. Après
le diff, « Renommer » (grisé si la saisie change après le diff) écrit, en une seule opération :

1. la section `[env:<puce>-<lieu>-<nom>]` du cenv, copie de l'ancienne (même base, chemins du dossier et define
   remplacés), placée comme à la création ; l'ancienne est retirée ;
2. la section du `.h` avec la nouvelle identité ; l'ancienne est retirée ;
3. le dossier de la carte **déplacé** (pas copié) vers son nouveau nom, `_persist.json` aux nouvelles valeurs
   d'identité (le reste octet pour octet) ;
4. dans `platformio_override.ini`, la ligne de `default_envs` garde son état (active ou commentée) sous le nouveau
   nom, et `data_dir` suit le dossier.

Garder son IP, son topic ou son client MQTT est permis ; une identité portée par une AUTRE carte est signalée,
comme à la création. Un commentaire de section du `.h` qui ne cite pas l'env est signalé (à revoir). Refus si un autre env référence celui-ci (`extends`, `${env:<env>…}`), si le nouvel env, dossier ou
define existe déjà, ou pendant un build. Ce qui cite encore l'ancien nom (commentaires, scripts, bancs) est signalé,
jamais modifié. Renommer puis revenir à l'ancien nom redonne des fichiers identiques.

### Supprimer un env

« Supprimer cet env » : pour un env qui ne sert plus, ou pour défaire une création ratée. Après le diff,
« Supprimer » :

1. retire la section `[env:…]` du cenv ; le bandeau `; LOCALISATION:` juste au-dessus part aussi s'il ne couvre plus
   rien (lieu créé puis vidé : créer puis supprimer redonne le cenv d'origine) ;
2. retire la section du `.h` (commentaire `// -- Options for …` compris ; si c'était le `#if` de tête, la suivante
   devient `#if`). Section partagée par deux envs (`#if defined(A) || defined(B)`) : seul `defined(<env>)` est
   retiré de la condition ;
3. renomme le dossier `data/<lieu>/<carte>` en `<carte>-sauvegarde` (`-sauvegarde-2`, `-3`… si le nom est pris) :
   rien n'est effacé, les builds et la page l'ignorent. À retirer à la main quand on est sûr ;
4. retire l'env de `default_envs` (ligne active ou commentée, dans le seul bloc `default_envs`) ; un `data_dir` qui
   désignait le dossier est signalé, et aussi un `default_envs` sans plus aucun env actif (`pio run` sans `-e`
   construirait alors tous les envs).

Les commentaires `// -- Options for …` de la section du `.h`, et ceux qui les suivent jusqu'au `#if`, partent avec elle.

Refus pour une base dont d'autres envs héritent ou qu'ils référencent (envs nommés), pour un env de l'amont, ou
pendant un build. Les citations de l'env ailleurs sont signalées. Créer puis supprimer un env redonne un cenv, un
`.h` et un `platformio_override.ini` identiques à l'origine.

### Sauvegardes

Chaque écriture (enregistrement, création, renommage, suppression) est **atomique** : si un fichier ne peut pas
être écrit en route, ce qui a déjà été fait est défait (fichiers remis, dossier copié retiré, dossier renommé
remis). Avant d'écrire, chaque fichier modifié est copié dans
`%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\<date-heure>-<nature>\` (chemins du dépôt gardés),
**gardé 30 jours** ; la page affiche ce dossier après l'opération. Plus de `.bak` commun avec la page build.
Une erreur inattendue (fichier verrouillé…) est affichée avec son message (réponse 500), sans rien laisser à moitié.
Si l'annulation elle-même échoue, le message dit ce qui reste à remettre à la main. Chaque fichier est écrit par
remplacement (jamais tronqué), et les écritures passent une par une (double clic, deux onglets). Si la page est
arrêtée en pleine opération (annuaire, Ctrl+C), la sauvegarde garde sa marque `en_cours.json` : au chargement suivant,
la page affiche un bandeau rouge « Opération interrompue » avec les étapes à vérifier ; « J'ai vérifié » retire la
marque, la sauvegarde reste.

### Bancs

Dans `outils_docs/scripts_python/outils_pc/`, avec le Python du penv PlatformIO (code de sortie 0 = vert) :
`test_fichiers_berry_ini.py`, `_etat.py`, `_ecriture.py` (relecture par `ProjectConfig` de PlatformIO),
`_creation.py` (copie du dépôt dans un dossier temporaire), `_suppression.py`, `_renommage.py`, `_sauvegarde.py`,
`_web.py`, `_blocs.py` (regroupement par bloc, avec témoins), et la sonde Chrome
`test_fichiers_berry_page_chrome.py` ; cible Custom : `build/test_cible_fichiers_berry.py`. Aucun banc n'écrit
dans le vrai dépôt ni dans le vrai dossier des sauvegardes.
