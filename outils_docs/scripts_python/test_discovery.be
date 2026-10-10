# Test Berry de la table de decouverte /json/discovery.json
# -----------------------------------------------------------------------------
# Charge les VRAIS udpFonctions.be, discoveryFonctions.be et rangeExtenderFonctions.be
# sous des globaux bouchonnes, et verifie les lecteurs/ecrivains de la table :
#   1-3. ImAlive (maitre) : fiche rangee sous sa MAC {MAC: {esclaveN: {...}}}, ancienne
#        entree racine purgee, message sans MAC ignore.
#   4.   Page /discovery : une entree sans bloc 'config', ou un ipMaitre vide, ne tronque plus la page.
#   5.   RoutageRangeExtender : une fiche MAC sans 'lwt' ou sans bloc 'rangeExtender' ne leve plus.
#   5 bis. redirige : RgxPort envoye une seule fois par port/IP (doublons de la table NAPT lwIP).
#   6.   Boutons RangeExtender : 'lwt'/'config'/'sensors' ne sont plus pris pour des fiches.
#   7.   Bout en bout : l'esclave ecrit sa fiche, l'envoie en UDP (forceEnvoiParams) et en MQTT ;
#        le maitre la range ; chaque champ lu par un script consommateur (CONTRAT) doit y etre.
#   11.  mqtt_discovery : discovery.json ecrit seulement si le contenu change ; 'sensors' ignore.
#   12.  lwt : la fiche retenue ne force plus "Online" (va-et-vient avec le LWT) ; purge des MAC
#        anciennes publiant la meme fiche (heure du dernier 'sensors'), effacees du broker par le maitre.
# Les lecteurs de modbusFonctions (clients TCP, IP UDP : fichesModbus) sont testes dans
# banc_test_modbus.be section 6, sur la meme forme de table.
#
# Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/test_discovery.be
# Arguments optionnels : [dossier_sources] (defaut data/fs) [dossier_bouchons]
# (defaut outils_docs/scripts_python/bouchons_berry). Temoin : lancer sur une copie de
# l'ancien code (git show <rev>:data/fs/<f>.be) -> les tests des correctifs doivent echouer.
# Derniere ligne : TEST_DISCOVERY: OK|ECHEC.
#
# Portee : logique de la table seulement. Ne teste NI l'emission UDP reelle, NI MQTT,
# NI le rendu HTML. Ne remplace pas l'observation apres flash.

import global
import sys
import string
import json
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(size(global._argv) > 2 ? global._argv[2] : "outils_docs/scripts_python/bouchons_berry")

# --- globaux fournis par le firmware sur l'appareil, bouchonnes ici ---
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var journal = []
def log(m, l) journal.push(str(m)) end
class TasmotaStub
  var cmds                             # commandes passees a tasmota.cmd
  var rgxClients                       # reponse de RgxClients, pilotee par le test
  var statusNet                        # reponse de Status 5, pilotee par le test (role joue)
  var rgxRefus                         # true : RgxPort repond "ERROR" (table NAPT pleine)
  def init()
    self.cmds = []
    self.rgxRefus = false
    self.rgxClients = {}
    self.statusNet = {"IPAddress": "192.168.0.43", "Mac": "AA:AA:AA:AA:AA:00", "Hostname": "SERVEUR-GARAGE"}
  end
  def yield() end
  def rtc() return {"utc": 1790000000, "local": 1790000000} end
  def cmd(c, m)
    self.cmds.push(c)
    if c == "Status 5"      return {"StatusNET": self.statusNet}    end
    if c == "RgxClients"    return {"RgxClients": self.rgxClients}    end
    # RgxPort repond en texte, pas en JSON : tasmota.cmd renvoie alors la chaine telle quelle
    if string.find(c, "RgxPort") == 0    return self.rgxRefus ? "ERROR" : "OK TCP 192.168.0.43:8081 -> 192.168.4.2:80"    end
    return {}
  end
  def resp_cmnd(x) end
  def add_rule(a, b, c) end              # controleRangeExtender (section 14)
  def add_cmd(a, b) end
  # Timers en attente : memes regles que tasmota_class.be (set_timer EMPILE, remove_timer
  # retire tous ceux de cet id)
  var timers
  def set_timer(a, b, c)    if self.timers == nil  self.timers = []  end    self.timers.push(c)    end
  def remove_timer(id)
    if self.timers == nil    return    end
    var i = 0
    while i < size(self.timers)    if self.timers[i] == id  self.timers.remove(i)  else  i += 1  end    end
  end
  def nbTimers(id)
    var n = 0
    for t: (self.timers == nil ? [] : self.timers)    if t == id  n += 1  end    end
    return n
  end
end
var tasmota = TasmotaStub()
class Driver end                       # classe de base des drivers Tasmota (section 14)
var envois = []                        # datagrammes UDP qui seraient partis
class udp
  def begin(a, b) return true end
  def begin_multicast(a, b) return true end
  def send(ip, port, b) envois.push(b.asstring()) return true end
  def send_multicast(b) envois.push(b.asstring()) return true end
  def close() end
end
var boolMute = true
var serveur = {"udp": {"id": 0, "debug": "ON", "activation": "ON"},
               "rangeExtender": {"activation": "ON", "id": 0, "debug": "ON"},
               "discovery": {"debug": "ON"},
               "mqtt": {"topic": "garage", "groupTopic1": "tasmotas/garage"},
               "hostname": "SERVEUR-GARAGE"}
var drivers = {"ModBus": {"id": 0}}
var diverses = {"telePeriod": 300}
var udpFonctions = nil                 # (re)affectes par les fichiers charges
var discoveryFonctions = nil
var rangeExtenderFonctions = nil
var configGlobal = nil
var logFonctions = nil                 # la VRAIE fonction de log commune (seuil par cible)
var modules = {}                       # lu par logFonctions (cibles garage, cuve)

# --- charge les vrais modules ---
print(">>> sources testees :", SOURCES)
def charge(nom)
  var f = open(SOURCES + "/" + nom + ".be", "r")
  var src = f.read()
  f.close()
  compile(src)()
end
charge("logFonctions")
charge("udpFonctions")
charge("discoveryFonctions")
charge("rangeExtenderFonctions")
import gestionFileFolder
import webserver
import mqtt
gestionFileFolder.contenu = false      # fichier absent -> false, comme le vrai readFile

# --- mini-harnais d'assertions ---
var total = 0
var echecs = 0
def verifie(nom, attendu, obtenu)
  total += 1
  var ok = (attendu == obtenu)
  if !ok    echecs += 1    end
  print(string.format("[%s] %-52s attendu=%s  obtenu=%s", ok ? "PASS" : "FAIL", nom, str(attendu), str(obtenu)))
end
# Appelle fn() : "OK", ou "EXCEPTION <type> <message>" si elle leve
def essaie(fn)
  try
    fn()
    return "OK"
  except .. as e, m
    return "EXCEPTION " + str(e) + " " + str(m)
  end
end
def table() return json.load(gestionFileFolder.fichiers.find("/json/discovery.json", "null")) end
def journalise(motif)
  for l: journal    if string.find(l, motif) >= 0    return true    end    end
  return false
end

var MAC_CUVE = "E8:06:90:11:22:33"
var CLE_CUVE = "E80690112233"          # forme des cles de la table ET de RgxClients (xdrv_58:193)
# Fiche d'esclave telle que discoveryFonctions.changementEtatDemarrage la construit
def ficheCuve(avecMac)
  var r = {"id": 2, "nom": "Capteurs de Cuve", "IPAddress": "192.168.4.2", "host": "CAPTEURS-CUVE.local",
           "topic": "jardin/cuve", "typeReglageHeure": "UDP", "typeConnection": "RangeExtender",
           "rangeExtender": {"activation": "ON", "id": 2, "routagePort": 8081, "ipMaitre": "192.168.0.43"},
           "ModBus": {"activation": "ON", "id": 2, "UDP": {"activation": "ON", "IPAddress": "192.168.4.2"}}}
  if avecMac    r["adresseMAC"] = MAC_CUVE    end
  return {"esclave2": r}
end
# Bloc 'config' de la decouverte MQTT native de Tasmota (sous-ensemble utile)
def configCuve() return {"dn": "Capteurs de Cuve", "ip": "192.168.4.2", "hn": "CAPTEURS-CUVE", "t": "jardin/cuve"} end
# Payload tel que controleUDP le rejoue apres reception du message de l'esclave (forceEnvoiParams)
def imAlive(fiche) return udpFonctions.reglageUDP("ReglageUDP", 0, "ImAlive " + json.dump(fiche), nil) end

print("")
print("=== 1. ImAlive, table absente ===")
gestionFileFolder.fichiers = {}
verifie("ImAlive ne leve pas", "OK", essaie(def () imAlive(ficheCuve(true)) end))
var t = table()
verifie("fiche rangee sous la MAC", true, t != nil && t.contains(CLE_CUVE) && isinstance(t[CLE_CUVE], map) && t[CLE_CUVE].contains("esclave2"))
verifie("aucune entree racine 'esclave2'", false, t != nil && t.contains("esclave2"))
verifie("esclave marque Online (vu en UDP)", "Online", (t != nil && t.contains(CLE_CUVE)) ? t[CLE_CUVE].find("lwt") : nil)
verifie("heure + ipMaitre renvoyes (typeReglageHeure UDP)", 2, size(envois))

print("")
print("=== 2. ImAlive, table deja remplie par MQTT + ancienne entree racine ===")
var init2 = {}
init2[CLE_CUVE] = {"config": configCuve(), "lwt": "Online"}
init2["esclave2"] = ficheCuve(true)["esclave2"]
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init2)}
verifie("ImAlive ne leve pas", "OK", essaie(def () imAlive(ficheCuve(true)) end))
t = table()
verifie("config MQTT preservee", "Capteurs de Cuve", t[CLE_CUVE].find("config", {}).find("dn"))
verifie("lwt MQTT preserve", "Online", t[CLE_CUVE].find("lwt"))
verifie("role ajoute a la fiche MAC", true, t[CLE_CUVE].contains("esclave2"))
verifie("ancienne entree racine purgee", false, t.contains("esclave2"))

print("")
print("=== 3. ImAlive sans MAC : ignore, table intacte ===")
var avant = gestionFileFolder.fichiers["/json/discovery.json"]
journal = []
verifie("ImAlive sans MAC ne leve pas", "OK", essaie(def () imAlive(ficheCuve(false)) end))
verifie("table inchangee", true, avant == gestionFileFolder.fichiers["/json/discovery.json"])
verifie("rejet journalise", true, journalise("sans adresse MAC"))

print("")
print("=== 4. Page /discovery avec entrees sans 'config' ===")
var init4 = {}
init4["esclave2"] = ficheCuve(true)["esclave2"]
init4["AAAAAAAAAA01"] = {"config": {"dn": "Serveur", "ip": "192.168.0.43", "hn": "SERVEUR-GARAGE", "t": "garage"}, "lwt": "Online",
                         "maitre": {"id": 0, "nom": "Serveur", "IPAddress": "192.168.0.43"}}
init4["BBBBBBBBBB02"] = ficheCuve(true)
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init4), "/sd/css/main.css": ""}
webserver.envoye = []
webserver.termine = false
verifie("page ne leve pas", "OK", essaie(def () discoveryFonctions.affichePageDiscovery() end))
verifie("page terminee (content_stop)", true, webserver.termine)
var boutons = 0
for s: webserver.envoye    if string.find(s, "<button class='button") >= 0    boutons += 1    end    end
verifie("1 bouton (seule l'entree avec config)", 1, boutons)
# Esclave RangeExtender qui n'a pas encore recu l'IP du maitre (ipMaitre vide)
var ficheSansIpMaitre = ficheCuve(true)
ficheSansIpMaitre["esclave2"]["rangeExtender"]["ipMaitre"] = ""
ficheSansIpMaitre["config"] = configCuve()
var init4b = {}
init4b[CLE_CUVE] = ficheSansIpMaitre
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init4b), "/sd/css/main.css": ""}
webserver.envoye = []
webserver.termine = false
discoveryFonctions.affichePageDiscovery()
verifie("page terminee malgre ipMaitre vide", true, webserver.termine)

print("")
print("=== 5. RoutageRangeExtender : fiche MAC sans lwt ===")
var init5 = {}
init5[CLE_CUVE] = ficheCuve(true)
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init5)}
tasmota.cmds = []
verifie("routage ne leve pas (fiche sans lwt)", "OK", essaie(def () rangeExtenderFonctions.routageRangeExtender("RoutageRangeExtender", 2, "", nil) end))
verifie("aucun routage sans lwt Online", 0, size(tasmota.cmds))
init5[CLE_CUVE]["lwt"] = "Online"
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init5)}
rangeExtenderFonctions.etat()["redirections"] = {}   # deja posee par la page /discovery (section 4)
tasmota.cmds = []
essaie(def () rangeExtenderFonctions.routageRangeExtender("RoutageRangeExtender", 2, "", nil) end)
# NB : list.find(x) cherche la VALEUR x, pas l'indice -> acces par [0]
verifie("routage pose si lwt Online (non-regression)", "RgxPort tcp, 8081, 192.168.4.2, 80", size(tasmota.cmds) > 0 ? tasmota.cmds[0] : nil)
# Module sans RangeExtender (pas de bloc 'rangeExtender') mais Online : pas de port de routage
init5[CLE_CUVE]["esclave2"].remove("rangeExtender")
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init5)}
tasmota.cmds = []
verifie("esclave sans bloc rangeExtender : sans exception", "OK", essaie(def () rangeExtenderFonctions.routageRangeExtender("RoutageRangeExtender", 2, "", nil) end))
verifie("esclave sans bloc rangeExtender : pas de routage", 0, size(tasmota.cmds))

print("")
print("=== 5 bis. Redirection NAPT posee une seule fois (doublons lwIP) ===")
rangeExtenderFonctions.etat()["redirections"] = {}
tasmota.cmds = []
verifie("1re redirection posee", true, rangeExtenderFonctions.redirige(8081, "192.168.4.2"))
verifie("RgxPort envoye une fois", 1, size(tasmota.cmds))
verifie("2e appel, meme IP : en place", true, rangeExtenderFonctions.redirige(8081, "192.168.4.2"))
verifie("2e appel : pas de RgxPort (pas de doublon)", 1, size(tasmota.cmds))
verifie("port en chaine : reconnu comme deja pose", true, rangeExtenderFonctions.redirige("8081", "192.168.4.2"))
verifie("port en chaine : pas de RgxPort", 1, size(tasmota.cmds))
verifie("IP changee : redirection reposee", true, rangeExtenderFonctions.redirige(8081, "192.168.4.3"))
verifie("IP changee : RgxPort envoye", 2, size(tasmota.cmds))
tasmota.rgxRefus = true
journal = []
verifie("table pleine : redirection refusee", false, rangeExtenderFonctions.redirige(8082, "192.168.4.4"))
verifie("refus non memorise", nil, rangeExtenderFonctions.etat()["redirections"].find(8082))
verifie("refus journalise", true, journalise("REFUSEE"))
tasmota.rgxRefus = false
tasmota.cmds = []
verifie("apres un refus : nouvel essai au prochain affichage", true, rangeExtenderFonctions.redirige(8082, "192.168.4.4"))
verifie("apres un refus : RgxPort renvoye", 1, size(tasmota.cmds))
rangeExtenderFonctions.etat()["redirections"] = {}   # section 6 verifie un RgxPort neuf

print("")
print("=== 6. Boutons RangeExtender : fiche MAC complete (config, sensors, lwt) ===")
var init6 = ficheCuve(true)
init6["config"] = configCuve()
init6["sensors"] = {"sn": {"Time": "2026-09-30T12:00:00"}}
init6["lwt"] = "Online"
var table6 = {}
table6[CLE_CUVE] = init6
table6["AAAAAAAAAA01"] = {"maitre": {"id": 0, "nom": "Serveur", "IPAddress": "192.168.0.43"}, "lwt": "Online"}
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(table6)}
tasmota.rgxClients = {}
tasmota.rgxClients[CLE_CUVE] = {"IPAddress": "192.168.4.2", "RSSI": -60}
tasmota.cmds = []
webserver.envoye = []
verifie("boutons ne levent pas (lwt chaine dans la fiche)", "OK", essaie(def () rangeExtenderFonctions.afficheBoutonsModulesEsclaves() end))
verifie("1 bouton pour l'esclave connecte", 1, size(webserver.envoye))
verifie("routage NAPT pose pour l'esclave", true, tasmota.cmds.find("RgxPort tcp, 8081, 192.168.4.2, 80") != nil)
init6["lwt"] = "Offline"
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(table6)}
webserver.envoye = []
essaie(def () rangeExtenderFonctions.afficheBoutonsModulesEsclaves() end)
verifie("aucun bouton si l'esclave est Offline", 0, size(webserver.envoye))
gestionFileFolder.fichiers = {}
verifie("table absente : ne leve pas", "OK", essaie(def () rangeExtenderFonctions.afficheBoutonsModulesEsclaves() end))

print("")
print("=== 7. Bout en bout : fiche ecrite par l'esclave -> UDP et MQTT -> table du maitre ===")
# Contrat : chaque champ lu par un script consommateur doit arriver dans la table du maitre,
# par les DEUX canaux (UDP ImAlive et decouverte MQTT retenue). Chemins relatifs a la fiche.
var CONTRAT = {
  "adresseMAC": "ImAlive (rangement sous la MAC), boutons RangeExtender (RgxClients)",
  "nom": "ImAlive, routage et boutons RangeExtender",
  "typeReglageHeure": "ImAlive (renvoi de l'heure et de ipMaitre)",
  "IPAddress": "IP UDP (fichesModbus), routage NAPT",
  "groupTopic": "fichesModbus (filtre par groupe)",
  "ModBus/id": "fichesModbus (client TCP, IP UDP)",
  "ModBus/TCP/IPAddress": "client TCP du maitre (ReglageModbus ImAlive)",
  "ModBus/UDP/IPAddress": "voie UDP ModBus",
  "rangeExtender/activation": "page /discovery",
  "rangeExtender/id": "page /discovery",
  "rangeExtender/routagePort": "routage NAPT, boutons, page",
  "rangeExtender/ipMaitre": "page /discovery (port distant)"
}
def champ(fiche, chemin)
  var v = fiche
  for k : string.split(chemin, "/")
    if !isinstance(v, map)    return nil    end
    v = v.find(k, nil)
  end
  return v
end
def verifieContrat(canal, fiche)
  var manquants = []
  for chemin : CONTRAT.keys()    if champ(fiche, chemin) == nil    manquants.push(chemin)    end    end
  verifie(canal + " : champs necessaires aux lecteurs", "[]", str(manquants))
end

# --- cote ESCLAVE (cuve : id 2, RangeExtender esclave, ModBus serie + UDP + TCP) ---
serveur = {"adresseMAC": "", "nom": "Capteurs de Cuve", "IP": {"IPAddress": "0.0.0.0"}, "hostname": "CAPTEURS-CUVE",
           "udp": {"id": 2, "activation": "ON", "debug": "ON"},
           "rangeExtender": {"activation": "ON", "id": 2, "ipMaitre": "192.168.0.43", "debug": "ON"},
           "mqtt": {"topic": "jardin/cuve", "groupTopic1": "tasmotas/garage"}, "discovery": {"debug": "ON"}}
drivers = {"ModBus": {"activation": "ON", "id": 2, "debit": 19200, "mode": "8N1", "timeoutReponse": 5000,
                      "typeComm": {"Serial": "ON", "UDP": "ON", "TCP": "ON", "MQTT": "OFF"}}}
diverses = {"telePeriod": 300, "fuseauHoraire": {"typeReglageHeure": "UDP"}}
tasmota.statusNet = {"IPAddress": "192.168.4.2", "Mac": MAC_CUVE, "Hostname": "CAPTEURS-CUVE"}
gestionFileFolder.fichiers = {}
verifie("esclave : ecriture de sa fiche (Wifi#Connected)", "OK",
        essaie(def () discoveryFonctions.changementEtatDemarrage({"Connected": 1}, "Wifi", {"WIFI": {"Connected": 1}}) end))
t = table()
var ficheLocale = (t != nil) ? champ(t, CLE_CUVE + "/esclave2") : nil
verifie("esclave : cle MAC au format RgxClients (12 hexa)", true, t != nil && t.contains(CLE_CUVE))
verifieContrat("fiche locale", ficheLocale)
verifie("groupTopic = groupTopic1 du persist", "tasmotas/garage", champ(ficheLocale, "groupTopic"))
verifie("IPAddress = IP reelle (DHCP du point d'acces)", "192.168.4.2", champ(ficheLocale, "IPAddress"))

# Canal UDP : forceEnvoiParams (methode d'envoi inchangee : multicast esclave)
envois = []
essaie(def () udpFonctions.reglageUDP("ReglageUDP", 0, "forceEnvoiParams ON", nil) end)
verifie("esclave : 1 datagramme ImAlive emis", 1, size(envois))
var msgUDP = size(envois) > 0 ? envois[0] : ""
# controleUDP rejoue la commande qui suit le topic : "ReglageUDP ImAlive {...}"
var posCmd = string.find(msgUDP, "ReglageUDP ")
var payloadUDP = posCmd >= 0 ? msgUDP[posCmd + size("ReglageUDP ") ..] : ""

# Canal MQTT : publication retenue sur tasmota/discovery/<MAC>/<role>
mqtt.publies = []
essaie(def () discoveryFonctions.changementEtatDemarrage({"Connected": 1}, "Mqtt", {"MQTT": {"Connected": 1}}) end)
verifie("esclave : fiche publiee (retenue) en MQTT", "tasmota/discovery/" + CLE_CUVE + "/esclave2 retain=true",
        size(mqtt.publies) > 0 ? mqtt.publies[0][0] + " retain=" + str(mqtt.publies[0][2]) : "rien")
var pubMQTT = size(mqtt.publies) > 0 ? mqtt.publies[0] : ["", "null"]

# --- cote MAITRE (P4 : id 0, RangeExtender maitre) : table vierge, reception par chaque canal ---
serveur = {"adresseMAC": "AA:AA:AA:AA:AA:00", "nom": "Serveur de Garage", "IP": {"IPAddress": "192.168.0.43"}, "hostname": "SERVEUR-GARAGE",
           "udp": {"id": 0, "activation": "ON", "debug": "ON"},
           "rangeExtender": {"activation": "ON", "id": 0, "debug": "ON"},
           "mqtt": {"topic": "garage", "groupTopic1": "tasmotas/garage"}, "discovery": {"debug": "ON"}}
drivers = {"ModBus": {"id": 0}}
tasmota.statusNet = {"IPAddress": "192.168.0.43", "Mac": "AA:AA:AA:AA:AA:00", "Hostname": "SERVEUR-GARAGE"}

gestionFileFolder.fichiers = {}
verifie("maitre : reception UDP ImAlive", "OK", essaie(def () udpFonctions.reglageUDP("ReglageUDP", 0, payloadUDP, nil) end))
t = table()
verifieContrat("recu par UDP", t != nil ? champ(t, CLE_CUVE + "/esclave2") : nil)

gestionFileFolder.fichiers = {}
verifie("maitre : reception MQTT discovery", true, essaie(def () discoveryFonctions.mqtt_discovery(pubMQTT[0], 0, pubMQTT[1], nil) end) == "OK")
t = table()
verifieContrat("recu par MQTT", t != nil ? champ(t, CLE_CUVE + "/esclave2") : nil)

print("")
print("=== 8. Fiche perimee sous notre MAC (carte reaffectee maitre -> esclave2) ===")
# Cas reel du 2026-10-03 : le broker retenait tasmota/discovery/<MAC>/maitre (ancienne
# identite SERVEUR-RLY-CAVE) ; l'esclave la rangeait et l'annoncait au maitre par ImAlive.
var ficheMaitrePerimee = {"id": 0, "nom": "Serveur Relais Cave", "typeReglageHeure": "NTP", "adresseMAC": MAC_CUVE}
var topicPerime = "tasmota/discovery/" + CLE_CUVE + "/maitre"
def tableAvecPerimee()
  var t0 = {}
  t0[CLE_CUVE] = {"maitre": ficheMaitrePerimee, "esclave2": ficheCuve(true)["esclave2"]}
  gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(t0)}
end

# --- cote ESCLAVE : il recoit l'ancienne fiche retenue a sa reconnexion MQTT ---
serveur = {"adresseMAC": MAC_CUVE, "nom": "Capteurs de Cuve", "IP": {"IPAddress": "192.168.4.2"}, "hostname": "CAPTEURS-CUVE",
           "udp": {"id": 2, "activation": "ON", "debug": "ON"},
           "rangeExtender": {"activation": "ON", "id": 2, "ipMaitre": "192.168.0.43", "debug": "ON"},
           "mqtt": {"topic": "jardin/cuve", "groupTopic1": "tasmotas/garage"}, "discovery": {"debug": "ON"}}
tableAvecPerimee()
mqtt.publies = []
verifie("esclave : reception de sa fiche perimee", "OK", essaie(def () discoveryFonctions.mqtt_discovery(topicPerime, 0, json.dump(ficheMaitrePerimee), nil) end))
verifie("esclave : effacement retenu publie sur le broker", topicPerime + " '' retain=true",
        size(mqtt.publies) == 1 ? mqtt.publies[0][0] + " '" + mqtt.publies[0][1] + "' retain=" + str(mqtt.publies[0][2]) : str(mqtt.publies))
t = table()
verifie("esclave : fiche perimee retiree de discovery.json", false, t[CLE_CUVE].contains("maitre"))
verifie("esclave : sa fiche actuelle conservee", true, t[CLE_CUVE].contains("esclave2"))

# Il recoit ensuite son propre message d'effacement (abonne a tasmota/discovery/+/#) : rien ne casse
mqtt.publies = []
verifie("esclave : reception de l'effacement", "OK", essaie(def () discoveryFonctions.mqtt_discovery(topicPerime, 0, "", nil) end))
verifie("esclave : pas de nouvelle publication", 0, size(mqtt.publies))

# Sa fiche ACTUELLE n'est jamais effacee
mqtt.publies = []
essaie(def () discoveryFonctions.mqtt_discovery("tasmota/discovery/" + CLE_CUVE + "/esclave2", 0, json.dump(ficheCuve(true)["esclave2"]), nil) end)
verifie("esclave : fiche du role actuel non effacee", 0, size(mqtt.publies))
verifie("esclave : fiche du role actuel toujours rangee", true, table()[CLE_CUVE].contains("esclave2"))

# Le 'maitre' d'une AUTRE MAC n'est pas perime pour nous
mqtt.publies = []
essaie(def () discoveryFonctions.mqtt_discovery("tasmota/discovery/AAAAAAAAAA00/maitre", 0, json.dump({"id": 0, "nom": "Serveur de Garage"}), nil) end)
verifie("esclave : maitre d'une autre MAC conserve", true, table().find("AAAAAAAAAA00", {}).contains("maitre"))
verifie("esclave : ... et non efface sur le broker", 0, size(mqtt.publies))

# ImAlive apres nettoyage : annonce la fiche esclave2, plus la fiche perimee
tableAvecPerimee()
essaie(def () discoveryFonctions.mqtt_discovery(topicPerime, 0, json.dump(ficheMaitrePerimee), nil) end)
envois = []
essaie(def () udpFonctions.reglageUDP("ReglageUDP", 0, "forceEnvoiParams ON", nil) end)
var msgApres = size(envois) > 0 ? envois[0] : ""
verifie("esclave : ImAlive porte esclave2 (plus maitre)", true,
        string.find(msgApres, '"esclave2"') >= 0 && string.find(msgApres, '"maitre"') < 0)

# --- cote MAITRE : il recoit l'effacement et purge sa copie ---
serveur = {"adresseMAC": "AA:AA:AA:AA:AA:00", "nom": "Serveur de Garage", "IP": {"IPAddress": "192.168.0.43"}, "hostname": "SERVEUR-GARAGE",
           "udp": {"id": 0, "activation": "ON", "debug": "ON"},
           "rangeExtender": {"activation": "ON", "id": 0, "debug": "ON"},
           "mqtt": {"topic": "garage", "groupTopic1": "tasmotas/garage"}, "discovery": {"debug": "ON"}}
tableAvecPerimee()
mqtt.publies = []
verifie("maitre : reception de l'effacement", "OK", essaie(def () discoveryFonctions.mqtt_discovery(topicPerime, 0, "", nil) end))
t = table()
verifie("maitre : fiche perimee retiree de sa copie", false, t[CLE_CUVE].contains("maitre"))
verifie("maitre : fiche esclave2 conservee", true, t[CLE_CUVE].contains("esclave2"))
verifie("maitre : ne publie rien", 0, size(mqtt.publies))

print("")
print("=== 9. forceEnvoiParams : une seule chaine de timers ===")
# Avant : timer sans id -> chaque appel manuel ajoutait une chaine d'envois periodiques.
serveur = {"adresseMAC": MAC_CUVE, "nom": "Capteurs de Cuve", "IP": {"IPAddress": "192.168.4.2"}, "hostname": "CAPTEURS-CUVE",
           "udp": {"id": 2, "activation": "ON", "debug": "ON"},
           "rangeExtender": {"activation": "ON", "id": 2, "ipMaitre": "192.168.0.43", "debug": "ON"},
           "mqtt": {"topic": "jardin/cuve", "groupTopic1": "tasmotas/garage"}, "discovery": {"debug": "ON"}}
tasmota.timers = []
for i: 1 .. 3
  essaie(def () udpFonctions.reglageUDP("ReglageUDP", 0, "forceEnvoiParams ON", nil) end)
end
verifie("3 appels -> 1 seul timer en attente", 1, size(tasmota.timers))
verifie("... et il porte l'id 'forceEnvoiParams'", 1, tasmota.nbTimers("forceEnvoiParams"))

print("")
print("=== 10. forceEnvoiParams : n'annonce que le role du persist ===")
# Sans passer par MQTT (esclave qui n'atteint pas le broker) : la fiche perimee reste dans
# la table locale. Elle est placee AVANT esclave2 pour que l'ancien code (1re cle) la prenne.
var tPerimee = {}
tPerimee[CLE_CUVE] = {"maitre": ficheMaitrePerimee, "esclave2": ficheCuve(true)["esclave2"]}
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(tPerimee)}
envois = []
essaie(def () udpFonctions.reglageUDP("ReglageUDP", 0, "forceEnvoiParams ON", nil) end)
var imA = size(envois) > 0 ? envois[0] : ""
var posJson = string.find(imA, "ImAlive ")
var ficheEnvoyee = posJson >= 0 ? json.load(imA[posJson + size("ImAlive ") ..]) : nil
verifie("table avec fiche perimee : 1 ImAlive", 1, size(envois))
var rolesEnvoyes = []
if ficheEnvoyee != nil    for k: ficheEnvoyee.keys()    rolesEnvoyes.push(k)    end    end
verifie("... qui ne porte QUE esclave2", "['esclave2']", str(rolesEnvoyes))

# Sa propre fiche absente : rien n'est envoye (avant : 'ImAlive {}', rejete par le maitre)
var tSansFiche = {}
tSansFiche[CLE_CUVE] = {"maitre": ficheMaitrePerimee}
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(tSansFiche)}
envois = []
essaie(def () udpFonctions.reglageUDP("ReglageUDP", 0, "forceEnvoiParams ON", nil) end)
verifie("fiche esclave2 absente : aucun ImAlive", 0, size(envois))

print("")
print("=== 11. mqtt_discovery : ecriture seulement si le contenu change ===")
# Avant (constate sur la cuve le 2026-10-05) : 'jsonDiscovery != json.load(...)' compare des
# OBJETS map, toujours differents -> discovery.json reecrit a CHAQUE message retenu recu a la
# connexion MQTT, 'sensors' compris (heure et temperatures changent a chaque publication).
import introspect
var mv = introspect.get(discoveryFonctions, "memeValeur")      # nil sur l'ancien code (temoin)
verifie("memeValeur : maps imbriquees egales", true, mv != nil && mv({"a": {"b": [1, {"c": "x"}]}}, {"a": {"b": [1, {"c": "x"}]}}))
verifie("memeValeur : valeur differente", false, mv != nil && mv({"a": 1}, {"a": 2}))
verifie("memeValeur : cle en plus", false, mv != nil && mv({"a": 1}, {"a": 1, "b": 2}))
verifie("memeValeur : 1 et \"1\" differents", false, mv != nil && mv({"a": 1}, {"a": "1"}))

var nbEcritures = 0
var ecritOrigine = gestionFileFolder.writeFile
gestionFileFolder.writeFile = def (chemin, data) nbEcritures += 1    ecritOrigine(chemin, data) end
gestionFileFolder.fichiers = {}
var topicCfg = "tasmota/discovery/AAAAAAAAAA01/config"
var cfgPorte = {"ip": "192.168.0.45", "dn": "Porte de Cave", "hn": "PORTE-CAVE", "t": "cave/porte", "fn": ["Lumiere", nil]}
essaie(def () discoveryFonctions.mqtt_discovery(topicCfg, 0, json.dump(cfgPorte), nil) end)
verifie("1re fiche config : 1 ecriture", 1, nbEcritures)
nbEcritures = 0
essaie(def () discoveryFonctions.mqtt_discovery(topicCfg, 0, json.dump(cfgPorte), nil) end)
verifie("meme fiche renvoyee (retenue) : 0 ecriture", 0, nbEcritures)
cfgPorte["ip"] = "192.168.0.46"
nbEcritures = 0
essaie(def () discoveryFonctions.mqtt_discovery(topicCfg, 0, json.dump(cfgPorte), nil) end)
verifie("fiche config modifiee : 1 ecriture", 1, nbEcritures)
verifie("... nouvelle IP rangee", "192.168.0.46", table().find("AAAAAAAAAA01", {}).find("config", {}).find("ip"))
nbEcritures = 0
essaie(def () discoveryFonctions.mqtt_discovery(topicCfg, 0, "pas du json", nil) end)
verifie("charge illisible : 0 ecriture, sans exception", 0, nbEcritures)
nbEcritures = 0
essaie(def () discoveryFonctions.mqtt_discovery("tasmota/discovery/AAAAAAAAAA01/sensors", 0, '{"sn":{"Time":"2026-10-05T10:00:00"},"ver":1}', nil) end)
verifie("'sensors' : 0 ecriture", 0, nbEcritures)
verifie("'sensors' : non range", false, table().find("AAAAAAAAAA01", {}).contains("sensors"))
gestionFileFolder.writeFile = ecritOrigine

print("")
print("=== 12. Va-et-vient lwt et purge des MAC anciennes (meme fiche) ===")
# Constate le 2026-10-05 : (a) chaque fiche 'config' retenue forcait lwt=Online, le LWT retenu
# 'Offline' le remettait aussitot -> 2 ecritures par module hors ligne a chaque reconnexion ;
# (b) 3 MAC 'RIDEAU-GARAGE' (cartes remplacees) se chassaient de la table a chaque reconnexion.
serveur = {"adresseMAC": "58:8C:81:5B:56:40", "nom": "Serveur de Garage", "IP": {"IPAddress": "192.168.0.43"}, "hostname": "SERVEUR-GARAGE",
           "udp": {"id": 0, "activation": "ON", "debug": "ON"},
           "rangeExtender": {"activation": "ON", "id": 0, "debug": "ON"},
           "mqtt": {"topic": "garage", "groupTopic1": "tasmotas/garage"}, "discovery": {"debug": "ON"}}
gestionFileFolder.writeFile = def (chemin, data) nbEcritures += 1    ecritOrigine(chemin, data) end
gestionFileFolder.fichiers = {}
discoveryFonctions.etat()["heuresSensors"] = {}
def disc(mac, type, charge) essaie(def () discoveryFonctions.mqtt_discovery("tasmota/discovery/" + mac + "/" + type, 0, charge, nil) end) end
def cfgRideau() return json.dump({"ip": "192.168.4.3", "dn": "Rideau de garage", "hn": "RIDEAU-GARAGE", "t": "garage/rideau"}) end
def releve(heure) return json.dump({"sn": {"Time": heure, "Switch1": "OFF"}, "ver": 1}) end

# (a) va-et-vient lwt
disc("CCCCCCCCCC01", "config", json.dump({"ip": "192.168.0.50", "dn": "Volet", "hn": "VR-PORTE", "t": "volet/entree"}))
verifie("fiche neuve : lwt pose a Online", "Online", table().find("CCCCCCCCCC01", {}).find("lwt"))
essaie(def () discoveryFonctions.mqtt_lwt("tele/volet/entree/LWT", 0, "Offline", nil) end)
verifie("LWT retenu Offline applique", "Offline", table().find("CCCCCCCCCC01", {}).find("lwt"))
nbEcritures = 0
disc("CCCCCCCCCC01", "config", json.dump({"ip": "192.168.0.50", "dn": "Volet", "hn": "VR-PORTE", "t": "volet/entree"}))
verifie("fiche retenue rejouee : 0 ecriture", 0, nbEcritures)
verifie("... lwt reste Offline (le topic LWT decide)", "Offline", table().find("CCCCCCCCCC01", {}).find("lwt"))

# (b) purge : 3 MAC, meme fiche ; le maitre efface les anciennes du broker
disc("DDDDDDDDDD01", "config", cfgRideau())
disc("DDDDDDDDDD02", "config", cfgRideau())
disc("DDDDDDDDDD03", "config", cfgRideau())
disc("DDDDDDDDDD03", "esclave3", json.dump({"id": 3, "nom": "Rideau de garage"}))
verifie("3 fiches rideau toutes rangees (plus de chasse mutuelle)", 3,
        (table().contains("DDDDDDDDDD01") ? 1 : 0) + (table().contains("DDDDDDDDDD02") ? 1 : 0) + (table().contains("DDDDDDDDDD03") ? 1 : 0))
mqtt.publies = []
disc("DDDDDDDDDD01", "sensors", releve("2025-12-23T14:40:53"))
verifie("1er releve seul : aucune purge", true, table().contains("DDDDDDDDDD01"))
disc("DDDDDDDDDD02", "sensors", releve("2026-03-11T13:25:38"))
verifie("releve plus recent : la MAC ancienne quitte la table", false, table().contains("DDDDDDDDDD01"))
verifie("... ses messages retenus effaces (config + sensors)", "tasmota/discovery/DDDDDDDDDD01/config '' true|tasmota/discovery/DDDDDDDDDD01/sensors '' true",
        size(mqtt.publies) == 2 ? mqtt.publies[0][0] + " '" + mqtt.publies[0][1] + "' " + str(mqtt.publies[0][2]) + "|" + mqtt.publies[1][0] + " '" + mqtt.publies[1][1] + "' " + str(mqtt.publies[1][2]) : str(mqtt.publies))
verifie("... purge journalisee", true, journalise("DISCOVERY_PURGE"))
mqtt.publies = []
disc("DDDDDDDDDD03", "sensors", releve("2026-05-22T03:04:26"))
verifie("la plus recente reste", true, table().contains("DDDDDDDDDD03") && table()["DDDDDDDDDD03"].contains("esclave3"))
verifie("la 2e ancienne quitte la table", false, table().contains("DDDDDDDDDD02"))
verifie("... 2 effacements sur le broker", 2, size(mqtt.publies))
mqtt.publies = []
disc("DDDDDDDDDD01", "config", "")
verifie("effacement recu en retour : sans exception ni publication", 0, size(mqtt.publies))

# Heure non reglee (1970) : aucune decision
disc("EEEEEEEEEE01", "config", json.dump({"dn": "Pompe", "hn": "POMPE", "t": "jardin/pompe"}))
disc("EEEEEEEEEE02", "config", json.dump({"dn": "Pompe", "hn": "POMPE", "t": "jardin/pompe"}))
disc("EEEEEEEEEE01", "sensors", releve("2026-10-01T10:00:00"))
disc("EEEEEEEEEE02", "sensors", releve("1970-01-01T00:00:14"))
verifie("heure 1970 : les 2 MAC conservees", true, table().contains("EEEEEEEEEE01") && table().contains("EEEEEEEEEE02"))

# Ordre inverse : la plus recente arrive d'abord, l'ancienne ensuite -> l'ancienne part
disc("FFFFFFFFFF01", "config", json.dump({"dn": "Cave", "hn": "SERVEUR-RLY-CAVE", "t": "cave/a"}))
disc("FFFFFFFFFF02", "config", json.dump({"dn": "Cave", "hn": "SERVEUR-RLY-CAVE", "t": "cave/b"}))
disc("FFFFFFFFFF01", "sensors", releve("2026-10-03T09:11:44"))
disc("FFFFFFFFFF02", "sensors", releve("2026-09-27T15:21:39"))
verifie("ordre inverse : l'ancienne (recue en 2e) part", false, table().contains("FFFFFFFFFF02"))
verifie("ordre inverse : la recente reste", true, table().contains("FFFFFFFFFF01"))

# Cote ESCLAVE : retrait local seulement, aucune publication sur le broker
serveur["udp"]["id"] = 2
mqtt.publies = []
disc("GGGGGGGGGG01", "config", json.dump({"dn": "TV", "hn": "TV", "t": "salon/tv"}))
disc("GGGGGGGGGG02", "config", json.dump({"dn": "TV", "hn": "TV", "t": "salon/tv"}))
disc("GGGGGGGGGG01", "sensors", releve("2026-01-01T00:00:00"))
disc("GGGGGGGGGG02", "sensors", releve("2026-10-05T00:00:00"))
verifie("esclave : ancienne retiree de sa table", false, table().contains("GGGGGGGGGG01"))
verifie("esclave : rien publie sur le broker", 0, size(mqtt.publies))
gestionFileFolder.writeFile = ecritOrigine
serveur["udp"]["id"] = 0

print("")
print("=== 13. lireUDP : relais MQTT du push esclave (maitre seulement, texte brut) ===")
# Le VRAI lireUDP sur un faux socket ; modbusFonctions est un faux qui note les appels (le bouchon
# 'modbusFonctions' renvoie global.modbusFonctions). relaiePushMQTT lui-meme : banc_test_modbus.be §25.
class SocketFaux
  var msgs, remote_ip, remote_port
  def init(m) self.msgs = m self.remote_ip = "192.168.4.2" self.remote_port = 4000 end
  def read() return size(self.msgs) > 0 ? bytes().fromstring(self.msgs.pop(0)) : nil end
end
var appels = []
var mbFaux = module("modbusFonctions")
mbFaux.relaiePushMQTT = def (texte, ip) appels.push("relais:" + texte + "@" + str(ip)) end
mbFaux.lireMsgModbus = def (regle, p) appels.push("lire:seq=" + str(p["Seq"])) end
global.modbusFonctions = mbFaux
var etatUDP = udpFonctions.etat()
var sauveRecep = etatUDP["udpReception"]
def recoit(texte)
  appels = []
  etatUDP["udpReception"] = [nil, SocketFaux([texte])]
  return essaie(def () udpFonctions.lireUDP("MultiCast", {}) end)
end
drivers["ModBus"]["id"] = 0
var PUSH = "ModbusPushUDP 12 031000A000010200FFE7D0"
verifie("maitre : push traite sans exception", "OK", recoit(PUSH))
verifie("maitre : relais du texte brut et de l'IP, puis lecture", "['relais:" + PUSH + "@192.168.4.2', 'lire:seq=12']", str(appels))
recoit("ModbusUDP 01030001001015C6")
verifie("temoin ModbusUDP (pas un push) : aucun relais", false, string.find(str(appels), "relais:") >= 0)
drivers["ModBus"]["id"] = 2
recoit(PUSH)
verifie("temoin esclave (id 2) : push ignore, aucun relais", "[]", str(appels))
drivers["ModBus"]["id"] = 0
etatUDP["udpReception"] = sauveRecep
global.modbusFonctions = nil

print("")
print("=== 14. controleRangeExtender.init : persist sauve AVANT le Restart (boucle de redemarrages) ===")
# init() aligne les id RangeExtender/ModBus/UDP/TCP puis redemarre. Ces modifications imbriquees ne
# marquent pas le persist modifie : sans save(true), le boot suivant relisait les anciennes valeurs,
# corrigeait de nouveau et redemarrait sans fin. activation OFF : configExtenderByJson ne fait rien.
var controleRangeExtender = nil
var fRgx = open(SOURCES + "/controleRangeExtender.be", "r")
compile(fRgx.read())()
fRgx.close()
import persist
def initRgx(idRgx, idUdp)
  tasmota.cmds = []
  persist.nb_save = 0
  serveur["rangeExtender"] = {"activation": "OFF", "id": idRgx}
  serveur["udp"]["id"] = idUdp
  serveur["tcp"] = {"activation": "ON", "id": idRgx}
  drivers["ModBus"] = {"activation": "ON", "id": idRgx}
  return essaie(def () controleRangeExtender.CONTROLE_RANGE_EXTENDER() end)
end
verifie("id UDP desaligne : init sans exception", "OK", initRgx(2, 0))
verifie("id UDP desaligne : persist sauve puis Restart", "1/true", str(persist.nb_save) + "/" + str(tasmota.cmds.find("Restart 1") != nil))
verifie("... id UDP aligne en memoire", 2, serveur["udp"]["id"])
initRgx(2, 2)
verifie("temoin ids alignes : ni sauvegarde ni Restart", "0/false", str(persist.nb_save) + "/" + str(tasmota.cmds.find("Restart 1") != nil))
serveur["rangeExtender"] = {"activation": "ON", "id": 0, "debug": "ON"}
serveur["udp"]["id"] = 0
drivers["ModBus"] = {"id": 0}
serveur.remove("tcp")

print("")
print(string.format("TEST_DISCOVERY: %s (%i tests, %i echec(s))", echecs == 0 ? "OK" : "ECHEC", total, echecs))
