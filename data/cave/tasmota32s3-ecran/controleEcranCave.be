# Driver de l'ecran 7B de la cave : ECRAN (interface HASPmota ecranCaveHaspmota, veille par ecranFonctions, affichage chaque seconde,
# A8 du 2026-11-13) et ABONNEMENTS MQTT de l'affichage (plan ecran-cave-vues-commandes, A6, 2026-11-12). Charge par
# demarrage.chargeFichier("controleEcranCave", "modules.ecranCave") ; ecranCaveFonctions est compile avant (autoexec) et importe ici.
# Topics lus dans le persist : modules.ecranCave.sources = {"cave": <topic du serveur>, "cuve": <topic de la cuve>} ; abonnements
# tele/<cave>/SENSOR, tele/<cave>/STATE, stat/<cave>/RESULT, stat/<cave>/STATUS10 et tele/<cuve>/SENSOR. A la connexion MQTT :
# `cmnd/<cave>/STATE` et `cmnd/<cave>/STATUS 10`, pour ne pas attendre la telemetrie. Reception reseau = callback frequent :
# aucun log info (les erreurs sont journalisees par ecranCaveFonctions.recoit).
class CONTROLE_ECRAN_CAVE : Driver
    var cave
    var echecs    # dernier message d'erreur par callback : une ligne par CHANGEMENT de message, pas une par tic

    # Journalise l'echec `e` `m` du callback `cle` seulement s'il differe du dernier (callbacks frequents : pas de spam)
    def echec(cle, texte, e, m)
        import ecranCaveFonctions
        var msg = str(e) + " " + str(m)
        if (self.echecs.find(cle) == msg)    return    end
        self.echecs[cle] = msg
        ecranCaveFonctions.log("CONTROLE_ECRAN_CAVE_ERREUR: " + texte + " : " + msg + " !", LOG_LEVEL_ERREUR)
    end

    # Callback `cle` revenu a la normale apres une erreur : une ligne debug, puis silence
    def retabli(cle, texte)
        import ecranCaveFonctions
        if (!self.echecs.contains(cle))    return    end
        self.echecs.remove(cle)
        ecranCaveFonctions.log("CONTROLE_ECRAN_CAVE: " + texte + " retabli !", LOG_LEVEL_DEBUG)
    end

    def init()
        import mqtt
        import ecranFonctions
        import ecranCaveFonctions
        self.echecs = {}
        # Ecran d'abord (veille, reglages lus dans modules.ecranCave) : l'interface HASPmota est la seule sur le FS (cenv)
        ecranFonctions.bloc = "ecranCave"
        try
            ecranFonctions.demarre(ecranFonctions.charge(["ecranCaveHaspmota"]))
        except .. as e, m
            ecranCaveFonctions.log("CONTROLE_ECRAN_CAVE_ERREUR: interface non chargee : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
        end
        var cfg = modules.find("ecranCave")
        var src = (type(cfg) == "instance") ? cfg.find("sources") : nil
        if (type(src) != "instance" || type(src.find("cave")) != "string" || type(src.find("cuve")) != "string")
            ecranCaveFonctions.log("ECRAN_CAVE_ERREUR: modules.ecranCave.sources (cave, cuve) absent du persist : affichage MQTT inactif !", LOG_LEVEL_ERREUR)
            return
        end
        self.cave = src["cave"]
        self.abonne("cave", "tele/" + self.cave + "/SENSOR")
        self.abonne("cave", "tele/" + self.cave + "/STATE")
        self.abonne("cave", "stat/" + self.cave + "/RESULT")
        self.abonne("cave", "stat/" + self.cave + "/STATUS10")
        self.abonne("cuve", "tele/" + src["cuve"] + "/SENSOR")
        tasmota.add_rule("Mqtt#Connected", /-> self.demande(), "ecran_cave_mqtt")
        if (mqtt.connected())    self.demande()    end
    end

    def abonne(source, topic)
        import mqtt
        import ecranCaveFonctions
        mqtt.subscribe(topic, def (t, i, s, b) ecranCaveFonctions.recoit(source, t, s) return true end)
    end

    # Veille et luminosite (callback frequent : jamais de log info ici) ; I2C ecrit aux seuls changements d'etat
    def every_250ms()
        import ecranFonctions
        try
            ecranFonctions.suitVeille()
            self.retabli("veille", "suivi de la veille")
        except .. as e, m
            self.echec("veille", "veille non suivie", e, m)
        end
    end

    # Rafraichit l'ecran chaque seconde (callback frequent : jamais de log info ici) ; l'interface n'ecrit que ce qui a change
    def every_second()
        import ecranFonctions
        import ecranCaveFonctions
        if (ecranFonctions.interface == nil)    return    end
        try
            ecranFonctions.interface.affiche(ecranCaveFonctions.modele())
            self.retabli("ecran", "rafraichissement de l'ecran")
        except .. as e, m
            self.echec("ecran", "ecran non rafraichi", e, m)
        end
    end

    # Etat de la cave sans attendre sa telemetrie
    def demande()
        import mqtt
        mqtt.publish("cmnd/" + self.cave + "/STATE", "")
        mqtt.publish("cmnd/" + self.cave + "/STATUS", "10")
    end
end

controleEcranCave = CONTROLE_ECRAN_CAVE()
tasmota.add_driver(controleEcranCave)

# Valeur du fichier charge (controle P3.3 de banc_demarrage : un controleXxx.be finit par son return)
return controleEcranCave
