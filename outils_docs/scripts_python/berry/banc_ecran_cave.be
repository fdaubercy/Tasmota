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
    var ms, rules, cmds, timers
    def init() self.ms = 100000 self.rules = {} self.cmds = [] self.timers = [] end
    def millis(n) return self.ms end
    def add_rule(a, f, id) self.rules[id] = f end
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

print("BANC_ECRAN_CAVE: " + (echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")") + " (" + str(nbControles) + " controles)")
