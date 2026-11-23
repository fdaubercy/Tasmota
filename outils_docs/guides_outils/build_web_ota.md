# Build : OTA du firmware et du FS

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

### L'IP de l'OTA

Lue dans `WIFI_IP_ADDRESS`. Si elle vaut `0.0.0.0` (DHCP) ou manque, la ligne demande une IP à saisir : elle ne
vaut que pour ce lancement (rien n'est réécrit) et la ligne est refusée tant que le champ est vide.

**Esclaves derrière le range extender du maître** (cuve, rideau, portail de jardin) : sans IP fixe, la page propose
`<IP du maître>:<8080 + id - 1>` (`192.168.0.43:8081` pour la cuve, `192.168.0.43:8082` pour le rideau, port 8083 pour le portail de jardin, id 4), tiré de
`serveur.rangeExtender` du persist de la carte au dépôt (`activation` ON, `id` ≥ 1, `ipMaitre`). La note sous la
ligne dit d'où vient l'adresse (« par le maître », ou « IP fixe de user_config_override.h »). Le champ accepte
aussi une saisie `IP:port`. Avant d'envoyer quoi que ce soit à une adresse `IP:port`, la page (étape
« Connexion par le maître ») :

1. envoie `RoutageRangeExtender` au maître, qui pose ses redirections d'après sa table de découverte (la table
   des redirections se vide à chaque redémarrage du maître) ;
2. demande `Status 5` à la carte jointe par ce port, et compare son nom d'hôte à celui du persist de l'env.

Maître injoignable, Berry du maître arrêté, esclave hors ligne pour le maître (rien derrière le port) ou autre
carte derrière le port : **refus, rien n'est envoyé**. Ensuite, firmware et FS passent par la redirection comme
pour une carte jointe directement.

Pendant tout l'envoi, la page met le maître en `Sleep 0`, puis remet sa valeur, même en cas d'échec : à `Sleep 50`,
le relais du maître marque des pauses de plusieurs secondes et l'esclave abandonne l'envoi au bout de 5 s
(mesure du 2026-10-28 : coupé à 3 % ; à `Sleep 0`, 74 à 102 Ko/s sans pause). Si la valeur n'a pas pu être
remise, la ligne de l'env le dit : la remettre à la main (`Sleep 50` dans la console du maître).

Une carte restée **en safeboot** par un envoi coupé ne connaît plus `Status` : la page la reconnaît à sa page
d'accueil (« SAFEBOOT », titre = `serveur.nom` du persist) et relance l'envoi du firmware sans autre geste.

### OTA du firmware

La page lance `pio run -e X` (compilation), puis envoie elle-même `.pio/build/<env>/firmware.bin.gz` (à défaut, ou
s'il est plus ancien que `firmware.bin` : `firmware.bin`) par `/up` puis `/u2` (protocole de `pio-tools/espupload.py`).
Si la carte n'a qu'une partition OTA (image `0xE9`), la page la bascule d'abord en safeboot par `/u4` ; si l'envoi
échoue ensuite, le message dit que la carte est restée en safeboot (renvoyer un firmware par `http://<ip>/up`).
Succès **prouvé par `Status 2`** : la carte doit
revenir (90 s maximum) avec une version et une date de compilation changées ; le texte de la réponse seul ne
suffit pas. Aucun script de build n'est modifié et il n'y a plus de variable `TASMOTA_OTA_IP`.

### OTA du file system

Tasmota n'accepte pas d'image LittleFS en OTA : la page envoie le **contenu de `.pio/build/<env>/littlefs.bin`**,
l'image que le `buildfs` vient d'écrire (celle qu'un `uploadfs` par câble flasherait), fichier par fichier par
`/ufsu`, `_persist.json` compris. Elle lit l'image avec littlefs-python (Python du penv PlatformIO), avec les
paramètres du `buildfs`, et en extrait les fichiers dans un dossier temporaire. **Pas `littlefs_data`** : ce dossier
est rempli par `post_esp32.py` après chaque édition des liens du firmware, n'est jamais vidé, et ne reçoit
`data/fs`, `data/json`, `data/sd` que pour certaines cibles : il porterait les restes d'un ancien build. Déroulé :

1. construction du FS si elle n'est pas déjà cochée, puis lecture de `littlefs.bin` (absente ou illisible : **rien
   n'est envoyé**, l'env est en échec). **Contrôle d'identité** : le nom d'hôte (`serveur.hostname`, sans casse) et
   le topic (`serveur.mqtt.topic`) du `_persist.json` de l'image doivent être ceux du `_persist.json` de l'env au
   dépôt (`data/<lieu>/<carte>/`). Sinon, ou si l'image n'a pas de persist lisible, **rien n'est envoyé** et le motif
   nomme les deux identités (le 2026-10-26, le P4 avait reçu le FS de la cuve). Sans persist de l'env au dépôt,
   l'étape affiche « identité non contrôlée » ;
2. **sauvegarde du `_persist.json` de la carte** dans `%LOCALAPPDATA%\outils_tasmota\build\persist\<env>-<horodatage>.json`.
   Impossible à télécharger, ou pas du JSON valide : **rien n'est envoyé**, l'env est en échec ;
3. **comparaison avec la carte**, avant toute écriture : place libre (`UfsFree`) et taille de chaque fichier déjà
   présent (pages `/ufsd` des dossiers concernés). Un fichier de même taille est relu et comparé octet pour octet :
   **identique, il n'est pas renvoyé**. Bilan de place, en blocs de 4 Ko : les nouveaux fichiers moins ceux qu'ils
   remplacent. S'il dépasse la place libre, **rien n'est envoyé** et le motif donne les Ko libres et les Ko nécessaires.
   Le FS n'est jamais vidé : `/.settings` (réglages Tasmota), `/.drvset*` (calibrages) et les données des modules
   (`/energie/`…) n'ont pas de copie au dépôt ;
4. envoi des fichiers, sous-dossiers compris, `_persist.json` en dernier. Tasmota refuse un fichier plus gros que sa
   place libre, même s'il en remplace un (« Fichier trop grand ») : dans ce cas l'ancien est **supprimé juste avant**
   d'envoyer le nouveau. Jamais le persist : s'il ne tient pas, l'env est en échec et le persist de la carte reste
   intact. Un refus de la carte affiche sa raison (le texte qui suit « Échoué »). Cas réel du 2026-11-09 : différentiel
   (FS de 320 Ko), arrêt sur `jsParam.js` (37 Ko pour 32 Ko libres) alors que les 4 derniers fichiers étaient identiques ;
5. relecture du `_persist.json` de la carte, comparé octet pour octet à celui envoyé (différent : env en échec,
   **pas de restauration automatique**, le chemin de la sauvegarde est affiché) ;
6. rechargement des globales Berry (`Br import persist …`) ;
7. `Restart 1`, attente du retour de la carte (90 s), relecture du persist. Si le persist relu après le
   redémarrage diffère de celui envoyé, un **avertissement** est affiché avec le chemin de la sauvegarde (l'env
   n'échoue pas : les fichiers sont déjà envoyés et la carte est revenue) ; carte non revenue : env en échec.
