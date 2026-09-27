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
end

# Active le Driver uniquement si le module 'pompeVideCave' est active
# 'global.' explicite : l'affectation d'un nom non declare dans un bloc 'if' est refusee en
# mode strict ("strict: no global ..."), et loadBerryFile compile ce fichier en contexte LOCAL
# (tasmota.compile) ou meme le niveau fichier ne cree plus de globale.
if (modules["pompeVideCave"].find("activation", "OFF") == "ON")
    import global
    global.controlePompeVideCave = CONTROLE_POMPE_VIDE_CAVE()
    tasmota.add_driver(global.controlePompeVideCave)
end
