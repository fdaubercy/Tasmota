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
            "redirections": {}        # maitre : redirections NAPT deja posees, port -> IP (voir redirige)
        }
    end
    return global._etatRangeExtenderFonctions
end
rangeExtenderFonctions.etat = rangeExtenderFonctions_etat


def rangeExtenderFonctions_log(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "rangeExtender")
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
    logFonctions.log(string.format("RANGE_EXTENDER: redirection NAPT %i -> %s:80 REFUSEE (table de 10 redirections pleine ? redemarrer le maitre)",
                      port, ip), LOG_LEVEL_ERREUR, "rangeExtender")
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
        return []     # aucune sous-commande (les logs se reglent avec ReglageLog)
    end
    return nil
end
rangeExtenderFonctions.aideReglageRangeExtender = rangeExtenderFonctions_aideReglageRangeExtender

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

    logFonctions.log("REGLAGE_RANGE_EXTENDER: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS, "rangeExtender")
    if (parametres != false)
        if (parametres.size() > 0)	logFonctions.log("REGLAGE_RANGE_EXTENDER: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS, "rangeExtender")	end
        if (parametres.size() > 1)	logFonctions.log("REGLAGE_RANGE_EXTENDER: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS, "rangeExtender")	end
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd["ReglageRangeExtender"]["resultat"] = "OK"
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
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: -------------------- RangeExtender changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	rangeExtenderFonctions.log("RANGE_EXTENDER_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

    if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    tasmota.yield()

	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    if (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            # Uniquement si c'est un Point d'accès Range Extender
            # Lance le routage TCP pour les différents esclaves connus
            if serveur["rangeExtender"].find("id", 99) == 0
                tasmota.cmd("RoutageRangeExtender", boolMute)
            end
        elif msg[trigger].find("Save", 0)
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

# Maitre RangeExtender : affiche sur SA page d'accueil une section "Leds mirroring" par esclave
# ModBus equipe d'un ruban WS2812, pilote par un relai virtuel 'ModBus_TasmotaSlaveModBusN' (type 1376).
# Pourquoi (2026-10-11) : un esclave est derriere le NAPT du maitre (192.168.4.x), injoignable
# depuis le reseau maison. Sa page /leds (ledsPanelFonctions) est servie sur son port 80 avec des
# URL relatives : elle passe par la redirection <maitre>:<routagePort> -> <esclave>:80 qui sert
# deja sa page web, sans redirection supplementaire, quel que soit le nombre d'esclaves.
# Un esclave hors RangeExtender (sans routagePort) est vise directement par son IP.
# Une seule section par esclave, meme si plusieurs relais du maitre visent le meme ruban.
# Hypothese : ruban sur 1 rangee (le maitre ne connait pas le PixelHeight de l'esclave).
def rangeExtenderFonctions_afficheMiroirLedsEsclaves()
    import webserver
    import string
    import ledsPanelFonctions

    if (serveur.find("rangeExtender", {}).find("id", 99) != 0)    return    end
    if (!isinstance(drivers.find("ModBus", nil), map) || drivers["ModBus"].find("activation", "OFF") != "ON")    return    end
    var esclavesModbus = drivers["ModBus"].find("environnement", {}).find("TasmotaSlaveModBus", {})

    # Adresse par laquelle le navigateur a joint le maitre (IP ou nom .local), sans le port
    var hote = webserver.header("Host")
    hote = (hote != nil ? string.split(hote, ":")[0] : tasmota.wifi().find("ip", ""))

    var fiches = nil        # discovery.json lu une seule fois, et seulement si un ruban est a montrer
    var affiches = {}       # id ModBus des esclaves deja affiches

    for cleModule: modules.keys()
        if (!isinstance(modules[cleModule], map) || modules[cleModule].find("activation", "OFF") != "ON")    continue    end
        var relais = modules[cleModule].find("environnement", {}).find("relais", nil)
        if (!isinstance(relais, map))    continue    end

        for cleRLY: relais.keys()
            tasmota.yield()
            var relai = relais[cleRLY]
            if (!isinstance(relai, map) || relai.find("activation", "OFF") != "ON")    continue    end
            if (relai.find("type", 0) != 1376 || relai.find("nbLeds", 0) <= 1)    continue    end
            var virtuel = str(relai.find("virtuel", "OFF"))
            if (string.find(virtuel, "ModBus_TasmotaSlaveModBus") != 0)    continue    end
            var esclave = esclavesModbus.find(string.split(virtuel, "_")[1], nil)
            if (!isinstance(esclave, map) || esclave.find("activation", "OFF") != "ON")    continue    end
            var id = int(esclave.find("id", 0))
            if (id <= 0 || affiches.contains(id))    continue    end

            # Fiche discovery de l'esclave (meme lecture que envoiMsgModbusUDP)
            if (fiches == nil)
                import modbusFonctions
                fiches = modbusFonctions.fichesModbus()
            end
            var ficheEsclave = nil
            for fiche: fiches
                if (fiche["ModBus"].find("id", -1) == id)    ficheEsclave = fiche    break    end
            end
            var ip = (ficheEsclave != nil ? str(ficheEsclave.find("IPAddress", "")) : "")
            if (ip == "")
                rangeExtenderFonctions.log(string.format("RANGE_EXTENDER: miroir LEDs '%s' : IP de l'esclave ModBus %i absente de discovery.json !", str(relai.find("nom", cleRLY)), id), LOG_LEVEL_DEBUG)
                continue
            end

            # Par la redirection du maitre si l'esclave est client de son point d'acces, sinon en direct
            var url = "http://" + ip + "/leds"
            var rangeExtender = ficheEsclave.find("rangeExtender", {})
            var routagePort = isinstance(rangeExtender, map) ? rangeExtender.find("routagePort", nil) : nil
            if (routagePort != nil)
                if (!rangeExtenderFonctions.redirige(routagePort, ip))    continue    end
                url = string.format("http://%s:%i/leds", hote, int(routagePort))
            end

            affiches[id] = true
            ledsPanelFonctions.afficheSection(id, "Leds mirroring " + str(relai.find("nom", cleRLY)), url, int(relai["nbLeds"]), 1)
        end
    end
end
rangeExtenderFonctions.afficheMiroirLedsEsclaves = rangeExtenderFonctions_afficheMiroirLedsEsclaves

# Retourne le module lors de l'importation
return rangeExtenderFonctions