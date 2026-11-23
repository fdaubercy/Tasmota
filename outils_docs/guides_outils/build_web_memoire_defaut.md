# Build : mémoire, partitions et env par défaut

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

### Onglet « Mémoire et partitions » : occupation et table de chaque env

L'onglet s'ouvre sur l'env coché dans l'onglet Build (sinon la première carte) ; la liste en haut (cartes groupées par
lieu, bases en dernier) en choisit un autre sans toucher aux cases.

- **Occupation** : une jauge par partition de la flash et par zone RAM du journal (DIRAM, IRAM, RTC, LP RAM...),
  orange à 85 %, rouge à 95 %. Elle est relevée seule après chaque compilation réussie ; « Analyser » relit le dernier
  build sans rien compiler. La taille du FS est estimée (`≈`) d'après les fichiers de l'image ; PSRAM et tas ne se
  lisent que sur la carte (pas encore dans l'onglet).
- **Table** : un curseur et un champ en Ko par partition, par pas de 64 Ko ; le FS (sinon app0) compense pour que toute
  la flash reste répartie. `nvs`, `otadata` et `app0` ne se suppriment pas. « Voir le diff » fait valider la table par
  le serveur (`build_partitions.py`), puis « Écrire » pose `partitions/env_<env>.csv` et `board_build.partitions` dans
  la section de l'env : la table par défaut, partagée, n'est jamais modifiée. « Partir d'une table existante » règle les
  curseurs sur une table de `partitions/` à la taille de la flash ; si la table finale est identique à un de ces fichiers,
  l'env pointe vers lui et aucun CSV n'est créé (c'est aussi le retour à la table par défaut) (copie d'origine dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`).
- **Importer, exporter, ajouter** : « Importer un CSV » passe par les mêmes contrôles (adresses contiguës, pas de colonne
  Flags), « Exporter en CSV » télécharge la table réglée, « Ajouter la partition » l'insère avant le FS, 64 Ko pris sur lui.
- **Résumé dans l'onglet Build** : sous le nom de chaque env déjà analysé, `app0`, `FS` et `DIRAM` en %, en orange à 85 %, en
  rouge à 95 % comme les jauges. Un clic ouvre cet onglet sur l'env.
- **Lire sur la carte** : interroge la carte par le réseau, en lecture seule (`Status 4`, `Status 5`, `UfsSize`, `UfsFree`), à
  l'adresse de sa ligne dans l'onglet Build : FS réel (le `≈` du dessus est une estimation), PSRAM, tas libre, nom de la carte
  lue. Rien n'est enregistré. Carte muette : un message. Esclave joint par le maître : redirection posée et identité vérifiée
  d'abord. Refusé pendant un envoi.
- **Nom du fichier** : facultatif. Vide, la table part dans `partitions/env_<env>.csv` ; saisi, dans `partitions/<nom>.csv`.
  Un fichier nommé qui existe déjà n'est jamais réécrit, ni un `env_` qui sert aussi à un autre env. « Voir le diff » compare
  la table à TOUS les fichiers de `partitions/` : si elle est identique à l'un d'eux, la page le propose ; OK = l'env pointe
  vers lui, Annuler = un nouveau fichier est créé quand même.
- **4 ou 6 partitions** : acceptées, le FS restant dernier et un safeboot restant en 0x10000. Sans safeboot, l'env reçoit
  `board_upload.arduino.flash_extra_images =` (vide) et l'OTA du firmware est refusée. Avec un FS, le « Téléverser le
  firmware » par câble est refusé, seul « Effacer puis téléverser » passe : `post_esp32.py::patch_partitions_bin` suppose
  5 partitions. ⚠️ La page ne contrôle pas un `pio run -t upload` lancé hors d'elle ; une telle table n'a pas encore été
  essayée sur une carte.
- **Après l'écriture** : la nouvelle table ne part qu'avec un « Effacer puis téléverser » par câble, qui remplace aussi
  le persist de la carte par celui du dépôt. D'ici là, toute OTA de l'env est refusée (une OTA n'écrit jamais la
  table). Le prochain build repart de zéro (le cenv a changé).
### Onglet « Env par défaut (Platformio override) » : ce que compile un simple `pio run`

Le bloc `default_envs` de `platformio_override.ini` fixe les envs compilés par un `pio run` sans `-e`. L'onglet le
modifie sans ouvrir le fichier ; il ne lance rien.

- **Colonnes** : une par puce (Safeboot, ESP32, ESP32-S3, ESP32-P4, Autres), avec les lignes du bloc. Vos cartes et bases
  qui n'y sont pas apparaissent aussi, marquées « absent du bloc » : cochées, elles y sont ajoutées dans le groupe de
  leur puce (sinon à la fin du bloc) ; non cochées, rien n'est écrit pour elles.
- **Modifications en attente** : le futur fichier entier, recalculé à chaque case, lignes changées surlignées. Rien
  n'est écrit avant « Enregistrer ». Seul l'état commenté ou actif d'une ligne change : commentaires, indentation et
  fins de ligne restent. Copie d'origine dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`.
- **« Cocher ces envs dans l'onglet Build »** remplace la sélection de cet onglet, sans toucher aux actions : on lance
  ensuite par le bouton habituel. Les cases non enregistrées sont reportées aussi.
- **À la création d'un env** (pages Fichiers Berry par env et Assistant persist) : la case « Ajouter à `default_envs` »,
  décochée par défaut, l'y rend actif du même coup, en une seule écriture ; le diff le montre avant « Créer ».
- **Refus** : liste vide (un `pio run` construirait tous les envs), env inconnu, ligne `default_envs = x` ou ligne à
  plusieurs envs à corriger à la main, écriture pendant un lancement ou un build, fichier changé depuis l'aperçu.
- **À savoir** : enregistrer change l'empreinte du projet, donc le `pio run` suivant vide `.pio/build` (les objets
  inchangés reviennent du cache `.cache`). L'ordre des lignes n'a aucun effet : `pio run` suit l'ordre des sections
  des `.ini`, c'est pourquoi l'onglet ne propose pas de réordonner.
