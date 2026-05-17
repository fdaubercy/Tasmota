# Définition du module
var configGlobal = module("/configGlobal")

# Fonction chargé de tester un paramètre enregistré avec celui présent en json
# paramTasmota: Commande envoyé à tasmota pour récupérer la donnée : ex=SetOption56
# paramJson: la donnée json sélectionnée: ex=data["selectSignalFort"]
# typeData: type de donnée à comparer: ex=real / int / str
# @Retourne true=changement du paramètre
configGlobal.testeParam = def(paramTasmota, paramJson, typeData)
	import string
	import persist

	var resultat = false

	# type par défaut
	typeData = (typeData == "" ? "str" : typeData)
	
	if paramJson != ""
		if (typeData == "str")
			resultat = string.split(str(tasmota.cmd(paramTasmota, boolMute)[paramTasmota]), " (")[0] != str(paramJson)
		elif (typeData == "int")
			resultat = int(tasmota.cmd(paramTasmota, boolMute)[paramTasmota]) != int(paramJson)
		elif (typeData == "real")
			resultat = real(tasmota.cmd(paramTasmota, boolMute)[paramTasmota]) != real(paramJson)
		elif (typeData == "json")
			import json
			resultat = json.load(tasmota.cmd(paramTasmota, boolMute)[paramTasmota]) != json.load(paramJson)
		end

		# Si les 2 paramètres sont différents
		if resultat
			if (str(paramJson) != "")	tasmota.cmd(string.format("%s %s", paramTasmota, str(paramJson)), boolMute)	end
			return true
		else return false
		end
	else return false
	end
end

# Paramétrage par tasmota.cmd à partir des paramètres enregistrés en json
# @json = _persist.json comprenant l'ensemble des paramètres
configGlobal.configGlobalByJson = def(nbIOActivesJSON)
	import string
    import globalFonctions
	import diversFonctions
	import configModules
    import persist
	import json

	var reponseCMD
	var enregistrePersistant = false
	var data

	var template = persist.template
	var gpioPinUtilises = []

	var ordreGPIO = []
	if (diverses.find("typeESP", "ESP32") == "ESP32")
		ordreGPIO = ["GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO9", "GPIO10", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO19", "GPIO20", "GPIO21", "GPIO22", "GPIO23", "GPIO24", "GPIO25", "GPIO26", "GPIO27", "GPIO6", "GPIO7", "GPIO8", "GPIO11", "GPIO32", "GPIO33", "GPIO34", "GPIO35", "GPIO36", "GPIO37", "GPIO38", "GPIO39"]	
	elif (diverses.find("typeESP", "ESP32") == "ESP32S3")
    	ordreGPIO = ["GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO19", "GPIO20", "GPIO21", "GPIO33", "GPIO34", "GPIO35", "GPIO36", "GPIO37", "GPIO38", "GPIO39", "GPIO40", "GPIO41", "GPIO42", "GPIO43", "GPIO44", "GPIO45", "GPIO46", "GPIO47", "GPIO48"]	
	elif (diverses.find("typeESP", "ESP32") == "ESP32P4")
    	ordreGPIO = ["GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO19", "GPIO20", "GPIO21", "GPIO22", "GPIO23", "GPIO24", "GPIO25", "GPIO26", "GPIO27", "GPIO28", "GPIO29", "GPIO30", "GPIO31", "GPIO32", "GPIO33", "GPIO34", "GPIO35", "GPIO36", "GPIO37", "GPIO38", "GPIO39", "GPIO40", "GPIO41", "GPIO42", "GPIO43", "GPIO44", "GPIO45", "GPIO46", "GPIO47", "GPIO48", "GPIO49", "GPIO50", "GPIO51", "GPIO52", "GPIO53", "GPIO54"]	
	end

	# Exemples de commandes :
	# template -> resultat = {"NAME":"ESP32 Relay x8","GPIO":[0,0,161,0,32,0,0,0,230,231,229,162,0,0,0,0,0,0,0,0,0,226,227,228,0,0,0,0,224,225,0,0,0,0,0,0],"FLAG":0,"BASE":1}
	# gpio -> renvoie une liste des parametres GPIO -> resultat partiel = {"GPIO0":{"0":"Aucun"},"GPIO1":{"0":"Aucun"}}
	# gpios -> renvoie une liste des numeros représentant le type de GPIO -> resultat partiel = {"GPIOs1":{"0":"Aucun","6208":"Option A","8448":"Option E","32":"Bouton"}}
	# module -> renvoie le nom du module activé -> resultat = {"Module":{"1":"ESP32-DevKit"}}
	# modules -> renvoie les modèles enregistrés -> resultat = {"Modules":{"0":"ESP32 Relay x8","1":"ESP32-DevKit"}}

	data = serveur["wifi"]
	# Recherche du signal le plus fort
	if configGlobal.testeParam("SetOption56", data["selectSignalFort"], "")
		log(string.format("CONTROLE_GENERAL: %s la recherche du signal wifi le plus fort !", (data["selectSignalFort"] == "ON" ? "Active" : "Désactive")), LOG_LEVEL_DEBUG)
	end

	# Règle la puissance du wifi et le mot de passe
	if configGlobal.testeParam("WifiPower", data["power"], "int")
		log("CONTROLE_GENERAL: Regle la puissance du Wifi !", LOG_LEVEL_DEBUG)		
	end

	if tasmota.cmd("SSId1", boolMute)["SSId1"] != data["reseau1"]["nomReseauWifi"]
		if data["reseau1"]["nomReseauWifi"] != "" && data["reseau1"]["mdpWifi"] != ""
			log(string.format("CONTROLE_GENERAL: Regle le SSID & le mot de passe pour le reseau %s!", data["reseau1"]["nomReseauWifi"]), LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog SSId1 %s; Password1 %s", 
													data["reseau1"]["nomReseauWifi"], 
													data["reseau1"]["mdpWifi"]), boolMute)
		end
	end

	if tasmota.cmd("SSId2", boolMute)["SSId2"] != data["reseau2"]["nomReseauWifi"]
		if data["reseau2"]["nomReseauWifi"] != "" && data["reseau2"]["mdpWifi"] != ""
			log(string.format("CONTROLE_GENERAL: Regle le SSID & le mot de passe pour le reseau %s!", data["reseau2"]["nomReseauWifi"]), LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog SSId2 %s; Password2 %s; AP 1", 
													data["reseau2"]["nomReseauWifi"], 
													data["reseau2"]["mdpWifi"]), boolMute)
		end
	end

	# Règle le nom du serveur
	data = serveur
	if configGlobal.testeParam("DeviceName", data["nom"], "")
		log("CONTROLE_GENERAL: Regle le nom du serveur !", LOG_LEVEL_DEBUG)		
	end
	
	# Règle le hostname
	if configGlobal.testeParam("Hostname", data["hostname"], "")
		log("CONTROLE_GENERAL: Regle le hostname !", LOG_LEVEL_DEBUG)
	end

	# Paramétrage le mDNS
	if configGlobal.testeParam("SetOption55", data["mDNS"], "")
		log(string.format("CONTROLE_GENERAL: %s le mDNS !", (data["mDNS"] == "ON" ? "Active" : "Désactive")), LOG_LEVEL_DEBUG)
	end

	# Règle les adresse IP / Masque de sous-reseau / Gateway / DNS Server
	if configGlobal.testeParam("IPAddress1", data["IP"]["IPAddress"], "str") && data["IP"]["IPAddress"] != ""
		log("CONTROLE_GENERAL: Regle l'adresse IP du module !", LOG_LEVEL_DEBUG)
	end
	if configGlobal.testeParam("IPAddress2", data["IP"]["IPGateway"], "str") && data["IP"]["IPGateway"] != ""
		log("CONTROLE_GENERAL: Regle l'adresse IP de la passerelle !", LOG_LEVEL_DEBUG)
	end
	if configGlobal.testeParam("IPAddress3", data["IP"]["Subnet"], "str") && data["IP"]["Subnet"] != ""
		log("CONTROLE_GENERAL: Regle le masque de sous-réseau !", LOG_LEVEL_DEBUG)
	end
	if configGlobal.testeParam("IPAddress4", data["IP"]["DNSServer"], "str") && data["IP"]["DNSServer"] != ""
		log("CONTROLE_GENERAL: Regle l'adresse IP du serveur DNS !", LOG_LEVEL_DEBUG)
	end

	# Règle le CORS (Cross Origin Resource Sharing)
	# Pouvoir faire des requetes XmlHttpRequest sur un autre domaine

	# Règle les paramètres MQTT
	# Active MQTT
	# Paramétrage supprimé pour permettre l'émission de messages MQTT même si le module est désactivé
	if configGlobal.testeParam("SetOption3", data["mqtt"]["activation"], "")
		log("CONTROLE_GENERAL: " + (tasmota.cmd("SetOption3", boolMute)["SetOption3"] == "ON" ? "Active" : "Désactive") + " les communications MQTT !", LOG_LEVEL_DEBUG)
	end

	if (data["mqtt"]["activation"] == "ON")
		# Hote & Port & Client
		if configGlobal.testeParam("MqttHost", data["mqtt"]["hote"], "") || configGlobal.testeParam("MqttPort", data["mqtt"]["port"], "") && configGlobal.testeParam("MqttClient", data["mqtt"]["client"], "")
			log("CONTROLE_GENERAL: Regle l'IP, le port MQTT et le client !", LOG_LEVEL_DEBUG)
		end
				
		# Utilisateur & Mot de passe & Topic
		if configGlobal.testeParam("MqttUser", data["mqtt"]["utilisateur"], "str") || configGlobal.testeParam("Topic", data["mqtt"]["topic"], "str")
			log("CONTROLE_GENERAL: Regle l'utilisateur, le mot de passe et le topic pour MQTT !", LOG_LEVEL_DEBUG)
		end

		# Gère les abonnements aux topics de groupe
		var cmd = tasmota.cmd("groupTopic", boolMute)
		if str(cmd["GroupTopic1"]) != str(data["mqtt"]["groupTopic1"])
			tasmota.cmd("GroupTopic1" + str(data["mqtt"]["groupTopic1"]), boolMute)
			tasmota.cmd("GroupTopic2" + str(data["mqtt"]["groupTopic2"]), boolMute)
			tasmota.cmd("GroupTopic3" + str(data["mqtt"]["groupTopic3"]), boolMute)
		end
	end

    # Réglage des paramètres diverses
	# Règle la localisation & le fuseau horaire
	data = diverses

	if configGlobal.testeParam("Latitude", data["localisation"]["latitude"], "real") || configGlobal.testeParam("Longitude", data["localisation"]["longitude"], "real")
		log("CONTROLE_GENERAL: Regle la localisation !", LOG_LEVEL_DEBUG)
	end

	# Active ou désactive le driver correspondant aux modules Real Time Clock (DS3231, DS1307, etc...)
	if (diverses["fuseauHoraire"].find("typeReglageHeure", "NTP") == "RTC")
		if (drivers["I2C"]["environnement"].find("DS3231", {}).find("activation", "OFF") == "ON")
			# Active le Driver 26
			var reponse = tasmota.cmd(string.format("I2CDriver%i", drivers["I2C"]["environnement"]["DS3231"]["I2CDriver"]), boolMute)["I2CDriver"]
			if (string.find(reponse, "!" + str(drivers["I2C"]["environnement"]["DS3231"]["I2CDriver"])) > -1 || string.find(reponse, str(drivers["I2C"]["environnement"]["DS3231"]["I2CDriver"])) == -1)
				tasmota.cmd(string.format("I2CDriver%i ON", drivers["I2C"]["environnement"]["DS3231"]["I2CDriver"]), boolMute)
			end
		end
	end

	if (configGlobal.testeParam("Timezone", data["fuseauHoraire"]["timezone"], "int"))
		log("CONTROLE_GENERAL: Regle la timezone !", LOG_LEVEL_DEBUG)
	end

	log("CONTROLE_GENERAL: Regle le fuseau horaire !", LOG_LEVEL_DEBUG)
	tasmota.cmd(string.format("TimeStd %i,%i,%i,%i,%i,%i", 
											data["fuseauHoraire"]["TimeStd"]["Hemisphere"], data["fuseauHoraire"]["TimeStd"]["Week"], data["fuseauHoraire"]["TimeStd"]["Month"], data["fuseauHoraire"]["TimeStd"]["Day"], data["fuseauHoraire"]["TimeStd"]["Hour"], data["fuseauHoraire"]["TimeStd"]["Offset"]), 
											boolMute)	
	tasmota.cmd(string.format("TimeDst %i,%i,%i,%i,%i,%i", 
											data["fuseauHoraire"]["TimeDst"]["Hemisphere"], data["fuseauHoraire"]["TimeDst"]["Week"], data["fuseauHoraire"]["TimeDst"]["Month"], data["fuseauHoraire"]["TimeDst"]["Day"], data["fuseauHoraire"]["TimeDst"]["Hour"], data["fuseauHoraire"]["TimeDst"]["Offset"]), 
											boolMute)	

	# Réglage de l'affichage de la Température interne de l'ESP32'
	if configGlobal.testeParam("SetOption146", data.find("affichageTempESP32", "OFF"), "")
		log(string.format("CONTROLE_GENERAL: Règle l'affichage de la température de l'ESP32' à %s !", data.find("affichageTempESP32", "OFF")), LOG_LEVEL_DEBUG)
	end

	# Réglage de l'affichage du modèle sur le webUI
	if configGlobal.testeParam("SetOption141", (data.find("affichageNomModele", "OFF") == "ON" ? "OFF" : "ON"), "")
		log(string.format("CONTROLE_GENERAL: Règle l'affichage du nom de modèle' à %s !", (data.find("affichageNomModele", "OFF") == "ON" ? "OFF" : "ON")), LOG_LEVEL_DEBUG)
	end

	# Réglage de la telePeriod
	if configGlobal.testeParam("TelePeriod", data.find("telePeriod", 300), "int")
		var periode = data.find("telePeriod", 300)

		log(string.format("CONTROLE_GENERAL: Règle la telePeriod à %is !", periode), LOG_LEVEL_DEBUG)
	end

	# Evite un reset sur appui long sur un bouton
	if configGlobal.testeParam("SetOption1", data["eviteResetBTN"], "")
		log("CONTROLE_GENERAL: Evite un reset sur appui long sur un bouton !", LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("SetOption1 %s", data["eviteResetBTN"]), boolMute)
	end
	
	# Paramètre le niveau des logs
	if configGlobal.testeParam("SerialLog", data["logs"]["level"], "int")
		log("CONTROLE_GENERAL: Regle le niveau des logs série!", LOG_LEVEL_DEBUG)
	end
    if configGlobal.testeParam("WebLog", data["logs"]["level"], "int")
        log("CONTROLE_GENERAL: Regle le niveau des logs Web!", LOG_LEVEL_DEBUG)
    end


	# Nb de fichiers de logs pour enregistrement dans plusieurs fichiers
	if configGlobal.testeParam("FileLog", data["logs"].find("nbLogsFiles", 0), "int")
		log("CONTROLE_GENERAL: " + (data["logs"].find("nbLogsFiles", 0) > 0 ? "Active" : "Désactive") + " l'enregistrement des logs " + (data["logs"].find("nbLogsFiles", 0) > 0 ? "dans maximum " + str(data["logs"].find("nbLogsFiles", 0)) + " fichiers" : "!"), LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("FileLog %i", data["logs"].find("nbLogsFiles", 0)), boolMute)
	end

	# Paramètre les relais/Switchs/Boutons/LED/CarteSD dans le modele et sur interface web en fonction des persist.json	
    # Pour les éléments non-spécifiques à certains modules & drivers
	enregistrePersistant = configModules.configDevicesByJon("modules", gpioPinUtilises, ordreGPIO, template, nbIOActivesJSON)
    enregistrePersistant = (configModules.configDevicesByJon("drivers", gpioPinUtilises, ordreGPIO, template, nbIOActivesJSON) || enregistrePersistant)

    # Mets à jour le fichier json/componentes.json
    diversFonctions.recupereTemplate(template)

	# Efface le paramétrage des GPIOs inutilisés dans le modèle
	log("CONTROLE_GLOBAL: gpioPinUtilises=" + str(gpioPinUtilises), LOG_LEVEL_DEBUG_PLUS)

	for gpioTemp: template["GPIO"].keys()
		var boolPinUtilise = false
	
		# On parcoure le tableau de pins utilisés à la recherche de 'ordreGPIO[gpioTemp]'
		for gpioPin: gpioPinUtilises.keys()
			if gpioPinUtilises[gpioPin] == ordreGPIO[gpioTemp]
				boolPinUtilise = true
			end
		end

		# Si 'ordreGPIO[gpioTemp]' n'est pas utilisé
		if !boolPinUtilise
			if template["GPIO"][gpioTemp] != 1 && template["GPIO"][gpioTemp] != 0
				# enregistrePersistant = true
				log("CONTROLE_GLOBAL: " + str(ordreGPIO[gpioTemp]) + " inutilise -> il sera reinitialise de " + str(template["GPIO"][gpioTemp]) + " a 1 !", LOG_LEVEL_DEBUG_PLUS)
				template["GPIO"][gpioTemp] = 1

                enregistrePersistant = true
			end
		end
	end

	# Enregistre le pin du modèle dans persist.json
	if enregistrePersistant
        log("CONTROLE_GLOBAL: template=" + str(template), LOG_LEVEL_DEBUG_PLUS)
        template["NAME"] = persist.template["NAME"]
        persist.template = template

		log("CONTROLE_GLOBAL: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)
		persist.save() 
	end
	
	# Paramètre le nouveau modèle
	reponseCMD = tasmota.cmd("Template", boolMute)
	if reponseCMD["BASE"] != template["BASE"] || reponseCMD["NAME"] != template["NAME"] || reponseCMD["GPIO"] != template["GPIO"] || reponseCMD["FLAG"] != template["FLAG"]
		log("CONTROLE_GLOBAL: Parametre le nouveau modele !", LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("Template {\"BASE\": %i, \"GPIO\": %s, \"NAME\": \"%s\", \"FLAG\": %i}", template["BASE"], str(template["GPIO"]), template["NAME"], template["FLAG"]), boolMute)
	end

	# Récupère le type de modeles (template) paramétrés
	reponseCMD = tasmota.cmd("Modules", boolMute)
	for cle: reponseCMD["Modules"].keys()
		if reponseCMD["Modules"][cle] == template["NAME"] && !tasmota.cmd("Module", boolMute)["Module"].find("0", false)
			log(string.format("CONTROLE_GLOBAL: Active le module %s: %s !", cle, reponseCMD["Modules"][cle]), LOG_LEVEL_DEBUG)
			tasmota.cmd("Module " + str(cle), boolMute)
		end
	end

    return enregistrePersistant
end

# Retourne le module lors de l'importation
return configGlobal