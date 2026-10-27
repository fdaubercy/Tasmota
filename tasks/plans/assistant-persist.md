---
chantier: assistant-persist
titre: Assistant de création du persist d'un nouvel env (page 7900, tuile de l'annuaire)
statut: actif
cree: 2026-10-27
maj: 2026-10-27
---
# Assistant de création du persist — plan d'implémentation

> **Pour l'exécutant :** sous-skill requise : superpowers:subagent-driven-development (recommandée) ou
> superpowers:executing-plans. Cocher une étape seulement après vérification, avec « — preuve : … ».

## Contexte

**But :** une page web (http://127.0.0.1:7900), ouverte depuis l'annuaire, pose des questions et en tire le
`_persist.json` d'une nouvelle carte. Elle produit avec lui l'`autoexec.be`, la section du cenv et la section
`#elif` du `.h` qui vont avec, et les écrit dans une seule transaction. Les questions et leurs règles viennent d'un
**JSON modèle** qui se met à jour seul à partir des persists du dépôt.

**Spec (validée le 2026-10-27) :** `docs/superpowers/specs/2026-10-27-assistant-persist-design.md`.
- La lire en entière avant toute action.
- « §x » renvoie à ses sections, « décision n » à son §2, « choix » à son §5.6.

**Architecture :**
- Outil PC Python **stdlib** dans `outils_docs/scripts_python/outils_pc/`, sur le squelette de
  `fichiers_berry_web.py` :
  - `ThreadingHTTPServer`, `fabrique_gestionnaire`, `acces_web.Acces` ;
  - POST un par un sous verrou ;
  - `LookupError`→404, `ValueError`/`TypeError`→400, `RuntimeError`→409, autre→500.
- Modules purs (modèle, parc, génération, fichiers, création) testés sans serveur ; serveur et page par-dessus.
- Le moteur de la page 7800 (`fichiers_berry_creation`) est **réutilisé**, sans changement de comportement.

**Bancs :**
- Au modèle de `test_fichiers_berry_creation.py` : `ECHECS`, `verifie(obtenu, attendu, libelle)`, `principal()`,
  **code de sortie 0 = vert**, dépôt d'essai `depot_essai(t)` dans un `tempfile.TemporaryDirectory()`.
- `OUTILS_TASMOTA_DOSSIER` pointé dans le dossier temporaire, pour que les sauvegardes n'aillent pas dans le vrai dossier.
- Lancés depuis la racine :
  `"$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_<x>.py`.

### Contraintes globales (valent pour toutes les actions)

- **Port et nom :** port **7900**. Nom d'accès `"Assistant persist"`, littéral et identique dans
  `acces_web.Acces(...)` et dans le registre de l'annuaire (`test_annuaire.py` le vérifie).
- **En-tête POST :** `X-Assistant-Persist: 1` + `acces.origine_autorisee`.
- **Aucun `pio run`** par l'exécutant.
- **Bancs :** aucune écriture des vrais fichiers par un banc (dépôt d'essai seulement). Lecture seule des vrais
  persists autorisée.
- **Build en cours :** écriture du dépôt refusée pendant un build. `fichiers_berry_web.builds_en_cours_defaut()` :
  liste non vide **ou `None`** → refus, injectable pour les bancs.
- **Mots de passe :** ils ne sortent **jamais** du serveur.
  - Aperçu, diff, résumé, erreurs : `***` (`fichiers_berry_creation._masque`) ou valeur absente.
  - Le modèle n'en contient aucun.
- **Format des fichiers générés :**
  - fins de ligne du dépôt (`fichiers_berry_creation._eol` du cenv), UTF-8 sans BOM ;
  - persist = `json.dumps(obj, indent="\t", ensure_ascii=False)` dans l'ordre des clés du modèle ;
  - écriture en octets (`errors="surrogateescape"`).
- **Fichiers interdits :** `data/fs/*.be` jamais modifié.
- **Taille :** fichiers < 500 lignes. Sinon, le signaler et demander ; ne pas compresser les commentaires.
- **Langue :** textes de la page en français, avec accents.
- **Commits :**
  - en français, **sans accents**, **sans trailer `Co-Authored-By`** ;
  - `git commit -- <chemins>`, puis relire `git show --stat HEAD` ;
  - un commit par action ; rien poussé.

### Points de relecture (cas que la spec implique et que les tests nominaux ne couvrent pas)

1. **Mot de passe ambigu ou introuvable.** Deux persists donnent deux mots de passe différents pour le même nom de
   réseau, ou le réseau n'existe dans aucun persist.
   - Attendu : refus explicite qui nomme le réseau, sans valeur.
   - Test `secret_ambigu` et `reseau_inconnu` (A3).
2. **`modele_persist.json` cassé à la main** (JSON invalide).
   - Attendu : la page s'ouvre, un bandeau rouge nomme l'erreur et sa ligne ; ni fusion automatique ni réécriture du
     fichier ; création refusée.
   - Test `modele_illisible` (A6).
3. **Persist du dépôt illisible.**
   - Attendu : la fusion et les listes du parc l'ignorent avec un avertissement, sans planter.
   - Test `persist_illisible` (A3).
4. **Saisie modifiée entre « Voir le diff » et « Créer ».**
   - Attendu : bouton grisé côté page, 409 côté serveur.
   - Tests `empreinte_perimee` (A4) et la sonde Chrome (A5).
5. **Bloc activé dont le module est exclu**, ou module chargé par l'autoexec mais ni sur le FS ni en flash.
   - Attendu : refus de cohérence, même si le modèle a été mal édité.
   - Test `coherence_module_exclu` (A3).

---

## A1 — Schéma corrigé et JSON modèle couvrant le parc

Fichiers :
- modifier `outils_docs/scripts_python/berry/genere_schema_persist.py` ;
- régénérer `outils_docs/schemas/persist.schema.json` ;
- créer `outils_docs/schemas/modele_persist.json`, `outils_pc/assistant_persist_modele.py`,
  `outils_pc/test_assistant_persist_modele.py`.

Format du modèle (contrat partagé par A1 à A6 ; la spec §8 laisse la forme au constructeur, elle est fixée ici) :
- `version: 1`.
- `socle` : arbre complet d'un persist, **dans l'ordre des clés du parc** (§4), toutes clés constantes avec leur valeur.
  - Les clés d'identité valent un gabarit `"{{hostname}}"` etc. Variables :
    - `lieu`, `nom`, `nom_lisible`, `hostname` ;
    - `topic`, `groupe` (= `tasmotas/<lieu>`) ;
    - `ip`, `passerelle`, `reseau1`, `reseau2` ;
    - `id`, `ip_maitre`, `type_esp`, `heure`, `ssid_ap`.
  - Une chaîne qui est **exactement** `"{{id}}"` est remplacée par l'entier.
  - Les secrets valent `"@secret:wifi1"`, `"@secret:wifi2"`, `"@secret:mqtt"`, `"@secret:ap"` ou `"@secret:ftp"`.
- `roles` : `{"autonome"|"maitre"|"esclave": {"<chemin.pointe>": valeur}}`, appliqué après le socle (§4 Rôle, choix).
- `puces` : `{"ESP32"|"ESP32S3"|"ESP32P4": {...}}`, avec :
  - `gpio` : 36 / 38 / 55 ;
  - `historique` : false / true / true ;
  - `prefixe_env` : `tasmota32` / `tasmota32s3` / `tasmota32p4` ;
  - `h` : liste des lignes du gabarit `#elif` ;
  - `ajouts` : `{"<chemin>": valeur}`, par exemple `serveur.coprocesseur` et `HostedESPC6` du P4.
- `blocs` : liste ordonnée d'objets à la forme suivante :
  ```
  {id, libelle, aide, puces, dependances, actif: {"<chemin>": v}, inactif: {"<chemin>": v},
   solidify: ["${berry_commun.modbus}", …], exclude_si_inactif: ["data/fs/x.be", …],
   autoexec: [{rang, appel, modules, condition, groupe}]}
  ```
  - `appel` ∈ `importe | compile | charge | leds | historique`.
- `socle_autoexec` : même forme que `blocs[].autoexec`, toujours présent, plus `entete` (lignes de commentaire).
- `metier` : `{gabarit: {name, activation, reglage, log, environnement{…vides}}, controle: [lignes], fonctions: [lignes]}`.
  - Variables `{{metier}}` et `{{Metier}}`.
  - Rangs : `compile` du métier = 900, `chargeFichier` = 999.
- `cenv` : lignes du gabarit de section.
  - Variables `{{env}}`, `{{base}}`, `{{define}}`, `{{dossier}}`, `{{solidify}}`, `{{exclude}}`.
- `a_completer` : liste des chemins ajoutés par la fusion automatique (A6), vide au départ.

Interfaces produites (`assistant_persist_modele.py`) :
- `FICHIER_MODELE = "outils_docs/schemas/modele_persist.json"`.
- `charge_modele(racine) -> dict` : `ValueError("modele_persist.json ligne L : …")` si illisible.
- `chemins(donnees, prefixe=()) -> set[tuple]` : chemins feuilles.
  - Les groupes à suffixe numérique `xxxN` d'un `environnement` sont réduits à `xxx#`.
  - Les clés directes de `modules` autres que `activation` sont réduites à `modules.*`.
- `chemins_modele(modele) -> set[tuple]` : socle + `roles` + `puces.*.ajouts` + `blocs.*.actif/inactif` + `metier.gabarit`
  (sous `modules.*`).
- `persists_du_depot(racine) -> list[tuple[str, dict|None, str]]` : (chemin relatif, données ou None, erreur).
  Ce sont les `data/*/*/_persist.json` hors `*sauvegarde*`.
- `ecarts(racine, modele) -> dict` : `{nouvelles: {chemin: [cartes]}, disparues: [chemin], divergentes: {chemin:
  {modele, parc}}, illisibles: [fichier]}`.

Étapes :
- [x] Schéma :
  - dans `genere_schema_persist.py`, ne plus rendre `required` les blocs optionnels. Ajouter
    `diverses.historique`, `drivers.leds.environnement.leds.ledRGB`, `serveur.coprocesseur`, `drivers.I2S`,
    `drivers.Ethernet`, `drivers.voletRoulants`, `drivers.HostedESPC6` à une constante `OPTIONNELS` consultée avant
    `SEUIL_REQUIS` ;
  - régénérer le schéma (`python outils_docs/scripts_python/berry/genere_schema_persist.py`) ;
  - attendu : `--valide` → 8/8 OK, et le schéma contient `coprocesseur`. — preuve : genere_schema_persist.py --valide 8/8 OK, coprocesseur dans le schema (fb2fd6b)
- [x] Témoin du schéma : retirer temporairement `diverses.historique` de `OPTIONNELS` (copie du script dans le
  scratchpad) → `--valide` doit redonner KO sur le différentiel et la cave ESP32. — preuve : task-1-report.md §3 : KO differentiel et cave ESP32
- [x] Banc `test_assistant_persist_modele.py` (rouge d'abord, module absent) :
  - `couverture_parc` : `ecarts(RACINE, charge_modele(RACINE))["nouvelles"] == {}` en lecture seule des vrais
    persists ;
  - `aucun_secret` : aucune des valeurs réelles des 5 chemins secrets (lues dans le parc) n'apparaît dans le texte du
    modèle ;
  - `secrets_marques` : les 5 chemins valent `@secret:*` dans le socle ou les rôles ;
  - `ordre_racine` : `list(modele["socle"]) == ["diverses", "serveur", "template", "modules", "drivers"]` ;
  - `chemins_reduits` : `("drivers","ModBus","environnement","TasmotaSlaveModBus","TasmotaSlaveModBus#","id")` présent,
    `modules.*` présent ;
  - `rien_a_completer` : `modele["a_completer"] == []`. — preuve : test_assistant_persist_modele.py ROUGE (module absent) puis 45 OK VERT (3af4c55)
- [x] Écrire `assistant_persist_modele.py` puis `modele_persist.json`, à partir des 8 persists et de leur constat (§4,
  §5.6).
  - Les 4 blocs de l'autoexec de la cuve donnent les rangs de référence.
  - Le gabarit `h` de chaque puce reprend les lignes communes des sections existantes de la puce. Les mots de passe y
    sont écrits `{{@wifi1}}` / `{{@wifi2}}` / `{{@ap}}`. — preuve : fb2fd6b + 3af4c55 (blocs[].h, metier.cles_propres)
- [x] Banc VERT. Témoin : supprimer `drivers.voletRoulants` du modèle (copie) → `couverture_parc` ROUGE, avec les 7
  cartes nommées. — preuve : VERT ; temoin sans voletRoulants : 29 chemins, 7 cartes nommees (task-1-report.md §3)
- [x] Commit `feat(assistant-persist): modele de persist et schema corrige`. — preuve : fb2fd6b, correction 3af4c55 ; relecture + re-relecture : tous constats corriges

## A2 — Lecture du parc et règles des mots de passe

Fichiers : créer `outils_pc/assistant_persist_parc.py`, `outils_pc/test_assistant_persist_parc.py`.

Interfaces produites :
- `maitres(racine) -> list[dict]` : `[{env, dossier, hostname, ip, id}]`. Cartes à `rangeExtender.id == 0` et
  `rangeExtender.activation == "ON"`. `env` est retrouvé par `fichiers_berry_etat.dossier_carte` sur
  `Ini.envs_cenv()`.
- `ids_pris(racine) -> dict[int, list[str]]` : id → cartes. Valeur de `serveur.rangeExtender.id`.
- `reseaux(racine) -> list[str]` : noms de `reseau1`/`reseau2` connus, plus `<hostname>-GATEWAY` de chaque maître.
- `id_libre(racine) -> int` : plus petit id ≥ 1 absent de `ids_pris`.
- `base_par_defaut(racine, puce) -> str` : base la plus utilisée par les cartes du cenv dont le préfixe d'env est celui
  de la puce. Égalité → ordre alphabétique.
- `secrets(racine, reseau1, reseau2) -> dict[str, str]` : clés `wifi1`, `wifi2`, `mqtt`, `ap`, `ftp`. Règle de la spec
  §5.1 :
  - réseau → mot de passe associé à ce nom dans le parc ;
  - `<HOSTNAME>-GATEWAY` → `rangeExtender.AP.mdp` de cette carte ;
  - `mqtt`, `ap`, `ftp` : valeur commune ;
  - `ValueError` qui nomme le réseau ou la clé (jamais la valeur) si absent ou ambigu.

Étapes :
- [x] Banc ROUGE (module absent), avec ces tests :
  - `maitres_du_parc` : les dossiers des maîtres valent exactement `{data/cave/tasmota32s3-serveur-rly,
    data/etage2/tasmota32s3-grenier, data/garage/tasmota32p4-serveur-modbus, data/garage/tasmota32s3-serveur-modbus}`,
    lus en lecture seule (constat du 2026-10-27 : id 0 et Range Extender ON). La cuve, le rideau, le différentiel
    et la cave ESP32 n'en font pas partie.
  - `id_libre_parc` : `== 1` (ids pris : 0, 2, 3).
  - `secrets_esclave` : `secrets(RACINE, "SERVEUR-GARAGE-GATEWAY", "SERVEUR-GARAGE-GATEWAY")["wifi1"]` est égal au
    `rangeExtender.AP.mdp` du P4. Comparer les deux valeurs dans le test, sans les imprimer.
  - `secret_ambigu` (point 1) : dépôt d'essai où un persist change le mot de passe de `MAISON` → `ValueError`, avec
    `"MAISON"` dans le message et aucune des deux valeurs.
  - `reseau_inconnu` (point 1).
  - `persist_illisible` (point 3) : un persist tronqué dans le dépôt d'essai → `maitres()` répond, carte ignorée. — preuve : test_assistant_persist_parc.py ROUGE (module absent), 6 tests presents
- [x] Écrire `assistant_persist_parc.py` en s'appuyant sur `assistant_persist_modele.persists_du_depot`. — preuve : d769850 outils_pc/assistant_persist_parc.py
- [x] Banc VERT. Témoin : dans `secrets`, ignorer le cas `-GATEWAY` → `secrets_esclave` ROUGE. — preuve : 28 OK VERT ; temoin -GATEWAY neutralise -> secrets_esclave ROUGE (task-2-report.md)
- [x] Commit `feat(assistant-persist): lecture du parc et regles des mots de passe`. — preuve : d769850, relecture approuvee

## A3 — Génération : persist, autoexec, listes du cenv, cohérence, squelettes

Fichiers : créer `outils_pc/assistant_persist_generation.py`, `outils_pc/test_assistant_persist_generation.py`.

Interfaces produites :
```python
@dataclass
class Reponses:
    puce: str                 # "ESP32" | "ESP32S3" | "ESP32P4"
    base: str                 # env de base (vide -> base_par_defaut)
    lieu: str
    nom: str
    ip: str = "0.0.0.0"
    heure: str = "NTP"        # "NTP" | "RTC" | "UDP" ; RTC => DS3231 actif
    role: str = "autonome"    # "autonome" | "maitre" | "esclave"
    maitre: str = ""          # env du maitre (esclave)
    id: int = 0               # force a 0 hors esclave
    reseau1: str = ""         # autonome/maitre ; esclave -> <HOSTNAME maitre>-GATEWAY
    reseau2: str = ""         # vide -> reseau1
    topic: str = ""           # vide -> "<lieu>/<nom>"
    blocs: list = field(default_factory=list)    # ids de modele["blocs"] coches
    metiers: list = field(default_factory=list)  # noms modules.<x> ; le 1er = principal (decision 16)
    squelettes: bool = False
    define: str = ""          # vide -> fichiers_berry_creation.define(base, lieu, nom)
```
- `variables(racine, r) -> dict` : valeurs des `{{…}}`. Le hostname et le reste de l'identité suivent
  `fichiers_berry_creation.identite_par_defaut`. Pour un esclave : passerelle `192.168.4.1` et `ip_maitre` du maître.
- `persist(modele, r, vars, secrets=None) -> dict`, appliqué dans l'ordre :
  1. socle ;
  2. puce (`ajouts`, `template.GPIO = [1]*gpio`, `typeESP`) ;
  3. rôle ;
  4. blocs `actif`/`inactif` ;
  5. métiers.
  - `secrets=None` → chaque `@secret:*` devient `"***"`.
  - L'ordre des clés est celui du socle ; une clé ajoutée va en fin de son parent.
- `texte_persist(obj, eol) -> str`.
- `autoexec(modele, r) -> str` : entrées du socle, des blocs cochés, puis du métier principal (`compile` rang 900,
  `chargeFichier` rang 999). Algorithme :
  - les entrées de même `groupe` fusionnent en un seul appel, modules concaténés par `rang` ;
  - les appels sont triés par plus petit `rang` ;
  - `importe` donne une seule ligne ;
  - la sortie est `entete` + `import demarrage` + `if demarrage.prologue()` + les lignes indentées de 4 espaces +
    `end`.
- `listes_cenv(modele, r) -> {"solidify": [str], "exclude": [str]}` :
  - solidify = `${berry_commun.socle}` + `solidify` des blocs cochés ;
  - exclude = union des `exclude_si_inactif` des blocs non cochés.
  - Les modules métier ne vont dans aucune des deux listes (choix).
- `coherence(modele, r, obj, texte_autoexec, listes) -> list[str]` : refus. Cas couverts :
  - bloc `ON` sans ses modules ;
  - module de l'autoexec présent dans `exclude` ;
  - id différent entre `rangeExtender`, `udp`, `tcp` et `ModBus` ;
  - dépendance non cochée ;
  - historique sur une puce sans `historique`.
- `squelettes(modele, metier) -> dict[str, str]` : `{"controle<Metier>.be": …, "<metier>Fonctions.be": …}`.
- `graphiques_initial() -> str` : `{"affichage": {}, "groupes": {}}`.
- `reponses_depuis_persist(modele, donnees, env) -> Reponses` : sert au rejeu du parc (§7).

Étapes :
- [x] Banc ROUGE (module absent). Tests :
  - `rejeu_parc` : pour chaque carte au format actuel (P4, cuve, rideau, cave S3, différentiel, grenier),
    `persist(modele, reponses_depuis_persist(...), …, secrets=<vrais>)` comparé au vrai persist, sur les chemins de
    `chemins_modele`. Écarts tolérés : `template.GPIO`, le contenu de `modules.<x>.environnement`, et les clés de
    `a_completer`. Sortie : liste des écarts par carte, vide attendue.
  - `autoexec_cuve` : la suite des appels `demarrage.*` (commentaires retirés) générée pour les réponses de la cuve
    est égale à celle de `data/garage/tasmota32s3-capteurs-cuve-modbus/autoexec.be`.
  - `historique_esp32` : `Reponses(puce="ESP32", blocs=["historique"], …)` → `coherence` non vide.
  - `coherence_module_exclu` (point 5) : modèle muté où le bloc `modbus` n'a plus de `solidify` → refus qui nomme
    `controleModbus`.
  - `ids_alignes` : esclave id 4 → les 4 chemins valent l'entier 4.
  - `aucun_secret_sans_secrets` : `texte_persist(persist(..., secrets=None))` ne contient aucune valeur réelle.
  - `squelettes_compilent` : écrire les squelettes de `piscine` dans un dossier temporaire et lancer
    `python outils_docs/scripts_python/berry/verifie_berry.py <fichier>` → code 0, aucun avertissement de charte. — preuve : test_assistant_persist_generation.py ROUGE (module absent), tests du brief presents
- [x] Écrire `assistant_persist_generation.py` jusqu'au VERT. Si `rejeu_parc` révèle une clé du parc absente ou fausse,
  corriger le **modèle** (A1), jamais la tolérance. — preuve : a92c232 ; 41 OK VERT ; rejeu : 13 tolerances nommees (Ruling 8), autoexec_cuve = vrai autoexec
- [x] Témoin : retirer le rôle `esclave` de `ipMaitre` dans une copie du modèle → `rejeu_parc` ROUGE sur la cuve et le
  rideau seulement. — preuve : temoin ipMaitre retire : ROUGE cuve + rideau seulement (task-3-report.md)
- [x] Commit `feat(assistant-persist): generation du persist, de l'autoexec et des listes du cenv`. — preuve : a92c232, relecture approuvee

## A4 — Création atomique (cenv, `.h`, dossier) et démarrage prouvé

Fichiers :
- modifier `outils_pc/fichiers_berry_creation.py` (extraction seulement) et `berry/banc_demarrage.py` (option
  `--dossier`) ;
- créer `outils_pc/assistant_persist_creation.py`, `outils_pc/test_assistant_persist_creation.py`.

Interfaces :
- Consomme : A1 à A3, plus `fichiers_berry_creation` : `define`, `nom_env`, `identite_par_defaut`, `_insere_cenv`,
  `_masque`, `_prises`, `_eol`, `_encode`, `FICHIER_H`, `SECTION_H`, `CHAMPS_IDENTITE`.
- Extraction dans `fichiers_berry_creation.py`, appelée par `_refus`, qui garde son comportement :
  - `refus_nom(racine, ini, base, lieu, nom, env, dossier, nouveau, texte_h, texte_cenv) -> list[str]` : base
    inconnue, lieu et nom, `-base`, env, dossier, define ;
  - `refus_identite(identite) -> list[str]` ;
  - `avertit_prises(racine, texte_h, identite, avertissements, sauf_dossier=None)`.
- Produit :
  - `prepare(racine, r) -> dict` : `{env, dossier, define, diff, empreinte, avertissements, refus, apercu: {persist,
    autoexec}}`. Rien n'est écrit, secrets masqués.
  - `cree(racine, r, empreinte_lue, builds_en_cours) -> dict` : `{cree, env, dossier, diff, avertissements,
    sauvegarde, resume, liens}`.
    - `liens` = `{"build": "http://127.0.0.1:7700/?env=<env>", "fichiers": "http://127.0.0.1:7800/?env=<env>"}`.
    - `resume` = texte de la décision 11 : env, dossier, define, rôle, id, IP, topic, blocs, fichiers écrits.
- Section `.h` : gabarit `puces[puce].h`, encadré par `// -- Options for <env> ------` et
  `#elif defined(<define>)`. Elle est insérée **avant la ligne `#else`/`#endif` de niveau 8 espaces qui ferme la
  chaîne des firmwares**, et les `{{@…}}` sont remplis par `secrets()`.
- Section cenv : gabarit `cenv`, insérée par `_insere_cenv`, puis `fichiers_berry_coprocesseur.adapte_cenv`.
- `avertit_prises` est complété par un avertissement si l'id d'un esclave est déjà pris.
- Refus propres à `prepare`, en plus de `refus_nom`, `refus_identite` et `coherence` :
  - esclave sans maître connu ;
  - nom de métier hors de `[a-z][a-zA-Z0-9]*`, ou `data/fs/controle<Metier>.be` existe déjà ;
  - `ValueError` de `secrets()`, avec son message ;
  - persist généré refusé par `genere_schema_persist.valide` (chemins fautifs dans le message).
- `empreinte` = sha256(octets cenv + octets `.h` + octets `modele_persist.json` + `json.dumps(asdict(r), sort_keys=True)`).

Étapes :
- [x] Extraire `refus_nom`, `refus_identite`, `avertit_prises` ; `test_fichiers_berry_creation.py`,
  `test_fichiers_berry_renommage.py` et `test_fichiers_berry_web.py` restent VERTS **sans changer leurs attentes**. — preuve : refus_nom/refus_identite/avertit_prises extraits ; bancs 7800 (creation, renommage, web, suppression) VERTS sans changer leurs attentes (96519fd)
- [x] Banc `test_assistant_persist_creation.py` ROUGE. Tests sur `depot_essai` (importé de
  `test_fichiers_berry_creation`) :
  - `cree_esclave_s3` : `Reponses(puce="ESP32S3", lieu="garage", nom="piscine", role="esclave",
    maitre="tasmota32p4-garage-serveur-modbus", blocs=["udp","discovery","rangeExtender","modbus","leds",
    "historique"], metiers=["piscine"], squelettes=True)` →
    - les fichiers existent : `data/garage/tasmota32s3-piscine/{_persist.json, autoexec.be, graphiques.json,
      controlePiscine.be, piscineFonctions.be}` ;
    - le cenv contient `[env:tasmota32s3-garage-piscine]` ;
    - le `.h` contient `#elif defined(FIRMWARE_ESP32S3_GARAGE_PISCINE)` et `STA_SSID1` = `"SERVEUR-GARAGE-GATEWAY"`.
  - `persist_valide_schema` : le persist écrit passe `genere_schema_persist.valide` ;
  - `vu_par_build` : `fichiers_berry_etat.dossier_carte("tasmota32s3-garage-piscine")` = le dossier écrit ;
  - `empreinte_perimee` (point 4) : `r.ip` modifié après `prepare` → `RuntimeError` ;
  - `build_en_cours` : `builds_en_cours=lambda: ["x"]` → `RuntimeError`, rien écrit ; `lambda: None` → refus aussi ;
  - `refus_existant` : nom de l'env du rideau → refus ;
  - `refus_metier` : `metiers=["Piscine-2"]` → refus ; `metiers=["general"]` (`data/fs/controleGeneral.be` existe) → refus ;
  - `atomique` : une exception injectée dans la 3e écriture → dépôt identique (octets du cenv et du `.h`, dossier absent) ;
  - `diff_sans_secret` : aucune valeur réelle dans `diff`, `resume`, `apercu`. — preuve : test_assistant_persist_creation.py ROUGE (module absent), tests du brief + refus_metier
- [x] Écrire `assistant_persist_creation.py` jusqu'au VERT. — preuve : 96519fd ; 49 OK VERT
- [x] Ajouter `--dossier <data/…> --env <env>` à `banc_demarrage.py` pour une carte hors de `CARTES` : instantané sans
  référence, **rouge si la rubrique erreurs n'est pas vide**. Puis le lancer sur la carte `piscine` générée dans un
  dépôt d'essai (`--sources` = copie de `data/fs`).
  - Attendu : aucune erreur. Si `controleGeneral` ou `configModules` refusent un `environnement` vide, corriger le
    gabarit `metier` (A1), pas les modules de `data/fs`. — preuve : banc_demarrage --dossier : carte piscine generee, erreurs (0) ; 6 cartes de reference inchangees
- [x] Témoin du démarrage : retirer `return controlePiscine` du squelette (copie) → `banc_demarrage --dossier` ROUGE. — preuve : temoin sans return controlePiscine : ROUGE sur copie (task-4-report.md)
- [x] Commit `feat(assistant-persist): creation atomique d'un env genere`. — preuve : 96519fd, relecture approuvee

## A5 — Page 7900 (disposition A), serveur et annuaire

Fichiers :
- créer `outils_pc/assistant_persist_web.py`, `outils_pc/assistant_persist_page.py`,
  `outils_pc/test_assistant_persist_web.py`, `outils_pc/test_assistant_persist_page_chrome.py`,
  `build/cible_assistant_persist.py`, `build/test_cible_assistant_persist.py` ;
- modifier `outils_pc/annuaire_registre.py`, `outils_pc/test_annuaire.py`, `build/pre_utilitaires_platformio.py`,
  `.claude/hooks/garde_build.py`, `.vscode/tasks.json`.

Routes (`fabrique_gestionnaire(acces, racine, builds_en_cours, etat_modele)`) :
- GET :
  - `/` : la page ;
  - `/execution` : `{"en_cours": false}` ;
  - `/parc` : `{puces, bases: {puce: [..]}, base_defaut: {puce: env}, maitres, ids_pris, id_libre, reseaux, blocs:
    [{id, libelle, aide, puces, dependances}]}` ;
  - `/modele/etat` : rempli en A6 ; ici `{}` ;
  - `/interrompues`.
- POST :
  - `/apercu {reponses}` → `{persist, autoexec, refus, avertissements}`, calculé par le serveur avec
    `secrets=None` ;
  - `/prepare` → `prepare()` ;
  - `/creation {reponses, empreinte}` → `cree()` ;
  - `/interrompue/acquitte`.

Page (maquette validée, onglet A de `docs/superpowers/specs/2026-10-27-assistant-persist-maquette.html`) :
- pastilles cliquables **Carte · Réseau · Fonctions · Bloc métier · Vérification** ;
- formulaire à gauche, aperçu `<pre>` du persist à droite, rafraîchi par `/apercu` (anti-rebond de 300 ms) ;
- étape Réseau : rôle en boutons radio, liste des maîtres, id proposé et ids pris, réseaux en liste ;
- étape Fonctions : cases grisées avec leur raison (puce, dépendance) ;
- étape Bloc métier : liste de noms, le 1er principal, case « squelettes » ;
- étape Vérification : fichiers, avertissements, autoexec, diff, bouton « Créer l'env » grisé à toute saisie
  après le diff ;
- après création : liens build et Fichiers Berry, et résumé avec un bouton « Copier ».

Étapes :
- [x] Banc `test_assistant_persist_web.py` ROUGE. Serveur lancé sur un port libre et un dépôt d'essai.
  - Toutes les routes : codes et formes.
  - POST sans l'en-tête → 403.
  - **Aucune des 5 valeurs réelles de mot de passe dans aucune réponse**, y compris en erreur. — preuve : test_assistant_persist_web.py ROUGE puis VERT ; aucun mot de passe dans 35 reponses HTTP ; POST sans en-tete -> 403
- [x] Écrire `assistant_persist_web.py` et `assistant_persist_page.py` jusqu'au VERT. — preuve : 44a9c24 (assistant_persist_web.py, _page.py, _page_js.py)
- [x] Sonde Chrome `test_assistant_persist_page_chrome.py`, sur le modèle de
  `test_fichiers_berry_page_chrome.py` (DevTools, `Runtime.exceptionThrown`).
  - Chaque pastille s'affiche.
  - Changer le nom met l'aperçu à jour (le hostname change).
  - Esclave → liste des maîtres non vide.
  - « Créer » grisé après une saisie qui suit le diff.
  - 0 erreur JS.
  - Témoin : casser un identifiant DOM dans une copie de la page → sonde ROUGE. — preuve : test_assistant_persist_page_chrome.py : 53 OK, 0 erreur JS ; temoin id=creer casse detecte
- [x] **Annuaire** (demande explicite de l'utilisateur) :
  - ajouter `Outil("assistant_persist", "Assistant persist", "Assistant persist", GROUPES[2], …,
    DOSSIER + "outils_pc/assistant_persist_web.py", [_port("http", 7900)], "http", …)` à
    `annuaire_registre.OUTILS` ;
  - ajouter l'id à la liste figée de `test_annuaire.py` ;
  - `test_annuaire.py`, `test_annuaire_lanceur.py` et `test_annuaire_securite.py` VERTS. — preuve : tuile assistant_persist (Maintenance, 7900) ; test_annuaire, _lanceur, _securite VERTS
- [x] Cible Custom et intégration :
  - `build/cible_assistant_persist.py`, copie adaptée de `cible_fichiers_berry.py` (`NOM_CIBLE =
    "assistant_persist"`, port 7900, page démarrée détachée) ;
  - `import` + `enregistre` et `CIBLES_HORS_BUILD` dans `pre_utilitaires_platformio.py` ;
  - `"assistant_persist"` dans `garde_build.py::CIBLES_OUTILS` ;
  - tâche « Outil : assistant persist » dans `.vscode/tasks.json`, sur le modèle de la tâche 7800.
  - Bancs VERTS : `build/test_cible_assistant_persist.py`, `build/test_garde_build.py`.
  - La tâche VS Code est lancée une fois (Tasks: Run Task) avant d'être annoncée (leçon du 2026-10-13) : à faire par
    l'utilisateur, à noter dans le compte rendu. — preuve : cible_assistant_persist.py + test VERT, garde_build CIBLES_OUTILS, CIBLES_HORS_BUILD, tasks.json (${env:USERPROFILE}) ; tache a lancer une fois par l'utilisateur
- [x] Commit `feat(assistant-persist): page 7900, tuile de l'annuaire et cible Custom`. — preuve : 44a9c24, relecture approuvee

## A6 — Fidélité du modèle : fusion à l'ouverture et bouton

Fichiers : modifier `assistant_persist_modele.py`, `assistant_persist_web.py`, `assistant_persist_page.py` ; créer
`outils_pc/test_assistant_persist_fidelite.py`.

Interfaces produites :
- `fusionne_nouvelles(racine, modele) -> (modele, ajouts: list[str])` :
  - chaque chemin de `ecarts()["nouvelles"]` est ajouté à la bonne place ;
  - sous `socle`, ou sous `puces.<p>.ajouts` si une seule puce le porte ;
  - défaut = valeur la plus fréquente dans le parc (égalité → première carte par ordre de chemin) ;
  - chemin secret (feuille `mdp*|pass*|pwd*`) → `@secret:<chemin>` ;
  - chemin ajouté à `a_completer`.
- `ecrit_modele(racine, modele, nature)` par `fichiers_berry_sauvegarde.Transaction(racine, nature)` : JSON indenté
  par tabulation, fins de ligne du dépôt.
- `propose_mise_a_jour(racine, modele) -> {diff, empreinte, retraits, alignements}` et
  `applique_mise_a_jour(racine, empreinte)`. Disparues retirées, défauts divergents alignés, `a_completer` inchangé.
- `principal()` : `fusionne_nouvelles` + `ecrit_modele(..., "modele-auto")` au démarrage si `ajouts`. Le résultat est
  servi par `/modele/etat` (`{ajouts, disparues, divergentes, a_completer, erreur}`).
- POST `/modele/prepare` et `/modele/applique`.
- Bandeau orange « N clés ajoutées au modèle, à compléter », bouton « Mettre à jour le modèle » (diff puis
  validation).

Étapes :
- [ ] Banc ROUGE. Tests :
  - `fusion_cle_nouvelle` : dépôt d'essai, clé `serveur.udp.essai = 7` ajoutée à 2 persists → ajoutée au socle avec 7,
    présente dans `a_completer`, modèle écrit et sauvegarde créée ;
  - `fusion_secret` : nouvelle clé `serveur.mqtt.mdpSecours` → `@secret:…`, aucune valeur ;
  - `fusion_rien` : parc couvert → aucune écriture (date de modification inchangée) ;
  - `bouton_retrait` : clé du modèle absente du parc → proposée au retrait, appliquée seulement avec la bonne
    empreinte ;
  - `modele_illisible` (point 2) : modèle invalide → `principal` démarre, `/modele/etat.erreur` non vide, fichier
    intact, `/prepare` refusé ;
  - `banc_couverture_signale` : après fusion, `test_assistant_persist_modele.rien_a_completer` échoue (attendu :
    le modèle fusionné doit être relu).
- [ ] Écrire jusqu'au VERT, puis relancer la sonde Chrome avec un bandeau présent.
- [ ] Témoin : désactiver l'ajout à `a_completer` → `fusion_cle_nouvelle` ROUGE.
- [ ] Commit `feat(assistant-persist): mise a jour automatique et manuelle du modele`.

## A7 — Éditeur des entrées/sorties du bloc métier (décision 4, 2e étape)

Fichiers : créer `outils_pc/assistant_persist_elements.py` et `outils_pc/test_assistant_persist_elements.py` ;
modifier la page, le serveur et `assistant_persist_generation.persist`.

Interfaces produites :
- `GROUPES_ELEMENTS = ("boutons", "interrupteurs", "relais", "capteurs", "compteurs", "thermometres", "analogiques")`.
- `gabarits_elements(modele) -> dict[groupe, dict]` : clés de chaque élément relevées dans le parc (§4).
  - socle `activation, nom, id, pin, type, virtuel, relaisLie` ;
  - relais + `afficheWeb, value, etat, timer, publishMQTT, timestamp, idModBus` ;
  - LED : + `channel, nbLeds`.
  Les gabarits entrent dans le modèle sous `metier.elements` (A1 complété).
- `broches_valides(puce) -> list[int]` : lues dans l'ordre des GPIO de `data/fs/configGlobal.be` (branches `typeESP`),
  jamais devinées.
- `verifie_elements(puce, elements, broches_drivers) -> list[str]` : refus en cas de broche hors plage, broche en
  double (éléments et broches des drivers activés : ModBus RX/TX, I2C, LEDs), ou nom en double dans un groupe.
- `Reponses.elements: dict[groupe, list[dict]]`, écrit dans `modules.<principal>.environnement.<groupe>.<groupe sing.>N`.

Étapes :
- [ ] Banc ROUGE :
  - `rejeu_environnement` : l'`environnement` de la cuve rejoué = le vrai ;
  - `broche_double` : refus ;
  - `broche_hors_plage_esp32` : refus ;
  - `broche_driver` : relais sur la broche RX ModBus → refus.
- [ ] Écrire jusqu'au VERT ; retirer la tolérance `environnement` de `rejeu_parc` (A3), qui doit rester VERT.
- [ ] Page : étape Bloc métier, tableau d'éléments (ajout, suppression, broche en liste), sonde Chrome étendue
  (ajouter 2 relais et voir l'aperçu changer).
- [ ] Témoin : `verifie_elements` sans les broches des drivers → `broche_driver` ROUGE.
- [ ] Commit `feat(assistant-persist): editeur des entrees/sorties`.

## A8 — Analyse des clés `adressMAC` / `adresseMAC` et `telePeriod` (lecture seule)

Décision du 2026-10-27 : les clés restent telles quelles ; l'analyse est rendue à l'utilisateur, qui décide.

- [ ] Recenser :
  - écrivains et lecteurs de `serveur.adressMAC` et de `serveur.adresseMAC` dans `data/` (hors `*sauvegarde*`),
    au format `fichier::fonction` ;
  - quand chacune est écrite (démarrage, discovery), et si une carte lit l'une en croyant lire l'autre.
- [ ] Recenser les lecteurs de `serveur.udp.telePeriod`, `serveur.rangeExtender.telePeriod` et `diverses.telePeriod`
  (grep du chemin complet et des accès par `find("telePeriod")`, leçon du 2026-10-04).
- [ ] Rédiger `outils_docs/ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md` :
  - en place, avantages, inconvénients ;
  - options : laisser, fusionner, retirer ;
  - effet de chacune sur le modèle et sur les cartes.
  Aucun fichier de code modifié.
- [ ] Commit `docs: analyse des cles adressMAC/adresseMAC et telePeriod`, puis présenter les options à l'utilisateur.

## A9 — Documentation

- [ ] `outils_docs/README.md` : § « Assistant persist (page web) » :
  - lancement (tuile, tâche, cible) ;
  - étapes ;
  - mots de passe ;
  - mise à jour du modèle ;
  - bancs.
- [ ] `CLAUDE.md`, carte des documents : entrée `assistant_persist_web.py` (+ modules, bancs, spec, plan), sur le
  modèle de l'entrée `fichiers_berry_web.py`. Lancer
  `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` → code 0.
- [ ] Skill `bancs` : ligne « assistant_persist_* → bancs `test_assistant_persist_*.py` ».
- [ ] Description de l'outil dans `annuaire_registre.py` relue. Mémoire du projet : une entrée.
- [ ] Commit `docs(assistant-persist): mode d'emploi et carte des documents`.

## A10 — Modification d'un env existant (décision 9 : à déclencher par l'utilisateur)

Ne pas commencer sans son feu vert. À ce moment-là, écrire d'abord un plan détaillé de cette action (spec §6 point
7). Cadre déjà fixé :
- relire le persist d'une carte vers `Reponses` (`reponses_depuis_persist`, A3) ;
- ajouter ou retirer des blocs et des éléments ;
- réécrire le persist en **gardant le texte** des parties non touchées (`spans_json`,
  `fichiers_berry_coprocesseur._membres`), jamais par un `json.dumps` complet ;
- même transaction, même diff.

- [ ] Feu vert de l'utilisateur, puis plan détaillé de l'action écrit et validé.
- [ ] Réalisation selon ce plan.

## Améliorations restantes

- [ ] [projet] Fumée réelle avec l'utilisateur (spec §7) :
  - création d'un env de test par la page ;
  - compilation par la page build, hors d'un autre build ;
  - suppression par la page 7800.
- [ ] [projet] Relire et compléter les questions des clés `a_completer` après chaque fusion automatique.

## Vérification

À la fin de chaque action : son banc VERT avec son témoin ROUGE. Bancs de non-régression :
- `test_fichiers_berry_*.py` ;
- `test_annuaire*.py` ;
- `build/test_garde_build.py` ;
- `genere_schema_persist.py --valide` (8/8) ;
- `banc_demarrage.py` (6 cartes inchangées).

Avant de déclarer la page prête, la sonde Chrome doit être verte (leçon du 2026-10-16).
