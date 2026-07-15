# Solidification Berry — Phase 1 (validation expérimentale) — Plan d'implémentation

> **Pour les workers agentiques :** SOUS-SKILL REQUISE : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour exécuter ce plan tâche par tâche. Les étapes utilisent la syntaxe case à cocher (`- [ ]`).

**Objectif :** Trancher par l'expérience, sur des fichiers jetables, ce que le solidifieur Berry accepte réellement — avant d'écrire la moindre ligne du paramètre `USE_SOLIDIFY_BERRY`.

**Architecture :** Deux fichiers `.be` jetables déposés dans `lib/libesp32/berry_custom/src/embedded/` (le créneau amont officiel, aujourd'hui vide et déjà listé dans `SOLIDIFY_DIRS`). Un simple `pio run` déclenche `gen-berry-structures.py`, qui exécute `solidify_all_python.be` et écrit `src/solidify/solidified_*.h`. On observe ce qui sort. Aucune modification du code de production.

**Tech Stack :** PlatformIO (espressif32), Python 3 (scripts pio-tools), Berry, `berry_port` (réimplémentation Python de la VM Berry tournant sur le PC).

## Contraintes globales

- **Ne toucher sous aucun prétexte** à `data/fs/controleModbus.be`, `data/fs/controleUDP.be`,
  `data/fs/udpFonctions.be` — modifications en cours par l'utilisateur.
- **Tout en français** : commentaires, logs, identifiants, messages de commit.
- **Messages de commit sans accents** (précédent d'encodage cassé), sans trailer `Co-Authored-By`.
- **Aucune modification du code de production** en phase 1 : les seuls fichiers créés sont jetables et
  vivent dans `lib/libesp32/berry_custom/src/embedded/`, ignoré par git (`src/.gitignore` : `embedded/*`).
- **Env de test : `tasmota32s3-etage2-grenier`** (COM32). Choisi car il est déjà commenté hors de
  `default_envs`, et son `controleGrenier.be` est vide — c'est l'appareil le moins critique du parc.
- ⚠️ **Un build réécrit `tasmota/user_config_override.h` (`increment_config_holder`) et
  `platformio_override.ini` (`adapteParametresPlatformio_override`)** — deux fichiers que
  l'utilisateur a modifiés et non commités. La tâche 1 pose le filet de sécurité. Ne jamais lancer
  de build avant elle.
- **Ne rien pousser** vers `origin` sans demande explicite.

---

### Task 1 : Filet de sécurité avant tout build

**Files:**
- Create: `docs/superpowers/plans/_sauvegarde-avant-solidify/user_config_override.h.avant`
- Create: `docs/superpowers/plans/_sauvegarde-avant-solidify/platformio_override.ini.avant`
- Create: `docs/superpowers/plans/_sauvegarde-avant-solidify/etat-git.txt`

**Interfaces:**
- Consomme : rien.
- Produit : une copie hors-git-index des deux fichiers que le build va réécrire, et la liste des
  fichiers modifiés au moment T. Les tâches suivantes s'appuient sur l'existence de ce filet.

- [ ] **Étape 1 : Créer le dossier de sauvegarde**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
mkdir -p docs/superpowers/plans/_sauvegarde-avant-solidify
```

- [ ] **Étape 2 : Copier les deux fichiers que le build va réécrire**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
cp tasmota/user_config_override.h docs/superpowers/plans/_sauvegarde-avant-solidify/user_config_override.h.avant
cp platformio_override.ini docs/superpowers/plans/_sauvegarde-avant-solidify/platformio_override.ini.avant
```

- [ ] **Étape 3 : Figer l'état git de référence**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
git status --porcelain > docs/superpowers/plans/_sauvegarde-avant-solidify/etat-git.txt
cat docs/superpowers/plans/_sauvegarde-avant-solidify/etat-git.txt
```

Attendu : exactement 9 lignes ` M` (dont `data/fs/controleModbus.be`, `data/fs/controleUDP.be`,
`data/fs/udpFonctions.be`, `tasmota/user_config_override.h`, `platformio_override.ini`) plus les
lignes `??`.

- [ ] **Étape 4 : Vérifier que la sauvegarde est exploitable**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
diff tasmota/user_config_override.h docs/superpowers/plans/_sauvegarde-avant-solidify/user_config_override.h.avant && echo "SAUVEGARDE OK"
```

Attendu : `SAUVEGARDE OK` (aucune différence).

**Si cette étape échoue, ARRÊTER le plan.** Sans filet, on ne lance aucun build.

- [ ] **Étape 5 : Ne pas committer ce dossier**

Le dossier est un filet temporaire, pas un livrable. Vérifier qu'il n'entre pas dans l'index :

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
echo "_sauvegarde-avant-solidify/" >> .git/info/exclude
git status --porcelain | grep sauvegarde-avant-solidify && echo "ERREUR: encore visible" || echo "EXCLU OK"
```

Attendu : `EXCLU OK`.

---

### Task 2 : Fichier de test « module » et première réponse à Q1

**Files:**
- Create: `lib/libesp32/berry_custom/src/embedded/testFonctions.be`
- Observe: `lib/libesp32/berry_custom/src/solidify/solidified_testFonctions.h`

**Interfaces:**
- Consomme : le filet de la tâche 1.
- Produit : la réponse à **Q1** — « `var x = module("/x")` est-il atteignable depuis `global` par le
  résolveur `#@ solidify:` ? ». Hypothèse à réfuter : **non**.

**Pourquoi ce fichier :** il reproduit exactement la forme réelle des `xxxFonctions.be` du framework
(`data/fs/vrFonctions.be` comme modèle) : singleton `module()`, attribut `DEBUG`, `log()` lazy,
handler `reglage*`, `return` final.

- [ ] **Étape 1 : Écrire le fichier de test**

Créer `lib/libesp32/berry_custom/src/embedded/testFonctions.be` :

```berry
#-
    - Fichier JETABLE — validation de la solidification (phase 1).
    - Reproduit la forme reelle des xxxFonctions.be du framework :
      singleton module(), attribut DEBUG, log() lazy, handler reglage*, return final.
    - A SUPPRIMER apres le verdict.
-#

#@ solidify:testFonctions

# Definition du module
var testFonctions = module("/testFonctions")

testFonctions.DEBUG = nil
testFonctions.sensorsTest = {"valeur": 42}

testFonctions.log = def(msg, levelDebug)
    if (testFonctions.DEBUG == nil)
        testFonctions.DEBUG = "ON"
    end

    if (testFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

testFonctions.reglageTest = def(cmd, idx, payload, payload_json)
    import string
    import json

    var reponse_cmnd = "reglageTest: "

    testFonctions.log("REGLAGE_TEST: payload=" + str(payload), 4)

    reponse_cmnd += string.format("valeur=%i", testFonctions.sensorsTest["valeur"])
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Retourne le module lors de l'importation
return testFonctions
```

- [ ] **Étape 2 : Lancer le build et observer**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
pio run -e tasmota32s3-etage2-grenier 2>&1 | tee docs/superpowers/plans/_sauvegarde-avant-solidify/build-q1.log | grep -i "parsing\|solidif\|error\|attribute_error\|traceback"
```

Deux issues possibles, **les deux sont des résultats valides** :

- `Parsing: testFonctions.be` puis un build qui continue → **Q1 = OUI**, hypothèse réfutée.
- Une exception (`attribute_error`, `value_error`, ou trace Python de `berry_port`) → **Q1 = NON**,
  hypothèse confirmée.

- [ ] **Étape 3 : Consigner le résultat brut**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
ls -la lib/libesp32/berry_custom/src/solidify/
```

Attendu si Q1 = OUI : un fichier `solidified_testFonctions.h` non vide.
Attendu si Q1 = NON : rien d'autre que `.keep`.

- [ ] **Étape 4 : Si Q1 = NON, tester la variante « classe »**

Ne faire cette étape **que** si l'étape 2 a échoué. Remplacer le singleton par une classe, qui est
la forme qu'arendst solidifie réellement (`driver_class.be` comme modèle) — le but est de distinguer
« le solidifieur ne sait pas faire » de « c'est la convention `var ... = module()` qui bloque ».

Remplacer intégralement le fichier par :

```berry
#-
    - Fichier JETABLE — validation de la solidification (phase 1), variante classe.
    - A SUPPRIMER apres le verdict.
-#

#@ solidify:TestFonctions

class TestFonctions
    var DEBUG
    var sensorsTest

    def init()
        self.DEBUG = "ON"
        self.sensorsTest = {"valeur": 42}
    end

    def log(msg, levelDebug)
        if (self.DEBUG == "ON")
            log(msg, levelDebug)
        end
    end
end
```

Relancer :

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
pio run -e tasmota32s3-etage2-grenier 2>&1 | grep -i "parsing\|solidif\|error"
ls -la lib/libesp32/berry_custom/src/solidify/
```

Si `solidified_testFonctions.h` apparaît ici mais pas à l'étape 2 → **le blocage est bien la
convention `var ... = module()`**, et la phase 2 devra prévoir une adaptation de forme.

- [ ] **Étape 5 : Restaurer les fichiers réécrits par le build**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
diff tasmota/user_config_override.h docs/superpowers/plans/_sauvegarde-avant-solidify/user_config_override.h.avant || echo "CFG_HOLDER a ete incremente — comportement normal du build"
git status --porcelain > docs/superpowers/plans/_sauvegarde-avant-solidify/etat-git-apres.txt
diff docs/superpowers/plans/_sauvegarde-avant-solidify/etat-git-apres.txt docs/superpowers/plans/_sauvegarde-avant-solidify/etat-git.txt || echo "ATTENTION: l'etat git a change, verifier ci-dessus"
```

Aucun des 3 fichiers en cours (`controleModbus.be`, `controleUDP.be`, `udpFonctions.be`) ne doit
apparaître comme modifié différemment. **S'ils ont bougé, restaurer immédiatement depuis la sauvegarde
et arrêter le plan.**

---

### Task 3 : Fichier de test « driver » et réponse à Q2

**Files:**
- Create: `lib/libesp32/berry_custom/src/embedded/controleTest.be`
- Observe: `lib/libesp32/berry_custom/src/solidify/solidified_controleTest.h`

**Interfaces:**
- Consomme : le filet de la tâche 1 ; le verdict Q1 de la tâche 2.
- Produit : la réponse à **Q2** — « un `tasmota.add_driver()` au niveau fichier casse-t-il le
  solidifieur ? ». Hypothèse à réfuter : **oui, ça casse** (`tasmota` vaut `nil` sur le PC, stubbé
  par `solidify_all_python.be`).

**Pourquoi ce fichier :** il reproduit la forme réelle des `controleXxx.be`, garde d'activation en
pied comprise — c'est précisément ce code de pied qui est suspecté d'être incompatible.

- [ ] **Étape 1 : Écrire le fichier de test**

Créer `lib/libesp32/berry_custom/src/embedded/controleTest.be` :

```berry
#- NOTES :
    - Fichier JETABLE — validation de la solidification (phase 1).
    - Reproduit la forme reelle des controleXxx.be : class : Driver + garde
      d'activation en pied appelant tasmota.add_driver().
    - A SUPPRIMER apres le verdict.
-#

#@ solidify:CONTROLE_TEST

var controleTest

class CONTROLE_TEST : Driver
    var flagINIT

    def init()
        import string

        self.flagINIT = 0
        tasmota.add_cmd('ReglageTest', / cmd, idx, payload, payload_json -> nil)
        self.flagINIT = 1
    end

    def every_second()
    end

    def web_sensor()
        import string

        tasmota.yield()
        tasmota.web_send(string.format("{s}Test{m}%i{e}", 42))
    end

    def json_append()
    end
end

# Active le Driver de controle du module test
# C'EST CE BLOC QUI EST SUSPECTE : il s'execute au niveau fichier,
# donc sur le PC pendant la solidification, ou `tasmota` vaut nil.
try
    controleTest = CONTROLE_TEST()
    tasmota.add_driver(controleTest)
    log("CONTROLE_TEST: Driver active !", 3)
except .. as error, message
    log(string.format("CONTROLE_TEST_ERREUR: %s -> %s", error, message), 1)
end
```

- [ ] **Étape 2 : Lancer le build et observer**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
pio run -e tasmota32s3-etage2-grenier 2>&1 | tee docs/superpowers/plans/_sauvegarde-avant-solidify/build-q2.log | grep -i "parsing\|solidif\|error\|traceback"
ls -la lib/libesp32/berry_custom/src/solidify/
```

- `solidified_controleTest.h` généré → **Q2 = NON, ça ne casse pas.** Le `try/except` a probablement
  absorbé l'erreur. Noter que le driver n'aura alors **pas** été enregistré au moment de la
  solidification — ce qui est le comportement voulu.
- Exception non rattrapée / build interrompu → **Q2 = OUI, ça casse.** Les `controleXxx.be` ne sont
  pas solidifiables tels quels.

- [ ] **Étape 3 : Isoler la cause si Q2 = OUI**

Ne faire cette étape **que** si l'étape 2 a échoué. Retirer le bloc de pied (les 8 dernières lignes,
de `try` à `end`) et relancer :

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
pio run -e tasmota32s3-etage2-grenier 2>&1 | grep -i "parsing\|solidif\|error"
ls -la lib/libesp32/berry_custom/src/solidify/
```

Si `solidified_controleTest.h` apparaît maintenant → **la cause est confirmée : c'est bien le code de
pied**, et la classe elle-même est solidifiable. C'est le résultat le plus utile possible, car il
oriente directement la phase 2 (déplacer la garde d'activation hors du niveau fichier).

- [ ] **Étape 4 : Vérifier que les fichiers en cours n'ont pas bougé**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
git status --porcelain -- data/fs/controleModbus.be data/fs/controleUDP.be data/fs/udpFonctions.be
```

Attendu : exactement 3 lignes ` M`, identiques à `etat-git.txt`. Rien d'autre.

---

### Task 4 : Q3 — la question bloquante (nécessite un flash)

**Files:**
- Observe: `lib/libesp32/berry_custom/src/solidify/solidified_testFonctions.h`
- Modify (temporaire, restauré en fin de tâche) : `lib/libesp32/berry_custom/src/be_custom_module.c`

**Interfaces:**
- Consomme : un `solidified_testFonctions.h` généré (tâche 2). **Si la tâche 2 n'a rien produit,
  même en variante classe, SAUTER cette tâche et aller directement à la tâche 5 : le verdict est
  déjà « non solidifiable en l'état ».**
- Produit : la réponse à **Q3** — « le module solidifié est-il enregistré de sorte qu'`import
  testFonctions` fonctionne sans fichier sur le FS ? ». **Q3 est bloquante : si elle échoue, la
  phase 2 est abandonnée.**

⚠️ **Cette tâche flashe un appareil réel** (grenier, COM32). Demander confirmation à l'utilisateur
avant l'étape 3. Ne pas utiliser `erase_upload` : il effacerait `_persist.json`, ce qui suffit à
empêcher tout le framework de se charger (`autoexec.be:31`).

- [ ] **Étape 1 : Lire le .h généré et relever le symbole exporté**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
head -20 lib/libesp32/berry_custom/src/solidify/solidified_testFonctions.h
grep -n "be_local_module\|be_local_class\|extern const" lib/libesp32/berry_custom/src/solidify/solidified_testFonctions.h
```

Relever le nom exact du symbole (`be_module_testFonctions` ou `be_class_TestFonctions` selon la
variante retenue en tâche 2). Il sert à l'étape suivante.

- [ ] **Étape 2 : Rattacher le module solidifié**

`be_custom_module.c` porte un marqueur `/*solidify*/` prévu pour ça, et `modules.h` définit
`CUSTOM_NATIVE_MODULES` / `CUSTOM_NATIVE_CLASSES` consommés par `be_modtab.c:240` et `:387`.

Modifier `lib/libesp32/berry_custom/src/be_custom_module.c` — remplacer la ligne `/*solidify*/` par
l'inclusion du header généré (adapter le nom si la variante classe a été retenue) :

```c
/*solidify*/
#include "solidify/solidified_testFonctions.h"
```

Et modifier `lib/libesp32/berry_custom/src/modules.h` :

```c
#define CUSTOM_NATIVE_MODULES     &be_native_module(testFonctions),
#define CUSTOM_NATIVE_CLASSES
```

**Si le symbole relevé à l'étape 1 est une classe et non un module**, utiliser à la place :

```c
#define CUSTOM_NATIVE_MODULES
#define CUSTOM_NATIVE_CLASSES     &be_class_TestFonctions,
```

- [ ] **Étape 3 : Compiler et flasher (DEMANDER CONFIRMATION AVANT)**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
pio run -e tasmota32s3-etage2-grenier -t upload 2>&1 | tail -20
```

Attendu : compilation sans erreur, upload sur COM32 réussi.
Si l'édition de liens échoue sur un symbole indéfini → le nom relevé à l'étape 1 est faux, y revenir.

- [ ] **Étape 4 : Vérifier sur l'appareil — LE test de Q3**

Ouvrir la console Berry (`http://192.168.0.44/` → Configuration → Berry Scripting Console) et
exécuter :

```berry
import path
path.listdir("/")
```

Attendu : **aucun** `testFonctions.be` ni `testFonctions.bec` dans la liste.

Puis :

```berry
import testFonctions
print(testFonctions.sensorsTest)
```

- Affiche `{'valeur': 42}` → **Q3 = OUI. La voie est ouverte, la phase 2 a un sens.**
- `module_not_found` ou équivalent → **Q3 = NON. La phase 2 est abandonnée**, et le verdict doit
  dire pourquoi.

- [ ] **Étape 5 : Mesurer le gain (seulement si Q3 = OUI)**

Dans la console Berry :

```berry
tasmota.gc()
```

Noter la valeur. C'est la référence à comparer, en phase 2, avec un module chargé depuis le FS.

- [ ] **Étape 6 : Restaurer les deux fichiers C**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
git checkout -- lib/libesp32/berry_custom/src/be_custom_module.c lib/libesp32/berry_custom/src/modules.h
git status --porcelain -- lib/libesp32/berry_custom/
```

Attendu : aucune sortie (les deux fichiers sont revenus à l'état du dépôt).

---

### Task 5 : Écrire le verdict et nettoyer

**Files:**
- Create: `docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md`
- Delete: `lib/libesp32/berry_custom/src/embedded/testFonctions.be`
- Delete: `lib/libesp32/berry_custom/src/embedded/controleTest.be`
- Delete: `docs/superpowers/plans/_sauvegarde-avant-solidify/`

**Interfaces:**
- Consomme : les réponses Q1 (tâche 2), Q2 (tâche 3), Q3 (tâche 4).
- Produit : le document qui conditionne la phase 2. C'est le livrable du plan.

- [ ] **Étape 1 : Écrire le verdict**

Créer `docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md` avec cette structure
exacte, en remplaçant chaque `<...>` par le résultat **observé** (jamais inféré) :

```markdown
# Solidification Berry — verdict de la phase 1

Date : <date de l'experience>
Env de test : tasmota32s3-etage2-grenier

## Q1 — `var x = module("/x")` est-il atteignable par `#@ solidify:` ?

Reponse : <OUI | NON>
Preuve : <sortie exacte du build, ou presence/absence de solidified_testFonctions.h>
Variante classe testee : <OUI | NON — et son resultat>
Consequence pour la phase 2 : <...>

## Q2 — un `tasmota.add_driver()` au niveau fichier casse-t-il le solidifieur ?

Reponse : <OUI | NON>
Preuve : <sortie exacte>
Cause isolee en retirant le bloc de pied : <OUI | NON | non teste>
Consequence pour la phase 2 : <...>

## Q3 (bloquante) — `import` trouve-t-il le module solidifie sans fichier sur le FS ?

Reponse : <OUI | NON | non teste car Q1 et Q2 negatifs>
Preuve : <sortie de path.listdir("/") et de import testFonctions>
Symbole exporte : <be_module_... | be_class_...>
tasmota.gc() releve : <valeur>

## Verdict

<Phase 2 : GO | NO-GO>

Regle de selection des fichiers a retenir pour la phase 2 :
<...>

## Ecarts entre hypotheses et realite

| Question | Hypothese de la spec | Realite observee |
|---|---|---|
| Q1 | NON | <...> |
| Q2 | OUI | <...> |
| Q3 | OUI | <...> |
```

- [ ] **Étape 2 : Supprimer les fichiers jetables**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
rm -f lib/libesp32/berry_custom/src/embedded/testFonctions.be
rm -f lib/libesp32/berry_custom/src/embedded/controleTest.be
rm -f lib/libesp32/berry_custom/src/solidify/solidified_testFonctions.h
rm -f lib/libesp32/berry_custom/src/solidify/solidified_controleTest.h
ls -a lib/libesp32/berry_custom/src/embedded/ lib/libesp32/berry_custom/src/solidify/
```

Attendu : chaque dossier ne contient plus que `.` , `..` et `.keep`.

- [ ] **Étape 3 : Vérifier que le dépôt est revenu à son état de départ**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
git status --porcelain | grep -v '^?? docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md'
```

Attendu : **exactement** les mêmes lignes que `docs/superpowers/plans/_sauvegarde-avant-solidify/etat-git.txt`
— soit les 9 ` M` (dont `user_config_override.h`, dont le `CFG_HOLDER` a pu être incrémenté par les
builds : c'est normal et attendu) et les `??` connus.

**Si un des 3 fichiers en cours a été altéré, le signaler immédiatement à l'utilisateur avant toute
autre action.**

- [ ] **Étape 4 : Retirer le filet de sécurité**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
rm -rf docs/superpowers/plans/_sauvegarde-avant-solidify
```

- [ ] **Étape 5 : Committer le verdict**

```bash
cd /c/Users/fdaub/Documents/Github/Tasmota
git add docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md
git commit -F - <<'EOF'
docs: verdict de la phase 1 de la solidification Berry

Resultat experimental des 3 questions ouvertes par la spec du 2026-07-15,
observe sur l'env tasmota32s3-etage2-grenier avec des fichiers jetables.

Aucun fichier de production modifie.
EOF
git log -1 --format='%h %s'
```

**Ne pas pousser.** Le push n'est pas auto-autorisé sur ce dépôt.

---

## Ce que ce plan ne fait pas

- Il n'écrit **pas** `copy_berry_solidify()` ni le paramètre `USE_SOLIDIFY_BERRY` — c'est la phase 2,
  conditionnée par le verdict (cf. spec, section « Phase 2 »).
- Il ne solidifie **aucun** module réel (`modbusFonctions.be` reste le candidat, mais après validation).
- Il ne réécrit **pas** les `controleXxx.be`.
- Il ne touche pas à `autoexec.be` ni à l'exclusion LittleFS.

Une fois le verdict écrit et relu par l'utilisateur, la phase 2 fera l'objet de son propre plan.
