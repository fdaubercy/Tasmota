# Driver du module metier ecranDebits : ecran TFT des 6 debits de la nourrice de chauffage ; la logique est dans ecranDebitsFonctions.be.
# Charge depuis le LittleFS par demarrage.chargeFichier("controleEcranDebits", "modules.ecranDebits"), seulement
# si modules.ecranDebits.activation vaut "ON" ; ecranDebitsFonctions est compile avant.
# Les valeurs viennent de la carte d'acquisition par modBus_TasmotaSlaveModBus (releve groupe ModBus, push UDP).
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).

class CONTROLE_EcranDebits : Driver
    def init()
        import ecranDebitsFonctions
        tasmota.add_cmd("ReglageEcranDebits", ecranDebitsFonctions.reglageEcranDebits)
        ecranDebitsFonctions.demarreEcran()
        ecranDebitsFonctions.log("CONTROLE_ECRAN_DEBITS: module ecranDebits charge, fenetre attendue " + str(ecranDebitsFonctions.fenetre()) + " s !", LOG_LEVEL_INFO)
    end

    # Rafraichit l'ecran chaque seconde (callback frequent : jamais de log info ici) ; n'ecrit que ce qui a change
    def every_second()
        import ecranDebitsFonctions
        try
            ecranDebitsFonctions.ecran()
        except .. as e, m
            ecranDebitsFonctions.log("CONTROLE_ECRAN_DEBITS_ERREUR: ecran non rafraichi : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
        end
    end
end

# Active le driver du module
controleEcranDebits = CONTROLE_EcranDebits()
tasmota.add_driver(controleEcranDebits)

# Valeur du fichier charge (controle P3.3 de banc_demarrage : un controleXxx.be finit par son return)
return controleEcranDebits
