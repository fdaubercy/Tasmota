# Pour l'aide au protocole ModBus: voir le fichier 'ModBus.help'

# Rend ce module solidifiable (ajouté le 2026-07-15).
# Pour Berry, ce n'est qu'un commentaire : aucun effet sur l'appareil, le fichier
# reste utilisable tel quel sur le LittleFS.
# C'est le solidifieur du PC qui la lit (solidify_all_python.be, regex ligne ~52).
# Sans elle, un `custom_berry_solidify` sur ce fichier produit un .h VIDE (379 octets)
# sans la moindre erreur — le piège le plus coûteux de toute la chaîne.
#@ solidify:modbusFonctions

# Définition du module
#
# NE JAMAIS écrire d'appel à module suivi d'une parenthèse et d'un guillemet dans un
# commentaire de ce fichier. addEntryToModtab() (solidify-from-url.py:56) cherche ce
# motif par une regex sur le fichier ENTIER, commentaires compris, et retient la
# PREMIÈRE occurrence pour en faire un identifiant C. Un exemple en commentaire est
# donc lu comme la vraie déclaration. Constaté le 2026-07-16 : un commentaire citant
# l'ancienne forme a régénéré un modules.h invalide, et cassé le build.
#
# Le nom ci-dessous n'a plus son slash initial (retiré le 2026-07-15) : ce nom finit
# collé dans un identifiant C par l'opérateur ## (berry.h:376, be_constobj.h:272), où
# un caractère '/' est illégal — le préprocesseur refuse de coller be_native_module_
# avec lui.
#
# Sans effet sur l'appareil : `import modbusFonctions` (16 usages) charge le FICHIER
# du LittleFS et ne regarde pas ce nom. Une fois solidifié, en revanche, l'import
# cherchera dans la table native PAR NOM — et c'est ce nom-ci qui devra y répondre.
#
# À ne pas confondre avec le CHEMIN passé à gestionFileFolder.compileModule(), qui
# garde son slash : c'est un fichier sur le LittleFS, pas un nom de module.
var modbusFonctions = module("modbusFonctions")

modbusFonctions.DEBUG = nil
modbusFonctions.serialModBus = nil
modbusFonctions.timeout_ReponseModBus_ms = 4000
modbusFonctions.attenteReponse = false
modbusFonctions.clients = [nil, nil, nil, nil, nil, nil]     # 5 connexions TCP possibles au max pour les 5 esclaves ModBus (id = 1 à 5)

# # *************************************************
# # * ModBus Commandes 
# # *************************************************
modbusFonctions.UNDEFINED = 0x00
modbusFonctions.LECTURE_COILS = 0x01
modbusFonctions.LECTURE_ENTREES_DISCRETES = 0x02
modbusFonctions.LECTURE_REGISTRES_HOLDER = 0x03
modbusFonctions.LECTURE_REGISTRES_ENTREES = 0x04
modbusFonctions.ECRITURE_COIL_UNIQUE = 0x05
modbusFonctions.ECRITURE_REGISTRE_UNIQUE = 0x06
modbusFonctions.ECRITURE_COILS = 0x0F                       # functionCode = 15
modbusFonctions.ECRITURE_REGISTRES_HOLDER = 0x10            # functionCode = 16
modbusFonctions.ISALIVE_ESCLAVE = 0x11                      # Inutilisée

modbusFonctions.tabFonctionsName = [
                                        "UNDEFINED",                    # 0x00
                                        "LECTURE_COILS",                # 0x01
                                        "LECTURE_ENTREES_DISCRETES",    # 0x02 
                                        "LECTURE_REGISTRES_HOLDER",     # 0x03
                                        "LECTURE_REGISTRES_ENTREES",    # 0x04
                                        "ECRITURE_COIL_UNIQUE",         # 0x05
                                        "ECRITURE_REGISTRE_UNIQUE",     # 0x06
                                        "", 
                                        "", 
                                        "", 
                                        "", 
                                        "", 
                                        "", 
                                        "", 
                                        "", 
                                        "ECRITURE_COILS",               # 0x0F 
                                        "ECRITURE_REGISTRES_HOLDER",    # 0x10
                                        "ISALIVE_ESCLAVE"               # 0x11
                                    ]

# # *************************************************
# # * ModBus Types de Données 
# # *************************************************
modbusFonctions.tabType = {
                            "undefined": 0,
                            "uint8": 1,
                            "uint16": 2,
                            "uint32": 3,
                            "int8": 4,
                            "int16": 5,
                            "int32": 6,
                            "float": 7,
                            "raw": 8,
                            "hex": 9,
                            "bit": 10
                        }

modbusFonctions.tabErreur = {
                                "noerror": 0,
                                "nodataexpected": 1,
                                "wrongdeviceaddress": 2,
                                "wrongfunctioncode": 3,
                                "wrongstartaddress": 4,
                                "wrongtype": 5,
                                "wrongnbRegistres": 6,
                                "wrongnbValeurs": 7,
                                "tomanydata": 8,
                                "crcerror": 9
}

modbusFonctions.nbRegistres = 0             # Nombre de bits ou registres à lire / écrire
modbusFonctions.nbOctets = 0                # Nombre d'octets à lire / écrire
modbusFonctions.nbValeurs = 0               # Nombre de valeurs à lire / écrire
modbusFonctions.raw = false

modbusFonctions.MBR_MAX_REGISTERS = 64

# trame["nbValeurs"] = Nombre de valeurs à lire / écrire

modbusFonctions.log = def(msg, levelDebug)
    if (modbusFonctions.DEBUG == nil)
        modbusFonctions.DEBUG = drivers["ModBus"].find("debug", "OFF")
    end

    if (modbusFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

# Règle les paramètres des la connexion ModBus Série: Débit, TimeOut
modbusFonctions.configModbusByJson = def() 
    import json
    import string
    import configGlobal
    import introspect

    var modbusJSON = drivers["ModBus"]

    if (modbusJSON.find("activation", "OFF") == "ON" && drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON")
        # Règle la communication ModBus si activée & si maitre ModBus (id = 0)
        if (modbusJSON.find("id", 99) == 0)
            try
                # Règle de débit de la ligne ModBus
                if (configGlobal.testeParam("ModbusBaudrate", modbusJSON["debit"], "int"))
                    modbusFonctions.log(string.format("CONFIG_MODBUS: Regle le Baudrate du port ModBus à %i Bauds !", modbusJSON["debit"]), LOG_LEVEL_DEBUG)
                end

                # Règle le protocole de communication ModBus
                if (configGlobal.testeParam("ModbusSerialConfig", modbusJSON["mode"], "str"))
                    modbusFonctions.log(string.format("CONFIG_MODBUS: Regle le protocole utilisé par ModBus: %s !", modbusJSON["mode"]), LOG_LEVEL_DEBUG)
                end

                # Règle le timeout d'attente d'une réponse par le maitre ModBus
                if (configGlobal.testeParam("ModbusSerialTimeout", modbusJSON["timeoutReponse"], "int"))
                    modbusFonctions.log(string.format("CONFIG_MODBUS: Règle le timeout d'attente d'une réponse par le maitre ModBus à %sms !", modbusJSON["timeoutReponse"]), LOG_LEVEL_DEBUG)
                end
            except .. as e, m
                print('Erreur: ', e, " -> ", m)
            end
        # Règle la communication ModBus si activée (Si Eslave ModBus id > 0)
        elif (modbusJSON.find("id", 0) > 0)
            # Paramétrage port RS485 : gpio_rx:4 gpio_tx:5
            modbusFonctions.serialModBus = serial(modbusJSON["environnement"]["pinsModBus"]["RX"]["pin"], 
                                                    modbusJSON["environnement"]["pinsModBus"]["TX"]["pin"], 
                                                    modbusJSON["debit"], introspect.get(serial, string.format("SERIAL_%s", modbusJSON["mode"])))
        end
    end
end

#- exemples: 
    ReglageModbus logActivation OFF
    ReglageModbus envoiMessageUDP 0x01 TEST
    ReglageModbus envoiMessageTCP 192.168.4.2 TEST

    ReglageModbus BaudrateModbus 9600
    ReglageModbus RecupereBaudrateConn16channels 0x01
    ReglageModbus ReglageBaudrateConn16channels 0x01 19200
    ReglageModbus ActivationReponseCMD ON

    ReglageModbus ImAlive ON
-#
modbusFonctions.reglageModbus = def(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import gestionFileFolder
    import tcpFonctions

    var fonction = false
    var parametres = false
    var reponse_cmnd = "ReglageModbus: "
    
    # Test   
    modbusFonctions.log("REGLAGE_MODBUS: -------------------- ReglageModbus -------------------", LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log("REGLAGE_MODBUS: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log("REGLAGE_MODBUS: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log("REGLAGE_MODBUS: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log("REGLAGE_MODBUS: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    modbusFonctions.log("REGLAGE_MODBUS: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
	if (parametres.size() > 0)	modbusFonctions.log("REGLAGE_MODBUS: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
	if (parametres.size() > 1)	modbusFonctions.log("REGLAGE_MODBUS: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

    # Activation ou désactivation des logs de la liaison RS485 -> ordre: logActivation
    if (string.toupper(fonction) == string.toupper("logActivation"))
        try
            # Adapte le paramètre
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            modbusFonctions.DEBUG = parametres[0]

            # Sauvegarde le paramètre
            drivers["ModBus"]["debug"] = parametres[0]
            persist.save()
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Envoi de messages UDP pour test
    elif (string.toupper(fonction) == string.toupper("envoiMessageUDP"))
        modbusFonctions.log(string.format("REGLAGE_MODBUS: Données ModBus UDP envoyées à %s >>> %s", parametres[0], parametres[1]), LOG_LEVEL_DEBUG)
        # modbusFonctions.envoiMsgModbus = def(parametres[1])
    # Envoi de messages TCP pour test
    elif (string.toupper(fonction) == string.toupper("envoiMessagTCP"))
        modbusFonctions.log(string.format("REGLAGE_MODBUS: Ouverture connexion UDP sur le port %i: %s", 
                                            tcpFonctions.port, tcpFonctions.client.connect(parametres[0], tcpFonctions.port) ? "OK" : "Echec"), LOG_LEVEL_DEBUG_PLUS)

        # Si le client est connecté & socket disponible
        if (tcpFonctions.client.listening() && tcpFonctions.client.connected())
            tasmota.delay(250)
            modbusFonctions.log(string.format("REGLAGE_MODBUS: Données ModBus TCP envoyées à %s >>> %s", parametres[0], parametres[1]), LOG_LEVEL_DEBUG)
            tcpFonctions.client.write(parametres[1])
        end
    # Régle BaudRate de la liaison ModBus ModBus
    elif (string.toupper(fonction) == string.toupper("BaudrateModbus"))
        tasmota.cmd(string.format("ModbusBaudrate %s", str(parametres[0])))
    # Récupération du BaudRate de la liaison ModBus Série avec le Connecteur 16 channels
    elif (string.toupper(fonction) == string.toupper("RecupereBaudrateConn16channels"))
        tasmota.cmd(string.format("ModBusSend {\"deviceaddress\": %s, \"functioncode\": 3, \"startaddress\": 0xFE, \"type\":\"uint16\", \"count\":1}", str(parametres[0])))
    # Règle BaudRate de la liaison ModBus Série avec le Connecteur 16 channels
    elif (string.toupper(fonction) == string.toupper("ReglageBaudrateConn16channels"))
        if (parametres[1] == "1200")
            parametres[1] = "0"
        elif (parametres[1] == "2400")
            parametres[1] = "1"
        elif (parametres[1] == "4800")
            parametres[1] = "2"
        elif (parametres[1] == "9600")
            parametres[1] = "3"
        elif (parametres[1] == "19200")
            parametres[1] = "4"
        else 
            parametres[1] = "5"  # Défaut à 9600
        end
        tasmota.cmd(string.format("ModBusSend {\"deviceaddress\": %s, \"functioncode\": 6, \"startaddress\": 0xFE, \"type\":\"uint16\", \"count\":1, \"Values\":[%s]}", str(parametres[0]), str(parametres[1])))
    # (Des)active la réponse de l'esclave aux commandes ModBus
    elif (string.toupper(fonction) == string.toupper("ActivationReponseCMD"))
        # Adapte le paramètre
        parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))

        # Sauvegarde le paramètre
        drivers["ModBus"]["activationReponseCMD"] = parametres[0]
        persist.save()
    # Force le Client ModBus TCP (Maitre ModBus: id == 0) à se connecter au serveur TCP de ce module (utile si le client ne s'est pas encore connecté ou a perdu la connexion)
    elif (string.toupper(fonction) == string.toupper("ImAlive") && drivers["ModBus"].find("id", 99) == 0)
        # Adapte le paramètre
        parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
        if (parametres[0] == "OFF")     return     end

        # Paramétrage Clients et Serveur ModBus TCP si activé
        if (drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON" && serveur["tcp"].find("activation", "OFF") == "ON")
            # Recherche l'IP de l'esclave ModBus dans la table des périphériques
            var jsonData = json.load(gestionFileFolder.readFile("/json/discovery.json")).find(string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), {})
            var IP = ""
            var id = 0

            # Si maitre ModBus (id == 0) ==> Se connecte en tant que client TCP à l'esclave ModBus
            for item: jsonData.keys()
                # Crée l'instance du client
                if (modbusFonctions.clients[id] == nil)     modbusFonctions.clients[id] = tcpclientasync()      end

                for cle : jsonData[item].keys()
                    if (cle == "maitre")
                        id = jsonData[item][cle]["ModBus"].find("id", 0)
                        IP = jsonData[item][cle]["ModBus"]["TCP"].find("IPAddress", "")

                        # Vérifie la connexion TCP
                        if (!modbusFonctions.clients[id].connected())
                            # Connecte le client au serveur TCP
                            tcpFonctions.log(string.format("REGLAGE_MODBUS: Ouverture connexion TCP [%s] sur le port %i: %s", 
                                                                        IP, tcpFonctions.port, modbusFonctions.clients[id].connect(IP, tcpFonctions.port) ? "OK" : "Echec"), LOG_LEVEL_DEBUG_PLUS)

                            tasmota.delay(250)
                        else tcpFonctions.log(string.format("Le client ModBus TCP est déjà connecté à l'esclave ModBus %i [%s]", id, IP), LOG_LEVEL_DEBUG_PLUS)
                        end

                        break
                    end
                end
            end
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd += string.format("logActivated=%s", modbusFonctions.DEBUG)
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
modbusFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import json
    import tcpFonctions
    import gestionFileFolder
    import udpFonctions

	# Test
	modbusFonctions.log("MODBUS_CHGT_ETAT_DEMARRAGE: -------------------- modBus changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	modbusFonctions.log("MODBUS_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	modbusFonctions.log("MODBUS_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	modbusFonctions.log("MODBUS_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
	
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
            # Paramétrage Clients et Serveur ModBus TCP si activé
            if (drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON" && serveur["tcp"].find("activation", "OFF") == "ON")
                # Active les instances clients ModBus TCP (Si TCP activé & Maitre ModBus id = 0)
                if (drivers["ModBus"]["id"] == 0)
                    modbusFonctions.log("MODBUS_CHGT_ETAT_DEMARRAGE: Initialisation des instances Clients ModBus TCP !", LOG_LEVEL_DEBUG)

                    # Si maitre ModBus (id == 0) ==> Se connecte en tant que client TCP à l'esclave ModBus
                    tasmota.cmd("ReglageModbus ImAlive ON", boolMute)
                # Envoi une commande en UDP ou MQTT pour avertir le Client ModBus TCP de se connecter à ce serveur TCP (Si TCP activé & Esclave ModBus id > 0)
                elif (serveur["udp"].find("activation", "OFF") == "ON" &&drivers["ModBus"]["id"] > 0)
                    modbusFonctions.log("MODBUS_CHGT_ETAT_DEMARRAGE: Force le Client ModBus TCP de se connecter à ce serveur !", LOG_LEVEL_DEBUG)

                    # L'esclave renvoie au maitre ses paramètres par UDP MultiCast
                    var message = string.format("tele/%s/%s %s ON", serveur["mqtt"]["topic"], "ReglageModbus", "ImAlive")

                    # UDP Envoi Esclave -> Maitre
                    # udpFonctions.envoiUDP("UniCast", "192.168.0.43", message)	# UniCast
                    udpFonctions.envoiUDP("MultiCast", "", message)				# MultiCast

                    tasmota.set_timer(diverses["telePeriod"] * 1000, def()  
                                                                        modbusFonctions.log("MODBUS_CHGT_ETAT_DEMARRAGE: Force le Client ModBus TCP à vérifier sa connexion à ce serveur !", LOG_LEVEL_DEBUG)
                                                                        message = string.format("tele/%s/%s %s ON", serveur["mqtt"]["topic"], "ReglageModbus", "ImAlive")
                                                                        udpFonctions.envoiUDP("MultiCast", "", message)				# MultiCast
                                                                    end)
                end
            end

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

# Fonction d'envoi de messages ModBus sur les différentes voies: Série RS485 / TCP / UDP
modbusFonctions.envoiMsgModbus = def(paramMSG, typeMsg, id)
    import json
    import string

    # Valeur par défaut du type de message
    if (typeMsg == nil)    typeMsg = "Commande"     end

    # Décrit le type de commande ModBus envoyée pour le log
    if (paramMSG["FunctionCode"] == modbusFonctions.LECTURE_ENTREES_DISCRETES)  # 0x02
        if (typeMsg == "Commande")  modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Demande l'état de l'interrupteur d'ID=%i !", id), LOG_LEVEL_DEBUG)     end 
    elif (paramMSG["FunctionCode"] == modbusFonctions.LECTURE_REGISTRES_ENTREES)  # 0x04
        if (typeMsg == "Commande")  
            if (paramMSG["StartAddress"] - id + 1 == 4704)
                modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Demande de valeur de l'entrée analogique d'ID=%i !", id), LOG_LEVEL_DEBUG) 
            elif (paramMSG["StartAddress"] - id + 1 == 352)
                modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Demande de valeur du compteur d'ID=%i !", id), LOG_LEVEL_DEBUG) 
            elif ((paramMSG["StartAddress"] - id + 1 == 1312) || (paramMSG["StartAddress"] - id + 1 == 1216))
                modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Demande de valeur du thermomètre d'ID=%i !", id), LOG_LEVEL_DEBUG)
            end 
        end
    elif (paramMSG["FunctionCode"] == modbusFonctions.ECRITURE_REGISTRE_UNIQUE)  # 0x06
        if (typeMsg == "Commande")      modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Commande le relai d'ID=%i !", id), LOG_LEVEL_DEBUG)    end
    elif (paramMSG["FunctionCode"] == modbusFonctions.ECRITURE_REGISTRES_HOLDER)  # 0x10
        if (typeMsg == "Commande")      modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Commande les LEDS WS2812 d'ID=%i !", id), LOG_LEVEL_DEBUG)     end
    end

    # Envoi la trame par port série
    if (drivers["ModBus"].find("activationReponseCMD", "ON") == "ON")
        if(drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON")    modbusFonctions.envoiMsgModbusSerial(paramMSG, typeMsg)     end
    end

    # Envoi la trame par TCP & UDP
    if(drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON")    modbusFonctions.envoiMsgModbusTCP(modbusFonctions.prepareTrame(paramMSG, typeMsg), typeMsg)     end
    if(drivers["ModBus"]["typeComm"].find("UDP", "OFF") == "ON")    modbusFonctions.envoiMsgModbusUDP(modbusFonctions.prepareTrame(paramMSG, typeMsg), typeMsg)     end
end

modbusFonctions.envoiMsgModbusSerial = def(paramMSG, typeMsg)
    import string
    import json
    import diversFonctions

    var reponse = {}

    # Si maitre ModBus (id = 0)
    if (drivers["ModBus"].find("id", 99) == 0)
        # Teste le Flag d'attente de réponse avant d'envoyer = Une commande en cours attend déjà une réponse
        # Si 'faux': Le canal ModBus est libre: la commande peut être envoyée
        if (!modbusFonctions.attenteReponse) 
            # Flag qui marque l'attente d'une réponse pour le maitre (id = 0): Evite de lancer des ordres en même temps
            modbusFonctions.log("ENVOI_MSG_MODBUS: -------------------- envoiMsgModbusSerial -------------------", LOG_LEVEL_DEBUG)
            reponse = tasmota.cmd("ModBusSend " + json.dump(paramMSG), boolMute)

            # Déclenche un timer pour réinitialiser le flag d'attente de réponse
            modbusFonctions.attenteReponse = true
            modbusFonctions.reinitialiseFlagModBus(paramMSG)

            # Teste la réussite de la commande si le canal ModBus était libre
            # Echec de la commande 'ModBusSend()' => Relance la fonction d'envoi dans 500ms & sort de la fonction en cours
            if (reponse.find("ModbusSend", "") == "Failed")
                modbusFonctions.relanceEnvoiMsgModbus(paramMSG, typeMsg)
                modbusFonctions.log("ENVOI_MSG_MODBUS: Envoi du message ModBus = Echec", LOG_LEVEL_DEBUG_PLUS)
                modbusFonctions.log(f"ENVOI_MSG_MODBUS: Echec de la commande ModBus {json.dump(paramMSG):s} => sera renvoyée plus tard !", LOG_LEVEL_DEBUG_PLUS)

                modbusFonctions.attenteReponse = false
            # Erreur de la commande 'ModBusSend()' => Relance la fonction d'envoi dans 500ms & sort de la fonction en cours
            elif (reponse.find("Command", "") == "Error")
                # modbusFonctions.relanceEnvoiMsgModbus(paramMSG, typeMsg)
                modbusFonctions.log("ENVOI_MSG_MODBUS: Envoi du message ModBus = Erreur", LOG_LEVEL_DEBUG_PLUS)
                modbusFonctions.log(f"ENVOI_MSG_MODBUS: Erreur de la commande ModBus {json.dump(paramMSG):s} => Vérifier le paramétrage de la commande ModBus !", LOG_LEVEL_DEBUG_PLUS)

                modbusFonctions.attenteReponse = false
            # Commande réussie
            else (reponse.find("ModbusSend", "") == "Done") 
                modbusFonctions.log("ENVOI_MSG_MODBUS: Commande ModBus envoyée -> " + "ModBusSend " + json.dump(paramMSG), LOG_LEVEL_DEBUG_PLUS)

                reponse = modbusFonctions.prepareTrame(paramMSG, typeMsg)
                modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Message ModBus envoyé = 0x%s", reponse.tohex()), LOG_LEVEL_DEBUG_PLUS)
                modbusFonctions.log("ENVOI_MSG_MODBUS: Envoi du message ModBus = OK", LOG_LEVEL_DEBUG_PLUS)
            end

            # Sort de la fonction après envoi du message par la commande 'ModBusSend()'
            return               
        # Si 'vrai': Une commande précédente attend déjà une reponse => Relance la fonction d'envoi dans 500ms & sort de la fonction en cours
        elif (modbusFonctions.attenteReponse)
            tasmota.set_timer(drivers["ModBus"].find("timeoutReponse", 1000), / -> modbusFonctions.envoiMsgModbusSerial(paramMSG, typeMsg), "envoiMsgEnCours_" + str(paramMSG["StartAddress"]))
            modbusFonctions.log("ENVOI_MSG_MODBUS: Commande ModBus en cours ........ la commande '" + json.dump(paramMSG) + "' sera renvoyée plus tard !", LOG_LEVEL_DEBUG)

            return 
        end
    #- Si Esclave ModBus (id > 0)
        Fonction 0x02 ==> Lecture des entrées discrètes (Read Discrete Inputs) : ex=Récupérer l'état de boutons, capteurs, contacts, interrupteurs.
        ex: Réponse à -> 
        Fonction 0x03 ==> Lecture des registres de maintien (Holding Registers) : ex=Valeur des consignes, paramètres, états d’un capteur, valeur d'un relai (Sur 2 octets)
        Fonction 0x04 ==> "Lecture des entrées analogiques & températures (Input Registers)"     ex=Récupérer une valeur analogique, température, humidité, compteurs etc.
        ex: Réponse à -> ModBusSend {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "type":"float", "Count":1, "Values":0}
        ex: Réponse à -> ModBusSend {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 4704, "type":"float", "Count":1, "Values":0}
        ex: Réponse à -> ModBusSend {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 352, "type":"float", "Count":1, "Values":0}
        Fonction 0x05 ==> "Écriture d’une sortie digitale unique (Coil)"   ex=1 relai
        ex: Réponse à -> ModBusSend {"DeviceAddress": 1, "FunctionCode": 5, "StartAddress": 1, "type":"bit", "Count":1, "Values":[0]}
        Fonction 0x06 ==> "Écriture dans un registre (Write Single Register)"     ex= commande d'un relai de module 16 output
        ex: Réponse à -> ModBusSend {"DeviceAddress": 1, "FunctionCode": 6, "StartAddress": 1, "type":"uint8", "Count":1, "Values":[1, 0]}
                         ModBusSend {"deviceaddress": 2, "functioncode": 6, "startaddress": 0x0001, "type":"uint8", "count":1, "values":[1,0]}
        Fonction 0x10 ==> "Écriture de plusieurs registres (Write Multiple Registers)"     ex= commande d'une LED WS2812B (la couleur, la saturation, la luminosite d'une LED WS2812B)
        ModBusSend {"deviceaddress": 2, "functioncode": 16, "startaddress": 0x0001, "type":"uint16", "count":3, "values":[255, 255, 255]}
        ex: Ne récupère aucune réponse
    -#
    else
        # Prépare la trame ModBus à envoyer
        # var Trame = modbusFonctions.prepareTrame(paramMSG, typeMsg)
        tasmota.yield()

        # Envoi la trame
        reponse = modbusFonctions.prepareTrame(paramMSG, typeMsg)
        modbusFonctions.log(string.format("ENVOI_MSG_MODBUS: Message ModBus envoyé = 0x%s", reponse.tohex()), LOG_LEVEL_DEBUG_PLUS)
        modbusFonctions.serialModBus.write(reponse)
    end
end

#- Fonction d'envoi de la commande ModBus et des réponse ModBus
    par communication UDP si le paramétre est "True" dans _persist.json
    lancé après une commande 'ModBusSend' (si maitre: id == 0) OU une commande 'modbusFonctions.serialModBus.write' (si esclave: id > 0)
    depuis la fonction 'modbusFonctions.envoiMsgModbus(paramMSG, typeMsg)'
-#
modbusFonctions.envoiMsgModbusUDP = def(Trame, typeMsg)
    import udpFonctions
    import json
    import gestionFileFolder
    import re
    import string

    if (drivers["ModBus"]["typeComm"].find("UDP", "OFF") == "OFF" && serveur["udp"].find("activation", "OFF") == "OFF")    return      end
    modbusFonctions.log("ENVOI_MSG_MODBUS_UDP: ------------------ envoiMsgModbusUDP ------------------", LOG_LEVEL_DEBUG)

    # Recherche l'IP de l'esclave ModBus dans la table des périphériques
    var paramDiscovery = json.load(gestionFileFolder.readFile("/json/paramDiscovery.json")).find(string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), {})
    var IP_ModBus = "192.168.4.2"

    # l'id du destinataire est le 1er octet de la trame ModBus
    var id = Trame.get(0, -1)

    # Si maitre ModBus (id == 0)
    if (drivers["ModBus"].find("id", 99) == 0)
        for item: paramDiscovery.keys()
            var pattern = re.compile('^(maitre|esclave[0-9]+)$')
            var result = {}

            for cle : paramDiscovery[item].keys()
                if pattern.match(cle)
                    # result.insert(cle, jsonData[cle])

                    if (paramDiscovery[item][cle].find("ModBus", false))
                        if (paramDiscovery[item][cle]["ModBus"]["id"] == id)
                            IP_ModBus = paramDiscovery[item][cle]["IPAddress"]
                            break
                        end
                    end

                    break
                end
            end
        end
    end

    # Si maitre ModBus (id == 0) => envoi par UDP MultiCast
    if (drivers["ModBus"].find("id", 99) == 0)
        # udpFonctions.envoiUDP("UniCast", IP_ModBus, "ModbusUDP " + Trame.tostring())
        udpFonctions.envoiUDP("MultiCast", "192.168.4.1", "ModbusUDP " + Trame.tostring())
    # Si esclave ModBus (id > 0) => envoi par UDP UniCast
    elif (drivers["ModBus"].find("id", 0) > 0)
        # udpFonctions.envoiUDP("UniCast", "192.168.0.43", "ModbusUDP " + json.dump(Trame))
        udpFonctions.envoiUDP("MultiCast", "", "ModbusUDP " + Trame.tostring())
    end
end

#- Fonction d'envoi de la commande ModBus et des réponse ModBus
    par communication TCP si le paramétre est "True" dans _persist.json
    lancé après une commande 'ModBusSend' (si maitre: id == 0) OU une commande 'modbusFonctions.serialModBus.write' (si esclave: id > 0)
    depuis la fonction 'modbusFonctions.envoiMsgModbus(paramMSG, typeMsg)'

    @ Client: Instance du client TCP OU du serveur TCP, qui envoient la trame
        Client = modbusFonctions.clients[id]        # Si esclave ModBus (id > 0) => Client TCP (Maitre ModBus)
        Client = tcpFonctions.connexionAsync        # Si esclave ModBus (id == 0) => Serveur TCP (Esclave ModBus)
-#
modbusFonctions.envoiMsgModbusTCP = def(Client, Trame, typeMsg)
# modbusFonctions.envoiMsgModbusTCP = def(Trame, typeMsg)
    import json
    import string

    if (drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "OFF" && serveur["tcp"].find("activation", "OFF") == "OFF")    return      end
    modbusFonctions.log("ENVOI_MSG_MODBUS_TCP: ------------------ envoiMsgModbusTCP ------------------", LOG_LEVEL_DEBUG)

    # l'id du destinataire est le 1er octet de la trame ModBus
    var id = Trame.get(0, -1)

    # Si maitre ModBus (id == 0) ==> Se connecte en tant que client TCP à l'esclave ModBus
    if (drivers["ModBus"].find("id", 99) == 0)
        # Récupère les informations pour savoir si le port est disponible pour envoyer des infos ou ordre
        if (Client.connected() && Client.listening())
            modbusFonctions.log(string.format("ENVOI_MSG_MODBUS_TCP: Message ModBus TCP envoyé: %s %s", "ModbusTCP", Trame.tohex()), LOG_LEVEL_DEBUG_PLUS)
            Client.write(bytes().fromstring("ModbusTCP ") + Trame)
        end

    # Si esclave ModBus (id > 0) ==> Envoi la trame ModBus reçue par le serveur TCP
    elif (drivers["ModBus"].find("id", 0) > 0)
        # Si le Maitre ModBus (seul client ModBusTCP) a déjà ouvert la connexion
        if (Client != nil)
            modbusFonctions.log(string.format("ENVOI_MSG_MODBUS_TCP: Message ModBus TCP envoyé: %s %s", "ModbusTCP", Trame.tohex()), LOG_LEVEL_DEBUG_PLUS)
            Client.write(bytes().fromstring("ModbusTCP ") + Trame)
        else modbusFonctions.log("ENVOI_MSG_MODBUS_TCP: Connexion TCP avec le maitre non-initiée !", LOG_LEVEL_ERREUR)
        end
    end
end

# Fonction de lecture de messages ModBus sur le port RS485 (Uniquement pour les esclaves: id > 0)
# Imite le rôle de la fonction native modbus Tasmota
# Puis publie le message MQTT 'ModbusReceived' sur le Topic ==> Déclenchera la règle 'tasmota.add_rule('ModbusReceived')' -> vers la fonction controleModbus.recupereReponseModBus()
modbusFonctions.lireMsgModbus = def(typeTitre, msg)
    import string
    import json

    var paramMSG = nil

    tasmota.yield()

    # Recoit message sur le port RS485
    if (typeTitre == "ModbusReceived")
        if (modbusFonctions.serialModBus != nil && modbusFonctions.serialModBus.available()) 
            #- Exemple de json à construire à la réception d'une trame
                @ Count = Nombre d'octets de données reçus ou retournés dans la réponse
                @ Length = Longueur de la tame entière avec le CRC
                @ Values = valeur ou tableau de valeur
                @ Erreur = Erreur de réception (0=OK, 1=Adresse esclave incorrecte, 9=CRC incorrecte)
            -#
            paramMSG = {typeTitre: {"Trame": "", "DeviceAddress": 0, "FunctionCode": 0, "FunctionName": "", "StartAddress": 0, "Length": 0, "Count": 0, "Values": [], "CRC": 0, "Erreur": 0}}
            paramMSG[typeTitre]["Trame"] = modbusFonctions.serialModBus.read() 

            # Réception du message
            modbusFonctions.log("RECEPTION_MSG_MODBUS: -------------------- lireMsgModbus -------------------", LOG_LEVEL_DEBUG_PLUS)
            modbusFonctions.log(string.format("RECEPTION_MSG_MODBUS: Message ModBus reçu = 0x%s", paramMSG[typeTitre]["Trame"].tohex()), LOG_LEVEL_DEBUG_PLUS)
            
            tasmota.yield()

            # Parse la trame
            modbusFonctions.decrypteMSG(paramMSG, typeTitre)
            if (paramMSG[typeTitre]["Erreur"] != modbusFonctions.tabErreur["noerror"])
                modbusFonctions.log("RECEPTION_MSG_MODBUS: Message ModBus reçu avec erreur", LOG_LEVEL_DEBUG_PLUS)
                return
            end

            tasmota.yield()

            # Prépare le json à publier sur le topic MQTT
            tasmota.publish_result(string.format("{\"%s\": {\"Trame\": \"%s%02X\", \"DeviceAddress\": %i, \"FunctionCode\": %i, \"FunctionName\": \"%s\", \"StartAddress\": %i, \"Length\": %i, \"Count\": %i, \"Values\": %s, \"Erreur\": %i}}", 
                                                    typeTitre,
                                                    paramMSG[typeTitre]["Trame"].tohex(), paramMSG[typeTitre]["CRC"],
                                                    paramMSG[typeTitre]["DeviceAddress"], paramMSG[typeTitre]["FunctionCode"],
                                                    paramMSG[typeTitre]["FunctionName"], paramMSG[typeTitre]["StartAddress"],
                                                    paramMSG[typeTitre]["Length"], paramMSG[typeTitre]["Count"],  
                                                    paramMSG[typeTitre]["Values"].tostring(), paramMSG[typeTitre]["Erreur"] 
                                                ), serveur["mqtt"]["topic"])
            
            # Initialise le buffer & le Flag d'attente de réponse après ordre
            var buffer = modbusFonctions.serialModBus.read()

            modbusFonctions.attenteReponse = false
            modbusFonctions.serialModBus.flush()
        end
    # Recoit message sur le port TCP
    elif (typeTitre == "ModbusReceivedTCP")
        #- Exemple de json à construire à la réception d'une trame
            @ Count = Nombre d'octets de données reçus ou retournés dans la réponse
            @ Length = Longueur de la tame entière avec le CRC
            @ Values = valeur ou tableau de valeur
            @ Erreur = Erreur de réception (0=OK, 1=Adresse esclave incorrecte, 9=CRC incorrecte)
        -#
        paramMSG = {typeTitre: {"Trame": "", "Info": {},"DeviceAddress": 0, "FunctionCode": 0, "FunctionName": "", "StartAddress": 0, "Length": 0, "Count": 0, "Values": [], "CRC": 0, "Erreur": 0}}
        paramMSG[typeTitre]["Trame"] = msg["Trame"] 
        paramMSG[typeTitre]["Info"] = msg["Info"] 

        # Réception du message
        modbusFonctions.log("RECEPTION_MSG_MODBUS: -------------------- lireMsgModbusTCP -------------------", LOG_LEVEL_DEBUG_PLUS)
        modbusFonctions.log(string.format("RECEPTION_MSG_MODBUS: Message ModBus TCP reçu = 0x%s", paramMSG[typeTitre]["Trame"].tohex()), LOG_LEVEL_DEBUG_PLUS)
        
        tasmota.yield()
        # Parse la trame
        modbusFonctions.decrypteMSG(paramMSG, typeTitre)
        if (paramMSG[typeTitre]["Erreur"] != 0)
            modbusFonctions.log("RECEPTION_MSG_MODBUS: Message ModBus reçu avec erreur", LOG_LEVEL_DEBUG_PLUS)
            return
        end

        tasmota.yield()

        # Prépare le json à publier sur le topic MQTT
        tasmota.publish_result(string.format("{\"%s\": {\"Trame\": \"%s%02X\", \"Info\": %s, \"DeviceAddress\": %i, \"FunctionCode\": %i, \"FunctionName\": \"%s\", \"StartAddress\": %i, \"Length\": %i, \"Count\": %i, \"Values\": %s, \"Erreur\": %i}}", 
                                                typeTitre,
                                                paramMSG[typeTitre]["Trame"].tohex(), paramMSG[typeTitre]["CRC"], json.dump(paramMSG[typeTitre]["Info"]),
                                                paramMSG[typeTitre]["DeviceAddress"], paramMSG[typeTitre]["FunctionCode"],
                                                paramMSG[typeTitre]["FunctionName"], paramMSG[typeTitre]["StartAddress"],
                                                paramMSG[typeTitre]["Length"], paramMSG[typeTitre]["Count"],  
                                                paramMSG[typeTitre]["Values"].tostring(), paramMSG[typeTitre]["Erreur"] 
                                            ), serveur["mqtt"]["topic"])
    end
end

# Fonction chargée d'éxécuter la commande ModBus
# Prépare la réponse pour l'envoyer au maitre
modbusFonctions.executeCmdModbus = def(paramMSG)
    import string

    # Initialise le tableau des valeurs
    tasmota.yield()

    modbusFonctions.log("EXECUTE_CMD_MODBUS: -------------------- executeCmdModbus -------------------", LOG_LEVEL_DEBUG)
    modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: DeviceAddress = 0x%02X", paramMSG["DeviceAddress"]), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: StartAddress = 0x%04X", paramMSG["StartAddress"]), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: FunctionCode = 0x%02X ('%s')", paramMSG["FunctionCode"], paramMSG["FunctionName"]), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Count = %i", str(paramMSG["Count"])), LOG_LEVEL_DEBUG_PLUS)

    # Poursuit si l'id du module esclave correspond à celui de la trame ==> N'execute pas la commande
    if (paramMSG["DeviceAddress"] != drivers["ModBus"]["id"])   return false    end

    #-
        Fonction 0x02 ==> Lecture des entrées discrètes (Read Discrete Inputs) : ex=Récupérer l'état de boutons, capteurs, contacts, interrupteurs.
        réponse attendue ==> 
        StartAddress = type + (id-1) (ex: 1, 2, 3, ...): ex Demande de l'état de l'interrupteur n°1=160 (0x00A0)
        Count = 1 (Attend 2 registres de 16 bits)
        ex: Réponse à -> ModBusSend {"DeviceAddress": 3, "FunctionCode": 2, "StartAddress": 160, "type":"uint8", "Count":1, "Values":0}
                    -> 03 02 01 FF E0 70
        Fonction 0x04 ==> "Lecture des entrées analogiques & températures (Input Registers)"     ex=Récupérer une valeur analogique, température, humidité, compteurs etc.
        réponse attendue ==> float: sur 4 octets, 2 registres de 16 bits
        StartAddress = type + (id-1) (ex: 1, 2, 3, ...): ex Demande T° DS18B20 n°1=1312 (0x0520)
        Count = 2 (Attend 2 registres de 16 bits)
        ex: Réponse à -> ModBusSend {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "type":"float", "Count":1, "Values":0}
                    -> 02 04 05 20 00 01 F0 FC
    -#
    # Fonction 0x02 ==> Lecture des entrées discrètes (Read Discrete Inputs) : ex=Récupérer l'état de boutons, capteurs, contacts, interrupteurs.
    # Fonction 0x04 ==> "Lecture des entrées analogiques & températures (Input Registers)"     ex=Récupérer une valeur analogique, température, humidité, compteurs etc.
    if (paramMSG["FunctionName"] == "LECTURE_ENTREES_DISCRETES" || paramMSG["FunctionName"] == "LECTURE_REGISTRES_ENTREES")
        # Détermine le type de capteur à lire
        var typeCapteur = int(paramMSG["StartAddress"])

        # Parcours tous les modules
        for cle: modules.keys()
            #     # Parcours les éléments et capteurs pour le module
            if (type(modules[cle]) != "instance")	continue 	end	

            if (modules[cle].find("activation", "OFF") == "ON")
                for capteurs: modules[cle]["environnement"].keys()
                    if (type(modules[cle]["environnement"][capteurs]) != "instance")	continue 	end

                    for numCapteur: modules[cle]["environnement"][capteurs].keys()
                        if (type(modules[cle]["environnement"][capteurs][numCapteur]) != "instance")	continue 	end

                        if (modules[cle]["environnement"][capteurs][numCapteur].find("activation", "OFF") == "ON")
                            var typo = modules[cle]["environnement"][capteurs][numCapteur]["type"]
                            var id = modules[cle]["environnement"][capteurs][numCapteur]["id"]

                            # Capteur trouvé
                            if (typeCapteur == typo + id - 1)
                                try
                                    # functionCode = 0x04 ==> Récupère la valeur du capteur (Thermomètres ou compteur ou entrées analogiques)
                                    if (paramMSG["FunctionName"] == "LECTURE_REGISTRES_ENTREES")
                                        if (capteurs == "thermometres" || capteurs == "compteurs" || capteurs == "analogiques")
                                            var value = real(modules[cle]["environnement"][capteurs][numCapteur].find("value", 0.00))

                                            paramMSG["Count"] /= 2
                                            
                                            # DS18B20
                                            if (typo == 1312)
                                                paramMSG["type"] = "float"

                                                paramMSG["Values"].push(value)
                                                modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Demande de la valeur de %s: %.2f", modules[cle]["environnement"][capteurs][numCapteur]["nom"], real(value)), LOG_LEVEL_DEBUG_PLUS)
                                            # DHT22 (AM2302)
                                            elif (typo == 1216)
                                                paramMSG["type"] = "float"

                                                paramMSG["Values"].push(value)

                                                value = real(modules[cle]["environnement"][capteurs][numCapteur].find("Humidity", 0.00))
                                                paramMSG["Values"].push(value)

                                                modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Demande de la valeur de %s: %.2f°C / %.2f%%RH", modules[cle]["environnement"][capteurs][numCapteur]["nom"], real(paramMSG["Values"][0]), real(paramMSG["Values"][1])), LOG_LEVEL_DEBUG_PLUS)
                                            # COMPTEURS / ENTRÉES ANALOGIQUES
                                            elif (typo == 352 || typo == 4704)
                                                paramMSG["type"] = "uint32"

                                                # Valeur max du compteur imposée par BERRY: int32 (0x7FFFFFFF = 2 147 483 647)
                                                # Idéalement les valeurs max des compteurs sont:   0x3B9AC9FF = 999 999 999
                                                # Au dela de ce chiffre, il redémarrera a 0
                                                paramMSG["Values"].push(int(value))
                                                modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Demande de la valeur de %s: %u", modules[cle]["environnement"][capteurs][numCapteur]["nom"], value), LOG_LEVEL_DEBUG_PLUS)
                                            end
                                        end
                                    # functionCode = 0x02 ==> Récupère la valeur de l'interrupteur / capteur / bouton
                                    elif (paramMSG["FunctionName"] == "LECTURE_ENTREES_DISCRETES")
                                        if (capteurs == "interrupteurs" || capteurs == "boutons" || capteurs == "capteurs")
                                            var etat = modules[cle]["environnement"][capteurs][numCapteur]["etat"]
                                            var value = 0

                                            paramMSG["type"] = "uint8"

                                            if (modules[cle]["environnement"][capteurs][numCapteur].find("SwitchMode", 1) == 1)
                                                value = (etat == "ON" ? 0xFF : 0x00)
                                            elif (modules[cle]["environnement"][capteurs][numCapteur].find("SwitchMode", 1) == 2)
                                                value = (etat == "ON" ? 0x00 : 0xFF)
                                            end
                                            
                                            paramMSG["Values"].push(value)
                                            modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Values modifiées = %s", str(paramMSG["Values"])), LOG_LEVEL_DEBUG_PLUS)

                                            modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Demande de la valeur de %s: %i (%s)", modules[cle]["environnement"][capteurs][numCapteur]["nom"], int(value), etat), LOG_LEVEL_DEBUG_PLUS)
                                        end
                                    end

                                    # Renvoi exactement la réponse s'il accepte la commande
                                    tasmota.yield()
                                    modbusFonctions.envoiMsgModbus(paramMSG, "Reponse", typeCapteur)
                                except .. as e, m
                                    print('Erreur: ', e, " -> ", m)
                                end
                            end
                        end
                    end
                end
            end
        end
    # Fonction 0x05 ==> "Écriture d’une sortie digitale unique (Coil)"   ex=Activer 1 relai
    # ex: Réponse à -> ModBusSend {"DeviceAddress": 1, "FunctionCode": 5, "StartAddress": 1, "type":"bit", "Count":1, "Values":[0]}
    elif (paramMSG["FunctionName"] == "ECRITURE_COIL_UNIQUE")
        modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: value = 0x%02X", paramMSG["Values"][0]), LOG_LEVEL_DEBUG_PLUS)

        # Execute la commande
        tasmota.cmd(string.format("Power%i %s", paramMSG["StartAddress"], (paramMSG["Values"][0] == 0xFF ? "ON" : "OFF")))

        # Renvoi exactement la même trame s'il accepte la commande
        modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Commande le Relai %i: %s (%s)", paramMSG["StartAddress"], str(paramMSG["Values"]), (paramMSG["Values"][0] == 0xFF ? "ON" : "OFF")), LOG_LEVEL_DEBUG_PLUS)

        tasmota.yield()
        modbusFonctions.envoiMsgModbus(paramMSG, "Reponse", paramMSG["StartAddress"])
    # Fonction 0x06 ==> "Écriture dans un registre (Write Single Register)"     ex=Changer une valeur analogique / Relai temporisé
    # ex: Réponse à -> ModBusSend {"DeviceAddress": 1, "FunctionCode": 6, "StartAddress": 1, "type":"bit", "Count":1, "Values":[0]}
    elif (paramMSG["FunctionName"] == "ECRITURE_REGISTRE_UNIQUE")
        var commande = paramMSG["Values"][0]
        var delai = paramMSG["Values"][1]           # 0s < delai < 255s

        paramMSG["type"] = "uint8"

        modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: commande = 0x%02X", commande), LOG_LEVEL_DEBUG_PLUS)
        modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: delai = 0x%02X", delai), LOG_LEVEL_DEBUG_PLUS)

        # Execute la commande
        tasmota.cmd(string.format("Power%i %s", paramMSG["StartAddress"], (commande == 0x02 ? "ON" : "OFF")))
        # Inverse la commande si le timer est supérieur à 0
        if (delai > 0)
            tasmota.set_timer(delai * 1000, def()   tasmota.cmd(string.format("Power%i %s", paramMSG["StartAddress"], (commande == 0x02 ? "OFF" : "ON")))  end)
        end

        # Renvoi exactement la même trame s'il accepte la commande
        modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Commande le %i: %s (délai = %d)", paramMSG["StartAddress"], (paramMSG["Values"][0] == 0xFF ? "ON" : "OFF"), delai), LOG_LEVEL_DEBUG_PLUS)

        tasmota.yield()
        modbusFonctions.envoiMsgModbus(paramMSG, "Reponse", paramMSG["StartAddress"])
    # Fonction 0x10 ==> "Écriture de plusieurs registres (Write Multiple Registers)"     ex= commande d'une LED WS2812B (la couleur, la saturation, la luminosite)
    # Count = Nb. de registres de 16 bits à ecrire
    # ex Réponse attendue ==> Nb. de registres de 16 bits écrits
    elif (paramMSG["FunctionName"] == "ECRITURE_REGISTRES_HOLDER")
        # Détermine le type device à modifier
        var typeDevice = int(paramMSG["StartAddress"])

        # Parcours tous les modules pour trouver et modifier le device
        for cle: modules.keys()
            # Parcours les éléments et capteurs pour le module
            if (type(modules[cle]) != "instance")	continue 	end	

            if (modules[cle].find("activation", "OFF") == "ON")
                for capteurs: modules[cle]["environnement"].keys()
                    if (type(modules[cle]["environnement"][capteurs]) != "instance")	continue 	end

                    for numCapteur: modules[cle]["environnement"][capteurs].keys()
                        if (type(modules[cle]["environnement"][capteurs][numCapteur]) != "instance")	continue 	end

                        if (modules[cle]["environnement"][capteurs][numCapteur].find("activation", "OFF") == "ON")
                            var typo = modules[cle]["environnement"][capteurs][numCapteur]["type"]
                            var id = modules[cle]["environnement"][capteurs][numCapteur]["id"]

                            # Capteur trouvé
                            if (typeDevice == typo + id - 1)
                                # LEDS WS2812B
                                if (typo == 1376)
                                    try
                                        # Enregistre les nouvelles valeurs en json
                                        var couleur = paramMSG["Values"][0]
                                        var saturation = paramMSG["Values"][1]
                                        var luminosite = paramMSG["Values"][2]

                                        paramMSG["type"] = "uint16"

                                        modules[cle]["environnement"][capteurs][numCapteur]["couleur"] = couleur
                                        modules[cle]["environnement"][capteurs][numCapteur]["saturation"] = saturation
                                        modules[cle]["environnement"][capteurs][numCapteur]["value"] = luminosite
                                        
                                        modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Modifie la couleur de %s: %i", modules[cle]["environnement"][capteurs][numCapteur]["nom"], luminosite), LOG_LEVEL_DEBUG_PLUS)
                                    
                                        # Execute les commandes
                                        var reponse  = tasmota.cmd(string.format("HSBColor %i, %i, %i", couleur, saturation, luminosite), boolMute)

                                        # Prépare les valeurs à renvoyer
                                        paramMSG["Values"][0] = int(string.split(reponse["HSBColor"], ",")[0])
                                        paramMSG["Values"][1] = int(string.split(reponse["HSBColor"], ",")[1])
                                        paramMSG["Values"][2] = int(string.split(reponse["HSBColor"], ",")[2])

                                        modbusFonctions.log(string.format("EXECUTE_CMD_MODBUS: Values = %s", str(paramMSG["Values"])), LOG_LEVEL_DEBUG_PLUS)

                                        # Renvoi exactement la réponse s'il accepte la commande
                                        tasmota.yield()
                                        modbusFonctions.envoiMsgModbus(paramMSG, "Reponse", typeDevice)
                                    except .. as e, m
                                        print('Erreur: ', e, " -> ", m)
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    end
end

#- Fonction chargée de parser les caractéristiques du message ModBus
    S'appuie sur la fonction 'void ModbusBridgeHandle(void)' de 'xdrv_63_modbus_bridge.ino'
    Sort un résultat sous format json
    @typeTitre = "ModbusReceived"
    paramMSG[typeTitre]["Erreur"] permet au traitement de savoir si le message est valide ou non
-#
modbusFonctions.decrypteMSG = def (paramMSG, typeTitre)
    import string
    import crc
    import json

    # Réception du message
    modbusFonctions.log("DECRYPTE_MSG_MODBUS: -------------------- decrypteMSG -------------------", LOG_LEVEL_DEBUG_PLUS)
    paramMSG[typeTitre]["Erreur"] = 0
    paramMSG[typeTitre]["Values"] = []

    # Parse la trame
    paramMSG[typeTitre]["DeviceAddress"] = paramMSG[typeTitre]["Trame"].get(0, -1)
    modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: DeviceAddress = 0x%02X", paramMSG[typeTitre]["DeviceAddress"]), LOG_LEVEL_DEBUG_PLUS)

    # Retourne 'Erreur=1' si l'adresse de l'esclave est incorrecte
    if (paramMSG[typeTitre]["DeviceAddress"] != drivers["ModBus"]["id"])
        # Refuse le message si l'ID de l'esclave ne correspond pas
        if (drivers["ModBus"].find("id", 0) > 0)  
            paramMSG[typeTitre]["Erreur"] = 1 
            modbusFonctions.log("DECRYPTE_MSG_MODBUS: Ce n'est pas un message pour ce module !", LOG_LEVEL_DEBUG_PLUS)
            return   
        end
    end

    tasmota.yield()
    # Détermine la taille totale de la trame reçue
    paramMSG[typeTitre]["Length"] = paramMSG[typeTitre]["Trame"].size()
    modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Taille totale de la trame : %i octets", paramMSG[typeTitre]["Length"]), LOG_LEVEL_DEBUG_PLUS) 

    # Extrait & Supprime le CRC
    paramMSG[typeTitre]["CRC"] = paramMSG[typeTitre]["Trame"].get(paramMSG[typeTitre]["Length"] - 2, -2)
    paramMSG[typeTitre]["crcCalcule"] = modbusFonctions.crc16modbus(paramMSG[typeTitre]["Trame"].resize(paramMSG[typeTitre]["Trame"].size() - 2))
    
    modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: CRC reçu = 0x%04X", paramMSG[typeTitre]["CRC"]), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: CRC calculé = 0x%04X", paramMSG[typeTitre]["crcCalcule"]), LOG_LEVEL_DEBUG_PLUS)

    tasmota.yield()

    # Retourne 'Erreur=2' si le CRC est inexacte
    if (paramMSG[typeTitre]["CRC"] != paramMSG[typeTitre]["crcCalcule"])
        paramMSG[typeTitre]["Erreur"] = 2
        modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Le message ModBus reçu est incomplet & le CRC est inexacte = %04X", paramMSG[typeTitre]["CRC"]), LOG_LEVEL_DEBUG_PLUS)
        return
    end

    # Détermine quelle est la fonction demandée pour définir la taille de la trame attendue
    # Détermine si le message ModBus TCP est une réponse automatique d'esclave ou une réponse à une commande du Maitre
    paramMSG[typeTitre]["FunctionCode"] = paramMSG[typeTitre]["Trame"].get(1, -1)
    if (paramMSG[typeTitre]["FunctionCode"] & 0x80 == 0x80)
        # Transformation pour récupérer la fonction réelle
        paramMSG[typeTitre]["FunctionCode"] &= 0x7F
        modbusFonctions.log("DECRYPTE_MSG_MODBUS: Type de msg Modbus = Automatique", LOG_LEVEL_DEBUG_PLUS)
    else 
        modbusFonctions.log("DECRYPTE_MSG_MODBUS: Type de msg Modbus = Réponse à un ordre", LOG_LEVEL_DEBUG_PLUS)
    end

    paramMSG[typeTitre]["FunctionName"] = modbusFonctions.tabFonctionsName[paramMSG[typeTitre]["FunctionCode"]]
    paramMSG[typeTitre]["StartAddress"] = paramMSG[typeTitre]["Trame"].get(2, -2)

    modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: FunctionCode = 0x%02X ('%s')", paramMSG[typeTitre]["FunctionCode"], paramMSG[typeTitre]["FunctionName"]), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: StartAddress = 0x%04X", paramMSG[typeTitre]["StartAddress"]), LOG_LEVEL_DEBUG_PLUS)

    # Récupère les valeurs reçues en fonction de la fonction
    # FunctionCode = 0x02 (Lecture de l'état d'interrupteurs/capteurs)| 0x03 | 0x04 (Lecture T°/Hum./Compteurs/Entrées analogiques)
    if (paramMSG[typeTitre]["FunctionName"] == "LECTURE_ENTREES_DISCRETES" || paramMSG[typeTitre]["FunctionName"] == "LECTURE_REGISTRES_HOLDER" || paramMSG[typeTitre]["FunctionName"] == "LECTURE_REGISTRES_ENTREES")
        # Détermine le nombre d'octets de données attendus
        paramMSG[typeTitre]["Count"] = paramMSG[typeTitre]["Trame"].get(4, -2)
        modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Count (Nb. octets demandés) = %i", paramMSG[typeTitre]["Count"]), LOG_LEVEL_DEBUG_PLUS)

        # Sort de la fonction si la longueur de la trame reçue est != 8 octets
        if (paramMSG[typeTitre]["Length"] != 8)
            paramMSG[typeTitre]["Erreur"] = 6
            modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Le message ModBus reçu est incomplet ! Longueur reçue = %i octets | Longueur attendue = %i octets", 
                                                paramMSG[typeTitre]["Length"], 8), LOG_LEVEL_DEBUG_PLUS)
            return
        end
    # FunctionCode = 0x05 | 0x06 (Ecriture de la valeur de relais)
    elif (paramMSG[typeTitre]["FunctionName"] == "ECRITURE_COIL_UNIQUE" || paramMSG[typeTitre]["FunctionName"] == "ECRITURE_REGISTRE_UNIQUE")
        # Détermine le nombre d'octets de données attendus
        paramMSG[typeTitre]["Count"] = 2
        modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Count (Nb. octets demandés) = %i", paramMSG[typeTitre]["Count"]), LOG_LEVEL_DEBUG_PLUS)

        # Sort de la fonction si la longueur de la trame reçue est != 8 octets
        if (paramMSG[typeTitre]["Length"] != 8)
            paramMSG[typeTitre]["Erreur"] = 6
            modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Le message ModBus reçu est incomplet ! Longueur reçue = %i octets | Longueur attendue = %i octets", 
                                                paramMSG[typeTitre]["Length"], 8), LOG_LEVEL_DEBUG_PLUS)
            return
        end

        paramMSG[typeTitre]["Values"].push(paramMSG[typeTitre]["Trame"].get(4, -1))
        if(paramMSG[typeTitre]["FunctionName"] == "ECRITURE_REGISTRE_UNIQUE")   paramMSG[typeTitre]["Values"].push(paramMSG[typeTitre]["Trame"].get(5, -1))     end
    # FunctionCode = 0x10 (Ecriture de plusieurs de registres tels que LEDs WS2812B)
    elif (paramMSG[typeTitre]["FunctionName"] == "ECRITURE_REGISTRES_HOLDER")
        # Détermine le nombre de registres de données à écrire
        paramMSG[typeTitre]["Count"] = paramMSG[typeTitre]["Trame"].get(4, -2)
        modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Count (Nb. registres à écrire) = %i", paramMSG[typeTitre]["Count"]), LOG_LEVEL_DEBUG_PLUS)

        # Détermine le nombre d'octets/donnee à écrire
        paramMSG[typeTitre]["type"] = int(paramMSG[typeTitre]["Trame"].get(6, -1) / paramMSG[typeTitre]["Count"])
        for item: modbusFonctions.tabType.keys()
            if (modbusFonctions.tabType[item] == paramMSG[typeTitre]["type"])
                paramMSG[typeTitre]["type"] = item
                break
            end
        end
        modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Type = %s", paramMSG[typeTitre]["type"]), LOG_LEVEL_DEBUG_PLUS)

        # Sort de la fonction si la longueur de la trame reçue est != (9 + Count) octets
        if (paramMSG[typeTitre]["Length"] != (9 + (paramMSG[typeTitre]["Count"] * 2)))
            paramMSG[typeTitre]["Erreur"] = 6
            modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Le message ModBus reçu est incomplet ! Longueur reçue = %i octets | Longueur attendue = %i octets", 
                                                paramMSG[typeTitre]["Length"], (9 + (paramMSG[typeTitre]["Count"] * 2))), LOG_LEVEL_DEBUG_PLUS)
            return
        end

        for nb: 0 .. paramMSG[typeTitre]["Count"] - 1
            paramMSG[typeTitre]["Values"].push(paramMSG[typeTitre]["Trame"].get(7 + (nb * 2), -2))
        end
    end

    modbusFonctions.log(string.format("DECRYPTE_MSG_MODBUS: Values = %s", str(paramMSG[typeTitre]["Values"])), LOG_LEVEL_DEBUG_PLUS)
end

#- Prépare la Trame ModBus à partir des paramètres du message json  à envoyer
    S'appuie sur la fonction 'void CmndModbusBridgeSend(char *json_in)' de 'xdrv_63_modbus_bridge.ino'
    Récupère les données à envoyer par ModBus & Ajoute le CRC
    Se comporte différemment selon que ce message représente une commande ou une réponse
    @paramMSG = json représentant le message ModBus à envoyer
    @typeMsg = "Commande" (valeur par défaut) ou "Reponse"
-#
modbusFonctions.prepareTrame = def(paramMSG, typeMsg)
    import json
    import string

    var Trame = bytes()
    var bitMode = false
    var crcCalcule = 0

    # modbusFonctions.nbValeurs = modbusBridge.count (code C++)
    # modbusFonctions.nbRegistres = modbusBridge.dataCount (code C++)
    # modbusFonctions.nbOctets = modbusBridge.byteCount (code C++)

    # Valeur par défaut du type de message
    if (typeMsg == nil)    typeMsg = "Commande"     end

    # Ecrit les valeurs en big endian par defaut (octets de poids lourds diffusés en 1er): "endian": "lsb"
    # if (paramMSG["Endian"] == nil)    paramMSG["Endian"] = "lsb"     end

    modbusFonctions.log("PREPARE_TRAME_MODBUS: ------------------ prepareTrame ------------------", LOG_LEVEL_DEBUG_PLUS)
    paramMSG["FunctionName"] = modbusFonctions.tabFonctionsName[paramMSG["FunctionCode"]]
    paramMSG["Erreur"] = 0

    # Reconstruction de la trame à envoyer
    Trame.add(paramMSG["DeviceAddress"], 1)
    Trame.add(paramMSG["FunctionCode"], 1)

    # Calcule le nombre d'octets de données à envoyer/pour réponse en fonction du type de donnée
    # Minimum, un valeur envoyée est aux format int8 (pour les coils) / int16 (pour les registres)
    modbusFonctions.nbValeurs = paramMSG.find("Count", 1)

    # Si functionCode = 0x01 |0x02 | 0x0F:
    # Count != Nb de registres
    # Count = Nb de bits à lire / écrire => On calcul le nombre d'octets de données à lire / écrire
    if (paramMSG["FunctionName"] == "LECTURE_COILS" || paramMSG["FunctionName"] == "LECTURE_ENTREES_DISCRETES" || paramMSG["FunctionName"] == "ECRITURE_COILS")
        bitMode = true
    end

    # Induit une erreur si DeviceAddress == 0x00 | FunctionCode > 0x06 && FunctionCode != 0x0F && FunctionCode != 0x10
    if (paramMSG.find("DeviceAddress", 0x00) == 0)
        paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongdeviceaddress"]        # Erreur = 2
    elif (paramMSG["FunctionCode"] > modbusFonctions.ECRITURE_REGISTRE_UNIQUE && paramMSG["FunctionCode"] != modbusFonctions.ECRITURE_COILS && paramMSG["FunctionCode"] != modbusFonctions.ECRITURE_REGISTRES_HOLDER)
        paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongfunctioncode"]         # Erreur = 3
    else
        if (paramMSG["FunctionName"] == "UNDEFINED")    paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongfunctioncode"]     end     # Erreur = 3     
    end

    # Par défaut : type == "int8"
    paramMSG["type"] = paramMSG.find("type", "int8")   

    # Calcule le nombre d'octets à lire / écrire (modbusFonctions.nbOctets)
    if (bitMode)    modbusFonctions.nbOctets = (modbusFonctions.nbValeurs + 7) / 8     end

    # Calcule le nombre de registres à lire / écrire (modbusFonctions.nbRegistres)
    if (paramMSG.find("type", "") == "int8" || paramMSG.find("type", "") == "uint8")
        modbusFonctions.nbRegistres = (bitMode ? modbusFonctions.nbValeurs : ((modbusFonctions.nbValeurs - 1) / 2) + 1)
    elif (paramMSG.find("type", "") == "int16" || paramMSG.find("type", "") == "uint16" || paramMSG.find("type", "") == "")
        if (paramMSG.find("type", "") == "uint16")   paramMSG["type"] = "uint16"     end
        modbusFonctions.nbRegistres = modbusFonctions.nbValeurs
    elif (paramMSG.find("type", "") == "int32" || paramMSG.find("type", "") == "uint32" || paramMSG.find("type", "") == "float")
        modbusFonctions.nbRegistres = (bitMode ? modbusFonctions.nbValeurs : 2 * modbusFonctions.nbValeurs)
    elif (paramMSG.find("type", "") == "raw")
        modbusFonctions.nbRegistres = (bitMode ? modbusFonctions.nbValeurs : ((modbusFonctions.nbValeurs - 1) / 2) + 1)
    elif (paramMSG.find("type", "") == "hex")
        modbusFonctions.nbRegistres = (bitMode ? modbusFonctions.nbValeurs : ((modbusFonctions.nbValeurs - 1) / 2) + 1)
    elif (paramMSG.find("type", "") == "bit")
        modbusFonctions.nbRegistres = (bitMode ? modbusFonctions.nbValeurs : ((modbusFonctions.nbValeurs - 1) / 16) + 1)
    else
        paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongtype"]
    end

    # Previent l'overflow du buffer 
    if ((!bitMode) && (modbusFonctions.nbRegistres > modbusFonctions.MBR_MAX_REGISTERS))
        paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongnbValeurs"]
    end

    if ((bitMode) && (modbusFonctions.nbRegistres > modbusFonctions.MBR_MAX_REGISTERS * 8))
        paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongnbValeurs"]
    end

    var writeDataSize = size(paramMSG["Values"])
    var writeDataSize2 = 0
    var writeData = bytes()

    # Détecte si le nombre de données demandées est valide
    # functionCode = 0x05
    if(paramMSG["FunctionName"] == "ECRITURE_COIL_UNIQUE")
        if (modbusFonctions.nbValeurs != 1)     paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongnbValeurs"]     end
    # functionCode = 0x06
    elif(paramMSG["FunctionName"] == "ECRITURE_REGISTRE_UNIQUE")
    # functionCode = 0x0F
    elif(paramMSG["FunctionName"] == "ECRITURE_COILS")
        if(paramMSG["type"] == "bit")
            writeDataSize2 = writeDataSize
        elif(paramMSG["type"] == "hex")
            writeDataSize2 = writeDataSize * 8
        elif(paramMSG["type"] == "int16")
            writeDataSize2 = writeDataSize * 16
        elif(paramMSG["type"] == "int32")
            writeDataSize2 = writeDataSize * 32
        end
        if (modbusFonctions.nbValeurs > writeDataSize2)  paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongnbValeurs"]     end
    # functionCode = 0x10
    elif(paramMSG["FunctionName"] == "ECRITURE_REGISTRES_HOLDER")
        if (modbusFonctions.nbValeurs > writeDataSize)     paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongnbValeurs"]     end
    end

    # Copie les données à écrire si spécifiées
    # int8 / uint8 => testés avec la fonction 0x04 | 0x06
    # int16 / uint16 => testés avec la fonction 0x04 | 0x06 | 0x10
    # int32 / uint32 => testés avec la fonction 0x04 | 0x10
    # float (même nb d'octets que uint32) => testés avec la fonction 0x04 | 0x06

    if (paramMSG["Erreur"] == modbusFonctions.tabErreur["noerror"] && type(paramMSG["Values"]) == "instance")
        if (modbusFonctions.nbRegistres > 40)
            paramMSG["Erreur"] = modbusFonctions.tabErreur["tomanydata"]
        else
            # Alloue N octets à l'ensemble des données à inscrire
            modbusFonctions.nbRegistres *= 2
            writeData = bytes(-modbusFonctions.nbRegistres)

            # Parcours les valeurs
            for nb: 0 .. writeDataSize - 1
                # Sort de la boucle si il y a une erreur
                if (paramMSG["Erreur"] != modbusFonctions.tabErreur["noerror"])     break   end

                # En fonction du type de données ecrites ou attendues
                if (paramMSG["type"] == "bit")
                    # TODO
                elif (paramMSG["type"] == "hex")
                elif (paramMSG["type"] == "raw")
                elif (paramMSG["type"] == "int8" || paramMSG["type"] == "uint8")
                    writeData[nb] = paramMSG["Values"][nb]
                    writeData[nb + 1] = paramMSG["Values"][nb + 1]
                    if (modbusFonctions.nbRegistres != writeDataSize / 2)    paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongnbValeurs"]    end
                elif (paramMSG["type"] == "int16" || paramMSG["type"] == "uint16")
                    writeData[nb * 2] = paramMSG["Values"][nb] >> 8
                    writeData[(nb * 2) + 1] = paramMSG["Values"][nb]
                elif (paramMSG["type"] == "int32" || paramMSG["type"] == "uint32")
                    writeData[nb * 4] = paramMSG["Values"][nb] >> 24
                    writeData[(nb * 4) + 1] = paramMSG["Values"][nb] >> 16
                    writeData[(nb * 4) + 2] = paramMSG["Values"][nb] >> 8
                    writeData[(nb * 4) + 3] = paramMSG["Values"][nb]
                elif (paramMSG["type"] == "float")
                    writeData.setfloat(nb * 4, paramMSG["Values"][nb])
                    writeData.reverse(nb * 4, 4)
                else
                    paramMSG["Erreur"] = modbusFonctions.tabErreur["wrongtype"]
                end
            end
        end

        # Adapte les données avec le protocole ModBus pour la functionCode = 0x05
        if (paramMSG["FunctionName"] == "ECRITURE_COIL_UNIQUE")
            writeData[0] = (writeData[0] ? 0xFF00 : 0x0000)         # High Byte
        end
    end

    # Post-traitement en fonction de functionCode
    # Fonction 0x01 ==> Lire les coils (bits) : ex=Etat des relais -> Chaque coil est un bit (0 ou 1) représentant une sortie numérique (variable binaire)
    if (paramMSG["FunctionName"] == "LECTURE_ENTREES_DISCRETES")

    # Fonction 0x02 ==> Lecture des entrées discrètes (Read Discrete Inputs) : ex=Récupérer l'état de boutons, capteurs, contacts, interrupteurs.
    elif (paramMSG["FunctionName"] == "LECTURE_ENTREES_DISCRETES")

    # Fonction 0x03 ==> Lecture des registres de maintien de 16 bits (Holding Registers)    ex=Récupérer une valeur entrée analogique, relai, etat d'une led WS2812B (la couleur, la saturation, la luminosite)
    elif (paramMSG["FunctionName"] == "LECTURE_REGISTRES_HOLDER")

    # Fonction 0x04 ==> "Lecture des entrées analogiques & températures (Input Registers)"     ex=Récupérer une valeur analogique, température, humidité, compteurs etc.
    elif (paramMSG["FunctionName"] == "LECTURE_REGISTRES_ENTREES")
        # modbusFonctions.nbRegistres /= 2

        # Ajoute le nombre de registres demandés
        if (typeMsg == "Commande")
            Trame.add(paramMSG["StartAddress"], -2)     # Sur 2 octets
            Trame.add(modbusFonctions.nbRegistres, -2)
        else 
            Trame.add(modbusFonctions.nbRegistres, -1)

            # Ajoute à la trame, les données à écrire
            Trame += writeData
        end
    # Fonction 0x05 ==> "Écriture d’une sortie digitale unique (Coil)"   ex=Activer 1 relai
    # Lors de l'écriture sur un seul Coil ou un seul Registre, le nombre de registres est toujours égal à 1. Nous empêchons également l'écriture de données hors plage.
    elif (paramMSG["FunctionName"] == "ECRITURE_COIL_UNIQUE")
        modbusFonctions.nbRegistres = 1

        # Ajoute à la trame, les données à écrire
        Trame.add(paramMSG["StartAddress"], -2)     # Sur 2 octets
        Trame += writeData
    # Fonction 0x06 ==> "Écriture dans un registre (Write Single Register)"     ex=Relai temporisé
    # Lors de l'écriture sur un seul Coil ou un seul Registre, le nombre de registres est toujours égal à 1. Nous empêchons également l'écriture de données hors plage.
    elif (paramMSG["FunctionName"] == "ECRITURE_REGISTRE_UNIQUE")
        modbusFonctions.nbRegistres = 1

        # Ajoute à la trame, les données à écrire
        Trame.add(paramMSG["StartAddress"], -2)     # Sur 2 octets
        Trame += writeData
    # Fonction 0x0F ==> "Écriture multiple de Coils"        ex=Utilisé pour changer simultanément plusieurs sorties (Write Multiple Coils)
    elif (paramMSG["FunctionName"] == "ECRITURE_COILS")

    # Fonction 0x10 ==> "Écriture de plusieurs registres (Write Multiple Registers)"     ex= commande d'une LED WS2812B (la couleur, la saturation, la luminosite)
    elif (paramMSG["FunctionName"] == "ECRITURE_REGISTRES_HOLDER")
        # Ajoute le nombre de registres demandés
        Trame.add(modbusFonctions.nbValeurs, -2)

        if (typeMsg == "Commande")
            # Ajoute le nombre d'octets
            Trame.add(paramMSG["StartAddress"], -2)     # Sur 2 octets
            Trame.add(modbusFonctions.nbRegistres, -1)

            # Ajoute à la trame, les données à écrire
            Trame += writeData
        end
    end

    tasmota.yield()

    crcCalcule = modbusFonctions.crc16modbus(Trame)
    Trame.add(crcCalcule, -2)

    # Détermine la taille totale de la trame reçue
    paramMSG["Length"] = size(Trame)

    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: Type de msg Modbus = %s", typeMsg), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: DeviceAddress = 0x%02X", paramMSG.find("DeviceAddress", 0)), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: FunctionCode = 0x%02X ('%s')", paramMSG.find("FunctionCode", 0), paramMSG.find("FunctionName", 0)), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: StartAddress = 0x%04X", paramMSG.find("StartAddress", 0)), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: Type de données = %s", paramMSG.find("type", "")), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: BitMode = %s", str(bitMode)), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: NbValeurs (Nombre de valeurs à lire / écrire) = %i", modbusFonctions.nbValeurs), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: NbRegistres (Nombre de bits ou registres à lire / écrire) = %i", modbusFonctions.nbRegistres), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: NbOctets (Nombre d'octets à lire / écrire) = %i", modbusFonctions.nbOctets), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: Values = %s", str(paramMSG.find("Values", 0))), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: WriteData = %s", writeData.tohex()), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: CRC calculé = 0x%04X", crcCalcule), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: Erreur = %i", paramMSG['Erreur']), LOG_LEVEL_DEBUG_PLUS)
    modbusFonctions.log(string.format("PREPARE_TRAME_MODBUS: Longeur de la trame = %i octets", paramMSG["Length"]), LOG_LEVEL_DEBUG_PLUS)

    return Trame
end

# Fonction chargée de relancer une fonction après un timer
modbusFonctions.relanceEnvoiMsgModbus = def(paramMSG, typeMsg)
    # Probleme 'set_timer()' avec l'ESP32-P4
    if (diverses["typeESP"] == "ESP32P4")
        tasmota.add_cron(f"*/{drivers['ModBus'].find('timeoutReponse', 1000) / 1000:i} * * * * *", 
                                            def()
                                                tasmota.remove_cron("envoiMsgModbus_" + str(paramMSG["StartAddress"]))
                                                modbusFonctions.envoiMsgModbusSerial(paramMSG, typeMsg)
                                            end, "envoiMsgModbus_" + str(paramMSG["StartAddress"]))
    else tasmota.set_timer(drivers["ModBus"].find("timeoutReponse", 1000), / -> modbusFonctions.envoiMsgModbusSerial(paramMSG, typeMsg), "envoiMsgModbus_" + str(paramMSG["StartAddress"]))
    end
end

# Fonction chargée de réinitialiser le Flag d'avertissement de connexion ModBus en cours
# après un délai de timeout défini par 'drivers['ModBus']['timeoutReponse']'
modbusFonctions.reinitialiseFlagModBus = def(paramMSG)
    tasmota.set_timer(drivers["ModBus"].find("timeoutReponse", 1000), 
                                            def()
                                                if (modbusFonctions.attenteReponse)
                                                    modbusFonctions.attenteReponse = false
                                                    modbusFonctions.log("ENVOI_MSG_MODBUS: Réinitialisation du Flag 'attenteReponse=false'", LOG_LEVEL_DEBUG_PLUS)
                                                end
                                            end, "resetFlagTimeout_" + str(paramMSG["StartAddress"]))
end

modbusFonctions.crc16modbus = def(buf)
    var crc = 0x0000FFFF
    var polynomial = 0x0000A001

    for pos : 0 .. size(buf) - 1
        var byt = buf.get(pos)

        crc ^= byt & 0x000000FF
        for j : 0 .. 7
            if (crc & 0x00000001) == 0
                crc >>= 1
            else
                crc >>= 1
                crc ^= polynomial
            end
        end
    end

    crc = (crc >> 8) + ((crc & 0x00FF) << 8)
    return crc
end

# Retourne le module lors de l'importation
return modbusFonctions