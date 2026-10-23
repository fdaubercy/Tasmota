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
          Time <ts>             <-- unicast "Timestamp" -----  si la fiche reçue a typeReglageHeure == "UDP"
          persist ipMaitre      <-- unicast "ipMaitre"  -----  (topic tele/<groupTopic1>/ReglageUDP ...),
                                                               a l'IPAddress de la fiche (multicast si absente)

      1. Côté esclave
         * Déclenchement : changementEtatDemarrage (System#Boot, id > 0), puis timer NOMMÉ "forceEnvoiParams"
           ré-armé à chaque passage (remove_timer avant set_timer : une seule chaîne d'envois, même après
           des appels manuels — avant le 2026-10-03, chaque appel manuel en ajoutait une).
         * Collecte : la fiche est CONSTRUITE à la connexion Wi-Fi par discoveryFonctions.changementEtatDemarrage
           depuis le _persist.json (serveur, drivers.ModBus, diverses) + Status 5, et rangée sous
           discovery.json[MAC]["esclaveN"]. Champs : id, nom, topic, groupTopic, IPAddress, adresseMAC, host,
           typeReglageHeure, rangeExtender{activation, id, routagePort = 8080+id-1, ipMaitre},
           ModBus{activation, id, voieCommandes, Serial{...}, TCP{IPAddress, port}, UDP{...}}.
           voieCommandes ("Serial" | "UDP", 2026-10-15) : voie par laquelle l'esclave veut recevoir
           les commandes du maitre ; lue par modbusFonctions.voieDe. 'ReglageModbus VoieCommandes'
           la change et renvoie aussitot la fiche (forceEnvoiParams + MQTT retenu).
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
           NTP ou RTC) : répond Timestamp + ipMaitre en UNICAST à l'IPAddress de la fiche (2026-10-17,
           correction C5 : marche en Range Extender ET en Wi-Fi classique, et l'unicast est acquitté
           par la radio) ; fiche sans IP lisible -> multicast, comme avant.
         * Contrepoids : resetClientsConnectes, une fois après telePeriod au démarrage, met tout 'Offline'.
      3. Ce que le maître fait de la table
         * rangeExtenderFonctions : boutons de la page d'accueil (RgxClients x fiches esclaveN 'Online') et
           commande RoutageRangeExtender -> 'RgxPort tcp, <routagePort>, <IP esclave>, 80'. Rôle 'maitre' ignoré.
         * discoveryFonctions.affichePageDiscovery : boutons de /discovery, port calculé depuis ipMaitre.
         * modbusFonctions.fichesModbus (fiches des AUTRES MAC du même groupTopic portant un bloc ModBus) :
           voie (voieCommandes) et IP de chaque esclave pour les commandes ModBus (routesFiches ->
           voieDe / ipDe ; une seule fiche retenue par ModBus.id, choisitFiche) ; clients ModBus TCP
           (ReglageModbus ImAlive ON).
      Pièges connus
         * Carte réaffectée (2026-10-03) : une fiche 'maitre' périmée, retenue sur le broker sous la MAC de
           l'esclave, était annoncée à la place d'esclaveN. Le maître la rangeait en 'maitre' (ignorée par
           le routage, prise pour l'id ModBus 0) et, typeReglageHeure valant 'NTP', ne renvoyait ni heure
           ni IP. Corrigé par : choix du rôle par l'id (forceEnvoiParams) + effacement des fiches périmées
           (discoveryFonctions.mqtt_discovery). Bancs : outils_docs/scripts_python/berry/test_discovery.be §8-10.
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
            "ip": ["", ""],            # adresses [UniCast, MultiCast]
            "ecouteOuverte": [false, false],   # socket d'ecoute ouverte [UniCast, MultiCast] (C7)
            "secoursFini": false,      # les 2 ecoutes ouvertes (Boot ou secours), ou System#Save (C7)
            "reseauDepuis": nil,       # tasmota.millis() de la montee du reseau, Boot pas encore vu (C7)
            "essaiApres": [nil, nil]   # apres une ouverture refusee : pas de nouvel essai avant (C7)
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
                "Groupe 224.3.0.1, en Range Extender comme en Wi-Fi classique. Esclave (id > 0) : par",
                "sa STA ; maitre (id = 0) : par son point d'acces s'il est actif, sinon par sa STA.",
                "Sert aux tests.",
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
        # Maitre ou esclave, Range Extender ou Wi-Fi classique : envoiUDP choisit l'interface (2026-10-17,
        # correction C4 ; avant : rien ne partait hors Range Extender, et sans message d'erreur)
        else
            udpFonctions.envoiUDP("MultiCast", "", message)
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
            udpFonctions.log("REGLAGE_UDP_ERREUR: envoi de ImAlive au maitre impossible : " + str(e) + " - " + str(m) + " !", LOG_LEVEL_ERREUR)
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
            # Range la fiche sous sa MAC ({MAC: {role: {...}}}, corrige le 2026-09-30 : elle etait rangee
            # a la RACINE sous son role, ce qui cassait /discovery), 'lwt' = Online (sans lui, un esclave
            # RangeExtender qui n'atteint pas le broker n'etait jamais route), purge l'ancienne entree racine.
            # Le fichier n'est reecrit que si la fiche change (audit N2/P5.2, 2026-10-24) : voir
            # discoveryFonctions.rangeFicheImAlive.
            import discoveryFonctions
            discoveryFonctions.rangeFicheImAlive(mac, device, tmp[device])

            tasmota.yield()
            udpFonctions.log("REGLAGE_UDP: Le maitre UDP a reçu les paramètres de l'esclave '" + str(tmp[device].find("nom", device)) + "' !", LOG_LEVEL_DEBUG_PLUS)

            if (tmp[device].find("typeReglageHeure", "NTP") == "UDP")
                # Reponse en UNICAST a l'IP de la fiche que l'esclave vient d'envoyer (2026-10-17, correction
                # C5) : le multicast du maitre ne sort que par UNE interface, un esclave en Wi-Fi classique
                # (sur la box) ne le recevait jamais ; l'unicast est en plus acquitte par la radio 802.11.
                # Fiche sans IPv4 lisible : multicast, comme avant.
                var ipEsclave = str(tmp[device].find("IPAddress", ""))
                var voie = (udpFonctions.estIPv4(ipEsclave) ? "UniCast" : "MultiCast")
                var ipVoie = (voie == "UniCast" ? ipEsclave : "")

                # Envoi la mise à jour de l'heure a l'esclave
                var message = string.format("tele/%s/%s %s %i", serveur["mqtt"]["groupTopic1"], "ReglageUDP", "Timestamp", int(tasmota.rtc()["utc"]))
                udpFonctions.envoiUDP(voie, ipVoie, message)

                # Envoi de son adresse IP a l'esclave
                message = string.format("tele/%s/%s %s %s", serveur["mqtt"]["groupTopic1"], "ReglageUDP", "ipMaitre", tasmota.cmd("Status 5", boolMute)["StatusNET"]["IPAddress"])
                udpFonctions.envoiUDP(voie, ipVoie, message)

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
            udpFonctions.log("REGLAGE_UDP_ERREUR: mise a l'heure par le maitre (Timestamp) impossible : " + str(e) + " - " + str(m) + " !", LOG_LEVEL_ERREUR)
        end
    # L'esclave enregistre l'adresse IP du maitre
    elif (string.toupper(fonction) == string.toupper("ipMaitre") && serveur["udp"]["id"] > 0)
        try
            # Corrige le 2026-10-24 : insert() ne remplace pas une cle existante (les persists portent deja
            # "ipMaitre") et persist.save() sans true n'ecrit pas une modif imbriquee : une nouvelle IP du
            # maitre n'etait jamais retenue. Affectation, et ecriture flash SEULEMENT si l'IP change.
            var ip = str(parametres[0])
            if (!udpFonctions.estIPv4(ip))
                udpFonctions.log("REGLAGE_UDP_ERREUR: IP du maitre invalide '" + ip + "' : ignoree !", LOG_LEVEL_ERREUR)
            elif (serveur["rangeExtender"].find("ipMaitre", "") != ip)
                serveur["rangeExtender"]["ipMaitre"] = ip
                persist.serveur = serveur
                persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
                udpFonctions.log("REGLAGE_UDP: L'esclave UDP a enregistré l'adresse IP du maitre: " + ip, LOG_LEVEL_INFO)
            end

            tasmota.yield()
        except .. as e, m
            udpFonctions.log("REGLAGE_UDP_ERREUR: enregistrement de l'IP du maitre (ipMaitre) impossible : " + str(e) + " - " + str(m) + " !", LOG_LEVEL_ERREUR)
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
            # Ouverture par ouvreEcoute (C7) : rien si le secours sans MQTT l'a deja ouverte
            # Le secours ne s'arrete que si les DEUX ecoutes sont ouvertes : un Boot dont l'ouverture echoue
            # le laisse reessayer (sinon plus rien ne rouvrirait l'ecoute, le defaut L3 sous une autre forme)
            udpFonctions.ouvreEcoute(typeComm)
            udpFonctions.etat()["secoursFini"] = (udpFonctions.etat()["ecouteOuverte"][0] && udpFonctions.etat()["ecouteOuverte"][1])

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
            udpFonctions.etat()["ecouteOuverte"] = [false, false]
            udpFonctions.etat()["secoursFini"] = true        # Save precede un redemarrage : ne rien rouvrir
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

# Ouvre la socket d'ecoute de typeComm (UniCast : port 2000, MultiCast : 224.3.0.1:4000), UNE seule fois.
# true si elle est ouverte. Rien tant que le reseau n'est pas monte : creer une socket avant la pile TCP/IP
# plante l'ESP32 (constate le 2026-10-11, voir envoiUDP).
def udpFonctions_ouvreEcoute(typeComm)
    import string
    var e = udpFonctions.etat()
    var i = (string.toupper(str(typeComm)) == "UNICAST" ? 0 : 1)
    if (e["ecouteOuverte"][i])    return true    end
    if (e["udpReception"][i] == nil || !tasmota.is_network_up())    return false    end
    var ok = (i == 0 ? e["udpReception"][0].begin(e["ip"][0], e["port"][0])
                     : e["udpReception"][1].begin_multicast(e["ip"][1], e["port"][1]))
    e["ecouteOuverte"][i] = (ok ? true : false)
    if (ok)
        udpFonctions.log(string.format("UDP_ECOUTE: ecoute %s ouverte sur le port %i !", str(typeComm), e["port"][i]), LOG_LEVEL_DEBUG_PLUS)
    else
        udpFonctions.log(string.format("UDP_ECOUTE_ERREUR: ouverture de l'ecoute %s sur le port %i refusee !", str(typeComm), e["port"][i]), LOG_LEVEL_ERREUR)
    end
    return e["ecouteOuverte"][i]
end
udpFonctions.ouvreEcoute = udpFonctions_ouvreEcoute

# Correction C7 (2026-10-21, DIAGNOSTIC_UDP_2026-10-17.md, defaut L3) : System#Boot n'est leve qu'a la
# 1re connexion MQTT (xdrv_02_9_mqtt.ino:1487). Broker injoignable au demarrage = aucune ecoute UDP, et une
# cuve commandee par UDP n'entend plus le P4. Appelee chaque seconde par les deux CONTROLE_UDP : si les deux
# ecoutes ne sont pas ouvertes 60 s apres la montee du reseau (Boot absent, ou son ouverture refusee), les ouvre. Les 60 s laissent le chemin
# normal intact et le point d'acces du maitre se creer avant l'abonnement multicast (course L2).
# Le reste de Boot (fiche de l'esclave, timer resetEsclaves du maitre) attend le vrai Boot.
def udpFonctions_secoursSansMqtt(typeComm)
    import string
    var e = udpFonctions.etat()
    if (e["secoursFini"])    return    end
    if (!tasmota.is_network_up())
        e["reseauDepuis"] = nil
        return
    end
    var delai = 60000                       # ms, depuis la montee du reseau, puis entre deux essais
    var maintenant = tasmota.millis()
    if (e["reseauDepuis"] == nil)
        e["reseauDepuis"] = maintenant
        return
    end
    if (maintenant - e["reseauDepuis"] < delai)    return    end
    var i = (string.toupper(str(typeComm)) == "UNICAST" ? 0 : 1)
    if (e["ecouteOuverte"][i])    return    end
    var essai = e["essaiApres"]
    if (essai[i] != nil && (maintenant - essai[i]) < 0)    return    end    # difference : sans souci du debordement de millis
    # Un seul evenement par ouverture (pas un log par seconde) : info admise malgre every_second
    if (udpFonctions.ouvreEcoute(typeComm))
        udpFonctions.log(string.format("UDP_ECOUTE_SECOURS: ecoute %s ouverte sans System#Boot (MQTT injoignable ?) ou apres son echec, %i s apres le reseau !", str(typeComm), delai / 1000), LOG_LEVEL_INFO)
        e["secoursFini"] = (e["ecouteOuverte"][0] && e["ecouteOuverte"][1])
    else
        essai[i] = maintenant + delai       # ouverture refusee (erreur deja journalisee) : nouvel essai plus tard
    end
end
udpFonctions.secoursSansMqtt = udpFonctions_secoursSansMqtt

# Cette fonction gère l'envoi de messages UDP en unicast et multicast
def udpFonctions_envoiUDP(typeComm, ipDestinataire, message)
	import string

	# Reseau pas encore monte (2026-10-11) : creer la socket avant que la pile TCP/IP soit prete
	# plante l'ESP32 (LoadProhibited dans sys_mbox_post <- lwip_socket <- NetworkUdp::begin).
	# Constate sur la cuve : push du ruban a 2,6 s, Wi-Fi a 4,1 s, 3 plantages puis demarrage
	# de secours SANS Berry. On n'envoie rien : l'appelant reessaie ou le maitre relit.
	if (!tasmota.is_network_up())
		udpFonctions.log(string.format("ENVOI_MSG_UDP: Reseau non connecte, '%s' non envoye !", message), LOG_LEVEL_DEBUG)
		return
	end

	var resultatEnvoi

    udpFonctions.log("ENVOI_MSG_UDP: ------------------------ UDP sendUDP ----------------------", LOG_LEVEL_DEBUG_PLUS)

    # Interface d'emission (2026-10-17, outils_docs/DIAGNOSTIC_UDP_2026-10-17.md, corrections C1 + C2) :
    #   * ESCLAVE (udp.id > 0), unicast et multicast : socket liee a l'IP de SA STA. Sans liaison, lwIP
    #     prend la 1re interface du sous-reseau (ip4.c:171-178) : sur un esclave qui a AUSSI son point
    #     d'acces en 192.168.4.1/24, c'est ce point d'acces, et tout envoi vers le maitre 192.168.4.1 etait
    #     perdu (mesure : non lie -> perdu, lie a 192.168.4.2 -> recu). La liaison choisit la STA
    #     (crochet ESP-IDF ip4_route_src_hook, lwip_default_hooks.c:122).
    #   * MAITRE, unicast : toutes les interfaces, la destination choisit (192.168.4.x -> AP, LAN -> STA).
    #   * MAITRE, multicast (correction C3) : par son point d'acces, adresse LUE dans le persist
    #     (serveur.rangeExtender.AP.IPAddress, ipAP) au lieu du 192.168.4.1 ecrit en dur. Un ipDestinataire
    #     non vide impose l'interface (usage historique) : les appelants passent "" pour laisser ce choix.
    #   * MAITRE, multicast par la box (2026-10-17, interfacesMulticastMaitre) : AUSSI par sa STA, mais
    #     seulement si la decouverte connait un esclave joignable par la box (esclavesBox). Sans point
    #     d'acces actif ni esclave sur la box, le multicast n'est pas emis ("Non emis").
    #   * Port source ALEATOIRE (0) : la socket d'emission ne se lie plus aux ports d'ecoute 2000 / 4000,
    #     elle ne peut plus capter un datagramme entrant pendant sa courte vie (udp.c:267).
    #   * Multicast aussi en Wi-Fi classique (correction C4 ; avant : seulement si activation ON). Un
    #     esclave sur la box n'atteint le maitre que si la box relaie le multicast entre clients Wi-Fi.
    var esclave = (serveur["udp"].find("id", 0) > 0)
    var mode = string.toupper(str(typeComm))
    var interfaces = [""]       # IP locales d'emission, une socket par entree ("" = toutes) ; [] = rien a emettre
    var ipDest = ipDestinataire
    var port = nil
    if (mode == "UNICAST")
        port = udpFonctions.etat()["port"][0]
        if (esclave)    interfaces = [udpFonctions.ipSTA()]    end
    elif (mode == "MULTICAST")
        port = udpFonctions.etat()["port"][1]
        ipDest = "224.3.0.1"
        if (esclave)
            interfaces = [udpFonctions.ipSTA()]
        elif (ipDestinataire != nil && ipDestinataire != "")
            interfaces = [ipDestinataire]
        else
            interfaces = udpFonctions.interfacesMulticastMaitre()
        end
    else
        udpFonctions.log(string.format("ENVOI_MSG_UDP_ERREUR: type de communication inconnu '%s', '%s' non envoye !", str(typeComm), message), LOG_LEVEL_ERREUR)
    end

    if (port != nil && size(interfaces) == 0)
        resultatEnvoi = "Non emis"
        udpFonctions.log("ENVOI_MSG_UDP: multicast du maitre non emis : pas de point d'acces actif et aucun esclave joignable par la box", LOG_LEVEL_DEBUG)
    elif (port != nil)
        var ok = true
        for ipLocale: interfaces
            var envoye = udpFonctions.emet(ipLocale, ipDest, port, message)
            # Liaison refusee (IP de la STA changee entre-temps...) : un 2e essai sur toutes les interfaces
            # vaut mieux qu'un message perdu.
            if (!envoye && ipLocale != "")
                udpFonctions.log(string.format("ENVOI_MSG_UDP: envoi par l'interface %s refuse, nouvel essai sur toutes les interfaces", ipLocale), LOG_LEVEL_DEBUG)
                ipLocale = ""
                envoye = udpFonctions.emet("", ipDest, port, message)
            end
            ok = ok && envoye
            udpFonctions.log(string.format("ENVOI_MSG_UDP: interface d'emission '%s', destination %s:%i", (ipLocale == "" ? "toutes" : ipLocale), str(ipDest), port), LOG_LEVEL_DEBUG_PLUS)
        end
        resultatEnvoi = (ok ? "OK" : "Echec")
    end

	# Format inchange : lu par outils_pc/testeur_udp_essais.py (RE_ENVOI)
	udpFonctions.log(string.format("ENVOI_MSG_UDP: Données %s envoyées vers '%s' >>>> %s >>>> %s", typeComm, ipDestinataire, message, resultatEnvoi), LOG_LEVEL_DEBUG)
    tasmota.yield()
    # true si le datagramme est parti (2026-10-17) : la file du maitre ModBus en a besoin pour renvoyer
    # un message dont l'envoi UDP a echoue (modbusFonctions.envoieTeteUDP)
    return resultatEnvoi == "OK"
end
udpFonctions.envoiUDP = udpFonctions_envoiUDP

# Adresse IPv4 de la STA de la carte (sa liaison Wi-Fi cliente), "" si inconnue (2026-10-17).
def udpFonctions_ipSTA()
    var w = tasmota.wifi()
    var ip = (isinstance(w, map) ? str(w.find("ip", "")) : "")
    return ((ip == "0.0.0.0" || ip == "nil") ? "" : ip)
end
udpFonctions.ipSTA = udpFonctions_ipSTA

# Adresse du point d'acces Range Extender de la carte, lue dans le persist ; "" si le Range Extender est
# inactif (2026-10-17, correction C3 : remplace le "192.168.4.1" ecrit en dur). Sert au multicast du maitre.
def udpFonctions_ipAP()
    var rgx = serveur.find("rangeExtender", {})
    if (!isinstance(rgx, map) || rgx.find("activation", "OFF") != "ON")    return ""    end
    var ap = rgx.find("AP", {})
    var ip = (isinstance(ap, map) ? str(ap.find("IPAddress", "192.168.4.1")) : "192.168.4.1")
    return (udpFonctions.estIPv4(ip) ? ip : "192.168.4.1")
end
udpFonctions.ipAP = udpFonctions_ipAP

# Interfaces du multicast du MAITRE quand l'appelant n'en impose pas (2026-10-17) : son point d'acces s'il est
# actif (inchange), PLUS sa STA si la decouverte connait un esclave joignable par la box (esclavesBox).
# Liste vide : rien a emettre. Mesure de l'essai 2 (Wi-Fi classique) : la box relaie le multicast entre
# clients Wi-Fi, mais celui du maitre partait par son seul point d'acces et n'atteignait pas l'esclave.
def udpFonctions_interfacesMulticastMaitre()
    var liste = []
    var ap = udpFonctions.ipAP()
    if (ap != "")    liste.push(ap)    end
    if (udpFonctions.esclavesBox())
        var sta = udpFonctions.ipSTA()
        if (sta != "" && sta != ap)    liste.push(sta)    end
    end
    return liste
end
udpFonctions.interfacesMulticastMaitre = udpFonctions_interfacesMulticastMaitre

# true si /json/discovery.json connait au moins un esclave joignable par la box (2026-10-17) : fiche
# 'esclaveN' d'une autre MAC, de MEME groupTopic que la carte, MAC 'Online', IPv4 dans le /24 de la STA de la
# carte (le reseau de la box) et HORS du /24 de son point d'acces (un esclave en 192.168.4.x est derriere le
# point d'acces : la STA ne lui sert a rien). STA inconnue : aucun esclave (rien a emettre par elle).
# Resultat en cache : la table n'est relue que si sa date change, ou apres 30 s (date a la seconde : deux
# ecritures dans la meme seconde ne se distinguent pas). Les 8 ecrivains de la table restent inchanges.
def udpFonctions_esclavesBox()
    import path
    import json
    import re
    import string
    import gestionFileFolder

    var etat = udpFonctions.etat()
    var date = path.last_modified("/json/discovery.json")
    var cache = etat.find("esclavesBox")
    if (cache != nil && cache[0] == date && tasmota.millis() - cache[1] < 30000)    return cache[2]    end

    var trouve = false
    try
        var fichier = gestionFileFolder.readFile("/json/discovery.json")
        var table = (fichier != false && fichier != nil && fichier != "") ? json.load(fichier) : nil
        if (isinstance(table, map))
            var maMAC = string.replace(str(serveur.find("adresseMAC", "")), ":", "")
            var monGroupe = serveur.find("mqtt", {}).find("groupTopic1", "")
            var ap = udpFonctions.ipAP()
            var reseauAP = (ap != "" ? udpFonctions.reseau24(ap) : "")
            var sta = udpFonctions.ipSTA()
            var reseauBox = (udpFonctions.estIPv4(sta) ? udpFonctions.reseau24(sta) : "")
            if (reseauBox == reseauAP)    table = {}    end      # STA inconnue, ou meme reseau que l'AP
            var pattern = re.compile('^esclave[0-9]+$')
            for mac: table.keys()
                var entree = table[mac]
                if (mac == maMAC || !isinstance(entree, map) || entree.find("lwt", "") != "Online")    continue    end
                for role: entree.keys()
                    var fiche = entree[role]
                    if (pattern.match(role) == nil || !isinstance(fiche, map))    continue    end
                    if (fiche.find("groupTopic", "") != monGroupe)    continue    end
                    var ip = str(fiche.find("IPAddress", ""))
                    if (!udpFonctions.estIPv4(ip) || udpFonctions.reseau24(ip) != reseauBox)    continue    end
                    trouve = true
                    break
                end
                if (trouve)    break    end
                tasmota.yield()
            end
        end
    except .. as error, message
        udpFonctions.log(string.format("ESCLAVES_BOX_ERREUR: table de decouverte illisible : %s --> %s", error, message), LOG_LEVEL_ERREUR)
    end

    if (cache == nil || cache[2] != trouve)
        udpFonctions.log(string.format("ESCLAVES_BOX: multicast du maitre par la box %s", (trouve ? "ACTIVE (esclave joignable par la box decouvert)" : "DESACTIVE (aucun esclave joignable par la box)")), LOG_LEVEL_INFO)
    end
    etat["esclavesBox"] = [date, tasmota.millis(), trouve]
    return trouve
end
udpFonctions.esclavesBox = udpFonctions_esclavesBox

# "a.b.c." : reseau /24 d'une IPv4 deja validee par estIPv4 (2026-10-17).
def udpFonctions_reseau24(ip)
    import string
    var m = string.split(str(ip), ".")
    return m[0] + "." + m[1] + "." + m[2] + "."
end
udpFonctions.reseau24 = udpFonctions_reseau24

# true si texte est une IPv4 utilisable "a.b.c.d" (0-255, pas 0.0.0.0) (2026-10-17, correction C5 : IP d'une fiche).
def udpFonctions_estIPv4(texte)
    import string
    var s = str(texte)
    var morceaux = string.split(s, ".")
    if (size(morceaux) != 4 || s == "0.0.0.0")    return false    end
    for m: morceaux
        if (size(m) == 0 || size(m) > 3)    return false    end
        for i: 0 .. size(m) - 1
            if (m[i] < "0" || m[i] > "9")    return false    end
        end
        if (int(m) > 255)    return false    end
    end
    return true
end
udpFonctions.estIPv4 = udpFonctions_estIPv4

# Emet UN datagramme par une socket neuve liee a ipLocale ("" = toutes les interfaces), port source
# ALEATOIRE (0), puis la ferme. true si la pile l'a accepte (pas une preuve de reception).
def udpFonctions_emet(ipLocale, ipDest, port, message)
    var u = udp()
    var ok = u.begin(ipLocale, 0)
    if (ok)    ok = u.send(ipDest, port, bytes().fromstring(message))    end
    u.close()
    return (ok ? true : false)
end
udpFonctions.emet = udpFonctions_emet

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
        #   "ModbusUDP"     : commande/reponse. Depuis le 2026-10-15 : "ModbusUDP <tid> <trame hexa>",
        #                     tid = numero de transaction du maitre, renvoye tel quel par l'esclave
        #                     (PROTOCOLE_MODBUS.md §9, « Commandes sans fil », M3). L'ancien format
        #                     "ModbusUDP <trame hexa>" reste lu (tid absent).
        # Info.voie = "UDP" marque la trame venue par l'UDP : l'esclave y repond par la meme voie (M4).
        var enveloppe = string.split(paramMSG["msgString"], " ", 1)
        if (enveloppe[0] == "ModbusPushUDP" || enveloppe[0] == "ModbusUDP")
            var estPush = (enveloppe[0] == "ModbusPushUDP")
            if (estPush && drivers["ModBus"].find("id", 99) != 0)    return true    end

            try
                import modbusFonctions
                var ip = (string.toupper(typeComm) == string.toupper("UniCast")) ? udpFonctions.etat()["udpReception"][0].remote_ip : udpFonctions.etat()["udpReception"][1].remote_ip
                # Push : "ModbusPushUDP <seq> <trame hexa>" (numero d'ordre, 2026-09-29) ; un esclave
                # d'avant le numero d'ordre envoie "ModbusPushUDP <trame hexa>" -> seq absent (nil).
                # Le nombre avant la trame est le seq d'un push, ou le tid d'une commande/reponse
                var hex = enveloppe[1]
                var numero = nil
                var morceaux = string.split(enveloppe[1], " ", 1)
                if (size(morceaux) == 2)
                    numero = int(morceaux[0])
                    hex = morceaux[1]
                end
                var info = {"remote_ip": ip, "voie": "UDP"}
                if (!estPush && numero != nil)    info["transaction"] = numero    end
                # Copie brute vers MQTT, filtre seq non applique (2026-10-10, garde dans la fonction)
                if (estPush)    modbusFonctions.relaiePushMQTT(paramMSG["msgString"], ip)    end
                # La regle 'ModbusReceivedUDP' (controleModbus.be, modBus_TasmotaSlaveModBus.be) prend le relais
                modbusFonctions.lireMsgModbus("ModbusReceivedUDP", {"Trame": bytes(hex), "Info": info, "Automatique": estPush, "Seq": estPush ? numero : nil})
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
            # Message d'un seul mot (2026-10-17, C6) : params[1] levait index_error dans every_100ms
            paramMSG["commande"] = decoupage[nb_slash] + " " + (size(params) > 1 ? params[1] : "")
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
        
    # Lit le fichier json (une seule lecture : le texte sert aussi a la comparaison, audit P9.3)
    var texte = gestionFileFolder.readFile("/json/discovery.json")
    var paramDiscovery = json.load(texte)
    if (paramDiscovery == nil)
        udpFonctions.log("RESET_NB_ESCLAVES_JSON: Le fichier n'existe pas ou est vide !", LOG_LEVEL_DEBUG_PLUS)
        return
    end

    # Parcours tous les esclaves enregistrés et les marque tous 'Offline'
    for item: paramDiscovery.keys()
        paramDiscovery[item]["lwt"] = "Offline"
    end

    # Enregistre ou Mets à jour en variable les capteurs activés dans un tableau
    var nouveau = json.dump(paramDiscovery)
    if (texte != nouveau)
        gestionFileFolder.writeFile("/json/discovery.json", nouveau)
    end

    # Décharge le json
    paramDiscovery = {}
end
udpFonctions.resetClientsConnectes = udpFonctions_resetClientsConnectes

# Retourne le module lors de l'importation
return udpFonctions