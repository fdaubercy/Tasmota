#- NOTES Sur le module I2C ADS1115 à 4 entrées analogiques
    - Configurateur lancé une seule fois au démarrage : compte les entrées analogiques virtuelles
      'I2C_ADS1115', vérifie que le module répond sur le bus I2C, puis active le driver Tasmota 13
      (ADS1115) et règle l'affichage WebSensor12. Aucune tâche périodique.
    - Revu le 2026-09-27 avant solidification :
        * adresse comparée en minuscules : I2CScan répond "0x%02x" (support_a_i2c.ino:349) ;
          en majuscules, les adresses 0x4A/0x4B n'étaient jamais trouvées ;
        * I2CScan lancé une seule fois (il l'était pour CHAQUE module, avant même de savoir
          si le module avait des analogiques) ;
        * plus de 'drivers[nil]' quand aucune entrée ne vise l'ADS1115 (exception au boot) ;
        * '/json/nbIOActives.json' n'est plus rechargé : il n'était jamais lu ;
        * héritage ': Driver' rétabli (il était annulé par un '#').
-#
# Rendu solidifiable (2026-09-27), sur le modele de controleGeneral : la classe est portee
# par le module import-able 'i2c_ads1115'. autoexec le charge par 'import' (version en FLASH
# via load_native), plus par loadBerryFile (qui recompilait la classe en RAM).
# 'import' appelle AUTOMATIQUEMENT i2c_ads1115_init(m), en pied de fichier.
#@ solidify:i2c_ads1115
var i2c_ads1115 = module("i2c_ads1115")

class I2C_ADS1115 : Driver
    # Variables
    var adresseI2C
    var nbAnalogiquesADS1115

    def init(adresseI2C)
        import string

        self.adresseI2C = adresseI2C
        self.nbAnalogiquesADS1115 = 0

        if (self.adresseI2C == nil)  return  end

        # Compte les entrées analogiques activées et reliées virtuellement à l'ADS1115
        for cleModule: modules.keys()
            tasmota.yield()

            if (type(modules[cleModule]) != "instance")   continue      end

            var analogiques = modules[cleModule].find("environnement", {}).find("analogiques", false)
            if (!analogiques)   continue    end

            for cleANA: analogiques.keys()
                if type(analogiques[cleANA]) != "instance"   continue    end
                tasmota.yield()

                if (analogiques[cleANA].find("activation", "OFF") == "ON" && analogiques[cleANA].find("virtuel", "OFF") == "I2C_ADS1115")
                    self.nbAnalogiquesADS1115 += 1
                end
            end
        end

        if (self.nbAnalogiquesADS1115 == 0)
            log("I2C_ADS1115: Aucune entrée analogique activée sur l'ADS1115 !", LOG_LEVEL_DEBUG)
            return
        end

        # Vérifie une seule fois que l'ADS1115 répond sur le bus I2C
        var result = tasmota.cmd("I2CScan", boolMute)
        if (result == nil || !result.contains("I2CScan"))
            log("I2C_ADS1115: Le bus I2C n'est pas activé dans le firmware ou les ports I2C ne sont pas configurés !", LOG_LEVEL_ERREUR)
            return
        end

        # 'adresseI2C' vaut "0x48" dans le persist : string.format la convertit par int()
        var adresse = string.format("0x%02x", self.adresseI2C)
        if (string.find(result["I2CScan"], adresse) < 0)
            log(string.format("I2C_ADS1115: Module absent du bus I2C à l'adresse %s !", adresse), LOG_LEVEL_ERREUR)
            return
        end

        # Active le Driver 13 (ADS1115) s'il est désactivé ou absent de la liste
        var ads1115 = drivers["I2C"]["environnement"]["ADS1115"]
        var reponse = tasmota.cmd("I2CDriver", boolMute)["I2CDriver"]
        if (string.find(reponse, "!13") > -1 || string.find(reponse, "13") == -1)
            tasmota.cmd("I2CDriver13 ON", boolMute)
        end

        # Vérifie si on doit interdire l'affichage des valeurs de capteurs sur la page html
        if (ads1115.find("affichageWebSensor", false))
            tasmota.cmd(string.format("WebSensor12 %s", ads1115.find("affichageWebSensor", "ON")), boolMute)
        end

        log(string.format("I2C_ADS1115: %i entrée(s) analogique(s) sur le module %s !", self.nbAnalogiquesADS1115, adresse), LOG_LEVEL_DEBUG)
    end
end

# Publie la classe dans le module (solidification + import).
i2c_ads1115.I2C_ADS1115 = I2C_ADS1115

# init() : APPELEE AUTOMATIQUEMENT par 'import i2c_ads1115' (be_module.c:285-296, module_init).
# Ne PAS la rappeler depuis autoexec. Reprend le code d'activation de niveau fichier d'avant
# (gardes comprises) ; l'instance est publiee dans global.i2c_ads1115.
# Lit controleGeneral.nbIOActivesJSON : importer controleGeneral AVANT ce module.
def i2c_ads1115_init(m)
    import global

    var nbIO = controleGeneral.nbIOActivesJSON.find("analogiques", {})
    if (nbIO.find("actives", {}).find("nb", 0) > nbIO.find("reels", {}).find("nb", 0))
        if (drivers.find("I2C", {}).find("activation", "OFF") == "ON")
            try
                var ads1115 = drivers["I2C"].find("environnement", {}).find("ADS1115", {})
                if (ads1115.find("activation", "OFF") == "ON")
                    global.i2c_ads1115 = m.I2C_ADS1115(ads1115.find("adresseI2C"))
                    tasmota.add_driver(global.i2c_ads1115)
                    log("I2C_ADS1115: Driver I2C_ADS1115 activé !", LOG_LEVEL_DEBUG)
                end
            except .. as error, message
                import string
                log(string.format("I2C_ADS1115_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
            end
        end
    end
    return m
end
i2c_ads1115.init = i2c_ads1115_init
