# Banc de la carte d'AFFICHAGE des debits (data/bureau/tasmota32s3-ecran-debits-pac) : lecture des 7 entrees analogiques
# virtuelles (centiemes de L/min, mot d'etats), « inconnu » apres 2 fenetres, total partiel, ecran HASPmota, veille,
# commande ReglageEcranDebits, driver controleEcranDebits. Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_ecran_debits.be <dossier_vide> [fichier_module]
# fichier_module : (temoin) une copie modifiee de ecranDebitsFonctions.be ("-" = l'original) ; fichier_driver : idem pour
# controleEcranDebits.be. Derniere ligne : BANC_ECRAN_DEBITS: OK|ECHEC
import global
import sys
import string
import json
import os

var SORTIE = global._argv[1]
var CARTE = "data/bureau/tasmota32s3-ecran-debits-pac/"
var SOURCE = size(global._argv) > 2 && global._argv[2] != "-" ? global._argv[2] : CARTE + "ecranDebitsFonctions.be"
var CONTROLE = size(global._argv) > 3 ? global._argv[3] : CARTE + "controleEcranDebits.be"   # temoin du driver

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
ecris(SORTIE + "/modules/ecranDebitsFonctions.be", lis(SOURCE))
ecris(SORTIE + "/modules/path.be", "import global\nvar p = module('path')\np.exists = def (f) return f == '/json/pages.jsonl' && global.PAGE_PRESENTE end\nreturn p\n")
ecris(SORTIE + "/modules/display.be", "import global\nvar d = module('display')\nd.started = def () return global.ECRAN_DEMARRE end\nd.dimmer = def (v, s) if v == nil return global.DIM end global.DIM_APPLIQUE = v end\nreturn d\n")
ecris(SORTIE + "/modules/modbusFonctions.be", "var m = module('modbusFonctions')\nm.SENTINELLE_UINT32 = 0x7FFFFFFF\nreturn m\n")
ecris(SORTIE + "/modules/haspmota.be","import global\nvar h = module('haspmota')\nh.start = def (f) global.HASP_DEMARRE = f global.creeObjets() end\nh.dimming_state = 100\nh.dimmed_panel = nil\nreturn h\n")
sys.path().push(SORTIE + "/modules")

global.JOURNAL = []
global.SAUVES = 0
global.LOG_LEVEL_ERREUR = 1
global.LOG_LEVEL_INFO = 2
global.LOG_LEVEL_DEBUG = 3
global.LOG_LEVEL_DEBUG_PLUS = 4
global.boolMute = true
var fauxLog = module("logFonctions")
fauxLog.log = def (m, n, c) global.JOURNAL.push([m, n]) end
fauxLog.actif = def (n, c) return true end
global.logFonctions = fauxLog

global.T = 1000000                       # tasmota.rtc()["local"] : secondes
global.REPONSE = nil
global.CMDS = []
global.DRIVERS = []
global.COMMANDES = {}
global.REGLES = []
global.ECRITURES = 0                     # ecritures d'attributs sur les objets de l'ecran
var fauxTasmota = module("tasmota")
fauxTasmota.rtc = def () return {"local": global.T} end
fauxTasmota.millis = def () return global.T * 1000 end
fauxTasmota.resp_cmnd = def (r) global.REPONSE = r end
fauxTasmota.cmd = def (c, m) global.CMDS.push(c) return {} end
fauxTasmota.add_driver = def (d) global.DRIVERS.push(d) end
fauxTasmota.add_cmd = def (n, f) global.COMMANDES[n] = f end
fauxTasmota.publish_rule = def (r) global.REGLES.push(r) end
fauxTasmota.defer = def (f) f() end
global.tasmota = fauxTasmota
# Objets HASPmota (pages.jsonl) : attributs gardes dans une map, comme les membres virtuels de lvh_obj
class ObjetEcran
    var attr
    def init()    self.attr = {}    end
    def setmember(k, v)    self.attr[k] = v    global.ECRITURES += 1    end
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

# ---- Verifications --------------------------------------------------------------------------------------------
var ok = true
def verifie(nom, cond)
    print((cond ? "  OK    " : "  ECHEC ") + nom)
    if (!cond)    ok = false    end
end
def erreurs()
    var n = 0
    for l: global.JOURNAL    if (l[1] == global.LOG_LEVEL_ERREUR)    n += 1    end    end
    return n
end
def fenetreInconnue()
    var n = 0
    for l: global.JOURNAL    if (l[1] == global.LOG_LEVEL_DEBUG && string.find(l[0], "ECRAN_DEBITS: fenetre ?") == 0)    n += 1    end    end
    return n
end

# Vrai persist de la carte : bloc modules.ecranDebits (7 entrees analogiques virtuelles) et bloc ModBus du maitre
var persist = json.load(lis(CARTE + "_persist.json"))
global.modules = {"ecranDebits": persist["modules"]["ecranDebits"]}
global.drivers = {"ModBus": persist["drivers"]["ModBus"]}
def ana(i)    return global.modules["ecranDebits"]["environnement"]["analogiques"]["analogique" + str(i)]    end
# Pose la valeur d'une entree comme le fait modBus_TasmotaSlaveModBus : value, etatConstate, constateA (age en s)
def pose(i, valeur, age, etat)
    var e = ana(i)
    e["value"] = valeur
    e["etatConstate"] = etat == nil ? "valide" : etat
    e["constateA"] = global.T - age
end
def poseTout(v, etats, age)
    for i: 1 .. 6    pose(i, v[i - 1], age)    end
    pose(7, etats, age)
end
def efface()
    for i: 1 .. 7    var e = ana(i)    e.remove("etatConstate")    e.remove("constateA")    e["value"] = 0    end
end
def texte(n)    return global.("p1b" + str(n)).text    end

print("--- persist de la carte")
var VIRT = "ModBus_TasmotaSlaveModBus1"
var aligne = persist["modules"]["ecranDebits"]["environnement"]["analogiques"]["activation"] == "ON"
for i: 1 .. 7
    var e = ana(i)
    aligne = aligne && e["activation"] == "ON" && e["type"] == 4704 && e["id"] == i && e["idModBus"] == i && e["virtuel"] == VIRT && e["pin"] == -1
end
verifie("analogique1-7 actives, type 4704, id et idModBus 1 a 7, virtuel de l'esclave 1", aligne)
var mb = persist["drivers"]["ModBus"]
verifie("maitre : id 0, RS485 17/18, 19200 8N1, periodeReleve 10, Serial et UDP", mb["id"] == 0 && mb["debit"] == 19200 && mb["mode"] == "8N1"
        && mb["environnement"]["pinsModBus"]["RX"]["pin"] == 17 && mb["environnement"]["pinsModBus"]["TX"]["pin"] == 18
        && mb["periodeReleve"] == 10 && mb["typeComm"]["Serial"] == "ON" && mb["typeComm"]["UDP"] == "ON")
var esc = mb["environnement"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus1"]
verifie("esclave 1 : actif, id 1, lectureGroupee ON", esc["activation"] == "ON" && esc["id"] == 1 && esc["lectureGroupee"] == "ON")
var re = persist["serveur"]["rangeExtender"]
verifie("Range Extender maitre id 0, point d'acces SERVEUR-DEBITS-PAC-GATEWAY, NAPT", re["activation"] == "ON" && re["id"] == 0
        && re["AP"]["SSID"] == "SERVEUR-DEBITS-PAC-GATEWAY" && re["AP"]["routeNAPT"] == "ON")
verifie("ecran : Option A3 GPIO 21, SPI 10/11/12/13, DC 14, XPT2046 CS 41, retroeclairage 40, reset 42",
        persist["drivers"]["ecran"]["activation"] == "ON" && persist["drivers"]["ecran"]["environnement"]["pinsEcrans"]["pinsEcran1"]["pin"] == 21
        && persist["drivers"]["ecran"]["environnement"]["pinsEcrans"]["pinsEcran7"]["pin"] == 41 && persist["drivers"]["ecran"]["environnement"]["pinsEcrans"]["pinsEcran10"]["pin"] == 42)

import ecranDebitsFonctions
print("--- lecture des entrees")
verifie("reglages par defaut du persist : fenetre 10 s, veille 5 min", ecranDebitsFonctions.fenetre() == 10 && ecranDebitsFonctions.veille() == 5)
poseTout([12345, 100, 5000, 0, 7, 999999], 4096, 0)
var d = ecranDebitsFonctions.debits(global.T)
verifie("12 345 centiemes = 123,45 L/min, 100 = 1 L/min, 7 = 0,07", d[0] > 123.449 && d[0] < 123.451 && d[1] == 1.0 && d[3] == 0.0 && d[4] > 0.069 && d[4] < 0.071)
pose(1, 12345, 0, "defaillant")
verifie("etatConstate defaillant : inconnu (nil)", ecranDebitsFonctions.debits(global.T)[0] == nil)
pose(1, 12345, 0, "inconnu")
verifie("etatConstate inconnu (chien de garde du maitre) : inconnu", ecranDebitsFonctions.debits(global.T)[0] == nil)
pose(1, 12345, 20)
verifie("mesure vieille de 2 fenetres pile (20 s) : encore valide", ecranDebitsFonctions.debits(global.T)[0] != nil)
pose(1, 12345, 21)
verifie("mesure vieille de plus de 2 fenetres (21 s) : inconnu", ecranDebitsFonctions.debits(global.T)[0] == nil)
global.modules["ecranDebits"]["fenetre"] = 30
verifie("fenetre 30 s : 21 s de vieillesse reste valide", ecranDebitsFonctions.debits(global.T)[0] != nil)
global.modules["ecranDebits"]["fenetre"] = 10
pose(1, 12345, -60)
verifie("releve date apres maintenant (persist.save d'avant le redemarrage, heure NTP pas encore la) : inconnu", ecranDebitsFonctions.debits(global.T)[0] == nil)
pose(1, 0x7FFFFFFF, 0)
verifie("sentinelle 0x7FFFFFFF : inconnu, jamais 21 474 836 L/min", ecranDebitsFonctions.debits(global.T)[0] == nil)
efface()
verifie("entrees jamais mises a jour (demarrage) : toutes inconnues", ecranDebitsFonctions.debits(global.T) == [nil, nil, nil, nil, nil, nil])
global.modules["ecranDebits"]["fenetre"] = "dix"
verifie("fenetre illisible au persist : defaut 10", ecranDebitsFonctions.fenetre() == 10)
global.modules["ecranDebits"]["fenetre"] = 10

print("--- mot d'etats")
poseTout([100, 100, 100, 100, 100, 100], 4096 + (1 << 1) + (1 << 8), 0)
var w = ecranDebitsFonctions.etats(global.T)
verifie("bit 1 = voie 2 muette, bit 8 = voie 3 imprecise, rien d'autre", w["muets"] == [false, true, false, false, false, false]
        && w["imprecis"] == [false, false, true, false, false, false])
pose(7, 4096 + 1, 21)
verifie("mot d'etats perime : non frais, aucun muet", ecranDebitsFonctions.etats(global.T)["frais"] == false && ecranDebitsFonctions.etats(global.T)["muets"] == [false, false, false, false, false, false])

print("--- ecran (HASPmota, modele B)")
efface()
global.JOURNAL = []
ecranDebitsFonctions.ecran()
verifie("demarrage sans ecran (rien jamais recu) : aucun message « fenetre ? »", fenetreInconnue() == 0 && erreurs() == 0)
poseTout([12345, 0, 50, 0, 20000, 7], 4096 + (1 << 1) + (1 << 8), 0)
ecranDebitsFonctions.ecran()
verifie("HASPmota non demarre : rien ecrit, pas d'erreur", global.p1b13 == nil && erreurs() == 0)
global.JOURNAL = []
global.T += 25
ecranDebitsFonctions.ecran()
verifie("sans ecran : les voies devenues inconnues sont quand meme signalees (« fenetre ? »)", fenetreInconnue() == 1)
poseTout([12345, 0, 50, 0, 20000, 7], 4096 + (1 << 1) + (1 << 8), 0)
global.creeObjets()
ecranDebitsFonctions.ecran()
verifie("voie 1 : 12 345 -> « 123.45 L/min », couleur normale", texte(13) == "123.45 L/min" && global.p1b13.text_color == "#E8EDF2")
verifie("barre : la plus forte (voie 5, 200 L/min) a 100, voie 1 a 62", global.p1b52.val == 100 && global.p1b12.val == 62)
verifie("voie 2 muette (bit 1) : « 0.00 L/min », rouge, « muet »", global.p1b23.text == "0.00 L/min" && global.p1b23.text_color == "#FF6B6B" && global.p1b24.text == "muet")
verifie("voie 3 imprecise (bit 8) : orange, debit et barre", global.p1b33.text_color == "#F2B84B" && global.p1b32.bg_color10 == "#F2B84B")
verifie("voie 4 a 0 : « arrêt », grise", global.p1b43.text == "0.00 L/min" && global.p1b44.text == "arrêt" && global.p1b43.text_color == "#6C7A89")
verifie("nom des departs lu du persist", global.p1b11.text == "Départ 1" && global.p1b61.text == "Départ 6")
verifie("total de 6 voies valides : somme sans « partiel »", texte(2) == "Total 324.02 L/min")
pose(6, 7, 99)
ecranDebitsFonctions.ecran()
verifie("voie 6 perimee : « inconnu » en rouge, barre vide, pas de part", global.p1b63.text == "inconnu" && global.p1b61.text_color == "#FF6B6B" && global.p1b62.val == 0 && global.p1b64.text == "")
verifie("une voie inconnue : total des autres marque « partiel »", texte(2) == "Total 323.95 L/min (partiel)")
for i: 1 .. 6    pose(i, 100, 99)    end
ecranDebitsFonctions.ecran()
verifie("toutes inconnues : « Total inconnu »", texte(2) == "Total inconnu" && global.p1b13.text == "inconnu")
verifie("page Details : etat de chaque voie et fenetre", global.p2b11.text == "1. Départ 1 : inconnu" && global.p2b90.text == "Fenêtre attendue : 10 s (inconnu au-delà de 20 s)")

print("--- ecriture seulement si ca change")
poseTout([100, 200, 300, 400, 500, 600], 4096, 0)
ecranDebitsFonctions.ecran()
global.ECRITURES = 0
ecranDebitsFonctions.ecran()
verifie("rien de change : aucune ecriture sur l'ecran", global.ECRITURES == 0)
pose(2, 250, 0)
ecranDebitsFonctions.ecran()
verifie("une voie change : l'ecran est reecrit", global.ECRITURES > 0 && global.p1b23.text == "2.50 L/min")
global.modules["ecranDebits"]["environnement"]["analogiques"]["analogique3"]["nom"] = "Salon"
ecranDebitsFonctions.ecran()
verifie("nom change au persist : reecrit", global.p1b31.text == "Salon")
global.modules["ecranDebits"]["environnement"]["analogiques"]["analogique3"]["nom"] = "Départ 3"

print("--- « fenetre ? » quand toutes les voies passent inconnues ensemble")
poseTout([100, 100, 100, 100, 100, 100], 4096, 0)
ecranDebitsFonctions.ecran()
global.JOURNAL = []
global.T += 25
ecranDebitsFonctions.ecran()
verifie("6 voies valides puis 6 perimees : un message debug « fenetre ? »", fenetreInconnue() == 1 && erreurs() == 0)
global.T += 5
ecranDebitsFonctions.ecran()
verifie("toujours perimees : pas de repetition", fenetreInconnue() == 1)
poseTout([100, 100, 100, 100, 100, 100], 4096, 0)
ecranDebitsFonctions.ecran()
global.T += 25
ecranDebitsFonctions.ecran()
verifie("valides de nouveau puis perimees : un 2e message", fenetreInconnue() == 2)
poseTout([100, 100, 100, 100, 100, 100], 4096, 0)
ecranDebitsFonctions.ecran()
global.JOURNAL = []
pose(3, 100, 99)
ecranDebitsFonctions.ecran()
verifie("une seule voie perimee : pas de message", fenetreInconnue() == 0)
global.T += 25
ecranDebitsFonctions.ecran()
verifie("la derniere voie connue se perd : toutes inconnues, un message", fenetreInconnue() == 1)

print("--- ecran : demarrage et veille")
global.JOURNAL = []
verifie("sans pages.jsonl : HASPmota non demarre, sans erreur", !ecranDebitsFonctions.demarreEcran() && global.HASP_DEMARRE == nil && erreurs() == 0)
global.PAGE_PRESENTE = true
verifie("ecran non demarre : erreur journalisee", !ecranDebitsFonctions.demarreEcran() && global.HASP_DEMARRE == nil && erreurs() == 1)
global.ECRAN_DEMARRE = true
poseTout([12345, 100, 100, 100, 100, 100], 4096, 0)
ecranDebitsFonctions.ecran()
verifie("ecran pret : HASPmota demarre sur /json/pages.jsonl", ecranDebitsFonctions.demarreEcran() && global.HASP_DEMARRE == "/json/pages.jsonl")
verifie("ecran pret : valeurs ecrites sur les objets NEUFS meme si rien n'a change", global.p1b13.text == "123.45 L/min")
import haspmota
verifie("veille de 5 min par defaut appliquee a HASPmota", haspmota.dimming_time == 5)

print("--- ReglageEcranDebits")
var r = ecranDebitsFonctions.reglageEcranDebits
global.JOURNAL = []
r("ReglageEcranDebits", 0, "fenetre 15", nil)
var rep = json.load(global.REPONSE)
verifie("fenetre 15 : ecrite au persist, sauvee, reponse coherente", ecranDebitsFonctions.fenetre() == 15 && global.SAUVES == 1
        && rep["ReglageEcranDebits"]["fenetre"] == 15 && rep["ReglageEcranDebits"]["veille"] == 5)
r("ReglageEcranDebits", 0, "fenetre 1", nil)
r("ReglageEcranDebits", 0, "fenetre 61", nil)
r("ReglageEcranDebits", 0, "fenetre abc", nil)
r("ReglageEcranDebits", 0, "fenetre 2.5", nil)
verifie("fenetre 1, 61, abc, 2.5 : refusees et journalisees, rien change", erreurs() == 4 && ecranDebitsFonctions.fenetre() == 15 && global.SAUVES == 1)
r("ReglageEcranDebits", 0, "veille 10", nil)
verifie("veille 10 : ecrite au persist et appliquee a HASPmota", global.modules["ecranDebits"]["veille"] == 10 && haspmota.dimming_time == 10)
haspmota.dimming_state = 25
global.VOILE_RETIRE = false
class FauxVoile def stop() global.VOILE_RETIRE = true end end
haspmota.dimmed_panel = FauxVoile()
global.DIM = 80
global.DIM_APPLIQUE = nil
global.REGLES = []
r("ReglageEcranDebits", 0, "veille 0", nil)
verifie("veille 0 sur ecran assombri : voile retire, luminosite rendue, evenement de sortie de veille publie",
        global.VOILE_RETIRE && haspmota.dimmed_panel == nil && haspmota.dimming_state == 100 && global.DIM_APPLIQUE == 80
        && global.REGLES == ['{"hasp":{"p0b0":{"idle":"off"}}}'])
global.JOURNAL = []
r("ReglageEcranDebits", 0, "veille 121", nil)
r("ReglageEcranDebits", 0, "veille abc", nil)
verifie("veille 121 et abc : refusees, rien change", erreurs() == 2 && global.modules["ecranDebits"]["veille"] == 0)
global.modules["ecranDebits"]["veille"] = "dix"
verifie("veille illisible au persist : defaut 5", ecranDebitsFonctions.veille() == 5)
global.modules["ecranDebits"]["veille"] = 5
var aide = ecranDebitsFonctions.aideReglageEcranDebits
verifie("aide : liste fenetre et veille, detail de chacune", size(aide(nil)) == 2 && aide(nil)[0][0] == "fenetre" && aide(nil)[1][0] == "veille"
        && aide("FENETRE") != nil && aide("veille") != nil && aide("autre") == nil)

print("--- driver controleEcranDebits")
global.modules["ecranDebits"]["fenetre"] = 10
global.JOURNAL = []
global.HASP_DEMARRE = nil
var pilote = compile(lis(CONTROLE))()
verifie("driver ajoute, commande ReglageEcranDebits declaree, HASPmota demarre", size(global.DRIVERS) == 1 && global.COMMANDES.contains("ReglageEcranDebits")
        && global.HASP_DEMARRE == "/json/pages.jsonl" && erreurs() == 0)
poseTout([54321, 100, 100, 100, 100, 100], 4096, 0)
global.JOURNAL = []
pilote.every_second()
verifie("every_second : l'ecran est rafraichi, aucun log info dans ce callback frequent", texte(13) == "543.21 L/min" && size(global.JOURNAL) == 0)
global.T += 25
pilote.every_second()
verifie("25 s sans nouvelle mesure : la voie passe a « inconnu »", texte(13) == "inconnu")

print(ok ? "BANC_ECRAN_DEBITS: OK" : "BANC_ECRAN_DEBITS: ECHEC")
