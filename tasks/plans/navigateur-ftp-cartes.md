---
chantier: navigateur-ftp-cartes
titre: Navigateur FTP des cartes (page de l'annuaire, FTP allumé à la demande)
objectif: Parcourir, télécharger, envoyer, ranger et supprimer les fichiers d'une carte par FTP depuis une page de l'annuaire, le FTP n'étant allumé que le temps de la session
statut: actif
cree: 2026-11-20
maj: 2026-11-21 (A6 faite, commit 1e1891ba3 ; reste A7, essais sur cartes)
famille: methode
liens: menage-page, cartes-simulees
spec: 2026-11-20-navigateur-ftp-cartes-design.md
---
# Navigateur FTP des cartes

## Contexte

Spec : `docs/superpowers/specs/2026-11-20-navigateur-ftp-cartes-design.md` (à lire avec ce plan, elle porte le
pourquoi et les décisions). Maquette retenue (A) : `outils_docs/navigateur_ftp/maquettes_interfaces.html`.

Exécution : superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans, action par action.

Architecture : un outil PC Python sur le modèle de `outils_pc/icones_catalogue_web.py` et `menage_web.py`
(`ThreadingHTTPServer`, `acces_web.Acces`, `annuaire_outils.hote_autorise`). Le serveur allume le FTP d'une carte
par HTTP (`build_ota_http._commande(ip, "UfsFTP 1|2", delai)`), lui parle par `ftplib` (bibliothèque standard) et
l'éteint (`UfsFTP 0`) à chaque fin de session. Page HTML/CSS/JS dans une constante Python. Aucune dépendance ajoutée.

Bancs : scripts à code de sortie (0 = vert), fonction `verifie(obtenu, attendu, libelle)` comme
`test_icones_catalogue_web.py`, lancés par le Python de PlatformIO :
`~/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/outils_pc/<banc>.py`.

### Contraintes globales (copiées de la spec)

- Port 7450 ; groupe de l'annuaire « Configuration des cartes » ; `NOM_CIBLE` `ftp_cartes`.
- Fichiers `outils_pc/ftp_cartes_web.py`, `ftp_cartes_page.py`, `ftp_cartes_session.py`, `ftp_cartes_liste.py`,
  `build/cible_ftp_cartes.py` ; chacun sous 500 lignes.
- FTP de la carte : contrôle 21, données 50009 (passif seul), un client à la fois, déconnexion du client par la carte
  après 5 min sans commande.
- Extinction (`UfsFTP 0`) sur : « Déconnecter », changement de carte, `pagehide` + `sendBeacon`, 15 min (900 s)
  sans action comptées par le serveur PC, arrêt de l'outil (`atexit` compris).
- Délais : allumage 10 s au plus, opération FTP 30 s.
- Identifiants FTP lus dans `tasmota/user_config_override.h` côté serveur, jamais renvoyés à la page ni journalisés.
- Écritures (allumage, envoi, suppression, dossier, renommage, déplacement) : `acces_web.est_local` seulement.
- Fichiers protégés (seconde confirmation) : `autoexec.be`, `autoexec.bat`, `_persist.json`, `*.bec`, `.drvset*`,
  suppression des dossiers `/sd` et `/json`.
- Rien n'est écrit dans le dépôt par l'outil. Commits : français, sans accents, sans Co-Authored-By,
  `git commit -- <chemins>`, agent `controleur-secrets` lancé et lu avant chaque commit.

### Points de vigilance (non couverts par la spec, testés dans l'action indiquée)

1. Un nom de fichier de la carte avec espace, accent ou `#` : liste, téléchargement et suppression doivent marcher
   (A3 `cas_noms_speciaux`, A5 sonde).
2. Une carte qui redémarre au milieu d'une session : l'opération suivante rend une erreur lisible, pas une page figée,
   et la pastille repasse à « éteint » (A3 `cas_carte_perdue`).
3. Deux onglets du navigateur sur l'outil : le second voit la session ouverte par le premier, aucune seconde
   connexion FTP n'est tentée (A4 `cas_deux_onglets`).
4. Envoi d'un fichier plus gros que `MAX_ENVOI` (16 Mo) : refus avant toute écriture sur la carte (A4 `cas_envoi_trop_gros`).
5. `sendBeacon` n'envoie pas l'en-tête anti-CSRF `X-...` des autres POST : la route `/ferme` l'accepte sans cet
   en-tête (origine vérifiée), et elle seule (A4 `cas_beacon`).

## A1 — Persist : FTP coupé sur toutes les cartes du dépôt
- [x] Vérifier qu'aucun build ne tourne (`garde_build.py`), puis passer `serveur.serveurFTP.activation` de `"ON"` à `"OFF"` dans chaque `data/<lieu>/<carte>/_persist.json` (hors dossiers `*-sauvegarde`) par remplacement de texte limité au bloc `serveurFTP` : une seule ligne changée par fichier — preuve : 10 persist, `git diff -U0` = 10 fois `"activation": "ON"` -> `"OFF"`, bloc `serveurFTP` dans le contexte de chacun (P4 à part, étape suivante)
- [x] Persist du P4 (`data/garage/tasmota32p4-serveur-modbus/_persist.json`) : même changement, APRÈS le commit des modifications en cours d'une autre session dans ce fichier (choix de l'utilisateur du 2026-11-20) — preuve : accord de l'utilisateur du 2026-11-21 ; condition levée (l'autre session a commité, `a1e23a51a`, fichier propre avant) ; remplacement d'octets limité au bloc `serveurFTP`, `git diff --numstat` = `1 1`, seule ligne changée `"activation": "ON"` -> `"OFF"`, JSON relu en `strict=False` = `OFF` ; pas encore commité
- [x] Vérification : script jetable (scratchpad) qui relit chaque persist en `json.loads(..., strict=False)` et affiche `env : activation` ; attendu `OFF` partout, P4 et cuve compris ; `git diff --stat` = 1 ligne par fichier — preuve : `OFF` partout sauf le P4 (`ON`, reporté), numstat `1 1` sur les 10 fichiers (rapport `.superpowers/sdd/navigateur-ftp-cartes/task-1-report.md`)
- [x] `controleur-secrets` sur ce diff (lu), puis commit `chore(persist): serveur FTP coupe par defaut sur toutes les cartes` — preuve : contrôle OK, commit `4d56b759f` (10 fichiers, 10+/10-) ; message réel `chore(persist): serveur FTP coupe par defaut sur 10 cartes` (le P4 n'en faisait pas partie) ; recontrôlé le 2026-11-21 : `git show` = 10 fois `"activation": "ON"` -> `"OFF"`, 1 ligne par fichier, et relevé de l'arbre : 13 `OFF`, 1 `ON` (P4), 0 illisible
- [x] Noter dans « Améliorations restantes » la liste des cartes dont le persist est à porter sur la carte (A7) — preuve : section « Améliorations restantes » ci-dessous

## A2 — Liste des cartes éligibles (`ftp_cartes_liste.py`)

Interfaces produites :
`est_esclave_rgx(persist: Path) -> bool | None` (None = illisible) ;
`ftp_retire(texte_h: str, firmware: str) -> bool | None` (None = doute) ;
`identifiants(racine: Path, firmware: str) -> tuple[str, str]` ;
`liste(racine: Path) -> {"cartes": [{"env", "lieu", "nom", "hote", "adresse", "puce", "firmware"}], "exclues": [{"env", "raison"}]}`.
Consomme `build_envs.liste_envs`, `lieux.identites`, `lieux.puce`.

- [x] Banc `outils_pc/test_ftp_cartes_liste.py`, mini-dépôt temporaire, cas rouges d'abord :
  - [x] `cas_esclave` : persist avec `rangeExtender` `ON`, `id` 2, `ipMaitre` → exclue, raison contient « Range Extender »
  - [x] `cas_persist_illisible` : JSON cassé → `est_esclave_rgx` rend None, carte exclue ; persist avec caractère de contrôle dans une chaîne → lu (strict=False)
  - [x] `cas_sans_use_ftp` : section `#elif defined(FIRMWARE_X)` avec `#undef USE_FTP` → exclue ; section sans `#undef` → gardée ; `#undef USE_FTP` sous un `#if !defined(FIRMWARE_X)` → gardée pour l'env X, exclue pour un autre env de la section ; condition non évaluable → doute → exclue
  - [x] `cas_puce` : env ESP8266 → exclue
  - [x] `cas_adresse` : IP du `.h` → `adresse` = IP ; IP absente ou 0.0.0.0 → `adresse` = `<Hostname>.local`
  - [x] `cas_identifiants` : `USER_FTP`/`PW_FTP` de la partie commune, remplacés par ceux de la section de l'env s'ils y sont redéfinis ; `json.dumps(liste(...))` ne contient pas le mot de passe
  - [x] `cas_depot_reel` : sur le vrai dépôt, la cuve (`tasmota32s3-capteurs-cuve-modbus`), le rideau et le portail sont exclus ; `tasmota32s3-bureau-serveur-debits-pac` est exclu (esclave de l'écran) ; le P4, l'écran des débits et la cave S3 sont présents ; les 3 ESP32 sans PSRAM sont exclus — preuve : banc vert sur le vrai dépôt (rapport `task-2-report.md`)
- [x] Lancer le banc : rouge (module absent) — preuve : rouge constaté, module absent (rapport `task-2-report.md`)
- [x] Écrire `ftp_cartes_liste.py` (lecture des sections du `.h` sur le modèle de `autoexec_gardes.py` / `build/verifie_lib_ignore.py`, sans modifier `build_envs.py`) — preuve : `ftp_cartes_liste.py` (252 lignes), commit `ba8d59eeb`
- [x] Banc vert, sortie collée en preuve ; témoin : retirer le test d'esclave fait rougir `cas_depot_reel` — preuve : 50 OK, code 0 ; témoins : `est_esclave_rgx` forcé à False rougit `cas_esclave` et `cas_depot_reel`, `!` sans effet donne 5 KO
- [x] `controleur-secrets` lu, commit `feat(ftp): liste des cartes joignables par FTP` — preuve : contrôle OK, relecture `relecteur-outils-python` sans critique ni important, commit `ba8d59eeb`

## A3 — Session FTP (`ftp_cartes_session.py`) et faux serveur de carte

Interfaces produites :
`class Session(commande=build_ota_http._commande, fabrique_ftp=ftplib.FTP, horloge=time.monotonic, inactivite=900)` ;
`ouvre(carte: dict, support: str) -> dict` (`support` ∈ `"sd"`, `"flash"`) ; `ferme(raison: str) -> dict` ;
`etat() -> {"env", "support", "etat", "message", "sd"}` (`etat` ∈ `eteint`, `allumage`, `actif`, `erreur` ; `sd` ∈ True, False, None) ;
`liste(chemin) -> [{"nom", "type", "taille", "date"}]` ; `lit(chemin, sortie: BinaryIO)` ;
`zip(chemins: list[str], sortie: BinaryIO)` ; `envoie(dossier, nom, flux, ecraser: bool)` ;
`supprime(chemin, confirmations: int)` ; `cree_dossier(chemin)` ; `deplace(source, cible)` ; `tic()` ;
`valide_chemin(chemin: str) -> str` (ValueError) ; `protege(chemin: str) -> bool`.
Erreurs métier : `class RefusFtp(Exception)` (message lisible, code HTTP 409 côté web).

- [x] Faux serveur `outils_pc/faux_ftp_carte.py` (pour les bancs) : `socketserver`, dossier temporaire, un seul client, PASV seul sur un port choisi, commandes `USER PASS PWD CWD TYPE PASV MLSD LIST RETR STOR DELE MKD RMD RNFR RNTO NOOP QUIT`, option `coupe_apres(n)` pour simuler une carte perdue ; faux `commande(ip, cmnd, delai)` qui journalise les `UfsFTP n` — preuve : faux_ftp_carte.py (265 lignes), commit `1aedba758`
- [x] Banc `outils_pc/test_ftp_cartes_session.py`, cas rouges d'abord : — preuve : 22 cas (dont `cas_supprime_detours`, `cas_noms_hostiles`, `cas_ouvre_refus_eteint`, `cas_allumage_delai`, `cas_concurrence` ajoutés à la relecture), 131 OK
  - [x] `cas_ouvre` : `ouvre(carte, "sd")` envoie `UfsFTP 1`, `"flash"` envoie `UfsFTP 2` ; `etat()["etat"] == "actif"`
  - [x] `cas_sd_inconnue` : `Ufs` sans réponse → `etat()["sd"] is None` ; `ouvre(..., "sd")` lève `RefusFtp` (jamais la flash sous l'étiquette SD)
  - [x] `cas_ferme_toujours` : `ferme()` envoie `UfsFTP 0` même si `quit()` FTP lève ; idem après `ouvre` d'une autre carte (l'ancienne reçoit `UfsFTP 0` avant que la nouvelle reçoive `UfsFTP 1`)
  - [x] `cas_inactivite` : horloge avancée de 899 s → `tic()` ne ferme pas ; 901 s → `UfsFTP 0`, raison « inactivite »
  - [x] `cas_reconnexion` : client FTP coupé par la carte (timeout 5 min simulé) → `liste()` rouvre la session une fois sans `UfsFTP` supplémentaire et réussit
  - [x] `cas_carte_perdue` : `coupe_apres(1)` + reconnexion impossible → `RefusFtp` lisible, `etat()["etat"] == "erreur"`
  - [x] `cas_chemins` : `valide_chemin` refuse `..`, `\x00`, `\n`, plus de 255 caractères ; accepte `/histo/mesures-2026-11.bin`
  - [x] `cas_protege` : `supprime("/autoexec.be", 1)` lève `RefusFtp` ; `supprime("/autoexec.be", 2)` supprime ; idem `/sd` et `/json` ; `/histo/x.bin` avec 1 confirmation supprime
  - [x] `cas_noms_speciaux` : `mesures 2026#é.bin` listé, lu, supprimé
  - [x] `cas_zip` : `zip(["/histo"])` contient les fichiers du dossier avec leurs chemins relatifs et leurs octets exacts
  - [x] `cas_place` : `Ufs` donne une place libre inférieure à la taille du flux → `RefusFtp` avant tout `STOR` ; place inconnue → envoi tenté
  - [x] `cas_ecrasement` : `envoie(..., ecraser=False)` sur un nom existant lève `RefusFtp` ; `ecraser=True` remplace
  - [x] `cas_deplace` : `deplace("/histo/a.bin", "/archives/a.bin")` (dossier existant) déplace
  - [x] `cas_mot_de_passe` : aucune valeur rendue par `etat()` ni message de `RefusFtp` ne contient le mot de passe
- [x] Lancer le banc : rouge — preuve : rouge constaté, module absent (rapport `task-3-report.md`)
- [x] `ouvre` refuse une `adresse` qui ne correspond pas à `^[A-Za-z0-9.-]+$` (nom d'hôte venu du persist, remarque de la relecture de A2), cas `cas_adresse_invalide` du banc — preuve : `cas_adresse_invalide` vert
- [x] Écrire `ftp_cartes_session.py` : un `threading.Lock` autour de toute opération FTP ; `mlsd()` avec repli `LIST` ; attente du port 21 par `socket.create_connection` répétée jusqu'à 10 s ; `ftplib` garde l'hôte du contrôle pour les données (adresse PASV ignorée, défaut de `ftplib`) — preuve : 375 lignes, commit `1aedba758`
- [x] Banc vert, sortie collée en preuve ; témoin : supprimer l'envoi de `UfsFTP 0` dans `ferme` fait rougir `cas_ferme_toujours` — preuve : 131 OK, code 0 ; sans `UfsFTP 0` dans `ferme` : 9 KO ; `_allume` posé après l'envoi : 1 KO
- [x] `relecteur-outils-python` sur les deux fichiers, remarques traitées ; `controleur-secrets` lu, commit `feat(ftp): session FTP allumee a la demande` — preuve : relecture Opus : 3 importants + zip-slip corrigés en un tour, re-relecture 6/6 ADDRESSED ; contrôle de secrets OK ; commit `1aedba758`

## A4 — Serveur web et routes (`ftp_cartes_web.py`)

Interfaces produites (consommées par la page, A5) :
`GET /` (page), `GET /cartes` (`ftp_cartes_liste.liste`), `GET /etat`, `GET /liste?chemin=`, `GET /telecharge?chemin=` (fichier brut, `Content-Disposition: attachment`) ;
`POST /ouvre {env, support}`, `POST /ferme {}` (accepté sans en-tête `X-...`, origine vérifiée), `POST /zip {chemins}` (zip en réponse),
`POST /envoie?dossier=&nom=&ecraser=0|1` (corps brut, `MAX_ENVOI = 16 * 1024 * 1024`), `POST /supprime {chemin, confirmations}`, `POST /dossier {chemin}`, `POST /deplace {source, cible}`.
`fabrique_gestionnaire(acces, racine, session)` ; `principal()` avec `--http 7450`, options `acces_web`, `atexit` qui appelle `session.ferme("arret de l'outil")`, fil d'horloge qui appelle `session.tic()` toutes les 10 s.

- [x] Banc `outils_pc/test_ftp_cartes_web.py` (serveur réel sur 127.0.0.1, port libre, faux serveur de carte d'A3, mini-dépôt), cas rouges d'abord : — preuve : banc `test_ftp_cartes_web.py` : 9 cas (7 du plan + `cas_concurrence`, `cas_serveur`), 77 OK, VERT
  - [x] `cas_routes` : chaque route ci-dessus répond (200 ou 409 attendu), verbe inconnu → 405 — preuve : `cas_routes` vert ; PUT, DELETE, HEAD, OPTIONS → 405 ; `filename*` d'un nom accentué vérifié
  - [x] `cas_ecritures_ce_pc` : `POST /ouvre`, `/envoie`, `/supprime`, `/dossier`, `/deplace` depuis une adresse non locale (handler avec `client_address` simulé) → 403 ; `GET /liste` et `/telecharge` depuis cette adresse avec jeton → 200 — preuve : `cas_ecritures_ce_pc` vert
  - [x] `cas_beacon` : `POST /ferme` sans en-tête `X-...` et origine locale → 200 et `UfsFTP 0` ; `POST /supprime` sans en-tête → refusé — preuve : `cas_beacon` vert ; mutants « X exigé sur /ferme » 4 KO, « origine non vérifiée » 2 KO (relecture)
  - [x] `cas_deux_onglets` : deux `GET /etat` successifs voient la même session ; un second `POST /ouvre` sur la même carte ne crée pas de seconde connexion FTP — preuve : `cas_deux_onglets` vert, et `cas_concurrence` : deux /ouvre simultanés → un seul UfsFTP, un seul USER (`Session.ouvre_ou_reprend` sous verrou ; témoin sans elle : UfsFTP [1, 1])
  - [x] `cas_envoi_trop_gros` : `Content-Length` > `MAX_ENVOI` → 413, aucun `STOR` reçu par le faux serveur — preuve : `cas_envoi_trop_gros` vert : 413, aucun STOR
  - [x] `cas_secret` : aucune réponse (`/cartes`, `/etat`, erreurs) ne contient le mot de passe du mini-dépôt — preuve : `cas_secret` refait au tour de corrections : refus 530 citant le mot de passe → 409 masqué, RuntimeError forcée → 500 sans le mot de passe ; témoin « 500 = str(erreur) » ROUGE
  - [x] `cas_host_hostile` : `Host: evil.example` → 403 (`hote_autorise`) — preuve : `cas_host_hostile` vert ; mutant sans `hote_autorise` 2 KO
- [x] Lancer le banc : rouge — preuve : ModuleNotFoundError sur `ftp_cartes_web` avant le code (`.superpowers/sdd/navigateur-ftp-cartes/task-4-report.md`)
- [x] Écrire `ftp_cartes_web.py` sur le modèle de `icones_catalogue_web.py` (CSP, en-têtes) et des POST de `menage_web.py` (taille du corps bornée, `est_local`) — preuve : `ftp_cartes_web.py` (284 lignes) : CSP, Host, X-, est_local, corps borné, timeout 60 s, SO_EXCLUSIVEADDRUSE, atexit + fil tic 10 s
- [x] Banc vert, sortie collée en preuve ; témoin : retirer le contrôle `est_local` de `/supprime` fait rougir `cas_ecritures_ce_pc` — preuve : VERT sur 3 lancements + 1 relance du relecteur (77 OK) ; témoin `/supprime` retiré des écritures → 3 KO sur `cas_ecritures_ce_pc`
- [x] `relecteur-outils-python` lu ; `controleur-secrets` lu, commit `feat(ftp): serveur web du navigateur FTP` — preuve : relecture Opus : 1 spec ❌ (`cas_secret`) + 2 importants corrigés en un tour, re-relecture 4/4 ADDRESSED ; contrôle de secrets OK ; commit `77a429cae`

## A5 — La page (interface A) et sa sonde Chrome (`ftp_cartes_page.py`)
- [x] Écrire `PAGE` d'après la maquette A et la spec §6 : listes Lieu et Carte (`remplitParLieu` de `lieux.JS`, `?lieu=`), pastille d'état, bascule Flash / SD (grisée si `sd` vaut False, « SD inconnue » si None), bouton « Historique et énergie » (SD puis `/histo`), « Déconnecter », arborescence chargée dossier par dossier, tableau à cases, barre d'actions ; confirmations (une, ou deux pour les fichiers protégés) ; `pagehide` → `navigator.sendBeacon("/ferme")` ; mode sombre ; aucun CDN — preuve : `ftp_cartes_page.py` (439 lignes), listes Lieu/Carte par `lieux.JS`, pastille 4 états, bascule Flash/SD, confirmations, `pagehide` + `sendBeacon`, mode sombre, aucun CDN ; copie figée de la session au clic (tour 2)
- [x] Sonde `outils_pc/test_ftp_cartes_page_chrome.py` (hermétique : serveur de l'outil + faux serveur de carte, Chrome headless au profil `sonde_ftp_cartes`) : choix d'une carte → pastille « actif » ; liste de `/histo` ; nom spécial affiché ; suppression d'un fichier protégé : 1 confirmation → toujours présent, 2 → supprimé ; fermeture de l'onglet → le faux serveur a reçu `UfsFTP 0` ; aucun message d'erreur de la console JS — preuve : `test_ftp_cartes_page_chrome.py` (379 lignes), 77 vérifications ; rouge avant la page (22 échecs avec la page minimale)
- [x] Sonde verte, sortie collée en preuve ; Chrome `sonde_*` orphelins vérifiés arrêtés 15 s après — preuve : sonde 6 passages de suite verts (77 OK), relancée verte par chaque relecteur ; 0 Chrome `sonde_` vivant 15 s après chaque lot
- [x] `relecteur-pages-web` lu, remarques traitées ; `controleur-secrets` lu, commit `feat(ftp): page du navigateur FTP` — preuve : relecture Opus + 2 re-relectures ciblées (tour 1 : 11/11 ADDRESSED sauf B2 page et B13 ; tour 2 : 3/3 ADDRESSED) ; contrôle de secrets OK ; commit `3003ca9e4`

## A6 — Intégration : annuaire, tâche VS Code, cible Custom, documentation
- [x] Entrée `Outil("ftp_cartes", ...)` dans `annuaire_registre.py`, groupe `GROUPES[3]` (« Configuration des cartes »), `_port("http", 7450)` ; `test_annuaire.py` vert — preuve : `annuaire_registre.py` (entrée après `assistant_persist`, aussi `lieu=True` car la page lit `?lieu=`), `test_annuaire.py` mis à jour (id `ftp_cartes`, 23 -> 24 outils) : VERT, 185 OK, code 0
- [x] Tâche VS Code « Outil : navigateur FTP des cartes (http://127.0.0.1:7450) » dans `.vscode/tasks.json` (fichier suivi ET présent en amont : demander l'accord avant, comme pour `.vscode/settings.json`) — preuve : accord de l'utilisateur du 2026-11-21, `git diff -- .vscode/tasks.json` = la seule tâche ajoutée (+10 lignes), JSON valide (31 tâches, commentaires `//` retirés)
- [x] Vérifier qu'aucun build ne tourne ; `build/cible_ftp_cartes.py` copié de `cible_icones_catalogue.py` (`NOM_CIBLE = "ftp_cartes"`, `PORT_DEFAUT = "7450"`) ; import et `enregistre(env)` dans `build/pre_utilitaires_platformio.py`, `NOM_CIBLE` ajouté à la liste de sortie anticipée ; `'ftp_cartes'` ajouté à `CIBLES_OUTILS` de `.claude/hooks/garde_build.py` — preuve : aucun `platformio run` ni `scons` (seuls `annuaire_outils.py` et `build_web.py`, des outils) avant les éditions de `build/` et du hook ; `cible_ftp_cartes.py` créé, pré-script et hook édités
- [x] Bancs `build/test_cible_ftp_cartes.py` (copie adaptée de `test_cible_icones_catalogue.py`) et `build/test_garde_build.py` verts — preuve : les deux VERT, code 0 ; mutants jetables en faux dépôt (`PORT_DEFAUT` 7451, `ftp_cartes` hors `CIBLES_OUTILS`, pré-script sans `NOM_CIBLE` ou sans `enregistre`) : tous ROUGE, témoin sans mutation VERT ; vraie page démarrée sur 17450 reconnue par `cible_ftp_cartes.repond`
- [x] Section « Navigateur FTP des cartes (page web) » dans `outils_docs/README.md` (usage, FTP à la demande, persist à `OFF`, esclaves exclus, fichiers protégés) ; entrée dans la carte des documents de `CLAUDE.md` ; `verifie_references_docs.py` à 0 défaut ; `relecteur-docs` lu — preuve : README (section avant « Fabrique d'extensions »), `CLAUDE.md` (entrée et « les 22 `cible_*.py` »), `verifie_references_docs.py` 31 documents, 0 défaut, code 0 ; `relecteur-docs` lu : 0 bloquant, 0 à corriger, 3 mineurs (gras semé dans la prose du README retiré ; deux énumérations de 4 à 5 termes laissées, facultatif), 12 points vérifiés exacts (renvois, options, cible, tâche, 5 fins de session, décompte 13 persist sur 14 à `OFF`, 22 `cible_*.py`, fichiers sous 500 lignes)
- [x] `controleur-secrets` lu, commit `feat(ftp): navigateur FTP dans l'annuaire, cible et documentation` — preuve : contrôle de secrets OK, 0 alerte sur 11 fichiers ; commit `1e1891ba3` (11 fichiers), sans trailer

## A7 — Essai sur les cartes réelles
- [ ] Porter le persist à `OFF` sur le P4 et sur une S3 (onglet « Fichiers » de la page Build), puis vérifier `UfsFTP` → 0 après un redémarrage — état du 2026-11-21 : P4 FAIT (méthode changée par décision de l'utilisateur : le persist du dépôt diffère de celui de la carte, on fusionne la seule ligne FTP dans le persist actuel ; `UfsFTP` 2 → 0 vérifié après redémarrage ; sauvegarde du persist d'avant : `%LOCALAPPDATA%\outils_tasmota\build\persist\tasmota32p4-garage-serveur-modbus-20261121-103348.json`) ; S3 : aucune joignable avec un firmware FTP (grenier RDC : `UfsFTP` inconnu), reste à faire quand une S3 répond
- [ ] P4 : ouvrir depuis la page, relever la racine vue en SD et en flash, la réponse de `Ufs` et la présence des dates `MLSD` ; reporter ces constats dans la spec §10
- [ ] P4 : télécharger `/histo` en zip et comparer la taille aux fichiers listés ; envoyer puis supprimer un fichier témoin ; créer, déplacer, supprimer un dossier témoin
- [ ] Après chacun des 5 événements de fin de session (Déconnecter, autre carte, fermeture d'onglet, 15 min, arrêt de l'outil) : `UfsFTP` lu sur la carte = 0
- [ ] Même parcours court sur une S3 (sans SD si possible : bascule SD grisée ou « SD inconnue »)
- [ ] Porter le persist à `OFF` sur les autres cartes listées en A1 ; cocher chacune dans « Améliorations restantes »

## A8 — Reprise des améliorations restantes (décisions du 2026-11-21)
- [x] Décisions de l'utilisateur consignées : seconde confirmation pour DÉPLACER un fichier protégé ; FTP éteint au dernier onglet seulement ; l'annuaire refuse d'arrêter l'outil tant qu'une session est ouverte ; A7 : pilote d'abord (une S3 sans SD puis le P4), les autres cartes ensuite — preuve : réponses à la question groupée du 2026-11-21, toutes les options recommandées
- [x] Tâche 7, serveur : seconde confirmation du déplacement, dossier contenant un fichier protégé = deux confirmations, cible d'un déplacement déjà existante refusée, `Session.ouvre` sûre sur exception, `noms_ignores` borné, paire env/support pour `/zip` et `/telecharge`, registre d'onglets (FTP éteint au dernier), `GET /execution` et entrée d'annuaire (`route_occupe`, `arret_refuse`) — preuve : commit `54e3397ea` ; bancs rejoues le 2026-11-21 : test_ftp_cartes_liste, test_ftp_cartes_web, test_ftp_cartes_session, test_annuaire VERTS (code 0)
- [x] Tâche 8, liste : test de concordance de `GENERIQUES` avec les bases du cenv ; première liste de `/cartes` rapide (cache ou chargement paresseux) — preuve : commit `54e3397ea` (`ftp_cartes_liste.py`, concordance de `GENERIQUES`, cache de `liste()` invalidé par `(chemin, mtime_ns, taille)`, préchauffage) ; bancs rejoues le 2026-11-21 : test_ftp_cartes_liste, test_ftp_cartes_web, test_ftp_cartes_session, test_annuaire VERTS (code 0)
- [x] Tâche 9, page et sonde : mineurs de la page A5, seconde confirmation du déplacement, identifiant d'onglet, paire env/support sur le zip et le téléchargement — preuve : page dans `54e3397ea`, sonde dans `e8fbbe24d` (sonde principale + `_onglets` + `_corrections`, 3 passages verts de suite, 15 au total sur le code final, 0 Chrome `sonde_` orphelin). Limites non levées : B9 (repli sur la flash si `sd` vaut null) non modifié, B15 (corps de 16 Mo) évité seulement quand le fichier figure dans la liste affichée
- [x] Tâche 10, sondes à page habillée : neutraliser la barre commune (`acces_barre`) dans les autres sondes Chrome — preuve : commit `087b9bc8a` : `sonde_hermetique.py` + `test_sonde_hermetique.py` (3 mutants tués), appelé par 7 sondes (0 requête vers :7700 sous espion) ; `plan_maison` et `taches_planifiees` restent rouges comme avant (1 échec chacune, constaté sur la version HEAD)
- [ ] Relectures (`relecteur-outils-python`, `relecteur-pages-web`), documentation (README, `CLAUDE.md`, spec §7), `controleur-secrets`, commits
- [x] Lignes traitées de « Améliorations restantes » cochées avec leur preuve — preuve : 8 lignes de « Améliorations restantes » et les cases des tâches 7 à 10 cochées avec leurs commits (`54e3397ea`, `e8fbbe24d`, `087b9bc8a`) ; restent ouvertes A7 (cartes réelles), `GET /etat` sans contrôle d'origine, `sd` null, arrêt brutal, persist OFF des cartes injoignables

## Améliorations restantes
- [x] [projet] Page A5, mineurs reportés (relectures du 2026-11-21) : message « Rallumer » ou « autre onglet » écrasé quand le sondage ferme une boîte ouverte au milieu d'un geste (et « Envoyé : 0 fichier(s) » trompeur) ; `effaceVues()` absent de la branche non JSON de `ouvrir` ; `/zip` et `/telecharge` sans la paire env/support (409 en texte brut pour le zip) ; `ouvrir` et `deconnecter` ne ferment pas une boîte ouverte ; B9 repli automatique sur la flash si `sd` vaut null ; B15 corps de 16 Mo envoyé deux fois si le fichier existe déjà ; `protege()` ne regarde que le chemin visé (un dossier contenant `autoexec.be` part avec une seule confirmation) ; `Session.deplace` ne vérifie pas que la cible existe ; la sonde n'a pas de cas pour l'arrêt au premier 409 des boucles multi-fichiers ni pour l'assertion « 409 » avant clic — preuve : commits `54e3397ea` (page) et `e8fbbe24d` (sonde) ; reste B9 (`sd` null, décision de l'utilisateur) et B15 pour une liste périmée, voir la ligne « Téléchargement d'un seul fichier »
- [x] [projet] Sondes à page habillée (`acces.habille`) : leur barre lit les vraies fiches de présence et interroge la vraie page Build ; `test_ftp_cartes_page_chrome.py` neutralise `acces_barre`, les autres sondes non — preuve : commit `087b9bc8a` (`neutralise_barre()` dans 7 sondes ; la sonde FTP garde sa neutralisation en ligne, elle pourra utiliser `sonde_hermetique`)
- [x] [projet] Déplacer un fichier protégé (`autoexec.be`, `_persist.json`…) ne demande qu'une confirmation : seconde confirmation à décider avec l'utilisateur (relecture de A3) — preuve : décision de l'utilisateur du 2026-11-21 (deux confirmations) ; serveur et page dans `54e3397ea`, cas de la sonde `test_ftp_cartes_page_chrome_onglets.py` dans `e8fbbe24d`
- [x] [projet] `Session.ouvre` : une exception levée par `identifiants()` sur un changement de support laisse le FTP allumé jusqu'au `tic()` (15 min) ; `noms_ignores` grossit sans limite (relecture de A3) — preuve : commit `54e3397ea` (`ouvre_ou_reprend` sûre sur exception, `noms_ignores` borné) ; `test_ftp_cartes_session.py` VERT le 2026-11-21
- [x] [projet] `ftp_cartes_liste.GENERIQUES` est écrite en dur : un `FIRMWARE_*` amont inconnu y est jugé faux (carte listée, refus visible à l'allumage) ; test de concordance avec les bases du cenv à prévoir — preuve : commit `54e3397ea` : test de concordance dans `test_ftp_cartes_liste.py` (VERT, rouge avec un `-DFIRMWARE_INCONNU` ajouté à une copie d'ini)
- [ ] [projet] Porter le persist à `OFF` sur chaque carte, A7. État du 2026-11-21 : garage P4 FAIT ; grenier RDC : firmware sans commande `UfsFTP`, rien à éteindre ; injoignables ce jour : cuve, rideau, portail, bureau ×2, étage 2, cave ×3 ; garage s3-serveur-modbus : même adresse que le P4 (env alternatif de la même carte). MÉTHODE : ne PAS envoyer le persist du dépôt par l'onglet « Fichiers » (il diffère de celui des cartes : GPIO, blocs écran, Ethernet, voir le relevé du 2026-11-21) ; fusionner la seule ligne FTP dans le persist ACTUEL de la carte avec `.superpowers/sdd/navigateur-ftp-cartes/pousse_ftp_off.py` (mode `apercu` puis `envoi`, même code que la page : sauvegarde, relecture, redémarrage). Liste d'origine : bureau ecran-debits-pac, bureau serveur-debits-pac, cave s3-ecran, cave s3-serveur-rly, étage 2 grenier, RDC grenier, garage P4 (persist déjà à `OFF` dans le dépôt le 2026-11-21), cuve, portail-jardin, rideau, garage s3-serveur-modbus
- [x] [projet] Page Build : `build_envs.adresse_par_maitre` lit les persist en strict, l'adresse de la cuve par le maître n'est pas calculée (IP à saisir à la main) — preuve : `strict=False` dans `build_envs.py::adresse_par_maitre` (correctif PRÉVENTIF : vérifié le 2026-11-21, les 14 persist du dépôt se lisent aussi en JSON strict, aucun ne porte de caractère de contrôle ; l'affirmation contraire, née en A1 puis reprise dans plusieurs commentaires, était fausse) ; cas ajouté à `test_build_envs.py` (caractère de contrôle dans une chaîne), rouge avant, VERT après ; sur le vrai dépôt la cuve obtient `192.168.0.43:8081` (source `maitre`), le rideau `:8082`, le portail `:8083` ; reste de même nature : `build_envs.py::topic_carte` lit encore en strict, non modifié, et une dizaine d'autres lecteurs de persist d'`outils_pc/` ; non commité
- [ ] [projet] `GET /etat?onglet=<hex>` enregistre un onglet sans contrôle d'origine (les GET n'en ont pas) : une page tierce pourrait maintenir jusqu'à 32 faux onglets et empêcher le « dernier onglet parti » ; borné par l'inactivité de 15 min ; piste : `vu()` seulement si une session est ouverte ou si `Sec-Fetch-Site` vaut `same-origin` (relecture de la tâche 7, 2026-11-21)
- [ ] [projet] Téléchargement d'un seul fichier : un 409 (session changée) n'est vu par le navigateur que comme un échec de téléchargement, seul remède `fetch` + blob (tâche 9) ; carte SD inconnue (`sd` null) : pas de repli automatique sur la flash, choix à confirmer
- [x] [projet] A5 : le `pagehide` de n'importe quel onglet (ou d'un autre appareil muni du jeton) éteint le FTP ouvert par un autre onglet : identifiant d'onglet ou extinction au dernier onglet, à trancher (relecture de A4) — preuve : décision de l'utilisateur du 2026-11-21 (dernier onglet seulement) ; registre `ftp_cartes_onglets.py` et identifiant d'onglet, commits `54e3397ea` et `e8fbbe24d`
- [ ] [projet] Arrêt brutal de l'outil (job de l'annuaire tué, console fermée) : `atexit` ne passe pas, le FTP de la carte reste allumé jusqu'au prochain redémarrage ou réseau (relecture de A4)
- [x] [projet] Arrêt brutal, piste (A6) : l'annuaire refuse d'arrêter un outil occupé quand `Outil.route_occupe` répond `{"en_cours": true}` (`annuaire_outils.py::route_occupee`, comme `/execution` de la page Build) ; `ftp_cartes_web.py` pourrait exposer cette route tant qu'une session est ouverte, avec `arret_refuse` dans `annuaire_registre.py`. Ne couvre ni la mort de l'annuaire (job tué) ni la tâche VS Code — preuve : commit `54e3397ea` : `GET /execution` de `ftp_cartes_web.py` et `arret_refuse` de `annuaire_registre.py` ; `test_annuaire.py` VERT le 2026-11-21. Ne couvre toujours pas la mort de l'annuaire (job tué) ni la tâche VS Code
- [x] [projet] Mesuré en A6 sur le vrai dépôt : premier `GET /cartes` en 3,7 s (6 cartes, 12 exclues), et un premier essai a dépassé 5 s : la page attend la liste avant d'afficher quoi que ce soit ; cache ou chargement paresseux à envisager — preuve : commit `54e3397ea` : cache de `liste()` et préchauffage au démarrage, cas de banc rouge puis vert dans `test_ftp_cartes_liste.py`
- [x] [projet] `menage_web.py` et `icones_catalogue_web.py` héritent de `allow_reuse_address = 1` : deux instances sur le même port sous Windows (corrigé dans `ftp_cartes_web.py` par `SO_EXCLUSIVEADDRUSE`, relecture de A4) — preuve : `ServeurMenage` et la nouvelle `ServeurIcones` (`allow_reuse_address = False` + `server_bind` en `SO_EXCLUSIVEADDRUSE`) ; cas « un second serveur sur le même port lève OSError » ajouté à `test_menage_web.py` (rouge avant : `obtenu False`) et `test_icones_catalogue_web.py`, VERT après ; démarrage réel des deux outils : 2e instance « port indisponible », code 1 ; même défaut encore présent dans une vingtaine d'autres `*_web.py` (`ThreadingHTTPServer` nu), non modifiés ; non commité

## Vérification
Plan fini quand A1 à A7 sont cochés avec preuve, le FTP de chaque carte du dépôt est à `OFF` dans son persist et sur
la carte, et l'essai A7 a montré `UfsFTP 0` après chaque fin de session.
