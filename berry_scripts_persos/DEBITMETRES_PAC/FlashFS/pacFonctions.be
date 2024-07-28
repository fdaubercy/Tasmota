# Définition du module
var pacFonctions = module("/pacFonctions")

pacFonctions.reglageDebitmetre = def(cmd, idx, payload, payload_json)
    import string
    import json
    import webFonctions

    var fonction = false
    var parametre = false
    var reponse_cmnd
    
    # Test   
    log ("REGLAGE_DEBITMETRE: -------------------- reglageDebitmetre -------------------", LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_DEBITMETRE: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_DEBITMETRE: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_DEBITMETRE: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_DEBITMETRE: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        fonction = str(string.split(payload, " ", 1)[0])
        parametre = str(string.split(payload, " ", 1)[1])
    else fonction = payload
    end

    log ("REGLAGE_DEBITMETRE: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_DEBITMETRE: parametre=" + str(parametre), LOG_LEVEL_DEBUG_PLUS)

    var groupTopic = tasmota.cmd("GroupTopic")["GroupTopic1"]
    var pac = controleGeneral.parametres["modules"]["PAC"]

    # Présentation des différents capteurs aux maitre RangeExtender
    if (string.toupper(fonction) == "" && controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 0) > 0)
        parametre = pac["environnement"]["debitmetres"]
        parametre.insert("idModule", controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 99))

        reponse_cmnd = ""
        reponse_cmnd = "enregistrementDebitmetres " + json.dump(parametre)

        # Envoi des données par mqtt au maitre
        webFonctions.envoiMQTT(string.format("cmnd/%s/ReglageDebitmetre", groupTopic), reponse_cmnd, "")
    # Enregistrement des paramètres des débitmètres dans _persist.json pour le maitre
    elif (string.toupper(fonction) == "ENREGISTREMENTDEBITMETRES" && controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 99)== 0)
        # ex: parametre={'idModule': 1, 'source': 'average', 
        # 'debitmetre1': {'id': 1, 'virtuel': 'OFF', 'value': 0, 'nom': 'Débit Entrée - Cuisine', 'pin': 14, 'facteurCorrection': 1000, 'activation': 'ON', 'type': 287744}, 
        # 'debitmetre2': {'id': 2, 'virtuel': 'OFF', 'value': 0, 'nom': 'Débit Salon - SàM', 'pin': 12, 'facteurCorrection': 1000, 'activation': 'ON', 'type': 287745}, 'unit': 'l/min'}
        parametre = json.load(parametre)

        # Modifie la valeur de la clé 'virtuel'
        for cle: parametre.keys()
            if type(parametre[cle]) != "instance"
                if cle != "idModule"
                    pac["environnement"]["debitmetres"][cle] = parametre[cle]
                end
                continue
            end		

            parametre[cle]["virtuel"] = "ON"
            cle = "debitmetre" + str(parametre["idModule"] * parametre[cle]["id"])
            pac["environnement"]["debitmetres"][cle] = parametre[cle]
        end

        # Enregistre en json
        persist.parametres = controleGeneral.parametres	
        persist.save()
    # Permet de générer des données de débit aléatoires & lancer la commande REGLAGE (telePeriod 3s)
    elif (string.toupper(fonction) == "TEST") 
        pac["test"] = string.toupper(parametre)

        # Lance la commande REGLAGE (telePeriod 3s)
        tasmota.cmd(string.format("ReglageDebitmetre REGLAGE %s", string.toupper(parametre)))
    # Permet d'envoyer par mqtt l'état des capteurs sur une période = 10s
    elif (string.toupper(fonction) == "REGLAGE")
        pac["reglage"] = string.toupper(parametre)
        if (string.toupper(parametre) == "ON")
            controleGeneral.parametres["diverses"]["telePeriod"] = 3
        else
            controleGeneral.parametres["diverses"]["telePeriod"] = 300
        end
        persist.save()

        tasmota.cmd(string.format("TelePeriod %i", int(controleGeneral.parametres["diverses"]["telePeriod"])))
    # Modifie le type de relevé des données de débit (average=0 / raw=1)
    elif (string.toupper(fonction) == "SOURCE")
        if parametre != pac["environnement"]["debitmetres"]["source"] 
            pac["environnement"]["debitmetres"]["source"] = parametre 
            persist.save()

            tasmota.cmd(string.format("Sensor96 9 %i", (parametre == "average" ? 0 : 1)), boolMute)
        end
    # Modifie les unités données de débit (l/min=0 / L/h=1)
    elif (string.toupper(fonction) == "UNIT")
        if parametre != pac["environnement"]["debitmetres"]["unit"]
            pac["environnement"]["debitmetres"]["unit"] = parametre 
            persist.save()

            tasmota.cmd(string.format("Sensor96 0 %i", (parametre == "l/min" ? 0 : 1)), boolMute)
        end
    # Modifie le facteur de correction du capteur (facteurCorrection * 1000)
    elif (string.toupper(fonction) == "CORRECTION")
        if parametre != pac["environnement"]["debitmetres"]["debitmetre" + str(idx)]["facteurCorrection"]
            pac["environnement"]["debitmetres"]["debitmetre" + str(idx)]["facteurCorrection"] = int(parametre)
            persist.save()

            tasmota.cmd(string.format("Sensor96 %i %i", idx, parametre), boolMute)
        end
    end

    # pour le maitre: Envoi de la commande par MQTT sur le groupTopic1 vers les autres modules esclaves
    if (string.toupper(fonction) == "REGLAGE" || string.toupper(fonction) == "SOURCE" || string.toupper(fonction) == "UNIT" || string.toupper(fonction) == "CORRECTION"  || string.toupper(fonction) == "TEST")
        if (controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 99) == 0)
            for cle: controleRangeExtender.modulesConnectes.keys()
                webFonctions.envoiMQTT("cmnd/" + controleRangeExtender.modulesConnectes[cle]["topicModule"] + "/ReglageDebitmetre", str(fonction) + " " + str(parametre), "")
            end
        end
    end

    # Commande réussie
    reponse_cmnd = {}
    reponse_cmnd["ReglageDebitmetre"] = {}
    reponse_cmnd["ReglageDebitmetre"]["test"] = pac.find("test", "OFF")
    reponse_cmnd["ReglageDebitmetre"]["reglage"] = pac.find("reglage", "OFF")
    reponse_cmnd["ReglageDebitmetre"]["source"] = pac.find("source", "average")
    reponse_cmnd["ReglageDebitmetre"]["unit"] = pac.find("unit", "L/h")
    reponse_cmnd["ReglageDebitmetre"]["amountUnit"] = pac.find("amountUnit", "L")

    reponse_cmnd["ReglageDebitmetre"]["facteurCorrection"] = []
    var debitmetres = pac["environnement"]["debitmetres"]
    for nb: 0 .. controleGeneral.nbIO.find("nbDebitmetresActives", 0) - 1
        if debitmetres["debitmetre" + str(nb + 1)]["activation"] == "ON" 
            reponse_cmnd["ReglageDebitmetre"]["facteurCorrection"].resize(nb + 1)
            reponse_cmnd["ReglageDebitmetre"]["facteurCorrection"][debitmetres["debitmetre" + str(nb + 1)]["id"] - 1] = debitmetres["debitmetre" + str(nb + 1)]["id"]
        end
    end
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
pacFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt

	# Test
	log ("PAC_CHGT_ETAT_DEMARRAGE: -------------------- PAC changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	log ("PAC_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	log ("PAC_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	log ("PAC_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	if (type(value) == "instance")
		for cle: value.keys()
			value = value[cle]
		end
	end

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
        elif msg["WIFI"].find("Disonnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
			# Si c'est un esclave Range Extender
            if controleGeneral.parametres["serveur"].find("rangeExtender", false)
                if controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 0) > 0
                    # Envoi ses capteurs enregistrés
                    log ("PAC_CHGT_ETAT_DEMARRAGE: Envoi au Range Extender ses capteurs enregistrés !", LOG_LEVEL_DEBUG)
                    tasmota.cmd("ReglageDebitmetre", boolMute)
                end
            end
        elif msg["MQTT"].find("Disconnected", 0)
        end
    end
end

# Règles sur changement d'état des capteurs
pacFonctions.changementEtatCapteur = def(value, trigger, msg, moduleCapteur, cleBouton)
    import string
	import mqtt
	import json

	# Test
	log ("PAC_GESTION_CAPTEURS: -------------------- pac changementEtatCapteur -------------------", LOG_LEVEL_DEBUG)
	log ("PAC_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	log ("PAC_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	log ("PAC_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	log ("PAC_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)			# moduleCapteur=pompeVideCave
	log ("PAC_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG)					# cleBouton=bouton1

	if (type(value)) == "instance"
        try
            for cle: value.keys()   value = value[cle]  end
        except .. as variable, message
            # C'est un tableau
            if (variable == "type_error")  
            elif (variable == "index_error")  
            end
        end
	end

    # Gère les actions sur modification de valeur des débits
    if string.find(trigger, "Debitmetre") > -1
        var debitmetre = controleGeneral.parametres["modules"][moduleCapteur]["environnement"]["debitmetres"].find(cleBouton, false)

		if debitmetre
			if debitmetre.find("activation", "OFF") == "ON" && ((debitmetre.find("pin", -1) != -1  && debitmetre.find("virtuel", "OFF") == "OFF") || debitmetre.find("virtuel", "OFF") == "ON")
				if int(debitmetre["value"]) != int(value)
					log (string.format("GESTION_CAPTEURS: Débit " + (msg["Source"] == "average" ? "moyen " : "instantané ") + "%i=%i%s !", debitmetre["id"], value, msg["Unit"]), LOG_LEVEL_DEBUG)
					debitmetre["value"] = value
				end

				if controleGeneral.parametres["modules"][moduleCapteur]["environnement"]["debitmetres"].find("amountUnit", "ml") != msg["AmountUnit"]
					controleGeneral.parametres["modules"][moduleCapteur]["environnement"]["debitmetres"]["amountUnit"] = msg["AmountUnit"]

					# Enregistre en json
					# persist.parametres = controleGeneral.parametres	
					# persist.save()
				end
			end
		end
	end
end
    
# Retourne le module lors de l'importation
return pacFonctions