# Onglet « autoexec.bat » de l'Assistant persist — conception

Date : 2026-11-03. Plan d'origine : `tasks/plans/energie-differentiel.md`, A14. Maquettes : `outils_docs/autoexec_bat/`
(**modèle C retenu**, avec un ajout du modèle A).

## Intention

L'`autoexec.bat` d'une carte (`data/<lieu>/<carte>/autoexec.bat`) est exécuté par Tasmota à chaque démarrage
(`xdrv_50_filesystem.ino::UfsExecuteCommandFileLoop`). On l'écrit aujourd'hui à la main, sans aide. Deux besoins, de
même poids pour l'utilisateur :

1. **Être protégé des erreurs.** Cas vécu le 2026-11-02 sur le différentiel (commit `b87e5cc1b`) : une ligne
   `Hostname` faisait redémarrer la carte à chaque démarrage (boucle), vue seulement à la mise en service.
2. **Écrire vite une commande dont on ignore la syntaxe** (ex. les 11 minuteries recopiées à la main, `AdcParam1`).

Seul le différentiel a un `autoexec.bat` aujourd'hui ; l'outil doit aussi savoir en créer un pour une autre carte.

## Décisions de l'utilisateur (2026-11-03)

- **Endroit** : nouvel onglet de l'Assistant persist (page 7900, `assistant_persist_web.py`). L'Assistant gère déjà la
  configuration d'une carte (persist, autoexec.be, cenv, `.h`) ; il n'a pas encore d'onglets : en ajouter deux,
  « Persist (créer, modifier, supprimer) » (la page actuelle, inchangée) et « autoexec.bat ».
- **Disposition : modèle C** (`outils_docs/autoexec_bat/modele-C.png`) :
  - en haut : choix de la carte (env personnel), chemin du fichier, nombre de lignes et d'avertissements,
    « Annuler les modifications », « Enregistrer… (diff) » ;
  - à gauche : le fichier en **texte libre** ; un point coloré dans la marge des lignes à risque ;
  - dessous : **la liste de tous les avertissements** (numéro de ligne, type, explication, correction proposée
    quand il y en a une) ;
  - à droite : **l'ajout guidé** — recherche dans la banque, formulaire des champs de la commande choisie, aperçu de
    la ligne produite, « Insérer à la ligne n » ; puis « Tes commandes » (celles ajoutées par l'utilisateur) ;
  - en bas : le **diff** avant enregistrement, « Écrire dans le dépôt », puis « Envoyer à la carte (OTA)… ».
- **Ajout du modèle A** : cliquer un avertissement de la liste amène à sa ligne dans le texte ; survoler le point de
  la marge affiche le détail de l'avertissement.
- **Après « Enregistrer »** : diff confirmé, fichier du dépôt écrit, **puis envoi proposé** à la carte en OTA. La carte
  exécute le fichier au prochain démarrage (l'envoi ne redémarre pas la carte sans le demander).
- **Avertissements** (les quatre, à l'ajout comme sur le fichier entier) :
  1. **redémarrage à répétition** : la commande fait redémarrer la carte ; liste tirée du code Tasmota
     (`TasmotaGlobal.restart_flag = 2` dans la fonction `Cmnd…` de la commande : 24 fichiers du firmware,
     `CmndHostname` sans condition) **plus** les cas vécus ;
  2. **doublon avec le persist** : la commande règle un paramètre que `data/fs/configGlobal.be` repose déjà depuis
     le persist de cette carte (même table que les marques « ↻ démarrage » : `build_sauvegarde::POSEES`,
     `build_sauvegarde::commandes_posees`) ; dire la clé du persist et sa valeur ;
  3. **secret en clair** : `Password…`, `MqttPassword`, `WebPassword`, jetons… : le fichier est versionné dans un
     dépôt **public** ;
  4. **commande inconnue** : nom absent des commandes connues (faute de frappe), avec la commande la plus proche.
- **Banque de commandes** : un fichier JSON **du dépôt** (versionné, le même sur les deux postes) ; chaque commande
  personnalisée ajoutée par l'utilisateur la complète. Aucune valeur secrète dedans.

### Décisions complémentaires (après relecture, 2026-11-03)

- **Avertissements rouges** (boucle de redémarrage, secret en clair) : **rien n'est bloqué, confirmation explicite**.
  « Écrire dans le dépôt » demande de cocher « J'ai lu les N avertissements rouges » ; l'envoi à la carte la redemande.
  Les oranges (doublon persist, commande inconnue, ligne trop longue, redémarrage seulement si la valeur change) ne
  demandent rien.
- **Commande perso = modèle à champs** : l'utilisateur définit la commande avec des champs typés (texte, nombre,
  liste, heure, jours, relais…) pour qu'elle s'insère ensuite par formulaire, comme les commandes proposées. Il faut
  donc un **éditeur de modèle** (nom, description, catégorie, ligne avec ses champs, aperçu) ; une ligne tapée dans
  le texte et absente de la banque est proposée comme point de départ d'un modèle.
- **Commandes qui redémarrent** : pas d'autre cas vécu que `Hostname`. La liste vient d'une **recherche dans la doc
  et le code de Tasmota** : la documentation des commandes (dépôt `tasmota/docs`, `Commands.md` : mentions « restart »,
  « reboot », « causes a restart ») **et** le code du fork (`restart_flag = 2` dans les fonctions `Cmnd…`), croisés ;
  chaque entrée garde sa source et son classement « toujours » / « si la valeur change ».

### Choix de Claude (relecture du 2026-11-03, à contrôler)

- **Secrets dans les commentaires** : une ligne en commentaire est aussi masquée (`***`) et reçoit l'avertissement
  « secret en clair » ; rien n'en part vers la page. Les deux mots de passe déjà en commentaire dans l'`autoexec.bat`
  du différentiel restent tels quels (choix déjà fait par l'utilisateur, ne pas proposer de les changer).
- **Remise des secrets** : chaque `***` reprend la valeur d'origine de la **même commande, dans l'ordre**
  d'apparition (`Password1` → la 1re valeur de `Password1` du fichier sur disque…). `***` pour une commande sans
  valeur d'origine : enregistrement refusé avec le motif (saisir la valeur).
- **Commande connue** = présente dans les tables de commandes du code du fork (C), ajoutée par `tasmota.add_cmd`
  dans `data/fs`, ou dans la banque ; pas de vérification par env (gardes `USE_*`).
- **Envoi OTA** : identité vérifiée d'abord (`Status 5` comparé au nom d'hôte du persist, comme
  `build_ota_maitre::joint_par_maitre`) ; l'`autoexec.bat` de la carte est relu avant d'être écrasé et, s'il diffère
  du fichier du dépôt d'avant la modification, l'écart est montré et confirmé ; case « redémarrer ensuite »
  décochée par défaut.
- **Encodage** : UTF-8 sans BOM, fins de ligne du fichier d'origine gardées (CRLF ou LF).

## Ce que le firmware impose (constaté dans le code)

- Une commande par ligne ; `Backlog a; b; c` en enchaîne plusieurs. Ligne commençant par `;` (après espaces) :
  commentaire. Ligne vide ignorée. Fin de ligne `\n` ou `\r`.
- **Ligne de plus de 510 caractères tronquée sans message** (`cmd_line[512]`) : à signaler comme un avertissement
  (cinquième type, de la même famille que « commande inconnue » : la commande exécutée ne sera pas celle écrite).
- Une commande y est exécutée à chaque démarrage : une commande qui redémarre la carte **sans condition** crée une
  boucle ; une qui ne redémarre **que si la valeur change** ne coûte qu'un redémarrage au premier passage. Les deux
  cas sont à distinguer dans l'avertissement.

## Buts, non-buts, anti-buts

- **Buts** : les deux besoins ci-dessus ; zéro boucle de redémarrage introduite par l'outil sans avertissement
  rouge ; un fichier écrit identique octet pour octet hors des lignes modifiées (commentaires, lignes vides, ordre,
  fins de ligne gardés).
- **Non-buts** : exécuter les commandes sur la carte pour les essayer ; éditer les règles (`Rule`) ou le Berry ;
  remplacer l'éditeur du persist ; analyser la *valeur* de chaque commande (seulement le nom, les secrets et la
  longueur ; la syntaxe des valeurs n'est garantie que pour les commandes saisies par le formulaire).
- **Anti-buts** (échec même si « ça marche ») : un mot de passe envoyé à la page (règle de l'Assistant : les secrets
  restent côté serveur) ; un fichier réécrit qui perd des commentaires ou des lignes ; un envoi à la carte pendant
  un build ; un avertissement si bavard qu'on finit par ne plus le lire (une ligne propre n'affiche rien).

## Contraintes du dépôt (à suivre)

- Écriture **atomique** et sauvegardée comme les autres écritures de l'Assistant (moteur des transactions de
  `fichiers_berry_sauvegarde.Transaction`) ; refus pendant un build (comme la création d'env).
- Mots de passe **jamais envoyés à la page** : remplacés par `***` à la lecture, remis côté serveur à l'écriture pour
  les lignes que l'utilisateur n'a pas changées (même principe que l'Assistant et l'onglet Sauvegarde).
- Envoi à la carte : **même moteur que la page build** (`build_ota_fs.envoie_fs_ota` sur un dossier temporaire ne
  contenant que `autoexec.bat`, `fichiers=["autoexec.bat"]`, sans redémarrage), adresse résolue comme la page build
  (`build_envs`, esclave `IP:port` par le maître), refus si un build ou un envoi est en cours (`garde_build`, détection
  de `build_serie`). Transport MQTT possible plus tard (`build_ota_mqtt`), pas dans ce premier jet.
- Fichiers sous 500 lignes ; renvois au code par `fichier::fonction` dans les documents durables ; banc par module,
  sonde Chrome pour l'onglet ; mode d'emploi au README (`outils_docs/README.md` § Assistant persist) ; tuile de
  l'annuaire à jour.

## Laissé au constructeur

- Le format exact de la banque (proposition : `outils_docs/schemas/banque_autoexec.json`, une entrée par commande :
  nom, catégorie, description, modèle de ligne avec champs typés — texte, nombre, liste, heure, jours, relais —,
  comportement au redémarrage, origine « proposée » / « perso » et date d'ajout).
- Comment obtenir la liste des commandes connues (tables `kTasmotaCommands` et `k…Commands` des pilotes, préfixes
  compris ; commandes Berry ajoutées par `tasmota.add_cmd` dans `data/fs` ; banque perso) et celle des commandes qui
  redémarrent : produites par un script depuis le code du fork et la doc de Tasmota, figées dans un fichier relu par
  un banc qui échoue si le code a changé ; classement « toujours / si la valeur change » vérifié à la main.
- Le contenu initial de la banque : les commandes de l'`autoexec.bat` du différentiel et les courantes (SetOption,
  Timer, AdcParam, WebSensor, LedPower/LedState, SerialLog/WebLog, Latitude/Longitude, Timezone/TimeStd/TimeDst…).
- Le découpage en modules (le serveur de l'Assistant fait 426 lignes, son JS 397 + 120).
