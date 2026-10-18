---
chantier: Modbus-garage
titre: ModBus du garage (P4, cuve, rideau) et commandes sans fil
statut: actif
crée: 2026-10-18
maj: 2026-10-18
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
- [X] Fixer le faux contact (réception, et émission le 2026-10-17 : coupure 22:31:37 → 22:39:30)
- [ ] Observation stable : au moins 1 h sans abandon sur les esclaves 1 et 2 (pont série + sniffeur)

## A5 — E3 sur la cuve (commandes par UDP)
- [ ] Sur accord : `ReglageModbus VoieCommandes UDP` sur la cuve
- [ ] Observer : `POMPE_QUEUE: envoi UDP` sur le P4, plus aucune trame de la cuve au sniffeur RS485
- [ ] Adapter la grille du testeur au mode UDP (critères de réception série)
- [ ] Repasser la grille en UDP ; retour possible par `ReglageModbus VoieCommandes Serial`

## A6 — Rideau (id 3)
- [ ] Rebuild et flash du rideau (muet, fiche périmée, sans E1)
- [ ] Grille ModBus filaire P4 ↔ rideau
- [ ] E4 : `ReglageModbus VoieCommandes UDP` sur le rideau, puis grille en UDP

## A7 — E5 et finitions
- [ ] E5 : débrancher le câble ModBus des esclaves (décision de l'utilisateur, après observation)
- [ ] Sur accord : C7 (sockets d'écoute ouvertes aussi sans MQTT, `DIAGNOSTIC_UDP_2026-10-17.md`)
- [ ] Sur accord : minuteur SerialLog de `logFonctions.appliqueProfil`

## Améliorations restantes
- [ ] [conversation] Pousser le commit 3b4d4fa36 (sur demande)
- [ ] [projet] Capteurs de la cuve une fois branchés : `I2CScan` → 0x48, `Status 10` → DS18B20 (pull-up 4,7 kΩ sur GPIO18)
- [ ] [projet] Synchro du fork (retard sur l'amont), sur `development` propre, avant la prochaine série de builds

## Vérification
Chaque étape sur carte se prouve par une ligne de log horodatée (pont série :7000, syslog :7200) ou par le
sniffeur ModBus :7300 ; chaque étape de code par un commit et le banc concerné (skill `bancs`).
Ni commit ni push sans demande ; aucune commande de réglage sur une carte sans accord.
