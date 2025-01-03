# Définition du module
var RS485Fonctions = module("/RS485Fonctions")

var serialRS485

RS485Fonctions.ReglageRS485 = def(cmd, idx, payload, payload_json)
    import string
    import json
    import webFonctions

    var fonction = false
    var parametre = false
    var reponse_cmnd
    
    # Test   
    log ("REGLAGE_RS485: -------------------- ReglageRS485 -------------------", LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RS485: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RS485: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RS485: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RS485: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        fonction = str(string.split(payload, " ", 1)[0])
        parametre = str(string.split(payload, " ", 1)[1])
    else fonction = payload
    end

    log ("REGLAGE_RS485: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    log ("REGLAGE_RS485: parametre=" + str(parametre), LOG_LEVEL_DEBUG_PLUS)

    var groupTopic = tasmota.cmd("GroupTopic")["GroupTopic1"]
    var RS485 = controleGeneral.parametres["modules"]["RS485"]



    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
RS485Fonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt

	# Test
	log ("RS485_CHGT_ETAT_DEMARRAGE: -------------------- RS485 changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	log ("RS485_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	log ("RS485_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	log ("RS485_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

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
            # Paramétrage port RS485 : gpio_rx:4 gpio_tx:5 
            serialRS485 = serial(controleGeneral.parametres["modules"]["RS485"]["environnement"]["pinsRS485s"]["RX"]["pin"], 
                                        controleGeneral.parametres["modules"]["RS485"]["environnement"]["pinsRS485s"]["RX"]["pin"], 
                                        controleGeneral.parametres["modules"]["RS485"]["debit"], serial.SERIAL_8N1)
            return serialRS485
        elif msg[trigger].find("Boot", 0)
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
			# Si c'est un esclave RS485
            if controleGeneral.parametres["modules"].find("RS485", false)
                if controleGeneral.parametres["modules"]["RS485"].find("idModule", 0) > 0
                    # Envoi ses capteurs enregistrés
                    log ("RS485_CHGT_ETAT_DEMARRAGE: Envoi au Maitre RS485, ses capteurs enregistrés !", LOG_LEVEL_DEBUG)
                    tasmota.cmd("ReglageRS485", boolMute)
                end
            end
        elif msg["MQTT"].find("Disconnected", 0)
        end
    end
end

# Règles sur changement d'état des capteurs
RS485Fonctions.changementEtatCapteur = def(value, trigger, msg, moduleCapteur, cleBouton)
    import string
	import mqtt
	import json

	# Test
	log ("RS485_GESTION_CAPTEURS: -------------------- RS485 changementEtatCapteur -------------------", LOG_LEVEL_DEBUG)
	log ("RS485_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	log ("RS485_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	log ("RS485_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	log ("RS485_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)			# moduleCapteur=pompeVideCave
	log ("RS485_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG)					# cleBouton=bouton1





end

# Fonction d'envoi de messages sur le port RS485
RS485Fonctions.envoiMsgRS485 = def(msg)
    import crc
    import re

    # Calcul & Ajout du CRC au message, puis ajoute les caractères de début et de fin de ligne
    var calculCRC = crc.crc8(0xFF, bytes().fromstring(msg))
    msg = "\r" + msg + ";" + str(calculCRC) + "\n"

    # Envoi le message sur le port RS485
    if (serialRS485 != nil) serialRS485.write(bytes().fromstring(msg))  end
    log ("ENVOI_RS485: Message RS485 envoyé =" + re.match("(.*?)\r(.*?)\n", msg)[2], LOG_LEVEL_DEBUG_PLUS)
end

# Retourne le module lors de l'importation
return RS485Fonctions