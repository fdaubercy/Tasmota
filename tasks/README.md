# Suivi des plans de travail

Trace des plans de modification du fork (`tasks/plans/`, format `tasks/plans/_FORMAT.md`).
Avancement = moyenne des % des actions `## A<n>`, chaque action pesant autant (même calcul que la
vue « Suivi du plan » de VS Code). L'objectif vient de la clé `objectif:` de l'en-tête de chaque plan.

Le tableau se met à jour seul dès qu'un plan change, quel qu'en soit l'auteur (Claude, la main, le mod à
la validation d'un plan), tant que VS Code est ouvert (extension « Suivi du plan » ≥ 0.4.1), et quand Claude
édite un plan (hook `.claude/hooks/index_plans_edition.sh`). À la main : `node .claude/hooks/index_plans.mjs`
(`--verifier` : code 1 s'il est en retard).

## Plans suivis

<!-- debut-index-plans : bloc regenere par .claude/hooks/index_plans.mjs, ne pas editer -->

45 plans : 19 actif, 1 en-pause, 25 clos.

| Plan | Objectif principal | Statut | Avancement | Reste à faire | Créé | Mis à jour |
|---|---|---|---|---|---|---|
| [Deux envs, serveur du grenier du RDC (volets) et Sonoff de la porte de la cave ; identité de la cave S3](plans/envs-grenier-rdc-sonoff-cave.md) | Paramétrer deux environnements, la carte Waveshare 8DI-8RO du grenier du rez-de-chaussée qui commande les volets et le Sonoff ESP8285 de la porte de la cave, préparer le retour en production de la cave S3, lui ajouter l'écran 7B et en faire le maître range extender du Sonoff ; ajouter la pompe de la piscine (192.168.0.40) le projecteur du jardin (192.168.0.41) et celui du barbecue : sauvegarde, env, mise en service | actif | ████░░░░░░ 41 % (42/94) | 52 étapes, 3 améliorations | 2026-11-11 | 2026-11-12 (A17 : env du NOUS créé et adapté, mesure vérifiée, compilation lancée) |
| [Atelier des écrans (page 7960) : une description d'écran, deux interfaces générées](plans/atelier-ecrans.md) | Modifier sur le PC la disposition d'un écran tactile de carte (objets, boutons, pages) et y épingler des remarques, puis générer de la même description le pages.jsonl de HASPmota et le code LVGL pur en Berry | actif | ███████░░░ 67 % (36/63) | 27 étapes, 1 amélioration | 2026-11-11 | 2026-11-12 (A11 livraison regroupée ; A12 à A15 : quatre améliorations) |
| [Écran 7B de la cave, vues, commandes par ModBus, affichage par MQTT, veille et pannes des flotteurs](plans/ecran-cave-vues-commandes.md) | Commander les appareils de la cave et voir son état sur l'écran 7B esclave, sans rien changer au comportement des autres cartes | actif | █████░░░░░ 52 % (19/40) | 21 étapes, 3 améliorations | 2026-11-12 | 2026-11-12 |
| [Étiquettes QR code des cartes (page 7970) : impression, page de la carte, écran](plans/etiquettes-qrcode.md) | Composer par env un QR code stylé qui affiche l identité de la carte (hostname, IP, clés du persist), l imprimer en étiquette ou en planche A4, l afficher sur une page de la carte et sur son écran, et signaler quand il est périmé | actif | ██████░░░░ 60 % (28/50) | 22 étapes | 2026-11-12 | 2026-11-12 |
| [Visuel des volets sur la page d'accueil et réglage des durées par les boutons](plans/visuel-reglage-volets.md) | Dessiner sous les curseurs des volets une façade dont les tabliers suivent la position réelle en direct, et régler tempsMontee et tempsDescente depuis la page Configuration avec les boutons existants | actif | ████████░░ 79 % (38/46) | 8 étapes, 1 amélioration | 2026-11-11 | 2026-11-12 |
| [Débits de la nourrice sur deux cartes, acquisition esclave et affichage maître](plans/debits-deux-cartes.md) | Faire passer les 6 débits de la carte d'acquisition (esclave ModBus id 1) à une carte d'affichage (maître id 0) par une lecture groupée RS485 et un push UDP, sans rien changer au garage | actif | ██████░░░░ 62 % (33/49) | 16 étapes, 3 améliorations | 2026-11-09 | 2026-11-11 |
| [Mesure des 6 débits de la nourrice de chauffage, écran TFT et page web](plans/debitmetres-chauffage.md) | Mesurer et afficher les débits des 6 départs de radiateur avec un ESP32-S3 Tasmota, sans gêner l'écran | actif | ███████░░░ 68 % (35/50) | 15 étapes, 4 améliorations | 2026-11-08 | 2026-11-09 |
| [Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie » (disposition B)](plans/energie-differentiel.md) | Passer le différentiel sur le firmware du fork sans perdre calibrage, compteur ni minuteries, et lui donner une page Énergie (kWh par heure/jour/mois, coût, puissance 24 h) | actif | ██████████ 100 % (69/70) | 1 étape | 2026-10-31 | 2026-11-09 |
| [Page d'équilibrage de la nourrice servie par la carte des débits, débits lus en direct](plans/equilibrage-par-la-carte.md) | Ouvrir le guide d'équilibrage depuis la carte des débits et y lire les 6 débits mesurés, sans les taper à la main | actif | ████████░░ 83 % (20/22) | 2 étapes | 2026-11-09 | 2026-11-09 |
| [Historique et page /graphiques des 6 débits de la nourrice](plans/historique-debits.md) | Garder en flash l'historique des 6 débits et du total, et les voir en courbes sur la page /graphiques de la carte | actif | ████████░░ 75 % (8/10) | 2 étapes, 1 amélioration | 2026-11-08 | 2026-11-09 |
| [Page dédiée « Niveau de la cuve » (jauges A, H et B), lien depuis l'encadré de la cuve](plans/jauges-cuve.md) | Afficher volume (jauge A), taux (jauge H) et tensions brute et recalculée de la sonde (cadran B) de la cuve sur une page dédiée ouverte depuis son encadré, sur la cuve et le P4 | actif | ██████████ 98 % (31/32) | 1 étape, 1 amélioration | 2026-10-31 | 2026-11-09 |
| [Page web « Build et téléversement » (port 7700, tuile de l'annuaire)](plans/page-build-televersement.md) | Compiler et téléverser en série (COM ou OTA) les envs cochés depuis une page web, avec progression en direct | actif | ██████████ 100 % (89/89) | 2 améliorations | 2026-10-24 | 2026-11-09 |
| [Voie Ethernet complète — FTP, UDP, esclaves par le point d'accès, repli sur le Wi-Fi](plans/voie-reseau-ethernet.md) | Qu'une carte en voie Ethernet garde tous ses services et ses esclaves, et ne devienne jamais injoignable si le câble tombe | actif | █████░░░░░ 47 % (18/33) | 15 étapes, 1 amélioration | 2026-11-02 | 2026-11-08 |
| [Onglet « Sauvegarde configuration » de la page build (modèle B)](plans/sauvegarde-config-cartes.md) | Sauvegarder, comparer, modifier paramètre par paramètre et restaurer la configuration (/dl : Settings + .drvset*) de chaque carte depuis la page build | actif | ██████████ 100 % (33/33) | — | 2026-11-03 | 2026-11-03 |
| [Ruban WS2812 de la cuve en AUTO/MANUEL et carte cuve v0.2](plans/ruban-cuve.md) | Piloter le ruban WS2812 de la cuve en AUTO/MANUEL (bouton et ModBus) et préparer la carte cuve v0.2 | actif | ████████░░ 77 % (23/31) | 8 étapes, 2 améliorations | 2026-10-18 | 2026-11-02 |
| [Cave — envs ESP32/S3 alignés sur la carte en ligne, audit de l'env S3, carte S3 8 relais de remplacement](plans/relais-cave-s3.md) | Aligner les envs de la cave sur les broches de la carte en ligne, auditer l'env S3 et choisir une carte ESP32-S3 à 8 relais pour la remplacer | actif | ████████░░ 80 % (17/19) | 2 étapes, 3 améliorations | 2026-10-31 | 2026-10-31 |
| [Sniffeur I2C (ESP32-S3 dédié + outil PC de l'annuaire)](plans/sniffeur-i2c.md) | Voir en direct le trafic I2C de n'importe quelle carte du parc, décodé jusqu'au registre, et lire ou écrire un registre par la carte ou au banc | actif | ███████░░░ 72 % (33/43) | 10 étapes, 1 amélioration | 2026-10-31 | 2026-10-31 |
| [Plan d'action de l'audit Berry (propositions P2.1 à P10.7)](plans/actions-audit-berry.md) | Mettre en œuvre, lot par lot et sur décision de l'utilisateur, les 78 propositions de l'audit Berry | actif | █████████░ 91 % (89/95) | 6 étapes, 1 amélioration | 2026-10-22 | 2026-10-26 |
| [Ethernet en option sur le maître ModBus P4 (SERVEUR-GARAGE)](plans/ethernet-p4.md) | Ajouter l'Ethernet en option sur le maître ModBus P4, le Wi-Fi restant le défaut | actif | ░░░░░░░░░░ 0 % (0/37) | 37 étapes, 1 amélioration | 2026-10-26 | 2026-10-26 |
| [Suites de l'audit de l'env S3 du serveur relais de la cave](plans/audit-relais-cave-s3.md) | Rendre l'env tasmota32s3-cave-serveur-rly prêt à remplacer la carte de la cave en ligne, selon les propositions de l'audit | en-pause | ░░░░░░░░░░ 0 % (0/22) | 22 étapes, 2 améliorations | 2026-10-31 | 2026-10-31 |
| [Classement des cartes par lieu dans les pages des outils PC](plans/classement-par-lieu.md) | Retrouver les cartes par emplacement dans la maison sur la page Build (bascule Famille/Lieu/Puce, intertitres de l'onglet Fichiers) et dans les listes de carte des autres pages | clos | ██████████ 100 % (21/21) | — | 2026-11-10 | 2026-11-11 |
| [Lieu partagé depuis l'annuaire, lieu dans le syslog et le sniffeur MQTT](plans/lieu-partage-syslog-mqtt.md) | Choisir un lieu une fois dans l'annuaire et le retrouver dans les pages ouvertes, et ranger par lieu les lignes du syslog et les messages du sniffeur MQTT | clos | ██████████ 100 % (26/26) | — | 2026-11-11 | 2026-11-11 |
| [Atelier des graphiques (page 7950) et moteur commun des pages de graphiques](plans/atelier-graphiques.md) | Préparer sur le PC un graphique pour une carte, le voir avec ses vraies valeurs, puis écrire dans le dépôt la description qui le fait apparaître sur la carte, sans Berry écrit à la main | clos | ██████████ 100 % (39/39) | — | 2026-11-03 | 2026-11-09 |
| [Onglet « autoexec.bat » de l'Assistant persist (modèle C)](plans/autoexec-bat.md) | Modifier ou ajouter des lignes à l'autoexec.bat d'une carte depuis l'Assistant persist, avec banque de commandes, avertissements (boucle de redémarrage, doublon persist, secret, commande inconnue) et envoi proposé à la carte | clos | ██████████ 100 % (21/21) | — | 2026-11-03 | 2026-11-09 |
| [Envoi MQTT de l'autoexec.bat, commandes par carte, extensions .tapp (document, script, page)](plans/autoexec-mqtt-tapp.md) | Envoyer l'autoexec.bat par MQTT, signaler une commande non compilée pour la carte, et savoir fabriquer un .tapp (document, script, page de l'annuaire) | clos | ██████████ 100 % (21/21) | — | 2026-11-05 | 2026-11-09 |
| [Atelier des graphiques — page « Énergie » du différentiel (palier 4)](plans/energie-atelier.md) | Que l'atelier reprenne et modifie la page /energie du différentiel (ajouter, restyler, échelle de temps, déplacer, taille) puis l'envoie par Téléverser, sans toucher au comptage | clos | ██████████ 100 % (24/24) | — | 2026-11-08 | 2026-11-09 |
| [Atelier des graphiques — destination « Graphiques » et bouton « Téléverser »](plans/atelier-destinations.md) | Poser un graphique de l'atelier sur une page dédiée, sur /graphiques ou sur une nouvelle page, puis l'envoyer à la carte par la page Build qui prépare tout et attend le clic Envoyer | clos | ██████████ 96 % (40/41) | 1 étape | 2026-11-04 | 2026-11-08 |
| [Env S3 relais cave adapté à la carte Waveshare ESP32-S3-ETH-8DI-8RO](plans/cave-s3-waveshare.md) | Faire tourner les entrées-sorties actuelles du persist de la cave S3 sur la carte Waveshare 8DI-8RO, relais par le TCA9554 | clos | ██████████ 100 % (17/17) | 5 améliorations | 2026-10-31 | 2026-11-02 |
| [lib_ignore pour chaque env personnel, avec garde au pre-build](plans/lib-ignore-envs.md) | Etendre a tous les envs personnels le lib_ignore valide sur la cuve, chaque liste etablie et controlee par un script avant le scan des dependances | clos | ██████████ 100 % (17/17) | 2 améliorations | 2026-10-31 | 2026-11-02 |
| [Réduire le temps des compilations et éviter les recompilations complètes](plans/temps-compilation.md) | Ne plus recompiler tasmota.ino.cpp ni purger .pio/build sans raison, mesurer avant de séparer les dossiers de build par env, puis montrer l'occupation mémoire et régler les partitions depuis la page build | clos | ██████████ 100 % (57/57) | 1 amélioration | 2026-11-01 | 2026-11-02 |
| [Modifier default_envs depuis la page Build](plans/default-envs-page.md) | Choisir sur la page Build les envs compilés par un simple pio run, sans ouvrir platformio_override.ini | clos | ██████████ 100 % (17/17) | — | 2026-11-01 | 2026-11-01 |
| [Accélérer le scan des dépendances (LDF) — essai lib_ignore sur l'env de la cuve](plans/lib-ignore-cuve.md) | Réduire le temps du scan LDF et de la compilation de l'env cuve en ignorant les bibliothèques qu'il n'utilise pas, mesuré avant et après | clos | ██████████ 100 % (19/19) | 1 amélioration | 2026-10-31 | 2026-11-01 |
| [Assistant persist — reprendre, modifier et supprimer un env existant (A10)](plans/assistant-persist-modification.md) | Reprendre un env existant dans la page 7900 pour le modifier sans perdre ses retouches, ou le supprimer après vérification | clos | ██████████ 100 % (38/38) | 2 améliorations | 2026-10-29 | 2026-10-30 |
| [Assistant de création du persist d'un nouvel env (page 7900, tuile de l'annuaire)](plans/assistant-persist.md) | Créer le persist, l'autoexec et les sections de build d'une nouvelle carte par questions, depuis une page web | clos | ██████████ 100 % (47/47) | — | 2026-10-27 | 2026-10-30 |
| [Assistant pas à pas de la page « Synchro du fork » (port 7500)](plans/assistant-synchro-fork.md) | Guider pas à pas la synchro du fork sur la page 7500, avec résolution des conflits fichier par fichier | clos | ██████████ 100 % (33/33) | — | 2026-10-27 | 2026-10-29 |
| [Détection de blocage d'un volet par son inclinaison (MPU6050)](plans/blocage-trappe-mpu6050.md) | Arrêter un volet et loguer une erreur quand son inclinaison ne bouge plus pendant la course (trappe bloquée) | clos | ██████████ 100 % (29/29) | 3 améliorations | 2026-10-28 | 2026-10-29 |
| [Capteur d'inclinaison MPU6050 pour les volets (trappe du grenier)](plans/inclinaison-trappe-mpu6050.md) | Lire l'angle réel de la trappe du grenier par un MPU6050 pour recaler la position du volet | clos | ██████████ 100 % (28/28) | 3 améliorations | 2026-10-28 | 2026-10-28 |
| [Alerte web « firmware du coprocesseur ESP32-C6 pas à jour » sur les P4](plans/alerte-firmware-c6.md) | Signaler sur les P4 un firmware du coprocesseur Wi-Fi ESP32-C6 en retard et proposer sa mise à jour (HostedOta) | clos | ██████████ 100 % (34/34) | — | 2026-10-26 | 2026-10-27 |
| [Page web « Fichiers Berry par env » (port 7800, tuile de l'annuaire, cible Custom)](plans/fichiers-berry-env.md) | Régler par une page web l'état de chaque fichier Berry par env (FS, exclu, solidifié) et créer un env | clos | ██████████ 100 % (31/31) | 1 amélioration | 2026-10-25 | 2026-10-25 |
| [Page « Fichiers Berry par env » — supprimer et renommer un env, écritures atomiques, sauvegardes, erreurs claires](plans/fichiers-berry-suppression.md) | Supprimer et renommer un env depuis la page Fichiers Berry, avec écritures atomiques et sauvegardes | clos | ██████████ 100 % (31/31) | — | 2026-10-25 | 2026-10-25 |
| [Audit complet — scripts Berry, environnements de build, solidification, logs et communications](plans/audit-berry.md) | Auditer en lecture seule le code Berry, les envs de build, la solidification, les logs et les communications | clos | ██████████ 100 % (77/77) | 2 améliorations | 2026-10-21 | 2026-10-22 |
| [ModBus du garage (P4, cuve, rideau) et commandes sans fil](plans/modbus-garage.md) | Fiabiliser le ModBus filaire du garage (P4, cuve, rideau) puis passer les commandes par UDP | clos | ██████████ 100 % (20/20) | 1 amélioration | — | 2026-10-22 |
| [Graphiques des mesures dans les pages web des cartes S3/P4 (uPlot)](plans/graphiques-web.md) | Afficher l'historique et le temps réel des mesures en graphiques dans les pages web des cartes S3/P4 | clos | ██████████ 100 % (80/80) | — | 2026-10-18 | 2026-10-20 |
| [La vue de droite suit le plan de la conversation active](plans/plan-par-conversation.md) | Faire afficher par la vue de droite le plan suivi par la conversation Claude active | clos | ██████████ 100 % (20/20) | — | 2026-10-18 | 2026-10-18 |
| [Suivi des plans de travail (extension VS Code + mod)](plans/suivi-plan.md) | Suivre l'avancement des plans en % dans une vue VS Code à droite, partagée entre conversations et postes | clos | ██████████ 100 % (23/23) | 5 améliorations | 2026-10-18 | 2026-10-18 |

### Points restants des plans non terminés

#### [Deux envs, serveur du grenier du RDC (volets) et Sonoff de la porte de la cave ; identité de la cave S3](plans/envs-grenier-rdc-sonoff-cave.md) — 41 %

- A3 — Brochage et volets : Relais CH1-CH4 par le TCA9554 (`tca9554.dat` du dossier de la carte), interverrouillage montée/descente par volet. Fait en A2 sur le papier (CH1-CH6, `Interlock 1,2 3,4 5,6` corrigé dans `vrFonctions.be`) : à cocher après l'essai à vide sur la carte.
- A3 — Brochage et volets : Boutons DI1-DI4, DHT22 sur GPIO21 ; classeur `Brochage GPIO - tasmota32s3-rdc-grenier.xlsx` par
- A3 — Brochage et volets : Durées d'ouverture et de fermeture du volet de la porte reprises du Sonoff Dual R3 (lecture seule de .46 :
- A4 — Identification des volets sur MQTT : Faire valider par l'utilisateur la réponse du Contexte (volets natifs Shutter1/Shutter2 sous `rdc/grenier`, noms,
- A4 — Identification des volets sur MQTT : Recenser ce qui vise `volet/entree` aujourd'hui (Node-RED du Pi, Alexa, Home Assistant) et la liste des
- A5 — Compilation et mise en service : Compilation par la page Build (:7700), SUCCESS lu en fin de journal, taille de l'image et du FS.
- A5 — Compilation et mise en service : À la réception de la carte : flash série, `Status 5`, volets en marche à vide (relais seuls), puis moteur recâblé.
- A5 — Compilation et mise en service : Sonoff Dual R3 (.46) éteint et retiré AVANT la mise sous tension du grenier (même IP .46) ; automatisations basculées ; env `tasmota32-rdc-vr-porte` gardé ou
- A6 — Cave S3 : identité d'essai : Reprendre les améliorations restantes du plan `cave-s3-waveshare` (compilation, port COM, câblage DI3/DI4,
- A7 — Retour en production de la cave S3 : Le jour du remplacement, sur ordre de l'utilisateur : passer l'identité de la cave S3 à 192.168.0.48 et
- A7 — Retour en production de la cave S3 : Ancienne carte ESP32 éteinte AVANT la mise sous tension de la S3 (même IP, même client MQTT).
- A7 — Retour en production de la cave S3 : Contrôle : Node-RED, Telegram et le Sonoff .45 (A8) voient la cave comme avant ; `lieux.py` range ses messages
- A8 — Sonoff ESP8285 de la porte de la cave, lumières de la cave (192.168.0.45) : Réglages du Sonoff par `Backlog` et `Rule` en console seulement (pas d'`autoexec.bat` possible), proposés puis
- A9 — Écran Waveshare 7B pour le serveur relais de la cave : Dépend du plan `debits-deux-cartes` A8 : le code d'écran générique (`ecranFonctions`, veille, luminosité, polices)
- A9 — Écran Waveshare 7B pour le serveur relais de la cave : Maquette des vues de la cave (lumières, relais, température et humidité, pompe) proposée puis validée par
- A9 — Écran Waveshare 7B pour le serveur relais de la cave : Boutons physiques du serveur de la cave remplacés par ceux de l'écran ? (idée de l'utilisateur, 2026-11-11). À
- A9 — Écran Waveshare 7B pour le serveur relais de la cave : `banc_demarrage.py`, `verifie_berry.py`, agent `relecteur-berry`, compilation par la page Build ; essai sur carte.
- A10 — Range extender maître sur la cave S3 : Ports d'accès aux esclaves : `<ip cave>:<8080 + id - 1>` par `RoutageRangeExtender` ; id réservé pour l'écran 7B
- A10 — Range extender maître sur la cave S3 : Le point d'accès exige le Wi-Fi : la voie Ethernet (A6, améliorations) ne doit pas le couper.
- A10 — Range extender maître sur la cave S3 : `banc_demarrage.py` ; compilation par la page Build ; essai sur carte (AP visible, NAPT : un client du point
- A11 — Lien MQTT entre la porte de la cave et le serveur de la cave, garde-fou contre l'écho : Faire valider le garde-fou et la table des relais (Sonoff : `POWER1` lumière, `POWER2` porte ; serveur : `POWER3`
- A11 — Lien MQTT entre la porte de la cave et le serveur de la cave, garde-fou contre l'écho : Vérifier sur le Tasmota 12.0.2 du Sonoff qu'un déclencheur compare bien à `%var1%` (`Power1#State!=%var1%`) :
- A11 — Lien MQTT entre la porte de la cave et le serveur de la cave, garde-fou contre l'écho : Sonoff : retirer de la Rule1 les deux règles `Power1#State` qui publient `POWER3` (la Rule1 garde le bouton, la
- A11 — Lien MQTT entre la porte de la cave et le serveur de la cave, garde-fou contre l'écho : Essai, avec preuve dans le sniffeur MQTT (:7100) : allumage depuis la porte, depuis la cave (bouton, puis écran si
- A12 — Visuel des volets sur la page d'accueil (toutes les cartes à volets) : Réalisation, bancs, sondes, essais sur carte : par A14 (plan dédié)
- A13 — Réglage des durées de montée et de descente par les boutons : Réalisation, bancs, essais sur carte : par A14 (plan dédié)
- A14 — Réaliser le visuel et le réglage des durées (plan dédié `visuel-reglage-volets`) : Taper `/suivi suivre visuel-reglage-volets` et exécuter ce plan de A1 à sa dernière action
- A14 — Réaliser le visuel et le réglage des durées (plan dédié `visuel-reglage-volets`) : Plan `visuel-reglage-volets` clos (100 %, `statut: clos`), puis retour ici : cocher les étapes restantes d'A12 et d'A13
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : Aucun fichier de FS ajouté à la compilation ni à l'envoi (demande de l'utilisateur) : pas de pré-script ni de
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : `config_decodee.json` est dans le dossier de la carte (choix de l'utilisateur) : il ne doit jamais partir en flash.
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : Taille de l'image comparée au 1 Mo ; mise à jour en OTA (tasmota.bin ~620 Ko ne tient pas à côté de l'ancien) :
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : Essai réel sur .45 puis .42, avec l'accord de l'utilisateur : sauvegarde, copie modifiée (un texte, une Rule),
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : Classement par lieu des messages : `lieux.py::identites` ne lit que les persists ; sans persist, ces cartes ne sont
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : Lien avec les autres cartes : MQTT et Rules seulement (A11 pour la porte) ; la discovery Berry est impossible.
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : Timers de la TV (demande de l'utilisateur, 2026-11-12 : « il faut sauvegarder les timers ») : 1 à 9 armés, tous les
- A15 — Modules ESP8266/ESP8285 sans Berry (1 Mo) : questions et essais : Langue (anglais aujourd'hui) et version : passer en français et à jour ? Décision de l'utilisateur, taille à vérifier.
- A16 — Pompe de la piscine (192.168.0.40) : sauvegarde, env, mise en service : Faire dire par l'utilisateur pourquoi la carte est muette (éteinte pour l'hiver, prise coupée, répéteur KuWFi
- A16 — Pompe de la piscine (192.168.0.40) : sauvegarde, env, mise en service : Sauvegarde par l'onglet « Sauvegarde configuration » (HTTP ; MQTT masqué pour un ESP8266), page Build redémarrée
- A16 — Pompe de la piscine (192.168.0.40) : sauvegarde, env, mise en service : Relevé de la carte en lecture seule : `Status 0`, `Template`, `Module`, `GPIO`, `Timers`, `Rule1` à `Rule3`, `Emulation`,
- A16 — Pompe de la piscine (192.168.0.40) : sauvegarde, env, mise en service : Compilation par la page Build (:7700), SUCCESS lu en fin de journal, taille de l'image comparée au 1 Mo (les deux
- A16 — Pompe de la piscine (192.168.0.40) : sauvegarde, env, mise en service : Recenser ce qui vise `jardin/pompe_piscine` (Node-RED du Pi, Alexa par l'émulation, Home Assistant, Telegram) avant
- A16 — Pompe de la piscine (192.168.0.40) : sauvegarde, env, mise en service : Mise en service, avec l'accord de l'utilisateur : sauvegarde « avant flash », envoi, `Status 0`, timers et Rules relus,
- A17 — Projecteur du jardin (192.168.0.41) : sauvegarde, env, mise en service : Contrôle de faisabilité AVANT l'env : aucun ESP32 classique du dépôt ne compile `USE_WIFI_RANGE_EXTENDER` (S3 de la
- A17 — Projecteur du jardin (192.168.0.41) : sauvegarde, env, mise en service : Sauvegarde par l'onglet « Sauvegarde configuration » (HTTP), page Build redémarrée avant ; `/_persist.json` de la
- A17 — Projecteur du jardin (192.168.0.41) : sauvegarde, env, mise en service : `.dmp` décodé en `config_decodee.json` (mots de passe masqués), comme .42 et .45 ; template « NOUS B2T » vérifié
- A17 — Projecteur du jardin (192.168.0.41) : sauvegarde, env, mise en service : Compilation par la page Build (:7700), SUCCESS lu en fin de journal, taille comparée à la partition de 4 Mo.
- A17 — Projecteur du jardin (192.168.0.41) : sauvegarde, env, mise en service : Recenser ce qui vise `jardin/projecteur_led` (Node-RED, Alexa, Home Assistant) avant tout changement d'identité.
- A17 — Projecteur du jardin (192.168.0.41) : sauvegarde, env, mise en service : Mise en service, avec l'accord de l'utilisateur : sauvegarde « avant flash », envoi (OTA possible sur 4 Mo),
- A18 — Projecteur du barbecue : copie de l'env du NOUS du jardin (A17) : À la réception (firmware d'origine du vendeur, Tasmota ou Tuya ?) : connexion au point d'accès de la carte,
- A18 — Projecteur du barbecue : copie de l'env du NOUS du jardin (A17) : Env créé par copie du NOUS du jardin (diff montré, accord de l'utilisateur), hors build en cours ; `test_lieux.py`,
- A18 — Projecteur du barbecue : copie de l'env du NOUS du jardin (A17) : Compilation par la page Build, SUCCESS lu en fin de journal.
- A18 — Projecteur du barbecue : copie de l'env du NOUS du jardin (A17) : Mise en service, avec l'accord de l'utilisateur : sauvegarde « avant flash », envoi, `Status 0`, relais commandé une
- Amélioration [projet] : Ethernet W5500 de la carte du grenier du RDC (`ReglageGlobal VoieReseau ethernet`) si un câble arrive au grenier.
- Amélioration [projet] : Alias Berry lisible par volet (`VoletPorte`, `VoletCuisine`) si l'utilisateur le veut (A4).
- Amélioration [projet] : Resynchroniser les deux lampes de la cave à la reconnexion MQTT d'une des cartes (`Mqtt#Connected`).

#### [Atelier des écrans (page 7960) : une description d'écran, deux interfaces générées](plans/atelier-ecrans.md) — 67 %

- A11 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur) : [utilisateur] Carte d'affichage joignable : 192.168.0.51 muette depuis le 2026-11-12 (alimentation, Wi-Fi ; avec
- A11 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur) : Firmware de la carte postérieur à 5c3291884 (`ecranFonctions.be` déplacé dans `data/fs`) : `Status 2` comparé à la
- A11 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur) : [utilisateur] Essai : un bouton ajouté à l'écran des débits dans l'atelier, généré dans les deux interfaces, écrit
- A11 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur) : Capture réelle depuis l'atelier (« Capture de la carte ») : image identique à l'écran, mémoire PSRAM prise par
- A11 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur) : Commit des fichiers de l'essai (description, interfaces générées, remarques éventuelles)
- A11 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur) : [utilisateur] Vue de droite : taper `/suivi suivre debits-deux-cartes` puis `/suivi suivre atelier-ecrans` ; à cocher
- A11 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur) : Retour au plan `debits-deux-cartes` : cocher son action A9 avec la preuve de l'essai, passer ce plan en `statut: clos`
- A12 — Écrans des autres cartes au catalogue : Banc d'abord (rouge) : trois sources (cartes, `outils_docs/atelier_ecrans/display/`, `tasmota/displaydesc/`) ;
- A12 — Écrans des autres cartes au catalogue : `atelier_ecrans_catalogue.py` (sources, clés, champs `source`, `fichier`, `bus`, `bpp`, `couleur`) ; catalogue
- A12 — Écrans des autres cartes au catalogue : Changement d'écran (A8) : `display.ini` repris de la source de l'écran (carte, bibliothèque ou amont) ; bancs
- A12 — Écrans des autres cartes au catalogue : Commit
- A15 — Onglet « display.ini » : lire, expliquer, valider, créer : Référence `outils_docs/schemas/display_ini_parametres.json` (sections, arguments, bases, ordre, pièges, sources) ;
- A15 — Onglet « display.ini » : lire, expliquer, valider, créer : Analyseur et contrôles du § 6.4 (`atelier_ecrans_display.py`) : banc d'abord (rouge) sur les trois `display.ini` du
- A15 — Onglet « display.ini » : lire, expliquer, valider, créer : Routes (liste, lecture expliquée, diff, enregistrement dans la bibliothèque, copie depuis l'amont, notes) ; refus
- A15 — Onglet « display.ini » : lire, expliquer, valider, créer : Onglet de la page : liste des fichiers, éditeur ligne par ligne expliqué, panneau « Paramètres » avec « Ajouter » à la
- A15 — Onglet « display.ini » : lire, expliquer, valider, créer : « Appliquer à la carte » par le chemin du changement d'écran (diff, broches du persist, lien page Build)
- A15 — Onglet « display.ini » : lire, expliquer, valider, créer : Essai sur la carte (192.168.0.51 joignable) : envoi du `display.ini`, `DisplayReinit` ou `Restart 1`, « Garder » /
- A15 — Onglet « display.ini » : lire, expliquer, valider, créer : Mode d'emploi (`outils_docs/README.md`), carte des documents du `CLAUDE.md` ; commit
- A13 — Import d'un `pages.jsonl` écrit à la main : Banc d'abord (rouge) : import puis génération HASPmota = mêmes objets JSON que la source, sur les six `pages.jsonl`
- A13 — Import d'un `pages.jsonl` écrit à la main : Description : objet `brut` accepté par le validateur, réécrit tel quel par le générateur HASPmota, signalé absent de
- A13 — Import d'un `pages.jsonl` écrit à la main : Page : bouton « Importer le pages.jsonl de la carte », diff avant écriture, objets `brut` hachurés et non éditables
- A13 — Import d'un `pages.jsonl` écrit à la main : Commit
- A14 — Objets du palier 2 : image, liste déroulante, interrupteur, roue, QR code : Bancs d'abord (rouge) : `img` (PNG seul), `dropdown`, `switch`, `roller`, `qrcode` dans le validateur et les deux
- A14 — Objets du palier 2 : image, liste déroulante, interrupteur, roue, QR code : Catalogue, validateur, générateur HASPmota, moteur LVGL pur (`lv.image`, `lv.dropdown`, `lv.switch`, `lv.roller`,
- A14 — Objets du palier 2 : image, liste déroulante, interrupteur, roue, QR code : Page : palette, propriétés (éditeur de liste d'options, choix d'un PNG du dossier de la carte), dessin approché,
- A14 — Objets du palier 2 : image, liste déroulante, interrupteur, roue, QR code : Règle de rangement des images ramenée au `.png` (`gestionFileFolder.be`, accord de l'utilisateur) ;
- A14 — Objets du palier 2 : image, liste déroulante, interrupteur, roue, QR code : Essai sur la carte : un objet de chaque type sur l'écran des débits, vu et touché (avec A11) ; commit
- Amélioration [projet] : Propositions de réglages des `display.ini` par Claude d'après les notes de terrain (`<nom>.notes.md`)

#### [Écran 7B de la cave, vues, commandes par ModBus, affichage par MQTT, veille et pannes des flotteurs](plans/ecran-cave-vues-commandes.md) — 52 %

- A5 — L'écran envoie ses touches : Vérifier qu'un bouton sans broche ne fait pas planter `changementEtatCapteur` (`device["pin"]` dans un `format %i`) ni le relevé `0x02` du maître ; corriger en `find("pin", -1)` si besoin (dans `globalFonctions.be`, sans autre changement)
- A5 — L'écran envoie ses touches : Banc rouge d'abord : `banc_ecran_cave.{py,be}` (modèle `banc_ecran_debits`) : `touche_pousse_mot`, `seq_avance_jamais_zero`, `refus_si_perime`, `relance_jusqu_a_confirmation`, `abandon_apres_5`, `redemarrer_toujours_on`
- A5 — L'écran envoie ses touches : Code ; banc VERT ; mutants rouges
- A5 — L'écran envoie ses touches : Commit `feat(ecran-cave): envoi des touches par push ModBus`
- A6 — L'écran affiche l'état par MQTT : Commit `feat(ecran-cave): affichage par MQTT, valeurs datees et perimees`
- A7 — Pages HASPmota de l'écran : Maquette du rendu (capture de l'aperçu de l'atelier) validée par l'utilisateur avant l'écriture des pages
- A7 — Pages HASPmota de l'écran : `ecran.json` validé par `atelier_ecrans_description.valide` ; `pages.jsonl` généré
- A7 — Pages HASPmota de l'écran : `banc_ecran_cave` étendu : chaque objet référencé par `affiche` existe dans `pages.jsonl` ; `confirmation_avant_redemarrage` ; `menu_ouvre_et_ferme`
- A7 — Pages HASPmota de l'écran : Commit `feat(ecran-cave): pages HASPmota (accueil, graphiques, cuve, reglages, menu)`
- A8 — Intégration, non-régression, compilation : Cenv de `tasmota32s3-cave-ecran` : `custom_interface_ecran = haspmota` et ses listes, fichiers du dossier ; autoexec de l'écran (`ecranFonctions`, `ecranCaveFonctions`, `controleEcranCave`, `modules.ecranCave` ON)
- A8 — Intégration, non-régression, compilation : `banc_demarrage.py` : cave et écran réenregistrés (contenu relu), toutes les autres cartes VERTES SANS réenregistrement
- A8 — Intégration, non-régression, compilation : `banc_test_modbus.py`, `banc_ecran_debits.py`, `banc_pompe_cave.py`, `banc_ecran_cave.py` VERTS ; `verifie_berry.py` 0 erreur ; `genere_schema_persist.py --valide` 0 erreur
- A8 — Intégration, non-régression, compilation : Agent `relecteur-berry` sur tous les `.be` touchés ; remarques traitées
- A8 — Intégration, non-régression, compilation : Compilation par la page Build : cave, écran (et débits, garage si `data/fs` solidifié touché) ; journaux SUCCESS
- A8 — Intégration, non-régression, compilation : `PROTOCOLE_MODBUS.md` §10 et `outils_docs/README.md` (mode d'emploi de l'écran) ; plan `envs-grenier-rdc-sonoff-cave` A9 coché
- A8 — Intégration, non-régression, compilation : Commit `feat(ecran-cave): integration et documentation`
- A9 — Essai sur carte (écran branché) : Flash de l'écran (USB, effacer puis téléverser) ; `TasmotaSlaveModBus1` et `modules.ecranCave` de la cave à ON, persist renvoyé à chaud
- A9 — Essai sur carte (écran branché) : Chaque touche commute son relais ; redémarrage après confirmation ; aucune commutation au redémarrage de l'écran ni du serveur (journal syslog)
- A9 — Essai sur carte (écran branché) : Broker coupé : valeurs grisées, touches refusées ; RS485 seul, puis Wi-Fi seul
- A9 — Essai sur carte (écran branché) : Marche manuelle de la pompe : flotteurs ignorés, réactivés à l'arrêt et après la minuterie
- A9 — Essai sur carte (écran branché) : Veille, réveil sans action, luminosité
- Amélioration [projet] : Solidifier `ecranFonctions` dans les envs à écran (plan `debits-deux-cartes` A8)
- Amélioration [projet] : Boutons physiques du serveur à garder ou retirer (plan `envs-grenier-rdc-sonoff-cave` A9)
- Amélioration [projet] : Topic de la cave à changer au retour en production (A7 du plan d'origine) : seul le persist de l'écran à modifier

#### [Étiquettes QR code des cartes (page 7970) : impression, page de la carte, écran](plans/etiquettes-qrcode.md) — 60 %

- A6 — Page `/qrcode` de la carte : Essai sur une carte choisie par l'utilisateur : réglage écrit par la page 7970, firmware recompilé et FS envoyé
- A6 — Page `/qrcode` de la carte : Commit
- A7 — Suivi des changements, téléversement, liens des autres outils : Bancs d'abord (rouge) : hostname changé dans le persist -> `a_reimprimer` et `a_regenerer` ; topic changé et
- A7 — Suivi des changements, téléversement, liens des autres outils : Module, routes, badges ; bancs VERT
- A7 — Suivi des changements, téléversement, liens des autres outils : « Téléverser » : URL de la page Build `?env=&depuis=qrcode&fichiers=/json/qrcode.json&redemarrer=0` (sur le modèle
- A7 — Suivi des changements, téléversement, liens des autres outils : Lien « Étiquette QR à refaire » dans le message de fin d'un renommage (Fichiers Berry) et d'une modification
- A7 — Suivi des changements, téléversement, liens des autres outils : Régénération au build (demande du 2026-11-12) : le pré-script (`build/pre_utilitaires_platformio.py`), avant
- A7 — Suivi des changements, téléversement, liens des autres outils : Commit
- A8 — QR code à l'écran des cartes (après l'atelier des écrans) : Objet `qrcode` du catalogue : bouton qui affiche le QR code en surimpression pendant `delai_s` (défaut 30), texte
- A8 — QR code à l'écran des cartes (après l'atelier des écrans) : Bancs des deux générateurs VERT avec l'objet ; essai sur l'écran des débits, scan au téléphone
- A8 — QR code à l'écran des cartes (après l'atelier des écrans) : Commit
- A9 — Documentation : `outils_docs/README.md` § « Étiquettes QR code (page web) » : usage, verdict, impression à 100 %, planche, page de
- A9 — Documentation : `CLAUDE.md` (carte des documents) : modules `etiquettes_qr_*`, `qrcodePage.be`, liste `etiquette_qr`, bancs ;
- A9 — Documentation : Commit ; plan passé `statut: clos`
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Banc du filtre d'abord (rouge), avec mutants : refus d'une valeur portant des identifiants d'URL (`://x:y@`), un
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Filtre ; banc VERT ; appliqué en plus du filtre de l'A2 (clé ET valeur), avertissement dans l'aperçu,
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Fiche HTML autonome (aucune ressource externe, CSS en ligne, clair/sombre par `prefers-color-scheme`,
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Réglage « Contenu du QR code » : en mode lien, QR code = `url_fiche` (verdict sur l'URL), proposé pour toute carte
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Publication : diff des fiches avant envoi, bouton « Publier » distinct d'« Écrire », refus pendant un build ;
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Mise en service par l'utilisateur, une fois : Settings > Pages > Source « Deploy from a branch », branche
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Essai réel : une carte publiée, QR code en mode lien imprimé, scanné au téléphone en 4G
- A10 — Fiches en ligne (GitHub Pages) et filtre durci : Commit

#### [Visuel des volets sur la page d'accueil et réglage des durées par les boutons](plans/visuel-reglage-volets.md) — 79 %

- A8 — Essais sur carte : Grenier du 2e étage (`inverse` 1, bouton unique) : envoi par la page Build, dessin ouvert quand la trappe est ouverte,
- A8 — Essais sur carte : Trappe à MPU6050 actif (si le capteur est posé) : dessin qui suit l'angle, réglage sans arrêt en butée, durée du MPU
- A8 — Essais sur carte : P4 du garage : dessin de la porte (`inverse` 1), chrono seul (journal : aucun `Shutter*` envoyé par le réglage)
- A8 — Essais sur carte : Grenier du RDC à sa mise en service (`inverse` 0, 2 boutons et bouton unique) : les 3 ouvertures, réglage de chaque volet
- A8 — Essais sur carte : Durées mesurées recopiées dans les persists du dépôt, si l'utilisateur le demande
- A9 — Revenir au plan d'origine `envs-grenier-rdc-sonoff-cave` : Passer ce plan à `statut: clos`, puis cocher A14 et les étapes de réalisation d'A12 et d'A13 du plan d'origine, avec preuve
- A9 — Revenir au plan d'origine `envs-grenier-rdc-sonoff-cave` : Taper `/suivi suivre envs-grenier-rdc-sonoff-cave` et reprendre à sa prochaine étape
- A10 — Façade du rideau du garage (demande du 2026-11-12) : Essai sur carte : dessin qui suit la porte pendant une course du P4 ; P4 injoignable -> grisé, position des fins de course
- Amélioration [projet] : Corriger en amont la boucle sans accolades de `CmndShutterButton` (`ShutterButton<x> 0`) : proposition à

#### [Débits de la nourrice sur deux cartes, acquisition esclave et affichage maître](plans/debits-deux-cartes.md) — 62 %

- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Compilation des deux envs par la page Build, SUCCESS lu en fin de journal, flash de l'acquisition < 80 % ; acquisition flashée en premier (USB, « Effacer puis téléverser »), puis l'affichage
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : RS485 seul (Wi-Fi de l'acquisition coupé) : les 6 débits sur l'écran au rythme du relevé ; push seul (câble débranché) : écran à jour ≤ 2 s après la fin d'une fenêtre ; les deux coupés : « inconnu » après 2 fenêtres
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Affichage redémarré : l'acquisition revient seule sur le point d'accès, aucun redémarrage de sa part, compteurs continus ; tas des deux cartes mesuré avant et après une heure
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Téléphone sur `SERVEUR-DEBITS-PAC-GATEWAY` : Internet par le NAPT ; page d'équilibrage par `http://192.168.0.51:8080/equilibrage` depuis le Wi-Fi maison ; MQTT des deux cartes reçu
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Garage : grille ModBus repassée (`testeur_udp`, onglet « Grille ModBus ») après le prochain flash d'une carte du garage, aucun écart
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Commit par `/commite`
- A7 — Retour au plan « debitmetres-chauffage » : Cocher l'étape « Réalisation par le plan `tasks/plans/debits-deux-cartes.md` » de l'action A8 de `tasks/plans/debitmetres-chauffage.md` (preuve : commit de A6), passer ce plan en `statut: clos`, puis reprendre `debitmetres-chauffage` où il attend : A2 (niveaux mesurés, K confirmé à réception, PAC), A5 (page web de la carte des débits), A6 (essai de charge, sur l'acquisition sans écran), A7 (pose et étalonnage)
- A8 — Carte d'affichage sur le Waveshare ESP32-S3-Touch-LCD-7B (module acheté, 1024 × 600) : Modèle `outils_docs/schemas/modele_persist.json` (fait en partie le 2026-11-11 : `extinction`, `luminosite`, `pwmInverse` dans `metier.cles_propres`, tests de l'assistant VERT) : ajouter les nouvelles clés d'écran (luminosité, gradation de la veille) quand le pilote les crée, par « Mettre à jour le modèle » de la page 7900 (demande du 2026-11-11) ; le bloc `ecran` du modèle reste le défaut générique (ILI9488 SPI, OFF)
- A8 — Carte d'affichage sur le Waveshare ESP32-S3-Touch-LCD-7B (module acheté, 1024 × 600) : Interface LVGL pur en Berry (même maquette, objets LVGL, courbe possible par `lv.chart`) ; banc VERT
- A8 — Carte d'affichage sur le Waveshare ESP32-S3-Touch-LCD-7B (module acheté, 1024 × 600) : `banc_demarrage` des deux variantes (haspmota et lvgl), quand `ecranHaspmota.be` et `ecranLvgl.be` existeront
- A8 — Carte d'affichage sur le Waveshare ESP32-S3-Touch-LCD-7B (module acheté, 1024 × 600) : Essai sur la carte (avec A6) : image, couleurs, tactile, rétroéclairage, stabilité avec le Wi-Fi, relevé RS485
- A8 — Carte d'affichage sur le Waveshare ESP32-S3-Touch-LCD-7B (module acheté, 1024 × 600) : Solidifier le code d'écran générique et stable (veille, luminosité, chargement de l'interface : module `ecranFonctions` séparé du code des débits) : liste validée par l'utilisateur, module déplacé dans `data/fs`, ajouté au `custom_berry_solidify` des seuls envs à écran, `banc_demarrage` vert, compilation par la page Build (demande du 2026-11-11) (déplacement dans data/fs fait le 2026-11-12, plan ecran-cave-vues-commandes A1 ; solidification restante)
- A8 — Carte d'affichage sur le Waveshare ESP32-S3-Touch-LCD-7B (module acheté, 1024 × 600) : Polices : Roboto Condensed TTF sous /sd/polices par FreeType (choix du 2026-11-11), a verifier sur la carte AVEC et SANS carte SD : chemin vu par LVGL (`lvbe_fopen` -> `lv_zip_ufsp`), RAM et PSRAM de FreeType (4 tailles), rendu, place en flash pendant le premier rangement sans SD (~290 Ko : original + copie)
- A8 — Carte d'affichage sur le Waveshare ESP32-S3-Touch-LCD-7B (module acheté, 1024 × 600) : Vérifier sur la carte, avec l'utilisateur : le sens du PWM de luminosité (registre 0x05 de l'expandeur, clé persist de l'inversion à corriger au besoin), l'adresse 0x5D du tactile GT911, les couleurs de la dalle
- A9 — Atelier des écrans (plan `atelier-ecrans`) : Suivre le plan : taper `/suivi suivre atelier-ecrans` ; revenir ici : `/suivi suivre debits-deux-cartes`
- A9 — Atelier des écrans (plan `atelier-ecrans`) : Plan `atelier-ecrans` réalisé et clos (`statut: clos`) — preuve attendue : essai réel de son action A10
- Amélioration [projet] : Rétroéclairage gradué automatiquement par une mesure de lumière (ADC de l'expandeur ou GPIO6)
- Amélioration [projet] : Fenêtre de mesure transmise par l'acquisition (évite la recopie à la main sur l'affichage)
- Amélioration [projet] : Défaut de l'ancien chemin `Count` > 1 (`[v, 0, …]`) corrigé pour toutes les cartes, avec la grille du garage

#### [Mesure des 6 débits de la nourrice de chauffage, écran TFT et page web](plans/debitmetres-chauffage.md) — 68 %

- A2 — Matériel et câblage : Niveaux mesurés à réception sur une voie montée (haut ≈ 3,3 V, bas < 0,8 V)
- A2 — Matériel et câblage : Largeur de la carte S3 achetée compatible avec le bornier DNDINS3 (25,4 ou 28 mm, 44 broches)
- A2 — Matériel et câblage : Recherche d'un module tout-en-un vendu en ligne (demande du 2026-11-09) : ESP32-S3 (N16R8 de préférence) + écran tactile intégré + GPIO accessibles pour les 6 débitmètres (au moins 6 entrées libres hors broches de l'écran, de la PSRAM et du démarrage), alimentation 5 V ; comparatif (référence, prix, broches libres, pilote d'écran pris en charge par Tasmota/HASPmota, boîtier) contre la solution actuelle S3 DevKit + ILI9488 séparés, choix laissé à l'utilisateur
- A2 — Matériel et câblage : PAC = **Daikin Altherma haute température** (utilisateur, 2026-11-08 ; photo : 1re génération grise, `EKHBRD` + `EKHTS` + `ERRQ`/`ERSQ` probable, guide § 2.1 ter) : modèle exact lu sur la plaque ; débit minimal de la notice (12 L/min sur Altherma 3 H HT, 20 L/min sur ETBH/ETBX16) et ΔT réglé (radiateurs : 10 K fixe, 8 K si `[2-0C]` = 2 ; la pompe module son débit pour le tenir). Plage du capteur à reconfirmer : part de chaque radiateur × débit minimal de la PAC ≥ 1 L/min (≈ 1,7 L/min pour 1 400 W sur ~10 kW) ; seul un robinet thermostatique qui ferme passe sous le seuil (guide `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`, § 2.1 bis)
- A2 — Matériel et câblage : Facteur K confirmé à réception (référence lue sur l'étiquette ; volume connu passé dans un capteur : impulsions / litres × 60)
- A5 — Affichage sur l'écran TFT et page web : Page web de la carte : 6 lignes nommées (`web_sensor`) ; lignes natives des compteurs bruts et du `FlowRateMeter` jugées sur la vraie page (gardées ou masquées), avec l'utilisateur
- A6 — Essai de charge sur banc : Générateur : second ESP32 en `PwmFrequency` sur 6 sorties câblées aux entrées de la carte (fait AVANT l'achat des 5 autres capteurs)
- A6 — Essai de charge sur banc : Paliers 11, 55, 275 Hz (1, 5 et 25 L/min), puis 1 000 et 2 000 Hz par voie : impulsions comptées contre envoyées (écart < 0,5 %)
- A6 — Essai de charge sur banc : Résultats reportés au § 6 ter de l'analyse (estimation remplacée par la mesure)
- A7 — Pose, étalonnage et documentation : Débit affiché par la PAC relevé AVANT la pose des capteurs (référence)
- A7 — Pose, étalonnage et documentation : Pose sur la nourrice, 6 voies affichées et nommées
- A7 — Pose, étalonnage et documentation : Débit de la PAC relevé APRÈS la pose : au-dessus de son minimum constructeur, aucun défaut de débit sur une semaine
- A7 — Pose, étalonnage et documentation : Contrôle de cohérence : somme des 6 débits contre le débit de la PAC, K corrigé par `ReglageDebits` si besoin
- A7 — Pose, étalonnage et documentation : Commit par `/commite`
- A8 — Étude : deux S3, acquisition et affichage séparés (demande du 2026-11-09) : Réalisation par le plan `tasks/plans/debits-deux-cartes.md` (lecture groupée, push UDP, carte d'affichage, mise en service) ; à sa clôture, revenir ici : A2 (niveaux, K à réception), A5 (page web de l'acquisition), A6 (essai de charge), A7 (pose et étalonnage)
- Amélioration [projet] : Carte porteuse PCB pour la nourrice (skill `pcb-tasmota`)
- Amélioration [projet] : Historique et page `/graphiques` des 6 débits : plan `tasks/plans/historique-debits.md` (actif : A1 à A3 faits, historique activé et compilé le 2026-11-08, commit `c8c21131f` ; reste l'essai sur la carte, A4)
- Amélioration [projet] : Lire la PAC (EKHBRD probable, photo du 2026-11-08) : passerelle RTD-W en Modbus RS485 ou pont P1P2MQTT, lecture seule ; pas de voie X10A prouvee (guide § 2.1 ter)
- Amélioration [projet] : Températures départ et retour (DS18B20) pour la puissance par radiateur : P (W) ≈ 1,16 × Q (L/h) × ΔT (K)

#### [Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie » (disposition B)](plans/energie-differentiel.md) — 100 %

- A11 — Remarques de l'utilisateur du 2026-11-02 (soir) : Thermomètre corrigé (« n'oublie pas la correction des paramètres ») : GPIO34 lit ~2,2 V au lieu de 0,64 V depuis l'envoi du FS (15 °C au lieu de 27 °C) ; `AdcParam1` rétabli (B 15000), `SetOption146` écarté ; cause inconnue, il faut la température réelle près du boîtier

#### [Page d'équilibrage de la nourrice servie par la carte des débits, débits lus en direct](plans/equilibrage-par-la-carte.md) — 83 %

- A5 — Sur la carte (avec le matériel) : FS envoyé par la page Build ; bouton « Équilibrage » de l'accueil ouvert depuis le téléphone ; « Lire les débits » = valeurs de l'accueil ; suivi direct ; tas mesuré avant et après la première ouverture
- A5 — Sur la carte (avec le matériel) : Favori du téléphone vers `/equilibrage` : la page s'ouvre (relais) ; « Garder les puissances sur la carte » puis rechargement depuis un autre appareil : puissances retrouvées ; schéma sur les débits réels en suivi direct

#### [Historique et page /graphiques des 6 débits de la nourrice](plans/historique-debits.md) — 75 %

- A4 — Essai sur la carte : Après 1 h : séries D1-D6 et Total présentes (`/histo`), courbes sur `/graphiques`, RAM et FS relevés
- A4 — Essai sur la carte : Après un redémarrage : historique conservé, aucune erreur au journal (`ReglageLog` / syslog)
- Amélioration [projet] : Envoi vers Influx/Grafana du Pi (bouton « Historique (Grafana) » : clé `grafana` du persist)

#### [Page dédiée « Niveau de la cuve » (jauges A, H et B), lien depuis l'encadré de la cuve](plans/jauges-cuve.md) — 98 %

- A6 — Build et essai sur les cartes : Relevé ModBus 4708 vu au sniffeur ou dans le log du P4 (valeur = tension de la sonde de la cuve en mV) — bloqué : ADS1115 débranché avec la sonde (`I2CScan` : « No devices found » sur la cuve, 2026-11-09) ; sans lui `cuveFonctions.montageSonde` rend nil, la tension recalculée reste « -,-- » sur la cuve même, en simulation comprise. À refaire sonde et ADS1115 rebranchés
- Amélioration [projet] : Factoriser le chargeur ECharts commun à `graphiques.js` et `cuve.js` si l'essai est adopté — REPORTÉ par décision de l'utilisateur (2026-11-09) : à faire avec le prochain flash qu'on aura de toute façon à faire sur ces cartes (mise à jour d'ECharts ou de liquidfill, firmware à recompiler pour une autre raison), pas pour lui seul ; en attendant, garde-fou du banc ci-dessous. Coût : 4 copies (`cuve.js`, `graphiques.js`, `graphiques_moteur.js` pour liquidfill, `pages_graphiques.js`), un fichier commun touche 3 modules SOLIDIFIÉS (`graphiquesFonctions`, `cuvePageFonctions`, `pagesGraphiques`) -> firmware à recompiler sur chaque carte à graphiques (P4 : `CfgHolder` 1608 -> 1609, réglages remis à l'usine)

#### [Page web « Build et téléversement » (port 7700, tuile de l'annuaire)](plans/page-build-televersement.md) — 100 %

- Amélioration [projet] : OTA du FS par MQTT (`build_ota_mqtt.py`) : mêmes parades que l'A17 (place, fichiers identiques).
- Amélioration [projet] : Relance de l'OTA vers une carte DÉJÀ en safeboot, prouvée en réel : le 2026-10-28 à 19:31 (cuve en

#### [Voie Ethernet complète — FTP, UDP, esclaves par le point d'accès, repli sur le Wi-Fi](plans/voie-reseau-ethernet.md) — 47 %

- A1 — FTP sur les deux voies : Sur carte : FTP joignable par l'IP Ethernet. Sources : écoute sur toutes les interfaces (`WiFiServer` sans adresse imposée). Essai possible sans flash : câble sur le P4 (`Ethernet` ON, `UfsFTP` 2, relevé du 2026-11-02 : IP Ethernet 0.0.0.0, donc pas de lien)
- A1 — FTP sur les deux voies : Sur carte, Wi-Fi client coupé : lister et transférer un fichier en mode passif, avec un client qui suit l'adresse annoncée
- A2 — Trous de l'UDP, du Range Extender et des autres modules en Ethernet : `udpFonctions.ipSTA` chez un esclave en Ethernet : "" = « toutes les interfaces » (`udpFonctions.be::envoiUDP`) ; essai d'envoi réel à faire sur carte (code fait le 2026-11-08 : socket liée à l'IP Ethernet, test_discovery « esclave en Ethernet » OK ; reste l'essai)
- A3 — Esclaves en Wi-Fi quand le maître est en Ethernet : `xdrv_58_range_extender.ino` : montage du point d'accès si `WL_CONNECTED` OU `EthernetHasIP()` ; DNS pris sur l'Ethernet ; `RgxPort` sur l'IP Ethernet si la STA est absente ; modification minimale (fichier de l'amont, conflit possible à la synchro)
- A3 — Esclaves en Wi-Fi quand le maître est en Ethernet : Ordre au démarrage : `WifiDisable` ne doit pas couper un point d'accès déjà monté (`WifiSetMode(WIFI_OFF)`, garde `wifi_down`)
- A3 — Esclaves en Wi-Fi quand le maître est en Ethernet : `configGlobal_voieReseau` : ne plus forcer le Range Extender à OFF, retirer `activationAvantEthernet` (annule la décision du 2026-11-02, à la demande de l'utilisateur) ; banc_boot cas 6-7 adaptés
- A3 — Esclaves en Wi-Fi quand le maître est en Ethernet : Compilation de la cave S3 et du P4 par la page Build
- A3 — Esclaves en Wi-Fi quand le maître est en Ethernet : Essai sur carte : un esclave sur le point d'accès joint le broker MQTT par le câble (trafic vu sortir par l'Ethernet, câble seul branché) ; `RgxPort` joignable depuis le LAN
- A3 — Esclaves en Wi-Fi quand le maître est en Ethernet : Essai P4 : le C6 tient-il le point d'accès avec le Wi-Fi client coupé ?
- A4 — Deux adresses IP facultatives et accès par le nom : Clé facultative `serveur.IPEthernet` (même forme que `serveur.IP`) ; absente = même IP qu'en Wi-Fi ; schéma du persist régénéré
- A4 — Deux adresses IP facultatives et accès par le nom : `ReglageGlobal VoieReseau` sans argument : répond aussi l'IP en service et le nom `<hostname>.local`
- A4 — Deux adresses IP facultatives et accès par le nom : Page Build : OTA par `WIFI_IP_ADDRESS` (`build_envs.py`), donc une carte à IP Ethernet distincte n'est pas jointe : accepter le nom `.local` ou l'IP Ethernet
- A4 — Deux adresses IP facultatives et accès par le nom : Mode d'emploi dans `outils_docs/README.md`
- A4 — Deux adresses IP facultatives et accès par le nom : Essai : `ping SERVEUR-RLY-CAVE.local` depuis le PC, sur les deux voies
- A5 — Repli automatique sur le Wi-Fi si l'Ethernet tombe : Essais sur carte : câble débranché puis rebranché (l'événement `ETH#Connected` vient-il en IP fixe ?), état des relais au retour (`PowerOnState`), point d'accès actif (redémarrage en plus par `xdrv_58`)
- Amélioration [projet] : `tasks/plans/cave-s3-waveshare.md` : l'essai de `VoieReseau` à réception de la carte reprend les essais de ce plan

#### [Ruban WS2812 de la cuve en AUTO/MANUEL et carte cuve v0.2](plans/ruban-cuve.md) — 77 %

- A2 — Lot 2 : ruban en AUTO/MANUEL avec bouton poussoir sur la cuve : Bouton physique de la cuve (GPIO7) essayé sur la carte : appui court = allume/éteint, appui long = couleur suivante (MANUEL), double appui = retour AUTO
- A3 — Lot 3 : pilotage du ruban depuis le maître P4 : « Couleur suivante » depuis le P4 observée sur la carte (`RubanEsclave1 suivante`, puis relevé du mode MANUEL)
- A3 — Lot 3 : pilotage du ruban depuis le maître P4 : Bouton physique du maître (`bouton2`, GPIO22, appui long 15) essayé sur la carte
- A5 — Avant de commander la carte : Tension laissée au capteur de niveau (~11 V, ~8 V sur une voie 4-20 mA) vérifiée avec sa référence et sa voie — question à reposer à l'utilisateur
- A5 — Avant de commander la carte : Mesurer le DevKit ESP32-S3 et les modules (entraxes des broches)
- A5 — Avant de commander la carte : Vérifier la hauteur des fusibles MF-R dans le boîtier
- A5 — Avant de commander la carte : Relecture finale par l'agent `relecteur-pcb`
- A5 — Avant de commander la carte : Export de fabrication (Gerber, BOM, CPL pour JLCPCB)
- Amélioration [projet] : Cuve : PSRAM détectée un démarrage sur deux le 2026-10-14 (même firmware) ; cause non établie (câble, alimentation ou module). La surveiller au prochain démarrage par le pont série. Le 2026-10-31 : un seul défaut avec le blocage ci-dessous (bloquée = `HDW:` SANS « (PSRAM) », le code s'exécute depuis la PSRAM : PsrMax 5376 Ko = 8 Mo − programme) ; config OPI correcte ; 25/25 démarrages avec PSRAM les 24-25/10 ; hypothèse non prouvée : les 2 USB-C branchés le 14/10. Surveillance : syslog journalisé par l'annuaire (`%TEMP%\syslog_tasmota.log`), une ligne `HDW:` sans « (PSRAM) » = récidive.
- Amélioration [projet] : Cuve : cause du blocage après `HDW:` à la suite du flash du 2026-10-15 non établie. Même défaut que la PSRAM ci-dessus (voir sa ligne).

#### [Cave — envs ESP32/S3 alignés sur la carte en ligne, audit de l'env S3, carte S3 8 relais de remplacement](plans/relais-cave-s3.md) — 80 %

- A5 — Commit : `git commit -- <chemins de ce plan seulement>`, message en français sans accents. ⚠️ `user_config_override.h` porte déjà des changements de build (CFG_HOLDER) : les montrer à l'utilisateur avant de les inclure.
- A5 — Commit : `git show --stat HEAD` relu
- Amélioration [projet] : Une fois la carte choisie : nouveau template, nouvelles broches du persist S3 et section du cenv pour CETTE carte (l'env S3 actuel suppose un DevKit + module relais câblé)
- Amélioration [projet] : Compiler les deux envs (page build) une fois le build du P4 fini, sur décision de l'utilisateur
- Amélioration [projet] : Si la S3 remplace la carte en ligne : topic `-v2` contre `cave/serveur-rly-cave` côté Node-RED et Telegram (pris en charge par l'audit)

#### [Sniffeur I2C (ESP32-S3 dédié + outil PC de l'annuaire)](plans/sniffeur-i2c.md) — 72 %

- A6 — Mode maître au banc (composant isolé) : Firmware : ordres `MW`/`MR`/`MWR` -> arrêt de l'écoute, Wire sur les mêmes broches, réponse `M`, retour à l'écoute ; refus `M ok=0 err=bus_actif` si un front de SCL a été vu dans les 2 dernières secondes ; banc Unity du refus — codé (d9747da91, `main.cpp::ordre_maitre`), refus testé côté PC seulement : à vérifier sur carte en A8, pas de banc C++ du refus
- A7 — Intégration : annuaire, cible Custom, tâche VS Code, documentation : Tâche VS Code « Outil : sniffeur I2C (http://127.0.0.1:7350) » (`${env:USERPROFILE}`), lancée une fois — tâche écrite (d7e7ca9f6), sa ligne de commande vérifiée (page 200) ; reste à la lancer par Tasks: Run Task
- A8 — Validation sur matériel (avec l'utilisateur) : Broches 4/5 confirmées sur la sérigraphie du DevKit ; flash du firmware hors build ; ligne `I` reçue
- A8 — Validation sur matériel (avec l'utilisateur) : Une carte du parc branchée (3 fils) : `I2CScan` + une lecture connue -> mêmes adresses et valeurs dans le fil que dans le log de la carte
- A8 — Validation sur matériel (avec l'utilisateur) : Captures réelles remplacent les trames PROVISOIRE des bancs (A4), bancs verts
- A8 — Validation sur matériel (avec l'utilisateur) : Vitesse : 100 kHz sans perte ; essai 400 kHz (source à trouver : réglage de vitesse Tasmota si disponible, sinon 2e ESP32) -> limite constatée affichée dans la page et l'Aide
- A8 — Validation sur matériel (avec l'utilisateur) : Lecture par la carte (A5) et lecture au banc d'un composant isolé (A6) vues dans le fil
- A9 — Clôture : `tasks/README.md` à jour (`node .claude/hooks/index_plans.mjs --verifier`), plan `statut: clos`
- A9 — Clôture : Commits relus, push du sha relu
- A10 — Voie MQTT pour l'envoi par la carte (demande du 2026-10-31) : Essai réel : lecture d'un registre d'un esclave par MQTT, trame vue dans le fil (avec A8)
- Amélioration [projet] : Voie 2 : firmware Raspberry Pi Pico (PIO) parlant le même protocole, `I puce=rp2040`

#### [Plan d'action de l'audit Berry (propositions P2.1 à P10.7)](plans/actions-audit-berry.md) — 91 %

- A1 — Décisions à prendre (aucun code) : P8.5 — ESP-NOW côté P4 : passerelle S3, ou ESP-NOW réservé aux S3 (après P8.4) (corrige T2 ; cote G, effort —, risque dec)
- A1 — Décisions à prendre (aucun code) : P8.10 — Attendre esp-hosted-mcu#19 avant tout ESP-NOW sur le P4 ; pas de C6 reflashé (corrige T2 ; cote G, effort nul, risque dec)
- A13 — Radio : ESP-NOW et TasMesh (exploration) : P8.1 — Ne pas retenir TasMesh pour le garage (corrige T1, T2 ; cote S, effort nul, risque nul)
- A13 — Radio : ESP-NOW et TasMesh (exploration) : P8.2 — TasMesh seulement pour de futurs capteurs ESP8266 sur batterie, broker ESP32/S3 (corrige T1 ; cote S, effort faible, risque faible)
- A13 — Radio : ESP-NOW et TasMesh (exploration) : P8.3 — Signaler la régression T10 à l'amont après un essai (corrige T10 ; cote D, effort faible, risque nul)
- A13 — Radio : ESP-NOW et TasMesh (exploration) : P8.4 — Essai borné ESP-NOW entre deux S3 (QuickEspNow) : latence, pertes, coexistence, tas (corrige T3-T9 ; cote S, effort moyen, risque faible)
- Amélioration [projet] : Ré-audit ciblé après les lots retenus (même grille, mêmes preuves), à noter dans `tasks/plans/audit-berry.md`

#### [Ethernet en option sur le maître ModBus P4 (SERVEUR-GARAGE)](plans/ethernet-p4.md) — 0 %

- A1 — Essai sur table du PHY Ethernet, avant tout code : Avec l'accord de l'utilisateur, P4 près de la box, câble branché : `Status 5` (état de départ) et `Ethernet` / `EthType` / `EthAddress` relevés
- A1 — Essai sur table du PHY Ethernet, avant tout code : `Ethernet 1` (redémarre) puis `Status 5` → bloc `StatusNET.Ethernet` avec une IP DHCP, `EthType` = 1
- A1 — Essai sur table du PHY Ethernet, avant tout code : .43 (STA) répond toujours, cuve et rideau joignables ; état remis comme au départ
- A1 — Essai sur table du PHY Ethernet, avant tout code : Résultat consigné dans la spec (§3) ; si le PHY ne monte pas : arrêt du chantier et diagnostic (`superpowers:systematic-debugging`)
- A2 — Bloc `serveur.ethernet` dans les persists : Liste des 8 persists établie par `git ls-files \| grep _persist.json` (hors `*-sauvegarde`), bloc inséré après `serveur.IP` avec les valeurs de la spec §5.1, fins de ligne de chaque fichier conservées
- A2 — Bloc `serveur.ethernet` dans les persists : Chaque fichier relu par `python -c "import json;json.load(open(...,encoding='utf-8'))"` ; `git diff --stat` = 8 fichiers
- A2 — Bloc `serveur.ethernet` dans les persists : `outils_docs/schemas/persist.schema.json` régénéré par `genere_schema_persist.py`, puis `--valide` vert
- A2 — Bloc `serveur.ethernet` dans les persists : Commit `feat(persist): bloc serveur.ethernet (OFF) dans les persists`
- A3 — `configGlobal` : critère de carte et application au démarrage : Bouchons du banc de démarrage étendus : `gpio.pin_used` piloté par le cas (broches ETH ou non), réponses de `Ethernet`/`EthType`/`EthAddress`/`EthIPAddress`… au format Tasmota, journal des commandes envoyées
- A3 — `configGlobal` : critère de carte et application au démarrage : Tests écrits AVANT le code (doivent échouer) : `ethernet_absent_rien_envoye`, `carte_sans_broches_on_rien_envoye`, `p4_off_drapeau_1_envoie_ethernet_off`, `p4_on_aligne_puis_ethernet_on`, `p4_deuxieme_boot_aucune_commande`
- A3 — `configGlobal` : critère de carte et application au démarrage : `carteAvecEthernet` et `configEthernet` écrits dans `data/fs/configGlobal.be`, appel ajouté dans `configGlobalByJson` après le bloc `IP` (`configGlobal.be:136-147`)
- A3 — `configGlobal` : critère de carte et application au démarrage : Tests verts + témoin : critère des broches neutralisé dans une copie → `carte_sans_broches_on_rien_envoye` échoue
- A3 — `configGlobal` : critère de carte et application au démarrage : `banc_demarrage.py` : instantanés des 5 cartes sans PHY **identiques** ; celui du P4 relu, écart attendu (`Ethernet 0`) enregistré par `--enregistre --carte tasmota32p4-garage-serveur-modbus`. `banc_boot.py` vert
- A3 — `configGlobal` : critère de carte et application au démarrage : Commit `feat(berry): configGlobal applique serveur.ethernet sur la seule carte a Ethernet`
- A4 — `ReglageGlobal Ethernet [ON\|OFF]` : Tests écrits avant : état sans argument (aucune écriture), `ON` → persist `ON` sauvé AVANT la commande différée `Ethernet 1`, `on` accepté, `1`/`toto` refusés sans écriture, carte sans Ethernet refusée
- A4 — `ReglageGlobal Ethernet [ON\|OFF]` : `globalFonctions.reglageEthernet` + branche `ETHERNET` dans `reglageGlobal` (`globalFonctions.be:667`, réponse `{"ReglageGlobal": …}` comme `ModeConnexion`) + ligne d'aide
- A4 — `ReglageGlobal Ethernet [ON\|OFF]` : Tests verts + témoin (ordre persist/commande inversé dans une copie → test rouge) ; `verifie_berry` sans avertissement de charte
- A4 — `ReglageGlobal Ethernet [ON\|OFF]` : Commit `feat(berry): ReglageGlobal Ethernet ON\|OFF`
- A5 — Bouton Ethernet dans la page Configuration : `web_add_config_button` et route `/ethernet` dans `data/fs/controleWeb.be` (handlers `controleWeb.be:371`), bouton absent si `!carteAvecEthernet()`, confirmation JS « la carte va redémarrer » avant le POST
- A5 — Bouton Ethernet dans la page Configuration : Test au banc (ou bouchon webserver) : bouton émis sur le P4, absent sur une S3 ; POST `bascule` appelle `reglageEthernet`
- A5 — Bouton Ethernet dans la page Configuration : Commit `feat(web): bouton Ethernet dans Configuration`
- A6 — `/discovery` : IP STA du maître : Test écrit avant (`test_discovery.be` ou banc voisin) : fiche `config` avec `ip` .50 et `hn` `SERVEUR-GARAGE-eth` + fiche `maitre` `IPAddress` .43 sous la même MAC → bouton vers .43, port distant 10043, `SERVEUR-GARAGE.local` ; sans fiche `maitre` → suffixe `-eth` retiré
- A6 — `/discovery` : IP STA du maître : Correction dans `discoveryFonctions.be:743-749` ; test vert + témoin (ancien code → rouge)
- A6 — `/discovery` : IP STA du maître : Inventaire en lecture des usages Berry de l'IP/nom réseau (`config.ip`, `config.hn`, `NetworkAddress`…) consigné dans la spec §5.6 ; corrections éventuelles → « Améliorations restantes »
- A6 — `/discovery` : IP STA du maître : Relecture des `.be` modifiés par l'agent `relecteur-berry` ; commit `fix(berry): /discovery annonce l IP Wi-Fi du maitre quand l Ethernet est actif`
- A7 — Build et téléversement du P4, option à OFF : Aucun build en cours ; build + téléversement du P4 par l'utilisateur (ou avec son accord, page Build :7700) ; fichiers réécrits par le build commités (chore)
- A7 — Build et téléversement du P4, option à OFF : Un seul redémarrage dû à `Ethernet 0`, puis plus aucun (log syslog `CONTROLE_GENERAL`) ; `Ethernet` = OFF
- A7 — Build et téléversement du P4, option à OFF : Non-régression : cuve et rideau joignables (8081/8082), `/discovery` correcte, ModBus vers la cuve OK sur 10 min (log `modbus`)
- A8 — Option à ON : `ReglageGlobal Ethernet ON` (accord de l'utilisateur) → un seul redémarrage, `Status 5` : Ethernet .50, STA .43
- A8 — Option à ON : .43 et .50 répondent ; cuve et rideau joignables par le point d'accès et par `RgxPort` ; `/discovery` vers .43
- A8 — Option à ON : Bouton de la page Configuration : état affiché, bascule OFF puis ON confirmée
- A9 — Mesure du routage et débranchement du câble : Instrument choisi (lecture seule) et témoin : interface de sortie de MQTT (.5) et syslog (.3) relevée sur 3 démarrages
- A9 — Mesure du routage et débranchement du câble : Câble débranché option ON : P4 joignable en .43, pas de redémarrage pendant 10 min ; câble rebranché : .50 revient
- A9 — Mesure du routage et débranchement du câble : Résultat consigné (spec §6 + README) ; si le trafic reste sur la STA ou varie : noté, chantier poursuivi sans correctif (décision du 2026-10-26)
- A10 — Documentation et remontage : `outils_docs/README.md` : plan d'adressage (.50 = Ethernet du Serveur de Garage), mode d'emploi `ReglageGlobal Ethernet` et bouton, résultat de A9
- A10 — Documentation et remontage : `CLAUDE.md` § « Carte des documents » : spec et plan ajoutés ; commit `docs: Ethernet du P4`
- A10 — Documentation et remontage : P4 remonté au garage, état final (ON ou OFF) choisi par l'utilisateur ; `statut: clos`
- Amélioration [projet] : Correctif C (priorité de route de l'Ethernet / Range Extender sans STA) si A9 le montre utile — chantier à part

#### [Suites de l'audit de l'env S3 du serveur relais de la cave](plans/audit-relais-cave-s3.md) — 0 %

- A1 — Prouver que l'env compile et tient en mémoire (P1) : Aucun `pio run`/scons en cours juste avant (garde_build, Win32_Process)
- A1 — Prouver que l'env compile et tient en mémoire (P1) : Env compilé via la page « Build et téléversement » (7700), sans téléversement
- A1 — Prouver que l'env compile et tient en mémoire (P1) : Taille du firmware relevée contre la partition app de 3 904 Kio
- A1 — Prouver que l'env compile et tient en mémoire (P1) : Après un premier flash : tas libre interne et PSRAM relevés (`Status 4`, `BRY: GC`)
- A2 — Ports et état de la bascule (P2, P4) : `upload_port`/`monitor_port` de l'env changés (COM3 est la cuve) ou commentés
- A2 — Ports et état de la bascule (P2, P4) : État réel des relais de la carte en ligne relevé juste avant la bascule
- A2 — Ports et état de la bascule (P2, P4) : État voulu des relais au premier démarrage de la S3 décidé et appliqué après le flash
- A3 — Topics, consommateurs et messages retenus (P3, P8) : Consommateurs de `cave/serveur-rly-cave` inventoriés sur le Pi (Node-RED, Grafana, Influx, autres)
- A3 — Topics, consommateurs et messages retenus (P3, P8) : Flux Telegram importé et réglé (token, broker) pour `cave/serveur-rly-cave-v2`
- A3 — Topics, consommateurs et messages retenus (P3, P8) : Messages retenus de l'ancien topic et LWT `-v2` effacés après la bascule
- A3 — Topics, consommateurs et messages retenus (P3, P8) : Groupe `tasmotas/cave` : carte en ligne vérifiée ; commentaires de l'env corrigés
- A4 — Rôle réseau de la cave (P5) : Décision : la cave est-elle « maître » UDP / Range Extender / discovery / FTP ?
- A4 — Rôle réseau de la cave (P5) : Si non : les 4 blocs à OFF dans `data/cave/tasmota32s3-serveur-rly/_persist.json`, banc de démarrage mis à jour
- A4 — Rôle réseau de la cave (P5) : Si oui : raison consignée dans le commentaire de l'env
- A5 — Alerte de la pompe (P6, P10) : Capteurs de niveau câblés et activés (GPIO 2/15), ou limite consignée
- A5 — Alerte de la pompe (P6, P10) : `EtatPompe`, `AcquittePompe` et `ALERTE_POMPE` essayés sur la carte
- A5 — Alerte de la pompe (P6, P10) : Banc de la relance de sécurité écrit (`finTimerRelai`, `relanceRelai`, `acquitteRelance`)
- A5 — Alerte de la pompe (P6, P10) : Une seule copie de `controlePompeVideCave.be` retenue
- A6 — Allègement de l'env (P7, P9, P11) : Base `tasmota32s3-base-N16R8-sans-ecran` et `SET_ESP32_STACK_SIZE` essayés, taille comparée à A1
- A6 — Allègement de l'env (P7, P9, P11) : `leds` retiré de la solidification, ou conservé par choix
- A6 — Allègement de l'env (P7, P9, P11) : `fsMqtt` chargé par l'autoexec de la cave si l'envoi de fichiers par MQTT est voulu
- A6 — Allègement de l'env (P7, P9, P11) : Persist nettoyé : `TasmotaSlaveModBus2`, `diverses.historique.grafana`, `ledPower`
- Amélioration [projet] : Vérifier si un 2e « maître » (id 0) perturbe la table discovery du P4
- Amélioration [projet] : Réduire la partition FS (11,3 Mo) pour la cave si l'écriture de l'image gêne

#### [Atelier des graphiques — destination « Graphiques » et bouton « Téléverser »](plans/atelier-destinations.md) — 96 %

- A10 — Retour au plan précédent non terminé : Conversation rattachée de nouveau à `atelier-graphiques` (`/suivi suivre atelier-graphiques`) ; prochaine action

#### [Env S3 relais cave adapté à la carte Waveshare ESP32-S3-ETH-8DI-8RO](plans/cave-s3-waveshare.md) — 100 %

- Amélioration [projet] : Compiler l'env S3 (page build) une fois le build du P4 fini : prouve `USE_TCA9554` et la taille (audit P1)
- Amélioration [projet] : `upload_port`/`monitor_port` = COM3, port de la cuve (audit P2) : à poser au branchement de la Waveshare
- Amélioration [projet] : Câblage des capteurs de niveau (actifs) sur DI3/DI4 (COM, DGND) à valider sur la carte reçue, avant de compter sur la relance de la pompe
- Amélioration [projet] : À la réception : compiler, puis essayer `ReglageGlobal VoieReseau ethernet` sur la carte (`Status 5`, IP .243 sur le câble, retour au Wi-Fi par la console série)
- Amélioration [projet] : Brochage de l'en-tête (21, 48) à confirmer à réception : aucun schéma PDF publié

#### [lib_ignore pour chaque env personnel, avec garde au pre-build](plans/lib-ignore-envs.md) — 100 %

- Amélioration [projet] : Piscine (ESP8266) : liste établie à la main avec `--propose` si un jour utile (pas de garde)
- Amélioration [projet] : Cache des inclusions par date de modification si les ~11 s du contrôle pèsent

#### [Réduire le temps des compilations et éviter les recompilations complètes](plans/temps-compilation.md) — 100 %

- Amélioration [projet] : VS Code lui-même prend ~1,1 cœur pendant un build (01/11 : hôte des extensions 0,3, GPU 0,26, deux fenêtres 0,47) : fermer les conversations Claude inutiles ou identifier l'extension, à mesurer

#### [Accélérer le scan des dépendances (LDF) — essai lib_ignore sur l'env de la cuve](plans/lib-ignore-cuve.md) — 100 %

- Amélioration [projet] : Couper par `#undef` (section de la cuve dans `user_config_override.h`) les 7 fonctions actives inutiles (IR, DALI, TM1638, LoRa, iBeacon, Berry Animation, SEN5X) puis ignorer leurs bibliothèques : firmware plus petit, à valider sur la carte. **Matter, SendMail et KNX restent actifs** (décision de l'utilisateur du 2026-10-31) : jamais dans un `lib_ignore` ni un `#undef`

#### [Assistant persist — reprendre, modifier et supprimer un env existant (A10)](plans/assistant-persist-modification.md) — 100 %

- Amélioration [projet] : Changer de base ou de puce d'une carte existante (aujourd'hui : refus, créer une autre carte).
- Amélioration [projet] : Éléments des métiers 2 à N (non relus par `reponses_depuis_persist` : conservés mais non éditables).

#### [Détection de blocage d'un volet par son inclinaison (MPU6050)](plans/blocage-trappe-mpu6050.md) — 100 %

- Amélioration [projet] : Essai réel sur la trappe du grenier (avec le reste de l'inclinaison)
- Amélioration [projet] : Accessoire — angle dans le JSON SENSOR (Grafana, historique ; vérifier que `historiqueSeries` n'exclut pas les volets)
- Amélioration [projet] : Accessoire — température interne du MPU6050 (registre `0x41`) comme capteur du grenier

#### [Capteur d'inclinaison MPU6050 pour les volets (trappe du grenier)](plans/inclinaison-trappe-mpu6050.md) — 100 %

- Amélioration [projet] : Essai réel sur la trappe du grenier : SDA/SCL déclarés dans le gabarit, câble court, calibrage, puis activation dans le persist du grenier (décision de l'utilisateur)
- Amélioration [projet] : Détection de blocage : moteur en marche, angle figé N secondes -> `ShutterStop` + log `erreur`
- Amélioration [conversation] : Commit sur demande de l'utilisateur (`/commite`)

#### [Page web « Fichiers Berry par env » (port 7800, tuile de l'annuaire, cible Custom)](plans/fichiers-berry-env.md) — 100 %

- Amélioration [projet] : Écriture du cenv acceptée pendant la pause « rebranchez la carte » d'une série de la page build (aucun pio ne tourne) : l'env suivant de la série construirait son FS avec la liste modifiée.

#### [Audit complet — scripts Berry, environnements de build, solidification, logs et communications](plans/audit-berry.md) — 100 %

- Amélioration [projet] : Après décision de l'utilisateur seulement : exécution des propositions qu'il aura retenues, lot par lot
- Amélioration [projet] : Ré-audit ciblé après les lots retenus (même grille, même preuves)

#### [ModBus du garage (P4, cuve, rideau) et commandes sans fil](plans/modbus-garage.md) — 100 %

- Amélioration [projet] : Capteurs de la cuve une fois branchés : `I2CScan` → 0x48, `Status 10` → DS18B20 (pull-up 4,7 kΩ sur GPIO18)

#### [Suivi des plans de travail (extension VS Code + mod)](plans/suivi-plan.md) — 100 %

- Amélioration [projet] : Bande composée meteo-contexte + suivi-plan (les deux appellent `next(e)`) — après validation de la v1
- Amélioration [projet] : Outil appelable par Claude pour cocher, seulement si les coches mal formées se répètent
- Amélioration [conversation] : Regarder la vue à l'écran : à droite, thèmes clair/sombre, mise à jour < 1 s, barre d'état, restauration au redémarrage
- Amélioration [conversation] : Installer le mod (installe_suivi_plan.py --mod) puis confirmer à l'écran : ligne de statut dans le panneau Claude, bloc suiviPlan dans une nouvelle conversation, recopie + ouverture de la vue après un mode plan, /suivi accepté
- Amélioration [conversation] : Build et flash du P4 avec les correctifs « voie ModBus » (fait par l'utilisateur), puis commit sur demande

<!-- fin-index-plans -->

## Plans plus anciens (hors format suivi, sans %)

Plans d'implémentation au format superpowers (`docs/superpowers/plans/`), sans cases cochées :
leur avancement se lit ailleurs.

| Plan | Objectif principal | Où en est-il |
|---|---|---|
| [Solidification Berry, phase 1](../docs/superpowers/plans/2026-07-15-solidification-berry-phase1.md) | Solidifier les modules Berry dans le firmware pour libérer la RAM | `tasks/reprise-solidification-berry.md` |
| [Annuaire des outils PC](../docs/superpowers/plans/2026-10-17-annuaire-outils.md) | Lister, lancer et arrêter les outils PC depuis une page (port 7600) | livré (`outils_pc/annuaire_outils.py`) |
