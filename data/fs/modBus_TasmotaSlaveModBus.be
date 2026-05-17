#- NOTES Sur l'ajout de fonctionnalité pour les maitres des modules ModBus TasmotaSlave
    - ModBus.help peut vous aider à comprendre la gestion des communications
    - Utilise le Driver ModBus natif de Tasmota
    - Chargé de créer les devices virtuels ModBus
    - Donne de nouvelles compétences de controleau maitre sir les modules Tasmota utilisés comme esclaves ModBus
    - Gère les commandes envoyées sur les ports ModBus en fonction des types (relais, interrupteurs, capteurs, boutons, thermometres ...)
    - Crée des règles ou commandes similaires à celles de Tasmota pour les devices virtuelles
-#

var modBus_TasmotaSlaveModBus

class MODBUS_TASMOTA_SLAVE : Driver
    # Variables
    var nbIOActivesJSON
    var dataJson
    var DEBUG

    def init()
        import json
        import string
        import gestionFileFolder

        self.DEBUG = nil
        self.nbIOActivesJSON = nil
        # self.idModule = idModule
        self.dataJson = {"TasmotaSlaveModBus": {}}

        # Paramètre dataJson par défaut
        for cle: drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].keys()
            tasmota.yield()
            if type(drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]) != "instance"   continue    end

            if (drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle].find("activation", "OFF") == "ON")
                self.dataJson["TasmotaSlaveModBus"].insert(cle, {})
            end
        end

        # Enregistre ou Mets à jour en variable les capteurs activés dans un tableaus
        self.nbIOActivesJSON = json.load(gestionFileFolder.readFile("/json/nbIOActives.json"))

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
        tasmota.add_rule("System", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end) 

        # Si maitre ModBus peuvent reçoit une réponse après avoir envoyé un ordre
        # Et ajoute le résultat en json
        for cle: drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].keys()
            tasmota.yield()
            if type(drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]) != "instance"   continue    end

            if (drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle].find("activation", "OFF") == "ON")
                # Ajoute une règle pour chaque esclave ModBus TasmotaSlaveModBus
                # Gestion des messages recus par ModbusReceived
                if (drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON")
                    tasmota.add_rule(string.format("ModbusReceived#DeviceAddress==%i", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]["id"]), def(value, trigger, msg) self.recupereReponseModBus(value, trigger, msg)    end, "tasmotaSlaveModBus_Received")
                end

                if (drivers["ModBus"]["typeComm"].find("UDP", "OFF") == "ON" && serveur["udp"].find("activation", "OFF") == "ON")
                    # Gestion des messages recus par ModbusReceivedUDP
                    tasmota.add_rule(string.format("ModbusReceivedUDP#DeviceAddress==%i", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]["id"]), def(value, trigger, msg) self.recupereReponseModBus(value, trigger, msg)    end, "tasmotaSlaveModBusUDP_Received")
                end

                if (drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON" && serveur["tcp"].find("activation", "OFF") == "ON")
                    # Gestion des messages recus par ModbusReceivedTCP
                    tasmota.add_rule(string.format("ModbusReceivedTCP#DeviceAddress==%i", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]["id"]), def(value, trigger, msg) self.recupereReponseModBus(value, trigger, msg)    end, "tasmotaSlaveModBusTCP_Received")
                end
            end
        end

        # Ajoute les commandes personnalisées si le module est activé
        tasmota.add_cmd('ReglageSlaveModBus', def(cmd, idx, payload, payload_json)  self.reglageSlaveModBus(cmd, idx, payload, payload_json)  end)
		if (self.nbIOActivesJSON["WS2812"]["actives"].find("nb", 0) > self.nbIOActivesJSON["WS2812"]["reels"].find("nb", 0))
			tasmota.add_cmd('HSBCOLOR', def(cmd, idx, payload, payload_json)    self.HSBColor(cmd, idx, payload, payload_json)   end)
			tasmota.add_cmd('DIMMER', def(cmd, idx, payload, payload_json)  self.Dimmer(cmd, idx, payload, payload_json)   end)				
		end   
    end

    def log(msg, levelDebug)
        import persist
    
        if (self.DEBUG == nil)
            self.DEBUG = drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].find("debug", "OFF")
        end
    
        if (self.DEBUG == "ON")
            log(msg, levelDebug)
        end
    end

    #- Exemples: 
        ReglageSlaveModBus1 logActivation OFF   => Active ou désactive les logs du module
        ReglageSlaveModBus1 id 0x02   => Change le l'adresse ModBus de l'esclave ModBus_TasmotaSlaveModBus1
    -#
    def reglageSlaveModBus(cmd, idx, payload, payload_json)
        import string
        import json
        import persist

        var fonction = false
        var parametres = []
        var reponse_cmnd
        
        # Test   
        self.log("REGLAGE_MODBUS_TASMOTA_SLAVE: -------------------- reglageSlaveModBus -------------------", LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_TASMOTA_SLAVE: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_TASMOTA_SLAVE: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_TASMOTA_SLAVE: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_TASMOTA_SLAVE: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

        # Détermine la fonction appelée et ses paramètres
        if string.find(payload, " ") > - 1
            parametres = string.split(payload , " ", 1)
            fonction = parametres.pop(0)
        else fonction = payload
        end

        log("REGLAGE_MODBUS_TASMOTA_SLAVE: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
        if (parametres.size() > 0)	log("REGLAGE_MODBUS_TASMOTA_SLAVE: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
        if (parametres.size() > 1)	log("REGLAGE_MODBUS_TASMOTA_SLAVE: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

        # Activation ou désactivation des logs de gestion de la garage -> ordre: logActivation
        if (string.toupper(fonction) == string.toupper("logActivation"))
            try
                # Adapte le paramètre
                parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
                self.DEBUG = parametres[0]

                # Sauvegarde le paramètre
                drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus" + str(idx)]["debug"] = parametres[0]
                persist.save()
            except .. as e, m
                # print('Erreur: ', e, " -> ", m)
            end
        # Change le l'adresse ModBus de l'esclave ModBus_TasmotaSlaveModBus<x> -> ordre: id
        elif (string.toupper(fonction) == string.toupper("id"))
            try
                # Adapte le paramètre
                var nouvelleID = int(parametres[0])

                # Vérifie que l'ID est entre 1 et 247
                if (nouvelleID < 1 || nouvelleID > 247)
                    reponse_cmnd = string.format("reglageSlaveModBus: id=%i, Erreur: L'adresse ModBus doit être comprise entre 1 et 247", idx)
                    tasmota.resp_cmnd(json.dump(reponse_cmnd))
                    return
                end

                # Sauvegarde le paramètre
                drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus" + str(idx)]["id"] = nouvelleID
                persist.save()
            except .. as e, m
                # print('Erreur: ', e, " -> ", m)
            end
        end

        # Commande réussie
        # Réponse à la commande
        reponse_cmnd = string.format("reglageSlaveModBus: id=%i, logActivated=%s", idx, self.DEBUG)
        tasmota.resp_cmnd(json.dump(reponse_cmnd))
    end

    def HSBColor(cmd, idx, payload, payload_json)
        import string
        import json
        import persist
        import re
        import modbusFonctions
    
        var fonction = false
        var parametres = []
        var reponse_cmnd
        
        # Test   
        self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: -------------------- HSBColor -------------------", LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)
    
        var couleur = -1
        var saturation = -1
        var luminosite = -1
    
        # Récupère tous les paramètres de leds WS2812B enregistrés en json
        # Parcours tous les modules pour trouver et modifier le device
        for cle: modules.keys()
            # Parcours les éléments et capteurs pour le module
            if (type(modules[cle]) != "instance")	continue 	end	
    
            if (modules[cle].find("activation", "OFF") == "ON")
                for capteurs: modules[cle]["environnement"].keys()
                    if (type(modules[cle]["environnement"][capteurs]) != "instance")	continue 	end
    
                    for numCapteur: modules[cle]["environnement"][capteurs].keys()
                        if (type(modules[cle]["environnement"][capteurs][numCapteur]) != "instance")	continue 	end
    
                        if (modules[cle]["environnement"][capteurs][numCapteur].find("activation", "OFF") == "ON")
                            # LEDS WS2812B
                            if (modules[cle]["environnement"][capteurs][numCapteur]["type"] == 1376)
                                # Récupère les paramètres de la couleur
                                couleur = modules[cle]["environnement"][capteurs][numCapteur].find("couleur", 0)
                                saturation = modules[cle]["environnement"][capteurs][numCapteur].find("saturation", 0)
                                luminosite = modules[cle]["environnement"][capteurs][numCapteur].find("value", 0)
    
                                # Modifie le paramètre déterminé par idx
                                if (idx == 1)
                                    self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: Modification de la couleur des LEDS = " + str(payload), LOG_LEVEL_DEBUG_PLUS)
                                    couleur = payload
                                    modules[cle]["environnement"][capteurs][numCapteur]["couleur"] = int(payload)
                                elif (idx == 2)
                                    self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: Modification de la saturation des LEDS = " + str(payload), LOG_LEVEL_DEBUG_PLUS)
                                    saturation = payload
                                    modules[cle]["environnement"][capteurs][numCapteur]["saturation"] = int(payload)
                                elif (idx == 2)
                                    self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: Modification de la luminosité des LEDS = " + str(payload), LOG_LEVEL_DEBUG_PLUS)
                                    luminosite = payload
                                    modules[cle]["environnement"][capteurs][numCapteur]["value"] = int(payload)
                                end
    
                                # Si c'est une device ModBus, on envoie la commande sur le port ModBus
                                if (modules[cle]["environnement"][capteurs][numCapteur].find("virtuel", "OFF") != "OFF")
                                    if (string.find(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "ModBus_TasmotaSlaveModBus") > - 1)
                                        var typeConnex = string.split(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "_")[0]
                                        var moduleConnex = string.split(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "_")[1]
                                        var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", string.split(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "_")[1])[0]

                                        if (typeConnex == "ModBus")
                                            if (modules[cle]["environnement"][capteurs][numCapteur].find("idModBus", false) != false)
                                                # Construit la trame
                                                var trameModBus = 	{
                                                                        "DeviceAddress": drivers["ModBus"]["environnement"][groupeConnex][moduleConnex]["id"],
                                                                        "FunctionCode": 0x10, 
                                                                        "StartAddress": modules[cle]["environnement"][capteurs][numCapteur]["type"] + modules[cle]["environnement"][capteurs][numCapteur]["idModBus"] - 1, 
                                                                        "type": "uint16", 
                                                                        "Count": 3, 
                                                                        "Values": [couleur, saturation, luminosite]
                                                                    }
        
                                                # Envoi de la commande ModBus
                                                # tasmota.cmd("ModBusSend " + json.dump(trameModBus))#, boolMute)
                                                modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"])
                                            end 
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    
        # Commande réussie
        # Réponse à la commande
        var power = (luminosite == 0 ? "OFF" : "ON")
        reponse_cmnd = string.format("{\"POWER1\":\"%s\",\"Dimmer\":%i,\"HSBColor\":\"%i,%i,%i\"}", (luminosite == 0 ? "OFF" : "ON"), luminosite, couleur, saturation, luminosite)
        tasmota.resp_cmnd(reponse_cmnd)
    end

    def Dimmer(cmd, idx, payload, payload_json)
        import string
        import json
        import persist
        import re
        import modbusFonctions
    
        var fonction = false
        var parametres = []
        var reponse_cmnd
        
        # Test   
        self.log("MODBUS_TASMOTA_SLAVE_DIMMER: -------------------- Dimmer -------------------", LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_DIMMER: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_DIMMER: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_DIMMER: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_TASMOTA_SLAVE_DIMMER: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)
    
        var couleur = -1
        var saturation = -1
        var luminosite = -1
    
        # Récupère tous les paramètres de leds WS2812B enregistrés en json
        # Parcours tous les modules pour trouver et modifier le device
        for cle: modules.keys()
            # Parcours les éléments et capteurs pour le module
            if (type(modules[cle]) != "instance")	continue 	end	
    
            if (modules[cle].find("activation", "OFF") == "ON")
                for capteurs: modules[cle]["environnement"].keys()
                    if (type(modules[cle]["environnement"][capteurs]) != "instance")	continue 	end
    
                    for numCapteur: modules[cle]["environnement"][capteurs].keys()
                        if (type(modules[cle]["environnement"][capteurs][numCapteur]) != "instance")	continue 	end
    
                        if (modules[cle]["environnement"][capteurs][numCapteur].find("activation", "OFF") == "ON")
                            # LEDS WS2812B
                            if (modules[cle]["environnement"][capteurs][numCapteur]["type"] == 1376 && modules[cle]["environnement"][capteurs][numCapteur]["id"] == idx)
                                # Récupère les paramètres de la couleur
                                couleur = modules[cle]["environnement"][capteurs][numCapteur].find("couleur", 0)
                                saturation = modules[cle]["environnement"][capteurs][numCapteur].find("saturation", 0)
                                luminosite = modules[cle]["environnement"][capteurs][numCapteur].find("value", 0)
    
                                # Modifie le paramètre déterminé par idx
                                self.log("MODBUS_TASMOTA_SLAVE_DIMMER: Modification de la luminosité des LEDS = " + str(payload), LOG_LEVEL_DEBUG_PLUS)
                                luminosite = int(payload)
                                modules[cle]["environnement"][capteurs][numCapteur]["value"] = int(payload)
    
                                # Si c'est une device ModBus, on envoie la commande sur le port ModBus
                                if (modules[cle]["environnement"][capteurs][numCapteur].find("virtuel", "OFF") != "OFF")
                                    if (string.find(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "ModBus_TasmotaSlaveModBus") > - 1)
                                        var typeConnex = string.split(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "_")[0]
                                        var moduleConnex = string.split(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "_")[1]
                                        var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", string.split(modules[cle]["environnement"][capteurs][numCapteur]["virtuel"], "_")[1])[0]

                                        if (typeConnex == "ModBus")
                                            if (modules[cle]["environnement"][capteurs][numCapteur].find("idModBus", false) != false)
                                                # Construit la trame
                                                var trameModBus = 	{
                                                                        "DeviceAddress": drivers["ModBus"]["environnement"][groupeConnex][moduleConnex]["id"],
                                                                        "FunctionCode": 0x10, 
                                                                        "StartAddress": modules[cle]["environnement"][capteurs][numCapteur]["type"] + modules[cle]["environnement"][capteurs][numCapteur]["idModBus"] - 1, 
                                                                        "type": "uint16", 
                                                                        "Count": 3, 
                                                                        "Values": [couleur, saturation, luminosite]
                                                                    }		
        
                                                # Envoi de la commande ModBus
                                                modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"])
                                            end 
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    
        # Commande réussie
        # Réponse à la commande
        var power = (luminosite == 0 ? "OFF" : "ON")
        tasmota.cmd("POWER1 " + power, boolMute)

        reponse_cmnd = string.format("{\"POWER1\":\"%s\",\"Dimmer\":%i,\"HSBColor\":\"%i,%i,%i\"}", (luminosite == 0 ? "OFF" : "ON"), luminosite, couleur, saturation, luminosite)
        tasmota.resp_cmnd(reponse_cmnd)
    end

    # Ajoute 'dataJson["TasmotaSlaveModBus"]' au json Teleperiod
    def json_append()
        import json

        tasmota.response_append(", \"TasmotaSlaveModBus\":" + json.dump(self.dataJson["TasmotaSlaveModBus"]))
    end

    # Pour le maitre ModBus: A chaque réception d'une trame ModBus de la part d'un esclave TasmotaSlaveModBus
    # Modifie en persist json: la valeur de la device en fonction du message ModBus recu.
    # L'enregistre dans 'dataJson["TasmotaSlaveModBus"]'
    def recupereReponseModBus(value, trigger, msg)
        import json
        import string
        import modbusFonctions
        import globalFonctions

        var nameTasmotaSlaveModBus = ""

        self.log("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: -------------------- TasmotaSlaveModBus recupereReponseModBus -------------------", LOG_LEVEL_DEBUG)
        self.log("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: value = " + str(value), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: trigger = " + str(trigger), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: msg = " + str(msg), LOG_LEVEL_DEBUG_PLUS)

        # ex: {"TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {}}}
        # Doit chercher d'abord le n° du ModBus_TasmotaSlaveModBus dans persist.json
        for cle: drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].keys()
            if (type(drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]) != "instance")   continue      end

            if (int(drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]["id"]) == value)
                nameTasmotaSlaveModBus = cle
            end
        end
        var dataJson = self.dataJson["TasmotaSlaveModBus"][nameTasmotaSlaveModBus]

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
        self.log(f"MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Type de msg Modbus = {TypeMsg:s}", LOG_LEVEL_DEBUG_PLUS)

        # Certaines fonctions ne retournent aucune données
        msg["FunctionName"] = modbusFonctions.tabFonctionsName[msg["FunctionCode"]]
        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: FunctionCode = 0x%02X ('%s')", msg["FunctionCode"], msg["FunctionName"]), LOG_LEVEL_DEBUG_PLUS)

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

                        # Si la device est activée (réels + virtuels)
                        if (env[cleEnv][cleDevice].find("activation", "OFF") == "ON" && env[cleEnv][cleDevice].find("virtuel", "OFF") != "OFF")
                            if (env[cleEnv][cleDevice]["virtuel"] == "ModBus_" + nameTasmotaSlaveModBus)
                                if (env[cleEnv][cleDevice]["type"] + env[cleEnv][cleDevice]["idModBus"] - 1 == msg["StartAddress"])
                                    # Ajoute la valeur dataJson["TasmotaSlaveModBus"] en fonction du numéro d'esclave
                                    # ex: {"TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {"relais": {}}}}
                                    var valeur = 0.00
                                    
                                    # Corrige la valeur affichée en json Teleperiod
                                    if (cleEnv == "analogiques")
                                        if (!dataJson.find("ANALOG", false))
                                            try dataJson.insert("ANALOG", {})  
                                            except .. as error, message 
                                                self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                            end
                                        end

                                        valeur = int(msg["Values"][0])
                                        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de la nouvelle valeur de l'entrée analogique n°%i: %i", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)

                                        if (env[cleEnv][cleDevice]["value"] != valeur)
                                            env[cleEnv][cleDevice]["value"] = valeur

                                            if (!dataJson["ANALOG"].insert("A" + str(env[cleEnv][cleDevice]["id"]), valeur))
                                                dataJson["ANALOG"]["A" + str(env[cleEnv][cleDevice]["id"])] = valeur
                                            end 
                                        end
                                    elif (cleEnv == "compteurs")
                                        if (!dataJson.find("COUNTER", false))
                                            try dataJson.insert("COUNTER", {})  
                                            except .. as error, message 
                                                self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                            end
                                        end

                                        valeur = int(msg["Values"][0])
                                        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de la nouvelle valeur du compteur n°%i: %i", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)

                                        if (env[cleEnv][cleDevice]["value"] != valeur)
                                            env[cleEnv][cleDevice]["value"] = valeur

                                            if (!dataJson["COUNTER"].insert("C" + str(env[cleEnv][cleDevice]["id"]), valeur))
                                                dataJson["COUNTER"]["C" + str(env[cleEnv][cleDevice]["id"])] = valeur
                                            end 
                                        end

                                    elif (cleEnv == "thermometres")
                                        if (!dataJson.find("Temperatures", false))
                                            try dataJson.insert("Temperatures", {})  
                                            except .. as error, message 
                                                self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                            end
                                        end

                                        valeur = real(msg["Values"][0])
                                        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de la nouvelle valeur du thermomètre n°%i: %.2f°C", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)

                                        # DHT22 (AM2302)
                                        if (env[cleEnv][cleDevice]["type"] == 1216)
                                            if (env[cleEnv][cleDevice]["value"] != valeur)  # Température 
                                                env[cleEnv][cleDevice]["value"] = valeur

                                                if (!dataJson["Temperatures"].find("AM2301", false))
                                                    try dataJson["Temperatures"].insert("AM2301", {})  
                                                    except .. as error, message 
                                                        self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                                    end
                                                end
                                                if (!dataJson["Temperatures"]["AM2301"].insert("Temperature", valeur))
                                                    dataJson["Temperatures"]["AM2301"]["Temperature"] = valeur
                                                end 
                                            end

                                            valeur = real(msg["Values"][1])
                                            self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de la nouvelle valeur de l'hygromètre n°%i: %.1fRH", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)
                                            
                                            if (env[cleEnv][cleDevice]["Humidity"] != valeur)   #Humidity
                                                env[cleEnv][cleDevice]["Humidity"] = valeur

                                                if (!dataJson["Temperatures"].find("AM2301", false))
                                                    try dataJson["Temperatures"].insert("AM2301", {})  
                                                    except .. as error, message 
                                                        self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                                    end
                                                end

                                                if (!dataJson["Temperatures"]["AM2301"].insert("Humidity", valeur))
                                                    dataJson["Temperatures"]["AM2301"]["Humidity"] = valeur
                                                end 
                                            end
                                        # DS18B20
                                        elif (env[cleEnv][cleDevice]["type"] == 1312)  
                                            if (env[cleEnv][cleDevice]["value"] != valeur)
                                                env[cleEnv][cleDevice]["value"] = valeur

                                                if (!dataJson["Temperatures"].find("DS18B20-" + str(env[cleEnv][cleDevice]["id"]), false))
                                                    try dataJson["Temperatures"].insert("DS18B20-" + str(env[cleEnv][cleDevice]["id"]), {})  
                                                    except .. as error, message 
                                                        self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                                    end 
                                                end

                                                if (!dataJson["Temperatures"]["DS18B20-" + str(env[cleEnv][cleDevice]["id"])].insert("Id", env[cleEnv][cleDevice]["serialNumber"]))
                                                    dataJson["Temperatures"]["DS18B20-" + str(env[cleEnv][cleDevice]["id"])]["Id"] = env[cleEnv][cleDevice]["serialNumber"]
                                                end 
                                                if (!dataJson["Temperatures"]["DS18B20-" + str(env[cleEnv][cleDevice]["id"])].insert("Temperature", valeur))
                                                    dataJson["Temperatures"]["DS18B20-" + str(env[cleEnv][cleDevice]["id"])]["Temperature"] = valeur
                                                end 
                                            end
                                        end
                                    elif (cleEnv == "interrupteurs")
                                        if (!dataJson.find("Switchs", false))
                                            try dataJson.insert("Switchs", {})  
                                            except .. as error, message 
                                                self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                            end
                                        end

                                        if (env[cleEnv][cleDevice].find("SwitchMode", 1) == 1)
                                            valeur = (msg["Values"][0] == 0xFF ? "ON" : "OFF")
                                        elif (env[cleEnv][cleDevice].find("SwitchMode", 1) == 2)
                                            valeur = (msg["Values"][0] == 0xFF ? "OFF" : "ON")
                                        end

                                        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de l'état de l'interrupteur n°%i: %s", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)

                                        if (env[cleEnv][cleDevice]["etat"] != valeur)
                                            env[cleEnv][cleDevice]["etat"] = valeur

                                            if (!dataJson["Switchs"].insert("S" + str(env[cleEnv][cleDevice]["id"]), valeur))
                                                dataJson["Switchs"]["S" + str(env[cleEnv][cleDevice]["id"])] = valeur
                                            end 
                                        end
                                    elif (cleEnv == "boutons")
                                        if (!dataJson.find("Buttons", false))
                                            try dataJson.insert("Buttons", {})  
                                            except .. as error, message 
                                                self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                            end
                                        end

                                        if (env[cleEnv][cleDevice].find("SwitchMode", 1) == 1)
                                            valeur = (msg["Values"][0] == 0xFF ? "ON" : "OFF")
                                        elif (env[cleEnv][cleDevice].find("SwitchMode", 1) == 2)
                                            valeur = (msg["Values"][0] == 0xFF ? "OFF" : "ON")
                                        end

                                        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de l'état du bouton n°%i: %s", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)

                                        if (env[cleEnv][cleDevice]["etat"] != valeur)
                                            env[cleEnv][cleDevice]["etat"] = valeur

                                            if (!dataJson["Buttons"].insert("B" + str(env[cleEnv][cleDevice]["id"]), valeur))
                                                dataJson["Buttons"]["B" + str(env[cleEnv][cleDevice]["id"])] = valeur
                                            end 
                                        end
                                    elif (cleEnv == "relais")
                                        if (!dataJson.find("POWER" + str(env[cleEnv][cleDevice]["id"]), false))
                                            try dataJson.insert("POWER" + str(env[cleEnv][cleDevice]["id"]), "OFF")  
                                            except .. as error, message 
                                                self.log(string.format("TRAITEMENT_MSG_TASMOTA_SLAVE_MODBUS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                                            end
                                        end

                                        valeur = (msg["Values"][0] == 0xFF ? "ON" : "OFF")
                                        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de l'état du relai n°%i: %s", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)

                                        if (env[cleEnv][cleDevice]["etat"] != valeur)
                                            env[cleEnv][cleDevice]["etat"] = valeur
                                            dataJson["POWER" + str(env[cleEnv][cleDevice]["id"])] = valeur
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end

            # Modifie en json persist
            modules[cleModule]["environnement"] = env
        end

        # Ajoute la donnée reçue en json
        self.log("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: dataJson=" + json.dump(self.dataJson), LOG_LEVEL_DEBUG_PLUS)

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
        self.log("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: -------------------- SlaveModBus changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
        self.log("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
        self.log("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
        self.log("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
        
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
                # Gère les commandes envoyées aux devices ModBus du TasmotaSlaveModBus au demarrage

                # Récupère le délai de la Teleperiod
                var teleperiod = tasmota.cmd("TelePeriod", boolMute)["TelePeriod"]

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
                                        if ((string.find(devices[cleDev]["virtuel"], "ModBus_TasmotaSlaveModBus") > - 1) && (devices[cleDev].find("idModBus", false) != false))
                                            var valueModBus
                                            var couleur = -1
                                            var saturation = -1
                                            var luminosite = -1
                                            
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

                                                # LEDS WS2812B
                                                if (devices[cleDev]["type"] == 1376)
                                                    # Récupère les paramètres de la couleur
                                                    couleur = devices[cleDev].find("couleur", 0)
                                                    saturation = devices[cleDev].find("saturation", 0)
                                                    luminosite = devices[cleDev].find("value", 0)
                                                end
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
                                                        # LEDS WS2812B
                                                        if (devices[cleDev]["type"] == 1376)
                                                            trameModBus["FunctionCode"] = 0x10
                                                            trameModBus["StartAddress"] = devices[cleDev]["type"] + devices[cleDev]["idModBus"] - 1 
                                                            trameModBus["type"] = "uint16"
                                                            trameModBus["Count"] = 3
                                                            trameModBus["Values"] = [couleur, saturation, luminosite]

                                                            self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Commande sur le réseau ModBus pour les LEDS WS2812 n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO)
                                                        # Relais
                                                        else  
                                                            trameModBus["FunctionCode"] = 0x06
                                                            trameModBus["StartAddress"] = devices[cleDev]["type"] + devices[cleDev]["idModBus"] - 1  
                                                            trameModBus["type"] = "uint8"
                                                            trameModBus["Count"] = 1
                                                            trameModBus["Values"] = [valueModBus, 0]

                                                            tasmota.cmd(string.format("Power%i %s", devices[cleDev]["id"], devices[cleDev]["etat"]))
                                                            self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Commande sur le réseau ModBus pour le relai n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO)
                                                        end
                                                        modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"]) 
                                                    # Demande au demarrage l'état des interrupteurs virtuels ModBus
                                                    # ex: modbussend {"Count":1,"StartAddress":0x03,"values":0,"type":"uint8","FunctionCode":2,"StartAddress":160}
                                                    elif (cleDevices == "interrupteurs" || cleDevices == "capteurs" || cleDevices == "boutons")
                                                        trameModBus["FunctionCode"] = 0x02
                                                        trameModBus["StartAddress"] = devices[cleDev]["type"] + devices[cleDev]["idModBus"] - 1
                                                        trameModBus["type"] = "uint8"
                                                        trameModBus["Count"] = 1
                                                        trameModBus["Values"] = 0

                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Lance sur le réseau ModBus, la demande d'état " + (cleDevices == "interrupteurs" ? "de l'interrupteur" : "du capteur")  + "n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO) 

                                                        # tasmota.add_cron("*/60 * * * * *",  /-> modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"]), "majInter_TasmotaSlaveModBus")
                                                        # modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"])
                                                    # Demande régulièrement la valeur des entrées analogiques virtuels ModBus / Teleperiod
                                                    # ex: ModBusSend {"FunctionCode":4,"Values":0,"Count":1,"DeviceAddress":0x02,"type":"uint32","StartAddress":4704}
                                                    elif (cleDevices == "analogiques")
                                                        trameModBus["FunctionCode"] = 0x04
                                                        trameModBus["StartAddress"] = devices[cleDev]["type"] + devices[cleDev]["idModBus"] - 1
                                                        trameModBus["type"] = "uint32"
                                                        trameModBus["Count"] = 1
                                                        trameModBus["Values"] = 0

                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Lance sur le réseau ModBus, la demande de valeur de l'entrée analogique n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO) 

                                                        # tasmota.add_cron(string.format("*/%i * * * * *", teleperiod), /-> modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"]), "majAnalogiques_TasmotaSlaveModBus")
                                                        # modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"])
                                                    # Demande au demarrage la valeur des compteurs virtuels ModBus
                                                    # ex: ModBusSend {"FunctionCode":4,"Values":0,"Count":1,"DeviceAddress":0x02,"type":"uint32","StartAddress":352}
                                                    elif (cleDevices == "compteurs")
                                                        trameModBus["FunctionCode"] = 0x04
                                                        trameModBus["StartAddress"] = devices[cleDev]["type"] + devices[cleDev]["idModBus"] - 1
                                                        trameModBus["type"] = "uint32"
                                                        trameModBus["Count"] = 1
                                                        trameModBus["Values"] = 0

                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Lance sur le réseau ModBus, la demande de valeur du compteur n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO) 

                                                        # tasmota.add_cron(string.format("*/%i * * * * *", teleperiod),  /-> modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"]), "majCompteurs_TasmotaSlaveModBus")
                                                        # modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"])
                                                    # Demande régulièrement la valeur des thermomètres & DHT22 virtuels ModBus / TelePeriod
                                                    # ex DS18B20: ModBusSend {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "type":"float", "Count":1, "Values":-1.5}
                                                    elif (cleDevices == "thermometres")
                                                        # DHT22 (AM2302)
                                                        if (devices[cleDev]["type"] == 1216)
                                                            trameModBus["FunctionCode"] = 0x04
                                                            trameModBus["StartAddress"] = devices[cleDev]["type"] + devices[cleDev]["idModBus"] - 1
                                                            trameModBus["type"] = "float"
                                                            trameModBus["Count"] = 2        # Attendra 2 valeurs: T° + Humidité
                                                            trameModBus["Values"] = 0 
                                                        # DS18B20
                                                        elif (devices[cleDev]["type"] == 1312)  
                                                            trameModBus["FunctionCode"] = 0x04
                                                            trameModBus["StartAddress"] = devices[cleDev]["type"] + devices[cleDev]["idModBus"] - 1
                                                            trameModBus["type"] = "float"
                                                            trameModBus["Count"] = 1
                                                            trameModBus["Values"] = 0  
                                                        end
                                                            
                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Lance sur le réseau ModBus, la demande de valeur du thermomètre n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO) 

                                                        # tasmota.add_cron(string.format("*/%i * * * * *", teleperiod),  /-> modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"]), "majThermo_TasmotaSlaveModBus")
                                                        # modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"])
                                                    end
                                                end
                                            end
                                        end
                                    end 
                                end
                            end
                        end
                    except .. as error, message
                        modbusFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: %s --> %s", error, message), LOG_LEVEL_ERREUR)
                    end
                end
            end
        end
    end
end

# Active le Driver de controle global des modules virtuelles ModBus
if (drivers["ModBus"].find("activation", "OFF") == "ON")
    if (drivers["ModBus"]["environnement"].find("TasmotaSlaveModBus", false) != false)
        for cle: drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].keys()
            import string

            if type(drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]) != "instance"   continue    end

            try
                if (drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle].find("activation", "OFF") == "ON")
                    modBus_TasmotaSlaveModBus = MODBUS_TASMOTA_SLAVE()
                    tasmota.add_driver(modBus_TasmotaSlaveModBus)

                    log("MODBUS_TASMOTA_SLAVE: Driver activé !", LOG_LEVEL_DEBUG)

                    break
                end
            except .. as error, message
                log(string.format("MODBUS_TASMOTA_SLAVE_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
            end
        end
    end
end