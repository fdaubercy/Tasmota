# Demarrage de la carte Serveur Débits de PAC (env tasmota32s3-bureau-serveur-debits-pac), genere par l'assistant de creation du persist. Le deroule
# commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module
# solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des
# modules de la carte. Ne pas le compiler en .bec (voir demarrage.be).
# Esclave ModBus id 1 de la carte d'affichage (plan debits-deux-cartes, A3) : pile ModBus dans l'ordre de la cuve.
import demarrage
if demarrage.prologue()
    # Modules solidifies appeles par leur nom GLOBAL (GETNGBL) : leur globale n'existe que par import
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions", "historiqueFonctions", "historiqueSeries", "graphiquesFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["debitsFonctions", "equilibragePage"], "modules.debits")

    # controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON). Sans condition : init() porte la garde.
    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb"])
    demarrage.charge(["fsMqtt"])                                            # fichiers du FS recus par MQTT (page Build 7700)
    demarrage.charge(["controleUDP"], "serveur.udp")                        # push des debits au maitre ; exige par le RangeExtender
    demarrage.charge(["controleModbus"])                                    # ouvre le port serie RS485 (GPIO 17/18)
    demarrage.charge(["controleDiscovery"], "serveur.discovery")            # fiche ImAlive au maitre : son RoutageRangeExtender (:8080) en depend
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")   # esclave (id 1) derriere SERVEUR-DEBITS-PAC-GATEWAY, point d'acces propre
    demarrage.historique()                                                  # historique des debits et page /graphiques (diverses.historique)
    demarrage.chargeFichier("controleDebits", "modules.debits")
end
