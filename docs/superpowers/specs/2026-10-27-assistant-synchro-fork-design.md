# Assistant pas à pas de la page « Synchro du fork » — conception

Date : 2026-10-27. Statut : en revue par l'utilisateur.
Outil existant : la page de synchro du fork, http://127.0.0.1:7500
(`outils_docs/scripts_python/maintenance/synchro_fork_web.py` et ses modules `synchro_fork_*.py`).

## 1. Intention

Aujourd'hui, le bouton « Diagnostic seul (--dry-run) » de la page dit où en est le fork (avance,
retard, nouveautés de l'amont) puis s'arrête. Il ne dit pas **quoi faire ensuite** : il faut deviner
s'il faut commiter d'abord, si un fichier modifié des deux côtés va poser problème, s'il faut pousser,
et relancer le bon script. Et quand l'amont entre en conflit avec le fork, le script de merge abandonne
(`synchronise_fork_tasmota.py::synchro_locale` fait `git merge --abort`) en renvoyant vers le script de
**rebase** — l'autre stratégie, qu'il ne faut justement pas mélanger.

L'assistant transforme le résultat du dry-run en une **liste d'étapes**, propre au cas constaté, que
l'on suit une à une jusqu'à un fork synchronisé, **y compris en cas de conflit, en restant en merge**.

Un succès : après un dry-run, on n'a plus jamais besoin du terminal ni de réfléchir à l'ordre des
opérations ; chaque étape dit pourquoi elle est là, ce qu'elle va faire, et attend un clic.

## 2. Décisions de l'utilisateur (2026-10-27)

1. **Déclencheur** : l'assistant apparaît **après le dry-run seulement** (bouton existant
   « Diagnostic seul (--dry-run) » de l'onglet merge), sous la sortie du script. Rien n'est analysé
   sans ce geste.
2. **Présentation** : **liste d'étapes verticale**. Toutes les étapes utiles visibles d'un coup avec
   leur statut ; seule l'étape courante est dépliée et active.
3. **Arbre de travail sale** : **montrer, classer, bloquer**. Chaque fichier suivi modifié est listé
   avec son diff et classé « touché aussi par l'amont » (rouge) ou « sans recouvrement ». L'étape reste
   bloquée tant que l'arbre n'est pas propre : l'utilisateur commite lui-même (`/commite`), puis bouton
   « Revérifier ». **La page ne commite pas ces fichiers.**
4. **Conflit prévu** : **résolution dans le merge**. Merge local de l'amont, puis fichier par fichier :
   garder le mien / prendre l'amont / ouvrir dans VS Code, puis « marquer résolu ». Jamais de rebase,
   jamais de push forcé.
5. **Rebase** : l'onglet « Synchro (rebase) » reste, **replié en mode avancé** (section « Avancé »),
   avec le rappel « ne pas mélanger les deux stratégies ».

## 3. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Après un dry-run, une liste d'étapes calculée à partir de l'état réel : branche, arbre, avance,
  retard, commits non poussés, fichiers touchés des deux côtés, prévision exacte du merge.
- Voie sans conflit : la voie actuelle (synchro en ligne GitHub puis locale, puis push confirmé).
- Voie avec conflit : merge local guidé fichier par fichier, commit du merge, push confirmé, journal.
- Le terminal ne change pas : `synchronise_fork_tasmota.py` garde son déroulé et ses questions.

**Non-objectifs**
- Synchroniser une autre branche que `development` (le hook de détection et la règle du dépôt ne
  parlent que d'elle ; une autre branche affichée = étape « basculer sur development »).
- Résoudre un conflit **à l'intérieur** d'un fichier dans la page (éditeur de fusion) : c'est le rôle
  de VS Code, que l'assistant ouvre.
- Remonter des commits vers l'amont (arendst) : l'avance du fork est normale et le reste.

**Anti-objectifs** (ce qui ferait échouer l'outil même s'il « marche »)
- Un `git push --force`, un `git stash`, un `git reset`, ou un rebase déclenché par l'assistant.
- Une action qui modifie quelque chose (fetch excepté) sans clic explicite de l'utilisateur.
- Un merge tué en plein vol, laissant `MERGE_HEAD` sans que la page le montre.
- Commiter les fichiers de travail de l'utilisateur (règle du dépôt).
- Annoncer « aucun conflit » sur une prévision qui ne regarde pas le dépôt local réel.

## 4. Les étapes

L'analyse produit une liste ordonnée ; chaque étape a un statut : **faite** ✔, **à faire** (courante,
dépliée), **bloquée** ✖ (une condition manque, le texte dit laquelle), **en attente** ○ (une étape
précédente n'est pas faite), ou **sans objet** (masquée). Après chaque action, l'analyse est refaite et
la liste recalculée : l'état affiché est toujours celui du dépôt, jamais un état mémorisé par la page.

| # | Étape | Apparaît quand | Contenu, action |
|---|---|---|---|
| 1 | Pas d'opération git en cours | `MERGE_HEAD` ou rebase en cours **non lancé par l'assistant** | Bloquée : explique, propose « Abandonner le merge » (`git merge --abort`) seulement pour un merge ; un rebase se termine au terminal. |
| 2 | Branche `development` | HEAD ≠ `development` | Bouton « Basculer sur development » (`git switch development`), actif seulement si l'arbre est propre. |
| 3 | Arbre propre | fichiers suivis modifiés (hors journal des synchros, comme `arbre_sale()`) | Liste classée (§5.2), diff au clic, « Revérifier ». Bloquée tant que la liste n'est pas vide. Les non suivis sont comptés, pas bloquants (comme aujourd'hui). |
| 4 | Lire les nouveautés | retard > 0 | Les commits de l'amont, ● en tête, et la liste des fichiers que l'amont touche. Commits pris dans le dépôt local (`git log HEAD..upstream/development`), passés par un adaptateur qui produit les mêmes tuples `(sha, titre, mots)` qu'`analyser_commits` (qui, elle, lit des dicts de l'API GitHub) : ce sont eux qu'écrit le journal en voie B. **Étape d'information, jamais bloquante** : pas de bouton « J'ai lu », elle n'empêche aucune étape suivante. |
| 5 | Fichiers touchés des deux côtés | intersection non vide (§5.1) | Pour chaque fichier, une vue trois colonnes : base commune / mon fork / l'amont (§5.3). Information, pas de blocage. |
| 6 | Prévision du merge | retard > 0 | Résultat de `git merge-tree` : « sans conflit » ou « N fichier(s) en conflit » (liste). Choix de la voie : ci-dessous. |
| 7A | Synchroniser (en ligne puis local) | prévision sans conflit **et** aucun commit local non poussé | Lance le script de merge **réel** par la session existante (`/lance merge`, sans `--dry-run`) : ses questions (« Synchroniser ? », « Pousser ? ») restent ses boutons habituels. |
| 7B | Merger en local (et résoudre) | prévision avec conflit, **ou** des commits locaux non poussés | Voie §6 : merge local, résolution fichier par fichier s'il y a lieu (sans conflit, la voie se réduit à « Lancer le merge » puis « Terminer »), commit du merge. |

**Pourquoi des commits non poussés imposent la voie B** : la voie A fusionne d'abord **en ligne**
(`merge-upstream` de GitHub : origin + amont, sans les commits locaux), puis en local. La prévision,
elle, est calculée sur le HEAD local : avec des commits non poussés, elle ne décrit pas ce que fera la
voie A, et un conflit pourrait n'apparaître qu'à l'étape locale, après la fusion en ligne — état
« en ligne fait, local en retard » que le script gère en abandonnant. Quand HEAD = `origin/development`,
la prévision locale est exactement celle de GitHub, et l'étape locale du script est une avance rapide
(sans conflit possible). Si malgré tout le script de la voie A finit en échec, la réanalyse qui suit
voit l'état réel (local en retard sur origin, ou retard intact) et propose les étapes correspondantes
(`ff-origin`, ou voie B) : aucune transition spéciale n'est codée.
| 8 | Pousser | commits locaux non poussés vers `origin/development` (y compris quand il n'y a **aucun** retard) | Liste des commits, bouton « Pousser » avec confirmation ; `git push origin development`, jamais `--force`. En voie A, c'est la question du script qui joue ce rôle : l'étape 8 ne s'affiche que si des commits restent non poussés après lui. |
| 9 | Commiter le journal | `HISTORIQUE_SYNCHRO_FORK.md` modifié | Le bouton existant « Commiter le journal » (`synchro_fork_etat.commit_journal`). |

Cas particuliers :
- **Retard 0, avance > 0, rien à pousser** : une seule ligne « Fork à jour ; tes N commits d'avance
  sont normaux et restent dans le fork ». Aucune étape.
- **Retard 0, commits non poussés** : seule l'étape 8.
- **Dry-run en échec** (code ≠ 0, GitHub injoignable) : pas d'assistant, le message d'erreur du script
  suffit.

## 5. L'analyse (lecture seule, hormis le fetch)

Déclenchée par la page à la fin d'un dry-run réussi (événement `fin`, `code == 0`, précédé d'un
`debut` avec `simulation: true` et `script: "merge"` ; `fin` ne porte pas `simulation` : la page le
retient du `debut`), puis après chaque action de l'assistant. Exception : si un merge lancé par
l'assistant est en cours (§6), l'assistant s'affiche dès le chargement de la page, pour qu'on ne perde
pas le fil d'un merge commencé.

### 5.1 Ce qui est calculé, et sur quoi

L'analyse travaille sur le **dépôt local**, car c'est là que le merge aura lieu :
1. `git fetch upstream development` et `git fetch origin` (le hook de détection fait déjà le premier ;
   un fetch ne touche ni l'arbre ni l'index). Échec réseau → l'analyse le dit, rien d'autre n'est fait.
2. Retard local = `git rev-list --count HEAD..upstream/development` ; non poussés =
   `origin/development..HEAD` (calcul déjà fait par `synchro_fork_etat.etat`, à réutiliser). Les chiffres GitHub du dry-run restent affichés à côté (ils peuvent
   différer : commits non poussés), avec une phrase qui l'explique, comme le fait déjà `diagnostic()`.
3. Fichiers touchés par l'amont = `git diff --name-only HEAD...upstream/development` ; par le fork =
   `git diff --name-only upstream/development...HEAD` ; **touchés des deux côtés** = intersection.
4. **Prévision** = `git merge-tree --write-tree --name-only --no-messages HEAD upstream/development`
   (git ≥ 2.38 ; poste actuel : 2.54). Code 0 = merge propre ; code 1 = conflits, fichiers listés après
   l'identifiant d'arbre. L'objet arbre écrit dans `.git/objects` est sans référence (ramassé par
   `git gc`) : sans effet visible. git trop ancien → l'étape 6 dit « prévision impossible » et la voie A
   reste proposée (le script abandonne proprement en cas de conflit, comme aujourd'hui).
5. Arbre sale, classé (§5.2).

### 5.2 Classement des fichiers modifiés (étape 3)

Chaque fichier suivi modifié reçoit, à partir de `synchro_fork_etat.fichiers_modifies` (dicts
`{etat, chemin, journal}`, journal déjà repéré ; **pas** `arbre_sale()` du script, qui rend des lignes
brutes), la classe suivante :
- **touché aussi par l'amont** (rouge) : il est dans la liste du §5.1-3 côté amont. Commiter avant la
  synchro est indispensable, et il peut ensuite entrer en conflit (la prévision le dira).
- **sans recouvrement** : l'amont n'y touche pas.
Les fichiers que le build réécrit (`platformio_override.ini`, `tasmota/user_config_override.h`,
`lib/libesp32/berry_custom/src/modules.h`, `tasmota/tasmota_defines_for_berry.*`) sont signalés comme
tels (« réécrit par le build ») : c'est le cas le plus fréquent, et la règle du dépôt dit lesquels se
commitent (voir `tasks/lessons.md`, 2026-10-13). L'assistant **n'en commite aucun** : il renvoie à
`/commite`.

### 5.3 Vue trois colonnes (étape 5 et voie B)

Pour un chemin de la liste, la page affiche le diff « base → mon fork » et le diff « base → amont »
côte à côte (base = `git merge-base HEAD upstream/development`). Contenu obtenu par `git diff
<base> HEAD -- f` et `git diff <base> upstream/development -- f`, tronqué comme `synchro_fork_etat.diff`
(300 Ko). Chemin refusé s'il n'est pas dans la liste calculée (même règle que `/diff` : pas de lecture
arbitraire du disque).

## 6. Voie B : merge local guidé

Préalables vérifiés au clic (refus avec explication sinon) : branche `development`, arbre propre,
aucune exécution de script en cours (`Session.en_cours()`), **aucun build en cours** (§7), local à
jour avec `origin/development` (sinon `git merge --ff-only origin/development` d'abord, proposé comme
sous-étape).

1. **Lancer le merge** : `git merge --no-ff --no-commit upstream/development`. Le dépôt est alors en
   état de merge (`MERGE_HEAD`), conflits marqués. La liste des fichiers en conflit vient de
   `git diff --name-only --diff-filter=U`, **pas** de la prévision (c'est le dépôt qui fait foi).
2. **Pour chaque fichier en conflit**, trois actions :
   - **Garder le mien** : `git checkout --ours -- f` puis `git add -- f` ;
   - **Prendre l'amont** : `git checkout --theirs -- f` puis `git add -- f` ;
   - **Ouvrir dans VS Code** : `code -r <chemin absolu>` (l'éditeur de fusion de VS Code s'ouvre sur un
     fichier en conflit), puis **Marquer résolu** : refusé si le fichier contient encore des marqueurs
     `<<<<<<<` / `=======` / `>>>>>>>` en début de ligne ; sinon `git add -- f`.
   La vue trois colonnes du §5.3 est disponible sur chaque fichier.
   **Conflits sans marqueurs** (type lu dans `git status --porcelain` : `DU`, `UD`, `AU`, `UA`, `DD`,
   `AA`, ou fichier binaire) :
   - modifié d'un côté, supprimé de l'autre : les deux boutons disent ce qu'ils font — « Garder le
     fichier » (`git add -- f`, version présente sur le disque) / « Le supprimer » (`git rm -- f`),
     libellés selon le côté qui supprime ; pas de « Ouvrir » ni de contrôle de marqueurs ;
   - binaire : seulement « Garder le mien » / « Prendre l'amont » ;
   - tout autre cas : affiché comme « à résoudre au terminal » (commande indiquée), et « Terminer le
     merge » reste inactif tant que git le liste en conflit.
3. **Terminer le merge** : actif quand plus aucun fichier n'est en conflit. `git commit --no-edit`
   (message par défaut de git : « Merge remote-tracking branch 'upstream/development' into development »).
   Puis entrée au journal des synchros par `synchronise_fork_tasmota.noter_historique` (mêmes
   commits, `type_merge` = « merge local (conflits résolus) »).
4. **Pousser** : étape 8. Après le push, `origin/development` contient les commits de l'amont : le fork
   en ligne n'est plus en retard, sans passer par `merge-upstream` de GitHub (qui aurait refusé).
5. **Abandonner le merge** : bouton visible pendant toute la voie B ; `git merge --abort`, confirmation
   demandée. Dépôt rendu à son état d'avant.

Un merge laissé en cours (page fermée, serveur arrêté) est retrouvé à la réanalyse : s'il a été lancé
par l'assistant (`MERGE_HEAD` = `upstream/development` résolu au moment de l'analyse), la voie B reprend
à l'étape 2 ; sinon l'étape 1 le signale comme opération étrangère. Le refus de `/lance` pendant un
merge (`synchro_fork_etat.operation_git`) reste en place.

## 7. Garde-fous

- **Un clic = une action git**, annoncée avant (la commande exacte est affichée sous le bouton).
- **Revérification à chaque clic** de la voie B : branche `development` et `MERGE_HEAD` = le commit
  `upstream/development` qu'a fusionné l'assistant (noté dans `.git/` par l'assistant au lancement du
  merge, fichier à lui). Sinon refus 409 « merge étranger » : jamais de `checkout --ours/--theirs` sur
  un merge que l'assistant n'a pas lancé.
- **Jamais** : `--force`, `stash`, `reset`, `rebase`, `checkout` d'une autre branche que
  `development`, commit d'un autre fichier que ceux du merge en cours ou du journal.
- Les POST de l'assistant suivent les règles des POST existants : en-tête `X-Synchro: 1`, même
  origine, corps JSON validé, refus 409 si un script tourne ou si une autre action de l'assistant est en
  cours (un verrou).
- **Build en cours** → refus de toute action qui modifie l'arbre (basculer de branche, merge, résolution,
  abandon) : un merge réécrit des fichiers lus par `pio`. Détection : celle de
  `outils_pc/build_serie.py::builds_en_cours_defaut` (même règle que les pages build et fichiers Berry),
  importée par le même `sys.path` explicite qu'`acces_web` (exception déjà notée dans `CLAUDE.md`, à
  compléter). **Détection impossible (`None`) = refus**, avec le message « impossible de vérifier
  qu'aucun build ne tourne ».
- Push : confirmation explicite, `git push origin development`, sortie de git affichée telle quelle.
- Les actions git de l'assistant tournent avec `GIT_EDITOR=true` et `GIT_TERMINAL_PROMPT=0` (comme la
  session), et un délai maximal ; un délai dépassé est **signalé, jamais suivi d'un kill** d'un merge
  (même raison que la session : pas d'arrêt forcé en plein vol).

## 8. La page

- Onglet « Synchro (merge) » : sous la sortie du dry-run, le bloc **Assistant** (liste verticale du §4).
  Le bouton « Synchroniser… » existant reste (lancement direct du script, comme aujourd'hui).
- Onglet « Synchro (rebase) » : déplacé dans une section **Avancé** repliée (bouton ou onglet
  discret), avec en tête : « Stratégie rebase : ne pas l'alterner avec le merge, c'est ce qui fait
  diverger un fork. Pour la synchro habituelle, utiliser l'assistant. »
- Onglet « Aide » : un paragraphe sur l'assistant (étapes, voie B, ce qu'il ne fait jamais).
- `outils_docs/README.md` (section de la synchro) et `CLAUDE.md` (carte des documents, ligne
  `synchro_fork_*`) : complétés.

## 9. Ce que je laisse au constructeur (choix faits par Claude, à valider en relisant)

- **Découpage** : un module `synchro_fork_assistant.py` (analyse et liste d'étapes, fonctions pures
  testables sur un faux dépôt) et un module `synchro_fork_fusion.py` (actions de la voie B et push) ;
  le JS/HTML de l'assistant dans un module à part (`synchro_fork_page_assistant.py`) concaténé à
  `PAGE`, pour garder `synchro_fork_page.py` lisible.
- **Routes** proposées : `GET /assistant` (analyse), `GET /trois-voies?chemin=`, `POST /assistant/action`
  `{action, chemin?, confirmation?}` avec `action` ∈ {`bascule`, `ff-origin`, `merge`, `garde-mien`,
  `prend-amont`, `ouvre`, `resolu`, `termine`, `abandonne`, `pousse`}.
- La voie A réutilise le script réel plutôt que de réappeler ses fonctions une à une : son déroulé et
  ses gardes (arbre sale vérifié **avant** la synchro distante) restent la référence unique.
- `code -r` peut ouvrir le fichier dans une autre fenêtre VS Code que celle du dépôt : acceptable
  (l'utilisateur voit le fichier) ; si `code` est introuvable, le bouton le dit et donne le chemin.
- Après la relecture « constructeur » : voie B imposée dès qu'il y a des commits non poussés (§4) ;
  étape 4 non bloquante, sans « J'ai lu » ; conflits sans marqueurs (§6) ; revérification du
  `MERGE_HEAD` à chaque clic (§7) ; détection de build impossible = refus (§7) ; commits du journal
  pris dans le dépôt local par un adaptateur (§4) ; assistant affiché au chargement si un merge de
  l'assistant est en cours (§5).

## 10. Vérification

- **Banc** `test_synchro_fork_assistant.py` (code de sortie 0 = vert), sur un **faux dépôt** construit
  dans un dossier temporaire : un dépôt nu « amont », un dépôt nu « origin », un clone de travail
  (remotes `upstream` et `origin` locaux, aucun réseau, jamais le vrai dépôt). Cas : à jour ; avance
  seule ; retard sans recouvrement ; retard avec fichier touché des deux côtés sans conflit ; conflit
  prévu → merge → garder le mien / prendre l'amont / marqueurs restants refusés → terminer → push
  (vers le nu « origin », vérifié par `git log`) ; abandon ; arbre sale classé ; build en cours simulé
  → refus ; détection de build impossible → refus ; merge étranger détecté et refusé au clic ; commits
  non poussés + prévision sans conflit → voie B (pas A) ; fichier modifié ici et supprimé par l'amont.
- **Témoins** : un analyseur qui prendrait la prévision au lieu de `--diff-filter=U` pour la liste des
  conflits, et un « Marquer résolu » qui n'inspecterait pas les marqueurs, doivent faire échouer le banc.
- Groupe ajouté à `test_synchro_fork_web.py` : routes de l'assistant (en-tête, origine, 409, chemin
  hors liste refusé).
- **Sonde Chrome** (leçons du 2026-10-16 et du 2026-10-17) : page pilotée par DevTools sur le serveur
  branché au faux dépôt ; dry-run simulé → assistant affiché, clic sur chaque étape, aucune erreur JS.
- **Essai réel** en fin de chantier, avec l'utilisateur : dry-run sur le vrai dépôt (2 commits de retard
  au 2026-10-27, prévision « sans conflit »), voie A jusqu'à la question de push.
