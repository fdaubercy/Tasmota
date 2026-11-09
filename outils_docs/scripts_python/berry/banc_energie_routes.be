# Banc des routes de lecture de data/fs/energieFonctions.be : f=description, f=mois, f=direct. Lancer DEPUIS LA RACINE :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_energie_routes.be <dossier_vide> [fichier_module]
# fichier_module : (temoin) une copie modifiee du module. Derniere ligne : BANC_ENERGIE_ROUTES: OK|ECHEC
import global
import sys
import string
import json
import os

var SORTIE = global._argv[1]
var SOURCE = size(global._argv) > 2 ? global._argv[2] : "data/fs/energieFonctions.be"
def ecris(chemin, texte)
    var f = open(chemin, "w")
    f.write(texte)
    f.close()
end
def lis(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end

os.mkdir(SORTIE + "/modules")
ecris(SORTIE + "/modules/webserver.be", "import global\nvar w = module('webserver')\n"
    "w.check_privileged_access = def () return global.ACCES end\n"
    "w.has_arg = def (a) return global.ARGS.contains(a) end\n"
    "w.arg = def (a) return global.ARGS[a] end\n"
    "w.content_open = def (c, m) global.CODE = c global.TYPE = m global.REPONSE = '' end\n"
    "w.content_send = def (t) if global.CASSE raise 'io_error', 'casse' end global.APPELS.push(size(t)) global.REPONSE += t end\n"
    "w.content_close = def () global.FERMES += 1 end\n"
    "w.content_start = def (t) global.PAGE = true end\n"
    "w.content_send_style = def () end\n"
    "w.content_button = def (b) end\n"
    "w.content_stop = def () end\n"
    "w.BUTTON_MAIN = 0\n"
    "return w\n")
# Le relais ne lit pas le fichier : il note le chemin (LUS) et l'envoie en entier, comme le vrai module le ferait ligne a ligne
ecris(SORTIE + "/modules/gestionFileFolder.be", "import global\nvar g = module('gestionFileFolder')\n"
    "g.readFileByLineAndContentSend = def (c) global.LUS.push(c) global.REPONSE += open(c, 'r').read() end\nreturn g\n")
ecris(SORTIE + "/modules/energieFonctions.be", string.replace(lis(SOURCE),
    'var energieFonctions = module("energieFonctions")', 'import global global.energieFonctions = module("energieFonctions")'))
sys.path().push(SORTIE + "/modules")

global.ACCES = true
global.ARGS = {}
global.CODE = 0
global.TYPE = ""
global.REPONSE = ""
global.APPELS = []
global.FERMES = 0
global.CASSE = false
global.LOGS = []
global.CAPTEURS = "{}"
global.PAGE = false
global.boolMute = true
global.diverses = {}
global.LOG_LEVEL_ERREUR = 1
global.LOG_LEVEL_INFO = 2
global.LOG_LEVEL_DEBUG = 3
global.LOG_LEVEL_DEBUG_PLUS = 4
var fauxLog = module("logFonctions")
fauxLog.log = def (m, n, c) global.LOGS.push(str(n) + " " + m) end
global.logFonctions = fauxLog
var tasmota = module("tasmota")
tasmota.yield = def () end
tasmota.read_sensors = def () return global.CAPTEURS end
global.tasmota = tasmota

global.energieFonctions = module("declaration")
import energieFonctions as E
global.energieFonctions = nil
E.DOSSIER = SORTIE + "/energie"
E.DESCRIPTION = SORTIE + "/energie_page.json"
os.mkdir(E.DOSSIER)

var echecs = 0
def verifie(nom, attendu, obtenu)
    if (str(attendu) == str(obtenu))
        print("  OK    " + nom)
    else
        echecs += 1
        print("  ECHEC " + nom + " : attendu " + str(attendu) + ", obtenu " + str(obtenu))
    end
end
def appelle(args)
    global.ARGS = args
    global.APPELS = []
    global.FERMES = 0
    global.LOGS = []
    E.route(bytes())
end

# ---- f=description
appelle({"f": "description"})
verifie("description absente : 404", 404, global.CODE)
verifie("description absente : corps JSON", "absent", json.load(global.REPONSE)["erreur"])
var DESC = '{"version":1,"elements":[{"type":"valeur"}]}'
ecris(E.DESCRIPTION, DESC)
appelle({"f": "description"})
verifie("description : 200", 200, global.CODE)
verifie("description : JSON", "application/json", global.TYPE)
verifie("description : relayee telle quelle", DESC, global.REPONSE)
var pile = "{\"x\":\""
while (size(pile) < 4096 - 2)    pile += "a"    end
pile += "\"}"                                                      # exactement 4096 octets
verifie("borne : fichier de 4096 octets", 4096, size(pile))
ecris(E.DESCRIPTION, pile)
appelle({"f": "description"})
verifie("4096 octets : accepte", 200, global.CODE)
ecris(E.DESCRIPTION, pile + " ")
appelle({"f": "description"})
verifie("4097 octets : 413", 413, global.CODE)
verifie("4097 octets : fichier jamais lu", 1, size(global.APPELS))
verifie("4097 octets : 413 journalise", true, size(global.LOGS) == 1 && string.find(global.LOGS[0], "ENERGIE") >= 0)
verifie("4097 octets : corps d'erreur", "trop gros", json.load(global.REPONSE)["erreur"])

# morceaux : une description de ~4000 octets sur UNE ligne, relayee par morceaux de 512 octets au plus
var gros = "{\"x\":\""
while (size(gros) < 4000)    gros += "abcdefghij"    end
gros += "\"}"
ecris(E.DESCRIPTION, gros)
appelle({"f": "description"})
verifie("gros : 200", 200, global.CODE)
verifie("gros : octet pour octet", gros, global.REPONSE)
var maxi = 0
for n: global.APPELS    if n > maxi    maxi = n    end    end
verifie("gros : aucun content_send au-dela de 512", true, maxi <= 512 && size(global.APPELS) > 2)
verifie("gros : fermee une fois", 1, global.FERMES)
# fichier vide : 200, corps vide
ecris(E.DESCRIPTION, "")
appelle({"f": "description"})
verifie("vide : 200", 200, global.CODE)
verifie("vide : corps vide", "", global.REPONSE)
verifie("vide : fermee", 1, global.FERMES)
# exception pendant l'envoi : content_close appele, ligne _ERREUR
ecris(E.DESCRIPTION, DESC)
global.CASSE = true
appelle({"f": "description"})
global.CASSE = false
verifie("exception : content_close appele", 1, global.FERMES)
verifie("exception : ligne _ERREUR", true, size(global.LOGS) == 1 && string.find(global.LOGS[0], "ENERGIE_ERREUR") >= 0 && global.LOGS[0][0] == "1")

# ---- f=mois
ecris(E.DOSSIER + "/mois-2026-10.json", '{"d":[1,2],"de":[3,4]}')
appelle({"f": "mois", "m": "2026-10"})
verifie("mois : 200", 200, global.CODE)
verifie("mois : relaye", '{"d":[1,2],"de":[3,4]}', global.REPONSE)
appelle({"f": "mois", "m": "2026-09"})
verifie("mois purge : 404", 404, global.CODE)
for m: ["../x", "2026-13", "2026-00", "2026-1", "26-10-01", "2026-10x", "x2026-10", "", "2026-10/../a", "20261010"]
    appelle({"f": "mois", "m": m})
    verifie("mois '" + m + "' : 400", 400, global.CODE)
    verifie("mois '" + m + "' : rien lu", 1, size(global.APPELS))
end
appelle({"f": "mois"})
verifie("mois sans m : 400", 400, global.CODE)

# ---- f=direct
global.CAPTEURS = '{"ENERGY":{"Power":123,"Current":0.5,"Factor":0.87,"Frequency":50,"Voltage":231,"ApparentPower":140,"ReactivePower":60,"Today":1.2,"Yesterday":3.4,"Total":99.5,"Period":2}}'
appelle({"f": "direct"})
var d = json.load(global.REPONSE)
verifie("direct : p i f hz", [123, 0.5, 0.87, 50], [d["p"], d["i"], d["f"], d["hz"]])
verifie("direct : champs ajoutes", [231, 140, 60, 1.2, 3.4, 99.5], [d["Voltage"], d["ApparentPower"], d["ReactivePower"], d["Today"], d["Yesterday"], d["Total"]])
verifie("direct : champ hors liste absent", false, d.contains("Period"))
global.CAPTEURS = '{"ENERGY":{"Power":5,"Voltage":230}}'
appelle({"f": "direct"})
d = json.load(global.REPONSE)
verifie("direct : present", 230, d["Voltage"])
verifie("direct : absent = pas de cle", [false, false, false], [d.contains("Today"), d.contains("Yesterday"), d.contains("Total")])
global.CAPTEURS = '{"Time":"x"}'
appelle({"f": "direct"})
verifie("direct sans ENERGY : JSON valide", nil, json.load(global.REPONSE)["p"])

# ---- acces et f inconnu
global.ACCES = false
global.CODE = 0
appelle({"f": "description"})
verifie("acces refuse : rien ouvert", 0, global.CODE)
global.ACCES = true
appelle({"f": "inconnu"})
verifie("f inconnu : page d'aujourd'hui", true, global.PAGE)

print(echecs == 0 ? "BANC_ENERGIE_ROUTES: OK" : "BANC_ENERGIE_ROUTES: ECHEC (" + str(echecs) + ")")
