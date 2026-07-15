#-
    Ce module est conçu pour permettre la communication maitre-esclave
        entre 2 modules ESP32 équipés de Tasmota

    Pour l'aide au protocole ModBus: voir le fichier 'ModBus.help'

    Pour la transmission de données, on distingue les différents modes de communication suivants :
        - Modbus TCP : communication TCP/IP ETHERNET basée sur le modèle client/serveur
        - Modbus RTU : transmission asynchrone série via RS-232 ou RS-485
        - Modbus ASCII : similaire au protocole RTU, seulement un format de données différent, utilisation plutôt rare

    La communication entre Maitre et Esclaves ModBus peut être réalisée par connexion:
        - UDP : drivers["ModBus"]["typeComm"]["UDP"] == "ON"
        - TCP : drivers["ModBus"]["typeComm"]["TCP"] == "ON"
        - Serial: drivers["ModBus"]["typeComm"]["Serial"] == "ON"
        - MQTT: drivers["ModBus"]["typeComm"]["MQTT"] == "ON"

    Les communications ModBus UDP et TCP emettent et recoivent sur les ports par défaut de ces 2 protocoles:
        - UDP: Ports 2000 & 4000
        - TCP: Port 8888

    L'envoi des message ModBus est lancée par la fonction 'modbusFonctions.envoiMsgModbus(paramMSG)':
        - controle si le message peut être envoyé par:
            * voie serie: drivers["ModBus"]["typeComm"]["Serial"] = "ON" ==> fonction 'modbusFonctions.envoiMsgModbusSerial(paramMSG)'
            * voie UDP: drivers["ModBus"]["typeComm"]["UDP"] = "ON" ==> fonction 'modbusFonctions.envoiMsgModbusUDP(paramMSG)'
            * voie TCP: drivers["ModBus"]["typeComm"]["TCP"] = "ON" ==> fonction 'modbusFonctions.envoiMsgModbusTCP(paramMSG)'

    La réception des ordres (Esclaves ModBus) ou réponse à une commande (Maitre ModBus):
        - Port Série: la réponse est interceptée par la règle -> tasmota.add_rule('ModbusReceived') -> vers la fonction controleModbus.recupereReponseModBus()
            * lecture des données recues sur port série par le fonction 'modbusFonctions.lireMsgModbus'
        - Port TCP: la réponse est interceptée par la règle -> tasmota.add_rule('ModbusReceivedTCP') -> vers la fonction controleModbus.recupereReponseModBusTCP()
            * lecture des données recues sur port série par le fonction 'tcpFonctions.lireTCP()'
        - Port UDP: la réponse est interceptée par la règle -> tasmota.add_rule('ModbusReceivedUDP') -> vers la fonction controleModbus.recupereReponseModBusUDP()
            * lecture des données recues sur port série par le fonction 'udpFonctions.lireUDP(typeComm, paramMSG)'

    Un Flag 'modbusFonctions.attenteReponse': permet de savoir si une trame est recue après un ordre
        - 'modbusFonctions.attenteReponse' == false (Pas de réponse en attente):
            * quand le Driver est initialisée
            * quand une réponse est reçue et reconnue par la fonction 'modbusFonctions.lireMsgModbus()'
        - 'modbusFonctions.attenteReponse' == true (Réponse en attente):
            * quand le maitre a envoyé une commande: début de la commande 'modbusFonctions.envoiMsgModbus(paramMSG, typeMsg)'
            * après un délai de TimeOut défini par 'drivers['ModBus']['timeoutReponse']'

    Le calcul des erreurs de communication ModBus:
        - codeErreur (paramMSG[typeTitre]["Erreur"]):
            * 0: Pas d'Erreur
            * 1: Le message reçue n'est pas destiné à cet esclave (Adresse esclave incorrecte)
            * 2: Le CRC du message est incorrect
            * 3: Fonction ModBus non supportée par l'esclave
            * 4: Adresse de registre invalide
            * 5: Valeur de donnée invalide
            * 6: Longuer de trame invalide

    Fonctionnement global du module de contrôle ModBus TCP:
        - Berry tcpFonctions.be
            * Initialisé par: Événement System#Boot
            * Trame: Format custom "ModbusTCP " + trame
            * Connexions max: géré par vous
            * Intégration: Règle ModbusReceivedTCP manuelle
            * Fermeture: System#Save → serveur.close()


    Séquence complète des communications ModBusTCP
        Esclave (id > 0)                          Maitre (id == 0)
        System#Boot                               System#Boot
        → tcpserver(8888)                         → tcpclientasync()
        → attend hasclient()                      → client.connect("192.168.x.x", 8888)
            ↑                                           ↓
            └──────── connexion TCP établie ────────────┘
                            ↕
                modbusFonctions.envoiMsgModbusTCP()
                → client.write("ModbusTCP " + trame)
                            ↕
                lireTCP("Serveur") → connexionAsync.readbytes()
                → modbusFonctions.lireMsgModbus("ModbusReceivedTCP", msg)
                → tasmota.add_rule('ModbusReceivedTCP') déclenché

    Structure d'une trame Modbus TCP:
        * Une trame Modbus TCP = MBAP Header (7 octets) + PDU Modbus (variable)

        ┌───────────┬──────────┬──────────┬──────────┬──────────────────┐
        │Transaction│ Protocol │  Length  │  UnitID  │  PDU (Function   │
        │   ID (2)  │  ID (2)  │   (2)    │   (1)    │  Code + Data)    │
        └───────────┴──────────┴──────────┴──────────┴──────────────────┘
        Champ	            Taille	        Rôle
        Transaction ID	    2 octets	    Identifie la requête (permet d'associer réponse à demande)
        Protocol ID	        2 octets	    Toujours 0x0000 pour Modbus
        Length	            2 octets	    Nombre d'octets suivants (UnitID + PDU)
        Unit ID	            1 octet	        Remplace l'adresse esclave RTU (1-247)
        PDU	                variable	    Function Code + données (identique à RTU, sans CRC)
-#

var controleModbus

class CONTROLE_MODBUS : Driver
    # Variables

    # *************************************************
    # * Flags sur le port ModBus
    # *************************************************
    var timeout_ReponseModBus_ms                   # Délai max avant de déclarer un timeout
    var reponseModBus

    def init()
        import modbusFonctions
        import string
        import diversFonctions
        import introspect

        # *************************************************
        # * Flags sur le port ModBus
        # *************************************************
        self.timeout_ReponseModBus_ms = drivers["ModBus"].find("timeoutReponse", 1000)      # Délai max avant de déclarer un timeout
        self.reponseModBus = nil

        modbusFonctions.timeout_ReponseModBus_ms = self.timeout_ReponseModBus_ms
        modbusFonctions.attenteReponse = false

        # Règle la communication ModBus si activée (Si Eslave ModBus)
        modbusFonctions.log("CONTROLE_MODBUS: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Configure l'ouverture des ports ModBus (différents s'il s'agit d'un maitre ou d'un esclave)
        modbusFonctions.configModbusByJson()
        tasmota.yield()

        # Active les connexions TCP et UDP nécessaires aux communications ModBus
        # Utilisent le port 502 connexions TCP & par défaut pour les connexions UDP
        var modifID = false
        if (serveur["udp"].find("activation", "OFF") == "OFF")   
            serveur["udp"]["activation"] = "ON"
            serveur["udp"]["id"] = drivers["ModBus"]["id"]

            modifID = true
        else
            if (serveur["udp"]["id"] != drivers["ModBus"]["id"])
                serveur["udp"]["id"] = drivers["ModBus"]["id"]

                modifID = true
            end
        end

        if (serveur["tcp"].find("activation", "OFF") == "OFF")   
            serveur["tcp"]["activation"] = "ON"
            serveur["tcp"]["id"] = drivers["ModBus"]["id"]

            modifID = true
        else
            if (serveur["tcp"]["id"] != drivers["ModBus"]["id"])
                serveur["tcp"]["id"] = drivers["ModBus"]["id"]

                modifID = true
            end
        end

        if (modifID)    tasmota.cmd("Restart 1",boolMute)   end

        #-  Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
            - Message log sur connexion wifi
            - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
            - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        -#
        # tasmota.add_rule("Wifi", def(value, trigger, msg) modbusFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleModbus_System")
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) modbusFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleModbus_Mqtt") 
        tasmota.add_rule("System", def(value, trigger, msg) modbusFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleModbus_Wifi")
        # tasmota.add_rule("Time", def(value, trigger, msg) modbusFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleModbus_Time")

        # Si maitre ModBus peuvent reçoit une réponse après avoir envoyé un ordre
        # Si esclave ModBus, Analyse l'ordre, Execute la commande & Prépare la réponse
        if (drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON" && drivers["ModBus"]["id"] > 0)
            # Gestion des messages recus par ModbusReceived
            tasmota.add_rule('ModbusReceived', def(value, trigger, msg) self.recupereReponseModBus(value, trigger, msg)    end, "controleModbus_Received")
        end
        if (serveur["udp"].find("activation", "OFF") == "ON" && drivers["ModBus"]["typeComm"].find("UDP", "OFF") == "ON")
            # Gestion des messages recus par ModbusReceivedUDP
            tasmota.add_rule('ModbusReceivedUDP', def(value, trigger, msg) self.recupereReponseModBusUDP(value, trigger, msg)    end, "controleModbusUDP_Received")
        end
        if (serveur["tcp"].find("activation", "OFF") == "ON" && drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON" && drivers["ModBus"]["id"] > 0)
            # Gestion des messages recus par ModbusReceivedTCP
            tasmota.add_rule('ModbusReceivedTCP', def(value, trigger, msg) self.recupereReponseModBus(value, trigger, msg)    end, "controleModbusTCP_Received")
        end

        # Pour les esclaves ModBus, on attend une requête de lecture d'un registre ou d'une sortie numérique
        # On attend une requête par lecture régulière sur le port ModBus en utilisant la fonction BERRY 'serialRead()' tous les 250ms
        # L'esclave répond sur le port ModBus en utilisant la fonction BERRY 'serial.write()'

		# Ajoute les commandes personnalisées
		tasmota.add_cmd('ReglageModbus', modbusFonctions.reglageModbus)		
        
		# Stats d'utilisation des mémoires
		diversFonctions.statMemory()
    end

    # Réceptionne chaque trame dans un buffer:
    # - si maitre (id == 0) ==> RAS
    # - si esclave (id > 0) ==> Execute la commande : 'modbusFonctions.executeCmdModbus(paramMSG)' (Traite la trame & lance la commande si trame reconnue)
    def recupereReponseModBus(value, trigger, msg)
        import modbusFonctions
        import string

        # Uniquement si esclave ModBus (id > 0)
        if (drivers["ModBus"]["id"] == 0)   return      end

        # Test
        modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS: -------------------- modBus recupereReponseModBus -------------------", LOG_LEVEL_DEBUG_PLUS)
        modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS_TCP: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)
        modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS_TCP: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)
        modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS_TCP: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)

        # Détermine l'item à analyser dans le message ModBus recu
        var TypeMsg = ""
        if (string.find(trigger, "ModbusReceived#DeviceAddress") > -1)
            msg = msg["ModbusReceived"]
            TypeMsg = "Série"
        elif (string.find(trigger, "ModbusReceivedUDP#DeviceAddress") > -1)
            msg = msg["ModbusReceivedUDP"]
            TypeMsg = "UDP"
        elif (string.find(trigger, "ModbusReceivedTCP#DeviceAddress") > -1)
            msg = msg["ModbusReceivedTCP"]
            TypeMsg = "TCP"
        end
        modbusFonctions.log(f"MODBUS_RECUPERE_REPONSE_MODBUS: Type de msg Modbus = {TypeMsg:s}", LOG_LEVEL_DEBUG_PLUS)

        # Récupère la réponse à une requête ModBus
        self.reponseModBus = value
        if (self.reponseModBus != nil)
            modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS: Réponse ModBus reçue: " + str(self.reponseModBus), LOG_LEVEL_DEBUG)

            # Si aucune erreur détectée dans la trame reçue
            if (self.reponseModBus.find("Erreur", 0) == 0)
                # Si id(de l'esclave) == DeviceAddress
                if (self.reponseModBus["DeviceAddress"] == drivers["ModBus"]["id"])
                    modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS: Traitement du message en cours ...", LOG_LEVEL_DEBUG)
                    modbusFonctions.executeCmdModbus(self.reponseModBus)
                end
            end
        end
    end

    # Réceptionne chaque trame UDP dans un buffer
    def recupereReponseModBusUDP(value, trigger, msg)
        import modbusFonctions
        import json

        var tabFonctionsName = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
            tabFonctionsName.insert(1, "LECTURE_COILS")
            tabFonctionsName.insert(2, "LECTURE_ENTREES_DISCRETES")
            tabFonctionsName.insert(3, "LECTURE_REGISTRES_HOLDER")
            tabFonctionsName.insert(4, "LECTURE_REGISTRES_ENTREES")
            tabFonctionsName.insert(5, "ECRITURE_COIL_UNIQUE")
            tabFonctionsName.insert(6, "ECRITURE_REGISTRE_UNIQUE")
            tabFonctionsName.insert(0x0F, "ECRITURE_COILS")
            tabFonctionsName.insert(0x10, "ECRITURE_REGISTRES_HOLDER")
            tabFonctionsName.insert(0x11, "ISALIVE_ESCLAVE")

        # Récupère la réponse à une requête ModBus UDP
        self.reponseModBus = value
        if (self.reponseModBus != nil)
            # Initialise le flag d'attente de réponse
            modbusFonctions.attenteReponse = false

            # Pré-traitement de la trame reçue
            self.reponseModBus["FunctionName"] = tabFonctionsName[self.reponseModBus["FunctionCode"]]
            self.reponseModBus["DeviceAddress"] = int(self.reponseModBus["DeviceAddress"])
            # self.reponseModBus["Values"] = []
            if (type(self.reponseModBus["Values"]) == "int")
                self.reponseModBus["Values"] = [self.reponseModBus["Values"]]
            end
            modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS_UDP: Réponse ModBus UDP reçue: " + str(self.reponseModBus), LOG_LEVEL_DEBUG_PLUS)

            # Si maitre ModBus (id==0)
            if (drivers["ModBus"]["id"] == 0)

            # Si esclave ModBus (id>0)
            elif (drivers["ModBus"]["id"] > 0)
            # Si aucune erreur détectée dans la trame reçue
                if (self.reponseModBus.find("Erreur", 0) == 0)
                    # Si id(maitre ou esclave) == DeviceAddress
                    if (self.reponseModBus["DeviceAddress"] == drivers["ModBus"]["id"])
                        modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS_UDP: Traitement du message en cours ...", LOG_LEVEL_DEBUG_PLUS)

                        # Réinitialise le flag d'attente de réponse
                        modbusFonctions.attenteReponse = false

                        modbusFonctions.executeCmdModbus(self.reponseModBus)
                    else modbusFonctions.log("MODBUS_RECUPERE_REPONSE_MODBUS_UDP: Message ModBus reçu destiné à un autre esclave ...", LOG_LEVEL_DEBUG_PLUS)
                    end
                end
            end
        end
    end

    # Réceptionne chaque trame dans un buffer
    # Renvoi vers la fonction 'modbusFonctions.lireMsgModbus()'
    def every_100ms()
        import json
        import string
        import modbusFonctions  

        # Uniquement si communication ModBus Serial activée
        if (drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON")
            # Uniquement les esclaves ModBus (si esclave :id > 0)
            if (drivers["ModBus"]["id"] > 0)
                # Récupère les messages sur le port ModBus Serial (respecte l'API Tasmota) 
                modbusFonctions.lireMsgModbus("ModbusReceived", nil)     
                tasmota.yield()
            # Pour que les Maitres ModBus puissent recevoir les réponse automatiques des esclaves après l'envoi d'une commande
            # elif (drivers["ModBus"]["id"] == 0)
            #     # Récupère les messages sur le port ModBus Serial (respecte l'API Tasmota) 
            #     modbusFonctions.lireMsgModbus("ModbusReceived", nil)     
            #     tasmota.yield()
            end
        end
    end
end

# Active le Driver de controle global des modules
# Uniquement si esclave ModBus
if (drivers["ModBus"].find("activation", "OFF") == "ON")
    controleModbus = CONTROLE_MODBUS()
    tasmota.add_driver(controleModbus)
end