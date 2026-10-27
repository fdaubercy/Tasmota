# Banc d'equivalence du DEMARRAGE d'une carte (2026-10-25, audit Berry P4.2 : autoexec commun).
# -----------------------------------------------------------------------------------------------------------
# Lance par son enveloppe, depuis la racine du depot (les 6 cartes maintenues, comparees a leur reference) :
#     python outils_docs/scripts_python/berry/banc_demarrage.py [--enregistre] [--carte <env>]
# ou pour une carte (imprime son instantane) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_demarrage.be --env <env> --carte <dossier> [--cenv <ini>] [sources]
#
# Execute l'autoexec.be ENTIER de la carte sur le faux firmware de banc_boot (bouchons_berry/boot/ : LittleFS en
# memoire, modules solidifies de l'env lus dans platformio_tasmota_cenv.ini, persist de la carte), puis imprime
# un INSTANTANE de ce que le demarrage a mis en place : exception, drivers, regles, commandes, crons, minuteries,
# fichiers compiles du LittleFS, globales creees, erreurs journalisees. L'enveloppe le compare a une reference
# enregistree AVANT la refonte : une refonte de l'autoexec doit rendre le meme instantane (les ecarts voulus,
# ex. differentiel et grenier remis au modele, se relisent puis s'enregistrent par --enregistre).
# Limites : celles de banc_boot (pas de bus, pas de timing, tout peripherique I2C repond) ; seul l'autoexec
# tourne (pas d'evenement System#Boot ni de seconde de driver : c'est le role de banc_boot, pour le P4).
import global
import sys
import os
import string
import json

BANC_BOOT = nil  LITTLEFS = nil  tasmota = nil  PREPARATION_BOOT = nil  OBJET_FACTICE = nil  CENV_BANC = nil

var BOUCHONS = "outils_docs/scripts_python/berry/bouchons_berry/boot"
var ENV = nil
var CARTE = nil
var SOURCES = "data/fs"
var i = 1
while i < size(global._argv)
    var a = global._argv[i]
    if a == "--env"    ENV = global._argv[i + 1]    i += 1
    elif a == "--carte"    CARTE = global._argv[i + 1]    i += 1
    elif a == "--cenv"    CENV_BANC = global._argv[i + 1]    i += 1
    else    SOURCES = a
    end
    i += 1
end
if ENV == nil || CARTE == nil    print("usage : banc_demarrage.be --env <env> --carte <dossier> [--cenv <ini>] [sources]")    return    end
var TRAVAIL = ".pio/banc_demarrage_" + ENV

def litDisque(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end
def ecrisDisque(chemin, texte)
    var f = open(chemin, "w")
    f.write(texte)
    f.close()
end

compile(BOUCHONS + "/faux_firmware.be", "file")()
compile(BOUCHONS + "/preparation_boot.be", "file")()
BANC_BOOT.sources = SOURCES
BANC_BOOT.carte = CARTE
BANC_BOOT.litDisque = litDisque
BANC_BOOT.ecrisDisque = ecrisDisque

var globalesAvant = global()
var dossierSolidifies = PREPARATION_BOOT.prepare(ENV, SOURCES, CARTE, litDisque(CARTE + "/_persist.json"), TRAVAIL)
sys.path().push(CARTE)
sys.path().push(SOURCES)
sys.path().push(dossierSolidifies)
sys.path().push(BOUCHONS)
compile("import gpio import light wire1 = OBJET_FACTICE('wire1') wire2 = OBJET_FACTICE('wire2')")()

var exception = nil
try
    compile(LITTLEFS.fichiers["/autoexec.be"])()
except .. as e, m
    exception = str(e) + " - " + str(m)
end

# --- Instantane : listes triees, une ligne par rubrique ---
def trie(l)
    var r = l.copy()
    for a: 0 .. size(r) - 2
        for b: a + 1 .. size(r) - 1
            if r[b] < r[a]    var t = r[a]  r[a] = r[b]  r[b] = t    end
        end
    end
    return r
end
def ligne(titre, liste) print(titre + " (" + str(size(liste)) + ") : " + trie(liste).concat(", ")) end

var drivers = []
for d: tasmota.drivers    drivers.push(classname(d))    end
var regles = []
for r: tasmota.regles    regles.push(str(r[0]))    end
var commandes = []
for c: tasmota.commandes.keys()    commandes.push(str(c))    end
var crons = []
for c: tasmota.crons.keys()    crons.push(str(c))    end
var timers = []
for t: tasmota.timers    timers.push(str(t[2]))    end
var compiles = []
var sources = []
for f: LITTLEFS.fichiers.keys()
    if string.find(f, "/", 1) == -1 && string.endswith(f, ".bec")    compiles.push(f)    end
    if string.find(f, "/", 1) == -1 && string.endswith(f, ".be")    sources.push(f)    end
end
var globales = []
for g: global()
    var t = type(global.member(g))
    if globalesAvant.find(g) == nil && BANC_BOOT.solidifies.find(g) == nil && t != "function" && t != "class"    globales.push(g + ":" + t)    end
end
var erreurs = []
for l: BANC_BOOT.journal
    if l[1] == 1 || string.find(l[0], "_ERREUR") >= 0    erreurs.push(l[0])    end
end

print("carte : " + ENV)
print("exception : " + (exception == nil ? "aucune" : exception))
ligne("drivers", drivers)
ligne("regles", regles)
ligne("commandes", commandes)
ligne("crons", crons)
ligne("minuteries", timers)
ligne("compiles", compiles)
ligne("sources", sources)
ligne("globales", globales)
ligne("erreurs", erreurs)
