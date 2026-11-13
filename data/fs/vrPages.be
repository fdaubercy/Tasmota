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
 *             "tempsMontee", "tempsDescente", "inclinaison": {"ouvert", "ferme"} si le MPU6050 du volet est actif,
 *             "finsDeCourse": {"ouverture", "fermeture"} = NOMS des deux interrupteurs si le bloc facade du volet porte
 *             "finsDeCourse": {"module", "ouverture": <id interrupteur>, "fermeture": <id>}, sinon nil}], "decor": liste
 *             de drivers.voletRoulants.facade.decor (ex. ["chevrefeuille", "porte", "pergola"], ["maison"] ; nil si absente),
 *             "camera": {"nom", "id"} si drivers.voletRoulants.facade.camera = {"module", "id": <id du relais>} designe un relais
 *             ACTIF de modules[module].environnement.relais (id N = Power<N>, controleGeneral.be::set_power_handler), sinon nil}
 *             trie par place ; nil si la facade est inactive. Seuls les volets actifs qui portent un bloc facade comptent.
 * finsDeCourse() : {id du volet (texte): {"ouverture": "ON"|"OFF", "fermeture": ...}} lu dans le champ "etat" des interrupteurs
 *             de modules[module].environnement.interrupteurs ; une cle absente = etat inconnu. Sans construire la facade.
 * accueil() : ajout a la page d'accueil : <div id='vf'> + window.VOLETS (facade()) + /sd/js/volets.js. Rien sans facade.
 * bouton()  : bouton « Réglage des volets » de la page de configuration. Rien sans facade.
 * route()   : GET /volets (page de reglage ; ?f=etat : vrReglage.etatPage() en JSON ; ?f=capteurs : finsDeCourse() en JSON, plus
 *             "camera": "ON"|"OFF" (tasmota.get_power) si la camera est declaree) ; ordre() : POST /volets
 *             (action = debut | appui | annuler, id ; ou camera, etat = ON | OFF : Power du relais de la camera)
 *             -> {"ok", "message", "etat"} ; 400 si action inconnue ou camera refusee, 500 JSON sur
 *             exception ; appui : temoin etape = etape affichee par la page, 409 sans appui s'il differe de l'etape courante.
 *             Les deux derriere webserver.check_privileged_access() (Referer qui designe la carte). Facade testee par
 *             active() (bon marche) ; facade() seulement pour l'accueil et la page entiere.
 * Page : /sd/css/reglageVolets.css, /sd/html/reglageVolets.html, window.VOLETS_REGLAGE (facade() + "etat"), /sd/js/reglageVolets.js.
 *
 * SOLIDIFIE sur les envs a facade : aucun etat dans le module (sa table est en lecture seule, piege 12).
********************************************************************************************* -#

#@ solidify:vrPages
var vrPages = module("vrPages")

vrPages.RAFRAICHISSEMENT = 2345         # WebRefresh par defaut de Tasmota (ms)

# Facade active, sans la construire (routes lues toutes les 500 ms) : meme test que CONTROLE_VR.facade
def vrPages_active()
    var volets = drivers.find("voletRoulants")
    var f = (type(volets) == "instance" ? volets.find("facade") : nil)
    return type(f) == "instance" && f.find("activation", "OFF") == "ON"
end
vrPages.active = vrPages_active

# Facade decrite dans le persist (voir l'en-tete), nil si inactive
def vrPages_facade()
    import vrFonctions
    import vrPages
    if (!vrPages.active())    return nil    end
    var volets = drivers["voletRoulants"]
    var f = volets["facade"]

    var ouvertures = []
    for vr: volets.find("environnement", {}).find("VRs", {})
        if (type(vr) != "instance" || vr.find("activation", "OFF") != "ON")    continue    end
        var place = vr.find("facade")
        if (type(place) != "instance")    continue    end
        var incl = vrFonctions.inclinaison(vr)
        var o = {"id": vr.find("id"), "nom": vr.find("nom", "Volet"), "type": place.find("type"), "place": place.find("place", 0),
                 "inverse": vrFonctions.inverse(vr.find("id")), "tempsMontee": vr.find("tempsMontee", 0), "tempsDescente": vr.find("tempsDescente", 0),
                 "inclinaison": (incl != nil ? {"ouvert": incl.find("angleOuvert", 85), "ferme": incl.find("angleFerme", 3)} : nil),
                 "finsDeCourse": vrPages.fins(place.find("finsDeCourse"))}
        var i = size(ouvertures)
        while (i > 0 && ouvertures[i - 1]["place"] > o["place"])    i -= 1    end     # insertion : trie par place
        ouvertures.insert(i, o)
    end

    var r = tasmota.cmd("WebRefresh", boolMute)
    var ms = (isinstance(r, map) ? r.find("WebRefresh") : nil)
    var cam = vrPages.relaisCamera()
    return {"toit": f.find("toit", "aucun"), "rafraichissement": (type(ms) == "int" && ms > 0 ? ms : vrPages.RAFRAICHISSEMENT), "ouvertures": ouvertures,
            "decor": f.find("decor"), "camera": (cam != nil ? {"nom": cam.find("nom"), "id": cam["id"]} : nil)}
end
vrPages.facade = vrPages_facade

# Interrupteur du module de fin.find("module") dont l'id est fin.find(cle) ("ouverture" ou "fermeture"), nil si introuvable
def vrPages_interrupteur(fin, cle)
    var m = modules.find(fin.find("module", ""))
    var env = (type(m) == "instance" ? m.find("environnement") : nil)
    var liste = (type(env) == "instance" ? env.find("interrupteurs") : nil)
    var id = fin.find(cle)
    if type(liste) != "instance" || id == nil    return nil    end
    for inter: liste
        if type(inter) == "instance" && inter.find("id") == id    return inter    end
    end
    return nil
end
vrPages.interrupteur = vrPages_interrupteur

# Bloc finsDeCourse d'un volet -> {"ouverture": nom, "fermeture": nom} (nom nil si l'interrupteur manque), nil sans bloc
def vrPages_fins(fin)
    import vrPages
    if type(fin) != "instance"    return nil    end
    var r = {}
    for cle: ["ouverture", "fermeture"]
        var inter = vrPages.interrupteur(fin, cle)
        r[cle] = (inter != nil ? inter.find("nom") : nil)
    end
    return r
end
vrPages.fins = vrPages_fins

# Etat des fins de course de chaque volet qui en declare : {id (texte): {"ouverture": "ON"|"OFF", "fermeture": ...}} ; cle absente = inconnu
def vrPages_finsDeCourse()
    import vrPages
    var r = {}
    var volets = drivers.find("voletRoulants")
    if type(volets) != "instance"    return r    end
    for vr: volets.find("environnement", {}).find("VRs", {})
        if (type(vr) != "instance" || vr.find("activation", "OFF") != "ON")    continue    end
        var place = vr.find("facade")
        var fin = (type(place) == "instance" ? place.find("finsDeCourse") : nil)
        if (type(fin) != "instance")    continue    end
        var etats = {}
        for cle: ["ouverture", "fermeture"]
            var inter = vrPages.interrupteur(fin, cle)
            var etat = (inter != nil ? inter.find("etat") : nil)
            if (etat == "ON" || etat == "OFF")    etats[cle] = etat    end
        end
        r[str(vr.find("id"))] = etats
    end
    return r
end
vrPages.finsDeCourse = vrPages_finsDeCourse

# Relais de la camera de facade (drivers.voletRoulants.facade.camera = {"module", "id"}), nil s'il manque ou s'il est inactif
def vrPages_relaisCamera()
    var volets = drivers.find("voletRoulants")
    var f = (type(volets) == "instance" ? volets.find("facade") : nil)
    var c = (type(f) == "instance" ? f.find("camera") : nil)
    if type(c) != "instance"    return nil    end
    var m = modules.find(c.find("module", ""))
    var liste = (type(m) == "instance" ? m.find("environnement", {}).find("relais") : nil)
    if type(liste) != "instance"    return nil    end
    for r: liste
        if type(r) == "instance" && r.find("id") == c.find("id") && type(r.find("id")) == "int" && r["id"] > 0 && r.find("activation", "OFF") == "ON"    return r    end
    end
    return nil
end
vrPages.relaisCamera = vrPages_relaisCamera

# Etat reel de la camera ("ON"/"OFF", bit id - 1 de tasmota.get_power()), nil sans camera ou sans ce relais
def vrPages_etatCamera()
    import vrPages
    var r = vrPages.relaisCamera()
    var p = (r != nil ? tasmota.get_power() : nil)
    if !isinstance(p, list) || r["id"] > size(p)    return nil    end
    return p[r["id"] - 1] ? "ON" : "OFF"
end
vrPages.etatCamera = vrPages_etatCamera

# Allume ou eteint la camera : [ok, message]
def vrPages_commandeCamera(etat)
    import vrPages
    var r = vrPages.relaisCamera()
    if r == nil    return [false, "Caméra de façade non déclarée"]    end
    if etat != "ON" && etat != "OFF"    return [false, "État attendu : ON ou OFF"]    end
    var p = tasmota.get_power()
    if !isinstance(p, list) || r["id"] > size(p)    return [false, "Power" + str(r["id"]) + " absent : relais non déclaré (tca9554.dat ?)"]    end
    tasmota.set_power(r["id"] - 1, etat == "ON")
    return [true, "Caméra de façade " + (etat == "ON" ? "allumée" : "éteinte")]
end
vrPages.commandeCamera = vrPages_commandeCamera

# Chaine JSON sans aucun « < » (ni fermeture de balise, ni « <!-- » dans un <script>) : echappement unicode u003c, relu « < » par le JS
def vrPages_json(v)
    import json
    import string
    return string.replace(json.dump(v), "<", "\\u003c")
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
    if (!vrPages.active())    return    end
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
        if (!vrPages.active())
            vrPages.envoie(404, {"ok": false, "message": "Façade inactive"})
            return
        end
        if (webserver.has_arg("f") && webserver.arg("f") == "etat")
            vrPages.envoie(200, vrReglage.etatPage())
            return
        end
        if (webserver.has_arg("f") && webserver.arg("f") == "capteurs")     # lue a chaque rafraichissement de la facade : rien dans le journal
            var c = vrPages.finsDeCourse()
            var cam = vrPages.etatCamera()
            if (cam != nil)    c["camera"] = cam    end
            vrPages.envoie(200, c)
            return
        end
        var f = vrPages.facade()
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
        if (!vrPages.active())
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
            var courante = vrReglage.etatPage()["etape"]
            if ((webserver.has_arg("etape") ? webserver.arg("etape") : nil) != (courante == nil ? "" : courante))
                code = 409              # temoin absent ou perime : l'appui viserait une autre etape (moteur)
                r = [false, "L'étape a changé : état relu"]
            else
                r = vrReglage.appui(id, "page")
            end
        elif (action == "annuler")
            vrReglage.annule("annule")
            r = [true, vrReglage.etatPage().find("message", "")]
        elif (action == "camera")
            r = vrPages.commandeCamera(webserver.has_arg("etat") ? webserver.arg("etat") : "")
            code = (r[0] ? 200 : 400)
            vrFonctions.log("VR_PAGES: " + r[1] + " (page d'accueil) !", (r[0] ? LOG_LEVEL_INFO : LOG_LEVEL_ERREUR))
        else
            code = 400
            r = [false, "Action inconnue"]
        end
        if (action != "camera")    vrFonctions.log("VR_PAGES: Ordre " + action + " du volet " + str(id) + " : " + str(r[0]) + " !", LOG_LEVEL_DEBUG)    end
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
