# Recense toutes les variables globales
var boolMute = true
#var progLoaded = false
var controleGeneral

# Déclaration des variables de LOG
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

# Charge un fichier ".be" & le supprime si le chargement est OK
def compileModules()
    # Déclaration des librairies utilisées
    import persist
    import gestionFileFolder

    var test = true

    # Vérifie si le persist.json est présent et paramétré
    if (persist.find("parametres", false))
        # Compile autoexec.be & les modules
        test = test && gestionFileFolder.compileModule("/autoexec")
        test = test && gestionFileFolder.compileModule("/configGlobal")
        test = test && gestionFileFolder.compileModule("/gestionFileFolder")
        test = test && gestionFileFolder.compileModule("/globalFonctions")
        test = test && gestionFileFolder.compileModule("/RS485Fonctions", persist.find("parametres")["modules"]["RS485"].find("activation", "OFF"))

        return test
    else    
        log ("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
        return false
    end
end

# Charge un fichier ".be" & le supprime si le chargement est OK
def chargeFichiers()
    # Déclaration des librairies utilisées
    import persist
    import gestionFileFolder

    # Vérifie si le persist.json est présent et paramétré
    if (persist.find("parametres", false))
        # Charge les fonctions accessoires UDP & WebSocket
        gestionFileFolder.loadBerryFile("/controleUDP", persist.find("parametres")["serveur"].find("udp", {}).find("activation", "OFF"))


        # Gère le script BERRY global à lancer
        # Charge le Driver de controle global des modules & gestionWeb
        gestionFileFolder.loadBerryFile("/controleGlobal")
        gestionFileFolder.loadBerryFile("/controleRS485", persist.find("parametres")["modules"]["RS485"].find("activation", "OFF"))
        gestionFileFolder.loadBerryFile("/controleCuve", persist.find("parametres")["modules"]["cuve"].find("activation", "OFF"))
        

    else log ("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
    end

    # Execute la focntion au démarrage
    log ("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
    gestionFileFolder.listeEtRepartitLesFichiers()
end

# Charge un fichier ".be" & le supprime si le chargement est OK
if (compileModules())
    print("CHARGE FICHIERS EFFECTUEE")
    chargeFichiers()
# Erreur decompilation d'un des fichiers => on recommence
else 
    # print("ON RECOMMENCE COMPILATION")
    # print(type(controleRS485))
    # tasmota.add_cron("*/10 * * * * *", compileModules, "compileModules")
    # compileModules()
end