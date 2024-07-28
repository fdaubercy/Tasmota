# Définition du module
var rangeExtenderFonctions = module("/rangeExtenderFonctions")

# Enregistre les abonnements MQTT pour capter les emisions des données des capteurs des modules connectés
# Gestion des messages mqtt des abonnements par la fonction type désignée dans mqtt.subscribe : 'f(topic, idx, data, databytes)' dans ce script
# Réalilse le routage
rangeExtenderFonctions.routageAndMqttRangeExtender = def(modulesConnectes)
	import mqtt
	import string

	for cle: modulesConnectes.keys()
		# Enregistre les abonnements MQTT pour capter les emisions des données des capteurs du module 
		log ("ROUTAGE_SUBSCRIBE_RANGEEXTENDER: S'abonne au topic du module " + str(cle), LOG_LEVEL_DEBUG)
        mqtt.unsubscribe("tele/" + modulesConnectes[cle]["topicModule"] + "/SENSOR")
		mqtt.subscribe("tele/" + modulesConnectes[cle]["topicModule"] + "/SENSOR", / topic, idx, payload -> rangeExtenderFonctions.recupereCapteursConnectes(topic, idx, payload))

		# Réalilse le routage
		log ("ROUTAGE_SUBSCRIBE_RANGEEXTENDER: Paramètre le routage NAPT du module " + str(cle), LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("RgxPort tcp, %i, %s, 80", modulesConnectes[cle]["routagePort"], modulesConnectes[cle]["IPAddress"]), boolMute)
	end
end

rangeExtenderFonctions.reglageRangeExtender = def(cmd, idx, payload, payload_json)
    import string
    import json
    import mqtt
    import gestionFileFolder
    import webFonctions

    var fonction = false
    var parametre = false
    var reponse_cmnd = {}
    
    # Test   
    log ("REGLAGE_RANGE_EXTENDER: -------------------- reglageRangeExtender -------------------", LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RANGE_EXTENDER: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RANGE_EXTENDER: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RANGE_EXTENDER: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RANGE_EXTENDER: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        fonction = str(string.split(payload, " ", 1)[0])
        parametre = str(string.split(payload, " ", 1)[1])
    else fonction = payload
    end

    log ("REGLAGE_RANGE_EXTENDER: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RANGE_EXTENDER: parametre=" + str(parametre), LOG_LEVEL_DEBUG_PLUS)

    var groupTopic = tasmota.cmd("GroupTopic", boolMute)["GroupTopic1"]
    var serveur = controleGeneral.parametres["serveur"]

    var reponse = tasmota.cmd("STATUS 5", boolMute)
    reponse_cmnd["nom"] = serveur["nom"]
    reponse_cmnd["Gateway"] = reponse["StatusNET"]["Gateway"]
    reponse_cmnd["Mac"] = reponse["StatusNET"]["Mac"]
    reponse_cmnd["IPAddress"] = reponse["StatusNET"]["IPAddress"]
    if serveur["rangeExtender"].find("idModuleRangeExpender", 0) != 0 
        reponse_cmnd["routagePort"] = 8080 + serveur["rangeExtender"].find("idModuleRangeExpender", 99) - 1
    end
    reponse_cmnd["idModule"] = serveur["rangeExtender"].find("idModuleRangeExpender", 99)
    reponse_cmnd["topicModule"] = str(serveur["mqtt"].find("topic", ""))

    # Retourne les données de paramétrage du routage NAPT
    # Uniquement si c'est le point d'accès (d'id=0)
    if string.toupper(fonction) == "ROUTAGENAPT" && serveur["rangeExtender"].find("idModuleRangeExpender", 99) == 0
        parametre = json.load(parametre)

        # Si c'est un message d'un module RangeExtender & routageNAPT==false
        if parametre["idModule"] > 0 && !parametre.find("routageNAPT", false)
            # Enregistre ou Mets à jour en variable les modules RangeExtender connectés dans un tableau
            controleRangeExtender.modulesConnectes[str(parametre["idModule"])] = parametre
            controleGeneral.parametres["serveur"]["rangeExtender"]["modulesConnectes"] = controleRangeExtender.modulesConnectes
            if (gestionFileFolder.readFile("/modulesConnectes.json") != json.dump(controleRangeExtender.modulesConnectes))
                gestionFileFolder.writeFile("/modulesConnectes.json", json.dump(controleRangeExtender.modulesConnectes))
            end

            # Enregistre les abonnements MQTT pour capter les emisions des données des capteurs du module 
            # Réalilse le routage
            rangeExtenderFonctions.routageAndMqttRangeExtender(controleRangeExtender.modulesConnectes)

            reponse_cmnd["routageNAPT"] = "OK"

            # Le Point d'accès renvoi aux modules connectés ses paramètres
            webFonctions.envoiMQTT(string.format("cmnd/%s/ReglageRangeExtender", groupTopic), "routageNAPT " + json.dump(reponse_cmnd), "")
        end
    # Gère la réponse à la commande envoyée
    # Uniquement les modules connectés (d'id>0)
    elif string.toupper(fonction) == "ROUTAGENAPT" && serveur["rangeExtender"].find("idModuleRangeExpender", 0) > 0
        parametre = json.load(parametre)

        # Si c'est un message du maitre RangeExtender & routageNAPT=OK
        if parametre["idModule"] == 0 && parametre["routageNAPT"] == "OK"
            # Le module connecté enregistre le topic du maitre en json persist
            controleGeneral.parametres["serveur"]["rangeExtender"]["AP"]["topic"] = parametre["topicModule"]

            # Enregistre en json
            persist.parametres = controleGeneral.parametres	
            persist.save()
        end
    end

    # Lance la commande paramétrage du routage NAPT sur le point d'accès vers ce module
    # Uniquement les modules (Pas le point d'accès d'id=0)
    if string.toupper(fonction) == "ENVOIPARAMNAPT" && serveur["rangeExtender"].find("idModuleRangeExpender", 0) > 0
        webFonctions.envoiMQTT(string.format("cmnd/%s/ReglageRangeExtender", groupTopic), "routageNAPT " + json.dump(reponse_cmnd), "")
    end

    # Commande réussie
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

rangeExtenderFonctions.configExtenderByJson = def(json)
    import string
    import configGlobal

    var reponseCMD

	# Règle le point d'accès Range Extender si activé
    json = json["AP"]
	if json.find("etat", "OFF") == "ON"
		# Etat du point d'accès
		if (configGlobal.testeParam("RgxState", json["etat"], "str"))
			log ("CONFIG_EXTENDER: Regle l'état d'activation du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
		end

		# Etat du routage NAPT du point d'accès
        if (configGlobal.testeParam("RgxNAPT", json["routeNAPT"], "str"))
			log ("CONFIG_EXTENDER: Regle le routage du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
		end

		# Nom AP & Mot de passe
		reponseCMD = tasmota.cmd("RgxSSId", boolMute)
		if str(reponseCMD["Rgx"]["SSId"]) != str(json["SSID"]) || str(reponseCMD["Rgx"]["Password"]) != str(json["mdp"])
			log ("CONFIG_EXTENDER: Regle le nom et le mot de passe du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog RgxSSId %s; RgxPassword  %s", json["SSID"], json["mdp"]))
		end

		# Adresse IP et Masque de sous-réseau
		if str(reponseCMD["Rgx"]["IPAddress"]) != str(json["IPAddress"]) || str(reponseCMD["Rgx"]["Subnetmask"]) != str(json["Subnet"])
			log ("CONFIG_EXTENDER: Regle l'adresse IP & le masque de sous-réseau du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog RgxAddress %s; RgxSubnet %s", json["IPAddress"], json["Subnet"]))
		end
	end
end

# Règles sur changement d'état lors du démarrage de Tasmota
rangeExtenderFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt

	# Test
	log ("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: -------------------- RangeExtender changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	log ("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	log ("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	log ("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

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
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
			# Si c'est un esclave Range Extender
			if controleGeneral.parametres["serveur"].find("rangeExtender", {}).find("idModuleRangeExpender", 0) > 0
				# Envoi ses paramètres au RangeExtender
				log ("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: Envoi au Range Extender ses paramètres !", LOG_LEVEL_DEBUG)
				tasmota.cmd("ReglageRangeExtender envoiParamNAPT", boolMute)
			end
        elif msg["MQTT"].find("Disconnected", 0)
        end
    end
end

# Gère les données reçues par MQTT sur les topics abonnés
# Ex : enregistrement des données issues des capteurs qui sont externes ou virtuels
rangeExtenderFonctions.recupereCapteursConnectes = def(topic, idx, data)
    import json
    import string

    # Uniquement si c'est un Point d'accès Range Extender
    if (controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 0) > 0)   return  end

    # Test   
    log ("REC_CAPTEURS_CONNECTES: -------------------- recupereCapteursConnectes -------------------", LOG_LEVEL_DEBUG_PLUS)
    log ("REC_CAPTEURS_CONNECTES: topic=" + str(topic), LOG_LEVEL_DEBUG_PLUS)
    log ("REC_CAPTEURS_CONNECTES: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    log ("REC_CAPTEURS_CONNECTES: data=" + str(data), LOG_LEVEL_DEBUG_PLUS)

    # ex: data={"Time":"2024-05-31T13:58:16","Débit":{"Rate":[0,0],"AmountToday":[0,0],"DurationToday":[0,0],"Source":"average","AmountUnit":"L","Unit":"l/min"},"nameDebitmetres": ["D��bit Entrée - Cuisine", "Débit Salon - SàM"], "idDebitmetres": [1, 2]}
    var tabParam = string.split(topic, "/")
    var prefix = ""
    var suffix = ""

    # Topic de la forme: %fonction utilisée%/%identification du module RangeExtender%
    topic = ""
    for nb: 0 .. tabParam.size() - 1
        if (nb == 0)    
            prefix = tabParam[nb]
        elif (nb == tabParam.size() - 1)    
            suffix = tabParam[nb]  
        else
            topic = topic + (topic == "" ? "" : "/") + tabParam[nb]
        end
    end
    idx = (string.find(topic, "module") > - 1 ? int(string.split(topic, "module")[1]) : 0)
    data = json.load(data)

    # Réception d'une trame 'tele/%topic%/SENSOR'
    if prefix == "tele" && suffix == "SENSOR"
        # Débitmètres: Gestion des trames MQTT des capteurs connectés
        if (string.find(topic, "pac") > -1)
            for cleModules: controleGeneral.parametres["modules"].keys()
                var modul = controleGeneral.parametres["modules"][cleModules]
                if type(modul) != "instance"
                    continue
                end	

                # Si le module est activé uniquement
                if modul.find("activation", "OFF") == "OFF"
                    continue
                end

                for cleEnv: modul["environnement"].keys()
                    if type(modul["environnement"][cleEnv]) != "instance"
                        continue
                    end	

                    # Débitmètres 
                    if data.find("Débit", false) && cleEnv == "debitmetres"
                        var debitmetres = modul["environnement"].find(cleEnv, false)
                            
                        if debitmetres
                            for cleD: debitmetres.keys()
                                if type(debitmetres[cleD]) != "instance"
                                    continue
                                end	                   

                                for nb: 0 .. 1
                                    if debitmetres[cleD]["id"] == idx * data["idDebitmetres"][nb]
                                        debitmetres[cleD]["value"] = data["Débit"]["Rate"][nb]
                                        debitmetres[cleD]["AmountToday"] = data["Débit"]["AmountToday"][nb]
                                        debitmetres[cleD]["DurationToday"] = data["Débit"]["DurationToday"][nb]
                                    end
                                end
                            end

                            controleGeneral.parametres["modules"][cleModules]["environnement"][cleEnv] = debitmetres
                        end

                        # Sort de la fonction
                        return
                    end
                end
            end
        end
    end

    tasmota.resp_cmnd_done()
end

# Retourne le module lors de l'importation
return rangeExtenderFonctions