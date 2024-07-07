# Définition du module
var webFonctions = module("/webFonctions")

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
		log ("GESTION_WEB: Code reponse=" + str(codeReponse) + " -> Serveur connecte mais avec redirection demandee -> Location: " +  webClient.get_header("Location") + " !", LOG_LEVEL_DEBUG_PLUS)
	elif codeReponse == 200
		log ("GESTION_WEB: Code reponse=" + str(codeReponse) + " apres la requete '" + url + "' -> Serveur connecte !", LOG_LEVEL_DEBUG_PLUS)
	else 
		log ("GESTION_WEB: Code reponse=" + str(codeReponse) + " apres la requete '" + url + "' -> Serveur deconnecte !", LOG_LEVEL_DEBUG_PLUS)
	end
	
	# Lit la réponse html
	reception = webClient.get_string()
	log ("GESTION_WEB: Reponse HTML=" + reception + " !", LOG_LEVEL_DEBUG_PLUS)
	
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

# Modifie les paramètres en json
webFonctions.traiteCommandeHTTP = def(typeModule, categorie, commande)
    import webserver
    import persist
    import json
	import gestionFileFolder
	import string

    # Test : Parcours les données POST recues
    log ("TRAITE_COMMANDE_HTTP: -------------------- traiteCommandeHTTP -------------------", LOG_LEVEL_DEBUG_PLUS)
    for nb: 0 .. webserver.arg_size() - 1
        log (string.format("TRAITE_COMMANDE_HTTP: %s -> %s", webserver.arg_name(nb), webserver.arg(nb)), LOG_LEVEL_DEBUG_PLUS)
    end

    var parametres = persist.find("parametres")

    # Réalise l'action
    if (commande == "modifParam")
        log ("TRAITE_COMMANDE_HTTP: Modification des paramètres en json !", LOG_LEVEL_DEBUG)
        if typeModule == "Thermo-Hygrometre" || typeModule == "pompeVideCave" || typeModule == "autres"
			parametres["modules"][typeModule] = json.load(webserver.arg("json"))[typeModule]
        elif typeModule == "serveur"
            parametres["serveur"] = json.load(webserver.arg("json"))
        end

        log ("TRAITE_COMMANDE_HTTP: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)	
        persist.parametres = parametres	
        persist.save() 

        # Reboot
        tasmota.cmd("Restart 1;", boolMute)

    elif (commande == "supprElement")
        log ("TRAITE_COMMANDE_HTTP: Demande de suppression de l'élément " + webserver.arg("element") + " du module " + typeModule + " !", LOG_LEVEL_DEBUG)
        parametres["modules"][typeModule]["environnement"][categorie].remove(webserver.arg("element"))

        log ("TRAITE_COMMANDE_HTTP: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)	
        persist.parametres = parametres	
        persist.save() 

        # Reboot
        tasmota.cmd("Restart 1;", boolMute)
    elif (commande == "jsonSensors")
        log ("TRAITE_COMMANDE_HTTP: Demande d'envoi du json sensors !", LOG_LEVEL_DEBUG)

		var jsonRequete = {};
		jsonRequete.insert("sensors", json.load(tasmota.read_sensors()))

        # Récupération et envoi
        webserver.content_response(json.dump(jsonRequete))

    elif (commande == "toggleSwitch" && webserver.arg("switchID") != nil)
        log ("TRAITE_COMMANDE_HTTP: Demande d'inversion de l'état du capteur " + webserver.arg("switchID") + " !", LOG_LEVEL_DEBUG)
    elif (commande == "supprBerryFS")
        log ("TRAITE_COMMANDE_HTTP: Demande de suppression des scripts BERRY & des fichiers sur carte SD !", LOG_LEVEL_DEBUG)
        gestionFileFolder.supprBerryFS("")
        gestionFileFolder.supprBerryFS("/sd")

        # Reboot
        tasmota.cmd("Restart 1;", boolMute)
    elif (commande == "btn_resetESP32")
        log ("WEBSERVER: Demande de reset de l'ESP32 !", LOG_LEVEL_DEBUG)

        tasmota.cmd("Reset 2;", boolMute)
    end

    # Renvoi la réponse à la page web
    return "OK"
end

# Envoi message mqtt en fonction de l'ordre
webFonctions.envoiMQTT = def(topic, payload, fonction)
	import mqtt
	import json
	import string

	if (payload == nil) payload = {} end

	# Si la fonction == "" => le payload n'est pas modifié
	var strPayload = (type(payload) == "instance" ? json.dump(payload) : payload)

	mqtt.publish(topic, strPayload)
end

#- 
# Classe qui gère la connexion en tant que serveur TCP Async
Tasmota ne gère pas encore les webSocket
class tcpServeur
    var tcp
    var connexion

    def init(port)
        self.tcp = tcpserver(port)

        log ("TCP_SERVEUR: Connexion: OK", LOG_LEVEL_DEBUG)

        tasmota.add_driver(self)
        tasmota.add_fast_loop(/-> self.fast_loop()) 
    end

    def fast_loop()
        import string

        # Vérifie si un client se connecte
        if !self.tcp.hasclient()
            #log (string.format("TCP_SERVEUR: Client non-connecté !"), LOG_LEVEL_DEBUG)
        else 
            if self.connexion == nil
                log (string.format("TCP_SERVEUR: Client connecté !"), LOG_LEVEL_DEBUG)
                self.connexion =  self.tcp.acceptasync()
            end
        end

        if self.connexion != nil
            var packet = self.connexion.read()

            if packet != nil && packet != "" && packet != "\n"
                log (string.format("TCP_SERVEUR: Données reçues: "), LOG_LEVEL_DEBUG)
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

# Retourne le module lors de l'importation
return webFonctions