# Simulation d'UNE requete HTTP du rideau du garage par le VRAI module Berry (2026-11-14, plan tasks/plans/cartes-simulees.md, A2).
# Charge data/garage/tasmota32s3-rideau-garage-modbus/controleRideau.be avec le VRAI _persist.json, puis rejoue la requete.
# Lancer DEPUIS LA RACINE du depot (via outils_pc/cartes_simulees.py) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/simule_carte_rideau.be <dossier carte> <scenario.json> accueil
#     lib/libesp32/berry/berry.exe ... <dossier carte> <scenario.json> route <chemin> <id>
# Scenario (JSON) : {"maitre": {"code": 200, "position": 30} | {"code": -1}, "interrupteurs": {"1": "OFF", "2": "ON"}}
#   maitre = reponse du P4 a Status 10 (curseur 0..100, avant inversion) ; code -1 = P4 muet.
# Derniere ligne de sortie : SIMULE:<json {"code", "mime", "corps", "fichiers"}> ; "fichiers" = fichiers /sd a inserer dans la page.
import global
import sys
import string
import json
var CARTE = _argv[1]
sys.path().push(CARTE)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/rideau")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
class LogStub def log(m, n, c) end end
var logFonctions = LogStub()
class Driver end

class TasmotaStub
    var drivers
    def init() self.drivers = [] end
    def millis() return 100000 end
    def cmd(c, m) return (c == "WebRefresh" ? {"WebRefresh": 2345} : {}) end
    def add_driver(d) self.drivers.push(d) end
end
var tasmota = TasmotaStub()

def lis(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end
var SCENARIO = json.load(lis(_argv[2]))
var MAITRE = SCENARIO.find("maitre", {"code": -1})

class webclient
    def set_timeouts(a, b) return self end
    def begin(u) end
    def GET() return MAITRE.find("code", -1) end
    def get_string()
        if MAITRE.contains("brut")    return MAITRE["brut"]    end      # reponse REELLE du P4 (Status 10), lue par le Python
        return json.dump({"StatusSNS": {"Time": "x", "Shutter1": {"Position": MAITRE.find("position", 0), "Direction": 0, "Target": MAITRE.find("position", 0), "Tilt": 0}}})
    end
    def close() end
end

import webserver
webserver.routes = []
webserver.args = {}
webserver.envoye = []
webserver.code = 200
webserver.mime = "text/html"
webserver.on = def (uri, f, methode) webserver.routes.push([uri, f]) end
webserver.check_privileged_access = def () return true end
webserver.has_arg = def (n) return webserver.args.contains(n) end
webserver.arg = def (n) return webserver.args[n] end
webserver.content_open = def (code, t) webserver.code = code webserver.mime = t end
webserver.content_close = def () end
import gestionFileFolder
var FICHIERS = []
gestionFileFolder.readFileByLineAndContentSend = def (chemin) FICHIERS.push(chemin) end

var persist = json.load(lis(CARTE + "/_persist.json"))
var modules = persist["modules"]
var drivers = persist["drivers"]
var serveur = persist["serveur"]
var inter = modules["rideau"]["environnement"]["interrupteurs"]
for k: SCENARIO.find("interrupteurs", {}).keys()
    inter["interrupteur" + k]["etat"] = SCENARIO["interrupteurs"][k]
end

import controleRideau
var pilote = tasmota.drivers[0]
var mode = _argv[3]
if mode == "accueil"
    pilote.web_add_main_button()
else
    webserver.args = {"f": "position", "id": _argv[5]}
    for x: webserver.routes    if x[0] == _argv[4]    x[1]()    end    end
end
print("SIMULE:" + json.dump({"code": webserver.code, "mime": webserver.mime, "corps": webserver.envoye.concat(), "fichiers": FICHIERS}))
