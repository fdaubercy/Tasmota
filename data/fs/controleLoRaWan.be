#- Commandes LoRa
    - LoRaConfig : afficher la configuration actuelle.
    - LoRaConfig 1 : définir la configuration LoRa par défaut.
    - LoRaConfig 2 : définir la configuration LoRaWan par défaut.
    - LoRaConfig {"Frequency":868.0,"Bandwidth":125.0} : modifier la fréquence et la bande passante. Les autres paramètres peuvent être modifiés en utilisant la même disposition de paramètres JSON.
    - LoRaSend : désactiver l'hexadécimal et passer au décodage texte.
    - LoRaSend <string> : envoyer en ajoutant \n (retour à la ligne).
    - LoRaSend1 <string> : envoyer en ajoutant \n (retour à la ligne).
    - LoRaSend2 <string> : envoyer.
    - LoRaSend3 <string> : remplacer les caractères d'échappement et envoyer.
    - LoRaSend4 <string> : envoyer au format binaire. Les données des messages de réponse sont codées sous forme de chaînes binaires.
    - LoRaSend5 <string> : envoyer au format hexadécimal. Les données des messages de réponse sont codées sous forme de chaînes hexadécimales.
    - LoRaSend6 <string> : envoi sous forme de chaîne de nombres décimaux délimitée par des virgules.
    - LoRaSend15 ​​<string> : envoi sous forme hexadécimale avec IQ inversé. Les données des messages de réponse sont codées sous forme de chaînes hexadécimales.
    - LoRaOption4 1 : activation de la réception des commandes LoRaCommand. Aucune sécurité : toute personne à portée peut envoyer n'importe quelle commande.
    - LoRaCommand <topic_of_lora_receiver> <command> : envoi de la commande à l'appareil avec un sujet MQTT.
-#

#- Commandes LoRaWan
    - LoRaWanBridge 1 : activation du pont LoRaWan.
    - LoRaWanBridge 0 : désactivation du pont LoRaWan.
    - LoRaOption3 1 : activation du décodage LoRaWan des données reçues de Dragino LDS01 et MerryIoT DW10.
    - SetOption100 1 : suppression de LwReceived du message JSON.
    - SetOption118 1 : déplacement de LwReceived du message JSON vers le sous-sujet, remplaçant la valeur par défaut « SENSOR ».
    - SetOption119 1 : suppression de l'adresse de l'appareil de la charge utile JSON. Peut être utilisé avec LoRaWanName lorsque l'adresse est déjà connue du sujet.
    - SetOption144 1 : inclusion de l'heure dans les messages LwReceived, comme pour les autres capteurs.
    - LoRaWanAppKey<x> <32_character_app_key> : définition de la clé d'application connue de l'appareil ou du nœud LoRaWan à joindre.
    - LoRaWanName<x> <string> : définir un nom convivial pour l'appareil ou le nœud.
-#

var controleLoRaWan

class CONTROLE_LORAWAN : Driver
    # Variables

    def init()
        import loRaWanFonctions

        # Règle la communication ModBus si activée (Si Eslave ModBus)
        loRaWanFonctions.log("CONTROLE_LORAWAN: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Configure la mise en place du réseau LoRaWan
        loRaWanFonctions.configLoRaWanByJson()
        tasmota.yield()

        #-         
            Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
            - Message log sur connexion wifi
        -#
        # tasmota.add_rule("Wifi", def(value, trigger, msg) loRaWanFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleLoRaWan_System")
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) loRaWanFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleLoRaWan_Mqtt") 
        # tasmota.add_rule("System", def(value, trigger, msg) loRaWanFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleLoRaWan_Wifi")
        # tasmota.add_rule("Time", def(value, trigger, msg) loRaWanFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleLoRaWan_Time")

        # Ajoute les règles personnalisées
        tasmota.add_rule('LwReceived', def(value, trigger, msg) self.recupereReponseLoRaWan(value, trigger, msg)    end, "controleLoRaWan_Received")

		# Ajoute les commandes personnalisées
		tasmota.add_cmd('ReglageLoRaWan', loRaWanFonctions.reglageLoRaWan)	
    end

    # Réceptionne chaque trame dans un buffer
    def recupereReponseLoRaWan(value, trigger, msg)

    end
end 

# Active le Driver de controle global des modules
controleLoRaWan = CONTROLE_LORAWAN()
tasmota.add_driver(controleLoRaWan)