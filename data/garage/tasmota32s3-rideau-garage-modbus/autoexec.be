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

# Execute la fonction au démarrage
log("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
import gestionFileFolder
gestionFileFolder.listeEtRepartitLesFichiers()

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
    gestionFileFolder.loadBerryFile("/controleGeneral", "ON", "ON")
    gestionFileFolder.loadBerryFile("/controleLedTemoin", "ON", "ON")
    gestionFileFolder.loadBerryFile("/i2c_ads1115", drivers["I2C"]["environnement"]["ADS1115"].find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/i2c_mcp23017", drivers["I2C"]["environnement"]["MCP23017"].find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/modBus_Conn16channels", drivers["ModBus"]["environnement"]["Conn16channels"].find("activation", "ON"), "ON")
    gestionFileFolder.loadBerryFile("/modBus_TasmotaSlaveModBus", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].find("activation", "ON"), "ON")
    gestionFileFolder.loadBerryFile("/controleWeb", serveur.find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/controleUDP", serveur["udp"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleTCP", serveur["tcp"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleModbus", drivers["ModBus"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleRangeExtender", serveur["rangeExtender"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleLoRaWan", drivers["LoRaWan"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleVoletRoulants", drivers.find("voletRoulants", {}).find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/controleDiscovery", serveur["discovery"].find("activation", "OFF"), "ON")

    # Compile autoexec.be
    # gestionFileFolder.compileModule("/autoexec", "ON")
else log("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end
