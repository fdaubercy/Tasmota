# Définition du module
var configModules = module("/configModules")

# Parcours soit les 'modules', soit les 'drivers' paramétrés dans le json
# @typologie = paragraphe parcouru dans le json -> "modules" ou "drivers"
configModules.configDevicesByJon = def(typologie, gpioPinUtilises, ordreGPIO, template, nbIOActivesJSON)
	import string

	var typeApp
	var id = 0
	var pin = 0
	var pos = 0
	var enregistrePersistant = false
	var reponseCMD

	var types = (typologie == "modules" ? modules : drivers)
	if types.find("activation", "ON") == "ON"
		log(string.format("CONTROLE_GENERAL: Paramètre les éléments non-spécifiques à certains %s !", typologie), LOG_LEVEL_DEBUG)
		for cleType: types.keys()
			if (type(types[cleType]) != "instance")	continue 	end	
			tasmota.yield()

			# Si le module est activé
			if types[cleType]["activation"] == "ON"				# ex: ["modules"]["cuve"]["activation"]
				# Parcours les capteurs génériques des modules, dans le modele et sur interface web en fonction des persist.json :
				# 	- Paramètre les relais 
				# 	- Paramètre les capteurs ou interrupteurs (Switch)
				# 	- Paramètre les boutons (Button)
				# 	- Paramètre les Capteurs Hygro/Thermo DHT22
				# 	- Paramètre le pin, le type & le numero des LED et LEDLink
				# Parcours les capteurs spécifques des modules

				# Active ou non la LED de status et définie son niveau
				if cleType == "leds"
					var ledPower = types[cleType].find("ledPower", "OFF")

					if tasmota.cmd("LedPower", boolMute)["LedPower1"] != ledPower
						log(string.format("CONTROLE_GENERAL: %s ledPower !", (ledPower=="ON" ? "Active" : "Desactive")), LOG_LEVEL_DEBUG)
						tasmota.cmd(string.format("Backlog LedPower %i; SetOption31 %s;", (ledPower=="ON" ? 1 : 0), (ledPower=="ON" ? "OFF" : "ON")), boolMute)
					end	
					if types[cleType].find("ledState", 0) != 8
						tasmota.cmd(string.format("LedState %i", types[cleType]["ledState"]), boolMute)
					end
				end

				# print(">>>>>>>>>>>>>>>>>>" + typologie + " : cleType=" + str(cleType) + " -> activation=" + types[cleType]["activation"])

				var env = types[cleType]["environnement"]			# ex: env = ["modules"]["cuve"]["environnement"]
				for cleDevices: env.keys()								# ex: cleDevices = ["modules"]["cuve"]["environnement"]["analogiques"]
					if (type(env[cleDevices]) != "instance")	continue	end	
					tasmota.yield()

					# print(">>>>>>>>>>>>>>>>>> cleType=" + str(cleType) + " -> activation=" + types[cleType]["activation"] + 
					# 				" / cleDevices=" + str(cleDevices) + " -> activation=" + env[cleDevices].find("activation", "ON"))

					# Compte le nombre de devices dans chaque piece de l'environnement
					var j = 0
					for cleDev: env[cleDevices].keys()
						if type(env[cleDevices][cleDev]) != "instance"	continue	end		# ex: cleDev = ["modules"]["cuve"]["environnement"]["analogiques"]["analogique1"]
						j += 1
					end

					if env[cleDevices].find("activation", "ON") == "OFF"
						# On stoppe la boucle 'for cleDevices: env.keys()' et passe aux devices d'environnement suivantes
						if (typologie == "drivers")
							break
						elif (typologie == "modules")
							continue
						end
					else log(string.format("CONFIG_GLOBAL: Parametre les %i %s du module %s !", j, cleDevices, cleType), LOG_LEVEL_DEBUG)
					end

					for cleDev: env[cleDevices].keys()
						if (type(env[cleDevices][cleDev]) != "instance")	continue	end	# ex: cleDev = ["modules"]["cuve"]["activation"]["environnement"]["analogiques"]["activation"]	
						tasmota.yield()
						
						typeApp = ""
						# ex: cleDev = ["modules"]["cuve"]["environnement"]["analogiques"]["analogique1"]	
						if env[cleDevices][cleDev].find("activation", "OFF") == "ON" && ((env[cleDevices][cleDev].find("pin", -1) != -1  && env[cleDevices][cleDev].find("virtuel", "OFF") == "OFF") || env[cleDevices][cleDev].find("virtuel", "OFF") != "OFF")
							# Uniquement si pin != -1 & type != ""
							id = int(env[cleDevices][cleDev].find("id", 1))
							pin = env[cleDevices][cleDev]["pin"]

							# Ne prends pas en commpte l'id pour le paramétrage des leds ws2812
							# Paramètre le nombre de leds de la bande WS2812
							if (env[cleDevices][cleDev]["type"] == 1376)
								# Change l'ID en fonction du nombre de relais car le relai de led est toujours le dernier
								# Les leds WS2812 comptent dans les leds et les relais
                                #- Obsolète
                                    id = nbIOActivesJSON["WS2812"]["actives"].find("nb", 0) + env[cleDevices][cleDev]["channel"]
                                    if (id != int(env[cleDevices][cleDev].find("id", 1)))
                                        enregistrePersistant = true
                                    end
                                -#
								typeApp = int(env[cleDevices][cleDev]["type"] + env[cleDevices][cleDev]["channel"] + 1 - 1)

								reponseCMD = tasmota.cmd("Pixels", boolMute).find("Pixels", false)
								if (reponseCMD && (int(reponseCMD) != env[cleDevices][cleDev]["nbLeds"]))
									log(string.format("CONFIG_GLOBAL: Parametrage du nombre de LED du bandeau WS2812 = %i LEDs!", id, env[cleDevices][cleDev]["nbLeds"]), LOG_LEVEL_DEBUG)
									tasmota.cmd(string.format("Pixels %i", env[cleDevices][cleDev]["nbLeds"]), boolMute)
								end
							else	typeApp = int(env[cleDevices][cleDev]["type"]) + id - 1
							end

							# print(">>>>>>>>>>>>>>>>>>" + cleDev + " : GPIO" + str(pin) + " -> " + str(template["GPIO"][pos]) + " / " + str(typeApp))

							if pin != -1 && typeApp != ""	
								# Ajoute au tableau des pins utilisés
								gpioPinUtilises.push("GPIO" + str(pin))	
								
								# Repérer la place du GPIO dans le modèle
								# log("ordreGPIO.size()=" + str(ordreGPIO.size()), LOG_LEVEL_DEBUG_PLUS)
								for i: 0 .. ordreGPIO.size() - 1
									if ordreGPIO[i] == "GPIO" + str(pin)
										pos = i
										break
									end
								end			
								
								# print(">>>>>>>>>>>>>>>>>>" + cleDev + " : GPIO" + str(pin) + " -> " + str(template["GPIO"][pos]) + " / " + str(typeApp))
								
								if template["GPIO"][pos] != typeApp
									template["GPIO"][pos] = typeApp
									log(string.format("CONFIG_GLOBAL: Modifie en json le type de %s = %i !", cleDev, int(typeApp) + id - 1), LOG_LEVEL_DEBUG)
									
									enregistrePersistant = true
								end		
							end

							# Paramètre le nom des relais et WS2812
							if cleDevices == "relais"
								if env[cleDevices][cleDev]["nom"] != ""
                                    # print(">>>>>>>>>>>>>>>>>>id" + str(id))
									# print(">>>>>>>>>>>>>>>>>>" + typologie + " : Relai " + str(id) + " -> nom en json=" + env[cleDevices][cleDev]["nom"] + " / WebButton" + str(id) + "=" + tasmota.cmd(string.format("WebButton%i", id), boolMute)[string.format("WebButton%i", id)] + " / Différence=" + str(tasmota.cmd(string.format("WebButton%i", id), boolMute)[string.format("WebButton%i", id)] != env[cleDevices][cleDev]["nom"]))
								
									if tasmota.cmd(string.format("WebButton%i", id), boolMute)[string.format("WebButton%i", id)] != env[cleDevices][cleDev]["nom"]
										log(string.format("CONFIG_GLOBAL: Modifie sur WebUI le nom " + 
																	(env[cleDevices][cleDev]["type"] == 1376 ? "de la LED WS2812" : "du Relai") + " %i = %s !", 
																	id, env[cleDevices][cleDev]["nom"]), LOG_LEVEL_DEBUG)
										tasmota.cmd(string.format("WebButton%i %s", id, env[cleDevices][cleDev]["nom"]), boolMute)
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
							# Paramètre le nom d'alias des DS18B20
							elif cleDevices == "thermometres"
								if (env[cleDevices][cleDev]["type"] == 1312)
									reponseCMD = tasmota.cmd(string.format("Ds18Alias %s, DS18B20-%i", env[cleDevices][cleDev]["serialNumber"], env[cleDevices][cleDev]["id"]), boolMute).find(string.format("DS18B20-%i", env[cleDevices][cleDev]["id"]), "")
									if reponseCMD == env[cleDevices][cleDev]["serialNumber"]
										log(string.format("CONFIG_GLOBAL: Parametrage de l'alias du DS18B20 n°%i = Ds18Alias %s, DS18B20-%i !", env[cleDevices][cleDev]["id"], env[cleDevices][cleDev]["serialNumber"], env[cleDevices][cleDev]["id"]), LOG_LEVEL_DEBUG)
									end
								end
							end
                        end
                    end
                end
            end
        end
    end

    return enregistrePersistant
end

# Retourne le module lors de l'importation
return configModules