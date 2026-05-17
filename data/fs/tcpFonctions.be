var tcpFonctions = module("/tcpFonctions")

tcpFonctions.DEBUG = nil
tcpFonctions.port = 0
tcpFonctions.serveur = nil
tcpFonctions.client = nil
tcpFonctions.connexionAsync = nil
tcpFonctions.msgTCP = nil

tcpFonctions.log = def(msg, levelDebug)
    if (tcpFonctions.DEBUG == nil)
        tcpFonctions.DEBUG = serveur["tcp"].find("debug", "OFF")
    end

    if (tcpFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

# exemples: 
# ReglageTCP logActivation OFF
tcpFonctions.reglageTCP = def(cmd, idx, payload, payload_json)
    import string
    import json

    var fonction = false
    var parametres = []
    var reponse_cmnd = {"ReglageTCP": {}}

    # Test   
    tcpFonctions.log("REGLAGE_TCP: -------------------- reglageTCP -------------------", LOG_LEVEL_DEBUG_PLUS)
    tcpFonctions.log("REGLAGE_TCP: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    tcpFonctions.log("REGLAGE_TCP: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    tcpFonctions.log("REGLAGE_TCP: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    tcpFonctions.log("REGLAGE_TCP: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 2)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    tcpFonctions.log("REGLAGE_TCP: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres != false)
        if (parametres.size() > 0)	log("REGLAGE_TCP: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
        if (parametres.size() > 1)	log("REGLAGE_TCP: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end
    end

    # Activation ou désactivation des logs -> ordre: logActivation
    if string.toupper(fonction) == string.toupper("logActivation")
        try
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            tcpFonctions.DEBUG = parametres[0]

            serveur["tcp"]["debug"] = parametres[0]
            persist.serveur["tcp"]["debug"] = parametres[0]
        except .. as error, message
            tcpFonctions.log(string.format("REGLAGE_TCP_ERREUR: %s --> %s", error, message), LOG_LEVEL_ERREUR)
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["ReglageTCP"]["logActivated"] = str(tcpFonctions.DEBUG)
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

tcpFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import tcpFonctions
    import json
    import introspect

    # Test
    tcpFonctions.log("TCP_CHGT_ETAT_DEMARRAGE: -------------------- TCP changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
    tcpFonctions.log("TCP_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
    tcpFonctions.log("TCP_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
    tcpFonctions.log("TCP_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

    if (type(value)) == "instance"
        for cle: value.keys()
            value = value[cle]
        end
    end

    tasmota.yield()

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
        elif msg["WIFI"].find("Disconnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            try
                # Ce sont les esclaves qui servent de serveur TCP
                if (serveur["tcp"]["id"] > 0)
                    tcpFonctions.log(f"TCP_CHGT_ETAT_DEMARRAGE: Initialisation du serveur TCP sur le port :{tcpFonctions.port:i}", LOG_LEVEL_DEBUG)
                    tcpFonctions.serveur = tcpserver(tcpFonctions.port)
                # Le maitre ouvre une connexion TCP avec chacun des esclaves (serveurs TCP)
                elif (serveur["tcp"]["id"] == 0)
                    # Crée les instances du client TCP
                    tcpFonctions.client = tcpclientasync()
                end
            except .. as error, message
                tcpFonctions.log(string.format("TCP_CHGT_ETAT_DEMARRAGE_ERREUR: %s --> %s", error, message), LOG_LEVEL_ERREUR)
            end
        elif msg[trigger].find("Save", 0)
            if (serveur["tcp"]["id"] > 0)
                tcpFonctions.log("TCP_CHGT_ETAT_DEMARRAGE: Fermeture connexion TCP", LOG_LEVEL_DEBUG_PLUS)
                tcpFonctions.serveur.close()
            end
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

# Cette fonction gère la lecture de messages TCP ASync
# Puis publie le message MQTT 'ModbusReceivedTCP' sur le Topic ==> Déclenchera la règle 'tasmota.add_rule('ModbusReceivedTCP')' -> vers la fonction controleModbus.recupereReponseModBusUDP()
# @type typeClient: Le type de connexion TCP (Serveur ou Client)
tcpFonctions.lireTCP = def(typeClient)
    import string
    import json

    var msg = {}
    var dataRecus = false

    tasmota.yield()

    # Lecture du message par le serveur TCP
    if (typeClient == "Serveur")
        # Vérifie si un nouveau client se connecte
        if (tcpFonctions.serveur.hasclient())
            # Accepte la connexion asynchrone
            tcpFonctions.connexionAsync = tcpFonctions.serveur.acceptasync()
            tcpFonctions.log(f"LIRE_TCP: Connexion Asynchrone TCP acceptée avec le nouveau client '{tcpFonctions.connexionAsync.info()['remote_addr']:s}' !", LOG_LEVEL_DEBUG)
        end

        if (tcpFonctions.connexionAsync != nil)
            # tcpFonctions.connexionAsync.info = {'available': false, 'remote_addr': '192.168.4.1', 'listening': true, 'remote_port': 56132, 'local_addr': '192.168.4.4', 'connected': true, 'local_port': 8888, 'fd': 58}
            if (tcpFonctions.connexionAsync.connected())
                # Réception du message
                var nb_data = tcpFonctions.connexionAsync.available()
                if (nb_data > 0)
                    tcpFonctions.log(f"LIRE_TCP: ------------------------ TCP lire {typeClient:s} ----------------------", LOG_LEVEL_DEBUG_PLUS)
                    tcpFonctions.log(f"LIRE_TCP: Nb Données recues par le {typeClient:s}: {nb_data:i}", LOG_LEVEL_DEBUG_PLUS)

                    msg.insert("Trame", tcpFonctions.connexionAsync.readbytes())
                    msg.insert("Info", tcpFonctions.connexionAsync.info())

                    tcpFonctions.log(string.format(f"LIRE_TCP: Données brutes recues par {typeClient:s}: %s", msg["Trame"].tohex()), LOG_LEVEL_DEBUG_PLUS)

                    dataRecus = true
                end
            end
        end
    # Lecture du message par le client TCP
    elif (typeClient == "Client")
        if (tcpFonctions.client.available() > 0)
            tcpFonctions.log(f"LIRE_TCP: ------------------------ TCP lire {typeClient:s} ----------------------", LOG_LEVEL_DEBUG_PLUS)

            msg.insert("Trame", tcpFonctions.client.readbytes())
            msg.insert("Info", tcpFonctions.client.info())

            tcpFonctions.log(string.format(f"LIRE_TCP: Données brutes recues par {typeClient:s}: %s", msg["Trame"].tohex()), LOG_LEVEL_DEBUG_PLUS)

            dataRecus = true
        end
    end

    # Si des données ont été reçues
    if (dataRecus)
        # Réception d'une trame ModBusTCP
        if (string.find(msg["Trame"].asstring(), "ModbusTCP") > -1)
            # On transforme la chaine en mots
            var typeTitre = "ModbusReceivedTCP"
            
            msg["Trame"] = msg["Trame"][size("ModbusTCP ") .. -1]
            try
                import modbusFonctions
                modbusFonctions.lireMsgModbus("ModbusReceivedTCP", msg)
            except .. as error, message
                tcpFonctions.log(string.format("REGLAGE_TCP_ERREUR: %s --> %s", error, message), LOG_LEVEL_ERREUR)
            end
        end

        tasmota.yield()
        dataRecus = false
    #-
        # Si client envoi 'SALUT CA GAZ' => imprime : bytes('53414C55542043412047415A')
        # Si client envoi bytes("1122334455").tostring() => imprime : bytes('62797465732827313132323333343435352729')
        print(msg)  
        
        # Si client envoi 'SALUT CA GAZ' => imprime : bytes('53414C55542043412047415A')
        # Si client envoi bytes("1122334455").tostring() => imprime : bytes('62797465732827313132323333343435352729')
        print(msg.tostring())   
        # Si client envoi 'SALUT CA GAZ' => imprime : 53414C55542043412047415A
        # Si client envoi bytes("1122334455").tostring() => imprime : 62797465732827313132323333343435352729
        print(msg.tohex())   

        # Si client envoi 'SALUT CA GAZ' => imprime : SALUT CA GAZ
        # Si client envoi bytes("1122334455").tostring() => imprime : bytes('1122334455')
        print(msg.asstring()) 

        # Le module répond
        # tcpFonctions.remote_port = self.connexionAsync.info()["remote_port"]
        # tcpFonctions.connexionAsync.write("J'AI BIEN ENTENDU TA DEMANDE !")
    -#
    end
end

# Cette fonction gère l'envoi de messages TCP ASync
# @type typeClient: Le type de connexion TCP (Serveur ou Client)
# @IP_Dest: L'adresse IP du destinataire (uniquement pour le client TCP)
tcpFonctions.envoiMsgTCP = def(typeClient, IP_Dest, message)
    import json
    import string

    if (serveur["tcp"].find("activation", "OFF") == "OFF")    return      end
    tcpFonctions.log("ENVOI_MSG_TCP: ------------------ envoiMsgTCP ------------------", LOG_LEVEL_DEBUG)

    # # Envoi du message par le serveur TCP
    # if (typeClient == "Serveur")
    #     if (tcpFonctions.connexionAsync != nil)
    #         if (tcpFonctions.connexionAsync.connected())
    #             tcpFonctions.connexionAsync.write(message)
    #         end
    #     end
    # # Envoi du message par le client TCP
    # elif (typeClient == "Client")
    #     if (tcpFonctions.client != nil)
    #         tcpFonctions.client.write(message)
    #     end
    # end
end

# Retourne le module lors de l'importation
return tcpFonctions