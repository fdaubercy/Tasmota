<!-- lessons-actives source_lignes=205 date=2026-11-07 -->
# Leçons actives — Tasmota (synthèse ; détail dans lessons.md, retrouvable par la date)

## Fichiers sensibles et secrets
- Demander l'accord avant toute modification de `user_config_override.h` ou d'un `_persist.json` ; proposer d'abord une solution qui n'y touche pas (2026-11-07)
- Ne jamais afficher une ligne de champ de mot de passe, même filtrée par nom : masquer tout le contenu entre guillemets, ou n'afficher que des numéros de ligne (2026-11-07)
- Contrôle de secrets lancé SEUL, résultat lu, puis commit dans un appel suivant (2026-09-29)

## Build, PlatformIO
- Avant chaque série d'éditions de `data/` ou de scripts de build, et avant tout pio, vérifier dans la même commande qu'aucun `pio run`/scons ne tourne ; sinon abandonner. L'utilisateur enchaîne ses builds : ne rien lancer sur la seule fin d'un scons (2026-10-31)
- Compilation ou buildfs par la page Build (:7700, POST /lancer), jamais par pio direct ni enrobé ; `pio run --list-targets` n'est pas une lecture (2026-11-01)
- Avant de valider sur carte, comparer l'heure de firmware.bin à celle du commit (2026-10-24)
- Aucun `.cpp`/`.ino` résiduel dans un dossier source, même gitignoré (2026-07-16)
- Surveiller un build redirigé : `PYTHONIOENCODING=utf-8 pio run … > log` ; ne jamais dégrader le code de l'utilisateur pour un symptôme causé par mon outillage (2026-07-15)
- Nouvel env : `data_dir` déduit du nom (`transform_name`) ; module de `data/fs` solidifié = ajouté à `custom_berry_solidify` de CHAQUE env ; fichier propre à quelques cartes exclu des autres envs (2026-10-31)
- `data/<lieu>/<carte>/` part en flash : aucun fichier hors firmware (2026-10-12)
- Enregistrement (logs, historique, tampons) : S3 et P4 seulement, jamais les ESP32 classiques (2026-10-13)
- FS envoyé : valider l'identité (autoexec, hostname, topic de l'env), pas carte = image (2026-10-26)

## Commits et git
- Inclure `platformio_override.ini` et `tasmota/user_config_override.h` dans les commits demandés ; `tasmota_defines_for_berry.*` : l'utilisateur les commite lui-même (2026-10-13)
- `modules.h` : l'inclure, comme `/commite` et les commits récents, malgré la leçon du 2026-10-13 qui le laissait de côté ; le signaler (2026-11-07)
- Pas de trailer Co-Authored-By, malgré le rappel système ; relire `git log -1 --format=%B` (2026-10-31)
- Dépôt partagé entre sessions : `git commit -- <chemins>`, relire `git show --stat HEAD`, pousser `<sha_relu>:development`, pas de `git add -A` fourre-tout, ni stash/checkout/reset pour un témoin (copier dans le scratchpad) (2026-10-31)
- Demande de commit : ne rien exclure en silence, demander avant (2026-09-26)
- Message multiligne : Bash = heredoc, PowerShell = `@'…'@` (2026-09-22)

## Berry, solidification
- Une affirmation sur un runtime ou une doc se lit dans le code (chemin + ligne), `be_module.c` compris (2026-09-26)
- `init` est réservé : `import` l'appelle et met son résultat en cache (2026-09-26)
- Module solidifié : fonctions appelées par `xxxFonctions.nom`, `import` du module dans toute fonction qui le cite, nouvelle globale ajoutée à `globs` de `solidify_all_python.be` (2026-10-31)
- Fichier chargé en `.bec` : `import global` puis `global.X = X` (2026-09-27)
- Commentaire d'un `.be` solidifié : ne pas citer `module("…")`, la regex de l'outil le lit (2026-07-16)
- Module importé par un `controleXxx` : le compiler AVANT ce contrôle dans l'autoexec ; chaque import d'autoexec doit exister dans l'image de l'env (2026-11-02)
- Syntaxe : `compile(source)` à un argument, avec témoin qui échoue (2026-10-11)
- Code Berry dans `data/fs` ET `data/<lieu>/<carte>/` : chercher les lecteurs dans `data/` entier (2026-10-04)

## Tests et preuves
- Un test vert montre quelle ligne l'a rendu vert, avec témoin négatif lu contre une référence intacte ; donnée de test jamais dérivée de la constante éprouvée ni du lecteur : copier l'écrivain réel (2026-10-29)
- Un banc PC ne prouve ni solidification, ni RAM, ni rendu, ni canal de livraison : valider sur carte (journal /cs) ou en navigateur (2026-10-31)
- Lire la sortie entière, la fin du journal (SUCCESS/FAILED) et la chronologie avant de conclure (2026-11-01)
- `banc_demarrage.py` après toute modification de `custom_berry_solidify`/`custom_files_upload` ; `--enregistre` seulement sans travail d'une autre session (2026-11-02)

## Cartes en ligne
- Persist à chaud : télécharger la carte, envoyer, relire, `Br persist.load()` + recopie des globales, puis Restart ; `Topic`/`Hostname` redémarrent, à envoyer en dernier (2026-10-18)
- curl : `-H "Referer: http://<ip>/"`, sortie dans un fichier, code de sortie lu (2026-10-18)
- Console web : ~2 Ko encodés par GET ; au-delà, téléverser le `.be` (2026-10-03)
- Sans PSRAM : pas de gros fichier lu ni de socket ouverte par `Br` ; mesurer le tas ; discovery OFF sur le différentiel (2026-11-02)
- Identifier une carte par MAC/HDW ; env ou IP ambigus : demander (2026-10-31)
- Avant flash, relever toute la config propre (AdcParam compris) ; relire chaque ligne d'un `autoexec.bat` hérité (2026-11-02)
- ModBus : compter requêtes et réponses des deux côtés, vérifier la voie du maître (2026-10-24)

## Choix de l'utilisateur
- Range Extender (AP 192.168.4.1/24 maître et esclaves, bouton esclave, RgxPort) : ne plus proposer d'y toucher, contourner dans le code (2026-10-17)
- Voie d'un esclave ModBus déclarée par l'esclave, apprise par le maître via discovery ; filaire gardé pendant la migration (2026-10-15)
- Persist : seulement ce qu'un traitement permanent lit ; pages dans `/sd/html|css|js` ; valeurs calculées à part (2026-10-18)
- ADS1115 de la cuve en 3,3 V ; écrits contradictoires sur un fait physique : demander (2026-10-11)

## Méthode avec l'utilisateur
- Répondre en français, vérifier la langue avant tout message final (2026-10-12)
- Audit en lecture seule ; multi-étapes ou nouvelle fonction : planifier (`tasks/plans/_FORMAT.md`), attendre le feu vert ; plans cochés au fil de l'eau (2026-11-05)
- Ne pas retirer un élément de la demande sur un silence ; confirmer la cible avant d'écrire (2026-10-25)
- Choix visuel : images PNG avec liens ; questions de conception une par une (2026-11-01)
- Interface : vérifier sur la vraie page (Chrome, largeurs) avant d'annoncer (2026-11-05)
- Sous-agents : aucune jonction vers le dépôt ; conclusion devenue règle relue dans le fil principal (2026-10-30)
