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
# NE TESTE PAS : le vrai broker, l'ecran, l'envoi des touches (A5).
import global
import sys
import string
import json

sys.path().push("data/fs")
sys.path().push("data/cave/tasmota32s3-ecran")
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
    var ms, rules, cmds
    def init() self.ms = 100000 self.rules = {} self.cmds = [] end
    def millis(n) return self.ms end
    def add_rule(a, f, id) self.rules[id] = f end
    def remove_rule(a, id) self.rules.remove(id) end
    def add_driver(d) end
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
    mqtt.publies.clear()
    mqtt.abonnes = {}
    mqtt.connecte = (relie != false)
    JOURNAL.clear()
    FONCTIONS.valeurs = {}                             # module importe (comme sur la carte) : etat remis a neuf a la main
    FONCTIONS.derniere = {}
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

print("BANC_ECRAN_CAVE: " + (echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")") + " (" + str(nbControles) + " controles)")
