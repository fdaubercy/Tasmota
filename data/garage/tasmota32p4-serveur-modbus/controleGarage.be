var controleGarage

class CONTROLE_GARAGE : Driver
	# Variables
	var flagINIT        # Flag marquant la fin de l'initialisation du module principal

    # Flags pour les logs à enregistrer
    var indiceLog
    var nbLogsFilesMax
    var fileLogSize_Ko

    def init()
        import garageFonctions
        import json
        import gestionFileFolder
        import string

        self.flagINIT = 0

        # Flags pour les logs à enregistrer
        self.indiceLog = 0
        self.nbLogsFilesMax = modules["garage"]["logs"]["nbLogsFiles"]
        self.fileLogSize_Ko = modules["garage"]["logs"]["fileLogSize_Ko"]

        garageFonctions.log("CONTROLE_GARAGE: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Vérifie si des logs doivent être crées
        if (modules["garage"].find("logs", {}).find("nbLogsFiles", 0) != nil || modules["garage"].find("logs", {}).find("nbLogsFiles", 0) > 0)
            var fileLog = string.format(modules["garage"]["logs"]["fileLogName"], modules["garage"]["logs"]["nbLogsFiles"])

            # Compte le nombre de fichiers de logs présents
            self.indiceLog = gestionFileFolder.compteIndiceMaxFileLogs(fileLog)
            if (self.indiceLog == 0)    self.indiceLog = 1      end

            # Déclenche périodiquement /60s, l'enregistrement en logs
            tasmota.add_cron("*/60 * * * * *", /-> controleGarage.enregistreLogs(fileLog), "majLogGarage")
        end

        #-         
            Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
            - Message log sur connexion wifi
            - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
            - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        -#
        # tasmota.add_rule("Wifi", def(value, trigger, msg) garageFonctions.changementEtatDemarrage(value, trigger, msg) end)
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) garageFonctions.changementEtatDemarrage(value, trigger, msg) end)  
        # tasmota.add_rule("System", def(value, trigger, msg) garageFonctions.changementEtatDemarrage(value, trigger, msg) end) 

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

        # Active ou désactive le driver correspondant / Paramètre l'affichage sur page html du capteur
        # Il y a des entrées analogiques actives mais pas d'entrées analogiques réelles
        # Les règles des entrées analogiques réelles sont gérées par le module général
        tasmota.yield()
        
        # Ajoute les commandes personnalisées si le module est activé
        tasmota.add_cmd('ReglageGarage', garageFonctions.reglageGarage)

        # Marqueur de fin d'initialisation du module principal
        self.flagINIT = 1 
    end

    # Affiche les capteurs du module cuve sur la page web
    def web_sensor()
        import json
        import string
        import persist
        import garageFonctions
        import gestionFileFolder

        var variablesRemplacement

        tasmota.yield()

        # Affiche sur la page web le capteur de niveau de cuve 
        gestionFileFolder.readFileByLineAndContentSend("/sd/css/webSensor.css", "", "web_send")

        # Pour les entrées analogiques
        variablesRemplacement = {}
        if (modules["garage"]["environnement"].find("analogiques", false))
            garageFonctions.log("WEBSERVER_GARAGE: Envoi a la page web de l'etat des capteurs !", LOG_LEVEL_DEBUG)

            # Parcours les entrées analogiques
            variablesRemplacement.insert("drivers->nom", modules["garage"]["environnement"]["analogiques"]["name"])
            for cle: modules["garage"]["environnement"]["analogiques"].keys()
                var anaJson = modules["garage"]["environnement"]["analogiques"][cle]
                if type(anaJson) != "instance"  continue    end

                tasmota.yield()

                # Pour les entrées analogiques virtuelles de type ADS1115
                if (anaJson.find("activation", "OFF") == "ON" && anaJson.find("virtuel", "OFF") != "OFF")
                    if (string.find(anaJson["virtuel"], "ModBus_TasmotaSlaveModBus") > -1)
                        # Ajoute à la page web
                        if (anaJson["idModBus"] == 1)
                            variablesRemplacement.insert("sensorsCuve->valeurCapteurHauteur->titre", anaJson["nom"])

                            var value = tasmota.scale_int(int(anaJson["value"]), 0, 32767, 0, 6144)
                            variablesRemplacement.insert("sensorsCuve->valeursAnalogiques->valeurCapteurHauteur", str(value) + "mV")

                            # Convertit la valeur (en V) vers une valeur en cm
                            # Coefficient de conversion: 30mV/cm
                            variablesRemplacement.insert("sensorsCuve->hauteurEau->titre", "Hauteur Eau: ")

                            var hauteurEau = value / anaJson.find("conversion_mV_cm", 1.0)
                            variablesRemplacement.insert("sensorsCuve->niveauCuve->hauteurEau", str(hauteurEau) + "cm")

                            garageFonctions.log(string.format("WEBSERVER_GARAGE: %s = %imV", anaJson["nom"], real(value)), LOG_LEVEL_INFO)

                            # Calcul le pourcentage d'eau dans la cuve & le volume disponible
                            var hauteur = anaJson.find("dimensions", {}).find("hauteur", 100)    # en cm
                            var largeur = anaJson.find("dimensions", {}).find("largeur", 100)    # en cm
                            var longueur = anaJson.find("dimensions", {}).find("longueur", 100)    # en cm

                            var pourcentageEau = int(hauteurEau / real(hauteur) * 100) / 100.00 

                            variablesRemplacement.insert("sensorsCuve->tauxRemplissage->titre", "Taux de remplissage: ")
                            variablesRemplacement.insert("sensorsCuve->niveauCuve->tauxRemplissage", str(pourcentageEau * 100) + "%")

                            var volume =  int(hauteur * largeur * longueur * pourcentageEau / 1000)    # en litres

                            variablesRemplacement.insert("sensorsCuve->volume->titre", "Volume disponible: ")	
                            variablesRemplacement.insert("sensorsCuve->niveauCuve->volume", str(volume) + "L")	

                            # Change la couleur des bordures en fonction du niveau de remplissage
                            # en récupérant les valurs de couleur RGB du ruban LED WS2812 en json
                            if (light.get(0)["rgb"] != "1A1A1A")
                                variablesRemplacement.insert("colorWs2812", light.get(0)["rgb"])
                            else
                                variablesRemplacement.insert("colorWs2812", "eaeaea")
                            end
                        end
                    end
                end
            end

            # Modifie le code html à afficher et l'envoi
            gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorNiveauCuve.html', variablesRemplacement, "web_send")
        end

        tasmota.yield()

        # Pour les thermometres
        if (modules["garage"]["environnement"].find("thermometres", false))
            garageFonctions.log("WEBSERVER_GARAGE: Envoi a la page web de l'etat des thermometres !", LOG_LEVEL_DEBUG)

            # Parcours les thermomètres
            for cle: modules["garage"]["environnement"]["thermometres"].keys()
                var thermoJson = modules["garage"]["environnement"]["thermometres"][cle]
                if type(thermoJson) != "instance"  continue    end

                tasmota.yield()

                if (thermoJson.find("activation", "OFF") == "ON")
                    var temperature = 0.00
                    var humidity = 0.00

                    # Récupère la valeur des thermomètres dans le json sensors
                    # DS18B20
                    if (thermoJson["type"] == 1312)
                        variablesRemplacement = {}
                        variablesRemplacement.insert("drivers2->nom", "Surveillance T°")

                        temperature = real(thermoJson["value"])
                        temperature = int(temperature * 10) / 10.0

                        # Ajoute à la page web
                        variablesRemplacement.insert("sensors->DS18B20->titre", thermoJson["nom"])
                        variablesRemplacement.insert("sensors->DS18B20->Temperature", str(temperature) + "°C")	
                        garageFonctions.log(string.format("CAPTEURS_GARAGE: %s = %.2f°C", thermoJson["nom"], temperature), LOG_LEVEL_INFO)

                        # Modifie le code html à afficher et l'envoi
                        gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorDS18B20.html', variablesRemplacement, "web_send")
                    # DHT22
                    elif (thermoJson["type"] == 1216)
                        variablesRemplacement = {}
                        variablesRemplacement.insert("drivers2->nom", "Surveillance T° & Humidité")

                        temperature = real(thermoJson["value"])
                        temperature = int(temperature * 10) / 10.0

                        humidity = real(thermoJson["value"])
                        humidity = int(humidity * 10) / 10.0

                        # Ajoute à la page web
                        variablesRemplacement.insert("sensors->AM2301->titre", thermoJson["nom"])
                        variablesRemplacement.insert("sensors->AM2301->titre2", string.replace(thermoJson["nom"], "T°", "Humidité"))
                        variablesRemplacement.insert("sensors->AM2301->Temperature", str(temperature) + "°C")		
                        variablesRemplacement.insert("sensors->AM2301->Humidity", str(humidity) + "%RH")	
                        garageFonctions.log(string.format("CAPTEURS_GARAGE: %s = %.1f°C / %.1f%%RH", thermoJson["nom"], temperature, humidity), LOG_LEVEL_INFO)

                        # Modifie le code html à afficher et l'envoi
                        gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorDHT22.html', variablesRemplacement, "web_send")
                    end
                end
            end
        end

        # Pour les compteurs
        if (modules["garage"]["environnement"].find("compteurs", false))
            garageFonctions.log("WEBSERVER_GARAGE: Envoi a la page web de l'etat des compteurs !", LOG_LEVEL_DEBUG)

            # Parcours les compteurs
            for cle: modules["garage"]["environnement"]["compteurs"].keys()
                var comptJson = modules["garage"]["environnement"]["compteurs"][cle]
                if type(comptJson) != "instance"  continue    end

                tasmota.yield()

                if (comptJson.find("activation", "OFF") == "ON")
                    var compteur = 0

                    variablesRemplacement = {}
                    variablesRemplacement.insert("drivers1->nom", "Etat des compteurs")

                    
                    compteur = real(json.load(tasmota.read_sensors())["COUNTER"]["C1"] / 1000.00)    # En kWh
                    # compteur = real(comptJson["value"] / 1000.00)    # En kWh

                    # Ajoute à la page web
                    variablesRemplacement.insert("sensors->compteur->titre", comptJson["nom"])
                    variablesRemplacement.insert("sensors->compteur->Consommation", str(compteur) + "kWh")
                    garageFonctions.log(string.format("CAPTEURS_GARAGE: %s = %.2fkWh", comptJson["nom"], compteur), LOG_LEVEL_INFO)

                    # Modifie le code html à afficher et l'envoi
                    gestionFileFolder.readFileByLineReplaceAndWebSend('/sd/html/webSensorCompteurElec.html', variablesRemplacement, "web_send")
                end
            end
        end
    end

    # Ajoute les données de cuve à la réponse JSON
    def json_append()
        import garageFonctions
        import json
        import string

        # Pour les thermometres virtuels
        if (modules["garage"]["environnement"].find("thermometres", false))
            # Ajoute à la réponse JSON
            # Parcours les thermomètres
            for cle: modules["garage"]["environnement"]["thermometres"].keys()
                var thermoJson = modules["garage"]["environnement"]["thermometres"][cle]
                if type(thermoJson) != "instance"  continue    end

                tasmota.yield()

                if (thermoJson.find("activation", "OFF") == "ON" && thermoJson.find("virtuel", "OFF") != "OFF")
                    var temperature = 0.00
                    var humidity = 0.00

                    # Récupère la valeur des thermomètres dans le json sensors
                    # DS18B20
                    if (thermoJson["type"] == 1312)
                        # "DS18B20":{"Id":"041600F6FBFF","Temperature":22.7}
                        tasmota.response_append(string.format(", \"DS18B20\": {\"id\": \"%s\", \"Temperature\": %.1f}", thermoJson["serialNumber"], real(thermoJson["value"])))
                    end
                end
            end
        end

        tasmota.yield()

        # Pour les entrées analogiques virtuels
        if (modules["garage"]["environnement"].find("analogiques", false))
            # Ajoute à la réponse JSON
            # Parcours les entrées analogiques
            for cle: modules["garage"]["environnement"]["analogiques"].keys()
                var anaJson = modules["garage"]["environnement"]["analogiques"][cle]
                if type(anaJson) != "instance"  continue    end

                tasmota.yield()

                if (anaJson.find("activation", "OFF") == "ON" && anaJson.find("virtuel", "OFF") != "OFF")
                    # Pour les entrées analogiques virtuelles de type ADS1115
                    if (string.find(anaJson["virtuel"], "ModBus_TasmotaSlaveModBus") > -1)
                        if (anaJson["idModBus"] == 1)
                            # "sensorsCuve": {"valeursAnalogiques":{"valeurCapteurHauteur":616},"niveauCuve":{"tauxRemplissage":0.17,"hauteurEau":19,"volume":1144}}
                            var value = tasmota.scale_int(int(anaJson["value"]), 0, 32767, 0, 6144)
                            var hauteurEau = value / anaJson.find("conversion_mV_cm", 1.0)

                            # Calcul le pourcentage d'eau dans la cuve & le volume disponible
                            var hauteur = anaJson.find("dimensions", {}).find("hauteur", 100)    # en cm
                            var largeur = anaJson.find("dimensions", {}).find("largeur", 100)    # en cm
                            var longueur = anaJson.find("dimensions", {}).find("longueur", 100)    # en cm

                            var pourcentageEau = int(hauteurEau / real(hauteur) * 100) / 100.00 

                            var volume =  int(hauteur * largeur * longueur * pourcentageEau / 1000)    # en litres

                            tasmota.response_append(string.format(", \"sensorsCuve\": {\"valeursAnalogiques\": {\"valeurCapteurHauteur\": %i}, \"niveauCuve\":{\"tauxRemplissage\": %.2f, \"hauteurEau\": %i, \"volume\": %i}}", 
                                                                                tasmota.scale_int(int(anaJson["value"]), 0, 32767, 0, 6144), real(pourcentageEau), int(hauteurEau), volume))
                        end
                    end
                end
            end
        end
    end

    # Enregistre dans les logs les données du garage
    def enregistreLogs(fileChemin)
        import json
        import string
        import introspect
        import gestionFileFolder
        import garageFonctions

        garageFonctions.log("ENREGISTRE_LOGS_GARAGE: Enregistrement des données de garage en logs !", LOG_LEVEL_DEBUG_PLUS)

        tasmota.yield()

        # Ecrit les données sous format json
        var data = "{\"date\":\"" + tasmota.time_str(tasmota.rtc("local")) + "\"}"

        gestionFileFolder.enregistreLogs(fileChemin, self, data)
    end
end

# Active le Driver de controle global des modules
controleGarage = CONTROLE_GARAGE()
tasmota.add_driver(controleGarage)