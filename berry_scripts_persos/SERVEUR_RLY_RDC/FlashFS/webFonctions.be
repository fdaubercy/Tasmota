# Teste l'état de la connexion wifi.
# Retourne le résultat sous forme booléenne
def verifConnection()
    import mqtt
    import json

	var connected = false
    var parametres = persist.find("parametres")
	
	# # Vérifie si wifi connecté
	var wifi = tasmota.wifi()
	
	if !wifi.find("ip", false) && connected
		connected = false
		log ("GESTION_WEB: Module tasmota deconnecte !", LOG_LEVEL_DEBUG)

        tasmota.cmd("Restart 1", boolMute)
	elif wifi.find("ip", false) && !connected
		connected = true
		log ("GESTION_WEB: Module tasmota connecte !", LOG_LEVEL_DEBUG)
		
		mqtt.publish("tele/" + parametres["serveur"]["mqtt"]["topic"] + "/WIFI", json.dump(wifi))
	end
	
	return connected 
end	

# Classe TCP Client
# Retourne la réponse du serveur
def clientWeb(url, typeRequest, data)
    import json

	var webClient
	var codeReponse
	var reception
	
	# Si le module n'est pas connecté
	if !verifConnection() return end 
	
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
def htmlWebSocket()
    import webserver

	webserver.content_start("WebSocket Test")
	webserver.content_send_style()
		
	var html = "<script type='text/javascript'>" + 
					"function WebSocketTest() {" + 
						"if ('WebSocket' in window) {" +
							"console.log('WebSocket is supported by your Browser!');" + 
							"/* Let us open a web socket */" + 
							"var ws = new WebSocket('ws://192.168.0.48:8888/');" +
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
						"} else {" +
							"/* The browser doesn't support WebSocket */" +
							"console.log('WebSocket NOT supported by your Browser!');" +
						"}" + 
					"}" +
				"</script>" +
				"<div id='sse'>" +
					"<a href='javascript:WebSocketTest()'>Run WebSocket</a>" +
				"</div>"
				
	webserver.content_send(html)
	webserver.content_stop()
end

# Modifie les paramètres en json
def traiteCommandeHTTP(typeModule, categorie, commande)
    import webserver
    import persist
    import json

    # Test : Parcours les données POST recues
    print("------------------------ traiteCommandeHTTP -----------------------")
    for nb: 0 .. webserver.arg_size() - 1
        print(webserver.arg_name(nb) + "->" + webserver.arg(nb))
    end

    var parametres = persist.find("parametres")

    # Réalise l'action
    if (commande == "modifParam")
        log ("WEBSERVER: Modification des paramètres en json !", LOG_LEVEL_DEBUG)
        if typeModule == "Thermo-Hygrometre" || typeModule == "pompeVideCave" || typeModule == "autres"
			parametres["modules"][typeModule] = json.load(webserver.arg("json"))[typeModule]
        elif typeModule == "serveur"
            parametres["serveur"] = json.load(webserver.arg("json"))
        end

        log ("WEBSERVER: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)	
        persist.parametres = parametres	
        persist.save() 

        # Reboot
        tasmota.cmd("Restart 1;", boolMute)

    elif (commande == "supprElement")
        log ("WEBSERVER: Demande de suppression de l'élément " + webserver.arg("element") + " du module " + typeModule + " !", LOG_LEVEL_DEBUG)
        parametres["modules"][typeModule]["environnement"][categorie].remove(webserver.arg("element"))

        log ("WEBSERVER: Modifie & Enregistre _persist.json !", LOG_LEVEL_DEBUG)	
        persist.parametres = parametres	
        persist.save() 

        # Reboot
        tasmota.cmd("Restart 1;", boolMute)
    elif (commande == "jsonSensors")
        log ("WEBSERVER: Demande d'envoi du json sensors !", LOG_LEVEL_DEBUG)

		var jsonRequete = {};
		jsonRequete.insert("sensors", json.load(tasmota.read_sensors()))

        # Récupération et envoi
        webserver.content_response(json.dump(jsonRequete))

    elif (commande == "toggleSwitch" && webserver.arg("switchID") != nil)
        log ("WEBSERVER: Demande d'inversion de l'état du capteur " + webserver.arg("switchID") + " !", LOG_LEVEL_DEBUG)
    elif (commande == "supprBerryFS")
        log ("WEBSERVER: Demande de suppression des scripts BERRY & des fichiers sur carte SD !", LOG_LEVEL_DEBUG)
        supprBerryFS("")
        supprBerryFS("/sd")

        # Reboot
        tasmota.cmd("Restart 1;", boolMute)
    elif (commande == "btn_resetESP32")
        log ("WEBSERVER: Demande de reset de l'ESP32 !", LOG_LEVEL_DEBUG)

        tasmota.cmd("Reset 2;", boolMute)
    end

    # Renvoi la réponse à la page web
    return "OK"
end