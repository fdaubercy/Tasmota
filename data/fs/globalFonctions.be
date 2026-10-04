# Définition du module
#@ solidify:globalFonctions
var globalFonctions = module("globalFonctions")

# Delai avant demarrage du serveur FTP apres connexion Wi-Fi.
# Demarrer le FTP tout de suite faisait planter le module (abort() dans 'new FtpServer',
# ~5 Ko) : la regle Wifi tombe pendant le pic memoire du boot (compilation des .be en .bec).
# En regime etabli le tas libre est ~76 Ko, largement suffisant.
globalFonctions.DELAI_DEMARRAGE_FTP_MS = 50000

# Demarre le serveur FTP (mode 2) s'il n'est pas deja actif. Appelee par la minuterie
# 'demarrageFTP' armee dans changementEtatDemarrage.
def globalFonctions_demarreFTP()
	# Firmware compile sans USE_FTP (ex. la cave) : 'UFSFTP' est une commande inconnue -> pas de cle 'UfsFTP'
	var etatFTP = tasmota.cmd("UFSFTP", boolMute)
	if !isinstance(etatFTP, map) || !etatFTP.contains("UfsFTP")
		logFonctions.log("GLOBAL_FTP: Serveur FTP absent de ce firmware (USE_FTP) !", LOG_LEVEL_DEBUG)
		return
	end
	if (int(etatFTP["UfsFTP"]) == 0)	tasmota.cmd("UFSFTP 2", boolMute)	end
end
globalFonctions.demarreFTP = globalFonctions_demarreFTP

# Règles sur changement d'état lors du démarrage de Tasmota
def globalFonctions_changementEtatDemarrage(value, trigger, msg)
    import string
    import mqtt
    import persist
	import gestionFileFolder
	import introspect

	# Test
	logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: -------------------- global changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	# Pas de "deballage" de 'value' ici (inutilise dans cette fonction) : l'ancienne boucle
	# 'for cle: value.keys() value = value[cle] end' reindexait la valeur precedente des qu'il
	# y avait plus d'une cle -> "string indices must be integers" (ex. bloc 'Wifi' de STATE).

	# Lorsque la connexion Wi-Fi est change
	# La regle "Wifi" recoit AUSSI tout JSON portant une cle 'Wifi' (telemetrie STATE, Status 11,
	# reponse a 'State'...) : seuls {"WIFI":{"Connected"|"Disconnected":..}} et {"Wifi":"ON"|"OFF"}
	# sont traites, le reste est ignore au lieu de lever une erreur de cle.
	if (trigger == "Wifi")
		var etatWifi = msg.find("WIFI")
		if !isinstance(etatWifi, map)	etatWifi = {}	end

        if etatWifi.find("Connected", 0)
			introspect.set(controleGeneral, "connected", true)

			# Règle les paramètres du serveur FTP
			if serveur.find("serveurFTP", false)
				if serveur["serveurFTP"]["activation"] == "ON"
					# Demarrage DIFFERE (voir DELAI_DEMARRAGE_FTP_MS) ; timer nomme -> une reconnexion
					# Wi-Fi reprogramme au lieu d'empiler plusieurs demarrages.
					tasmota.remove_timer("demarrageFTP")
					tasmota.set_timer(globalFonctions.DELAI_DEMARRAGE_FTP_MS, globalFonctions.demarreFTP, "demarrageFTP")
				else
					tasmota.remove_timer("demarrageFTP")
					tasmota.cmd("UFSFTP 0", boolMute)
				end
			end
        elif etatWifi.find("Disconnected", 0)
            introspect.set(controleGeneral, "connected", false)
        elif (msg.find("Wifi") == "OFF" || msg.find("Wifi") == "ON")
			introspect.set(controleGeneral, "connected", (msg["Wifi"] == "OFF" ? false : true))
            logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: Wifi " + (msg["Wifi"] == "OFF" ? "désactivé" : "activé") + " !", LOG_LEVEL_DEBUG)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    # Save: Avant redemarrage de tasmota
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            introspect.set(controleGeneral, "booted", true)

			# Récupère son adresse MAC si inconnue en json (ou si elle a changé)
			# Un seul 'Status 5', et son resultat est verifie avant d'etre indexe : sous faible
			# memoire la reponse peut etre tronquee, et tasmota.cmd() renvoie alors la CHAINE brute
			# (exec_rules, JSON invalide) -> "string indices must be integers" au boot.
			var statusNET = tasmota.cmd("Status 5", boolMute)
			var adresseMAC = (isinstance(statusNET, map) && isinstance(statusNET.find("StatusNET"), map)) ? statusNET["StatusNET"].find("Mac") : nil
			if (adresseMAC == nil)
				logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: Adresse MAC illisible (reponse 'Status 5' invalide) !", LOG_LEVEL_ERREUR)
			elif (!serveur.find("adressMAC", false))
				serveur.insert("adressMAC", adresseMAC)
				logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: Récupère l'adresse MAC du module !", LOG_LEVEL_DEBUG)
			elif (serveur["adressMAC"] != adresseMAC)
				serveur["adressMAC"] = adresseMAC
				logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: Modifie l'adresse MAC du module !", LOG_LEVEL_DEBUG)
			end
		elif msg[trigger].find("Save", 0)
			try
				persist.serveur = serveur	
				persist.diverses = diverses
				persist.modules = modules
				persist.drivers = drivers
				persist.save() 
			except .. as error, message
				logFonctions.log(string.format("GLOBAL_CHGT_ETAT_DEMARRAGE_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
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
						logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: Regle la date de passage à l'heure d'hiver !", LOG_LEVEL_DEBUG)
						tasmota.cmd(string.format("TimeStd %i,%i,%i,%i,%i,%i", 
																diverses["fuseauHoraire"]["TimeStd"]["Hemisphere"], diverses["fuseauHoraire"]["TimeStd"]["Week"], diverses["fuseauHoraire"]["TimeStd"]["Month"], 
																diverses["fuseauHoraire"]["TimeStd"]["Day"], diverses["fuseauHoraire"]["TimeStd"]["Hour"], diverses["fuseauHoraire"]["TimeStd"]["Offset"]), 
																boolMute)
				end

				var TimeDst = tasmota.cmd("TimeDst", boolMute)["TimeDst"]
				if (TimeDst["Hemisphere"] != diverses["fuseauHoraire"]["TimeDst"]["Hemisphere"] || TimeDst["Week"] != diverses["fuseauHoraire"]["TimeDst"]["Week"] || TimeDst["Month"] != diverses["fuseauHoraire"]["TimeDst"]["Month"] ||
						TimeDst["Day"] != diverses["fuseauHoraire"]["TimeDst"]["Day"] || TimeDst["Hour"] != diverses["fuseauHoraire"]["TimeDst"]["Hour"] || TimeDst["Offset"] != diverses["fuseauHoraire"]["TimeDst"]["Offset"])
						logFonctions.log("GLOBAL_CHGT_ETAT_DEMARRAGE: Regle la date de passage à l'heure d'été !", LOG_LEVEL_DEBUG)
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
globalFonctions.changementEtatDemarrage = globalFonctions_changementEtatDemarrage

# Règles sur changement d'état des capteurs
# Si relaisLie != []
# Déclenche les relais liés aux capteurs
# Publie sur le réseau mqtt si paramétré
# Envoi une réponse automatique sur ModBus UDP ou TCP si esclave ModBus
def globalFonctions_changementEtatCapteur(value, trigger, msg, moduleCapteur, cleBouton)
    import string
	import mqtt
	import json
    import persist
    import re

	var device

	# Test
	logFonctions.log("GLOBAL_GESTION_CAPTEURS: -------------------- global changementEtatCapteur -------------------", LOG_LEVEL_DEBUG_PLUS)
	logFonctions.log("GLOBAL_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)							# value=SINGLE
	logFonctions.log("GLOBAL_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)						# trigger=Button1
	logFonctions.log("GLOBAL_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)								# msg={'Button1': {'Action': SINGLE}}
	logFonctions.log("GLOBAL_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG_PLUS)			# moduleCapteur=pompeVideCave
	logFonctions.log("GLOBAL_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG_PLUS)					# cleBouton=bouton1

	# Extrait la valeur scalaire d'un evenement, ex: {"Action": "ON"} -> "ON" (eventuellement imbrique).
	# Avant : 'for cle: value.keys() value = value[cle] end' reaffectait 'value' PENDANT le parcours
	# de ses cles -> des la 2e cle, indexation de la valeur extraite (erreur), et un seul niveau deroule.
	while isinstance(value, map)
		if value.contains("Action")
			value = value["Action"]
		elif value.size() == 1
			value = value[value.keys()()]		# unique cle
		else
			logFonctions.log("GLOBAL_GESTION_CAPTEURS_ERREUR: Valeur ambigue pour '" + str(trigger) + "' : " + str(value), LOG_LEVEL_ERREUR)
			return
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
					for nb: 0 .. relaisLie.find("ids", []).size() - 1
						globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
					end

                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        if (device.find("SwitchMode", 1) == 1)
                            value = (device["etat"] == "ON" ? 0xFF : 0x00)
                        elif (device.find("SwitchMode", 1) == 2)
                            value = (device["etat"] == "ON" ? 0x00 : 0xFF)
                        end

                        # Push 0x10 vers le maitre en UDP (option B) : voir modbusFonctions.pousseEtat
                        tasmota.yield()
                        logFonctions.log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        import modbusFonctions
                        modbusFonctions.pousseEtat(device["type"] + device["id"] - 1, "uint16", [value])
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
					for nb: 0 .. relaisLie.find("ids", []).size() - 1
						globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
					end

                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        if (device.find("SwitchMode", 1) == 1)
                            value = (device["etat"] == "ON" ? 0xFF : 0x00)
                        elif (device.find("SwitchMode", 1) == 2)
                            value = (device["etat"] == "ON" ? 0x00 : 0xFF)
                        end

                        # Push 0x10 vers le maitre en UDP (option B) : voir modbusFonctions.pousseEtat
                        tasmota.yield()
                        logFonctions.log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        import modbusFonctions
                        modbusFonctions.pousseEtat(device["type"] + device["id"] - 1, "uint16", [value])
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
                    for nb: 0 .. relaisLie.find("ids", []).size() - 1
                        globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
                    end

                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        if (device.find("SwitchMode", 1) == 1)
                            value = (device["etat"] == "ON" ? 0xFF : 0x00)
                        elif (device.find("SwitchMode", 1) == 2)
                            value = (device["etat"] == "ON" ? 0x00 : 0xFF)
                        end

                        # Push 0x10 vers le maitre en UDP (option B) : voir modbusFonctions.pousseEtat
                        tasmota.yield()
                        logFonctions.log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        import modbusFonctions
                        modbusFonctions.pousseEtat(device["type"] + device["id"] - 1, "uint16", [value])
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
                    var limites = device.find("limites", [])
                    if (limites.size() > 0)
                        if int(value) >= int(limites[1])
                            logFonctions.log(string.format("GESTION_CAPTEURS: Humidite superieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
                            value = "ON"
                        else
                            logFonctions.log(string.format("GESTION_CAPTEURS: Humidite inferieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
                            value = "OFF"
                        end
                    end

                    # Cherche les relais liés
                    var relaisLie = device["relaisLie"]
                    var typeOrdre = relaisLie["type"]
                    for nb: 0 .. relaisLie.find("ids", []).size() - 1
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
                    for nb: 0 .. relaisLie.find("ids", []).size() - 1
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
                    for nb: 0 .. relaisLie.find("ids", []).size() - 1
                        globalFonctions.modifEtatRelai(moduleCapteur, relaisLie["ids"][nb], typeOrdre, value, false, false, relaisLie["delai"])
                    end		
                    
                    # Envoi son état au Maitre ModBus si le module est un esclave ModBus (id > 0)
                    if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"].find("id", 0) > 0)
                        # Push 0x10 vers le maitre en UDP (option B) : voir modbusFonctions.pousseEtat
                        tasmota.yield()
                        logFonctions.log(string.format("GLOBAL_GESTION_CAPTEURS: Informe le maitre ModBus du changement de valeur de '%s' (GPIO %i) = %s", device["nom"], device["pin"], device["etat"]), LOG_LEVEL_DEBUG_PLUS)
                        import modbusFonctions
                        modbusFonctions.pousseEtat(device["type"] + device["id"] - 1, "uint32", [int(value)])
                    end
                end
			end
		end
	end

	# Enregistre les nouvelles valeurs de capteurs en json
	persist.modules = modules	
end
globalFonctions.changementEtatCapteur = globalFonctions_changementEtatCapteur

# Règle sur changement d'état du Dimmer et HSBColor des leds WS2812
def globalFonctions_changementEtatWS2812(value, trigger, msg, moduleLED, cleLED)
    import string
	import json
    import persist

	var device

	# Test
	logFonctions.log("GLOBAL_GESTION_WS2812: -------------------- global changementEtatWS2812 -------------------", LOG_LEVEL_DEBUG)
	logFonctions.log("GLOBAL_GESTION_WS2812: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	logFonctions.log("GLOBAL_GESTION_WS2812: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	logFonctions.log("GLOBAL_GESTION_WS2812: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	logFonctions.log("GLOBAL_GESTION_WS2812: moduleLED=" + str(moduleLED), LOG_LEVEL_DEBUG)					# moduleCapteur=cuve
	logFonctions.log("GLOBAL_GESTION_WS2812: cleLED=" + str(cleLED), LOG_LEVEL_DEBUG)						# cleLED=relai1

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
globalFonctions.changementEtatWS2812 = globalFonctions_changementEtatWS2812

# Permet la modification de l'état des relais selon l'état de certains capteurs, boutons, ou interrupteurs
# Est déclenché à partir de la fonction: 'globalFonctions.changementEtatCapteur'
def globalFonctions_modifEtatRelai(moduleCapteur, idRelai, typeOrdre, etat, boolCapteurs, boolTimer, delaiAvantCommande)
	import string

	# Test
	logFonctions.log("MODIF_ETAT_RELAI: -------------------- global modifEtatRelai -------------------", LOG_LEVEL_DEBUG)
	logFonctions.log("MODIF_ETAT_RELAI: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)						
	logFonctions.log("MODIF_ETAT_RELAI: idRelai=" + str(idRelai), LOG_LEVEL_DEBUG)								
	logFonctions.log("MODIF_ETAT_RELAI: typeOrdre=" + str(typeOrdre), LOG_LEVEL_DEBUG)								
	logFonctions.log("MODIF_ETAT_RELAI: etat=" + str(etat), LOG_LEVEL_DEBUG)									
	logFonctions.log("MODIF_ETAT_RELAI: boolCapteurs=" + str(boolCapteurs), LOG_LEVEL_DEBUG)		
	logFonctions.log("MODIF_ETAT_RELAI: boolTimer=" + str(boolTimer), LOG_LEVEL_DEBUG)									
	logFonctions.log("MODIF_ETAT_RELAI: delaiAvantCommande=" + str(delaiAvantCommande), LOG_LEVEL_DEBUG)
	
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

	logFonctions.log("MODIF_ETAT_RELAI: -------------------- global modifEtatRelai 2 -------------------", LOG_LEVEL_DEBUG)							
	logFonctions.log("MODIF_ETAT_RELAI: typeOrdre=" + str(typeOrdre), LOG_LEVEL_DEBUG)								
	logFonctions.log("MODIF_ETAT_RELAI: etat=" + str(etat), LOG_LEVEL_DEBUG)									
	logFonctions.log("MODIF_ETAT_RELAI: boolCapteurs=" + str(boolCapteurs), LOG_LEVEL_DEBUG)		
	logFonctions.log("MODIF_ETAT_RELAI: boolTimer=" + str(boolTimer), LOG_LEVEL_DEBUG)									
	logFonctions.log("MODIF_ETAT_RELAI: delaiAvantCommande=" + str(delaiAvantCommande), LOG_LEVEL_DEBUG)

	# Lance l'ordre
	if delaiAvantCommande != 0
		tasmota.remove_timer(string.format("timer_commande%i", idRelai))
		tasmota.set_timer(delaiAvantCommande * 1000, /-> tasmota.cmd("Power" + str(idRelai) + " " + etat, boolMute), string.format("timer_commande%i", idRelai))
		logFonctions.log(string.format("MODIF_ETAT_RELAI: Relai %i %s après délai de %is!", idRelai, etat, delaiAvantCommande), LOG_LEVEL_DEBUG)
	else
		tasmota.cmd("Power" + str(idRelai) + " " + etat, boolMute)
		logFonctions.log(string.format("MODIF_ETAT_RELAI: Relai %i %s !", idRelai, etat), LOG_LEVEL_DEBUG)
	end

	# Désactive les capteurs associés à son fonctionnement
	if boolCapteurs
		var capteurs = modules[moduleCapteur]["environnement"].find("capteurs", false)
		
		if capteurs
			# Désactive temporairement les capteurs si Relai ON / Réactive les capteurs si Relai OFF
			logFonctions.log("MODIF_ETAT_RELAI: " + (etat == "ON" ? "Desactivation" : "Reactivation") + " des capteurs !", LOG_LEVEL_DEBUG)
			for cleCapteurs: capteurs.keys()
				capteurs[cleCapteurs]["activation"] = (etat == "ON" ? "OFF" : "ON")
			end	
		end
	end
end
globalFonctions.modifEtatRelai = globalFonctions_modifEtatRelai

# Aide de la commande ReglageGlobal, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def globalFonctions_aideReglageGlobal(sujet)
    import string
    if (sujet == nil)
        return [
            ["afficheMemoire", "afficheMemoire", "affiche l'etat de la memoire dans les logs"],
            ["nbLogsFiles", "nbLogsFiles <n>", "regle le nombre de fichiers de logs (FileLog), sauvegarde"],
            ["logLevel", "logLevel <0..4>", "regle le niveau de log serie et web (SerialLog/WebLog), sauvegarde"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "AFFICHEMEMOIRE")
        return ["Parametre : aucun.",
                "Effet : ecrit dans les logs (niveau debug) l'espace programme utilise, la PSRAM",
                "        utilisee (si presente) et le heap libre. Rien n'est sauvegarde.",
                "Exemple : ReglageGlobal afficheMemoire"]
    end
    if (sujet == "NBLOGSFILES")
        return ["Parametre : entier, nombre de fichiers de logs (commande Tasmota FileLog).",
                "Effet : applique 'FileLog <n>' puis memorise la valeur (diverses logs nbLogsFiles)",
                "        et sauvegarde (persist.save). Parametre absent ou non entier : ignore.",
                "Exemple : ReglageGlobal nbLogsFiles 14"]
    end
    if (sujet == "LOGLEVEL")
        return ["Parametre : entier de 0 a 4 (niveaux de SerialLog et WebLog de Tasmota).",
                "Effet : applique 'SerialLog <n>' et 'WebLog <n>' puis memorise le niveau",
                "        (diverses logs level) et sauvegarde (persist.save).",
                "        Parametre absent ou non entier : ignore.",
                "Exemple : ReglageGlobal logLevel 3"]
    end
    return nil
end
globalFonctions.aideReglageGlobal = globalFonctions_aideReglageGlobal

# exemples: 
# ReglageGlobal afficheMemoire
# ReglageGlobal nbLogsFiles 14
# (les niveaux de logs se reglent par ReglageLog : voir logFonctions.be)
def globalFonctions_reglageGlobal(cmd, idx, payload, payload_json)
    import string
    import json
    import mqtt
    import gestionFileFolder
	import persist
    import diversFonctions
    if diversFonctions.traiteAide("ReglageGlobal", payload, globalFonctions.aideReglageGlobal, true)    return    end


    var fonction = false
    var parametres = []
    var reponse_cmnd = {}
    
    # Test   
    logFonctions.log("REGLAGE_GLOBAL: -------------------- reglageGlobal -------------------", LOG_LEVEL_DEBUG_PLUS)
    logFonctions.log("REGLAGE_GLOBAL: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    logFonctions.log("REGLAGE_GLOBAL: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    logFonctions.log("REGLAGE_GLOBAL: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    logFonctions.log("REGLAGE_GLOBAL: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    logFonctions.log("REGLAGE_GLOBAL: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
	if (parametres != false)
		if (parametres.size() > 0)	logFonctions.log("REGLAGE_GLOBAL: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
		if (parametres.size() > 1)	logFonctions.log("REGLAGE_GLOBAL: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end
	end

    if string.toupper(fonction) == "AFFICHEMEMOIRE"
        diversFonctions.statMemory()          # importe en tete de fonction (un 2e import = redefinition en strict)
	elif string.toupper(fonction) == string.toupper("nbLogsFiles")
        try
            # Sauvegarde le paramètre
			tasmota.cmd(string.format("FileLog %i", int(parametres[0])), boolMute)
            diverses["logs"]["nbLogsFiles"] = int(parametres[0])
            persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
	end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd = "ReglageGlobal: Affiche les statistiques de la mémoire"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
globalFonctions.reglageGlobal = globalFonctions_reglageGlobal

# Retourne le module lors de l'importation
return globalFonctions