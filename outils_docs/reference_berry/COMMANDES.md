# Commandes Tasmota personnalisées des modules Berry

Liste des commandes ajoutées par les modules Berry de `data/` (`tasmota.add_cmd`, vérifiées le 2026-11-23 dans les `.be` hors `*sauvegarde*`). La seule commande de réglage des logs est `ReglageLog` (charte : `CLAUDE.md` § Logs Berry et `data/fs/logFonctions.be`) ; les anciens `logActivation` et `ReglageGlobal logLevel` n'existent plus.

Toute commande ci-dessous accepte `help` (ou `aide`, `?`) : `<Commande> help` liste ses sous-commandes, `<Commande> help <sous-commande>` en donne le détail. Un nombre collé au nom de la commande est l'index Tasmota (`RubanEsclave1` = commande `RubanEsclave`, index 1). `<ip>` remplace toute adresse d'exemple.

## ReglageGlobal (`data/fs/controleGeneral.be`)

- `ReglageGlobal afficheMemoire` : affiche l'utilisation des mémoires ROM, RAM et du garbage collector du module.
- `ReglageGlobal nbLogsFiles 14` : nombre de fichiers de logs gardés.
- `ReglageGlobal heureReboot 03:30 | OFF` : redémarrage quotidien à heure fixe, ou désactivé (sans valeur : état).
- `ReglageGlobal VoieReseau wifi | ethernet` : choisit la voie réseau (`serveur.voieReseau` du persist), puis redémarre. Les deux voies s'excluent et gardent l'IP de `serveur.IP` ; en Ethernet, la surveillance du Wi-Fi et le Range Extender sont désactivés. Sans lien Ethernet, la carte ne répond plus que sur sa console série (sans valeur : état).
- `ReglageGlobal timerRebootSansWifi 300 | OFF` : redémarrage après N s sans Wi-Fi d'affilée (60 s minimum), ou désactivé.

## ReglageLog (`data/fs/controleGeneral.be`)

- `ReglageLog` : affiche le profil de logs actif, les sorties et le réglage de chaque module.
- `ReglageLog help | help <sous-commande> | help niveaux` : aide en console.
- `ReglageLog profil normal|debug` : applique un profil aux sorties (série, web, mqtt, syslog).
- `ReglageLog modbus debug` : règle les logs d'un module (erreur, info, debug, detail).
- `ReglageLog tous detail` : règle d'un coup les logs de tous les modules de la carte.
- `ReglageLog syslog aucun` : règle une sortie du profil actif (aucun, erreur, info, debug, detail).

## Rubans WS2812

`ReglageLeds` (`data/fs/controleLeds.be`) :

- `ReglageLeds` : état du ruban (mode AUTO ou MANUEL, minutes restantes, couleur de la palette).
- `ReglageLeds rubanAuto | rubanManuel | rubanSuivante` : retour en AUTO, couleur figée, couleur suivante de la palette.
- `ReglageLeds rubanDuree 30` : durée du mode MANUEL en minutes (0 = jusqu'au double appui).
- `ReglageLeds rubanAppuiLong 15` : durée d'un appui long en dixièmes de seconde (SetOption32, commun à tous les boutons).
- `ReglageLeds rubanBouton` : mode d'emploi du bouton (court = allume ou éteint, long = couleur suivante, double = AUTO).
- Persist : `drivers.leds.environnement.leds.ruban`.

Sur le maître ModBus (`data/fs/modBus_TasmotaSlaveModBus.be`, enregistrée sous `RUBANESCLAVE`) :

- `RubanEsclave1 etat | auto | suivante` : mode du ruban de l'esclave du relais virtuel POWER1 (AUTO, ou MANUEL et minutes restantes), retour en AUTO, couleur suivante. L'index choisit le POWERn ; une réponse d'erreur dit si ce POWERn n'est pas un ruban virtuel ModBus. Bouton du maître : clé `bouton` du relais virtuel du ruban ; protocole : `outils_docs/reference_berry/PROTOCOLE_MODBUS.md`, fin du § 9.
- `HSBCOLOR1 <teinte>`, `HSBCOLOR2 <saturation>` et `DIMMER<id> <luminosité>` : sur un module à LEDs WS2812 pilotées en ModBus, remplacent les commandes Tasmota et envoient la valeur à l'esclave (`DIMMER 0` = POWER OFF).
- `SCHEME 0..14` : animation des rubans WS2812 des esclaves ModBus (0 = une seule couleur) ; sans paramètre : la valeur mémorisée.

## ReglageUDP (`data/fs/controleUDP.be`, `data/fs/udpFonctions.be::reglageUDP`)

- `ReglageUDP envoiUniCast <ip> <message>` : envoie un message UDP en unicast (test).
- `ReglageUDP envoiMultiCast <message>` : envoie un message UDP en multicast (test, Range Extender).
- `ReglageUDP forceEnvoiParams ON` : sur un esclave (`serveur.udp.id` > 0) seulement, envoie sa fiche de rôle de `/json/discovery.json` au maître (message `ImAlive`), puis ré-arme un envoi périodique à chaque `diverses.telePeriod` secondes.
- Internes, échangées entre modules : `ReglageUDP ImAlive <json>` (maître : range la fiche reçue), `ReglageUDP Timestamp <secondes>` et `ReglageUDP ipMaitre <ip>` (esclaves).
- L'ancienne sous-commande `telePeriodClients` n'existe plus dans le code (retirée de cette liste le 2026-11-23).

## Range Extender (`data/fs/controleRangeExtender.be`)

- `RoutageRangeExtender` : pose les redirections NAPT de tous les esclaves Range Extender en ligne de `/json/discovery.json` (équivalent de `RgxPort tcp, <routagePort>, <ip de l'esclave>, 80` pour chacun). Un index collé (`RoutageRangeExtender1`) est accepté mais ne filtre rien : `rangeExtenderFonctions.routageRangeExtender` ne s'en sert pas.
- `ReglageRangeExtender` : aucune sous-commande (voir plus bas).

## Cuve et capteurs (`data/garage/tasmota32s3-capteurs-cuve-modbus/controleCuve.be`)

- `ReglageCuve etalonnageCapteur ON` : augmente la fréquence de mesure pendant 10 min (une mesure toutes les 10 s).
- `Backlog ReglageCuve hauteurCuve 110; ReglageCuve largeurCuve 180; ReglageCuve longueurCuve 340` : force et enregistre les dimensions de la cuve.
- `ReglageAna voltageMax 3.3` : tension maximale admissible de l'ADS1115.
- `ReglageAna cablage` : rappelle le câblage des 4 voies de l'ADS1115 (pont diviseur ou shunt à poser, valeurs E24).
- `ReglageAna voie A0 tension 0-10V` : A0 et A1 en tension 0-5V, 0-10V ou 0-24V ; `ReglageAna voie A2 courant 4-20mA` : A2 et A3 en courant 0-20mA ou 4-20mA (boucle coupée détectée sous 3,6 mA).
- `ReglageAna seuilMin A0 50` : sous 50 mV à l'entrée de l'ADS1115, la lecture est une erreur (sonde débranchée) ; 0 = désactivé.
- `ReglageAna alimentation 3.3` : tension d'alimentation (VDD) de l'ADS1115, 3.3 ou 5 ; change les résistances conseillées. Câblage : `outils_docs/Electronique/ADS1115/CABLAGE_ADS1115.md`.
- Le simulateur `ReglageCuve simulation` est décrit dans `outils_docs/README.md`.

## ReglageModbus (`data/fs/controleModbus.be`, `data/fs/modbusFonctions.be::reglageModbus`)

- `ReglageModbus envoiMessageUDP <ip> TEST` : test, envoie le message en UDP unicast à l'IP.
- `ReglageModbus envoiMessagTCP <ip> TEST` : test, ouvre une connexion TCP et y écrit le message (orthographe de la sous-commande : `envoiMessagTCP`).
- `ReglageModbus BaudrateModbus 9600` : débit du bus.
- `ReglageModbus RecupereBaudrateConn16channels 0x01` et `ReglageModbus ReglageBaudrateConn16channels 0x01 19200` (ou `usine`) : lit et règle le débit de la carte 16 relais.
- `ReglageModbus TesteDebitConn16channels 0x01 9600` : teste la carte 16 relais à un débit donné, puis revient au bus.
- `ReglageModbus VerifieConn16channels [corrige] [<carte>]` : retrouve l'ID et le débit de la carte 16 relais, compare au persist, corrige si demandé.
- `ReglageModbus ActivationReponseCMD ON|OFF` : (dés)active la réponse de l'esclave aux commandes ModBus.
- `ReglageModbus RelaisPushMQTT ON|OFF` : (maître) recopie les push UDP des esclaves sur `tele/<topic>/MODBUSPUSH`, pour les observer depuis le réseau maison (OFF par défaut).
- Interne : `ReglageModbus ImAlive ON|OFF` force le maître à connecter ses clients ModBus TCP.
- `ReglageSlaveModBus1 id 0x02` (`data/fs/modBus_TasmotaSlaveModBus.be`) : change l'adresse ModBus de l'esclave `ModBus_TasmotaSlaveModBus1`.

## Cave

- `EtatPompe` : affiche l'état de la pompe vide-cave, des niveaux et de l'alerte.
- `AcquittePompe` : efface l'alerte et le compteur de relances, puis affiche l'état.
- Fichier : `data/cave/<carte>/controlePompeVideCave.be`.

## Volets

- `ReglageVolets Inclinaison <id>` : angle mesuré par le MPU6050 du volet.
- `ReglageVolets Apprentissage <id> ouvert|ferme` : apprend les butées du volet (voir `outils_docs/README.md` § « Inclinaison d'un volet ou d'une trappe »).

## Commandes sans sous-commande documentée ici

`ReglageGarage`, `ReglageDiscovery`, `ReglageRangeExtender`, `ReglageConn16Channel`, `ReglageTCP` et `ReglageLoRaWan` n'ont que `help` ; leurs logs se règlent avec `ReglageLog`. Quatre autres commandes existent dans le code sans avoir figuré dans l'ancienne liste : `ReglageHumidite` (`data/cave/<carte>/controleHumidite.be`), `ReglageMqttLiaison` (`data/fs/controleMqttLiaison.be`, voir `outils_docs/README.md` § « Voie MQTT maître/esclaves »), `ReglageDebits` et `ReglageEcranDebits` (dossiers des cartes de débits dans `data/bureau/`) : utiliser leur `help`.
