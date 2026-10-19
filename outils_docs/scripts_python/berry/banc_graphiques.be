# Banc de test Berry des graphiques de l'historique (2026-10-18) : data/fs/graphiquesFonctions.be (envoi
# d'ECharts compresse par morceaux, page /graphiques, URL Grafana) et le filtre d'historique du maitre P4
# (data/garage/tasmota32p4-serveur-modbus/controleGarage.be : faux zeros de la cuve -> nil).
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python, qui ajoute le rendu de la page dans Chrome sans interface :
#     python outils_docs/scripts_python/berry/banc_graphiques.py
# Ou directement, DEPUIS LA RACINE DU DEPOT (dossier_sortie : ou ecrire ECharts recu et la page) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_graphiques.be <dossier_sortie> [dossier_sources]
#
# Les VRAIS fichiers sont COMPILES depuis leur texte, pas importes : berry.exe cherche un module d'abord
# dans le dossier du fichier qui l'importe, et data/fs/ fournirait alors les vrais historiqueFonctions et
# gestionFileFolder a la place des bouchons (bouchons_berry/graphiques/).
# Portee : la logique Berry. Le rendu de la page (graphiques.js, ECharts) est juge par l'enveloppe Python.
# La derniere ligne, BANC_GRAPHIQUES: OK|ECHEC, est lue par l'enveloppe pour son code de sortie.
import global
import sys
import string
import json

if (size(global._argv) < 2)
    print("Usage : berry.exe banc_graphiques.be <dossier_sortie> [dossier_sources]")
    print("BANC_GRAPHIQUES: ECHEC (argument manquant)")
    return
end
var SORTIE = global._argv[1]
var SOURCES = size(global._argv) > 2 ? global._argv[2] : "data/fs"
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/graphiques")

# ---- Globaux du firmware bouchonnes -------------------------------------------------------------
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
class Driver end
class TASMOTA_BOUCHON
    var topic
    def init() self.topic = "garage" end
    def yield() end
    def add_cron() end
    def add_cmd() end
    def add_driver() end
    def add_rule() end
    def cmd(c, muet) return (c == "Topic" ? {"Topic": self.topic} : nil) end
end
tasmota = TASMOTA_BOUCHON()
var journal = []
class LOG_BOUCHON def log(msg, niveau, cible) journal.push([msg, niveau, cible]) end end
logFonctions = LOG_BOUCHON()

def charge(chemin)
    var f = open(chemin, "r")
    var source = f.read()
    f.close()
    return compile(source)()
end

var echecs = 0
def verifie(condition, nom)
    print((condition ? "  OK     " : "  ECHEC  ") + nom)
    if (!condition)    echecs += 1    end
end
# Premiere ligne GRAPHIQUES_ERREUR en erreur journalisee depuis l'indice 'depuis', ou nil
def dernierErreur(depuis)
    for i: depuis .. size(journal) - 1
        if (journal[i][1] == LOG_LEVEL_ERREUR && string.find(journal[i][0], "GRAPHIQUES_ERREUR:") == 0)    return journal[i]    end
    end
    return nil
end

import webserver
import historiqueFonctions
import gestionFileFolder

# Configuration reelle de la page : bloc diverses.historique et drivers (noms des esclaves ModBus) du persist du
# maitre P4, reglages de la page dans son graphiques.json
var fp = open("data/garage/tasmota32p4-serveur-modbus/_persist.json", "r")
var persistP4 = json.load(fp.read())
fp.close()
historiqueFonctions.config = persistP4["diverses"]["historique"]
drivers = persistP4["drivers"]

var graphiquesFonctions = charge(SOURCES + "/graphiquesFonctions.be")
var REGLAGES_P4 = "data/garage/tasmota32p4-serveur-modbus/graphiques.json"
graphiquesFonctions.FICHIER_REGLAGES = REGLAGES_P4

# ---- 1. Envoi d'ECharts compresse par morceaux -------------------------------------------------
print("1. /graphiques?f=echarts.js.gz")
verifie(size(graphiquesFonctions.FICHIERS) == 1, "un seul fichier servi : echarts.js.gz (uPlot retire)")
graphiquesFonctions.FICHIERS["echarts.js.gz"][0] = "data/sd/js/echarts.min.js.gz"
webserver.raz({"f": "echarts.js.gz"})
webserver.sortie = open(SORTIE + "/echarts_recu.js.gz", "wb")
graphiquesFonctions.route()
webserver.sortie.close()
verifie(webserver.code == 200 && webserver.mime == "application/octet-stream", "echarts.js.gz : 200 application/octet-stream")
verifie(webserver.envois >= 100 && webserver.ferme, "echarts.js.gz : envoye en morceaux de 2 Ko (" + str(webserver.envois) + "), reponse fermee")
webserver.raz({"f": "uplot.js"})
webserver.sortie = open(SORTIE + "/ancien.txt", "wb")
graphiquesFonctions.route()
webserver.sortie.close()
verifie(webserver.code == nil && webserver.debut == "Graphiques", "ancien nom uplot.js : aucun fichier servi, la page est renvoyee")

print("2. Fichier absent, acces refuse")
graphiquesFonctions.FICHIERS["echarts.js.gz"][0] = "data/sd/js/nexiste_pas.js.gz"
webserver.raz({"f": "echarts.js.gz"})
webserver.sortie = open(SORTIE + "/absent.txt", "wb")
var avant = size(journal)
graphiquesFonctions.route()
webserver.sortie.close()
verifie(webserver.code == 404, "fichier absent : 404")
verifie(size(journal) == avant + 1 && journal[-1][1] == LOG_LEVEL_ERREUR && string.find(journal[-1][0], "GRAPHIQUES_ERREUR:") == 0
        && journal[-1][2] == "serveurWeb", "fichier absent : une ligne GRAPHIQUES_ERREUR en erreur, cible serveurWeb")
# Exception en plein envoi (connexion perdue, flash illisible) : fichier ET reponse fermes, erreur journalisee
graphiquesFonctions.FICHIERS["echarts.js.gz"][0] = "data/sd/js/echarts.min.js.gz"
webserver.raz({"f": "echarts.js.gz"})
webserver.sortie = open(SORTIE + "/exception.txt", "wb")
var envoiNormal = webserver.content_send
webserver.content_send = def (x) raise "io_error", "connexion perdue" end
avant = size(journal)
graphiquesFonctions.route()
webserver.content_send = envoiNormal
webserver.sortie.close()
verifie(webserver.code == 200 && webserver.ferme && size(journal) == avant + 1 && journal[-1][1] == LOG_LEVEL_ERREUR,
        "exception en plein envoi : reponse fermee quand meme, une erreur journalisee")
webserver.raz({"f": "echarts.js.gz"})
webserver.privilegie = false
webserver.sortie = open(SORTIE + "/refuse.txt", "wb")
graphiquesFonctions.route()
webserver.sortie.close()
webserver.privilegie = true
verifie(webserver.code == nil && webserver.envois == 0, "acces non privilegie : rien n'est envoye")

# ---- 3. URL Grafana -----------------------------------------------------------------------------
print("3. URL Grafana")
verifie(graphiquesFonctions.urlGrafana({"grafana": "http://pi:3000/d/x?var-appareil=%topic%"}) == "http://pi:3000/d/x?var-appareil=garage",
        "%topic% remplace par le topic de la carte")
tasmota.topic = "jardin/cuve"
verifie(graphiquesFonctions.urlGrafana({"grafana": "http://pi/d/x?var-appareil=%topic%"}) == "http://pi/d/x?var-appareil=jardin/cuve",
        "topic a plusieurs niveaux (jardin/cuve)")
tasmota.topic = "garage"
verifie(graphiquesFonctions.urlGrafana({"grafana": "http://pi/d/fixe"}) == "http://pi/d/fixe", "URL sans %topic% inchangee")
verifie(graphiquesFonctions.urlGrafana({}) == "", "pas de cle grafana : chaine vide (pas de bouton)")

# ---- 4. Page /graphiques ------------------------------------------------------------------------
print("4. Page /graphiques (ecrite pour le rendu dans Chrome)")
webserver.raz({})
webserver.sortie = open(SORTIE + "/page.html", "wb")
graphiquesFonctions.route()
webserver.sortie.close()
var fpage = open(SORTIE + "/page.html", "r")
var page = fpage.read()
fpage.close()
verifie(webserver.debut == "Graphiques" && webserver.bouton == webserver.BUTTON_MAIN && webserver.termine,
        "gabarit Tasmota : content_start, bouton Menu principal, content_stop")
var debutConfig = string.find(page, "window.GRAPHIQUES=")
var finConfig = string.find(page, ";</script>", debutConfig)
var config = (debutConfig >= 0 && finConfig > 0 ? json.load(page[debutConfig + 18 .. finConfig - 1]) : nil)
verifie(config != nil, "window.GRAPHIQUES est du JSON valide")
if (config != nil)
    verifie(config["bibliotheque"] == "echarts-6.1.0" && config["nom"] == "mesures", "cle de cache d'ECharts et nom de l'historique")
    verifie(config["grafana"] == "http://192.168.0.5:3000/d/historique-cuve?var-appareil=garage", "URL Grafana du persist, topic remplace")
    verifie(config["affichage"].find("sensorsCuve.niveauCuve.tauxRemplissage", {}).find("facteur") == 100,
            "reglages 'affichage' de graphiques.json transmis (series nommees par leur chemin)")
    verifie(json.dump(config["groupes"]) == json.dump({"Cuve": ["sensorsCuve.niveauCuve"]}), "groupe « Cuve » de graphiques.json transmis")
    verifie(config["esclaves"].find("TasmotaSlaveModBus1") == "Capteurs Cuve ModBus", "noms des esclaves ModBus tires du persist")
    verifie(isinstance(config["compteurs"], map), "reglages des compteurs du persist transmis (unites)")
    verifie(config["rafraichissement"] == 60, "periode de relecture par defaut : 60 s")
    verifie(config["direct"] == 10, "cadence du temps reel par defaut : 10 s")
end
verifie(string.find(page, "// graphiques.js") > 0 && string.find(page, "id='g_graphiques'") > 0 && string.find(page, "#g_zone{") > 0,
        "gabarit /sd/html/graphiques.html, style /sd/css/graphiques.css et graphiques.js inclus")
verifie(string.find(page, "#g_zone{") > string.find(page, "<style>", string.find(page, "</head>")) , "style envoye entre <style> et </style>")

verifie(graphiquesFonctions.periode(120) == 120 && graphiquesFonctions.periode(3) == 10 && graphiquesFonctions.periode("x") == 60
        && graphiquesFonctions.periode(nil) == 60, "periode de relecture : bornee a 10 s, 60 s si absente ou mal typee")
verifie(graphiquesFonctions.cadenceDirect(0) == 0 && graphiquesFonctions.cadenceDirect(2) == 2 && graphiquesFonctions.cadenceDirect(60) == 60
        && graphiquesFonctions.cadenceDirect(10) == 10, "cadence du temps reel : valeurs de la liste de la page (0 = arret) acceptees")
verifie(graphiquesFonctions.cadenceDirect(7) == 10 && graphiquesFonctions.cadenceDirect("5") == 10 && graphiquesFonctions.cadenceDirect(nil) == 10
        && graphiquesFonctions.cadenceDirect(-1) == 10, "cadence hors liste, mal typee ou absente : 10 s")

# Reglages de la page absents ou illisibles : page servie quand meme, erreur journalisee si illisibles
def pageAvecReglages(chemin, sortie)
    graphiquesFonctions.FICHIER_REGLAGES = chemin
    webserver.raz({})
    webserver.sortie = open(SORTIE + "/" + sortie, "wb")
    graphiquesFonctions.route()
    webserver.sortie.close()
    graphiquesFonctions.FICHIER_REGLAGES = REGLAGES_P4
    var f = open(SORTIE + "/" + sortie, "r")
    var texte = f.read()
    f.close()
    var d = string.find(texte, "window.GRAPHIQUES=")
    return json.load(texte[d + 18 .. string.find(texte, ";</script>", d) - 1])
end
avant = size(journal)
var sansReglages = pageAvecReglages(SORTIE + "/absent.json", "page_sans_reglages.html")
verifie(webserver.termine && size(sansReglages["affichage"]) == 0 && size(sansReglages["groupes"]) == 0 && size(journal) == avant + 1,
        "graphiques.json absent : page servie, affichage et groupes vides, aucune erreur")
var fr = open(SORTIE + "/illisible.json", "w")
fr.write("{pas du json")
fr.close()
avant = size(journal)
var illisible = pageAvecReglages(SORTIE + "/illisible.json", "page_illisible.html")
verifie(webserver.termine && size(illisible["affichage"]) == 0 && dernierErreur(avant) != nil,
        "graphiques.json illisible : page servie, une ligne GRAPHIQUES_ERREUR en erreur")

# Persist et reglages mal formes : la page est servie, avec des objets vides
fr = open(SORTIE + "/mal_types.json", "w")
fr.write(json.dump({"affichage": [], "groupes": "Cuve"}))
fr.close()
var driversReels = drivers
drivers = {"ModBus": "ON"}
var malTypes = nil
try malTypes = pageAvecReglages(SORTIE + "/mal_types.json", "page_mal_types.html") except .. as e, m print("    exception : " + str(e) + " " + str(m)) end
drivers = driversReels
verifie(malTypes != nil && webserver.termine && isinstance(malTypes["affichage"], map) && isinstance(malTypes["groupes"], map)
        && size(malTypes["esclaves"]) == 0, "reglages mal types et drivers.ModBus pas une map : page servie, objets vides, pas d'exception")

# Un libelle des reglages contenant </script> ne doit pas fermer le script de configuration
fr = open(SORTIE + "/echappe.json", "w")
fr.write(json.dump({"affichage": {"sensorsCuve.niveauCuve.volume": {"libelle": "Volume</script><b>"}}}))
fr.close()
pageAvecReglages(SORTIE + "/echappe.json", "page_echappee.html")
fpage = open(SORTIE + "/page_echappee.html", "r")
var pageEchappee = fpage.read()
fpage.close()
var bloc = pageEchappee[string.find(pageEchappee, "window.GRAPHIQUES=") .. string.find(pageEchappee, ";</script>") - 1]
verifie(string.find(bloc, "</") < 0 && string.find(bloc, "Volume<\\/script>") > 0, "'</' du persist echappe dans window.GRAPHIQUES")

# ---- 5. Filtre d'historique du maitre P4 --------------------------------------------------------
print("5. Filtre des faux zeros de la cuve (controleGarage.filtreHistorique)")
var ana = {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus", "idModBus": 1}
var th = {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus1", "idModBus": 1, "type": 1312}
diverses = {"historique": {"activation": "ON"}}
modules = {"garage": {"environnement": {"analogiques": {"name": "Cuve", "niveau": ana},
                                        "thermometres": {"affichageWebSensor": "OFF", "thermometre1": th}}}}
charge("data/garage/tasmota32p4-serveur-modbus/controleGarage.be")
verifie(size(historiqueFonctions.filtres) == 1, "filtre enregistre aupres de l'historique")
var chemins = ["ESP32.Temperature", "sensorsCuve.niveauCuve.hauteurEau", "sensorsCuve.valeursAnalogiques.valeurCapteurHauteur", "DS18B20.Temperature"]
def essai(etatNiveau, etatThermo, attendu, nom)
    if (etatNiveau == nil)    ana.remove("etatConstate")    else    ana["etatConstate"] = etatNiveau    end
    if (etatThermo == nil)    th.remove("etatConstate")     else    th["etatConstate"] = etatThermo     end
    var v = [29.4, 0.0, 0.0, 0.0]
    historiqueFonctions.filtres[0](chemins, v)
    verifie(str(v) == str(attendu), nom + " -> " + str(v))
end
essai("valide", "valide", [29.4, 0.0, 0.0, 0.0], "niveau et thermometre valides : tout garde")
essai("defaillant", "valide", [29.4, nil, nil, 0.0], "niveau defaillant : sensorsCuve.* a nil")
essai("valide", "defaillant", [29.4, 0.0, 0.0, nil], "thermometre defaillant : DS18B20.* a nil")
essai("inconnu", "inconnu", [29.4, nil, nil, nil], "esclave muet (inconnu) : tout ce qui vient de la cuve a nil")
essai(nil, nil, [29.4, nil, nil, nil], "pas encore relu depuis le demarrage : a nil")
ana["activation"] = "OFF"
essai("valide", "valide", [29.4, nil, nil, 0.0], "entree analogique desactivee : niveau a nil")
ana["activation"] = "ON"
th["type"] = 1216
essai("valide", "valide", [29.4, 0.0, 0.0, nil], "pas de DS18B20 (1312) parmi les thermometres : DS18B20.* a nil")
modules = {}
var sansGarage = [29.4, 0.0, 0.0, 0.0]
var leve = false
try historiqueFonctions.filtres[0](chemins, sansGarage) except .. leve = true end
verifie(!leve && str(sansGarage) == str([29.4, nil, nil, nil]), "modules sans bloc garage : pas d'exception (la mesure de la minute est gardee)")

# ---- Bouton « Historique (Grafana) » de l'accueil (controleWeb.be, toutes les cartes, A7) --------------
# Globales lues par controleWeb.be, declarees AVANT de le compiler (sinon « undeclared »)
class CONTROLE_GENERAL_BOUCHON var nbIOActivesJSON def init() self.nbIOActivesJSON = {"WS2812": {"actives": {}, "reels": {}}} end end
controleGeneral = CONTROLE_GENERAL_BOUCHON()
boolMute = true
serveur = {}
diverses = {}
charge(SOURCES + "/controleWeb.be")
var accueilWeb = global.controleWeb.CONTROLE_WEB()   # global : controleWeb est cree par le fichier charge
def accueil(div)
    diverses = div
    var f = open(SORTIE + "/accueil.html", "wb")
    webserver.sortie = f
    webserver.raz()
    var leve = nil
    try accueilWeb.web_add_main_button() except .. as e, m leve = str(e) + " : " + str(m) end
    f.close()
    f = open(SORTIE + "/accueil.html", "r")
    var html = f.read()
    f.close()
    return (leve != nil ? "EXCEPTION " + leve : html)
end
def persistReel(chemin)
    var fp = open(chemin, "r")
    var d = json.load(fp.read())["diverses"]
    fp.close()
    return d
end
var URL_TEST = "http://pi:3000/d/x?var-appareil=%topic%"
tasmota.topic = "cave/serveur-rly-cave"
var html = accueil({"historique": {"grafana": URL_TEST}})
verifie(string.find(html, "Historique (Grafana)") > 0 &&
        string.find(html, "window.open(\"http://pi:3000/d/x?var-appareil=cave/serveur-rly-cave\",\"_blank\",\"noopener\")") > 0,
        "carte sans historique local + cle grafana : bouton, topic remplace")
verifie(string.find(accueil({"historique": {"activation": "OFF", "grafana": URL_TEST}}), "Historique (Grafana)") > 0,
        "historique a OFF + cle grafana : bouton")
verifie(accueil({"historique": {"activation": "ON", "grafana": URL_TEST}}) == "",
        "historique local actif : pas de bouton (le bouton Graphiques y mene deja)")
verifie(accueil({"historique": {"activation": "OFF"}}) == "" && accueil({}) == "" && accueil({"historique": {"grafana": ""}}) == "",
        "pas de cle grafana (ou vide) : rien d'envoye")
verifie(accueil(nil) == "", "globale diverses absente : rien d'envoye, pas d'exception")
verifie(accueil({"historique": nil}) == "" && accueil({"historique": "x"}) == "",
        "bloc historique null ou pas une map : rien d'envoye, l'accueil n'est pas casse")
tasmota.topic = "garage"
html = accueil({"historique": {"grafana": "http://pi/d/x?a='b'&c=\"d\"<e"}})
var debutAttr = string.find(html, "onclick='")
verifie(debutAttr > 0 && string.count(html, "'") == 2 && string.find(html, "<e") < 0 && string.find(html, "%27b%27") > 0,
        "guillemet simple et chevron de l'URL neutralises dans l'attribut onclick")
verifie(accueil(persistReel("data/garage/tasmota32p4-serveur-modbus/_persist.json")) == "" &&
        accueil(persistReel("data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json")) == "",
        "persists reels du P4 et de la cuve (historique actif) : pas de bouton en double")
verifie(accueil(persistReel("data/cave/tasmota32-serveur-rly/_persist.json")) == "" &&
        accueil(persistReel("data/bureau/tasmota32-interrupteur-differentiel/_persist.json")) == "",
        "persists reels des ESP32 classiques (pas de cle grafana, decision du 2026-10-18) : pas de bouton")

print(echecs == 0 ? "BANC_GRAPHIQUES: OK" : "BANC_GRAPHIQUES: ECHEC (" + str(echecs) + ")")
