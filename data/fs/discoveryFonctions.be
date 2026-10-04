#@ solidify:discoveryFonctions
var discoveryFonctions = module("discoveryFonctions")

# Etat modifiable du module, dans une GLOBALE (solidification 2026-09-27). Un module
# solidifie est constant (en flash) : y ecrire leve "'module' value has no writable
# attribute", et ses listes sont figees. La map est creee au premier appel avec les
# valeurs de depart qu'avaient les anciens attributs du module.
def discoveryFonctions_etat()
    import global
    if (global._etatDiscoveryFonctions == nil)
        global._etatDiscoveryFonctions = {}
    end
    return global._etatDiscoveryFonctions
end
discoveryFonctions.etat = discoveryFonctions_etat


def discoveryFonctions_log(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "discovery")
end
discoveryFonctions.log = discoveryFonctions_log

# Role de CE module dans la decouverte, tire du _persist.json (serveur['udp']['id']) :
# 0 -> 'maitre', N > 0 -> 'esclaveN'. C'est la cle sous laquelle il range et publie sa fiche.
def discoveryFonctions_roleLocal()
    import string

    var id = serveur["udp"].find("id", 99)
    if (id > 0)         return "esclave" + str(id)
    elif (id == 0)      return "maitre"
    end
    # Dernier nombre de l'adresse IP locale du module Tasmota
    return "module" + string.split(serveur["IP"]["IPAddress"], ".")[-1]
end
discoveryFonctions.roleLocal = discoveryFonctions_roleLocal

# Aide de la commande ReglageDiscovery, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def discoveryFonctions_aideReglageDiscovery(sujet)
    import string
    if (sujet == nil)
        return []     # aucune sous-commande (les logs se reglent avec ReglageLog)
    end
    return nil
end
discoveryFonctions.aideReglageDiscovery = discoveryFonctions_aideReglageDiscovery

def discoveryFonctions_reglageDiscovery(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions

    if diversFonctions.traiteAide("ReglageDiscovery", payload, discoveryFonctions.aideReglageDiscovery, true)    return    end

    var fonction = false
    var parametres = []                # liste vide (et non false) : parametres.size() plus bas
    var reponse_cmnd = "ReglageDiscovery: "
    
    # Test   
    discoveryFonctions.log("REGLAGE_DISCOVERY: -------------------- ReglageDiscovery -------------------", LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("REGLAGE_DISCOVERY: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("REGLAGE_DISCOVERY: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("REGLAGE_DISCOVERY: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("REGLAGE_DISCOVERY: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    discoveryFonctions.log("REGLAGE_DISCOVERY: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres.size() > 0)	discoveryFonctions.log("REGLAGE_DISCOVERY: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
    if (parametres.size() > 1)	discoveryFonctions.log("REGLAGE_DISCOVERY: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd += "OK"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
discoveryFonctions.reglageDiscovery = discoveryFonctions_reglageDiscovery

# Règles sur changement d'état lors du démarrage de Tasmota
def discoveryFonctions_changementEtatDemarrage(value, trigger, msg)
    import persist
    import string
    import json
    import mqtt
    import gestionFileFolder

    # Test
    discoveryFonctions.log("DISCOVERY_CHGT_ETAT_DEMARRAGE: -------------------- Discovery changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
    discoveryFonctions.log("DISCOVERY_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
    discoveryFonctions.log("DISCOVERY_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
    discoveryFonctions.log("DISCOVERY_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

    if (type(value)) == "instance"
        for cle: value.keys()
            value = value[cle]
        end
    end

    tasmota.yield()

    # Lorsque la connexion Wi-Fi est change
    if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
            var boolJsonModifie = false

            # Enregistre adresse MAC en json persist
            var status = tasmota.cmd("Status 5", boolMute)
            if (serveur.find("adresseMAC", "00:00:00:00:00:00") != status["StatusNET"]["Mac"])
                serveur["adresseMAC"] = tasmota.cmd("Status 5", boolMute)["StatusNET"]["Mac"]
                persist.serveur = serveur
                persist.save()
            end

            # Prépare le json à envoyer aux autres modules pour les fonction Discovery
            var data = {}
            data.insert(string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), {})

            var item = discoveryFonctions.roleLocal()

            var jsonData = data[string.replace(serveur["adresseMAC"], ":", "")]

            jsonData.insert(item, {})

            jsonData[item].insert("id", serveur["udp"]["id"])
            jsonData[item].insert("nom", serveur["nom"])

            tasmota.yield()

            jsonData[item].insert("IPAddress", status["StatusNET"]["IPAddress"])
            jsonData[item].insert("adresseMAC", status["StatusNET"]["Mac"])
            jsonData[item].insert("host", status["StatusNET"]["Hostname"] + ".local")
            jsonData[item].insert("topic", serveur["mqtt"]["topic"])
            # Groupe MQTT (2026-09-30) : la decouverte ecoute TOUT le broker (toutes les pieces).
            # Les lecteurs qui cherchent un module par son id ModBus (modbusFonctions.fichesModbus)
            # ne retiennent que les fiches de LEUR groupe, pour ne pas confondre deux esclaves
            # de meme id installes dans deux pieces.
            jsonData[item].insert("groupTopic", serveur["mqtt"].find("groupTopic1", ""))
            jsonData[item].insert("typeReglageHeure", diverses["fuseauHoraire"].find("typeReglageHeure", "NTP"))

            # Si c'est un module RangeExtender (maitre ou esclave)
            if (serveur["rangeExtender"].find("activation", "OFF") == "ON")
                jsonData[item].insert("typeConnection", "RangeExtender")

                jsonData[item].insert("rangeExtender", {})
                jsonData[item]["rangeExtender"].insert("activation", serveur["rangeExtender"]["activation"])
                jsonData[item]["rangeExtender"].insert("id", serveur["rangeExtender"]["id"])
                jsonData[item]["rangeExtender"].insert("routagePort", 8080 + serveur["rangeExtender"]["id"] - 1)
                jsonData[item]["rangeExtender"].insert("ipMaitre", serveur["rangeExtender"].find("ipMaitre", ""))
            else jsonData[item].insert("typeConnection", "WiFiClassique")
            end

            # Si c'est un module ModBus (maitre ou esclave)
            if (drivers["ModBus"].find("activation", "OFF") == "ON")
                jsonData[item].insert("ModBus", {})
                jsonData[item]["ModBus"].insert("activation", drivers["ModBus"]["activation"])
                jsonData[item]["ModBus"].insert("id", drivers["ModBus"]["id"])

                if (drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON")
                    jsonData[item]["ModBus"].insert("Serial", {})

                    jsonData[item]["ModBus"]["Serial"].insert("activation", drivers["ModBus"]["typeComm"].find("Serial", "OFF"))
                    jsonData[item]["ModBus"]["Serial"].insert("timeoutReponse", drivers["ModBus"].find("timeoutReponse", 3000))
                    jsonData[item]["ModBus"]["Serial"].insert("debit", drivers["ModBus"].find("debit", 9600))
                    jsonData[item]["ModBus"]["Serial"].insert("mode", drivers["ModBus"].find("mode", "8N1"))
                end

                if (drivers["ModBus"]["typeComm"].find("TCP", "OFF") == "ON")
                    jsonData[item]["ModBus"].insert("TCP", {})

                    jsonData[item]["ModBus"]["TCP"].insert("activation", drivers["ModBus"]["typeComm"].find("TCP", "OFF"))
                    jsonData[item]["ModBus"]["TCP"].insert("port", 502)
                    jsonData[item]["ModBus"]["TCP"].insert("IPAddress", status["StatusNET"]["IPAddress"])
                end

                if (drivers["ModBus"]["typeComm"].find("UDP", "OFF") == "ON")
                    jsonData[item]["ModBus"].insert("UDP", {})
                    jsonData[item]["ModBus"]["UDP"].insert("activation", drivers["ModBus"]["typeComm"].find("UDP", "OFF"))
                    jsonData[item]["ModBus"]["UDP"].insert("IPAddress", status["StatusNET"]["IPAddress"])
                end

                if (drivers["ModBus"]["typeComm"].find("MQTT", "OFF") == "ON")
                    jsonData[item]["ModBus"].insert("MQTT", {})
                    jsonData[item]["ModBus"]["MQTT"].insert("activation", drivers["ModBus"]["typeComm"].find("MQTT", "OFF"))
                end
            end

            tasmota.yield()

            try
                # Compare ce json aux données enregistrées dans '/json/discovery.json'
                var jsonDiscovery = {}

                # Si fichier 'discovery.json' existe et n'est pas vide, charge les données pour comparer avec le json à envoyer
                if (gestionFileFolder.readFile("/json/discovery.json") != false && gestionFileFolder.readFile("/json/discovery.json") != "")
                    jsonDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
                end

                tasmota.yield()

                # Si l'adresse MAC est absente
                if (!jsonDiscovery.find(string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), false))
                    jsonDiscovery.insert(string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), jsonData)
                    boolJsonModifie = true
                else
                    # Si l'item existe déjà dans jsonDiscovery, on met à jour les données
                    if (jsonDiscovery[string.replace(serveur.find("adresseMAC", "000000000000"), ":", "")].find(item, false))
                        # Si les 2 json sont différents
                        if (jsonDiscovery[string.replace(serveur.find("adresseMAC", "000000000000"), ":", "")][item] != jsonData[item])
                            jsonDiscovery[string.replace(serveur.find("adresseMAC", "000000000000"), ":", "")][item] = jsonData[item]
                            boolJsonModifie = true
                        end
                    # Sinon, on ajoute le nouvel item
                    else
                        jsonDiscovery[string.replace(serveur.find("adresseMAC", "000000000000"), ":", "")].insert(item, jsonData[item])
                        boolJsonModifie = true
                    end
                end

                # Écriture du JSON mis à jour dans le fichier
                if (boolJsonModifie)    gestionFileFolder.writeFile("/json/discovery.json", json.dump(jsonDiscovery))   end

                # Décharge le json
                jsonDiscovery = {}
                jsonData = {}
            except .. as error, message
                discoveryFonctions.log(string.format("DISCOVERY_CHGT_ETAT_DEMARRAGE: %s --> %s", error, message), LOG_LEVEL_ERREUR)
            end
        elif msg["WIFI"].find("Disonnected", 0)
        end
    # Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
        elif msg[trigger].find("Save", 0)
        end
    # Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
            var item = discoveryFonctions.roleLocal()

            try
                # Compare ce json aux données enregistrées dans '/json/discovery.json'
                var jsonDiscovery = {}

                # Si fichier 'discovery.json' existe et n'est pas vide, charge les données pour comparer avec le json à envoyer
                if (gestionFileFolder.readFile("/json/discovery.json") != false && gestionFileFolder.readFile("/json/discovery.json") != "")
                    jsonDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))

                    # On publie le json modifié si c'est un esclave RangeExtender
                    mqtt.publish(string.format("tasmota/discovery/%s/%s", string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), item), json.dump(jsonDiscovery[string.replace(serveur.find("adresseMAC", "000000000000"), ":", "")][item]), true)
                end
            except .. as error, message
                discoveryFonctions.log(string.format("DISCOVERY_CHGT_ETAT_DEMARRAGE: %s --> %s", error, message), LOG_LEVEL_ERREUR)
            end
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
discoveryFonctions.changementEtatDemarrage = discoveryFonctions_changementEtatDemarrage

# récupère les données MQTT reçues
# pour les messages liés à la découverte des modules Tasmota sur le réseau local
def discoveryFonctions_mqtt_discovery(topic, idx, data, databytes)
    import gestionFileFolder
    import json
    import string
    import mqtt
    import re

    # Test
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: -------------------- Discovery mqtt_discovery -------------------", LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: topic=" + str(topic), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: data=" + str(data), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: databytes=" + str(databytes), LOG_LEVEL_DEBUG_PLUS)

    # Uniquementpour discovery
    if (string.find(topic, "tasmota/discovery/") == -1)
        return false
    end

    # Découpe le topic MQTT
    var topicParts = string.split(topic, "/")
    var typeData = topicParts[string.count(topic, "/")]
    var item = topicParts[string.count(topic, "/") - 1]
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: typeData=" + typeData, LOG_LEVEL_DEBUG_PLUS)

    # Fiche perimee : un role (maitre/esclaveN/moduleN) publie sous NOTRE MAC qui n'est pas
    # notre role actuel. Cas reel (2026-10-03) : carte reaffectee de SERVEUR-RLY-CAVE (maitre)
    # en CAPTEURS-CUVE (esclave2) ; le broker gardait l'ancienne fiche 'maitre' retenue,
    # rangee a chaque reconnexion dans discovery.json puis annoncee au maitre par ImAlive.
    # -> on efface le message retenu sur le broker (publication vide retenue).
    var effacement = (data == nil || size(data) == 0)
    var macLocale = string.toupper(string.replace(serveur.find("adresseMAC", ""), ":", ""))
    var perimee = (string.toupper(item) == macLocale && typeData != discoveryFonctions.roleLocal() &&
                   re.compile('^(maitre|esclave[0-9]+|module[0-9]+)$').match(typeData) != nil)
    if (perimee && !effacement)
        logFonctions.log("DISCOVERY_MQTT_DATA: Fiche '" + typeData + "' perimee sous notre MAC (role actuel '" + discoveryFonctions.roleLocal() + "') : effacement sur le broker", LOG_LEVEL_INFO, "discovery")
        mqtt.publish(topic, "", true)
    end

    # Fiche perimee ou message d'effacement (charge vide, recu par TOUS les modules) :
    # retire l'entree de discovery.json au lieu d'y ranger nil
    if (perimee || effacement)
        try
            var fichier = gestionFileFolder.readFile("/json/discovery.json")
            var jsonEfface = (fichier != false && fichier != "") ? json.load(fichier) : nil
            if (isinstance(jsonEfface, map) && isinstance(jsonEfface.find(item), map) && jsonEfface[item].contains(typeData))
                jsonEfface[item].remove(typeData)
                gestionFileFolder.writeFile("/json/discovery.json", json.dump(jsonEfface))
                discoveryFonctions.log("DISCOVERY_MQTT_DATA: '" + typeData + "' de " + item + " retire de discovery.json", LOG_LEVEL_DEBUG_PLUS)
            end
        except .. as error, message
            discoveryFonctions.log(string.format("DISCOVERY_MQTT_DATA: %s --> %s", error, message), LOG_LEVEL_ERREUR)
        end
        return true
    end

    data = json.load(data)

    # Prépare le json
    var paramJSON = {}
    var boolJsonModifie = false
    var jsonDiscovery = {}

    paramJSON.insert(item, {})
    paramJSON[item].insert(typeData, data)

    # Modifie le json
    if (typeData == "config")   discoveryFonctions.log("DISCOVERY_MQTT_DATA: hostname=" + data['dn'], LOG_LEVEL_DEBUG_PLUS)     end

    # Si c'est le json discovery pour le module en question
    try
        # Si fichier '/json/discovery.json' existe et n'est pas vide, charge les données pour comparer avec le json à envoyer
        # Ouvre le fichier enregistré pour la découverte des modules Tasmota sur le réseau local
        if (gestionFileFolder.readFile("/json/discovery.json") != false && gestionFileFolder.readFile("/json/discovery.json") != "")
            jsonDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
        end

        tasmota.yield()

        # Compare ce json aux données enregistrées dans 'discovery.json'
        # Cherche l'adresse MAC dans le json enregistré
        # Si adresse MAC présente
        if (jsonDiscovery.find(item, false))
            # Si typeData présente: la modifie
            if (jsonDiscovery[item].find(typeData, false))
                jsonDiscovery[item][typeData] = paramJSON[item][typeData]
            # Si typeData absente: la crée
            else    
                jsonDiscovery[item].insert(typeData, paramJSON[item][typeData])
            end
        # Si adresse MAC absente l'insert
        else 
            jsonDiscovery.insert(item, paramJSON[item])
        end

        # Par défaut, on considère que le module est en ligne à la réception de son message de découverte MQTT
        if (typeData == "config")   jsonDiscovery[item].insert("lwt", "Online")     end

        # Recherche une device avec une autre adresse MAC portant le même hostname / devicename
        if (typeData == "config")
            for cle: jsonDiscovery.keys()
                if (jsonDiscovery[cle].find("config", false))
                    if (cle != item)
                        if (jsonDiscovery[cle]["config"]["hn"] == paramJSON[item]["config"]["hn"] && jsonDiscovery[cle]["config"]["dn"] == paramJSON[item]["config"]["dn"])
                            jsonDiscovery.remove(cle)
                        end
                    end
                end
            end
        end

        tasmota.yield()

        # Le met à jour si différent
        if (jsonDiscovery != json.load(gestionFileFolder.readFile("/json/discovery.json")))
            gestionFileFolder.writeFile("/json/discovery.json", json.dump(jsonDiscovery))
        end

        # Décharge le json
        jsonDiscovery = {}
        paramJSON = {}

        return true
    except .. as error, message
        discoveryFonctions.log(string.format("DISCOVERY_MQTT_DATA: %s --> %s", error, message), LOG_LEVEL_ERREUR)
    end
end
discoveryFonctions.mqtt_discovery = discoveryFonctions_mqtt_discovery


# récupère les données MQTT reçues
# pour les messages LWT sur le réseau local
def discoveryFonctions_mqtt_lwt(topic, idx, data, databytes)
    import json
    import string
    import mqtt
    import re
    import gestionFileFolder

    # Test
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: -------------------- Discovery mqtt_lwt -------------------", LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: topic=" + str(topic), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: data=" + str(data), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("DISCOVERY_MQTT_DATA: databytes=" + str(databytes), LOG_LEVEL_DEBUG_PLUS)

    # Uniquementpour discovery
    if (string.find(topic, "LWT") == -1)
        return false
    end

    var boolJsonModifie = false
    # Découpe le topic MQTT
    # var m = re.match("^tele/(.+)/LWT$", topic)
    var m = re.match("^[^/]+/(.+)/LWT$", topic)
    var topicLWT = ""
    if (m)  topicLWT = m[1]     end

    try
        # Charge 'json/discovery.json'
        var jsonDiscovery = {}

        # Si fichier '/json/discovery.json' existe et n'est pas vide, charge les données pour comparer avec le json à envoyer
        if (gestionFileFolder.readFile("/json/discovery.json") != false && gestionFileFolder.readFile("/json/discovery.json") != "")
            jsonDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
        end

        tasmota.yield()

        # Parcours le json discovery pour trouver le module Tasmota correspondant au topic du message LWT
        for item: jsonDiscovery.keys()
            if (jsonDiscovery[item].find("config", false))
                if (jsonDiscovery[item]["config"]["t"] == topicLWT)
                    # Si LWT existe dans le json discovery, le met à jour, sinon l'ajoute
                    if (jsonDiscovery[item].find("lwt", false))
                        if (jsonDiscovery[item]["lwt"] != data)
                            jsonDiscovery[item]["lwt"] = data
                            boolJsonModifie = true
                        end
                    else
                        jsonDiscovery[item].insert("lwt", data)
                        boolJsonModifie = true
                    end

                    break
                end
            end
        end
        tasmota.yield()

        # Le met à jour si différent
        if (boolJsonModifie)    gestionFileFolder.writeFile("/json/discovery.json", json.dump(jsonDiscovery))   end
        tasmota.yield()

        jsonDiscovery = {}
        return true
    except .. as error, message
        discoveryFonctions.log(string.format("DISCOVERY_MQTT_LWT: %s --> %s", error, message), LOG_LEVEL_ERREUR)
    end
end
discoveryFonctions.mqtt_lwt = discoveryFonctions_mqtt_lwt

# Gestion de l'affichage de la page des modules découverts
def discoveryFonctions_affichePageDiscovery()
    import webserver
    import gestionFileFolder
    import json
    import string
    import re

    # Test
    discoveryFonctions.log("AFFICHE_DISCOVERY: -------------------- controleDiscovery affichePageDiscovery -------------------", LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("AFFICHE_DISCOVERY: Referer = " +  (webserver.header("Referer") != nil ? webserver.header("Referer") : ""), LOG_LEVEL_DEBUG_PLUS)
    discoveryFonctions.log("AFFICHE_DISCOVERY: Host = " + webserver.header("Host"), LOG_LEVEL_DEBUG_PLUS)

    var titreHTML = "Modules Tasmotas connectés au réseau local"
    var url_host = webserver.header("Host")
    var typeURL = "local"
    var i = 0
    var portLocal = 80
    var portDistant = 10000

    # Détermine si c'est une connection locale ou distante
    # Connexion en locale par l'IP
    if (string.find(url_host, "192.168.0.") > -1)
        typeURL = "local"
    # Connexion en locale par le nom de domaine
    elif (string.find(url_host, ".local") > -1)
        typeURL = "localDNS"
    # Connexion distante par le nom de domaine de la freebox
    elif (string.find(url_host, ".freeboxos.fr") > -1)
        typeURL = "freeboxDNS"
    # Connexion par le RangeExtender
    elif (string.find(url_host, "192.168.4.") > -1)
        typeURL = "rangeExtender"
    end
    discoveryFonctions.log("AFFICHE_DISCOVERY: type de connexion: = " + typeURL, LOG_LEVEL_DEBUG_PLUS)

    # Démarrage la page
    webserver.content_start(titreHTML)
    webserver.content_send_style(gestionFileFolder.readFile("/sd/css/main.css"))

    try
        # On parcours le fichier
        var jsonDiscovery = {}
        if (gestionFileFolder.readFile("/json/discovery.json") != false && gestionFileFolder.readFile("/json/discovery.json") != "")
            jsonDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))

            # Titre de la page
            webserver.content_send("<div style=\"padding:0px 5px;text-align:center;\"><h3><hr>Modules Tasmota connectés <br/>au réseau local<hr></h3></div>")

            var IP = ""
            var titre = ""
            var colorBTN = "bgrn"

            discoveryFonctions.log("AFFICHE_DISCOVERY: Parcoure les modules Tasmota enregistrés sur le réseau local !", LOG_LEVEL_DEBUG_PLUS)
            for item: jsonDiscovery.keys()
                # Une entree sans bloc 'config' (module jamais vu par la decouverte MQTT native,
                # ou ancienne fiche ImAlive rangee a la racine) n'a ni nom ni IP a afficher :
                # on la saute. L'acces direct levait une exception qui tronquait la page (2026-09-30).
                if (!isinstance(jsonDiscovery[item], map) || !isinstance(jsonDiscovery[item].find("config", nil), map))
                    discoveryFonctions.log(f"AFFICHE_DISCOVERY: - Entree '{item:s}' sans bloc 'config', ignoree", LOG_LEVEL_DEBUG_PLUS)
                    continue
                end

                titre = jsonDiscovery[item]['config']['dn']
                discoveryFonctions.log(f"AFFICHE_DISCOVERY: - Pour le module Tasmota '{titre:s}':", LOG_LEVEL_DEBUG_PLUS)
                colorBTN = "bgrn"
                i = i + 1

                portDistant = 10000 + int(string.split(jsonDiscovery[item]["config"]["ip"], ".")[3])            # portDistant = 10000 + last octet of local IP
                portLocal = 80

                if (typeURL == "local")
                    IP = jsonDiscovery[item]["config"]["ip"]
                elif (typeURL == "localDNS")
                    IP = jsonDiscovery[item]["config"]["hn"] + ".local"
                elif (typeURL == "freeboxDNS")
                    IP = string.split(url_host, ":")[0]
                end

                # Teste s'il s'agit d'un module RangeExtender
                var pattern = re.compile('^(maitre|esclave[0-9]+)$')

                for role: jsonDiscovery[item].keys()
                    if (pattern.match(role) != nil)
                        if (jsonDiscovery[item][role].find("rangeExtender", false))
                            discoveryFonctions.log(f"AFFICHE_DISCOVERY:\t * RangeExtender existant !", LOG_LEVEL_DEBUG_PLUS)
                            # Si esclave RangeExtender (id > 0)
                            if (jsonDiscovery[item][role]["rangeExtender"].find("activation", "OFF") == "ON" && jsonDiscovery[item][role]["rangeExtender"].find("id", 0) > 0)
                                discoveryFonctions.log(f'AFFICHE_DISCOVERY:\t * RangeExtender activé (id = {jsonDiscovery[item][role]["rangeExtender"].find("id", 0):i})', LOG_LEVEL_DEBUG_PLUS)

                                portLocal = jsonDiscovery[item][role]["rangeExtender"].find("routagePort", 8080)
                                # ipMaitre est vide tant que l'esclave n'a pas recu 'ReglageUDP ipMaitre' du
                                # maitre : l'indexation [3] levait alors une exception qui tronquait la page.
                                var ipMaitre = str(jsonDiscovery[item][role]["rangeExtender"].find("ipMaitre", ""))
                                if (size(string.split(ipMaitre, ".")) == 4)
                                    portDistant = 10000 + int(string.split(ipMaitre, ".")[3]) + 8080 + jsonDiscovery[item][role]["rangeExtender"].find("id", 0) - 1        # portDistant = 10000 + last octet of local IP + 8080 + id - 1
                                end

                                if (typeURL == "local")
                                    IP = (jsonDiscovery[item][role]["rangeExtender"].find("ipMaitre", "") == "" ? jsonDiscovery[item][role]["rangeExtender"]["ipMaitre"] : jsonDiscovery[item][role]["rangeExtender"]["ipMaitre"])
                                elif (typeURL == "freeboxDNS")
                                    IP = string.split(url_host, ":")[0]         #  IP = http://fdaubercy.freeboxos.fr
                                end

                                # Change la couleur des boutons des esclaves RangeExtender
                                colorBTN = "bgrey"

                                # Active le routage NAPT si pas encore fait (si id == 0, c'est le maître)
                                if (serveur["rangeExtender"].find("id", 99) == 0)
                                    import rangeExtenderFonctions
                                    discoveryFonctions.log(f'AFFICHE_DISCOVERY:\t * Active le routage NAPT vers le module {titre:s} ({jsonDiscovery[item][role]["IPAddress"]:s}) sur le port {portLocal:d} !', LOG_LEVEL_DEBUG)
                                    # Par rangeExtenderFonctions.redirige (2026-10-04) : un RgxPort a chaque affichage
                                    # de cette page creait un doublon dans la table NAPT de 10 cases du maitre
                                    rangeExtenderFonctions.redirige(portLocal, jsonDiscovery[item][role]["IPAddress"])
                                end
                            end
                        end
                    end
                end

                discoveryFonctions.log(f'AFFICHE_DISCOVERY:\t * IP = {IP:s}', LOG_LEVEL_DEBUG_PLUS)
                discoveryFonctions.log(f'AFFICHE_DISCOVERY:\t * portLocal = {portLocal:i}', LOG_LEVEL_DEBUG_PLUS)
                discoveryFonctions.log(f'AFFICHE_DISCOVERY:\t * portDistant = {portDistant:i}', LOG_LEVEL_DEBUG_PLUS)
                discoveryFonctions.log(f'AFFICHE_DISCOVERY:\t * couleur du bouton = {colorBTN:s}', LOG_LEVEL_DEBUG_PLUS)

                webserver.content_send(string.format("<p></p><form target='_blank'><button class='button %s' formaction='http://%s:%i'>%s</button></form>", 
                                                        colorBTN, IP, (typeURL == "freeboxDNS" ? portDistant : portLocal), titre))
            end

            # On ajoute les autres éléments de base d'une page Tasmota
            webserver.content_send("<div></div><p></p>")
            webserver.content_send("<form id=\"but1\" style=\"display:block;margin-top: 15px;\" action=\"mn\" method=\"get\"><button name=\"\">Tools</button></form> <p></p>")
            webserver.content_send("<form id=\"but2\" style=\"display:block;\" action=\".\" method=\"get\"><button name=\"\">Menu principal</button></form> <p></p>")

            #- end of web page -#
            webserver.content_stop()	
        end
    except .. as error, message
        discoveryFonctions.log(string.format("AFFICHE_DISCOVERY: %s --> %s", error, message), LOG_LEVEL_ERREUR)
    end
end
discoveryFonctions.affichePageDiscovery = discoveryFonctions_affichePageDiscovery

# Retourne le module lors de l'importation
return discoveryFonctions