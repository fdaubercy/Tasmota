# Assistant persist

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Assistant persist (page web)

Une page qui pose des questions et en tire le `_persist.json` d'une **nouvelle carte** (elle sait aussi **modifier ou
supprimer un env existant**, voir plus bas), avec l'`autoexec.be`, la
section du cenv et la section `#elif` de `tasmota/user_config_override.h` qui vont avec. Les questions et leurs règles
viennent d'un **modèle** (`outils_docs/schemas/modele_persist.json`) qui se met à jour à partir des persists du dépôt.
Le moteur d'écriture est celui de « Fichiers Berry par env » (créer un env), sans changement de comportement.
Conception : [spec](../../docs/superpowers/specs/2026-10-27-assistant-persist-design.md) ; plan :
`tasks/plans/assistant-persist.md`.

Les listes de cartes du parc (env à modifier, carte de l'onglet autoexec.bat) sont groupées par lieu de la maison
(`outils_pc/lieux.py`).

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Configuration des cartes » : « Assistant persist ». Rien n'est écrit
  avant « Créer l'env » : on peut l'arrêter à tout moment.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : assistant persist (http://127.0.0.1:7900) ».
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/assistant_persist_web.py` (`--http 7900`,
  `--local`, `--sans-navigateur`).
- **Cible PlatformIO** « Assistant persist (page web) » dans *Project Tasks > <env> > Custom* : démarre la page
  détachée (console dans `%LOCALAPPDATA%\outils_tasmota\consoles\assistant_persist.log`) puis rend la main.
  Comme toute cible, **jamais pendant un build**.

Port **7900**. Depuis un autre appareil : lien à jeton affiché dans la console, comme les autres outils
(`acces_web.py`) ; depuis ce PC, aucun jeton.

### Les étapes de la page

1. **Questions** : identité de la carte (puce, lieu, nom, topic, IP), réseau, fonctions à activer. Sous chaque case de
   fonction, une ligne grise rappelle, **en lecture seule**, son coût en Ko (lu dans les blocs `TAILLE DU BINOME`, solidifié
   et `.bec`), ses `#define` et ses `lib_ignore` (bibliothèques ignorées quand le bloc est absent) ; rien de cela n'est
   écrit ni généré, la sortie de l'assistant ne change pas. Une fonction sans bloc de taille n'affiche que ce qu'elle a.
2. **Entrées et sorties du bloc métier** : un éditeur par groupe (boutons, interrupteurs, relais, capteurs, compteurs,
   thermomètres, analogiques, `pinsTechniques`, `debitmetres`). Les broches proposées sont celles de la puce d'après `data/fs/configGlobal.be`.
   `pinsTechniques` porte les broches du gabarit qui ne sont ni relais ni capteurs (UART de la BL0942 et 2e bobine du
   relais bistable du différentiel) ; `debitmetres` porte les `FlowRateMeter` et leur facteur `k` (carte Serveur Débits de
   PAC) ; vide, un de ces deux groupes n'est pas écrit. Un élément relu garde sa clé (`analogique5`,
   `rxBL0942`) ; un élément ajouté prend le premier numéro libre.
   La page **refuse** une broche en double, une broche déjà prise par ModBus, I2C ou LEDs, ou hors plage.
   Un élément **OFF** n'est pas contrôlé : il n'occupe pas sa broche.
3. **Aperçu** du `_persist.json` en direct, mots de passe masqués (`***`).
4. **Diff** de chaque fichier touché (nouveau dossier `data/<lieu>/<puce>-<nom>`, cenv, `.h`).
5. **Création** en **une transaction** : si un fichier ne peut pas être écrit, tout est défait. Sauvegardes
   horodatées dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`, gardées 30 jours. Refusée pendant un
   build, et si la saisie a changé depuis « Voir le diff » (le bouton se grise, le serveur répond 409).

Après la création, la page affiche un **résumé à copier** et deux liens : la page build (7700, env coché) et
« Fichiers Berry par env » (7800, `?env=<nom>`) pour choisir ce qui est sur le FS, exclu ou solidifié.

### Les mots de passe

**Ils ne sont jamais envoyés à la page.** Le serveur les recopie : mots de passe Wi-Fi des familles « maison » prises
dans les persists du parc, et mot de passe commun mqtt / point d'accès / FTP. L'aperçu, le diff, le résumé et les
erreurs montrent `***` ou rien. Si deux persists donnent deux mots de passe pour le même nom de réseau, ou si le
réseau est inconnu du parc, la création est refusée en nommant le réseau (sans valeur). Le modèle n'en contient
aucun : ses valeurs sont `@secret:<famille>`.

### Le modèle `modele_persist.json`

- **À l'ouverture**, les clés **nouvelles** du parc (présentes dans un persist du dépôt, absentes du modèle) sont
  **fusionnées automatiquement** ; un bandeau orange « à compléter » liste celles qu'il faut documenter (texte de
  question, valeur par défaut).
- **« Mettre à jour le modèle »** : le bouton affiche le diff de la mise à jour proposée, puis la valide.
- **« Relue »** (une par clé du bandeau « à compléter », avec son chemin et sa valeur par défaut, `***` si secret) : retire cette seule clé de `a_completer` après diff et validation ; le modèle n'est écrit que si l'empreinte du diff est encore la bonne (409 sinon).
- Chaque écriture du modèle est précédée d'une **sauvegarde horodatée**, au même endroit que les autres.
- Modèle **cassé à la main** (JSON invalide) : la page s'ouvre avec un bandeau rouge qui donne l'erreur et sa ligne ;
  ni fusion ni réécriture, et la création est refusée.
- Persist du dépôt illisible : ignoré avec un avertissement.

### Modifier ou supprimer un env existant

Conception : spec §10 ; plan `tasks/plans/assistant-persist-modification.md`. Code : `assistant_persist_texte.py`
(édition du texte sans le reformater), `assistant_persist_delta.py` (écart A -> B), `assistant_persist_modification.py`
(application aux fichiers), `assistant_persist_page_js_env.py` (page).

**Charger.** La liste des cartes du parc (`cartes` dans `/parc`) permet de choisir un env : `GET /env` relit son
`_persist.json` (plus la base et le define tirés du cenv) et remplit les questions avec ces réponses. L'autoexec et
les sections du cenv et du `.h` ne sont lus qu'à la préparation de la modification.

**Modifier.** L'assistant ne régénère jamais une carte. Il génère **A** (les réponses relues) et **B** (les réponses de
la page), puis applique au vrai fichier le **seul écart A -> B** ; tout le reste (retouches à la main, ordre,
commentaires) ne bouge pas d'un octet. Écart vide : rien n'est écrit et « Modifier » est grisé. Même cheminement que
la création : « Voir le diff » (`/modification/prepare`), puis « Modifier » (`/modification`) en une transaction.

- **Persist** : l'écart est calculé par chemin JSON et appliqué dans le texte. Un `remplace` garde la forme de la valeur
  (compacte sur une ligne ou indentée) ; un ajout se pose après sa clé soeur ; les objets compacts sont gérés.
  *Limite* : un bloc objet **entier** retiré puis ré-ajouté est réécrit en indentation uniforme (sa mise en forme mixte
  d'origine est perdue ; le JSON reste valide).
- **Autoexec, section du cenv, section du `.h`** : écart ligne à ligne. Si une ligne de A est introuvable telle quelle
  (retouchée à la main), **toute** la modification est refusée (409) ; le refus cite le fichier et les lignes, mots de
  passe masqués. Ancre d'un ajout : la ligne précédente si elle est unique (ajout après elle) ; absente, refus ;
  présente plusieurs fois, la paire précédente + suivante, puis la suivante seule, sinon refus. Une ligne qui deviendrait
  double (par exemple un module déjà ajouté à la main) est refusée.
- **Figés** : lieu, nom, puce et base. Renommer se fait dans la page 7800 « Fichiers Berry par env » ; changer de base
  ou de puce revient à créer une autre carte.
- **Esclave** : le bloc `rangeExtender` n'est pas relu (voulu). Cocher la case sur un esclave qui a déjà ces lignes est
  refusé comme doublon.
- **Métiers 2 à N** : leurs éléments sont conservés mais non éditables.
- Mots de passe, build et empreinte comme à la création : jamais envoyés à la page, `***` dans le diff, les refus et
  les erreurs ; refus pendant un build ; empreinte périmée -> refaire « Voir le diff ».

**Supprimer.** Réservé aux **cartes du parc** listées par l'assistant (une base, ou un env sans `_persist.json` :
page 7800). `/suppression/prepare` affiche le panneau des éléments retirés : section du cenv, section du `.h` et son
define, `default_envs` et `data_dir` de `platformio_override.ini`, dossier renommé en `...-sauvegarde`. Il faut cocher
« J'ai vérifié ces éléments » avant que « Supprimer » (`/suppression`) s'active.

### Onglet « autoexec.bat »

Deuxième onglet de la page : modifier l'`autoexec.bat` d'une carte du parc, ou y ajouter des lignes, sans en connaître
la syntaxe. Le fichier s'exécute **à chaque démarrage** de la carte. Choisir la carte en haut ; rien n'est écrit avant
« Écrire dans le dépôt », rien n'est envoyé avant « Envoyer ».

- **Le texte, à gauche**, se modifie librement. Les mots de passe y sont remplacés par `***` : la page ne les reçoit
  jamais, le serveur les remet à l'écriture. Retirer ou ajouter une ligne portant une commande à `***`, alors qu'il en
  reste une autre de la même commande, est refusé au diff (message explicite) : retaper la valeur ou annuler.
- **« Supprimer la ligne N »**, sous le texte : la ligne du curseur, ou celle de l'avertissement cliqué.
- **Les avertissements**, sous le texte et en points dans la marge (survol = détail, clic sur la liste = la ligne) :

  | Niveau | Avertissement | Ce qu'il faut faire |
  |---|---|---|
  | Rouge | Redémarrage à répétition (`Hostname`…) | Retirer la ligne, régler la valeur autrement (bouton « Enlever ») |
  | Rouge | Secret en clair, même en commentaire | Le dépôt est public : garder la valeur hors du fichier |
  | Orange | Redémarrage si la valeur change | Vérifier (bouton « Enlever ») |
  | Orange | Doublon : le persist repose déjà la commande au démarrage | Retirer la ligne (bouton « Enlever ») ou changer le persist |
  | Orange | Commande inconnue | « Corriger » propose la plus proche |
  | Orange | Commande absente : pas compilée pour cette carte (`USE_…` non défini dans son env) | Retirer la ligne, ou compiler la fonction dans le firmware de la carte |
  | Orange | Commande absente (Berry) : `ReglageXxx` d'un module que l'`autoexec.be` de la carte ne charge pas | Retirer la ligne, ou charger le module dans l'`autoexec.be` |
  | Orange | Ligne de plus de 510 octets : le firmware la tronque | Couper la ligne |

  Les rouges demandent de cocher « J'ai lu les N avertissements rouges » à l'écriture et à l'envoi.

  « Commande absente » ne sort que si c'est **certain** : les macros de l'env sont lues sans compiler (quelques secondes au
  premier passage, puis en mémoire tant que le cenv et `user_config_override.h` ne changent pas), et une garde que la lecture ne
  tranche pas ne donne rien. Une commande définie à plusieurs endroits du firmware (`Subscribe` : règles ou script)
  n'est signalée que si **tous** sont exclus. Si la lecture échoue, une ligne discrète « Vérification par carte
  indisponible » s'affiche et aucune alerte n'est donnée. Limite : les commandes BLE et MI32 ne sont jamais signalées
  (leurs gardes passent par des macros que la lecture ne pose pas) ; les `SetOption` ne sont pas concernées.

  Pour les commandes Berry (`tasmota.add_cmd` dans `data/fs` ou le dossier de la carte), même règle de certitude : l'alerte ne
  sort que si **aucun** des modules qui la déclarent n'est chargé par l'`autoexec.be` (nom entre guillemets ou après `import`,
  module importé par un module chargé, `demarrage.leds()`, `demarrage.historique()`). Un nom cité dans un commentaire ou chargé
  sous une condition `OFF` du persist compte comme chargé : on se trompe du côté du silence. `autoexec.be` absent, vide ou de
  forme non comprise : aucune alerte. Une commande Berry qui porte le nom d'une commande du firmware (`Dimmer`) n'est jamais
  signalée (code `autoexec_berry.py`, banc `test_autoexec_berry.py`).
- **« Ajouter », à droite** : chercher dans la banque (`outils_docs/schemas/banque_autoexec.json`), remplir le
  formulaire, vérifier l'aperçu, insérer sous la ligne du curseur. Une commande qui déclencherait l'alerte « absente »
  pour la carte choisie (non compilée, ou module Berry non chargé) est **en pointillés**, avec la raison en infobulle et sous
  son titre ; elle reste sélectionnable. Sans vérification possible (préprocesseur indisponible), rien n'est marqué. « Nouveau modèle… » et « En faire un modèle »
  ajoutent une commande à la banque (« Tes commandes »).
- **Si la commande est déjà dans le fichier** : la page donne sa ligne et propose « Remplacer par la nouvelle » ou
  « Enlever l'existante » ; « Insérer quand même » reste possible pour une commande qui se répète (`Delay`, `Publish`).
  Dans une `Backlog`, seule la commande visée part ; une `Backlog` vidée disparaît. `SO146` et `SetOption146` sont la
  même commande (seul alias court du firmware) ; les autres alias (`Power` = `Power1`) ne sont pas reconnus à cet endroit. Une ligne en commentaire ne compte pas.
- **« Enregistrer… (diff) »** montre les changements, puis **« Écrire dans le dépôt »** écrit le fichier (refusé pendant un
  build, ou si le fichier a changé sur le disque depuis sa lecture ; copie dans
  `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`). Le fichier n'est pas commité : à faire à la main.
- **« Puis envoyer à la carte (OTA)… »** envoie **le fichier du dépôt**, sans toucher au firmware ni au persist, par l'une
  des deux voies choisies dans le panneau : **Wi-Fi (HTTP)**, par défaut (`/ufsu`), ou **MQTT**, pour une carte sans
  adresse IP joignable (esclave derrière son maître). Changer de voie relance la lecture de la carte. Grisé tant qu'une
  modification n'est pas écrite. La page lit d'abord la carte (`Status 5`) et
  refuse si son nom d'hôte diffère du `serveur.hostname` du persist du dépôt. Elle montre le fichier de la carte s'il
  diffère et demande de cocher son remplacement ; la copie de l'ancien fichier part dans `autoexec_cartes\<env>\` du
  même dossier. « Redémarrer la carte ensuite » est décochée : sinon la carte l'exécute au prochain démarrage. Pour une
  carte derrière le maître (cuve, rideau, portail de jardin), le maître passe en `Sleep 0` le temps de l'envoi.

**Voie MQTT** : broker du dépôt (celui de `user_config_override.h`), topic lu dans `serveur.mqtt.topic` du persist du
dépôt, identité par `cmnd/<topic>/Status 5`, fichier transmis par le module `fsMqtt` de la carte (`fsmqtt/<topic>/…`, contrôle
MD5). La carte doit avoir chargé `fsMqtt` : c'est le cas du P4, de la cuve, du rideau, du portail de jardin, de la cave, des cartes des débits du bureau et du grenier du RDC
(ligne `demarrage.charge(["fsMqtt"])` de leur autoexec, `data/**/autoexec.be`). Sinon : refus « aucune réponse de fsMqtt.be ». Une
carte qui n'a pas d'autoexec chargeant `fsMqtt` peut le recevoir par l'extension `fsMqtt.tapp` (voir « Fabrique
d'extensions »). Si l'`autoexec.bat` de la carte ne peut pas être relu par MQTT, rien n'est envoyé (fichier absent : envoi
normal).

Autres voies : un envoi série de la page Build écrit aussi ce fichier, mais il réécrit tout le système de fichiers,
persist compris. Un refus « répond X à Status 5, pas Y »
veut dire que la carte n'a pas encore reçu le persist du dépôt : l'envoyer depuis la page Build, puis réessayer.

Si Tasmota évolue, régénérer la liste des commandes : `autoexec_commandes.py --verifier` (écarts), `--generer` (mise à jour de
`outils_docs/schemas/commandes_tasmota.json`). Conception : [spec](../../docs/superpowers/specs/2026-11-03-onglet-autoexec-bat-design.md) ;
plans : `tasks/plans/autoexec-bat.md`, `tasks/plans/autoexec-mqtt-tapp.md` (voie MQTT, alerte « absente »). Bancs :
`test_autoexec_analyse.py`, `test_autoexec_banque.py`, `test_autoexec_commandes.py`, `test_autoexec_envoi.py`,
`test_autoexec_fichier.py`, `test_autoexec_gardes.py`, `test_assistant_persist_autoexec.py`, sonde
`test_assistant_persist_autoexec_chrome.py`.

### Limites connues

- L'éditeur ne règle que **activation, nom, broche et type**. `idModBus`, `virtuel`, `channel`, `nbLeds` se
  complètent à la main dans le `_persist.json` créé.
- Les broches de **SD, I2S, Ethernet et LoRa** ne sont pas contrôlées.
- Les éléments ne vont que sur le **bloc métier principal**.
- Les éléments des **métiers 2 à N** sont conservés lors d'une modification, mais non éditables (voir « Modifier ou supprimer un env existant »).
- Une carte dont la section du `.h` (ou l'autoexec, ou la section du cenv) a été retouchée à la main au point qu'une ligne générée ne s'y retrouve plus est **refusée à la modification** (le refus cite le fichier et la ligne) : c'est le cas aujourd'hui de plusieurs cartes anciennes du parc — les reprendre à la main ou les recréer.
- Clés `adressMAC` / `adresseMAC` et `telePeriod` : tranché le 2026-10-28 — `telePeriod` de `serveur.udp` et `serveur.rangeExtender` retirées (jamais lues), MAC écrite dans `adresseMAC` dès le boot par `globalFonctions`, `adressMAC` retirée ;
  voir `outils_docs/historique/ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md`.

### Bancs

Dans `outils_docs/scripts_python/outils_pc/`, avec le Python du penv PlatformIO (code de sortie 0 = vert) :
`test_assistant_persist_modele.py`, `_parc.py`, `_elements.py`, `_generation.py`, `_creation.py`, `_fidelite.py`,
`_texte.py`, `_delta.py`, `_modification.py` (lent : plusieurs minutes, rejeu du parc), `_web.py`, et la sonde Chrome `test_assistant_persist_page_chrome.py` ; cible Custom :
`build/test_cible_assistant_persist.py`. Les bancs travaillent sur un dépôt d'essai temporaire (lecture seule des
vrais persists) : aucun n'écrit dans le vrai dépôt ni dans le vrai dossier des sauvegardes.
