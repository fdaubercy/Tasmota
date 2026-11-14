#- *********************************************************************************************
 * visuelFonctions.be - Visuel d'accueil de la carte : fond, points chauds, etat unifie (2026-11-14)
 *
 * Plan tasks/plans/atelier-visuels.md (A3), spec docs/superpowers/specs/2026-11-13-atelier-visuels-accueil-design.md §6.
 * Charge par controleVisuel.be, qui pose son driver SEULEMENT si /json/visuel.json existe et est valide (modele qrcodePage).
 *
 * Route /visuel (acces privilegie), actions par ?f= a liste blanche :
 *     f=fond  -> le fond (visuel.svg|webp|jpg sous /sd/images/<EXT>/, ou a la racine), par morceaux de 2048 o, cache 24 h
 *     f=etat  -> un seul JSON : {t, power, sensor, modbus, wifi, reseau} ; chaque bloc n'existe que si la description a une
 *                source de ce type (RAM des ESP32 classiques) ; module absent = bloc vide, jamais d'exception
 * Accueil : html() = <div id='vz'>, window.VISUEL = description (< echappe), puis /sd/js/visuel.js inline (comme vrPages_accueil).
 *
 * SOLIDIFIABLE : l'etat (description lue une fois, cache du bloc reseau) vit dans la globale _etatVisuel, pas dans le module.
 * Les chemins FICHIER, JS et RACINE_FOND sont des constantes (un banc les redirige). Logs : cible visuel, prefixe VISUEL:.
 * Limite connue : modbus.esclaves ne vient que de modbusFonctions.etat().ipsApprises (voie UDP) ; un esclave de la voie serie
 * n'a pas d'horodatage propre cote maitre (modbus_serie, lui, a derniereReponseSerie).
********************************************************************************************* -#

#@ solidify:visuelFonctions
var visuelFonctions = module("visuelFonctions")

visuelFonctions.FICHIER = "/json/visuel.json"
visuelFonctions.JS = "/sd/js/visuel.js"
visuelFonctions.RACINE_FOND = ""           # prefixe des chemins de fond (vide sur la carte)
visuelFonctions.MORCEAU = 2048             # octets lus et envoyes a la fois
visuelFonctions.CACHE_RESEAU = 30000       # ms entre deux RgxClients (commande lourde : chaque reponse part aussi en MQTT)

def visuelFonctions_log(msg, niveau)
    logFonctions.log(msg, niveau, "visuel")
end
visuelFonctions.log = visuelFonctions_log

# Etat du module, une globale : {"desc": map|nil, "types": {type de source: true}, "reseau": [millis, lignes]|nil}
def visuelFonctions_etatModule()
    import global
    if (global._etatVisuel == nil)    global._etatVisuel = {"desc": nil, "types": {}, "reseau": nil}    end
    return global._etatVisuel
end
visuelFonctions.etatModule = visuelFonctions_etatModule

def visuelFonctions_nombre(v)
    var ty = type(v)
    return ty == "int" || ty == "real"
end
visuelFonctions.nombre = visuelFonctions_nombre

# Regles de atelier_visuels_description.valide (memes cas : outils_docs/schemas/cas_visuel.json), sans le poids du fond.
# Liste de messages ; vide = valide.
def visuelFonctions_valide(d)
    import visuelFonctions
    if (!isinstance(d, map))    return ["description : objet attendu"]    end
    var err = []
    var fond = d.find("fond")
    var larg = 0
    var haut = 0
    if (d.find("version") != 1)    err.push("version : 1 attendue")    end
    if (!isinstance(fond, map) || ["svg", "webp", "jpg"].find(fond.find("type")) == nil)    err.push("fond.type : svg, webp ou jpg attendu")    end
    if (isinstance(fond, map))
        larg = fond.find("largeur")
        haut = fond.find("hauteur")
        if (type(larg) != "int" || type(haut) != "int" || larg <= 0 || haut <= 0)
            err.push("fond : largeur et hauteur entieres positives attendues")
            larg = 0
            haut = 0
        end
    end
    if (d.contains("rafraichissement"))
        var r = d["rafraichissement"]
        if (!visuelFonctions.nombre(r) || r < 1000)    err.push("rafraichissement : nombre >= 1000 attendu")    end
    end
    var els = d.find("elements")
    if (!isinstance(els, list))
        err.push("elements : liste attendue")
        els = []
    end
    var ids = {}
    for i: 0 .. size(els) - 1
        var el = els[i]
        var p = "elements[" + str(i) + "]"
        if (!isinstance(el, map))    err.push(p + " : objet attendu")    continue    end
        var id = el.find("id")
        if (type(id) != "string" || id == "")
            err.push(p + " : id absent")
        elif (ids.contains(id))
            err.push(p + " : id en double")
        else
            ids[id] = true
        end
        var ty = el.find("type")
        if (["voyant", "valeur", "liaison"].find(ty) == nil)    err.push(p + " : type inconnu")    continue    end
        for c: (ty == "liaison" ? ["x", "y", "x2", "y2"] : ["x", "y"])
            var v = el.find(c)
            var maxi = (c[0] == "x" ? larg : haut)
            if (!visuelFonctions.nombre(v))
                err.push(p + " : " + c + " absent")
            elif (maxi > 0 && (v < 0 || v > maxi))
                err.push(p + " : " + c + " hors du fond (0 a " + str(maxi) + ")")
            end
        end
        visuelFonctions.valideSource(p, el, ty, err)
    end
    return err
end
visuelFonctions.valide = visuelFonctions_valide

def visuelFonctions_valideSource(p, el, ty, err)
    import visuelFonctions
    var s = el.find("source")
    if (!isinstance(s, map))    err.push(p + " : source absente")    return    end
    var st = s.find("type")
    var permis = {"voyant": ["relais", "mesure"], "valeur": ["mesure"], "liaison": ["modbus_serie", "modbus_esclave", "esclave", "wifi"]}[ty]
    if (permis.find(st) == nil)    err.push(p + " : source de type inconnue pour un " + ty)    return    end
    if (st == "relais" && (type(s.find("n")) != "int" || s["n"] < 1))    err.push(p + " : source.n absent ou invalide")    end
    if (st == "mesure")
        var ch = s.find("chemin")
        var ok = isinstance(ch, list) && size(ch) > 0
        if (ok)    for c: ch    if (type(c) != "string" || c == "")    ok = false    end    end    end
        if (!ok)    err.push(p + " : source.chemin vide ou invalide")    end
        for cle: ["on", "on_min"]
            if (s.contains(cle) && (ty != "voyant" || (cle == "on_min" && !visuelFonctions.nombre(s[cle]))))
                err.push(p + " : condition " + cle + " refusee ici")
            end
        end
    end
    if (st == "modbus_esclave" && (type(s.find("id")) != "int" || s["id"] < 1))    err.push(p + " : source.id absent ou invalide")    end
    if (st == "esclave" && (type(s.find("mac")) != "string" || s["mac"] == ""))    err.push(p + " : source.mac absent")    end
    if (s.contains("seuil_s"))
        if (!visuelFonctions.nombre(s["seuil_s"]) || s["seuil_s"] <= 0)    err.push(p + " : seuil_s doit etre un nombre positif")    end
    elif (st == "modbus_serie" || st == "modbus_esclave")
        err.push(p + " : seuil_s absent")
    end
end
visuelFonctions.valideSource = visuelFonctions_valideSource

# Lit et valide la description UNE fois (puis la garde). map, ou nil : fichier absent (silence), illisible ou invalide (erreur).
def visuelFonctions_charge()
    import path
    import json
    import string
    import visuelFonctions
    var m = visuelFonctions.etatModule()
    if (m["desc"] != nil)    return m["desc"]    end
    if (!path.exists(visuelFonctions.FICHIER))    return nil    end
    var d
    try
        var f = open(visuelFonctions.FICHIER, "r")
        var texte = f.read()
        f.close()
        d = json.load(texte)
    except .. as erreur, message
        visuelFonctions.log("VISUEL_ERREUR: " + visuelFonctions.FICHIER + " illisible : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        return nil
    end
    var err = visuelFonctions.valide(d)
    if (size(err) > 0)
        visuelFonctions.log(string.format("VISUEL_ERREUR: description refusee (%d defaut(s)), premier : %s !", size(err), err[0]), LOG_LEVEL_ERREUR)
        return nil
    end
    var types = {}
    for el: d["elements"]    types[el["source"]["type"]] = true    end
    m["desc"] = d
    m["types"] = types
    visuelFonctions.log("VISUEL: description chargee, " + str(size(d["elements"])) + " element(s) !", LOG_LEVEL_INFO)
    return d
end
visuelFonctions.charge = visuelFonctions_charge

# Description en JSON pour une page : '<' echappe (pas de </script> possible)
def visuelFonctions_json(d)
    import json
    import string
    return string.replace(json.dump(d), "<", "\\u003c")
end
visuelFonctions.json = visuelFonctions_json

# Bloc a poser sur l'accueil ('' sans description) : conteneur, description, puis visuel.js inline
def visuelFonctions_html()
    import visuelFonctions
    var d = visuelFonctions.charge()
    if (d == nil)    return ""    end
    var js = ""
    try
        var f = open(visuelFonctions.JS, "r")
        js = f.read()
        f.close()
    except .. as erreur, message
        visuelFonctions.log("VISUEL_ERREUR: " + visuelFonctions.JS + " illisible : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        return ""
    end
    return "<div id='vz'></div><script>window.VISUEL=" + visuelFonctions.json(d) + ";</script><script>" + js + "</script>"
end
visuelFonctions.html = visuelFonctions_html

def visuelFonctions_accueil()
    import webserver
    import visuelFonctions
    var h = visuelFonctions.html()
    if (h != "")    webserver.content_send(h)    end
end
visuelFonctions.accueil = visuelFonctions_accueil

# Chemin du fond sur le LittleFS, ou nil : /sd/images/<EXT>/visuel.<ext> d'abord, puis la racine
def visuelFonctions_cheminFond()
    import path
    import string
    import visuelFonctions
    for ext: ["svg", "webp", "jpg"]
        for c: ["/sd/images/" + string.toupper(ext) + "/visuel." + ext, "/visuel." + ext]
            if (path.exists(visuelFonctions.RACINE_FOND + c))    return visuelFonctions.RACINE_FOND + c    end
        end
    end
    return nil
end
visuelFonctions.cheminFond = visuelFonctions_cheminFond

# Reponse d'erreur courte, reponse fermee
def visuelFonctions_refuse(code, texte)
    import webserver
    webserver.content_open(code, "text/plain")
    webserver.content_send(texte)
    webserver.content_close()
end
visuelFonctions.refuse = visuelFonctions_refuse

# f=fond : le fond par morceaux ; 404 et une ligne erreur s'il manque
def visuelFonctions_fond()
    import webserver
    import visuelFonctions
    var chemin = visuelFonctions.cheminFond()
    if (chemin == nil)
        visuelFonctions.refuse(404, "Fond absent")
        visuelFonctions.log("VISUEL_ERREUR: Fond absent (visuel.svg|webp|jpg) !", LOG_LEVEL_ERREUR)
        return
    end
    var mimes = {"svg": "image/svg+xml", "webp": "image/webp", "jpg": "image/jpeg"}
    var mime = mimes[chemin[-3 ..] == "ebp" ? "webp" : chemin[-3 ..]]
    var fichier
    var ouverte = false
    try
        fichier = open(chemin, "rb")
        webserver.header("Cache-Control", "max-age=86400")
        webserver.content_open(200, mime)
        ouverte = true
        while (true)
            var morceau = fichier.readbytes(visuelFonctions.MORCEAU)
            if (morceau == nil || size(morceau) == 0)    break    end
            webserver.content_send(morceau)
            tasmota.yield()
        end
        fichier.close()
        webserver.content_close()
    except .. as erreur, message
        if (fichier != nil)    fichier.close()    end
        if (ouverte)
            webserver.content_close()
        else
            visuelFonctions.refuse(500, "Lecture impossible")
        end
        visuelFonctions.log("VISUEL_ERREUR: Envoi de " + chemin + " : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
    end
end
visuelFonctions.fond = visuelFonctions_fond

# JSON SENSOR reduit aux chemins demandes par les sources `mesure` : {"ANALOG": {"A1": 1.5}}
def visuelFonctions_sensor(d)
    import json
    var brut = json.load(tasmota.read_sensors())
    var r = {}
    if (!isinstance(brut, map))    return r    end
    for el: d["elements"]
        var s = el["source"]
        if (s["type"] != "mesure")    continue    end
        var src = brut
        var dst = r
        var ch = s["chemin"]
        for i: 0 .. size(ch) - 1
            if (!isinstance(src, map) || !src.contains(ch[i]))    break    end
            if (i == size(ch) - 1)
                dst[ch[i]] = src[ch[i]]
            else
                src = src[ch[i]]
                if (!dst.contains(ch[i]))    dst[ch[i]] = {}    end
                dst = dst[ch[i]]
            end
        end
    end
    return r
end
visuelFonctions.sensor = visuelFonctions_sensor

# {"serie_ms", "esclaves": {adresse: millis}} ; {} si ModBus n'est pas charge sur cette carte
def visuelFonctions_modbus()
    var r = {}
    try
        import modbusFonctions
        var e = modbusFonctions.etat()
        r["serie_ms"] = e.find("derniereReponseSerie", 0)
        var esc = {}
        var ips = e.find("ipsApprises", {})
        for a: ips.keys()
            if (isinstance(ips[a], map))    esc[str(a)] = ips[a].find("ms", 0)    end
        end
        r["esclaves"] = esc
    except ..
        r = {}
    end
    return r
end
visuelFonctions.modbus = visuelFonctions_modbus

# Lignes {mac, etat, rssi} des MAC demandees, d'apres etatReseau ; mises en cache CACHE_RESEAU ms. [] sans module ni range extender.
def visuelFonctions_reseau(d)
    import visuelFonctions
    var m = visuelFonctions.etatModule()
    var t = tasmota.millis()
    if (m["reseau"] != nil && t - m["reseau"][0] < visuelFonctions.CACHE_RESEAU)    return m["reseau"][1]    end
    var lignes = []
    try
        import discoveryFonctions
        var macs = {}
        for el: d["elements"]    if (el["source"]["type"] == "esclave")    macs[el["source"]["mac"]] = true    end    end
        var reponse = tasmota.cmd("RgxClients", boolMute)
        var rgx = isinstance(reponse, map) ? reponse.find("RgxClients") : nil
        for l: discoveryFonctions.etatReseau(discoveryFonctions.lisTable(), rgx)
            if (macs.contains(l["mac"]))    lignes.push({"mac": l["mac"], "etat": l["etat"], "rssi": l.find("rssi")})    end
        end
    except .. as erreur, message
        visuelFonctions.log("VISUEL: reseau indisponible : " + str(erreur) + " " + str(message), LOG_LEVEL_DEBUG)
    end
    m["reseau"] = [t, lignes]
    return lignes
end
visuelFonctions.reseau = visuelFonctions_reseau

# L'etat unifie (map) ; blocs seulement pour les types de sources presents. nil sans description.
def visuelFonctions_etat()
    import visuelFonctions
    var d = visuelFonctions.charge()
    if (d == nil)    return nil    end
    var types = visuelFonctions.etatModule()["types"]
    var r = {"t": tasmota.millis()}
    if (types.contains("relais"))    r["power"] = tasmota.get_power()    end
    if (types.contains("mesure"))
        try
            r["sensor"] = visuelFonctions.sensor(d)
        except .. as erreur, message
            r["sensor"] = {}
            visuelFonctions.log("VISUEL: SENSOR illisible : " + str(erreur) + " " + str(message), LOG_LEVEL_DEBUG)
        end
    end
    if (types.contains("modbus_serie") || types.contains("modbus_esclave"))    r["modbus"] = visuelFonctions.modbus()    end
    if (types.contains("wifi"))
        var w = tasmota.wifi()
        r["wifi"] = isinstance(w, map) && w.find("up", false)
    end
    if (types.contains("esclave"))    r["reseau"] = visuelFonctions.reseau(d)    end
    return r
end
visuelFonctions.etat = visuelFonctions_etat

# Route /visuel : f = fond ou etat
def visuelFonctions_route()
    import webserver
    import json
    import visuelFonctions
    if (!webserver.check_privileged_access())    return nil    end
    var f = (webserver.has_arg("f") ? webserver.arg("f") : "")
    if (f == "fond")
        visuelFonctions.fond()
    elif (f == "etat")
        var e = visuelFonctions.etat()
        if (e == nil)
            visuelFonctions.refuse(404, "Pas de visuel")
            return
        end
        webserver.content_open(200, "application/json")
        webserver.content_send(json.dump(e))
        webserver.content_close()
        visuelFonctions.log("VISUEL: etat envoye !", LOG_LEVEL_DEBUG_PLUS)
    else
        visuelFonctions.refuse(404, "Action inconnue")
    end
end
visuelFonctions.route = visuelFonctions_route

# Retourne le module lors de l'importation
return visuelFonctions
