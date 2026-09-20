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
   **Branche `chantier-modbus-grenier`**, jamais poussee.
3. **`tasks/reprise-solidification-berry.md`** — l'autre chantier (solidification Berry),
   sa prochaine action et ses questions ouvertes.
4. **`outils_docs/SOLIDIFICATION_BERRY.md`** — le mecanisme complet + 11 pieges, a lire
   des que le sujet Berry/solidification arrive.
5. **`outils_docs/PROTOCOLE_MODBUS.md`** — a lire des que le sujet ModBus arrive : carte
   des registres de la carte 16 relais (§8) et architecture de synchronisation (§9).

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
  avant de pousser (`input()`, ligne 434). Dans un hook, l'entree standard n'est pas
  un terminal -> `EOFError` **apres** le merge ;
- contre les conflits, la vraie prevention est la **frequence** — petits paquets, sur
  `development` propre, **avant** d'ouvrir un chantier — pas l'automatisme.

### Que faire quand le hook signale du retard

Basculer sur `development` avec un arbre propre, puis lancer la synchro a la main,
sortie sous les yeux ; lire le rapport et confirmer (ou non) le push :

```
python outils_docs/scripts_python/synchronise_fork_tasmota.py
```

`--dry-run` pour un diagnostic seul, qui ne modifie rien. **Ne jamais merger l'amont
dans une branche de chantier** : le hook le rappelle en affichant la branche courante.

## Exception assumee a la regle des 500 lignes

`outils_docs/scripts_python/synchronise_fork_tasmota.py` fait **527 lignes**, et
c'est **voulu** (decide le 2026-07-15). Ne pas le decouper pour satisfaire le
compteur.

Decomposition reelle : 333 lignes de code, 57 d'en-tete docstring (qui **est** la
sortie de `--help`), 99 vides, 38 de commentaires. La plus grosse fonction fait
79 lignes. L'esprit de la regle — un fichier qui n'en fait pas trop — est respecte ;
seul le total brut deborde, de 27 lignes de documentation.

Extraire un module d'utilitaires partages avec `synchronise_upstream_tasmota.py`
reste possible **le jour ou un troisieme script apparaitra**, pas avant.

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
python outils_docs/scripts_python/corrige_reglages_vscode.py --verifier
```

Settings Sync **apporte** les reglages mais ne dit jamais **pourquoi** ils existent, et
n'alertera pas si `exclusionPolicy` saute. Ce script, lui, diagnostique (`--etat`),
applique si besoin, et **prouve** que l'exclusion agit (temoin/cible sur l'indexeur).

Il est idempotent, sauvegarde avant d'ecrire, et refuse de fusionner a l'aveugle dans un
`C_Cpp.files.exclude` existant. A lancer si le symptome ci-dessous reapparait.

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
- Pour surveiller un build en redirigeant la sortie, poser `PYTHONIOENCODING=utf-8` :
  sinon Python passe en cp1252, le `✔` du script pre-build tue le thread de recopie de pio,
  et **toute** la sortie est perdue. Ne pas « corriger » le script de l'utilisateur pour ca.

## Journal des lecons

`tasks/lessons.md` — voir la section « AU DEMARRAGE DE CHAQUE SESSION » en tete de ce
fichier. A lire en entier avant de toucher au code, a completer apres chaque correction.

## Carte des documents de ce depot

Pour ne pas chercher : ce qui a ete produit et ou.

- `CLAUDE.md` (ce fichier) — regles du depot, synchro du fork, montage d'un nouveau poste,
  PermissionError.
- `.claude/hooks/verifie_synchro_fork.sh` — hook `SessionStart` : signale le retard du fork
  sur l'amont (detecteur seul, ne synchronise pas). Declare dans `.claude/settings.json`.
- `tasks/lessons.md` — journal des erreurs et regles.
- `tasks/reprise-solidification-berry.md` — etat du chantier solidification, prochaine action.
- `tasks/reprise-chantier-modbus-grenier.md` — etat du chantier ModBus (carte 16 relais +
  esclaves), decisions tranchees, plan en phases. ⚠️ Nom trompeur : **cibles = les 3 modules
  garage**, le grenier est en sommeil. Branche `chantier-modbus-grenier`.
- `outils_docs/SOLIDIFICATION_BERRY.md` — mecanisme, verification (§5), parametres, 11 pieges.
- `outils_docs/PROTOCOLE_MODBUS.md` — ModBus RTU/TCP standard, implementation maison (3 transports
  Serie/UDP/TCP), extension esclave->maitre, failles du mecanisme d'envoi, design de queue FIFO,
  carte des registres de la carte 16 relais (§8), architecture de synchronisation (§9).
- `outils_docs/Electronique/Connecteur ModBus/` — docs constructeur de la carte 16 relais
  (`... commamd.docx` = jeu de commandes, `... Manual.docx` = caracteristiques).
- `docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md` — verdict Q1/Q2/Q3.
- `outils_docs/scripts_python/` :
  - `synchronise_fork_tasmota.py` — synchro du fork (merge, jamais de force-push).
  - `solidifie_et_compile_berry.py` — verifie qu'un module est solidifiable en ~10 s (compile le .h).
  - `nomme_fonctions_berry.py` — convertit les fonctions anonymes d'un module.
  - `corrige_reglages_vscode.py` — pose et prouve les reglages VS Code (PermissionError).
