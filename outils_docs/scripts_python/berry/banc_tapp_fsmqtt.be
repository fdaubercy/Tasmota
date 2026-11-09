# Banc Berry de l'exemple d'extension data/extensions/fsMqtt/autoexec.be (gabarit A de EXTENSIONS_TAPP.md).
# Rejoue son autoexec.be comme tapp.be : AVANT /autoexec.be, donc sans LOG_LEVEL_* ni logFonctions. Regles protegees :
# aucune globale creee, rien de charge avant la minuterie, un echec de chargement journalise sans exception.
#
# Lancer via son enveloppe Python (racine, berry.exe, code de sortie, archive, temoins mutes) :
#     python outils_docs/scripts_python/berry/banc_tapp_fsmqtt.py
# Derniere ligne : BANC_TAPP_FSMQTT: OK|ECHEC. Ne teste ni la lecture de l'archive par le firmware, ni /ext : essai sur carte, A10.
import global
import sys
var EXTENSION = size(global._argv) > 1 ? global._argv[1] : "data/extensions/fsMqtt"
var JOURNAL = []                                    # lu par le bouchon de logFonctions

class TasmotaStub
    var minuteries, extensions, regles, retirees
    def init() self.minuteries = [] self.extensions = [] self.regles = {} self.retirees = [] end
    def set_timer(d, f, id) self.minuteries.push([d, f]) end
    def add_rule(p, f, id) self.regles[id] = p end  # fsMqtt : « pret » republie a chaque connexion MQTT
    def remove_rule(p, id) self.regles.remove(id) end
    def remove_timer(id) self.retirees.push(id) end
    def add_extension(d) self.extensions.push(d) end
end
var tasmota = TasmotaStub()

var echecs = 0
def verifie(ok, libelle)
    print((ok ? "OK   " : "KO   ") + libelle)
    if !ok    echecs += 1    end
end

def nouvelles_globales(avant)
    var r = []
    for n: global()
        if avant.find(n) == nil    r.push(n)    end
    end
    return r
end

def source()
    var f = open(EXTENSION + "/autoexec.be", "r")
    var t = f.read()
    f.close()
    return t
end

# Declenche la minuterie posee par l'extension ; rend le texte de l'exception qui en sort, ou nil
def declenche(m)
    try
        m[1]()
    except .. as e, msg
        return str(e) + " : " + str(msg)
    end
end

def journal_contient(texte)
    import string
    for l: JOURNAL
        if string.find(l[0], texte) >= 0    return true    end
    end
    return false
end

# --- chargement, comme tapp.be : ni LOG_LEVEL_*, ni logFonctions, ni fsMqtt atteignables
var avant = global()
var erreur_chargement
try
    compile(source())()
except .. as e, msg
    erreur_chargement = str(e) + " : " + str(msg)
end
verifie(erreur_chargement == nil, "chargement avant le prologue : aucune exception (" + str(erreur_chargement) + ")")
var nouvelles = nouvelles_globales(avant)
verifie(size(nouvelles) == 0, "chargement : aucune globale creee (" + str(nouvelles) + ")")
verifie(size(tasmota.minuteries) == 1, "chargement : une seule minuterie posee")
var minuterie = size(tasmota.minuteries) ? tasmota.minuteries[0] : [0, def () end]
verifie(minuterie[0] >= 1000, "minuterie d'au moins 1000 ms : elle passe apres le prologue de /autoexec.be")

# --- le prologue de demarrage.be a tourne : constantes et logFonctions disponibles
global.LOG_LEVEL_ERREUR = 1
global.LOG_LEVEL_INFO = 2
global.LOG_LEVEL_DEBUG = 3
global.LOG_LEVEL_DEBUG_PLUS = 4
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/fsmqtt")

# --- firmware sans fsMqtt : l'echec se journalise et ne sort pas de la minuterie
var sortie = declenche(minuterie)
verifie(sortie == nil, "module absent : aucune exception ne sort (" + str(sortie) + ")")
verifie(journal_contient("EXT_FSMQTT_ERREUR"), "module absent : erreur journalisee")
verifie(!journal_contient("EXT_FSMQTT: module charge"), "module absent : pas de succes annonce")

# --- firmware avec fsMqtt (le vrai module) : abonnements sous le topic du persist
sys.path().push("data/fs")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/fsmqtt")   # le dernier pousse l'emporte
import persist
import mqtt
persist._p = {"serveur": {"mqtt": {"topic": "garage/rideau"}}}
JOURNAL.clear()
sortie = declenche(minuterie)
verifie(sortie == nil, "module present : aucune exception ne sort (" + str(sortie) + ")")
verifie(journal_contient("EXT_FSMQTT: module charge"), "module present : chargement journalise")
verifie(!journal_contient("_ERREUR"), "module present : aucune erreur journalisee")
verifie(mqtt.abonnes.contains("fsmqtt/garage/rideau/ordre") && mqtt.abonnes.contains("fsmqtt/garage/rideau/morceau"),
        "module present : fsMqtt abonne a ordre et morceau")

# --- /ext : « Running » exige add_extension ; « Stop » appelle unload(), qui doit couper la reception
import introspect
verifie(size(tasmota.extensions) == 1 && introspect.contains(tasmota.extensions[0], "unload"),
        "chargement : une extension declaree par add_extension, avec unload()")
if size(tasmota.extensions) == 1 && introspect.contains(tasmota.extensions[0], "unload")
    # Stop pendant un envoi (/fsmqtt.tmp) et une lecture (fichier ouvert) : rien ne doit rester
    class FichierOuvert var ferme def init() self.ferme = false end def close() self.ferme = true end end
    var lu = FichierOuvert()
    global.FS = {"fichiers": {"/fsmqtt.tmp": bytes("00")}, "dossiers": {}}
    global.fsMqttRecepteur.transfert = {}
    global.fsMqttRecepteur.lecture = {"f": lu}
    tasmota.extensions[0].unload()
    verifie(!global.FS["fichiers"].contains("/fsmqtt.tmp"), "Stop pendant un envoi : /fsmqtt.tmp efface")
    verifie(lu.ferme, "Stop pendant une lecture : fichier ferme")
    verifie(tasmota.retirees.find("ext_fsmqtt") != nil, "Stop : minuterie de chargement de l'extension retiree")
    verifie(!mqtt.abonnes.contains("fsmqtt/garage/rideau/ordre") && !mqtt.abonnes.contains("fsmqtt/garage/rideau/morceau"),
            "Stop : desabonne de ordre et morceau")
    verifie(!tasmota.regles.contains("fsmqtt_pret"), "Stop : regle Mqtt#Connected retiree")
    verifie(tasmota.retirees.find("fsmqtt_lit") != nil, "Stop : minuterie de lecture retiree")
    verifie(global.fsMqttRecepteur == nil, "Stop : recepteur oublie")
    tasmota.extensions[0].unload()                 # second Stop : sans effet, sans exception
    # --- relance depuis /ext : tasmota.load rejoue l'autoexec de l'archive, 'import fsMqtt' est en cache
    tasmota.minuteries.clear()
    JOURNAL.clear()
    compile(source())()
    sortie = size(tasmota.minuteries) ? declenche(tasmota.minuteries[0]) : "aucune minuterie"
    verifie(sortie == nil && !journal_contient("_ERREUR"), "relance : sans erreur (" + str(sortie) + ")")
    verifie(mqtt.abonnes.contains("fsmqtt/garage/rideau/ordre") && mqtt.abonnes.contains("fsmqtt/garage/rideau/morceau"),
            "relance : reabonne a ordre et morceau")
    # --- carte dont l'autoexec a deja lance la reception : Stop et Uninstall (delete_ext -> unload) n'y touchent pas
    tasmota.extensions.clear()
    tasmota.minuteries.clear()
    var avant_recepteur = global.fsMqttRecepteur
    compile(source())()
    declenche(tasmota.minuteries[0])
    tasmota.extensions[0].unload()
    verifie(global.fsMqttRecepteur != nil && global.fsMqttRecepteur == avant_recepteur && mqtt.abonnes.contains("fsmqtt/garage/rideau/ordre"),
            "reception lancee par l'autoexec : Stop de l'extension ne la coupe pas")
end

print("BANC_TAPP_FSMQTT: " + (echecs == 0 ? "OK" : "ECHEC"))
