# Extensions Tasmota (`.tapp`) : caractéristiques, quand en faire une, comment la fabriquer

Document écrit le 2026-11-07 (plan `tasks/plans/autoexec-mqtt-tapp.md`, action A5), à partir du code du dépôt.
**Rien de ce qui est dit ici n'a été essayé sur une carte** : chaque fait est lu dans le code et renvoie à sa source
(`fichier::fonction`). Ce qui dépend d'un comportement réel de la carte est marqué « non essayé sur carte » ; la liste
de ce qui reste à essayer est en fin de document (§ 9, essai prévu en A10).

## 1. En cinq lignes

- Un `.tapp` est une archive ZIP **sans compression** contenant un `manifest.json`, un `autoexec.be` et, au besoin,
  d'autres `.be`. Le firmware la monte comme un mini-système de fichiers et exécute son `autoexec.be`.
- Le firmware en lance tous ceux de `/.extensions/` puis de `/`, **avant** le `/autoexec.be` de la carte.
- Elle s'arrête proprement (`unload()`), se désactive en renommant (`.tapp_`), se pilote depuis la page `/ext`.
- Dans ce dépôt, **un `.tapp` n'est pas le bon choix par défaut** : choisir selon le tableau ci-dessous.
- Script de fabrication : `outils_docs/scripts_python/berry/gen_tapp.py` (§ 5.4). Les sources d'extension iront dans
  `data/extensions/<nom>/` (A7 et A8, **pas encore créé**), avec une page dans l'annuaire des outils (A7, à venir).

| Besoin | Voie la mieux adaptée | Pourquoi |
|---|---|---|
| Module commun à presque toutes les cartes, ou qui doit exister dès le prologue | **Module solidifié** (`custom_berry_solidify`, § SOLIDIFICATION_BERRY) | Bytecode en flash : aucune RAM de heap pour le code, survit au formatage du FS. Coût : un build et une mise à jour du firmware. |
| Module propre à une carte, modifié souvent | **`.be` sur le FS + `demarrage.charge` / `chargeFichier`** | Une ligne d'autoexec, compilé en `.bec`, ordre de démarrage maîtrisé, charte et bancs du dépôt déjà câblés. |
| Fonction **optionnelle**, à poser, retirer ou arrêter **sans toucher à l'autoexec ni au firmware**, ou à partager entre cartes tel quel | **`.tapp`** | Un seul fichier, activable et arrêtable depuis `/ext`, qui s'ajoute à une carte sans rien modifier d'autre. |

Un `.tapp` n'apporte **pas** d'économie de RAM par rapport à un `.be` (voir § 2.5) ni de contrôle de l'ordre de
démarrage (il s'exécute avant l'autoexec, § 2.3). Le choisir pour la **séparation** (poser et retirer sans rien d'autre),
pas pour la performance.

## 2. Caractéristiques

### 2.1 Format de l'archive

`lib/libesp32/Zip-readonly-FS/src/ZipReadFS.cpp::ZipArchive::parse` lit les en-têtes locaux ZIP à la suite et **refuse
l'archive entière** (rien n'est monté) si :

| Condition | Conséquence |
|---|---|
| signature d'en-tête invalide | refus, journal `ZIP: invalid zip signature` |
| drapeaux généraux non nuls | refus |
| méthode de compression non nulle (donc `ZIP_DEFLATED` interdit) | refus |
| taille compressée différente de la taille d'origine | refus |
| nom d'entrée de plus de 64 octets | refus |

L'archive doit donc être en `ZIP_STORED`. Le firmware lit les en-têtes locaux seulement (pas le répertoire central) et
ignore le champ supplémentaire. Le nom d'entrée est coupé au dernier `#` ; le commentaire du code dit « retirer les
noms de dossiers » mais le code ne coupe que sur `#` : une entrée dans un sous-dossier garderait son `/` (non essayé sur carte).
`gen_tapp.py` interdit donc les sous-dossiers : l'archive est **à plat**.

Fichiers attendus : `manifest.json` et `autoexec.be` (les `.be` voisins sont libres). L'amont fabrique ses archives par
`zip -j -0` (commentaire en tête des `autoexec.be` de `tasmota/berry/extensions/`), ce qui donne le même format.

### 2.2 Manifeste

Lu par `lib/libesp32/berry_tasmota/src/embedded/tasmota_class.be::read_extension_manifest`, qui ouvre `<archive>#manifest.json`.

| Clé | Rôle | Valeur par défaut / règle |
|---|---|---|
| `name` | **obligatoire** : nom affiché dans `/ext` | sans `name`, le manifeste est refusé (`nil`) et l'extension n'est pas listée |
| `description` | texte de `/ext` | `""` |
| `version` | entier, ou chaîne `0x…` convertie par `int()` ; affichée `vA.B.C.D` (octets de `0xAABBCCDD`) par `extension_manager.be::version_string` | `0` |
| `min_tasmota` | entier ou `0x…` | `0` ; **lu mais jamais comparé** dans `extension_manager.be` ni dans `read_extension_manifest` : il ne protège de rien |
| `author`, `features` | présents dans les exemples de l'amont | ignorés par le firmware |

`read_extension_manifest` ajoute une clé calculée `autorun` : vrai si le chemin se termine par `.tapp` (faux pour `.tapp_`).

### 2.3 Cycle de vie

| Étape | Qui | Détail (source) |
|---|---|---|
| Lancement au démarrage | événement synthétique `autoexec`, **juste avant** `BrLoad("autoexec.be")` | `tasmota/tasmota_xdrv_driver/xdrv_52_9_berry.ino` (cas `FUNC_LOOP`, au premier tick) ; `tapp.be::autoexec` appelle `autoexec_dir("/.extensions/")` puis `autoexec_dir("/")` |
| Fichiers retenus | `tapp.be::autoexec_dir` | nom se terminant par **`.tapp`** exactement ; un `.tapp_` n'est jamais lancé |
| Chargement | `tasmota_class.be::load` | ajoute `#autoexec` au nom, pose `tasmota.wd = "<archive>#"`, ajoute ce chemin à `sys.path`, exécute `autoexec.be`, **retire** le chemin et vide `wd` à la fin |
| Enregistrement | l'`autoexec.be` de l'extension | `tasmota.add_extension(instance)` : enregistre l'instance sous le chemin de l'archive (`tasmota.wd`, `#` final retiré) dans `tasmota._ext` (`tasmota_class.be::add_extension`) |
| Arrêt | `tasmota.unload_extension(chemin_ou_instance)` | appelle `unload()` si l'instance en a un, retire le driver (`remove_driver`), force un `tasmota.gc()` (`tasmota_class.be::unload_extension`) |
| Désactivation | renommage `.tapp` → `.tapp_` | `extension_manager.be::enable_disable_ext` ; une extension qui tourne est re-clée sous son nouveau nom |
| Lancement à la main | `tasmota.load("/.extensions/x.tapp")` | `extension_manager.be::run_stop_ext`, bouton « Run » de `/ext` |

Deux conséquences qui comptent pour le code d'une extension :

- `tasmota.wd` n'est valable **que pendant** le chargement. Tout `import` d'un fichier de l'archive doit se faire dans
  `autoexec.be`, au chargement : un `import` tardif (dans un rappel, une minuterie) ne trouvera plus le fichier,
  `sys.path` ayant été nettoyé (raisonnement sur `load`, non essayé sur carte).
- `unload_extension` ne retire **que** le driver. Les commandes (`add_cmd`), règles (`add_rule`), minuteries, abonnements
  MQTT et pages web enregistrés par l'extension restent actifs : c'est le rôle de `unload()` de les retirer
  (`remove_cmd`, `remove_rule`, `remove_timer`...).

Le démarrage d'extensions ne dépend pas de `SetOption153` : cette option ne coupe que `/autoexec.be`
(`xdrv_52_9_berry.ino::BrLoad`). La même fonction ne lance rien si la prévention de boucle de redémarrage est active
(`TasmotaGlobal.no_autoexec`), mais l'événement `autoexec`, donc les `.tapp`, est envoyé **avant** cet appel : une
extension fautive qui plante au démarrage n'est pas arrêtée par `SetOption153` (lu dans le code, non essayé sur carte).

### 2.4 Emplacement et activation

- `/.extensions/` : dossier constante `EXT_FOLDER` de `Extension_manager` (`lib/libesp32/berry_tasmota/src/embedded/extension_manager.be`), listé par `list_extensions` (`.tapp` et `.tapp_`).
- `/` (racine) : lancé aussi par `tapp.be::autoexec_dir("/")`, mais **non listé** dans `/ext` (la page ne parcourt que
  `/.extensions/`) : une extension à la racine tourne sans pouvoir être arrêtée ni désactivée depuis la page.
- Page `/ext` : `extension_manager.be::web_add_handler` ; actions Run / Stop, Auto-run (renommage), Uninstall, et une
  boutique en ligne (`install_from_store`, dépôt `https://ota.tasmota.com/extensions/` par défaut, **sans objet** ici).
  Le bouton « Running » reflète `tasmota._ext` : **une extension qui n'appelle pas `tasmota.add_extension` s'affiche
  « Stopped »** même si elle tourne, et « Stop » ne peut pas l'arrêter.
- Dossier `/.extensions/` créé au démarrage par `data/fs/gestionFileFolder.be::gestionFileFolder_listeEtRepartitLesFichiers` si absent (§ 8).

### 2.5 RAM : ce qui est mesuré et ce qui est raisonné

**Rien n'a été mesuré sur carte.** Raisonnement sur le code :

- Un `.be` embarqué est **compilé en bytecode dans le tas Berry** au chargement (`tasmota_class.be::load` appelle
  `compile`), comme un `.be` chargé par `demarrage.chargeFichier`. Aucun gain par rapport à lui.
- Un module **solidifié** a son bytecode en flash : aucun coût de tas pour le code. Une extension qui se contente de
  charger un module solidifié (gabarit A, § 5.1) ne coûte donc que sa petite `autoexec.be`.
- L'archive est lue sur le FS (lecture seule, aucune décompression) ; la table des entrées (`ZipArchive`) vit en RAM
  pendant que le fichier est ouvert. Ordre de grandeur non mesuré.
- Arrêter une extension (`unload_extension`) libère ce que Berry peut ramasser (`tasmota.gc()`), pas ce qui reste
  référencé par une règle, une commande ou un abonnement non retirés.

## 3. Intérêts et limites

**Intérêts**

- Pose, retrait, désactivation, arrêt à chaud sans toucher à l'autoexec ni à `_persist.json`, depuis `/ext` ou par fichier.
- Un seul fichier à distribuer ; format que l'amont utilise (6 exemples : `tasmota/berry/extensions/`).
- Les sources restent séparées du FS des cartes : on peut retirer une fonction sans toucher au reste.

**Limites (dans ce dépôt)**

- S'exécute **avant** `/autoexec.be` : `logFonctions`, les `LOG_LEVEL_*`, les blocs du persist (`serveur`, `diverses`…)
  ne sont pas encore posés par `demarrage.prologue` (§ 6.1). Une extension qui logue ou lit le persist à son chargement
  est fragile.
- Hors de la chaîne de contrôle du dépôt : pas de `compileModule`, pas de `.bec`, pas de charte vérifiée à l'exécution,
  pas dans `banc_demarrage` (qui rejoue l'autoexec des cartes). Le script `gen_tapp.py` compile et lit la charte, c'est tout.
- Un formatage du FS l'efface (§ 7), un téléversement du firmware en série réécrit le FS depuis `custom_files_upload`.
- `min_tasmota` ne protège de rien (§ 2.2). Pas de dépendance déclarée entre extensions.
- Plus lourd qu'une ligne d'autoexec pour un module qui sera de toute façon sur toutes les cartes.

## 4. Cas d'utilisation

| Cas | Verdict | Raison |
|---|---|---|
| **`fsMqtt` sur une carte dont l'autoexec ne le charge pas** (cave S3, différentiel…) : recevoir des fichiers par MQTT sans modifier l'autoexec ni le persist de la carte | **adapté** (exemple décidé : A8, `data/extensions/fsMqtt/`) | `fsMqtt` est solidifié dans le socle (`platformio_tasmota_cenv.ini::berry_commun`) : l'extension n'embarque rien, elle ne fait que l'importer. P4, cuve et rideau le chargent déjà (`demarrage.charge(["fsMqtt"])`) : pas d'extension pour eux. |
| Outil de diagnostic temporaire (page web, sonde) à poser le temps d'une mise au point | **adapté** | retiré ensuite sans trace ; c'est le rôle des 6 exemples de l'amont (`Wifi_Heap_Sticker`, `Devices_Online`, `Leds_Panel`…) |
| Fonction d'affichage sur `/` (bandeau, vignette) sans lien avec la logique métier | **adapté** | `web_status_line_left` de `Wifi_Heap_Sticker` en est le modèle |
| Module ModBus, UDP, historique, volets… | **non adapté** | solidifiés ou chargés par `demarrage.charge` dans un ordre précis ; un `.tapp` passerait avant le prologue |
| Quoi que ce soit qui lit `persist`, `logFonctions` ou `LOG_LEVEL_*` dès le chargement | **non adapté tel quel** | à différer (§ 5.1) ; sinon module classique |
| Mise à jour fréquente d'un module de production | **non adapté** | `build_ota_fs.py` / `fsMqtt` poussent déjà un `.be` simple, avec contrôle d'identité |

## 5. Processus de codage pas à pas

### 5.1 Règles du dépôt à respecter

- **Charte des logs** (`CLAUDE.md`, section « Logs Berry », implémentée par `data/fs/logFonctions.be::logFonctions_log`) :
  jamais `log()` direct, toujours `logFonctions.log(msg, niveau [, cible])` ; préfixe `NOM_MAJ_SNAKE: Message en français !`,
  suffixe `_ERREUR` dans un `except` ; niveau par sa constante `LOG_LEVEL_*` ; pas d'`info` dans un rappel fréquent.
  `gen_tapp.py` signale les écarts en avertissements.
- **Pas de globale créée** : tout `import`/`var` de l'`autoexec.be` sous `do … end`. Sans cela, un `import` ou un `var`
  de niveau fichier devient une globale du framework.
- **Ordre avant le prologue** : `LOG_LEVEL_*` et `logFonctions` sont posés par `data/fs/demarrage.be::demarrage_prologue`,
  appelé depuis `/autoexec.be`, donc **après** les extensions. Une extension qui en a besoin **différera son travail**
  par `tasmota.set_timer`. L'événement `autoexec` et `BrLoad("autoexec.be")` s'exécutent dans le même tick
  (`xdrv_52_9_berry.ino`), donc une minuterie de 1000 ms passe après le prologue. **Non essayé sur carte.**
- **Compilation avant le prologue** : différer ne suffit pas. Le fichier entier est compilé au chargement, et un nom sans
  déclaration refuse la compilation **même dans une fonction jamais appelée** (`be_parser.c::singlevaraux` rend `ETVOID`, puis
  « `'LOG_LEVEL_INFO' undeclared` », firmware compris : `comp_set_named_gbl` et `comp_set_strict` de `xdrv_52_9_berry.ino`
  ne changent rien ; reproduit par `berry.exe -g -s`, banc `berry/banc_tapp_fsmqtt.py`). L'extension ne se lancerait pas du
  tout. Écrire donc `import global` puis `global.LOG_LEVEL_INFO`, et `import logFonctions` **dans** la fonction. Même chose
  pour `serveur`, `diverses`, `modules`, `drivers`, `boolMute`, `controleGeneral`… : `gen_tapp.py` les refuse
  (`gen_tapp.py::GLOBALES_DU_FRAMEWORK`), alors que `verifie_berry.py` seul les accepte, car il les déclare d'avance pour
  les modules chargés après le prologue.
- **Module solidifié** : si ses fonctions retrouvent leur module par un nom global, un `import` sous `do … end` ne
  suffit pas (la globale n'existe pas) ; voir le commentaire de `demarrage.be::demarrage_importe` pour la parade
  (`global.setmember`). `fsMqtt` n'est pas concerné (`fsMqtt_init` reçoit le module en argument).

### 5.2 Gabarit A : charger un module déjà solidifié

Dossier `ext_a/` (nom d'archive libre) :

`manifest.json`
```json
{
  "name": "Reception FS MQTT",
  "version": "0x1B0B0700",
  "description": "Charge le module solidifie fsMqtt sur une carte dont l'autoexec ne le charge pas",
  "min_tasmota": "0x0F010001"
}
```

`autoexec.be`
```berry
# Extension sans .be embarque : le module est solidifie dans le firmware, l'extension ne fait que le charger.
# Differe apres /autoexec.be : le prologue de demarrage.be pose LOG_LEVEL_* et le persist dont logFonctions a besoin.
do
  tasmota.set_timer(1000, def ()
    import global                 # LOG_LEVEL_* lus a l execution : a la compilation, avant /autoexec.be, ces noms n existent pas
    import logFonctions
    try
      import fsMqtt
      logFonctions.log("EXT_FSMQTT: module charge par l'extension !", global.LOG_LEVEL_INFO)
    except .. as e, m
      logFonctions.log(f"EXT_FSMQTT_ERREUR: chargement impossible : {e} - {m} !", global.LOG_LEVEL_ERREUR)
    end
  end)
end
```

Limites de ce gabarit : sans `add_extension` ni `unload()`, `/ext` affiche l'extension « Stopped » et ne peut pas
l'arrêter ; pour `fsMqtt` c'est voulu (il n'a pas d'instance à enregistrer : `fsMqtt_init` publie son récepteur dans
`global.fsMqttRecepteur`, et `fsMqtt` n'a aucune méthode `unload`). Un arrêt demanderait du code dans le module lui-même.
`fsMqtt_init` lit `persist` et abonne `fsmqtt/<topic>/ordre` et `…/morceau` : **sans `serveur.mqtt.topic` dans le persist
de la carte, rien n'est abonné** (journal `FS_MQTT_ERREUR`).

### 5.3 Gabarit B : module embarqué avec `unload()`

Dossier `ext_b/` : `manifest.json` (même forme que ci-dessus, `name` : « Mon extension »), `mon_ext.be`, `autoexec.be`.

`mon_ext.be`
```berry
# Gabarit d'extension : un driver, une commande, une regle, tous retires par unload().
class Mon_ext
  static var REGLE = "mon_ext_connecte"

  def init()
    tasmota.add_driver(self)
    tasmota.add_cmd("MonExt", / cmd, idx, payload, payload_json -> self.commande(payload))
    tasmota.add_rule("Mqtt#Connected", /-> self.connecte(), self.REGLE)
  end

  def commande(payload)
    tasmota.resp_cmnd(f'{{"MonExt":"{payload}"}}')
  end

  def connecte()
    import global                 # pas de LOG_LEVEL_* nu : le fichier est compile avant /autoexec.be
    import logFonctions
    logFonctions.log("MON_EXT: MQTT connecte !", global.LOG_LEVEL_INFO)
  end

  def every_second()
    # appele par add_driver ; pas d'info ici (charte, regle 4)
  end

  # Appele par tasmota.unload_extension : retire TOUT ce qui a ete enregistre (rien ne l'est a ta place).
  def unload()
    tasmota.remove_cmd("MonExt")
    tasmota.remove_rule("Mqtt#Connected", self.REGLE)
    tasmota.remove_driver(self)
  end
end

return Mon_ext()
```

`autoexec.be`
```berry
do                                      # pas de globale ajoutee
  import introspect
  var mon_ext = introspect.module('mon_ext', true)    # charge depuis l'archive, sans cache
  tasmota.add_extension(mon_ext)                      # chemin = tasmota.wd, valide pendant ce chargement seulement
end
```

Points à connaître :

- `introspect.module(nom, true)` charge le module comme un `import` mais **sans globale** et sans cache
  (`lib/libesp32/berry/src/be_introspectlib.c`) ; c'est la forme des exemples de l'amont. `import mon_ext` sous `do … end`
  convient aussi (local au bloc) mais met le module en cache : il survivrait à un `unload_extension` (non essayé sur carte).
  Retenue ici : `introspect.module(…, true)`, comme l'amont.
- `tasmota.add_extension(instance)` sans second argument utilise `tasmota.wd` : n'appeler **que** dans l'`autoexec.be`.
- Les rappels enregistrés doivent être des **fermetures** (`/args -> self.methode(args)`), pas des méthodes liées :
  `tasmota_class.be::add_cmd` et `set_timer` passent par `check_not_method` et lèvent `type_error` sinon.
- Les commentaires de l'amont `tasmota.unload_extension('Leds Panel')` (fin des `autoexec.be` d'exemple) **ne marchent
  pas** : la clé de `tasmota._ext` est le **chemin** de l'archive (`/.extensions/Leds_Panel.tapp`), pas le `name` du
  manifeste (`unload_extension` cherche la chaîne telle quelle). Utiliser le chemin ou l'instance.
- Une extension qui journalise à son chargement (hors minuterie) s'expose au problème d'ordre du § 5.1.

### 5.4 Fabriquer l'archive

```
PYTHONIOENCODING=utf-8 ~/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/berry/gen_tapp.py <dossier> [--sortie x.tapp]
```

`gen_tapp.py::construit` exige `autoexec.be` et un `manifest.json` valide (`name` non vide, `version`/`min_tasmota`
entiers ou `0x…`), refuse sous-dossiers, noms non ASCII, `#` dans un nom, noms de plus de 64 octets ; vérifie la syntaxe
de chaque `.be` avec le moteur de `verifie_berry.py`, sans déclarer d'avance les noms du framework (§ 5.1) ; écrit en
`ZIP_STORED`, date fixe, atomiquement. Code de sortie 0 = construit, 1 = refus (motif sur stderr, ancien `.tapp` intact).

**L'exemple du gabarit A, `data/extensions/fsMqtt/`, a son banc** (`berry/banc_tapp_fsmqtt.py`, `berry.exe -g -s` comme le
firmware) : chargement sans `LOG_LEVEL_*` ni `logFonctions`, aucune globale créée, minuterie, échec journalisé, vrai
`fsMqtt` abonné, archive reproductible. Le `.tapp` n'est pas versionné (`data/extensions/.gitignore`) : il se refait à
l'identique. Cela prouve la **syntaxe Berry** et le **format** ; cela ne prouve pas le comportement sur carte.

## 6. Envoi sur une carte

| Voie | État dans le code | Essai sur carte |
|---|---|---|
| Page `/ext` de la carte : boutons Run / Stop / Auto-run / Uninstall | `extension_manager.be::page_extensions_ctl` ; **ne reçoit pas de fichier** (sa boutique télécharge depuis un dépôt `…/extensions/`) | sans objet pour déposer un fichier |
| HTTP `/ufsu` (page « Gestionnaire de fichiers » de Tasmota) | écrit dans le « dossier courant » `ufs_path` + `/` + nom (`tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino::UfsUploadFileOpen`) ; `outils_docs/scripts_python/outils_pc/build_ota_fs.py::envoie_fs_ota` fixe déjà ce dossier (`/ufsd?dir=0&download=/<dossier>`) et crée les dossiers par `Br import path path.mkdir` : la même méthode atteint `/.extensions/` | **non essayé sur carte** (A10) |
| MQTT, module `fsMqtt` | `data/fs/fsMqtt.be::chemin_valide` accepte `/.extensions/x.tapp` (absolu, sans `..`, ≤ 49 caractères) ; l'ordre `debut` crée le dossier parent manquant ; taille ≤ 1 Mo (`TAILLE_MAX`) ; contrôle MD5 ; envoi : `build_ota_mqtt.py::envoie_fs_mqtt(fichiers=…)` | **non essayé sur carte** (A10) |
| Dépôt à la racine (`/x.tapp`) | lancé tel quel au prochain démarrage (`autoexec_dir("/")`), puis déplacé dans `/.extensions/` par `gestionFileFolder` (§ 8) | **non essayé sur carte** |
| Image du FS (`custom_files_upload`) | `pio-tools/post_esp32.py::esp32_build_filesystem` copie les fichiers listés **à la racine de l'image** ; un dossier listé est fusionné dans la racine (`copytree`) ; voir § 7 | non essayé |

Le nom d'hôte de la carte est à vérifier avant tout envoi (identité), comme le font déjà `build_ota_fs.py` et
`autoexec_envoi.py` ; la page de l'annuaire prévue en A7 s'appuiera dessus (à venir, non décrite ici).

## 7. Pièges

1. **Ordre avant `/autoexec.be`** (§ 2.3, § 5.1) : `logFonctions`, `LOG_LEVEL_*`, `persist.serveur`… absents au chargement,
   donc **à la compilation** : un `LOG_LEVEL_INFO` nu empêche l'extension de se lancer, minuterie ou pas (§ 5.1).
   `fsMqtt_init` lit `persist` (module natif, présent) et appelle `logFonctions.log` seulement sur son chemin d'erreur
   (`serveur.mqtt.topic` absent), où `LOG_LEVEL_ERREUR` n'existe pas encore : l'erreur levée à ce moment-là est **peut-être**
   l'échec de la globale manquante plutôt que le message prévu (non essayé sur carte). D'où la minuterie du gabarit A.
2. **Formatage du FS** : l'ordre `efface` de `fsMqtt.be::efface` fait `path.format(true)` ; `/.extensions/` disparaît avec le
   reste, comme tout fichier non rejoué. La page Build envoie ensuite l'image complète (`build_ota_mqtt.py::envoie_fs_mqtt`,
   `effacer=True`) : une extension absente de l'image est perdue.
3. **Envoi de l'image du FS** : il n'ignore pas `/.extensions/`, contrairement à ce que supposait le plan de ce chantier :
   `build_ota_fs.py::extrait_image` parcourt toute l'image (`fs.walk("/")`) et `_inventaire` tout le
   dossier (`rglob("*")`, dossiers cachés compris) ; rien ne filtre `.extensions`. Le vrai piège est **en amont**, dans la
   construction de l'image : `post_esp32.py::esp32_build_filesystem` ne met dans l'image que ce que liste
   `custom_files_upload`, à plat (un `.tapp` listé atterrit à la racine, pas dans `/.extensions/`). Sans entrée dans cette
   liste, une extension déposée sur la carte n'est pas dans l'image : un téléversement du firmware en série (qui flashe
   aussi le FS, voir `CLAUDE.md`, « Vigilances de build ») la fait disparaître. Non essayé sur carte.
4. **Pas de `min_tasmota` effectif** (§ 2.2) : une extension écrite pour un firmware plus récent se charge quand même et échoue à l'exécution.
5. **Une extension fautive se relance à chaque démarrage** (§ 2.3) et `SetOption153` ne l'arrête pas ; pour la
   neutraliser sans carte accessible en série : la renommer en `.tapp_` (via `/ufsd` ou `Br import path path.rename(...)`, non essayé sur carte).
6. **`import` tardif impossible** (§ 2.3) : tout fichier de l'archive s'importe pendant `autoexec.be`.
7. **`.tapp` déposé à la racine** : rangé dans `/.extensions/` au démarrage, et remplace un homonyme, voir § 8.

## 8. Un `.tapp` déposé à la racine : `gestionFileFolder.be`

Corrigé le 2026-11-07 à la demande de l'utilisateur. **Effet seulement avec un firmware recompilé** : le module est
solidifié dans le socle ; une carte qui tourne encore sur un ancien firmware garde l'ancien comportement, décrit à la fin.

`data/fs/gestionFileFolder.be::gestionFileFolder_listeEtRepartitLesFichiers`, à chaque démarrage (appelé par le prologue) :

- `/.extensions` est créé s'il manque, et les `.tapp` de la racine y sont rangés **au même démarrage**. Seuls les noms
  **finis par** `.tapp` sont pris : `x.tapp_`, `mon.tapp.bak` restent à leur place.
- Le fichier a déjà été lancé depuis `/` à ce démarrage (`tapp.be::autoexec_dir`, avant le prologue) : ce démarrage-là,
  il tourne sans figurer dans `/ext` (§ 2.4). Il repart de `/.extensions/` au démarrage suivant.
- Un fichier de même nom dans `/.extensions/` **est remplacé** : déposer une nouvelle version à la racine sert de mise à
  jour. Le journal le dit (`REPARTITION_FICHIERS: ... remplace la version en place`, niveau `info`).

`gestionFileFolder_deplaceFichier` déplace sans perdre : copie par morceaux de 2 Ko dans `<destination>.tmp`, taille relue
et comparée (un FS plein tronque), remplacement, **puis** suppression de l'original. Une panne laisse l'original et
l'ancienne version en place, retire le temporaire et journalise `REPARTITION_FICHIERS_ERREUR` ; le déplacement est retenté
au démarrage suivant. Les `.json`, `.html`, `.js` et `.css` passent par la même fonction. Banc sur FS en mémoire :
`outils_docs/scripts_python/berry/banc_repartition_fichiers.py`. **Non essayé sur un vrai LittleFS.**

Avec un firmware antérieur : l'original était supprimé **avant** l'écriture (FS plein ou coupure : fichier perdu), le
`.tapp` restait à la racine jusqu'au démarrage suivant si `/.extensions` manquait, et tout nom contenant `.tapp` était pris.

## 9. Ce qui reste à essayer (A10) et où écrire le résultat

À noter ci-dessous après l'essai, par ligne, avec la date, la carte et la sortie du journal :

| Fait à essayer sur carte | Résultat |
|---|---|
| Un `.tapp` posé dans `/.extensions/` est lancé avant `/autoexec.be`, une extension sans `add_extension` s'affiche « Stopped » | _à remplir_ |
| Gabarit A : `fsMqtt` chargé par minuterie ; sans la minuterie, ce qui casse (`logFonctions` absent ?) | _à remplir_ |
| Gabarit B : `unload_extension` retire driver, commande et règle ; l'`import` d'un fichier de l'archive après chargement échoue | _à remplir_ |
| `/ufsu` écrit dans `/.extensions/` par `build_ota_fs.py` ; MQTT `fsMqtt` aussi (binaire, MD5) | _à remplir_ |
| Déplacement des `.tapp` de la racine sur un firmware recompilé : rangé au même démarrage, archive identique, panne de FS plein | _à remplir_ |
| Entrée ZIP avec `/` dans son nom (§ 2.1) | _à remplir_ |
| Consommation de tas d'une extension A et B (mesure `tasmota.memory()` avant/après) | _à remplir_ |
| Une extension fautive et `SetOption153` (§ 2.3) | _à remplir_ |
