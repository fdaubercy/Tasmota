# Banc du preinit.be de la carte d'affichage des debits (Waveshare ESP32-S3-Touch-LCD-7B) : sequence de l'expandeur I2C
# 0x24 et du reset du GT911, sur un bus I2C et des GPIO simules. Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_preinit_7b.be <dossier_vide> [fichier_preinit]
# fichier_preinit : (temoin) une copie modifiee de preinit.be. Derniere ligne : BANC_PREINIT_7B: OK|ECHEC
import global
import sys
import os

var SORTIE = global._argv[1]
var SOURCE = size(global._argv) > 2 ? global._argv[2] : "data/bureau/tasmota32s3-ecran-debits-pac/preinit.be"

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

# ---- Faux firmware : chaque geste est note dans global.SEQ, dans l'ordre -----------------------------------------
os.mkdir(SORTIE + "/modules")
ecris(SORTIE + "/modules/gpio.be", "import global\nvar g = module('gpio')\ng.OUTPUT = 3\ng.INPUT = 1\n"
      + "g.pin_mode = def (p, m) global.SEQ.push(['mode', p, m]) end\n"
      + "g.digital_write = def (p, v) global.SEQ.push(['ecrit', p, v]) end\nreturn g\n")
sys.path().push(SORTIE + "/modules")

class FauxBus
    var adresses, panne, refuse, n
    # refuse : numero (1, 2, 3...) de l'ecriture qui n'obtient pas d'ACK (Wire.write rend false)
    def init(adresses, panne, refuse)    self.adresses = adresses    self.panne = panne    self.refuse = refuse    self.n = 0    end
    def write(a, reg, val, n)
        if self.panne    raise "i2c_error", "bus bloque"    end
        self.n += 1
        global.SEQ.push(["i2c", a, reg, val, n])
        return self.n != self.refuse
    end
end
var fauxTasmota = module("tasmota")
fauxTasmota.wire_scan = def (a) return global.BUS != nil && global.BUS.adresses.find(a) != nil ? global.BUS : nil end
fauxTasmota.delay = def (ms) global.SEQ.push(["attente", ms]) end
global.tasmota = fauxTasmota
global.log = def (m, n) global.JOURNAL.push([m, n]) end

var ECHECS = 0
def verifie(libelle, ok)
    print((ok ? "  OK    " : "  ECHEC ") + libelle)
    if !ok    ECHECS += 1    end
end
def lance(bus)
    global.SEQ = []
    global.JOURNAL = []
    global.BUS = bus
    compile(lis(SOURCE))()
end
def erreurs()
    var n = 0
    for l: global.JOURNAL    if l[1] == 1    n += 1    end    end
    return n
end

print("--- expandeur present")
lance(FauxBus([0x24, 0x5D]))
var ATTENDU = [
    ["i2c", 0x24, 0x02, 0xFF, 1],        # toutes les EXIO en sortie
    ["i2c", 0x24, 0x03, 0xDD, 1],        # dalle alimentee (EXIO6), retroeclairage, tactile en reset (EXIO1 a 0), EXIO5 a 0 (USB)
    ["mode", 4, 3],                      # INT du GT911 en sortie
    ["attente", 100],
    ["ecrit", 4, 0],                     # INT bas pendant le reset -> adresse 0x5D
    ["attente", 100],
    ["i2c", 0x24, 0x03, 0xDF, 1],        # reset du tactile relache
    ["attente", 200],
    ["mode", 4, 1],                      # INT rendu au pilote GT911
]
verifie("sequence exacte de la demo Waveshare (mode, reset du tactile, INT bas, 100/100/200 ms, INT rendu)", global.SEQ == ATTENDU)
if global.SEQ != ATTENDU    print("    obtenu : " + str(global.SEQ))    end
verifie("une ligne info, aucune erreur", erreurs() == 0 && size(global.JOURNAL) == 1 && global.JOURNAL[0][1] == 2)
verifie("EXIO5 a 0 (USB, pas le CAN) dans les deux ecritures des sorties", (global.SEQ[1][3] & 0x20) == 0 && (global.SEQ[6][3] & 0x20) == 0)
verifie("alimentation de la dalle (EXIO6) et retroeclairage (EXIO2) a 1 des la premiere ecriture",
        (global.SEQ[1][3] & 0x44) == 0x44)

print("--- expandeur absent")
lance(FauxBus([0x5D]))
verifie("aucune ecriture, aucun GPIO touche", size(global.SEQ) == 0)
import string
verifie("une erreur au journal qui nomme l'expandeur absent", erreurs() == 1 && string.find(global.JOURNAL[0][0], "0x24 absent") >= 0)

print("--- bus en panne")
lance(FauxBus([0x24], true))
verifie("exception attrapee : une erreur au journal, la carte continue", erreurs() == 1)

print("--- ecriture refusee (pas d'ACK)")
lance(FauxBus([0x24], false, 1))
verifie("1re ecriture refusee : erreur, aucun GPIO touche", erreurs() == 1 && size(global.SEQ) == 1
        && string.find(global.JOURNAL[0][0], "refuse") >= 0)
lance(FauxBus([0x24], false, 2))
verifie("2e ecriture refusee : erreur, aucun GPIO touche", erreurs() == 1 && size(global.SEQ) == 2)
lance(FauxBus([0x24], false, 3))
verifie("reset non relache : erreur, INT quand meme rendu au pilote", erreurs() == 1
        && global.SEQ[size(global.SEQ) - 1] == ["mode", 4, 1] && string.find(global.JOURNAL[0][0], "non relache") >= 0)

print("--- pas de globales laissees")
verifie("aucune constante globale (SORTIES, EXPANDEUR...)", global.contains("SORTIES") == false && global.contains("EXPANDEUR") == false)

print(ECHECS == 0 ? "BANC_PREINIT_7B: OK" : "BANC_PREINIT_7B: ECHEC")
