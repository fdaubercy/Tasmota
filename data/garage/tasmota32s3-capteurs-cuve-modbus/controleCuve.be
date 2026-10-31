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
 * Attention : une entree de l'ADS1115 ne doit JAMAIS depasser sa tension d'alimentation (VDD + 0,3 V),
 * quelle que soit la plage Sensor12 (le +/-6.144V n'autorise pas 6 V sur un ADS1115 alimente en 3,3 V).
 * ADS1115 de la cuve alimente en 3,3 V (choix du 2026-10-11) : pont diviseur 0-10V R1 = 24 kOhm / R2 = 10 kOhm,
 * SDA/SCL en direct sur l'ESP32 (en 5 V : R1 = 15 kOhm et convertisseur de niveau obligatoire) -> ReglageAna cablage.
 * Detail : outils_docs/Electronique/ADS1115/CABLAGE_ADS1115.md
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
        self.nbLogsFilesMax = modules["cuve"].find("logs", {}).find("nbLogsFiles", 0)
        self.fileLogSize_Ko = modules["cuve"].find("logs", {}).find("fileLogSize_Ko", 10000)

        var typeConnex
        var moduleConnex
        var jsonData

        cuveFonctions.log("CONTROLE_CUVE: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Vérifie si des logs doivent être crées
        if (modules["cuve"].find("logs", {}).find("nbLogsFiles", 0) > 0)      # 0 = pas de fichiers de logs, pas de rotation
            var fileLog = string.format(modules["cuve"]["logs"]["fileLogName"], modules["cuve"]["logs"]["nbLogsFiles"])

            # Compte le nombre de fichiers de logs présents
            self.indiceLog = gestionFileFolder.compteIndiceMaxFileLogs(fileLog)
            if (self.indiceLog == 0)    self.indiceLog = 1      end

            # Déclenche périodiquement /60s, l'enregistrement en logs
            tasmota.add_cron("*/60 * * * * *", /-> self.enregistreLogs(fileLog), "majLogCuve")
        end

        # Historique de la carte (data/fs/historiqueFonctions.be, demarre par autoexec.be) : le niveau
        # en erreur de mesure est enregistre comme absent, pas comme une fausse valeur
        if (diverses.find("historique", {}).find("activation", "OFF") == "ON")
            import historiqueFonctions
            historiqueFonctions.ajouteFiltre(/ chemins, valeurs -> self.filtreHistorique(chemins, valeurs))
        end

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
                        logFonctions.log("INIT_ADS1115: Voltage Max.: " + str(cuveFonctions.voltageMax), LOG_LEVEL_DEBUG, "cuve")

                        # Mets à jour les valeurs des capteurs
                        logFonctions.log("INIT_ADS1115: Enregistre les taches CRON !", LOG_LEVEL_DEBUG, "cuve")
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

    # Ruban en rouge clignotant tant que le capteur de niveau est en erreur de mesure
    def every_second()
        if (!self.flagINIT)    return    end
        import cuveFonctions
        cuveFonctions.majTemoinErreur()
    end

    # Page /cuve : jauges du volume et du taux (data/fs/cuvePageFonctions.be, importe a la premiere requete)
    def web_add_handler()
        import webserver
        webserver.on("/cuve", / -> self.pageCuve(), webserver.HTTP_GET)
    end

    def pageCuve()
        import cuvePageFonctions
        import cuveFonctions
        cuvePageFonctions.route(modules["cuve"].find("dimensions", {}), cuveFonctions.montageSonde())
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
        # En erreur de mesure (meme regle que la sentinelle ModBus), valeurs '-,--' : la derniere valeur
        # connue (souvent 0) ne doit pas passer pour une mesure
        variablesRemplacement = {}
        var erreurNiveau = cuveFonctions.niveauEnErreur()
        var vide = "-,--"
        if (modules["cuve"]["environnement"].find("analogiques", false))    # && cuveFonctions.sensorsCuve.find("niveauCuve", false))
            logFonctions.log("WEBSERVER_CUVE: Envoi a la page web de l'etat des capteurs !", LOG_LEVEL_DEBUG, "cuve")

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
                            # Tension brute (entree de l'ADS1115, apres le pont) et tension de la sonde recalculee
                            # (2026-10-31) : affichees meme en erreur de mesure, elles servent a la diagnostiquer
                            var tensions = cuveFonctions.sensorsCuve["valeursAnalogiques"]
                            variablesRemplacement.insert("sensorsCuve->valeurCapteurHauteur->titre", "Tension brute (ADS1115) : ")
                            variablesRemplacement.insert("sensorsCuve->valeursAnalogiques->valeurCapteurHauteur", str(tensions["valeurCapteurHauteur"]) + "mV")
                            variablesRemplacement.insert("sensorsCuve->tensionSonde->titre", "Tension sonde (recalculée) : ")
                            variablesRemplacement.insert("sensorsCuve->valeursAnalogiques->tensionSonde",
                                                         (tensions.contains("tensionSonde_V") ? string.format("%.2fV", tensions["tensionSonde_V"]) : vide + "V"))

                            variablesRemplacement.insert("sensorsCuve->hauteurEau->titre", "Hauteur Eau: ")
                            variablesRemplacement.insert("sensorsCuve->niveauCuve->hauteurEau", (erreurNiveau ? vide : str(cuveFonctions.sensorsCuve["niveauCuve"]["hauteurEau"])) + "cm")

                            cuveFonctions.log(string.format("CAPTEURS_CUVE: %s = %imV", anaJson["nom"], real(cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"])), LOG_LEVEL_DEBUG)
                        end
                    end
                end
            end

            # Calcul le pourcentage d'eau dans la cuve & le volume disponible
            variablesRemplacement.insert("sensorsCuve->tauxRemplissage->titre", "Taux de remplissage: ")
            variablesRemplacement.insert("sensorsCuve->niveauCuve->tauxRemplissage", (erreurNiveau ? vide : str(cuveFonctions.sensorsCuve["niveauCuve"]["tauxRemplissage"] * 100)) + "%")
            variablesRemplacement.insert("sensorsCuve->volume->titre", "Volume disponible: ")
            variablesRemplacement.insert("sensorsCuve->niveauCuve->volume", (erreurNiveau ? vide : str(cuveFonctions.sensorsCuve["niveauCuve"]["volume"])) + "L")

            # Couleur des bordures : celle du niveau sur le ruban, CALCULEE (et non relue sur le ruban,
            # pour qu'elle s'affiche aussi ruban eteint) ; rouge clignotant en erreur de mesure
            if (erreurNiveau)
                variablesRemplacement.insert("colorWs2812", "FF0000")
                variablesRemplacement.insert("classeErreur", "erreurCapteur")
            else
                var ws2812 = cuveFonctions.relaisRuban()
                var etat = (ws2812 != nil ? light.get(ws2812.find("channel", 0)) : nil)
                var sat = (etat != nil ? etat.find("sat", 255) : 255)
                variablesRemplacement.insert("colorWs2812", cuveFonctions.couleurTeinte(cuveFonctions.teinteNiveau(cuveFonctions.sensorsCuve["niveauCuve"]["tauxRemplissage"]), sat))
                variablesRemplacement.insert("classeErreur", "")
            end

            # Modifie le code html à afficher et l'envoi
            gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorNiveauCuve.html', variablesRemplacement, "web_send")
        end

        tasmota.yield()

        # Pour les thermometres
        if (modules["cuve"]["environnement"].find("thermometres", false))
            logFonctions.log("WEBSERVER_CUVE: Envoi a la page web de l'etat des thermometres !", LOG_LEVEL_DEBUG, "cuve")

            # Parcours les thermomètres
            for cle: modules["cuve"]["environnement"]["thermometres"].keys()
                var thermoJson = modules["cuve"]["environnement"]["thermometres"][cle]
                if type(thermoJson) != "instance"  continue    end

                if (thermoJson.find("activation", "OFF") == "ON")
                    var temperature = 0.00
                    var humidity = 0.00

                    # Récupère la valeur des thermomètres dans le json sensors
                    # DS18B20 : sonde absente des capteurs -> '-,--' (et non plus encadre absent)
                    if (thermoJson["type"] == 1312)
                        variablesRemplacement = {}
                        variablesRemplacement.insert("drivers2->nom", "Surveillance T°")

                        var sonde = self.lectureDS18B20(thermoJson)
                        var texte = vide
                        if (sonde != nil && sonde.find("Temperature") != nil)
                            temperature = real(sonde["Temperature"])
                            temperature = int(temperature * 10) / 10.0
                            texte = str(temperature)
                        end

                        # Ajoute à la page web
                        variablesRemplacement.insert("sensors->DS18B20->titre", thermoJson["nom"])
                        variablesRemplacement.insert("sensors->DS18B20->Temperature", texte + "°C")
                        cuveFonctions.log(string.format("CAPTEURS_CUVE: %s = %s°C", thermoJson["nom"], texte), LOG_LEVEL_DEBUG)

                        # Modifie le code html à afficher et l'envoi
                        gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorDS18B20.html', variablesRemplacement, "web_send")
                    # DHT22
                    elif (thermoJson["type"] == 1216)
                        variablesRemplacement = {}
                        variablesRemplacement.insert("drivers2->nom", "Surveillance T° & Humidité")

                        temperature = real(controleGeneral.lectureSensors()["AM2301"]["Temperature"])
                        temperature = int(temperature * 10) / 10.0

                        humidity = real(controleGeneral.lectureSensors()["AM2301"]["Humidity"])
                        humidity = int(humidity * 10) / 10.0

                        # Ajoute à la page web
                        variablesRemplacement.insert("sensors->AM2301->titre", thermoJson["nom"])
                        variablesRemplacement.insert("sensors->AM2301->titre2", string.replace(thermoJson["nom"], "T°", "Humidité"))
                        variablesRemplacement.insert("sensors->AM2301->Temperature", str(temperature) + "°C")		
                        variablesRemplacement.insert("sensors->AM2301->Humidity", str(humidity) + "%RH")	
                        cuveFonctions.log(string.format("CAPTEURS_CUVE: %s = %.1f°C / %.1f%%RH", thermoJson["nom"], temperature, humidity), LOG_LEVEL_DEBUG)

                        # Modifie le code html à afficher et l'envoi
                        gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorDHT22.html', variablesRemplacement, "web_send")
                    end
                end
            end
        end
    end

    # Mesure d'une sonde DS18B20 dans les capteurs Tasmota, ou nil. Le framework lui donne l'alias
    # 'DS18B20-<id>' (Ds18Alias, configModules.be) ; sans alias, une sonde seule s'appelle 'DS18B20'.
    def lectureDS18B20(thermoJson)
        var capteurs = controleGeneral.lectureSensors()
        var sonde = capteurs.find("DS18B20-" + str(thermoJson.find("id", 1)))
        if (sonde == nil)    sonde = capteurs.find("DS18B20")    end
        return (isinstance(sonde, map) ? sonde : nil)
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

    # Filtre de l'historique (historiqueFonctions.ajouteFiltre) : niveau en erreur de mesure
    # (cuveFonctions.niveauEnErreur, regle de la sentinelle ModBus) -> séries sensorsCuve.niveauCuve.* à nil
    def filtreHistorique(chemins, valeurs)
        import string
        import cuveFonctions

        if (!cuveFonctions.niveauEnErreur())    return    end
        for i: 0 .. size(chemins) - 1
            if (string.startswith(chemins[i], "sensorsCuve.niveauCuve."))    valeurs[i] = nil    end
        end
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
        var thermo = modules["cuve"]["environnement"].find("thermometres", {}).find("thermometre1")
        var sonde = (thermo != nil ? self.lectureDS18B20(thermo) : nil)
        if (sonde != nil && sonde.find("Temperature") != nil)
            temperatureCuve = real(sonde["Temperature"])
            temperatureCuve = int(temperatureCuve * 10) / 10.0
        else
            sonde = nil
        end

        tasmota.yield()

        # Ecrit les données
        var data = "{\"date\":\"" + tasmota.time_str(tasmota.rtc("local")) + 
                        "\",\"niveauCuve\":" + json.dump(cuveFonctions.sensorsCuve["niveauCuve"]) + 
                        (sonde != nil ? ",\"temperatureCuve\":" + str(temperatureCuve) : "") + "}"

        gestionFileFolder.enregistreLogs(fileChemin, self, data)
    end
end

# Active le Driver de controle global des modules
controleCuve = CAPTEURS_CUVE()
tasmota.add_driver(controleCuve)