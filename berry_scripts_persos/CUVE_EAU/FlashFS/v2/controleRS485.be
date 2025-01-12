#-
    NOTES :
        - Les port RS485 est paramétré à l'ouverture du Driver
        - Ce module permet la mise en place d'une passerelle mqtt <-> RS485
        - Les trames sont composées de :
            * 1 caractère de début '\r'
            * deviceAddress = adresse du dispositif destinataire
            * functionCode = numero code de la fonction à lancer
            * values = paramètre(s) sous format json (si plusieurs paramètres) ou string (1 seul paramètre)
            * 1 caractère de fin '\n'
-#
var controleRS485

class CONTROLE_RS485 : Driver
    # Variables
    var msg
    var serialRS485
    var buffer
    var sensorsRS485
    var jsonRS485
    var delimiteurs

    # *************************************************
    # * TasmotaClient Command definitions
    # *************************************************
    var MARQUEUR_START
    var MARQUEUR_END
    var MARQUEUR_SEPARATEUR
   
    var CMND_FUNC_JSON
    var CMND_FUNC_EVERY_SECOND
    var CMND_FUNC_EVERY_100_MSECOND
    var CMND_PUBLISH_TELE
    var CMND_EXECUTE_CMND
   
    # *************************************************
    # * TasmotaClient Parameter defintions
    # *************************************************
    var RESPONSE_FUNC_JSON
    var RESPONSE_PUBLISH_TELE

    def init()
        import json
        import string
        import persist
        import mqtt
        import RS485Fonctions

        var parametres = persist.find("parametres")

        # *************************************************
        # * TasmotaClient Command definitions
        # *************************************************
        self.MARQUEUR_START = "\r"
        self.MARQUEUR_END = "\n"
        self.MARQUEUR_SEPARATEUR = ";"
    
        self.CMND_FUNC_JSON = 0x01
        self.CMND_PUBLISH_TELE = 0x02
        self.CMND_FUNC_EVERY_SECOND = 0x03
        self.CMND_FUNC_EVERY_100_MSECOND = 0x04
        self.CMND_EXECUTE_CMND = 0x05
    
        # *************************************************
        # * TasmotaClient Parameter defintions
        # *************************************************
        self.RESPONSE_FUNC_JSON = 0x11
        self.RESPONSE_PUBLISH_TELE = 0x12

        self.buffer = ""
        self.sensorsRS485 = ""
        self.jsonRS485 = {}
        self.delimiteurs = {"MARQUEUR_START": self.MARQUEUR_START, "MARQUEUR_SEPARATEUR": self.MARQUEUR_SEPARATEUR, "MARQUEUR_END": self.MARQUEUR_END}

        log ("CONTROLE_RS485: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        #-         
            Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
            - Message log sur connexion wifi
            - Gestion des enregistrements en mqtt si c'est un esclave RangeExtender (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
            - Gestion des enregistrements en RS485 si c'est un esclave RS485 (idDevice > 0 & idDevice != -1) pour enregistrer ses capteurs comme virtuels auprès du maitre
        -#
        tasmota.add_rule("Wifi", def(value, trigger, msg) RS485Fonctions.changementEtatDemarrage(value, trigger, msg) end)
        tasmota.add_rule("Mqtt", def(value, trigger, msg) RS485Fonctions.changementEtatDemarrage(value, trigger, msg) end)  
        tasmota.add_rule("System", def(value, trigger, msg) RS485Fonctions.changementEtatDemarrage(value, trigger, msg, parametres["modules"]["RS485"]["idModule"], self.jsonRS485) end)	
        

        # Paramétrage port RS485 : gpio_rx:4 gpio_tx:5
        self.serialRS485 = serial(4, 5, parametres["modules"]["RS485"]["debit"], serial.SERIAL_8N1)

        #-     
            Parcours tous les modules paramétrés
            - Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
                Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
                par la fonction 'every_second()'
            - Compte les devices non-virtuelles
            - Compte le nombre de devices activés par type et les range dans un tableau
            - Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage) 
        -#

        # Mets à jour la liste des modules maitres, esclaves et devices de chacun à partir d'un fichier json 'RS485.json'
        var RS485 = persist.find("parametres")["modules"].find("RS485", false)
        if (RS485)
            var cleModule = (RS485["idModule"] == 0 ? "maitre" : "esclave" + str(RS485["idModule"]))

            self.jsonRS485.insert(cleModule, {})
            self.jsonRS485[cleModule].insert("id", RS485["idModule"])
            self.jsonRS485[cleModule].insert("topic", persist.find("parametres")["serveur"]["mqtt"]["topic"])
        end

        # Demande aux modules esclaves leurs parametres
        if RS485["idModule"] == 0 && persist.find("parametres")["modules"].find("activation", "OFF") == "ON" && RS485.find("activation", "OFF") == "ON"
            var payload = "cuve/niveau/esclave" + self.MARQUEUR_SEPARATEUR + ""
            RS485Fonctions.envoiMsgRS485(self.serialRS485, self.CMND_FUNC_JSON, self.delimiteurs, payload)
        end

		# Ajoute les commandes personnalisées si le module est activé
		if persist.find("parametres")["modules"].find("activation", "OFF") == "ON" && RS485.find("activation", "OFF") == "ON"
			if RS485["environnement"].find("pinsRS485s", false)
				# Ajoute les commandes personnalisées
				tasmota.add_cmd('ReglageRS485', RS485Fonctions.ReglageRS485)					
			end
		end

        # Pour test
        # if RS485["idModule"] == 0 && persist.find("parametres")["modules"].find("activation", "OFF") == "ON" && RS485.find("activation", "OFF") == "ON"
        #     var payload = "cuve/niveau/esclave" + self.MARQUEUR_SEPARATEUR + "POWER ON"
        #     tasmota.add_cron("*/10 * * * * *", /-> RS485Fonctions.envoiMsgRS485(self.serialRS485, self.CMND_EXECUTE_CMND, self.delimiteurs, payload), "publish_cmnd_quickly")
        # end
    end

    # Réceptionne chaque trame dans un buffer
    def every_250ms()
        import RS485Fonctions
        import string
        import persist
        import json

        var commande = 0
        var topic = ""
        var data = ""
        var RS485 = persist.find("parametres")["modules"]["RS485"]
        var payload = ""

        # Récupère les messages sur le port RS485 (respecte l'API Tasmota)
        self.buffer = RS485Fonctions.lireMsgRS485(self.serialRS485, self.delimiteurs)

        # On traite le message   
        if (self.buffer)   
            # On découpe le message sur les repères ";" en tableau
            self.buffer = string.split(self.buffer, self.MARQUEUR_SEPARATEUR)
            commande = int(self.buffer[0])
            topic = self.buffer[1]
            data = self.buffer[2]

            # Puis on dispatche selon la réponse reçue vers la fonction associée (Uniquement pour le maitre RS485)
            if persist.find("parametres")["modules"]["RS485"]["idModule"] == 0
                # Traite les paramètres RS485 envoyés par les esclaves
                if commande == self.RESPONSE_FUNC_JSON
                    data = json.load(data)
                    for cle: data.keys()
                        if (self.jsonRS485.find(cle, false)) 
                            self.jsonRS485[cle] = data[cle]
                        else self.jsonRS485.insert(cle, data[cle])  
                        end
                    end
                # Renvoi les données recues vers une fonction qui traitera traitera les données json recus pour mettre à jour une device
                elif commande == self.RESPONSE_PUBLISH_TELE
                    if data != "{}"
                        # Enregistre les data pour ajouter au json sensor par la fonction 'json_append()'
                        self.sensorsRS485 = data
                    end
                end
            end

            # Puis on dispatche selon la commande reçue vers la fonction associée (Uniquement pour l'esclave RS485)
            if (persist.find("parametres")["modules"]["RS485"]["idModule"] > 0)
                # Demande à l'esclave ses paramètres RS485 (Pour tous les esclaves à la fois)
                if commande == self.CMND_FUNC_JSON
                    payload = string.format("tele/%s/SENSOR", persist.find("parametres")["serveur"]["mqtt"]["topic"]) + self.MARQUEUR_SEPARATEUR + 
                                                    json.dump(self.jsonRS485)
                    RS485Fonctions.envoiMsgRS485(self.serialRS485, self.RESPONSE_FUNC_JSON, self.delimiteurs, payload)

                # Demande à l'esclave la réalisation de commande / 1 seconde
                elif commande == self.CMND_FUNC_EVERY_SECOND
                    
                # Demande à l'esclave la réalisation de commande / 100 millisecondes
                elif commande == self.CMND_FUNC_EVERY_100_MSECOND

                # Demande à l'esclave de publier par mqtt une donnée (json) par MQTT sous forme '/tele/%topic%/RESULT'
                elif commande == self.CMND_PUBLISH_TELE

                # Demande à l'esclave la réalisation d'une commande relai par la fonction berry: tasmota.cmd())
                # Pour éxecution d'une commande tasmota OU d'une commande personnalisée
                elif commande == self.CMND_EXECUTE_CMND
                    # Si le topic est celui de l'esclave concerné
                    if (persist.find("parametres")["serveur"]["mqtt"]["topic"] == topic)    tasmota.cmd(data)   end
                end
            end            
        end

        # Initialisation du buffer
        self.buffer = ""
    end

    # Envoi sur le port RS485 des valeurs des capteurs
    def every_second()
        import string
        import RS485Fonctions
        import persist
        import json

        var RS485 = persist.find("parametres")["modules"]["RS485"]

        # Uniquement les esclaves RS485
        var payload = string.format("tele/%s/SENSOR", persist.find("parametres")["serveur"]["mqtt"]["topic"]) + self.MARQUEUR_SEPARATEUR + 
                                        "\"" + persist.find("parametres")["serveur"]["hostname"] + "\": " + 
                                        (json.load(tasmota.read_sensors()) == nil ? "{}" : tasmota.read_sensors())

        if RS485["idModule"] > 0 && persist.find("parametres")["modules"].find("activation", "OFF") == "ON" && RS485.find("activation", "OFF") == "ON"
            RS485Fonctions.envoiMsgRS485(self.serialRS485, self.RESPONSE_PUBLISH_TELE, self.delimiteurs, payload)
        end
    end

    # Ajoute les données retournées par les message avec ordre 'RESPONSE_FUNC_JSON' & 'RESPONSE_PUBLISH_TELE'
    def json_append()
        import persist

        if self.sensorsRS485 != ""
            tasmota.response_append(", " + self.sensorsRS485)
        end
    end

    # Ajoute lesdonnées retournées par les message avec ordre 'RESPONSE_FUNC_JSON' & 'RESPONSE_PUBLISH_TELE'
    # Qu'il faut ajouter à l'affichage sur la page WebSensor
    # Affiche les informations du capteur sur l’interface utilisateur Web
    def web_sensor()
    end

    # ------------- Fonctions qui transmettent une la modification d'état de devices localisées sur l'esclave -------------
    # ------------- Si la device est paramétrée en json comme : virtuel = "ON" && publishMQTT <> ""
    
    # Appelé chaque fois qu’une commande 'Power' est effectuée
    # IDX est une valeur d’indice combinée, avec un bit par relais ou voyant actuellement allumé
    def set_power_handler(cmd, idx)

    end

    # Appelé lorsqu’une interaction avec un Bouton ou un Switch se produit
    # IDX est encodé comme suit : device_save << 24 | Clé << 16 | État << 8 | appareil
    def any_key(cmd, idx)
        log ("CONTROLE_RS485_ANYKEY: ----------------------- rs485 SetPowerHandler ----------------------", LOG_LEVEL_DEBUG)
		log ("CONTROLE_RS485_ANYKEY: Lecture automatisee de l'etat des Boutons & Switchs (Interrupteurs)", LOG_LEVEL_DEBUG)
        log ("CONTROLE_RS485_ANYKEY: cmd = " + str(cmd), LOG_LEVEL_DEBUG)
        log ("CONTROLE_RS485_ANYKEY: device_save = " + str(0xFF & (idx >> 24)), LOG_LEVEL_DEBUG)            # device_save << 24
        log ("CONTROLE_RS485_ANYKEY: key  = " + str(0xFF & (idx >> 16)), LOG_LEVEL_DEBUG)                   # key  << 16 -> key=0 (Bouton) / key=1 (Switch ou Interrupteurs)
        log ("CONTROLE_RS485_ANYKEY: state  = " + str(0xFF & (idx >> 8)), LOG_LEVEL_DEBUG)                  # state  << 8
        log ("CONTROLE_RS485_ANYKEY: device  = " + str(0xFF & idx), LOG_LEVEL_DEBUG)                        # device
    end

    # Appelé à chaque changement d'état de capteurs (analogique,, ds18b20 ....)
    # L'appel à cette fonction est défini dans la fonction 'init()' du module par la fonction tasmota : tasmota.add_rule(trigger:string, f:function [, id:any])
    def changementEtatCapteur()
        
    end
    # ---------------------------------------------------------------------------------------------------------------------
end

# Active le Driver de controle global des modules
controleRS485 = CONTROLE_RS485()
tasmota.add_driver(controleRS485)
#tasmota.add_fast_loop(/-> controleRS485.fast_loop())