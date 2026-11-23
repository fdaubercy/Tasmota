# Build : réparation automatique des pannes

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

### Réparation automatique des pannes

Quand un `pio run` de la série échoue sur une panne connue, la page la corrige et relance l'étape (le bandeau de la ligne de l'env l'indique). Le branchement est dans
`build_serie.py::Serie._execute_env`, le moteur dans `build_reparations.py::Reparateur`.

- **Catalogue de règles** : une règle = un motif (expression régulière) cherché dans les 50 dernières lignes du journal de l'étape ratée, les étapes
  concernées (`prebuild`, `compilation`, `liens`, `buildfs`) et une liste d'actions. Règles de base : `outils_docs/schemas/reparations_build.json`
  (suivi par git, la page ne l'écrit jamais ; aujourd'hui `verrou_fichier` : un `PermissionError` sur un chemin du dépôt, pas sur un port COM).
  Règles locales : `%LOCALAPPDATA%\outils_tasmota\build\reparations.json` (règles ajoutées par l'IA, clé `supprimees`), elles l'emportent à id égal.
  Une règle locale fautive est ignorée et signalée, une base illisible n'arrête pas la série.
- **Actions permises**, liste fermée (`build_reparations.py::ACTIONS`), aucune commande libre : `attendre {secondes}`, `libere_verrou` (ferme ou attend
  le processus qui tient le fichier du message d'erreur), `vide_build` (vide `.pio/build/<env>` de l'env raté seulement).
- **Garde-fous** : 2 relances au plus par étape (env, action, cible) et par série (`build_reparations.py::RELANCES_MAX`) ; une règle ne s'applique pas deux fois à la même panne (signature = id de la règle + ligne
  reconnue) ; un arrêt demandé prime (l'env est « arrêté »). Seules les étapes `pio` de compilation, de liens et de `buildfs` sont relancées :
  jamais un `upload` ou `erase_upload` par COM, jamais un envoi OTA.
- **Processus qui tient le fichier** (`build_reparations_verrou.py`) : la liste blanche `cpptools-srv.exe`, `cpptools.exe` est fermée sans demander.
  Un `pio`, `scons` ou `python` d'une autre origine n'est jamais fermé : on attend la fin de ce build. Pour tout autre processus, la page pose la
  question Fermer / Attendre / Annuler ; sans réponse en 10 minutes, l'env échoue et la série continue. La page, le `pio` de la série et `claude`
  ne sont jamais touchés.
- **Sur la page** : un bandeau « Réparation en cours : <titre> » (puis « réussie » ou « échouée ») sur la ligne de l'env, une ligne `[réparation] …`
  dans son journal, et le panneau « Réparations » (liste des règles, origine, bouton Supprimer sur une règle locale seulement). L'état se
  reconstruit au rechargement par les événements rejoués.
- **Diagnostic par l'IA** : sur un env en échec sans règle, le bouton « Faire diagnostiquer par l'IA » lance `claude -p` en lecture seule
  (`build_reparations_ia.py::diagnostique`), sur l'abonnement déjà connecté (le fils ne reçoit jamais `ANTHROPIC_API_KEY` ni `ANTHROPIC_AUTH_TOKEN`).
  Il ne voit que la fin du journal passée par `filtre_secrets`. La proposition n'est offerte que si c'est du JSON, si le motif correspond au journal
  fourni et si les actions sont dans la liste fermée ; « Appliquer et relancer » la revalide côté serveur. La règle n'entre dans le catalogue local
  (origine `ia`) que si la relance réussit.
- **Case « Relancer après réparation par l'IA »** (décochée par défaut, mémorisée dans le navigateur) : même chose sans clic, un seul diagnostic par env
  et par lancement, seulement pour une panne `pio` sans règle du catalogue, jamais pour un envoi, refusée si un build étranger tourne.
- **Ce PC seulement** : un client distant (jeton) peut lire le panneau, rien de plus, et sa case de l'IA est ignorée.
- **Limites** : non essayé sur une vraie série de production (bancs avec un faux `pio`, un diagnostic réel en lecture seule sur un journal archivé) ;
  les échecs d'envoi OTA (HTTP, MQTT) et série (port COM tenu) ne sont pas couverts.
- Bancs : `test_build_reparations.py`, `_verrou.py`, `_ia.py`, `test_build_serie.py`, `test_build_web.py`, sonde `test_build_page_reparations_chrome.py`.
