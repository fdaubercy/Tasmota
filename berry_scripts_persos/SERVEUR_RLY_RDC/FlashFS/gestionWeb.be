# Gestion des pages internet
# Données GET & POST utilisées :
#	module : quel chapitre du json sera demandé
#   environnement : sous-module
#	modifParam : quel est le chapitre qui sera modifié par requête
# 	script : le type de script 'javascript' demandé par le serveur
#	commande : type de commande berry à réaliser

# Attention : autoriser l'access-crossing sur le site distant si vous y accédez
# Ajouter 'dans la section <Directory> de 'httpd.conf' d'Apache2 : Header set Access-Control-Allow-Origin "*"
# Ajouter le fichier 'componentes.json' dans le dossier de votre serveur

# Fonctions nécesaires au Driver
class GESTION_WEB : CONTROLE_GENERAL
    # Variables
	var parametres
    var formSelection
    var categorieSelection
    var sensors

    def init()
        import json

        # Lance le driver de CONTROLE_GENERAL
        super(self).init()

        self.formSelection = ""
        self.categorieSelection = ""
    end

    def every_second()
    end

	def web_sensor()
        import json
        import string

		self.sensors = json.load(tasmota.read_sensors())
		
		if self.parametres["modules"]["pompeVideCave"].find("activation", "OFF") == "ON"
			log ("WEBSERVER: Envoi a la page web de l'etat des capteurs !", LOG_LEVEL_DEBUG_PLUS)

            var sensorPompeCave = "<table style='width=100%'>" + 
                                    "<fieldset>" + 
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
                                                "flex-direction:row;" + 
                                            "}" + 
                                            ".titreSwitch{" + 
                                                "width:40%;" + 
                                                "text-align:right;" + 
                                                "padding-top:9px;" + 
                                            "}" + 
                                            ".btnSwitch{" + 
                                                "width:20%;" + 
                                                "height:35px;" + 
                                                "font-size:0.9rem;" + 
                                                "font-weight:bold;" + 
                                                "background-color:#1fa3ec63;" +
                                            "}" + 
                                            ".bdis{" + 
                                                "background:#888;" + 
                                            "}" + 
                                            ".bdis:hover{" + 
                                                "background:#888;"
                                            "}" +
                                        "</style>" +
                                        "<legend><b title='sensorPompe'>Etat de la Pompe Vide-Cave & Capteurs</b></legend>" +
                                        "<div class='parametre'>" + 
                                            "<div>Dernière mise en route: </div>" + 
                                            "<div>" + string.split(afficheDateTime(self.parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["ON"], ""), " ")[1] + "</div>" + 
                                        "</div>" + 
                                        "<div class='parametre'>" + 
                                            "<div>Nb. de cycles du jour: </div>" + 
                                            "<div>" + str(self.parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["nbCyclesJour"]) + "</div>" + 
                                        "</div>" + 
                                        "<div class='parametre'>" + 
                                            "<div>Intervalle de fonctionnement moyen: </div>" + 
                                            "<div>" + str(int(self.parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["delai"] / 60)) + "min" + "</div>" + 
                                        "</div>"			
                    for nb:0 .. self.nbSwitchsActives - 1
                        var capteur = self.parametres["modules"]["pompeVideCave"]["environnement"]["capteurs"]["capteur" + str(nb+1)]
                        sensorPompeCave += "<div class='parametre'>" + 
                                            "<div class='titreSwitch'>" + capteur["nom"] + " :</div>" + 
                                            "<button class='btnSwitch'>" + self.sensors['Switch' + str(capteur["id"])] + "</button>" +
                                        "</div>"			
                    end
                    sensorPompeCave +=		"</fieldset>" + 
                                "</table>"
			tasmota.web_send(sensorPompeCave)
		end
	end	

	# Envoi des parametres à la page web
	def envoiJson()
        import json
        import webserver

		var jsonRequete = {}
		var typeModule = (webserver.has_arg('module') ? webserver.arg('module') : '')
		var categorie = (webserver.has_arg('categorie') ? webserver.arg('categorie') : '')
        var commande = (webserver.has_arg('commande') ? webserver.arg('commande') : '')

        # Test
        print("------------------------ envoiJson -----------------------")
        print("typeModule=" + str(typeModule))
        print("categorie=" + str(categorie))
        print("commande=" + str(commande))
	
		# Si une commande est envoyée
        if (commande != "" )
            var reponse = traiteCommandeHTTP(typeModule, categorie, commande)
            
            # Ne renvoie pas de json si commande = "modifParam"
            if (commande == "modifParam")
                jsonRequete.insert("Succes", reponse)
                webserver.content_response(json.dump(jsonRequete))

                return
            elif (commande == "jsonSensors")
                return
            end
        end

        # Détermine quelle partie du json est envoyée à la page web
        if (typeModule != "")
            if (typeModule == "serveur" || typeModule == "diverses")
                jsonRequete.insert(typeModule, self.parametres[typeModule])
            else
                jsonRequete.insert(typeModule, self.parametres["modules"][typeModule])
                jsonRequete.insert("componentes", self.parametres["modele"]["componentes"])
            end
                    
            webserver.content_response(json.dump(jsonRequete))
        else
            webserver.content_response(json.dump(self.parametres))
        end
    end

    # Gestion de l'affichage de la page des paramètres des capteurs pour réglage
	def affichePageParametres()
        import string
        import webserver

		var titreHTML = ""
        var tempFile = ""
        var buffer = ""
		
		# Gère la réponse au bouton 
		# Requete XMLHttpResponse : Corps de la page
		if webserver.has_arg("module") && webserver.has_arg("categorie")
			titreHTML = "Paramètres des modules"
			self.formSelection = webserver.arg("module")
			self.categorieSelection = webserver.arg("categorie")
			
			log (string.format("WEBSERVER: Affichage de la page des parametres du module '%s' !", self.formSelection), LOG_LEVEL_DEBUG)

            # Vérifie si la catégorie est contenu dans le module
            if self.formSelection != "serveur" && self.formSelection != "diverses"
            else
                if self.categorieSelection != "generale" && self.parametres[self.formSelection].find(self.categorieSelection) == nil
                    log (string.format("WEBSERVER: Redirection vers la page '%s' !", "/modules?module=" + self.formSelection + "&categorie=generale"), LOG_LEVEL_DEBUG)
                    webserver.redirect("/modules?module=" + self.formSelection + "&categorie=generale")   
                end            
            end

			# Démarrage la page
			webserver.content_start(titreHTML)
			webserver.content_send_style()		

            # Envoi les scripts css
            webserver.content_send(str(readFile("/sd/css/main.css")))

			# Envoi le formulaire de selection de module
            tempFile = readFile("/sd/html/formSelectParametres.html")
            for cle: self.parametres.keys()
                if type(self.parametres[cle]) != "instance"
                    continue
                end	
                if cle == "serveur"
                    buffer += "<option value='" + cle + "' " + (self.formSelection == cle ? "selected" : "") + ">Serveur</option>"
                elif cle == "diverses"
                    buffer += "<option value='" + cle + "' " + (self.formSelection == cle ? "selected" : "") + ">Divers</option>"
                elif cle == "modules"
                    for cleModule: self.parametres[cle].keys()
                        if type(self.parametres[cle][cleModule]) != "instance"
                            continue
                        end	
                        
                        buffer += "<option value='" + cleModule + "' " + (self.formSelection == cleModule ? "selected" : "") + ">" + self.parametres[cle][cleModule]["name"] + "</option>"
                    end
                end
            end
            tempFile = string.replace(tempFile, "##SELECT_OPTION_MODULES##", buffer)

			# Envoi la page web
            # Envoi le formulaire de selection de categorie dans le module
			if self.formSelection == "serveur"
                # Envoi le formulaire de selection de categorie dans le module
                buffer = "<div style='display:block;'>" + 
                            "<label>Catégorie :</label>" + 
                            "<select id='categorie' placeholder='Sélectionnez la catégorie'>" + 
                                "<option value='generale' " + (self.categorieSelection == "generale" ? "selected" : "") + ">Général</option>" + 
                                "<option value='wifi' " + (self.categorieSelection == "wifi" ? "selected" : "") + ">Wifi</option>" + 
                                "<option value='localisation' " + (self.categorieSelection == "localisation" ? "selected" : "") + ">Localisation</option>" + 
                                "<option value='fuseauHoraire' " + (self.categorieSelection == "fuseauHoraire" ? "selected" : "") + ">Fuseau Horaire</option>" + 
                                "<option value='mqtt' " + (self.categorieSelection == "mqtt" ? "selected" : "") + ">MQTT</option>" + 
                                "<option value='web' " + (self.categorieSelection == "web" ? "selected" : "") + ">Server Web</option>" + 
                            "</select>" + 
                        "</div>"
                tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
                webserver.content_send(tempFile)

				# Début du formulaire
                tempFile = readFile("/sd/html/pageParamServeur.html")
                webserver.content_send(tempFile)

                # Envoi les scripts javascript
                tempFile = readFile("/sd/js/main.js")
                webserver.content_send(tempFile)

                tempFile = readFile("/sd/js/jsParamServeur.js")
                webserver.content_send(tempFile)
			elif self.formSelection == "diverses"
                # Envoi le formulaire de selection de categorie dans le module
                tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", "")
                webserver.content_send(tempFile)

				# Début du formulaire
                tempFile = readFile("/sd/html/pageParamDiverses.html")
                webserver.content_send(tempFile)

                # Envoi les scripts javascript
                tempFile = readFile("/sd/js/main.js")
                webserver.content_send(tempFile)

                tempFile = readFile("/sd/js/jsParamDiverses.js")
                webserver.content_send(tempFile)
            else
                buffer = "<div style='display:block;'>" + 
                            "<label>Catégorie :</label>" + 
                            "<select id='categorie' placeholder='Sélectionnez la catégorie'>" + 
                                "<option value='boutons'>Boutons</option>" + 
                                "<option value='relais'>Relais</option>" + 
                                "<option value='capteurs'>Capteurs</option>" + 
                                "<option value='thermometres'>Capteurs de température</option>" + 
                                "<option value='autres'>Autres</option>" + 
                                "<option value='' selected></option>" + 
                            "</select>" + 
                        "</div>"
                tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
                webserver.content_send(tempFile)

                # Début du formulaire
                if (self.formSelection == "Thermo-Hygrometre" || self.formSelection == "pompeVideCave" || self.formSelection == "autres")
                    tempFile = readFile("/sd/html/pageParam.html")
                end
                webserver.content_send(tempFile)

                # Envoi les scripts javascript
                tempFile = readFile("/sd/js/main.js")
                webserver.content_send(tempFile)

                if (self.formSelection == "Thermo-Hygrometre" || self.formSelection == "pompeVideCave" || self.formSelection == "autres")
                    tempFile = readFile("/sd/js/jsParam.js")
                end
                webserver.content_send(tempFile)
			end

			#- end of web page -#
			webserver.content_stop()			
		end
    end

    # Modifie l'état des capteurs pour test
    def etatCapteurs()
        import string
        import webserver

		var titreHTML = ""
        var tempFile = ""
        var buffer = ""
		
		# Gère la réponse au bouton 
		# Requete XMLHttpResponse : Corps de la page
		if webserver.has_arg("module")
			titreHTML = "Modif. Capteurs"
			self.formSelection = webserver.arg("module")
			
			log (string.format("WEBSERVER: Affichage de la page de modification des capteurs du module '%s' !", self.formSelection), LOG_LEVEL_DEBUG)

			# Démarrage la page
			webserver.content_start(titreHTML)
			webserver.content_send_style()	
            
            # Envoi les scripts css
            webserver.content_send(str(readFile("/sd/css/main.css")))

			# Envoi le formulaire de selection de module
            tempFile = readFile("/sd/html/formSelectParametres.html")
            for cle: self.parametres.keys()
                if type(self.parametres[cle]) != "instance"
                    continue
                end	
                if cle == "serveur"
                    buffer += "<option value='" + cle + "' " + (self.formSelection == cle ? "selected" : "") + ">Serveur</option>"
                elif cle == "diverses"
                    buffer += "<option value='" + cle + "' " + (self.formSelection == cle ? "selected" : "") + ">Divers</option>"
                elif cle == "modules"
                    for cleModule: self.parametres[cle].keys()
                        if type(self.parametres[cle][cleModule]) != "instance"
                            continue
                        end	
                        
                        buffer += "<option value='" + cleModule + "' " + (self.formSelection == cleModule ? "selected" : "") + ">" + self.parametres[cle][cleModule]["name"] + "</option>"
                    end
                end
            end
            tempFile = string.replace(tempFile, "##SELECT_OPTION_MODULES##", buffer)

            # Envoi le formulaire de selection de categorie dans le module
            tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", "")
            webserver.content_send(tempFile)

            # Début du formulaire
            tempFile = readFile("/sd/html/pageModifCapteurs.html")
            webserver.content_send(tempFile)

            # Envoi les scripts javascript
            tempFile = readFile("/sd/js/main.js")
            webserver.content_send(tempFile)

            tempFile = readFile("/sd/js/jsModifCapteurs.js")
            webserver.content_send(tempFile)
    
			#- end of web page -#
			webserver.content_stop()    
        end
    end

	#- Création de boutons dans le menu principal -#
	def web_add_main_button()
        import webserver

        log ("WEBSERVER: Affichage du bouton !", LOG_LEVEL_DEBUG)
		webserver.content_send("<p></p><button class='button bgrn' onclick='window&#46;location&#46;href=\"/modules?module=serveur&categorie=generale\"'>Réglages des modules</button>")
        webserver.content_send("<p></p><button class='button bgrn' onclick='window&#46;location&#46;href=\"/capteurs?module=pompeVideCave\"'>Etat des capteurs</button>")
    end	

	# Charge les appels aux fonctions selon l'url
	def web_add_handler()
        import webserver

        webserver.on("/modules", / -> self.affichePageParametres(), webserver.HTTP_GET)	
		webserver.on("/json", / -> self.envoiJson(), webserver.HTTP_ANY)	
        webserver.on("/capteurs", / -> self.etatCapteurs(), webserver.HTTP_GET)	
	end
end

# Charge la gestion des pages web
# gestionWeb = GESTION_WEB()
# tasmota.add_driver(gestionWeb)	
# gestionWeb.web_add_handler()