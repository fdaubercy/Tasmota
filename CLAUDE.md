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
  directement par `python outils_docs/scripts_python/<outil>.py` (ex. `sniffeur_modbus.py
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
  garage**, le grenier est en sommeil. Travail sur `development` (branche de chantier supprimee
  le 2026-10-04).
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
- `outils_docs/AUDIT_MODBUS_2026-09-29.md` — audit complet ModBus garage (B1 corrige, secrets
  en clair sur depot public, defauts G1-G8 actifs, L1-L13 latents, ameliorations par priorite).
- `outils_docs/Electronique/Connecteur ModBus/` — docs constructeur de la carte 16 relais
  (`... commamd.docx` = jeu de commandes, `... Manual.docx` = caracteristiques).
- `docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md` — verdict Q1/Q2/Q3.
- `outils_docs/scripts_python/` :
  - `synchronise_fork_tasmota.py` — synchro du fork (merge, jamais de force-push).
  - `solidifie_et_compile_berry.py` — verifie qu'un module est solidifiable en ~10 s (compile le .h).
  - `nomme_fonctions_berry.py` — convertit les fonctions anonymes d'un module.
  - `corrige_reglages_vscode.py` — pose et prouve les reglages VS Code (PermissionError).
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
    editables dans la page), `debit_modbus.py` (trouve puis corrige, sur confirmation, le debit et
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
