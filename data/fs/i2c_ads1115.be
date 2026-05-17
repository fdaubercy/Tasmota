#- NOTES Sur le module I2C ADS1115 à 4 entrées analogiques
-#

var i2c_ads1115

class I2C_ADS1115# : Driver
    # Variables
    var nbIOActivesJSON
    var adresseI2C
    var nbAnalogiquesADS1115

    def init(adresseI2C)
        import json
        import string
        import gestionFileFolder

        self.nbIOActivesJSON = nil
        self.adresseI2C = adresseI2C
        self.nbAnalogiquesADS1115 = 0

        if (self.adresseI2C == nil)  return  end

        # Enregistre ou Mets à jour en variable les capteurs activés dans un tableaus
        self.nbIOActivesJSON = json.load(gestionFileFolder.readFile("/json/nbIOActives.json"))

        # Compte le nombre de relais virtuels liés au module I2C 'i2c_mcp23017'
        # Gère la modification du fichier 'mcp23x.dat' pour les relais du MCP23017
        # Parcours les relais virtuels I2C
        var typeConnex
        var moduleConnex
        var jsonData

        for cleModule: modules.keys()
            tasmota.yield()

            if (type(modules[cleModule]) != "instance")   continue      end

            var analogiques = modules[cleModule]["environnement"].find("analogiques", false)
            var result = tasmota.cmd("I2CScan", boolMute)
            if (analogiques)
                # Si les connexions I2C sont activées dans le firmware et les ports I2C configurés
                if (result.contains("I2CScan"))
                    # Module ADS1115 connecté
                    if (analogiques && string.find(result["I2CScan"], string.format("0x%02X", self.adresseI2C)) > -1)
                        for cleANA: analogiques.keys()
                            if type(analogiques[cleANA]) != "instance"   continue    end
                            tasmota.yield()

                            # Si le capteur analogique est activé (réels + virtuels)
                            if (analogiques[cleANA].find("activation", "OFF") == "ON" && analogiques[cleANA].find("virtuel", "OFF") != "OFF")
                                if (analogiques[cleANA]["virtuel"] == "I2C_ADS1115")
                                        
                                    typeConnex = string.split(analogiques[cleANA]["virtuel"],"_")[0]
                                    moduleConnex = string.split(analogiques[cleANA]["virtuel"],"_")[1]

                                    self.nbAnalogiquesADS1115 += 1
                                end
                            end
                        end

                        if (drivers[typeConnex]["environnement"][moduleConnex]["activation"] == "ON")
                            # Active le Driver 13
                            var reponse = tasmota.cmd("I2CDriver", boolMute)["I2CDriver"]
                            if (string.find(reponse, "!13") > -1 || string.find(reponse, "13") == -1)
                                tasmota.cmd("I2CDriver13 ON", boolMute)
                            end

                            # Vérifie si on doit interdire l'affichage des valeurs de capteurs sur la page html
                            if (drivers[typeConnex]["environnement"][moduleConnex].find("affichageWebSensor", false))
                                tasmota.cmd(string.format("WebSensor12 %s", drivers[typeConnex]["environnement"][moduleConnex].find("affichageWebSensor", "ON")), boolMute)
                            end
                        end
                    end
                elif (result.contains("Command"))
                    if (result["Command"] == "Error")
                        log(string.format("I2C_ADS1115: Le bus I2C n'est pas activé dans le firmware ou les ports I2C ne sont pas configurés !"), LOG_LEVEL_ERREUR)
                    end
                end
            end
        end
    end
end
    
# Active le Driver de controle global des modules
if (controleGeneral.nbIOActivesJSON["analogiques"]["actives"]["nb"] > controleGeneral.nbIOActivesJSON["analogiques"]["reels"]["nb"])
    if (drivers["I2C"].find("activation", "OFF") == "ON")
        try
            if (drivers["I2C"]["environnement"]["ADS1115"].find("activation", "OFF") == "ON")
                i2c_ads1115 = I2C_ADS1115(drivers["I2C"]["environnement"]["ADS1115"]["adresseI2C"])
                tasmota.add_driver(i2c_ads1115)
                log("I2C_ADS1115: Driver I2C_ADS1115 activé !", LOG_LEVEL_DEBUG)
            end
        except .. as error, message
            import string
            log(string.format("I2C_ADS1115_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
        end
    end
end