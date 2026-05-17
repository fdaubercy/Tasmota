# MODBUS dans Tasmota

## Introduction

MODBUS est un protocole de communication série largement utilisé dans l'industrie pour la communication entre appareils électroniques. Dans Tasmota, MODBUS permet de communiquer avec des appareils compatibles MODBUS tels que des capteurs, actionneurs et contrôleurs industriels.

## Notes sur les communications ModBus
    - Les port RS485 est paramétré à l'ouverture du Driver
    - Ce module permet la mise en place d'une passerelle mqtt <-> RS485
    - Les trames sont composées de :
        * 1 caractère de début '\r'
        * DeviceAddress = adresse du dispositif destinataire
        * functionCode = numero code de la fonction à lancer
        * values = paramètre(s) sous format json (si plusieurs paramètres) ou string (1 seul paramètre)
        * 1 caractère de fin '\n'
    - Enregistre les modules esclaves et maitres en json 'RS485.json'

### Protocole personnalisé pour les envois automatiques par l'esclave sans ordre du Maitre
    - Les numéros d'identification des commandes restent les mêmes que selon le protocole officiel
    - Concerne les envois ModBus des esclaves sur modifications de toutes sortes de capteurs, entrées, sorties
    - On identifie ce type d'envoi automatique de l'esclave en mettant le bit 8 (bit de poids fort) à 1:
        * ex: la commande "Écriture de plusieurs registres (Write Multiple Registers)" = 0x10 (0b0001 0000)
                prend comme valeur -> 0x90 (0b1001 0000)
        * La formule de transformation est réalisé par une opération bit à bit: 0x80(0b1000 0000) OR 0x10(0b0001 0000) = 0x90(0b1001 0000)
        * La fonction OR bit à bit = '|' en codage BERRY
    - Si le bit8=1: 
        * le maitre reconnait que c'est un message automatique d'un esclave si: fonction AND 0x80 = 0x80
        * le maitre récupère la valeur de la fonction réelle: fonction reelle = fonction AND 0x7F

    - Les voies de communication par protocole ModBus sont paramétrées en json _persist.json:
        "typeComm": {
            "Serial": "OFF",        # Communication ModBus classique sur le port série (ModBusSend pour les maitres / Protocole & fonction BERRY pour les esclaves)
            "UDP": "ON",            # Communication ModBus par port UDP (MultiCast): Permet aux esclaves d'envoyer spontanément l'état de le ur capteur sans attendre un ordre du maitre
            "MQTT": "OFF",          # Non-implémenté
            "TCP": "OFF"            # Pas utilisé car ne fcontionne pas lorsque 2 modules (esclave + maitre) communiquent ensemble par l'intermédiaire du RangeExtender
        }

### Pour tester les commandes et les réponses ModBus
    - Désactiver la réponse des esclaves aux commandes Modbus: ReglageModbus ActivationReponseCMD OFF
    - Exemple de script ModBus berry à utiliser dans le console BERRY du Maitre:
        import modbusFonctions

        # Trame ModBus: 02040520000270FE
        trameModBus = {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "type":"float", "Count":1, "Values":0}
        modbusFonctions.envoiMsgModbus(trameModBus, "Commande", 1)
    - Exemple de script ModBus berry à utiliser dans le console BERRY de l'Esclave:
        import modbusFonctions
        import string

        var reponse = bytes("0204023FC00000 4CAC")
        modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Message ModBus envoyé = 0x%s", reponse.tohex()), LOG_LEVEL_DEBUG_PLUS)
        modbusFonctions.serialModBus.write(reponse)

### Pages HTML : 
    - https://en.wikipedia.org/wiki/Modbus
    - https://www.modbustools.com/modbus.html

    - Explications Fonctions ModBus Série:
        * https://www.simplymodbus.ca/FC01.htm
        * https://ipc2u.com/articles/knowledge-base/modbus-rtu-made-simple-with-detailed-descriptions-and-examples/
        * https://sti-monge.fr/maintenancesystemes/wp-content/uploads/2013/06/protocole-modbus.pdf
        * https://ozeki.hu/p_5846-appendix.html
        * https://yutec.fr/automatisme/protocole-de-communication/fonctions-modbus/

    - Explications Fonctions ModBus TCP:
        * https://ozeki.hu/p_5858-modbus-tcp.html

    - Calcul du CRC ModBus: https://crccalc.com/?crc=030201FF&method=CRC-16&datatype=hex&outtype=hex

### Liste des fonctions utilisées
        Code Fonction       Signification	                            Utilisation
        -----------------------------------------------------------------------------------------------------------
        0x01	            Lire Coils (relais ON/OFF)	                Lire l’état des relais
        0x02	            Lire Discrete Inputs (capteurs ON/OFF)	    Lire état des capteurs digitaux
        0x03	            Lire Holding Registers	                    Lire valeurs analogiques
        0x04	            Lire Input Registers	                    Lire entrées analogiques
        0x05	            Écrire un seul Coil	                        Activer/Désactiver un relais
        0x06	            Écrire un Holding Register	                Changer une valeur analogique
        0x08                Diagnostic Modbus                           Loopback Test, Echo, etc.
        0x0F	            Écrire plusieurs Coils	                    Changer plusieurs relais
        0x10	            Écrire plusieurs Holding Registers	        Envoyer plusieurs valeurs analogiques
        0x11                Rapport d’identification d’un esclave       Report Slave ID 
        0x14                Lecture des fichiers de registre            Read File Record
        0x16                Masquage d’un registre                      Mask Write Register
        0x17                Lecture/Écriture simultanée                 Read/Write Multiple Registers

## Exemples de commandes pour les Modules ModBus 16 channels

### Détails dans le fichier Word: '/Connecteur ModBus 16 channels/16 Channel  Multifunction RS485 Module commamd.docx'

#### Pour les platines 16 relais ================================================================================
    - Fermeture Relai 1: 01 06 00 01 01 00 D9 9A
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 1, "FunctionCode": 6, "StartAddress": 0x0001, "type":"uint8", "Count":1, "Values":[1,0]}

    - Ouverture Relai 1: 01 06 00 01 02 00 D9 6A
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 1, "FunctionCode": 6, "StartAddress": 0x0001, "type":"uint8", "Count":1, "Values":[2,0]}

    - Fermeture de tous les relais：01 06 00 00 07 00 8B FA
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 1, "FunctionCode": 6, "StartAddress": 0x0000, "type":"uint8", "Count":1, "Values":[7,0]}

    - Ouverture de tous les relais：01 06 00 00 08 00 8E 0A
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 1, "FunctionCode": 6, "StartAddress": 0x0000, "type":"uint8", "Count":1, "Values":[8,0]}

    - Lecture de l'état des 16 relais: 01 03 00 01 00 10 15 C6
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x01, "FunctionCode": 3, "StartAddress": 0x0001, "type":"uint16", "Count":16, "Values":[0, 16]}

#### Pour les paramètres ModBus =====================================================================
    - Lecture Slave ID: FF 03 00 FF 00 01 A1 E4
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0xFF, "FunctionCode": 3, "StartAddress": 0x00FF, "type":"uint16", "Count":1, "Values":1}

    - Ecriture Slave ID=2: 01 06 00 FF 00 02 F9 FB
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x01, "FunctionCode": 6, "StartAddress": 0x00FF, "type":"uint8", "Count":1, "Values":[0,2]}

    - Lecture Baudrate: 01 03 00 FE 00 01 E5 FA
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x01, "FunctionCode": 3, "StartAddress": 0x00FE, "type":"uint8", "Count":2, "Values":1}

    - Ecriture Baudrate: 01 06 00 FE 00 04 E9 F9
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x01, "FunctionCode": 6, "StartAddress": 0x00FE, "type":"uint8", "Count":1, "Values":[0,4]} 

    - Factory reset: 01 06 00 FE 00 05 28 39
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x01, "FunctionCode": 6, "StartAddress": 0x00FE, "type":"uint8", "Count":1, "Values":[0,5]}  

## Exemples de commandes pour les Modules TasmotaSlaveModBus (Modules Tasmota Esclaves ModBus) 
    - Ils mettent en place une communication ModBus par script BERRY

    - Communication Série RTU:
        * Le Maitre (id == 0): 
            . Au démarrage du module: Scanne en persist json si certaines devices virtuelles sont de type 'ModBus_TasmotaSlaveModbus' ou 'ModBus_Conn16Channel'
                -> Si présence de devices 'TasmotaSlaveModBus': Envoie une requete pour chaque device pour synchroniser leur état (ModBus_TasmotaSlaveModbus.changementEtatDemarrage(value, trigger, msg))
                -> Si présence de devices 'ModBus_Conn16Channel': Envoie une requete pour chaque device pour synchroniser leur état (ModBus_Conn16Channel.changementEtatDemarrage(value, trigger, msg))
            . Envoie des messages ModBus par la commande ModBusSend
            . pour debuggage: modbusFonctions.prepareTrame(paramMSG, typeMsg)
            . Recoit et traite la réponse "ModBusReceived" & Traite la réponse par la fonction 'modBus_TasmotaSlaveModBus.recupereReponseModBus(value, trigger, msg):
                Enregistre la donnée recue en _persist.json
                Publie en json Teleperiod Sensor
        * L'esclave (id > 0):
            . Recoit la commande par liaison série: modbusFonctions.lireMsgModbus("ModbusReceived", nil)
            . Publie en mqtt sur "ModbusReceived"
            . Traite la commande "ModbusReceived" par 'controleModbus.recupereReponseModBus(value, trigger, msg)
            . Traite la fonction ModBus par 'modbusFonctions.executeCmdModbus(self.reponseModBus)'
            . Répond par envoie de données ou confirmation de la commande par 'modbusFonctions.envoiMsgModbusSerial(paramMSG, "Réponse")' vers le maitre
    
    - Communication TCP:
        * Structure des message ModBus TCP:
            ------------------------- MBAP header ------------------------- | FunctionCode | Data | CRC
            ID Transaction | ID Protocole | Nb Octets de Trame | ID Esclave | FunctionCode | Data | CRC
            -------------------------------------------------------------------------------------------
        * ID Protocole == 0x0000
        * ID Transcation: incrémenter par le maitre ModBusTCP à chaque envoie 

        * Permet aux esclaves ModBus RTU d'envoyer spontanément les données des capteurs lorsqu'ils sont modifiés ou périodiquement
        * Fonctionne sur le port 502
        * Les esclaves (id == 0):
            . Démarrent en mode serveur TCP Asynchrone sur le port 502 (System#Boot)
            . Envoie l'état de capteurs sur modifications par la fonction 'globalFonctions.changementEtatCapteur(value, trigger, msg, moduleCapteur, cleBouton)'
            . La fonction d'envoi ModBus TCP: 'modbusFonctions.envoiMsgModbus(paramMSG, typeMsg, id)' -> 'modbusFonctions.envoiMsgModbusTCP(Trame, typeMsg)'

        * Le Maitre (id > 0):
            . Se connecte au port TCP 502 sur chaque esclave ModBus RTU (System#Boot)
            . Paramétrer le tableau des instances de client TCP pour la réception des trames

### Pour commander les relais et capteurs ======================================================================
     - Ecriture de l'état d'un relai 1 (temporisé ou non): 02 06 00 E0 02 00 89 6F
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x02, "FunctionCode": 0x06, "StartAddress": 256, "type":"uint8", "Count":1, "Values":[2, 0]}  

     - Ecriture des variables de LEDs WS2812A: 
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x02, "FunctionCode": 0x06, "StartAddress": 1376, "type":"uint16", "Count":3, "Values":[80, 100, 200]} 

     - Lecture de l'interrupteur 1: 03 02 00 A0 00 01 B8 0A
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x03, "FunctionCode": 0x02, "StartAddress": 160, "type":"uint8", "Count":1, "Values":0}   

     - Lecture du capteur 1: 03 02 00 A0 00 01 B8 0A
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x03, "FunctionCode": 0x02, "StartAddress": 160, "type":"uint8", "Count":1, "Values":0}  

     - Lecture du bouton 1: 
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x03, "FunctionCode": 0x02, "StartAddress": 32, "type":"uint8", "Count":1, "Values":0}  

     - Lecture de la valeur du capteur analogique 1: 
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x02, "FunctionCode": 0x04, "StartAddress": 4704, "type":"uint32", "Count":1, "Values":0} 

     - Lecture de la valeur du compteur 1: 
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x02, "FunctionCode": 0x04, "StartAddress": 352, "type":"uint32", "Count":1, "Values":0} 

     - Lecture de la température du DS18B20 1: 
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x02, "FunctionCode": 0x04, "StartAddress": 1312, "type":"float", "Count":1, "Values":0} 

     - Lecture de la température / humidité du DHT22 1: 
        * Commande Tasmota équivalente: ModBusSend {"DeviceAddress": 0x02, "FunctionCode": 0x04, "StartAddress": 1216, "type":"uint16", "Count":2, "Values":0} 

### Processus de communication & Explication du fonctionnement des scripts BERRY ===============================


## Protocole officiel ModBus RTU
    - Le protocole Modbus RTU est un protocole de communication série standard qui a été développé par Modicon en 1979.
    - Il est utilisé pour la communication entre plusieurs dispositifs connectés à la même ligne série.
    - Le protocole Modbus RTU est un protocole maître/esclave, ce qui signifie qu'un dispositif maître contrôle un ou plusieurs dispositifs esclaves.

    - Caractéristiques : 
        * Utilise une communication série sur RS485 ou RS232.
        * Format des trames en binaire, plus efficace que Modbus ASCII.
        * Nécessite un convertisseur RS485 (ex: MAX485).
        * Protocole basé sur UART (TX/RX).
        * Utilise CRC16 pour la détection d’erreurs.

    - Format des trames MODBUS : [ID Esclave] [Code Fonction] [Données] [CRC16]

### Codes de fonctions Modbus : 
    * 0x01  -> Lire les coils (bits) : 
        EXEMPLES : Etat des relais
        Chaque coil est un bit (0 ou 1) représentant une sortie numérique (variable binaire)
        Identifiés par une adresse unique dans la plage 00001 à 09999.
    * 0x02  -> Lire les entrées discrètes ==> Lecture de l'état d'interrupteurs/capteurs: 
        EXEMPLES : Etat des boutons ou interrupteur
        Valeur possible : 0 (OFF) ou 1 (ON).
        Lecture uniquement : Le maître ne peut que lire (Function Code 02).
        Utilisation : Lire l'état de boutons, capteurs, contacts, interrupteurs.
        Adresses Modbus : 10001 à 19999 (notation classique).
    * 0x03  -> Lire les registres de maintien (Holding Registers) :
        EXEMPLES : Valeur des consignes, paramètres (Sur 2 octets)
        Utilisé pour lire des données numériques stockées ou des paramètres
        Registres de maintien (Holding Registers)
        Adresses: 40001 à 49999 (dans la numérotation Modbus classique).
        Peuvent être lus et écrits.
        Utilisés pour stocker des valeurs comme des consignes, paramètres, états d’un capteur, etc.
        Chaque registre contient 16 bits (2 octets).
    * 0x04  -> Lire les registres d’entrée (Input Registers) ==> Lecture T°/Hum./Compteurs/Entrées analogiques:
        EXEMPLES : Valeur des capteurs (température, tension, pression, etc.).
        Adresses: 30001 à 39999.
        Lecture seule (le maître peut uniquement lire).
        Utilisés pour stocker des valeurs mesurées par des capteurs (température, tension, pression, etc.).
        Chaque registre contient 16 bits (2 octets).
    * 0x05  -> Écrire un coil
    * 0x06  -> Écrire un registre unique ==> Ecriture de la valeur de relais
    * 0x08  -> Diagnostic Modbus (Loopback Test, Echo, etc.)
    * 0x0F  -> Écriture multiple de Coils : Utilisé pour changer simultanément plusieurs sorties (Write Multiple Coils)
    * 0x10  -> Écrire plusieurs registres
    * 0x11  -> Rapport d’identification d’un esclave (Report Slave ID)
    * 0x14  -> Lecture des fichiers de registre (Read File Record)
    * 0x16  -> Masquage d’un registre (Mask Write Register)
    * 0x17  -> Lecture/Écriture simultanée (Read/Write Multiple Registers)

### functionCode < 5:

#### Exemple de trame de "Lecture des coils (bits) = 0x01"
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            L’esclave Modbus ID 1
        Code Fonction	        03	            Lecture des coils
        Adresse de départ	    00 01	        Lire à partir du coil 1
        Nombre de coils	        00 02	        Lire 2 coils
        CRC16	                95 CB	        Contrôle d’erreur

    - Reponse possible :
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l'esclave
        Code Fonction	        03	            Lecture de Coils
        Nombre d’octets	        01	            nb octets = (nb coils + 7) / 8 bits
        Valeurs des registres	03 	            Valeurs 0x03
        CRC16	                4E 87	        Contrôle d’erreur

#### Exemple de trame de "Lecture des Entrées Digitales (Read Discrete Inputs)" = 0x02
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l'esclave
        Code Fonction	        02	            Lecture des entrées digitales
        Adresse de départ	    00 10	        Lire à partir de l'entrée 16
        Nombre d'entrées	    00 08	        Lire 8 entrées
        CRC16	                79 C5	        Contrôle d’erreur

    - Reponse possible :
        Champ	                        Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse de l'esclave            01
        Code fonction                   02
        Nombre d’octets de données      01      nb octets = (nb coils + 7) / 8 bits => ici = (8+7)/8 = 1
        Valeurs des entrées             B2      Entrée 1à8
        CRC                             3F 1D

#### Exemple de trame de "Lecture des registres de maintien de 16 bits (Holding Registers)" = 0x03 
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            L'esclave Modbus avec l'ID 1
        Code Fonction	        03	            Lecture de registres "Holding" (0x03)
        Adresse de départ	    00 01	        Lire à partir du registre 1 (0x0001)
        Nombre de registres	    00 02	        Lire 2 registres
        CRC16	                B3 BC	        Contrôle d’erreur (vérifie si la trame est valide)

    - Reponse possible :
        Champ	                        Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse de l'esclave            01
        Code fonction                   03
        Nombre d'octets de données      04              nb octets = nb registres × 2 octets
        Valeurs des registres           12 34 56 78     Valeurs 0x1234 et 0x5678
        Contrôle d'erreur               CRC

#### Exemple de trame de "Lecture des entrées analogiques (Input Registers)" = 0x04
        Champ	                    Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	            01	            L’esclave Modbus ID 1
        Code Fonction	            04	            Lecture des entrées analogiques
        Adresse de départ	        00 01	        Lire à partir du registre 1
        Nombre de registres	        00 02	        Lire 2 registres
        CRC16	                    90 0B	        Contrôle d’erreur

    - Reponse possible :
        Champ	                    Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	            01	            ID de l'esclave
        Code Fonction	            04	            Lecture des entrées analogiques
        Nombre d’octets	            04	            nb octets = nb registres × 2 octets
        Valeurs des registres	    12 34 56 78	    Valeurs 0x1234 et 0x5678
        CRC16	                    F1 45	        Contrôle d’erreur

#### Exemple de trame de "Écriture d’une sortie digitale unique (Coil)" = 0x05
        Champ	                    Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	            01	            ID de l'esclave
        Code Fonction	            05	            Écriture d’une sortie digitale
        Adresse de la sortie	    00 01	        Sortie n°1
        Valeur à écrire	            FF 00	        Activer la sortie sur 2 octets (Normalement uint16)
        CRC16	                    DD FA	        Contrôle d’erreur

    - Reponse possible : L'esclave renvoie exactement la même trame s'il accepte la commande :

#### Exemple de trame de "Écriture dans un registre (Write Single Register)" = 0x06
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l'esclave
        Code Fonction	        06	            Écriture d'un registre
        Adresse du registre	    00 01	        Registre 1
        Valeur à écrire	        00 FF	        Écrire 0x00FF (Normalement uint16)
        CRC16	                89 D5	        Contrôle d’erreur

    - Reponse possible : L'esclave renvoie exactement la même trame s'il accepte la commande :

#### Exemple de trame de "Écriture multiple de sorties digitales (Write Multiple Coils)" = 0x0F
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l’esclave
        Code Fonction	        0F	            Écriture multiple de Coils
        Adresse de départ	    00 13	        Écriture à partir du Coil 19 (0x0013 en hex)
        Nombre de Coils	        00 0A	        10 Coils à écrire (0x000A en hex)
        Nombre d’octets	        02	            nb octets = (nb coils + 7) / 8 bits => ici = (10+7)/8 = 2
        Valeurs des Coils	    8C 01	        10001100 00000001
        CRC16	                49 5B	        Contrôle d’erreur

    - Reponse possible :
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l’esclave
        Code Fonction	        0F	            Écriture multiple de Coils
        Adresse de départ	    00 13	        Confirmation : écriture à partir du Coil 19
        Nombre de Coils	        00 0A	        Confirmation : 10 Coils écrits
        CRC16	                26 CF	        Contrôle d’erreur

#### Exemple de trame de "Écriture de plusieurs registres (Write Multiple Registers)" = 0x10
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l'esclave
        Code Fonction	        10	            Écriture de plusieurs registres
        Adresse de départ	    00 01	        Premier registre 1
        Nombre de registres	    00 02	        Nombre total : 2
        Nombre d’octets	        04	            nb octets = nb registres × 2 octets => ici 2 registres × 2 octets = 4
        Valeurs des registres	12 34 56 78	    Valeurs 0x1234 et 0x5678
        CRC16	                C5 F0	        Contrôle d’erreur

    - Reponse possible :
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l’esclave
        Code Fonction	        10	            Écriture de plusieurs registres
        Adresse de départ	    00 01	        Confirmation : Ecriture du registre 1
        Nombre de registres	    00 02	        Confirmation : Ecriture de 2 registres
        CRC16	                10 08	        Contrôle d’erreur

#### Exemple de trame de "Rapport d’identification d’un esclave (Report Slave ID)" = 0x11
        Champ	                Valeur	        Explication
        ----------------------------------------------------------------------
        Adresse Esclave	        01	            ID de l’esclave interrogé
        Code Fonction	        11	            Demande du rapport d’identification (Report Slave ID)
        CRC16	                6E 91	        Contrôle d’erreur

    - Reponse possible :
        L’esclave répond avec son ID, son statut, et des données additionnelles.

        Champ	                Valeur	                                                    Explication
        --------------------------------------------------------------------------------------------------------------------
        Adresse Esclave	        01	                                                        ID de l’esclave
        Code Fonction	        11	                                                        Réponse au rapport d’identification
        Nombre d’octets	        0D	                                                        Longueur des données suivantes
        Slave ID	            45	                                                        Identifiant unique de l’esclave
        Statut Run Indicator	FF	                                                        0xFF = Actif, 0x00 = Inactif
        Données Additionnelles	4D 6F 64 62 75 73 20 44 65 76 69 63 65 20 76 31 2E 30	    ASCII : "Modbus Device v1.0"
        CRC16	                6F 5A	                                                    Contrôle d’erreur


#### Récapitulatif de la structure des trames en fonction de 'fonctionCode'
    - COMMANDES :
        Catégorie de Commande         ---------------------- LECTURE ------------------------- | ------------------- ECRITURE ------------------ |
        Coil ou Registre              --------- COIL --------- | --------- REGISTRE ---------- | REGIST | REGIST | --- COIL --- | -- REGISTRE -- |
        Type de commande	          0x01       |  0x02       |  0x03         |  0x04         |  0x05  |  0x06  |  0x0F        |  0x10          |
        ------------------------------------------------------------------------------------------------------------------------------------------
        Adresse Esclave               XX         |  XX         |  XX           |  XX           |  XX    |  XX    |  XX          |  XX            |   
        Code Fonction                 XX         |  XX         |  XX           |  XX           |  XX    |  XX    |  XX          |  XX            |      
        Adresse de départ             XX XX      |  XX XX      |  XX XX        |  XX XX        |  XX XX |  XX XX |  XX XX       |  XX XX         |     
        Nombre de registres ou coil   XX XX      |  XX XX      |  XX XX        |  XX XX        |        |        |  XX XX       |  XX XX         |
        Nombre d’octets                          |             |               |               |        |        |  XX          |  XX            |
        Valeur(s) à écrire                       |             |               |               |  XX XX |  XX XX |  XX          |  XX XX         |     
        CRC16                         XX XX      |  XX XX      |  XX XX        |  XX XX        |  XX XX |  XX XX |  XX XX       |  XX XX         |
        ------------------------------------------------------------------------------------------------------------------------------------------ 
        Nombre total d'octets trame   8          |  8          |  8            |  8            |  8     |  8     |  9+nb_octet  |  9+(2*nb_reg)  |   

    - REPONSES POSSIBLES :
        Type de commande	          0x01       |  0x02       |  0x03         | 0x04          |  0x05  |  0x06  |  0x0F        |  0x10          |
        ------------------------------------------------------------------------------------------------------------------------------------------
        Adresse Esclave               XX         |  XX         |  XX           |  XX           |  XX    |  XX    |  XX          |  XX            |    
        Code Fonction                 XX         |  XX         |  XX           |  XX           |  XX    |  XX    |  XX          |  XX            |      
        Adresse de départ                        |             |               |               |  XX XX |  XX XX |  XX XX       |  XX XX         |      
        Nombre de registres ou coil              |             |               |               |        |        |  XX XX       |  XX XX         |
        Nombre d’octets               XX         |  XX         |  XX           |  XX           |        |        |              |                | 
        Valeur(s) à écrire ou lire    XX         |  XX         |  XX XX        |  XX XX        |  XX XX |  XX XX |              |                |
        Slave ID                                 |             |               |               |        |        |              |                |
        Statut Run Indicator                     |             |               |               |        |        |              |                |
        Données Additionnelles                   |             |               |               |        |        |              |                |     
        CRC16                         XX XX      |  XX XX      |  XX XX        |  XX XX        |  XX XX |  XX XX |  XX XX       |  XX XX         |
        ------------------------------------------------------------------------------------------------------------------------------------------
        Nombre total d'octets trame   5+nb_octet |  5+nb_octet |  5+(2*nb_reg) |  5+(2*nb_reg) |  8     |  8     |  8           |  8             |

## Configuration

### Activation du support MODBUS

Pour activer le support MODBUS dans Tasmota :

1. Compiler le firmware avec le support MODBUS activé
2. Configurer les paramètres MODBUS via l'interface web ou les commandes console

### Paramètres de configuration

- **Adresse MODBUS** : Adresse de l'appareil esclave (1-247)
- **Vitesse de transmission** : Baudrate (par défaut 9600)
- **Parité** : None, Even, Odd
- **Bits de données** : 8
- **Bits d'arrêt** : 1 ou 2

## Commandes MODBUS

### Commandes de base

- `ModbusSend` : Envoi d'une requête MODBUS
- `ModbusRead` : Lecture de registres
- `ModbusWrite` : Écriture de registres

### Exemples de commandes

```
ModbusSend 1,3,0,10,5  # Lecture de 5 registres à partir de l'adresse 0 sur l'esclave 1
ModbusRead 1,40001,10  # Lecture de 10 valeurs à partir du registre 40001
```

## Types de données MODBUS

- **Coils** : Registres binaires (0/1)
- **Discrete Inputs** : Entrées numériques
- **Holding Registers** : Registres de maintien (16 bits)
- **Input Registers** : Registres d'entrée (16 bits)

## Exemples d'utilisation

### Lecture d'un capteur de température

```
# Configuration
ModbusBaudrate 9600
ModbusConfig 1,8N1

# Lecture de la température (registre 40001)
ModbusRead 1,40001,1
```

### Contrôle d'un relais

```
# Activation d'un relais (coil 0)
ModbusWrite 1,0,1
```

## Dépannage

### Problèmes courants

- **Pas de réponse** : Vérifier l'adresse de l'esclave et la connexion physique
- **Erreurs de parité** : Vérifier les paramètres de communication
- **Timeouts** : Ajuster le délai d'attente MODBUS

### Commandes de diagnostic

- `ModbusScan` : Scanner les appareils sur le bus
- `ModbusDebug` : Activer le mode debug

## Ressources supplémentaires

- [Spécification MODBUS](https://modbus.org/specs.php)
- [Documentation Tasmota](https://tasmota.github.io/docs/)
- [Forum Tasmota](https://forum.tasmota.com/)
