# Build : onglet « Fichiers »

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

### Onglet « Fichiers » : envoyer quelques fichiers du FS

Pour remplacer un ou deux fichiers sur une carte (un `.be` corrigé, un gabarit, le persist) sans renvoyer tout le
file system. Onglet **Fichiers**, en haut de la page (l'onglet ouvert est retenu au rechargement). Deux transports :
**HTTP** (adresse de la carte) ou **MQTT** (par le broker, voir plus bas).

1. **Carte destinataire** (colonne de gauche) : les envs « Mes cartes » envoyables en OTA, sous un intertitre par
   lieu (« GARAGE · 3 »). L'adresse et sa
   provenance sont celles de l'onglet Build (IP fixe de `user_config_override.h`, ou `IP du maître:port` pour un
   esclave du range extender) ; une adresse saisie ici vaut aussi pour l'onglet Build, pour ce lancement seulement.
2. **Préparer la liste** : construit l'image du FS de la carte (`pio run -t buildfs`, comme « Construire le file
   system ») à partir des fichiers **du dépôt**, puis la relit. Refusé pendant un build, comme tout lancement.
3. La liste montre les fichiers **de l'image** (pas ceux de la carte), par dossier : taille, date du fichier au
   dépôt, et « dépôt plus récent que l'image » quand un fichier a été modifié depuis (préparer à nouveau). Cocher
   dans le tableau (la case d'en-tête coche le dossier affiché) ; le panier « À envoyer » les reprend, avec
   « retirer » et le total.
4. **Options**, choisies à chaque envoi :
   - **Recharger Berry** (`BrRestart`) : cochée d'office dès qu'un `.be` ou le persist part (décochable) ;
   - **Redémarrer la carte** (`Restart 1`, puis attente de son retour) : recharge aussi Berry, l'autre case est
     alors grisée. Sans aucune des deux, les fichiers sont seulement écrits.
5. **Envoyer N fichiers**. Le bouton dit pourquoi il est grisé (carte, adresse, liste, fichiers, lancement en cours).
   Si un fichier à envoyer est « dépôt plus récent que l'image », une **confirmation** le nomme : il partirait dans son
   ancienne version (Annuler, puis « Préparer la liste »). Les fichiers de `data/sd` et `data/json` comptent aussi.

Déroulé côté serveur (`build_ota_fs.py::envoie_fs_ota` avec `fichiers=`) :

- l'image envoyée doit être **celle de la liste** : si un `buildfs` l'a réécrite entre-temps, l'envoi est refusé
  (« préparer à nouveau ») ;
- **même contrôle d'identité** que l'OTA du FS : une image d'une autre carte n'est jamais envoyée (la liste
  s'affiche quand même, avec le motif) ; par le maître, même redirection et vérification du nom d'hôte, et maître en
  `Sleep 0` le temps de l'envoi ;
- **si `_persist.json` est coché** (annoncé « sauvegardé avant l'envoi ») : sauvegarde du persist de la carte,
  persist envoyé en dernier, relu et comparé, puis **toujours** rechargé (`persist.load()`) avant tout redémarrage
  (le persist vit en RAM : un redémarrage sans rechargement réécrirait l'ancien par-dessus le nouveau) ; après
  `Restart 1`, relecture comme pour l'OTA du FS. Sans persist coché, rien de tout cela.

L'avancement s'affiche **dans l'onglet** : barre en pourcentage, étape en cours et journal des étapes avec leur
détail (« 2/3 /controleCuve.be »), pour l'envoi comme pour la préparation de la liste. Le Suivi commun, sous les
deux onglets, montre la même chose sur la ligne « Envoyer des fichiers ». Les lancements partis de cet onglet ne
modifient pas les derniers choix mémorisés de l'onglet Build.

**Transport MQTT** (A16) : choisi dans le panier « À envoyer ». Les fichiers passent par le broker de
`user_config_override.h`, en morceaux de 1 900 octets (4 en vol, accusé cumulé, renvoi si un morceau se perd), vers le
module **`data/fs/fsMqtt.be` de la carte**, sous le topic de son persist (`fsmqtt/<serveur.mqtt.topic>/…`).
L'adresse de la carte est inutile : un esclave du range extender joint le broker par la sortie de son maître, sans
redirection ni `Sleep 0`. Débit mesuré : 14 à 18 Ko/s vers la cuve, sans coupure (HTTP : 74 à 102 Ko/s, mais coupé
quand le relais du maître marque une pause). Chaque fichier s'écrit dans `/fsmqtt.tmp` et ne remplace le vrai
qu'après contrôle de sa taille et de son MD5. Même déroulé que l'HTTP (persist sauvegardé par MQTT s'il part, envoyé
en dernier, rechargé ; redémarrage ou `BrRestart`, puis attente du « prêt » du module). **Prérequis** : `fsMqtt.be`
est solidifié dans le socle (toutes les cartes, firmware recompilé) et chargé par l'autoexec de la carte
(`demarrage.charge(["fsMqtt"])` : maître P4, cuve, rideau, portail de jardin, cave, écran de la cave, cartes des débits du bureau et grenier du RDC à ce jour, voir `data/**/autoexec.be` ; l'extension `data/extensions/fsMqtt` est l'autre voie). Sans lui, la page le dit (« aucune réponse sur
fsmqtt/<topic> ») et rien n'est envoyé.

**Effacer tout le FS avant l'envoi** (MQTT seulement, confirmation) : la carte FORMATE son FS (`path.format`,
persist et autoexec compris ; `/sd` de la flash aussi), puis toute l'image est envoyée, **persist en premier** (sans
effacement, il part en dernier) : un échec en cours d'envoi laisse au moins à la carte son persist, celui de l'image ;
celui d'avant reste dans la sauvegarde faite par la page. Le module, solidifié, survit.
Le formatage bloque la carte : s'il dépasse les 5 s du watchdog de la boucle, elle redémarre avec un FS vide, donc
sans autoexec ni Berry : la reprendre en HTTP (cet onglet) ou par câble. Idem si elle redémarre entre les deux. Bancs :
`berry/banc_fsmqtt.py` (module), `outils_pc/test_build_ota_mqtt.py` (PC) ; aucun essai sur carte à ce jour.

#### Arrivée depuis l'atelier des graphiques

Le bouton « Téléverser » de l'atelier des graphiques (voir « Atelier des graphiques ») ouvre la page à l'adresse
`/?env=<env>&depuis=atelier&fichiers=<chemins séparés par des virgules>&redemarrer=<0|1>`. Le même mécanisme sert à la
page des étiquettes QR (`depuis=qrcode`) et à l'atelier des visuels (`depuis=visuel`), avec leurs propres textes
(`build_page_atelier.py::AT_ORIGINES`). Le code est dans
`build_page_atelier.py::arriveeAtelier` (JS de la page, branché sur l'onglet Fichiers). Avec une liste **vide**
(`fichiers=`, lien « Envoyer par la page Build ↗ » de l'atelier, toujours visible), la page choisit la carte et construit
l'image sans rien cocher : bandeau « cochez les fichiers à envoyer ». Déroulé avec une liste :

1. La page sélectionne l'env, bascule sur l'onglet « Fichiers » et affiche un **bandeau** : « Fichiers sélectionnés
   automatiquement par l'Atelier des graphiques, pour téléverser un graphique nouveau ou modifié. Vérifiez puis cliquez
   sur « Envoyer ». »
2. Elle lance seule la **construction du FS** de l'env (le `buildfs` de « Préparer la liste », par `POST /lancer` avec ses
   en-têtes habituels : un lien ouvert par un tiers ne peut lancer que cela, qui ne touche aucune carte).
3. À la fin réussie de **ce** `buildfs`, elle relit la liste et **coche exactement les fichiers de la liste** présents dans
   l'image neuve. « Redémarrer » est coché si `redemarrer=1`.
4. Elle **n'envoie rien** : l'utilisateur vérifie la sélection puis clique « Envoyer ».

Cas limites :

- **Fichier absent de l'image** : jamais ignoré en silence, le bandeau écrit « Absent de l'image du FS, non coché : ... ».
- **Paramètres hostiles ou invalides** : env inconnu, absent des cartes envoyables en OTA ou de l'amont, chemin avec `..`,
  absolu, `\`, `:` ou caractère de contrôle, liste vide ou de plus de 1 Ko, `redemarrer` autre que 0 ou 1. Chacun est
  signalé par un message, rien n'est coché, et pour un env refusé ou une liste sans chemin valide **aucun `pio` ne part**.
- **Build déjà en cours** : si c'est un lancement de la page, rien n'est envoyé ; le `buildfs` part à la fin du build en
  cours (flux `/flux`). Si le serveur refuse parce qu'un build tourne **hors de la page**, nouvel essai **toutes les 5 s,
  1 h au plus**, avec un message. Toute autre réponse 409 abandonne avec un message.
- **Changement de carte** avant la fin, ou **redémarrage de l'outil** (flux coupé) : la sélection automatique est
  **abandonnée avec un message**. Un `buildfs` en échec ou arrêté ne coche rien et le dit.
- **Rechargement de la page** : l'adresse est ramenée à `?env=<env>` dès que le `buildfs` est accepté, donc un rechargement
  ne relance jamais la construction ; pendant l'attente d'un autre build, il reprend l'attente sans doublon.
