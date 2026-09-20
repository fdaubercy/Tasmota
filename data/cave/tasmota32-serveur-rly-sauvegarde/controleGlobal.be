# NOTES :
# - Encore penser à paramétrer le module ('template') en fonction du changement de pin du relai dans la page : trappe?action=affichage
# 		* Types de GPIO enregistrés dans _persist.json sous parametres["componentes"]
# 		* A paramétrer au démarrage après validation du formulaire html des paramètres : fonction'modifParametres' dans 'globarVar.be'
# 		* Attention ajouter donc les numeros de relais ou switchs ou boutons dans ce formulaire
#		* ex de commande : tasmota.cmd("Template {'NAME':'Example Template','GPIO':[416,0,418,0,417,2720,0,0,2624,32,2656,224,0,0],'FLAG':0,'BASE':0}")

# Gère les actions sur les relais
# Lance le timer si le relai est une relai astable avec timer
# boolCapteurs=true -> si il faut désactiver les capteurs qui gèrent son déclenchement
# boolTimer=true -> si il faut activer le timer
# delaiAvantCommande -> délai avant commande du relai

import string
import json
import mqtt

def modifEtatRelai(moduleRelai, idRelai, etat, boolCapteurs, boolTimer, delaiAvantCommande)
	if etat == "TOGGLE"
		if tasmota.get_power()[idRelai - 1] == true
			etat = "OFF"
		else etat = "ON"
		end
	end
	
	if (etat == "") return end
	if (tasmota.get_power()[idRelai - 1] == true && etat == "ON") return end
	if (tasmota.get_power()[idRelai - 1] == false && etat == "OFF") return end
	
	# Paramètres par défaut si absent
	if boolCapteurs == nil boolCapteurs = false end
	if boolTimer == nil boolTimer = true end
	if delaiAvantCommande == nil delaiAvantCommande = 0 end
	
	# Lance l'ordre
	if delaiAvantCommande != 0
		tasmota.remove_timer(string.format("timer_commande%i", idRelai))
		tasmota.set_timer(delaiAvantCommande * 1000, /-> tasmota.cmd("Power" + str(idRelai) + " " + etat, boolMute), string.format("timer_commande%i", idRelai))
		log (string.format("GESTION_CAPTEURS: Relai %i %s après délai de %is!", idRelai, etat, delaiAvantCommande), LOG_LEVEL_DEBUG)
	else
		tasmota.cmd("Power" + str(idRelai) + " " + etat, boolMute)
		log (string.format("GESTION_CAPTEURS: Relai %i %s !", idRelai, etat), LOG_LEVEL_DEBUG)
	end
	
	
	# Désactive les capteurs associés à son focntionnement
	if boolCapteurs
		var capteurs = parametres["modules"][moduleRelai]["environnement"].find("capteursPosition", false)
		
		if capteurs
			# Désactive temporairement les capteurs si Relai ON / Réactive les capteurs si Relai OFF
			log ("GESTION_CAPTEURS: " + (etat == "ON" ? "Desactivation" : "Reactivation") + " des capteurs !", LOG_LEVEL_DEBUG)
			for cleCapteurs: capteurs.keys()
				capteurs[cleCapteurs]["activation"] = (etat == "ON" ? "OFF" : "ON")
			end	
		end
	end
	
	# Lance le timer si paramétré
	if boolTimer
		var relais = parametres["modules"][moduleRelai]["environnement"].find("relais", false)
		if relais
			for cle: relais.keys()
				relais[cle]["etat"] = etat
				
				if etat == "ON" && relais[cle]["id"] == idRelai && relais[cle]["timer"] != 0
					log (string.format("GESTION_CAPTEURS: Lancement du timer pour le relai %i: %is !", idRelai, relais[cle]["timer"]), LOG_LEVEL_INFO)
					
					tasmota.remove_timer(string.format("timer_relai%i", idRelai))
					tasmota.set_timer(relais[cle]["timer"] * 1000, /-> modifEtatRelai(moduleRelai, idRelai, "TOGGLE", boolCapteurs, false), string.format("timer_relai%i", idRelai))
				elif etat == "OFF" && relais[cle]["id"] == idRelai && relais[cle]["timer"] != 0
					log (string.format("GESTION_CAPTEURS: Supprime le timer pour le relai %i !", idRelai), LOG_LEVEL_INFO)
					
					tasmota.remove_timer(string.format("timer_relai%i", idRelai))
				end
			end
		end
	end
end

# Règles sur changement d'état des capteurs
def changementEtatCapteur(value, trigger, msg, moduleCapteur, id)
	# value=0 ou 1
	# trigger=Switch2
	# msg={"Switch2":{"Action":"ON"}}
	
	var action = ""
									
	# Sort de la fontion
	if type(value) == "instance" 
		if value.find("Action", false)
			action = value["Action"]
		else return
		end
	end
	
	# print("value=" + str(value))
	# print("trigger=" + str(trigger))
	# print("msg=" + str(msg))
	# print("moduleCapteur=" + moduleCapteur)
	# print("id=" + str(id))
	# print("action=" + action)
	
	# Gère les actions sur modification d'état des switchs
	if string.find(trigger, "Switch") > -1
		var capteurs = parametres["modules"][moduleCapteur]["environnement"]["capteursPosition"]
		for cle: capteurs.keys()
			if capteurs[cle]["id"] == id && capteurs[cle]["activation"] == "ON"
				# Enregistre l'état en json
				capteurs[cle]["etat"] = value
				
				# Cherche les relais liés
				var relaisLie = capteurs[cle]["relaisLie"]
				for nb: 0 .. relaisLie["modules"].size() - 1
					modifEtatRelai(relaisLie["modules"][nb], relaisLie["ids"][nb], (action == "ON" ? relaisLie["etatSiON"][nb] : relaisLie["etatSiOFF"][nb]), false, false, (action == "ON" ? relaisLie["delaiSiON"][nb] : relaisLie["delaiSiOFF"][nb]))
				end
			end
		end
	end

	# Gère les actions sur modification d'état des switchs
	if string.find(trigger, "Button") > -1
		var boutons = parametres["modules"][moduleCapteur]["environnement"]["boutons"]	
		for cle: boutons.keys()
			if boutons[cle]["id"] == id && boutons[cle]["activation"] == "ON"
				# Enregistre l'état en json
				boutons[cle]["etat"] = value
				
				# Cherche les relais liés
				var relaisLie = boutons[cle]["relaisLie"]
				for nb: 0 .. relaisLie["modules"].size() - 1
					modifEtatRelai(relaisLie["modules"][nb], relaisLie["ids"][nb], (action == "SINGLE" ? relaisLie["etatSiON"][nb] : relaisLie["etatSiOFF"][nb]), true, true, (action == "ON" ? relaisLie["delaiSiON"][nb] : relaisLie["delaiSiOFF"][nb]))
				end		
			end
		end
	end
	
	# Gère les actions sur modification d'état des switchs
	if string.find(trigger, "AM2301#Humidity") > -1
		var thermos = parametres["modules"][moduleCapteur]["environnement"].find("thermometres", false)	
		for cle: thermos.keys()
			if thermos[cle]["id"] == id && thermos[cle]["activation"] == "ON" && int(thermos[cle]["value"]) != int(value)
				# Enregistre l'état en json
				thermos[cle]["value"] = real(value)

				# Compare l'humidité avec les limites
				var limites = thermos[cle]["relaisLie"]["limites"]
				
				if int(value) >= int(limites[1])
					log (string.format("GESTION_CAPTEURS: Humidite superieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
					action = "ON"
				else
					log (string.format("GESTION_CAPTEURS: Humidite inferieure a %i%% !", limites[1]), LOG_LEVEL_DEBUG)
					action = "OFF"
				end
					
				# Cherche les relais liés
				var relaisLie = thermos[cle]["relaisLie"]
				for nb: 0 .. relaisLie["modules"].size() - 1
					modifEtatRelai(relaisLie["modules"][nb], relaisLie["ids"][nb], (action == "ON" ? relaisLie["etatSiON"][nb] : relaisLie["etatSiOFF"][nb]), false, true, (action == "ON" ? relaisLie["delaiSiON"][nb] : relaisLie["delaiSiOFF"][nb]))
				end	
			end
		end
	end
end

class CONTROLE_GENERAL : Driver
	# Variables
	var sensors
	var enregistrePersistant
	var nbRelaisActives
	var nbSwitchsActives
	var nbButtonsActives
	var tcpServeur
	
	def init()
		self.enregistrePersistant = false
		self.nbRelaisActives = 0
		self.nbSwitchsActives = 0
		self.nbButtonsActives = 0

		log ("CONTROLE_GENERAL: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
		# Teste la connection au wifi toutes 30 minutes sinon redemarre
		if parametres["serveur"]["web"].find("activation", "OFF") == "ON"
			# A CORRIGER : Crée un problème de déconnexion
			# tasmota.add_cron("0 */30 * * * *", /-> clientWeb("https://www.google.com/"), "testeConnection")
		end
		
		# Mets à jours la json self.parametres / 120s
		tasmota.add_cron("0 */2 * * * *", /-> self.majCapteursJson(), "majCapteursJson")
		
		# Déclenche une action tous les jours à minuit
		tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")
		
		# Compte le nombre de relais activés
		# Reset compteur des cycles & timestamp du relai de pompe de cave au démarrage
		for cleModules: parametres["modules"].keys()
			if type(parametres["modules"][cleModules]) != "instance"
				continue
			end		
			
			# Si le module est activé
			if parametres["modules"][cleModules].find("activation", "OFF") == "ON"
				var relais = parametres["modules"][cleModules]["environnement"].find("relais", false)
			
				if relais
					for cleRLY: relais.keys()
						# Si le relai est activé
						if relais[cleRLY]["activation"] == "ON" && relais[cleRLY]["id"] != -1
							if cleModules == "pompeVideCave" 
								relais[cleRLY]["timestamp"]["nbCyclesJour"] = 0 
								if relais[cleRLY]["timestamp"]["ON"] == 0 relais[cleRLY]["timestamp"]["ON"] = tasmota.rtc()["local"] end
								if relais[cleRLY]["timestamp"]["OFF"] == 0 relais[cleRLY]["timestamp"]["OFF"] = tasmota.rtc()["local"] end
							end
							self.nbRelaisActives += 1		
						end
					end
				end
			end
		end		
		log (string.format("CONTROLE_GENERAL: Nb. de relais actives = %i !", self.nbRelaisActives), LOG_LEVEL_DEBUG)
		
		# Ajoute les règles sur changement d'état des capteurs si ils sont activés
		# Parcours tous les modules paramétrés
		if parametres["modules"].find("activation", "OFF") == "ON"
			for cleModule: parametres["modules"].keys()
				if type(parametres["modules"][cleModule]) != "instance"
					continue
				end
				
				if parametres["modules"][cleModule].find("activation", "OFF") == "ON"
					var capteurs = parametres["modules"][cleModule]["environnement"].find("capteursPosition", false)	
					if parametres["modules"][cleModule]["environnement"].find("interrupteurs", false)
						capteurs.insert("interrupteurs", parametres["modules"][cleModule]["environnement"]["interrupteurs"])
					end	

					if capteurs
						for cleCapteurs: capteurs.keys()
							if capteurs[cleCapteurs].find("activation", "OFF") == "ON"
								self.nbSwitchsActives += 1
								
								tasmota.add_rule(string.format("Switch%i", capteurs[cleCapteurs]["id"]), def(value, trigger, msg) changementEtatCapteur(value, trigger, msg, cleModule, capteurs[cleCapteurs]["id"]) end)				
							end
						end
					end
					
					var boutons = parametres["modules"][cleModule]["environnement"].find("boutons", false)
					if boutons
						for cleBoutons: boutons.keys()
							if boutons[cleBoutons].find("activation", "OFF") == "ON"
								self.nbButtonsActives += 1	

								tasmota.add_rule(string.format("Button%i", boutons[cleBoutons]["id"]), def(value, trigger, msg) changementEtatCapteur(value, trigger, msg, cleModule, boutons[cleBoutons]["id"]) end)
							end									
						end
					end
					
					var thermos = parametres["modules"][cleModule]["environnement"].find("thermometres", false)
					if thermos
						for cleTH: thermos.keys()
							if thermos[cleTH].find("activation", "OFF") == "ON"
								tasmota.add_rule("AM2301#Humidity", def(value, trigger, msg) changementEtatCapteur(value, trigger, msg, cleModule, thermos[cleTH]["id"]) end)
							end									
						end
					end
				end
			end
			
			# Détache ou attache les boutons et switchs si activés >= 1
			log (string.format("CONTROLE_GENERAL: Nb. de switchs actives = %i !", self.nbSwitchsActives), LOG_LEVEL_DEBUG)	
			if self.nbSwitchsActives > 0
				if tasmota.cmd("SetOption114", boolMute)["SetOption114"] != "ON"
					log ("CONTROLE_GENERAL: Detache tous les switchs !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption114 ON", boolMute)		
				end
			else
				if tasmota.cmd("SetOption114", boolMute)["SetOption114"] != "OFF"
					log ("CONTROLE_GENERAL: Attache tous les switchs !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption114 OFF", boolMute)		
				end	
			end
			
			# Détache ou attache les interrupteurs & capteurs si activés >= 1
			log (string.format("CONTROLE_GENERAL: Nb. de boutons actives = %i !", self.nbButtonsActives), LOG_LEVEL_DEBUG)
			if self.nbButtonsActives > 0
				if tasmota.cmd("SetOption73", boolMute)["SetOption73"] != "ON"
					log ("CONTROLE_GENERAL: Detache tous les boutons !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption73 ON", boolMute)		
				end
			else
				if tasmota.cmd("SetOption73", boolMute)["SetOption73"] != "OFF"
					log ("CONTROLE_GENERAL: Attache tous les boutons !", LOG_LEVEL_DEBUG)
					tasmota.cmd("SetOption73 OFF", boolMute)		
				end	
			end
		end
		
		# Ajoute les commandes personnalisées si le module est activé
		tasmota.add_cmd('ReglageGlobal', reglageGlobal)
		# Parcours tous les modules paramétrés
		if parametres["modules"].find("activation", "OFF") == "ON"
			for cleModule: parametres["modules"].keys()
				if type(parametres["modules"][cleModule]) != "instance"
					continue
				end

				if parametres["modules"][cleModule].find("activation", "OFF") == "ON"
					if cleModule == "Thermo-Hygrometre"
						tasmota.add_cmd('ReglageDHT22', reglageDHT22)
					elif cleModule == "pompeVideCave"
						tasmota.add_cmd('ReglagePompe', reglagePompe)
					elif cleModule == "autres"
						tasmota.add_cmd('ReglageAutres', reglageAutres)						
					end
				end
			end
		end
		
		# Configure le module tasmota
		configByJson(parametres)
		
		self.sensors = json.load(tasmota.read_sensors())
	end
	
	def json_append()		
		var msg = string.format(",\"pompeVideCave\":{\"relai\": \"%s\", \"timestampON\": %i, \"timestampOFF\": %i, \"delaiFonctionnement\": %i, \"nbCyclesJour\": %i}", 
									parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["etat"], 
									parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["ON"],
									parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["OFF"],
									(parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["nbCyclesJour"] == 0 ? 0 : parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["delai"]), 
									parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["nbCyclesJour"])
		tasmota.response_append(msg)
	end
	
	def every_250ms()
	end
	
	# Mets a jour l'état des capteurs dans le fichier en json
	def majCapteursJson()
		self.sensors = json.load(tasmota.read_sensors())
		
		if tasmota.read_sensors() == nil
			return
		end
		
		log ("GESTION_CAPTEURS: Mise a jour de l'etat des capteurs de niveau !", LOG_LEVEL_INFO)

		# Parcours tous les modules paramétrés
		if parametres["modules"].find("activation", "OFF") == "ON"
			for cle: parametres["modules"].keys()
				if type(parametres["modules"][cle]) != "instance"
					continue
				end
				
				if parametres["modules"][cle].find("activation", "OFF") == "ON"
					if cle == "pompeVideCave"
						# Pour les switchs
						var capteurs = parametres["modules"][cle]["environnement"]["capteursPosition"]
						for cleCapteurs: capteurs.keys()
							if capteurs[cleCapteurs].find("activation", "OFF") == "ON"
								var id = capteurs[cleCapteurs].find("id", -1)
								if id != -1
									parametres["modules"][cle]["environnement"]["capteursPosition"][cleCapteurs]["etat"] = self.sensors.find(string.format("Switch%i", id), "OFF")
								end
							end
						end
					end
				end
			end
		end		
	end	
	
	# Se lance chaque jour à minuit
	def majMinuit()
		if parametres["modules"].find("activation", "OFF") == "ON"
			if parametres["modules"]["pompeVideCave"].find("activation", "OFF") == "ON"
				parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["delai"] = 0
				parametres["modules"]["pompeVideCave"]["environnement"]["relais"]["relai1"]["timestamp"]["nbCyclesJour"] = 0
			end
		end
	end
	
	#- Se déclenche sur modification d'état d'un relai par l'interface webUI ou commande Power -#
	def set_power_handler(cmd, idx)
		var etat = ""
		var i = 0
		
		log("CONTROLE_GENERAL: Lecture automatisee de l'etat des relais", LOG_LEVEL_DEBUG)
		for nb: 0 .. self.nbRelaisActives
			if 1 & (idx >> (nb)) == 1
				etat = "ON"
			else etat = "OFF"
			end
			
			# Parcours tous les modules paramétrés
			if parametres["modules"].find("activation", "OFF") == "ON"
				for cle: parametres["modules"].keys()
					if type(parametres["modules"][cle]) != "instance"
						continue
					end

					# Pour chaque module activé
					if parametres["modules"][cle].find("activation", "OFF") == "ON"
						# Mise à jour des relais
						var relais = parametres["modules"][cle]["environnement"]["relais"]

						for cleRLY: relais.keys()
							if relais[cleRLY]["etat"] != etat && relais[cleRLY]["id"] == nb + 1
								log((string.format("GESTION_RELAIS: Lecture etat bit %i -> relai %i = %s", 7 - nb, nb + 1, etat)), LOG_LEVEL_DEBUG)
								
								# Ajoute des détails de déclenchement en json
								relais[cleRLY]["etat"] = etat
								if etat == "ON"
									if tasmota.rtc()["local"] > relais[cleRLY]["timestamp"]["ON"]
										relais[cleRLY]["timestamp"]["delai"] = tasmota.rtc()["local"] - relais[cleRLY]["timestamp"]["ON"]
									end
									
									if cle == "pompeVideCave"
										relais[cleRLY]["timestamp"]["nbCyclesJour"] += 1
									end
								end
								relais[cleRLY]["timestamp"][etat] = tasmota.rtc()["local"]
								
								# Vérifie si il y a un timer paramétrer ou à annuler
								if etat == "ON" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0
									log (string.format("GESTION_RELAIS: Lancement du timer pour le relai %i: %is !", nb + 1, relais[cleRLY]["timer"]), LOG_LEVEL_INFO)
									tasmota.set_timer(relais[cleRLY]["timer"] * 1000, /-> modifEtatRelai(cle, nb + 1, "TOGGLE", false, false, 0), string.format("timer_relai%i", nb + 1))								
								elif etat == "OFF" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0
									log (string.format("GESTION_RELAIS: Supprime le timer pour le relai %i !", nb + 1), LOG_LEVEL_INFO)
									tasmota.remove_timer(string.format("timer_relai%i", nb + 1))								
								end
								
								# Vérifie si il doit y avoir emission d'un message MQTT
								var tabTopics = relais[cleRLY]["publishMQTT"]
								for nbMQTT: 0 .. tabTopics["topic"].size() - 1
									var topic = tabTopics["topic"][nbMQTT]
									if string.find(topic, "cmnd") > -1
										log (string.format("GESTION_RELAIS: Publie sur le réseau mqtt pour le relai %i !", nb + 1), LOG_LEVEL_INFO)
										mqtt.publish(topic, etat)								
									end
								end
							end
						end
					end
				end
			end
		end
	end	
end

# Active le Driver de controle global des modules
controleGeneral = CONTROLE_GENERAL()
tasmota.add_driver(controleGeneral)

