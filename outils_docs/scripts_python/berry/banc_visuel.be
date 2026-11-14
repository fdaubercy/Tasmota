# Banc de test Berry du visuel d'accueil (2026-11-14, plan tasks/plans/atelier-visuels.md A3) : data/fs/visuelFonctions.be et
# data/fs/controleVisuel.be (driver pose seulement avec une description valide, bloc d'accueil, route /visuel : fond par
# morceaux, etat unifie, refus, 404 journalises).
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python (code de sortie, mutants) :
#     python outils_docs/scripts_python/berry/banc_visuel.py
# Ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_visuel.be <dossier_sortie> [dossier_sources]
#
# visuelFonctions est COPIE dans <dossier_sortie>/modules ; webserver et path sont les bouchons de bouchons_berry/graphiques,
# modbusFonctions et discoveryFonctions ceux de bouchons_berry/visuel (module absent tant que le banc ne pose rien).
# Le LittleFS de la carte est <dossier_sortie>/fs. Derniere ligne : BANC_VISUEL: OK|ECHEC.
import global
import sys
import string
import json
import os

if (size(global._argv) < 2)
    print("Usage : berry.exe banc_visuel.be <dossier_sortie> [dossier_sources]")
    print("BANC_VISUEL: ECHEC (argument manquant)")
    return
end
var SORTIE = global._argv[1]
var SOURCES = size(global._argv) > 2 ? global._argv[2] : "data"
var FS = SORTIE + "/fs"

def lisFichier(chemin, mode)
    var f = open(chemin, mode == nil ? "r" : mode)
    var t = (mode == "rb" ? f.readbytes() : f.read())
    f.close()
    return t
end
def ecrisFichier(chemin, contenu)
    var f = open(chemin, "wb")
    f.write(contenu)
    f.close()
end
for d: [SORTIE + "/modules", FS, FS + "/json", FS + "/sd", FS + "/sd/js", FS + "/sd/images", FS + "/sd/images/SVG", FS + "/sd/images/WEBP"]
    if (!os.path.exists(d))    os.mkdir(d)    end
end
# Solidifie sur la carte, visuelFonctions n'est PAS un global : declare en global le temps de l'import (voir banc_qrcode_page.be)
ecrisFichier(SORTIE + "/modules/visuelFonctions.be", string.replace(lisFichier(SOURCES + "/fs/visuelFonctions.be"),
    'var visuelFonctions = module("visuelFonctions")', 'import global global.visuelFonctions = module("visuelFonctions")'))
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/graphiques")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/visuel")
sys.path().push(SORTIE + "/modules")

# ---- Globaux du firmware bouchonnes -------------------------------------------------------------
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
boolMute = true
class Driver end
var pilotes = []
var APPELS = []              # commandes passees a tasmota.cmd
var MILLIS = 100000
var POWER = [true, false]
var SENSOR = '{"Time":"2026-11-14T10:00:00","ANALOG":{"A1":1.5,"A2":2.5},"Switch1":"ON","ESP32":{"Temperature":40}}'
var WIFI_UP = true
class TASMOTA_BOUCHON
    def yield() end
    def add_driver(d) pilotes.push(d) end
    def millis() return MILLIS end
    def get_power() return POWER end
    def read_sensors() return SENSOR end
    def wifi() return {"up": WIFI_UP} end
    def cmd(c, muet) APPELS.push(c) return {"RgxClients": {}} end
end
tasmota = TASMOTA_BOUCHON()
var journal = []
class LOG_BOUCHON def log(msg, niveau, cible) journal.push([msg, niveau, cible]) end end
logFonctions = LOG_BOUCHON()

var echecs = 0
def verifie(condition, nom)
    print((condition ? "  OK     " : "  ECHEC  ") + nom)
    if (!condition)    echecs += 1    end
end
def erreurs() var n = 0 for j: journal if (j[1] == LOG_LEVEL_ERREUR)    n += 1    end end return n end

import webserver
import path
var routes = {}
var ENTETES = {}
webserver.on = def (url, f, methode) routes[url] = [f, methode] end
webserver.header = def (nom, valeur) ENTETES[nom] = valeur end
path.racine = FS                         # existence des fichiers : LittleFS simule

def vide(m) var ks = [] for k: m.keys() ks.push(k) end for k: ks m.remove(k) end end
def sert(args, appel, nomFichier)
    webserver.raz(args)
    vide(ENTETES)
    var f = open(SORTIE + "/" + nomFichier, "wb")
    webserver.sortie = f
    var leve = nil
    try appel() except .. as e, m leve = str(e) + " : " + str(m) end
    f.close()
    return leve != nil ? "EXCEPTION " + leve : lisFichier(SORTIE + "/" + nomFichier)
end
def route(args, nomFichier) return sert(args, def () routes["/visuel"][0]() end, nomFichier) end

# Repart d'un module neuf : etat efface, driver et routes oublies, description (ou rien) posee dans le LittleFS
import visuelFonctions
var VF = visuelFonctions
global.visuelFonctions = nil
VF.RACINE_FOND = FS
VF.JS = FS + "/sd/js/visuel.js"      # script bouchon : le banc ne depend pas du vrai visuel.js (A4)
var JS_BANC = "(function(){window.VZ_BANC=1;})();"
ecrisFichier(VF.JS, JS_BANC)
def repart(texte)
    global._etatVisuel = nil
    pilotes.clear()
    vide(routes)
    journal.clear()
    APPELS.clear()
    if (texte == nil)
        if (os.path.exists(FS + "/json/visuel.json"))    os.remove(FS + "/json/visuel.json")    end
    else
        ecrisFichier(FS + "/json/visuel.json", texte)
    end
end
VF.FICHIER = FS + "/json/visuel.json"
# Charge controleVisuel.be (compile + execution, puis init(m) que 'import' appelle seul sur la carte) ;
# rend le driver pose, ou nil si la description n'en a pas permis
def charge_controle()
    var m = compile(lisFichier(SOURCES + "/fs/controleVisuel.be"))()
    m.init(m)
    return size(pilotes) > 0 ? pilotes[size(pilotes) - 1] : nil
end
def description(elements, extra)
    var d = {"version": 1, "fond": {"type": "svg", "largeur": 480, "hauteur": 320}, "elements": elements}
    if (extra != nil)    for k: extra.keys()    d[k] = extra[k]    end    end
    return json.dump(d)
end
var VOYANT_RELAIS = {"id": "v1", "type": "voyant", "x": 10, "y": 10, "source": {"type": "relais", "n": 1}}
var VOYANT_MESURE = {"id": "v2", "type": "voyant", "x": 20, "y": 10, "source": {"type": "mesure", "chemin": ["Switch1"], "on": "ON"}}
var VALEUR = {"id": "n1", "type": "valeur", "x": 30, "y": 10, "source": {"type": "mesure", "chemin": ["ANALOG", "A1"]}}
var L_SERIE = {"id": "l1", "type": "liaison", "x": 1, "y": 1, "x2": 9, "y2": 9, "source": {"type": "modbus_serie", "seuil_s": 90}}
var L_ESCL = {"id": "l2", "type": "liaison", "x": 1, "y": 2, "x2": 9, "y2": 9, "source": {"type": "modbus_esclave", "id": 3, "seuil_s": 90}}
var L_MAC = {"id": "l3", "type": "liaison", "x": 1, "y": 3, "x2": 9, "y2": 9, "source": {"type": "esclave", "mac": "AABBCCDDEEFF"}}
var L_WIFI = {"id": "l4", "type": "liaison", "x": 1, "y": 4, "x2": 9, "y2": 9, "source": {"type": "wifi"}}

# ---- 1. Sans /json/visuel.json : aucun driver ----------------------------------------------------
print("1. Carte sans /json/visuel.json")
repart(nil)
verifie(VF.FICHIER != nil && VF.charge() == nil && size(journal) == 0, "charge() : nil, silence")
verifie(charge_controle() == nil && size(pilotes) == 0, "controleVisuel : aucun driver pose")
verifie(VF.html() == "" && VF.etat() == nil, "html() vide, etat() nil")

# ---- 2. Description invalide : refusee, erreur, aucun driver --------------------------------------
print("2. Description invalide ou illisible")
repart('{"version": 2, "fond": {"type": "svg", "largeur": 480, "hauteur": 320}, "elements": []}')
verifie(VF.charge() == nil && erreurs() == 1 && string.find(journal[0][0], "VISUEL_ERREUR:") == 0, "version 2 : refusee, une ligne VISUEL_ERREUR")
verifie(charge_controle() == nil && size(pilotes) == 0, "invalide : aucun driver")
repart('{"version": 1, ')
verifie(VF.charge() == nil && erreurs() == 1, "JSON tronque : refuse, une erreur, pas d'exception")

# ---- 3. Cas partages avec le validateur Python (outils_docs/schemas/cas_visuel.json) --------------
print("3. Cas partages avec atelier_visuels_description.valide")
var cas = json.load(lisFichier("outils_docs/schemas/cas_visuel.json"))
var comptes = 0
for c: cas
    var seuil = false
    for e: c["erreurs"]    if (string.find(e, "au-dessus du seuil") >= 0)    seuil = true    end    end
    if (seuil)    continue    end            # poids du fond : controle de l'outil seulement
    var mien = VF.valide(c["desc"])
    var attendu = size(c["erreurs"])
    verifie((size(mien) > 0) == (attendu > 0), "cas '" + c["nom"] + "' : " + (attendu > 0 ? "refuse" : "accepte") + " comme en Python")
    comptes += 1
end
verifie(comptes >= 20, "au moins 20 cas rejoues (" + str(comptes) + ")")

# ---- 4. Description valide : driver, bloc d'accueil ------------------------------------------------
print("4. Description valide : driver et accueil")
var PIEGE = {"id": "a</script>b", "type": "voyant", "x": 5, "y": 5, "source": {"type": "relais", "n": 1}}
repart(description([VOYANT_RELAIS, PIEGE]))
verifie(charge_controle() != nil && size(pilotes) == 1, "controleVisuel : un driver pose")
var p = pilotes[0]
p.web_add_handler()
verifie(routes.contains("/visuel") && size(routes) == 1 && routes["/visuel"][1] == webserver.HTTP_GET, "web_add_handler : GET /visuel, seule route")
var accueil = sert({}, def () p.web_add_main_button() end, "accueil.html")
verifie(string.find(accueil, "<div id='vz'></div><script>window.VISUEL=") == 0, "accueil : conteneur puis window.VISUEL")
verifie(string.count(accueil, "</script>") == 2 && string.count(accueil, "<script>") == 2, "accueil : deux scripts, aucun </script> venu de la description")
verifie(string.find(accueil, "a\\u003c/script>b") > 0, "'<' echappe en \\u003c dans la description injectee")
verifie(string.find(accueil, "</script><script>" + JS_BANC + "</script>") > string.find(accueil, "window.VISUEL="), "visuel.js inline apres la description")
verifie(string.find(accueil, "EXCEPTION") != 0 && erreurs() == 0, "aucune exception ni erreur")

# ---- 5. Etat unifie : seuls les blocs demandes ---------------------------------------------------
print("5. f=etat")
global.modbusBouchon = nil
global.reseauBouchon = nil
repart(description([VOYANT_RELAIS]))
charge_controle()
pilotes[0].web_add_handler()
var avantJ = size(journal)
var e = json.load(route({"f": "etat"}, "etat1.json"))
var cles = size(e)
verifie(webserver.code == 200 && webserver.mime == "application/json" && webserver.ferme, "200 application/json, reponse fermee")
verifie(cles == 2 && e.contains("power") && e["t"] == MILLIS && e["power"] == [true, false], "relais seul : t et power, rien d'autre : " + str(cles))
verifie(erreurs() == 0, "etat : aucune erreur")
var infos = 0
for i: avantJ .. size(journal) - 1    if (journal[i][1] == LOG_LEVEL_INFO)    infos += 1    end    end
verifie(infos == 0, "etat : jamais d'info")

# Tous les types, modules ModBus et UDP ABSENTS : blocs vides, pas d'exception
repart(description([VOYANT_RELAIS, VOYANT_MESURE, VALEUR, L_SERIE, L_ESCL, L_MAC, L_WIFI]))
charge_controle()
pilotes[0].web_add_handler()
var t0 = route({"f": "etat"}, "etat2.json")
e = json.load(t0)
verifie(e != nil && string.find(t0, "EXCEPTION") != 0, "modules absents : pas d'exception")
verifie(size(e["modbus"]) == 0 && size(e["reseau"]) == 0, "modules absents : modbus {} et reseau []")
verifie(size(e["sensor"]) == 2 && e["sensor"]["Switch1"] == "ON" && size(e["sensor"]["ANALOG"]) == 1 && e["sensor"]["ANALOG"]["A1"] == 1.5, "sensor reduit aux seuls chemins demandes : " + json.dump(e["sensor"]))
verifie(e["wifi"] == true, "wifi : up de tasmota.wifi()")
WIFI_UP = false
verifie(json.load(route({"f": "etat"}, "etat2b.json"))["wifi"] == false, "wifi : down")
WIFI_UP = true

# ---- 6. Modules presents ------------------------------------------------------------------------
print("6. ModBus, UDP et reseau presents")
global.modbusBouchon = {"derniereReponseSerie": 99000, "ipsApprises": {3: {"ip": "192.168.0.7", "ms": 98000}}}
global.reseauBouchon = {"lignes": [{"mac": "AABBCCDDEEFF", "nom": "cuve", "etat": "ok", "rssi": -60, "detail": "x"}, {"mac": "112233445566", "nom": "autre", "etat": "muet", "rssi": nil, "detail": "y"}], "appels": 0}
# modbusFonctions a ete importe absent plus haut : ne reste pas en cache, l'import suivant le trouve
global._etatVisuel = nil
e = json.load(route({"f": "etat"}, "etat3.json"))
verifie(e["modbus"]["serie_ms"] == 99000 && e["modbus"]["esclaves"]["3"] == 98000, "modbus : serie_ms et esclaves par adresse : " + json.dump(e["modbus"]))
verifie(size(e["reseau"]) == 1 && e["reseau"][0]["mac"] == "AABBCCDDEEFF" && e["reseau"][0]["etat"] == "ok" && e["reseau"][0]["rssi"] == -60,
        "reseau : seule la MAC demandee, mac, etat, rssi : " + json.dump(e["reseau"]))
verifie(global.reseauBouchon["appels"] == 1, "reseau : etatReseau appele une fois")
route({"f": "etat"}, "etat3b.json")
verifie(global.reseauBouchon["appels"] == 1, "reseau : mis en cache (2e lecture sans nouvel appel)")
MILLIS += 31000
route({"f": "etat"}, "etat3c.json")
verifie(global.reseauBouchon["appels"] == 2, "reseau : relu apres 30 s")
var rgx = 0
for c: APPELS    if (c == "RgxClients")    rgx += 1    end    end
verifie(rgx == 2, "RgxClients : 2 commandes pour 3 lectures de l'etat (" + str(rgx) + ")")

# ---- 7. Relais absent, type sans source demandee ---------------------------------------------------
print("7. Element qui cite un relais absent")
repart(description([{"id": "v9", "type": "voyant", "x": 10, "y": 10, "source": {"type": "relais", "n": 9}}]))
charge_controle()
pilotes[0].web_add_handler()
var t7 = route({"f": "etat"}, "etat4.json")
e = json.load(t7)
verifie(string.find(t7, "EXCEPTION") != 0 && e != nil && size(e["power"]) == 2 && erreurs() == 0, "relais 9 sur 2 : pas d'exception, l'element est ignore cote page, power rendu tel quel")

# ---- 8. Fond --------------------------------------------------------------------------------------
print("8. f=fond")
repart(description([VOYANT_RELAIS]))
charge_controle()
pilotes[0].web_add_handler()
var avant = erreurs()
var absent = route({"f": "fond"}, "fond_absent.txt")
verifie(webserver.code == 404 && webserver.ferme && erreurs() == avant + 1 && string.find(journal[-1][0], "VISUEL_ERREUR:") == 0, "fond manquant : 404, reponse fermee, une ligne erreur")
verifie(VF.cheminFond() == nil, "cheminFond() : nil sans fond")
ecrisFichier(FS + "/visuel.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>")
verifie(VF.cheminFond() == FS + "/visuel.svg", "cheminFond() : trouve a la racine")
var svg = route({"f": "fond"}, "fond_recu.svg")
verifie(webserver.code == 200 && webserver.mime == "image/svg+xml" && ENTETES.find("Cache-Control") == "max-age=86400" && svg == "<svg xmlns='http://www.w3.org/2000/svg'/>",
        "svg : 200 image/svg+xml, Cache-Control 24 h, contenu intact")
ecrisFichier(FS + "/sd/images/SVG/visuel.svg", "<svg id='range'/>")
verifie(VF.cheminFond() == FS + "/sd/images/SVG/visuel.svg", "cheminFond() : le chemin range avant la racine")
os.remove(FS + "/sd/images/SVG/visuel.svg")
os.remove(FS + "/visuel.svg")
# WebP binaire de 5000 octets : plusieurs morceaux de 2048, octets identiques
var gros = bytes()
for i: 0 .. 4999    gros.add(i % 251, 1)    end
ecrisFichier(FS + "/sd/images/WEBP/visuel.webp", gros)
route({"f": "fond"}, "fond_recu.webp")
verifie(webserver.code == 200 && webserver.mime == "image/webp" && webserver.envois >= 3 && lisFichier(SORTIE + "/fond_recu.webp", "rb") == gros,
        "webp : 200 image/webp, " + str(webserver.envois) + " morceaux, octets identiques")
os.remove(FS + "/sd/images/WEBP/visuel.webp")
ecrisFichier(FS + "/visuel.jpg", bytes("ffd8ffe0"))
route({"f": "fond"}, "fond_recu.jpg")
verifie(webserver.mime == "image/jpeg" && lisFichier(SORTIE + "/fond_recu.jpg", "rb") == bytes("ffd8ffe0"), "jpg : image/jpeg, octets identiques")
os.remove(FS + "/visuel.jpg")

# ---- 9. Refus et actions inconnues ---------------------------------------------------------------
print("9. Acces non privilegie et f inconnu")
for args: [{}, {"f": "fond"}, {"f": "etat"}]
    webserver.privilegie = false
    var s = route(args, "refuse.txt")
    webserver.privilegie = true
    verifie(webserver.code == nil && webserver.envois == 0 && s == "", "acces refuse, f=" + str(args.find("f")) + " : rien n'est envoye")
end
route({"f": "inconnu"}, "inconnu.txt")
verifie(webserver.code == 404 && webserver.ferme, "f= inconnu : 404")
route({}, "sans_f.txt")
verifie(webserver.code == 404 && webserver.ferme, "sans f : 404")

print(echecs == 0 ? "BANC_VISUEL: OK" : "BANC_VISUEL: ECHEC (" + str(echecs) + ")")
