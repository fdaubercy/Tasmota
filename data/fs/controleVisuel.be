# Driver du visuel d'accueil (plan tasks/plans/atelier-visuels.md, A3) : la logique est dans visuelFonctions.be.
# Charge par l'autoexec des seules cartes qui ont un visuel. Le driver n'est pose que si /json/visuel.json existe et est
# valide : sans description, ni bloc sur l'accueil ni route (modele qrcodePage). Le bloc se pose sous les boutons des relais,
# au-dessus des boutons de menu (web_add_main_button), comme la facade des volets.
# Logs : charte du CLAUDE.md (cible visuel : ReglageLog visuel <niveau>).

var controleVisuel

class CONTROLE_VISUEL : Driver
    def web_add_main_button()
        import visuelFonctions
        visuelFonctions.accueil()
    end

    def web_add_handler()
        import webserver
        webserver.on("/visuel", def () import visuelFonctions visuelFonctions.route() end, webserver.HTTP_GET)
    end
end

import visuelFonctions
if (visuelFonctions.charge() != nil)
    try
        controleVisuel = CONTROLE_VISUEL()
        tasmota.add_driver(controleVisuel)
    except .. as error, message
        logFonctions.log("CONTROLE_VISUEL_ERREUR: " + str(error) + " -> " + str(message) + " !", LOG_LEVEL_ERREUR, "visuel")
    end
end

# Valeur du fichier charge (controle P3.3 de banc_demarrage : un controleXxx.be finit par son return)
return controleVisuel
