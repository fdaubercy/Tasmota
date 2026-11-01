---
chantier: temps-compilation
titre: Réduire le temps des compilations et éviter les recompilations complètes
statut: actif
cree: 2026-11-01
maj: 2026-11-01
source: breezy-mapping-backus.md
objectif: Ne plus recompiler tasmota.ino.cpp ni purger .pio/build sans raison, mesurer avant de séparer les dossiers de build par env, puis montrer l'occupation mémoire et régler les partitions depuis la page build
---
# Réduire le temps des compilations

## Contexte
Question du 2026-11-01 (« la page Build peut-elle lancer 2 compilations ensemble ? » → non, et ce n'est pas
souhaitable), puis demande d'un topo sur ce qui évite les recompilations complètes.

Ce que montrent les journaux de la page (`%LOCALAPPDATA%\outils_tasmota\build\journaux\`) :
- **Changer d'env purge `.pio/build`**. L'empreinte du projet (`platformio/project/helpers.py::compute_project_checksum`)
  hache la config de TOUS les envs (dont `data_dir`, réécrit à chaque env) et la liste des `.c/.h` de `lib/`
  (les `_temp_be_*.c` de `berry_custom` changent selon l'env). P4 du 01/11 04:32, après le différentiel :
  837 fichiers récupérés du cache, 177 recompilés.
- **Le cache objet amortit** : `build_cache_dir = .cache` (`platformio.ini`, amont).
- **`CFG_HOLDER` est incrémenté à CHAQUE `pio run`** (`pre_utilitaires_platformio.py::increment_config_holder`,
  appelé sans condition hors safeboot et hors cibles d'outils, envois et buildfs compris). `user_config_override.h`
  change, donc `tasmota.ino.cpp` n'est jamais repris du cache, ni Berry (`berry_conf.h` inclut `my_user_config.h`).
  Cuve du 01/11, build réussi : 175 fichiers recompilés (berry_tasmota 66, berry 42, berry_custom 35…), 584 repris, 51 min.
  Le « 655 s pour 1 fichier » du 31/10 écrit d'abord ici venait d'un build ÉCHOUÉ (coupé en cours) : chiffre faux.

Décisions de l'utilisateur (2026-11-01) :
- `CFG_HOLDER` incrémenté **seulement si** `user_config_override.h` (hors ligne `CFG_HOLDER`) a changé depuis le dernier
  incrément. Le `_persist.json`, d'abord inclus, a été retiré le même jour à la demande de l'utilisateur (175 fichiers
  recompilés pour toutes les cartes, alors qu'il ne passe pas par SECTION1). État commun à tous les envs.
- Autonomie (2026-11-01) : Claude avance seul, compilations de mesure comprises, quand aucun build ne tourne ; seuil de
  A2 : 10 min par changement d'env ; purge après les mesures ; essai QEMU borné. Restent à l'utilisateur : flash d'une
  carte, modification de la table d'un env réel, Defender.
- Dossier de build par env : **mesurer d'abord**, décider ensuite.
- Port COM : **reste dans le cenv** (changement rare, la purge est acceptée).
- Inclus : contrôle `lib_ignore` sauté sans compilation, script d'exclusions Defender, purge de `.cache`.
- Rejeté : deux compilations en parallèle (fichiers partagés ; worktree possible mais 4 cœurs déjà saturés),
  coupure de la LTO (firmware différent de celui livré).

Décisions sur la mémoire et les partitions (2026-11-01, actions A7 à A10, à réaliser plus tard) : interface **modèle B**
(un curseur par partition) ; mesures dans un onglet + résumé sur la page d'accueil ; **OTA bloquée** tant qu'une table
modifiée n'a pas été flashée par câble ; ajoutés : lecture sur la carte, ajout d'une partition, préréglages et CSV.
Inspiration : ESP32 Partition Builder (README seul, l'outil n'a pas pu être lu).

Contraintes : jamais de `pio run` pendant un build de l'utilisateur (hook `garde_build`, leçon du 2026-10-31) ;
pas de modification de fichiers amont (`pio-tools/`, `platformio.ini`) ; lire `tasks/lessons.md` avant le code.

## A1 — CFG_HOLDER incrémenté seulement si le .h a changé
- [x] Module voisin `build/cfg_holder.py` — preuve : `cfg_holder.py::doit_incrementer`, `::enregistre`, `test_cfg_holder.py` VERT
  (empreinte de `user_config_override.h` sans la ligne `#define CFG_HOLDER` ; état commun dans `%LOCALAPPDATA%\outils_tasmota\build\cfg_holder.json`, hors
  dépôt ; illisible ou absent = incrément)
- [x] Incrément seulement pour un `pio run` qui construit le firmware — preuve : `cfg_holder.py::construit_firmware`, 7 cas VERTS
  (aucune cible, `upload`, `erase_upload` ; jamais `nobuild`, `buildfs`, `uploadfs` seuls)
- [x] Garder le FS joint à l'upload série — preuve : compilation de mesure du 01/11 07:43 sans changement : « Building firmware.bin », « Image LittleFS créée », « Utilisera une commande de téléchargement personnalisée »
  (la post-action de `firmware.bin`, `pio-tools/post_esp32.py::esp32_create_combined_bin`, ne tournait que parce que
  `CFG_HOLDER` forçait l'édition des liens ; `env.AlwaysBuild` + `env.NoCache` sur `firmware.bin` dans le pré-build)
- [x] Commentaires « CFG_HOLDER change à chaque run » corrigés — preuve : `build_envs.py::_fs_avec_firmware`, en-têtes de `syslog_tasmota.py` et `build_serie.py`
- [x] `increment_config_holder` inchangé (rend True), appelé seulement si `cfg_holder.doit_incrementer` — preuve : `pre_utilitaires_platformio.py` (bloc « CFG_HOLDER : seulement… »), `test_config_holder.py` VERT
  (état enregistré après l'écriture du .h ; lignes « CFG_HOLDER inchangé : … » / « CFG_HOLDER incrémenté : … »)
- [x] Banc `build/test_cfg_holder.py` — preuve : 19 cas VERTS, 6 mutants tués, contrat avec la vraie `increment_config_holder`
- [x] Mesure réelle — preuve : cuve, 01/11 06:40 (incrément) 51 min, 175 compilés / 584 repris ; 01/11 07:43 « CFG_HOLDER inchangé », 23 min 24 s, 1 compilé / 771 repris
  (étapes datées par les fichiers produits : préparation ~8 min 30, `tasmota.ino.cpp` ~9 min sur un cœur, lien LTO 5 min 38)

## A11 — Ce qui reste dans les 23 min d'un build sans changement (constaté le 01/11)
- [x] `tasmota.ino.cpp` recompilé sans changement : cause et correctif — preuve : journal `20261101-134632` (`SCONSFLAGS=--debug=explain`), plus aucun « Compiling » ni « Linking », 355 s contre 771 s à 13:15
  (`pioino.py::InoToCPPConverter._gcc_preprocess` : nom temporaire aléatoire écrit en ligne 1 par `g++ -E`, seule différence entre deux générations ; `build/ino_stable.py`, banc `test_ino_stable.py`)
- [ ] Lien LTO en série malgré `post_lto_parallele.py` (« lto-wrapper: using serial compilation of 32 LTRANS jobs ») :
  hypothèse, GCC a besoin d'un `make` sous Windows pour paralléliser et le poste n'en a pas ; vérifier, puis essayer un `make`
  dans le PATH du build, et mesurer
- [ ] Préparation de ~8 min 30 : détailler (contrôle `lib_ignore` 80 s à chaque compilation, LDF, solidification Berry de
  6 bibliothèques, `dump-defines.py`) et ne garder que ce qui sert

## A2 — Mesurer le coût d'un changement d'env, puis décider du dossier de build par env
- [x] Relevé des durées et du nombre de fichiers compilés, même env répété vs après changement d'env — preuve : cuve sans changement
  23 min 24 s (1 compilé) ; P4 après la cuve 29 min 39 s (177 compilés : son propre CFG_HOLDER/défines) ; retour à la
  cuve après le P4 14 min 57 s, 1 compilé, le reste repris de `.cache` (journaux du 01/11 de la page)
- [x] Taille de `.cache` et de `.pio/build` relevée (hors build) — preuve : `.cache` 17 391 Mo (dont 5 383 Mo inutilisés depuis 30 j) ; `.pio/build` 183 Mo
- [x] Synthèse chiffrée présentée à l'utilisateur ; décision consignée ici (faire / ne pas faire) — preuve : la purge
  de `.pio/build` au changement d'env ne coûte rien de mesurable (le cache objet rend 771 objets sur 772) :
  **ne pas faire** (proposé le 01/11 sur ces chiffres ; à rouvrir si un retour d'env dépasse 10 min de plus qu'un
  build sans changement). Si « faire » :
  nouveau plan (`PLATFORMIO_BUILD_DIR` par env posé par la page, ~18 fichiers dont le pré-build
  `pre_utilitaires_platformio.py` qui code `.pio/build` en dur pour `copy_fs_image`)

## A3 — Contrôle lib_ignore sauté quand le pio run ne compile pas
- [x] Vérifier si `buildfs`/`uploadfs` seuls passent par le scan des dépendances — preuve : non, la plateforme 2026.10.50
  le coupe (`builder/main.py::switch_off_ldf` : uploadfs, uploadfsota, buildfs, erase, download_fs)
- [x] Contrôle sauté si le `pio run` ne compile rien — preuve : `verifie_lib_ignore.py::compile_rien`, `::controle(env, cibles)`, 9 cas VERTS, témoin (buildfs oublié) : 3 KO
  (`nobuild`, ou seulement des cibles de `SANS_COMPILATION` ; cibles passées par le pré-build)
- [x] Ligne « lib_ignore de <env> : controle saute… » lue par la page — preuve : `build_progression._LIB_IGNORE` la capte (essai direct)
- [x] Bancs verts — preuve : `test_verifie_lib_ignore.py`, `test_build_progression.py`, `test_data_dir.py`, `test_copie_fs.py` VERTS (Python de PlatformIO)
- [x] Vu dans le journal d'un `nobuild upload` ou d'un `buildfs` réel — preuve : buildfs de la cuve lancé par la page le 01/11 09:01, journal `20261101-090109-…-buildfs.log` ligne 6, SUCCESS en 110,8 s

## A4 — Script d'exclusions Windows Defender
- [x] Script `maintenance/exclusions_defender.ps1` — preuve : analyse PowerShell 0 erreur ; refuse hors administrateur (essai, code 1)
  (exclusions `.pio`, `.cache` du dépôt et `~/.platformio` ; `-Verifier` = lecture seule, idempotent)
- [x] Lancé par l'utilisateur — preuve : déclaré fait par l'utilisateur le 2026-11-01 ; non relu par Claude (`Get-MpPreference` sans administrateur : « Must be an administrator to view exclusions »)
- [x] Mention dans `CLAUDE.md` — preuve : § « MONTER UN NOUVEAU POSTE », sous-titre « 5. Exclusions Windows Defender »

## A5 — Purge du cache objet .cache
- [x] Critère d'âge — preuve : SCons 4.11.1 `CacheDir.py::CacheRetrieveFunc` fait `os.utime(cachefile)` à chaque reprise : date de modification = dernière utilisation
- [x] Outil `maintenance/purge_cache_build.py` — preuve : `--dry-run` réel : 17 391 Mo, 29 185 objets / 5 383 Mo libérables (7 s)
  (objets inutilisés depuis N jours, défaut 30 ; fichier `config` du cache gardé ; refus pendant un build par `garde_build.builds_en_cours`)
- [x] Banc sur un faux cache — preuve : `test_purge_cache_build.py` VERT (9 cas, témoin objet récent gardé) ; mention dans `outils_docs/README.md`
- [ ] Purge réelle lancée par l'utilisateur (sans `--dry-run`)

## A6 — Documentation
- [x] `CLAUDE.md` § « Vigilances de build » et carte des documents — preuve : `verifie_references_docs.py` 0 défaut
- [x] `outils_docs/README.md` § build — preuve : sous-titre « Ce qui fait recompiler (et ce qui ne le fait plus) »

## A7 — Mesurer la mémoire de chaque env (à faire plus tard)
Décidé le 2026-11-01. Maquettes, chiffres réels et contraintes : `outils_docs/partitions/`.
- [x] Module `outils_pc/build_memoire.py` — preuve : `build_memoire.py::analyse` sur les vrais P4, cuve, cave, différentiel (tables, app0, safeboot, zones RAM ; cave et différentiel sans journal : note)
  (app0 = ligne « Flash: » du dernier journal RÉUSSI ; safeboot = binaire cité par le journal ; FS = `littlefs_data`
  arrondi au bloc, estimation : l'image écrite par post_esp32.py n'est pas lisible avec les réglages du buildfs)
- [x] Mesures enregistrées dans `%LOCALAPPDATA%\outils_tasmota\build\memoire\<env>.json` — preuve : `build_memoire.py::enregistre`, `::derniere`, cas du banc
- [x] Analyse automatique après chaque compilation réussie — preuve : `build_serie.py::Serie._execute_env` ; `test_build_serie.py` VERT (effective au prochain redémarrage de la page)
- [x] Analyse lancée seule — preuve : `build_web.py` `POST /memoire/analyser` et `GET /memoire` ; `test_build_web.py` VERT
- [ ] Lecture sur la carte : `Status 4` et `UfsSize`/`UfsFree` (PSRAM, tas, FS réel), par le transport HTTP de `build_ota_http.py` ; carte muette = message, pas d'échec
- [x] Banc `test_build_memoire.py` — preuve : 16 cas VERTS sur des extraits de vrais journaux P4 et S3, 6 mutants tués (un mutant équivalent écarté, et le test mort qu'il révélait supprimé)

## A8 — Onglet « Mémoire et partitions », modèle B (à faire plus tard)
- [x] Module `outils_pc/build_page_memoire.py` — preuve : marques `/*CSS_MEMOIRE*/`, `<!--VUE_MEMOIRE-->`, `/*JS_MEMOIRE*/` de `build_page.py` ; sonde `test_build_page_memoire_chrome.py` VERTE (22 vérifications) ; inséré comme `build_page_fichiers.py`
- [x] Liste des envs — preuve : `build_page_memoire.py` (`mEnvs`), sonde `test_build_page_memoire_chrome.py` VERTE (22 vérifications) (env par défaut, pas d'env amont) ; par défaut le premier env coché sur la page d'accueil ; en choisir un autre ne change pas les cases
- [x] Jauges — preuve : sonde `test_build_page_memoire_chrome.py` VERTE (22 vérifications) (7 zones, 73,0 %, FS marqué ≈) ; jauges par zone (capacité, occupé, libre, date de l'analyse), orange à 85 %, rouge à 95 %
- [x] Barre et lignes — preuve : sonde `test_build_page_memoire_chrome.py` VERTE (22 vérifications) (app0 +64 Ko -> FS en 0x4C0000, nvs/otadata/app0 non supprimables) ; barre de la flash et une ligne par partition : case de suppression, curseur par pas de 64 Ko, champ en Ko, occupé
- [ ] Résumé sur chaque env de la page d'accueil (app0, FS, DIRAM), avec les mêmes seuils ; un clic ouvre l'onglet
- [ ] Bouton « Analyser » et bouton « Lire sur la carte »
- [x] Sonde Chrome — preuve : sonde `test_build_page_memoire_chrome.py` VERTE (22 vérifications), dépôt d'essai temporaire, écriture jusqu'au bout puis OTA refusée (409) ; sonde Chrome `test_build_page_memoire_chrome.py`, exécutée dans un vrai navigateur ; aucune écriture dans le dépôt réel

## A9 — Écrire la table de partitions d'un env (à faire plus tard)
- [x] Module `outils_pc/build_partitions.py` — preuve : `build_partitions.py::valide`, 11 cas de refus VERTS ; validation (alignement et tailles de 64 Ko, `nvs` en 0x9000, `otadata` en 0xE000, `app0` obligatoire, minimum = occupé, somme = flash), mêmes règles que la maquette
- [x] Suppression — preuve : `build_partitions.py::prepare` (avertissements, repris par le `confirm` de la page), `test_build_partitions.py` VERT, sonde VERT : `safeboot` et `spiffs` demandent une confirmation qui nomme la conséquence ; `nvs`, `otadata`, `app0` refusées aussi côté serveur
- [x] Écriture d'un CSV propre à l'env — preuve : `build_partitions.py::prepare`, `::ecrit` (`partitions/env_<env>.csv`, `build_envs.py::pose_option`), routes `POST /partitions/diff` et `/partitions/ecrire` de `build_web.py` ; écriture d'un CSV propre à l'env dans `partitions/`, et de `board_build.partitions` dans sa section du cenv : diff d'abord, transaction et sauvegarde (`fichiers_berry_sauvegarde.Transaction`), refus pendant un build ; les autres envs ne changent pas
- [x] OTA BLOQUÉES — preuve : `build_partitions.py::ota_bloquee`, `::libere` appelés par `build_serie.py::Serie.controle` et `::_execute_env` ; OTA du firmware et du FS BLOQUÉES pour un env dont la table a changé, avec le motif affiché, jusqu'au prochain « Effacer puis téléverser » réussi (état hors dépôt, contrôle côté serveur dans `build_serie.py`)
- [x] Rappels — preuve : avertissements de `build_partitions.py::prepare` (persist, purge, OTA, héritiers) ; avant l'écriture, rappeler que le flash série remplace le persist de la carte par celui du dépôt, et annoncer la purge de `.pio/build` (le cenv change)
- [x] Vérifier `post_esp32.py::patch_partitions_bin` et `partition_core` — preuve : lecture du code le 01/11 (voir dessous)
  `patch_partitions_bin` écrit la taille du FS aux octets 0x89-0x8B (5e entrée) et l'empreinte MD5 en 0xA0 : il suppose
  EXACTEMENT 5 partitions. Avec 4 (safeboot ou FS supprimé) ou 6 (ajout), il corromprait la table. Il ne s'applique que
  lors d'un upload série quand esptool détecte une flash plus grande que celle déclarée (`esp32_detect_flashsize`).
  `partition_core.be::resize_fs_to_max` et `::invalidate_spiffs` supposent le FS en DERNIÈRE position.
- [x] Tables de 4 ou 6 partitions, FS toujours dernier — preuve : `test_build_partitions.py` VERT (image du safeboot retirée vérifiée par `PlatformBoardConfig`) ; essai sur carte non fait
  (`post_esp32.py::esp32_detect_flashsize` ne teste la flash que pour la cible `upload` exacte : `erase_upload` n'est jamais corrigé. Plutôt qu'un contrôle de la flash détectée, `build_partitions.py::motifs_envoi` refuse donc l'`upload` par câble de ces tables ; sans safeboot, `board_upload.arduino.flash_extra_images` vidé dans la section de l'env)
- [x] Préréglages (tables de `partitions/`), même validation ; table identique à un fichier = l'env pointe vers lui — preuve : `test_build_partitions.py` VERT (14 mutants), `test_build_page_memoire_chrome.py` VERT
- [x] Import et export d'un CSV, passés par la même validation — preuve : `build_partitions.py::lit_import`, `test_build_partitions.py` VERT, sonde `test_build_page_memoire_chrome.py` VERT
- [x] Banc — preuve : `test_build_partitions.py` VERT, 27 cas, 10 mutants tués, deux vraies tables reproduites octet pour octet ; banc `test_build_partitions.py` (copies temporaires du cenv, relues par `ProjectConfig`, avec mutants) ; table produite identique octet pour octet à `esp32_partition_app3904k_fs11584k.csv` sans modification
- [ ] Essai réel par l'utilisateur sur une carte, par câble : démarrage, FS et Berry vérifiés, puis OTA de nouveau permise

## A10 — Annuaire et documentation de la fonction (à faire plus tard)
- [x] Descriptif de la tuile — preuve : `annuaire_registre.py` (entrée `build`), `test_annuaire.py` VERT ; descriptif de la tuile « Build et téléversement » (`annuaire_registre.py`) : occupation de la mémoire et réglage des partitions par env, écrit quand la fonction existe ; `test_annuaire.py` vert
- [x] Documentation — preuve : `outils_docs/README.md` § « Onglet « Mémoire et partitions » », `CLAUDE.md` (carte des documents), `verifie_references_docs.py` 0 défaut ; `outils_docs/README.md` § build et `CLAUDE.md` (carte des documents, nouveaux modules)

## Améliorations restantes
- [ ] [projet] Dossier de build par env, si A2 conclut « faire » (A2 a conclu « ne pas faire » le 01/11)
- [ ] [projet] `cpptools` (indexeur C/C++ de VS Code) occupe 0,75 cœur sur 4 hors build (mesure du 01/11, 8 s) : exclure `.pio`, `.cache` et `lib/` de son analyse, dans le profil VS Code, à essayer et à mesurer
- [ ] [projet] QEMU d'Espressif (ESP32-S3 seulement, pas le P4 ; sans support officiel) : essai borné pour démarrer une table modifiée sans toucher une carte, avant l'essai réel de A9 ; démarrage de Tasmota non garanti
- [ ] [projet] Sortir le port COM du cenv si les changements de port deviennent fréquents
- [ ] [projet] Défaut existant, à vérifier : un `nobuild upload` (envoi après la pause « rebranchez la carte ») n'a
  pas de règle pour `firmware.bin` (`builder/main.py`, bloc `nobuild`), donc la post-action FS de `post_esp32.py` ne tourne
  pas et le FS ne serait PAS joint, alors que la page grise « Construire / Téléverser le FS » (`build_serie.py::Serie._plan`).
  Aucun journal `nobuild` pour trancher.
- [ ] [projet] `CFG_HOLDER` et `user_config_override.h` sont communs à tous les envs : modifier le `.h` pour une carte fait
  tout recompiler aux autres et recharge leurs réglages SECTION1 au flash suivant. À revoir seulement si cela gêne.

## Vérification
- A1 : `test_cfg_holder.py` vert (mutants tués) ; deux compilations successives du même env par l'utilisateur, la
  seconde sans « Compiling …tasmota.ino.cpp.o » et nettement plus courte ; `git diff tasmota/user_config_override.h`
  vide après un build sans changement.
- A3 : journal d'un `nobuild upload` sans les 11-24 s du contrôle.
- A4/A5 : `-Verifier` et `--dry-run` en lecture seule, puis exécution par l'utilisateur.
- Aucun `pio run` lancé par Claude pendant un build de l'utilisateur.
