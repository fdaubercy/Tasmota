# Déclaration des librairies utilisées
import persist
# import partition_wizard        # Importe la librairie Partition_Wizard

# Recense toutes les variables globales
var controleGeneral = {}

# Déclaration des variables de LOG
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4            # niveau Berry "detail" : logFonctions.log() l'emet au niveau 3 du firmware (jamais 4, donc sans les BRY: GC)

serveur = persist.serveur
diverses = persist.diverses
modules = persist.modules
drivers = persist.drivers
boolMute = diverses.find("cmdMute", false)

# Fonction de log commune (charte : logFonctions.be). Importee AVANT tout le reste :
# les modules charges ensuite loguent par logFonctions.log(). Import de niveau fichier :
# cree la globale 'logFonctions' (module solidifie).
import logFonctions

# Allege le persist en RAM AVANT tout le reste (carte sans PSRAM) :
#   - listes vides de cles connues supprimees (leurs lecteurs utilisent .find(cle, [])) ;
#   - environnement des drivers inactifs mis en veille dans /json/driversInactifs.json (rien n'est perdu).
# Import de niveau fichier : cree la globale 'diversFonctions' (module solidifie, cf. plus bas).
import diversFonctions
if (diversFonctions.elagueListesVides(persist._p) > 0)     persist.save(true)     end
diversFonctions.hiberneDriversInactifs()

# Execute la fonction au démarrage
logFonctions.log("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
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

# Vérifie si le persist.json est présent et paramétré
if (persist._p != nil && persist._p.size() != 0)
    # Compile les modules
    gestionFileFolder.compileModule("/configGlobal", "ON")
    gestionFileFolder.compileModule("/configDevices", "ON")
    gestionFileFolder.compileModule("/configModules", "ON")
    gestionFileFolder.compileModule("/gestionFileFolder", "ON")
    gestionFileFolder.compileModule("/globalFonctions", "ON")
    gestionFileFolder.compileModule("/diversFonctions", "ON")
    gestionFileFolder.compileModule("/logFonctions", "ON")
    gestionFileFolder.compileModule("/webFonctions", serveur.find("activation", "OFF"))
    # Service reseau NON active -> ni compile ni charge. Ne pas compter sur le 2e argument de
    # loadBerryFile/compileModule : il ne filtre PAS le chargement (garde commentee dans
    # gestionFileFolder.be:326 et :348-351) -> les 4 services se chargeaient meme a OFF
    # (+~40 Ko de Berry, crash memoire au boot sur ESP32 sans PSRAM). Constate le 2026-09-27.
    if serveur["udp"].find("activation", "OFF") == "ON"    gestionFileFolder.compileModule("/udpFonctions", serveur["udp"].find("activation", "OFF"))    end
    if serveur["tcp"].find("activation", "OFF") == "ON"    gestionFileFolder.compileModule("/tcpFonctions", serveur["tcp"].find("activation", "OFF"))    end
    if serveur["rangeExtender"].find("activation", "OFF") == "ON"    gestionFileFolder.compileModule("/rangeExtenderFonctions", serveur["rangeExtender"].find("activation", "OFF"))    end
    # gestionFileFolder.compileModule("/modbusFonctions", drivers["ModBus"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/loRaWanFonctions", drivers["LoRaWan"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/vrFonctions")


    # Compile les modules internes à Tasmota
    # gestionFileFolder.compileModule("/leds_panel", "ON")
    # gestionFileFolder.compileModule("/partition_wizard", "ON")

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
    # gestionFileFolder.loadBerryFile("/i2c_ads1115", drivers["I2C"]["environnement"]["ADS1115"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/i2c_mcp23017", drivers["I2C"]["environnement"]["MCP23017"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/modBus_Conn16channels", drivers["ModBus"]["environnement"]["Conn16channels"].find("activation", "ON"), "ON")
    # gestionFileFolder.loadBerryFile("/modBus_TasmotaSlaveModBus", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].find("activation", "ON"), "ON")
    do
        import controleWeb as _ctrl
    end
    if serveur["udp"].find("activation", "OFF") == "ON"    import controleUDP as _ctrl    end
    if serveur["tcp"].find("activation", "OFF") == "ON"    import controleTCP as _ctrl    end
    # gestionFileFolder.loadBerryFile("/controleModbus", drivers["ModBus"].find("activation", "OFF"), "ON")
    if serveur["rangeExtender"].find("activation", "OFF") == "ON"    import controleRangeExtender as _ctrl    end
    # gestionFileFolder.loadBerryFile("/controleLoRaWan", drivers["LoRaWan"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleVoletRoulants", drivers.find("voletRoulants", {}).find("activation", "OFF"), "ON")
    if serveur["discovery"].find("activation", "OFF") == "ON"    import controleDiscovery as _ctrl    end
    gestionFileFolder.loadBerryFile("/controlePompeVideCave", modules["pompeVideCave"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleGrenier", modules.find("grenier", {}).find("activation", "OFF"), "ON")

    # NE PAS compiler autoexec.be en .bec : tasmota.compile() compile en contexte LOCAL
    # (tasmota_class.be:480, upstream #23457). Le .bec tournerait alors sous le nom 'loader'
    # et tous les import/var/affectations de niveau fichier ci-dessus deviendraient des
    # LOCALES : 'configGlobal' undeclared, puis 'controleGeneral' undeclared dans les regles,
    # des le DEUXIEME demarrage (le premier, en .be, fonctionne). Constate le 2026-09-26.
    # gestionFileFolder.compileModule("/autoexec", "ON")
else logFonctions.log("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end

