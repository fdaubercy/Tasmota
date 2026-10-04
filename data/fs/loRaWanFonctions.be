# Définition du module
#@ solidify:loRaWanFonctions
var loRaWanFonctions = module("loRaWanFonctions")

# Etat modifiable du module, dans une GLOBALE (solidification 2026-09-27). Un module
# solidifie est constant (en flash) : y ecrire leve "'module' value has no writable
# attribute", et ses listes sont figees. La map est creee au premier appel avec les
# valeurs de depart qu'avaient les anciens attributs du module.
def loRaWanFonctions_etat()
    import global
    if (global._etatLoRaWanFonctions == nil)
        global._etatLoRaWanFonctions = {}
    end
    return global._etatLoRaWanFonctions
end
loRaWanFonctions.etat = loRaWanFonctions_etat


def loRaWanFonctions_log(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "lorawan")
end
loRaWanFonctions.log = loRaWanFonctions_log

# Aide de la commande ReglageLoRaWan, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def loRaWanFonctions_aideReglageLoRaWan(sujet)
    import string
    if (sujet == nil)
        return []
    end
    return nil
end
loRaWanFonctions.aideReglageLoRaWan = loRaWanFonctions_aideReglageLoRaWan

def loRaWanFonctions_reglageLoRaWan(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    if diversFonctions.traiteAide("ReglageLoRaWan", payload, loRaWanFonctions.aideReglageLoRaWan, true)    return    end


    var fonction = false
    var parametres = []                # liste vide (et non false) : parametres.size() plus bas
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

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd += "aucun reglage disponible"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
loRaWanFonctions.reglageLoRaWan = loRaWanFonctions_reglageLoRaWan

# Configuration de la mise en place du réseau LoRaWan
# En fonction des paramètres de configuration enregistrés en JSON
def loRaWanFonctions_configLoRaWanByJson()

end
loRaWanFonctions.configLoRaWanByJson = loRaWanFonctions_configLoRaWanByJson

# Règles sur changement d'état lors du démarrage de Tasmota
def loRaWanFonctions_changementEtatDemarrage(value, trigger, msg)
    import string
    import mqtt
    import json
    import gestionFileFolder

	# Test
	loRaWanFonctions.log("LORAWAN_CHGT_ETAT_DEMARRAGE: -------------------- LoRaWan changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
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
loRaWanFonctions.changementEtatDemarrage = loRaWanFonctions_changementEtatDemarrage

# Retourne le module lors de l'importation
return loRaWanFonctions