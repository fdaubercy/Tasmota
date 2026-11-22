# Demarrage du serveur de la cave (S3, pompe de vide cave), maitre ModBus (RS485 GPIO 17/18 et UDP) et maitre du
# range extender (id 0) ; l'ecran 7B sera une autre carte, esclave id 1 (decide le 2026-11-12). Le deroule commun (globales, garde du persist, logs,
# carte SD, chargement protege de chaque module) est dans le module solidifie data/fs/demarrage.be (audit P4.2,
# 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte.
# Ne pas le compiler en .bec (voir demarrage.be).
# Service reseau NON active -> ni compile ni charge (+~40 Ko de Berry sinon : crash memoire constate le 2026-09-27).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["tcpFonctions"], "serveur.tcp")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")

    # Pile ModBus dans l'ordre du P4 : controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON).
    # Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb"])
    demarrage.charge(["fsMqtt"])                                            # fichiers du FS recus par MQTT (page Build 7700), comme la carte ESP32
    demarrage.charge(["controleHue"])                                       # emulation Hue (Alexa) : sans garde, remet Emulation a 0 a OFF (serveur.emulationHue)
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleTCP"], "serveur.tcp")
    demarrage.charge(["controleModbus"])                                    # ouvre le port serie RS485 (GPIO 17/18)
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.charge(["controlePompeVideCave"], "modules.pompeVideCave")        # solidifie : data/cave/tasmota32s3-serveur-rly/controlePompeVideCave.be
    demarrage.charge(["controleHumidite"], "modules.Thermo-Hygrometre")         # solidifie : tuiles et bornes d'humidite, page /humidite
    demarrage.chargeFichier("controleCommandesEcran", "modules.ecranCave")      # touches de l'ecran 7B (A4) : pose global.commandesEsclave
    demarrage.leds()
    demarrage.historique()
    demarrage.charge(["qrcodePage"])
end
