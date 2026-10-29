# Demarrage de la carte capteurs de la cuve (esclave ModBus du garage). Le deroule commun (globales, garde du
# persist, logs, carte SD, chargement protege de chaque module) est dans le module solidifie data/fs/demarrage.be
# (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte.
# Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions", "ledsFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")
    demarrage.compile(["cuveFonctions"], "modules.cuve")

    # controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON). Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb"])
    demarrage.charge(["fsMqtt"])                                            # fichiers du FS recus par MQTT (page Build 7700)
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleModbus"])                                    # ouvre le port serie RS485
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.leds()                                                        # AVANT controleCuve : couleur du niveau des son init
    demarrage.historique()                                                  # AVANT controleCuve, qui l'importe
    demarrage.chargeFichier("controleCuve", "modules.cuve")                 # non solidifie : depuis le LittleFS
end
