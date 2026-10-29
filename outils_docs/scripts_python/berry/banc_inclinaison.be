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
    var cmds, timers, scans, bus, reponse, horloge     # horloge : millis simulees, avancees par le test
    def init() self.cmds = [] self.timers = {} self.scans = [] self.bus = {} self.reponse = nil self.horloge = 0 end
    def millis() return self.horloge end
    def time_reached(t) return self.horloge >= t end
    var surCmd                                      # facultatif : rejoue un evenement synchrone (Direction 0)
    def cmd(c, m) self.cmds.push(c) if self.surCmd != nil    self.surCmd(c)    end return {} end
    def wire_scan(adr, idx) self.scans.push(adr) return self.bus.find(adr) end
    var delais
    def set_timer(d, f, id) self.timers[id] = f if self.delais == nil    self.delais = {}    end self.delais[id] = d end
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
var serveur = {"mqtt": {"topic": "grenier"}}

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
# Commandes du Shutter (ShutterStop, ShutterSet*), sans la lecture de ShutterMotorStop
def pilotage()
    var l = []
    for c: tasmota.cmds    if string.find(c, "ShutterS") == 0    l.push(c)    end    end
    return l
end
# ShutterMotorStop (500 ms) + 100 ms ecoules : les commandes differees apres un arret partent
def attente()
    tasmota.horloge += 700
    var noms = []
    for k: tasmota.timers.keys()    if string.find(k, "vrShutter") == 0    noms.push(k)    end    end
    for k: noms
        var f = tasmota.timers[k]
        tasmota.timers.remove(k)
        f()
    end
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
verifie(mpu.ecrits == [[104, 0x6B, 0], [104, 0x1A, 6]], "reveil 0x6B = 0 puis filtre passe-bas 0x1A = 6, une seule fois")
verifie(mpu.lectures == 16, "4 lectures par angle")
verifie(size(tasmota.scans) == 1, "wire_scan fait une fois, puis en cache")
inclinaison["filtre"] = 3
vrFonctions.etat()["bus"] = {}
vrFonctions.lireAngle(1, inclinaison)
verifie(mpu.ecrits[-1] == [104, 0x1A, 3], "cle 'filtre' du persist ecrite dans 0x1A")
inclinaison.remove("filtre")

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
verifie(size(shutterSet()) == 0, "juste apres l'arret : recalage differe (ShutterMotorStop, sinon loop() reentre)")
attente()
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

print("10. Blocage : moteur en marche, angle fige 'blocage' secondes -> ShutterStop + erreur")
inclinaison["angleOuvert"] = 85
inclinaison["angleFerme"] = 3
vrFonctions.etat()["inclinaison"] = {}
def pas()                                       # un pas de suivi : 250 ms plus tard
    tasmota.horloge += 250
    if tasmota.timers.contains("vrInclinaison1")    tasmota.timers["vrInclinaison1"]()    end
end
def stops()
    var l = []
    for c: tasmota.cmds    if string.find(c, "ShutterStop") == 0    l.push(c)    end    end
    return l
end
tasmota.cmds = []
incline(mpu, 40)
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
for n: 1 .. 19    pas()    end
verifie(size(stops()) == 0, "angle fige 4,75 s : pas encore de blocage")
avant = erreurs()
pas()
verifie(stops() == ["ShutterStop1"] && erreurs() == avant + 1, "angle fige 5 s : ShutterStop1 et une erreur")
verifie(!tasmota.timers.contains("vrInclinaison1"), "blocage : suivi non rearme")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
tasmota.cmds = []
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
for n: 1 .. 40
    incline(mpu, 40 + n * 0.5)
    pas()
end
verifie(size(stops()) == 0 && tasmota.timers.contains("vrInclinaison1"), "volet qui bouge (2 degres/s) pendant 10 s : pas de blocage")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
tasmota.horloge += 10000                        # volet a l'arret 10 s, au meme angle
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
for n: 1 .. 19    pas()    end
verifie(size(stops()) == 0, "temoin : nouvelle course, repere repris au depart (pas de blocage immediat)")
pas()
verifie(stops() == ["ShutterStop1"], "nouvelle course figee 5 s : blocage")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
tasmota.cmds = []
inclinaison["blocage"] = 0
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
for n: 1 .. 40    pas()    end
verifie(size(stops()) == 0, "blocage 0 : pas de detection")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
inclinaison.remove("blocage")

print("11. Arret en butee : le volet atteint la butee vers laquelle il va -> ShutterStop PUIS recalage")
vrFonctions.etat()["inclinaison"] = {}
tasmota.cmds = []
incline(mpu, 40)
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
incline(mpu, 70)
pas()
verifie(size(stops()) == 0, "ouverture a 70 degres : pas d'arret")
incline(mpu, 86)
pas()
verifie(pilotage() == ["ShutterStop1"], "butee ouverte atteinte : ShutterStop1 tout de suite")
attente()
verifie(pilotage() == ["ShutterStop1", "ShutterSetClose1"], "puis ShutterSetClose1 apres ShutterMotorStop (ShutterSet* ne coupe pas le moteur)")
verifie(!tasmota.timers.contains("vrInclinaison1"), "arret en butee : suivi coupe")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
tasmota.cmds = []
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
verifie(size(tasmota.cmds) == 0, "depart de la butee ouverte vers la fermeture : rien")
incline(mpu, 2)
pas()
attente()
verifie(pilotage() == ["ShutterStop1", "ShutterSetOpen1"], "butee fermee atteinte en fermeture : arret puis recalage")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
tasmota.cmds = []
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
attente()
verifie(pilotage() == ["ShutterStop1", "ShutterSetOpen1"], "deja fermee et commandee en fermeture : arret et recalage")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
tasmota.cmds = []
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
attente()
verifie(pilotage() == ["ShutterStop1"], "temoin : une course reprend avant le delai -> recalage differe abandonne")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
capteurs["capteurOuvert"] = "Switch1"
tasmota.cmds = []
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
incline(mpu, 86)
pas()
verifie(size(tasmota.cmds) == 0, "butee ouverte non designee (Switch1) : ni arret ni recalage par l'inclinaison")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
vrFonctions.etat()["inclinaison"] = {}
incline(mpu, 40)
tasmota.cmds = []
avant = erreurs()
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
incline(mpu, 86)
for n: 1 .. 21    pas()    end
verifie(stops() == ["ShutterStop1"] && erreurs() == avant, "moteur qui force 5 s sur la butee non designee : arret SANS erreur de blocage")
verifie(!vrFonctions.suiviInclinaison(1).find("bloque", false), "butee non designee atteinte : pas d'etat BLOQUE")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
capteurs["capteurOuvert"] = "Inclinaison"
vrFonctions.etat()["inclinaison"] = {}
incline(mpu, 40)
tasmota.cmds = []
tasmota.surCmd = def (c) if c == "ShutterStop1"    vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)    end end
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
incline(mpu, 86)
pas()
tasmota.surCmd = nil
attente()
verifie(pilotage() == ["ShutterStop1", "ShutterSetClose1"], "Direction 0 synchrone pendant ShutterStop : un seul recalage")

print("12. Blocage visible : ligne web et tele/<topic>/INCLINAISON<id> retenu, au changement seulement")
import mqtt as mqttBouchon
import json
var publies = mqttBouchon.publies
publies.clear()
vrFonctions.etat()["inclinaison"] = {}
incline(mpu, 40)
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
for n: 1 .. 20    pas()    end
verifie(string.find(vrFonctions.ligneWebInclinaison(vr1), "BLOQU") > 0, "apres un blocage : ligne web BLOQUE")
verifie(size(publies) == 1 && publies[0][0] == "tele/grenier/INCLINAISON1" && publies[0][2] == true, "blocage publie sur tele/grenier/INCLINAISON1, retenu")
verifie(size(publies) == 1 && json.load(publies[0][1])["Bloque"] == true, "message : Bloque true")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
verifie(size(publies) == 1, "arret apres le blocage : pas de nouvelle publication")
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
verifie(size(publies) == 2 && json.load(publies[1][1])["Bloque"] == false, "nouvelle course : Bloque false publie")
verifie(string.find(vrFonctions.ligneWebInclinaison(vr1), "BLOQU") < 0, "nouvelle course : ligne web normale")
pas()
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
verifie(size(publies) == 2, "course sans blocage : rien de plus publie")

print("13. Sens inverse : l'angle part a l'oppose du sens de course -> ShutterStop + erreur + alerte")
vrFonctions.etat()["inclinaison"] = {}
publies.clear()
tasmota.cmds = []
incline(mpu, 40)
avant = erreurs()
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
incline(mpu, 38)
pas()
verifie(size(stops()) == 0, "2 degres a l'envers : sous le seuil (3), rien")
incline(mpu, 36.5)
pas()
verifie(stops() == ["ShutterStop1"] && erreurs() == avant + 1, "3,5 degres a l'envers : ShutterStop1 et une erreur")
verifie(!tasmota.timers.contains("vrInclinaison1"), "sens inverse : suivi coupe")
verifie(string.find(vrFonctions.ligneWebInclinaison(vr1), "sens inverse") > 0, "ligne web : BLOQUE (sens inverse)")
verifie(size(publies) == 1 && json.load(publies[0][1])["Cause"] == "sens inverse", "MQTT : Cause sens inverse")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
tasmota.cmds = []
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
for n: 1 .. 8
    incline(mpu, 36 - n * 2)
    pas()
end
verifie(size(stops()) == 0, "fermeture dans le bon sens : rien")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
inclinaison["sensInverse"] = 0
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
incline(mpu, 10)
pas()
verifie(size(stops()) == 0, "sensInverse 0 : pas de detection")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
inclinaison.remove("sensInverse")

print("14. Durees de course mesurees butee a butee, proposees pour tempsMontee / tempsDescente")
vr1["tempsMontee"] = 10
vr1["tempsDescente"] = 10
vrFonctions.etat()["inclinaison"] = {}
incline(mpu, 2)
vrFonctions.releveInclinaison(vr1)
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
for n: 1 .. 50
    incline(mpu, 2 + n * 1.67)
    pas()
end
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
vrFonctions.reglageVolets("ReglageVolets", 0, "Inclinaison 1", nil)
verifie(string.find(tasmota.reponse, "ouverture 12.5 s") > 0, "ferme -> ouvert en 50 pas : ouverture 12.5 s mesuree")
verifie(string.find(tasmota.reponse, "tempsMontee 13 (actuel 10)") > 0, "proposition tempsMontee 13, arrondie au-dessus")
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
incline(mpu, 50)
pas()
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
incline(mpu, 2)
pas()
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
vrFonctions.reglageVolets("ReglageVolets", 0, "Inclinaison 1", nil)
verifie(string.find(tasmota.reponse, "fermeture") < 0, "course partie d'entre deux : pas de mesure de fermeture")

print("15. Surveillance a l'arret : une lecture toutes les 'surveillance' s, jamais en course")
def infos(motif)
    var n = 0
    for l: journal    if l[1] == LOG_LEVEL_INFO && string.find(l[0], motif) >= 0    n += 1    end    end
    return n
end
vrFonctions.etat()["inclinaison"] = {}
incline(mpu, 40)
vrFonctions.surveille(vr1)
verifie(!tasmota.timers.contains("vrSurveillance1"), "surveillance 0 (defaut) : aucune minuterie")
inclinaison["surveillance"] = 30
vrFonctions.surveille(vr1)
verifie(tasmota.timers.contains("vrSurveillance1"), "surveillance 30 s : minuterie armee")
incline(mpu, 60)
var bouge = infos("hors manoeuvre")
tasmota.timers["vrSurveillance1"]()
verifie(proche(vrFonctions.suiviInclinaison(1)["angle"], 60), "tick : angle relu (60)")
verifie(infos("hors manoeuvre") == bouge + 1, "trappe bougee a la main : une ligne info")
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
lu = mpu.lectures
tasmota.timers["vrSurveillance1"]()
verifie(mpu.lectures == lu && tasmota.timers.contains("vrSurveillance1"), "en course : pas de lecture, minuterie rearmee")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
attente()                                       # commandes differees des sections precedentes
tasmota.cmds = []
incline(mpu, 88)
tasmota.timers["vrSurveillance1"]()
attente()
verifie(shutterSet() == ["ShutterSetClose1"], "amenee en butee ouverte a la main : recalage")
mpu.accel = nil
tasmota.timers["vrSurveillance1"]()
tasmota.timers["vrSurveillance1"]()
verifie(tasmota.delais["vrSurveillance1"] == 120000, "capteur muet : periode doublee a chaque echec (2 echecs -> 120 s)")
mpu.accel = [0, 0, 16384]
incline(mpu, 88)
tasmota.timers["vrSurveillance1"]()
verifie(tasmota.delais["vrSurveillance1"] == 30000, "capteur revenu : periode normale")
tasmota.remove_timer("vrSurveillance1")
inclinaison["activation"] = "OFF"
vrFonctions.surveille(vr1)
verifie(!tasmota.timers.contains("vrSurveillance1"), "inclinaison OFF : aucune minuterie")
inclinaison["activation"] = "ON"

print("16. Position reelle en % : volet ARRETE seulement, ShutterSetPosition<id> <100 - %ouverture>")
def positions()
    var l = []
    for c: tasmota.cmds    if string.find(c, "ShutterSetPosition") == 0    l.push(c)    end    end
    return l
end
vrFonctions.etat()["inclinaison"] = {}
tasmota.cmds = []
incline(mpu, 44)
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
verifie(size(positions()) == 0, "positionReelle OFF (defaut) : rien")
inclinaison["positionReelle"] = "ON"
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
verifie(size(positions()) == 0, "en course : jamais (ShutterSetPosition ne coupe pas le moteur)")
vrFonctions.positionReelle(vr1, 60)
verifie(size(positions()) == 0, "appel direct en course : refuse aussi")
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
attente()
verifie(positions() == ["ShutterSetPosition1 50"], "arret a 44 degres (50 % ouvert) : ShutterSetPosition1 50")
tasmota.cmds = []
incline(mpu, 45)
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
attente()
verifie(positions() == ["ShutterSetPosition1 49"], "apres une course : renvoyee meme a 1 % (Tasmota a pu deriver en course)")
tasmota.cmds = []
vrFonctions.positionReelle(vr1, 46)
attente()
verifie(size(positions()) == 0, "volet arrete, ecart de 1 % : rien (pas d'ecriture a chaque releve)")
incline(mpu, 20)
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
attente()
verifie(positions() == ["ShutterSetPosition1 79"], "arret a 20 degres (21 % ouvert) : ShutterSetPosition1 79 (ShutterInvert 1)")
vrFonctions.surveille(vr1)                      # surveillance relancee (arretee en fin de section 15)
tasmota.cmds = []
incline(mpu, 70)
tasmota.timers["vrSurveillance1"]()
attente()
verifie(positions() == ["ShutterSetPosition1 18"], "surveillance : trappe bougee a la main -> position corrigee")
tasmota.remove_timer("vrSurveillance1")
inclinaison.remove("surveillance")
inclinaison.remove("positionReelle")

print(echecs == 0 ? "BANC_INCLINAISON: OK" : "BANC_INCLINAISON: ECHEC (" + str(echecs) + ")")
