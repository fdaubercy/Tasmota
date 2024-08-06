# Déclaration des librairies utilisées
import persist
import path

# Recense toutes les variables globales
var boolMute = true
var progLoaded = false
var controleGeneral
var controleRangeExtender

# Déclaration des variables de LOG
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

# Charge un fichier ".be" & le supprime si le chargement est OK
import gestionFileFolder

# Vérifie si le persist.json est présent et paramétré
if (persist.find("parametres", false))
    # Compile autoexec.be & les modules
    gestionFileFolder.compileModule("/autoexec")
    gestionFileFolder.compileModule("/configGlobal")
    gestionFileFolder.compileModule("/gestionFileFolder")
    gestionFileFolder.compileModule("/globalFonctions")
    gestionFileFolder.compileModule("/rangeExtenderFonctions", persist.find("parametres")["serveur"]["rangeExtender"].find("activation", "OFF"))
    gestionFileFolder.compileModule("/webFonctions", persist.find("parametres")["serveur"].find("activation", "OFF"))
    gestionFileFolder.compileModule("/displayFonctions", persist.find("parametres")["modules"].find("ecran", {}).find("activation", "OFF"))
    gestionFileFolder.compileModule("/ts_calibrate", persist.find("parametres")["modules"].find("ecran", {}).find("activation", "OFF"))

    # Charge les fonctions accessoires UDP & WebSocket
    gestionFileFolder.loadBerryFile("/controleUDP", persist.find("parametres")["serveur"].find("etat", {}).find("etat", "OFF"))

    # Gère le script BERRY global à lancer
    # Charge le Driver de controle global des modules & gestionWeb
    gestionFileFolder.loadBerryFile("/controleGlobal")
    gestionFileFolder.loadBerryFile("/controleRangeExtender", persist.find("parametres")["serveur"]["rangeExtender"].find("activation", "OFF"))
    gestionFileFolder.loadBerryFile("/controleDisplay", persist.find("parametres")["modules"].find("ecran", {}).find("activation", "OFF"))
    gestionFileFolder.loadBerryFile("/controleWeb", persist.find("parametres")["serveur"].find("activation", "OFF"))

    # Charge le module en memoire lors de la 1ere utilisation
    if persist.find("parametres")["modules"].find("ecran", {}).find("activation", "OFF")
        var wd = tasmota.wd
        tasmota.add_cmd("DisplayCalibrate",
            def ()
                import sys
                var path = sys.path()
            
                path.push(wd)
                import ts_calibrate
                path.pop()
            
                tasmota.set_timer(0, /-> ts_calibrate.start())
                tasmota.resp_cmnd_done()
            end
        )
    end

    # A la fin du processus
    progLoaded = true
else log ("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end

# Execute la focntion au démarrage
log ("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
gestionFileFolder.listeEtRepartitLesFichiers()