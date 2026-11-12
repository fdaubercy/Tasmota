# Écran 7B de la cave : vues, commandes et veille (conception)

Date : 2026-11-12. Plan d'origine : `tasks/plans/envs-grenier-rdc-sonoff-cave.md`, action A9.
Rôles déjà en place (commit `6aba839ea`) : le serveur relais de la cave (`tasmota32s3-cave-serveur-rly`) est maître
ModBus (RS485 GPIO 18/17 et UDP) et maître du range extender ; l'écran Waveshare ESP32-S3-Touch-LCD-7B
(`tasmota32s3-cave-ecran`, dossier `data/cave/tasmota32s3-ecran`) est esclave ModBus id 1 (RS485 GPIO 16/15 et UDP),
client du point d'accès de la cave. Voir `outils_docs/PROTOCOLE_MODBUS.md` §10.

## 1. Intention

Un écran tactile posé dans la cave, à côté du serveur, pour faire sur place sans téléphone :
- allumer ou éteindre les appareils de la cave ;
- voir d'un coup d'œil l'état de la cave (température, humidité, ventilation, niveau d'eau du vide-cave) et le
  niveau de la cuve d'eau du jardin ;
- redémarrer le serveur de la cave.

L'écran est une autre carte, reliée au serveur par le câble RS485 et par le Wi-Fi du serveur. Les boutons physiques
du serveur restent en place (décision sur leur sort : hors de ce document, A9 du plan).

## 2. Ce que l'utilisateur a décidé (2026-11-12)

- Disposition « C » : mesures à gauche, grosses touches à droite, rangées en deux groupes, **Capteurs** et
  **Appareils**.
- Plusieurs pages : **Accueil**, **Graphiques T° / HR**, **Cuve et vide-cave**, **Réglages écran**.
- Appareils commandés depuis l'écran : **Lumières** (relais 3 « LED Machines », relayé au Sonoff de la porte
  `cave/lumiere`), **Lave-linge** (relais 5 « Lavage », qui alimente le lave-linge), **Pompe cuve** (relais 4),
  **Pompe vide-cave** (relais 1) : elle peut être **forcée** depuis l'écran.
- Pas de place réservée pour un sèche-linge ni pour d'autres machines pour l'instant.
- Capteurs affichés : température et humidité de la cave ; **ventilation** (relais 2) par une icône qui tourne
  quand elle marche ; **niveau d'eau du vide-cave** par ses deux flotteurs (bas et haut) ; **niveau de la cuve
  d'eau**, récupéré **par MQTT**.
- **Redémarrer le module** = redémarrer le **serveur de la cave**.
- L'aspect des touches suit l'état de l'appareil (allumé, éteint).
- Voie des données : **commandes par ModBus** (écran → serveur), **affichage par MQTT** (serveur et cuve → écran),
  avec une **alerte** visible quand l'affichage n'est plus à jour.
- **Veille** : l'écran s'éteint au bout d'un temps sans contact et se rallume au premier appui. Le code de veille
  commun (`ecranFonctions.be`, aujourd'hui dans le dossier de l'écran des débits) est **déplacé dans `data/fs`
  dans ce chantier** et sert aux deux écrans.
- Une touche envoie **l'état voulu** (marche ou arrêt), jamais une bascule ; tant que l'état affiché est grisé
  (périmé), l'appui est **refusé** avec un message « état inconnu ».
- **Pas de confirmation** pour le lave-linge (ni à l'allumage ni à l'arrêt).
- **Pompe vide-cave forcée** : un appui la met en marche, un second appui l'arrête, la minuterie de 120 s l'arrête
  aussi ; le forçage est **permis même quand les flotteurs disent « sec »**.
- **Une marche manuelle de la pompe vide-cave désactive les flotteurs jusqu'à son arrêt manuel** (écran ou bouton
  physique « Pompe Cave »). Vérifié dans le code le 2026-11-12 : ce n'est PAS le cas aujourd'hui.
  `globalFonctions.be::globalFonctions_modifEtatRelai` a un paramètre `boolCapteurs` qui désactive les capteurs du
  module au passage à ON et les réactive au passage à OFF, mais aucun appel ne le met à `true`
  (`globalFonctions_commandeRelaisLies` le force à `false`). Point d'attention : cette désactivation écrit
  `activation: OFF` dans le persist ; un redémarrage pendant une marche manuelle ne doit pas laisser les flotteurs
  désactivés. Question ouverte du constructeur : l'arrêt par la minuterie de 120 s compte-t-il comme « arrêt
  manuel » (flotteurs réactivés) ? Par défaut, oui : tout passage du relais à OFF les réactive.
- **Panne des flotteurs du vide-cave** détectée et signalée :
  - positions **inchangées depuis trop longtemps**, au sens (a) : la pompe a tourné sans que le flotteur ne
    réagisse dans un délai **réglable** (pas une alerte « rien n'a bougé depuis N jours », qui sonnerait à tort en
    été) ;
  - **flotteur haut fermé alors que le flotteur bas est ouvert** (incohérent).
- **`data/fs` peut être modifié, à condition de ne changer le comportement que pour ce module** (pompe vide-cave,
  écran de la cave) : les autres cartes qui partagent ces fichiers (garage, débits) gardent exactement leur
  comportement.

### Existant vérifié dans le code (2026-11-12)

- Relais de la pompe : minuterie de 120 s (`timer`), arrêt de sécurité par `controleGeneral.be::finTimerRelai`.
- Si le flotteur **haut** est encore fermé à la fin de la minuterie : relance après `pause` (10 s), au plus
  `maxRelances` (3) fois ; au-delà, pompe arrêtée et alerte « probable défaut du capteur (ou pompe inefficace) »
  publiée sur `topicAlerte` (`tele/cave/serveur-rly-cave-v2/ALERTE_POMPE`) et sur la page web (`relai["alerte"]`),
  effacée au cycle normal suivant (`acquitteRelance`) ou par la commande `AcquittePompe`. Clé `relance` du relai1
  de `pompeVideCave`. Cela couvre déjà le cas (a) pour le flotteur haut.
- Flotteur **bas** : `relaisLie` de type `OFF` avec un `delai` (aujourd'hui 0 s) avant la commande d'arrêt.
- À ajouter :
  - le cas (a) pour le flotteur **bas** : un arrêt par la minuterie alors que le haut est déjà retombé veut dire
    que le bas n'a pas réagi (bloqué fermé, ou pompe faible) ; alerte après un nombre réglable de cycles de ce
    genre (choix de Claude) ;
  - l'incohérence haut fermé / bas ouvert, alerte immédiate (après un court anti-rebond) ;
  - ces alertes dans le JSON du serveur (lu par l'écran) et sur la même voie que `ALERTE_POMPE`.

## 3. Choix de Claude (à relire)

- Navigation par un **menu ☰** en haut à gauche, qui ouvre une fenêtre par-dessus la page (liste des pages et
  « Redémarrer le serveur ») ; l'utilisateur n'a pas tranché entre ce menu et une page « Menu » en tuiles.
- Un appui est **gardé par l'écran jusqu'à ce que le serveur l'ait pris en compte** (état du relais relu), pour
  qu'un push UDP perdu ne soit pas rattrapé de travers par le relevé RS485.
- La pompe vide-cave et la ventilation gardent leur automatisme ; la touche « Pompe vide-cave » porte la mention
  « auto ».
- La ventilation est affichée, pas commandée (non demandé).
- Vide-cave : trois états lus des deux flotteurs, « sec » (aucun), « entre les deux » (bas seul), « plein » (haut) ;
  l'incohérence (haut sans bas) est affichée comme une **panne**, pas comme un niveau.
- Où vit la détection de panne des flotteurs : sur le **serveur de la cave** (il lit les flotteurs et commande la
  pompe ; l'alerte doit exister écran éteint ou absent), publiée dans son JSON et affichée par l'écran.
- Cuve : pourcentage en jauge et volume en litres, si le message de la cuve les porte.
- Données périmées : une valeur non rafraîchie depuis plus de 3 × la période de télémétrie de sa source est grisée,
  et l'horloge de la barre du haut est barrée tant que le broker MQTT n'est pas joint.
- Redémarrage : fenêtre de confirmation à deux touches (« Redémarrer » / « Annuler ») ; jamais d'action sur un
  seul appui.

## 4. Fonctionnement attendu

### 4.1 Commande (écran → serveur), par ModBus

- Chaque touche d'appareil et l'ordre de redémarrage sont des **boutons virtuels de l'esclave** (bloc
  `modules.ecranCave` du persist de l'écran, réservé à cet usage), poussés au maître par le push UDP existant
  (`modbusFonctions.be::pousseEtat`) et lus aussi au relevé RS485 du maître quand le Wi-Fi manque.
- Côté maître, la réception d'un bouton d'esclave existe déjà (`modBus_TasmotaSlaveModBus.be`, branche `boutons`) :
  elle met l'état à jour mais **n'agit pas**. À ajouter : une **table dans le persist de la cave** qui associe
  « esclave id 1, bouton n » à une action (« basculer le relais m », « redémarrer »), et l'appel de cette action
  sur le modèle de `vrFonctions.capteurVirtuel` pour les interrupteurs.
- Une action ne part que sur un **appui** (front montant), jamais sur un état lu au démarrage ni au relevé
  périodique d'un état inchangé : un redémarrage du maître ou de l'écran ne doit rien commuter.
- `TasmotaSlaveModBus1` « ECRAN-CAVE » de la cave passe à ON au flash de l'écran (décision du 2026-11-12).

### 4.2 Affichage (serveur et cuve → écran), par MQTT

- Source cave : topic du serveur de la cave (aujourd'hui `cave/serveur-rly-cave-v2`, identité d'essai ; il changera
  au retour en production, A7) : état des relais 1 à 5, température et humidité (AM2301), flotteurs du vide-cave.
- Source cuve : carte `jardin/cuve`, clé `sensorsCuve` de `tele/jardin/cuve/SENSOR` (`controleCuve.be::json_append`).
- Les topics sont **lus dans le persist de l'écran**, jamais écrits en dur.
- L'écran passe par le point d'accès de la cave puis le NAPT du serveur pour joindre le broker.

### 4.3 Veille

- Après un délai sans contact (réglable, page Réglages écran), la dalle s'éteint (rétroéclairage coupé par
  l'expandeur 0x24).
- Le premier appui sur l'écran éteint **rallume seulement** : il ne déclenche aucune touche.
- Repartir du générique de l'écran des débits (`ecranFonctions.be` : veille, extinction, luminosité ; plan
  `debits-deux-cartes` A8), sans le recopier si on peut le partager.

## 5. Contraintes

- Règles du dépôt (`CLAUDE.md`) : charte des logs Berry, modules solidifiés, `banc_demarrage.py`, compilation par la
  page Build. `data/fs` : accord donné le 2026-11-12 pour `modBus_TasmotaSlaveModBus.be` (appel à la réception d'un
  bouton d'esclave), `globalFonctions.be` (flotteurs désactivés pendant une marche manuelle) et `ecranFonctions.be`
  (déplacé), **sans changer le comportement des autres cartes** : tout nouveau comportement est conditionné par une
  clé du persist absente ailleurs ; bancs du garage et des débits relancés, instantanés de `banc_demarrage.py`
  inchangés pour elles.
- Écran S3 avec PSRAM : RAM interne à surveiller (LVGL / HASPmota).
- Interface d'écran : HASPmota comme l'écran des débits (`custom_interface_ecran = haspmota`), sauf raison
  contraire trouvée au plan ; l'atelier des écrans (`atelier_ecrans_haspmota.py`) peut générer les pages.
- Rien n'est essayé sur carte tant que l'écran n'est pas branché : bancs PC et rendu d'abord.

## 6. Non-objectifs

- Sèche-linge, lave-vaisselle, prises connectées des machines.
- Commande de la ventilation.
- Retrait des boutons physiques du serveur.
- Affichage passant par ModBus (le maître qui écrit ses états dans l'esclave) : écarté au profit de MQTT.

## 7. Anti-objectifs (échec même si « ça marche »)

- Un relais qui commute seul au démarrage du maître ou de l'écran, ou au réveil de l'écran.
- Un redémarrage du serveur sur un appui accidentel.
- Un affichage figé qui a l'air à jour.

## 8. Laissé au constructeur

- Format exact de la table d'actions du maître, et nom de sa clé dans le persist.
- Numérotation des boutons virtuels de l'écran et registres ModBus correspondants.
- Clés exactes du JSON MQTT lues pour chaque valeur ; abonnement (`mqtt.subscribe` Berry ou autre).
- Délais par défaut (veille, péremption), découpage des pages HASPmota, icônes.
- Contenu de la page Graphiques (courbes T° / HR) : source et durée.
