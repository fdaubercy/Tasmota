# Banc de test Berry de la mise en veille de l'environnement des drivers inactifs (2026-10-20) :
# diversFonctions.hiberneDriversInactifs(), appelee a la ligne 31 de chaque autoexec.be, AVANT que
# gestionFileFolder.listeEtRepartitLesFichiers() ne cree /json.
# Panne d'origine (P4 du garage, 2026-10-20) : LittleFS neuf -> pas de /json -> writeFile leve io_error,
# rien ne l'attrape, l'autoexec meurt et aucun module n'est charge (« BRY: No 'autoexec.be' »).
# -----------------------------------------------------------------------------------------------
# A lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_veille_drivers.be [dossier_sources]
# Le VRAI diversFonctions est importe depuis dossier_sources (data/fs par defaut) ; path, persist et
# gestionFileFolder sont bouchonnes (bouchons_berry/veille/ : LittleFS en memoire).
# berry.exe ne pose pas de code de sortie : la derniere ligne, BANC_VEILLE_DRIVERS: OK|ECHEC, fait foi.
import global
import sys
import json
import string

var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/veille")   # le dernier ajoute est cherche en premier : bouchons avant data/fs

LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
class TASMOTA_BOUCHON    def yield() end    end
tasmota = TASMOTA_BOUCHON()
var journal = []
var invalidations = 0               # appels a logFonctions.invalideSeuils (audit P6.3)
class LOG_BOUCHON
    def log(msg, niveau, cible) journal.push([msg, niveau]) end
    def invalideSeuils() invalidations += 1 end
end
logFonctions = LOG_BOUCHON()
drivers = {}                        # global du firmware (persist.drivers), pose par prepare()
boolMute = true                     # globale de l autoexec, lue par d autres fonctions du module

import persist
import path
import gestionFileFolder
import diversFonctions

var echecs = 0
def controle(nom, condition)
    if condition    print("  ok    " + nom)
    else            print("  ECHEC " + nom)    echecs += 1
    end
end

# LittleFS neuf : seulement la racine ; drivers comme le P4 du depot (ecran OFF avec un environnement)
def prepare()
    gestionFileFolder.dossiers = {"/": true}
    gestionFileFolder.fichiers = {}
    gestionFileFolder.plein = false
    persist.sauvegardes = 0
    invalidations = 0
    path.creations = 0
    journal = []
    drivers = {"activation": "ON",
               "ecran": {"activation": "OFF", "environnement": {"ecran": {"largeur": 320}}},
               "leds": {"activation": "ON", "environnement": {"broche": 5}}}
end

# Appelle la fonction comme l'autoexec : une exception qui sort tuerait l'autoexec sur la carte
def appelle()
    try
        diversFonctions.hiberneDriversInactifs()
        return nil
    except .. as e, m
        return str(e) + " - " + str(m)
    end
end

def erreurLoguee()
    for l: journal    if (l[1] == LOG_LEVEL_ERREUR && string.find(l[0], "VEILLE_DRIVERS_ERREUR") == 0)    return true    end    end
    return false
end

print("1. LittleFS neuf, sans /json (panne du P4)")
prepare()
var exc = appelle()
controle("aucune exception ne sort (l'autoexec continue)" + (exc ? " : " + exc : ""), exc == nil)
controle("/json cree", path.isdir("/json"))
var veille = gestionFileFolder.fichiers.find("/json/driversInactifs.json")
controle("driversInactifs.json ecrit avec l'environnement de 'ecran'",
         veille != nil && json.load(veille).find("ecran", {}).find("ecran", {}).find("largeur") == 320)
controle("pas de .tmp restant", !gestionFileFolder.fichiers.contains("/json/driversInactifs.json.tmp"))
controle("persist allege : environnement de 'ecran' vide", drivers["ecran"]["environnement"].size() == 0)
controle("driver actif intact", drivers["leds"]["environnement"].find("broche") == 5)
controle("persist sauvegarde", persist.sauvegardes == 1)

print("2. Ecriture impossible (LittleFS plein) : rien n'est perdu, l'erreur est loguee")
prepare()
gestionFileFolder.plein = true
exc = appelle()
controle("aucune exception ne sort" + (exc ? " : " + exc : ""), exc == nil)
controle("erreur VEILLE_DRIVERS_ERREUR loguee", erreurLoguee())
controle("environnement de 'ecran' conserve dans le persist", drivers["ecran"]["environnement"].size() == 1)
controle("persist non sauvegarde", persist.sauvegardes == 0)

print("3. Regime etabli : /json present, reveil d'un driver redevenu actif")
prepare()
gestionFileFolder.dossiers["/json"] = true
gestionFileFolder.fichiers["/json/driversInactifs.json"] = json.dump({"ecran": {"ecran": {"largeur": 320}}})
drivers["ecran"] = {"activation": "ON", "environnement": {}}
exc = appelle()
controle("aucune exception ne sort" + (exc ? " : " + exc : ""), exc == nil)
controle("environnement de 'ecran' restaure", drivers["ecran"]["environnement"].find("ecran", {}).find("largeur") == 320)
controle("persist sauvegarde", persist.sauvegardes == 1)
controle("P6.3 : seuils de log en cache oublies (reveil)", invalidations == 1)

print("4. Regime etabli : /json present, mise en veille d'un driver devenu inactif")
prepare()
gestionFileFolder.dossiers["/json"] = true
gestionFileFolder.fichiers["/json/driversInactifs.json"] = json.dump({"SD": {"broche": 12}})
exc = appelle()
controle("aucune exception ne sort" + (exc ? " : " + exc : ""), exc == nil)
controle("/json existant non recree", path.creations == 0)
veille = json.load(gestionFileFolder.fichiers.find("/json/driversInactifs.json", "{}"))
controle("fichier complete : 'ecran' ajoute, 'SD' garde", veille.contains("ecran") && veille.find("SD", {}).find("broche") == 12)
controle("pas de .tmp restant", !gestionFileFolder.fichiers.contains("/json/driversInactifs.json.tmp"))
controle("persist allege et sauvegarde", drivers["ecran"]["environnement"].size() == 0 && persist.sauvegardes == 1)
controle("P6.3 : seuils de log en cache oublies (mise en veille)", invalidations == 1)

print(echecs == 0 ? "BANC_VEILLE_DRIVERS: OK" : "BANC_VEILLE_DRIVERS: ECHEC (" + str(echecs) + ")")
