# Banc de test Berry de la page de l'esclave 4 (portail de jardin), plan tasks/plans/facade-garage-portail-commande.md A8 :
# data/garage/tasmota32s3-portail-jardin-modbus/controlePortail.be (ajout a l'accueil, route /portail?f=position, contact de
# fermeture lu sur sa broche). VRAI module, VRAI persist de l'esclave 4 (auquel le banc ajoute en memoire modules.portail.facade),
# webserver et gpio bouchonnes.
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python (code de sortie, mutants) :
#     python outils_docs/scripts_python/berry/banc_portail_facade.py
# Ou directement, DEPUIS LA RACINE DU DEPOT (dossier_sources : dossier de controlePortail.be, pour un mutant) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_portail_facade.be [dossier_sources]
# Ne teste ni le vrai serveur web de Tasmota, ni le reseau, ni le dessin (banc test_volets.mjs, sonde test_volets_chrome.py).
# La derniere ligne, BANC_PORTAIL_FACADE: OK|ECHEC, est lue par l'enveloppe.
import global
import sys
import string
import json
var CARTE = "data/garage/tasmota32s3-portail-jardin-modbus"
var SOURCES = size(global._argv) > 1 ? global._argv[1] : CARTE
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/rideau")      # gpio (contact lu sur la broche)

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
var journal = []
class LogStub def log(m, n, c) journal.push([str(m), n, c]) end end
var logFonctions = LogStub()
class Driver end

class TasmotaStub
    var drivers, panne
    def init() self.drivers = [] self.panne = false end
    def cmd(c, m)
        if self.panne    raise "io_error", "panne simulee"    end
        return (c == "WebRefresh" ? {"WebRefresh": 2345} : {})
    end
    def add_driver(d) self.drivers.push(d) end
end
var tasmota = TasmotaStub()

import webserver
webserver.routes = []
webserver.acces = true
webserver.args = {}
webserver.code = nil
webserver.on = def (uri, f, methode) webserver.routes.push([uri, f]) end
webserver.check_privileged_access = def () return webserver.acces end
webserver.has_arg = def (n) return webserver.args.contains(n) end
webserver.arg = def (n) return webserver.args[n] end
webserver.content_open = def (code, t) webserver.code = code end
webserver.content_close = def () webserver.termine = true end
import gestionFileFolder
gestionFileFolder.envoyes = []
gestionFileFolder.readFileByLineAndContentSend = def (chemin) gestionFileFolder.envoyes.push(chemin) end
def razWeb() webserver.envoye = [] webserver.termine = false webserver.acces = true webserver.code = nil gestionFileFolder.envoyes = [] end

var echecs = 0
def verifie(c, nom)
    print((c ? "  ok   " : "  ECHEC ") + nom)
    if !c    echecs += 1    end
end
def nbJournal(texte, niveau)
    var n = 0
    for l: journal    if string.find(l[0], texte) > -1 && l[1] == niveau    n += 1    end    end
    return n
end
def valeurs(page)
    var debut = string.find(page, "window.VOLETS=") + 14
    return json.load(page[debut .. string.find(page, ";</script>") - 1])
end

# Le VRAI persist de l'esclave 4 ; la cle modules.portail.facade est ajoutee en memoire (le fichier du depot la recevra apres accord)
var f = open(CARTE + "/_persist.json", "r")
var persist = json.load(f.read())
f.close()
var modules = persist["modules"]
var drivers = persist["drivers"]
var serveur = persist["serveur"]
var AVANT = modules["portail"].find("facade")
modules["portail"]["facade"] = {"activation": "ON", "decor": ["portailSeul", "finition"], "capteur": 1}

# Interroge la route enregistree : rend la reponse decodee (ou nil si rien n'est envoye)
def route(args)
    razWeb()
    webserver.args = args
    var r = nil
    for x: webserver.routes    if x[0] == "/portail"    r = x[1]    end    end
    if r == nil    return nil    end
    r()
    return (size(webserver.envoye) > 0 ? json.load(webserver.envoye.concat()) : nil)
end
import gpio
var CONTACT = modules["portail"]["environnement"]["interrupteurs"]["interrupteur1"]
var PIN = CONTACT["pin"]

print("1. Chargement : driver enregistre, route posee")
import controlePortail
verifie(size(tasmota.drivers) == 1, "driver du portail enregistre")
verifie(size(webserver.routes) == 1 && webserver.routes[0][0] == "/portail", "route /portail posee des l'init")
var pilote = tasmota.drivers[0]
pilote.web_add_handler()
verifie(size(webserver.routes) == 1, "FUNC_WEB_ADD_HANDLER apres l'init : route non redeclaree")
verifie(CONTACT["pin"] == 47 && CONTACT["SwitchMode"] == 2 && CONTACT["virtuel"] == "OFF", "contact du persist : GPIO 47, SwitchMode 2 (a la masse = ON), non virtuel")

print("2. Accueil")
razWeb()
pilote.web_add_main_button()
var v = valeurs(webserver.envoye.concat())
verifie(v != nil && size(v["ouvertures"]) == 1, "window.VOLETS : une ouverture")
var o = v["ouvertures"][0]
verifie(o["type"] == "portail2" && o["source"] == "/portail?f=position" && o["tempsMontee"] == 0 && o["tempsDescente"] == 0, "un portail a deux vantaux, source = route du portail, sans duree de course (saut direct)")
verifie(v["toit"] == "unPan" && v["decor"] == ["portailSeul", "finition"] && v["rafraichissement"] == 2345, "toit unPan, decor du persist, rafraichissement = WebRefresh")
verifie(v["lectureSeule"] == true, "page en lecture seule (aucun clic de commande)")
verifie(gestionFileFolder.envoyes == ["/sd/js/volets.js"] && webserver.envoye[-1] == "</script>", "volets.js envoye, script referme")

print("3. Contact a la masse = ferme")
gpio.niveaux = {PIN: 0}
gpio.lus = []
var r = route({"f": "position"})
verifie(r != nil && r["ouverture"] == 0 && r["muet"] == false && r["capteurs"]["fermeture"] == "ON", "broche a la masse : fermeture ON, ouverture 0 %")
verifie(gpio.lus == [PIN], "broche " + str(PIN) + " lue (" + str(gpio.lus) + ")")

print("4. Contact non ferme = grand ouvert")
gpio.niveaux = {PIN: 1}
r = route({"f": "position"})
verifie(r != nil && r["ouverture"] == 100 && r["capteurs"]["fermeture"] == "OFF", "broche haute : fermeture OFF, ouverture 100 %")

print("5. Broche illisible : repli sur la cle etat, une ligne d'erreur par panne")
gpio.panne = true
CONTACT["etat"] = "ON"
journal = []
r = route({"f": "position"})
verifie(r != nil && r["ouverture"] == 0 && r["capteurs"]["fermeture"] == "ON", "panne : etat du persist (ON = ferme)")
r = route({"f": "position"})
r = route({"f": "position"})
verifie(nbJournal("CONTROLE_PORTAIL_ERREUR", 1) == 1, "une seule ligne d'erreur pour trois lectures en panne (" + str(nbJournal("CONTROLE_PORTAIL_ERREUR", 1)) + ")")
gpio.panne = false
CONTACT["etat"] = "OFF"
gpio.niveaux = {}
r = route({"f": "position"})
verifie(r != nil && r["ouverture"] == 100 && r["capteurs"]["fermeture"] == "OFF", "broche sans niveau : etat du persist (OFF = non ferme, 100 %)")
CONTACT.remove("etat")
r = route({"f": "position"})
verifie(r != nil && r["ouverture"] == nil && !r.contains("capteurs"), "ni broche ni etat : position inconnue (null), pas de cle capteurs")
CONTACT["etat"] = "OFF"

print("5b. SwitchMode 1 : broche haute = ON (sens inverse du mode 2)")
CONTACT["SwitchMode"] = 1
gpio.niveaux = {PIN: 0}
r = route({"f": "position"})
verifie(r != nil && r["capteurs"]["fermeture"] == "OFF" && r["ouverture"] == 100, "SwitchMode 1, broche a la masse : OFF (non ferme)")
gpio.niveaux = {PIN: 1}
r = route({"f": "position"})
verifie(r != nil && r["capteurs"]["fermeture"] == "ON", "SwitchMode 1, broche haute : ON")
CONTACT["SwitchMode"] = 2

print("6. Acces et arguments")
gpio.niveaux = {PIN: 0}
razWeb()
webserver.acces = false
webserver.args = {"f": "position"}
var rt = nil
for x: webserver.routes    rt = x[1]    end
rt()
verifie(size(webserver.envoye) == 0 && webserver.code == nil, "client non autorise : aucune reponse")
r = route({})
verifie(webserver.code == 400, "sans f : 400")
r = route({"f": "autre"})
verifie(webserver.code == 400, "f inconnu : 400")

print("7. Facade inactive : rien n'est pose")
modules["portail"]["facade"]["activation"] = "OFF"
webserver.routes = []
var inactif = controlePortail.CONTROLE_PORTAIL()
verifie(size(webserver.routes) == 0, "facade OFF : aucune route")
razWeb()
inactif.web_add_main_button()
verifie(size(webserver.envoye) == 0, "facade OFF : rien ajoute a l'accueil")
modules["portail"].remove("facade")
var sans = controlePortail.CONTROLE_PORTAIL()
verifie(size(webserver.routes) == 0, "bloc facade absent : aucune route")

print("8. Erreur a l'accueil et decor par defaut")
modules["portail"]["facade"] = {"activation": "ON"}
razWeb()
gestionFileFolder.readFileByLineAndContentSend = def (chemin) raise "io_error", "fichier absent" end
journal = []
var p2 = controlePortail.CONTROLE_PORTAIL()
p2.web_add_main_button()
verifie(webserver.envoye[-1] == "</script>" && nbJournal("CONTROLE_PORTAIL_ERREUR", 1) == 1, "volets.js illisible : script referme, une erreur loguee")
razWeb()
tasmota.panne = true
journal = []
p2.web_add_main_button()
verifie(size(webserver.envoye) == 0 && nbJournal("CONTROLE_PORTAIL_ERREUR", 1) == 1, "exception avant l'envoi : aucun </script> orphelin, une erreur loguee")
tasmota.panne = false
razWeb()
gestionFileFolder.readFileByLineAndContentSend = def (chemin) gestionFileFolder.envoyes.push(chemin) end
p2.web_add_main_button()
var d2 = valeurs(webserver.envoye.concat())
verifie(d2["decor"] == ["portailSeul", "finition"], "sans cle decor : defaut portailSeul + finition")
modules["portail"]["facade"] = AVANT

print(echecs == 0 ? "BANC_PORTAIL_FACADE: OK" : "BANC_PORTAIL_FACADE: ECHEC (" + str(echecs) + ")")
