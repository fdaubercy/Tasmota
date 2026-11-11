# Driver du module metier ecranDebits : ecran tactile des 6 debits de la nourrice de chauffage ; la logique des debits est dans
# ecranDebitsFonctions.be, le generique d'ecran (veille, luminosite, choix de l'interface) dans ecranFonctions.be, le dessin dans
# l'INTERFACE presente sur le FS (choisie a la compilation, option custom_interface_ecran du cenv) : ecranHaspmota (+ pages.jsonl)
# ou ecranLvgl. Les deux presentes : HASPmota (ligne info) ; aucune : erreur, carte vivante sans ecran.
# Charge depuis le LittleFS par demarrage.chargeFichier("controleEcranDebits", "modules.ecranDebits"), seulement
# si modules.ecranDebits.activation vaut "ON" ; ecranFonctions, ecranDebitsFonctions et l'interface sont compiles avant (autoexec).
# Les valeurs viennent de la carte d'acquisition par modBus_TasmotaSlaveModBus (releve groupe ModBus, push UDP).
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).

class CONTROLE_EcranDebits : Driver
    def init()
        import ecranFonctions
        import ecranDebitsFonctions
        ecranFonctions.bloc = "ecranDebits"    # reglages de l'ecran : modules.ecranDebits du persist
        tasmota.add_cmd("ReglageEcranDebits", ecranDebitsFonctions.reglageEcranDebits)
        try
            ecranDebitsFonctions.demarreEcran(ecranFonctions.charge(["ecranHaspmota", "ecranLvgl"]))
        except .. as e, m
            ecranDebitsFonctions.log("CONTROLE_ECRAN_DEBITS_ERREUR: interface non chargee : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
        end
        ecranDebitsFonctions.log("CONTROLE_ECRAN_DEBITS: module ecranDebits charge, fenetre attendue " + str(ecranDebitsFonctions.reglage("fenetre")) + " s !", LOG_LEVEL_INFO)
    end

    # Veille et luminosite (callback frequent : jamais de log info ici) ; I2C ecrit aux seuls changements d'etat
    def every_250ms()
        import ecranFonctions
        ecranFonctions.suitVeille()
    end

    # Rafraichit l'ecran chaque seconde (callback frequent : jamais de log info ici) ; l'interface n'ecrit que ce qui a change
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
