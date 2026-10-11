#- NOTES Sur le module I2C ADS1115 à 4 entrées analogiques
    - Configurateur lancé une seule fois au démarrage : compte les entrées analogiques virtuelles
      'I2C_ADS1115', vérifie que le module répond sur le bus I2C, puis active le driver Tasmota 13
      (ADS1115) et règle l'affichage WebSensor12. Aucune tâche périodique.
    - Revu le 2026-09-27 avant solidification :
        * adresse comparée en minuscules : I2CScan répond "0x%02x" (support_a_i2c.ino:349) ;
          en majuscules, les adresses 0x4A/0x4B n'étaient jamais trouvées ;
        * I2CScan lancé une seule fois (il l'était pour CHAQUE module, avant même de savoir
          si le module avait des analogiques) ;
        * plus de 'drivers[nil]' quand aucune entrée ne vise l'ADS1115 (exception au boot) ;
        * '/json/nbIOActives.json' n'est plus rechargé : il n'était jamais lu ;
        * héritage ': Driver' rétabli (il était annulé par un '#').
    - Les 4 voies (2026-10-11). Persist drivers.I2C.environnement.ADS1115 :
        "alimentation_V": 3.3                       tension d'alimentation (VDD) de l'ADS1115
        "voies": {"A0": {"mesure": "tension", "plage": "0-10V", "seuilMin_mV": 0}, ...}
          * A0, A1 : mesure "tension", plage "0-5V" | "0-10V" | "0-24V"
          * A2, A3 : mesure "courant", plage "0-20mA" | "4-20mA"
          * seuilMin_mV : en dessous (mV a l'entree de l'ADS1115), la lecture n'est pas une mesure
            (sonde debranchee ou non alimentee) ; 0 = desactive.
      Une entree ne doit jamais depasser la tension d'alimentation : la pleine echelle de chaque voie
      est ramenee a une tension CIBLE (3,0 V si VDD = 3,3 V ; 4,0 V si VDD = 5 V ; plage +/-4,096 V,
      Sensor12 S1). montage() en deduit les resistances (E24) : pont diviseur R1 (capteur -> entree) /
      R2 = 10 kOhm (entree -> GND) pour une tension, shunt (entree -> GND) pour un courant.
      rappelCablage() le journalise au demarrage (et sur ReglageAna cablage).
      Detail et schema : outils_docs/Electronique/ADS1115/CABLAGE_ADS1115.md.
    - Validite d'une lecture (mesureValide), appelee par les modules qui lisent l'ADS1115 :
        * les 4 voies exactement a 0 : ADS1115 perdu apres le demarrage (une lecture I2C ratee rend
          0 sans erreur, support_a_i2c.ino:123) ;
        * sous seuilMin_mV : sonde debranchee ou non alimentee ;
        * plage 4-20mA sous 3,6 mA : boucle coupee (le 4 mA du zero vivant a disparu).
-#
# Rendu solidifiable (2026-09-27), sur le modele de controleGeneral : la classe est portee
# par le module import-able 'i2c_ads1115'. autoexec le charge par 'import' (version en FLASH
# via load_native), plus par loadBerryFile (qui recompilait la classe en RAM).
# 'import' appelle AUTOMATIQUEMENT i2c_ads1115_init(m), en pied de fichier.
#@ solidify:i2c_ads1115
var i2c_ads1115 = module("i2c_ads1115")

class I2C_ADS1115 : Driver
    # Variables
    var adresseI2C
    var nbAnalogiquesADS1115
    var muet                    # 4 voies a 0 constatees (pour ne journaliser que la transition)

    static VOIES = ["A0", "A1", "A2", "A3"]
    static PLAGES_TENSION = {"0-5V": 5.0, "0-10V": 10.0, "0-24V": 24.0}
    static PLAGES_COURANT = {"0-20mA": 20.0, "4-20mA": 20.0}
    static R2 = 10000                   # resistance basse du pont diviseur (Ohm)
    static SEUIL_BOUCLE_mA = 3.6        # 4-20 mA : en dessous, boucle coupee
    # Serie E24 (une decade) : valeurs normalisees des resistances courantes
    static E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                  3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]

    def init(adresseI2C)
        import string

        self.adresseI2C = adresseI2C
        self.nbAnalogiquesADS1115 = 0
        self.muet = false

        if (self.adresseI2C == nil)  return  end

        # Compte les entrées analogiques activées et reliées virtuellement à l'ADS1115
        for cleModule: modules.keys()
            tasmota.yield()

            if (type(modules[cleModule]) != "instance")   continue      end

            var analogiques = modules[cleModule].find("environnement", {}).find("analogiques", false)
            if (!analogiques)   continue    end

            for cleANA: analogiques.keys()
                if type(analogiques[cleANA]) != "instance"   continue    end
                tasmota.yield()

                if (analogiques[cleANA].find("activation", "OFF") == "ON" && analogiques[cleANA].find("virtuel", "OFF") == "I2C_ADS1115")
                    self.nbAnalogiquesADS1115 += 1
                end
            end
        end

        if (self.nbAnalogiquesADS1115 == 0)
            logFonctions.log("I2C_ADS1115: Aucune entrée analogique activée sur l'ADS1115 !", LOG_LEVEL_DEBUG)
            return
        end

        # Rappel du cablage des 4 voies, AVANT la recherche du module : utile justement s'il ne repond pas
        self.rappelCablage()

        # Vérifie une seule fois que l'ADS1115 répond sur le bus I2C
        var result = tasmota.cmd("I2CScan", boolMute)
        if (result == nil || !result.contains("I2CScan"))
            logFonctions.log("I2C_ADS1115: Le bus I2C n'est pas activé dans le firmware ou les ports I2C ne sont pas configurés !", LOG_LEVEL_ERREUR)
            return
        end

        # 'adresseI2C' vaut "0x48" dans le persist : string.format la convertit par int()
        var adresse = string.format("0x%02x", self.adresseI2C)
        if (string.find(result["I2CScan"], adresse) < 0)
            logFonctions.log(string.format("I2C_ADS1115: Module absent du bus I2C à l'adresse %s !", adresse), LOG_LEVEL_ERREUR)
            return
        end

        # Active le Driver 13 (ADS1115) s'il est désactivé ou absent de la liste
        var ads1115 = drivers["I2C"]["environnement"]["ADS1115"]
        var reponse = tasmota.cmd("I2CDriver", boolMute)["I2CDriver"]
        if (string.find(reponse, "!13") > -1 || string.find(reponse, "13") == -1)
            tasmota.cmd("I2CDriver13 ON", boolMute)
        end

        # Vérifie si on doit interdire l'affichage des valeurs de capteurs sur la page html
        if (ads1115.find("affichageWebSensor", false))
            tasmota.cmd(string.format("WebSensor12 %s", ads1115.find("affichageWebSensor", "ON")), boolMute)
        end

        logFonctions.log(string.format("I2C_ADS1115: %i entrée(s) analogique(s) sur le module %s !", self.nbAnalogiquesADS1115, adresse), LOG_LEVEL_DEBUG)
    end

    # Le bloc ADS1115 du persist ({} s'il manque)
    def config()
        return drivers.find("I2C", {}).find("environnement", {}).find("ADS1115", {})
    end

    # La configuration d'une voie ("A0".."A3"), avec ses valeurs par defaut
    def voie(nom)
        var v = self.config().find("voies", {}).find(nom, {})
        var courant = (nom == "A2" || nom == "A3")
        return {"mesure": v.find("mesure", courant ? "courant" : "tension"), "plage": v.find("plage", courant ? "0-20mA" : "0-10V"),
                "seuilMin_mV": v.find("seuilMin_mV", 0)}
    end

    # Tension cible (V) a l'entree de l'ADS1115 pour la pleine echelle d'une voie
    def tensionCible()
        return (real(self.config().find("alimentation_V", 3.3)) >= 4.5 ? 4.0 : 3.0)
    end

    # Valeur E24 la plus proche de x : par exces (superieur = true) ou par defaut
    def e24(x, superieur)
        var decade = 1.0
        while (x >= decade * 10)    decade *= 10    end
        while (x < decade)    decade /= 10    end
        var retenue = (superieur ? 10 * decade : decade)
        for m: self.E24
            var r = m * decade
            if (superieur && r >= x - 0.0001)    return r    end
            if (!superieur && r <= x + 0.0001)    retenue = r    end
        end
        return retenue
    end

    # Ohm en texte : 6800 -> "6,8 kOhm", 24000 -> "24 kOhm", 150 -> "150 Ohm"
    def ohm(r)
        import string
        if (r >= 1000)
            var k = string.format("%.1f", r / 1000.0)
            if (string.find(k, ".0") == size(k) - 2)    k = k[0 .. size(k) - 3]    end
            return string.replace(k, ".", ",") + " kOhm"
        end
        return string.format("%i Ohm", int(r))
    end

    # Montage d'une voie : {"montage": "direct"|"pont"|"shunt", "R1", "R2", "Rshunt" (Ohm), "pleineEchelle_V"}
    def montage(nom)
        var v = self.voie(nom)
        var cible = self.tensionCible()
        if (v["mesure"] == "courant")
            var imax = self.PLAGES_COURANT.find(v["plage"], 20.0)
            var rs = self.e24(cible / (imax / 1000.0), false)
            return {"montage": "shunt", "Rshunt": rs, "pleineEchelle_V": rs * imax / 1000.0}
        end
        var vmax = self.PLAGES_TENSION.find(v["plage"], 10.0)
        if (vmax <= cible)    return {"montage": "direct", "pleineEchelle_V": vmax}    end
        var r1 = self.e24(self.R2 * (vmax / cible - 1), true)
        return {"montage": "pont", "R1": r1, "R2": self.R2, "pleineEchelle_V": vmax * self.R2 / (r1 + self.R2)}
    end

    # Texte du rappel de cablage d'une voie
    def rappel(nom)
        import string
        var v = self.voie(nom)
        var m = self.montage(nom)
        var pe = string.replace(string.format("%.2f V", m["pleineEchelle_V"]), ".", ",")
        var texte = string.format("%s %s %s : ", nom, v["mesure"], v["plage"])
        if (m["montage"] == "direct")
            texte += "capteur directement sur " + nom + " (pleine echelle " + pe + ")"
        elif (m["montage"] == "pont")
            texte += string.format("pont diviseur, R1 = %s entre le signal du capteur et %s, R2 = %s entre %s et GND (pleine echelle %s)",
                                   self.ohm(m["R1"]), nom, self.ohm(m["R2"]), nom, pe)
        else
            texte += string.format("shunt %s entre %s et GND ; boucle : alim + -> capteur (+), capteur (-) -> %s ; GND de l'alim relie au GND de l'ADS1115 (pleine echelle %s)",
                                   self.ohm(m["Rshunt"]), nom, nom, pe)
            if (v["plage"] == "4-20mA")    texte += " ; boucle coupee detectee sous 3,6 mA"    end
        end
        if (v["seuilMin_mV"] > 0)    texte += string.format(" ; erreur sous %i mV", int(v["seuilMin_mV"]))    end
        return texte
    end

    # Journalise le rappel de cablage des 4 voies
    def rappelCablage()
        import string
        logFonctions.log(string.replace(string.format("I2C_ADS1115_CABLAGE: alimentation %.1f V, pleine echelle visee %.1f V a l'entree (Sensor12 S1 : +/-4.096 V)",
                         real(self.config().find("alimentation_V", 3.3)), self.tensionCible()), ".", ","), LOG_LEVEL_INFO)
        for nom: self.VOIES
            logFonctions.log("I2C_ADS1115_CABLAGE: " + self.rappel(nom), LOG_LEVEL_INFO)
        end
    end

    # true si 'valeurs' (map brute A0..A3 de l'ADS1115) porte les 4 voies exactement a 0
    def toutesAZero(valeurs)
        for nom: self.VOIES
            if (!valeurs.contains(nom) || int(valeurs[nom]) != 0)    return false    end
        end
        return true
    end

    # true si la lecture 'mV' (a l'entree de l'ADS1115) de la voie 'nom' est une mesure.
    # 'valeurs' : la map brute A0..A3 de la meme lecture (detection de l'ADS1115 perdu).
    def mesureValide(nom, mV, valeurs)
        var muet = self.toutesAZero(valeurs)
        if (muet != self.muet)
            self.muet = muet
            if (muet)
                logFonctions.log("I2C_ADS1115_MUET: les 4 voies lisent exactement 0 : ADS1115 perdu sur le bus I2C (cablage, alimentation) ?", LOG_LEVEL_ERREUR)
            else
                logFonctions.log("I2C_ADS1115_MUET: l'ADS1115 repond de nouveau", LOG_LEVEL_INFO)
            end
        end
        if (muet)    return false    end

        var v = self.voie(nom)
        if (v["seuilMin_mV"] > 0 && mV < v["seuilMin_mV"])    return false    end
        if (v["mesure"] == "courant" && v["plage"] == "4-20mA")
            if (mV / self.montage(nom)["Rshunt"] < self.SEUIL_BOUCLE_mA)    return false    end    # mV / Ohm = mA
        end
        return true
    end
end

# Publie la classe dans le module (solidification + import).
i2c_ads1115.I2C_ADS1115 = I2C_ADS1115

# init() : APPELEE AUTOMATIQUEMENT par 'import i2c_ads1115' (be_module.c:285-296, module_init).
# Ne PAS la rappeler depuis autoexec. Reprend le code d'activation de niveau fichier d'avant
# (gardes comprises) ; l'instance est publiee dans global.i2c_ads1115.
# Lit controleGeneral.nbIOActivesJSON : importer controleGeneral AVANT ce module.
def i2c_ads1115_init(m)
    import global

    var nbIO = controleGeneral.nbIOActivesJSON.find("analogiques", {})
    if (nbIO.find("actives", {}).find("nb", 0) > nbIO.find("reels", {}).find("nb", 0))
        if (drivers.find("I2C", {}).find("activation", "OFF") == "ON")
            try
                var ads1115 = drivers["I2C"].find("environnement", {}).find("ADS1115", {})
                if (ads1115.find("activation", "OFF") == "ON")
                    global.i2c_ads1115 = m.I2C_ADS1115(ads1115.find("adresseI2C"))
                    tasmota.add_driver(global.i2c_ads1115)
                    logFonctions.log("I2C_ADS1115: Driver I2C_ADS1115 activé !", LOG_LEVEL_DEBUG)
                end
            except .. as error, message
                import string
                logFonctions.log(string.format("I2C_ADS1115_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
            end
        end
    end
    return m
end
i2c_ads1115.init = i2c_ads1115_init
