# Demarrage de la carte Serveur Débits de PAC (env tasmota32s3-bureau-serveur-debits-pac), genere par l'assistant de creation du persist. Le deroule
# commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module
# solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des
# modules de la carte. Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["debitsFonctions", "equilibragePage"], "modules.debits")

    demarrage.charge(["controleGeneral", "controleLedTemoin", "controleWeb", "fsMqtt"])
    demarrage.charge(["controleUDP"], "serveur.udp")                        # exige par le RangeExtender (sinon force a ON + redemarrage)
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")   # maitre (id 0) : point d'acces SERVEUR-DEBITS-PAC-GATEWAY, NAPT
    demarrage.historique()                                                  # historique des debits et page /graphiques (diverses.historique)
    demarrage.chargeFichier("controleDebits", "modules.debits")
end
