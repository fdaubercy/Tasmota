# Solidification Berry — verdict de la phase 1

Date : 2026-07-15
Env de test : `tasmota32s3-etage2-grenier`
Methode : solidifieur lance **a la main**, sans build complet (voir « Ecart de methode »).

> **Verdict en une ligne : phase 2 = GO.** Les deux formes du framework sont
> solidifiables. Mais la phase 2 telle que la spec l'imaginait n'a plus lieu d'etre :
> le parametre a ecrire **existe deja en amont** (`custom_berry_solidify`).

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

**Consequence : la convention maison `var xxxFonctions = module("/xxxFonctions")` est
solidifiable telle quelle. Aucune adaptation de forme n'est necessaire.**

Variante classe testee : non — inutile, l'hypothese etait deja refutee.

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
| `xxxFonctions.be` (singleton `module()`) | **OUI, tel quel** | aucune |
| `controleXxx.be` (`class : Driver`) | **OUI** | deplacer la garde d'activation hors du niveau fichier |

Candidat n°1 inchange : `modbusFonctions.be` (79 Ko) — c'est un `xxxFonctions.be`,
donc solidifiable sans retouche.

**Ce que la phase 2 doit faire :**

1. Declarer `custom_berry_solidify` dans l'env concerne. Rien a coder.
2. Verifier Q3 sur appareil : `import x` sans le fichier sur le FS.
3. Traiter le piege 4 (doc `outils_docs/SOLIDIFICATION_BERRY.md`) : un module solidifie
   ne doit **plus** partir sur le LittleFS, sinon `autoexec.be` le recompile et on paie
   la RAM qu'on croyait economiser, en silence.
4. Mesurer le gain reel (`tasmota.gc()` avant/apres), sans quoi tout ceci reste theorique.

**Ce que la phase 2 ne doit PAS faire** : ecrire `USE_SOLIDIFY_BERRY`, ecrire
`copy_berry_solidify()`, editer `modules.h` ou `be_custom_module.c` a la main. Tout
cela serait reinvente, ou ecrase au prochain build.

---

## Ecarts entre hypotheses et realite

| Question | Hypothese de la spec | Realite observee |
|---|---|---|
| Q1 | NON | **OUI** — un `var` au niveau fichier est global ; forme maison solidifiable telle quelle |
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
