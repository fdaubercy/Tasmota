# Suivi des plans de travail

Trace des plans de modification du fork (`tasks/plans/`, format `tasks/plans/_FORMAT.md`).
Avancement = moyenne des % des actions `## A<n>`, chaque action pesant autant (même calcul que la
vue « Suivi du plan » de VS Code). L'objectif vient de la clé `objectif:` de l'en-tête de chaque plan.

Le tableau se met à jour seul quand Claude édite un plan (hook `.claude/hooks/index_plans_edition.sh`) ;
après une édition à la main : `node .claude/hooks/index_plans.mjs` (`--verifier` : code 1 s'il est en retard).

## Plans suivis

<!-- debut-index-plans : bloc regenere par .claude/hooks/index_plans.mjs, ne pas editer -->

17 plans : 4 actif, 0 en-pause, 13 clos.

| Plan | Objectif principal | Statut | Avancement | Créé | Mis à jour |
|---|---|---|---|---|---|
| [Page web « Build et téléversement » (port 7700, tuile de l'annuaire)](plans/page-build-televersement.md) | Compiler et téléverser en série (COM ou OTA) les envs cochés depuis une page web, avec progression en direct | actif | ██████████ 99 % (83/84) | 2026-10-24 | 2026-10-30 |
| [Plan d'action de l'audit Berry (propositions P2.1 à P10.7)](plans/actions-audit-berry.md) | Mettre en œuvre, lot par lot et sur décision de l'utilisateur, les 78 propositions de l'audit Berry | actif | █████████░ 91 % (89/95) | 2026-10-22 | 2026-10-26 |
| [Ethernet en option sur le maître ModBus P4 (SERVEUR-GARAGE)](plans/ethernet-p4.md) | Ajouter l'Ethernet en option sur le maître ModBus P4, le Wi-Fi restant le défaut | actif | ░░░░░░░░░░ 0 % (0/37) | 2026-10-26 | 2026-10-26 |
| [Ruban WS2812 de la cuve en AUTO/MANUEL et carte cuve v0.2](plans/ruban-cuve.md) | Piloter le ruban WS2812 de la cuve en AUTO/MANUEL (bouton et ModBus) et préparer la carte cuve v0.2 | actif | ███████░░░ 67 % (13/21) | 2026-10-18 | 2026-10-18 |
| [Assistant persist — reprendre, modifier et supprimer un env existant (A10)](plans/assistant-persist-modification.md) | Reprendre un env existant dans la page 7900 pour le modifier sans perdre ses retouches, ou le supprimer après vérification | clos | ██████████ 100 % (38/38) | 2026-10-29 | 2026-10-30 |
| [Assistant de création du persist d'un nouvel env (page 7900, tuile de l'annuaire)](plans/assistant-persist.md) | Créer le persist, l'autoexec et les sections de build d'une nouvelle carte par questions, depuis une page web | clos | ██████████ 100 % (47/47) | 2026-10-27 | 2026-10-30 |
| [Assistant pas à pas de la page « Synchro du fork » (port 7500)](plans/assistant-synchro-fork.md) | Guider pas à pas la synchro du fork sur la page 7500, avec résolution des conflits fichier par fichier | clos | ██████████ 100 % (33/33) | 2026-10-27 | 2026-10-29 |
| [Détection de blocage d'un volet par son inclinaison (MPU6050)](plans/blocage-trappe-mpu6050.md) | Arrêter un volet et loguer une erreur quand son inclinaison ne bouge plus pendant la course (trappe bloquée) | clos | ██████████ 100 % (29/29) | 2026-10-28 | 2026-10-29 |
| [Capteur d'inclinaison MPU6050 pour les volets (trappe du grenier)](plans/inclinaison-trappe-mpu6050.md) | Lire l'angle réel de la trappe du grenier par un MPU6050 pour recaler la position du volet | clos | ██████████ 100 % (28/28) | 2026-10-28 | 2026-10-28 |
| [Alerte web « firmware du coprocesseur ESP32-C6 pas à jour » sur les P4](plans/alerte-firmware-c6.md) | Signaler sur les P4 un firmware du coprocesseur Wi-Fi ESP32-C6 en retard et proposer sa mise à jour (HostedOta) | clos | ██████████ 100 % (34/34) | 2026-10-26 | 2026-10-27 |
| [Page web « Fichiers Berry par env » (port 7800, tuile de l'annuaire, cible Custom)](plans/fichiers-berry-env.md) | Régler par une page web l'état de chaque fichier Berry par env (FS, exclu, solidifié) et créer un env | clos | ██████████ 100 % (31/31) | 2026-10-25 | 2026-10-25 |
| [Page « Fichiers Berry par env » — supprimer et renommer un env, écritures atomiques, sauvegardes, erreurs claires](plans/fichiers-berry-suppression.md) | Supprimer et renommer un env depuis la page Fichiers Berry, avec écritures atomiques et sauvegardes | clos | ██████████ 100 % (31/31) | 2026-10-25 | 2026-10-25 |
| [Audit complet — scripts Berry, environnements de build, solidification, logs et communications](plans/audit-berry.md) | Auditer en lecture seule le code Berry, les envs de build, la solidification, les logs et les communications | clos | ██████████ 100 % (77/77) | 2026-10-21 | 2026-10-22 |
| [ModBus du garage (P4, cuve, rideau) et commandes sans fil](plans/modbus-garage.md) | Fiabiliser le ModBus filaire du garage (P4, cuve, rideau) puis passer les commandes par UDP | clos | ██████████ 100 % (20/20) | — | 2026-10-22 |
| [Graphiques des mesures dans les pages web des cartes S3/P4 (uPlot)](plans/graphiques-web.md) | Afficher l'historique et le temps réel des mesures en graphiques dans les pages web des cartes S3/P4 | clos | ██████████ 100 % (80/80) | 2026-10-18 | 2026-10-20 |
| [La vue de droite suit le plan de la conversation active](plans/plan-par-conversation.md) | Faire afficher par la vue de droite le plan suivi par la conversation Claude active | clos | ██████████ 100 % (20/20) | 2026-10-18 | 2026-10-18 |
| [Suivi des plans de travail (extension VS Code + mod)](plans/suivi-plan.md) | Suivre l'avancement des plans en % dans une vue VS Code à droite, partagée entre conversations et postes | clos | ██████████ 100 % (23/23) | 2026-10-18 | 2026-10-18 |

<!-- fin-index-plans -->

## Plans plus anciens (hors format suivi, sans %)

Plans d'implémentation au format superpowers (`docs/superpowers/plans/`), sans cases cochées :
leur avancement se lit ailleurs.

| Plan | Objectif principal | Où en est-il |
|---|---|---|
| [Solidification Berry, phase 1](../docs/superpowers/plans/2026-07-15-solidification-berry-phase1.md) | Solidifier les modules Berry dans le firmware pour libérer la RAM | `tasks/reprise-solidification-berry.md` |
| [Annuaire des outils PC](../docs/superpowers/plans/2026-10-17-annuaire-outils.md) | Lister, lancer et arrêter les outils PC depuis une page (port 7600) | livré (`outils_pc/annuaire_outils.py`) |
