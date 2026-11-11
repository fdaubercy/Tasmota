# Driver du module metier ecranDebits : ecran tactile des 6 debits de la nourrice de chauffage ; la logique des debits est dans
# ecranDebitsFonctions.be, le generique d'ecran (veille, luminosite, choix de l'interface) dans ecranFonctions.be, le dessin dans
# l'INTERFACE presente sur le FS (choisie a la compilation, option custom_interface_ecran du cenv) : ecranHaspmota (+ pages.jsonl)
# ou ecranLvgl. Les deux presentes : HASPmota (ligne info) ; aucune : erreur, carte vivante sans ecran.
# Charge depuis le LittleFS par demarrage.chargeFichier("controleEcranDebits", "modules.ecranDebits"), seulement
# si modules.ecranDebits.activation vaut "ON" ; ecranFonctions, ecranDebitsFonctions et l'interface sont compiles avant (autoexec).
# Les valeurs viennent de la carte d'acquisition par modBus_TasmotaSlaveModBus (releve groupe ModBus, push UDP).
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).

class CONTROLE_EcranDebits : Driver
    var echecs    # dernier message d'erreur par callback : une ligne par CHANGEMENT de message, pas une par tic

    # Journalise l'echec `e` `m` du callback `cle` seulement s'il differe du dernier (callbacks frequents : pas de spam)
    def echec(cle, texte, e, m)
        import ecranDebitsFonctions
        var msg = str(e) + " " + str(m)
        if (self.echecs.find(cle) == msg)    return    end
        self.echecs[cle] = msg
        ecranDebitsFonctions.log("CONTROLE_ECRAN_DEBITS_ERREUR: " + texte + " : " + msg + " !", LOG_LEVEL_ERREUR)
    end

    # Callback `cle` revenu a la normale apres une erreur : une ligne debug, puis silence
    def retabli(cle, texte)
        import ecranDebitsFonctions
        if (!self.echecs.contains(cle))    return    end
        self.echecs.remove(cle)
        ecranDebitsFonctions.log("CONTROLE_ECRAN_DEBITS: " + texte + " retabli !", LOG_LEVEL_DEBUG)
    end

    def init()
        self.echecs = {}
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
        try
            ecranFonctions.suitVeille()
            self.retabli("veille", "suivi de la veille")
        except .. as e, m
            self.echec("veille", "veille non suivie", e, m)
        end
    end

    # Rafraichit l'ecran chaque seconde (callback frequent : jamais de log info ici) ; l'interface n'ecrit que ce qui a change
    def every_second()
        import ecranDebitsFonctions
        try
            ecranDebitsFonctions.ecran()
            self.retabli("ecran", "rafraichissement de l'ecran")
        except .. as e, m
            self.echec("ecran", "ecran non rafraichi", e, m)
        end
    end
end

# Active le driver du module
controleEcranDebits = CONTROLE_EcranDebits()
tasmota.add_driver(controleEcranDebits)

# Valeur du fichier charge (controle P3.3 de banc_demarrage : un controleXxx.be finit par son return)
return controleEcranDebits
