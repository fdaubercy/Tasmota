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
    def web_sensor()
        var pompe = modules["pompeVideCave"]

        if (pompe.find("activation", "OFF") != "ON")    return    end

        var relai = pompe["environnement"]["relais"]["relai1"]
        var capteurs = pompe["environnement"]["capteurs"]

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
                        "<div class='parametre'>" +
                            "<div>Derniere mise en route: </div>" +
                            "<div>" + affiche_heure(relai["timestamp"]["ON"]) + "</div>" +
                        "</div>" +
                        "<div class='parametre'>" +
                            "<div>Nb. de cycles du jour: </div>" +
                            "<div>" + str(relai["timestamp"].find("nbCyclesJour", 0)) + "</div>" +
                        "</div>" +
                        "<div class='parametre'>" +
                            "<div>Intervalle de fonctionnement moyen: </div>" +
                            "<div>" + str(int(relai["timestamp"].find("delai", 0) / 60)) + "min</div>" +
                        "</div>"

        for cleCapteur: capteurs.keys()
            if (type(capteurs[cleCapteur]) != "instance")    continue    end
            if (capteurs[cleCapteur].find("activation", "OFF") != "ON")    continue    end

            msg += "<div class='parametre'>" +
                        "<div class='titreSwitch'>" + capteurs[cleCapteur].find("nom", cleCapteur) + " :</div>" +
                        "<button class='btnSwitch'>" + controleGeneral.sensors.find("Switch" + str(capteurs[cleCapteur]["id"]), "?") + "</button>" +
                    "</div>"
        end

        msg += "</fieldset></table>"

        tasmota.web_send(msg)
    end
end

# Active le Driver uniquement si le module 'pompeVideCave' est active
if (modules["pompeVideCave"].find("activation", "OFF") == "ON")
    controlePompeVideCave = CONTROLE_POMPE_VIDE_CAVE()
    tasmota.add_driver(controlePompeVideCave)
end
