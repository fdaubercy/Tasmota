# Demarrage du portail de jardin sur ESP32 classique (carte ESP32_Relay_X4_Modbus_v1.3, SANS PSRAM), remplacante du S3. Le deroule commun (globales, garde
# du persist, logs, carte SD, chargement protege de chaque module) est dans le module solidifie data/fs/demarrage.be : ce fichier ne garde que la LISTE
# ORDONNEE des modules de la carte, sur le modele du projecteur du jardin (autre ESP32 sans PSRAM).
# Palier 1 : base + discovery en EMISSION seule (serveur.discovery.ecoute = OFF dans le persist). Paliers suivants, a ajouter UN par UN en relevant le tas
# (Status 4, BRY: GC) : udpFonctions + controleUDP, modbus (modbusFonctions, modBus_TasmotaSlaveModBus, controleModbus), fsMqtt, leds, controlePortail.
# Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")
    demarrage.charge(["controleGeneral", "controleWeb"])
    demarrage.charge(["controleDiscovery"], "serveur.discovery")
    demarrage.charge(["qrcodePage"])
end
