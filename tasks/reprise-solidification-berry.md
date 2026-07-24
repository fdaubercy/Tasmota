# Reprise — Solidification Berry

> État au 2026-07-16, fin de session. À lire en entier avant de reprendre.
> Document de reprise : le mettre à jour, ne pas en créer un second.

## En une phrase

La solidification est **généralisée à 10 modules du framework** sur le grenier
(`configDevices/Global/Modules`, `diversFonctions`, `gestionFileFolder`,
`globalFonctions`, `webFonctions` + les 3 drivers `controleGeneral/Web/LedTemoin`
refactorés en modules import-ables). **Tout compile au vrai xtensa-gcc, seul ou en lot.**
`modbusFonctions` est **retiré** de la liste (le grenier ne l'utilise pas).
**Il reste à flasher, valider l'import à l'exécution (Q3) et mesurer la RAM.**

---

## LA PROCHAINE ACTION

**Rebuild + flash du grenier**, puis valider Q3 et mesurer la RAM. Le firmware n'est
**plus** celui du 06:58 (qui ne portait que `modbusFonctions`) — il faut reconstruire
avec les 10 modules :

```
pio run -e tasmota32s3-etage2-grenier            # ~2h16
pio run -e tasmota32s3-etage2-grenier -t upload
```

⚠️ **`erase_upload` ne « perd » pas le persist — il le remplace par celui du dépôt**
(`littlefs.bin` joint au flash, `pio-tools/post_esp32.py:385-392` ; FS construit pour
`buildfs`/`uploadfs`/`upload`/`erase_upload`, `pre_utilitaires_platformio.py:500`). Le risque
est un dépôt en retard sur l'état vivant, pas un effacement sec — s'assurer que le
`_persist.json` du dépôt est à jour avant de flasher.

**AVANT le build**, rejouer la chaine rapide sur chaque module (10 s/fichier) —
ne jamais lancer 2h16 a l'aveugle :

```
python outils_docs/scripts_python/solidifie_et_compile_berry.py data/fs/<module>.be
```

Puis console Berry du grenier (`http://192.168.0.44/` → Berry Scripting Console) :

```berry
import introspect
import configModules
introspect.solidified(configModules)          # true = vient bien de la FLASH  <-- LA preuve
import controleWeb
introspect.solidified(controleWeb)            # idem pour un driver refactore
# Verifier les drivers actifs : page web du grenier, LED temoin, controle general.
import path
path.listdir("/")                             # les .be solidifies peuvent rester (import gagne)
```

`introspect.solidified()` (`be_introspectlib.c:140`) retourne `gc_isconst(...)` : vrai si
l'objet est const, donc en flash. C'est la seule vérification qui **demande** l'origine à la VM
au lieu de la déduire de l'absence du fichier.

- **`import` répond + `solidified()==true`** → **Q3 = OUI**, la voie est prouvee.
- **`module_not_found`** → Q3 = NON, et tout le reste est caduc.

**Le gain RAM se mesure ICI** (contrairement a `modbusFonctions`, non utilise sur le
grenier) : ces 10 modules ETAIENT sur le LittleFS du grenier et charges en RAM. Relever
`tasmota.memory("heap_free")` (octets) et un `tasmota.gc()` **avant** (firmware actuel) et
**apres** flash. Attention drivers : verifier que la page web, la LED temoin et le controle
general fonctionnent toujours — le refactor `loadBerryFile`->`import`+`init()` n'a ete
prouve qu'a la COMPILATION, pas a l'execution.

---

## Ce qui est acquis (prouvé, pas supposé)

| Question | Réponse | Preuve |
|---|---|---|
| Q1 — `var x = module(...)` solidifiable ? | **OUI pour la forme**, mais le **nom** ne doit pas porter de slash | préprocesseur xtensa |
| Q2 — `tasmota.add_driver()` au niveau fichier casse ? | **OUI** — cause isolée : c'est le code de **niveau fichier**, pas la classe | avec pied : rc=1 / sans pied : `.h` de 7503 o, 4 méthodes |
| Q3 — `import` sans fichier sur le FS ? | **NON TESTÉ** | ← la prochaine action |
| Q4 — un driver `loadBerryFile` beneficie-t-il de la solidification ? | **NON tel quel** — `loadBerryFile`->`load()` ignore la table native ; il faut le refactorer en module import-able | `gestionFileFolder.be:305` (load) vs `:346` (compileModule) |

**Les 5 prérequis par module** (établis sur `modbusFonctions`, appliqués aux 10 du grenier) :

1. Le fichier listé dans `custom_berry_solidify` (`platformio_tasmota_cenv.ini`) — désormais
   les **10 modules du grenier**, `modbusFonctions` **retiré** de la liste.
2. Directive `#@ solidify:<nom>` en tête (le `<nom>` = module import-able, ou classe→module
   pour un driver).
3. Nom de module **sans slash** — `module("<nom>")`.
4. **0 fonction anonyme** (`nomme_fonctions_berry.py` ; les lambdas inline `/->…` sont
   auto-nommées par le solidifieur, sans collision — vérifié sur `controleWeb`/`webFonctions`).
5. **Globaux du framework stubbés** dans `berry_custom/solidify_all_python.be` — +4 le
   2026-07-16 (`controleGeneral,controleWeb,controleLedTemoin,webserver`).

---

## Les 4 murs rencontrés (et tombés)

Chacun a coûté cher. Ne pas les réintroduire.

1. **`log` non stubbé** → `syntax_error: 'log' undeclared`. Incohérence amont : les
   4 autres créneaux le stubbent, pas `berry_custom`. Corrigé (`1d6950504`).
2. **Aucun `glob_classes`** → `syntax_error: 'Driver' undeclared`. **Aucun `controleXxx.be`
   n'était solidifiable.** Corrigé (`cd41cd76c`).
3. **Le slash du nom de module** → `error: pasting "be_native_module_" and "/" does not
   give a valid preprocessing token`. Corrigé (`4514c4f43`).
4. **15 closures toutes `_anonymous_`** → `error: redefinition of '_anonymous__closure'`.
   **C'est ce qui a fait échouer le build de 2h16.** Corrigé en nommant les fonctions
   (`1bbdac9e9`).

---

## La généralisation aux 10 modules du grenier (2026-07-16)

Fait, et vérifié à la compilation (chaque `.h` compile au xtensa-gcc, seul **et** en lot
de 10 sans collision `_anonymous_` ni global non déclaré). Deux familles, deux recettes :

**1) Les 7 modules import-ables** (`configDevices/Global/Modules`, `diversFonctions`,
`gestionFileFolder`, `globalFonctions`, `webFonctions`) — recette `modbusFonctions` telle
quelle : `nomme_fonctions_berry.py --ecrire`, slash retiré (`module("x")`), directive
`#@ solidify:x`. **Aucun changement d'autoexec** : ils sont charges par `compileModule`
puis `import`, et `import` tente `load_native` (FLASH) avant `load_package` (le `.bec`).

**2) Les 3 drivers** (`controleGeneral`, `controleWeb`, `controleLedTemoin`) — refactor,
car charges par `loadBerryFile`->`load()` qui **ignore la table native** (Q4). Patron :

```berry
#@ solidify:controleXxx
var controleXxx = module("controleXxx")
class CONTROLE_XXX [: Driver] ... end            # inchangee
controleXxx.CONTROLE_XXX = CONTROLE_XXX          # classe publiee dans le module
def controleXxx_init()                           # remplace le code de niveau fichier
    var inst = controleXxx.CONTROLE_XXX()
    global.controleXxx = inst                    # les consommateurs lisent ce global
    tasmota.add_driver(inst)
    # + controleWeb : inst.web_add_handler()
    # + controleLedTemoin : if !inst.config_ok inst = nil end (avant le global)
    return inst
end
controleXxx.init = controleXxx_init
```

Et dans `autoexec.be` du grenier : `loadBerryFile("/controleXxx", ...)` remplace par
`import controleXxx as _ctrl` + `_ctrl.init()`. **Pieges du refactor driver :**
- Le code de niveau fichier (instanciation + `add_driver`) planterait le solidifieur PC
  (`tasmota` stub a nil) : il **doit** passer dans `init()`, jamais rester au niveau fichier.
- Nom du module = nom de l'instance global : pas de collision (bare `controleXxx` = global
  var = l'instance ; `import controleXxx` = table native = le module). Importer avec `as`
  pour ne pas ecraser le placeholder `var controleGeneral = {}` de l'autoexec.
- Ordre : garder `controleGeneral` import+init **avant** `i2c_ads1115` (qui lit
  `controleGeneral.nbIOActivesJSON` au niveau fichier).
- 4 globaux ajoutes au stub `solidify_all_python.be` : `controleGeneral,controleWeb,`
  `controleLedTemoin,webserver`.

**NON PROUVE a l'execution** : tout ceci ne vaut qu'a la compilation. La resolution
`import`->FLASH et le bon fonctionnement des drivers apres refactor = Q3, a valider au flash.

## Décisions ouvertes

**a) Généraliser aux autres modules (`udpFonctions` 7, `discoveryFonctions` 6, …) ?**
Le patron est desormais rode (modules import-ables **et** drivers). **À ne décider
qu'après la mesure RAM sur le grenier puis le garage.**

**b) Le coût des globaux ajoutés — NON MESURÉ.** Les noms intermédiaires
(`modbusFonctions_log`, …) deviennent des globaux Berry. Gratuit pour un module
**solidifié** (le chunk n'est jamais exécuté), mais **coût net** pour un module resté sur
le LittleFS. Convertir les 12 autres sans les solidifier ajouterait 83 globaux sur la RAM
qu'on cherche à économiser. **À mesurer avant de généraliser.**

**c) Le vrai gain se mesure sur le serveur de garage**, seul appareil où
`modbusFonctions.be` est réellement sur le LittleFS et chargé. C'est là que le **piège 4**
mord : il faudra le retirer de son `data_dir` **et** neutraliser
`gestionFileFolder.compileModule("/modbusFonctions")` dans son `autoexec.be:41`, sinon il
sera recompilé en RAM par-dessus la version solidifiée — on paierait deux fois, en silence
et sans aucun signal.

**d) PR chez arendst ?** Les correctifs `log` et `Driver` sont des incohérences amont
(`berry_custom` est le seul créneau à ne stubber ni `log` ni de classes, alors que c'est
celui prévu pour le code utilisateur). Si elles passent, notre divergence retombe à zéro.
Le stub des 9 globaux, lui, nous est propre et reste chez nous.

---

## Méthode : ne plus jamais lancer un build à l'aveugle

Un build fait **2h16**. La chaîne complète se rejoue en **une dizaine de secondes** :

```
python outils_docs/scripts_python/solidifie_et_compile_berry.py
```

Elle enchaîne les 3 étapes de `gen-berry-structures.py` — solidification, `coc`, puis
**compilation** du `.h` avec le vrai `xtensa-esp-elf-gcc`. Les 3 verdicts rendus avant elle
étaient **faux**, tous pour la même raison : conclure sur l'**existence** d'un `.h` sans le
compiler. **Toujours la passer avant de lancer un build.**

Pour convertir un autre module (les 12 restants) :

```
python outils_docs/scripts_python/nomme_fonctions_berry.py data/fs/<module>.be
python outils_docs/scripts_python/nomme_fonctions_berry.py data/fs/<module>.be --ecrire
```

Sans `--ecrire` : simulation seule. Les deux scripts portent des chemins absolus vers ce
poste — à adapter si le dépôt bouge.

Solidifier à la main (court-circuite le pré-script qui vide `embedded/`) :

```bash
cd lib/libesp32/berry_custom
PYTHONPATH=../berry PYTHONUTF8=1 python -m berry_port -s -g solidify_all_python.be
```

---

## Pièges de la chaîne (détail complet dans `outils_docs/SOLIDIFICATION_BERRY.md`)

- La ligne `Berry solidification: …` d'un build **ne prouve rien** (piège 10).
- `grep Parsing:` ne renvoie **jamais** rien : la ligne est filtrée
  (`gen-berry-structures.py:301-312`) — piège 11.
- Un `.h` de **379 octets** = vide, avec `rc = 0` et zéro message. Toujours comparer la
  taille à l'ordre de grandeur attendu (~244 000 o pour `modbusFonctions`).
- **Un commentaire n'est pas inerte** : `addEntryToModtab()` cherche `module("…")` par
  regex sur le fichier **entier**, commentaires compris, et retient la **première**
  occurrence. Un exemple en commentaire a régénéré un `modules.h` invalide et cassé un
  build (`34b6756a4`).
- `cleanFolder()` (pré-script, **inconditionnel**) vide `embedded/`, vide `solidify/` et
  réinitialise `modules.h` à **chaque** build. Déposer un fichier à la main est sans effet ;
  éditer `modules.h` à la main est écrasé.

---

## Sur un AUTRE poste (nouveau clone)

**Voir `CLAUDE.md`, section « MONTER UN NOUVEAU POSTE ».** En résumé :

1. **VS Code** → Settings Sync, en **cochant `Profiles`** (sans quoi les réglages `C_Cpp`
   qui corrigent le `PermissionError` n'arrivent jamais : ils vivent dans le profil actif,
   pas dans le profil par défaut).
2. **PlatformIO** → rien à faire. Les 16,6 Go se réinstallent au premier `pio run`.
3. **Le filet** → `python outils_docs/scripts_python/corrige_reglages_vscode.py --verifier`
   si le `PermissionError` intermittent sur `tasmota.ino.cpp` réapparaît.

Le reste est dans le dépôt. Les outils Python n'ont **aucun chemin en dur** : racine du
dépôt, PlatformIO et toolchain xtensa sont tous déduits.

## État du dépôt

- **8 commits locaux non poussés.** Le fork est à jour avec arendst (0 de retard).
- Modifiés en permanence par les builds, sans intérêt à committer :
  `tasmota/tasmota_defines_for_berry.{be,h}`, `tasmota/user_config_override.h`
  (CFG_HOLDER), `lib/libesp32/berry_custom/src/modules.h`, `.claude-flow/`.
- Synchroniser le fork : `python outils_docs/scripts_python/synchronise_fork_tasmota.py`
  (merge, jamais de force-push ; le journal va dans `outils_docs/HISTORIQUE_SYNCHRO_FORK.md`).

## Documents liés

- `docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md` — le verdict, **avec
  sa correction en tête** (une première version affirmait à tort que la convention était
  solidifiable telle quelle).
- `outils_docs/SOLIDIFICATION_BERRY.md` — le mécanisme, la vérification (§5), les
  paramètres (§6), les 11 pièges.
- `tasks/lessons.md` — les leçons, dont les 3 récidives du même piège de vérification.
- `CLAUDE.md` — règles du dépôt (pas de graphify, commits en français, sans accents).
