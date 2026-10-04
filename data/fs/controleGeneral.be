#-  NOTES :
    - Encore penser à paramétrer le module ('template') en fonction du changement de pin du relai dans la page : trappe?action=affichage
        * Types de GPIO enregistrés dans _persist.json sous parametres["componentes"]
        * A paramétrer au démarrage après validation du formulaire html des paramètres : fonction'modifParametres' dans 'globarVar.be'
        * Attention ajouter donc les numeros de relais ou switchs ou boutons dans ce formulaire
        * ex de commande : tasmota.cmd("Template {'NAME':'Example Template','GPIO':[416,0,418,0,417,2720,0,0,2624,32,2656,224,0,0],'FLAG':0,'BASE':0}")
    - Pour tasmota :
        * Bouton (BUTTON) = bouton poussoir
        * Interrupteur (Switch) = Interrupteur
            Gère les actions sur les relais
            Lance le timer si le relai est une relai astable avec timer
            boolCapteurs=true -> si il faut désactiver les capteurs qui gèrent son déclenchement
            boolTimer=true -> si il faut activer le timer
            delaiAvantCommande -> délai avant commande du relai
    - Le réglage de l'heure de la device est réalisé par :
        * connexion à un serveur NTP: diverses["fuseauHoraire"]["typeReglageHeure"] = "NTP"
        * réglage manuel: diverses["fuseauHoraire"]["typeReglageHeure"] = "MANUEL"
        * reglage par module Real Time Clock: diverses["fuseauHoraire"]["typeReglageHeure"] = "RTC"
        * reglage par réception de l'heure par le maitre en UDP: diverses["fuseauHoraire"]["typeReglageHeure"] = "UDP"
-#

# Rendu solidifiable (2026-07-16) : la classe est portee par un module import-able
# 'controleGeneral', seul moyen pour que la version en FLASH remplace le fichier du
# LittleFS (import tente load_native avant load_package). Charge par 'import' + init()
# depuis autoexec, plus par loadBerryFile (qui, lui, recompile la classe en RAM).
# IMPORTANT : garder l'import+init() AVANT le chargement de i2c_ads1115 (qui lit
# controleGeneral.nbIOActivesJSON au niveau fichier).
#@ solidify:controleGeneral
var controleGeneral = module("controleGeneral")

class CONTROLE_GENERAL : Driver
    # Variables
	var sensors
	var sensorsEcheance				# Fin de validite du cache de 'sensors' (tasmota.millis)
	var lectureSensorsEnCours		# Garde de reentrance de lectureSensors()
	var sensors_valeurAnterieure
	var enregistrePersistant
    var nbIOActivesJSON
	var boolMute

    var flagINIT        # Flag marquant la fin de l'initialisation du module principal
	var connected
	var mqttConnected
    var booted
	var flagTimestampInitialized
	var relances					# Relances de securite en cours, par relai : {"<module>_<id>": nb}

	# Se lance chaque jour à minuit
	def heureReboot()
		import string

        logFonctions.log(string.format("CONTROLE_GENERAL: Reboot du module programmé à %s !", diverses["heureReboot"]), LOG_LEVEL_DEBUG)
		tasmota.cmd("Restart 1", boolMute)
	end

	def timerRebootSiDeconnexionWifi()
        import string

        # Teste le Flag de connexion wifi
		if (!self.connected)
            logFonctions.log(string.format("CONTROLE_GENERAL: Reboot du module par deconnexion Wifi !", diverses["heureReboot"]), LOG_LEVEL_DEBUG)
			tasmota.cmd("Restart 1", boolMute)
		end

        # Teste la commande Ping sur le serveur DNS ou IP de la box internet
        # tasmota.cmd("Ping4 {tasmota.cmd('IPAddress4', boolMute)['IPAddress4']:s}", boolMute)
	end

    def init()
        import json
        import string
        import configGlobal
		import globalFonctions
		import configDevices
		import diversFonctions
        import introspect
		import logFonctions

		self.enregistrePersistant = false
        self.nbIOActivesJSON = {}
		self.connected = false
		self.mqttConnected = false
        self.booted = false
        self.flagINIT = 0
		self.flagTimestampInitialized = false
		self.relances = {}

		# Les sensors sont lus A LA DEMANDE par lectureSensors() (plus a l'init ni chaque seconde)
		self.sensors = {}
		self.sensorsEcheance = 0
		self.lectureSensorsEnCours = false

        logFonctions.log("CONTROLE_GENERAL: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
		# Défini la tache cron pour le reboot sans wifi
		if (serveur["wifi"].find("timerRebootSansWifi", 0) != 0)
            # introspect.get(controleGeneral).heureReboot()
			tasmota.add_cron(string.format("*/%i * * * * *", serveur["wifi"].find("timerRebootSansWifi", 0)), /-> introspect.get(controleGeneral, "timerRebootSiDeconnexionWifi"), "timerRebootSiDeconnexionWifi")
		end

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        tasmota.add_rule("System", globalFonctions.changementEtatDemarrage, "controleGeneral_System")	
        tasmota.add_rule("Wifi", globalFonctions.changementEtatDemarrage, "controleGeneral_Wifi")
        tasmota.add_rule("Mqtt", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleGeneral_Mqtt")
		tasmota.add_rule("Time", def(value, trigger, msg) globalFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleGeneral_Time")

        #- Parcours tous les modules paramétrés
			* Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
			* Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
					par la fonction 'every_second()'
			* Compte les devices non-virtuelles
			* Compte le nombre de devices activées par type et les range dans un tableau
			* Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
			* Détache ou attache les boutons et switchs si activés >= 1
			* Détache ou attache les interrupteurs & capteurs si activés >= 1
		-#

		# Parcours tous les modules paramétrés
		configDevices.configDevicesByRules(modules, self.nbIOActivesJSON)
		configDevices.configDevicesByRules(drivers, self.nbIOActivesJSON)

		logFonctions.log(string.format("CONTROLE_GENERAL: %i relais activés / %i WS2812 activés / %i switchs activés / %i capteurs activés / %i boutons activés / %i entrées analogiques activées / %i thermometres activés / %i compteurs activés !", 
									self.nbIOActivesJSON["relais"]["actives"].find("nb", 0), self.nbIOActivesJSON["WS2812"]["actives"].find("nb", 0), 
                                    self.nbIOActivesJSON["switchs"]["actives"].find("nb", 0), self.nbIOActivesJSON["capteurs"]["actives"].find("nb", 0), 
									self.nbIOActivesJSON["boutons"]["actives"].find("nb", 0), self.nbIOActivesJSON["analogiques"]["actives"].find("nb", 0), 
									self.nbIOActivesJSON["thermometres"]["actives"].find("nb", 0), self.nbIOActivesJSON["compteurs"]["actives"].find("nb", 0)), LOG_LEVEL_DEBUG)
		logFonctions.log(string.format("CONTROLE_GENERAL: %i relais réels / %i WS2812 réels / %i switchs réels / %i capteurs réels / %i boutons réels / %i entrées analogiques réelles / %i thermometres réels / %i compteurs réels !", 
                                    self.nbIOActivesJSON["relais"]["reels"].find("nb", 0), self.nbIOActivesJSON["WS2812"]["reels"].find("nb", 0), 
                                    self.nbIOActivesJSON["switchs"]["reels"].find("nb", 0), self.nbIOActivesJSON["capteurs"]["reels"].find("nb", 0), 
									self.nbIOActivesJSON["boutons"]["reels"].find("nb", 0), self.nbIOActivesJSON["analogiques"]["reels"].find("nb", 0), 
									self.nbIOActivesJSON["thermometres"]["reels"].find("nb", 0), self.nbIOActivesJSON["compteurs"]["actives"].find("nb", 0)), LOG_LEVEL_DEBUG)

        # Configure le module tasmota (paramètres communs à tous les modules Tasmota)
		configGlobal.configGlobalByJson(self.nbIOActivesJSON)        

        # Ajoute les commandes personnalisées si le module est activé
		tasmota.add_cmd('ReglageGlobal', globalFonctions.reglageGlobal)
		tasmota.add_cmd('ReglageLog', logFonctions.reglageLog)     # seule commande de reglage des logs (charte : logFonctions.be)

		# Stats d'utilisation des mémoires
		diversFonctions.statMemory()

        # Marqueur de fin d'initialisation du module principal
        self.flagINIT = 1

		# 5 s apres l'init (etat des relais restaure par Tasmota, SwitchMode appliques et relus) :
		#  1. arme la minuterie des relais deja ON au demarrage,
		#  2. aligne l'etat des capteurs sur la realite.
		tasmota.set_timer(5000, def ()
			self.armeTimersRelaisDemarrage()
			if (self.nbIOActivesJSON["capteurs"]["reels"].find("nb", 0) > 0)
				self.resynchroniseCapteurs()
			end
		end, "demarrageDiffere")
    end

	# Un relai a minuterie deja ON au demarrage (PowerOnState restaure l'etat d'avant le
	# redemarrage, avant le chargement de Berry) ne passe jamais par set_power_handler :
	# sa minuterie n'etait donc jamais lancee -> ex. pompe vide-cave tournant sans limite.
	def armeTimersRelaisDemarrage()
		import string
		import diversFonctions

		var etats = tasmota.get_power()
		var tableau = diversFonctions.joinJsonTab(modules, drivers)
		for i: 0 .. tableau.size() - 1
			if (tableau[i].find("activation", "OFF") != "ON")	continue	end
			for cle: tableau[i].keys()
				if (type(tableau[i][cle]) != "instance" || tableau[i][cle].find("activation", "OFF") != "ON")	continue	end
				var relais = tableau[i][cle].find("environnement", {}).find("relais", false)
				if (!relais)	continue	end

				for cleRLY: relais.keys()
					var relai = relais[cleRLY]
					if (type(relai) != "instance" || relai.find("activation", "OFF") != "ON" || relai.find("timer", 0) == 0)	continue	end
					var id = relai.find("id", 0)
					if (id < 1 || id > etats.size() || !etats[id - 1])	continue	end

					relai["etat"] = "ON"
					logFonctions.log(string.format("GESTION_RELAIS: Relai n°%i deja ON au demarrage -> lancement du timer de %is !", id, relai["timer"]), LOG_LEVEL_INFO)
					tasmota.set_timer(relai["timer"] * 1000, /-> self.finTimerRelai(cle, relai), string.format("timer_relai%i", id))
				end
			end
		end
	end

	#- Relance de securite d'un relai a timer (ex. pompe vide-cave), parametree dans le persist :
	       "relance": {"capteur": "capteur2", "pause": 10, "maxRelances": 3, "topicAlerte": "..."}
	   A la fin du timer, le relai est coupe. Si le capteur 'capteur' (niveau haut) est encore ON,
	   le relai est relance apres 'pause' s, au plus 'maxRelances' fois de suite. Au-dela : arret,
	   alerte (log, MQTT sur 'topicAlerte', page web via relai["alerte"]) -> probable defaut du capteur.
	   Compteur et alerte sont remis a zero des qu'un arret survient avec le niveau haut retombe.
	-#
	def finTimerRelai(cle, relai)
		import string
		import globalFonctions

		var id = relai["id"]
		logFonctions.log(string.format("GESTION_RELAIS: Fin du timer du relai n°%i -> arret de securite", id), LOG_LEVEL_INFO)
		globalFonctions.modifEtatRelai(cle, id, "Switch", "TOGGLE", false, false, 0)

		var reglage = relai.find("relance", false)
		if (!reglage)	return	end

		var cleCompteur = cle + "_" + str(id)
		if (!self.niveauHautActif(cle, reglage))
			self.acquitteRelance(cle, relai)
			return
		end

		var nb = self.relances.find(cleCompteur, 0)
		var maxRelances = reglage.find("maxRelances", 3)
		var nomCapteur = self.nomCapteurRelance(cle, reglage)

		if (nb < maxRelances)
			nb += 1
			self.relances[cleCompteur] = nb
			var message = string.format("Niveau haut '%s' toujours actif apres l'arret de securite : relance %i/%i dans %is", nomCapteur, nb, maxRelances, reglage.find("pause", 10))
			logFonctions.log("GESTION_RELAIS: " + message, LOG_LEVEL_INFO)
			self.publieAlerteRelance(cle, relai, "relance", message, nb, maxRelances)
			tasmota.set_timer(reglage.find("pause", 10) * 1000, /-> self.relanceRelai(cle, relai), string.format("relance_relai%i", id))
		else
			var message = string.format("Niveau haut '%s' toujours actif apres %i relances : probable defaut du capteur (ou pompe inefficace). Pompe arretee.", nomCapteur, maxRelances)
			relai["alerte"] = message
			self.relances.remove(cleCompteur)
			logFonctions.log("GESTION_RELAIS_ERREUR: " + message, LOG_LEVEL_ERREUR)
			self.publieAlerteRelance(cle, relai, "defaut", message, nb, maxRelances)
		end
	end

	# Relance effective apres la pause, si le niveau haut est TOUJOURS actif et le relai toujours coupe
	def relanceRelai(cle, relai)
		import string
		import globalFonctions

		if (!self.niveauHautActif(cle, relai["relance"]))
			logFonctions.log(string.format("GESTION_RELAIS: Niveau haut retombe pendant la pause : pas de relance du relai n°%i", relai["id"]), LOG_LEVEL_INFO)
			self.acquitteRelance(cle, relai)
			return
		end
		if (relai.find("etat", "OFF") == "ON")	return	end

		logFonctions.log(string.format("GESTION_RELAIS: Relance du relai n°%i", relai["id"]), LOG_LEVEL_INFO)
		globalFonctions.modifEtatRelai(cle, relai["id"], "ON", "ON", false, false, 0)
	end

	# Remise a zero du compteur de relances et de l'alerte (cycle termine normalement)
	def acquitteRelance(cle, relai)
		self.relances.remove(cle + "_" + str(relai["id"]))
		if (relai.find("alerte", "") != "")
			logFonctions.log("GESTION_RELAIS: Alerte du relai n°" + str(relai["id"]) + " acquittee (niveau haut retombe)", LOG_LEVEL_INFO)
			relai["alerte"] = ""
		end
	end

	# Etat du capteur de niveau haut de la relance : lecture reelle (sensors), a defaut l'etat memorise
	def niveauHautActif(cle, reglage)
		var capteur = modules.find(cle, {}).find("environnement", {}).find("capteurs", {}).find(reglage.find("capteur", ""), false)
		# Capteur absent ou desactive (ex. non branche) : jamais de relance sur sa lecture
		if (!capteur || capteur.find("activation", "OFF") != "ON")	return false	end
		return self.lectureSensors().find("Switch" + str(capteur["id"]), capteur.find("etat", "OFF")) == "ON"
	end

	def nomCapteurRelance(cle, reglage)
		var capteur = modules.find(cle, {}).find("environnement", {}).find("capteurs", {}).find(reglage.find("capteur", ""), {})
		return capteur.find("nom", reglage.find("capteur", "?"))
	end

	def publieAlerteRelance(cle, relai, evenement, message, nb, maxRelances)
		import mqtt
		import json

		var topic = relai["relance"].find("topicAlerte", "")
		if (topic == "" || !mqtt.connected())	return	end
		mqtt.publish(topic, json.dump({"Module": cle, "Relai": relai["id"], "Evenement": evenement,
		                               "Relance": nb, "MaxRelances": maxRelances, "Message": message}))
	end

	# Au demarrage, l'etat 'etat' des capteurs dans le persist peut ne plus correspondre a la
	# realite (redemarrage, persist redeploye). Or changementEtatCapteur ignore un evenement
	# egal a l'etat memorise : un vrai niveau haut pourrait alors passer inapercu.
	# -> l'etat memorise est invalide, puis l'etat REEL est rejoue une fois comme un evenement
	#    'SwitchN#Action' : la logique relaisLie s'applique a l'etat courant
	#    (ex. niveau haut deja ON au demarrage -> la pompe demarre).
	def resynchroniseCapteurs()
		import string

		var sensors = self.lectureSensors()
		for cleModule: modules.keys()
			var moduleCapteurs = modules[cleModule]
			if (type(moduleCapteurs) != "instance" || moduleCapteurs.find("activation", "OFF") != "ON")	continue	end
			var capteurs = moduleCapteurs.find("environnement", {}).find("capteurs", false)
			if (!capteurs)	continue	end

			for cleCapteur: capteurs.keys()
				var capteur = capteurs[cleCapteur]
				if (type(capteur) != "instance")	continue	end
				# Capteurs REELS seulement : un virtuel n'a pas de SwitchN dans les sensors
				if (capteur.find("activation", "OFF") != "ON" || capteur.find("virtuel", "OFF") != "OFF" || capteur.find("pin", -1) == -1)	continue	end

				var cle = "Switch" + str(capteur["id"])
				var etatReel = sensors.find(cle)
				if (etatReel == nil)
					logFonctions.log(string.format("CONTROLE_GENERAL_ERREUR: Etat de '%s' (%s) introuvable dans les sensors : non resynchronise", capteur.find("nom", cleCapteur), cle), LOG_LEVEL_ERREUR)
					continue
				end

				logFonctions.log(string.format("CONTROLE_GENERAL: Resynchronise '%s' (%s) : memorise=%s / reel=%s", capteur.find("nom", cleCapteur), cle, str(capteur.find("etat")), etatReel), LOG_LEVEL_INFO)
				capteur["etat"] = ""
				tasmota.publish_rule(string.format("{\"%s\": {\"Action\": \"%s\"}}", cle, etatReel))
			end
		end
	end

	# Lit les sensors A LA DEMANDE, avec un cache d'1 s.
	# read_sensors() reconstruit toute la telemetrie SENSOR (MqttShowSensor, qui appelle aussi le
	# json_append() de CHAQUE driver Berry) : le faire chaque seconde jetait 150 a 290 objets/s.
	# Garde de reentrance : un json_append() qui appellerait lectureSensors() recoit la copie en cours.
	def lectureSensors()
		import json

		if (self.lectureSensorsEnCours || !tasmota.time_reached(self.sensorsEcheance))
			return self.sensors
		end

		self.lectureSensorsEnCours = true
		var lu
		try
			lu = json.load(tasmota.read_sensors())
		except .. as e, m
			logFonctions.log("CONTROLE_GENERAL_ERREUR: Lecture des sensors impossible : " + str(m), LOG_LEVEL_ERREUR)
		end
		self.lectureSensorsEnCours = false

		if isinstance(lu, map)	self.sensors = lu	end
		self.sensorsEcheance = tasmota.millis(1000)
		return self.sensors
	end

	# Ajoute les changements d'etat des Switchs (interrupteurs & capteurs) et Boutons REELS
	# a la machine de gestion des regles, uniquement si le MQTT n'est pas connecte
    def every_second()
		import string

		# Cas normal (MQTT connecte) : rien a detecter -> AUCUNE lecture des sensors.
		# La reference est oubliee pour repartir d'un etat frais a la prochaine coupure
		# (sinon un etat vieux de plusieurs heures declencherait de faux evenements).
		if (self.flagINIT != 1 || (serveur["mqtt"]["activation"] == "ON" && self.mqttConnected))
			self.sensors_valeurAnterieure = nil
			return
		end

		# Tasmota numerote interrupteurs ET capteurs comme 'SwitchN' : les deux comptent
		var nbSwitchs = self.nbIOActivesJSON["switchs"]["reels"].find("nb", 0) + self.nbIOActivesJSON["capteurs"]["reels"].find("nb", 0)
		var nbBoutons = self.nbIOActivesJSON["boutons"]["reels"].find("nb", 0)
		if (nbSwitchs + nbBoutons == 0)		return		end

		tasmota.yield()

		var sensors = self.lectureSensors()
		var anterieur = self.sensors_valeurAnterieure
		self.sensors_valeurAnterieure = sensors
		if (anterieur == nil || anterieur == sensors)	return	end		# 1re lecture ou cache non renouvele

		# Switchs PUIS boutons (avant : 'elif' -> les boutons n'etaient jamais surveilles s'il y avait des switchs)
		for groupe: [["Switch", nbSwitchs], ["Button", nbBoutons]]
			for nb: 1 .. groupe[1]
				var cle = groupe[0] + str(nb)
				var etat = sensors.find(cle)
				if (etat != nil && anterieur.find(cle) != nil && etat != anterieur[cle])
					tasmota.publish_rule(string.format("{\"%s\": {\"Action\": \"%s\"}}", cle, etat))
				end
			end
		end
    end

	# Parcours les modules pour detecter les capteurs & boutons qui ne sont pas automatiquement ajouter dans self.sensors
	def json_append()
        import string
		import persist

		var msg = ""
		tasmota.yield()

		# Parcours  les modules pour detecter les capteurs & boutons qui ne sont pas automatiquement ajouter dans self.sensors
		if (self.nbIOActivesJSON.find("boutons",false))
			if self.nbIOActivesJSON["boutons"]["actives"].find("nb", 0) > 0
				for cleModules: modules.keys()
					if type(modules[cleModules]) != "instance"
						continue
					end	

					# Si le module est activé
					var modules = modules[cleModules]
					if modules.find("activation", "OFF") == "ON"
						if (modules["environnement"].find("boutons", false))
							if type(modules["environnement"]["boutons"]) != "instance"
								continue
							end	

							for cleBoutons: modules["environnement"]["boutons"].keys()
								var bouton = modules["environnement"]["boutons"][cleBoutons]

								tasmota.yield()

								if bouton.find("activation", "OFF") == "ON" && ((bouton.find("pin", -1) != -1  && bouton.find("virtuel", "OFF") == "OFF") || bouton.find("virtuel", "OFF") != "OFF")
									#print("Button" + str(bouton))
									msg += ",\"Button" + str(bouton["id"]) + "\": \"" + bouton["etat"] + "\""
								end
							end
						end
					end
				end

				tasmota.response_append(msg)
			end
		end
    end

    #- Création de boutons dans le menu principal -#
	def web_add_main_button()
	end

	#- Se déclenche sur modification d'état d'un relai par l'interface webUI ou commande Power
	        Enregistre le nouvel état des relais en json
	        Enregistre le timestamp de modification d'état en json
	        Enregistre le nb de cycles de modification d'état en json
	        Gère le timer de relai si il y en a un (!=0)
	        Publie l'état du relai sur mqtt sur le topic personnalisé paramétré
     -#
	def set_power_handler(cmd, idx)
		import json
		import mqtt
		import string
		import diversFonctions
		import globalFonctions
		import persist
		import introspect
		import re

		var etat = ""

		tasmota.yield()
		
		logFonctions.log("GLOBAL_POWER_HANDLER: -------------------- global SetPowerHandler -------------------", LOG_LEVEL_DEBUG)
		logFonctions.log("GLOBAL_POWER_HANDLER: Lecture automatisee de l'etat des relais", LOG_LEVEL_DEBUG)
		logFonctions.log("GLOBAL_POWER_HANDLER: cmd=" + str(cmd), LOG_LEVEL_DEBUG)
		logFonctions.log("GLOBAL_POWER_HANDLER: idx=" + str(idx), LOG_LEVEL_DEBUG)
		logFonctions.log("GLOBAL_POWER_HANDLER: idx(binaire)=" + str(diversFonctions.printBinaire(idx)), LOG_LEVEL_DEBUG)

		for nb: 0 .. self.nbIOActivesJSON["relais"]["actives"]["nb"]
			if 1 & (idx >> (nb)) == 1
				etat = "ON"
			else etat = "OFF"
			end

			tasmota.yield()

			# Parcours tous les modules paramétrés
			# tableau = jonction de json sous format tableau
			var tableau = diversFonctions.joinJsonTab(modules, drivers)
			for i: 0 .. tableau.size() - 1
				tasmota.yield()
				
				if tableau[i].find("activation", "OFF") == "ON"
					for cle: tableau[i].keys()
						if (type(tableau[i][cle]) != "instance")		continue	end

						# Pour chaque module activé
						if tableau[i][cle].find("activation", "OFF") == "ON"
							# Mise à jour des relais
							var relais = tableau[i][cle]["environnement"].find("relais", false)

							if (relais)
								for cleRLY: relais.keys()
									if (relais[cleRLY].find("activation", "OFF") == "ON" && relais[cleRLY].find("etat", "OFF") != etat && relais[cleRLY]["id"] == nb + 1)
										logFonctions.log((string.format("GESTION_RELAIS: Lecture de l'etat du bit %i -> " + (relais[cleRLY]["type"] == 1376 ? "led w2812" : "relai") + " n°%i = %s", nb, nb + 1, etat)), LOG_LEVEL_DEBUG)
										
										# Ajoute des détails de déclenchement en json (timestamp et délai)
										relais[cleRLY]["etat"] = etat
										if etat == "ON"
											if tasmota.rtc()["local"] > relais[cleRLY]["timestamp"]["ON"]
                                                logFonctions.log((string.format("GESTION_RELAIS: Enregistre le timestamp de passage à 'ON' du Relai n°%i = %s", nb + 1, etat)), LOG_LEVEL_DEBUG)
												relais[cleRLY]["timestamp"]["delai"] = tasmota.rtc()["local"] - relais[cleRLY]["timestamp"]["ON"]
											end
											
											# Comptage des mises en route du jour : seulement pour les relais dont le
											# persist porte la cle 'nbCyclesJour' (ex. pompe vide-cave), pour ne pas
											# alourdir tous les relais. Remise a zero au changement de jour (heure locale).
											var horodatage = relais[cleRLY]["timestamp"]
											if (horodatage.contains("nbCyclesJour"))
												var jour = tasmota.rtc()["local"] / 86400
												if (horodatage.find("jourCycles", -1) != jour)
													horodatage["jourCycles"] = jour
													horodatage["nbCyclesJour"] = 0
												end
												horodatage["nbCyclesJour"] = horodatage["nbCyclesJour"] + 1
											end
										end
										relais[cleRLY]["timestamp"][etat] = tasmota.rtc()["local"]

										# Relance de securite : un arret alors que le niveau haut est retombe est un
										# cycle normal -> compteur de relances et alerte remis a zero.
										if (etat == "OFF" && relais[cleRLY].find("relance", false))
											if (!self.niveauHautActif(cle, relais[cleRLY]["relance"]))
												self.acquitteRelance(cle, relais[cleRLY])
											end
										end

										# Vérifie si il y a un timer paramétrer ou à annuler
										if (etat == "ON" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0)
											logFonctions.log(string.format("GESTION_RELAIS: Lancement du timer pour le relai n°%i: %is !", nb + 1, relais[cleRLY]["timer"]), LOG_LEVEL_INFO)
											var relaiTimer = relais[cleRLY]
											tasmota.set_timer(relais[cleRLY]["timer"] * 1000, /-> self.finTimerRelai(cle, relaiTimer), string.format("timer_relai%i", nb + 1))
										elif etat == "OFF" && relais[cleRLY]["id"] == nb + 1 && relais[cleRLY]["timer"] != 0
											logFonctions.log(string.format("GESTION_RELAIS: Supprime le timer pour le relai n°%i !", nb + 1), LOG_LEVEL_INFO)
											tasmota.remove_timer(string.format("timer_relai%i", nb + 1))								
										end

										# Vérifie si il doit y avoir emission d'un message MQTT
										if (mqtt.connected())
											var tabTopics = relais[cleRLY].find("publishMQTT", false)
											if (tabTopics != false)
												for nbMQTT: 0 .. tabTopics.find("topic", []).size() - 1
													var topic = tabTopics["topic"][nbMQTT]
													if string.find(topic, "cmnd") > -1
														logFonctions.log(string.format("GESTION_RELAIS: Publie sur le réseau mqtt pour le relai n°%i !", nb + 1), LOG_LEVEL_INFO)
														mqtt.publish(topic, etat)								
													end
												end
											end
										end

										# Vérifie si il doit y avoir emission d'un message ModBus
										if (relais[cleRLY].find("virtuel", "OFF") != "OFF")
											var typeConnex = string.split(relais[cleRLY]["virtuel"], "_")[0]
											var moduleConnex = string.split(relais[cleRLY]["virtuel"], "_")[1]
											var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", string.split(relais[cleRLY]["virtuel"], "_")[1])[0]

											if (!string.endswith(groupeConnex , "s"))
												groupeConnex = groupeConnex + "s"
											end

											if (drivers[typeConnex]["activation"] == "ON" && drivers[typeConnex]["environnement"][groupeConnex][moduleConnex]["activation"] == "ON")
												if (introspect.members("controleModbus") == nil)
													logFonctions.log("GESTION_RELAIS: Attention le Driver 'controleModbus' n'est pas activé !", LOG_LEVEL_INFO)
												end

												if (relais[cleRLY].find("idModBus", false) != false)
													# Componentes   -> type=224: "Relais",
													#               -> type=1376: "WS2812"
													#               -> type=256: "Relais_i"
													var valueModBus 
													if (relais[cleRLY]["type"] == 224 || relais[cleRLY]["type"] == 1376)
														valueModBus = (etat == "ON" ? 0x02 : 0x01)
													elif (relais[cleRLY]["type"] == 256)
														valueModBus = (etat == "ON" ? 0x01 : 0x02)
													end

													# Construit la trame
													var trameModBus = 	{
																			"DeviceAddress": drivers[typeConnex]["environnement"][groupeConnex][moduleConnex]["id"], 
																			"FunctionCode": 6, 
																			"StartAddress": (groupeConnex == "TasmotaSlaveModBus" ? relais[cleRLY]["type"] + relais[cleRLY]["idModBus"] - 1 : relais[cleRLY]["idModBus"]),
																			"type": "uint8", 
																			"Count": 1, 
																			"Values": [valueModBus, 0]
																		}

													# Envoi l'ordre sur le réseau ModBus
													logFonctions.log(string.format("GESTION_RELAIS: Publie sur le réseau ModBus pour le relai n°%i !", nb + 1), LOG_LEVEL_INFO)
													
													import modbusFonctions
													modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["DeviceAddress"])
                                                end
											end
										end

										# Enregistre les nouvelles valeurs de capteurs en json
										if (i == 0)
											persist.modules = tableau[i]
										else	persist.drivers = tableau[i]
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

    #- Appelé lorsqu'une interaction avec un Bouton réel (BP) et Switchs réel (capteurs & interrupteurs) se produit. 
        idx est codé comme suit : device_save << 24 | key << 16 | state << 8 | device
    -#
    #- key & state
        key 0 = KEY_BUTTON = button_topic
        key 1 = KEY_SWITCH = switch_topic
        state 0 = POWER_OFF = off
        state 1 = POWER_ON = on
        state 2 = POWER_TOGGLE = toggle
        state 3 = POWER_HOLD = hold
        state 4 = POWER_INCREMENT = button still pressed
        state 5 = POWER_INV = button released
        state 6 = POWER_CLEAR = button released
        state 7 = POWER_RELEASE = button released
        state 9 = CLEAR_RETAIN = clear retain flag
        state 10 = POWER_DELAYED = button released delayed
        Button Multipress
        state 10 = SINGLE
        state 11 = DOUBLE
        state 12 = TRIPLE
        state 13 = QUAD
        state 14 = PENTA
    -#
    def any_key(cmd, idx)
		import string
		
		tasmota.yield()
		
		logFonctions.log("GLOBAL_ANY_KEY: -------------------- global any_key -------------------", LOG_LEVEL_DEBUG)
		logFonctions.log("GLOBAL_ANY_KEY: Lecture automatisee de l'etat des Boutons (BP) et Switchs (capteurs & interrupteurs)", LOG_LEVEL_DEBUG)
		logFonctions.log("GLOBAL_ANY_KEY: cmd=" + str(cmd), LOG_LEVEL_DEBUG)
		logFonctions.log("GLOBAL_ANY_KEY: idx=" + str(idx), LOG_LEVEL_DEBUG)
		logFonctions.log(string.format("GLOBAL_ANY_KEY: idx = 0x%07X", idx), LOG_LEVEL_DEBUG)

        #- Détails de idx
            idx=33620226
            en binaire =>  0010 0000 0001 0000 0001 0000 0010
            id de la device =>					    0000 0010		== 2: ex:Button1 ou Switch2 (capteurs ou interrupteurs) 
            state =>					  0000 0001					== 1: 0 = "OFF" / 1 = "ON" / ....
            key =>				0000 0001							== 1: 0 = KEY_BUTTON / 1 = KEY_SWITCH
            device_save => 0001                                     == 1
        -#
    end
end

# Publie la classe dans le module (solidification + import).
controleGeneral.CONTROLE_GENERAL = CONTROLE_GENERAL

# init() : instancie le Driver de controle global des modules, l'enregistre et publie
# l'instance dans global.controleGeneral. Remplace le code de niveau fichier.
# APPELEE AUTOMATIQUEMENT par 'import controleGeneral' (be_module.c:285-296, module_init) :
# Berry passe le module en parametre 'm' et renvoie le resultat a la place du module.
# Ne PAS la rappeler depuis autoexec, et ne PAS lire le module par son nom global : une fois
# solidifie, ce nom n'est jamais affecte (il valait la map {} de l'autoexec -> attribute_error).
# La construction ne lit pas global.controleGeneral : la cron qui le reference s'execute plus tard.
def controleGeneral_init(m)
    var inst = m.CONTROLE_GENERAL()
    global.controleGeneral = inst
    tasmota.add_driver(inst)
    return inst
end
controleGeneral.init = controleGeneral_init