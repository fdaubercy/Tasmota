---
chantier: fichiers-berry-env
titre: Page web « Fichiers Berry par env » (port 7800, tuile de l'annuaire, cible Custom)
statut: actif
cree: 2026-10-25
maj: 2026-10-25
---
# Page web « Fichiers Berry par env » — plan d'implémentation

> **Pour l'exécutant :** sous-skill requise : superpowers:subagent-driven-development (recommandée) ou
> superpowers:executing-plans. Cocher une étape seulement après vérification, avec « — preuve : … ».

## Contexte

**But :** une page web (http://127.0.0.1:7800) pour (1) régler, env par env, l'état de chaque fichier Berry
(Sur le FS / Exclu / Solidifié) en écrivant `platformio_tasmota_cenv.ini`, et (2) créer un nouvel env à
partir d'une carte modèle (section du cenv, dossier `data/`, section de `user_config_override.h`).

**Spec :** `docs/superpowers/specs/2026-10-25-page-fichiers-berry-design.md` — à lire en entier avant toute
action ; « §x » ci-dessous renvoie à ses sections, « choix 7.x » à son §7.

**Architecture :** outil PC Python **stdlib** dans `outils_docs/scripts_python/outils_pc/`, squelette de
`build_web.py` (`ThreadingHTTPServer`, `fabrique_gestionnaire`, `acces_web.Acces`, `traite_post` dont les
exceptions donnent `LookupError`→404, `ValueError`/`TypeError`→400, `RuntimeError`→409). Modules purs
(lecture/résolution, état, écriture, création) testés sans serveur ; serveur et page par-dessus.

**Bancs :** au modèle de `test_build_envs.py` (`ECHECS`, `verifie(obtenu, attendu, libelle)`, `principal()`,
**code de sortie 0 = vert**), dépôt d'essai dans un `tempfile.TemporaryDirectory()` ; lancés avec
`"$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/test_fichiers_berry_<x>.py`.

### Contraintes globales (valent pour toutes les actions)

- Port **7800** ; nom d'accès `"Fichiers Berry par env"` identique dans `acces_web.Acces(...)` et dans le
  registre de l'annuaire (vérifié par `test_annuaire.py` l.50-56) ; en-tête POST `X-Fichiers-Berry: 1` +
  `acces.origine_autorisee`.
- **Aucun `pio run`** (ni `--list-targets`) par l'exécutant ; **aucune écriture des vrais fichiers** par un
  banc (dépôt d'essai seulement ; `test_vrais_fichiers` en lecture seule).
- Écriture **refusée pendant un build** : `build_serie.builds_en_cours_defaut()` (liste non vide **ou None**
  → refus, comme `build_web.py:194`), injectable pour les bancs.
- Les trois fichiers écrits sont en **CRLF** (cenv, `user_config_override.h`, `_persist.json`) : fins de ligne
  et encodage conservés, lecture/écriture en octets (`utf-8`, `errors="surrogateescape"`).
- Chemins écrits relatifs à la racine, séparateur `/` ; comparaison des entrées sur le chemin normalisé.
- Fichiers < 500 lignes (sinon le signaler et demander, ne pas compresser) ; textes de la page en français.
- Commits en français **sans accents**, **sans trailer `Co-Authored-By`** (CLAUDE.md du dépôt), un commit
  par action ; rien poussé.

### Points de relecture (cas que la spec implique et que les tests nominaux ne couvrent pas)

1. **Liste héritée d'un fichier de l'amont** (`custom_files_upload` de `env:tasmota32s3` dans
   `platformio_tasmota32.ini`) : retirer une de ses entrées est refusé (« liste de l'amont ») ; en ajouter une
   dans la base du cenv l'ajoute à l'option propre de la base → test `ecriture_refuse_amont` (A3).
2. **Commentaire en fin de ligne de valeur** (`data/fs/x.be   ; raison (2026-10-25)`) : l'entrée est lue
   sans le commentaire ; la retirer retire la ligne entière ; les autres commentaires restent intacts →
   test `lecture_commentaire_en_ligne` (A1), `ecriture_retire_ligne_commentee` (A3).
3. **Même fichier dans deux listes** (socle ET liste propre, ou exclu ET solidifié) : marqué incohérent ;
   un changement d'état le retire de toutes → test `etat_doublon` (A2), `ecriture_doublon_partage` (A3).
4. **Exclusion par NOM de fichier** (`post_esp32.py:216`, `os.path.basename`) : un `.be` de la carte qui
   porte le nom d'un `.be` de `data/fs` serait exclu avec lui → la page signale l'homonyme → test
   `etat_homonyme` (A2).
5. **Persist avec octets non ASCII et CRLF** (rideau) : après création, seuls les 8 spans d'identité
   diffèrent, octet pour octet → test `creation_persist_octets` (A4).

---

## A1 — Lecture et résolution du `.ini` (`fichiers_berry_ini.py`)

Fichiers : créer `outils_pc/fichiers_berry_ini.py`, `outils_pc/test_fichiers_berry_ini.py`.
Produit (utilisé par A2 à A6) :
- `@dataclass Entree(chemin: str, section: str, option: str, fichier: str, ligne: int, commentaire: str)` —
  `section` = section où la ligne est écrite (`env:x` ou `berry_commun`), `fichier` = nom du `.ini`, `ligne` =
  index 0 dans ce fichier.
- `lit_sections(racine) -> Ini` : toutes les sections (pas seulement `env:*`) des 4 `.ini` de
  `build_envs.FICHIERS_INI`, dans cet ordre (le dernier l'emporte), avec pour chaque option le texte brut et
  les numéros de ligne de chaque ligne de valeur.
- `Ini.chaine(env) -> list[str]` (`extends`, garde contre les cycles) ; `Ini.definie_dans(env, option) -> str|None`.
- `resout(ini, env, option) -> list[Entree]` : valeur résolue, `${section.option}` et `${env:X.option}`
  développés récursivement (profondeur illimitée, `ValueError` sur cycle), lignes vides et commentaires
  ignorés, chaque entrée gardant sa ligne d'origine.
- `envs_touches(ini, section, option) -> list[str]` : envs du cenv dont `resout(..., option)` traverse
  `(section, option)`, triés.

- [x] Écrire `test_fichiers_berry_ini.py` avec un `CENV` d'essai (CRLF) contenant `[berry_commun] socle/modbus`,
  une base, deux cartes (dont une qui hérite `custom_files_exclude`), et un `ENV32` d'amont : tests
  `resout_socle_et_propre` (provenances `berry_commun`/`env:carte`), `resout_cascade_env` (3 niveaux),
  `resout_cycle` (`ValueError`), `lecture_commentaire_en_ligne` (point 1/2), `envs_touches_socle` (= les 2
  cartes + la base qui l'utilisent), `test_vrais_fichiers` (lecture seule : `resout` du P4 contient
  `data/fs/udpFonctions.be` venu de `berry_commun`). — preuve : test_fichiers_berry_ini.py (7 tests + vrais fichiers)
- [x] Lancer le banc : ROUGE (module absent). — preuve : ModuleNotFoundError fichiers_berry_ini
- [x] Écrire `fichiers_berry_ini.py` (parseur ligne à ligne propre — écart assumé à la spec §6 « réutiliser
  `build_envs` » : `ConfigParser` perd les numéros de ligne, indispensables pour réécrire ; la liste et la
  famille des envs restent prises à `build_envs.liste_envs` ;
  une ligne de continuation commence par un blanc ; `;`/`#` précédé d'un blanc = commentaire en ligne). — preuve : outils_pc/fichiers_berry_ini.py
- [x] Banc VERT, et témoin : remplacer `${berry_commun.socle}` par `${berry_commun.socl}` dans le `CENV`
  d'essai → `resout_socle_et_propre` doit passer ROUGE. — preuve : banc VERT ; temoin socl -> 4 KO
- [x] Commit `feat(fichiers-berry): lecture et resolution des listes du cenv`. — preuve : 5f4666819

## A2 — Recensement et état d'un env (`fichiers_berry_etat.py`)

Fichiers : créer `outils_pc/fichiers_berry_etat.py`, `outils_pc/test_fichiers_berry_etat.py`.
Consomme A1. Produit :
- `dossier_carte(env: str) -> str` : règle de `transform_name` (`pre_utilitaires_platformio.py:256`, recopiée,
  pas importée : SCons) ; `ValueError` sans tiret.
- `recense(racine, env) -> list[dict]` : `{"chemin", "groupe": "fs"|"carte"|"amont"}` — `data/fs/*.be`,
  `<dossier_carte>/*.be` (aucun pour une base), `tasmota/berry/modules/*` de premier niveau en `.bec`/`.tapp`/`.be` ;
  dossiers `*sauvegarde*` ignorés.
- `etat_env(racine, env) -> dict` : `{"env", "dossier_carte", "exclude_solidified": bool, "fichiers": [
  {"chemin", "groupe", "etat": "fs"|"exclu"|"solidifie"|"absent", "figes": bool, "provenances": [{"option",
  "section", "partagee": bool, "amont": bool, "envs": [...]}], "incoherent": bool, "homonyme": str|None}],
  "hors_perimetre": [Entree...], "disparus": [Entree...]}`. Règles : spec §2.1, §2.2, choix 7.3, 7.4 ;
  `figes` = `autoexec.be` ; `partagee` = la ligne n'est pas dans la section de l'env ; `amont` = son fichier
  n'est pas le cenv.
- `envs_proposes(racine) -> list[dict]` : `{"nom", "famille": "cartes"|"bases"}` — envs ESP32 du cenv
  (choix 7.7 ; ESP8266 = `extends` qui remonte à `env:tasmota` sans `tasmota32`).

- [x] Tests : `recense_carte` (dépôt d'essai : 3 `data/fs`, 2 carte, 1 amont, un dossier `*sauvegarde*` ignoré),
  `etat_trois_etats`, `etat_amont_absent` (module amont hors `custom_files_upload` → `absent`),
  `etat_doublon` (point 3), `etat_homonyme` (point 4), `etat_hors_perimetre` (`data/sd/js/x.js.gz` exclu →
  `hors_perimetre`), `etat_disparu` (ligne vers un fichier absent), `etat_sans_exclude_solidified`,
  `envs_proposes_sans_esp8266`, `dossier_carte_vrais_envs` (lecture seule : pour chaque env de carte du vrai
  cenv, `dossier_carte` = le dossier `data/` qui figure dans son `custom_files_upload` résolu). — preuve : test_fichiers_berry_etat.py (10 tests)
- [x] Banc ROUGE, puis écrire le module, banc VERT ; témoin : neutraliser l'exclusion `*sauvegarde*` →
  `recense_carte` ROUGE. — preuve : ROUGE (module absent) puis VERT ; temoin autoexec amont admis -> recense_carte KO
- [x] Commit `feat(fichiers-berry): recensement et etat des fichiers par env`. — preuve : 52fd3c907

## A3 — Changements d'état et écriture du cenv (`fichiers_berry_ecriture.py`)

Fichiers : créer `outils_pc/fichiers_berry_ecriture.py`, `outils_pc/test_fichiers_berry_ecriture.py`.
Consomme A1, A2. Produit :
- `@dataclass Demande(chemin: str, etat: str, raison: str = "", partage_accepte: bool = False)`.
- `prepare(racine, env, demandes: list[Demande]) -> dict` : `{"diff": str (unified, par fichier),
  "empreinte": sha256 hex du cenv lu, "confirmations": [{"chemin", "section", "option", "envs"}],
  "commentaires_cites": [{"ligne", "texte"}], "refus": [str]}`. Une demande qui touche une liste partagée
  sans `partage_accepte` → listée dans `confirmations`, non appliquée. Retrait d'une entrée dont le fichier
  n'est pas le cenv → `refus` (« liste de l'amont »).
- `enregistre(racine, env, demandes, empreinte, builds_en_cours) -> dict` : recalcule, `RuntimeError` si
  build (liste non vide ou None), si l'empreinte a changé, si `confirmations` ou `refus` non vides ; copie
  `.bak` puis écrit ; renvoie `{"ecrit": True, "diff"}`.
- Règles d'écriture (spec §2.5, choix 7.1, 7.5) : ajout = nouvelle ligne de continuation en fin de l'option,
  indentée comme ses voisines, suivie de `; <raison> (AAAA-MM-JJ)` si raison ; option héritée non définie →
  `option = ${env:<ancêtre qui la définit>.option}` + la ligne ; option absente partout → `option = <chemin>`,
  insérée après la dernière ligne de valeur de la section ; retrait = suppression de la ligne (si c'est la
  ligne `option = x`, la 1re continuation remonte ; option vidée → `option =` gardée, pour ne pas réactiver
  un héritage) ; un changement d'état retire le fichier de **toutes** les listes où il figure.

- [x] Tests (sur dépôt d'essai CRLF) : `ecriture_ajout_exclu`, `ecriture_option_heritee` (la chaîne
  `${env:base...}` apparaît, l'héritage reste dans `resout`), `ecriture_option_absente`, `ecriture_partage_confirme`
  (sans `partage_accepte` → `confirmations` = envs de `envs_touches`, cenv inchangé ; avec → ligne retirée de
  `[berry_commun]`), `ecriture_refuse_amont` (point 1), `ecriture_retire_ligne_commentee` (point 2),
  `ecriture_doublon_partage` (point 3), `ecriture_garde_commentaires` (tous les `;` hors ligne retirée
  identiques), `ecriture_crlf` (aucun `\n` nu), `ecriture_raison`, `commentaires_cites` (un `; LoRaWan …` au-dessus
  de l'option est cité quand `loRaWanFonctions.be` bouge), `refus_build` (liste `["pio run"]` et `None`),
  `refus_empreinte` (cenv touché entre `prepare` et `enregistre`), `bak_present`, et `relu_par_platformio` :
  le cenv écrit relu par `platformio.project.config.ProjectConfig` du penv donne pour l'env la même liste que
  `resout` (preuve de la contrainte §6 « trois lecteurs »). — preuve : test_fichiers_berry_ecriture.py (16 tests, dont relu_par_platformio)
- [x] Banc ROUGE, puis écrire le module, banc VERT ; témoin : écrire en `\n` → `ecriture_crlf` ROUGE. — preuve : ROUGE (module absent) puis VERT ; temoin ecriture LF -> 6 KO
- [x] Commit `feat(fichiers-berry): ecriture des listes du cenv (diff, empreinte, listes partagees)`. — preuve : d6bc80ed0

## A4 — Création d'un env depuis une carte modèle (`fichiers_berry_creation.py`)

Fichiers : créer `outils_pc/fichiers_berry_creation.py`, `outils_pc/test_fichiers_berry_creation.py`.
Consomme A1, A2. Produit :
- `CHAMPS_IDENTITE = ("CODE_IMAGE_STR", "PROJECT", "WIFI_IP_ADDRESS", "WIFI_RGX_SSID", "MQTT_CLIENT_ID",
  "MQTT_TOPIC", "MQTT_GRPTOPIC", "FRIENDLY_NAME")`.
- `CLES_PERSIST = {"serveur.nom": "FRIENDLY_NAME", "serveur.hostname": "PROJECT", "serveur.IP.IPAddress":
  "WIFI_IP_ADDRESS", "serveur.mqtt.client": "MQTT_CLIENT_ID", "serveur.mqtt.topic": "MQTT_TOPIC",
  "serveur.mqtt.groupTopic1": "MQTT_GRPTOPIC", "serveur.rangeExtender.AP.SSID": "WIFI_RGX_SSID",
  "template.NAME": "CODE_IMAGE_STR"}` (dernière correspondance : choix de Claude).
- `identite_par_defaut(lieu, nom) -> dict` (choix de Claude, modèle = le rideau) : `PROJECT` = `NOM-LIEU` en
  majuscules, `MQTT_CLIENT_ID` = `PROJECT`, `MQTT_TOPIC` = `lieu/nom`, `MQTT_GRPTOPIC` = `tasmotas/lieu`,
  `WIFI_RGX_SSID` = `PROJECT-GATEWAY`, `FRIENDLY_NAME` = `CODE_IMAGE_STR` = nom, tirets → espaces, initiale
  majuscule, `WIFI_IP_ADDRESS` = `0.0.0.0`.
- `nom_env(base, lieu, nom) -> str` = `<1er segment de base>-<lieu>-<nom>` ; `define(base, lieu, nom) -> str` =
  `FIRMWARE_<ESP32|ESP32S3|ESP32P4>_<LIEU>_<NOM>` (`-` → `_`). `lieu` : `[a-z0-9]+` ; `nom` : `[a-z0-9]+(-[a-z0-9]+)*`.
- `prepare_creation(racine, modele, base, lieu, nom, identite, define) -> dict` : `{"env", "dossier", "diff"
  (cenv + .h + persist, secrets masqués), "empreinte" (sha256 cenv + .h), "avertissements", "refus"}`.
- `cree(racine, ..., empreinte, builds_en_cours) -> dict` : mêmes refus que A3 + refus de §2.6 ; `.bak` des
  deux fichiers ; copie du dossier modèle (hors `*sauvegarde*`) ; rien n'est commité.
- Règles (spec §2.6) : section du cenv = celle du modèle (de `[env:` jusqu'avant le bloc de commentaires qui
  précède la section suivante), en-tête renommé, `extends` et `${env:<ancienne base>.` → nouvelle base, define
  remplacé, lignes actives `upload_port`/`monitor_port` retirées, chemins `<dossier modèle>` → nouveau dossier,
  `custom_files_upload = ${env:<base>.custom_files_upload}` + nouveau dossier ; insertion après le dernier env
  du même lieu (segment 2), sinon en fin de fichier sous un bandeau `; LOCALISATION: <LIEU>` au format
  existant. Section `.h` = du commentaire `        // -- Options for …` jusqu'avant le suivant, insérée
  après celle du modèle, ouverte par `#elif defined(<define>)` même si le modèle ouvre la chaîne par `#if … || …`
  (conditions internes citant l'ancien define → `avertissements`) ; defines d'identité, `Hostname` de
  `USER_BACKLOG` et `NAME` de `USER_TEMPLATE` remplacés. Persist : remplacement des seuls spans de valeur des
  `CLES_PERSIST`, repérés par un petit analyseur JSON qui suit le chemin de clés (pas de `json.dumps`).
- Refus : env, dossier ou define existant ; IP ≠ `0.0.0.0`, `MQTT_TOPIC` ou `MQTT_CLIENT_ID` déjà présents dans
  une autre section du `.h` ou un autre `data/**/_persist.json` (hors `*sauvegarde*`) ; nom invalide ; build.

- [x] Tests (dépôt d'essai bâti en recopiant la vraie section rideau du cenv, sa section du `.h` et son dossier
  `data/` réel) : `creation_nom_et_define`, `creation_section_cenv` (relue par `ProjectConfig` : `extends`,
  define, pas d'`upload_port`, `custom_files_upload` = base + dossier), `creation_chemins_reecrits`
  (`controleRideau.be` pointe vers le nouveau dossier), `creation_section_h` (8 defines + `USER_BACKLOG` +
  `NAME`), `creation_modele_cave` (`#if … || …` → `#elif`, avertissement), `creation_persist_octets`
  (point 5), `creation_insertion_lieu` (après le dernier env garage / nouveau bandeau pour `jardin2`),
  `refus_identite_prise` (topic `garage/rideau`), `refus_existant`, `diff_masque` (aucune valeur de
  `STA_PASS*` ni mot de passe du persist dans `diff`), `refus_build`, et `nouvelle_carte_vue_par_build`
  (`build_envs.liste_envs` du dépôt d'essai contient le nouvel env en famille `cartes`). — preuve : test_fichiers_berry_creation.py (10 tests sur copie du depot reel)
- [x] Banc ROUGE, puis écrire le module, banc VERT ; témoin : désactiver le masquage → `diff_masque` ROUGE. — preuve : ROUGE (module absent) puis VERT ; temoin masquage coupe -> diff_masque KO
- [x] Commit `feat(fichiers-berry): creation d un env depuis une carte modele`. — preuve : f0e234c63

## A5 — Serveur web (`fichiers_berry_web.py`)

Fichiers : créer `outils_pc/fichiers_berry_web.py`, `outils_pc/test_fichiers_berry_web.py`.
Consomme A2-A4. Produit les routes (JSON) :
- `GET /` (page de A6, repli provisoire si `ImportError`), `GET /execution` → `{"en_cours": false}` (lu par la
  cible, A7), `GET /envs` → `{"envs": envs_proposes}`, `GET /etat?env=X` → `etat_env` (recensement refait à
  chaque appel, spec §2.2).
- `POST /prepare` `{env, demandes}` → `prepare` ; `POST /enregistre` `{env, demandes, empreinte}` → `enregistre` ;
  `POST /creation/prepare` et `POST /creation` → A4.
- `principal()` : `--http` (défaut 7800) + `acces_web.ajoute_options` ; `acces_web.Acces(args.http, args.local,
  "Fichiers Berry par env")` ; `builds_en_cours` injectable (attribut de module) pour les bancs.

- [ ] Tests (serveur sur port libre, dépôt d'essai, `builds_en_cours` simulé) : `get_etat`, `post_sans_entete`
  (403), `post_enregistre` (cenv modifié), `post_pendant_build` (409), `post_empreinte_perimee` (409),
  `post_creation`, `get_env_inconnu` (404).
- [ ] Banc ROUGE, puis écrire le module, banc VERT ; témoin : retirer le contrôle de l'en-tête →
  `post_sans_entete` ROUGE.
- [ ] Commit `feat(fichiers-berry): serveur web port 7800`.

## A6 — Page (disposition B) et sonde Chrome (`fichiers_berry_page.py`)

Fichiers : créer `outils_pc/fichiers_berry_page.py` (`PAGE = r"""…"""`), `outils_pc/test_fichiers_berry_page_chrome.py`
(au modèle de `test_build_page_chrome.py` : Chrome headless + CDP stdlib, serveur sous test en processus fils
`--serveur PORT DEPOT`, dépôt d'essai, `builds_en_cours` = `[]`, témoin `INJECTION_TEMOIN`).
Contenu (spec §2.3-§2.6, maquette B validée) : choix de l'env (présélection par `?env=`), « Revérifier les
fichiers », liste déroulante des fichiers + radios (libellés « Sur le FS / Absent » pour l'amont ; `autoexec.be`
figé ; « Solidifié » montre le rappel des conditions de §2.5), « Appliquer » (modifications en attente gardées
dans la page ; liste partagée → fenêtre « Modifier la liste partagée (N envs : …) » / « Annuler »), trois
colonnes avec badges de provenance et marques (en attente, incohérent, homonyme, hors périmètre, disparu),
avertissement si `exclude_solidified` est faux, « Voir le diff puis enregistrer » (diff, commentaires cités,
rappel « le build suivant repart de zéro », champ « raison » par ajout), bouton « Créer un env à partir de… »
(formulaire de §2.6, champs préremplis par `identite_par_defaut` via `/creation/prepare`), et après un
enregistrement le lien « Construire / téléverser le FS » vers `http://127.0.0.1:7700/?env=<nom>`.

- [ ] Sonde : chargement sans erreur JS, `?env=` présélectionne, Appliquer sur un fichier du socle ouvre la
  fenêtre partagée avec la liste des envs, Annuler ne laisse rien en attente, diff affiché puis enregistrement
  (cenv d'essai modifié), formulaire de création prérempli ; témoin `INJECTION_TEMOIN` → ROUGE détecté.
- [ ] Sonde ROUGE, puis écrire la page, sonde VERTE.
- [ ] Commit `feat(fichiers-berry): page disposition B et sonde Chrome`.

## A7 — Accès : cible Custom, tâche VS Code, annuaire

Fichiers : créer `build/cible_fichiers_berry.py` et `build/test_cible_fichiers_berry.py` (copies adaptées de
`cible_build_web.py` / `test_cible_build_web.py` : `NOM_CIBLE = "fichiers_berry"`, `PORT_DEFAUT = "7800"`,
option `custom_fichiers_berry_http`, console `consoles/fichiers_berry.log`, titre de cible « Fichiers Berry par
env (page web) ») ; modifier `build/pre_utilitaires_platformio.py` (import + `enregistre(env)` après l.743-744,
`NOM_CIBLE` ajouté à `CIBLES_HORS_BUILD` l.758-760 et à son commentaire) ; `.vscode/tasks.json` : tâche
« Outil : fichiers Berry par env (http://127.0.0.1:7800) » sur le modèle de celle de la page build (l.191-201 :
`${env:USERPROFILE}\\.platformio\\penv\\Scripts\\python.exe`, jamais `${userHome}`), et corriger au passage son
commentaire périmé « pas de cible PlatformIO Custom » ; `outils_pc/annuaire_registre.py`
(entrée `Outil("fichiers_berry", "Fichiers Berry par env", "Fichiers Berry par env", GROUPES[2], …,
DOSSIER + "outils_pc/fichiers_berry_web.py", [_port("http", 7800)], "http", "Console capturée : " +
CONSOLE.format("fichiers_berry"))`, `dans_job=True`, pas de `route_occupe`) ; `outils_pc/test_annuaire.py`
(l.43-44 : ids + `"fichiers_berry"` ; l.342-345 : 7 → 8).

- [ ] `test_cible_fichiers_berry.py` ROUGE, écrire la cible, VERT ; `test_annuaire.py` mis à jour VERT.
- [ ] Vérifier par lecture que `CIBLES_HORS_BUILD` contient la cible (pas de `pio run --list-targets`, leçon du
  2026-10-17) ; demander à l'utilisateur de rafraîchir Project Tasks hors build et de lancer la cible une fois.
- [ ] Tâche VS Code lancée une fois (Tasks: Run Task) avant d'être annoncée (leçon du 2026-10-13).
- [ ] Commit `feat(fichiers-berry): cible Custom et tuile de l annuaire`.

## A8 — Liens croisés avec la page build

Fichiers : modifier `outils_pc/build_page.py` (`ligneEnv(e)` l.335 : lien « Régler ses fichiers » →
`http://127.0.0.1:7800/?env=<nom>` ; lecture de `?env=` au chargement (`chargeEnvs`) qui coche cet env) et
`outils_pc/test_build_page_chrome.py` (le lien existe, `?env=` coche l'env).

- [ ] Sonde de la page build ROUGE sur les 2 nouveaux contrôles, puis modification, VERTE ; bancs `test_build_*.py`
  tous VERTS.
- [ ] Commit `feat(build): liens croises avec la page Fichiers Berry par env`.

## A9 — Documentation et essai réel avec l'utilisateur

- [ ] `outils_docs/README.md` : section « Fichiers Berry par env (page web) » ; `CLAUDE.md` : entrée dans la carte
  des documents (modules, port, bancs) et nouveau compte de lignes de `build_page.py` ; `.claude/skills/bancs/SKILL.md` :
  bancs `test_fichiers_berry_*.py` (et signaler que les `test_build_*` y manquent).
- [ ] Essai réel **avec l'utilisateur, hors build** : passer un fichier propre d'un env en « Exclu » puis le
  rétablir ; `git diff platformio_tasmota_cenv.ini` vide à la fin.
- [ ] Essai réel : liste partagée → la fenêtre nomme les bons envs ; « Annuler » ne change rien.
- [ ] Essai réel de création (carte choisie par l'utilisateur), relecture du diff des 3 fichiers par l'utilisateur,
  puis suppression de l'essai si ce n'était qu'un test (`.bak` à l'appui).
- [ ] Commit `docs: page Fichiers Berry par env (README, CLAUDE.md, bancs)` ; `statut: clos` quand tout est coché.

## Améliorations restantes

- [ ] [projet] Supprimer ou renommer un env depuis la page (hors périmètre de la spec).
- [ ] [projet] Ajouter les bancs `test_build_*.py` à la skill `bancs`.

## Vérification

Tous les bancs `test_fichiers_berry_*.py`, `test_cible_fichiers_berry.py`, `test_annuaire.py` et `test_build_*.py`
VERTS, sondes Chrome VERTES avec témoin ROUGE, essais réels d'A9 faits avec l'utilisateur.
