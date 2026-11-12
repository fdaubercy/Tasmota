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
import mqtt

var cg = nil                                       # instance de CONTROLE_GENERAL du scenario
var modules = {}
var drivers = {}
var diverses = {}
var serveur = {}
var PERSIST = nil
var NBRELAIS = 4

class TasmotaStub
    var puissance, timers, cmds, t, sw, reponse, nbLectures, rules
    def init() self.puissance = [false, false, false, false] self.timers = {} self.cmds = [] self.t = 1000000 self.sw = {} self.reponse = "" self.nbLectures = 0 self.rules = [] end
    def response_append(s) self.reponse += s end
    def yield() end
    def millis(n) return 0 end
    def time_reached(t) return true end
    def read_sensors()
        self.nbLectures += 1
        self.reponse = ""                               # comme l_read_sensors du firmware : ResponseClear() avant de rebatir SENSOR
        return json.dump(self.sw)
    end
    def memory() return {"program": 100, "program_free": 50, "heap_free": 1} end
    def rtc() return {"local": self.t, "utc": self.t} end
    def add_driver(d) end
    def add_rule(a, b, c) self.rules.push([a, b]) end
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
var DRV = nil
def chargeDriver()
    charge_fichier("data/cave/tasmota32s3-serveur-rly/controlePompeVideCave.be")    # le driver de la carte
    DRV = global.controlePompeVideCave
end
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
    tasmota.t = 1000000
    tasmota.sw = {}
    tasmota.reponse = ""
    tasmota.nbLectures = 0
    tasmota.rules = []
    mqtt.relie = false
    mqtt.publies.clear()
    logFonctions.journal.clear()
    configDevices.activationAuBranchement = nil
    GF = charge_fichier(SOURCES + "/globalFonctions.be")
    global.globalFonctions = GF
    CG = charge_fichier(SOURCES + "/controleGeneral.be")
    cg = CG.init(CG)                                   # ce que fait 'import controleGeneral' au firmware
    global.controleGeneral = cg
    chargeDriver()
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

# --- A3 : pannes des flotteurs et etat publie -------------------------------------------------------
# Etat des flotteurs : lu par read_sensors (controleGeneral) et rejoue comme evenement SwitchN#Action (regles du driver)
def sw(bas, haut)
    tasmota.sw = {"Switch1": bas, "Switch2": haut}
    for r: tasmota.rules
        if (r[0] == "Switch1#Action")    r[1](bas, r[0], nil)    end
        if (r[0] == "Switch2#Action")    r[1](haut, r[0], nil)    end
    end
end
def tick(dt) tasmota.t += dt  DRV.every_second() end
def relai() return pompe()["relais"]["relai1"] end
def alerte() return relai()["alerte"] end
def depart() GF.modifEtatRelai("pompeVideCave", 1, "ON", "ON", false, true, 0) end
# Marche automatique menee a terme par la minuterie de 120 s
def cycleMinuterie()
    depart()
    tick(0)
    tick(120)
    tasmota.timers["timer_relai1"][1]()
    tick(0)
end
# Marche manuelle (bouton) coupee par la minuterie
def cycleManuel()
    appuiBouton()
    tick(0)
    tick(120)
    tasmota.timers["timer_relai1"][1]()
    tick(0)
end
def evenements() var l = [] for p: mqtt.publies    l.push(json.load(p)["Evenement"])    end return str(l) end

print("--- incoherence_apres_anti_rebond")
monte([], false)
mqtt.relie = true
sw("OFF", "ON")
tick(0)
tick(4)
verifie("pas d'alerte avant 5 s", "", alerte())
tick(2)
verifie("alerte incoherence apres 6 s", true, string.find(alerte(), "ncoherence") >= 0)
verifie("publiee sur la voie ALERTE_POMPE", "['incoherence']", evenements())
tick(10)
verifie("une seule publication", "['incoherence']", evenements())

print("--- incoherence_breve_ignoree")
monte([], false)
sw("OFF", "ON")
tick(0)
tick(3)
sw("ON", "ON")
tick(1)
sw("OFF", "ON")
tick(0)
tick(3)
verifie("deux episodes de 3 s : pas d'alerte", "", alerte())
sw("OFF", "OFF")
tick(10)
verifie("plus incoherent ensuite : toujours pas d'alerte", "", alerte())

print("--- flotteur_bas_apres_n_arrets")
monte([], false)
mqtt.relie = true
sw("ON", "OFF")
cycleMinuterie()
cycleMinuterie()
verifie("2 arrets : pas d'alerte", "", alerte())
cycleMinuterie()
verifie("3 arrets : alerte flotteurBas", true, string.find(alerte(), "bas") >= 0)
verifie("publiee", "['flotteurBas']", evenements())
cycleMinuterie()
verifie("4e arret : l'alerte reste", true, string.find(alerte(), "bas") >= 0)
verifie("sans nouvelle publication", "['flotteurBas']", evenements())
DRV.acquitte()
cycleMinuterie()
cycleMinuterie()
verifie("acquittement : compteur remis a 0", "", alerte())
cycleMinuterie()
verifie("3 arrets apres l'acquittement : alerte", true, string.find(alerte(), "bas") >= 0)

print("--- arret_court_ne_compte_pas")
monte([], false)
sw("ON", "OFF")
for i: 1 .. 4
    depart()
    tick(0)
    tick(10)
    GF.modifEtatRelai("pompeVideCave", 1, "OFF", "OFF", false, true, 0)
    tick(0)
end
verifie("arrets a 10 s (pas la minuterie) : pas d'alerte", "", alerte())

print("--- arret_normal_remet_compteur")
monte([], false)
sw("ON", "OFF")
cycleMinuterie()
cycleMinuterie()
sw("OFF", "OFF")
cycleMinuterie()                                      # arret avec le bas retombe
sw("ON", "OFF")
cycleMinuterie()
verifie("1 arret apres la remise a 0 : pas d'alerte", "", alerte())
cycleMinuterie()
verifie("2 arrets apres la remise a 0 : pas d'alerte", "", alerte())

print("--- manuel_ne_compte_pas")
monte([], false)
sw("ON", "OFF")
cycleManuel()
cycleManuel()
cycleManuel()
cycleManuel()
verifie("4 marches manuelles : pas d'alerte", "", alerte())

print("--- json_append_porte_pompe_vide_cave")
monte([], false)
sw("ON", "OFF")
tasmota.reponse = '{"Time":"x","Switch1":"ON"'                    # SENSOR en cours de construction par la telemetrie
DRV.json_append()
verifie("json_append ne vide pas le tampon SENSOR (pas de read_sensors)", '{"Time":"x","Switch1":"ON",', tasmota.reponse[0 .. 26])
var j = json.load(tasmota.reponse + "}")["PompeVideCave"]
verifie("pompe, manuel, niveaux, alerte", "OFF/OFF/ON/OFF/", str(j["Pompe"]) + "/" + j["Manuel"] + "/" + j["Niveaux"]["Bas"] + "/" + j["Niveaux"]["Haut"] + "/" + j["Alerte"])
appuiBouton()
tasmota.reponse = ""
for c: ["capteur1", "capteur2"]    pompe()["capteurs"][c].remove("etat")    end
tasmota.rules = []
chargeDriver()                                         # aucun evenement ni etat memorise : niveaux inconnus
DRV.json_append()
j = json.load("{" + tasmota.reponse[1 ..] + "}")["PompeVideCave"]
verifie("marche manuelle, niveaux inconnus", "ON/ON/?/?", j["Pompe"] + "/" + j["Manuel"] + "/" + j["Niveaux"]["Bas"] + "/" + j["Niveaux"]["Haut"])
relai()["alerte"] = "texte d'alerte"
tasmota.reponse = ""
DRV.json_append()
j = json.load("{" + tasmota.reponse[1 ..] + "}")["PompeVideCave"]
verifie("alerte recopiee", "texte d'alerte", j["Alerte"])

print("--- capteur_off_volontaire_reste_off")
monte([], false)
pompe()["capteurs"]["capteur1"]["activation"] = "OFF"          # coupe a la main par l'utilisateur
appuiBouton()
verifie("pendant la marche : seul capteur2 suspendu", "OFF/OFF/nil/ON", etatCapteurs())
appuiBouton()
verifie("apres : capteur1 reste OFF, capteur2 revient", "OFF/ON/nil/nil", etatCapteurs())

print("--- fin_manuelle_garde_alerte_si_haut_actif")
monte([], false)
sw("OFF", "ON")
appuiBouton()
relai()["alerte"] = "defaut en cours"
appuiBouton()                                          # fin manuelle, haut encore ON
verifie("l'alerte defaut n'est pas effacee", "defaut en cours", alerte())

print("--- fin_minuterie_manuelle_niveau_haut_on")
monte([], false)
sw("OFF", "ON")
appuiBouton()
tasmota.timers["timer_relai1"][1]()
verifie("relance automatique reprise (1/3)", 1, cg.relances.find("pompeVideCave_1", 0))
verifie("minuterie de relance armee", true, tasmota.timers.contains("relance_relai1"))

print("--- no_read_sensors_en_every_second")
monte([], false)
sw("OFF", "ON")
var avant = tasmota.nbLectures
for i: 1 .. 6    tick(1)    end
verifie("aucune lecture de la telemetrie en 6 ticks", avant, tasmota.nbLectures)
DRV.json_append()
verifie("ni dans json_append", avant, tasmota.nbLectures)

print("--- sans_relance_ne_leve_pas")
monte([], false)
relai().remove("relance")
chargeDriver()
sw("OFF", "ON")
tick(0)
tick(10)
verifie("pannes sans relance : rien, pas d'exception", "", alerte())
DRV.json_append()
verifie("json_append repond quand meme", true, string.find(tasmota.reponse, "PompeVideCave") >= 0)

print("BANC_POMPE_CAVE: " + (echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")") + " (" + str(nbControles) + " controles)")
