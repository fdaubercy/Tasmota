# Demarrage du serveur de la cave (ESP32 sans PSRAM, pompe de vide cave), carte EN SERVICE a 192.168.0.48 (hostname
# SERVEUR-RLY-CAVE, topic cave/serveur-rly-cave), maitre du range extender (id 0), discovery OFF (sature la RAM Berry d'un ESP32 sans PSRAM). Depuis le 2026-11-22 ce dossier remplace
# l'ancien code de data/cave/tasmota32-serveur-rly-sauvegarde/ (celui que la carte executait jusque-la).
# Le deroule commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le
# module solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des
# modules de la carte. Tout est solidifie sauf ce fichier et le _persist.json (donnees de la carte).
# Ne pas le compiler en .bec (voir demarrage.be).
# Service reseau NON active -> ni compile ni charge (+~40 Ko de Berry sinon : crash memoire constate le 2026-09-27).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["tcpFonctions"], "serveur.tcp")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")

    # controleGeneral AVANT les autres controles. Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "controleWeb"])
    demarrage.charge(["fsMqtt"])                                            # fichiers du FS recus par MQTT (page Build 7700)
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleTCP"], "serveur.tcp")
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.charge(["controlePompeVideCave"], "modules.pompeVideCave")    # solidifie : data/cave/tasmota32-serveur-rly/controlePompeVideCave.be
    demarrage.charge(["controleHumidite"], "modules.Thermo-Hygrometre")     # solidifie : tuiles et bornes d'humidite, page /humidite
    demarrage.charge(["qrcodePage"])
end
