# Driver de la page « Systeme » des ecrans tactiles (plan tasks/plans/atelier-ecrans.md, A19) : la logique est dans
# ecranSysteme.be (memoire, flash, reseau, dernieres erreurs, boutons GC et Redemarrer). Charge depuis le LittleFS APRES le
# driver de l'ecran de la carte (controleEcranDebits, controleEcranCave...), qui demarre l'interface (ecranFonctions.interface).
# Garde d'activation en pied : modules.ecranSysteme.activation == "ON" ; page des objets : modules.ecranSysteme.page.
# Logs : charte du CLAUDE.md (cible ecranSysteme : ReglageLog ecranSysteme <niveau>).

var controleEcranSysteme

class CONTROLE_EcranSysteme : Driver
    var echec    # dernier message d'erreur du rafraichissement : une ligne par CHANGEMENT de message, pas une par seconde

    def init()
        import ecranSysteme
        self.echec = nil
        ecranSysteme.regles()      # boutons de la page en HASPmota (regles hasp#p<page>b<id>#event)
        ecranSysteme.log("CONTROLE_ECRAN_SYSTEME: page Systeme sur la page " + str(ecranSysteme.page()) + " de l'ecran !", LOG_LEVEL_INFO)
    end

    # Suivi continu de la RAM et rafraichissement de la page si elle est affichee (callback frequent : jamais de log info ici)
    def every_second()
        import ecranSysteme
        try
            ecranSysteme.tic()
            if (self.echec != nil)
                self.echec = nil
                ecranSysteme.log("CONTROLE_ECRAN_SYSTEME: rafraichissement retabli !", LOG_LEVEL_DEBUG)
            end
        except .. as e, m
            var msg = str(e) + " " + str(m)
            if (self.echec != msg)
                self.echec = msg
                ecranSysteme.log("CONTROLE_ECRAN_SYSTEME_ERREUR: page Systeme non rafraichie : " + msg + " !", LOG_LEVEL_ERREUR)
            end
        end
    end
end

# Active le driver du module
if (modules.find("ecranSysteme", {}).find("activation", "OFF") == "ON")
    try
        controleEcranSysteme = CONTROLE_EcranSysteme()
        tasmota.add_driver(controleEcranSysteme)
    except .. as error, message
        logFonctions.log("CONTROLE_ECRAN_SYSTEME_ERREUR: " + str(error) + " -> " + str(message) + " !", LOG_LEVEL_ERREUR, "ecranSysteme")
    end
end

# Valeur du fichier charge (controle P3.3 de banc_demarrage : un controleXxx.be finit par son return)
return controleEcranSysteme
