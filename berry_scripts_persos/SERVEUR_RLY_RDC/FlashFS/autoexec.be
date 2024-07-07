# Déclaration des librairies utilisées
import persist

# Recense toutes les variables globales
var boolMute = true
var progLoaded = false
var controleGeneral

# Déclaration des variables de LOG
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

# Vérifie si le persist.json est présent et paramétré
if (persist.find("parametres", false))
    # Vérifie si il y a une carte SD et des fichiers à copier dessus au 1er démarrage
    if persist.find("parametres")["diverses"]["SD"].find("activation", "OFF") == "ON"
        load("/gestionFileFolder.be")
    end

    # Charge les fonctions utilisées
    log ("AUTO_EXE: Charge les fonctions globales !", LOG_LEVEL_DEBUG)
    load("/globalFonctions.be")
    if persist.find("parametres")["serveur"].find("activation", "OFF") == "ON"
        load("/webFonctions.be")
    end

    # Gère le script BERRY global à lancer
    # Charge le Driver de controle global des modules
    log("------------------------------ ACTIVATION CONTROLE GLOBAL ------------------------------", LOG_LEVEL_INFO)
    log ("AUTO_EXE: Lance le Driver 'CONTROLE_GENERAL' !", LOG_LEVEL_DEBUG)
    load("/controleGlobal.be")

    log("-------------------------------- ACTIVATION GESTION WEB --------------------------------", LOG_LEVEL_INFO)
    if persist.find("parametres")["serveur"].find("activation", "OFF") == "ON"
        load("/gestionWeb.be")
    end

    log("----------------------------- ACTIVATION GESTION COMMANDES -----------------------------", LOG_LEVEL_INFO)
    load("/commandes.be")

    # A la fin du processus
    progLoaded = true
else log ("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end