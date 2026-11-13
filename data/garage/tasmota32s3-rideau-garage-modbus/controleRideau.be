# Solidifiable (2026-10-20), sur le modele de controleModbus : la classe est portee par le module
# 'controleRideau' ; autoexec le charge par 'import' (version en FLASH, env tasmota32s3-garage-rideau-garage-modbus).
# 'import' appelle AUTOMATIQUEMENT controleRideau_init(m), en pied de fichier, qui porte la garde d'activation.
#@ solidify:controleRideau
var controleRideau = module("controleRideau")

class CONTROLE_RIDEAU : Driver
	# Variables
    var flagINIT        # Flag marquant la fin de l'initialisation du module principal

    # Flags pour les logs à enregistrer
    var indiceLog
    var nbLogsFilesMax
    var fileLogSize_Ko

    var maitreMuet      # Facade : dernier etat du maitre (nil inconnu, true muet), pour ne loguer qu'au changement
    var essaiMaitre     # Facade : tasmota.millis() de la derniere requete au maitre (muet : une requete toutes les 10 s)
    var routePosee      # Facade : route /rideau deja declaree (init puis FUNC_WEB_ADD_HANDLER)
    var gpioEnPanne     # Facade : derniere lecture materielle d'un fin de course en echec, pour ne loguer qu'au changement

    # Squelette (2026-10-12) : la porte est pilotee par le driver voletRoulants DU MAITRE P4 ; celui de cette carte ne
    # tourne pas (vrFonctions et controleVoletRoulants exclus de son FS), son bloc du persist ne sert qu'a la facade.
    #
    # Facade (2026-11-12, plan tasks/plans/visuel-reglage-volets.md, A10) : la porte dessinee sur la page d'accueil, comme
    # sur le P4, par /sd/js/volets.js. Activee par drivers.voletRoulants.facade.activation "ON" ; volets dessines : ceux
    # du bloc qui portent un bloc 'facade' (type, place). Position : GET /rideau?f=position, que la page interroge a
    # chaque rafraichissement ; la carte la demande alors au maitre (Status 10, StatusSNS.Shutter<id>.Position, a
    # l'adresse serveur.rangeExtender.ipMaitre), JAMAIS sans page ouverte. Maitre muet : la position vient des fins de
    # course de CETTE carte (etat des interrupteurs designes par capteursPosition, celui que le maitre recoit par ModBus),
    # 100 ou 0, inconnue entre les deux ; la page grise alors le dessin.
    #
    # Fins de course (2026-11-13, plan tasks/plans/facade-garage-capteurs.md) : le bloc facade d'un volet peut porter
    # "finsDeCourse": {"module": "rideau", "ouverture": <id interrupteur>, "fermeture": <id>} ; window.VOLETS transmet alors
    # leurs NOMS, et la reponse de /rideau?f=position leur etat ("capteurs": {"ouverture", "fermeture"}, "ON" = contact
    # ferme). Etat lu sur la broche (gpio.digital_read, SwitchMode 1 ou 2 seulement), repli sur la cle 'etat' du persist.
    # "decor" de drivers.voletRoulants.facade est transmis tel quel (dessin de volets.js).
    def init()
        self.flagINIT = 0

        # Configuration du journal lue dans le persist (modules.rideau.logs), comme la cuve
        self.indiceLog = 0
        self.nbLogsFilesMax = modules["rideau"].find("logs", {}).find("nbLogsFiles", 0)
        self.fileLogSize_Ko = modules["rideau"].find("logs", {}).find("fileLogSize_Ko", 10000)

        self.web_add_handler()          # le serveur web peut deja tourner : FUNC_WEB_ADD_HANDLER ne viendrait plus
        logFonctions.log("CONTROLE_RIDEAU: Driver charge (squelette) !", LOG_LEVEL_DEBUG, "rideau")
        self.flagINIT = 1
    end

    def every_second()
    end

    # Volets a dessiner : [bloc du driver, liste des VRs actifs qui portent un bloc 'facade'], ou nil si la facade est inactive
    def facade()
        var vrs = drivers.find("voletRoulants", {})
        var f = vrs.find("facade")
        if (type(f) != "instance" || f.find("activation", "OFF") != "ON")    return nil    end
        var liste = []
        for vr: vrs.find("environnement", {}).find("VRs", {})
            if (type(vr) == "instance" && vr.find("activation", "OFF") == "ON" && type(vr.find("facade")) == "instance")    liste.push(vr)    end
        end
        return [f, liste]
    end

    # Ajout a la page d'accueil (forme de data/fs/vrPages.be::facade, plus 'source'). Une erreur ne casse jamais l'accueil.
    def web_add_main_button()
        var fa = self.facade()
        if (fa == nil || size(fa[1]) == 0)    return    end
        import webserver
        import json
        import string
        import gestionFileFolder
        var ouvert = false
        try
            var ouvertures = []
            for vr: fa[1]
                ouvertures.push({"id": vr.find("id"), "nom": vr.find("nom", "Volet"), "type": vr["facade"].find("type"),
                    "place": vr["facade"].find("place", 0), "inverse": vr.find("inverse", 1), "tempsMontee": vr.find("tempsMontee", 0),
                    "tempsDescente": vr.find("tempsDescente", 0), "inclinaison": nil, "source": "/rideau?f=position&id=" + str(vr.find("id")),
                    "finsDeCourse": self.nomsFins(vr["facade"].find("finsDeCourse"))})
            end
            var r = tasmota.cmd("WebRefresh", boolMute)
            var ms = (isinstance(r, map) ? r.find("WebRefresh") : nil)
            var v = {"toit": fa[0].find("toit", "aucun"), "rafraichissement": (type(ms) == "int" && ms > 0 ? ms : 2345), "ouvertures": ouvertures,
                     "decor": fa[0].find("decor")}
            webserver.content_send("<div id='vf'></div><script>window.VOLETS=" + string.replace(json.dump(v), "<", "\\u003c") + ";</script><script>")
            ouvert = true
            gestionFileFolder.readFileByLineAndContentSend("/sd/js/volets.js")
        except .. as erreur, message
            logFonctions.log("CONTROLE_RIDEAU_ERREUR: Facade : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "rideau")
        end
        if ouvert    webserver.content_send("</script>")    end
    end

    def web_add_handler()
        if (self.routePosee || self.facade() == nil)    return    end
        import webserver
        self.routePosee = true
        webserver.on("/rideau", / -> self.route(), webserver.HTTP_GET)
    end

    # GET /rideau?f=position&id=<n> -> {"ouverture": % ou null, "muet": true si le maitre n'a pas repondu}
    def route()
        import webserver
        import json
        if (!webserver.check_privileged_access())    return nil    end
        var id = (webserver.has_arg("id") ? int(webserver.arg("id")) : 0)
        var vr = nil
        var fa = self.facade()
        for v: (fa != nil ? fa[1] : [])
            if (v.find("id") == id)    vr = v    end
        end
        if (vr == nil || !webserver.has_arg("f") || webserver.arg("f") != "position")
            webserver.content_open(400, "application/json")
            webserver.content_send("{\"erreur\":\"f=position et id d'un volet de la facade attendus\"}")
            webserver.content_close()
            return
        end
        var p = self.positionMaitre(id)
        var rep = (p != nil ? {"ouverture": (vr.find("inverse", 1) == 1 ? 100 - p : p), "muet": false} : {"ouverture": self.positionCapteurs(vr), "muet": true})
        var fins = vr["facade"].find("finsDeCourse")
        if (type(fins) == "instance")    rep["capteurs"] = self.etatsFins(fins)    end
        webserver.content_open(200, "application/json")
        webserver.content_send(json.dump(rep))
        webserver.content_close()
    end

    # Position du volet 'id' lue chez le maitre (valeur du curseur : 100 - position si ShutterInvert), nil s'il ne repond pas
    def positionMaitre(id)
        import json
        import string
        var ip = str(serveur.find("rangeExtender", {}).find("ipMaitre", ""))
        if (size(string.split(ip, ".")) != 4)    return nil    end
        # Maitre muet : une requete toutes les 10 s, chacune bloque le serveur web jusqu'a 1,4 s (fins de course entre-temps)
        if (self.maitreMuet == true && self.essaiMaitre != nil && tasmota.millis() - self.essaiMaitre < 10000)    return nil    end
        self.essaiMaitre = tasmota.millis()
        var cl = webclient()
        var p = nil
        var cause = ""
        try
            cl.set_timeouts(800, 600)           # reponse, connexion : sous USE_BERRY_TIMEOUT (4 s par callback)
            cl.begin("http://" + ip + "/cm?cmnd=Status%2010")
            var code = cl.GET()
            if (code == 200)
                var sh = json.load(cl.get_string())
                sh = (isinstance(sh, map) ? sh.find("StatusSNS", {}).find("Shutter" + str(id)) : nil)
                p = (isinstance(sh, map) ? sh.find("Position") : nil)
                if (type(p) != "int")    p = nil    cause = "pas de Shutter" + str(id)    end
            else
                cause = "code " + str(code)
            end
        except .. as erreur, message
            cause = str(erreur) + " " + str(message)
        end
        try    cl.close()    except .. end
        var muet = (p == nil)
        if (muet != self.maitreMuet)        # une ligne par changement, pas une par rafraichissement de la page
            self.maitreMuet = muet
            if muet
                logFonctions.log("CONTROLE_RIDEAU_ERREUR: Position du maitre " + ip + " illisible (" + cause + "), fins de course de la carte !", LOG_LEVEL_ERREUR, "rideau")
            else
                logFonctions.log("CONTROLE_RIDEAU: Position lue chez le maitre " + ip + " !", LOG_LEVEL_INFO, "rideau")
            end
        end
        return p
    end

    # Repli : % d'ouverture d'apres les fins de course de la carte (100 ouvert, 0 ferme), nil entre les deux ou sans capteur.
    # Etat logique de l'interrupteur (cle 'etat', "ON" = en butee), celui que la carte envoie au maitre par ModBus.
    def positionCapteurs(vr)
        var cp = vr.find("capteursPosition", {})
        if (cp.find("activation", "OFF") != "ON")    return nil    end
        var ouvert = self.etatInterrupteur(cp.find("capteurOuvert")) == "ON"
        var ferme = self.etatInterrupteur(cp.find("capteurFerme")) == "ON"
        return (ouvert && !ferme ? 100 : (ferme && !ouvert ? 0 : nil))
    end

    # Etat ("ON"/"OFF") de l'interrupteur "Switch<n>" de modules.rideau, nil s'il n'existe pas
    def etatInterrupteur(nom)
        import string
        nom = str(nom)
        if (string.find(nom, "Switch") != 0)    return nil    end
        var n = int(nom[6..])
        for i: modules["rideau"].find("environnement", {}).find("interrupteurs", {})
            if (type(i) == "instance" && i.find("id") == n)    return i.find("etat")    end
        end
        return nil
    end

    # Interrupteur d'id fins[cle] dans modules[fins.module].environnement.interrupteurs, nil s'il n'existe pas
    def interrupteurFin(fins, cle)
        var m = modules.find(fins.find("module", ""))
        var liste = (type(m) == "instance" ? m.find("environnement", {}).find("interrupteurs") : nil)
        if (type(liste) != "instance" || fins.find(cle) == nil)    return nil    end
        for i: liste
            if (type(i) == "instance" && i.find("id") == fins[cle])    return i    end
        end
        return nil
    end

    # Bloc finsDeCourse -> {"ouverture": nom, "fermeture": nom} (nom nil si l'interrupteur manque), nil sans bloc
    def nomsFins(fins)
        if (type(fins) != "instance")    return nil    end
        var r = {}
        for cle: ["ouverture", "fermeture"]
            var i = self.interrupteurFin(fins, cle)
            r[cle] = (i != nil ? i.find("nom") : nil)
        end
        return r
    end

    # Etat "ON"/"OFF" de chaque fin de course (cle absente = inconnu), sens de la cle 'etat' : "ON" = contact ferme
    def etatsFins(fins)
        var r = {}
        for cle: ["ouverture", "fermeture"]
            var e = self.etatMateriel(self.interrupteurFin(fins, cle))
            if (e != nil)    r[cle] = e    end
        end
        return r
    end

    # Etat d'un interrupteur lu sur sa broche, comme Tasmota le calcule (support_switch_v4.ino::SwitchHandler) : SwitchMode 1
    # (FOLLOW) "ON" = broche haute, SwitchMode 2 (FOLLOW_INV) "ON" = broche basse (pull-up du type 160 : contact ferme a
    # la masse). Virtuel, sans broche, autre SwitchMode ou lecture en echec : cle 'etat' du persist (regle Switch<id>#Action).
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
                logFonctions.log("CONTROLE_RIDEAU_ERREUR: Broche " + str(pin) + " illisible (" + str(erreur) + " " + str(message) + "), etat du persist !", LOG_LEVEL_ERREUR, "rideau")
            end
            self.gpioEnPanne = true
            return e
        end
        if (type(n) != "int")    return e    end
        self.gpioEnPanne = false
        return ((n == 0) == (mode == 2) ? "ON" : "OFF")
    end

    def web_sensor()
        # Rien à afficher
    end

    # Ajoute les données des capteurs de rideau de garage à la réponse JSON
    def json_append()
        # Rien à ajouter
    end

    # Enregistre dans les logs les états du capteurs et relais de rideau de garage
    def enregistreLogs(fileChemin)
        # Rien à enregistrer
    end
end

# Publie la classe dans le module (solidification + import).
controleRideau.CONTROLE_RIDEAU = CONTROLE_RIDEAU

# init() : APPELEE AUTOMATIQUEMENT par 'import controleRideau' (be_module.c:285-296, module_init).
# Ne PAS la rappeler depuis autoexec. Driver enregistre seulement si le module rideau est active ;
# l'instance est publiee dans global.controleRideau.
def controleRideau_init(m)
    import global

    if (modules.find("rideau", {}).find("activation", "OFF") == "ON")
        global.controleRideau = m.CONTROLE_RIDEAU()
        tasmota.add_driver(global.controleRideau)
    end
    return m
end
controleRideau.init = controleRideau_init

# Valeur du module importe depuis le LittleFS (sans elle, import rend nil et init() n'est pas appelee)
return controleRideau
