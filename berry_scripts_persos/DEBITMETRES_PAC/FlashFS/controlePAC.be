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
    var formSelection
    var categorieSelection

    def init()
        import json
        import string
        import pacFonctions
        import webFonctions

        self.formSelection = ""
        self.categorieSelection = ""

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

                            tasmota.remove_rule("Débit#Rate", "chgtDebit" + str(debitmetres[cleD]["id"]))
                            tasmota.add_rule("Débit#Rate", def(value, trigger, msg) pacFonctions.changementEtatCapteur(value[debitmetres[cleD]["id"] - 1], trigger, msg, "PAC", cleD) end, "chgtDebit" + str(debitmetres[cleD]["id"]))
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

                # Les valeurs 'Rate', 'AmountToday' & 'DurationToday' sont enregistrés en json par la fonction 'rangeExtenderFonctions.recupereCapteursConnectes()'
                jsonSensor["Débit"]["Rate"] = []
                jsonSensor["Débit"]["AmountToday"] = []
                jsonSensor["Débit"]["DurationToday"] = []
                for nb: 0 .. controleGeneral.nbIO.find("nbDebitmetresActives", 0) - 1
                    if dev["debitmetre" + str(nb + 1)]["activation"] == "ON" 
                        jsonSensor["Débit"]["Rate"].resize(nb + 1)
                        jsonSensor["Débit"]["Rate"][dev["debitmetre" + str(nb + 1)]["id"] - 1] = dev["debitmetre" + str(nb + 1)]["value"]

                        jsonSensor["Débit"]["AmountToday"].resize(nb + 1)
                        jsonSensor["Débit"]["AmountToday"][dev["debitmetre" + str(nb + 1)]["id"] - 1] = dev["debitmetre" + str(nb + 1)].find("AmountToday", 0)

                        jsonSensor["Débit"]["DurationToday"].resize(nb + 1)
                        jsonSensor["Débit"]["DurationToday"][dev["debitmetre" + str(nb + 1)]["id"] - 1] = dev["debitmetre" + str(nb + 1)].find("DurationToday", 0)
                    end
                end

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

	def web_sensor()
        import json
        import string

        var htmlSensor = ""

		controleGeneral.sensors = json.load(tasmota.read_sensors())

		# Uniquement si c'est un Point d'accès Range Extender
        if controleGeneral.parametres["serveur"].find("rangeExtender", false)
            if (controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 99) != 0) return    end
        end

        if controleGeneral.parametres["modules"].find("activation", "OFF") == "ON"
            log ("PAC_WEBSERVER: Envoi a la page web de l'etat des capteurs virtuels!", LOG_LEVEL_DEBUG_PLUS)
                            htmlSensor =    "<table style='width=100%'>"
            # Parcours les modules
            for cleModule: controleGeneral.parametres["modules"].keys()
                if (type(controleGeneral.parametres["modules"][cleModule]) != "instance")   continue    end		
                    
                if controleGeneral.parametres["modules"][cleModule].find("activation", "OFF") == "ON"
                    # Parcours les débitmètres dans chaque module
                    var debitmetres = controleGeneral.parametres["modules"][cleModule]["environnement"].find("debitmetres", false)            
                    if debitmetres
                        for cleD: debitmetres.keys()
                            if (type(debitmetres[cleD]) != "instance")   continue   end

                            # Si débitmètre virtuel
                            if debitmetres[cleD].find("activation", "OFF") == "ON" && debitmetres[cleD].find("virtuel", "OFF") == "ON"
                                htmlSensor +=   "<fieldset>" + 
                                                    "<style>" + 
                                                        "div, fieldset, input, select {" + 
                                                            "padding:3px;" + 
                                                        "}" + 
                                                        "fieldset{" + 
                                                            "border-radius:0.3rem;" + 
                                                        "}" + 
                                                        ".parametre{" + 
                                                            "border-radius:0.3rem;" + 
                                                            "padding:1px;" + 
                                                            "display:flex;" + 
                                                            "flex-direction:column;" + 
                                                            "font-size:0.9rem;" + 
                                                        "}" + 
                                                    "</style>" +
                                                    "<legend><b title=''>" + debitmetres[cleD]["nom"] + "</b></legend>"
                                    htmlSensor +=   "<div class='parametre'>" + 
                                                        "<div>- Débit: " + str(real(debitmetres[cleD].find("Rate", 0.0))) + " " + debitmetres.find("unit", "ml/min") + "</div>" + 
                                                        "<div>- Qté journalier: " + str(real(debitmetres[cleD].find("AmountToday", 0.0))) + " " + debitmetres.find("amountUnit", "ml") + "</div>"
                                                            
                                                        var time_dump = tasmota.time_dump(debitmetres[cleD].find("DurationToday", 0))
                                                        var duree = (time_dump["hour"] < 10 ? "0": "") + str(time_dump["hour"]) + ":" + (time_dump["min"] < 10 ? "0": "") + str(time_dump["min"]) + ":" + (time_dump["sec"] < 10 ? "0": "") + str(time_dump["sec"])
                                        htmlSensor +=   "<div>- Tps fonctionnement journalier: " + duree + "</div>" + 
                                                    "</div>"
                                htmlSensor +=   "</fieldset>"
                            end
                        end
                    end
                end
            end
                            htmlSensor +=   "</table>"
        end

        tasmota.web_send(htmlSensor)

	end	

	# Envoi des parametres à la page web
	def envoiJson()
        import json
        import webserver
        import webFonctions
        import globalFonctions

		var jsonRequete = {}
        var jsonRequete2 = ""
		var typeModule = (webserver.has_arg('module') ? webserver.arg('module') : '')
		var categorie = (webserver.has_arg('categorie') ? webserver.arg('categorie') : '')
        var commande = (webserver.has_arg('commande') ? webserver.arg('commande') : '')

        # Test   
        log ("PAC_ENVOI_JSON: -------------------- controlePAC envoiJson -------------------", LOG_LEVEL_DEBUG_PLUS)
        log ("PAC_ENVOI_JSON: typeModule=" + str(typeModule), LOG_LEVEL_DEBUG_PLUS)
        log ("PAC_ENVOI_JSON: categorie=" + str(categorie), LOG_LEVEL_DEBUG_PLUS)
        log ("PAC_ENVOI_JSON: commande=" + str(commande), LOG_LEVEL_DEBUG_PLUS)

		# Si une commande est envoyée
        if (commande != "" )
            if (commande == "jsonSensors")
                jsonRequete.insert("sensors", json.load(tasmota.read_sensors()))

                # Si testPAC == "ON"
                var pac = controleGeneral.parametres["modules"]["PAC"]
                if (pac["activation"] == "ON" && pac.find("test", "OFF") == "ON")
                    for cle: jsonRequete["sensors"]["Débit"]["Rate"].keys()
                        jsonRequete["sensors"]["Débit"]["Rate"][cle] = globalFonctions.getRandomInt(0, 150)
                    end
                end

                webserver.content_response(json.dump(jsonRequete))
                return
            end
        end

        # Détermine quelle partie du json est envoyée à la page web
        if (typeModule != "")
            jsonRequete.insert(typeModule, controleGeneral.parametres["modules"][typeModule])
        else
            jsonRequete = controleGeneral.parametres
        end
        webserver.content_response(json.dump(jsonRequete))
    end

    # Gestion de l'affichage de la page des paramètres des capteurs pour réglage
	def afficheGraphiques()
        import string
        import webserver
        import gestionFileFolder

		var titreHTML = ""
        var tempFile = ""
        var buffer = ""

		# Gère la réponse au bouton 
		# Requete XMLHttpResponse : Corps de la page
		if webserver.has_arg("module") && webserver.has_arg("categorie")
			titreHTML = "Paramètres des modules"
			self.formSelection = webserver.arg("module")
			self.categorieSelection = webserver.arg("categorie")
			
            if (self.formSelection != "PAC")    return  end
			log ("WEBSERVER: Affichage de la page des graphiques du module 'PAC' !", LOG_LEVEL_DEBUG)

			# Démarrage la page
			webserver.content_start(titreHTML)
			webserver.content_send_style()	

            # Envoi les scripts css
            gestionFileFolder.readFileByLineAndContentSend("/sd/css/main.css")

			# Envoi le formulaire de selection de module
            tempFile = gestionFileFolder.readFile("/sd/html/formSelectParametres.html")
            for cle: controleGeneral.parametres.keys()
                if (type(controleGeneral.parametres[cle]) != "instance")   continue    end	
                if cle == "serveur"
                    buffer += "<option value='" + cle + "' " + (self.formSelection == cle ? "selected" : "") + ">Serveur</option>"
                elif cle == "diverses"
                    buffer += "<option value='" + cle + "' " + (self.formSelection == cle ? "selected" : "") + ">Divers</option>"
                elif cle == "modules"
                    for cleModule: controleGeneral.parametres[cle].keys()
                        if (type(controleGeneral.parametres[cle][cleModule]) != "instance")     continue   end	
                        buffer += "<option value='" + cleModule + "' " + (self.formSelection == cleModule ? "selected" : "") + ">" + controleGeneral.parametres[cle][cleModule]["name"] + "</option>"
                    end
                end
            end
            tempFile = string.replace(tempFile, "##SELECT_OPTION_MODULES##", buffer)

			# Envoi la page web
            # Envoi le formulaire de selection de categorie dans le module
            buffer = "<div style='display:block;'>" + 
                        "<label>Catégorie :</label>" + 
                        "<select id='categorie' placeholder='Sélectionnez la catégorie'>" + 
                            "<option value='boutons'>Boutons</option>" + 
                            "<option value='capteurs'>Capteurs</option>" + 
                            "<option value='thermometres'>Capteurs de température</option>" + 
                            "<option value='debitmetres'>Débitmètres</option>" + 
                            "<option value='leds'>Leds</option>" + 
                            "<option value='relais'>Relais</option>" + 
                            "<option value='pinsSDs'>Connexion Carte SD</option>" + 
                            "<option value='pinsEcrans'>Connexion Ecran</option>" + 
                            "<option value='ws2812s'>WS2812</option>" + 
                            "<option value='' selected></option>" + 
                        "</select>" + 
                    "</div>"

            tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
            webserver.content_send(tempFile)

            # Début du formulaire
            gestionFileFolder.readFileByLineAndContentSend("/sd/html/pageGraphiques.html")

            # Envoi les scripts javascript
            gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
            gestionFileFolder.readFileByLineAndContentSend("/sd/js/graphiques.js")

 		    #- end of web page -#
            webserver.content_stop()			
        end           
    end

	#- Création de boutons dans le menu principal -#
	def web_add_main_button()
        import webserver

        log ("WEBSERVER: Affichage du bouton !", LOG_LEVEL_DEBUG)
		webserver.content_send("<p></p><button class='button bgrn' onclick='window&#46;location&#46;href=\"/graphiques?module=PAC&categorie=debitmetres\"'>Graphiques</button>")
    end	

	# Charge les appels aux fonctions selon l'url spécifiques aux modules
	def web_add_handler()
        import webserver

        webserver.on("/graphiques", / -> self.afficheGraphiques(), webserver.HTTP_GET)	
        webserver.on("/jsonGraphiques", / -> self.envoiJson(), webserver.HTTP_ANY)	
	end
end

# Active le Driver de controle global des modules
controlePAC = CONTROLE_PAC()
tasmota.add_driver(controlePAC)