# Solidification Berry — verdict de la phase 1

Date : 2026-07-15
Env de test : `tasmota32s3-etage2-grenier`
Methode : solidifieur lance **a la main**, sans build complet (voir « Ecart de methode »).

> **Verdict en une ligne : phase 2 = GO, mais au prix d'une modification de nos 15
> modules.** Le parametre a ecrire **existe deja en amont** (`custom_berry_solidify`) ;
> en revanche notre convention `module("/x")` **doit perdre son slash**.

> ## ⚠️ CORRECTION du 2026-07-15, apres coup
>
> **Une premiere version de ce verdict affirmait que nos `xxxFonctions.be` etaient
> « solidifiables tels quels ». C'est FAUX, et l'erreur merite d'etre expliquee.**
>
> Elle venait d'avoir conclu sur la seule existence du `.h` genere, **sans jamais le
> compiler**. Or le nom de module `/modbusFonctions` produit du C invalide :
>
> ```
> $ xtensa-esp-elf-gcc -E test_macro.c
> be_native_module_autoconf;              <- amont, nom nu : OK
> be_native_module_/modbusFonctions;      <- nous :
> error: pasting "be_native_module_" and "/" does not give a valid preprocessing token
> ```
>
> `berry.h:376` (`#define be_native_module(name) be_native_module_##name`) et
> `be_constobj.h:272-277` (`static const bmodule m_lib##_c_name`) collent le nom du
> module dans un identifiant C. Un `/` ne peut pas en faire partie.
>
> C'est le **piege 10 un cran au-dessus** : un `.h` genere ne prouve pas un `.h`
> valide, exactement comme une ligne `Berry solidification:` ne prouve pas une
> solidification. La lecon vaut d'etre retenue : **ne jamais valider un artefact de
> compilation sans le compiler**.

---

## Ecart de methode — a lire en premier

**Le plan ne pouvait pas fonctionner tel qu'ecrit.** Il prevoyait de deposer un `.be`
dans `lib/libesp32/berry_custom/src/embedded/` puis de lancer `pio run`. Or
`pio-tools/solidify-from-url.py` est un **pre-script** (`platformio_tasmota32.ini:52`)
et sa fonction `cleanFolder()` (l.33-47) vide `embedded/`, vide `solidify/` et
reinitialise `modules.h` — **inconditionnellement, a chaque build** (l.152 :
`cleanFolder() # always clean up this folder`).

Constate en direct : le premier build a supprime le fichier de test avant que le
solidifieur ne s'execute. Resultat : zero sortie, zero erreur, `exit 0` — un faux
« Q1 = NON » parfaitement credible.

La tache 4 du plan (editer `be_custom_module.c` et `modules.h` a la main) etait
condamnee pour la meme raison : `cleanFolder()` reecrit `modules.h` a chaque build.

**Ce qui marche** : lancer le solidifieur directement, ce qui court-circuite le
pre-script. C'est ce que fait le post-script `gen-berry-structures.py`, qui ne nettoie
rien :

```bash
cd lib/libesp32/berry_custom
PYTHONPATH=../berry PYTHONUTF8=1 python -m berry_port -s -g solidify_all_python.be
```

Verdict rendu en secondes, sans build. **Aucun appareil n'a ete flashe** : Q3 n'a pas
eu besoin de l'etre (voir plus bas).

---

## Q1 — `var x = module("/x")` est-il atteignable par `#@ solidify:` ?

**Reponse : OUI.** Hypothese de la spec (« NON ») **refutee**.

Preuve : `solidified_testFonctions.h`, 6027 octets, contenant
`be_local_module(/testFonctions, ...)`, deux fonctions solidifiees, et le membre `log`
exporte en closure (`{ be_ckey(log, -1), BE_CLOSURE, be_kv_closure(...) }`).

Le raisonnement de la spec — « un `var` au niveau fichier est local au chunk compile,
donc invisible depuis `global` » — est faux : en Berry, un `var` au niveau fichier
**est** global. Le resolveur (`solidify_all_python.be:78-90`) le trouve.

**Consequence, corrigee :** la **forme** (`var x = module(...)` au niveau fichier) est
bien solidifiable — le resolveur trouve le `var`, et c'est ce que Q1 demandait. Mais le
**nom** `/xxxFonctions` ne l'est pas : il finit dans un identifiant C, ou le `/` est
illegal (voir la correction en tete). Il faut donc **retirer le slash** :

```berry
var modbusFonctions = module("modbusFonctions")   # et non module("/modbusFonctions")
```

Cela concerne **15 de nos 30 modules** (un seul est deja sans slash).

**Le slash est-il utile aujourd'hui ?** Non : nos modules font `import modbusFonctions`
(sans slash) et `import` charge le **fichier** du LittleFS ; le nom passe a `module()`
n'est que cosmetique. Une fois solidifie, en revanche, `import modbusFonctions` cherche
dans la table native **par nom** — et `/modbusFonctions` n'y repondrait pas. Le slash
gene donc deux fois : compilation C **et** resolution de l'import.

⏳ **A verifier avant de toucher aux 15 modules** : que le retrait du slash n'a aucun
effet sur l'appareil (`gestionFileFolder.compileModule()` recoit des chemins avec slash,
ce qui est un usage distinct).

Variante classe testee : non — inutile, l'hypothese de Q1 etait deja refutee.

### Mais un obstacle reel, sans rapport avec Q1

Le premier essai est mort sur :

```
syntax_error: string:25: 'log' undeclared (first use in this function)
```

`solidify_all_python.be` de `berry_custom` **ne stubbait pas `log`**, alors que
`berry_tasmota`, `berry_matter`, `berry_animation` et `lv_haspmota` le font tous.
Incoherence amont, frappant justement le creneau prevu pour le code utilisateur —
celui qui logue. **Corrige** (commit `1d6950504`), verifie en rejouant le cas d'echec
exact.

---

## Q2 — un `tasmota.add_driver()` au niveau fichier casse-t-il le solidifieur ?

**Reponse : OUI, ca casse.** Hypothese de la spec **confirmee**, et cause isolee.

| Fichier teste | Resultat |
|---|---|
| `controleTest.be` **avec** le bloc de pied | `type_error: 'nil' value is not callable`, exit 1, aucune sortie |
| `controleTest.be` **sans** le bloc de pied | `solidified_controleTest.h`, **7503 octets**, exit 0 |

Le `.h` produit contient `be_local_class(CONTROLE_TEST, ...)` et **les quatre methodes**
solidifiees : `init`, `web_sensor`, `every_second`, `json_append`.

**Le fait decisif : `init()` contient `tasmota.add_cmd(...)` et se solidifie sans
probleme.** Le corps d'une fonction est *compile*, jamais *execute*, pendant la
solidification. Seul le code de **niveau fichier** s'execute — ou `tasmota` vaut `nil`.

Le `try/except` du pied ne sauve rien : `tasmota.add_cmd()` leve dans `init()`,
le handler `except` appelle `log(...)` — nil lui aussi — et l'erreur du gestionnaire
d'erreur, elle, n'est plus rattrapee.

**Consequence pour la phase 2 : la garde d'activation doit sortir du niveau fichier.**
La classe, elle, n'a pas besoin d'etre touchee.

### Second obstacle, decouvert au passage

```
syntax_error: string:15: 'Driver' undeclared (first use in this function)
```

`berry_custom` n'avait **aucun `glob_classes`**, alors que `berry_tasmota` declare
`glob_classes = "I2C_Driver"` et fabrique des classes vides via
`compile(f"class {g} end")()`. Une classe ne peut pas etre stubbee a `nil` : `class X :
Driver` exige une vraie classe. **En l'etat, aucun `controleXxx.be` n'etait
solidifiable, quelle que soit sa forme.** Corrige de la meme facon.

---

## Q3 (bloquante) — `import` trouve-t-il le module solidifie sans fichier sur le FS ?

**Reponse : non teste — et la question ne se pose plus dans ces termes.**

La spec supposait un rattachement **manuel** (editer `be_custom_module.c` et
`modules.h`). C'est faux : `solidify-from-url.py` fait ce travail **automatiquement**
via `addEntryToModtab()` (l.50-97) et `addHeaderFile()` (l.99-112), qui detectent seuls
si le fichier declare un `module()` ou une `class`, ecrivent `modules.h` et enregistrent
le symbole dans `be_modtab.c`.

Q3 reste a verifier **sur appareil**, mais par le chemin officiel (`custom_berry_solidify`
+ build + flash), pas par l'edition manuelle que la spec imaginait.

---

## La decouverte principale : le parametre existe deja

La spec voulait creer `USE_SOLIDIFY_BERRY` et une fonction `copy_berry_solidify()`.
**Tout cela existe en amont**, sous le nom `custom_berry_solidify`
(`solidify-from-url.py:154`) : une option PlatformIO **par environnement**.

```ini
[env:tasmota32s3-etage2-grenier]
custom_berry_solidify = data/fs/modbusFonctions.be
```

Le pre-script copie le fichier dans `embedded/`, genere `modules.h`, enregistre le
module dans `be_modtab.c`, et le solidifieur fait le reste. **Il n'y a rien a ecrire.**

### Sauf que ce mecanisme etait casse dans notre fork

`pio-tools/solidify-from-url.py` avait diverge et perdu les correctifs d'arendst :
les lignes definissant `src_path` avaient disparu, celles qui l'utilisent etaient
restees (`NameError` sur tout fichier local) ; `BERRY_EXECUTABLE` etait lue hors de sa
portee. Invisible tant que `custom_berry_solidify` n'est pas defini : le `except: pass`
(l.155) avalait tout. **Corrige** en reprenant la version amont (commit `260991cd2`) —
la divergence avec arendst sur ce fichier est retombee a zero.

---

## Verdict

**Phase 2 : GO** — mais sa portee change du tout au tout.

**Regle de selection des fichiers a retenir pour la phase 2 :**

| Type | Solidifiable ? | Condition |
|---|---|---|
| `xxxFonctions.be` (singleton `module()`) | **OUI** | **retirer le slash** : `module("x")` et non `module("/x")` — 15 modules concernes ; + la directive `#@ solidify:` |
| `controleXxx.be` (`class : Driver`) | **OUI** | deplacer la garde d'activation hors du niveau fichier ; + la directive `#@ solidify:` |

**Trois prerequis, dont aucun n'etait dans la spec :**

1. `custom_berry_solidify = data/fs/<module>.be` dans l'env (prouve : le pre-script
   trouve le fichier local et le copie).
2. **La directive `#@ solidify:<nom>` en tete du module.** Aucun de nos 30 modules n'en
   portait. Sans elle, le `.h` sort **vide** (379 octets) avec `rc = 0` et zero message :
   le piege le plus couteux de la chaine.
3. **Les 9 globaux de notre framework** stubbes dans `solidify_all_python.be` :
   `drivers, serveur, diverses, modules, boolMute, LOG_LEVEL_ERREUR, LOG_LEVEL_DEBUG,
   LOG_LEVEL_DEBUG_PLUS` + `serial` (global Tasmota, lacune amont de plus).
   Trouves automatiquement en 30 s par iteration sur le solidifieur manuel, au lieu de
   9 builds de 40 minutes.

**Preuve chiffree** (`modbusFonctions.be`, directive ajoutee, 9 globaux stubbes) :
source 79 178 octets -> `solidified_modbusFonctions.h` de **243 223 octets**,
**15 fonctions** solidifiees, 1 `be_local_module`. Le module se solidifie donc
integralement — **mais ce `.h` ne compilera pas tant que le slash est la.**

Candidat n°1 inchange : `modbusFonctions.be` (79 Ko) — c'est un `xxxFonctions.be`,
donc solidifiable sans retouche.

**Ce que la phase 2 doit faire :**

1. Declarer `custom_berry_solidify` dans l'env concerne. Rien a coder.
2. Verifier Q3 sur appareil : `import x` sans le fichier sur le FS.
3. ~~Traiter le piege 4 : un module solidifie ne doit plus partir sur le LittleFS,
   sinon on paie la RAM en silence.~~ **CORRIGE le 2026-07-16 : c'etait faux.**
   `be_module.c:285-288` essaie `load_native()` AVANT `load_package()` : le module natif
   gagne, le `.be` restant n'est **jamais charge**, aucune RAM en double. Le seul cout
   residuel est le `compileModule()` de l'`autoexec.be`, qui compile un `.bec` inutile —
   du temps de boot et des ecritures flash. **Optimisation, pas condition de correction.**
   Cf. pieges 4 et 4 bis de `outils_docs/SOLIDIFICATION_BERRY.md`.
4. Mesurer le gain reel (`tasmota.gc()` avant/apres), sans quoi tout ceci reste theorique.

**Corollaire, etabli le 2026-07-16 :** solidifier POUR CERTAINS FIRMWARES SEULEMENT ne
demande aucun travail. `custom_berry_solidify` est une option par environnement, `import`
prefere le natif, et le nom de `module()` ne sert pas a resoudre le fichier. Meme source,
meme LittleFS : c'est l'env qui tranche. Cf. §6 bis de `outils_docs/SOLIDIFICATION_BERRY.md`.

**Ce que la phase 2 ne doit PAS faire** : ecrire `USE_SOLIDIFY_BERRY`, ecrire
`copy_berry_solidify()`, editer `modules.h` ou `be_custom_module.c` a la main. Tout
cela serait reinvente, ou ecrase au prochain build.

---

## Ecarts entre hypotheses et realite

| Question | Hypothese de la spec | Realite observee |
|---|---|---|
| Q1 | NON | **OUI pour la forme** — un `var` au niveau fichier est global, le resolveur le trouve. **Mais le NOM `/x` produit du C invalide** : il faut retirer le slash (15 modules) |
| Q2 | OUI, ca casse | **OUI** — confirme, et cause isolee : c'est le code de niveau fichier, pas la classe |
| Q3 | OUI | **Non teste** — la question etait mal posee : le rattachement est automatique, pas manuel |
| Methode | deposer un `.be` + `pio run` | **Impossible** — un pre-script vide `embedded/` a chaque build |
| Phase 2 | ecrire `USE_SOLIDIFY_BERRY` | **Inutile** — `custom_berry_solidify` existe deja en amont |

## Corrections apportees pendant la phase 1

| Commit | Objet |
|---|---|
| `260991cd2` | reprise de la version amont de `solidify-from-url.py` (fichiers locaux enfin supportes) |
| `1d6950504` | `log` stubbe dans `berry_custom/solidify_all_python.be` |
| *(a suivre)* | `glob_classes = "Driver"` dans le meme fichier |

Les deux ajouts a `solidify_all_python.be` sont des **candidats a une PR chez arendst** :
`berry_custom` est le seul des creneaux a ne stubber ni `log` ni de classes, alors que
c'est precisement celui prevu pour le code utilisateur. Si elle passe, notre divergence
retombe a zero.
