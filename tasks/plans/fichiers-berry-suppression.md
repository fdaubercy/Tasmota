---
chantier: fichiers-berry-suppression
titre: Page « Fichiers Berry par env » — supprimer et renommer un env, écritures atomiques, sauvegardes, erreurs claires
statut: actif
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
- [ ] Commit `feat(fichiers-berry): boutons Supprimer et Renommer cet env dans la page`.

## A5 — Recensement et création pendant un build (amélioration 3)

- [ ] `etat_env` : un `.be` du dossier de la carte identique à `data/fs/<même nom>` est une copie temporaire, ni
  proposé ni « homonyme » ; `GET /etat` porte `build_en_cours` et la page l'affiche en bandeau. Création :
  `copie_dossier` ignore ces copies et les sous-dossiers `fs`, `json`, `sd`. Tests ROUGE puis VERT (état, création).
- [ ] Commit `fix(fichiers-berry): copies temporaires d un build ignorees (recensement, creation)`.

## A6 — Documentation et essai réel

- [ ] README § « Fichiers Berry par env » (suppression, sauvegardes), `CLAUDE.md` (carte des documents), skill `bancs`.
- [ ] Essai réel avec l'utilisateur, hors build : créer un env d'essai, le renommer, puis le supprimer depuis la page ; `git status`
  sans cenv ni `.h`, dossier `…-sauvegarde` présent puis retiré à la main.
- [ ] Commit `docs: suppression et renommage d un env (README, CLAUDE.md, bancs)` ; `statut: clos`.

## Améliorations restantes

- [x] [projet] Renommer un env : rétabli dans le périmètre par l'utilisateur le 2026-10-25 (action A3b). — preuve : spec §10

## Vérification

Tous les bancs `test_fichiers_berry_*.py`, `build/test_cible_fichiers_berry.py`, `test_annuaire.py`,
`build/test_garde_build.py` VERTS ; sonde Chrome VERTE avec témoin détecté ; essai réel fait avec l'utilisateur.
