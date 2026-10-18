# Banc de test Berry des graphiques de l'historique (2026-10-18) : data/fs/graphiquesFonctions.be (envoi
# d'uPlot par morceaux, page /graphiques, URL Grafana) et le filtre d'historique du maitre P4
# (data/garage/tasmota32p4-serveur-modbus/controleGarage.be : faux zeros de la cuve -> nil).
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python, qui ajoute le rendu de la page dans Chrome sans interface :
#     python outils_docs/scripts_python/berry/banc_graphiques.py
# Ou directement, DEPUIS LA RACINE DU DEPOT (dossier_sortie : ou ecrire uPlot recu et la page) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_graphiques.be <dossier_sortie> [dossier_sources]
#
# Les VRAIS fichiers sont COMPILES depuis leur texte, pas importes : berry.exe cherche un module d'abord
# dans le dossier du fichier qui l'importe, et data/fs/ fournirait alors les vrais historiqueFonctions et
# gestionFileFolder a la place des bouchons (bouchons_berry/graphiques/).
# Portee : la logique Berry. Le rendu de la page (graphiques.js, uPlot) est juge par l'enveloppe Python.
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

import webserver
import historiqueFonctions
import gestionFileFolder

# Configuration reelle de la page : bloc diverses.historique du persist du maitre P4
var fp = open("data/garage/tasmota32p4-serveur-modbus/_persist.json", "r")
historiqueFonctions.config = json.load(fp.read())["diverses"]["historique"]
fp.close()

var graphiquesFonctions = charge(SOURCES + "/graphiquesFonctions.be")

# ---- 1. Envoi d'uPlot par morceaux --------------------------------------------------------------
print("1. /graphiques?f=uplot.js et uplot.css")
graphiquesFonctions.FICHIERS["uplot.js"][0] = "data/sd/js/uPlot.iife.min.js"
graphiquesFonctions.FICHIERS["uplot.css"][0] = "data/sd/css/uPlot.min.css"
webserver.raz({"f": "uplot.js"})
webserver.sortie = open(SORTIE + "/uplot_recu.js", "wb")
graphiquesFonctions.route()
webserver.sortie.close()
verifie(webserver.code == 200 && webserver.mime == "application/javascript", "uplot.js : 200 application/javascript")
verifie(webserver.envois >= 20 && webserver.ferme, "uplot.js : envoye en morceaux de 2 Ko (" + str(webserver.envois) + "), reponse fermee")
webserver.raz({"f": "uplot.css"})
webserver.sortie = open(SORTIE + "/uplot_recu.css", "wb")
graphiquesFonctions.route()
webserver.sortie.close()
verifie(webserver.code == 200 && webserver.mime == "text/css", "uplot.css : 200 text/css")

print("2. Fichier absent, acces refuse")
graphiquesFonctions.FICHIERS["uplot.css"][0] = "data/sd/css/nexiste_pas.css"
webserver.raz({"f": "uplot.css"})
webserver.sortie = open(SORTIE + "/absent.txt", "wb")
var avant = size(journal)
graphiquesFonctions.route()
webserver.sortie.close()
verifie(webserver.code == 404, "fichier absent : 404")
verifie(size(journal) == avant + 1 && journal[-1][1] == LOG_LEVEL_ERREUR && string.find(journal[-1][0], "GRAPHIQUES_ERREUR:") == 0
        && journal[-1][2] == "serveurWeb", "fichier absent : une ligne GRAPHIQUES_ERREUR en erreur, cible serveurWeb")
# Exception en plein envoi (connexion perdue, flash illisible) : fichier ET reponse fermes, erreur journalisee
graphiquesFonctions.FICHIERS["uplot.css"][0] = "data/sd/css/uPlot.min.css"
webserver.raz({"f": "uplot.css"})
webserver.sortie = open(SORTIE + "/exception.txt", "wb")
var envoiNormal = webserver.content_send
webserver.content_send = def (x) raise "io_error", "connexion perdue" end
avant = size(journal)
graphiquesFonctions.route()
webserver.content_send = envoiNormal
webserver.sortie.close()
verifie(webserver.code == 200 && webserver.ferme && size(journal) == avant + 1 && journal[-1][1] == LOG_LEVEL_ERREUR,
        "exception en plein envoi : reponse fermee quand meme, une erreur journalisee")
webserver.raz({"f": "uplot.js"})
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
    verifie(config["uplot"] == "uPlot-1.6.30" && config["nom"] == "mesures", "cle de cache uPlot et nom de l'historique")
    verifie(config["grafana"] == "http://192.168.0.5:3000/d/historique-cuve?var-appareil=garage", "URL Grafana du persist, topic remplace")
    verifie(config["affichage"].find("tauxRemplissage", {}).find("facteur") == 100, "reglages 'affichage' du persist transmis")
end
verifie(string.find(page, "// graphiques.js") > 0 && string.find(page, "g_trace") > 0, "graphiques.js et la zone du trace inclus")
# Un libelle du persist contenant </script> ne doit pas fermer le script de configuration
historiqueFonctions.config["affichage"]["volume"]["libelle"] = "Volume</script><b>"
webserver.raz({})
webserver.sortie = open(SORTIE + "/page_echappee.html", "wb")
graphiquesFonctions.route()
webserver.sortie.close()
historiqueFonctions.config["affichage"]["volume"]["libelle"] = "Volume"
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

print(echecs == 0 ? "BANC_GRAPHIQUES: OK" : "BANC_GRAPHIQUES: ECHEC (" + str(echecs) + ")")
