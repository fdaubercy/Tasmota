# Définition du module
var vrFonctions = module("/vrFonctions")

vrFonctions.DEBUG = nil

vrFonctions.log = def(msg, levelDebug)
    if (vrFonctions.DEBUG == nil)
        vrFonctions.DEBUG = drivers["voletRoulants"].find("debug", "OFF")
    end

    if (vrFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

#- exemples: 
    ReglageVolets logActivation OFF
-#
vrFonctions.reglageVolets = def(cmd, idx, payload, payload_json)
    import string
    import json
    import persist

    var fonction = false
    var parametres = false
    var reponse_cmnd = "reglageVolets: "
    
    # Test   
    vrFonctions.log("REGLAGE_VOLETS: -------------------- reglageVolets -------------------", LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    vrFonctions.log("REGLAGE_VOLETS: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
	if (parametres.size() > 0)	vrFonctions.log("REGLAGE_VOLETS: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
	if (parametres.size() > 1)	vrFonctions.log("REGLAGE_VOLETS: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

    # Activation ou désactivation des logs de la liaison RS485 -> ordre: logActivation
    if string.toupper(fonction) == "LOGACTIVATION"
        try
            # Adapte le paramètre
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            vrFonctions.DEBUG = parametres[0]

            # Sauvegarde le paramètre
            drivers["voletRoulants"]["debug"] = parametres[0]
            persist.save()
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd += string.format("logActivated=%s", vrFonctions.DEBUG)
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

vrFonctions.configVRByJson = def()
    import string
    import configGlobal

    var vrJSON = drivers["voletRoulants"]

    # Règle la mise en place et le paramétrage du(des)volet(s) roulant(s)
    if (vrJSON.find("activation", "OFF") == "ON")
        # Paramètre global des volets roulants
        try
            # Active ou nom les volets roulants
            if (configGlobal.testeParam("SetOption80", vrJSON["activation"], "str"))
                vrFonctions.log("CONFIG_VR: Active les volets roulants !", LOG_LEVEL_DEBUG)
            end

            # Paramètre le mode de fonctionnement de tous les volets roulants
            if (configGlobal.testeParam("ShutterMode", vrJSON["mode"], "int"))
                vrFonctions.log(string.format("CONFIG_VR: Paramètre le mode de fonctionnement des volets roulants: Mode %i !", vrJSON["mode"]), LOG_LEVEL_DEBUG)
            end
        except .. as error, message
            vrFonctions.log(string.format("CONFIG_VR_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
        end 

        # Paramètre chaque volet roulant
        for cle: vrJSON["environnement"]["VRs"].keys()
            if type(vrJSON["environnement"]["VRs"][cle]) != "instance"   continue    end

            try
                if (vrJSON["environnement"]["VRs"][cle].find("activation", "OFF") == "ON")
                    # Paramètre le relai lié
                    if (configGlobal.testeParam(string.format("ShutterRelay%i", vrJSON["environnement"]["VRs"][cle]["id"]), vrJSON["environnement"]["VRs"][cle]["relais1"], "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre le 1er relai du volet roulant %i: Relai %i !", vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["relais1"]), LOG_LEVEL_DEBUG)
                    end

                    # Paramètre le délai de bascule du relai (si Mode=3: Volet Roulant de garage)
                    if (vrJSON["mode"] == 3)
                        if (configGlobal.testeParam(string.format("PulseTime%i", vrJSON["environnement"]["VRs"][cle]["relais1"]), 5, "int"))
                            vrFonctions.log(string.format("CONFIG_VR2: Paramètre le délai de bascule du 1er relai du volet roulant %i: 5s !", vrJSON["environnement"]["VRs"][cle]["id"]), LOG_LEVEL_DEBUG)
                        end
                    # Paramètre l'Interlock entre le relai1 et le suivant
                    elif (vrJSON["mode"] == 1)
                        tasmota.cmd(string.format("Interlock %i,%i", vrJSON['environnement']['VRs'][cle]['relais1'], vrJSON['environnement']['VRs'][cle]['relais1'] + 1), boolMute)
                        tasmota.cmd("Interlock ON", boolMute)
                    end

                    # Paramétre l'aspect et l'ordre des boutons de VR sur webUI
                    if (configGlobal.testeParam(string.format("ShutterInvertWebButtons%i", vrJSON["environnement"]["VRs"][cle]["id"]), 0, "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre les icones par défaut du volet roulant %i !", vrJSON["environnement"]["VRs"][cle]["id"]), LOG_LEVEL_DEBUG)
                    end
                    if (configGlobal.testeParam(string.format("ShutterInvert%i", vrJSON["environnement"]["VRs"][cle]["id"]), 1, "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre la représentation numérique de l'état du volet roulant %i !", vrJSON["environnement"]["VRs"][cle]["id"]), LOG_LEVEL_DEBUG)
                    end

                    # Paramètre le temps d'ouverture/fermeture du volet roulant
                    if (configGlobal.testeParam(string.format("ShutterOpenDuration%i", vrJSON["environnement"]["VRs"][cle]["id"]), vrJSON["environnement"]["VRs"][cle]["tempsMontee"], "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre le temps d'ouverture du volet roulant %i: %is !", vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["tempsMontee"]), LOG_LEVEL_DEBUG)
                    end
                    if (configGlobal.testeParam(string.format("ShutterCloseDuration%i", vrJSON["environnement"]["VRs"][cle]["id"]), vrJSON["environnement"]["VRs"][cle]["tempsDescente"], "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre le temps de fermeture du volet roulant %i: %is !", vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["tempsDescente"]), LOG_LEVEL_DEBUG)
                    end

                    # Paramètres les commandes par boutons choisies
                    for cleBTN: vrJSON["environnement"]["VRs"][cle]["boutons"].keys()
                        if (vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN].find("activation", "OFF") == "ON" && vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN].find("id", -1) != -1)
                            vrFonctions.log(string.format("CONFIG_VR2: Paramètre le BP %i pour la fonction '%s' !", vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["id"], vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["function"]), LOG_LEVEL_DEBUG)
                            tasmota.cmd(string.format("ShutterButton%i %i %s %i", 
                                                                    vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["id"], 
                                                                    vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["function"], 
                                                                    (vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["mqtt"] == "ON" ? 1 : 0), boolMute))
                        end
                    end
                end
            except .. as error, message
                vrFonctions.log(string.format("CONFIG_VR2_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
            end  
        end              
    end
end

# Règles sur changement d'état lors du démarrage de Tasmota
vrFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import json
    import gestionFileFolder

	# Test
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: -------------------- Volets changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
	
    if (type(value) == "instance")
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
        elif msg[trigger].find("Save", 0)
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
	# Se déclenche un évènement sur les heures et la synchronisation NTP (si activé)
    elif (trigger == "Time")
        # A chaque fois que le NTP est initialisé et l'heure synchronisée
        if type(msg["Time"]) == "instance"
            if msg["Time"].find("Initialized", 0)
            # A chaque heure, quand le système NTP est synchronisé
            elif msg["Time"].find("Set", 0)
            end
        end
    end
end

# Règles sur changement d'état des capteurs
vrFonctions.changementEtatCapteur = def(value, trigger, msg, numRideau, etatRideau)
    import string
    import json
    import persist

	var device

	# Test
	vrFonctions.log("VR_GESTION_CAPTEURS: -------------------- Volets changementEtatCapteur -------------------", LOG_LEVEL_DEBUG)
	vrFonctions.log("VR_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	vrFonctions.log("VR_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	vrFonctions.log("VR_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
    vrFonctions.log("VR_GESTION_CAPTEURS: numRideau=" + str(numRideau), LOG_LEVEL_DEBUG)			        # numRideau=1
	vrFonctions.log("VR_GESTION_CAPTEURS: etatRideau=" + str(etatRideau), LOG_LEVEL_DEBUG)			        # etatRideau=ouverture

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

	tasmota.yield()

    # Modifie l'état du rideau en fonction du capteur déclenché
    var vrJSON = drivers["voletRoulants"]
    if (etatRideau == "ouverture" && value == "ON")
        # On force l'affichage de l'état 'ouvert' du rideau
        tasmota.cmd(string.format("ShutterSetClose%i", numRideau), boolMute)
        vrFonctions.log(string.format("VR_GESTION_CAPTEURS: Force l'affichage du volet %i en ouverture !", numRideau), LOG_LEVEL_DEBUG)
    elif (etatRideau == "fermeture" && value == "ON")
        # On force l'affichage de l'état 'fermé' du rideau
        tasmota.cmd(string.format("ShutterSetOpen%i", numRideau), boolMute)
        vrFonctions.log(string.format("VR_GESTION_CAPTEURS: Force l'affichage du volet %i en fermeture !", numRideau), LOG_LEVEL_DEBUG)
    end

	# Enregistre les nouvelles valeurs de capteurs en json
	# persist.modules = modules
end

# Règles sur changement d'état des capteurs
vrFonctions.changementDirection = def(value, trigger, msg, numRideau)
    import string
    import json

	# Test
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: -------------------- Volets changementDirection -------------------", LOG_LEVEL_DEBUG)
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
    vrFonctions.log("VR_CHANGEMENT_DIRECTION: numRideau=" + str(numRideau), LOG_LEVEL_DEBUG)			        # numRideau=1

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    # Teste la valeur (#0: Arrêt / #1: Ouverture en cours / #-1: Fermeture en cours)
    if (value == 0)
        vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: Le volet %i est à l'arrêt !", numRideau), LOG_LEVEL_DEBUG)
    elif (value == 1)
        vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: Le volet %i est en cours d'ouverture !", numRideau), LOG_LEVEL_DEBUG)
    elif (value == -1)
        vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: Le volet %i est en cours de fermeture !", numRideau), LOG_LEVEL_DEBUG)
    end

	tasmota.yield()

    # Modifie l'état de certains relais en fonction de la direction du volet
    var vrJSON = drivers["voletRoulants"]
    var activationSiOuvert = vrJSON["environnement"]["VRs"][string.format("VR%i", numRideau)].find("activationSiOuvert", false)
    var activationSiFerme = vrJSON["environnement"]["VRs"][string.format("VR%i", numRideau)].find("activationSiFerme", false)

    # Parcours les relais à activer ou désactiver à l'ouverture du volet
    if (value == 1)
        if (activationSiOuvert != false)
            if (activationSiOuvert["activation"] == "ON")   
                for i: 0 .. activationSiOuvert["tabRelais"].size() - 1
                    tasmota.cmd(string.format("Power%i %s", activationSiOuvert["tabRelais"][i], activationSiOuvert["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à l'ouverture du volet %i !", (activationSiOuvert["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiOuvert["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end

        if (activationSiFerme != false)
            if (activationSiFerme["activation"] == "ON")
                for i: 0 .. activationSiFerme["tabRelais"].size() - 1
                    tasmota.cmd(string.format("Power%i %i", activationSiFerme["tabRelais"][i], 1 - activationSiFerme["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à l'ouverture du volet %i !", (1 - activationSiFerme["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiFerme["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end
    end

    # Parcours les relais à activer ou désactiver à la fermeture du volet
    if (value == -1)
        if (activationSiFerme != false)
            if (activationSiFerme["activation"] == "ON")
                for i: 0 ..activationSiFerme["tabRelais"].size() - 1
                    tasmota.cmd(string.format("Power%i %i", activationSiFerme["tabRelais"][i], activationSiFerme["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à la fermeture du volet %i !", (activationSiFerme["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiFerme["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end

        if (activationSiOuvert != false)
            if (activationSiOuvert["activation"] == "ON")   
                for i: 0 .. activationSiOuvert["tabRelais"].size() - 1
                    tasmota.cmd(string.format("Power%i %s", activationSiOuvert["tabRelais"][i],  1 - activationSiOuvert["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à la fermeture du volet %i !", (1 - activationSiOuvert["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiOuvert["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end
    end
end

# Retourne le module lors de l'importation
return vrFonctions