# Affiche sur la page principale de Tasmota l'etat de la pompe vide-cave et des
# capteurs de niveau (bas/haut) : derniere mise en route, nb de cycles du jour,
# intervalle de fonctionnement moyen, etat brut des Switch associes.
#
# Migre 'afficheSensorPompeCave()' (webFonctions.be) + 'web_sensor()' (gestionWeb.be)
# de l'ancien module (tasmota32-serveur-rly-sauvegarde) vers le framework actuel :
#  - persist a plat ('modules', pas 'parametres.modules')
#  - capteurs de niveau ranges sous 'capteurs' (pas 'capteursPosition'), type+id separes
#  - 'diversFonctions.afficheDateTime()' ne formate plus que l'heure courante (elle ne
#    prend plus de timestamp en parametre) -> formatage local du timestamp stocke ici.

import string

# Formate un timestamp epoch en 'HHhMM'.
def affiche_heure(timestamp)
    if (timestamp == 0)    return "jamais"    end

    var time_dump = tasmota.time_dump(timestamp)
    var heure = (time_dump["hour"] < 10 ? "0" + str(time_dump["hour"]) : str(time_dump["hour"]))
    var minute = (time_dump["min"] < 10 ? "0" + str(time_dump["min"]) : str(time_dump["min"]))

    return heure + "h" + minute
end

class CONTROLE_POMPE_VIDE_CAVE : Driver
    # Pannes des flotteurs (persist pompeVideCave.pannes = {"antiRebond": s, "maxArretsMinuterie": n}, sans la cle : rien)
    #  - incoherence : haut ON et bas OFF depuis plus de antiRebond s (physiquement impossible)
    #  - flotteurBas : n arrets de suite par la minuterie (duree >= timer - 1 s) alors que le haut est OFF et le bas encore ON ;
    #    remis a 0 par un arret avec le bas OFF ; rien n'est compte pendant une marche manuelle (flotteurs suspendus)
    # Alerte sur la voie de controleGeneral::publieAlerteRelance (topicAlerte, relai["alerte"], effacee par AcquittePompe).
    var debutIncoh, alerteIncoh, arrets, etatPrec, manuelPrec

    def init()
        self.debutIncoh = 0
        self.alerteIncoh = false
        self.arrets = 0
        self.etatPrec = "OFF"
        self.manuelPrec = false
    end

    # ON tant qu'un flotteur est suspendu par une marche manuelle
    def manuel(capteurs)
        for cleCapteur: capteurs.keys()
            if (type(capteurs[cleCapteur]) == "instance" && capteurs[cleCapteur].find("suspendu", "OFF") == "ON")    return true    end
        end
        return false
    end

    def leveAlerte(relai, evenement, message)
        relai["alerte"] = message
        logFonctions.log("POMPE_VIDE_CAVE_ERREUR: " + message, LOG_LEVEL_ERREUR)
        controleGeneral.publieAlerteRelance("pompeVideCave", relai, evenement, message, 0, relai.find("relance", {}).find("maxRelances", 3))
    end

    def every_second()
        var pompe = modules["pompeVideCave"]
        var pannes = pompe.find("pannes", false)
        if (!pannes || pompe.find("activation", "OFF") != "ON")    return    end

        var relai = pompe["environnement"]["relais"]["relai1"]
        var capteurs = pompe["environnement"]["capteurs"]
        var sensors = controleGeneral.lectureSensors()
        var bas = sensors.find("Switch" + str(capteurs["capteur1"]["id"]), "?")
        var haut = sensors.find("Switch" + str(capteurs[relai["relance"]["capteur"]]["id"]), "?")
        var maintenant = tasmota.rtc()["local"]
        var etat = relai.find("etat", "OFF")

        if (bas == "OFF" && haut == "ON")
            if (self.debutIncoh == 0)
                self.debutIncoh = maintenant
            elif (!self.alerteIncoh && maintenant - self.debutIncoh >= pannes.find("antiRebond", 5))
                self.alerteIncoh = true
                self.leveAlerte(relai, "incoherence", "Incoherence des flotteurs : niveau haut actif alors que le niveau bas est inactif. Verifier les capteurs.")
            end
        else
            self.debutIncoh = 0
            self.alerteIncoh = false
        end

        if (self.etatPrec == "ON" && etat == "OFF" && !self.manuelPrec)
            var timer = relai.find("timer", 0)
            if (bas == "OFF")
                self.arrets = 0
            elif (haut == "OFF" && timer > 0 && relai["timestamp"]["OFF"] - relai["timestamp"]["ON"] >= timer - 1)
                self.arrets += 1
                var max = pannes.find("maxArretsMinuterie", 3)
                var message = "Pompe arretee par la minuterie alors que le niveau bas reste actif : probable defaut du capteur de niveau bas (ou pompe inefficace)."
                if (self.arrets == max)
                    self.leveAlerte(relai, "flotteurBas", message)
                elif (self.arrets > max)
                    relai["alerte"] = message       # controleGeneral::finTimerRelai l'a effacee a cet arret : elle reste tant que ca dure
                end
            end
        end
        # memorise pendant la marche : a l'arret, controleGeneral a deja reactive les flotteurs
        if (etat == "ON")    self.manuelPrec = self.manuel(capteurs)    end
        self.etatPrec = etat
    end

    # Etat lu par l'ecran de la cave (SENSOR) : "PompeVideCave": {"Pompe", "Manuel", "Niveaux": {"Bas", "Haut"}, "Alerte"}
    def json_append()
        import json
        var pompe = modules["pompeVideCave"]
        if (pompe.find("activation", "OFF") != "ON")    return    end
        var relai = pompe["environnement"]["relais"]["relai1"]
        var capteurs = pompe["environnement"]["capteurs"]
        var sensors = controleGeneral.lectureSensors()
        var haut = capteurs.find(relai.find("relance", {}).find("capteur", "capteur2"), {})
        tasmota.response_append(string.format(',"PompeVideCave":{"Pompe":"%s","Manuel":"%s","Niveaux":{"Bas":"%s","Haut":"%s"},"Alerte":%s}',
            relai.find("etat", "OFF"), self.manuel(capteurs) ? "ON" : "OFF",
            sensors.find("Switch" + str(capteurs["capteur1"]["id"]), "?"), sensors.find("Switch" + str(haut.find("id", 0)), "?"),
            json.dump(relai.find("alerte", ""))))
    end

    def web_sensor()
        var pompe = modules["pompeVideCave"]

        if (pompe.find("activation", "OFF") != "ON")    return    end

        var relai = pompe["environnement"]["relais"]["relai1"]
        var capteurs = pompe["environnement"]["capteurs"]
        var horodatage = relai["timestamp"]
        var maintenant = tasmota.rtc()["local"]

        # Etat de la pompe + temps restant avant l'arret de securite (timer du relai)
        var etatPompe = relai.find("etat", "OFF")
        var textePompe = etatPompe
        if (etatPompe == "ON" && relai.find("timer", 0) != 0 && horodatage.find("ON", 0) != 0)
            var reste = horodatage["ON"] + relai["timer"] - maintenant
            if (reste < 0)    reste = 0    end
            textePompe += string.format(" (arret de securite dans %is)", reste)
        end

        # Relance de securite en cours (niveau haut encore actif apres l'arret du timer)
        var nbRelances = controleGeneral.relances.find("pompeVideCave_" + str(relai["id"]), 0)
        if (nbRelances > 0)
            textePompe += string.format(" - relance %i/%i", nbRelances, relai.find("relance", {}).find("maxRelances", 3))
        end

        # Compteur remis a zero au changement de jour par controleGeneral, a la mise en route
        # suivante : tant qu'il n'y en a pas eu aujourd'hui, la valeur stockee est celle d'hier.
        var nbCycles = horodatage.find("nbCyclesJour", 0)
        if (horodatage.find("jourCycles", -1) != maintenant / 86400)    nbCycles = 0    end

        var msg = "<table style='width:100%'>" +
                    "<fieldset>" +
                        "<style>" +
                            "div, fieldset, input, select{padding:3px;}" +
                            "fieldset{border-radius:0.3rem;}" +
                            ".parametre{border-radius:0.3rem;padding:1px;display:flex;flex-direction:row;}" +
                            ".titreSwitch{width:40%;text-align:right;padding-top:9px;}" +
                            ".btnSwitch{width:20%;height:35px;font-size:0.9rem;font-weight:bold;background-color:#1fa3ec63;}" +
                        "</style>" +
                        "<legend><b title='sensorPompe'>" + pompe.find("name", "Pompe Vide-Cave") + "</b></legend>" +
                        # Alerte levee par controleGeneral apres le nombre max de relances (acquittee
                        # automatiquement au premier arret avec le niveau haut retombe)
                        (relai.find("alerte", "") != "" ?
                            "<div style='color:#fff;background:#d43535;border-radius:0.3rem;padding:4px;margin-bottom:4px;'><b>&#9888; " +
                            relai["alerte"] + "</b></div>" : "") +
                        "<div class='parametre'>" +
                            "<div>Pompe: </div>" +
                            "<div><b>" + textePompe + "</b></div>" +
                        "</div>" +
                        "<div class='parametre'>" +
                            "<div>Derniere mise en route: </div>" +
                            "<div>" + affiche_heure(horodatage.find("ON", 0)) + "</div>" +
                        "</div>" +
                        "<div class='parametre'>" +
                            "<div>Nb. de cycles du jour: </div>" +
                            "<div>" + str(nbCycles) + "</div>" +
                        "</div>" +
                        "<div class='parametre'>" +
                            # 'delai' = ecart entre les 2 dernieres mises en route (pas une moyenne)
                            "<div>Intervalle depuis la mise en route precedente: </div>" +
                            "<div>" + str(int(horodatage.find("delai", 0) / 60)) + "min</div>" +
                        "</div>"

        var sensors = controleGeneral.lectureSensors()      # Lecture a la demande (cache 1 s)
        for cleCapteur: capteurs.keys()
            if (type(capteurs[cleCapteur]) != "instance")    continue    end
            if (capteurs[cleCapteur].find("activation", "OFF") != "ON")    continue    end

            msg += "<div class='parametre'>" +
                        "<div class='titreSwitch'>" + capteurs[cleCapteur].find("nom", cleCapteur) + " :</div>" +
                        "<button class='btnSwitch'>" + sensors.find("Switch" + str(capteurs[cleCapteur]["id"]), "?") + "</button>" +
                    "</div>"
        end

        msg += "</fieldset></table>"

        tasmota.web_send(msg)
    end

    # Etat complet de la pompe, pour la commande 'EtatPompe' (lue par Node-RED -> Telegram)
    def etat()
        var pompe = modules["pompeVideCave"]
        var relai = pompe["environnement"]["relais"]["relai1"]
        var horodatage = relai["timestamp"]
        var maintenant = tasmota.rtc()["local"]
        var sensors = controleGeneral.lectureSensors()

        var reste = 0
        if (relai.find("etat", "OFF") == "ON" && relai.find("timer", 0) != 0 && horodatage.find("ON", 0) != 0)
            reste = horodatage["ON"] + relai["timer"] - maintenant
            if (reste < 0)    reste = 0    end
        end

        var niveaux = {}
        var capteurs = pompe["environnement"]["capteurs"]
        for cleCapteur: capteurs.keys()
            if (type(capteurs[cleCapteur]) != "instance" || capteurs[cleCapteur].find("activation", "OFF") != "ON")    continue    end
            niveaux[capteurs[cleCapteur].find("nom", cleCapteur)] = sensors.find("Switch" + str(capteurs[cleCapteur]["id"]), "?")
        end

        return {
            "Pompe": relai.find("etat", "OFF"),
            "ArretSecuriteDans": reste,
            "Relance": controleGeneral.relances.find("pompeVideCave_" + str(relai["id"]), 0),
            "MaxRelances": relai.find("relance", {}).find("maxRelances", 3),
            "Niveaux": niveaux,
            "DerniereMiseEnRoute": affiche_heure(horodatage.find("ON", 0)),
            "CyclesJour": (horodatage.find("jourCycles", -1) == maintenant / 86400 ? horodatage.find("nbCyclesJour", 0) : 0),
            "Alerte": relai.find("alerte", "")
        }
    end

    # Efface l'alerte et le compteur de relances (commande 'AcquittePompe')
    def acquitte()
        var relai = modules["pompeVideCave"]["environnement"]["relais"]["relai1"]
        controleGeneral.acquitteRelance("pompeVideCave", relai)
        relai["alerte"] = ""
        self.arrets = 0
    end
end

# Active le Driver uniquement si le module 'pompeVideCave' est active
# 'global.' explicite : l'affectation d'un nom non declare dans un bloc 'if' est refusee en
# mode strict ("strict: no global ..."), et loadBerryFile compile ce fichier en contexte LOCAL
# (tasmota.compile) ou meme le niveau fichier ne cree plus de globale.
if (modules["pompeVideCave"].find("activation", "OFF") == "ON")
    import global
    global.controlePompeVideCave = CONTROLE_POMPE_VIDE_CAVE()
    tasmota.add_driver(global.controlePompeVideCave)

    # Commandes Tasmota (console, HTTP, MQTT cmnd/<topic>/...) : reponse sur stat/<topic>/RESULT
    #   EtatPompe      -> {"EtatPompe": {"Pompe": "ON", "Niveaux": {...}, "Alerte": "", ...}}
    #   AcquittePompe  -> efface l'alerte et le compteur de relances, puis renvoie l'etat
    # Aide des commandes, appelee SEULEMENT par diversFonctions.traiteAide (commandes sans sous-commande) :
    # sujet == nil -> [[nom, syntaxe, resume]] ; sujet non nil -> nil (pas de detail)
    def aideEtatPompe(sujet)
        if (sujet == nil)
            return [["", "(sans argument)", "affiche l'etat de la pompe vide-cave, des niveaux et de l'alerte"]]
        end
        return nil
    end
    def aideAcquittePompe(sujet)
        if (sujet == nil)
            return [["", "(sans argument)", "efface l'alerte et le compteur de relances, puis affiche l'etat"]]
        end
        return nil
    end

    tasmota.add_cmd("EtatPompe", def(cmd, idx, payload, payload_json)
        import json
        import diversFonctions
        if diversFonctions.traiteAide("EtatPompe", payload, aideEtatPompe, false)    return    end
        tasmota.resp_cmnd(json.dump({"EtatPompe": global.controlePompeVideCave.etat()}))
    end)
    tasmota.add_cmd("AcquittePompe", def(cmd, idx, payload, payload_json)
        import json
        import diversFonctions
        if diversFonctions.traiteAide("AcquittePompe", payload, aideAcquittePompe, false)    return    end
        global.controlePompeVideCave.acquitte()
        tasmota.resp_cmnd(json.dump({"AcquittePompe": "OK", "EtatPompe": global.controlePompeVideCave.etat()}))
    end)
end
