# Demarrage de l'ecran 7B de la cave (env tasmota32s3-cave-ecran), ESCLAVE du serveur de la cave : ModBus id 1 (RS485
# GPIO 16/15 et UDP), client de son point d'acces (range extender id 1) ; decide le 2026-11-12. Vues : plan
# envs-grenier-rdc-sonoff-cave, A9. Le deroule
# commun (globales, garde du persist, logs, carte SD, chargement protege de chaque module) est dans le module
# solidifie data/fs/demarrage.be (audit P4.2, 2026-10-25) : ce fichier ne garde que la LISTE ORDONNEE des
# modules de la carte. Ne pas le compiler en .bec (voir demarrage.be).
import demarrage
if demarrage.prologue()
    demarrage.importe(["configGlobal", "globalFonctions", "webFonctions", "modbusFonctions"])
    demarrage.compileSocle()
    demarrage.compile(["udpFonctions"], "serveur.udp")
    demarrage.compile(["rangeExtenderFonctions"], "serveur.rangeExtender")
    demarrage.compile(["ecranCaveFonctions"], "modules.ecranCave")             # modele MQTT de l'affichage (A6), compile AVANT son controle

    demarrage.charge(["controleGeneral", "controleLedTemoin", "i2c_ads1115", "i2c_mcp23017", "modBus_Conn16channels", "modBus_TasmotaSlaveModBus", "controleWeb", "fsMqtt"])
    demarrage.charge(["controleUDP"], "serveur.udp")
    demarrage.charge(["controleModbus"])                                    # ouvre le port serie RS485 (GPIO 16/15)
    demarrage.charge(["controleDiscovery"], "serveur.discovery")            # fiche ImAlive au maitre : son RoutageRangeExtender (:8080) en depend
    demarrage.charge(["controleRangeExtender"], "serveur.rangeExtender")   # esclave (id 1) derriere SERVEUR-RLY-CAVE-GATEWAY
    demarrage.chargeFichier("controleEcranCave", "modules.ecranCave")      # abonnements MQTT de l'affichage (A6)
end
