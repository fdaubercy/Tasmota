# Demarrage de la carte du grenier (en sommeil). Le deroule commun (globales, garde du persist, logs, carte SD,
# chargement protege de chaque module) est dans le module solidifie data/fs/demarrage.be (audit P4.2,
# 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte.
# Ne pas le compiler en .bec (voir demarrage.be).
# Services reseau remis au modele des autres cartes : ni compiles ni charges s'ils ne sont pas actives.
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["tcpFonctions"], "serveur.tcp")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")
    demarrage.compile(["loRaWanFonctions"], "drivers.LoRaWan")
    demarrage.compile(["vrFonctions"], "drivers.voletRoulants")

    demarrage.charge(["controleGeneral", "controleLedTemoin", "controleWeb"])
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleTCP"], "serveur.tcp")
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")
    demarrage.charge(["controleLoRaWan"], "drivers.LoRaWan")
    demarrage.charge(["controleVoletRoulants"], "drivers.voletRoulants")
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.chargeFichier("controleGrenier", "modules.grenier")           # non solidifie : depuis le LittleFS
    demarrage.leds()
    demarrage.historique()
end
