# Déclaration des librairies utilisées
import persist

# Recense toutes les variables globales
var boolMute = true
var progLoaded = false

# Déclaration des variables de LOG
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

# Charge un fichier ".be" & le supprime si le chargement est OK
import gestionFileFolder

# Supprime le fichier autoexec.be
gestionFileFolder.loadBerryFile("/autoexec.be", "OFF")

# Vérifie si le persist.json est présent et paramétré
if (persist.find("parametres", false))
    # Charge les fonctions accessoires UDP & WebSocket
    gestionFileFolder.loadBerryFile("/controleUDP.be", persist.find("parametres")["serveur"].find("etat", {}).find("etat", "OFF"))

    # Gère le script BERRY global à lancer
    # Charge le Driver de controle global des modules & gestionWeb
    gestionFileFolder.loadBerryFile("/controleGlobal.be")
    gestionFileFolder.loadBerryFile("/controleRangeExtender.be", persist.find("parametres")["serveur"]["rangeExtender"].find("activation", "OFF"))
    gestionFileFolder.loadBerryFile("/controlePAC.be", persist.find("parametres")["modules"]["PAC"].find("activation", "OFF"))

    # A la fin du processus
    progLoaded = true
else log ("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end