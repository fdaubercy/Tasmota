var controleRideau

class CONTROLE_RIDEAU : Driver
	# Variables
    var flagINIT        # Flag marquant la fin de l'initialisation du module principal

    # Flags pour les logs à enregistrer
    var indiceLog
    var nbLogsFilesMax
    var fileLogSize_Ko

    def init()

    end

    def every_second()
    end

    # Affiche les capteurs du module cuve sur la page web
    def web_sensor()
        # Rien à afficher
    end

    # Ajoute les données des capteurs de rideau de garage à la réponse JSON
    def json_append()
        # Rien à ajouter
    end

    # Enregistre dans les logs les états du capteurs et relais de rideau de garage
    def enregistreLogs(fileChemin)
        # Rien à enregistrer
    end
end

# Active le Driver de controle global des modules
controleRideau = CONTROLE_RIDEAU()
tasmota.add_driver(controleRideau)