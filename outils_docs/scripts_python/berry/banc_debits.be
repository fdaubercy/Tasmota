# Banc du module debits (data/bureau/tasmota32s3-serveur-debits-pac) : calcul des 6 debits, JSON du FlowRateMeter,
# commande ReglageDebits, driver controleDebits. Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_debits.be <dossier_vide> [fichier_module]
# fichier_module : (temoin) une copie modifiee de debitsFonctions.be. Derniere ligne : BANC_DEBITS: OK|ECHEC
import global
import sys
import string
import json
import os

var SORTIE = global._argv[1]
var CARTE = "data/bureau/tasmota32s3-serveur-debits-pac/"
var SOURCE = size(global._argv) > 2 ? global._argv[2] : CARTE + "debitsFonctions.be"

def lis(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end
def ecris(chemin, texte)
    var f = open(chemin, "w")
    f.write(texte)
    f.close()
end

# ---- Faux firmware --------------------------------------------------------------------------------------------
os.mkdir(SORTIE + "/modules")
ecris(SORTIE + "/modules/persist.be", "import global\nvar p = module('persist')\np.save = def (x) global.SAUVES += 1 end\nreturn p\n")
ecris(SORTIE + "/modules/diversFonctions.be", "var d = module('diversFonctions')\nd.traiteAide = def (c, p, f, v) return false end\nreturn d\n")
ecris(SORTIE + "/modules/debitsFonctions.be", lis(SOURCE))
ecris(SORTIE + "/modules/path.be", "import global\nvar p = module('path')\np.exists = def (f) return f == '/json/pages.jsonl' && global.PAGE_PRESENTE end\nreturn p\n")
ecris(SORTIE + "/modules/display.be", "import global\nvar d = module('display')\nd.started = def () return global.ECRAN_DEMARRE end\nd.dimmer = def (v, s) if v == nil return global.DIM end global.DIM_APPLIQUE = v end\nreturn d\n")
ecris(SORTIE + "/modules/haspmota.be", "import global\nvar h = module('haspmota')\nh.start = def (f) global.HASP_DEMARRE = f global.creeObjets() end\nh.dimming_state = 100\nh.dimmed_panel = nil\nreturn h\n")
sys.path().push(SORTIE + "/modules")

global.JOURNAL = []
global.SAUVES = 0
global.LOG_LEVEL_ERREUR = 1
global.LOG_LEVEL_INFO = 2
global.LOG_LEVEL_DEBUG = 3
global.LOG_LEVEL_DEBUG_PLUS = 4
global.boolMute = true
global.modules = {"debits": {"activation": "ON"}}
var fauxLog = module("logFonctions")
fauxLog.log = def (m, n, c) global.JOURNAL.push([m, n]) end
fauxLog.actif = def (n, c) return true end
global.logFonctions = fauxLog

global.MS = 0
global.CAPTEURS = nil
global.COMPTEURS = [nil, nil, nil, nil]
global.REPONSE = nil
global.CMDS = []
global.WEB = []
global.DRIVERS = []
global.COMMANDES = {}
var fauxTasmota = module("tasmota")
fauxTasmota.millis = def () return global.MS end
fauxTasmota.read_sensors = def () return global.CAPTEURS end
fauxTasmota.resp_cmnd = def (r) global.REPONSE = r end
fauxTasmota.cmd = def (c, m) global.CMDS.push(c) return {} end
fauxTasmota.web_send = def (t) global.WEB.push(t) end
fauxTasmota.response_append = def (t) global.REPONSE = t end
fauxTasmota.add_driver = def (d) global.DRIVERS.push(d) end
fauxTasmota.add_cmd = def (n, f) global.COMMANDES[n] = f end
fauxTasmota.publish_rule = def (r) global.REGLES.push(r) end
global.REGLES = []
global.tasmota = fauxTasmota
# Objets HASPmota (pages.jsonl) : attributs gardes dans une map, comme les membres virtuels de lvh_obj
class ObjetEcran
    var attr
    def init()    self.attr = {}    end
    def setmember(k, v)    self.attr[k] = v    end
    def member(k)    return self.attr.find(k)    end
end
global.PAGE_PRESENTE = false
global.ECRAN_DEMARRE = false
global.HASP_DEMARRE = nil
def creeObjets()
    global.p1b2 = ObjetEcran()
    global.p2b90 = ObjetEcran()
    for n: 1 .. 6
        for k: 1 .. 4    global.("p1b" + str(10 * n + k)) = ObjetEcran()    end
        global.("p2b" + str(10 * n + 1)) = ObjetEcran()
    end
end
global.creeObjets = creeObjets
class Driver end
global.Driver = Driver
var fauxGpio = module("gpio")
fauxGpio.counter_read = def (i) return global.COMPTEURS[i] end
global.gpio = fauxGpio

# ---- Verifications --------------------------------------------------------------------------------------------
var ok = true
def verifie(nom, cond)
    print((cond ? "  OK    " : "  ECHEC ") + nom)
    if (!cond)    ok = false    end
end
def proche(a, b)    return a != nil && b != nil && (a - b < 0.001 && b - a < 0.001)    end
def erreurs()
    var n = 0
    for l: global.JOURNAL    if (l[1] == global.LOG_LEVEL_ERREUR)    n += 1    end    end
    return n
end

import debitsFonctions
var K = [11.0, 11.0, 11.0, 11.0, 11.0, 11.0]

print("--- calcul")
# Rate 91,6667 a calibrage 1000 = 11 Hz = 1 L/min (K 11) ; 110 impulsions en 10 s = 11 Hz = 1 L/min
var d = debitsFonctions.calcule([91.6667, 0], [0, 100, nil, 500], [110, 100, nil, 400], 10000, K)
verifie("voie 1 (FlowRateMeter) : 1 L/min", proche(d[0], 1.0))
verifie("voie 2 a l'arret : 0", proche(d[1], 0.0))
verifie("voie 3 (compteur) : 1 L/min", proche(d[2], 1.0))
verifie("voie 4 sans impulsion : 0", proche(d[3], 0.0))
verifie("voie 5 compteur non configure : nil", d[4] == nil)
verifie("voie 6 compteur remis a zero : nil", d[5] == nil)
verifie("total des voies mesurees : 2", proche(debitsFonctions.total(d), 2.0))
verifie("total sans mesure : nil", debitsFonctions.total([nil, nil]) == nil)
d = debitsFonctions.calcule(45.8333, nil, [nil, nil, nil, nil], 0, K)
verifie("Rate seul (une voie configuree) : voie 1 a 0,5 L/min", proche(d[0], 0.5) && d[1] == nil)
d = debitsFonctions.calcule(nil, [0, 0, 0, 0], [220, 0, 0, 0], 10000, [11.0, 11.0, 22.0, 11.0, 11.0, 11.0])
verifie("K propre a la voie 3 (22) : 1 L/min", proche(d[2], 1.0) && d[0] == nil)

print("--- JSON des capteurs")
verifie("cle francaise Débit", debitsFonctions.rates('{"Débit":{"Rate":[91.67,0],"Unit":"l/min"}}')[0] == 91.67)
verifie("cle anglaise Flowrate", debitsFonctions.rates('{"Flowrate":{"Rate":3.5}}') == 3.5)
verifie("FlowRateMeter absent : nil", debitsFonctions.rates('{"ESP32":{"Temperature":40}}') == nil)
verifie("texte nil : nil", debitsFonctions.rates(nil) == nil)

print("--- mesure")
global.CAPTEURS = '{"Débit":{"Rate":[183.3333,91.6667]}}'
global.COMPTEURS = [1000, 2000, 3000, 4000]
global.MS = 50000
debitsFonctions.mesure()
verifie("1re mesure : voies 1-2 lues", proche(debitsFonctions.debits[0], 2.0) && proche(debitsFonctions.debits[1], 1.0))
verifie("1re mesure : voies 3-6 sans mesure", debitsFonctions.debits[2] == nil && debitsFonctions.debits[5] == nil)
global.COMPTEURS = [1220, 2110, 3330, 4000]
global.MS = 60000
debitsFonctions.mesure()
verifie("2e mesure : voies 3, 4, 5, 6 = 2, 1, 3, 0 L/min", proche(debitsFonctions.debits[2], 2.0) && proche(debitsFonctions.debits[3], 1.0)
        && proche(debitsFonctions.debits[4], 3.0) && proche(debitsFonctions.debits[5], 0.0))
var j = json.load("{" + debitsFonctions.json()[1..] + "}")
verifie("JSON SENSOR : bloc DEBITS, D3 et Total", j != nil && j["DEBITS"]["D3"] == 2 && j["DEBITS"]["Total"] == 9)
debitsFonctions.debits = [1.0, nil, 0.5, 0, 0, 0]
j = json.load("{" + debitsFonctions.json()[1..] + "}")
verifie("JSON SENSOR : voie sans mesure = null", j != nil && j["DEBITS"].contains("D2") && j["DEBITS"]["D2"] == nil)
var w = debitsFonctions.lignesWeb()
verifie("page : 7 lignes (6 departs + total)", size(w) == 7)
verifie("page : nom par defaut, debit et part", string.find(w[0], "Départ 1") >= 0 && string.find(w[0], "1.00 L/min") >= 0 && string.find(w[0], "67 %") >= 0)
verifie("page : moins de 1 L/min signale", string.find(w[2], "imprécis") >= 0)
verifie("page : voie sans mesure", string.find(w[1], "-,--") >= 0)
verifie("JSON SENSOR : voie 3 a 0,5 L/min signalee imprecise", j["DEBITS"]["Imprecis"] == [3])

print("--- ecran (HASPmota, modele B)")
var e = debitsFonctions.etatVoie(2.35, 7.9, 3.1)
verifie("voie normale : debit, part, barre relative a la plus forte", e == ["2.35 L/min", "30 %", 76, "normal"])
verifie("voie a 0,65 L/min : imprecise", debitsFonctions.etatVoie(0.65, 7.9, 3.1)[3] == "imprecis")
verifie("voie a 0 : arret, barre vide", debitsFonctions.etatVoie(0.0, 7.9, 3.1) == ["0.00 L/min", "arrêt", 0, "arret"])
verifie("voie sans mesure : absente", debitsFonctions.etatVoie(nil, 7.9, 3.1)[3] == "absent")
global.modules["debits"] = {"activation": "ON"}
debitsFonctions.debits = [2.35, 1.8, 0.65, 3.1, 0, nil]
debitsFonctions.ecran()
verifie("HASPmota non demarre : rien ecrit, pas d'erreur", global.p1b13 == nil)
global.creeObjets()
debitsFonctions.ecran()
verifie("ecran : debit et couleur de la voie 1", global.p1b13.text == "2.35 L/min" && global.p1b13.text_color == "#E8EDF2")
verifie("ecran : barre de la voie 4 (la plus forte) a 100", global.p1b42.val == 100 && global.p1b12.val == 76)
verifie("ecran : voie 3 imprecise en orange (debit et barre)", global.p1b33.text_color == "#F2B84B" && global.p1b32.bg_color10 == "#F2B84B")
verifie("ecran : voie 6 absente en rouge", global.p1b63.text == "-,--" && global.p1b61.text_color == "#FF6B6B")
verifie("ecran : total et nom par defaut", global.p1b2.text == "Total 7.90 L/min" && global.p1b51.text == "Départ 5")
verifie("ecran : page Details (K, fenetre)", global.p2b11.text == "1. Départ 1 : K 11.0 Hz par L/min" && global.p2b90.text == "Mesure toutes les 10 s")
global.MS = 70000
global.p1b13.text = nil
debitsFonctions.mesure()
verifie("mesure : ecran reecrit", global.p1b13.text != nil)
global.JOURNAL = []
verifie("sans pages.jsonl : HASPmota non demarre, sans erreur", !debitsFonctions.demarreEcran() && global.HASP_DEMARRE == nil && erreurs() == 0)
global.PAGE_PRESENTE = true
verifie("ecran non demarre : erreur journalisee", !debitsFonctions.demarreEcran() && global.HASP_DEMARRE == nil && erreurs() == 1)
global.ECRAN_DEMARRE = true
verifie("ecran pret : HASPmota demarre sur /json/pages.jsonl", debitsFonctions.demarreEcran() && global.HASP_DEMARRE == "/json/pages.jsonl")
import haspmota
verifie("ecran pret : veille de 5 min par defaut appliquee a HASPmota", haspmota.dimming_time == 5)

print("--- capteur muet (10 min a 0 L/min)")
debitsFonctions.zero = [nil, nil, nil, nil, nil, nil]
debitsFonctions.muets = [false, false, false, false, false, false]
global.JOURNAL = []
var dm = [0.0, 1.0, nil, 0.0, 0.0, 0.0]
debitsFonctions.suitMuets(dm, 0)
debitsFonctions.suitMuets(dm, 599999)
verifie("0 L/min depuis 9 min 59 s : pas muet", debitsFonctions.muets == [false, false, false, false, false, false] && erreurs() == 0)
debitsFonctions.suitMuets(dm, 600000)
verifie("0 L/min depuis 10 min : voies 1, 4, 5, 6 muettes, voie 2 (1 L/min) et 3 (sans mesure) non", debitsFonctions.muets == [true, false, false, true, true, true])
verifie("une erreur par voie au passage", erreurs() == 4)
debitsFonctions.suitMuets(dm, 700000)
verifie("toujours muettes : pas de nouvelle erreur", erreurs() == 4 && debitsFonctions.muets[0])
debitsFonctions.suitMuets([0.5, 1.0, nil, 0.0, 0.0, 0.0], 710000)
verifie("une impulsion revient : voie 1 de nouveau normale", !debitsFonctions.muets[0] && debitsFonctions.muets[3])
debitsFonctions.suitMuets(dm, 720000)
debitsFonctions.suitMuets(dm, 1319999)
verifie("nouvelle serie a 0 : le compte repart de zero", !debitsFonctions.muets[0])
debitsFonctions.suitMuets(dm, 1320000)
verifie("nouvelle serie a 0 depuis 10 min : voie 1 muette, une erreur de plus", debitsFonctions.muets[0] && erreurs() == 5)
debitsFonctions.debits = dm
var jm = json.load("{" + debitsFonctions.json()[1..] + "}")
verifie("JSON SENSOR : Muets = [1, 4, 5, 6]", jm["DEBITS"]["Muets"] == [1, 4, 5, 6])
verifie("page : voie muette signalee", string.find(debitsFonctions.lignesWeb()[0], "capteur muet") >= 0 && string.find(debitsFonctions.lignesWeb()[1], "muet") < 0)
debitsFonctions.ecran()
verifie("ecran : voie muette en rouge, « muet »", global.p1b13.text_color == "#FF6B6B" && global.p1b14.text == "muet" && global.p1b23.text_color == "#E8EDF2")
global.modules["debits"]["muet"] = 1
debitsFonctions.zero = [nil, nil, nil, nil, nil, nil]
debitsFonctions.muets = [false, false, false, false, false, false]
debitsFonctions.suitMuets(dm, 0)
debitsFonctions.suitMuets(dm, 60000)
verifie("persist muet = 1 : muette apres 1 min", debitsFonctions.muets[0])
for faux: [0, -5, "dix"]
    global.modules["debits"]["muet"] = faux
    debitsFonctions.zero = [nil, nil, nil, nil, nil, nil]
    debitsFonctions.muets = [false, false, false, false, false, false]
    debitsFonctions.suitMuets(dm, 0)
    debitsFonctions.suitMuets(dm, 60000)
    verifie("persist muet = " + str(faux) + " : ignore, defaut 10 min", !debitsFonctions.muets[0])
end
global.modules["debits"].remove("muet")
debitsFonctions.zero = [nil, nil, nil, nil, nil, nil]
debitsFonctions.muets = [false, false, false, false, false, false]

print("--- ReglageDebits")
# Bloc debits du vrai persist de la carte : nom et K dans environnement.debitmetres et compteurs
global.modules["debits"] = json.load(lis(CARTE + "_persist.json"))["modules"]["debits"]
def entree(i)
    var env = global.modules["debits"]["environnement"]
    return i < 2 ? env["debitmetres"]["debitmetre" + str(i + 1)] : env["compteurs"]["compteur" + str(i - 1)]
end
verifie("persist : noms et K des 6 voies lus", debitsFonctions.voie(0)["nom"] == "Debit 1" && debitsFonctions.voie(5)["nom"] == "Debit 6"
        && proche(debitsFonctions.voie(2)["k"], 11.0))
var r = debitsFonctions.reglageDebits
global.JOURNAL = []
r("ReglageDebits", 0, "k 3 11.4", nil)
verifie("k 3 11.4 : ecrit dans compteur1 et sauve", proche(entree(2)["k"], 11.4) && global.SAUVES == 1)
verifie("k 3 : les autres voies gardent leur K", proche(entree(0)["k"], 11.0) && proche(entree(3)["k"], 11.0))
r("ReglageDebits", 0, "k 7 5", nil)
r("ReglageDebits", 0, "k 1 abc", nil)
r("ReglageDebits", 0, "k 0 11", nil)
r("ReglageDebits", 0, "k 1 0,05", nil)
verifie("voie 7, K non numerique, voie 0, K 0,05 : refuses et journalises", erreurs() == 4 && global.SAUVES == 1)
r("ReglageDebits", 0, "nom 2 Salle de bain", nil)
verifie("nom avec espaces, ecrit dans debitmetre2", entree(1)["nom"] == "Salle de bain" && proche(entree(2)["k"], 11.4))
r("ReglageDebits", 0, "k 4 11,6", nil)
verifie("k 4 11,6 : virgule francaise lue 11.6", proche(entree(3)["k"], 11.6))
r("ReglageDebits", 0, "k  5   12", nil)
verifie("espaces doubles : k 5 12 accepte", proche(entree(4)["k"], 12.0) && erreurs() == 4)
r("ReglageDebits", 0, "k 6 3abc", nil)
r("ReglageDebits", 0, "k 2.5 11", nil)
verifie("K '3abc' et voie 2.5 refuses", erreurs() == 6 && proche(entree(5)["k"], 11.0))
r("ReglageDebits", 0, "nom 6 <b>A&B{m}", nil)
verifie("nom echappe dans la page", string.find(debitsFonctions.lignesWeb()[5], "&lt;b>A&amp;B&#123;m}") >= 0)
global.modules["debits"]["environnement"]["compteurs"].remove("compteur4")
var sauves = global.SAUVES
r("ReglageDebits", 0, "k 6 11", nil)
verifie("voie sans entree au persist : refusee, rien sauve", erreurs() == 7 && global.SAUVES == sauves && debitsFonctions.voie(5)["nom"] == "Départ 6")
global.JOURNAL = []
r("ReglageDebits", 0, "fenetre 1", nil)
verifie("fenetre 1 refusee", erreurs() == 1 && debitsFonctions.fenetre() == 10)
r("ReglageDebits", 0, "fenetre 15", nil)
var rep = json.load(global.REPONSE)
verifie("fenetre 15 : ecrite, reponse coherente", debitsFonctions.fenetre() == 15 && rep["ReglageDebits"]["fenetre"] == 15
        && rep["ReglageDebits"]["voies"][1]["nom"] == "Salle de bain")
global.JOURNAL = []
r("ReglageDebits", 0, "veille 10", nil)
verifie("veille 10 : ecrite au persist et appliquee a HASPmota", global.modules["debits"]["veille"] == 10 && haspmota.dimming_time == 10)
haspmota.dimming_state = 25
global.VOILE_RETIRE = false
class FauxVoile def stop() global.VOILE_RETIRE = true end end
haspmota.dimmed_panel = FauxVoile()
global.DIM = 80
global.DIM_APPLIQUE = nil
r("ReglageDebits", 0, "veille 0", nil)
verifie("veille 0 (jamais) acceptee", haspmota.dimming_time == 0 && erreurs() == 0)
verifie("veille 0 sur ecran assombri : voile retire, luminosite des reglages rendue",
        global.VOILE_RETIRE && haspmota.dimmed_panel == nil && haspmota.dimming_state == 100 && global.DIM_APPLIQUE == 80)
r("ReglageDebits", 0, "veille 121", nil)
r("ReglageDebits", 0, "veille abc", nil)
r("ReglageDebits", 0, "veille 2.5", nil)
verifie("veille 121, abc, 2.5 : refusees, rien change", erreurs() == 3 && global.modules["debits"]["veille"] == 0)
rep = json.load(global.REPONSE)
verifie("reponse : veille", rep["ReglageDebits"]["veille"] == 0)
global.modules["debits"]["veille"] = "dix"
verifie("veille illisible au persist : defaut 5", debitsFonctions.veille() == 5)
global.modules["debits"].remove("veille")
verifie("reponse : etat muet des voies et duree de l'ecran (ecran_ms)", rep["ReglageDebits"].contains("muets") && rep["ReglageDebits"].contains("ecran_ms"))
verifie("mesure : duree d'ecriture de l'ecran relevee", type(debitsFonctions.ecranMs) == "int")

print("--- driver controleDebits")
global.CMDS = []
var pilote = compile(lis(CARTE + "controleDebits.be"))()
verifie("driver enregistre et commande ajoutee", size(global.DRIVERS) == 1 && global.COMMANDES.contains("ReglageDebits"))
verifie("calibrage du FlowRateMeter neutralise", global.CMDS == ["Sensor96 0 0", "Sensor96 1 1000", "Sensor96 2 1000"])
global.COMPTEURS = [0, 0, 0, 0]
global.MS = 100000
debitsFonctions.releve = nil
for i: 1 .. 14    pilote.every_second()    end
verifie("pas de mesure avant la fenetre (15 s)", debitsFonctions.releve == nil)
pilote.every_second()
verifie("mesure a la 15e seconde", debitsFonctions.releve != nil && debitsFonctions.releve["t"] == 100000)
global.CAPTEURS = "pas du json"
global.MS = 115000
for i: 1 .. 15    pilote.every_second()    end
verifie("JSON illisible : mesure faite, voies 1-2 sans mesure", debitsFonctions.releve["t"] == 115000 && debitsFonctions.debits[0] == nil
        && proche(debitsFonctions.debits[2], 0.0))

print(ok ? "BANC_DEBITS: OK" : "BANC_DEBITS: ECHEC")
