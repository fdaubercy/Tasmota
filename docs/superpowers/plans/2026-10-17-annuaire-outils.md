# Annuaire des outils PC — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** une page web (port 7600) qui montre quels outils PC tournent, ouvre leur page, les lance et les
arrête — depuis ce PC et depuis le téléphone — avec un onglet Aide, démarrée avec VS Code.

**Architecture :** chaque outil dépose une *fiche de présence* JSON au démarrage de son serveur
(`acces_web.py`) ; l'annuaire lit ces fiches, sonde les ports, et lance les outils par `python <script>`
dans un Job Object Windows (mort de l'annuaire = mort des outils, sauf la synchro du fork). Un registre
Python décrit les 6 outils ; tuiles et Aide en sont générées.

**Tech Stack :** Python 3 stdlib (`http.server`, `ctypes`, `subprocess`, `json`), pyserial (déjà dans le
penv PlatformIO) pour lister les ports, HTML/JS sans dépendance.

**Spec :** `docs/superpowers/specs/2026-10-17-annuaire-outils-design.md`

## Global Constraints

- Fichiers dans `outils_docs/scripts_python/outils_pc/` ; chaque fichier < 500 lignes.
- Python : `"$USERPROFILE/.platformio/penv/Scripts/python.exe"` (noté `PY` ci-dessous). Bancs = scripts
  autonomes, code de sortie 0 = vert, style `verifie(obtenu, attendu, libelle)` de `test_acces_web.py`.
- Jamais de `pio` ; jamais de lancement d'outil par une cible Custom ; ne rien lancer pendant un build.
- Ne jamais toucher `.vscode/settings.json`. Dans `tasks.json` : `${env:USERPROFILE}`, jamais `${userHome}`.
- Données hors dépôt sous `%LOCALAPPDATA%\outils_tasmota\` (surcharge par la variable
  `OUTILS_TASMOTA_DOSSIER`, utilisée par les bancs) : `presence\<port>.json`, `consoles\<id>.log`,
  `derniers.json`.
- Port de l'annuaire : **7600**. Rafraîchissement de la page : **3 s**, seulement page ouverte.
- Aucun secret transmis : l'annuaire ne passe jamais `--mot-de-passe` / `--utilisateur` au sniffeur MQTT.
- Commits : messages en français, **sans accents**, prefixes `feat:`/`docs:`/`test:`, **sans trailer
  `Co-Authored-By`**, `git add` de chemins explicites seulement (l'arbre contient du travail en cours de
  l'utilisateur), **jamais de push**, pas de graphify.
- Une page web s'annonce seulement après exécution dans un vrai Chrome piloté par DevTools (leçons du
  2026-10-16 et 2026-10-17).

## Review Focus

1. **Fiche périmée** (outil tué par `taskkill /F`, fiche restée) → l'outil est « arrêté », la fiche est
   supprimée — test `fiche_perimee_supprimee` (Task 3).
2. **Port de page qui répond sans fiche** (ancienne version d'un outil, ou autre programme sur ce port)
   → « en marche (sans fiche) », lien local seulement, pas de lien distant ni de bouton Lancer (un
   lancement échouerait sur le port pris) — test `port_sans_fiche` (Task 3).
3. **POST /lance depuis le téléphone avec des valeurs piégées** (`"COM3 --x"`, `"../x"`, débit `12`,
   clé inconnue) → 400, aucun processus créé — tests `valeurs_piegees_refusees` (Task 2) et
   `lance_refuse_400` (Task 5).
4. **Annuaire tué brutalement** → outils lancés morts, synchro vivante — test `taskkill_annuaire` (Task 4).
5. **Deuxième annuaire** sur 7600 → sortie silencieuse code 0 ; port 7600 tenu par autre chose → code 1
   avec message — test `double_demarrage` (Task 5).

---

### Task 1 : fiche de présence dans `acces_web.py`

**Files :**
- Modify : `outils_docs/scripts_python/outils_pc/acces_web.py` (docstring l.1-25, `Acces.__init__` l.74-80,
  `Acces.annonce` l.90-101)
- Test : `outils_docs/scripts_python/outils_pc/test_acces_web.py`

**Interfaces :**
- Produces :
  - `dossier_donnees() -> pathlib.Path` : `OUTILS_TASMOTA_DOSSIER` sinon `%LOCALAPPDATA%\outils_tasmota`.
  - `dossier_presence() -> Path` : `dossier_donnees() / "presence"` (créé à la demande).
  - `Acces.annonce(...)` écrit en plus `presence/<port>.json` :
    `{"nom": str, "port": int, "pid": os.getpid(), "debut": "AAAA-MM-JJTHH:MM:SS", "jeton": str|None
    (None si local), "local": bool, "lance_par": os.environ.get("OUTILS_TASMOTA_LANCE_PAR", "")}`,
    écriture atomique (fichier `.tmp` puis `os.replace`), et enregistre `atexit` → `Acces.efface_presence()`.
  - `Acces.efface_presence() -> None` : supprime la fiche si son `pid` est le nôtre ; silencieux sinon.
  - Écrit dans `annonce()` et non dans `__init__` : `pont_serie.py:156` et `sniffeur_modbus_http.py:81`
    créent des `Acces` de repli qui n'annoncent rien.

- [ ] **Step 1 : tests** dans `test_acces_web.py`, avec `OUTILS_TASMOTA_DOSSIER` pointé sur un
  `tempfile.mkdtemp()` :
  - `presence_ecrite` : `Acces(7999, False, "Outil test").annonce(ouvrir=False)` → `presence/7999.json`
    existe, `nom == "Outil test"`, `pid == os.getpid()`, `jeton == acces.jeton`, `local is False`.
  - `presence_locale_sans_jeton` : `Acces(7998, True, "x").annonce(False)` → `jeton is None`.
  - `lance_par` : avec `OUTILS_TASMOTA_LANCE_PAR=annuaire` → `lance_par == "annuaire"`.
  - `efface_presence` : après `efface_presence()`, le fichier n'existe plus ; une fiche au `pid` étranger
    (réécrite à la main avec `pid: 1`) n'est pas effacée.
  - `presence_sous_processus` : un sous-processus `PY -c` qui annonce puis sort normalement ne laisse
    aucune fiche (atexit).
- [ ] **Step 2 :** `PY outils_docs/scripts_python/outils_pc/test_acces_web.py` → KO sur les nouveaux cas.
- [ ] **Step 3 :** implémenter ; compléter la docstring du module (fiche de présence, son dossier, à quoi
  elle sert : l'annuaire).
- [ ] **Step 4 :** même commande → tout OK, code 0.
- [ ] **Step 5 :** commit `feat(outils): fiche de presence des outils web pour l'annuaire`.

### Task 2 : registre des outils et validation des paramètres

**Files :**
- Create : `outils_docs/scripts_python/outils_pc/annuaire_registre.py`
- Test : `outils_docs/scripts_python/outils_pc/test_annuaire.py` (créé ici, enrichi Tasks 3 et 5)

**Interfaces :**
- Produces :
  - `@dataclass Parametre(cle: str, libelle: str, option: str, defaut: str, genre: str)` ;
    `genre ∈ {"com", "com_ou_pont", "debit", "port_http"}`.
  - `@dataclass Outil(id: str, nom_acces: str, nom: str, groupe: str, interet: str, aide: str,
    script: str, parametres: list[Parametre], cle_port_page: str, journaux: str,
    dans_job: bool = True, route_occupe: str = "")` ; `script` relatif à la racine du dépôt.
    Propriétés : `a_port_com -> bool` (un paramètre `com`/`com_ou_pont`), `port_page(valeurs) -> int`.
  - `GROUPES = ["Bus et cartes", "Réseau et journaux", "Maintenance"]` ; `OUTILS: list[Outil]` ;
    `par_id(id) -> Outil` (KeyError sinon).
  - `DEBITS = [9600, 19200, 38400, 57600, 74880, 115200, 230400, 460800, 921600]`.
  - `valide(outil, valeurs: dict, ports_detectes: list[str], ponts: list[int]) -> list[str]` : renvoie
    les arguments CLI (`[option, valeur, ...]`), lève `ValueError(message en français)` sinon. Règles :
    clé inconnue → refus ; `com` : `"auto"` ou membre de `ports_detectes` ; `com_ou_pont` : `""`, membre
    de `ports_detectes`, ou `f"pont:{p}"` avec `p in ponts` ; `debit` : entier de `DEBITS` ; `port_http` :
    entier 1024-65535 ; valeur absente → `defaut`. Une valeur `""` d'un `com_ou_pont` omet l'option.
  - `en_json() -> dict` : groupes et outils sérialisés pour la page (sans `script`).

Contenu des 6 fiches (`nom_acces` = 3e argument exact de `acces_web.Acces(...)` dans chaque outil) :

| id | nom_acces | groupe | script | paramètres (clé option défaut genre) | port page | dans_job | route_occupe |
|---|---|---|---|---|---|---|---|
| pont_serie | `Pont serie` | Bus et cartes | `outils_docs/scripts_python/outils_pc/pont_serie.py` | port `--port` auto com ; vitesse `--vitesse` 115200 debit ; tcp `--tcp` 7000 port_http | tcp | oui | |
| sniffeur_modbus | `sniffeur ModBus` | Bus et cartes | `…/outils_pc/sniffeur_modbus.py` | port `--port` auto com ; debit `--debit` 19200 debit ; http `--http` 7300 port_http | http | oui | |
| testeur_udp | `Testeur UDP` | Bus et cartes | `…/outils_pc/testeur_udp.py` | port_maitre `--port-maitre` "" com_ou_pont ; port_esclave `--port-esclave` "" com_ou_pont ; vitesse `--vitesse` 115200 debit ; http `--http` 7400 port_http | http | oui | |
| sniffeur_mqtt | `Sniffeur MQTT` | Réseau et journaux | `…/outils_pc/sniffeur_mqtt.py` | http `--http` 7100 port_http | http | oui | |
| syslog | `Serveur syslog` | Réseau et journaux | `…/outils_pc/syslog_tasmota.py` | http `--http` 7200 port_http | http | oui | |
| synchro_fork | `Synchro du fork` | Maintenance | `outils_docs/scripts_python/maintenance/synchro_fork_web.py` | http `--http` 7500 port_http | http | **non** | `/execution` |

`interet` (une ligne), `aide` (usage, paramètres, arrêt) et `journaux` : rédigés depuis la docstring de
chaque script et sa section dans `CLAUDE.md` (« Carte des documents ») ; `journaux` nomme toujours la
console capturée `%LOCALAPPDATA%\outils_tasmota\consoles\<id>.log` plus le journal propre à l'outil
s'il en a un (lire son `--journal` et son défaut dans le script).

- [ ] **Step 1 : tests** (`test_annuaire.py`, section « registre ») :
  - `six_outils` : `[o.id for o in OUTILS]` égale la colonne id ci-dessus, dans cet ordre ; chaque
    `groupe in GROUPES` ; chaque `script` existe sous la racine du dépôt.
  - `nom_acces_reel` : pour chaque outil, la chaîne `nom_acces` figure dans son script dans un appel
    `acces_web.Acces(` (lecture du fichier) — garde contre une dérive.
  - `options_reelles` : chaque `Parametre.option` figure dans un `add_argument(` du script.
  - `valide_defauts` : `valide(par_id("sniffeur_modbus"), {}, [], [])` →
    `["--port", "auto", "--debit", "19200", "--http", "7300"]`.
  - `valide_pont` : testeur UDP, `{"port_maitre": "pont:7000"}`, `ponts=[7000]` → contient
    `"--port-maitre", "pont:7000"` ; sans `7000` dans `ponts` → `ValueError` ; `port_esclave` `""` → option absente.
  - `valeurs_piegees_refusees` (Review Focus 3) : `{"port": "COM3 --x"}`, `{"port": "../x"}`,
    `{"debit": "12"}`, `{"inconnue": "1"}`, `{"http": "80"}` → chacun `ValueError`.
  - `synchro_hors_job` : `par_id("synchro_fork").dans_job is False`, `route_occupe == "/execution"`.
- [ ] **Step 2 :** `PY outils_docs/scripts_python/outils_pc/test_annuaire.py` → échec (module absent).
- [ ] **Step 3 :** implémenter `annuaire_registre.py`.
- [ ] **Step 4 :** même commande → OK, code 0.
- [ ] **Step 5 :** commit `feat(annuaire): registre des outils et validation des parametres`.

### Task 3 : état des outils (fiches, PID, ports)

**Files :**
- Create : `outils_docs/scripts_python/outils_pc/annuaire_presence.py`
- Test : `test_annuaire.py` (section « presence »)

**Interfaces :**
- Consumes : `acces_web.dossier_presence()`, `annuaire_registre.OUTILS`, `Outil.port_page`.
- Produces :
  - `pid_vivant(pid: int) -> bool` : `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION=0x1000)` +
    `GetExitCodeProcess == STILL_ACTIVE (259)` par `ctypes`.
  - `port_repond(port: int, delai: float = 0.3) -> bool` : connexion TCP à 127.0.0.1.
  - `lit_fiches() -> dict[str, dict]` (clé `nom`) : fiches valides et vivantes ; une fiche au PID mort
    est **supprimée** ; fichier illisible ignoré.
  - `etat_outils(lances: dict[str, dict], derniers: dict[str, dict], hote_client: str | None) -> list[dict]`
    — une entrée par outil : `{"id", "etat": "marche"|"arrete"|"bloque", "raison": str, "port": int,
    "debut": str|None, "lien": str|None, "peut_arreter": bool, "lance_ailleurs": bool, "console": bool}`.
    `lances` = outils lancés par cet annuaire `{id: {"pid", "valeurs"}}` (Task 4) ; `derniers` = dernières
    valeurs par outil ; `hote_client` = nom d'hôte de l'en-tête `Host` pour un client distant, `None` en local.
    Règles : fiche vivante → `marche`, `lien` = `http://127.0.0.1:<port>/` en local, sinon
    `http://<hote_client>:<port>/?jeton=<jeton>` (`None` si fiche sans jeton) ; `peut_arreter` si
    `fiche["lance_par"] == "annuaire"`. Pas de fiche mais port qui répond → `marche`, raison
    `"en marche (sans fiche)"`, lien local seulement. Sinon `arrete`, ou `bloque` si une valeur COM de
    `derniers` est tenue par un outil de `lances` en marche (raison `"COM3 tenu par Pont série"`) —
    « Lancer » reste proposé, la fenêtre permet de choisir un autre port.

- [ ] **Step 1 : tests** (fiches écrites à la main dans un `OUTILS_TASMOTA_DOSSIER` temporaire ; un vrai
  serveur sur un port libre pour « marche ») :
  - `fiche_vivante` : fiche `nom="Serveur syslog"`, `pid=os.getpid()`, port d'un serveur ouvert →
    `etat == "marche"`, `lien == "http://127.0.0.1:<port>/"` ; avec `hote_client="192.168.0.3"` → lien
    `http://192.168.0.3:<port>/?jeton=<jeton>`.
  - `fiche_perimee_supprimee` (Review Focus 1) : fiche au PID d'un `PY -c "pass"` terminé → `arrete`, fichier supprimé.
  - `port_sans_fiche` (Review Focus 2) : port de page qui répond, sans fiche → `marche`, raison
    `"en marche (sans fiche)"`, `lien` distant `None`.
  - `com_tenu` : `lances={"pont_serie": {..., "valeurs": {"port": "COM3"}}}` avec fiche vivante du pont,
    `derniers={"sniffeur_modbus": {"port": "COM3"}}` → sniffeur `bloque`, raison contient `COM3`.
  - `peut_arreter` : `lance_par="annuaire"` → `True` ; `""` → `False` et `lance_ailleurs True`.
  - Témoin : `pid_vivant(os.getpid()) is True` et `pid_vivant` d'un processus terminé `is False`.
- [ ] **Step 2 :** lancer le banc → KO sur la section.
- [ ] **Step 3 :** implémenter `annuaire_presence.py`.
- [ ] **Step 4 :** banc → OK, code 0.
- [ ] **Step 5 :** commit `feat(annuaire): etat des outils par fiches de presence`.

### Task 4 : lanceur et Job Object

**Files :**
- Create : `outils_docs/scripts_python/outils_pc/annuaire_lanceur.py`
- Test : `outils_docs/scripts_python/outils_pc/test_annuaire_lanceur.py`

**Interfaces :**
- Consumes : `annuaire_registre.valide`, `Outil`, `acces_web.dossier_donnees()`.
- Produces :
  - `rattache_au_job() -> bool` : crée un Job Object avec `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (0x2000) |
    JOB_OBJECT_LIMIT_BREAKAWAY_OK (0x800)` (`SetInformationJobObject`, classe 9,
    `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`) et y **rattache l'annuaire lui-même**
    (`AssignProcessToJobObject(job, GetCurrentProcess())`) ; le handle reste ouvert jusqu'à la mort du
    processus ; les enfants héritent du job. `False` (et message console) si l'appel échoue.
  - `class Lanceur(racine: Path, python: str = sys.executable)` :
    - `lance(outil: Outil, args: list[str]) -> int` : `[python, "-u", racine/outil.script, *args,
      "--sans-navigateur"]`, `cwd=racine`, env + `PYTHONUTF8=1` + `OUTILS_TASMOTA_LANCE_PAR=annuaire`,
      stdout+stderr → `consoles/<id>.log` (fichier, **jamais un PIPE** : une synchro qui survit à
      l'annuaire ne doit pas écrire dans un tube cassé). `dans_job False` → `creationflags =
      CREATE_BREAKAWAY_FROM_JOB (0x01000000) | CREATE_NEW_PROCESS_GROUP` ; si `OSError` (job parent sans
      breakaway), relancer sans le drapeau et écrire `"[annuaire] synchro liee a l'annuaire"` en tête de
      sa console. Retourne le PID ; mémorise `lances[id] = {"pid", "valeurs"}`.
    - `arrete(outil: Outil, pid: int) -> None` : `taskkill /T /F /PID <pid>` (arbre : le `python.exe` du
      penv est un lanceur qui crée un enfant).
    - `console(id: str, lignes: int = 200) -> list[str]` : fin de `consoles/<id>.log`.
    - `lances: dict[str, dict]` ; `derniers() -> dict` / `memorise(id, valeurs)` sur `derniers.json`.

- [ ] **Step 1 : tests** (`test_annuaire_lanceur.py`, `OUTILS_TASMOTA_DOSSIER` temporaire, faux outils =
  petits scripts écrits dans le dossier temporaire, qui dorment 60 s en écrivant une ligne) :
  - `lance_et_console` : `lance` d'un faux outil → PID vivant, sa ligne apparaît dans `console(id)`.
  - `arrete_arbre` : faux outil qui lance lui-même un enfant ; après `arrete`, **les deux** PID sont morts
    (témoin : `os.kill`/`TerminateProcess` du seul parent laisse l'enfant vivant).
  - `taskkill_annuaire` (Review Focus 4) : un sous-processus « mini-annuaire » (`PY -c` qui appelle
    `rattache_au_job()`, lance un faux outil `dans_job=True` et un `dans_job=False`, écrit leurs PID dans
    un fichier, puis dort) ; `taskkill /F /PID <mini-annuaire>` → le premier PID meurt sous 3 s, le
    second vit encore (puis le test le tue). Témoin : sans `rattache_au_job()`, le premier survit.
  - `derniers_memorises` : `memorise("pont_serie", {"port": "COM3"})` puis nouveau `Lanceur` →
    `derniers()["pont_serie"]["port"] == "COM3"`.
- [ ] **Step 2 :** `PY outils_docs/scripts_python/outils_pc/test_annuaire_lanceur.py` → échec.
- [ ] **Step 3 :** implémenter `annuaire_lanceur.py`.
- [ ] **Step 4 :** même commande → OK, code 0 ; aucun processus de test restant (`tasklist` filtré sur
  les PID notés).
- [ ] **Step 5 :** commit `feat(annuaire): lancement et arret des outils, job Windows`.

### Task 5 : serveur HTTP de l'annuaire

**Files :**
- Create : `outils_docs/scripts_python/outils_pc/annuaire_outils.py` (point d'entrée)
- Test : `test_annuaire.py` (section « serveur »)

**Interfaces :**
- Consumes : Tasks 1-4 ; `pont_serie.liste_ports()` (`[{"port", "description", "usb"}]`) ;
  `annuaire_page.PAGE` (Task 6 ; d'ici là une page minimale).
- Produces :
  - CLI : `--http` (défaut 7600) + `acces_web.ajoute_options`. `acces = Acces(args.http, args.local,
    "Annuaire des outils")`. Au démarrage : `rattache_au_job()`, puis bind ; sur `OSError` de bind :
    fiche `presence/<port>.json` vivante au nom `"Annuaire des outils"` → `sys.exit(0)` sans rien
    afficher ; sinon message `"Port 7600 deja utilise par un autre programme"` et code 1.
  - `fabrique_gestionnaire(lanceur, acces) -> type[BaseHTTPRequestHandler]`, routes (toutes derrière
    `acces.controle`) :
    - `GET /` → page ; `GET /registre` → `en_json()` ; `GET /etat` → `{"outils": etat_outils(...),
      "liens_reseau": acces.liens_reseau() si client local sinon []}` ;
      `GET /ports` → `liste_ports()` annoté `{"tenu_par": nom|None}` (liste vide si pyserial absent) ;
      `GET /console?id=<id>` → `{"lignes": [...]}`.
    - `POST /lance` `{"id", "valeurs"}` et `POST /arrete` `{"id"}` : exigent l'en-tête
      `X-Annuaire: 1` et `acces.origine_autorisee` (403 sinon). `/lance` : `valide` → 400
      `{"erreur": message}` si `ValueError` ; outil déjà en marche → 409. `/arrete` : `peut_arreter`
      faux → 409 ; `route_occupe` défini et `GET 127.0.0.1:<port><route>` renvoie `en_cours: true` →
      409 `"Une operation de synchro est en cours : arret refuse"`.

- [ ] **Step 1 : tests** (serveur démarré dans un thread sur un port libre, registre réel, lanceur dont
  `lance`/`arrete` sont remplacés par des enregistreurs) :
  - `routes_get` : `/registre` a 6 outils ; `/etat` a 6 entrées ; `/console?id=inconnu` → 404.
  - `lance_ok` : POST `/lance` `{"id": "syslog", "valeurs": {}}` avec `X-Annuaire: 1` → 200 et
    l'enregistreur a reçu `["--http", "7200"]`.
  - `lance_refuse_400` (Review Focus 3) : `{"id": "sniffeur_modbus", "valeurs": {"port": "COM3 --x"}}`
    → 400, enregistreur vide ; sans `X-Annuaire` → 403 ; `Origin: http://evil` → 403.
  - `arret_synchro_refuse` : faux serveur sur le port de la synchro répondant `/execution`
    `{"en_cours": true}`, fiche `lance_par=annuaire` → POST `/arrete` → 409 ; `en_cours: false` → 200.
  - `acces_distant` : réutiliser `cas_refus` de `test_acces_web.py` (IP réseau du PC, sauté si aucune) :
    sans jeton → 403 ; avec jeton → 200.
  - `double_demarrage` (Review Focus 5) : `PY annuaire_outils.py --http <p> --sans-navigateur` lancé
    deux fois → le second sort en code 0 sans sortie ; un socket quelconque sur `<q>` puis lancement
    sur `<q>` → code 1 et message.
- [ ] **Step 2 :** banc → KO sur la section.
- [ ] **Step 3 :** implémenter `annuaire_outils.py`.
- [ ] **Step 4 :** `PY …/test_annuaire.py` et `PY …/test_acces_web.py` → OK, code 0.
- [ ] **Step 5 :** commit `feat(annuaire): serveur de l'annuaire des outils (port 7600)`.

### Task 6 : page Outils + Aide

**Files :**
- Create : `outils_docs/scripts_python/outils_pc/annuaire_page.py` (`PAGE: str`)
- Modify : `annuaire_outils.py` (servir `PAGE`)

**Interfaces :**
- Consumes : `/registre`, `/etat`, `/ports`, `/console`, `/lance`, `/arrete` (Task 5).
- Comportement fixé par la spec et la maquette A : onglets **Outils** / **Aide** ; tuiles groupées dans
  l'ordre de `GROUPES`, pastille vert/gris/orange, nom, intérêt, port, heure de début, raison ; boutons
  **Ouvrir ↗** (`target=_blank`, `lien`), **Lancer**, **Arrêter** (si `peut_arreter`), mention « lancé
  ailleurs », lien **console** (panneau des 200 dernières lignes, rafraîchi tant qu'il est ouvert).
  « Lancer » d'un outil `a_port_com` ouvre une fenêtre modale pré-remplie (`derniers` puis défauts) :
  listes déroulantes alimentées par `/ports` (« COM7 — CH343 », port tenu marqué), `pont:<port>` proposé
  aux `com_ou_pont` si le pont est en marche, débit parmi `DEBITS` ; erreurs 400/409 affichées dans la
  fenêtre ou sur la tuile. Sur ce PC uniquement : encadré « depuis un autre appareil » avec les
  `liens_reseau` (lien copiable). `/etat` interrogé toutes les 3 s, arrêté quand l'onglet est caché
  (`visibilitychange`). Aide générée depuis `/registre` : usage de la page, comment lancer, intérêt,
  paramètres (option, défaut), comment arrêter, journaux. Mise en page lisible sur téléphone (une
  colonne sous 600 px).

- [ ] **Step 1 :** écrire `annuaire_page.py` ; brancher `GET /` dessus.
- [ ] **Step 2 : vérification navigateur** — annuaire lancé sur un port libre avec
  `OUTILS_TASMOTA_DOSSIER` temporaire et une fiche « Serveur syslog » vivante (vrai petit serveur) ;
  Chrome `--headless=new --remote-debugging-port`, piloté par un client CDP stdlib dans le scratchpad
  (`Runtime.evaluate` après 4 s, `Runtime.exceptionThrown` écouté). Attendu : 0 exception ; 6 tuiles ;
  syslog vert avec « Ouvrir ↗ » ; clic « Lancer » du sniffeur ModBus ouvre la modale avec le débit
  `19200` ; clic onglet Aide → 6 sections. Témoin : une page volontairement cassée
  (`$('inexistant').onclick=…` en tête) doit faire remonter une exception par la même sonde.
- [ ] **Step 3 :** `PY …/test_annuaire.py` → OK (la route `/` renvoie toujours 200).
- [ ] **Step 4 :** commit `feat(annuaire): page des outils et onglet Aide`.

### Task 7 : démarrage avec VS Code et documentation

**Files :**
- Modify : `.vscode/tasks.json` (bloc « Outil : … », après la tâche synchro l.170)
- Modify : `CLAUDE.md` (« Carte des documents », liste `outils_pc/`)

- [ ] **Step 1 :** ajouter la tâche, sur le modèle de la surveillance Berry (l.18-40) :
  `"label": "Outil : annuaire des outils (http://127.0.0.1:7600)"`, `"type": "process"`, `"command":
  "${env:USERPROFILE}\\.platformio\\penv\\Scripts\\python.exe"`, `"args": ["-u",
  "outils_docs/scripts_python/outils_pc/annuaire_outils.py", "--sans-navigateur"]`, `"isBackground":
  true`, `"runOptions": { "runOn": "folderOpen" }`, `"presentation": { "reveal": "never", "panel":
  "dedicated" }`, `"problemMatcher": []`. `tasks.json` est ignoré par `.gitignore` : `git add -f`.
- [ ] **Step 2 :** `CLAUDE.md` : une entrée `annuaire_outils.py` (+ `annuaire_registre.py`,
  `annuaire_presence.py`, `annuaire_lanceur.py`, `annuaire_page.py`) — rôle, port 7600, fiches de
  présence sous `%LOCALAPPDATA%\outils_tasmota\`, démarrage avec VS Code, outils arrêtés avec lui sauf la
  synchro, bancs `test_annuaire.py` / `test_annuaire_lanceur.py` ; mentionner dans l'entrée
  `acces_web.py` qu'il écrit la fiche de présence.
- [ ] **Step 3 : essai réel** (hors build en cours de l'utilisateur) : demander à l'utilisateur de lancer
  la tâche une fois (`Tasks: Run Task`, puis autoriser les tâches automatiques), ouvrir
  http://127.0.0.1:7600, lancer et arrêter le serveur syslog depuis la page, puis ouvrir le lien
  « depuis un autre appareil » sur le téléphone. Mesurer la RAM du processus au repos (attendu ≈ 15-25 Mo).
- [ ] **Step 4 :** commit `docs: annuaire des outils (tache VS Code, carte des documents)`.
