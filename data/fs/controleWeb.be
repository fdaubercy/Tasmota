#- 
    - Gestion des pages internet globales sans tenir compte des modules activés en json
    - Données GET & POST utilisées :
        * module : quel chapitre du json sera demandé
    - environnement : sous-module
        * modifParam : quel est le chapitre qui sera modifié par requête
        * script : le type de script 'javascript' demandé par le serveur
        * commande : type de commande berry à réaliser

    - Attention : autoriser l'access-crossing sur le site distant si vous y accédez
    - Ajouter 'dans la section <Directory> de 'httpd.conf' d'Apache2 : Header set Access-Control-Allow-Origin "*"
    - Ajouter le fichier '/jsoncomponentes.json' dans le dossier de votre serveur 
-#

var controleWeb

class CONTROLE_WEB
    # Variables
    var formSelection
    var categorieSelection

    def init()
        import webFonctions
        
        self.formSelection = ""
        self.categorieSelection = ""

        # log("WEBSERVER: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
		# Déclenche une action tous les jours à minuit
	    # tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        tasmota.add_rule("System", def(value, trigger, msg) webFonctions.changementEtatDemarrage(value, trigger, msg) end)	
        # tasmota.add_rule("Wifi", def(value, trigger, msg) webFonctions.changementEtatDemarrage(value, trigger, msg) end)
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) webFonctions.changementEtatDemarrage(value, trigger, msg) end)
    end

    def every_second()
    end

	# Envoi des parametres à la page web
	def envoiJson()
        import webFonctions
        import webserver
        import json
        import persist

		var jsonRequete = {}
		var typeModule = (webserver.has_arg('module') ? webserver.arg('module') : '')
		var categorie = (webserver.has_arg('categorie') ? webserver.arg('categorie') : '')
        var commande = (webserver.has_arg('commande') ? webserver.arg('commande') : '')

        # Test   
        webFonctions.log("ENVOI_JSON: -------------------- envoiJson -------------------", LOG_LEVEL_DEBUG_PLUS)
        webFonctions.log("ENVOI_JSON: typeModule=" + str(typeModule), LOG_LEVEL_DEBUG_PLUS)
        webFonctions.log("ENVOI_JSON: categorie=" + str(categorie), LOG_LEVEL_DEBUG_PLUS)
        webFonctions.log("ENVOI_JSON: commande=" + str(commande), LOG_LEVEL_DEBUG_PLUS)

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
            # Vient d'executé une commande Tasmota paramétrée +/- Redémarre
            else
                jsonRequete.insert("Succes", reponse)
            end
        end

        # Détermine quelle partie du json est envoyée à la page web
        if (typeModule != "")
            if (typeModule == "serveur" || typeModule == "diverses")
                jsonRequete.insert(typeModule, persist._p[typeModule])
            else
                jsonRequete.insert(typeModule, persist.modules[typeModule])
            end
        else
            for item: persist._p.keys()
                jsonRequete.insert(item, persist._p[item])
            end
        end
        webserver.content_response(json.dump(jsonRequete))
    end

    # Gestion de l'affichage de la page des paramètres des capteurs pour réglage
	def affichePageParametres()
        import webserver
        import gestionFileFolder
        import string
        import webFonctions
        import persist

        var titreHTML = ""
        var tempFile = ""
        var buffer = ""
        var parametres = persist.find("parametres")

		# Gère la réponse au bouton 
		# Requete XMLHttpResponse : Corps de la page
		if !webserver.has_arg("module") || !webserver.has_arg("categorie")    return      end
        
        titreHTML = "Paramètres des modules"
        self.formSelection = webserver.arg("module")
        self.categorieSelection = webserver.arg("categorie")

        # Vérifie si la catégorie est contenu dans le module
        # if self.formSelection != "serveur" && self.formSelection != "diverses"
        #     if persist.parametres["modules"]["activation"] == "ON"  && !persist.parametres["modules"][self.formSelection]["environnement"].find(self.categorieSelection, false)
        #         for cleEnv: persist.parametres["modules"][self.formSelection]["environnement"].keys()
        #             webFonctions.log(string.format("WEBSERVER: Redirection vers la page '%s' !", "/modules?module=" + self.formSelection + "&categorie=" + cleEnv), LOG_LEVEL_DEBUG)
        #             webserver.redirect("/modules?module=" + self.formSelection + "&categorie=" + cleEnv)  
        #             return
        #         end
        #     end
        # else
        #     if self.categorieSelection != "generale" && !persist.parametres[self.formSelection].find(self.categorieSelection, false)
        #         webFonctions.log(string.format("WEBSERVER: Redirection vers la page '%s' !", "/modules?module=" + self.formSelection + "&categorie=generale"), LOG_LEVEL_DEBUG)
        #         webserver.redirect("/modules?module=" + self.formSelection + "&categorie=generale")   
        #     end        
        # end

		# Démarrage la page
		webserver.content_start(titreHTML)
		webserver.content_send_style()	

        # Envoi les scripts css
        gestionFileFolder.readFileByLineAndContentSend("/sd/css/main.css")

		# Envoi le formulaire de selection de module
        tempFile = gestionFileFolder.readFile("/sd/html/formSelectParametres.html")
        buffer += "<option value='serveur' " + (self.formSelection == "serveur" ? "selected" : "") + ">Serveur</option>"
        buffer += "<option value='diverses' " + (self.formSelection == "diverses" ? "selected" : "") + ">Divers</option>"

        var tabParam = ["modules", "drivers"]
        for nb: 0 .. tabParam.size() - 1
            var cle = tabParam[nb]
            for cleModule: persist._p[cle].keys()
                if (type(persist._p[cle][cleModule]) != "instance")     continue   end	
                buffer += "<option value='" + cleModule + "' " + (self.formSelection == cleModule ? "selected" : "") + ">" + persist._p[cle][cleModule]["name"] + "</option>"
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
                            "<option value='udp' " + (self.categorieSelection == "udp" ? "selected" : "") + ">Connexion UDP</option>" + 
                        "</select>" + 
                    "</div>"
            tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
            webserver.content_send(tempFile)

		# Début du formulaire
            gestionFileFolder.readFileByLineAndContentSend("/sd/html/pageParamServeur.html")

        # Envoi les scripts javascript
        #     gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
        #     gestionFileFolder.readFileByLineAndContentSend("/sd/js/jsParamServeur.js")
		elif self.formSelection == "diverses"
            # Envoi le formulaire de selection de categorie dans le module
            buffer = "<div style='display:block;'>" + 
                        "<label>Catégorie :</label>" + 
                        "<select id='categorie' placeholder='Sélectionnez la catégorie'>" + 
                            "<option value='generale' " + (self.categorieSelection == "generale" ? "selected" : "") + ">Général</option>" + 
                            "<option value='logs' " + (self.categorieSelection == "logs" ? "selected" : "") + ">Enregistrements Logs</option>" + 
                            "<option value='localisation' " + (self.categorieSelection == "localisation" ? "selected" : "") + ">Localisation</option>" + 
                            "<option value='fuseauHoraire' " + (self.categorieSelection == "fuseauHoraire" ? "selected" : "") + ">Fuseau Horaire</option>" + 
                        "</select>" + 
                    "</div>"
            tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
            webserver.content_send(tempFile)

		# Début du formulaire
            gestionFileFolder.readFileByLineAndContentSend("/sd/html/pageParamDiverses.html")

        # Envoi les scripts javascript
        #     gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
        #     gestionFileFolder.readFileByLineAndContentSend("/sd/js/jsParamDiverses.js")
        else
            buffer = "<div style='display:block;'>" + 
                        "<label>Catégorie :</label>" + 
                        "<select id='categorie' placeholder='Sélectionnez la catégorie'>" + 
                            "<option value='generale' " + (self.categorieSelection == "generale" ? "selected" : "") + ">Général</option>"
            if (persist._p["modules"][self.formSelection].find("logs", false))
                buffer += "<option value='logs' " + (self.categorieSelection == "logs" ? "selected" : "") + ">Enregistrements Logs</option>"
            end
            if (persist._p["modules"].find(self.formSelection, false))
                if (persist._p["modules"][self.formSelection]["environnement"].find("boutons", false))
                    buffer += "<option value='boutons' " + (self.categorieSelection == "boutons" ? "selected" : "") + ">Boutons</option>"
                end
                if (persist._p["modules"][self.formSelection]["environnement"].find("capteurs", false))
                    buffer += "<option value='capteurs' " + (self.categorieSelection == "capteurs" ? "selected" : "") + ">Capteurs</option>"
                end
                if (persist._p["modules"][self.formSelection]["environnement"].find("thermometres", false))
                    buffer += "<option value='thermometres' " + (self.categorieSelection == "thermometres" ? "selected" : "") + ">Capteurs de température</option>"
                end
                if (persist._p["modules"][self.formSelection]["environnement"].find("debitmetres", false))
                    buffer += "<option value='debitmetres' " + (self.categorieSelection == "debitmetres" ? "selected" : "") + ">Débitmètres</option>"
                end
                if (persist._p["modules"][self.formSelection]["environnement"].find("analogiques", false))
                    buffer += "<option value='debitmetanalogiquesres' " + (self.categorieSelection == "analogiques" ? "selected" : "") + ">Entrées analogiques</option>"
                end
                if (persist._p["modules"][self.formSelection]["environnement"].find("interrupteurs", false))
                    buffer += "<option value='interrupteurs' " + (self.categorieSelection == "interrupteurs" ? "selected" : "") + ">Interrupteurs</option>"
                end
                if (persist._p["modules"][self.formSelection]["environnement"].find("leds", false))
                    buffer += "<option value='leds' " + (self.categorieSelection == "leds" ? "selected" : "") + ">Leds</option>"
                end
                if (persist._p["modules"][self.formSelection]["environnement"].find("relais", false))
                    buffer += "<option value='relais' " + (self.categorieSelection == "relais" ? "selected" : "") + ">Relais</option>"
                end

            end
        #                     "<option value='pinsSDs'>Connexion Carte SD</option>" + 
        #                     "<option value='pinsEcrans'>Connexion Ecran</option>" + 
        #                     "<option value='' selected></option>" + 
            buffer += "</select>" + 
                    "</div>"

            tempFile = string.replace(tempFile, "##SELECT_OPTION_CATEGORIES##", buffer)
            webserver.content_send(tempFile)

        #     # Début du formulaire
            # gestionFileFolder.readFileByLineAndContentSend("/sd/html/pageParam.html")
            webserver.content_send("<div style='display:none;' id='componentes'>")
                gestionFileFolder.readFileByLineAndContentSend("/json/componentes.json")
            webserver.content_send("</div>")

        #     # Envoi les scripts javascript
        #     gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
        #     gestionFileFolder.readFileByLineAndContentSend("/sd/js/jsParam.js")
		end

		#- end of web page -#
		webserver.content_stop()	
    end

    # Modifie l'état des capteurs pour test
    def etatCapteurs()
        import string
        import webserver
        import gestionFileFolder

		var titreHTML = ""
        var tempFile = ""
        var buffer = ""
		
		# Gère la réponse au bouton 
		# Requete XMLHttpResponse : Corps de la page
		if webserver.has_arg("module")
			titreHTML = "Modif. Capteurs"
			self.formSelection = webserver.arg("module")
			
			log(string.format("WEBSERVER: Affichage de la page de modification des capteurs du module '%s' !", self.formSelection), LOG_LEVEL_DEBUG)

			# Démarrage la page
			webserver.content_start(titreHTML)
			webserver.content_send_style()	
            
            # Envoi les scripts css
            webserver.content_send(str(gestionFileFolder.readFile("/sd/css/main.css")))

			# Envoi le formulaire de selection de module
            tempFile = gestionFileFolder.readFile("/sd/html/formSelectParametres.html")
            for cle: self.parametres.keys()
                if (type(self.parametres[cle]) != "instance")   continue    end	
                tasmota.yield()
                
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
            tempFile = gestionFileFolder.readFile("/sd/html/pageModifCapteurs.html")
            webserver.content_send(tempFile)

            # Envoi les scripts javascript
            tempFile = gestionFileFolder.readFile("/sd/js/main.js")
            webserver.content_send(tempFile)

            tempFile = gestionFileFolder.readFile("/sd/js/jsModifCapteurs.js")
            webserver.content_send(tempFile)
    
			#- end of web page -#
			webserver.content_stop()    
        end
    end

	#- Création de boutons dans le menu principal -#
    # Affiche les paramétres des leds WS2812 virtuelles
    # Affichage des réglages de SCHEME sur webUI
	def web_add_main_button()
        import webserver
        import webFonctions
		import gestionFileFolder

        # Affiche les paramétres des leds WS2812 virtuelles
        if (controleGeneral.nbIOActivesJSON["WS2812"]["actives"].find("nb", 0) > controleGeneral.nbIOActivesJSON["WS2812"]["reels"].find("nb", 0))
            webFonctions.log("WEBSERVER: Affichage des paramètres des leds virtuelles sur webUI !", LOG_LEVEL_DEBUG)
            gestionFileFolder.readFileByLineAndContentSend("/sd/html/ledVirtuel.html")
        end

		tasmota.yield()

		# Détermine si des leds WS2812 sont activées
        webFonctions.log("WEBSERVER: Affichage des réglages de SCHEME sur webUI !", LOG_LEVEL_DEBUG)
		if (controleGeneral.nbIOActivesJSON["WS2812"]["reels"].find("nb", 0) > 0)
            gestionFileFolder.readFileByLineAndContentSend("/sd/js/main.js")
            gestionFileFolder.readFileByLineAndContentSend("/sd/html/formSelectSchemeWS2812.html")

            var javascript = 	"<script type='application/javascript'>" + 
                                    "document.getElementById('scheme').value = '" + str(int(tasmota.cmd("Scheme", boolMute)["Scheme"])) + "';"
                                "</script>"
            webserver.content_send(javascript)
        end
    end

	#- Création de boutons dans le menu 'Tools' -#
    # Bouton de gestion des paramétrage de modules
    def web_add_management_button()
        import webserver
        import webFonctions

        # Affiche le bouton de réglage des paramètres Tasmota enregistrés en json
        webFonctions.log("WEBSERVER: Affichage du bouton !", LOG_LEVEL_DEBUG)
		webserver.content_send("<p></p><button class='button bgrn' onclick='window.location.href=\"/modules?module=serveur&categorie=generale\"'>Réglages des modules</button>")
    end	

	# Charge les appels aux fonctions selon l'url
	def web_add_handler()
        import webserver
        import webFonctions

        tasmota.yield()

        webserver.on("/modules", / -> self.affichePageParametres(), webserver.HTTP_GET)	
		webserver.on("/json", / -> self.envoiJson(), webserver.HTTP_ANY)	
        webserver.on("/capteurs", / -> self.etatCapteurs(), webserver.HTTP_GET)	
        webserver.on("/wss", / -> webFonctions.htmlWebSocket(), webserver.HTTP_ANY)	
	end
end

# Active le Driver d'affichage des pages web
controleWeb = CONTROLE_WEB()
tasmota.add_driver(controleWeb)	
controleWeb.web_add_handler()
