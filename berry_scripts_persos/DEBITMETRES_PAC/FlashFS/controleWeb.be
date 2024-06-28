# Gestion des pages internet
# Données GET & POST utilisées :
#	module : quel chapitre du json sera demandé
#   environnement : sous-module
#	modifParam : quel est le chapitre qui sera modifié par requête
# 	script : le type de script 'javascript' demandé par le serveur
#	commande : type de commande berry à réaliser

# Attention : autoriser l'access-crossing sur le site distant si vous y accédez
# Ajouter 'dans la section <Directory> de 'httpd.conf' d'Apache2 : Header set Access-Control-Allow-Origin "*"
# Ajouter le fichier 'componentes.json' dans le dossier de votre serveur

var controleWeb

class CONTROLE_WEB
    # Variables
	var parametres
    var formSelection
    var categorieSelection
    var sensors

    def init()
        import json

        # Lance le driver de CONTROLE_GENERAL
        #super(self).init()

        self.formSelection = ""
        self.categorieSelection = ""
    end

    def every_second()
    end


	#- Création de boutons dans le menu principal -#
	def web_add_main_button()
        import webserver

        log ("WEBSERVER: Affichage du bouton !", LOG_LEVEL_DEBUG)
		webserver.content_send("<p></p><button class='button bgrn' onclick='window&#46;location&#46;href=\"/modules?module=serveur&categorie=generale\"'>Réglages des modules</button>")

        # Ajoute autant de boutons que de modules connectés au RangeExtender
		# Uniquement si c'est un Point d'accès Range Extender
		if controleGeneral.parametres["serveur"]["rangeExtender"].find("idModuleRangeExpender", 99) == 0
            webserver.content_send("<hr>")
            for cle: controleGeneral.modulesConnectes.keys()
                if controleGeneral.modulesConnectes[cle] != nil
                    var url = "http://" + controleGeneral.parametres["serveur"]["IP"]["IPAddress"] + ":" + str(controleGeneral.modulesConnectes[cle]["routagePort"])
                    var titre = "Module " + controleGeneral.modulesConnectes[cle]["nom"]

                    # Ouverture de la page dans un nouvel onglet
                    webserver.content_send("<p></p><button class='button bgrn' onclick='window&#46;open(\"" + url + "\")'>" + titre + "</button>")
                end
            end
        end
    end	

	# Charge les appels aux fonctions selon l'url
	def web_add_handler()
        import webserver

        webserver.on("/modules", / -> self.affichePageParametres(), webserver.HTTP_GET)	
		webserver.on("/json", / -> self.envoiJson(), webserver.HTTP_ANY)	
        webserver.on("/capteurs", / -> self.etatCapteurs(), webserver.HTTP_GET)	
	end
end

# Charge la gestion des pages web
controleWeb = CONTROLE_WEB()
tasmota.add_driver(controleWeb)	
controleWeb.web_add_handler()