# Demarrage du projecteur du jardin, NOUS B2T (ESP32 sans PSRAM, page /energie sans enregistrement). Le deroule commun (globales, garde du
# persist, logs, carte SD, chargement protege de chaque module) est dans le module solidifie data/fs/demarrage.be
# (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte.
# Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["discoveryFonctions"], "serveur.discovery")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")
    demarrage.charge(["controleGeneral", "controleWeb"])
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")   # point d'acces de secours, sans NAPT
    demarrage.charge(["controleDiscovery"], "serveur.discovery")       # page /discovery : modules du reseau (2026-10-31)
    demarrage.charge(["controleEnergie"], "diverses.energie")          # page /energie, releve de consommation (2026-11-02)
end
