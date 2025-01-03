var controleRS485

class CONTROLE_RS485 : Driver
    # Variables
    var msg
    var serialRS485

    def init()
        import json
        import string
        import RS485Fonctions

        log ("GESTION_CUVE: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
        # - Message log sur connexion wifi
        # - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        # - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        serialRS485 = tasmota.add_rule("System", def(value, trigger, msg) RS485Fonctions.changementEtatDemarrage(value, trigger, msg) end)	
        #tasmota.add_rule("Wifi", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)
        #tasmota.add_rule("Mqtt", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)

        #-     
        Parcours tous les modules paramétrés
        - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
            Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
            par la fonction 'every_second()'
        - Compte les devices non-virtuelles
        - Compte le nombre de devices activés par type et les range dans un tableau
        - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage) 
        -#

		# Ajoute les commandes personnalisées si le module est activé
        # Paramétrage port RS485 : gpio_rx:4 gpio_tx:5 
        var RS485 = controleGeneral.parametres["modules"]["RS485"]
		if controleGeneral.parametres["modules"].find("activation", "OFF") == "ON" && RS485.find("activation", "OFF") == "ON"
			if RS485["environnement"].find("pinsRS485s", false)
				# Ajoute les commandes personnalisées
				tasmota.add_cmd('ReglageRS485', RS485Fonctions.ReglageRS485)					
			end
		end
    end

    def every_second()
        import string
        import re
        import RS485Fonctions

        # Envoi du message sur port RS485 -> "\r" + deviceAddress  + ";" + functionCode + ";" + values + ";" + crc + "\n"
        # values est non-nul si le maitre envoi un parametre à modifier
        self.msg = string.format("%i;%s;%i", 0x1F, (tasmota.read_sensors() == nil ? "pas de sensor" : tasmota.read_sensors()), 12)

        # Envoi le message sur le port RS485
        RS485Fonctions.envoiMsgRS485(self.msg)

        # Recoit message sur le port RS485
        self.msg = serialRS485.read()
        
        # teste la presence des caractères de début et de fin
        if (string.find(self.msg.asstring(), "\r") | string.find(self.msg.asstring(), "\n")) > -1
            # Extrait le texte entre '\r' & '\n'
            if re.match("\r(.*?)\n", self.msg.asstring()) != nil
                self.msg = re.match("(.*?)\r(.*?)\n", self.msg.asstring())[2]
                print("Message RS485 reçu = " + self.msg)
            else print("Message RS485 reçu érroné ! ")
            end
        end
    end
end

# Active le Driver de controle global des modules
controleRS485 = CONTROLE_RS485()
tasmota.add_driver(controleRS485)