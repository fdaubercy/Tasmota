# Solidifiable, sur le modele de controleRideau : la classe est portee par le module 'controlePortail' ; autoexec le charge par 'import'
# (version en FLASH, env tasmota32s3-garage-portail-jardin-modbus). 'import' appelle AUTOMATIQUEMENT controlePortail_init(m), en pied de
# fichier, qui porte la garde d'activation.
#@ solidify:controlePortail
var controlePortail = module("controlePortail")

class CONTROLE_PORTAIL : Driver
    # Page d'accueil de l'esclave 4 (plan tasks/plans/facade-garage-portail-commande.md, A8) : le portail dessine seul par
    # /sd/js/volets.js (decor 'portailSeul'), avec son capteur de fermeture. Cette carte N'EST PAS pilotee depuis sa page : le maitre P4
    # lui envoie les ordres (Shutters du P4 -> relais virtuels -> ModBus -> relais reels de 1 s), la page est en lecture seule.
    # Activee par modules.portail.facade.activation "ON". Cles de modules.portail.facade :
    #   "decor"   : liste transmise a volets.js (defaut ["portailSeul", "finition"] : ni mur ni toit, avec la nuit)
    #   "capteur" : id de l'interrupteur de fermeture dans modules.portail.environnement.interrupteurs (defaut 1)
    # Contact ferme (ON) = portail ferme (0 %) ; contact non ferme (OFF) = portail grand ouvert (100 %), sans capteur d'ouverture.
    # Position : GET /portail?f=position, que la page interroge a chaque rafraichissement (jamais sans page ouverte).
    var routePosee      # route /portail deja declaree (init puis FUNC_WEB_ADD_HANDLER)
    var gpioEnPanne     # derniere lecture materielle du contact en echec, pour ne loguer qu'au changement

    def init()
        logFonctions.declare("portail", "modules.portail", "portail de jardin (controlePortail)")    # cible de log du binome (plan binomes-berry A4)
        self.web_add_handler()          # le serveur web peut deja tourner : FUNC_WEB_ADD_HANDLER ne viendrait plus
        logFonctions.log("CONTROLE_PORTAIL: Driver charge !", LOG_LEVEL_DEBUG, "portail")
    end

    def every_second()
    end

    # Bloc facade du module (instance) ou nil si la facade est inactive
    def facade()
        var f = modules.find("portail", {}).find("facade")
        if (type(f) != "instance" || f.find("activation", "OFF") != "ON")    return nil    end
        return f
    end

    # Interrupteur de fermeture : celui d'id facade.capteur (defaut 1) dans modules.portail.environnement.interrupteurs, nil s'il manque
    def interrupteur(f)
        var id = f.find("capteur", 1)
        for i: modules["portail"].find("environnement", {}).find("interrupteurs", {})
            if (type(i) == "instance" && i.find("id") == id)    return i    end
        end
        return nil
    end

    # Ajout a la page d'accueil (forme de controleRideau::web_add_main_button). Une erreur ne casse jamais l'accueil.
    def web_add_main_button()
        var f = self.facade()
        if (f == nil)    return    end
        import webserver
        import json
        import string
        import gestionFileFolder
        var ouvert = false
        try
            var r = tasmota.cmd("WebRefresh", boolMute)
            var ms = (isinstance(r, map) ? r.find("WebRefresh") : nil)
            var ouvertures = [{"id": 1, "nom": "Portail", "type": "portail2", "place": 1, "inverse": 0, "tempsMontee": 0, "tempsDescente": 0,
                "inclinaison": nil, "source": "/portail?f=position"}]
            var v = {"toit": "unPan", "rafraichissement": (type(ms) == "int" && ms > 0 ? ms : 2345), "ouvertures": ouvertures,
                     "decor": f.find("decor", ["portailSeul", "finition"]), "lectureSeule": true}
            webserver.content_send("<div id='vf'></div><script>window.VOLETS=" + string.replace(json.dump(v), "<", "\\u003c") + ";</script><script>")
            ouvert = true
            gestionFileFolder.readFileByLineAndContentSend("/sd/js/volets.js")
        except .. as erreur, message
            logFonctions.log("CONTROLE_PORTAIL_ERREUR: Facade : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "portail")
        end
        if ouvert    webserver.content_send("</script>")    end
    end

    def web_add_handler()
        if (self.routePosee || self.facade() == nil)    return    end
        import webserver
        self.routePosee = true
        webserver.on("/portail", / -> self.route(), webserver.HTTP_GET)
    end

    # GET /portail?f=position -> {"ouverture": 0 (ferme), 100 (non ferme) ou null (contact illisible), "muet": false, "capteurs": {"fermeture": "ON"|"OFF"}}
    def route()
        import webserver
        import json
        if (!webserver.check_privileged_access())    return nil    end
        var f = self.facade()
        if (f == nil || !webserver.has_arg("f") || webserver.arg("f") != "position")
            webserver.content_open(400, "application/json")
            webserver.content_send("{\"erreur\":\"f=position attendu\"}")
            webserver.content_close()
            return
        end
        var etat = self.etatMateriel(self.interrupteur(f))
        var rep = {"ouverture": (etat == "ON" ? 0 : (etat == "OFF" ? 100 : nil)), "muet": false}
        if (etat != nil)    rep["capteurs"] = {"fermeture": etat}    end
        webserver.content_open(200, "application/json")
        webserver.content_send(json.dump(rep))
        webserver.content_close()
    end

    # Etat du contact lu sur sa broche, comme Tasmota le calcule (support_switch_v4.ino::SwitchHandler) : SwitchMode 1 (FOLLOW) "ON" =
    # broche haute, SwitchMode 2 (FOLLOW_INV) "ON" = broche basse (pull-up du type 160 : contact ferme a la masse). Virtuel, sans
    # broche, autre SwitchMode ou lecture en echec : cle 'etat' du persist (regle Switch<id>#Action).
    def etatMateriel(i)
        if (i == nil)    return nil    end
        var e = i.find("etat")
        e = (e == "ON" || e == "OFF" ? e : nil)
        var mode = i.find("SwitchMode", 1)
        var pin = i.find("pin", -1)
        if (i.find("virtuel", "OFF") != "OFF" || type(pin) != "int" || pin < 0 || (mode != 1 && mode != 2))    return e    end
        var n = nil
        try
            import gpio
            n = gpio.digital_read(pin)
        except .. as erreur, message
            if (!self.gpioEnPanne)          # une ligne par panne, pas une par rafraichissement de la page
                logFonctions.log("CONTROLE_PORTAIL_ERREUR: Broche " + str(pin) + " illisible (" + str(erreur) + " " + str(message) + "), etat du persist !", LOG_LEVEL_ERREUR, "portail")
            end
            self.gpioEnPanne = true
            return e
        end
        if (type(n) != "int")    return e    end
        self.gpioEnPanne = false
        return ((n == 0) == (mode == 2) ? "ON" : "OFF")
    end

    def web_sensor()
        # Rien a afficher
    end

    def json_append()
        # Rien a ajouter
    end
end

# Publie la classe dans le module (solidification + import).
controlePortail.CONTROLE_PORTAIL = CONTROLE_PORTAIL

# init() : APPELEE AUTOMATIQUEMENT par 'import controlePortail'. Ne PAS la rappeler depuis autoexec. Driver enregistre seulement
# si le module portail est active ; l'instance est publiee dans global.controlePortail.
def controlePortail_init(m)
    import global

    if (modules.find("portail", {}).find("activation", "OFF") == "ON")
        global.controlePortail = m.CONTROLE_PORTAIL()
        tasmota.add_driver(global.controlePortail)
    end
    return m
end
controlePortail.init = controlePortail_init

# Valeur du module importe depuis le LittleFS (sans elle, import rend nil et init() n'est pas appelee)
return controlePortail
