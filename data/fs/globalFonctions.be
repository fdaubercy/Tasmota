# Définition du module
var globalFonctions = module("/globalFonctions")

# Règles sur changement d'état lors du démarrage de Tasmota
globalFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import persist
	import gestionFileFolder
	import introspect

	# Test
	log("GLOBAL_CHGT_ETAT_DEMARRAGE: -------------------- global changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	log("GLOBAL_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	log("GLOBAL_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	log("GLOBAL_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
			introspect.set(controleGeneral, "connected", true)

			# Règle les paramètres du serveur FTP
			if serveur.find("serveurFTP", false)
				if serveur["serveurFTP"]["activation"] == "ON"
					if (int(tasmota.cmd("UFSFTP", boolMute)["UfsFTP"]) == 0)	tasmota.cmd("UFSFTP 2", boolMute)	end
				else tasmota.cmd("UFSFTP 0", boolMute)
				end
			end
        elif msg["WIFI"].find("Disconnected", 0)
            introspect.set(controleGeneral, "connected", false)
        elif (msg.find("Wifi") == "OFF" || msg.find("Wifi") == "ON")
			introspect.set(controleGeneral, "connected", (msg["Wifi"] == "OFF" ? false : true))
            log("GLOBAL_CHGT_ETAT_DEMARRAGE: Wifi " + (msg["Wifi"] == "OFF" ? "désactivé" : "activé") + " !", LOG_LEVEL_DEBUG)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    # Save: Avant redemarrage de tasmota
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            introspect.set(controleGeneral, "booted", true)

			# Récupère son adresse MAC si inconnue en json
			if (!serveur.find("adressMAC", false))
				serveur.insert("adressMAC", tasmota.cmd("Status 5", boolMute)["StatusNET"]["Mac"])
				log("GLOBAL_CHGT_ETAT_DEMARRAGE: Récupère l'adresse MAC du module !", LOG_LEVEL_DEBUG)
			else
				if (serveur["adressMAC"] != tasmota.cmd("Status 5", boolMute)["StatusNET"]["Mac"])
					serveur["adressMAC"] = tasmota.cmd("Status 5", boolMute)["StatusNET"]["Mac"]
					log("CONTROLE_GENERAL: Modifie l'adresse MAC du module !", LOG_LEVEL_DEBUG)
				end
			end
		elif msg[trigger].find("Save", 0)
			try
				persist.serveur = serveur	
				persist.diverses = diverses
				persist.modules = modules
				persist.drivers = drivers
				persist.save() 
			except .. as error, message
				log(string.format("GLOBAL_CHGT_ETAT_DEMARRAGE_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
			end
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
			introspect.set(controleGeneral, "mqttConnected", true)
        elif msg["MQTT"].find("Disconnected", 0)
			introspect.set(controleGeneral, "mqttConnected", false)
        end
	# Se déclenche un évènement sur les heures et la synchronisation NTP (si activé)
    elif (trigger == "Time")
        # A chaque fois que le NTP est initialisé et l'heure synchronisée
        if type(msg["Time"]) == "instance"
            if msg["Time"].find("Initialized", 0)
				# A chaque heure, quand le système NTP est synchronisé
				introspect.set(controleGeneral, "flagTimestampInitialized", true)

				var TimeStd = tasmota.cmd("TimeStd", boolMute)["TimeStd"]
				if (TimeStd["Hemisphere"] != diverses["fuseauHoraire"]["TimeStd"]["Hemisphere"] || TimeStd["Week"] != diverses["fuseauHoraire"]["TimeStd"]["Week"] || TimeStd["Month"] != diverses["fuseauHoraire"]["TimeStd"]["Month"] ||
						TimeStd["Day"] != diverses["fuseauHoraire"]["TimeStd"]["Day"] || TimeStd["Hour"] != diverses["fuseauHoraire"]["TimeStd"]["Hour"] || TimeStd["Offset"] != diverses["fuseauHoraire"]["TimeStd"]["Offset"])
						log("GLOBAL_CHGT_ETAT_DEMARRAGE: Regle la date de passage à l'heure d'hiver !", LOG_LEVEL_DEBUG)
						tasmota.cmd(string.format("TimeStd %i,%i,%i,%i,%i,%i", 
																diverses["fuseauHoraire"]["TimeStd"]["Hemisphere"], diverses["fuseauHoraire"]["TimeStd"]["Week"], diverses["fuseauHoraire"]["TimeStd"]["Month"], 
																diverses["fuseauHoraire"]["TimeStd"]["Day"], diverses["fuseauHoraire"]["TimeStd"]["Hour"], diverses["fuseauHoraire"]["TimeStd"]["Offset"]), 
																boolMute)
				end

				var TimeDst = tasmota.cmd("TimeDst", boolMute)["TimeDst"]
				if (TimeDst["Hemisphere"] != diverses["fuseauHoraire"]["TimeDst"]["Hemisphere"] || TimeDst["Week"] != diverses["fuseauHoraire"]["TimeDst"]["Week"] || TimeDst["Month"] != diverses["fuseauHoraire"]["TimeDst"]["Month"] ||
						TimeDst["Day"] != diverses["fuseauHoraire"]["TimeDst"]["Day"] || TimeDst["Hour"] != diverses["fuseauHoraire"]["TimeDst"]["Hour"] || TimeDst["Offset"] != diverses["fuseauHoraire"]["TimeDst"]["Offset"])
						log("GLOBAL_CHGT_ETAT_DEMARRAGE: Regle la date de passage à l'heure d'été !", LOG_LEVEL_DEBUG)
						tasmota.cmd(string.format("TimeDst %i,%i,%i,%i,%i,%i", 
																diverses["fuseauHoraire"]["TimeDst"]["Hemisphere"], diverses["fuseauHoraire"]["TimeDst"]["Week"], diverses["fuseauHoraire"]["TimeDst"]["Month"], 
																diverses["fuseauHoraire"]["TimeDst"]["Day"], diverses["fuseauHoraire"]["TimeDst"]["Hour"], diverses["fuseauHoraire"]["TimeDst"]["Offset"]), 
																boolMute)
				end

				# Paramètre l'heure du reboot si il est paramétré
				if (diverses["heureReboot"] != "")
					var heures = int(string.split(diverses["heureReboot"], ":")[0])
					var minutes = int(string.split(diverses["heureReboot"], ":")[1])
					
					tasmota.add_cron(string.format("0 %i %i * * *", minutes, heures), /-> introspect.get(controleGeneral, "heureReboot"), "heureReboot")
				end		
				
				# Corrige un bug sur enregistrement du paramètre 'TelePeriod' dès le paramétrage du RangeExtender
				tasmota.cmd(string.format("TelePeriod %i", diverses.find("telePeriod", 300)), boolMute)
			elif msg["Time"].find("Set", 0)
			end
        end
    end
end

# Règles sur changement d'état des capteurs
# Si relaisLie != []
# Déclenche les relais liés aux capteurs
# Publie sur le réseau mqtt si paramétré
# Envoi une réponse automatique sur ModBus UDP ou TCP si esclave ModBus
globalFonctions.changementEtatCapteur = def(value, trigger, msg, moduleCapteur, cleBouton)
    import string
	import mqtt
	import json
    import persist
    import re

	var device
    var trameModBus = 	{
                            "DeviceAddress": drivers["ModBus"]["id"],
                            "FunctionCode": 0, 
                            "FunctionName": "",
                            "StartAddress": 0, 
                            "type": "", 
                            "Count": 0, 
                            "Values": []
                        }

	# Test
	log("GLOBAL_GESTION_CAPTEURS: -------------------- global changementEtatCapteur -------------------", LOG_LEVEL_DEBUG_PLUS)
	log("GLOBAL_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)							# value=SINGLE
	log("GLOBAL_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)						# trigger=Button1
	log("GLOBAL_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)								# msg={'Button1': {'Action': SINGLE}}
	log("GLOBAL_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG_PLUS)			# moduleCapteur=pompeVideCave
	log("GLOBAL_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG_PLUS)					# cleBouton=bouton1

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

	tasmota.yield()

	# Les différents capteurs sont stockés dans les paragraphes 'modules' du fichier persist.json
    # Gère les actions sur modification d'état des switchs (capteurs & interrupteurs)
    # Envoi une réponse automatique sur ModBus si esclave ModBus
	if (string.find(trigger, "Switch") > -1)
		device = modules[moduleCapteur]["environnement"]["capteurs"].find(cleBouton, false)
		if (device)
			if device.find("activation", "OFF") == "ON" && ((device.find("pin", -1) != -1  && device.find("virtuel", "OFF") == "OFF") || device.find("virtuel", "OFF") != "OFF")
				if (device["etat"] != value)
					# Enregistre l'état en json
					device["etat"] = value
					modules[moduleCapteur]["environnement"]["capteurs"][cleBouton]["value"] = value

					# Cherche les relais liés
					var relaisLie = device["relaisLie"]
					var typeOrdre = relaisLie["type"]
					for nb: 0 .. relaisLie["ids"].size() - 1
						globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
					end

                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        if (device.find("SwitchMode", 1) == 1)
                            value = (device["etat"] == "ON" ? 0xFF : 0x00)
                        elif (device.find("SwitchMode", 1) == 2)
                            value = (device["etat"] == "ON" ? 0x00 : 0xFF)
                        end

                        trameModBus["FunctionCode"] = 0x02 | 0x80           # Transformation retour automatique de valeur d'un capteur au maitre
                        trameModBus["FunctionName"] = "LECTURE_ENTREES_DISCRETES"
                        trameModBus["StartAddress"] = device["type"] + device["id"] - 1
                        trameModBus["type"] = "uint8"
                        trameModBus["Count"] = 1
                        trameModBus["Values"].push(value)

                        # Envoi automatique vers le Maitre sur changement de valeur par ModBus TCP Uniquement
                        tasmota.yield()
                        log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        if(drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON") 
                            import modbusFonctions   
                            modbusFonctions.envoiMsgModbusTCP(modbusFonctions.prepareTrame(trameModBus, "Reponse"), "Reponse")     
                        end
                    end
				end
			end
		end

		device = modules[moduleCapteur]["environnement"]["interrupteurs"].find(cleBouton, false)
		if (device)
			if device.find("activation", "OFF") == "ON" && ((device.find("pin", -1) != -1  && device.find("virtuel", "OFF") == "OFF") || device.find("virtuel", "OFF") != "OFF")
				if (device["etat"] != value)
					# Enregistre l'état en json
					device["etat"] = value
					modules[moduleCapteur]["environnement"]["interrupteurs"][cleBouton]["value"] = value

					# Cherche les relais liés
					var relaisLie = device["relaisLie"]
					var typeOrdre = relaisLie["type"]
					for nb: 0 .. relaisLie["ids"].size() - 1
						globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
					end

                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        if (device.find("SwitchMode", 1) == 1)
                            value = (device["etat"] == "ON" ? 0xFF : 0x00)
                        elif (device.find("SwitchMode", 1) == 2)
                            value = (device["etat"] == "ON" ? 0x00 : 0xFF)
                        end

                        trameModBus["FunctionCode"] = 0x02 | 0x80           # Transformation retour automatique de valeur d'un capteur au maitre
                        trameModBus["FunctionName"] = "LECTURE_ENTREES_DISCRETES"
                        trameModBus["StartAddress"] = device["type"] + device["id"] - 1
                        trameModBus["type"] = "uint8"
                        trameModBus["Count"] = 1
                        trameModBus["Values"].push(value)

                        # Envoi automatique vers le Maitre sur changement de valeur par ModBus TCP Uniquement
                        tasmota.yield()
                        log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        if(drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON") 
                            import modbusFonctions   
                            modbusFonctions.envoiMsgModbusTCP(modbusFonctions.prepareTrame(trameModBus, "Reponse"), "Reponse")     
                        end
                    end
				end
			end
		end
	# Gère les actions sur modification d'état des BP
    # Envoi une réponse automatique sur ModBus si esclave ModBus
	elif (string.find(trigger, "Button") > -1)
		device = modules[moduleCapteur]["environnement"]["boutons"].find(cleBouton, false)
		if (device)
			if device.find("activation", "OFF") == "ON" && ((device.find("pin", -1) != -1  && device.find("virtuel", "OFF") == "OFF") || device.find("virtuel", "OFF") != "OFF")
				if (device["etat"] != value)
                    # Enregistre l'état en json
                    device["etat"] = value
                    modules[moduleCapteur]["environnement"]["boutons"][cleBouton]["value"] = value

                    # Cherche les relais liés
                    var relaisLie = device["relaisLie"]
                    var typeOrdre = relaisLie["type"]
                    for nb: 0 .. relaisLie["ids"].size() - 1
                        globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
                    end

                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        if (device.find("SwitchMode", 1) == 1)
                            value = (device["etat"] == "ON" ? 0xFF : 0x00)
                        elif (device.find("SwitchMode", 1) == 2)
                            value = (device["etat"] == "ON" ? 0x00 : 0xFF)
                        end

                        trameModBus["FunctionCode"] = 0x02 | 0x80           # Transformation retour automatique de valeur d'un capteur au maitre
                        trameModBus["FunctionName"] = "LECTURE_ENTREES_DISCRETES"
                        trameModBus["StartAddress"] = device["type"] + device["id"] - 1
                        trameModBus["type"] = "uint8"
                        trameModBus["Count"] = 1
                        trameModBus["Values"].push(value)

                        # Envoi automatique vers le Maitre sur changement de valeur par ModBus TCP Uniquement
                        tasmota.yield()
                        log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        if(drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON") 
                            import modbusFonctions   
                            modbusFonctions.envoiMsgModbusTCP(modbusFonctions.prepareTrame(trameModBus, "Reponse"), "Reponse")     
                        end
                    end
				end
			end
		end
	# Gère les actions sur modification d'état des DHT22 & DS18B20
    # N'envoie pas de réponse automatique sur ModBus car varie trop souvent
	elif (string.find(trigger, "AM2301#Temperature") > -1 || string.find(trigger, "AM2301#Humidity") > -1 || string.find(trigger, "DS18B20") > -1)
		device = modules[moduleCapteur]["environnement"]["thermometres"].find(cleBouton, false)
		if (device)
			if device.find("activation", "OFF") == "ON" && ((device.find("pin", -1) != -1  && device.find("virtuel", "OFF") == "OFF") || device.find("virtuel", "OFF") != "OFF")
				if (device["value"] != value)
                    # Enregistre l'état en json
                    if (string.find(trigger, "AM2301#Temperature") > -1 || string.find(trigger, "DS18B20") > -1)
                        device["value"] = value
                        modules[moduleCapteur]["environnement"]["thermometres"][cleBouton]["value"] = real(value)
                    else
                        device["Humidity"] = value
                        modules[moduleCapteur]["environnement"]["thermometres"][cleBouton]["Humidity"] = real(value)
                    end

                    # Compare la température & l'humidité avec les limites
                    var limites = device["limites"]
                    if (limites.size() > 0)
                        if int(value) >= int(limites[1])
                            log(string.format("GESTION_CAPTEURS: Humidite superieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
                            value = "ON"
                        else
                            log(string.format("GESTION_CAPTEURS: Humidite inferieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
                            value = "OFF"
                        end
                    end

                    # Cherche les relais liés
                    var relaisLie = device["relaisLie"]
                    var typeOrdre = relaisLie["type"]
                    for nb: 0 .. relaisLie["ids"].size() - 1
                        globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, true, relaisLie["delai"])
                    end	
				end
			end
		end
	# Gère les actions sur modification d'état des capteur analogiques réels
    # N'envoie pas de réponse automatique car varie trop souvent
	elif (string.find(trigger, "ANALOG#A") > -1)
		device = modules[moduleCapteur]["environnement"]["analogiques"].find(cleBouton, false)
		if (device)
			if device.find("activation", "OFF") == "ON" && ((device.find("pin", -1) != -1  && device.find("virtuel", "OFF") == "OFF") || device.find("virtuel", "OFF") != "OFF")
                if (device["value"] != value)
                    # Enregistre l'état en json
                    device["value"] = int(value)
                    modules[moduleCapteur]["environnement"]["analogiques"][cleBouton]["value"] = int(value)

                    # Cherche les relais liés
                    var relaisLie = device["relaisLie"]
                    var typeOrdre = relaisLie["type"]
                    for nb: 0 .. relaisLie["ids"].size() - 1
                        globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
                    end
                end
			end
		end	
	# Gère les actions sur modification d'état des compteurs réels
    # Envoi une réponse automatique sur ModBus si esclave ModBus
	elif (string.find(trigger, "COUNTER#C") > -1)
		device = modules[moduleCapteur]["environnement"]["compteurs"].find(cleBouton, false)
		if (device)
			if device.find("activation", "OFF") == "ON" && ((device.find("pin", -1) != -1  && device.find("virtuel", "OFF") == "OFF") || device.find("virtuel", "OFF") != "OFF")
                if (device["etat"] != value)
                    # Enregistre l'état en json
                    device["etat"] = real(value)
                    modules[moduleCapteur]["environnement"]["compteurs"][cleBouton]["value"] = real(value)
                    
                    # Cherche les relais liés
                    var relaisLie = device["relaisLie"]
                    var typeOrdre = relaisLie["type"]
                    for nb: 0 .. relaisLie["ids"].size() - 1
                        globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
                    end		
                    
                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        trameModBus["FunctionCode"] = 0x04 | 0x80           # Transformation retour automatique de valeur d'un capteur au maitre
                        trameModBus["FunctionName"] = "LECTURE_REGISTRES_ENTREES"
                        trameModBus["StartAddress"] = device["type"] + device["id"] - 1
                        trameModBus["type"] = "uint32"
                        trameModBus["Count"] = 1
                        trameModBus["Values"].push(int(value))

                        # Envoi automatique vers le Maitre sur changement de valeur par ModBus TCP Uniquement
                        tasmota.yield()
                        log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        if(drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON") 
                            import modbusFonctions   
                            modbusFonctions.envoiMsgModbusTCP(modbusFonctions.prepareTrame(trameModBus, "Reponse"), "Reponse")     
                        end
                    end
                end
			end
		end
	end

	# Enregistre les nouvelles valeurs de capteurs en json
	persist.modules = modules	
end

# Règle sur changement d'état du Dimmer et HSBColor des leds WS2812
globalFonctions.changementEtatWS2812 = def(value, trigger, msg, moduleLED, cleLED)
    import string
	import json
    import persist

	var device

	# Test
	log("GLOBAL_GESTION_WS2812: -------------------- global changementEtatWS2812 -------------------", LOG_LEVEL_DEBUG)
	log("GLOBAL_GESTION_WS2812: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	log("GLOBAL_GESTION_WS2812: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	log("GLOBAL_GESTION_WS2812: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	log("GLOBAL_GESTION_WS2812: moduleLED=" + str(moduleLED), LOG_LEVEL_DEBUG)					# moduleCapteur=cuve
	log("GLOBAL_GESTION_WS2812: cleLED=" + str(cleLED), LOG_LEVEL_DEBUG)						# cleLED=relai1

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

	tasmota.yield()

	# Les différents bandeaux LEDs WS2812 sont stockés dans les paragraphes 'modules' du fichier persist.json
	if (string.find(trigger, "Dimmer") > -1)
		device = modules[moduleLED]["environnement"]["relais"].find(cleLED, false)
		if (device)
			if device.find("activation", "OFF") == "ON" && ((device.find("pin", -1) != -1  && device.find("virtuel", "OFF") == "OFF") || device.find("virtuel", "OFF") != "OFF")
				if (device["etat"] != value)	
					# Enregistre l'état en json:
					# de la luminosité
					device["value"] = value
					modules[moduleLED]["environnement"]["relais"][cleLED]["value"] = value

					if (msg.find("HSBColor", false))
						# de la saturation
						device["saturation"] = int(string.split(msg["HSBColor"], ",")[1])
						modules[moduleLED]["environnement"]["relais"][cleLED]["saturation"] = device["saturation"]

						# de la saturation
						device["couleur"] = int(string.split(msg["HSBColor"], ",")[0])
						modules[moduleLED]["environnement"]["relais"][cleLED]["couleur"] = device["couleur"]
					end
				end
			end
		end
	end

	# Enregistre les nouvelles valeurs de capteurs en json
	persist.modules = modules
end

# Permet la modification de l'état des relais selon l'état de certains capteurs, boutons, ou interrupteurs
# Est déclenché à partir de la fonction: 'globalFonctions.changementEtatCapteur'
globalFonctions.modifEtatRelai = def(moduleCapteur, idRelai, typeOrdre, etat, boolCapteurs, boolTimer, delaiAvantCommande)
	import string

	# Test
	log("MODIF_ETAT_RELAI: -------------------- global modifEtatRelai -------------------", LOG_LEVEL_DEBUG)
	log("MODIF_ETAT_RELAI: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)						
	log("MODIF_ETAT_RELAI: idRelai=" + str(idRelai), LOG_LEVEL_DEBUG)								
	log("MODIF_ETAT_RELAI: typeOrdre=" + str(typeOrdre), LOG_LEVEL_DEBUG)								
	log("MODIF_ETAT_RELAI: etat=" + str(etat), LOG_LEVEL_DEBUG)									
	log("MODIF_ETAT_RELAI: boolCapteurs=" + str(boolCapteurs), LOG_LEVEL_DEBUG)		
	log("MODIF_ETAT_RELAI: boolTimer=" + str(boolTimer), LOG_LEVEL_DEBUG)									
	log("MODIF_ETAT_RELAI: delaiAvantCommande=" + str(delaiAvantCommande), LOG_LEVEL_DEBUG)
	
	tasmota.yield()

	# Modifie l'ordre envoyé au relai en fonction du type de capteur ou bouton
	if (typeOrdre == "Switch" && (etat == "TOGGLE" || etat == "SINGLE"))
		if tasmota.get_power()[idRelai - 1] == true
			etat = "OFF"
		else etat = "ON"
		end
	elif (typeOrdre == "ON" && etat == "OFF")
		return
	elif (typeOrdre == "OFF" && etat == "ON")
		return
	end
	
	# Si le relai est déjà dans l'état visé
	if (etat == "") return end
	if (tasmota.get_power()[idRelai - 1] == true && etat == "ON") return end
	if (tasmota.get_power()[idRelai - 1] == false && etat == "OFF") return end

	# Paramètres par défaut si absent
	if boolCapteurs == nil boolCapteurs = false end
	if boolTimer == nil boolTimer = true end
	if delaiAvantCommande == nil delaiAvantCommande = 0 end

	log("MODIF_ETAT_RELAI: -------------------- global modifEtatRelai 2 -------------------", LOG_LEVEL_DEBUG)							
	log("MODIF_ETAT_RELAI: typeOrdre=" + str(typeOrdre), LOG_LEVEL_DEBUG)								
	log("MODIF_ETAT_RELAI: etat=" + str(etat), LOG_LEVEL_DEBUG)									
	log("MODIF_ETAT_RELAI: boolCapteurs=" + str(boolCapteurs), LOG_LEVEL_DEBUG)		
	log("MODIF_ETAT_RELAI: boolTimer=" + str(boolTimer), LOG_LEVEL_DEBUG)									
	log("MODIF_ETAT_RELAI: delaiAvantCommande=" + str(delaiAvantCommande), LOG_LEVEL_DEBUG)

	# Lance l'ordre
	if delaiAvantCommande != 0
		tasmota.remove_timer(string.format("timer_commande%i", idRelai))
		tasmota.set_timer(delaiAvantCommande * 1000, /-> tasmota.cmd("Power" + str(idRelai) + " " + etat, boolMute), string.format("timer_commande%i", idRelai))
		log(string.format("MODIF_ETAT_RELAI: Relai %i %s après délai de %is!", idRelai, etat, delaiAvantCommande), LOG_LEVEL_DEBUG)
	else
		tasmota.cmd("Power" + str(idRelai) + " " + etat, boolMute)
		log(string.format("MODIF_ETAT_RELAI: Relai %i %s !", idRelai, etat), LOG_LEVEL_DEBUG)
	end

	# Désactive les capteurs associés à son fonctionnement
	if boolCapteurs
		var capteurs = modules[moduleCapteur]["environnement"].find("capteurs", false)
		
		if capteurs
			# Désactive temporairement les capteurs si Relai ON / Réactive les capteurs si Relai OFF
			log("MODIF_ETAT_RELAI: " + (etat == "ON" ? "Desactivation" : "Reactivation") + " des capteurs !", LOG_LEVEL_DEBUG)
			for cleCapteurs: capteurs.keys()
				capteurs[cleCapteurs]["activation"] = (etat == "ON" ? "OFF" : "ON")
			end	
		end
	end
end

# exemples: 
# ReglageGlobal afficheMemoire
# ReglageGlobal nbLogsFiles 14
# ReglageGlobal logLevel 4
globalFonctions.reglageGlobal = def(cmd, idx, payload, payload_json)
    import string
    import json
    import mqtt
    import gestionFileFolder
	import persist

    var fonction = false
    var parametres = []
    var reponse_cmnd = {}
    
    # Test   
    log("REGLAGE_GLOBAL: -------------------- reglageGlobal -------------------", LOG_LEVEL_DEBUG_PLUS)
    log("REGLAGE_GLOBAL: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    log("REGLAGE_GLOBAL: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    log("REGLAGE_GLOBAL: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    log("REGLAGE_GLOBAL: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    log("REGLAGE_GLOBAL: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
	if (parametres != false)
		if (parametres.size() > 0)	log("REGLAGE_GLOBAL: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
		if (parametres.size() > 1)	log("REGLAGE_GLOBAL: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end
	end

    if string.toupper(fonction) == "AFFICHEMEMOIRE"
		import diversFonctions

        diversFonctions.statMemory()
	elif string.toupper(fonction) == string.toupper("nbLogsFiles")
        try
            # Sauvegarde le paramètre
			tasmota.cmd(string.format("FileLog %i", int(parametres[0])), boolMute)
            diverses["logs"]["nbLogsFiles"] = int(parametres[0])
            persist.save()
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end		
	elif string.toupper(fonction) == string.toupper("logLevel")
        try
            # Sauvegarde le paramètre
			tasmota.cmd(string.format("Backlog SerialLog %i; WebLog %i;", int(parametres[0]), int(parametres[0])), boolMute)
            diverses["logs"]["level"] = int(parametres[0])
            persist.save()
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end	
	end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd = "ReglageGlobal: Affiche les statistiques de la mémoire"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Retourne le module lors de l'importation
return globalFonctions