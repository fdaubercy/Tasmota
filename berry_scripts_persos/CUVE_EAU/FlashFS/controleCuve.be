var controleCuve

class CONTROLE_CUVE : Driver
    # Variables
    var formSelection
    var categorieSelection
    var ajustement
    var AnaValues
    var gain

    def init()
        import json
        import string
        import cuveFonctions

        self.formSelection = ""
        self.categorieSelection = ""

        log ("GESTION_CUVE: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
        # - Message log sur connexion wifi
        # - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        # - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        #tasmota.add_rule("System", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)	
        #tasmota.add_rule("Wifi", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)
        #tasmota.add_rule("Mqtt", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)

        #-     
        Parcours tous les modules paramétrés
        - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
            Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
            par la fonction 'every_second()'
        - Compte les devices non-virtuelles
        - Compte le nombre de devices activés par type et les range dans un tableau
        - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage) 
        -#
        var modules = controleGeneral.parametres["modules"]
        if modules.find("activation", "OFF") == "ON"
            # Si le module est activé
            if modules["cuve"].find("activation", "OFF") == "ON"
                var env = controleGeneral.parametres["modules"]["cuve"]["environnement"]
                var ads1115 = env.find("ADS1115", false)

                controleGeneral.nbIO["nbAnaActives"] = 0
                controleGeneral.nbIO["nbAnaReels"] = 0

                if ads1115
                    if ads1115.find("activation", "OFF") == "ON"
                        # Ajoute les règles
                        for cleD: ads1115.keys()
                            if type(ads1115[cleD]) != "instance"
                                continue
                            end

                            # Rules & Nb de débitmètres totaux (réels et virtuels)
                            if ads1115[cleD].find("activation", "OFF") == "ON"
                                controleGeneral.nbIO["nbAnaActives"] = controleGeneral.nbIO.find("nbAnaActives", 0) + 1

                                #tasmota.remove_rule("Débit#Rate", "chgtDebit" + str(debitmetres[cleD]["id"]))
                                #tasmota.add_rule("Débit#Rate", def(value, trigger, msg) pacFonctions.changementEtatCapteur(value[debitmetres[cleD]["id"] - 1], trigger, msg, "PAC", cleD) end, "chgtDebit" + str(debitmetres[cleD]["id"]))
                            end

                            # Nb de débitmètres réels (non-virtuels)
                            if ads1115[cleD].find("activation", "OFF") == "ON" && ads1115[cleD].find("virtuel", "OFF") == "OFF"
                                controleGeneral.nbIO["nbAnaReels"] = controleGeneral.nbIO.find("nbAnaReels", 0) + 1
                            end
                        end
                    end
                end

				# Enregistre ou Mets à jour en variable les capteurs activés dans un tableau
				if (gestionFileFolder.readFile("/nbIO.json") != json.dump(controleGeneral.nbIO))
					gestionFileFolder.writeFile("/nbIO.json", json.dump(controleGeneral.nbIO))
				end
            end

            log (string.format("GESTION_CUVE: Nb. d'entrées analogiques d'ADS1115 I2C actives = %i !", controleGeneral.nbIO.find("nbAnaActives", 0)), LOG_LEVEL_DEBUG)
            log (string.format("GESTION_CUVE: Nb. d'entrées analogiques d'ADS1115 I2C réelles = %i !", controleGeneral.nbIO.find("nbAnaReels", 0)), LOG_LEVEL_DEBUG)
        end

		# Ajoute les commandes personnalisées si le module est activé
        var cuve = controleGeneral.parametres["modules"]["cuve"]
		if controleGeneral.parametres["modules"].find("activation", "OFF") == "ON" && cuve.find("activation", "OFF") == "ON"
			var ads1115 = cuve["environnement"].find("ADS1115", false)

			if ads1115
				# Ajoute les commandes personnalisées
				tasmota.add_cmd('ReglageAna', cuveFonctions.ReglageAna)					
			end
		end

        # Paramétrage 'I2CDriver13' & 'WebSensor12' après l'enregistrement du modèle par 'controleGlobal.be'
        # Active ou désactive le Driver13 si le Nb. d'entrées analogiques d'ADS1115 I2C activées >= 1
		if controleGeneral.nbIO.find("nbAnaActives", 0) > 0 && controleGeneral.nbIO.find("nbAnaReels", 0) > 0
				if string.find(tasmota.cmd("I2CDriver", boolMute)["I2CDriver"], "!13") > -1 && string.find(tasmota.cmd("I2CDriver", boolMute)["I2CDriver"], "13") > -1
                    log ("GESTION_CUVE: Active le Driver13 pour l'ADS1115 !", LOG_LEVEL_DEBUG)
                    tasmota.cmd("I2CDriver13 1", boolMute)
				end

                # Désactive l'affichage web des valeurs issues du firmware de l'ADS1115
                tasmota.cmd("WebSensor12 " + (cuve["environnement"]["ADS1115"].find("affichageWebSensor", "ON") == "OFF" ? str(0) : str(1)), boolMute)
		else
				if string.find(tasmota.cmd("I2CDriver", boolMute)["I2CDriver"], "!13") == -1 && string.find(tasmota.cmd("I2CDriver", boolMute)["I2CDriver"], "13") > -1
                    log ("GESTION_CUVE: Désactive le Driver13 pour l'ADS1115 !", LOG_LEVEL_DEBUG)
                    tasmota.cmd("I2CDriver13 0", boolMute)
				end
		end

        # Récupère le gain du capteur
        var pasGain = [0.1875, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125]
        self.gain = real(pasGain[int(string.split(tasmota.cmd("Sensor12", boolMute)["ADS1115"]["Settings"], "S")[1])])
        log (string.format("GESTION_CUVE: Gain des capteurs de l'ADS1115 = %.4f", self.gain), LOG_LEVEL_INFO)
    end

    def every_100ms()
    end

    def every_second()
        # print(tasmota.read_sensors())
    end

	# Se lance chaque jour à minuit
	def majMinuit()
    end

	def web_sensor()
        import json
        import string

        var htmlSensor = ""
        self.AnaValues = [0.00, 0.00, 0.00, 0.00]

        # Récupère les capteurs
        controleGeneral.sensors = json.load(tasmota.read_sensors())

        # Corrige les valeurs des capteurs analogiques avec la valeur étalon
        log (string.format("GESTION_CUVE: Ajustement=%d", self.ajustement), LOG_LEVEL_INFO)
        self.ajustement = controleGeneral.sensors["ADS1115"]["A0"]

        for nb: 0 .. 3
            # Ajustement de la valeur en fonction de la valeur étalon
            if (nb != 0)    self.AnaValues[nb] = controleGeneral.sensors["ADS1115"]["A" + str(nb)] - self.ajustement    end

            if controleGeneral.parametres["modules"]["cuve"].find("activation", "OFF") == "ON" && controleGeneral.parametres["modules"]["cuve"]["environnement"]["ADS1115"].find("activation", "OFF") == "ON"
                # Correction de la valeur en 'V' en fonction du gain
                controleGeneral.parametres["modules"]["cuve"]["environnement"]["ADS1115"]["Ana" + str(nb + 1)]["value"] = real(self.AnaValues[nb] * self.gain) / 1000
                
                # Affichage sur la page web selon le paramètre
                if (controleGeneral.parametres["modules"]["cuve"]["environnement"]["ADS1115"]["Ana" + str(nb + 1)].find("affichageWebSensor", "OFF") == "ON" && nb > 0)  
                    htmlSensor += string.format("{s}Capteur de Niveau de Cuve{m}%.3fV{e}", real(self.AnaValues[nb] * self.gain) / 1000)
                end
            end
        end

        # Affichage sur page web
        if controleGeneral.parametres["modules"]["cuve"].find("activation", "OFF") == "ON"
            log ("CUVE_WEBSERVER: Envoi a la page web de l'etat des capteurs !", LOG_LEVEL_DEBUG_PLUS)
            tasmota.web_send(htmlSensor)
        end
    end
    
    # Ajoute des données au json sensors
    # Si le capteur est virtuel et activé, recrée le json (comme si il était réel)
	def json_append()	
        import string
        import json

    end

	# Envoi des parametres à la page web
	def envoiJson()
        import json
        import webserver
        import webFonctions
        import globalFonctions

    end

	#- Création de boutons dans le menu principal -#
	def web_add_main_button()
        # import webserver

        # log ("WEBSERVER: Affichage du bouton !", LOG_LEVEL_DEBUG)
		# webserver.content_send("<p></p><button class='button bgrn' onclick='window&#46;location&#46;href=\"/graphiques?module=PAC&categorie=debitmetres\"'>Graphiques</button>")
    end	

	# Charge les appels aux fonctions selon l'url spécifiques aux modules
	def web_add_handler()
        import webserver

        # webserver.on("/graphiques", / -> self.afficheGraphiques(), webserver.HTTP_GET)	
        # webserver.on("/jsonGraphiques", / -> self.envoiJson(), webserver.HTTP_ANY)	
	end
end

# Active le Driver de controle global des modules
controleCuve = CONTROLE_CUVE()
tasmota.add_driver(controleCuve)