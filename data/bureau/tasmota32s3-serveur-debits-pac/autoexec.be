# Demarrage de la carte Serveur Débits de PAC (env tasmota32s3-bureau-serveur-debits-pac), genere par l'assistant de creation du persist. Le deroule
# commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module
# solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des
# modules de la carte. Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["debitsFonctions"], "modules.debits")

    demarrage.charge(["controleGeneral", "controleLedTemoin", "controleWeb", "fsMqtt"])
    demarrage.chargeFichier("controleDebits", "modules.debits")
end
