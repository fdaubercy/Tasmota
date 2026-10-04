#@ solidify:tcpFonctions
var tcpFonctions = module("tcpFonctions")

# Etat modifiable du module, dans une GLOBALE (solidification 2026-09-27). Un module
# solidifie est constant (en flash) : y ecrire leve "'module' value has no writable
# attribute", et ses listes sont figees. La map est creee au premier appel avec les
# valeurs de depart qu'avaient les anciens attributs du module.
def tcpFonctions_etat()
    import global
    if (global._etatTcpFonctions == nil)
        global._etatTcpFonctions = {
            "port": 0,                 # port TCP du serveur
            "serveur": nil,            # objet tcpserver (esclave)
            "client": nil,             # objet tcpclientasync (maitre)
            "connexionAsync": nil,     # connexion acceptee par le serveur
            "msgTCP": nil             # dernier message TCP lu
        }
    end
    return global._etatTcpFonctions
end
tcpFonctions.etat = tcpFonctions_etat


def tcpFonctions_log(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "tcp")
end
tcpFonctions.log = tcpFonctions_log

# Aide de la commande ReglageTCP, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def tcpFonctions_aideReglageTCP(sujet)
    import string
    if (sujet == nil)
        return []     # aucune sous-commande (les logs se reglent avec ReglageLog)
    end
    return nil
end
tcpFonctions.aideReglageTCP = tcpFonctions_aideReglageTCP

def tcpFonctions_reglageTCP(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions

    if diversFonctions.traiteAide("ReglageTCP", payload, tcpFonctions.aideReglageTCP, true)    return    end

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
        if (parametres.size() > 0)	logFonctions.log("REGLAGE_TCP: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS, "tcp")	end
        if (parametres.size() > 1)	logFonctions.log("REGLAGE_TCP: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS, "tcp")	end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["ReglageTCP"]["resultat"] = "OK"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
tcpFonctions.reglageTCP = tcpFonctions_reglageTCP

def tcpFonctions_changementEtatDemarrage(value, trigger, msg)
    import string
    import mqtt
    import tcpFonctions
    import json
    import introspect

    # Test
    tcpFonctions.log("TCP_CHGT_ETAT_DEMARRAGE: -------------------- TCP changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
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
                    tcpFonctions.log(f"TCP_CHGT_ETAT_DEMARRAGE: Initialisation du serveur TCP sur le port :{tcpFonctions.etat()['port']:i}", LOG_LEVEL_DEBUG)
                    tcpFonctions.etat()["serveur"] = tcpserver(tcpFonctions.etat()["port"])
                # Le maitre ouvre une connexion TCP avec chacun des esclaves (serveurs TCP)
                elif (serveur["tcp"]["id"] == 0)
                    # Crée les instances du client TCP
                    tcpFonctions.etat()["client"] = tcpclientasync()
                end
            except .. as error, message
                tcpFonctions.log(string.format("TCP_CHGT_ETAT_DEMARRAGE_ERREUR: %s --> %s", error, message), LOG_LEVEL_ERREUR)
            end
        elif msg[trigger].find("Save", 0)
            if (serveur["tcp"]["id"] > 0)
                tcpFonctions.log("TCP_CHGT_ETAT_DEMARRAGE: Fermeture connexion TCP", LOG_LEVEL_DEBUG_PLUS)
                tcpFonctions.etat()["serveur"].close()
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
tcpFonctions.changementEtatDemarrage = tcpFonctions_changementEtatDemarrage

# Cette fonction gère la lecture de messages TCP ASync
# Puis publie le message MQTT 'ModbusReceivedTCP' sur le Topic ==> Déclenchera la règle 'tasmota.add_rule('ModbusReceivedTCP')' -> vers la fonction controleModbus.recupereReponseModBusUDP()
# @type typeClient: Le type de connexion TCP (Serveur ou Client)
def tcpFonctions_lireTCP(typeClient)
    import string
    import json

    var msg = {}
    var dataRecus = false

    tasmota.yield()

    # Lecture du message par le serveur TCP
    if (typeClient == "Serveur")
        # Vérifie si un nouveau client se connecte
        if (tcpFonctions.etat()["serveur"].hasclient())
            # Accepte la connexion asynchrone
            tcpFonctions.etat()["connexionAsync"] = tcpFonctions.etat()["serveur"].acceptasync()
            tcpFonctions.log(f"LIRE_TCP: Connexion Asynchrone TCP acceptée avec le nouveau client '{tcpFonctions.etat()['connexionAsync'].info()['remote_addr']:s}' !", LOG_LEVEL_DEBUG)
        end

        if (tcpFonctions.etat()["connexionAsync"] != nil)
            # tcpFonctions.etat()["connexionAsync"].info = {'available': false, 'remote_addr': '192.168.4.1', 'listening': true, 'remote_port': 56132, 'local_addr': '192.168.4.4', 'connected': true, 'local_port': 8888, 'fd': 58}
            if (tcpFonctions.etat()["connexionAsync"].connected())
                # Réception du message
                var nb_data = tcpFonctions.etat()["connexionAsync"].available()
                if (nb_data > 0)
                    tcpFonctions.log(f"LIRE_TCP: ------------------------ TCP lire {typeClient:s} ----------------------", LOG_LEVEL_DEBUG_PLUS)
                    tcpFonctions.log(f"LIRE_TCP: Nb Données recues par le {typeClient:s}: {nb_data:i}", LOG_LEVEL_DEBUG_PLUS)

                    msg.insert("Trame", tcpFonctions.etat()["connexionAsync"].readbytes())
                    msg.insert("Info", tcpFonctions.etat()["connexionAsync"].info())

                    tcpFonctions.log(string.format(f"LIRE_TCP: Données brutes recues par {typeClient:s}: %s", msg["Trame"].tohex()), LOG_LEVEL_DEBUG_PLUS)

                    dataRecus = true
                end
            end
        end
    # Lecture du message par le client TCP
    elif (typeClient == "Client")
        if (tcpFonctions.etat()["client"].available() > 0)
            tcpFonctions.log(f"LIRE_TCP: ------------------------ TCP lire {typeClient:s} ----------------------", LOG_LEVEL_DEBUG_PLUS)

            msg.insert("Trame", tcpFonctions.etat()["client"].readbytes())
            msg.insert("Info", tcpFonctions.etat()["client"].info())

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
        # tcpFonctions.etat()["connexionAsync"].write("J'AI BIEN ENTENDU TA DEMANDE !")
    -#
    end
end
tcpFonctions.lireTCP = tcpFonctions_lireTCP

# Cette fonction gère l'envoi de messages TCP ASync
# @type typeClient: Le type de connexion TCP (Serveur ou Client)
# @IP_Dest: L'adresse IP du destinataire (uniquement pour le client TCP)
def tcpFonctions_envoiMsgTCP(typeClient, IP_Dest, message)
    import json
    import string

    if (serveur["tcp"].find("activation", "OFF") == "OFF")    return      end
    tcpFonctions.log("ENVOI_MSG_TCP: ------------------ envoiMsgTCP ------------------", LOG_LEVEL_DEBUG_PLUS)

    # # Envoi du message par le serveur TCP
    # if (typeClient == "Serveur")
    #     if (tcpFonctions.etat()["connexionAsync"] != nil)
    #         if (tcpFonctions.etat()["connexionAsync"].connected())
    #             tcpFonctions.etat()["connexionAsync"].write(message)
    #         end
    #     end
    # # Envoi du message par le client TCP
    # elif (typeClient == "Client")
    #     if (tcpFonctions.etat()["client"] != nil)
    #         tcpFonctions.etat()["client"].write(message)
    #     end
    # end
end
tcpFonctions.envoiMsgTCP = tcpFonctions_envoiMsgTCP

# Retourne le module lors de l'importation
return tcpFonctions