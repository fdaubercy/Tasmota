# Banc de test Berry de la facade du rideau du garage (2026-11-12, plan tasks/plans/visuel-reglage-volets.md, A10) :
# data/garage/tasmota32s3-rideau-garage-modbus/controleRideau.be (ajout a l'accueil, route /rideau?f=position, position
# lue chez le maitre P4, repli sur les fins de course). VRAI module, VRAI persist du rideau, webclient et webserver bouchonnes.
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python (code de sortie, mutants) :
#     python outils_docs/scripts_python/berry/banc_rideau_facade.py
# Ou directement, DEPUIS LA RACINE DU DEPOT (dossier_sources : dossier de controleRideau.be, pour un mutant) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_rideau_facade.be [dossier_sources]
# Ne teste ni le vrai serveur web de Tasmota, ni le reseau, ni le dessin (sonde outils_pc/test_volets_chrome.py).
# La derniere ligne, BANC_RIDEAU_FACADE: OK|ECHEC, est lue par l'enveloppe.
import global
import sys
import string
import json
var CARTE = "data/garage/tasmota32s3-rideau-garage-modbus"
var SOURCES = size(global._argv) > 1 ? global._argv[1] : CARTE
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
var journal = []
class LogStub def log(m, n, c) journal.push([str(m), n]) end end
var logFonctions = LogStub()
class Driver end

class TasmotaStub
    var drivers, ms, panne
    def init() self.drivers = [] self.ms = 100000 self.panne = false end
    def millis() return self.ms end
    def cmd(c, m)
        if self.panne    raise "io_error", "panne simulee"    end
        return (c == "WebRefresh" ? {"WebRefresh": 2345} : {})
    end
    def add_driver(d) self.drivers.push(d) end
end
var tasmota = TasmotaStub()

# Maitre simule : [code, texte] ; "exception" = GET leve une exception
var MAITRE = [-1, nil]
var requetes = []
var fermetures = 0
class webclient
    var url
    def set_timeouts(a, b) return self end
    def begin(u) self.url = u end
    def GET()
        requetes.push(self.url)
        if MAITRE[0] == "exception"    raise "io_error", "connexion coupee"    end
        return MAITRE[0]
    end
    def get_string() return MAITRE[1] end
    def close() fermetures += 1 end
end
def statut(position) return json.dump({"StatusSNS": {"Time": "x", "Shutter1": {"Position": position, "Direction": 0, "Target": position, "Tilt": 0}}}) end

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

# Le VRAI persist du rideau
var f = open(CARTE + "/_persist.json", "r")
var persist = json.load(f.read())
f.close()
var modules = persist["modules"]
var drivers = persist["drivers"]
var serveur = persist["serveur"]

# Interroge la route enregistree : rend la reponse decodee (ou nil si rien n'est envoye)
def route(args)
    razWeb()
    webserver.args = args
    var r = nil
    for x: webserver.routes    if x[0] == "/rideau"    r = x[1]    end    end
    if r == nil    return nil    end
    r()
    return (size(webserver.envoye) > 0 ? json.load(webserver.envoye.concat()) : nil)
end
def interrupteurs(e1, e2)
    var i = modules["rideau"]["environnement"]["interrupteurs"]
    i["interrupteur1"]["etat"] = e1
    i["interrupteur2"]["etat"] = e2
end

print("1. Chargement : driver enregistre, route posee (facade active dans le persist du depot)")
import controleRideau
verifie(size(tasmota.drivers) == 1, "driver du rideau enregistre")
verifie(size(webserver.routes) == 1 && webserver.routes[0][0] == "/rideau", "route /rideau posee des l'init")
var pilote = tasmota.drivers[0]
pilote.web_add_handler()
verifie(size(webserver.routes) == 1, "FUNC_WEB_ADD_HANDLER apres l'init : route non redeclaree")

print("2. Accueil")
razWeb()
pilote.web_add_main_button()
var page = webserver.envoye.concat()
var debut = string.find(page, "window.VOLETS=") + 14
var v = json.load(page[debut .. string.find(page, ";</script>") - 1])
verifie(v != nil && size(v["ouvertures"]) == 1, "window.VOLETS : une ouverture")
var o = v["ouvertures"][0]
verifie(o["type"] == "garage" && o["id"] == 1 && o["inverse"] == 1 && o["tempsMontee"] == 15 && o["tempsDescente"] == 15, "porte du garage, inverse 1, 15 s (bloc du persist)")
verifie(o["source"] == "/rideau?f=position&id=1", "source = route du rideau")
verifie(v["toit"] == "unPan" && v["rafraichissement"] == 2345, "toit unPan, rafraichissement = WebRefresh")
verifie(gestionFileFolder.envoyes == ["/sd/js/volets.js"] && webserver.envoye[-1] == "</script>", "volets.js envoye, script referme")

print("3. Position lue chez le maitre")
MAITRE = [200, statut(30)]
requetes = []
fermetures = 0
var r = route({"f": "position", "id": "1"})
verifie(r != nil && r["ouverture"] == 70 && r["muet"] == false, "curseur du P4 a 30 (inverse 1) -> 70 % d'ouverture")
verifie(requetes == ["http://192.168.0.43/cm?cmnd=Status%2010"], "Status 10 demande a ipMaitre (" + str(requetes) + ")")
verifie(fermetures == 1, "client HTTP ferme")
verifie(nbJournal("Position lue chez le maitre", LOG_LEVEL_INFO) == 1, "maitre en ligne : une ligne info")

print("4. Maitre muet : fins de course de la carte")
journal = []
MAITRE = [-1, nil]
interrupteurs("ON", "OFF")
r = route({"f": "position", "id": "1"})
verifie(r["ouverture"] == 100 && r["muet"] == true, "Switch1 (capteurOuvert) ON -> 100 %, muet")
requetes = []
interrupteurs("OFF", "ON")
verifie(route({"f": "position", "id": "1"})["ouverture"] == 0, "Switch2 (capteurFerme) ON -> 0 %")
verifie(size(requetes) == 0, "maitre muet depuis moins de 10 s : pas de nouvelle requete")
interrupteurs("OFF", "OFF")
MAITRE = ["exception", nil]
fermetures = 0
tasmota.ms += 10000
r = route({"f": "position", "id": "1"})
verifie(size(requetes) == 1, "10 s apres : nouvelle requete au maitre")
verifie(r["ouverture"] == nil && r["muet"] == true, "entre les deux (et exception du client) -> position inconnue")
verifie(fermetures == 1, "client ferme apres une exception")
verifie(nbJournal("illisible", LOG_LEVEL_ERREUR) == 1, "trois echecs de suite : UNE ligne erreur")
MAITRE = [200, json.dump({"StatusSNS": {"Time": "x"}})]
tasmota.ms += 10000
verifie(route({"f": "position", "id": "1"})["muet"] == true, "maitre sans Shutter1 -> muet")
MAITRE = [200, statut(0)]
tasmota.ms += 10000
verifie(route({"f": "position", "id": "1"})["ouverture"] == 100, "maitre revenu : curseur a 0 -> 100 %")
verifie(nbJournal("Position lue chez le maitre", LOG_LEVEL_INFO) == 1, "retour du maitre : une ligne info")

print("5. Requetes refusees")
requetes = []
route({"id": "1"})
verifie(webserver.code == 400 && size(requetes) == 0, "sans f=position : 400, maitre non interroge")
route({"f": "position", "id": "2"})
verifie(webserver.code == 400 && size(requetes) == 0, "volet inconnu : 400")
razWeb()
webserver.acces = false
webserver.args = {"f": "position", "id": "1"}
webserver.routes[0][1]()
verifie(size(webserver.envoye) == 0 && size(requetes) == 0, "acces refuse (Referer) : rien")

print("6. Exception avant l'ouverture du script : aucun </script> orphelin")
tasmota.panne = true
razWeb()
journal = []
pilote.web_add_main_button()
tasmota.panne = false
verifie(size(webserver.envoye) == 0, "rien envoye (" + str(webserver.envoye) + ")")
verifie(nbJournal("CONTROLE_RIDEAU_ERREUR: Facade", LOG_LEVEL_ERREUR) == 1, "exception loguee en erreur")

print("7. Facade inactive")
drivers["voletRoulants"]["facade"]["activation"] = "OFF"
razWeb()
pilote.web_add_main_button()
verifie(size(webserver.envoye) == 0, "accueil : rien")
route({"f": "position", "id": "1"})
verifie(webserver.code == 400, "route : 400")

print(echecs == 0 ? "BANC_RIDEAU_FACADE: OK" : "BANC_RIDEAU_FACADE: ECHEC (" + str(echecs) + ")")
