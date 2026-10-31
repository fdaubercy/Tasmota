# Banc de test Berry de la page /cuve (2026-10-31) : data/fs/cuvePageFonctions.be (route, fichier de l'extension
# liquidfill, page, dimensions de la cuve) et les routes /cuve des deux cartes : CONTROLE_GARAGE du maitre P4
# (instancie en entier, persist reel) et CAPTEURS_CUVE de la cuve (methodes isolees de son texte).
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python, qui ajoute le rendu de la page dans Chrome sans interface :
#     python outils_docs/scripts_python/berry/banc_cuve_page.py
# Ou directement, DEPUIS LA RACINE DU DEPOT (dossier_sortie : ou ecrire les pages ; dossier_sources : contient fs/ et sd/,
# "data" par defaut ; sert au temoin du banc, qui l'oriente vers une copie modifiee) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_cuve_page.be <dossier_sortie> [dossier_sources]
#
# Les VRAIS fichiers sont COMPILES depuis leur texte ; cuvePageFonctions et graphiquesFonctions, que la route importe,
# sont COPIES dans <dossier_sortie>/modules (seul dossier ajoute au chemin avec les bouchons : data/fs fournirait les
# vrais historiqueFonctions et gestionFileFolder a la place des bouchons).
# La derniere ligne, BANC_CUVE_PAGE: OK|ECHEC, est lue par l'enveloppe pour son code de sortie.
import global
import sys
import string
import json
import os

if (size(global._argv) < 2)
    print("Usage : berry.exe banc_cuve_page.be <dossier_sortie> [dossier_sources]")
    print("BANC_CUVE_PAGE: ECHEC (argument manquant)")
    return
end
var SORTIE = global._argv[1]
var SOURCES = size(global._argv) > 2 ? global._argv[2] : "data"

def lisFichier(chemin)
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
if (!os.path.exists(SORTIE + "/modules"))    os.mkdir(SORTIE + "/modules")    end
for m: ["cuvePageFonctions", "graphiquesFonctions"]
    ecrisFichier(SORTIE + "/modules/" + m + ".be", lisFichier(SOURCES + "/fs/" + m + ".be"))
end
# cuveFonctions (importe par pageCuve de la cuve pour le montage de la sonde) : bouchon, sans montage connu
ecrisFichier(SORTIE + "/modules/cuveFonctions.be", "var m = module('cuveFonctions')\nm.montageSonde = def () return nil end\nreturn m\n")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/graphiques")
sys.path().push(SORTIE + "/modules")

# ---- Globaux du firmware bouchonnes -------------------------------------------------------------
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
class Driver end
var pilotes = []
class TASMOTA_BOUCHON
    def yield() end
    def add_cron() end
    def add_cmd() end
    def add_driver(d) pilotes.push(d) end
    def add_rule() end
    def cmd(c, muet) return nil end
end
tasmota = TASMOTA_BOUCHON()
var journal = []
class LOG_BOUCHON def log(msg, niveau, cible) journal.push([msg, niveau, cible]) end end
logFonctions = LOG_BOUCHON()

def charge(chemin)
    return compile(lisFichier(chemin))()
end

var echecs = 0
def verifie(condition, nom)
    print((condition ? "  OK     " : "  ECHEC  ") + nom)
    if (!condition)    echecs += 1    end
end

import webserver
import path
import gestionFileFolder
import historiqueFonctions
# Routes declarees par web_add_handler (le bouchon du module natif ne les garde pas)
var routes = {}
webserver.on = def (url, f, methode) routes[url] = [f, methode] end
gestionFileFolder.racine = SOURCES
path.racine = SOURCES

import cuvePageFonctions
import graphiquesFonctions

# Rend la page ou le fichier d'une requete ; renvoie le texte ecrit (ou "EXCEPTION ...")
def sert(args, appel, nomFichier)
    webserver.raz(args)
    var f = open(SORTIE + "/" + nomFichier, "wb")
    webserver.sortie = f
    var leve = nil
    try appel() except .. as e, m leve = str(e) + " : " + str(m) end
    f.close()
    return leve != nil ? "EXCEPTION " + leve : lisFichier(SORTIE + "/" + nomFichier)
end
# window.CUVE tel que la page l'ecrit, ou nil
def configDe(page)
    var d = string.find(page, "window.CUVE=")
    var fin = string.find(page, ";</script>", d)
    return (d >= 0 && fin > 0 ? json.load(page[d + 12 .. fin - 1]) : nil)
end
def route(dim, args, nom, sonde)
    return sert(args, def () cuvePageFonctions.route(dim, sonde) end, nom)
end

# ---- 1. Acces et fichier de l'extension --------------------------------------------------------
print("1. Acces refuse, /cuve?f=liquidfill.js.gz")
webserver.privilegie = false
var sortie = route({"hauteur": 110}, {}, "refuse.txt")
webserver.privilegie = true
verifie(webserver.code == nil && webserver.envois == 0 && webserver.debut == nil && sortie == "", "acces non privilegie : rien n'est envoye")
webserver.privilegie = false
sortie = route({}, {"f": "liquidfill.js.gz"}, "refuse_f.txt")
webserver.privilegie = true
verifie(webserver.code == nil && webserver.envois == 0 && sortie == "", "acces non privilegie + f= : rien n'est envoye non plus")

var fichierLiquid = cuvePageFonctions.FICHIERS.find("liquidfill.js.gz")
verifie(size(cuvePageFonctions.FICHIERS) == 1 && fichierLiquid != nil && fichierLiquid[0] == "/sd/js/echarts-liquidfill.min.js.gz"
        && fichierLiquid[1] == "application/octet-stream", "un seul fichier servi : /sd/js/echarts-liquidfill.min.js.gz en application/octet-stream")
# L'envoi lit le chemin tel quel sur le disque : on le pointe vers le fichier des sources, apres avoir verifie le chemin declare
fichierLiquid[0] = SOURCES + "/sd/js/echarts-liquidfill.min.js.gz"
webserver.raz({"f": "liquidfill.js.gz"})
webserver.sortie = open(SORTIE + "/liquidfill_recu.js.gz", "wb")
cuvePageFonctions.route({})
webserver.sortie.close()
fichierLiquid[0] = "/sd/js/echarts-liquidfill.min.js.gz"
verifie(webserver.code == 200 && webserver.mime == "application/octet-stream" && webserver.envois >= 1 && webserver.ferme && webserver.debut == nil,
        "liquidfill.js.gz : 200 application/octet-stream, " + str(webserver.envois) + " morceaux, reponse fermee, pas de page")
webserver.raz({"f": "inconnu.js"})
webserver.sortie = open(SORTIE + "/inconnu.txt", "wb")
cuvePageFonctions.route({})
webserver.sortie.close()
verifie(webserver.code == nil && webserver.debut == "Niveau de la cuve", "f= inconnu : aucun fichier servi, la page est renvoyee")

# ---- 2. Dimensions et page ----------------------------------------------------------------------
print("2. Dimensions de la cuve")
var D = cuvePageFonctions.dimension
verifie(D({"hauteur": 110}, "hauteur") == 110 && D({"hauteur": 55.5}, "hauteur") == 55.5, "dimension en cm lue (entier ou reel)")
verifie(D({}, "hauteur") == 100 && D(nil, "hauteur") == 100 && D("x", "hauteur") == 100 && D([1], "hauteur") == 100, "bloc absent, vide ou pas une map : 100")
verifie(D({"hauteur": 0}, "hauteur") == 100 && D({"hauteur": -5}, "hauteur") == 100 && D({"hauteur": "110"}, "hauteur") == 100
        && D({"hauteur": nil}, "hauteur") == 100 && D({"hauteur": true}, "hauteur") == 100, "valeur nulle, negative ou mal typee : 100")

print("3. Page /cuve")
var DIM = {"hauteur": 110, "longueur": 340, "largeur": 180}
var avant = size(journal)
var page = route(DIM, {}, "page.html")
var cfg = configDe(page)
verifie(webserver.debut == "Niveau de la cuve" && webserver.bouton == webserver.BUTTON_MAIN && webserver.termine && string.find(page, "EXCEPTION") != 0,
        "gabarit Tasmota : content_start, bouton Menu principal, content_stop")
verifie(cfg != nil, "window.CUVE est du JSON valide")
if (cfg != nil)
    verifie(cfg["volumeMax"] == 6732 && cfg["hauteur"] == 110, "dimensions 110/340/180 : volumeMax 6732 L, hauteur 110")
    verifie(cfg["bibliotheque"] == "echarts-6.1.0" && cfg["extension"] == "liquidfill-3.1.0" && cfg["nom"] == "mesures",
            "cles de cache des deux bibliotheques et nom de l'historique")
end
var pc = string.find(page, "<style>", string.find(page, "</head>"))
var pcss = string.find(page, "#c_zone", pc)
var pfinstyle = string.find(page, "</style>", pcss)
var phtml = string.find(page, "id='c_jauges'")
var pcfg = string.find(page, "window.CUVE=")
var pjs = string.find(page, "// Page /cuve")
verifie(pc > 0 && pcss > pc && pfinstyle > pcss && phtml > pfinstyle && pcfg > phtml && pjs > pcfg,
        "ordre : style (cuve.css), gabarit (cuve.html), window.CUVE, cuve.js")
verifie(string.count(page, "</script>") == 2 && string.find(page, "<script>", pcfg + 20) > 0, "deux balises </script> : configuration, puis cuve.js")
verifie(string.find(page, "</", pcfg) == string.find(page, "</script>", pcfg), "rien de ferme entre window.CUVE et le premier </script>")
verifie(size(journal) > avant && journal[-1][1] == LOG_LEVEL_DEBUG && journal[-1][2] == "serveurWeb" && string.find(journal[-1][0], "CUVE_PAGE:") == 0,
        "une ligne CUVE_PAGE en debug, cible serveurWeb")

cfg = configDe(route({}, {}, "page_vide.html"))
verifie(cfg != nil && cfg["volumeMax"] == 1000 && cfg["hauteur"] == 100, "dimensions {} : volumeMax 1000, hauteur 100")
cfg = configDe(route(nil, {}, "page_nil.html"))
verifie(cfg != nil && cfg["volumeMax"] == 1000 && cfg["hauteur"] == 100, "dimensions nil : volumeMax 1000, hauteur 100")
cfg = configDe(route({"hauteur": "abc", "longueur": -3, "largeur": nil}, {}, "page_invalide.html"))
verifie(cfg != nil && cfg["volumeMax"] == 1000 && cfg["hauteur"] == 100, "dimensions invalides : volumeMax 1000, hauteur 100")
cfg = configDe(route({"hauteur": 50, "longueur": 100}, {}, "page_partielle.html"))
verifie(cfg != nil && cfg["volumeMax"] == 500 && cfg["hauteur"] == 50, "largeur absente : 100 par defaut (50x100x100 = 500 L)")

# Echelles du cadran des tensions : window.CUVE.sonde
print("3b. Echelles du cadran des tensions (window.CUVE.sonde)")
var SONDE = {"rapport": 3.03, "entreeMax_V": 3.3, "sondeMax_V": 10.0}
cfg = configDe(route(DIM, {}, "page_sans_sonde.html", nil))
verifie(cfg != nil && cfg.find("sonde") == nil && string.find(lisFichier(SORTIE + "/page_sans_sonde.html"), "\"sonde\":null") > 0, "route(dim, nil) : window.CUVE.sonde = null")
cfg = configDe(route(DIM, {}, "page_sonde_invalide.html", {"entreeMax_V": 0}))
verifie(cfg != nil && cfg.find("sonde") == nil, "map invalide {entreeMax_V: 0} : sonde null")
cfg = configDe(route(DIM, {}, "page_sonde.html", SONDE))
verifie(cfg != nil && isinstance(cfg.find("sonde"), map) && cfg["sonde"]["entreeMax_V"] == 3.3 && cfg["sonde"]["sondeMax_V"] == 10 && cfg["sonde"]["rapport"] > 3.02 && cfg["sonde"]["rapport"] < 3.04,
        "map valide : gardee telle quelle dans window.CUVE.sonde")
var S = cuvePageFonctions.sonde
verifie(S(SONDE) == SONDE && S(nil) == nil && S("x") == nil && S([1]) == nil, "sonde() : map valide rendue, nil / chaine / liste : nil")
verifie(S({"entreeMax_V": 3.3}) == nil && S({"sondeMax_V": 10}) == nil && S({"entreeMax_V": 3.3, "sondeMax_V": 0}) == nil && S({"entreeMax_V": -1, "sondeMax_V": 10}) == nil
        && S({"entreeMax_V": "3.3", "sondeMax_V": 10}) == nil && S({"entreeMax_V": nil, "sondeMax_V": 10}) == nil, "sonde() : cle absente, nulle, negative ou mal typee : nil")
verifie(S({"entreeMax_V": 3, "sondeMax_V": 10}) != nil, "sonde() : entiers acceptes")
cfg = configDe(route(DIM, {}, "page_sonde_json.html", SONDE))
verifie(string.count(lisFichier(SORTIE + "/page_sonde_json.html"), "</script>") == 2, "page avec sonde : toujours deux </script>")

# Historique sans instance : nom vide (la page le signale) ; nom contenant </script> : echappe
var nomsNormal = historiqueFonctions.nomsInstances
historiqueFonctions.nomsInstances = def () return [] end
cfg = configDe(route(DIM, {}, "page_sans_nom.html"))
verifie(cfg != nil && cfg["nom"] == "", "aucune instance d'historique : nom vide")
historiqueFonctions.nomsInstances = def () return ["a</script><b>"] end
var pageEch = route(DIM, {}, "page_echappee.html")
var debEch = string.find(pageEch, "window.CUVE=")
var blocEch = pageEch[debEch .. string.find(pageEch, ";</script>", debEch) - 1]
verifie(string.find(blocEch, "</") < 0 && string.find(blocEch, "a<\\/script><b>") > 0, "'</' du nom echappe dans window.CUVE")
historiqueFonctions.nomsInstances = nomsNormal

# ---- 4. Routes des cartes ------------------------------------------------------------------------
print("4. Route /cuve du maitre P4 (CONTROLE_GARAGE du depot, persist reel)")
var fp = open("data/garage/tasmota32p4-serveur-modbus/_persist.json", "r")
var persistP4 = json.load(fp.read())
fp.close()
modules = persistP4["modules"]
modules["garage"]["logs"]["nbLogsFiles"] = 0      # pas de rotation de fichiers de logs sous banc
diverses = {}
drivers = persistP4["drivers"]
pilotes = []
charge("data/garage/tasmota32p4-serveur-modbus/controleGarage.be")
var p4 = pilotes[0]
p4.web_add_handler()
verifie(routes.contains("/cuve") && routes["/cuve"][1] == webserver.HTTP_GET, "web_add_handler declare GET /cuve")
var ana = modules["garage"]["environnement"]["analogiques"]
verifie(ana["analogique1"]["idModBus"] == 1 && ana["analogique1"]["dimensions"]["hauteur"] == 110, "(controle) le persist reel porte l'analogique 1 : 110/340/180")
cfg = configDe(sert({}, def () routes["/cuve"][0]() end, "page_p4.html"))
verifie(cfg != nil && cfg["volumeMax"] == 6732 && cfg["hauteur"] == 110, "GET /cuve : dimensions de l'analogique 1 du persist (6732 L, 110 cm)")
# Les dimensions sont celles de l'analogique d'idModBus 1 relie a un esclave ModBus, pas d'un autre
ana["analogique1"]["dimensions"] = {"hauteur": 200, "longueur": 100, "largeur": 100}
ana["analogique2"]["dimensions"] = {"hauteur": 10, "longueur": 10, "largeur": 10}
cfg = configDe(sert({}, def () p4.pageCuve() end, "page_p4_b.html"))
verifie(cfg != nil && cfg["volumeMax"] == 2000, "dimensions modifiees dans l'analogique 1 : suivies (2000 L), pas celles de l'analogique 2")
ana["analogique1"]["virtuel"] = "I2C_ADS1115"
cfg = configDe(sert({}, def () p4.pageCuve() end, "page_p4_c.html"))
verifie(cfg != nil && cfg["volumeMax"] == 1000 && cfg["hauteur"] == 100, "analogique 1 non relie a un esclave ModBus : dimensions par defaut")
ana["analogique1"]["virtuel"] = "ModBus_TasmotaSlaveModBus1"
ana["analogique1"]["idModBus"] = 2
cfg = configDe(sert({}, def () p4.pageCuve() end, "page_p4_d.html"))
verifie(cfg != nil && cfg["volumeMax"] == 1000, "aucun analogique d'idModBus 1 : dimensions par defaut")
webserver.privilegie = false
sortie = sert({}, def () p4.pageCuve() end, "page_p4_refus.txt")
webserver.privilegie = true
verifie(webserver.code == nil && webserver.envois == 0 && sortie == "", "route P4, acces non privilegie : rien n'est envoye")

print("4b. Tension de la sonde recue de la cuve par ModBus (CONTROLE_GARAGE.tensionSonde, registre 4708)")
var a2 = ana["analogique2"]
verifie(a2["idModBus"] == 5 && a2["activation"] == "ON" && a2["virtuel"] == "ModBus_TasmotaSlaveModBus1", "(controle) persist reel : analogique2 = idModBus 5 de l'esclave cuve")
a2["value"] = 6800
a2["etatConstate"] = "valide"
var tP4 = p4.tensionSonde()
verifie(tP4 != nil && (tP4 - 6.8 < 0.000001) && (6.8 - tP4 < 0.000001), "6800 mV recus -> 6,8 V (" + str(tP4) + ")")
a2["etatConstate"] = "defaillant"
verifie(p4.tensionSonde() == nil, "sentinelle de l'esclave (etatConstate defaillant) -> nil, pas l'ancienne valeur")
a2["etatConstate"] = "valide"
a2["activation"] = "OFF"
verifie(p4.tensionSonde() == nil, "entree desactivee -> nil")
a2["activation"] = "ON"

print("5. Route /cuve de la cuve (CAPTEURS_CUVE : methodes isolees de controleCuve.be)")
var texteCuve = lisFichier("data/garage/tasmota32s3-capteurs-cuve-modbus/controleCuve.be")
var debM = string.find(texteCuve, "    def web_add_handler()")
var finM = string.find(texteCuve, "cuvePageFonctions.route(", debM)
verifie(debM > 0 && finM > debM, "(controle) methodes web_add_handler et pageCuve retrouvees dans le texte")
var finM2 = string.find(texteCuve, "    end", finM)
var classeCuve = compile("class CUVE_ISOLEE\n" + texteCuve[debM .. finM2 + 6] + "\nend\nreturn CUVE_ISOLEE")()
var cuve = classeCuve()
routes = {}
cuve.web_add_handler()
verifie(routes.contains("/cuve") && routes["/cuve"][1] == webserver.HTTP_GET, "web_add_handler declare GET /cuve")
fp = open("data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json", "r")
modules = json.load(fp.read())["modules"]
fp.close()
cfg = configDe(sert({}, def () routes["/cuve"][0]() end, "page_cuve.html"))
verifie(cfg != nil && cfg["volumeMax"] == 6732 && cfg["hauteur"] == 110, "GET /cuve : dimensions du bloc modules.cuve.dimensions (6732 L, 110 cm)")
modules["cuve"].remove("dimensions")
cfg = configDe(sert({}, def () cuve.pageCuve() end, "page_cuve_b.html"))
verifie(cfg != nil && cfg["volumeMax"] == 1000 && cfg["hauteur"] == 100, "bloc dimensions absent : dimensions par defaut")

print(echecs == 0 ? "BANC_CUVE_PAGE: OK" : "BANC_CUVE_PAGE: ECHEC (" + str(echecs) + ")")
