# Reprise : ModBus du garage

> Réécrit le 2026-11-23 à partir de l'ancienne reprise (45 Ko, archivée dans `tasks/archive/reprise-chantier-modbus-grenier.md`).
> Chaque point « reste » ci-dessous a été revérifié le 2026-11-23 dans le code, git et les plans. Mettre ce fichier à jour, ne pas en créer un second.

## SI TU REPRENDS À FROID

Le chantier ModBus (ancien nom : « grenier ») porte sur le **GARAGE**. Le grenier (`tasmota32s3-etage2-grenier`) est en sommeil : ne pas y repartir (erreur du 2026-07-24, voir `tasks/lessons.md`).
Travail sur `development`. Plan suivi : `tasks/plans/modbus-garage.md` (clos le 2026-10-22). Prolongement actif : `tasks/plans/voie-mqtt.md` (voie MQTT, essais A10 du portail).
Prochaine action ouverte : essai du **rideau (id 3)** sur carte, voir « Ce qui reste ».

## Cibles

- Maître P4 (id 0) : `data/garage/tasmota32p4-serveur-modbus/`, env `tasmota32p4-garage-serveur-modbus`. Porte aussi la carte 16 relais (id 1, RS485).
- Cuve (id 2) : `data/garage/tasmota32s3-capteurs-cuve-modbus/`, env `tasmota32s3-garage-capteurs-cuve-modbus`.
- Rideau (id 3) : `data/garage/tasmota32s3-rideau-garage-modbus/`, env `tasmota32s3-garage-rideau-garage-modbus`.
- Portail de jardin (esclave 4) : `data/garage/tasmota32-portail-jardin-modbus/` (ESP32) et `tasmota32s3-portail-jardin-modbus/` ; jamais de commande réelle sans l'utilisateur (`voie-mqtt.md` A10).

## Décisions tranchées (ne pas rouvrir)

- RS485 / ModBus RTU, on part des fichiers existants (pas de réécriture), pas de MBAP, pas de driver natif `xdrv_94_modbus_relay`.
- Ne pas toucher à l'AP des esclaves (192.168.4.1/24), ni à `USE_ESP32_WDT`. Pas de MqttLog en debug sur un esclave derrière le NAPT. Log série coupé 600 s après le démarrage (`SERIALLOG_TIMER`) : gardé par choix.
- Capteurs de la cuve : 2147483647 et null sont les sentinelles « pas de mesure » (`modbusFonctions.be`, section sentinelle de `PROTOCOLE_MODBUS.md` §9), pas un défaut.
- Timeouts sur TOUS les esclaves alors que le sniffeur voit leurs réponses : vérifier d'abord le câblage de réception du P4 (faux contact constaté les 17 et 21/10).
- Rebuild complet obligatoire après toute modification d'un module solidifié (`modbusFonctions`, `udpFonctions`, `controleModbus`) : un `uploadfs` ne suffit pas. Le persist du dépôt doit être à jour avant un flash (il remplace celui de la carte).
- Phase 3 (scission de `modbusFonctions.be` par rôle) : non lancée, ne pas la lancer telle quelle (frontière fausse sur le garage, `lireMsgModbus` sert aussi le maître ; fichier déclaré exception des 500 lignes dans `CLAUDE.md`).

## Fait (preuves)

- Grille de l'audit validée P4 et cuve le 2026-10-17 (`AUDIT_MODBUS_2026-09-29.md` §6), re-prouvée en UDP le 2026-10-21 ; commandes sans fil C1 à C7, E1 à E3, E5 de la cuve : `PROTOCOLE_MODBUS.md` §9 et plan `modbus-garage.md` A1 à A7.
- `seq` du push (ancien « bloqué par une décision ») : FAIT. Commit `4532f12ec` dans `development` ; émis par `modbusFonctions.be::pousseEtat`, contrôlé par `modbusFonctions.be::accepteSeq` ; `ACCEPTE_SEQ` observé sur le P4 le 2026-10-17 20:33.

## Ce qui reste (vérifié le 2026-11-23)

1. **Rideau (id 3), jamais vérifié sur carte** : flash, grille filaire, E4 (`ReglageModbus VoieCommandes UDP`), E5 (câble débranché) et lignes `UDP_ECOUTE` (C7) sont « considérés réalisés par décision de l'utilisateur le 2026-10-21 » (`modbus-garage.md` A6, A7). Code livré : `fa2b919bf` (commandes par UDP), `c7ecb23ce` (fsMqtt). Rideau hors ligne à ce jour d'après `tasks/lessons.md` du 2026-11-14.
2. `BUS_SERIE_MUET` : détecteur codé (`66640e431`, `modbusFonctions.be::noteBusMuet`) après les silences du bus du 24/10 ; aucun déclenchement consigné depuis dans les plans ni les leçons. Au prochain cas : tas haut = câblage ou émetteur, tas bas = RAM ; sans cas en quelques jours, classer.
3. Capteurs de la cuve à brancher : `I2CScan` doit montrer 0x48, `Status 10` le DS18B20 (pull-up 4,7 kΩ sur GPIO18) ; case ouverte de `modbus-garage.md`.
4. Réserve 5k de la grille UDP : la publication UDP porte `StartAddress: 0`, ce qui fausse le critère du testeur (`testeur_udp_grille.py`) ; à trancher (corriger le critère ou la publication).
5. Mineurs : cavalier M0 de la carte 16 relais non confirmé (pas de `cavalierM0` dans le persist du P4 ; poser `"connecte"` si 16 écarts d'un coup) ; `# TODO` du type `"bit"` dans `modbusFonctions.be::prepareTrame`.

Périmés et retirés de l'ancienne reprise : « flasher et observer » (fait), `clients[id]` créé avant `id` (corrigé le 2026-09-29), UDP à `OFF` (activé par `66c75a320`), TCP cassé.

## Renvois

`outils_docs/PROTOCOLE_MODBUS.md` §8 (carte 16 relais), §9 (synchronisation, commandes sans fil), §11 (voie MQTT) ; `outils_docs/AUDIT_MODBUS_2026-09-29.md` §6 (grille) ; `outils_docs/DIAGNOSTIC_UDP_2026-10-17.md` ; sniffeur et testeur : `outils_docs/README.md`. Archive : `tasks/archive/reprise-chantier-modbus-grenier.md` (encadrés « ÉTAT AU » d'origine, détail des essais).
