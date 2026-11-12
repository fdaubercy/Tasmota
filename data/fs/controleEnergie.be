# Driver de la page /energie et du releve de consommation (2026-11-02) : la logique est dans energieFonctions.be.
# Toutes les 5 min : point de la courbe de puissance, et note du compteur si l'heure locale a change (une heure
# manquee est rattrapee au passage suivant), copie de la courbe en flash a chaque note. Calibrage verifie une minute apres le demarrage.
# Solidifiable, sur le modele de controleDiscovery : 'import' appelle controleEnergie_init(m), qui porte la garde d'activation.
#@ solidify:controleEnergie
var controleEnergie = module("controleEnergie")

class CONTROLE_ENERGIE : Driver
    var courbe      # puissance sur 24 h (bytes, voir energieFonctions.courbeVide)
    var relue       # courbe.bin relu : il faut l'heure valide, absente a l'init
    var cle         # heure locale de la derniere note

    def init()
        import energieFonctions
        self.courbe = energieFonctions.courbeVide()
        tasmota.add_cron("0 */5 * * * *", / -> self.cycle(), "energie_cycle")
        tasmota.add_rule("Time#Initialized", / -> self.cycle(), "energie_heure")
        tasmota.set_timer(60000, / -> self.calibrage(), "energie_calibrage")
    end

    def cycle()
        import energieFonctions
        try
            var rtc = tasmota.rtc()
            if (rtc["utc"] < energieFonctions.HEURE_VALIDE)    return    end
            var enregistre = energieFonctions.enregistre()     # OFF : rien n'est lu ni ecrit en flash
            if (enregistre && !self.relue)
                self.courbe = energieFonctions.lisCourbe(rtc["local"])
                self.relue = true
            end
            var mesure = energieFonctions.mesure()
            if (mesure == nil)    return    end
            energieFonctions.notePuissance(self.courbe, rtc["local"], mesure.find("Power"))
            var cle = rtc["local"] / 3600
            if (enregistre && cle != self.cle && energieFonctions.releve(mesure, rtc))
                self.cle = cle
                energieFonctions.sauveCourbe(self.courbe, rtc["local"])
            end
        except .. as erreur, message
            logFonctions.log("ENERGIE_ERREUR: Releve : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        end
    end

    def calibrage()
        import energieFonctions
        try
            energieFonctions.verifieCalibrage()
        except .. as erreur, message
            logFonctions.log("ENERGIE_ERREUR: Calibrage : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        end
    end

    def web_add_main_button()
        import webserver
        webserver.content_send("<style>table:has(td>button){border-spacing:0;margin:0 -5px;width:calc(100% + 10px)!important}</style><p></p><form action='/energie' method='get'><button>Énergie</button></form>")
    end

    def web_add_config_button()
        import webserver
        webserver.content_send("<p></p><form action='/energie' method='get'><input type='hidden' name='f' value='tarifs'><button>Tarifs de l'électricité</button></form>")
    end

    # Remplace la ligne « ADC1 Temperature » de Tasmota (masquee par WebSensor2 0 dans autoexec.bat) : son nom est fige en C
    def web_sensor()
        import json
        import string
        import webserver
        try
            var analog = json.load(tasmota.read_sensors()).find("ANALOG")
            var t = (isinstance(analog, map) ? analog.find("Temperature1") : nil)
            if (t != nil)
                webserver.content_send("{s}Température ambiante{m}" + string.replace(string.format("%.1f", t), ".", ",") + " °C{e}")
            end
        except .. as erreur, message
            logFonctions.log("ENERGIE_ERREUR: Temperature : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        end
    end

    def web_add_handler()
        import webserver
        import energieFonctions
        webserver.on("/energie", / -> energieFonctions.route(self.courbe), webserver.HTTP_GET)
        webserver.on("/energie", / -> energieFonctions.enregistrePrix(), webserver.HTTP_POST)
    end
end
controleEnergie.CONTROLE_ENERGIE = CONTROLE_ENERGIE

def controleEnergie_init(m)
    import global
    if (diverses.find("energie", {}).find("activation", "OFF") == "ON")
        var inst = m.CONTROLE_ENERGIE()
        global.controleEnergie = inst
        tasmota.add_driver(inst)
        inst.web_add_handler()
    end
    return m
end
controleEnergie.init = controleEnergie_init

return controleEnergie
