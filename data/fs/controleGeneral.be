#-  NOTES :
    - Encore penser à paramétrer le module ('template') en fonction du changement de pin du relai dans la page : trappe?action=affichage
        * Types de GPIO enregistrés dans _persist.json sous parametres["componentes"]
        * A paramétrer au démarrage après validation du formulaire html des paramètres : fonction'modifParametres' dans 'globarVar.be'
        * Attention ajouter donc les numeros de relais ou switchs ou boutons dans ce formulaire
        * ex de commande : tasmota.cmd("Template {'NAME':'Example Template','GPIO':[416,0,418,0,417,2720,0,0,2624,32,2656,224,0,0],'FLAG':0,'BASE':0}")
    - Pour tasmota :
        * Bouton (BUTTON) = bouton poussoir
        * Interrupteur (Switch) = Interrupteur
            Gère les actions sur les relais
            Lance le timer si le relai est une relai astable avec timer
            boolCapteurs=true -> si il faut désactiver les capteurs qui gèrent son déclenchement
            boolTimer=true -> si il faut activer le timer
            delaiAvantCommande -> délai avant commande du relai
    - Le réglage de l'heure de la device est réalisé par :
        * connexion à un serveur NTP: diverses["fuseauHoraire"]["typeReglageHeure"] = "NTP"
        * réglage manuel: diverses["fuseauHoraire"]["typeReglageHeure"] = "MANUEL"
        * reglage par module Real Time Clock: diverses["fuseauHoraire"]["typeReglageHeure"] = "RTC"
        * reglage par réception de l'heure par le maitre en UDP: diverses["fuseauHoraire"]["typeReglageHeure"] = "UDP"
-#

class CONTROLE_GENERAL : Driver
    # Variables
	var sensors
	var sensors_valeurAnterieure
	var enregistrePersistant
    var nbIOActivesJSON
	var boolMute

    var flagINIT        # Flag marquant la fin de l'initialisation du module principal
	var connected
	var mqttConnected
    var booted
	var flagTimestampInitialized

	# Se lance chaque jour à minuit
	def heureReboot()
		import string

        log(string.format("CONTROLE_GENERAL: Reboot du module programmé à %s !", diverses["heureReboot"]), LOG_LEVEL_DEBUG)
		tasmota.cmd("Restart 1", boolMute)
	end

	def timerRebootSiDeconnexionWifi()
        import string

        # Teste le Flag de connexion wifi
		if (!self.connected)
            log(string.format("CONTROLE_GENERAL: Reboot du module par deconnexion Wifi !", diverses["heureReboot"]), LOG_LEVEL_DEBUG)
			tasmota.cmd("Restart 1", boolMute)
		end

        # Teste la commande Ping sur le serveur DNS ou IP de la box internet
        # tasmota.cmd("Ping4 {tasmota.cmd('IPAddress4', boolMute)['IPAddress4']:s}", boolMute)
	end

    def init()
        import json
        import string
        import configGlobal
		import globalFonctions
		import configDevices
		import diversFonctions
        import introspect
        
		self.enregistrePersistant = false
        self.nbIOActivesJSON = {}
		self.connected = false
		self.mqttConnected = false
        self.booted = false
        self.flagINIT = 0
		self.flagTimestampInitialized = false

		# Récupère les sensors
		self.sensors = json.load(tasmota.read_sensors())

        log("CONTROLE_GENERAL: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
		# Défini la tache cron pour le reboot sans wifi
		if (serveur["wifi"].find("timerRebootSansWifi", 0) != 0)
            # introspect.get(controleGeneral).heureReboot()
			tasmota.add_cron(string.format("*/%i * * * * *", serveur["wifi"].find("timerRebootSansWifi", 0)), /-> introspect.get(controleGeneral, "timerRebootSiDeconnexionWifi"), "timerRebootSiDeconnexionWifi")
		end

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        tasmota.add_rule("System", globalFonctions.changementEtatDemarrage, "controleGeneral_System")	
        tasmota.add_rule("Wifi", globalFonctions.changementEtatDemarrage, "controleGeneral_Wifi")
        tasmota.add_rule("Mqtt", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleGeneral_Mqtt")
		tasmota.add_rule("Time", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleGeneral_Time")

        #- Parcours tous les modules paramétrés
			* Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
			* Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
					par la fonction 'every_second()'
			* Compte les devices non-virtuelles
			* Compte le nombre de devices activées par type et les range dans un tableau
			* Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
			* Détache ou attache les boutons et switchs si activés >= 1
			* Détache ou attache les interrupteurs & capteurs si activés >= 1
		-#

		# Parcours tous les modules paramétrés
		configDevices.configDevicesByRules(modules, self.nbIOActivesJSON)
		configDevices.configDevicesByRules(drivers, self.nbIOActivesJSON)

		log(string.format("CONTROLE_GENERAL: %i relais activés / %i WS2812 activés / %i switchs activés / %i capteurs activés / %i boutons activés / %i entrées analogiques activées / %i thermometres activés / %i compteurs activés !", 
									self.nbIOActivesJSON["relais"]["actives"].find("nb", 0), self.nbIOActivesJSON["WS2812"]["actives"].find("nb", 0), 
                                    self.nbIOActivesJSON["switchs"]["actives"].find("nb", 0), self.nbIOActivesJSON["capteurs"]["actives"].find("nb", 0), 
									self.nbIOActivesJSON["boutons"]["actives"].find("nb", 0), self.nbIOActivesJSON["analogiques"]["actives"].find("nb", 0), 
									self.nbIOActivesJSON["thermometres"]["actives"].find("nb", 0), self.nbIOActivesJSON["compteurs"]["actives"].find("nb", 0)), LOG_LEVEL_DEBUG)
		log(string.format("CONTROLE_GENERAL: %i relais réels / %i WS2812 réels / %i switchs réels / %i capteurs réels / %i boutons réels / %i entrées analogiques réelles / %i thermometres réels / %i compteurs réels !", 
                                    self.nbIOActivesJSON["relais"]["reels"].find("nb", 0), self.nbIOActivesJSON["WS2812"]["reels"].find("nb", 0), 
                                    self.nbIOActivesJSON["switchs"]["reels"].find("nb", 0), self.nbIOActivesJSON["capteurs"]["reels"].find("nb", 0), 
									self.nbIOActivesJSON["boutons"]["reels"].find("nb", 0), self.nbIOActivesJSON["analogiques"]["reels"].find("nb", 0), 
									self.nbIOActivesJSON["thermometres"]["reels"].find("nb", 0), self.nbIOActivesJSON["compteurs"]["actives"].find("nb", 0)), LOG_LEVEL_DEBUG)

        # Configure le module tasmota (paramètres communs à tous les modules Tasmota)
		configGlobal.configGlobalByJson(self.nbIOActivesJSON)        

        # Ajoute les commandes personnalisées si le module est activé
		tasmota.add_cmd('ReglageGlobal', globalFonctions.reglageGlobal)

		# Stats d'utilisation des mémoires
		diversFonctions.statMemory()

        # Marqueur de fin d'initialisation du module principal
        self.flagINIT = 1
    end

	# Ajoute les capteurs non gérés automatiquement vers la machine de gestion des règles (Si le MQTT n'est pas connecté)
    def every_second()
		import json
		import string

		tasmota.yield()

		# Mets à jours la json self.parametres / 1s
		self.sensors = json.load(tasmota.read_sensors())
		self.sensors_valeurAnterieure = (self.sensors_valeurAnterieure == nil ? self.sensors : self.sensors_valeurAnterieure)

		# Ajoute les capteurs non gérés automatiquement vers la machine de gestion des règles (Si le MQTT n'est pas connecté)
		# Uniquement pour les capteurs réels
		if (serveur["mqtt"]["activation"] != "ON" || !self.mqttConnected)
			if(self.nbIOActivesJSON["switchs"]["reels"].find("nb", 0) > 0)
				for nb: 1 .. self.nbIOActivesJSON["switchs"]["reels"]["nb"]
					if (self.sensors.find("Switch" + str(nb), false))
						if (self.sensors_valeurAnterieure.find("Switch" + str(nb), false))
							if (self.sensors["Switch" + str(nb)] != self.sensors_valeurAnterieure["Switch" + str(nb)])
								tasmota.publish_rule(string.format("{\"Switch%i\": {\"Action\": \"%s\"}}", nb, self.sensors["Switch" + str(nb)]))
							end
						end
					end
				end
			elif(self.nbIOActivesJSON["boutons"]["reels"].find("nb", 0) > 0)
				for nb: 1 .. self.nbIOActivesJSON["boutons"]["reels"]["nb"]
					if (self.sensors.find("Button" + str(nb), false))
						if (self.sensors_valeurAnterieure.find("Button" + str(nb), false))
							if (self.sensors["Button" + str(nb)] != self.sensors_valeurAnterieure["Button" + str(nb)])
								tasmota.publish_rule(string.format("{\"Button%i\": {\"Action\": \"%s\"}}", nb, self.sensors["Button" + str(nb)]))
							end
						end
					end
				end
			elif(self.nbIOActivesJSON["analogiques"]["reels"].find("nb", 0) > 0)

			elif(self.nbIOActivesJSON["thermometres"]["reels"].find("nb", 0) > 0)

			elif(self.nbIOActivesJSON["compteurs"]["reels"].find("nb", 0) > 0)

			end

			# Mets à jours les valeurs antérieures des sensors
			self.sensors_valeurAnterieure = self.sensors
		end
    end

	# Parcours les modules pour detecter les capteurs & boutons qui ne sont pas automatiquement ajouter dans self.sensors
	def json_append()
        import string
		import persist

		var msg = ""
		tasmota.yield()

		# Parcours  les modules pour detecter les capteurs & boutons qui ne sont pas automatiquement ajouter dans self.sensors
		if (self.nbIOActivesJSON.find("boutons",false))
			if self.nbIOActivesJSON["boutons"]["actives"].find("nb", 0) > 0
				for cleModules: modules.keys()
					if type(modules[cleModules]) != "instance"
						continue
					end	

					# Si le module est activé
					var modules = modules[cleModules]
					if modules.find("activation", "OFF") == "ON"
						if (modules["environnement"].find("boutons", false))
							if type(modules["environnement"]["boutons"]) != "instance"
								continue
							end	

							for cleBoutons: modules["environnement"]["boutons"].keys()
								var bouton = modules["environnement"]["boutons"][cleBoutons]

								tasmota.yield()

								if bouton.find("activation", "OFF") == "ON" && ((bouton.find("pin", -1) != -1  && bouton.find("virtuel", "OFF") == "OFF") || bouton.find("virtuel", "OFF") != "OFF")
									#print("Button" + str(bouton))
									msg += ",\"Button" + str(bouton["id"]) + "\": \"" + bouton["etat"] + "\""
								end
							end
						end
					end
				end

				tasmota.response_append(msg)
			end
		end
    end

    #- Création de boutons dans le menu principal -#
	def web_add_main_button()
	end

	#- Se déclenche sur modification d'état d'un relai par l'interface webUI ou commande Power
	        Enregistre le nouvel état des relais en json
	        Enregistre le timestamp de modification d'état en json
	        Enregistre le nb de cycles de modification d'état en json
	        Gère le timer de relai si il y en a un (!=0)
	        Publie l'état du relai sur mqtt sur le topic personnalisé paramétré
     -#
	def set_power_handler(cmd, idx)
		import json
		import mqtt
		import string
		import diversFonctions
		import globalFonctions
		import persist
		import introspect
		import re

		var etat = ""

		tasmota.yield()
		
		log("GLOBAL_POWER_HANDLER: -------------------- global SetPowerHandler -------------------", LOG_LEVEL_DEBUG)
		log("GLOBAL_POWER_HANDLER: Lecture automatisee de l'etat des relais", LOG_LEVEL_DEBUG)
		log("GLOBAL_POWER_HANDLER: cmd=" + str(cmd), LOG_LEVEL_DEBUG)
		log("GLOBAL_POWER_HANDLER: idx=" + str(idx), LOG_LEVEL_DEBUG)
		log("GLOBAL_POWER_HANDLER: idx(binaire)=" + str(diversFonctions.printBinaire(idx)), LOG_LEVEL_DEBUG)

		for nb: 0 .. self.nbIOActivesJSON["relais"]["actives"]["nb"]
			if 1 & (idx >> (nb)) == 1
				etat = "ON"
			else etat = "OFF"
			end

			tasmota.yield()

			# Parcours tous les modules paramétrés
			# tableau = jonction de json sous format tableau
			var tableau = diversFonctions.joinJsonTab(modules, drivers)
			for i: 0 .. tableau.size() - 1
				tasmota.yield()
				
				if tableau[i].find("activation", "OFF") == "ON"
					for cle: tableau[i].keys()
						if (type(tableau[i][cle]) != "instance")		continue	end

						# Pour chaque module activé
						if tableau[i][cle].find("activation", "OFF") == "ON"
							# Mise à jour des relais
							var relais = tableau[i][cle]["environnement"].find("relais", false)

							if (relais)
								for cleRLY: relais.keys()
									if (relais[cleRLY].find("activation", "OFF") == "ON" && relais[cleRLY].find("etat", "OFF") != etat && relais[cleRLY]["id"] == nb + 1)
										log((string.format("GESTION_RELAIS: Lecture de l'etat du bit %i -> " + (relais[cleRLY]["type"] == 1376 ? "led w2812" : "relai") + " n°%i = %s", nb, nb + 1, etat)), LOG_LEVEL_DEBUG)
										
										# Ajoute des détails de déclenchement en json (timestamp et délai)
										relais[cleRLY]["etat"] = etat
										if etat == "ON"
											if tasmota.rtc()["local"] > relais[cleRLY]["timestamp"]["ON"]
                                                log((string.format("GESTION_RELAIS: Enregistre le timestamp de passage à 'ON' du Relai n°%i = %s", nb + 1, etat)), LOG_LEVEL_DEBUG)
												relais[cleRLY]["timestamp"]["delai"] = tasmota.rtc()["local"] - relais[cleRLY]["timestamp"]["ON"]
											end
											
											# if cle == "pompeVideCave"
											# 	relais[cleRLY]["timestamp"]["nbCyclesJour"] += 1
											# end
										end
										relais[cleRLY]["timestamp"][etat] = tasmota.rtc()["local"]

										# Vérifie si il y a un timer paramétrer ou à annuler
										if (etat == "ON" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0)
											log(string.format("GESTION_RELAIS: Lancement du timer pour le relai n°%i: %is !", nb + 1, relais[cleRLY]["timer"]), LOG_LEVEL_INFO)
											tasmota.set_timer(relais[cleRLY]["timer"] * 1000, /-> globalFonctions.modifEtatRelai(cle, nb + 1, "Switch", "TOGGLE", false, false, 0), string.format("timer_relai%i", nb + 1))								
										elif etat == "OFF" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0
											log(string.format("GESTION_RELAIS: Supprime le timer pour le relai n°%i !", nb + 1), LOG_LEVEL_INFO)
											tasmota.remove_timer(string.format("timer_relai%i", nb + 1))								
										end

										# Vérifie si il doit y avoir emission d'un message MQTT
										if (mqtt.connected())
											var tabTopics = relais[cleRLY].find("publishMQTT", false)
											if (tabTopics != false)
												for nbMQTT: 0 .. tabTopics["topic"].size() - 1
													var topic = tabTopics["topic"][nbMQTT]
													if string.find(topic, "cmnd") > -1
														log(string.format("GESTION_RELAIS: Publie sur le réseau mqtt pour le relai n°%i !", nb + 1), LOG_LEVEL_INFO)
														mqtt.publish(topic, etat)								
													end
												end
											end
										end

										# Vérifie si il doit y avoir emission d'un message ModBus
										if (relais[cleRLY].find("virtuel", "OFF") != "OFF")
											var typeConnex = string.split(relais[cleRLY]["virtuel"], "_")[0]
											var moduleConnex = string.split(relais[cleRLY]["virtuel"], "_")[1]
											var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", string.split(relais[cleRLY]["virtuel"], "_")[1])[0]

											if (!string.endswith(groupeConnex , "s"))
												groupeConnex = groupeConnex + "s"
											end

											if (drivers[typeConnex]["activation"] == "ON" && drivers[typeConnex]["environnement"][groupeConnex][moduleConnex]["activation"] == "ON")
												if (introspect.members("controleModbus") == nil)
													log("GESTION_RELAIS: Attention le Driver 'controleModbus' n'est pas activé !", LOG_LEVEL_INFO)
												end

												if (relais[cleRLY].find("idModBus", false) != false)
													# Componentes   -> type=224: "Relais",
													#               -> type=1376: "WS2812"
													#               -> type=256: "Relais_i"
													var valueModBus 
													if (relais[cleRLY]["type"] == 224 || relais[cleRLY]["type"] == 1376)
														valueModBus = (etat == "ON" ? 0x02 : 0x01)
													elif (relais[cleRLY]["type"] == 256)
														valueModBus = (etat == "ON" ? 0x01 : 0x02)
													end

													# Construit la trame
													var trameModBus = 	{
																			"DeviceAddress": drivers[typeConnex]["environnement"][groupeConnex][moduleConnex]["id"], 
																			"FunctionCode": 6, 
																			"StartAddress": (groupeConnex == "TasmotaSlaveModBus" ? relais[cleRLY]["type"] + relais[cleRLY]["idModBus"] - 1 : relais[cleRLY]["idModBus"]),
																			"type": "uint8", 
																			"Count": 1, 
																			"Values": [valueModBus, 0]
																		}

													# Envoi l'ordre sur le réseau ModBus
													log(string.format("GESTION_RELAIS: Publie sur le réseau ModBus pour le relai n°%i !", nb + 1), LOG_LEVEL_INFO)
													
													import modbusFonctions
													modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["DeviceAddress"])
                                                end
											end
										end

										# Enregistre les nouvelles valeurs de capteurs en json
										if (i == 0)
											persist.modules = tableau[i]
										else	persist.drivers = tableau[i]
										end	
									end
								end
							end
						end
					end
				end
			end
		end
	end

    #- Appelé lorsqu'une interaction avec un Bouton réel (BP) et Switchs réel (capteurs & interrupteurs) se produit. 
        idx est codé comme suit : device_save << 24 | key << 16 | state << 8 | device
    -#
    #- key & state
        key 0 = KEY_BUTTON = button_topic
        key 1 = KEY_SWITCH = switch_topic
        state 0 = POWER_OFF = off
        state 1 = POWER_ON = on
        state 2 = POWER_TOGGLE = toggle
        state 3 = POWER_HOLD = hold
        state 4 = POWER_INCREMENT = button still pressed
        state 5 = POWER_INV = button released
        state 6 = POWER_CLEAR = button released
        state 7 = POWER_RELEASE = button released
        state 9 = CLEAR_RETAIN = clear retain flag
        state 10 = POWER_DELAYED = button released delayed
        Button Multipress
        state 10 = SINGLE
        state 11 = DOUBLE
        state 12 = TRIPLE
        state 13 = QUAD
        state 14 = PENTA
    -#
    def any_key(cmd, idx)
		import string
		
		tasmota.yield()
		
		log("GLOBAL_ANY_KEY: -------------------- global any_key -------------------", LOG_LEVEL_DEBUG)
		log("GLOBAL_ANY_KEY: Lecture automatisee de l'etat des Boutons (BP) et Switchs (capteurs & interrupteurs)", LOG_LEVEL_DEBUG)
		log("GLOBAL_ANY_KEY: cmd=" + str(cmd), LOG_LEVEL_DEBUG)
		log("GLOBAL_ANY_KEY: idx=" + str(idx), LOG_LEVEL_DEBUG)
		log(string.format("GLOBAL_ANY_KEY: idx = 0x%07X", idx), LOG_LEVEL_DEBUG)

        #- Détails de idx
            idx=33620226
            en binaire =>  0010 0000 0001 0000 0001 0000 0010
            id de la device =>					    0000 0010		== 2: ex:Button1 ou Switch2 (capteurs ou interrupteurs) 
            state =>					  0000 0001					== 1: 0 = "OFF" / 1 = "ON" / ....
            key =>				0000 0001							== 1: 0 = KEY_BUTTON / 1 = KEY_SWITCH
            device_save => 0001                                     == 1
        -#
    end
end

# Active le Driver de controle global des modules
controleGeneral = CONTROLE_GENERAL()
tasmota.add_driver(controleGeneral)