# Demarrage de la carte du portail de jardin (esclave ModBus id 4, Shutter en mode 1 : 2 volets, un par vantail). Le deroule
# commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module solidifie
# data/fs/demarrage.be : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte, sur le modele de celui du rideau
# (esclave ModBus) auquel s'ajoute le driver des volets roulants, qui tourne ICI (le rideau, lui, est pilote par le P4).
# Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")
    demarrage.compile(["vrFonctions"], "drivers.voletRoulants")

    # controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON). Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb"])
    demarrage.charge(["fsMqtt"])                                            # fichiers du FS recus par MQTT (page Build 7700)
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleModbus"])                                    # ouvre le port serie RS485
    demarrage.charge(["controleVoletRoulants"], "drivers.voletRoulants")    # Shutter mode 1 : 2 volets, Interlock par vantail
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.leds()
    demarrage.historique()
end
