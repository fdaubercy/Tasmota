# PLC et OpenPLC : cours et ressources

Écrit le 2026-11-15, à la demande de l'utilisateur. Tout vient des connaissances générales de Claude : **aucune adresse n'a été ouverte ni vérifiée**, et les titres de livres sont à contrôler avant achat.

## 1. Le PLC (automate programmable industriel, API)

Petit ordinateur durci qui pilote des machines et des installations : il lit des **entrées** (boutons, fins de course, capteurs), exécute un programme, écrit des **sorties** (relais, contacteurs, voyants). Il est fait pour tourner des années dans un coffret, avec parasites, chaleur et 24 V DC.

Ce qui le distingue d'un microcontrôleur nu (ESP32) :
- entrées et sorties isolées (optocoupleurs), tolérantes au bruit ;
- cycle déterministe, temps de réponse borné ;
- langages normalisés IEC 61131-3, lisibles par un électricien ;
- modularité : cartes d'E/S ajoutables ou remplaçables ;
- programme visible en direct, sans recompiler.

### Cycle de scrutation
1. Lecture des entrées, copiées dans une image mémoire figée.
2. Exécution du programme sur cette image.
3. Écriture des sorties depuis l'image.
4. Communication et diagnostics, retour au début.

Pendant un cycle, une entrée ne change pas de valeur dans le programme : le comportement est prévisible, mais une impulsion plus courte qu'un cycle peut être ratée.

### Langages IEC 61131-3
| Langage | Forme | Usage |
|---|---|---|
| LD (ladder) | Contacts et bobines, comme un schéma de relais | Le plus répandu |
| FBD | Blocs reliés par des fils | Régulation, calcul |
| ST (texte structuré) | Proche du Pascal | Algorithmes |
| IL | Assembleur simplifié | Obsolète |
| SFC (grafcet) | Étapes et transitions | Séquences |

Auto-maintien marche/arrêt, en ladder puis en texte structuré :

```
|--[ Marche ]--+--[/ Arret ]--( Moteur )--|
|              |                          |
|--[ Moteur ]--+                          |
```

```
Moteur := (Marche OR Moteur) AND NOT Arret;
```

### Entrées/sorties
Adresses : `%IX0.0` (entrée TOR), `%QX0.1` (sortie TOR), `%IW0` (entrée analogique 16 bits). Signaux : TOR, analogique (0-10 V, 4-20 mA), bus de terrain (ModBus RTU/TCP, Profibus, Profinet, CAN).

### PLC et domotique
Le PLC sert surtout aux installations techniques (chauffage, ventilation, pompes, volets) quand la fiabilité prime : la logique tourne même si le réseau ou le serveur tombe. Les systèmes grand public (Home Assistant, Tasmota, KNX) apportent prix, Wi-Fi et interfaces.

| | PLC industriel | ESP32 / Tasmota |
|---|---|---|
| Prix | 150 € à plusieurs milliers | 5 à 30 € |
| Robustesse | Très haute | Moyenne, selon le montage |
| Programmation | IEC 61131-3 | Berry, règles, C++ |
| Cycle déterministe | Oui | Non (Wi-Fi, GC, watchdog) |
| ModBus | Natif | Implémenté en Berry dans ce fork |

Le maître ModBus P4 et ses esclaves jouent déjà le rôle d'un PLC avec E/S distantes, sans les garanties de temps réel.

## 2. OpenPLC

Projet libre qui reproduit un PLC en logiciel :
- **OpenPLC Editor** : éditeur graphique des 5 langages, sur PC ;
- **OpenPLC Runtime** : moteur d'exécution (le programme est compilé en C), sur Raspberry Pi, Linux, Windows (Cygwin) et certaines cartes (ESP32, ESP8266, Arduino, STM32 selon les variantes) ;
- **interface web** : téléverser le programme, démarrer/arrêter, déclarer les périphériques ModBus, voir les variables.

Protocoles : ModBus (maître et esclave, RTU et TCP), DNP3, EtherNet/IP.

Mise en route : dessiner le programme, exporter le `.st`, le téléverser dans l'interface web, déclarer les esclaves ModBus et la correspondance avec `%IX`/`%QX`, démarrer.

Limites : temps réel mou sous Linux (cycle non garanti à la milliseconde) ; variantes ESP32 moins mûres que la version Raspberry Pi ; aucune certification de sécurité (pas d'arrêt d'urgence de personnes) ; communauté plus petite que celle des marques commerciales.

### Intérêt pour ce dépôt
OpenPLC aurait un sens pour remplacer la logique du maître P4 par un programme ladder, avec le Raspberry Pi SERVEUR-BUREAU comme maître ModBus et les cartes (relais, cuve, rideau) comme esclaves. La pile Berry + Tasmota fait déjà ce travail avec Wi-Fi, MQTT, pages web et historique, que OpenPLC ne fournit pas : pas de gain évident, sauf pour apprendre le ladder ou pour une partie très critique (pompe de cuve par exemple).

## 3. Ressources

### Sites
| Site | Intérêt |
|---|---|
| openplcproject.com | Site officiel : téléchargements, documentation, forum |
| github.com/thiagoralves/OpenPLC_v3 | Code du Runtime, installation |
| github.com/thiagoralves/OpenPLC_Editor | Code de l'éditeur |
| plcopen.org | Norme IEC 61131-3, blocs standard |
| plcacademy.com | Cours gratuits : ladder, texte structuré, grafcet |
| realpars.com | Cours et articles d'automatisme (anglais) |
| modbus.org | Spécifications officielles du ModBus |
| simplymodbus.ca | Trames et codes de fonction expliqués |
| beremiz.org | Autre environnement libre IEC 61131-3 |
| codesys.com | Environnement industriel, version de développement gratuite |
| github.com/pymodbus-dev/pymodbus | Tester un esclave ModBus depuis le PC en Python |
| tasmota.github.io, home-assistant.io | Lien avec la domotique |
| Wikipédia FR : Automate programmable industriel, Grafcet, Modbus | Introduction en français |

Testeurs et simulateurs ModBus : ModbusPal, Modbus Poll, QModMaster. Ladder sur microcontrôleur : LDmicro.

### Lectures
Livres (titres à vérifier) :
- « Automates programmables industriels », Mohamed Chaib (ou ouvrages équivalents chez Dunod) ;
- ouvrages sur le Grafcet (William Bolton, Éducation nationale) ;
- « Programmable Logic Controllers », W. Bolton (anglais) ;
- « Programming Industrial Control Systems Using IEC 1131-3 », R.W. Lewis (anglais).

Documents gratuits :
- cours de lycées techniques (STI2D, BTS électrotechnique, CIRA) : chercher « cours automate programmable pdf », « cours grafcet pdf » ;
- supports Siemens SCE et Schneider Electric Éducation ;
- « Modbus Application Protocol Specification » (modbus.org), court et utile pour le bus RS485 ;
- documentation du Runtime OpenPLC, sections ModBus et périphériques.

### Vidéos
Chaînes YouTube à chercher : OpenPLC Project (auteur du projet), RealPars, PLC Academy, chaînes françaises d'électrotechnique et d'automatisme.

Recherches utiles : « OpenPLC Raspberry Pi tutorial », « OpenPLC Modbus RTU slave », « ladder logic basics », « IEC 61131-3 explained », « grafcet exemple portail », « API Siemens S7-1200 débutant ».

### Ordre conseillé
1. Une vidéo d'introduction aux API.
2. simplymodbus.ca, pour relier le sujet au ModBus du dépôt.
3. Le tutoriel d'installation OpenPLC sur Raspberry Pi.
4. Un cours de grafcet, utile pour modéliser volets et portail.

## 4. Pistes de suite
- Essai sur le Pi avec OpenPLC et la carte 16 relais en ModBus RTU (voir `PROTOCOLE_MODBUS.md` § 8 pour la carte des registres).
- Comparaison de `data/fs/modbusFonctions.be` avec un cycle de scrutation PLC.
