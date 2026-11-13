# Touches de l'ecran 7B de la cave : le serveur EXECUTE ce que l'ecran lui pousse (plan ecran-cave-vues-commandes, A4,
# 2026-11-12). Charge par l'autoexec sous la garde modules.ecranCave ; pose global.commandesEsclave, que le crochet de
# modBus_TasmotaSlaveModBus.be::recupereReponseModBus (branche 'boutons') appelle SEULEMENT pour un push (Automatique) :
# un releve periodique ou l'etat lu d'une touche ne commande rien.
# Mot pousse par l'ecran au registre 32 + numero - 1 : (seq << 1) | (voulu == "ON" ? 1 : 0), seq de 1 a 127, propre a
# chaque touche, jamais 0. Meme seq que la precedente dans les 30 s = relance de l'ecran, ignoree ; au-dela = ecran redemarre,
# executee ; seq 0 = ignoree (RAM seulement : un redemarrage du serveur oublie les seq, la relance suivante est executee une fois).
# Logs en debug : appele depuis la reception ModBus (charte, regle 4) ; la commutation reste dans le journal natif (POWERn).
# Persist modules.ecranCave : esclave (cle du driver, ex. TasmotaSlaveModBus1), actions {"<n>": {module, relai, manuel} |
# {redemarre: "ON"}}, environnement.boutons : cinq boutons VIRTUELS ModBus (pas de GPIO). Choix assume : ils laissent une
# regle Button<id>#Action inerte (configDevices.be) et des cles Button11..15 dans le JSON SENSOR (controleGeneral::json_append),
# que rien ne lit (historiqueSeries exclut Button*) ; on ne touche ni a l'un ni a l'autre (decide le 2026-11-12).
import string

class COMMANDES_ECRAN
    var derniere                    # "<esclave>/<numero>" -> [derniere seq executee, millis de son execution]
    static FENETRE_MS = 30000       # relances de l'ecran : 5 x 2 s ; au-dela, meme seq = ecran redemarre (seq repartie de 1)

    def init()
        self.derniere = {}
    end

    def recoit(esclave, numero, mot)
        import global
        import globalFonctions
        var cfg = global.modules.find("ecranCave")
        if (type(cfg) != "instance" || cfg.find("activation", "OFF") != "ON" || cfg.find("esclave") != esclave)    return    end

        var seq = (int(mot) >> 1) & 0x7F
        var voulu = ((int(mot) & 1) == 1) ? "ON" : "OFF"
        if (seq == 0)
            logFonctions.log(string.format("COMMANDES_ECRAN: touche %s ignoree (seq 0) !", str(numero)), LOG_LEVEL_DEBUG)
            return
        end
        var action = cfg.find("actions", {}).find(str(numero))
        if (type(action) != "instance")
            logFonctions.log(string.format("COMMANDES_ECRAN_ERREUR: touche %s inconnue (aucune action dans modules.ecranCave.actions) !", str(numero)), LOG_LEVEL_ERREUR)
            return
        end
        var cle = esclave + "/" + str(numero)
        var vu = self.derniere.find(cle)
        var maintenant = tasmota.millis()
        if (vu != nil && vu[0] == seq && maintenant - vu[1] < self.FENETRE_MS)
            logFonctions.log(string.format("COMMANDES_ECRAN: touche %s, seq %i deja executee, ignoree !", str(numero), seq), LOG_LEVEL_DEBUG)
            return
        end
        self.derniere[cle] = [seq, maintenant]

        try
            if (action.find("redemarre", "OFF") == "ON")
                if (voulu == "ON")
                    logFonctions.log("COMMANDES_ECRAN: redemarrage du serveur demande par l'ecran !", LOG_LEVEL_DEBUG)
                    tasmota.cmd("Restart 1")
                end
            else
                logFonctions.log(string.format("COMMANDES_ECRAN: touche %s -> %s relai %s = %s !", str(numero), action["module"], str(action["relai"]), voulu), LOG_LEVEL_DEBUG)
                globalFonctions.modifEtatRelai(action["module"], action["relai"], voulu, voulu, action.find("manuel", "OFF") == "ON", true, 0)
            end
        except .. as e, m
            logFonctions.log(string.format("COMMANDES_ECRAN_ERREUR: touche %s : %s - %s !", str(numero), str(e), str(m)), LOG_LEVEL_ERREUR)
        end
    end
end

import global
global.commandesEsclave = COMMANDES_ECRAN()
