#- *********************************************************************************************
 * vrPages.be - Visuel de la facade et page de reglage des durees des volets (2026-11-11)
 *
 * Fichier de fonctions SANS driver : appele par le driver des volets (CONTROLE_VR de controleVoletRoulants.be :
 * web_add_main_button, web_add_config_button, web_add_handler). Spec :
 * docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md ; plan tasks/plans/visuel-reglage-volets.md, A4.
 * Le driver n'importe ce module QUE si drivers.voletRoulants.facade.activation vaut "ON" : les envs sans facade
 * (tasmota32-rdc-vr-porte) l'excluent du FS (liste volets_pages de [berry_commun]).
 *
 * facade()  : {"toit", "rafraichissement" (WebRefresh, ms), "ouvertures": [{"id", "nom", "type", "place", "inverse",
 *             "tempsMontee", "tempsDescente", "inclinaison": {"ouvert", "ferme"} si le MPU6050 du volet est actif}]}
 *             trie par place ; nil si la facade est inactive. Seuls les volets actifs qui portent un bloc facade comptent.
 * accueil() : ajout a la page d'accueil : <div id='vf'> + window.VOLETS (facade()) + /sd/js/volets.js. Rien sans facade.
 * bouton()  : bouton « Réglage des volets » de la page de configuration. Rien sans facade.
 * route()   : GET /volets (page de reglage ; ?f=etat : vrReglage.etatPage() en JSON) ; ordre() : POST /volets
 *             (action = debut | appui | annuler, id) -> {"ok", "message", "etat"} ; 400 si action inconnue, 500 JSON sur
 *             exception. Les deux derriere webserver.check_privileged_access() (Referer qui designe la carte).
 * Page : /sd/css/reglageVolets.css, /sd/html/reglageVolets.html, window.VOLETS_REGLAGE (facade() + "etat"), /sd/js/reglageVolets.js.
 *
 * SOLIDIFIE sur les envs a facade : aucun etat dans le module (sa table est en lecture seule, piege 12).
********************************************************************************************* -#

#@ solidify:vrPages
var vrPages = module("vrPages")

vrPages.RAFRAICHISSEMENT = 2345         # WebRefresh par defaut de Tasmota (ms)

# Facade decrite dans le persist (voir l'en-tete), nil si inactive
def vrPages_facade()
    import vrFonctions
    import vrPages
    var volets = drivers.find("voletRoulants")
    var f = (type(volets) == "instance" ? volets.find("facade") : nil)
    if (type(f) != "instance" || f.find("activation", "OFF") != "ON")    return nil    end

    var ouvertures = []
    for vr: volets.find("environnement", {}).find("VRs", {})
        if (type(vr) != "instance" || vr.find("activation", "OFF") != "ON")    continue    end
        var place = vr.find("facade")
        if (type(place) != "instance")    continue    end
        var incl = vrFonctions.inclinaison(vr)
        var o = {"id": vr.find("id"), "nom": vr.find("nom", "Volet"), "type": place.find("type"), "place": place.find("place", 0),
                 "inverse": vr.find("inverse", 0), "tempsMontee": vr.find("tempsMontee", 0), "tempsDescente": vr.find("tempsDescente", 0),
                 "inclinaison": (incl != nil ? {"ouvert": incl.find("angleOuvert", 85), "ferme": incl.find("angleFerme", 3)} : nil)}
        var i = size(ouvertures)
        while (i > 0 && ouvertures[i - 1]["place"] > o["place"])    i -= 1    end     # insertion : trie par place
        ouvertures.insert(i, o)
    end

    var r = tasmota.cmd("WebRefresh", boolMute)
    var ms = (isinstance(r, map) ? r.find("WebRefresh") : nil)
    return {"toit": f.find("toit", "aucun"), "rafraichissement": (type(ms) == "int" && ms > 0 ? ms : vrPages.RAFRAICHISSEMENT), "ouvertures": ouvertures}
end
vrPages.facade = vrPages_facade

# Chaine JSON sans « </ » (jamais de fermeture de balise dans un <script>)
def vrPages_json(v)
    import json
    import string
    return string.replace(json.dump(v), "</", "<\\/")
end
vrPages.json = vrPages_json

# Reponse JSON complete, reponse fermee
def vrPages_envoie(code, v)
    import webserver
    import json
    webserver.content_open(code, "application/json")
    webserver.content_send(json.dump(v))
    webserver.content_close()
end
vrPages.envoie = vrPages_envoie

# Ajout a la page d'accueil (FUNC_WEB_ADD_MAIN_BUTTON). Une erreur ne doit jamais casser l'accueil : le <script> est refermé.
def vrPages_accueil()
    import webserver
    import gestionFileFolder
    import vrFonctions
    import vrPages
    var f = vrPages.facade()
    if (f == nil)    return    end
    try
        webserver.content_send("<div id='vf'></div><script>window.VOLETS=" + vrPages.json(f) + ";</script><script>")
        gestionFileFolder.readFileByLineAndContentSend("/sd/js/volets.js")
    except .. as erreur, message
        vrFonctions.log("VR_PAGES_ERREUR: Accueil : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
    end
    webserver.content_send("</script>")
end
vrPages.accueil = vrPages_accueil

# Bouton de la page de configuration (FUNC_WEB_ADD_CONFIG_BUTTON)
def vrPages_bouton()
    import webserver
    import vrPages
    if (vrPages.facade() == nil)    return    end
    webserver.content_send("<p></p><form action='/volets' method='get'><button>Réglage des volets</button></form>")
end
vrPages.bouton = vrPages_bouton

# GET /volets : la page de reglage, ou ?f=etat (etat du mode en JSON)
def vrPages_route()
    import webserver
    import gestionFileFolder
    import vrFonctions
    import vrReglage
    import vrPages
    if (!webserver.check_privileged_access())    return nil    end

    try
        var f = vrPages.facade()
        if (f == nil)
            vrPages.envoie(404, {"ok": false, "message": "Façade inactive"})
            return
        end
        if (webserver.has_arg("f") && webserver.arg("f") == "etat")
            vrPages.envoie(200, vrReglage.etatPage())
            return
        end
        f["etat"] = vrReglage.etatPage()
        vrFonctions.log("VR_PAGES: Page de réglage demandée !", LOG_LEVEL_DEBUG)
        webserver.content_start("Réglage des volets")
        webserver.content_send_style()
        webserver.content_send("<style>")
        gestionFileFolder.readFileByLineAndContentSend("/sd/css/reglageVolets.css")
        webserver.content_send("</style>")
        gestionFileFolder.readFileByLineAndContentSend("/sd/html/reglageVolets.html")
        webserver.content_send("<script>window.VOLETS_REGLAGE=" + vrPages.json(f) + ";</script><script>")
        gestionFileFolder.readFileByLineAndContentSend("/sd/js/reglageVolets.js")
        webserver.content_send("</script>")
        webserver.content_button(webserver.BUTTON_MAIN)
        webserver.content_stop()
    except .. as erreur, message
        vrFonctions.log("VR_PAGES_ERREUR: Page : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        try
            webserver.content_stop()
        except ..
        end
    end
end
vrPages.route = vrPages_route

# POST /volets : action = debut | appui | annuler, id = numero du volet
def vrPages_ordre()
    import webserver
    import vrFonctions
    import vrReglage
    import vrPages
    if (!webserver.check_privileged_access())    return nil    end

    var ouverte = false         # reponse ouverte : a fermer aussi apres une exception (posee juste avant l'ouverture)
    try
        if (vrPages.facade() == nil)
            ouverte = true
            vrPages.envoie(404, {"ok": false, "message": "Façade inactive"})
            return
        end
        var action = (webserver.has_arg("action") ? webserver.arg("action") : "")
        var id = (webserver.has_arg("id") ? int(webserver.arg("id")) : -1)
        var r = nil
        var code = 200
        if (action == "debut")
            r = vrReglage.debut(id)
        elif (action == "appui")
            r = vrReglage.appui(id, "page")
        elif (action == "annuler")
            vrReglage.annule("annule")
            r = [true, vrReglage.etatPage().find("message", "")]
        else
            code = 400
            r = [false, "Action inconnue"]
        end
        vrFonctions.log("VR_PAGES: Ordre " + action + " du volet " + str(id) + " : " + str(r[0]) + " !", LOG_LEVEL_DEBUG)
        var reponse = {"ok": r[0], "message": r[1], "etat": vrReglage.etatPage()}     # evaluee AVANT l'ouverture
        ouverte = true
        vrPages.envoie(code, reponse)
    except .. as erreur, message
        vrFonctions.log("VR_PAGES_ERREUR: Ordre : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        try
            if (!ouverte)               # exception avant la reponse : le navigateur ne doit pas attendre sans fin
                vrPages.envoie(500, {"ok": false, "message": "Erreur interne de la carte"})
            else
                webserver.content_close()
            end
        except ..
        end
    end
end
vrPages.ordre = vrPages_ordre

# Retourne le module lors de l'importation
return vrPages
