# Banc Berry de l'emulation Hue (Alexa) : data/fs/hueFonctions.be (module pur) et data/fs/controleHue.be (pont global.hue_bridge,
# reglage FriendlyName et Emulation). Charge les VRAIS modules (et le vrai configGlobal.be) sous des bouchons
# (bouchons_berry/hue/ : logFonctions, persist) et un faux tasmota qui garde les commandes envoyees. Aucun reseau, aucune carte.
# Persists REELS des 4 cartes lus dans data/ (relais, volets, cles alexa).
#
# Lancer via son enveloppe Python (racine, berry.exe, code de sortie, mutants) :
#     python outils_docs/scripts_python/berry/banc_hue.py
# Ou DEPUIS LA RACINE : lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_hue.be [dossier_sources]
# Derniere ligne : BANC_HUE: OK|ECHEC.
import global
import sys
import json
import string
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push("data/fs")                                                  # configGlobal.be reel
sys.path().push(SOURCES)                                                    # modules testes (copie mutee eventuelle)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/hue")      # le dernier pousse l'emporte

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
var serveur = {}                                                            # globales du demarrage, citees par configGlobal.be
var diverses = {}
var modules = {}
var drivers = {}
var JOURNAL = []
import logFonctions                                                         # globale, comme apres demarrage.prologue (bouchon)
var PERSIST_BANC = {}
var MAC = "AA:BB:CC:DD:EE:FF"

# Faux firmware : FriendlyName1..8, Emulation, relais, SetOption109. 'envoyees' = commandes qui ECRIVENT, dans l'ordre.
class TasmotaStub
    var fn, emulation, envoyees, puissances, poses, option109, fige, panne, mac, horsCanaux
    def init(emulation, noms)
        self.mac = MAC
        self.emulation = emulation
        self.fn = noms != nil ? noms : ["Tasmota", "Tasmota2", "Tasmota3", "Tasmota4", "Tasmota5", "Tasmota6", "Tasmota7", "Tasmota8"]
        self.envoyees = []
        self.puissances = []
        for i: 0 .. 31    self.puissances.push(false)    end
        self.poses = []
        self.option109 = 0
        self.fige = false             # true : les FriendlyName ne changent pas (masquage impossible)
        self.panne = false            # true : set_power et get_power levent
        self.horsCanaux = false       # true : set_power rend nil sans commuter (index >= devices_present)
    end
    def cmd(c, mute)
        var p = string.split(c, " ", 1)
        var nom = p[0]
        if nom == "FriendlyName" && size(p) == 1
            var r = {}
            for i: 1 .. 8    r["FriendlyName" + str(i)] = self.fn[i - 1]    end
            return r
        elif string.find(nom, "FriendlyName") == 0 && size(p) == 2
            self.envoyees.push(c)
            if !self.fige    self.fn[int(nom[12 ..]) - 1] = p[1]    end
            return {nom: p[1]}
        elif nom == "Emulation"
            if size(p) == 2
                self.envoyees.push(c)
                self.emulation = int(p[1])
            end
            return {"Emulation": self.emulation}
        end
        return {"Command": "Unknown"}
    end
    def get_power()
        if self.panne    raise "io_error", "panne simulee"    end
        return self.puissances.copy()
    end
    def set_power(i, v)
        if self.panne    raise "io_error", "panne simulee"    end
        if self.horsCanaux    return nil    end
        self.poses.push([i, v])
        self.puissances[i] = v
        return v
    end
    def get_option(n) return n == 109 ? self.option109 : 0 end
    def wifi() return {"mac": self.mac, "up": true} end
end
var tasmota = TasmotaStub(0, nil)

var echecs = 0
var nb = 0
def verifie(ok, libelle)
    print((ok ? "OK   " : "KO   ") + libelle)
    nb += 1
    if !ok    echecs += 1    end
end

def erreurs()
    var n = 0
    for e: JOURNAL    if e[1] == LOG_LEVEL_ERREUR    n += 1    end    end
    return n
end

def lit_persist(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return json.load(t)
end

# Type d'erreur Hue d'une reponse, nil si ce n'est pas une erreur Hue (succes, nil, JSON invalide)
def type_erreur(x)
    var j = type(x) == "string" ? json.load(x) : nil
    var e = isinstance(j, list) && size(j) > 0 && isinstance(j[0], map) ? j[0].find("error") : nil
    return isinstance(e, map) ? e.find("type") : nil
end

def ns(liste)
    var r = []
    for e: liste    r.push(e["n"])    end
    return r
end

# Reference : xdrv_20_hue.ino::DecodeLightIdZigbee, recopie du C (hors Zigbee)
def decode_natif(hue_id)
    var relay_id = hue_id & 0xF
    if hue_id & (1 << 28)    relay_id += 16    end
    if relay_id == 0    relay_id = 32    end
    return relay_id
end

# Rejoue l'init du pont : persist pose, faux firmware neuf, journal vide
def demarre(persist_banc, stub)
    import global
    global.PERSIST_BANC = persist_banc
    global.tasmota = stub
    global.JOURNAL = []
    global.hue_bridge = nil
    var ok = true
    try
        import controleHue
        controleHue.init(controleHue)
    except .. as e, m
        print("     exception : " + str(e) + " " + str(m))
        ok = false
    end
    return ok
end

import hueFonctions
import controleHue

# --- 1. id Hue : formule native (bits 4 a 27 = 3 octets bas de la MAC 0xDD 0xEE 0xFF -> 0x0DDEEFF0)
verifie(hueFonctions.idHue(1, MAC) == 0x0DDEEFF1, "id du relais 1")
verifie(hueFonctions.idHue(15, MAC) == 0x0DDEEFFF, "id du relais 15")
verifie(hueFonctions.idHue(16, MAC) == 0x1DDEEFF0, "id du relais 16 : bit 28 pose")
verifie(hueFonctions.idHue(24, MAC) == 0x1DDEEFF8, "id du relais 24 : bit 28 pose")
verifie(hueFonctions.idHue(32, MAC) == 0x0DDEEFF0, "id du relais 32 : code 0, sans bit 28")
var aller_retour = true
for n: 1 .. 32
    if decode_natif(hueFonctions.idHue(n, MAC)) != n    aller_retour = false    end
end
verifie(aller_retour, "DecodeLightId natif retombe sur le meme relais (1 a 32)")
verifie(hueFonctions.idHue(0, MAC) == nil && hueFonctions.idHue(33, MAC) == nil && hueFonctions.idHue("1", MAC) == nil, "id hors de 1 a 32 refuse")
verifie(hueFonctions.idHue(1, "pas une mac") == nil, "MAC illisible refusee")
verifie(hueFonctions.uniqueid(5, MAC) == "aa:bb:cc:dd:ee:ff:00:15-01" && hueFonctions.uniqueid(16, MAC) == "aa:bb:cc:dd:ee:ff:00:00-01",
        "uniqueid comme GetHueDeviceId (octet bas xor 0x10, MAC en minuscules)")

# --- 2. choix des sorties sur un persist d'essai
var VR = {"activation": "ON", "environnement": {"VRs": {"VR1": {"activation": "ON", "relais1": 7}, "VR2": {"activation": "OFF", "relais1": 9}}}}
var essai = {"activation": "ON",
    "a": {"activation": "ON", "environnement": {"relais": {
        "r1": {"activation": "ON", "id": 1, "nom": "Relais 1"},
        "r2": {"activation": "ON", "id": 2, "alexa": {"activation": "ON", "nom": "Lampe", "type": "onoff"}},
        "r3": {"activation": "ON", "id": 3, "alexa": {"activation": "OFF", "nom": "Eteinte"}},
        "r4": {"activation": "OFF", "id": 4, "alexa": {"activation": "ON", "nom": "Inactif"}},
        "r7": {"activation": "ON", "id": 7, "alexa": {"activation": "ON", "nom": "Volet monte"}},
        "r8": {"activation": "ON", "id": 8, "alexa": {"activation": "ON", "nom": "Volet descend"}},
        "r9": {"activation": "ON", "id": 9, "alexa": {"activation": "ON", "nom": "Volet inactif"}},
        "r10": {"activation": "ON", "id": 10, "alexa": {"activation": "ON", "nom": ""}},
        "r11": {"activation": "ON", "id": 11, "alexa": {"activation": "ON", "nom": "123456789012345678901234567890123"}},
        "r12": {"activation": "ON", "id": 12, "alexa": {"activation": "ON", "nom": "lampe"}},
        "r13": {"activation": "ON", "id": 13, "alexa": {"activation": "ON", "nom": "Variateur", "type": "dimmer"}},
        "r14": {"activation": "ON", "id": 0, "alexa": {"activation": "ON", "nom": "Id nul"}},
        "r15": {"activation": "ON", "id": 15, "alexa": "ON"},
        "r16": {"activation": "ON", "id": 16, "alexa": {"activation": "ON", "nom": "12345678901234567890123456789012"}},
        "r2b": {"activation": "ON", "id": 2, "alexa": {"activation": "ON", "nom": "Meme relais"}},
        "r24": {"activation": "ON", "id": 24, "alexa": {"activation": "ON", "nom": "Sans type"}}}}},
    "b": {"activation": "OFF", "environnement": {"relais": {"r5": {"activation": "ON", "id": 5, "alexa": {"activation": "ON", "nom": "Module inactif"}}}}}}
JOURNAL = []
var l = hueFonctions.appareils(essai, {"voletRoulants": VR})
verifie(str(ns(l)) == "[2, 9, 16, 24]", "sorties exposees triees : 2, 9 (VR inactif), 16 (32 caracteres), 24 (type absent = onoff) : " + str(ns(l)))
verifie(l[0]["nom"] == "Lampe" && l[0]["cle"] == "a/r2", "nom vocal et cle de la sortie repris")
verifie(erreurs() == 11, "un refus journalise par sortie refusee (11) : " + str(erreurs()))
var cibles_ok = true
for e: JOURNAL    if e[2] != "emulationHue" || string.find(e[0], "CONTROLE_HUE_ERREUR: ") != 0    cibles_ok = false    end    end
verifie(cibles_ok, "refus en erreur, prefixe CONTROLE_HUE_ERREUR, cible emulationHue")
var vus = ""
for e: JOURNAL    vus += e[0] + "\n"    end
verifie(string.find(vus, "a/r7 refusee, relais de volet") >= 0 && string.find(vus, "a/r8 refusee, relais de volet") >= 0, "relais1 et relais1+1 d'un volet actif refuses")
verifie(string.find(vus, "a/r12 refusee, nom deja pris par a/r2") >= 0, "nom en double (casse ignoree) refuse")
verifie(string.find(vus, "a/r2b refusee, relais 2 deja expose") >= 0, "relais deja expose refuse (le premier par cle garde)")
verifie(string.find(vus, "a/r10 ") >= 0 && string.find(vus, "a/r11 ") >= 0, "nom vide et nom de 33 caracteres refuses")
verifie(string.find(vus, "a/r13 refusee, type dimmer") >= 0 && string.find(vus, "a/r14 refusee, id") >= 0 && string.find(vus, "a/r15 refusee, cle alexa invalide") >= 0, "type, id et cle alexa invalides refuses")
verifie(string.find(vus, "a/r4 ") >= 0 && string.find(vus, "b/r5 ") >= 0 && string.find(vus, "a/r3") < 0 && string.find(vus, "a/r1 ") < 0,
        "relais et module inactifs refuses ; alexa OFF ou absente : ni liste ni bruit")
VR["activation"] = "OFF"
verifie(str(ns(hueFonctions.appareils(essai, {"voletRoulants": VR}))) == "[2, 7, 8, 9, 16, 24]", "driver des volets a OFF : ses relais redeviennent exposables")
VR["activation"] = "ON"

# --- 3. persist absent ou invalide : liste vide, jamais d'exception
var sans_exception = true
try
    for p: [[nil, nil], ["x", 3], [{"activation": "OFF", "a": essai["a"]}, nil], [{"activation": "ON", "m": "pas une map"}, {"voletRoulants": "x"}],
            [{"activation": "ON", "m": {"environnement": "x"}}, {"voletRoulants": {"activation": "ON", "environnement": {"VRs": "x"}}}],
            [{"activation": "ON", "m": {"environnement": {"relais": ["liste"]}}}, nil], [{"activation": "ON", "m": {"environnement": {"relais": {"r": "x"}}}}, nil]]
        if size(hueFonctions.appareils(p[0], p[1])) != 0    sans_exception = false    end
    end
except .. as e, m
    print("     exception : " + str(e) + " " + str(m))
    sans_exception = false
end
verifie(sans_exception, "persist absent, modules a OFF ou blocs invalides : liste vide, aucune exception")
var bases = [{}, {"serveur": "x"}, {"serveur": {"emulationHue": "ON"}}, {"serveur": {"emulationHue": {"activation": "ON"}}, "modules": "x", "drivers": 3}]
var inits_ok = true
for b: bases
    var t = TasmotaStub(2, nil)
    if !demarre(b, t) || global.hue_bridge == nil || global.hue_bridge.discover() != nil    inits_ok = false    end
end
verifie(inits_ok, "init sur persist absent ou invalide : pont publie, vide, aucune exception")

# --- 4. les 4 vrais persists
var CARTES = {"data/garage/tasmota32p4-serveur-modbus/_persist.json": "[1, 5, 24, 26]",
              "data/cave/tasmota32s3-serveur-rly/_persist.json": "[2, 3]",
              "data/rdc/tasmota32s3-grenier/_persist.json": "[]",
              "data/etage2/tasmota32s3-grenier/_persist.json": "[]"}
for chemin: CARTES.keys()
    var p = lit_persist(chemin)
    JOURNAL = []
    var lp = hueFonctions.appareils(p["modules"], p["drivers"])
    var eh = p["serveur"].find("emulationHue")
    verifie(str(ns(lp)) == CARTES[chemin] && erreurs() == 0, chemin + " : sorties " + str(ns(lp)) + ", aucune erreur")
    verifie(isinstance(eh, map) && eh.find("activation") == "OFF" && eh.find("log") == "info", chemin + " : serveur.emulationHue a OFF, log info")
end

# Shutters du P4 refuses meme avec une cle alexa (rideau 2 et 3, portail 20 a 23)
var p4 = lit_persist("data/garage/tasmota32p4-serveur-modbus/_persist.json")
for id: [2, 3, 20, 22]
    p4["modules"]["garage"]["environnement"]["relais"]["relai" + str(id)]["alexa"] = {"activation": "ON", "nom": "Shutter " + str(id)}
end
JOURNAL = []
verifie(str(ns(hueFonctions.appareils(p4["modules"], p4["drivers"]))) == "[1, 5, 24, 26]" && erreurs() == 4, "P4 reel : relais 2, 3, 20 et 22 des Shutters refuses meme avec une cle alexa")

# --- 5. reglage du firmware par l'init
var p4on = lit_persist("data/garage/tasmota32p4-serveur-modbus/_persist.json")
var p4off = lit_persist("data/garage/tasmota32p4-serveur-modbus/_persist.json")
p4on["serveur"]["emulationHue"]["activation"] = "ON"

var t_off = TasmotaStub(2, nil)
demarre(p4off, t_off)
verifie(str(t_off.envoyees) == "['Emulation 0']", "OFF : Emulation remise a 0, aucun FriendlyName touche : " + str(t_off.envoyees))
verifie(global.hue_bridge != nil && global.hue_bridge.discover() == nil, "OFF : pont publie mais vide")
var t_off0 = TasmotaStub(0, nil)
demarre(p4off, t_off0)
verifie(size(t_off0.envoyees) == 0, "OFF et Emulation deja a 0 : aucune commande (pas de redemarrage)")

var t_on = TasmotaStub(0, nil)
demarre(p4on, t_on)
var dernier_fn = -1
var premiere_emu = -1
for i: 0 .. size(t_on.envoyees) - 1
    if string.find(t_on.envoyees[i], "FriendlyName") == 0    dernier_fn = i    end
    if string.find(t_on.envoyees[i], "Emulation") == 0 && premiere_emu < 0    premiere_emu = i    end
end
verifie(dernier_fn == 7 && premiere_emu == 8 && size(t_on.envoyees) == 9 && t_on.envoyees[8] == "Emulation 2", "ON : 8 FriendlyName masques PUIS Emulation 2 : " + str(t_on.envoyees))
verifie(t_on.fn[0] == "$Tasmota" && t_on.fn[7] == "$Tasmota8", "ON : FriendlyName prefixes de $, nom garde")
var t_on2 = TasmotaStub(2, ["$a", "$", "$c", "$d", "$e", "$f", "$g", "$h"])
demarre(p4on, t_on2)
verifie(size(t_on2.envoyees) == 0, "ON et tout deja regle : aucune commande (pas de redemarrage en boucle) : " + str(t_on2.envoyees))
var t_part = TasmotaStub(0, ["$a", "", "c", "$d", "$e", "$f", "$g", "$h"])
demarre(p4on, t_part)
verifie(str(t_part.envoyees) == "['FriendlyName2 $', 'FriendlyName3 $c', 'Emulation 2']", "ON : seuls les noms non masques sont reecrits : " + str(t_part.envoyees))
var t_fige = TasmotaStub(2, nil)
t_fige.fige = true
demarre(p4on, t_fige)
verifie(t_fige.emulation == 0 && t_fige.envoyees[-1] == "Emulation 0", "masquage non verifie : emulation remise a 0 (relais natifs jamais listes)")

# --- 6. le pont : decouverte, etat, commandes (P4 reel a ON, Emulation deja reglee)
var t = TasmotaStub(2, ["$a", "$b", "$c", "$d", "$e", "$f", "$g", "$h"])
demarre(p4on, t)
var pont = global.hue_bridge
var id5 = hueFonctions.idHue(5, MAC)
var id24 = hueFonctions.idHue(24, MAC)
var id20 = hueFonctions.idHue(20, MAC)
t.puissances[4] = true
var d = json.load("{" + pont.discover() + "}")
verifie(isinstance(d, map) && size(d) == 4 && d.contains(str(id5)) && d.contains(str(id24)), "decouverte : JSON valide, les 4 sorties du P4 sous leur id Hue")
verifie(d[str(id5)]["state"]["on"] == true && d[str(id24)]["state"]["on"] == false && d[str(id5)]["name"] == "Projecteur du garage", "decouverte : etat reel des relais et nom vocal")
verifie(d[str(id5)]["uniqueid"] == hueFonctions.uniqueid(5, MAC) && !d[str(id5)]["state"].contains("bri"), "decouverte : uniqueid, pas de bri (Echo de 2e generation)")
t.option109 = 1
verifie(json.load(pont.full_status(id5))["state"]["bri"] == 254, "SetOption109 (Echo 1re generation) : bri dans l'etat")
t.option109 = 0
var st = json.load(pont.full_status(id20))
verifie(isinstance(st, list) && st[0]["error"]["type"] == 3, "etat d'un id hors liste blanche (portail) : erreur Hue, pas l'etat du relais")
verifie(type(pont.full_status(12345)) == "string", "etat d'un id inconnu : une chaine")
verifie(pont.groups() == nil, "groupe 0 : rien ajoute (le natif liste deja les ids)")

JOURNAL = []
var r = pont.cmd(id24, "{\"on\":true}")
verifie(str(t.poses) == "[[23, true]]" && t.puissances[23] == true, "commande ON du projecteur du jardin : set_power(23, true)")
var rj = json.load(r)
verifie(isinstance(rj, list) && rj[0]["success"]["/lights/" + str(id24) + "/state/on"] == true, "reponse Hue de succes, chemin de l'id")
var info = false
for e: JOURNAL    if e[1] == LOG_LEVEL_INFO && string.find(e[0], "CONTROLE_HUE: Projecteur du jardin") == 0    info = true    end    end
verifie(info, "une ligne info par commande recue")
t.poses = []
r = pont.cmd(id24, "{\"on\":false,\"bri\":120}")
verifie(str(t.poses) == "[[23, false]]" && json.load(r)[0]["success"]["/lights/" + str(id24) + "/state/on"] == false, "commande OFF (bri ignore)")

t.poses = []
var refus_ok = true
for id: [id20, hueFonctions.idHue(2, MAC), hueFonctions.idHue(25, MAC), hueFonctions.idHue(3, MAC), 0, 12345]
    var y = pont.cmd(id, "{\"on\":true}")
    if type_erreur(y) != 3    refus_ok = false    end
end
verifie(refus_ok && size(t.poses) == 0, "commande d'un id hors liste blanche (portail, rideau, pompe...) : erreur Hue, rien ne commute")
var corps_ok = true
for corps: [nil, "", "pas du json", "{\"bri\":3}", "{\"on\":1}", "[true]"]
    var y = pont.cmd(id5, corps)
    if type_erreur(y) != 6    corps_ok = false    end
end
verifie(corps_ok && size(t.poses) == 0, "corps vide, invalide ou sans booleen on : erreur Hue, rien ne commute")
t.panne = true
var leve = false
var x = nil
try
    x = pont.cmd(id5, "{\"on\":true}")
except .. as e, m
    leve = true
end
verifie(!leve && type_erreur(x) == 901, "exception pendant la commande : rattrapee, erreur Hue rendue (jamais la main au natif)")
leve = false
try
    x = pont.full_status(id5)
except .. as e, m
    leve = true
end
verifie(!leve && type(x) == "string", "exception pendant l'etat : rattrapee, une chaine")
t.panne = false

# --- 7. MAC lue a chaque requete : vide ou nulle au demarrage (C6 du P4), puis la vraie ; changement de MAC
var tm = TasmotaStub(2, ["$a", "$b", "$c", "$d", "$e", "$f", "$g", "$h"])
tm.mac = ""
demarre(p4on, tm)
var pm = global.hue_bridge
JOURNAL = []
verifie(pm.discover() == nil && type_erreur(pm.cmd(id5, "{\"on\":true}")) == 901 && size(tm.poses) == 0 && erreurs() == 1,
        "MAC vide : rien d'expose, commande refusee par une erreur Hue, UNE seule erreur journalisee pour la panne")
verifie(pm.discover() == nil && type_erreur(pm.cmd(id5, "{\"on\":true}")) == 901 && erreurs() == 1, "MAC toujours illisible : pas de nouvelle ligne de log (anti-inondation)")
tm.mac = "00:00:00:00:00:00"
verifie(pm.discover() == nil && type(pm.full_status(id5)) == "string", "MAC nulle (C6 pas pret) : rien d'expose, une chaine")
tm.mac = MAC
var dm = json.load("{" + pm.discover() + "}")
verifie(isinstance(dm, map) && size(dm) == 4 && dm.contains(str(id5)), "MAC lue plus tard : les 4 sorties apparaissent sous les ids de la vraie MAC")
tm.mac = "11:22:33:44:55:66"
var id5b = hueFonctions.idHue(5, tm.mac)
var db = json.load("{" + pm.discover() + "}")
verifie(db.contains(str(id5b)) && !db.contains(str(id5)) && type_erreur(pm.cmd(id5, "{\"on\":true}")) == 3, "MAC changee : ids recalcules, l'ancien id n'est plus accepte")

# --- 7b. set_power rend nil (index hors des canaux de la carte) : rien n'a commute, Alexa n'entend pas « fait »
var th = TasmotaStub(2, ["$a", "$b", "$c", "$d", "$e", "$f", "$g", "$h"])
demarre(p4on, th)
th.horsCanaux = true
JOURNAL = []
var rh = global.hue_bridge.cmd(id24, "{\"on\":true}")
verifie(type_erreur(rh) == 901 && erreurs() == 1, "set_power nil : erreur Hue (pas de succes) et erreur journalisee")

# --- 8. pont a OFF : tout est refuse
var t2 = TasmotaStub(2, nil)
demarre(p4off, t2)
var x2 = global.hue_bridge.cmd(id5, "{\"on\":true}")
verifie(type_erreur(x2) == 3 && size(t2.poses) == 0, "OFF : commande d'un id pourtant marque alexa refusee")

print("")
print(str(nb) + " controles, " + str(echecs) + " echec(s)")
print("BANC_HUE: " + (echecs == 0 ? "OK" : "ECHEC"))
