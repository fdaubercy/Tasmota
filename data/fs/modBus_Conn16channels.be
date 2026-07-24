#- NOTES Sur le module ModBus 16 sorties numériques
    - 16 sorties numériques (coils) de 1 à 16
    - ModBus.help peut vous aider à comprendre la gestion des communications
    - Utilise le Driver ModBus natif de Tasmota
    - Les commandes et les propriétés du module sont décrites dans le fichier '16 Channel  Multifunction RS485 Module commamd.docx'
    - Les relais de la platine 16 relais sont des relais inversés (circuit fermé lors de la presence de 0V sur la borne de commande)
-#

#- Réglage initial du module
    - L'adresse du module vierge est: 0x01
    - Le BaudRate configuré en usine: 9600 bps
        * Configurer le débit ModBus de Tasmota temporairement: 
                var ser = serial(4, 5, 1200, serial.SERIAL_8N1)
                ser.write(bytes("010300FE0001E5FA"))
                tasmota.delay(1000)
                msg = ser.read()
                print(msg.asstring())
                print(ser.available())
                
                tasmota.cmd("ModbusBaudrate 9600")
                tasmota.cmd("ModBusSend {\"deviceaddress\": 1, \"functioncode\": 3, \"startaddress\": 0xFE, \"type\":\"uint16\", \"count\":1}")
-#

#- TABLE D'INVERSION Open/Close - centralisee ici, et ici SEULEMENT (phase 2, 2026-07-24)

    La carte ne parle pas en etats de relais mais en NIVEAUX DE SORTIE. Son glossaire :
        "Open"  = control port output LOW  level  (0V)
        "Close" = control port output HIGH level  (+5V)

    Le sens depend donc du relais cable derriere, designe par son 'type' Tasmota :
        type 224 "Relais"    (direct)  -> ON = sortie HAUTE = Close
        type 256 "Relais_i"  (inverse) -> ON = sortie BASSE = Open      <- les 16 voies du garage

    PIEGE : les deux sens n'encodent pas "Close" de la meme facon.
        Ecriture (0x06) : ordre     Open = 0x01, Close = 0x02
        Lecture  (0x03) : registre  open = 0x0001, close = 0x0000
    "Open" vaut 1 des deux cotes, "Close" vaut 2 en ecriture et 0 en lecture. D'ou deux
    fonctions distinctes plutot qu'une seule table - c'est exactement l'erreur que la
    centralisation doit rendre impossible.

    Cavalier M0 (piege 2 de PROTOCOLE_MODBUS.md section 8) : connecte, il inverse la
    polarite des sorties et donc TOUTE cette table. Lu dans le persist du groupe
    Conn16channels, defaut "deconnecte" (reglage d'usine). S'il est deplace sans que ce
    reglage suive, la relecture sera coherente et FAUSSE.
-#
var modBus_Conn16channels

class MODBUS_CONN_16CHANNEL : Driver
    # Variables
    var nbIOActivesJSON
    var DEBUG
    var indexRegistres        # {idModBus: [cleModule, cleEnv, cleDevice]} - voir construitIndexRegistres()
    var dernierSondageA       # horodatage (s) de la derniere reponse 0x03 exploitee
    var etatsInconnus         # true quand le chien de garde a expire (3 x T sans reponse)

    #- SONDAGE PERIODIQUE, CHIEN DE GARDE, RECONCILIATION (phase 4, 2026-07-24)

        La carte 16 relais ne peut RIEN pousser : elle ne parle que si on l'interroge
        (PROTOCOLE_MODBUS.md section 9, tableau des rythmes). C'est donc un polling maitre
        0x03 qui fournit l'etat constate, avec T = 30 s.

        Sans cet emetteur, tout le traitement de relecture ecrit en phase 2 restait du code
        mort : rien n'emettait jamais la requete.

        La periode est lue dans le persist du groupe Conn16channels ('periodeSondage',
        defaut 30 s) via .find() : aucune clef nouvelle n'est exigee du persist existant.
    -#
    def periodeSondage()
        return int(drivers["ModBus"]["environnement"]["Conn16channels"].find("periodeSondage", 30))
    end

    # Emet la requete de relecture des 16 voies. Une seule trame, une seule entree en file.
    def sondeEtats(nameConn16channel)
        import modbusFonctions

        var conn = drivers["ModBus"]["environnement"]["Conn16channels"].find(nameConn16channel, nil)
        if (conn == nil || conn.find("activation", "OFF") != "ON")    return    end

        # ModBusSend {"deviceaddress":1,"functioncode":3,"startaddress":1,"type":"uint16","count":16}
        modbusFonctions.envoiMsgModbus({
                                            "DeviceAddress": conn.find("id", 1),
                                            "FunctionCode": modbusFonctions.LECTURE_REGISTRES_HOLDER,
                                            "StartAddress": 1,
                                            "type": "uint16",
                                            "Count": 16,
                                            "Values": []
                                        }, "Commande", conn.find("id", 1))
    end

    #- Chien de garde - la clause "jamais faux en silence" de la section 9.
        Passe les etats CONSTATES a "inconnu" au-dela de 3 x T sans reponse. On ne touche
        pas a l'etat commande : c'est la connaissance de la realite qui est perdue, pas
        l'intention. Mieux vaut afficher "inconnu" qu'une vieille valeur presentee comme
        fraiche.
    -#
    def verifieChienDeGarde()
        import string

        if (self.dernierSondageA == nil || self.etatsInconnus)    return    end
        if (tasmota.rtc()["local"] - self.dernierSondageA <= 3 * self.periodeSondage())    return    end

        self.etatsInconnus = true
        self.log(string.format("MODBUS_CONN_16CH_CHIEN_DE_GARDE: aucune reponse depuis plus de %i s -> etats constates passes a 'inconnu'", 3 * self.periodeSondage()), LOG_LEVEL_ERREUR)

        for idModBus: self.indexRegistres.keys()
            var cible = self.indexRegistres[idModBus]
            modules[cible[0]]["environnement"][cible[1]][cible[2]]["etatConstate"] = "inconnu"
        end
    end

    # true si le cablage inverse la sortie pour ce type de relais (M0 pris en compte)
    def sortieInversee(typeRelais)
        var m0Connecte = (drivers["ModBus"]["environnement"]["Conn16channels"].find("cavalierM0", "deconnecte") == "connecte")
        return (typeRelais == 256) != m0Connecte        # XOR : M0 inverse la table
    end

    # Etat "ON"/"OFF" -> ordre a envoyer en 0x06 (Open = 0x01, Close = 0x02)
    def ordrePourEtat(typeRelais, etat)
        if (self.sortieInversee(typeRelais))    return (etat == "ON" ? 0x01 : 0x02)    end
        return (etat == "ON" ? 0x02 : 0x01)
    end

    # Registre relu en 0x03 (open = 0x0001, close = 0x0000) -> etat "ON"/"OFF"
    def etatPourRegistre(typeRelais, registre)
        var estOpen = (registre != 0)
        if (self.sortieInversee(typeRelais))    return (estOpen ? "ON" : "OFF")    end
        return (estOpen ? "OFF" : "ON")
    end

    #- INDEX INVERSE {idModBus: [cleModule, cleEnv, cleDevice]} (phase 2, 2026-07-24)

        Remplace un balayage complet de 'modules' par voie relue. Une reponse 0x03 porte
        les 16 voies d'un coup : sans index, il faudrait 16 balayages imbriques a chaque
        sondage. L'index se construit une fois et repond en un acces.

        Il est reconstruit a chaque appel, et non mis en cache entre les sondages : la
        configuration bouge (commandes ReglageXxx, ajout d'un relai virtuel), et un index
        perime designerait la MAUVAISE cible - c'est-a-dire commanderait le mauvais relai.
        Un index faux est pire qu'un balayage lent ; le cout reste d'un parcours par
        sondage, contre seize auparavant.
    -#
    def construitIndexRegistres(nameConn16channel)
        var index = {}

        for cleModule: modules.keys()
            tasmota.yield()
            if (type(modules[cleModule]) != "instance")   continue      end

            var env = modules[cleModule].find("environnement", nil)
            if (env == nil)   continue    end

            for cleEnv: env.keys()
                if (type(env[cleEnv]) != "instance")   continue    end

                for cleDevice: env[cleEnv].keys()
                    if (type(env[cleEnv][cleDevice]) != "instance")   continue    end

                    var device = env[cleEnv][cleDevice]
                    if (device.find("activation", "OFF") != "ON")                       continue    end
                    if (device.find("virtuel", "OFF") != "ModBus_" + nameConn16channel)  continue    end
                    if (device.find("idModBus", false) == false)                        continue    end

                    index[device["idModBus"]] = [cleModule, cleEnv, cleDevice]
                end
            end
        end

        return index
    end

    def init()
        import json
        import gestionFileFolder
        import string

        self.DEBUG = nil
        self.nbIOActivesJSON = nil
        self.indexRegistres = {}
        self.dernierSondageA = nil      # nil = aucun sondage abouti -> le chien de garde ne mord pas encore
        self.etatsInconnus = false

        # Enregistre ou Mets à jour en variable les capteurs activés dans un tableaus
        self.nbIOActivesJSON = json.load(gestionFileFolder.readFile("/json/nbIOActives.json"))

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
        tasmota.add_rule("System", def(value, trigger, msg) self.changementEtatDemarrage(value, trigger, msg) end) 

        # Si maitre ModBus peuvent reçoit une réponse après avoir envoyé un ordre
        # Et ajoute le résultat en json
        for cle: drivers["ModBus"]["environnement"]["Conn16channels"].keys()
            tasmota.yield()
            if type(drivers["ModBus"]["environnement"]["Conn16channels"][cle]) != "instance"   continue    end

            if (drivers["ModBus"]["environnement"]["Conn16channels"][cle].find("activation", "OFF") == "ON")
                # Ajoute une règle pour chaque module Conn16Channels
                # Gestion des messages recus par ModbusReceived
                if (drivers["ModBus"]["typeComm"].find("Serial", "OFF") == "ON")
                    tasmota.add_rule(string.format("ModbusReceived#DeviceAddress==%i", drivers["ModBus"]["environnement"]["Conn16channels"][cle]["id"]), def(value, trigger, msg) self.recupereReponseModBus(value, trigger, msg)    end, "conn16channelsModBus_Received")

                    #- SONDAGE PERIODIQUE + CHIEN DE GARDE (phase 4)
                        La carte ne pousse rien : ce cron est la seule source de l'etat
                        constate. 'cle' est capture par la closure, un cron par carte.
                    -#
                    var nomCarte = cle
                    tasmota.add_cron(string.format("*/%i * * * * *", self.periodeSondage()),
                                     def() self.sondeEtats(nomCarte) self.verifieChienDeGarde() end,
                                     "conn16channels_sondage_" + nomCarte)

                    #- RECONCILIATION AU DEMARRAGE (phase 4)
                        Au boot, la copie du maitre ne vaut rien tant qu'elle n'a pas ete
                        confrontee au materiel : les relais ont pu bouger pendant qu'il
                        etait eteint. On sonde donc une fois, sans attendre le 1er cron.
                        Differe de 15 s : le bus et les esclaves doivent etre prets, et le
                        chargement des autres drivers ne doit pas etre ralenti.
                    -#
                    tasmota.set_timer(15000, def() self.sondeEtats(nomCarte) end, "conn16channels_boot_" + nomCarte)
                end
            end
        end

        # Ajoute les commandes personnalisées si le module est activé
        tasmota.add_cmd('ReglageConn16Channel', def(cmd, idx, payload, payload_json)  self.reglageConn16Channel(cmd, idx, payload, payload_json)  end)
    end

    def log(msg, levelDebug)
        import persist
        import string
    
        if (self.DEBUG == nil)
            self.DEBUG = drivers["ModBus"]["environnement"]["Conn16channels"].find("debug", "OFF")
        end
    
        if (self.DEBUG == "ON")
            log(msg, levelDebug)
        end
    end

    #- Exemples: 
        ReglageConn16Channel logActivation OFF   => Active ou désactive les logs du module
    -#
    def reglageConn16Channel(cmd, idx, payload, payload_json)
        import string
        import json
        import persist

        var fonction = false
        var parametres = []
        var reponse_cmnd
        
        # Test   
        self.log("REGLAGE_MODBUS_CONN_16CH: -------------------- ReglageConn16Channel -------------------", LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
        self.log("REGLAGE_MODBUS_CONN_16CH: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

        # Détermine la fonction appelée et ses paramètres
        if string.find(payload, " ") > - 1
            parametres = string.split(payload , " ", 1)
            fonction = parametres.pop(0)
        else fonction = payload
        end

        log("REGLAGE_MODBUS_CONN_16CH: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
        if (parametres.size() > 0)	log("REGLAGE_MODBUS_CONN_16CH: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
        if (parametres.size() > 1)	log("REGLAGE_MODBUS_CONN_16CH: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

        # Activation ou désactivation des logs de gestion de la garage -> ordre: logActivation
        if (string.toupper(fonction) == string.toupper("logActivation"))
            try
                # Adapte le paramètre
                parametres[0] = (parametres[0] == "1" ? "ON" : (parametres[0] == "0" ? "OFF" : parametres[0]))
                self.DEBUG = parametres[0]

                # Sauvegarde le paramètre
                drivers["ModBus"]["environnement"]["Conn16channels"]["debug"] = parametres[0]
                persist.save()
            except .. as e, m
                # print('Erreur: ', e, " -> ", m)
            end
        end

        # Commande réussie
        # Réponse à la commande
        reponse_cmnd = string.format("reglageConn16Channel: id=%i, logActivated=%s", idx, self.DEBUG)
        tasmota.resp_cmnd(json.dump(reponse_cmnd))
    end

    # Pour le maitre ModBus: A chaque réception d'une trame ModBus de la part d'un module conn16Channel
    # Modifie en persist json: la valeur de la device en fonction du message ModBus recu.
    def recupereReponseModBus(value, trigger, msg)
        import modbusFonctions
        import string
        import json

        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: -------------------- Conn16channels recupereReponseModBus -------------------", LOG_LEVEL_DEBUG)
        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: value = " + str(value), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: trigger = " + str(trigger), LOG_LEVEL_DEBUG_PLUS)
        self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: msg = " + str(msg), LOG_LEVEL_DEBUG_PLUS)

        # Détermine l'item à analyser dans le message ModBus recu
        var TypeMsg = ""
        if (string.find(trigger, "ModbusReceived#DeviceAddress") > -1)
            msg = msg["ModbusReceived"]
            TypeMsg = "Série"
        elif (string.find(trigger, "ModbusReceivedUDP#DeviceAddress") > -1)
            msg = msg["ModbusReceivedUDP"]
            TypeMsg = "UDP"
        elif (string.find(trigger, "ModbusReceivedTCP#DeviceAddress") > -1)
            msg = msg["ModbusReceivedTCP"]
            TypeMsg = "TCP"
        end
        self.log(f"MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: Type de msg Modbus = {TypeMsg:s}", LOG_LEVEL_DEBUG_PLUS)

        # Complete la reponse de lecture avec StartAddress/Count/type de la requete en
        # vol (la trame RTU ne les porte pas) -> le maitre sait a quel registre repondre.
        # REJET STRICT (2026-07-24) : une trame hors-sequence ne doit ni etre completee
        # depuis la requete en vol, ni l'acquitter - sinon elle lui volerait sa reponse,
        # et la vraie requete serait perdue au lieu d'etre renvoyee par le timeout.
        # Une TELEMETRIE spontanee, elle, porte deja son propre StartAddress (lu dans la
        # trame par decrypteMSG) : on la traite normalement, mais elle n'acquitte rien.
        var estReponseEnVol = modbusFonctions.apparieReponse(msg)
        if (!estReponseEnVol && !msg.find("Automatique", false))    return    end

        # Certaines fonctions ne retournent aucune données
        msg["FunctionName"] = modbusFonctions.tabFonctionsName[msg["FunctionCode"]]
        self.log(string.format("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: FunctionCode = 0x%02X ('%s')", msg["FunctionCode"], msg["FunctionName"]), LOG_LEVEL_DEBUG_PLUS)

        if (msg["FunctionName"] == "ECRITURE_REGISTRES_HOLDER")
            # Acquitte le message en vol (reponse recue) -> pompe le suivant
            if (estReponseEnVol)    modbusFonctions.termineEnVol(true)    end

            return
        end

        #- RELECTURE D'ETAT (0x03) - phase 2, 2026-07-24

            La carte renvoie ses 16 voies en une seule trame : un registre 16 bits par
            canal, 0x0001 = open, 0x0000 = close (PROTOCOLE_MODBUS.md section 8).
            On reporte ici l'etat CONSTATE sur les relais virtuels, via l'index inverse.

            On ne commande RIEN. Un ecart entre l'etat commande et l'etat constate est
            journalise, pas corrige : emettre un Power depuis la reponse a un sondage
            creerait une boucle de retroaction (Power -> envoi ModBus -> reponse ->
            Power...). La reconciliation commande/constate est la phase 4, avec son
            chien de garde et son numero de sequence.
        -#
        if (msg["FunctionName"] == "LECTURE_REGISTRES_HOLDER")
            var valeurs = msg.find("Values", nil)

            if (type(valeurs) != "instance" || size(valeurs) == 0)
                self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: reponse 0x03 sans valeurs exploitables", LOG_LEVEL_ERREUR)
            else
                # Retrouve le Conn16channel emetteur a partir de son adresse ModBus
                var nameConn16channel = nil
                for cle: drivers["ModBus"]["environnement"]["Conn16channels"].keys()
                    if (type(drivers["ModBus"]["environnement"]["Conn16channels"][cle]) != "instance")   continue    end
                    if (drivers["ModBus"]["environnement"]["Conn16channels"][cle].find("id", -1) == msg.find("DeviceAddress", -2))
                        nameConn16channel = cle
                        break
                    end
                end

                if (nameConn16channel == nil)
                    self.log(string.format("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: aucun Conn16channel d'adresse %s", str(msg.find("DeviceAddress", -2))), LOG_LEVEL_ERREUR)
                else
                    self.indexRegistres = self.construitIndexRegistres(nameConn16channel)

                    # Le 1er registre lu correspond au canal StartAddress (1 par defaut)
                    var canalDepart = msg.find("StartAddress", 1)

                    for rang: 0 .. size(valeurs) - 1
                        tasmota.yield()
                        var idModBus = canalDepart + rang
                        var cible = self.indexRegistres.find(idModBus, nil)
                        if (cible == nil)   continue    end

                        var device = modules[cible[0]]["environnement"][cible[1]][cible[2]]
                        var etatConstate = self.etatPourRegistre(device.find("type", 256), valeurs[rang])

                        # DEUX PLANS, JAMAIS CONFONDUS (phase 4) :
                        #   device["etat"]         = etat COMMANDE - ce que le framework a
                        #                            demande. Lu par le reste du systeme
                        #                            (Power, interface web) : on n'y touche PAS.
                        #   device["etatConstate"] = ce que la carte rapporte reellement.
                        # Ecraser "etat" avec le constate (ce que faisait la premiere version
                        # de la phase 2) detruisait la seule reference permettant de detecter
                        # une divergence - et rendait la reconciliation impossible.
                        device["etatConstate"] = etatConstate
                        device["constateA"]    = tasmota.rtc()["local"]

                        if (device.find("etat", "OFF") != etatConstate)
                            self.log(string.format("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: ECART voie %i (relai n°%i) : commande=%s, constate=%s",
                                                    idModBus, device.find("id", 0), device.find("etat", "OFF"), etatConstate), LOG_LEVEL_INFO)
                        end
                    end

                    self.dernierSondageA = tasmota.rtc()["local"]
                    self.etatsInconnus   = false
                end
            end
        end

        # Ajoute la donnée reçue en json
        # self.log("MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: dataJson=" + json.dump(self.dataJson), LOG_LEVEL_DEBUG_PLUS)

        # Acquitte le message en vol (reponse recue)
        if (estReponseEnVol)    modbusFonctions.termineEnVol(true)    end
    end

    # Règles sur changement d'état lors du démarrage de Tasmota
    def changementEtatDemarrage(value, trigger, msg)
        import string
        import json
        import re
        import modbusFonctions

        # Test
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: -------------------- Conn16Channel changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG)
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
        self.log("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
        
        if (type(value) == "instance")
            for cle: value.keys()
                value = value[cle]
            end
        end

        tasmota.yield()

        # Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
        # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
        # Save: Avant redemarrage de tasmota
        if (trigger == "System")
            if msg[trigger].find("Boot", 0)
                # Configure les relais virtuels ModBus si ils existent et sont paramétrés
                # Gère les commandes envoyées aux devices ModBus du Conn16channel au demarrage
                # Parcours les devices virtuels ModBus
                for cleModule: modules.keys()
                    tasmota.yield()
                    if (type(modules[cleModule]) != "instance")   continue      end

                    try
                        for cleDevices: modules[cleModule]["environnement"].keys()          # ex: cleDevices = "relais", "capteurs", etc.
                            var devices = modules[cleModule]["environnement"].find(cleDevices, false)

                            if (type(devices) != "instance")   continue      end

                            if (devices)
                                var tabEtatRelais = nil

                                if (cleDevices == "relais")
                                    tabEtatRelais = tasmota.get_power()
                                end

                                for cleDev: devices.keys()      # ex: "relai1", "capteur2", etc.
                                    if type(devices[cleDev]) != "instance"   continue    end
                                    tasmota.yield()

                                    # Si le relai est activé (réels + virtuels)
                                    if (devices[cleDev].find("activation", "OFF") == "ON" && devices[cleDev].find("virtuel", "OFF") != "OFF")
                                        if ((string.find(devices[cleDev]["virtuel"], "ModBus_Conn16channel") > - 1) && (devices[cleDev].find("idModBus", false) != false))
                                            var valueModBus
                                            
                                            if (cleDevices == "relais")
                                                # Rappel de l'état des relais avant redémarrage
                                                if (tabEtatRelais[devices[cleDev]["id"] - 1] == true)    
                                                    tabEtatRelais[devices[cleDev]["id"] - 1] = "ON"
                                                else tabEtatRelais[devices[cleDev]["id"] - 1] = "OFF"    
                                                end  

                                                # Componentes   -> type=224: "Relais",
                                                #               -> type=256: "Relais_i"
                                                # Passe par la table d'inversion centralisee (en-tete du fichier) :
                                                # c'est la MEME regle que la relecture 0x03, elle ne peut plus diverger.
                                                valueModBus = self.ordrePourEtat(devices[cleDev]["type"], devices[cleDev]["etat"])

                                                # Execute la commande 'Power' si différent
                                                if (tabEtatRelais[devices[cleDev]["id"] - 1] == devices[cleDev]["etat"])        continue    end
                                            end

                                            var typeConnex = string.split(devices[cleDev]["virtuel"], "_")[0]
                                            var moduleConnex = string.split(devices[cleDev]["virtuel"], "_")[1]
                                            var groupeConnex = re.search("([a-zA-Z0-9]+[^0-9$]+)", string.split(devices[cleDev]["virtuel"], "_")[1])[0]

                                            if (typeConnex == "ModBus")
                                                if (devices[cleDev].find("idModBus", false) != false)
                                                    # Construit la trame
                                                    # Relai fermé si borne de commande à l'état bas (0V): valueModBus = 0x01
                                                    # Relai ouvert si borne de commande à l'état haut (+5V): valueModBus = 0x02
                                                    var trameModBus = 	{
                                                                            "DeviceAddress": drivers["ModBus"]["environnement"][groupeConnex][moduleConnex]["id"],
                                                                            "FunctionCode": 0, 
                                                                            "StartAddress": 0, 
                                                                            "type": "", 
                                                                            "Count": 0, 
                                                                            "Values": []
                                                                        }

                                                    # Envoi l'ordre sur le réseau ModBus
                                                    if (cleDevices == "relais")
                                                        trameModBus["FunctionCode"] = 0x06
                                                        trameModBus["StartAddress"] = devices[cleDev]["idModBus"] 
                                                        trameModBus["type"] = "uint8"
                                                        trameModBus["Count"] = 1
                                                        trameModBus["Values"] = [valueModBus, 0]
                                                                                        
                                                        tasmota.cmd(string.format("Power%i %s", devices[cleDev]["id"], devices[cleDev]["etat"]))
                                                        modbusFonctions.envoiMsgModbus(trameModBus, "Commande", trameModBus["StartAddress"]) 
                                                        self.log(string.format("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE: Commande sur le réseau ModBus pour le relai n°%i !", devices[cleDev]["id"]), LOG_LEVEL_INFO) 
                                                    end
                                                end
                                            end
                                        end
                                    end 
                                end
                            end
                        end
                    except .. as error, message
                        modbusFonctions.log(string.format("MODBUS_CONN_16CH_CHGT_ETAT_DEMARRAGE_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
                    end
                end
            end
        end
    end
end

# Active le Driver de controle global des modules
if (controleGeneral.nbIOActivesJSON["relais"]["actives"]["nb"] > controleGeneral.nbIOActivesJSON["relais"]["reels"]["nb"])
    if (drivers["ModBus"].find("activation", "OFF") == "ON")
        for cle: drivers["ModBus"]["environnement"]["Conn16channels"].keys()
            import string

            if type(drivers["ModBus"]["environnement"]["Conn16channels"][cle]) != "instance"   continue    end

            try
                if (drivers["ModBus"]["environnement"]["Conn16channels"][cle].find("activation", "OFF") == "ON")
                    modBus_Conn16channels = MODBUS_CONN_16CHANNEL()
                    tasmota.add_driver(modBus_Conn16channels)

                    log("MODBUS_CONN_16CHANNEL: Driver activé !", LOG_LEVEL_DEBUG)

                    break
                end
            except .. as error, message
                log(string.format("MODBUS_CONN_16CHANNEL_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
            end
        end
    end
end