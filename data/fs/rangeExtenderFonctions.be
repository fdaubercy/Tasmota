# Définition du module
#@ solidify:rangeExtenderFonctions
var rangeExtenderFonctions = module("rangeExtenderFonctions")

# Etat modifiable du module, dans une GLOBALE (solidification 2026-09-27). Un module
# solidifie est constant (en flash) : y ecrire leve "'module' value has no writable
# attribute", et ses listes sont figees. La map est creee au premier appel avec les
# valeurs de depart qu'avaient les anciens attributs du module.
def rangeExtenderFonctions_etat()
    import global
    if (global._etatRangeExtenderFonctions == nil)
        global._etatRangeExtenderFonctions = {
            "DEBUG": nil,             # 'ON'/'OFF', lu une fois depuis serveur['rangeExtender']['debug']
            "redirections": {}        # maitre : redirections NAPT deja posees, port -> IP (voir redirige)
        }
    end
    return global._etatRangeExtenderFonctions
end
rangeExtenderFonctions.etat = rangeExtenderFonctions_etat


def rangeExtenderFonctions_log(msg, levelDebug)
    if (rangeExtenderFonctions.etat()["DEBUG"] == nil)
        rangeExtenderFonctions.etat()["DEBUG"] = serveur["rangeExtender"].find("debug", "OFF")
    end

    if (rangeExtenderFonctions.etat()["DEBUG"] == "ON")
        log(msg, levelDebug)
    end
end
rangeExtenderFonctions.log = rangeExtenderFonctions_log

# Pose la redirection NAPT <port du maitre> -> <ip>:80 (RgxPort) SAUF si elle est deja en place.
# Pourquoi (2026-10-04) : ip_portmap_add (lwIP, ip4_napt.c:632) met a jour une redirection
# existante SANS s'arreter, puis en cree un DOUBLON dans la premiere case libre. La table
# compte 10 cases (NAPT_PORT, xdrv_58_range_extender.ino:62), allouees une fois au demarrage :
# rappeler RgxPort a chaque affichage de la page d'accueil la remplissait (5 affichages avec
# 2 esclaves) ; ensuite, plus AUCUN nouvel esclave ne pouvait etre redirige jusqu'au
# redemarrage du maitre, sans message. Les redirections posees sont memorisees (port -> IP) ;
# la table lwIP et cette memoire repartent toutes deux de zero au redemarrage.
# Retourne true si la redirection est en place.
def rangeExtenderFonctions_redirige(port, ip)
    import string

    var etat = rangeExtenderFonctions.etat()
    if (etat.find("redirections") == nil)    etat["redirections"] = {}    end
    var poses = etat["redirections"]
    port = int(port)
    ip = str(ip)
    if (poses.find(port) == ip)    return true    end           # deja posee, meme IP : rien a faire

    # RgxPort repond "OK TCP ..." si la redirection est posee, "ERROR" sinon (table pleine...)
    var reponse = tasmota.cmd(string.format("RgxPort tcp, %i, %s, 80", port, ip), boolMute)
    if (reponse != nil && string.find(str(reponse), "OK") >= 0)
        poses[port] = ip
        rangeExtenderFonctions.log(string.format("RANGE_EXTENDER: redirection NAPT %i -> %s:80 posee", port, ip), LOG_LEVEL_DEBUG)
        return true
    end
    log(string.format("RANGE_EXTENDER: redirection NAPT %i -> %s:80 REFUSEE (table de 10 redirections pleine ? redemarrer le maitre)",
                      port, ip), LOG_LEVEL_ERREUR)
    return false
end
rangeExtenderFonctions.redirige = rangeExtenderFonctions_redirige

# Aide de la commande RoutageRangeExtender (sans sous-commande), appelee par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def rangeExtenderFonctions_aideRoutageRangeExtender(sujet)
    if (sujet == nil)
        return [
            ["", "(sans argument)", "pose les redirections NAPT (RgxPort) vers les esclaves RangeExtender connus"]
        ]
    end
    return nil
end
rangeExtenderFonctions.aideRoutageRangeExtender = rangeExtenderFonctions_aideRoutageRangeExtender

# Réalilse le routage
# Active RgxNAPT: RoutageRangeExtender
# RgxPort tcp, 8080, 192.168.4.2, 80
def rangeExtenderFonctions_routageRangeExtender(cmd, idx, payload, payload_json)
	import string
    import json
    import gestionFileFolder
    import persist
    import re
    import diversFonctions

    if diversFonctions.traiteAide("RoutageRangeExtender", payload, rangeExtenderFonctions.aideRoutageRangeExtender, false)    return    end

    var jsonData = {}
    var reponse_cmnd = {"RoutageRangeExtender": {"commmande": "", "status": "Echec..."}}
    var typeID = "esclave" + str(idx)
    
    # Test   
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: -------------------- routageRangeExtender -------------------", LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Lit le fichier json
    var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
    if (paramDiscovery == nil)
        rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: Le fichier 'discovery.json' n'existe pas ou est vide !", LOG_LEVEL_DEBUG_PLUS)
        return
    end

    reponse_cmnd["RoutageRangeExtender"]["status"] = "Echec..."

    # Parcours le json en listant les adresses MAC (item = adresse MAC)
    for item: paramDiscovery.keys()
        var pattern = re.compile('^(maitre|esclave[0-9]+)$')
        var result = {}

        # Parcours tous les esclaves enregistrés et les marque tous 'Offline'
        for cle : paramDiscovery[item].keys()
            # Evite le maitre
            if (cle == "maitre")    continue    end

            if pattern.match(cle)
                # result.insert(cle, jsonDiscovery[cle])
                # break

                # .find : une fiche recue par ImAlive n'a pas de 'lwt' tant que la decouverte MQTT n'est pas passee.
                # Seul un esclave RangeExtender (bloc 'rangeExtender' publie) a un port de routage.
                if (paramDiscovery[item].find("lwt", "Offline") == "Online" && isinstance(paramDiscovery[item][cle].find("rangeExtender", nil), map))
                    # Réalilse le routage
                    rangeExtenderFonctions.log("ROUTAGE_RANGE_EXTENDER: Paramètre le routage NAPT du module " + paramDiscovery[item][cle]["nom"], LOG_LEVEL_DEBUG)

                    reponse_cmnd["RoutageRangeExtender"]["commande"] = string.format("RgxPort tcp, %i, %s, 80", int(paramDiscovery[item][cle]["rangeExtender"]["routagePort"]),paramDiscovery[item][cle]["IPAddress"])
                    # Une seule fois par port et par IP : voir redirige (doublons de la table lwIP)
                    rangeExtenderFonctions.redirige(paramDiscovery[item][cle]["rangeExtender"]["routagePort"], paramDiscovery[item][cle]["IPAddress"])
                end
            end
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["RoutageRangeExtender"]["status"] = "Succès"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
rangeExtenderFonctions.routageRangeExtender = rangeExtenderFonctions_routageRangeExtender

# Aide de la commande ReglageRangeExtender, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def rangeExtenderFonctions_aideReglageRangeExtender(sujet)
    import string
    if (sujet == nil)
        return [
            ["logActivation", "logActivation <ON|OFF|1|0>", "active/coupe les logs de debug du RangeExtender"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "LOGACTIVATION")
        return ["Parametre : ON ou 1 = logs de debug RangeExtender actifs ; OFF ou 0 = coupes.",
                "Sauvegarde : serveur.rangeExtender.debug (persist.save).",
                "Exemple : ReglageRangeExtender logActivation ON"]
    end
    return nil
end
rangeExtenderFonctions.aideReglageRangeExtender = rangeExtenderFonctions_aideReglageRangeExtender

# exemples:
# ReglageRangeExtender logActivation OFF
def rangeExtenderFonctions_reglageRangeExtender(cmd, idx, payload, payload_json)
    import string
    import json
    import gestionFileFolder
    import persist
    import diversFonctions

    if diversFonctions.traiteAide("ReglageRangeExtender", payload, rangeExtenderFonctions.aideReglageRangeExtender, true)    return    end

    var fonction = false
    var parametres = false
    var jsonData = {}
    var reponse_cmnd = {"ReglageRangeExtender": {}}
    var typeID
    
    # Test   
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: -------------------- reglageRangeExtender -------------------", LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    rangeExtenderFonctions.log("REGLAGE_RANGE_EXTENDER: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    log("REGLAGE_RANGE_EXTENDER: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres != false)
        if (parametres.size() > 0)	log("REGLAGE_RANGE_EXTENDER: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
        if (parametres.size() > 1)	log("REGLAGE_RANGE_EXTENDER: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end
    end

    # Activation ou désactivation des logs du RangeExtender -> ordre: logActivation
    if string.toupper(fonction) == "LOGACTIVATION"
        try
            # Adapte le paramètre
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
            rangeExtenderFonctions.etat()["DEBUG"] = parametres[0]

            # Sauvegarde le paramètre
            serveur["rangeExtender"]["debug"] = parametres[0]
            persist.save()                  # serveur = persist.serveur : comme ReglageDiscovery
        except .. as e, m
            # print('Erreur: ', e, " -> ", m)
        end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["ReglageRangeExtender"]["logActivated"] = str(rangeExtenderFonctions.etat()["DEBUG"])
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
rangeExtenderFonctions.reglageRangeExtender = rangeExtenderFonctions_reglageRangeExtender

def rangeExtenderFonctions_configExtenderByJson()
    import persist
    import configGlobal
    import string

    var reponseCMD
    var json = serveur["rangeExtender"]

	# Règle le point d'accès Range Extender si activé (Si Maitre RangeExtender)
    if (json.find("activation", "OFF") == "ON")
        # Etat du routage NAPT du point d'accès
        if (configGlobal.testeParam("RgxNAPT", json["AP"]["routeNAPT"], "str"))
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle le routage du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
        end

        # Nom AP & Mot de passe
        reponseCMD = tasmota.cmd("RgxSSId", boolMute)
        if str(reponseCMD["Rgx"]["SSId"]) != str(json["AP"]["SSID"]) || str(reponseCMD["Rgx"]["Password"]) != str(json["AP"]["mdp"])
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle le nom et le mot de passe du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
            tasmota.cmd(string.format("Backlog RgxSSId %s; RgxPassword  %s", json["AP"]["SSID"], json["AP"]["mdp"]), boolMute)
        end

        # Adresse IP et Masque de sous-réseau
        if str(reponseCMD["Rgx"]["IPAddress"]) != str(json["AP"]["IPAddress"]) || str(reponseCMD["Rgx"]["Subnetmask"]) != str(json["AP"]["Subnet"])
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle l'adresse IP & le masque de sous-réseau du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
            tasmota.cmd(string.format("Backlog RgxAddress %s; RgxSubnet %s", json["AP"]["IPAddress"], json["AP"]["Subnet"]), boolMute)
        end

        # Etat du point d'accès
        if (configGlobal.testeParam("RgxState", json["activation"], "str"))
            tasmota.cmd(string.format("RgxState %s", json["activation"]), boolMute)
            rangeExtenderFonctions.log("CONFIG_EXTENDER: Regle l'état d'activation du point d'accès Range Extender !", LOG_LEVEL_DEBUG)
        end
    end
end
rangeExtenderFonctions.configExtenderByJson = rangeExtenderFonctions_configExtenderByJson

# Règles sur changement d'état lors du démarrage de Tasmota
def rangeExtenderFonctions_changementEtatDemarrage(value, trigger, msg)
    import persist
    import string
    import json

    var rangeExtender

	# Test
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: -------------------- RangeExtender changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

    if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    tasmota.yield()

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
        elif msg["WIFI"].find("Disonnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            # Uniquement si c'est un Point d'accès Range Extender
            # Lance le routage TCP pour les différents esclaves connus
            if serveur["rangeExtender"].find("id", 99) == 0
                tasmota.cmd("RoutageRangeExtender", boolMute)
            end
        elif msg[trigger].find("Save", 0)
        end
    # Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
	# Se déclenche un évènement sur les heures et la synchronisation NTP (si activé)
    elif (trigger == "Time")
        # A chaque fois que le NTP est initialisé et l'heure synchronisée
        if type(msg["Time"]) == "instance"
            if msg["Time"].find("Initialized", 0)
            # A chaque heure, quand le système NTP est synchronisé
            elif msg["Time"].find("Set", 0)
            end
        end
    end
end
rangeExtenderFonctions.changementEtatDemarrage = rangeExtenderFonctions_changementEtatDemarrage

# Se charge d'afficher le bouton de lien vers lapage webUI des clients Ranextender connectés
# Fonction inutilisée
def rangeExtenderFonctions_afficheBoutonsModulesEsclaves()
    import webserver
    import string
    import gestionFileFolder
    import json

    import re

    var rgxClients = {}
    var i = 1
    var patternEsclave = re.compile('^esclave[0-9]+$')

    # Lit le fichier json (absent ou vide -> table vide, au lieu d'un .keys() sur nil)
    var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
    if (paramDiscovery == nil)    paramDiscovery = {}    end

    tasmota.yield()

    # Ajoute autant de boutons que de modules connectés au RangeExtender
    # Uniquement si c'est un Point d'accès Range Extender
    if serveur["rangeExtender"].find("id", 99) == 0
        rangeExtenderFonctions.log("RANGE_EXTENDER: Affichage du bouton !", LOG_LEVEL_DEBUG)

        # Convention : cmd avec boolMute + acces JSON garde (une cmd peut renvoyer nil
        # ou un dict sans la cle) pour ne pas planter sur .size().
        var _reponseRgx = tasmota.cmd("RgxClients", boolMute)
        rgxClients = _reponseRgx ? _reponseRgx.find("RgxClients") : nil

        # Si au moins 1 client est connecté
        if (rgxClients != nil && rgxClients.size() > 0)
            # webserver.content_send("<hr>")
            for mac: rgxClients.keys()
                for cle: paramDiscovery.keys()
                    tasmota.yield()

                    # Ne retient que les fiches d'esclaves (evite le maitre). Une fiche MAC porte aussi
                    # 'config', 'sensors' (maps) et 'lwt' (chaine) : appeler .find sur 'lwt' levait
                    # une exception qui interrompait l'affichage des boutons (corrige le 2026-09-30).
                    if (!isinstance(paramDiscovery[cle], map))    continue    end
                    for item: paramDiscovery[cle].keys()
                        if (patternEsclave.match(item) != nil && isinstance(paramDiscovery[cle][item], map))
                            var adresseMac = string.replace(paramDiscovery[cle][item].find("adresseMAC", ""), ":", "")
                            var etat = paramDiscovery[cle].find("lwt", "Offline")

                            if (adresseMac == mac && etat == "Online")
                                # .find : un module sans RangeExtender (pas de bloc) peut etre client du point d'acces
                                var routagePort = paramDiscovery[cle][item].find("rangeExtender", {}).find("routagePort", 8080)
                                var ipEsclave = str(paramDiscovery[cle][item].find("IPAddress", "192.168.4.1"))
                                var url = "http://" + serveur["hostname"] + ".local:" + str(routagePort)
                                var titre = str(paramDiscovery[cle][item].find("nom", item))

                                # Active le routage NAPT si pas encore fait (redirige ne rappelle pas
                                # RgxPort pour une redirection deja posee : sinon doublon a chaque affichage)
                                rangeExtenderFonctions.redirige(routagePort, ipEsclave)

                                # Ouverture de la page dans un nouvel onglet
                                var btn = "<p></p><button class=\"button bgrn\" id=\"btn_test\" onclick=\"setTimeout(() => {window&#46;open(\'" + url + "\');}, 1000);\">" + titre + "</button>"
                                webserver.content_send(btn)
                            end
                        end
                    end
                end
            end
        end
    end
end
rangeExtenderFonctions.afficheBoutonsModulesEsclaves = rangeExtenderFonctions_afficheBoutonsModulesEsclaves

# Retourne le module lors de l'importation
return rangeExtenderFonctions