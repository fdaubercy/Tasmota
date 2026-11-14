---
chantier: default-envs-page
titre: Modifier default_envs depuis la page Build
statut: clos
cree: 2026-11-01
maj: 2026-11-01
source: cuddly-rolling-sprout.md
objectif: Choisir sur la page Build les envs compilés par un simple pio run, sans ouvrir platformio_override.ini
famille: build
---
# Modifier `default_envs` depuis la page Build

## Contexte
Le bloc `default_envs` de `platformio_override.ini` fixe ce que compile un `pio run` sans `-e`. Aujourd'hui, on
(dé)commente les lignes à la main. Il doit devenir modifiable sur une page web.

**Décisions de l'utilisateur**
- Après enregistrement : un bouton reporte la liste dans l'onglet Build ; on lance ensuite par le bouton Lancer habituel.
- Envs de Mes cartes / Mes bases absents du bloc : proposés ; ajoutés au groupe de leur puce **seulement s'ils sont cochés**.
- **Le modèle d'onglet est choisi sur images avant tout code** (message du 2026-11-01).

**Mes choix (à corriger au besoin)**
- Outil : page Build (:7700), nouvel onglet. C'est là qu'on décide quoi compiler, et le schéma d'onglet à fichiers
  séparés existe déjà (`build_page_fichiers.py`, `build_page_memoire.py`).
- Le report **remplace** la sélection de l'onglet Build, sans toucher aux actions cochées.
- **Liste vide refusée** : sans env actif, `pio run` construirait tous les envs (`run/cli.py`).
- **Écriture refusée (409)** pendant un lancement ou un build : le pre-script réécrit ce fichier.
- Enregistrement en deux temps : diff, puis écriture contrôlée par empreinte, comme les partitions. Pas de commit par la page.
- **Pas de réordonnancement** : `pio run` suit l'ordre des sections du `.ini`, pas celui du bloc (`run/cli.py`).
- Seul l'état commenté ou actif de la ligne change ; commentaires de groupe, indentation et fins de ligne sont gardés.

**Constats vérifiés**
- Modifier le bloc change l'empreinte du projet (`project/helpers.py::compute_project_checksum` hache toute la config) :
  le `pio run` suivant vide `.pio/build`, amorti par `.cache`. L'onglet l'annonce avant d'enregistrer.
- Absents du bloc aujourd'hui : `tasmota32s3-base-N16R8-sans-ecran`, `tasmota32p4r3-base-devkit`.

## A1 — Maquettes d'onglet, choix de l'utilisateur
Images dans `outils_docs/default_envs/` : `modele-A.png` à `modele-D.png`, code `maquettes_default_envs.html`, `README.md`.
Rendues au vrai style de la page Build, avec les vrais envs. Modèles proposés :
A cases par groupe de puce (reprend le fichier) · B colonnes par puce · C deux listes « Compilés / Non compilés » ·
D lignes du bloc à gauche, diff en direct à droite.
- [x] Quatre PNG produits par Chrome sans fenêtre, relus par moi — preuve : outils_docs/default_envs/modele-A.png à modele-D.png, relus ; défauts de C et D corrigés puis recapturés
- [x] Modèle choisi par l'utilisateur et noté dans ce plan (aucun code avant) — preuve : message du 2026-11-01, **modèle B + « Modifications en attente » dessous** = futur `platformio_override.ini` entier, lignes changées surlignées, recalculé à chaque case ; le bouton devient « Enregistrer »

## A2 — Lecture et écriture du bloc : `outils_pc/build_defaut.py`
Réutilise `fichiers_berry_suppression.py::bloc_default_envs`, `_actifs`, `ligne_default_envs`,
`build_envs.py::liste_envs`, `fichiers_berry_sauvegarde.Transaction`.
- [x] `lit` : groupes du bloc, état de chaque ligne, envs absents proposés, ligne citant un env inconnu signalée — preuve : test_build_defaut.py VERT
- [x] `prepare` : aperçu du futur fichier, empreinte, erreurs (liste vide, env inconnu coché), avertissement de purge ; rien n'est écrit — preuve : test_build_defaut.py VERT
- [x] `ecrit` : refus pendant un build ou si le fichier a changé, écriture atomique, copie de sauvegarde — preuve : test_build_defaut.py VERT, 10 mutants tués
- [x] Banc `test_build_defaut.py` sur copie temporaire : relecture par `ProjectConfig.default_envs()`, seules les lignes
      visées changent, le bloc survit au pre-script (`data_dir` réécrit), témoins qui doivent échouer — preuve : VERT sur copie des vrais .ini (`os.chdir` : extra_configs se résout depuis le dossier courant)

## A3 — Routes de `build_web.py`
- [x] `GET /defaut`, `POST /defaut/diff`, `POST /defaut/ecrire` (409 pendant un lancement ou un build), docstring à jour — preuve : build_web.py, test_build_web.py::test_defaut VERT
- [x] Banc `test_build_web.py` complété, dont le refus pendant un build — preuve : test_defaut (build, détection impossible, lancement, témoin 200), VERT

## A4 — Onglet selon le modèle choisi : `outils_pc/build_page_defaut.py`
- [x] CSS/HTML/JS de l'onglet, branchés dans `build_page.py` comme `build_page_memoire.py` — preuve : test_build_page_defaut_chrome.py VERT, capture relue sur copie des vrais .ini
- [x] Futur fichier surligné et annonce de la purge avant « Enregistrer » — preuve : sonde « case B », « purge annoncee »
- [x] Bouton « Cocher ces envs dans l'onglet Build » : remplace la sélection, y compris pour un env de famille repliée (safeboot) — preuve : sonde « report », VERT
- [x] Sonde Chrome `test_build_page_defaut_chrome.py` : onglet exécuté, aucune erreur JS, report vérifié, aucun envoi ni build — preuve : VERT ; sondes Build, Fichiers et Mémoire VERT aussi

## A5 — Documentation et livraison
- [x] `outils_docs/README.md` (mode d'emploi), `CLAUDE.md` (carte des documents, compte de lignes de `build_page.py`) — preuve : sections écrites, verifie_references_docs.py 0 défaut
- [x] `verifie_references_docs.py` vert, tous les bancs `test_build_*` verts — preuve : 0 défaut ; envs, fichiers, memoire, ota_fs, ota_mqtt, progression, serie, solidification, defaut, web, partitions et sondes page/fichiers/mémoire/defaut VERT le 2026-11-01
- [x] Essai réel par l'utilisateur sur la page, puis commit (`git commit -- <chemins>`) — preuve : essai des 5 étapes sur :7700 validé par l'utilisateur le 2026-11-01 (« oui ca fonctionne ») ; case de création vérifiée sur copies seulement

## A6 — Case « Ajouter à default_envs » à la création d'un env
Demande du 2026-11-01 : décochée par défaut, sur la page Fichiers Berry par env et sur l'Assistant persist.
- [x] `build_defaut.avec_env_cree`, `fichiers_berry_creation.ajoute_default_envs`, écriture dans la Transaction de création — preuve : test_fichiers_berry_creation.py::test_default_envs, test_assistant_persist_creation.py::test_default_envs VERT
- [x] Case dans les deux pages, envoyée au serveur — preuve : sondes test_fichiers_berry_page_chrome.py et test_assistant_persist_page_chrome.py, ligne « case default_envs visible » OK

## Améliorations restantes
- [x] [projet] Sonde `test_assistant_persist_page_chrome.py` rouge sur le bandeau du modèle : elle attend 1 clé à compléter, le parc réel en donne 5 (TCA9554 du persist de la cave, absentes de `modele_persist.json`) ; sans lien avec ce plan — preuve : bloc TCA9554 (OFF) au socle du modèle (arrivé dans le commit 88444d66b), sonde, `test_assistant_persist_modele.py` et `test_assistant_persist_fidelite.py` VERT le 2026-11-01 ; écarts TCA9554 tolérés dans `test_assistant_persist_generation.py`

## Vérification
1. `test_build_defaut.py` : la liste relue par `ProjectConfig` est exactement celle cochée, et le diff ne touche que les lignes visées.
2. Sonde Chrome de l'onglet sur la vraie page.
3. Essai réel, hors build : décocher et cocher un env, relire le diff, enregistrer, contrôler `git diff platformio_override.ini`,
   reporter dans l'onglet Build. Aucune compilation n'est lancée pour cet essai.
