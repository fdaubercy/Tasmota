---
chantier: navigateur-ftp-cartes
titre: Navigateur FTP des cartes (page de l'annuaire, FTP allumé à la demande)
objectif: Parcourir, télécharger, envoyer, ranger et supprimer les fichiers d'une carte par FTP depuis une page de l'annuaire, le FTP n'étant allumé que le temps de la session
statut: actif
cree: 2026-11-20
maj: 2026-11-20 (A1 hors P4)
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
- [ ] Persist du P4 (`data/garage/tasmota32p4-serveur-modbus/_persist.json`) : même changement, APRÈS le commit des modifications en cours d'une autre session dans ce fichier (choix de l'utilisateur du 2026-11-20)
- [x] Vérification : script jetable (scratchpad) qui relit chaque persist en `json.loads(..., strict=False)` et affiche `env : activation` ; attendu `OFF` partout, P4 et cuve compris ; `git diff --stat` = 1 ligne par fichier — preuve : `OFF` partout sauf le P4 (`ON`, reporté), numstat `1 1` sur les 10 fichiers (rapport `.superpowers/sdd/navigateur-ftp-cartes/task-1-report.md`)
- [x] `controleur-secrets` sur ce diff (lu), puis commit `chore(persist): serveur FTP coupe par defaut sur toutes les cartes` — preuve : contrôle OK, commit `4d56b759f` (10 fichiers, 10+/10-)
- [x] Noter dans « Améliorations restantes » la liste des cartes dont le persist est à porter sur la carte (A7) — preuve : section « Améliorations restantes » ci-dessous

## A2 — Liste des cartes éligibles (`ftp_cartes_liste.py`)

Interfaces produites :
`est_esclave_rgx(persist: Path) -> bool | None` (None = illisible) ;
`ftp_retire(texte_h: str, firmware: str) -> bool | None` (None = doute) ;
`identifiants(racine: Path, firmware: str) -> tuple[str, str]` ;
`liste(racine: Path) -> {"cartes": [{"env", "lieu", "nom", "hote", "adresse", "puce", "firmware"}], "exclues": [{"env", "raison"}]}`.
Consomme `build_envs.liste_envs`, `lieux.identites`, `lieux.puce`.

- [ ] Banc `outils_pc/test_ftp_cartes_liste.py`, mini-dépôt temporaire, cas rouges d'abord :
  - [ ] `cas_esclave` : persist avec `rangeExtender` `ON`, `id` 2, `ipMaitre` → exclue, raison contient « Range Extender »
  - [ ] `cas_persist_illisible` : JSON cassé → `est_esclave_rgx` rend None, carte exclue ; persist avec caractère de contrôle dans une chaîne → lu (strict=False)
  - [ ] `cas_sans_use_ftp` : section `#elif defined(FIRMWARE_X)` avec `#undef USE_FTP` → exclue ; section sans `#undef` → gardée ; `#undef USE_FTP` sous un `#if !defined(FIRMWARE_X)` → gardée pour l'env X, exclue pour un autre env de la section ; condition non évaluable → doute → exclue
  - [ ] `cas_puce` : env ESP8266 → exclue
  - [ ] `cas_adresse` : IP du `.h` → `adresse` = IP ; IP absente ou 0.0.0.0 → `adresse` = `<Hostname>.local`
  - [ ] `cas_identifiants` : `USER_FTP`/`PW_FTP` de la partie commune, remplacés par ceux de la section de l'env s'ils y sont redéfinis ; `json.dumps(liste(...))` ne contient pas le mot de passe
  - [ ] `cas_depot_reel` : sur le vrai dépôt, la cuve (`tasmota32s3-capteurs-cuve-modbus`), le rideau et le portail sont exclus ; `tasmota32s3-bureau-serveur-debits-pac` est exclu (esclave de l'écran) ; le P4, l'écran des débits et la cave S3 sont présents ; les 3 ESP32 sans PSRAM sont exclus
- [ ] Lancer le banc : rouge (module absent)
- [ ] Écrire `ftp_cartes_liste.py` (lecture des sections du `.h` sur le modèle de `autoexec_gardes.py` / `build/verifie_lib_ignore.py`, sans modifier `build_envs.py`)
- [ ] Banc vert, sortie collée en preuve ; témoin : retirer le test d'esclave fait rougir `cas_depot_reel`
- [ ] `controleur-secrets` lu, commit `feat(ftp): liste des cartes joignables par FTP`

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

- [ ] Faux serveur `outils_pc/faux_ftp_carte.py` (pour les bancs) : `socketserver`, dossier temporaire, un seul client, PASV seul sur un port choisi, commandes `USER PASS PWD CWD TYPE PASV MLSD LIST RETR STOR DELE MKD RMD RNFR RNTO NOOP QUIT`, option `coupe_apres(n)` pour simuler une carte perdue ; faux `commande(ip, cmnd, delai)` qui journalise les `UfsFTP n`
- [ ] Banc `outils_pc/test_ftp_cartes_session.py`, cas rouges d'abord :
  - [ ] `cas_ouvre` : `ouvre(carte, "sd")` envoie `UfsFTP 1`, `"flash"` envoie `UfsFTP 2` ; `etat()["etat"] == "actif"`
  - [ ] `cas_sd_inconnue` : `Ufs` sans réponse → `etat()["sd"] is None` ; `ouvre(..., "sd")` lève `RefusFtp` (jamais la flash sous l'étiquette SD)
  - [ ] `cas_ferme_toujours` : `ferme()` envoie `UfsFTP 0` même si `quit()` FTP lève ; idem après `ouvre` d'une autre carte (l'ancienne reçoit `UfsFTP 0` avant que la nouvelle reçoive `UfsFTP 1`)
  - [ ] `cas_inactivite` : horloge avancée de 899 s → `tic()` ne ferme pas ; 901 s → `UfsFTP 0`, raison « inactivite »
  - [ ] `cas_reconnexion` : client FTP coupé par la carte (timeout 5 min simulé) → `liste()` rouvre la session une fois sans `UfsFTP` supplémentaire et réussit
  - [ ] `cas_carte_perdue` : `coupe_apres(1)` + reconnexion impossible → `RefusFtp` lisible, `etat()["etat"] == "erreur"`
  - [ ] `cas_chemins` : `valide_chemin` refuse `..`, `\x00`, `\n`, plus de 255 caractères ; accepte `/histo/mesures-2026-11.bin`
  - [ ] `cas_protege` : `supprime("/autoexec.be", 1)` lève `RefusFtp` ; `supprime("/autoexec.be", 2)` supprime ; idem `/sd` et `/json` ; `/histo/x.bin` avec 1 confirmation supprime
  - [ ] `cas_noms_speciaux` : `mesures 2026#é.bin` listé, lu, supprimé
  - [ ] `cas_zip` : `zip(["/histo"])` contient les fichiers du dossier avec leurs chemins relatifs et leurs octets exacts
  - [ ] `cas_place` : `Ufs` donne une place libre inférieure à la taille du flux → `RefusFtp` avant tout `STOR` ; place inconnue → envoi tenté
  - [ ] `cas_ecrasement` : `envoie(..., ecraser=False)` sur un nom existant lève `RefusFtp` ; `ecraser=True` remplace
  - [ ] `cas_deplace` : `deplace("/histo/a.bin", "/archives/a.bin")` (dossier existant) déplace
  - [ ] `cas_mot_de_passe` : aucune valeur rendue par `etat()` ni message de `RefusFtp` ne contient le mot de passe
- [ ] Lancer le banc : rouge
- [ ] Écrire `ftp_cartes_session.py` : un `threading.Lock` autour de toute opération FTP ; `mlsd()` avec repli `LIST` ; attente du port 21 par `socket.create_connection` répétée jusqu'à 10 s ; `ftplib` garde l'hôte du contrôle pour les données (adresse PASV ignorée, défaut de `ftplib`)
- [ ] Banc vert, sortie collée en preuve ; témoin : supprimer l'envoi de `UfsFTP 0` dans `ferme` fait rougir `cas_ferme_toujours`
- [ ] `relecteur-outils-python` sur les deux fichiers, remarques traitées ; `controleur-secrets` lu, commit `feat(ftp): session FTP allumee a la demande`

## A4 — Serveur web et routes (`ftp_cartes_web.py`)

Interfaces produites (consommées par la page, A5) :
`GET /` (page), `GET /cartes` (`ftp_cartes_liste.liste`), `GET /etat`, `GET /liste?chemin=`, `GET /telecharge?chemin=` (fichier brut, `Content-Disposition: attachment`) ;
`POST /ouvre {env, support}`, `POST /ferme {}` (accepté sans en-tête `X-...`, origine vérifiée), `POST /zip {chemins}` (zip en réponse),
`POST /envoie?dossier=&nom=&ecraser=0|1` (corps brut, `MAX_ENVOI = 16 * 1024 * 1024`), `POST /supprime {chemin, confirmations}`, `POST /dossier {chemin}`, `POST /deplace {source, cible}`.
`fabrique_gestionnaire(acces, racine, session)` ; `principal()` avec `--http 7450`, options `acces_web`, `atexit` qui appelle `session.ferme("arret de l'outil")`, fil d'horloge qui appelle `session.tic()` toutes les 10 s.

- [ ] Banc `outils_pc/test_ftp_cartes_web.py` (serveur réel sur 127.0.0.1, port libre, faux serveur de carte d'A3, mini-dépôt), cas rouges d'abord :
  - [ ] `cas_routes` : chaque route ci-dessus répond (200 ou 409 attendu), verbe inconnu → 405
  - [ ] `cas_ecritures_ce_pc` : `POST /ouvre`, `/envoie`, `/supprime`, `/dossier`, `/deplace` depuis une adresse non locale (handler avec `client_address` simulé) → 403 ; `GET /liste` et `/telecharge` depuis cette adresse avec jeton → 200
  - [ ] `cas_beacon` : `POST /ferme` sans en-tête `X-...` et origine locale → 200 et `UfsFTP 0` ; `POST /supprime` sans en-tête → refusé
  - [ ] `cas_deux_onglets` : deux `GET /etat` successifs voient la même session ; un second `POST /ouvre` sur la même carte ne crée pas de seconde connexion FTP
  - [ ] `cas_envoi_trop_gros` : `Content-Length` > `MAX_ENVOI` → 413, aucun `STOR` reçu par le faux serveur
  - [ ] `cas_secret` : aucune réponse (`/cartes`, `/etat`, erreurs) ne contient le mot de passe du mini-dépôt
  - [ ] `cas_host_hostile` : `Host: evil.example` → 403 (`hote_autorise`)
- [ ] Lancer le banc : rouge
- [ ] Écrire `ftp_cartes_web.py` sur le modèle de `icones_catalogue_web.py` (CSP, en-têtes) et des POST de `menage_web.py` (taille du corps bornée, `est_local`)
- [ ] Banc vert, sortie collée en preuve ; témoin : retirer le contrôle `est_local` de `/supprime` fait rougir `cas_ecritures_ce_pc`
- [ ] `relecteur-outils-python` lu ; `controleur-secrets` lu, commit `feat(ftp): serveur web du navigateur FTP`

## A5 — La page (interface A) et sa sonde Chrome (`ftp_cartes_page.py`)
- [ ] Écrire `PAGE` d'après la maquette A et la spec §6 : listes Lieu et Carte (`remplitParLieu` de `lieux.JS`, `?lieu=`), pastille d'état, bascule Flash / SD (grisée si `sd` vaut False, « SD inconnue » si None), bouton « Historique et énergie » (SD puis `/histo`), « Déconnecter », arborescence chargée dossier par dossier, tableau à cases, barre d'actions ; confirmations (une, ou deux pour les fichiers protégés) ; `pagehide` → `navigator.sendBeacon("/ferme")` ; mode sombre ; aucun CDN
- [ ] Sonde `outils_pc/test_ftp_cartes_page_chrome.py` (hermétique : serveur de l'outil + faux serveur de carte, Chrome headless au profil `sonde_ftp_cartes`) : choix d'une carte → pastille « actif » ; liste de `/histo` ; nom spécial affiché ; suppression d'un fichier protégé : 1 confirmation → toujours présent, 2 → supprimé ; fermeture de l'onglet → le faux serveur a reçu `UfsFTP 0` ; aucun message d'erreur de la console JS
- [ ] Sonde verte, sortie collée en preuve ; Chrome `sonde_*` orphelins vérifiés arrêtés 15 s après
- [ ] `relecteur-pages-web` lu, remarques traitées ; `controleur-secrets` lu, commit `feat(ftp): page du navigateur FTP`

## A6 — Intégration : annuaire, tâche VS Code, cible Custom, documentation
- [ ] Entrée `Outil("ftp_cartes", ...)` dans `annuaire_registre.py`, groupe `GROUPES[3]` (« Configuration des cartes »), `_port("http", 7450)` ; `test_annuaire.py` vert
- [ ] Tâche VS Code « Outil : navigateur FTP des cartes (http://127.0.0.1:7450) » dans `.vscode/tasks.json` (fichier suivi ET présent en amont : demander l'accord avant, comme pour `.vscode/settings.json`)
- [ ] Vérifier qu'aucun build ne tourne ; `build/cible_ftp_cartes.py` copié de `cible_icones_catalogue.py` (`NOM_CIBLE = "ftp_cartes"`, `PORT_DEFAUT = "7450"`) ; import et `enregistre(env)` dans `build/pre_utilitaires_platformio.py`, `NOM_CIBLE` ajouté à la liste de sortie anticipée ; `'ftp_cartes'` ajouté à `CIBLES_OUTILS` de `.claude/hooks/garde_build.py`
- [ ] Bancs `build/test_cible_ftp_cartes.py` (copie adaptée de `test_cible_icones_catalogue.py`) et `build/test_garde_build.py` verts
- [ ] Section « Navigateur FTP des cartes (page web) » dans `outils_docs/README.md` (usage, FTP à la demande, persist à `OFF`, esclaves exclus, fichiers protégés) ; entrée dans la carte des documents de `CLAUDE.md` ; `verifie_references_docs.py` à 0 défaut ; `relecteur-docs` lu
- [ ] `controleur-secrets` lu, commit `feat(ftp): navigateur FTP dans l'annuaire, cible et documentation`

## A7 — Essai sur les cartes réelles
- [ ] Porter le persist à `OFF` sur le P4 et sur une S3 (onglet « Fichiers » de la page Build), puis vérifier `UfsFTP` → 0 après un redémarrage
- [ ] P4 : ouvrir depuis la page, relever la racine vue en SD et en flash, la réponse de `Ufs` et la présence des dates `MLSD` ; reporter ces constats dans la spec §10
- [ ] P4 : télécharger `/histo` en zip et comparer la taille aux fichiers listés ; envoyer puis supprimer un fichier témoin ; créer, déplacer, supprimer un dossier témoin
- [ ] Après chacun des 5 événements de fin de session (Déconnecter, autre carte, fermeture d'onglet, 15 min, arrêt de l'outil) : `UfsFTP` lu sur la carte = 0
- [ ] Même parcours court sur une S3 (sans SD si possible : bascule SD grisée ou « SD inconnue »)
- [ ] Porter le persist à `OFF` sur les autres cartes listées en A1 ; cocher chacune dans « Améliorations restantes »

## Améliorations restantes
- [ ] [projet] Porter le persist à `OFF` sur chaque carte (onglet « Fichiers » de la page Build), A7 : bureau ecran-debits-pac, bureau serveur-debits-pac, cave s3-ecran, cave s3-serveur-rly, étage 2 grenier, RDC grenier, garage P4 (après son commit), cuve, portail-jardin, rideau, garage s3-serveur-modbus
- [ ] [projet] Page Build : `build_envs.adresse_par_maitre` lit les persist en strict, l'adresse de la cuve par le maître n'est pas calculée (IP à saisir à la main)

## Vérification
Plan fini quand A1 à A7 sont cochés avec preuve, le FTP de chaque carte du dépôt est à `OFF` dans son persist et sur
la carte, et l'essai A7 a montré `UfsFTP 0` après chaque fin de session.
