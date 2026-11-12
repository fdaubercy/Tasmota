# Banc de data/fs/energieFonctions.be : notes horaires, jour, mois, coupure, compteur incoherent, prix, heure d'ete et
# d'hiver, purge, courbe, calibrage. Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_energie.be <dossier_vide> [fichier_module]
# fichier_module : (temoin) une copie modifiee du module. Derniere ligne lue par l'enveloppe : BANC_ENERGIE: OK|ECHEC
# Faux firmware ici ; les fichiers de l'historique sont de vrais fichiers dans <dossier_vide>.
import global
import sys
import string
import json
import os

var SORTIE = global._argv[1]
var SOURCE = size(global._argv) > 2 ? global._argv[2] : "data/fs/energieFonctions.be"

def lis(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end
def ecris(chemin, texte)
    var f = open(chemin, "w")
    f.write(texte)
    f.close()
end

# Bouchons, ecrits dans <dossier_vide>/modules : path (vrais fichiers), webserver (reponse memorisee)
os.mkdir(SORTIE + "/modules")
ecris(SORTIE + "/modules/path.be", "import os\nvar path = module('path')\n"
    "path.exists = def (c) return os.path.exists(c) end\n"
    "path.mkdir = def (c) return os.mkdir(c) end\n"
    "path.remove = def (c) return os.remove(c) end\n"
    "path.listdir = def (d) return os.listdir(d) end\n"
    "path.rename = def (a, b) if os.path.exists(b) return false end var f = open(a, 'r') var t = f.read() f.close() f = open(b, 'w') f.write(t) f.close() os.remove(a) return true end\n"
    "return path\n")
ecris(SORTIE + "/modules/webserver.be", "import global\nvar w = module('webserver')\n"
    "w.BUTTON_MAIN = 0\n"
    "w.BUTTON_CONFIGURATION = 1\n"
    "w.check_privileged_access = def () return global.ACCES end\n"
    "w.has_arg = def (a) return global.ARGS.contains(a) end\n"
    "w.arg = def (a) return global.ARGS[a] end\n"
    "w.content_open = def (c, m) global.CODE = c global.REPONSE = '' end\n"
    "w.content_send = def (t) global.REPONSE += t end\n"
    "w.content_close = def () end\n"
    "w.content_start = def (t) global.REPONSE = '' end\n"
    "w.content_send_style = def () end\n"
    "w.content_button = def (b) end\n"
    "w.content_stop = def () end\n"
    "return w\n")
ecris(SORTIE + "/modules/gestionFileFolder.be", "import global\nvar g = module('gestionFileFolder')\n"
    "g.readFileByLineAndContentSend = def (c) global.REPONSE += '[' + c + ']' end\nreturn g\n")
# Solidifie, le module n'est pas un global : une fonction qui le cite sans l'importer doit echouer ici comme sur la carte
ecris(SORTIE + "/modules/energieFonctions.be", string.replace(lis(SOURCE),
    'var energieFonctions = module("energieFonctions")', 'import global global.energieFonctions = module("energieFonctions")'))
sys.path().push(SORTIE + "/modules")

# ---- Faux firmware --------------------------------------------------------------------------------------------
global.JOURNAL = []
global.ACCES = true
global.ARGS = {}
global.CODE = 0
global.REPONSE = ""
global.LOG_LEVEL_ERREUR = 1
global.LOG_LEVEL_INFO = 2
global.LOG_LEVEL_DEBUG = 3
global.LOG_LEVEL_DEBUG_PLUS = 4
global.boolMute = true
global.diverses = {}
var fauxLog = module("logFonctions")
fauxLog.log = def (m, n, c) global.JOURNAL.push([m, n]) end
global.logFonctions = fauxLog

global.LIBRE = 300
global.REGLAGES = {}
global.CMDS = []
global.CAPTEURS = "{}"
global.RTC = {"utc": 0, "local": 0}
def jourCivil(jours)      # jours depuis 1970 -> [annee, mois, jour]
    var z = jours + 719468
    var era = z / 146097
    var doe = z - era * 146097
    var yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365
    var doy = doe - (365 * yoe + yoe / 4 - yoe / 100)
    var mp = (5 * doy + 2) / 153
    var m = mp < 10 ? mp + 3 : mp - 9
    return [yoe + era * 400 + (m <= 2 ? 1 : 0), m, doy - (153 * mp + 2) / 5 + 1]
end
var tasmota = module("tasmota")
tasmota.yield = def () end
tasmota.rtc = def () return global.RTC end
tasmota.read_sensors = def () return global.CAPTEURS end
tasmota.time_dump = def (e)
    var c = jourCivil(e / 86400)
    return {"year": c[0], "month": c[1], "day": c[2], "hour": (e % 86400) / 3600, "min": (e % 3600) / 60, "sec": e % 60, "epoch": e}
end
tasmota.cmd = def (c, muet)
    global.CMDS.push(c)
    if (c == "UfsFree")    return {"UfsFree": global.LIBRE}    end
    var morceaux = string.split(c, " ")
    if (size(morceaux) == 2)    global.REGLAGES[morceaux[0]] = int(morceaux[1])    end
    return {morceaux[0]: global.REGLAGES.find(morceaux[0])}
end
global.tasmota = tasmota

global.energieFonctions = module("declaration")      # le nom doit exister a la compilation du fichier
import energieFonctions as E
global.energieFonctions = nil                         # une fonction qui le cite sans import echoue, comme sur la carte
E.DOSSIER = SORTIE + "/energie"
var D = E.DOSSIER

var echecs = 0
def verifie(nom, attendu, obtenu)
    if (str(attendu) == str(obtenu))
        print("  OK    " + nom)
    else
        echecs += 1
        print("  ECHEC " + nom + " : attendu " + str(attendu) + ", obtenu " + str(obtenu))
    end
end
def vide()
    if (os.path.exists(D))
        for n: os.listdir(D)    os.remove(D + "/" + n)    end
    else
        os.mkdir(D)
    end
    global.JOURNAL = []
end

# Epoch d'une date (mois et jour a partir de 1) a l'heure h, sans fuseau
def epoch(a, m, j, h)
    var y = m <= 2 ? a - 1 : a
    var era = y / 400
    var yoe = y - era * 400
    var doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + j - 1
    var doe = yoe * 365 + yoe / 4 - yoe / 100 + doy
    return (era * 146097 + doe - 719468) * 86400 + h * 3600
end
def releve(kwh, local, utc)
    return E.releve({"Total": kwh}, {"utc": utc == nil ? local - 3600 : utc, "local": local})
end
def somme(l)
    var s = 0
    for v: l    s += v    end
    return s
end
var H = epoch(2026, 11, 2, 14)

print("--- Heure pleine")
vide()
releve(100.0, H)
var e = E.lisEtat()
verifie("premiere note : rien de verse", 0, somme(e["h"]))
verifie("premiere note : jour", "2026-11-02", e["j"])
verifie("premiere note : ecrite", 100000, e["w"])
releve(100.5, H + 1800)
verifie("meme heure : pas de nouvelle note", 100000, E.lisEtat()["w"])
releve(100.5, H + 3600)
e = E.lisEtat()
verifie("heure ecoulee : 500 Wh a 14 h", 500, e["h"][14])
verifie("rien a 15 h", 0, e["h"][15])
verifie("verse au jour", 500, e["d"][1])
verifie("verse au mois", [["2026-11", 500, 0]], e["a"])

print("--- Changement de jour")
vide()
var soir = epoch(2026, 11, 2, 23)
releve(10.0, soir)
releve(10.2, soir + 3600)
e = E.lisEtat()
verifie("23 h verse a la veille", 200, e["d"][1])
verifie("nouveau jour", "2026-11-03", e["j"])
verifie("heures remises a zero", 0, somme(e["h"]))

print("--- Changement de mois : archive")
vide()
soir = epoch(2026, 11, 30, 23)
releve(10.0, soir)
releve(10.3, soir + 3600)
e = E.lisEtat()
verifie("nouveau mois", "2026-12", e["m"])
verifie("jours remis a zero", 0, somme(e["d"]))
verifie("12 mois : deux entrees", [["2026-11", 300, 0], ["2026-12", 0, 0]], e["a"])
verifie("archive du mois clos", 300, E.lisJson("mois-2026-11.json")["d"][29])
for i: 1 .. 24
    E.bascule(e, tasmota.time_dump(epoch(2027 + (i - 1) / 12, ((i - 1) % 12) + 1, 1, 0)))
end
verifie("24 mois au plus", 24, size(e["a"]))

print("--- Coupure et redemarrage")
vide()
releve(50.0, H)
releve(50.1, H + 1200)           # redemarrage dans la meme heure : etat relu du fichier
verifie("redemarrage dans l'heure : note gardee", 50000, E.lisEtat()["w"])
releve(53.0, H + 5 * 3600)       # 5 h de coupure : tout porte a l'heure ecoulee quand la carte le constate
e = E.lisEtat()
verifie("coupure : a l'heure constatee", 3000, e["h"][18])
verifie("coupure : journee juste", 3000, somme(e["d"]))
vide()
var veille = epoch(2026, 11, 2, 20)
releve(50.0, veille)
releve(52.0, veille + 8 * 3600)  # coupure a cheval sur minuit : heure et jour de la case, pas de la veille
e = E.lisEtat()
verifie("coupure sur minuit : jour du constat", 2000, e["d"][2])
verifie("coupure sur minuit : heure du constat", 2000, e["h"][3])

vide()
ecris(D + "/etat.json", "pas du json")
releve(50.0, H)
verifie("etat abime : mis de cote", true, os.path.exists(D + "/etat.json.corrompu"))
verifie("etat abime : repart", 50000, E.lisEtat()["w"])
verifie("etat abime : log erreur", 1, global.JOURNAL[0][1])

print("--- Compteur incoherent")
vide()
releve(50.0, H)
releve(49.0, H + 3600)
e = E.lisEtat()
verifie("baisse : non comptee", 0, somme(e["d"]))
verifie("baisse : note repart", 49000, e["w"])
var erreurs = 0
for l: global.JOURNAL
    if (l[1] == 1)    erreurs += 1    end
end
verifie("baisse : log erreur", 1, erreurs)
releve(49.5, H + 7200)
verifie("baisse : l'heure suivante compte", 500, somme(E.lisEtat()["d"]))
vide()
releve(0.0, H)
releve(564.205, H + 3600)        # EnergyTotal retabli a la main (A8) : pas 564 kWh en une heure
e = E.lisEtat()
verifie("compteur retabli : non compte", 0, somme(e["d"]))
verifie("compteur retabli : note repart", 564205, e["w"])
releve(564.205 + 9.0, H + 7200)
verifie("9 kWh en 1 h : plausible", 9000, somme(E.lisEtat()["d"]))

print("--- Prix")
vide()
releve(10.0, H)
releve(11.0, H + 3600)
verifie("sans prix : cout nul", 0, E.lisEtat()["he"][14])
verifie("prix valide", nil, E.ajoutePrix("2026-11-02", "0,2"))
releve(12.0, H + 7200)
e = E.lisEtat()
verifie("cout au prix", 2000, e["he"][15])
verifie("passe intact", 0, e["he"][14])
verifie("prix d'une date future", nil, E.ajoutePrix("2027-01-01", "0.3"))
verifie("prix antidate", nil, E.ajoutePrix("2026-01-01", "0.1"))
verifie("liste triee", ["2026-01-01", "2026-11-02", "2027-01-01"], [E.lisJson("prix.json")[0][0], E.lisJson("prix.json")[1][0], E.lisJson("prix.json")[2][0]])
verifie("prix en vigueur", 2000, E.prixA("2026-12-31"))
verifie("prix avant le premier", 0, E.prixA("2025-12-31"))
releve(13.0, H + 3 * 3600)
e = E.lisEtat()
verifie("heure suivante : prix en vigueur, pas le futur", 2000, e["he"][16])
verifie("cout du mois", 4000, e["a"][-1][2])
verifie("meme date : remplace", nil, E.ajoutePrix("2026-11-02", "0.25"))
verifie("meme date : valeur", 2500, E.prixA("2026-12-31"))
verifie("pas de doublon", 3, size(E.lisJson("prix.json")))
for cas: [["2026-13-01", "0.2"], ["2026-02-30", "0.2"], ["2026-00-10", "0.2"], ["26-1-1", "0.2"], ["", "0.2"], ["abcd-ef-gh", "0.2"], ["2026-1a-05", "0.2"]]
    verifie("date refusee " + cas[0], "Date invalide", E.ajoutePrix(cas[0], cas[1]))
end
verifie("29 fevrier bissextile", nil, E.ajoutePrix("2028-02-29", "0.2"))
verifie("29 fevrier non bissextile", "Date invalide", E.ajoutePrix("2027-02-29", "0.2"))
for cas: ["0", "-1", "2.5", "abc", ""]
    verifie("prix refuse '" + cas + "'", "Prix invalide", E.ajoutePrix("2026-05-01", cas))
end

print("--- Tarif HC/HP")
verifie("plage a cheval sur minuit", 0xC0003F, E.masqueHC("22-6"))
verifie("deux plages, zeros, espaces", 0x01C0F8, E.masqueHC(" 03-8 , 14-17"))
verifie("fin a 24", 0xC00000, E.masqueHC("22-24"))
for cas: ["", "22", "22-", "-6", "a-b", "25-3", "3-25", "5-5", "0-24", "0-12,12-0", "22-6-8", "1.5-3"]
    verifie("plages refusees '" + cas + "'", nil, E.masqueHC(cas))
end
vide()
verifie("HC/HP valide", nil, E.ajoutePrix("2026-11-02", "0.2", "0,1", "22-6"))
verifie("entree HC/HP", ["2026-11-02", 2000, 1000, 0xC0003F], E.lisJson("prix.json")[0])
verifie("heure creuse", 1000, E.prixA("2026-11-03", 23))
verifie("derniere heure creuse", 1000, E.prixA("2026-11-03", 5))
verifie("premiere heure pleine", 2000, E.prixA("2026-11-03", 6))
verifie("HC invalide", "Prix invalide", E.ajoutePrix("2026-12-01", "0.2", "abc", "22-6"))
verifie("plages invalides", "Heures creuses invalides", E.ajoutePrix("2026-12-01", "0.2", "0.1", "x"))
verifie("refus : rien d'ecrit", 1, size(E.lisJson("prix.json")))
verifie("Base apres HC/HP", nil, E.ajoutePrix("2026-12-01", "0.3"))
verifie("Base : plus d'heures creuses", 3000, E.prixA("2026-12-02", 23))
verifie("HC/HP avant", 1000, E.prixA("2026-11-30", 23))
var hc23 = 1604358000 # 2020-11-02 23:00 UTC : seule l'heure du jour compte ici
vide()
E.ajoutePrix("2020-01-01", "0.2", "0.1", "22-6")
var etatHc = E.etatNeuf()
E.verse(etatHc, 1000, hc23)
E.verse(etatHc, 1000, hc23 - 17 * 3600)
verifie("heure creuse valorisee", 1000, etatHc["he"][23])
verifie("heure pleine valorisee", 2000, etatHc["he"][6])

print("--- Heure d'ete et d'hiver")
vide()
var ete = epoch(2027, 3, 28, 1)        # 01:00 locale, 03:00 une heure reelle plus tard
releve(10.0, ete, ete)
releve(10.4, ete + 7200, ete + 3600)
e = E.lisEtat()
verifie("ete : l'heure ecoulee reste a 1 h", 400, e["h"][1])
verifie("ete : l'heure sautee reste vide", 0, e["h"][2])
vide()
var hiver = epoch(2026, 10, 25, 2)     # 02:00 locale, l'heure 02 se repete
releve(10.0, hiver, hiver)
releve(10.3, hiver, hiver + 3600)      # 02:00 pour la seconde fois : meme heure locale, pas de note
verifie("hiver : pas de note dans l'heure repetee", 10000, E.lisEtat()["w"])
releve(10.7, hiver + 3600, hiver + 7200)
e = E.lisEtat()
verifie("hiver : les deux heures dans la meme case", 700, e["h"][2])
verifie("hiver : rien a 3 h", 0, e["h"][3])

print("--- Purge")
vide()
for m: ["2025-03", "2024-01", "2024-12", "2025-01"]
    ecris(D + "/mois-" + m + ".json", "{}")
end
ecris(D + "/prix.json", "[]")
global.LIBRE = 300
E.purge()
verifie("place suffisante : rien d'efface", 5, size(os.listdir(D)))
var libres = [10, 10, 100, 100, 100]
tasmota.cmd = def (c, muet) return {"UfsFree": size(libres) > 0 ? libres.pop(0) : 100} end
E.purge()
verifie("place manquante : le plus ancien d'abord", false, os.path.exists(D + "/mois-2024-01.json"))
verifie("place manquante : le suivant", false, os.path.exists(D + "/mois-2024-12.json"))
verifie("place revenue : on s'arrete", true, os.path.exists(D + "/mois-2025-01.json"))
verifie("les prix ne sont jamais purges", true, os.path.exists(D + "/prix.json"))
tasmota.cmd = def (c, muet) return {"UfsFree": 300} end
vide()
for i: 1 .. 12    ecris(D + string.format("/mois-2024-%02i.json", i), "{}")    end
for i: 1 .. 12    ecris(D + string.format("/mois-2025-%02i.json", i), "{}")    end
ecris(D + "/mois-2026-01.json", "{}")
E.purge()
verifie("25 archives : 24 gardees", 24, size(os.listdir(D)))
verifie("25 archives : la plus ancienne part", false, os.path.exists(D + "/mois-2024-01.json"))
tasmota.cmd = def (c, muet) return {"UfsFree": 5} end
vide()
ecris(D + "/prix.json", "[]")
E.purge()
verifie("plus rien a effacer : log erreur", 1, global.JOURNAL[-1][1])

print("--- Ecriture atomique")
tasmota.cmd = def (c, muet) return {"UfsFree": 300} end
vide()
verifie("ecriture", true, E.ecrisJson("etat.json", {"w": 1}))
verifie("aucun temporaire restant", false, os.path.exists(D + "/etat.json.tmp"))
verifie("remplacement", true, E.ecrisJson("etat.json", {"w": 2}))
verifie("relu", 2, E.lisEtat()["w"])
os.remove(D + "/etat.json")
ecris(D + "/etat.json.tmp", '{"w":3}')
verifie("arret entre les deux : temporaire repris", 3, E.lisEtat()["w"])
ecris(D + "/etat.json", "pas du json")
os.remove(D + "/etat.json.tmp")
verifie("etat illisible : nil", nil, E.lisEtat())

print("--- Courbe")
var c = E.courbeVide()
verifie("576 octets", 576, size(c))
var midi = epoch(2026, 11, 2, 12)
E.notePuissance(c, midi, 1234.4)
verifie("point a son heure", 1234, c.get(2 * E.indexCourbe(midi), 2))
E.notePuissance(c, midi + 300, -5)
verifie("negatif ramene a 0", 0, c.get(2 * E.indexCourbe(midi + 300), 2))
E.notePuissance(c, midi + 600, 70000)
verifie("trop grand : distinct du vide", 65534, c.get(2 * E.indexCourbe(midi + 600), 2))
E.notePuissance(c, midi + 900, nil)
verifie("nil : reste vide", 65535, c.get(2 * E.indexCourbe(midi + 900), 2))

print("--- Courbe copiee en flash")
vide()
var depart = epoch(2026, 11, 2, 12)
verifie("sans fichier : courbe vide", 65535, E.lisCourbe(depart).get(0, 2))
var cc = E.courbeVide()
E.notePuissance(cc, depart, 500)
E.notePuissance(cc, depart - 300, 400)
verifie("copie ecrite", true, E.sauveCourbe(cc, depart))
verifie("aucun temporaire", false, os.path.exists(D + "/courbe.bin.tmp"))
var relue = E.lisCourbe(depart)
verifie("relue : point", 500, relue.get(2 * E.indexCourbe(depart), 2))
verifie("relue : point precedent", 400, relue.get(2 * E.indexCourbe(depart - 300), 2))
E.notePuissance(cc, depart + 900, 777)      # point de la veille a l'heure ou la carte sera coupee
E.sauveCourbe(cc, depart)
relue = E.lisCourbe(depart + 1200)
verifie("coupure : points ecoules vides", 65535, relue.get(2 * E.indexCourbe(depart + 900), 2))
verifie("coupure : point d'avant garde", 500, relue.get(2 * E.indexCourbe(depart), 2))
verifie("copie de plus de 24 h : ignoree", 65535, E.lisCourbe(depart + 86400).get(2 * E.indexCourbe(depart), 2))
verifie("copie dans le futur : ignoree", 65535, E.lisCourbe(depart - 3600).get(2 * E.indexCourbe(depart), 2))
ecris(D + "/courbe.bin", "abime")
verifie("fichier abime : courbe vide", 576, size(E.lisCourbe(depart)))

print("--- Calibrage")
var defauts = {"PowerCal": 596, "VoltageCal": 15187, "CurrentCal": 251213}
var CAL = {"PowerCal": 310, "VoltageCal": 15963, "CurrentCal": 124194}
tasmota.cmd = def (c, muet)
    global.CMDS.push(c)
    var morceaux = string.split(c, " ")
    if (size(morceaux) == 2)    global.REGLAGES[morceaux[0]] = int(morceaux[1])    end
    return {morceaux[0]: global.REGLAGES.find(morceaux[0])}
end
global.diverses = {"energie": {"calibrage": CAL}}
global.REGLAGES = {"PowerCal": 596, "VoltageCal": 15187, "CurrentCal": 251213}
verifie("defauts : rejoue", true, E.verifieCalibrage())
verifie("defauts : valeurs posees", 124194, global.REGLAGES["CurrentCal"])
verifie("defauts : VoltageCal", 15963, global.REGLAGES["VoltageCal"])
global.REGLAGES = {"PowerCal": 300, "VoltageCal": 15000, "CurrentCal": 120000}
verifie("valeurs propres : intact", false, E.verifieCalibrage())
verifie("valeurs propres : non modifiees", 300, global.REGLAGES["PowerCal"])
global.REGLAGES = {"PowerCal": 596, "VoltageCal": 15187, "CurrentCal": 120000}
verifie("une seule valeur propre : intact", false, E.verifieCalibrage())
verifie("une seule valeur propre : non modifiee", 596, global.REGLAGES["PowerCal"])
global.diverses = {"energie": {"activation": "ON"}}
global.REGLAGES = {"PowerCal": 596, "VoltageCal": 15187, "CurrentCal": 251213}
verifie("cle absente : rien", false, E.verifieCalibrage())
verifie("cle absente : non modifiee", 596, global.REGLAGES["PowerCal"])
global.diverses = {}
verifie("bloc absent : rien", false, E.verifieCalibrage())
verifie("enregistrement : bloc absent = ON", true, E.enregistre())
global.diverses = {"energie": {"activation": "ON"}}
verifie("enregistrement : cle absente = ON", true, E.enregistre())
global.diverses = {"energie": {"enregistrement": "OFF"}}
verifie("enregistrement : OFF", false, E.enregistre())
global.diverses = {}

print("--- Routes")
vide()
global.RTC = {"utc": midi, "local": midi}
releve(20.0, midi - 3600)
releve(20.4, midi)
E.ajoutePrix("2026-11-01", "0.2")
var courbe = E.courbeVide()
E.notePuissance(courbe, midi, 750)
global.ACCES = false
global.REPONSE = "intact"
E.route(courbe)
verifie("acces refuse : rien d'envoye", "intact", global.REPONSE)
global.ARGS = {"jour": "2026-12-01", "prix": "0.3"}
E.enregistrePrix()
verifie("acces refuse : prix non enregistre", 1, size(E.lisJson("prix.json")))
global.ACCES = true
global.ARGS = {"f": "donnees"}
E.route(courbe)
var donnees = json.load(global.REPONSE)
ecris(SORTIE + "/donnees.json", global.REPONSE)
verifie("donnees : JSON valide", true, isinstance(donnees, map))
verifie("donnees : date de la carte", "2026-11-02", donnees["aujourdhui"])
verifie("donnees : 288 points", 288, size(donnees["courbe"]))
verifie("donnees : point le plus recent en dernier", 750, donnees["courbe"][287])
verifie("donnees : vide = null", nil, donnees["courbe"][0])
verifie("donnees : compteur illisible", nil, donnees["wCourant"])
verifie("donnees : enregistrement actif", true, donnees["enregistrement"])
global.diverses = {"energie": {"enregistrement": "OFF"}}
E.route(courbe)
verifie("donnees : enregistrement coupe", false, json.load(global.REPONSE)["enregistrement"])
global.diverses = {}
global.CAPTEURS = '{"ENERGY":{"Total":1234.567}}'
E.route(courbe)
verifie("donnees : compteur en Wh entiers", 1234567, json.load(global.REPONSE)["wCourant"])
# Autre carte que le differentiel : compteur a plusieurs voies (Total en liste) -> illisible, rien n'est compte ni ecrit
global.CAPTEURS = '{"ENERGY":{"Total":[1.5,2.5],"Power":[10,20]}}'
E.route(courbe)
verifie("plusieurs voies : compteur illisible", nil, json.load(global.REPONSE)["wCourant"])
verifie("plusieurs voies : aucune note", false, E.releve(E.mesure(), {"utc": 1762000000, "local": 1762003600}))
global.CAPTEURS = "{}"
E.route(courbe)
verifie("donnees : heure", 400, donnees["etat"]["h"][11])
verifie("donnees : prix", 2000, donnees["prix"][0][1])
vide()
E.route(courbe)
donnees = json.load(global.REPONSE)
verifie("sans historique : etat null", nil, donnees["etat"])
verifie("sans historique : prix vides", 0, size(donnees["prix"]))
global.CAPTEURS = '{"ENERGY":{"Total":1.5,"Power":123,"Current":0.6,"Factor":0.87,"Frequency":50,"Voltage":231}}'
global.ARGS = {"f": "direct"}
E.route(courbe)
var direct = json.load(global.REPONSE)
verifie("direct : puissance", 123, direct["p"])
verifie("direct : facteur", 0.87, direct["f"])
verifie("direct : pas la tension", nil, direct.find("v"))
global.CAPTEURS = '{"Time":"x"}'
E.route(courbe)
verifie("direct sans ENERGY : JSON valide", nil, json.load(global.REPONSE)["p"])
global.ARGS = {}
E.route(courbe)
verifie("page : ordre css, html, js", "[/sd/css/energie.css]", global.REPONSE[string.find(global.REPONSE, "[") .. string.find(global.REPONSE, "]")])
verifie("page : gabarit puis script", true, string.find(global.REPONSE, "energie.html") < string.find(global.REPONSE, "energie.js"))
global.ARGS = {"f": "tarifs"}
E.route(courbe)
verifie("tarifs : gabarit", true, string.find(global.REPONSE, "energieTarifs.html") >= 0 && string.find(global.REPONSE, "energieTarifs.js") >= 0)
global.ARGS = {"jour": "2026-12-05", "prix": "0.3", "hc": "0.15", "plages": "x"}
E.enregistrePrix()
verifie("POST HC/HP refuse", "Heures creuses invalides", json.load(global.REPONSE)["erreur"])
global.ARGS = {"jour": "2026-12-05", "prix": "0.3", "hc": "0.15", "plages": "22-6"}
E.enregistrePrix()
verifie("POST HC/HP accepte", 1500, E.prixA("2026-12-06", 22))
global.ARGS = {"jour": "2026-13-01", "prix": "0.3"}
E.enregistrePrix()
verifie("POST refuse : 400", 400, global.CODE)
verifie("POST refuse : message", "Date invalide", json.load(global.REPONSE)["erreur"])
global.ARGS = {"jour": "2026-12-01", "prix": "0.3"}
E.enregistrePrix()
verifie("POST accepte : 200", 200, global.CODE)
verifie("POST accepte : enregistre", 3000, E.prixA("2026-12-02"))

print(echecs == 0 ? "BANC_ENERGIE: OK" : "BANC_ENERGIE: ECHEC (" + str(echecs) + ")")
