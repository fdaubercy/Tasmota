# Demarrage de l'interrupteur differentiel du bureau (ESP32 sans PSRAM). Le deroule commun (globales, garde du
# persist, logs, carte SD, chargement protege de chaque module) est dans le module solidifie data/fs/demarrage.be
# (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des modules de la carte.
# Ne pas le compiler en .bec (voir demarrage.be).
import partition_wizard        # assistant de partitions de Tasmota (page web)
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["partition_wizard"])
    demarrage.charge(["controleGeneral", "controleWeb"])
end
