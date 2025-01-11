# Définition du module
var RS485Fonctions = module("/RS485Fonctions")

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
        elif msg[trigger].find("Boot", 0)
			# # Si c'est un esclave RS485
            # if controleGeneral.parametres["modules"].find("RS485", false)
            #     if controleGeneral.parametres["modules"]["RS485"].find("idModule", 0) > 0
            #         # Envoi ses capteurs enregistrés
            #         log ("RS485_CHGT_ETAT_DEMARRAGE: Envoi au Maitre RS485, ses capteurs enregistrés !", LOG_LEVEL_DEBUG)
            #         tasmota.cmd("ReglageRS485", boolMute)
            #     end
            # end
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
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
RS485Fonctions.envoiMsgRS485 = def(objSerial, ordre, delimiteurs, msg)
    import crc
    import re

    # Calcul & Ajout du CRC au message, puis ajoute les caractères de début et de fin de ligne
    var calculCRC = crc.crc8(0xFF, bytes().fromstring(str(ordre)) + delimiteurs["MARQUEUR_SEPARATEUR"] + bytes().fromstring(msg))
    msg = delimiteurs["MARQUEUR_START"] + str(ordre) + delimiteurs["MARQUEUR_SEPARATEUR"] + msg + delimiteurs["MARQUEUR_SEPARATEUR"] + str(calculCRC) + delimiteurs["MARQUEUR_END"]

    # Envoi le message sur le port RS485
    if (objSerial != nil) 
        # Supprime les marqueurs de début et de fin de ligne
        if re.match("(.*?)" + delimiteurs["MARQUEUR_START"] + "(.*?)" + delimiteurs["MARQUEUR_END"], msg) == nil
            log ("ENVOI_RS485: Le message RS485 ne sera pas envoyé car il ne possède pas de caractères de débt & de fin de ligne !", LOG_LEVEL_ERREUR)
        else    log ("ENVOI_RS485: Trame RS485 envoyée = " + re.match("(.*?)" + delimiteurs["MARQUEUR_START"] + "(.*?)" + delimiteurs["MARQUEUR_END"], msg)[2], LOG_LEVEL_DEBUG_PLUS)
                objSerial.write(bytes().fromstring(msg))
        end
    end
end

# Fonction de lecture de messages sur le port RS485
RS485Fonctions.lireMsgRS485 = def(objSerial, delimiteurs)
    import re
    import crc
    import string

    # Recoit message sur le port RS485
    if (objSerial != nil && objSerial.available()) 
        var msg = objSerial.read()
        var crcRecu = 0
        var output = ""

        msg = msg.asstring()
        msg = re.match("(.*?)" + delimiteurs["MARQUEUR_START"] + "(.*?)" + delimiteurs["MARQUEUR_END"], msg)[2]

        if msg == nil
            log ("RECEPTION_RS485: ATTENTION - Le message RS485 ne possède pas de caractères de débit & de fin de ligne !", LOG_LEVEL_ERREUR)
            return false
        end

        # On teste le CRC en le recalculant
        # On découpe le méssage pour récupérer le CRC reçu
        crcRecu = int(string.split(msg, delimiteurs["MARQUEUR_SEPARATEUR"])[string.count(msg, delimiteurs["MARQUEUR_SEPARATEUR"])])

        # On enlève le CRC de la trame reçue pour le recalculer et comparer
        #msg = string.tr(msg, string.format(";%s", str(crcRecu)), "")
        output = string.split(msg, delimiteurs["MARQUEUR_SEPARATEUR"])
        var nb = string.count(msg, delimiteurs["MARQUEUR_SEPARATEUR"]) - 1

        msg = ""
        for i: 0 .. nb
            msg = msg + output[i] + (i == nb ? "" : delimiteurs["MARQUEUR_SEPARATEUR"])
        end
        
        if (crcRecu == crc.crc8(0xFF, bytes().fromstring(msg)))
            log ("RECEPTION_RS485: Message RS485 reçu = " + msg, LOG_LEVEL_DEBUG_PLUS)
            log ("RECEPTION_RS485: Le message RS485 reçu est complet & le CRC est exacte = " + str(crcRecu), LOG_LEVEL_DEBUG_PLUS)
            return msg
        else    log ("RECEPTION_RS485: ATTENTION - Le CRC du message RS485 est erroné, le message ne sera pas traité !", LOG_LEVEL_ERREUR)
                return false
        end
    end
end

# Retourne le module lors de l'importation
return RS485Fonctions