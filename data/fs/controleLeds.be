#- NOTES :
    - controleLeds.be — Le pilote (driver) des LED de la carte (2026-10-11, ruban 2026-10-13)
        * Enregistre le driver aupres de Tasmota, uniquement si drivers.leds est actif ET si la LED RGB
          du dev-kit (drivers.leds.environnement.leds.ledRGB) ou le ruban (...leds.ruban) est active
          (garde en pied de fichier).
        * Toute la logique est dans le module partage 'ledsFonctions'.
        * every_second() : ruban (fin du MANUEL, couleur changee hors bouton, clignotement d'erreur),
          puis LED du dev-kit (couleur imposee > erreur signalee > voyant d'etat).
        * Ruban actif : regle 'Button<bouton>#Action' (id 'ledsRuban'), commande ReglageLeds,
          pastille d'aide sur le bouton du ruban et ligne d'etat sur la page d'accueil.

    - Les autres modules s'en servent par 'import ledsFonctions' :
        * ledsFonctions.signaleErreur("<source>", true/false)   -> rouge clignotant
        * ledsFonctions.imposeCouleur("<source>", 0xRRGGBB, bri) -> couleur imposee (nil = rend la main)
        * ledsFonctions.appliqueAuto(teinte)                     -> couleur du mode AUTO du ruban
        * ledsFonctions.enregistreRetourAuto(fonction, texte)    -> repose la couleur au retour en AUTO
-#

var controleLeds

class CONTROLE_LEDS : Driver
    def init()
        import string
        import ledsFonctions
        var led = ledsFonctions.config()
        if (led != nil)    logFonctions.log("CONTROLE_LEDS: Voyant RGB du dev-kit actif (GPIO" + str(led["pin"]) + ") !", LOG_LEVEL_INFO, "leds")    end

        var ruban = ledsFonctions.configRuban()
        if (ruban != nil)
            var bouton = int(ruban.find("bouton", 0))
            if (bouton > 0)
                ledsFonctions.regleBouton()
                tasmota.add_rule(string.format("Button%i#Action", bouton), def(value, trigger, msg)
                    import ledsFonctions
                    ledsFonctions.actionBouton(value)
                end, "ledsRuban")
            end
            tasmota.add_cmd('ReglageLeds', ledsFonctions.reglageLeds)
            logFonctions.log(string.format("CONTROLE_LEDS: Ruban en mode AUTO, bouton %s !", (bouton > 0 ? "Button" + str(bouton) : "absent")), LOG_LEVEL_INFO, "leds")
        end
    end

    def every_second()
        import ledsFonctions
        ledsFonctions.maj()
    end

    # Pastille d'aide dans le coin du bouton du ruban
    def web_add_main_button()
        import webserver
        import ledsFonctions
        if (ledsFonctions.configRuban() == nil)    return    end
        webserver.content_send(ledsFonctions.scriptAideWeb())
    end

    # Ligne d'etat du ruban ; son bouton 'Auto' revient ici par la requete de rafraichissement (?m=1&ldAuto=1)
    def web_sensor()
        import webserver
        import ledsFonctions
        if (ledsFonctions.configRuban() == nil || ledsFonctions.relaisRuban() == nil)    return    end
        if (webserver.has_arg("ldAuto"))    ledsFonctions.retourAuto("page web")    end
        tasmota.web_send(ledsFonctions.ligneWeb())
    end
end

# Active le driver seulement si la LED RGB ou le ruban est active dans le persist
if (drivers.find("leds", {}).find("activation", "OFF") == "ON" &&
    (drivers["leds"].find("environnement", {}).find("leds", {}).find("ledRGB", {}).find("activation", "OFF") == "ON" ||
     drivers["leds"].find("environnement", {}).find("leds", {}).find("ruban", {}).find("activation", "OFF") == "ON"))
    try
        controleLeds = CONTROLE_LEDS()
        tasmota.add_driver(controleLeds)
    except .. as error, message
        logFonctions.log("CONTROLE_LEDS_ERREUR: " + str(error) + " -> " + str(message), LOG_LEVEL_ERREUR, "leds")
    end
end
