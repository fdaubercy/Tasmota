import string

# Fonctions générales
# Remplace toutes les occurences d'un mot dans une phrase
def replaceString(phrase, mot, mot2)
	var boutPhrase = []
	var phraseFinale = ""
	
	boutPhrase = string.split(phrase, mot) 
	
	for nb:0 .. string.count(phrase, mot)
		if nb != string.count(phrase, mot) 
			phraseFinale += boutPhrase[nb] + mot2
		else phraseFinale += boutPhrase[nb]
		end
	end
	
	return phraseFinale
end

# Fonction qui fractionne un json
# Retourne un tableau contenant les différentes parties du json
def fractionneJson(jsonATraiter, nbDivisions)
	var tmpComponentes = {}
	var returnComponentes = {}
	var nbCles = jsonATraiter.size()
	var nbClesParTmp = nbCles / nbDivisions
	var txt = ""
	var template = "<option value='%s'>%s</option>"
	var iterations = 1
	var idTmp = 0
	
	# Crée la structure du <select> avec les componenetes possibles pour tasmota
	for cle: jsonATraiter.keys()
		# txt += string.format(template, cle, jsonATraiter[cle])
		tmpComponentes.insert(cle, jsonATraiter[cle])
		
		if iterations > nbClesParTmp
			returnComponentes.insert(idTmp, tmpComponentes)
			# tmpComponentes.insert(str(idTmp), txt)
			# tmpComponentes.push(txt)
			
			iterations = 1
			idTmp += 1
			txt = ""
		end
		
		iterations += 1
	end
	
	return returnComponentes
end

# Paramétrage par tasmota.cmd à partir des paramètres enregistrés en json
def configByJson(json)
	var reponseCMD
	var id = 0
	var pos = 0
	var enregistrePersistant = false
	var data
	var modules
	var typeApp
	var pin = 0
	
	
	var componentes = json["modele"]["componentes"]
	var componentesInverse = {}

	var template = json["modele"]["template"]
		template["NAME"] = json["modele"]["template"]["NAME"]
	var gpioPinUtilises = []

	# Exemples de commandes :
	# template -> resultat = {"NAME":"ESP32 Relay x8","GPIO":[0,0,161,0,32,0,0,0,230,231,229,162,0,0,0,0,0,0,0,0,0,226,227,228,0,0,0,0,224,225,0,0,0,0,0,0],"FLAG":0,"BASE":1}
	# gpio -> renvoie une liste des parametres GPIO -> resultat partiel = {"GPIO0":{"0":"Aucun"},"GPIO1":{"0":"Aucun"}}
	# gpios -> renvoie une liste des numeros représentant le type de GPIO -> resultat partiel = {"GPIOs1":{"0":"Aucun","6208":"Option A","8448":"Option E","32":"Bouton"}}
	# module -> renvoie le nom du module activé -> resultat = {"Module":{"1":"ESP32-DevKit"}}
	# modules -> renvoie les modèles enregistrés -> resultat = {"Modules":{"0":"ESP32 Relay x8","1":"ESP32-DevKit"}}
	
	data = json["serveur"]["wifi"]
	# Recherche du signal le plus fort
	if tasmota.cmd("SetOption56", boolMute)["SetOption56"] != data["selectSignalFort"]
		log (string.format("CONTROLE_GENERAL: %s la recherche du signalwifi le plus fort !", (data["selectSignalFort"] == "ON" ? "Active" : "Désactive")), LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("SetOption56 %s", data["selectSignalFort"]), boolMute)
	end
	
	# Paramétrage le scan de réseaux wifi toutes les 44 min
	if tasmota.cmd("SetOption57", boolMute)["SetOption57"] != data["reScanBy44"]
		log (string.format("CONTROLE_GENERAL: %s le sacn des réseaux wifi / 44 min !", (data["reScanBy44"] == "ON" ? "Active" : "Désactive")), LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("SetOption57 %s", data["reScanBy44"]), boolMute)
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
	
	if tasmota.cmd("SSId2", boolMute)["SSId2"] != data["reseau2"]["nomReseauWifi"]
		if data["power"] != 0 && data["reseau2"]["nomReseauWifi"] != "" && data["reseau2"]["mdpWifi"] != ""
			log (string.format("CONTROLE_GENERAL: Regle la puissance du wifi et le mot de passe pour le reseau %s!", data["reseau2"]["nomReseauWifi"]), LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog WifiPower %i; SSId2 %s; Password2 %s;", 
													data["power"], data["reseau2"]["nomReseauWifi"], 
													data["reseau2"]["mdpWifi"]), boolMute)
		end
	end

	# Règle la localisation & le fuseau horaire
	data = json["serveur"]["localisation"]
	if real(tasmota.cmd("Latitude", boolMute)["Latitude"]) != real(data["latitude"]) || real(tasmota.cmd("Longitude", boolMute)["Longitude"]) != real(data["longitude"])
		if data["latitude"] != "" && data["longitude"] != ""
			log ("CONTROLE_GENERAL: Regle la localisation !", LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog Latitude %s; Longitude %s;", data["latitude"], data["longitude"]), boolMute)		
		end
	end
	
	data = json["serveur"]["fuseauHoraire"]		
	if int(tasmota.cmd("Timezone", boolMute)["Timezone"]) != int(data["timezone"]) || string.find(str(data["TimeStd"]), str(tasmota.cmd("TimeStd", boolMute)["TimeStd"])) == -1 || string.find(str(data["TimeDst"]), str(tasmota.cmd("TimeDst", boolMute)["TimeDst"])) == -1
		if data["timezone"] != 0 && data["TimeStd"] != "" && data["TimeDst"] != ""
			log ("CONTROLE_GENERAL: Regle le fuseau horaire !", LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog Timezone %i; TimeStd %s; TimeDst %s", 
													data["timezone"], data["TimeStd"], 
													data["TimeDst"]), boolMute)		
		end
	end
	
	# Règle le nom du serveur
	data = json["serveur"]["nom"]
	if tasmota.cmd("DeviceName", boolMute)["DeviceName"] != data
		if data != ""
			log ("CONTROLE_GENERAL: Regle le nom du serveur !", LOG_LEVEL_DEBUG)
			
			tasmota.cmd(string.format("DeviceName %s", data), boolMute)
		end			
	end
	
	# Règle le hostname
	data = json["serveur"]["hostname"]
	if tasmota.cmd("Hostname", boolMute)["Hostname"] != data
		if data != ""
			log ("CONTROLE_GENERAL: Regle le hostname !", LOG_LEVEL_DEBUG)
			
			tasmota.cmd(string.format("Hostname %s", data), boolMute)
		end		
	end

	# Paramétrage le mDNS
	data = json["serveur"]["mDNS"]
	if tasmota.cmd("SetOption55", boolMute)["SetOption55"] != data
		log (string.format("CONTROLE_GENERAL: %s le mDNS !", (data == "ON" ? "Active" : "Désactive")), LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("SetOption55 %s", data), boolMute)
	end
	
	# Règle les adresse IP / Masque de sous-reseau / Gateway / DNS Server
	data = json["serveur"]["IP"]
	if string.find(tasmota.cmd("IPAddress1", boolMute)["IPAddress1"], data["IPAddress"]) == -1
		if data["IPAddress"] != ""
			log ("CONTROLE_GENERAL: Regle l'adresse IP du module !", LOG_LEVEL_DEBUG)
			
			tasmota.cmd(string.format("IPAddress1 %s", data["IPAddress"]), boolMute)
		end
	end
	if str(tasmota.cmd("IPAddress2", boolMute)["IPAddress2"]) != str(data["IPGateway"])
		if data["IPGateway"] != ""
			log ("CONTROLE_GENERAL: Regle l'adresse IP de la passerelle !", LOG_LEVEL_DEBUG)
			
			tasmota.cmd(string.format("IPAddress2 %s", data["IPGateway"]), boolMute)
		end
	end
	if str(tasmota.cmd("IPAddress3", boolMute)["IPAddress3"]) != str(data["Subnet"])
		if data["Subnet"] != ""
			log ("CONTROLE_GENERAL: Regle le masque de sous-réseau !", LOG_LEVEL_DEBUG)
			
			tasmota.cmd(string.format("IPAddress3 %s", data["Subnet"]), boolMute)
		end
	end
	if str(tasmota.cmd("IPAddress4", boolMute)["IPAddress4"]) != str(data["DNSServer"])
		if data["DNSServer"] != ""
			log ("CONTROLE_GENERAL: Regle l'adresse IP du serveur DNS !", LOG_LEVEL_DEBUG)
			
			tasmota.cmd(string.format("IPAddress4 %s", data["DNSServer"]), boolMute)
		end
	end

	# Règle les paramètres MQTT
	data = json["serveur"]["mqtt"]
	if data["activation"] == "ON"
		## Hote & Port & Client
		if str(tasmota.cmd("MqttHost", boolMute)["MqttHost"]) != str(data["hote"]) || tasmota.cmd("MqttPort", boolMute)["MqttPort"] != data["port"] && str(tasmota.cmd("MqttClient", boolMute)["MqttClient"]) != str(data["client"])
			log ("CONTROLE_GENERAL: Regle l'IP, le port MQTT et le client !", LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog MqttHost %s; MqttPort %i; MqttClient %s", 
											data["hote"], data["port"], data["client"]), boolMute)
		end
			
		## Utilisateur & Mot de passe & Topic
		if str(tasmota.cmd("MqttUser", boolMute)["MqttUser"]) != str(data["utilisateur"]) || str(tasmota.cmd("Topic", boolMute)["Topic"]) != str(data["topic"])
			log ("CONTROLE_GENERAL: Regle l'utilisateur, le mot de passe et le topic pour MQTT !", LOG_LEVEL_DEBUG)
			tasmota.cmd(string.format("Backlog MqttUser %s; MqttPassword %s; Topic %s", 
											data["utilisateur"], data["mdp"], data["topic"]), boolMute)
		end
	end
	
	# # Règle le CORS (Cross Origin Resource Sharing)
	# # Pouvoir faire des requetes XmlHttpRequest sur un autre domaine

	# Récupère le template (modele)
	var ordreGPIO = ["GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO9", "GPIO10", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO19", "GPIO20", "GPIO21", "GPIO22", "GPIO23", "GPIO24", "GPIO25", "GPIO26", "GPIO27", "GPIO6", "GPIO7", "GPIO8", "GPIO11", "GPIO32", "GPIO33", "GPIO34", "GPIO35", "GPIO36", "GPIO37", "GPIO38", "GPIO39"]	
	if str(tasmota.cmd("Template", boolMute)) != str(template)
		log ("CONTROLE_GENERAL: Recupere le template du modele !", LOG_LEVEL_DEBUG)
		
		template = tasmota.cmd("Template", boolMute)
		enregistrePersistant = true
	end
	
	# Récupère les componentes existants du modele 
	reponseCMD = tasmota.cmd("GPIOs", boolMute)
	for cle: reponseCMD.keys()
		if componentes.size() == 0
			log ("CONTROLE_GENERAL: Enregistre les componentes en json !", LOG_LEVEL_DEBUG)
			json["modele"]["componentes"] = reponseCMD[cle]	

			enregistrePersistant = true
		end
	end	
	
	# Prépare l'inversion des 'componentes'
	for cle: componentes.keys()
		componentesInverse.insert(componentes[cle], cle)
	end
	
	# Enregistre le pin du modèle dans persist.json
	if enregistrePersistant
		log ("CONTROLE_GLOBAL: Enregistre Template et Componentes en json !", LOG_LEVEL_DEBUG)

		persist.parametres = json	
		persist.save() 
	end
	enregistrePersistant = false
	
	# Réglage des paramètres du serveur
	data = json["diverses"]
	# Evite un reset sur appui long sur un bouton
	if tasmota.cmd("SetOption1", boolMute)["SetOption1"] != data["eviteResetBTN"]
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

	# Paramètre le pin, le type & le numero des LED et LEDLink en fonction des persist.json
	log ("CONTROLE_GENERAL: Parametre les LED !", LOG_LEVEL_DEBUG)
	var leds = json["diverses"]["leds"]

	# On parcours les leds du serveur
	for cleLED: leds.keys()
		typeApp = ""
		
		# Si les leds sont activées
		if leds[cleLED]["activation"] == "ON"	
			# Uniquement si pin != -1 & type != ""
			id = int(leds[cleLED]["type"] & 0x1F) + 1
			typeApp = int((leds[cleLED]["type"] & 0xFFE0) >> 5) + id - 1
			pin = leds[cleLED]["pin"]
						
			if pin != -1 && typeApp != ""	
				# Ajoute au tableau des pins utilisés
				gpioPinUtilises.push("GPIO" + str(pin))
				
				# Repérer la place du GPIO dans le modèle
				log ("ordreGPIO.size()=" + str(ordreGPIO.size()), LOG_LEVEL_DEBUG_PLUS)
				for i: 0 .. ordreGPIO.size() - 1
					if ordreGPIO[i] == "GPIO" + str(pin)
						pos = i
						break
					end
				end				
				
				if template["GPIO"][pos] != typeApp
					template["GPIO"][pos] = typeApp
					log (string.format("CONTROLE_GLOBAL: Modifie en json le type de la LED %i = %i !", id, typeApp), LOG_LEVEL_DEBUG)
					
					enregistrePersistant = true
				end		
			end
		end
	end
	
	# Paramètre les relais/Switchs/Boutons/LED dans le modele et sur interface web en fonction des persist.json	
	modules = json["modules"]
	# # controleGeneral.nbRelaisActives = 0
	
	if modules["activation"] == "ON"
		for cleModule: modules.keys()
			if type(modules[cleModule]) != "instance"
				continue
			end		
			
			# Si le module est activé
			if modules[cleModule]["activation"] == "ON"
				# On parcours les relais du module
				# Paramètre les relais dans le modele et sur interface web en fonction des persist.json	
				var relais = modules[cleModule]["environnement"].find("relais", false)		
				if relais
					log (string.format("CONTROLE_GENERAL: Parametre les Relais du module %s !", cleModule), LOG_LEVEL_DEBUG)
					log (string.format("CONTROLE_GLOBAL: Il y a %i relais a parametrer !", modules[cleModule]["environnement"]["relais"].size()), LOG_LEVEL_DEBUG)
					
					for cleRelai: relais.keys()
						typeApp = ""
						
						if relais[cleRelai]["activation"] == "ON"
							# Uniquement si pin != -1 & type != ""
							id = int(relais[cleRelai]["type"] & 0x1F) + 1
							typeApp = int((relais[cleRelai]["type"] & 0xFFE0) >> 5) + id - 1
							pin = relais[cleRelai]["pin"]
							
							if pin != -1 && typeApp != ""	
								# Ajoute au tableau des pins utilisés
								gpioPinUtilises.push("GPIO" + str(pin))	
								
								# Repérer la place du GPIO dans le modèle
								log ("ordreGPIO.size()=" + str(ordreGPIO.size()), LOG_LEVEL_DEBUG_PLUS)
								for i: 0 .. ordreGPIO.size() - 1
									if ordreGPIO[i] == "GPIO" + str(pin)
										pos = i
										break
									end
								end				
								
								if template["GPIO"][pos] != typeApp
									template["GPIO"][pos] = typeApp
									log (string.format("CONTROLE_GLOBAL: Modifie en json le type du Relai %i = %i !", id, int(typeApp) + id - 1), LOG_LEVEL_DEBUG)
									
									enregistrePersistant = true
								end		
							end
							
							# Paramètre le nom des relais
							if relais[cleRelai]["nom"] != ""
								if tasmota.cmd("WebButton" + str(id), boolMute)["WebButton" + str(id)] != relais[cleRelai]["nom"]
									log (string.format("CONTROLE_GLOBAL: Modifie sur WebUI le nom du Relai %i = %s !", id, relais[cleRelai]["nom"]), LOG_LEVEL_DEBUG)
									tasmota.cmd("WebButton" + str(id) + " " + relais[cleRelai]["nom"], boolMute)
								end
							end						
						end
					end
				end
				
				# Paramètre le pin, le type & le numero des capteurs ou interrupteurs (Switch) en fonction des persist.json
				var switchs = modules[cleModule]["environnement"].find("capteursPosition", false)
				if modules[cleModule]["environnement"].find("interrupteurs") != nil
					switchs.insert("interrupteurs", modules[cleModule]["environnement"]["interrupteurs"])
				end
				
				if switchs
					log (string.format("CONTROLE_GENERAL: Parametre les Interrupteurs & Capteurs (Switch) du module %s !", cleModule), LOG_LEVEL_DEBUG)
					log (string.format("CONTROLE_GLOBAL: Il y a %i capteurs a parametrer !", modules[cleModule]["environnement"]["capteursPosition"].size() + (modules[cleModule]["environnement"].find("interrupteurs") != nil ? modules[cleModule]["environnement"]["interrupteurs"].size() : 0)), LOG_LEVEL_DEBUG)
					
					for cleSwitch: switchs.keys()
						typeApp = ""
						
						if switchs[cleSwitch]["activation"] == "ON"
							# Uniquement si pin != -1 & type != ""
							id = int(switchs[cleSwitch]["type"] & 0x1F) + 1
							typeApp = int((switchs[cleSwitch]["type"] & 0xFFE0) >> 5) + id - 1
							pin = switchs[cleSwitch]["pin"]

							if pin != -1 && typeApp != ""	
								# Ajoute au tableau des pins utilisés
								gpioPinUtilises.push("GPIO" + str(pin))	
								
								# Repérer la place du GPIO dans le modèle
								log ("ordreGPIO.size()=" + str(ordreGPIO.size()), LOG_LEVEL_DEBUG_PLUS)
								for i: 0 .. ordreGPIO.size() - 1
									if ordreGPIO[i] == "GPIO" + str(pin)
										pos = i
										break
									end
								end												
							
								if template["GPIO"][pos] != typeApp
									template["GPIO"][pos] = typeApp
									log (string.format("CONTROLE_GLOBAL: Modifie en json le type du Switch %i = %i !", id, int(typeApp) + id - 1), LOG_LEVEL_DEBUG)
									
									enregistrePersistant = true
								end										

								# Paramètre le mode de l'interrupteur ou capteur : SwitchMode
								reponseCMD = tasmota.cmd(string.format("SwitchMode%i", id), boolMute)[string.format("SwitchMode%i", id)]
								if int(reponseCMD) != 1
									# Quand le circuit est fermé, Tasmota enverra ON
									log(string.format("CONTROLE_GLOBAL: Parametrage du mode du capteur ou interrupteur %i = SwitchMode 1!", id), LOG_LEVEL_DEBUG)
									tasmota.cmd(string.format("Backlog SwitchMode%i 1;", id), boolMute)
								end		
							end
						end
					end	
				end

				# Paramètre le pin, le type & le numero des boutons (Button) en fonction des persist.json
				var boutons = modules[cleModule]["environnement"].find("boutons", false)
				
				if boutons
					log (string.format("CONTROLE_GENERAL: Parametre les Boutons du module %s !", cleModule), LOG_LEVEL_DEBUG)
					log (string.format("CONTROLE_GLOBAL: Il y a %i boutons a parametrer !", modules[cleModule]["environnement"]["boutons"].size()), LOG_LEVEL_DEBUG)
					
					for cleBTN: boutons.keys()
						typeApp = ""
						
						if boutons[cleBTN]["activation"] == "ON"
							# Uniquement si pin != -1 & type != ""
							id = int(boutons[cleBTN]["type"] & 0x1F) + 1
							typeApp = int((boutons[cleBTN]["type"] & 0xFFE0) >> 5) + id - 1
							pin = boutons[cleBTN]["pin"]

							if pin != -1 && typeApp != ""	
								# Ajoute au tableau des pins utilisés
								gpioPinUtilises.push("GPIO" + str(pin))	
								
								# Repérer la place du GPIO dans le modèle
								log ("ordreGPIO.size()=" + str(ordreGPIO.size()), LOG_LEVEL_DEBUG_PLUS)
								for i: 0 .. ordreGPIO.size() - 1
									if ordreGPIO[i] == "GPIO" + str(pin)
										pos = i
										break
									end
								end												
							
								if template["GPIO"][pos] != typeApp
									template["GPIO"][pos] = typeApp
									log (string.format("CONTROLE_GLOBAL: Modifie en json le type du Bouton %i = %i !", id, int(typeApp) + id - 1), LOG_LEVEL_DEBUG)
									
									enregistrePersistant = true
								end	

								# Paramètre le mode du bouton : SwitchMode
								# reponseCMD = tasmota.cmd(string.format("SwitchMode%i", id), boolMute)[string.format("SwitchMode%i", id)]
								# if reponseCMD != 2
									# # Quand le circuit est fermé, Tasmota enverra OFF
									# log(string.format("CONTROLE_GLOBAL: Parametrage du mode du bouton %i = SwitchMode 2!", id), LOG_LEVEL_DEBUG)
									# tasmota.cmd(string.format("Backlog SwitchMode%i 2;", id), boolMute)
								# end		

								# Compte le nombre de boutons activés
								# controleGeneral.nbButtonsActives += 1							
							end
						end
					end	
				end
				
				# Paramètres les Capteurs Hygro/Thermo DHT22 dans le modele et sur interface web en fonction des persist.json	
				var thermo = modules[cleModule]["environnement"].find("thermometres", false)
				
				if thermo
					log (string.format("CONTROLE_GENERAL: Parametre capteurs Thermo/Hygro DHT22 du module %s !", cleModule), LOG_LEVEL_DEBUG)
					log (string.format("CONTROLE_GLOBAL: Il y a %i thermometres a parametrer !", modules[cleModule]["environnement"]["thermometres"].size()), LOG_LEVEL_DEBUG)
					
					for cleTH: thermo.keys()
						typeApp = ""
						
						if thermo[cleTH]["activation"] == "ON"					
							# Uniquement si pin != -1 & type != ""
							typeApp = thermo[cleTH]["type"]
							pin = thermo[cleTH]["pin"]		

							# Uniquement si pin != -1 & type != ""
							id = int(thermo[cleTH]["type"] & 0x1F) + 1
							typeApp = int((thermo[cleTH]["type"] & 0xFFE0) >> 5) + id - 1
							pin = thermo[cleTH]["pin"]							
					
							if pin != -1 && typeApp != ""	
								# Ajoute au tableau des pins utilisés
								gpioPinUtilises.push("GPIO" + str(pin))	

								# Repérer la place du GPIO dans le modèle
								log ("ordreGPIO.size()=" + str(ordreGPIO.size()), LOG_LEVEL_DEBUG_PLUS)
								for i: 0 .. ordreGPIO.size() - 1
									if ordreGPIO[i] == "GPIO" + str(pin)
										pos = i
										break
									end
								end							

								if template["GPIO"][pos] != typeApp
									template["GPIO"][pos] = typeApp
									log (string.format("CONTROLE_GLOBAL: Modifie en json le type Thermomètre = %i !", int(typeApp)), LOG_LEVEL_DEBUG)
									
									enregistrePersistant = true
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
			if template["GPIO"][gpioTemp] != 1
				# enregistrePersistant = true
				log("CONTROLE_GLOBAL: " + str(ordreGPIO[gpioTemp]) + " inutilise -> il sera reinitialise de " + str(template["GPIO"][gpioTemp]) + " a 1 !", LOG_LEVEL_DEBUG_PLUS)
				template["GPIO"][gpioTemp] = 1
			end
		end
	end
	
	template["NAME"] = json["modele"]["template"]["NAME"]
	json["modele"]["template"] = template
	log ("CONTROLE_GLOBAL: template=" + str(template), LOG_LEVEL_DEBUG_PLUS)
	
	# Enregistre le pin du modèle dans persist.json
	if enregistrePersistant
		log ("CONTROLE_GLOBAL: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)
	
		persist.parametres = json	
		persist.save() 
	end
	
	# Paramètre le nouveau modèle
	if str(tasmota.cmd("Template", boolMute)) != str(template)
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
	
	# Active ou non la LED de status et définie son niveau
	if tasmota.cmd("LedPower", boolMute)["LedPower1"] != data["ledPower"]
		log (string.format("CONTROLE_GENERAL: %s ledPower !", (data["ledPower"]=="ON" ? "Active" : "Desactive")), LOG_LEVEL_DEBUG)
		tasmota.cmd(string.format("Backlog LedPower %s; SetOption31 %s;", data["ledPower"], (data["ledPower"]=="ON" ? "OFF" : "ON")), boolMute)
	end	
	tasmota.cmd(string.format("LedState %i", data["ledState"]), boolMute)
end

def afficheDateTime(timestamp, sepHoraire, boolAfficheSec)
	var time_dump = tasmota.time_dump(timestamp)
	
	# Paramètres par défaut si absent
	if sepHoraire == "" sepHoraire = "-" end
	if boolAfficheSec == nil boolAfficheSec = false end
	
	var date = (time_dump["day"] < 10 ? "0" + str(time_dump["day"]) : str(time_dump["day"])) + "/" 
		date += (time_dump["month"] < 10 ? "0" + str(time_dump["month"]) : str(time_dump["month"])) + "/" 
		date += str(time_dump["year"]) + " "
		
	if sepHoraire == ":"
		date += (time_dump["hour"] < 10 ? "0" + str(time_dump["hour"]) : str(time_dump["hour"])) + ":" 
		date += (time_dump["min"] < 10 ? "0" + str(time_dump["min"]) : str(time_dump["min"])) + ":" 
		date += (time_dump["sec"] < 10 ? "0" + str(time_dump["sec"]) : str(time_dump["sec"]))
	else
		date += (time_dump["hour"] < 10 ? "0" + str(time_dump["hour"]) : str(time_dump["hour"])) + "h" 
		date += (time_dump["min"] < 10 ? "0" + str(time_dump["min"]) : str(time_dump["min"]))
		if boolAfficheSec
			date += "min" + (time_dump["sec"] < 10 ? "0" + str(time_dump["sec"]) : str(time_dump["sec"])) + "s" 
		end
	end
		
	return date
end
