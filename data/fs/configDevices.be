# Définition du module
var configDevices = module("/configDevices")

# Parcours tous les modules activés paramétrés
# Paramètre les règles pour chaque type de device: add_rule -> changementEtatCapteur
# Compte le nombre de devices activées & réelles par type 
# Enregistre les paramètres dans le fichier '/json/nbIO.json'
# Paramètre l'affichage ou non de la valeur du capteur sur webUI
# Active ou non le Driver Tasmota dédié
configDevices.configDevicesByRules = def(modules, nbIOActivesJSON)
    import gestionFileFolder
    # import introspect
    import string
    import json
    import globalFonctions
	import re

    for cleModule: modules.keys()
		tasmota.yield()
		
        if (type(modules[cleModule]) != "instance")   continue      end

		# Crée le fichier JSON s'il n'existe pas
		if (!nbIOActivesJSON.find("WS2812", false))		nbIOActivesJSON.insert("WS2812", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end
		if (!nbIOActivesJSON.find("relais", false))		nbIOActivesJSON.insert("relais", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end
		if (!nbIOActivesJSON.find("switchs", false))	nbIOActivesJSON.insert("switchs", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end
		if (!nbIOActivesJSON.find("capteurs", false))	nbIOActivesJSON.insert("capteurs", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end
		if (!nbIOActivesJSON.find("boutons", false))	nbIOActivesJSON.insert("boutons", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end
		if (!nbIOActivesJSON.find("analogiques", false))	nbIOActivesJSON.insert("analogiques", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end
		if (!nbIOActivesJSON.find("thermometres", false))	nbIOActivesJSON.insert("thermometres", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end
		if (!nbIOActivesJSON.find("compteurs", false))	nbIOActivesJSON.insert("compteurs", {"actives": {"nb": 0}, "reels": {"nb": 0}})	end

        # Si le module est activé
        if modules[cleModule].find("activation", "OFF") == "ON"
        	var env = modules[cleModule]["environnement"]
  
        	var relais = env.find("relais", false)
        	if (relais)
        		for cleRLY: relais.keys()
        			if type(relais[cleRLY]) != "instance"   continue    end
					tasmota.yield()

        			# Si le relai est activé (réels + virtuels)
        			if relais[cleRLY].find("activation", "OFF") == "ON" && ((relais[cleRLY].find("pin", -1) != -1  && relais[cleRLY].find("virtuel", "OFF") == "OFF") || relais[cleRLY].find("virtuel", "OFF") != "OFF")
        				relais[cleRLY]["timestamp"]["nbCyclesJour"] = 0 
        				if relais[cleRLY]["timestamp"]["ON"] == 0 relais[cleRLY]["timestamp"]["ON"] = tasmota.rtc()["local"] end
        				if relais[cleRLY]["timestamp"]["OFF"] == 0 relais[cleRLY]["timestamp"]["OFF"] = tasmota.rtc()["local"] end

                        # Nb de relais et WS2812 (non-virtuels)
                        if (relais[cleRLY].find("activation", "OFF") == "ON" && relais[cleRLY].find("virtuel", "OFF") == "OFF")
							nbIOActivesJSON["relais"]["actives"]["nb"] = nbIOActivesJSON["relais"]["actives"].find("nb", 0) + 1
							nbIOActivesJSON["relais"]["reels"]["nb"] = nbIOActivesJSON["relais"]["reels"].find("nb", 0) + 1
							if (relais[cleRLY]["type"] == 1376)		
								nbIOActivesJSON["WS2812"]["actives"]["nb"] = nbIOActivesJSON["WS2812"]["actives"].find("nb", 0) + 1	
								nbIOActivesJSON["WS2812"]["reels"]["nb"] = nbIOActivesJSON["WS2812"]["reels"].find("nb", 0) + 1		
							end
						# Pour les relais & LEDs WS2812 (virtuels)
						elif (relais[cleRLY].find("virtuel", "OFF") != "OFF")
							# L'état des relais & LEDs WS2812 virtuels n'est pas rappelés nativement par tasmota
							if (relais[cleRLY]["etat"] == "ON")
								tasmota.set_power(relais[cleRLY]["id"] - 1, true)
								if (relais[cleRLY]["type"] == 1376)
									light.set({"power": (relais[cleRLY]["etat"] == "ON" ? true : false), "hue":relais[cleRLY].find("couleur", 0), "bri":relais[cleRLY].find("value", 0), "sat":relais[cleRLY].find("saturation", 0)})
								end
							end

							if (relais[cleRLY]["virtuel"] == "I2C_MCP23017")
								var result = tasmota.cmd("I2CScan", boolMute)
								# Si les connexions I2C sont activées dans le firmware et les ports I2C configurés
								if (result.contains("I2CScan"))
									# Module MCP23017 connecté
									if (string.find(result["I2CScan"], str(drivers["I2C"]["environnement"]["MCP23017"]["adresseI2C"])) > -1)
										nbIOActivesJSON["relais"]["actives"]["nb"] = nbIOActivesJSON["relais"]["actives"].find("nb", 0) + 1
										if (relais[cleRLY]["type"] == 1376)
											nbIOActivesJSON["WS2812"]["actives"]["nb"] = nbIOActivesJSON["WS2812"]["actives"].find("nb", 0) + 1	
										end
									else log(string.format("CONFIG_DEV_BY_RULES: Le MCP23017 n'est pas connecté: Le relai %i ne sera pas comptabilisé !", relais[cleRLY]["id"]), LOG_LEVEL_DEBUG_PLUS)
									end
								elif (result.contains("Command"))
									if (result["Command"] == "Error")
										log(string.format("CONFIG_DEV_BY_RULES: Le bus I2C n'est pas activé dans le firmware ou les ports I2C ne sont pas configurés !"), LOG_LEVEL_ERREUR)
									end
								end
							elif (string.find(relais[cleRLY]["virtuel"], "ModBus_Conn16channel") > - 1)
								# Module ModBus activé
								if (drivers["ModBus"]["activation"] == "ON" && drivers["ModBus"]["environnement"]["Conn16channels"][string.split(relais[cleRLY]["virtuel"], "_")[1]]["activation"] == "ON")
									nbIOActivesJSON["relais"]["actives"]["nb"] = nbIOActivesJSON["relais"]["actives"].find("nb", 0) + 1
									if (relais[cleRLY]["type"] == 1376)
										nbIOActivesJSON["WS2812"]["actives"]["nb"] = nbIOActivesJSON["WS2812"]["actives"].find("nb", 0) + 1	
									end
								else log(string.format("CONFIG_DEV_BY_RULES: Le controle du ModBus et l'esclave ModBus %i ne sont pas activés !", drivers["ModBus"]["environnement"]["Conn16channels"][string.split(relais[cleRLY]["virtuel"], "_")[1]]["id"]), LOG_LEVEL_DEBUG_PLUS)
								end									
							elif (string.find(relais[cleRLY]["virtuel"], "ModBus_TasmotaSlaveModBus") > - 1)
								# Module ModBus activé
								if (drivers["ModBus"]["activation"] == "ON" && drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][string.split(relais[cleRLY]["virtuel"], "_")[1]]["activation"] == "ON")
									nbIOActivesJSON["relais"]["actives"]["nb"] = nbIOActivesJSON["relais"]["actives"].find("nb", 0) + 1
									if (relais[cleRLY]["type"] == 1376)
										nbIOActivesJSON["WS2812"]["actives"]["nb"] = nbIOActivesJSON["WS2812"]["actives"].find("nb", 0) + 1	
									end
								else log(string.format("CONFIG_DEV_BY_RULES: Le controle du ModBus et l'esclave ModBus %i ne sont pas activés !", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][string.split(relais[cleRLY]["virtuel"], "_")[1]]["id"]), LOG_LEVEL_DEBUG_PLUS)
								end
							end
						end

						# Règle pour toutes les LEDs WS2812 réelles
						# Les changements d'état des relais réels et virtuels sont gérés par la fonction 'controleGeneral.set_power_handler()'
						if (nbIOActivesJSON["WS2812"]["reels"].find("nb", 0) > 0)
							if (relais[cleRLY]["type"] == 1376)	
								tasmota.remove_rule("Dimmer")
								tasmota.add_rule("Dimmer", def(value, trigger, msg) globalFonctions.changementEtatWS2812(value, trigger, msg, cleModule, cleRLY) end)				
							
								tasmota.remove_rule(string.format("Dimmer%i", relais[cleRLY]["id"]))
								tasmota.add_rule(string.format("Dimmer%i", relais[cleRLY]["id"]), def(value, trigger, msg) globalFonctions.changementEtatWS2812(value, trigger, msg, cleModule, cleRLY) end)				
							end
						end
					end
        		end

				# Actualise le nombre de relais activés
				tasmota.global.devices_present = nbIOActivesJSON["relais"]["actives"]["nb"]
        	end

			# Les capteurs tout ou rien sont aussi des interrupteurs
        	var capteurs = env.find("capteurs", false)	
        	if (capteurs)
        		for cleCapteurs: capteurs.keys()
        			if type(capteurs[cleCapteurs]) != "instance"    continue    end
					tasmota.yield()

        			if capteurs[cleCapteurs].find("activation", "OFF") == "ON" && ((capteurs[cleCapteurs].find("pin", -1) != -1  && capteurs[cleCapteurs].find("virtuel", "OFF") == "OFF") || capteurs[cleCapteurs].find("virtuel", "OFF") != "OFF")
        				nbIOActivesJSON["capteurs"]["actives"]["nb"] = nbIOActivesJSON["capteurs"]["actives"].find("nb", 0) + 1

                        # Nb de capteurs réels (non-virtuels)
                        if capteurs[cleCapteurs].find("activation", "OFF") == "ON" && capteurs[cleCapteurs].find("virtuel", "OFF") == "OFF"
                            nbIOActivesJSON["capteurs"]["reels"]["nb"] = nbIOActivesJSON["capteurs"]["reels"].find("nb", 0) + 1
                        end

						# Règle pour toutes les capteurs réels
						if (nbIOActivesJSON["capteurs"]["reels"].find("nb", 0) > 0)
							tasmota.remove_rule(string.format("Switch%i#Action", capteurs[cleCapteurs]["id"]))
        					tasmota.add_rule(string.format("Switch%i#Action", capteurs[cleCapteurs]["id"]), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleCapteurs) end)				
						end
					end
        		end
        	end

        	var interrupteurs = env.find("interrupteurs", false)
        	if (interrupteurs)
        		for cleInterrupteurs: interrupteurs.keys()
        			if type(interrupteurs[cleInterrupteurs]) != "instance"    continue    end
					tasmota.yield()

        			if interrupteurs[cleInterrupteurs].find("activation", "OFF") == "ON" && ((interrupteurs[cleInterrupteurs].find("pin", -1) != -1  && interrupteurs[cleInterrupteurs].find("virtuel", "OFF") == "OFF") || interrupteurs[cleInterrupteurs].find("virtuel", "OFF") != "OFF")
        				nbIOActivesJSON["switchs"]["actives"]["nb"] = nbIOActivesJSON["switchs"]["actives"].find("nb", 0) + 1

                        # Nb d'interrupteurs réels (non-virtuels)
                        if interrupteurs[cleInterrupteurs].find("activation", "OFF") == "ON" && interrupteurs[cleInterrupteurs].find("virtuel", "OFF") == "OFF"
                            nbIOActivesJSON["switchs"]["reels"]["nb"] = nbIOActivesJSON["switchs"]["reels"].find("nb", 0) + 1
                        end

						# Règle pour toutes les interrupteurs réels
						if (nbIOActivesJSON["switchs"]["reels"].find("nb", 0) > 0)
							tasmota.remove_rule(string.format("Switch%i#Action", interrupteurs[cleInterrupteurs]["id"]))
        					tasmota.add_rule(string.format("Switch%i#Action", interrupteurs[cleInterrupteurs]["id"]), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleInterrupteurs) end)	
						end
					end
        		end
        	end
 
        	var boutons = env.find("boutons", false)
        	if (boutons)
        		for cleBoutons: boutons.keys()
        			if type(boutons[cleBoutons]) != "instance"  continue    end
					tasmota.yield()

        			if boutons[cleBoutons].find("activation", "OFF") == "ON" && ((boutons[cleBoutons].find("pin", -1) != -1  && boutons[cleBoutons].find("virtuel", "OFF") == "OFF") || boutons[cleBoutons].find("virtuel", "OFF") != "OFF")
        				nbIOActivesJSON["boutons"]["actives"]["nb"] = nbIOActivesJSON["boutons"]["actives"].find("nb", 0) + 1

                        # Nb de boutons réels (non-virtuels)
                        if boutons[cleBoutons].find("activation", "OFF") == "ON" && boutons[cleBoutons].find("virtuel", "OFF") == "OFF"
                            nbIOActivesJSON["boutons"]["reels"]["nb"] = nbIOActivesJSON["boutons"]["reels"].find("nb", 0) + 1
                        end

						# Règle pour toutes les boutons réels
						if (nbIOActivesJSON["boutons"]["reels"].find("nb", 0) > 0)
        					tasmota.remove_rule(string.format("Button%i#Action", boutons[cleBoutons]["id"]))
        					tasmota.add_rule(string.format("Button%i#Action", boutons[cleBoutons]["id"]), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleBoutons) end)
						end
					end									
        		end
        	end

            var analogiques = env.find("analogiques", false)
        	if (analogiques)
        		for cleAnalogiques: analogiques.keys()
        			if type(analogiques[cleAnalogiques]) != "instance"  continue    end
					tasmota.yield()

        			if analogiques[cleAnalogiques].find("activation", "OFF") == "ON" && ((analogiques[cleAnalogiques].find("pin", -1) != -1  && analogiques[cleAnalogiques].find("virtuel", "OFF") == "OFF") || analogiques[cleAnalogiques].find("virtuel", "OFF") != "OFF")
						# Pour les entrées analogiques virtuelles de type ADS1115
						if (analogiques[cleAnalogiques].find("virtuel", "OFF") != "OFF")
							if (analogiques[cleAnalogiques]["virtuel"] == "I2C_ADS1115")
								var result = tasmota.cmd("I2CScan", boolMute)
								# Si les connexions I2C sont activées dans le firmware et les ports I2C configurés
								if (result.contains("I2CScan"))
									# Module ADS1115 connecté
									if (string.find(result["I2CScan"], str(drivers["I2C"]["environnement"]["ADS1115"]["adresseI2C"])) > -1)
										nbIOActivesJSON["analogiques"]["actives"]["nb"] = nbIOActivesJSON["analogiques"]["actives"].find("nb", 0) + 1
									else 
										log(string.format("CONFIG_DEV_BY_RULES: L'ADS1115 n'est pas connecté: L'entrée analogique %i ne sera pas comptabilisée !", analogiques[cleAnalogiques]["id"]), LOG_LEVEL_DEBUG_PLUS)
									end
								elif (result.contains("Command"))
									if (result["Command"] == "Error")
										log(string.format("CONFIG_DEV_BY_RULES: Le bus I2C n'est pas activé dans le firmware ou les ports I2C ne sont pas configurés !"), LOG_LEVEL_ERREUR)
									end
								end
							elif (string.find(analogiques[cleAnalogiques]["virtuel"], "ModBus_TasmotaSlaveModBus") > - 1)
								if (drivers["ModBus"].find("activation", "OFF") == "ON" && drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"][string.split(analogiques[cleAnalogiques]["virtuel"], "_")[1]].find("activation", "OFF") == "ON")
									nbIOActivesJSON["analogiques"]["actives"]["nb"] = nbIOActivesJSON["analogiques"]["actives"].find("nb", 0) + 1
								else 
									log(string.format("CONFIG_DEV_BY_RULES: %s n'est pas activé: L'entrée analogique %i ne sera pas comptabilisée !", string.split(analogiques[cleAnalogiques]["virtuel"], "_")[1], analogiques[cleAnalogiques]["id"]), LOG_LEVEL_DEBUG_PLUS)
								end								
							end
						else 
							nbIOActivesJSON["analogiques"]["actives"]["nb"] = nbIOActivesJSON["analogiques"]["actives"].find("nb", 0) + 1
						end

                        # Nb d'entrées analogiques réelles (non-virtuels)
                        if (nbIOActivesJSON["analogiques"]["reels"].find("nb", 0) > 0)
                            nbIOActivesJSON["analogiques"]["reels"]["nb"] = nbIOActivesJSON["analogiques"]["reels"].find("nb", 0) + 1
                        end

						# Pour les entrées analogiques réelles
						if (nbIOActivesJSON["analogiques"]["reels"].find("nb", 0) > 0)
							tasmota.remove_rule(string.format("ANALOG#A%d", analogiques[cleAnalogiques]["id"] - 1))
							tasmota.add_rule(string.format("ANALOG#A%d", analogiques[cleAnalogiques]["id"] - 1), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleAnalogiques) end)
						end

						# Pour les entrées analogiques virtuelles
						if (nbIOActivesJSON["analogiques"]["actives"].find("nb", 0) > nbIOActivesJSON["analogiques"]["reels"].find("nb", 0))
                            # var typeConnex = string.split(analogiques[cleAnalogiques]["virtuel"], "_")[0]
                            var moduleConnex = string.split(analogiques[cleAnalogiques]["virtuel"], "_")[1]
                            var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", moduleConnex)[0]

							# Virtuels de type ADS1115
							if (moduleConnex == "ADS1115")
								tasmota.remove_rule(string.format("Tele#ADS1115#A%d", analogiques[cleAnalogiques]["id"] - 1))
								tasmota.add_rule(string.format("Tele#ADS1115#A%d", analogiques[cleAnalogiques]["id"] - 1), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleAnalogiques) end)
							end

							# Virtuels de type TasmotaSlaveModBus
							if (groupeConnex == "TasmotaSlaveModBus")
								tasmota.remove_rule(string.format("Tele#TasmotaSlaveModBus#%s#ANALOG#A%d", moduleConnex, analogiques[cleAnalogiques]["id"]))
								tasmota.add_rule(string.format("Tele#TasmotaSlaveModBus#%s#ANALOG#A%d", moduleConnex, analogiques[cleAnalogiques]["id"]), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleAnalogiques) end)
							end
						end
					end									
        		end
        	end

            var thermos = env.find("thermometres", false)
			if (thermos)
				for cleTH: thermos.keys()
					if type(thermos[cleTH]) != "instance"  continue    end
					tasmota.yield()

					if thermos[cleTH].find("activation", "OFF") == "ON" && ((thermos[cleTH].find("pin", -1) != -1  && thermos[cleTH].find("virtuel", "OFF") == "OFF") || thermos[cleTH].find("virtuel", "OFF") != "OFF")
						nbIOActivesJSON["thermometres"]["actives"]["nb"] = nbIOActivesJSON["thermometres"]["actives"].find("nb", 0) + 1

                        # Nb de thermometres réels (non-virtuels)
                        if thermos[cleTH].find("activation", "OFF") == "ON" && thermos[cleTH].find("virtuel", "OFF") == "OFF"
                            nbIOActivesJSON["thermometres"]["reels"]["nb"] = nbIOActivesJSON["thermometres"]["reels"].find("nb", 0) + 1
                        end
						
						# Pour les thermomètres réels
						if (nbIOActivesJSON["thermometres"]["reels"].find("nb", 0) > 0)
							# DHT22 (AM2302)
							if (thermos[cleTH]["type"] == 1216)
								tasmota.add_rule("Tele#AM2301#Humidity", def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleTH) end)
								tasmota.add_rule("Tele#AM2301#Temperature", def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleTH) end)
							# DS18B20
							elif (thermos[cleTH]["type"] == 1312)
								tasmota.add_rule(string.format("Tele#DS18B20-%i#Temperature", thermos[cleTH]["id"]), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleTH) end)
							end
						end

						# Pour les thermomètres virtuelles
						if (nbIOActivesJSON["thermometres"]["actives"].find("nb", 0) > nbIOActivesJSON["thermometres"]["reels"].find("nb", 0))
                            # var typeConnex = string.split(analogiques[cleAnalogiques]["virtuel"], "_")[0]
                            var moduleConnex = string.split(thermos[cleTH]["virtuel"], "_")[1]
                            var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", moduleConnex)[0]

							# Virtuels de type TasmotaSlaveModBus
							if (groupeConnex == "TasmotaSlaveModBus")
								# DHT22 (AM2302)
								if (thermos[cleTH]["type"] == 1216)
									tasmota.remove_rule(string.format("Tele#TasmotaSlaveModBus#%s#Temperatures#AM2301#Humidity", moduleConnex))
									tasmota.add_rule(string.format("Tele#TasmotaSlaveModBus#%s#Temperatures#AM2301#Humidity", moduleConnex), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleTH) end)
									
									tasmota.remove_rule(string.format("Tele#TasmotaSlaveModBus#%s#Temperatures#AM2301#Temperature", moduleConnex))
									tasmota.add_rule(string.format("Tele#TasmotaSlaveModBus#%s#Temperatures#AM2301#Temperature", moduleConnex), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleTH) end)
								# DS18B20
								elif (thermos[cleTH]["type"] == 1312)
									tasmota.remove_rule(string.format("Tele#TasmotaSlaveModBus#%s#Temperatures#DS18B20-%i#Temperature", moduleConnex, thermos[cleTH]["id"]))
									tasmota.add_rule(string.format("Tele#TasmotaSlaveModBus#%s#Temperatures#DS18B20-%i#Temperature", moduleConnex, thermos[cleTH]["id"]), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleTH) end)
								end
							end
						end
					end									
				end
			end

			var compteurs = env.find("compteurs", false)
			if (compteurs)
				for cleCompt: compteurs.keys()
					if type(compteurs[cleCompt]) != "instance"  continue    end
					tasmota.yield()

					if compteurs[cleCompt].find("activation", "OFF") == "ON" && ((compteurs[cleCompt].find("pin", -1) != -1  && compteurs[cleCompt].find("virtuel", "OFF") == "OFF") || compteurs[cleCompt].find("virtuel", "OFF") != "OFF")
						nbIOActivesJSON["compteurs"]["actives"]["nb"] = nbIOActivesJSON["compteurs"]["actives"].find("nb", 0) + 1

                        # Nb de compteurs réels (non-virtuels)
                        if compteurs[cleCompt].find("activation", "OFF") == "ON" && compteurs[cleCompt].find("virtuel", "OFF") == "OFF"
                            nbIOActivesJSON["compteurs"]["reels"]["nb"] = nbIOActivesJSON["compteurs"]["reels"].find("nb", 0) + 1
                        end

						# Pour les compteurs réels
						if (nbIOActivesJSON["compteurs"]["reels"].find("nb", 0) > 0)
							tasmota.add_rule("Tele#COUNTER#C", def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleCompt) end)
						end

						# Pour les compteurs virtuels
						if (nbIOActivesJSON["compteurs"]["actives"].find("nb", 0) > nbIOActivesJSON["compteurs"]["reels"].find("nb", 0))
                            # var typeConnex = string.split(analogiques[cleAnalogiques]["virtuel"], "_")[0]
                            var moduleConnex = string.split(compteurs[cleCompt]["virtuel"], "_")[1]
                            var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", moduleConnex)[0]

							# Virtuels de type TasmotaSlaveModBus
							if (groupeConnex == "TasmotaSlaveModBus")
								tasmota.remove_rule(string.format("Tele#TasmotaSlaveModBus#%s#COUNTER#C%d", moduleConnex, compteurs[cleCompt]["id"]))
								tasmota.add_rule(string.format("Tele#TasmotaSlaveModBus#%s#COUNTER#C%d", moduleConnex, compteurs[cleCompt]["id"]), def(value, trigger, msg) globalFonctions.changementEtatCapteur(value, trigger, msg, cleModule, cleCompt) end)
							end
						end
					end
				end
			end

        	# Enregistre ou Mets à jour en variable les capteurs activés dans un tableaus
            try
                var temp = gestionFileFolder.readFile("/json/nbIOActives.json")
                if (temp != json.dump(nbIOActivesJSON))
                    gestionFileFolder.writeFile("/json/nbIOActives.json", json.dump(nbIOActivesJSON))
                end
			except .. as error, message
                gestionFileFolder.writeFile("/nbIOActives.json", json.dump(nbIOActivesJSON))
                gestionFileFolder.listeEtRepartitLesFichiers()

                log(string.format("CONFIG_DEVICES_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
			end
        end
    end

	tasmota.yield()

	# Détache ou attache les boutons et switchs si activés >= 1
	if nbIOActivesJSON["switchs"]["actives"].find("nb", 0) > 0
		if tasmota.cmd("SetOption114", boolMute)["SetOption114"] != "ON"
			log("CONFIG_DEVICES: Detache tous les switchs !", LOG_LEVEL_DEBUG)
			tasmota.cmd("SetOption114 ON", boolMute)		
		end
	else
		if tasmota.cmd("SetOption114", boolMute)["SetOption114"] != "OFF"
			log("CONFIG_DEVICES: Attache tous les switchs !", LOG_LEVEL_DEBUG)
			tasmota.cmd("SetOption114 OFF", boolMute)		
		end	
	end

	tasmota.yield()
			
	# Détache ou attache les interrupteurs & capteurs si activés >= 1
	if nbIOActivesJSON["boutons"]["actives"].find("nb", 0) > 0
		if tasmota.cmd("SetOption73", boolMute)["SetOption73"] != "ON"
			log("CONFIG_DEVICES: Detache tous les boutons !", LOG_LEVEL_DEBUG)
			tasmota.cmd("SetOption73 ON", boolMute)		
		end
	else
		if tasmota.cmd("SetOption73", boolMute)["SetOption73"] != "OFF"
			log("CONFIG_DEVICES: Attache tous les boutons !", LOG_LEVEL_DEBUG)
			tasmota.cmd("SetOption73 OFF", boolMute)		
		end	
	end

	tasmota.yield()

	# Active ou désactive le driver correspondant / Paramètre l'affichage sur page html du capteur
    # Il y a des thermometres actifs
    if nbIOActivesJSON["thermometres"]["actives"].find("nb", 0) > 0
        # Parcours les modules
        for modul: modules.keys()
			if type(modules[modul]) != "instance"  continue    end
			tasmota.yield()

			if (modules[modul].find("activation", false) == "ON")
				var thermos = modules[modul]["environnement"].find("thermometres", false)
				if (thermos)
					# Parcours les thermometres
					for cleTH: thermos.keys()
						if (type(thermos[cleTH]) != "instance")   continue      end
						if (thermos[cleTH]["activation"] == "ON")
							# DS18B20
							if (thermos[cleTH]["type"] == 1312)
								# Vérifie si on doit interdire l'affichage des valeurs de thermometres sur la page html
								tasmota.cmd(string.format("WebSensor5 %s", thermos.find("affichageWebSensor", "ON")), boolMute)
								log(string.format("CONTROLE_GENERAL: Affichage sur WebUI des thermometres = %i !", modules[modul].find("affichageWebSensor", "ON")), LOG_LEVEL_DEBUG)
							# DHT11 ou DHT22
							elif (thermos[cleTH]["type"] == 1216)
								# Vérifie si on doit interdire l'affichage des valeurs de thermometres sur la page html
								tasmota.cmd(string.format("WebSensor6 %s", thermos.find("affichageWebSensor", "ON")), boolMute)
								log(string.format("CONTROLE_GENERAL: Affichage sur WebUI des thermohygrometres = %i !", modules[modul].find("affichageWebSensor", "ON")), LOG_LEVEL_DEBUG)
							end
						end
					end
				end
			end
		end
    end

	# Il y a des compteurs actifs
    if nbIOActivesJSON["compteurs"]["actives"].find("nb", 0) > 0
        # Parcours les modules
        for modul: modules.keys()
			if type(modules[modul]) != "instance"  continue    end
			tasmota.yield()

			if (modules[modul].find("activation", false) == "ON")
				var compteurs = modules[modul]["environnement"].find("compteurs", false)
				if (compteurs)
					# Parcours les compteurs
					for cleCompt: compteurs.keys()
						if (type(compteurs[cleCompt]) != "instance")   continue      end
						if (compteurs[cleCompt]["activation"] == "ON")
							# Vérifie si on doit interdire l'affichage des valeurs de compteurs sur la page html
							tasmota.cmd(string.format("WebSensor1 %s", compteurs.find("affichageWebSensor", "ON")), boolMute)
							log(string.format("CONTROLE_GENERAL: Affichage sur WebUI des compteurs = %i !", modules[modul].find("affichageWebSensor", "ON")), LOG_LEVEL_DEBUG)
						end
					end
				end
			end
		end
    end
end

# Retourne le module lors de l'importation
return configDevices