# Banc de test Berry du mode reglage des durees des volets (data/fs/vrReglage.be, 2026-11-11).
# -----------------------------------------------------------------------------------------------
# Charge le VRAI vrReglage.be et le VRAI vrFonctions.be sous des globaux bouchonnes : Shutter de Tasmota simule
# (liste tasmota.cmds, reponse de ShutterPosition<id> programmable, regles et timers declenches a la main), horloge
# simulee (tasmota.horloge, en ms).
#
# Lancer via son enveloppe Python (deduit racine + berry.exe, code de sortie) :
#     python outils_docs/scripts_python/berry/banc_reglage_volets.py [dossier_sources]
# Ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_reglage_volets.be [dossier_sources]
#
# dossier_sources (defaut data/fs) : pour eprouver une copie (temoin mute) sans toucher a data/fs.
# Copier data/fs EN ENTIER, et passer la copie INTACTE avant la copie mutee (lecon du 2026-10-06).
# Portee : la machine du mode (etapes, ordres envoyes et leur ordre, ecriture du persist, gardes). Ne teste NI le vrai
# Shutter, NI les vrais boutons, NI le moteur. Derniere ligne : BANC_REGLAGE_VOLETS: OK|ECHEC.
import global
import sys
import string
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/volets")      # webserver (groupe 17, routes), en dernier

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

class Driver end
class TasmotaStub
    var refresh, pilotes, commandes
    var cmds, timers, regles, directions, horloge, surCmd, doublons, capteurs, lectures, positions
    var modele, inv, interne, bouge
    var power                       # etats des relais (get_power / set_power), camera de facade (groupe 17c)
    def init() self.refresh = 1500 self.pilotes = [] self.commandes = [] self.cmds = [] self.timers = [] self.regles = {} self.directions = {} self.horloge = 0 self.doublons = 0 self.lectures = 0 self.positions = 0
               self.modele = true self.inv = {} self.interne = {} self.bouge = 0 end
    def millis(d) return self.horloge + (d == nil ? 0 : d) end
    def time_reached(t) return self.horloge >= t end
    # Regle de xdrv_27_esp32_shutter.ino : ShutterOpen/Close visent la position interne 100 / 0 SANS ShutterInvert ;
    # ShutterSetOpen/Close passent par CmndShutterSetPosition, qui pose 100 - x si ShutterInvert (inv[id], pose par le test).
    # Une course qui change la position compte dans 'bouge' et, si 'modele', rapporte Direction +-1 a la regle du reglage.
    def shutter(c)
        for p: [["ShutterSetOpen", 100, false], ["ShutterSetClose", 0, false], ["ShutterOpen", 100, true], ["ShutterClose", 0, true]]
            var reste = c[size(p[0]) ..]
            if string.find(c, p[0]) != 0 || size(reste) == 0 || str(int(reste)) != reste    continue    end
            var id = int(reste)
            if !p[2]    self.interne[id] = self.inv.find(id, false) ? 100 - p[1] : p[1]    return    end
            if self.interne.find(id, -1) == p[1]    return    end
            self.bouge += 1
            self.interne[id] = p[1]
            var f = self.regles.find(string.format("Shutter%i#Direction|vrReglage_Direction", id))
            if self.modele && f != nil    f(p[1] == 100 ? 1 : -1, string.format("Shutter%i#Direction", id), {})    end
            return
        end
    end
    def cmd(c, m)
        self.cmds.push(c)
        self.shutter(c)
        if self.surCmd != nil    self.surCmd(c)    end
        if c == "ShutterMotorStop"    return {"ShutterMotorStop": 500}    end
        if c == "WebRefresh"    return self.refresh == nil ? {} : {"WebRefresh": self.refresh}    end
        if string.find(c, "ShutterPosition") == 0    self.positions += 1    end      # relance le moteur : jamais envoye
        return {}
    end
    # JSON des capteurs (FUNC_JSON_APPEND du Shutter) ; 'capteurs' force un texte (absent, illisible)
    def read_sensors()
        import json
        self.lectures += 1
        if self.capteurs != nil    return self.capteurs    end
        var j = {"Time": "2026-11-11T12:00:00"}
        for id: self.directions.keys()    j["Shutter" + str(id)] = {"Position": 0, "Direction": self.directions[id], "Target": 0, "Tilt": 0}    end
        return json.dump(j)
    end
    def get_power() return self.power end
    def set_power(i, v) self.power[i] = v end
    # Le vrai set_timer AJOUTE sans dedoublonner (tasmota_class.be) : un doublon d'id est compte
    def set_timer(d, f, id)
        for t: self.timers    if t[0] == id    self.doublons += 1    end    end
        self.timers.push([id, f, d])
    end
    def remove_timer(id)
        var i = 0
        while i < size(self.timers)
            if self.timers[i][0] == id    self.timers.remove(i)    else    i += 1    end
        end
    end
    def add_rule(pat, f, id) self.regles[pat + "|" + str(id)] = f end
    def remove_rule(pat, id) self.regles.remove(pat + "|" + str(id)) end
    def yield() end
    def add_driver(d) self.pilotes.push(d) end
    def add_cmd(n, f) self.commandes.push(n) end
end
var tasmota = TasmotaStub()

def bp(id, fonction) return {"activation": "ON", "id": id, "function": fonction, "mqtt": "OFF"} end
var vr1 = {"activation": "ON", "nom": "Volet porte", "id": 1, "inverse": 0, "relais1": 1, "tempsMontee": 15, "tempsDescente": 16,
           "boutons": {"bouton1": {"activation": "OFF", "id": -1, "function": "toggle", "mqtt": "OFF"}, "bouton2": bp(1, "up"), "bouton3": bp(2, "down")}}
var vr2 = {"activation": "ON", "nom": "Volet cuisine", "id": 2, "inverse": 0, "relais1": 3, "tempsMontee": 15, "tempsDescente": 16,
           "boutons": {"bouton2": bp(3, "up"), "bouton3": bp(4, "down")}}
var vr3 = {"activation": "ON", "nom": "Trappe", "id": 3, "inverse": 0, "relais1": 5, "tempsMontee": 15, "tempsDescente": 16,
           "boutons": {"bouton1": bp(5, "toggle")}}
var voletsMoteur = {"activation": "ON", "mode": 1, "environnement": {"VRs": {"VR1": vr1, "VR2": vr2, "VR3": vr3}}}
var drivers = {"voletRoulants": voletsMoteur}
var modules = {}                      # persist.modules : interrupteurs du maitre lus par vrPages.finsDeCourse (groupe 17b)
var persist = {}
var serveur = {"mqtt": {"topic": "grenier"}}

import vrFonctions
import vrReglage
import persist as persistBouchon
import configGlobal

var params = []                       # [commande, valeur] passes a configGlobal.testeParam (durees remises)
configGlobal.testeParam = def (c, v, t) params.push([c, v]) return false end
var appelsConfig = 0
var configOrig = vrFonctions.configVRByJson
vrFonctions.configVRByJson = def () appelsConfig += 1 configOrig() end

var echecs = 0
def verifie(c, nom)
    print((c ? "  ok   " : "  ECHEC ") + nom)
    if !c    echecs += 1    end
end
var T = 0                             # origine du groupe en cours (ms)
def reinit()
    vrFonctions.etat().remove("reglage")
    vrFonctions.etat().remove("inclinaison")
    drivers["voletRoulants"] = voletsMoteur
    tasmota.cmds = []
    tasmota.timers = []
    tasmota.regles = {}
    tasmota.directions = {}
    tasmota.surCmd = nil
    tasmota.capteurs = nil
    tasmota.lectures = 0
    tasmota.doublons = 0
    tasmota.modele = true
    tasmota.inv = {}
    tasmota.interne = {}
    tasmota.bouge = 0
    tasmota.horloge += 1000000
    T = tasmota.horloge
    for vr: [vr1, vr2, vr3]
        vr["activation"] = "ON"
        vr["inverse"] = 0
        vr["tempsMontee"] = 15
        vr["tempsDescente"] = 16
    end
    params.clear()
end
def idx(n, etat, ancien) return (etat << 16) | (ancien << 8) | (n - 1) end
def appuie(n, t) tasmota.horloge = T + t return vrReglage.bouton(idx(n, 0, 1)) end
def page(id, t) tasmota.horloge = T + t return vrReglage.appui(id, "page") end
def regle(id, valeur)
    var f = tasmota.regles.find(string.format("Shutter%i#Direction|vrReglage_Direction", id))
    if f != nil    f(valeur, string.format("Shutter%i#Direction", id), {})    end
end
def aRegle(id) return tasmota.regles.contains(string.format("Shutter%i#Direction|vrReglage_Direction", id)) end
def nbTimers(id)
    var n = 0
    for t: tasmota.timers    if t[0] == id    n += 1    end    end
    return n
end
def declenche(prefixe)
    var a = []
    var i = 0
    while i < size(tasmota.timers)
        if string.find(tasmota.timers[i][0], prefixe) == 0    a.push(tasmota.timers[i][1])    tasmota.timers.remove(i)    else    i += 1    end
    end
    for f: a    f()    end
    return size(a)
end
def attente() declenche("vrShutter") end              # recalages differes par commandeArret (ShutterMotorStop)
# Ordres envoyes, sans les lectures (ShutterMotorStop, ShutterPosition<id> sans argument)
def ordres()
    var l = []
    for c: tasmota.cmds
        if c == "ShutterMotorStop" || (string.find(c, "ShutterPosition") == 0 && string.find(c, " ") < 0)    continue    end
        l.push(c)
    end
    return l
end
# Ordres de course et de recalage seuls (ni durees, ni boutons, ni Interlock)
def courses()
    var l = []
    for c: ordres()
        for p: ["ShutterOpen", "ShutterClose", "ShutterSetOpen", "ShutterSetClose", "ShutterStop", "ShutterToggle"]
            if string.find(c, p) == 0 && string.find(c, "Duration") < 0    l.push(c)    break    end
        end
    end
    return l
end
def memes(a, b)
    if size(a) != size(b)    return false    end
    for x: a    if b.find(x) == nil    return false    end    end
    return true
end
def param(nom)
    var r = nil
    for p: params    if p[0] == nom    r = p[1]    end    end
    return r
end
def erreurs()
    var n = 0
    for l: journal    if l[1] == LOG_LEVEL_ERREUR    n += 1    end    end
    return n
end
def etape() return vrReglage.etatPage()["etape"] end

print("1. Aucun reglage encore : etatPage minimal, bouton non consomme")
var e = vrReglage.etatPage()
verifie(!e["actif"] && e.find("etape") == nil, "etatPage : actif faux, etape nil")
verifie(!vrReglage.bouton(idx(1, 0, 1)), "bouton : non consomme")

print("2. Deroule complet, 2 boutons (up 1, down 2) : ordres exacts, durees 14 et 13 s, un seul save")
reinit()
tasmota.surCmd = def (c) if c == "ShutterStop1"    regle(1, 0)    end end   # arret rapporte pendant la commande
var r = vrReglage.debut(1)
verifie(r[0], "debut accepte : " + str(r[1]))
var o = ordres()
verifie(tasmota.lectures == 1, "debut : direction lue dans le JSON des capteurs")
verifie(size(o) == 7 && o[0] == "ShutterOpenDuration1 130" && o[1] == "ShutterCloseDuration1 130" && o[2] == "ShutterButton1 0" && o[6] == "ShutterSetClose1",
        "debut : course allongee a 130 s (au-dela du delai de 120 s), boutons du volet retires, position fermee")
verifie(size(o) == 7 && memes(o[3..5], ["ShutterButton2 3 up 0", "ShutterButton2 4 down 0", "ShutterButton3 5 toggle 0"]), "debut : boutons des autres volets renvoyes (Button1)")
verifie(vrFonctions.enReglage(1) && !vrFonctions.enReglage(2), "enReglage(1) vrai, (2) faux")
e = vrReglage.etatPage()
verifie(e["actif"] && e["etape"] == "pret" && e["id"] == 1 && e["cle"] == "VR1" && e["nom"] == "Volet porte" && e["type"] == "moteur", "etatPage : pret, VR1, nom, moteur")
verifie(memes(e["boutons"], [1, 2]) && e["avant"]["tempsMontee"] == 15 && e["avant"]["tempsDescente"] == 16, "etatPage : boutons 1 et 2, durees d'avant 15 et 16")
verifie(e["mesures"].find("tempsMontee") == nil && e["chrono_ms"] == 0 && e["mpu"] == nil, "etatPage : ni mesure, ni chrono, ni MPU")
verifie(nbTimers("vrReglage_delai") == 1 && aRegle(1), "delai arme, regle d'arret posee")
tasmota.cmds = []
verifie(appuie(2, 1000), "appui du bouton down a l'etape de montee : consomme")
verifie(ordres() == ["ShutterOpen1"] && etape() == "montee", "montee : ShutterOpen1 (sens impose par l'etape)")
tasmota.horloge = T + 6000
verifie(vrReglage.etatPage()["chrono_ms"] == 5000, "chrono 5 s en montee")
verifie(vrReglage.bouton(idx(2, 1, 0)) && etape() == "montee", "relache du bouton : consomme, pas d'etape")
tasmota.cmds = []
appuie(1, 15400)
verifie(ordres() == ["ShutterStop1"] && etape() == "haut", "haut : ShutterStop1, arret rapporte aussitot sans annuler")
verifie(vrFonctions.suiviInclinaison(1).find("arret") == T + 15400, "haut : suivi arret pose (recalage differe)")
attente()
verifie(ordres() == ["ShutterStop1", "ShutterSetOpen1"], "haut : position ouverte recalee apres ShutterMotorStop")
verifie(vrReglage.etatPage()["mesures"]["tempsMontee"] == 14, "tempsMontee : 14,4 s -> 14")
tasmota.cmds = []
appuie(2, 17000)
verifie(ordres() == ["ShutterClose1"] && etape() == "descente", "descente : ShutterClose1")
tasmota.cmds = []
params.clear()
var sauves = persistBouchon.nb_save
var config = appelsConfig
appuie(1, 29600)
o = ordres()
verifie(size(o) > 0 && o[0] == "ShutterStop1" && o.find("ShutterSetClose1") == nil, "fini : ShutterStop1 d'abord, recalage differe")
verifie(vr1["tempsMontee"] == 14 && vr1["tempsDescente"] == 13 && type(vr1["tempsDescente"]) == "int", "durees 14 et 13 (12,6 s) ecrites, entieres")
verifie(persistBouchon.nb_save == sauves + 1 && persistBouchon.drivers == drivers, "persist.drivers = drivers, save une fois")
verifie(appelsConfig == config + 1 && param("ShutterOpenDuration1") == 14 && param("ShutterCloseDuration1") == 13, "configVRByJson : durees remises (14, 13)")
verifie(o.find("ShutterButton1 1 up 0") != nil && o.find("ShutterButton1 2 down 0") != nil, "configVRByJson : boutons du volet remis")
attente()
verifie(ordres()[-1] == "ShutterSetClose1", "fini : position fermee recalee apres ShutterMotorStop")
e = vrReglage.etatPage()
verifie(!e["actif"] && e["etape"] == "fini" && e["mesures"]["tempsDescente"] == 13 && !vrFonctions.enReglage(1), "etatPage : fini, inactif, mesures gardees")
verifie(nbTimers("vrReglage_delai") == 0 && !aRegle(1) && tasmota.doublons == 0, "sortie : delai et regle retires, jamais deux delais")
verifie(!vrReglage.bouton(idx(1, 0, 1)), "apres la sortie : bouton non consomme")

print("3. Bouton unique toggle : meme deroule, ShutterOpen puis ShutterClose quoi que dise le bouton")
reinit()
vrReglage.debut(3)
verifie(memes(vrReglage.etatPage()["boutons"], [5]), "boutons du volet : [5]")
appuie(5, 1000)
appuie(5, 15000)
attente()
appuie(5, 17000)
appuie(5, 30000)
attente()
verifie(courses() == ["ShutterSetClose3", "ShutterOpen3", "ShutterStop3", "ShutterSetOpen3", "ShutterClose3", "ShutterStop3", "ShutterSetClose3"], "toggle : sens impose par l'etape")
verifie(vr3["tempsMontee"] == 14 && vr3["tempsDescente"] == 13 && etape() == "fini", "toggle : durees 14 et 13 ecrites")

print("3b. Exception apres l'ecriture du persist (recalage) : sortie fini quand meme, une erreur")
reinit()
vrReglage.debut(1)
page(1, 1000)
page(1, 15000)
page(1, 17000)
tasmota.surCmd = def (c) if c == "ShutterMotorStop"    raise "io_error", "panne simulee"    end end
nbErr = erreurs()
try    page(1, 30000)    except .. as x, y    print("  (exception sortie de appui : " + str(x) + ")")    end
tasmota.surCmd = nil
verifie(etape() == "fini" && !vrReglage.etatPage()["actif"] && vr1["tempsDescente"] == 13, "exception apres l'ecriture : etape fini, inactif, durees ecrites")
verifie(erreurs() == nbErr + 1 && nbTimers("vrReglage_delai") == 0 && !aRegle(1), "exception apres l'ecriture : une erreur, delai et regle retires")

print("4. inverse 1 (ShutterInvert 1) : ordres de course jamais croises, recalages croises ; le volet bouge a chaque appui")
reinit()
vr3["inverse"] = 1
tasmota.inv[3] = true                                # ShutterInvert3 1, pose par configVRByJson sur la carte
vrReglage.debut(3)
verifie(tasmota.interne.find(3) == 0, "debut : position interne 0 (ferme) apres le recalage")
page(3, 1000)
verifie(tasmota.bouge == 1 && etape() == "montee", "montee : le volet bouge (interne 0 -> 100)")
page(3, 15000)
attente()
verifie(tasmota.interne.find(3) == 100 && etape() == "haut", "haut : position interne 100 (ouvert) apres le recalage")
page(3, 17000)
verifie(tasmota.bouge == 2 && etape() == "descente", "descente : le volet bouge (interne 100 -> 0)")
page(3, 30000)
attente()
verifie(etape() == "fini" && vr3["tempsMontee"] == 14 && vr3["tempsDescente"] == 13, "inverse 1 : fini, durees 14 et 13 ecrites")
verifie(courses() == ["ShutterSetOpen3", "ShutterOpen3", "ShutterStop3", "ShutterSetClose3", "ShutterClose3", "ShutterStop3", "ShutterSetOpen3"], "inverse 1 : ouvre = ShutterOpen, posFerme = ShutterSetOpen")

print("4b. Arrivee d'une course sans aucun Direction non nul : refus, rien d'ecrit")
reinit()
tasmota.modele = false                               # le moteur ne part pas : aucune regle Direction
vrReglage.debut(1)
page(1, 1000)
tasmota.cmds = []
sauves = persistBouchon.nb_save
config = appelsConfig
r = page(1, 15000)
verifie(!r[0] && etape() == "refus" && string.find(vrReglage.etatPage()["message"], "n'a pas bougé") >= 0, "arrivee sans depart vu : refus, « n'a pas bougé »")
verifie(ordres()[0] == "ShutterStop1" && persistBouchon.nb_save == sauves && vr1["tempsMontee"] == 15 && appelsConfig == config + 1, "sans depart vu : stop, rien d'ecrit, configVRByJson")

print("4c. Ecriture du persist en echec : durees d'avant remises, sortie annule, une erreur")
reinit()
vrReglage.debut(1)
page(1, 1000)
page(1, 15000)
page(1, 17000)
var saveOrig = persistBouchon.save
persistBouchon.save = def (force) raise "io_error", "flash pleine simulee" end
params.clear()
nbErr = erreurs()
config = appelsConfig
r = page(1, 30000)
persistBouchon.save = saveOrig
verifie(!r[0] && etape() == "annule" && !vrReglage.etatPage()["actif"], "save en echec : etape annule, inactif")
verifie(vr1["tempsMontee"] == 15 && vr1["tempsDescente"] == 16 && erreurs() == nbErr + 1, "save en echec : 15 et 16 remis, une erreur")
verifie(appelsConfig == config + 1 && param("ShutterOpenDuration1") == 15 && param("ShutterCloseDuration1") == 16, "save en echec : configVRByJson avec les durees d'avant")

print("5. Annulation en montee : stop, rien d'ecrit, configVRByJson rappele")
reinit()
vrReglage.debut(1)
page(1, 1000)
tasmota.cmds = []
sauves = persistBouchon.nb_save
config = appelsConfig
vrReglage.annule("annule")
o = ordres()
verifie(size(o) > 0 && o[0] == "ShutterStop1", "annulation : ShutterStop1")
verifie(persistBouchon.nb_save == sauves && vr1["tempsMontee"] == 15 && vr1["tempsDescente"] == 16, "annulation : rien d'ecrit")
verifie(appelsConfig == config + 1 && o.find("ShutterButton1 1 up 0") != nil, "annulation : configVRByJson rappele (boutons remis)")
verifie(etape() == "annule" && !vrReglage.etatPage()["actif"] && !aRegle(1) && nbTimers("vrReglage_delai") == 0, "annulation : etape annule, regle et delai retires")
reinit()
vrReglage.debut(1)
tasmota.cmds = []
vrReglage.annule("annule")
verifie(ordres().find("ShutterStop1") == nil && etape() == "annule", "annulation avant la montee : aucun ShutterStop")

print("6. Delai de 120 s : stop, etape delai, une erreur au journal")
reinit()
vrReglage.debut(1)
page(1, 1000)
verifie(nbTimers("vrReglage_delai") == 1 && tasmota.timers[-1][2] == 120000 && tasmota.doublons == 0, "delai rearme a 120 s, sans doublon")
tasmota.cmds = []
var nbErr = erreurs()
sauves = persistBouchon.nb_save
config = appelsConfig
verifie(declenche("vrReglage_delai") == 1, "timer du delai declenche")
verifie(ordres()[0] == "ShutterStop1" && etape() == "delai" && !vrReglage.etatPage()["actif"], "delai : ShutterStop1, etape delai")
verifie(erreurs() == nbErr + 1 && persistBouchon.nb_save == sauves && appelsConfig == config + 1, "delai : une erreur, rien d'ecrit, configVRByJson")
verifie(!aRegle(1), "delai : regle retiree")

print("7. Rebond : deux appuis a 300 ms -> une seule etape")
reinit()
vrReglage.debut(1)
tasmota.cmds = []
verifie(page(1, 1000)[0], "1er appui (page) accepte")
verifie(appuie(1, 1300), "2e appui (bouton, 300 ms apres) : consomme")
verifie(courses() == ["ShutterOpen1"] && etape() == "montee", "une seule etape : montee")
verifie(!page(1, 1600)[0] && etape() == "montee", "3e appui 600 ms apres le 1er : ignore")
vrReglage.annule("annule")

print("8. Mesure de 1,5 s : refusee, rien d'ecrit")
reinit()
vrReglage.debut(1)
page(1, 1000)
tasmota.cmds = []
sauves = persistBouchon.nb_save
config = appelsConfig
r = page(1, 2500)
verifie(!r[0] && etape() == "refus" && !vrReglage.etatPage()["actif"], "1,5 s : refus, sortie du mode")
verifie(ordres()[0] == "ShutterStop1" && persistBouchon.nb_save == sauves && vr1["tempsMontee"] == 15 && appelsConfig == config + 1, "1,5 s : stop, rien d'ecrit, configVRByJson")

print("9. En course : le JSON des capteurs donne Direction 1 -> refus, aucun ordre ; JSON absent ou illisible : accepte")
reinit()
tasmota.directions[1] = 1
r = vrReglage.debut(1)
verifie(!r[0] && size(tasmota.cmds) == 0 && tasmota.lectures == 1, "en course : refus, aucune commande")
verifie(vrFonctions.etat().find("reglage") == nil && size(tasmota.timers) == 0 && size(tasmota.regles) == 0, "en course : rien de modifie")
tasmota.directions[1] = 0
verifie(vrReglage.debut(1)[0], "Direction 0 : accepte")
vrReglage.annule("annule")
reinit()
tasmota.capteurs = "{}"
verifie(vrReglage.debut(1)[0], "Shutter1 absent du JSON : accepte")
vrReglage.annule("annule")
reinit()
tasmota.capteurs = "pas du json"
verifie(vrReglage.debut(1)[0], "JSON illisible : accepte")
vrReglage.annule("annule")

print("10. Refus du debut : volet inconnu, inactif, reglage deja actif")
reinit()
verifie(!vrReglage.debut(9)[0] && size(tasmota.cmds) == 0, "volet 9 inconnu : refus, aucune commande")
vr2["activation"] = "OFF"
verifie(!vrReglage.debut(2)[0] && size(tasmota.cmds) == 0, "volet inactif : refus, aucune commande")
vr2["activation"] = "ON"
vrReglage.debut(1)
tasmota.cmds = []
verifie(!vrReglage.debut(2)[0] && size(tasmota.cmds) == 0, "second reglage pendant un premier : refus, aucune commande")
verifie(vrFonctions.enReglage(1) && vrReglage.etatPage()["id"] == 1, "le premier reglage continue")

vrReglage.annule("annule")
reinit()
vrFonctions.suiviInclinaison(1)["arret"] = T - 500             # ShutterMotorStop 500 ms + 100 : debut permis a T + 100
r = vrReglage.debut(1)
verifie(!r[0] && r[1] == "Le volet vient de s'arrêter : réessayez dans une seconde" && size(ordres()) == 0 && vrReglage.etat() == nil, "arret il y a 500 ms : refus, aucun ordre")
tasmota.horloge = T + 100
verifie(vrReglage.debut(1)[0], "arret il y a 600 ms : accepte")
vrReglage.annule("annule")

print("10b. Volet SANS MPU : changementDirection note l'arret et la course ; recalage differe retenu si la course reprend")
reinit()
tasmota.horloge = T + 5000
vrFonctions.changementDirection(1, "Shutter1#Direction", {}, 1)
verifie(vrFonctions.suiviInclinaison(1)["enCourse"], "Direction 1 : en course")
tasmota.horloge = T + 9000
vrFonctions.changementDirection(0, "Shutter1#Direction", {}, 1)
verifie(vrFonctions.suiviInclinaison(1).find("arret") == T + 9000 && !vrFonctions.suiviInclinaison(1)["enCourse"], "Direction 0 : arret note, plus en course")
tasmota.horloge = T + 9200
r = vrReglage.debut(1)
verifie(!r[0] && r[1] == "Le volet vient de s'arrêter : réessayez dans une seconde" && vrReglage.etat() == nil, "arret il y a 200 ms (sans MPU) : refus")
tasmota.cmds = []
vrFonctions.commandeArret(1, "ShutterSetOpen1")
verifie(nbTimers("vrShutterSetOpen1") == 1 && size(ordres()) == 0, "recalage juste apres l'arret : differe")
vrFonctions.changementDirection(-1, "Shutter1#Direction", {}, 1)
attente()
verifie(ordres().find("ShutterSetOpen1") == nil, "course reprise avant le delai : recalage differe non envoye")

print("10c. Un AUTRE volet roule : refus, aucun ordre (ShutterOpen/CloseDuration rappellent ShutterInit pour tous)")
reinit()
tasmota.directions[1] = 0
tasmota.directions[2] = -1
r = vrReglage.debut(1)
verifie(!r[0] && string.find(r[1], "volet 2 roule") >= 0 && size(tasmota.cmds) == 0 && vrReglage.etat() == nil, "volet 2 en course : refus nommant le volet 2, aucune commande")
tasmota.directions[2] = 0
verifie(vrReglage.debut(1)[0], "volet 2 arrete : accepte")
vrReglage.annule("annule")
reinit()
vrReglage.debut(1)
tasmota.cmds = []

print("11. Bouton d'un autre volet : non consomme")
verifie(!vrReglage.bouton(idx(3, 0, 1)) && !vrReglage.bouton(idx(4, 1, 0)), "boutons 3 et 4 (volet 2) : non consommes")
verifie(etape() == "pret" && size(ordres()) == 0, "aucune etape, aucun ordre")
verifie(!vrReglage.appui(2, "page")[0], "appui sur un autre volet : refuse")
vrReglage.annule("annule")

print("12. Chrono du garage (mode 3) : aucun ordre Shutter* ni Power*, durees ecrites")
reinit()
var garage = {"activation": "ON", "nom": "Porte du garage", "id": 1, "inverse": 1, "relais1": 1, "tempsMontee": 20, "tempsDescente": 20, "boutons": {}}
drivers["voletRoulants"] = {"activation": "ON", "mode": 3, "environnement": {"VRs": {"VR1": garage}}}
verifie(vrReglage.debut(1)[0] && vrReglage.etatPage()["type"] == "chrono" && size(vrReglage.etatPage()["boutons"]) == 0, "debut : type chrono, aucun bouton")
verifie(size(tasmota.cmds) == 0 && size(tasmota.regles) == 0, "debut : aucune commande, aucune regle")
verifie(!vrReglage.appui(1, "bouton")[0] && etape() == "pret", "appui 'bouton' refuse")
sauves = persistBouchon.nb_save
config = appelsConfig
page(1, 1000)
page(1, 19000)
page(1, 21000)
page(1, 38000)
var pilote = false
for c: tasmota.cmds    if string.find(c, "Shutter") == 0 || string.find(c, "Power") == 0    pilote = true    end    end
verifie(!pilote && etape() == "fini", "chrono : aucun Shutter* ni Power*, fini")
verifie(garage["tempsMontee"] == 18 && garage["tempsDescente"] == 17 && persistBouchon.nb_save == sauves + 1 && appelsConfig == config + 1, "chrono : 18 et 17 ecrits, save et configVRByJson une fois")
reinit()
drivers["voletRoulants"] = {"activation": "ON", "mode": 3, "environnement": {"VRs": {"VR1": garage}}}
vrReglage.debut(1)
page(1, 1000)
config = appelsConfig
vrReglage.annule("annule")
verifie(size(tasmota.cmds) == 0 && appelsConfig == config && etape() == "annule", "chrono annule : aucune commande, pas de configVRByJson")
vrReglage.debut(1)
declenche("vrReglage_delai")
verifie(etape() == "delai" && string.find(vrReglage.etatPage()["message"], "arrêté") < 0, "chrono : delai sans « volet arrêté » (aucun ordre envoye)")
reinit()
garage["capteursPosition"] = {"activation": "ON", "capteurOuvert": "Interrupteur7"}
drivers["voletRoulants"] = {"activation": "ON", "mode": 3, "environnement": {"VRs": {"VR1": garage}}}
vrReglage.debut(1)
page(1, 1000)
verifie(!vrFonctions.enReglage(1), "chrono actif : enReglage faux (fins de course laissees telles quelles)")
vrFonctions.capteurVirtuel(7, "ON")
attente()
verifie(tasmota.cmds.find("ShutterSetClose1") != nil, "chrono actif : capteurVirtuel recale la porte (ShutterSetClose1, inverse 1)")
vrReglage.annule("annule")
garage.remove("capteursPosition")

print("13. Arret inattendu en montee (sens inverse du MPU) : annule, cause rendue, rien d'ecrit")
reinit()
vrReglage.debut(1)
page(1, 1000)
regle(1, 1)
verifie(etape() == "montee", "Direction 1 : rien")
var suivi = vrFonctions.suiviInclinaison(1)
suivi["bloque"] = true
suivi["cause"] = "sens inverse"
tasmota.cmds = []
sauves = persistBouchon.nb_save
config = appelsConfig
nbErr = erreurs()
regle(1, 0)
e = vrReglage.etatPage()
verifie(e["etape"] == "annule" && e["cause"] == "sens inverse" && !e["actif"], "Direction 0 subie : annule, cause sens inverse")
verifie(persistBouchon.nb_save == sauves && vr1["tempsMontee"] == 15 && appelsConfig == config + 1 && erreurs() == nbErr + 1, "rien d'ecrit, configVRByJson, une erreur")
verifie(!aRegle(1) && ordres().find("ShutterStop1") == nil, "regle retiree, aucun ShutterStop (moteur deja coupe)")

print("14. Arret rapporte en retard puis arret subi en descente : cause bloque ; sans MPU : arret")
reinit()
vrReglage.debut(1)
page(1, 1000)
page(1, 15000)
regle(1, 0)                                         # arret de la montee, rapporte apres la commande
verifie(etape() == "haut", "arret de la montee rapporte en retard : sans effet")
page(1, 17000)
suivi = vrFonctions.suiviInclinaison(1)
suivi["bloque"] = true
suivi["cause"] = "blocage"
regle(1, -1)
regle(1, 0)
verifie(etape() == "annule" && vrReglage.etatPage()["cause"] == "bloque", "arret subi en descente : annule, cause bloque")
reinit()
vrReglage.debut(1)
page(1, 1000)
regle(1, 1)
regle(1, 0)
verifie(etape() == "annule" && vrReglage.etatPage()["cause"] == "arret", "arret subi sans MPU : cause arret")

print("14b. Direction 0 avant le vrai depart : ignore ; valeur passee en map : meme traitement")
def sansModele() reinit() tasmota.modele = false end        # Direction rapportes a la main seulement
sansModele()
vrReglage.debut(1)
page(1, 1000)
regle(1, 0)
verifie(etape() == "montee" && vrReglage.etatPage()["actif"], "Direction 0 avant tout Direction 1 : ignore")
regle(1, 1)
regle(1, 0)
verifie(etape() == "annule" && vrReglage.etatPage()["cause"] == "arret", "Direction 1 puis 0 : arret subi")
sansModele()
vrReglage.debut(1)
page(1, 1000)
regle(1, {"Direction": 0})
verifie(etape() == "montee", "map Direction 0 avant le depart : ignore")
regle(1, {"Direction": 1})
regle(1, {"Direction": 0})
verifie(etape() == "annule" && vrReglage.etatPage()["cause"] == "arret", "map Direction 1 puis 0 : arret subi")
sansModele()
vrReglage.debut(1)
page(1, 1000)
regle(1, 1)
page(1, 15000)
regle(1, 0)                                         # notre arret de la montee
page(1, 17000)
regle(1, 0)                                         # 0 rapporte avant le vrai depart de la descente
verifie(etape() == "descente", "descente : Direction 0 avant son depart ignore (indicateur remis au depart)")
vrReglage.annule("annule")

print("14c. Depart d'une course : recalage differe encore en attente retire")
reinit()
vrReglage.debut(1)
page(1, 1000)
page(1, 15000)
verifie(nbTimers("vrShutterSetOpen1") == 1, "haut : recalage ShutterSetOpen1 en attente")
page(1, 17000)
verifie(nbTimers("vrShutterSetOpen1") == 0 && nbTimers("vrShutterSetClose1") == 0, "depart de la descente : recalage retire")
verifie(courses().find("ShutterSetOpen1") == nil, "aucun ShutterSetOpen1 envoye")
vrReglage.annule("annule")

print("15. Durees du MPU : videes au debut, rendues dans mpu")
reinit()
vrFonctions.suiviInclinaison(1)["durees"] = {"ouverture": 9.0}
vrReglage.debut(1)
verifie(vrFonctions.suiviInclinaison(1).find("durees") == nil && vrReglage.etatPage()["mpu"] == nil, "debut : durees du MPU videes, mpu nil")
vrFonctions.suiviInclinaison(1)["durees"] = {"ouverture": 14.2}
e = vrReglage.etatPage()
verifie(e["mpu"] != nil && e["mpu"]["tempsMontee"] == 14.2 && e["mpu"].find("tempsDescente") == nil, "mpu : tempsMontee 14,2, tempsDescente nil")
vrReglage.annule("annule")

print("16. Exception pendant le debut : boutons remis, erreur au journal")
reinit()
tasmota.surCmd = def (c) if c == "ShutterButton1 0"    raise "io_error", "panne simulee"    end end
config = appelsConfig
nbErr = erreurs()
r = vrReglage.debut(1)
tasmota.surCmd = nil
verifie(!r[0] && !vrFonctions.enReglage(1) && appelsConfig == config + 1 && erreurs() == nbErr + 1, "exception : refus, configVRByJson, une erreur")
verifie(!aRegle(1) && nbTimers("vrReglage_delai") == 0, "exception : ni regle ni delai")

print("17. Pages : facade, accueil, routes /volets, branchement du driver")
reinit()
import webserver
import json
import gestionFileFolder        # bouchon partage : la fonction d'envoi est ajoutee ici seulement, le fichier n'est pas touche
gestionFileFolder.readFileByLineAndContentSend = def (chemin) webserver.content_send("[" + chemin + "]") end
vr1["facade"] = {"type": "porte", "place": 3}
vr2["facade"] = {"type": "fenetre", "place": 1}
vr3["facade"] = {"type": "trappe", "place": 2}
vr1["nom"] = "Volet <b>porte</b> <!--"
import controleVoletRoulants            # driver importe SANS facade : il ne doit rien enregistrer
var pilote = global.controleVRoulant
verifie(pilote != nil && size(tasmota.pilotes) == 1, "driver instancie par import (init)")
webserver.raz()
pilote.web_add_handler()
pilote.web_add_config_button()
pilote.web_add_main_button()
verifie(size(webserver.routes) == 0 && size(webserver.envoye) == 0, "sans bloc facade : ni route, ni bouton, ni accueil")
import vrPages
verifie(vrPages.facade() == nil, "facade() nil sans bloc facade")
voletsMoteur["facade"] = {"activation": "OFF", "toit": "unPan"}
verifie(vrPages.facade() == nil, "facade() nil si activation OFF")
webserver.raz()
vrPages.accueil()
vrPages.bouton()
verifie(size(webserver.envoye) == 0, "facade inactive : rien dans l'accueil, pas de bouton")
voletsMoteur["facade"] = {"activation": "ON", "toit": "deuxPans"}
var onOrig = webserver.on
webserver.on = def (c, f, m) raise "io_error", "routes refusees" end
var nbPilotes = size(tasmota.pilotes)
nbErr = erreurs()
controleVoletRoulants.init(controleVoletRoulants)        # 3 volets actifs, routes en echec
webserver.on = onOrig
verifie(size(tasmota.pilotes) == nbPilotes + 1 && erreurs() == nbErr + 1, "init : routes en echec -> un seul driver de plus, une erreur")
vr3["capteursPosition"] = {"activation": "ON", "inclinaison": {"activation": "ON", "angleOuvert": 80, "angleFerme": 5}}
var f = vrPages.facade()
verifie(f != nil && f["toit"] == "deuxPans" && f["rafraichissement"] == 1500 && size(f["ouvertures"]) == 3, "facade : toit, WebRefresh 1500, 3 ouvertures")
var o = f["ouvertures"]
verifie(o[0]["id"] == 2 && o[1]["id"] == 3 && o[2]["id"] == 1 && o[0]["place"] == 1 && o[2]["type"] == "porte", "ouvertures triees par place")
verifie(o[0]["nom"] == "Volet cuisine" && o[0]["inverse"] == 0 && o[0]["tempsMontee"] == 15 && o[0]["tempsDescente"] == 16, "ouverture : nom, inverse, durees")
verifie(o[0].find("inclinaison") == nil && o[1]["inclinaison"]["ouvert"] == 80 && o[1]["inclinaison"]["ferme"] == 5, "inclinaison posee pour le seul volet a MPU")
tasmota.refresh = nil
verifie(vrPages.facade()["rafraichissement"] == 2345, "WebRefresh absent : 2345")
tasmota.refresh = 1500
vr2["activation"] = "OFF"
verifie(size(vrPages.facade()["ouvertures"]) == 2, "volet inactif : sans dessin")
vr2["activation"] = "ON"
vr1.remove("inverse")         # cle absente : 1, comme vrFonctions.inverse et ShutterInvert (configVRByJson)
o = vrPages.facade()["ouvertures"]
verifie(o[2]["id"] == 1 && o[2]["inverse"] == 1 && o[0]["inverse"] == 0, "inverse absent : 1 ; inverse 0 : 0")
vr1["inverse"] = 0

webserver.raz()
vrPages.accueil()
var t = webserver.texte()
verifie(string.find(t, "<div id='vf'></div><script>window.VOLETS=") == 0 && string.find(t, "[/sd/js/volets.js]") > 0 && t[-9..] == "</script>", "accueil : div, donnees, volets.js, fermeture")
var jv = t[string.find(t, "VOLETS=") + 7 .. string.find(t, ";</script>") - 1]
verifie(string.find(jv, "<") < 0 && json.load(jv)["ouvertures"][2]["nom"] == "Volet <b>porte</b> <!--", "accueil : tout « < » echappe dans le JSON, nom relu intact")
webserver.raz()
pilote.web_add_main_button()
verifie(webserver.texte() == t, "driver : web_add_main_button envoie l'accueil")
webserver.raz()
pilote.web_add_config_button()
verifie(string.find(webserver.texte(), "action='/volets'") > 0 && string.find(webserver.texte(), "Réglage des volets") > 0, "driver : bouton « Réglage des volets » vers /volets")
webserver.raz()
webserver.routes = []
pilote.web_add_handler()
verifie(size(webserver.routes) == 2 && webserver.routes[0][0] == "/volets" && webserver.routes[0][2] == webserver.HTTP_GET && webserver.routes[1][2] == webserver.HTTP_POST, "driver : routes GET et POST /volets")

# Acces : sans Referer (acces non privilegie), ni la page, ni l'etat, ni l'ordre ne repondent
webserver.privilegie = false
for g: [vrPages.route, vrPages.ordre]
    webserver.raz({"f": "etat", "action": "debut", "id": "1"})
    g()
    verifie(webserver.code == nil && size(webserver.envoye) == 0 && !webserver.ferme, "acces refuse : rien envoye")
end
verifie(!vrFonctions.enReglage(1), "acces refuse : aucun reglage commence")
webserver.privilegie = true

# GET ?f=etat
tasmota.cmds = []
webserver.raz({"f": "etat"})
vrPages.route()
verifie(webserver.code == 200 && webserver.mime == "application/json" && webserver.ferme && json.load(webserver.texte())["actif"] == false, "?f=etat : etatPage en JSON, reglage inactif")
# POST debut, appui
def poste(action, id, etape)
    var a = {}
    if action != nil    a["action"] = action    end
    if id != nil    a["id"] = id    end
    if etape != nil    a["etape"] = etape    end
    webserver.raz(a)
    vrPages.ordre()
    return webserver.code == nil ? nil : [webserver.code, json.load(webserver.texte())]
end
tasmota.horloge = T + 1000
var r = poste("debut", "1")
verifie(r[0] == 200 && r[1]["ok"] == true && r[1]["etat"]["actif"] && r[1]["etat"]["etape"] == "pret" && webserver.ferme, "POST debut : ok, etape pret")
tasmota.horloge = T + 5000
webserver.raz()
vrPages.bouton()
verifie(tasmota.cmds.find("WebRefresh") == nil && size(webserver.envoye) == 1, "?f=etat, POST et bouton : facade testee sans etre construite (aucun WebRefresh)")
r = poste("appui", "1", "pret")
verifie(r[0] == 200 && r[1]["ok"] == true && r[1]["etat"]["etape"] == "montee", "POST appui : montee")
tasmota.horloge = T + 19000
tasmota.cmds = []
r = poste("appui", "1", "pret")
verifie(r[0] == 409 && r[1]["ok"] == false && r[1]["message"] == "L'étape a changé : état relu" && r[1]["etat"]["etape"] == "montee" && size(ordres()) == 0,
        "POST appui, etape affichee perimee (pret) : 409, etat relu joint, aucun ordre")
verifie(poste("appui", "1")[0] == 409 && etape() == "montee", "POST appui sans temoin : 409")
r = poste("appui", "1", "montee")
verifie(r[1]["etat"]["etape"] == "haut", "POST appui : haut")
webserver.raz({"f": "etat"})
vrPages.route()
verifie(json.load(webserver.texte())["etape"] == "haut", "?f=etat suit l'etape")
r = poste("annuler", "1")
verifie(r[0] == 200 && r[1]["ok"] == true && !r[1]["etat"]["actif"] && !vrFonctions.enReglage(1), "POST annuler : reglage termine")
r = poste("debut", "99")
verifie(r[0] == 200 && r[1]["ok"] == false && r[1]["message"] != "" && !r[1]["etat"]["actif"], "POST debut volet inconnu : refus, ok faux")
r = poste("bidon", "1")
verifie(r[0] == 400 && r[1]["ok"] == false && !vrFonctions.enReglage(1), "action inconnue : 400, rien commence")
r = poste(nil, nil)
verifie(r[0] == 400, "sans action : 400")
# Exception : 500 JSON, reponse fermee, une erreur au journal
var debutOrig = vrReglage.debut
vrReglage.debut = def (id) raise "panne", "simulee" end
nbErr = erreurs()
r = poste("debut", "1")
vrReglage.debut = debutOrig
verifie(r[0] == 500 && webserver.ferme && erreurs() == nbErr + 1, "exception : 500 JSON, reponse fermee, une erreur")
# Exception APRES un ordre reussi (etatPage de la reponse) : 500 quand meme, jamais une reponse fermee sans ouverture
var etatPageOrig = vrReglage.etatPage
vrReglage.etatPage = def () raise "panne", "simulee" end
r = poste("debut", "1")
vrReglage.etatPage = etatPageOrig
verifie(r != nil && r[0] == 500 && webserver.ferme, "exception dans etatPage : 500 JSON, reponse fermee")
vrReglage.annule("annule")
# Page de reglage
webserver.raz()
vrPages.route()
t = webserver.texte()
verifie(string.find(t, "[start ") == 0 && webserver.termine, "page : demarree et terminee")
var iCss = string.find(t, "[/sd/css/reglageVolets.css]")
var iHtml = string.find(t, "[/sd/html/reglageVolets.html]")
var iDonnees = string.find(t, "window.VOLETS_REGLAGE=")
var iJs = string.find(t, "[/sd/js/reglageVolets.js]")
verifie(iCss > 0 && iHtml > iCss && iDonnees > iHtml && iJs > iDonnees, "page : css, html, donnees, js dans l'ordre")
# button_pressed du driver : un reglage actif consomme les boutons du volet, jamais ceux des autres
verifie(!pilote.button_pressed("", idx(1, 0, 1)), "button_pressed : false sans reglage")
tasmota.horloge = T + 40000
vrReglage.debut(1)
verifie(pilote.button_pressed("", idx(2, 0, 1)) && !pilote.button_pressed("", idx(4, 0, 1)), "button_pressed : bouton du volet en reglage vrai, autre volet faux")
vrReglage.annule("annule")
# Facade du garage (2026-11-13, plan facade-garage-capteurs A1) : decor et fins de course (etat des interrupteurs du maitre)
print("17b. Facade du garage : decor, finsDeCourse, GET /volets?f=capteurs")
var sw = def (id, nom, etat) return {"activation": "ON", "nom": nom, "id": id, "etat": etat} end
modules = {"garage": {"environnement": {"interrupteurs": {"interrupteur1": sw(1, "Capteur Fermeture Rideau Garage", "ON"),
                                                               "interrupteur2": sw(2, "Capteur Ouverture Rideau Garage", "OFF")}}}}
webserver.privilegie = true
var nbErr2 = erreurs()
f = vrPages.facade()
verifie(f.find("decor") == nil && f["ouvertures"][2].find("finsDeCourse") == nil, "sans decor ni finsDeCourse : cles nil (facade des greniers inchangee)")
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(webserver.code == 200 && size(json.load(webserver.texte())) == 0, "?f=capteurs sans finsDeCourse : {}")
voletsMoteur["facade"]["decor"] = ["chevrefeuille", "porte", "pergola"]
vr1["facade"]["finsDeCourse"] = {"module": "garage", "ouverture": 2, "fermeture": 1}
f = vrPages.facade()
verifie(f.find("decor") == ["chevrefeuille", "porte", "pergola"], "facade : decor lu dans drivers.voletRoulants.facade.decor")
verifie(f["ouvertures"][2]["id"] == 1 && f["ouvertures"][2]["finsDeCourse"]["ouverture"] == "Capteur Ouverture Rideau Garage" && f["ouvertures"][2]["finsDeCourse"]["fermeture"] == "Capteur Fermeture Rideau Garage", "facade : finsDeCourse porte les NOMS des interrupteurs (id 2 = ouverture, id 1 = fermeture)")
verifie(f["ouvertures"][0].find("finsDeCourse") == nil && f["ouvertures"][1].find("finsDeCourse") == nil, "facade : les autres volets sans finsDeCourse")
vr1["facade"]["finsDeCourse"]["ouverture"] = 9
verifie(vrPages.facade()["ouvertures"][2]["finsDeCourse"]["ouverture"] == nil, "facade : interrupteur introuvable -> nom nil (la page met un nom par defaut)")
vr1["facade"]["finsDeCourse"]["ouverture"] = 2
tasmota.cmds = []
webserver.raz({"f": "capteurs"})
vrPages.route()
var c = json.load(webserver.texte())
verifie(webserver.code == 200 && webserver.mime == "application/json" && webserver.ferme && size(c) == 1 && c["1"]["ouverture"] == "OFF" && c["1"]["fermeture"] == "ON" && size(c["1"]) == 2, "?f=capteurs : {id du VR: {ouverture: OFF, fermeture: ON}} lu dans etat des interrupteurs")
verifie(tasmota.cmds.find("WebRefresh") == nil, "?f=capteurs : facade non construite (aucun WebRefresh)")
modules["garage"]["environnement"]["interrupteurs"]["interrupteur2"]["etat"] = "ON"
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(json.load(webserver.texte())["1"]["ouverture"] == "ON", "?f=capteurs suit l'etat : ouverture passee a ON")
modules["garage"]["environnement"]["interrupteurs"]["interrupteur2"].remove("etat")
modules["garage"]["environnement"]["interrupteurs"]["interrupteur1"]["etat"] = "n'importe quoi"
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(size(json.load(webserver.texte())["1"]) == 0, "?f=capteurs : etat absent ou inconnu -> cle absente (inconnu, pastille grise)")
var modOrig = modules["garage"]
modules.remove("garage")
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(webserver.code == 200 && size(json.load(webserver.texte())["1"]) == 0, "?f=capteurs : module absent -> {} pour le volet, pas d'exception")
modules["garage"] = modOrig
webserver.privilegie = false
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(webserver.code == nil && size(webserver.envoye) == 0, "?f=capteurs : acces refuse, rien envoye")
webserver.privilegie = true
voletsMoteur["facade"]["activation"] = "OFF"
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(webserver.code == 404 && webserver.ferme, "?f=capteurs : facade inactive -> 404")
voletsMoteur["facade"]["activation"] = "ON"
verifie(erreurs() == nbErr2, "?f=capteurs : aucune erreur loguee (acces refuse, 404 et module absent compris)")
# Camera de facade du RDC (2026-11-13) : relais declare par facade.camera, etat par get_power, commande par POST action=camera
print("17c. Camera de facade : facade().camera, etat dans ?f=capteurs, POST action=camera")
var nbErr3 = erreurs()
modules["autres"] = {"activation": "ON", "environnement": {"relais": {"relai1": {"activation": "OFF", "nom": "Caméra de façade", "id": 7}}}}
voletsMoteur["facade"]["camera"] = {"module": "autres", "id": 7}
tasmota.power = [false, false, false, false, false, false, true]
verifie(vrPages.facade().find("camera") == nil, "camera : relais inactif -> camera nil (aucun voyant)")
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(json.load(webserver.texte()).find("camera") == nil, "?f=capteurs : relais inactif -> pas de cle camera")
modules["autres"]["environnement"]["relais"]["relai1"]["activation"] = "ON"
f = vrPages.facade()
verifie(f["camera"] != nil && f["camera"]["id"] == 7 && f["camera"]["nom"] == "Caméra de façade", "facade : camera {nom, id} du relais d'id 7")
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(json.load(webserver.texte())["camera"] == "ON", "?f=capteurs : camera ON (bit 6 de get_power)")
tasmota.power[6] = false
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(json.load(webserver.texte())["camera"] == "OFF", "?f=capteurs : camera OFF")
tasmota.power = [false]
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(json.load(webserver.texte()).find("camera") == nil, "?f=capteurs : Power7 absent de get_power -> etat inconnu, pas de cle")
webserver.raz({"action": "camera", "etat": "ON"})
vrPages.ordre()
verifie(webserver.code == 400 && !json.load(webserver.texte())["ok"] && tasmota.power == [false], "POST camera, Power7 absent de get_power : 400, rien commande")
tasmota.power = [false, false, false, false, false, false, false]
webserver.raz({"action": "camera", "etat": "ON"})
vrPages.ordre()
var rc = json.load(webserver.texte())
verifie(webserver.code == 200 && rc["ok"] && tasmota.power[6] == true && rc["message"] == "Caméra de façade allumée", "POST camera ON : set_power(6, true), 200")
webserver.raz({"action": "camera", "etat": "OFF"})
vrPages.ordre()
verifie(webserver.code == 200 && tasmota.power[6] == false, "POST camera OFF : set_power(6, false)")
webserver.raz({"action": "camera", "etat": "peut-etre"})
vrPages.ordre()
verifie(webserver.code == 400 && !json.load(webserver.texte())["ok"] && tasmota.power[6] == false, "POST camera, etat invalide : 400, rien commande")
webserver.privilegie = false
webserver.raz({"action": "camera", "etat": "ON"})
vrPages.ordre()
verifie(webserver.code == nil && tasmota.power[6] == false, "POST camera : acces refuse, rien commande")
webserver.privilegie = true
voletsMoteur["facade"].remove("camera")
webserver.raz({"action": "camera", "etat": "ON"})
vrPages.ordre()
verifie(webserver.code == 400 && tasmota.power[6] == false, "POST camera sans camera declaree : 400, rien commande")
verifie(erreurs() == nbErr3 + 3, "camera : les trois refus (Power absent, etat invalide, camera absente) logues en erreur")
# Projecteur du garage (2026-11-14) : facade.lampe, meme mecanisme que la camera
print("17d. Projecteur de facade : facade().lampe, etat dans ?f=capteurs, POST action=lampe")
modules["garage"] = {"activation": "ON", "environnement": {"relais": {"relai5": {"activation": "ON", "nom": "Projecteur de Garage", "id": 5}}}}
voletsMoteur["facade"]["lampe"] = {"module": "garage", "id": 5}
tasmota.power = [false, false, false, false, true]
f = vrPages.facade()
verifie(f["lampe"] != nil && f["lampe"]["id"] == 5 && f["lampe"]["nom"] == "Projecteur de Garage", "facade : lampe {nom, id} du relais d'id 5")
webserver.raz({"f": "capteurs"})
vrPages.route()
verifie(json.load(webserver.texte())["lampe"] == "ON", "?f=capteurs : lampe ON (bit 4 de get_power)")
# Renommer le relais ne casse pas le lien (module + id) : meme appareil, nouveau nom partout
modules["garage"]["environnement"]["relais"]["relai5"]["nom"] = "Eclairage pergola"
f = vrPages.facade()
verifie(f["lampe"] != nil && f["lampe"]["id"] == 5 && f["lampe"]["nom"] == "Eclairage pergola", "lampe : relais renomme, toujours trouve par son id, nouveau nom repris")
webserver.raz({"action": "lampe", "etat": "OFF"})
vrPages.ordre()
rc = json.load(webserver.texte())
verifie(webserver.code == 200 && rc["ok"] && tasmota.power[4] == false && rc["message"] == "Eclairage pergola éteint", "POST lampe OFF (nom repris) : set_power(4, false), 200")
voletsMoteur["facade"].remove("lampe")
webserver.raz({"action": "lampe", "etat": "ON"})
vrPages.ordre()
verifie(webserver.code == 400 && tasmota.power[4] == false, "POST lampe sans lampe declaree : 400, rien commande")
modules.remove("garage")
modules.remove("autres")
voletsMoteur["facade"].remove("decor")
vr1["facade"].remove("finsDeCourse")
for v: [vr1, vr2, vr3]    v.remove("facade")    end
vr3.remove("capteursPosition")
voletsMoteur.remove("facade")


verifie(tasmota.positions == 0, "aucun ShutterPosition envoye par le module, de tout le banc")
print(echecs == 0 ? "BANC_REGLAGE_VOLETS: OK" : "BANC_REGLAGE_VOLETS: ECHEC (" + str(echecs) + ")")
