# Banc Berry de data/fs/gestionFileFolder.be::listeEtRepartitLesFichiers : repartition des fichiers au demarrage.
# Charge le VRAI module sous les bouchons de bouchons_berry/fsmqtt/ (FS en memoire, logFonctions). Regle protegee :
# une ecriture ratee ne perd jamais le fichier d'origine.
#
# Lancer via son enveloppe Python (racine, berry.exe, code de sortie, temoins mutes) :
#     python outils_docs/scripts_python/berry/banc_repartition_fichiers.py
# Derniere ligne : BANC_REPARTITION: OK|ECHEC. Ne teste pas LittleFS.
import global
import sys
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/fsmqtt")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var JOURNAL = []
var RENOMMAGE_REFUSE = false
var ECRITURE_KO = false         # l'ecriture leve (carte sans place, selon le firmware)
var ECRITURE_COUPEE = false     # l'ecriture ne garde que le premier octet, sans erreur : FS plein
var FS = {"fichiers": {}, "dossiers": {}}

# open() du firmware sur le FS en memoire (le module est compile apres cette globale : elle remplace le builtin)
class FichierMemoire
    var c, pos
    def init(c, mode)
        if c[0] != "/"    c = "/" + c    end       # comme le firmware
        self.c = c  self.pos = 0
        if mode == "w"    FS["fichiers"][c] = bytes()    end
        if mode == "r" && !FS["fichiers"].contains(c)    raise "io_error", "absent : " + c    end
    end
    def write(d)
        if ECRITURE_KO    raise "io_error", "write failed"    end
        if type(d) == "string"    d = bytes().fromstring(d)    end
        FS["fichiers"][self.c] = FS["fichiers"][self.c] + (ECRITURE_COUPEE ? d[0 .. 0] : d)
    end
    def read()
        var t = FS["fichiers"][self.c]  self.pos = size(t)  return t.asstring()
    end
    def readbytes(n)
        var t = FS["fichiers"][self.c]
        var fin = self.pos + n > size(t) ? size(t) : self.pos + n
        var r = fin > self.pos ? t[self.pos .. fin - 1] : bytes()
        self.pos = fin
        return r
    end
    def size()    return global.size(FS["fichiers"][self.c])    end
    def close() end
end
var open = def (c, mode) return FichierMemoire(c, mode) end

class TasmotaStub
    def yield() end
end
var tasmota = TasmotaStub()
var load = def () end       # builtin du firmware, absent de berry.exe ; le reste du module ne sert pas ici

import logFonctions
import gestionFileFolder
global.gestionFileFolder = gestionFileFolder

var echecs = 0
def verifie(condition, libelle)
    print((condition ? "OK   " : "KO   ") + libelle)
    if !condition    echecs += 1    end
end

# Binaire : octets nuls et non ASCII, sur plus d'un morceau de copie (une archive .tapp en est un)
def binaire(n)
    var b = bytes()
    for i: 0 .. n - 1    b.add(i % 251)    end
    return b
end

def remet(fichiers, dossiers)
    FS = {"fichiers": fichiers, "dossiers": dossiers}
    JOURNAL = []
    RENOMMAGE_REFUSE = false
    ECRITURE_KO = false
    ECRITURE_COUPEE = false
end

def existe(c)    return FS["fichiers"].contains(c)    end
def erreurs()
    import string
    var n = 0
    for j: JOURNAL    if j[1] == LOG_LEVEL_ERREUR && string.find(j[0], "_ERREUR") > 0    n += 1    end    end
    return n
end
def lance()    gestionFileFolder.listeEtRepartitLesFichiers()    end

# Cas ordinaires
var gros = binaire(5000)
remet({"/x.tapp": gros, "/a.json": bytes().fromstring('{"a":1}'), "/_persist.json": bytes().fromstring("{}"),
       "/p.html": bytes().fromstring("<p>"), "/s.js": bytes().fromstring("js"), "/s.css": bytes().fromstring("css")},
      {"/sd": true, "/.extensions": true})
lance()
verifie(!existe("/x.tapp") && FS["fichiers"].find("/.extensions/x.tapp") == gros, "tapp : deplace, octets identiques (binaire, 5000 octets)")
verifie(!existe("/a.json") && FS["fichiers"].find("/json/a.json") == bytes().fromstring('{"a":1}'), "json : deplace dans /json")
verifie(existe("/_persist.json") && !existe("/json/_persist.json"), "persist : reste a la racine")
verifie(FS["fichiers"].find("/sd/html/p.html") != nil && FS["fichiers"].find("/sd/js/s.js") != nil && FS["fichiers"].find("/sd/css/s.css") != nil, "html, js, css : deplaces sur la SD")
var restes = 0
for c: FS["fichiers"].keys()    if c[-4 ..] == ".tmp"    restes += 1    end    end
verifie(restes == 0 && erreurs() == 0, "aucun fichier temporaire ni erreur")

# Images des ecrans : .png, .jpg, .bmp (casse indifferente) vers /sd/images/PNG, JPG, BMP (un dossier par format, choix du
# 2026-11-13) ; un nom qui contient seulement .png reste a la racine
remet({"/fond.png": bytes("89504e47"), "/icone.JPG": bytes("ffd8"), "/vue.bmp": bytes("424d"), "/note.png.txt": bytes("01")}, {"/sd": true, "/.extensions": true})
lance()
verifie(FS["fichiers"].find("/sd/images/PNG/fond.png") == bytes("89504e47") && existe("/sd/images/JPG/icone.JPG") && existe("/sd/images/BMP/vue.bmp")
        && FS["dossiers"].contains("/sd/images/PNG") && !existe("/fond.png") && existe("/note.png.txt")
        && !existe("/sd/images/PNG/note.png.txt"), "images : deplacees dans /sd/images/<FORMAT>, octets identiques")

# Fonds du visuel d'accueil : .svg et .webp (4 lettres : dossier WEBP, pas EBP), un nom qui les contient seulement reste
remet({"/visuel.svg": bytes("3c737667"), "/visuel.WEBP": bytes("52494646"), "/note.svg.txt": bytes("01"), "/x.webp.bak": bytes("02")}, {"/sd": true, "/.extensions": true})
lance()
verifie(FS["fichiers"].find("/sd/images/SVG/visuel.svg") == bytes("3c737667") && FS["fichiers"].find("/sd/images/WEBP/visuel.WEBP") == bytes("52494646")
        && !existe("/visuel.svg") && !existe("/visuel.WEBP") && existe("/note.svg.txt") && existe("/x.webp.bak") && !existe("/sd/images/EBP/visuel.WEBP"),
        "svg et webp : deplaces dans /sd/images/SVG et /sd/images/WEBP, les noms qui les contiennent seulement restent")

# Dossier des extensions absent : le .tapp est deplace des ce demarrage
remet({"/x.tapp": bytes("0102")}, {"/sd": true})
lance()
verifie(FS["dossiers"].contains("/.extensions") && existe("/.extensions/x.tapp") && !existe("/x.tapp"), "tapp : dossier cree et fichier deplace au meme demarrage")

# Seuls les noms finis par .tapp
remet({"/mon.tapp.bak": bytes("01"), "/y.tapp_": bytes("02"), "/note.tapp.txt": bytes("03")}, {"/sd": true, "/.extensions": true})
lance()
verifie(existe("/mon.tapp.bak") && existe("/y.tapp_") && existe("/note.tapp.txt") && size(FS["fichiers"]) == 3, "tapp : un nom qui contient seulement .tapp reste a sa place")

# Homonyme : la nouvelle version remplace l'ancienne, et le journal le dit
import string
remet({"/x.tapp": bytes("0202"), "/.extensions/x.tapp": bytes("0101")}, {"/sd": true, "/.extensions": true})
lance()
var dit = false
for j: JOURNAL    if string.find(j[0], "remplace") > 0 && string.find(j[0], "x.tapp") > 0    dit = true    end    end
verifie(FS["fichiers"].find("/.extensions/x.tapp") == bytes("0202") && !existe("/x.tapp") && dit, "tapp : homonyme remplace, journal qui le dit")

# Les pannes : l'original survit, l'homonyme aussi, rien ne traine, une erreur est journalisee
def panne(libelle, regle)
    remet({"/x.tapp": bytes("010203040506"), "/a.json": bytes("0a0b"), "/p.html": bytes("0c0d"), "/.extensions/x.tapp": bytes("0909")}, {"/sd": true, "/.extensions": true})
    regle()
    lance()
    verifie(FS["fichiers"].find("/x.tapp") == bytes("010203040506"), libelle + " : le .tapp d'origine survit, intact")
    verifie(FS["fichiers"].find("/a.json") == bytes("0a0b"), libelle + " : le .json d'origine survit")
    verifie(FS["fichiers"].find("/p.html") == bytes("0c0d"), libelle + " : le .html d'origine survit")
    var tmp = 0
    for c: FS["fichiers"].keys()    if c[-4 ..] == ".tmp"    tmp += 1    end    end
    verifie(tmp == 0, libelle + " : aucun temporaire laisse")
    verifie(erreurs() >= 3, libelle + " : erreur journalisee pour chaque fichier (" + str(erreurs()) + ")")
end
panne("ecriture qui leve", def () ECRITURE_KO = true end)
panne("FS plein, ecriture tronquee", def () ECRITURE_COUPEE = true end)
remet({"/x.tapp": bytes("0102")}, {"/sd": true, "/.extensions": true})
ECRITURE_KO = true
lance()
verifie(FS["fichiers"].find("/.extensions/x.tapp") == nil, "ecriture qui leve : aucune copie partielle sous le nom final")
remet({"/x.tapp": bytes("010203"), "/.extensions/x.tapp": bytes("0909")}, {"/sd": true, "/.extensions": true})
ECRITURE_COUPEE = true
lance()
verifie(FS["fichiers"].find("/.extensions/x.tapp") == bytes("0909"), "FS plein : l'ancienne version de l'extension reste en place")
remet({"/x.tapp": bytes("010203")}, {"/sd": true, "/.extensions": true})
RENOMMAGE_REFUSE = true
lance()
verifie(FS["fichiers"].find("/x.tapp") == bytes("010203") && erreurs() >= 1, "renommage refuse : l'original survit, erreur journalisee")

print(echecs == 0 ? "BANC_REPARTITION: OK" : "BANC_REPARTITION: ECHEC (" + str(echecs) + ")")
