# Définition du module
var globalFonctions = module("/globalFonctions")

globalFonctions.afficheDateTime = def(sepHoraire, boolAfficheSec, sepDateHeure)
    import string

	var time_dump = tasmota.time_dump(tasmota.rtc()["local"])
	
	# Paramètres par défaut si absent
	if sepHoraire == "" sepHoraire = "-" end
	if boolAfficheSec == nil boolAfficheSec = false end
	
	var date = (time_dump["day"] < 10 ? "0" + str(time_dump["day"]) : str(time_dump["day"])) + "/" 
		date += (time_dump["month"] < 10 ? "0" + str(time_dump["month"]) : str(time_dump["month"])) + "/" 
		date += str(time_dump["year"]) + (sepDateHeure == "" ? " " : sepDateHeure)
		
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

# Génère un débit aléatoire
globalFonctions.getRandomInt = def(min, max)
	import math
	import crypto

	var index_found = true
	var x1 = 0

	min = math.ceil(min);
	max = math.floor(max);

	while (index_found)
		x1 = crypto.random(1)[0]
		if ((x1 >= min) && (x1 <= max))
			index_found = false
		end
	end

	return int(x1);
end

# Récupère les template enreistré dans la device Tasmota
# Récupère les componentes
# @ordreGPIO = tableau de GPIO
# @template = tableau json enregistré dans _persist.json
# @ Retourne true si l'enregistrement en json doit être effectué
globalFonctions.recupereTemplate = def(json, ordreGPIO, template, componentesInverse)
    import persist

    var enregistrePersistant = false
    var reponseCMD
    var componentes = json["modele"]["componentes"]

	# Récupère le template (modele)
	if str(tasmota.cmd("Template", boolMute)) != str(template)
		log ("RECUP_TEMPLATE: Recupere le template du modele !", LOG_LEVEL_DEBUG)
		
		template = tasmota.cmd("Template", boolMute)
		enregistrePersistant = true
	end

	# Récupère les componentes existants du modele 
	reponseCMD = tasmota.cmd("GPIOs", boolMute)
	for cle: reponseCMD.keys()
		if componentes.size() == 0
			log ("RECUP_TEMPLATE: Enregistre les componentes en json !", LOG_LEVEL_DEBUG)
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
		log ("RECUP_TEMPLATE: Enregistre Template et Componentes en json !", LOG_LEVEL_DEBUG)

		persist.parametres = json	
		persist.save() 

        enregistrePersistant = false
	end

    return enregistrePersistant
end

# Règles sur changement d'état lors du démarrage de Tasmota
globalFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import persist

	# Test
	log ("GLOBAL_CHGT_ETAT_DEMARRAGE: -------------------- global changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	log ("GLOBAL_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	log ("GLOBAL_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	log ("GLOBAL_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
			controleGeneral.connected = true
        elif msg["WIFI"].find("Disonnected", 0)
            controleGeneral.connected = false
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    # Save: Avant redemarrage de tasmota
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
			# listen on port 2000 for all interfaces
			#udpListener("224.3.0.1", 2000)

			# Tasmota ne gère pas encore les webSockets
			#tcpServeur(8888)
        elif msg[trigger].find("Save", 0)
            persist.parametres = controleGeneral.parametres	
            persist.save() 
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
	# Se déclenche après la connexion d'un nouveau client Range Extender
    elif (trigger == "RgxClients")
    end
end

# Règles sur changement d'état des capteurs
globalFonctions.changementEtatCapteur = def(value, trigger, msg, moduleCapteur, cleBouton)
    import string
	import mqtt
	import json

	# Test
	log ("GLOBAL_GESTION_CAPTEURS: -------------------- global changementEtatCapteur -------------------", LOG_LEVEL_DEBUG)
	log ("GLOBAL_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	log ("GLOBAL_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	log ("GLOBAL_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	log ("GLOBAL_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)			# moduleCapteur=pompeVideCave
	log ("GLOBAL_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG)					# cleBouton=bouton1

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    # Gère les actions sur modification d'état des switchs
    if string.find(trigger, "Switch") > -1
        var capteur = controleGeneral.parametres["modules"][moduleCapteur]["environnement"]["capteurs"].find(cleBouton, false)

		if capteur
			if capteur.find("activation", "OFF") == "ON" && ((capteur.find("pin", -1) != -1  && capteur.find("virtuel", "OFF") == "OFF") || capteur.find("virtuel", "OFF") == "ON")
				# Enregistre l'état en json
				capteur["etat"] = value
						
				# Cherche les relais liés
				var relaisLie = capteur["relaisLie"]
				var typeOrdre = relaisLie["type"]
				for nb: 0 .. relaisLie["ids"].size() - 1
					globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
				end
			end
		end
    end

    # Gère les actions sur modification d'état des switchs
    if string.find(trigger, "Button") > -1
        var bouton = controleGeneral.parametres["modules"][moduleCapteur]["environnement"]["boutons"].find(cleBouton, false)

		if bouton
			if bouton.find("activation", "OFF") == "ON" && ((bouton.find("pin", -1) != -1  && bouton.find("virtuel", "OFF") == "OFF") || bouton.find("virtuel", "OFF") == "ON")
				# Enregistre l'état en json
				bouton["etat"] = value
						
				# Cherche les relais liés
				var relaisLie = bouton["relaisLie"]
				var typeOrdre = relaisLie["type"]

				for nb: 0 .. relaisLie["ids"].size() - 1
					globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, true, true, relaisLie["delai"])	
				end
			end
		end
    end

    # Gère les actions sur modification d'état des switchs
    if string.find(trigger, "AM2301#Humidity") > -1
        var thermo = controleGeneral.parametres["modules"][moduleCapteur]["environnement"].find(cleBouton, false)

		if thermo
			if thermo.find("activation", "OFF") == "ON" && ((thermo.find("pin", -1) != -1  && thermo.find("virtuel", "OFF") == "OFF") || thermo.find("virtuel", "OFF") == "ON")
				if int(thermo["value"]) != int(value)
					# Enregistre l'état en json
					thermo["value"] = real(value)

					# Compare l'humidité avec les limites
					var limites = thermo["relaisLie"]["limites"]
							
					if int(value) >= int(limites[1])
						log (string.format("GESTION_CAPTEURS: Humidite superieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
						value = "ON"
					else
						log (string.format("GESTION_CAPTEURS: Humidite inferieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
						value = "OFF"
					end
								
					# Cherche les relais liés
					var relaisLie = thermo["relaisLie"]
					var typeOrdre = relaisLie["type"]
					for nb: 0 .. relaisLie["ids"].size() - 1
						globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, true, relaisLie["delai"])
					end	
				end
			end
		end
    end
end

# Retourne le module lors de l'importation
return globalFonctions