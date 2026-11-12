#- *********************************************************************************************
 * qrcodePage.be - Page /qrcode : le QR code de la carte, tel que regle dans l'outil « Etiquettes QR code » (2026-11-12)
 *
 * Plan tasks/plans/etiquettes-qrcode.md (A6), spec docs/superpowers/specs/2026-11-12-etiquettes-qrcode-design.md §7.7.
 * Charge par l'autoexec (ligne demarrage.charge(["qrcodePage"]) posee par l'outil 7970). L'import appelle init(m), qui
 * pose le driver QRCODE_PAGE SEULEMENT si /json/qrcode.json existe : sans reglage, ni bouton ni route.
 *
 * Route /qrcode (acces privilegie : Tasmota exige un Referer qui designe la carte) :
 *     /qrcode              -> la page (gabarit /sd/html/qrcode.html, style /sd/css/qrcode.css, scripts
 *                             /sd/js/qrcode_options.js, le meme que l'outil 7970, et /sd/js/qrcode.js)
 *     /qrcode?f=lib.js.gz  -> /sd/js/qr-code-styling.min.js.gz (qr-code-styling 1.9.2, gzip ; empreintes dans
 *                             outils_docs/etiquettes_qr/lib/LISEZMOI.md), decompresse par la page
 *     /qrcode?f=reglage    -> /json/qrcode.json tel quel (texte, style, image, correction, ip_inscrite, modules)
 *     /qrcode?f=etat       -> {"ip": IP reelle (diversFonctions.ipLAN), "hostname"} : la page la compare a l'IP inscrite
 * Les fichiers partent par morceaux : le reglage peut porter une image en data URI, jamais lue en entier en RAM.
 *
 * SOLIDIFIABLE (custom_berry_solidify des envs qui ont la page) : aucun etat dans le module, chaque fonction l'importe.
 * Les chemins FICHIER et LIB sont des constantes (un banc les redirige sur le disque).
********************************************************************************************* -#

#@ solidify:qrcodePage
var qrcodePage = module("qrcodePage")

qrcodePage.FICHIER = "/json/qrcode.json"
qrcodePage.LIB = "/sd/js/qr-code-styling.min.js.gz"
qrcodePage.MORCEAU = 2048           # octets lus et envoyes a la fois

# Envoie un fichier du LittleFS par morceaux ; 404 s'il est absent
def qrcodePage_envoie(chemin, mime)
    import webserver
    import path
    import string
    import qrcodePage
    if (!path.exists(chemin))
        webserver.content_open(404, "text/plain")
        webserver.content_send("Fichier absent : " + chemin)
        webserver.content_close()
        logFonctions.log(string.format("QRCODE_PAGE_ERREUR: Fichier absent du LittleFS : %s !", chemin), LOG_LEVEL_ERREUR, "serveurWeb")
        return
    end
    var fichier
    var ouverte = false             # reponse ouverte : a fermer aussi apres une exception
    try
        fichier = open(chemin, "rb")
        webserver.content_open(200, mime)
        ouverte = true
        while (true)
            var morceau = fichier.readbytes(qrcodePage.MORCEAU)
            if (morceau == nil || size(morceau) == 0)    break    end
            webserver.content_send(morceau)
            tasmota.yield()
        end
        fichier.close()
        webserver.content_close()
    except .. as erreur, message
        if (fichier != nil)    fichier.close()    end
        if (!ouverte)               # fichier present mais illisible : repondre quand meme, la page affiche l'erreur
            webserver.content_open(500, "text/plain")
            webserver.content_send("Lecture impossible : " + chemin)
        end
        webserver.content_close()
        logFonctions.log(string.format("QRCODE_PAGE_ERREUR: Envoi de %s : %s %s !", chemin, erreur, message), LOG_LEVEL_ERREUR, "serveurWeb")
    end
end
qrcodePage.envoie = qrcodePage_envoie

# {"ip", "hostname"} de la carte ; chaines vides si inconnus
def qrcodePage_etat()
    import webserver
    import json
    import diversFonctions
    var status = tasmota.cmd("Status 5", true)
    var reseau = (isinstance(status, map) ? status.find("StatusNET", {}) : {})
    var etat = {"ip": diversFonctions.ipLAN(), "hostname": str(reseau.find("Hostname", ""))}
    webserver.content_open(200, "application/json")
    webserver.content_send(json.dump(etat))
    webserver.content_close()
end
qrcodePage.etat = qrcodePage_etat

def qrcodePage_page()
    import webserver
    import gestionFileFolder
    logFonctions.log("QRCODE_PAGE: Page du QR code demandee !", LOG_LEVEL_DEBUG, "serveurWeb")
    webserver.content_start("QR code")
    webserver.content_send_style()
    webserver.content_send("<style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/css/qrcode.css")
    webserver.content_send("</style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/html/qrcode.html")
    webserver.content_send("<script>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/js/qrcode_options.js")
    gestionFileFolder.readFileByLineAndContentSend("/sd/js/qrcode.js")
    webserver.content_send("</script>")
    webserver.content_button(webserver.BUTTON_MAIN)
    webserver.content_stop()
end
qrcodePage.page = qrcodePage_page

# Route /qrcode : f = lib.js.gz, reglage ou etat ; sinon la page
def qrcodePage_route()
    import webserver
    import qrcodePage
    if (!webserver.check_privileged_access())    return nil    end
    var f = (webserver.has_arg("f") ? webserver.arg("f") : "")
    if (f == "lib.js.gz")
        qrcodePage.envoie(qrcodePage.LIB, "application/octet-stream")
    elif (f == "reglage")
        qrcodePage.envoie(qrcodePage.FICHIER, "application/json")
    elif (f == "etat")
        qrcodePage.etat()
    else
        qrcodePage.page()
    end
end
qrcodePage.route = qrcodePage_route

# ---- Driver et chargement -----------------------------------------------------------------------

class QRCODE_PAGE : Driver
    def web_add_handler()
        import webserver
        webserver.on("/qrcode", def () import qrcodePage qrcodePage.route() end, webserver.HTTP_GET)
    end
    def web_add_main_button()
        import webserver
        webserver.content_send("<p></p><form action='/qrcode' method='get'><button>QR code</button></form>")
    end
end
qrcodePage.QRCODE_PAGE = QRCODE_PAGE

# Appelee par import (be_module.c::module_init) avec le module : pose le driver si la carte a un reglage, rend le module.
# Ne rien appeler ici qui importe qrcodePage : le module n'est mis en cache qu'apres init (voir pagesGraphiques.be).
def qrcodePage_init(m)
    import path
    if (!path.exists(m.FICHIER))    return m    end
    try
        tasmota.add_driver(m.QRCODE_PAGE())
    except .. as erreur, message
        logFonctions.log("QRCODE_PAGE_ERREUR: Driver non cree : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
    end
    return m
end
qrcodePage.init = qrcodePage_init

# Retourne le module lors de l'importation
return qrcodePage
