# Demarrage du maitre P4 du garage. Le deroule commun (globales, garde du persist, logs, carte SD, chargement
# protege de chaque module) est dans le module solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce
# fichier ne garde que la LISTE ORDONNEE des modules de la carte. Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["garageFonctions"], "modules.garage")
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")

    # controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON). Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb"])
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleModbus"])
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")
    demarrage.charge(["controleVoletRoulants"], "drivers.voletRoulants")   # volet natif sur les relais VIRTUELS (porte du rideau)
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.charge(["controleES8311"])
    demarrage.charge(["controleCoprocesseur"], "serveur.coprocesseur")    # alerte « firmware du C6 pas a jour » (accueil web)
    demarrage.historique()                                                  # AVANT controleGarage, qui l'importe
    demarrage.chargeFichier("controleGarage", "modules.garage")             # non solidifie : depuis le LittleFS
end
