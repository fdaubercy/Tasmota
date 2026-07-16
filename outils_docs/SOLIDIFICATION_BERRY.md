# La solidification Berry — comment ça marche, et les pièges

> Statut au 2026-07-15 : les mécanismes décrits ici sont **lus dans le code de ce dépôt**, chemin et
> ligne à l'appui. Ce qui reste **à vérifier expérimentalement** est signalé par ⏳ (phase 1 en cours,
> cf. `docs/superpowers/specs/2026-07-15-solidification-berry-design.md`).
>
> Les §5 à §7 (vérifier, paramètres, ce qui n'est pas solidifié) et les pièges 10-11 ont été établis
> par **observation d'un build réel** le 2026-07-15 (env `tasmota32s3-etage2-grenier`), pas par lecture.
>
> **Pressé ?** Trois choses à savoir : la solidification est **active par défaut** à chaque build (§6) ;
> nos modules de `data/fs/` ne sont **jamais** solidifiés (§7) ; et la ligne `Berry solidification: …`
> **ne prouve rien** — la preuve est `output_files` (§5, piège 10).

## 1. Le malentendu à dissiper d'abord

Il y a **trois** états possibles du code Berry, pas deux :

| | Le bytecode est fabriqué | Il vit | Coût RAM |
|---|---|---|---|
| `.be` | sur l'ESP32, au boot | RAM/PSRAM | plein + temps de compilation au boot |
| `.bec` | sur l'ESP32, une fois, puis relu | RAM/PSRAM | **plein** |
| **solidifié** | **sur le PC, à la compilation** | **flash (segment read-only)** | **zéro** |

**`.bec` n'est PAS de la solidification.** C'est le piège n°1.

`gestionFileFolder.compileModule()` / `loadBerryFile()` compilent `.be` → `.bec` et suppriment le `.be`.
On gagne de la place sur le LittleFS et du temps de boot. **On ne gagne pas un octet de RAM** : le
bytecode d'un `.bec` est chargé en mémoire exactement comme celui d'un `.be`.

La solidification, elle, ne produit pas du bytecode mais **du C**. Le code devient des structures
`const` compilées dans le firmware, lues directement depuis la flash. Extrait réel
(`lib/libesp32/berry_tasmota/src/solidify/solidified_driver_class.h`) :

```c
/* Solidification of driver_class.h */
/* Generated code, don't edit */
#include "be_constobj.h"
extern const bclass be_class_Driver;
be_local_closure(class_Driver_add_cmd,   /* name */
  be_nested_proto(7, /* nstack */ 3, /* argc */ ...
```

Il n'y a plus rien à allouer : l'objet **est** dans le binaire.

## 2. Où ça se passe

### Le créneau utilisateur : `lib/libesp32/berry_custom/`

Dossier fourni par arendst **exactement pour ça**, et **vide** dans notre dépôt
(`src/embedded/.keep`). Il est déjà listé dans `SOLIDIFY_DIRS`
(`pio-tools/gen-berry-structures.py:249`), aux côtés de `berry_tasmota`, `berry_matter`,
`berry_animation`, `lv_binding_berry`, `lv_haspmota`.

```
lib/libesp32/berry_custom/
├── solidify_all_python.be     <- le solidifieur de ce dossier
├── src/
│   ├── .gitignore             <- ignore embedded/* et solidify/*
│   ├── embedded/              <- ON DEPOSE LES .be ICI
│   ├── solidify/              <- les .h generes atterrissent ICI
│   ├── be_custom_module.c     <- porte le marqueur /*solidify*/
│   ├── modules.h              <- CUSTOM_NATIVE_MODULES / CUSTOM_NATIVE_CLASSES
│   └── berry_custom.h         <- force-inclus par xdrv_52_9_berry.ino:42
```

### La chaîne de build

`platformio_tasmota32.ini:54-56` enchaîne trois post-scripts, dans cet ordre :

1. **`dump-defines.py`** — invoque le préprocesseur C++ croisé en mode `-E -dM` et écrit
   `tasmota/tasmota_defines_for_berry.h` (~3 200 `#define`, gitignoré, régénéré à chaque build).
   Pourquoi : *« For solidified code to be correct it must know which Tasmota features are compiled
   into the firmware »* — le solidifieur doit voir les mêmes `USE_*` et `D_*` que le compilateur C++.
2. **`gen-berry-defines.py`**
3. **`gen-berry-structures.py`** — pour chaque dossier de `SOLIDIFY_DIRS`, exécute son
   `solidify_all_python.be` via `berry_port` (réimplémentation Python de la VM Berry tournant **sur le
   PC**), et écrit `src/solidify/solidified_*.h`.

⚠️ **`post:` ne veut pas dire « après la compilation ».** En PlatformIO, un script `post:` s'exécute
quand l'environnement est chargé, donc **avant** que les sources soient compilées. Concrètement : le
verdict de solidification tombe dans les premières minutes d'un `pio run`, pas à la fin. La doc amont
l'explique : `$CXX` n'est le vrai cross-compilateur qu'après le passage du platform builder.

### La directive

Repérée par la regex `#@\s*solidify:([A-Za-z0-9_.,]+)` (`solidify_all_python.be`) :

```berry
#@ solidify:Driver
class Driver
```

Second champ optionnel : `weak` (chaînes faibles) → `#@ solidify:MaClasse,weak`.

### Le rattachement au firmware

Trois fichiers, à modifier à la main :

```c
// be_custom_module.c — remplacer le marqueur /*solidify*/ par :
#include "solidify/solidified_monModule.h"

// modules.h — declarer le symbole :
#define CUSTOM_NATIVE_MODULES     &be_native_module(monModule),
#define CUSTOM_NATIVE_CLASSES
```

`be_modtab.c:240` et `:387` consomment ces deux macros. `berry_custom.h` est force-inclus par
`xdrv_52_9_berry.ino:42`.

## 3. Quand solidifier — et quand surtout pas

**La solidification est un outil de PRODUCTION, pas de développement.**

Elle tourne à la compilation, sur le PC. Donc **chaque modification impose un rebuild complet et un
reflash**. On perd exactement ce que le framework `data/fs` apporte : éditer un `.be`, le téléverser,
`BrRestart`, tester — quinze secondes.

| Situation | Verdict |
|---|---|
| Module en cours d'écriture ou de débogage | **Ne pas solidifier.** Laisser dans `data/fs/`. |
| Module stable, volumineux, qui pèse sur la RAM | **Candidat.** Ex. `modbusFonctions.be` (79 Ko). |
| Module dont l'activation varie d'un appareil à l'autre | Attention : un module solidifié est dans le firmware **sans condition**. Sans impact ici (un firmware par appareil), mais la granularité `_persist.json` ne s'y applique plus. |

## 4. Les pièges

### Piège 1 — Croire que `.bec` économise de la RAM

Voir §1. C'est le plus coûteux, parce qu'il donne l'illusion du travail fait.

### Piège 2 — Le solidifieur EXÉCUTE le code sur le PC

Dans `solidify_all_python.be` :

```berry
var compiled = compile(src)
compiled()      # run the compile code to instanciate the classes and modules
```

Il ne se contente pas de lire le fichier : **il l'exécute**, sur le PC, où `tasmota`, `gpio`, `light`,
`webclient` n'existent pas — le script les stubbe à `nil` :

```berry
var globs = "path,ctypes_bytes_dyn,tasmota,ccronexpr,gpio,light,webclient,load,MD5,lv,..."
for g:string2.split(globs, ",")
  global.(g) = nil
end
```

⏳ **Conséquence attendue (Q2, en cours de vérification)** : tout appel `tasmota.*` **au niveau
fichier** casse la solidification. Ça vise directement nos `controleXxx.be`, dont la garde
d'activation en pied appelle `tasmota.add_driver()`. Le corps des fonctions, lui, n'est pas exécuté —
seul le niveau fichier compte.

### Piège 3 — La directive résout depuis `global`

```berry
var o = global
for subname : string2.split(object_name, '.')
  o = o.(subname)
```

L'objet visé par `#@ solidify:` doit être **global**. Chez arendst, `class Driver` déclarée au niveau
fichier est bien globale.

⏳ **Notre convention `var xxxFonctions = module("/xxxFonctions")` déclare un `var` local au fichier**
— probablement pas atteignable (Q1, en cours de vérification). Si confirmé, la forme des
`xxxFonctions.be` devra être adaptée pour être solidifiable.

### Piège 4 — Le `.be` qui reste sur le LittleFS coûte du BOOT, pas de la RAM

> ⚠️ **Corrigé le 2026-07-16.** Une version antérieure de ce piège affirmait qu'un module à
> la fois solidifié et présent sur le FS faisait « payer la RAM qu'on croyait économiser, en
> silence ». **C'est faux**, et l'erreur venait d'une supposition jamais vérifiée dans le code.

**Ce que fait réellement `import`** (`lib/libesp32/berry/src/be_module.c:282-288`) :

```c
int be_module_load_nocache(bvm *vm, bstring *path, bbool nocache)
{
    int res = BE_OK;
    if (!load_cached(vm, path)) {          /* 1. deja charge ?        */
        res = load_native(vm, path);       /* 2. module NATIF         */
        if (res == BE_IO_ERROR)
            res = load_package(vm, path);  /* 3. fichier sur le FS    */
```

**Le natif gagne.** Le fichier n'est cherché que si aucun module natif ne répond. Un `.be`
qui traîne à côté d'un module solidifié n'est donc **jamais chargé** : aucune RAM en double.

**Le coût résiduel est réel, mais ailleurs.** `autoexec.be` appelle
`gestionFileFolder.compileModule("/monModule", <activation>)`, qui compile le `.be` en `.bec`
via `tasmota.compile()` — indépendamment de tout `import`. Sur un appareil où le module est
solidifié, c'est **du temps de boot et des écritures flash pour rien**.

**Donc : sauter le `compileModule()` d'un module solidifié est une OPTIMISATION, pas une
condition de correction.** Le firmware fonctionne correctement dans les deux cas.

⏳ Non mesuré : ce que coûte exactement `tasmota.compile()` (il écrit le `.bec` ; reste à
établir s'il charge quoi que ce soit en RAM au passage).

### Piège 4 bis — Le nom passé à `module()` ne sert PAS à trouver le fichier

Corollaire du mécanisme ci-dessus, et il rassure. `load_package()` construit un chemin de
**fichier** à partir du nom d'`import` (`import monModule` → cherche `monModule.be`). Le nom
passé à `module("...")` dans le fichier n'intervient **que** pour la table native.

Consequence pratique : retirer le slash d'un `module("/monModule")` — obligatoire pour
solidifier, cf. §1 du verdict — **n'a aucun effet** sur les appareils qui chargent depuis le
LittleFS. Le même fichier sert les deux mondes.

### Piège 5 — `src/.gitignore` ignore `embedded/*` et `solidify/*`

```
_temp*
solidify/*
embedded/*
```

Un `.be` déposé là n'est **ni versionné, ni vu par `genere_sauvegarde_tasmota.py`** (qui travaille au
diff git). Bien pour des copies temporaires générées au build — **dangereux** si on y met la seule
copie d'une source. Garder `data/fs/` comme source de vérité.

### Piège 6 — `ls` ment

`solidify_all_python.be` fait `clean_directory(prefix_out)` à chaque passage, mais **préserve les
fichiers commençant par `.`** :

```berry
if f[0] == '.'  continue end    # ignore files starting with `.`
```

Donc `.keep` survit. Et comme `ls` sans `-a` masque les fichiers cachés, un `ls src/solidify/` qui ne
renvoie **rien** ne veut pas dire « le dossier est vide » : il veut dire « aucun `.h` généré, mais
`.keep` est toujours là ». Toujours `ls -a`.

### Piège 7 — Un build réécrit des fichiers suivis

Rien à voir avec Berry, mais ça mord quand on multiplie les builds de test :
`pre_utilitaires_platformio.py` appelle `increment_config_holder()` (réécrit
`tasmota/user_config_override.h`) et `adapteParametresPlatformio_override()` (réécrit
`platformio_override.ini`, avec un `.bak`). **Sauvegarder ces deux fichiers avant une série de builds
expérimentaux**, surtout s'ils portent du travail non commité.

### Piège 8 — `UBE_BERRY_DEBUG_GC` : coquille amont, mais cohérente

`user_config_override.h:615` déclare `UBE_BERRY_DEBUG_GC` (pour `USE_`). C'est une faute de frappe
amont — **mais elle est cohérente avec son site d'usage** (`xdrv_52_9_berry.ino:297`). L'option
fonctionne. **La « corriger » en `USE_BERRY_DEBUG_GC` la casserait.**

### Piège 9 — Mesurer le coût du debug plutôt que celui du code

`USE_BERRY_DEBUG` (actif depuis le 2026-07-15) coûte **+8 % sur le code compilé** — or c'est justement
ce qu'on cherche à réduire. Le recommenter avant toute campagne de mesure sérieuse.

### Piège 10 — La ligne `Berry solidification: …` NE prouve RIEN

**C'est le piège de vérification n°1**, constaté en direct le 2026-07-15.

Un build affiche :

```
Berry solidification: lib\libesp32\berry_custom\solidify_all_python.be
```

Cette ligne dit seulement que **le script a été lancé**. Elle est imprimée par
`gen-berry-structures.py:280` *avant* toute exécution. Avec un `src/embedded/` vide, le script nettoie
un dossier vide, liste zéro fichier et écrit zéro sortie — **la ligne s'affiche à l'identique**.

Mesuré ce jour sur `tasmota32s3-etage2-grenier` :

| Module | `output_files` du cache | Réalité |
|---|---|---|
| `berry_tasmota` | 34 | 34 `solidified_*.h` produits |
| `berry_custom` | **0** | ligne affichée, **rien produit** |

La preuve est `output_files` et les `.h`, jamais la ligne de log. Voir §5.

**Corollaire non intuitif** : un module qui ne produit rien **ne peut jamais être mis en cache**.
`gen-berry-structures.py:177-179` dit « aucune sortie enregistrée → il faut relancer ». Donc
`berry_custom` vide est **relancé à chaque build, éternellement, pour ne rien faire**, et sa ligne
apparaît toujours en clair — alors qu'un module qui a produit des `.h` affichera `(cached, skipped)`.
Voir cette ligne à chaque build n'est donc pas le signe que ça marche : c'est le signe que c'est vide.

### Piège 11 — Ne pas grepper `Parsing:` : la ligne est filtrée

`solidify_all_python.be:55` imprime bien `Parsing: <fichier>` pour chaque `.be` traité. Mais
`gen-berry-structures.py:301-312` **filtre explicitement** cette sortie avant de la relayer :

```python
if stripped.startswith("Parsing:"):
    continue
if stripped.startswith("Skipping:"):
    continue
```

Seul ce qui n'est **pas** du bavardage de routine (erreurs, warnings, tracebacks) remonte. Un
`pio run | grep -i parsing` ne renverra donc **jamais rien**, y compris quand la solidification
fonctionne parfaitement — et on conclut à tort à un échec.

## 5. Vérifier qu'une solidification a vraiment eu lieu

Par ordre de force de preuve. Les niveaux 1 et 2 sont les seuls qui comptent au quotidien.

| # | Ce qu'on regarde | Où | Ce que ça prouve |
|---|---|---|---|
| 0 | `Berry solidification: <script>` | log du build | Le script a tourné. **Rien de plus** (piège 10). |
| 1 | `solidified_*.h` présents, horodatés de ce build | `lib/libesp32/<module>/src/solidify/` | Des sorties ont été écrites. Utiliser `ls -a` (piège 6). |
| 2 | `output_files` non vide | `.pio/build/<env>/berry_solidify_cache/<module>.json` | Le build a **enregistré** ces sorties. |
| 3 | Symboles `be_class_X` / `be_module_X` | `nm` sur le `.elf` | Le code est **réellement dans le firmware**. |
| 4 | `import x` réussit alors que `path.listdir("/")` ne montre pas le fichier | console Berry de l'appareil | Preuve de bout en bout : c'est la version solidifiée qui sert. |

Niveaux 1 et 2 :

```bash
ls -a lib/libesp32/berry_custom/src/solidify/
cat .pio/build/<env>/berry_solidify_cache/berry_custom.json   # champ output_files
```

Niveau 3 (Windows, après l'édition de liens) :

```powershell
& "$env:USERPROFILE\.platformio\packages\toolchain-xtensa-esp-elf\bin\xtensa-esp-elf-gcc-nm.exe" `
  .pio\build\<env>\firmware.elf | Select-String 'be_class_|be_module_'
```

## 6. Les paramètres

| Paramètre | Où | Effet |
|---|---|---|
| `-DDISABLE_BERRY_SOLIDIFY` | `build_flags` | **Désactive** l'étape 1 (`gen-berry-structures.py:242`). Utile pour itérer sur du C/C++ sans retoucher au Berry ; le `coc` de l'étape 2 tourne quand même. |
| `PYTHONUTF8=1` | posé d'office | `gen-berry-structures.py:264` le force pour le sous-processus : sans lui, la cp1252 de Windows échoue à lire certains `.be` (notamment `berry_animation`). Ne pas le retirer. |
| `#@ solidify:Nom` | dans le `.be` | Désigne l'objet à solidifier. Résolu **depuis `global`** (piège 3). |
| `#@ solidify:Nom,weak` | dans le `.be` | Idem, avec chaînes faibles. |
| `USE_SOLIDIFY_BERRY` | *(n'existe pas encore)* | Paramètre par env envisagé en phase 2, **conditionné au verdict de la phase 1**. Ne pas le chercher aujourd'hui. |

**Il n'y a aucun paramètre à activer pour que la solidification tourne** : elle est active par défaut
à chaque build, sur les six dossiers de `SOLIDIFY_DIRS`. La question n'est jamais « est-elle
activée ? » mais « a-t-elle quelque chose à solidifier ? ».

## 6 bis. Solidifier pour CERTAINS firmwares seulement

Question posée le 2026-07-16 : *comment garder les scripts sur le FS pour certains modules,
et solidifier pour d'autres ?*

**Réponse : c'est déjà le cas, et ça se règle tout seul.** Trois faits s'emboîtent.

**1. `custom_berry_solidify` est une option PAR ENVIRONNEMENT.**

```ini
[env:tasmota32s3-etage2-grenier]           ; solidifie
custom_berry_solidify   =   data/fs/modbusFonctions.be

[env:tasmota32p4-garage-serveur-modbus]    ; reste en fs
; rien a ajouter
```

**2. `import` prefere le natif au fichier** (piege 4). Le firmware qui embarque le module
solidifie utilise la version en flash ; celui qui ne l'embarque pas retombe sur le `.be` du
LittleFS. **Le mecanisme se selectionne lui-meme.**

**3. Le nom de `module()` ne sert pas a trouver le fichier** (piege 4 bis). La forme adaptee
pour la solidification reste donc parfaitement utilisable en mode FS.

**Conclusion : meme source, meme LittleFS, meme `autoexec.be`.** Un seul fichier `.be` sert
les deux mondes ; c'est l'env qui tranche, firmware par firmware.

### Ce qui monte sur le LittleFS de chaque appareil

À savoir, parce que c'est contre-intuitif : **tous les appareils portent TOUS les modules**.

`pre_utilitaires_platformio.py` (`copy_fs_image`, l.469) copie, **au moment de l'upload
seulement** (`buildfs`/`uploadfs`/`upload`/`erase_upload`), le contenu de `data/fs/` **à plat**
dans le `data_dir` de l'appareil, construit `littlefs.bin` avec, puis `remove_backup_data()`
(l.532) efface les copies — `Global.liste_fichiers_exclus` etant la liste des fichiers
d'origine à conserver.

`Global.dossiers_a_copier = ["fs", "json", "sd"]` (l.69) est **en dur** : aucune selection par
env a ce niveau. D'ou un `littlefs.bin` de ~11 Mo partout.

C'est donc l'`autoexec.be` de chaque appareil qui decide ce qui est **charge**, via
`compileModule("/monModule", <activation lue dans _persist.json>)`.

### Eviter la compilation au boot : rien a faire (depuis le 2026-07-16)

`copy_fs_image()` (`pre_utilitaires_platformio.py`) lit desormais `custom_berry_solidify`
de l'env courant et **ne copie pas** ces fichiers sur le LittleFS. Comme le `.be` est absent,
`gestionFileFolder.compileModule()` devient un no-op silencieux :

```berry
# gestionFileFolder.be:360-379
if path.exists(chemin + ".be")
    ...compile...
else return true          # <-- fichier absent : ne fait RIEN
end
```

**Aucune ligne de Berry a modifier, aucun `autoexec.be` a retoucher.** Une seule declaration
commande toute la chaine :

```ini
custom_berry_solidify   =   data/fs/modbusFonctions.be
```

1. le module entre dans le firmware (pre-script)
2. son `.be` ne monte pas sur le LittleFS (`copy_fs_image`)
3. `compileModule` ne fait rien (fichier absent)
4. `import` trouve le natif (`be_module.c:286`)

Verifie sur un vrai `pio run -t buildfs` : `modbusFonctions.be` saute, `udpFonctions.be`
(non solidifie) est copie, l'image se construit.

⚠️ **Consequence a connaitre** : le module n'est plus **du tout** sur le FS de cet appareil.
Plus de boucle courte « editer le `.be` → televerser → `BrRestart` » pour lui : toute
modification impose un rebuild + reflash. C'est le prix de la solidification (§3), et c'est
pourquoi on ne solidifie qu'un module **fige**.

## 7. Ce qui n'est PAS solidifié — et ne le sera jamais tout seul

Point de vigilance principal pour ce dépôt, parce qu'il est contre-intuitif.

Les modules de `data/fs/` (`controleModbus.be`, `controleUDP.be`, `udpFonctions.be`, …) sont
téléversés sur le **LittleFS** et chargés à l'exécution par `autoexec.be`. **Aucun build ne les
solidifiera**, quel que soit le nombre de `Berry solidification:` vus passer : `solidify_all_python.be:27`
ne lit **que** `src/embedded/`.

Les 34 `solidified_*.h` régénérés à chaque build sont ceux d'**arendst** (`berry_tasmota`), pas les
nôtres. Voir un build « solidifier » abondamment ne dit donc rien de notre propre code.

Pour qu'un de nos modules soit solidifié, il faut l'amener dans `berry_custom/src/embedded/` **et**
qu'il soit solidifiable — ce que la phase 1 doit trancher (Q1/Q2, §4 pièges 2 et 3).

## 8. Méthode recommandée

1. **Développer dans `data/fs/`.** Boucle courte, `.be` → téléverser → `BrRestart`.
2. **Mesurer avant de solidifier.** `ReglageGlobal logLevel 4` donne gratuitement les lignes
   `BRY: GC from X to Y bytes` (`xdrv_52_9_berry.ino:290-293`, aucun flag requis). `tasmota.gc()`
   avant/après une opération donne son coût réel.
3. **Ne solidifier qu'un module figé**, et un seul à la fois.
4. **Vérifier le gain**, pas le supposer : `tasmota.gc()` avant/après, et `path.listdir("/")` pour
   confirmer que le fichier n'est plus sur le FS.

## 9. Références

- Créneau utilisateur : `lib/libesp32/berry_custom/`
- Solidifieur : `lib/libesp32/berry_custom/solidify_all_python.be`
- Chaîne de build : `platformio_tasmota32.ini:54-56`, `pio-tools/gen-berry-structures.py`
- Defines : `lib/libesp32/berry/TASMOTA_DEFINES_FOR_BERRY.md`, `pio-tools/dump-defines.py`
- Exemple amont : `lib/libesp32/berry_tasmota/src/embedded/driver_class.be` →
  `src/solidify/solidified_driver_class.h`
- Enregistrement : `lib/libesp32/berry/default/be_modtab.c:240` et `:387`
- Doc officielle : <https://tasmota.github.io/docs/Berry/>
- Spec et verdict : `docs/superpowers/specs/2026-07-15-solidification-berry-design.md`
