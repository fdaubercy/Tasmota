#- *********************************************************************************************
 * graphiquesFonctions.be - Page web des graphiques de l'historique de la carte (2026-10-18)
 *
 * Fichier de fonctions SANS driver : la route /graphiques est declaree par le driver HISTORIQUE_WEB
 * de historiqueFonctions.be, qui n'importe ce module qu'a la premiere requete : aucune RAM tant que
 * la page n'est pas ouverte. Reserve aux ESP32-S3 et P4, comme l'historique (exclu du LittleFS des
 * ESP32 classiques par custom_files_exclude, platformio_tasmota_cenv.ini).
 *
 * Route /graphiques (acces privilegie : Tasmota exige un Referer qui designe la carte) :
 *     /graphiques                -> la page (bouton « Graphiques » de l'accueil, pose par HISTORIQUE_WEB)
 *     /graphiques?f=echarts.js.gz -> /sd/js/echarts.min.js.gz  (ECharts 6.1.0 complet, gzip, envoye par morceaux)
 *
 * Route POST /graphiques (enregistre()) : parametre composition (x-www-form-urlencoded) = JSON de la composition,
 * ou le texte null pour Retablir ; reponse JSON {"ok":true,"graphiques":[...]|null} ou {"erreur":"..."} (400 : refus,
 * 500 : ecriture impossible). Rien n'est ecrit si la composition est invalide.
 *
 * Gabarit de la page : /sd/html/graphiques.html et /sd/css/graphiques.css ; logique : /sd/js/graphiques_trace.js,
 * /sd/js/graphiques_edition.js puis /sd/js/graphiques.js (envoyes dans cet ordre ; un script absent est ignore).
 *
 * Reglages facultatifs de la page, dans /json/graphiques.json de la carte (source data/<lieu>/<carte>/graphiques.json),
 * lu a l'ouverture de la page seulement : rien en RAM le reste du temps, contrairement au persist (2026-10-18).
 * Une serie s'appelle par son chemin dans le JSON SENSOR, ex. "sensorsCuve.niveauCuve.tauxRemplissage" :
 *     "affichage": {"sensorsCuve.niveauCuve.tauxRemplissage": {"libelle": "Remplissage", "unite": "%", "facteur": 100}}
 *         libelle, unite et facteur (multiplie chaque valeur) par serie ; a defaut, le chemin (esclave ModBus
 *         remplace par son nom) et une unite devinee (Temperature -> °C, Humidity -> %, hauteur -> cm...) ;
 *     "groupes": {"Cuve": ["sensorsCuve.niveauCuve"]}
 *         un graphique par groupe (titre -> debuts de chemin) ; les autres series vont dans « Mesures » ;
 *     "rafraichissement": 60
 *         periode de relecture de l'historique affiche, en secondes (10 au minimum ; mois en cours : 15 min) ;
 *     "direct": 10
 *         cadence par defaut des valeurs en temps reel (/histo?p=direct), en secondes : 0 (arret), 2, 5, 10, 30
 *         ou 60 ; chaque visiteur la change dans la page (liste « Direct »), son choix est garde par son navigateur.
 *     "graphiques": [{"titre": "Cuve", "periode": "jour", "type": "courbe", "series": [{"chemin": "a.b", "type": "aire"}, "c.d"]}]
 *         composition enregistree depuis la page (POST /graphiques), reponse a window.GRAPHIQUES.graphiques ; absente = graphiques
 *         par defaut (groupes). Au plus 8 graphiques de 12 series ; titre de 1 a 60 caracteres ; periode jour, mois ou AAAA-MM[-a]
 *         (-a, -b... = plusieurs graphiques du meme mois) ; type courbe, barres, escalier ou aire (par graphique, et par serie) ;
 *         series = liste de chemins (chaine ou {chemin, type}) ou la chaine "autres" ; toute autre cle est ecartee ; 8192 octets au plus.
 * Dans le bloc diverses.historique du persist (lu aussi par le bouton des ESP32 classiques, controleWeb) :
 *     "grafana": "http://192.168.0.5:3000/d/historique-cuve?var-appareil=%topic%"
 *         bouton vers le tableau Grafana du Pi ; '%topic%' = topic MQTT de la carte. Absent = pas de bouton.
 *
 * Ni Content-Encoding ni cache HTTP depuis Berry : content_open pose « no-cache » et ne permet pas d'autre
 * en-tete, et UfsServe (UFILESYS_STATIC_SERVING) n'envoie pas Content-Encoding. ECharts (1,1 Mo, decide le
 * 2026-10-18 a la place d'uPlot) est donc stocke COMPRESSE (368 Ko) et envoye tel quel ; la page le decompresse
 * (DecompressionStream) et le garde dans le localStorage du navigateur, redemande seulement au changement de version.
 * Source : paquet npm echarts 6.1.0 (integrite sha512 du registre verifiee), dist/echarts.min.js compresse par
 * gzip -9 ; sha256 du .gz : 6d0658f623f5f3a8ae1f9fb8bf275c1388fd54ddfcee13f646bd0df1e2c00418.
********************************************************************************************* -#

#@ solidify:graphiquesFonctions
var graphiquesFonctions = module("graphiquesFonctions")

# Fichiers servis : nom demande (f=) -> [chemin sur le LittleFS, type MIME]
graphiquesFonctions.FICHIERS = {
    "echarts.js.gz": ["/sd/js/echarts.min.js.gz", "application/octet-stream"]
}
graphiquesFonctions.MORCEAU = 2048      # octets lus et envoyes a la fois : borne la RAM
graphiquesFonctions.FICHIER_REGLAGES = "/json/graphiques.json"      # reglages de la page (affichage, groupes)
graphiquesFonctions.VERSION_BIBLIOTHEQUE = "echarts-6.1.0"     # cle du cache localStorage : a changer avec le fichier

# Envoie un fichier du LittleFS par morceaux, en binaire ("rb" : le fichier est compresse)
def graphiquesFonctions_envoieFichier(chemin, mime)
    import webserver
    import path
    import string
    if (!path.exists(chemin))
        webserver.content_open(404, "text/plain")
        webserver.content_send("Fichier absent : " + chemin)
        webserver.content_close()
        logFonctions.log(string.format("GRAPHIQUES_ERREUR: Fichier absent du LittleFS : %s !", chemin), LOG_LEVEL_ERREUR, "serveurWeb")
        return
    end

    var file
    var ouverte = false         # reponse ouverte : a fermer aussi apres une exception
    try
        file = open(chemin, "rb")
        webserver.content_open(200, mime)
        ouverte = true
        while (true)
            var morceau = file.readbytes(graphiquesFonctions.MORCEAU)
            if (morceau == nil || size(morceau) == 0)    break    end
            webserver.content_send(morceau)
            tasmota.yield()
        end
        file.close()
        webserver.content_close()
    except .. as erreur, message
        if (file != nil)    file.close()    end
        if (ouverte)    webserver.content_close()    end
        logFonctions.log(string.format("GRAPHIQUES_ERREUR: Envoi de %s : %s %s !", chemin, erreur, message), LOG_LEVEL_ERREUR, "serveurWeb")
    end
end
graphiquesFonctions.envoieFichier = graphiquesFonctions_envoieFichier

# Route /graphiques : f = fichier statique (echarts.js.gz)
def graphiquesFonctions_route()
    import webserver
    if (!webserver.check_privileged_access())    return nil    end

    var f = (webserver.has_arg("f") ? webserver.arg("f") : "")
    var fichier = graphiquesFonctions.FICHIERS.find(f)
    if (fichier != nil)
        graphiquesFonctions.envoieFichier(fichier[0], fichier[1])
        return
    end

    graphiquesFonctions.page()
end
graphiquesFonctions.route = graphiquesFonctions_route

# URL du tableau Grafana (diverses.historique.grafana) ; '%topic%' y est remplace par le topic MQTT de la
# carte : le meme reglage sert a toutes les cartes. "" = pas de bouton.
def graphiquesFonctions_urlGrafana(historique)
    import string
    var url = str(historique.find("grafana", ""))
    if (string.find(url, "%topic%") > -1)
        var reponse = tasmota.cmd("Topic", true)
        var topic = (isinstance(reponse, map) ? str(reponse.find("Topic", "")) : "")
        url = string.replace(url, "%topic%", topic)
    end
    return url
end
graphiquesFonctions.urlGrafana = graphiquesFonctions_urlGrafana

# Reglages de la page (/json/graphiques.json) ; {} si le fichier est absent ou illisible (erreur journalisee).
# strict : nil si le fichier existe mais est illisible (l'enregistrement ne doit pas l'ecraser : affichage, groupes...
# seraient perdus)
def graphiquesFonctions_lisReglages(strict)
    import path
    import json
    import string
    var chemin = graphiquesFonctions.FICHIER_REGLAGES
    if (!path.exists(chemin))    return {}    end
    var reglages = nil
    var f
    try
        f = open(chemin, "r")
        reglages = json.load(f.read())
        f.close()
    except .. as erreur, message
        if (f != nil)    f.close()    end
        logFonctions.log(string.format("GRAPHIQUES_ERREUR: Lecture de %s : %s %s !", chemin, erreur, message), LOG_LEVEL_ERREUR, "serveurWeb")
    end
    if (!isinstance(reglages, map))
        logFonctions.log(string.format("GRAPHIQUES_ERREUR: %s n'est pas un objet JSON : reglages ignores !", chemin), LOG_LEVEL_ERREUR, "serveurWeb")
        return (strict ? nil : {})
    end
    return reglages
end
graphiquesFonctions.lisReglages = graphiquesFonctions_lisReglages

# Periode de relecture de la page en secondes (reglage 'rafraichissement') : 60 par defaut, 10 au minimum
# (chaque relecture de la vue 24 h coute une requete /histo d'environ 10 Ko a la carte)
def graphiquesFonctions_periode(v)
    if (type(v) != "int" && type(v) != "real")    return 60    end
    return (v < 10 ? 10 : int(v))
end
graphiquesFonctions.periode = graphiquesFonctions_periode

# Cadence par defaut du temps reel en secondes (reglage 'direct') : une des valeurs de la liste de la page, 10 sinon
def graphiquesFonctions_cadenceDirect(v)
    if ((type(v) == "int" || type(v) == "real") && [0, 2, 5, 10, 30, 60].find(int(v)) != nil)    return int(v)    end
    return 10
end
graphiquesFonctions.cadenceDirect = graphiquesFonctions_cadenceDirect

# Noms des esclaves ModBus du persist (drivers.ModBus.environnement.TasmotaSlaveModBus) : cle -> name,
# pour les libelles par defaut des series TasmotaSlaveModBus.<cle>.* ; {} sans driver ModBus
def graphiquesFonctions_nomsEsclaves()
    import global
    var noms = {}
    var esclaves = (global.contains("drivers") ? global.drivers : nil)
    for cle: ["ModBus", "environnement", "TasmotaSlaveModBus"]      # chaque niveau peut manquer ou ne pas etre une map
        if (!isinstance(esclaves, map))    return noms    end
        esclaves = esclaves.find(cle)
    end
    if (!isinstance(esclaves, map))    return noms    end
    for cle: esclaves.keys()
        var e = esclaves[cle]
        if (isinstance(e, map) && e.find("name") != nil)    noms[cle] = str(e["name"])    end
    end
    return noms
end
graphiquesFonctions.nomsEsclaves = graphiquesFonctions_nomsEsclaves

# Page des graphiques, au gabarit Tasmota : le trace est fait dans le navigateur par /sd/js/graphiques.js,
# qui lit /histo ; la carte ne fournit que la configuration (window.GRAPHIQUES)
def graphiquesFonctions_page()
    import webserver
    import json
    import historiqueFonctions
    import gestionFileFolder

    var noms = historiqueFonctions.nomsInstances()
    var historique = (historiqueFonctions.config != nil ? historiqueFonctions.config : {})
    var reglages = graphiquesFonctions.lisReglages()
    var carte = def (m, cle) var v = m.find(cle) return (isinstance(v, map) ? v : {}) end     # mal type -> {} (le JS attend des objets)
    var config = {"bibliotheque": graphiquesFonctions.VERSION_BIBLIOTHEQUE, "nom": (size(noms) > 0 ? noms[0] : "mesures"),
                  "affichage": carte(reglages, "affichage"), "groupes": carte(reglages, "groupes"),
                  "grafana": graphiquesFonctions.urlGrafana(historique), "compteurs": carte(historique, "compteurs"),
                  "esclaves": graphiquesFonctions.nomsEsclaves(),
                  "rafraichissement": graphiquesFonctions.periode(reglages.find("rafraichissement")),
                  "direct": graphiquesFonctions.cadenceDirect(reglages.find("direct")),
                  "graphiques": (isinstance(reglages.find("graphiques"), list) ? reglages.find("graphiques") : nil)}
    logFonctions.log("GRAPHIQUES: Page des graphiques demandee !", LOG_LEVEL_DEBUG, "serveurWeb")

    webserver.content_start("Graphiques")
    webserver.content_send_style()
    webserver.content_send("<style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/css/graphiques.css")
    webserver.content_send("</style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/html/graphiques.html")
    # '</' echappe : un libelle du persist contenant '</script>' ne peut pas fermer le script
    import string
    webserver.content_send("<script>window.GRAPHIQUES=" + string.replace(json.dump(config), "</", "<\\/") + ";</script><script>")
    # trace, edition puis page : un script absent (fichier pas encore televerse) ne casse pas la page
    import path
    for js: ["/sd/js/graphiques_trace.js", "/sd/js/graphiques_edition.js"]
        if (path.exists(js))
            gestionFileFolder.readFileByLineAndContentSend(js)
            webserver.content_send("\n")
        end
    end
    gestionFileFolder.readFileByLineAndContentSend("/sd/js/graphiques.js")
    webserver.content_send("</script>")
    webserver.content_button(webserver.BUTTON_MAIN)
    webserver.content_stop()
end
graphiquesFonctions.page = graphiquesFonctions_page

# ---- Composition des graphiques (POST /graphiques, 2026-10-19) -----------------------------------
graphiquesFonctions.MAX_GRAPHIQUES = 8      # graphiques par composition
graphiquesFonctions.MAX_SERIES = 12         # series par graphique
graphiquesFonctions.MAX_CORPS = 8192        # octets acceptes pour le parametre composition (controle avant json.load)
graphiquesFonctions.TYPES = ["courbe", "barres", "escalier", "aire"]

# Texte sans ses espaces, tabulations et fins de ligne de debut et de fin
def graphiquesFonctions_rogne(t)
    import string
    var d = 0
    var f = size(t)
    while (d < f && string.find(" \t\r\n", t[d]) >= 0)    d += 1    end
    while (f > d && string.find(" \t\r\n", t[f - 1]) >= 0)    f -= 1    end
    return (f > d ? t[d .. f - 1] : "")
end
graphiquesFonctions.rogne = graphiquesFonctions_rogne

# Periode valide : "jour", "mois", ou un mois "AAAA-MM" suivi eventuellement de "-a", "-b"...
def graphiquesFonctions_periodeValide(p)
    import string
    if (type(p) != "string")    return false    end
    if (p == "jour" || p == "mois")    return true    end
    var n = size(p)
    if (n != 7 && n != 9)    return false    end
    for i: [0, 1, 2, 3, 5, 6]
        if (string.find("0123456789", p[i]) < 0)    return false    end
    end
    if (p[4] != "-")    return false    end
    var mois = int(p[5 .. 6])
    if (mois < 1 || mois > 12)    return false    end
    return (n == 7 || (p[7] == "-" && p[8] >= "a" && p[8] <= "z"))
end
graphiquesFonctions.periodeValide = graphiquesFonctions_periodeValide

# Valide et nettoie une composition (frontiere systeme : texte venu du navigateur).
# Retourne [composition_nettoyee, nil] ou [nil, "message d'erreur"]
def graphiquesFonctions_valideComposition(c)
    var G = graphiquesFonctions
    if (!isinstance(c, list))    return [nil, "La composition doit etre une liste de graphiques"]    end
    if (size(c) > G.MAX_GRAPHIQUES)
        return [nil, "Trop de graphiques (" + str(G.MAX_GRAPHIQUES) + " au plus)"]
    end
    var propre = []
    for i: 0 .. size(c) - 1
        var g = c[i]
        var nom = "Graphique " + str(i + 1)
        if (!isinstance(g, map))    return [nil, nom + " : doit etre un objet"]    end
        var titre = g.find("titre")
        if (type(titre) != "string")    return [nil, nom + " : titre absent"]    end
        titre = G.rogne(titre)
        if (size(titre) < 1 || size(titre) > 60)    return [nil, nom + " : le titre doit faire de 1 a 60 caracteres"]    end
        var periode = g.find("periode")
        if (periode == nil)    periode = "jour"    end
        if (!G.periodeValide(periode))    return [nil, nom + " : periode invalide"]    end
        var genre = g.find("type")
        if (genre == nil)    genre = "courbe"    end
        if (type(genre) != "string" || G.TYPES.find(genre) == nil)    return [nil, nom + " : type inconnu"]    end
        var series = g.find("series")
        if (type(series) == "string")
            if (series != "autres")    return [nil, nom + " : series doit etre une liste ou \"autres\""]    end
        elif (isinstance(series, list))
            if (size(series) > G.MAX_SERIES)
                return [nil, nom + " : trop de series (" + str(G.MAX_SERIES) + " au plus)"]
            end
            var sp = []
            for j: 0 .. size(series) - 1
                var s = series[j]
                if (type(s) == "string")    s = {"chemin": s}    end
                if (!isinstance(s, map))    return [nil, nom + " : serie " + str(j + 1) + " invalide"]    end
                var chemin = s.find("chemin")
                if (type(chemin) != "string" || size(chemin) < 1 || size(chemin) > 120)
                    return [nil, nom + " : serie " + str(j + 1) + " : chemin de 1 a 120 caracteres attendu"]
                end
                var e = {"chemin": chemin}
                var t = s.find("type")
                if (t != nil)
                    if (type(t) != "string" || G.TYPES.find(t) == nil)    return [nil, nom + " : serie " + str(j + 1) + " : type inconnu"]    end
                    e["type"] = t
                end
                sp.push(e)
            end
            series = sp
        else
            return [nil, nom + " : series absente"]
        end
        propre.push({"titre": titre, "periode": periode, "type": genre, "series": series})
    end
    return [propre, nil]
end
graphiquesFonctions.valideComposition = graphiquesFonctions_valideComposition

# Ecrit les reglages dans FICHIER_REGLAGES : fichier temporaire puis renommage ; true si reussi
def graphiquesFonctions_ecrisReglages(reglages)
    import path
    import json
    import string
    var chemin = graphiquesFonctions.FICHIER_REGLAGES
    var tmp = chemin + ".tmp"
    var f
    try
        f = open(tmp, "w")
        f.write(json.dump(reglages))
        f.close()
        f = nil
        var ok = path.rename(tmp, chemin)
        if (!ok)                    # le renommage refuse d'ecraser : on retire la destination et on recommence
            path.remove(chemin)
            ok = path.rename(tmp, chemin)
        end
        if (!ok)    raise "io_error", "renommage impossible"    end
        return true
    except .. as erreur, message
        if (f != nil)    f.close()    end
        try
            if (path.exists(tmp))    path.remove(tmp)    end
        except ..
        end
        logFonctions.log(string.format("GRAPHIQUES_ERREUR: Ecriture de %s : %s %s !", chemin, erreur, message), LOG_LEVEL_ERREUR, "serveurWeb")
        return false
    end
end
graphiquesFonctions.ecrisReglages = graphiquesFonctions_ecrisReglages

# Traite le parametre composition ; retourne [code HTTP, reponse sous forme de map]
def graphiquesFonctions_traiteComposition()
    import webserver
    import json
    import string
    var G = graphiquesFonctions
    var refus = def (message)
        logFonctions.log(string.format("GRAPHIQUES_ERREUR: Composition refusee : %s !", message), LOG_LEVEL_ERREUR, "serveurWeb")
        return [400, {"erreur": message}]
    end
    if (!webserver.has_arg("composition"))    return refus("parametre composition absent")    end
    var texte = webserver.arg("composition")
    if (type(texte) != "string")    return refus("parametre composition illisible")    end
    if (size(texte) > G.MAX_CORPS)    return refus("composition trop grosse (" + str(G.MAX_CORPS) + " octets au plus)")    end

    var composition = nil
    if (G.rogne(texte) != "null")       # null = Retablir : on supprime la cle
        var lue = json.load(texte)
        if (lue == nil)    return refus("JSON illisible")    end
        var verdict = G.valideComposition(lue)
        if (verdict[1] != nil)    return refus(verdict[1])    end
        composition = verdict[0]
    end

    var reglages = G.lisReglages(true)
    if (reglages == nil)    return [500, {"erreur": "graphiques.json illisible sur la carte : rien n'est remplace"}]    end
    if (composition == nil)    reglages.remove("graphiques")    else    reglages["graphiques"] = composition    end
    if (!G.ecrisReglages(reglages))
        return [500, {"erreur": "Ecriture impossible sur la carte"}]
    end
    if (composition == nil)
        logFonctions.log("GRAPHIQUES: Composition retablie (reglages par defaut) !", LOG_LEVEL_INFO, "serveurWeb")
    else
        logFonctions.log(string.format("GRAPHIQUES: Composition enregistree (%i graphiques) !", size(composition)), LOG_LEVEL_INFO, "serveurWeb")
    end
    return [200, {"ok": true, "graphiques": composition}]
end
graphiquesFonctions.traiteComposition = graphiquesFonctions_traiteComposition

# POST /graphiques : enregistre la composition (parametre composition = JSON, ou "null" pour Retablir)
def graphiquesFonctions_enregistre()
    import webserver
    import json
    import string
    if (!webserver.check_privileged_access())    return nil    end

    var ouverte = false         # reponse ouverte : a fermer aussi apres une exception
    try
        var verdict = graphiquesFonctions.traiteComposition()
        webserver.content_open(verdict[0], "application/json")
        ouverte = true
        if (verdict[0] == 200)      # "null" ecrit a la main : json.dump(nil) n'est pas garanti
            var g = verdict[1]["graphiques"]
            webserver.content_send("{\"ok\":true,\"graphiques\":" + (g == nil ? "null" : json.dump(g)) + "}")
        else
            webserver.content_send(json.dump(verdict[1]))
        end
        webserver.content_close()
    except .. as erreur, message
        logFonctions.log(string.format("GRAPHIQUES_ERREUR: Enregistrement : %s %s !", erreur, message), LOG_LEVEL_ERREUR, "serveurWeb")
        try
            if (!ouverte)               # exception avant la reponse : le navigateur ne doit pas attendre sans fin
                webserver.content_open(500, "application/json")
                webserver.content_send("{\"erreur\":\"Erreur interne de la carte\"}")
            end
            webserver.content_close()
        except ..
        end
    end
end
graphiquesFonctions.enregistre = graphiquesFonctions_enregistre

# Retourne le module lors de l'importation
return graphiquesFonctions
