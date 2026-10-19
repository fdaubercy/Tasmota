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
 * Gabarit de la page : /sd/html/graphiques.html et /sd/css/graphiques.css ; logique : /sd/js/graphiques.js.
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

# Reglages de la page (/json/graphiques.json) ; {} si le fichier est absent ou illisible (erreur journalisee)
def graphiquesFonctions_lisReglages()
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
        return {}
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
                  "direct": graphiquesFonctions.cadenceDirect(reglages.find("direct"))}
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
    gestionFileFolder.readFileByLineAndContentSend("/sd/js/graphiques.js")
    webserver.content_send("</script>")
    webserver.content_button(webserver.BUTTON_MAIN)
    webserver.content_stop()
end
graphiquesFonctions.page = graphiquesFonctions_page

# Retourne le module lors de l'importation
return graphiquesFonctions
