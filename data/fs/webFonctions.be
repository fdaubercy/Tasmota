# Définition du module
var webFonctions = module("/webFonctions")

webFonctions.DEBUG = nil

webFonctions.log = def(msg, levelDebug)
	if (webFonctions.DEBUG == nil)
        webFonctions.DEBUG = serveur.find("debug", "OFF")
    end

    if (webFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

# exemples: 
# ReglageWeb logActivation OFF
webFonctions.reglageWeb = def(cmd, idx, payload, payload_json)
    import string
    import json

    var fonction = false
    var parametres = false
    var reponse_cmnd = ""
    
    # Test   
    webFonctions.log("REGLAGE_WEB: -------------------- reglageGlobal -------------------", LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("REGLAGE_WEB: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("REGLAGE_WEB: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("REGLAGE_WEB: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("REGLAGE_WEB: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 2)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    webFonctions.log("REGLAGE_WEB: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    (parametres[0] ? webFonctions.log("REGLAGE_WEB: parametre=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS) : "")
    (parametres[1] ? webFonctions.log("REGLAGE_WEB: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS) : "")

    # Activation ou désactivation des logs du WebServeur -> ordre: logActivation
    if string.toupper(fonction) == "LOGACTIVATION"
        # Adapte le paramètre
        parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
        webFonctions.DEBUG = parametres[0]

        # Sauvegarde le paramètre
        serveur["rangeExtender"]["debug"] = webFonctions.DEBUG
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd = string.format("ReglageWeb: logActivated=%s", webFonctions.DEBUG)
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
webFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt

	# Test
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: -------------------- webServer changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    tasmota.yield()

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
        elif msg["WIFI"].find("Disonnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    # Save: Avant redemarrage de tasmota
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            import gestionFileFolder

            # webFonctions.tcp = tcpserver(webFonctions.port)
            # webFonctions.log(">>>>>>>>>>>>>>>>>>>>>>>>>>>TCP_SERVEUR: Connexion: OK", LOG_LEVEL_DEBUG)

            # Parcours tous les modules à la recherche de leds WS2812
            for cleModule: modules.keys()
                tasmota.yield()
        
                if (type(modules[cleModule]) != "instance")   continue      end
        
                # Si le module est activé
                if modules[cleModule].find("activation", "OFF") == "ON"
                    var env = modules[cleModule]["environnement"]

                    var relais = env.find("relais", false)
                    if (relais)
                        for cleRLY: relais.keys()
                            if type(relais[cleRLY]) != "instance"   continue    end
                            tasmota.yield()

        			        # Si le relai est activé
        			        if relais[cleRLY].find("activation", "OFF") == "ON" && ((relais[cleRLY].find("pin", -1) != -1  && relais[cleRLY].find("virtuel", "OFF") == "OFF") || relais[cleRLY].find("virtuel", "OFF") != "OFF")
                                # Nb de relai réels (non-virtuels)
                                if relais[cleRLY].find("activation", "OFF") == "ON" && relais[cleRLY].find("virtuel", "OFF") == "OFF"
                                
                                    # Relais de type "WS2812"
                                    if (relais[cleRLY]["type"] == 1376)
                                        if (relais[cleRLY]["nbLeds"] > 1)       
                                            # gestionFileFolder.loadBerryFile("/leds_panel", "ON", "OFF")     

                                            import introspect

                                            var leds_panel = introspect.module('leds_panel', true)     # load module but don't cache
                                            if (leds_panel != nil)
                                                tasmota.add_driver(leds_panel, "leds_panel")
                                            end
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        elif msg[trigger].find("Save", 0)
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
    end
end

# Classe TCP Client
# Retourne la réponse du serveur
webFonctions.clientWeb = def(url, typeRequest, data, etatConnexion)
    import json

	var webClient
	var codeReponse
	var reception
	
	# Si le module n'est pas connecté
	if !etatConnexion return end 
	
	# Vérifie les données à envoyer en fonction du type de requête
	if typeRequest == nil typeRequest = "GET" end
	if data == nil data = '' end
	
	# Prépare les données à transmettre en vérifiant son type
	if data != nil  && type(data) == "instance"
		data = json.dump(data)
	end
	
	if typeRequest == "GET" && data != '' 
		url += "?" + data 
	end
	
	# Initialise le client web
	webClient = webclient()
	
	# Paramètre les headers nécessaires
	webClient.set_follow_redirects(false)
	webClient.collect_headers("Location")
	
	webClient.url_encode(url)
	webClient.begin(str(url))
	
	# Envoi la requête
	if typeRequest == "GET"
		codeReponse = webClient.GET()
	elif typeRequest == "POST"
		codeReponse = webClient.POST(data)
	elif typeRequest == "PUT"
		codeReponse = webClient.PUT()
	elif typeRequest == "DELETE"
		codeReponse = webClient.DELETE()
	end
	
	webClient.add_header("Content-Type", "application/x-www-form-urlencoded")
	
	# Réponse du naviguateur
	if codeReponse == 301 || codeReponse == 302
		webFonctions.log("GESTION_WEB: Code reponse=" + str(codeReponse) + " -> Serveur connecte mais avec redirection demandee -> Location: " +  webClient.get_header("Location") + " !", LOG_LEVEL_DEBUG_PLUS)
	elif codeReponse == 200
		webFonctions.log("GESTION_WEB: Code reponse=" + str(codeReponse) + " apres la requete '" + url + "' -> Serveur connecte !", LOG_LEVEL_DEBUG_PLUS)
	else 
		webFonctions.log("GESTION_WEB: Code reponse=" + str(codeReponse) + " apres la requete '" + url + "' -> Serveur deconnecte !", LOG_LEVEL_DEBUG_PLUS)
	end
	
	# Lit la réponse html
	reception = webClient.get_string()
	webFonctions.log("GESTION_WEB: Reponse HTML=" + reception + " !", LOG_LEVEL_DEBUG_PLUS)
	
	# Ferme la connexion
	webClient.close()
	
	return reception
end	

# Affiche une page pour initier un webSocket
webFonctions.htmlWebSocket = def()
    import webserver

	webserver.content_start("WebSocket Test")
	webserver.content_send_style()
		
	var html = "<script type='text/javascript'>" + 
					"var ws = new WebSocket('ws://192.168.0.43:8888');"
					"function WebSocketTest() {" + 
						"if ('WebSocket' in window) {" +
							"console.log('WebSocket is supported by your Browser!');" + 
							"/* Let us open a web socket */" + 
							"" +
							"ws.onopen = function() {" +
								"/* Web Socket is connected, send data using send() */" + 
								"ws.send('Message to send');" +
								"console.log('Message is sent...');" +
							"};" +
							"ws.onmessage = function (evt) {" + 
								"var received_msg = evt.data;" + 
								"console.log('Message is received...');"
							"};" +
							"ws.onclose = function() {" + 
								"/* websocket is closed. */" + 
								"console.log('Connection is closed...');" +
							"};" +
							"ws.onerror = function(error) {" + 
								"alert('[error]');" + 
							"};" + 
						"} else {" +
							"/* The browser doesn't support WebSocket */" +
							"console.log('WebSocket NOT supported by your Browser!');" +
						"}" + 
					"}" +
					"function WebSocketSend() {" + 
						"ws.send('Message to send');" +
						"console.log('Message is sent...');" +
					"}" +
				"</script>" +
				"<div id='sse'><a href='javascript:WebSocketTest()'>Run WebSocket</a></div>" + 
				"<div id='ssf'><a href='javascript:WebSocketSend()'>Send WebSocket</a></div>"
				
	webserver.content_send(html)
	webserver.content_stop()
end

#- 
    # Classe qui gère la connexion en tant que serveur TCP Async
    Tasmota ne gère pas encore les webSocket
    class tcpServeur
        var tcp
        var connexion

        def init(port)
            self.tcp = tcpserver(port)

            webFonctions.log("TCP_SERVEUR: Connexion: OK", LOG_LEVEL_DEBUG)

            tasmota.add_driver(self)
            tasmota.add_fast_loop(/-> self.fast_loop()) 
        end

        def fast_loop()
            import string

            # Vérifie si un client se connecte
            if !self.tcp.hasclient()
                #webFonctions.log(string.format("TCP_SERVEUR: Client non-connecté !"), LOG_LEVEL_DEBUG)
            else 
                if self.connexion == nil
                    webFonctions.log(string.format("TCP_SERVEUR: Client connecté !"), LOG_LEVEL_DEBUG)
                    self.connexion =  self.tcp.acceptasync()
                end
            end

            if self.connexion != nil
                var packet = self.connexion.read()

                if packet != nil && packet != "" && packet != "\n"
                    webFonctions.log(string.format("TCP_SERVEUR: Données reçues: "), LOG_LEVEL_DEBUG)
                end

                if packet != nil && packet != "" && packet != "\n"
                    print(packet)
                    packet = self.connexion.read()

                    # if string.find(packet, "GET") > -1
                    #     print("TRAME TROUVEE !!")
                    #     self.connexion.write("101 Switching Protocols")
                    #     self.connexion.write("Upgrade: websocket")
                    #     self.connexion.write("Connection: Upgrade")
                    # end
                end

                #self.connexion.close()
            end
        end
    end 
-#

# Modifie les paramètres en json
webFonctions.traiteCommandeHTTP = def(typeModule, categorie, commande)
    import string

    var resultat = ""

    # Test : Parcours les données POST recues
	webFonctions.log("WEBSERVER_TRAITE_COMMANDE: -------------------- webServer traiteCommandeHTTP -------------------", LOG_LEVEL_DEBUG)
    webFonctions.log("WEBSERVER_TRAITE_COMMANDE: typeModule=" + str(typeModule), LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("WEBSERVER_TRAITE_COMMANDE: categorie=" + str(categorie), LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("WEBSERVER_TRAITE_COMMANDE: commande=" + str(commande), LOG_LEVEL_DEBUG_PLUS)

    tasmota.yield()

    # Réalise l'action
	# Modifie un paramètre en json +/- Redémarre
    if (commande == "modifParam")
        webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Modification des paramètres en json !", LOG_LEVEL_DEBUG)
    # Execute une commande Tasmota paramétrée +/- Redémarre
    else
        webFonctions.log(string.format("WEBSERVER_TRAITE_COMMANDE: Exécute une commande Tasmota : %s!", "tasmota.cmd('" + commande + "')"), LOG_LEVEL_DEBUG)
        resultat = tasmota.cmd(commande)        #, boolMute)
    end

    return resultat

    # if (commande == "modifParam")
	# 	var parametres = persist.find("parametres")
    #     if typeModule == "Thermo-Hygrometre" || typeModule == "pompeVideCave" || typeModule == "autres"
	# 		parametres["modules"][typeModule] = json.load(webserver.arg("json"))[typeModule]
    #     elif typeModule == "serveur"
    #         parametres["serveur"] = json.load(webserver.arg("json"))
    #     end

    #     webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)	
    #     persist.parametres = parametres	
    #     persist.save() 

    #     # Reboot
    #     tasmota.cmd("Restart 1;", boolMute)
	# # Supprime un élément en json & Redémarre
    # elif (commande == "supprElement")
    #     webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Demande de suppression de l'élément " + webserver.arg("element") + " du module " + typeModule + " !", LOG_LEVEL_DEBUG)
        
	# 	var parametres = persist.find("parametres")
	# 	parametres["modules"][typeModule]["environnement"][categorie].remove(webserver.arg("element"))

    #     webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)	
    #     persist.parametres = parametres	
    #     persist.save() 

    #     # Reboot
    #     tasmota.cmd("Restart 1;", boolMute)
	# # Demande d'envoi du json sensors
    # elif (commande == "jsonSensors")
    #     webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Demande d'envoi du json sensors !", LOG_LEVEL_DEBUG)

	# 	var jsonRequete = {};
	# 	jsonRequete.insert("sensors", json.load(tasmota.read_sensors()))

    #     # Récupération et envoi
    #     webserver.content_response(json.dump(jsonRequete))
	# # Demande d'inversion de l'état d'un capteur
    # elif (commande == "toggleSwitch" && webserver.arg("switchID") != nil)
    #     webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Demande d'inversion de l'état du capteur " + webserver.arg("switchID") + " !", LOG_LEVEL_DEBUG)
	# # Demande de suppression des scripts BERRY & des fichiers sur carte SD & Redémarre
    # elif (commande == "supprBerryFS")
    #     webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Demande de suppression des scripts BERRY & des fichiers sur carte SD !", LOG_LEVEL_DEBUG)
    #     gestionFileFolder.supprBerryFS("")
    #     gestionFileFolder.supprBerryFS("/sd")

    #     # Reboot
    #     tasmota.cmd("Restart 1;", boolMute)
	# # Demande de reset de l'ESP32
    # elif (commande == "btn_resetESP32")
    #     webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Demande de reset de l'ESP32 !", LOG_LEVEL_DEBUG)

    #     tasmota.cmd("Reset 2;", boolMute)
    # end

    # # Renvoi la réponse à la page web
    # return "OK"
end

# Retourne le module lors de l'importation
return webFonctions