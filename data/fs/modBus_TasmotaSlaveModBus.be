#- NOTES Sur l'ajout de fonctionnalité pour les maitres des modules ModBus TasmotaSlave
    - ModBus.help peut vous aider à comprendre la gestion des communications
    - Utilise le Driver ModBus natif de Tasmota
    - Chargé de créer les devices virtuels ModBus
    - Donne de nouvelles compétences de controleau maitre sir les modules Tasmota utilisés comme esclaves ModBus
    - Gère les commandes envoyées sur les ports ModBus en fonction des types (relais, interrupteurs, capteurs, boutons, thermometres ...)
    - Crée des règles ou commandes similaires à celles de Tasmota pour les devices virtuelles
-#

# Rendu solidifiable (2026-09-27), sur le modele de controleGeneral : la classe est portee
# par le module import-able 'modBus_TasmotaSlaveModBus'. autoexec le charge par 'import' (version en FLASH
# via load_native), plus par loadBerryFile (qui recompilait la classe en RAM).
# 'import' appelle AUTOMATIQUEMENT modBus_TasmotaSlaveModBus_init(m), en pied de fichier.
#@ solidify:modBus_TasmotaSlaveModBus
var modBus_TasmotaSlaveModBus = module("modBus_TasmotaSlaveModBus")

class MODBUS_TASMOTA_SLAVE : Driver
    # Variables
    var nbIOActivesJSON
    var dataJson
    var derniersContacts                # chien de garde : id esclave -> heure du dernier contact
    var esclavesMuets                   # chien de garde : id esclave -> true tant qu'il est muet

    def init()
        import json
        import string
        import gestionFileFolder

        self.nbIOActivesJSON = nil
        self.derniersContacts = {}
        self.esclavesMuets = {}
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
			tasmota.add_cmd('SCHEME', def(cmd, idx, payload, payload_json)  self.Scheme(cmd, idx, payload, payload_json)   end)
		end   
    end

    def log(msg, levelDebug)
        logFonctions.log(msg, levelDebug, "slaveModbus")
    end

    # Aide de la commande ReglageSlaveModBus, appelee SEULEMENT par diversFonctions.traiteAide :
    # sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
    def aideReglageSlaveModBus(sujet)
        import string
        if (sujet == nil)
            return [
                ["id", "id <1..247>", "change l'adresse ModBus de l'esclave ReglageSlaveModBus<n> (sauve)"]
            ]
        end
        sujet = string.toupper(sujet)
        if (sujet == "ID")
            return ["Parametre : <id> entre 1 et 247 (ex. 2 ou 0x02) ; hors bornes = erreur.",
                    "Le suffixe numerique de la commande (n) designe l'esclave TasmotaSlaveModBus<n>.",
                    "Effet : sauve le nouvel id dans le persist ; les regles ModbusReceived deja",
                    "posees gardent l'ancien id : redemarrer pour une prise en compte complete.",
                    "Exemple : ReglageSlaveModBus1 id 0x02"]
        end
        return nil
    end

    #- Exemples:
        ReglageSlaveModBus1 id 0x02   => Change le l'adresse ModBus de l'esclave ModBus_TasmotaSlaveModBus1
    -#
    def reglageSlaveModBus(cmd, idx, payload, payload_json)
        import string
        import json
        import persist
        import diversFonctions

        # Aide en console : ReglageSlaveModBus help | help <sous-commande> | sous-commande inconnue
        if diversFonctions.traiteAide("ReglageSlaveModBus", payload, / s -> self.aideReglageSlaveModBus(s), true)    return    end

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

        logFonctions.log("REGLAGE_MODBUS_TASMOTA_SLAVE: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS, "slaveModbus")
        if (parametres.size() > 0)	logFonctions.log("REGLAGE_MODBUS_TASMOTA_SLAVE: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS, "slaveModbus")	end
        if (parametres.size() > 1)	logFonctions.log("REGLAGE_MODBUS_TASMOTA_SLAVE: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS, "slaveModbus")	end

        # Change le l'adresse ModBus de l'esclave ModBus_TasmotaSlaveModBus<x> -> ordre: id
        if (string.toupper(fonction) == string.toupper("id"))
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
                persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
            except .. as e, m
                # print('Erreur: ', e, " -> ", m)
            end
        end

        # Commande réussie
        # Réponse à la commande
        reponse_cmnd = string.format("reglageSlaveModBus: id=%i", idx)
        tasmota.resp_cmnd(json.dump(reponse_cmnd))
    end

    # Aide de la commande HSBCOLOR, appelee SEULEMENT par diversFonctions.traiteAide.
    # Commande a VALEUR : une seule entree de nom "", pas de detail.
    def aideHSBColor(sujet)
        if (sujet == nil)
            return [
                ["", "<teinte>   (HSBCOLOR1 teinte, HSBCOLOR2 saturation)", "regle la teinte (idx 1) ou la saturation (idx 2) des LEDS WS2812 ; HSBCOLOR3 sans effet"]
            ]
        end
        return nil
    end

    def HSBColor(cmd, idx, payload, payload_json)
        import string
        import json
        import persist
        import re
        import modbusFonctions
        import diversFonctions

        # Aide en console : HSBCOLOR help (commande a valeur : aucune sous-commande a verifier)
        if diversFonctions.traiteAide("HSBCOLOR", payload, / s -> self.aideHSBColor(s), false)    return    end
    
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
                                    couleur = int(payload)
                                    modules[cle]["environnement"][capteurs][numCapteur]["couleur"] = int(payload)
                                elif (idx == 2)
                                    self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: Modification de la saturation des LEDS = " + str(payload), LOG_LEVEL_DEBUG_PLUS)
                                    saturation = int(payload)
                                    modules[cle]["environnement"][capteurs][numCapteur]["saturation"] = int(payload)
                                elif (idx == 3)     # etait 'idx == 2' (doublon) : HSBColor3 ignore jusqu'au 2026-10-11
                                    self.log("MODBUS_TASMOTA_SLAVE_HSB_COLOR: Modification de la luminosité des LEDS = " + str(payload), LOG_LEVEL_DEBUG_PLUS)
                                    luminosite = int(payload)
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
                                                self.relitRuban(modules[cle]["environnement"][capteurs][numCapteur], capteurs, trameModBus["DeviceAddress"])
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

    # Aide de la commande DIMMER, appelee SEULEMENT par diversFonctions.traiteAide.
    # Commande a VALEUR : une seule entree de nom "", pas de detail.
    def aideDimmer(sujet)
        if (sujet == nil)
            return [
                ["", "<luminosite>   (DIMMER<id> luminosite)", "regle la luminosite de la LED WS2812 d'id <id> (0 = POWER1 OFF) et l'envoie a l'esclave"]
            ]
        end
        return nil
    end

    def Dimmer(cmd, idx, payload, payload_json)
        import string
        import json
        import persist
        import re
        import modbusFonctions
        import diversFonctions

        # Aide en console : DIMMER help (commande a valeur : aucune sous-commande a verifier)
        if diversFonctions.traiteAide("DIMMER", payload, / s -> self.aideDimmer(s), false)    return    end
    
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
                                                self.relitRuban(modules[cle]["environnement"][capteurs][numCapteur], capteurs, trameModBus["DeviceAddress"])
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

    # Aide de la commande SCHEME, appelee SEULEMENT par diversFonctions.traiteAide.
    # Commande a VALEUR : une seule entree de nom "", pas de detail.
    def aideScheme(sujet)
        if (sujet == nil)
            return [
                ["", "<animation>   (0 a 14)", "regle l'animation des rubans WS2812 des esclaves ModBus (0 = une seule couleur) ; sans parametre : la valeur memorisee"]
            ]
        end
        return nil
    end

    # Animation des rubans WS2812 virtuels (2026-10-11) : appelee par le menu "Animations LEDs" de
    # la page du maitre (/json?commande=scheme N). Memorise l'animation dans le relai ("scheme") et
    # l'envoie a l'esclave par une ecriture 0x06 au registre du ruban : [0x03, animation]
    # (0x02/0x01 = ON/OFF ; modbusFonctions.executeCmdModbus l'execute par 'Scheme').
    def Scheme(cmd, idx, payload, payload_json)
        import string
        import modbusFonctions
        import diversFonctions

        if diversFonctions.traiteAide("SCHEME", payload, / s -> self.aideScheme(s), false)    return    end

        var animation = nil
        if (payload != nil && payload != "")
            animation = int(payload)
            if (animation < 0 || animation > 14)
                tasmota.resp_cmnd(string.format("{\"Scheme\":\"erreur : %s hors de 0..14\"}", str(payload)))
                return
            end
        end

        var memorisee = 0
        for cle: modules.keys()
            if (type(modules[cle]) != "instance" || modules[cle].find("activation", "OFF") != "ON")    continue    end
            var relais = modules[cle].find("environnement", {}).find("relais")
            if (type(relais) != "instance")    continue    end

            for cleRLY: relais.keys()
                tasmota.yield()
                var relai = relais[cleRLY]
                if (type(relai) != "instance" || relai.find("activation", "OFF") != "ON" || relai.find("type") != 1376)    continue    end
                var virtuel = str(relai.find("virtuel", "OFF"))
                if (string.find(virtuel, "ModBus_TasmotaSlaveModBus") != 0 || relai.find("idModBus") == nil)    continue    end
                var esclave = drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].find(string.split(virtuel, "_")[1])
                if (type(esclave) != "instance")    continue    end

                if (animation == nil)    memorisee = relai.find("scheme", 0)    continue    end

                relai["scheme"] = animation
                var trameModBus = {
                                    "DeviceAddress": esclave["id"],
                                    "FunctionCode": 6,
                                    "StartAddress": relai["type"] + relai["idModBus"] - 1,
                                    "type": "uint8",
                                    "Count": 1,
                                    "Values": [0x03, animation]
                                  }
                self.log(string.format("MODBUS_TASMOTA_SLAVE_SCHEME: Animation %i envoyee a l'esclave %i ('%s') !", animation, esclave["id"], str(relai.find("nom", cleRLY))), LOG_LEVEL_DEBUG)
                modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["DeviceAddress"])
            end
        end

        tasmota.resp_cmnd(string.format("{\"Scheme\":%i}", animation == nil ? memorisee : animation))
    end

    # Relecture d'un ruban WS2812 juste apres une ecriture 0x10 (2026-10-11). La reponse standard
    # a une 0x10 ne porte aucune valeur, et le pont ModBus natif refuse la fonction 0x17
    # (ecriture + lecture) : la lecture 0x03 part donc derriere l'ecriture, dans la meme file,
    # et recupereReponseModBus recopie l'etat REELLEMENT applique par l'esclave.
    def relitRuban(device, famille, idEsclave)
        import modbusFonctions

        var trame = self.demandeLecture(device, famille, idEsclave)
        if (trame != nil)    modbusFonctions.envoiMsgModbus(trame, "Commande", trame["StartAddress"])    end
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

        self.log("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: -------------------- TasmotaSlaveModBus recupereReponseModBus -------------------", LOG_LEVEL_DEBUG_PLUS)
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
        # .find : un id inconnu (esclave renomme a chaud...) ne doit pas lever avant l'acquittement
        var dataJson = self.dataJson["TasmotaSlaveModBus"].find(nameTasmotaSlaveModBus, {})

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

        # Complete la reponse de lecture avec StartAddress/Count/type de la requete en
        # vol (la trame RTU ne les porte pas) -> le maitre sait a quel registre repondre.
        # REJET STRICT (2026-07-24) : une trame hors-sequence ne doit ni etre completee
        # depuis la requete en vol, ni l'acquitter - sinon elle lui volerait sa reponse,
        # et la vraie requete serait perdue au lieu d'etre renvoyee par le timeout.
        # Une TELEMETRIE spontanee, elle, porte deja son propre StartAddress (lu dans la
        # trame par decrypteMSG) : on la traite normalement, mais elle n'acquitte rien.
        var estReponseEnVol = modbusFonctions.apparieReponse(msg)
        if (!estReponseEnVol && !msg.find("Automatique", false))    return    end

        # Chien de garde : une reponse appariee ou un push = l'esclave est vivant
        self.noteContact(int(value))

        # Certaines fonctions ne retournent aucune données
        msg["FunctionName"] = modbusFonctions.tabFonctionsName[msg["FunctionCode"]]
        self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: FunctionCode = 0x%02X ('%s')", msg["FunctionCode"], msg["FunctionName"]), LOG_LEVEL_DEBUG_PLUS)

        # Une ECRITURE 0x10 non sollicitee (Automatique) = push d'etat de l'esclave (option B,
        # 2026-09-29) : ses 'Values' sont des registres bruts, convertis plus bas selon le type
        # du capteur vise. Toute autre 0x10 = reponse a une commande du maitre (LEDs WS2812) :
        # on l'acquitte et on sort.
        var push = (msg["FunctionName"] == "ECRITURE_REGISTRES_HOLDER" && msg.find("Automatique", false))
        if (msg["FunctionName"] == "ECRITURE_REGISTRES_HOLDER" && !push)
            # Acquitte le message en vol (reponse recue) -> pompe le suivant
            if (estReponseEnVol)    modbusFonctions.termineEnVol(true)    end

            return
        end

        # Traitement protege (2026-09-29, audit G5) : une donnee absente d'un appareil (cle
        # manquante, idModBus nil...) levait une exception AVANT l'acquittement ci-dessous ->
        # requete jamais acquittee, 3 renvois x timeout, et regles suivantes coupees.
        try
            # Parcours les devices virtuels ModBus
            for cleModule: modules.keys()
                tasmota.yield()

                if (type(modules[cleModule]) != "instance")   continue      end

                var env = modules[cleModule].find("environnement")
                if (env)
                    for cleEnv: env.keys()
                        if type(env[cleEnv]) != "instance"   continue    end

                        for cleDevice: env[cleEnv].keys()
                            if type(env[cleEnv][cleDevice]) != "instance"   continue    end
                            tasmota.yield()

                            # Si la device est activée (réels + virtuels)
                            if (env[cleEnv][cleDevice].find("activation", "OFF") == "ON" && env[cleEnv][cleDevice].find("virtuel", "OFF") != "OFF")
                                if (env[cleEnv][cleDevice]["virtuel"] == "ModBus_" + nameTasmotaSlaveModBus)
                                    if (env[cleEnv][cleDevice].find("idModBus") != nil && env[cleEnv][cleDevice].find("type") != nil &&
                                        env[cleEnv][cleDevice]["type"] + env[cleEnv][cleDevice]["idModBus"] - 1 == msg["StartAddress"])
                                        # Push 0x10 : registres bruts -> valeurs, selon le type du capteur
                                        # (2 registres par float/uint32, 1 par etat), une seule fois.
                                        if (push)
                                            var t = env[cleEnv][cleDevice]["type"]
                                            msg["Values"] = modbusFonctions.motsVersValeurs(msg["Values"],
                                                                (t == 1312 || t == 1216) ? "float" : ((t == 352 || t == 4704) ? "uint32" : "uint16"))
                                            push = false
                                        end

                                        # Sentinelle 'pas de mesure' de l'esclave (capteur absent ou defaillant,
                                        # modbusFonctions.estSansMesure, 2026-10-10) : etat 'defaillant',
                                        # valeur precedente conservee mais plus presentee comme fraiche.
                                        if (cleEnv == "thermometres" || cleEnv == "analogiques" || cleEnv == "compteurs")
                                            # Liste vide = reponse anormale, pas une sentinelle : elle suit le
                                            # chemin d'erreur (exception journalisee) plus bas.
                                            var vals = msg.find("Values", [])
                                            if (size(vals) > 0 && modbusFonctions.estSansMesure(vals[0], cleEnv == "thermometres" ? "float" : "uint32"))
                                                self.noteDefaillant(env[cleEnv][cleDevice], nameTasmotaSlaveModBus)
                                                continue
                                            end
                                        end

                                        # Valeur fraiche : leve l'etat 'inconnu' pose par le chien de garde.
                                        # (Un relai, lui, ne se constate que par une lecture 0x01, plus bas.)
                                        if (cleEnv != "relais")
                                            if (env[cleEnv][cleDevice].find("etatConstate") == "defaillant")
                                                logFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_CAPTEUR: '%s' (%s) : mesure de nouveau valide",
                                                                  str(env[cleEnv][cleDevice].find("nom", cleDevice)), nameTasmotaSlaveModBus), LOG_LEVEL_INFO, "slaveModbus")
                                            end
                                            env[cleEnv][cleDevice]["etatConstate"] = "valide"
                                            env[cleEnv][cleDevice]["constateA"] = tasmota.rtc()["local"]
                                        end

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

                                                    if (!dataJson["Temperatures"]["DS18B20-" + str(env[cleEnv][cleDevice]["id"])].insert("Id", env[cleEnv][cleDevice].find("serialNumber", "")))
                                                        dataJson["Temperatures"]["DS18B20-" + str(env[cleEnv][cleDevice]["id"])]["Id"] = env[cleEnv][cleDevice].find("serialNumber", "")
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

                                            # Etat lu sur le BIT 0 (2026-09-29) : la reponse serie a une lecture
                                            # 0x02 porte le bit empaquete (0x01), le push 0x10 le mot 0x00FF ;
                                            # l'ancienne comparaison a 0xFF lisait OFF la reponse standard.
                                            var actif = (int(msg["Values"][0]) & 0x01) == 0x01
                                            if (env[cleEnv][cleDevice].find("SwitchMode", 1) == 1)
                                                valeur = (actif ? "ON" : "OFF")
                                            elif (env[cleEnv][cleDevice].find("SwitchMode", 1) == 2)
                                                valeur = (actif ? "OFF" : "ON")
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

                                            # Etat lu sur le BIT 0 (2026-09-29) : la reponse serie a une lecture
                                            # 0x02 porte le bit empaquete (0x01), le push 0x10 le mot 0x00FF ;
                                            # l'ancienne comparaison a 0xFF lisait OFF la reponse standard.
                                            var actif = (int(msg["Values"][0]) & 0x01) == 0x01
                                            if (env[cleEnv][cleDevice].find("SwitchMode", 1) == 1)
                                                valeur = (actif ? "ON" : "OFF")
                                            elif (env[cleEnv][cleDevice].find("SwitchMode", 1) == 2)
                                                valeur = (actif ? "OFF" : "ON")
                                            end

                                            self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Réception de l'état du bouton n°%i: %s", env[cleEnv][cleDevice]["id"], valeur), LOG_LEVEL_DEBUG)

                                            if (env[cleEnv][cleDevice]["etat"] != valeur)
                                                env[cleEnv][cleDevice]["etat"] = valeur

                                                if (!dataJson["Buttons"].insert("B" + str(env[cleEnv][cleDevice]["id"]), valeur))
                                                    dataJson["Buttons"]["B" + str(env[cleEnv][cleDevice]["id"])] = valeur
                                                end 
                                            end
                                        elif (cleEnv == "relais")
                                            # Commande / constate (2026-09-29), sur le modele de la carte 16
                                            # relais : seule une LECTURE 0x01 dit l'etat reel du relai. Il est
                                            # range dans 'etatConstate', compare a 'etat' (l'etat COMMANDE),
                                            # et un ecart est journalise, jamais corrige. L'echo d'une commande
                                            # 0x06 ne fait qu'accuser reception : il reecrivait 'etat' a OFF
                                            # (il porte 0x01/0x02, jamais 0xFF).
                                            if (msg["FunctionName"] == "LECTURE_COILS")
                                                var device = env[cleEnv][cleDevice]
                                                # Relais_i (256) : logique inversee, ON commande = relai physique au repos
                                                var bit = (int(msg["Values"][0]) & 0x01) == 0x01
                                                valeur = ((bit != (device["type"] == 256)) ? "ON" : "OFF")
                                                self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Etat constate du relai n°%i: %s", device["id"], valeur), LOG_LEVEL_DEBUG)

                                                device["etatConstate"] = valeur
                                                device["constateA"] = tasmota.rtc()["local"]
                                                dataJson["POWER" + str(device["id"])] = valeur
                                                if (device.find("etat", "OFF") != valeur)
                                                    logFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_ECART: relai n°%i (%s) : commande=%s, constate=%s",
                                                                      device["id"], nameTasmotaSlaveModBus, device.find("etat", "OFF"), valeur), LOG_LEVEL_ERREUR, "slaveModbus")
                                                end
                                            # Ruban WS2812 (1376, 2026-10-11) : lecture 0x03 = [teinte, saturation, luminosite, animation],
                                            # echelle HSBColor (modbusFonctions.etatRuban). L'esclave est maitre de son ruban
                                            # (la cuve le colore selon le niveau) : le maitre RECOPIE l'etat lu, y compris
                                            # 'etat', sans ecart a journaliser.
                                            # Meme traitement pour le PUSH 0x10 du ruban (modbusFonctions.surveilleRubans) :
                                            # une 0x10 qui arrive ici est forcement un push, les autres sont sorties plus haut.
                                            elif ((msg["FunctionName"] == "LECTURE_REGISTRES_HOLDER" || msg["FunctionName"] == "ECRITURE_REGISTRES_HOLDER") &&
                                                  env[cleEnv][cleDevice]["type"] == 1376)
                                                var device = env[cleEnv][cleDevice]
                                                var vals = msg.find("Values", [])
                                                if (size(vals) < 3)    raise "value_error", "reponse 0x03 du ruban incomplete : " + str(vals)    end

                                                valeur = (int(vals[2]) > 0 ? "ON" : "OFF")
                                                # Animation (4e registre, 2026-10-11) : absente d'une reponse d'esclave pas encore a jour -> inchangee
                                                var animation = (size(vals) >= 4 ? int(vals[3]) : device.find("scheme", 0))
                                                if (device.find("couleur") != int(vals[0]) || device.find("saturation") != int(vals[1]) ||
                                                    device.find("value") != int(vals[2]) || device.find("etat") != valeur || device.find("scheme") != animation)
                                                    self.log(string.format("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: Ruban WS2812 n°%i (%s) : teinte %i, saturation %i, luminosite %i (%s), animation %i",
                                                                           device["id"], nameTasmotaSlaveModBus, int(vals[0]), int(vals[1]), int(vals[2]), valeur, animation), LOG_LEVEL_DEBUG)
                                                end
                                                device["couleur"] = int(vals[0])
                                                device["saturation"] = int(vals[1])
                                                device["value"] = int(vals[2])
                                                device["scheme"] = animation
                                                device["etat"] = valeur
                                                device["etatConstate"] = valeur
                                                device["constateA"] = tasmota.rtc()["local"]
                                                dataJson["POWER" + str(device["id"])] = valeur

                                                # Bouton du maitre (POWERn = relai virtuel du ruban, 2026-10-12) : recopie l'etat de
                                                # l'esclave, sinon un ruban allume sur l'esclave restait OFF dans la page du maitre.
                                                # Pas de boucle : 'etat' est deja a jour, set_power_handler ne renvoie donc aucun 0x06.
                                                var puissances = tasmota.get_power()
                                                var rang = device["id"] - 1
                                                if (rang >= 0 && rang < size(puissances) && puissances[rang] != (valeur == "ON"))
                                                    tasmota.set_power(rang, valeur == "ON")
                                                end
                                            end
                                        end
                                    end
                                end
                            end
                        end
                    end
                end

                # Modifie en json persist
                if (env)    modules[cleModule]["environnement"] = env    end
            end
        except .. as erreur, message
            logFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_ERREUR: traitement de la reponse de %s (0x%02X, registre %s) : %s -> %s",
                              nameTasmotaSlaveModBus, msg.find("FunctionCode", 0), str(msg.find("StartAddress")), erreur, message), LOG_LEVEL_ERREUR, "slaveModbus")
        end

        # Ajoute la donnée reçue en json
        self.log("MODBUS_RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: dataJson=" + json.dump(self.dataJson), LOG_LEVEL_DEBUG_PLUS)

        # Acquitte le message en vol (reponse recue)
        if (estReponseEnVol)    modbusFonctions.termineEnVol(true)    end
    end

    # Règles sur changement d'état lors du démarrage de Tasmota
    def changementEtatDemarrage(value, trigger, msg)
        import string
        import json
        import re
        import modbusFonctions

        # Test
        self.log("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: -------------------- SlaveModBus changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
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

                                                # Execute la commande 'Power' si différent. Un ruban WS2812 (1376), lui, est
                                                # toujours RELU (plus bas) : l'esclave est maitre de son ruban (2026-10-11).
                                                if (devices[cleDev]["type"] != 1376 && tabEtatRelais[devices[cleDev]["id"] - 1] == devices[cleDev]["etat"])        continue    end
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
                                                        # LEDS WS2812B : DEMANDE de l'etat reel (0x03), et non plus renvoi de la couleur
                                                        # memorisee (2026-10-11) : la cuve colore elle-meme son ruban (niveau, erreur),
                                                        # le renvoi l'ecrasait a chaque demarrage du maitre.
                                                        if (devices[cleDev]["type"] == 1376)
                                                            trameModBus = self.demandeLecture(devices[cleDev], cleDevices, trameModBus["DeviceAddress"])

                                                            self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Demande l'etat du ruban WS2812 n°%i (teinte, saturation, luminosite) !", devices[cleDev]["id"]), LOG_LEVEL_INFO)
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

                                                        # Aucune lecture au demarrage (envoi commente ci-dessous) : le releve periodique
                                                        # (releveEsclaves, toutes les periodeReleve() s) s'en charge. Message corrige le 2026-10-11 :
                                                        # il annoncait une demande jamais envoyee.
                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: " + (cleDevices == "interrupteurs" ? "Interrupteur" : (cleDevices == "boutons" ? "Bouton" : "Capteur")) + " n°%i : etat lu par le releve periodique (toutes les %i s), pas au demarrage", devices[cleDev]["id"], self.periodeReleve()), LOG_LEVEL_DEBUG)

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

                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Entrée analogique n°%i : valeur lue par le releve periodique (toutes les %i s), pas au demarrage", devices[cleDev]["id"], self.periodeReleve()), LOG_LEVEL_DEBUG)

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

                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Compteur n°%i : valeur lue par le releve periodique (toutes les %i s), pas au demarrage", devices[cleDev]["id"], self.periodeReleve()), LOG_LEVEL_DEBUG)

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
                                                            
                                                        self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Thermomètre n°%i : valeur lue par le releve periodique (toutes les %i s), pas au demarrage", devices[cleDev]["id"], self.periodeReleve()), LOG_LEVEL_DEBUG)

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

                # Option A (2026-09-29) : releve periodique des appareils virtuels, par le maitre
                # seul. add_cron et non set_timer : set_timer est peu fiable sur ESP32-P4 (cf.
                # modbusFonctions.armeTimer). Premier releve a la prochaine demi-minute.
                if (drivers["ModBus"].find("id", 99) == 0)
                    tasmota.remove_cron("releve_TasmotaSlaveModBus")
                    tasmota.add_cron(string.format("*/%i * * * * *", self.periodeReleve()), def() self.releveEsclaves() self.verifieChienDeGarde() end, "releve_TasmotaSlaveModBus")
                    self.log(string.format("MODBUS_TASMOTA_SLAVE_CHGT_ETAT_DEMARRAGE: Releve des esclaves + chien de garde armes (toutes les %i s)", self.periodeReleve()), LOG_LEVEL_INFO)
                end
            end
        end
    end

    # Demande de LECTURE d'un appareil virtuel, au protocole maison : un appareil par requete,
    # StartAddress = type + idModBus - 1 (cf. modbusFonctions.executeCmdModbus cote esclave).
    # Retourne la trame, ou nil si la famille d'appareil ne se lit pas.
    def demandeLecture(device, famille, idEsclave)
        var trame = {"DeviceAddress": idEsclave, "FunctionCode": 0, "StartAddress": device["type"] + device["idModBus"] - 1,
                     "type": "", "Count": 1, "Values": 0}

        if (famille == "interrupteurs" || famille == "capteurs" || famille == "boutons")
            trame["FunctionCode"] = 0x02
            trame["type"] = "uint8"
        # Relais (224 Relais, 256 Relais_i) : lecture 0x01 de l'etat reel, compare a l'etat
        # commande par recupereReponseModBus.
        elif (famille == "relais" && (device["type"] == 224 || device["type"] == 256))
            trame["FunctionCode"] = 0x01
            trame["type"] = "uint8"
        # Ruban WS2812 (1376, 2026-10-11) : lecture 0x03 de 4 registres, l'etat REEL du ruban
        # [teinte, saturation, luminosite, animation] a l'echelle HSBColor (modbusFonctions.etatRuban).
        elif (famille == "relais" && device["type"] == 1376)
            trame["FunctionCode"] = 0x03
            trame["type"] = "uint16"
            trame["Count"] = 4
        elif (famille == "analogiques" || famille == "compteurs")
            trame["FunctionCode"] = 0x04
            trame["type"] = "uint32"
        elif (famille == "thermometres")
            trame["FunctionCode"] = 0x04
            trame["type"] = "float"
            if (device["type"] == 1216)    trame["Count"] = 2    end     # DHT22 : T + humidite
        else
            return nil
        end
        return trame
    end

    # Option A (2026-09-29) : SOURCE DE VERITE de l'etat des esclaves. Chaque appareil virtuel
    # 'ModBus_TasmotaSlaveModBus<n>' est relu par une requete de la file du maitre (serie) :
    # une reponse perdue, ou un push UDP (option B) manque, sont repares au releve suivant.
    # La reponse est traitee par recupereReponseModBus, comme toute reponse a une requete.
    # Retourne le nombre de demandes placees dans la file.
    def releveEsclaves()
        import string
        import modbusFonctions

        var nb = 0
        var esclaves = drivers["ModBus"]["environnement"].find("TasmotaSlaveModBus", {})
        var sondes = {}         # esclaves muets deja sondes pendant ce cycle (audit G3)

        for cleModule: modules.keys()
            if (type(modules[cleModule]) != "instance")    continue    end
            var env = modules[cleModule].find("environnement")
            if (type(env) != "instance")    continue    end

            for famille: env.keys()
                if (type(env[famille]) != "instance")    continue    end

                for cleDevice: env[famille].keys()
                    var device = env[famille][cleDevice]
                    if (type(device) != "instance")    continue    end
                    if (device.find("activation", "OFF") != "ON" || device.find("idModBus") == nil)    continue    end

                    # ex: virtuel = "ModBus_TasmotaSlaveModBus2" -> esclave "TasmotaSlaveModBus2"
                    var virtuel = str(device.find("virtuel", "OFF"))
                    if (string.find(virtuel, "ModBus_TasmotaSlaveModBus") != 0)    continue    end
                    var esclave = esclaves.find(string.split(virtuel, "_")[1])
                    if (type(esclave) != "instance" || esclave.find("activation", "OFF") != "ON")    continue    end

                    var trame = self.demandeLecture(device, famille, int(esclave["id"]))
                    # Esclave declare muet (par la file : abandons de suite, ou par le chien de
                    # garde) : UNE seule sonde par cycle, pas tous ses appareils (audit G3).
                    var muet = modbusFonctions.estMuet(int(esclave["id"])) ||
                               (self.esclavesMuets != nil && self.esclavesMuets.find(int(esclave["id"]), false))
                    if (trame != nil && muet)
                        if (sondes.find(int(esclave["id"]), false))    continue    end
                        sondes[int(esclave["id"])] = true
                    end
                    if (trame != nil)
                        modbusFonctions.envoiMsgModbus(trame, "Commande", trame["StartAddress"])
                        nb += 1
                    end
                    tasmota.yield()
                end
            end
        end

        self.log(string.format("MODBUS_TASMOTA_SLAVE_RELEVE: %i demande(s) de lecture placee(s) dans la file", nb), LOG_LEVEL_DEBUG)
        return nb
    end

    # Periode du releve des esclaves, en secondes (cron). Le chien de garde declare muet un
    # esclave sans contact depuis plus de 3 periodes (3 releves manques).
    def periodeReleve() return 30 end

    # Chien de garde (2026-09-29) : un esclave est vivant tant qu'il repond a une requete
    # (appariee) ou qu'il pousse un etat. Appele par recupereReponseModBus.
    def noteContact(idEsclave)
        import string

        if (self.derniersContacts == nil)    self.derniersContacts = {}    end
        if (self.esclavesMuets == nil)    self.esclavesMuets = {}    end
        self.derniersContacts[idEsclave] = tasmota.rtc()["local"]
        import modbusFonctions
        modbusFonctions.noteContactBus(idEsclave)       # leve aussi l'etat muet de la file (push compris)
        if (self.esclavesMuets.find(idEsclave, false))
            self.esclavesMuets.remove(idEsclave)
            logFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_CHIEN_DE_GARDE: l'esclave d'ID=%i repond de nouveau", idEsclave), LOG_LEVEL_INFO, "slaveModbus")
        end
    end

    # Capteur sans mesure (2026-10-10) : l'esclave a repondu la sentinelle (NaN / 0x7FFFFFFF ; nil
    # apres le pont serie). Etat constate 'defaillant', journalise UNE fois (erreur) et pas a chaque
    # releve ; le retour est journalise a la premiere vraie valeur (recupereReponseModBus).
    # L'esclave, lui, repond : son chien de garde n'est pas concerne.
    def noteDefaillant(device, nomEsclave)
        import string
        if (device.find("etatConstate") != "defaillant")
            logFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_CAPTEUR: '%s' (%s) : aucune mesure (capteur absent ou defaillant)",
                              str(device.find("nom", "?")), nomEsclave), LOG_LEVEL_ERREUR, "slaveModbus")
        end
        device["etatConstate"] = "defaillant"
        device["constateA"] = tasmota.rtc()["local"]
    end

    # Chien de garde (2026-09-29), sur le modele de la carte 16 relais : un esclave actif sans
    # contact depuis plus de 3 periodes de releve est declare MUET, une seule fois, et les
    # etats constates de ses appareils virtuels passent a 'inconnu'. L'etat COMMANDE ('etat')
    # n'est pas touche. Le retour a la normale se fait au contact suivant (noteContact), et
    # chaque appareil retrouve son constat a sa prochaine valeur recue.
    # Retourne le nombre d'appareils passes a 'inconnu'.
    def verifieChienDeGarde()
        import string

        if (self.derniersContacts == nil)    self.derniersContacts = {}    end
        if (self.esclavesMuets == nil)    self.esclavesMuets = {}    end
        var maintenant = tasmota.rtc()["local"]
        var esclaves = drivers["ModBus"]["environnement"].find("TasmotaSlaveModBus", {})
        var nb = 0

        for cle: esclaves.keys()
            var esclave = esclaves[cle]
            if (type(esclave) != "instance" || esclave.find("activation", "OFF") != "ON")    continue    end
            var id = int(esclave["id"])
            var dernier = self.derniersContacts.find(id)

            # Premier passage : le decompte part de maintenant (pas d'esclave muet au boot)
            if (dernier == nil)
                self.derniersContacts[id] = maintenant
                continue
            end
            if (self.esclavesMuets.find(id, false) || maintenant - dernier <= 3 * self.periodeReleve())    continue    end

            self.esclavesMuets[id] = true
            logFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_CHIEN_DE_GARDE: esclave %s (ID=%i) muet depuis %i s -> etats constates passes a 'inconnu'",
                              cle, id, maintenant - dernier), LOG_LEVEL_ERREUR, "slaveModbus")
            nb += self.passeInconnu("ModBus_" + cle)
        end
        return nb
    end

    # Passe a 'inconnu' l'etat constate des appareils RELUS portes par le virtuel donne
    # (ex: "ModBus_TasmotaSlaveModBus2"). Retourne le nombre d'appareils touches.
    def passeInconnu(virtuel)
        var nb = 0
        for cleModule: modules.keys()
            if (type(modules[cleModule]) != "instance")    continue    end
            var env = modules[cleModule].find("environnement")
            if (type(env) != "instance")    continue    end

            for famille: env.keys()
                if (type(env[famille]) != "instance")    continue    end
                for cleDevice: env[famille].keys()
                    var device = env[famille][cleDevice]
                    # Seuls les appareils que le releve RELIT passent a 'inconnu' (audit G7) : les
                    # autres (LEDs WS2812 1376...) n'en sortiraient jamais, faute de lecture.
                    if (type(device) == "instance" && device.find("virtuel") == virtuel && self.demandeLecture(device, famille, 0) != nil)
                        device["etatConstate"] = "inconnu"
                        nb += 1
                    end
                end
            end
        end
        return nb
    end
end

# Active le Driver de controle global des modules virtuelles ModBus
# Publie la classe dans le module (solidification + import).
modBus_TasmotaSlaveModBus.MODBUS_TASMOTA_SLAVE = MODBUS_TASMOTA_SLAVE

# init() : APPELEE AUTOMATIQUEMENT par 'import modBus_TasmotaSlaveModBus' (be_module.c:285-296, module_init).
# Ne PAS la rappeler depuis autoexec. Reprend a l'identique le code d'activation de niveau
# fichier d'avant (gardes comprises) ; l'instance est publiee dans global.modBus_TasmotaSlaveModBus.
def modBus_TasmotaSlaveModBus_init(m)
    import global

    if (drivers["ModBus"].find("activation", "OFF") == "ON")
        if (drivers["ModBus"]["environnement"].find("TasmotaSlaveModBus", false) != false)
            for cle: drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].keys()
                import string

                if type(drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle]) != "instance"   continue    end

                try
                    if (drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][cle].find("activation", "OFF") == "ON")
                        global.modBus_TasmotaSlaveModBus = m.MODBUS_TASMOTA_SLAVE()
                        tasmota.add_driver(global.modBus_TasmotaSlaveModBus)

                        logFonctions.log("MODBUS_TASMOTA_SLAVE: Driver activé !", LOG_LEVEL_DEBUG, "slaveModbus")

                        break
                    end
                except .. as error, message
                    logFonctions.log(string.format("MODBUS_TASMOTA_SLAVE_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR, "slaveModbus")
                end
            end
        end
    end
    return m
end
modBus_TasmotaSlaveModBus.init = modBus_TasmotaSlaveModBus_init
