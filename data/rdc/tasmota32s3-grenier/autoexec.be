# Demarrage du serveur du grenier du RDC (Waveshare ESP32-S3-ETH-8DI-8RO) : volets de la porte d'entree et de la cuisine,
# trappe du grenier, DHT22, maitre ModBus (RS485 et UDP) et maitre du range extender (id 0 ; l'ecran sera une autre carte, esclave id 1).
# Le deroule commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module
# solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des modules de la
# carte. Ne pas le compiler en .bec (voir demarrage.be).
# Service reseau NON active -> ni compile ni charge (+~40 Ko de Berry sinon : crash memoire constate le 2026-09-27).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["tcpFonctions"], "serveur.tcp")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")

    # Pile ModBus dans l'ordre du P4 : controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON).
    # Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb"])
    demarrage.charge(["fsMqtt"])                                            # fichiers du FS recus par MQTT (page Build 7700)
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleTCP"], "serveur.tcp")
    demarrage.charge(["controleModbus"])                                    # ouvre le port serie RS485 (GPIO 17/18)
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")   # maitre (id 0), point d'acces SERVEUR-GRENIER-RDC-GATEWAY
    demarrage.charge(["controleVoletRoulants"], "drivers.voletRoulants")   # volets natifs Shutter1 (porte), Shutter2 (cuisine), Shutter3 (trappe)
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.leds()                                                        # LED WS2812 de la carte (GPIO38) : voyant d'etat
    demarrage.historique()
end
