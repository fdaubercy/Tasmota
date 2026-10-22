---
chantier: Modbus-garage
titre: ModBus du garage (P4, cuve, rideau) et commandes sans fil
statut: clos
crée: 2026-10-18
maj: 2026-10-22
reprise: tasks/reprise-chantier-modbus-grenier.md
---
# ModBus du garage (P4, cuve, rideau) et commandes sans fil

## Contexte
Les 3 modules GARAGE : maître P4 (id 0), cuve (id 2), rideau (id 3), et la carte 16 relais (id 1).
Le nom de la reprise dit « grenier » : le grenier est en sommeil, ne pas y repartir.
Objectif : ModBus filaire fiable, puis commandes ModBus par UDP (E1-E5, `PROTOCOLE_MODBUS.md` §9),
esclave par esclave, avant de décider de débrancher le câble (E5).
Décisions tenues : ne pas toucher à l'AP des esclaves (192.168.4.1/24) ni à `USE_ESP32_WDT` ; pas de
MqttLog en debug sur un esclave ; capteurs de la cuve non branchés (sentinelles = normal).
Détail et preuves complètes : la reprise, encadré « ETAT AU 2026-10-17 SOIR ».

## A1 — Grille ModBus filaire P4 ↔ cuve
- [x] Tests 1 à 7 de la grille (`AUDIT_MODBUS_2026-09-29.md` §6) passés au testeur, onglet « Grille ModBus » — preuve : AUDIT §6 « VALIDÉE le 2026-10-17 pour le couple P4 ↔ cuve », décision de l'utilisateur ; commit e489ea1d4
- [x] Testeur : consigne qui disparaît, décompte, preuves des étapes corrigées — preuve : commit 0da23d052
- [x] Testeur : lignes longues envoyées par blocs de 64 octets (troncature série Tasmota) — preuve : commit 116c7cfa6, test 7 rejoué

## A2 — UDP maître ↔ esclave (C1-C6)
- [x] Émission liée à la STA de l'esclave, `ReglageGlobal ModeConnexion`, testeur UDP — preuve : commit 37276e5dc
- [x] Essais dans les deux modes (Range Extender, Wi-Fi classique) — preuve : testeur UDP 6/6 RECU + 10/10 cuve → P4 le 2026-10-17, `PROTOCOLE_MODBUS.md` §9

## A3 — E2 + E3 côté maître (routage par esclave)
- [x] Code : `voieDe`, `ipDe`, `noteIP`, `annonceRoute`, file mixte Serial/UDP, `envoieTeteUDP`, décodage des réponses côté maître — preuve : commit 2c79bda1f, banc_test_modbus 292/292
- [x] Rebuild complet et flash du P4 — preuve : P4 CfgHolder 1507, `voieDe`/`envoieTeteUDP` présents (introspect) le 2026-10-17
- [x] E2 observé : routes annoncées, tout reste en série, aucune erreur — preuve : `ROUTE_ESCLAVE: esclave d'ID=2 : voie Serial, IP 192.168.4.2 (fiche)` 22:30:29 ; `routesAnnoncees` {2, 3} ; commit 3b4d4fa36

## A4 — Câblage RS485 du P4
- [X] Fixer le faux contact (réception, et émission le 2026-10-17 : coupure 22:31:37 → 22:39:30) — preuve : câblage repris par l'utilisateur ; aucune coupure pendant l'observation ci-dessous ; rechute constatée le 2026-10-21 (P4 sans aucune réception série depuis son flash du 20, carte relais 1229/1229 au sniffeur), câbles du P4 repositionnés par l'utilisateur à ~06:12
- [x] Observation stable : au moins 1 h sans abandon sur les esclaves 1 et 2 (pont série + sniffeur) — preuve : 2026-10-18 12:00:00 → 13:02:30 (62,5 min), sniffeur : esclave 1 126/126, esclave 2 375/376 (la dernière en vol à l'arrêt), 0 sans réponse ; réceptions du P4 par MQTT 126 et 375, aucun trou > 5 min ; pont : 0 abandon sur 1 et 2 (les 123 abandons et 123 `MBR Recv timed out` sont tous le rideau, id 3, non flashé) ; RE-PROUVÉE le 2026-10-21 après le recâblage : 06:15:31 → 07:18:11 (62,7 min), carte relais 125/125 au sniffeur, 0 sans réponse, 125 réceptions du P4 ; cuve en UDP : 377 réceptions, aucun trou > 5 min, 0 abandon ni muet sur 1 et 2 (124 abandons = rideau, id 3)

## A5 — E3 sur la cuve (commandes par UDP)
- [x] Sur accord : `ReglageModbus VoieCommandes UDP` sur la cuve — preuve : accord « A5 » le 2026-10-18 ; cuve 13:36:43 `REGLAGE_VOIE_COMMANDES: commandes ModBus attendues par la voie UDP`, fiche republiée (MQTT + ImAlive) ; retour : `ReglageModbus VoieCommandes Serial`
- [x] Observer : `POMPE_QUEUE: envoi UDP` sur le P4, plus aucune trame de la cuve au sniffeur RS485 — preuve : P4 13:37:30 `ROUTE_ESCLAVE: esclave d'ID=2 : voie UDP, IP 192.168.4.2 (fiche)`, puis `envoi UDP ... ModbusUDP 1..12` (IP apprise dès le 2e) et `ModbusReceivedUDP` tid 1..12, aucun rejet `APPARIE_REPONSE` ; sniffeur : esclave 2 figé à 720/720 depuis 13:37:30 (avant : 717 à 13:36:42)
- [x] Adapter la grille du testeur au mode UDP (critères de réception série) — preuve : `testeur_udp_grille.py` (1d lit `voieCommandes`, tests 2 et 6 refusés sans elle ; 2p compte/interdit selon la voie, 2q, 2r ; test 6 UDP inversé avec pause 6p de 150 s) ; `test_testeur_udp.py` 242 vérifications, 0 échec ; 6 mutants sur 6 rendus rouges
- [x] Repasser la grille en UDP ; retour possible par `ReglageModbus VoieCommandes Serial` — preuve : grille du testeur, voie UDP lue en 1d, 2026-10-21 : 1 OK, 2 OK (30 envois UDP / 30 réponses), 3 OK (06:18, après recâblage du P4), 4 12/12, 5 10/11, 6 10/10 (6q à 06:20:37, après la pause), 7 5/6 ; validée par l'utilisateur avec 2 réserves : 5k (critère faussé par `StartAddress: 0` de la publication UDP, ruban bien en AUTO en 5l) et 7d (fiche périmée du rideau, réglée par A6)

## A6 — Rideau (id 3)
- [x] Rebuild et flash du rideau (muet, fiche périmée, sans E1) — preuve : considéré comme réalisé par décision de l'utilisateur le 2026-10-21 (non vérifié sur carte dans cette conversation)
- [x] Grille ModBus filaire P4 ↔ rideau — preuve : considéré comme réalisé par décision de l'utilisateur le 2026-10-21 (non vérifié sur carte dans cette conversation)
- [x] E4 : `ReglageModbus VoieCommandes UDP` sur le rideau, puis grille en UDP — preuve : considéré comme réalisé par décision de l'utilisateur le 2026-10-21 (non vérifié sur carte dans cette conversation)

## A7 — E5 et finitions
- [x] E5 : débrancher le câble ModBus des esclaves (décision de l'utilisateur, après observation) — preuve : rideau considéré comme fait par décision de l'utilisateur le 2026-10-21 (non observé sur le rideau, A6 également considérée comme réalisée) ; cuve : câble débranché par l'utilisateur vers 06:45 le 2026-10-21, observation 06:46:20 → 07:49:02 (62,7 min) VALIDE : cuve 375 réceptions UDP du P4, aucun trou > 5 min, 0 abandon ni muet ; carte relais 126/126 au sniffeur, 0 sans réponse ; MQTT connecté sans coupure (123 abandons = rideau, id 3). Reste le rideau, après A6
- [x] Sur accord : C7 (sockets d'écoute ouvertes aussi sans MQTT, `DIAGNOSTIC_UDP_2026-10-17.md`) — preuve : commit 3df7e35ff ; syslog du 2026-10-22 : P4 08:00:06.861/.862 et cuve 08:12:42.786/.788 `UDP_ECOUTE: ecoute UniCast ouverte sur le port 2000 !` puis `MultiCast ... 4000 !` moins d'1 s après `MQT: Connecté`, aucun `UDP_ECOUTE_SECOURS` ni `_ERREUR` ; cuve rejointe par UDP après son flash (6 `ModbusReceivedUDP` au P4 en 1 min) ; rideau à flasher plus tard (décision de l'utilisateur) ; accord le 2026-10-21 ; CODÉ : `udpFonctions.ouvreEcoute` / `secoursSansMqtt` + `every_second` de `controleUDP.be`, `test_discovery` 216/0 (ancien code 11 échecs, 3 mutants rouges), solidification OK, banc ModBus 309/309, relecteur-berry sans bloquant ; reste : rebuild complet + flash des 3 cartes, puis `UDP_ECOUTE` au démarrage
- [x] Sur accord : minuteur SerialLog de `logFonctions.appliqueProfil` — preuve : décision de l'utilisateur le 2026-10-21 : NE PAS désactiver, comportement par défaut de Tasmota conservé (log série coupé 600 s après le démarrage, `SERIALLOG_TIMER`, `tasmota.h:218`) ; pour suivre une carte plus longtemps, passer par MQTT, la console web ou le syslog

## Améliorations restantes
- [x] [conversation] Pousser le commit 3b4d4fa36 (sur demande) — preuve : déjà sur origin/development (`git merge-base --is-ancestor 3b4d4fa36 origin/development`), poussé avec 10d29fe93 le 2026-10-21
- [ ] [projet] Capteurs de la cuve une fois branchés : `I2CScan` → 0x48, `Status 10` → DS18B20 (pull-up 4,7 kΩ sur GPIO18)
- [x] [projet] Synchro du fork (retard sur l'amont), sur `development` propre, avant la prochaine série de builds — preuve : merge 4b31fd849 le 2026-10-21 (16 commits de l'amont), retard 0, local = origin

## Vérification
Chaque étape sur carte se prouve par une ligne de log horodatée (pont série :7000, syslog :7200) ou par le
sniffeur ModBus :7300 ; chaque étape de code par un commit et le banc concerné (skill `bancs`).
Ni commit ni push sans demande ; aucune commande de réglage sur une carte sans accord.
