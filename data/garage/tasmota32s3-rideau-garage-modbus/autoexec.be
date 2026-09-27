# Déclaration des librairies utilisées
import persist
# import partition_wizard        # Importe la librairie Partition_Wizard

# Recense toutes les variables globales
var controleGeneral = {}

# Déclaration des variables de LOG
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4

logSerial = LOG_LEVEL_INFO
logWeb = LOG_LEVEL_INFO

serveur = persist.serveur
diverses = persist.diverses
modules = persist.modules
drivers = persist.drivers
boolMute = diverses.find("cmdMute", false)

# Allege le persist en RAM AVANT tout le reste :
#   - listes vides de cles connues supprimees (leurs lecteurs utilisent .find(cle, [])) ;
#   - environnement des drivers inactifs mis en veille dans /json/driversInactifs.json (rien n'est perdu).
# Import de niveau fichier : cree la globale 'diversFonctions' (module solidifie).
import diversFonctions
if (diversFonctions.elagueListesVides(persist._p) > 0)     persist.save(true)     end
diversFonctions.hiberneDriversInactifs()

# Execute la fonction au démarrage
log("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
import gestionFileFolder
gestionFileFolder.listeEtRepartitLesFichiers()

# Modules SOLIDIFIES dont des fonctions retrouvent leur propre module par son nom GLOBAL
# (GETNGBL) : leur code de niveau fichier ne s'execute pas, ce nom n'existe donc que si
# on l'importe ICI, au niveau fichier (un import de niveau fichier cree la globale,
# comme pour gestionFileFolder ci-dessus). Sinon : "'configGlobal' undeclared" au boot.
# Recense dans le bytecode solidifie (GETNGBL vers un nom de module) le 2026-09-26.
import configGlobal
import globalFonctions
import webFonctions
import modbusFonctions

# Vérifie si le persist.json est présent et paramétré
if (persist._p != nil && persist._p.size() != 0)
    # Compile les modules
    gestionFileFolder.compileModule("/configGlobal", "ON")
    gestionFileFolder.compileModule("/configDevices", "ON")
    gestionFileFolder.compileModule("/configModules", "ON")
    gestionFileFolder.compileModule("/gestionFileFolder", "ON")
    gestionFileFolder.compileModule("/globalFonctions", "ON")
    gestionFileFolder.compileModule("/diversFonctions", "ON")
    gestionFileFolder.compileModule("/webFonctions", serveur.find("activation", "OFF"))
    gestionFileFolder.compileModule("/udpFonctions", serveur["udp"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/tcpFonctions", serveur["tcp"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/rangeExtenderFonctions", serveur["rangeExtender"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/modbusFonctions", drivers["ModBus"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/loRaWanFonctions", drivers["LoRaWan"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/vrFonctions", drivers.find("voletRoulants", {}).find("activation", "OFF"))
    gestionFileFolder.compileModule("/discoveryFonctions", serveur["discovery"].find("activation", "OFF"))

    # Charge les Drivers nécessaires au fonctionnement diu module Tasmota
    # controleGeneral/LedTemoin/Web sont SOLIDIFIES : charges par 'import' (version en
    # FLASH via load_native), au lieu de loadBerryFile (qui recompile en RAM).
    # 'import' appelle AUTOMATIQUEMENT init(module) du module (be_module.c:285-296) :
    # init() publie l'instance dans global.controleXxx et fait add_driver, comme avant.
    # Ne PAS rappeler _ctrl.init() ici : ce serait le constructeur de l'instance.
    # Garder controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON).
    do
        import controleGeneral as _ctrl
    end
    do
        import controleLedTemoin as _ctrl
    end
    do import i2c_ads1115 as _ctrl end   # solidifie : init() porte la garde d'activation
    do import i2c_mcp23017 as _ctrl end   # solidifie : init() porte la garde d'activation
    do import modBus_Conn16channels as _ctrl end   # solidifie : init() porte la garde d'activation
    do import modBus_TasmotaSlaveModBus as _ctrl end   # solidifie : init() porte la garde d'activation
    do
        import controleWeb as _ctrl
    end
    do import controleUDP as _ctrl end   # solidifie : init() porte la garde d'activation
    # gestionFileFolder.loadBerryFile("/controleTCP", serveur["tcp"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleModbus", drivers["ModBus"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleRangeExtender", serveur["rangeExtender"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleLoRaWan", drivers["LoRaWan"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleVoletRoulants", drivers.find("voletRoulants", {}).find("activation", "OFF"), "ON")
    do import controleDiscovery as _ctrl end   # solidifie : init() porte la garde d'activation

    # Compile autoexec.be
    # gestionFileFolder.compileModule("/autoexec", "ON")
else log("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end
