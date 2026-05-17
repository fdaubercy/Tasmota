var udpFonctions = module("/udpFonctions")

udpFonctions.DEBUG = nil
udpFonctions.udpReception = [nil, nil]
udpFonctions.port = [0, 0]
udpFonctions.typeComm = ["", ""]
udpFonctions.ip = ["", ""]

# # *************************************************
# # * ModBus Commandes 
# # *************************************************
# CMND_FEATURES
# CMND_FUNC_JSON
# CMND_FUNC_EVERY_SECOND
# CMND_FUNC_EVERY_100_MSECOND
# CMND_CLIENT_SEND
# CMND_PUBLISH_TELE
# CMND_EXECUTE_CMND

udpFonctions.log = def(msg, levelDebug)
    if (udpFonctions.DEBUG == nil)
        udpFonctions.DEBUG = serveur["udp"].find("debug", "OFF")
    end

    if (udpFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

# exemples: 
# ReglageUDP logActivation OFF
# ReglageUDP envoiUniCast 192.168.0.43 Salut Ca gaz ! OU ReglageUDP envoiUniCast 192.168.4.3 Salut Ca gaz !
# ReglageUDP envoiMultiCast Salut Ca gaz ! OU ReglageUDP envoiMultiCast 192.168.4.3 Salut Ca gaz !
# ReglageUDP forceEnvoiParams ON
# ReglageUDP Timestamp 1766072035
udpFonctions.reglageUDP = def(cmd, idx, payload, payload_json)
    import string
    import json
    import mqtt
    import persist
    import gestionFileFolder
    import re

    var fonction = false
    var parametres = []
    var reponse_cmnd = {"ReglageUDP": {}}
    
    # Test   
    udpFonctions.log("REGLAGE_UDP: -------------------- reglageUDP -------------------", LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 2)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    udpFonctions.log("REGLAGE_UDP: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres != false)
        if (parametres.size() > 0)	log("REGLAGE_UDP: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
        if (parametres.size() > 1)	log("REGLAGE_UDP: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end
    end

    # Activation ou désactivation des logs de la liaison RS485 -> ordre: logActivation
    if string.toupper(fonction) == string.toupper("logActivation")
        try
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            udpFonctions.DEBUG = parametres[0]

            serveur["udp"]["debug"] = parametres[0]
            persist.serveur["udp"]["debug"] = parametres[0]
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Envoi de messages UDP UniCast sur l'IP principale du destinataire pour test
    elif string.toupper(fonction) == string.toupper("envoiUniCast")
        udpFonctions.envoiUDP("UniCast", parametres[0], parametres[1])	# UniCast (Maitre ou Esclaves RangeExtender)
        udpFonctions.log(string.format("ReglageUDP: Données UDP UniCast envoyées à %s >>> %s", parametres[0], parametres[1]), LOG_LEVEL_DEBUG)

        reponse_cmnd["ReglageUDP"]["envoiMessage"] = str(parametres[1])
    # Envoi de messages UDP MultiCast pour test
    elif string.toupper(fonction) == string.toupper("envoiMultiCast")
        # Esclave RangeExtender (id > 0)
        if (serveur["rangeExtender"].find("activation", "OFF") == "ON" && serveur["udp"]["id"] > 0)
            udpFonctions.envoiUDP("MultiCast", "", parametres[0] + " " + parametres[1])
            udpFonctions.log(string.format("ReglageUDP: Données UDP MultiCast envoyées >>> %s", parametres[0] + " " + parametres[1]), LOG_LEVEL_DEBUG)
        # Maitre RangeExtender (id == 0)
        elif (serveur["rangeExtender"].find("activation", "OFF") == "ON" && serveur["udp"]["id"] == 0)
            udpFonctions.envoiUDP("MultiCast", "192.168.4.1", parametres[0] + " " + parametres[1])
            udpFonctions.log(string.format("ReglageUDP: Données UDP MultiCast envoyées >>> %s", parametres[0] + " " + parametres[1]), LOG_LEVEL_DEBUG)
        end
        
        reponse_cmnd["ReglageUDP"]["envoiMessage"] = str(parametres[1])
    # Force l'esclave à envoyer ses paramètres au maitre en UniCast UDP
    elif (string.toupper(fonction) == string.toupper("forceEnvoiParams") && serveur["udp"]["id"] > 0)
        try
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))

            if (parametres[0] == "ON")
                udpFonctions.log("REGLAGE_UDP: Force l'esclave UDP à envoyer ses paramètres au maitre !", LOG_LEVEL_DEBUG_PLUS)

                # L'esclave renvoie au maitre ses paramètres par UDP MultiCast
                var jsonData = json.load(gestionFileFolder.readFile("/json/discovery.json")).find(string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), {})
                if (jsonData != {})
                    var pattern = re.compile('^(maitre|esclave[0-9]+)$')
                    var result = {}

                    for cle : jsonData.keys()
                        if pattern.match(cle)
                            result.insert(cle, jsonData[cle])
                            break
                        end
                    end

                    var message = string.format("tele/%s/%s %s %s", serveur["mqtt"]["topic"], "ReglageUDP", "ImAlive", json.dump(result))

                    # UDP Envoi Esclave -> Maitre
                    # udpFonctions.envoiUDP("UniCast", "192.168.0.43", message)	# UniCast
                    udpFonctions.envoiUDP("MultiCast", "", message)				# MultiCast
                end
            end
        except .. as e, m
            print('Erreur: ', e, " -> ", m)
        end

        tasmota.set_timer(diverses["telePeriod"] * 1000, def()  tasmota.cmd("ReglageUDP forceEnvoiParams ON", boolMute)     end)
    # Récupère les paramètres de chaque esclave sous format json
    elif (string.toupper(fonction) == string.toupper("ImAlive") && serveur["udp"]["id"] == 0)
        # Les données avec des espaces sont coupées
        # Dans cette fonction on va les réunir
        var tmp = json.load(parametres[0] + " " + parametres[1])
        var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
        var device = ""

        # Mets à jour le tableau
        if (paramDiscovery == nil)   paramDiscovery = {}      end
        for item: tmp.keys()    device = item   end

        if (paramDiscovery.insert(device, tmp[device]) == false)
            paramDiscovery.setitem(device, tmp[device])
        end

        # Puis enregistre le fichier
        gestionFileFolder.writeFile("/json/discovery.json", json.dump(paramDiscovery))
        
        tasmota.yield()
        udpFonctions.log("REGLAGE_UDP: Le maitre UDP a reçu les paramètres de l'esclave '" + tmp[device]["nom"] + "' !", LOG_LEVEL_DEBUG_PLUS)

        if (paramDiscovery[device].find("typeReglageHeure", "NTP") == "UDP")
            # Envoi la mise à jour de l'heure aux esclaves en MultiCast UDP
            var message = string.format("tele/%s/%s %s %i", serveur["mqtt"]["groupTopic1"], "ReglageUDP", "Timestamp", int(tasmota.rtc()["utc"]))
            udpFonctions.envoiUDP("MultiCast", "192.168.4.1", message)

            # Envoi deson adresse IP aux esclaves en MultiCast UDP
            message = string.format("tele/%s/%s %s %s", serveur["mqtt"]["groupTopic1"], "ReglageUDP", "ipMaitre", tasmota.cmd("Status 5", boolMute)["StatusNET"]["IPAddress"])
            udpFonctions.envoiUDP("MultiCast", "192.168.4.1", message)

            udpFonctions.log("REGLAGE_UDP: Envoi de la mise à jour de l'heure UDP aux esclaves & son adresse IP !", LOG_LEVEL_DEBUG_PLUS)
        end

        # Réponse série à la commande
        reponse_cmnd["ReglageUDP"][tmp[device]["nom"]] = "Online"

    # L'esclave met à jour son horloge interne
    elif (string.toupper(fonction) == string.toupper("Timestamp") && serveur["udp"]["id"] > 0)
        try
            var timestamp = int(parametres[0])
            tasmota.cmd("Time " + str(timestamp), boolMute)
            tasmota.yield()

            udpFonctions.log("REGLAGE_UDP: L'esclave UDP a mis à jour son horloge interne avec le timestamp: " + str(timestamp), LOG_LEVEL_DEBUG_PLUS)
        except .. as e, m
            print('Erreur: ', e, " -> ", m)
        end
    # L'esclave enregistre l'adresse IP du maitre
    elif (string.toupper(fonction) == string.toupper("ipMaitre") && serveur["udp"]["id"] > 0)
        try
            serveur["rangeExtender"].insert("ipMaitre", parametres[0])
            persist.serveur = serveur
            persist.save()

            tasmota.yield()

            udpFonctions.log("REGLAGE_UDP: L'esclave UDP a enregistré l'adresse IP du maitre: " + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)
        except .. as e, m
            print('Erreur: ', e, " -> ", m)
        end

    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["ReglageUDP"]["logActivated"] = str(udpFonctions.DEBUG)
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
udpFonctions.changementEtatDemarrage = def(value, trigger, msg, typeComm)
    import string
    import mqtt
    import json
    import persist

    var status

	# Test
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: -------------------- UDP changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
    udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: typeComm=" + str(typeComm), LOG_LEVEL_DEBUG_PLUS)		# msg=UniCast / msg = MultiCast

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    tasmota.yield()

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
            # Evite de répéter l'opération 2 fois
            if (string.toupper(typeComm) == string.toupper("MultiCast"))  return  end

            # Enregistre adresse MAC en json persist
            serveur["adresseMAC"] = tasmota.cmd("Status 5", boolMute)["StatusNET"]["Mac"]

            persist.serveur = serveur
            persist.save()
        elif msg["WIFI"].find("Disconnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            if (string.toupper(typeComm) == string.toupper("UniCast"))
                udpFonctions.log(string.format("UDP_CHGT_ETAT_DEMARRAGE: Ouverture connexion UniCast sur le port %i: %s", 
                                                udpFonctions.port[0], udpFonctions.udpReception[0].begin(udpFonctions.ip[0], udpFonctions.port[0]) ? "OK" : "Echec"), LOG_LEVEL_DEBUG_PLUS)
            elif (string.toupper(typeComm) == string.toupper("MultiCast"))								
                udpFonctions.log(string.format("UDP_CHGT_ETAT_DEMARRAGE: Ouverture connexion MultiCast sur le port %i: %s", 
                                                udpFonctions.port[1], udpFonctions.udpReception[1].begin_multicast(udpFonctions.ip[1], udpFonctions.port[1]) ? "OK" : "Echec"), LOG_LEVEL_DEBUG_PLUS)
            end

            # Evite de répéter l'opération 2 fois
            if (string.toupper(typeComm) == string.toupper("MultiCast"))  return  end

            # Les esclaves envoient leurs paramètres par UDP MultiCast au Maitre / telePeriod
            # Le Maitre reset l'état de chaque esclave connus avant réception
            if (serveur["udp"]["id"] > 0)
                udpFonctions.log(string.format("UDP_CHGT_ETAT_DEMARRAGE: L'esclave n°%i envoie ses paramètres au maitre !", serveur["udp"]["id"]), LOG_LEVEL_DEBUG)
                # udpFonctions.resetClientsConnectes()
                tasmota.cmd("ReglageUDP forceEnvoiParams ON")
            else 
                tasmota.set_timer(diverses["telePeriod"] * 1000, def()  udpFonctions.resetClientsConnectes()     end, "resetEsclaves")
            end
        elif msg[trigger].find("Save", 0)
            udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: Fermeture connexion MultiCast & UniCast", LOG_LEVEL_DEBUG_PLUS)
            udpFonctions.udpReception[0].close()
            udpFonctions.udpReception[1].close()
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

# Cette fonction gère l'envoi de messages UDP en unicast et multicast
udpFonctions.envoiUDP = def(typeComm, ipDestinataire, message)
	import string
	
	var udpEmission = udp()
	var resultatEnvoi

    udpFonctions.log("ENVOI_MSG_UDP: ------------------------ UDP sendUDP ----------------------", LOG_LEVEL_DEBUG)
	
	# Ouvre la connexion UniCast sortante ou MultiCast sortante pour les maitres RangeExtender
	if (string.toupper(typeComm) == string.toupper("UniCast"))
		udpEmission.begin("", udpFonctions.port[0])      # envoi sur toutes les interfaces, port identifié
    end

	# Ouvre la connexion MultiCast sortante pour le maitre RangeExtender
    if (serveur["rangeExtender"].find("activation", "OFF") == "ON")
        if (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] == 0)
            udpEmission.begin(ipDestinataire, 0)      # envoi sur toutes les interfaces, port aléatoire
        # Ouvre la connexion MultiCast sortante pour les autres
        elif (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] > 0)
            udpEmission.begin_multicast("224.3.0.1", udpFonctions.port[1])
        end
    end
	
	# Envoi la commande
	# en UniCast
	if (string.toupper(typeComm) == string.toupper("UniCast"))
		resultatEnvoi = udpEmission.send(ipDestinataire, udpFonctions.port[0], bytes().fromstring(message)) ? "OK" : "Echec"
    end

	# en MultiCast sortante pour le maitre RangeExtender
    if (serveur["rangeExtender"].find("activation", "OFF") == "ON")
        if (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] == 0)
            resultatEnvoi = udpEmission.send("224.3.0.1", udpFonctions.port[1], bytes().fromstring(message)) ? "OK" : "Echec"
        # en MultiCast pour les autres
        elif (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] > 0)
            resultatEnvoi = udpEmission.send_multicast(bytes().fromstring(message)) ? "OK" : "Echec"
        end
    end

	udpFonctions.log(string.format("ENVOI_MSG_UDP: Données %s envoyées vers '%s' >>>> %s >>>> %s", typeComm, ipDestinataire, message, resultatEnvoi), LOG_LEVEL_DEBUG)
    tasmota.yield()
	
	# Ferme la connexion
	udpEmission.close()
end

# Cette fonction gère la lecture de messages UDP en unicast et multicast
# Puis publie le message MQTT 'ModbusReceivedUDP' sur le Topic ==> Déclenchera la règle 'tasmota.add_rule('ModbusReceivedUDP')' -> vers la fonction controleModbus.recupereReponseModBusUDP()
udpFonctions.lireUDP = def(typeComm, paramMSG)
    import string
    import json

    var msg = (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.udpReception[0].read() : udpFonctions.udpReception[1].read()
    tasmota.yield()

    # Récupère les messages sur le port UDP (respecte l'API Tasmota)
    while msg != nil
        # Réception du message
        udpFonctions.log("LIRE_UDP: ------------------------ UDP lire ----------------------", LOG_LEVEL_DEBUG)
        udpFonctions.log(string.format("LIRE_UDP: Données UDP %s reçues de '%s' sur le port %i", typeComm, 
                                                (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.udpReception[0].remote_ip : udpFonctions.udpReception[1].remote_ip,
                                                (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.udpReception[0].remote_port : udpFonctions.udpReception[1].remote_port),
                                                LOG_LEVEL_DEBUG)
        udpFonctions.log("LIRE_UDP: msg = " + str(msg.asstring()), LOG_LEVEL_DEBUG)

        tasmota.yield()

        # On transforme la chaine en mots
        paramMSG["msgHex"] = msg
        paramMSG["msgString"] = msg.asstring()

        # On détermine le type de message
        # Cas particulier des réception de trames UDP ModBus -> Traitement des commandes ModBus UDP
        if (string.find(paramMSG["msgString"], "ModbusUDP") > - 1)
            var tabFonctionsName = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
                tabFonctionsName.insert(1, "LECTURE_COILS")
                tabFonctionsName.insert(2, "LECTURE_ENTREES_DISCRETES")
                tabFonctionsName.insert(3, "LECTURE_REGISTRES_HOLDER")
                tabFonctionsName.insert(4, "LECTURE_REGISTRES_ENTREES")
                tabFonctionsName.insert(5, "ECRITURE_COIL_UNIQUE")
                tabFonctionsName.insert(6, "ECRITURE_REGISTRE_UNIQUE")
                tabFonctionsName.insert(0x0F, "ECRITURE_COILS")
                tabFonctionsName.insert(0x10, "ECRITURE_REGISTRES_HOLDER")
                tabFonctionsName.insert(0x11, "ISALIVE_ESCLAVE")

            var tmp = json.load(string.split(paramMSG["msgString"], " ", 1)[1])

            # Détermine si le message ModBus UDP est une réponse automatique d'esclave ou une réponse à une commande du Maitre
            if (tmp["FunctionCode"] & 0x80 == 0x80)
                # Transformation pour récupérer la fonction réelle
                tmp["FunctionCode"] &= 0x7F
                tmp["TypeMsg"] = "Automatique"
                udpFonctions.log("LIRE_UDP: Type de msg Modbus = Automatique", LOG_LEVEL_DEBUG)
            else 
                tmp["TypeMsg"] = "Réponse Ordre"
                udpFonctions.log("LIRE_UDP: Type de msg Modbus = Réponse à un ordre", LOG_LEVEL_DEBUG)
            end
            tmp["FunctionName"] = tabFonctionsName[tmp["FunctionCode"]]

            udpFonctions.log(string.format("LIRE_UDP: DeviceAddress = 0x%02X", int(tmp["DeviceAddress"])), LOG_LEVEL_DEBUG_PLUS)
            udpFonctions.log(string.format("LIRE_UDP: StartAddress = 0x%04X", tmp["StartAddress"]), LOG_LEVEL_DEBUG_PLUS)
            udpFonctions.log(string.format("LIRE_UDP: FunctionCode = 0x%02X ('%s')", tmp["FunctionCode"], tmp["FunctionName"]), LOG_LEVEL_DEBUG_PLUS)
            udpFonctions.log(string.format("LIRE_UDP: Count = %i", str(tmp["Count"])), LOG_LEVEL_DEBUG_PLUS)
            udpFonctions.log(string.format("LIRE_UDP: Values = %s", str(tmp["Values"])), LOG_LEVEL_DEBUG_PLUS)

            # La commande sera traitée par la règle 'ModbusReceivedUDP' dans 'controleModbus.be'
            tasmota.publish_result("{\"ModbusReceivedUDP\": " + json.dump(tmp) + "}", serveur["mqtt"]["topic"])

            return true
        # Cas général des trames UDP TasmotaClient -> Traitement des commandes TasmotaClient UDP
        else
            # On découpe en fonction de " "
            var params = string.split(msg.asstring(), " ", 1)

            # Découpage général sur les "/"
            var decoupage = string.split(params[0], "/")
            var nb_slash = string.count(params[0], "/")

            paramMSG["prefix"] = decoupage[0]
            paramMSG["commande"] = decoupage[nb_slash] + " " + params[1]
            paramMSG["topic"] = ""
            for i: 1 .. nb_slash - 1
                if paramMSG["topic"] == ""
                    paramMSG["topic"] = decoupage[i]
                else paramMSG["topic"] += "/" + decoupage[i]
                end
            end

            udpFonctions.log("LIRE_UDP: prefix=" + str(paramMSG["prefix"]), LOG_LEVEL_DEBUG_PLUS)	
            udpFonctions.log("LIRE_UDP: topic=" + str(paramMSG["topic"]), LOG_LEVEL_DEBUG_PLUS)	
            udpFonctions.log("LIRE_UDP: commande=" + str(paramMSG["commande"]), LOG_LEVEL_DEBUG_PLUS)	

            # Reconnait les bons topics (Uniquement les esclaves car eux envoient leurs données avec leur topic)
            # Le maitre récupère tous les messages
            if (serveur["udp"]["id"] == 0)
                return true
            else
                if ((paramMSG["topic"] == serveur["mqtt"]["groupTopic1"]) || (paramMSG["topic"] == serveur["mqtt"]["topic"]))
                    return true
                else return false
                end
            end
        end

        tasmota.yield()

        # Initialise le buffer
        msg = (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.udpReception[0].read() : udpFonctions.udpReception[1].read()
    end

    return false
end

# Fonction qui gère l'envoi de commande TasmotaClient par UDP sous format string
# CMD = commande répondant au fonctionnenemt de l'API Tasmota
# Type de trame: <CMD>
udpFonctions.sendTasmotaClientUDP = def(typeComm, destinationIP, commande)
    import string

    typeComm = ((typeComm == "" || typeComm == nil) ? "MultiCast" : typeComm)
    var port = (string.toupper(typeComm) == string.toupper("uniCast")) ? udpFonctions.port : udpFonctions.port * 2

    # Test   
    udpFonctions.log("ENVOI_TASMOTA_CLIENT_UDP: --------------- sendTasmotaClientUDP --------------", LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log(f"ENVOI_TASMOTA_CLIENT_UDP: Données {typeComm} envoyées ({destinationIP}) >>>> {commande}", LOG_LEVEL_DEBUG)
    udpFonctions.log(f"ENVOI_TASMOTA_CLIENT_UDP: Adresse IP = {destinationIP}", LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log(f"ENVOI_TASMOTA_CLIENT_UDP: commande = {commande}", LOG_LEVEL_DEBUG_PLUS)

    tasmota.yield()
#-
    if (string.toupper(typeComm) == string.toupper("uniCast"))
        udpFonctions.udpUniCast.send(destinationIP, port, bytes().fromstring(commande))
    elif (string.toupper(typeComm) == string.toupper("multiCast"))
        udpFonctions.udpMultiCast.send_multicast(bytes().fromstring(commande))
    end
-#
end

# Réinitialise les esclaves enregistrés / 300s
# Enregistrés dans '/json/discovery.json' en paramètrant le paramètre "lwt": "Offline"
# Cela permet de détecter si un module habituel est déconnecté
udpFonctions.resetClientsConnectes = def()
    import gestionFileFolder
    import string
    import json
        
    # Lit le fichier json
    var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
    if (paramDiscovery == nil)
        udpFonctions.log("RESET_NB_ESCLAVES_JSON: Le fichier n'existe pas ou est vide !", LOG_LEVEL_DEBUG_PLUS)
        return
    end

    # Parcours tous les esclaves enregistrés et les marque tous 'Offline'
    for item: paramDiscovery.keys()
        paramDiscovery[item]["lwt"] = "Offline"
    end

    # Enregistre ou Mets à jour en variable les capteurs activés dans un tableau
    if (gestionFileFolder.readFile("/json/discovery.json") != json.dump(paramDiscovery))
        gestionFileFolder.writeFile("/json/discovery.json", json.dump(paramDiscovery))
    end

    # Décharge le json
    paramDiscovery = {}
end

# Retourne le module lors de l'importation
return udpFonctions