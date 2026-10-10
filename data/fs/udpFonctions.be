#-
    - C'est un module partagé (singleton via module()) qui contient toute la logique métier UDP.
    - Variables globales du module :
        * udpReception[0/1] — sockets UDP ouverts (0=UniCast, 1=MultiCast)
        * port[0/1], ip[0/1], typeComm[0/1] — paramètres des deux canaux

    - Fonctions principales :
        Fonction	                    Rôle
        log()	                        Délègue à logFonctions.log (seuil de la cible "udp", réglé par ReglageLog)
        reglageUDP()	                Commande Tasmota ReglageUDP — dispatche vers les sous-fonctions selon le mot-clé reçu
        changementEtatDemarrage()	    Gère les événements système (System#Boot, Wifi#Connected, System#Save) : ouvre/ferme les sockets, déclenche l'envoi des paramètres
        envoiUDP()	                    Envoie un message UDP (UniCast vers une IP, ou MultiCast selon le rôle maître/esclave)
        lireUDP()	                    Lit un paquet UDP entrant, détecte si c'est une trame ModBus ou une commande TasmotaClient, et route vers le bon handler
        resetClientsConnectes()	        Marque tous les esclaves comme "Offline" dans /json/discovery.json (appelé au démarrage du maître)

    - Sous-commandes de ReglageUDP :
        Sous-commande	                Qui	            Effet
        envoiUniCast <ip> <msg>	        tous	        Envoie un message en unicast (test)
        envoiMultiCast <msg>	        tous	        Envoie un message en multicast
        forceEnvoiParams ON	            esclave	        Envoie SA fiche 'esclaveN' (discovery.json) au maître via MultiCast, puis replanifie via telePeriod
        ImAlive <json>	                maître	        Reçoit les paramètres d'un esclave, met à jour /json/discovery.json, et lui envoie l'heure + son IP en retour
        Timestamp <ts>	                esclave	        Met à jour l'horloge interne avec le timestamp reçu
        ipMaitre <ip>	                esclave	        Enregistre l'IP du maître en persistance

    - Flux de démarrage :
        * System#Boot → ouverture des sockets UDP
        * Esclave → envoie forceEnvoiParams ON → publie ses infos en MultiCast
        * Maître → reçoit ImAlive → répond avec l'heure et son IP
        * System#Save → fermeture des sockets

    - Cycle forceEnvoiParams → ImAlive (présentation esclave → maître), état au 2026-10-03
      En une phrase : toutes les telePeriod (300 s), un ESCLAVE (serveur.udp.id > 0) envoie par UDP sa
      « fiche d'identité » au MAITRE (id 0) ; le maître la range dans /json/discovery.json, lui renvoie
      l'heure et son IP, puis s'en sert pour le routage NAPT, la page /discovery et ModBus.

        ESCLAVE (ex. cuve, id 2)                                MAITRE (id 0)
        System#Boot -> ReglageUDP forceEnvoiParams ON
          1. lit SA fiche discovery.json[sa MAC]["esclave"+id]
          2. "tele/<topic>/ReglageUDP ImAlive {"esclaveN":{...}}"
          3. multicast 224.3.0.1:4000  -------------------->  CONTROLE_UDP.every_100ms -> lireUDP
          4. re-arme le timer "forceEnvoiParams"                -> tasmota.cmd("ReglageUDP ImAlive {...}")
                                                                -> discovery.json[MAC][role] = fiche ; [MAC]["lwt"] = "Online"
          Time <ts>             <-- multicast "Timestamp" ---  si la fiche reçue a typeReglageHeure == "UDP"
          persist ipMaitre      <-- multicast "ipMaitre"  ---  (topic tele/<groupTopic1>/ReglageUDP ...)

      1. Côté esclave
         * Déclenchement : changementEtatDemarrage (System#Boot, id > 0), puis timer NOMMÉ "forceEnvoiParams"
           ré-armé à chaque passage (remove_timer avant set_timer : une seule chaîne d'envois, même après
           des appels manuels — avant le 2026-10-03, chaque appel manuel en ajoutait une).
         * Collecte : la fiche est CONSTRUITE à la connexion Wi-Fi par discoveryFonctions.changementEtatDemarrage
           depuis le _persist.json (serveur, drivers.ModBus, diverses) + Status 5, et rangée sous
           discovery.json[MAC]["esclaveN"]. Champs : id, nom, topic, groupTopic, IPAddress, adresseMAC, host,
           typeReglageHeure, rangeExtender{activation, id, routagePort = 8080+id-1, ipMaitre},
           ModBus{id, Serial{...}, TCP{IPAddress, port}, UDP{...}}.
           forceEnvoiParams n'envoie QUE la clé "esclave" + serveur.udp.id (même règle que
           discoveryFonctions.roleLocal) ; fiche absente -> rien n'est envoyé.
         * Envoi : envoiUDP("MultiCast") -> 224.3.0.1:4000, message au format d'un topic MQTT.
      2. Côté maître
         * Réception : CONTROLE_UDP.every_100ms (controleUDP.be) -> lireUDP coupe au 1er espace
           (préfixe / topic / commande). Le maître accepte tous les topics ; un esclave, seulement son
           topic ou son groupTopic1. Puis tasmota.cmd(commande).
         * ImAlive (reglageUDP) : recolle le JSON coupé aux espaces (dès le découpage, log compris) ; exige UNE fiche portant une
           adresseMAC ; écrit discovery.json[MAC][role] et [MAC]["lwt"] = "Online". Le rôle annoncé
           n'est PAS confronté à l'id. Si typeReglageHeure == "UDP" (les esclaves ; un maître est en
           NTP ou RTC) : répond Timestamp + ipMaitre en multicast.
         * Contrepoids : resetClientsConnectes, une fois après telePeriod au démarrage, met tout 'Offline'.
      3. Ce que le maître fait de la table
         * rangeExtenderFonctions : boutons de la page d'accueil (RgxClients x fiches esclaveN 'Online') et
           commande RoutageRangeExtender -> 'RgxPort tcp, <routagePort>, <IP esclave>, 80'. Rôle 'maitre' ignoré.
         * discoveryFonctions.affichePageDiscovery : boutons de /discovery, port calculé depuis ipMaitre.
         * modbusFonctions.fichesModbus (fiches des AUTRES MAC du même groupTopic portant un bloc ModBus) :
           IP de l'esclave pour l'envoi ModBus UDP (id = 1er octet de la trame) ; clients ModBus TCP
           (ReglageModbus ImAlive ON).
      Pièges connus
         * Carte réaffectée (2026-10-03) : une fiche 'maitre' périmée, retenue sur le broker sous la MAC de
           l'esclave, était annoncée à la place d'esclaveN. Le maître la rangeait en 'maitre' (ignorée par
           le routage, prise pour l'id ModBus 0) et, typeReglageHeure valant 'NTP', ne renvoyait ni heure
           ni IP. Corrigé par : choix du rôle par l'id (forceEnvoiParams) + effacement des fiches périmées
           (discoveryFonctions.mqtt_discovery). Bancs : outils_docs/scripts_python/test_discovery.be §8-10.
         * La fiche n'est reconstruite qu'à la connexion Wi-Fi : un ipMaitre reçu n'y entre qu'à la
           reconnexion suivante (ImAlive et MQTT annoncent l'ancienne valeur d'ici là).
      Détail et tableaux : outils_docs/ANALYSE_BERRY_MODBUS_DISCOVERY.md §2.6.
-#

#@ solidify:udpFonctions
var udpFonctions = module("udpFonctions")

# Etat modifiable du module, dans une GLOBALE (solidification 2026-09-27). Un module
# solidifie est constant (en flash) : y ecrire leve "'module' value has no writable
# attribute", et ses listes sont figees. La map est creee au premier appel avec les
# valeurs de depart qu'avaient les anciens attributs du module.
def udpFonctions_etat()
    import global
    if (global._etatUdpFonctions == nil)
        global._etatUdpFonctions = {
            "udpReception": [nil, nil], # objets udp de reception [UniCast, MultiCast]
            "port": [0, 0],            # ports [UniCast, MultiCast]
            "typeComm": ["", ""],      # types de communication [UniCast, MultiCast]
            "ip": ["", ""]            # adresses [UniCast, MultiCast]
        }
    end
    return global._etatUdpFonctions
end
udpFonctions.etat = udpFonctions_etat


# # *************************************************
# # * ModBus Commandes 
# # *************************************************
# CMND_FEATURES
# CMND_FUNC_JSON
# CMND_FUNC_EVERY_SECOND
# CMND_FUNC_EVERY_100_MSECOND
# CMND_CLIENT_SEND
# CMND_PUBLISH_TELE
# CMND_EXECUTE_CMND

def udpFonctions_log(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "udp")
end
udpFonctions.log = udpFonctions_log

# Aide de la commande ReglageUDP, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def udpFonctions_aideReglageUDP(sujet)
    import string
    if (sujet == nil)
        return [
            ["envoiUniCast", "envoiUniCast <ip> <message>", "envoie un message UDP en unicast (test)"],
            ["envoiMultiCast", "envoiMultiCast <message>", "envoie un message UDP en multicast (test, RangeExtender)"],
            ["forceEnvoiParams", "forceEnvoiParams <ON|OFF|1|0>", "esclave : envoie sa fiche au maitre (interne, periodique)"],
            ["ImAlive", "ImAlive <json>", "maitre : recoit la fiche d'un esclave (interne, envoye par l'esclave)"],
            ["Timestamp", "Timestamp <secondes>", "esclave : regle l'heure (interne, envoye par le maitre)"],
            ["ipMaitre", "ipMaitre <ip>", "esclave : memorise l'IP du maitre (interne, envoye par le maitre)"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "ENVOIUNICAST")
        return ["Parametres : <ip> <message> (le message peut contenir des espaces).",
                "Envoie le message en UDP unicast a l'IP, sur le port UDP de la carte.",
                "Sert aux tests ; la reponse contient envoiMessage.",
                "Exemple : ReglageUDP envoiUniCast 192.168.0.43 Salut Ca gaz !"]
    elif (sujet == "ENVOIMULTICAST")
        return ["Parametre : <message> (un ou plusieurs mots ; absent -> erreur dans la reponse).",
                "N'envoie quelque chose que si le RangeExtender est active (ON) :",
                "esclave (id > 0) -> multicast 224.3.0.1 ; maitre (id = 0) -> via 192.168.4.1.",
                "Sinon : aucun envoi. Sert aux tests.",
                "Exemple : ReglageUDP envoiMultiCast Salut Ca gaz !"]
    elif (sujet == "FORCEENVOIPARAMS")
        return ["Parametre : ON ou 1 = envoie ; OFF ou 0 = n'envoie pas. Esclaves seulement (id > 0).",
                "Envoie au maitre (multicast) SA fiche 'esclaveN' de /json/discovery.json",
                "sous la forme 'ImAlive {json}', puis re-arme un timer de telePeriod secondes.",
                "Surtout INTERNE : lance au demarrage et par son propre timer.",
                "Exemple : ReglageUDP forceEnvoiParams ON"]
    elif (sujet == "IMALIVE")
        return ["Parametre : <json> = {\"esclaveN\": {... \"adresseMAC\": \"AA:BB:...\"}} (UNE fiche).",
                "Maitre seulement (id = 0) : range la fiche dans /json/discovery.json, marque",
                "l'esclave Online ; si typeReglageHeure = UDP, renvoie heure et IP du maitre.",
                "INTERNE : envoye par les esclaves, pas fait pour etre tape a la main.",
                "Un JSON sans adresse MAC est ignore."]
    elif (sujet == "TIMESTAMP")
        return ["Parametre : <secondes> = heure UTC (epoch Unix). Esclaves seulement (id > 0).",
                "Regle l'horloge de la carte (commande Time).",
                "INTERNE : envoye par le maitre apres un ImAlive (typeReglageHeure = UDP).",
                "Exemple : ReglageUDP Timestamp 1766072035"]
    elif (sujet == "IPMAITRE")
        return ["Parametre : <ip> = adresse IP du maitre. Esclaves seulement (id > 0).",
                "Memorise : serveur.rangeExtender.ipMaitre, avec persist.save immediat.",
                "INTERNE : envoye par le maitre apres un ImAlive (typeReglageHeure = UDP).",
                "Exemple : ReglageUDP ipMaitre 192.168.0.3"]
    end
    return nil
end
udpFonctions.aideReglageUDP = udpFonctions_aideReglageUDP

# exemples:
# ReglageUDP envoiUniCast 192.168.0.43 Salut Ca gaz ! OU ReglageUDP envoiUniCast 192.168.4.3 Salut Ca gaz !
# ReglageUDP envoiMultiCast Salut Ca gaz ! OU ReglageUDP envoiMultiCast 192.168.4.3 Salut Ca gaz !
# ReglageUDP forceEnvoiParams ON
# ReglageUDP Timestamp 1766072035
def udpFonctions_reglageUDP(cmd, idx, payload, payload_json)
    import string
    import json
    import mqtt
    import persist
    import gestionFileFolder
    import diversFonctions

    if diversFonctions.traiteAide("ReglageUDP", payload, udpFonctions.aideReglageUDP, true)    return    end

    var fonction = false
    var parametres = []
    var reponse_cmnd = {"ReglageUDP": {}}
    
    # Test   
    udpFonctions.log("REGLAGE_UDP: -------------------- reglageUDP -------------------", LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log("REGLAGE_UDP: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 2)
        fonction = parametres.pop(0)
        # ImAlive porte UN seul parametre, un JSON dont les valeurs contiennent des espaces
        # ("Capteurs de Cuve") : recolle avant le log, sinon parametre1/parametre2 montraient
        # un JSON coupe en deux (corrige le 2026-10-04 ; le traitement, lui, recollait deja).
        if (string.toupper(fonction) == "IMALIVE")    parametres = [parametres.concat(" ")]    end
    else fonction = payload
    end

    udpFonctions.log("REGLAGE_UDP: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
    if (parametres != false)
        if (parametres.size() > 0)	logFonctions.log("REGLAGE_UDP: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS, "udp")	end
        if (parametres.size() > 1)	logFonctions.log("REGLAGE_UDP: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS, "udp")	end
    end

    # Envoi de messages UDP UniCast sur l'IP principale du destinataire pour test
    if string.toupper(fonction) == string.toupper("envoiUniCast")
        udpFonctions.envoiUDP("UniCast", parametres[0], parametres[1])	# UniCast (Maitre ou Esclaves RangeExtender)
        udpFonctions.log(string.format("ReglageUDP: Données UDP UniCast envoyées à %s >>> %s", parametres[0], parametres[1]), LOG_LEVEL_DEBUG)

        reponse_cmnd["ReglageUDP"]["envoiMessage"] = str(parametres[1])
    # Envoi de messages UDP MultiCast pour test
    elif string.toupper(fonction) == string.toupper("envoiMultiCast")
        # Message = tous les mots apres la sous-commande (2026-10-04 : parametres[0] + " " +
        # parametres[1] levait une exception pour un message d'un seul mot)
        var message = parametres.concat(" ")
        if (message == "")
            reponse_cmnd["ReglageUDP"]["erreur"] = "message absent : ReglageUDP envoiMultiCast <message>"
        # Esclave RangeExtender (id > 0)
        elif (serveur["rangeExtender"].find("activation", "OFF") == "ON" && serveur["udp"]["id"] > 0)
            udpFonctions.envoiUDP("MultiCast", "", message)
            udpFonctions.log(string.format("ReglageUDP: Données UDP MultiCast envoyées >>> %s", message), LOG_LEVEL_DEBUG)
        # Maitre RangeExtender (id == 0)
        elif (serveur["rangeExtender"].find("activation", "OFF") == "ON" && serveur["udp"]["id"] == 0)
            udpFonctions.envoiUDP("MultiCast", "192.168.4.1", message)
            udpFonctions.log(string.format("ReglageUDP: Données UDP MultiCast envoyées >>> %s", message), LOG_LEVEL_DEBUG)
        end
        
        reponse_cmnd["ReglageUDP"]["envoiMessage"] = message
    # Force l'esclave à envoyer ses paramètres au maitre en UniCast UDP
    elif (string.toupper(fonction) == string.toupper("forceEnvoiParams") && serveur["udp"]["id"] > 0)
        try
            parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))

            if (parametres[0] == "ON")
                udpFonctions.log("REGLAGE_UDP: Force l'esclave UDP à envoyer ses paramètres au maitre !", LOG_LEVEL_DEBUG_PLUS)

                # L'esclave renvoie au maitre ses paramètres par UDP MultiCast
                var jsonData = json.load(gestionFileFolder.readFile("/json/discovery.json")).find(string.replace(serveur.find("adresseMAC", "000000000000"), ":", ""), {})
                # N'envoie QUE la fiche de son role actuel (persist : serveur.udp.id), comme
                # discoveryFonctions.roleLocal(). Corrige le 2026-10-03 : la 1re cle maitre|esclaveN
                # trouvee partait, et une fiche 'maitre' perimee (carte reaffectee) a ete annoncee
                # au maitre a la place de 'esclave2'. Fiche absente : rien n'est envoye (avant :
                # 'ImAlive {}', rejete par le maitre).
                var role = "esclave" + str(serveur["udp"]["id"])
                if (!isinstance(jsonData.find(role), map))
                    udpFonctions.log("REGLAGE_UDP: Fiche '" + role + "' absente de discovery.json : ImAlive non envoye !", LOG_LEVEL_DEBUG)
                else
                    var result = {}
                    result[role] = jsonData[role]

                    var message = string.format("tele/%s/%s %s %s", serveur["mqtt"]["topic"], "ReglageUDP", "ImAlive", json.dump(result))

                    # UDP Envoi Esclave -> Maitre
                    # udpFonctions.envoiUDP("UniCast", "192.168.0.43", message)	# UniCast
                    udpFonctions.envoiUDP("MultiCast", "", message)				# MultiCast
                end
            end
        except .. as e, m
            print('Erreur: ', e, " -> ", m)
        end

        # Timer NOMME : set_timer empile toujours un nouveau timer (tasmota_class.be:275), donc
        # chaque 'forceEnvoiParams ON' tape a la main ajoutait une chaine d'envois de plus.
        # On retire l'eventuel timer en attente avant de re-armer : une seule chaine a la fois.
        tasmota.remove_timer("forceEnvoiParams")
        tasmota.set_timer(diverses["telePeriod"] * 1000, def()  tasmota.cmd("ReglageUDP forceEnvoiParams ON", boolMute)     end, "forceEnvoiParams")
    # Récupère les paramètres de chaque esclave sous format json
    elif (string.toupper(fonction) == string.toupper("ImAlive") && serveur["udp"]["id"] == 0)
        # Les données avec des espaces sont coupées
        # Dans cette fonction on va les réunir
        var tmp = json.load(parametres.concat(" "))
        var device = ""
        var mac = ""

        # Le message porte UNE fiche : {"esclaveN": {..., "adresseMAC": "AA:BB:..."}}
        if (isinstance(tmp, map) && size(tmp) == 1)
            for item: tmp.keys()    device = item   end
            if (isinstance(tmp[device], map))
                mac = string.replace(str(tmp[device].find("adresseMAC", "")), ":", "")
            end
        end

        if (mac == "")
            udpFonctions.log("REGLAGE_UDP: ImAlive illisible ou sans adresse MAC, ignore : " + parametres.concat(" "), LOG_LEVEL_ERREUR)
        else
            var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
            if (paramDiscovery == nil)   paramDiscovery = {}      end

            # Range la fiche sous sa MAC : forme {MAC: {role: {...}}}, celle des 3 autres voies
            # d'ecriture (discoveryFonctions.be). Corrige le 2026-09-30 : elle etait rangee a la
            # RACINE sous son role ("esclave2"), ce qui cassait la page /discovery (acces direct
            # a ['config']) et placait le 'lwt' de resetClientsConnectes dans la fiche du role.
            if (!paramDiscovery.contains(mac) || !isinstance(paramDiscovery[mac], map))   paramDiscovery[mac] = {}   end
            paramDiscovery[mac][device] = tmp[device]

            # Un ImAlive recu prouve que l'esclave est joignable en UDP : c'est le pendant de
            # resetClientsConnectes (qui marque tout 'Offline'). Sans lui, un esclave RangeExtender
            # qui n'atteint pas le broker n'avait jamais de 'lwt' et n'etait jamais route.
            paramDiscovery[mac]["lwt"] = "Online"

            # Purge l'entree racine laissee par l'ancienne version
            if (paramDiscovery.contains(device))   paramDiscovery.remove(device)   end

            # Puis enregistre le fichier
            gestionFileFolder.writeFile("/json/discovery.json", json.dump(paramDiscovery))

            tasmota.yield()
            udpFonctions.log("REGLAGE_UDP: Le maitre UDP a reçu les paramètres de l'esclave '" + str(tmp[device].find("nom", device)) + "' !", LOG_LEVEL_DEBUG_PLUS)

            if (tmp[device].find("typeReglageHeure", "NTP") == "UDP")
                # Envoi la mise à jour de l'heure aux esclaves en MultiCast UDP
                var message = string.format("tele/%s/%s %s %i", serveur["mqtt"]["groupTopic1"], "ReglageUDP", "Timestamp", int(tasmota.rtc()["utc"]))
                udpFonctions.envoiUDP("MultiCast", "192.168.4.1", message)

                # Envoi deson adresse IP aux esclaves en MultiCast UDP
                message = string.format("tele/%s/%s %s %s", serveur["mqtt"]["groupTopic1"], "ReglageUDP", "ipMaitre", tasmota.cmd("Status 5", boolMute)["StatusNET"]["IPAddress"])
                udpFonctions.envoiUDP("MultiCast", "192.168.4.1", message)

                udpFonctions.log("REGLAGE_UDP: Envoi de la mise à jour de l'heure UDP aux esclaves & son adresse IP !", LOG_LEVEL_DEBUG_PLUS)
            end

            # Réponse série à la commande
            reponse_cmnd["ReglageUDP"][str(tmp[device].find("nom", device))] = "Online"
        end

    # L'esclave met à jour son horloge interne
    elif (string.toupper(fonction) == string.toupper("Timestamp") && serveur["udp"]["id"] > 0)
        try
            var timestamp = int(parametres[0])
            tasmota.cmd("Time " + str(timestamp), boolMute)
            tasmota.yield()

            udpFonctions.log("REGLAGE_UDP: L'esclave UDP a mis à jour son horloge interne avec le timestamp: " + str(timestamp), LOG_LEVEL_DEBUG_PLUS)
        except .. as e, m
            print('Erreur: ', e, " -> ", m)
        end
    # L'esclave enregistre l'adresse IP du maitre
    elif (string.toupper(fonction) == string.toupper("ipMaitre") && serveur["udp"]["id"] > 0)
        try
            serveur["rangeExtender"].insert("ipMaitre", parametres[0])
            persist.serveur = serveur
            persist.save()

            tasmota.yield()

            udpFonctions.log("REGLAGE_UDP: L'esclave UDP a enregistré l'adresse IP du maitre: " + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)
        except .. as e, m
            print('Erreur: ', e, " -> ", m)
        end

    end

    # Commande réussie
    # Réponse à la commande
    if (reponse_cmnd["ReglageUDP"].size() == 0)    reponse_cmnd["ReglageUDP"]["resultat"] = "OK"    end
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
udpFonctions.reglageUDP = udpFonctions_reglageUDP

# Règles sur changement d'état lors du démarrage de Tasmota
def udpFonctions_changementEtatDemarrage(value, trigger, msg, typeComm)
    import string
    import mqtt
    import json
    import persist

    var status

	# Test
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: -------------------- UDP changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
    udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: typeComm=" + str(typeComm), LOG_LEVEL_DEBUG_PLUS)		# msg=UniCast / msg = MultiCast

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    tasmota.yield()

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
            # Evite de répéter l'opération 2 fois
            if (string.toupper(typeComm) == string.toupper("MultiCast"))  return  end

            # Enregistre adresse MAC en json persist
            serveur["adresseMAC"] = tasmota.cmd("Status 5", boolMute)["StatusNET"]["Mac"]

            persist.serveur = serveur
            persist.save()
        elif msg["WIFI"].find("Disconnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
            if (string.toupper(typeComm) == string.toupper("UniCast"))
                udpFonctions.log(string.format("UDP_CHGT_ETAT_DEMARRAGE: Ouverture connexion UniCast sur le port %i: %s", 
                                                udpFonctions.etat()["port"][0], udpFonctions.etat()["udpReception"][0].begin(udpFonctions.etat()["ip"][0], udpFonctions.etat()["port"][0]) ? "OK" : "Echec"), LOG_LEVEL_DEBUG_PLUS)
            elif (string.toupper(typeComm) == string.toupper("MultiCast"))								
                udpFonctions.log(string.format("UDP_CHGT_ETAT_DEMARRAGE: Ouverture connexion MultiCast sur le port %i: %s", 
                                                udpFonctions.etat()["port"][1], udpFonctions.etat()["udpReception"][1].begin_multicast(udpFonctions.etat()["ip"][1], udpFonctions.etat()["port"][1]) ? "OK" : "Echec"), LOG_LEVEL_DEBUG_PLUS)
            end

            # Evite de répéter l'opération 2 fois
            if (string.toupper(typeComm) == string.toupper("MultiCast"))  return  end

            # Les esclaves envoient leurs paramètres par UDP MultiCast au Maitre / telePeriod
            # Le Maitre reset l'état de chaque esclave connus avant réception
            if (serveur["udp"]["id"] > 0)
                udpFonctions.log(string.format("UDP_CHGT_ETAT_DEMARRAGE: L'esclave n°%i envoie ses paramètres au maitre !", serveur["udp"]["id"]), LOG_LEVEL_DEBUG)
                # udpFonctions.resetClientsConnectes()
                tasmota.cmd("ReglageUDP forceEnvoiParams ON", boolMute)
            else 
                tasmota.set_timer(diverses["telePeriod"] * 1000, def()  udpFonctions.resetClientsConnectes()     end, "resetEsclaves")
            end
        elif msg[trigger].find("Save", 0)
            udpFonctions.log("UDP_CHGT_ETAT_DEMARRAGE: Fermeture connexion MultiCast & UniCast", LOG_LEVEL_DEBUG_PLUS)
            udpFonctions.etat()["udpReception"][0].close()
            udpFonctions.etat()["udpReception"][1].close()
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
udpFonctions.changementEtatDemarrage = udpFonctions_changementEtatDemarrage

# Cette fonction gère l'envoi de messages UDP en unicast et multicast
def udpFonctions_envoiUDP(typeComm, ipDestinataire, message)
	import string
	
	var udpEmission = udp()
	var resultatEnvoi

    udpFonctions.log("ENVOI_MSG_UDP: ------------------------ UDP sendUDP ----------------------", LOG_LEVEL_DEBUG_PLUS)
	
	# Ouvre la connexion UniCast sortante ou MultiCast sortante pour les maitres RangeExtender
	if (string.toupper(typeComm) == string.toupper("UniCast"))
		udpEmission.begin("", udpFonctions.etat()["port"][0])      # envoi sur toutes les interfaces, port identifié
    end

	# Ouvre la connexion MultiCast sortante pour le maitre RangeExtender
    if (serveur["rangeExtender"].find("activation", "OFF") == "ON")
        if (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] == 0)
            udpEmission.begin(ipDestinataire, 0)      # envoi sur toutes les interfaces, port aléatoire
        # Ouvre la connexion MultiCast sortante pour les autres
        elif (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] > 0)
            udpEmission.begin_multicast("224.3.0.1", udpFonctions.etat()["port"][1])
        end
    end
	
	# Envoi la commande
	# en UniCast
	if (string.toupper(typeComm) == string.toupper("UniCast"))
		resultatEnvoi = udpEmission.send(ipDestinataire, udpFonctions.etat()["port"][0], bytes().fromstring(message)) ? "OK" : "Echec"
    end

	# en MultiCast sortante pour le maitre RangeExtender
    if (serveur["rangeExtender"].find("activation", "OFF") == "ON")
        if (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] == 0)
            resultatEnvoi = udpEmission.send("224.3.0.1", udpFonctions.etat()["port"][1], bytes().fromstring(message)) ? "OK" : "Echec"
        # en MultiCast pour les autres
        elif (string.toupper(typeComm) == string.toupper("MultiCast") && serveur["udp"]["id"] > 0)
            resultatEnvoi = udpEmission.send_multicast(bytes().fromstring(message)) ? "OK" : "Echec"
        end
    end

	udpFonctions.log(string.format("ENVOI_MSG_UDP: Données %s envoyées vers '%s' >>>> %s >>>> %s", typeComm, ipDestinataire, message, resultatEnvoi), LOG_LEVEL_DEBUG)
    tasmota.yield()
	
	# Ferme la connexion
	udpEmission.close()
end
udpFonctions.envoiUDP = udpFonctions_envoiUDP

# Cette fonction gère la lecture de messages UDP en unicast et multicast
# Puis publie le message MQTT 'ModbusReceivedUDP' sur le Topic ==> Déclenchera la règle 'tasmota.add_rule('ModbusReceivedUDP')' -> vers la fonction controleModbus.recupereReponseModBusUDP()
def udpFonctions_lireUDP(typeComm, paramMSG)
    import string
    import json

    var msg = (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.etat()["udpReception"][0].read() : udpFonctions.etat()["udpReception"][1].read()
    tasmota.yield()

    # Récupère les messages sur le port UDP (respecte l'API Tasmota)
    while msg != nil
        # Réception du message
        udpFonctions.log("LIRE_UDP: ------------------------ UDP lire ----------------------", LOG_LEVEL_DEBUG_PLUS)
        udpFonctions.log(string.format("LIRE_UDP: Données UDP %s reçues de '%s' sur le port %i", typeComm, 
                                                (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.etat()["udpReception"][0].remote_ip : udpFonctions.etat()["udpReception"][1].remote_ip,
                                                (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.etat()["udpReception"][0].remote_port : udpFonctions.etat()["udpReception"][1].remote_port),
                                                LOG_LEVEL_DEBUG)
        udpFonctions.log("LIRE_UDP: msg = " + str(msg.asstring()), LOG_LEVEL_DEBUG)

        tasmota.yield()

        # On transforme la chaine en mots
        paramMSG["msgHex"] = msg
        paramMSG["msgString"] = msg.asstring()

        # On détermine le type de message
        # Trames ModBus en UDP (reecrit le 2026-09-29) : "<enveloppe> <trame en hexa>". La trame
        # binaire est decodee par modbusFonctions.lireMsgModbus -> decrypteMSG, comme en TCP, puis
        # publiee en 'ModbusReceivedUDP'. L'ancienne version attendait du JSON apres l'enveloppe,
        # alors que l'emission envoyait une trame binaire : aucune trame n'etait lisible.
        #   "ModbusPushUDP" : push d'etat d'un esclave (option B) -> seul le MAITRE le traite ;
        #                     marque Automatique : il n'acquitte aucune requete.
        #   "ModbusUDP"     : commande/reponse (repli quand le serie est coupe).
        var enveloppe = string.split(paramMSG["msgString"], " ", 1)
        if (enveloppe[0] == "ModbusPushUDP" || enveloppe[0] == "ModbusUDP")
            var estPush = (enveloppe[0] == "ModbusPushUDP")
            if (estPush && drivers["ModBus"].find("id", 99) != 0)    return true    end

            try
                import modbusFonctions
                var ip = (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.etat()["udpReception"][0].remote_ip : udpFonctions.etat()["udpReception"][1].remote_ip
                # Push : "ModbusPushUDP <seq> <trame hexa>" (numero d'ordre, 2026-09-29) ; un esclave
                # d'avant le numero d'ordre envoie "ModbusPushUDP <trame hexa>" -> seq absent (nil).
                var hex = enveloppe[1]
                var seq = nil
                if (estPush)
                    var morceaux = string.split(enveloppe[1], " ", 1)
                    if (size(morceaux) == 2)
                        seq = int(morceaux[0])
                        hex = morceaux[1]
                    end
                    # Copie brute vers MQTT, filtre seq non applique (2026-10-10, garde dans la fonction)
                    modbusFonctions.relaiePushMQTT(paramMSG["msgString"], ip)
                end
                # La regle 'ModbusReceivedUDP' (controleModbus.be, modBus_TasmotaSlaveModBus.be) prend le relais
                modbusFonctions.lireMsgModbus("ModbusReceivedUDP", {"Trame": bytes(hex), "Info": {"remote_ip": ip}, "Automatique": estPush, "Seq": seq})
            except .. as error, message
                udpFonctions.log(string.format("LIRE_UDP_ERREUR: trame ModBus illisible '%s' : %s --> %s", paramMSG["msgString"], error, message), LOG_LEVEL_ERREUR)
            end

            return true
        # Cas général des trames UDP TasmotaClient -> Traitement des commandes TasmotaClient UDP
        else
            # On découpe en fonction de " "
            var params = string.split(msg.asstring(), " ", 1)

            # Découpage général sur les "/"
            var decoupage = string.split(params[0], "/")
            var nb_slash = string.count(params[0], "/")

            paramMSG["prefix"] = decoupage[0]
            paramMSG["commande"] = decoupage[nb_slash] + " " + params[1]
            paramMSG["topic"] = ""
            for i: 1 .. nb_slash - 1
                if paramMSG["topic"] == ""
                    paramMSG["topic"] = decoupage[i]
                else paramMSG["topic"] += "/" + decoupage[i]
                end
            end

            udpFonctions.log("LIRE_UDP: prefix=" + str(paramMSG["prefix"]), LOG_LEVEL_DEBUG_PLUS)	
            udpFonctions.log("LIRE_UDP: topic=" + str(paramMSG["topic"]), LOG_LEVEL_DEBUG_PLUS)	
            udpFonctions.log("LIRE_UDP: commande=" + str(paramMSG["commande"]), LOG_LEVEL_DEBUG_PLUS)	

            # Reconnait les bons topics (Uniquement les esclaves car eux envoient leurs données avec leur topic)
            # Le maitre récupère tous les messages
            if (serveur["udp"]["id"] == 0)
                return true
            else
                if ((paramMSG["topic"] == serveur["mqtt"]["groupTopic1"]) || (paramMSG["topic"] == serveur["mqtt"]["topic"]))
                    return true
                else return false
                end
            end
        end

        tasmota.yield()

        # Initialise le buffer
        msg = (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.etat()["udpReception"][0].read() : udpFonctions.etat()["udpReception"][1].read()
    end

    return false
end
udpFonctions.lireUDP = udpFonctions_lireUDP

# Fonction qui gère l'envoi de commande TasmotaClient par UDP sous format string
# CMD = commande répondant au fonctionnenemt de l'API Tasmota
# Type de trame: <CMD>
def udpFonctions_sendTasmotaClientUDP(typeComm, destinationIP, commande)
    import string

    typeComm = ((typeComm == "" || typeComm == nil) ? "MultiCast" : typeComm)
    var port = (string.toupper(typeComm) == string.toupper("uniCast")) ? udpFonctions.etat()["port"] : udpFonctions.etat()["port"] * 2

    # Test   
    udpFonctions.log("ENVOI_TASMOTA_CLIENT_UDP: --------------- sendTasmotaClientUDP --------------", LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log(f"ENVOI_TASMOTA_CLIENT_UDP: Données {typeComm} envoyées ({destinationIP}) >>>> {commande}", LOG_LEVEL_DEBUG)
    udpFonctions.log(f"ENVOI_TASMOTA_CLIENT_UDP: Adresse IP = {destinationIP}", LOG_LEVEL_DEBUG_PLUS)
    udpFonctions.log(f"ENVOI_TASMOTA_CLIENT_UDP: commande = {commande}", LOG_LEVEL_DEBUG_PLUS)

    tasmota.yield()
#-
    if (string.toupper(typeComm) == string.toupper("uniCast"))
        udpFonctions.udpUniCast.send(destinationIP, port, bytes().fromstring(commande))
    elif (string.toupper(typeComm) == string.toupper("multiCast"))
        udpFonctions.udpMultiCast.send_multicast(bytes().fromstring(commande))
    end
-#
end
udpFonctions.sendTasmotaClientUDP = udpFonctions_sendTasmotaClientUDP

# Réinitialise les esclaves enregistrés / 300s
# Enregistrés dans '/json/discovery.json' en paramètrant le paramètre "lwt": "Offline"
# Cela permet de détecter si un module habituel est déconnecté
def udpFonctions_resetClientsConnectes()
    import gestionFileFolder
    import string
    import json
        
    # Lit le fichier json
    var paramDiscovery = json.load(gestionFileFolder.readFile("/json/discovery.json"))
    if (paramDiscovery == nil)
        udpFonctions.log("RESET_NB_ESCLAVES_JSON: Le fichier n'existe pas ou est vide !", LOG_LEVEL_DEBUG_PLUS)
        return
    end

    # Parcours tous les esclaves enregistrés et les marque tous 'Offline'
    for item: paramDiscovery.keys()
        paramDiscovery[item]["lwt"] = "Offline"
    end

    # Enregistre ou Mets à jour en variable les capteurs activés dans un tableau
    if (gestionFileFolder.readFile("/json/discovery.json") != json.dump(paramDiscovery))
        gestionFileFolder.writeFile("/json/discovery.json", json.dump(paramDiscovery))
    end

    # Décharge le json
    paramDiscovery = {}
end
udpFonctions.resetClientsConnectes = udpFonctions_resetClientsConnectes

# Retourne le module lors de l'importation
return udpFonctions