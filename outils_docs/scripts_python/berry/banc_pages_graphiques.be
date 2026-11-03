# Banc de test Berry du moteur commun des pages de graphiques (2026-11-03) : data/fs/pagesGraphiques.be
# (validation de la description, index au demarrage, boutons, route /pages : page, valeurs, sources, liquidfill).
# -----------------------------------------------------------------------------------------------
# Lancer via son enveloppe Python (code de sortie, comparaison de l'extension liquidfill recue) :
#     python outils_docs/scripts_python/berry/banc_pages_graphiques.py
# Ou directement, DEPUIS LA RACINE DU DEPOT (dossier_sortie : fichiers produits ; dossier_sources : contient
# pagesGraphiques.be, data/fs par defaut ; le temoin du banc l'oriente vers une COPIE mutee) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_pages_graphiques.be <dossier_sortie> [dossier_sources]
#
# Les modules (moteur et validation) sont charges COMME SOLIDIFIES : compile en portee globale (comme le solidifieur), puis sa globale et les noms
# globaux de ses fonctions et de sa classe sont retires (une fois solidifie, ils n'existent pas : piege 12 de
# outils_docs/SOLIDIFICATION_BERRY.md, lecons du 2026-10-31). L'import passe ensuite par init(), comme
# demarrage.charge sur la carte : un init() qui importerait le module deborderait la pile ici aussi.
# La derniere ligne, BANC_PAGES_GRAPHIQUES: OK|ECHEC, est lue par l'enveloppe pour son code de sortie.
import global
import sys
import string
import json
import os
import gc

if (size(global._argv) < 2)
    print("Usage : berry.exe banc_pages_graphiques.be <dossier_sortie> [dossier_sources]")
    print("BANC_PAGES_GRAPHIQUES: ECHEC (argument manquant)")
    return
end
var SORTIE = global._argv[1]
var SOURCES = size(global._argv) > 2 ? global._argv[2] : "data/fs"
var BOUCHONS = "outils_docs/scripts_python/berry/bouchons_berry/pages_graphiques"

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
var echecs = 0
def verifie(condition, nom)
    print((condition ? "  OK     " : "  ECHEC  ") + nom)
    if (!condition)    echecs += 1    end
end

# ---- Globaux du firmware bouchonnes -------------------------------------------------------------
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
class Driver end
var pilotes = []
var CAPTEURS = '{"Time":"2026-11-03T10:00:00","DS18B20":{"Temperature":21.5},"sensorsCuve":{"niveauCuve":{"volume":4174,"etat":"OK"}}}'
class TASMOTA_BOUCHON
    def yield() end
    def add_driver(d) pilotes.push(d) end
    def read_sensors() return CAPTEURS end
    def rtc() return {"utc": 1792230900} end
end
tasmota = TASMOTA_BOUCHON()
var journal = []
class LOG_BOUCHON def log(msg, niveau, cible) journal.push([msg, niveau, cible]) end end
logFonctions = LOG_BOUCHON()
class LOG_MUET def log(msg, niveau, cible) end end
# Nombre de lignes PAGES_GRAPHIQUES_ERREUR journalisees en erreur depuis l'indice 'depuis'
def erreurs(depuis)
    var n = 0
    for i: depuis .. size(journal) - 1
        if (journal[i][1] == LOG_LEVEL_ERREUR && string.find(journal[i][0], "PAGES_GRAPHIQUES_ERREUR:") == 0)    n += 1    end
    end
    return n
end

# ---- Chargement du module, comme solidifie --------------------------------------------------------
# Comme le solidifieur (berry_custom/solidify_all_python.be) : texte compile en portee GLOBALE puis execute, sans init().
# Importe depuis un fichier, ses noms de niveau fichier seraient des locaux captures par ses fonctions et masqueraient
# un appel par nom global (lecon du 2026-10-31) : ici ils sont globaux, puis retires, comme sur la carte.
if (!os.path.exists(SORTIE + "/modules"))    os.mkdir(SORTIE + "/modules")    end
# Les deux modules : le moteur et sa validation (embarques et solidifies ensemble). 'import <nom>' (fonctions des modules,
# demarrage.charge sur la carte) doit rendre CE module et passer par init() : un fichier relais du chemin le rend.
var MODULES = ["pagesGraphiquesValidation", "pagesGraphiques"]
var attendus = 0
for nom: MODULES
    var source = lisFichier(SOURCES + "/" + nom + ".be")
    verifie(string.find(source, "#@ solidify:" + nom + "\n") >= 0 && string.find(source, "var " + nom + " = module(\"" + nom + "\")") >= 0,
            nom + " : directive de solidification et declaration du module presentes")
    attendus += string.count(source, "\ndef " + nom + "_") + 1          # fonctions et module
    global.(".banc_" + nom) = compile(source)()
    ecrisFichier(SORTIE + "/modules/" + nom + ".be", "import global return global.('.banc_" + nom + "')")
end
attendus += 1                                                              # classe PAGES_GRAPHIQUES
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/graphiques")      # webserver, path, gestionFileFolder
sys.path().push(SORTIE + "/modules")

import webserver
import path
import gestionFileFolder
var routes = {}
webserver.on = def (url, f, methode) routes[url] = [f, methode] end
gestionFileFolder.racine = BOUCHONS
path.racine = BOUCHONS

print("1. Noms globaux retires, import (init)")
var retires = 0
for nom: global()
    if (MODULES.find(nom) != nil || nom == "PAGES_GRAPHIQUES" || string.find(nom, "pagesGraphiques_") == 0 || string.find(nom, "pagesGraphiquesValidation_") == 0)
        global.(nom) = nil
        retires += 1
    end
end
verifie(retires == attendus, "noms globaux des modules retires, comme une fois solidifies (" + str(retires) + "/" + str(attendus) + ")")
var PG = nil
var V = nil
try
    import pagesGraphiques as _pg
    import pagesGraphiquesValidation as _v
    PG = _pg
    V = _v
except .. as e, m
    print("  EXCEPTION a l'import : " + str(e) + " " + str(m))
end
verifie(PG != nil && PG.route != nil && PG.route == global.(".banc_pagesGraphiques").route, "import passe par init(), qui rend le module")
verifie(V != nil && V.valide != nil && V.valide == global.(".banc_pagesGraphiquesValidation").valide, "import de la validation")
verifie(size(pilotes) == 1 && classname(pilotes[0]) == "PAGES_GRAPHIQUES", "init() pose UN driver PAGES_GRAPHIQUES")
verifie(size(routes) == 0 && !global.contains(".pagesGraphiques"), "init() ne lit pas la description (demarre() vient de web_add_handler)")
if (PG == nil || V == nil)
    print("BANC_PAGES_GRAPHIQUES: ECHEC (module non charge)")
    return
end
import introspect
var MEMBRES = [introspect.members(PG), introspect.members(V)]

# Rend la reponse d'une requete ; renvoie le texte ecrit (ou "EXCEPTION ...")
def sert(args, appel, nomFichier)
    webserver.raz(args)
    var f = open(SORTIE + "/" + nomFichier, "wb")
    webserver.sortie = f
    var leve = nil
    try appel() except .. as e, m leve = str(e) + " : " + str(m) end
    f.close()
    return leve != nil ? "EXCEPTION " + leve : lisFichier(SORTIE + "/" + nomFichier)
end
var pilote = pilotes[0]
def requete(args, nom)
    return sert(args, def () routes["/pages"][0]() end, nom)
end

# ---- 2. Verdicts : memes que atelier_graphiques_description::valide ------------------------------
print("2. Cas de cas_description.json")
var cas = json.load(lisFichier(BOUCHONS + "/cas_description.json"))
verifie(cas["styles"] == V.STYLES, "STYLES = ceux de l'atelier (" + str(size(V.STYLES)) + ")")
var identiques = 0
for c: cas["cas"]
    var verdict = nil
    try
        verdict = (size(V.valide(c["description"])) == 0)
    except .. as e, m
        print("  EXCEPTION " + c["nom"] + " : " + str(e) + " " + str(m))
    end
    if (verdict == c["valide"])
        identiques += 1
    else
        print("  DIFFERENT " + c["nom"] + " : attendu " + str(c["valide"]) + ", motifs " + str(verdict == nil ? "exception" : V.valide(c["description"])))
    end
end
verifie(identiques == size(cas["cas"]), str(identiques) + "/" + str(size(cas["cas"])) + " cas : meme verdict que l'atelier, sans exception")
var CAS = {}
for c: cas["cas"]    CAS[c["nom"]] = c["description"]    end

# ---- 3. Description absente, tronquee, illisible, invalide ---------------------------------------
print("3. Description inutilisable : aucun bouton, page « Description invalide »")
var FICHIER = SORTIE + "/pages_graphiques.json"
PG.FICHIER = FICHIER
var existeVrai = path.exists
var scenarios = [["absente", nil], ["tronquee", '{"version": 1, "pages": [{"id": "a"'], ["illisible", "ILLISIBLE"],
                 ["invalide", json.dump(CAS["invalide : version 2"])], ["trop gros", nil]]
var gros = ""
for i: 1 .. 400    gros += "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"    end      # 40 000 o
scenarios[4][1] = gros
for s: scenarios
    if (path.exists(FICHIER))    os.remove(FICHIER)    end
    if (s[1] != nil && s[1] != "ILLISIBLE")    ecrisFichier(FICHIER, s[1])    end
    if (s[1] == "ILLISIBLE")    path.exists = def (c) return true end    end      # le fichier « existe » mais ne s'ouvre pas
    var j = size(journal)
    var index = nil
    try index = PG.demarre() except .. as e, m print("  EXCEPTION demarre : " + str(e) + " " + str(m)) end
    var boutons = sert({}, def () pilote.web_add_main_button() end, "boutons_" + s[0] + ".html")
    var page = sert({"p": "a"}, def () PG.route() end, "page_" + s[0] + ".html")
    path.exists = existeVrai
    verifie(index != nil && size(index) == 0 && boutons == "", s[0] + " : demarre() sans exception, index vide, aucun bouton")
    verifie(string.find(page, "Description invalide") >= 0 && webserver.termine && erreurs(j) >= 2, s[0] + " : page « Description invalide » complete, PAGES_GRAPHIQUES_ERREUR journalise")
end
var pageInvalide = lisFichier(SORTIE + "/page_invalide.html")
verifie(string.find(pageInvalide, "version") >= 0, "le motif est affiche (version : doit valoir 1)")

# ---- 4. Description valide : index, boutons, routes ------------------------------------------------
print("4. Index, boutons et route /pages")
var desc = {"version": 1, "pages": [
    {"id": "cuve", "titre": "x", "graphiques": []},
    {"id": "tableau-cuve", "titre": "Cuve <&> garage", "acces": "bouton",
     "graphiques": [{"type": "cadran", "titre": "Volume </script>", "series": ["calc:cuve.manque"], "min": 0, "max": 6732}]},
    {"id": "detail", "titre": "Detail", "acces": "lien", "graphiques": [{"type": "courbe", "titre": "T", "series": ["DS18B20.Temperature"]}]},
    {"id": "defaut", "titre": "Par defaut", "graphiques": [{"type": "aire", "titre": "T", "series": ["DS18B20.Temperature"]}]}],
    "calculees": {"cuve.manque": {"formule": "6732 - sensorsCuve.niveauCuve.volume", "nature": "direct"}}}
verifie(size(V.valide(desc)) >= 2, "description piegee (id reserve cuve, graphiques vide) refusee")
desc["pages"].remove(0)
verifie(size(V.valide(desc)) == 0, "description de travail valide")
ecrisFichier(FICHIER, json.dump(desc))
var j = size(journal)
var sortie = sert({}, def () pilote.web_add_handler() end, "handler.txt")
verifie(routes.contains("/pages") && routes["/pages"][1] == webserver.HTTP_GET, "web_add_handler declare GET /pages")
var index = PG.index()
verifie(size(index) == 3 && index[0] == ["tableau-cuve", "Cuve <&> garage", "bouton"] && index[2][2] == "bouton", "index = [id, titre, acces] (acces par defaut : bouton)")
var boutons = sert({}, def () pilote.web_add_main_button() end, "boutons.html")
verifie(string.count(boutons, "<form action='/pages'") == 2 && string.find(boutons, "value='tableau-cuve'") >= 0 && string.find(boutons, "value='defaut'") >= 0
        && string.find(boutons, "value='detail'") < 0, "deux boutons : les pages a acces bouton seulement")
verifie(string.find(boutons, "Cuve &lt;&amp;&gt; garage") >= 0, "titre du bouton echappe")

webserver.privilegie = false
sortie = requete({"p": "tableau-cuve"}, "refuse.html")
webserver.privilegie = true
verifie(sortie == "" && webserver.code == nil && webserver.debut == nil, "acces non privilegie : rien n'est envoye")

j = size(journal)
var page = requete({"p": "tableau-cuve"}, "page.html")
var pos = [string.find(page, "BOUCHON_CSS"), string.find(page, "BOUCHON_HTML"), string.find(page, "window.PAGE_GRAPHIQUES="),
           string.find(page, "BOUCHON_FORMULE_JS"), string.find(page, "BOUCHON_PAGE_JS")]
var ordre = true
for i: 0 .. size(pos) - 1    if (pos[i] < 0 || (i > 0 && pos[i] < pos[i - 1]))    ordre = false    end    end
verifie(ordre && webserver.termine && webserver.bouton == webserver.BUTTON_MAIN, "page : css, html, window.PAGE_GRAPHIQUES, formule.js puis pages_graphiques.js, bouton Menu")
var d = string.find(page, "window.PAGE_GRAPHIQUES=")
var config = (d >= 0 ? json.load(page[d + 23 .. string.find(page, ";</script>", d) - 1]) : nil)
verifie(config != nil && config["page"]["id"] == "tableau-cuve" && size(config["page"]["graphiques"]) == 1
        && config["calculees"].contains("cuve.manque") && config["historique"] == false, "window.PAGE_GRAPHIQUES : page, calculees, historique")
verifie(string.find(page, "Volume </script>") < 0 && string.find(page, "Volume <\\/script>") >= 0, "'</' echappe dans la description injectee")
verifie(webserver.debut == "Cuve &lt;&amp;&gt; garage", "titre de la page echappe")
var gf = lisFichier(SOURCES + "/graphiquesFonctions.be")
var cp = lisFichier(SOURCES + "/cuvePageFonctions.be")
verifie(config != nil && string.find(gf, 'VERSION_BIBLIOTHEQUE = "' + config["bibliotheque"] + '"') >= 0
        && string.find(cp, 'VERSION_EXTENSION = "' + config["extension"] + '"') >= 0, "cles de cache = celles de graphiquesFonctions et cuvePageFonctions")
verifie(erreurs(j) == 0, "page valide : aucune erreur journalisee")
global.historiqueFonctions = true
page = requete({"p": "detail"}, "page_detail.html")
global.historiqueFonctions = nil
verifie(string.find(page, '"historique":true') >= 0 && string.find(page, '"id":"detail"') >= 0, "page a acces lien servie aussi ; historique vu")

j = size(journal)
page = requete({"p": "inconnue"}, "inconnue.html")
verifie(string.find(page, "Page inconnue") >= 0 && webserver.termine && erreurs(j) == 1, "page inconnue : message et erreur journalisee")
var scripts = PG.SCRIPTS
PG.SCRIPTS = [scripts[0], SORTIE + "/absent.js"]
j = size(journal)
page = requete({"p": "tableau-cuve"}, "sans_js.html")
PG.SCRIPTS = scripts
verifie(webserver.termine && string.find(page, "BOUCHON_FORMULE_JS") >= 0 && erreurs(j) == 1, "fichier du gabarit absent : journalise, la page se termine")

# ---- 5. f=valeurs, f=sources, fichiers ------------------------------------------------------------
print("5. f=valeurs, f=sources, f=liquidfill.js.gz")
sortie = requete({"f": "valeurs", "c": "DS18B20.Temperature,absent.x,sensorsCuve.niveauCuve,sensorsCuve.niveauCuve.etat"}, "valeurs.json")
var v = json.load(sortie)
verifie(webserver.code == 200 && v != nil && v["t"] == 1792230900 && v["valeurs"]["DS18B20.Temperature"] == 21.5
        && v["valeurs"].contains("absent.x") && v["valeurs"]["absent.x"] == nil && v["valeurs"]["sensorsCuve.niveauCuve"] == nil
        && v["valeurs"]["sensorsCuve.niveauCuve.etat"] == "OK", "valeurs : feuille lue, chemin absent -> null, objet -> null")
var douze = []
for i: 1 .. 12    douze.push("a.s" + str(i))    end
sortie = requete({"f": "valeurs", "c": douze.concat(",")}, "valeurs12.json")
verifie(webserver.code == 200 && size(json.load(sortie)["valeurs"]) == 12, "12 chemins : acceptes")
douze.push("a.s13")
j = size(journal)
sortie = requete({"f": "valeurs", "c": douze.concat(",")}, "valeurs13.json")
verifie(webserver.code == 400 && json.load(sortie).contains("erreur") && erreurs(j) == 1, "13 chemins : refus 400, erreur journalisee")
for c: ["a..b", "", "a.__proto", "x.constructor"]
    sortie = requete({"f": "valeurs", "c": c}, "valeurs_invalide.json")
    verifie(webserver.code == 400, "chemin invalide '" + c + "' : refus 400")
end
sortie = requete({"f": "sources"}, "sources.json")
var src = json.load(sortie)
verifie(webserver.code == 200 && src != nil && size(src) == 2 && src["historique"] == false && src["flash"] == [], "sources sans historique : " + sortie)
global.historiqueFonctions = true
sortie = requete({"f": "sources"}, "sources2.json")
global.historiqueFonctions = nil
verifie(json.load(sortie)["historique"] == true, "sources avec historique : true")
sortie = requete({"f": "inconnu.js"}, "inconnu.json")
verifie(webserver.code == 404, "fichier inconnu : 404")
verifie(PG.FICHIER_LIQUIDFILL == "/sd/js/echarts-liquidfill.min.js.gz" && PG.MORCEAU == 2048, "extension : /sd/js/echarts-liquidfill.min.js.gz par morceaux de 2048 o")
PG.FICHIER_LIQUIDFILL = "data/sd/js/echarts-liquidfill.min.js.gz"
sortie = requete({"f": "liquidfill.js.gz"}, "liquidfill_recu.js.gz")
PG.FICHIER_LIQUIDFILL = "/sd/js/echarts-liquidfill.min.js.gz"
verifie(webserver.code == 200 && webserver.mime == "application/octet-stream" && webserver.envois > 1 && webserver.ferme, "extension envoyee en " + str(webserver.envois) + " morceaux (contenu compare par l'enveloppe)")
PG.FICHIER_LIQUIDFILL = SORTIE + "/absent.js.gz"
j = size(journal)
sortie = requete({"f": "liquidfill.js.gz"}, "liquidfill_absent.txt")
PG.FICHIER_LIQUIDFILL = "/sd/js/echarts-liquidfill.min.js.gz"
verifie(webserver.code == 404 && erreurs(j) == 1, "extension absente : 404, erreur journalisee")

# ---- 6. RAM : tas Berry avant/apres demarre() avec 8 pages ----------------------------------------
print("6. RAM")
var texte8 = json.dump(CAS["valide : 8 pages"])
ecrisFichier(FICHIER, texte8)
var journalVrai = logFonctions
logFonctions = LOG_MUET()           # le journal du banc ne doit pas compter dans la mesure
global.(".pagesGraphiques") = nil
def tas() gc.collect() return gc.allocated() end
var avant = tas()
PG.demarre()
var apres = tas()
global.(".pagesGraphiques") = nil       # ce que l'index retient = ce que rend son effacement
var index8 = apres - tas()
PG.demarre()
var complete = json.load(texte8)
var avecDescription = tas()
complete = nil
var description8 = avecDescription - tas()
logFonctions = journalVrai
verifie(size(PG.index()) == 8, "8 pages indexees")
# Le brut compte aussi des registres morts de la VM (la description lue reste dans la fenetre de la boucle du banc
# jusqu'a ce qu'un appel les ecrase) : ce que l'index retient se lit a son effacement
print(string.format("  RAM (berry.exe, 64 bits) : tas Berry %i o avant demarre(), %i o apres (+%i o brut) ; index de 8 pages : %i o retenus ; la description complete en RAM couterait %i o",
                    avant, apres, apres - avant, index8, description8))
verifie(index8 > 0 && index8 < description8 / 2, "l'index retient moins de la moitie de ce que couterait la description complete")

# ---- 7. Aucun etat dans la table du module --------------------------------------------------------
verifie([introspect.members(PG), introspect.members(V)] == MEMBRES, "tables des modules inchangees par les appels (etat dans la globale cachee seulement)")

print(echecs == 0 ? "BANC_PAGES_GRAPHIQUES: OK" : "BANC_PAGES_GRAPHIQUES: ECHEC (" + str(echecs) + ")")
