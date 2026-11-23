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
   decoulent. Le hook `SessionStart` en injecte la synthese (`tasks/lessons-actives.md`) et les entrees plus recentes ;
   **avant de toucher a un sujet, y chercher par mot-cle** (grep), sans le lire en entier (plus de 230 Ko). Chaque entree
   est une erreur passee a ne pas refaire.
2. **`tasks/reprise-modbus-garage.md`** — ce qui reste du chantier ModBus : cibles = les 3 modules GARAGE (maitre
   P4, cuve, rideau) et le portail de jardin ; le grenier est en sommeil. Lire son encadre « SI TU REPRENDS A FROID ».
   Travail sur **`development`**. L'ancienne reprise (« grenier ») est dans `tasks/archive/`.
3. **`outils_docs/SOLIDIFICATION_BERRY.md`** — le mecanisme complet, les pieges, l'etat reel et la regle des fichiers
   de carte (§3 et §7), a lire des que le sujet Berry/solidification arrive.
4. **`outils_docs/PROTOCOLE_MODBUS.md`** — a lire des que le sujet ModBus arrive : carte
   des registres de la carte 16 relais (§8) et architecture de synchronisation (§9).
5. **`tasks/plans/`** — plans de travail suivis (`statut: actif`, format `tasks/plans/_FORMAT.md`) :
   le mod `suivi-plan` en injecte le resume en debut de conversation ; sans le mod, lire le plan actif.
6. **`outils_docs/INDEX.md`** — l'aiguillage : quelle situation -> quel fichier lire, et rien d'autre. Importe ici :

@outils_docs/INDEX.md

Si le demarrage affiche une ligne `fork : N commit(s) de retard sur upstream/development`,
c'est le hook de detection : voir la section « Synchro du fork » plus bas. **Ne pas lancer
la synchro de sa propre initiative**, et surtout pas dans une branche de chantier.

**Apres chaque correction de l'utilisateur**, ajouter immediatement une entree a
`tasks/lessons.md` au format `[YYYY-MM-DD] | ce qui s'est mal passe | regle a suivre`.
Append uniquement, ne jamais supprimer une entree.

## Graphify : exemption COMPLETE

**`/graphify --update` ne doit PAS etre lance avant un commit sur ce depot, et aucune carte des connaissances
(`graphify-out/`) n'y est creee** : les deux regles globales (pre-commit, « cree la carte si elle n'existe pas ») ne
s'appliquent pas ici. L'aiguillage des documents est `outils_docs/INDEX.md`.

La regle globale l'impose sur mes projets ; ce depot y deroge explicitement (decide le
2026-07-15). Raison : il n'y a **pas de `graphify-out/`** ici, donc rien a mettre a jour ;
et en construire une carte sur un depot de la taille de Tasmota (~15 000 fichiers amont)
serait un chantier sans rapport avec le travail mene.

Ordre de commit sur ce depot : `git add` puis `git commit`. Rien d'autre.

## Synchro du fork : un hook qui DETECTE, une synchro qui reste manuelle

Le hook `SessionStart` (`.claude/hooks/verifie_synchro_fork.sh`, une fois par 24 h) signale le retard de `development`
sur l'amont ; il ne synchronise jamais. **Ne pas lancer la synchro de sa propre initiative, ne jamais merger l'amont dans
une branche de chantier, ne pas faire lancer la synchro par un hook** (decide le 2026-07-24 : timeout = `MERGE_HEAD`
orphelin, questions sans terminal). Sur `development` propre, a la main : `python
outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py` (« N » ou `--dry-run` = diagnostic), ou la page web
:7500. Detail, raisons et assistant pas a pas : `outils_docs/environnement/SYNCHRO_FORK.md` ; agent `diagnostic-synchro-fork`.

## Fichiers de plus de 500 lignes

Avant de proposer de decouper un fichier de plus de 500 lignes, lire `outils_docs/verification/EXCEPTIONS_500_LIGNES.md` :
une exception qui y figure est une decision de l'utilisateur, ne pas la decouper pour satisfaire le compteur. Nouvelle
exception = une entree datee dans ce fichier, jamais ici.

## Nouveau poste, PermissionError sur tasmota.ino.cpp

Detail : `outils_docs/environnement/NOUVEAU_POSTE.md` (Settings Sync avec `Profiles` coche, PlatformIO, filet
`maintenance/corrige_reglages_vscode.py --verifier`, extension suivi-plan, exclusions Defender). Le PermissionError
intermittent vient de l'indexeur C/C++ : `C_Cpp.files.exclude` ET `C_Cpp.exclusionPolicy` dans le profil VS Code ACTIF,
**jamais** dans `.vscode/settings.json` (suivi par git et present en amont).

## Commits

- Messages **en francais** — titre et corps. Regle explicite du 2026-07-15. Le depot amont
  est anglophone : ce fork ne l'est pas, et ses commits ne remontent pas chez arendst.
  Seuls les prefixes conventionnels (`feat:`, `fix:`, `docs:`, `chore:`) restent en anglais :
  ce sont des etiquettes lues par les outils, pas de la prose.
- Messages **sans accents** (precedent d'encodage casse).
- **Pas** de trailer `Co-Authored-By`.
- **Push** : autorise quand Claude le juge utile (decision du 2026-10-29, confirmee le 2026-11-23), TOUJOURS apres l'agent
  `preparateur-push` (verdict STOP = pas de push), jamais `--force`.
- Ne **jamais** commiter le travail en cours de l'utilisateur sans demande explicite.
- **Avant tout commit ou push** (decide le 2026-11-14) : lancer l'agent `controleur-secrets` (depot public), lire son rapport,
  puis seulement commiter, dans un appel suivant. Si le commit touche un `.be` de `data/`, lancer aussi `verificateur-solidification`
  (le vert des bancs ne prouve pas la solidification, panne du 2026-11-13). Un `.py` d'outil : `relecteur-outils-python`
  est recommande (au jugement). **Avant tout push** : agent `preparateur-push` (appele par `/commite pousse`, verdict STOP = pas de push). Les autres agents de `outils_docs/SOUS_AGENTS.md` restent au jugement. Un agent qui
  signale un « bloquant » arrete le commit jusqu'a decision de l'utilisateur.

## Fichiers a ne jamais toucher sans accord

- `data/fs/*.be` — modules en cours d'ecriture par l'utilisateur.
- `.vscode/settings.json` — suivi par git **et** present en amont : toute modif entrera
  en conflit a chaque synchronisation du fork. Les reglages VS Code personnels vont dans le
  profil actif (`%APPDATA%\Code\User\profiles/<id>/settings.json`), pas ici.

## Vigilances de build

Detail et mesures : `outils_docs/environnement/VIGILANCES_BUILD.md`. A chaque session :
- **Jamais un build en parallele de celui de l'utilisateur** ; aucune cible PlatformIO, meme un outil, pendant un build
  (`pio run` purge `.pio/build` si l'empreinte change) : lancer l'outil par `python outils_docs/scripts_python/outils_pc/<outil>.py`.
- IntelliSense ne se reconstruit jamais pendant un build (`platformio-ide.autoRebuildAutocompleteIndex: false`, profil actif).
- Sortie d'un build redirigee : `PYTHONIOENCODING=utf-8`, sinon toute la sortie est perdue ; ne pas corriger le script
  de l'utilisateur pour ca.
- Un build reecrit `platformio_override.ini` et parfois `tasmota/user_config_override.h` (`CFG_HOLDER`) : a commiter.

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
fichier. A interroger par mot-cle avant de toucher a un sujet, a completer apres chaque correction.

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
  **Nouveau plan (2026-11-14)** : lui donner dans son en-tete `objectif:` et `famille:` (et `parent:`, `liens:`, `spec:` si
  utile), sinon il n'est pas range dans l'arbre de l'organigramme (`maintenance/organigramme_plans.py`, regenere par le hook a
  chaque edition d'un plan ; publication en ligne : bouton de la tuile ou `--publier`). Format : `tasks/plans/_FORMAT.md`.

## Carte des documents de ce depot

Aiguillage : `outils_docs/INDEX.md`, importe en tete de ce fichier. **Une fonctionnalite, un outil ou un document
nouveau = UNE ligne dans INDEX.md**, jamais un paragraphe ici. Detail des outils et fonctions (en attendant les guides
de A20) : `outils_docs/CARTE_DOCUMENTS.md`.

Dans les documents durables (ce fichier, `INDEX.md`, `outils_docs/README.md`, `SOLIDIFICATION_BERRY.md`,
`PROTOCOLE_MODBUS.md`, `CARTE_MODULES_BERRY.md`, `.claude/skills`, `agents`, `commands`), renvoyer au code par
`fichier::fonction`, jamais par numero de ligne. Controle : `python outils_docs/scripts_python/maintenance/verifie_references_docs.py`
(code 1 = renvoi faux). Les documents dates (audits, diagnostics, specs, `ANALYSE_*`) gardent leurs numeros.

Regles tirees de la carte, a garder en tete :
- des scripts Python qui s'importent entre eux restent dans le MEME dossier de `outils_docs/scripts_python/` ;
- modifier un mod de `.claude/mods/` = monter `version` dans son `plugin.json`, puis `marketplace update` et `plugin update` ;
- ne JAMAIS emettre de faux push vers 224.3.0.1:4000 depuis un banc : le vrai maitre le traiterait ;
- outils PC : un mot de passe n'est JAMAIS envoye a une page (recopie cote serveur, `***` a l'ecran) ; le flux TCP brut
  du pont serie reste reserve a ce PC ;
- `reprise_limite.py` ne change jamais de compte et ne lance jamais une session en double.
