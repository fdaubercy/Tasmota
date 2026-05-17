#- NOTES Sur le module I2C MCP23017 à 16 sorties numériques
-#
var i2c_mcp23017

class I2C_MCP23017 : Driver
    # Variables
    var nbIOActivesJSON
    var adresseI2C
    var nbRelaisVirtuelsMCP23017

    def init(adresseI2C)
        import json
        import string
        import gestionFileFolder

        self.nbIOActivesJSON = nil
        self.adresseI2C = adresseI2C
        self.nbRelaisVirtuelsMCP23017 = 0

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
            var tabParam = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

            tasmota.yield()

            if (type(modules[cleModule]) != "instance")   continue      end

            var relais = modules[cleModule]["environnement"].find("relais", false)
            var result = tasmota.cmd("I2CScan", boolMute)
            if (relais)
                # Si les connexions I2C sont activées dans le firmware et les ports I2C configurés
                if (result.contains("I2CScan"))
                    # Module MCP23017 connecté
                    if (relais && string.find(result["I2CScan"]["I2CScan"], string.format("0x%02X", self.adresseI2C)) > -1)
                        for cleRLY: relais.keys()
                            if type(relais[cleRLY]) != "instance"   continue    end
                            tasmota.yield()

                            # Si le relai est activé (réels + virtuels)
                            if (relais[cleRLY].find("activation", "OFF") == "ON" && relais[cleRLY].find("virtuel", "OFF") != "OFF")
                                if (relais[cleRLY]["virtuel"] == "I2C_MCP23017")
                                    typeConnex = string.split(relais[cleRLY]["virtuel"],"_")[0]
                                    moduleConnex = string.split(relais[cleRLY]["virtuel"],"_")[1]

                                    self.nbRelaisVirtuelsMCP23017 += 1

                                    tabParam[relais[cleRLY]["id"] - 1] = relais[cleRLY]["type"] + relais[cleRLY]["id"] - 1
                                end
                            end
                        end

                        if (drivers[typeConnex]["environnement"][moduleConnex]["activation"] == "ON")
                            # Active le Driver 22
                            var reponse = tasmota.cmd("I2CDriver22", boolMute)["I2CDriver"]
                            if (string.find(reponse, "!22") > -1 || string.find(reponse, "22") == -1)
                                tasmota.cmd("I2CDriver22 ON", boolMute)
                            end
            
                            # Crée ou modifie le fichier 'mcp23x.dat' pour les relais
                            # ex: {"NAME":"MCP23017 A=Ri1-8, B=Ri9-16","GPIO":[256,257,258,259,260,261,262,263,264,265,266,267,268,269,270,271]}
                            jsonData = string.format('{"NAME":"%s","GPIO":%s}', drivers[typeConnex]["environnement"][moduleConnex]["name"], tabParam.tostring())
            
                            # Si cela a changé, on enregistre dans le fichier 'mcp23x.dat'
                            if (jsonData != gestionFileFolder.readFile("/mcp23x.dat"))
                                log(string.format("INIT_I2C_MCP23017: Modèle MCP23017=%s", jsonData), LOG_LEVEL_INFO)
                                gestionFileFolder.writeFile("/mcp23x.dat", jsonData)
            
                                # redémarrage
                                tasmota.cmd("Restart 1", boolMute)
                            end
                        end
                    end
                elif (result.contains("Command"))
                    if (result["Command"] == "Error")
                        log(string.format("INIT_I2C_MCP23017: Le bus I2C n'est pas activé dans le firmware ou les ports I2C ne sont pas configurés !"), LOG_LEVEL_ERREUR)
                    end
                end
            end
        end
    end
end

# Active le Driver de controle global des modules
if (controleGeneral.nbIOActivesJSON["relais"]["actives"]["nb"] > controleGeneral.nbIOActivesJSON["relais"]["reels"]["nb"])
    if (drivers["I2C"].find("activation", "OFF") == "ON")
        try
            if (drivers["I2C"]["environnement"]["MCP23017"].find("activation", "OFF") == "ON")
                i2c_mcp23017 = I2C_MCP23017(drivers["I2C"]["environnement"]["MCP23017"]["adresseI2C"])
                tasmota.add_driver(i2c_mcp23017)
                log("I2C_MCP23017: Driver I2C_MCP23017 activé !", LOG_LEVEL_DEBUG)
            end
        except .. as error, message
            import string
            log(string.format("I2C_MCP23017_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
        end
    end
end