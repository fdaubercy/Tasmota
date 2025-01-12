#- *********************************************************************************************
 * ADS1115 - 4 channel 16BIT A/D converter
 * I2C Address: 0x48, 0x49, 0x4A or 0x4B
 *
 * The ADC input range (or gain) can be changed via the following
 * defines, but be careful never to exceed VDD +0.3V max, or to
 * exceed the upper and lower limits if you adjust the input range!
 * Setting these values incorrectly may destroy your ADC!
 * ADS1115
 * -------
 * Setting "S0" -> 2/3x gain +/- 6.144V  1 bit = 0.1875mV (default)
 * Setting "S1" ->  1x gain   +/- 4.096V  1 bit = 0.125mV
 * Setting "S2" ->  2x gain   +/- 2.048V  1 bit = 0.0625mV
 * Setting "S3" ->  4x gain   +/- 1.024V  1 bit = 0.03125mV
 * Setting "S4" ->  8x gain   +/- 0.512V  1 bit = 0.015625mV
 * Setting "S5" ->  16x gain  +/- 0.256V  1 bit = 0.0078125mV
********************************************************************************************* -#

#- *********************************************************************************************
 * Capteur Analogique immergé dans l'eau de la cuve
 * Détecte la hauteur d'eau dans la Cuve
 * Variation de tension de 0 à 10V
 *
 * Attention l'ADS1115 n'accepte des tensions que de 0 à 6.144V
 * Donc nécessite l'emploi d'un pont diviseur de tension 10V vers 6V
********************************************************************************************* -#

var controleCuve

class CAPTEURS_CUVE : Driver
	# Variables
	var ads1115
    var ajustement
    var gain
    var sensors
    var flagINIT        # Flag marquant la fin de l'initialisation du module principal

    def init()
        import json
        import string
        import persist
        import gestionFileFolder

        var parametres = persist.find("parametres")

        self.ads1115 = [0.00, 0.00, 0.00, 0.00]
        self.flagINIT = 0

        log ("CONTROLE_CUVE: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        #-         
            Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
            - Message log sur connexion wifi
            - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
            - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        -#
        # tasmota.add_rule("Wifi", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)  
        # tasmota.add_rule("System", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)  

        # Parcours tous les modules paramétrés
		# - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
		# 	Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
		# 	par la fonction 'every_second()'
		# - Compte les devices non-virtuelles
        # - Compte le nombre de devices activées par type et les range dans un tableau
        # - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
		# - Détache ou attache les boutons et switchs si activés >= 1
		# - Détache ou attache les interrupteurs & capteurs si activés >= 1
        var modules = parametres["modules"]["cuve"]
        if modules.find("activation", "OFF") == "ON"
            var ADS1115 = modules["environnement"].find("ADS1115", false)
            if (ADS1115)
                if ADS1115.find("activation", "OFF") == "ON"
                    controleGeneral.nbIO["nbAnaActives"] = 0
                    controleGeneral.nbIO["nbAnaReels"] = 0

                    for cleANA: ADS1115.keys()
                        if type(ADS1115[cleANA]) != "instance"   continue    end

                        # Si l'entrée analogique est activée
                        if ADS1115[cleANA].find("activation", "OFF") == "ON" && ((ADS1115[cleANA].find("pin", -1) != -1  && ADS1115[cleANA].find("virtuel", "OFF") == "OFF") || ADS1115[cleANA].find("virtuel", "OFF") == "ON")
                            controleGeneral.nbIO["nbAnaActives"] = controleGeneral.nbIO.find("nbAnaActives", 0) + 1	

                            # Nb d'entrées analogiques réelles (non-virtuels)
                            if ADS1115[cleANA].find("activation", "OFF") == "ON" && ADS1115[cleANA].find("virtuel", "OFF") == "OFF"
                                controleGeneral.nbIO["nbAnaReels"] = controleGeneral.nbIO.find("nbAnaReels", 0) + 1
                            end
                        end
                    end

                    # Enregistre ou Mets à jour en variable les capteurs activés dans un tableau
                    if (gestionFileFolder.readFile("/nbIO.json") != json.dump(controleGeneral.nbIO))
                        gestionFileFolder.writeFile("/nbIO.json", json.dump(controleGeneral.nbIO))
                    end

                    log (string.format("CONTROLE_CUVE: Nb. de d'entrées analogiques actives = %i !", controleGeneral.nbIO.find("nbAnaActives", 0)), LOG_LEVEL_DEBUG)
                    log (string.format("CONTROLE_CUVE: Nb. de d'entrées analogiques réelles = %i !", controleGeneral.nbIO.find("nbAnaReels", 0)), LOG_LEVEL_DEBUG)
                end
            end
        end

		# Récupère le capteur analagique 'A0' étalon
        if controleGeneral.nbIO["nbAnaActives"] > 0
            self.ajustement = json.load(tasmota.read_sensors())["ADS1115"]["A0"]
            log (string.format("CONTROLE_CUVE: Ajustement=%d", self.ajustement), LOG_LEVEL_INFO)

            # Récupère le gain du capteur
            var pasGain = [0.1875, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125]
            self.gain = pasGain[int(string.split(tasmota.cmd("Sensor12", boolMute)["ADS1115"]["Settings"], "S")[1])]
            log (string.format("CONTROLE_CUVE: Gain=%.4f", self.gain), LOG_LEVEL_INFO)

            # Vérifie si on doit interdire l'affichage des valeurs de capteurs sur la page html
            if (modules["environnement"]["ADS1115"].find("affichageWebSensor", false))
                tasmota.cmd(string.format("WebSensor12 %s", modules["environnement"]["ADS1115"].find("affichageWebSensor", "ON")), boolMute)
            end
        end

        # Ajoute les commandes personnalisées si le module est activé

        # Marqueur de fin d'initialisation du module principal
        self.flagINIT = 1 
    end

    def web_sensor()
        import json
        import string

        var htmlSensor = ""

        # Récupère les capteurs
        self.sensors = json.load(tasmota.read_sensors())

        # Corrige les valeurs des capteurs analogiques avec la valeur étalon
        self.ajustement = self.sensors["ADS1115"]["A0"]
        for nb: 0 .. 3
            self.ads1115[nb] = self.sensors["ADS1115"]["A" + str(nb)] - self.ajustement
        end

        # Affichage sur page web
        log (string.format("CAPTEURS_CUVE: %d", self.ads1115[3]), LOG_LEVEL_INFO)
        htmlSensor += string.format("{s}Capteur de Niveau de Cuve{m}%.3fV{e}", real(self.ads1115[3] * self.gain) / 1000)
        tasmota.web_send(htmlSensor)
    end
end

# Active le Driver de controle global des modules
controleCuve = CAPTEURS_CUVE()
tasmota.add_driver(controleCuve)