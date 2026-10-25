---
chantier: fichiers-berry-suppression
titre: Page « Fichiers Berry par env » — supprimer et renommer un env, écritures atomiques, sauvegardes, erreurs claires
statut: clos
cree: 2026-10-25
maj: 2026-10-25
---
# Supprimer et renommer un env depuis la page « Fichiers Berry par env »

## Contexte

**Spec :** `docs/superpowers/specs/2026-10-25-page-fichiers-berry-design.md` §9 (validée par l'utilisateur le
2026-10-25 : « Tout est correct »). Ordre voulu : suppression avec les améliorations 1 (atomicité), 2 (erreurs
claires) et 5 (sauvegardes séparées), puis 3 (recensement et création pendant un build).

**Code existant** (`outils_docs/scripts_python/outils_pc/`) : `fichiers_berry_ini.py` (lecture, `heritiers`,
`envs_touches`), `fichiers_berry_etat.py`, `fichiers_berry_ecriture.py` (`.bak` l.204), `fichiers_berry_creation.py`
(`_regions`, `_fin_utile`, `_section_h`, `.bak` l.354, `copytree` l.349), `fichiers_berry_web.py`, `fichiers_berry_page.py`.
Bancs maison (code de sortie 0 = vert) lancés par `"$USERPROFILE/.platformio/penv/Scripts/python.exe" -u <banc>`.

**Constats** (lus le 2026-10-25) :
- `platformio_override.ini` : `default_envs` cite chaque env, en ligne active ou `; commentée` ; `data_dir` désigne un
  dossier de carte.
- Aucun dossier de carte n'a de sous-dossier, ni de `.be` identique à un `data/fs/<même nom>`. Une copie identique
  est donc une copie temporaire de `copy_fs_image` (`pre_utilitaires_platformio.py:517`), qui recopie aussi `json/` et `sd/`.
- Création puis suppression doivent rendre cenv et `.h` identiques, octet pour octet : retirer la ligne vide insérée
  avant la section du cenv (`_insere_cenv`) et le `// -- Options for` de la section du `.h`.

### Contraintes globales

- Python stdlib ; fichiers < 500 lignes ; textes de la page en français ; écriture en octets (`surrogateescape`),
  fins de ligne conservées.
- Aucun banc n'écrit dans le vrai dépôt ni dans le vrai `%LOCALAPPDATA%` : `OUTILS_TASMOTA_DOSSIER` temporaire.
- Refus pendant un build, partout où l'on écrit.
- Commits en français sans accents, sans `Co-Authored-By`, rien poussé.

### Points de relecture

1. Section du `.h` en tête de chaîne (`#if`) supprimée : la suivante devient `#if`, et la chaîne compile encore.
2. Section partagée (`#if defined(A) || defined(B)`) : seul `defined(X)` part (avec son `||`), le corps reste.
3. Échec au milieu d'une suppression ou d'une création : tous les fichiers sont remis, le dossier est remis ou retiré.
4. `default_envs` : seule la ligne exacte de l'env part, active ou commentée, jamais un env dont le nom le contient.
5. Base référencée par `${env:<base>…}` sans `extends` : refus, avec la liste des envs.

## A1 — Sauvegardes horodatées et transaction (`fichiers_berry_sauvegarde.py`)

Interfaces produites : `Transaction(racine, nature)` (gestionnaire de contexte) avec `.ecrit(rel, octets)`,
`.renomme(rel_src, rel_dst)`, `.copie_dossier(rel_src, rel_dst, ignore=None)`, `.dossier` (sauvegarde) ; à la sortie
sur exception, annulation en ordre inverse puis l'exception repart. `dossier_sauvegardes()` =
`acces_web.dossier_donnees()/fichiers_berry/sauvegardes` ; `purge(jours=30)`.

- [x] Banc `test_fichiers_berry_sauvegarde.py` ROUGE puis VERT : copie horodatée avant écriture (contenu d'origine),
  annulation sur exception (fichier remis, dossier copié retiré, renommage défait), purge > 30 jours, rien hors
  `OUTILS_TASMOTA_DOSSIER`. — preuve : ROUGE (module absent, 4 KO) puis VERT
- [x] `fichiers_berry_ecriture.enregistre` et `fichiers_berry_creation.cree` passent par `Transaction` (plus de `.bak`) ;
  résultat `sauvegarde` = chemin du dossier ; bancs écriture/création adaptés (le `.bak` attendu devient la sauvegarde). — preuve : test_sauvegarde_et_diff et test_sauvegarde ROUGE (KeyError) puis VERT ; bancs isolés par OUTILS_TASMOTA_DOSSIER ; sonde « chemin de la sauvegarde affiché » VERT, témoin détecté
- [x] Création atomique : test `test_creation_atomique` (écriture du cenv qui échoue → `.h` remis, dossier retiré) ROUGE puis VERT. — preuve : 4 KO puis VERT
- [x] Commit `feat(fichiers-berry): sauvegardes horodatees et ecritures atomiques`. — preuve : 40e1e96a2

## A2 — Erreurs claires (`fichiers_berry_web.py`)

- [x] `test_fichiers_berry_web.py` : une exception inattendue (`OSError` levée par `builds_en_cours`) → 500 avec le
  message, connexion non coupée ; ROUGE puis VERT (`except Exception` en dernier dans `do_GET` et `do_POST`). — preuve : test_erreur_inattendue ROUGE (RemoteDisconnected, GET et POST) puis VERT
- [x] Commit `fix(fichiers-berry): reponse 500 avec le message sur erreur inattendue`. — preuve : 748e2f994

## A3 — Suppression d'un env (`fichiers_berry_suppression.py`)

Interfaces produites : `prepare_suppression(racine, env) -> {env, dossier, dossier_sauvegarde, diff, empreinte,
avertissements, refus}` ; `supprime(racine, env, empreinte, builds_en_cours) -> {supprime, env, dossier_sauvegarde,
sauvegarde, avertissements}` ; RuntimeError (→ 409) si build, empreinte périmée, refus.

- [x] Banc `test_fichiers_berry_suppression.py` (copie du vrai dépôt, comme `test_fichiers_berry_creation.py`) ROUGE puis VERT : — preuve : ROUGE (module absent), puis VERT 34 contrôles
  - [x] création puis suppression → cenv et `.h` identiques octet pour octet, dossier renommé `…-sauvegarde` ;
  - [x] section `#if` de tête (cave) supprimée → la suivante devient `#if` ; section partagée → seul `defined(X)` part ;
  - [x] `default_envs` : ligne active et ligne commentée retirées, aucune autre ; `data_dir` sur le dossier → avertissement ;
  - [x] `…-sauvegarde` déjà pris → `…-sauvegarde-2` ;
  - [x] refus : base héritée ou référencée (envs nommés), env inconnu, build en cours, empreinte périmée ;
  - [x] atomicité : échec à la 2e écriture → tout remis ;
  - [x] citations ailleurs (commentaires du cenv, autres fichiers `.ini`/`.py` connus) signalées, non modifiées.
- [x] Commit `feat(fichiers-berry): suppression d un env (cenv, .h, default_envs, dossier en -sauvegarde)`. — preuve : 849d21147

## A3b — Renommage d'un env (`fichiers_berry_renommage.py`, spec §10)

Interfaces produites : `Renommage(env, lieu, nom, identite, define="")` ; `prepare_renommage(racine, r)` ->
`{env, nouvel_env, dossier, nouveau_dossier, define, diff, empreinte, avertissements, refus}` ; `renomme(racine, r,
empreinte, builds_en_cours)`. Réutilise la copie de section et l'identité de `fichiers_berry_creation` et le retrait
de `fichiers_berry_suppression`.

- [x] Banc `test_fichiers_berry_renommage.py` ROUGE puis VERT : — preuve : ROUGE (module absent) puis VERT 26 contrôles
  - [x] rideau renommé : nouvel env lu par PlatformIO (`build_envs.liste_envs`), ancien absent, dossier déplacé (ancien
    absent, pas de `-sauvegarde`), persist aux nouvelles valeurs seules (octet pour octet ailleurs) ;
  - [x] même IP gardée : accepté (l'identité actuelle de l'env ne compte pas) ; topic d'une AUTRE carte : refusé ;
  - [x] `default_envs` : ligne active reste active, commentée reste commentée, au nouveau nom ; `data_dir` suit ;
  - [x] renommer puis renommer en sens inverse : cenv, `.h` et dossier comme au départ, hors identité modifiée ; (cenv, override et persist identiques ; le `.h` diffère par NAME/Hostname dérivés de l'identité)
  - [x] refus : env référencé, nouveau nom déjà pris, build ; atomicité (panne → tout remis).
- [x] Commit `feat(fichiers-berry): renommage d un env (identite reproposee, dossier deplace)`.

## A4 — Routes et page de la suppression et du renommage

- [x] `POST /suppression/prepare {env}`, `POST /suppression {env, empreinte}`, `POST /renommage/prepare {env, lieu, nom,
  identite, define?}`, `POST /renommage {..., empreinte}` ; test web ROUGE puis VERT. — preuve : test_post_renommage_puis_suppression ROUGE (400, routes absentes) puis VERT ; GET /identite?env= ajouté
- [x] Page : bouton « Supprimer cet env… » (cartes et bases du cenv), panneau avec diff, avertissements, refus, dossier
  renommé, bouton « Supprimer <env> » grisé si refus ou si l'env choisi change ; après succès, liste des envs
  rechargée et chemin de la sauvegarde affiché. — preuve : panneaux dans fichiers_berry_page_envs.py (page 451 lignes, sous 500)
- [x] Page : bouton « Renommer cet env… » : lieu, nom, « Proposer » (identité), diff, « Renommer » (grisé si la saisie
  change après le diff) ; après succès, l'env renommé est choisi. — preuve : idem
- [x] Sonde Chrome : créer, renommer puis supprimer un env d'essai ; refus sur une base ; ROUGE puis VERT, témoin VERT. — preuve : 11 KO puis VERT, témoin détecté
- [x] Commit `feat(fichiers-berry): boutons Supprimer et Renommer cet env dans la page`. — preuve : 30d72376e

## A5 — Recensement et création pendant un build (amélioration 3)

- [x] `etat_env` : un `.be` du dossier de la carte identique à `data/fs/<même nom>` est une copie temporaire, ni
  proposé ni « homonyme » ; `GET /etat` porte `build_en_cours` et la page l'affiche en bandeau. Création :
  `copie_dossier` ignore ces copies et les sous-dossiers `fs`, `json`, `sd`. Tests ROUGE puis VERT (état, création). — preuve : test_fichiers_berry_etat (test_copie_temporaire),
  _creation (test_copies_temporaires_ignorees), _web (build_en_cours) rouges puis VERT ; 8 bancs + sonde Chrome VERT.
- [x] Commit `fix(fichiers-berry): copies temporaires d un build ignorees (recensement, creation)`.

## A6 — Documentation et essai réel

- [x] README § « Fichiers Berry par env » (suppression, sauvegardes), `CLAUDE.md` (carte des documents), skill `bancs`. — preuve : outils_docs/README.md § Renommer / Supprimer / Sauvegardes, CLAUDE.md (carte), .claude/skills/bancs/SKILL.md:58
- [x] Essai réel avec l'utilisateur, hors build : créer un env d'essai, le renommer, puis le supprimer depuis la page ; `git status`
  sans cenv ni `.h`, dossier `…-sauvegarde` présent puis retiré à la main.
- [x] Commit `docs: suppression et renommage d un env (README, CLAUDE.md, bancs)` ; `statut: clos`.

## A7 — Règle d'identité assouplie et mineurs de la revue (demande du 2026-10-25)

- [x] Identité déjà portée par une autre carte (IP, topic, client MQTT) : **avertissement** au lieu d'un refus, à la
  création comme au renommage (carte remplacée). Env, dossier, define déjà pris : toujours refusés. — preuve : test_fichiers_berry_creation (topic du rideau), _renommage (test_unicite, P4 renommable) ROUGE puis VERT ; vrai dépôt : P4 renommable, 3 avertissements
- [x] M8 : identité refusée avec `;` (tout champ), espace dans `PROJECT`, `MQTT_CLIENT_ID`, `MQTT_TOPIC`, `MQTT_GRPTOPIC`,
  `WIFI_IP_ADDRESS`, `+`/`#` dans les champs MQTT. M4 : define cherché hors commentaires (cenv `;`, `.h` `//`). — preuve : test_identite_invalide, test_define_en_commentaire ROUGE puis VERT
- [x] M2/M3 : `.h` : tout le bloc `// -- Options for …` + commentaires contigus suit sa section (suppression, renommage ;
  commentaire sans le nom de l'env signalé au renommage). cenv : bandeau `; LOCALISATION:` devenu vide retiré ; pas
  d'avertissement pour un commentaire au-dessus qui n'est que le bandeau. — preuve : test_section_partagee_puis_tete (commentaires des caves), test_nouveau_lieu_aller_retour, test_commentaire_h, test_autre_lieu ROUGE puis VERT ; vrai dépôt : plus d'avertissement pour les 3 cartes du garage
- [x] M10 : `default_envs` lu dans son seul bloc ; avertissement s'il ne reste aucun env actif. M7 : empreinte du
  renommage avec `_persist.json`, de la suppression avec le nom `-sauvegarde`. M5 : `KeyError`/`IndexError` → 500. — preuve : test_default_envs_vide, test_sauvegarde_apparue, test_persist_change, test_erreur_inattendue (KeyError) ROUGE puis VERT
- [x] M1/M9 : dossier parent créé retiré si le renommage échoue (et après `copie_dossier`) ; fichier écrit par
  remplacement atomique ; marque `en_cours.json` dans la sauvegarde, retirée à la fin : une opération interrompue
  (processus arrêté) est signalée par la page au chargement, acquittable. — preuve : test_parents_retires, test_interrompue, test_interrompues (web), sonde Chrome (bandeau, « J'ai vérifié ») ROUGE puis VERT
- [x] Bancs ROUGE puis VERT, suite complète + sonde Chrome VERTES ; README, spec §9-§10 mis à jour ; commit. — preuve : 11 bancs + sonde Chrome VERTS (2 passes) ; README § Créer/Renommer/Supprimer/Sauvegardes, spec §9 §10

## Améliorations restantes

- [x] [projet] Renommer un env : rétabli dans le périmètre par l'utilisateur le 2026-10-25 (action A3b). — preuve : spec §10
- [x] [conversation] Revue finale (opus) : I1 écritures concurrentes (verrou des POST, boutons grisés avant l'envoi), I2
  annulation incomplète signalée (`AnnulationIncomplete`), M6 `GET /etat` sans attendre la détection (`GET /build`). — preuve : 20588aef8
- [x] [projet] Mineurs de la revue, traités en A7 (demande du 2026-10-25) : M1 dossier `data/<lieu>` vide laissé si un renommage vers un
  nouveau lieu échoue ; M2 commentaires `// -- Options for …` d'une section partagée et bandeau `; LOCALISATION:` vide laissés ;
  M3 avertissement « commentaire au-dessus » déclenché par le bandeau du lieu ; M4 define cherché aussi dans les commentaires
  du cenv (refus au renommage retour de la cave) ; M5 `KeyError` → 404 au lieu de 500 ; M7 empreinte du renommage sans
  `_persist.json`, nom `-sauvegarde` recalculé à l'écriture ; M8 `;` accepté dans l'identité (commande en plus dans
  `USER_BACKLOG`) ; M9 atomicité face aux exceptions, pas à un arrêt du processus ; M10 `default_envs` peut devenir vide.
- [x] [projet] Question de la revue : une carte remplacée (P4 après l'ancien maître S3, caves) ne peut pas garder son
  identité au renommage, l'ancienne carte la porte encore dans le `.h`. Garder la règle ou l'assouplir ? — réponse :
  assouplie (avertissement), action A7

## Vérification

Tous les bancs `test_fichiers_berry_*.py`, `build/test_cible_fichiers_berry.py`, `test_annuaire.py`,
`build/test_garde_build.py` VERTS ; sonde Chrome VERTE avec témoin détecté ; essai réel fait avec l'utilisateur.
