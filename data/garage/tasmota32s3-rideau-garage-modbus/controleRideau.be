# Solidifiable (2026-10-20), sur le modele de controleModbus : la classe est portee par le module
# 'controleRideau' ; autoexec le charge par 'import' (version en FLASH, env tasmota32s3-garage-rideau-garage-modbus).
# 'import' appelle AUTOMATIQUEMENT controleRideau_init(m), en pied de fichier, qui porte la garde d'activation.
#@ solidify:controleRideau
var controleRideau = module("controleRideau")

class CONTROLE_RIDEAU : Driver
	# Variables
    var flagINIT        # Flag marquant la fin de l'initialisation du module principal

    # Flags pour les logs à enregistrer
    var indiceLog
    var nbLogsFilesMax
    var fileLogSize_Ko

    # Squelette (2026-10-12) : la porte est pilotee par le driver voletRoulants (et nativement par
    # le maitre P4). Ce driver est pret a recevoir l'affichage web, la telemetrie et le journal.
    def init()
        self.flagINIT = 0

        # Configuration du journal lue dans le persist (modules.rideau.logs), comme la cuve
        self.indiceLog = 0
        self.nbLogsFilesMax = modules["rideau"].find("logs", {}).find("nbLogsFiles", 0)
        self.fileLogSize_Ko = modules["rideau"].find("logs", {}).find("fileLogSize_Ko", 10000)

        logFonctions.log("CONTROLE_RIDEAU: Driver charge (squelette) !", LOG_LEVEL_DEBUG)
        self.flagINIT = 1
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

# Publie la classe dans le module (solidification + import).
controleRideau.CONTROLE_RIDEAU = CONTROLE_RIDEAU

# init() : APPELEE AUTOMATIQUEMENT par 'import controleRideau' (be_module.c:285-296, module_init).
# Ne PAS la rappeler depuis autoexec. Driver enregistre seulement si le module rideau est active ;
# l'instance est publiee dans global.controleRideau.
def controleRideau_init(m)
    import global

    if (modules.find("rideau", {}).find("activation", "OFF") == "ON")
        global.controleRideau = m.CONTROLE_RIDEAU()
        tasmota.add_driver(global.controleRideau)
    end
    return m
end
controleRideau.init = controleRideau_init

# Valeur du module importe depuis le LittleFS (sans elle, import rend nil et init() n'est pas appelee)
return controleRideau
