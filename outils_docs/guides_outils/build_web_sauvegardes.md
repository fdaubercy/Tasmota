# Build : sauvegarde de la configuration des cartes

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

### Onglet « Sauvegarde configuration » : sauvegarder, comparer, modifier, restaurer

Une sauvegarde est le fichier `/dl` de la carte, celui de « Sauvegarder la configuration » de sa page web : ses
Settings (Wi-Fi, MQTT, minuteries, gabarit, règles, `AdcParam`...) **et** ses fichiers `.drvset*` (calibrage,
compteurs ; voir l'onglet « Aide »). Fichiers `AAAAMMJJ-HHMMSS_<origine>.dmp` dans `outils_docs/sauvegardes_cartes/<env>/`,
**ignoré par git** : un `.dmp` porte les mots de passe Wi-Fi et MQTT en clair, et le dépôt est public.

- **Carte** en haut (liste groupée par lieu), avec l'adresse de sa ligne dans l'onglet Build (méthode OTA). Un esclave derrière le Range
  Extender est joint par le maître (`IP:port`), redirection posée et identité vérifiée d'abord, comme pour un envoi.
- **« Sauvegarder maintenant »** : nouvelle sauvegarde « manuelle ». Une sauvegarde « avant flash » est prise seule
  avant un envoi du firmware par câble, une « avant restauration » avant chaque restauration.
  ESP8266 (Sonoff) : Rules, timers et `Mem` sont dans la sauvegarde (Settings). Juste après la prise, la carte est
  interrogée sur ce qu'elle garde ailleurs (fichiers d'un système de fichiers, appareils Zigbee) et sur son firmware ;
  le message de la page (ou le journal, avant flash) dit ce qu'il faudrait récupérer autrement.
- **Paramètres** de la sauvegarde choisie, repliés par thème, avec un filtre (nom ou valeur). Mots de passe affichés
  `***` : laissés ainsi, ils gardent leur valeur. Une valeur changée est surlignée ; « Enregistrer la copie » écrit
  une **nouvelle** sauvegarde « modifiée », l'originale n'est jamais réécrite. La copie est relue et comparée à
  l'attendu : au moindre écart, rien n'est gardé.
- **Origine** de chaque sauvegarde : fixée par l'action qui l'a prise (« manuelle », « avant flash », « avant
  restauration », « modifiée ») et écrite dans le nom du fichier et sa fiche `.json`.
- **Supprimer** : cocher les sauvegardes dans l'historique, puis « Supprimer la sélection » (confirmation ; `.dmp` et
  fiche effacés).
- **« Comparer »** : écarts avec la carte en ligne (rien n'est enregistré) ou avec une autre sauvegarde ; les
  paramètres en écart sont mis en couleur.
- **« Restaurer : <date · origine> »** (la sauvegarde choisie d'un clic dans l'historique ; les cases servent à supprimer) : une fenêtre liste les écarts
  (paramètre, valeur sur la carte, valeur après restauration, marque « ↻ démarrage ») et alerte si le nom d'hôte de la
  carte jointe diffère ; « Restaurer » ou « Annuler » (Échap). Puis un bloc d'avancement suit les étapes du serveur
  (sauvegarde de la carte d'abord, envoi, redémarrage, relecture) et donne le résultat : sauvegarde d'avant, écarts
  relus, et ceux reposés au démarrage. Refusée pendant un envoi de la série, et pour une sauvegarde d'une autre puce.
- **À savoir** : au démarrage, le persist et l'`autoexec.bat` reposent leurs réglages ; ils l'emportent sur une
  valeur restaurée. Ces paramètres portent la marque **« ↻ démarrage »** ; son survol nomme la source et la commande
  (`autoexec.bat (SerialLog)`, `persist (Hostname)`). La marque vient de la commande Tasmota de chaque paramètre
  (decode-config) comparée aux lignes de l'`autoexec.bat` de la carte et aux commandes que `data/fs/configGlobal.be`
  pose depuis le persist (`build_sauvegarde::reposes`). Une commande de `configGlobal.be` ne compte que si le persist de
  la carte la fait poser : clé remplie, MQTT actif pour `MqttHost`/`Topic`..., voie Ethernet pour `EthIPAddress`...
  (table `build_sauvegarde::POSEES`, tenue à la main ; le banc exige une ligne par commande de `configGlobal.be`).
  Les niveaux de logs du profil actif (`SerialLog`, `WebLog`, `MqttLog`, `SysLog`) sont comptés aussi.
- **Liaison** : « HTTP (adresse) » par défaut ; **« MQTT (broker) »** pour une carte que ce PC ne joint pas en HTTP.
  La carte est jointe par le broker de `user_config_override.h` et le topic de son persist au dépôt, par les commandes
  `FileDownload` / `FileUpload` de Tasmota (`build_sauvegarde_mqtt.py`) : même fichier que `/dl`, même déroulé
  (sauvegarde d'avant, envoi, relecture une fois la carte revenue sur le broker). Le `MqttPassword` de la carte doit
  être le `MQTT_PASS` du `.h`. Essai réel du 2026-11-03 sur le différentiel : lecture en 2 s.
- **Purge automatique** (case sous l'historique, cochée par défaut, commune à toutes les cartes, mémorisée dans
  le fichier « reglages.json » du dossier des sauvegardes ; décochée, rien n'est effacé seul) : à chaque sauvegarde « avant flash » ou « avant restauration », celles de ces deux origines
  de **plus de 90 jours** sont effacées, en gardant toujours les **5 plus récentes** de chaque origine. Une sauvegarde
  « manuelle » ou « modifiée » n'est jamais effacée seule (`build_sauvegarde::purge`).
- **decode-config** (tasmota/decode-config) lit et écrit les paramètres. Il vit hors du dépôt et du Python de
  PlatformIO, dans `%LOCALAPPDATA%\outils_tasmota\decode_config\` : `python outils_docs/scripts_python/outils_pc/decode_config.py`
  l'installe (`--verifier` pour contrôler). Sans lui, sauvegarde et restauration restent possibles, pas la lecture des
  paramètres. Une version de Tasmota plus récente que la sienne n'est lisible qu'une fois sa disposition comparée
  (`decode_config.VERSIONS_VERIFIEES`) ; sinon la sauvegarde reste restaurable mais pas modifiable. Les textes
  (nom d'hôte, textes des boutons...) sont écrits par l'outil lui-même : decode-config 16.0.0.0 tronque la réserve de
  textes d'un ESP32 en les écrivant.
