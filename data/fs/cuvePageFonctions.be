#- *********************************************************************************************
 * cuvePageFonctions.be - Page web du niveau de la cuve, en jauges (2026-10-31, premier essai)
 *
 * Fichier de fonctions SANS driver : la route /cuve est declaree par le driver de la carte qui affiche
 * l'encadre du niveau (CAPTEURS_CUVE de la cuve, CONTROLE_GARAGE du maitre P4), qui n'importe ce module
 * qu'a la premiere requete : aucune RAM tant que la page n'est pas ouverte. Lien depuis la legende de
 * /sd/html/webSensorNiveauCuve.html.
 *
 * Route /cuve (acces privilegie : Tasmota exige un Referer qui designe la carte) :
 *     /cuve                    -> la page : jauge liquide (volume en litres), demi-cercle (taux en %) et cadran
 *                                 des tensions (brute a l'entree de l'ADS1115, et sonde 0-10 V recalculee par le pont)
 *     /cuve?f=liquidfill.js.gz -> /sd/js/echarts-liquidfill.min.js.gz (extension echarts-liquidfill, gzip)
 * ECharts lui-meme vient de /graphiques?f=echarts.js.gz (graphiquesFonctions), meme cle de cache localStorage
 * que la page des graphiques : il n'est pas retelecharge d'une page a l'autre.
 *
 * Valeurs : lues par la page dans /histo?p=direct (historiqueFonctions), series ...niveauCuve.volume et
 * ...niveauCuve.tauxRemplissage. Sans historique actif sur la carte, la page l'indique et n'affiche rien.
 *
 * Gabarit : /sd/html/cuve.html et /sd/css/cuve.css ; logique : /sd/js/cuve.js. Donnees de la carte dans
 * window.CUVE (volume maximal tire des dimensions de la cuve, versions des bibliotheques, nom de l'historique).
 *
 * Extension : paquet npm echarts-liquidfill 3.1.0 (MIT, integrite sha512 du registre verifiee),
 * dist/echarts-liquidfill.min.js compresse par gzip -9 -n ; sha256 du .gz :
 * ce5237145fd586dec775a119bdec6d8c333c066e816c513c9aaf5b40a7e9522b. Faite pour ECharts 5 ; rendu verifie avec
 * l'ECharts 6.1.0 des cartes le 2026-10-31 (tasks/plans/jauges-cuve.md, A1).
 *
 * SOLIDIFIE dans le firmware de la cuve et du P4 (custom_berry_solidify) : aucun etat dans le module (sa table
 * est en lecture seule une fois solidifie, piege 12 de outils_docs/SOLIDIFICATION_BERRY.md).
********************************************************************************************* -#

#@ solidify:cuvePageFonctions
var cuvePageFonctions = module("cuvePageFonctions")

# Fichiers servis : nom demande (f=) -> [chemin sur le LittleFS, type MIME]
cuvePageFonctions.FICHIERS = {
    "liquidfill.js.gz": ["/sd/js/echarts-liquidfill.min.js.gz", "application/octet-stream"]
}
cuvePageFonctions.VERSION_EXTENSION = "liquidfill-3.1.0"      # cle du cache localStorage : a changer avec le fichier

# Dimension en cm lue dans le bloc dimensions ; 100 si absente ou invalide (meme defaut que controleGarage)
def cuvePageFonctions_dimension(dimensions, cle)
    var v = (isinstance(dimensions, map) ? dimensions.find(cle) : nil)
    return ((type(v) == "int" || type(v) == "real") && v > 0 ? v : 100)
end
cuvePageFonctions.dimension = cuvePageFonctions_dimension

# Echelles du cadran des tensions : {"entreeMax_V", "sondeMax_V"} (reels > 0 ; cuveFonctions.montageSonde), ou nil si
# la carte ne connait pas le montage (la page prend alors 3,3 V a l'entree de l'ADS1115 et 10 V pour la sonde)
def cuvePageFonctions_sonde(sonde)
    if (!isinstance(sonde, map))    return nil    end
    for cle: ["entreeMax_V", "sondeMax_V"]
        var v = sonde.find(cle)
        if ((type(v) != "int" && type(v) != "real") || v <= 0)    return nil    end
    end
    return sonde
end
cuvePageFonctions.sonde = cuvePageFonctions_sonde

# Route /cuve : f = fichier statique (liquidfill.js.gz), sinon la page.
# dimensions : bloc {hauteur, longueur, largeur} en cm de la cuve ; sonde : voir sonde(). Fournis par le driver de la carte
def cuvePageFonctions_route(dimensions, sonde)
    import webserver
    if (!webserver.check_privileged_access())    return nil    end

    var f = (webserver.has_arg("f") ? webserver.arg("f") : "")
    var fichier = cuvePageFonctions.FICHIERS.find(f)
    if (fichier != nil)
        import graphiquesFonctions
        graphiquesFonctions.envoieFichier(fichier[0], fichier[1])
        return
    end

    cuvePageFonctions.page(dimensions, sonde)
end
cuvePageFonctions.route = cuvePageFonctions_route

def cuvePageFonctions_page(dimensions, sonde)
    import webserver
    import json
    import string
    import gestionFileFolder
    import graphiquesFonctions
    import historiqueFonctions

    var hauteur = cuvePageFonctions.dimension(dimensions, "hauteur")
    var volumeMax = int(hauteur * cuvePageFonctions.dimension(dimensions, "longueur") * cuvePageFonctions.dimension(dimensions, "largeur") / 1000)   # cm3 -> L
    var noms = historiqueFonctions.nomsInstances()
    var config = {"bibliotheque": graphiquesFonctions.VERSION_BIBLIOTHEQUE, "extension": cuvePageFonctions.VERSION_EXTENSION,
                  "nom": (size(noms) > 0 ? noms[0] : ""), "volumeMax": volumeMax, "hauteur": hauteur,
                  "sonde": cuvePageFonctions.sonde(sonde)}
    logFonctions.log(string.format("CUVE_PAGE: Page du niveau demandee (volume max %i L) !", volumeMax), LOG_LEVEL_DEBUG, "serveurWeb")

    webserver.content_start("Niveau de la cuve")
    webserver.content_send_style()
    webserver.content_send("<style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/css/cuve.css")
    webserver.content_send("</style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/html/cuve.html")
    webserver.content_send("<script>window.CUVE=" + string.replace(json.dump(config), "</", "<\\/") + ";</script><script>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/js/cuve.js")
    webserver.content_send("</script>")
    webserver.content_button(webserver.BUTTON_MAIN)
    webserver.content_stop()
end
cuvePageFonctions.page = cuvePageFonctions_page

# Retourne le module lors de l'importation
return cuvePageFonctions
