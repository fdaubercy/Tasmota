# Définition du module
var configGlobal = module("/configGlobal")

# Fonction chargé de tester un paramètre enregistré avec celui présent en json
# paramTasmota: Commande envoyé à tasmota pour récupérer la donnée : ex=SetOption56
# paramJson: la donnée json sélectionnée: ex=data["selectSignalFort"]
# typeData: type de donnée à comparer: ex=real / int / str
# @Retourne true=changement du paramètre
configGlobal.testeParam = def(paramTasmota, paramJson, typeData)
	import string

	var resultat = false

	# type par défaut
	typeData = (typeData == "" ? "str" : typeData)
	
	if paramJson != ""
		if (typeData == "str")
			resultat = str(tasmota.cmd(paramTasmota, boolMute)[paramTasmota]) != str(paramJson)
		elif (typeData == "int")
			resultat = int(tasmota.cmd(paramTasmota, boolMute)[paramTasmota]) != int(paramJson)
		elif (typeData == "real")
			resultat = real(tasmota.cmd(paramTasmota, boolMute)[paramTasmota]) != real(paramJson)
		end

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
configGlobal.configGlobalByJson = def(json)
	import string
    import globalFonctions

	var reponseCMD
	var id = 0
	var pos = 0
	var enregistrePersistant = false
	var data
	var modules
	var typeApp
	var pin = 0

	var componentesInverse = {}

	var template = json["template"]
		template["NAME"] = json["template"]["NAME"]
	var gpioPinUtilises = []

	var ordreGPIO = []
	if (json["diverses"].find("typeESP", "ESP32") == "ESP32")
		ordreGPIO = ["GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO9", "GPIO10", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO19", "GPIO20", "GPIO21", "GPIO22", "GPIO23", "GPIO24", "GPIO25", "GPIO26", "GPIO27", "GPIO6", "GPIO7", "GPIO8", "GPIO11", "GPIO32", "GPIO33", "GPIO34", "GPIO35", "GPIO36", "GPIO37", "GPIO38", "GPIO39"]	
	elif (json["diverses"].find("typeESP", "ESP32") == "ESP32S3")
    	ordreGPIO = ["GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO19", "GPIO20", "GPIO21", "GPIO33", "GPIO34", "GPIO35", "GPIO36", "GPIO37", "GPIO38", "GPIO39", "GPIO40", "GPIO41", "GPIO42", "GPIO43", "GPIO44", "GPIO45", "GPIO46", "GPIO47", "GPIO48"]	
	end

	# Exemples de commandes :
	# template -> resultat = {"NAME":"ESP32 Relay x8","GPIO":[0,0,161,0,32,0,0,0,230,231,229,162,0,0,0,0,0,0,0,0,0,226,227,228,0,0,0,0,224,225,0,0,0,0,0,0],"FLAG":0,"BASE":1}
	# gpio -> renvoie une liste des parametres GPIO -> resultat partiel = {"GPIO0":{"0":"Aucun"},"GPIO1":{"0":"Aucun"}}
	# gpios -> renvoie une liste des numeros représentant le type de GPIO -> resultat partiel = {"GPIOs1":{"0":"Aucun","6208":"Option A","8448":"Option E","32":"Bouton"}}
	# module -> renvoie le nom du module activé -> resultat = {"Module":{"1":"ESP32-DevKit"}}
	# modules -> renvoie les modèles enregistrés -> resultat = {"Modules":{"0":"ESP32 Relay x8","1":"ESP32-DevKit"}}
	
	data = json["serveur"]["wifi"]
	# Recherche du signal le plus fort
	if configGlobal.testeParam("SetOption56", data["selectSignalFort"], "")
		log (string.format("CONTROLE_GENERAL: %s la recherche du signal wifi le plus fort !", (data["selectSignalFort"] == "ON" ? "Active" : "Désactive")), LOG_LEVEL_DEBUG)
	end

	# Règle la puissance du wifi et le mot de passe
	if tasmota.cmd("SSId1", boolMute)["SSId1"] != data["reseau1"]["nomReseauWifi"]
		if data["power"] != 0 && data["reseau1"]["nomReseauWifi"] != "" && data["reseau1"]["mdpWifi"] != ""
			log (string.format("CONTROLE_GENERAL: Regle la puissance du wifi et le mot de passe pour le reseau %s!", data["reseau1"]["nomReseauWifi"]), LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog WifiPower %i; SSId1 %s; Password1 %s;", 
													data["power"], data["reseau1"]["nomReseauWifi"], 
													data["reseau1"]["mdpWifi"]), boolMute)
		end
	end
	if data["power"] != 0 && configGlobal.testeParam("SSId2", data["reseau2"]["nomReseauWifi"], "") && data["reseau2"]["mdpWifi"] != ""
		log (string.format("CONTROLE_GENERAL: Regle la puissance du wifi et le mot de passe pour le reseau %s!", data["reseau2"]["nomReseauWifi"]), LOG_LEVEL_DEBUG)
	end

	# Règle le nom du serveur
	data = json["serveur"]["nom"]
	if configGlobal.testeParam("DeviceName", data, "")
		log ("CONTROLE_GENERAL: Regle le nom du serveur !", LOG_LEVEL_DEBUG)		
	end
	
	# Règle le hostname
	data = json["serveur"]["hostname"]
	if configGlobal.testeParam("Hostname", data, "")
		log ("CONTROLE_GENERAL: Regle le hostname !", LOG_LEVEL_DEBUG)
	end

	# Paramétrage le mDNS
	data = json["serveur"]["mDNS"]
	if configGlobal.testeParam("SetOption55", data, "")
		log (string.format("CONTROLE_GENERAL: %s le mDNS !", (data == "ON" ? "Active" : "Désactive")), LOG_LEVEL_DEBUG)
	end

	# Règle les adresse IP / Masque de sous-reseau / Gateway / DNS Server
	data = json["serveur"]["IP"]
	if string.find(tasmota.cmd("IPAddress1", boolMute)["IPAddress1"], data["IPAddress"]) == -1 && data["IPAddress"] != ""
		log ("CONTROLE_GENERAL: Regle l'adresse IP du module !", LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("IPAddress1 %s", data["IPAddress"]), boolMute)
	end
	if configGlobal.testeParam("IPAddress2", data["IPGateway"], "str")
		log ("CONTROLE_GENERAL: Regle l'adresse IP de la passerelle !", LOG_LEVEL_DEBUG)
	end
	if configGlobal.testeParam("IPAddress3", data["Subnet"], "str")
		log ("CONTROLE_GENERAL: Regle le masque de sous-réseau !", LOG_LEVEL_DEBUG)
	end
	if data["DNSServer"] != "0.0.0.0"
		if configGlobal.testeParam("IPAddress4", data["DNSServer"], "str")
			log ("CONTROLE_GENERAL: Regle l'adresse IP du serveur DNS !", LOG_LEVEL_DEBUG)
		end
	end

	# Règle le CORS (Cross Origin Resource Sharing)
	# Pouvoir faire des requetes XmlHttpRequest sur un autre domaine

	# Règle les paramètres MQTT
	data = json["serveur"]["mqtt"]
	if data["activation"] == "ON"
		# Hote & Port & Client
		if configGlobal.testeParam("MqttHost", data["hote"], "") || configGlobal.testeParam("MqttPort", data["port"], "") && configGlobal.testeParam("MqttClient", data["client"], "")
			log ("CONTROLE_GENERAL: Regle l'IP, le port MQTT et le client !", LOG_LEVEL_DEBUG)
		end
			
		# Utilisateur & Mot de passe & Topic
		if configGlobal.testeParam("MqttUser", data["utilisateur"], "str") || configGlobal.testeParam("Topic", data["topic"], "str")
			log ("CONTROLE_GENERAL: Regle l'utilisateur, le mot de passe et le topic pour MQTT !", LOG_LEVEL_DEBUG)
		end

		# Gère les abonnements aux topics de groupe
		var cmd = tasmota.cmd("groupTopic", boolMute)
		for nb: 1 .. 3
			if str(cmd[string.format("GroupTopic%i", nb)]) != str(data[string.format("groupTopic%i", nb)])
				tasmota.cmd("GroupTopic1" + str(data["groupTopic1"]))
				tasmota.cmd(string.format("GroupTopic%i %s", nb, str(data["groupTopic1"])), boolMute)
			end
		end
	end

    # Réglage des paramètres diverses
	# Règle la localisation & le fuseau horaire
	data = json["diverses"]["localisation"]
	if configGlobal.testeParam("Latitude", data["latitude"], "real") || configGlobal.testeParam("Longitude", data["longitude"], "real")
		log ("CONTROLE_GENERAL: Regle la localisation !", LOG_LEVEL_DEBUG)
	end
	
	data = json["diverses"]["fuseauHoraire"]	
	if configGlobal.testeParam("Timezone", data["timezone"], "int") || string.find(str(data["TimeStd"]), str(tasmota.cmd("TimeStd", boolMute)["TimeStd"])) == -1 || string.find(str(data["TimeDst"]), str(tasmota.cmd("TimeDst", boolMute)["TimeDst"])) == -1
		if data["timezone"] != 0 && data["TimeStd"] != "" && data["TimeDst"] != ""
			log ("CONTROLE_GENERAL: Regle le fuseau horaire !", LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog Timezone %i; TimeStd %s; TimeDst %s", 
													data["timezone"], data["TimeStd"], 
													data["TimeDst"]), boolMute)		
		end
	end

    data = json["diverses"]

	# Réglage de la telePeriod
	if configGlobal.testeParam("TelePeriod", data.find("telePeriod", 300), "int")
		var periode = data.find("telePeriod", 300)

		log (string.format("CONTROLE_GENERAL: Règle la telePeriod à %is !", periode), LOG_LEVEL_DEBUG)
	end

	# Evite un reset sur appui long sur un bouton
	if configGlobal.testeParam("SetOption1", data["eviteResetBTN"], "")
		log ("CONTROLE_GENERAL: Evite un reset sur appui long sur un bouton !", LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("SetOption1 %s", data["eviteResetBTN"]), boolMute)
	end

	# Paramètre le niveau des logs
	logSerial = data["logs"]
	logWeb = data["logs"]

	if !tasmota.cmd("SerialLog", boolMute)["SerialLog"].find(str(logSerial), false) || tasmota.cmd("WebLog", boolMute)["WebLog"] != logWeb
		log ("CONTROLE_GENERAL: Regle le niveau des logs !", LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("Backlog SerialLog %i; WebLog %i;", logSerial, logWeb), boolMute)
	end

    # Récupère le template (modele)
    enregistrePersistant = globalFonctions.recupereTemplate(json, ordreGPIO, template, componentesInverse)

	# Paramètre les relais/Switchs/Boutons/LED/CarteSD dans le modele et sur interface web en fonction des persist.json	
    # Pour les éléments non-spécifiques à certains modules
	modules = json["modules"]
	if modules["activation"] == "ON"
		for cleModule: modules.keys()
			if type(modules[cleModule]) != "instance"	continue	end	
			
			# Si le module est activé
			if modules[cleModule]["activation"] == "ON"				# ex: ["modules"]["cuve"]["activation"]
				# Parcours les capteurs génériques des modules, dans le modele et sur interface web en fonction des persist.json :
				# 	- Paramètre les relais 
				# 	- Paramètre les capteurs ou interrupteurs (Switch)
				# 	- Paramètre lees boutons (Button)
				# 	- Paramètre les Capteurs Hygro/Thermo DHT22
				# 	- Paramètre le pin, le type & le numero des LED et LEDLink
				# Parcours les capteurs spécifques des modules

				# Active ou non la LED de status et définie son niveau
				if cleModule == "leds"
					var ledPower = modules[cleModule].find("ledPower", "OFF")

					if tasmota.cmd("LedPower", boolMute)["LedPower1"] != ledPower
						log (string.format("CONTROLE_GENERAL: %s ledPower !", (ledPower=="ON" ? "Active" : "Desactive")), LOG_LEVEL_DEBUG)
						tasmota.cmd(string.format("Backlog LedPower %i; SetOption31 %s;", (ledPower=="ON" ? 1 : 0), (ledPower=="ON" ? "OFF" : "ON")), boolMute)
					end	
					if modules[cleModule].find("ledState", 0) != 8
						tasmota.cmd(string.format("LedState %i", modules[cleModule]["ledState"]), boolMute)
					end
				end

				var env = modules[cleModule]["environnement"]			# ex: env = ["modules"]["cuve"]["activation"]["environnement"]
				for cleDevices: env.keys()								# ex: cleDevices = ["modules"]["cuve"]["activation"]["environnement"]["ADS1115"]
					if type(env[cleDevices]) != "instance"	
						continue
					end	

					# Compte le nombre de devices dans chaque piece de l'environnement
					var j = 0
					for cleDev: env[cleDevices].keys()
						if type(env[cleDevices][cleDev]) != "instance"		# ex: cleDev = ["modules"]["cuve"]["activation"]["environnement"]["ADS1115"]["activation"]
							continue
						end	
						j += 1
					end

					if env[cleDevices].find("activation", "ON") == "OFF"
						# On stoppe la boucle et passe aux devices d'environnement suivantes
						break
					else log (string.format("CONFIG_GLOBAL: Parametre les %i %s du module %s !", j, cleDevices, cleModule), LOG_LEVEL_DEBUG)
					end
					
					for cleDev: env[cleDevices].keys()
						if (type(env[cleDevices][cleDev]) != "instance")	# ex: cleDev = ["modules"]["cuve"]["activation"]["environnement"]["ADS1115"]["activation"]	
							continue	
						end	

						typeApp = ""
						# ex: cleDev = ["modules"]["cuve"]["activation"]["environnement"]["ADS1115"]["Ana1"]	
						#if env[cleDevices][cleDev].find("activation", "OFF") == "ON" && ((env[cleDevices][cleDev].find("pin", -1) != -1  && env[cleDevices][cleDev].find("virtuel", "OFF") == "OFF"))
						if env[cleDevices][cleDev].find("activation", "OFF") == "ON" && ((env[cleDevices][cleDev].find("pin", -1) != -1  && env[cleDevices][cleDev].find("virtuel", "OFF") == "OFF") || env[cleDevices][cleDev].find("virtuel", "OFF") == "ON")
							# Uniquement si pin != -1 & type != ""
							#id = int(env[cleDevices][cleDev]["type"] & 0x1F) + 1
							#typeApp = int((env[cleDevices][cleDev]["type"] >> 5) & 0xFFE0) + id - 1

							id = int(env[cleDevices][cleDev].find("id", 1))
							pin = env[cleDevices][cleDev]["pin"]

							typeApp = int(env[cleDevices][cleDev]["type"]) + id - 1
							# Pour les WS2812
							if cleDevices == "ws2812s"
								typeApp = int(env[cleDevices][cleDev]["type"]) + int(env[cleDevices][cleDev]["channel"]) - 1
							else typeApp = int(env[cleDevices][cleDev]["type"]) + id - 1
							end

							if pin != -1 && typeApp != ""	
								# Ajoute au tableau des pins utilisés
								gpioPinUtilises.push("GPIO" + str(pin))	
								
								# Repérer la place du GPIO dans le modèle
								# log ("ordreGPIO.size()=" + str(ordreGPIO.size()), LOG_LEVEL_DEBUG_PLUS)
								for i: 0 .. ordreGPIO.size() - 1
									if ordreGPIO[i] == "GPIO" + str(pin)
										pos = i
										break
									end
								end				
								
								if template["GPIO"][pos] != typeApp
									template["GPIO"][pos] = typeApp
									log (string.format("CONFIG_GLOBAL: Modifie en json le type de %s = %i !", cleDev, int(typeApp) + id - 1), LOG_LEVEL_DEBUG)
									
									enregistrePersistant = true
								end		
							end

							# Paramètre le nom des relais et WS2812
							if cleDevices == "relais" || cleDevices == "ws2812s"
								if env[cleDevices][cleDev]["nom"] != ""
									if tasmota.cmd("WebButton" + str(id), boolMute)["WebButton" + str(id)] != env[cleDevices][cleDev]["nom"]
										log (string.format("CONFIG_GLOBAL: Modifie sur WebUI le nom du Relai %i = %s !", id, env[cleDevices][cleDev]["nom"]), LOG_LEVEL_DEBUG)
										tasmota.cmd("WebButton" + str(id) + " " + env[cleDevices][cleDev]["nom"], boolMute)
									end
								end
							# Paramètre le mode de l'interrupteur ou capteur : SwitchMode
							elif (cleDevices == "capteurs" || cleDevices == "interrupteurs")
								reponseCMD = tasmota.cmd(string.format("SwitchMode%i", id), boolMute)[string.format("SwitchMode%i", id)]
								if int(reponseCMD) != env[cleDevices][cleDev]["SwitchMode"]
									# Quand le circuit est fermé, Tasmota enverra ON
									log(string.format("CONFIG_GLOBAL: Parametrage du mode du capteur ou interrupteur %i = SwitchMode %i!", id, env[cleDevices][cleDev]["SwitchMode"]), LOG_LEVEL_DEBUG)
									tasmota.cmd(string.format("Backlog SwitchMode%i %i;", id, env[cleDevices][cleDev]["SwitchMode"]), boolMute)
								end	
							# Paramètre le mode du bouton : SwitchMode
							elif cleDevices == "boutons"
								reponseCMD = tasmota.cmd(string.format("SwitchMode%i", id), boolMute)[string.format("SwitchMode%i", id)]
								if reponseCMD != env[cleDevices][cleDev]["SwitchMode"]
									# Quand le circuit est fermé, Tasmota enverra OFF
									log(string.format("CONFIG_GLOBAL: Parametrage du mode du bouton %i = SwitchMode %i!", id, env[cleDevices][cleDev]["SwitchMode"]), LOG_LEVEL_DEBUG)
									tasmota.cmd(string.format("Backlog SwitchMode%i %i;", id, env[cleDevices][cleDev]["SwitchMode"]), boolMute)
								end	
							end
						end
					end
				end
	 		end
		end
	end	

	# Efface le paramétrage des GPIOs inutilisés dans le modèle
	log ("CONTROLE_GLOBAL: gpioPinUtilises=" + str(gpioPinUtilises), LOG_LEVEL_DEBUG_PLUS)

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
			if template["GPIO"][gpioTemp] != 1 #&& template["GPIO"][gpioTemp] != 0
				# enregistrePersistant = true
				log("CONTROLE_GLOBAL: " + str(ordreGPIO[gpioTemp]) + " inutilise -> il sera reinitialise de " + str(template["GPIO"][gpioTemp]) + " a 1 !", LOG_LEVEL_DEBUG_PLUS)
				template["GPIO"][gpioTemp] = 1
			end
		end
	end

	template["NAME"] = json["template"]["NAME"]
	json["template"] = template
	log ("CONTROLE_GLOBAL: template=" + str(template), LOG_LEVEL_DEBUG_PLUS)
	
	# Enregistre le pin du modèle dans persist.json
	if enregistrePersistant
		log ("CONTROLE_GLOBAL: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)
	
		persist.parametres = json	
		persist.save() 
	end
	
	# Paramètre le nouveau modèle
	reponseCMD = tasmota.cmd("Template", boolMute)
	if reponseCMD["BASE"] != template["BASE"] || reponseCMD["NAME"] != template["NAME"] || reponseCMD["GPIO"] != template["GPIO"] || reponseCMD["FLAG"] != template["FLAG"]
		log ("CONTROLE_GLOBAL: Parametre le nouveau modele !", LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("Template {\"BASE\": %i, \"GPIO\": %s, \"NAME\": \"%s\", \"FLAG\": %i}", template["BASE"], str(template["GPIO"]), template["NAME"], template["FLAG"]), boolMute)

		# Récupère le type de modeles (template) paramétrés
		reponseCMD = tasmota.cmd("Modules", boolMute)
		for cle: reponseCMD["Modules"].keys()
			if reponseCMD["Modules"][cle] == template["NAME"]
				log ("CONTROLE_GLOBAL: Parametre le type de module active !", LOG_LEVEL_DEBUG)
				tasmota.cmd("Module " + str(cle), boolMute)
			end
		end
	end
end

# Retourne le module lors de l'importation
return configGlobal