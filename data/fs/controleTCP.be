#- NOTES :
    - N'utilise que les connexions TCP Asynchrones
    - Chaque esclave (id > 0) sert de serveur TCP.
        Le Maitre se connecte comme client à chaque esclave pour lequel il veut envoyer un ordre.
-#

#- EXEMPLE DE SCRIPT BERRY DE CONNEXION D'UN CLIENT TCP AU SERVEUR
    import tcpFonctions

    # Crée l'instance du client
    tcpFonctions.client = tcpclientasync()

    # Connecte le client au serveur TCP
    tcpFonctions.client.connect("192.168.4.5", 8888)

    tasmota.delay(250)

    # Récupère les informations pour savoir si le port est disponible pour envoyer des infos ou ordre
    print(tcpFonctions.client.info())
    tcpFonctions.client.write("BONJOUR, CA GAZ. COMMENT VAS TU ??")
    tcpFonctions.client.write(bytes("1122334455").tostring())
-#

var controleTCP

# Driver de gestion des connexions TCP lancées par les modules connectés entre eux
# Classe qui gère la connexion en tant que serveur TCP Async
# Tasmota ne gère pas encore les webSocket
class CONTROLE_TCP
    # Variables
    var connexion
    var connexionAsync
    var port

    def init(port)
        import tcpFonctions

        self.connexion = nil
        self.connexionAsync = nil
        self.port = port

        # Définit les variables du module udpFonctions
        tcpFonctions.port = self.port

        tcpFonctions.log("TCP_SERVER: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
		# Déclenche une action tous les jours à minuit
	    # tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Active les connexions  UDP nécessaires
        if (serveur["udp"].find("activation", "OFF") == "OFF")  
            serveur["udp"]["activation"] = "ON"
            serveur["udp"]["id"] = serveur["tcp"]["id"]

            tasmota.cmd("Restart 1",boolMute)
        end

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        tasmota.add_rule("System", def(value, trigger, msg) tcpFonctions.changementEtatDemarrage(value, trigger, msg) end)	
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) tcpFonctions.changementEtatDemarrage(value, trigger, msg) end, "udpListener_Mqtt")
        tasmota.add_rule("Wifi", def(value, trigger, msg) tcpFonctions.changementEtatDemarrage(value, trigger, msg) end)
        # tasmota.add_rule("Time", def(value, trigger, msg) tcpFonctions.changementEtatDemarrage(value, trigger, msg) end, "udpListener_Time")

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
        tasmota.add_cmd('ReglageTCP', tcpFonctions.reglageTCP)
    end

    # Fonction chargée de récupérer les messages TCP
    def every_250ms()
        import string
        import tcpFonctions

        # Ce sont les esclaves qui servent de serveur TCP
        if (serveur["tcp"]["id"] > 0)
            if (tcpFonctions.serveur == nil)    return  end

            # Traitement du message
            tcpFonctions.msgTCP = tcpFonctions.lireTCP("Serveur")

            tasmota.yield()
        end

        # Pour les clients TCP
        if (serveur["tcp"]["id"] == 0)
            if (tcpFonctions.client == nil)    return  end

            # Traitement du message
            tcpFonctions.msgTCP = tcpFonctions.lireTCP("Client")

            tasmota.yield()
        end
    end
end

# Active le Driver du serveur TCP Async
if (serveur["tcp"].find("activation", "OFF") == "ON")
    controleTCP = CONTROLE_TCP(502)
    tasmota.add_driver(controleTCP)
end