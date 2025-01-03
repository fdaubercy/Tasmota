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
		import gestionFileFolder
		import globalFonctions

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
	    configGlobal.configGlobalByJson(self.parametres)

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        #tasmota.add_rule("System", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end)	
        tasmota.add_rule("Wifi", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end)
        #tasmota.add_rule("Mqtt", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end)

        # Parcours tous les modules paramétrés
		# - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
		# 	Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
		# 	par la fonction 'every_second()'
		# - Compte les devices non-virtuelles
        # - Compte le nombre de devices activées par type et les range dans un tableau
        # - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
        var modules = self.parametres["modules"]
        if modules.find("activation", "OFF") == "ON"
			self.nbIO["nbRelaisActives"] = 0
			self.nbIO["nbSwitchsActives"] = 0
			self.nbIO["nbButtonsActives"] = 0

			for cleModule: modules.keys()
				if type(modules[cleModule]) != "instance"
					continue
				end

                # Si le module est activé
                if modules[cleModule].find("activation", "OFF") == "ON"
                    var env = self.parametres["modules"][cleModule]["environnement"]

                    var relais = env.find("relais", false)
                    if relais
                        for cleRLY: relais.keys()
                            if type(relais[cleRLY]) != "instance"
                                continue
                            end

                            # Si le relai est activé
                            if relais[cleRLY].find("activation", "OFF") == "ON" && ((relais[cleRLY].find("pin", -1) != -1  && relais[cleRLY].find("virtuel", "OFF") == "OFF") || relais[cleRLY].find("virtuel", "OFF") == "ON")
                                if cleModule == "pompeVideCave" 
                                    relais[cleRLY]["timestamp"]["nbCyclesJour"] = 0 
                                    if relais[cleRLY]["timestamp"]["ON"] == 0 relais[cleRLY]["timestamp"]["ON"] = tasmota.rtc()["local"] end
                                    if relais[cleRLY]["timestamp"]["OFF"] == 0 relais[cleRLY]["timestamp"]["OFF"] = tasmota.rtc()["local"] end
                                end
                                self.nbIO["nbRelaisActives"] = self.nbIO.find("nbRelaisActives", 0) + 1	
                            end
                        end
                    end

                    var capteurs = env.find("capteurs", false)	
                    if env.find("interrupteurs", false)     capteurs.insert("interrupteurs", env["interrupteurs"])  end	
                    if capteurs
                        for cleCapteurs: capteurs.keys()
                            if type(capteurs[cleCapteurs]) != "instance"
                                continue
                            end

                            if capteurs[cleCapteurs].find("activation", "OFF") == "ON" && ((capteurs[cleCapteurs].find("pin", -1) != -1  && capteurs[cleCapteurs].find("virtuel", "OFF") == "OFF") || capteurs[cleCapteurs].find("virtuel", "OFF") == "ON")
                                self.nbIO["nbSwitchsActives"] = self.nbIO.find("nbSwitchsActives", 0) + 1	
                                tasmota.add_rule(string.format("Switch%i#Action", capteurs[cleCapteurs]["id"]), def(value, trigger, msg) self.changementEtatCapteur(value, trigger, msg, cleModule, cleCapteurs) end)				
                            end
                        end
                    end

                    var boutons = env.find("boutons", false)
                    if boutons
                        for cleBoutons: boutons.keys()
                            if type(boutons[cleBoutons]) != "instance"
                                continue
                            end

                            if boutons[cleBoutons].find("activation", "OFF") == "ON" && ((boutons[cleBoutons].find("pin", -1) != -1  && boutons[cleBoutons].find("virtuel", "OFF") == "OFF") || boutons[cleBoutons].find("virtuel", "OFF") == "ON")
                                self.nbIO["nbButtonsActives"] = self.nbIO.find("nbButtonsActives", 0) + 1	

                                tasmota.remove_rule(string.format("Button%i#Action", boutons[cleBoutons]["id"]))
                                tasmota.add_rule(string.format("Button%i#Action", boutons[cleBoutons]["id"]), def(value, trigger, msg) self.changementEtatCapteur(value, trigger, msg, cleModule, cleBoutons) end)
                            end									
                        end
                    end

                    # Enregistre ou Mets à jour en variable les capteurs activés dans un tableau
                    if (gestionFileFolder.readFile("/nbIO.json") != json.dump(self.nbIO))
                        gestionFileFolder.writeFile("/nbIO.json", json.dump(self.nbIO))
                    end
                end
            end

            log (string.format("CONTROLE_GENERAL: Nb. de relais actives = %i !", self.nbIO.find("nbRelaisActives", 0)), LOG_LEVEL_DEBUG)

			# Détache ou attache les boutons et switchs si activés >= 1
			log (string.format("CONTROLE_GENERAL: Nb. de switchs actives = %i !", self.nbIO.find("nbSwitchsActives", 0)), LOG_LEVEL_DEBUG)	
			if self.nbIO.find("nbRelaisActives", 0) > 0
				if tasmota.cmd("SetOption114", boolMute)["SetOption114"] != "ON"
					log ("CONTROLE_GENERAL: Detache tous les switchs !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption114 ON", boolMute)		
				end
			else
				if tasmota.cmd("SetOption114", boolMute)["SetOption114"] != "OFF"
					log ("CONTROLE_GENERAL: Attache tous les switchs !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption114 OFF", boolMute)		
				end	
			end
			
			# Détache ou attache les interrupteurs & capteurs si activés >= 1
			log (string.format("CONTROLE_GENERAL: Nb. de boutons actives = %i !", self.nbIO.find("nbButtonsActives", 0)), LOG_LEVEL_DEBUG)
			if self.nbIO.find("nbButtonsActives", 0) > 0
				if tasmota.cmd("SetOption73", boolMute)["SetOption73"] != "ON"
					log ("CONTROLE_GENERAL: Detache tous les boutons !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption73 ON", boolMute)		
				end
			else
				if tasmota.cmd("SetOption73", boolMute)["SetOption73"] != "OFF"
					log ("CONTROLE_GENERAL: Attache tous les boutons !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption73 OFF", boolMute)		
				end	
			end
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

	#- Se déclenche sur modification d'état d'un relai par l'interface webUI ou commande Power -#
	def set_power_handler(cmd, idx)
        import string
        import mqtt
		import globalFonctions

		var etat = ""
		var i = 0
		
		print("----------------------- SetPowerHandler ----------------------")
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
						var relais = self.parametres["modules"][cle]["environnement"]["relais"]

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

# Active le Driver de controle global des modules
controleGeneral = CONTROLE_GENERAL()
tasmota.add_driver(controleGeneral)