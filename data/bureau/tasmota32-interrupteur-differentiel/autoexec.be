# Déclaration des librairies utilisées
import persist
import partition_wizard        # Importe la librairie Partition_Wizard

# Recense toutes les variables globales
var controleGeneral

# Déclaration des variables de LOG
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4            # niveau Berry "detail" : logFonctions.log() l'emet au niveau 3 du firmware (jamais 4, donc sans les BRY: GC)

serveur = persist.serveur
diverses = persist.diverses
modules = persist.modules
drivers = persist.drivers
# Garde de tete (audit P10.1, constat B1, 2026-10-23) : un persist vide, corrompu ou prive d'un de
# ses 4 blocs faisait planter la ligne suivante (diverses.find sur nil) AVANT tout log : carte muette.
# Persist invalide -> rien de ce qui le lit n'est execute, l'erreur est journalisee en fin de fichier.
var persistValide = isinstance(serveur, map) && isinstance(diverses, map) && isinstance(modules, map) && isinstance(drivers, map)
boolMute = (persistValide ? diverses.find("cmdMute", false) : true)

# Fonction de log commune (charte : logFonctions.be). Importee AVANT tout le reste :
# les modules charges ensuite loguent par logFonctions.log(). Import de niveau fichier :
# cree la globale 'logFonctions' (module solidifie).
import logFonctions

# Allege le persist en RAM AVANT tout le reste (carte sans PSRAM), comme la cave :
#   - listes vides de cles connues supprimees (leurs lecteurs utilisent .find(cle, [])) ;
#   - environnement des drivers inactifs mis en veille dans /json/driversInactifs.json (rien n'est perdu).
# Import de niveau fichier : cree la globale 'diversFonctions' (module solidifie, cf. plus bas).
import diversFonctions
if (persistValide && diversFonctions.elagueListesVides(persist._p) > 0)     persist.save(true)     end
if (persistValide)    diversFonctions.hiberneDriversInactifs()    end

# Execute la fonction au démarrage
logFonctions.log("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
import gestionFileFolder
gestionFileFolder.listeEtRepartitLesFichiers()

# Modules SOLIDIFIES dont des fonctions retrouvent leur propre module par son nom GLOBAL
# (GETNGBL) : leur code de niveau fichier ne s'execute pas, ce nom n'existe donc que si
# on l'importe ICI, au niveau fichier (un import de niveau fichier cree la globale,
# comme pour gestionFileFolder ci-dessus). Sinon : "'configGlobal' undeclared" au boot.
# Meme liste que la cave (recensee dans le bytecode solidifie le 2026-09-26).
import configGlobal
import globalFonctions
import webFonctions

# Charge un module SANS que son echec arrete les suivants (audit B2/B5, P10.2, 2026-10-24) : avant, une
# exception dans un controleXxx (cle absente du persist, peripherique muet...) interrompait l'autoexec et
# privait la carte de tous les modules charges apres lui. L'echec est journalise, le chargement continue.
def chargeModule(nom, chargement)
    try
        chargement()
    except .. as e, m
        logFonctions.log("AUTO_EXE_ERREUR: echec du chargement de '" + nom + "' : " + str(e) + " - " + str(m) + " (modules suivants charges quand meme) !", LOG_LEVEL_ERREUR)
    end
end

# Vérifie si le persist.json est présent et paramétré
if (persistValide)
    # Compile les modules (no-op pour les modules solidifies : leur .be n'est plus sur le LittleFS)
    gestionFileFolder.compileModule("/configGlobal", "ON")
    gestionFileFolder.compileModule("/configDevices", "ON")
    gestionFileFolder.compileModule("/configModules", "ON")
    gestionFileFolder.compileModule("/gestionFileFolder", "ON")
    gestionFileFolder.compileModule("/globalFonctions", "ON")
    gestionFileFolder.compileModule("/diversFonctions", "ON")
    gestionFileFolder.compileModule("/logFonctions", "ON")
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
    # controleGeneral/Web sont SOLIDIFIES : charges par 'import' (version en FLASH via
    # load_native), au lieu de loadBerryFile (qui recompile en RAM).
    # 'import' appelle AUTOMATIQUEMENT init(module) du module (be_module.c:285-296) :
    # init() publie l'instance dans global.controleXxx et fait add_driver, comme avant.
    # Ne PAS rappeler _ctrl.init() ici : ce serait le constructeur de l'instance.
    chargeModule("controleGeneral", def () import controleGeneral as _ctrl end)
    # gestionFileFolder.loadBerryFile("/i2c_ads1115", drivers["I2C"]["environnement"]["ADS1115"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/i2c_mcp23017", drivers["I2C"]["environnement"]["MCP23017"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/modBus_Conn16channel", drivers["ModBus"]["environnement"]["Conn16channel"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/modbus_TasmotaSlaveModBus", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus1"].find("activation", "OFF"), "ON")
    chargeModule("controleWeb", def () import controleWeb as _ctrl end)
    # gestionFileFolder.loadBerryFile("/controleUDP", serveur["udp"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleModbus", drivers["ModBus"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleRangeExtender", serveur["rangeExtender"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleLoRaWan", drivers["LoRaWan"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleVoletRoulants", drivers.find("voletRoulants", {}).find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleDiscovery", serveur["discovery"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleGarage", modules.find("garage", {}).find("activation", "OFF"), "ON")

    # NE PAS compiler autoexec.be en .bec : tasmota.compile() compile en contexte LOCAL
    # (tasmota_class.be:480, upstream #23457). Le .bec tournerait alors sous le nom 'loader'
    # et tous les import/var/affectations de niveau fichier ci-dessus deviendraient des
    # LOCALES : 'configGlobal' undeclared, puis 'controleGeneral' undeclared dans les regles,
    # des le DEUXIEME demarrage. Constate sur la cave le 2026-09-26.
    # gestionFileFolder.compileModule("/autoexec", "ON")
else
    var blocs = {"serveur": serveur, "diverses": diverses, "modules": modules, "drivers": drivers}
    var manquants = []
    for c: blocs.keys()    if !isinstance(blocs[c], map)    manquants.push(c)    end    end
    logFonctions.log("AUTO_EXE: Attention, le fichier de paramétrage est absent ou invalide (bloc(s) manquant(s) : " + manquants.concat(", ") + ") : aucun module chargé !", LOG_LEVEL_ERREUR)
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
