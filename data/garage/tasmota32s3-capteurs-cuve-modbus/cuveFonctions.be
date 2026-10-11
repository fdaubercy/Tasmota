# Définition du module
var cuveFonctions = module("/cuveFonctions")

cuveFonctions.sensorsCuve = {"valeursAnalogiques": {"valeurCapteurHauteur": 0}, "niveauCuve": {"hauteurEau": 0, "tauxRemplissage": 0, "volume": 0}}
cuveFonctions.voltageMin = 0.00
cuveFonctions.voltageMax = 0.00         # voltageMax admissible par l'ADS1115 selon la plage de mesure paramétrée

cuveFonctions.log = def(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "cuve")
end

# --- Couleur du niveau et erreur de mesure (2026-10-11) ---
# Le ruban WS2812 et l'encadre web prennent la couleur du taux de remplissage : teinte 0 (rouge, vide)
# a 119 (vert, pleine). En ERREUR DE MESURE, rouge clignotant. L'erreur suit la MEME regle que la
# sentinelle 'pas de mesure' envoyee au maitre ModBus : modbusFonctions.mesureFraiche (aucune mesure
# depuis 3 TelePeriod, 90 s au moins ; delai de grace apres le demarrage).
# Le clignotement ecrit les pixels du ruban (classe Leds) et non light.set : light.set reecrit les
# Settings a chaque appel, et 'rgb' 000000 couperait le ruban (Power off, xdrv_52_3_berry_light.ino:273).
cuveFonctions.enErreur = false          # dernier etat d'erreur constate (pour ne traiter que les transitions)
cuveFonctions.phaseClignote = false     # phase du clignotement : true = rouge, false = eteint
cuveFonctions.ruban = nil               # strip natif du pilote light (Leds), cree a la premiere ecriture

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

# Le relais WS2812 du module (ruban), ou nil s'il n'est pas actif
cuveFonctions.relaisRuban = def()
    var ws2812 = modules["cuve"]["environnement"].find("relais", {}).find("relai1")
    if (ws2812 == nil || ws2812.find("activation", "OFF") != "ON" || ws2812.find("type") != 1376)    return nil    end
    return ws2812
end

# Ecrit une couleur (entier 0xRRGGBB) sur tout le ruban, a la luminosite du pilote light.
# Ruban eteint : rien n'est ecrit (l'erreur ne rallume pas un ruban eteint volontairement).
cuveFonctions.peintRuban = def(couleur)
    var ws2812 = cuveFonctions.relaisRuban()
    if (ws2812 == nil)    return    end
    var etat = light.get(ws2812.find("channel", 0))
    if (etat == nil || !etat.find("power", false))    return    end
    try
        if (cuveFonctions.ruban == nil)    cuveFonctions.ruban = Leds()    end
        cuveFonctions.ruban.clear_to(couleur, etat.find("bri", 127))
        cuveFonctions.ruban.show()
    except .. as error, message
        cuveFonctions.ruban = nil
        cuveFonctions.log("PEINT_RUBAN_ERREUR: " + str(error) + " -> " + str(message), LOG_LEVEL_ERREUR)
    end
end

# Appelee chaque seconde (controleCuve.every_second) : clignotement rouge tant que le capteur de niveau
# est en erreur ; au retour d'une mesure, le ruban reprend la couleur du niveau (celle du pilote light,
# que le clignotement avait recouverte sans la modifier).
# LED RGB du dev-kit (module commun ledRGBFonctions) : ruban allume -> elle le recopie (couleur imposee) ;
# ruban eteint ou absent -> voyant d'etat, ou l'erreur de niveau clignote en rouge (signaleErreur).
cuveFonctions.majTemoinErreur = def()
    var erreur = cuveFonctions.niveauEnErreur()

    if (erreur != cuveFonctions.enErreur)
        cuveFonctions.enErreur = erreur
        if (erreur)
            cuveFonctions.log("CUVE_ERREUR_MESURE: capteur de niveau sans mesure (absent ou defaillant) : ruban et encadre en rouge clignotant", LOG_LEVEL_ERREUR)
        else
            cuveFonctions.log("CUVE_ERREUR_MESURE: capteur de niveau de nouveau mesure : couleur du niveau retablie", LOG_LEVEL_INFO)
            var ws2812 = cuveFonctions.relaisRuban()
            var etat = (ws2812 != nil ? light.get(ws2812.find("channel", 0)) : nil)
            if (etat != nil)    cuveFonctions.peintRuban(int("0x" + etat.find("rgb", "000000")))    end
        end
    end

    # Etat du ruban
    var ws2812 = cuveFonctions.relaisRuban()
    var etat = (ws2812 != nil ? light.get(ws2812.find("channel", 0)) : nil)
    var allume = (etat != nil && etat.find("power", false))
    var couleur = (allume ? int("0x" + etat.find("rgb", "000000")) : nil)

    if (erreur)
        cuveFonctions.phaseClignote = !cuveFonctions.phaseClignote
        couleur = (cuveFonctions.phaseClignote ? 0xFF0000 : 0x000000)
        cuveFonctions.peintRuban(couleur)
        if (!allume)    couleur = nil    end
    end

    cuveFonctions.majLedRGB(erreur, couleur, (etat != nil ? etat.find("bri", 127) : 127))
end

# Transmet a la LED RGB du dev-kit (si elle est activee) l'erreur de niveau et la couleur du ruban
# (nil = ruban eteint ou absent : la LED redevient voyant d'etat)
cuveFonctions.majLedRGB = def(erreur, couleur, bri)
    var led = drivers.find("leds", {}).find("environnement", {}).find("leds", {}).find("ledRGB", {})
    if (drivers.find("leds", {}).find("activation", "OFF") != "ON" || led.find("activation", "OFF") != "ON")    return    end
    import ledRGBFonctions
    ledRGBFonctions.signaleErreur("cuve", erreur)
    ledRGBFonctions.imposeCouleur("cuve", couleur, bri)
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
                "        et sauvegarde (persist.save). Parametre absent ou non entier : ignore.",
                "        Les 3 dimensions servent au calcul du volume ; la reponse les rappelle.",
                "Exemple : Backlog ReglageCuve hauteurCuve 110; ReglageCuve largeurCuve 180;",
                "          ReglageCuve longueurCuve 340"]
    end
    return nil
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
        try
            modules["cuve"]["dimensions"]["hauteur"] = int(parametres[0])
            persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Reglage largeur de Cuve
    elif string.toupper(fonction) == "LARGEURCUVE"
        try
            modules["cuve"]["dimensions"]["largeur"] = int(parametres[0])
            persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Reglage longueur de Cuve
    elif string.toupper(fonction) == "LONGUEURCUVE"
        try
            modules["cuve"]["dimensions"]["longueur"] = int(parametres[0])
            persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
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
            ["voltageMax", "voltageMax <volts>", "regle la tension maximale admissible de l'ADS1115"]
        ]
    end
    sujet = string.toupper(sujet)
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

    # Commande réussie
    # Réponse à la commande
    # 3 valeurs pour 3 formats (il n'en passait qu'une : string.format levait, aucune reponse)
    var ana = modules["cuve"]["environnement"]["analogiques"]
    reponse_cmnd = string.format("reglageADS1115: valeur Min=%i, valeur Max=%i, voltage Max=%.2fV",
                                    ana.find("valeurMin", 0), ana.find("valeurMax", 0), ana.find("voltageMax", 6.144))
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
cuveFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import json

	# Test
	cuveFonctions.log("CUVE_CHGT_ETAT_DEMARRAGE: -------------------- Cuve changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
	cuveFonctions.log("CUVE_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	cuveFonctions.log("CUVE_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	cuveFonctions.log("CUVE_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	if (type(value) == "instance")
		for cle: value.keys()
			value = value[cle]
		end
	end

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
        elif msg["WIFI"].find("Disonnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    # Save: Avant redemarrage de tasmota
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
        elif msg[trigger].find("Save", 0)
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
    end
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
	# d'imbrication (avant : un seul niveau deroule, et 'value' reaffectee pendant le parcours de ses
	# cles). Une map a plusieurs cles (ex. mesures ADS1115 A0..A3) est volontairement laissee intacte.
	while isinstance(value, map)
		if value.contains("Action")
			value = value["Action"]
		elif value.size() == 1
			value = value[value.keys()()]		# unique cle
		else
			break
		end
	end

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
        var nb = 1

        # Parcours les capteurs analogiques enregistrés pour enregistrer leur valeur
        for cleAna: analogiques.keys()
            tasmota.yield()
            if type(analogiques[cleAna]) != "instance"   continue    end

            cleAna = string.format("analogique%d", nb)
            nb += 1

            if (analogiques[cleAna].find("activation", "OFF") == "ON" && analogiques[cleAna].find("virtuel", "OFF") != "OFF")
                # Mesure recue (meme inchangee) : fraicheur pour la sentinelle ModBus (2026-10-10).
                # Teste la PRESENCE de la cle (contains) et non sa valeur : une lecture 0 est une mesure.
                # noteMesure appele directement (et non noteMesureModbus, reserve a l'esclave ModBus) :
                # l'erreur de mesure du ruban et de la page web (niveauEnErreur) en depend aussi (2026-10-11).
                if (msg["ADS1115"].contains(string.format("A%d", analogiques[cleAna]["id"] - 1)))
                    import modbusFonctions
                    modbusFonctions.noteMesure(int(analogiques[cleAna]["type"]) + int(analogiques[cleAna]["id"]) - 1)
                end
                if (!msg["ADS1115"].find(string.format("A%d", analogiques[cleAna]["id"] - 1), false))    continue    end
                if int(analogiques[cleAna]["value"]) != int(msg["ADS1115"][string.format("A%d", analogiques[cleAna]["id"] - 1)])
                    cuveFonctions.log(string.format("CUVE_GESTION_CAPTEURS: Mise à jour du capteur '%s' en json.", analogiques[cleAna]["nom"]), LOG_LEVEL_DEBUG)

                    # Enregistre la valeur en json
                    analogiques[cleAna]["value"] = int(msg["ADS1115"][string.format("A%d", analogiques[cleAna]["id"] - 1)])
                    modules[moduleCapteur]["environnement"]["analogiques"][cleAna]["value"] = int(analogiques[cleAna]["value"])

                    # Mets àjour le taux de remplissage, et le volume d'eau disponible
                    # Récupère la valeur analogique du capteur & la convertit en mV
                    cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"] = tasmota.scale_int(analogiques[cleAna]["value"], 
                                                                                                                        0, 32767, 0, cuveFonctions.voltageMax)

                    # Borne la valeur du capteur de hauteur d'eau
                    if (cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"] < 0)   
                        cuveFonctions.sensorsCuve["valeursAnalogiques"]["valeurCapteurHauteur"] = 0
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

        var pourcentageEau = int(cuveFonctions.sensorsCuve["niveauCuve"]["hauteurEau"] / real(hauteur) * 100) / 100.00  

        cuveFonctions.sensorsCuve["niveauCuve"]["tauxRemplissage"] = pourcentageEau
        cuveFonctions.sensorsCuve["niveauCuve"]["volume"] =  int(hauteur * largeur * longueur * pourcentageEau / 1000)    # en litres

        # Règle la couleur de la LED WS2812 témoin en fonction du taux de remplissage
        # (en erreur de mesure, majTemoinErreur fait clignoter le ruban en rouge par-dessus)
        var ws2812 = cuveFonctions.relaisRuban()
        if (ws2812 != nil)
            var channel = ws2812.find("channel", 0)
            var etatWs2812 = light.get(channel)

            if (etatWs2812 != nil)
                light.set({"hue": cuveFonctions.teinteNiveau(pourcentageEau), "bri": etatWs2812["bri"], "sat": etatWs2812["sat"]}, channel)
            end
        end

        cuveFonctions.log(string.format("CUVE_GESTION_CAPTEURS: sensorsCuve=%s", cuveFonctions.sensorsCuve), LOG_LEVEL_INFO)
    end
end

# Retourne le module lors de l'importation
return cuveFonctions