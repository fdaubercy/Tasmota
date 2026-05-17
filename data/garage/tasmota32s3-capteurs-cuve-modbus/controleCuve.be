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
 * 
 * Le capteur analagique A0 sert d'étalon pour ajuster la valeur max
 * Le capteur analagique A1 sert d'étalon pour ajuster la valeur min
********************************************************************************************* -#

var controleCuve

class CAPTEURS_CUVE : Driver
	# Variables
	var ads1115
    var gain
    var flagINIT        # Flag marquant la fin de l'initialisation du module principal

    # Flags pour les logs à enregistrer
    var indiceLog
    var nbLogsFilesMax
    var fileLogSize_Ko

    def init()
        import cuveFonctions
        import json
        import gestionFileFolder
        import string

        self.ads1115 = [0.00, 0.00, 0.00, 0.00]
        self.flagINIT = 0

        # Flags pour les logs à enregistrer
        self.indiceLog = 0
        self.nbLogsFilesMax = modules["cuve"]["logs"]["nbLogsFiles"]
        self.fileLogSize_Ko = modules["cuve"]["logs"]["fileLogSize_Ko"]

        var typeConnex
        var moduleConnex
        var jsonData

        cuveFonctions.log("CONTROLE_CUVE: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Vérifie si des logs doivent être crées
        if (modules["cuve"].find("logs", {}).find("nbLogsFiles", 0) != nil || modules["cuve"].find("logs", {}).find("nbLogsFiles", 0) > 0)
            var fileLog = string.format(modules["cuve"]["logs"]["fileLogName"], modules["cuve"]["logs"]["nbLogsFiles"])

            # Compte le nombre de fichiers de logs présents
            self.indiceLog = gestionFileFolder.compteIndiceMaxFileLogs(fileLog)
            if (self.indiceLog == 0)    self.indiceLog = 1      end

            # Déclenche périodiquement /60s, l'enregistrement en logs
            tasmota.add_cron("*/60 * * * * *", /-> self.enregistreLogs(fileLog), "majLogCuve")
        end

        #-         
            Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
            - Message log sur connexion wifi
            - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
            - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        -#
        # tasmota.add_rule("Wifi", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end)  
        # tasmota.add_rule("System", def(value, trigger, msg) cuveFonctions.changementEtatDemarrage(value, trigger, msg) end) 

        #- Parcours tous les modules paramétrés
		    - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
		        Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
		        par la fonction 'every_second()'
		    - Compte les devices non-virtuelles
            - Compte le nombre de devices activées par type et les range dans un tableau
            - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
		    - Détache ou attache les boutons et switchs si activés >= 1
		    - Détache ou attache les interrupteurs & capteurs si activés >= 1
        -#

        # Désactive le driver correspondant si nécessaire
        # Il y a des entrées analogiques actives mais pas d'entrées analogiques réelles
        # Les règles des entrées analogiques réelles sont gérées par le module général
        if (controleGeneral.nbIOActivesJSON["analogiques"]["actives"]["nb"] > controleGeneral.nbIOActivesJSON["analogiques"]["reels"]["nb"])
            if (drivers["I2C"].find("activation", "OFF") == "ON")
                try
                    if (drivers["I2C"]["environnement"]["ADS1115"].find("activation", "OFF") == "ON")
                        # Vérifie la plage de mesure paramétrée pour l'ADS1115
                        cuveFonctions.voltageMax = int(tasmota.cmd("Sensor12", boolMute)["ADS1115"]["Range"])
                        log("INIT_ADS1115: Voltage Max.: " + str(cuveFonctions.voltageMax), LOG_LEVEL_DEBUG)

                        # Mets à jour les valeurs des capteurs
                        log("INIT_ADS1115: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
                        cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", "")
                        tasmota.add_cron("*/60 * * * * *", /-> cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", ""), "majNiveauCuve")
                    end
                except .. as error, message
                    cuveFonctions.log(string.format("INIT_CUVE_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                end
            end
        end

        tasmota.yield()

        # Ajoute les commandes personnalisées si le module est activé
        tasmota.add_cmd('ReglageCuve', cuveFonctions.reglageCuve)
        tasmota.add_cmd('ReglageAna', cuveFonctions.reglageAna)

        # Marqueur de fin d'initialisation du module principal
        self.flagINIT = 1 
    end

    def every_second()
    end

    # Affiche les capteurs du module cuve sur la page web
    def web_sensor()
        import json
        import string
        import persist
        import introspect
        import cuveFonctions
        import gestionFileFolder

        var nameJsonSensor = string.split(modules["cuve"]["environnement"]["analogiques"]["analogique1"]["virtuel"],"_")[1]
        var variablesRemplacement

        tasmota.yield()

        # Affiche sur la page web le capteur de niveau de cuve 
        gestionFileFolder.readFileByLineAndContentSend("/sd/css/webSensor.css", "", "web_send")
        
        # Pour les entrées analogiques
        variablesRemplacement = {}
        if (modules["cuve"]["environnement"].find("analogiques", false))    # && cuveFonctions.sensorsCuve.find("niveauCuve", false))
            log("WEBSERVER_CUVE: Envoi a la page web de l'etat des capteurs !", LOG_LEVEL_DEBUG)

            # Parcours les entrées analogiques
            variablesRemplacement.insert("drivers->nom", modules["cuve"]["environnement"]["analogiques"]["name"])
            for cle: modules["cuve"]["environnement"]["analogiques"].keys()
                var anaJson = modules["cuve"]["environnement"]["analogiques"][cle]
                if type(anaJson) != "instance"  continue    end

                # Pour les entrées analogiques virtuelles de type ADS1115
                if (anaJson.find("activation", "OFF") == "ON" && anaJson.find("virtuel", "OFF") != "OFF")
                    if (anaJson["virtuel"] == "I2C_ADS1115")
                        # Ajoute à la page web
                        if (anaJson["id"] == 1)
                            variablesRemplacement.insert("sensorsCuve->valeurCapteurHauteur->titre", anaJson["nom"])
                            variablesRemplacement.insert("sensorsCuve->valeursAnalogiques->valeurCapteurHauteur", str(cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"]) + "mV")

                            variablesRemplacement.insert("sensorsCuve->hauteurEau->titre", "Hauteur Eau: ")
                            variablesRemplacement.insert("sensorsCuve->niveauCuve->hauteurEau", str(cuveFonctions.sensorsCuve["niveauCuve"]["hauteurEau"]) + "cm")

                            cuveFonctions.log(string.format("CAPTEURS_CUVE: %s = %imV", anaJson["nom"], real(cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"])), LOG_LEVEL_INFO)
                        end
                    end
                end
            end

            # Calcul le pourcentage d'eau dans la cuve & le volume disponible
            variablesRemplacement.insert("sensorsCuve->tauxRemplissage->titre", "Taux de remplissage: ")
            variablesRemplacement.insert("sensorsCuve->niveauCuve->tauxRemplissage", str(cuveFonctions.sensorsCuve["niveauCuve"]["tauxRemplissage"] * 100) + "%")
            variablesRemplacement.insert("sensorsCuve->volume->titre", "Volume disponible: ")	
            variablesRemplacement.insert("sensorsCuve->niveauCuve->volume", str(cuveFonctions.sensorsCuve["niveauCuve"]["volume"]) + "L")	

            # Change la couleur des bordures en fonction du niveau de remplissage
            if (light.get(0)["rgb"] != "1A1A1A")
                variablesRemplacement.insert("colorWs2812", light.get(0)["rgb"])
            else
                variablesRemplacement.insert("colorWs2812", "eaeaea")
            end

            # Modifie le code html à afficher et l'envoi
            gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorNiveauCuve.html', variablesRemplacement, "web_send")
        end

        tasmota.yield()

        # Pour les thermometres
        if (modules["cuve"]["environnement"].find("thermometres", false))
            log("WEBSERVER_CUVE: Envoi a la page web de l'etat des thermometres !", LOG_LEVEL_DEBUG)

            # Parcours les thermomètres
            for cle: modules["cuve"]["environnement"]["thermometres"].keys()
                var thermoJson = modules["cuve"]["environnement"]["thermometres"][cle]
                if type(thermoJson) != "instance"  continue    end

                if (thermoJson.find("activation", "OFF") == "ON")
                    var temperature = 0.00
                    var humidity = 0.00

                    # Récupère la valeur des thermomètres dans le json sensors
                    # DS18B20
                    if (thermoJson["type"] == 1312 && introspect.get(controleGeneral, "sensors").find("DS18B20", false))
                        variablesRemplacement = {}
                        variablesRemplacement.insert("drivers2->nom", "Surveillance T°")

                        var serialNumber = thermoJson["serialNumber"]
                        temperature = real(introspect.get(controleGeneral, "sensors")["DS18B20"]["Temperature"])
                        temperature = int(temperature * 10) / 10.0

                        # Ajoute à la page web
                        variablesRemplacement.insert("sensors->DS18B20->titre", thermoJson["nom"])
                        variablesRemplacement.insert("sensors->DS18B20->Temperature", str(temperature) + "°C")	
                        cuveFonctions.log(string.format("CAPTEURS_CUVE: %s = %.2f°C", thermoJson["nom"], temperature), LOG_LEVEL_INFO)

                        # Modifie le code html à afficher et l'envoi
                        gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorDS18B20.html', variablesRemplacement, "web_send")
                    # DHT22
                    elif (thermoJson["type"] == 1216)
                        variablesRemplacement = {}
                        variablesRemplacement.insert("drivers2->nom", "Surveillance T° & Humidité")

                        temperature = real(introspect.get(controleGeneral, "sensors")["AM2301"]["Temperature"])
                        temperature = int(temperature * 10) / 10.0

                        humidity = real(introspect.get(controleGeneral, "sensors")["AM2301"]["Humidity"])
                        humidity = int(humidity * 10) / 10.0

                        # Ajoute à la page web
                        variablesRemplacement.insert("sensors->AM2301->titre", thermoJson["nom"])
                        variablesRemplacement.insert("sensors->AM2301->titre2", string.replace(thermoJson["nom"], "T°", "Humidité"))
                        variablesRemplacement.insert("sensors->AM2301->Temperature", str(temperature) + "°C")		
                        variablesRemplacement.insert("sensors->AM2301->Humidity", str(humidity) + "%RH")	
                        cuveFonctions.log(string.format("CAPTEURS_CUVE: %s = %.1f°C / %.1f%%RH", thermoJson["nom"], temperature, humidity), LOG_LEVEL_INFO)

                        # Modifie le code html à afficher et l'envoi
                        gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorDHT22.html', variablesRemplacement, "web_send")
                    end
                end
            end
        end
    end

    # Ajoute les données de cuve à la réponse JSON
    def json_append()
        import json
        import string
        import cuveFonctions


        # Pour les entrées analogiques
        if (modules["cuve"]["environnement"].find("analogiques", false))
            # Ajoute à la réponse JSON
            tasmota.response_append(string.format(", \"sensorsCuve\": %s", json.dump(cuveFonctions.sensorsCuve)))
        end
        tasmota.yield()
    end

    # Enregistre dans les logs le niveau de cuve et la température de cuve
    def enregistreLogs(fileChemin)
        import json
        import string
        import introspect
        import gestionFileFolder
        import cuveFonctions

        # Sort de la fonction si les données qui nous intéressent sont absents
        if (cuveFonctions.sensorsCuve == nil)     return      end
        cuveFonctions.log("ENREGISTRE_LOGS_CUVE: Enregistrement des données de cuve en logs !", LOG_LEVEL_DEBUG_PLUS)

        var temperatureCuve = 0.00
        if (introspect.get(controleGeneral, "sensors").find("DS18B20", false))
            temperatureCuve = real(introspect.get(controleGeneral, "sensors")["DS18B20"]["Temperature"])
            temperatureCuve = int(temperatureCuve * 10) / 10.0
        end

        tasmota.yield()

        # Ecrit les données
        var data = "{\"date\":\"" + tasmota.time_str(tasmota.rtc("local")) + 
                        "\",\"niveauCuve\":" + json.dump(cuveFonctions.sensorsCuve["niveauCuve"]) + 
                        (introspect.get(controleGeneral, "sensors").find("DS18B20", false) ? ",\"temperatureCuve\":" + str(temperatureCuve) : "") + "}"

        gestionFileFolder.enregistreLogs(fileChemin, self, data)
    end
end

# Active le Driver de controle global des modules
controleCuve = CAPTEURS_CUVE()
tasmota.add_driver(controleCuve)