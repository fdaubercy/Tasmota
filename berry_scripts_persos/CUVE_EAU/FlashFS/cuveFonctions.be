# Définition du module
var cuveFonctions = module("/cuveFonctions")

cuveFonctions.ReglageAna = def(cmd, idx, payload, payload_json)
    import string
    import json
    import webFonctions

    var fonction = false
    var parametre = false
    var reponse_cmnd
    
    # Test   
    log ("REGLAGE_ANA: -------------------- ReglageAna -------------------", LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_ANA: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_ANA: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_ANA: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_ANA: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        fonction = str(string.split(payload, " ", 1)[0])
        parametre = str(string.split(payload, " ", 1)[1])
    else fonction = payload
    end

    log ("REGLAGE_ANA: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_ANA: parametre=" + str(parametre), LOG_LEVEL_DEBUG_PLUS)

    var groupTopic = tasmota.cmd("GroupTopic")["GroupTopic1"]
    var pac = controleGeneral.parametres["modules"]["PAC"]



    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
cuveFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt

	# Test
	log ("CUVE_CHGT_ETAT_DEMARRAGE: -------------------- Cuve changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	log ("CUVE_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	log ("CUVE_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	log ("CUVE_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

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
                    log ("CUVE_CHGT_ETAT_DEMARRAGE: Envoi au Range Extender ses capteurs enregistrés !", LOG_LEVEL_DEBUG)
                    tasmota.cmd("ReglageAna", boolMute)
                end
            end
        elif msg["MQTT"].find("Disconnected", 0)
        end
    end
end

# Règles sur changement d'état des capteurs
cuveFonctions.changementEtatCapteur = def(value, trigger, msg, moduleCapteur, cleBouton)
    import string
	import mqtt
	import json

	# Test
	log ("CUVE_GESTION_CAPTEURS: -------------------- pac changementEtatCapteur -------------------", LOG_LEVEL_DEBUG)
	log ("CUVE_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	log ("CUVE_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	log ("CUVE_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	log ("CUVE_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)			# moduleCapteur=pompeVideCave
	log ("CUVE_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG)					# cleBouton=bouton1





end

# Retourne le module lors de l'importation
return cuveFonctions