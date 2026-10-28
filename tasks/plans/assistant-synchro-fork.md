---
chantier: assistant-synchro-fork
titre: Assistant pas à pas de la page « Synchro du fork » (port 7500)
statut: actif
cree: 2026-10-27
maj: 2026-10-28
---
# Assistant pas à pas de la synchro du fork — plan d'implémentation

> **Pour l'exécutant :** sous-skill requise : superpowers:subagent-driven-development (recommandée) ou
> superpowers:executing-plans. Cocher une étape seulement après vérification, avec « — preuve : … ».

## Contexte

**But :** après un dry-run sur la page http://127.0.0.1:7500, une liste verticale d'étapes, propre au cas constaté,
mène jusqu'au fork synchronisé. En cas de conflit, elle reste en **merge** et propose une résolution fichier par fichier.

**Spec (validée le 2026-10-27) :** `docs/superpowers/specs/2026-10-27-assistant-synchro-fork-design.md`.
- La lire en entier avant toute action.
- « §x » renvoie à ses sections.

**Architecture :**
- Deux modules purs, testés sur un **faux dépôt** sans réseau :
  - `synchro_fork_assistant.py` : analyse et liste d'étapes, en lecture seule (hormis le fetch) ;
  - `synchro_fork_fusion.py` : actions de la voie B et push.
- Les routes s'ajoutent à `synchro_fork_web.py`.
- Le bloc de page vit dans `synchro_fork_page_assistant.py`, concaténé à `PAGE`.
- Le script de merge (`synchronise_fork_tasmota.py`) garde son déroulé au terminal. La voie A le lance tel quel.

**Bancs :**
- Même modèle que `test_synchro_fork_web.py` : liste `ECHECS`, `verifie(obtenu, attendu, libelle)`, `principal()`, code de sortie 0 = vert.
- Lancés depuis la racine : `python -u outils_docs/scripts_python/maintenance/test_<x>.py`.

### Contraintes globales (valent pour toutes les actions)

- **Dossier :** tout le code est dans `outils_docs/scripts_python/maintenance/`. Seul import hors de ce dossier : `outils_pc/` par le `sys.path` explicite déjà posé dans `synchro_fork_web.py`.
- **Commandes git interdites à l'assistant :**
  - `push --force` (ni `-f`, ni `--force-with-lease`) ;
  - `stash` et `reset` ;
  - `rebase` ;
  - un `switch` ou `checkout` de branche vers autre chose que `development` ;
  - un commit d'un fichier qui n'appartient ni au merge en cours ni au journal.
- **Aucun kill d'un processus git.** Un délai dépassé est signalé (§7).
- **Variables d'environnement des actions git :** `GIT_EDITOR=true` et `GIT_TERMINAL_PROMPT=0`. Toujours `git -c core.quotePath=false`.
- **POST :**
  - en-tête `X-Synchro: 1` et `acces.origine_autorisee`, comme les POST existants ;
  - codes d'erreur : `LookupError`→404, `ValueError`/`TypeError`→400, `RuntimeError`→409 ;
  - une seule action d'assistant à la fois (verrou) ;
  - refus si `session.en_cours()`.
- **Build en cours** (`build_serie.builds_en_cours_defaut()`, injectable) : liste non vide **ou `None`** → refus de toute action qui modifie l'arbre. Message pour `None` : « impossible de vérifier qu'aucun build ne tourne ».
- **Bancs :** jamais le vrai dépôt (faux dépôt dans `tempfile.TemporaryDirectory()`), jamais le réseau, jamais `pio run`.
- **Pas de dialogue navigateur** (`alert`, `confirm`) : une confirmation = un second bouton « Confirmer ».
- **Langue :**
  - textes de la page en français avec accents ;
  - code et commentaires dans le style des fichiers voisins (sans accents) ;
  - commits en français sans accents, sans `Co-Authored-By`, par `git commit -- <chemins>` puis `git show --stat HEAD` ; une autre session peut travailler sur le dépôt.
- **Taille :** fichiers < 500 lignes. `synchronise_fork_tasmota.py` est une exception déjà admise : y ajouter le minimum et mettre à jour son compte dans `CLAUDE.md`.

### Points de vigilance (non couverts par la spec, chacun a son test dans l'action qui le possède)

1. **Fetch impossible** (hors ligne, remote cassé) : l'analyse renvoie `erreur`, sans étape modifiante → test A1.
2. **Chemin avec espace ou accent** dans un conflit (`dossier é/fichier x.txt`) : toutes les actions fonctionnent → test A2.
3. **Push refusé** parce qu'origin a avancé entre-temps : erreur git affichée, aucun forçage → test A2.
4. **Double clic** sur une action : la seconde requête reçoit un 409 → test A3.
5. **Serveur arrêté en plein merge**, page rouverte : l'assistant s'affiche au chargement et reprend à la résolution → tests A2 (analyse) et A4 (sonde).

## A1 — Faux dépôt et analyse (lecture seule)

Fichiers :
- créer `faux_depot_synchro.py` (outil de banc), `synchro_fork_assistant.py` et `test_synchro_fork_assistant.py` ;
- modifier `synchro_fork_etat.py` (`racine` en paramètre).

Interfaces produites :
- `faux_depot_synchro.cree(dossier: Path) -> Path`.
  - Crée `amont.git` et `origin.git` (dépôts nus, branche `development`, un commit commun avec `commun.txt`, `a.txt`, `dossier é/fichier x.txt`), puis le clone de travail `travail/` (remotes `upstream` et `origin`, branche `development`, `user.name`/`user.email` locaux).
  - Rend le chemin de `travail/`.
- `faux_depot_synchro.commit_amont(dossier, fichiers: dict[str, str|None], message) -> str` : commit dans l'amont par un clone jetable (`None` = suppression). Rend le sha.
- `faux_depot_synchro.commit_local(travail, fichiers, message) -> str` : la même chose dans `travail/`.
- `synchro_fork_etat.fichiers_modifies(racine=REPO)` et `_git(*args, racine=REPO)` : comportement inchangé par défaut.
- `synchro_fork_assistant.FICHIERS_BUILD = ("platformio_override.ini", "tasmota/user_config_override.h", "lib/libesp32/berry_custom/src/modules.h", "tasmota/tasmota_defines_for_berry.be", "tasmota/tasmota_defines_for_berry.h")`.
- `commits_locaux(racine) -> list[tuple[str, str, list[str]]]` : `git log --format=%H%x09%s HEAD..upstream/development`. Elle rend `(sha[:9], titre, mots)` avec les mots de `sft.MOTS_SAILLANTS`, dans l'ordre d'arrivée (le plus ancien d'abord, comme l'API).
- `prevision(racine) -> {"possible": bool, "conflits": list[str]}` (`merge-tree` du §5.1-4 ; « possible » est faux si git est trop ancien ou si la commande échoue).
- `analyse(racine, fetch=True) -> dict`, avec les clés `branche`, `operation` (`""|"merge"|"rebase"`), `merge_assistant` (bool, fourni par A2 : vaut `False` tant qu'A2 n'existe pas), `retard`, `non_pousses`, `retard_origin` (`HEAD..origin/development` ; s'il est > 0, `fusion_b` affiche d'abord le bouton `ff-origin`), `commits` (`[{sha, titre, saillant}]`), `touches_amont`, `touches_deux`, `prevision`, `fichiers` (`[{etat, chemin, classe: "amont"|"libre", build: bool}]`, sans le journal), `non_suivis`, `journal_modifie`, `voie` (`"A"|"B"|""`), `etapes`, `erreur`.
- `etapes(a: dict) -> list[dict]` (fonction pure).
  - Chaque étape est un dict `{id, titre, statut, detail}`.
  - `id` ∈ `operation`, `branche`, `arbre`, `nouveautes`, `deux_cotes`, `prevision`, `synchro_a`, `fusion_b`, `pousser`, `journal`.
  - `statut` ∈ `faite`, `courante`, `bloquee`, `attente`. Une étape sans objet est absente de la liste.
  - Une seule étape est `courante`, la première non faite et non informative ; `nouveautes` et `deux_cotes` ne bloquent jamais.
  - Règle de voie (§4) : B si `prevision.conflits` est non vide, ou si `non_pousses > 0` et `retard > 0`. Sinon A si `retard > 0`, sinon `""`.
- `trois_voies(racine, chemin, autorises: list[str]) -> {"mien": str, "amont": str}`.
  - `ValueError` si `chemin` n'est pas dans `autorises`.
  - Contenu : diffs `base→HEAD` et `base→upstream/development`, tronqués à `synchro_fork_etat.MAX_DIFF`.

Étapes :
- [x] Banc rouge d'abord (module absent), un test par cas, sur `faux_depot_synchro`. — preuve : test_synchro_fork_assistant.py, 18 cas (3001502fc, 9b644313b)
  - `a_jour` : `voie == ""`, `etapes == []`.
  - `avance_seule` : un commit local poussé, `retard == 0` → `etapes == []`.
  - `non_pousses_seuls` : `[e["id"] for e in etapes] == ["pousser"]`.
  - `retard_sans_recouvrement` : amont modifie `a.txt` → `voie == "A"`, `touches_deux == []`, `prevision == {"possible": True, "conflits": []}`.
  - `deux_cotes_sans_conflit` : amont modifie la ligne 1 de `commun.txt`, local la ligne 5 → `touches_deux == ["commun.txt"]`, `conflits == []`, `voie == "A"`.
  - `conflit` : même ligne des deux côtés → `conflits == ["commun.txt"]`, `voie == "B"`.
  - `non_pousses_force_b` : commit local non poussé sans conflit + retard → `voie == "B"`.
  - `arbre_sale` :
    - `a.txt` est touché par l'amont et modifié sans commit → classe `amont` ;
    - `tasmota/user_config_override.h` modifié → `build is True` ;
    - l'étape `arbre` est `courante`, `synchro_a` est `attente`.
  - `autre_branche` : HEAD sur `essai` → étape `branche` présente.
  - `fetch_impossible` (vigilance 1) : URL d'`upstream` cassée → `erreur != ""` ; aucune étape `synchro_a`, `fusion_b` ni `pousser`.
  - `commits_adaptateur` : le titre `"Berry: fix"` donne un tuple avec `"berry"` dans les mots.
  - `trois_voies_hors_liste` : `ValueError`.
  - `courante_unique` : dans chaque cas, au plus une étape a le statut `courante`.
- [x] Lancer : ROUGE (ImportError). — preuve : ModuleNotFoundError (task-1-report.md)
- [x] Ajouter `racine` à `synchro_fork_etat`, puis écrire `faux_depot_synchro.py` et `synchro_fork_assistant.py`. — preuve : 3001502fc
- [x] Banc VERT, et `test_synchro_fork_web.py` toujours vert. — preuve : 72 OK 0 KO code 0, web vert ; relecture approuvee + correctif statuts bloques re-relu (9b644313b)
- [x] Témoin : une copie de l'analyse (dans le scratchpad) qui ignore `non_pousses` dans la règle de voie fait passer `non_pousses_force_b` au ROUGE. — preuve : temoin 2 KO, code 1 (task-1-report.md)
- [x] Commit `feat(synchro-fork): analyse de l assistant pas a pas`. — preuve : 3001502fc + fix 9b644313b

## A2 — Voie B : merge local guidé et push

Fichiers :
- créer `synchro_fork_fusion.py` ;
- étendre `test_synchro_fork_assistant.py` (groupe `fusion`) ;
- modifier `synchronise_fork_tasmota.py` : paramètre `historique` de `noter_historique`.

Interfaces consommées : `faux_depot_synchro`, `synchro_fork_assistant.analyse`, `commits_locaux`.

Interfaces produites :
- `MARQUE = "synchro-fork-assistant"` : fichier `.git/<MARQUE>` contenant le sha d'`upstream/development` fusionné. Il est écrit au lancement du merge et supprimé par `termine` et `abandonne`.
- `merge_assistant_en_cours(racine) -> bool` : `MERGE_HEAD` existe et son contenu égale le sha de la marque. Branché dans `analyse()["merge_assistant"]`, l'étape `fusion_b` reprend alors à la résolution.
- `conflits(racine) -> list[{"chemin", "type", "binaire"}]`.
  - `type` est le code à deux lettres de `git status --porcelain` (`UU`, `DU`, `UD`, `AA`…), seulement pour les entrées non fusionnées.
  - `binaire` est lu dans `git diff --numstat` (`-` comme compteur).
- Actions. Chacune prend `(racine, ..., builds_en_cours)`, rend un texte de résultat et lève `RuntimeError` en cas de refus. Le build est vérifié en premier.
  - `bascule(racine, builds)` : `git switch development`, si l'arbre est propre.
  - `ff_origin(racine, builds)` : `git merge --ff-only origin/development`.
  - `lance_merge(racine, builds)` :
    - préalables du §6 vérifiés ;
    - `git merge --no-ff --no-commit upstream/development` ; un code 1 avec des conflits n'est **pas** une erreur ;
    - écrit la marque.
  - `resout(racine, chemin, choix, builds)` :
    - `choix` ∈ `mien`, `amont` (`checkout --ours|--theirs` puis `add`), `garder` (`add`), `supprimer` (`rm`), `resolu` (`add`) ;
    - `resolu` est refusé s'il reste une ligne commençant par `<<<<<<<`, `=======` ou `>>>>>>>` ;
    - `mien` et `amont` sont refusés pour `DU`/`UD` ; `garder` et `supprimer` ne sont acceptés que pour `DU`/`UD`/`AU`/`UA` ;
    - `chemin` doit être dans `conflits()`, sinon `ValueError` ;
    - **revérification à chaque appel** : sinon `RuntimeError("merge etranger")`.
  - `ouvre(racine, chemin) -> str` : `code -r <absolu>` (`shutil.which("code")`, sinon `RuntimeError` avec le chemin).
  - `termine(racine, builds, historique=None)` :
    - refusé si `conflits()` n'est pas vide ;
    - `git commit --no-edit` ;
    - puis `sft.noter_historique(commits_locaux_avant_merge, origin, upstream, "development", "merge local (conflits resolus)", historique=historique or racine / sft.HISTORIQUE_REL)` ; les commits sont lus et gardés au lancement du merge, dans la marque en JSON.
  - `abandonne(racine, builds)` : `git merge --abort` pour **tout** merge en cours, qu'il vienne de l'assistant ou non. L'étape `operation` le propose pour un merge étranger (§4), mais jamais pour un rebase (`RuntimeError`). La marque est supprimée.
  - `pousse(racine) -> str` : `git push origin development`, sortie de git rendue, `RuntimeError` si le code ≠ 0.

Étapes :
- [x] Banc rouge, groupe `fusion`. — preuve : test_synchro_fork_fusion.py, 121 OK code 0 (9318a0193, f9fdb16ae)
  - `merge_propre` : voie B sans conflit → `lance_merge`, `conflits == []`, `termine` → `git log -1 --format=%P` montre 2 parents ; le journal du faux dépôt contient le titre du commit amont.
  - `mien` / `amont` : le contenu de `commun.txt` est celui du côté choisi, `conflits == []`.
  - `resolu_avec_marqueurs` : `RuntimeError` ; après réécriture propre du fichier, accepté.
  - `modifie_ici_supprime_amont` : `type == "UD"`. `mien` → `RuntimeError`, `supprimer` → le fichier est absent après `termine`.
  - `chemin_accentue` (vigilance 2) : un conflit sur `dossier é/fichier x.txt`, résolu par `amont`.
  - `merge_etranger` : un `git merge` lancé à la main → `resout` → `RuntimeError` ; `analyse()["merge_assistant"] is False`, étape `operation` présente.
  - `reprise` (vigilance 5) : marque et `MERGE_HEAD` présents → `analyse()["merge_assistant"] is True`, `fusion_b` courante.
  - `abandon` : `abandonne` → `MERGE_HEAD` absent, marque absente, HEAD inchangé. Même chose sur un merge étranger ; un rebase en cours → `RuntimeError`.
  - `ff_origin` : `origin` est avancé par un autre clone → `analyse()["retard_origin"] == 1`, `lance_merge` → `RuntimeError` ; `ff_origin` puis `lance_merge` → accepté.
  - `build_en_cours` : `builds=lambda: ["pio run -e x"]` → `RuntimeError` ; `builds=lambda: None` → `RuntimeError` contenant « impossible de vérifier ».
  - `push` : `pousse` → `git -C origin.git log development` contient le commit de merge.
  - `push_refuse` (vigilance 3) : `origin` est avancé par un autre clone → `pousse` → `RuntimeError` ; `origin` est inchangé.
  - `jamais_de_force` : la source de `synchro_fork_fusion.py` ne contient ni `--force`, ni `"-f"`, ni `stash`, ni `reset`, ni `rebase`.
- [x] Lancer : ROUGE. — preuve : ModuleNotFoundError (task-2-report.md)
- [x] Ajouter `historique=None` à `noter_historique` (défaut `HISTORIQUE`), puis écrire `synchro_fork_fusion.py` et le brancher dans `analyse`. — preuve : 9318a0193
- [x] Banc VERT. Le script au terminal reste inchangé : `python -u outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py --help` affiche le même texte. — preuve : fusion 121 OK, assistant 72 OK, web vert, --help identique ; relecture + re-relecture (8/8 traites)
- [x] Témoins (copies dans le scratchpad) : — preuve : temoins resolu sans marqueurs et liste de prevision ROUGES ; +4 temoins du correctif ROUGES (task-2-report.md)
  - un `resolu` qui n'inspecte pas les marqueurs → ROUGE ;
  - une liste de conflits prise dans `prevision()` au lieu de `--diff-filter=U` → ROUGE sur `merge_etranger` ou `reprise`.
- [x] Commit `feat(synchro-fork): merge local guide de l assistant`. — preuve : 9318a0193 + fix f9fdb16ae

## A3 — Routes du serveur

Fichiers :
- modifier `synchro_fork_web.py` ;
- étendre `test_synchro_fork_web.py` (groupe `assistant`).

Interfaces consommées : `analyse`, `trois_voies`, et les actions d'A2.

Interfaces produites :
- `fabrique_gestionnaire(session, acces, racine=REPO, builds_en_cours=build_serie.builds_en_cours_defaut)`.
- `traite_post(chemin, demande, session, racine, builds_en_cours, verrou)`.
- Routes :
  - `GET /assistant` → `analyse(racine)` ;
  - `GET /trois-voies?chemin=` → JSON `{mien, amont}`, la liste autorisée étant `touches_deux` ∪ chemins de `conflits()` ;
  - `POST /assistant/action` avec `{action, chemin?, choix?, confirmation?}`.
- `action` ∈ `bascule`, `ff-origin`, `merge`, `resout`, `ouvre`, `termine`, `abandonne`, `pousse`.
  - `abandonne` et `pousse` exigent `confirmation == "oui"`, sinon `ValueError`.
  - Réponse : `{"ok": True, "resultat": str, "analyse": analyse(racine, fetch=False)}`.
- Le verrou est un `threading.Lock` pris par `acquire(blocking=False)`. S'il est occupé : `RuntimeError("une action est deja en cours")`.

Étapes :
- [x] Banc rouge, groupe `assistant` : serveur sur un port libre, avec `racine` = faux dépôt et `builds_en_cours=lambda: []`. — preuve : test_synchro_fork_web.py groupe assistant (52e466b23)
  - `GET /assistant` rend 200 et une liste `etapes`.
  - Un POST sans `X-Synchro` rend 403.
  - Une action inconnue rend 400.
  - `pousse` sans confirmation rend 400.
  - Un chemin de `/trois-voies` hors liste rend 400.
  - Une action pendant une exécution de la session (faux script qui attend une question) rend 409.
  - **Double clic** (vigilance 4) : deux POST `merge` simultanés (deux threads) rendent exactement un 200 et un 409.
- [x] Lancer : ROUGE. — preuve : TypeError sur racine (task-3-report.md)
- [x] Implémenter. Ajouter les routes à la docstring de `synchro_fork_web.py`. — preuve : 52e466b23
- [x] Banc VERT (tous les groupes de `test_synchro_fork_web.py`, plus `test_synchro_fork_assistant.py`). — preuve : web VERT, double clic [200, 409], assistant et fusion verts ; relecture approuvee
- [x] Commit `feat(synchro-fork): routes de l assistant`. — preuve : 52e466b23

## A4 — La page

Fichiers :
- créer `synchro_fork_page_assistant.py` et `test_synchro_fork_page_chrome.py` ;
- modifier `synchro_fork_page.py`.

Interfaces consommées : les routes d'A3, ainsi que les événements `debut` (`script`, `simulation`) et `fin` (`code`) du flux.

Interfaces produites :
- `synchro_fork_page_assistant.BLOC` (HTML du bloc, placé sous la sortie du script dans l'onglet merge).
- `synchro_fork_page_assistant.SCRIPT` (JS).
- `synchro_fork_page_assistant.STYLE` (CSS, avec les variables de couleur existantes).
- `PAGE` les insère par `.replace()` sur trois repères commentés.

Comportement :
- L'assistant s'affiche après un `fin` (code 0) dont le `debut` était `script == "merge"` avec `simulation == true`, ou au chargement si `GET /assistant` rend `merge_assistant == true`.
- Liste verticale, une ligne par étape (✔ faite, ✖ bloquée, ○ attente, la courante dépliée) ; chaque bouton affiche la commande git exacte qu'il lance.
- L'étape `synchro_a` appelle le lancement existant (`lance("merge", false)`).
- La voie B montre un tableau des conflits avec les boutons prévus par `type` (§6), la vue trois colonnes au clic, et « Abandonner le merge » toujours visible.
- `pousse` et `abandonne` demandent un second bouton « Confirmer ».
- L'analyse est rafraîchie après chaque action (champ `analyse` de la réponse) et après chaque `fin`.
- Rebase : le bouton d'onglet « Synchro (rebase) » est déplacé dans un `<details>` « Avancé » placé après les onglets. L'avertissement de la spec §8 figure en tête de l'onglet.
- Aide : un paragraphe sur l'assistant.

Étapes :
- [x] Sonde Chrome rouge d'abord, sur le modèle de `outils_pc/test_build_page_chrome.py` : DevTools, `Runtime.evaluate` après délai, `Runtime.exceptionThrown`. — preuve : test_synchro_fork_page_chrome.py ROUGE 12 KO (task-4-report.md)
  - Mise en place : serveur sur le faux dépôt en conflit ; la session porte un faux `synchronise_fork_tasmota.py` (dossier temporaire) qui imprime puis sort en 0.
  - Clic sur « Diagnostic seul » → l'élément `#assistant` est visible et contient `fusion_b` courante.
  - Clic sur « Lancer le merge » → le tableau des conflits a une ligne.
  - Clic sur « Prendre l'amont » → la ligne disparaît.
  - Clic sur « Terminer » → la liste est recalculée.
  - Rechargement en plein merge (vigilance 5) → l'assistant est visible sans dry-run.
  - `<details>` « Avancé » présent, onglet rebase accessible.
  - Aucune exception JS.
- [x] Lancer : ROUGE (`#assistant` absent). — preuve : #assistant absent avant implementation
- [x] Implémenter le bloc et l'insérer dans `PAGE`. — preuve : 722d4684f
- [x] Sonde VERTE. Témoin : un `SCRIPT` qui référence un id absent → exception relevée, ROUGE. — preuve : sonde VERTE sans exception JS + XSS teste ; temoins id absent et sans echappe ROUGES (4fd8f5452)
- [x] Commit `feat(synchro-fork): assistant pas a pas sur la page`. — preuve : 722d4684f + fix 4fd8f5452

## A5 — Documentation et relecture

- [x] `outils_docs/README.md`, section de la synchro du fork : l'assistant, ses deux voies, ce qu'il ne fait jamais. — preuve : nouvelle section « Synchro du fork (page web) » (lancer, l'assistant, ce qu'il ne fait jamais, bancs) + ligne d'index
- [x] `CLAUDE.md` : — preuve : 560 lignes, carte `maintenance/` (3 modules, 3 bancs, sonde, faux depot, liste blanche), exception `build_serie`, paragraphe de la page web ; `verifie_references_docs.py` → 0 defaut, code 0
  - ligne `synchro_fork_*` de la carte des documents (nouveaux modules, bancs, sonde) ;
  - compte de lignes de `synchronise_fork_tasmota.py` ;
  - `outils_pc/build_serie` ajouté à l'exception d'import.
  - Puis `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` → code 0.
- [x] Relecture du diff complet par un sous-agent neuf (superpowers:requesting-code-review). Corriger, puis relancer les trois bancs. — preuve : relecture finale (opus) 0 critique, 2 importants + 9 mineurs corriges en 33e191da5, re-relecture 11/11 ; bancs assistant, fusion, fusion_suite, web x3, sonde Chrome verts ; 3 residus notes (registre)
- [ ] Commit `docs(synchro-fork): assistant pas a pas`.

## A6 — Essai réel (avec l'utilisateur)

- [ ] Page lancée par l'utilisateur (tâche « Outil : synchro du fork »), dry-run sur le vrai dépôt : l'assistant montre les étapes attendues pour l'état du jour. Au 2026-10-27 : 2 commits de retard, prévision sans conflit ; l'arbre sale bloque tant que les fichiers du build ne sont pas commités.
- [ ] Après accord de l'utilisateur seulement : voie A jusqu'à la question « Pousser ? », à laquelle **l'utilisateur** répond. Résultat noté ici.

## Améliorations restantes

## Vérification

- `python -u outils_docs/scripts_python/maintenance/test_synchro_fork_assistant.py` → code 0.
- `python -u outils_docs/scripts_python/maintenance/test_synchro_fork_web.py` → code 0.
- `python -u outils_docs/scripts_python/maintenance/test_synchro_fork_page_chrome.py` → code 0.
