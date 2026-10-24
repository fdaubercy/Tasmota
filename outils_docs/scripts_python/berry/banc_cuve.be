# Banc de test Berry de la LOGIQUE METIER de la cuve (2026-10-24, audit Berry P10.4, constat B10) :
#   data/garage/tasmota32s3-capteurs-cuve-modbus/cuveFonctions.be   (niveau -> hauteur -> taux -> volume -> teinte -> couleur)
#   data/garage/tasmota32s3-capteurs-cuve-modbus/controleCuve.be     (page web, json_append, filtre de l'historique, DS18B20)
# -----------------------------------------------------------------------------------------------------------------
# Charge les VRAIS fichiers (pas des copies) sous des globaux bouchonnes et les EXECUTE, AVANT de flasher une carte.
#
# Lancer via son enveloppe Python (deduit racine + berry.exe, code de sortie 0/1) :
#     python outils_docs/scripts_python/berry/banc_cuve.py [dossier_cuve]
# Ou directement, DEPUIS LA RACINE DU DEPOT (verdict = DERNIERE ligne, BANC_CUVE: OK | ECHEC (n)) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_cuve.be [dossier_cuve]
#
# dossier_cuve (defaut data/garage/tasmota32s3-capteurs-cuve-modbus) : pour eprouver une COPIE ENTIERE du dossier
# (temoin mute) sans toucher a data/. Le _persist.json lu est celui de ce dossier : geometrie, conversion
# mV/cm, ruban, thermometre viennent de LUI, jamais recopies ici. Passer la copie INTACTE avant la copie mutee.
#
# VALEURS ATTENDUES : calculees ici par des formules INDEPENDANTES du code teste (entiers purs ou tables a la
# main), jamais relues sur la sortie du code. Le seul maillon reconstruit est tasmota.scale_int, dont le
# bouchon PORTE le C du firmware (support_float.ino : changeIntScale -> changeUIntScale) ; il est lui-meme
# controle contre la formule flottante v * vmax / 32767 (+-1) avant de servir.
#
# TEMOINS NEGATIFS : controles qui DOIVENT echouer (temoin()), plus, hors de ce fichier, une mutation de
# cuveFonctions.be lancee sur une copie (le banc doit passer ROUGE) - voir le rapport de P10.4.
#
# DEFAUTS CONNUS (DEFAUTS_CONNUS, modele de banc_boot.be) : le comportement ATTENDU apres correction est ecrit
# des aujourd'hui. Tant que le drapeau vaut true, un controle non satisfait s'affiche CONNU et ne compte pas ;
# s'il devient satisfait il s'affiche CORRIGE ? et COMPTE comme echec : passer le drapeau a false.
#
# NE TESTE PAS : le vrai tasmota.scale_int du firmware (bouchon porte du C), le timing des crons, le rendu reel
# de la page, le ruban physique, le vrai ModBus, le pilote i2c_ads1115 reel (mesureValide est simule), la
# memoire. Un banc vert ne remplace pas l'observation sur la carte.
import global
import sys
import string
import json

var SOURCES_CUVE = size(global._argv) > 1 ? global._argv[1] : "data/garage/tasmota32s3-capteurs-cuve-modbus"
# berry.exe cherche les modules du DERNIER chemin ajoute au premier : bouchons de la cuve > bouchons communs
# (light, persist) > sources de la cuve.
sys.path().push(SOURCES_CUVE)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/cuve")

var DEFAUTS_CONNUS = {
    "N1": true,    # lecture ADS1115 NEGATIVE (bruit a 0 V) -> scale_int la rend en pleine echelle (wrap uint16) : cuve "pleine"
    "HB": true,    # taux et volume non bornes : un capteur au-dessus de la hauteur donne > 100 % et un volume > capacite
    "T1": true,    # taux tronque une unite trop bas par la virgule flottante (hauteur 100 cm : 53 cm -> 52 %)
    "V1": true,    # volume tronque d'un litre par la virgule flottante (cuve 100x100x100 : 13 %, 26 %, 52 %)
    "D3": true,    # ReglageCuve hauteurCuve abc : 0 memorise, alors que l'aide promet "non entier : ignore"
    "D3b": true,   # une dimension a 0 memorisee fait lever divzero_error a chaque releve (real(hauteur) au denominateur)
}

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
var journal = []                                  # [niveau, message, cible] de logFonctions.log
class LogStub def log(m, n, c) journal.push([n, str(m), c]) end end
var logFonctions = LogStub()
class Driver end

# --- tasmota : seulement ce que la logique de la cuve appelle ---
# scale_int : PORT du firmware (support_float.ino:447-467 changeIntScale, :392-435 changeUIntScale). Deux
# particularites qui comptent : les 5 arguments doivent etre ENTIERS (xdrv_52_3_berry_tasmota.ino : sinon
# type_error), et le premier est reconverti en uint16_t -> un negatif devient num + 65536 (donc > from_max,
# donc ramene a from_max).
def scaleUInt(num, fmin, fmax, tmin, tmax)
    if fmin >= fmax    return (tmin > tmax ? tmax : tmin)    end
    if num > fmax    num = fmax    elif num < fmin    num = fmin    end
    if tmin > tmax
        num = (fmax - num) + fmin
        var t = tmin   tmin = tmax   tmax = t
    end
    if num == fmin    return tmin    end
    if num == fmax    return tmax    end
    var r
    if tmax - tmin > fmax - fmin
        r = (((num - fmin) * (tmax - tmin) * 2) / (fmax - fmin) + 1) / 2 + tmin
    else
        r = (((num - fmin) * 2 + 1) * (tmax - tmin + 1)) / ((fmax - fmin + 1) * 2) + tmin
    end
    return (r > tmax ? tmax : (r < tmin ? tmin : r))
end
class TasmotaStub
    var crons, timers, cmds, reponses, ajouts
    def init() self.crons = [] self.timers = [] self.cmds = {} self.reponses = [] self.ajouts = [] end
    def scale_int(v, a, b, c, d)
        for x: [v, a, b, c, d]
            if type(x) != "int"    raise "type_error", "scale_int: arguments entiers requis"    end
        end
        return scaleUInt(v & 65535, a, b, c, d)         # a, c >= 0 : decalages nuls de changeIntScale
    end
    def yield() end
    def add_driver(d) end
    def add_cron(c, f, id) self.crons.push([c, id]) end
    def remove_cron(id) self.crons.push(["remove", id]) end
    def set_timer(ms, f) self.timers.push(ms) end
    def add_cmd(n, f) self.cmds[n] = f end
    def resp_cmnd(x) self.reponses.push(x) end
    def response_append(x) self.ajouts.push(x) end
end
var tasmota = TasmotaStub()

class ControleGeneralStub
    var capteurs, nbIOActivesJSON
    def init() self.capteurs = {} self.nbIOActivesJSON = {"analogiques": {"actives": {"nb": 1}, "reels": {"nb": 1}}} end
    def lectureSensors() return self.capteurs end
end
var controleGeneral = ControleGeneralStub()

var modules = {}
var drivers = {}
var diverses = {}
import light
global.light = light
import modbusFonctions
import ledsFonctions
import gestionFileFolder
import persist

def lis(chemin)
    var f = open(chemin, "r")
    var s = f.read()
    f.close()
    return s
end
# Recharge le persist de la cuve : etat neuf pour chaque scenario
def charge()
    var p = json.load(lis(SOURCES_CUVE + "/_persist.json"))
    modules = p["modules"]
    drivers = p["drivers"]
    diverses = p["diverses"]
    diverses["historique"] = {"activation": "OFF"}
end
charge()
var CUVE = modules["cuve"]
var ANA0 = CUVE["environnement"]["analogiques"]["analogique1"]
# Geometrie et conversion LUES dans le persist de la carte (les attendus en derivent)
var HAUT = CUVE["dimensions"]["hauteur"]
var LARG = CUVE["dimensions"]["largeur"]
var LONG = CUVE["dimensions"]["longueur"]
var CONV = ANA0["conversion_mV_cm"]
var VMAX = 6144                                   # plage +-6.144 V de l'ADS1115 (Sensor12 Range) : int, comme au demarrage
var ADRESSE = ANA0["type"] + ANA0["id"] - 1       # adresse de la sentinelle ModBus : 4704

import cuveFonctions

# --- verdicts ---
var echecs = 0
var nbControles = 0
def verifie(c, nom)
    nbControles += 1
    print((c ? "  ok   " : "  ECHEC ") + nom)
    if !c    echecs += 1    end
end
# Temoin negatif : 'c' est une affirmation FAUSSE ; le banc doit la voir fausse
def temoin(nom, c)
    nbControles += 1
    if c
        print("  ECHEC (temoin) " + nom + " : l'affirmation fausse est passee, le banc ne sait pas echouer")
        echecs += 1
    else
        print("  ok   [temoin negatif, echec attendu] " + nom)
    end
end
def connu(cle, nom, condition, constat)
    nbControles += 1
    if !DEFAUTS_CONNUS.find(cle, false)
        print((condition ? "  ok   " : "  ECHEC ") + nom + " [" + cle + "]")
        if !condition    echecs += 1    end
        return
    end
    if condition
        print("  CORRIGE ? " + nom + " [" + cle + "] : passer DEFAUTS_CONNUS['" + cle + "'] a false")
        echecs += 1
    else
        print("  CONNU   " + nom + " [" + cle + "]" + (constat != nil ? " -- aujourd'hui : " + constat : ""))
    end
end

# --- montage d'un scenario ---
def remet(vmax, conv, h, l, L)
    charge()
    CUVE = modules["cuve"]
    ANA0 = CUVE["environnement"]["analogiques"]["analogique1"]
    ANA0["conversion_mV_cm"] = conv
    if h == nil    CUVE.remove("dimensions")    else    CUVE["dimensions"] = {"hauteur": h, "largeur": l, "longueur": L}    end
    cuveFonctions.voltageMax = vmax
    cuveFonctions.sensorsCuve = {"valeursAnalogiques": {"valeurCapteurHauteur": 0}, "niveauCuve": {"hauteurEau": 0, "tauxRemplissage": 0, "volume": 0}}
    cuveFonctions.enErreur = false
    cuveFonctions.retourAutoEnregistre = false
    light.etat = {"power": true, "hue": 60, "sat": 255, "bri": 127}
    light.sets = []
    ledsFonctions.teintes = []   ledsFonctions.erreurs = []   ledsFonctions.retours = []
    modbusFonctions.notes = []   modbusFonctions.demandes = []   modbusFonctions.fraiche = true
    journal.clear()
    global.i2c_ads1115 = nil
end
def remetNormal() remet(VMAX, CONV, HAUT, LARG, LONG) end

def capteurs(raw)
    controleGeneral.capteurs = {"ADS1115": {"A0": raw, "A1": 0, "A2": 0, "A3": 0}}
end
# Un releve de la voie A0 (valeur toujours "changee" : la valeur memorisee est invalidee d'abord)
def releve(raw)
    capteurs(raw)
    ANA0["value"] = -999999
    cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", "")
end
def mesures() return cuveFonctions.sensorsCuve end
def derniereTeinte()
    var t = ledsFonctions.teintes
    return size(t) > 0 ? t[size(t) - 1] : nil
end
def hex2(s) return int("0x" + s) end
def proche(a, b, tol) return (a - b <= tol) && (b - a <= tol) end

# ================================================================================================
print("1. Bouchon de scale_int controle contre la formule flottante (avant de servir d'etalon)")
var pires = 0
for n: [0, 1, 100, 5000, 9100, 16384, 18200, 32766, 32767]
    var obs = tasmota.scale_int(n, 0, 32767, 0, VMAX)
    var ref = n * VMAX / 32767.0
    if !(obs - ref <= 1.0 && ref - obs <= 1.0)    pires += 1    end
end
verifie(pires == 0, "scale_int(n, 0, 32767, 0, 6144) = n * 6144 / 32767 a +-1 mV sur 9 valeurs")
verifie(tasmota.scale_int(32767, 0, 32767, 0, VMAX) == VMAX && tasmota.scale_int(0, 0, 32767, 0, VMAX) == 0, "bornes exactes : 0 -> 0, 32767 -> plage")
verifie(tasmota.scale_int(40000, 0, 32767, 0, VMAX) == VMAX, "au-dessus de 32767 : ramene a la plage (saturation)")
var typeErreur = false
try tasmota.scale_int(100, 0, 32767, 0, 0.00) except .. as e, m typeErreur = (e == "type_error") end
verifie(typeErreur, "scale_int refuse un argument reel (voltageMax = 0.00 par defaut) : type_error comme au firmware")

# ================================================================================================
print("2. teinteNiveau : taux de remplissage -> teinte 0 (rouge) .. 119 (vert), borne a [0, 1]")
# Attendu a la main : int(119 * taux)
var tabTeinte = [[0, 0], [1, 119], [0.5, 59], [0.25, 29], [0.75, 89], [0.01, 1], [0.99, 117], [0.1, 11],
                 [-0.5, 0], [-100, 0], [1.5, 119], [2, 119], [100, 119], [0.0, 0], [1.0, 119]]
for c: tabTeinte
    verifie(cuveFonctions.teinteNiveau(c[0]) == c[1], "taux " + str(c[0]) + " -> teinte " + str(c[1]))
end
var ko = []
for tc: 0 .. 100
    var attendu = (119 * tc) / 100                    # entiers purs
    var obs = cuveFonctions.teinteNiveau(tc / 100.00)
    if obs != attendu    ko.push([tc, obs, attendu])    end
end
verifie(size(ko) == 0, "balayage des 101 taux entiers en % : teinte = 119 * % / 100 (entiers)" + (size(ko) > 0 ? " premier ecart " + str(ko[0]) : ""))
temoin("teinteNiveau(0.5) n'est PAS 60", cuveFonctions.teinteNiveau(0.5) == 60)

# ================================================================================================
print("3. couleurTeinte : teinte 0..119 + saturation -> 'RRGGBB'")
# Attendu a la main (entiers) : t < 60 -> R = 255, G = mini + (255 - mini) * t / 60 ; t >= 60 -> G = 255,
# R = mini + (255 - mini) * (119 - t) / 59 ; B = mini = 255 - sat
var tabCoul = [[0, 255, "FF0000"], [30, 255, "FF7F00"], [59, 255, "FFFA00"], [60, 255, "FFFF00"],
               [90, 255, "7DFF00"], [100, 255, "52FF00"], [119, 255, "00FF00"],
               [0, 0, "FFFFFF"], [119, 0, "FFFFFF"], [60, 0, "FFFFFF"],
               [0, 128, "FF7F7F"], [119, 128, "7FFF7F"]]
for c: tabCoul
    verifie(cuveFonctions.couleurTeinte(c[0], c[1]) == c[2], "teinte " + str(c[0]) + " sat " + str(c[1]) + " -> " + c[2])
end
var mauvais = []
for sat: [255, 128, 40]
    var mini = 255 - sat
    var rPrec = 256   var gPrec = -1
    for t: 0 .. 119
        var s = cuveFonctions.couleurTeinte(t, sat)
        var r = hex2(s[0 .. 1])   var g = hex2(s[2 .. 3])   var b = hex2(s[4 .. 5])
        var r0 = (t < 60 ? 255 : mini + ((255 - mini) * (119 - t)) / 59)
        var g0 = (t < 60 ? mini + ((255 - mini) * t) / 60 : 255)
        if size(s) != 6 || r != r0 || g != g0 || b != mini    mauvais.push([sat, t, s])    end
        if t < 60 && g < gPrec    mauvais.push(["g decroit", sat, t])    end
        if t >= 60 && r > rPrec   mauvais.push(["r croit", sat, t])    end
        if t < 60    gPrec = g    else    rPrec = r    end
    end
end
verifie(size(mauvais) == 0, "balayage 3 saturations x 120 teintes : formule entiere, 6 caracteres, rouge->jaune->vert monotone" + (size(mauvais) > 0 ? " premier ecart " + str(mauvais[0]) : ""))
temoin("teinte 0 sat 255 n'est PAS 00FF00", cuveFonctions.couleurTeinte(0, 255) == "00FF00")

# ================================================================================================
print("4. Capteur de niveau, ruban : lecture du persist de la carte")
remetNormal()
verifie(cuveFonctions.capteurNiveau() != nil && cuveFonctions.capteurNiveau()["id"] == 1, "capteurNiveau : analogique1 actif")
ANA0["activation"] = "OFF"
verifie(cuveFonctions.capteurNiveau() == nil, "capteurNiveau nil si analogique1 desactive")
remetNormal()
verifie(cuveFonctions.relaisRuban() != nil, "relaisRuban : relai1 ON de type 1376 (WS2812)")
CUVE["environnement"]["relais"]["relai1"]["type"] = 1
verifie(cuveFonctions.relaisRuban() == nil, "relaisRuban nil si le relai n'est pas un WS2812")
remetNormal()
CUVE["environnement"]["relais"]["relai1"]["activation"] = "OFF"
verifie(cuveFonctions.relaisRuban() == nil, "relaisRuban nil si relai1 OFF")
remetNormal()
verifie(cuveFonctions.rubanGere() && cuveFonctions.ledsActif(), "rubanGere et ledsActif : drivers.leds ON et ruban ON")
drivers["leds"]["environnement"]["leds"]["ruban"]["activation"] = "OFF"
verifie(!cuveFonctions.rubanGere() && cuveFonctions.ledsActif(), "ruban OFF mais ledRGB ON : ledsActif seul")
drivers["leds"]["environnement"]["leds"]["ledRGB"]["activation"] = "OFF"
verifie(!cuveFonctions.rubanGere() && !cuveFonctions.ledsActif(), "ruban et ledRGB OFF : ni l'un ni l'autre")
remetNormal()
drivers["leds"]["activation"] = "OFF"
verifie(!cuveFonctions.rubanGere() && !cuveFonctions.ledsActif(), "driver leds OFF : ni l'un ni l'autre")

# ================================================================================================
print("5. Chaine capteur -> mV -> hauteur -> taux -> volume -> teinte (geometrie du persist : " + str(HAUT) + "x" + str(LARG) + "x" + str(LONG) + " cm, " + str(CONV) + " mV/cm)")
remetNormal()
releve(0)
verifie(mesures()["valeursAnalogiques"]["valeurCapteurHauteur"] == 0 && mesures()["niveauCuve"]["hauteurEau"] == 0, "cuve VIDE : 0 mV, 0 cm")
verifie(mesures()["niveauCuve"]["tauxRemplissage"] == 0 && mesures()["niveauCuve"]["volume"] == 0, "cuve VIDE : taux 0, volume 0 L")
verifie(derniereTeinte() == 0, "cuve VIDE : teinte 0 (rouge) donnee a ledsFonctions (ruban gere)")
# Pleine : hauteur de la cuve en mV = HAUT * CONV (3410 mV) ; raw 18200 -> 3412 mV -> 110 cm
remetNormal()
releve(18200)
var mvPleine = mesures()["valeursAnalogiques"]["valeurCapteurHauteur"]
verifie(proche(mvPleine, 18200 * VMAX / 32767.0, 1.0), "cuve PLEINE : 18200 -> " + str(mvPleine) + " mV (~3412,5)")
verifie(mesures()["niveauCuve"]["hauteurEau"] == HAUT, "cuve PLEINE : hauteur " + str(HAUT) + " cm")
verifie(mesures()["niveauCuve"]["tauxRemplissage"] == 1.0, "cuve PLEINE : taux 1.0")
verifie(mesures()["niveauCuve"]["volume"] == (HAUT * LARG * LONG) / 1000, "cuve PLEINE : volume " + str((HAUT * LARG * LONG) / 1000) + " L (h x l x L / 1000)")
verifie(derniereTeinte() == 119, "cuve PLEINE : teinte 119 (vert)")
# A moitie
remetNormal()
releve(9100)
var mvMoitie = mesures()["valeursAnalogiques"]["valeurCapteurHauteur"]
var hMoitie = (mvMoitie - mvMoitie % CONV) / CONV
verifie(proche(mvMoitie, 9100 * VMAX / 32767.0, 1.0), "a moitie : 9100 -> " + str(mvMoitie) + " mV (~1706)")
verifie(mesures()["niveauCuve"]["hauteurEau"] == hMoitie && hMoitie == 55, "a moitie : hauteur = mV / " + str(CONV) + " tronque = 55 cm")
verifie(mesures()["niveauCuve"]["tauxRemplissage"] == 0.5, "a moitie : taux 0.5")
verifie(mesures()["niveauCuve"]["volume"] == (HAUT * LARG * LONG) / 2000, "a moitie : volume " + str((HAUT * LARG * LONG) / 2000) + " L")
verifie(derniereTeinte() == 59, "a moitie : teinte 59 (int(119 x 0.5))")
# Balayage de toute la plage du convertisseur (hauteur au-dela de la cuve comprise : le calcul est le meme)
remetNormal()
var ecarts = []
var maxTaux = 0
for raw: 0 .. 32767
    if raw % 193 != 0 && raw != 32767    continue    end
    releve(raw)
    var mv = mesures()["valeursAnalogiques"]["valeurCapteurHauteur"]
    var h = (mv - mv % CONV) / CONV                                  # hauteur entiere en cm
    var tc = (h * 100) / HAUT                                         # taux en %, entiers purs
    var vol = ((HAUT * LARG * LONG / 100) * tc) / 1000                # litres, entiers purs (HAUT x l x L divisible par 100 ici)
    var teinte = (119 * tc) / 100
    if teinte > 119    teinte = 119    end
    var m = mesures()["niveauCuve"]
    var obs = [mv, m["hauteurEau"], int(m["tauxRemplissage"] * 100 + 0.5), m["volume"], derniereTeinte()]
    if !proche(mv, raw * VMAX / 32767.0, 1.0) || m["hauteurEau"] != h || obs[2] != tc || m["volume"] != vol || obs[4] != teinte
        ecarts.push([raw, obs, [h, tc, vol, teinte]])
    end
    if tc > maxTaux    maxTaux = tc    end
end
verifie(size(ecarts) == 0, "balayage 171 releves sur 0..32767 : mV, hauteur, taux, volume, teinte = formules entieres independantes" + (size(ecarts) > 0 ? " premier ecart " + str(ecarts[0]) : ""))
# Temoin : le meme balayage compare a un volume FAUX (+1 L) doit lever des ecarts
var faux = 0
for raw: [3000, 9100, 15000]
    remetNormal() releve(raw)
    var mv = mesures()["valeursAnalogiques"]["valeurCapteurHauteur"]
    var h = (mv - mv % CONV) / CONV
    var vol = (((HAUT * LARG * LONG / 100) * ((h * 100) / HAUT)) / 1000) + 1
    if mesures()["niveauCuve"]["volume"] != vol    faux += 1    end
end
temoin("un volume attendu +1 L serait detecte (3 releves sur 3 en ecart)", faux != 3)

# ================================================================================================
print("6. Valeurs hors bornes du capteur")
remetNormal()
releve(32767)
var mvMax = mesures()["valeursAnalogiques"]["valeurCapteurHauteur"]
verifie(mvMax == VMAX, "raw 32767 : pleine echelle " + str(VMAX) + " mV")
verifie(derniereTeinte() == 119, "au-dessus de la cuve : la teinte reste bornee a 119")
connu("HB", "capteur au-dessus de la hauteur de la cuve : taux <= 1 et volume <= capacite",
      mesures()["niveauCuve"]["tauxRemplissage"] <= 1.0 && mesures()["niveauCuve"]["volume"] <= (HAUT * LARG * LONG) / 1000,
      "taux " + str(mesures()["niveauCuve"]["tauxRemplissage"]) + ", volume " + str(mesures()["niveauCuve"]["volume"]) + " L (capacite " + str((HAUT * LARG * LONG) / 1000) + " L) - cuveFonctions.be:571-574")
remetNormal()
releve(40000)
verifie(mesures()["valeursAnalogiques"]["valeurCapteurHauteur"] == VMAX, "raw 40000 (> 32767) : sature a la pleine echelle")
remetNormal()
releve(-3)
connu("N1", "raw -3 (bruit de l'ADS1115 a 0 V) : 0 mV et 0 cm, comme cuve vide",
      mesures()["valeursAnalogiques"]["valeurCapteurHauteur"] == 0 && mesures()["niveauCuve"]["hauteurEau"] == 0,
      str(mesures()["valeursAnalogiques"]["valeurCapteurHauteur"]) + " mV, " + str(mesures()["niveauCuve"]["hauteurEau"]) + " cm (scale_int : support_float.ino:466 -> :392, num reconverti en uint16) - le garde 'valeur < 0' de cuveFonctions.be:554 est du code mort")
print("  (N1 repose sur le bouchon porte du C : a confirmer sur carte avec un releve brut negatif)")

# ================================================================================================
print("7. Valeurs par defaut et defauts de troncature (hauteur absente : 100 cm ; voltageMax 32767 + 1 mV/cm : raw = cm)")
remet(32767, 1, nil, nil, nil)
releve(50)
verifie(mesures()["niveauCuve"]["hauteurEau"] == 50 && mesures()["niveauCuve"]["tauxRemplissage"] == 0.5, "dimensions absentes : 100 cm par defaut, 50 cm -> 0.5")
verifie(mesures()["niveauCuve"]["volume"] == 500, "dimensions absentes : 100x100x100 = 1000 L, a 50 % : 500 L")
remet(32767, 1, nil, nil, nil)
releve(53)
connu("T1", "hauteur 100 cm, eau a 53 cm : taux 0.53", int(mesures()["niveauCuve"]["tauxRemplissage"] * 100 + 0.5) == 53,
      "taux " + str(mesures()["niveauCuve"]["tauxRemplissage"]) + " (cuveFonctions.be:571 : int(h / real(H) * 100) en flottant)")
remet(32767, 1, nil, nil, nil)
releve(59)
connu("T1", "hauteur 100 cm, eau a 59 cm : taux 0.59", int(mesures()["niveauCuve"]["tauxRemplissage"] * 100 + 0.5) == 59,
      "taux " + str(mesures()["niveauCuve"]["tauxRemplissage"]))
for pc: [13, 26, 52]
    remet(32767, 1, nil, nil, nil)
    releve(pc)
    connu("V1", "cuve 100x100x100 a " + str(pc) + " % : volume " + str(pc * 10) + " L", mesures()["niveauCuve"]["volume"] == pc * 10,
          "volume " + str(mesures()["niveauCuve"]["volume"]) + " L (cuveFonctions.be:574 : int(h x l x L x taux / 1000) en flottant)")
end
# Une geometrie differente ne doit pas changer la logique (200 x 100 x 100, 2 mV/cm)
remet(32767, 2, 200, 100, 100)
releve(200)
verifie(mesures()["niveauCuve"]["hauteurEau"] == 100 && mesures()["niveauCuve"]["tauxRemplissage"] == 0.5 && mesures()["niveauCuve"]["volume"] == 1000, "cuve 200x100x100, 2 mV/cm, 200 mV : 100 cm, 0.5, 1000 L")

# ================================================================================================
print("8. Valeur inchangee, changement de dimensions, ADS1115 absent")
remetNormal()
releve(9100)
var v1 = mesures()["niveauCuve"]["volume"]
journal.clear()
cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", "")        # meme valeur memorisee
verifie(mesures()["niveauCuve"]["volume"] == v1, "meme lecture : meme volume")
CUVE["dimensions"]["hauteur"] = HAUT * 2
capteurs(9100)                                                              # valeur memorisee inchangee
cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", "")
verifie(mesures()["niveauCuve"]["tauxRemplissage"] == 0.25, "hauteur de cuve doublee, lecture inchangee : le taux est recalcule (0.25)")
remetNormal()
controleGeneral.capteurs = {}
var av = mesures()["niveauCuve"]["volume"]
cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", "")
verifie(mesures()["niveauCuve"]["volume"] == av && size(modbusFonctions.notes) == 0, "ADS1115 absent des capteurs : rien n'est modifie, aucune mesure notee")
verifie(size(journal) > 0 && journal[size(journal) - 1][1] == "CUVE_GESTION_CAPTEURS: pas de mesure ADS1115 dans les capteurs", "ADS1115 absent : une ligne de debug, pas d'exception")
controleGeneral.capteurs = {"ADS1115": {"A0": 100, "A1": 0}}                 # lecture incomplete (2 voies)
cuveFonctions.changementEtatCapteur("", "ADS1115", "", "cuve", "")
verifie(size(modbusFonctions.notes) == 0, "lecture ADS1115 a 2 voies seulement (size != 4) : ignoree")

# ================================================================================================
print("9. Fraicheur de la mesure (sentinelle ModBus) et validite du pilote")
remetNormal()
releve(0)
verifie(modbusFonctions.notes == [ADRESSE], "lecture 0 : c'est une mesure, noteMesure(" + str(ADRESSE) + ") appele (presence de la cle, pas sa valeur)")
remetNormal()
global.i2c_ads1115 = nil
releve(5000)
verifie(modbusFonctions.notes == [ADRESSE], "pilote i2c_ads1115 absent : lecture acceptee")
class FauxAds : Driver
    var valide, vues
    def init(v) self.valide = v self.vues = [] end
    def mesureValide(cle, mV, valeurs) self.vues.push([cle, mV]) return self.valide end
end
remetNormal()
var ads = FauxAds(false)
global.i2c_ads1115 = ads
releve(5000)
verifie(size(modbusFonctions.notes) == 0, "pilote : mesureValide = false -> noteMesure NON appele")
verifie(size(ads.vues) == 1 && ads.vues[0][0] == "A0" && proche(ads.vues[0][1], 5000 * VMAX / 32767.0, 1.0), "mesureValide recoit ('A0', mV de la voie)")
verifie(mesures()["niveauCuve"]["hauteurEau"] > 0, "lecture jugee invalide : le niveau est tout de meme calcule (comportement actuel)")
remetNormal()
global.i2c_ads1115 = FauxAds(true)
releve(5000)
verifie(modbusFonctions.notes == [ADRESSE], "pilote : mesureValide = true -> noteMesure appele")
global.i2c_ads1115 = nil
remetNormal()
verifie(cuveFonctions.niveauEnErreur() == false && modbusFonctions.demandes == [ADRESSE], "niveauEnErreur : mesure fraiche -> pas d'erreur, adresse " + str(ADRESSE) + " interrogee")
modbusFonctions.fraiche = false
verifie(cuveFonctions.niveauEnErreur() == true, "niveauEnErreur : mesure perimee -> erreur")
ANA0["activation"] = "OFF"
verifie(cuveFonctions.niveauEnErreur() == false, "niveauEnErreur : capteur desactive -> jamais en erreur")

# ================================================================================================
print("10. Couleur du ruban : appliqueCouleurNiveau")
remetNormal()
mesures()["niveauCuve"]["tauxRemplissage"] = 0.5
cuveFonctions.appliqueCouleurNiveau()
verifie(ledsFonctions.teintes == [59] && size(light.sets) == 0, "ruban gere par ledsFonctions : teinte 59 donnee a ledsFonctions, light non touche")
remetNormal()
drivers["leds"]["environnement"]["leds"]["ruban"]["activation"] = "OFF"
mesures()["niveauCuve"]["tauxRemplissage"] = 0.25
cuveFonctions.appliqueCouleurNiveau()
verifie(size(light.sets) == 1 && light.sets[0].find("hue") == 29 && size(light.sets[0]) == 1 && size(ledsFonctions.teintes) == 0, "ruban non gere : light.set({'hue': 29}) direct, sans 'power'")
remetNormal()
CUVE["environnement"]["relais"]["relai1"]["activation"] = "OFF"
cuveFonctions.appliqueCouleurNiveau()
verifie(size(light.sets) == 0 && size(ledsFonctions.teintes) == 0, "relai du ruban inactif : rien n'est pose")
remetNormal()
mesures()["niveauCuve"]["tauxRemplissage"] = 7
cuveFonctions.appliqueCouleurNiveau()
verifie(ledsFonctions.teintes == [119], "taux 7 (absurde) : teinte bornee a 119")

# ================================================================================================
print("11. majTemoinErreur : transitions de l'erreur de mesure, signalement a ledsFonctions")
remetNormal()
cuveFonctions.majTemoinErreur()
verifie(cuveFonctions.enErreur == false && ledsFonctions.erreurs == [["cuve", false]], "mesure fraiche : pas d'erreur, ledsFonctions informe (cuve, false)")
verifie(size(ledsFonctions.retours) == 1 && cuveFonctions.retourAutoEnregistre, "fonction de retour en AUTO enregistree au 1er passage")
cuveFonctions.majTemoinErreur()
verifie(size(ledsFonctions.retours) == 1, "... et une seule fois")
journal.clear()
modbusFonctions.fraiche = false
cuveFonctions.majTemoinErreur()
verifie(cuveFonctions.enErreur == true && ledsFonctions.erreurs[size(ledsFonctions.erreurs) - 1] == ["cuve", true], "passage en erreur : enErreur, ledsFonctions informe (cuve, true)")
verifie(size(journal) == 1 && journal[0][0] == LOG_LEVEL_ERREUR && string.find(journal[0][1], "CUVE_ERREUR_MESURE") == 0 && journal[0][2] == "cuve", "une ligne ERREUR CUVE_ERREUR_MESURE sur la cible cuve")
cuveFonctions.majTemoinErreur()
verifie(size(journal) == 1, "erreur qui dure : pas de nouvelle ligne de log")
modbusFonctions.fraiche = true
cuveFonctions.majTemoinErreur()
verifie(cuveFonctions.enErreur == false && size(journal) == 2 && journal[1][0] == LOG_LEVEL_INFO, "retour de la mesure : ligne INFO, enErreur retombe")
remetNormal()
drivers["leds"]["activation"] = "OFF"
cuveFonctions.majTemoinErreur()
verifie(size(ledsFonctions.erreurs) == 0, "ledsFonctions inactif : l'erreur ne lui est pas signalee")

# ================================================================================================
print("12. Commandes ReglageCuve / ReglageAna : aide, dimensions, reponse")
var liste = cuveFonctions.aideReglageCuve(nil)
verifie(size(liste) == 4 && liste[0][0] == "etalonnageCapteur" && size(liste[1]) == 3, "aideReglageCuve(nil) : 4 commandes [nom, syntaxe, resume]")
verifie(cuveFonctions.aideReglageCuve("hauteurcuve") != nil && cuveFonctions.aideReglageCuve("LARGEURCUVE") != nil && cuveFonctions.aideReglageCuve("zzz") == nil, "aide par sujet : insensible a la casse, nil si inconnu")
verifie(size(cuveFonctions.aideReglageAna(nil)) == 5 && cuveFonctions.aideReglageAna("voltagemax") != nil && cuveFonctions.aideReglageAna("zzz") == nil, "aideReglageAna : 5 commandes, sujet voltageMax, inconnu -> nil")
remetNormal()
persist.nb_save = 0
tasmota.reponses = []
cuveFonctions.reglageCuve("ReglageCuve", 0, "hauteurCuve 120", nil)
verifie(CUVE["dimensions"]["hauteur"] == 120 && persist.nb_save == 1, "hauteurCuve 120 : memorisee (int) et sauvee")
cuveFonctions.reglageCuve("ReglageCuve", 0, "largeurCuve 200", nil)
cuveFonctions.reglageCuve("ReglageCuve", 0, "longueurCuve 300", nil)
verifie(CUVE["dimensions"]["largeur"] == 200 && CUVE["dimensions"]["longueur"] == 300, "largeurCuve et longueurCuve memorisees")
verifie(tasmota.reponses[size(tasmota.reponses) - 1] == json.dump("ReglageCuve: reglage=OFF, largeurCuve=200cm, longueurCuve=300cm, hauteurCuve=120cm"), "reponse : rappelle reglage et les 3 dimensions")
cuveFonctions.reglageCuve("ReglageCuve", 0, "hauteurCuve 12.7", nil)
verifie(CUVE["dimensions"]["hauteur"] == 12, "hauteurCuve 12.7 : partie entiere retenue (12)")
cuveFonctions.reglageCuve("ReglageCuve", 0, "hauteurCuve", nil)
verifie(CUVE["dimensions"]["hauteur"] == 12, "hauteurCuve sans parametre : ignore")
remetNormal()
cuveFonctions.reglageCuve("ReglageCuve", 0, "hauteurCuve abc", nil)
connu("D3", "hauteurCuve abc : ignore, la hauteur reste " + str(HAUT), CUVE["dimensions"]["hauteur"] == HAUT,
      "hauteur = " + str(CUVE["dimensions"]["hauteur"]) + " (int('abc') = 0 en Berry ; cuveFonctions.be:230)")
remetNormal()
cuveFonctions.reglageCuve("ReglageCuve", 0, "hauteurCuve 0", nil)
var leve = false
try releve(9100) except .. as e, m leve = true end
connu("D3b", "hauteur de cuve 0 memorisee : un releve ne leve pas d'exception", !leve && CUVE["dimensions"]["hauteur"] > 0,
      "divzero_error a chaque releve (cuveFonctions.be:571, real(hauteur) = 0)")
remetNormal()
tasmota.crons = []   tasmota.timers = []
cuveFonctions.reglageCuve("ReglageCuve", 0, "etalonnageCapteur 1", nil)
verifie(CUVE["reglage"] == "ON" && tasmota.crons == [["remove", "majNiveauCuve"], ["*/5 * * * * *", "majNiveauCuve"]] && tasmota.timers == [600000], "etalonnage 1 -> ON : cron toutes les 5 s, retour a la cadence normale par timer de 10 min")
tasmota.crons = []
cuveFonctions.reglageCuve("ReglageCuve", 0, "etalonnageCapteur OFF", nil)
verifie(CUVE["reglage"] == "OFF" && tasmota.crons == [["remove", "majNiveauCuve"], ["*/60 * * * * *", "majNiveauCuve"]], "etalonnage OFF : cadence normale tout de suite")
remetNormal()
cuveFonctions.reglageAna("ReglageAna", 0, "voltageMax 3.3", nil)
verifie(proche(CUVE["environnement"]["analogiques"]["voltageMax"], 3.3, 0.001), "voltageMax 3.3 memorise (reel)")
cuveFonctions.reglageAna("ReglageAna", 0, "voltageMax", nil)
verifie(proche(CUVE["environnement"]["analogiques"]["voltageMax"], 3.3, 0.001), "voltageMax sans parametre : ignore")
verifie(string.find(tasmota.reponses[size(tasmota.reponses) - 1], "voltage Max=3.30V") >= 0, "reponse ReglageAna : 'voltage Max=3.30V'")

# ================================================================================================
print("13. controleCuve.be : page web, JSON, filtre de l'historique, DS18B20")
var ctrl = nil
try
    remetNormal()
    var src = lis(SOURCES_CUVE + "/controleCuve.be")
    ctrl = compile(src + "\nreturn controleCuve\n")()
except .. as e, m
    print("  ECHEC chargement de controleCuve.be : " + str(e) + " " + str(m))
    echecs += 1
end
if ctrl != nil
    verifie(isinstance(ctrl, Driver) && ctrl.flagINIT == 1, "controleCuve instancie (init termine, flagINIT = 1)")
    verifie(tasmota.cmds.contains("ReglageCuve") && tasmota.cmds.contains("ReglageAna"), "commandes ReglageCuve et ReglageAna enregistrees")
    # filtreHistorique
    remetNormal()
    var chemins = ["sensorsCuve.niveauCuve.volume", "sensorsCuve.niveauCuve.hauteurEau", "sensorsCuve.valeursAnalogiques.valeurCapteurHauteur", "autre.mesure"]
    var vals = [100, 50, 1700, 12]
    ctrl.filtreHistorique(chemins, vals)
    verifie(vals == [100, 50, 1700, 12], "filtreHistorique, mesure fraiche : rien n'est touche")
    modbusFonctions.fraiche = false
    vals = [100, 50, 1700, 12]
    ctrl.filtreHistorique(chemins, vals)
    verifie(vals[0] == nil && vals[1] == nil && vals[2] == 1700 && vals[3] == 12, "filtreHistorique, erreur : series niveauCuve.* a nil, les autres intactes")
    # DS18B20
    controleGeneral.capteurs = {"DS18B20-1": {"Temperature": 12.34}}
    verifie(ctrl.lectureDS18B20({"id": 1})["Temperature"] == 12.34, "lectureDS18B20 : sonde 'DS18B20-1' (alias du framework)")
    controleGeneral.capteurs = {"DS18B20": {"Temperature": 7.5}}
    verifie(ctrl.lectureDS18B20({"id": 1})["Temperature"] == 7.5, "lectureDS18B20 : repli sur 'DS18B20' sans alias")
    controleGeneral.capteurs = {"DS18B20-1": 5}
    verifie(ctrl.lectureDS18B20({"id": 1}) == nil, "lectureDS18B20 : valeur non-map ignoree (nil)")
    controleGeneral.capteurs = {}
    verifie(ctrl.lectureDS18B20({"id": 1}) == nil, "lectureDS18B20 : sonde absente -> nil")
    # json_append
    remetNormal()
    releve(9100)
    tasmota.ajouts = []
    ctrl.json_append()
    var ja = json.load("{" + tasmota.ajouts[0][1 ..] + "}")
    verifie(ja != nil && ja["sensorsCuve"]["niveauCuve"]["volume"] == mesures()["niveauCuve"]["volume"] && ja["sensorsCuve"]["niveauCuve"]["hauteurEau"] == 55, "json_append : JSON valide, volume et hauteur de la mesure")
    # web_sensor : mesure fraiche, a moitie
    remetNormal()
    releve(9100)
    controleGeneral.capteurs = {"DS18B20-1": {"Temperature": 12.34}}
    gestionFileFolder.envois = []
    ctrl.web_sensor()
    var niv = gestionFileFolder.envois[0][1]
    verifie(gestionFileFolder.envois[0][0] == "/sd/html/webSensorNiveauCuve.html", "web_sensor : gabarit du niveau de cuve")
    verifie(string.find(niv["sensorsCuve->niveauCuve->tauxRemplissage"], "50%") == 0 && niv["sensorsCuve->niveauCuve->volume"] == str((HAUT * LARG * LONG) / 2000) + "L", "web_sensor : taux '50%' et volume " + str((HAUT * LARG * LONG) / 2000) + "L")
    verifie(niv["sensorsCuve->niveauCuve->hauteurEau"] == "55cm" && string.find(niv["sensorsCuve->valeursAnalogiques->valeurCapteurHauteur"], "mV") > 0, "web_sensor : hauteur '55cm', tension en mV")
    verifie(niv["colorWs2812"] == cuveFonctions.couleurTeinte(59, 255) && niv["colorWs2812"] == "FFFA00" && niv["classeErreur"] == "", "web_sensor : couleur de l'encadre = teinte 59 a saturation 255 (FFFA00), pas de classe d'erreur")
    verifie(size(gestionFileFolder.envois) == 2 && string.find(gestionFileFolder.envois[1][1]["sensors->DS18B20->Temperature"], "12.3") == 0, "web_sensor : thermometre 12.34 -> '12.3' (une decimale tronquee)")
    # web_sensor : sonde absente
    controleGeneral.capteurs = {}
    gestionFileFolder.envois = []
    ctrl.web_sensor()
    verifie(string.find(gestionFileFolder.envois[1][1]["sensors->DS18B20->Temperature"], "-,--") == 0, "web_sensor : sonde absente -> '-,--'")
    # web_sensor : erreur de mesure
    modbusFonctions.fraiche = false
    gestionFileFolder.envois = []
    ctrl.web_sensor()
    niv = gestionFileFolder.envois[0][1]
    verifie(niv["colorWs2812"] == "FF0000" && niv["classeErreur"] == "erreurCapteur", "web_sensor, erreur de mesure : encadre rouge + classe 'erreurCapteur'")
    verifie(niv["sensorsCuve->niveauCuve->hauteurEau"] == "-,--cm" && niv["sensorsCuve->niveauCuve->volume"] == "-,--L" && niv["sensorsCuve->niveauCuve->tauxRemplissage"] == "-,--%", "web_sensor, erreur : valeurs '-,--' (la derniere valeur connue ne passe pas pour une mesure)")
    # web_sensor : saturation du ruban prise sur light (ruban eteint ou blanc)
    modbusFonctions.fraiche = true
    light.etat["sat"] = 0
    gestionFileFolder.envois = []
    ctrl.web_sensor()
    verifie(gestionFileFolder.envois[0][1]["colorWs2812"] == "FFFFFF", "web_sensor : ruban sature a 0 (blanc de la palette) -> encadre FFFFFF, couleur relue sur light")
end

print("")
print("Controles : " + str(nbControles) + ", echecs : " + str(echecs))
print(echecs == 0 ? "BANC_CUVE: OK" : "BANC_CUVE: ECHEC (" + str(echecs) + ")")
