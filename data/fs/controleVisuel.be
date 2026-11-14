# Driver du visuel d'accueil (plan tasks/plans/atelier-visuels.md, A3) : la logique est dans visuelFonctions.be.
# Charge par l'autoexec des seules cartes qui ont un visuel. Le driver n'est pose que si /json/visuel.json existe et est
# valide : sans description, ni bloc sur l'accueil ni route (modele qrcodePage). Le bloc se pose sous les boutons des relais,
# au-dessus des boutons de menu (web_add_main_button), comme la facade des volets.
# Logs : charte du CLAUDE.md (cible visuel : ReglageLog visuel <niveau>).

# Rendu solidifiable (2026-11-14), sur le modele de controleLeds : la classe est portee par le module import-able
# 'controleVisuel'. 'import' appelle AUTOMATIQUEMENT controleVisuel_init(m), en pied de fichier.
#@ solidify:controleVisuel
var controleVisuel = module("controleVisuel")

class CONTROLE_VISUEL : Driver
    def web_add_main_button()
        import visuelFonctions
        visuelFonctions.accueil()
    end

    def web_add_handler()
        import webserver
        import visuelFonctions
        webserver.on("/visuel", def () visuelFonctions.route() end, webserver.HTTP_GET)
    end
end

# Publie la classe dans le module (solidification + import).
controleVisuel.CONTROLE_VISUEL = CONTROLE_VISUEL

# init() : APPELEE AUTOMATIQUEMENT par 'import controleVisuel'. Ne PAS la rappeler depuis l'autoexec.
# Publie le nom GLOBAL 'visuelFonctions' : les fonctions de ce module solidifie s'appellent entre elles par ce nom,
# qu'un module natif ne cree pas lui-meme. Le driver n'est pose que si la description est valide.
def controleVisuel_init(m)
    import global
    import visuelFonctions
    global.visuelFonctions = visuelFonctions

    if (visuelFonctions.charge() != nil)
        try
            global.controleVisuel = m.CONTROLE_VISUEL()
            tasmota.add_driver(global.controleVisuel)
        except .. as error, message
            logFonctions.log("CONTROLE_VISUEL_ERREUR: " + str(error) + " -> " + str(message) + " !", LOG_LEVEL_ERREUR, "visuel")
        end
    end
    return m
end
controleVisuel.init = controleVisuel_init

# Valeur du module importe depuis le LittleFS (sans elle, import rend nil et init() n'est pas appelee)
return controleVisuel
