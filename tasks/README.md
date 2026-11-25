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

63 plans : 25 actif, 0 en-pause, 38 clos.

### build

| Plan | Objectif | Avancement | Attend | Mis à jour |
|---|---|---|---|---|
| [binomes-berry](plans/binomes-berry.md) | Créer un env ou un persist sans oubli, chaque binôme driver plus module portant sa taille, ses fichiers et se… | 87 % (69/76) | 4 à vous, 1 sur carte | 2026-11-24 |
| [cartes-simulees](plans/cartes-simulees.md) | Simuler n'importe quelle carte du parc hors ligne (pages réelles, routes Berry réelles, valeurs rejouées ou d… | 75 % (18/24) | 2 sur carte | 2026-11-14 |

### cave

| Plan | Objectif | Avancement | Attend | Mis à jour |
|---|---|---|---|---|
| [relais-cave-s3](plans/relais-cave-s3.md) | Remplacer la carte ESP32 de la cave en ligne par une S3 8 relais (Waveshare 8DI-8RO) : envs alignés, audit de… | 56 % (34/58) | 2 sur carte, 3 à vous | 2026-11-23 |
| [ecran-cave-vues-commandes](plans/ecran-cave-vues-commandes.md) | Commander les appareils de la cave et voir son état sur l'écran 7B esclave, sans rien changer au comportement… | 87 % (34/41) | 1 sur carte, 1 à vous | 2026-11-13 |
| [envs-grenier-rdc-sonoff-cave](plans/envs-grenier-rdc-sonoff-cave.md) | Paramétrer deux environnements, la carte Waveshare 8DI-8RO du grenier du rez-de-chaussée qui commande les vol… | 43 % (44/95) | 8 sur carte, 7 à vous | 2026-11-12 |

### debits-energie

| Plan | Objectif | Avancement | Attend | Mis à jour |
|---|---|---|---|---|
| [debitmetres-chauffage](plans/debitmetres-chauffage.md) | Mesurer et afficher les débits des 6 départs de radiateur avec un ESP32-S3 Tasmota, sans gêner l'écran | 60 % (35/51) | 3 à vous, 1 sur carte | 2026-11-13 |
| [debits-deux-cartes](plans/debits-deux-cartes.md) | Faire passer les 6 débits de la carte d'acquisition (esclave ModBus id 1) à une carte d'affichage (maître id… | 62 % (33/49) | 5 sur carte, 2 à vous | 2026-11-11 |
| [equilibrage-par-la-carte](plans/equilibrage-par-la-carte.md) | Ouvrir le guide d'équilibrage depuis la carte des débits et y lire les 6 débits mesurés, sans les taper à la… | 83 % (20/22) | 1 sur carte | 2026-11-09 |
| [historique-debits](plans/historique-debits.md) | Garder en flash l'historique des 6 débits et du total, et les voir en courbes sur la page /graphiques de la c… | 75 % (8/10) | — | 2026-11-09 |

### graphiques-ecrans

| Plan | Objectif | Avancement | Attend | Mis à jour |
|---|---|---|---|---|
| [atelier-visuels](plans/atelier-visuels.md) | Depuis une photo réelle, produire par carte un fond (photo allégée ou dessin vectorisé) et des points chauds… | 84 % (58/69) | 2 sur carte, 1 à vous | 2026-11-15 |
| [facade-esclaves-grenier-rdc](plans/facade-esclaves-grenier-rdc.md) | Chaque page d'accueil montre seulement ce que sa carte dirige : portail seul (esclave 4), garage et porte seu… | 38 % (6/15) | 2 à vous, 1 sur carte | 2026-11-15 |
| [facade-garage-portail-commande](plans/facade-garage-portail-commande.md) | Une façade du P4 plus fidèle (finition, cônes de la caméra et de la lampe), commandable par clic (rideau, por… | 83 % (26/30) | 1 à vous, 2 sur carte | 2026-11-15 |
| [etiquettes-qrcode](plans/etiquettes-qrcode.md) | Composer par env un QR code stylé qui affiche l identité de la carte (hostname, IP, clés du persist), l impri… | 90 % (51/56) | 2 sur carte | 2026-11-14 |
| [atelier-ecrans](plans/atelier-ecrans.md) | Modifier sur le PC la disposition d'un écran tactile de carte (objets, boutons, pages) et y épingler des rema… | 88 % (74/91) | 8 sur carte, 1 à vous | 2026-11-13 |
| [facade-garage-capteurs](plans/facade-garage-capteurs.md) | Voir sur la façade de l'accueil du P4 et de la carte du rideau l'état réel des deux fins de course, dans un d… | 38 % (7/13) | 1 sur carte | 2026-11-13 |
| [visuel-reglage-volets](plans/visuel-reglage-volets.md) | Dessiner sous les curseurs des volets une façade dont les tabliers suivent la position réelle en direct, et r… | 79 % (38/46) | 1 sur carte | 2026-11-12 |

### methode

| Plan | Objectif | Avancement | Attend | Mis à jour |
|---|---|---|---|---|
| [actions-audit-berry](plans/actions-audit-berry.md) | Mettre en œuvre, lot par lot et sur décision de l'utilisateur, les 78 propositions de l'audit Berry | 91 % (89/95) | 3 sur carte | 2026-10-26 |

### modbus-reseau

| Plan | Objectif | Avancement | Attend | Mis à jour |
|---|---|---|---|---|
| [voie-mqtt](plans/voie-mqtt.md) | Commander des esclaves, lire leurs capteurs et être averti de leurs changements d'état par MQTT, à côté de Mo… | 95 % (60/64) | 2 à vous, 1 sur carte | 2026-11-21 |
| [plan-maison-echelle](plans/plan-maison-echelle.md) | Remplacer les pièces schématiques du plan de la maison par un vrai plan à l'échelle (en mètres), un étage par… | 3 % (1/25) | — | 2026-11-19 |
| [voie-reseau-ethernet](plans/voie-reseau-ethernet.md) | Qu'une carte en voie Ethernet garde tous ses services et ses esclaves, et ne devienne jamais injoignable si l… | 47 % (18/33) | 7 sur carte, 1 à vous | 2026-11-18 |
| [rgx-ethernet-uplink](plans/rgx-ethernet-uplink.md) | Faire démarrer l'AP du Range Extender quand seul l'Ethernet a une IP, en un PR propre accepté par arendst | 41 % (11/29) | 1 à vous, 7 sur carte | 2026-11-16 |
| [tasmesh-evolution-amont](plans/tasmesh-evolution-amont.md) | Sonder arendst/Tasmota par une discussion courte, puis proposer de petits PR isolés sur TasMesh si les mainte… | 35 % (7/20) | 1 à vous, 1 sur carte | 2026-11-16 |
| [plan-maison](plans/plan-maison.md) | Document visuel qui place chaque carte Tasmota dans sa pièce et montre qui parle à qui, par quel moyen et qui… | 94 % (36/38) | 1 à vous, 1 sur carte | 2026-11-15 |
| [ruban-cuve](plans/ruban-cuve.md) | Piloter le ruban WS2812 de la cuve en AUTO/MANUEL (bouton et ModBus) et préparer la carte cuve v0.2 | 77 % (23/31) | 3 sur carte | 2026-11-02 |
| [sniffeur-i2c](plans/sniffeur-i2c.md) | Voir en direct le trafic I2C de n'importe quelle carte du parc, décodé jusqu'au registre, et lire ou écrire u… | 72 % (33/43) | 3 sur carte, 1 à vous | 2026-10-31 |

### Plans clos

- build (18) : [build-reparations](plans/build-reparations.md), [lib-ignore-cuve](plans/lib-ignore-cuve.md), [lib-ignore-envs](plans/lib-ignore-envs.md), [temps-compilation](plans/temps-compilation.md), [page-build-televersement](plans/page-build-televersement.md), [sauvegarde-config-cartes](plans/sauvegarde-config-cartes.md), [compilations-nuit](plans/compilations-nuit.md), [build-fin-partitions](plans/build-fin-partitions.md), [classement-par-lieu](plans/classement-par-lieu.md), [lieu-partage-syslog-mqtt](plans/lieu-partage-syslog-mqtt.md), [autoexec-bat](plans/autoexec-bat.md), [autoexec-mqtt-tapp](plans/autoexec-mqtt-tapp.md), [default-envs-page](plans/default-envs-page.md), [assistant-persist-modification](plans/assistant-persist-modification.md), [assistant-persist](plans/assistant-persist.md), [assistant-synchro-fork](plans/assistant-synchro-fork.md), [fichiers-berry-env](plans/fichiers-berry-env.md), [fichiers-berry-suppression](plans/fichiers-berry-suppression.md)
- debits-energie (3) : [energie-differentiel](plans/energie-differentiel.md), [jauges-cuve](plans/jauges-cuve.md), [energie-atelier](plans/energie-atelier.md)
- graphiques-ecrans (3) : [graphiques-web](plans/graphiques-web.md), [atelier-graphiques](plans/atelier-graphiques.md), [atelier-destinations](plans/atelier-destinations.md)
- methode (8) : [navigateur-ftp-cartes](plans/navigateur-ftp-cartes.md), [navigateur-ftp-cartes-a5-reprise](plans/navigateur-ftp-cartes-a5-reprise.md), [menage-appliquer](plans/menage-appliquer.md), [menage-page](plans/menage-page.md), [sondes-en-cours](plans/sondes-en-cours.md), [audit-berry](plans/audit-berry.md), [plan-par-conversation](plans/plan-par-conversation.md), [suivi-plan](plans/suivi-plan.md)
- modbus-reseau (5) : [blocage-trappe-mpu6050](plans/blocage-trappe-mpu6050.md), [inclinaison-trappe-mpu6050](plans/inclinaison-trappe-mpu6050.md), [ethernet-p4](plans/ethernet-p4.md), [alerte-firmware-c6](plans/alerte-firmware-c6.md), [modbus-garage](plans/modbus-garage.md)
- voie-mqtt (1) : [voie-mqtt-bloc1](plans/voie-mqtt-bloc1.md)

<!-- fin-index-plans -->

## Plans plus anciens (hors format suivi, sans %)

Plans d'implémentation au format superpowers (`docs/superpowers/plans/`), sans cases cochées :
leur avancement se lit ailleurs.

| Plan | Objectif principal | Où en est-il |
|---|---|---|
| [Solidification Berry, phase 1](../docs/superpowers/plans/2026-07-15-solidification-berry-phase1.md) | Solidifier les modules Berry dans le firmware pour libérer la RAM | `tasks/reprise-solidification-berry.md` |
| [Annuaire des outils PC](../docs/superpowers/plans/2026-10-17-annuaire-outils.md) | Lister, lancer et arrêter les outils PC depuis une page (port 7600) | livré (`outils_pc/annuaire_outils.py`) |
