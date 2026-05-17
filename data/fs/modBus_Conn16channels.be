#- NOTES Sur le module ModBus 16 sorties numériques
    - 16 sorties numériques (coils) de 1 à 16
    - ModBus.help peut vous aider à comprendre la gestion des communications
    - Utilise le Driver ModBus natif de Tasmota
    - Les commandes et les propriétés du module sont décrites dans le fichier '16 Channel  Multifunction RS485 Module commamd.docx'
    - Les relais de la platine 16 relais sont des relais inversés (circuit fermé lors de la presence de 0V sur la borne de commande)
-#

#- Réglage initial du module
    - L'adresse du module vierge est: 0x01
    - Le BaudRate configuré en usine: 9600 bps
        * Configurer le débit ModBus de Tasmota temporairement: 
                var ser = serial(4, 5, 1200, serial.SERIAL_8N1)
                ser.write(bytes("010300FE0001E5FA"))
                tasmota.delay(1000)
                msg = ser.read()
                print(msg.asstring())
                print(ser.available())
                
                tasmota.cmd("ModbusBaudrate 9600")
                tasmota.cmd("ModBusSend {\"deviceaddress\": 1, \"functioncode\": 3, \"startaddress\": 0xFE, \"type\":\"uint16\", \"count\":1}")
-#

var modBus_Conn16channels

class MODBUS_CONN_16CHANNEL : Driver
    # Variables
    var nbIOActivesJSON
    var DEBUG

    def init()
        import json
        import gestionFileFolder
        import string

        self.DEBUG = nil
        self.nbIOActivesJSON = nil

        # Enregistre ou Mets à jour en variable les capteurs activés dans un tableaus
        self.nbIOActivesJSON = json.load(gestionFileFolder.readFile("/json/nbIOActives.json"))

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
        tasmota.add_rule("System", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end) 

        # Si maitre ModBus peuvent reçoit une réponse après avoir envoyé un ordre
        # Et ajoute le résultat en json
        for cle: drivers["ModBus"]["environnement"]["Conn16channels"].keys()
            tasmota.yield()
            if type(drivers["ModBus"]["environnement"]["Conn16channels"][cle]) != "instance"   continue    end

            if (drivers["ModBus"]["environnement"]["Conn16channels"][cle].find("activation", "OFF") == "ON")
                # Ajoute une règle pour chaque module Conn16Channels
                # Gestion des messages recus par ModbusReceived
                if (drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON")
                    tasmota.add_rule(string.format("ModbusReceived#DeviceAddress==%i", drivers["ModBus"]["environnement"]["Conn16channels"][cle]["id"]), def(value, trigger, msg) self.recupereReponseModBus(value, trigger, msg)    end, "conn16channelsModBus_Received")
                end
            end
        end

        # Ajoute les commandes personnalisées si le module est activé
        tasmota.add_cmd('ReglageConn16Channel', def(cmd, idx, payload, payload_json)  self.reglageConn16Channel(cmd, idx, payload, payload_json)  end)
    end

    def log(msg, levelDebug)
        import persist
        import string
    
        if (self.DEBUG == nil)
            self.DEBUG = drivers["ModBus"]["environnement"]["Conn16channels"].find("debug", "OFF")
        end
    
        if (self.DEBUG == "ON")
            log(msg, levelDebug)
        end
    end

    #- Exemples: 
        ReglageConn16Channel logActivation OFF   => Active ou désactive les logs du module
    -#
    def reglageConn16Channel(cmd, idx, payload, payload_json)
        import string
        import json
        import persist

        var fonction = false
        var parametres = []
        var reponse_cmnd
        
        # Test   
        self.log("REGLAGE_MODBUS_CONN_16CH: -------------------- ReglageConn16Channel -------------------", LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

        # Détermine la fonction appelée et ses paramètres
        if string.find(payload, " ") > - 1
            parametres = string.split(payload , " ", 1)
            fonction = parametres.pop(0)
        else fonction = payload
        end

        log("REGLAGE_MODBUS_CONN_16CH: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
        if (parametres.size() > 0)	log("REGLAGE_MODBUS_CONN_16CH: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
        if (parametres.size() > 1)	log("REGLAGE_MODBUS_CONN_16CH: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

        # Activation ou désactivation des logs de gestion de la garage -> ordre: logActivation
        if (string.toupper(fonction) == string.toupper("logActivation"))
            try
                # Adapte le paramètre
                parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
                self.DEBUG = parametres[0]

                # Sauvegarde le paramètre
                drivers["ModBus"]["environnement"]["Conn16channels"]["debug"] = parametres[0]
                persist.save()
            except .. as e, m
                # print('Erreur: ', e, " -> ", m)
            end
        end

        # Commande réussie
        # Réponse à la commande
        reponse_cmnd = string.format("reglageConn16Channel: id=%i, logActivated=%s", idx, self.DEBUG)
        tasmota.resp_cmnd(json.dump(reponse_cmnd))
    end

    # Pour le maitre ModBus: A chaque réception d'une trame ModBus de la part d'un module conn16Channel
    # Modifie en persist json: la valeur de la device en fonction du message ModBus recu.
    def recupereReponseModBus(value, trigger, msg)
        import modbusFonctions
        import string
        import json

        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: -------------------- Conn16channels recupereReponseModBus -------------------", LOG_LEVEL_DEBUG)
        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: value = " + str(value), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: trigger = " + str(trigger), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: msg = " + str(msg), LOG_LEVEL_DEBUG_PLUS)

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
        self.log(f"MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: Type de msg Modbus = {TypeMsg:s}", LOG_LEVEL_DEBUG_PLUS)

        # Certaines fonctions ne retournent aucune données
        msg["FunctionName"] = modbusFonctions.tabFonctionsName[msg["FunctionCode"]]
        self.log(string.format("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: FunctionCode = 0x%02X ('%s')", msg["FunctionCode"], msg["FunctionName"]), LOG_LEVEL_DEBUG_PLUS)

        if (msg["FunctionName"] == "ECRITURE_REGISTRES_HOLDER")
            # Initialise le buffer & le Flag d'attente de réponse après ordre
            modbusFonctions.attenteReponse = false

            return
        end

        # Parcours les devices virtuels ModBus
        for cleModule: modules.keys()
            tasmota.yield()

            if (type(modules[cleModule]) != "instance")   continue      end

            var env = modules[cleModule]["environnement"]
            if (env)
                for cleEnv: env.keys()
                    if type(env[cleEnv]) != "instance"   continue    end

                    for cleDevice: env[cleEnv].keys()
                        if type(env[cleEnv][cleDevice]) != "instance"   continue    end
                        tasmota.yield()




                        
                    end
                end
            end

            # Modifie en json persist
            modules[cleModule]["environnement"] = env
        end

        # Ajoute la donnée reçue en json
        # self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: dataJson=" + json.dump(self.dataJson), LOG_LEVEL_DEBUG_PLUS)

        # Initialise le buffer & le Flag d'attente de réponse après ordre
        modbusFonctions.attenteReponse = false
    end

    # Règles sur changement d'état lors du démarrage de Tasmota
    def changementEtatDemarrage(value, trigger, msg)
        import string
        import json
        import re
        import modbusFonctions

        # Test
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: -------------------- Conn16Channel changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
        
        if (type(value) == "instance")
            for cle: value.keys()
                value = value[cle]
            end
        end

        tasmota.yield()

        # Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
        # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
        # Save: Avant redemarrage de tasmota
        if (trigger == "System")
            if msg[trigger].find("Boot", 0)
                # Configure les relais virtuels ModBus si ils existent et sont paramétrés
                # Gère les commandes envoyées aux devices ModBus du Conn16channel au demarrage
                # Parcours les devices virtuels ModBus
                for cleModule: modules.keys()
                    tasmota.yield()
                    if (type(modules[cleModule]) != "instance")   continue      end

                    try
                        for cleDevices: modules[cleModule]["environnement"].keys()          # ex: cleDevices = "relais", "capteurs", etc.
                            var devices = modules[cleModule]["environnement"].find(cleDevices, false)

                            if (type(devices) != "instance")   continue      end

                            if (devices)
                                var tabEtatRelais = nil

                                if (cleDevices == "relais")
                                    tabEtatRelais = tasmota.get_power()
                                end

                                for cleDev: devices.keys()      # ex: "relai1", "capteur2", etc.
                                    if type(devices[cleDev]) != "instance"   continue    end
                                    tasmota.yield()

                                    # Si le relai est activé (réels + virtuels)
                                    if (devices[cleDev].find("activation", "OFF") == "ON" && devices[cleDev].find("virtuel", "OFF") != "OFF")
                                        if ((string.find(devices[cleDev]["virtuel"], "ModBus_Conn16channel") > - 1) && (devices[cleDev].find("idModBus", false) != false))
                                            var valueModBus
                                            
                                            if (cleDevices == "relais")
                                                # Rappel de l'état des relais avant redémarrage
                                                if (tabEtatRelais[devices[cleDev]["id"] - 1] == true)    
                                                    tabEtatRelais[devices[cleDev]["id"] - 1] = "ON"
                                                else tabEtatRelais[devices[cleDev]["id"] - 1] = "OFF"    
                                                end  

                                                # Componentes   -> type=224: "Relais",
                                                #               -> type=256: "Relais_i"
                                                if (devices[cleDev]["type"] == 224)
                                                    valueModBus = (devices[cleDev]["etat"] == "ON" ? 0x02 : 0x01)
                                                elif (devices[cleDev]["type"] == 256)
                                                    valueModBus = (devices[cleDev]["etat"] == "ON" ? 0x01 : 0x02)
                                                end

                                                # Execute la commande 'Power' si différent
                                                if (tabEtatRelais[devices[cleDev]["id"] - 1] == devices[cleDev]["etat"])        continue    end
                                            end

                                            var typeConnex = string.split(devices[cleDev]["virtuel"], "_")[0]
                                            var moduleConnex = string.split(devices[cleDev]["virtuel"], "_")[1]
                                            var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", string.split(devices[cleDev]["virtuel"], "_")[1])[0]

                                            if (typeConnex == "ModBus")
                                                if (devices[cleDev].find("idModBus", false) != false)
                                                    # Construit la trame
                                                    # Relai fermé si borne de commande à l'état bas (0V): valueModBus = 0x01
                                                    # Relai ouvert si borne de commande à l'état haut (+5V): valueModBus = 0x02
                                                    var trameModBus = 	{
                                                                            "DeviceAddress": drivers["ModBus"]["environnement"][groupeConnex][moduleConnex]["id"],
                                                                            "FunctionCode": 0, 
                                                                            "StartAddress": 0, 
                                                                            "type": "", 
                                                                            "Count": 0, 
                                                                            "Values": []
                                                                        }

                                                    # Envoi l'ordre sur le réseau ModBus
                                                    if (cleDevices == "relais")
                                                        trameModBus["FunctionCode"] = 0x06
                                                        trameModBus["StartAddress"] = devices[cleDev]["idModBus"] 
                                                        trameModBus["type"] = "uint8"
                                                        trameModBus["Count"] = 1
                                                        trameModBus["Values"] = [valueModBus, 0]
                                                                                        
                                                        tasmota.cmd(string.format("Power%i %s", devices[cleDev]["id"], devices[cleDev]["etat"]))
                                                        modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"]) 
                                                        self.log(string.format("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: Commande sur le réseau ModBus pour le relai n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO) 
                                                    end
                                                end
                                            end
                                        end
                                    end 
                                end
                            end
                        end
                    except .. as error, message
                        modbusFonctions.log(string.format("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                    end
                end
            end
        end
    end
end

# Active le Driver de controle global des modules
if (controleGeneral.nbIOActivesJSON["relais"]["actives"]["nb"] > controleGeneral.nbIOActivesJSON["relais"]["reels"]["nb"])
    if (drivers["ModBus"].find("activation", "OFF") == "ON")
        for cle: drivers["ModBus"]["environnement"]["Conn16channels"].keys()
            import string

            if type(drivers["ModBus"]["environnement"]["Conn16channels"][cle]) != "instance"   continue    end

            try
                if (drivers["ModBus"]["environnement"]["Conn16channels"][cle].find("activation", "OFF") == "ON")
                    modBus_Conn16channels = MODBUS_CONN_16CHANNEL()
                    tasmota.add_driver(modBus_Conn16channels)

                    log("MODBUS_CONN_16CHANNEL: Driver activé !", LOG_LEVEL_DEBUG)

                    break
                end
            except .. as error, message
                log(string.format("MODBUS_CONN_16CHANNEL_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
            end
        end
    end
end