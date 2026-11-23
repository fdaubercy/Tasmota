# Monter un nouveau poste, et le PermissionError sur tasmota.ino.cpp

Tire de `CLAUDE.md` le 2026-11-23 (plan `binomes-berry`, A11).

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
