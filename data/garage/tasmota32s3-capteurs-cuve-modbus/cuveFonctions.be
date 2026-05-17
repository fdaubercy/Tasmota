# Définition du module
var cuveFonctions = module("/cuveFonctions")

cuveFonctions.DEBUG = nil
cuveFonctions.sensorsCuve = {"valeursAnalogiques": {"valeurCapteurHauteur": 0}, "niveauCuve": {"hauteurEau": 0, "tauxRemplissage": 0, "volume": 0}}
cuveFonctions.voltageMin = 0.00
cuveFonctions.voltageMax = 0.00         # voltageMax admissible par l'ADS1115 selon la plage de mesure paramétrée

cuveFonctions.log = def(msg, levelDebug)
    import persist

    if (cuveFonctions.DEBUG == nil)
        cuveFonctions.DEBUG = modules["cuve"].find("debug", "OFF")
    end

    if (cuveFonctions.DEBUG == "ON")
        log(msg, levelDebug)
    end
end

#- Exemples: 
    ReglageCuve logActivation OFF   => Active ou désactive les logs du module
    ReglageCuve etalonnageCapteur ON       => Augmente la frequence de mesure pendant 10min (frequence=1mesure/10s)
    Backlog ReglageCuve hauteurCuve 110; ReglageCuve largeurCuve 180; ReglageCuve longueurCuve 340      => Force et enregistre les dimensions de la cuve
-#
cuveFonctions.reglageCuve = def(cmd, idx, payload, payload_json)
    import string
    import json
    import persist

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

    log("REGLAGE_CUVE: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres.size() > 0)	log("REGLAGE_CUVE: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
    if (parametres.size() > 1)	log("REGLAGE_CUVE: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

    if (!modules["cuve"].find("dimensions", false))
        modules["cuve"].insert("dimensions", {})
    end

    # Activation ou désactivation des logs de gestion de la cuve -> ordre: logActivation
    if string.toupper(fonction) == "LOGACTIVATION"
        try
            # Adapte le paramètre
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            cuveFonctions.DEBUG = parametres[0]

            # Sauvegarde le paramètre
            modules["cuve"]["debug"] = parametres[0]
            persist.save()
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Augmente la frequence de mesure pendant 10min (frequence=1mesure/10s)
    elif string.toupper(fonction) == string.toupper("etalonnageCapteur")
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
            persist.save()
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Reglage hauteur de Cuve
    elif string.toupper(fonction) == "HAUTEURCUVE"
        try
            modules["cuve"]["dimensions"]["hauteur"] = int(parametres[0])
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Reglage largeur de Cuve
    elif string.toupper(fonction) == "LARGEURCUVE"
        try
            modules["cuve"]["dimensions"]["largeur"] = int(parametres[0])
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    # Reglage longueur de Cuve
    elif string.toupper(fonction) == "LONGUEURCUVE"
        try
            modules["cuve"]["dimensions"]["longueur"] = int(parametres[0])
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd = string.format("ReglageCuve: logActivated=%s, reglage=%s, largeurCuve=%dcm, longueurCuve=%dcm, hauteurCuve=%dcm", 
                                            cuveFonctions.DEBUG, modules["cuve"]["reglage"], modules["cuve"]["dimensions"].find("largeur", 100), 
                                            modules["cuve"]["dimensions"].find("longueur", 100), 
                                            modules["cuve"]["dimensions"].find("hauteur", 100))
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

#- Exemples: 
    ReglageAna voltageMax 3.3
    ReglageAna voltageMax 3.20
-#
cuveFonctions.reglageAna = def(cmd, idx, payload, payload_json)
    import string
    import json
    import webFonctions

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

    log("REGLAGE_ANA: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres.size() > 0)	log("REGLAGE_ANA: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
    if (parametres.size() > 1)	log("REGLAGE_ANA: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

    # Activation ou désactivation des logs du RangeExtender -> ordre: logActivation
    if string.toupper(fonction) == "VOLTAGEMAX"
        try
            modules["cuve"]["environnement"]["analogiques"]["voltageMax"] = real(parametres[0])
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd = string.format("reglageADS1115: valeur Min=%i, valeur Max=%i, voltage Max=%.2fV", 
                                    modules["cuve"]["environnement"]["analogiques"].find("voltageMax", 6.144))
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end

# Règles sur changement d'état lors du démarrage de Tasmota
cuveFonctions.changementEtatDemarrage = def(value, trigger, msg)
    import string
    import mqtt
    import json

	# Test
	cuveFonctions.log("CUVE_CHGT_ETAT_DEMARRAGE: -------------------- Cuve changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
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
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: -------------------- Cuve changementEtatCapteur -------------------", LOG_LEVEL_DEBUG)
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: moduleCapteur=" + str(moduleCapteur), LOG_LEVEL_DEBUG)			# moduleCapteur=pompeVideCave
	cuveFonctions.log("CUVE_GESTION_CAPTEURS: cleBouton=" + str(cleBouton), LOG_LEVEL_DEBUG)					# cleBouton=bouton1

    tasmota.yield()

	if (type(value) == "instance" && value.size() == 1)
		for cle: value.keys()
			value = value[cle]
		end
	end

    # Si msg="" & value=""
    if (msg == "" || value == "")
        msg = {}
        msg.insert("ADS1115", controleGeneral.sensors[trigger])
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
        var ws2812 = modules[moduleCapteur]["environnement"]["relais"]["relai1"]
        if (ws2812.find("activation", "OFF") == "ON")
            var channel = ws2812.find("channel", 1)
            var etatWs2812 = light.get(channel)

            light.set({"hue": int(119.00 * pourcentageEau), "bri": etatWs2812["bri"], "sat": etatWs2812["sat"]}, channel)
        end

        cuveFonctions.log(string.format("CUVE_GESTION_CAPTEURS: sensorsCuve=%s", cuveFonctions.sensorsCuve), LOG_LEVEL_INFO)
    end
end

# Retourne le module lors de l'importation
return cuveFonctions