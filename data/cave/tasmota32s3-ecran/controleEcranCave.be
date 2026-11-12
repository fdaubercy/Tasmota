# Driver de l'ecran 7B de la cave : ABONNEMENTS MQTT de l'affichage (plan ecran-cave-vues-commandes, A6, 2026-11-12). Charge par
# demarrage.chargeFichier("controleEcranCave", "modules.ecranCave") ; ecranCaveFonctions est compile avant (autoexec) et importe ici.
# Topics lus dans le persist : modules.ecranCave.sources = {"cave": <topic du serveur>, "cuve": <topic de la cuve>} ; abonnements
# tele/<cave>/SENSOR, tele/<cave>/STATE, stat/<cave>/RESULT, stat/<cave>/STATUS10 et tele/<cuve>/SENSOR. A la connexion MQTT :
# `cmnd/<cave>/STATE` et `cmnd/<cave>/STATUS 10`, pour ne pas attendre la telemetrie. Reception reseau = callback frequent :
# aucun log info (les erreurs sont journalisees par ecranCaveFonctions.recoit).
class CONTROLE_ECRAN_CAVE : Driver
    var cave

    def init()
        import mqtt
        import ecranCaveFonctions
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
