#- *********************************************************************************************
 * controleCoprocesseur.be - Alerte « firmware du coprocesseur Wi-Fi pas a jour » des cartes P4 (2026-10-26)
 *
 * Sur le P4, le Wi-Fi passe par un coprocesseur ESP32-C6 (esp_hosted, en SDIO). Son firmware ne suit pas
 * celui du P4 : il se met a jour a part (commande HostedOta). Ce module le signale sur l'accueil web et
 * mene a la page /coprocesseur, d'ou la mise a jour se lance.
 *
 * Version VISEE = la bibliotheque esp_hosted compilee dans le firmware du P4 (champ "Host" de la commande
 * Hosted, xdrv_84_esp32_hosted.ino::CmndHosted) : le C6 doit avoir la meme. Le fichier sans numero de
 * version du serveur suit mal (2.12.6 quand l'hote est en 2.12.13, constate le 2026-10-26) : on vise
 * <url>/v<Host>/network_adapter_<MCU>.bin, et on demande TOUJOURS l'URL complete a HostedOta (la forme
 * courte la deduit d'OtaUrl).
 *
 * Deroule, au demarrage seulement (les deux versions ne changent qu'au redemarrage ; un HostedOta reussi
 * redemarre le P4) :
 *  1. 20 s apres le chargement : lecture locale de Hosted (relue toutes les 20 s, 6 fois au plus, tant que
 *     le C6 vaut 0.0.0). C6 a jour, ou carte sans coprocesseur : FIN, aucun acces reseau.
 *  2. C6 en retard : ligne d'alerte sur l'accueil, puis UNE requete au serveur ~3 min apres le demarrage
 *     (Wi-Fi stabilise) : les 512 premiers octets du fichier (Range), dont l'en-tete d'image
 *     (esp_app_desc_t, version a l'offset 0x30) prouve que la version est publiee. Echec reseau : nouvel
 *     essai toutes les heures, 6 essais au plus. Publiee : le fichier par defaut est lu une fois ensuite,
 *     pour signaler s'il est plus recent que l'hote (il faudrait alors recompiler le P4).
 *
 * Configuration dans le persist, bloc serveur.coprocesseur :
 *     {"activation": "ON", "url": "https://ota.tasmota.com/tasmota32/coprocessor", "mqtt": "ON"}
 * MQTT ("mqtt": "ON" ; absent = OFF) : tele/<serveur.mqtt.topic>/COPROCESSEUR, message RETENU, publie a chaque
 * changement d'etat (lecture locale, reponse du serveur, mise a jour lancee) et a chaque connexion au broker :
 *     {"MCU": "esp32c6", "Version": "2.6.6", "Attendue": "2.12.13", "AJour": false, "Publiee": true, "Lancee": false}
 * ("Publiee" : null tant que le serveur n'a pas repondu). Topic a part : le JSON SENSOR (Influx/Node-RED du Pi,
 * series de l'historique) n'est pas touche. Rien n'est publie pour une carte sans coprocesseur.
 * Page : /coprocesseur (GET : etat, POST : lance HostedOta). Gabarit /sd/html/coprocesseur.html, rempli par
 * son script a partir de window.COPRO. Logs : cible general. Banc : outils_docs/scripts_python/berry/banc_coprocesseur.py
********************************************************************************************* -#

#@ solidify:controleCoprocesseur
var controleCoprocesseur = module("controleCoprocesseur")

class COPROCESSEUR : Driver
    static URL_DEFAUT = "https://ota.tasmota.com/tasmota32/coprocessor"
    static ID_TIMER = "coprocesseur"
    static DELAI_LOCAL = 20000          # ms entre deux lectures de Hosted
    static DELAI_SERVEUR = 180000       # ms apres le demarrage avant la premiere requete
    static DELAI_ESSAI = 3600000        # ms entre deux essais vers le serveur
    static DELAI_DEFAUT = 10000         # ms avant la lecture du fichier par defaut
    static ESSAIS_MAX = 6

    var base                            # URL du dossier coprocessor, sans '/' final
    var etat                            # nil (pas lu), "absent", "inconnu", "aJour", "retard"
    var c6, hote, mcu                   # versions "2.6.6" / "2.12.13", puce "esp32c6"
    var publiee                         # nil (non verifiee), true, false
    var versionDefaut                   # version du fichier par defaut du serveur, nil si non lue
    var lectures, essais                # lectures de Hosted, requetes au serveur
    var lancee                          # HostedOta deja lance par la page
    var ligne                           # ligne d'accueil precalculee ("" = rien)
    var mqttActif                       # publication de l'etat sur tele/<topic>/COPROCESSEUR

    def init(config)
        var url = str(config.find("url", self.URL_DEFAUT))
        while (size(url) > 0 && url[-1] == "/")    url = url[0 .. -2]    end
        self.base = url
        self.lectures = 0
        self.essais = 0
        self.lancee = false
        self.ligne = ""
        self.mqttActif = (config.find("mqtt", "OFF") == "ON")
        tasmota.set_timer(self.DELAI_LOCAL, / -> self.verifieLocal(), self.ID_TIMER)
        # Message retenu republie a chaque (re)connexion : le broker a pu le perdre (redemarrage du Pi)
        if (self.mqttActif)    tasmota.add_rule("Mqtt#Connected", def (valeur, declencheur, message) self.publie() end, self.ID_TIMER)    end
    end

    # "2.12.13" -> 0x020C0D ; nil si ce n'est pas une version a 3 nombres (0..255)
    def versionEntier(texte)
        import string
        if (type(texte) != "string")    return nil    end
        var parties = string.split(texte, ".")
        if (size(parties) != 3)    return nil    end
        var r = 0
        for p: parties
            if (size(p) == 0 || size(p) > 3)    return nil    end
            for i: 0 .. size(p) - 1
                if (p[i] < "0" || p[i] > "9")    return nil    end
            end
            var n = int(p)
            if (n > 255)    return nil    end
            r = r * 256 + n
        end
        return r
    end

    # Version ecrite dans l'en-tete d'une image ESP-IDF (esp_app_desc_t a 0x20, nombre magique ABCD5432,
    # version sur 32 octets a 0x30) ; nil si l'en-tete n'en est pas un
    def versionImage(octets)
        if (!isinstance(octets, bytes) || size(octets) < 0x50)    return nil    end
        if (octets[0x20 .. 0x23] != bytes("3254CDAB"))    return nil    end
        var fin = 0x30
        while (fin < 0x50 && octets[fin] != 0)    fin += 1    end
        if (fin == 0x30)    return nil    end
        var texte = octets[0x30 .. fin - 1].asstring()
        return (self.versionEntier(texte) != nil ? texte : nil)
    end

    # Fichier du serveur : version donnee -> dossier v<version> ; nil -> fichier par defaut
    def urlFichier(version)
        var mcu = (self.mcu != nil ? self.mcu : "esp32c6")
        return self.base + (version != nil ? "/v" + version : "") + "/network_adapter_" + mcu + ".bin"
    end

    # 1. Lecture locale des versions
    def verifieLocal()
        import string
        var reponse = tasmota.cmd("Hosted", boolMute)
        var h = (isinstance(reponse, map) ? reponse.find("Hosted") : nil)
        if (!isinstance(h, map))
            self.etat = "absent"
            logFonctions.log("COPROCESSEUR: Pas de coprocesseur Wi-Fi (commande Hosted inconnue) !", LOG_LEVEL_DEBUG)
            return
        end
        self.c6 = str(h.find("Hosted", ""))
        self.hote = str(h.find("Host", ""))
        self.mcu = str(h.find("MCU", "esp32c6"))
        var vC6 = self.versionEntier(self.c6)
        var vHote = self.versionEntier(self.hote)
        self.lectures += 1

        if (vC6 == nil || vC6 == 0 || vHote == nil)
            self.etat = "inconnu"
            if (self.lectures < self.ESSAIS_MAX)
                tasmota.set_timer(self.DELAI_LOCAL, / -> self.verifieLocal(), self.ID_TIMER)
            else
                logFonctions.log(string.format("COPROCESSEUR_ERREUR: Version du coprocesseur illisible (C6 '%s', hote '%s') !", self.c6, self.hote), LOG_LEVEL_ERREUR)
            end
            return
        end

        if (vC6 >= vHote)
            self.etat = "aJour"
            logFonctions.log(string.format("COPROCESSEUR: Firmware du %s a jour (v%s) !", self.mcu, self.c6), LOG_LEVEL_INFO)
            self.publie()
            return
        end

        self.etat = "retard"
        self.majLigne()
        logFonctions.log(string.format("COPROCESSEUR: Firmware du %s en retard : v%s, v%s attendue par le firmware du P4 !", self.mcu, self.c6, self.hote), LOG_LEVEL_INFO)
        self.publie()
        var attente = self.DELAI_SERVEUR - tasmota.millis()
        tasmota.set_timer((attente > 1000 ? attente : 1000), / -> self.verifieServeur(), self.ID_TIMER)
    end

    # Requete des 512 premiers octets de 'url' : [code HTTP (negatif = echec reseau), version lue ou nil]
    def lisEnTete(url)
        var cl = webclient()
        var code = -1
        var version = nil
        try
            cl.set_timeouts(2000, 1500)         # reponse, connexion : sous USE_BERRY_TIMEOUT (4 s par callback)
            cl.begin(url)
            cl.add_header("Range", "bytes=0-511")
            code = cl.GET()
            if (code == 206)    version = self.versionImage(cl.get_bytes())    end    # 200 : Range ignore, corps NON lu (1,2 Mo)
        except .. as erreur, message
            logFonctions.log("COPROCESSEUR_ERREUR: Requete " + url + " : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
            code = -1
        end
        try    cl.close()    except .. end
        return [code, version]
    end

    # 2. Disponibilite de la version visee sur le serveur
    def verifieServeur()
        import string
        self.essais += 1
        var url = self.urlFichier(self.hote)
        var r = self.lisEnTete(url)
        if (r[0] == 200 || (r[0] == 206 && r[1] == self.hote))
            self.publiee = true
            logFonctions.log("COPROCESSEUR: Version v" + self.hote + " publiee : " + url + " !", LOG_LEVEL_INFO)
            tasmota.set_timer(self.DELAI_DEFAUT, / -> self.verifieDefaut(), self.ID_TIMER)
        elif (r[0] == 206)
            self.publiee = false
            logFonctions.log(string.format("COPROCESSEUR_ERREUR: %s contient la version '%s', pas v%s !", url, str(r[1]), self.hote), LOG_LEVEL_ERREUR)
        elif (r[0] == 404)
            self.publiee = false
            logFonctions.log("COPROCESSEUR: Version v" + self.hote + " pas encore publiee (" + url + ") !", LOG_LEVEL_INFO)
        else
            var suite = (self.essais < self.ESSAIS_MAX ? "nouvel essai dans 1 h" : "abandon jusqu'au prochain demarrage")
            logFonctions.log(string.format("COPROCESSEUR_ERREUR: Serveur injoignable (code %i, essai %i/%i), %s !", r[0], self.essais, self.ESSAIS_MAX, suite), LOG_LEVEL_ERREUR)
            if (self.essais < self.ESSAIS_MAX)
                tasmota.set_timer(self.DELAI_ESSAI, / -> self.verifieServeur(), self.ID_TIMER)
            end
        end
        self.majLigne()
        if (self.publiee != nil)    self.publie()    end
    end

    # Etat sur tele/<topic>/COPROCESSEUR (retenu) ; rien tant que les versions ne sont pas lues
    def publie()
        import mqtt
        import json
        if (!self.mqttActif || (self.etat != "aJour" && self.etat != "retard"))    return false    end
        var topic = (isinstance(serveur, map) ? serveur.find("mqtt", {}).find("topic", "") : "")
        if (topic == "" || !mqtt.connected())    return false    end
        var etat = {"MCU": self.mcu, "Version": self.c6, "Attendue": self.hote, "AJour": (self.etat == "aJour"),
                    "Publiee": self.publiee, "Lancee": self.lancee}
        try
            mqtt.publish("tele/" + topic + "/COPROCESSEUR", json.dump(etat), true)
        except .. as erreur, message
            logFonctions.log("COPROCESSEUR_ERREUR: Publication MQTT : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
            return false
        end
        logFonctions.log("COPROCESSEUR: Etat publie sur tele/" + topic + "/COPROCESSEUR !", LOG_LEVEL_DEBUG)
        return true
    end

    # Version du fichier par defaut, pour la page seulement (une lecture, sans nouvel essai)
    def verifieDefaut()
        var r = self.lisEnTete(self.urlFichier(nil))
        if (r[0] == 206 && r[1] != nil)
            self.versionDefaut = r[1]
            logFonctions.log("COPROCESSEUR: Fichier par defaut du serveur en v" + r[1] + " !", LOG_LEVEL_DEBUG)
        end
    end

    def majLigne()
        if (self.etat != "retard")
            self.ligne = ""
            return
        end
        var dispo = (self.publiee == true ? "disponible" : (self.publiee == false ? "pas encore publiée" : "disponibilité non vérifiée"))
        self.ligne = "{s}<a href='/coprocesseur' style='color:#f80;font-weight:bold'>&#9888; Wi-Fi " + self.mcu +
                     " à mettre à jour</a>{m}v" + self.c6 + " &rarr; v" + self.hote + " (" + dispo + "){e}"
    end

    def peutMettreAJour()
        return (self.etat == "retard" && self.publiee != false && !self.lancee)
    end

    # Rafraichissement de l'accueil (~2 s) : chaine precalculee, pas de log
    def web_sensor()
        if (size(self.ligne) > 0)    tasmota.web_send(self.ligne)    end
    end

    def web_add_handler()
        import webserver
        webserver.on("/coprocesseur", / -> self.page(), webserver.HTTP_GET)
        webserver.on("/coprocesseur", / -> self.lance(), webserver.HTTP_POST)
    end

    # Page /coprocesseur : donnees en window.COPRO, gabarit /sd/html/coprocesseur.html
    def page()
        import webserver
        import json
        import string
        import gestionFileFolder
        if (!webserver.check_privileged_access())    return nil    end
        var donnees = {"etat": self.etat, "mcu": self.mcu, "c6": self.c6, "hote": self.hote, "publiee": self.publiee,
                       "url": (self.hote != nil ? self.urlFichier(self.hote) : nil), "defaut": self.versionDefaut,
                       "possible": self.peutMettreAJour(), "lancee": self.lancee, "essais": self.essais}
        webserver.content_start("Coprocesseur Wi-Fi")
        webserver.content_send_style()
        webserver.content_send("<script>window.COPRO=" + string.replace(json.dump(donnees), "</", "<\\/") + ";</script>")
        gestionFileFolder.readFileByLineAndContentSend("/sd/html/coprocesseur.html")
        webserver.content_button(webserver.BUTTON_MAIN)
        webserver.content_stop()
    end

    # POST /coprocesseur : lance HostedOta sur l'URL complete de la version visee (rien n'est lu du navigateur)
    def lance()
        import webserver
        if (!webserver.check_privileged_access())    return nil    end
        if (self.peutMettreAJour())
            var url = self.urlFichier(self.hote)
            self.lancee = true
            logFonctions.log("COPROCESSEUR: Mise a jour lancee depuis la page web : HostedOta " + url + " !", LOG_LEVEL_INFO)
            tasmota.cmd("HostedOta " + url, boolMute)
            self.publie()
        else
            logFonctions.log("COPROCESSEUR: Mise a jour refusee (etat " + str(self.etat) + ", publiee " + str(self.publiee) + ", deja lancee " + str(self.lancee) + ") !", LOG_LEVEL_DEBUG)
        end
        self.page()
    end
end
controleCoprocesseur.COPROCESSEUR = COPROCESSEUR

# init() : APPELEE AUTOMATIQUEMENT par 'import controleCoprocesseur' (be_module.c, module_init), qui rend
# son resultat a la place du module. Garde d'activation : serveur.coprocesseur.activation == "ON", sinon nil.
def controleCoprocesseur_init(m)
    import global
    var config = (isinstance(serveur, map) ? serveur.find("coprocesseur", {}) : {})
    if (!isinstance(config, map) || config.find("activation", "OFF") != "ON")    return nil    end
    var inst = m.COPROCESSEUR(config)
    global.controleCoprocesseur = inst
    tasmota.add_driver(inst)
    inst.web_add_handler()
    return inst
end
controleCoprocesseur.init = controleCoprocesseur_init

return controleCoprocesseur
