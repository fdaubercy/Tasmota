# Définition du module
var cuveFonctions = module("/cuveFonctions")

cuveFonctions.sensorsCuve = {"valeursAnalogiques": {"valeurCapteurHauteur": 0}, "niveauCuve": {"hauteurEau": 0, "tauxRemplissage": 0, "volume": 0}}
cuveFonctions.voltageMax = 0.00         # voltageMax admissible par l'ADS1115 selon la plage de mesure paramétrée

cuveFonctions.log = def(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "cuve")
end

# --- Couleur du niveau et erreur de mesure (2026-10-11, mode manuel du ruban 2026-10-13) ---
# Le ruban WS2812 et l'encadre web prennent la couleur du taux de remplissage : teinte 0 (rouge, vide)
# a 119 (vert, pleine). En ERREUR DE MESURE, rouge clignotant. L'erreur suit la MEME regle que la
# sentinelle 'pas de mesure' envoyee au maitre ModBus : modbusFonctions.mesureFraiche (aucune mesure
# depuis 3 TelePeriod, 90 s au moins ; delai de grace apres le demarrage).
# Ruban gere par le module commun ledsFonctions (drivers.leds.environnement.leds.ruban actif) : la cuve
# ne fait que lui donner la teinte du niveau (mode AUTO) et lui signaler l'erreur ; ledsFonctions
# clignote, gere le mode MANUEL (bouton, page web) et la recopie par la LED du dev-kit.
# Ruban non gere : la teinte est posee directement, sans clignotement ni mode MANUEL.
cuveFonctions.enErreur = false          # dernier etat d'erreur constate (pour ne traiter que les transitions)
cuveFonctions.retourAutoEnregistre = false  # fonction de retour en AUTO donnee a ledsFonctions

# Teinte (0..119) d'un taux de remplissage, borne a [0, 1]
cuveFonctions.teinteNiveau = def(taux)
    taux = real(taux)
    if (taux < 0)    taux = 0.0    end
    if (taux > 1)    taux = 1.0    end
    return int(119.00 * taux)
end

# Couleur 'RRGGBB' (pleine luminosite) d'une teinte 0..119 et d'une saturation 0..255 :
# la couleur du ruban, calculee sans lui (l'encadre se colore meme ruban eteint)
cuveFonctions.couleurTeinte = def(teinte, sat)
    import string
    var mini = 255 - int(sat)
    var r = (teinte < 60 ? 255 : mini + (255 - mini) * (119 - teinte) / 59)
    var g = (teinte < 60 ? mini + (255 - mini) * teinte / 60 : 255)
    return string.format("%02X%02X%02X", int(r), int(g), mini)
end

# Le capteur de hauteur d'eau (analogique1) d'ou vient le niveau, ou nil
cuveFonctions.capteurNiveau = def()
    var ana = modules["cuve"]["environnement"].find("analogiques", {}).find("analogique1")
    if (ana == nil || ana.find("activation", "OFF") != "ON")    return nil    end
    return ana
end

# true si le capteur de niveau est en erreur de mesure (regle de la sentinelle ModBus)
cuveFonctions.niveauEnErreur = def()
    import modbusFonctions
    var ana = cuveFonctions.capteurNiveau()
    if (ana == nil)    return false    end
    return !modbusFonctions.mesureFraiche(int(ana["type"]) + int(ana["id"]) - 1)
end

# Releve brut de l'ADS1115 (0..32767) -> mV. Le releve est borne a 0 AVANT scale_int (2026-10-24, audit N1) :
# scale_int passe la valeur en uint16 (changeIntScale -> changeUIntScale, support_float.ino:466), un releve
# negatif (bruit de l'ADS1115 a 0 V) y devenait la PLEINE echelle -> cuve vide annoncee pleine.
cuveFonctions.versMv = def(brut)
    var b = int(brut)
    if (b < 0)    b = 0    end
    return tasmota.scale_int(b, 0, 32767, 0, cuveFonctions.voltageMax)
end

# true si la lecture 'mV' de la voie 'cleA' de l'ADS1115 est une mesure, selon le pilote i2c_ads1115
# (global.i2c_ads1115, instance publiee par i2c_ads1115_init). Pilote absent, ou firmware sans
# mesureValide (pas encore recompile) : la lecture est acceptee, comme avant.
cuveFonctions.lectureValide = def(cleA, mV, valeurs)
    import global
    import introspect
    var ads = (global.contains("i2c_ads1115") ? global.i2c_ads1115 : nil)
    if (!isinstance(ads, Driver) || introspect.get(ads, "mesureValide") == nil)    return true    end
    return ads.mesureValide(cleA, mV, valeurs)
end

# Montage de la sonde de niveau, d'apres sa voie de l'ADS1115 (i2c_ads1115.montage, 2026-10-31) :
# {"rapport", "entreeMax_V", "sondeMax_V"}, rapport = tension de la sonde / tension a l'entree de l'ADS1115
# (pont R1/R2 ; 1 en direct). nil sans pilote (ou firmware sans montage), sans capteur de niveau, ou si la voie
# mesure un courant.
cuveFonctions.montageSonde = def()
    import global
    import string
    import introspect
    var ana = cuveFonctions.capteurNiveau()
    var ads = (global.contains("i2c_ads1115") ? global.i2c_ads1115 : nil)
    if (ana == nil || !isinstance(ads, Driver) || introspect.get(ads, "montage") == nil)    return nil    end
    var m = ads.montage(string.format("A%d", int(ana["id"]) - 1))
    var rapport = (m["montage"] == "pont" ? real(m["R1"] + m["R2"]) / m["R2"] : (m["montage"] == "direct" ? 1.0 : nil))
    if (rapport == nil)    return nil    end
    return {"rapport": rapport, "entreeMax_V": m["pleineEchelle_V"], "sondeMax_V": m["pleineEchelle_V"] * rapport}
end

# Entree analogique qui sert la tension de la sonde au maitre par ModBus (virtuel "Calcul_tensionSonde", 2026-10-31) :
# registre type + id - 1 (4708 pour l'id 5), valeur en mV entiers. nil si le persist n'en a pas (ou desactivee).
cuveFonctions.entreeTensionSonde = def()
    for e: modules["cuve"]["environnement"].find("analogiques", {})
        if (isinstance(e, map) && e.find("activation", "OFF") == "ON" && e.find("virtuel") == "Calcul_tensionSonde")    return e    end
    end
    return nil
end

# Le relais WS2812 du module (ruban), ou nil s'il n'est pas actif
cuveFonctions.relaisRuban = def()
    var ws2812 = modules["cuve"]["environnement"].find("relais", {}).find("relai1")
    if (ws2812 == nil || ws2812.find("activation", "OFF") != "ON" || ws2812.find("type") != 1376)    return nil    end
    return ws2812
end

# true si le ruban est gere par le module commun ledsFonctions (mode MANUEL, bouton, clignotement)
cuveFonctions.rubanGere = def()
    if (drivers.find("leds", {}).find("activation", "OFF") != "ON")    return false    end
    return (drivers["leds"].find("environnement", {}).find("leds", {}).find("ruban", {}).find("activation", "OFF") == "ON")
end

# true si ledsFonctions est charge (ruban gere ou LED RGB du dev-kit active) : il recoit l'erreur de niveau
cuveFonctions.ledsActif = def()
    if (cuveFonctions.rubanGere())    return true    end
    if (drivers.find("leds", {}).find("activation", "OFF") != "ON")    return false    end
    return (drivers["leds"].find("environnement", {}).find("leds", {}).find("ledRGB", {}).find("activation", "OFF") == "ON")
end

# Donne au ruban la teinte du niveau : par ledsFonctions (ignoree en mode MANUEL) si le ruban est gere,
# sinon directement (light.set sans 'power' : un ruban eteint le reste)
cuveFonctions.appliqueCouleurNiveau = def()
    import light
    var ws2812 = cuveFonctions.relaisRuban()
    if (ws2812 == nil)    return    end
    var teinte = cuveFonctions.teinteNiveau(cuveFonctions.sensorsCuve["niveauCuve"]["tauxRemplissage"])
    if (cuveFonctions.rubanGere())
        import ledsFonctions
        ledsFonctions.appliqueAuto(teinte)
    else
        var channel = ws2812.find("channel", 0)
        if (light.get(channel) != nil)    light.set({"hue": teinte}, channel)    end
    end
end

# Appelee chaque seconde (controleCuve.every_second) : journalise les transitions de l'erreur de niveau
# et la signale a ledsFonctions (clignotement du ruban en AUTO, LED du dev-kit en rouge clignotant).
# Au premier passage (demarrage termine), donne a ledsFonctions la fonction du retour en AUTO.
cuveFonctions.majTemoinErreur = def()
    var erreur = cuveFonctions.niveauEnErreur()

    if (erreur != cuveFonctions.enErreur)
        cuveFonctions.enErreur = erreur
        if (erreur)
            cuveFonctions.log("CUVE_ERREUR_MESURE: capteur de niveau sans mesure (absent ou defaillant) : ruban et encadre en rouge clignotant", LOG_LEVEL_ERREUR)
        else
            cuveFonctions.log("CUVE_ERREUR_MESURE: capteur de niveau de nouveau mesure : couleur du niveau retablie", LOG_LEVEL_INFO)
        end
    end

    if (!cuveFonctions.ledsActif())    return    end
    import ledsFonctions
    ledsFonctions.signaleErreur("cuve", erreur)
    if (!cuveFonctions.retourAutoEnregistre && cuveFonctions.rubanGere())
        ledsFonctions.enregistreRetourAuto(/-> cuveFonctions.appliqueCouleurNiveau(), "la couleur suit le niveau de la cuve (rouge = vide, vert = pleine)")
        cuveFonctions.retourAutoEnregistre = true
    end
end

# Aide de la commande ReglageCuve, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
cuveFonctions.aideReglageCuve = def(sujet)
    import string
    if (sujet == nil)
        return [
            ["etalonnageCapteur", "etalonnageCapteur <ON|OFF>", "mesure rapprochee du niveau pendant 10 min"],
            ["hauteurCuve", "hauteurCuve <cm>", "regle la hauteur de la cuve"],
            ["largeurCuve", "largeurCuve <cm>", "regle la largeur de la cuve"],
            ["longueurCuve", "longueurCuve <cm>", "regle la longueur de la cuve"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "ETALONNAGECAPTEUR")
        return ["Parametre : ON ou OFF (1 = ON, 0 = OFF).",
                "Effet ON : remplace la tache cron de mesure 'majNiveauCuve' par une tache plus",
                "        frequente (cron '*/5 * * * * *', soit toutes les 5 s), puis un timer de",
                "        10 min remet la cadence normale ('*/60 * * * * *').",
                "Effet OFF : remet tout de suite la cadence normale.",
                "Sauvegarde : modules cuve reglage = ON|OFF (persist.save).",
                "Exemple : ReglageCuve etalonnageCapteur ON"]
    end
    if (sujet == "HAUTEURCUVE" || sujet == "LARGEURCUVE" || sujet == "LONGUEURCUVE")
        return ["Parametre : entier, dimension en cm (partie entiere retenue).",
                "Effet : memorise modules cuve dimensions " + (sujet == "HAUTEURCUVE" ? "hauteur" : (sujet == "LARGEURCUVE" ? "largeur" : "longueur")) + ".",
                "        et sauvegarde (persist.save). Parametre absent, non numerique, < 1 cm ou > 10000 cm :",
                "        ignore (erreur journalisee), la dimension memorisee reste en place.",
                "        Les 3 dimensions servent au calcul du volume ; la reponse les rappelle.",
                "Exemple : Backlog ReglageCuve hauteurCuve 110; ReglageCuve largeurCuve 180;",
                "          ReglageCuve longueurCuve 340"]
    end
    return nil
end

# Dimension de cuve saisie par ReglageCuve -> entier en cm (partie entiere), ou nil si le parametre n'est pas
# un nombre positif (2026-10-24, audit D3) : int('abc') vaut 0 en Berry, et une hauteur 0 memorisee faisait
# lever divzero_error a chaque releve.
cuveFonctions.dimensionCuve = def(p)
    var s = str(p)
    if (size(s) == 0)    return nil    end
    var point = false
    for i: 0 .. size(s) - 1
        if (s[i] == "." && !point)    point = true    continue    end
        if (s[i] < "0" || s[i] > "9")    return nil    end
    end
    var r = real(s)
    if (r < 1 || r > 10000)    return nil    end      # 1 cm .. 100 m : au-dela, int() deborderait
    return int(r)
end

# Memorise une dimension de la cuve ("hauteur", "largeur", "longueur") si le parametre est valide
cuveFonctions.regleDimension = def(cle, p)
    import string
    import persist
    var v = cuveFonctions.dimensionCuve(p)
    if (v == nil)
        cuveFonctions.log(string.format("REGLAGE_CUVE_ERREUR: %s '%s' refusee : nombre de cm >= 1 attendu, valeur memorisee conservee !", cle, str(p)), LOG_LEVEL_ERREUR)
        return
    end
    modules["cuve"]["dimensions"][cle] = v
    persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
end

#- Exemples:
    ReglageCuve etalonnageCapteur ON       => Augmente la frequence de mesure pendant 10min (frequence=1mesure/10s)
    Backlog ReglageCuve hauteurCuve 110; ReglageCuve largeurCuve 180; ReglageCuve longueurCuve 340      => Force et enregistre les dimensions de la cuve
-#
cuveFonctions.reglageCuve = def(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    if diversFonctions.traiteAide("ReglageCuve", payload, cuveFonctions.aideReglageCuve, true)    return    end


    var fonction = false
    var parametres = []
    var reponse_cmnd
    
    # Test   
    cuveFonctions.log("REGLAGE_CUVE: -------------------- ReglageCuve -------------------", LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_CUVE: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_CUVE: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_CUVE: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_CUVE: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    logFonctions.log("REGLAGE_CUVE: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS, "cuve")
    if (parametres.size() > 0)	logFonctions.log("REGLAGE_CUVE: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS, "cuve")	end
    if (parametres.size() > 1)	logFonctions.log("REGLAGE_CUVE: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS, "cuve")	end

    if (!modules["cuve"].find("dimensions", false))
        modules["cuve"].insert("dimensions", {})
    end

    # Augmente la frequence de mesure pendant 10min (frequence=1mesure/10s)
    if string.toupper(fonction) == string.toupper("etalonnageCapteur")
        try
            # Adapte le paramètre
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            
            # Supprime la tache CRON de mesure actuelle & Augmente la fréquence
            if (parametres[0] == "ON")
                # Mesures du niveau toutes les 10s
                tasmota.remove_cron("majNiveauCuve")
                tasmota.add_cron("*/5 * * * * *", /-> cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", ""), "majNiveauCuve")

                # Lance un timer qui annulera la tache CRON et la remettra d'origine / 60s après 10min
                tasmota.set_timer(600000,   def()  
                                                tasmota.remove_cron("majNiveauCuve")
                                                tasmota.add_cron("*/60 * * * * *", /-> cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", ""), "majNiveauCuve")
                                            end)
            else
                tasmota.remove_cron("majNiveauCuve")
                tasmota.add_cron("*/60 * * * * *", /-> cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", ""), "majNiveauCuve")
            end

            # Enregistre le reglage
            modules["cuve"]["reglage"] = parametres[0]
            persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Reglage hauteur de Cuve
    elif string.toupper(fonction) == "HAUTEURCUVE"
        cuveFonctions.regleDimension("hauteur", parametres.size() > 0 ? parametres[0] : "")
    # Reglage largeur de Cuve
    elif string.toupper(fonction) == "LARGEURCUVE"
        cuveFonctions.regleDimension("largeur", parametres.size() > 0 ? parametres[0] : "")
    # Reglage longueur de Cuve
    elif string.toupper(fonction) == "LONGUEURCUVE"
        cuveFonctions.regleDimension("longueur", parametres.size() > 0 ? parametres[0] : "")
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd = string.format("ReglageCuve: reglage=%s, largeurCuve=%dcm, longueurCuve=%dcm, hauteurCuve=%dcm",
                                            modules["cuve"]["reglage"], modules["cuve"]["dimensions"].find("largeur", 100), 
                                            modules["cuve"]["dimensions"].find("longueur", 100), 
                                            modules["cuve"]["dimensions"].find("hauteur", 100))
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Aide de la commande ReglageAna, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
cuveFonctions.aideReglageAna = def(sujet)
    import string
    if (sujet == nil)
        return [
            ["voltageMax", "voltageMax <volts>", "regle la tension maximale admissible de l'ADS1115"],
            ["cablage", "cablage", "rappelle le cablage des 4 voies (pont diviseur ou shunt a poser)"],
            ["voie", "voie <A0..A3> <tension|courant> <plage>", "regle ce que mesure une voie et rappelle son cablage"],
            ["seuilMin", "seuilMin <A0..A3> <mV>", "en dessous, la lecture est une erreur (sonde debranchee) ; 0 = desactive"],
            ["alimentation", "alimentation <volts>", "tension d'alimentation de l'ADS1115 (3.3 ou 5)"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "CABLAGE")
        return ["Sans parametre. Journalise et renvoie le montage de chaque voie : pont diviseur",
                "R1/R2 pour une tension, resistance de shunt pour un courant (valeurs E24),",
                "calcule pour que la pleine echelle reste sous la tension d'alimentation.",
                "Exemple : ReglageAna cablage"]
    end
    if (sujet == "VOIE")
        return ["Parametres : voie A0..A3, mesure tension|courant, plage :",
                "  tension (A0, A1) : 0-5V, 0-10V ou 0-24V",
                "  courant (A2, A3) : 0-20mA ou 4-20mA (4-20mA : boucle coupee detectee sous 3,6 mA)",
                "Effet : memorise drivers I2C ADS1115 voies <voie>, sauvegarde, renvoie le cablage a poser.",
                "Exemples : ReglageAna voie A0 tension 0-10V ; ReglageAna voie A2 courant 4-20mA"]
    end
    if (sujet == "SEUILMIN")
        return ["Parametres : voie A0..A3, seuil en mV mesures A L'ENTREE de l'ADS1115 (apres le pont).",
                "Effet : une lecture sous ce seuil n'est pas une mesure (sonde debranchee ou non",
                "        alimentee) : erreur de mesure apres le delai de fraicheur. 0 = desactive.",
                "Exemple : ReglageAna seuilMin A0 50"]
    end
    if (sujet == "ALIMENTATION")
        return ["Parametre : tension d'alimentation (VDD) de l'ADS1115, en volts : 3.3 ou 5.",
                "Effet : pleine echelle visee 3,0 V (3,3 V) ou 4,0 V (5 V) ; change les resistances",
                "        conseillees (ReglageAna cablage). Une entree ne doit jamais depasser VDD.",
                "Exemple : ReglageAna alimentation 3.3"]
    end
    if (sujet == "VOLTAGEMAX")
        return ["Parametre : nombre reel, tension max en volts (ex. 3.3 ou 3.20).",
                "Effet : memorise modules cuve environnement analogiques voltageMax.",
                "        et sauvegarde (persist.save). Parametre absent ou non numerique : ignore.",
                "Exemple : ReglageAna voltageMax 3.3"]
    end
    return nil
end

#- Exemples: 
    ReglageAna voltageMax 3.3
    ReglageAna voltageMax 3.20
-#
cuveFonctions.reglageAna = def(cmd, idx, payload, payload_json)
    import string
    import json
    import webFonctions
    import persist
    import diversFonctions
    if diversFonctions.traiteAide("ReglageAna", payload, cuveFonctions.aideReglageAna, true)    return    end


    var fonction = false
    var parametres = []
    var reponse_cmnd
    
    # Test   
    cuveFonctions.log("REGLAGE_ANA: -------------------- ReglageAna -------------------", LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_ANA: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_ANA: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_ANA: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    cuveFonctions.log("REGLAGE_ANA: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    logFonctions.log("REGLAGE_ANA: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS, "cuve")
    if (parametres.size() > 0)	logFonctions.log("REGLAGE_ANA: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS, "cuve")	end
    if (parametres.size() > 1)	logFonctions.log("REGLAGE_ANA: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS, "cuve")	end

    # Reglage de la tension maximale admissible de l'ADS1115 -> ordre: voltageMax
    if string.toupper(fonction) == "VOLTAGEMAX"
        try
            modules["cuve"]["environnement"]["analogiques"]["voltageMax"] = real(parametres[0])
            persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    end

    # Voies de l'ADS1115 (2026-10-11) : la configuration vit dans drivers.I2C.environnement.ADS1115,
    # le pilote i2c_ads1115 en deduit le cablage (rappel) et la validite des lectures (mesureValide)
    var fonctionMaj = string.toupper(str(fonction))
    if (fonctionMaj == "CABLAGE" || fonctionMaj == "VOIE" || fonctionMaj == "SEUILMIN" || fonctionMaj == "ALIMENTATION")
        tasmota.resp_cmnd(json.dump(cuveFonctions.reglageVoies(fonctionMaj, (parametres.size() > 0 ? parametres[0] : ""))))
        return
    end

    # Commande réussie
    # Réponse à la commande
    # 3 valeurs pour 3 formats (il n'en passait qu'une : string.format levait, aucune reponse)
    var ana = modules["cuve"]["environnement"]["analogiques"]
    reponse_cmnd = string.format("reglageADS1115: valeur Min=%i, valeur Max=%i, voltage Max=%.2fV",
                                    ana.find("valeurMin", 0), ana.find("valeurMax", 0), ana.find("voltageMax", 6.144))
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Sous-commandes de ReglageAna sur les voies de l'ADS1115 : retourne la reponse (map) a la commande
cuveFonctions.reglageVoies = def(fonction, arguments)
    import string
    import global
    import introspect
    import persist

    var ads = (global.contains("i2c_ads1115") ? global.i2c_ads1115 : nil)
    if (!isinstance(ads, Driver) || introspect.get(ads, "rappel") == nil)
        return {"erreur": "pilote i2c_ads1115 absent (ADS1115 inactif) ou firmware a recompiler"}
    end
    var conf = drivers["I2C"]["environnement"]["ADS1115"]
    var mots = (arguments == "" ? [] : string.split(arguments, " "))

    try
        if (fonction == "VOIE")
            var nom = string.toupper(mots[0])
            var mesure = string.tolower(mots[1])
            var plage = mots[2]
            if (ads.VOIES.find(nom) == nil)    return {"erreur": "voie inconnue : " + nom + " (A0..A3)"}    end
            var plages = (mesure == "courant" ? ads.PLAGES_COURANT : ads.PLAGES_TENSION)
            if ((mesure != "tension" && mesure != "courant") || !plages.contains(plage))
                return {"erreur": "mesure ou plage inconnue : tension 0-5V|0-10V|0-24V, courant 0-20mA|4-20mA"}
            end
            if (!conf.contains("voies"))    conf["voies"] = {}    end
            var voie = conf["voies"].find(nom, {})
            voie["mesure"] = mesure
            voie["plage"] = plage
            if (!voie.contains("seuilMin_mV"))    voie["seuilMin_mV"] = 0    end
            conf["voies"][nom] = voie
            persist.save(true)
            cuveFonctions.log("REGLAGE_ANA: " + ads.rappel(nom), LOG_LEVEL_INFO)
            return {nom: ads.rappel(nom)}
        elif (fonction == "SEUILMIN")
            var nom = string.toupper(mots[0])
            if (ads.VOIES.find(nom) == nil)    return {"erreur": "voie inconnue : " + nom + " (A0..A3)"}    end
            if (!conf.contains("voies"))    conf["voies"] = {}    end
            var voie = conf["voies"].find(nom, ads.voie(nom))
            voie["seuilMin_mV"] = int(mots[1])
            conf["voies"][nom] = voie
            persist.save(true)
            return {nom: ads.rappel(nom)}
        elif (fonction == "ALIMENTATION")
            conf["alimentation_V"] = real(mots[0])
            persist.save(true)
        end
    except .. as error, message
        return {"erreur": "parametres invalides (" + str(message) + ") : ReglageAna aide " + string.tolower(fonction)}
    end

    # CABLAGE (et retour d'ALIMENTATION) : les 4 voies
    ads.rappelCablage()
    var reponse = {"alimentation_V": real(conf.find("alimentation_V", 3.3))}
    for nom: ads.VOIES    reponse[nom] = ads.rappel(nom)    end
    return reponse
end

# Règles sur changement d'état des capteurs
cuveFonctions.changementEtatCapteur = def(value, trigger, msg, moduleCapteur, cleBouton)
    import string
	import mqtt
	import json

	# Test
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: -------------------- Cuve changementEtatCapteur -------------------", LOG_LEVEL_DEBUG_PLUS)
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)			# moduleCapteur=pompeVideCave
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG)					# cleBouton=bouton1

    tasmota.yield()

	# Extrait la valeur scalaire d'un evenement, ex: {"Action": "ON"} -> "ON", sur TOUS les niveaux
	# d'imbrication. Une map a plusieurs cles (ex. mesures ADS1115 A0..A3) est volontairement laissee intacte.
	import diversFonctions
	value = diversFonctions.valeurScalaire(value)

    # Si msg="" & value=""
    if (msg == "" || value == "")
        msg = {}
        msg.insert("ADS1115", controleGeneral.lectureSensors().find(trigger))
    end

    # ADS1115 absent des capteurs (I2C en defaut) : pas de mesure, donc pas de noteMesure ;
    # l'erreur de mesure viendra de la fraicheur (niveauEnErreur), sans exception a chaque cron
    if (!isinstance(msg, map) || !isinstance(msg.find("ADS1115"), map))
        cuveFonctions.log("CUVE_GESTION_CAPTEURS: pas de mesure ADS1115 dans les capteurs", LOG_LEVEL_DEBUG)
        return
    end

    # Gère les actions sur modification d'état des capteur analogiques virtuels
    var analogiques = modules[moduleCapteur]["environnement"]["analogiques"]

    # Evite un bug
    if (analogiques && msg["ADS1115"].size() == 4 && string.find(json.dump(msg), "div10") < 0)
        # Parcours les voies de l'ADS1115 enregistrees pour enregistrer leur valeur. Vraie cle de chaque entree, et
        # seulement les virtuels I2C_ADS1115 (2026-10-31) : la boucle relisait 'analogique<rang>' (key_error si les
        # numeros ne se suivent pas) et prenait tout virtuel pour une voie (analogique5, tension de la sonde servie
        # par ModBus, aurait ete ecrasee par la voie A4).
        var sonde = cuveFonctions.montageSonde()               # une fois par releve (montage : boucle E24, petites maps)
        var entree = cuveFonctions.entreeTensionSonde()
        for cleAna: analogiques.keys()
            tasmota.yield()
            if type(analogiques[cleAna]) != "instance"   continue    end

            if (analogiques[cleAna].find("activation", "OFF") == "ON" && analogiques[cleAna].find("virtuel", "OFF") == "I2C_ADS1115")
                # Mesure recue (meme inchangee) : fraicheur pour la sentinelle ModBus (2026-10-10).
                # Teste la PRESENCE de la cle (contains) et non sa valeur : une lecture 0 est une mesure.
                # noteMesure appele directement (et non noteMesureModbus, reserve a l'esclave ModBus) :
                # l'erreur de mesure du ruban et de la page web (niveauEnErreur) en depend aussi (2026-10-11).
                # Une lecture n'est une mesure que si le pilote i2c_ads1115 l'accepte (mesureValide) : ADS1115
                # perdu (4 voies a 0), sous le seuilMin_mV de la voie, boucle 4-20 mA coupee -> pas de noteMesure.
                var cleA = string.format("A%d", analogiques[cleAna]["id"] - 1)
                if (msg["ADS1115"].contains(cleA))
                    import modbusFonctions
                    var mVlu = cuveFonctions.versMv(msg["ADS1115"][cleA])
                    if (cuveFonctions.lectureValide(cleA, mVlu, msg["ADS1115"]))
                        modbusFonctions.noteMesure(int(analogiques[cleAna]["type"]) + int(analogiques[cleAna]["id"]) - 1)
                        # La tension de la sonde servie au maitre est fraiche avec la mesure dont elle est tiree
                        if (entree != nil && sonde != nil)
                            modbusFonctions.noteMesure(int(entree["type"]) + int(entree["id"]) - 1)
                        end
                    end
                end
                if (!msg["ADS1115"].find(string.format("A%d", analogiques[cleAna]["id"] - 1), false))    continue    end
                if int(analogiques[cleAna]["value"]) != int(msg["ADS1115"][string.format("A%d", analogiques[cleAna]["id"] - 1)])
                    cuveFonctions.log(string.format("CUVE_GESTION_CAPTEURS: Mise à jour du capteur '%s' en json.", analogiques[cleAna]["nom"]), LOG_LEVEL_DEBUG)

                    # Enregistre la valeur en json
                    analogiques[cleAna]["value"] = int(msg["ADS1115"][string.format("A%d", analogiques[cleAna]["id"] - 1)])
                    modules[moduleCapteur]["environnement"]["analogiques"][cleAna]["value"] = int(analogiques[cleAna]["value"])

                    # Mets àjour le taux de remplissage, et le volume d'eau disponible
                    # Récupère la valeur analogique du capteur & la convertit en mV (bornee a 0 : versMv, audit N1)
                    cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"] = cuveFonctions.versMv(analogiques[cleAna]["value"])

                    # Tension de la sonde (0-10 V) recalculee par le rapport du pont, au centieme de volt
                    # (2026-10-31) : affichee sur l'accueil et la page /cuve a cote de la tension brute
                    if (sonde != nil)
                        var mVSonde = cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"] * sonde["rapport"]
                        cuveFonctions.sensorsCuve["valeursAnalogiques"]["tensionSonde_V"] = int(mVSonde / 10 + 0.5) / 100.0
                        # ... et servie au maitre P4 par ModBus, en mV entiers (entreeTensionSonde)
                        if (entree != nil)    entree["value"] = int(mVSonde + 0.5)    end
                    end

                    # Convertit la valeur (en V) vers une valeur en cm
                    # Coefficient de conversion: 30mV/cm
                    cuveFonctions.sensorsCuve["niveauCuve"]["hauteurEau"] = 
                                        cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"] / modules[moduleCapteur]["environnement"]["analogiques"][cleAna].find("conversion_mV_cm", 1.0)
                end
            end
        end

        # Calcul le pourcentage d'eau dans la cuve & le volume disponible
        var hauteur = modules[moduleCapteur].find("dimensions", {}).find("hauteur", 100)    # en cm
        var largeur = modules[moduleCapteur].find("dimensions", {}).find("largeur", 100)    # en cm
        var longueur = modules[moduleCapteur].find("dimensions", {}).find("longueur", 100)    # en cm

        # Hauteur nulle ou negative (persist edite a la main) : pas de calcul, sinon divzero_error a chaque
        # releve (2026-10-24, audit D3b). Le taux et le volume precedents restent en place.
        if (hauteur <= 0)
            cuveFonctions.log(string.format("CUVE_GESTION_CAPTEURS_ERREUR: hauteur de cuve invalide (%s cm) : taux et volume non calcules, corriger par ReglageCuve hauteurCuve <cm> !", str(hauteur)), LOG_LEVEL_ERREUR)
        else
            # Pourcentage ENTIER : multiplier avant de diviser (2026-10-24, audit T1). h / H * 100 passait par
            # une fraction non representable (0,53) et la troncature rendait 52.
            var pourcent = int(cuveFonctions.sensorsCuve["niveauCuve"]["hauteurEau"] * 100 / real(hauteur))
            # Borne a 0..100 % (2026-10-24, audit HB) : un capteur au-dessus de la hauteur de la cuve annoncait
            # plus de 100 % et un volume superieur a la capacite.
            if (pourcent > 100)    pourcent = 100    elif (pourcent < 0)    pourcent = 0    end
            var pourcentageEau = pourcent / 100.00

            cuveFonctions.sensorsCuve["niveauCuve"]["tauxRemplissage"] = pourcentageEau
            cuveFonctions.sensorsCuve["niveauCuve"]["volume"] =  int(hauteur * largeur * longueur * pourcentageEau / 1000)    # en litres
        end

        # Règle la couleur du ruban WS2812 en fonction du taux de remplissage (mode AUTO ; en erreur de
        # mesure, ledsFonctions fait clignoter le ruban en rouge par-dessus)
        cuveFonctions.appliqueCouleurNiveau()

        cuveFonctions.log(string.format("CUVE_GESTION_CAPTEURS: sensorsCuve=%s", cuveFonctions.sensorsCuve), LOG_LEVEL_INFO)
    end
end

# Retourne le module lors de l'importation
return cuveFonctions