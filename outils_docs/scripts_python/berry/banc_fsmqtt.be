# Banc Berry de data/fs/fsMqtt.be : reception de fichiers du FS par MQTT (A16 de la page Build 7700).
# Charge le VRAI module sous des bouchons (bouchons_berry/fsmqtt/ : FS en memoire, mqtt, crypto, persist,
# logFonctions ; open() et tasmota bouchonnes ici) et rejoue les ordres du PC : envoi par morceaux, morceaux
# perdus ou en double, controles de fin, chemins refuses, lecture, rechargement, BrRestart/Restart, effacement.
#
# Lancer via son enveloppe Python (racine, berry.exe, code de sortie, temoin mute) :
#     python outils_docs/scripts_python/berry/banc_fsmqtt.py
# Ou DEPUIS LA RACINE : lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_fsmqtt.be [dossier_sources]
# Derniere ligne : BANC_FSMQTT: OK|ECHEC. Ne teste ni le vrai MQTT, ni LittleFS, ni le vrai MD5 (bouchon).
import global
import sys
import string
import json
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/fsmqtt")   # le dernier pousse l'emporte

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var JOURNAL = []
var RENOMMAGE_REFUSE = false
var ECRITURE_KO = false
var FS = {"fichiers": {}, "dossiers": {}}

# open() du firmware sur le FS en memoire (le module est compile apres cette globale : elle remplace le builtin)
class FichierMemoire
    var c, pos
    def init(c, mode)
        self.c = c  self.pos = 0
        if mode == "w"    FS["fichiers"][c] = bytes()    end
        if mode == "a" && !FS["fichiers"].contains(c)    FS["fichiers"][c] = bytes()    end
        if mode == "r" && !FS["fichiers"].contains(c)    raise "io_error", "absent : " + c    end
    end
    def write(d)
        if ECRITURE_KO    raise "io_error", "write failed"    end
        FS["fichiers"][self.c] = FS["fichiers"][self.c] + d
    end
    def readbytes(n)
        var t = FS["fichiers"][self.c]
        var fin = self.pos + n > size(t) ? size(t) : self.pos + n
        var r = fin > self.pos ? t[self.pos .. fin - 1] : bytes()
        self.pos = fin
        return r
    end
    def close() end
end
var open = def (c, mode) return FichierMemoire(c, mode) end

class TasmotaStub
    var cmds, regles, timers
    def init() self.cmds = [] self.regles = {} self.timers = {} end
    def cmd(c) self.cmds.push(c) return {} end
    def add_rule(p, f, id) self.regles[p] = f end
    def set_timer(d, f, id) self.timers[id] = f end
    def declenche(id)
        if !self.timers.contains(id)    return false    end
        var f = self.timers[id]  self.timers.remove(id)  f()  return true
    end
end
var tasmota = TasmotaStub()

var echecs = 0
def verifie(ok, libelle)
    print((ok ? "OK   " : "KO   ") + libelle)
    if !ok    echecs += 1    end
end

import mqtt
import crypto
import persist
import fsMqtt
var BASE = "fsmqtt/garage/cuve/"
var id = 0
def ordre(o) id += 1  o["id"] = id  var s = json.dump(o)  mqtt.abonnes[BASE + "ordre"](BASE + "ordre", 0, s, bytes().fromstring(s)) end
def morceau(position, donnees) var m = bytes()  m.add(position, -4)  m = m + donnees  mqtt.abonnes[BASE + "morceau"](BASE + "morceau", 0, "", m) end
def etats()
    var r = []
    for p: mqtt.publies    if p[0] == BASE + "etat"    r.push(json.load(p[1]))    end    end
    return r
end
def dernier() var e = etats()  return size(e) ? e[-1] : {} end
def md5(d) var h = crypto.MD5()  h.update(d)  return string.tolower(h.finish().tohex()) end
def donnees(n) var d = bytes()  for i: 0 .. n - 1    d.add((i * 7 + 3) % 256, 1)    end  return d end
def envoie(chemin, d, taille_morceau)
    ordre({"op": "debut", "chemin": chemin, "taille": size(d), "md5": md5(d)})
    var p = 0
    while p < size(d)
        var fin = p + taille_morceau > size(d) ? size(d) : p + taille_morceau
        morceau(p, d[p .. fin - 1])
        p = fin
    end
    ordre({"op": "fin"})
end

# --- chargement
verifie(mqtt.abonnes.contains(BASE + "ordre") && mqtt.abonnes.contains(BASE + "morceau"), "chargement : abonne a ordre et morceau sous le topic du persist")
verifie(etats()[0]["op"] == "pret" && etats()[0]["version"] == 1, "chargement : « pret » publie (MQTT connecte)")
mqtt.publies = []
tasmota.regles["Mqtt#Connected"]()
verifie(dernier()["op"] == "pret", "reconnexion MQTT : « pret » republie")

# --- envoi en 3 morceaux, dans un dossier a creer
var d = donnees(4000)
mqtt.publies = []
envoie("/json/sous/a.json", d, 1896)
verifie(FS["fichiers"].find("/json/sous/a.json") == d, "envoi : fichier ecrit a l'identique (3 morceaux)")
verifie(FS["dossiers"].contains("/json") && FS["dossiers"].contains("/json/sous"), "envoi : dossiers du chemin crees")
verifie(!FS["fichiers"].contains("/fsmqtt.tmp"), "envoi : fichier temporaire renomme, plus de /fsmqtt.tmp")
var acc = []
for e: etats()    if e["op"] == "morceau"    acc.push(e["octets"])    end    end
verifie(acc == [1896, 3792, 4000], "envoi : accuse cumule par morceau " + str(acc))
verifie(dernier()["op"] == "fin" && dernier()["ok"] && dernier()["octets"] == 4000, "envoi : fin acceptee, taille rendue")

# --- morceau perdu puis renvoye, morceau en double
mqtt.publies = []
d = donnees(3000)
ordre({"op": "debut", "chemin": "/b.be", "taille": 3000, "md5": md5(d)})
morceau(0, d[0 .. 999])
morceau(2000, d[2000 .. 2999])                      # le morceau 1000..1999 est perdu
verifie(dernier()["octets"] == 1000, "perte : morceau hors position ignore, accuse reste a 1000")
morceau(0, d[0 .. 999])                             # double
verifie(dernier()["octets"] == 1000, "double : morceau deja recu ignore")
morceau(1000, d[1000 .. 1999])
morceau(2000, d[2000 .. 2999])
ordre({"op": "fin"})
verifie(FS["fichiers"].find("/b.be") == d && dernier()["ok"], "perte : renvoi depuis l'accuse -> fichier identique")

# --- controles de fin : l'ancien fichier reste en place
var ancien = FS["fichiers"]["/b.be"]
d = donnees(500)
ordre({"op": "debut", "chemin": "/b.be", "taille": 500, "md5": "00"})
morceau(0, d)
ordre({"op": "fin"})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "MD5") >= 0, "MD5 different : refuse")
verifie(FS["fichiers"]["/b.be"] == ancien && !FS["fichiers"].contains("/fsmqtt.tmp"), "MD5 different : ancien fichier intact, temporaire supprime")
ordre({"op": "debut", "chemin": "/b.be", "taille": 500, "md5": md5(d)})
morceau(0, d[0 .. 299])
ordre({"op": "fin"})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "300 o sur 500") >= 0, "fin avant la taille : refuse")
ordre({"op": "debut", "chemin": "/b.be", "taille": 10, "md5": md5(d)})
morceau(0, d)
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "plus de données") >= 0, "plus de donnees qu'annonce : refuse")
ordre({"op": "fin"})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "aucun transfert") >= 0, "fin sans transfert : refuse")
RENOMMAGE_REFUSE = true
ordre({"op": "debut", "chemin": "/c.be", "taille": 500, "md5": md5(d)})
morceau(0, d)
ordre({"op": "fin"})
RENOMMAGE_REFUSE = false
verifie(!dernier()["ok"] && !FS["fichiers"].contains("/fsmqtt.tmp"), "renommage impossible : refuse, temporaire supprime")
verifie(FS["fichiers"]["/b.be"] == ancien, "temoin : /b.be toujours l'ancien apres les refus")

# --- chemins et tailles refuses
for c: ["b.be", "/../b.be", "/json/../b.be", "/", "/json/", "/fsmqtt.tmp", "/" + string.format("%050d", 0)]
    ordre({"op": "debut", "chemin": c, "taille": 1, "md5": "x"})
    verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "chemin refusé") >= 0, "chemin refuse : " + c)
end
ordre({"op": "debut", "chemin": "/x.be", "taille": 2000000, "md5": "x"})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "taille") >= 0, "taille > 1 Mo : refusee")
ordre({"op": "debut", "chemin": "/json", "taille": 1, "md5": "x"})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "dossier") >= 0, "chemin d'un dossier existant : refuse")
ordre({"op": "debut", "chemin": "/x.be", "taille": 1})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "md5") >= 0, "md5 absent : refuse")

# --- debut pendant un transfert : le premier est abandonne ; abandon explicite
ordre({"op": "debut", "chemin": "/d.be", "taille": 5, "md5": md5(bytes("0102030405"))})
morceau(0, bytes("0102"))
ordre({"op": "debut", "chemin": "/e.be", "taille": 1, "md5": md5(bytes("09"))})
morceau(0, bytes("09"))
ordre({"op": "fin"})
verifie(FS["fichiers"].find("/e.be") == bytes("09") && !FS["fichiers"].contains("/d.be"), "nouveau debut : l'ancien transfert est abandonne")
ordre({"op": "debut", "chemin": "/f.be", "taille": 1, "md5": "x"})
ordre({"op": "abandon"})
verifie(dernier()["ok"] && !FS["fichiers"].contains("/fsmqtt.tmp"), "abandon : temporaire supprime")
morceau(0, bytes("01"))
verifie(dernier()["op"] == "abandon", "abandon : un morceau tardif n'est plus accuse")

# --- payload vide (payload_b nil) et ecriture en echec
ordre({"op": "debut", "chemin": "/g.be", "taille": 3, "md5": md5(bytes("010203"))})
mqtt.abonnes[BASE + "morceau"](BASE + "morceau", 0, "", nil)
verifie(dernier()["op"] == "debut", "payload vide (nil) : ignore sans planter")
ECRITURE_KO = true
morceau(0, bytes("010203"))
ECRITURE_KO = false
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "écriture impossible") >= 0 && !FS["fichiers"].contains("/fsmqtt.tmp"),
        "ecriture en echec : refus repondu, temporaire supprime")
verifie(JOURNAL[-1][1] == LOG_LEVEL_ERREUR, "ecriture en echec : erreur journalisee")

# --- lecture (sauvegarde du persist par le PC)
d = donnees(4000)
FS["fichiers"]["/_persist.json"] = d
mqtt.publies = []
ordre({"op": "lit", "chemin": "/_persist.json"})
var relu = bytes()
var positions = []
for p: mqtt.publies
    if p[0] == BASE + "lu"    positions.push(p[1].get(0, -4))  relu = relu + p[1][4 ..]    end
end
verifie(relu == d && positions == [0, 1896, 3792], "lit : fichier renvoye par morceaux avec leur position " + str(positions))
verifie(dernier()["ok"] && dernier()["octets"] == 4000 && dernier()["md5"] == md5(d), "lit : taille et MD5 rendus")
d = donnees(10000)
FS["fichiers"]["/gros.json"] = d
mqtt.publies = []
ordre({"op": "lit", "chemin": "/gros.json"})
var lus = 0
for p: mqtt.publies    if p[0] == BASE + "lu"    lus += 1    end    end
verifie(lus == 4 && tasmota.timers.contains("fsmqtt_lit"), "lit : 4 morceaux par rappel, la suite par minuterie")
ordre({"op": "lit", "chemin": "/gros.json"})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "déjà en cours") >= 0, "lit : seconde lecture pendant la premiere refusee")
while tasmota.declenche("fsmqtt_lit") end
relu = bytes()
for p: mqtt.publies    if p[0] == BASE + "lu"    relu = relu + p[1][4 ..]    end    end
verifie(relu == d && dernier()["op"] == "lit" && dernier()["ok"] && dernier()["octets"] == 10000, "lit : 10 000 o en 2 lots, identiques")
ordre({"op": "lit", "chemin": "/absent.json"})
verifie(!dernier()["ok"], "lit : fichier absent -> refuse")

# --- rechargement, Berry, redemarrage
global.serveur = nil
ordre({"op": "recharge"})
verifie(persist.chargements == 1 && global.serveur == persist._p["serveur"] && dernier()["ok"], "recharge : persist.load() et globales")
ordre({"op": "berry"})
verifie(dernier()["ok"] && tasmota.cmds[-1] == "Backlog BrRestart", "berry : reponse puis BrRestart par Backlog (hors de la VM)")
ordre({"op": "redemarre"})
verifie(dernier()["ok"] && tasmota.cmds[-1] == "Backlog Restart 1", "redemarre : reponse puis Restart 1 par Backlog")

# --- ordres invalides
ordre({"op": "inconnu"})
verifie(!dernier()["ok"] && dernier()["erreur"] == "ordre inconnu", "ordre inconnu : refuse")
var n = size(JOURNAL)
mqtt.abonnes[BASE + "ordre"](BASE + "ordre", 0, "pas du json", bytes())
verifie(size(JOURNAL) == n + 1 && JOURNAL[-1][1] == LOG_LEVEL_ERREUR, "ordre illisible : erreur journalisee")

# --- effacement total, par lots, /sd compris (dossier du LittleFS, celui de l'image)
FS = {"fichiers": {"/sd/html/a.html": bytes("01")}, "dossiers": {"/sd": true, "/sd/html": true}}
for i: 0 .. 29    FS["fichiers"]["/f" + str(i) + ".be"] = bytes("01")    end
FS["dossiers"]["/json"] = true  FS["dossiers"]["/json/a"] = true
FS["fichiers"]["/json/a/z.json"] = bytes("01")
mqtt.publies = []
ordre({"op": "efface"})
verifie(dernier()["restants"] > 0 && size(FS["fichiers"]) > 1, "efface : premier lot seulement, avancement publie (" + str(dernier()["restants"]) + " restants)")
ordre({"op": "efface"})
verifie(!dernier()["ok"] && string.find(dernier()["erreur"], "déjà en cours") >= 0, "efface : second ordre pendant l'effacement refuse")
var lots = 1
while tasmota.declenche("fsmqtt_efface")    lots += 1    end
verifie(lots == 2 && dernier()["ok"] && dernier()["restants"] == 0 && dernier()["fichiers"] == 32 && dernier()["dossiers"] == 4,
        "efface : 2 lots de 20, 32 fichiers et 4 dossiers (" + str(dernier()) + ")")
verifie(size(FS["fichiers"]) == 0 && size(FS["dossiers"]) == 0, "efface : tout le FS supprime, /sd compris")

# --- sans topic dans le persist : rien n'est abonne
persist._p = {"serveur": {}}
mqtt.abonnes = {}
n = size(JOURNAL)
verifie(fsMqtt.demarre() == nil && size(mqtt.abonnes) == 0 && JOURNAL[-1][1] == LOG_LEVEL_ERREUR, "sans serveur.mqtt.topic : inactif, erreur journalisee")

var cibles = []
for j: JOURNAL    if j[2] != nil    cibles.push(j[2])    end    end
verifie(size(cibles) == 0, "logs : cible general (aucune cible inconnue de logFonctions) " + str(cibles))

print(echecs == 0 ? "BANC_FSMQTT: OK" : "BANC_FSMQTT: ECHEC (" + str(echecs) + ")")
