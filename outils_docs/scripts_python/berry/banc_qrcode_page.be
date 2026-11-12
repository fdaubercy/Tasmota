# Banc de test Berry de la page /qrcode (2026-11-12, plan tasks/plans/etiquettes-qrcode.md A6) : data/fs/qrcodePage.be
# (driver pose a l'import seulement si /json/qrcode.json existe, bouton d'accueil, route : page, bibliotheque gz, reglage,
# etat {ip, hostname}).
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python (code de sortie, fichiers recus compares octet par octet) :
#     python outils_docs/scripts_python/berry/banc_qrcode_page.py
# Ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_qrcode_page.be <dossier_sortie> [dossier_sources]
#
# qrcodePage est COPIE dans <dossier_sortie>/modules (avec un bouchon de diversFonctions) ; webserver, path et
# gestionFileFolder sont les bouchons de bouchons_berry/graphiques. Le LittleFS de la carte est <dossier_sortie>/fs :
# le banc y pose (ou non) json/qrcode.json. La derniere ligne, BANC_QRCODE_PAGE: OK|ECHEC, donne le verdict.
import global
import sys
import string
import json
import os

if (size(global._argv) < 2)
    print("Usage : berry.exe banc_qrcode_page.be <dossier_sortie> [dossier_sources]")
    print("BANC_QRCODE_PAGE: ECHEC (argument manquant)")
    return
end
var SORTIE = global._argv[1]
var SOURCES = size(global._argv) > 2 ? global._argv[2] : "data"
var FS = SORTIE + "/fs"

def lisFichier(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end
def ecrisFichier(chemin, texte)
    var f = open(chemin, "w")
    f.write(texte)
    f.close()
end
for d: [SORTIE + "/modules", FS, FS + "/json"]
    if (!os.path.exists(d))    os.mkdir(d)    end
end
# Solidifie sur la carte, qrcodePage n'est PAS un global : declare en global le temps de l'import, puis retire (voir
# banc_cuve_page.be : un `var` de module capture par ses fonctions masquerait un import oublie)
ecrisFichier(SORTIE + "/modules/qrcodePage.be", string.replace(lisFichier(SOURCES + "/fs/qrcodePage.be"),
    'var qrcodePage = module("qrcodePage")', 'import global global.qrcodePage = module("qrcodePage")'))
var IP = "192.168.0.60"
ecrisFichier(SORTIE + "/modules/diversFonctions.be",
    "var m = module('diversFonctions')\nm.ip = '" + IP + "'\nm.ipLAN = def () return m.ip end\nreturn m\n")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/graphiques")
sys.path().push(SORTIE + "/modules")

# ---- Globaux du firmware bouchonnes -------------------------------------------------------------
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
class Driver end
var pilotes = []
class TASMOTA_BOUCHON
    var status5
    def yield() end
    def add_driver(d) pilotes.push(d) end
    def cmd(c, muet) return (c == "Status 5" ? self.status5 : nil) end
end
tasmota = TASMOTA_BOUCHON()
tasmota.status5 = {"StatusNET": {"Hostname": "tasmota-tv-salon", "IPAddress": "0.0.0.0"}}
var journal = []
class LOG_BOUCHON def log(msg, niveau, cible) journal.push([msg, niveau, cible]) end end
logFonctions = LOG_BOUCHON()

var echecs = 0
def verifie(condition, nom)
    print((condition ? "  OK     " : "  ECHEC  ") + nom)
    if (!condition)    echecs += 1    end
end

import webserver
import path
import gestionFileFolder
import diversFonctions
var routes = {}
webserver.on = def (url, f, methode) routes[url] = [f, methode] end
gestionFileFolder.racine = SOURCES       # page : gabarit, style et scripts du depot
path.racine = FS                         # existence de /json/qrcode.json : LittleFS simule

# Rend la reponse d'un appel ; renvoie le texte ecrit (ou "EXCEPTION ...")
def sert(args, appel, nomFichier)
    webserver.raz(args)
    var f = open(SORTIE + "/" + nomFichier, "wb")
    webserver.sortie = f
    var leve = nil
    try appel() except .. as e, m leve = str(e) + " : " + str(m) end
    f.close()
    return leve != nil ? "EXCEPTION " + leve : lisFichier(SORTIE + "/" + nomFichier)
end

# ---- 1. Sans /json/qrcode.json : ni driver, ni bouton, ni route -----------------------------------
print("1. Carte sans /json/qrcode.json")
import qrcodePage
var QP = qrcodePage
global.qrcodePage = nil
verifie(size(pilotes) == 0, "import sans qrcode.json : aucun driver pose")
verifie(QP.FICHIER == "/json/qrcode.json" && QP.LIB == "/sd/js/qr-code-styling.min.js.gz", "chemins du LittleFS : /json/qrcode.json et /sd/js/qr-code-styling.min.js.gz")

# ---- 2. Avec le fichier : driver, route, bouton --------------------------------------------------
print("2. Carte avec /json/qrcode.json")
var REGLAGE = '{"version": 1, "texte": "Hostname : tasmota-tv-salon · IP : 192.168.0.60", "style": {"points": "rounded"}, "image": null, "correction": "M", "ip_inscrite": "192.168.0.60", "modules": 33}\n'
ecrisFichier(FS + "/json/qrcode.json", REGLAGE)
QP.init(QP)
verifie(size(pilotes) == 1, "init avec qrcode.json : un driver pose")
var pilote = pilotes[0]
pilote.web_add_handler()
verifie(routes.contains("/qrcode") && routes["/qrcode"][1] == webserver.HTTP_GET && size(routes) == 1, "web_add_handler declare GET /qrcode, seule route")
import introspect
verifie(introspect.get(pilote, "web_add_main_button") == nil, "aucun bouton sur la page d'accueil (demande du 2026-11-12)")
var bouton = sert({}, def () pilote.web_add_management_button() end, "bouton.html")
verifie(string.find(bouton, "action='/qrcode'") > 0 && string.find(bouton, "<button>QR code</button>") > 0, "bouton « QR code » du menu Outils vers /qrcode")

# ---- 3. Acces refuse -----------------------------------------------------------------------------
print("3. Acces non privilegie")
for args: [{}, {"f": "lib.js.gz"}, {"f": "reglage"}, {"f": "etat"}]
    webserver.privilegie = false
    var s = sert(args, def () routes["/qrcode"][0]() end, "refuse.txt")
    webserver.privilegie = true
    verifie(webserver.code == nil && webserver.envois == 0 && webserver.debut == nil && s == "", "acces refuse, f=" + str(args.find("f")) + " : rien n'est envoye")
end

# ---- 4. Fichiers servis par morceaux -------------------------------------------------------------
print("4. Bibliotheque et reglage")
# L'envoi ouvre le chemin du LittleFS tel quel : on le pointe sur le disque, apres avoir verifie le chemin declare
QP.LIB = SOURCES + "/sd/js/qr-code-styling.min.js.gz"
sert({"f": "lib.js.gz"}, def () routes["/qrcode"][0]() end, "lib_recue.js.gz")
verifie(webserver.code == 200 && webserver.mime == "application/octet-stream" && webserver.envois >= 2 && webserver.ferme && webserver.debut == nil,
        "lib.js.gz : 200 application/octet-stream, " + str(webserver.envois) + " morceaux, reponse fermee, pas de page")
QP.FICHIER = FS + "/json/qrcode.json"
var recu = sert({"f": "reglage"}, def () routes["/qrcode"][0]() end, "reglage_recu.json")
verifie(webserver.code == 200 && webserver.mime == "application/json" && webserver.ferme && recu == REGLAGE, "reglage : 200 application/json, fichier tel quel")
QP.LIB = SORTIE + "/absent.js.gz"
var avant = size(journal)
var absent = sert({"f": "lib.js.gz"}, def () routes["/qrcode"][0]() end, "absent.txt")
verifie(webserver.code == 404 && webserver.ferme && string.find(absent, "absent") >= 0, "bibliotheque absente : 404 et reponse fermee")
verifie(size(journal) == avant + 1 && journal[-1][1] == LOG_LEVEL_ERREUR && string.find(journal[-1][0], "QRCODE_PAGE_ERREUR:") == 0,
        "bibliotheque absente : une ligne QRCODE_PAGE_ERREUR en erreur")
QP.LIB = "/sd/js/qr-code-styling.min.js.gz"
QP.FICHIER = "/json/qrcode.json"

# ---- 5. Etat de la carte -------------------------------------------------------------------------
print("5. Etat : IP reelle et hostname")
var etat = json.load(sert({"f": "etat"}, def () routes["/qrcode"][0]() end, "etat.json"))
verifie(webserver.code == 200 && webserver.mime == "application/json" && webserver.ferme, "etat : 200 application/json, reponse fermee")
verifie(etat != nil && etat["ip"] == IP && etat["hostname"] == "tasmota-tv-salon", "etat : IP de diversFonctions.ipLAN, hostname de Status 5 : " + str(etat))
diversFonctions.ip = ""
tasmota.status5 = nil
etat = json.load(sert({"f": "etat"}, def () routes["/qrcode"][0]() end, "etat_vide.json"))
verifie(etat != nil && etat["ip"] == "" && etat["hostname"] == "", "sans IP ni Status 5 : chaines vides, pas d'exception : " + str(etat))
diversFonctions.ip = IP
tasmota.status5 = {"StatusNET": {"Hostname": "tasmota-tv-salon"}}

# ---- 6. Page -------------------------------------------------------------------------------------
print("6. Page /qrcode")
avant = size(journal)
var page = sert({}, def () routes["/qrcode"][0]() end, "page.html")
verifie(webserver.debut == "QR code" && webserver.bouton == webserver.BUTTON_MANAGEMENT && webserver.termine && string.find(page, "EXCEPTION") != 0,
        "gabarit Tasmota : content_start, bouton de retour au menu Outils, content_stop")
var pcss = string.find(page, "#q_zone", string.find(page, "</head>"))
var phtml = string.find(page, "id='q_zone'")
var popt = string.find(page, "function optionsQR")
var pjs = string.find(page, "// Page /qrcode")
verifie(pcss > 0 && phtml > pcss && popt > phtml && pjs > popt, "ordre : qrcode.css, qrcode.html, qrcode_options.js, qrcode.js")
verifie(string.count(page, "<script") == 1 && string.count(page, "</script>") == 1, "un seul script, sans donnees de la carte dans la page")
verifie(size(journal) == avant + 1 && journal[-1][1] == LOG_LEVEL_DEBUG && journal[-1][2] == "serveurWeb" && string.find(journal[-1][0], "QRCODE_PAGE:") == 0,
        "une ligne QRCODE_PAGE en debug, cible serveurWeb")
var autre = sert({"f": "inconnu"}, def () routes["/qrcode"][0]() end, "inconnu.html")
verifie(webserver.debut == "QR code" && autre == page, "f= inconnu : la page")

print(echecs == 0 ? "BANC_QRCODE_PAGE: OK" : "BANC_QRCODE_PAGE: ECHEC (" + str(echecs) + ")")
