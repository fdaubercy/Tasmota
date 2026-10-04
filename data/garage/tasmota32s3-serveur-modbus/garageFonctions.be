# Définition du module
var garageFonctions = module("/garageFonctions")

garageFonctions.log = def(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "garage")
end

# Aide de la commande ReglageGarage, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
garageFonctions.aideReglageGarage = def(sujet)
    if (sujet == nil)
        return []
    end
    return nil
end
garageFonctions.reglageGarage = def(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    if diversFonctions.traiteAide("ReglageGarage", payload, garageFonctions.aideReglageGarage, true)    return    end


    var fonction = false
    var parametres = []
    var reponse_cmnd
    
    # Test   
    garageFonctions.log ("REGLAGE_GARAGE: -------------------- ReglageGarage -------------------", LOG_LEVEL_DEBUG_PLUS)
    garageFonctions.log ("REGLAGE_GARAGE: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    garageFonctions.log ("REGLAGE_GARAGE: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    garageFonctions.log ("REGLAGE_GARAGE: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    garageFonctions.log ("REGLAGE_GARAGE: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    logFonctions.log ("REGLAGE_GARAGE: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS, "garage")
    if (parametres.size() > 0)	logFonctions.log ("REGLAGE_GARAGE: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS, "garage")	end
    if (parametres.size() > 1)	logFonctions.log ("REGLAGE_GARAGE: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS, "garage")	end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd = "ReglageGarage: aucun reglage disponible"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
garageFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import json

	# Test
	garageFonctions.log ("GARAGE_CHGT_ETAT_DEMARRAGE: -------------------- Garage changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	garageFonctions.log ("GARAGE_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	garageFonctions.log ("GARAGE_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	garageFonctions.log ("GARAGE_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

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
    end
end

# Retourne le module lors de l'importation
return garageFonctions