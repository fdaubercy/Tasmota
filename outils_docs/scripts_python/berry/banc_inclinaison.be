# Banc de test Berry du capteur d'inclinaison MPU6050 des volets (data/fs/vrFonctions.be, 2026-10-28).
# -----------------------------------------------------------------------------------------------
# Charge le VRAI vrFonctions.be sous des globaux bouchonnes ; le bus I2C est simule (faux 'wire' dont
# le test fixe les accelerations AX/AY/AZ) - AVANT de flasher une carte.
#
# Lancer via son enveloppe Python (deduit racine + berry.exe, code de sortie) :
#     python outils_docs/scripts_python/berry/banc_inclinaison.py [dossier_sources]
# Ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_inclinaison.be [dossier_sources]
#
# dossier_sources (defaut data/fs) : pour eprouver une copie (temoin mute) sans toucher a data/fs.
# Copier data/fs EN ENTIER, et passer la copie INTACTE avant la copie mutee (lecon du 2026-10-06).
# Portee : la logique (garde d'activation, angle, hysteresis, recalage, suivi pendant la course,
# ReglageVolets Inclinaison). Ne teste NI le vrai bus I2C, NI le vrai Shutter de Tasmota, NI le
# capteur physique. La derniere ligne, BANC_INCLINAISON: OK|ECHEC, donne le code de sortie.
import global
import sys
import string
import math
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
# Les bouchons (persist, configGlobal, diversFonctions) passent APRES le dossier des sources.
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
var journal = []                      # [message, niveau]
class LogStub
    def log(m, n, c) journal.push([str(m), n]) end
    def actif(n, c) return true end
end
var logFonctions = LogStub()

# Faux bus I2C : un MPU6050 par adresse ; accel = [AX, AY, AZ] en int16 signes, nil = bus en panne
class WireStub
    var ecrits, lectures, accel, zeros       # zeros : lectures a 0 apres le reveil (1er echantillon pas pret)
    def init() self.ecrits = [] self.lectures = 0 self.accel = [0, 0, 16384] self.zeros = 0 end
    def write(a, reg, v, n) self.ecrits.push([a, reg, v]) end
    def read_bytes(a, reg, n)
        self.lectures += 1
        var b = bytes()
        if self.accel == nil    return b    end
        for v: (self.zeros > 0 ? [0, 0, 0] : self.accel)    b.add(v < 0 ? v + 0x10000 : v, -2)    end
        if self.zeros > 0    self.zeros -= 1    end
        return b
    end
end

class TasmotaStub
    var cmds, timers, scans, bus, reponse
    def init() self.cmds = [] self.timers = {} self.scans = [] self.bus = {} self.reponse = nil end
    def cmd(c, m) self.cmds.push(c) return {} end
    def wire_scan(adr, idx) self.scans.push(adr) return self.bus.find(adr) end
    def set_timer(d, f, id) self.timers[id] = f end
    def remove_timer(id) if self.timers.contains(id) self.timers.remove(id) end end
    def resp_cmnd(x) self.reponse = x end
    def yield() end
end
var tasmota = TasmotaStub()

var inclinaison = {"activation": "OFF", "adresse": 104, "axes": "YZ", "angleOuvert": 85, "angleFerme": 3, "marge": 3}
var capteurs = {"activation": "ON", "capteurOuvert": "Inclinaison", "capteurFerme": "Switch2", "inclinaison": inclinaison}
var vr1 = {"activation": "ON", "id": 1, "capteursPosition": capteurs}
var drivers = {"voletRoulants": {"activation": "ON", "mode": 1, "environnement": {"VRs": {"VR1": vr1}}}}
var persist = {}

import vrFonctions

var echecs = 0
def verifie(c, nom)
    print((c ? "  ok   " : "  ECHEC ") + nom)
    if !c    echecs += 1    end
end
# Pose sur le faux capteur l'acceleration d'une trappe inclinee de 'deg' degres (axes Y et Z)
def incline(w, deg)
    var r = deg * math.pi / 180
    w.accel = [0, int(math.sin(r) * 16384), int(math.cos(r) * 16384)]
end
def proche(a, b) return a != nil && math.abs(a - b) < 0.5 end
def erreurs()
    var n = 0
    for l: journal    if l[1] == LOG_LEVEL_ERREUR    n += 1    end    end
    return n
end
def shutterSet()
    var l = []
    for c: tasmota.cmds    if string.find(c, "ShutterSet") == 0    l.push(c)    end    end
    return l
end

print("1. Garde : inclinaison OFF (ou bloc absent) -> le bus n'est jamais touche")
verifie(size(vrFonctions.inclinaisonsActives()) == 0, "inclinaison OFF : aucun volet surveille")
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
verifie(size(tasmota.scans) == 0 && size(tasmota.timers) == 0, "course sans inclinaison : ni wire_scan ni minuterie")
capteurs.remove("inclinaison")
verifie(size(vrFonctions.inclinaisonsActives()) == 0, "bloc absent (anciens persists) : aucun volet, pas d'erreur")
capteurs["inclinaison"] = inclinaison

print("2. Lecture de l'angle (int16 signes, moyenne de 4, reveil une seule fois)")
var mpu = WireStub()
tasmota.bus[104] = mpu
for deg: [0, 45, 90, -30]
    incline(mpu, deg)
    verifie(proche(vrFonctions.lireAngle(1, inclinaison), deg), "angle " + str(deg) + " degres")
end
verifie(size(mpu.ecrits) == 1 && mpu.ecrits[0][1] == 0x6B && mpu.ecrits[0][2] == 0, "reveil 0x6B = 0 ecrit une seule fois")
verifie(mpu.lectures == 16, "4 lectures par angle")
verifie(size(tasmota.scans) == 1, "wire_scan fait une fois, puis en cache")

print("3. ReglageVolets Inclinaison : lisible meme inclinaison OFF (calibrage), sans recalage")
incline(mpu, 42)
vrFonctions.reglageVolets("ReglageVolets", 0, "Inclinaison 1", nil)
verifie(tasmota.reponse != nil && string.find(tasmota.reponse, "42") >= 0, "reponse : angle 42")
verifie(size(shutterSet()) == 0, "calibrage : aucun ShutterSet")
vrFonctions.reglageVolets("ReglageVolets", 0, "Inclinaison 7", nil)
verifie(string.find(tasmota.reponse, "volet 7") >= 0, "volet inconnu : reponse explicite")

print("4. Activee : recalage au seul franchissement, hysteresis 'marge'")
inclinaison["activation"] = "ON"
verifie(size(vrFonctions.inclinaisonsActives()) == 1, "inclinaison ON : un volet surveille")
incline(mpu, 90)
vrFonctions.releveInclinaison(vr1)
# ShutterInvert 1 (configVRByJson) : ShutterSetClose = position ouverte
verifie(shutterSet() == ["ShutterSetClose1"], "ouvert au premier releve (demarrage) -> ShutterSetClose1")
for deg: [88, 83, 87]
    incline(mpu, deg)
    vrFonctions.releveInclinaison(vr1)
end
verifie(size(shutterSet()) == 1, "rebond 88, 83 (> 85 - 3), 87 : reste ouvert, pas de nouveau recalage")
incline(mpu, 80)
vrFonctions.releveInclinaison(vr1)
incline(mpu, 86)
vrFonctions.releveInclinaison(vr1)
verifie(size(shutterSet()) == 2, "80 (entre) puis 86 : nouveau franchissement, 2e recalage")
incline(mpu, 0)
vrFonctions.releveInclinaison(vr1)
verifie(size(shutterSet()) == 2, "ferme mais capteurFerme = Switch2 : pas de recalage par l'inclinaison")
capteurs["capteurFerme"] = "Inclinaison"
incline(mpu, 40)
vrFonctions.releveInclinaison(vr1)
incline(mpu, 1)
vrFonctions.releveInclinaison(vr1)
verifie(shutterSet()[-1] == "ShutterSetOpen1" && size(shutterSet()) == 3, "capteurFerme = Inclinaison : ferme -> ShutterSetOpen1")

print("5. Suivi pendant la course, arret avec le volet")
tasmota.cmds = []
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
verifie(tasmota.timers.contains("vrInclinaison1"), "ouverture : suivi arme")
var lu = mpu.lectures
tasmota.timers["vrInclinaison1"]()
verifie(mpu.lectures == lu + 4 && tasmota.timers.contains("vrInclinaison1"), "pas suivant : releve et re-arme")
incline(mpu, 90)
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
verifie(!tasmota.timers.contains("vrInclinaison1"), "arret : suivi coupe")
verifie(shutterSet() == ["ShutterSetClose1"], "arret : derniere lecture, ouvert -> recalage")

print("6. Pannes : capteur absent, bus muet, axes invalides -> erreur, pas d'exception, suivi coupe")
var avant = erreurs()
inclinaison["adresse"] = 105
verifie(vrFonctions.lireAngle(1, inclinaison) == nil && erreurs() == avant + 1, "adresse sans capteur : nil + erreur")
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
verifie(!tasmota.timers.contains("vrInclinaison1"), "capteur absent : pas de suivi arme")
inclinaison["adresse"] = 104
mpu.accel = nil
avant = erreurs()
verifie(vrFonctions.lireAngle(1, inclinaison) == nil && erreurs() == avant + 1, "bus muet : nil + erreur")
var scans = size(tasmota.scans)
mpu.accel = [0, 0, 16384]
verifie(proche(vrFonctions.lireAngle(1, inclinaison), 0) && size(tasmota.scans) == scans + 1, "apres panne : nouveau wire_scan, lecture retablie")
inclinaison["axes"] = "YQ"
avant = erreurs()
verifie(vrFonctions.lireAngle(1, inclinaison) == nil && erreurs() == avant + 1, "axes invalides : nil + erreur")
inclinaison["axes"] = "YZ"

print("6b. Reveil : registres a 0 tant que le 1er echantillon n'est pas pret (relecture, audit relecteur)")
vrFonctions.etat()["bus"] = {}
mpu.zeros = 2
incline(mpu, 60)
verifie(proche(vrFonctions.lireAngle(1, inclinaison), 60), "2 lectures a 0 apres le reveil : ignorees, angle 60")
vrFonctions.etat()["bus"] = {}
mpu.zeros = 100
avant = erreurs()
verifie(vrFonctions.lireAngle(1, inclinaison) == nil && erreurs() == avant + 1, "temoin : vecteur toujours nul -> nil + erreur, pas un angle de 0")
mpu.zeros = 0

print("7. Montage inverse : angleOuvert < angleFerme")
inclinaison["angleOuvert"] = 0
inclinaison["angleFerme"] = 90
vrFonctions.etat()["inclinaison"] = {}
tasmota.cmds = []
incline(mpu, -2)
vrFonctions.releveInclinaison(vr1)
verifie(shutterSet() == ["ShutterSetClose1"], "-2 degres avec angleOuvert 0 : ouvert (au-dela de la butee)")
incline(mpu, 88)
vrFonctions.releveInclinaison(vr1)
verifie(shutterSet() == ["ShutterSetClose1"], "88 degres, capteurFerme = Inclinaison, angleFerme 90 : pas encore ferme")

print("8. Apprentissage des butees : ReglageVolets Apprentissage <id> ouvert|ferme")
import persist as persistBouchon
var apprend = def (butee) vrFonctions.reglageVolets("ReglageVolets", 0, "Apprentissage 1 " + butee, nil) return tasmota.reponse end
inclinaison["axes"] = "XY"                      # faux reglages : l'apprentissage doit les remplacer
inclinaison["angleOuvert"] = 33
inclinaison["angleFerme"] = 44
var sauves = persistBouchon.nb_save
incline(mpu, 92)
apprend("ouvert")
verifie(persistBouchon.nb_save == sauves && inclinaison["angleOuvert"] == 33, "une seule butee relevee : rien d'ecrit")
tasmota.cmds = []
incline(mpu, 2)
var rep = apprend("ferme")
verifie(persistBouchon.nb_save == sauves + 1, "2 butees relevees : persist.save appele")
verifie(inclinaison["axes"] == "YZ" || inclinaison["axes"] == "ZY", "axes appris dans le plan Y/Z (rotation autour de X)")
verifie(string.find(rep, "appris") >= 0, "reponse : valeurs apprises")
verifie(size(shutterSet()) == 0, "apprentissage : aucune commande du volet")
incline(mpu, 92)
verifie(proche(vrFonctions.lireAngle(1, inclinaison), inclinaison["angleOuvert"]), "apres apprentissage, butee ouverte relue = angleOuvert")
vrFonctions.releveInclinaison(vr1)
incline(mpu, 47)
vrFonctions.releveInclinaison(vr1)
incline(mpu, 2)
vrFonctions.releveInclinaison(vr1)
verifie(vrFonctions.suiviInclinaison(1)["etat"] == "ferme", "apres apprentissage, butee fermee reconnue")
incline(mpu, 30)
apprend("ouvert")
incline(mpu, 35)
rep = apprend("ferme")
verifie(persistBouchon.nb_save == sauves + 1 && string.find(rep, "refuse") >= 0, "temoin : butees a 5 degres -> refus, rien d'ecrit")
incline(mpu, 170)
apprend("ouvert")
incline(mpu, -80)
rep = apprend("ferme")
verifie(persistBouchon.nb_save == sauves + 1 && string.find(rep, "refuse") >= 0, "temoin : arc qui traverse les 2 coupures de atan2 -> refus")
vrFonctions.suiviInclinaison(1)["enCourse"] = true
sauves = persistBouchon.nb_save
incline(mpu, 92)
rep = apprend("ouvert")
verifie(string.find(rep, "course") >= 0 && !vrFonctions.etat().find("apprentissage", {}).contains(1), "volet en course : butee refusee, rien retenu")
vrFonctions.suiviInclinaison(1)["enCourse"] = false
rep = apprend("milieu")
verifie(string.find(rep, "ouvert|ferme") >= 0, "butee inconnue : syntaxe rappelee")

print("9. Ligne de la page web : dernier angle releve, sans relire le bus")
vr1["nom"] = "Trappe"
inclinaison["axes"] = "YZ"                      # axes fixes : les angles appris en 8 ne comptent plus
incline(mpu, 47)
vrFonctions.releveInclinaison(vr1)
var lues = mpu.lectures
var ligne = vrFonctions.ligneWebInclinaison(vr1)
verifie(string.find(ligne, "{s}Trappe : inclinaison{m}47.0") == 0 && string.find(ligne, "(entre){e}") > 0, "ligne : nom, angle 47.0, etat")
verifie(mpu.lectures == lues, "la ligne web ne lit pas le bus")
mpu.accel = nil
vrFonctions.releveInclinaison(vr1)
verifie(string.find(vrFonctions.ligneWebInclinaison(vr1), "capteur muet") > 0, "capteur muet affiche apres une panne")
mpu.accel = [0, 0, 16384]

print(echecs == 0 ? "BANC_INCLINAISON: OK" : "BANC_INCLINAISON: ECHEC (" + str(echecs) + ")")
