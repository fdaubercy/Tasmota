# Demarrage du serveur de la cave (S3, pompe de vide cave). Le deroule commun (globales, garde du persist, logs,
# carte SD, chargement protege de chaque module) est dans le module solidifie data/fs/demarrage.be (audit P4.2,
# 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte.
# Ne pas le compiler en .bec (voir demarrage.be).
# Service reseau NON active -> ni compile ni charge (+~40 Ko de Berry sinon : crash memoire constate le 2026-09-27).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["tcpFonctions"], "serveur.tcp")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")

    demarrage.charge(["controleGeneral", "controleLedTemoin", "controleWeb"])
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleTCP"], "serveur.tcp")
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.chargeFichier("controlePompeVideCave", "modules.pompeVideCave")   # non solidifie : depuis le LittleFS
    demarrage.leds()
    demarrage.historique()
end
