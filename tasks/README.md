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

38 plans : 14 actif, 1 en-pause, 23 clos.

| Plan | Objectif principal | Statut | Avancement | Reste à faire | Créé | Mis à jour |
|---|---|---|---|---|---|---|
| [Mesure des 6 débits de la nourrice de chauffage, écran TFT et page web](plans/debitmetres-chauffage.md) | Mesurer et afficher les débits des 6 départs de radiateur avec un ESP32-S3 Tasmota, sans gêner l'écran | actif | ███████░░░ 68 % (35/50) | 15 étapes, 4 améliorations | 2026-11-08 | 2026-11-09 |
| [Débits de la nourrice sur deux cartes, acquisition esclave et affichage maître](plans/debits-deux-cartes.md) | Faire passer les 6 débits de la carte d'acquisition (esclave ModBus id 1) à une carte d'affichage (maître id 0) par une lecture groupée RS485 et un push UDP, sans rien changer au garage | actif | ███░░░░░░░ 29 % (10/30) | 20 étapes, 2 améliorations | 2026-11-09 | 2026-11-09 |
| [Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie » (disposition B)](plans/energie-differentiel.md) | Passer le différentiel sur le firmware du fork sans perdre calibrage, compteur ni minuteries, et lui donner une page Énergie (kWh par heure/jour/mois, coût, puissance 24 h) | actif | ██████████ 100 % (69/70) | 1 étape | 2026-10-31 | 2026-11-09 |
| [Page d'équilibrage de la nourrice servie par la carte des débits, débits lus en direct](plans/equilibrage-par-la-carte.md) | Ouvrir le guide d'équilibrage depuis la carte des débits et y lire les 6 débits mesurés, sans les taper à la main | actif | ████████░░ 83 % (20/22) | 2 étapes | 2026-11-09 | 2026-11-09 |
| [Historique et page /graphiques des 6 débits de la nourrice](plans/historique-debits.md) | Garder en flash l'historique des 6 débits et du total, et les voir en courbes sur la page /graphiques de la carte | actif | ████████░░ 75 % (8/10) | 2 étapes, 1 amélioration | 2026-11-08 | 2026-11-09 |
| [Page web « Build et téléversement » (port 7700, tuile de l'annuaire)](plans/page-build-televersement.md) | Compiler et téléverser en série (COM ou OTA) les envs cochés depuis une page web, avec progression en direct | actif | ██████████ 100 % (89/89) | 2 améliorations | 2026-10-24 | 2026-11-09 |
| [Voie Ethernet complète — FTP, UDP, esclaves par le point d'accès, repli sur le Wi-Fi](plans/voie-reseau-ethernet.md) | Qu'une carte en voie Ethernet garde tous ses services et ses esclaves, et ne devienne jamais injoignable si le câble tombe | actif | █████░░░░░ 47 % (18/33) | 15 étapes, 1 amélioration | 2026-11-02 | 2026-11-08 |
| [Onglet « Sauvegarde configuration » de la page build (modèle B)](plans/sauvegarde-config-cartes.md) | Sauvegarder, comparer, modifier paramètre par paramètre et restaurer la configuration (/dl : Settings + .drvset*) de chaque carte depuis la page build | actif | ██████████ 100 % (33/33) | — | 2026-11-03 | 2026-11-03 |
| [Ruban WS2812 de la cuve en AUTO/MANUEL et carte cuve v0.2](plans/ruban-cuve.md) | Piloter le ruban WS2812 de la cuve en AUTO/MANUEL (bouton et ModBus) et préparer la carte cuve v0.2 | actif | ████████░░ 77 % (23/31) | 8 étapes, 2 améliorations | 2026-10-18 | 2026-11-02 |
| [Page dédiée « Niveau de la cuve » (jauges A, H et B), lien depuis l'encadré de la cuve](plans/jauges-cuve.md) | Afficher volume (jauge A), taux (jauge H) et tensions brute et recalculée de la sonde (cadran B) de la cuve sur une page dédiée ouverte depuis son encadré, sur la cuve et le P4 | actif | █████████░ 92 % (27/32) | 5 étapes, 5 améliorations | 2026-10-31 | 2026-10-31 |
| [Cave — envs ESP32/S3 alignés sur la carte en ligne, audit de l'env S3, carte S3 8 relais de remplacement](plans/relais-cave-s3.md) | Aligner les envs de la cave sur les broches de la carte en ligne, auditer l'env S3 et choisir une carte ESP32-S3 à 8 relais pour la remplacer | actif | ████████░░ 80 % (17/19) | 2 étapes, 3 améliorations | 2026-10-31 | 2026-10-31 |
| [Sniffeur I2C (ESP32-S3 dédié + outil PC de l'annuaire)](plans/sniffeur-i2c.md) | Voir en direct le trafic I2C de n'importe quelle carte du parc, décodé jusqu'au registre, et lire ou écrire un registre par la carte ou au banc | actif | ███████░░░ 72 % (33/43) | 10 étapes, 1 amélioration | 2026-10-31 | 2026-10-31 |
| [Plan d'action de l'audit Berry (propositions P2.1 à P10.7)](plans/actions-audit-berry.md) | Mettre en œuvre, lot par lot et sur décision de l'utilisateur, les 78 propositions de l'audit Berry | actif | █████████░ 91 % (89/95) | 6 étapes, 1 amélioration | 2026-10-22 | 2026-10-26 |
| [Ethernet en option sur le maître ModBus P4 (SERVEUR-GARAGE)](plans/ethernet-p4.md) | Ajouter l'Ethernet en option sur le maître ModBus P4, le Wi-Fi restant le défaut | actif | ░░░░░░░░░░ 0 % (0/37) | 37 étapes, 1 amélioration | 2026-10-26 | 2026-10-26 |
| [Suites de l'audit de l'env S3 du serveur relais de la cave](plans/audit-relais-cave-s3.md) | Rendre l'env tasmota32s3-cave-serveur-rly prêt à remplacer la carte de la cave en ligne, selon les propositions de l'audit | en-pause | ░░░░░░░░░░ 0 % (0/22) | 22 étapes, 2 améliorations | 2026-10-31 | 2026-10-31 |
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

#### [Débits de la nourrice sur deux cartes, acquisition esclave et affichage maître](plans/debits-deux-cartes.md) — 29 %

- A3 — Acquisition : 7 registres et push (`data/bureau/tasmota32s3-serveur-debits-pac/`) : Banc rouge d'abord, `outils_docs/scripts_python/berry/banc_debits.be` : `modules.debits.modbus "ON"` → après `mesure()`, analogique1 = `int(q * 100 + 0.5)` (1,234 L/min → 123), voie `nil` → `SENTINELLE_UINT32`, analogique7 = bits muets/imprécis + bit 12, `noteMesure` appelé pour 4704-4710, UN appel `pousseEtat(4704, "uint32", [7 valeurs])` ; clé absente → ni écriture ni push (témoin)
- A3 — Acquisition : 7 registres et push (`data/bureau/tasmota32s3-serveur-debits-pac/`) : `debitsFonctions_publieModbus(d)` appelée par `debitsFonctions_mesure` après `debitsFonctions_suitMuets` ; `declareMesure(4704 + i, 2 * fenetre * 1000)` au premier appel et à chaque changement de fenêtre
- A3 — Acquisition : 7 registres et push (`data/bureau/tasmota32s3-serveur-debits-pac/`) : Persist de l'acquisition : `analogiques` ON, `analogique1-7` actives (`pin` -1, `type` 4704, `virtuel` `Calcul_debit1-6` et `Calcul_etatsDebits`), `modules.debits.modbus` ON ; `drivers.ModBus` ON id 1, Serial ON, UDP ON, `voieCommandes` Serial, `lectureGroupee` ON, RX 17 / TX 18 (types série de la cuve 3232/3200) ; `serveur.rangeExtender.id` 1, `ipMaitre` 192.168.0.51, `reseau1` = `SERVEUR-DEBITS-PAC-GATEWAY` (mot de passe recopié, jamais affiché) ; `timerRebootSansWifi` 0 ; `drivers.ecran` OFF
- A3 — Acquisition : 7 registres et push (`data/bureau/tasmota32s3-serveur-debits-pac/`) : Autoexec : `udpFonctions`, `controleUDP`, puis la pile `berry_commun.modbus` dans l'ordre de la cuve ; cenv : `extends = env:tasmota32s3-base-N16R8-sans-ecran`, `${berry_commun.modbus}` dans `custom_berry_solidify`, `pages.jsonl` et `display.ini` exclus ; section `#elif` du `.h` : `WIFI_IP_ADDRESS "0.0.0.0"`, `STA_SSID1` = point d'accès de l'affichage, `WIFI_RGX_SSID` propre (`ACQUISITION-DEBITS-PAC-GATEWAY`), `USE_ILI9488` retiré
- A3 — Acquisition : 7 registres et push (`data/bureau/tasmota32s3-serveur-debits-pac/`) : `banc_debits.py` VERT, `banc_demarrage.py --carte` VERT (référence réenregistrée sur une copie de `data/fs` du commit), `test_assistant_persist_generation.py` (rejeu du parc) VERT
- A4 — Carte d'affichage : env, persist, code d'écran : Env créé par l'assistant persist (:7900, `POST /creation`) sur le modèle de l'acquisition actuelle (écran ILI9488, base `tasmota32s3-base-N16R8`) : `tasmota32s3-bureau-ecran-debits-pac`, dossier `data/bureau/tasmota32s3-ecran-debits-pac`, nom « Écran Débits de PAC », IP 192.168.0.51, topic `chauffage/pac/ecran` ; diff relu ; exclusions `page_cuve`, `page_energie`, `pages_graphiques`, `pages_graphiques_moteur` vérifiées
- A4 — Carte d'affichage : env, persist, code d'écran : Persist de l'affichage : `serveur.rangeExtender` ON id 0, AP `SERVEUR-DEBITS-PAC-GATEWAY` + NAPT (mot de passe recopié côté serveur) ; `drivers.ModBus` ON id 0, Serial ON, UDP ON, RX 17 / TX 18, `periodeReleve` 10, `TasmotaSlaveModBus1` ON id 1 `lectureGroupee` ON ; 7 analogiques `virtuel` `ModBus_TasmotaSlaveModBus1`, `idModBus` 1-7, `type` 4704, `nom` des 6 départs ; `drivers.ecran` de l'acquisition d'aujourd'hui ; bloc `ecranDebits` : `fenetre` 10, `veille` 5
- A4 — Carte d'affichage : env, persist, code d'écran : Banc rouge d'abord `outils_docs/scripts_python/berry/banc_ecran_debits.py` (+ `.be`, bouchons de `banc_debits`) : 12 345 → 123,45 L/min ; `etatConstate` ≠ `valide` ou `constateA` plus vieux que 2 × fenêtre → « inconnu » ; bits muets/imprécis rendus comme sur l'acquisition ; total « partiel » si une voie inconnue, « inconnu » si toutes ; message `ECRAN_DEBITS: fenetre ?` en `debug` quand toutes les voies passent inconnues ensemble
- A4 — Carte d'affichage : env, persist, code d'écran : `ecranDebitsFonctions.be` + `controleEcranDebits.be` dans le dossier de l'affichage : rendu repris de `debitsFonctions_ecran`, `debitsFonctions_demarreEcran`, `debitsFonctions_appliqueVeille` et `pages.jsonl` (modèle B), alimenté par les 7 entrées ; `ReglageEcranDebits fenetre\|veille` et son aide ; section `#elif` du `.h` (pont ModBus et Range Extender comme le P4, `USE_ILI9488`)
- A4 — Carte d'affichage : env, persist, code d'écran : `banc_ecran_debits.py` VERT ; `banc_demarrage.py` : carte ajoutée à `CARTES`, référence enregistrée ; `verifie_berry.py` 0 erreur 0 écart
- A5 — Outils et documentation : `outils_pc/decodeur_modbus.py` : persist du maître choisi (P4 par défaut, affichage en option) ; une réponse 0x04 groupée et un push de 14 registres nommés registre par registre (débit 1 … débit 6, états avec ses bits) ; `test_sniffeur_modbus.py` VERT avec un cas groupé
- A5 — Outils et documentation : `outils_docs/PROTOCOLE_MODBUS.md` : sous-section « Lecture groupée et push multi-valeurs (2026-11-09) » (clés, bit 12, défaut `Count` > 1 de l'ancien chemin) ; `outils_docs/README.md` § des débits (deux cartes, accès `192.168.0.51:8080/equilibrage`) ; carte des documents du `CLAUDE.md` ; `verifie_references_docs.py` 0 défaut
- A5 — Outils et documentation : Relecture par `relecteur-berry` des `.be` modifiés, remarques traitées
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Compilation des deux envs par la page Build, SUCCESS lu en fin de journal, flash de l'acquisition < 80 % ; acquisition flashée en premier (USB, « Effacer puis téléverser »), puis l'affichage
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : RS485 seul (Wi-Fi de l'acquisition coupé) : les 6 débits sur l'écran au rythme du relevé ; push seul (câble débranché) : écran à jour ≤ 2 s après la fin d'une fenêtre ; les deux coupés : « inconnu » après 2 fenêtres
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Affichage redémarré : l'acquisition revient seule sur le point d'accès, aucun redémarrage de sa part, compteurs continus ; tas des deux cartes mesuré avant et après une heure
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Téléphone sur `SERVEUR-DEBITS-PAC-GATEWAY` : Internet par le NAPT ; page d'équilibrage par `http://192.168.0.51:8080/equilibrage` depuis le Wi-Fi maison ; MQTT des deux cartes reçu
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Garage : grille ModBus repassée (`testeur_udp`, onglet « Grille ModBus ») après le prochain flash d'une carte du garage, aucun écart
- A6 — Mise en service sur les deux cartes (avec l'utilisateur) : Commit par `/commite`
- A7 — Retour au plan « debitmetres-chauffage » : Cocher l'étape « Réalisation par le plan `tasks/plans/debits-deux-cartes.md` » de l'action A8 de `tasks/plans/debitmetres-chauffage.md` (preuve : commit de A6), passer ce plan en `statut: clos`, puis reprendre `debitmetres-chauffage` où il attend : A2 (niveaux mesurés, K confirmé à réception, PAC), A5 (page web de la carte des débits), A6 (essai de charge, sur l'acquisition sans écran), A7 (pose et étalonnage)
- Amélioration [projet] : Fenêtre de mesure transmise par l'acquisition (évite la recopie à la main sur l'affichage)
- Amélioration [projet] : Défaut de l'ancien chemin `Count` > 1 (`[v, 0, …]`) corrigé pour toutes les cartes, avec la grille du garage

#### [Différentiel Nous D3T — persist corrigé, calibrage protégé, page « Énergie » (disposition B)](plans/energie-differentiel.md) — 100 %

- A11 — Remarques de l'utilisateur du 2026-11-02 (soir) : Thermomètre corrigé (« n'oublie pas la correction des paramètres ») : GPIO34 lit ~2,2 V au lieu de 0,64 V depuis l'envoi du FS (15 °C au lieu de 27 °C) ; `AdcParam1` rétabli (B 15000), `SetOption146` écarté ; cause inconnue, il faut la température réelle près du boîtier

#### [Page d'équilibrage de la nourrice servie par la carte des débits, débits lus en direct](plans/equilibrage-par-la-carte.md) — 83 %

- A5 — Sur la carte (avec le matériel) : FS envoyé par la page Build ; bouton « Équilibrage » de l'accueil ouvert depuis le téléphone ; « Lire les débits » = valeurs de l'accueil ; suivi direct ; tas mesuré avant et après la première ouverture
- A5 — Sur la carte (avec le matériel) : Favori du téléphone vers `/equilibrage` : la page s'ouvre (relais) ; « Garder les puissances sur la carte » puis rechargement depuis un autre appareil : puissances retrouvées ; schéma sur les débits réels en suivi direct

#### [Historique et page /graphiques des 6 débits de la nourrice](plans/historique-debits.md) — 75 %

- A4 — Essai sur la carte : Après 1 h : séries D1-D6 et Total présentes (`/histo`), courbes sur `/graphiques`, RAM et FS relevés
- A4 — Essai sur la carte : Après un redémarrage : historique conservé, aucune erreur au journal (`ReglageLog` / syslog)
- Amélioration [projet] : Envoi vers Influx/Grafana du Pi (bouton « Historique (Grafana) » : clé `grafana` du persist)

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

#### [Page dédiée « Niveau de la cuve » (jauges A, H et B), lien depuis l'encadré de la cuve](plans/jauges-cuve.md) — 92 %

- A6 — Build et essai sur les cartes : Persists de la cuve et du P4 sauvegardés depuis les cartes AVANT tout envoi (diff carte / dépôt relu)
- A6 — Build et essai sur les cartes : Firmware (module solidifié) ET FS de la cuve et du P4 envoyés (page build : compiler + téléverser + FS), aucun autre build en cours ; firmware plus récent que le dernier commit
- A6 — Build et essai sur les cartes : Relevé ModBus 4708 vu au sniffeur ou dans le log du P4 (valeur = tension de la sonde de la cuve en mV)
- A6 — Build et essai sur les cartes : Capture Chrome de l'accueil des 2 cartes : lien visible, largeur de page inchangée (mesurée avant/après)
- A6 — Build et essai sur les cartes : Capture Chrome de `/cuve` sur les 2 cartes : jauges A et H aux valeurs de l'encadré
- Amélioration [projet] : Pleine échelle de l'ADS1115 : Tasmota remet ±6,144 V à chaque détection (`Ads1115Detect`) et le P4 suppose 6 144 mV en dur ; si `Sensor12 S1` est un jour posé, le P4 se trompe d'un facteur 1,5 (exploration du 2026-10-31)
- Amélioration [projet] : Ancien maître S3 gelé : son `controleGarage.be` ne remplit pas les 2 nouvelles lignes du gabarit partagé (`#…#` en clair s'il est rallumé)
- Amélioration [projet] : Factoriser le chargeur ECharts commun à `graphiques.js` et `cuve.js` si l'essai est adopté
- Amélioration [projet] : Le P4 ne borne pas le taux à 0..100 % et n'a pas le correctif de troncature de la cuve (`controleGarage.be`, constaté à l'exploration)
- Amélioration [projet] : Ancien maître S3 (`tasmota32s3-serveur-modbus`) : il partage l'encadré, le lien y mènera à une page absente

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
