#- *********************************************************************************************
 * pagesGraphiques.be - Moteur commun des pages de graphiques d'une carte (atelier des graphiques, 2026-11-03)
 *
 * Spec : docs/superpowers/specs/2026-11-03-atelier-graphiques-design.md (4.1, 4.2, 7) ; plan
 * tasks/plans/atelier-graphiques.md (A2). Banc : outils_docs/scripts_python/berry/banc_pages_graphiques.py.
 *
 * Chargement : l'autoexec de la carte fait demarrage.charge(["pagesGraphiques"]) (module sur le LittleFS ou
 * solidifie). L'import appelle init(m) (be_module.c::module_init), qui pose le driver PAGES_GRAPHIQUES et rend
 * le module. init() NE LIT PAS la description : toute fonction qui importe ce module, appelee pendant init(),
 * relancerait l'import (le module n'est mis en cache qu'apres init) et donc init(), jusqu'au debordement de pile.
 * demarre() est appele par le driver, dans web_add_handler (une fois, au lancement du serveur web).
 *
 * Description : /json/pages_graphiques.json (source data/<lieu>/<carte>/pages_graphiques.json, ecrite par
 * l'atelier). Validation : module voisin data/fs/pagesGraphiquesValidation.be (meme verdict que
 * outils_docs/scripts_python/outils_pc/atelier_graphiques_description.py::valide), a embarquer et solidifier (ou non)
 * TOUJOURS avec ce module ; separe pour que chaque fichier reste sous 500 lignes.
 * Au demarrage, seul l'index (id, titre, acces de chaque page) reste en RAM, dans la globale cachee
 * '.pagesGraphiques' : la table du module est en lecture seule une fois solidifie (piege 12 de
 * outils_docs/SOLIDIFICATION_BERRY.md). Les graphiques ne sont relus qu'a l'ouverture d'une page.
 * Description absente, tronquee, illisible ou invalide : aucun bouton, et la page repond « Description invalide »
 * avec le motif (log PAGES_GRAPHIQUES_ERREUR) ; les autres routes de la carte ne sont pas touchees.
 *
 * Route /pages (GET, acces privilegie : Tasmota exige un Referer qui designe la carte) :
 *     /pages?p=<id>                      -> la page (bouton d'accueil si acces "bouton", sinon lien d'un encadre)
 *     /pages?f=valeurs&c=<a.b>,<c.d>...  -> {"t": <utc>, "valeurs": {"a.b": 21.5, "c.d": null}} lu dans
 *                                           tasmota.read_sensors() ; 12 chemins au plus, sinon 400 {"erreur": ...}
 *     /pages?f=sources                   -> {"historique": true|false, "flash": []} (adaptateurs en flash : palier 4)
 *     /pages?f=liquidfill.js.gz          -> /sd/js/echarts-liquidfill.min.js.gz, par morceaux de 2048 octets
 * ECharts reste servi par /graphiques?f=echarts.js.gz (graphiquesFonctions), meme cle de cache localStorage.
 * Independant de historiqueFonctions (spec 7.4) : seul f=sources dit si l'historique est present.
 *
 * Contrat du gabarit (fichiers ecrits par l'action A3, envoyes dans cet ordre ; un fichier absent est journalise
 * et saute) : <style> + /sd/css/pages_graphiques.css + </style>, /sd/html/pages_graphiques.html, puis
 *     <script>window.PAGE_GRAPHIQUES={"page": <la page de la description>, "calculees": <calculees de la
 *     description, {} si aucune>, "bibliotheque": "echarts-6.1.0", "extension": "liquidfill-3.1.0",
 *     "historique": true|false};</script>
 * ('</' y est ecrit '<\/'), puis <script> /sd/js/pages_graphiques_formule.js, /sd/js/pages_graphiques.js </script>.
 *
 * Solidifiable : aucun etat dans la table du module, 'import pagesGraphiques' dans toute fonction qui le cite,
 * appels par pagesGraphiques.nom (jamais par le nom global d'une fonction, qui n'existe pas une fois solidifie).
********************************************************************************************* -#

#@ solidify:pagesGraphiques
var pagesGraphiques = module("pagesGraphiques")

pagesGraphiques.FICHIER = "/json/pages_graphiques.json"
pagesGraphiques.MAX_FICHIER = 32768         # octets du fichier lu : au-dela, refuse sans le lire (le JSON compact, lui, est borne a 8192)
pagesGraphiques.GABARIT_CSS = "/sd/css/pages_graphiques.css"
pagesGraphiques.GABARIT_HTML = "/sd/html/pages_graphiques.html"
pagesGraphiques.SCRIPTS = ["/sd/js/pages_graphiques_formule.js", "/sd/js/pages_graphiques.js"]
pagesGraphiques.FICHIER_LIQUIDFILL = "/sd/js/echarts-liquidfill.min.js.gz"
pagesGraphiques.MORCEAU = 2048              # octets lus et envoyes a la fois : borne la RAM
pagesGraphiques.MAX_CHEMINS = 12            # chemins par requete f=valeurs
pagesGraphiques.VERSION_BIBLIOTHEQUE = "echarts-6.1.0"     # = graphiquesFonctions.VERSION_BIBLIOTHEQUE (verifie par le banc)
pagesGraphiques.VERSION_EXTENSION = "liquidfill-3.1.0"     # = cuvePageFonctions.VERSION_EXTENSION (verifie par le banc)

# ---- Lecture de la description --------------------------------------------------------------------

# [description, nil] si elle est lisible et valide, [nil, motif] sinon (motif journalise en erreur)
def pagesGraphiques_lisDescription()
    import pagesGraphiques
    import path
    import json
    import string
    var P = pagesGraphiques
    var motif = nil
    var d = nil
    var f
    try
        if (!path.exists(P.FICHIER))
            motif = "description absente"
        else
            f = open(P.FICHIER, "r")
            var n = f.size()
            if (n > P.MAX_FICHIER)
                motif = string.format("fichier de %i octets (%i au plus)", n, P.MAX_FICHIER)
            else
                d = json.load(f.read())
                if (d == nil)    motif = "JSON illisible (fichier tronque ?)"    end
            end
            f.close()
            f = nil
        end
        if (motif == nil)
            import pagesGraphiquesValidation
            var motifs = pagesGraphiquesValidation.valide(d)
            if (size(motifs) > 0)    motif = motifs[0] + (size(motifs) > 1 ? string.format(" (et %i autre(s) motif(s))", size(motifs) - 1) : "")    end
        end
    except .. as erreur, message
        if (f != nil)    f.close()    end
        motif = string.format("lecture impossible : %s %s", erreur, message)
    end
    if (motif != nil)
        logFonctions.log(string.format("PAGES_GRAPHIQUES_ERREUR: Description %s invalide : %s !", P.FICHIER, motif), LOG_LEVEL_ERREUR, "serveurWeb")
        return [nil, motif]
    end
    return [d, nil]
end
pagesGraphiques.lisDescription = pagesGraphiques_lisDescription

# Lit la description et ne garde que l'index [[id, titre, acces], ...] dans la globale cachee ; rend l'index
def pagesGraphiques_demarre()
    import pagesGraphiques
    import global
    import string
    var lu = pagesGraphiques.lisDescription()
    var index = []
    if (lu[0] != nil)
        for p: lu[0]["pages"]    index.push([p["id"], p["titre"], p.find("acces", "bouton")])    end
    end
    global.(".pagesGraphiques") = index
    logFonctions.log(string.format("PAGES_GRAPHIQUES: %i page(s) de graphiques declaree(s) !", size(index)), LOG_LEVEL_INFO, "serveurWeb")
    return index
end
pagesGraphiques.demarre = pagesGraphiques_demarre

# Index des pages ([] avant demarre())
def pagesGraphiques_index()
    import global
    return (global.contains(".pagesGraphiques") ? global.(".pagesGraphiques") : [])
end
pagesGraphiques.index = pagesGraphiques_index

# ---- Pages et reponses --------------------------------------------------------------------------

# Texte sans caractere HTML actif
def pagesGraphiques_echappe(t)
    import string
    t = string.replace(str(t), "&", "&amp;")
    t = string.replace(t, "<", "&lt;")
    t = string.replace(t, ">", "&gt;")
    t = string.replace(t, "\"", "&quot;")
    return string.replace(t, "'", "&#39;")
end
pagesGraphiques.echappe = pagesGraphiques_echappe

# Un bouton d'accueil par page a acces "bouton" (web_add_main_button : index en RAM seulement, aucun fichier lu)
def pagesGraphiques_boutons()
    import pagesGraphiques
    import webserver
    for e: pagesGraphiques.index()
        if (e[2] == "bouton")
            webserver.content_send("<p></p><form action='/pages' method='get'><input type='hidden' name='p' value='" + e[0] +
                                   "'><button>" + pagesGraphiques.echappe(e[1]) + "</button></form>")
        end
    end
end
pagesGraphiques.boutons = pagesGraphiques_boutons

def pagesGraphiques_repondJson(code, objet)
    import webserver
    import json
    webserver.content_open(code, "application/json")
    webserver.content_send(json.dump(objet))
    webserver.content_close()
end
pagesGraphiques.repondJson = pagesGraphiques_repondJson

# Page de message au gabarit Tasmota (description invalide, page inconnue)
def pagesGraphiques_pageMessage(titre, texte)
    import pagesGraphiques
    import webserver
    webserver.content_start("Pages de graphiques")
    webserver.content_send_style()
    webserver.content_send("<p><b>" + titre + "</b> : " + pagesGraphiques.echappe(texte) + "</p>")
    webserver.content_button(webserver.BUTTON_MAIN)
    webserver.content_stop()
end
pagesGraphiques.pageMessage = pagesGraphiques_pageMessage

# Envoie un fichier texte du gabarit ; absent (pas encore televerse) : journalise et saute, la page continue
def pagesGraphiques_envoieTexte(chemin)
    import path
    import string
    import gestionFileFolder
    if (path.exists(chemin))
        gestionFileFolder.readFileByLineAndContentSend(chemin)
    else
        logFonctions.log(string.format("PAGES_GRAPHIQUES_ERREUR: Fichier du gabarit absent : %s !", chemin), LOG_LEVEL_ERREUR, "serveurWeb")
    end
end
pagesGraphiques.envoieTexte = pagesGraphiques_envoieTexte

# Envoie un fichier binaire par morceaux (meme mecanisme que graphiquesFonctions.envoieFichier, sans en dependre)
def pagesGraphiques_envoieFichier(chemin, mime)
    import pagesGraphiques
    import webserver
    import path
    import string
    if (!path.exists(chemin))
        logFonctions.log(string.format("PAGES_GRAPHIQUES_ERREUR: Fichier absent du LittleFS : %s !", chemin), LOG_LEVEL_ERREUR, "serveurWeb")
        pagesGraphiques.repondJson(404, {"erreur": "fichier absent"})
        return
    end
    var file
    var ouverte = false         # reponse ouverte : a fermer aussi apres une exception
    try
        file = open(chemin, "rb")
        webserver.content_open(200, mime)
        ouverte = true
        while (true)
            var morceau = file.readbytes(pagesGraphiques.MORCEAU)
            if (morceau == nil || size(morceau) == 0)    break    end
            webserver.content_send(morceau)
            tasmota.yield()
        end
        file.close()
        webserver.content_close()
    except .. as erreur, message
        if (file != nil)    file.close()    end
        if (ouverte)    webserver.content_close()    end
        logFonctions.log(string.format("PAGES_GRAPHIQUES_ERREUR: Envoi de %s : %s %s !", chemin, erreur, message), LOG_LEVEL_ERREUR, "serveurWeb")
    end
end
pagesGraphiques.envoieFichier = pagesGraphiques_envoieFichier

# Historique present sur la carte (globale du module, ou son etat cache une fois demarre)
def pagesGraphiques_historique()
    import global
    for nom: ["historiqueFonctions", ".historiqueFonctions"]
        if (global.contains(nom) && global.(nom) != nil)    return true    end      # une globale peut rester declaree a nil
    end
    return false
end
pagesGraphiques.historique = pagesGraphiques_historique

# f=valeurs : valeurs instantanees des chemins demandes (c=a.b,c.d), lues dans le JSON SENSOR ; null si absent ou non feuille
def pagesGraphiques_valeurs()
    import pagesGraphiques
    import webserver
    import json
    import string
    import pagesGraphiquesValidation
    var P = pagesGraphiques
    var brut = (webserver.has_arg("c") ? webserver.arg("c") : "")
    var refus = nil
    # Borne AVANT le decoupage : MAX_CHEMINS chemins de 96 octets et leurs virgules
    if (size(brut) > P.MAX_CHEMINS * 97)    refus = string.format("parametre c de %i octets (%i au plus)", size(brut), P.MAX_CHEMINS * 97)    end
    var chemins = (refus == nil ? string.split(brut, ",") : [])
    if (refus == nil && size(chemins) > P.MAX_CHEMINS)    refus = string.format("%i chemins demandes (%i au plus)", size(chemins), P.MAX_CHEMINS)    end
    for c: chemins
        if (refus == nil && !pagesGraphiquesValidation.cheminOk(c))    refus = "chemin invalide : " + c    end
    end
    if (refus != nil)
        logFonctions.log("PAGES_GRAPHIQUES_ERREUR: Valeurs refusees : " + refus + " !", LOG_LEVEL_ERREUR, "serveurWeb")
        P.repondJson(400, {"erreur": refus})
        return
    end
    var texte = tasmota.read_sensors()
    var capteurs = (type(texte) == "string" ? json.load(texte) : nil)
    var liste = []
    for c: chemins
        var v = capteurs
        for seg: string.split(c, ".")    v = (isinstance(v, map) ? v.find(seg) : nil)    end
        liste.push((isinstance(v, map) || isinstance(v, list)) ? nil : v)
    end
    # Memes filtres que le Direct de /graphiques : une mesure en erreur ou un esclave muet donne null, pas un faux 0.
    # Une exception est journalisee, les valeurs partent quand meme (comme historiqueFonctions.valeursDirectes).
    if (P.historique())
        try
            import historiqueFonctions
            for f: historiqueFonctions.filtres    f(chemins, liste)    end
        except .. as erreur, message
            logFonctions.log(string.format("PAGES_GRAPHIQUES_ERREUR: Filtre -> %s %s !", erreur, message), LOG_LEVEL_ERREUR, "serveurWeb")
        end
    end
    var valeurs = {}
    for i: 0 .. size(chemins) - 1    valeurs[chemins[i]] = liste[i]    end
    P.repondJson(200, {"t": tasmota.rtc()["utc"], "valeurs": valeurs})
end
pagesGraphiques.valeurs = pagesGraphiques_valeurs

# Page p=<id> : gabarit commun et description de la page (voir l'en-tete pour le contrat)
def pagesGraphiques_page(id)
    import pagesGraphiques
    import webserver
    import json
    import string
    var P = pagesGraphiques
    var lu = P.lisDescription()
    if (lu[0] == nil)
        P.pageMessage("Description invalide", lu[1])
        return
    end
    var page = nil
    for p: lu[0]["pages"]
        if (p["id"] == id)
            page = p
            break
        end
    end
    if (page == nil)
        logFonctions.log(string.format("PAGES_GRAPHIQUES_ERREUR: Page inconnue : %s !", str(id)[0..23]), LOG_LEVEL_ERREUR, "serveurWeb")
        P.pageMessage("Page inconnue", id)
        return
    end
    var config = {"page": page, "calculees": lu[0].find("calculees", {}), "bibliotheque": P.VERSION_BIBLIOTHEQUE,
                  "extension": P.VERSION_EXTENSION, "historique": P.historique()}
    lu = nil
    logFonctions.log(string.format("PAGES_GRAPHIQUES: Page %s demandee !", id), LOG_LEVEL_DEBUG, "serveurWeb")
    webserver.content_start(P.echappe(page["titre"]))
    webserver.content_send_style()
    webserver.content_send("<style>")
    P.envoieTexte(P.GABARIT_CSS)
    webserver.content_send("</style>")
    P.envoieTexte(P.GABARIT_HTML)
    # '</' echappe : un titre contenant '</script>' ne peut pas fermer le script
    webserver.content_send("<script>window.PAGE_GRAPHIQUES=" + string.replace(json.dump(config), "</", "<\\/") + ";</script><script>")
    for js: P.SCRIPTS
        P.envoieTexte(js)
        webserver.content_send("\n")
    end
    webserver.content_send("</script>")
    webserver.content_button(webserver.BUTTON_MAIN)
    webserver.content_stop()
end
pagesGraphiques.page = pagesGraphiques_page

# Route /pages : f = valeurs, sources ou fichier ; sinon la page p
def pagesGraphiques_route()
    import pagesGraphiques
    import webserver
    if (!webserver.check_privileged_access())    return nil    end
    var P = pagesGraphiques
    try
        var f = (webserver.has_arg("f") ? webserver.arg("f") : "")
        if (f == "valeurs")    P.valeurs()
        elif (f == "sources")    P.repondJson(200, {"historique": P.historique(), "flash": []})
        elif (f == "liquidfill.js.gz")    P.envoieFichier(P.FICHIER_LIQUIDFILL, "application/octet-stream")
        elif (f != "")    P.repondJson(404, {"erreur": "fichier inconnu"})
        else    P.page(webserver.has_arg("p") ? webserver.arg("p") : "")
        end
    except .. as erreur, message
        logFonctions.log("PAGES_GRAPHIQUES_ERREUR: Route /pages : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
    end
end
pagesGraphiques.route = pagesGraphiques_route

# ---- Driver et chargement -----------------------------------------------------------------------

class PAGES_GRAPHIQUES : Driver
    def web_add_handler()
        import webserver
        import pagesGraphiques
        pagesGraphiques.demarre()
        webserver.on("/pages", def () import pagesGraphiques pagesGraphiques.route() end, webserver.HTTP_GET)
    end
    def web_add_main_button()
        import pagesGraphiques
        pagesGraphiques.boutons()
    end
end
pagesGraphiques.PAGES_GRAPHIQUES = PAGES_GRAPHIQUES

# Appelee par import (be_module.c::module_init) avec le module : pose le driver, rend le module (mis en cache par import).
# Ne rien appeler ici qui importe pagesGraphiques (voir l'en-tete).
def pagesGraphiques_init(m)
    try
        tasmota.add_driver(m.PAGES_GRAPHIQUES())
    except .. as erreur, message
        logFonctions.log("PAGES_GRAPHIQUES_ERREUR: Driver non cree : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
    end
    return m
end
pagesGraphiques.init = pagesGraphiques_init

# Retourne le module lors de l'importation
return pagesGraphiques
