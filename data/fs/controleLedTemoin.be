# clignote_led.be - Fait clignoter une led_temoin sur un GPIO Tasmota
# La configuration est lue depuis _persist.json > drivers > voletRoulants > VRs > VR1 > led_temoin.

# Accessible depuis la console ou un autre script via global.controleLedTemoin :
#   global.controleLedTemoin.demarre()
#   global.controleLedTemoin.arrete()
#   global.controleLedTemoin.stop() ; global.controleLedTemoin = nil

class CONTROLE_LED_TEMOIN
    # Variables d'instance
    var pin          # Numéro du GPIO physique
    var intervalle   # Durée ON/OFF en millisecondes
    var etat         # Etat courant de la LED (true = allumée)
    var actif        # Le clignotement est en cours
    var DEBUG

    var config_ok    # true si la config a été trouvée dans persist

    def init()
        import gpio

        self.pin        = 39
        self.intervalle = 500
        self.etat       = false
        self.actif      = false
        self.DEBUG      = nil
        self.config_ok  = self._charge_config()

        if self.config_ok
            gpio.pin_mode(self.pin, gpio.OUTPUT)
            gpio.digital_write(self.pin, 0)
            tasmota.add_driver(self)
        end
    end

    def stop()
        self.arrete()
        tasmota.remove_driver(self)
        log("CONTROLE_LED_TEMOIN: Driver déchargé", LOG_LEVEL_INFO)
    end

    def log(msg, levelDebug)
        if (self.DEBUG == nil)
            self.DEBUG = drivers["voletRoulants"].find("debug", "OFF")
        end

        if (self.DEBUG == "ON")
            log(msg, levelDebug)
        end
    end

    #- Recherche récursivement un objet 'led_temoin' (activation ON) dans un objet JSON.
       Parcourt jusqu'à 3 niveaux de profondeur pour couvrir les structures :
         environnement > led_temoin
         environnement > <groupe> > led_temoin
         environnement > <groupe> > <item> > led_temoin
       Retourne le premier objet led_temoin actif trouvé, ou nil. -#
    def _cherche_dans_env(env)
        if type(env) != 'instance' return nil end

        # Niveau 1 : led_temoin directement dans environnement
        var led = env.find("led_temoin")
        if led != nil && led.find("activation", "OFF") == "ON" return led end

        # Niveaux 2 et 3 : parcourt les groupes puis les items
        for cle_grp: env.keys()
            var grp = env[cle_grp]
            if type(grp) != 'instance' continue end

            # Niveau 2 : led_temoin dans le groupe
            led = grp.find("led_temoin")
            if led != nil && led.find("activation", "OFF") == "ON" return led end

            # Niveau 3 : led_temoin dans chaque item du groupe
            for cle_item: grp.keys()
                var item = grp[cle_item]
                if type(item) != 'instance' continue end

                led = item.find("led_temoin")
                if led != nil && led.find("activation", "OFF") == "ON" return led end
            end
        end

        return nil
    end

    #- Parcourt les sections 'drivers' et 'modules' de persist et retourne
       le premier objet led_temoin actif trouvé, ou nil si aucun. -#
    def _cherche_led_temoin()
        import persist
        import string

        for section_name: ["drivers", "modules"]
            var section = persist.find(section_name)
            if type(section) != 'instance' continue end

            for cle: section.keys()
                var entite = section[cle]
                if type(entite) != 'instance' continue end
                if entite.find("activation", "OFF") != "ON" continue end

                var env = entite.find("environnement")
                if type(env) != 'instance' continue end

                var led = self._cherche_dans_env(env)
                if led != nil
                    self.log(string.format("CONTROLE_LED_TEMOIN: led_temoin trouvée dans persist[%s][%s]", section_name, cle), LOG_LEVEL_DEBUG)
                    return led
                end
            end
        end

        return false
    end

    #- Retourne true si la config a été trouvée et chargée, false sinon. -#
    def _charge_config()
        import string

        var led_temoin = self._cherche_led_temoin()
        if !led_temoin
            log("CONTROLE_LED_TEMOIN: Aucun 'led_temoin' actif trouvé dans persist, driver non chargé", LOG_LEVEL_INFO)
            return false
        end

        if led_temoin.find("pin") != nil        self.pin        = led_temoin["pin"]        end
        if led_temoin.find("intervalle") != nil self.intervalle = led_temoin["intervalle"] end

        self.log(string.format("CONTROLE_LED_TEMOIN: Config chargée - GPIO%d, intervalle %dms", self.pin, self.intervalle), LOG_LEVEL_DEBUG)
        return true
    end

    def demarre()
        import gpio

        if !self.actif
            self.actif = true
            self._bascule()
        end
    end

    def arrete()
        import gpio

        self.actif = false
        gpio.digital_write(self.pin, 0)
        self.etat = false
    end

    def _bascule()
        import gpio

        if !self.actif return end
        self.etat = !self.etat
        gpio.digital_write(self.pin, self.etat ? 1 : 0)
        tasmota.set_timer(self.intervalle, /-> self._bascule())
    end
end

global.controleLedTemoin = CONTROLE_LED_TEMOIN()
if !global.controleLedTemoin.config_ok
    global.controleLedTemoin = nil
end
