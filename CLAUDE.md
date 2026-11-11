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
4. **`outils_docs/SOLIDIFICATION_BERRY.md`** — le mecanisme complet + 13 pieges, a lire
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
Depuis le 2026-10-27, apres un « Diagnostic seul » reussi, la page affiche un **assistant pas a pas**
(etapes calculees sur le depot local) : voie A = le script de merge, voie B = merge local guide
fichier par fichier si conflit prevu ou commits non pousses. Jamais de rebase, stash, reset ni push
force ; le rebase est replie dans « Avance ». Mode d'emploi : `outils_docs/README.md` § « Synchro du fork
(page web) ».

## Exception assumee a la regle des 500 lignes

`outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py` fait **560 lignes**, et
c'est **voulu** (decide le 2026-07-15, a 527 lignes ; +7 le 2026-10-12 pour le correctif
du blocage sur son propre journal ; +24 le 2026-10-17 pour la confirmation et le
controle d'arbre propre AVANT la synchro distante, et les questions de la page web ; +2 le
2026-10-27 pour le journal ecrit par l'assistant de la page web, `noter_historique(historique=)`).
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

`data/fs/energieFonctions.be` fait **598 lignes**, et c'est **voulu** (decide le 2026-11-09 : exception plutot
qu'un decoupage ; 531 lignes avant le palier 4 de l'atelier, +57 pour les routes de lecture `f=description`, `f=mois`,
`f=direct`, +10 pour le relais par morceaux). Module SOLIDIFIE du differentiel (sans PSRAM) : comptage, stockage et
routes de la page `/energie` restent ensemble (spec `2026-11-08-atelier-energie-differentiel-design.md` §6.3) ; un
second module solidifie ajouterait une entree de `custom_berry_solidify` et de l'autoexec pour rien.

`outils_docs/scripts_python/outils_pc/build_page.py` fait **1226 lignes**, et c'est **voulu**
(decide le 2026-10-24 a 788 lignes : exception acceptee plutot qu'un decoupage CSS/JS ; 813 apres la
vague de corrections finale du meme jour ; 935 le 2026-10-25 avec le panneau « Sortie » et « Effacer puis
televerser » ; 1038 le meme jour avec la pause « rebranchez la carte » et les panneaux refermes ; 1053 avec
l'envoi sans recompiler apres la pause et la pause rouverte ; 1062 avec le lien « fichiers » vers la page
Fichiers Berry par env ; 1083 le 2026-10-26 avec les cases FS grisees quand l'envoi serie du firmware ecrit
deja le FS ; 1131 le meme jour avec les sons de fin de lancement et de pause ; 1153 le 2026-10-29 avec le
branchement de l'onglet « Fichiers », dont le code vit dans `build_page_fichiers.py` ; 1154 le 2026-10-31 avec
les durees en heures au-dela de 60 min ; 1162 le 2026-11-01 avec le branchement de l'onglet « Mémoire et partitions », dont
le code vit dans `build_page_memoire.py` ; 1169 le meme jour avec le branchement de l'onglet « Env par défaut (Platformio override) », dont le
code vit dans `build_page_defaut.py` ; 1206 le meme jour avec le bouton de purge du cache et le resume memoire de chaque env ; 1210 le 2026-11-02 avec les couleurs du panneau « Sortie », dont le code vit dans `build_page_couleurs.py` ; 1215 le meme jour avec le branchement de l'onglet « Aide », dont le texte vit dans `build_page_aide.py` ; 1223 le 2026-11-03 avec le branchement de l'onglet « Sauvegarde configuration », dont le code vit dans `build_page_sauvegarde.py` ; 1223 encore le 2026-11-10 avec le branchement de la bascule « Classer par », dont le code vit dans `build_page_lieux.py` (qui reprend aussi la memoire d'ouverture de `chargeEnvs`) ; 1226 le 2026-11-11 avec le branchement de `lieux.JS`, commun aux listes de cartes). C'est la page
unique de l'outil « Build et televersement » (HTML + CSS + JS dans une seule constante
servie par `build_web.py`) : ne pas la decouper pour satisfaire le compteur.

Meme outil, meme decision (2026-10-25, exception acceptee par l'utilisateur plutot qu'un decoupage) :
`build_serie.py` fait **816 lignes** (+9 le 2026-11-03 : sauvegarde « avant flash » de la configuration ; +18 le 2026-11-02 : sauvegarde et retablissement de `/.drvset003` autour d'un flash serie ; +14 le 2026-11-01 : table de partitions de l'env ; +19 le 2026-10-25 : total estime d'un env jamais compile ; +17 le 2026-10-26 : arret de pio sur solidification vide ; +8 le meme jour : FS fait par l'envoi serie du firmware ; +11 le 2026-10-27 : data_dir pose avant pio ; +3 le meme jour : identite de l'image du FS ; +7 le meme jour : duree des zones d'envoi memorisee, A13 ; +6 le 2026-10-28 : OTA par le maitre, A11 ; +9 le meme jour : Sleep 0 du maitre pendant l'envoi ; +30 le 2026-10-29 : action « fichiers » de l'onglet Fichiers ; +16 le meme jour : transport MQTT (A16) ; execution en serie des `pio run` : verrous, arret immediat, attente
d'un envoi au Ctrl+C, OTA, pause « rebranchez la carte » ; la couper separerait un etat partage sous le meme
verrou), et ses bancs `test_build_serie.py` (**1215**), `test_build_page_chrome.py` (**1103**),
`test_build_ota_fs.py` (**925**, +78 le 2026-11-09 : place, fichiers identiques, remplacement, A17), `test_build_web.py` (**797**), `test_atelier_graphiques_page_chrome.py` (**740**, sonde de la page de l'atelier, +5 le 2026-11-08 : lien « Envoyer par la page Build » et liste vide,
decision du 2026-11-05), `berry/banc_graphiques.py` (**571**, banc de la page /graphiques, decision du 2026-11-06), ainsi que `test_annuaire.py` (**523**,
banc de l'annuaire) : un banc par module, chaque test lisible seul. Ne pas les decouper pour satisfaire le
compteur.

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

### 5. Exclusions Windows Defender (vitesse des builds)

En PowerShell **administrateur** (le script refuse sinon) :

```
powershell -ExecutionPolicy Bypass -File outils_docs\scripts_python\maintenance\exclusions_defender.ps1
```

Exclut `.pio`, `.cache` et `~/.platformio` de l'analyse en temps reel ; `-Verifier` = lecture seule.

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
quelques millisecondes plus tard (`pioino.py::InoToCPPConverter.process`) — l'indexeur s'en saisit
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

- `tasmota.ino.cpp` portait en ligne 1 un nom de fichier temporaire aleatoire, donc n'etait jamais repris du cache :
  `build/ino_stable.py` rend ce nom fixe (mesure du 2026-11-01 sur la cuve, rien de modifie : 355 s au lieu de 771 s).
- Le pre-script pose `env.Decider("content-timestamp")` et `SetOption("implicit_cache", 1)` : ~20 s au lieu de ~230 s de
  parcours SCons sans rien compiler (mesure du 2026-11-01). Limite d'`implicit_cache` : un NOUVEL en-tete qui en masque un
  autre de meme nom plus loin dans les `-I` n'est vu qu'a la modification d'un fichier de la chaine (banc `build/test_scons_cache.py`).
- `gen-berry-structures` reecrit `lib/libesp32/berry/generate/` APRES le LDF : avec `implicit_cache`, SCons gardait la date lue avant et reprenait du cache un `be_string.c.o` sans les nouveaux textes (`undefined reference to be_const_str_...`, 2026-11-02 ; masque jusque-la par le `CFG_HOLDER` qui changeait a chaque build). Corrige par `clear_memoized_values()` dans `build/post_lto_parallele.py`, banc `build/test_scons_cache.py`.
- `firmware.elf` ne passe pas par le cache objet : repris du cache, il arrive sans `firmware.map`, et
  `pio-tools/name-firmware.py` echoue par `*** [firmware.bin]` sans message. Un retour sur un env refait donc son edition de liens.
- Un build reecrit `platformio_override.ini` (`adapteParametresPlatformio_override`), et
  `tasmota/user_config_override.h` (`increment_config_holder`) **seulement** si ce `.h` (hors ligne `CFG_HOLDER`) a
  change depuis le dernier increment, et pour un `pio run` qui compile le firmware (`build/cfg_holder.py`, decide le
  2026-11-01 ; etat par env dans `%LOCALAPPDATA%\outils_tasmota\build\cfg_holder.json` ; le `_persist.json`
  n'y entre pas, retire a la demande de l'utilisateur). Depuis le soir du 2026-11-01, une carte qui a sa section
  `#elif defined(FIRMWARE_...)` y porte SON `CFG_HOLDER` (lignes `#undef`/`#define` posees par
  `cfg_holder.py::incremente_section`) et n'incremente que si la partie commune du `.h` ou SA section a change : modifier
  la section d'une carte ne recharge plus SECTION1 sur les autres (elles recompilent quand meme, le fichier a change). Avant, `CFG_HOLDER` changeait a chaque run : `tasmota.ino.cpp` et
  tout Berry, soit 175 fichiers sur la cuve, n'etaient jamais repris du cache objet (`.cache`, `build_cache_dir`), car
  `berry_conf.h` inclut `my_user_config.h`. Le pre-script force aussi la
  refabrication de `firmware.bin` (`AlwaysBuild`) : sinon la post-action de `pio-tools/post_esp32.py` ne joindrait plus
  le FS a l'upload serie. Sauvegarder avant une serie de builds experimentaux.
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
  (`platformio/run/helpers.py::clean_build_dir`). L'empreinte inclut la liste des `.c/.h` de `lib/`
  (`project/helpers.py::compute_project_checksum`), or le pre-build regenere les `_temp_be_*.c` de
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
4. Dans un callback frequent (`every_50ms`, `every_100ms`, `every_250ms`, `every_second`, `web_sensor`,
   `json_append`, reception reseau ou serie) : pas d'`info`, seulement `debug` ou `detail`.
5. Un message couteux a construire (`json.dump`, `tohex`, gros `format`) se garde par
   `if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, cible) ... end` : Berry construit la chaine
   **avant** d'appeler `log()`, meme si elle est ensuite jetee. Plusieurs messages dans une meme
   fonction : `var detail = logFonctions.actif(...)` une fois, puis `if detail ... end`.
6. Le niveau s'ecrit par sa constante `LOG_LEVEL_*`, jamais en chiffre (seule exception :
   `data/fs/demarrage.be`, compile avant que les constantes existent). Niveau variable : un enrobeur
   `xxxFonctions.log(msg, niveau)` qui le recoit en parametre, ou une ternaire entre constantes
   (`ok ? LOG_LEVEL_INFO : LOG_LEVEL_ERREUR`).

**Controle automatique** : `verifie_berry.py` (donc le hook `verifie_berry_edition` a chaque edition
d'un `.be` par Claude) signale les ecarts aux regles 1, 2, 4, 5 et 6 en **avertissements**, sans
bloquer ni changer le code de sortie (`berry/charte_logs.py`, ses limites dans sa docstring ;
`--sans-charte` pour la syntaxe seule ; banc `berry/test_verifie_berry_charte.py`).

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
  n'est pas une panne : attendre la fin du build ou lancer l'outil hors PlatformIO. Une cible d'outil
  vivante (annuaire, pont serie... lances par leur cible Custom) n'est pas comptee comme un build.
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

Dans les documents durables (ce fichier, `outils_docs/README.md`, `SOLIDIFICATION_BERRY.md`,
`PROTOCOLE_MODBUS.md`, `CARTE_MODULES_BERRY.md`, `.claude/skills`, `agents`, `commands`), renvoyer au code par
`fichier::fonction`, jamais par numero de ligne : un numero se decale a chaque modification. Controle :
`python outils_docs/scripts_python/maintenance/verifie_references_docs.py` (code 1 = renvoi faux). Les documents
dates (audits, diagnostics, specs, `ANALYSE_*`) gardent leurs numeros : ce sont des traces.

- `CLAUDE.md` (ce fichier) — regles du depot, synchro du fork, montage d'un nouveau poste,
  PermissionError.
- `.claude/hooks/verifie_synchro_fork.sh` — hook `SessionStart` : signale le retard du fork
  sur l'amont (detecteur seul, ne synchronise pas). Declare dans `.claude/settings.json`.
- `.claude/hooks/garde_build.sh` + `garde_build.py` — hook `PreToolUse` (Bash, PowerShell) : refuse un
  `pio run` si un `platformio run` ou un `scons` tourne (`pio home` ignore). Filtre `if` : ne se lance
  que si la commande contient `pio`/`platformio`. Un chemin vers `pio.exe`/`platformio` passe en ARGUMENT
  (enrobeur, script de mesure) compte comme un `pio run` (`garde_build.py::est_pio`, incident du 2026-10-31). Un `pio run` (et son scons) dont TOUTES les cibles sont des
  cibles d'outils (`CIBLES_OUTILS` = les `NOM_CIBLE` des `build/cible_*.py`) n'est PAS un build : l'outil vit
  tant que la cible vit, la page de build l'attendrait sans fin. `__idedata`, une cible melee ou un scons sans
  cible lisible restent des builds ; lancer une cible d'outil pendant un vrai build reste refuse. Une cible
  d'outil qui DEMARRE compte comme un build pendant ses 30 premieres secondes (son demarrage peut purger
  `.pio/build`) : age par `CreationDate` dans la meme requete PowerShell. Banc
  `outils_docs/scripts_python/build/test_garde_build.py` (verifie aussi que la liste = les `NOM_CIBLE`).
- `.claude/hooks/reprise_limite.py` — hook `StopFailure` (`rate_limit`), demande du 2026-11-01 : a la limite
  d'utilisation, demarre une veille detachee qui retente `claude -p --resume <session>` toutes les 15 min (8 jours au
  plus, abandon apres 3 echecs qui ne sont pas des limites), dans le mode de la conversation (jamais bypassPermissions).
  Ne change jamais de compte. Journal `%LOCALAPPDATA%\outils_tasmota\reprise_limite\journal.log` ; banc
  `.claude/hooks/test_reprise_limite.py` (ne prouve pas le declenchement reel).
- `.claude/hooks/rappel_apres_compactage.sh` — hook `SessionStart` (`compact`) : rappelle de mettre
  a jour la reprise.
- `.claude/hooks/verifie_berry_edition.sh` + `.py` — hook `PostToolUse` (Edit, Write, MultiEdit) : apres
  chaque edition d'un `data/**/*.be` par Claude (hors `*sauvegarde*`), `verifie_berry.py <fichier>` (~0,8 s) ;
  erreur Berry ou verification impossible -> code 2, l'erreur revient a Claude ; ecarts a la charte des logs
  seuls -> code 0, avertissements renvoyes en `additionalContext` (audit P7.6). Filtre `sh` : rien n'est lance
  pour un autre fichier. Banc hors depot (faux depot + temoin verificateur absent) ; partie 5 de
  `berry/test_verifie_berry_charte.py` (faux depot : erreur, ecarts, fichier propre).
- `.claude/skills/bancs/` — skill : quel banc lancer pour quel fichier modifie, commande exacte (Python de
  PlatformIO pour `outils_pc/`, pyserial), lecture vert/rouge, pieges (bancs Berry sans code de sortie,
  `test_rs485_pc.py` n'est pas un banc, `--reel` = reseau).
- `.claude/agents/relecteur-berry.md` — sous-agent de relecture des `.be` modifies avant commit : syntaxe,
  charte des logs, RAM, regles du depot, bancs Berry lances. Ne modifie rien.
- `.claude/agents/relecteur-pages-web.md` — sous-agent de relecture des pages web (pages des outils PC generees par Python,
  pages servies par les cartes `data/sd`) avant commit : securite (XSS, anti-CSRF, SSRF), etat de la page, JS valide, mode sombre,
  sondes Chrome hermetiques. Ne modifie rien.
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
- `.claude/mods/suivi-sous-agents/` — mod, portee UTILISATEUR (installe pour tous les projets, pas seulement ce depot) : volet
  de progression des sous-agents (tache en cours, % d'apres leur liste TodoWrite, duree). Une consigne TodoWrite est ajoutee a chaque lancement de
  sous-agent ; le volet montre aussi le journal des outils et les remarques de chaque agent en cours. Commande `/sous-agents` (rouvre le volet).
  Banc : `claude plugin test .claude/mods/suivi-sous-agents`. Mise a jour comme `meteo-contexte` : monter `version` dans `plugin.json`, puis
  `claude.cmd plugin marketplace update mods-tasmota` et `claude.cmd plugin update suivi-sous-agents@mods-tasmota`.
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
  Depuis 0.4.0 (reglage `suiviPlan.ouvrirAvecConversation`, vrai par defaut) : la vue S'OUVRE d'elle-meme quand
  la conversation active suit un plan (message envoye ou bascule vers son onglet), une fois par conversation et
  par fenetre ; refermee a la main, elle ne se rouvre pas pour cette conversation (`C.ouvrirPourConversation`).
- `tasks/plans/` — un plan suivi par chantier ; format et regles de calcul dans `_FORMAT.md`.
- `tasks/README.md` — index des plans (demande du 2026-10-29) : objectif (cle `objectif:` de l'en-tete),
  statut, % de chaque plan. **A tenir a jour a chaque progression d'un plan** : le tableau est regenere par
  `node .claude/hooks/index_plans.mjs` (parseur du mod, memes % que la vue de droite), automatiquement par le
  hook `PostToolUse` `index_plans_edition.sh` quand Claude edite un `tasks/plans/*.md`, et par l'extension
  `suivi-plan` (>= 0.4.1, `extension.js::regenereIndex`) a TOUTE modification d'un plan tant que VS Code est ouvert
  (Bash, main, recopie par le mod a ExitPlanMode) ; `--verifier` = code 1 si en retard.
  Nouveau plan : lui donner une cle `objectif:`. Banc `node .claude/hooks/test_index_plans.mjs`.
- `tasks/lessons.md` — journal des erreurs et regles.
- `tasks/reprise-solidification-berry.md` — etat du chantier solidification, prochaine action.
- `tasks/reprise-chantier-modbus-grenier.md` — etat du chantier ModBus (carte 16 relais +
  esclaves), decisions tranchees, plan en phases. ⚠️ Nom trompeur : **cibles = les 3 modules
  garage**, le grenier est en sommeil. Travail sur `development` (branche de chantier supprimee
  le 2026-10-04).
- Firmware du coprocesseur Wi-Fi ESP32-C6 des P4 (2026-10-26) : `data/fs/controleCoprocesseur.be` (solidifie sur le P4,
  exclu des autres envs comme `controleES8311.be`), bloc persist `serveur.coprocesseur`. Au demarrage seulement : `Hosted`
  lu en local (C6 a jour -> aucun acces reseau) ; en retard -> ligne d'alerte sur l'accueil + UNE requete `Range` de
  512 o sur `<url>/v<Host>/network_adapter_<MCU>.bin` (version lue dans l'en-tete d'image), nouvel essai horaire, 6 au
  plus. Page `/coprocesseur` (gabarit `data/sd/html/coprocesseur.html`), bouton -> `HostedOta <URL complete>` ;
  resultat suivi par une regle `HostedOta`/`HostedLoad` : `Failed <code>` -> « echec » sur l'accueil et la page, bouton
  « Reessayer » ; `Failed 5379` = C6 BLOQUE (bug esp-hosted-mcu #143, flash serie seul remede) : cle persist
  `serveur.coprocesseur.bloque`, ni bouton ni requete, ligne d'accueil la 1re minute apres le demarrage seulement. Cle posee dans
  le persist du DEPOT (un flash serie reecrit le FS) : P4 du garage, et toute nouvelle carte P4 par
  `fichiers_berry_coprocesseur.VERSION_BLOQUEE` (regle du 2026-10-27). Version visee = `Host` (bibliotheque du firmware P4), PAS le fichier par defaut du serveur (en retard). Option `"mqtt": "ON"`
  (ON sur le P4) : `tele/<topic>/COPROCESSEUR` RETENU, a chaque changement d'etat et a chaque `Mqtt#Connected` (le JSON
  SENSOR n'est pas touche). Nouvel env : `outils_pc/fichiers_berry_coprocesseur.py` (appele par
  `fichiers_berry_creation._calcule`) pose ou neutralise l'alerte selon la PUCE de la base (persist, autoexec, cenv).
  Bancs `berry/banc_coprocesseur.py` (+ rendu Chrome), `outils_pc/test_fichiers_berry_creation.py`. Mode d'emploi :
  `outils_docs/README.md` ; plan `tasks/plans/alerte-firmware-c6.md`.
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
- `outils_docs/Schémas de branchement - Attribution des PINS des modules/<lieu>/<env>/Brochage GPIO - <env>.xlsx` — un
  classeur par carte (2026-11-08) : image de la carte, une ligne Excel par broche (cases fusionnees A:B / D:E, Arial,
  pointilles), usages tires du `_persist.json` (blocs actifs) puis COMPLETES A LA MAIN ; cartes a borniers : colonnes a
  texte vertical. Generateurs `outils_pc/genere_brochage_excel.py` (cartes `CARTES` : S3 DevKitC-1, DevKitC V4, P4) et
  `genere_brochage_horizontal.py` (ESP32 Relay x8, Waveshare 8DI-8RO), par Excel (pywin32, Python systeme) ; ne
  reecrivent jamais un classeur existant. Banc `outils_pc/test_genere_brochage.py`.
- Classement des cartes par lieu (2026-11-11, plan `tasks/plans/classement-par-lieu.md`, maquettes `outils_docs/filtre_lieu/`) :
  `outils_pc/lieux.py` = SEULE table des lieux (2e segment du nom d'env, exception de la piscine), `puce()`, et le JS
  `remplitParLieu` (listes `<optgroup>` des pages 7700 a 7980) ; banc `test_lieux.py`. Les routes `/envs`, `/parc`, `/cartes`
  ajoutent `lieu` (et `puce` pour la page Build) et `lieux`. Bascule « Classer par » de l'onglet Build : `build_page_lieux.py`,
  sonde `test_build_page_lieux_chrome.py` ; intertitres de l'onglet Fichiers : `build_page_fichiers.py::fichiersCartes`.
  Nouveau lieu : une ligne dans `lieux.LIEUX`, rien d'autre.
- `outils_docs/jauges/` — catalogue de 8 jauges pour afficher une mesure de capteur (2026-10-31) : images
  `jauge-A.png` a `jauge-H.png`, code `catalogue_jauges.html`, fiche `README.md`. **Choix retenu : A (liquide
  anime ECharts) ou H (demi-cercle SVG)**. Un gabarit `webSensor*.html` n'execute aucun script (zone remplacee
  toutes les ~2 s) : seuls les modeles SVG/CSS (D a H) s'y posent tels quels.
- `outils_docs/partitions/` — maquettes de l'onglet « Mémoire et partitions » de la page build (2026-11-01) : images
  `modele-A.png` à `modele-D.png`, code `maquettes_partitions.html`, contraintes `README.md`. **Choix retenu : B**. Pas
  encore réalisé : plan `tasks/plans/temps-compilation.md`, A7 à A10.
- Page `/cuve` (2026-10-31, premier essai, plan `tasks/plans/jauges-cuve.md`) : jauges A (volume en L) et H (taux en %)
  de la cuve, lien « (jauges) » dans la legende de `webSensorNiveauCuve.html`. Module `data/fs/cuvePageFonctions.be`
  (route declaree par `controleCuve.be::CAPTEURS_CUVE` et `controleGarage.be::CONTROLE_GARAGE` du P4), page
  `data/sd/{html,css,js}/cuve.*`, extension `data/sd/js/echarts-liquidfill.min.js.gz` ; valeurs par `/histo?p=direct`.
  Fichiers embarques sur la cuve et le P4 SEULEMENT : liste `page_cuve` de `[berry_commun]` dans le
  `custom_files_exclude` de tous les autres envs (regle : une page ne part que sur les cartes qui s'en servent).
  Banc `berry/banc_cuve_page.py`. Mode d'emploi : `outils_docs/README.md`.
- Page `/energie` du differentiel (2026-11-02, plan `tasks/plans/energie-differentiel.md`) : kWh et couts par heure, jour, mois gardes en flash, courbe de puissance 24 h ; `data/fs/energieFonctions.be` + `controleEnergie.be` (SOLIDIFIES, charges par l'autoexec, garde `diverses.energie`), `data/sd/{html,css,js}/energie.*` et `energieTarifs.*` (sous-page de Configuration : tarifs Base ou HC/HP) ; liste `page_energie` de `[berry_commun]` exclue de tous les autres envs. Banc `berry/banc_energie.py`. Mode d'emploi : `outils_docs/README.md`.
  Depuis le 2026-11-08 (palier 4 de l'atelier, spec `docs/superpowers/specs/2026-11-08-atelier-energie-differentiel-design.md`, plan `tasks/plans/energie-atelier.md`) la page se dessine d'apres `/json/energie_page.json` (routes `f=description`, `f=mois`, `f=direct` elargi ; repli sur la page d'avant si absente ou refusee ; 16 elements, 4096 o) ; ecrite par la destination « Energie » de l'atelier (`outils_pc/atelier_energie_description.py`, `atelier_graphiques_energie.py`, `atelier_graphiques_page_energie.py`, `cas_energie.json`) ; `energieFonctions` etant solidifie, firmware a recompiler une fois par la page Build. Bancs `berry/banc_energie_routes.py`, `banc_energie_description.py`, `outils_pc/test_energie_rendu.mjs`, `test_atelier_energie_description.py`, `test_atelier_graphiques_energie.py`, sonde `test_atelier_energie_page_chrome.py`.
- Carte des debits de la nourrice de chauffage (2026-11-08, plan `tasks/plans/debitmetres-chauffage.md`, pas encore essayee sur carte) :
  env `tasmota32s3-bureau-serveur-debits-pac`, module `debitsFonctions.be` + `controleDebits.be` du DOSSIER de la carte (pas `data/fs`),
  6 voies (2 `FlowRateMeter` groupe `debitmetres`, 4 `Counter` groupe `compteurs` ; `nom` et `k` dans l'entree de chaque voie),
  bloc `DEBITS` du JSON SENSOR, ecran TFT ILI9488 par HASPmota (`pages.jsonl`), capteur muet, veille de l'ecran, commande `ReglageDebits` ;
  historique et `/graphiques` (plan `tasks/plans/historique-debits.md`). Bancs `berry/banc_debits.py`, `banc_demarrage.py`, essai de charge
  `outils_pc/essai_charge_debits.py`. Guide d'equilibrage `outils_docs/chauffage/` (texte) ; page animee `equilibrage.html` du dossier de la carte, servie en `/equilibrage` par `equilibragePage.be` avec le code du mode carte `equilibrage_carte.js` (debits en direct, reglages gardes dans `/json/equilibrage.json`, relais pour un favori sans Referer ; plan `tasks/plans/equilibrage-par-la-carte.md`). Mode d'emploi : `outils_docs/README.md`.
- `outils_docs/EXTENSIONS_TAPP.md` — extensions Tasmota `.tapp` (2026-11-07) : format, cycle de vie, cas d'utilisation, gabarits
  A et B, envoi sur une carte, pieges (compilation avant `/autoexec.be`, formatage, image du FS). Essais sur carte : § 9, a faire (A10).
- `outils_docs/FICHIERS_DRVSET.md` — inventaire des fichiers `.drvset*`/`.snsset*` du firmware : role, contenu, chargement, sauvegarde, effacement (2026-11-02).
- `outils_docs/sauvegarde_config/` — maquettes de l'onglet « Sauvegardes » de la page build (2026-11-02) : `modele-A.png` a `modele-C.png`, code `maquettes_sauvegarde.html`, contraintes `README.md`. Choix en attente, rien de realise.
- `outils_docs/SOLIDIFICATION_BERRY.md` — mecanisme, verification (§5), parametres, 13 pieges.
- `outils_docs/PROTOCOLE_MODBUS.md` — ModBus RTU/TCP standard, implementation maison (3 transports
  Serie/UDP/TCP), extension esclave->maitre, failles du mecanisme d'envoi, design de queue FIFO,
  carte des registres de la carte 16 relais (§8), architecture de synchronisation (§9).
- `outils_docs/ANALYSE_BERRY_MODBUS_DISCOVERY.md` — **historique** (etat du 2026-09-22, encadre de tete :
  numeros de ligne perimes, defauts du §2.3 corriges depuis le 2026-09-30) — fonctionnement des programmes ModBus
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
    `outils_pc/`), `ota-files-uploader.py`, `update_idf55_framework.py` (appele par le pre-script),
    `ino_stable.py` (banc `test_ino_stable.py`), `test_scons_cache.py` (banc des reglages SCons du pre-script),
    `cfg_holder.py` (decide si le pre-script incremente `CFG_HOLDER`, banc `test_cfg_holder.py` ; plan
    `tasks/plans/temps-compilation.md`),
    `verifie_lib_ignore.py` (garde du pre-script, AVANT le scan des dependances : arrete le build si le `lib_ignore`
    qu'un env personnel ajoute a son parent ignore une bibliotheque incluse sous une garde vraie ou incertaine ;
    ~11 s ; ligne « lib_ignore de <env> : » lue par la page build ; `--propose <env>` = liste ignorable de l'env ;
    lecture des gardes dans le module voisin `lecture_gardes.py` ; un defaut du controle ne bloque jamais le build ;
    banc `test_verifie_lib_ignore.py [--reel]` ; plan `tasks/plans/lib-ignore-envs.md`).
  - `berry/` — `verifie_berry.py` (syntaxe de data/, tache VS Code de surveillance ; avertissements de
    charte des logs par `charte_logs.py`, banc `test_verifie_berry_charte.py`),
    `solidifie_et_compile_berry.py` (module solidifiable en ~10 s, compile le .h ; REFUSE pendant un build : il vide
    `berry_custom/src/embedded`, dont le build a besoin, incident du 2026-11-01),
    `nomme_fonctions_berry.py` (fonctions anonymes -> nommees), `carte_modules_berry.py`
    (-> `outils_docs/CARTE_MODULES_BERRY.md`, sortie deterministe : ni date ni ordre de hachage), `genere_schema_persist.py`
    (-> `outils_docs/schemas/persist.schema.json`), `gen_tapp.py` (dossier -> `.tapp` sans compression ; refuse un nom du
    framework nu, `LOG_LEVEL_*` compris, car la carte compile l'extension avant `/autoexec.be` ; banc `test_gen_tapp.py` ;
    exemple `data/extensions/fsMqtt/`, banc `banc_tapp_fsmqtt.{py,be}` sous `berry.exe -g -s` ; doc `outils_docs/EXTENSIONS_TAPP.md`),
    `banc_repartition_fichiers.{py,be}` (`gestionFileFolder.be::listeEtRepartitLesFichiers` : un fichier deplace au demarrage
    n'est jamais perdu, `.tapp` vers `/.extensions/`), et les bancs
    `banc_test_modbus.{py,be}`, `banc_leds.{py,be}` (ruban AUTO/MANUEL, bouton, LED du dev-kit),
    `banc_veille_drivers.be` (veille des drivers inactifs sur LittleFS neuf, `bouchons_berry/veille/`),
    `banc_boot.{py,be}` (autoexec ENTIER du P4 sur faux firmware `bouchons_berry/boot/` : persist reel, `{}`,
    sans `serveur.wifi`, ES8311 absent, telemetrie sans COUNTER ; timers de reboot P5.1 ; B1, B2, B3, MAC et ES8311 corriges, plus aucun defaut `CONNU`),
    `banc_demarrage.{py,be}` (autoexec ENTIER des 6 cartes maintenues, instantane compare a `bouchons_berry/demarrage/<env>.txt` ;
    les autoexec ne gardent que la liste ordonnee de leurs modules, le deroule commun est dans `data/fs/demarrage.be`, P4.2),
    `test_discovery.be` avec leurs `bouchons_berry/` (`bouchons_berry/leds/` : bouchon de
    `ledsFonctions`, ajoute par le seul banc ModBus ; dans `bouchons_berry/`, il masquerait le vrai
    module a `banc_leds`).
  - `maintenance/` — `purge_cache_build.py` (vide les objets du cache `.cache` inutilises depuis N jours, defaut 30 ;
    `--dry-run` ; refus pendant un build ; aussi bouton de la page build ; banc `test_purge_cache_build.py`), `exclusions_defender.ps1` (exclusions
    Defender des dossiers de build, en administrateur, `-Verifier`),
    `synchronise_fork_tasmota.py` (synchro du fork : merge, jamais de force-push),
    `synchronise_upstream_tasmota.py` (variante rebase), `corrige_reglages_vscode.py` (pose et
    prouve les reglages VS Code du PermissionError), `verifie_references_docs.py` (renvois au code des
    documents durables : `fichier::fonction`, jamais `fichier:ligne` ; chemins et fonctions cites verifies ;
    banc `test_verifie_references_docs.py`). Page web de la synchro : `synchro_fork_web.py`
    (serveur, port 7500) + `synchro_fork_session.py` (script lance en processus enfant, questions),
    `synchro_fork_etat.py` (bandeau, diff, journal), `synchro_fork_page.py`, `synchro_fork_question.py`
    (importe par les deux scripts) ; banc `test_synchro_fork_web.py` (`--reel` : vrais scripts en
    --dry-run) ; cible `build/cible_synchro_fork.py`. Assistant pas a pas (2026-10-27) :
    `synchro_fork_assistant.py` (analyse en lecture seule hors fetch, prevision `git merge-tree`, liste
    d'etapes), `synchro_fork_fusion.py` (voie B : merge local, resolution, termine, abandonne, pousse ;
    marque `.git/synchro-fork-assistant`), `synchro_fork_page_assistant.py` (bloc, style et script de la
    page) ; bancs `test_synchro_fork_assistant.py`, `test_synchro_fork_fusion.py`,
    `test_synchro_fork_fusion_suite.py` (faux depot `faux_depot_synchro.py` : amont et origin nus + clone ;
    commandes git d'ecriture limitees par `liste_blanche_git_synchro.py`), sonde Chrome
    `test_synchro_fork_page_chrome.py`. Spec `docs/superpowers/specs/2026-10-27-assistant-synchro-fork-design.md`,
    plan `tasks/plans/assistant-synchro-fork.md`. **Exceptions a la regle du meme dossier** : `outils_pc/build_web.py` importe
    `maintenance/purge_cache_build.py` (bouton de purge de la page build), et
    `synchro_fork_web.py` importe `outils_pc/acces_web.py` et `outils_pc/build_serie.py` (detection
    d'un build en cours) par un `sys.path` explicite ; de meme `outils_pc/autoexec_gardes.py` importe
    `build/verifie_lib_ignore.py` (macros d'un env), et `outils_pc/tapp_sources.py` importe `berry/gen_tapp.py`.
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
    `build/cible_sniffeur_modbus.py`) — meme convertisseur, page http://127.0.0.1:7300 : trames du bus en direct,
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
  - `sniffeur_i2c.py` (+ `sniffeur_i2c_web.py`, `sniffeur_i2c_http.py`, `sniffeur_i2c_aide.py`, `sniffeur_i2c_protocole.py`,
    `sniffeur_i2c_alertes.py`, `sniffeur_i2c_carte.py`, `decodeur_i2c.py`, `decodeur_i2c_puces.py`,
    `build/cible_sniffeur_i2c.py`) — page http://127.0.0.1:7350 (2026-10-31) : trafic d'un bus I2C par un ESP32-S3
    DEDIE (firmware autonome `outils_docs/firmware_sniffeur_i2c/`, PAS un env Tasmota ; SDA GPIO4, SCL GPIO5, GND,
    3,3 V seulement ; coeur 1 sans interruption, chien de garde des interruptions du coeur 1 coupe). Une ligne texte
    par transaction (protocole v=1, `sniffeur_i2c_protocole.py`, commun au futur Pico). Decodage jusqu'au registre
    (ADS1115, MCP23017, TCA9554, DS3231, MPU6050, ES8311) ; adresses partagees (0x20, 0x68) levees par la carte
    observee (puces actives de son persist), sinon « ambigu ». Envoi : par la carte, en HTTP ou en MQTT (`cmnd/<topic>/Br`,
    reponse `stat/<topic>/RESULT` : esclaves derriere le NAPT) (`Br (wire1.detect(a) ? wire1 :
    wire2).read/write`, pas `tasmota.wire_scan` qui rend nil pour une puce prise par un pilote C ; apercu avant envoi,
    ecriture confirmee, rapprochement de la trame) ou par le sniffeur maitre (composant isole, refus si le bus a vecu
    dans les 2 s). Journal `%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\` (30 jours). Bancs : `test_sniffeur_i2c.py`,
    sonde `test_sniffeur_i2c_page_chrome.py`, machine du firmware `firmware_sniffeur_i2c/banc/lance_banc.py` (MSVC ou
    g++). Spec `docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md` ; plan `tasks/plans/sniffeur-i2c.md`.
  - `sniffeur_mqtt.py` (+ `sniffeur_mqtt_web.py`, `sniffeur_mqtt_panneaux.py`, `sniffeur_mqtt_config.py`,
    `client_mqtt.py`, `build/cible_sniffeur_mqtt.py`) — sniffeur / publieur MQTT sur http://127.0.0.1:7100 :
    plusieurs brokers parametrables (TLS possible) et selectionnables, abonnements gerables un par
    un et memorises par broker, filtre d'affichage + favoris, differences avec le message precedent
    du meme topic, export .txt/.json, publication (retenu ou non). Panneaux : audit discovery,
    connexions LWT, logs par carte (`stat/<topic>/LOGGING`, sans occuper les ports serie), commande
    Tasmota avec sa reponse, arborescence des topics. Broker par defaut lu dans
    `user_config_override.h` ; les autres (mots de passe compris) dans
    `%APPDATA%\sniffeur_mqtt\config.json`, HORS depot. Cible PlatformIO « Sniffeur MQTT » dans Custom.
  - `syslog_tasmota.py` (+ `syslog_tasmota_web.py`, `build/cible_syslog_tasmota.py`) — serveur syslog :
    ecoute UDP 514, page http://127.0.0.1:7200 (filtre module / severite / texte), journal
    `%TEMP%/syslog_tasmota.log`. Cible PlatformIO « Serveur syslog » dans Custom. Les modules
    envoient a `SYS_LOG_HOST` (`user_config_override.h`) = **192.168.0.3, ce PC** (le NAS
    192.168.0.2 est eteint) : IP figee par une reservation DHCP sur la box (MAC Wi-Fi
    DC-85-DE-D9-CA-1D, confirmee le 2026-10-24 ; Windows reste en DHCP, c'est normal).
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
  - `build_web.py` (+ `build_page.py`, `build_serie.py`, `build_envs.py`, `build_progression.py`, `build_ota_fs.py` (FS ; firmware : `build_ota_firmware.py` ; maitre :
    `build_ota_maitre.py` ; transport HTTP : `build_ota_http.py`, decoupe le 2026-10-29 ; FS par MQTT : `build_ota_mqtt.py`,
    A16), `build_fichiers.py`, `build_page_fichiers.py`, `build_memoire.py` (occupation memoire de l'env, relue du dernier
    build, `GET /memoire`, `POST /memoire/analyser`), `build_page_memoire.py` (onglet « Mémoire et partitions », modele B ;
    sonde `test_build_page_memoire_chrome.py`), `build_partitions.py` (table de partitions de l'env : validation,
    `partitions/env_<env>.csv`, OTA bloquee jusqu'au prochain effacement ; `POST /partitions/diff|ecrire` ; plan
    `tasks/plans/temps-compilation.md` A7 a A10), `build_defaut.py` (bloc `default_envs` de `platformio_override.ini`, ce que
    compile un `pio run` sans -e : `GET /defaut`, `POST /defaut/diff|ecrire` ; banc `test_build_defaut.py`), `build_page_defaut.py`
    (onglet « Env par défaut (Platformio override) », modele B + futur fichier dessous ; sonde `test_build_page_defaut_chrome.py` ; maquettes
    `outils_docs/default_envs/` ; plan `tasks/plans/default-envs-page.md` ; case de creation d'env : `fichiers_berry_creation.py::ajoute_default_envs`),
    `build_solidification.py`, `build_drvset.py` (copie `/.drvset003` par le reseau avant un upload ou erase_upload serie, la renvoie apres, `Restart 99` puis relecture du calibrage ; copie dans `drvset/` du dossier de donnees de la page ; banc `test_build_drvset.py`), `build_page_aide.py` (onglet « Aide », texte fixe : fichiers `.drvset`), `build_page_couleurs.py` (codes ANSI du journal -> couleurs du terminal de VS Code dans le panneau « Sortie »), `build_sauvegarde.py` + `build_page_sauvegarde.py` + `build_sauvegarde_mqtt.py` (liaison MQTT : FileDownload/FileUpload ; banc `test_build_sauvegarde_mqtt.py`, avec la purge (case de l'onglet, `reglages.json`), les étapes de restauration et les marques « reposé au démarrage ») (onglet « Sauvegarde configuration », modele B : `/dl` de chaque carte dans `outils_docs/sauvegardes_cartes/<env>/`, ignore par git ; parametres, copie modifiee, comparaison, restauration ; « avant flash » prise par la serie ; banc `test_build_sauvegarde.py`, sonde `test_build_page_sauvegarde_chrome.py` ; plan `tasks/plans/sauvegarde-config-cartes.md`), `decode_config.py` (+ `decode_config_groupes.py` : decode-config 16.0.0.0 dans `%LOCALAPPDATA%\outils_tasmota\decode_config\`, hors depot et hors Python de PlatformIO ; textes ecrits par l'outil, decode-config tronquant la reserve d'un ESP32), et pour les bancs `build_faux_pio.py`, `build_ota_carte_simulee.py`) — page « Build et televersement »
    http://127.0.0.1:7700 (tuile de l'annuaire, groupe Maintenance, hors job : l'annuaire refuse de l'arreter pendant
    un lancement ; tache VS Code « Outil : build et televersement » ; cible Custom « Build et televersement (page web) »
    (`build/cible_build_web.py`, banc `build/test_cible_build_web.py`) qui DEMARRE LA PAGE DETACHEE puis rend la
    main : une cible est un `pio run`, vivante elle serait vue comme un build en cours ; `pio run` : jamais
    pendant un build). On coche des envs (Mes cartes / Mes bases / amont) et des actions (compiler, televerser le firmware
    OU effacer puis televerser, construire le FS, televerser le FS), COM ou OTA par ligne ; les `pio run` s'enchainent
    un a un (jamais deux ensemble ; attente si un build apparait ailleurs ; refus si port tenu ou absent), avec
    etape, % et durees en direct, et la **sortie de pio en direct** par env (panneau « Sortie » : journal de l'env
    lu par increments par `GET /sortie`, barres d'esptool contenues ; referme quand l'env reussit sauf geste de
    l'utilisateur, pas rouvert au rechargement pour un env reussi). **Pause « rebranchez la carte »** (choix 11
    revise) : deux envois sur le meme port COM sont acceptes ; avant l'envoi d'un env dont le port a deja servi dans
    la serie (compilation faite avant, en un `pio run` a part), bandeau « Branchez la carte X sur COMn » +
    Continuer / Passer cet env (`POST /continuer`), port reverifie a la reprise. Journaux tries par date de
    modification (pas l'heure du nom : heure d'hiver), purges au demarrage au-dela de 30 jours. « Effacer puis televerser » =
    `-t erase_upload --upload-port COMn`, COM seulement, exclusive avec l'upload, confirmation avant (persist et
    reglages de la carte remplaces par ceux du depot), etape « Effacement de la flash ». `data_dir` de `platformio_override.ini`
    pose sur le dossier de l'env AVANT chaque `pio run` d'une carte (`build_envs.py::ecrit_data_dir`) : pio lit ce fichier
    avant le pre-script, qui pose aussi `PROJECT_DATA_DIR` pour le lancement en cours (banc `build/test_data_dir.py`) ; sans
    cela, un buildfs seul prenait le dossier de l'env precedent (P4 avec le FS de la cuve, 2026-10-26). Port COM lu dans `platformio_tasmota_cenv.ini` et REECRIT dans la section de l'env
    (`.bak` ; **change l'empreinte -> le build suivant repart de zero**) ; IP OTA lue dans `WIFI_IP_ADDRESS`
    (0.0.0.0 -> esclave du range extender du maitre : `<ipMaitre>:<8080 + id - 1>` tire du persist,
    `build_envs.py::adresse_par_maitre` ; sinon saisie pour le lancement). Vers une adresse `IP:port`, AVANT tout envoi :
    `RoutageRangeExtender` sur le maitre puis `Status 5` compare au nom d'hote du persist (`build_ota_maitre.py::joint_par_maitre`),
    refus sinon ; maitre en `Sleep 0` le temps de l'envoi (`build_ota_maitre.py::coupe_sleep`, a `Sleep 50` son relais
    coupe l'envoi) ; carte deja en safeboot reconnue a sa page d'accueil (`build_ota_http.py::_page_safeboot`), envoi relance. OTA du firmware envoyee par la page (`/up`, `/u2`, safeboot `/u4`, preuve
    par `Status 2`) : aucun script de `build/` modifie. OTA du FS : fichiers extraits de `littlefs.bin` (image du `buildfs`,
    PAS `littlefs_data`, perime) par `/ufsu` apres controle d'identite (`build_ota_fs.py::verifie_identite` : nom d'hote et topic du persist de
    l'image = ceux du persist de l'env au depot, sinon rien n'est envoye), persist de
    la carte sauvegarde avant dans `%LOCALAPPDATA%\outils_tasmota\build\persist\`, relu, Berry recharge, `Restart 1`.
    Un upload (ou erase_upload) serie du firmware flashe AUSSI le FS (persist compris) a chaque fois pour les envs a
    `custom_files_upload` (post_esp32 reconstruit `littlefs.bin` a chaque edition des liens) : la page l'annonce, grise
    « Construire / Televerser le FS » si tous les envs coches sont dans ce cas, et sinon le serveur ne lance ni buildfs ni
    uploadfs pour eux (statut de l'envoi, `build_serie.py::Serie._plan`). Journaux de chaque `pio run` dans
    `%LOCALAPPDATA%\outils_tasmota\build\journaux\`. Chaque lancement reecrit `platformio_override.ini` et
    `user_config_override.h` (a commiter). Bancs : `test_build_*.py` (+ sonde `test_build_page_chrome.py`).
    Onglet « Fichiers » (A15, en cours, spec choix 24) : `GET /fichiers?env=` (`build_fichiers.py::liste` : fichiers de
    l'image du dernier buildfs, jeton = date de l'image) puis action `fichiers` de la serie (une carte OTA, fichiers
    choisis, refus si l'image a change depuis la liste ; `build_ota_fs.py::envoie_fs_ota` avec `fichiers=`). Page :
    `build_page_fichiers.py` (CSS/HTML/JS de l'onglet, maquette E, inseres dans `build_page.PAGE` ; avancement en % et
    journal des etapes dans l'onglet) ; sonde `test_build_page_fichiers_chrome.py` (Python de PlatformIO, aucun envoi).
    Transport MQTT (A16, spec choix 25 a 28) : `build_ota_mqtt.py::envoie_fs_mqtt` -> module carte `data/fs/fsMqtt.be`
    (topics `fsmqtt/<topic du persist>/ordre|morceau|etat|lu`, fichier temporaire + MD5, effacement = formatage
    `path.format`, bloquant : watchdog de 5 s ; SOLIDIFIE dans `berry_commun.socle`, charge par l'autoexec du P4 et de la cuve). Bancs `berry/banc_fsmqtt.py` (mutants),
    `test_build_ota_mqtt.py` (carte MQTT simulee).
    Arrivee depuis l'atelier des graphiques (2026-11-05, plan `tasks/plans/atelier-destinations.md` A7) : `?env=&depuis=atelier&fichiers=&redemarrer=`,
    code dans le module neuf `build_page_atelier.py` (JS seul, ajoute a la fin de celui de `build_page_fichiers.py`) : bandeau, `buildfs` lance seul, fichiers
    coches a la fin, rien d'envoye ; sonde `test_build_page_fichiers_chrome.py::sonde_atelier`.
    Mode d'emploi : `outils_docs/README.md` § « Build et televersement (page web) » (onglet : « Onglet « Fichiers » :
    envoyer quelques fichiers du FS »). Spec :
    `docs/superpowers/specs/2026-10-24-page-build-televersement-design.md` ; plan :
    `tasks/plans/page-build-televersement.md`.
  - `fichiers_berry_web.py` (+ `fichiers_berry_page.py`, `fichiers_berry_ini.py`, `fichiers_berry_etat.py`,
    `fichiers_berry_ecriture.py`, `fichiers_berry_creation.py`, `fichiers_berry_suppression.py`, `fichiers_berry_renommage.py`,
    `fichiers_berry_sauvegarde.py`, `fichiers_berry_page_envs.py`, `fichiers_berry_coprocesseur.py`) — page « Fichiers Berry par env » http://127.0.0.1:7800
    (tuile de l'annuaire, groupe Maintenance, arret libre : rien n'est ecrit avant « Enregistrer » ; tache VS Code
    « Outil : fichiers Berry par env » ; cible Custom « Fichiers Berry par env (page web) », `build/cible_fichiers_berry.py`,
    banc `build/test_cible_fichiers_berry.py`, page demarree detachee comme celle du build ; lien « fichiers » sur chaque
    env personnel de la page build, `?env=` dans les deux sens). Par env : chaque `.be` (data/fs, dossier de la carte,
    modules amont `tasmota/berry/modules`, recenses a chaque chargement) sur le FS, exclu ou solidifie, ecrit dans
    `custom_files_upload` / `custom_files_exclude` / `custom_berry_solidify` du cenv : resolution des `${...}` avec
    provenance (`fichiers_berry_ini.py`), liste partagee -> envs touches nommes puis « Modifier (N envs) » ou « Annuler »,
    option heritee -> `${env:<base>.opt}` + ligne, commentaires jamais touches (ceux qui citent le fichier signales),
    raison facultative `; raison (date)`, diff puis ecriture avec empreinte, refus pendant un build. Creation
    d'un env a partir d'une carte modele (`fichiers_berry_creation.py`) : section du cenv, dossier `data/<lieu>/<puce>-<nom>`
    (identite remplacee dans le `_persist.json`, texte garde octet pour octet), section `#elif` de `user_config_override.h` ;
    refus si env/dossier/define/IP/topic/client deja pris ; secrets masques dans le diff. Renommage d'un env
    (`fichiers_berry_renommage.py`, identite reproposee, dossier DEPLACE) et suppression (`fichiers_berry_suppression.py` :
    section du cenv et du `.h` retirees, `default_envs` de `platformio_override.ini`, dossier renomme en `…-sauvegarde`) ;
    panneaux dans `fichiers_berry_page_envs.py`. Toute ecriture est ATOMIQUE (`fichiers_berry_sauvegarde.Transaction` :
    annulation sur exception, copie horodatee dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`, 30 jours ;
    plus de `.bak` ; POST un par un ; marque `en_cours.json` restee = operation interrompue, bandeau dans la page).
    Identite deja portee par une autre carte = avertissement (carte remplacee), pas un refus. Copies temporaires d'un build (`.be` de la carte identique a `data/fs`) ni proposees ni recopiees ;
    exception inattendue -> 500 avec son message. Bancs `test_fichiers_berry_*.py`
    (copies temporaires, jamais le vrai depot ; `_ecriture` relu par `ProjectConfig`) + sonde Chrome
    `test_fichiers_berry_page_chrome.py`. Mode d'emploi : `outils_docs/README.md` § « Fichiers Berry par env (page web) ».
    Spec : `docs/superpowers/specs/2026-10-25-page-fichiers-berry-design.md` (§9 suppression, §10 renommage) ; plans :
    `tasks/plans/fichiers-berry-env.md`, `tasks/plans/fichiers-berry-suppression.md`.
  - `assistant_persist_web.py` (+ `assistant_persist_page.py`, `assistant_persist_page_js.py`, `assistant_persist_modele.py`,
    `assistant_persist_parc.py`, `assistant_persist_generation.py`, `assistant_persist_elements.py`,
    `assistant_persist_creation.py`, `assistant_persist_texte.py`, `assistant_persist_delta.py`,
    `assistant_persist_modification.py`, `assistant_persist_page_js_env.py`) — page « Assistant persist » http://127.0.0.1:7900 (tuile de l'annuaire, groupe
    Maintenance, arret libre : rien n'est ecrit avant « Creer l'env » ; tache VS Code « Outil : assistant persist » ;
    cible Custom « Assistant persist (page web) », `build/cible_assistant_persist.py`, banc
    `build/test_cible_assistant_persist.py`). Pose des questions et en tire le `_persist.json` d'une NOUVELLE carte, son
    autoexec, la section du cenv et la section `#elif` du `.h`, d'apres le modele `outils_docs/schemas/modele_persist.json`
    (se met a jour du parc : fusion des cles nouvelles a l'ouverture, bouton « Mettre a jour le modele » avec diff,
    sauvegardes horodatees). Editeur des entrees/sorties du bloc metier (broches de `data/fs/configGlobal.be`, refus des
    doublons et des broches ModBus/I2C/LEDs). Mots de passe JAMAIS envoyes a la page : recopies cote serveur, `***` dans
    l'apercu et le diff. Creation en une transaction, moteur de `fichiers_berry_creation.py` reutilise ; refusee pendant
    un build. Limites : seuls activation, nom, broche et type s'editent ; bloc metier principal seulement. Modification
    d'un env existant par ecart (A -> B, le reste intact) et suppression verifiee : faites (spec §10,
    `tasks/plans/assistant-persist-modification.md`). Bancs `test_assistant_persist_*.py` (dont `_texte`, `_delta`,
    `_modification`, ce dernier lent) + sonde Chrome
    `test_assistant_persist_page_chrome.py`. Mode d'emploi : `outils_docs/README.md` § « Assistant persist (page web) ».
    Spec : `docs/superpowers/specs/2026-10-27-assistant-persist-design.md` ; plan : `tasks/plans/assistant-persist.md` ;
    analyse en attente de decision : `outils_docs/ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md`.
    Onglet « autoexec.bat » (2026-11-05, modele C de `outils_docs/autoexec_bat/`) : `assistant_persist_autoexec.py` (routes),
    `autoexec_fichier.py` (lecture masquee, diff, ecriture), `autoexec_analyse.py` (avertissements), `autoexec_commandes.py`
    (fige `outils_docs/schemas/commandes_tasmota.json` ; `--verifier`, `--generer`), `autoexec_banque.py`
    (`outils_docs/schemas/banque_autoexec.json`), `autoexec_envoi.py` (HTTP `/ufsu` ou MQTT par `fsMqtt` de la carte,
    `build_ota_mqtt.py` ; nom d'hote de la carte = persist du depot, sinon refus ; verrou par carte), `autoexec_gardes.py`
    (alerte orange « absente » : commande dont TOUTES les gardes `USE_*` sont fausses pour l'env, cle `gardes` de
    `commandes_tasmota.json` ; calcul dans un processus fils, cache par env), `autoexec_berry.py` (même alerte pour une commande
    Berry dont l'`autoexec.be` de la carte ne charge pas le module ; banque marquée par `GET /autoexec/marques`), page `assistant_persist_page_autoexec.py`, `_autoexec_js.py`, `_autoexec_lignes_js.py` (commande deja presente,
    suppression de ligne). Mode d'emploi : `outils_docs/README.md` § « Onglet « autoexec.bat » » ; spec
    `docs/superpowers/specs/2026-11-03-onglet-autoexec-bat-design.md` ; plans `tasks/plans/autoexec-bat.md`, `tasks/plans/autoexec-mqtt-tapp.md`.
  - `tapp_web.py` (+ `tapp_page.py`, `tapp_sources.py`, `tapp_envoi.py`, `build/cible_tapp.py`) — page « Fabrique d'extensions »
    http://127.0.0.1:7980 (2026-11-07 ; tuile de l'annuaire, groupe Maintenance, arret libre ; tache VS Code ; cible Custom detachee,
    `NOM_CIBLE` fabrique_tapp). Sources dans `data/extensions/<nom>/` (gabarits A et B de `outils_docs/EXTENSIONS_TAPP.md`), manifeste,
    controle et fabrication par `berry/gen_tapp.py`, `.tapp` a cote du dossier (ignore par git) ; envoi HTTP ou MQTT vers
    `/.extensions/<nom>.tapp` par `autoexec_envoi.py` (identite, refus pendant un build, geste explicite ; en MQTT, lecture de la
    carte au seul clic « Lire la carte ») ; boutique locale de `/ext` (`GET /extensions/...`, publique, `tapp_sources.py::depot`) pour une carte dont
    l'`OtaUrl` pointe sur ce PC. Bancs `test_tapp_web.py`, `test_tapp_envoi.py`, sonde `test_tapp_page_chrome.py`,
    `build/test_cible_tapp.py`. Mode d'emploi : `outils_docs/README.md` § « Fabrique d'extensions (page web) ». Non essaye sur carte (A10).
  - `atelier_graphiques_web.py` (+ `atelier_graphiques_page.py`, `_page_js.py`, `_page_series.py`, `_description.py`, `_series.py`,
    `_conseil.py`, `_ecriture.py`, `build/cible_atelier_graphiques.py`) — page « Atelier des graphiques » http://127.0.0.1:7950 (2026-11-04, palier 1 ;
    tuile de l'annuaire, groupe Maintenance, arret libre : rien n'est ecrit avant « Ecrire dans le depot » ; tache VS Code « Outil : atelier des
    graphiques » ; cible Custom detachee, `NOM_CIBLE` atelier_graphiques ; modele B de `outils_docs/atelier_graphiques/`). Prepare les pages de graphiques d'une carte
    S3/P4 (series de l'historique, du JSON SENSOR ou calculees ; conseil de style ; apercu par le VRAI moteur de la carte, valeurs de la carte en ligne sinon
    persist du depot et valeurs simulees). Ecrit `data/<lieu>/<carte>/pages_graphiques.json` (valide par `_description.py::valide`), la ligne
    `demarrage.charge(["pagesGraphiques"])` de l'autoexec et le cenv : deux listes de `[berry_commun]`, `pages_graphiques` (gabarit, `.be` du moteur ; exclue de tout env sans page)
    et `pages_graphiques_moteur` (`pagesGraphiquesValidation.be`, `pages_graphiques.js`, `pages_graphiques_formule.js`, `graphiques_moteur.js` ; exclue des envs sans historique ET sans page : suit
    l'historique ou une page dediee) ;
    diff puis ecriture atomique, refusee pendant un build ou sur empreinte perimee ; `--exclusions` = application au vrai depot. Moteur cote carte :
    `data/fs/pagesGraphiques.be` + `pagesGraphiquesValidation.be` (route `/pages?p=<id>`, `?f=valeurs`, `?f=sources`, description `/json/pages_graphiques.json`),
    `data/sd/{html,css,js}/pages_graphiques.*` + `pages_graphiques_formule.js`. Premiere page : la cuve (`/pages?p=tableau`, courbe « Hauteur d'eau »).
    `ReglageCuve simulation <ON|OFF|minutes>` (`cuveFonctions.be::reglageCuve`) : hauteur d'eau simulee sans sonde, RAM seulement. Bancs
    `test_atelier_graphiques_*.py`, `test_pages_graphiques.mjs`, `test_pages_graphiques_chrome.py`, `berry/banc_pages_graphiques.py` (cas partages
    avec le validateur Python), `build/test_cible_atelier_graphiques.py`. Mode d'emploi : `outils_docs/README.md` ; spec
    `docs/superpowers/specs/2026-11-03-atelier-graphiques-design.md` ; plan `tasks/plans/atelier-graphiques.md`.
    **Destination « Graphiques » et bouton « Televerser »** (2026-11-05, spec `docs/superpowers/specs/2026-11-04-atelier-destinations-televersement-design.md`,
    plan `tasks/plans/atelier-destinations.md`) : menu « Page » (pages dediees, « Graphiques (/graphiques) » si l'historique est actif, « Autre… »). Modules neufs :
    `atelier_graphiques_graphiques.py` (ecriture de la cle `graphiques` de `graphiques.json`, graphiques `"moteur": "pages"` ; composition de la carte comparee au depot,
    choix `base=carte|depot`, jamais d'ecrasement implicite), `atelier_graphiques_televerse.py` (liste des fichiers a envoyer, URL de la page Build),
    `atelier_graphiques_page_destination.py` et `atelier_graphiques_page_televerse.py` (JS de la page). Bancs `test_atelier_graphiques_graphiques.py`
    et `test_atelier_graphiques_televerse.py`. Cote carte : `data/sd/js/graphiques_moteur.js` (trace d'un graphique `moteur` par `PagesGraphiques.optionDe`) ;
    `graphiquesFonctions.be::valideComposition` accepte `"moteur": "pages"` (valide par `pagesGraphiquesValidation.be`). Mode d'emploi : `outils_docs/README.md`.
