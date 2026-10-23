# Tasmota (fork personnel) — regles de ce depot

> Ces regles ne valent QUE pour ce depot. Elles completent `~/.claude/CLAUDE.md`
> et, en cas de contradiction, elles priment ici.
>
> **Ce fichier est auto-suffisant.** Il ne suppose PAS que le `~/.claude/CLAUDE.md`
> global soit present : sur un autre poste, il ne le sera pas. Tout ce qui est
> necessaire pour travailler correctement sur ce depot est ici ou pointe d'ici.

## AU DEMARRAGE DE CHAQUE SESSION — a lire avant toute action

Une session demarre **froide** : elle ne se souvient d'aucun echange precedent. Tout ce
qui survit est ecrit dans ces fichiers. Les lire N'EST PAS optionnel — c'est ce qui
remplace la memoire.

1. **`tasks/lessons.md`** — le journal des erreurs deja commises et des regles qui en
   decoulent. **A lire en entier avant de toucher au code.** Chaque entree est une erreur
   passee a ne pas refaire (5 pieges de verification y sont consignes, tous payes comptant).
2. **`tasks/reprise-chantier-modbus-grenier.md`** — le chantier en cours. ⚠️ **Son nom dit
   « grenier », mais les cibles sont les 3 modules GARAGE** (maitre P4, cuve, rideau)
   depuis le 2026-07-24 ; le grenier est en sommeil. Repartir sur le grenier est une
   erreur deja commise, consignee dans `lessons.md`. **Lire son encadre de tete « SI TU
   REPRENDS A FROID »** : il porte la prochaine action et la liste de ce qui reste.
   Le travail se fait sur **`development`** : la branche `chantier-modbus-grenier`, fusionnee,
   a ete supprimee le 2026-10-04.
3. **`tasks/reprise-solidification-berry.md`** — l'autre chantier (solidification Berry),
   sa prochaine action et ses questions ouvertes.
4. **`outils_docs/SOLIDIFICATION_BERRY.md`** — le mecanisme complet + 11 pieges, a lire
   des que le sujet Berry/solidification arrive.
5. **`outils_docs/PROTOCOLE_MODBUS.md`** — a lire des que le sujet ModBus arrive : carte
   des registres de la carte 16 relais (§8) et architecture de synchronisation (§9).
6. **`tasks/plans/`** — plans de travail suivis (`statut: actif`, format `tasks/plans/_FORMAT.md`) :
   le mod `suivi-plan` en injecte le resume en debut de conversation ; sans le mod, lire le plan actif.

Si le demarrage affiche une ligne `fork : N commit(s) de retard sur upstream/development`,
c'est le hook de detection : voir la section « Synchro du fork » plus bas. **Ne pas lancer
la synchro de sa propre initiative**, et surtout pas dans une branche de chantier.

**Apres chaque correction de l'utilisateur**, ajouter immediatement une entree a
`tasks/lessons.md` au format `[YYYY-MM-DD] | ce qui s'est mal passe | regle a suivre`.
Append uniquement, ne jamais supprimer une entree.

## Pre-commit : PAS de graphify

**`/graphify --update` ne doit PAS etre lance avant un commit sur ce depot.**

La regle globale l'impose sur mes projets ; ce depot y deroge explicitement (decide le
2026-07-15). Raison : il n'y a **pas de `graphify-out/`** ici, donc rien a mettre a jour ;
et en construire une carte sur un depot de la taille de Tasmota (~15 000 fichiers amont)
serait un chantier sans rapport avec le travail mene.

Ordre de commit sur ce depot : `git add` puis `git commit`. Rien d'autre.

Si une carte de connaissances est creee un jour ici, revoir cette regle.

## Synchro du fork : un hook qui DETECTE, une synchro qui reste manuelle

Depuis le 2026-07-24, un hook `SessionStart` signale au demarrage si le fork a pris
du retard sur `arendst/Tasmota`. Il **detecte, il ne synchronise pas**.

- `.claude/hooks/verifie_synchro_fork.sh` — fetch cible d'`upstream/development`
  **bride a une fois par 24 h**, calcul du retard, une ligne a l'ecran. Silence
  total si le fork est a jour. Ne touche **jamais** a l'arbre de travail et sort
  toujours en 0 : hors ligne, VPN ou amont indisponible, la session demarre
  normalement.
- `.claude/settings.json` — declare le hook. **`.claude/` est suivi par git** pour
  que le dispositif voyage entre postes ; seuls `.claude/settings.local.json`
  (permissions locales) et `.claude/.derniere-verif-synchro` (horodatage) sont
  dans le `.gitignore`.

Le retard est mesure sur la branche `development`, **pas sur `HEAD`** : on travaille
presque toujours sur une branche de chantier.

### Pourquoi le hook ne lance PAS la synchro

Le lancement automatique de `synchronise_fork_tasmota.py` a ete envisage puis
**rejete** (decide le 2026-07-24). Ne pas le reintroduire :

- un hook a un **timeout** ; un merge tue en plein vol laisse un `MERGE_HEAD` et un
  index a moitie ecrit — exactement l'etat conflictuel que le dispositif est cense
  eviter, et cree sans que personne ne regarde l'ecran ;
- le script est ecrit **pour un humain devant un terminal** : il demande confirmation
  avant la synchro distante et avant de pousser (`demander()`, lignes 514 et 443). Dans un
  hook, l'entree standard n'est pas un terminal -> la synchro est abandonnee (EOFError
  lu comme « non ») ;
- contre les conflits, la vraie prevention est la **frequence** — petits paquets, sur
  `development` propre, **avant** d'ouvrir un chantier — pas l'automatisme.

### Que faire quand le hook signale du retard

Basculer sur `development` avec un arbre propre, puis lancer la synchro a la main,
sortie sous les yeux. Une seule commande : diagnostic, nouveautes de l'amont listees
**avant** toute action, controle d'arbre propre, puis deux confirmations (synchro du
fork en ligne, puis push) :

```
python outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py
```

Repondre « N » a la premiere question = un diagnostic, rien n'est modifie. `--dry-run`
fait de meme sans poser de question. **Ne jamais merger l'amont
dans une branche de chantier** : le hook le rappelle en affichant la branche courante.

Meme chose depuis une **page web** : tache VS Code « Outil : synchro du fork » ou cible Custom
« Synchro du fork (page web) » -> http://127.0.0.1:7500 (`maintenance/synchro_fork_web.py`). Elle lance
les deux scripts (merge et rebase) tels qu'au terminal, leurs questions deviennent des boutons
(`synchro_fork_question.demander`) ; en plus : etat du fork, fichiers modifies et leur diff, journal
et son commit. Le push force du rebase exige de saisir le nom de la branche, verifie cote serveur.

## Exception assumee a la regle des 500 lignes

`outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py` fait **558 lignes**, et
c'est **voulu** (decide le 2026-07-15, a 527 lignes ; +7 le 2026-10-12 pour le correctif
du blocage sur son propre journal ; +24 le 2026-10-17 pour la confirmation et le
controle d'arbre propre AVANT la synchro distante, et les questions de la page web).
Ne pas le decouper pour satisfaire le compteur.

Decomposition reelle : 345 lignes de code, 59 d'en-tete docstring (qui **est** la
sortie de `--help`), 105 vides, 49 de commentaires. La plus grosse fonction (`main`)
fait 92 lignes. L'esprit de la regle — un fichier qui n'en fait pas trop — est respecte ;
seul le total brut deborde, de 58 lignes de documentation et de blancs.

Extraire un module d'utilitaires partages avec `synchronise_upstream_tasmota.py`
reste possible **le jour ou un troisieme script apparaitra**, pas avant.

`outils_docs/exemples de scripts BERRY/test_liaison_modbus.be` fait **613 lignes**, et
c'est **voulu** (decide le 2026-10-04 : « laisse ce test comme il est »). Ne pas le
decouper : c'est UN fichier a televerser sur chaque carte, qui se prepare et s'explique
seul au chargement ; le scinder imposerait deux televersements par carte.

## MONTER UN NOUVEAU POSTE

Trois choses, dans cet ordre. Rien d'autre n'est necessaire.

### 1. VS Code — Settings Sync (la voie native)

VS Code synchronise lui-meme reglages, extensions, snippets **et profils** entre
machines, via le compte GitHub. En continu, pas en photo : c'est ce qui evite que les
deux postes divergent dans trois mois. Aucun script a maintenir.

Sur **chaque** poste : `Ctrl+Shift+P` -> **`Settings Sync: Turn On...`** -> **cocher
`Profiles`** -> Sign in (GitHub).

> ⚠️ **Cocher `Profiles` n'est pas optionnel.** Par defaut, Settings Sync ne
> synchronise que le profil par defaut. Or nos reglages `C_Cpp` — ceux qui corrigent
> le `PermissionError` (§ suivant) — vivent dans le profil **actif** (« Frederic »).
> Sans `Profiles` coche, ils n'arriveront jamais sur l'autre poste, et le symptome
> reviendra sans qu'on comprenne pourquoi.

Ce qui est synchronise : ~40 Ko de config + la liste des 58 extensions. Les 247 Mo de
`%APPDATA%\Code\User` sont majoritairement de l'etat machine (positions de fenetres,
caches, historique) : ni synchronise, ni souhaitable.

### 2. PlatformIO — rien a faire

`~/.platformio` pese **16,6 Go** (246 000 fichiers), mais **il n'y a rien a copier** :
ce ne sont que des paquets et toolchains telecharges, verifies par empreinte. Aucun
fichier ecrit par nous. Le premier `pio run` les reinstalle seul — plus vite qu'une
copie, et sans risque d'etat incoherent.

Nos vrais reglages PlatformIO (`platformio_override.ini`, `platformio_tasmota_cenv.ini`)
sont **dans le depot**, donc deja la apres le clone.

### 3. Le filet — verifier que les reglages C/C++ agissent vraiment

```
python outils_docs/scripts_python/maintenance/corrige_reglages_vscode.py --verifier
```

Settings Sync **apporte** les reglages mais ne dit jamais **pourquoi** ils existent, et
n'alertera pas si `exclusionPolicy` saute. Ce script, lui, diagnostique (`--etat`),
applique si besoin, et **prouve** que l'exclusion agit (temoin/cible sur l'indexeur).

Il est idempotent, sauvegarde avant d'ecrire, et refuse de fusionner a l'aveugle dans un
`C_Cpp.files.exclude` existant. A lancer si le symptome ci-dessous reapparait.

### 4. Suivi des plans — extension VS Code locale + mod Claude

```
python outils_docs/scripts_python/maintenance/installe_suivi_plan.py --verifier --mod
```

L'extension `fdaubercy.suivi-plan` n'est pas sur la marketplace : Settings Sync ne l'installe pas.

---

## Le PermissionError sur tasmota.ino.cpp — pourquoi ces reglages existent

**Ces reglages ne sont PAS versionnes** : ils vivent dans le profil VS Code de la
machine. Sans Settings Sync (ou sans `Profiles` coche), ils sont **absents** d'un
nouveau poste, et le symptome revient.

### Le symptome, si on les oublie

Build qui echoue **par intermittence** sur :

```
PermissionError: [Errno 13] Permission denied: '...\tasmota\tasmota.ino.cpp'
```

### La cause (mesuree le 2026-07-15, pas supposee)

Ce n'est **ni** Windows Defender **ni** un build concurrent. C'est
`cpptools-srv2.exe -i TagParser`, l'indexeur de l'extension C/C++ de VS Code :
PlatformIO ecrit `tasmota.ino.cpp` (7,6 Mo), le relit, puis le **rouvre en ecriture**
quelques millisecondes plus tard (`pioino.py:104-110`) — l'indexeur s'en saisit
entre-temps. Nomme par le Restart Manager de Windows sur 23 echecs sur 23 ;
reproduit a 92 % dans le depot, 0 % hors depot.

### Le correctif

Dans les reglages du **profil VS Code actif** (et non `User\settings.json` : avec un
profil, ce fichier n'est plus celui qui s'applique). Trouver le profil actif via
`window.newWindowProfile` et `globalStorage\storage.json` (cle `userDataProfiles`) —
p. ex. `%APPDATA%\Code\User\profiles\<id>\settings.json` :

```json
"C_Cpp.files.exclude": {
    "**/.vscode": true,
    "**/.vs": true,
    "**/*.ino.cpp": true
},
"C_Cpp.exclusionPolicy": "checkFilesAndFolders",
```

**Les deux lignes sont indispensables.** Seul, `C_Cpp.files.exclude` **n'a aucun effet** :
par defaut (`checkFolders`) l'extension n'evalue ses exclusions qu'au niveau des
dossiers et « individual files are not checked ». Mesure a l'appui : 8 ouvertures sur 8
malgre l'exclusion, puis 0 sur 10 une fois `exclusionPolicy` pose.

**Ne PAS le mettre dans `.vscode/settings.json`** : ce fichier est suivi par git **et**
existe en amont — toute modification entrerait en conflit a chaque synchronisation du fork.

Prise en compte a chaud, sans redemarrer VS Code.

## Commits

- Messages **en francais** — titre et corps. Regle explicite du 2026-07-15. Le depot amont
  est anglophone : ce fork ne l'est pas, et ses commits ne remontent pas chez arendst.
  Seuls les prefixes conventionnels (`feat:`, `fix:`, `docs:`, `chore:`) restent en anglais :
  ce sont des etiquettes lues par les outils, pas de la prose.
- Messages **sans accents** (precedent d'encodage casse).
- **Pas** de trailer `Co-Authored-By`.
- **Ne jamais pousser** sans demande explicite : le push n'est pas auto-autorise sur ce depot.
- Ne **jamais** commiter le travail en cours de l'utilisateur sans demande explicite.

## Fichiers a ne jamais toucher sans accord

- `data/fs/*.be` — modules en cours d'ecriture par l'utilisateur.
- `.vscode/settings.json` — suivi par git **et** present en amont : toute modif entrera
  en conflit a chaque synchronisation du fork. Les reglages VS Code personnels vont dans le
  profil actif (`%APPDATA%\Code\User\profiles/<id>/settings.json`), pas ici.

## Vigilances de build

- Un build reecrit `tasmota/user_config_override.h` (`increment_config_holder`) et
  `platformio_override.ini` (`adapteParametresPlatformio_override`). Sauvegarder avant une
  serie de builds experimentaux.
- **Ne jamais lancer un build en parallele de celui de l'utilisateur** : deux `pio` ecrivant
  `tasmota/tasmota.ino.cpp` se plantent mutuellement.
- **IntelliSense ne doit jamais se reconstruire pendant un build** (constate le 2026-10-01) :
  `scons __idedata`, lance par l'extension PlatformIO/pioarduino quand `platformio_override.ini`
  change, execute `pio-tools/solidify-from-url.py`, dont `cleanFolder()` efface les
  `_temp_be_*.c` et reecrit `modules.h` de `lib/libesp32/berry_custom` pour l'env actif de
  l'IDE. Symptome : `TypeError : unsupported operand type(s) for -: 'float' and 'NoneType'`
  sur un `_temp_be_<module>_lib.c` ; pire, un build peut reussir avec la table de modules d'un
  autre env. Parade : `"platformio-ide.autoRebuildAutocompleteIndex": false` dans le **profil
  VS Code actif** (non versionne, voir « MONTER UN NOUVEAU POSTE »). Index a reconstruire a la
  main, hors build.
- Pour surveiller un build en redirigeant la sortie, poser `PYTHONIOENCODING=utf-8` :
  sinon Python passe en cp1252, le `✔` du script pre-build tue le thread de recopie de pio,
  et **toute** la sortie est perdue. Ne pas « corriger » le script de l'utilisateur pour ca.
- **Aucune cible PlatformIO pendant un build, meme un outil** (constate le 2026-10-10) : les
  cibles Custom « Sniffeur ModBus », « Sniffeur MQTT », « Serveur syslog » sont des `pio run`.
  Avant toute chose, `pio run` compare l'empreinte du projet a `.pio/build/project.checksum`
  et, si elle differe, **supprime tout `.pio/build`**, tous envs compris
  (`platformio/run/helpers.py:35-41`). L'empreinte inclut la liste des `.c/.h` de `lib/`
  (`project/helpers.py:157-175`), or le pre-build regenere les `_temp_be_*.c` de
  `berry_custom` **selon l'env** : changer d'env change l'empreinte. Symptome : un
  `erase_upload` P4 lance a 15:14, la cible sniffeur (env cave) a 15:37:31, `.pio/build`
  vide a 15:37:39, puis `*** [.pio\build\<env>\libXXX] ... Le chemin d'acces specifie est
  introuvable`. Le pre-build du sniffeur reecrit aussi `modules.h` en plein build (piege
  IntelliSense ci-dessus). Parade : pendant un build, lancer ces outils **hors PlatformIO**,
  directement par `python outils_docs/scripts_python/outils_pc/<outil>.py` (ex. `sniffeur_modbus.py
  --port auto --debit 19200 --http 7300`).

## Logs Berry — la charte (decidee le 2026-10-04)

A appliquer a **tout** log ecrit dans un `.be` de ce depot. Le mecanisme vit dans
`data/fs/logFonctions.be` (qui porte la meme charte en tete) ; la reference utilisateur
est dans `outils_docs/README.md`.

### Les 4 niveaux : quand utiliser lequel

| Mot (commandes, persist) | Constante | Pour quoi |
|---|---|---|
| `erreur` | `LOG_LEVEL_ERREUR` (1) | Un echec qui demande d'agir : exception, trame rejetee, abandon apres N tentatives, fichier absent. **Toujours emis**, quel que soit le seuil du module. |
| `info` | `LOG_LEVEL_INFO` (2) | Un evenement metier ou un changement d'etat, **une ligne par evenement** : relais commute, esclave connecte, configuration appliquee. Ce qu'on lit en fonctionnement normal. |
| `debug` | `LOG_LEVEL_DEBUG` (3) | Le deroule d'un traitement : etapes, decisions, valeurs cles. Pour suivre un module en mise au point. |
| `detail` | `LOG_LEVEL_DEBUG_PLUS` (4) | Le brut : trames, JSON complets, parametres recus par une commande, iterations de boucle. Emis au niveau **3** du firmware, jamais 4 : pas de melange avec les `BRY: GC`. |

### Les regles d'ecriture

1. **Toujours `logFonctions.log(msg, niveau [, cible])`, jamais `log()` direct.** Un `log()` direct
   contourne le seuil du module, et un `detail` sortirait au niveau 4 du firmware.
   Sans `cible`, le message depend du seuil `general`.
2. Prefixe `NOM_MAJ_SNAKE: Message en francais !`, suffixe `_ERREUR` dans les `except`.
3. Un echec se logue en `erreur`, jamais en `debug` « pour ne pas encombrer » : les erreurs
   sont la seule chose qu'on doit pouvoir retrouver une fois le debug eteint.
4. Dans un callback frequent (`every_50ms`, `every_second`, reception reseau ou serie) :
   pas d'`info`, seulement `debug` ou `detail`.
5. Un message couteux a construire (`json.dump`, gros `format`) se garde par
   `if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, cible) ... end` : Berry construit la chaine
   **avant** d'appeler `log()`, meme si elle est ensuite jetee.

### Les deux filtres successifs

Un message n'apparait sur une sortie que s'il passe **les deux** :

1. **Le seuil de son module** (sa `cible`) : cle `"log"` du bloc du module dans `_persist.json`
   (`diverses.logs.general` pour `general`). Regle par `ReglageLog <cible> <niveau>`, ou pour
   toutes les cibles de la carte d'un coup par `ReglageLog tous <niveau>`.
2. **Le seuil de la sortie** (`serie`, `web`, `mqtt`, `syslog`), donne par le **profil actif** :
   `diverses.logs.profil` et `diverses.logs.profils`. Regle par `ReglageLog profil <nom>`.

Exemple : voir le `detail` ModBus en console demande `ReglageLog modbus detail` **et** une
sortie `serie` a `debug` au moins. Une sortie a `detail` (niveau 4 du firmware) affiche aussi
les `BRY: GC` : c'est l'outil de mesure de la RAM.

**`ReglageLog` est la seule commande qui regle les logs.** Les anciens parametres
(`logActivation`, `ReglageGlobal logLevel`) sont supprimes : ne pas les reintroduire.

## Journal des lecons

`tasks/lessons.md` — voir la section « AU DEMARRAGE DE CHAQUE SESSION » en tete de ce
fichier. A lire en entier avant de toucher au code, a completer apres chaque correction.

## Demandes recurrentes : les outils qui les automatisent (2026-10-18)

Issus de l'audit des conversations du 2026-10-17. Les utiliser plutot que refaire a la main.

- **Commit** : `/commite` (`pousse` en argument pour pousser). Porte les regles de la section « Commits ».
- **Fin de conversation, passation** : `/fin-de-session` (reprise, lecons, memoire, mini-export lu
  par `/reprise-session`). Apres un compactage, un hook le rappelle.
- **Logs des cartes** : skill `logs-cartes` (journal syslog, pages :7200/:7100/:7000/:7600, filtres).
- **Builds** : le hook `garde_build` refuse tout `pio run` pendant un build deja en cours. Un refus
  n'est pas une panne : attendre la fin du build ou lancer l'outil hors PlatformIO.
- **Berry** : chaque `.be` de `data/` edite par Claude est compile aussitot (hook `verifie_berry_edition`) ;
  apres modification, skill `bancs` pour le banc a lancer ; avant commit, agent `relecteur-berry`.
- **Diagnostic** : devant un bug, une erreur ou un comportement inattendu, invoquer
  `superpowers:systematic-debugging` **avant** de proposer une correction (154 demandes de correction
  pour 5 usages mesures).
- **Plans** (2026-10-18) : question complexe -> mode plan + agents. Plan ecrit au format
  `tasks/plans/_FORMAT.md` (`## A<n> — titre` + sous-etapes `- [ ]`), recopie dans `tasks/plans/` a la
  validation par le mod `suivi-plan`, affiche a droite par l'extension. Cocher une etape seulement apres
  verification, avec `— preuve : …`. Commande `/suivi` (`/plan` est une commande integree).

## Carte des documents de ce depot

Pour ne pas chercher : ce qui a ete produit et ou.

- `CLAUDE.md` (ce fichier) — regles du depot, synchro du fork, montage d'un nouveau poste,
  PermissionError.
- `.claude/hooks/verifie_synchro_fork.sh` — hook `SessionStart` : signale le retard du fork
  sur l'amont (detecteur seul, ne synchronise pas). Declare dans `.claude/settings.json`.
- `.claude/hooks/garde_build.sh` + `garde_build.py` — hook `PreToolUse` (Bash, PowerShell) : refuse un
  `pio run` si un `platformio run` ou un `scons` tourne (`pio home` ignore). Filtre `if` : ne se lance
  que si la commande contient `pio`/`platformio`.
- `.claude/hooks/rappel_apres_compactage.sh` — hook `SessionStart` (`compact`) : rappelle de mettre
  a jour la reprise.
- `.claude/hooks/verifie_berry_edition.sh` + `.py` — hook `PostToolUse` (Edit, Write, MultiEdit) : apres
  chaque edition d'un `data/**/*.be` par Claude (hors `*sauvegarde*`), `verifie_berry.py <fichier>` (~0,8 s) ;
  erreur Berry ou verification impossible -> code 2, l'erreur revient a Claude. Filtre `sh` : rien n'est lance
  pour un autre fichier. Banc hors depot (faux depot + temoin verificateur absent).
- `.claude/skills/bancs/` — skill : quel banc lancer pour quel fichier modifie, commande exacte (Python de
  PlatformIO pour `outils_pc/`, pyserial), lecture vert/rouge, pieges (bancs Berry sans code de sortie,
  `test_rs485_pc.py` n'est pas un banc, `--reel` = reseau).
- `.claude/agents/relecteur-berry.md` — sous-agent de relecture des `.be` modifies avant commit : syntaxe,
  charte des logs, RAM, regles du depot, bancs Berry lances. Ne modifie rien.
- `.claude/commands/commite.md`, `.claude/commands/fin-de-session.md` — commandes `/commite`,
  `/fin-de-session` ; `.claude/skills/logs-cartes/` — skill de lecture des logs.
- `tasks/export-session-*.md` — mini-exports de passation ecrits par `/fin-de-session`.
- `.claude/mods/` — marketplace locale `mods-tasmota` ; mod `meteo-contexte` : UNE barre coloree de
  remplissage du contexte et cout de la session, au-dessus du prompt (terminal, et panneau VS Code 2.1.301 :
  la bande y est dessinee, contrairement a la doc ; a defaut, ligne de statut + pane). Au-dela de 45 %, le
  bouton « Preparer la passation » (`/fin-de-session`) est **toujours** visible ; toast unique. Sans processus
  ni reseau. Banc hors depot (hote simule). Modifier le mod = monter `version` dans `plugin.json`, puis
  `claude.cmd plugin marketplace update mods-tasmota` et `claude.cmd plugin update meteo-contexte@mods-tasmota`.
  Installation : `/plugin marketplace add <depot>/.claude/mods` puis `/plugin install meteo-contexte@mods-tasmota`.
- `.claude/mods/suivi-plan/` — mod : recopie le plan valide (ExitPlanMode) dans `tasks/plans/`, ligne
  d'avancement (`$.ui.status`), resume du plan actif injecte a chaque conversation, `/suivi`, fichier signal
  `%USERPROFILE%\.claude\suivi-plan\signal.json` qui ouvre la vue. Parseur partage avec l'extension :
  `hooks/parseur-plan.mjs` (banc `node .claude/mods/suivi-plan/tests/test_parseur.mjs`, avec mutants).
  Plan PAR CONVERSATION (0.2.0, 2026-10-18) : rattache par ExitPlanMode, edition d'un plan, `/suivi ouvrir`,
  `/suivi suivre <chantier>` ; `/suivi detacher` le lache. Ecrit `...\suivi-plan\conversations\<session>.json`,
  et a chaque message un signal `ouvrir: false` (ecrit AVANT le traitement du message). Depuis 0.3.0, la
  ligne d'avancement et le bloc injecte montrent d'abord le plan de la conversation.
  Banc : `claude.cmd plugin test .claude/mods/suivi-plan`.
- `outils_docs/vscode/suivi-plan/` — extension VS Code `fdaubercy.suivi-plan` : vue du plan a droite (%
  par action, ameliorations restantes), barre d'etat. Installation : `maintenance/installe_suivi_plan.py`.
  Suit l'onglet de conversation Claude actif (`conversations.js` : libelle d'onglet = titre du transcript
  tronque comme l'extension Claude 2.1.301 ; banc `test_conversations.js`) ; journal « Suivi du plan »
  (panneau Sortie) : une ligne par bascule. Libelles en collision : les conversations NON rattachees des
  30 derniers jours comptent (ambiguite affichee, pas de plan devine) ; un message envoye depuis un onglet
  lui apprend sa conversation ; un signal d'une autre conversation que l'onglet actif est ignore.
  Panneau Claude en barre laterale : aucune API ne dit quelle conversation y est affichee -> seuls le
  signal « message envoye » et la ligne d'avancement de la conversation le couvrent.
- `tasks/plans/` — un plan suivi par chantier ; format et regles de calcul dans `_FORMAT.md`.
- `tasks/lessons.md` — journal des erreurs et regles.
- `tasks/reprise-solidification-berry.md` — etat du chantier solidification, prochaine action.
- `tasks/reprise-chantier-modbus-grenier.md` — etat du chantier ModBus (carte 16 relais +
  esclaves), decisions tranchees, plan en phases. ⚠️ Nom trompeur : **cibles = les 3 modules
  garage**, le grenier est en sommeil. Travail sur `development` (branche de chantier supprimee
  le 2026-10-04).
- Graphiques des cartes S3/P4 (2026-10-18) : page `/graphiques` (bouton d'accueil) servie par
  `data/fs/graphiquesFonctions.be` (route et bouton declares par le driver `HISTORIQUE_WEB` de
  `historiqueFonctions.be`), gabarit `data/sd/html/graphiques.html` + `data/sd/css/graphiques.css`, logique
  `data/sd/js/graphiques.js` (+ `graphiques_trace.js` : trace ECharts d'un graphique, `graphiques_edition.js` : mode
  edition ; page COMPOSABLE (A9) : composition enregistree par `POST /graphiques` dans la cle `graphiques` de
  `/json/graphiques.json`, `graphiquesFonctions.enregistre`/`valideComposition`), ECharts 6 COMPRESSE `data/sd/js/echarts.min.js.gz` (Berry ne pose pas Content-Encoding :
  la page le decompresse, cache localStorage versionne) ; temps reel par `/histo?p=direct` (cadence de la liste
  « Direct » de la page, 10 s par defaut) ; series DECOUVERTES dans le JSON SENSOR
  par `data/fs/historiqueSeries.be` (ni relais, ni entrees, ni volets, ni internes ; persist : `exclues`, `ajouts`,
  `compteurs`) ; reglages de la page (`affichage`, `groupes`, `rafraichissement`, `direct`) dans `data/<lieu>/<carte>/graphiques.json` -> `/json/`,
  HORS persist (le persist est en RAM en permanence) ; `diverses.historique.grafana` reste au persist ; sans historique actif, la cle `.grafana` donne un bouton
  « Historique (Grafana) » sur l'accueil (`controleWeb.boutonGrafana`, solidifie, toutes les cartes). Mode d'emploi : `outils_docs/README.md` § « Les graphiques
  des mesures » ; banc `berry/banc_graphiques.py` (+ `.be`, `banc_historique.be`, `bouchons_berry/graphiques/` et `historique/`) ; plan `tasks/plans/graphiques-web.md`.
- `outils_docs/SOLIDIFICATION_BERRY.md` — mecanisme, verification (§5), parametres, 11 pieges.
- `outils_docs/PROTOCOLE_MODBUS.md` — ModBus RTU/TCP standard, implementation maison (3 transports
  Serie/UDP/TCP), extension esclave->maitre, failles du mecanisme d'envoi, design de queue FIFO,
  carte des registres de la carte 16 relais (§8), architecture de synchronisation (§9).
- `outils_docs/ANALYSE_BERRY_MODBUS_DISCOVERY.md` — fonctionnement des programmes ModBus
  Berry (3 transports, carte 16 relais, ESP32<->ESP32, push esclave->maitre) + audit de la
  table `/json/discovery.json` : formes ecrites/lues, 3 defauts bloquants la resolution
  d'IP en UDP, et tableau des elements restant a parametrer (importance/priorite/difficulte).
  §2.6 : cycle `forceEnvoiParams` -> `ImAlive` (presentation esclave -> maitre, usages de la
  table cote maitre, piege de la carte reaffectee) ; resume en tete de `data/fs/udpFonctions.be`.
- `outils_docs/DIAGNOSTIC_UDP_2026-10-17.md` — diagnostic UDP maitre <-> esclave (Range Extender /
  Wi-Fi classique) : matrice attendue, cause prouvee (AP de l'esclave en 192.168.4.1/24 -> ses envois
  vers le maitre partent par son AP), corrections C1-C7, plan des essais. Resume dans
  `PROTOCOLE_MODBUS.md` §9 (avec les resultats des essais). C1 a C6 appliques et valides sur les cartes le
  2026-10-17, dans les deux modes ; multicast du maitre par la box seulement si un esclave y est decouvert.
  `tasks/correctif-udp-interface-2026-10-17.diff` est historique : la reference est `data/fs/udpFonctions.be`.
- `outils_docs/AUDIT_MODBUS_2026-09-29.md` — audit complet ModBus garage (B1 corrige, secrets
  en clair sur depot public, defauts G1-G8 actifs, L1-L13 latents, ameliorations par priorite).
- `outils_docs/Electronique/Connecteur ModBus/` — docs constructeur de la carte 16 relais
  (`... commamd.docx` = jeu de commandes, `... Manual.docx` = caracteristiques).
- `docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md` — verdict Q1/Q2/Q3.
- `outils_docs/scripts_python/`, range par usage le 2026-10-12. **Des scripts qui s'importent
  entre eux restent dans le MEME dossier** (import d'un module voisin) : ne pas les separer.
  - `build/` — charges par PlatformIO : `pre_utilitaires_platformio.py` (pre-script ; importe les
    `cible_*.py` voisins), `post_lto_parallele.py`, les 7 `cible_*.py` (cibles Custom, qui lancent
    `outils_pc/`), `ota-files-uploader.py`, `update_idf55_framework.py` (appele par le pre-script).
  - `berry/` — `verifie_berry.py` (syntaxe de data/, tache VS Code de surveillance),
    `solidifie_et_compile_berry.py` (module solidifiable en ~10 s, compile le .h),
    `nomme_fonctions_berry.py` (fonctions anonymes -> nommees), `carte_modules_berry.py`
    (-> `outils_docs/CARTE_MODULES_BERRY.md`), `genere_schema_persist.py`
    (-> `outils_docs/schemas/persist.schema.json`), `gen_tapp.py`, et les bancs
    `banc_test_modbus.{py,be}`, `banc_leds.{py,be}` (ruban AUTO/MANUEL, bouton, LED du dev-kit),
    `banc_veille_drivers.be` (veille des drivers inactifs sur LittleFS neuf, `bouchons_berry/veille/`),
    `banc_boot.{py,be}` (autoexec ENTIER du P4 sur faux firmware `bouchons_berry/boot/` : persist reel, `{}`,
    sans `serveur.wifi`, ES8311 absent, telemetrie sans COUNTER ; timers de reboot P5.1 ; defaut connu MAC en `CONNU`, B1, B2, B3 et ES8311 corriges),
    `test_discovery.be` avec leurs `bouchons_berry/` (`bouchons_berry/leds/` : bouchon de
    `ledsFonctions`, ajoute par le seul banc ModBus ; dans `bouchons_berry/`, il masquerait le vrai
    module a `banc_leds`).
  - `maintenance/` — `synchronise_fork_tasmota.py` (synchro du fork : merge, jamais de force-push),
    `synchronise_upstream_tasmota.py` (variante rebase), `corrige_reglages_vscode.py` (pose et
    prouve les reglages VS Code du PermissionError). Page web de la synchro : `synchro_fork_web.py`
    (serveur, port 7500) + `synchro_fork_session.py` (script lance en processus enfant, questions),
    `synchro_fork_etat.py` (bandeau, diff, journal), `synchro_fork_page.py`, `synchro_fork_question.py`
    (importe par les deux scripts) ; banc `test_synchro_fork_web.py` (`--reel` : vrais scripts en
    --dry-run) ; cible `build/cible_synchro_fork.py`. **Seule exception a la regle du meme dossier** :
    `synchro_fork_web.py` importe `outils_pc/acces_web.py` par un `sys.path` explicite.
  - `sauvegarde/` — `genere_sauvegarde_tasmota.py`, `restaure_sauvegarde_tasmota.py` et leur
    interface Tk `interface_sauvegarde_restauration_tasmota.py`.
  - `reseau/` — petits outils autonomes : `comm_udp_*.py`, `envoi_message_udp.py`,
    `simple-server.py`, `multi_server_explorer.py`, `image_base64.py`.
  - `outils_pc/` — les outils PC autour des cartes, qui s'importent entre eux (`ecoute_udp.py`
    importe le sniffeur MQTT ; le sniffeur ModBus, 7 modules voisins) : `pont_serie.py`
    (+ `pont_serie_web.py`) et ceux-ci :
  - `acces_web.py` (banc `test_acces_web.py`) — commun aux pages des outils (pont serie, testeur UDP,
    sniffeurs MQTT et ModBus, syslog, synchro du fork), decide le 2026-10-17 : au lancement, lien
    cliquable dans la console (Ctrl+clic) et navigateur ouvert (`--sans-navigateur` pour l'eviter) ;
    ecoute sur tout le reseau (`--local` = 127.0.0.1 seulement). **Depuis ce PC : sans jeton**,
    protection d'avant (en-tete `X-...` + origine 127.0.0.1/localhost). **Depuis un autre appareil :
    jeton obligatoire**, tire a chaque lancement, dans le lien « depuis un autre appareil du reseau »
    de la console ; pose en cookie HttpOnly SameSite=Strict (un nom par port) puis retire de l'URL.
    Le flux TCP brut du pont serie reste reserve a ce PC. Pare-feu Windows : autoriser Python sur
    les reseaux prives au premier lancement, sinon les autres appareils n'atteignent pas la page.
    Ecrit aussi la fiche de presence de l'outil (`%LOCALAPPDATA%\outils_tasmota\presence\`), lue par l'annuaire.
  - `test_rs485_pc.py` — test du bus ModBus depuis le PC par un convertisseur USB-RS485
    (Waveshare CH343) : ecoute du bus, envoi brut, lecture/commande de la carte 16 relais,
    recherche de son debit, emulation de la carte (pour tester le maitre P4 sans elle).
  - `sniffeur_modbus.py` (+ `sniffeur_modbus_web.py`, `sniffeur_modbus_aide.py`, `decodeur_modbus.py`,
    `cible_sniffeur_modbus.py`) — meme convertisseur, page http://127.0.0.1:7300 : trames du bus en direct,
    appariement requete/reponse (latence, sans reponse, exceptions par esclave), envoi et raccourcis carte
    16 relais, emulation de la carte. `decodeur_modbus.py` decode chaque trame selon la norme (champ par
    champ, clic sur la trame) puis selon le dialecte de l'esclave vise : carte 16 relais (Conn16channels)
    ou ESP32 (TasmotaSlaveModBus : registre = code GPIO Tasmota + idModBus - 1), d'apres le persist du
    maitre P4. Onglet Aide : regles de formation des trames, registres de l'installation, decodeur manuel
    (accepte une ligne `ModbusPushUDP <seq> <hexa>`). Modules : `sniffeur_modbus_http.py` (routes),
    `surveillance_modbus.py` (ecart commande/releve d'un relais, collisions -> alertes dans le fil),
    `emulation_modbus.py` (le PC repond a la place de la carte relais, de la cuve, du rideau ; valeurs
    editables dans la page ; temperature et analogiques peuvent onduler : ± ecart, periode en min), `debit_modbus.py` (trouve puis corrige, sur confirmation, le debit et
    l'adresse de la carte relais, comme `verifieConn16`), `ecoute_udp.py` (rejoint 224.3.0.1:4000 en
    ecoute seule : push `ModbusPushUDP` des esclaves decodes et juges comme `accepteSeq` du maitre ;
    s'abonne aussi a `tele/+/MODBUSPUSH`, ou le maitre recopie les push qu'il recoit si
    `ReglageModbus RelaisPushMQTT ON` : les esclaves sont derriere son point d'acces NAPT, leur
    multicast n'atteint jamais le PC sur le Wi-Fi maison).
    Echo local du convertisseur appris au 1er envoi (`--echo auto`) : un accuse 0x05/0x06 est la copie
    exacte de la requete, il ne doit pas etre jete. Port ouvert sans DTR/RTS (pas de reset d'un ESP32).
    Banc : `test_sniffeur_modbus.py` (code de sortie 0 = vert ; persist de test ; UDP sur un groupe et un
    port de test en TTL 0 - ne JAMAIS emettre de faux push vers 224.3.0.1:4000, le vrai maitre le traiterait). Cible PlatformIO « Sniffeur ModBus » dans Custom
    (port : `custom_sniffeur_modbus_port`, defaut auto = le seul CH343 present).
  - `sniffeur_mqtt.py` (+ `sniffeur_mqtt_web.py`, `sniffeur_mqtt_panneaux.py`, `sniffeur_mqtt_config.py`,
    `client_mqtt.py`, `cible_sniffeur_mqtt.py`) — sniffeur / publieur MQTT sur http://127.0.0.1:7100 :
    plusieurs brokers parametrables (TLS possible) et selectionnables, abonnements gerables un par
    un et memorises par broker, filtre d'affichage + favoris, differences avec le message precedent
    du meme topic, export .txt/.json, publication (retenu ou non). Panneaux : audit discovery,
    connexions LWT, logs par carte (`stat/<topic>/LOGGING`, sans occuper les ports serie), commande
    Tasmota avec sa reponse, arborescence des topics. Broker par defaut lu dans
    `user_config_override.h` ; les autres (mots de passe compris) dans
    `%APPDATA%\sniffeur_mqtt\config.json`, HORS depot. Cible PlatformIO « Sniffeur MQTT » dans Custom.
  - `syslog_tasmota.py` (+ `syslog_tasmota_web.py`, `cible_syslog_tasmota.py`) — serveur syslog :
    ecoute UDP 514, page http://127.0.0.1:7200 (filtre module / severite / texte), journal
    `%TEMP%/syslog_tasmota.log`. Cible PlatformIO « Serveur syslog » dans Custom. Les modules
    envoient a `SYS_LOG_HOST` (`user_config_override.h`) = **192.168.0.3, ce PC** (le NAS
    192.168.0.2 est eteint) : IP a figer par un bail DHCP fixe sur la box.
  - `testeur_udp.py` (+ `testeur_udp_carte.py`, `testeur_udp_essais.py`, `testeur_udp_http.py`,
    `testeur_udp_web.py`, `testeur_udp_aide.py`, `testeur_udp_grille.py`, `testeur_udp_grille_web.py`,
    `build/cible_testeur_udp.py`) — page
    http://127.0.0.1:7400 pour tester l'UDP maitre <-> esclave : ouvre les 2 ports serie (maitre et
    esclave, reglables dans la page), envoie texte libre / trames `ModbusUDP` (E1) / push / `ImAlive`
    en unicast ou multicast et juge chaque essai (RECU, EMIS NON RECU, NON EMIS...). Bascule le mode
    de l'esclave par `ReglageGlobal ModeConnexion RangeExtender|WifiClassique <ssid> <mdp>` (Wi-Fi lu
    dans le persist du maitre du depot ; l'esclave memorise ses reseaux d'origine et redemarre).
    Pose les logs `udp`/`modbus` le temps des essais puis les restaure. Chaque carte se branche soit sur
    son port COM, soit par le pont serie (`pont:7000`, TCP brut ; avertit si le pont n'est pas demarre ;
    redemande au pont un port perdu, jamais apres « Arreter »). Onglet « Grille ModBus » : les 7 tests de
    la grille de `AUDIT_MODBUS_2026-09-29.md` §6 pour UN esclave (ID/Power/registre lus dans le persist du
    maitre, defaut cuve), juges sur les logs des deux cartes, consignes a valider dans la page ; pose
    aussi `slaveModbus`/`conn16channels` en debug sur le maitre. Onglet Aide. Cible PlatformIO
    « Testeur UDP maitre/esclave » dans Custom, et tache VS Code (Ctrl+Maj+P > Run Task). Banc :
    `test_testeur_udp.py` (cartes simulees par `testeur_udp_sim.py` ; groupe « pont » dans
    `test_testeur_udp_pont.py`, sur le vrai `pont_serie.py` en loop:// ; groupe « muette » dans
    `test_testeur_udp_muette.py` : carte qui ne repond plus sur son port ; groupe « grille » dans
    `test_testeur_udp_grille.py`, avec pannes simulees ; code de sortie 0 = vert).
  - `annuaire_outils.py` (+ `annuaire_registre.py`, `annuaire_presence.py`, `annuaire_lanceur.py`,
    `annuaire_page.py`) — annuaire des outils PC, page http://127.0.0.1:7600 : liste les outils (fiches de
    presence sous `%LOCALAPPDATA%\outils_tasmota\`, consoles dans `consoles\<id>.log`), les lance et les arrete.
    Demarre seul avec VS Code (tache « Outil : annuaire des outils », `runOn: folderOpen`) et ouvre sa page dans
    le navigateur a chaque ouverture de VS Code (decide le 2026-10-17 ; deja demarre -> ouvre seulement la page).
    Aussi cible Custom « Annuaire des outils (page web) » (`build/cible_annuaire.py`, `pio run` : jamais pendant
    un build) : si l'annuaire tourne deja, ouvre seulement sa page ; sinon le demarre (il s'arrete alors avec la cible).
    Les outils lances depuis l'annuaire s'arretent avec lui (job object Windows), SAUF la synchro du fork
    (hors job, console cachee propre, survit a la fermeture de VS Code ; arret refuse pendant un merge, rebase
    ou push ; synchro muette : refus si MERGE_HEAD ou rebase en cours dans `.git`). Tuile « liee a
    l'annuaire » si Windows a refuse de detacher la synchro. Client de ce PC : Host 127.0.0.1/localhost/[::1]
    exige (DNS rebinding). Autre appareil : lien a jeton de la console / de la page sur le PC. Bancs :
    `test_annuaire.py`, `test_annuaire_lanceur.py`, `test_annuaire_securite.py`.
    Spec : `docs/superpowers/specs/2026-10-17-annuaire-outils-design.md`.
