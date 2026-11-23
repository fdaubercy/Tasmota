# Navigateur FTP des cartes

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Navigateur FTP des cartes (page web)

Page http://127.0.0.1:7450 pour parcourir les fichiers d'une carte par FTP : récupérer les logs et l'historique de la SD, ajouter ou
supprimer des fichiers et des dossiers sur le FS, ranger. Cet outil écrit sur les cartes (envoi, création de dossier, déplacement,
suppression), depuis ce PC seulement ; il n'écrit rien dans le dépôt. Spec `docs/superpowers/specs/2026-11-20-navigateur-ftp-cartes-design.md`,
plan `tasks/plans/navigateur-ftp-cartes.md`.

### Lancer la page

- Tuile « Navigateur FTP des cartes » de l'annuaire (http://127.0.0.1:7600), groupe Configuration des cartes.
- Tâche VS Code « Outil : navigateur FTP des cartes (http://127.0.0.1:7450) ».
- Cible Custom détachée « Navigateur FTP des cartes (page web) » (`build/cible_ftp_cartes.py`, port par `custom_ftp_cartes_http`,
  `pio run -e <env> -t ftp_cartes`). Comme toute cible, jamais pendant un build : lancer alors la tâche VS Code ou le script.
- Ligne de commande : `python outils_docs/scripts_python/outils_pc/ftp_cartes_web.py [--http 7450] [--local] [--sans-navigateur]`.

Depuis un autre appareil, lien à jeton affiché dans la console (`acces_web.py`), mais l'allumage du FTP et tous les gestes qui écrivent
sont refusés (403) : ils ne passent que depuis ce PC.

### Ce que montre la page

Deux volets. À gauche, les cartes du parc, classées par lieu (`outils_pc/ftp_cartes_liste.py::liste`) : une carte est proposée si son env est
de la famille « cartes », de puce ESP32, ESP32-S3 ou ESP32-P4, si `USE_FTP` n'est pas retiré de sa section de `user_config_override.h`, et si elle
n'est pas esclave du Range Extender (derrière le NAPT du maître, son FTP n'est pas joignable). Au moindre doute la carte est exclue. La liste
(`GET /cartes`) est mise en cache, invalidée par `(chemin, mtime_ns, taille)` des ini, de `user_config_override.h` et des `_persist.json` lus, et
préchauffée au démarrage de l'outil : le calcul prend environ 1 s, une ouverture trop précoce n'attend que la fin de celui qui est en cours, les suivantes répondent en une dizaine de
millisecondes. Le banc vérifie aussi que `GENERIQUES` (les firmwares sans effet sur le FTP) couvre tous les `FIRMWARE_*` des envs cartes. À droite,
les fichiers du support choisi, Flash ou SD. On peut télécharger un fichier ou un zip de plusieurs, envoyer un fichier (16 Mo au plus),
créer un dossier, déplacer, supprimer. Un envoi qui écraserait un fichier existant n'a lieu que sur demande, et un déplacement vers un nom
déjà pris est refusé (409), jamais écrasé ; « déjà pris » se juge comme la SD en FAT, sans tenir compte de la casse ni des points et espaces finaux
(`AUTOEXEC.BE` est `autoexec.be`, `outils_pc/ftp_cartes_chemins.py::cle_fat`). Un dossier ne se déplace pas dans lui-même ni sous lui-même (refus
avant toute commande FTP ; un renommage qui ne change que la casse est refusé de même). Les chemins refusent `..`, `.`, les caractères de contrôle et
`\`. La page joint à chaque suppression et à chaque déplacement le type qu'elle a vu (`fichier` ou `dossier`) : si la carte a changé entre-temps (un
fichier devenu dossier plein), le serveur répond 409 « le type de l'élément a changé » sans rien supprimer. Tous les gestes de la page portent la paire carte et support (`env`, `support`), y compris
`/zip` et `/telecharge` : si un autre onglet a changé de carte ou de support entre-temps, le serveur répond 409 « la session a changé » et ne
touche à rien, la page le traite comme les autres 409. Les lectures qui ont un effet (`GET /etat?onglet=`, qui enregistre un onglet, `/liste`,
qui repousse les 15 min d'inactivité, `/telecharge`) refusent (403) une requête venue d'une autre origine : en-tête `Sec-Fetch-Site` autre que
`same-origin` ou `none` (un autre outil sur 127.0.0.1 est `same-site` et refusé aussi), ou `Origin` étranger ; sans ces en-têtes (navigation
directe, script), elles sont admises.

Un fichier protégé (`autoexec.be`, `autoexec.bat`, `_persist.json`, `.bec`, `.drvset*`, et les dossiers `/sd` et `/json`, majuscules,
points et espaces finaux compris car la SD est en FAT ; les noms courts 8.3 comme `AUTOEX~1.BE` ne sont pas reconnus) demande deux confirmations
pour être supprimé, deux pour être déplacé et deux pour être écrasé par un envoi, les autres une ou aucune (`outils_pc/ftp_cartes_chemins.py::protege`).
Pour l'écrasement, la page demande « l'écraser ? », envoie, et le serveur répond 409 « seconde confirmation » avant toute écriture sur la carte ; la
page ouvre alors la seconde boîte puis renvoie le fichier avec `confirmations=2` (le corps passe deux fois du navigateur à l'outil, une seule fois
vers la carte). Il en va de même d'un dossier qui en contient un, supprimé ou déplacé : le serveur le cherche (parcours
borné, la limite atteinte comptant comme « oui »), répond 409 et la page demande la seconde confirmation. Les identifiants FTP sont lus côté serveur dans
`user_config_override.h` et ne figurent dans aucune réponse ni aucun message.

### Le FTP n'est allumé que le temps du besoin

Choisir une carte envoie `UfsFTP` (SD si elle est montée, sinon Flash ; la SD est exigée si on la demande) ; l'outil éteint ensuite le FTP
(`UfsFTP 0`) à la fin de la session, par cinq événements : « Déconnecter » (ferme toujours, même avec d'autres onglets ouverts), le choix d'une
autre carte, la fermeture du DERNIER onglet, 15 min sans action, et l'arrêt propre de l'outil (`atexit`). Chaque onglet se présente par un
identifiant de 16 à 32 caractères hexadécimaux, tiré à l'ouverture de la page et envoyé à chaque sondage (`GET /etat?onglet=`, toutes les 5 s) et
à l'ouverture (`POST /ouvre`) ; en fermant, la page poste `/ferme` avec cet identifiant (`sendBeacon`) et le serveur n'éteint le FTP que s'il ne
reste aucun autre onglet (`ftp_cartes_onglets.py`). Un onglet qui disparaît sans prévenir (plantage, veille) est oublié après 90 s sans sondage,
et le FTP s'éteint alors si c'était le dernier (le délai de 90 s, et non 15 s, tient au ralentissement des minuteries d'un onglet caché par Chrome).
Une session ouverte sans identifiant (client ancien, `curl`) n'est jamais « perdue » : seule l'inactivité la ferme. Un changement de carte garde les
autres onglets connus : fermer l'onglet qui a changé de carte n'éteint pas le FTP sous les autres. Si la carte ne confirme pas `UfsFTP 0`, l'outil ne
l'oublie pas : plus aucun geste n'est accepté, la pastille passe en erreur et dit que l'extinction n'est pas confirmée, `UfsFTP 0` est renvoyé
à chaque tour d'horloge (10 s), cinq essais en tout (`ftp_cartes_session.py::Session.tic`), puis seul « Déconnecter » le renvoie ; tant que
l'extinction n'est pas confirmée, l'annuaire refuse d'arrêter l'outil, et ouvrir une autre carte est refusé (on ne laisse pas deux cartes
allumées). Rouvrir la même carte efface l'attente. Le dépôt porte aussi un filet côté carte : `serveur.serveurFTP.activation` vaut `OFF`
dans les 16 persist du dépôt qui portent le bloc (le dossier `*-sauvegarde` n'en a pas), et `data/fs/globalFonctions.be::regleFTP` envoie `UFSFTP 0` à chaque
connexion au réseau quand l'activation n'est pas `ON`. Les
cartes réelles ne reçoivent ce réglage qu'au prochain téléversement de leur FS.

### Limites connues

- **Arrêt de l'outil.** L'outil est lancé hors du Job Object de l'annuaire (`dans_job=False` dans `annuaire_registre.py`) : la mort de l'annuaire ou de
  VS Code ne le tue plus, et son fil d'horloge continue d'éteindre le FTP (90 s sans onglet, 15 min sans action). Le bouton « Arrêter » de l'annuaire
  est REFUSÉ tant qu'une session est ouverte (l'outil répond `{"en_cours": true}` sur `GET /execution`) : cliquer d'abord sur « Déconnecter ». Hors
  session, l'arrêt (`taskkill /T /F`, `annuaire_lanceur.py::_tue_arbre`) ne laisse rien d'allumé. Un arrêt brutal par un autre moyen (gestionnaire
  de tâches, arrêt d'une tâche VS Code) ne laisse pas exécuter `atexit` ni `finally` : le FTP de la carte reste alors allumé. Seul Ctrl+C dans un
  terminal passe par la fin propre. Après un arrêt brutal, rouvrir la carte dans la page puis « Déconnecter » (ou la commande `UfsFTP 0`), ou
  redémarrer la carte une fois son persist à `OFF`. Un outil laissé tourner après la fermeture de VS Code reste visible dans l'annuaire (« En cours »)
  et s'arrête à la main. L'arrêt par une tâche VS Code ou par la fin d'une cible n'a pas été vérifié.
- Le serveur FTP de la carte n'accepte qu'un client à la fois : l'outil sérialise ses opérations, mais un autre client FTP ouvert en même temps
  (FileZilla) bloque ou est bloqué.
- La session est unique pour tout l'outil : un second onglet qui choisit une autre carte ou un autre support remplace celle du premier, dont la
  page affiche « autre onglet » au sondage suivant.
- Rien n'a encore été essayé sur une vraie carte (plan, étape A7) : les bancs parlent à un faux serveur FTP de carte.

Bancs, dans `outils_docs/scripts_python/outils_pc/` avec le Python du penv PlatformIO : `test_ftp_cartes_liste.py`, `test_ftp_cartes_session.py`
(lent, plus de 35 s), `test_ftp_cartes_session_garde.py` (gardes : déplacement, dossiers protégés, exceptions), `test_ftp_cartes_session_relecture.py` (extinction non
confirmée, onglets au changement de carte, `\`, noms FAT, casse, dossier dans lui-même, type attendu, écrasement d'un fichier protégé),
`test_ftp_cartes_session_p4.py` (carte dont le serveur FTP ignore le chemin de `MLSD`, constaté sur le P4 : liste, zip, suppression, envoi, déplacement d'un sous-dossier), `test_ftp_cartes_onglets.py` (registre d'onglets, horloge simulée), `test_ftp_cartes_web.py`, `test_ftp_cartes_web_relecture.py` (anti-CSRF des GET,
`type`, `confirmations` de `/envoie`), la sonde Chrome `test_ftp_cartes_page_chrome.py` (qui appelle
`test_ftp_cartes_page_chrome_onglets.py` et `test_ftp_cartes_page_chrome_corrections.py`) et le faux serveur `faux_ftp_carte.py` ; pour la
cible Custom, `build/test_cible_ftp_cartes.py`. Pour l'annuaire, le refus d'arrêt en session est couvert par `test_annuaire.py` et
`test_annuaire_securite.py`.

Les sondes Chrome dont la page est habillée (barre « Annuaire » de `acces_web.py`) ne doivent pas lire les vraies fiches de présence ni interroger la
vraie page Build : `outils_pc/sonde_hermetique.py::neutralise_barre()` coupe la barre commune le temps de la sonde (banc `test_sonde_hermetique.py`).
Sept sondes l'appellent : `test_acces_repli_chrome.py`, `test_atelier_visuels_page_chrome.py`, `test_cartes_simulees_page_chrome.py`,
`test_icones_catalogue_page_chrome.py`, `test_sondes_page_chrome.py`, `test_plan_maison_page_chrome.py` et `test_taches_planifiees_page_chrome.py`.
