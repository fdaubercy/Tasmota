#-
    LE JSON '/json/discovery.json' CONTIENT DES PARAMETRES UTILISES DANS LES SCRIPTS SUIVANTS:
        - modbusFonctions.be -> modifications réalisées
        - udpFonctions.be -> modifications réalisées
        - rangeExtenderFonctions.be -> modifications réalisées
-#

#- 
    Driver de gérer l'enregistrement et le contrôle des modules Tasmota connectés au réseau local
    - Les modules Maitres RangeExtender redirigent les connexions vers les modules esclaves
    * via le routage NAPT (Network Address and Port Translation)

    - Les modules Tasmota sont accessibles à l'extérieur du réseua local via le DNS de la Freebox
    * si le port est redirigé dans la Freebox vers le module Tasmota
    * Les redirections de port sur la box internet doivent être faites manuellement par l'utilisateur
    * Le protocole de calcul des ports extérieurs de chaque module est : 10000 + dernier identifiant de l'IP locale du module
        ex : module Tasmota en IP locale : 192.168.0.43
        ex : port distant ouvert pour ce module Tasmota : 10000 + 43 = 10043
    * Le protocole de calcul des ports extérieurs de chaque module esclave RangeExtender est : 10000 + dernier identifiant de l'IP locale du module maitre + 8080 + id - 1
        ex : module Tasmota Maitre RangeExtender -> port extérieur ouvert : 10043
        ex : module Tasmota Esclave N°1 RangeExtender -> port extérieur ouvert : 10043 + 8080 + 1 - 1 = 18123
    - La box internet doit rediriger les ports vers l'IP locale du module Tasmota:
        * ex : port 10043 -> vers le port 80 & le module Tasmota d'adresse IP locale 192.168.0.43
        * ex : port 18123 -> vers le port 8080 & le module Tasmota esclave RangeExtender N°1 dont le maitre à l'adresse IP locale 192.168.0.43
-#

# Rendu solidifiable (2026-09-27), sur le modele de controleGeneral : la classe est portee
# par le module import-able 'controleDiscovery'. autoexec le charge par 'import' (version en FLASH
# via load_native), plus par loadBerryFile (qui recompilait la classe en RAM).
# 'import' appelle AUTOMATIQUEMENT controleDiscovery_init(m), en pied de fichier.
#@ solidify:controleDiscovery
var controleDiscovery = module("controleDiscovery")

class CONTROLE_DISCOVERY : Driver
    # Variables

    def init()
        import mqtt
        import discoveryFonctions

        discoveryFonctions.log("CONTROLE_DISCOVERY: Initialisation du driver de contrôle des modules Tasmota sur le réseau local", LOG_LEVEL_INFO)
        discoveryFonctions.log("CONTROLE_DISCOVERY: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)

        # Ajoute les règles lancés selon l'étape de démarrage de la device tasmota
        # tasmota.add_rule("System", discoveryFonctions.changementEtatDemarrage, "controleDiscovery_System")	
        tasmota.add_rule("Wifi", def(value, trigger, msg) discoveryFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleDiscovery_Wifi")
        tasmota.add_rule("Mqtt", def(value, trigger, msg) discoveryFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleDiscovery_Mqtt")
		# tasmota.add_rule("Time", def(value, trigger, msg) discoveryFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleDiscovery_Time")

        # S'abonne aux messages MQTT reçus pour le module de découverte
        # Les réponses sont gérés par la fonction 'mqtt_data'
        mqtt.subscribe("tasmota/discovery/+/#", /topic, idx, data, databytes -> discoveryFonctions.mqtt_discovery(topic, idx, data, databytes))

        # Détecte les messages MQTT LWT (Last Will and Testament) pour supprimer les modules Tasmota du json discovery en cas de déconnexion du réseau local
        mqtt.subscribe("tele/+/LWT", /topic, idx, data, databytes -> discoveryFonctions.mqtt_lwt(topic, idx, data, databytes))
        mqtt.subscribe("tele/+/+/LWT", /topic, idx, data, databytes -> discoveryFonctions.mqtt_lwt(topic, idx, data, databytes))
        mqtt.subscribe("tele/+/+/+/LWT", /topic, idx, data, databytes -> discoveryFonctions.mqtt_lwt(topic, idx, data, databytes))

        # Ajoute les commandes personnalisées si le module est activé
		tasmota.add_cmd('ReglageDiscovery', / cmd, idx, payload, payload_json -> discoveryFonctions.reglageDiscovery(cmd, idx, payload, payload_json))
    end

	#- Création de boutons dans le menu 'Tools' -#
    # Bouton renvoyant vers la page listannt tous les modules tasmota découverts
    def web_add_management_button()
        import webserver
        import discoveryFonctions

        # Test
        discoveryFonctions.log("ADD_BUTTON_DISCOVERY: -------------------- controleDiscovery web_add_management_button -------------------", LOG_LEVEL_DEBUG_PLUS)
        discoveryFonctions.log("ADD_BUTTON_DISCOVERY: Referer = " +  (webserver.header("Referer") != nil ? webserver.header("Referer") : ""), LOG_LEVEL_DEBUG_PLUS)
        discoveryFonctions.log("ADD_BUTTON_DISCOVERY: Host = " + webserver.header("Host"), LOG_LEVEL_DEBUG_PLUS)

        # Affiche le bouton de réglage des paramètres Tasmota enregistrés en json
        discoveryFonctions.log("ADD_BUTTON_DISCOVERY: Affichage du bouton !", LOG_LEVEL_DEBUG)
		webserver.content_send("<p></p><button class=\"button bgrn\" onclick=\"window.location.href='/discovery'\">Modules Tasmota Connectés</button>")
    end

	# Charge les appels aux fonctions selon l'url
	def web_add_handler()
        import discoveryFonctions
        import webserver

        webserver.on("/discovery", / -> discoveryFonctions.affichePageDiscovery(), webserver.HTTP_GET)	
    end
end

# Publie la classe dans le module (solidification + import).
controleDiscovery.CONTROLE_DISCOVERY = CONTROLE_DISCOVERY

# init() : APPELEE AUTOMATIQUEMENT par 'import controleDiscovery' (be_module.c:285-296, module_init).
# Ne PAS la rappeler depuis autoexec. Porte la garde d'activation (seule vraie
# desactivation) et remplace le code de niveau fichier d'avant.
# Publie aussi le nom GLOBAL 'discoveryFonctions' : les fonctions de ce module solidifie
# s'appellent entre elles par ce nom, qu'un module natif ne cree pas lui-meme.
def controleDiscovery_init(m)
    import global
    import discoveryFonctions
    global.discoveryFonctions = discoveryFonctions

    if (serveur["discovery"].find("activation", "OFF") == "ON")
        var inst = m.CONTROLE_DISCOVERY()
        global.controleDiscovery = inst
        tasmota.add_driver(inst)
        inst.web_add_handler()
    end
    return m
end
controleDiscovery.init = controleDiscovery_init
