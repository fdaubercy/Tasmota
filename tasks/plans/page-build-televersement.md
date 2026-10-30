---
chantier: page-build-televersement
titre: Page web « Build et téléversement » (port 7700, tuile de l'annuaire)
objectif: Compiler et téléverser en série (COM ou OTA) les envs cochés depuis une page web, avec progression en direct
statut: actif
cree: 2026-10-24
maj: 2026-10-30
---
# Page web « Build et téléversement » — plan d'implémentation

> **Pour l'exécutant :** sous-skill requise : superpowers:subagent-driven-development (recommandée) ou
> superpowers:executing-plans. Cocher une étape seulement après vérification, avec « — preuve : … ».

## Contexte

**But :** une page web (http://127.0.0.1:7700, tuile de l'annuaire :7600) qui lance en série, sur les
environnements cochés, compiler / téléverser le firmware / construire le FS / téléverser le FS, en COM ou
en OTA choisi par ligne, avec étape, %, durées et échecs en direct.

**Spec :** `docs/superpowers/specs/2026-10-24-page-build-televersement-design.md` — à lire avant toute
action ; les « choix 1 à 17 » cités ci-dessous sont ceux de sa section « Choix faits par Claude ».

**Architecture :** outil PC Python **stdlib** (+ pyserial du penv PlatformIO pour tester un port) dans
`outils_docs/scripts_python/outils_pc/`, squelette de `maintenance/synchro_fork_web.py` (serveur
`ThreadingHTTPServer`, `acces_web`, flux SSE rejouable). Un module par responsabilité : envs (lecture et
écriture des `.ini`, IP OTA), progression (analyse de la sortie pio, pur), série (exécution des `pio run`),
OTA (firmware et FS), page, serveur. L'OTA du firmware est envoyée par la page elle-même (`/u2`,
protocole de `espupload.py`), sans toucher au `.ini` ni aux scripts de build (spec choix 7 révisé).

**Bancs :** scripts `test_build_*.py` au modèle de `test_annuaire.py` (fonction `verifie(obtenu, attendu,
libelle)`, liste `ECHECS`, **code de sortie 0 = vert**), lancés avec le Python du penv :
`"%USERPROFILE%\.platformio\penv\Scripts\python.exe" -u outils_docs/scripts_python/outils_pc/test_build_<x>.py`.

### Contraintes globales (valent pour toutes les actions)

- **Jamais de `pio run` lancé par l'exécutant pendant la mise au point** (ni `--list-targets`) : les bancs
  utilisent un faux pio (A3). Les essais réels (A8) se font **avec l'utilisateur**, après lui avoir demandé,
  hors de tout build de sa part.
- Port **7700** ; nom d'accès `"Build et téléversement"` identique dans le registre et dans
  `acces_web.Acces(port, local, "Build et téléversement")`.
- Fils pio : `%USERPROFILE%\.platformio\penv\Scripts\pio.exe` (surchargeable par la variable
  `BUILD_WEB_PIO` pour les bancs), `cwd` = racine du dépôt, `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`,
  arbre tué par `taskkill /T /F /PID`.
- **Jamais** `PLATFORMIO_UPLOAD_PORT` ni `PLATFORMIO_EXTRA_SCRIPTS` (entrent dans l'empreinte → purge de
  `.pio/build`) : port COM par `--upload-port`.
- Données hors dépôt : `acces_web.dossier_donnees() / "build"` (`journaux/`, `persist/`, `derniers.json`,
  `references.json`).
- Toute requête HTTP vers une carte porte `Referer: http://<ip>/`.
- Textes de la page et logs en français ; commentaires au niveau des outils voisins ; commits en français
  sans accents, sans trailer `Co-Authored-By`, un commit par action, rien poussé sans demande.

### Points de relecture (cas que la spec implique et qu'aucun test « nominal » ne couvre)

1. Env dont le `upload_port` vient d'un `extends` (`tasmota32s3-garage-serveur-modbus` hérite COM11, ligne
   locale commentée `; upload_port = COM10`) : la page montre COM11 ; l'écriture ajoute une ligne active
   dans la section fille sans décommenter la ligne `;` → test `ecrit_port_herite` (A1).
2. Commentaire en fin de ligne (`upload_port = COM11          ; <- commente pour…`) : la réécriture garde le
   commentaire → test `ecrit_port_garde_commentaire` (A1).
3. Sortie pio avec codes ANSI et chemins `\` Windows → tests `progression_ansi`, `progression_chemins`
   (A2).
4. Carte injoignable pendant l'OTA du FS : aucun fichier envoyé, env en échec, série continue → test
   `ota_fs_persist_injoignable` (A4) et `serie_continue_apres_echec` (A3).
5. Build lancé dans VS Code entre deux envs : la série attend, puis reprend → test
   `serie_attend_build_externe` (A3).

## A1 — Environnements : liste, classement, port COM, IP OTA (`build_envs.py`)

Fichiers : créer `outils_pc/build_envs.py`, `outils_pc/test_build_envs.py`.

Interfaces produites :
- `@dataclass Env(nom: str, famille: str, sous_groupe: str, port: str, port_herite: bool, ip: str,
  ota_possible: bool, firmware: str, ecrivable: bool)` — `famille` ∈ `"cartes" | "bases" | "amont"` ;
  `sous_groupe` (amont seulement) ∈ `"safeboot" | "esp32" | "langues" | "esp8266"` ; `ip` = `""` si absente
  ou `0.0.0.0` ; `ecrivable` = défini dans `platformio_tasmota_cenv.ini`.
- `liste_envs(racine: Path) -> list[Env]`
- `ecrit_port(racine: Path, env: str, port: str) -> None` (lève `ValueError` si env non écrivable ou port
  invalide ; `port == ""` supprime la ligne active de la section).
- `lit_ip_ota(texte_h: str, firmware: str) -> str`

- [x] Banc d'abord, sur des `.ini` et un `.h` d'essai écrits dans un dossier temporaire (pas les vrais
  fichiers) : `classement` (un env cenv sans `-base` → `cartes` ; `tasmota32s3-base-N16R8` → `bases` ;
  `tasmota32-FR` → `amont/langues` ; `tasmota32c3-safeboot` → `amont/safeboot` ; `tasmota-lite` →
  `amont/esp8266` ; `[env:tasmota32_base]` et `[env:tasmota32_idf55_base]` absents de la liste),
  `port_direct`, `port_herite` (via `extends`, `port_herite=True`), `port_absent` (`""`),
  `ecrit_port_modifie`, `ecrit_port_ajoute`, `ecrit_port_herite`, `ecrit_port_garde_commentaire`,
  `ecrit_port_vide_supprime`, `ecrit_port_refuse_amont`, `ecrit_port_refuse_injection` (`"COM3\n[env:x]"`
  refusé ; seul `^COM\d{1,3}$` accepté), `ecrit_port_sauvegarde` (`.bak` créé), `ip_bloc_simple`,
  `ip_bloc_ou` (`defined(A) || defined(B)`), `ip_dhcp_vide` (`0.0.0.0` → `""`), `ota_esp8266_grise`. — preuve : test_build_envs.py (commit 96b061b83)
- [x] Vérifier que le banc échoue (module absent). — preuve : ROUGE ModuleNotFoundError, task-1-report
- [x] Implémenter `build_envs.py` : `configparser` (sans interpolation de PlatformIO, résolution
  d'`extends` à la main, sections `env:*` de `platformio_tasmota_env32.ini`, `platformio_tasmota_env.ini`,
  `platformio_tasmota_cenv.ini`, `platformio_override.ini`) ; `firmware` = dernier `-D FIRMWARE_*` des
  `build_flags` résolus ; `lit_ip_ota` reprend l'algorithme de
  `build/ota-files-uploader.py:_lire_ip_override` (l.46-88 : blocs `#if/#elif`, profondeur) ;
  `ota_possible` = l'env hérite de `[env:tasmota32_base]` (pré-script chargé), faux pour ESP8266 ;
  `ecrit_port` réécrit le fichier **ligne à ligne** (pas `configparser.write`) pour garder commentaires et
  alignement. — preuve : commits 96b061b83, 55493e83c (OTA par pre-script, fusion des ini)
- [x] Banc vert ; plus un contrôle sur les **vrais** fichiers en lecture seule : 15 envs cenv listés,
  `tasmota32s3-garage-capteurs-cuve-modbus` → COM12, `tasmota32s3-garage-serveur-modbus` → COM11 hérité. — preuve : test_build_envs.py 51 OK, sortie 0 (2026-10-24)
- [x] Commit `feat(build-web): liste et classement des environnements, port COM et IP OTA`. — preuve : 96b061b83 + 55493e83c, 85ec18057

## A2 — Progression : lecture de la sortie pio (`build_progression.py`)

Fichiers : créer `outils_pc/build_progression.py`, `outils_pc/test_build_progression.py`.

Interfaces produites :
- `class Suivi(action: str, reference_o: int | None)` — `action` ∈ `"compiler" | "upload" | "buildfs" |
  "uploadfs"` ; méthode `ligne(texte: str) -> dict | None` renvoie un événement
  `{"etape": str, "pourcent": int | None, "detail": str}` quand l'état change ; attributs `nb_o: int`,
  `resultat: "succes" | "echec" | None`, `extrait_erreur: list[str]` (10 dernières lignes `error:` /
  `Error` / `FAILED`), `fs_aussi: bool` (ligne `post_esp32` « Utilisera une commande de téléchargement
  personnalisée… »).
- `retire_ansi(texte: str) -> str`
- Étapes : `"Pré-build"`, `"Compilation"`, `"Édition des liens"`, `"Téléversement"`,
  `"Construction du FS"`.

- [x] Banc d'abord, sur des lignes d'essai : `progression_compilation` (avec `reference_o=1680`, 840
  lignes `Compiling .pio\build\e\src\x.o` → 50 %), `progression_sans_reference` (`pourcent` None, `detail`
  « 840 fichiers »), `progression_ansi`, `progression_chemins` (`/` et `\`), `progression_liens`
  (`Linking …firmware.elf` → étape « Édition des liens »), `progression_esptool` (`Writing at 0x00010000
  [=====>   ] 45.2% …` et l'ancien format `(45 %)` → 45), `progression_succes` (`[SUCCESS] Took 251.3
  seconds`), `progression_echec` (`[FAILED]` + extrait d'erreur), `progression_fs_aussi`, `pourcent_borne`
  (jamais > 99 avant le SUCCESS). — preuve : test_build_progression.py (commit 886802f53)
- [x] Vérifier que le banc échoue. — preuve : ROUGE ModuleNotFoundError, task-2-report
- [x] Implémenter (expressions régulières sur la ligne sans ANSI ; durées **non** lues dans la sortie :
  mesurées par A3). — preuve : commits 886802f53, 7de6dc9f0
- [x] Banc vert. — preuve : test_build_progression.py vert, sortie 0 avec -W error (2026-10-24)
- [x] Commit `feat(build-web): suivi de progression de la sortie pio`. — preuve : 886802f53 + 7de6dc9f0
- [x] **Calibrage** (pendant A8) : rejouer une vraie sortie de build et d'upload, ajuster les expressions,
  garder cette sortie (tronquée) comme jeu d'essai du banc. — preuve : journaux P4 et cuve du 2026-10-25 rejoués ; objets du cache, increment, zones esptool ; build_sortie_reelle_cuve.txt (commit 40f9f0726)

## A3 — Exécution en série (`build_serie.py`) et faux pio

Fichiers : créer `outils_pc/build_serie.py`, `outils_pc/build_faux_pio.py` (rejoue un scénario : lignes,
délais, code de sortie), `outils_pc/test_build_serie.py`.

Interfaces :
- Consomme : `Env`, `liste_envs` (A1) ; `Suivi` (A2) ; `envoie_fs_ota` (A4, appelée par injection pour
  que A3 se teste avant A4).
- Produit : `@dataclass Ligne(env: str, methode: "com" | "ota", port: str, ip: str)` ;
  `class Serie(racine: Path, dossier: Path, pio: str, builds_en_cours=..., port_libre=..., ota_fs=...)` avec
  `lance(lignes: list[Ligne], actions: set[str]) -> None` (lève `RuntimeError` si déjà en cours ou refus),
  `controle(lignes, actions) -> list[str]` (motifs de refus), `depuis(n: int, attente: float) ->
  list[dict]` (événements numérotés, modèle `synchro_fork_session.Session`), `en_cours() -> bool`,
  `arrete(immediat: bool) -> None`.
- Événements : `{"n", "type": "debut"|"etape"|"duree"|"ligne"|"echec"|"fin_env"|"attente"|"fin", "env",
  …}` ; `duree` porte `{"etape": "Compilation", "secondes": float}` émis **dès la fin** de l'étape.

- [x] Banc d'abord, avec `build_faux_pio.py` par `BUILD_WEB_PIO` et des fonctions injectées
  (`builds_en_cours`, `port_libre`) : `commandes` (compiler → `run -e X` ; upload COM → `run -e X -t upload
  --upload-port COM12` ; compiler+upload → un seul `-t upload` ; buildfs → `-t buildfs` ; uploadfs COM →
  `-t uploadfs --upload-port …`), `ota_variable` (upload OTA : `TASMOTA_OTA_IP=<ip>` dans l'environnement
  du fils, pas de `--upload-port`), `ordre_actions`, `serie_un_par_un` (jamais deux fils vivants),
  `serie_continue_apres_echec` (env 2 en échec à la compilation → son upload marqué « annulée », env 3
  lancé), `duree_des_la_fin`, `refus_build_en_cours`, `refus_port_tenu`, `refus_meme_port` (deux envois COM
  sur COM34 refusés ; deux compilations seules acceptées), `refus_ip_vide`, `serie_attend_build_externe`
  (événement `attente`, reprise), `arret_apres_env`, `arret_immediat` (arbre tué), `journal_ecrit`
  (journal sans ANSI dans `journaux/`), `reference_o_memorisee` (`references.json` mis à jour après un
  succès), `rappel_fichiers_modifies` (événement `fin` cite `platformio_override.ini` et
  `user_config_override.h`), `refus_double_lancement`. — preuve : test_build_serie.py + build_faux_pio.py (commit d74934f6c)
- [x] Vérifier que le banc échoue. — preuve : ROUGE ModuleNotFoundError build_serie, task-3-report
- [x] Implémenter : `builds_en_cours` par défaut = logique de `.claude/hooks/garde_build.py:56`
  (`builds_en_cours()`, importé par `sys.path`, sans appeler `main()`) ; `port_libre(port)` par défaut =
  ouverture/fermeture `serial.Serial(port)` (PermissionError → tenu ; absent de `list_ports` → absent) ;
  contrôle « build en cours » refait avant chaque env (attente par sondage toutes les 5 s) ; nombre de `.o`
  de référence relu après succès dans `.pio/build/<env>/` (`*.o`, récursif). — preuve : commits d74934f6c, f7b7981ec (detection None = attente)
- [x] Banc vert. — preuve : test_build_serie.py 63 OK, sortie 0 (2026-10-24)
- [x] Commit `feat(build-web): execution en serie des pio run, refus et arret`. — preuve : d74934f6c + f7b7981ec

## A4 — OTA : firmware et file system envoyés par la page (`/u2`, `/ufsu`) (`build_ota_fs.py`)

Fichiers : modifier `outils_pc/build_serie.py` ; créer
`outils_pc/build_ota_fs.py`, `outils_pc/test_build_ota_fs.py` (carte simulée : petit serveur HTTP local
qui imite `/cm`, `/ufsd`, `/ufsu`, `/ufsu?download=` et exige le `Referer`).

Interfaces produites :
- `envoie_fs_ota(env: str, ip: str, dossier_fs: Path, sauvegardes: Path, rapporte: Callable[[dict],
  None]) -> None` (lève `RuntimeError("<étape> : <motif>")` en échec) ; `rapporte` reçoit
  `{"etape": "Envoi des fichiers", "pourcent": int, "detail": "12/40 sd/js/x.js"}`.

- [x] **Firmware OTA par la page** (spec choix 7 révisé : le pré-script ne peut pas passer après
  `post_esp32.py`) : `envoie_firmware_ota(env, ip, dossier_build, rapporte)` dans `build_ota_fs.py`
  (`POST http://<ip>/u2?fsz=`, champ `file`, `firmware.bin.gz` sinon `firmware.bin`, `Referer`, % = octets
  envoyés, retour de la carte par `Status` en 90 s) ; dans `build_serie.py`, upload OTA = `pio run -e X`
  puis `envoie_firmware_ota` (plus de `TASMOTA_OTA_IP`) ; `build/` non modifié. Tests
  `ota_firmware_envoi`, `ota_firmware_referer`, `ota_firmware_gz_prefere`, `ota_firmware_echec`,
  `serie_upload_ota_par_page`. — preuve : envoie_firmware_ota (commits a98478c7f, d3f3da522 : bascule safeboot /u4, preuve Status 2) ; build/ non modifie
- [x] Banc d'abord : `ota_fs_ordre` (téléchargement du persist → `/ufsd` + envois → relecture → `Br …
  persist.load() …` → `Restart 1` → attente `Status`), `ota_fs_sauvegarde` (persist de la carte écrit dans
  `persist/<env>-<AAAAMMJJ-HHMMSS>.json`), `ota_fs_persist_injoignable` (aucun `/ufsu` reçu, erreur
  « Sauvegarde du persist »), `ota_fs_relecture_differente` (erreur, pas de restauration, chemin de la
  sauvegarde dans le message), `ota_fs_sous_dossiers` (`json/`, `sd/js/` créés et remplis), `ota_fs_referer`
  (toutes les requêtes l'ont), `ota_fs_echec_ufsu` (page contenant « Failed » → erreur),
  `ota_fs_pas_de_retour` (pas de réponse 90 s après `Restart 1`, délai réduit par paramètre dans le banc),
  `ota_fs_progression` (fichiers envoyés / total). — preuve : test_build_ota_fs.py + build_ota_carte_simulee.py
- [x] Vérifier que le banc échoue. — preuve : ROUGE ModuleNotFoundError puis 12 KO avant correctif, task-4-report
- [x] Implémenter `build_ota_fs.py` (`urllib.request`, multipart écrit à la main, champ `ufsu` ;
  commande Berry exacte de la spec, choix 10.5 ; dossier courant sur la carte par le mécanisme du
  gestionnaire de fichiers de Tasmota — à lire dans `tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino`).
  Dans `build_serie.py`, l'action « téléverser le FS » en OTA = `pio run -e X -t buildfs` (si pas déjà
  fait dans le lancement) puis `envoie_fs_ota(…, dossier_fs=.pio/build/<env>/littlefs_data)`. — preuve : commits a98478c7f, d3f3da522 (persist relu en JSON apres redemarrage)
- [x] Banc vert ; `test_build_serie.py` toujours vert. — preuve : test_build_ota_fs 64 OK, test_build_serie 69 OK, sortie 0 (2026-10-24)
- [x] Commit `feat(build-web): OTA du firmware et du file system par la page`. — preuve : a98478c7f + d3f3da522

## A5 — Serveur web (`build_web.py`)

Fichiers : créer `outils_pc/build_web.py`, `outils_pc/test_build_web.py`.

Interfaces :
- Consomme : `liste_envs`, `ecrit_port` (A1), `Serie`, `Ligne` (A3).
- Produit, routes : `GET /` (page de A6), `GET /envs` (liste JSON + derniers choix), `POST /port`
  (`{"env","port"}`), `POST /lancer` (`{"lignes":[…], "actions":[…]}`), `POST /arreter`
  (`{"immediat": bool}`), `GET /flux` (SSE, `Last-Event-ID` / `?depuis=`), `GET /execution`
  (`{"en_cours": bool}`), `GET /journal?env=` (texte). Options : `--http 7700`, `--local`,
  `--sans-navigateur`.

- [x] Banc d'abord (serveur lancé sur un port libre, `Serie` sur faux pio) : `routes_locales`,
  `post_sans_entete_refuse` (en-tête `X-Build: 1` exigé, + `origine_autorisee`), `distant_sans_jeton_refuse`,
  `port_refuse_pendant_lancement` (409), `port_ecrit_puis_relu`, `lancer_409_si_en_cours`,
  `flux_rejoue_depuis`, `execution_reflete_etat`, `corps_borne` (> 64 Ko refusé). — preuve : test_build_web.py (commit fb5b65677)
- [x] Vérifier que le banc échoue. — preuve : ROUGE module absent, task-5-report
- [x] Implémenter au modèle de `maintenance/synchro_fork_web.py` (`fabrique_gestionnaire`, `_flux`,
  `principal`) ; derniers choix lus/écrits dans `derniers.json`. — preuve : commits fb5b65677, 33fd66e60 (/journal du dernier lancement)
- [x] Banc vert. — preuve : test_build_web.py vert, sortie 0 (2026-10-24)
- [x] Commit `feat(build-web): serveur de la page build et televersement (port 7700)`. — preuve : fb5b65677 + 33fd66e60

## A6 — Page web (`build_page.py`)

Fichiers : créer `outils_pc/build_page.py` (HTML + CSS + JS servis par `GET /`), compléter
`test_build_web.py`.

Contenu imposé par la spec (maquettes de la conversation : liste à gauche, actions à droite, panneau de
suivi) :
- familles *Mes cartes*, *Mes bases*, *Tasmota (amont)* repliée avec ses 4 sous-groupes ;
- par ligne : case, nom, interrupteur COM / OTA (OTA grisé si `ota_possible` faux), champ port (vide si
  absent ; pour un env écrivable, modification → `POST /port` + ligne « le prochain build repartira de
  zéro » ; pour un env non écrivable, valeur gardée pour le lancement seulement) ou champ IP (saisie obligatoire si `ip` vide ; valable pour le lancement seulement) ; mention
  « le file system (persist compris) sera aussi flashé » quand upload COM est coché et qu'un `littlefs.bin`
  existe (champ `littlefs` à ajouter à `/envs`) ;
- 4 cases d'actions, bouton « Lancer (N env, l'un après l'autre) », boutons « Arrêter après cet env » et
  « Arrêt immédiat » (avertissement : carte à moitié flashée, copies dans `data/<lieu>/<carte>`) ;
- panneau de suivi : un bloc par env (étape, %, barre, durées dès la fin de chaque étape, extrait d'erreur,
  journal dépliable), **bandeau rouge** en tête pour chaque échec, rappel final des fichiers modifiés.

- [x] Banc d'abord : `page_contient` (les 4 actions, les 3 familles, `X-Build`), `envs_littlefs`. — preuve : test_build_web.py page_contient, envs_littlefs avec temoins (commit 48252486f)
- [x] Implémenter. — preuve : build_page.py (commits 48252486f, d90f0fb4f) ; 788 lignes, exception acceptee par l'utilisateur (CLAUDE.md)
- [x] Banc vert. — preuve : test_build_web.py 55 OK, sortie 0 (2026-10-24)
- [x] **Exécution dans un vrai Chrome** (leçons du 2026-10-16 et du 2026-10-17) : Chrome par DevTools
  (`--remote-debugging-port`, `Runtime.evaluate` après délai, `Runtime.exceptionThrown`), serveur sur faux
  pio : aucune exception JS, familles dépliables, lancement d'un scénario « 3 envs dont 1 en échec » →
  bandeau rouge, durées, barre à 100 % ; **témoin** : une erreur JS volontaire est bien détectée. — preuve : test_build_page_chrome.py : 40 OK sur 2 passes, temoin TypeError detecte, cas redemarrage du serveur ; captures build-page-*.png
- [x] Commit `feat(build-web): page de la liste des environnements et du suivi`. — preuve : 48252486f + d90f0fb4f

## A7 — Tuile de l'annuaire, tâche VS Code, documentation

Fichiers : modifier `outils_pc/annuaire_registre.py` (entrée `OUTILS`), `outils_pc/test_annuaire.py:43`
(liste des ids), `.vscode/tasks.json` (`git add -f`), `CLAUDE.md` (carte des documents),
`outils_docs/README.md`.

- [x] Entrée de registre : `id="build"`, `nom_acces="Build et téléversement"`, groupe `GROUPES[2]`
  (« Maintenance »), script `outils_pc/build_web.py`, paramètre `_port("http", 7700)`, `dans_job=False`,
  `route_occupe="/execution"`, textes `interet` / `aide` / `journaux` (journaux dans
  `%LOCALAPPDATA%\outils_tasmota\build\journaux\`). — preuve : annuaire_registre.py (commit 9385cebad)
- [x] `test_annuaire.py`, `test_annuaire_lanceur.py`, `test_annuaire_securite.py` verts. — preuve : les trois bancs d'annuaire sortie 0 (2026-10-24)
- [x] Tâche VS Code « Outil : build et téléversement (http://127.0.0.1:7700) » (commande
  `${env:USERPROFILE}\\.platformio\\penv\\Scripts\\python.exe`, jamais `${userHome}`) **lancée une fois**
  par Run Task avant d'être annoncée (leçon du 2026-10-13). — preuve : lancee par l'utilisateur par Run Task le 2026-10-24 ; / 200 (42 Ko), /execution 200, /envs 121 envs (10 cartes, 6 bases, 105 amont), fiche presence/7700.json
- [x] Documentation : section dans `outils_docs/README.md` (usage, OTA, persist, purge de `.pio/build`,
  fichiers réécrits) ; ligne dans la carte des documents de `CLAUDE.md`. — preuve : README + CLAUDE.md (commits fb7b28422, 6e7d8c3a6, a3219fe2f)
- [x] Commit `feat(annuaire): tuile Build et televersement` puis `docs: page build et televersement`. — preuve : 9385cebad + fb7b28422

## A8 — Essais réels avec l'utilisateur

Chaque essai : demander à l'utilisateur, vérifier qu'aucun build ne tourne, une carte à la fois.

- [x] Compiler seul un env (ex. cuve) : étapes, %, durée de compilation affichée dès la fin ; calibrage A2. — preuve : essai utilisateur 2026-10-25 (P4 et cuve, journaux 20261025-000156 et -003648) ; calibrage 40f9f0726
- [x] Téléverser par COM (cuve, COM12) : % esptool, mention « FS aussi flashé » si `littlefs.bin` présent. — preuve : essai utilisateur 2026-10-25, [SUCCESS] code 0, littlefs.bin écrit à 0x004b0000 (journal 20261025-003648)
- [x] Téléverser le firmware en OTA (P4) par la page (`/u2`) sans toucher au `.ini` : `git diff — preuve : essai réel de l'utilisateur, 2026-10-28
  platformio_tasmota_cenv.ini` vide.
  ; journal `20261028-063324-tasmota32p4-garage-serveur-modbus-upload.log` = `pio run -e …` SANS `-t upload` (compilation
  seule, SUCCESS) ; P4 relu après : `Status 2` BuildDateTime 2026-10-28T06:51:41 (cette compilation), redémarrage
  logiciel à 07:12:45 (`Status 1`), juste après `firmware.bin` (07:11) ; `git diff platformio_tasmota_cenv.ini` vide
  (dernier commit du fichier : 5638b27ac du 26/10).
- [x] Téléverser le FS en OTA sur une carte choisie par l'utilisateur : sauvegarde du persist présente,
  relecture identique, persist de la carte après redémarrage = persist envoyé. — preuve : essai réel de l'utilisateur sur le P4, 2026-10-26 ; sauvegarde `persist/tasmota32p4-garage-serveur-modbus-20261026-055308.json`
- [x] Série de 2 envs dont 1 en échec provoqué (port COM débranché) : bandeau rouge, l'autre env aboutit. — preuve : essai réel de l'utilisateur, 2026-10-25
- [x] Pause « rebranchez la carte » : deux cartes branchées tour à tour sur le même port COM — preuve : essai réel de l'utilisateur, 2026-10-25
- [x] Cible Custom « Build et téléversement (page web) » depuis Project Tasks — preuve : essai réel de l'utilisateur, 2026-10-25
- [x] Modification d'un port sur la page : ligne réécrite dans `platformio_tasmota_cenv.ini`, `.bak`
  présent, VS Code lit le même port. — preuve : essai utilisateur 2026-10-25 (« ça fonctionne »)

## A9 — Sortie de pio en direct sur la page (spec, choix 18)

Fichiers : `outils_pc/build_web.py` (lecture du journal par incréments), `outils_pc/build_page.py`
(panneau « Sortie »), bancs `test_build_web.py`, `test_build_page_chrome.py`.

- [x] Banc rouge d'abord : lecture incrémentale du journal de l'env en cours (décalage, env terminé, env
  inconnu, journal d'un autre env jamais servi) ; sonde Chrome : panneau qui se remplit pendant un faux
  pio, défilement auto en bas, arrêté si on remonte, erreurs en rouge. — preuve : ROUGE test_build_web 10 KO
  (/sortie 404, sortie_env absente) et sonde Chrome 6 KO (panneau absent), rapport a9-a10-report.md
- [x] Serveur : lecture du journal par incréments, sans tout renvoyer à chaque fois. — preuve : build_web.sortie_env
  + GET /sortie, journal écrit ligne à ligne (commit c0cbe03a2) ; test_build_web sortie_env / sortie_en_direct,
  mutant sans buffering=1 vu rouge
- [x] Page : panneau « Sortie » dépliable par env, chasse fixe, fond sombre, couleurs erreur/avertissement,
  lignes `
` d'esptool contenues. — preuve : build_page (commit c0cbe03a2) ; sonde Chrome, 8 vérifications
  « sortie : » vertes (témoin : 3 barres dans le journal brut, 1 dans le panneau)
- [x] Bancs `test_build_*` et sonde Chrome verts. — preuve : 5 bancs test_build_* et sonde Chrome (témoin compris)
  sortie 0, 2026-10-25
- [x] Essai réel par l'utilisateur : sortie visible pendant une compilation. — preuve : essai réel de l'utilisateur, 2026-10-25

## A10 — Effacer puis téléverser (`erase_upload`) (spec, choix 19)

Fichiers : `outils_pc/build_serie.py`, `outils_pc/build_progression.py`, `outils_pc/build_web.py`,
`outils_pc/build_page.py`, `outils_pc/build_faux_pio.py`, leurs bancs.

- [x] Lire le texte réel d'esptool pour l'effacement (paquet installé) et la cible `erase_upload` de la
  plateforme ; banc rouge : action `erase_upload` (ordre, COM seulement, refus OTA, exclusive avec
  `upload`, envoi pour le refus de port et pour M7), étape « Effacement de la flash ». — preuve :
  platforms/espressif32/builder/main.py:1984-1993 (« Erasing... », $ERASECMD :947), esptool 5.4.0
  cmds.py:2273 et :2282 ; ROUGE progression (action inconnue), série (actions invalides), web 7 KO, sonde 9 KO
- [x] Série et progression : `pio run -e X -t erase_upload --upload-port COMn`, étape d'effacement. — preuve :
  commit 3f22d0ff5 ; test_build_serie erase_upload_* et test_build_progression effacement verts
- [x] Page : case « Effacer puis téléverser », décoche « Téléverser le firmware » et inversement, grisée en
  OTA, confirmation (persist et réglages effacés), mention « FS aussi flashé ». — preuve : commit 3f22d0ff5 ;
  sonde Chrome, 9 vérifications « effacer : » vertes (témoins : env sans fichiers, ligne revenue en COM)
- [x] Bancs `test_build_*`, `test_annuaire*` et sonde Chrome verts ; README et CLAUDE.md à jour. — preuve : 8 bancs
  et sonde Chrome sortie 0 (2026-10-25) ; README et CLAUDE.md dans le commit docs qui suit 3f22d0ff5
- [x] Essai réel par l'utilisateur : `erase_upload` sur une carte choisie par lui. — preuve : essai réel de l'utilisateur en cours, validé par lui le 2026-10-25

## A11 — OTA des esclaves derrière le range extender du maître (demande du 2026-10-26)

Demande : l'OTA (firmware et FS) marche quand l'IP est connue (maître P4) ; pour les esclaves joints par le
range extender du maître (cuve, rideau), trouver le mode de connexion et l'adresse ou le port qui marche, et
afficher en face de chaque env l'adresse retenue, lue dans la config (persist) ou la télémétrie.
Reconnaissance (2026-10-26) : cuve `rangeExtender.id` 2, rideau 3, `ipMaitre` 192.168.0.43, `apiHTTP` ON ;
le maître redirige `<IP maître>:<8080 + id - 1>` -> `<IP esclave>:80` (`RgxPort`, posé par
`rangeExtenderFonctions.redirige`, commande `RoutageRangeExtender`) ; table vidée au redémarrage du maître.
Fichiers pressentis : `outils_pc/build_envs.py`, `build_ota_fs.py`, `build_serie.py`, `build_web.py`,
`build_page.py`, leurs bancs ; spec à compléter (choix 20).

- [x] Design validé par l'utilisateur (brainstorming), spec complétée. — preuve : l'utilisateur a choisi de sauter les
  questions (« démarre tout de suite sans questions », 2026-10-28) ; choix de Claude écrits dans la spec, choix 20 et 21.
- [x] Adresse OTA déduite par env : IP fixe du `.h`, sinon `http://<ipMaitre>:<8080 + id - 1>` si l'esclave est en — preuve : `build_envs.py::adresse_par_maitre`, banc
  range extender, sinon saisie ; affichée en face de l'env avec sa provenance.
  `test_build_envs::test_adresse_par_maitre` VERT ; vrai dépôt : cuve `192.168.0.43:8081`, rideau `:8082` (maitre),
  P4 `192.168.0.43` (h) ; sonde Chrome VERTE (100 OK), « OTA par le maitre (A11) : adresse et provenance en face de l'env ».
- [x] Avant l'envoi par le maître : redirection posée (`RoutageRangeExtender` sur le maître) et identité de la carte — preuve : `build_ota_fs.py::joint_par_maitre`,
  jointe vérifiée (nom d'hôte du persist) ; refus sinon.
  appelé par `build_serie.py::Serie._lance_ota` ; bancs `test_build_ota_fs::test_par_maitre` (8 cas) et
  `test_build_serie::test_ota_par_maitre` VERTS ; sur les vraies cartes (2026-10-28, sans envoi) : cuve « carte
  jointe par le maître : CAPTEURS-CUVE », rideau hors ligne -> refus « aucune carte derrière 192.168.0.43:8082 ».
- [x] Firmware et FS en OTA par le maître dans les bancs (carte simulée derrière un faux maître). — preuve : faux maître
  = `Carte(maitre=True)` de `build_ota_carte_simulee.py` (RoutageRangeExtender, Status 5) ; les envois firmware et FS
  des bancs `test_build_ota_fs` visent déjà une adresse `127.0.0.1:<port>` (même forme `IP:port`), tous VERTS ;
  `test_ota_par_maitre` : maître consulté avant l'envoi, refus -> aucun envoi.
- [x] Essai réel par l'utilisateur : OTA du firmware ou du FS sur la cuve par le maître. — preuve : flux de la page 7700 du 2026-10-29, `Sleep 50 -> 0`, carte jointe CAPTEURS-CUVE, bascule safeboot, envoi 100 % en 62 s, `Status 2` compilé 02:33:57 -> 04:31:47, succès, aucun « Sleep NON remis »

Essai du 2026-10-28 (08:03) : ÉCHEC. Connexion par le maître OK (CAPTEURS-CUVE), bascule en safeboot OK, puis envoi
coupé à 3 % (`WinError 10053`) ; cuve restée en safeboot (Tasmota 15.4.0.1, `/u4` -> `true`, ne connaît pas `Status`).
Cause reproduite sans écriture (POST de zéros sur `/u2` armé, octet magique refusé) : par la redirection du maître,
~16 Ko/s puis une pause de 6,4 s à 172 Ko -> la cuve ferme (WebServer Arduino : `HTTP_MAX_POST_WAIT` 5000 ms).
Le téléchargement par la carte (`Upgrade`) aurait le même délai (`HTTPCLIENT_DEFAULT_TCP_TIMEOUT` 5000 ms).
Second défaut : la page lit `Status 2` avant l'envoi -> impossible de relancer vers une carte déjà en safeboot.
CAUSE PROUVÉE (même mesure, 1 Mo) : `Sleep` du maître. `Sleep 0` -> 74 et 102 Ko/s, aucune pause, envoi complet ;
`Sleep 50` (réglage du maître) -> 16 à 27 Ko/s, pauses jusqu'à 7,8 s, coupure (deux mesures). `Sleep 50` remis après.
CORRIGÉ dans le code (2026-10-28, à valider par l'essai réel) : `build_ota_fs.py::coupe_sleep` (maître en `Sleep 0`
le temps de l'envoi, valeur remise) ; carte déjà en safeboot reconnue à sa page d'accueil
(`build_ota_fs.py::_page_safeboot`), envoi relancé. Bancs `test_build_ota_fs.py` et `test_build_serie.py` verts.

Constats sur carte (2026-10-26, lecture seule sauf mention) : la table `RgxPort` du maître était vide après son
redémarrage de 05:53 (`192.168.0.43:8081` muet) ; `RoutageRangeExtender` n'a rien posé et
`rangeExtenderFonctions.redirige` plante (`'boolMute' undeclared`) parce que le Berry du P4 ne démarre plus (voir A12).
Fiche discovery du maître : cuve `192.168.4.2` Online port 8081, rideau `192.168.4.3` Offline port 8082.

## A12 — Défaut : `buildfs` construit le FS avec le dossier `data_dir` du lancement PRÉCÉDENT (2026-10-26)

Preuve : journaux `20261026-055152-tasmota32p4-...-buildfs.log:105` (`copy_fs_image(... p4 ... littlefs.bin,
data\garage\tasmota32s3-capteurs-cuve-modbus)`) et `20261026-054628-...cuve...-buildfs.log:103` (dossier du rideau) :
le pré-script réécrit `data_dir` dans `platformio_override.ini` pendant le `pio run`, mais PlatformIO l'a déjà lu.
Conséquence : l'OTA du FS du P4 de 05:53 a envoyé l'`autoexec.be` et le persist de la cuve ; depuis, le Berry du P4
ne démarre plus (`global()` sans `serveur`, `boolMute`, `LOG_LEVEL_*`). Persist réel du P4 sauvegardé avant :
`persist/tasmota32p4-garage-serveur-modbus-20261026-055308.json`. Les firmwares par câble (FS de
`custom_files_upload`) et l'`uploadfs` de la cuve de 05:48 (dossier de la cuve) ne sont pas touchés.

- [x] Rendre au P4 son FS, contrôle de l'`autoexec.be` relu sur la carte. — preuve : relu sur la carte le 2026-10-27,
  `autoexec.be` = « Demarrage du maitre P4 du garage », `global.contains("serveur")` et `("boolMute")` vrais,
  firmware du 2026-10-26T22:39 (`Status 2`) ; la cuve répond de nouveau par le maître (`192.168.0.43:8081`,
  Hostname CAPTEURS-CUVE)
- [x] Corriger à la source, page ET pré-script (choix de l'utilisateur du 2026-10-27). — preuve : pré-script
  `env.Replace(PROJECT_DATA_DIR=...)` dans `adapteParametresPlatformio_override`, banc `build/test_data_dir.py` ROUGE
  (`'.'`) puis VERT ; pré-scripts lus avant le script de la plateforme (`platformio/builder/main.py:167` puis `:173`) ;
  page : `build_envs.ecrit_data_dir` appelé par `Serie._lance_pio`, test_build_envs (11 vérifications « data_dir ») et
  test_build_serie (`data_dir_avant_pio`, faux pio qui relève le data_dir vu au démarrage) rouges puis VERTS ; bancs
  build_web, ota_fs, solidification, progression, fichiers_berry_*, cible_build_web VERTS. Reste à lire sur un vrai
  buildfs la ligne `copy_fs_image` du journal (dossier de l'env construit).
- [x] Garde dans l'OTA du FS : image refusée sans l'identité de l'env. — preuve : `build_ota_fs.verifie_identite` (nom d'hôte sans casse + topic, image contre persist de l'env au dépôt) appelée par
  `Serie._lance_ota` avant `ota_fs` ; test_build_ota_fs `test_identite_image` (7 vérifications) et test_build_serie
  `uploadfs_ota_identite` (refus sans envoi, témoin accepté) rouges puis VERTS ; cas réel rejoué sur le dépôt (dossier
  de la cuve présenté pour le P4) : refus « l'image porte l'identité de CAPTEURS-CUVE (jardin/cuve), pas celle de
  tasmota32p4-garage-serveur-modbus (SERVEUR-GARAGE, garage) » ; les 8 cartes à persist acceptées avec leur dossier.
  Contrôle de l'`autoexec.be` après envoi non ajouté : la relecture existante (carte = image) le couvre maintenant que
  l'image est contrôlée contre l'env.

## A13 — Pourcentage pendant l'envoi du firmware et du FS (demande du 2026-10-26)

- [x] Vérifier ce que la page affiche pendant l'envoi ; manque constaté et nommé. — preuve : journal réel
  `20261027-064311-…cuve…-erase_upload.log` rejoué dans `Suivi` (% par zone : bootloader, partitions, boot_app0,
  safeboot, firmware, littlefs) et page réelle dans Chrome (faux pio, 4 zones) : « firmware.bin · 16 % … 99 % » puis
  « littlefs.bin · 25 % », la barre repart de 0 à chaque zone, aucun % de l'envoi entier. OTA du firmware : un
  événement par point de %, correct. OTA du FS : % = fichiers finis / nombre de fichiers, émis APRÈS chaque fichier ;
  sur le P4, `echarts.min.js.gz` fait 368 Ko contre 10 à 40 Ko pour les autres : le % reste figé puis saute.
- [x] Pourcentage visible sur la carte de l'env pendant tout envoi (firmware et FS, COM et OTA) ; bancs et sonde Chrome. — preuve : sonde Chrome VERTE (99 OK) dont « pourcent_envoi » : 2e envoi par câble, barre
  [11, 21, 32, 43, 43, 62, 81, 99] sans recul, texte « littlefs.bin … · zone 3/3 » ; bancs verts `test_build_progression`
  (extrait réel cuve : début du firmware 11 %, fin 49 %, jamais de recul), `test_build_serie::test_pourcent_global_envoi`,
  `test_build_ota_fs::test_ota_fs_progression_octets` (% des octets, ≥ 8 valeurs pour un fichier de 12 morceaux).
  `build_progression.py::Suivi._envoi` (% pondéré par la durée des zones, `references.json`), `build_ota_fs.py::envoie_fs_ota`.

## A14 — Étude de faisabilité : envoi du firmware et du FS par MQTT (demande du 2026-10-29)

Étude en LECTURE SEULE : trace, avantages/inconvénients, propositions ; l'utilisateur décide de la suite.
Pistes déjà relevées : firmware -> commande native `FileUpload` (type 1 = firmware OTA, type 2 = réglages,
`tasmota/tasmota_xdrv_driver/xdrv_02_1_mqtt_file.ino`, exemple `tools/mqtt-file/upload-ota.py`) ; le FS n'a PAS de type
`FileUpload` -> à faire passer par Berry (abonnement MQTT, écriture par morceaux) ou par `Upgrade`/`UfsServe`.

- [x] Firmware par `FileUpload` — preuve : lecture du code le 2026-10-29, conclusion ci-dessous. Protocole
  (morceaux, base64 ou binaire, MD5, `MqttFileValidate`), taille des
  morceaux et tampon MQTT (`MQTT_MAX_PACKET_SIZE`), safeboot (partition OTA unique : bascule nécessaire comme `/u4` ?),
  redémarrage, preuve par `Status 2` ; activé dans nos firmwares ? (`USE_MQTT_FILE`).
  CONCLUSION : `FileUpload` type 1 INUTILISABLE sur nos cartes S3/P4, qui ont UNE partition OTA + safeboot
  (cuve : bascule `/u4` constatée). Dans l'appli, `xdrv_02_1_mqtt_file.ino::MqttFileUploadValidate` fait
  `Update.begin` sur la partition OTA suivante, qui n'existe pas (la seule est celle qui tourne) ; dans le safeboot,
  `FileUpload` n'existe pas : le safeboot est compilé en `FIRMWARE_MINIMAL` (`tasmota_configurations_ESP32.h`, juste
  après « FIRMWARE_SAFEBOOT specific additions ») et la commande est sous `#ifndef FIRMWARE_MINIMAL`
  (`xdrv_02_9_mqtt.ino`), comme `Status`, que le safeboot de la cuve refuse (« Unknown », 2026-10-28). Reste vrai :
  `USE_MQTT_FILE` est défini en tête de `xdrv_02_1_mqtt_file.ino` (actif dans l'appli), mot de passe = celui du
  MQTT de la carte, morceaux ≈ `MQTT_MAX_PACKET_SIZE` (2048 chez nous) − en-tête − topic, MD5 final, `restart_flag = 2`.
  PISTE QUI RESTE pour le firmware : `OtaUrl <url du PC>` + `Upgrade 1` envoyés PAR MQTT
  (`support_tasmota.ino` : partition unique -> `OtaFactoryWrite`, redémarrage en safeboot, qui TIRE l'URL en HTTP ;
  `Upgrade` et `OtaUrl` restent dans le safeboot). Il faut un serveur HTTP sur le PC ; un esclave le joint par la
  sortie NAPT du maître (même relais : `Sleep 0` du maître toujours utile, délai `HTTPCLIENT_DEFAULT_TCP_TIMEOUT` 5 s).
- [x] FS par MQTT — preuve : lecture du code le 2026-10-29, conclusion ci-dessous. Aucun type natif ; chiffrer une
  réception Berry (`mqtt.subscribe`, écriture par morceaux dans LittleFS, contrôle MD5, RAM du S3 et du P4, persist
  en RAM) ; ou tirer les fichiers par HTTP depuis le PC sur ordre MQTT.
  CONCLUSION : aucune commande Tasmota ne télécharge un fichier dans le FS (`FileUpload` : firmware et réglages
  seulement ; pas d'`UrlFetch`). Deux voies, toutes deux en Berry, donc un module à écrire et à charger sur chaque carte :
  (1) POUSSÉE par MQTT : abonnement `mqtt.subscribe` (déjà utilisé : `controleDiscovery.be`, rappel avec `databytes`),
  morceaux de ≤ ~2 Ko (`MQTT_MAX_PACKET_SIZE` 2048 moins topic et en-tête), ajoutés au fichier, accusé publié par
  morceau, MD5 à la fin ; chaque rappel est court (sous `USE_BERRY_TIMEOUT`, 4 s), RAM ~2 Ko par message ; lent
  (un aller-retour broker par morceau) mais aucun serveur à ouvrir sur le PC.
  (2) TIRÉE en HTTP sur ordre MQTT : `webclient().write_file(<chemin>)` (`xdrv_52_3_berry_webclient.ino::wc_writefile`,
  écrit le corps dans le fichier) depuis un serveur HTTP du PC ; rapide, mais BLOQUANT : un gros fichier dépasse les
  4 s d'un rappel Berry -> passer par `async_get_start` ou découper ; même relais NAPT que l'OTA HTTP pour un esclave.
  Dans les deux cas, persist en RAM : recharger Berry puis `Restart 1`, comme l'OTA HTTP du FS (`envoie_fs_ota`).
- [x] Esclaves derrière le NAPT du maître — preuve : essais réels du 2026-10-29 (`essai_a14.py`, scratchpad : script
  Berry temporaire `/a14_essai.be`, fichiers aléatoires relus par `/ufsu` = IDENTIQUES à chaque essai, nettoyage fait,
  aucun redémarrage, mémoire Berry inchangée). Poussée MQTT (morceaux de 1900 o) / tirée HTTP (`write_file`) :
  maître P4 (Sleep 50) : poussée 3,6 Ko/s (1 morceau en vol) et 8,1 Ko/s (4) ; tirée 32 Ko en 0,56 s ;
  cuve par le maître, Sleep 50 : poussée 0,8 Ko/s (1, pauses jusqu'à 14 s, MAIS sans coupure) et 14,2 Ko/s (4) ;
  tirée 32 Ko en 0,34 s ;
  cuve, maître en Sleep 0 : poussée 5,7 / 15,9 / 18,3 Ko/s (1 / 4 / 8 en vol) ; tirée 8 Ko 0,1 s, 32 Ko 0,7 s,
  128 Ko 1,7 s (≈ 77 Ko/s ; au-delà de ~250 Ko, risque Berry 4 s / watchdog 5 s -> asynchrone obligatoire).
  L'esclave joint le broker et le PC par la sortie NAPT du maître, sans redirection ; MQTT tolère les pauses du
  relais (pas de délai de 5 s comme le serveur web), le `Sleep 0` du maître n'est utile qu'en poussée sans fenêtre.
  Non mesuré : effet sur MqttLog. Questions d'origine : passent-ils par le broker sans redirection ? débit mesuré (le `Sleep`
  du maître compte-t-il encore ?), effet sur MqttLog et sur les plantages déjà vus (broker chargé, mémoire
  `project_mqttlog_esclaves_napt`).
- [x] Comparaison avec l'OTA HTTP actuelle — preuve : mesures du 2026-10-29 ci-dessus et du 2026-10-28 (A11).
  Durée et robustesse : HTTP `/u2`/`/ufsu` 74 à 102 Ko/s mais coupé par les pauses du relais (maître en Sleep 50,
  délai de 5 s du serveur web de l'esclave) ; MQTT poussé 14 à 18 Ko/s (4 à 8 morceaux en vol), SANS coupure
  malgré des pauses de 14 s ; MQTT tiré ~77 Ko/s mais bloquant (4 s Berry, watchdog 5 s). Sécurité : broker local
  sans TLS (192.168.0.5), comme les commandes déjà envoyées par MQTT ; `FileUpload` (mot de passe) hors sujet.
  Place dans la page : transport choisi dans l'onglet « Fichiers » (A15 puis A16).
- [x] Rapport rendu à l'utilisateur ; décision notée — preuve : rapport du 2026-10-29 dans la conversation ;
  DÉCISION DE L'UTILISATEUR (2026-10-29) : « utilisons la voie poussée par mqtt » -> réalisée en A16, après l'onglet
  HTTP (A15) demandé d'abord. Le firmware reste en HTTP (étape 1 : pas de `FileUpload` possible).

## A16 — Transport « MQTT poussé » dans l'onglet « Fichiers » (décision du 2026-10-29)

Fichiers envoyés par morceaux sur `<préfixe>/<topic>/morceau`, accusé cumulé de la carte, 4 à 8 morceaux en vol,
fichier relu ou contrôlé à la fin ; même choix de fichiers, de carte et d'options après envoi que A15.

- [x] Conception validée — preuve : spec choix 25 à 28 (section A16) ; l'utilisateur a passé les questions
  (« passons », 2026-10-29) : CHOIX DE CLAUDE, à relire par l'utilisateur. Énoncé : topics, protocole (début avec chemin et taille, morceaux, fin avec contrôle, erreur,
  abandon), écriture dans un fichier temporaire puis renommage (pas de fichier à moitié écrit), dossiers créés,
  limite de taille, sécurité (seulement la carte visée : topic de la carte ; rien hors du FS).
- [x] Module Berry récepteur — preuve : `data/fs/fsMqtt.be` (A16 lancée par l'utilisateur ; chargé par AUCUN autoexec,
  liste des cartes à décider) ; `berry/banc_fsmqtt.py` VERT (FS en mémoire, 3 mutants rouges : position, MD5,
  effacement d'un seul coup) ; `relecteur-berry` : 0 bloquant, 6 corrections faites (cible de log, exceptions de
  morceau/lit/efface, payload vide, `lit` par lots, efface réentrant, chemin de dossier) et testées.
  Énoncé : Module Berry récepteur (NOUVEAU fichier de `data/fs`, avec l'accord de l'utilisateur ; charte des logs,
  rappels courts, RAM ; chargé par l'autoexec des cartes visées, solidification à décider) ; banc Berry + mutants ;
  `relecteur-berry`.
- [x] Côté PC — preuve : `build_ota_mqtt.py::envoie_fs_mqtt` (module à part, `build_ota_fs.py` découpé le même jour) ;
  `test_build_ota_mqtt.py` VERT (21 OK : carte MQTT simulée, perte et renvoi avec témoin, fenêtre de 4, carte muette,
  MD5 refusé, persist illisible, options, effacement ; mutant sans retour arrière rouge) ; `test_build_serie::
  test_fichiers_mqtt` VERT (7 OK). Énoncé : Côté PC : envoi par `client_mqtt.py` dans `build_ota_fs.py` (fenêtre, reprise, % en direct), banc Python avec une
  carte MQTT simulée + témoin.
- [x] EFFACER TOTALEMENT le FS — preuve : ordre `efface` de `fsMqtt.be` (fichier par fichier, lots de 20 par
  minuterie, `/sd` de la flash compris : Berry n'écrit que sur `ffsp`), testé par les deux bancs ; page : case
  « Effacer tout le FS avant l'envoi », MQTT seulement, confirmation, toute l'image envoyée ensuite (sonde Chrome).
  NON essayé sur carte. Énoncé : EFFACER TOTALEMENT le FS de la carte cible par MQTT (demande du 2026-10-29). Relevé dans le code le
  2026-10-29 : pas de commande `UfsFormat` (commandes Ufs : Type, Size, Free, Delete, Rename, Run, List, Serve) ;
  Berry a `path.format(true)` -> `be_port.cpp::be_format_fs` -> `LittleFS.format()`, en UNE commande, envoyable telle
  quelle sur `cmnd/<topic>/Br`. RISQUES à trancher à la conception : le formatage efface toute la partition d'un bloc
  (environ 11 Mo sur la cuve, partition à 0x4b0000) et peut dépasser le watchdog de 5 s (`USE_ESP32_WDT`) -> carte
  redémarrée en plein effacement ; autre voie sans long blocage : supprimer fichier par fichier (`UfsList` +
  `UfsDelete`, dossiers par `path.rmdir`), à mesurer. Après effacement : le persist est en RAM et le System#Save d'un
  redémarrage le RÉÉCRIT (FS pas vide) ; plus d'autoexec ni de modules non solidifiés -> la carte perd ses fonctions
  Berry jusqu'au renvoi du FS. Page : confirmation explicite (comme `erase_upload`), proposer « effacer puis envoyer
  tout le FS », essai d'abord sur une carte hors service.
- [x] Onglet : choix du transport (HTTP / MQTT) ; doc ; bancs et sonde Chrome. — preuve :
  `test_build_page_fichiers_chrome.py` VERT (+8 : MQTT sans adresse, effacement confirmé ou refusé, retour en HTTP) ;
  README § « Onglet « Fichiers » », CLAUDE.md.
- [x] Décisions de l'utilisateur sur les choix (2026-10-29) — preuve : spec choix 26 et 27 révisés ; `fsMqtt.be`
  solidifiable (`solidifie_et_compile_berry.py` : .h compilé par xtensa, 0 anonyme), dans `berry_commun.socle`,
  chargé par les autoexec du P4 et de la cuve (`banc_demarrage.py` VERT, références des 2 cartes réenregistrées :
  + règle `Mqtt#Connected`, + globale `fsMqttRecepteur` ; `banc_boot.py` OK) ; `efface` = `path.format(true)`
  (`banc_fsmqtt.py` VERT, mutant « formatage sans contrôle » rouge ; `test_build_ota_mqtt.py` VERT).
- [x] Essai réel par l'utilisateur : envoi par MQTT, maître puis cuve par le maître. — preuve : firmware des 2 cartes
  par `erase_upload` le 2026-10-30 (05:06 et 05:55) ; `global.fsMqttRecepteur` = instance sur les deux (topics
  `fsmqtt/garage/` et `fsmqtt/jardin/cuve/`), `/fsMqtt.be` absent du FS (module du firmware) ; envois de l'onglet
  Fichiers en MQTT (dit par l'utilisateur), persist sauvegardé avant à 06:51 (P4) et 06:53 (cuve) ; `/autoexec.be`
  des cartes identique au dépôt (2020 o MD5 56637B4E…, 1888 o MD5 E60F6778…).
- [x] Essai réel par l'utilisateur : « Effacer tout le FS » sur une carte, durée mesurée. — preuve : P4, 2026-10-30 19:38, journal `20261030-193815-…-fichiers-mqtt.log` : `efface` répondu en 0,22 s (page :
  0,2 s, sans redémarrage, uptime 11 h 39), persist en PREMIER (`6457148a1`), 31 debut / 31 fin, recharge, BrRestart,
  « pret » à 19:40:12 ; carte relue : `/_persist.json` et `/logs` présents, fsMqtt actif. Premier essai du matin
  ÉCHOUÉ (fichier 27/31, réponse 22 s après l'ordre) : veille modem du Wi-Fi du P4 en Sleep 50, corrigée par
  `WIFI_NO_SLEEP` (`781a54ed6`) ; journal horodaté de l'échange ajouté (`19b4699de`).

## A15 — Onglet « Fichiers » : envoyer des fichiers choisis du dépôt à une carte choisie, par HTTP (demande du 2026-10-29)

Choix de l'utilisateur (2026-10-29) : onglet de la page 7700 ; fichiers DU DÉPÔT seulement ; après l'envoi, choix
à l'envoi (« recharger Berry » cochée d'office si un `.be` ou `_persist.json` part, « redémarrer » décochée ; persist
de la carte sauvegardé avant d'être remplacé). Envoi HTTP classique (`/ufsu`) d'abord ; MQTT plus tard (A14).
Réutilisé, pas réécrit : `build_ota_fs.py::extrait_image` + `verifie_identite` (liste et chemins EXACTS du FS, depuis
l'image `littlefs.bin` du buildfs : même résultat que l'OTA complète du FS), l'envoi de `envoie_fs_ota` (dossiers
créés, persist sauvegardé puis relu, `BR_RECHARGE`, `Restart 1`), `joint_par_maitre` + `coupe_sleep` pour un esclave,
le verrou d'envoi de `build_serie.py` (jamais pendant un build ni un autre envoi).

- [x] Conception validée — preuve : choix de l'utilisateur du 2026-10-29 (maquette C + colonne destinataire de B =
  maquette E, comparée à A, B, C, D dans le navigateur), spec choix 24. Maquette de l'onglet (carte choisie dans la liste des envs à adresse OTA, bouton « Préparer »
  = buildfs de cet env puis liste des fichiers de l'image, cases à cocher, dossier de destination = celui de l'image,
  options après envoi, suivi et journal comme les autres envois) ; spec complétée (choix 24).
- [x] `build_ota_fs.envoie_fs_ota` accepte un SOUS-ENSEMBLE — preuve : `test_build_ota_fs::test_ota_fs_partiel` VERT (22 OK : 5 cas de sous-ensemble et d'options, refus d'un fichier absent ou d'une liste vide sans contacter la carte), témoin `test_ota_fs_ordre` (envoi complet) inchangé ; 2 mutants rouges (choix ignoré : 15 KO ; persist toujours sauvegardé : 6 KO) ; test_build_serie et test_build_web VERTS. Persist choisi -> BR_RECHARGE toujours (sinon le System#Save d'un redémarrage réécrirait l'ancien) ; « redémarrer » prime sur « recharger Berry » (`BrRestart`). Énoncé : SOUS-ENSEMBLE de fichiers et les options après envoi (recharger Berry,
  redémarrer) ; sans sous-ensemble, comportement inchangé. Banc `test_build_ota_fs` (sous-ensemble seul envoyé,
  persist non coché -> pas de sauvegarde ni de relecture, options respectées) + témoin.
- [x] Serveur — preuve : `build_fichiers.py::liste` + banc NEUF `test_build_fichiers.py` VERT (10 OK : chemins, tailles,
  dossiers, « plus récent que l'image », identité, image absente / illisible / d'une autre carte, env inconnu) ;
  `test_build_serie::test_fichiers_ota` VERT (12 OK : 6 refus, aucun pio run, choix transmis, % sous l'action
  « fichiers ») ; `test_build_web::test_fichiers` VERT deux fois (8 OK : 400/409, jeton, derniers.json du Build intact) ;
  sonde Chrome VERTE (un 1er passage KO sur `sonde_sortie`, barre du panneau Sortie, vert au 2e : délai, sans rapport).
  Énoncé : `GET /fichiers?env=` (liste de l'image : chemin, taille, date de l'image, image absente ou plus
  ancienne que le dépôt signalée) et lancement d'un envoi partiel dans la série (`build_serie`, refus pendant un build).
  Banc `test_build_web` / `test_build_serie`.
- [x] Page : onglet « Fichiers » (`build_page.py`), sélection, envoi, suivi ; sonde Chrome `test_build_page_chrome`. — preuve : `test_build_page_fichiers_chrome.py` VERT (33 OK, maquette E, barre % et journal, envoi intercepté) ; `test_build_page_chrome.py` VERT (témoin compris) ; `test_build_web.py` VERT (+2, mutant `onglet` rouge) ; défaut trouvé par la sonde corrigé (ligne « fichiers » absente du Suivi).
  Code : `build_page_fichiers.py` (inséré dans PAGE), `build_web.py` (`onglet: "fichiers"` : derniers choix du Build non écrits).
  Demande de l'utilisateur (2026-10-29) : l'onglet montre l'avancement de l'envoi, barre en POURCENTAGE et journal
  des étapes (événements `etape` de l'action « fichiers » : étape, %, détail « 3/5 /controleCuve.be »), sans passer
  par l'onglet Build.
- [x] Doc : README § Build et téléversement, CLAUDE.md (tailles) ; `verifie_references_docs` sans défaut. — preuve : `outils_docs/README.md` § « Onglet « Fichiers » : envoyer quelques fichiers du FS » ; CLAUDE.md (build_page 1153, test_build_web 721, `build_page_fichiers.py`, sonde) ; `verifie_references_docs.py` : 18 documents, 0 défaut.
- [x] Essai réel par l'utilisateur : un fichier `.be` vers le maître, puis vers la cuve par le maître. — preuve : validé
  par l'utilisateur le 2026-10-30 (« tu peux également cocher la dernière étape de A15 ») ; `/autoexec.be` des deux
  cartes identique au dépôt (MD5 56637B4E…, E60F6778…), voir l'essai A16 du même jour.

## Améliorations restantes

- [x] [projet] Refuser dès la fin du pré-build un module solidifié vide (cas réel du 2026-10-26 : `demarrage.be` sans
  `#@ solidify:demarrage`, P4 et rideau en échec d'édition des liens après 1 h ; ligne ajoutée avec l'accord de
  l'utilisateur). — preuve : `build_solidification.py` + `build_serie._lance_pio` (pio tué à la 1re ligne de
  compilation) ; test_build_solidification VERT (10 OK), test_build_serie VERT (7 vérifications « solidification_vide »,
  témoin .h plein, buildfs non contrôlé ; rouge avant : 5 KO), test_build_web VERT ; sur le dépôt réel (modules.h du
  build raté) : « solidification vide : demarrage (directive … absente de demarrage.be) » ; demarrage.be resolidifié
  hors build : 39 718 octets avec `be_define_const_native_module(demarrage)` (373 sans la directive)

- [x] [projet] Pause « rebranchez la carte X sur COMn » entre deux envs au port partagé (aujourd'hui :
  refus, spec choix 11). — preuve : commit 320fa8f32 (build_serie._attend_carte, POST /continuer, bandeau de la
  page) ; test_build_serie 34 vérifications « pause » vertes, test_build_web /continuer et Ctrl+C pendant la pause,
  sonde Chrome 5 vérifications « pause » (mutant du bandeau vu rouge) ; spec choix 11 révisé
- [x] [projet] Corriger le `NameError` latent de `increment_config_holder` à 65535
  (`pre_utilitaires_platformio.py:397-402`), relevé par la reconnaissance, hors périmètre. — preuve : déjà corrigé par febb53fd0 (audit P2.3), pre_utilitaires_platformio.py:395-401
- [x] [projet] `garde_build` ignore les cibles d'outils (annuaire, pont série… lancés par leur cible Custom) : la page
  de build ne les attend plus sans fin. — preuve : commit c741dc9ae ; build/test_garde_build.py vert (28 OK, liste
  = NOM_CIBLE des cible_*.py ; mutant sans « annuaire » vu rouge, 4 KO)
- [x] [projet] Défauts relevés : ordre des journaux à l'heure d'hiver, purge à 30 jours, infobulle d'effacement,
  panneaux Sortie refermés en succès, texte d'arrêt de l'annuaire. — preuve : commit 82c924c66 ; test_build_web
  (heure qui recule, purge), test_annuaire (texteArret par node), sonde Chrome 73 OK avec témoin
- [x] [projet] Corrections après relecture : envoi `-t nobuild` après la pause (plus de recompilation),
  `garde_build` compte une cible d'outil comme un build pendant ses 30 premières secondes (formes collées
  `-tupload`/`-eenv`), pause rouverte si le port manque, boutons gardés désactivés après une réponse acceptée,
  `attente_carte` et pause sous le même verrou, env arrêté pendant la pause rangé à part, pas de « terminé » vert si
  aucun env n'a abouti, purge limitée aux journaux de la page et à la seule instance. — preuve : commits 825511d7f,
  b3766ae2b, e406ec547 ; test_build_serie 132 OK, test_build_web 106 OK, build/test_garde_build vert (37 OK),
  sonde Chrome 78 OK avec témoin (6 KO vus avant la page)
- [ ] [projet] Relance de l'OTA vers une carte DÉJÀ en safeboot, prouvée en réel : le 2026-10-28 à 19:31 (cuve en
  safeboot par le maître), envoi à 100 % puis réponse jugée « refusé par la carte (HTTP 200) », motif tronqué : vrai
  refus ou mot de `ECHECS_PAGE` trouvé dans le script de la page ? Garder la réponse entière, puis essai réel.
- [x] [projet] OTA du FS vers un esclave par le maître (cuve ou rideau), essai réel : jamais fait (l'esclave est lui
  aussi en `Sleep 50`, effet non mesuré). — preuve : essai de l'utilisateur du 2026-10-29 (page 7700, capture),
  cuve par 192.168.0.43:8081, « réussi · 2 min 51 s », envoi des fichiers 49 s ; avertissement « persist relu
  différent » expliqué : la cuve réécrit son persist au démarrage (drivers OFF et listes vides retirés, MAC ajoutée,
  état du relais, template GPIO), comparé au dépôt le même jour

## Vérification

Tous les bancs `test_build_*.py` et `test_annuaire*.py` verts (code de sortie 0) ; page exécutée dans
Chrome sans exception ; les 6 essais réels de A8 faits avec l'utilisateur.
