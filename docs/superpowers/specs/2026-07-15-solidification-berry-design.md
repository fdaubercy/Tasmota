# Solidification Berry pilotée par env — design

Date : 2026-07-15
Statut : validé, non implémenté

## Problème

Le framework Berry maison (`data/fs/*.be`, ~10 800 lignes) est chargé sur l'appareil sous forme
de bytecode : `gestionFileFolder` compile `.be` → `.bec`, ce qui réduit la taille du fichier et le
temps de boot, **mais pas la RAM**. Le bytecode d'un `.bec` est chargé en mémoire exactement comme
celui d'un `.be`.

Seule la **solidification** (bytecode généré à la compilation sur le PC, embarqué en structures C
dans le segment read-only de la flash) met le coût RAM à zéro. Elle est en revanche incompatible avec
la boucle de développement : chaque modification impose un rebuild complet et un reflash, alors que le
framework actuel permet « téléverser un `.be` → `BrRestart` → tester » en quelques secondes.

**But** : pouvoir activer la solidification par appareil, sans rien casser sur les appareils existants
et sans dégrader la boucle de développement.

## Décisions

| Question | Décision | Raison |
|---|---|---|
| Granularité | **Interrupteur global on/off par appareil** | Correspond à l'usage réel : appareil en dev = off, appareil figé = on |
| Déclencheur | **`-D USE_SOLIDIFY_BERRY` dans les `build_flags` de l'env** | Lisible là où sont déjà tous les réglages par appareil ; `pre_utilitaires_platformio.py` lit déjà `BUILD_FLAGS` |
| État initial | **Flag posé mais commenté** (`; -D USE_SOLIDIFY_BERRY`) | Fonctionnalité dormante ; aucun appareil existant ne change de comportement |
| Mécanisme | **Copie par le pre-script** vers `berry_custom/src/embedded/` | Réplique `copy_fs_image` déjà écrit et éprouvé : même hook, même cycle de vie, même nettoyage `atexit` |
| Sélection des fichiers | **À déterminer en phase 1** | Dépend de ce que le solidifieur accepte réellement — à observer, pas à inférer |

### Alternatives écartées

- **Liste de `.be` par env** (façon `custom_files_upload`) — granularité plus fine, mais l'usage réel
  est binaire (dev / production). À reconsidérer si la phase 1 montre qu'une partie seulement des
  fichiers est solidifiable.
- **Envs dédiés** (`...-solid`) — zéro code, mais duplique toute la config par appareil et rend
  `default_envs` ingérable.
- **Détection + saut silencieux des échecs** — un échec silencieux ferait croire à un gain de RAM
  inexistant. Rejeté : toute exclusion doit être explicite et loguée.

## Contexte technique établi

Vérifié dans le dépôt, pas inféré :

- `lib/libesp32/berry_custom/` est le créneau officiel amont pour du code utilisateur solidifié. Il
  existe et est **vide** (`src/embedded/.keep`). Il figure dans `SOLIDIFY_DIRS`
  (`pio-tools/gen-berry-structures.py:249`).
- Chaîne de build : `platformio_tasmota32.ini:54-56` enchaîne `dump-defines.py` (extrait les ~3 200
  `#define` du firmware pour que le solidifieur voie les mêmes `USE_*`/`D_*` que le C++),
  `gen-berry-defines.py`, puis `gen-berry-structures.py` qui exécute `solidify_all_python.be`.
- Directive de solidification : regex `#@\s*solidify:([A-Za-z0-9_.,]+)`, second champ optionnel `weak`.
- Le solidifieur **exécute le code sur le PC** (`solidify_all_python.be` : `var compiled = compile(src)`
  puis `compiled()` — « run the compile code to instanciate the classes and modules »). Les globales
  Tasmota (`tasmota`, `gpio`, `light`…) y sont stubbées à `nil`.
- Le résolveur de la directive part de `global` (`var o = global` puis `o = o.(subname)`).
- Enregistrement : `be_custom_module.c` porte un marqueur `/*solidify*/` ; `modules.h` définit
  `CUSTOM_NATIVE_MODULES` / `CUSTOM_NATIVE_CLASSES`, consommés par `be_modtab.c:240` et `:387` ;
  `berry_custom.h` est force-inclus par `xdrv_52_9_berry.ino:42`.
- `lib/libesp32/berry_custom/src/.gitignore` ignore `embedded/*` et `solidify/*` — les copies
  temporaires ne pollueront pas le dépôt.

## Phase 1 — Validation expérimentale

**Aucune modification du code de production.** Deux fichiers jetables dans
`lib/libesp32/berry_custom/src/embedded/`, calqués sur les deux formes réelles du framework :

- `testFonctions.be` — singleton `var testFonctions = module("/testFonctions")`, attribut `DEBUG`,
  `log()` lazy, handler `reglageTest`, `return testFonctions`, annoté `#@ solidify:testFonctions`.
- `controleTest.be` — `class CONTROLE_TEST : Driver` avec `init()`/`every_second()`/`web_sensor()`/
  `json_append()`, et la garde d'activation en pied appelant `tasmota.add_driver()`.

### Questions auxquelles la phase 1 doit répondre

| # | Question | Hypothèse | Conséquence si l'hypothèse tient |
|---|---|---|---|
| 1 | `var x = module("/x")` est-il atteignable depuis `global` par le résolveur `#@ solidify:` ? | **Non** (c'est un `var` local au fichier, pas un global) | La convention `xxxFonctions.be` doit être adaptée pour être solidifiable |
| 2 | Un `tasmota.add_driver()` au niveau fichier casse-t-il le solidifieur ? | **Oui** (`tasmota` vaut `nil` sur le PC) | Les `controleXxx.be` ne sont pas solidifiables tels quels |
| 3 | Un module solidifié est-il enregistré de sorte qu'`import testFonctions` fonctionne sans fichier sur le FS ? | Oui | Condition nécessaire à tout le reste — si non, le projet s'arrête |

**Livrable** : un verdict écrit sur les trois points. La règle de sélection des fichiers de la phase 2
en découle. Si Q3 échoue, la phase 2 est abandonnée.

## Phase 2 — Le paramètre

Conditionnée par le résultat de la phase 1.

### Déclencheur

```ini
build_flags             = ${env:tasmota32p4-base-devkit.build_flags}
                           -D FIRMWARE_ESP32P4_GARAGE_SERVEUR_MODBUS            ; Firmware perso
                           ; -D USE_SOLIDIFY_BERRY                              ; Solidification Berry (RAM=0, impose un reflash a chaque modif)
```

Convention de commentaire alignée sur l'existant (`; -D USE_WEBCAM`, `platformio_tasmota_cenv.ini:73`).

### Composant : `copy_berry_solidify(env)`

Nouvelle fonction dans `outils_docs/scripts_python/pre_utilitaires_platformio.py`, jumelle de
`copy_fs_image` (`:469`).

- **Entrée** : l'env courant (`$PIOENV`), ses `BUILD_FLAGS`, `data/fs/`.
- **Garde 1** : sortie immédiate si `USE_SOLIDIFY_BERRY` absent des `BUILD_FLAGS`.
- **Garde 2** : sortie immédiate si la target n'est pas une target de build — réutilise la liste
  `optimized_targets = ["buildfs", "uploadfs", "erase_upload", "upload"]` de `copy_fs_image`.
- **Effet** : copie les `.be` retenus de `data/fs/` vers `lib/libesp32/berry_custom/src/embedded/`.
- **Effet** : exclut ces mêmes `.be` de l'image LittleFS (cf. contrainte ci-dessous).
- **Nettoyage** : `atexit`, sur le modèle de `remove_backup_data`.
- **Sortie** : log explicite de chaque fichier solidifié et de chaque fichier exclu du LittleFS.

La source de vérité reste `data/fs/`. L'arborescence du projet ne change pas.

### Contraintes d'intégration

1. **Exclusion LittleFS — condition de correction, pas optimisation.** Un fichier à la fois solidifié
   et présent sur le FS serait recompilé et rechargé par `autoexec.be`, consommant la RAM qu'on croyait
   économiser. L'échec serait silencieux.
2. **`autoexec.be` doit sauter le `compileModule()`** d'un module solidifié : `import` le trouvera
   nativement. Mécanisme à définir en phase 2 (le fichier étant absent du FS, le comportement actuel
   de `gestionFileFolder` face à un fichier manquant doit être vérifié).
3. **Conditionnalité d'activation.** Un module solidifié est dans le firmware, sans condition — la
   granularité par appareil du `_persist.json` ne s'y applique plus. Sans impact pratique ici : un
   firmware est déjà compilé par appareil.

## Vérification

| Cas | Attendu |
|---|---|
| Flag absent (les 3 envs actifs) | Build **identique** à aujourd'hui — même artefacts, aucun fichier copié dans `berry_custom/` |
| Flag présent, env de test | `src/solidify/solidified_testFonctions.h` généré ; `berry_custom/src/embedded/` vidé après le build |
| Flag présent, sur l'appareil | `import testFonctions` répond alors qu'aucun `testFonctions.be`/`.bec` n'est sur le LittleFS (`path.listdir("/")`) |
| Gain mesuré | `tasmota.gc()` avant/après : la différence doit refléter le retrait du module de la RAM |

## Hors périmètre

- Solidifier les modules réels (`modbusFonctions.be`, 79 Ko — candidat évident, mais après validation).
- Réécrire les `controleXxx.be` pour les rendre solidifiables.
- Toute modification des trois fichiers en cours de travail (`controleModbus.be`, `controleUDP.be`,
  `udpFonctions.be`).
