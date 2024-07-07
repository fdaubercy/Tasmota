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

import webserver

# Fonctions nécesaires au Driver
class GESTION_WEB : Driver
	# Variables
	var sensors
	var formSelection
	var categorieSelection
	var connected
	
	def init()	
		self.connected = false
		self.formSelection = ""
		self.categorieSelection = ""
	end
	
	def every_second()
		var url = ""
		var jsonData = {}
		var connected = verifConnection()
		var reponse

		if self.connected != connected
			self.connected = connected
			
			# Si connexion wifi établie
			if self.connected
				jsonData.insert("parametres", parametres)
			
				reponse = clientWeb(parametres["serveur"]["web"]["url_sauvegarde_json"], "POST", jsonData)
				if json.load(reponse)["status"] == "OK"
					log ("WEBSERVER: Sauvegarde de persist.json sur le SERVEUR-NAS reussie !", LOG_LEVEL_DEBUG)
				else log ("WEBSERVER: Sauvegarde de persist.json sur le SERVEUR-NAS echouee !", LOG_LEVEL_DEBUG)
				end
			end
		end
	end
	
	def web_sensor()
		self.sensors = json.load(tasmota.read_sensors())
		
		if parametres["modules"]["pompeVideCave"].find("activation", "OFF") == "ON"
			log ("WEBSERVER: Envoi a la page web de l'etat des capteurs !", LOG_LEVEL_DEBUG_PLUS)
			tasmota.web_send(afficheSensorPompeCave())
		end
	end	

	#- Création de boutons dans le menu principal -#
	def web_add_main_button()
		log ("WEBSERVER: Affichage du bouton !", LOG_LEVEL_DEBUG)
		webserver.content_send("<p></p><button onclick='window.open(\"" + parametres["serveur"]["web"]["url_serveur"] + "/parametrage.html?device=&" + parametres["serveur"]["hostname"] + "&module=serveur&categorie=generale\")'>Réglages des modules</button>")
	end	
end

# Charge la gestion des pages web
gestionWeb = GESTION_WEB()
tasmota.add_driver(gestionWeb)	