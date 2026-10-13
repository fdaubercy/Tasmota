#- NOTES :
    - controleLeds.be — Le pilote (driver) de la LED RGB WS2812 du dev-kit ESP32-S3 (2026-10-11)
        * Enregistre le driver aupres de Tasmota, uniquement si drivers.leds est actif ET si
          drivers.leds.environnement.leds.ledRGB.activation == "ON" (garde en pied de fichier).
        * Toute la logique est dans le module partage 'ledsFonctions'.
        * every_second() : met a jour la LED (couleur imposee > erreur signalee > voyant d'etat).

    - Les autres modules s'en servent par 'import ledsFonctions' :
        * ledsFonctions.signaleErreur("<source>", true/false)   -> rouge clignotant
        * ledsFonctions.imposeCouleur("<source>", 0xRRGGBB, bri) -> couleur imposee (nil = rend la main)
-#

var controleLeds

class CONTROLE_LEDS : Driver
    def init()
        import ledsFonctions
        var led = ledsFonctions.config()
        logFonctions.log("CONTROLE_LEDS: Voyant RGB du dev-kit actif (GPIO" + (led != nil ? str(led["pin"]) : "?") + ") !", LOG_LEVEL_INFO, "leds")
    end

    def every_second()
        import ledsFonctions
        ledsFonctions.maj()
    end
end

# Active le driver seulement si la LED RGB est activee dans le persist
if (drivers.find("leds", {}).find("activation", "OFF") == "ON" &&
    drivers["leds"].find("environnement", {}).find("leds", {}).find("ledRGB", {}).find("activation", "OFF") == "ON")
    try
        controleLeds = CONTROLE_LEDS()
        tasmota.add_driver(controleLeds)
    except .. as error, message
        logFonctions.log("CONTROLE_LEDS_ERREUR: " + str(error) + " -> " + str(message), LOG_LEVEL_ERREUR, "leds")
    end
end
