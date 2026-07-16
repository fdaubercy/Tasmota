# Reprise — Solidification Berry

> État au 2026-07-16, fin de session. À lire en entier avant de reprendre.
> Document de reprise : le mettre à jour, ne pas en créer un second.

## En une phrase

La solidification **fonctionne de bout en bout** : `modbusFonctions` (15 fonctions) est
solidifié et présent dans le firmware du grenier. **Il reste à flasher et à mesurer** —
c'est la seule chose qui n'a pas été faite.

---

## LA PROCHAINE ACTION

Flasher le grenier et valider Q3. Le firmware est **déjà construit** (`firmware.bin`,
3,08 Mo, 2026-07-16 06:58) et contient les 34 symboles du module.

```
pio run -e tasmota32s3-etage2-grenier -t upload
```

⚠️ **Jamais `erase_upload`** : il effacerait `_persist.json`, et sans lui `autoexec.be`
ne charge plus rien (`autoexec.be:29`).

Puis console Berry du grenier (`http://192.168.0.44/` → Berry Scripting Console) :

```berry
import path
path.listdir("/")                            # modbusFonctions.be ne doit PAS y etre
import modbusFonctions                       # doit repondre depuis la flash
modbusFonctions.crc16modbus(bytes("0103"))   # une vraie fonction, vraiment appelee
```

- **`import` répond** → **Q3 = OUI**, phase 1 close, la voie est ouverte.
- **`module_not_found`** → Q3 = NON, et tout le reste est caduc.

**Ne pas espérer de gain RAM ici** : le grenier n'utilise pas ModBus, le module n'était
pas sur son LittleFS. `tasmota.gc()` y montrera zéro — vrai, mais sans valeur. Le grenier
valide le **mécanisme**, pas le chiffre.

---

## Ce qui est acquis (prouvé, pas supposé)

| Question | Réponse | Preuve |
|---|---|---|
| Q1 — `var x = module(...)` solidifiable ? | **OUI pour la forme**, mais le **nom** ne doit pas porter de slash | préprocesseur xtensa |
| Q2 — `tasmota.add_driver()` au niveau fichier casse ? | **OUI** — cause isolée : c'est le code de **niveau fichier**, pas la classe | avec pied : rc=1 / sans pied : `.h` de 7503 o, 4 méthodes |
| Q3 — `import` sans fichier sur le FS ? | **NON TESTÉ** | ← la prochaine action |

**Les 5 prérequis, tous en place et vérifiés :**

1. `custom_berry_solidify = data/fs/modbusFonctions.be` (`platformio_tasmota_cenv.ini:267`)
2. Directive `#@ solidify:modbusFonctions` en tête du module
3. Nom de module **sans slash** — `module("modbusFonctions")`
4. **15 fonctions nommées**, 0 anonyme
5. **9 globaux du framework stubbés** dans `berry_custom/solidify_all_python.be`

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

## Décisions ouvertes

**a) Généraliser aux 12 autres modules ?** 83 fonctions à nommer
(`gestionFileFolder` 11, `udpFonctions` 7, `discoveryFonctions` 6, …). **À ne décider
qu'après la mesure sur le garage.**

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

Une seule commande, une fois par poste :

```
python outils_docs/scripts_python/corrige_reglages_vscode.py --verifier
```

C'est la seule chose que git ne peut pas transporter : les réglages VS Code
(`C_Cpp.files.exclude` + `C_Cpp.exclusionPolicy`) vivent dans le profil de la machine.
Sans eux, le `PermissionError` intermittent sur `tasmota.ino.cpp` revient — et avec lui
les heures passées à le diagnostiquer.

Le script trouve le profil actif (piège : avec un profil, `User\settings.json` n'est
**plus** le fichier appliqué), pose les deux réglages, et **prouve qu'ils agissent**.
Le « pourquoi » est dans `CLAUDE.md`, section « À FAIRE SUR CHAQUE POSTE ».

Les deux outils Python n'ont **aucun chemin en dur** : racine du dépôt, PlatformIO et
toolchain xtensa sont tous déduits. Ils marchent sur n'importe quel poste, sous
réserve qu'un build y soit déjà passé une fois (pour que la toolchain soit là).

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
