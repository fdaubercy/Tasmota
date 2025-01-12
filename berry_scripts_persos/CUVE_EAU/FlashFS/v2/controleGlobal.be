# NOTES :
# - Encore penser à paramétrer le module ('template') en fonction du changement de pin du relai dans la page : trappe?action=affichage
# 		* Types de GPIO enregistrés dans _persist.json sous parametres["componentes"]
# 		* A paramétrer au démarrage après validation du formulaire html des paramètres : fonction'modifParametres' dans 'globarVar.be'
# 		* Attention ajouter donc les numeros de relais ou switchs ou boutons dans ce formulaire
#		* ex de commande : tasmota.cmd("Template {'NAME':'Example Template','GPIO':[416,0,418,0,417,2720,0,0,2624,32,2656,224,0,0],'FLAG':0,'BASE':0}")
# - Pour tasmota :
#   * Bouton (BUTTON) = bouton poussoir
#   * Interrupteur (Switch) = Interrupteur
# Gère les actions sur les relais
# Lance le timer si le relai est une relai astable avec timer
# boolCapteurs=true -> si il faut désactiver les capteurs qui gèrent son déclenchement
# boolTimer=true -> si il faut activer le timer
# delaiAvantCommande -> délai avant commande du relai
class CONTROLE_GENERAL : Driver
    # Variables
	var sensors
	var enregistrePersistant
    var parametres
	var connected
    var nbIO
    var flagINIT        # Flag marquant la fin de l'initialisation du module principal

    def init()
        import json
        import string
        import configGlobal
		import globalFonctions
        import persist

		self.enregistrePersistant = false
        self.nbIO = {}
        self.parametres = persist.find("parametres")
		self.connected = false
        self.flagINIT = 0

		# Récupère les sensors
		self.sensors = json.load(tasmota.read_sensors())

        log ("CONTROLE_GENERAL: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
		# Déclenche une action tous les jours à minuit
	    tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Configure le module tasmota (paramètres communs à tous les modules Tasmota)
	    if (configGlobal.configGlobalByJson())  self.parametres = persist.find("parametres")    end

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        tasmota.add_rule("System", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end)	
        tasmota.add_rule("Wifi", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end)
        tasmota.add_rule("Mqtt", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end)

        # Parcours tous les modules paramétrés
		# - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
		# 	Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
		# 	par la fonction 'every_second()'
		# - Compte les devices non-virtuelles
        # - Compte le nombre de devices activées par type et les range dans un tableau
        # - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
		# - Détache ou attache les boutons et switchs si activés >= 1
		# - Détache ou attache les interrupteurs & capteurs si activés >= 1
        var modules = self.parametres["modules"]
        if modules.find("activation", "OFF") == "ON"
			self.nbIO["nbRelaisActives"] = 0
			self.nbIO["nbSwitchsActives"] = 0
			self.nbIO["nbButtonsActives"] = 0
			self.nbIO["nbRelaisReels"] = 0
			self.nbIO["nbSwitchsReels"] = 0
			self.nbIO["nbButtonsReels"] = 0

			# Parcours tous les modules paramétrés
			globalFonctions.configDevices(modules, self.nbIO)
            log (string.format("CONTROLE_GENERAL: Nb. de relais actives = %i !", self.nbIO.find("nbRelaisActives", 0)), LOG_LEVEL_DEBUG)
			log (string.format("CONTROLE_GENERAL: Nb. de switchs actives = %i !", self.nbIO.find("nbSwitchsActives", 0)), LOG_LEVEL_DEBUG)	
			log (string.format("CONTROLE_GENERAL: Nb. de boutons actives = %i !", self.nbIO.find("nbButtonsActives", 0)), LOG_LEVEL_DEBUG)
			print()
            log (string.format("CONTROLE_GENERAL: Nb. de relais réels = %i !", self.nbIO.find("nbRelaisReels", 0)), LOG_LEVEL_DEBUG)
			log (string.format("CONTROLE_GENERAL: Nb. de switchs réels = %i !", self.nbIO.find("nbSwitchsReels", 0)), LOG_LEVEL_DEBUG)	
			log (string.format("CONTROLE_GENERAL: Nb. de boutons réels = %i !", self.nbIO.find("nbButtonsReels", 0)), LOG_LEVEL_DEBUG)
        end

        # Ajoute les commandes personnalisées si le module est activé

        # Marqueur de fin d'initialisation du module principal
        self.flagINIT = 1 
    end

	# Se lance chaque jour à minuit
	def majMinuit()
	end

    def every_second()
		# Mets à jours la json self.parametres / 1s
		#self.majCapteursJson()
    end

	# Parcours les modules pour detecter les capteurs & boutons qui ne sont pas automatiquement ajouter dans self.sensors
	def json_append()	
        import string

		var msg = ""

		# Parcours  les modules pour detecter les capteurs & boutons qui ne sont pas automatiquement ajouter dans self.sensors
		if self.nbIO["nbButtonsActives"] > 0
			for cleModules: self.parametres["modules"].keys()
				if type(self.parametres["modules"][cleModules]) != "instance"
					continue
				end	

				# Si le module est activé
				var modules = self.parametres["modules"][cleModules]
				if modules.find("activation", "OFF") == "ON"
					if (modules["environnement"].find("boutons", false))
						if type(modules["environnement"]["boutons"]) != "instance"
							continue
						end	

						for cleBoutons: modules["environnement"]["boutons"].keys()
							var bouton = modules["environnement"]["boutons"][cleBoutons]
							if bouton.find("activation", "OFF") == "ON" && ((bouton.find("pin", -1) != -1  && bouton.find("virtuel", "OFF") == "OFF") || bouton.find("virtuel", "OFF") == "ON")
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

	#- Se déclenche sur modification d'état d'un relai par l'interface webUI ou commande Power -#
	def set_power_handler(cmd, idx)
        import string
        import mqtt
		import globalFonctions

		var etat = ""
		var i = 0
		
		print("----------------------- global SetPowerHandler ----------------------")
		log("CONTROLE_GENERAL: Lecture automatisee de l'etat des relais", LOG_LEVEL_DEBUG)
		for nb: 0 .. self.nbIO["nbRelaisActives"]
			if 1 & (idx >> (nb)) == 1
				etat = "ON"
			else etat = "OFF"
			end
			
			# Parcours tous les modules paramétrés
			if self.parametres["modules"].find("activation", "OFF") == "ON"
				for cle: self.parametres["modules"].keys()
					if type(self.parametres["modules"][cle]) != "instance"
						continue
					end

					# Pour chaque module activé
					if self.parametres["modules"][cle].find("activation", "OFF") == "ON"
						# Mise à jour des relais
						var relais = self.parametres["modules"][cle]["environnement"].find("relais", false)

						if (relais)
							for cleRLY: relais.keys()
								if relais[cleRLY]["etat"] != etat && relais[cleRLY]["id"] == nb + 1
									log((string.format("GESTION_RELAIS: Lecture etat bit %i -> relai %i = %s", 7 - nb, nb + 1, etat)), LOG_LEVEL_DEBUG)
									
									# Ajoute des détails de déclenchement en json
									relais[cleRLY]["etat"] = etat
									if etat == "ON"
										if tasmota.rtc()["local"] > relais[cleRLY]["timestamp"]["ON"]
											relais[cleRLY]["timestamp"]["delai"] = tasmota.rtc()["local"] - relais[cleRLY]["timestamp"]["ON"]
										end
										
										if cle == "pompeVideCave"
											relais[cleRLY]["timestamp"]["nbCyclesJour"] += 1
										end
									end
									relais[cleRLY]["timestamp"][etat] = tasmota.rtc()["local"]
									
									# Vérifie si il y a un timer paramétrer ou à annuler
									if etat == "ON" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0
										log (string.format("GESTION_RELAIS: Lancement du timer pour le relai %i: %is !", nb + 1, relais[cleRLY]["timer"]), LOG_LEVEL_INFO)
										tasmota.set_timer(relais[cleRLY]["timer"] * 1000, /-> globalFonctions.modifEtatRelai(cle, nb + 1, "Switch", "TOGGLE", false, false, 0), string.format("timer_relai%i", nb + 1))								
									elif etat == "OFF" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0
										log (string.format("GESTION_RELAIS: Supprime le timer pour le relai %i !", nb + 1), LOG_LEVEL_INFO)
										tasmota.remove_timer(string.format("timer_relai%i", nb + 1))								
									end
									
									# Vérifie si il doit y avoir emission d'un message MQTT
									var tabTopics = relais[cleRLY]["publishMQTT"]
									for nbMQTT: 0 .. tabTopics["topic"].size() - 1
										var topic = tabTopics["topic"][nbMQTT]
										if string.find(topic, "cmnd") > -1
											log (string.format("GESTION_RELAIS: Publie sur le réseau mqtt pour le relai %i !", nb + 1), LOG_LEVEL_INFO)
											mqtt.publish(topic, etat)								
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
end

# Active le Driver de controle global des modules
controleGeneral = CONTROLE_GENERAL()
tasmota.add_driver(controleGeneral)
