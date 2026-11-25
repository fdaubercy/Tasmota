# Banc Berry de la page /humidite et de la commande ReglageHumidite : data/cave/<carte>/controleHumidite.be (les VRAIS, ESP32 et S3 de la
# cave) sous un faux tasmota, un faux webserver et un faux persist (bouchons_berry/humidite/). Persist REEL de chaque carte lu dans data/.
# Pourquoi ce banc : le 2026-11-23 la page ne sauvait plus rien. `re.match("^[0-9]{1,3}$", ...)` leve 'internal_error - error in regex'
# (le moteur re de Berry ne connait pas {n,m}) ; berry.exe embarque le MEME moteur : l'exception se reproduit ici.
#
# Lancer par son enveloppe : python outils_docs/scripts_python/berry/banc_humidite.py [--sans-mutants]   (code de sortie 0 = vert)
# Directement, depuis la racine : lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_humidite.be [chemin du module a tester]
# Derniere ligne : BANC_HUMIDITE: OK | ECHEC (n). Avec un chemin : le module de ce fichier est teste sur le persist de la carte ESP32 (mutants).
# NE TESTE PAS : le vrai firmware (HTTP, persist.save reel, solidification), web_sensor (tuiles de l'accueil), l'AM2301.
import global
import sys
import string
import json

sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/humidite")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
class Driver end
import logFonctions
global.logFonctions = logFonctions
import persist
import webserver
var modules = {}
var controleGeneral = nil

class TasmotaStub
    var cmds, reponse, drivers
    def init() self.cmds = {} self.reponse = "" self.drivers = [] end
    def add_driver(d) self.drivers.push(d) end
    def add_cmd(n, f) self.cmds[n] = f end
    def resp_cmnd(s) self.reponse = s end
end
var tasmota = TasmotaStub()
global.tasmota = tasmota

var echecs = 0
var nbControles = 0
def verifie(nom, attendu, obtenu)
    nbControles += 1
    var ok = (str(attendu) == str(obtenu))
    print((ok ? "  ok   " : "  ECHEC ") + nom + (ok ? "" : " : attendu " + str(attendu) + ", obtenu " + str(obtenu)))
    if !ok    echecs += 1    end
end

def lis(chemin)
    var f = open(chemin, "r")
    var s = f.read()
    f.close()
    return s
end

# Charge un module .be et rend le module qu'il construit ; les globales du firmware que le fichier cite sans que le banc les declare sont
# declarees a nil (compile() est strict), 20 essais au plus.
def charge_module(chemin)
    var src = lis(chemin) + "\nreturn controleHumidite\n"
    for essai: 1 .. 20
        try
            return compile(src)()
        except .. as e, m
            var r = string.split(str(m), "'")
            if (e != "syntax_error" || size(r) < 3 || string.find(str(m), "undeclared") < 0)
                print(">>> " + chemin + " non charge :", e, m)
                return nil
            end
            global.(r[1]) = nil
        end
    end
end

# Appelle f() et rend [valeur, exception ou nil] : une exception est un ECHEC du banc, jamais un plantage du banc
def essaie(f)
    try
        return [f(), nil]
    except .. as e, m
        return [nil, str(e) + " " + str(m)]
    end
end

# Etat neuf : persist reel de la carte, driver charge et instancie comme au demarrage (import -> init(m))
var DRV = nil
var TH = nil
def monte(carte, chemin)
    var d = json.load(lis("data/cave/" + carte + "/_persist.json"))
    modules = d["modules"]
    global.modules = modules
    TH = modules["Thermo-Hygrometre"]["environnement"]["thermometres"]["thermometre1"]
    persist.sauvegardes.clear()
    logFonctions.journal.clear()
    logFonctions.declarees.clear()
    tasmota.cmds = {}
    webserver.routes = []
    var M = charge_module(chemin)
    if (M == nil)    DRV = nil    return    end
    M.init(M)
    DRV = global.controleHumidite
end

def page_texte()
    return webserver.envoye.concat("")
end

# "basse haute" lus dans la derniere reponse de la commande (l'ordre des cles d'un JSON de map n'est pas stable)
def reponse_bornes()
    var j = json.load(tasmota.reponse)
    var b = isinstance(j, map) ? j.find("ReglageHumidite") : nil
    return isinstance(b, map) ? str(b.find("basse")) + " " + str(b.find("haute")) : "pas de bornes : " + tasmota.reponse
end

def scenarios(carte, chemin)
    print("--- " + carte + " (" + chemin + ")")
    monte(carte, chemin)
    verifie("module charge et driver cree", true, DRV != nil)
    if DRV == nil    return    end
    verifie("cible de log declaree : humidite -> modules.Thermo-Hygrometre", "[['humidite', 'modules.Thermo-Hygrometre']]", str(logFonctions.declarees))
    verifie("bornes du persist reel", "[50, 75]", str(DRV.bornes(DRV.thermo())))
    verifie("routes /humidite GET et POST", "[['/humidite', 1], ['/humidite', 2]]", str(webserver.routes))

    # regle() : valeurs valides
    var r = essaie(/ -> DRV.regle("40", "65"))
    verifie("regle 40 65 : pas d'exception", nil, r[1])
    verifie("regle 40 65 : succes (nil)", nil, r[0])
    verifie("regle 40 65 : limites ecrites", "[40, 65]", str(TH["limites"]))
    verifie("regle 40 65 : persist.save(true) appele une fois", "[true]", str(persist.sauvegardes))
    verifie("regle 40 65 : info loguee sous la cible humidite", "humidite", size(logFonctions.journal) > 0 ? logFonctions.journal[-1][2] : nil)
    r = essaie(/ -> DRV.regle(0, 100))
    verifie("regle 0 100 (entiers, extremes) : pas d'exception", nil, r[1])
    verifie("regle 0 100 : limites", "[0, 100]", str(TH["limites"]))
    r = essaie(/ -> DRV.regle("5", "10"))
    verifie("regle 5 10 (un chiffre, ecart 5) : limites", "[5, 10]", str(TH["limites"]))

    # regle() : refus, rien n'est ecrit
    TH["limites"] = [50, 75]
    persist.sauvegardes.clear()
    for cas: [["abc", "70"], ["", "70"], ["50", ""], ["1000", "70"], ["-5", "70"], ["5.5", "70"], ["50", "101"], ["60", "62"], ["70", "60"], ["50", "50"]]
        r = essaie(/ -> DRV.regle(cas[0], cas[1]))
        verifie("refus " + str(cas) + " : pas d'exception", nil, r[1])
        verifie("refus " + str(cas) + " : message d'erreur rendu", "string", type(r[0]))
    end
    verifie("refus : limites inchangees", "[50, 75]", str(TH["limites"]))
    verifie("refus : persist.save jamais appele", "[]", str(persist.sauvegardes))

    # page : POST (le geste de l'utilisateur) et GET
    webserver.args = {"bas": "30", "haut": "80"}
    r = essaie(/ -> DRV.enregistre())
    verifie("POST 30 80 : pas d'exception", nil, r[1])
    verifie("POST 30 80 : page terminee", true, webserver.termine)
    verifie("POST 30 80 : message de succes", true, string.find(page_texte(), "Bornes enregistrées.") >= 0)
    verifie("POST 30 80 : limites ecrites", "[30, 80]", str(TH["limites"]))
    verifie("POST 30 80 : curseurs sur les nouvelles valeurs", true, string.find(page_texte(), "name='bas' value='30'") >= 0 && string.find(page_texte(), "name='haut' value='80'") >= 0)
    webserver.args = {"bas": "70", "haut": "72"}
    r = essaie(/ -> DRV.enregistre())
    verifie("POST ecart 2 : pas d'exception", nil, r[1])
    verifie("POST ecart 2 : page terminee", true, webserver.termine)
    verifie("POST ecart 2 : message d'erreur affiche", true, string.find(page_texte(), "dépasser la basse") >= 0)   # absent du texte fixe de la page
    verifie("POST ecart 2 : pas de message de succes", true, string.find(page_texte(), "Bornes enregistrées.") < 0)
    verifie("POST ecart 2 : limites inchangees", "[30, 80]", str(TH["limites"]))
    webserver.args = {}
    r = essaie(/ -> DRV.enregistre())
    verifie("POST sans argument : pas d'exception", nil, r[1])
    verifie("POST sans argument : limites inchangees", "[30, 80]", str(TH["limites"]))
    r = essaie(/ -> DRV.affiche())
    verifie("GET : pas d'exception", nil, r[1])
    verifie("GET : page terminee", true, webserver.termine)

    # commande ReglageHumidite
    var cmd = tasmota.cmds.find("ReglageHumidite")
    verifie("commande ReglageHumidite declaree", true, cmd != nil)
    if cmd == nil    return    end
    r = essaie(/ -> cmd("ReglageHumidite", 1, "35 75", nil))
    verifie("commande 35 75 : pas d'exception", nil, r[1])
    verifie("commande 35 75 : limites ecrites", "[35, 75]", str(TH["limites"]))
    verifie("commande 35 75 : reponse", "35 75", reponse_bornes())
    r = essaie(/ -> cmd("ReglageHumidite", 1, "35", nil))
    verifie("commande a un seul mot : erreur dans la reponse", true, string.find(tasmota.reponse, "erreur") >= 0)
    r = essaie(/ -> cmd("ReglageHumidite", 1, "abc 70", nil))
    verifie("commande abc 70 : pas d'exception", nil, r[1])
    verifie("commande abc 70 : erreur dans la reponse", true, string.find(tasmota.reponse, "erreur") >= 0)
    verifie("commande abc 70 : limites inchangees", "[35, 75]", str(TH["limites"]))
    r = essaie(/ -> cmd("ReglageHumidite", 1, "", nil))
    verifie("commande sans argument : bornes rendues", "35 75", reponse_bornes())
end

if size(global._argv) > 1
    scenarios("tasmota32-serveur-rly", global._argv[1])            # module mute (enveloppe Python), persist de la carte ESP32
else
    for carte: ["tasmota32-serveur-rly", "tasmota32s3-serveur-rly"]
        scenarios(carte, "data/cave/" + carte + "/controleHumidite.be")
    end
end

print("BANC_HUMIDITE: " + (echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")") + " (" + str(nbControles) + " controles)")
