# Demarrage de la carte du portail de jardin (esclave ModBus id 4, 2 relais impulsionnels de 1 s qui lancent la carte electronique du portail). Le deroule
# commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module solidifie
# data/fs/demarrage.be : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte, sur le modele de celui du rideau
# (esclave ModBus) : le Shutter du portail tourne sur le P4 (mode 3, comme le rideau), cette carte n'execute que ses 2 relais.
# Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")

    # controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON). Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb"])
    demarrage.charge(["fsMqtt"])                                            # fichiers du FS recus par MQTT (page Build 7700)
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleModbus"])                                    # ouvre le port serie RS485
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.leds()
    demarrage.charge(["controlePortail"], "modules.portail")                 # page d'accueil : le portail seul et son capteur de fermeture (lecture seule)
    demarrage.historique()
    demarrage.charge(["qrcodePage"])
end
