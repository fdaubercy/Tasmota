var controleRS485

class CONTROLE_RS485 : Driver
    # Variables
    var msg
    var serialRS485

    def init()
        import json
        import string

        log ("GESTION_CUVE: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
        # - Message log sur connexion wifi
        # - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        # - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        #tasmota.add_rule("System", def(value, trigger, msg) RS485Fonctions.changementEtatDemarrage(value, trigger, msg) end)	
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
				#tasmota.add_cmd('ReglageRS485', RS485Fonctions.ReglageRS485)					
			end
		end
    end

    def every_second()
        import string
        import re
        import crc

        # Paramétrage port RS485 : gpio_rx:4 gpio_tx:5 
        self.serialRS485 = serial(controleGeneral.parametres["modules"]["RS485"]["environnement"]["pinsRS485s"]["RX"]["pin"]
                                                , controleGeneral.parametres["modules"]["RS485"]["environnement"]["pinsRS485s"]["RX"]["pin"]
                                                , controleGeneral.parametres["modules"]["RS485"]["debit"], serial.SERIAL_8N1)

        # Envoi du message sur port RS485 -> "\r" + deviceAddress  + ";" + functionCode + ";" + values + ";" + crc + "\n"
        # values est non-nul si le maitre envoi un parametre à modifier
        self.msg = string.format("%i;%s;%i", 0x1F, (tasmota.read_sensors() == nil ? "pas de sensor" : tasmota.read_sensors()), 12)

        # Envoi le message sur le port RS485
        #RS485Fonctions.envoiMsgRS485(self.msg)
    
        # Calcul & Ajout du CRC au message, puis ajoute les caractères de début et de fin de ligne
        var calculCRC = crc.crc8(0xFF, bytes().fromstring(self.msg))
        self.msg = "\r" + self.msg + ";" + str(calculCRC) + "\n"
    
        # Envoi le message sur le port RS485
        if (self.serialRS485 != nil) 
            self.serialRS485.write(bytes().fromstring(self.msg))
            if re.match("(.*?)\r(.*?)\n", self.msg) == nil
                log ("ENVOI_RS485: Le message RS485 ne sera pas envoyé car il ne possède pas de caractères de début & de fin de ligne !", LOG_LEVEL_DEBUG_PLUS)
            else log ("ENVOI_RS485: Message RS485 envoyé = " + re.match("(.*?)\r(.*?)\n", self.msg)[2], LOG_LEVEL_DEBUG_PLUS)
            end
        end

        # Recoit message sur le port RS485
        #RS485Fonctions.lireMsgRS485()
        
        # # teste la presence des caractères de début et de fin
        # if (string.find(self.msg.asstring(), "\r") | string.find(self.msg.asstring(), "\n")) > -1
        #     # Extrait le texte entre '\r' & '\n'
        #     if re.match("\r(.*?)\n", self.msg.asstring()) != nil
        #         self.msg = re.match("(.*?)\r(.*?)\n", self.msg.asstring())[2]
        #         print("Message RS485 reçu = " + self.msg)
        #     else print("Message RS485 reçu érroné ! ")
        #     end
        # end
    end
end

# Active le Driver de controle global des modules
controleRS485 = CONTROLE_RS485()
tasmota.add_driver(controleRS485)