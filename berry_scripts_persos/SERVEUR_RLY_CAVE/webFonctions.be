import json
import mqtt

# Teste l'état de la connexion wifi.
# Retourne le résultat sous forme booléenne
def verifConnection()
	var connected = gestionWeb.connected
	
	# # Vérifie si wifi connecté
	# var status5 = tasmota.cmd("status 5", boolMute)
		
	# if status5["StatusNET"]["IP6Local"] == "" && status5["StatusNET"]["IP6Global"] == "" && connected
		# connected = false
		# log ("GESTION_WEB: Module tasmota deconnecte !", LOG_LEVEL_DEBUG)
	# elif status5["StatusNET"]["IP6Local"] != "" && status5["StatusNET"]["IP6Global"] != "" && !connected 
		# connected = true
		# log ("GESTION_WEB: Module tasmota connecte !", LOG_LEVEL_DEBUG)
	# end
	var wifi = tasmota.wifi()
	
	if !wifi.find("ip", false) && connected
		connected = false
		log ("GESTION_WEB: Module tasmota deconnecte !", LOG_LEVEL_DEBUG)
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

# WebSensor si pompe de cave activée
def afficheSensorPompeCave()
	# Mets a jour les sensors
	controleGeneral.sensors = json.load(tasmota.read_sensors())
	
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
									"<div>" + string.split(afficheDateTime(parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["ON"], ""), " ")[1] + "</div>" + 
								"</div>" + 
								"<div class='parametre'>" + 
									"<div>Nb. de cycles du jour: </div>" + 
									"<div>" + str(parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["nbCyclesJour"]) + "</div>" + 
								"</div>" + 
								"<div class='parametre'>" + 
									"<div>Intervalle de fonctionnement moyen: </div>" + 
									"<div>" + str(int(parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["delai"] / 60)) + "min" + "</div>" + 
								"</div>"			
				for nb:0 .. controleGeneral.nbSwitchsActives - 1
			sensorPompeCave += "<div class='parametre'>" + 
									"<div class='titreSwitch'>" + (nb == 0 ? "Capteur de niveau bas" : "Capteur de niveau haut") + " :</div>" + 
									"<button class='btnSwitch'>" + controleGeneral.sensors['Switch' + str(nb + 1)] + "</button>" +
								"</div>"			
				end
	sensorPompeCave +=		"</fieldset>" + 
						"</table>"
						
	return sensorPompeCave
end
	
