# Test Berry de la table de decouverte /json/discovery.json
# -----------------------------------------------------------------------------
# Charge les VRAIS udpFonctions.be, discoveryFonctions.be et rangeExtenderFonctions.be
# sous des globaux bouchonnes, et verifie les lecteurs/ecrivains de la table :
#   1-3. ImAlive (maitre) : fiche rangee sous sa MAC {MAC: {esclaveN: {...}}} (2b : reecrite seulement si elle change), ancienne
#        entree racine purgee, message sans MAC ignore.
#   4.   Page /discovery : une entree sans bloc 'config', ou un ipMaitre vide, ne tronque plus la page.
#   5.   RoutageRangeExtender : une fiche MAC sans 'lwt' ou sans bloc 'rangeExtender' ne leve plus.
#   5 bis. redirige : RgxPort envoye une seule fois par port/IP (doublons de la table NAPT lwIP).
#   6.   Etat reseau (ex-boutons RangeExtender) : 'lwt'/'config'/'sensors' ne sont pas pris pour des fiches.
#   7.   Bout en bout : l'esclave ecrit sa fiche, l'envoie en UDP (forceEnvoiParams) et en MQTT ;
#        le maitre la range ; chaque champ lu par un script consommateur (CONTRAT) doit y etre.
#   11.  mqtt_discovery : discovery.json ecrit seulement si le contenu change ; 'sensors' ignore.
#   12.  lwt : la fiche retenue ne force plus "Online" (va-et-vient avec le LWT) ; purge des MAC
#        anciennes publiant la meme fiche (heure du dernier 'sensors'), effacees du broker par le maitre.
#   16.  Commandes sans fil (E1) : voieCommandes publiee dans la fiche ; lireUDP lit le tid de
#        "ModbusUDP <tid> <hexa>" et marque Info.voie = UDP (ancien format sans tid toujours lu).
#   17.  ReglageGlobal ModeConnexion : bascule Range Extender <-> Wi-Fi classique (reseaux memorises
#        une seule fois, restaures au retour, Restart differe, mot de passe hors reponse et hors log).
#   18.  envoiUDP : un esclave emet par sa STA (socket liee a son IP), port source aleatoire ; maitre :
#        multicast par son AP lu dans le persist ; lireUDP d'un message d'un seul mot.
#   19.  C3/C4/C5 (2026-10-17) : AP du maitre lu dans le persist (adresse non standard, valeur
#        invalide), ReglageUDP envoiMultiCast hors Range Extender, reponse a ImAlive en unicast a
#        l'IP de la fiche (multicast si la fiche n'a pas d'IPv4 valide), estIPv4.
#   20.  Multicast du maitre par la box (2026-10-17) : par sa STA seulement si la table connait un
#        esclave de meme groupTopic, 'Online', sur le reseau de la box ; AP inchange ; cache de la table.
#   21.  C7 (2026-10-21) : ecoute UDP ouverte sans MQTT 60 s apres le reseau si System#Boot manque ou
#        echoue ; jamais sans reseau, jamais deux fois ; nouvel essai 60 s apres un refus ; rien apres Save.
#   25.  P8.6 (2026-10-25) : peremption des fiches : Offline sans ImAlive depuis 2 x telePeriod, verifiee a
#        chaque telePeriod (au lieu d'un reset unique de toutes les fiches) ; ImAlive remet Online.
#   26.  P8.8 (2026-10-25) : etatReseau croise RgxClients et les fiches par MAC (ok, muet, absent, fantome,
#        ip, box, inconnu), affiche sur la page /discovery du maitre.
# Les lecteurs de modbusFonctions (clients TCP, IP UDP : fichesModbus) sont testes dans
# banc_test_modbus.be section 6, sur la meme forme de table.
#
# Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/test_discovery.be
# Arguments optionnels : [dossier_sources] (defaut data/fs) [dossier_bouchons]
# (defaut outils_docs/scripts_python/berry/bouchons_berry). Temoin : lancer sur une copie de
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
sys.path().push(size(global._argv) > 2 ? global._argv[2] : "outils_docs/scripts_python/berry/bouchons_berry")

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
  var reponse                          # dernier resp_cmnd (section 17)
  def resp_cmnd(x) self.reponse = x end
  # udpFonctions.envoiUDP n'envoie rien tant que le reseau n'est pas monte (d567b9d22,
  # udpFonctions.be:467) : vrai par defaut, reseauCoupe = true simule le demarrage avant le Wi-Fi
  var reseauCoupe
  def is_network_up() return self.reseauCoupe != true end
  var ipSta                            # section 18 : IP de la STA rendue par tasmota.wifi()
  def wifi() return {"ip": (self.ipSta != nil ? self.ipSta : "192.168.4.2"), "up": true} end
  var horloge                          # section 20 : tasmota.millis() (cache de udpFonctions.esclavesBox)
  def millis() return self.horloge != nil ? self.horloge : 0 end
  def add_rule(a, b, c) end              # controleRangeExtender (section 14)
  def add_cmd(a, b) end
  # Timers en attente : memes regles que tasmota_class.be (set_timer EMPILE, remove_timer
  # retire tous ceux de cet id)
  var timers
  var rappelsTimer                     # id -> fonction, si non nil (section 17 : Restart differe)
  def set_timer(a, b, c)
    if self.timers == nil  self.timers = []  end
    self.timers.push(c)
    if self.rappelsTimer != nil  self.rappelsTimer[c] = b  end
  end
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
var liaisons = []                      # section 18 : [adresse liee, destination, port, message, port source]
var refusLiaison = nil                 # section 18 : adresse dont begin() echoue
var socketsCreees = 0                  # section 23 : udp() crees et fermees (fuite de RAM, 2026-10-24)
var socketsFermees = 0
var echecsEnvoi = 0                    # section 23 : nombre de send() a faire echouer
class udp
  var lie, portLie
  def init() socketsCreees += 1 end
  def begin(a, b) self.lie = a self.portLie = b return a != refusLiaison end
  def begin_multicast(a, b) self.lie = "mc:" + str(a) self.portLie = b return true end
  def send(ip, port, b)
    if (echecsEnvoi > 0)    echecsEnvoi -= 1    return false    end
    envois.push(b.asstring()) liaisons.push([self.lie, ip, port, b.asstring(), self.portLie]) return true
  end
  def send_multicast(b) envois.push(b.asstring()) liaisons.push([self.lie, "224.3.0.1", self.portLie, b.asstring(), self.portLie]) return true end
  def close() socketsFermees += 1 end
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
var controleUDP = nil                  # section 24
var discoveryFonctions = nil
var rangeExtenderFonctions = nil
var configGlobal = nil
var logFonctions = nil                 # la VRAIE fonction de log commune (seuil par cible)
var modules = {}                       # lu par logFonctions (cibles garage, cuve)
var globalFonctions = nil              # section 17 (ReglageGlobal ModeConnexion)
var controleGeneral = nil              # reference par globalFonctions.be

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
charge("globalFonctions")
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
print("=== 2b. ImAlive repete : discovery.json reecrit SEULEMENT si la fiche change (audit P5.2) ===")
var ecr = gestionFileFolder.ecritures
verifie("ImAlive identique ne leve pas", "OK", essaie(def () imAlive(ficheCuve(true)) end))
verifie("ImAlive identique : aucune ecriture flash", 0, gestionFileFolder.ecritures - ecr)
var ficheModifiee = ficheCuve(true)
ficheModifiee["esclave2"]["IPAddress"] = "192.168.4.3"
ecr = gestionFileFolder.ecritures
verifie("fiche modifiee (IP) ne leve pas", "OK", essaie(def () imAlive(ficheModifiee) end))
verifie("fiche modifiee : une seule ecriture", 1, gestionFileFolder.ecritures - ecr)
verifie("fiche modifiee rangee", "192.168.4.3", table()[CLE_CUVE]["esclave2"]["IPAddress"])

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
print("=== 6. Etat reseau : fiche MAC complete (config, sensors, lwt) ===")
# Les boutons RangeExtender (afficheBoutonsModulesEsclaves, appel commente) sont retires (P5.10, 2026-10-25) :
# etatReseau (P8.8) est desormais le lecteur de RgxClients. Meme piege : 'lwt' (chaine), 'config', 'sensors'
# ne doivent pas etre pris pour des fiches.
var init6 = ficheCuve(true)
init6["config"] = configCuve()
init6["sensors"] = {"sn": {"Time": "2026-09-30T12:00:00"}}
init6["lwt"] = "Online"
var table6 = {}
table6[CLE_CUVE] = init6
table6["AAAAAAAAAA01"] = {"maitre": {"id": 0, "nom": "Serveur", "IPAddress": "192.168.0.43"}, "lwt": "Online"}
var rgx6 = {}
rgx6[CLE_CUVE] = {"IPAddress": "192.168.4.2", "RSSI": -60}
var e6 = nil
verifie("etatReseau ne leve pas (lwt chaine dans la fiche)", "OK", essaie(def () e6 = discoveryFonctions.etatReseau(table6, rgx6) end))
verifie("1 esclave classe, associe et vivant ; le maitre n'est pas classe", "1 ok",
        e6 == nil ? "nil" : str(size(e6)) + " " + (size(e6) > 0 ? e6[0]["etat"] : ""))
init6["lwt"] = "Offline"
verifie("esclave Offline : associe mais muet", "muet", discoveryFonctions.etatReseau(table6, rgx6)[0]["etat"])
verifie("table absente : ne leve pas", "OK", essaie(def () discoveryFonctions.etatReseau(nil, rgx6) end))

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
  "ModBus/voieCommandes": "voie des commandes annoncee par l'esclave (voieDe du maitre, 2026-10-15)",
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
print("=== 15. Reseau pas encore monte : aucun envoi UDP (d567b9d22) ===")
# udpFonctions.envoiUDP (udpFonctions.be:467) ne cree aucune socket tant que tasmota.is_network_up()
# est faux : creer la socket avant la pile TCP/IP plantait l'ESP32 (LoadProhibited, cuve 2026-10-11).
# Memes conditions que la section 1 (maitre, table absente), reseau coupe puis revenu (temoin).
serveur = {"udp": {"id": 0, "debug": "ON", "activation": "ON"},
           "rangeExtender": {"activation": "ON", "id": 0, "debug": "ON"},
           "discovery": {"debug": "ON"},
           "mqtt": {"topic": "garage", "groupTopic1": "tasmotas/garage"},
           "hostname": "SERVEUR-GARAGE"}
drivers = {"ModBus": {"id": 0}}
diverses = {"telePeriod": 300}
tasmota.reseauCoupe = true
gestionFileFolder.fichiers = {}
envois = []
journal = []
verifie("reseau coupe : ImAlive ne leve pas", "OK", essaie(def () imAlive(ficheCuve(true)) end))
verifie("reseau coupe : aucun datagramme emis", 0, size(envois))
verifie("reseau coupe : envoi refuse journalise", true, journalise("Reseau non connecte"))
t = table()
verifie("reseau coupe : la fiche est quand meme rangee", true, t != nil && t.contains(CLE_CUVE) && t[CLE_CUVE].contains("esclave2"))
tasmota.reseauCoupe = nil
gestionFileFolder.fichiers = {}
envois = []
imAlive(ficheCuve(true))
verifie("temoin reseau revenu : heure + ipMaitre renvoyes", 2, size(envois))

print("")
print("=== 16. Commandes sans fil, etape E1 : voie annoncee, numero de transaction (2026-10-15) ===")
# PROTOCOLE_MODBUS.md §9 « Commandes sans fil » M0 et M3. L'esclave annonce dans sa fiche la voie
# par laquelle il veut ses commandes ; lireUDP lit le numero de transaction de "ModbusUDP <tid> <hexa>"
# et marque la trame venue par l'UDP (Info.voie), pour que l'esclave reponde par la meme voie.
serveur = {"adresseMAC": "", "nom": "Capteurs de Cuve", "IP": {"IPAddress": "0.0.0.0"}, "hostname": "CAPTEURS-CUVE",
           "udp": {"id": 2, "activation": "ON", "debug": "ON"},
           "rangeExtender": {"activation": "ON", "id": 2, "ipMaitre": "192.168.0.43", "debug": "ON"},
           "mqtt": {"topic": "jardin/cuve", "groupTopic1": "tasmotas/garage"}, "discovery": {"debug": "ON"}}
drivers = {"ModBus": {"activation": "ON", "id": 2, "voieCommandes": "UDP",
                      "typeComm": {"Serial": "ON", "UDP": "ON", "TCP": "OFF", "MQTT": "OFF"}}}
diverses = {"telePeriod": 300, "fuseauHoraire": {"typeReglageHeure": "UDP"}}
tasmota.statusNet = {"IPAddress": "192.168.4.2", "Mac": MAC_CUVE, "Hostname": "CAPTEURS-CUVE"}
gestionFileFolder.fichiers = {}
discoveryFonctions.changementEtatDemarrage({"Connected": 1}, "Wifi", {"WIFI": {"Connected": 1}})
verifie("fiche : voieCommandes du persist publiee (UDP)", "UDP", champ(table(), CLE_CUVE + "/esclave2/ModBus/voieCommandes"))
drivers["ModBus"].remove("voieCommandes")
gestionFileFolder.fichiers = {}
discoveryFonctions.changementEtatDemarrage({"Connected": 1}, "Wifi", {"WIFI": {"Connected": 1}})
verifie("temoin cle absente du persist : fiche en Serial", "Serial", champ(table(), CLE_CUVE + "/esclave2/ModBus/voieCommandes"))

# lireUDP : meme faux socket que la section 13, le faux lireMsgModbus note la trame et Info
var infos = []
mbFaux.lireMsgModbus = def (regle, p) infos.push([p["Trame"].tohex(), p["Info"], p.find("Seq")]) end
global.modbusFonctions = mbFaux
def recoitUni(texte)
  infos = []
  etatUDP["udpReception"] = [SocketFaux([texte]), nil]
  return essaie(def () udpFonctions.lireUDP("UniCast", {}) end)
end
drivers["ModBus"]["id"] = 2
verifie("esclave : ModbusUDP avec tid lu sans exception", "OK", recoitUni("ModbusUDP 17 01030001001015C6"))
var lu16 = size(infos) > 0 ? infos[0] : ["", {}, nil]
verifie("... trame intacte apres le tid", "01030001001015C6", lu16[0])
verifie("... Info : tid 17, voie UDP, IP de l'emetteur", "17/UDP/192.168.4.2",
        str(lu16[1].find("transaction")) + "/" + str(lu16[1].find("voie")) + "/" + str(lu16[1].find("remote_ip")))
recoitUni("ModbusUDP 01030001001015C6")
lu16 = size(infos) > 0 ? infos[0] : ["", {}, nil]
verifie("temoin ancien format sans tid : trame intacte, tid absent", "01030001001015C6/nil", lu16[0] + "/" + str(lu16[1].find("transaction")))
verifie("temoin ancien format : voie UDP quand meme", "UDP", lu16[1].find("voie"))
# Un push garde son seq et ne prend pas de tid
drivers["ModBus"]["id"] = 0
mbFaux.relaiePushMQTT = def (texte, ip) end
infos = []
etatUDP["udpReception"] = [nil, SocketFaux([PUSH])]
udpFonctions.lireUDP("MultiCast", {})
lu16 = size(infos) > 0 ? infos[0] : ["", {}, nil]
verifie("push : seq 12, pas de tid", "12/nil", str(lu16[2]) + "/" + str(lu16[1].find("transaction")))
etatUDP["udpReception"] = sauveRecep
global.modbusFonctions = nil
drivers = {"ModBus": {"id": 0}}

print("")
print("=== 17. ReglageGlobal ModeConnexion : esclave Range Extender <-> Wi-Fi classique (2026-10-16) ===")
# Pour l'outil testeur_udp.py : bascule PAR LA SERIE, avec redemarrage. Dans ReglageGlobal (controleGeneral,
# charge partout) et non ReglageRangeExtender : controleRangeExtender n'est pas charge sur la cuve ni le
# rideau, et sa garde d'activation le retirerait des activation = OFF (retour impossible).
# Ne touche ni a RgxState ni au point d'acces (choix de l'utilisateur, lecon du 2026-10-03).
import persist
var MDP17 = "MotDePasseSecret17"
def esclave17()
  serveur = {"adresseMAC": MAC_CUVE, "udp": {"id": 2, "activation": "ON"},
             "rangeExtender": {"activation": "ON", "id": 2, "AP": {"SSID": "AP-CUVE"}},
             "wifi": {"power": 0, "reseau1": {"nomReseauWifi": "SERVEUR-GARAGE-GATEWAY", "mdpWifi": "mdpAP"},
                      "reseau2": {"nomReseauWifi": "iPhone de Frederic", "mdpWifi": "mdpTel"}},
             "mqtt": {"topic": "jardin/cuve"}}
end
def mode17(payload)
  tasmota.reponse = nil
  tasmota.cmds = []
  tasmota.rappelsTimer = {}
  persist.nb_save = 0
  journal = []
  globalFonctions.reglageGlobal("ReglageGlobal", 0, "ModeConnexion" + (payload == "" ? "" : " " + payload), nil)
  var r = json.load(str(tasmota.reponse))
  return (isinstance(r, map) ? r.find("ReglageGlobal", {}) : {})
end
def redemarre17()                      # declenche le Restart differe, rend les commandes passees
  for k: tasmota.rappelsTimer.keys()    tasmota.rappelsTimer[k]()    end
  return tasmota.cmds.find("Restart 1") != nil
end
def reseaux17() return serveur["wifi"]["reseau1"]["nomReseauWifi"] + "|" + serveur["wifi"]["reseau2"]["nomReseauWifi"] end
esclave17()
var r17 = mode17("")
verifie("lecture : mode RangeExtender, rien de sauve", "RangeExtender/0", str(r17.find("modeConnexion")) + "/" + str(persist.nb_save))
r17 = mode17("WifiClassique MAISON " + MDP17)
verifie("-> WifiClassique : reponse et redemarrage annonce", "WifiClassique/true", str(r17.find("modeConnexion")) + "/" + str(r17.find("redemarrage")))
verifie("... reseau1 = maison, reseau2 = point d'acces du maitre (filet)", "MAISON|SERVEUR-GARAGE-GATEWAY", reseaux17())
verifie("... mot de passe maison pose", MDP17, serveur["wifi"]["reseau1"]["mdpWifi"])
verifie("... activation Range Extender OFF, persist sauve", "OFF/true", serveur["rangeExtender"]["activation"] + "/" + str(persist.nb_save > 0))
verifie("... reseaux d'origine sauvegardes", "SERVEUR-GARAGE-GATEWAY|iPhone de Frederic",
        serveur["wifi"]["sauvegardeRangeExtender"]["reseau1"]["nomReseauWifi"] + "|" + serveur["wifi"]["sauvegardeRangeExtender"]["reseau2"]["nomReseauWifi"])
verifie("... mot de passe absent de la reponse", -1, string.find(str(tasmota.reponse), MDP17))
verifie("... bascule journalisee sans le mot de passe", "true/false", str(journalise("REGLAGE_MODE_CONNEXION")) + "/" + str(journalise(MDP17)))
verifie("... point d'acces non touche (aucune commande Rgx)", false, string.find(str(tasmota.cmds), "Rgx") >= 0)
verifie("... Restart differe (reponse d'abord), puis Restart 1", "false/true", str(tasmota.cmds.find("Restart 1") != nil) + "/" + str(redemarre17()))
r17 = mode17("WifiClassique MAISON " + MDP17)
verifie("temoin 2e bascule identique : ni sauvegarde ecrasee, ni redemarrage", "SERVEUR-GARAGE-GATEWAY/0/nil",
        serveur["wifi"]["sauvegardeRangeExtender"]["reseau1"]["nomReseauWifi"] + "/" + str(persist.nb_save) + "/" + str(r17.find("redemarrage")))
r17 = mode17("WifiClassique AUTRE-RESEAU " + MDP17)
verifie("2e bascule vers un AUTRE reseau : la sauvegarde garde l'origine", "SERVEUR-GARAGE-GATEWAY|iPhone de Frederic",
        serveur["wifi"]["sauvegardeRangeExtender"]["reseau1"]["nomReseauWifi"] + "|" + serveur["wifi"]["sauvegardeRangeExtender"]["reseau2"]["nomReseauWifi"])
verifie("... reseau2 reste le point d'acces du maitre", "AUTRE-RESEAU|SERVEUR-GARAGE-GATEWAY", reseaux17())
r17 = mode17("RangeExtender")
verifie("-> RangeExtender : reseaux d'origine restaures", "SERVEUR-GARAGE-GATEWAY|iPhone de Frederic", reseaux17())
verifie("... mots de passe d'origine restaures", "mdpAP|mdpTel", serveur["wifi"]["reseau1"]["mdpWifi"] + "|" + serveur["wifi"]["reseau2"]["mdpWifi"])
verifie("... sauvegarde effacee, activation ON, redemarrage", "false/ON/true",
        str(serveur["wifi"].contains("sauvegardeRangeExtender")) + "/" + serveur["rangeExtender"]["activation"] + "/" + str(redemarre17()))
r17 = mode17("RangeExtender")
verifie("temoin deja en RangeExtender : rien ne change", "nil/0", str(r17.find("redemarrage")) + "/" + str(persist.nb_save))
# Wi-Fi classique sans sauvegarde (bascule faite a la main) : le retour ne doit rien inventer
serveur["rangeExtender"]["activation"] = "OFF"
r17 = mode17("RangeExtender")
verifie("temoin retour sans sauvegarde : erreur, rien ne change", "true/OFF/0/nil",
        str(r17.find("erreur") != nil) + "/" + serveur["rangeExtender"]["activation"] + "/" + str(persist.nb_save) + "/" + str(r17.find("redemarrage")))
esclave17()
r17 = mode17("WifiClassique iPhone de Frederic " + MDP17)
verifie("SSID avec espaces : dernier mot = mot de passe", "iPhone de Frederic/" + MDP17,
        serveur["wifi"]["reseau1"]["nomReseauWifi"] + "/" + serveur["wifi"]["reseau1"]["mdpWifi"])
esclave17()
r17 = mode17("WifiClassique MAISON")
verifie("temoin mot de passe absent : erreur, rien ne change", "true/SERVEUR-GARAGE-GATEWAY/0",
        str(r17.find("erreur") != nil) + "/" + serveur["wifi"]["reseau1"]["nomReseauWifi"] + "/" + str(persist.nb_save))
r17 = mode17("LoRa")
verifie("temoin mode inconnu : erreur, rien ne change", "true/ON/0",
        str(r17.find("erreur") != nil) + "/" + serveur["rangeExtender"]["activation"] + "/" + str(persist.nb_save))
tasmota.rappelsTimer = nil
journal = []
var aide17 = globalFonctions.aideReglageGlobal(nil)
var noms17 = []
for l: aide17    noms17.push(l[0])    end
verifie("aide : ModeConnexion listee, detail present", "true/true", str(noms17.find("ModeConnexion") != nil) + "/" + str(globalFonctions.aideReglageGlobal("ModeConnexion") != nil))

print("")
print("=== 18. envoiUDP : un esclave emet par sa STA, port source aleatoire (diagnostic 2026-10-17) ===")
# Chevauchement mesure le 2026-10-17 : la cuve a son AP en 192.168.4.1/24 ET est cliente du maitre en
# 192.168.4.2/24. Socket non liee -> sortie par son AP, envoi au maitre perdu ; liee a 192.168.4.2 -> recu.
# Corrections C1 (liaison a la STA, esclave) + C2 (port source 0) + C6 (lireUDP, un seul mot), et
# depuis le 2026-10-17 C3 (multicast maitre) + C4 (multicast esclave hors RE) ; C5 : section 19.
serveur = {"udp": {"id": 2, "debug": "ON", "activation": "ON"},
           "rangeExtender": {"activation": "ON", "id": 2, "AP": {"IPAddress": "192.168.4.1", "Subnet": "255.255.255.0"}},
           "discovery": {"debug": "ON"},
           "mqtt": {"topic": "jardin/cuve", "groupTopic1": "tasmotas/garage"},
           "hostname": "CAPTEURS-CUVE"}
etatUDP["ip"] = ["", "224.3.0.1"]
etatUDP["port"] = [2000, 4000]
def dernier() return size(liaisons) > 0 ? liaisons[size(liaisons) - 1] : ["?", "?", 0, "?", "?"] end
def resume(l) return str(l[0]) + "/" + str(l[1]) + "/" + str(l[2]) + "/" + str(l[4]) end
tasmota.ipSta = "192.168.4.2"
liaisons = []
journal = []
udpFonctions.envoiUDP("UniCast", "192.168.4.1", "R1")
verifie("esclave RE unicast : lie a la STA, port source 0", "192.168.4.2/192.168.4.1/2000/0", resume(dernier()))
verifie("format du log d'envoi inchange (testeur_udp_essais.RE_ENVOI)", true,
        journalise("Données UniCast envoyées vers '192.168.4.1' >>>> R1 >>>> OK"))
liaisons = []
udpFonctions.envoiUDP("MultiCast", "", "R2")
verifie("esclave RE multicast : lie a la STA, groupe 224.3.0.1:4000, port source 0",
        "192.168.4.2/224.3.0.1/4000/0", resume(dernier()))
# Wi-Fi classique : le multicast esclave part par sa STA (C4 ; avant : rien, journal 'nil')
serveur["rangeExtender"]["activation"] = "OFF"
tasmota.ipSta = "192.168.0.50"
liaisons = []
journal = []
udpFonctions.envoiUDP("MultiCast", "", "R3")
verifie("C4 esclave Wi-Fi classique : multicast par la STA", "192.168.0.50/224.3.0.1/4000/0/true",
        resume(dernier()) + "/" + str(journalise(">>>> R3 >>>> OK")))
liaisons = []
udpFonctions.envoiUDP("UniCast", "192.168.0.43", "R4")
verifie("esclave Wi-Fi classique unicast : lie a la STA", "192.168.0.50/192.168.0.43/2000/0", resume(dernier()))
tasmota.ipSta = ""
liaisons = []
verifie("esclave STA inconnue : pas d'exception", "OK", essaie(def () udpFonctions.envoiUDP("UniCast", "192.168.0.43", "R5") end))
verifie("... socket sur toutes les interfaces", "/192.168.0.43/2000/0", resume(dernier()))
tasmota.ipSta = "192.168.4.2"
refusLiaison = "192.168.4.2"
etatUDP["socketsEmission"] = {}        # le refus ne joue qu'a l'ouverture : pas de socket deja ouverte (section 23)
liaisons = []
journal = []
udpFonctions.envoiUDP("UniCast", "192.168.4.1", "R6")
verifie("liaison refusee : 2e essai sur toutes les interfaces", "1//OK", str(size(liaisons)) + "/" + str(dernier()[0]) + "/" +
        (journalise(">>>> R6 >>>> OK") ? "OK" : "?"))
verifie("... et le 2e essai est journalise", true, journalise("nouvel essai sur toutes les interfaces"))
refusLiaison = nil
# Maitre : unicast inchange (port source aleatoire) ; multicast par son AP (persist), sinon sa STA (C3)
serveur["udp"]["id"] = 0
serveur["rangeExtender"]["activation"] = "ON"
tasmota.ipSta = "192.168.0.43"
liaisons = []
udpFonctions.envoiUDP("UniCast", "192.168.4.2", "R7")
verifie("maitre unicast : toutes les interfaces, port source 0 (avant : 2000)", "/192.168.4.2/2000/0", resume(dernier()))
liaisons = []
udpFonctions.envoiUDP("MultiCast", "192.168.4.1", "R8")
verifie("maitre multicast : par l'interface imposee par l'appelant", "192.168.4.1/224.3.0.1/4000/0", resume(dernier()))
liaisons = []
udpFonctions.envoiUDP("MultiCast", "", "R9")
verifie("C3 maitre multicast sans interface : par son AP (persist)", "192.168.4.1/224.3.0.1/4000/0", resume(dernier()))
serveur["rangeExtender"]["activation"] = "OFF"
gestionFileFolder.writeFile("/json/discovery.json", "{}")
liaisons = []
journal = []
udpFonctions.envoiUDP("MultiCast", "", "R10")
verifie("maitre sans Range Extender ni esclave sur la box : non emis", "0/true",
        str(size(liaisons)) + "/" + str(journalise(">>>> R10 >>>> Non emis")))
liaisons = []
journal = []
udpFonctions.envoiUDP("Broadcast", "", "R11")
verifie("type inconnu : rien n'est emis, erreur journalisee", "0/true",
        str(size(liaisons)) + "/" + str(journalise("ENVOI_MSG_UDP_ERREUR: type de communication inconnu 'Broadcast'")))
# lireUDP : message d'un seul mot (avant : index_error dans every_100ms)
serveur["udp"]["id"] = 2
drivers["ModBus"]["id"] = 2
etatUDP["udpReception"] = [SocketFaux(["TESTUDP"]), nil]
verifie("lireUDP : message d'un seul mot sans exception", "OK", essaie(def () udpFonctions.lireUDP("UniCast", {}) end))
etatUDP["udpReception"] = sauveRecep

print("")
print("=== 19. C3/C4/C5 : AP lu dans le persist, multicast hors Range Extender, ImAlive en unicast (2026-10-17) ===")
# Les deux modes sont de vrais modes d'usage (decision du 2026-10-17) : Range Extender ET Wi-Fi classique.
# C3 : maitre, AP a une adresse NON standard -> le multicast suit le persist, plus de 192.168.4.1 en dur
serveur["udp"]["id"] = 0
drivers["ModBus"]["id"] = 0
serveur["rangeExtender"] = {"activation": "ON", "id": 0, "AP": {"IPAddress": "192.168.7.1"}}
tasmota.ipSta = "192.168.0.43"
liaisons = []
udpFonctions.envoiUDP("MultiCast", "", "S1")
verifie("C3 maitre multicast : AP lu dans le persist", "192.168.7.1/224.3.0.1/4000/0", resume(dernier()))
serveur["rangeExtender"]["AP"] = {"IPAddress": "pas une adresse"}
liaisons = []
udpFonctions.envoiUDP("MultiCast", "", "S2")
verifie("C3 adresse d'AP invalide : repli 192.168.4.1", "192.168.4.1/224.3.0.1/4000/0", resume(dernier()))
serveur["rangeExtender"] = {"activation": "ON", "id": 0}
verifie("C3 bloc AP absent : 192.168.4.1", "192.168.4.1", udpFonctions.ipAP())
serveur["rangeExtender"]["activation"] = "OFF"
verifie("C3 Range Extender inactif : pas d'AP", "", udpFonctions.ipAP())
serveur["rangeExtender"] = {"activation": "ON", "id": 0, "AP": {"IPAddress": "192.168.7.1"}}

# C5 : reponse a ImAlive en UNICAST a l'IP de la fiche (Range Extender : 192.168.4.2, par l'AP du maitre)
def reponsesImAlive(fiche)
  gestionFileFolder.fichiers = {}
  liaisons = []
  imAlive(fiche)
  var r = []
  for l: liaisons    r.push(resume(l) + (string.find(l[3], "Timestamp") >= 0 ? ":heure" : (string.find(l[3], "ipMaitre") >= 0 ? ":ip" : ":?")))    end
  return r.concat("|")
end
verifie("C5 Range Extender : heure + ipMaitre en unicast a la fiche",
        "/192.168.4.2/2000/0:heure|/192.168.4.2/2000/0:ip", reponsesImAlive(ficheCuve(true)))
var ficheWifi = ficheCuve(true)
ficheWifi["esclave2"]["IPAddress"] = "192.168.0.50"
verifie("C5 Wi-Fi classique : unicast a l'IP de la box",
        "/192.168.0.50/2000/0:heure|/192.168.0.50/2000/0:ip", reponsesImAlive(ficheWifi))
var ficheSansIP = ficheCuve(true)
ficheSansIP["esclave2"].remove("IPAddress")
verifie("C5 fiche sans IP : repli multicast par l'AP",
        "192.168.7.1/224.3.0.1/4000/0:heure|192.168.7.1/224.3.0.1/4000/0:ip", reponsesImAlive(ficheSansIP))
ficheSansIP["esclave2"]["IPAddress"] = "0.0.0.0"
verifie("C5 fiche en 0.0.0.0 : repli multicast",
        "192.168.7.1/224.3.0.1/4000/0:heure|192.168.7.1/224.3.0.1/4000/0:ip", reponsesImAlive(ficheSansIP))
var ficheNTP = ficheCuve(true)
ficheNTP["esclave2"]["typeReglageHeure"] = "NTP"
verifie("C5 esclave a l'heure NTP : aucune reponse (inchange)", "", reponsesImAlive(ficheNTP))

# C4 : la commande de test emet aussi hors Range Extender (avant : rien, sans erreur)
serveur["udp"]["id"] = 2
drivers["ModBus"]["id"] = 2
serveur["rangeExtender"] = {"activation": "OFF", "id": 2}
tasmota.ipSta = "192.168.0.50"
liaisons = []
udpFonctions.reglageUDP("ReglageUDP", 0, "envoiMultiCast S4 en trois mots", nil)
verifie("C4 ReglageUDP envoiMultiCast hors Range Extender : par la STA",
        "192.168.0.50/224.3.0.1/4000/0|S4 en trois mots", resume(dernier()) + "|" + str(dernier()[3]))

# estIPv4 : seule porte vers l'unicast de C5 (validation a la frontiere : la fiche vient du reseau)
var casIP = {"192.168.4.2": true, "0.0.0.0": false, "256.1.1.1": false, "1.2.3": false, "1.2.3.4.5": false,
             "a.b.c.d": false, "": false, "nil": false, "192.168.0.": false, "1.2.3.4 ": false}
var faux = []
for k: casIP.keys()
  if udpFonctions.estIPv4(k) != casIP[k]    faux.push(k)    end
end
verifie("estIPv4 : 10 cas", "[]", str(faux))
verifie("estIPv4(nil) : false", false, udpFonctions.estIPv4(nil))

print("")
print("=== 20. Multicast du maitre par la box : seulement si un esclave y est decouvert (2026-10-17) ===")
# Regle de l'utilisateur : sans esclave retrouve par la box, pas de multicast du maitre par sa STA.
# Critere retenu : meme groupTopic + 'Online' + IP sur le reseau de la box ; multicast par l'AP inchange.
# Mesure de l'essai 2 (Wi-Fi classique) : la box relaie le multicast, mais celui du maitre partait par son AP.
import path                            # bouchon : date de la table = nombre d'ecritures
serveur["udp"]["id"] = 0
drivers["ModBus"]["id"] = 0
serveur["adresseMAC"] = "AA:AA:AA:AA:AA:00"
serveur["rangeExtender"] = {"activation": "ON", "id": 0, "AP": {"IPAddress": "192.168.4.1"}}
tasmota.ipSta = "192.168.0.43"
# Table a une seule entree : la fiche 'role' de la MAC 'cle', ecrite comme par les vrais ecrivains
def tableBox(cle, role, ip, groupe, lwt)
  var f = ficheCuve(true)["esclave2"]
  f["IPAddress"] = ip
  if groupe != nil    f["groupTopic"] = groupe    end
  var entree = {}
  entree[role] = f
  if lwt != nil    entree["lwt"] = lwt    end
  var t = {}
  t[cle] = entree
  gestionFileFolder.fichiers = {}
  gestionFileFolder.writeFile("/json/discovery.json", json.dump(t))
end
def ficheBox(ip, groupe, lwt) tableBox(CLE_CUVE, "esclave2", ip, groupe, lwt) end
# Interfaces par lesquelles le multicast du maitre est parti, dans l'ordre ("" = toutes)
def emissions20(msg)
  liaisons = []
  journal = []
  udpFonctions.envoiUDP("MultiCast", "", msg)
  var r = []
  for l: liaisons    r.push(str(l[0]) + (l[1] == "224.3.0.1" && l[2] == 4000 ? "" : "?"))    end
  return r.concat("+")
end
var GROUPE = "tasmotas/garage"
gestionFileFolder.writeFile("/json/discovery.json", "{}")
verifie("table vide : AP seul (inchange)", "192.168.4.1", emissions20("T1"))
ficheBox("192.168.0.6", GROUPE, "Online")
verifie("esclave box, meme groupe, Online : AP + STA", "192.168.4.1+192.168.0.43", emissions20("T2"))
verifie("... un seul log d'envoi, resultat OK", true, journalise(">>>> T2 >>>> OK"))
verifie("... changement journalise (ACTIVE)", true, journalise("ESCLAVES_BOX: multicast du maitre par la box ACTIVE"))
ficheBox("192.168.0.6", GROUPE, "Offline")
verifie("esclave box Offline : AP seul", "192.168.4.1", emissions20("T3"))
verifie("... changement journalise (DESACTIVE)", true, journalise("ESCLAVES_BOX: multicast du maitre par la box DESACTIVE"))
ficheBox("192.168.0.6", GROUPE, nil)
verifie("esclave box sans 'lwt' : AP seul", "192.168.4.1", emissions20("T4"))
ficheBox("192.168.0.6", "tasmotas/cave", "Online")
verifie("esclave box d'un autre groupe : AP seul", "192.168.4.1", emissions20("T5"))
ficheBox("192.168.0.6", nil, "Online")
verifie("esclave box sans groupTopic : AP seul", "192.168.4.1", emissions20("T6"))
ficheBox("192.168.4.2", GROUPE, "Online")
verifie("esclave derriere l'AP (192.168.4.2) : AP seul", "192.168.4.1", emissions20("T7"))
ficheBox("10.0.0.5", GROUPE, "Online")
verifie("esclave hors du reseau de la box : AP seul", "192.168.4.1", emissions20("T8"))
ficheBox("0.0.0.0", GROUPE, "Online")
verifie("esclave a l'IP invalide : AP seul", "192.168.4.1", emissions20("T9"))
tableBox("AAAAAAAAAA00", "esclave2", "192.168.0.6", GROUPE, "Online")
verifie("fiche sous NOTRE MAC : ignoree", "192.168.4.1", emissions20("T10"))
tableBox(CLE_CUVE, "maitre", "192.168.0.6", GROUPE, "Online")
verifie("fiche d'un autre maitre : ignoree", "192.168.4.1", emissions20("T11"))
gestionFileFolder.writeFile("/json/discovery.json", "pas du json")
verifie("table illisible : pas d'exception, AP seul", "192.168.4.1", emissions20("T12"))
# Interface imposee par l'appelant et multicast de l'esclave : inchanges
ficheBox("192.168.0.6", GROUPE, "Online")
liaisons = []
udpFonctions.envoiUDP("MultiCast", "192.168.4.1", "T13")
verifie("interface imposee : une seule emission", "1/192.168.4.1", str(size(liaisons)) + "/" + str(dernier()[0]))
# Liaison de la STA refusee : 2e essai sur toutes les interfaces, l'AP reste servi
refusLiaison = "192.168.0.43"
etatUDP["socketsEmission"] = {}        # le refus ne joue qu'a l'ouverture : pas de socket deja ouverte (section 23)
verifie("STA refusee : AP puis toutes les interfaces", "192.168.4.1+", emissions20("T14"))
refusLiaison = nil
# Sans Range Extender : la STA seulement s'il y a un esclave sur la box, sinon rien
serveur["rangeExtender"] = {"activation": "OFF", "id": 0}
verifie("sans AP, esclave box : STA seule", "192.168.0.43", emissions20("T15"))
ficheBox("192.168.0.6", GROUPE, "Offline")
verifie("sans AP, esclave Offline : non emis", "/true", emissions20("T16") + "/" + str(journalise(">>>> T16 >>>> Non emis")))
verifie("... raison journalisee", true, journalise("multicast du maitre non emis : pas de point d'acces actif et aucun esclave joignable par la box"))
ficheBox("192.168.0.6", GROUPE, "Online")
tasmota.ipSta = ""
verifie("sans AP, STA inconnue : non emis, sans exception", "", emissions20("T17"))
tasmota.ipSta = "192.168.0.43"
# Cache : une seule lecture de la table tant qu'elle ne change pas
var lectures = 0
var vraiReadFile = gestionFileFolder.readFile
gestionFileFolder.readFile = def (chemin) lectures += 1 return vraiReadFile(chemin) end
emissions20("T18")
lectures = 0
emissions20("T19") emissions20("T20") emissions20("T21")
verifie("cache : table inchangee, aucune relecture", 0, lectures)
ficheBox("192.168.0.6", GROUPE, "Offline")
var e22 = emissions20("T22")
verifie("cache : table reecrite, relue (non emis)", "1/", str(lectures) + "/" + e22)
# Date figee (deux ecritures dans la meme seconde) : resultat garde au plus 30 s
path.date = 1790000000
ficheBox("192.168.0.6", GROUPE, "Offline")
emissions20("T23")
ficheBox("192.168.0.6", GROUPE, "Online")
tasmota.horloge = 29000
verifie("date figee, < 30 s : ancien resultat garde", "", emissions20("T24"))
tasmota.horloge = 30001
verifie("date figee, > 30 s : table relue", "192.168.0.43", emissions20("T25"))
gestionFileFolder.readFile = vraiReadFile
path.date = nil
tasmota.horloge = nil

print("=== 21. C7 : ecoute UDP ouverte aussi sans MQTT (2026-10-21) ===")
# Avant C7, les sockets d'ecoute (2000 unicast, 4000 multicast) ne s'ouvraient que sur System#Boot,
# leve a la 1re connexion MQTT (DIAGNOSTIC_UDP_2026-10-17.md, L3) : broker injoignable au demarrage =
# une cuve commandee par UDP n'entend plus le P4. Secours : 60 s apres la montee du reseau sans Boot.
class udpCompte : udp
  var n
  def begin(a, b) self.n = (self.n == nil ? 1 : self.n + 1) return super(self).begin(a, b) end
  def begin_multicast(a, b) self.n = (self.n == nil ? 1 : self.n + 1) return super(self).begin_multicast(a, b) end
end
# Etat de demarrage, comme les deux CONTROLE_UDP le posent (controleUDP.be:84-87)
def demarre21()
  var e = udpFonctions.etat()
  e["udpReception"] = [udpCompte(), udpCompte()]
  e["port"] = [2000, 4000]
  e["typeComm"] = ["UniCast", "MultiCast"]
  e["ip"] = ["", "224.3.0.1"]
  e["ecouteOuverte"] = [false, false]
  e["secoursFini"] = false
  e["reseauDepuis"] = nil
  e["essaiApres"] = [nil, nil]
  e["cycleLance"] = false
  tasmota.reseauCoupe = false
  tasmota.horloge = 0
  tasmota.timers = []
  journal = []
end
# Une seconde du driver : les deux CONTROLE_UDP appellent every_second
def seconde21(ms)
  tasmota.horloge = ms
  return essaie(def () udpFonctions.secoursSansMqtt("UniCast") udpFonctions.secoursSansMqtt("MultiCast") end)
end
def boot21()
  return essaie(def ()
    udpFonctions.changementEtatDemarrage({"Boot": 1}, "System", {"System": {"Boot": 1}}, "UniCast")
    udpFonctions.changementEtatDemarrage({"Boot": 1}, "System", {"System": {"Boot": 1}}, "MultiCast")
  end)
end
def ouvertures21()
  var r = udpFonctions.etat()["udpReception"]
  return str(r[0].n == nil ? 0 : r[0].n) + "/" + str(r[1].n == nil ? 0 : r[1].n)
end
serveur["udp"]["id"] = 0
serveur["rangeExtender"] = {"activation": "ON", "id": 0, "AP": {"IPAddress": "192.168.4.1"}}
refusLiaison = nil
# a) Reseau absent : jamais de socket (plantage lwip_socket du 2026-10-11)
demarre21()
tasmota.reseauCoupe = true
var r21 = "OK"
for s: 1 .. 120    var x = seconde21(s * 1000)    if x != "OK"  r21 = x  end    end
verifie("reseau absent 120 s : aucune ouverture", "OK 0/0", r21 + " " + ouvertures21())
# b) Reseau monte a t=200 s, MQTT jamais connecte : rien avant 60 s, puis une ouverture de chaque
tasmota.reseauCoupe = false
seconde21(200000)
seconde21(259000)
verifie("reseau monte, 59 s sans Boot : pas encore ouvert", "0/0", ouvertures21())
verifie("60 s sans Boot : unicast ET multicast ouverts", "OK 1/1", seconde21(260000) + " " + ouvertures21())
verifie("... sur les bons ports", "/2000 mc:224.3.0.1/4000",
        str(udpFonctions.etat()["udpReception"][0].lie) + "/" + str(udpFonctions.etat()["udpReception"][0].portLie) + " " +
        str(udpFonctions.etat()["udpReception"][1].lie) + "/" + str(udpFonctions.etat()["udpReception"][1].portLie))
verifie("... secours journalise", true, journalise("UDP_ECOUTE_SECOURS: "))
for s: 261 .. 400    seconde21(s * 1000)    end
verifie("les secondes suivantes : aucune reouverture", "1/1", ouvertures21())
# c) MQTT revient : Boot ne rouvre pas (double begin), mais fait le reste (maitre : timer resetEsclaves)
verifie("Boot apres le secours : sans reouverture", "OK 1/1", boot21() + " " + ouvertures21())
verifie("... le maitre arme toujours resetEsclaves", 1, tasmota.nbTimers("resetEsclaves"))
# d) Chemin normal : Boot a t=5 s ouvre, le secours ne fait plus rien (TEMOIN du comportement d'avant)
demarre21()
seconde21(1000)
verifie("Boot normal : une ouverture de chaque", "OK 1/1", boot21() + " " + ouvertures21())
for s: 2 .. 200    seconde21(s * 1000)    end
verifie("... secours muet apres Boot", "1/1 false", ouvertures21() + " " + str(journalise("UDP_ECOUTE_SECOURS: ")))
# e) Reseau qui retombe avant 60 s : le delai repart de la remontee
demarre21()
seconde21(0)
tasmota.reseauCoupe = true
seconde21(30000)
tasmota.reseauCoupe = false
seconde21(40000)
seconde21(99000)
verifie("reseau retombe a 30 s, remonte a 40 s : rien a 99 s", "0/0", ouvertures21())
seconde21(100000)
verifie("... ouvert a 100 s", "1/1", ouvertures21())
# f) Ouverture refusee : erreur journalisee, nouvel essai 60 s plus tard seulement
demarre21()
refusLiaison = ""
seconde21(0)
seconde21(60000)
verifie("unicast refuse : multicast ouvert, unicast non", "1/1 false true", ouvertures21() + " " +
        str(udpFonctions.etat()["ecouteOuverte"][0]) + " " + str(udpFonctions.etat()["ecouteOuverte"][1]))
verifie("... echec journalise en erreur", true, journalise("UDP_ECOUTE_ERREUR: "))
for s: 61 .. 119    seconde21(s * 1000)    end
verifie("... pas de nouvel essai avant 60 s", "1/1", ouvertures21())
refusLiaison = nil
seconde21(120000)
verifie("... nouvel essai a 120 s, unicast ouvert", "2/1 true", ouvertures21() + " " + str(udpFonctions.etat()["ecouteOuverte"][0]))
# g) System#Save ferme : les sockets sont notees fermees, le secours ne les rouvre pas (Boot deja vu)
demarre21()
boot21()
essaie(def () udpFonctions.changementEtatDemarrage({"Save": 1}, "System", {"System": {"Save": 1}}, "UniCast") end)
verifie("Save : sockets notees fermees", "false false", str(udpFonctions.etat()["ecouteOuverte"][0]) + " " + str(udpFonctions.etat()["ecouteOuverte"][1]))
for s: 1 .. 200    seconde21(s * 1000)    end
verifie("... pas de reouverture par le secours", "1/1", ouvertures21())
# h) Boot dont l'ouverture echoue (retour du relecteur) : le secours prend le relais 60 s apres le reseau
demarre21()
seconde21(0)
refusLiaison = ""
boot21()
refusLiaison = nil
verifie("Boot, unicast refuse : secours pas fini", "false 1/1", str(udpFonctions.etat()["secoursFini"]) + " " + ouvertures21())
seconde21(59000)
verifie("... rien avant 60 s", "1/1", ouvertures21())
seconde21(60000)
verifie("... unicast rouvert par le secours, puis secours fini", "2/1 true", ouvertures21() + " " + str(udpFonctions.etat()["secoursFini"]))
# i) R2/P8.7 (2026-10-24) : sans MQTT, l'esclave se presente quand meme. Le secours lance le cycle de
#    presentation (forceEnvoiParams) UNE fois ; un Boot tardif ne le relance pas (une seule chaine de timers).
def presentations21()
  var n = 0
  for c: tasmota.cmds    if c == "ReglageUDP forceEnvoiParams ON"  n += 1  end    end
  return n
end
serveur["udp"]["id"] = 1
demarre21()
tasmota.cmds = []
seconde21(0)
seconde21(59000)
verifie("esclave sans MQTT, 59 s : pas encore de presentation", 0, presentations21())
seconde21(60000)
verifie("esclave sans MQTT, 60 s : presentation lancee par le secours (forceEnvoiParams)", 1, presentations21())
for s: 61 .. 120    seconde21(s * 1000)    end
boot21()
verifie("... ni les secondes suivantes ni un Boot tardif ne la relancent", 1, presentations21())
# j) TEMOIN : chemin normal, Boot -> une presentation, le secours n'en ajoute pas
demarre21()
tasmota.cmds = []
seconde21(1000)
boot21()
for s: 2 .. 200    seconde21(s * 1000)    end
verifie("TEMOIN : Boot normal -> une presentation, le secours n'en ajoute pas", 1, presentations21())
# k) Maitre sans MQTT : le timer resetEsclaves est arme par le secours
serveur["udp"]["id"] = 0
demarre21()
seconde21(0)
seconde21(60000)
verifie("maitre sans MQTT, 60 s : timer resetEsclaves arme par le secours", 1, tasmota.nbTimers("resetEsclaves"))
# l) Audit N9/P5.8 : l'ancienne boucle de deballage de 'value' (inutilisee ici) levait des la 2e cle
verifie("changementEtatDemarrage UDP, valeur a plusieurs cles : sans exception", "OK",
        essaie(def () udpFonctions.changementEtatDemarrage({"AP": 1, "SSId": "box", "RSSI": 80}, "Essai", {}, "UniCast") end))
tasmota.horloge = nil
tasmota.reseauCoupe = nil

print("")
print("=== 22. discovery.json lu UNE fois par traitement (audit M3/P9.3, 2026-10-24) ===")
def lectures22() return gestionFileFolder.lectures.find("/json/discovery.json", 0) end
# a) Page /discovery
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init4), "/sd/css/main.css": ""}
gestionFileFolder.lectures = {}
webserver.envoye = []
webserver.termine = false
verifie("page : ne leve pas", "OK", essaie(def () discoveryFonctions.affichePageDiscovery() end))
var boutons22 = 0
for s: webserver.envoye    if string.find(s, "<button class='button") >= 0    boutons22 += 1    end    end
verifie("page : 1 lecture de discovery.json, meme bouton", "1 1", str(lectures22()) + " " + str(boutons22))
# b) Mqtt#Connected d'un esclave : sa fiche republiee (retenue)
serveur = {"adresseMAC": MAC_CUVE, "nom": "Capteurs de Cuve", "IP": {"IPAddress": "192.168.4.2"}, "hostname": "CAPTEURS-CUVE",
           "udp": {"id": 2, "activation": "ON"}, "rangeExtender": {"activation": "ON", "id": 2},
           "mqtt": {"topic": "jardin/cuve", "groupTopic1": "tasmotas/garage"}, "discovery": {}}
var init22 = {}
init22[CLE_CUVE] = ficheCuve(true)
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init22)}
gestionFileFolder.lectures = {}
mqtt.publies = []
essaie(def () discoveryFonctions.changementEtatDemarrage({"Connected": 1}, "Mqtt", {"MQTT": {"Connected": 1}}) end)
verifie("Mqtt#Connected : 1 lecture, fiche publiee", "1 tasmota/discovery/" + CLE_CUVE + "/esclave2",
        str(lectures22()) + " " + (size(mqtt.publies) > 0 ? mqtt.publies[0][0] : "rien"))
gestionFileFolder.fichiers = {"/json/discovery.json": ""}
mqtt.publies = []
journal = []
essaie(def () discoveryFonctions.changementEtatDemarrage({"Connected": 1}, "Mqtt", {"MQTT": {"Connected": 1}}) end)
verifie("Mqtt#Connected, table vide : rien publie, pas d'erreur", "0 false", str(size(mqtt.publies)) + " " + str(journalise("_ERREUR")))
# c) Peremption (perimeFiches, P8.6, qui remplace resetClientsConnectes) : MAC jamais vue -> Offline,
#    ecriture seulement si besoin
udpFonctions.etat()["presence"] = {}
udpFonctions.etat()["peremptionDepuis"] = nil
init22[CLE_CUVE]["lwt"] = "Online"     # seules les fiches Online perissent
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init22)}
gestionFileFolder.lectures = {}
gestionFileFolder.ecritures = 0
udpFonctions.perimeFiches()
t = table()
verifie("peremption : 1 lecture, 1 ecriture, MAC Offline", "1 1 Offline", str(lectures22()) + " " + str(gestionFileFolder.ecritures) + " " + str(champ(t, CLE_CUVE + "/lwt")))
gestionFileFolder.lectures = {}
udpFonctions.perimeFiches()
verifie("peremption deja Offline : 1 lecture, aucune ecriture", "1 1", str(lectures22()) + " " + str(gestionFileFolder.ecritures))
# d) Table illisible : signalee en erreur (avant : exception journalisee par l'appelant)
gestionFileFolder.fichiers = {"/json/discovery.json": "{pas du json", "/sd/css/main.css": ""}
journal = []
webserver.termine = false
verifie("table illisible : page ne leve pas, terminee", "OK true", essaie(def () discoveryFonctions.affichePageDiscovery() end) + " " + str(webserver.termine))
verifie("... erreur journalisee", true, journalise("DISCOVERY_ERREUR"))

print("")
print("=== 23. Socket d'emission gardee ouverte : une par interface (fuite de RAM P9.1, 2026-10-24) ===")
# Mesure sur la cuve : chaque udp() + begin + send + close perdait ~97 octets de RAM interne (ESP-IDF/lwIP),
# soit ~0,6 Ko/min avec le ModBus UDP. Les sockets d'emission sont desormais gardees, une par adresse locale.
etatUDP["socketsEmission"] = {}
serveur["udp"]["id"] = 2
serveur["rangeExtender"]["activation"] = "ON"
tasmota.ipSta = "192.168.4.2"
socketsCreees = 0    socketsFermees = 0    liaisons = []
for i: 1 .. 10    udpFonctions.envoiUDP("UniCast", "192.168.4.1", "S" + str(i))    end
udpFonctions.envoiUDP("MultiCast", "", "S11")
verifie("esclave : 11 envois (unicast + multicast), UNE socket creee, aucune fermee", "11/1/0",
        str(size(liaisons)) + "/" + str(socketsCreees) + "/" + str(socketsFermees))
verifie("... toujours liee a la STA, port source 0 (C1, C2)", "192.168.4.2/224.3.0.1/4000/0", resume(dernier()))
# Maitre : unicast sur toutes les interfaces + multicast par son AP -> deux sockets
etatUDP["socketsEmission"] = {}
serveur["udp"]["id"] = 0
tasmota.ipSta = "192.168.0.43"
socketsCreees = 0    liaisons = []
for i: 1 .. 3    udpFonctions.envoiUDP("UniCast", "192.168.4.2", "M" + str(i))    udpFonctions.envoiUDP("MultiCast", "", "N" + str(i))    end
verifie("maitre : 6 envois, deux sockets ('' et l'AP)", "6/2", str(size(liaisons)) + "/" + str(socketsCreees))
# Envoi refuse sur une socket gardee (IP changee, Wi-Fi retombe) : fermee, renvoi sur une socket neuve
socketsCreees = 0    socketsFermees = 0    liaisons = []    journal = []
echecsEnvoi = 1
udpFonctions.envoiUDP("UniCast", "192.168.4.2", "M4")
verifie("envoi refuse sur la socket gardee : fermee, renvoye par une neuve, OK", "1/1/1/true",
        str(socketsFermees) + "/" + str(socketsCreees) + "/" + str(size(liaisons)) + "/" + str(journalise(">>>> M4 >>>> OK")))
socketsCreees = 0    liaisons = []
udpFonctions.envoiUDP("UniCast", "192.168.4.2", "M5")
verifie("... la socket neuve est gardee", "0/1", str(socketsCreees) + "/" + str(size(liaisons)))
# Adresses locales successives (DHCP) : jamais plus de MAX_SOCKETS_EMISSION sockets ouvertes
serveur["udp"]["id"] = 2
for i: 1 .. 10    tasmota.ipSta = "192.168.4." + str(10 + i)    udpFonctions.envoiUDP("UniCast", "192.168.4.1", "D" + str(i))    end
verifie("10 adresses STA successives : sockets ouvertes bornees", true,
        size(etatUDP["socketsEmission"]) <= udpFonctions.MAX_SOCKETS_EMISSION)
# Purge au plafond PUIS envoi refuse sur la socket neuve : elle ne doit pas rester dans la table (relecture)
etatUDP["socketsEmission"] = {}
for i: 1 .. udpFonctions.MAX_SOCKETS_EMISSION    tasmota.ipSta = "192.168.4." + str(30 + i)    udpFonctions.envoiUDP("UniCast", "192.168.4.1", "P" + str(i))    end
tasmota.ipSta = "192.168.4.99"
echecsEnvoi = 1
udpFonctions.emet("192.168.4.99", "192.168.4.1", 2000, "P9")
verifie("purge puis envoi refuse : socket fermee retiree de la nouvelle table", false, etatUDP["socketsEmission"].contains("192.168.4.99"))
echecsEnvoi = 0
# System#Save (avant un redemarrage) : les sockets d'emission sont fermees avec celles d'ecoute
var sauveRecep23 = etatUDP["udpReception"]
etatUDP["udpReception"] = [udp(), udp()]
socketsFermees = 0
var ouvertes23 = size(etatUDP["socketsEmission"])
essaie(def () udpFonctions.changementEtatDemarrage({"Save": 1}, "System", {"System": {"Save": 1}}, "UniCast") end)
verifie("System#Save : sockets d'emission fermees et oubliees", "true/0",
        str(socketsFermees >= 2 + ouvertes23) + "/" + str(size(etatUDP["socketsEmission"])))
etatUDP["udpReception"] = sauveRecep23
etatUDP["socketsEmission"] = {}
tasmota.ipSta = nil

print("")
print("=== 24. CONTROLE_UDP : chaque instance ne lit QUE sa socket (audit N5/P5.5, 2026-10-24) ===")
# Avant : les instances UniCast et MultiCast lisaient chacune les DEUX sockets en every_100ms (20 lectures/s pour 10).
class SocketCompteuse
  var msgs, lectures, remote_ip, remote_port
  def init(m) self.msgs = m self.lectures = 0 self.remote_ip = "192.168.4.2" self.remote_port = 51234 end
  def read() self.lectures += 1 return size(self.msgs) > 0 ? bytes().fromstring(self.msgs.pop(0)) : nil end
  def close() end
end
charge("controleUDP")
serveur["udp"]["id"] = 0
var uni24 = controleUDP.CONTROLE_UDP("UniCast", "", 2000)
var multi24 = controleUDP.CONTROLE_UDP("MultiCast", "224.3.0.1", 4000)
var sUni = SocketCompteuse([])
var sMulti = SocketCompteuse([])
etatUDP["udpReception"] = [sUni, sMulti]
for i: 1 .. 10    uni24.every_100ms()    multi24.every_100ms()    end
verifie("1 s des deux drivers : chaque socket lue 10 fois (avant : 20)", "10/10", str(sUni.lectures) + "/" + str(sMulti.lectures))
uni24.every_100ms()
verifie("l'instance UniCast ne lit pas la socket MultiCast", "11/10", str(sUni.lectures) + "/" + str(sMulti.lectures))
multi24.every_100ms()
verifie("l'instance MultiCast ne lit pas la socket UniCast", "11/11", str(sUni.lectures) + "/" + str(sMulti.lectures))
# Un message de chaque cote : chacun traite une fois, par l'instance de sa socket
journal = []
sUni.msgs = ["TESTUDP-U"]
sMulti.msgs = ["TESTUDP-M"]
uni24.every_100ms()
verifie("UniCast : son message lu, la socket MultiCast intacte", "0/1", str(size(sUni.msgs)) + "/" + str(size(sMulti.msgs)))
multi24.every_100ms()
verifie("MultiCast : son message lu a son tour", "0/0", str(size(sUni.msgs)) + "/" + str(size(sMulti.msgs)))
etatUDP["udpReception"] = sauveRecep

print("")
print("=== 25. P8.6 : peremption des fiches (Offline sans ImAlive depuis 2 x telePeriod) ===")
# Avant : resetClientsConnectes passait TOUT a Offline une seule fois, une telePeriod apres le demarrage du
# maitre (R1 : puis plus jamais de peremption ; R3 : tout Offline jusqu'aux ImAlive suivants).
var CLE_RIDEAU = "E80690AABBCC"
def lwt25(cle)
  var t = table()
  return (t != nil && isinstance(t.find(cle), map)) ? t[cle].find("lwt") : nil
end
# Le timer resetEsclaves echoit a l'instant ms (rappel capture par tasmota.rappelsTimer)
def tick25(ms)
  tasmota.horloge = ms
  var f = tasmota.rappelsTimer.find("resetEsclaves")
  tasmota.remove_timer("resetEsclaves")
  return f == nil ? "PAS DE TIMER" : essaie(f)
end
serveur["udp"]["id"] = 0
diverses = {"telePeriod": 300}
var init25 = {}
init25[CLE_CUVE] = {"config": configCuve(), "lwt": "Online"}
init25[CLE_RIDEAU] = {"config": {"dn": "Rideau"}, "lwt": "Online"}
init25["esclave9"] = "entree racine illisible"
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(init25)}
demarre21()
tasmota.rappelsTimer = {}
udpFonctions.lanceCyclePresentation()
verifie("maitre : timer de peremption arme", 1, tasmota.nbTimers("resetEsclaves"))
tasmota.horloge = 100000
imAlive(ficheCuve(true))
verifie("t=300 s : rien de perime avant 2 telePeriod (TEMOIN : avant, tout Offline)", "OK Online Online",
        tick25(300000) + " " + str(lwt25(CLE_CUVE)) + " " + str(lwt25(CLE_RIDEAU)))
verifie("... timer re-arme : verification a chaque telePeriod", 1, tasmota.nbTimers("resetEsclaves"))
verifie("t=600 s : rideau jamais vu -> Offline ; cuve vue a 100 s -> Online", "OK Online Offline",
        tick25(600000) + " " + str(lwt25(CLE_CUVE)) + " " + str(lwt25(CLE_RIDEAU)))
verifie("... passage journalise (UDP_PEREMPTION)", true, journalise("UDP_PEREMPTION: "))
verifie("... entree racine illisible conservee", "entree racine illisible", table().find("esclave9"))
tasmota.horloge = 650000
imAlive(ficheCuve(true))
tick25(900000)
tick25(1200000)
verifie("cuve vue a 650 s : encore Online a 1200 s (550 s < 600 s)", "Online", lwt25(CLE_CUVE))
verifie("t=1500 s : cuve muette depuis 850 s -> Offline", "OK Offline", tick25(1500000) + " " + str(lwt25(CLE_CUVE)))
var ecr25 = gestionFileFolder.ecritures
tick25(1800000)
verifie("rien a perimer : aucune ecriture flash", 0, gestionFileFolder.ecritures - ecr25)
tasmota.horloge = 1810000
imAlive(ficheCuve(true))
verifie("ImAlive apres peremption : de nouveau Online", "Online", lwt25(CLE_CUVE))
verifie("t=2100 s : cuve vue a 1810 s reste Online", "OK Online", tick25(2100000) + " " + str(lwt25(CLE_CUVE)))
tasmota.rappelsTimer = nil

print("")
print("=== 26. P8.8 : etatReseau, RgxClients x fiches par MAC, affiche sur /discovery ===")
# Avant : la discovery seule ne distinguait pas une panne Wi-Fi (esclave non associe au point d'acces)
# d'une panne UDP (associe mais muet), ni une fiche fantome (carte remplacee, meme IP autre MAC) (R4).
def fiche26(id, nom, ip, mac, typeConnection)
  var r = {}
  r["esclave" + str(id)] = {"id": id, "nom": nom, "IPAddress": ip, "adresseMAC": mac, "typeConnection": typeConnection,
                            "rangeExtender": {"activation": "ON", "id": id}}
  return r
end
var t26 = {}
t26["AA0000000001"] = fiche26(2, "Cuve", "192.168.4.2", "AA:00:00:00:00:01", "RangeExtender")      # associe, vivant
t26["AA0000000001"]["lwt"] = "Online"
t26["AA0000000002"] = fiche26(3, "Rideau", "192.168.4.3", "AA:00:00:00:00:02", "RangeExtender")    # associe, muet
t26["AA0000000002"]["lwt"] = "Offline"
t26["AA0000000003"] = fiche26(4, "Ancienne cuve", "192.168.4.4", "AA:00:00:00:00:03", "RangeExtender")   # fantome
t26["AA0000000003"]["lwt"] = "Offline"
t26["AA0000000004"] = fiche26(5, "Piscine", "192.168.4.5", "AA:00:00:00:00:04", "RangeExtender")   # absent du point d'acces
t26["AA0000000004"]["lwt"] = "Offline"
t26["AA0000000005"] = fiche26(6, "Cave", "192.168.4.6", "AA:00:00:00:00:05", "RangeExtender")      # IP divergente
t26["AA0000000005"]["lwt"] = "Online"
t26["AA0000000006"] = fiche26(7, "Differentiel", "192.168.0.50", "AA:00:00:00:00:06", "WifiClassique")   # sur la box
t26["AA0000000006"]["lwt"] = "Online"
t26["BB0000000000"] = {"config": {"dn": "Module MQTT seul", "ip": "192.168.0.60", "hn": "MODULE-MQTT"}, "lwt": "Online"}                      # pas un esclave UDP
t26["esclave9"] = "entree racine illisible"
var rgx26 = {"AA0000000001": {"IPAddress": "192.168.4.2", "RSSI": -22},
             "AA0000000002": {"IPAddress": "192.168.4.3", "RSSI": -70},
             "AA0000000005": {"IPAddress": "192.168.4.9", "RSSI": -40},
             "CC0000000007": {"IPAddress": "192.168.4.4", "RSSI": -50}}     # nouvelle carte, IP de l'ancienne cuve
var e26 = nil
verifie("etatReseau ne leve pas", "OK", essaie(def () e26 = discoveryFonctions.etatReseau(t26, rgx26) end))
def classe26(mac)
  for x: (e26 == nil ? [] : e26)    if x["mac"] == mac    return x["etat"]    end    end
  return nil
end
verifie("associe et UDP vivant", "ok", classe26("AA0000000001"))
verifie("associe mais UDP muet", "muet", classe26("AA0000000002"))
verifie("fiche fantome : son IP est tenue par une autre MAC associee", "fantome", classe26("AA0000000003"))
verifie("absent du point d'acces (panne Wi-Fi ou alimentation)", "absent", classe26("AA0000000004"))
verifie("IP divergente entre la fiche et le point d'acces", "ip", classe26("AA0000000005"))
verifie("esclave en Wi-Fi classique : hors point d'acces", "box", classe26("AA0000000006"))
verifie("client du point d'acces sans fiche ImAlive", "inconnu", classe26("CC0000000007"))
verifie("module MQTT sans fiche esclave : non classe", nil, classe26("BB0000000000"))
verifie("RgxClients absent (nil) : ne leve pas", "OK", essaie(def () discoveryFonctions.etatReseau(t26, nil) end))
# Fiche recue avec un 'config' qui n'est pas une map (fiche UDP/MQTT abimee) : la page /discovery ne casse pas
var t26b = {"AA00000000FF": {"esclave1": {"IPAddress": "192.168.4.9"}, "config": "abime", "lwt": "Online"}}
var nom26b = nil
verifie("fiche au 'config' non-map : ne leve pas", "OK", essaie(def () nom26b = discoveryFonctions.etatReseau(t26b, {})[0]["nom"] end))
verifie("... son nom affiche est sa MAC", "AA00000000FF", nom26b)
# Page /discovery du maitre (id rangeExtender 0) : le tableau d'etat reseau est affiche
serveur["rangeExtender"] = {"activation": "ON", "id": 0, "AP": {"IPAddress": "192.168.4.1"}}
tasmota.rgxClients = rgx26
gestionFileFolder.fichiers = {"/json/discovery.json": json.dump(t26), "/sd/css/main.css": ""}
webserver.envoye = []
webserver.termine = false
verifie("page /discovery ne leve pas", "OK", essaie(def () discoveryFonctions.affichePageDiscovery() end))
var html26 = webserver.envoye.concat("")
verifie("... tableau d'etat reseau affiche, page terminee", "true true true",
        str(string.find(html26, "tat r") >= 0) + " " + str(string.find(html26, "Ancienne cuve") >= 0) + " " + str(webserver.termine))
tasmota.rgxClients = {}

print("")
print("=== 27. P9.4 : CONTROLE_UDP.every_100ms sans map neuve a chaque tick, sans commande rejouee ===")
# Avant : 'var paramMSG = {}' a chaque tick de 100 ms, dans chacune des 2 instances. La map du tick est
# maintenant gardee tant qu'aucun message ne l'a remplie ; remplie, elle est remplacee (sinon le
# "prefix"/"commande" d'un message precedent ferait rejouer sa commande au message suivant).
serveur["udp"]["id"] = 0
var uni27 = controleUDP.CONTROLE_UDP("UniCast", "", 2000)
var s27 = SocketCompteuse([])
etatUDP["udpReception"] = [s27, SocketCompteuse([])]
var map27 = nil
verifie("la map du tick est un membre de l'instance", "OK", essaie(def () map27 = uni27.paramMSG end))
for i: 1 .. 5    uni27.every_100ms()    end
verifie("5 ticks sans message : meme map (aucune allocation)", true, map27 != nil && uni27.paramMSG == map27)
tasmota.cmds = []
s27.msgs = ["cmnd/garage/Power1 ON"]
uni27.every_100ms()
verifie("commande UDP executee une fois", "['Power1 ON']", str(tasmota.cmds))
s27.msgs = ["ModbusUDP 01030001001015C6"]      # trame ModBus : lireUDP ne pose ni "prefix" ni "commande"
uni27.every_100ms()
verifie("trame ModBus suivante : la commande precedente n'est pas rejouee", "['Power1 ON']", str(tasmota.cmds))
verifie("map remplie remplacee au tick suivant", true, uni27.paramMSG != map27)
etatUDP["udpReception"] = sauveRecep

print("")
print(string.format("TEST_DISCOVERY: %s (%i tests, %i echec(s))", echecs == 0 ? "OK" : "ECHEC", total, echecs))
