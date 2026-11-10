# Driver du module metier debits : 6 debitmetres de la nourrice de chauffage ; la logique est dans debitsFonctions.be.
# Charge depuis le LittleFS par demarrage.chargeFichier("controleDebits", "modules.debits"), seulement
# si modules.debits.activation vaut "ON" ; debitsFonctions est compile avant.
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).

class CONTROLE_Debits : Driver
    var secondes        # secondes depuis la derniere mesure

    def init()
        import debitsFonctions
        self.secondes = 0
        # Un seul etalonnage par voie, le K du persist : FlowRateMeter en L/min, calibrage neutre (voir debitsFonctions)
        tasmota.cmd("Sensor96 0 0", boolMute)
        tasmota.cmd("Sensor96 1 1000", boolMute)
        tasmota.cmd("Sensor96 2 1000", boolMute)
        tasmota.add_cmd("ReglageDebits", debitsFonctions.reglageDebits)
        if (modules["debits"].find("modbus", "OFF") == "ON")    debitsFonctions.declareModbus()    end   # registres non frais avant la 1re mesure
        debitsFonctions.demarreEcran()
        debitsFonctions.log("CONTROLE_DEBITS: module debits charge, mesure toutes les " + str(debitsFonctions.fenetre()) + " s !", LOG_LEVEL_INFO)
    end

    # Mesure toutes les `fenetre` secondes (callback frequent : jamais de log info ici)
    def every_second()
        import debitsFonctions
        self.secondes += 1
        if (self.secondes < debitsFonctions.fenetre())    return    end
        self.secondes = 0
        try
            debitsFonctions.mesure()
        except .. as e, m
            debitsFonctions.log("CONTROLE_DEBITS_ERREUR: mesure impossible : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
        end
    end

    # Page /equilibrage : guide d'equilibrage et debits en direct (equilibragePage.be, importe a la premiere requete)
    def web_add_handler()
        import webserver
        webserver.on("/equilibrage", / -> self.pageEquilibrage(), webserver.HTTP_GET)
        webserver.on("/equilibrage", / -> self.enregistreEquilibrage(), webserver.HTTP_POST)
    end

    def pageEquilibrage()
        import equilibragePage
        equilibragePage.route()
    end

    # Reglages de l'estimateur de la page (puissances des radiateurs) gardes sur la carte
    def enregistreEquilibrage()
        import equilibragePage
        equilibragePage.enregistre()
    end

    def web_add_main_button()
        import webserver
        webserver.content_send("<p></p><form action='/equilibrage' method='get'><button>Équilibrage</button></form>")
    end

    # Lignes de la page d'accueil : un depart par ligne, debit et part du total
    def web_sensor()
        import debitsFonctions
        for l: debitsFonctions.lignesWeb()    tasmota.web_send(l)    end
    end

    # Telemetrie (JSON SENSOR) : bloc DEBITS
    def json_append()
        import debitsFonctions
        tasmota.response_append(debitsFonctions.json())
    end
end

# Active le driver du module
controleDebits = CONTROLE_Debits()
tasmota.add_driver(controleDebits)

# Valeur du fichier charge (controle P3.3 de banc_demarrage : un controleXxx.be finit par son return)
return controleDebits
