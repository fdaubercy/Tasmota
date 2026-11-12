# Banc de test Berry de la MARCHE MANUELLE de la pompe vide-cave (plan ecran-cave-vues-commandes, A2, 2026-11-12) :
#   data/fs/globalFonctions.be   (commandeRelaisLies, modifEtatRelai, changementEtatCapteur : les VRAIS)
#   data/fs/controleGeneral.be   (init, set_power_handler, finTimerRelai : les VRAIS, instancies par controleGeneral.init)
# Persist lu : data/cave/tasmota32s3-serveur-rly/_persist.json (module pompeVideCave et ses cles reelles).
#
# Lancer par son enveloppe : python outils_docs/scripts_python/berry/banc_pompe_cave.py   (code de sortie 0 = vert)
# Directement, depuis la racine : lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_pompe_cave.be
# (verdict = DERNIERE ligne, BANC_POMPE_CAVE: OK | ECHEC (n)).
#
# CE QU'IL PROUVE : un appui sur le bouton (relaisLie.desactiveCapteurs = ON) coupe les flotteurs pendant la
# marche et les rend a l'arret (second appui, fin de minuterie) et au demarrage ; sans la cle, rien ne change.
# NE TESTE PAS : le vrai firmware (le Power du bouchon appelle set_power_handler en synchrone, comme on le
# croit du firmware, sans l'avoir mesure), le TCA9554, les entrees physiques, la page web.
import global
import sys
import string
import json

var SOURCES = "data/fs"
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/pompe_cave")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
class Driver end
import logFonctions
global.logFonctions = logFonctions
import configDevices

var cg = nil                                       # instance de CONTROLE_GENERAL du scenario
var modules = {}
var drivers = {}
var diverses = {}
var serveur = {}
var PERSIST = nil
var NBRELAIS = 4

class TasmotaStub
    var puissance, timers, cmds
    def init() self.puissance = [false, false, false, false] self.timers = {} self.cmds = [] end
    def yield() end
    def millis(n) return 0 end
    def time_reached(t) return false end
    def read_sensors() return "{}" end
    def memory() return {"program": 100, "program_free": 50, "heap_free": 1} end
    def rtc() return {"local": 1000000, "utc": 1000000} end
    def add_driver(d) end
    def add_rule(a, b, c) end
    def add_cmd(n, f) end
    def add_cron(c, f, id) end
    def remove_cron(id) end
    def remove_timer(id) self.timers.remove(id) end
    def set_timer(ms, f, id) self.timers[id != nil ? id : "anonyme"] = [ms, f] end
    def get_power() return self.puissance end
    def cmd(s, m)
        self.cmds.push(s)
        var r = string.split(s, " ")
        if size(r) == 2 && string.find(r[0], "Power") == 0
            var i = int(r[0][5 ..]) - 1
            self.puissance[i] = (r[1] == "ON")
            var masque = 0
            for k: 0 .. NBRELAIS - 1    if self.puissance[k]    masque += (1 << k)    end    end
            cg.set_power_handler("Power", masque)       # le firmware appelle le handler dans la foulee
        end
        return {}
    end
end
var tasmota = TasmotaStub()
global.tasmota = tasmota

# compile() est strict : un global du firmware que le fichier nomme et que le banc ne declare pas est declare
# a nil, puis on recompile (20 essais au plus), comme banc_test_modbus.be.
def charge_fichier(chemin)
    var f = open(chemin, "r")
    var src = f.read()
    f.close()
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

# Etat neuf pour chaque scenario. suspendus : capteurs deja suspendus (persist d'avant un redemarrage).
var GF = nil
var CG = nil
def monte(suspendus, sansCle)
    PERSIST = json.load(lis("data/cave/tasmota32s3-serveur-rly/_persist.json"))
    modules = PERSIST["modules"]
    drivers = PERSIST["drivers"]
    diverses = PERSIST["diverses"]
    serveur = PERSIST["serveur"]
    var pompe = modules["pompeVideCave"]["environnement"]
    pompe["relais"]["relai1"]["virtuel"] = "OFF"          # pas de TCA9554 ni de trame ModBus dans le banc
    if sansCle
        for b: ["bouton1", "bouton2"]    pompe["boutons"][b]["relaisLie"].remove("desactiveCapteurs")    end
    end
    for c: suspendus
        pompe["capteurs"][c]["activation"] = "OFF"
        pompe["capteurs"][c]["suspendu"] = "ON"
    end
    tasmota.puissance = [false, false, false, false]
    tasmota.timers = {}
    tasmota.cmds = []
    logFonctions.journal.clear()
    configDevices.activationAuBranchement = nil
    GF = charge_fichier(SOURCES + "/globalFonctions.be")
    global.globalFonctions = GF
    CG = charge_fichier(SOURCES + "/controleGeneral.be")
    cg = CG.init(CG)                                   # ce que fait 'import controleGeneral' au firmware
    global.controleGeneral = cg
end
def pompe() return modules["pompeVideCave"]["environnement"] end
def etatCapteurs()
    var c = pompe()["capteurs"]
    return c["capteur1"]["activation"] + "/" + c["capteur2"]["activation"] + "/" + str(c["capteur1"].find("suspendu")) + "/" + str(c["capteur2"].find("suspendu"))
end
def appuiBouton() GF.commandeRelaisLies("pompeVideCave", pompe()["boutons"]["bouton1"], "TOGGLE", false) end
def flotteur(cle, valeur) GF.changementEtatCapteur(valeur, "Switch" + str(pompe()["capteurs"][cle]["id"]), nil, "pompeVideCave", cle) end

print("--- appui_bouton_desactive_flotteurs")
monte([], false)
appuiBouton()
verifie("relais 1 ON", true, tasmota.puissance[0])
verifie("capteurs OFF et suspendu ON", "OFF/OFF/ON/ON", etatCapteurs())

print("--- flotteur_bas_ignore_en_manuel")
flotteur("capteur1", "ON")
flotteur("capteur1", "OFF")                            # le niveau bas retombe : sans la desactivation, le relais serait coupe
verifie("relais 1 reste ON", true, tasmota.puissance[0])

print("--- second_appui_reactive")
appuiBouton()
verifie("relais 1 OFF", false, tasmota.puissance[0])
verifie("capteurs ON, plus de suspendu", "ON/ON/nil/nil", etatCapteurs())

print("--- minuterie_reactive")
monte([], false)
appuiBouton()
verifie("pendant la marche : capteurs OFF et suspendu ON", "OFF/OFF/ON/ON", etatCapteurs())
verifie("minuterie armee (120 s)", 120000, tasmota.timers.find("timer_relai1", [nil])[0])
tasmota.timers["timer_relai1"][1]()                    # la minuterie arrive a son terme
verifie("relais 1 OFF a la fin", false, tasmota.puissance[0])
verifie("capteurs ON, plus de suspendu", "ON/ON/nil/nil", etatCapteurs())

print("--- demarrage_reactive")
monte(["capteur1", "capteur2"], false)
verifie("capteurs ON, sans suspendu, apres init()", "ON/ON/nil/nil", etatCapteurs())
verifie("capteurs deja ON quand init() branche les regles", "ON/ON", configDevices.activationAuBranchement)

print("--- sans_cle_inchange")
monte([], true)
appuiBouton()
verifie("relais 1 ON", true, tasmota.puissance[0])
verifie("capteurs jamais touches", "ON/ON/nil/nil", etatCapteurs())
appuiBouton()
verifie("relais 1 OFF, capteurs toujours intacts", "false/ON/ON/nil/nil", str(tasmota.puissance[0]) + "/" + etatCapteurs())

print("BANC_POMPE_CAVE: " + (echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")") + " (" + str(nbControles) + " controles)")
