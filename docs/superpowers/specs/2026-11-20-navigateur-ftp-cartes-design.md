# Navigateur FTP des cartes : conception

Date : 2026-11-20. Statut : conception validée en conversation, avant plan.

## 1. Intention

Une page web de l'annuaire des outils PC pour accéder aux fichiers d'une carte ESP32, ESP32-S3 ou ESP32-P4 par son
serveur FTP. Usages, dans les mots de l'utilisateur :

- récupérer sur le PC l'historique et les relevés écrits sur la carte SD ;
- ajouter ou supprimer un dossier ou un fichier du système de fichiers ;
- ranger des fichiers.

Constat du 2026-11-20 : aucun module n'écrit de journal texte sur la SD (les logs partent vers syslog, MQTT ou la
console). Les fichiers à récupérer sont aujourd'hui l'historique `/histo/<nom>-AAAA-MM.bin`
(`historiqueFonctions.DOSSIER`) et l'énergie `/energie` (`energieFonctions.DOSSIER`).

Ranger = déplacer ou renommer dans un même support (commandes FTP `RNFR`/`RNTO`).

## 2. Décisions prises avec l'utilisateur

| Sujet | Décision |
|---|---|
| Interface | Modèle A : explorateur à deux volets (maquette ci-dessous) |
| Serveur FTP des cartes | Allumé À LA DEMANDE par la page, jamais en permanence |
| Persist | `serveur.serveurFTP.activation` passe à `"OFF"` sur TOUTES les cartes |
| Esclaves du Range Extender | Exclus : ni listés, ni joints, aucune redirection NAPT posée |
| Construction | Outil PC Python du modèle des autres pages (façon n°1 ci-dessous) |

Décisions du 2026-11-21 (§7 et §9) : déplacer un fichier protégé demande aussi une seconde confirmation ; le FTP ne
s'éteint à la fermeture d'une page qu'avec le DERNIER onglet ouvert ; l'annuaire refuse d'arrêter l'outil pendant une
session ouverte.

## 3. Buts, non-buts, anti-buts

Buts : choisir une carte, parcourir la flash ou la SD, télécharger (fichier, sélection ou dossier en zip), envoyer
un fichier, créer et supprimer un dossier, supprimer, renommer, déplacer.

Non-buts (v1) :

- copier d'un support à l'autre en une action (flash vers SD) : se fait en deux temps, téléchargement puis envoi ;
- éditer un fichier dans la page ;
- joindre une carte derrière le NAPT d'un maître ;
- parcourir les disques du PC (modèle B écarté).

Anti-buts (l'outil est raté s'il fait cela, même en marchant) :

- laisser le FTP d'une carte allumé après la fin de la session ;
- envoyer le mot de passe FTP au navigateur, ou l'afficher dans un journal ;
- écrire quoi que ce soit dans le dépôt ;
- supprimer un fichier de démarrage sur un seul clic.

## 4. Ce qui existe (vérifié le 2026-11-20)

- Firmware : `tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino::FTP_Server` et `::Switch_FTP`. Commande `UfsFTP n` :
  0 = arrêt, 1 = `ufsp` (la SD si elle est montée, sinon la flash), 2 = `ffsp` (la flash). Le mode est ÉCRIT dans
  `Settings->mbflag2.FTP_Mode` et relancé à chaque `FUNC_NETWORK_UP`. Un seul support visible par session FTP.
- Bibliothèque `lib/lib_div/ESPFtpServer` : un seul client à la fois, mode passif seul, port de contrôle 21, port de
  données FIXE 50009, tampon de 4 Ko (S3/P4). Commandes : `LIST`, `MLSD`, `NLST`, `RETR`, `STOR`, `DELE`, `MKD`,
  `RMD`, `RNFR`/`RNTO`. La réponse `PASV` annonce `WiFi.localIP()`.
- Identifiants : `USER_FTP` et `PW_FTP` dans la partie commune de `tasmota/user_config_override.h`, communs à toutes
  les cartes. Les clés `utilisateur` et `mdp` du bloc `serveurFTP` du persist ne sont lues par aucun code.
- `USE_FTP` est retiré (`#undef`) dans les sections `#elif` des ESP32 sans PSRAM (cave ESP32, interrupteur
  énergie, projecteur LED) : `new FtpServer` les faisait planter.
- Berry : `data/fs/globalFonctions.be::globalFonctions_regleFTP`, appelée à chaque connexion réseau. Avec
  `activation` à `"ON"`, elle démarre le FTP en mode 2 après 50 s ; avec `"OFF"`, elle envoie `UfsFTP 0` aussitôt.
  Avec le persist à `"OFF"`, un redémarrage ou une reconnexion coupe donc le FTP : c'est le filet de sécurité de la
  décision « à la demande ».
- Esclaves du Range Extender : `outils_pc/build_envs.py::adresse_par_maitre` (bloc `serveur.rangeExtender` actif,
  `id` ≥ 1, `ipMaitre` présent).
- Cartes et lieux : `outils_pc/lieux.py::identites` (env, lieu, nom d'hôte, topic, IP propre).
- Commandes HTTP vers une carte : `outils_pc/build_ota_http.py::_commande` et `::_get`.

## 5. Façons de construire envisagées

1. Outil PC Python, client FTP par `ftplib` (bibliothèque standard), page JS servie par un serveur local, sur le
   modèle des autres outils (`acces_web.py`, annuaire, tâche VS Code, cible Custom détachée). RETENUE : protocole
   standard qui couvre toutes les actions demandées, aucune dépendance ajoutée, intégration identique aux autres pages.
2. Gestionnaire de fichiers HTTP intégré à Tasmota (`/ufsd`, `/ufsu`, `UfsDelete`, `UfsRename`), sans FTP. Écartée :
   la liste des fichiers n'existe qu'en page HTML à découper (fragile à chaque synchro de l'amont), pas de création
   de dossier propre, et ce n'est plus la page FTP demandée.
3. Modèles d'interface B (double panneau PC ↔ carte) et C (page par tâches) : écartés au profit de A. B oblige la
   page à parcourir les disques du PC ; C fige l'emplacement des fichiers dans la page.

## 6. La page (modèle A)

```
[Lieu ▾ garage] [Carte ▾ tasmota32p4-serveur-modbus]  ● FTP actif (SD)  [ Flash | SD ]  [Historique et énergie]  [Déconnecter]
┌───────────────┬───────────────────────────────────────────────┐
│ /             │ ☐ Nom                 Taille   Modifié        │
│ ├ histo       │ ☑ mesures-2026-11.bin  412 Ko  20/11 10:12    │
│ ├ energie     │ ☑ mesures-2026-10.bin  1,1 Mo  31/10 23:59    │
│ └ json        │ ☐ debits-2026-11.bin    96 Ko  20/11 10:12    │
├───────────────┴───────────────────────────────────────────────┤
│ Télécharger (zip) · Envoyer… · Nouveau dossier · Déplacer vers… · Renommer · Supprimer │
└───────────────────────────────────────────────────────────────┘
```

Maquette d'origine : `outils_docs/navigateur_ftp/maquettes_interfaces.html` (copie de l'écran présenté en
conversation, modèle A retenu).

- Liste des cartes groupée par lieu (`lieux.py`, fonction JS commune `remplitParLieu`), arrivée par `?lieu=` comme les
  autres pages 7xxx.
- Pastille d'état : éteint, allumage, actif (support), erreur avec son message.
- Bascule Flash / SD : grisée quand la carte n'a pas de SD (à lire par la commande `Ufs`, voir §10).
- Bouton « Historique et énergie » : bascule sur la SD et ouvre `/histo`.
- Arborescence à gauche chargée dossier par dossier (pas de parcours récursif d'avance).
- Tableau : nom, taille, date si la carte la donne (`MLSD`, repli sur `LIST`), cases à cocher.
- Mode sombre comme les autres pages.

## 7. Cycle de vie du FTP d'une carte

1. Choix d'une carte : le serveur PC envoie `UfsFTP 1` (SD) ou `UfsFTP 2` (flash) par HTTP, attend que le port 21
   réponde (quelques secondes au plus), ouvre la session `ftplib`.
2. Bascule de support : `UfsFTP` de l'autre mode (le firmware recrée le serveur), puis nouvelle session.
3. Fin de session, dans tous les cas suivants, `UfsFTP 0` est envoyé :
   - clic « Déconnecter » ;
   - choix d'une autre carte ;
   - dernière page fermée (`pagehide` + `navigator.sendBeacon` sur `POST /ferme`, voir le registre d'onglets ci-dessous) ;
   - 15 minutes sans action, décomptées par le serveur PC (pas par le navigateur) ;
   - arrêt de l'outil (arrêt normal et `atexit`).
4. Filet : si l'outil meurt sans prévenir, le persist à `"OFF"` coupe le FTP au prochain redémarrage ou à la prochaine
   reconnexion réseau de la carte.
5. Une reconnexion Wi-Fi de la carte pendant une session coupe son FTP (même filet). La page l'affiche et propose de
   rallumer, sans le faire seule.

Une seule carte active à la fois par instance de l'outil. Toutes les opérations FTP vers la carte passent par un
verrou (le serveur de la carte n'accepte qu'un client).

Registre d'onglets (`ftp_cartes_onglets.py`, décidé le 2026-11-21) : chaque page tire un identifiant de 16 à 32 caractères
hexadécimaux et le joint à chaque sondage (`GET /etat?onglet=`, toutes les 5 s) et à l'ouverture (`POST /ouvre`). Le
`sendBeacon` de `pagehide` poste `/ferme` avec cet identifiant : le serveur n'envoie `UfsFTP 0` que si aucun autre onglet
n'est enregistré. Un onglet qui disparaît sans prévenir (plantage, veille) est oublié après 90 s sans sondage, et `tic()`
éteint alors le FTP si c'était le dernier (90 s et non 15 s : Chrome ralentit à une fois par minute les minuteries d'un
onglet caché). « Déconnecter » poste `/ferme` sans identifiant et ferme toujours, même avec d'autres onglets. Une session
ouverte sans identifiant (client ancien, `curl`) n'est jamais « perdue » : seule l'inactivité la ferme.

Arrêt de l'outil par l'annuaire : l'outil est lancé hors du job de l'annuaire (`dans_job=False`) et répond `GET /execution`
(`{"en_cours": true}` tant que le FTP d'une carte est allumé) ; l'annuaire refuse alors « Arrêter » (« Déconnecter »
d'abord). Hors session, l'arrêt ne laisse rien d'allumé. Un arrêt brutal par un autre moyen (`atexit` ne passe pas) laisse
le FTP allumé : le filet du persist (point 4) reste le seul recours.

Le serveur de la carte déconnecte un client resté 5 minutes sans commande (`ESPFtpServer.h`, `FTP_TIME_OUT 5`), ce
qui n'éteint pas le serveur FTP. La session `ftplib` est donc rouverte sans bruit à l'opération suivante si elle est
tombée ; pas de `NOOP` d'entretien. Le décompte de 15 minutes du §7 reste celui du serveur PC et commande seul
l'extinction (`UfsFTP 0`).

## 8. Liste des cartes

Une carte apparaît si, et seulement si :

- son env est de la famille « cartes » (`build_envs.liste_envs`) et sa puce est ESP32, S3 ou P4 ;
- la section `#elif defined(FIRMWARE_...)` de son env dans `user_config_override.h` ne retire pas `USE_FTP` ;
- elle n'est PAS esclave du Range Extender. Un persist illisible exclut la carte (on ne joint jamais une carte dont
  on ne sait pas si elle est derrière un NAPT). Le lecteur doit tolérer les caractères de contrôle dans une chaîne
  (`strict=False`) : aucun persist du dépôt n'en porte au 2026-11-21 (les 16 se lisent en JSON strict, la première
  affirmation de cette note, tenue pour vraie le 2026-11-20, était fausse), mais un persist de carte peut en recevoir un.
  `build_envs.adresse_par_maitre` ne convenait PAS à l'origine : elle rendait « pas esclave » sur un persist illisible,
  l'inverse de la règle voulue ; elle lit aussi en `strict=False` depuis le 2026-11-21. L'outil a son propre lecteur
  (`strict=False`, illisible = exclu) dans `ftp_cartes_liste.py`. Le banc vérifie que la cuve réelle est exclue.
- Contrôle de `USE_FTP` par env : lecture des sections du `.h` comme `outils_pc/autoexec_gardes.py` et
  `build/verifie_lib_ignore.py` (macros d'un env), pas une liste figée. Doute sur la lecture = carte exclue.

Adresse : l'IP propre du `.h` si elle existe, sinon `<Hostname>.local` (mDNS résolu par ce PC depuis le 2026-11-13).
Une carte sans IP dont le nom `.local` ne se résout pas reste listée ; l'erreur s'affiche à l'allumage.
La liste est recalculée à chaque ouverture de la page, mais mise en cache : la clé est `(chemin, mtime_ns, taille)` des
fichiers lus (ini, `user_config_override.h`, persist), la liste est préchauffée au démarrage de l'outil et ne se recalcule
que si l'un d'eux a changé (décidé le 2026-11-21).

## 9. Sécurité

- Identifiants FTP lus côté serveur dans `user_config_override.h` (partie commune, ou section de l'env si elle les
  redéfinit). Jamais envoyés à la page, jamais écrits dans un journal.
- `acces_web.py` : sans jeton depuis ce PC, jeton depuis un autre appareil.
- Écritures (envoi, suppression, création, renommage, déplacement, allumage du FTP) : depuis ce PC seulement, comme
  la page Ménage et la page Tâches planifiées. Un autre appareil peut parcourir et télécharger une session déjà
  ouverte depuis ce PC.
- Confirmations :
  - toute suppression et tout écrasement demandent une confirmation ;
  - une seconde confirmation est demandée pour `autoexec.be`, `autoexec.bat`, `_persist.json`, `*.bec`, `.drvset*`,
    et pour la suppression des dossiers `/sd` et `/json` entiers, SANS tenir compte de la casse (la SD est en FAT) ;
  - la même seconde confirmation vaut pour DÉPLACER un de ces fichiers, `/sd` ou `/json` entiers compris (source ou cible protégée) et pour supprimer ou
    déplacer un dossier qui en contient un, à n'importe quelle profondeur (parcours borné, limite atteinte = deux
    confirmations) : le serveur répond 409 (« seconde confirmation ») et la page redemande ; `POST /deplace` et
    `POST /supprime` portent `confirmations` (entier, 400 sinon) ;
  - un déplacement vers une cible existante est refusé (409), jamais écrasé ;
  - décidé le 2026-11-22 : ÉCRASER un fichier protégé par un envoi demande aussi la seconde confirmation. `POST /envoie` porte
    `confirmations` en paramètre de requête (entier, 1 par défaut, 400 sinon) ; avec `ecraser=1` sur un fichier protégé existant, le
    serveur répond 409 « seconde confirmation » avant toute écriture sur la carte, la page ouvre la seconde boîte (texte d'écrasement) et
    renvoie avec `confirmations=2`. Écraser un fichier ordinaire reste à une confirmation, créer un fichier absent (même de nom protégé)
    n'en demande pas davantage (`ftp_cartes_session.py::Session.envoie`) ;
  - noms comparés comme FatFs (`ftp_cartes_chemins.py::cle_fat` : sans casse, sans points ni espaces finaux de chaque segment) pour
    `protege`, l'existence d'un nom à l'envoi et la cible d'un déplacement (`autoexec.be.` et `AUTOEXEC.BE ` sont protégés comme
    `autoexec.be`). Les noms courts 8.3 (`AUTOEX~1.BE`) ne sont pas traités. La flash (LittleFS) distingue la casse : la comparaison y est
    plus prudente que nécessaire (un refus de trop, jamais un écrasement) ;
  - un dossier ne se déplace ni dans lui-même ni sous lui-même (`ftp_cartes_chemins.py::dans_lui_meme`, 409 avant toute commande FTP ;
    un renommage qui ne change que la casse est refusé de même) ;
  - type attendu (décidé le 2026-11-22) : `POST /supprime` et `POST /deplace` portent `type` (`fichier` ou `dossier`, lu par la page dans la
    liste affichée) ; le serveur le compare au type sur la carte SOUS le verrou, avant toute commande de modification, et répond 409 « le type
    de l'élément a changé » s'il diffère (ou si l'élément a disparu). `type` absent ou vide : pas de contrôle ; autre valeur : 400.
- Les gestes de la page (dont `/zip` et `/telecharge`) portent la paire `env`/`support` ; si elle diffère de la session
  (un autre onglet a changé de carte ou de support) : 409 « la session a changé », rien n'est écrit.
- Le serveur n'envoie jamais le message brut d'une exception inattendue (il pourrait citer un mot de passe) : le type
  seul.
- Chemins reçus de la page validés côté serveur (pas de `..`, pas de caractère de contrôle, pas de `\`, longueur bornée :
  `ftp_cartes_chemins.py::valide_chemin`). `\` est refusé (400) car FatFs peut le lire comme un séparateur et sortir du dossier visé.
- Anti-CSRF des GET qui ont un effet (décidé le 2026-11-22) : `GET /etat?onglet=` (enregistre un onglet), `/liste` (repousse l'inactivité)
  et `/telecharge` refusent (403) une requête dont `Sec-Fetch-Site` n'est ni `same-origin` ni `none` (`same-site` compris : un autre outil
  sur 127.0.0.1 n'a pas la même origine, le port ne compte pas pour le « site »), ou dont l'`Origin` n'est pas celle de l'outil
  (`ftp_cartes_web.py::fabrique_gestionnaire`). Sans ces en-têtes (navigation directe, `urllib`, ancien navigateur) : admise. Les POST
  (`/zip` compris) avaient déjà l'en-tête `X-Ftp-Cartes` et le contrôle d'origine.
- Extinction non confirmée (décidé le 2026-11-22) : si `UfsFTP 0` échoue, la session garde l'adresse de la carte et l'état « allumé »
  (`en_session()` vrai, l'annuaire refuse l'arrêt), n'accepte plus aucun geste, et `tic()` renvoie `UfsFTP 0` (5 essais au plus,
  `ESSAIS_EXTINCTION`), puis « Déconnecter » seul. Ouvrir une autre carte est refusé tant que l'ancienne n'a pas confirmé ; rouvrir la même
  efface l'attente. Le message d'état ne cite aucun identifiant.
- Téléchargements : flux direct vers le navigateur ; zip construit en mémoire ou en fichier temporaire hors dépôt.
  Rien n'est écrit dans le dépôt.

## 10. Laissé au constructeur (décisions mineures, prises par Claude, à corriger si besoin)

- Port : 7450 (libre au 2026-11-20).
- Groupe de l'annuaire : « Configuration des cartes ».
- Noms de fichiers, sur le modèle des autres outils : `outils_pc/ftp_cartes_web.py` (serveur, routes),
  `ftp_cartes_page.py` (HTML/CSS/JS), `ftp_cartes_session.py` (allumage, extinction, verrou, inactivité, `ftplib`),
  `ftp_cartes_liste.py` (cartes éligibles), `build/cible_ftp_cartes.py` (`NOM_CIBLE` `ftp_cartes`). Chaque fichier
  sous 500 lignes.
- Détection de la SD : commande `Ufs` de la carte (type et taille du système de fichiers utilisateur) ; à vérifier
  sur une carte avant de figer la règle. Si `Ufs` ne répond pas ou ne tranche pas : bascule SD marquée « SD
  inconnue », la flash reste accessible ; jamais d'affichage silencieux de la flash sous l'étiquette SD.
- Écriture de `Settings` par `UfsFTP` à chaque allumage et extinction : acceptée (quelques sessions par jour,
  sauvegarde différée des réglages par Tasmota).
- Accès aux cartes réelles : le P4 et une S3 en ligne servent à l'essai final ; d'ici là, le code prévoit le repli
  ci-dessus et le banc couvre les deux cas (avec et sans SD).
- Racine vue dans chaque mode (`ufsp`, `ffsp`) et présence des dates dans `MLSD` : à relever sur une S3 et sur le P4
  au premier essai.
- Constats du premier essai sur le P4 du garage (2026-11-22, par l'API de l'outil, sans le navigateur : la page n'a pas
  été vue sur cette carte) :
  - `Ufs` ne rend QU'UN objet (`Type` 3, environ 11,3 Mo, 10,3 Mo libres : la flash) : pas de SD détectée. L'outil
    répond `sd` à `false`, ouvre en flash (`UfsFTP` 2) et la carte confirme ; « Déconnecter » ramène `UfsFTP` à 0.
  - Racine en flash : 16 entrées (`.drvset*`, `.extensions`, `.settings`, `_persist.json`, `autoexec.be`, des `.bec`,
    les dossiers `histo`, `json`, `logs` et `sd`, point de montage vide listé comme dossier).
  - `MLSD` donne la date des fichiers écrits depuis l'horloge de la carte (ex. 2026-11-21 06:15:50) ; les dossiers et
    les fichiers jamais datés (`pagesGraphiquesValidation.be`, `partition_wizard.bec`) sortent à l'époque 0 : la page
    affiche « 1969-12-31 23:59:59 ». Reste à faire : afficher un tiret pour cette date.
  - Non essayés : mode SD (cette carte n'en a pas), zip, envoi, suppression, déplacement, la page dans le navigateur.
- Place libre avant un envoi : lue par `Ufs` si la réponse la donne, refus si le fichier ne tient pas.
- Délais : allumage 10 s au plus, opérations FTP 30 s.

## 11. Bascule des persist (étape à part)

- Dans le dépôt : `serveur.serveurFTP.activation` à `"OFF"` dans chaque `data/<lieu>/<carte>/_persist.json` qui le
  porte à `"ON"`, sans toucher au reste du fichier (texte gardé octet pour octet hors cette valeur). Accord de
  l'utilisateur donné le 2026-11-20.
- Sur chaque carte : envoyer le nouveau `_persist.json` par l'onglet « Fichiers » de la page Build. Tant que ce n'est
  pas fait, une reconnexion rallume le FTP d'après l'ancien persist. La page FTP peut signaler une carte dont le FTP
  est déjà allumé à l'ouverture (indice d'un persist pas encore porté).
- Les dossiers `*-sauvegarde` ne sont pas concernés.

## 12. Intégration

Tuile de l'annuaire (`annuaire_registre.py`), tâche VS Code « Outil : navigateur FTP des cartes », cible Custom
détachée, section du mode d'emploi dans `outils_docs/README.md`, entrée dans la carte des documents de `CLAUDE.md`.

## 13. Preuves attendues

- Banc Python sans réseau : faux serveur FTP minimal dans le banc, qui imite la carte (un seul client, passif seul,
  port de données fixe), faux `UfsFTP` HTTP. Cas : liste, téléchargement, zip, envoi, suppression avec et sans
  confirmation, fichiers protégés, déplacement, extinction sur chacun des 5 événements du §7, refus des écritures
  depuis un autre appareil, chemins invalides, mot de passe absent de toute réponse. Témoins qui échouent sans le
  code testé.
- Banc de la liste : esclave du Range Extender exclu (dont la cuve réelle), env sans `USE_FTP` exclu, persist
  illisible exclu.
- Sonde Chrome hermétique de la page (Python de PlatformIO), Chrome arrêté après usage.
- Essai sur une vraie S3 et sur le P4 : allumage, parcours SD et flash, téléchargement de `/histo`, extinction
  vérifiée par `UfsFTP` (réponse 0) après chaque cas de fin de session.
