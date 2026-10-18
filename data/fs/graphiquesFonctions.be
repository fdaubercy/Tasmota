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
 *     /graphiques?f=uplot.js     -> /sd/js/uPlot.iife.min.js   (uPlot 1.6.30, envoye par morceaux)
 *     /graphiques?f=uplot.css    -> /sd/css/uPlot.min.css
 *
 * Reglages facultatifs de la page, dans le bloc diverses.historique du persist de la carte :
 *     "affichage": {"tauxRemplissage": {"libelle": "Remplissage", "unite": "%", "facteur": 100}, ...}
 *         libelle, unite et facteur (multiplie chaque valeur) par serie ; a defaut, le nom de la serie et une
 *         unite devinee de ce nom (temperature -> °C, hauteur -> cm, volume -> L, taux -> %...) ;
 *     "grafana": "http://192.168.0.5:3000/d/historique-cuve?var-appareil=%topic%"
 *         bouton vers le tableau Grafana du Pi ; '%topic%' = topic MQTT de la carte. Absent = pas de bouton.
 *
 * Ni gzip ni cache HTTP depuis Berry : content_open pose « no-cache » et ne permet pas d'autre en-tete,
 * et UfsServe (UFILESYS_STATIC_SERVING) n'envoie pas Content-Encoding. La page garde donc uPlot dans le
 * localStorage du navigateur et ne le redemande qu'au changement de version.
********************************************************************************************* -#

var graphiquesFonctions = module("graphiquesFonctions")

# Fichiers servis : nom demande (f=) -> [chemin sur le LittleFS, type MIME]
graphiquesFonctions.FICHIERS = {
    "uplot.js":  ["/sd/js/uPlot.iife.min.js", "application/javascript"],
    "uplot.css": ["/sd/css/uPlot.min.css", "text/css"]
}
graphiquesFonctions.MORCEAU = 2048      # octets lus et envoyes a la fois : borne la RAM
graphiquesFonctions.VERSION_UPLOT = "uPlot-1.6.30"     # cle du cache localStorage : a changer avec le fichier

# Envoie un fichier du LittleFS par morceaux (uPlot tient sur une seule ligne de 49 Ko)
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
        file = open(chemin, "r")
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

# Route /graphiques : f = fichier statique (uplot.js, uplot.css)
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

# Page des graphiques, au gabarit Tasmota : le trace est fait dans le navigateur par /sd/js/graphiques.js,
# qui lit /histo ; la carte ne fournit que la configuration (window.GRAPHIQUES)
def graphiquesFonctions_page()
    import webserver
    import json
    import historiqueFonctions
    import gestionFileFolder

    var noms = historiqueFonctions.nomsInstances()
    var historique = (historiqueFonctions.config != nil ? historiqueFonctions.config : {})
    var config = {"uplot": graphiquesFonctions.VERSION_UPLOT, "nom": (size(noms) > 0 ? noms[0] : "mesures"),
                  "affichage": historique.find("affichage", {}), "grafana": graphiquesFonctions.urlGrafana(historique)}
    logFonctions.log("GRAPHIQUES: Page des graphiques demandee !", LOG_LEVEL_DEBUG, "serveurWeb")

    webserver.content_start("Graphiques")
    webserver.content_send_style()
    webserver.content_send("<link rel='stylesheet' href='/graphiques?f=uplot.css'>"
                           "<style>#g_zone{text-align:left;max-width:calc(100vw - 24px)}#g_msg{margin:8px 0}.u-legend{font-size:12px}"
                           "#g_barre{display:flex;flex-wrap:wrap}#g_barre select,#g_barre button{width:auto;max-width:100%;"
                           "margin:0 8px 8px 0;padding:0 12px}#g_series{margin:8px 0;font-size:14px}"
                           "@media(max-width:600px){.u-title{font-size:14px}}</style>"
                           "<div id='g_zone'><div id='g_barre'><select id='g_vue'></select>"
                           "<button id='g_grafana' style='display:none'>Historique long (Grafana)</button></div>"
                           "<p id='g_msg'>Chargement...</p><div id='g_trace'></div><div id='g_series'></div></div>")
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
