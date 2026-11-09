# Page /equilibrage de la carte des debits (plan tasks/plans/equilibrage-par-la-carte.md) : le guide anime de
# l'equilibrage de la nourrice, /sd/html/equilibrage.html (pose depuis le dossier de la carte au demarrage par
# gestionFileFolder.listeEtRepartitLesFichiers), servi tel quel, et les debits mesures pour sa lecture en direct.
#     /equilibrage            -> la page : doctype, charset, viewport et window.CARTE (noms des departs, fenetre, nom
#                                de la carte), puis le fichier. Sans window.CARTE (artifact, fichier local), la page
#                                fait taper les debits a la main.
#     /equilibrage?f=debits   -> JSON {debits, total, noms, muets, imprecis, fenetre, age_s} (L/min, null = sans mesure)
# Acces privilegie comme /cuve (Tasmota exige un Referer qui designe la carte). Sans etat ; importe par controleDebits
# a la premiere requete, compile en .bec par demarrage.compile(["debitsFonctions", "equilibragePage"], "modules.debits").
# Logs : charte du CLAUDE.md (logFonctions.log, cible serveurWeb comme /cuve).
var equilibragePage = module("equilibragePage")

equilibragePage.PAGE = "/sd/html/equilibrage.html"

# Route /equilibrage : f=debits -> mesures, sinon la page
def equilibragePage_route()
    import webserver
    import equilibragePage
    if (!webserver.check_privileged_access())    return nil    end
    if ((webserver.has_arg("f") ? webserver.arg("f") : "") == "debits")
        equilibragePage.envoieDebits()
    else
        equilibragePage.envoiePage()
    end
end
equilibragePage.route = equilibragePage_route

# Noms des 6 departs (entrees du persist, voir debitsFonctions.voie)
def equilibragePage_noms()
    import debitsFonctions
    var noms = []
    for i: 0 .. debitsFonctions.NB_VOIES - 1    noms.push(debitsFonctions.voie(i)["nom"])    end
    return noms
end
equilibragePage.noms = equilibragePage_noms

# Mesures pour la page : relues toutes les `fenetre` s quand le suivi en direct est coche (pas de log : requete frequente)
def equilibragePage_debits()
    import debitsFonctions
    import equilibragePage
    var d = debitsFonctions.debits
    var imprecis = []
    for q: d    imprecis.push(debitsFonctions.imprecis(q))    end
    var r = debitsFonctions.releve
    return {"debits": d, "total": debitsFonctions.total(d), "noms": equilibragePage.noms(), "muets": debitsFonctions.muets,
            "imprecis": imprecis, "fenetre": debitsFonctions.fenetre(), "age_s": (r != nil ? (tasmota.millis() - r["t"]) / 1000 : nil)}
end
equilibragePage.debits = equilibragePage_debits

def equilibragePage_envoieDebits()
    import webserver
    import json
    import equilibragePage
    var texte
    try
        texte = json.dump(equilibragePage.debits())     # calcule AVANT d'ouvrir la reponse : rien ne reste ouvert
    except .. as erreur, message
        logFonctions.log("EQUILIBRAGE_PAGE_ERREUR: Mesures illisibles : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
        webserver.content_open(500, "text/plain")
        webserver.content_send("Mesures illisibles")
        webserver.content_close()
        return
    end
    webserver.content_open(200, "application/json")
    webserver.content_send(texte)
    webserver.content_close()
end
equilibragePage.envoieDebits = equilibragePage_envoieDebits

def equilibragePage_envoiePage()
    import webserver
    import json
    import path
    import string
    import gestionFileFolder
    import debitsFonctions
    import equilibragePage
    if (!path.exists(equilibragePage.PAGE))
        webserver.content_open(404, "text/plain")
        webserver.content_send("Page absente : " + equilibragePage.PAGE + " (FS de la carte a renvoyer)")
        webserver.content_close()
        logFonctions.log("EQUILIBRAGE_PAGE_ERREUR: " + equilibragePage.PAGE + " absent du LittleFS !", LOG_LEVEL_ERREUR, "serveurWeb")
        return
    end
    var carte = {"noms": equilibragePage.noms(), "fenetre": debitsFonctions.fenetre(),
                 "nom": tasmota.cmd("Hostname", boolMute).find("Hostname", "")}
    logFonctions.log("EQUILIBRAGE_PAGE: Page d'equilibrage demandee !", LOG_LEVEL_DEBUG, "serveurWeb")
    webserver.content_open(200, "text/html")
    var ouverte = true          # reponse ouverte : a fermer aussi apres une exception
    try
        webserver.content_send("<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>")
        webserver.content_send("<script>window.CARTE=" + string.replace(json.dump(carte), "</", "<\\/") + ";</script>")
        gestionFileFolder.readFileByLineAndContentSend(equilibragePage.PAGE)
        webserver.content_close()
        ouverte = false
    except .. as erreur, message
        logFonctions.log("EQUILIBRAGE_PAGE_ERREUR: Envoi de la page : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
        if (ouverte)    webserver.content_close()    end
    end
end
equilibragePage.envoiePage = equilibragePage_envoiePage

# Retourne le module lors de l'importation
return equilibragePage
