# Banc de la page « Systeme » CONSTRUITE par l'atelier (plan atelier-ecrans A19) : le VRAI ecranLvgl.be genere de l'ecran des
# debits (objets LVGL simules, bouchons_berry/ecran_lvgl/) pilote par le VRAI data/fs/ecranSysteme.be (ecranFonctions.interface
# = ecranLvgl) : chaque valeur ecrite par ecranSysteme.tic() trouve son objet, du bon type, et arrive sur l'objet LVGL ; un clic
# sur 120 = UN GC ; un clic sur 121 = « Confirmer ? » sans redemarrage ; deux clics = Restart 1.
# Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_page_systeme.be <dossier_vide> [interface]
# interface : le fichier ecranLvgl.be a tester ("-" = celui de la carte des debits). Derniere ligne : BANC_PAGE_SYSTEME: OK|ECHEC
import global
import sys
import string
import os

var SORTIE = global._argv[1]
var INTERFACE = size(global._argv) > 2 && global._argv[2] != "-" ? global._argv[2] : "data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be"
var PAGE = 4                             # modules.ecranSysteme.page du persist de l'ecran des debits

def lis(chemin)
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

# ---- Faux firmware (comme banc_ecran_systeme.be, plus tasmota.defer pour l'interface LVGL) ----------------------------
os.mkdir(SORTIE + "/modules")
ecrisFichier(SORTIE + "/modules/ecranLvgl.be", lis(INTERFACE))
ecrisFichier(SORTIE + "/modules/ecranSysteme.be", lis("data/fs/ecranSysteme.be"))
ecrisFichier(SORTIE + "/modules/ecranFonctions.be", lis("data/fs/ecranFonctions.be"))
ecrisFichier(SORTIE + "/modules/logFonctions.be", lis("data/fs/logFonctions.be"))
sys.path().push(SORTIE + "/modules")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/ecran_lvgl")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/ecran_systeme")

LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
global.boolMute = true
global.JOURNAL = []
global.log = def (m, n) global.JOURNAL.push([m, n]) end
global.diverses = {"logs": {"general": "info"}}
global.serveur = {}
global.drivers = {}
global.modules = {"ecranSysteme": {"activation": "ON", "page": PAGE, "log": "info"}, "ecranDebits": {"luminosite": 70, "veille": 0}}
global.MQTT_OK = true
global.T = 1000000
global.MEM = {"heap_free": 120, "frag": 35, "psram": 8192, "psram_free": 6144, "gc_heap": 100, "gc_time": 12, "stack_low": 2.5,
              "iram_free": 40, "program": 1800, "program_free": 2000}
global.REPONSES = {
    "Status 11": {"StatusSTS": {"UptimeSec": 93784, "LoadAvg": 60, "MqttCount": 4, "Wifi": {"LinkCount": 3, "Downtime": "0T00:01:05"}}},
    "UfsSize": {"UfsSize": 1856}, "UfsFree": {"UfsFree": 928},
    "Status 1": {"StatusPRM": {"RestartReason": "Software reset CPU", "BootCount": 17}},
    "Status 2": {"StatusFWR": {"Version": "15.1.0(tasmota32s3)", "BuildDateTime": "2026-11-12T10:20:30"}}}
global.CMDS = []
global.GC = 0
global.DIFFERES = []
class FauxGlobal    var sleep    def init()    self.sleep = 50    end    end
var fauxTasmota = module("tasmota")
fauxTasmota.millis = def () return global.T end
fauxTasmota.rtc = def (k) var h = 1790000000 + global.T / 1000    return k == nil ? {"local": h, "utc": h} : h end
fauxTasmota.memory = def (k)
    if (k != nil)    return global.MEM.find(k)    end
    var m = {}
    for c: global.MEM.keys()    m[c] = global.MEM[c]    end
    return m
end
fauxTasmota.cmd = def (c, mute) global.CMDS.push(c) return global.REPONSES.find(c) end
fauxTasmota.wifi = def (k) return {"rssi": -75, "quality": 50, "bssid": "AA:BB:CC:00:11:22", "ip": "192.168.0.51"}.find(k) end
fauxTasmota.read_sensors = def () return '{"ESP32":{"Temperature":45.3}}' end
fauxTasmota.strftime = def (f, t) return "10:00:00" end
fauxTasmota.gc = def () global.GC += 1 return 0 end
fauxTasmota.add_rule = def (p, f, id) end
fauxTasmota.defer = def (f) global.DIFFERES.push(f) end
fauxTasmota.global = FauxGlobal()
tasmota = fauxTasmota

import logFonctions
global.logFonctions = logFonctions
import lv
import display
import ecranLvgl
import ecranFonctions
import ecranSysteme
ecranFonctions.bloc = "ecranDebits"

var ok = true
def verifie(nom, cond)
    print((cond ? "  OK    " : "  ECHEC ") + nom)
    if (!cond)    ok = false    end
end
def erreurs()
    var k = 0
    for l: global.JOURNAL    if (l[1] == LOG_LEVEL_ERREUR)    k += 1    print("  journal : " + str(l[0]))    end    end
    return k
end
def compte(c)
    var k = 0
    for x: global.CMDS    if (x == c)    k += 1    end    end
    return k
end

display.demarre = true
verifie("demarre() du vrai ecranLvgl.be", ecranLvgl.demarre() == true)
ecranFonctions.interface = ecranLvgl
verifie("interface LVGL reconnue par ecranSysteme (couleurs entieres)", ecranSysteme.estLvgl(ecranLvgl))
ecranLvgl.montre(PAGE)
verifie("page Systeme affichee", ecranSysteme.pageAffichee() == PAGE)
global.JOURNAL = []
ecranSysteme.tic()
verifie("tic() : aucune erreur journalisee", erreurs() == 0)

# Chaque objet de CHAMPS : present, du bon type, attributs ecrits (cache) et arrives sur l'objet LVGL
var manquants = []
var mauvais = []
for c: ecranSysteme.CHAMPS
    var nom = "p" + str(PAGE) + "b" + str(c[3])
    var cache = ecranLvgl.cache.find(nom, {})
    if (!ecranLvgl.objets.contains(nom))    manquants.push(nom)
    elif (ecranLvgl.types[nom] != "label" || type(cache.find("text")) != "string" || type(cache.find("text_color")) != "int" ||
          ecranLvgl.objets[nom].texte != cache["text"] || ecranLvgl.objets[nom].style("text_color") != cache["text_color"])
        mauvais.push(nom)
    end
    if (c[4] != nil)
        nom = "p" + str(PAGE) + "b" + str(c[4])
        cache = ecranLvgl.cache.find(nom, {})
        if (!ecranLvgl.objets.contains(nom))    manquants.push(nom)
        elif (ecranLvgl.types[nom] != "bar" || type(cache.find("val")) != "int" || type(cache.find("bg_color10")) != "int" ||
              ecranLvgl.objets[nom].valeur != cache["val"] || ecranLvgl.objets[nom].style("bg_color", lv.PART_INDICATOR) != cache["bg_color10"])
            mauvais.push(nom)
        end
    end
end
verifie("chaque texte et barre de CHAMPS existe sur la page : " + str(manquants), size(manquants) == 0)
verifie("chaque ecriture sur un objet du bon type, arrivee sur l'objet LVGL : " + str(mauvais), size(mauvais) == 0)
verifie("valeur lue (RAM libre) affichee", ecranLvgl.objets["p4b1"].texte == "120 Ko")
verifie("barre (fragmentation) a sa valeur", ecranLvgl.objets["p4b4"].valeur == 35)

# Simule un appui sur `nom` : rappel LVGL de l'objet (EVENT_CLICKED), puis fonctions differees par tasmota.defer
def clic(nom)
    var o = ecranLvgl.objets[nom]
    for r: o.rappels    if (r[1] == lv.EVENT_CLICKED)    r[0](o, nil)    end    end
    var d = global.DIFFERES
    global.DIFFERES = []
    for f: d    f()    end
end
global.CMDS = []
clic("p4b120")
verifie("un clic sur 120 : un seul GC", global.GC == 1)
clic("p4b121")
verifie("un clic sur 121 : pas de redemarrage, « Confirmer ? »", compte("Restart 1") == 0 && ecranLvgl.textes["p4b121"].texte == "Confirmer ?")
clic("p4b121")
verifie("second clic sur 121 dans les 5 s : Restart 1, une fois", compte("Restart 1") == 1)
verifie("touchers : aucune erreur", erreurs() == 0)

print("BANC_PAGE_SYSTEME: " + (ok ? "OK" : "ECHEC"))
