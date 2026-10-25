# Définition du module
#@ solidify:webFonctions
var webFonctions = module("webFonctions")

def webFonctions_log(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "serveurWeb")
end
webFonctions.log = webFonctions_log

# Règles sur changement d'état lors du démarrage de Tasmota
def webFonctions_changementEtatDemarrage(value, trigger, msg)
    import string
    import mqtt

	# Test
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: -------------------- webServer changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	webFonctions.log("WEBSERVER_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}

	# Pas de "deballage" de 'value' ici (inutilise dans cette fonction) : l'ancienne boucle
	# 'for cle: value.keys() value = value[cle] end' levait des la 2e cle (2026-10-24, audit N9/P5.8).

    tasmota.yield()

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
            # webFonctions.tcp = tcpserver(webFonctions.port)
            # webFonctions.log(">>>>>>>>>>>>>>>>>>>>>>>>>>>TCP_SERVEUR: Connexion: OK", LOG_LEVEL_DEBUG)

            # Le miroir du ruban WS2812 (ex-leds_panel.bec charge ici) est servi par
            # ledsPanelFonctions sur le port 80 : routes posees par controleWeb.web_add_handler (2026-10-11)
        elif msg[trigger].find("Save", 0)
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
    end
end
webFonctions.changementEtatDemarrage = webFonctions_changementEtatDemarrage

# Modifie les paramètres en json
def webFonctions_traiteCommandeHTTP(typeModule, categorie, commande)
    import string

    var resultat = ""

    # Test : Parcours les données POST recues
	webFonctions.log("WEBSERVER_TRAITE_COMMANDE: -------------------- webServer traiteCommandeHTTP -------------------", LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("WEBSERVER_TRAITE_COMMANDE: typeModule=" + str(typeModule), LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("WEBSERVER_TRAITE_COMMANDE: categorie=" + str(categorie), LOG_LEVEL_DEBUG_PLUS)
    webFonctions.log("WEBSERVER_TRAITE_COMMANDE: commande=" + str(commande), LOG_LEVEL_DEBUG_PLUS)

    tasmota.yield()

    # Réalise l'action
	# Modifie un paramètre en json +/- Redémarre
    if (commande == "modifParam")
        webFonctions.log("WEBSERVER_TRAITE_COMMANDE: Modification des paramètres en json !", LOG_LEVEL_DEBUG)
    # Execute une commande Tasmota paramétrée +/- Redémarre
    else
        webFonctions.log(string.format("WEBSERVER_TRAITE_COMMANDE: Exécute une commande Tasmota : %s!", "tasmota.cmd('" + commande + "')"), LOG_LEVEL_DEBUG)
        resultat = tasmota.cmd(commande)        #, boolMute)
    end

    return resultat
end
webFonctions.traiteCommandeHTTP = webFonctions_traiteCommandeHTTP

# Retourne le module lors de l'importation
return webFonctions