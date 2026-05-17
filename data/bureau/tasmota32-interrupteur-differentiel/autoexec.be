# Déclaration des librairies utilisées
import persist
import partition_wizard        # Importe la librairie Partition_Wizard

# Recense toutes les variables globales
var controleGeneral

# Déclaration des variables de LOG
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4

var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

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
if (persist._p != nil || persist._p != {})
    # Compile autoexec.be & les modules
    gestionFileFolder.compileModule("/autoexec", "ON")
    gestionFileFolder.compileModule("/configGlobal", "ON")
    gestionFileFolder.compileModule("/configDevices", "ON")
    gestionFileFolder.compileModule("/configModules", "ON")
    gestionFileFolder.compileModule("/gestionFileFolder", "ON")
    gestionFileFolder.compileModule("/globalFonctions", "ON")
    gestionFileFolder.compileModule("/diversFonctions", "ON")
    gestionFileFolder.compileModule("/webFonctions", "ON")
    # gestionFileFolder.compileModule("/garageFonctions", "ON")
    # gestionFileFolder.compileModule("/udpFonctions")
    # gestionFileFolder.compileModule("/rangeExtenderFonctions")
    # gestionFileFolder.compileModule("/modbusFonctions")
    # gestionFileFolder.compileModule("/loRaWanFonctions")
    # gestionFileFolder.compileModule("/vrFonctions", drivers.find("voletRoulants", {}).find("activation", "OFF"))
    # gestionFileFolder.compileModule("/discoveryFonctions", serveur["discovery"].find("activation", "OFF"))

    #Compile les modules internes à Tasmota
    # gestionFileFolder.compileModule("/leds_panel", "ON")
    gestionFileFolder.compileModule("/partition_wizard", "ON")

    # Charge les Drivers nécessaires au fonctionnement diu module Tasmota
    gestionFileFolder.loadBerryFile("/controleGeneral", "ON", "ON")
    # gestionFileFolder.loadBerryFile("/i2c_ads1115", drivers["I2C"]["environnement"]["ADS1115"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/i2c_mcp23017", drivers["I2C"]["environnement"]["MCP23017"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/modBus_Conn16channel", drivers["ModBus"]["environnement"]["Conn16channel"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/modbus_TasmotaSlaveModBus", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus1"].find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/controleWeb", serveur.find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleUDP", serveur["udp"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleModbus", drivers["ModBus"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleRangeExtender", serveur["rangeExtender"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleLoRaWan", drivers["LoRaWan"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleVoletRoulants", drivers.find("voletRoulants", {}).find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleDiscovery", serveur["discovery"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleGarage", modules.find("garage", {}).find("activation", "OFF"), "ON")
else log("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end

# Modules persos dont Tasmota Berry a besoin pour fonctionner
# configDevices
# configModules
# configGlobal
# diversFonctions
# gestionFileFolder
# globalFonctions
# garageFonctions
# webFonctions
# rangeExtenderFonctions
# udpFonctions
# modbusFonctions
