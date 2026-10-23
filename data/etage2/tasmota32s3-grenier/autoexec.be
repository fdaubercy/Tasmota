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
# Garde de tete (audit P10.1, constat B1, 2026-10-23) : un persist vide, corrompu ou prive d'un de
# ses 4 blocs faisait planter la ligne suivante (diverses.find sur nil) AVANT tout log : carte muette.
# Persist invalide -> rien de ce qui le lit n'est execute, l'erreur est journalisee en fin de fichier.
var persistValide = isinstance(serveur, map) && isinstance(diverses, map) && isinstance(modules, map) && isinstance(drivers, map)
boolMute = (persistValide ? diverses.find("cmdMute", false) : true)

# Fonction de log commune (charte : logFonctions.be). Importee AVANT tout le reste :
# les modules charges ensuite loguent par logFonctions.log(). Import de niveau fichier :
# cree la globale 'logFonctions' (module solidifie).
import logFonctions

# Allege le persist en RAM AVANT tout le reste :
#   - listes vides de cles connues supprimees (leurs lecteurs utilisent .find(cle, [])) ;
#   - environnement des drivers inactifs mis en veille dans /json/driversInactifs.json (rien n'est perdu).
# Import de niveau fichier : cree la globale 'diversFonctions' (module solidifie).
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
# Recense dans le bytecode solidifie (GETNGBL vers un nom de module) le 2026-09-26.
import configGlobal
import globalFonctions
import webFonctions
# Historique et graphiques SOLIDIFIES (2026-10-20, ${berry_commun.historique} de platformio_tasmota_cenv.ini) :
# meme raison. Sans effet tant que historiqueFonctions.demarre() n'est pas appele (ni driver, ni releve) ;
# la version native passe avant tout .bec reste sur le LittleFS (be_module.c:286).
import historiqueFonctions
import historiqueSeries
import graphiquesFonctions

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
    # Compile les modules
    gestionFileFolder.compileModule("/configGlobal", "ON")
    gestionFileFolder.compileModule("/configDevices", "ON")
    gestionFileFolder.compileModule("/configModules", "ON")
    gestionFileFolder.compileModule("/gestionFileFolder", "ON")
    gestionFileFolder.compileModule("/globalFonctions", "ON")
    gestionFileFolder.compileModule("/diversFonctions", "ON")
    gestionFileFolder.compileModule("/logFonctions", "ON")
    gestionFileFolder.compileModule("/webFonctions", serveur.find("activation", "OFF"))
    gestionFileFolder.compileModule("/udpFonctions", serveur["udp"].find("activation", "OFF"))
    gestionFileFolder.compileModule("/tcpFonctions", serveur["tcp"].find("activation", "OFF"))
    gestionFileFolder.compileModule("/rangeExtenderFonctions", serveur["rangeExtender"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/modbusFonctions", drivers["ModBus"].find("activation", "OFF"))   # exclu du FS (ModBus/I2C OFF sur le grenier, 2026-09-27)
    gestionFileFolder.compileModule("/loRaWanFonctions", drivers["LoRaWan"].find("activation", "OFF"))
    gestionFileFolder.compileModule("/vrFonctions")

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
    chargeModule("controleGeneral", def () import controleGeneral as _ctrl end)
    chargeModule("controleLedTemoin", def () import controleLedTemoin as _ctrl end)
    # gestionFileFolder.loadBerryFile("/i2c_ads1115", drivers["I2C"]["environnement"].find("ADS1115", {"activation": "OFF"}).find("activation", "OFF"), "ON")   # exclu du FS (ModBus/I2C OFF sur le grenier, 2026-09-27)
    # gestionFileFolder.loadBerryFile("/i2c_mcp23017", drivers["I2C"]["environnement"].find("MCP23017", {"activation": "OFF"}).find("activation", "OFF"), "ON")   # exclu du FS (ModBus/I2C OFF sur le grenier, 2026-09-27)
    # gestionFileFolder.loadBerryFile("/modBus_Conn16channels", drivers["ModBus"]["environnement"].find("Conn16channels", {"activation": "OFF"}).find("activation", "ON"), "ON")   # exclu du FS (ModBus/I2C OFF sur le grenier, 2026-09-27)
    # gestionFileFolder.loadBerryFile("/modBus_TasmotaSlaveModBus", drivers["ModBus"]["environnement"].find("TasmotaSlaveModBus", {"activation": "OFF"}).find("activation", "ON"), "ON")   # exclu du FS (ModBus/I2C OFF sur le grenier, 2026-09-27)
    chargeModule("controleWeb", def () import controleWeb as _ctrl end)
    chargeModule("controleUDP", def () import controleUDP as _ctrl end)   # solidifie : init() porte la garde d'activation
    chargeModule("controleTCP", def () import controleTCP as _ctrl end)   # solidifie : init() porte la garde d'activation
    # gestionFileFolder.loadBerryFile("/controleModbus", drivers["ModBus"].find("activation", "OFF"), "ON")   # exclu du FS (ModBus/I2C OFF sur le grenier, 2026-09-27)
    chargeModule("controleRangeExtender", def () import controleRangeExtender as _ctrl end)   # solidifie : init() porte la garde d'activation
    chargeModule("controleLoRaWan", def () import controleLoRaWan as _ctrl end)   # solidifie : init() porte la garde d'activation
    chargeModule("controleVoletRoulants", def () import controleVoletRoulants as _ctrl end)   # solidifie : init() porte la garde d'activation
    chargeModule("controleDiscovery", def () import controleDiscovery as _ctrl end)   # solidifie : init() porte la garde d'activation
    chargeModule("controleGrenier", def () gestionFileFolder.loadBerryFile("/controleGrenier", modules.find("grenier", {}).find("activation", "OFF"), "ON") end)

    # LED RGB du dev-kit (drivers.leds.environnement.leds.ledRGB, 2026-10-11) et ruban WS2812 en mode
    # AUTO/MANUEL avec bouton (...leds.ruban, 2026-10-13) : module ledsFonctions compile et charge SEULEMENT
    # si l'un des deux est active. Voyant d'etat ; un module peut y signaler une erreur ou y imposer une couleur.
    if (drivers.find("leds", {}).find("activation", "OFF") == "ON" && (drivers["leds"].find("environnement", {}).find("leds", {}).find("ledRGB", {}).find("activation", "OFF") == "ON" || drivers["leds"].find("environnement", {}).find("leds", {}).find("ruban", {}).find("activation", "OFF") == "ON"))
        gestionFileFolder.compileModule("/ledsFonctions", "ON")
        gestionFileFolder.compileModule("/controleLeds", "ON")
        chargeModule("controleLeds", def () import controleLeds as _ctrl end)   # init() porte la garde d'activation (solidifiable, 2026-10-20)
    end

    # Compile autoexec.be
    # gestionFileFolder.compileModule("/autoexec", "ON")
    # Historique des mesures de la carte (data/fs/historiqueFonctions.be), S3/P4 seulement : 24 h en
    # RAM + min/moy/max horaires en flash, lus par /histo. Compile en .bec puis demarre si active.
    if diverses.find("historique", {}).find("activation", "OFF") == "ON"
        gestionFileFolder.compileModule("/historiqueFonctions", "ON")
        import historiqueFonctions
        chargeModule("historiqueFonctions", def () historiqueFonctions.demarre(diverses["historique"]) end)
    end

else
    var blocs = {"serveur": serveur, "diverses": diverses, "modules": modules, "drivers": drivers}
    var manquants = []
    for c: blocs.keys()    if !isinstance(blocs[c], map)    manquants.push(c)    end    end
    logFonctions.log("AUTO_EXE: Attention, le fichier de paramétrage est absent ou invalide (bloc(s) manquant(s) : " + manquants.concat(", ") + ") : aucun module chargé !", LOG_LEVEL_ERREUR)
end
