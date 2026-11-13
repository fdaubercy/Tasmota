# Banc de la page « Systeme » des ecrans tactiles (data/fs/ecranSysteme.be + controleEcranSysteme.be, plan atelier-ecrans A19) :
# valeurs ecrites sur les objets de la page du persist par une interface simulee (HASPmota : couleurs "#RRGGBB" ; LVGL genere :
# entieres), rien hors de la page affichee, cadences 5 s / 30 s, minimum et courbe de la RAM suivis page cachee, seuils de
# couleur, verdict OTA, double appui du redemarrage, GC, dernieres erreurs gardees par le VRAI logFonctions, donnees absentes.
# Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_ecran_systeme.be <dossier_vide> [module] [driver] [log]
# module, driver, log : (temoins) une copie modifiee de ecranSysteme.be, controleEcranSysteme.be, logFonctions.be ("-" =
# l'original). Derniere ligne : BANC_ECRAN_SYSTEME: OK|ECHEC
import global
import sys
import string
import os

var SORTIE = global._argv[1]
def argument(i, defaut)    return size(global._argv) > i && global._argv[i] != "-" ? global._argv[i] : defaut    end
var SOURCE = argument(2, "data/fs/ecranSysteme.be")
var CONTROLE = argument(3, "data/fs/controleEcranSysteme.be")
var LOGS = argument(4, "data/fs/logFonctions.be")

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

# ---- Faux firmware --------------------------------------------------------------------------------------------
os.mkdir(SORTIE + "/modules")
ecrisFichier(SORTIE + "/modules/ecranSysteme.be", lis(SOURCE))
ecrisFichier(SORTIE + "/modules/ecranFonctions.be", lis("data/fs/ecranFonctions.be"))
ecrisFichier(SORTIE + "/modules/logFonctions.be", lis(LOGS))
sys.path().push(SORTIE + "/modules")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/ecran_systeme")

LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
global.boolMute = true
global.JOURNAL = []                      # log() du firmware : [message, niveau]
global.log = def (m, n) global.JOURNAL.push([m, n]) end
global.diverses = {"logs": {"general": "info"}}
global.serveur = {}
global.drivers = {}
global.modules = {"ecranSysteme": {"activation": "ON", "page": 9, "log": "info"}, "ecranDebits": {"luminosite": 70, "veille": 0}}
global.MQTT_OK = true

global.T = 1000000                       # tasmota.millis()
def heure()    return 1790000000 + global.T / 1000    end
global.MEM = {}                          # tasmota.memory()
global.MEM_MAPS = 0                      # appels de tasmota.memory() SANS cle (une map allouee)
global.REPONSES = {}                     # tasmota.cmd : commande -> reponse
global.CMDS = []                         # commandes envoyees
global.WIFI = {}
global.CAPTEURS = "{}"
global.GC = 0
global.REGLES = []
global.DRIVERS = []
class FauxGlobal    var sleep    def init()    self.sleep = 50    end    end
var fauxTasmota = module("tasmota")
fauxTasmota.millis = def () return global.T end
fauxTasmota.rtc = def (k) return k == nil ? {"local": heure(), "utc": heure()} : heure() end
fauxTasmota.memory = def (k)
    if (k != nil)    return global.MEM.find(k)    end
    global.MEM_MAPS += 1
    var m = {}
    for c: global.MEM.keys()    m[c] = global.MEM[c]    end
    return m
end
fauxTasmota.cmd = def (c, mute) global.CMDS.push(c) return global.REPONSES.find(c) end
fauxTasmota.wifi = def (k) return global.WIFI.find(k) end
fauxTasmota.read_sensors = def () return global.CAPTEURS end
fauxTasmota.strftime = def (f, t) return string.format("%02d:%02d:%02d", (t % 86400) / 3600, (t % 3600) / 60, t % 60) end
fauxTasmota.gc = def () global.GC += 1 global.MEM["heap_free"] += 10 return 0 end
fauxTasmota.add_rule = def (p, f, id) global.REGLES.push([p, f, id]) end
fauxTasmota.add_driver = def (d) global.DRIVERS.push(d) end
fauxTasmota.global = FauxGlobal()
tasmota = fauxTasmota
class Driver end
global.Driver = Driver

import logFonctions
global.logFonctions = logFonctions
import ecranFonctions
import ecranSysteme
import haspmota
ecranFonctions.bloc = "ecranDebits"

# Interfaces simulees : chaque ecris est enregistre [objet, attribut, valeur] ; LVGL = membre `page`
global.ECRITS = []
var fauxHasp = module("ecranHaspmota")
fauxHasp.ecris = def (id, a, v) global.ECRITS.push([id, a, v]) end
var fauxLvgl = module("ecranLvgl")
fauxLvgl.ecris = def (id, a, v) global.ECRITS.push([id, a, v]) end
fauxLvgl.page = 9

def carte()
    global.MEM = {"heap_free": 120, "frag": 35, "psram": 8192, "psram_free": 6144, "gc_heap": 100, "gc_time": 12, "stack_low": 2.5,
                  "iram_free": 40, "program": 1800, "program_free": 2000, "flash": 16384}
    global.REPONSES = {
        "Status 11": {"StatusSTS": {"UptimeSec": 93784, "LoadAvg": 60, "Sleep": 50, "MqttCount": 4,
                                    "Wifi": {"RSSI": 50, "Signal": -75, "LinkCount": 3, "Downtime": "0T00:01:05"}}},
        "UfsSize": {"UfsSize": [30000000, 1856]}, "UfsFree": {"UfsFree": [1000, 928]},
        "Status 1": {"StatusPRM": {"RestartReason": "Software reset CPU", "BootCount": 17}},
        "Status 2": {"StatusFWR": {"Version": "15.1.0(tasmota32s3)", "BuildDateTime": "2026-11-12T10:20:30"}},
        "RgxClients": {"RgxClients": {"AABBCCDDEEFF": {"IPAddress": "192.168.4.2", "RSSI": -60},
                                      "112233445566": {"IPAddress": "192.168.4.3", "RSSI": -70}}}}
    global.WIFI = {"rssi": -75, "quality": 50, "bssid": "AA:BB:CC:00:11:22", "ip": "192.168.0.51"}
    global.CAPTEURS = '{"Time":"2026-11-13T10:00:00","ESP32":{"Temperature":45.3},"TempUnit":"C"}'
end

# Repart de zero : etat du module, interface, page affichee
def neuf(itf, affichee)
    import global
    global.(".ecranSysteme") = nil
    ecranFonctions.interface = itf
    haspmota.lvh_page_cur_idx = affichee
    fauxLvgl.page = affichee
    global.ECRITS = []
    global.CMDS = []
    global.MEM_MAPS = 0
    carte()
end

# Derniere valeur ecrite sur (objet, attribut), nil si jamais ; nombre d'ecritures sur (objet, attribut)
def lu(id, a)
    var v = nil
    for e: global.ECRITS    if (e[0] == id && e[1] == a)    v = e[2]    end    end
    return v
end
def nb(id, a)
    var n = 0
    for e: global.ECRITS    if (e[0] == id && e[1] == a)    n += 1    end    end
    return n
end
def compte(c)
    var n = 0
    for x: global.CMDS    if (x == c)    n += 1    end    end
    return n
end

var ok = true
def verifie(nom, cond)
    print((cond ? "  OK    " : "  ECHEC ") + nom)
    if (!cond)    ok = false    end
end
var VERT = "#3FD08A"
var ORANGE = "#FFA53F"
var ROUGE = "#FF5A5A"
var NEUTRE = "#E8EDF2"

# ---- 1. Table CHAMPS -------------------------------------------------------------------------------------------
print("--- 1. Table CHAMPS")
var ids = {}
var champsOk = size(ecranSysteme.CHAMPS) > 30
for c: ecranSysteme.CHAMPS
    for id: [c[3], c[4]]
        if (id == nil)    continue    end
        if (ids.contains(id) || id < 1 || id > 199 || id == ecranSysteme.BOUTON_GC || id == ecranSysteme.BOUTON_REDEMARRER)    champsOk = false    end
        ids[id] = true
    end
end
verifie("ids uniques, de 1 a 199, distincts des boutons", champsOk)

# ---- 2. Page affichee (HASPmota) : chaque champ sur le bon objet, texte, unite, couleur ---------------------------
print("--- 2. Valeurs ecrites (HASPmota, page 9 affichee)")
neuf(fauxHasp, 9)
ecranSysteme.tic()
var attendus = [[1, "120 Ko", VERT], [2, "120 Ko", VERT], [3, "35 %", ORANGE], [5, "8,0 Mo", NEUTRE], [6, "6,0 Mo", VERT],
                [8, "100 Ko", NEUTRE], [9, "12 ms", NEUTRE], [10, "2,5 Ko", VERT], [11, "40 Ko", NEUTRE], [20, "1,8 Mo", NEUTRE],
                [21, "2,0 Mo", ORANGE], [23, "possible", VERT], [24, "1,8 Mo", NEUTRE], [25, "928 Ko", VERT], [30, "60 %", ORANGE],
                [32, "50 ms", NEUTRE], [33, "45,3 °C", VERT], [40, "1 j 2 h", NEUTRE], [41, "Software reset CPU", NEUTRE],
                [42, "17", NEUTRE], [50, "-75 dBm", ORANGE], [52, "AA:BB:CC:00:11:22", NEUTRE], [53, "192.168.0.51", NEUTRE],
                [54, "2", NEUTRE], [55, "1 min 05 s", NEUTRE], [56, "connecté", VERT], [57, "3", NEUTRE], [58, "synchronisée", VERT],
                [70, "--", NEUTRE], [71, "--", NEUTRE], [72, "--", NEUTRE], [73, "--", NEUTRE], [80, "70 %", NEUTRE],
                [81, "jamais", NEUTRE], [90, "15.1.0(tasmota32s3)", NEUTRE], [91, "2026-11-12 10:20:30", NEUTRE], [101, "--", NEUTRE]]
for a: attendus
    var id = "p9b" + str(a[0])
    verifie(id + " = « " + a[1] + " » en " + a[2], lu(id, "text") == a[1] && lu(id, "text_color") == a[2])
end
verifie("barres : fragmentation 35, PSRAM 25, OTA 90, FS 50, charge 60, signal 50 (qualite)",
        lu("p9b4", "val") == 35 && lu("p9b7", "val") == 25 && lu("p9b22", "val") == 90 && lu("p9b26", "val") == 50 &&
        lu("p9b31", "val") == 60 && lu("p9b51", "val") == 50)
verifie("couleur des barres (bg_color10) : OTA orange, FS vert", lu("p9b22", "bg_color10") == ORANGE && lu("p9b26", "bg_color10") == VERT)
var horsPage = 0
for e: global.ECRITS    if (string.find(e[0], "p9b") != 0)    horsPage += 1    end    end
verifie("toutes les ecritures sur la page 9", horsPage == 0 && size(global.ECRITS) > 80)
verifie("Status 1 et Status 2 lus une fois, Status 11 une fois", compte("Status 1") == 1 && compte("Status 2") == 1 && compte("Status 11") == 1)
verifie("RgxClients non demande sans range extender actif", compte("RgxClients") == 0)

# ---- 3. Rien ecrit hors de la page, ni sans page au persist ; pas de map de tasmota.memory page cachee -----------
print("--- 3. Page cachee, page absente")
neuf(fauxHasp, 1)
for i: 1 .. 12    ecranSysteme.tic()    global.T += 1000    end
verifie("page 1 affichee : rien ecrit, aucune commande", size(global.ECRITS) == 0 && size(global.CMDS) == 0)
verifie("page cachee : tasmota.memory() jamais appele sans cle", global.MEM_MAPS == 0)
neuf(fauxHasp, 9)
global.modules["ecranSysteme"].remove("page")
ecranSysteme.tic()
verifie("sans page au persist : rien ecrit", size(global.ECRITS) == 0)
global.modules["ecranSysteme"]["page"] = 9
neuf(nil, 9)
ecranSysteme.tic()
verifie("sans ecran (interface nil) : rien ecrit, pas d'exception", size(global.ECRITS) == 0)

# ---- 4. Cadences ------------------------------------------------------------------------------------------------
print("--- 4. Cadences")
neuf(fauxHasp, 9)
for i: 0 .. 4    ecranSysteme.tic()    global.T += 1000    end
verifie("5 tics en 5 s : une seule mesure", nb("p9b1", "text") == 1)
ecranSysteme.tic()
verifie("a 5 s : seconde mesure, Status 1 et 2 pas relus", nb("p9b1", "text") == 2 && compte("Status 1") == 1 && compte("Status 2") == 1)
for i: 1 .. 24    global.T += 1000    ecranSysteme.tic()    end
verifie("a 29 s : Status 11 lu une seule fois", compte("Status 11") == 1 && nb("p9b1", "text") == 6)
global.T += 1000
ecranSysteme.tic()
verifie("a 30 s : Status 11 relu", compte("Status 11") == 2)
haspmota.lvh_page_cur_idx = 1
global.T += 1000
ecranSysteme.tic()
haspmota.lvh_page_cur_idx = 9
global.T += 1000
var avant = nb("p9b1", "text")
ecranSysteme.tic()
verifie("retour sur la page : mesure et Status 11 aussitot", nb("p9b1", "text") == avant + 1 && compte("Status 11") == 3)

# ---- 5. Minimum et courbe suivis page cachee --------------------------------------------------------------------
print("--- 5. RAM minimale et courbe")
neuf(fauxHasp, 1)
for v: [100, 80, 90]    global.MEM["heap_free"] = v    ecranSysteme.tic()    global.T += 1000    end
verifie("minimum 80 suivi page cachee", ecranSysteme.etat()["ramMin"] == 80)
verifie("courbe : un point au premier tic (100), 120 cases", ecranSysteme.etat()["points"] == 1 && size(ecranSysteme.courbe()) == 120 && ecranSysteme.courbe()[-1] == 100)
global.T += 26000
ecranSysteme.tic()
verifie("pas de point avant 30 s", ecranSysteme.etat()["points"] == 1)
global.T += 1000
ecranSysteme.tic()
verifie("point a 30 s", ecranSysteme.etat()["points"] == 2 && ecranSysteme.courbe()[-1] == 90 && ecranSysteme.courbe()[-2] == 100)
for i: 1 .. 130    global.T += 30000    ecranSysteme.tic()    end
verifie("courbe bornee a 120 points", size(ecranSysteme.courbe()) == 120 && ecranSysteme.courbe()[0] != nil)
haspmota.lvh_page_cur_idx = 9
global.MEM["heap_free"] = 95
ecranSysteme.tic()
verifie("minimum affiche (80 Ko, orange : seuil 30/15 non franchi -> vert)", lu("p9b2", "text") == "80 Ko" && lu("p9b2", "text_color") == VERT)

# ---- 6. Verdict OTA et seuils -----------------------------------------------------------------------------------
print("--- 6. Verdict OTA, seuils")
neuf(fauxHasp, 9)
global.MEM["program_free"] = 1500
ecranSysteme.tic()
verifie("place libre < programme : OTA impossible en rouge", lu("p9b23", "text") == "impossible" && lu("p9b23", "text_color") == ROUGE)
verifie("barre OTA pleine (100) rouge", lu("p9b22", "val") == 100 && lu("p9b22", "bg_color10") == ROUGE)
verifie("seuils RAM : 20 rouge, 45 orange, 60 vert",
        ecranSysteme.niveau("ramLibre", 20) == "rouge" && ecranSysteme.niveau("ramLibre", 45) == "orange" && ecranSysteme.niveau("ramLibre", 60) == "vert")
verifie("seuils fragmentation : 55 rouge, 30 orange, 10 vert",
        ecranSysteme.niveau("fragmentation", 55) == "rouge" && ecranSysteme.niveau("fragmentation", 30) == "orange" && ecranSysteme.niveau("fragmentation", 10) == "vert")
verifie("seuils signal : -85 rouge, -60 vert", ecranSysteme.niveau("rssi", -85) == "rouge" && ecranSysteme.niveau("rssi", -60) == "vert")
neuf(fauxHasp, 9)
global.MEM["heap_free"] = 20
ecranSysteme.tic()
verifie("RAM libre 20 Ko ecrite en rouge", lu("p9b1", "text") == "20 Ko" && lu("p9b1", "text_color") == ROUGE)

# ---- 7. Boutons : redemarrage confirme, GC ------------------------------------------------------------------------
print("--- 7. Boutons")
neuf(fauxHasp, 9)
ecranSysteme.appui(121)
verifie("un appui : pas de redemarrage, « Confirmer ? »", compte("Restart 1") == 0 && lu("p9b121", "text") == "Confirmer ?")
global.T += 2000
ecranSysteme.appui(121)
verifie("second appui dans les 5 s : Restart 1", compte("Restart 1") == 1)
neuf(fauxHasp, 1)
ecranSysteme.appui(121)
global.T += 4000
ecranSysteme.tic()
verifie("4 s apres : confirmation toujours en attente", lu("p9b121", "text") == "Confirmer ?")
global.T += 2000
ecranSysteme.tic()
verifie("6 s apres, page cachee : texte rendu « Redémarrer »", lu("p9b121", "text") == "Redémarrer")
ecranSysteme.appui(121)
verifie("appui apres expiration : pas de redemarrage", compte("Restart 1") == 0 && lu("p9b121", "text") == "Confirmer ?")
neuf(fauxHasp, 9)
ecranSysteme.bouton("down", "hasp#p9b121#event")
verifie("regle HASPmota : « down » ignore", lu("p9b121", "text") == nil)
ecranSysteme.bouton("up", "hasp#p9b121#event")
verifie("regle HASPmota : « up » sur p9b121 = appui", lu("p9b121", "text") == "Confirmer ?")
neuf(fauxHasp, 9)
ecranSysteme.tic()
global.T += 1000
ecranSysteme.bouton("up", "hasp#p9b120#event")
ecranSysteme.tic()
verifie("GC : tasmota.gc() lance, mesure relue aussitot (130 Ko)", global.GC == 1 && lu("p9b1", "text") == "130 Ko" && nb("p9b1", "text") == 2)

# ---- 8. Dernieres erreurs (vrai logFonctions) ---------------------------------------------------------------------
print("--- 8. Dernieres erreurs")
neuf(fauxHasp, 9)
global._etatLogFonctions = nil
logFonctions.log("TEST_ERREUR: E0 !", LOG_LEVEL_ERREUR)
logFonctions.log("TEST: une info !", LOG_LEVEL_INFO)
verifie("une erreur puis une info : seule l'erreur gardee", size(logFonctions.dernieresErreurs()) == 1)
for i: 1 .. 6    global.T += 1000    logFonctions.log("TEST_ERREUR: E" + str(i) + " !", LOG_LEVEL_ERREUR, "ecranSysteme")    end
var l = logFonctions.dernieresErreurs()
verifie("6 erreurs : les 5 dernieres, de E2 a E6, l'info non gardee", size(l) == 5 && l[0][1] == "TEST_ERREUR: E2 !" && l[4][1] == "TEST_ERREUR: E6 !")
verifie("heure de chaque erreur gardee (entier)", type(l[4][0]) == "int" && l[4][0] == heure())
ecranSysteme.tic()
verifie("erreur1 = la plus recente (heure + message), en rouge",
        lu("p9b101", "text") == tasmota.strftime("%H:%M:%S", heure()) + " TEST_ERREUR: E6 !" && lu("p9b101", "text_color") == ROUGE)
verifie("erreur5 = E2", string.find(str(lu("p9b105", "text")), "TEST_ERREUR: E2 !") > 0)
var longue = ""    for i: 1 .. 89    longue += "x"    end      # l'accent tombe sur les octets 90 et 91 (LONGUEUR_ERREUR = 90)
logFonctions.log(longue + "é fin", LOG_LEVEL_ERREUR)
neuf(fauxHasp, 9)
ecranSysteme.tic()
verifie("message coupe avant un accent (jamais un octet UTF-8 seul)", lu("p9b101", "text") == tasmota.strftime("%H:%M:%S", heure()) + " " + longue)
var sauveModules = global.modules    global.modules = nil
verifie("persist absent (modules nil) : pas de page, pas d'exception", ecranSysteme.page() == nil)
global.modules = sauveModules
verifie("cible ecranSysteme connue de logFonctions, bloc modules.ecranSysteme",
        logFonctions.CIBLES.find("ecranSysteme") != nil && logFonctions.lieu("ecranSysteme") != nil && logFonctions.lieu("ecranSysteme")[0] == global.modules["ecranSysteme"])
global.JOURNAL = []
ecranSysteme.log("ECRAN_SYSTEME: deroule !", LOG_LEVEL_DEBUG)
var filtre = size(global.JOURNAL) == 0
global.modules["ecranSysteme"]["log"] = "debug"
logFonctions.invalideSeuils()
ecranSysteme.log("ECRAN_SYSTEME: deroule !", LOG_LEVEL_DEBUG)
verifie("seuil de la cible ecranSysteme suivi (debug coupe a info, emis a debug)", filtre && size(global.JOURNAL) == 1)
global.modules["ecranSysteme"]["log"] = "info"
logFonctions.invalideSeuils()

# ---- 9. ModBus et range extender charges ------------------------------------------------------------------------
print("--- 9. ModBus, range extender")
class FauxEsclaves    var esclavesMuets, derniersContacts    end
neuf(fauxHasp, 9)
var fe = FauxEsclaves()
fe.esclavesMuets = {2: true}
fe.derniersContacts = {1: heure() - 12, 2: heure() - 400}
global.modBus_TasmotaSlaveModBus = fe
global.drivers = {"ModBus": {"environnement": {"TasmotaSlaveModBus": {"activation": "ON",
    "TasmotaSlaveModBus1": {"activation": "ON", "id": 1}, "TasmotaSlaveModBus2": {"activation": "ON", "id": 2},
    "TasmotaSlaveModBus3": {"activation": "OFF", "id": 3}}}}}
global.serveur = {"rangeExtender": {"activation": "ON"}}
ecranSysteme.tic()
verifie("esclaves joignables 1/2 en rouge (un muet)", lu("p9b70", "text") == "1/2" && lu("p9b70", "text_color") == ROUGE)
verifie("dernier contact : il y a 12 s", lu("p9b72", "text") == "il y a 12 s")
verifie("delais depasses : aucun compteur, « -- »", lu("p9b71", "text") == "--")
verifie("clients du point d'accès : 2", lu("p9b73", "text") == "2" && compte("RgxClients") == 1)
global.modBus_TasmotaSlaveModBus = nil
global.drivers = {}
global.serveur = {}

# ---- 10. Donnees absentes ---------------------------------------------------------------------------------------
print("--- 10. Donnees absentes")
neuf(fauxHasp, 9)
global.MEM = {"heap_free": 50}
global.REPONSES = {}
global.WIFI = {}
global.CAPTEURS = '{"Time":"2026-11-13T10:00:00","DS18B20":{"Temperature":20.0}}'
global.MQTT_OK = false
var exception = nil
try    ecranSysteme.tic()    except .. as e, m    exception = str(e) + " " + str(m)    end
verifie("aucune exception (" + str(exception) + ")", exception == nil)
verifie("PSRAM, OTA, FS, charge, signal, temperature, version : « -- »",
        lu("p9b5", "text") == "--" && lu("p9b23", "text") == "--" && lu("p9b24", "text") == "--" && lu("p9b30", "text") == "--" &&
        lu("p9b50", "text") == "--" && lu("p9b33", "text") == "--" && lu("p9b90", "text") == "--" && lu("p9b7", "val") == 0)
verifie("MQTT deconnecte en rouge", lu("p9b56", "text") == "déconnecté" && lu("p9b56", "text_color") == ROUGE)
verifie("Status 1 / 2 sans reponse : relus au tic suivant", (def () global.T += 5000 ecranSysteme.tic() return compte("Status 1") == 2 end)())
global.MQTT_OK = true

# ---- 11. Interface LVGL generee : couleurs entieres, page de ecranLvgl.page ---------------------------------------
print("--- 11. LVGL genere")
neuf(fauxLvgl, 9)
ecranSysteme.tic()
verifie("LVGL : texte et couleur entiere", lu("p9b1", "text") == "120 Ko" && lu("p9b1", "text_color") == 0x3FD08A && lu("p9b3", "text_color") == 0xFFA53F)
neuf(fauxLvgl, 2)
haspmota.lvh_page_cur_idx = 9      # piege : la page de HASPmota ne compte pas pour LVGL
ecranSysteme.tic()
verifie("LVGL page 2 affichee : rien ecrit", size(global.ECRITS) == 0)

# ---- 12. Driver ---------------------------------------------------------------------------------------------------
print("--- 12. Driver controleEcranSysteme")
def chargeDriver()
    global.DRIVERS = []
    global.REGLES = []
    return compile(lis(CONTROLE))()
end
global.modules["ecranSysteme"]["activation"] = "OFF"
neuf(fauxHasp, 9)
var d = chargeDriver()
verifie("garde : activation OFF -> aucun driver", d == nil && size(global.DRIVERS) == 0)
global.modules["ecranSysteme"]["activation"] = "ON"
d = chargeDriver()
verifie("activation ON -> driver ajoute", d != nil && size(global.DRIVERS) == 1)
verifie("regles HASPmota des deux boutons sur la page 9",
        size(global.REGLES) == 2 && global.REGLES[0][0] == "hasp#p9b120#event" && global.REGLES[1][0] == "hasp#p9b121#event")
d.every_second()
verifie("every_second : page rafraichie", lu("p9b1", "text") == "120 Ko")
var fauxCasse = module("ecranCasse")
fauxCasse.ecris = def (id, a, v) raise "io_error", "ecran casse" end
ecranFonctions.interface = fauxCasse
global.JOURNAL = []
for i: 1 .. 3    global.T += 5000    d.every_second()    end
var erreursDriver = 0
var infosDriver = 0
for j: global.JOURNAL
    if (j[1] == LOG_LEVEL_ERREUR && string.find(j[0], "CONTROLE_ECRAN_SYSTEME_ERREUR") == 0)    erreursDriver += 1    end
    if (j[1] == LOG_LEVEL_INFO)    infosDriver += 1    end
end
verifie("echec du rafraichissement : une erreur, pas une par seconde, aucune info", erreursDriver == 1 && infosDriver == 0)

print("BANC_ECRAN_SYSTEME: " + (ok ? "OK" : "ECHEC"))
