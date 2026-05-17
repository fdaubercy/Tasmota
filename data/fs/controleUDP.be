#- NOTES :
    - La transmission entre esclaves & Maitre est réalisée par connexion UDP:
        * Cette connexion est établie au démarrage sur le port 2000.
        * Elle est maintenue tout le temps

    - Les commande de réglages paramétrées sont :
        * logActivation: Active ou désactive les logs de la liaison RS485
            EX: ReglageUDP logActivation OFF
        * envoiMessage: Envoi un message UDP à l'adresse IP passée en paramètre
        EX: ReglageUDP envoiMessage 10.99.0.1 Salut Ca gaz !

    - Dans le fichiers json :'json/discovery.json', il enregistre les paramètres des modules connectés:
        * id, nom, adressMAC, routagePort, routageIP, routageMaitreIP (cette dernière sera transmise après par le maitre)
        * les paramètres de routage vont servir si le RangeExtender est activé
        * Il enregistre aussi les règles de routage pour chaque module connecté.
        * Il contient les paramètres pour le maitre et les esclaves.

    - L'esclave ne peut envoyer en des messages au maitre:
        * qu'en UniCast si il est connecté par le biais du RangeExtender
        * en MultiCast sur un reseau wifi classique
    - Le Maitre peut toujours envoyer en MultiCast

API des messages UDP
    - les identifiants :
        * 0 = maitre
        * 1 à 254 = esclaves
        * 255 = broadcast

    - Les communicationsUDP sont réalisées uniquement sur l'IP Wifi principale (pas celle du RangeExtender: 10.99.0.1)

    - Principes de fonctionnement:
        * Les communications UDP MultiCast sont principalement utilisées
            . les maitres & esclaves établissent la connexion UDP sur le port 2000 (UniCast) / port 3000 (MultiCast)
                    Le Maitre commande tous les esclaves par communication MultiCast
                    Les esclaves répondent par communication UniCast

        * Dès la connection wifi établie: #Wifi#Connected
            . Les esclaves (id > 0) se connectent d'abord au Maitre RangeExtender (AP 2) pour synchroniser leur horloge par NTP et/ou synchroniser leur DS3231
            . Les esclaves (id > 0) enregistrent leurs paramètres dans '/json/discovery.json': OK
            . Les esclaves (id > 0) envoient leurs paramètres par UDP MultiCast au Maitre (fonction 'ReglageUDP forceEnvoiParams ON') / TelePeriod: OK

        * les commandes utilisées respectent l'API Tasmota ou des commandes personnelles
-#

var controleUDP_unicast
var controleUDP_multicast

# Driver de gestion des connexions UDP lancées par les modules connectés au Range Extender
class CONTROLE_UDP
    # Variables
    var udpReception
    var port
    var typeComm
    var parametres
  
    def init(typeComm, ip, port)
        import udpFonctions
        import string
        import json
    
        self.udpReception = udp()
        self.port = port
        self.typeComm = typeComm
        self.parametres = serveur["udp"]

        # Définit les variables du module udpFonctions
        udpFonctions.udpReception[(string.toupper(self.typeComm) == string.toupper("UniCast") ? 0 : 1)] = self.udpReception
        udpFonctions.port[(string.toupper(self.typeComm) == string.toupper("UniCast") ? 0 : 1)] = self.port
        udpFonctions.typeComm[(string.toupper(self.typeComm) == string.toupper("UniCast") ? 0 : 1)] = self.typeComm
        udpFonctions.ip[(string.toupper(self.typeComm) == string.toupper("UniCast") ? 0 : 1)] = ip

        udpFonctions.log("CONTROLE_UDP: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        tasmota.add_rule("System", def(value, trigger, msg, typeComm) udpFonctions.changementEtatDemarrage(value, trigger, msg, self.typeComm) end)	
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) udpFonctions.changementEtatDemarrage(value, trigger, msg) end, "udpListener_Mqtt")
        # tasmota.add_rule("Wifi", def(value, trigger, msg, typeComm) udpFonctions.changementEtatDemarrage(value, trigger, msg, self.typeComm) end)
        # tasmota.add_rule("Time", def(value, trigger, msg) udpFonctions.changementEtatDemarrage(value, trigger, msg) end, "udpListener_Time")

        # Parcours tous les modules paramétrés
		# - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
		# 	Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
		# 	par la fonction 'every_second()'
		# - Compte les devices non-virtuelles
        # - Compte le nombre de devices activées par type et les range dans un tableau
        # - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
		# - Détache ou attache les boutons et switchs si activés >= 1
		# - Détache ou attache les interrupteurs & capteurs si activés >= 1

		# Ajoute les commandes personnalisées si le module est activé
        if (string.toupper(self.typeComm) == string.toupper("UniCast"))
		    tasmota.add_cmd('ReglageUDP', udpFonctions.reglageUDP)
        end
        # tasmota.add_cmd('CommandeUDP', udpFonctions.commandeUDP)
    end

#-  
    def every_100ms()
        import string
        
        # if (string.toupper(self.typeComm) == string.toupper("UniCast"))	
            var packet = self.udpReception.read()
            while packet != nil
                print(string.format("<<<< Données reçues en %s ([%s]:%i): %s", 
                                self.udpReception.remote_port == 2000 ? "UniCast" : "MultiCast", self.udpReception.remote_ip, 
                                self.udpReception.remote_port, packet.asstring()))
                packet = self.udpReception.read()
            end
        # end
    end
-#

    def every_100ms()
        import string
        import udpFonctions
        import json

        # Récupère les messages sur le port UDP (respecte l'API Tasmota)
        var paramMSG = {}
    
        # Traitement du message
        if (udpFonctions.lireUDP("UniCast", paramMSG) || udpFonctions.lireUDP("MultiCast", paramMSG))
            udpFonctions.log("TRAITEMENT_MSG_UDP: Traitement du message en cours ...", LOG_LEVEL_DEBUG_PLUS)

            # paramMSG["msgHex"] = msg
            udpFonctions.log("TRAITEMENT_MSG_UDP: Message=" + paramMSG["msgString"], LOG_LEVEL_DEBUG_PLUS)

            # Traitement du message de type API MQTT
            # Vérifie si c'est une commande Tasmota ou personnalisée
            if (paramMSG.find("prefix", false) && paramMSG.find("commande", false))
                if (paramMSG["prefix"] == "cmnd")
                    tasmota.cmd(paramMSG["commande"])
                # # C'est une réponse
                elif (paramMSG["prefix"] == "stat")
                    tasmota.cmd(paramMSG["commande"])
                # # C'est une télémetrie
                elif (paramMSG["prefix"] == "tele")
                    tasmota.cmd(paramMSG["commande"])
                end
            end

            tasmota.yield()

            # Traitement du message de type TasmotaClient
        end
    end
end

if (serveur["udp"].find("activation", "OFF") == "ON")
    controleUDP_unicast = CONTROLE_UDP("UniCast", "", 2000)
    tasmota.add_driver(controleUDP_unicast)

    controleUDP_multicast = CONTROLE_UDP("MultiCast", "224.3.0.1", 4000)
    tasmota.add_driver(controleUDP_multicast)
end

#-
    # UDP Envoi Esclave -> Maitre
    envoiUDP("UniCast", "192.168.0.43", "hello")	# UniCast
    envoiUDP("MultiCast", "", "hello3")				# MultiCast

    # UDP Envoi Maitre -> Esclave
    envoiUDP("UniCast", "192.168.4.3", "world")		# UniCast
    envoiUDP("MultiCast", "192.168.4.1", "hello2")	# MultiCast
-#

#-
    # UDP Envoi UniCast
    # Esclave UDP Envoi
    u1 = udp()
    u1.begin("", 2000)      # send on all interfaces, choose random port number
    u1.send("192.168.0.43", 2000, bytes().fromstring("hello"))
    u1.close()

    # Maitre UDP Envoi
    u1 = udp()
    u1.begin("", 2000)      # send on all interfaces, choose random port number
    u1.send("192.168.4.3", 2000, bytes().fromstring("world"))
    u1.close()

    # UDP Envoi MultiCast
    # Esclave UDP Envoi
    u2 = udp()
    u2.begin_multicast("224.3.0.1", 4000)
    u2.send_multicast(bytes().fromstring("hello3"))

    # Maitre UDP Envoi
    u2 = udp()
    u2.begin("192.168.4.1", 0)      # Envoi sur l'interface RangeExtender, choose random port number
    u2.send("224.3.0.1", 4000, bytes().fromstring("hello2"))
-#