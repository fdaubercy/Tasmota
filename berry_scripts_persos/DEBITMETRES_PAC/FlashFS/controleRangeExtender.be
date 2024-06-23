var controleRangeExtender

class CONTROLE_RANGE_EXTENDER : Driver
    # Variables
    var rangeExtender
    var modulesConnectes        # Tableau de modules connectés sur l'AP RangeExtender

    def init()
        import introspect
        import rangeExtenderFonctions
        import gestionFileFolder
        import json

        # Si c'est le Point d'accès Range Extender
        self.rangeExtender = introspect.get(controleGeneral, "parametres")["serveur"].find("rangeExtender", {})

        # Réalise le routage
        # Abonnements MQTT aux topics des modules connectés
        if self.rangeExtender.find("idModuleRangeExpender", 99) == 0
			# Récupère les modules connectés enregistrés
            if !gestionFileFolder.readFile("/modulesConnectes.json")
				self.modulesConnectes = {}
				gestionFileFolder.writeFile("/modulesConnectes.json", json.dump(self.modulesConnectes))
			else 
				self.modulesConnectes = json.load(gestionFileFolder.readFile("/modulesConnectes.json"))
				if self.modulesConnectes.size() > 0
					# Enregistre les abonnements MQTT pour capter les emisions des données des capteurs du module 
					# Réalise le routage
					rangeExtenderFonctions.routageAndMqttRangeExtender(self.modulesConnectes)
				end
			end
        end

        # Configure le module tasmota (paramètres spécifiques au RangeExtender)
        if (self.rangeExtender.find("idModuleRangeExpender", 99) == 0)  rangeExtenderFonctions.configExtenderByJson(self.rangeExtender)    end

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        #tasmota.add_rule("System", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end)	
        #tasmota.add_rule("Wifi", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end)
        tasmota.add_rule("Mqtt", def(value, trigger, msg) rangeExtenderFonctions.changementEtatDemarrage(value, trigger, msg) end)

		# Ajoute les commandes personnalisées si le module est activé
		tasmota.add_cmd('ReglageRangeExtender', rangeExtenderFonctions.reglageRangeExtender)
    end






end

# Active le Driver de controle global des modules
controleRangeExtender = CONTROLE_RANGE_EXTENDER()
tasmota.add_driver(controleRangeExtender)