# Demarrage de la carte Écran Débits de PAC (env tasmota32s3-bureau-ecran-debits-pac), genere par l'assistant de creation du persist. Le deroule
# commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module
# solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des
# modules de la carte. Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")
    demarrage.compile(["ecranDebitsFonctions"], "modules.ecranDebits")   # ecranFonctions est solidifie
    demarrage.compile(["ecranHaspmota", "ecranLvgl"], "modules.ecranDebits")   # interface : une seule sur le FS, l'absente est ignoree
    demarrage.compile(["ecranSysteme"], "modules.ecranSysteme")   # page Systeme de l'ecran

    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb", "fsMqtt"])
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleModbus"])
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")
    demarrage.chargeFichier("controleEcranDebits", "modules.ecranDebits")
    demarrage.chargeFichier("controleEcranSysteme", "modules.ecranSysteme")   # apres l'ecran : interface demarree
end
