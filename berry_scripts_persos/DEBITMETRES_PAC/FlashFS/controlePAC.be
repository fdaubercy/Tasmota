#-
 - Pensez à commenter ceci (fonction 'CmndTeleperiod' dans le fichier support_command.ino):
    ----------------------
    /*if ((Settings->tele_period > 0) && (Settings->tele_period < 10)) {
      Settings->tele_period = 10;   // Do not allow periods < 10 seconds
    }*/
    ----------------------
-#
var controlePAC

class CONTROLE_PAC : Driver
    # Variables

    def init()
        import json
        import string
        import pacFonctions
        import webFonctions

        log ("GESTION_PAC: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
		# Déclenche une action tous les jours à minuit
	    #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        #tasmota.add_rule("System", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end)	
        #tasmota.add_rule("Wifi", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end)
        tasmota.add_rule("Mqtt", def(value, trigger, msg) pacFonctions.changementEtatDemarrage(value, trigger, msg) end)

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
            if modules["PAC"].find("activation", "OFF") == "ON"
                var env = controleGeneral.parametres["modules"]["PAC"]["environnement"]
                var debitmetres = env.find("debitmetres", false)

                controleGeneral.nbIO["nbDebitmetresActives"] = 0
                controleGeneral.nbIO["nbDebitmetresReels"] = 0

                if debitmetres
                    # Ajoute les règles
                    for cleD: debitmetres.keys()
                        if type(debitmetres[cleD]) != "instance"
                            continue
                        end

                        # Rules & Nb de débitmètres totaux (réels et virtuels)
                        if debitmetres[cleD].find("activation", "OFF") == "ON" && ((debitmetres[cleD].find("pin", -1) != -1  && debitmetres[cleD].find("virtuel", "OFF") == "OFF") || debitmetres[cleD].find("virtuel", "OFF") == "ON")
                            controleGeneral.nbIO["nbDebitmetresActives"] = controleGeneral.nbIO.find("nbDebitmetresActives", 0) + 1

                            for nb: 0 .. 1
                                tasmota.remove_rule("Débit#Rate[nb + 1]")
                                tasmota.add_rule("Débit#Rate[nb + 1]", def(value, trigger, msg) pacFonctions.changementEtatCapteur(value, trigger, msg, "PAC", cleD) end)
                            end
                        end

                        # Nb de débitmètres réels (non-virtuels)
                        if debitmetres[cleD].find("activation", "OFF") == "ON" && debitmetres[cleD].find("virtuel", "OFF") == "OFF"
                            controleGeneral.nbIO["nbDebitmetresReels"] = controleGeneral.nbIO.find("nbDebitmetresReels", 0) + 1
                        end
                    end
                end

				# Enregistre ou Mets à jour en variable les capteurs activés dans un tableau
				if (gestionFileFolder.readFile("/nbIO.json") != json.dump(controleGeneral.nbIO))
					gestionFileFolder.writeFile("/nbIO.json", json.dump(controleGeneral.nbIO))
				end
            end

            log (string.format("GESTION_PAC: Nb. de débitmètres actives = %i !", controleGeneral.nbIO.find("nbDebitmetresActives", 0)), LOG_LEVEL_DEBUG_PLUS)
            log (string.format("GESTION_PAC: Nb. de débitmètres réels = %i !", controleGeneral.nbIO.find("nbDebitmetresReels", 0)), LOG_LEVEL_DEBUG_PLUS)
        end

		# Ajoute les commandes personnalisées si le module est activé
        var PAC = controleGeneral.parametres["modules"]["PAC"]
		if controleGeneral.parametres["modules"].find("activation", "OFF") == "ON" && PAC.find("activation", "OFF") == "ON"
			var debitmetres = PAC["environnement"].find("debitmetres", false)

			if debitmetres
				# Ajoute les commandes personnalisées
				tasmota.add_cmd('ReglageDebitmetre', pacFonctions.reglageDebitmetre)					
			end
		end

        # Paramétrage Sensor96 après l'enregistrement du modèle par 'controleGlobal.be'
        if controleGeneral.nbIO.find("nbDebitmetresActives", 0) > 0 && controleGeneral.nbIO.find("nbDebitmetresReels", 0) > 0
            # response = {"Sensor96":{"Factor":[1.000,1.000],"Source":"average","Unit":"l/min"}}
            var response = tasmota.cmd("Sensor96", boolMute)["Sensor96"]
            var debitmetres = controleGeneral.parametres["modules"]["PAC"]["environnement"].find("debitmetres", false)
        
            if debitmetres
                if response["Source"] != debitmetres["source"]
                    tasmota.cmd(string.format("Sensor96 9 %i", (debitmetres["source"] == "average" ? 0 : 1)), boolMute)
                end
        
                if response["Unit"] != debitmetres["unit"]
                    tasmota.cmd(string.format("Sensor96 0 %i", (debitmetres["unit"] == "l/min" ? 0 : 1)), boolMute)
                end
        
                for nb: 1 .. controleGeneral.nbIO.find("nbDebitmetresActives", 0)
                    if real(response["Factor"][nb - 1]) != real(debitmetres["debitmetre" + str(nb)]["facteurCorrection"])
                        tasmota.cmd(string.format("Sensor96 %i %i", nb, int(debitmetres["debitmetre" + str(nb)]["facteurCorrection"] * 1000)), boolMute)
                    end
                 end
            end
        end
    end

    def every_100ms()
    end

    def every_second()
        # print(tasmota.read_sensors())
    end

    # Ajoute des données au json sensors
    # Si le capteur est virtuel et activé, recrée le json (comme si il était réel)
	def json_append()	
        import string
        import json

        var jsonSensor = {}
        var i = 0

        # Demande à la fonction '' de créer la partie à ajouter au json sensors (format json)
        # Le transforme en string et l'ajoute

        # Si activés (Réels + virtuels) > 0 => ajoute les noms et les IDs
        if controleGeneral.nbIO.find("nbDebitmetresActives", 0) > 0 
            var dev = controleGeneral.parametres["modules"]["PAC"]["environnement"]["debitmetres"]

            # Si Virtuels > 0 (Activés > 0 && Réels == 0) => ajoute les unités et source
            if controleGeneral.nbIO.find("nbDebitmetresReels", 0) == 0
                jsonSensor["Débit"] = {}
                jsonSensor["Débit"]["Source"] = dev["source"]
                jsonSensor["Débit"]["AmountUnit"] = dev.find("AmountUnit", "L")
                jsonSensor["Débit"]["Unit"] = dev["unit"]

                # Les valeurs 'Rate', 'AmountToday' & 'DurationToday' sont ajoutés par la fonction 'rangeExtenderFonctions.recupereCapteursConnectes()'

                tasmota.response_append(", \"Débit\": " + json.dump(jsonSensor["Débit"]))
            end

            # Ajoute un tableau des noms des débitmètres activés (max 2 débitmètres réels dans Tasmota)
            jsonSensor["nameDebitmetres"] = []
            for nb: 0 .. controleGeneral.nbIO.find("nbDebitmetresActives", 0) - 1
                if dev["debitmetre" + str(nb + 1)]["activation"] == "ON" 
                    jsonSensor["nameDebitmetres"].resize(nb + 1)
                    jsonSensor["nameDebitmetres"][dev["debitmetre" + str(nb + 1)]["id"] - 1] = dev["debitmetre" + str(nb + 1)]["nom"]
                end
            end
            tasmota.response_append(", \"nameDebitmetres\": " + json.dump(jsonSensor["nameDebitmetres"]))

            # Ajoute un tableau des IDs des débitmètres activés (max 2 débitmètres réels dans Tasmota)
            jsonSensor["idDebitmetres"] = []
            for nb: 0 .. controleGeneral.nbIO.find("nbDebitmetresActives", 0) - 1
                if dev["debitmetre" + str(nb + 1)]["activation"] == "ON" 
                    jsonSensor["idDebitmetres"].resize(nb + 1)
                    jsonSensor["idDebitmetres"][dev["debitmetre" + str(nb + 1)]["id"] - 1] = dev["debitmetre" + str(nb + 1)]["id"]
                end
            end
            tasmota.response_append(", \"idDebitmetres\": " + json.dump(jsonSensor["idDebitmetres"]))
        end
    end

	# Se lance chaque jour à minuit
	def majMinuit()
	end

end

# Active le Driver de controle global des modules
controlePAC = CONTROLE_PAC()
tasmota.add_driver(controlePAC)