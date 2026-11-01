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
  change, donc `tasmota.ino.cpp` (~7,6 Mo, un seul cœur) n'est jamais repris du cache. Cuve du 31/10 :
  655 s pour UN fichier compilé (`tasmota.ino.cpp`) + édition de liens LTO.

Décisions de l'utilisateur (2026-11-01) :
- `CFG_HOLDER` incrémenté **seulement si** `user_config_override.h` (hors ligne `CFG_HOLDER`) **ou** le `_persist.json`
  de l'env a changé depuis le dernier incrément de cet env. NB signalé : le persist vit sur le FS et ne passe pas
  par SECTION1 ; l'inclure recharge les réglages Tasmota de la carte au prix d'une recompilation (choix assumé).
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

## A1 — CFG_HOLDER incrémenté seulement si le .h ou le persist de l'env a changé
- [x] Module voisin `build/cfg_holder.py` — preuve : `cfg_holder.py::doit_incrementer`, `::enregistre`, `test_cfg_holder.py` VERT
  (empreinte de `user_config_override.h` sans la ligne `#define CFG_HOLDER`, empreinte du `_persist.json` de l'env,
  dossier donné par `transform_name` ; état par env dans `%LOCALAPPDATA%\outils_tasmota\build\cfg_holder.json`, hors
  dépôt ; illisible ou absent = incrément)
- [x] Incrément seulement pour un `pio run` qui construit le firmware — preuve : `cfg_holder.py::construit_firmware`, 7 cas VERTS
  (aucune cible, `upload`, `erase_upload` ; jamais `nobuild`, `buildfs`, `uploadfs` seuls)
- [ ] Garder le FS joint à l'upload série : la post-action de `firmware.bin` (`pio-tools/post_esp32.py::esp32_create_combined_bin`)
  ne tournait QUE parce que `CFG_HOLDER` forçait l'édition des liens à chaque fois ; `env.AlwaysBuild` + `env.NoCache`
  sur `firmware.bin` dans le pré-build ; vérifié sur un journal d'upload sans changement (« Utilisera une commande de
  téléchargement personnalisée »)
- [x] Commentaires « CFG_HOLDER change à chaque run » corrigés — preuve : `build_envs.py::_fs_avec_firmware`, en-têtes de `syslog_tasmota.py` et `build_serie.py`
- [x] `increment_config_holder` inchangé (rend True), appelé seulement si `cfg_holder.doit_incrementer` — preuve : `pre_utilitaires_platformio.py` (bloc « CFG_HOLDER : seulement… »), `test_config_holder.py` VERT
  (état enregistré après l'écriture du .h ; lignes « CFG_HOLDER inchangé : … » / « CFG_HOLDER incrémenté : … »)
- [x] Banc `build/test_cfg_holder.py` — preuve : 19 cas VERTS, 6 mutants tués, contrat avec la vraie `increment_config_holder`
- [ ] Mesure réelle (build lancé par l'utilisateur) : deux compilations du même env sans modification → la seconde
  reprend `tasmota.ino.cpp` du cache ; durée relevée dans le journal

## A2 — Mesurer le coût d'un changement d'env, puis décider du dossier de build par env
- [ ] Relevé sur les journaux de la page : durée d'un build même env répété vs après changement d'env (après A1,
  pour isoler la purge) ; nombre de « Retrieved … from cache » et de « Compiling »
- [ ] Taille de `.cache` et de `.pio/build` relevée (hors build) — `.cache` : 17 391 Mo le 2026-11-01 (dont 5 383 Mo inutilisés depuis 30 j) ; `.pio/build` à relever
- [ ] Synthèse chiffrée présentée à l'utilisateur ; décision consignée ici (faire / ne pas faire). Si « faire » :
  nouveau plan (`PLATFORMIO_BUILD_DIR` par env posé par la page, ~18 fichiers dont le pré-build
  `pre_utilitaires_platformio.py` qui code `.pio/build` en dur pour `copy_fs_image`)

## A3 — Contrôle lib_ignore sauté quand le pio run ne compile pas
- [x] Vérifier si `buildfs`/`uploadfs` seuls passent par le scan des dépendances — preuve : non, la plateforme 2026.10.50
  le coupe (`builder/main.py::switch_off_ldf` : uploadfs, uploadfsota, buildfs, erase, download_fs)
- [x] Contrôle sauté si le `pio run` ne compile rien — preuve : `verifie_lib_ignore.py::compile_rien`, `::controle(env, cibles)`, 9 cas VERTS, témoin (buildfs oublié) : 3 KO
  (`nobuild`, ou seulement des cibles de `SANS_COMPILATION` ; cibles passées par le pré-build)
- [x] Ligne « lib_ignore de <env> : controle saute… » lue par la page — preuve : `build_progression._LIB_IGNORE` la capte (essai direct)
- [x] Bancs verts — preuve : `test_verifie_lib_ignore.py`, `test_build_progression.py`, `test_data_dir.py`, `test_copie_fs.py` VERTS (Python de PlatformIO)
- [ ] Vu dans le journal d'un `nobuild upload` ou d'un `buildfs` réel

## A4 — Script d'exclusions Windows Defender
- [x] Script `maintenance/exclusions_defender.ps1` — preuve : analyse PowerShell 0 erreur ; refuse hors administrateur (essai, code 1)
  (exclusions `.pio`, `.cache` du dépôt et `~/.platformio` ; `-Verifier` = lecture seule, idempotent)
- [ ] Lancé par l'utilisateur ; exclusions constatées par `-Verifier`
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
- [ ] Module `outils_pc/build_memoire.py` : table lue dans le CSV de l'env (`board_build.partitions`, sinon celui du board), `app0` = `firmware.bin`, `safeboot` = binaire de `variants/tasmota/`, FS = fichiers de l'image (`build_fichiers.py::liste`), RAM = tableau « Memory Type Usage Summary » du journal
- [ ] Mesures enregistrées dans `%LOCALAPPDATA%\outils_tasmota\build\memoire\<env>.json`, avec leur date : `.pio/build` est effacé à chaque changement d'env, et une compilation sans changement ne réaffiche plus le tableau mémoire
- [ ] Analyse automatique à la fin de chaque compilation réussie (`build_serie.py`), sans toucher aux scripts amont
- [ ] Analyse lancée seule depuis l'onglet (`POST /memoire/analyser`) : relit les fichiers existants, jamais de `pio run`, permise pendant un build
- [ ] Lecture sur la carte : `Status 4` et `UfsSize`/`UfsFree` (PSRAM, tas, FS réel), par le transport HTTP de `build_ota_http.py` ; carte muette = message, pas d'échec
- [ ] Banc `test_build_memoire.py`, fondé sur de vrais journaux P4 (DIRAM, HP core, LP) et S3 (DIRAM, IRAM, RTC) et sur un env jamais compilé

## A8 — Onglet « Mémoire et partitions », modèle B (à faire plus tard)
- [ ] Module `outils_pc/build_page_memoire.py`, inséré comme `build_page_fichiers.py`
- [ ] Liste des envs : par défaut le premier env coché sur la page d'accueil ; en choisir un autre ne change pas les cases
- [ ] Jauges par zone (capacité, occupé, libre, date de l'analyse), orange à 85 %, rouge à 95 %
- [ ] Barre de la flash et une ligne par partition : case de suppression, curseur par pas de 64 Ko, champ en Ko, occupé
- [ ] Résumé sur chaque env de la page d'accueil (app0, FS, DIRAM), avec les mêmes seuils ; un clic ouvre l'onglet
- [ ] Bouton « Analyser » et bouton « Lire sur la carte »
- [ ] Sonde Chrome `test_build_page_memoire_chrome.py`, exécutée dans un vrai navigateur ; aucune écriture dans le dépôt réel

## A9 — Écrire la table de partitions d'un env (à faire plus tard)
- [ ] Module `outils_pc/build_partitions.py` : validation (alignement et tailles de 64 Ko, `nvs` en 0x9000, `otadata` en 0xE000, `app0` obligatoire, minimum = occupé, somme = flash), mêmes règles que la maquette
- [ ] Suppression : `safeboot` et `spiffs` demandent une confirmation qui nomme la conséquence ; `nvs`, `otadata`, `app0` refusées aussi côté serveur
- [ ] Écriture d'un CSV propre à l'env dans `partitions/`, et de `board_build.partitions` dans sa section du cenv : diff d'abord, transaction et sauvegarde (`fichiers_berry_sauvegarde.Transaction`), refus pendant un build ; les autres envs ne changent pas
- [ ] OTA du firmware et du FS BLOQUÉES pour un env dont la table a changé, avec le motif affiché, jusqu'au prochain « Effacer puis téléverser » réussi (état hors dépôt, contrôle côté serveur dans `build_serie.py`)
- [ ] Avant l'écriture, rappeler que le flash série remplace le persist de la carte par celui du dépôt, et annoncer la purge de `.pio/build` (le cenv change)
- [ ] Ajout d'une partition (coredump…) : d'abord vérifier `post_esp32.py::patch_partitions_bin` (FS supposé en 5e position) et `partition_core` (FS supposé en dernier), puis autoriser ou refuser selon le résultat
- [ ] Préréglages (tables de `partitions/`), import et export d'un CSV, passés par la même validation
- [ ] Banc `test_build_partitions.py` (copies temporaires du cenv, relues par `ProjectConfig`, avec mutants) ; table produite identique octet pour octet à `esp32_partition_app3904k_fs11584k.csv` sans modification
- [ ] Essai réel par l'utilisateur sur une carte, par câble : démarrage, FS et Berry vérifiés, puis OTA de nouveau permise

## A10 — Annuaire et documentation de la fonction (à faire plus tard)
- [ ] Descriptif de la tuile « Build et téléversement » (`annuaire_registre.py`) : occupation de la mémoire et réglage des partitions par env, écrit quand la fonction existe ; `test_annuaire.py` vert
- [ ] `outils_docs/README.md` § build et `CLAUDE.md` (carte des documents, nouveaux modules)

## Améliorations restantes
- [ ] [projet] Dossier de build par env, si A2 conclut « faire »
- [ ] [projet] Sortir le port COM du cenv si les changements de port deviennent fréquents
- [ ] [projet] Défaut existant, à vérifier : un `nobuild upload` (envoi après la pause « rebranchez la carte ») n'a
  pas de règle pour `firmware.bin` (`builder/main.py`, bloc `nobuild`), donc la post-action FS de `post_esp32.py` ne tourne
  pas et le FS ne serait PAS joint, alors que la page grise « Construire / Téléverser le FS » (`build_serie.py::Serie._plan`).
  Aucun journal `nobuild` pour trancher.
- [ ] [projet] `CFG_HOLDER` est commun à tous les envs : un incrément pour un env (persist modifié) fait recompiler
  `tasmota.ino.cpp` aux autres et recharge leurs réglages SECTION1 au flash suivant. Un `CFG_HOLDER` par env
  (`-D` dans le cenv) l'éviterait.

## Vérification
- A1 : `test_cfg_holder.py` vert (mutants tués) ; deux compilations successives du même env par l'utilisateur, la
  seconde sans « Compiling …tasmota.ino.cpp.o » et nettement plus courte ; `git diff tasmota/user_config_override.h`
  vide après un build sans changement.
- A3 : journal d'un `nobuild upload` sans les 11-24 s du contrôle.
- A4/A5 : `-Verifier` et `--dry-run` en lecture seule, puis exécution par l'utilisateur.
- Aucun `pio run` lancé par Claude pendant un build de l'utilisateur.
