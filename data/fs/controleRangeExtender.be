#- NOTES :
    - l'ID RangeExtender doit être identique à l'ID udp car ils utilisent tous les 2 le fichier '/json/paramDiscovery.json'
    - Le Maitre Rangeextender active RgxNAPT:
        * Permet aux esclaves de récupérer l'heure et la date et de se connecter au reseau MQTT.
        * On peut alors se connecter à l'esclave:
            . en connectant son PC ou smartphone au reseau Gateway du maitre RangeExtender: ex: 'SERVEUR-GARAGE-GATEWAY'
            . en tapant les liens liés à l'esclave:
                http://ip-esclave
                http://RIDEAU-GARAGE.local
                http://CAPTEURS-CUVE.local

    - Les commande de réglages paramétrées sont :
        * logActivation: Active ou désactive les logs du RangeExtender
            EX: ReglageRangeExtender logActivation OFF

    - Principes de fonctionnement:
        * Dès la connection wifi établie: #Wifi#Connected
            . Les esclaves (id > 0) se connectent d'abord sur le reseau Wifi du Maitre RangeExtender (AP 2) pour synchroniser leur horloge
-#

var controleRangeExtender

# Driver permettant de gérer les connexions des modules connectés au Range Extender
class CONTROLE_RANGE_EXTENDER : Driver
    # Variables
    var rangeExtender

    def init()
        import json
        import rangeExtenderFonctions

        # Définit les variables du module rangeExtenderFonctions
        
        # Si c'est le Point d'accès Range Extender
        self.rangeExtender = serveur.find("rangeExtender", {})

        rangeExtenderFonctions.log("RANGE_EXTENDER: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Configure le module RangeExtender
        rangeExtenderFonctions.configExtenderByJson()

        # Synchronise les ID du RangeExtender et du module ModBus (si activé)
        var modifID = false
        if (drivers["ModBus"].find("activation", "OFF") == "ON")
            if (drivers["ModBus"]["id"] != serveur["rangeExtender"]["id"])
                drivers["ModBus"]["id"] = serveur["rangeExtender"]["id"]
                modifID = true
            end
        end

        # Active les connexions TCP et UDP nécessaires aux communications RangeExtender
        # Synchronise les ID du RangeExtender et des coonexions UDP & TCP
        if (serveur["udp"].find("activation", "OFF") == "OFF")   
            serveur["udp"]["activation"] = "ON"
            serveur["udp"]["id"] = serveur["rangeExtender"]["id"]

            modifID = true
        else
            if (serveur["udp"]["id"] != serveur["rangeExtender"]["id"])
                serveur["udp"]["id"] = serveur["rangeExtender"]["id"]

                modifID = true
            end
        end

        if (serveur["tcp"].find("activation", "OFF") == "OFF")   
            serveur["tcp"]["activation"] = "ON"
            serveur["tcp"]["id"] = serveur["rangeExtender"]["id"]

            modifID = true
        else
            if (serveur["tcp"]["id"] != serveur["rangeExtender"]["id"])
                serveur["tcp"]["id"] = serveur["rangeExtender"]["id"]

                modifID = true
            end
        end

        if (modifID)    tasmota.cmd("Restart 1",boolMute)   end

        # Parcours tous les modules paramétrés
		# - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
		# 	Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
		# 	par la fonction 'every_second()'
		# - Compte les devices non-virtuelles
        # - Compte le nombre de devices activées par type et les range dans un tableau
        # - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
		# - Détache ou attache les boutons et switchs si activés >= 1
		# - Détache ou attache les interrupteurs & capteurs si activés >= 1

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        tasmota.add_rule("System", def(value, trigger, msg) rangeExtenderFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleRangeExtender_System")	
        # tasmota.add_rule("Wifi", def(value, trigger, msg) rangeExtenderFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleRangeExtender_Wifi")
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) rangeExtenderFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleRangeExtender_Mqtt")
        tasmota.add_rule("Time", def(value, trigger, msg) rangeExtenderFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleRangeExtender_Time")

		# Ajoute les commandes personnalisées si le module est activé
		tasmota.add_cmd('ReglageRangeExtender', rangeExtenderFonctions.reglageRangeExtender)
        tasmota.add_cmd('RoutageRangeExtender', rangeExtenderFonctions.routageRangeExtender)
    end

	#- Création de boutons dans le menu principal -#
    #   Ce bouton est géré par le driver 'controleWeb'
    #   Le 'click' sur le bouton doit envoyer une requête sur l'url suivante: '/json?commande=Backlog RgxNAPT ON; RgxPort tcp, 8080, 24587CDE6688, 80;'
    #       appel la fonction 'controleWeb.envoiJson()': prépare la réponse json à la requête
    #       appel la fonction 'webFonctions.traiteCommandeHTTP(typeModule, categorie, commande)'
    #       l'activation et le routage durera environ 20min
#- 	
    def web_add_main_button()
        import rangeExtenderFonctions
        import introspect

        tasmota.yield()

		# Affiche le bouton qui fait le lien vers chacun des modules RangeExtender esclaves connectés
        if (introspect.module("rangeExtenderFonctions") != nil)
            rangeExtenderFonctions.afficheBoutonsModulesEsclaves()
        end
    end	 
-#
#-
    # Création de boutons dans le menu 'Tools'
	def web_add_management_button()
        import webserver
        webserver.content_send("<p></p><button onclick='la(\"&m_toggle_main=1\");'>Toggle Management</button>")
    end	

    # Création de boutons dans le menu 'Configuration'
	def web_add_config_button()
        import webserver
        webserver.content_send("<p></p><button onclick='la(\"&m_toggle_config=1\");'>Toggle Config</button>")
    end	
-#
end

# Active le Driver de controle global des modules
controleRangeExtender = CONTROLE_RANGE_EXTENDER()
tasmota.add_driver(controleRangeExtender) 