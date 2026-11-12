# Banc de test Berry des TOUCHES DE L'ECRAN de la cave (plan ecran-cave-vues-commandes, A4, 2026-11-12) :
#   data/fs/modBus_TasmotaSlaveModBus.be  (recupereReponseModBus, branche 'boutons' : le VRAI, sous-classe sans init)
#   data/cave/tasmota32s3-serveur-rly/controleCommandesEcran.be   (commandesEsclave.recoit : le VRAI)
#   data/fs/globalFonctions.be, controleGeneral.be (modifEtatRelai, marche manuelle de la pompe : les VRAIS)
# Persist lu : data/cave/tasmota32s3-serveur-rly/_persist.json (module ecranCave et ses cles reelles, active par le banc).
#
# Lancer par son enveloppe : python outils_docs/scripts_python/berry/banc_commandes_ecran.py   (code de sortie 0 = vert)
# (verdict = DERNIERE ligne, BANC_COMMANDES_ECRAN: OK | ECHEC (n)).
#
# CE QU'IL PROUVE : un push de l'ecran (mot (seq<<1)|voulu au registre 32 + touche - 1) commande le relai, une seule
# fois par seq ; un releve sans Automatique, une seq 0, une touche inconnue ne commandent rien ; Restart seulement sur ON ;
# la marche manuelle de la pompe suspend les flotteurs ; sans le module charge, le comportement du maitre est inchange.
# NE TESTE PAS : le vrai firmware, l'UDP/RS485, l'ecran.
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
var NBRELAIS = 5

class TasmotaStub
    var puissance, timers, cmds, t, sw, reponse, nbLectures, rules
    def init() self.puissance = [false, false, false, false, false] self.timers = {} self.cmds = [] self.t = 1000000 self.sw = {} self.reponse = "" self.nbLectures = 0 self.rules = [] end
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

# Sous-classe du vrai driver : init() court-circuite (dependances firmware), vraies methodes.
charge_fichier(SOURCES + "/modbusFonctions.be")
charge_fichier(SOURCES + "/modBus_TasmotaSlaveModBus.be")
class MaitreStub : global.modBus_TasmotaSlaveModBus.MODBUS_TASMOTA_SLAVE
    def init() self.dataJson = {"TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {}}} self.derniersContacts = {} self.esclavesMuets = {} end
end

# Etat neuf pour chaque scenario. avecModule : charge controleCommandesEcran.be (sinon global.commandesEsclave = nil).
var GF = nil
var CG = nil
var maitre = nil
def monte(avecModule)
    PERSIST = json.load(lis("data/cave/tasmota32s3-serveur-rly/_persist.json"))
    modules = PERSIST["modules"]
    drivers = PERSIST["drivers"]
    diverses = PERSIST["diverses"]
    serveur = PERSIST["serveur"]
    modules["ecranCave"]["activation"] = "ON"
    drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus1"]["activation"] = "ON"
    for cm: ["pompeVideCave", "autres"]               # pas de TCA9554 ni de trame ModBus dans le banc
        for r: modules[cm]["environnement"]["relais"].keys()
            modules[cm]["environnement"]["relais"][r]["virtuel"] = "OFF"
        end
    end
    tasmota.puissance = [false, false, false, false, false]
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
    global.commandesEsclave = nil
    GF = charge_fichier(SOURCES + "/globalFonctions.be")
    global.globalFonctions = GF
    CG = charge_fichier(SOURCES + "/controleGeneral.be")
    cg = CG.init(CG)
    global.controleGeneral = cg
    if avecModule    charge_fichier("data/cave/tasmota32s3-serveur-rly/controleCommandesEcran.be")    end
    maitre = MaitreStub()
end

def pompe() return modules["pompeVideCave"]["environnement"] end
def etatCapteurs()
    var c = pompe()["capteurs"]
    return c["capteur1"]["activation"] + "/" + c["capteur2"]["activation"] + "/" + str(c["capteur1"].find("suspendu")) + "/" + str(c["capteur2"].find("suspendu"))
end
def mot(seq, voulu) return (seq << 1) | (voulu ? 1 : 0) end
# Push de l'ecran (UDP, 0x10 non sollicite marque Automatique) au registre 32 + touche - 1, comme la regle ModbusReceivedUDP#DeviceAddress==1
def push(touche, m)
    maitre.recupereReponseModBus(1, "ModbusReceivedUDP#DeviceAddress==1", {"ModbusReceivedUDP": {"DeviceAddress": 1, "FunctionCode": 0x10,
        "StartAddress": 32 + touche - 1, "Count": 1, "Values": [m], "Automatique": true}})
end
def nbCmds(prefixe)
    var n = 0
    for c: tasmota.cmds    if string.find(c, prefixe) == 0    n += 1    end    end
    return n
end
def erreurs()
    var n = 0
    for l: logFonctions.journal    if l[0] == 1 && string.find(l[1], "COMMANDES_ECRAN_ERREUR") >= 0    n += 1    end    end
    return n
end

print("--- push_allume_relai")
monte(true)
push(1, mot(1, true))
verifie("touche 1 : relai 3 (Lumieres) ON", true, tasmota.puissance[2])
push(1, mot(2, false))
verifie("touche 1 OFF : relai 3 OFF", false, tasmota.puissance[2])
push(2, mot(1, true))
push(3, mot(1, true))
verifie("touche 2 -> relai 5, touche 3 -> relai 4 (seq propre a chaque touche)", "true/true", str(tasmota.puissance[4]) + "/" + str(tasmota.puissance[3]))

print("--- meme_seq_une_seule_action")
monte(true)
push(1, mot(5, true))
push(1, mot(5, true))
push(1, mot(5, true))
verifie("trois fois le meme mot : une seule commande Power3", 1, nbCmds("Power3"))
push(1, mot(5, false))
verifie("meme seq mais autre sens : ignore aussi (relance de l'ecran)", 1, nbCmds("Power3"))

print("--- releve_sans_action")
monte(true)
global.modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 1, "FunctionCode": 2, "StartAddress": 32, "Count": 1, "type": "uint8"}}
maitre.recupereReponseModBus(1, "ModbusReceived#DeviceAddress==1", {"ModbusReceived": {"DeviceAddress": 1, "FunctionCode": 2, "Values": [3]}})   # 3 = un mot qui, pousse, commanderait la touche 1
verifie("reponse de releve 0x02 : aucune commande", "0/0/false", str(nbCmds("Power")) + "/" + str(nbCmds("Restart")) + "/" + str(tasmota.puissance[2]))
verifie("l'etat lu de la touche est tout de meme enregistre", "ON", modules["ecranCave"]["environnement"]["boutons"]["bouton1"]["etat"])
global.modbusFonctions.etat()["enVol"] = nil

print("--- seq_zero_ignoree")
monte(true)
push(1, 1)
push(5, 1)
verifie("seq 0 : rien ne bouge", "0/0", str(nbCmds("Power")) + "/" + str(nbCmds("Restart")))

print("--- numero_inconnu_log_erreur")
monte(true)
global.commandesEsclave.recoit("TasmotaSlaveModBus1", 9, mot(1, true))
verifie("une erreur journalisee, aucune commande", "1/0", str(erreurs()) + "/" + str(nbCmds("Power")))
global.commandesEsclave.recoit("TasmotaSlaveModBus2", 1, mot(1, true))
verifie("autre esclave que celui de l'ecran : ignore sans erreur", "1/0", str(erreurs()) + "/" + str(nbCmds("Power")))

print("--- redemarre_seulement_sur_on")
monte(true)
push(5, mot(1, false))
verifie("OFF : pas de Restart", 0, nbCmds("Restart"))
push(5, mot(2, true))
verifie("ON : Restart 1", 1, nbCmds("Restart 1"))

print("--- pompe_manuelle_desactive_flotteurs")
monte(true)
push(4, mot(1, true))
verifie("touche 4 : relai 1 ON, flotteurs suspendus", "true/OFF/OFF/ON/ON", str(tasmota.puissance[0]) + "/" + etatCapteurs())
push(4, mot(2, false))
verifie("touche 4 OFF : relai 1 OFF, flotteurs rendus", "false/ON/ON/nil/nil", str(tasmota.puissance[0]) + "/" + etatCapteurs())

print("--- module_inactif_ou_absent")
monte(true)
modules["ecranCave"]["activation"] = "OFF"
push(1, mot(1, true))
verifie("ecranCave OFF : rien", 0, nbCmds("Power"))
monte(false)
verifie("sans le module : global.commandesEsclave nil", "nil", str(global.commandesEsclave))
push(1, mot(1, true))
verifie("sans crochet actif : push sans commande ni exception", "0/ON", str(nbCmds("Power")) + "/" + modules["ecranCave"]["environnement"]["boutons"]["bouton1"]["etat"])

print("--- boutons_virtuels_dans_sensor_tolere")
monte(true)
push(1, mot(1, true))
tasmota.reponse = ""
var exc = nil
try    cg.json_append()    except .. as e, m    exc = str(e) + " " + str(m)    end
verifie("json_append sans exception", "nil", str(exc))
verifie("SENSOR porte Button11 ON et Button12 OFF (cles tolerees, rien d'autre ne bouge)", "true/true/1", str(string.find(tasmota.reponse, '"Button11": "ON"') >= 0) + "/" + str(string.find(tasmota.reponse, '"Button12": "OFF"') >= 0) + "/" + str(nbCmds("Power")))

print("BANC_COMMANDES_ECRAN: " + (echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")") + " (" + str(nbControles) + " controles)")
