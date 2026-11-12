# Banc de la carte d'AFFICHAGE des debits (data/bureau/tasmota32s3-ecran-debits-pac) : lecture des 7 entrees analogiques
# virtuelles (centiemes de L/min, mot d'etats), « inconnu » apres 2 fenetres, modele d'ecran, historique de la courbe,
# veille et luminosite par l'expandeur I2C 0x24 (simule), commande ReglageEcranDebits, interface HASPmota sur les objets
# de pages.jsonl (simules), driver controleEcranDebits et choix de l'interface. Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_ecran_debits.be <dossier_vide> [module] [driver] [interface] [generique]
# module, driver, interface, generique : (temoins) une copie modifiee de ecranDebitsFonctions.be, controleEcranDebits.be,
# ecranHaspmota.be, ecranFonctions.be
# ("-" = l'original). Derniere ligne : BANC_ECRAN_DEBITS: OK|ECHEC
import global
import sys
import string
import json
import os

var SORTIE = global._argv[1]
var CARTE = "data/bureau/tasmota32s3-ecran-debits-pac/"
def argument(i, defaut)    return size(global._argv) > i && global._argv[i] != "-" ? global._argv[i] : defaut    end
var SOURCE = argument(2, CARTE + "ecranDebitsFonctions.be")
var CONTROLE = argument(3, CARTE + "controleEcranDebits.be")
var INTERFACE = argument(4, CARTE + "ecranHaspmota.be")
var GENERIQUE = argument(5, "data/fs/ecranFonctions.be")

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
ecris(SORTIE + "/modules/ecranHaspmota.be", lis(INTERFACE))
ecris(SORTIE + "/modules/ecranFonctions.be", lis(GENERIQUE))
# demarrage.importeUn : meme code que data/fs/demarrage.be (import par le nom)
ecris(SORTIE + "/modules/demarrage.be", "var d = module('demarrage')\nd.importeUn = def (nom) return compile('return (def () import ' + nom + ' as _m return _m end)()')() end\nreturn d\n")
ecris(SORTIE + "/modules/ecranLvgl.be", "import global\nvar m = module('ecranLvgl')\nm.demarre = def () global.LVGL_DEMARRE = true return true end\nm.affiche = def (x) global.LVGL_AFFICHE = x end\nreturn m\n")
# path : exists, listdir("/") (fichiers a la racine), mkdir refuse si le parent manque ou si le dossier existe (comme LittleFS)
ecris(SORTIE + "/modules/path.be", "import global\nimport string\nvar p = module('path')\np.exists = def (f) return global.FICHIERS.find(f) != nil end\n" +
      "p.listdir = def (d) var r = [] for f: global.FICHIERS if string.find(f, '/', 1) < 0 r.push(f[1 ..]) end end return r end\n" +
      "p.mkdir = def (d) var n = string.split(d, '/')[-1] var parent = d[0 .. -(size(n) + 2)]\n" +
      "  if global.DOSSIERS.find(d) != nil || (size(parent) > 0 && global.DOSSIERS.find(parent) == nil) return false end global.DOSSIERS.push(d) return true end\nreturn p\n")
# gestionFileFolder.deplaceFichier : refuse (false, original garde) si la source manque ou si le dossier de destination n'existe pas
ecris(SORTIE + "/modules/gestionFileFolder.be", "import global\nimport string\nvar g = module('gestionFileFolder')\n" +
      "g.deplaceFichier = def (s, d) var i = global.FICHIERS.find(s) var n = string.split(d, '/')[-1]\n" +
      "  if i == nil || global.DOSSIERS.find(d[0 .. -(size(n) + 2)]) == nil return false end global.FICHIERS[i] = d global.DEPLACES.push([s, d]) return true end\nreturn g\n")
ecris(SORTIE + "/modules/display.be", "import global\nvar d = module('display')\nd.started = def () return global.ECRAN_DEMARRE end\nreturn d\n")
ecris(SORTIE + "/modules/modbusFonctions.be", "var m = module('modbusFonctions')\nm.SENTINELLE_UINT32 = 0x7FFFFFFF\nreturn m\n")
ecris(SORTIE + "/modules/haspmota.be", "import global\nvar h = module('haspmota')\nh.start = def (f) global.HASP_DEMARRE = f global.creeObjets() end\nh.lvh_page_cur_idx = 1\nreturn h\n")
ecris(SORTIE + "/modules/lv.be", "import global\nvar l = module('lv')\nl.CHART_AXIS_PRIMARY_Y = 1\nl.CHART_POINT_NONE = 0x7FFFFFFF\n" +
      "l.PART_INDICATOR = 0x20000\nl.PART_ITEMS = 0x50000\nl.disp = def () return global.FauxDisp() end\nl.layer_sys = def () return 'sys' end\n" +
      "l.get_hor_res = def () return 1024 end\nl.get_ver_res = def () return 600 end\nl.obj = def (p) return global.FauxVoile(p) end\nreturn l\n")
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

global.T = 1000000                       # tasmota.rtc()["local"] : secondes ; millis = T * 1000
global.REPONSE = nil
global.DRIVERS = []
global.COMMANDES = {}
global.TIMERS = {}                       # tasmota.set_timer : identifiant -> [delai ms, fonction]
global.REGLES = []                       # [declencheur, fonction, id] de tasmota.add_rule
global.I2C = []                          # ecritures sur l'expandeur : [adresse, registre, valeur]
global.EXPANDEUR = true                  # false : wire_scan(0x24) rend nil
global.ACK = true                        # false : write rend false (pas d'ACK)
global.INACTIF = 0                       # ms sans toucher l'ecran (lv.disp().get_inactive_time())
global.FICHIERS = []                     # fichiers presents sur le FS (path.exists)
global.DOSSIERS = []                     # dossiers presents (path.mkdir) ; "/sd" = carte SD montee
global.DEPLACES = []                     # [source, destination] de gestionFileFolder.deplaceFichier
class FauxBus
    def write(a, r, v, n)    global.I2C.push([a, r, v])    return global.ACK    end
end
var fauxTasmota = module("tasmota")
fauxTasmota.rtc = def () return {"local": global.T} end
fauxTasmota.millis = def () return global.T * 1000 end
fauxTasmota.resp_cmnd = def (r) global.REPONSE = r end
fauxTasmota.add_driver = def (d) global.DRIVERS.push(d) end
fauxTasmota.add_cmd = def (n, f) global.COMMANDES[n] = f end
fauxTasmota.add_rule = def (p, f, id) global.REGLES.push([p, f, id]) end
# comme tasmota_class.be::set_timer, un second appel du meme identifiant EMPILE un timer (cle id, id+"+", ...) ; remove_timer les retire tous
fauxTasmota.set_timer = def (ms, f, id) var k = id  while global.TIMERS.contains(k)  k = str(k) + "+"  end  global.TIMERS[k] = [ms, f] end
fauxTasmota.remove_timer = def (id) var k = id  while global.TIMERS.contains(k)  global.TIMERS.remove(k)  k = str(k) + "+"  end end
fauxTasmota.wire_scan = def (a) return (a == 0x24 && global.EXPANDEUR) ? FauxBus() : nil end
global.tasmota = fauxTasmota
class FauxDisp    def get_inactive_time()    return global.INACTIF    end    end
global.FauxDisp = FauxDisp
global.VOILES = []
class FauxVoile
    var parent, efface, clic
    def init(p)    self.parent = p    self.efface = false    global.VOILES.push(self)    end
    def set_style_radius(v, s) end
    def set_style_border_width(v, s) end
    def set_style_bg_opa(v, s) end
    def set_pos(x, y) end
    def set_width(w) end
    def set_height(h) end
    def set_clickable(c)    self.clic = c    end
    def del()    self.efface = true    end
end
global.FauxVoile = FauxVoile
def voileActif()
    var n = 0
    for v: global.VOILES    if (!v.efface && v.clic && v.parent == "sys")    n += 1    end    end
    return n
end
# Objets HASPmota (pages.jsonl) : attributs gardes dans une map, comme les membres virtuels de lvh_obj
global.ECRITURES = 0                     # ecritures d'attributs sur les objets de l'ecran
class ObjetEcran
    var attr
    def init(j)    self.attr = j    end
    def setmember(k, v)    self.attr[k] = v    global.ECRITURES += 1    end
    def member(k)    return self.attr.find(k)    end
end
class FauxChart    # objet LVGL du chart : series ajoutees, points pousses, axe
    var series, points, axe, tailles
    def init()    self.series = []    self.points = []    self.tailles = []    end
    def add_series(c, axe)    self.series.push([c, axe])    self.points.push([])    return size(self.series) - 1    end
    def set_next_value(s, v)    self.points[s].push(v)    end
    def set_axis_range(a, mini, maxi)    self.axe = [a, mini, maxi]    end
    def set_style_size(w, h, sel)    self.tailles.push(sel)    end
    def set_style_line_width(w, sel) end
end
class ObjetChart : ObjetEcran
    var _lv_obj
    def init(j)    super(self).init(j)    self._lv_obj = FauxChart()    end
    def parse_color(c)    return c    end
end
global.ECRAN_DEMARRE = false
global.HASP_DEMARRE = nil
global.OBJETS = []
def creeObjets()
    for n: global.OBJETS    global.(n) = nil    end
    global.OBJETS = []
    for l: string.split(lis(CARTE + "pages.jsonl"), "\n")
        if (size(l) == 0)    continue    end
        var j = json.load(l)
        if (j.find("id") == nil || j["id"] == 0)    continue    end
        var nom = "p" + str(j["page"]) + "b" + str(j["id"])
        global.(nom) = j["obj"] == "chart" ? ObjetChart(j) : ObjetEcran(j)
        global.OBJETS.push(nom)
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
def infos()
    var n = 0
    for l: global.JOURNAL    if (l[1] == global.LOG_LEVEL_INFO)    n += 1    end    end
    return n
end
def retablies()
    var n = 0
    for l: global.JOURNAL    if (l[1] == global.LOG_LEVEL_DEBUG && string.find(l[0], "ECRAN: retabli") == 0)    n += 1    end    end
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
def texte(n)    return global.(n).text    end

print("--- persist de la carte")
var VIRT = "ModBus_TasmotaSlaveModBus1"
var aligne = persist["modules"]["ecranDebits"]["environnement"]["analogiques"]["activation"] == "ON"
for i: 1 .. 7
    var e = ana(i)
    aligne = aligne && e["activation"] == "ON" && e["type"] == 4704 && e["id"] == i && e["idModBus"] == i && e["virtuel"] == VIRT && e["pin"] == -1
end
verifie("analogique1-7 actives, type 4704, id et idModBus 1 a 7, virtuel de l'esclave 1", aligne)
var ed = persist["modules"]["ecranDebits"]
verifie("reglages de l'ecran au persist : fenetre 10, veille 5, extinction 30, luminosite 80, pwmInverse ON", ed["fenetre"] == 10 && ed["veille"] == 5
        && ed["extinction"] == 30 && ed["luminosite"] == 80 && ed["pwmInverse"] == "ON")
var mb = persist["drivers"]["ModBus"]
verifie("maitre : id 0, RS485 du Waveshare 7B (RX 16, TX 15), 19200 8N1, periodeReleve 10, Serial et UDP", mb["id"] == 0 && mb["debit"] == 19200 && mb["mode"] == "8N1"
        && mb["environnement"]["pinsModBus"]["RX"]["pin"] == 16 && mb["environnement"]["pinsModBus"]["TX"]["pin"] == 15
        && mb["periodeReleve"] == 10 && mb["typeComm"]["Serial"] == "ON" && mb["typeComm"]["UDP"] == "ON")
var esc = mb["environnement"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus1"]
verifie("esclave 1 : actif, id 1, lectureGroupee ON", esc["activation"] == "ON" && esc["id"] == 1 && esc["lectureGroupee"] == "ON")
var re = persist["serveur"]["rangeExtender"]
verifie("Range Extender maitre id 0, point d'acces SERVEUR-DEBITS-PAC-GATEWAY, NAPT", re["activation"] == "ON" && re["id"] == 0
        && re["AP"]["SSID"] == "SERVEUR-DEBITS-PAC-GATEWAY" && re["AP"]["routeNAPT"] == "ON")
# Waveshare ESP32-S3-Touch-LCD-7B : la dalle RGB prend presque tout (broches dans display.ini, pas dans le template) ;
# restent a la carte GPIO6, l'I2C 8/9 (tactile GT911, expandeur 0x24) et le RS485 16/15
var i2c = persist["drivers"]["I2C"]
verifie("I2C du 7B actif : SDA 8, SCL 9", i2c["activation"] == "ON"
        && i2c["environnement"]["pinsI2Cs"]["pinsI2C1"]["pin"] == 8 && i2c["environnement"]["pinsI2Cs"]["pinsI2C1"]["type"] == 640
        && i2c["environnement"]["pinsI2Cs"]["pinsI2C2"]["pin"] == 9 && i2c["environnement"]["pinsI2Cs"]["pinsI2C2"]["type"] == 608)
var LIBRES_7B = [6, 8, 9, 15, 16]
var horsCarte = []
def brochesActives(o, chemin, actif)
    if !isinstance(o, map)    return    end
    var a = actif && o.find("activation", "ON") != "OFF"
    var p = o.find("pin")
    if a && type(p) == "int" && p >= 0 && LIBRES_7B.find(p) == nil    horsCarte.push(chemin + "=" + str(p))    end
    for k: o.keys()    brochesActives(o[k], chemin + "." + k, a)    end
end
brochesActives(persist["drivers"], "drivers", true)
brochesActives(persist["modules"], "modules", true)
verifie("aucune broche active hors de GPIO 6, 8, 9, 15, 16 (les autres sont a la dalle du 7B) : " + str(horsCarte), size(horsCarte) == 0)
verifie("ecran actif (ST7262 1024x600 par display.ini)", persist["drivers"]["ecran"]["activation"] == "ON")

print("--- pages.jsonl (1024 x 600)")
var lignes = []
for l: string.split(lis(CARTE + "pages.jsonl"), "\n")    if (size(l) > 0)    lignes.push(json.load(l))    end    end
var dehors = []
var vus = {}
var doublons = []
var actions = []
var reglagesP0 = []
for j: lignes
    if (j == nil)    dehors.push("ligne illisible")    continue    end
    if (j.find("x") != nil && (j["x"] < 0 || j["y"] < 0 || j["x"] + j["w"] > 1024 || j["y"] + j["h"] > 600))    dehors.push(str(j["page"]) + "/" + str(j["id"]))    end
    if (j.find("id") != nil)
        var k = str(j["page"]) + "/" + str(j["id"])
        if (vus.contains(k))    doublons.push(k)    end
        vus[k] = true
    end
    if (j.find("action") != nil)    actions.push(j["action"])    end
    if (j["page"] == 0 && (j.contains("dimming_time") || j.contains("antiburn") || j.find("id") == 0))    reglagesP0.push(j)    end
end
verifie("chaque ligne lisible et chaque objet dans la dalle 1024 x 600 : " + str(dehors), size(dehors) == 0)
verifie("aucun objet en double : " + str(doublons), size(doublons) == 0)
verifie("pied de page : actions p1, p2, p3 (Debits, Courbes, Reglages)", actions == ["p1", "p2", "p3"])
verifie("page 0 sans dimming_time ni antiburn ni fond (HASPmota ne gere pas la veille, layer_top transparent)", size(reglagesP0) == 0)

import ecranFonctions
import ecranDebitsFonctions
var ecf = ecranFonctions
var edf = ecranDebitsFonctions
verifie("bloc du persist non pose : reglages par defaut", ecf.reglage("veille") == 5 && edf.reglage("fenetre") == 10)
ecf.bloc = "ecranDebits"    # pose par controleEcranDebits.init
print("--- lecture des entrees")
verifie("reglages par defaut du persist : fenetre 10 s, veille 5 min", edf.reglage("fenetre") == 10 && edf.reglage("veille") == 5)
poseTout([12345, 100, 5000, 0, 7, 999999], 4096, 0)
var d = edf.debits(global.T)
verifie("12 345 centiemes = 123,45 L/min, 100 = 1 L/min, 7 = 0,07", d[0] > 123.449 && d[0] < 123.451 && d[1] == 1.0 && d[3] == 0.0 && d[4] > 0.069 && d[4] < 0.071)
pose(1, 12345, 0, "defaillant")
verifie("etatConstate defaillant : inconnu (nil)", edf.debits(global.T)[0] == nil)
pose(1, 12345, 0, "inconnu")
verifie("etatConstate inconnu (chien de garde du maitre) : inconnu", edf.debits(global.T)[0] == nil)
pose(1, 12345, 20)
verifie("mesure vieille de 2 fenetres pile (20 s) : encore valide", edf.debits(global.T)[0] != nil)
pose(1, 12345, 21)
verifie("mesure vieille de plus de 2 fenetres (21 s) : inconnu", edf.debits(global.T)[0] == nil)
global.modules["ecranDebits"]["fenetre"] = 30
verifie("fenetre 30 s : 21 s de vieillesse reste valide", edf.debits(global.T)[0] != nil)
global.modules["ecranDebits"]["fenetre"] = 10
pose(1, 12345, -60)
verifie("releve date apres maintenant (persist.save d'avant le redemarrage, heure NTP pas encore la) : inconnu", edf.debits(global.T)[0] == nil)
pose(1, 0x7FFFFFFF, 0)
verifie("sentinelle 0x7FFFFFFF : inconnu, jamais 21 474 836 L/min", edf.debits(global.T)[0] == nil)
efface()
verifie("entrees jamais mises a jour (demarrage) : toutes inconnues", edf.debits(global.T) == [nil, nil, nil, nil, nil, nil])
global.modules["ecranDebits"]["fenetre"] = "dix"
global.modules["ecranDebits"]["luminosite"] = 101
verifie("reglage illisible ou hors bornes au persist : defaut (fenetre 10, luminosite 80)", edf.reglage("fenetre") == 10 && edf.reglage("luminosite") == 80)
global.modules["ecranDebits"]["fenetre"] = 10
global.modules["ecranDebits"]["luminosite"] = 80

print("--- mot d'etats")
poseTout([100, 100, 100, 100, 100, 100], 4096 + (1 << 1) + (1 << 8), 0)
var w = edf.etats(global.T)
verifie("bit 1 = voie 2 muette, bit 8 = voie 3 imprecise, rien d'autre", w["muets"] == [false, true, false, false, false, false]
        && w["imprecis"] == [false, false, true, false, false, false])
pose(7, 4096 + 1, 21)
verifie("mot d'etats perime : non frais, aucun muet", edf.etats(global.T)["frais"] == false && edf.etats(global.T)["muets"] == [false, false, false, false, false, false])

print("--- modele d'ecran")
def raz()    ecf.histo = nil    ecf.histoA = nil    ecf.points = 0    edf.courbeMax = 1000    end
efface()
global.JOURNAL = []
edf.modele(global.T)
verifie("demarrage (rien jamais recu) : aucun message « fenetre ? »", fenetreInconnue() == 0 && erreurs() == 0)
raz()
poseTout([12345, 0, 50, 0, 20000, 7], 4096 + (1 << 1) + (1 << 8), 0)
var m = edf.modele(global.T)
var v = m["voies"]
verifie("voie 1 : « 123,45 » + « L/min », normale, part 38 %", v[0]["debit"] == "123,45" && v[0]["unite"] == "L/min" && v[0]["etat"] == "normal" && v[0]["part"] == "38 %")
verifie("barre : la plus forte (voie 5, 200 L/min) a 100, voie 1 a 62", v[4]["barre"] == 100 && v[0]["barre"] == 62)
verifie("voie 2 muette (bit 1) : « muet », sans unite ni barre", v[1]["debit"] == "muet" && v[1]["unite"] == "" && v[1]["barre"] == 0 && v[1]["etat"] == "muet")
verifie("voie 3 imprecise (bit 8)", v[2]["etat"] == "imprecis" && v[2]["debit"] == "0,50")
verifie("voie 4 a 0 : « 0,00 », « arrêt »", v[3]["debit"] == "0,00" && v[3]["part"] == "arrêt" && v[3]["etat"] == "arret")
verifie("nom des departs lu du persist", v[0]["nom"] == "Débit 1" && v[5]["nom"] == "Débit 6")
verifie("total de 6 voies valides : « Total 324,0 L/min » sans « partiel »", m["total"] == "Total 324,0 L/min")
verifie("releve recu a l'instant : « relevé il y a 0 s », pastille verte", m["age"] == 0 && m["releve"] == "relevé il y a 0 s" && m["liaison"] == "vert")
verifie("reglages en texte : 10 s, 5 min, 80 %", m["reglages"]["fenetre"] == "10 s" && m["reglages"]["veille"] == "5 min" && m["reglages"]["luminosite"] == "80 %" && size(m["reglages"]) == 3)
# Cles du modele rendu (feuilles ; liste de maps : `voies[].k`) : le .py les compare a la section `modele` de ecran.json
def feuilles(x, p, res, lon)
    if isinstance(x, map)
        for k: x.keys()    feuilles(x[k], p == "" ? k : p + "." + k, res, lon)    end
    elif isinstance(x, list) && size(x) > 0 && isinstance(x[0], map)
        lon.push(p + "[]=" + str(size(x)))
        feuilles(x[0], p + "[]", res, lon)
    else
        if isinstance(x, list)    lon.push(p + "=" + str(size(x)))    end
        res.push(p)
    end
end
var cles_modele = []
var longueurs_modele = []
feuilles(m, "", cles_modele, longueurs_modele)
print("MODELE_CLES: " + cles_modele.concat(","))
print("MODELE_LONGUEURS: " + longueurs_modele.concat(","))
pose(6, 7, 99)
m = edf.modele(global.T)
verifie("voie 6 perimee : « -,-- » inconnu, barre vide, pas de part", m["voies"][5]["debit"] == "-,--" && m["voies"][5]["etat"] == "inconnu" && m["voies"][5]["barre"] == 0 && m["voies"][5]["part"] == "")
verifie("une voie inconnue : total des autres marque « partiel »", m["total"] == "Total 323,9 L/min (partiel)" || m["total"] == "Total 324,0 L/min (partiel)")
global.T += 25
m = edf.modele(global.T)
verifie("toutes perimees : « Total inconnu », releve de 25 s en rouge", m["total"] == "Total inconnu" && m["releve"] == "relevé il y a 25 s" && m["liaison"] == "muet")
global.T += 200
verifie("releve de plus de 2 min : en minutes", edf.modele(global.T)["releve"] == "relevé il y a 3 min")
efface()
verifie("aucun releve jamais recu : « aucun relevé », pastille grise", edf.modele(global.T)["releve"] == "aucun relevé" && edf.modele(global.T)["liaison"] == "inconnu")
poseTout([100, 100, 100, 100, 100, 100], 4096, 10)
pose(1, 100, 40)
pose(2, 100, -60)
verifie("age du releve : le plus RECENT des 7 (10 s), un releve date du futur ignore", edf.modele(global.T)["age"] == 10)
global.modules["ecranDebits"]["veille"] = 0
verifie("veille 0 : « jamais »", edf.modele(global.T)["reglages"]["veille"] == "jamais")
global.modules["ecranDebits"]["veille"] = 5

print("--- historique de la courbe")
raz()
poseTout([150, 250, 350, 450, 550, 650], 4096, 0)
m = edf.modele(global.T)
var h = m["historique"]
verifie("premier point tout de suite : 60 valeurs par voie, la derniere = le debit en centiemes, les autres nil",
        size(h) == 6 && size(h[0]) == 60 && h[0][59] == 150 && h[5][59] == 650 && h[0][58] == nil && m["points"] == 1)
global.T += 29
poseTout([160, 250, 350, 450, 550, 650], 4096, 0)
verifie("29 s plus tard : pas de nouveau point", edf.modele(global.T)["points"] == 1 && h[0][59] == 150)
global.T += 1
m = edf.modele(global.T)
verifie("30 s : un 2e point, le plus vieux retire", m["points"] == 2 && h[0][59] == 160 && h[0][58] == 150 && size(h[0]) == 60)
global.T += 30
poseTout([160, 250, 350, 450, 550, 650], 4096, 0)
pose(2, 250, 99)
m = edf.modele(global.T)
verifie("voie inconnue : point nil (trou dans la courbe)", h[1][59] == nil && h[0][59] == 160)
verifie("haut de l'axe : 10 L/min au moins", m["courbeMax"] == 1000)
for k: 1 .. 70
    global.T += 30
    poseTout([1234, 250, 350, 450, 550, 650], 4096, 0)
    m = edf.modele(global.T)
end
verifie("73 points : la liste reste a 60, plus de trace des premiers", size(h[0]) == 60 && h[0][0] == 1234 && m["points"] == 73)
verifie("haut de l'axe : 12,34 L/min arrondi a 14 L/min (multiple de 2)", m["courbeMax"] == 1400)

print("--- ecran HASPmota : demarrage")
import ecranHaspmota
global.JOURNAL = []
verifie("sans pages.jsonl : non demarre, erreur journalisee", !ecranHaspmota.demarre() && global.HASP_DEMARRE == nil && erreurs() == 1)
global.FICHIERS = ["/json/pages.jsonl"]
verifie("ecran non demarre : erreur journalisee, aucune interface retenue", !edf.demarreEcran(ecranHaspmota) && ecf.interface == nil && global.HASP_DEMARRE == nil && erreurs() == 2)
global.ECRAN_DEMARRE = true
global.REGLES = []
poseTout([12345, 0, 50, 0, 20000, 7], 4096 + (1 << 1) + (1 << 8), 0)
verifie("ecran pret : HASPmota demarre sur /json/pages.jsonl (rangement de l'image plate)", edf.demarreEcran(ecranHaspmota) && global.HASP_DEMARRE == "/json/pages.jsonl" && erreurs() == 2)
var ch = global.p2b70._lv_obj
verifie("courbe : 6 series de la maquette sur l'axe principal, points sans pastille", size(ch.series) == 6 && ch.series[0] == ["#3FA7FF", 1] && ch.series[5] == ["#F5D04A", 1]
        && ch.tailles == [0x20000])
var regles = []
for r: global.REGLES    regles.push(r[0])    end
var ids = true
for r: global.REGLES    ids = ids && r[2] == "ecranHaspmota" && r[1] == ecranHaspmota.bouton    end
verifie("6 regles des boutons - / + (hasp#p3bNN#event), un id commun", size(regles) == 6 && regles.find("hasp#p3b22#event") != nil && regles.find("hasp#p3b44#event") != nil && ids)
var manquants = []
for k: ecranHaspmota.BOUTONS.keys()    if (global.(k) == nil || global.(k).text == nil)    manquants.push(k)    end    end
verifie("chaque bouton des regles existe dans pages.jsonl : " + str(manquants), size(manquants) == 0 && global.p3b22.text == "-" && global.p3b24.text == "+")

print("--- ecran HASPmota : affichage")
edf.ecran()
var C = edf.COULEURS
verifie("voie 1 : « 123,45 » + « L/min », couleur normale", texte("p1b13") == "123,45" && texte("p1b14") == "L/min" && global.p1b13.text_color == C["normal"] && texte("p1b15") == "38 %")
verifie("barres : voie 5 a 100, voie 1 a 62, bleu", global.p1b52.val == 100 && global.p1b12.val == 62 && global.p1b12.bg_color10 == "#3FA7FF")
verifie("voie 2 muette : « muet » rouge #FF5A5A, nom rouge, sans unite", texte("p1b23") == "muet" && global.p1b23.text_color == "#FF5A5A" && global.p1b21.text_color == "#FF5A5A" && texte("p1b24") == "")
verifie("voie 3 imprecise : orange #FFA53F (debit, barre, nom)", global.p1b33.text_color == "#FFA53F" && global.p1b32.bg_color10 == "#FFA53F" && global.p1b31.text_color == "#FFA53F")
verifie("voie 4 a l'arret : « 0,00 », « arrêt », nom normal", texte("p1b43") == "0,00" && texte("p1b45") == "arrêt" && global.p1b41.text_color == C["normal"])
verifie("page Courbes : memes valeurs et couleurs", texte("p2b13") == "123,45" && texte("p2b23") == "muet" && global.p2b33.text_color == "#FFA53F" && texte("p2b12") == "Débit 1")
verifie("en-tete : total, releve, pastille verte", texte("p0b4") == "Total 324,0 L/min" && texte("p0b3") == "relevé il y a 0 s" && global.p0b2.bg_color == "#3FD08A")
verifie("pied de page : « Débits » (page 1) en bleu, les autres en gris", global.p0b91.bg_color == "#3FA7FF" && global.p0b92.bg_color == "#1F2B38" && global.p0b93.bg_color == "#1F2B38")
verifie("page Reglages : 10 s, 5 min, 80 %", texte("p3b23") == "10 s" && texte("p3b33") == "5 min" && texte("p3b43") == "80 %")
verifie("courbe : les 60 points de l'historique pousses par serie au 1er affichage, axe 0 a 14 L/min", size(ch.points[0]) == 60 && ch.points[0][59] == 1234 && ch.points[0][0] == 1234
        && size(ch.points[5]) == 60 && ch.axe == [1, 0, 1400] && texte("p2b71") == "14 L/min")
pose(6, 7, 99)
global.T += 1
edf.ecran()
verifie("voie 6 perimee : « -,-- » gris #5B6B7C, barre vide", texte("p1b63") == "-,--" && global.p1b63.text_color == "#5B6B7C" && global.p1b62.val == 0)
verifie("une seconde plus tard, sans nouveau point : rien pousse sur la courbe", size(ch.points[0]) == 60)
global.ECRITURES = 0
edf.ecran()
verifie("rien de change (meme seconde) : aucune ecriture sur l'ecran", global.ECRITURES == 0)
global.T += 1
global.ECRITURES = 0
edf.ecran()
verifie("une seconde de plus : seul le texte du releve est reecrit", global.ECRITURES == 1 && texte("p0b3") == "relevé il y a 2 s")
import haspmota
haspmota.lvh_page_cur_idx = 3
edf.ecran()
verifie("page Reglages affichee : son bouton passe en bleu, « Débits » en gris", global.p0b93.bg_color == "#3FA7FF" && global.p0b91.bg_color == "#1F2B38")
haspmota.lvh_page_cur_idx = 1
global.T += 30
edf.ecran()
verifie("30 s : un seul point de plus par serie", size(ch.points[0]) == 61 && size(ch.points[5]) == 61 && ch.points[5][60] == 0x7FFFFFFF)
global.modules["ecranDebits"]["environnement"]["analogiques"]["analogique3"]["nom"] = "Salon"
edf.ecran()
verifie("nom change au persist : reecrit sur les deux pages", texte("p1b31") == "Salon" && texte("p2b32") == "Salon")
global.modules["ecranDebits"]["environnement"]["analogiques"]["analogique3"]["nom"] = "Débit 3"
poseTout([12345, 0, 50, 0, 20000, 7], 4096, 0)
edf.ecran()
global.HASP_DEMARRE = nil
edf.demarreEcran(ecranHaspmota)
verifie("objets neufs (redemarrage de l'interface) : tout reecrit, courbe reremplie", texte("p1b13") == "123,45" && size(global.p2b70._lv_obj.points[0]) == 60)
ch = global.p2b70._lv_obj

print("--- boutons - / + de la page Reglages")
global.SAUVES = 0
ecranHaspmota.bouton("up", "hasp#p3b24#event")
verifie("fenetre + : 11 s en RAM tout de suite, ecriture du persist differee de 3 s (un seul timer d'identifiant fixe)",
        edf.reglage("fenetre") == 11 && global.SAUVES == 0 && size(global.TIMERS) == 1 && global.TIMERS.find("ecranFonctions_sauve")[0] == 3000)
global.TIMERS["ecranFonctions_sauve"][1]()
verifie("3 s sans nouvel appui : persist.save, le timer est consomme", global.SAUVES == 1 && edf.reglage("fenetre") == 11)
global.TIMERS = {}
ecranHaspmota.bouton("down", "hasp#p3b24#event")
verifie("appui (down) sans relache : rien", edf.reglage("fenetre") == 11)
ecranHaspmota.bouton("up", "hasp#p3b22#event")
ecranHaspmota.bouton("up", "hasp#p3b44#event")
edf.ecran()
verifie("fenetre - puis luminosite + : 10 s, 90 %, ecrits sur la page Reglages", edf.reglage("fenetre") == 10 && edf.reglage("luminosite") == 90
        && texte("p3b23") == "10 s" && texte("p3b43") == "90 %")
global.SAUVES = 0
for k: 1 .. 12    ecranHaspmota.bouton("up", "hasp#p3b42#event")    end
verifie("luminosite - 12 fois : bornee a 10 %, AUCUNE ecriture du persist pendant les appuis, un seul timer", edf.reglage("luminosite") == 10 && global.SAUVES == 0 && size(global.TIMERS) == 1)
global.TIMERS["ecranFonctions_sauve"][1]()
verifie("puis une seule ecriture pour les 12 appuis", global.SAUVES == 1)
global.TIMERS = {}
ecranHaspmota.bouton("up", "hasp#p3b44#event")
ecranHaspmota.bouton("up", "hasp#p3b44#event")
ecranHaspmota.bouton("up", "hasp#p3b34#event")
ecranHaspmota.bouton("up", "hasp#p3b32#event")
for k: 1 .. 10    ecranHaspmota.bouton("up", "hasp#p3b32#event")    end
verifie("veille - jusqu'a 0 (jamais), bornee", edf.reglage("veille") == 0)
global.modules["ecranDebits"]["luminosite"] = 95
ecranHaspmota.bouton("up", "hasp#p3b44#event")
verifie("luminosite 95 + 10 : ramenee a 100", edf.reglage("luminosite") == 100)
global.modules["ecranDebits"]["veille"] = 5
global.modules["ecranDebits"]["luminosite"] = 80

print("--- veille et luminosite (expandeur 0x24 simule)")
global.JOURNAL = []
global.I2C = []
ecf.etatVeille = nil
global.INACTIF = 0
ecf.suitVeille()
verifie("demarrage : luminosite 80 % en PWM inverse (registre 0x05 = 51), puis EXIO2 allume (0x03 = 0xDF)", global.I2C == [[0x24, 5, 51], [0x24, 3, 0xDF]] && voileActif() == 0)
global.I2C = []
ecf.suitVeille()
verifie("rien de change : aucune ecriture I2C", size(global.I2C) == 0)
global.INACTIF = 5 * 60000 - 1
ecf.suitVeille()
verifie("4 min 59 sans toucher : toujours allume", size(global.I2C) == 0)
global.INACTIF = 5 * 60000
ecf.suitVeille()
verifie("5 min sans toucher : gradation 10 % (0x05 = 229), voile pose sur layer_sys", global.I2C == [[0x24, 5, 229], [0x24, 3, 0xDF]] && voileActif() == 1)
global.I2C = []
global.INACTIF = 35 * 60000 - 1
ecf.suitVeille()
verifie("34 min 59 : encore a 10 %", size(global.I2C) == 0)
global.INACTIF = 35 * 60000
ecf.suitVeille()
verifie("veille + 30 min : retroeclairage eteint par EXIO2 seul (0x03 = 0xDB), voile garde", global.I2C == [[0x24, 3, 0xDB]] && voileActif() == 1)
global.I2C = []
global.INACTIF = 100
ecf.suitVeille()
verifie("toucher : luminosite reglee rendue, voile retire", global.I2C == [[0x24, 5, 51], [0x24, 3, 0xDF]] && voileActif() == 0)
global.modules["ecranDebits"]["extinction"] = 0
global.INACTIF = 600 * 60000
global.I2C = []
ecf.suitVeille()
verifie("extinction 0 : reste a 10 % meme apres 10 h", global.I2C == [[0x24, 5, 229], [0x24, 3, 0xDF]])
global.modules["ecranDebits"]["extinction"] = 30
global.modules["ecranDebits"]["veille"] = 0
global.I2C = []
ecf.suitVeille()
verifie("veille 0 : jamais assombri, luminosite reglee rendue", global.I2C == [[0x24, 5, 51], [0x24, 3, 0xDF]] && voileActif() == 0)
global.modules["ecranDebits"]["veille"] = 5
global.INACTIF = 0
global.modules["ecranDebits"]["pwmInverse"] = "OFF"
ecf.etatVeille = nil
global.I2C = []
ecf.suitVeille()
verifie("pwmInverse OFF : 80 % -> 0x05 = 204", global.I2C == [[0x24, 5, 204], [0x24, 3, 0xDF]])
global.modules["ecranDebits"].remove("pwmInverse")
verifie("pwmInverse absent du persist : ON (sens de la demo Waveshare)", ecf.pwmInverse())
global.modules["ecranDebits"]["pwmInverse"] = "ON"
global.modules["ecranDebits"]["luminosite"] = 100
ecf.etatVeille = nil
global.I2C = []
ecf.suitVeille()
verifie("100 % en inverse : rapport borne a 5 % (0x05 = 12), jamais un extreme", global.I2C == [[0x24, 5, 12], [0x24, 3, 0xDF]])
global.modules["ecranDebits"]["luminosite"] = 80
global.EXPANDEUR = false
ecf.etatVeille = nil
global.JOURNAL = []
ecf.suitVeille()
ecf.suitVeille()
verifie("expandeur absent : une erreur, pas une a chaque appel", erreurs() == 1)
global.I2C = []
global.T += 9
ecf.suitVeille()
verifie("expandeur absent : pas de nouvel essai avant 10 s", size(global.I2C) == 0 && erreurs() == 1)
global.EXPANDEUR = true
global.T += 1
global.I2C = []
ecf.suitVeille()
verifie("10 s apres : nouvel essai, luminosite appliquee (0x05 = 51), etat memorise, retablissement en debug seulement, pas d'autre erreur",
        global.I2C == [[0x24, 5, 51], [0x24, 3, 0xDF]] && ecf.etatVeille == 100 && erreurs() == 1 && infos() == 0 && retablies() == 1)
global.I2C = []
ecf.suitVeille()
verifie("applique : plus d'ecriture", size(global.I2C) == 0)
global.ACK = false
global.INACTIF = 5 * 60000
ecf.suitVeille()
verifie("pas d'ACK : erreur journalisee", erreurs() == 2 && ecf.etatVeille == 100)
global.I2C = []
global.T += 5
ecf.suitVeille()
ecf.suitVeille()
verifie("sans ACK : pas de nouvel essai avant 10 s (pas une ecriture a chaque tic)", size(global.I2C) == 0)
global.T += 5
ecf.suitVeille()
verifie("toujours sans ACK, 10 s apres : nouvel essai (ecriture tentee), muet (une erreur par panne)",
        size(global.I2C) > 0 && erreurs() == 2 && ecf.etatVeille == 100)
global.ACK = true
global.T += 10
ecf.suitVeille()
verifie("ACK rendu : gradation appliquee, retablissement signale", ecf.etatVeille == 10 && retablies() == 2 && erreurs() == 2)
global.INACTIF = 0
ecf.suitVeille()
var itf = ecf.interface
ecf.interface = nil
global.INACTIF = 50 * 60000
global.I2C = []
ecf.suitVeille()
verifie("sans ecran demarre : pas de veille (inactivite LVGL ignoree)", size(global.I2C) == 0)
ecf.interface = itf
global.INACTIF = 0

print("--- ReglageEcranDebits")
global.TIMERS = {}
var r = edf.reglageEcranDebits
global.JOURNAL = []
global.SAUVES = 0
r("ReglageEcranDebits", 0, "fenetre 15", nil)
var rep = json.load(global.REPONSE)["ReglageEcranDebits"]
verifie("fenetre 15 : ecrite au persist, sauvee tout de suite (geste unique, pas de timer), reponse avec les 5 reglages", edf.reglage("fenetre") == 15 && global.SAUVES == 1 && size(global.TIMERS) == 0
        && rep["fenetre"] == 15 && rep["veille"] == 5 && rep["extinction"] == 30 && rep["luminosite"] == 80 && rep["pwmInverse"] == "ON" && size(rep) == 5)
r("ReglageEcranDebits", 0, "fenetre 1", nil)
r("ReglageEcranDebits", 0, "fenetre 61", nil)
r("ReglageEcranDebits", 0, "fenetre abc", nil)
r("ReglageEcranDebits", 0, "fenetre 2.5", nil)
verifie("fenetre 1, 61, abc, 2.5 : refusees et journalisees, rien change", erreurs() == 4 && edf.reglage("fenetre") == 15 && global.SAUVES == 1)
r("ReglageEcranDebits", 0, "veille 10", nil)
r("ReglageEcranDebits", 0, "extinction 0", nil)
verifie("veille 10, extinction 0 : ecrites au persist", global.modules["ecranDebits"]["veille"] == 10 && global.modules["ecranDebits"]["extinction"] == 0)
r("ReglageEcranDebits", 0, "veille 121", nil)
r("ReglageEcranDebits", 0, "extinction 241", nil)
verifie("veille 121, extinction 241 : refusees", erreurs() == 6 && edf.reglage("veille") == 10)
global.I2C = []
r("ReglageEcranDebits", 0, "LUMINOSITE 50", nil)
ecf.suitVeille()
verifie("luminosite 50 : sauvee et appliquee au prochain passage (0x05 = 127)", edf.reglage("luminosite") == 50 && global.I2C == [[0x24, 5, 127], [0x24, 3, 0xDF]])
r("ReglageEcranDebits", 0, "luminosite 9", nil)
r("ReglageEcranDebits", 0, "luminosite 101", nil)
verifie("luminosite 9 et 101 : refusees", erreurs() == 8 && edf.reglage("luminosite") == 50)
global.I2C = []
r("ReglageEcranDebits", 0, "pwmInverse off", nil)
ecf.suitVeille()
verifie("pwmInverse off : sauve OFF, reapplique (0x05 = 127)", global.modules["ecranDebits"]["pwmInverse"] == "OFF" && size(global.I2C) == 2)
r("ReglageEcranDebits", 0, "pwmInverse peut-etre", nil)
verifie("pwmInverse inconnu : refuse", erreurs() == 9 && global.modules["ecranDebits"]["pwmInverse"] == "OFF")
global.modules["ecranDebits"]["pwmInverse"] = "ON"
global.modules["ecranDebits"]["luminosite"] = 80
global.modules["ecranDebits"]["extinction"] = 30
global.modules["ecranDebits"]["veille"] = 5
var aide = edf.aideReglageEcranDebits
var cles = []
for a: aide(nil)    cles.push(a[0])    end
verifie("aide : fenetre, veille, extinction, luminosite, pwmInverse, detail de chacune", cles == ["fenetre", "veille", "extinction", "luminosite", "pwmInverse"]
        && aide("FENETRE") != nil && aide("veille") != nil && aide("extinction") != nil && aide("luminosite") != nil && aide("pwminverse") != nil && aide("autre") == nil)

print("--- « fenetre ? » quand toutes les voies passent inconnues ensemble")
global.modules["ecranDebits"]["fenetre"] = 10
poseTout([100, 100, 100, 100, 100, 100], 4096, 0)
edf.ecran()
global.JOURNAL = []
global.T += 25
edf.ecran()
verifie("6 voies valides puis 6 perimees : un message debug « fenetre ? »", fenetreInconnue() == 1 && erreurs() == 0)
global.T += 5
edf.ecran()
verifie("toujours perimees : pas de repetition", fenetreInconnue() == 1)
poseTout([100, 100, 100, 100, 100, 100], 4096, 0)
edf.ecran()
global.T += 25
edf.ecran()
verifie("valides de nouveau puis perimees : un 2e message", fenetreInconnue() == 2)
poseTout([100, 100, 100, 100, 100, 100], 4096, 0)
edf.ecran()
global.JOURNAL = []
pose(3, 100, 99)
edf.ecran()
verifie("une seule voie perimee : pas de message", fenetreInconnue() == 0)
global.T += 25
edf.ecran()
verifie("la derniere voie connue se perd : toutes inconnues, un message", fenetreInconnue() == 1)
ecf.interface = nil
poseTout([100, 100, 100, 100, 100, 100], 4096, 0)
edf.ecran()
global.T += 25
edf.ecran()
verifie("sans ecran : les voies devenues inconnues sont quand meme signalees", fenetreInconnue() == 2)

print("--- driver controleEcranDebits et choix de l'interface")
def chargeDriver()
    ecf.bloc = nil
    global.DRIVERS = []
    global.COMMANDES = {}
    global.JOURNAL = []
    global.HASP_DEMARRE = nil
    global.LVGL_DEMARRE = nil
    ecf.interface = nil
    return compile(lis(CONTROLE))()
end
print("--- polices TTF rangees sous /sd/polices au demarrage")
global.FICHIERS = ["/RobotoCondensed-Regular.ttf", "/autoexec.be", "/json/pages.jsonl"]
global.JOURNAL = []
ecf.rangePolices()
verifie("police rangee : une ligne info", infos() == 1 && erreurs() == 0)
verifie("sans carte SD : /sd puis /sd/polices crees, la TTF deplacee, rien d'autre", global.DOSSIERS == ["/sd", "/sd/polices"]
        && global.DEPLACES == [["/RobotoCondensed-Regular.ttf", "/sd/polices/RobotoCondensed-Regular.ttf"]]
        && global.FICHIERS == ["/sd/polices/RobotoCondensed-Regular.ttf", "/autoexec.be", "/json/pages.jsonl"])
global.DEPLACES = []
ecf.rangePolices()
verifie("deja rangee : rien a deplacer au demarrage suivant", size(global.DEPLACES) == 0)
global.DOSSIERS = ["/sd"]
global.FICHIERS = ["/RobotoCondensed-Regular.ttf", "/json/pages.jsonl", "/ecranHaspmota.bec"]
chargeDriver()
verifie("carte SD montee (/sd existe) : rangee par le chargement de l'interface, avant HASPmota", global.DOSSIERS == ["/sd", "/sd/polices"]
        && global.DEPLACES == [["/RobotoCondensed-Regular.ttf", "/sd/polices/RobotoCondensed-Regular.ttf"]] && global.HASP_DEMARRE != nil)
global.DOSSIERS = []
global.DEPLACES = []

global.FICHIERS = ["/json/pages.jsonl", "/ecranHaspmota.bec"]
var pilote = chargeDriver()
verifie("ecranHaspmota.bec seul : HASPmota demarre, commande declaree, driver ajoute, bloc ecranDebits", ecf.bloc == "ecranDebits" && size(global.DRIVERS) == 1 && global.COMMANDES.contains("ReglageEcranDebits")
        && global.HASP_DEMARRE == "/json/pages.jsonl" && str(ecf.interface) == str(ecranHaspmota) && erreurs() == 0 && infos() == 1)
global.FICHIERS = ["/json/pages.jsonl", "/ecranHaspmota.be", "/ecranLvgl.bec"]
chargeDriver()
verifie("les deux interfaces : HASPmota retenue, une ligne info de plus", str(ecf.interface) == str(ecranHaspmota) && global.LVGL_DEMARRE == nil && infos() == 2 && erreurs() == 0)
global.FICHIERS = ["/ecranLvgl.be"]
chargeDriver()
import ecranLvgl
verifie("ecranLvgl seul : interface LVGL demarree et affichee", global.LVGL_DEMARRE && str(ecf.interface) == str(ecranLvgl) && global.HASP_DEMARRE == nil && global.LVGL_AFFICHE != nil)
global.FICHIERS = ["/json/pages.jsonl"]
chargeDriver()
verifie("aucune interface : erreur, carte vivante (commande et driver la quand meme)", erreurs() == 1 && ecf.interface == nil
        && size(global.DRIVERS) == 1 && global.COMMANDES.contains("ReglageEcranDebits"))
global.FICHIERS = ["/json/pages.jsonl", "/ecranHaspmota.bec"]
pilote = chargeDriver()
poseTout([54321, 100, 100, 100, 100, 100], 4096, 0)
global.JOURNAL = []
pilote.every_second()
verifie("every_second : l'ecran est rafraichi, aucun log dans ce callback frequent", texte("p1b13") == "543,21" && size(global.JOURNAL) == 0)
global.T += 25
pilote.every_second()
verifie("25 s sans nouvelle mesure : la voie passe a « -,-- »", texte("p1b13") == "-,--")
global.I2C = []
ecf.etatVeille = nil
global.INACTIF = 6 * 60000
global.JOURNAL = []
pilote.every_250ms()
verifie("every_250ms : veille suivie (gradation), aucun log", global.I2C == [[0x24, 5, 229], [0x24, 3, 0xDF]] && size(global.JOURNAL) == 0)
global.INACTIF = 0

print("--- persist edite a la main : une ligne d'erreur par changement de message, pas par tic")
var sain = global.modules["ecranDebits"]
global.modules["ecranDebits"] = 12            # pas une map
global.JOURNAL = []
for k: 1 .. 4    pilote.every_250ms()    end
verifie("every_250ms : 4 tics sur un persist illisible, une seule erreur (le callback ne leve plus)", erreurs() == 1)
for k: 1 .. 4    pilote.every_second()    end
verifie("every_second : 4 tics, une seule erreur de plus (message propre a l'ecran)", erreurs() == 2)
global.modules["ecranDebits"] = "texte"
pilote.every_second()
verifie("every_second : le message change (autre type de persist) : une nouvelle ligne", erreurs() == 3)
global.modules["ecranDebits"] = sain
global.JOURNAL = []
pilote.every_second()
pilote.every_250ms()
verifie("persist remis : une ligne debug « retabli » par callback, aucune erreur ni info", erreurs() == 0 && infos() == 0 && size(global.JOURNAL) == 2 && global.JOURNAL[0][1] == global.LOG_LEVEL_DEBUG)
pilote.every_second()
pilote.every_250ms()
verifie("puis le silence", size(global.JOURNAL) == 2)

print("--- mineurs")
var leve = false
try    ecf.setmember("inexistant", 1)    except ..    leve = true    end
verifie("ecranFonctions : ecrire un nom d'etat inconnu leve une exception (plus d'echec silencieux)", leve)
verifie("ecranFonctions : un nom connu s'ecrit toujours", (def () ecf.points = 7 return ecf.points == 7 end)())
ecf.points = 0
var bloc0 = ecf.bloc
ecf.bloc = "autreBloc"
global.modules["autreBloc"] = {}
global.JOURNAL = []
r("ReglageEcranDebits", 0, "pwmInverse OFF", nil)
verifie("pwmInverse : ecrit dans le bloc de ecranFonctions.bloc, pas dans « ecranDebits » en dur", global.modules["autreBloc"].find("pwmInverse") == "OFF"
        && global.modules["ecranDebits"].find("pwmInverse") == "ON" && erreurs() == 0)
global.modules.remove("autreBloc")
ecf.bloc = bloc0
var sauve = global.modules["ecranDebits"]
global.modules.remove("ecranDebits")
verifie("entree : persist sans le bloc ecranDebits (ou sans environnement) : nil, sans exception", edf.entree(1) == nil)
global.modules["ecranDebits"] = {}
verifie("entree : bloc sans environnement : nil", edf.entree(1) == nil)
global.modules["ecranDebits"] = sauve

print(ok ? "BANC_ECRAN_DEBITS: OK" : "BANC_ECRAN_DEBITS: ECHEC")
