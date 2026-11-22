# Pompe vide-cave, carte S3 de la cave (tasmota32s3-cave-serveur-rly) : SOLIDIFIABLE, sur le modele de controlePortail. La classe
# est portee par le module 'controlePompeVideCave' ; autoexec le charge par 'import' (version en FLASH). 'import' appelle
# AUTOMATIQUEMENT controlePompeVideCave_init(m), en pied de fichier, qui porte la garde d'activation.
#
# Affiche sur la page principale de Tasmota l'etat de la pompe vide-cave : derniere mise en route, nb de cycles du jour,
# intervalle depuis la mise en route precedente, et une cuve dessinee d'apres les deux flotteurs (cuve()). Surveille aussi les
# pannes des flotteurs (voir plus bas).
#
# Module solidifie : aucun import ni fonction de niveau fichier (le code de niveau fichier ne s'execute pas) ; tout est methode de
# la classe, les imports sont dans chaque methode ou closure qui les utilise.
# Meme affichage (heure(), cuve()) et memes commandes EtatPompe / AcquittePompe que data/cave/tasmota32-serveur-rly/controlePompeVideCave.be
# (carte ESP32, sans la gestion des pannes de flotteurs) : garder ces parties identiques.
#@ solidify:controlePompeVideCave
var controlePompeVideCave = module("controlePompeVideCave")

class CONTROLE_POMPE_VIDE_CAVE : Driver
    # Pannes des flotteurs (persist pompeVideCave.pannes = {"antiRebond": s, "maxArretsMinuterie": n}, sans la cle : rien)
    #  - incoherence : haut ON et bas OFF depuis plus de antiRebond s (physiquement impossible)
    #  - flotteurBas : n arrets de suite par la minuterie (duree >= timer - 1 s) alors que le haut est OFF et le bas encore ON ;
    #    remis a 0 par un arret avec le bas OFF ; rien n'est compte pendant une marche manuelle (flotteurs suspendus)
    # Alerte sur la voie de controleGeneral::publieAlerteRelance (topicAlerte, relai["alerte"], effacee par AcquittePompe).
    # Limites connues : l'alerte flotteurBas peut etre vide jusqu'a 1 s apres chaque arret (finTimerRelai l'efface, le tick
    # suivant la repose) ; AcquittePompe pendant une incoherence en cours acquitte l'episode, elle ne revient qu'a un nouvel episode.
    # Niveaux des flotteurs : jamais de read_sensors() ici (every_second et json_append, ce dernier appele DANS la telemetrie
    # SENSOR dont read_sensors() vide le tampon). Ils viennent d'une regle SwitchN#Action propre au driver (elle tourne meme
    # flotteur suspendu par une marche manuelle), amorcee par l'etat memorise du persist (corrige au demarrage par
    # controleGeneral::resynchroniseCapteurs, qui rejoue l'etat reel).
    var debutIncoh, alerteIncoh, arrets, etatPrec, manuelPrec, niv, idBas, idHaut

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

    def init()
        import string
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

        self.debutIncoh = 0
        self.alerteIncoh = false
        self.arrets = 0
        self.etatPrec = "OFF"
        self.manuelPrec = false
        self.niv = {"Bas": "?", "Haut": "?"}
        var pompe = modules.find("pompeVideCave")
        if (type(pompe) != "instance")    return    end
        var capteurs = pompe.find("environnement", {}).find("capteurs", {})
        var cleHaut = pompe.find("environnement", {}).find("relais", {}).find("relai1", {}).find("relance", {}).find("capteur", "")
        for role: [["Bas", "capteur1"], ["Haut", cleHaut]]
            var capteur = capteurs.find(role[1])
            if (type(capteur) != "instance" || type(capteur.find("id")) != "int")    continue    end
            var nom = role[0]
            self.niv[nom] = capteur.find("etat", "?")
            if (nom == "Bas")    self.idBas = capteur["id"]    else    self.idHaut = capteur["id"]    end
            tasmota.add_rule(string.format("Switch%i#Action", capteur["id"]), def(value, trigger, msg) self.niv[nom] = str(value) end)
        end
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
        if (!pannes || pompe.find("activation", "OFF") != "ON" || self.idBas == nil || self.idHaut == nil)    return    end

        var relai = pompe["environnement"]["relais"]["relai1"]
        var capteurs = pompe["environnement"]["capteurs"]
        var bas = self.niv["Bas"]
        var haut = self.niv["Haut"]
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
        import string
        var pompe = modules["pompeVideCave"]
        if (pompe.find("activation", "OFF") != "ON")    return    end
        var relai = pompe["environnement"]["relais"]["relai1"]
        var capteurs = pompe["environnement"]["capteurs"]
        tasmota.response_append(string.format(',"PompeVideCave":{"Pompe":"%s","Manuel":"%s","Niveaux":{"Bas":"%s","Haut":"%s"},"Alerte":%s}',
            relai.find("etat", "OFF"), self.manuel(capteurs) ? "ON" : "OFF",
            self.niv["Bas"], self.niv["Haut"],
            json.dump(relai.find("alerte", ""))))
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

        # Cuve : bas = capteur1, haut = capteur de la relance (comme init()) ; rien si l'un des deux est inactif
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
        self.arrets = 0
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
