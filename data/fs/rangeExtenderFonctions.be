# Définition du module
var rangeExtenderFonctions = module("/rangeExtenderFonctions")

rangeExtenderFonctions.DEBUG = nil

rangeExtenderFonctions.log = def(msg, levelDebug)
    if (rangeExtenderFonctions.DEBUG == nil)
        rangeExtenderFonctions.DEBUG = serveur["rangeExtender"].find("debug", "OFF")
    end

    if (rangeExtenderFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

# Réalilse le routage
# Active RgxNAPT: RoutageRangeExtender
# RgxPort tcp, 8080, 192.168.4.2, 80
rangeExtenderFonctions.routageRangeExtender = def(cmd, idx, payload, payload_json)
	import string
    import json
    import gestionFileFolder
    import persist
    import re

    var jsonData = {}
    var reponse_cmnd = {"RoutageRangeExtender": {"commmande": "", "status": "Echec..."}}
    var typeID = "esclave" + str(idx)
    
    # Test   
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: -------------------- routageRangeExtender -------------------", LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Lit le fichier json
    var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
    if (paramDiscovery == nil)
        rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: Le fichier 'discovery.json' n'existe pas ou est vide !", LOG_LEVEL_DEBUG_PLUS)
        return
    end

    reponse_cmnd["RoutageRangeExtender"]["status"] = "Echec..."

    # Parcours le json en listant les adresses MAC (item = adresse MAC)
    for item: paramDiscovery.keys()
        var pattern = re.compile('^(maitre|esclave[0-9]+)$')
        var result = {}

        # Parcours tous les esclaves enregistrés et les marque tous 'Offline'
        for cle : paramDiscovery[item].keys()
            # Evite le maitre
            if (cle == "maitre")    continue    end

            if pattern.match(cle)
                # result.insert(cle, jsonDiscovery[cle])
                # break

                if (paramDiscovery[item]["lwt"] == "Online")
                    # Réalilse le routage
                    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: Paramètre le routage NAPT du module " + paramDiscovery[item][cle]["nom"], LOG_LEVEL_DEBUG)

                    reponse_cmnd["RoutageRangeExtender"]["commande"] = string.format("RgxPort tcp, %i, %s, 80", int(paramDiscovery[item][cle]["rangeExtender"]["routagePort"]),paramDiscovery[item][cle]["IPAddress"])
                    tasmota.cmd(reponse_cmnd["RoutageRangeExtender"]["commande"], boolMute)         # ex: RgxPort tcp, 8080, 10.99.0.2, 80
                end
            end
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["RoutageRangeExtender"]["status"] = "Succès"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# exemples: 
# ReglageRangeExtender logActivation OFF
rangeExtenderFonctions.reglageRangeExtender = def(cmd, idx, payload, payload_json)
    import string
    import json
    import gestionFileFolder

    var fonction = false
    var parametres = false
    var jsonData = {}
    var reponse_cmnd = {"ReglageRangeExtender": {}}
    var typeID
    
    # Test   
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: -------------------- reglageRangeExtender -------------------", LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    log("REGLAGE_RANGE_EXTENDER: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres != false)
        if (parametres.size() > 0)	log("REGLAGE_RANGE_EXTENDER: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
        if (parametres.size() > 1)	log("REGLAGE_RANGE_EXTENDER: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end
    end

    # Activation ou désactivation des logs du RangeExtender -> ordre: logActivation
    if string.toupper(fonction) == "LOGACTIVATION"
        try
            # Adapte le paramètre
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            rangeExtenderFonctions.DEBUG = parametres[0]

            # Sauvegarde le paramètre
            serveur["rangeExtender"]["debug"] = parametres[0]
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["ReglageRangeExtender"]["logActivated"] = str(rangeExtenderFonctions.DEBUG)
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

rangeExtenderFonctions.configExtenderByJson = def()
    import persist
    import configGlobal
    import string

    var reponseCMD
    var json = serveur["rangeExtender"]

	# Règle le point d'accès Range Extender si activé (Si Maitre RangeExtender)
    if (json.find("activation", "OFF") == "ON")
        # Etat du routage NAPT du point d'accès
        if (configGlobal.testeParam("RgxNAPT", json["AP"]["routeNAPT"], "str"))
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle le routage du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
        end

        # Nom AP & Mot de passe
        reponseCMD = tasmota.cmd("RgxSSId", boolMute)
        if str(reponseCMD["Rgx"]["SSId"]) != str(json["AP"]["SSID"]) || str(reponseCMD["Rgx"]["Password"]) != str(json["AP"]["mdp"])
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle le nom et le mot de passe du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
            tasmota.cmd(string.format("Backlog RgxSSId %s; RgxPassword  %s", json["AP"]["SSID"], json["AP"]["mdp"]), boolMute)
        end

        # Adresse IP et Masque de sous-réseau
        if str(reponseCMD["Rgx"]["IPAddress"]) != str(json["AP"]["IPAddress"]) || str(reponseCMD["Rgx"]["Subnetmask"]) != str(json["AP"]["Subnet"])
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle l'adresse IP & le masque de sous-réseau du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
            tasmota.cmd(string.format("Backlog RgxAddress %s; RgxSubnet %s", json["AP"]["IPAddress"], json["AP"]["Subnet"]), boolMute)
        end

        # Etat du point d'accès
        if (configGlobal.testeParam("RgxState", json["activation"], "str"))
            tasmota.cmd(string.format("RgxState %s", json["activation"]), boolMute)
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle l'état d'activation du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
        end
    end
end

# Règles sur changement d'état lors du démarrage de Tasmota
rangeExtenderFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import persist
    import string
    import json

    var rangeExtender

	# Test
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: -------------------- RangeExtender changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

    if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    tasmota.yield()

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
        elif msg["WIFI"].find("Disonnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            # Uniquement si c'est un Point d'accès Range Extender
            # Lance le routage TCP pour les différents esclaves connus
            if serveur["rangeExtender"].find("id", 99) == 0
                tasmota.cmd("RoutageRangeExtender", boolMute)
            end
        elif msg[trigger].find("Save", 0)
        end
    # Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
	# Se déclenche un évènement sur les heures et la synchronisation NTP (si activé)
    elif (trigger == "Time")
        # A chaque fois que le NTP est initialisé et l'heure synchronisée
        if type(msg["Time"]) == "instance"
            if msg["Time"].find("Initialized", 0)
            # A chaque heure, quand le système NTP est synchronisé
            elif msg["Time"].find("Set", 0)
            end
        end
    end
end

# Se charge d'afficher le bouton de lien vers lapage webUI des clients Ranextender connectés
# Fonction inutilisée
rangeExtenderFonctions.afficheBoutonsModulesEsclaves = def()
    import webserver
    import string
    import gestionFileFolder
    import json

    var rgxClients = {}
    var i = 1

    # Lit le fichier json
    var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))

    tasmota.yield()

    # Ajoute autant de boutons que de modules connectés au RangeExtender
    # Uniquement si c'est un Point d'accès Range Extender
    if serveur["rangeExtender"].find("id", 99) == 0
        rangeExtenderFonctions.log("RANGE_EXTENDER: Affichage du bouton !", LOG_LEVEL_DEBUG)

        rgxClients = tasmota.cmd("RgxClients")["RgxClients"]

        # Si au moins 1 client est connecté
        if (rgxClients.size() > 0)
            # webserver.content_send("<hr>")
            for mac: rgxClients.keys()
                for cle: paramDiscovery.keys()
                    tasmota.yield()

                    # Evite le maitre
                    for item: paramDiscovery[cle].keys()
                        if (paramDiscovery[cle][item] != nil && item != "maitre")
                            var adresseMac = string.replace(paramDiscovery[cle][item].find("adresseMAC", ""), ":", "")
                            var etat = paramDiscovery[cle].find("lwt", "Offline")

                            if (adresseMac == mac && etat == "Online")
                                var url = "http://" + serveur["hostname"] + ".local:" + str(paramDiscovery[cle][item]["rangeExtender"].find("routagePort", 8080))
                                var titre = paramDiscovery[cle][item]["nom"]

                                # Active le routage NAPT si pas encore fait
                                rangeExtenderFonctions.log(f'RANGE_EXTENDER: Active le routage NAPT vers le module {titre:s} sur le port {paramDiscovery[cle][item]["rangeExtender"].find("routagePort", 8080):d} !', LOG_LEVEL_DEBUG)
                                tasmota.cmd(f'RgxPort tcp, {paramDiscovery[cle][item]["rangeExtender"].find("routagePort", 8080):d}, {paramDiscovery[cle][item].find("IPAddress", "192.168.4.1"):s}, 80', boolMute)

                                # Ouverture de la page dans un nouvel onglet
                                var btn = "<p></p><button class=\"button bgrn\" id=\"btn_test\" onclick=\"setTimeout(() => {window&#46;open(\'" + url + "\');}, 1000);\">" + titre + "</button>"
                                webserver.content_send(btn)
                            end
                        end
                    end
                end
            end
        end
    end
end

# Retourne le module lors de l'importation
return rangeExtenderFonctions