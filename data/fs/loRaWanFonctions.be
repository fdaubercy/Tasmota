# Définition du module
var loRaWanFonctions = module("/loRaWanFonctions")

loRaWanFonctions.DEBUG = nil

loRaWanFonctions.log = def(msg, levelDebug)

    if (loRaWanFonctions.DEBUG == nil)
        loRaWanFonctions.DEBUG = drivers["ModBus"].find("debug", "OFF")
    end

    if (loRaWanFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

#- exemples: 
    reglageLoRaWan logActivation OFF
-#
loRaWanFonctions.reglageLoRaWan = def(cmd, idx, payload, payload_json)
    import string
    import json

    var fonction = false
    var parametres = false
    var reponse_cmnd = "ReglageLoRaWan: "
    
    # Test   
    loRaWanFonctions.log("REGLAGE_LORAWAN: -------------------- ReglageLoRaWan -------------------", LOG_LEVEL_DEBUG_PLUS)
    loRaWanFonctions.log("REGLAGE_LORAWAN: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    loRaWanFonctions.log("REGLAGE_LORAWAN: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    loRaWanFonctions.log("REGLAGE_LORAWAN: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    loRaWanFonctions.log("REGLAGE_LORAWAN: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    loRaWanFonctions.log("REGLAGE_LORAWAN: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
	if (parametres.size() > 0)	loRaWanFonctions.log("REGLAGE_LORAWAN: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
	if (parametres.size() > 1)	loRaWanFonctions.log("REGLAGE_LORAWAN: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

    # Activation ou désactivation des logs de la liaison RS485 -> ordre: logActivation
    if string.toupper(fonction) == "LOGACTIVATION"
        try
            # Adapte le paramètre
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            loRaWanFonctions.DEBUG = parametres[0]

            # Sauvegarde le paramètre
            drivers["LoRaWan"]["debug"] = parametres[0]

            # Sauvegarde le paramètre
            modules["LoRaWan"]["debug"] = parametres[0]
            persist.save()
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd += string.format("logActivated=%s", loRaWanFonctions.DEBUG)
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Configuration de la mise en place du réseau LoRaWan
# En fonction des paramètres de configuration enregistrés en JSON
loRaWanFonctions.configLoRaWanByJson = def()

end

# Règles sur changement d'état lors du démarrage de Tasmota
loRaWanFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import json
    import gestionFileFolder

	# Test
	loRaWanFonctions.log("LORAWAN_CHGT_ETAT_DEMARRAGE: -------------------- LoRaWan changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	loRaWanFonctions.log("LORAWAN_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	loRaWanFonctions.log("LORAWAN_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	loRaWanFonctions.log("LORAWAN_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
	
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

# Retourne le module lors de l'importation
return loRaWanFonctions