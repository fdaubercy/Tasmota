# Banc de test Berry de data/fs/ledsFonctions.be : ruban WS2812 en mode AUTO/MANUEL, bouton poussoir,
# clignotement d'erreur, recopie par la LED du dev-kit, ReglageLeds, page web (2026-10-13).
# -----------------------------------------------------------------------------------------------
# Charge le VRAI fichier (pas une copie) sous des globaux bouchonnes et l'EXECUTE (sequences
# d'appuis, echeance du MANUEL simulee par tasmota.millis()) - AVANT de flasher une carte.
#
# Lancer via son enveloppe Python (deduit racine + berry.exe, code de sortie) :
#     python outils_docs/scripts_python/berry/banc_leds.py [dossier_sources]
# Ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_leds.be [dossier_sources]
#
# dossier_sources (defaut data/fs) : pour eprouver une copie (temoin mute) sans toucher a data/fs.
# Copier data/fs EN ENTIER : berry.exe cherche un module d'abord dans le dossier du fichier qui
# l'importe (ledsFonctions importe diversFonctions) et s'arrete sur io_error s'il y manque.
# Toujours passer la copie INTACTE avant la copie mutee (lecon du 2026-10-06).
# Portee : la logique du module. Ne teste NI le rendu reel de la page, NI les evenements reels du
# bouton, NI le ruban physique. La derniere ligne imprimee, BANC_LEDS: OK|ECHEC, est lue par
# l'enveloppe Python pour son code de sortie.
import global
import sys
import string
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
# berry.exe cherche les modules du DERNIER chemin ajoute au premier : les bouchons (light, persist,
# diversFonctions) passent donc APRES le dossier des sources, qui fournit ledsFonctions.be.
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
var journal = []
class LogStub def log(m, n, c) journal.push(str(m)) end end
var logFonctions = LogStub()

var peints = []                       # [couleur, bri] des clear_to sur le ruban natif
class Leds
    static WS2812_GRB = 1
    static SPI = 2
    var n
    def init(n, pin, a, b) self.n = n end
    def clear_to(c, b) if self.n == nil peints.push([c, b]) end end
    def show() end
end

class TasmotaStub
    var cmds, ms, timers, regles, schema, so32, so1
    def init() self.cmds = [] self.ms = 1000 self.timers = {} self.regles = {} self.schema = 0 self.so32 = 40 self.so1 = "OFF" end
    def cmd(c, m)
        import light
        self.cmds.push(c)
        if c == "_Scheme"    return {"Scheme": self.schema}    end
        if c == "SetOption32"    return {"SetOption32": self.so32}    end
        if c == "SetOption1"    return {"SetOption1": self.so1}    end
        if c == "StateText4"    return {"StateText4": "HOLD"}    end
        if c == "Power1 TOGGLE"    light.etat["power"] = !light.etat["power"]    end
        if c == "Scheme 0"    self.schema = 0    end
        return {}
    end
    def millis() return self.ms end
    def time_reached(t) return self.ms >= t end
    def set_timer(d, f, id) self.timers[id] = f end
    def remove_timer(id) if self.timers.contains(id) self.timers.remove(id) end end
    def add_rule(p, f, id) self.regles[p] = f end
    def resp_cmnd(x) end
    def scale_uint(v, a, b, c, d) return int((v - a) * (d - c) / (b - a) + c) end
    def wifi(x) return true end
    def eth(x) return false end
    def get_option(n) return 0 end
end
var tasmota = TasmotaStub()

var ruban = {"activation": "ON", "bouton": 1, "dureeManuel": 30, "appuiLong": 15}
var drivers = {"leds": {"activation": "ON", "environnement": {"leds": {"ruban": ruban}}}}
var modules = {"cuve": {"activation": "ON", "environnement": {"relais": {"relai1":
                {"activation": "ON", "type": 1376, "id": 1, "channel": 0, "virtuel": "OFF"}}}}}
var persist = {}
var diverses = {"eviteResetBTN": "OFF"}

import light
light.etat = {"power": true, "hue": 60, "sat": 255, "bri": 127, "rgb": "FFFF00"}
import ledsFonctions

var echecs = 0
def verifie(c, nom)
    print((c ? "  ok   " : "  ECHEC ") + nom)
    if !c    echecs += 1    end
end
var appelsAuto = 0
ledsFonctions.enregistreRetourAuto(def () appelsAuto += 1 ledsFonctions.appliqueAuto(100) end, "la couleur suit le niveau")

print("1. AUTO : la teinte du module metier est posee")
ledsFonctions.appliqueAuto(100)
verifie(light.etat["hue"] == 100 && ledsFonctions.mode == "AUTO", "teinte 100 posee en AUTO")
ledsFonctions.maj()
verifie(ledsFonctions.mode == "AUTO", "pas de faux changement exterieur apres appliqueAuto")

print("2. Couleur changee depuis la page web -> MANUEL, AUTO ignore")
light.etat["hue"] = 200
ledsFonctions.maj()
verifie(ledsFonctions.mode == "MANUEL", "ecart de teinte -> MANUEL")
verifie(ledsFonctions.resteMinutes() == 30, "30 min restantes")
ledsFonctions.appliqueAuto(50)
verifie(light.etat["hue"] == 200, "appliqueAuto ignore en MANUEL")
ledsFonctions.maj()
verifie(ledsFonctions.mode == "MANUEL", "pas de nouveau declenchement sur la meme couleur")

print("3. Fin de duree -> AUTO, couleur du module reposee")
tasmota.ms += 30 * 60000
ledsFonctions.maj()
verifie(ledsFonctions.mode == "AUTO" && appelsAuto == 1 && light.etat["hue"] == 100, "retour AUTO a l'echeance, rappel du module")

print("4. Bouton : appui court, double appui")
ledsFonctions.actionBouton("SINGLE")
verifie(light.etat["power"] == false && ledsFonctions.mode == "MANUEL", "SINGLE : Power1 TOGGLE + MANUEL")
ledsFonctions.actionBouton("SINGLE")
verifie(light.etat["power"] == true, "2e SINGLE rallume (pas de deduplication)")
ledsFonctions.actionBouton("DOUBLE")
verifie(ledsFonctions.mode == "AUTO" && appelsAuto == 2, "DOUBLE : retour AUTO")

print("5. Bouton : appui long, defilement, relachement")
light.etat["power"] = false
ledsFonctions.actionBouton("HOLD")
verifie(light.etat["power"] == true && light.etat["hue"] == 0 && light.etat["sat"] == 255, "HOLD : allume, rouge")
verifie(tasmota.timers.contains("ledsRubanDefile"), "defilement arme")
tasmota.timers["ledsRubanDefile"]()
verifie(light.etat["hue"] == 30, "cran du defilement : orange")
ledsFonctions.actionBouton("CLEAR")
verifie(!tasmota.timers.contains("ledsRubanDefile"), "CLEAR arrete le defilement")
ledsFonctions.maj()
verifie(ledsFonctions.mode == "MANUEL", "la couleur de la palette n'est pas prise pour un changement exterieur")

print("6. Retour AUTO : saturation d'avant le MANUEL rendue (blanc de la palette)")
for i: 1 .. 6    ledsFonctions.couleurSuivante()    end
verifie(light.etat["sat"] == 0, "blanc : saturation 0")
ledsFonctions.retourAuto("banc")
verifie(light.etat["sat"] == 255 && light.etat["hue"] == 100, "AUTO : saturation 255 et teinte du module")

print("7. Erreur : clignotement en AUTO seulement, recopie par la LED du dev-kit")
ledsFonctions.signaleErreur("cuve", true)
peints = []
ledsFonctions.maj()
ledsFonctions.maj()
verifie(size(peints) == 2 && peints[0][0] != peints[1][0], "AUTO + erreur : le ruban clignote (2 phases)")
verifie(!ledsFonctions.imposees.contains("ruban"), "erreur : pas de couleur imposee a la LED (elle clignote)")
ledsFonctions.passeManuel("banc")
peints = []
ledsFonctions.maj()
verifie(size(peints) == 1 && peints[0][0] == 0xFFFF00, "MANUEL : clignotement arrete, ruban repeint de sa couleur")
ledsFonctions.maj()
verifie(size(peints) == 1, "MANUEL : plus aucune ecriture de pixels")
ledsFonctions.signaleErreur("cuve", false)
ledsFonctions.maj()
verifie(ledsFonctions.imposees.contains("ruban"), "sans erreur, ruban allume : la LED recopie le ruban")

print("8. Animation lancee hors bouton -> MANUEL ; palette -> Scheme 0")
ledsFonctions.retourAuto("banc")
tasmota.schema = 3
ledsFonctions.maj()
verifie(ledsFonctions.mode == "MANUEL", "Scheme 3 -> MANUEL")
light.etat["hue"] = 321
ledsFonctions.maj()
verifie(ledsFonctions.mode == "MANUEL", "animation en cours : pas de detection de teinte")
ledsFonctions.couleurSuivante()
verifie(tasmota.schema == 0, "couleur de palette : animation arretee")

print("9. Blanc : une teinte differente sur du blanc n'est pas un changement")
ledsFonctions.retourAuto("banc")
light.etat["sat"] = 0
ledsFonctions.attendu = [100, 0]
light.etat["hue"] = 250
ledsFonctions.maj()
verifie(ledsFonctions.mode == "AUTO", "blanc -> blanc : reste AUTO")

print("10. ReglageLeds, reglages du bouton, aide, page web")
ledsFonctions.reglageLeds("ReglageLeds", 0, "rubanDuree 0", nil)
verifie(ruban["dureeManuel"] == 0, "rubanDuree 0 memorise")
ledsFonctions.reglageLeds("ReglageLeds", 0, "rubanManuel", nil)
verifie(ledsFonctions.mode == "MANUEL" && ledsFonctions.resteMinutes() == nil, "duree 0 : MANUEL sans fin")
tasmota.ms += 100 * 60000
ledsFonctions.maj()
verifie(ledsFonctions.mode == "MANUEL", "duree 0 : pas de retour AUTO au temps")
ledsFonctions.reglageLeds("ReglageLeds", 0, "rubanAuto", nil)
verifie(ledsFonctions.mode == "AUTO", "rubanAuto")
tasmota.cmds = []
ledsFonctions.regleBouton()
verifie(tasmota.cmds.find("SetOption32 15") != nil && tasmota.cmds.find("SetOption1 ON") != nil, "SetOption32 15 et SetOption1 ON")
verifie(diverses["eviteResetBTN"] == "ON", "eviteResetBTN ON inscrit dans le persist")
var aide = ledsFonctions.aideBouton()
verifie(string.find(aide.concat(" "), "1,5 s") >= 0 && string.find(aide.concat(" "), "suit le niveau") >= 0, "aide : appui long 1,5 s, description du module")
var web = ledsFonctions.scriptAideWeb()
verifie(string.find(web, "eb('o1')") >= 0 && string.find(web, "&#9432;") >= 0, "pastille sur le bouton o1")
verifie(string.find(web, "ldAuto") >= 0 && string.find(web, "MutationObserver") >= 0, "symbole du mode : clic = retour AUTO, suit la zone l1")
verifie(string.find(ledsFonctions.ligneWeb(), "data-m='AUTO' data-t='&#10227;'") >= 0, "ligne cachee AUTO = cycle")
ledsFonctions.passeManuel("banc")
verifie(string.find(ledsFonctions.ligneWeb(), "data-m='MANUEL' data-t='&#9995; ") >= 0, "ligne cachee MANUEL = main")

print("10b. Animation lue UNE fois par seconde, partagee avec modbusFonctions.etatRuban (audit N3/P5.3)")
var nbScheme = def () var n = 0 for c: tasmota.cmds    if c == "_Scheme"    n += 1    end    end return n end
tasmota.schema = 6
tasmota.cmds = []
ledsFonctions.maj()
verifie(nbScheme() == 1 && ledsFonctions.animationRecente() == 6, "maj : un seul '_Scheme', animation 6 disponible pour les autres modules")
tasmota.ms += 1400
verifie(ledsFonctions.animationRecente() == 6, "1,4 s plus tard : encore fraiche (le push de la seconde suivante la reprend)")
tasmota.ms += 200
verifie(ledsFonctions.animationRecente() == nil, "1,6 s sans maj : perimee -> nil (l'appelant relit '_Scheme' lui-meme)")
tasmota.schema = 0
ledsFonctions.maj()
ledsFonctions.retourAuto("banc")

print("11. Ruban desactive : plus rien")
ruban["activation"] = "OFF"
ledsFonctions.imposeCouleur("ruban", 0x123456, 10)
ledsFonctions.maj()
verifie(!ledsFonctions.imposees.contains("ruban"), "ruban inactif : la LED rend la main")

print(echecs == 0 ? "BANC_LEDS: OK" : "BANC_LEDS: ECHEC (" + str(echecs) + ")")
