# Banc de test Berry de l'AFFICHAGE de l'ecran de la cave par MQTT (plan ecran-cave-vues-commandes, A6, 2026-11-12) :
#   data/cave/tasmota32s3-ecran/ecranCaveFonctions.be  (modele des valeurs, peremption : le VRAI)
#   data/cave/tasmota32s3-ecran/controleEcranCave.be   (abonnements MQTT : le VRAI)
# Persist lu : data/cave/tasmota32s3-ecran/_persist.json (modules.ecranCave.sources et peremption reels, module active par le banc).
# Bouchons : bouchons_berry/fsmqtt/ (mqtt : abonnements rappelables, publications memorisees ; logFonctions : JOURNAL).
#
# Lancer par son enveloppe : python outils_docs/scripts_python/berry/banc_ecran_cave.py   (code de sortie 0 = vert)
# (verdict = DERNIERE ligne, BANC_ECRAN_CAVE: OK | ECHEC (n)).
#
# CE QU'IL PROUVE : les topics sont lus dans le persist ; un SENSOR (AM2301, PompeVideCave), un STATE ou RESULT (POWER1 a 5)
# du serveur de la cave et le SENSOR de la cuve (taux, volume) alimentent le modele ; une valeur est « perimee » apres le delai
# du persist (et tant que rien n'est recu : broker absent) ; un JSON invalide ou un champ inattendu n'arrete rien.
# A5 : touche(n) pousse le mot (seq << 1) | voulu au registre 32 + n - 1 par modbusFonctions.pousseEtat (bouchon), seq propre a chaque
# touche (1 a 127, jamais 0), refus si l'etat est perime, relance du meme mot toutes les 2 s (5 au plus) jusqu'a l'etat MQTT voulu ;
# la touche 5 (redemarrage) n'est jamais relancee. NE TESTE PAS : le vrai broker, l'ecran (A7), le serveur (banc_commandes_ecran).
import global
import sys
import string
import json

sys.path().push("data/fs")
sys.path().push("data/cave/tasmota32s3-ecran")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/ecran_cave")   # modbusFonctions (pousseEtat memorise)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/fsmqtt")   # le dernier pousse l'emporte : mqtt, logFonctions
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/ecran_cave_haspmota")   # A7 : display, haspmota, lv, path de l'interface HASPmota
if size(global._argv) > 1    sys.path().push(global._argv[1])    end   # dossier d'un ecranCaveHaspmota.be modifie (mutant) : il l'emporte sur le vrai

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var JOURNAL = []
class Driver end
import mqtt
import logFonctions
global.logFonctions = logFonctions

var modules = {}
class TasmotaStub
    var ms, rules, cmds, timers, regles, heure
    def init() self.ms = 100000 self.rules = {} self.cmds = [] self.timers = [] self.regles = [] self.heure = 1800000000 end
    def millis(n) return self.ms end
    def add_rule(a, f, id) self.rules[id] = f self.regles.push([a, f, id]) end
    def rtc() return {"local": self.heure} end
    def strftime(fmt, t) return "12:34" end
    def remove_rule(a, id) self.rules.remove(id) end
    def add_driver(d) end
    def set_timer(ms, f, id) self.timers.push([self.ms + ms, f, id]) end
    def remove_timer(id)
        var reste = []
        for t: self.timers    if t[2] != id    reste.push(t)    end    end
        self.timers = reste
    end
    # fait avancer l'horloge de d ms en declenchant les minuteries echues, dans l'ordre
    def avance(d)
        var fin = self.ms + d
        while true
            var i = -1
            for k: 0 .. size(self.timers) - 1
                if self.timers[k][0] <= fin && (i < 0 || self.timers[k][0] < self.timers[i][0])    i = k    end
            end
            if i < 0    break    end
            var t = self.timers[i]
            self.timers.remove(i)
            if t[0] > self.ms    self.ms = t[0]    end
            t[1]()
        end
        self.ms = fin
    end
    def cmd(s) self.cmds.push(s) end
    def yield() end
end
var tasmota = TasmotaStub()
global.tasmota = tasmota

def lis(chemin)
    var f = open(chemin, "r")
    var s = f.read()
    f.close()
    return s
end

var echecs = 0
var nbControles = 0
def verifie(nom, attendu, obtenu)
    nbControles += 1
    var ok = (str(attendu) == str(obtenu))
    print((ok ? "  ok   " : "  ECHEC ") + nom + (ok ? "" : " : attendu " + str(attendu) + ", obtenu " + str(obtenu)))
    if !ok    echecs += 1    end
end

# Etat neuf pour chaque scenario : persist de l'ecran (module actif), broker relie, modules recharges.
import modbusFonctions
import ecranCaveFonctions
var FONCTIONS = ecranCaveFonctions
var controleEcranCave = nil
var CONTROLE = nil
def monte(relie)
    var persist = json.load(lis("data/cave/tasmota32s3-ecran/_persist.json"))
    modules = persist["modules"]
    global.modules = modules
    modules["ecranCave"]["activation"] = "ON"
    tasmota.ms = 100000
    tasmota.rules = {}
    tasmota.regles = []
    tasmota.cmds = []
    tasmota.timers = []
    modbusFonctions.pushs = []
    modbusFonctions.injoignable = false
    mqtt.publies.clear()
    mqtt.abonnes = {}
    mqtt.connecte = (relie != false)
    JOURNAL.clear()
    FONCTIONS.valeurs = {}                             # module importe (comme sur la carte) : etat remis a neuf a la main
    FONCTIONS.derniere = {}
    FONCTIONS.reinitialise()                           # seq et relances des touches
    var c = compile(lis("data/cave/tasmota32s3-ecran/controleEcranCave.be"))
    c()
    CONTROLE = controleEcranCave
end
def recu(topic, texte)
    var f = mqtt.abonnes.find(topic)
    if f != nil    f(topic, 0, texte, bytes().fromstring(texte))    end
end
def v(cle)
    var m = FONCTIONS.modele()["valeurs"].find(cle)
    return m == nil ? "nil" : str(m["valeur"]) + (m["perime"] ? "!" : "")
end
def erreurs()
    var n = 0
    for l: JOURNAL    if l[1] == 1    n += 1    end    end
    return n
end

var CAVE = "cave/serveur-rly-cave-v2"
var CUVE = "jardin/cuve"

print("--- topics_lus_dans_le_persist")
monte()
var attendus = ["stat/" + CAVE + "/RESULT", "stat/" + CAVE + "/STATUS10", "tele/" + CAVE + "/SENSOR", "tele/" + CAVE + "/STATE", "tele/" + CUVE + "/SENSOR"]
var manquants = []
for t: attendus    if !mqtt.abonnes.contains(t)    manquants.push(t)    end    end
verifie("cinq abonnements aux topics du persist (aucun manquant)", "[]", str(manquants))
verifie("rien d'autre abonne", 5, size(mqtt.abonnes))
modules["ecranCave"]["sources"]["cave"] = "autre/topic"
modules["ecranCave"]["sources"]["cuve"] = "x/y"
mqtt.abonnes = {}
CONTROLE = compile(lis("data/cave/tasmota32s3-ecran/controleEcranCave.be"))
CONTROLE()
verifie("topics changes dans le persist : nouveaux abonnements", "true/false", str(mqtt.abonnes.contains("tele/autre/topic/SENSOR")) + "/" + str(mqtt.abonnes.contains("tele/" + CAVE + "/SENSOR")))

print("--- sensor_cave_lu")
monte()
recu("tele/" + CAVE + "/SENSOR", '{"Time":"2026-11-12T10:00:00","AM2301":{"Temperature":12.5,"Humidity":71.2,"DewPoint":7.5},"PompeVideCave":{"Pompe":"ON","Manuel":"OFF","Niveaux":{"Bas":"ON","Haut":"OFF"},"Alerte":""},"TempUnit":"C"}')
verifie("temperature et humidite", "12.5/71.2", v("temperature") + "/" + v("humidite"))
verifie("pompe, manuel, flotteurs", "ON/OFF/ON/OFF", v("pompe") + "/" + v("manuel") + "/" + v("niveauBas") + "/" + v("niveauHaut"))
verifie("aucune alerte", 0, size(FONCTIONS.modele()["alertes"]))
recu("tele/" + CAVE + "/SENSOR", '{"PompeVideCave":{"Pompe":"OFF","Manuel":"OFF","Niveaux":{"Bas":"OFF","Haut":"ON"},"Alerte":"incoherence des flotteurs"}}')
verifie("alerte de la pompe dans le modele", "['incoherence des flotteurs']", str(FONCTIONS.modele()["alertes"]))
verifie("une valeur absente d'un SENSOR garde la precedente", "12.5", v("temperature"))
recu("stat/" + CAVE + "/STATUS10", '{"StatusSNS":{"AM2301":{"Temperature":13.5,"Humidity":70.0}}}')
verifie("STATUS10 (reponse a la demande de connexion) lu comme un SENSOR", "13.5", v("temperature"))

print("--- power_lu_par_result")
monte()
recu("stat/" + CAVE + "/RESULT", '{"POWER3":"ON"}')
verifie("RESULT : relais 3 ON, les autres inconnus", "ON/nil", v("power3") + "/" + v("power1"))
recu("tele/" + CAVE + "/STATE", '{"Time":"x","POWER1":"OFF","POWER2":"OFF","POWER3":"OFF","POWER4":"ON","POWER5":"OFF","Wifi":{"RSSI":50}}')
verifie("STATE : POWER1 a 5", "OFF/OFF/OFF/ON/OFF", v("power1") + "/" + v("power2") + "/" + v("power3") + "/" + v("power4") + "/" + v("power5"))

print("--- cuve_lue")
monte()
recu("tele/" + CUVE + "/SENSOR", '{"sensorsCuve":{"valeursAnalogiques":{"valeurCapteurHauteur":1200},"niveauCuve":{"hauteurEau":40.0,"tauxRemplissage":0.62,"volume":3100}}}')
verifie("taux (0..1) et volume en L", "0.62/3100", v("taux") + "/" + v("volume"))
recu("tele/" + CUVE + "/SENSOR", '{"autre":1}')
verifie("SENSOR sans sensorsCuve : valeurs gardees", "0.62/3100", v("taux") + "/" + v("volume"))

print("--- perime_apres_delai")
monte()
verifie("rien recu (broker absent) : tout perime", "true/true", str(FONCTIONS.perime("cave")) + "/" + str(FONCTIONS.perime("cuve")))
recu("tele/" + CAVE + "/SENSOR", '{"AM2301":{"Temperature":12.5,"Humidity":71.2}}')
recu("tele/" + CUVE + "/SENSOR", '{"sensorsCuve":{"niveauCuve":{"tauxRemplissage":0.5,"volume":2500}}}')
verifie("juste recu : frais", "false/false", str(FONCTIONS.perime("cave")) + "/" + str(FONCTIONS.perime("cuve")))
tasmota.ms += 900 * 1000
verifie("a 900 s exactement : encore frais", "false", FONCTIONS.perime("cave"))
tasmota.ms += 1000
verifie("a 901 s : perime, valeurs marquees", "true/12.5!/0.5!", str(FONCTIONS.perime("cave")) + "/" + v("temperature") + "/" + v("taux"))
recu("tele/" + CAVE + "/STATE", '{"POWER1":"ON"}')
verifie("nouveau message de la cave : cave fraiche, cuve toujours perimee", "false/true", str(FONCTIONS.perime("cave")) + "/" + str(FONCTIONS.perime("cuve")))
modules["ecranCave"]["peremption"]["cuve"] = 60
verifie("delai du persist respecte (cuve 60 s)", "true", FONCTIONS.perime("cuve"))
verifie("source inconnue : perimee", "true", FONCTIONS.perime("nimporte"))
tasmota.ms = 100000 - 5
verifie("horloge qui recule : jamais fraiche par erreur", "true", FONCTIONS.perime("cave"))

print("--- json_invalide_ignore_sans_planter")
monte()
recu("tele/" + CAVE + "/SENSOR", '{"AM2301":{"Temperature":12.5}}')
var exc = nil
try
    recu("tele/" + CAVE + "/SENSOR", '{pas du json')
    recu("tele/" + CAVE + "/STATE", '')
    recu("tele/" + CUVE + "/SENSOR", '[1,2')
    recu("tele/" + CAVE + "/SENSOR", '{"AM2301":"texte","PompeVideCave":5}')
    recu("stat/" + CAVE + "/RESULT", '{"POWER3":{"x":1}}')
except .. as e, m
    exc = str(e) + " " + str(m)
end
verifie("aucune exception", "nil", str(exc))
verifie("valeur valide gardee", "12.5", v("temperature"))
verifie("JSON invalide : une erreur journalisee par message illisible, au moins", true, erreurs() >= 1)
monte()
recu("tele/" + CAVE + "/SENSOR", '{"AM2301":{"Temperature":12.5}}')
tasmota.ms += 1000 * 1000
recu("tele/" + CAVE + "/SENSOR", '{pas du json')
recu("tele/" + CAVE + "/STATE", '')
verifie("un JSON invalide ne rafraichit pas l'heure : cave toujours perimee, valeur gardee", "true/12.5!", str(FONCTIONS.perime("cave")) + "/" + v("temperature"))

print("--- connexion_demande_l_etat")
monte(true)
verifie("broker deja relie : STATE et STATUS 10 demandes",
    "cmnd/" + CAVE + "/STATE|cmnd/" + CAVE + "/STATUS|10", str(mqtt.publies[0][0]) + "|" + str(mqtt.publies[1][0]) + "|" + str(mqtt.publies[1][1]))
monte(false)
verifie("avant la connexion : rien publie", 0, size(mqtt.publies))
tasmota.rules["ecran_cave_mqtt"]()
verifie("Mqtt#Connected : deux demandes", 2, size(mqtt.publies))

# Touches (A5) : etat frais de la cave, puis appui
def cave_fraiche(power3, power5)
    recu("tele/" + CAVE + "/STATE", '{"POWER1":"OFF","POWER2":"OFF","POWER3":"' + power3 + '","POWER4":"OFF","POWER5":"' + power5 + '"}')
end
def pushs()
    return str(modbusFonctions.pushs)
end

print("--- touche_pousse_mot")
monte()
cave_fraiche("OFF", "ON")
verifie("touche 1 (power3 OFF) : envoye", "envoye", FONCTIONS.touche(1))
verifie("registre 32, mot (seq 1 << 1) | ON = 3", "[[32, 'uint16', 3]]", pushs())
modbusFonctions.pushs = []
verifie("touche 2 (power5 ON) : voulu OFF, registre 33, mot (1 << 1) | OFF = 2", "envoye [[33, 'uint16', 2]]", FONCTIONS.touche(2) + " " + pushs())
modbusFonctions.pushs = []
FONCTIONS.touche(3)
verifie("touche 3 (power4) : registre 34", "34", modbusFonctions.pushs[0][0])
modbusFonctions.pushs = []
FONCTIONS.touche(4)
verifie("touche 4 (power1) : registre 35", "35", modbusFonctions.pushs[0][0])
modbusFonctions.pushs = []
verifie("numero absent du persist : inconnu, rien pousse", "inconnu/0", FONCTIONS.touche(9) + "/" + str(size(modbusFonctions.pushs)))

print("--- seq_avance_jamais_zero")
monte()
cave_fraiche("OFF", "OFF")
var seqs = []
for i: 1 .. 130
    FONCTIONS.touche(1)
    seqs.push(modbusFonctions.pushs[size(modbusFonctions.pushs) - 1][2] >> 1)
end
verifie("seq 1, 2 puis 127 au 127e appui, retour a 1 au 128e", "1/2/127/1/2", str(seqs[0]) + "/" + str(seqs[1]) + "/" + str(seqs[126]) + "/" + str(seqs[127]) + "/" + str(seqs[128]))
var zero = 0
for q: seqs    if q == 0 || q > 127    zero += 1    end    end
verifie("jamais 0 ni au-dessus de 127", 0, zero)
monte()
cave_fraiche("OFF", "OFF")
FONCTIONS.touche(1)
FONCTIONS.touche(1)
FONCTIONS.touche(2)
verifie("seq propre a chaque touche : touche 2 repart de 1", "[[32, 'uint16', 3], [32, 'uint16', 5], [33, 'uint16', 3]]", pushs())

print("--- refus_si_perime")
monte()
verifie("rien recu (broker absent) : refuse, rien pousse", "refuse/0", FONCTIONS.touche(1) + "/" + str(size(modbusFonctions.pushs)))
cave_fraiche("OFF", "OFF")
tasmota.avance(901 * 1000)
verifie("etat vieux de 901 s : refuse, rien pousse", "refuse/0", FONCTIONS.touche(1) + "/" + str(size(modbusFonctions.pushs)))
cave_fraiche("OFF", "OFF")
verifie("etat frais a nouveau : envoye", "envoye", FONCTIONS.touche(1))
monte()
cave_fraiche("OFF", "OFF")
modbusFonctions.injoignable = true
verifie("maitre injoignable (pousseEtat nil) : refuse, aucune relance", "refuse/0", FONCTIONS.touche(1) + "/" + str(size(tasmota.timers)))
monte()
verifie("touche 5 sans etat recu : pas d'etat a verifier, envoyee", "envoye", FONCTIONS.touche(5))

print("--- relance_jusqu_a_confirmation")
monte()
cave_fraiche("OFF", "OFF")
FONCTIONS.touche(1)
tasmota.avance(1999)
verifie("avant 2 s : un seul push", 1, size(modbusFonctions.pushs))
tasmota.avance(1)
verifie("a 2 s : meme mot, meme registre", "[[32, 'uint16', 3], [32, 'uint16', 3]]", pushs())
tasmota.avance(2000)
verifie("a 4 s : troisieme push identique", 3, size(modbusFonctions.pushs))
cave_fraiche("ON", "OFF")
tasmota.avance(10000)
verifie("etat recu = voulu : plus de relance", 3, size(modbusFonctions.pushs))
verifie("aucune minuterie en attente", 0, size(tasmota.timers))
monte()
cave_fraiche("OFF", "OFF")
FONCTIONS.touche(1)
FONCTIONS.touche(1)
tasmota.avance(2000)
verifie("deuxieme appui avant confirmation : l'ancienne relance est annulee", "[[32, 'uint16', 3], [32, 'uint16', 5], [32, 'uint16', 5]]", pushs())

print("--- abandon_apres_5")
monte()
cave_fraiche("OFF", "OFF")
FONCTIONS.touche(1)
var avant = erreurs()
tasmota.avance(60 * 1000)
verifie("1 envoi + 5 relances, pas une de plus", 6, size(modbusFonctions.pushs))
verifie("une erreur journalisee a l'abandon", 1, erreurs() - avant)
verifie("aucune minuterie en attente", 0, size(tasmota.timers))
var mots = {}
for p: modbusFonctions.pushs    mots[p[2]] = 1    end
verifie("tous les push portent le meme mot", 1, size(mots))

print("--- redemarrer_toujours_on")
monte()
cave_fraiche("OFF", "OFF")
FONCTIONS.touche(5)
FONCTIONS.touche(5)
verifie("touche 5 : registre 36, ON (bit 0), seq 1 puis 2", "[[36, 'uint16', 3], [36, 'uint16', 5]]", pushs())

print("--- touche_redemarre_sans_relance")
monte()
FONCTIONS.touche(5)
tasmota.avance(60 * 1000)
verifie("un seul push malgre 60 s", 1, size(modbusFonctions.pushs))
verifie("aucune minuterie", 0, size(tasmota.timers))

print("--- persist_de_l_ecran")
monte()
var bt = modules["ecranCave"]["environnement"]["boutons"]
var ok = size(bt) == 5
for k: bt.keys()
    var b = bt[k]
    if !(b["type"] == 32 && b["pin"] == -1 && b["virtuel"] != "OFF" && b["activation"] == "ON" && b["id"] >= 1 && b["id"] <= 5)    ok = false    end
end
verifie("5 boutons virtuels type 32, ids 1 a 5, sans broche (pin -1, virtuel : ni GPIO ni regle Button)", true, ok)
verifie("correspondance touche -> etat", "power3/power5/power4/power1/redemarre", str(modules["ecranCave"]["touches"]["1"]) + "/" + str(modules["ecranCave"]["touches"]["2"]) + "/" + str(modules["ecranCave"]["touches"]["3"]) + "/" + str(modules["ecranCave"]["touches"]["4"]) + "/" + str(modules["ecranCave"]["touches"]["5"]))

# ======================================================================================================================
# A7 : interface HASPmota (ecranCaveHaspmota.be) sur les objets de pages.jsonl (simules : attributs gardes dans une map)
# ======================================================================================================================
var DOSSIER = "data/cave/tasmota32s3-ecran/"
var GLYPHE_ON = "\xEE\x9B\xA8"      # U+E6E8 lightbulb-on
var GLYPHE_OFF = "\xEE\x8C\xB5"     # U+E335 lightbulb
class ObjetEcran
    var attr
    def init(j)    self.attr = j    end
    def setmember(k, v)    self.attr[k] = v    end
    def member(k)    return self.attr.find(k)    end
end
class FauxChart
    var series, points, axe
    def init()    self.series = []    self.points = []    end
    def add_series(c, axe)    self.series.push(c)    self.points.push([])    return size(self.series) - 1    end
    def set_next_value(s, v)    self.points[s].push(v)    end
    def set_axis_range(a, mini, maxi)    self.axe = [mini, maxi]    end
    def set_style_size(w, h, sel) end
    def set_style_line_width(w, sel) end
end
class ObjetChart : ObjetEcran
    var _lv_obj
    def init(j)    super(self).init(j)    self._lv_obj = FauxChart()    end
    def parse_color(c)    return c    end
end
var OBJETS = []
def creeObjets()
    for n: OBJETS    global.(n) = nil    end
    OBJETS.clear()
    for l: string.split(lis(DOSSIER + "pages.jsonl"), "\n")
        if size(l) == 0    continue    end
        var j = json.load(l)
        if j.find("id") == nil || j["id"] == 0    continue    end
        var nom = "p" + str(j["page"]) + "b" + str(j["id"])
        global.(nom) = j["obj"] == "chart" ? ObjetChart(j) : ObjetEcran(j)
        OBJETS.push(nom)
    end
end
global.creeObjets = creeObjets
global.FICHIERS_ECRAN = ["/json/pages.jsonl"]
import display
import ecranFonctions
import ecranCaveHaspmota
var H = ecranCaveHaspmota
var DESC = json.load(lis("outils_docs/atelier_ecrans/cartes/tasmota32s3-cave-ecran/ecran.json"))

# Etat neuf : persist de l'ecran, objets recrees par demarre() (comme au demarrage de la carte)
def monteHasp()
    monte()
    display.demarre = true
    H.cache = {}
    H.menuEtat = 0
    H.angle = 0
    H.refusJusqua = 0
    H.series = {}
    H.pousses = 0
    ecranFonctions.bloc = "ecranCave"
    ecranFonctions.histo = nil
    ecranFonctions.histoA = nil
    ecranFonctions.points = 0
    tasmota.heure = 1800000000
    var ok = H.demarre()
    if !ok    print("  (demarre a rendu false)")    end
    return ok
end
def attr(id, k)
    var o = global.(id)
    return o == nil ? "absent" : str(o.attr.find(k))
end
def appuie(id, evt)
    for r: tasmota.regles
        if r[0] == "hasp#" + id + "#event"    r[1](evt == nil ? "up" : evt, "HASP#" + string.toupper(id) + "#EVENT")    end
    end
end
# Modele de ecranCaveFonctions.modele() : vals = cle -> valeur ; perimes = liste de cles perimees
def M(vals, perimes, alertes, broker)
    var v = {}
    for k: vals.keys()    v[k] = {"valeur": vals[k], "perime": perimes != nil && perimes.find(k) != nil}    end
    return {"valeurs": v, "alertes": alertes == nil ? [] : alertes, "broker": broker != false}
end
def plein()
    return {"temperature": 14.2, "humidite": 78, "taux": 0.63, "volume": 2520, "power1": "OFF", "power2": "ON", "power3": "OFF", "power4": "ON",
            "power5": "OFF", "pompe": "OFF", "manuel": "OFF", "niveauBas": "ON", "niveauHaut": "OFF"}
end

print("--- a7_liens_conformes_a_ecran_json")
var boutonsAttendus = 0
var ecartLiens = []
for o: DESC["objets"]
    var id = "p" + str(o["page"]) + "b" + str(o["id"])
    var att = []
    var l = o.find("liaison")
    if l != nil && l["attribut"] != "series"    att.push(str([l["attribut"], l["cle"], l.find("table"), l.find("format")]))    end
    var cs = o.find("couleur_selon")
    if cs != nil    for c: cs    att.push(str([c["attribut"], c["cle"], c["table"], nil]))    end    end
    var obtenu = []
    if H.LIENS.contains(id)    for b: H.LIENS[id]    obtenu.push(str(b))    end    end
    if str(att) != str(obtenu)    ecartLiens.push(id)    end
    var t = o.find("toucher")
    if t != nil && t.contains("fonction")
        boutonsAttendus += 1
        var f = t["fonction"]
        var a = t.find("args", [])
        var e = nil
        if string.endswith(f, ".menu")    e = ["menu", a[0]]
        elif string.endswith(f, "demandeRedemarrage")    e = ["demande"]
        elif string.endswith(f, "annuleRedemarrage")    e = ["annule"]
        elif string.endswith(f, ".touche")    e = a == [5] ? ["confirme"] : ["appui", a[0]]
        elif string.endswith(f, ".ajuste")    e = ["ajuste", a[0], a[1]]
        end
        if str(H.BOUTONS.find(id)) != str(e)    ecartLiens.push("bouton " + id)    end
    end
end
verifie("LIENS et BOUTONS = liaison, couleur_selon et toucher de ecran.json (aucun ecart)", "[]", str(ecartLiens))
verifie("autant de boutons que de toucher a fonction", boutonsAttendus, size(H.BOUTONS))
var ecartCoul = []
for t: DESC["couleurs"].keys()
    for k: DESC["couleurs"][t].keys()
        if H.COULEURS.find(t) == nil || H.COULEURS[t].find(k) != DESC["couleurs"][t][k]    ecartCoul.push(t + "." + k)    end
    end
end
verifie("COULEURS = couleurs de ecran.json", "[]", str(ecartCoul))

print("--- a7_objets_references_existent_dans_pages_jsonl")
verifie("demarre() rend true", true, monteHasp())
var absents = []
var references = []
for id: H.LIENS.keys()    references.push(id)    end
for id: H.BOUTONS.keys()    references.push(id)    end
for id: H.NAV.keys()    references.push(id)    end
for id: H.COURBES.keys()    references.push(id)    end
references.push(H.VENTILATEUR)
for i: 30 .. 38    references.push("p0b" + str(i))    end
for id: references    if global.(id) == nil    absents.push(id)    end    end
verifie("chaque objet reference par l'interface existe dans pages.jsonl (page + id)", "[]", str(absents))
H.affiche(M(plein()))
var nonEcrits = []
for id: H.LIENS.keys()
    for b: H.LIENS[id]    if !H.cache.contains(id + "." + b[0])    nonEcrits.push(id + "." + b[0])    end    end
end
verifie("affiche() ecrit chaque attribut lie (cle du modele produite)", "[]", str(nonEcrits))
var reglesHasp = 0
for r: tasmota.regles    if string.find(r[0], "hasp#") == 0    reglesHasp += 1    end    end   # les autres modules (Mqtt#Connected...) ne comptent pas
verifie("demarre(): une regle par bouton", size(H.BOUTONS), reglesHasp)
verifie("demarre(): une serie par courbe", 2, size(H.series))

print("--- a7_demarre_refuse_sans_ecran_ou_sans_pages")
monte()
display.demarre = false
JOURNAL.clear()
verifie("ecran non demarre : false, une erreur", "false/1", str(H.demarre()) + "/" + str(erreurs()))
display.demarre = true
global.FICHIERS_ECRAN = []
JOURNAL.clear()
verifie("pages.jsonl absent : false, une erreur", "false/1", str(H.demarre()) + "/" + str(erreurs()))
global.FICHIERS_ECRAN = ["/json/pages.jsonl"]

print("--- confirmation_avant_redemarrage")
monteHasp()
cave_fraiche("OFF", "OFF")
appuie("p0b1")
verifie("menu ouvert : bouton Redemarrer visible, confirmation cachee", "0/1/1", attr("p0b34", "hidden") + "/" + attr("p0b36", "hidden") + "/" + attr("p0b35", "hidden"))
appuie("p0b34")
verifie("Redemarrer seul : RIEN n'est pousse", 0, size(modbusFonctions.pushs))
verifie("la confirmation apparait (Confirmer, Annuler, question), Redemarrer disparait", "0/0/0/1", attr("p0b36", "hidden") + "/" + attr("p0b37", "hidden") + "/" + attr("p0b35", "hidden") + "/" + attr("p0b34", "hidden"))
appuie("p0b37")
verifie("Annuler : retour au menu, toujours rien pousse", "0/1/0", attr("p0b34", "hidden") + "/" + attr("p0b36", "hidden") + "/" + str(size(modbusFonctions.pushs)))
appuie("p0b34")
appuie("p0b36", "down")
verifie("Confirmer enfonce sans relachement : rien", 0, size(modbusFonctions.pushs))
appuie("p0b36")
verifie("Confirmer pousse la touche 5 (registre 36, mot 3)", "[[36, 'uint16', 3]]", pushs())
verifie("le menu se referme apres Confirmer", "1/1/1", attr("p0b30", "hidden") + "/" + attr("p0b34", "hidden") + "/" + attr("p0b36", "hidden"))

print("--- menu_ouvre_et_ferme")
monteHasp()
verifie("au depart : fenetre cachee", "1/1/1", attr("p0b30", "hidden") + "/" + attr("p0b31", "hidden") + "/" + attr("p0b34", "hidden"))
appuie("p0b1")
verifie("☰ ouvre : voile, fenetre, titre, croix, Redemarrer visibles", "0/0/0/0/0", attr("p0b30", "hidden") + "/" + attr("p0b31", "hidden") + "/" + attr("p0b32", "hidden") + "/" + attr("p0b33", "hidden") + "/" + attr("p0b34", "hidden"))
appuie("p0b33")
verifie("croix referme tout", "1/1/1/1/1", attr("p0b30", "hidden") + "/" + attr("p0b31", "hidden") + "/" + attr("p0b32", "hidden") + "/" + attr("p0b33", "hidden") + "/" + attr("p0b34", "hidden"))
appuie("p0b1")
appuie("p0b30")
verifie("un appui sur le voile referme aussi", "1/1", attr("p0b31", "hidden") + "/" + attr("p0b34", "hidden"))
appuie("p0b1")
appuie("p0b34")
appuie("p0b33")
verifie("fermer pendant la confirmation cache aussi Confirmer, Annuler et la question", "1/1/1", attr("p0b36", "hidden") + "/" + attr("p0b37", "hidden") + "/" + attr("p0b35", "hidden"))

print("--- valeur_perimee_grisee")
monteHasp()
H.affiche(M(plein()))
verifie("frais : temperature en clair, tuile lumieres OFF", "#E8EDF2/#1F2B38", attr("p1b12", "text_color") + "/" + attr("p1b50", "bg_color"))
H.affiche(M(plein(), ["temperature", "power3"]))
verifie("temperature perimee : grise", "#5B6B7C", attr("p1b12", "text_color"))
verifie("touche lumieres perimee : tuile eteinte, texte Périmé", "#18222D/Périmé/#5B6B7C", attr("p1b50", "bg_color") + "/" + attr("p1b52", "text") + "/" + attr("p1b52", "text_color"))
H.affiche(M({"temperature": 14.2}))
verifie("jamais recu : Inconnu et gris", "Inconnu/#18222D", attr("p1b52", "text") + "/" + attr("p1b50", "bg_color"))
H.affiche(M(plein(), nil, nil, false))
verifie("broker absent : horloge barree, pastille rouge, statut", "255/#FF5A5A/broker absent", attr("p0b7", "opa") + "/" + attr("p0b8", "bg_color") + "/" + attr("p0b9", "text"))
H.affiche(M(plein()))
verifie("broker joint : barre retiree, pastille verte", "0/#3FD08A/données à jour", attr("p0b7", "opa") + "/" + attr("p0b8", "bg_color") + "/" + attr("p0b9", "text"))
verifie("horloge de la barre du haut", "12:34", attr("p0b6", "text"))
tasmota.heure = 100
H.affiche(M(plein()))
verifie("horloge pas synchronisee : --:--", "--:--", attr("p0b6", "text"))

print("--- ventilation_tourne_seulement_a_ON")
monteHasp()
var vent = plein()
vent["power2"] = "OFF"
H.affiche(M(vent))
H.affiche(M(vent))
verifie("POWER2 OFF : l'icone ne tourne pas", 0, attr(H.VENTILATEUR, "transform_rotation"))
vent["power2"] = "ON"
H.affiche(M(vent))
H.affiche(M(vent))
verifie("POWER2 ON : deux pas de 45 degres", 900, attr(H.VENTILATEUR, "transform_rotation"))
verifie("couleur bleue a ON", "#3FA7FF", attr(H.VENTILATEUR, "arc_color10"))
vent["power2"] = "OFF"
H.affiche(M(vent))
verifie("OFF : s'arrete ou elle est, grisee", "900/#5B6B7C", attr(H.VENTILATEUR, "transform_rotation") + "/" + attr(H.VENTILATEUR, "arc_color10"))
vent["power2"] = "ON"
for i: 1 .. 10    H.affiche(M(vent))    end
verifie("l'angle reste dans un tour", true, int(attr(H.VENTILATEUR, "transform_rotation")) < 3600)

print("--- lumieresIcone_suit_l_etat")
monteHasp()
var lum = plein()
lum["power3"] = "ON"
H.affiche(M(lum))
verifie("allumees : ampoule allumee, jaune, texte", GLYPHE_ON + "/#FFD54A/Allumées", attr("p1b53", "text") + "/" + attr("p1b53", "text_color") + "/" + attr("p1b52", "text"))
lum["power3"] = "OFF"
H.affiche(M(lum))
verifie("eteintes : ampoule eteinte, grise", GLYPHE_OFF + "/#9FB3C8/Éteintes", attr("p1b53", "text") + "/" + attr("p1b53", "text_color") + "/" + attr("p1b52", "text"))
H.affiche(M(lum, ["power3"]))
verifie("perimee : ampoule eteinte (jamais allumee), grise", GLYPHE_OFF + "/#5B6B7C", attr("p1b53", "text") + "/" + attr("p1b53", "text_color"))
H.affiche(M({"temperature": 14.2}))
verifie("inconnue : ampoule eteinte", GLYPHE_OFF, attr("p1b53", "text"))

print("--- textes_des_appareils_et_du_vide_cave")
monteHasp()
var a = plein()
a["power4"] = "OFF"
a["power5"] = "ON"
H.affiche(M(a))
verifie("lave-linge ON / pompe cuve OFF", "En marche/Arrêt", attr("p1b62", "text") + "/" + attr("p1b72", "text"))
a["power1"] = "OFF"
H.affiche(M(a))
verifie("vide-cave arret auto, bouton Forcer", "Arrêt · auto/Forcer la marche", attr("p1b82", "text") + "/" + attr("p3b34", "text"))
a["power1"] = "ON"
a["pompe"] = "ON"
a["manuel"] = "ON"
H.affiche(M(a))
verifie("vide-cave marche manuelle, bouton Arreter", "Marche · manuel/Arrêter la marche/#3FA7FF", attr("p1b82", "text") + "/" + attr("p3b34", "text") + "/" + attr("p1b80", "bg_color"))
a["manuel"] = "OFF"
H.affiche(M(a))
verifie("vide-cave marche auto", "Marche · auto", attr("p1b82", "text"))
verifie("temperature, humidite, cuve en texte", "14,2 °C/78 %/63 %/2 520 L/63 % · 2 520 L", attr("p1b12", "text") + "/" + attr("p1b22", "text") + "/" + attr("p3b13", "text") + "/" + attr("p3b14", "text") + "/" + string.replace(attr("p1b32", "text"), "  ·  ", " · "))
verifie("niveau moyen (bas atteint, haut libre) : barre 50, flotteurs", "Niveau moyen/50/Atteint/Libre", attr("p1b42", "text") + "/" + attr("p3b23", "val") + "/" + attr("p3b30", "text") + "/" + attr("p3b26", "text"))
a["niveauHaut"] = "ON"
H.affiche(M(a))
verifie("flotteur haut : barre 100", "Niveau haut/100", attr("p1b42", "text") + "/" + attr("p3b23", "val"))
H.affiche(M(a, ["niveauHaut"]))
verifie("flotteur perime : barre 0, Inconnu, pastille grise", "Inconnu/0/#3A4552", attr("p1b42", "text") + "/" + attr("p3b23", "val") + "/" + attr("p3b24", "bg_color"))
H.affiche(M(plein(), nil, ["incoherence des flotteurs"]))
verifie("alerte : bandeau rouge, texte blanc", "#D93636/incoherence des flotteurs/#FFFFFF", attr("p0b20", "bg_color") + "/" + attr("p0b21", "text") + "/" + attr("p0b21", "text_color"))
H.affiche(M(plein()))
verifie("plus d'alerte : bandeau invisible", "#10161E/", attr("p0b20", "bg_color") + "/" + attr("p0b21", "text"))

print("--- touche_refusee_visible")
monteHasp()
H.affiche(M(plein()))
appuie("p1b50")
verifie("rien recu de la cave : touche 1 refusee, rien pousse", 0, size(modbusFonctions.pushs))
H.affiche(M(plein()))
verifie("statut : touche refusee", "touche refusée : état inconnu", attr("p0b9", "text"))
tasmota.ms += 3001
H.affiche(M(plein()))
verifie("apres 3 s le statut revient", "données à jour", attr("p0b9", "text"))
cave_fraiche("OFF", "OFF")
appuie("p1b50")
appuie("p1b60")
appuie("p1b70")
appuie("p1b80")
appuie("p3b34")
var regs = []
for q: modbusFonctions.pushs    regs.push(q[0])    end
verifie("tuiles 1 a 4 et bouton de la page 3 = touches 1, 2, 3, 4, 4 (registres 32 a 35, 35)", "[32, 33, 34, 35, 35]", regs)

print("--- courbes_et_reglages")
monteHasp()
H.affiche(M(plein()))
verifie("premier point tout de suite, temperature en dixiemes", "142/78", str(global.p2b30._lv_obj.points[0][0]) + "/" + str(global.p2b40._lv_obj.points[0][0]))
H.affiche(M(plein()))
verifie("pas de nouveau point avant 30 s", 1, ecranFonctions.points)
tasmota.ms += 30000
H.affiche(M(plein(), ["humidite"]))
verifie("deuxieme point : humidite perimee = trou", "2/" + str(0x7FFFFFFF), str(ecranFonctions.points) + "/" + str(global.p2b40._lv_obj.points[0][1]))
verifie("axes : temperature 40 °C (400 dixiemes), humidite 100", "[0, 400]/[0, 100]/40 °C/100 %", str(global.p2b30._lv_obj.axe) + "/" + str(global.p2b40._lv_obj.axe) + "/" + attr("p2b31", "text") + "/" + attr("p2b41", "text"))
verifie("reglages affiches (defauts du firmware)", "5 min/30 min/80 %", attr("p4b13", "text") + "/" + attr("p4b23", "text") + "/" + attr("p4b33", "text"))
appuie("p4b14")
appuie("p4b14")
appuie("p4b22")
appuie("p4b32")
H.affiche(M(plein()))
verifie("boutons + / - : veille 7, extinction 25, luminosite 70 (persist et ecran)", "7/25/70/7 min/25 min/70 %", str(modules["ecranCave"]["veille"]) + "/" + str(modules["ecranCave"]["extinction"]) + "/" + str(modules["ecranCave"]["luminosite"]) + "/" + attr("p4b13", "text") + "/" + attr("p4b23", "text") + "/" + attr("p4b33", "text"))
for i: 1 .. 30    appuie("p4b32")    end
verifie("luminosite bornee a 10 %", 10, modules["ecranCave"]["luminosite"])
for i: 1 .. 10    appuie("p4b12")    end
H.affiche(M(plein()))
verifie("veille a 0 : jamais", "jamais", attr("p4b13", "text"))

print("BANC_ECRAN_CAVE: " + (echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")") + " (" + str(nbControles) + " controles)")
