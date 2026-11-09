# Page /equilibrage de la carte des debits (plan tasks/plans/equilibrage-par-la-carte.md) : le guide anime de
# l'equilibrage de la nourrice, /sd/html/equilibrage.html, suivi du code du mode carte /sd/js/equilibrage_carte.js (poses
# depuis le dossier de la carte au demarrage par gestionFileFolder.listeEtRepartitLesFichiers), les debits mesures pour sa
# lecture en direct, et les reglages de son estimateur (puissances des radiateurs) gardes sur la carte.
#     GET  /equilibrage              -> la page : doctype, charset, viewport, window.CARTE (noms des departs, fenetre, nom
#                                       de la carte), le fichier, puis le code du mode carte
#     GET  /equilibrage?f=debits     -> JSON {debits, total, noms, muets, imprecis, fenetre, age_s} (L/min, null = sans mesure)
#     GET  /equilibrage?f=reglages   -> JSON des reglages enregistres ({} si aucun)
#     POST /equilibrage (reglages=)  -> enregistre les reglages dans /json/equilibrage.json (champs de CHAMPS seulement)
# Acces privilegie comme /cuve (mot de passe web s'il existe, Referer qui designe la carte). Un favori du telephone n'envoie
# pas de Referer : la carte repond alors une page de relais SANS DONNEE qui se recharge elle-meme ; le navigateur envoie
# cette fois le Referer et l'acces privilegie s'applique normalement.
# Reglages HORS persist (regle du depot : le persist ne garde que ce qu'un traitement permanent lit). Un envoi du FS par
# image (buildfs + upload) les efface : la page les reprend alors du navigateur, a reenregistrer.
# Sans etat ; importe par controleDebits a la premiere requete, compile en .bec par
# demarrage.compile(["debitsFonctions", "equilibragePage"], "modules.debits"). Logs : charte du CLAUDE.md, cible serveurWeb.
var equilibragePage = module("equilibragePage")

equilibragePage.PAGE = "/sd/html/equilibrage.html"
equilibragePage.CODE = "/sd/js/equilibrage_carte.js"
equilibragePage.REGLAGES = "/json/equilibrage.json"
equilibragePage.MAX_REGLAGES = 2048        # octets du JSON recu
equilibragePage.PERMIS = "0123456789.,-abcdefghijklmnopqrstuvwxyz"   # valeurs : nombres et codes de type (a22, f4, connu)

# Champs de la page gardes sur la carte : temperatures, debit de la PAC, et par radiateur type, dimensions, puissance
def equilibragePage_champs()
    var c = ["t-aller", "t-retour", "t-piece", "pac"]
    for n: 1 .. 6
        for s: ["-type", "-h", "-l", "-e", "-p", "-dt"]    c.push("r" + str(n) + s)    end
        c.push("p" + str(n))
    end
    return c
end
equilibragePage.champs = equilibragePage_champs

# Route GET /equilibrage
def equilibragePage_route()
    import webserver
    import equilibragePage
    if (webserver.header("Referer") == nil)    return equilibragePage.envoieRelais()    end
    if (!webserver.check_privileged_access())    return nil    end
    var f = (webserver.has_arg("f") ? webserver.arg("f") : "")
    if (f == "debits")
        equilibragePage.envoieJson(equilibragePage.debits)
    elif (f == "reglages")
        equilibragePage.envoieJson(equilibragePage.lisReglages)
    else
        equilibragePage.envoiePage()
    end
end
equilibragePage.route = equilibragePage_route

# Favori ou lien tape : aucune donnee, rechargement en ?r=1 (avec Referer cette fois). Un navigateur qui n'envoie jamais
# de Referer revient en ?r=1 sans Referer : le lien seul, sans rechargement, pour ne pas boucler.
def equilibragePage_envoieRelais()
    import webserver
    webserver.content_open(200, "text/html")
    webserver.content_send("<!doctype html><meta charset='utf-8'><title>Équilibrage</title>"
                           + (webserver.has_arg("r") ? "" : "<script>location.replace('/equilibrage?r=1')</script>")
                           + "<p><a href='/equilibrage'>Ouvrir la page d'équilibrage</a></p>")
    webserver.content_close()
end
equilibragePage.envoieRelais = equilibragePage_envoieRelais

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

# Reglages enregistres ({} si le fichier manque ou est illisible)
def equilibragePage_lisReglages()
    import path
    import json
    import equilibragePage
    if (!path.exists(equilibragePage.REGLAGES))    return {}    end
    var f = open(equilibragePage.REGLAGES, "r")
    var lu = json.load(f.read())
    f.close()
    return isinstance(lu, map) ? lu : {}
end
equilibragePage.lisReglages = equilibragePage_lisReglages

# Reponse JSON ; calcul AVANT d'ouvrir la reponse : une exception ne laisse rien d'ouvert
def equilibragePage_envoieJson(calcul)
    import webserver
    import json
    var texte
    try
        texte = json.dump(calcul())
    except .. as erreur, message
        logFonctions.log("EQUILIBRAGE_PAGE_ERREUR: Donnees illisibles : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
        webserver.content_open(500, "text/plain")
        webserver.content_send("Donnees illisibles")
        webserver.content_close()
        return
    end
    webserver.content_open(200, "application/json")
    webserver.content_send(texte)
    webserver.content_close()
end
equilibragePage.envoieJson = equilibragePage_envoieJson

# Verdict sur le texte recu : [map validee, nil] ou [nil, message]
def equilibragePage_valide(texte)
    import json
    import string
    import equilibragePage
    if (type(texte) != "string")    return [nil, "parametre reglages absent"]    end
    if (size(texte) > equilibragePage.MAX_REGLAGES)    return [nil, "reglages trop gros (" + str(equilibragePage.MAX_REGLAGES) + " octets au plus)"]    end
    var lu = json.load(texte)
    if (!isinstance(lu, map))    return [nil, "JSON illisible ou pas un objet"]    end
    var champs = equilibragePage.champs()
    for cle: lu.keys()
        var v = lu[cle]
        if (champs.find(cle) == nil)    return [nil, "champ inconnu : " + str(cle)]    end
        if (type(v) != "string" || size(v) > 12)    return [nil, "valeur refusee pour " + cle]    end
        for i: 0 .. size(v) - 1
            if (string.find(equilibragePage.PERMIS, string.tolower(v[i])) < 0)    return [nil, "caractere refuse pour " + cle]    end
        end
    end
    return [lu, nil]
end
equilibragePage.valide = equilibragePage_valide

# POST /equilibrage : enregistre les reglages de la page
def equilibragePage_enregistre()
    import webserver
    import json
    import equilibragePage
    if (!webserver.check_privileged_access())    return nil    end
    var verdict = equilibragePage.valide(webserver.has_arg("reglages") ? webserver.arg("reglages") : nil)
    var code = 200
    var reponse = {"ok": true}
    if (verdict[1] != nil)
        logFonctions.log("EQUILIBRAGE_PAGE_ERREUR: Reglages refuses : " + verdict[1] + " !", LOG_LEVEL_ERREUR, "serveurWeb")
        code = 400
        reponse = {"erreur": verdict[1]}
    else
        var f
        try
            f = open(equilibragePage.REGLAGES, "w")
            f.write(json.dump(verdict[0]))
            f.close()
            logFonctions.log("EQUILIBRAGE_PAGE: Reglages de la page enregistres (" + str(size(verdict[0])) + " champs) !", LOG_LEVEL_INFO, "serveurWeb")
        except .. as erreur, message
            if (f != nil)    try f.close() except .. end    end       # fichier tronque : lisReglages rend alors {}
            logFonctions.log("EQUILIBRAGE_PAGE_ERREUR: Ecriture de " + equilibragePage.REGLAGES + " : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
            code = 500
            reponse = {"erreur": "Ecriture impossible sur la carte"}
        end
    end
    webserver.content_open(code, "application/json")
    webserver.content_send(json.dump(reponse))
    webserver.content_close()
end
equilibragePage.enregistre = equilibragePage_enregistre

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
        if (path.exists(equilibragePage.CODE))
            webserver.content_send("<script>")
            gestionFileFolder.readFileByLineAndContentSend(equilibragePage.CODE)
            webserver.content_send("</script>")
        else
            logFonctions.log("EQUILIBRAGE_PAGE_ERREUR: " + equilibragePage.CODE + " absent du LittleFS : page sans lecture de la carte !", LOG_LEVEL_ERREUR, "serveurWeb")
        end
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
