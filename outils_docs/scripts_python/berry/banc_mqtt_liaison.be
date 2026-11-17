# Banc Berry de data/fs/mqttLiaisonFonctions.be : garde-fous de la voie MQTT (plan tasks/plans/voie-mqtt.md, A3).
# Charge le VRAI module sous des bouchons (bouchons_berry/liaison_mqtt/ : logFonctions, persist). Le temps est
# simule (millisecondes passees au module) : aucun reseau, aucune carte. Rejoue les cas de boucle : ordre puis accuse,
# ordre inutile, evenement de bouton, rafale d'un element, rafale sur tous, ordres sans accuse, et un MAITRE FAUTIF
# qui recommande l'inverse a chaque retour (la preuve que la boucle est bornee).
#
# Lancer via son enveloppe Python (racine, berry.exe, code de sortie, mutants) :
#     python outils_docs/scripts_python/berry/banc_mqtt_liaison.py
# Ou DEPUIS LA RACINE : lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_mqtt_liaison.be [dossier_sources]
# Derniere ligne : BANC_MQTT_LIAISON: OK|ECHEC. Ne teste pas le vrai MQTT (module pur, A4 branche mqtt).
import global
import sys
import string
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/liaison_mqtt")   # le dernier pousse l'emporte

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var JOURNAL = []

class Driver end                                   # classe du firmware, absente de berry.exe
class TasmotaStub
    var cmds, pilotes, reseau, ms, reponses
    def init() self.cmds = {} self.pilotes = [] self.reseau = true self.ms = 100000 self.reponses = [] end
    def add_cmd(n, f) self.cmds[n] = f end
    def add_driver(d) self.pilotes.push(d) end
    def is_network_up() return self.reseau end
    def millis() return self.ms end
    def resp_cmnd(s) self.reponses.push(s) end
end
var tasmota = TasmotaStub()

var echecs = 0
def verifie(ok, libelle)
    print((ok ? "OK   " : "KO   ") + libelle)
    if !ok    echecs += 1    end
end

import mqttLiaisonFonctions
var G = mqttLiaisonFonctions.GardeMqtt          # classe : valeurs par defaut (sans persist)

# --- 0. lecture du persist (drivers.liaisonMqtt.garde) : cles valides reprises, invalides ignorees
var gp = global.mqttLiaisonGarde
verifie(gp != nil && gp.max_element == 4 && gp.delai_accuse == 1500, "persist : maxParElement et delaiAccuseMs repris")
verifie(gp.essais_max == G.ESSAIS_MAX && gp.max_total == G.MAX_TOTAL, "persist : valeur invalide ou absente = defaut")

# --- 1. ordre, accuse, ecart : un ordre produit UN envoi, son retour n'est pas un evenement
var g = G()
verifie(g.demande("p/r1", "ON", 1000) == "envoyer", "ordre : envoye")
verifie(g.demande("p/r1", "ON", 1100) == "attente", "meme ordre pendant l'attente : pas de doublon")
verifie(g.recoit("p/r1", "ON", 1200) == "accuse", "retour attendu : accuse (pas un evenement)")
verifie(g.recoit("p/r1", "ON", 1300) == "inchange", "meme retour une seconde fois (tele periodique) : inchange")
verifie(g.demande("p/r1", "ON", 1400) == "identique", "ordre deja applique : rien n'est envoye (G3)")
verifie(size(g.attente) == 0, "plus d'ordre en attente apres accuse")

# --- 2. evenements venant de l'esclave
var h = G()
verifie(h.recoit("p/b1", "OFF", 1000) == "initial", "premier etat connu : initial (pas d'action au demarrage)")
verifie(h.recoit("p/b1", "ON", 2000) == "evenement", "bouton appuye sans ordre : evenement")
verifie(h.recoit("p/b1", "ON", 3000) == "inchange", "meme etat repete : inchange")
# ordre en cours, puis l'ancien etat repete par une tele : l'ordre reste en attente
var c = G()
c.recoit("p/r2", "OFF", 1000)
c.demande("p/r2", "ON", 2000)
verifie(c.recoit("p/r2", "OFF", 2500) == "inchange" && c.attente.contains("p/r2"), "ancien etat repete pendant un ordre : l'ordre reste attendu")
verifie(c.recoit("p/r2", "AUTRE", 2600) == "evenement" && !c.attente.contains("p/r2"), "etat inattendu pendant un ordre : evenement, ordre abandonne")

# --- 3. rafale sur UN element : quarantaine, les autres continuent
var q = G()
var n_envoyes = 0
var bloque_a = nil
for i: 0 .. 14
    var r = q.demande("p/r1", i % 2 == 0 ? "ON" : "OFF", 1000 + i * 100)
    if r == "envoyer"    n_envoyes += 1    q.recoit("p/r1", i % 2 == 0 ? "ON" : "OFF", 1000 + i * 100 + 50)
    elif bloque_a == nil    bloque_a = r    end
end
verifie(n_envoyes == G.MAX_ELEMENT && bloque_a == "quarantaine", "rafale d'un element : " + str(n_envoyes) + " ordres puis quarantaine")
verifie(q.demande("p/r2", "ON", 3000) == "envoyer", "un AUTRE element reste libre pendant la quarantaine")
verifie(q.demande("p/r1", "ON", 20000) == "quarantaine", "element en quarantaine : refuse")
verifie(q.etats["p/r1"] == "OFF" && q.demande("p/r1", "ON", 1000 + 1400 + G.QUARANTAINE_MS + 10) == "envoyer", "apres la quarantaine : l'element repart")
q.recoit("p/r1", "ON", 1000 + 1400 + G.QUARANTAINE_MS + 60)
verifie(q.demande("p/r1", "OFF", 1000 + 1400 + G.QUARANTAINE_MS + 200) == "envoyer", "apres la quarantaine : l'ordre SUIVANT passe aussi")

# --- 4. ordres espaces : jamais de quarantaine
var e = G()
var tous = true
for i: 0 .. 29
    var t = 1000 + i * 2000                       # 5 ordres par fenetre de 10 s au plus
    var v = i % 2 == 0 ? "ON" : "OFF"
    if e.demande("p/r1", v, t) != "envoyer"    tous = false    end
    e.recoit("p/r1", v, t + 100)
end
verifie(tous, "30 ordres espaces de 2 s : tous envoyes (la fenetre glisse)")

# --- 5. coupe-circuit global : beaucoup d'elements en peu de temps
var k = G()
var envoyes = 0
var coupe = false
for i: 0 .. 99
    var r = k.demande("p/e" + str(i), "ON", 1000 + i * 10)
    if r == "envoyer"    envoyes += 1    elif r == "coupe"    coupe = true    end
end
verifie(coupe && envoyes == G.MAX_TOTAL, "100 elements en 1 s : " + str(envoyes) + " ordres puis coupe-circuit")
verifie(k.demande("p/neuf", "ON", 5000) == "coupe", "coupe-circuit : tout est refuse")
verifie(k.demande("p/neuf", "ON", 1000 + 100 * 10 + G.COUPURE_MS) == "envoyer", "apres la coupure : la voie repart seule")
k.demande("p/z", "ON", 1)
k.rearme()
verifie(!k.coupe_actif && size(k.quarantaine) == 0, "rearme : quarantaines et coupe-circuit leves")

# --- 5 bis. ordre refuse pendant la coupure : aucune attente creee, rien a renvoyer
var kk = G()
for i: 0 .. 69    kk.demande("p/e" + str(i), "ON", 1000 + i)    end
verifie(kk.coupe_actif && kk.demande("p/nouveau", "ON", 2000) == "coupe" && !kk.attente.contains("p/nouveau"), "ordre refuse (coupe-circuit) : aucune attente creee")
# t = 0 est un instant valable (plus de sentinelle)
var z = G()
verifie(z.demande("p/r1", "ON", 0) == "envoyer" && z.recoit("p/r1", "ON", 10) == "accuse", "t = 0 : ordre envoye puis accuse")

# --- 6. ordre sans accuse : renvois bornes, puis echec
var r2 = G()
r2.demande("p/r1", "ON", 1000)
var s = r2.a_renvoyer(1000 + G.DELAI_ACCUSE_MS - 1)
verifie(size(s["renvoyer"]) == 0 && size(s["echec"]) == 0, "avant le delai d'accuse : rien")
s = r2.a_renvoyer(1000 + G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 1 && s["renvoyer"][0][0] == "p/r1" && s["renvoyer"][0][1] == "ON", "apres le delai : renvoi du meme ordre")
s = r2.a_renvoyer(1000 + 2 * G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 1, "deuxieme renvoi (3e emission)")
s = r2.a_renvoyer(1000 + 3 * G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 0 && size(s["echec"]) == 1 && s["echec"][0] == "p/r1" && size(r2.attente) == 0, "ESSAIS_MAX atteint : echec, plus de renvoi")
r2.demande("p/r2", "ON", 90000)
r2.recoit("p/r2", "ON", 90500)
verifie(size(r2.a_renvoyer(99999)["renvoyer"]) == 0, "ordre accuse : jamais renvoye")

# --- 6 bis. renvoi refuse par la quarantaine : ordre abandonne ET loggue
var rq = mqttLiaisonFonctions.GardeMqtt({"maxParElement": 2})
rq.demande("p/r1", "ON", 1000)
rq.demande("p/r1", "OFF", 1100)                    # remplace l'ordre en attente : essais repart a 1
verifie(rq.attente["p/r1"]["valeur"] == "OFF" && rq.attente["p/r1"]["essais"] == 1, "nouvel ordre de valeur differente : remplace l'ancien, essais a 1")
var nj = size(JOURNAL)
s = rq.a_renvoyer(1100 + G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 0 && size(s["echec"]) == 1 && size(rq.attente) == 0, "renvoi bloque par la quarantaine : echec, plus d'attente")
verifie(size(JOURNAL) > nj + 1 && string.find(JOURNAL[-1][0], "voie bloquée") >= 0 && JOURNAL[-1][1] == LOG_LEVEL_ERREUR, "renvoi bloque : echec loggue en erreur")

# --- 6 ter. arguments invalides et valeurs de types differents
var v = G()
verifie(v.demande(nil, "ON", 1000) == "invalide" && v.demande("", "ON", 1000) == "invalide" && v.demande(5, "ON", 1000) == "invalide", "cle nil, vide ou non texte : invalide, sans exception")
verifie(v.demande("p/r1", nil, 1000) == "invalide" && v.recoit(nil, "ON", 1000) == "invalide" && v.recoit("p/r1", nil, 1000) == "invalide", "valeur nil : invalide")
verifie(size(v.attente) == 0 && size(v.etats) == 0 && size(v.totaux) == 0, "appels invalides : aucun effet sur l'etat")
v.demande("p/r1", 1, 1000)
verifie(v.recoit("p/r1", "1", 1100) == "accuse", "ordre 1 (entier), retour \"1\" (texte) : accuse")
# premier retour, sans etat connu, different de l'ordre : probablement l'ancien etat, l'ordre reste attendu
var w = G()
w.demande("p/r2", "OFF", 1000)
verifie(w.recoit("p/r2", "ON", 1100) == "initial" && w.attente.contains("p/r2"), "1er retour different de l'ordre, etat inconnu : initial, ordre toujours attendu")
verifie(w.recoit("p/r2", "OFF", 1200) == "accuse", "puis le vrai retour : accuse")

# --- 7. LA PREUVE ANTI-BOUCLE : un maitre fautif recommande l'inverse a chaque retour de l'esclave
var f = G()
var ordres = 0
var refus = 0
var valeur = "ON"
for i: 0 .. 199                                    # 200 retours en 20 s
    var t = 1000 + i * 100
    var r = f.demande("p/r1", valeur, t)
    if r == "envoyer"
        ordres += 1
        f.recoit("p/r1", valeur, t + 50)           # l'esclave obeit et publie son etat
        valeur = valeur == "ON" ? "OFF" : "ON"     # le maitre fautif reagit a ce retour par l'ordre inverse
    else
        refus += 1
        valeur = valeur == "ON" ? "OFF" : "ON"
    end
end
verifie(ordres == G.MAX_ELEMENT, "maitre fautif : " + str(ordres) + " ordres sur 200 tentatives (borne : " + str(G.MAX_ELEMENT) + ")")

# --- 6 bis. G3 : un etat connu trop ancien n'est plus cru (un retour perdu laisserait un ordre refuse a tort)
var fa = G()
fa.recoit("p/r1", "ON", 1000)
verifie(fa.demande("p/r1", "ON", 1000 + G.AGE_ETAT_MS) == "identique", "G3 : etat connu recent, ordre identique refuse")
var fb = G()
fb.recoit("p/r1", "ON", 1000)
verifie(fb.demande("p/r1", "ON", 1001 + G.AGE_ETAT_MS) == "envoyer", "G3 : etat connu trop ancien, l'ordre identique repart")
verifie(fb.recoit("p/r1", "ON", 1100 + G.AGE_ETAT_MS) == "accuse" && fb.demande("p/r1", "ON", 1200 + G.AGE_ETAT_MS) == "identique", "G3 : le retour rafraichit l'etat, l'ordre redevient identique")
var fc = G({"ageEtatMs": 2000})
fc.recoit("p/r1", "ON", 1000)
verifie(fc.demande("p/r1", "ON", 3500) == "envoyer", "G3 : age lu dans le persist (ageEtatMs)")

# --- 7 bis. LE DRIVER (controleMqttLiaison) : abonnements, ordres, retours, renvois, commande
import mqtt
import json
import controleMqttLiaison
var D = global.mqttLiaisonDriver
var garde = global.mqttLiaisonGarde
verifie(D != nil && size(tasmota.pilotes) == 1 && tasmota.cmds.contains("ReglageMqttLiaison"), "driver : instance globale, add_driver et commande ReglageMqttLiaison")
verifie(size(D.esclaves) == 2 && D.esclaves["projecteur"] == "jardin/projecteur_led" && D.esclaves["pompe"] == "pompe", "driver : seuls les esclaves actifs, valides et sans doublon sont declares")
verifie(size(mqtt.abonnes) == 6 && mqtt.abonnes.contains("stat/jardin/projecteur_led/+") && mqtt.abonnes.contains("tele/pompe/LWT"), "driver : 3 abonnements par esclave (stat, LWT, SENSOR), jamais de joker global")

# ordres : reseau coupe -> rien n'est emis ni compte
tasmota.reseau = false
verifie(D.ordonne("projecteur", "Power1", "ON") == "hors_ligne" && size(mqtt.publies) == 0 && size(garde.attente) == 0, "ordre sans reseau : hors_ligne, rien publie, rien compte")
tasmota.reseau = true
mqtt.connecte = false
verifie(D.ordonne("projecteur", "Power1", "ON") == "hors_ligne" && size(mqtt.publies) == 0, "ordre sans broker : hors_ligne")
mqtt.connecte = true
verifie(D.ordonne("inconnu", "Power1", "ON") == "inconnu" && D.ordonne("inactif", "Power1", "ON") == "inconnu", "esclave non declare ou inactif : inconnu")
verifie(D.ordonne("projecteur", "Power1", "ON") == "envoyer" && size(mqtt.publies) == 1 && mqtt.publies[0][0] == "cmnd/jardin/projecteur_led/POWER1" && mqtt.publies[0][1] == "ON", "ordre : publie cmnd/<topic>/<commande>")
verifie(D.ordonne("projecteur", "Power1", "ON") == "attente" && size(mqtt.publies) == 1, "meme ordre pendant l'attente : rien de plus publie")

# retours : l'accuse n'est pas un evenement, un changement de l'esclave en est un
var evenements = size(JOURNAL)
mqtt.abonnes["stat/jardin/projecteur_led/+"]("stat/jardin/projecteur_led/RESULT", 0, '{"POWER1":"ON"}', bytes())
verifie(size(garde.attente) == 0 && garde.etats["projecteur/POWER1"] == "ON", "retour RESULT attendu : ordre accuse")
verifie(size(JOURNAL) == evenements, "accuse : aucun journal d'evenement")
mqtt.abonnes["stat/jardin/projecteur_led/+"]("stat/jardin/projecteur_led/POWER1", 0, "OFF", bytes())
verifie(garde.etats["projecteur/POWER1"] == "OFF" && JOURNAL[-1][1] == LOG_LEVEL_DEBUG && string.find(JOURNAL[-1][0], "évènement") > 0, "bouton local : evenement journalise en debug")
var avant_json = size(JOURNAL)
verifie(mqtt.abonnes["stat/jardin/projecteur_led/+"]("stat/jardin/projecteur_led/RESULT", 0, '{"Button1":{"Action":"SINGLE"},"POWER2":null}', bytes()) == false && !garde.etats.contains("projecteur/BUTTON1") && !garde.etats.contains("projecteur/POWER2") && size(JOURNAL) == avant_json, "objet Button et valeur nulle : ignores, sans etat ni erreur journalisee")
verifie(mqtt.abonnes["stat/jardin/projecteur_led/+"]("stat/jardin/projecteur_led/RESULT", 0, "pas du json", bytes()) == false, "RESULT illisible : ignore sans exception")
verifie(D.recu("stat/autre/chose/RESULT", '{"POWER1":"ON"}') == false && !garde.etats.contains("autre/POWER1"), "topic d'un esclave non declare : ignore")
mqtt.abonnes["tele/pompe/LWT"]("tele/pompe/LWT", 0, "Offline", bytes())
verifie(D.en_ligne["pompe"] == false, "LWT Offline : esclave hors ligne")
mqtt.abonnes["tele/pompe/LWT"]("tele/pompe/LWT", 0, "Online", bytes())
verifie(D.en_ligne["pompe"] == true, "LWT Online : esclave en ligne")
mqtt.abonnes["stat/pompe/+"]("stat/pompe/RESULT", 0, '{"POWER":"ON"}', bytes())
verifie(garde.etats.contains("pompe/POWER1"), "topic a un seul segment, esclave a un seul relais (POWER) : retour range sous POWER1")

# renvois : ordre sans accuse
var pub = size(mqtt.publies)
D.ordonne("projecteur", "Power2", "ON")
tasmota.ms = tasmota.ms + 1499
D.every_second()
verifie(size(mqtt.publies) == pub + 1, "avant le delai d'accuse : pas de renvoi")
tasmota.ms = tasmota.ms + 1
D.every_second()
verifie(size(mqtt.publies) == pub + 2 && mqtt.publies[-1][0] == "cmnd/jardin/projecteur_led/POWER2" && mqtt.publies[-1][1] == "ON", "apres le delai : meme ordre republie (commande en majuscules, Tasmota ignore la casse)")
tasmota.reseau = false
tasmota.ms = tasmota.ms + 5000
D.every_second()
verifie(size(mqtt.publies) == pub + 2, "renvoi sans reseau : rien publie")
tasmota.reseau = true

# commande ReglageMqttLiaison
var cmd = tasmota.cmds["ReglageMqttLiaison"]
def reponse(payload)
    tasmota.reponses = []
    cmd("ReglageMqttLiaison", 0, payload, nil)
    return json.load(tasmota.reponses[0])["ReglageMqttLiaison"]
end
verifie(reponse("etat").contains("quarantaines") && reponse("etat").contains("en_ligne") && reponse("")["coupe"] == false, "commande etat (avec en_ligne) et sans argument")
var r_ordre = reponse("ordre pompe Power1 OFF")
verifie(r_ordre["ordre"] == "envoyer" && reponse("ordre pompe Power1 OFF")["ordre"] == "attente", "commande ordre : passe par les garde-fous (envoyer puis attente)")
verifie(reponse("ordre pompe")["erreur"] != nil && reponse("zzz")["erreur"] != nil, "commande : syntaxe et sous-commande inconnue refusees")
garde.coupe_actif = true
garde.quarantaine["x"] = 9999999
verifie(reponse("rearme")["rearme"] == true && !garde.coupe_actif && size(garde.quarantaine) == 0, "commande rearme : leve coupe-circuit et quarantaines")

# liste blanche et normalisation : seules les commandes a etat sont permises, avec des valeurs connues
garde.attente = {}
mqtt.publies = []
verifie(D.ordonne("pompe", "Restart", "1") == "invalide" && D.ordonne("pompe", "Backlog", "Power1 ON") == "invalide" && D.ordonne("pompe", "Br", "x") == "invalide" && size(mqtt.publies) == 0, "commandes hors liste blanche (Restart, Backlog, Br) : invalide, rien publie")
verifie(D.ordonne("pompe", "Power1", "TOGGLE") == "invalide" && D.ordonne("pompe", "Power0", "ON") == "invalide" && D.ordonne("pompe", "Dimmer", "abc") == "invalide" && D.ordonne("pompe", "Dimmer1", "50") == "invalide" && D.ordonne("pompe", "a/b", "ON") == "invalide" && D.ordonne("pompe", nil, "ON") == "invalide" && D.ordonne("pompe", "Power1", nil) == "invalide", "TOGGLE, Power0, Dimmer mal forme, commande avec slash, nil : invalide")
verifie(size(mqtt.publies) == 0 && size(garde.attente) == 0, "ordres invalides : ni publie ni compte")
verifie(D.ordonne("projecteur", "Power5", "true") == "envoyer" && mqtt.publies[-1][0] == "cmnd/jardin/projecteur_led/POWER5" && mqtt.publies[-1][1] == "ON", "valeur true normalisee en ON")
verifie(D.ordonne("projecteur", "Dimmer", 50) == "envoyer" && mqtt.publies[-1][0] == "cmnd/jardin/projecteur_led/DIMMER" && mqtt.publies[-1][1] == "50", "Dimmer 50 : entier normalise en texte")
verifie(D.ordonne("pompe", "Power", "OFF") == "envoyer" && mqtt.publies[-1][0] == "cmnd/pompe/POWER1", "Power sans indice : range sous POWER1")
mqtt.abonnes["stat/pompe/+"]("stat/pompe/RESULT", 0, '{"POWER":"OFF"}', bytes())
verifie(!garde.attente.contains("pompe/POWER1") && garde.etats["pompe/POWER1"] == "OFF", "...et accuse par le retour POWER d'un esclave a un seul relais")
mqtt.abonnes["tele/pompe/LWT"]("tele/pompe/LWT", 0, "Offline", bytes())
mqtt.publies = []
verifie(D.ordonne("pompe", "Power", "ON") == "hors_ligne" && size(mqtt.publies) == 0, "esclave Offline (LWT) : ordre refuse, rien publie")
mqtt.abonnes["tele/pompe/LWT"]("tele/pompe/LWT", 0, "Online", bytes())
verifie(D.ordonne("pompe", "Power", "ON") == "envoyer", "esclave de retour Online : ordre accepte")

# declarations d'esclaves invalides (l'init a deja ecarte a/b, joker et sanstopic)
verifie(!D.declaration_valide("a/b", "t") && !D.declaration_valide("", "t") && !D.declaration_valide("n", "x/+") && !D.declaration_valide("n", "#") && !D.declaration_valide("n", "") && !D.declaration_valide("copie", "pompe") && D.declaration_valide("neuf", "autre/topic"), "declarations : nom avec slash, topic avec joker, vide ou en double refuses")
verifie(size(D.esclaves) == 2, "persist : a/b, joker et sanstopic ignores a l'init")

# plafond de renvois par passage : un publish lent bloque loop()
garde.attente = {}
garde.rearme()
for i: 3 .. 10    D.ordonne("projecteur", "Power" + str(i), "ON")    end          # 8 ordres en attente
var p0 = size(mqtt.publies)
tasmota.ms = tasmota.ms + 1500
D.every_second()
verifie(size(mqtt.publies) == p0 + 5, "plafond : 5 renvois au plus par passage")
D.every_second()
verifie(size(mqtt.publies) == p0 + 8, "les ordres restants repartent au passage suivant")

# --- 7 ter. SENSOR : elements virtuels MQTT_<nom> (A5)
import globalFonctions
globalFonctions.appels = []                                    # un test plus haut a deja envoye un Button1 : on repart de zero
var sf = mqtt.abonnes["tele/jardin/projecteur_led/SENSOR"]
verifie(sf != nil, "SENSOR : abonnement par esclave declare")
sf("tele/jardin/projecteur_led/SENSOR", 0, '{"Time":"x","DS18B20":{"Id":"1","Temperature":21.5}}', nil)
verifie(size(globalFonctions.appels) == 1 && globalFonctions.appels[0][0] == 21.5 && globalFonctions.appels[0][1] == "DS18B20#Temperature" && globalFonctions.appels[0][2] == "maison" && globalFonctions.appels[0][3] == "t1", "SENSOR : la valeur du chemin arrive a changementEtatCapteur avec son declencheur")
mqtt.abonnes["tele/pompe/SENSOR"]("tele/pompe/SENSOR", 0, '{"ANALOG":{"A1":512}}', nil)
verifie(size(globalFonctions.appels) == 2 && globalFonctions.appels[1][0] == 512 && globalFonctions.appels[1][1] == "ANALOG#A1" && globalFonctions.appels[1][3] == "a1", "SENSOR : un 2e esclave alimente son analogique")
sf("tele/jardin/projecteur_led/SENSOR", 0, '{"Time":"x"}', nil)
verifie(size(globalFonctions.appels) == 2, "SENSOR : chemin absent du JSON, element ignore")
var erreurs0 = 0
for j: JOURNAL    if j[1] == LOG_LEVEL_ERREUR    erreurs0 += 1    end    end
sf("tele/jardin/projecteur_led/SENSOR", 0, '{"DS18B20":{"Temp', nil)
sf("tele/jardin/projecteur_led/SENSOR", 0, '[1,2]', nil)
var erreurs1 = 0
for j: JOURNAL    if j[1] == LOG_LEVEL_ERREUR && string.find(j[0], "mal formé") >= 0    erreurs1 += 1    end    end
verifie(size(globalFonctions.appels) == 2 && erreurs1 == 2, "SENSOR : JSON mal forme ou non objet, rejete et loggue en erreur (" + str(erreurs1) + ")")
mqtt.abonnes["tele/pompe/SENSOR"]("tele/pompe/SENSOR", 0, '{"sensors":{"niveau":{"volume":7}}}', nil)
verifie(size(globalFonctions.appels) == 3 && globalFonctions.appels[2][0] == 7 && globalFonctions.appels[2][1] == "ANALOG#A2" && globalFonctions.appels[2][3] == "a2", "SENSOR : mqtt.declencheur impose le declencheur quand le chemin ne le porte pas")
mqtt.abonnes["tele/pompe/SENSOR"]("tele/pompe/SENSOR", 0, '{"COUNTER":{"C1":3}}', nil)
D.mesures("inactif", '{"COUNTER":{"C1":3}}')                      # appel direct : aucun abonnement n'existe pour un esclave inactif
verifie(size(globalFonctions.appels) == 3, "SENSOR : element lie a un esclave inactif ou sans chemin, jamais alimente")

# --- 7 quater. boutons et interrupteurs de l'esclave (A6) : stat/<topic>/RESULT {"Button1":{"Action":...}}
var rf = mqtt.abonnes["stat/jardin/projecteur_led/+"]
var n0 = size(globalFonctions.appels)
rf("stat/jardin/projecteur_led/RESULT", 0, '{"Button1":{"Action":"SINGLE"}}', nil)
var ap = globalFonctions.appels
verifie(size(ap) == n0 + 1 && ap[n0][0] == "SINGLE" && ap[n0][1] == "Button1" && ap[n0][2] == "maison" && ap[n0][3] == "b1", "bouton : l'action de l'esclave arrive a changementEtatCapteur pour l'element virtuel")
mqtt.abonnes["stat/pompe/+"]("stat/pompe/RESULT", 0, '{"Switch1":{"Action":"ON"}}', nil)
verifie(size(ap) == n0 + 2 && ap[n0 + 1][0] == "ON" && ap[n0 + 1][1] == "Switch1" && ap[n0 + 1][3] == "s1", "interrupteur : l'action arrive a l'element virtuel de l'esclave concerne")
rf("stat/jardin/projecteur_led/RESULT", 0, '{"Button2":{"Action":"SINGLE"}}', nil)
rf("stat/jardin/projecteur_led/RESULT", 0, '{"Button1":{"Action":3}}', nil)
rf("stat/jardin/projecteur_led/RESULT", 0, '{"Button1":{"Etat":"SINGLE"}}', nil)
verifie(size(ap) == n0 + 2, "bouton : cle inconnue, action non texte ou absente, ignores")
rf("stat/jardin/projecteur_led/RESULT", 0, '{"POWER1":"ON"}', nil)
verifie(size(ap) == n0 + 2, "un retour POWER n'est pas un evenement de bouton")

# garde d'activation : persist a OFF -> aucun driver
import persist
persist._p["drivers"]["liaisonMqtt"]["activation"] = "OFF"
global.mqttLiaisonDriver = nil
var avant = size(tasmota.pilotes)
controleMqttLiaison.init(controleMqttLiaison)
verifie(global.mqttLiaisonDriver == nil && size(tasmota.pilotes) == avant, "activation OFF : driver non cree ni ajoute")

# --- 8. journal : erreurs aux seuils franchis
var erreurs = 0
for j: JOURNAL    if j[1] == LOG_LEVEL_ERREUR && j[2] == "liaisonMqtt" && string.find(j[0], "LIAISON_MQTT_ERREUR: ") == 0    erreurs += 1    end    end
verifie(erreurs >= 3, "journal : quarantaine, coupe-circuit et echec loggues en erreur, cible liaisonMqtt (" + str(erreurs) + ")")

print(echecs == 0 ? "BANC_MQTT_LIAISON: OK" : "BANC_MQTT_LIAISON: ECHEC (" + str(echecs) + ")")
