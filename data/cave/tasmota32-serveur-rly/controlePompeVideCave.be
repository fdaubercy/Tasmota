# Pompe vide-cave, carte ESP32 de la cave (tasmota32-cave-serveur-rly, IP 192.168.0.48) : SOLIDIFIABLE, sur le modele de
# controlePortail. La classe est portee par le module 'controlePompeVideCave' ; autoexec le charge par 'import' (version en
# FLASH). 'import' appelle AUTOMATIQUEMENT controlePompeVideCave_init(m), en pied de fichier, qui porte la garde d'activation.
#
# Affiche sur la page principale de Tasmota l'etat de la pompe vide-cave : derniere mise en route, nb de cycles du jour,
# intervalle depuis la mise en route precedente, et une cuve dessinee d'apres les deux flotteurs (cuve()).
#
# Migre 'afficheSensorPompeCave()' (webFonctions.be) + 'web_sensor()' (gestionWeb.be)
# de l'ancien module (tasmota32-serveur-rly-sauvegarde) vers le framework actuel :
#  - persist a plat ('modules', pas 'parametres.modules')
#  - capteurs de niveau ranges sous 'capteurs' (pas 'capteursPosition'), type+id separes
#  - 'diversFonctions.afficheDateTime()' ne formate plus que l'heure courante (elle ne
#    prend plus de timestamp en parametre) -> formatage local du timestamp stocke ici.
#
# Module solidifie : aucun import ni fonction de niveau fichier (le code de niveau fichier ne s'execute pas) ; tout est
# methode de la classe, les imports sont dans chaque methode qui les utilise. Meme rendu de la cuve que
# data/cave/tasmota32s3-serveur-rly/controlePompeVideCave.be (copie du S3, solidifiee aussi) : garder les deux identiques.
#@ solidify:controlePompeVideCave
var controlePompeVideCave = module("controlePompeVideCave")

class CONTROLE_POMPE_VIDE_CAVE : Driver
    def init()
        # Commandes Tasmota (console, HTTP, MQTT cmnd/<topic>/...) : reponse sur stat/<topic>/RESULT
        #   EtatPompe      -> {"EtatPompe": {"Pompe": "ON", "Niveaux": {...}, "Alerte": "", ...}}
        #   AcquittePompe  -> efface l'alerte et le compteur de relances, puis renvoie l'etat
        # L'aide (traiteAide) : sujet == nil -> [[nom, syntaxe, resume]] ; sujet non nil -> nil (pas de detail)
        tasmota.add_cmd("EtatPompe", def(cmd, idx, payload, payload_json)
            import json
            import global
            import diversFonctions
            if diversFonctions.traiteAide("EtatPompe", payload, / sujet -> sujet == nil ? [["", "(sans argument)", "affiche l'etat de la pompe vide-cave, des niveaux et de l'alerte"]] : nil, false)    return    end
            tasmota.resp_cmnd(json.dump({"EtatPompe": global.controlePompeVideCave.etat()}))
        end)
        tasmota.add_cmd("AcquittePompe", def(cmd, idx, payload, payload_json)
            import json
            import global
            import diversFonctions
            if diversFonctions.traiteAide("AcquittePompe", payload, / sujet -> sujet == nil ? [["", "(sans argument)", "efface l'alerte et le compteur de relances, puis affiche l'etat"]] : nil, false)    return    end
            global.controlePompeVideCave.acquitte()
            tasmota.resp_cmnd(json.dump({"AcquittePompe": "OK", "EtatPompe": global.controlePompeVideCave.etat()}))
        end)
    end

    # Formate un timestamp epoch en 'HHhMM'.
    def heure(timestamp)
        if (timestamp == 0)    return "jamais"    end

        var time_dump = tasmota.time_dump(timestamp)
        var heure = (time_dump["hour"] < 10 ? "0" + str(time_dump["hour"]) : str(time_dump["hour"]))
        var minute = (time_dump["min"] < 10 ? "0" + str(time_dump["min"]) : str(time_dump["min"]))

        return heure + "h" + minute
    end

    # Cuve dessinee d'apres les deux flotteurs (bas, haut = "ON" / "OFF" / "?"), "ON" = eau au-dessus du flotteur.
    # L'eau est un palier fixe (25 / 60 / 100 %), pas une mesure. Bas OFF et haut ON est impossible : cuve rouge.
    def cuve(bas, haut)
        var texte = "Niveau inconnu"
        var hauteur = 0
        var couleur = "#3a8fd0"
        if (bas == "OFF" && haut == "OFF")
            texte = "Sous le niveau bas"
            hauteur = 25
        elif (bas == "ON" && haut == "OFF")
            texte = "Entre le bas et le haut"
            hauteur = 60
        elif (bas == "ON" && haut == "ON")
            texte = "Au-dessus du niveau haut"
            hauteur = 100
        elif (bas == "OFF" && haut == "ON")
            texte = "Incoh&eacute;rent, v&eacute;rifier les flotteurs"
            hauteur = 55
            couleur = "#b3261e"
        end
        var etatBas = (bas == "ON" ? "atteint" : (bas == "OFF" ? "non atteint" : "?"))
        var etatHaut = (haut == "ON" ? "atteint" : (haut == "OFF" ? "non atteint" : "?"))

        return "<div class='cuve'>" +
                    "<div class='tank'>" +
                        "<div class='eau' style='height:" + str(hauteur) + "%;background:" + couleur + ";'></div>" +
                        "<div class='rep' style='bottom:80%;'><span>haut</span></div>" +
                        "<div class='rep' style='bottom:40%;'><span>bas</span></div>" +
                    "</div>" +
                    "<div class='legCuve'>" +
                        "<div><b>" + texte + "</b></div>" +
                        "<div>Niveau bas : " + etatBas + "</div>" +
                        "<div>Niveau haut : " + etatHaut + "</div>" +
                    "</div>" +
                "</div>"
    end

    def web_sensor()
        import string
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
                            "fieldset{border-radius:0.3rem;min-width:0;max-width:100%;box-sizing:border-box;}" +
                            ".parametre{border-radius:0.3rem;padding:1px;display:flex;flex-direction:row;}" +
                            ".cuve{display:flex;justify-content:center;align-items:center;gap:22px;margin:12px 0 6px;}" +
                            ".tank{position:relative;box-sizing:border-box;width:90px;height:120px;padding:0;border:2px solid #ddd;border-top:none;border-radius:0 0 8px 8px;background:#444;overflow:hidden;}" +
                            ".eau{position:absolute;left:0;right:0;bottom:0;padding:0;}" +
                            ".rep{position:absolute;left:0;right:0;padding:0;border-top:2px dashed #ffd54f;font-size:0.7rem;color:#ffd54f;}" +
                            ".rep span{position:absolute;right:3px;top:1px;}" +
                            ".legCuve div{margin:5px 0;}" +
                        "</style>" +
                        "<legend><b title='sensorPompe'>" + pompe.find("name", "Pompe Vide-Cave") + "</b></legend>" +
                        # Alerte levee par controleGeneral apres le nombre max de relances (acquittee
                        # automatiquement au premier arret avec le niveau haut retombe)
                        (relai.find("alerte", "") != "" ?
                            "<div style='color:#fff;background:#d43535;border-radius:0.3rem;padding:4px;margin-bottom:4px;white-space:normal;overflow-wrap:anywhere;word-break:break-word;max-width:100%;box-sizing:border-box;'><b>&#9888; " +
                            relai["alerte"] + "</b></div>" : "") +
                        "<div class='parametre'>" +
                            "<div>Pompe: </div>" +
                            "<div><b>" + textePompe + "</b></div>" +
                        "</div>" +
                        "<div class='parametre'>" +
                            "<div>Derniere mise en route: </div>" +
                            "<div>" + self.heure(horodatage.find("ON", 0)) + "</div>" +
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

        # Cuve : bas = capteur1, haut = capteur de la relance ; rien si l'un des deux est inactif
        var sensors = controleGeneral.lectureSensors()      # Lecture a la demande (cache 1 s)
        var cBas = capteurs.find("capteur1")
        var cHaut = capteurs.find(relai.find("relance", {}).find("capteur", ""))
        if (type(cBas) == "instance" && type(cHaut) == "instance" && type(cBas.find("id")) == "int" && type(cHaut.find("id")) == "int" &&
            cBas.find("activation", "OFF") == "ON" && cHaut.find("activation", "OFF") == "ON")
            msg += self.cuve(sensors.find("Switch" + str(cBas["id"]), "?"), sensors.find("Switch" + str(cHaut["id"]), "?"))
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
            "DerniereMiseEnRoute": self.heure(horodatage.find("ON", 0)),
            "CyclesJour": (horodatage.find("jourCycles", -1) == maintenant / 86400 ? horodatage.find("nbCyclesJour", 0) : 0),
            "Alerte": relai.find("alerte", "")
        }
    end

    # Efface l'alerte et le compteur de relances (commande 'AcquittePompe')
    def acquitte()
        var relai = modules["pompeVideCave"]["environnement"]["relais"]["relai1"]
        controleGeneral.acquitteRelance("pompeVideCave", relai)
        relai["alerte"] = ""
    end
end

# Publie la classe dans le module (solidification + import).
controlePompeVideCave.CONTROLE_POMPE_VIDE_CAVE = CONTROLE_POMPE_VIDE_CAVE

# init() : APPELEE AUTOMATIQUEMENT par 'import controlePompeVideCave'. Ne PAS la rappeler depuis autoexec. Driver enregistre
# seulement si le module pompeVideCave est active ; l'instance est publiee dans global.controlePompeVideCave.
def controlePompeVideCave_init(m)
    import global

    if (modules.find("pompeVideCave", {}).find("activation", "OFF") == "ON")
        global.controlePompeVideCave = m.CONTROLE_POMPE_VIDE_CAVE()
        tasmota.add_driver(global.controlePompeVideCave)
    end
    return m
end
controlePompeVideCave.init = controlePompeVideCave_init

# Valeur du module importe depuis le LittleFS (sans elle, import rend nil et init() n'est pas appelee)
return controlePompeVideCave
