# Banc de test Berry de data/fs/controleCoprocesseur.be : alerte « firmware du coprocesseur Wi-Fi (ESP32-C6)
# pas a jour » des cartes P4 (2026-10-26, plan tasks/plans/alerte-firmware-c6.md).
# -----------------------------------------------------------------------------------------------
# Charge le VRAI fichier sous des globaux bouchonnes (tasmota.cmd("Hosted"), webclient, webserver) et
# l'EXECUTE : comparaison des versions, lecture de l'en-tete d'image du serveur, essais, ligne d'accueil,
# page /coprocesseur et lancement de HostedOta.
#
# Lancer via son enveloppe Python (deduit racine + berry.exe, code de sortie, rendu dans Chrome) :
#     python outils_docs/scripts_python/berry/banc_coprocesseur.py [--sans-navigateur]
# Ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_coprocesseur.be [dossier_sources [page.html]]
#
# dossier_sources (defaut data/fs) : pour eprouver une copie (temoin) sans toucher a data/fs.
# page.html : si donne, la page /coprocesseur du scenario « en retard, publie » y est ecrite (rendu Chrome).
# Portee : la logique du module. Ne teste NI le vrai serveur web de Tasmota, NI le reseau, NI la mise a jour
# reelle du C6. La derniere ligne imprimee, BANC_COPROCESSEUR: OK|ECHEC, est lue par l'enveloppe Python.
import global
import sys
import string
import json
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
var SORTIE_PAGE = size(global._argv) > 2 ? global._argv[2] : nil
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry")

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var boolMute = true
var journal = []
class LogStub def log(m, n, c) journal.push([str(m), n]) end end
var logFonctions = LogStub()
class Driver end                  # classe native du firmware, absente de berry.exe

# Reponse de la commande Hosted (nil = commande inconnue, carte sans coprocesseur)
var HOSTED = nil
def hosted(c6, hote) return {"Hosted": {"Host": hote, "Hosted": c6, "MCU": "esp32c6"}} end

class TasmotaStub
    var cmds, ms, timers, drivers, envoiWeb, regles
    def init() self.raz() self.drivers = [] end
    def raz() self.cmds = [] self.ms = 20000 self.timers = {} self.envoiWeb = [] self.regles = {} end
    def add_rule(p, f, id) self.regles[p] = f end
    def cmd(c, m)
        self.cmds.push(c)
        if c == "Hosted"    return (HOSTED != nil ? HOSTED : {"Command": "Unknown"})    end
        return {"HostedOta": "Version 2.6.6 from ..."}
    end
    def millis() return self.ms end
    def set_timer(d, f, id) self.timers[id] = [d, f] end
    def remove_timer(id) if self.timers.contains(id) self.timers.remove(id) end end
    def add_driver(d) self.drivers.push(d) end
    def web_send(t) self.envoiWeb.push(t) end
    # Declenche le timer 'id' (le retire d'abord, comme Tasmota) ; false s'il n'existe pas
    def declenche(id)
        if !self.timers.contains(id)    return false    end
        var t = self.timers[id]
        self.timers.remove(id)
        self.ms += t[0]
        t[1]()
        return true
    end
end
var tasmota = TasmotaStub()

# Serveur OTA simule : url -> [code, bytes ou nil] ; "exception" = GET leve une exception
var SERVEUR = {}
var requetes = []                 # [url, en-tetes] de chaque GET
var fermetures = 0
class webclient
    var url, entetes
    def init() self.entetes = {} end
    def set_timeouts(a, b) return self end
    def begin(u) self.url = u end
    def add_header(n, v) self.entetes[n] = v end
    def GET()
        requetes.push([self.url, self.entetes])
        var r = SERVEUR.find(self.url, [-1, nil])
        if r[0] == "exception"    raise "io_error", "connexion coupee"    end
        return r[0]
    end
    def get_bytes() return SERVEUR[self.url][1] end
    def close() fermetures += 1 end
end

# En-tete reel (0x90 premiers octets) de .../coprocessor/v2.12.13/network_adapter_esp32c6.bin, lu le 2026-10-26
var ENTETE_21213 = bytes("E9050220D6038040EE0000000D000000006300000000000120000D4260BA03003254CDAB000000000000000000000000322E31322E3133000000000000000000000000000000000000000000000000006E6574776F726B5F61646170746572000000000000000000000000000000000031343A34383A3234000000000000000053657020323620323032360000000000")
def entete(version)
    var b = ENTETE_21213.copy()
    for i: 0x30 .. 0x4F    b[i] = 0    end
    var v = bytes().fromstring(version)
    for i: 0 .. size(v) - 1    b[0x30 + i] = v[i]    end
    return b
end

var BASE = "https://ota.tasmota.com/tasmota32/coprocessor"
var URL_21213 = BASE + "/v2.12.13/network_adapter_esp32c6.bin"
var URL_DEFAUT = BASE + "/network_adapter_esp32c6.bin"

import webserver
webserver.HTTP_POST = 2
webserver.BUTTON_MAIN = 0
webserver.routes = []
webserver.acces = true
webserver.on = def (uri, f, methode) webserver.routes.push([uri, methode]) end
webserver.check_privileged_access = def () return webserver.acces end
webserver.content_button = def (b) end
import gestionFileFolder
gestionFileFolder.envoyes = []
gestionFileFolder.readFileByLineAndContentSend = def (chemin)
    gestionFileFolder.envoyes.push(chemin)
    var f = open("data" + chemin, "r")      # le VRAI gabarit du depot (data/sd/html/...)
    webserver.envoye.push(f.read())
    f.close()
end
def razWeb() webserver.envoye = [] webserver.termine = false webserver.acces = true gestionFileFolder.envoyes = [] end

var echecs = 0
def verifie(c, nom)
    print((c ? "  ok   " : "  ECHEC ") + nom)
    if !c    echecs += 1    end
end
def journalContient(texte, niveau)
    for l: journal    if string.find(l[0], texte) > -1 && (niveau == nil || l[1] == niveau)    return true    end    end
    return false
end
def contient(liste, texte)
    for t: liste    if string.find(str(t), texte) > -1    return true    end    end
    return false
end
def compteCmd(prefixe)
    var n = 0
    for c: tasmota.cmds    if string.find(c, prefixe) == 0    n += 1    end    end
    return n
end

print("1. Activation : garde du persist")
var serveur = {"coprocesseur": {"activation": "OFF"}}
import controleCoprocesseur as copro
verifie(copro == nil, "activation OFF -> import rend nil")
verifie(size(tasmota.drivers) == 0 && size(tasmota.timers) == 0, "OFF : ni driver, ni timer")

# L'import est en cache (il vaut nil) : le fichier est recompile et execute (il rend son module), puis son
# init() est appele comme le ferait l'import, cette fois en ACTIVE
serveur = {"coprocesseur": {"activation": "ON"}}
var inst = compile(SOURCES + "/controleCoprocesseur.be", "file")()
verifie(type(inst) == "module", "le fichier rend son module")
inst = inst.init(inst)
verifie(type(inst) == "instance" && size(tasmota.drivers) == 1, "activation ON -> instance enregistree comme driver")
verifie(contient(webserver.routes, "/coprocesseur") && size(webserver.routes) == 2, "routes GET et POST /coprocesseur")
var COPRO = classof(inst)
def neuf(config)
    tasmota.raz() requetes = [] journal = [] razWeb()
    return COPRO(config != nil ? config : {"activation": "ON"})
end

print("2. Versions : comparaison NUMERIQUE")
var c = neuf()
verifie(c.versionEntier("2.6.6") == 0x020606, "2.6.6 -> 0x020606")
verifie(c.versionEntier("2.12.13") == 0x020C0D, "2.12.13 -> 0x020C0D")
verifie(c.versionEntier("2.6.6") < c.versionEntier("2.12.13"), "2.6.6 < 2.12.13 (piege de la comparaison de chaines)")
verifie("2.6.6" > "2.12.13", "temoin : en chaines, 2.6.6 > 2.12.13")
for mauvaise: [nil, "", "2.6", "2.6.6.1", "a.b.c", "2..6", "300.0.0", "2.6.x", 2]
    verifie(c.versionEntier(mauvaise) == nil, "version invalide " + str(mauvaise) + " -> nil")
end

print("3. En-tete d'image (esp_app_desc_t)")
verifie(c.versionImage(ENTETE_21213) == "2.12.13", "en-tete reel -> 2.12.13")
verifie(c.versionImage(entete("2.12.6")) == "2.12.6", "en-tete 2.12.6")
var faux = ENTETE_21213.copy()  faux[0x20] = 0
verifie(c.versionImage(faux) == nil, "mauvais nombre magique -> nil")
verifie(c.versionImage(ENTETE_21213[0 .. 0x3F]) == nil, "en-tete tronque -> nil")
verifie(c.versionImage(entete("")) == nil, "version vide -> nil")
verifie(c.versionImage(entete("pas-une-v")) == nil, "version illisible -> nil")
verifie(c.versionImage(nil) == nil, "pas d'octets -> nil")

print("4. URL des fichiers")
verifie(c.urlFichier("2.12.13") == URL_21213, "URL versionnee")
verifie(c.urlFichier(nil) == URL_DEFAUT, "URL par defaut")
c = neuf({"activation": "ON", "url": "http://monserveur/copro/"})
verifie(c.urlFichier("2.12.13") == "http://monserveur/copro/v2.12.13/network_adapter_esp32c6.bin", "url du persist, '/' final retire")

print("5. Carte sans coprocesseur : rien")
HOSTED = nil
c = neuf()
verifie(tasmota.timers.contains("coprocesseur"), "lecture locale programmee au demarrage")
tasmota.declenche("coprocesseur")
verifie(c.etat == "absent" && size(tasmota.timers) == 0 && size(requetes) == 0, "Hosted inconnu -> absent, ni timer, ni requete")
c.web_sensor()
verifie(size(tasmota.envoiWeb) == 0, "pas de ligne sur l'accueil")

print("6. Version du C6 pas encore lue (0.0.0) : relu, 6 fois au plus")
HOSTED = hosted("0.0.0", "2.12.13")
c = neuf()
var n = 0
while tasmota.declenche("coprocesseur")    n += 1    end
verifie(n == 6 && c.etat == "inconnu" && size(requetes) == 0, "6 lectures puis abandon, aucune requete (" + str(n) + ")")

print("7. C6 a jour : AUCUN acces reseau")
HOSTED = hosted("2.12.13", "2.12.13")
c = neuf()
tasmota.declenche("coprocesseur")
verifie(c.etat == "aJour" && size(tasmota.timers) == 0, "a jour, plus aucun timer")
verifie(size(requetes) == 0, "aucune requete au serveur")
c.web_sensor()
verifie(size(tasmota.envoiWeb) == 0, "pas de ligne sur l'accueil")
HOSTED = hosted("2.12.14", "2.12.13")
c = neuf()
tasmota.declenche("coprocesseur")
verifie(c.etat == "aJour" && size(requetes) == 0, "C6 plus recent que l'hote -> pas d'alerte")

print("8. C6 en retard, version publiee")
HOSTED = hosted("2.6.6", "2.12.13")
SERVEUR = {URL_21213: [206, ENTETE_21213], URL_DEFAUT: [206, entete("2.12.6")]}
c = neuf()
tasmota.declenche("coprocesseur")
verifie(c.etat == "retard" && c.publiee == nil && size(requetes) == 0, "retard vu en local, serveur pas encore interroge")
verifie(journalContient("2.6.6", LOG_LEVEL_INFO), "retard journalise en info")
c.web_sensor()
verifie(contient(tasmota.envoiWeb, "/coprocesseur") && contient(tasmota.envoiWeb, "2.6.6") && contient(tasmota.envoiWeb, "2.12.13"), "ligne d'accueil : versions + lien")
verifie(contient(tasmota.envoiWeb, "non vérifiée"), "ligne : disponibilite non verifiee")
verifie(tasmota.timers.contains("coprocesseur") && tasmota.ms + tasmota.timers["coprocesseur"][0] == 180000, "requete programmee 3 min apres le demarrage")
tasmota.declenche("coprocesseur")
verifie(size(requetes) == 1 && requetes[0][0] == URL_21213, "une requete, sur l'URL versionnee")
verifie(requetes[0][1].find("Range") == "bytes=0-511", "seuls 512 octets demandes (Range)")
verifie(c.publiee == true && fermetures > 0, "publiee, client ferme")
tasmota.envoiWeb = []
c.web_sensor()
verifie(contient(tasmota.envoiWeb, "disponible") && !contient(tasmota.envoiWeb, "non vérifiée"), "ligne : disponible")
verifie(tasmota.declenche("coprocesseur") && c.versionDefaut == "2.12.6", "version du fichier par defaut lue ensuite (2.12.6)")
verifie(size(requetes) == 2 && size(tasmota.timers) == 0, "2 requetes en tout, plus aucun timer")

print("9. Page /coprocesseur puis mise a jour")
razWeb()
c.page()
var page = webserver.envoye.concat()
verifie(webserver.termine, "page terminee (content_stop)")
verifie(contient(gestionFileFolder.envoyes, "/sd/html/coprocesseur.html"), "gabarit /sd/html/coprocesseur.html envoye")
verifie(string.find(page, "window.COPRO=") > -1, "donnees de la page posees (window.COPRO)")
var debut = string.find(page, "window.COPRO=") + 13
var donnees = json.load(page[debut .. string.find(page, ";</script>", debut) - 1])
verifie(donnees != nil && donnees["c6"] == "2.6.6" && donnees["hote"] == "2.12.13" && donnees["possible"] == true && donnees["url"] == URL_21213, "donnees : versions, URL, mise a jour possible")
if SORTIE_PAGE != nil
    var f = open(SORTIE_PAGE, "w")  f.write(page)  f.close()
end
razWeb()
webserver.acces = false
c.lance()
verifie(compteCmd("HostedOta") == 0 && size(webserver.envoye) == 0, "acces refuse -> rien lance, rien envoye")
razWeb()
c.lance()
verifie(compteCmd("HostedOta ") == 1 && contient(tasmota.cmds, "HostedOta " + URL_21213), "POST -> HostedOta <URL complete>")
verifie(journalContient("HostedOta", LOG_LEVEL_INFO) || journalContient("lancee", LOG_LEVEL_INFO), "lancement journalise en info")
page = webserver.envoye.concat()
verifie(string.find(page, "\"lancee\":true") > -1, "page de retour : mise a jour lancee")
razWeb()
c.lance()
verifie(compteCmd("HostedOta ") == 1, "second POST : pas de second lancement")

print("10. C6 en retard, version PAS encore publiee (404)")
SERVEUR = {URL_21213: [404, nil]}
c = neuf()
tasmota.declenche("coprocesseur")
tasmota.declenche("coprocesseur")
verifie(c.publiee == false && size(tasmota.timers) == 0, "404 -> non publiee, pas de nouvel essai")
c.web_sensor()
verifie(contient(tasmota.envoiWeb, "pas encore publiée"), "ligne : pas encore publiee")
razWeb()
c.lance()
verifie(compteCmd("HostedOta") == 0, "POST refuse : rien lance")
razWeb()
c.page()
page = webserver.envoye.concat()
verifie(string.find(page, "\"possible\":false") > -1, "page : mise a jour impossible")

print("11. Serveur injoignable : nouvel essai toutes les heures, 6 au plus")
SERVEUR = {}
c = neuf()
tasmota.declenche("coprocesseur")
n = 0
while tasmota.declenche("coprocesseur")    n += 1    end
verifie(n == 6 && size(requetes) == 6 && c.publiee == nil, "6 essais puis abandon (" + str(n) + " essais, " + str(size(requetes)) + " requetes)")
verifie(journalContient("COPROCESSEUR_ERREUR", LOG_LEVEL_ERREUR), "echec journalise en erreur")
c.web_sensor()
verifie(contient(tasmota.envoiWeb, "non vérifiée"), "ligne : toujours non verifiee")

print("12. Exception du client web : rattrapee, nouvel essai")
SERVEUR = {URL_21213: ["exception", nil]}
c = neuf()
tasmota.declenche("coprocesseur")
var ok = true
try    tasmota.declenche("coprocesseur")    except .. as e, msg    ok = false    end
verifie(ok && c.publiee == nil && tasmota.timers.contains("coprocesseur"), "exception rattrapee, nouvel essai programme")

print("13. En-tete illisible ou d'une autre version")
SERVEUR = {URL_21213: [206, faux]}
c = neuf()
tasmota.declenche("coprocesseur")
tasmota.declenche("coprocesseur")
verifie(c.publiee == false, "en-tete illisible -> traite comme non publie")
SERVEUR = {URL_21213: [206, entete("2.12.6")]}
c = neuf()
tasmota.declenche("coprocesseur")
tasmota.declenche("coprocesseur")
verifie(c.publiee == false && journalContient("2.12.6", LOG_LEVEL_ERREUR), "fichier d'une autre version -> non publie, journalise")
SERVEUR = {URL_21213: [200, nil]}
c = neuf()
tasmota.declenche("coprocesseur")
tasmota.declenche("coprocesseur")
verifie(c.publiee == true, "200 (Range ignore) -> publie, corps non lu")

print("14. MQTT : tele/<topic>/COPROCESSEUR retenu, si \"mqtt\": \"ON\"")
import mqtt
serveur = {"coprocesseur": {"activation": "ON", "mqtt": "ON"}, "mqtt": {"topic": "SERVEUR-GARAGE"}}
var TOPIC = "tele/SERVEUR-GARAGE/COPROCESSEUR"
def dernier() return (size(mqtt.publies) > 0 ? mqtt.publies[-1] : [nil, nil, nil]) end
HOSTED = hosted("2.6.6", "2.12.13")
SERVEUR = {URL_21213: [206, ENTETE_21213], URL_DEFAUT: [206, entete("2.12.6")]}
mqtt.publies = []  mqtt.connecte = true
c = neuf({"activation": "ON", "mqtt": "ON"})
verifie(tasmota.regles.contains("Mqtt#Connected"), "regle Mqtt#Connected posee")
verifie(c.publie() == false && size(mqtt.publies) == 0, "rien avant la lecture des versions")
tasmota.declenche("coprocesseur")
var p = dernier()
var e = json.load(str(p[1]))
verifie(size(mqtt.publies) == 1 && p[0] == TOPIC && p[2] == true, "retard publie, sur le bon topic, RETENU")
verifie(e != nil && e["Version"] == "2.6.6" && e["Attendue"] == "2.12.13" && e["AJour"] == false && e["Publiee"] == nil && e["MCU"] == "esp32c6", "contenu : versions, AJour false, Publiee null")
tasmota.declenche("coprocesseur")
e = json.load(str(dernier()[1]))
verifie(size(mqtt.publies) == 2 && e["Publiee"] == true, "reponse du serveur publiee (Publiee true)")
tasmota.declenche("coprocesseur")
verifie(size(mqtt.publies) == 2, "lecture du fichier par defaut : pas de nouvelle publication")
tasmota.regles["Mqtt#Connected"](1, "Mqtt#Connected", {})
verifie(size(mqtt.publies) == 3 && dernier()[0] == TOPIC, "republie a la reconnexion au broker")
razWeb()
c.lance()
e = json.load(str(dernier()[1]))
verifie(size(mqtt.publies) == 4 && e["Lancee"] == true, "mise a jour lancee publiee")
mqtt.publies = []  mqtt.connecte = false
verifie(c.publie() == false && size(mqtt.publies) == 0, "broker deconnecte : rien, sans erreur")
mqtt.connecte = true
SERVEUR = {}
mqtt.publies = []
c = neuf({"activation": "ON", "mqtt": "ON"})
tasmota.declenche("coprocesseur")
tasmota.declenche("coprocesseur")
verifie(size(mqtt.publies) == 1, "serveur injoignable : pas de publication de plus (etat inchange)")
HOSTED = hosted("2.12.13", "2.12.13")
mqtt.publies = []
c = neuf({"activation": "ON", "mqtt": "ON"})
tasmota.declenche("coprocesseur")
e = json.load(str(dernier()[1]))
verifie(size(mqtt.publies) == 1 && e["AJour"] == true && size(requetes) == 0, "a jour : publie AJour true, toujours aucune requete")
HOSTED = nil
mqtt.publies = []
c = neuf({"activation": "ON", "mqtt": "ON"})
tasmota.declenche("coprocesseur")
verifie(size(mqtt.publies) == 0, "carte sans coprocesseur : rien publie")
HOSTED = hosted("2.6.6", "2.12.13")
mqtt.publies = []
c = neuf({"activation": "ON"})
tasmota.declenche("coprocesseur")
verifie(size(mqtt.publies) == 0 && !tasmota.regles.contains("Mqtt#Connected"), "cle mqtt absente : OFF, ni publication ni regle")
serveur = {"coprocesseur": {"activation": "ON", "mqtt": "ON"}, "mqtt": {"topic": ""}}
c = neuf({"activation": "ON", "mqtt": "ON"})
tasmota.declenche("coprocesseur")
verifie(size(mqtt.publies) == 0, "topic MQTT vide : rien publie")

print("15. Resultat de HostedOta (regle) : echec affiche, nouvel essai possible")
serveur = {"coprocesseur": {"activation": "ON", "mqtt": "ON"}, "mqtt": {"topic": "SERVEUR-GARAGE"}}
HOSTED = hosted("2.6.6", "2.12.13")
SERVEUR = {URL_21213: [206, ENTETE_21213], URL_DEFAUT: [206, entete("2.12.6")]}
mqtt.publies = []
c = neuf({"activation": "ON", "mqtt": "ON"})
verifie(tasmota.regles.contains("HostedOta") && tasmota.regles.contains("HostedLoad"), "regles HostedOta et HostedLoad posees")
tasmota.declenche("coprocesseur")
tasmota.declenche("coprocesseur")
razWeb()
c.lance()
verifie(c.lancee && string.find(c.ligne, "mise à jour en cours") > -1, "lancee : ligne d'accueil « mise a jour en cours »")
tasmota.regles["HostedOta"]("Version 2.6.6 from " + URL_21213, "HostedOta", {})
verifie(c.lancee && c.echec == nil, "reponse « Version ... from » : toujours en cours")
journal = []
tasmota.regles["HostedOta"]("Failed -1", "HostedOta", {})
verifie(!c.lancee && c.echec == "Failed -1" && c.tentatives == 1 && c.etat == "retard", "« Failed -1 » : echec retenu, plus en cours, pas bloque")
verifie(journalContient("COPROCESSEUR_ERREUR", LOG_LEVEL_ERREUR) && journalContient("Failed -1", LOG_LEVEL_ERREUR), "echec journalise en erreur, avec son code")
verifie(string.find(c.ligne, "échec de la mise à jour") > -1, "ligne d'accueil : echec")
e = json.load(str(dernier()[1]))
verifie(e["Echec"] == "Failed -1" && e["Lancee"] == false && e["Bloque"] == false, "echec publie en MQTT")
verifie(c.peutMettreAJour(), "apres un echec : bouton rendu")
razWeb()
c.page()
page = webserver.envoye.concat()
debut = string.find(page, "window.COPRO=") + 13
donnees = json.load(page[debut .. string.find(page, ";</script>", debut) - 1])
verifie(donnees["echec"] == "Failed -1" && donnees["tentatives"] == 1 && donnees["possible"] == true, "page : echec, tentatives, bouton")
if SORTIE_PAGE != nil
    var f = open(SORTIE_PAGE + ".echec.html", "w")  f.write(page)  f.close()
end
razWeb()
c.lance()
verifie(compteCmd("HostedOta ") == 2 && c.lancee && c.echec == nil, "nouvel essai : second HostedOta, echec efface")
tasmota.regles["HostedOta"]("Failed 7", "HostedOta", {})
verifie(c.echec == "Failed 7" && c.tentatives == 2, "second echec compte")
tasmota.regles["HostedLoad"]("Version 2.12.13 from /coprocessor/v2.12.13/network_adapter_esp32c6.bin", "HostedLoad", {})
verifie(c.lancee && c.echec == nil && !c.peutMettreAJour(), "HostedLoad tape en console : suivi, bouton retire pendant l'essai")
tasmota.regles["HostedLoad"]("Successful. Restarting", "HostedLoad", {})
verifie(c.lancee && c.echec == nil, "« Successful » : rien a faire, le P4 redemarre")

print("16. C6 bloque (Failed 5379, esp-hosted-mcu #143) : memorise, alerte d'accueil la 1re minute seulement")
import persist
persist.nb_save = 0
HOSTED = hosted("2.6.6", "2.12.13")
var cfg = {"activation": "ON", "mqtt": "ON"}
mqtt.publies = []
c = neuf(cfg)
tasmota.declenche("coprocesseur")
tasmota.declenche("coprocesseur")
razWeb()
c.lance()
journal = []
tasmota.regles["HostedOta"]("Failed 5379", "HostedOta", {})
verifie(c.etat == "bloque" && cfg.find("bloque") == "2.6.6" && persist.nb_save == 1, "« Failed 5379 » : etat bloque, version notee au persist, persist sauve")
verifie(!c.lancee && !c.peutMettreAJour(), "bloque : plus de bouton")
verifie(c.ligne == "", "plus d'une minute apres le demarrage : pas de ligne d'accueil")
verifie(journalContient("#143", LOG_LEVEL_ERREUR) && journalContient("flash serie", LOG_LEVEL_ERREUR), "blocage journalise en erreur (ticket, flash serie)")
e = json.load(str(dernier()[1]))
verifie(e["Bloque"] == true && e["AJour"] == false && e["Echec"] == "Failed 5379", "MQTT : Bloque true")
razWeb()
c.page()
page = webserver.envoye.concat()
debut = string.find(page, "window.COPRO=") + 13
donnees = json.load(page[debut .. string.find(page, ";</script>", debut) - 1])
verifie(donnees["etat"] == "bloque" && donnees["possible"] == false, "page : etat bloque, sans bouton")
if SORTIE_PAGE != nil
    var f = open(SORTIE_PAGE + ".bloque.html", "w")  f.write(page)  f.close()
end
razWeb()
c.lance()
verifie(compteCmd("HostedOta ") == 1, "POST alors que bloque : rien lance")
# Redemarrage : la cle du persist est relue
mqtt.publies = []
persist.nb_save = 0
c = neuf(cfg)
tasmota.declenche("coprocesseur")
verifie(c.etat == "bloque" && string.find(c.ligne, "bloqué en v2.6.6") > -1, "au demarrage suivant : bloque, ligne d'accueil (40 s)")
verifie(tasmota.timers.contains("coprocesseur") && tasmota.timers["coprocesseur"][0] == 20000, "minuterie d'effacement a 60 s du demarrage")
verifie(json.load(str(dernier()[1]))["Bloque"] == true, "MQTT au demarrage : Bloque true")
tasmota.declenche("coprocesseur")
verifie(c.ligne == "" && !tasmota.timers.contains("coprocesseur"), "a 60 s : ligne effacee, plus aucune minuterie")
verifie(size(requetes) == 0 && persist.nb_save == 0, "bloque : aucune requete au serveur, persist non reecrit")
verifie(!c.peutMettreAJour(), "bloque au demarrage : pas de bouton")
# Flash serie fait : une autre version lue sur le C6 efface la cle
HOSTED = hosted("2.9.3", "2.12.13")
c = neuf(cfg)
tasmota.declenche("coprocesseur")
verifie(cfg.find("bloque") == nil && persist.nb_save == 1 && c.etat == "retard", "C6 en autre version (2.9.3) : cle effacee, persist sauve, retard normal")
cfg["bloque"] = "2.6.6"
persist.nb_save = 0
HOSTED = hosted("2.12.13", "2.12.13")
c = neuf(cfg)
tasmota.declenche("coprocesseur")
verifie(cfg.find("bloque") == nil && persist.nb_save == 1 && c.etat == "aJour" && c.ligne == "", "C6 a jour : cle effacee, plus d'alerte")

print(echecs == 0 ? "BANC_COPROCESSEUR: OK" : "BANC_COPROCESSEUR: ECHEC (" + str(echecs) + ")")
