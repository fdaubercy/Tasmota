# Banc de logFonctions.declare (plan tasks/plans/binomes-berry.md A4) : une cible declaree par un binome est reglable par
# ReglageLog (lieu, seuil, regle, tous, aide) sans toucher CIBLES, DESCRIPTIONS ni lieu() ; les cibles historiques restent.
# Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_log_declare.be [dossier_de_logFonctions]
# (temoin : dossier contenant une copie modifiee de logFonctions.be). Derniere ligne : BANC_LOG_DECLARE: OK|ECHEC
import global
import sys

var DOSSIER = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(DOSSIER)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")     # persist (save compte)

LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
global.boolMute = true
global.JOURNAL = []
global.log = def (m, n) global.JOURNAL.push([m, n]) end
global.diverses = {"logs": {"general": "info"}}
global.serveur = {}
global.drivers = {"voletRoulants": {"activation": "ON", "log": "debug"}, "voletRoulants2": {"activation": "ON", "log": "debug"}}
global.modules = {"pompeVideCave": {"activation": "ON"}}
var fauxTasmota = module("tasmota")
fauxTasmota.cmd = def (c, m) return nil end
fauxTasmota.rtc = def (k) return 1790000000 end
fauxTasmota.loglevel = def (n) return true end
tasmota = fauxTasmota

import persist
import logFonctions
global.logFonctions = logFonctions

var echecs = 0
def verifie(cond, msg)
    print((cond ? "  OK    " : "  ECHEC ") + msg)
    if (!cond)    echecs += 1    end
end
def contient(l, x)    for e: l    if (e == x)    return true    end    end    return false    end

# Avant declaration : cible inconnue, historiques intacts
verifie(logFonctions.lieu("volets2") == nil, "cible non declaree : pas de lieu")
verifie(!contient(logFonctions.cibles(), "volets2"), "cible non declaree : absente de cibles()")
verifie(logFonctions.lieu("volets") != nil && logFonctions.seuil("volets") == 3, "cible historique volets : lieu et seuil debug")

# Declaration
logFonctions.declare("Volets2", "drivers.voletRoulants2", "volets du 2e etage (vr2Fonctions)")
logFonctions.declare("pompe", "modules.pompeVideCave", nil)
logFonctions.declare("fantome", "drivers.absent.environnement", "bloc absent")
var l = logFonctions.lieu("volets2")
verifie(l != nil && l[0] == global.drivers["voletRoulants2"] && l[1] == "log", "cible declaree : lieu = bloc du chemin, cle log")
verifie(logFonctions.seuil("Volets2") == 3, "cible declaree : seuil lu dans le bloc (debug)")
verifie(contient(logFonctions.cibles(), "Volets2") && contient(logFonctions.cibles(), "volets"), "cibles() = historiques + declarees")
verifie(size(logFonctions.cibles()) == size(logFonctions.CIBLES) + 3, "cibles() : chaque declaree une seule fois")
verifie(logFonctions.lieu("fantome") == nil, "chemin absent du persist : pas de lieu, pas d'exception")

# ReglageLog
var r = logFonctions.regle("volets2", "detail")
verifie(isinstance(r, map) && global.drivers["voletRoulants2"]["log"] == "detail", "ReglageLog volets2 detail : ecrit dans le bloc declare")
verifie(isinstance(r, map) && r["modules"].find("Volets2") == "detail", "etat de ReglageLog : la cible declaree y figure")
verifie(persist.nb_save > 0, "persist enregistre")
logFonctions.regle("tous", "erreur")
verifie(global.drivers["voletRoulants2"]["log"] == "erreur" && global.modules["pompeVideCave"]["log"] == "erreur", "ReglageLog tous : cibles declarees comprises")
verifie(type(logFonctions.regle("fantome", "info")) == "string", "cible declaree sans bloc : refus en texte")

# Aide
var aide = logFonctions.aideReglageLog(nil)
var trouve = false
for a: aide    if (a[0] == "Volets2" && a[2] == "seuil du module : volets du 2e etage (vr2Fonctions)")    trouve = true    end    end
verifie(trouve, "aide : la cible declaree et sa description")
var detail = logFonctions.aideReglageLog("pompe")
verifie(detail != nil && detail[0] == "Module : pompe.", "aide detaillee : description par defaut = nom")
verifie(logFonctions.description("modbus") == logFonctions.DESCRIPTIONS["modbus"], "description historique inchangee")

# Cible inconnue : toujours signalee
global.JOURNAL = []
logFonctions.log("X: essai !", LOG_LEVEL_INFO, "inexistante")
var signale = false
for j: global.JOURNAL    if (j[1] == 1 && size(j[0]) > 0)    signale = true    end    end
verifie(signale, "cible inconnue : erreur LOG_ERREUR signalee")

print(echecs == 0 ? "BANC_LOG_DECLARE: OK" : "BANC_LOG_DECLARE: ECHEC")
