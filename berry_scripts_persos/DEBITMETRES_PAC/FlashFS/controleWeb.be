# Gestion des pages internet globales sans tenir compte des modules activés en json
# Données GET & POST utilisées :
#	module : quel chapitre du json sera demandé
#   environnement : sous-module
#	modifParam : quel est le chapitre qui sera modifié par requête
# 	script : le type de script 'javascript' demandé par le serveur
#	commande : type de commande berry à réaliser

# Attention : autoriser l'access-crossing sur le site distant si vous y accédez
# Ajouter 'dans la section <Directory> de 'httpd.conf' d'Apache2 : Header set Access-Control-Allow-Origin "*"
# Ajouter le fichier 'componentes.json' dans le dossier de votre serveur

var controleWeb

class CONTROLE_WEB
    # Variables
	var parametres
    var formSelection
    var categorieSelection
    var sensors

    def init()
        self.formSelection = ""
        self.categorieSelection = ""
    end

    def every_second()
    end

	# Envoi des parametres à la page web
	def envoiJson()
        import json
        import webserver
        import webFonctions

		var jsonRequete = {}
        var jsonRequete2 = ""
		var typeModule = (webserver.has_arg('module') ? webserver.arg('module') : '')
		var categorie = (webserver.has_arg('categorie') ? webserver.arg('categorie') : '')
        var commande = (webserver.has_arg('commande') ? webserver.arg('commande') : '')

        # Test   
        log ("ENVOI_JSON: -------------------- envoiJson -------------------", LOG_LEVEL_DEBUG_PLUS)
        log ("ENVOI_JSON: typeModule=" + str(typeModule), LOG_LEVEL_DEBUG_PLUS)
        log ("ENVOI_JSON: categorie=" + str(categorie), LOG_LEVEL_DEBUG_PLUS)
        log ("ENVOI_JSON: commande=" + str(commande), LOG_LEVEL_DEBUG_PLUS)
	
		# Si une commande est envoyée
        if (commande != "" )
            var reponse = webFonctions.traiteCommandeHTTP(typeModule, categorie, commande)
            
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
                jsonRequete.insert(typeModule, controleGeneral.parametres[typeModule])
            else
                jsonRequete.insert(typeModule, controleGeneral.parametres["modules"][typeModule])
            end
        else
            jsonRequete = controleGeneral.parametres
        end
        webserver.content_response(json.dump(jsonRequete))
    end

    # Gestion de l'affichage de la page des paramètres des capteurs pour réglage
	def affichePageParametres()
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
			
			log (string.format("WEBSERVER: Affichage de la page des parametres du module '%s' !", self.formSelection), LOG_LEVEL_DEBUG)

            # Vérifie si la catégorie est contenu dans le module
            if self.formSelection != "serveur" && self.formSelection != "diverses"
                if controleGeneral.parametres["modules"]["activation"] == "ON"  && !controleGeneral.parametres["modules"][self.formSelection]["environnement"].find(self.categorieSelection, false)
                    for cleEnv: controleGeneral.parametres["modules"][self.formSelection]["environnement"].keys()
                        log (string.format("WEBSERVER: Redirection vers la page '%s' !", "/modules?module=" + self.formSelection + "&categorie=" + cleEnv), LOG_LEVEL_DEBUG)
                        webserver.redirect("/modules?module=" + self.formSelection + "&categorie=" + cleEnv)  
                        return
                    end
                end
            else
                if self.categorieSelection != "generale" && !controleGeneral.parametres[self.formSelection].find(self.categorieSelection, false)
                    log (string.format("WEBSERVER: Redirection vers la page '%s' !", "/modules?module=" + self.formSelection + "&categorie=generale"), LOG_LEVEL_DEBUG)
                    webserver.redirect("/modules?module=" + self.formSelection + "&categorie=generale")   
                end            
            end

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
			if self.formSelection == "serveur"
                # Envoi le formulaire de selection de categorie dans le module
                buffer = "<div style='display:block;'>" + 
                            "<label>Catégorie :</label>" + 
                            "<select id='categorie' placeholder='Sélectionnez la catégorie'>" + 
                                "<option value='generale' " + (self.categorieSelection == "generale" ? "selected" : "") + ">Général</option>" + 
                                "<option value='wifi' " + (self.categorieSelection == "wifi" ? "selected" : "") + ">Wifi</option>" + 
                                "<option value='mqtt' " + (self.categorieSelection == "mqtt" ? "selected" : "") + ">MQTT</option>" + 
                                "<option value='web' " + (self.categorieSelection == "web" ? "selected" : "") + ">Serveur Web</option>" + 
                                "<option value='rangeExtender' " + (self.categorieSelection == "rangeExtender" ? "selected" : "") + ">Range Extender</option>" + 
                                "<option value='serveurFTP' " + (self.categorieSelection == "serveurFTP" ? "selected" : "") + ">Serveur FTP</option>" + 
                            "</select>" + 
                        "</div>"
                tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
                webserver.content_send(tempFile)

				# Début du formulaire
                gestionFileFolder.readFileByLineAndContentSend("/sd/html/pageParamServeur.html")

                # Envoi les scripts javascript
                gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
                gestionFileFolder.readFileByLineAndContentSend("/sd/js/jsParamServeur.js")
			elif self.formSelection == "diverses"
                # Envoi le formulaire de selection de categorie dans le module
                buffer = "<div style='display:block;'>" + 
                            "<label>Catégorie :</label>" + 
                            "<select id='categorie' placeholder='Sélectionnez la catégorie'>" + 
                                "<option value='generale' " + (self.categorieSelection == "generale" ? "selected" : "") + ">Général</option>" + 
                                "<option value='localisation' " + (self.categorieSelection == "localisation" ? "selected" : "") + ">Localisation</option>" + 
                                "<option value='fuseauHoraire' " + (self.categorieSelection == "fuseauHoraire" ? "selected" : "") + ">Fuseau Horaire</option>" + 
                            "</select>" + 
                        "</div>"
                tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
                webserver.content_send(tempFile)

				# Début du formulaire
                gestionFileFolder.readFileByLineAndContentSend("/sd/html/pageParamDiverses.html")

                # Envoi les scripts javascript
                gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
                gestionFileFolder.readFileByLineAndContentSend("/sd/js/jsParamDiverses.js")
            else
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
                gestionFileFolder.readFileByLineAndContentSend("/sd/html/pageParam.html")
                webserver.content_send("<div style='display:none;' id='componentes'>")
                    gestionFileFolder.readFileByLineAndContentSend("/componentes.json")
                webserver.content_send("</div>")

                # Envoi les scripts javascript
                gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
                gestionFileFolder.readFileByLineAndContentSend("/sd/js/jsParam.js")
			end

			#- end of web page -#
			webserver.content_stop()			
		end
    end

	#- Création de boutons dans le menu principal -#
	def web_add_main_button()
        import webserver

        log ("WEBSERVER: Affichage du bouton !", LOG_LEVEL_DEBUG)
		webserver.content_send("<p></p><button class='button bgrn' onclick='window&#46;location&#46;href=\"/modules?module=serveur&categorie=generale\"'>Réglages des modules</button>")
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
controleWeb = CONTROLE_WEB()
tasmota.add_driver(controleWeb)	
controleWeb.web_add_handler()