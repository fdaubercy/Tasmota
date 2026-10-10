# Banc de test Berry des fonctions deterministes de data/fs/modbusFonctions.be
# -----------------------------------------------------------------------------
# Charge le VRAI fichier (pas une copie) sous des globaux bouchonnes, et verifie
# les fonctions pures contre des attendus connus - AVANT de flasher un module.
#
# Lancer via son enveloppe Python (deduit racine + berry.exe, code de sortie) :
#     python outils_docs/scripts_python/banc_test_modbus.py
# Ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/banc_test_modbus.be
#
# Portee : logique deterministe seulement (checksum, construction de trame,
# decision d'appariement, decodage, commandes de reglage). Ne teste NI le timing,
# NI la file, NI la carte 16 reelle. La derniere ligne imprimee,
# BANC_MODBUS: OK|ECHEC, est lue par l'enveloppe Python pour son code de sortie.
#
# Argument optionnel : le dossier des sources a tester (defaut data/fs), pour
# eprouver un correctif sur une copie sans toucher a data/fs (ex. pendant un build,
# qui solidifie data/fs au demarrage de chaque environnement).
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/banc_test_modbus.be <dossier>

import global
import sys
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
# Bouchons des modules natifs/de framework importes par les fonctions testees
# (crc, persist, gestionFileFolder, tcpFonctions) : 'import' les trouve ici.
sys.path().push("outils_docs/scripts_python/bouchons_berry")

# --- globaux fournis par le firmware sur l'appareil, bouchonnes ici ---
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var journal = []                       # messages passes a log() (quelques tests les lisent)
def log(m, l) journal.push(str(m)) end
# Vrai si un message du journal contient 'motif'
def journalise(motif)
  import string
  for l : journal    if string.find(l, motif) >= 0    return true    end    end
  return false
end
class TasmotaStub
  var publie                           # dernier JSON passe a publish_result (verifie par le banc)
  var cmds                             # commandes passees a tasmota.cmd (verifiees par le banc)
  var horloge                          # heure locale renvoyee par rtc(), pilotee par le banc
  var power                            # etats des relais renvoyes par get_power()
  var ms                               # millis() pilote par le banc (armeTimer P4)
  def init() self.cmds = [] self.horloge = 0 self.power = [] self.ms = 0 end
  def time_reached(t) return self.ms >= t end
  var publies                          # tous les JSON publies (G2 : plusieurs trames par lecture)
  def publish_result(s, topic) self.publie = s if self.publies != nil self.publies.push(s) end end
  def yield() end
  def rtc() return {"local": self.horloge} end
  def get_power() return self.power end
  var retourCmd                        # ce que renvoie cmd() (defaut "" ; une map pour pompeQueue)
  var regles                           # [nom, id] des add_rule / remove_rule, si non nil
  def cmd(c, m) self.cmds.push(c) return self.retourCmd == nil ? "" : self.retourCmd end
  def millis(d) return self.ms + (d == nil ? 0 : d) end
  def delay(ms) end
  def set_timer(a, b, c) end
  def remove_timer(nom) end
  var rappels                          # id -> fonction des add_rule, si non nil (section 23 : simulateur de carte)
  def add_rule(a, b, c) if self.regles != nil self.regles.push("+" + str(a) + "/" + str(c)) end if self.rappels != nil self.rappels[c] = b end end
  def remove_rule(a, c) if self.regles != nil self.regles.push("-" + str(a) + "/" + str(c)) end end
  def add_cron(a, b, c) end
  def remove_cron(nom) end
  def resp_cmnd(x) end
end
class Driver end                       # classe de base des drivers Tasmota
var tasmota = TasmotaStub()
var modules = {}
var drivers = {"ModBus": {"typeComm": {"Serial":"ON","TCP":"OFF","UDP":"OFF"},
                          "environnement": {}, "id": 0, "activationReponseCMD":"ON"}}
var serveur = {"tcp": {"activation":"OFF"}, "udp": {"activation":"OFF"}}
var persist = {}
var boolMute = true
var diverses = {}
var tcpFonctions = nil
var udpFonctions = nil
var gestionFileFolder = nil
var globalFonctions = nil
var serial = nil
var mqtt = nil
var introspect = nil
var tcpclientasync = nil
var modbusFonctions = nil              # sera (re)affecte par le fichier charge
var modBus_TasmotaSlaveModBus = nil    # idem
var logFonctions = nil                 # idem : la VRAIE fonction de log commune (seuil par cible)

# --- charge les vrais modules ---
print(">>> sources testees :", SOURCES)
var f = open(SOURCES + "/logFonctions.be", "r")
var src = f.read()
f.close()
compile(src)()
print(">>> logFonctions charge :", logFonctions != nil ? "OK" : "ECHEC")
f = open(SOURCES + "/modbusFonctions.be", "r")
src = f.read()
f.close()
compile(src)()
print(">>> modbusFonctions charge :", modbusFonctions != nil ? "OK" : "ECHEC")
f = open(SOURCES + "/modBus_TasmotaSlaveModBus.be", "r")
src = f.read()
f.close()
compile(src)()
print(">>> modBus_TasmotaSlaveModBus charge :", modBus_TasmotaSlaveModBus != nil ? "OK" : "ECHEC")

# Appelle f() et renvoie son resultat, ou "EXCEPTION <type>" si elle leve :
# un defaut qui plante doit apparaitre comme un resultat, pas arreter le banc.
def essaie(fn)
  try
    return fn()
  except .. as e, m
    return "EXCEPTION " + str(e)
  end
end

# --- mini-harnais d'assertions ---
var total = 0
var echecs = 0                          # echecs NON attendus (font echouer le banc)
var bugs_connus = 0                     # echecs attendus, documentes (n'echouent pas)
def verifie(nom, attendu, obtenu)
  import string
  total += 1
  var ok = (attendu == obtenu)
  if !ok    echecs += 1    end
  print(string.format("[%s] %-46s attendu=%s  obtenu=%s",
        ok ? "PASS" : "FAIL", nom, str(attendu), str(obtenu)))
end
# Pour un defaut CONNU et documente : on verifie qu'il est TOUJOURS present.
# Le jour ou il est corrige, cette ligne passe [!] CORRIGE et signale qu'il faut
# la transformer en verifie() normal.
def bug_connu(nom, attendu_apres_correction, obtenu, ref)
  import string
  total += 1
  var corrige = (attendu_apres_correction == obtenu)
  if corrige
    echecs += 1                         # un bug connu qui disparait DOIT alerter
    print(string.format("[!] %-46s CORRIGE (%s) -> repasser en verifie()", nom, ref))
  else
    bugs_connus += 1
    print(string.format("[BUG CONNU] %-40s %s ; obtenu=%s", nom, ref, str(obtenu)))
  end
end

print("")
print("=== 1. crc16modbus : 3 vecteurs de PROTOCOLE_MODBUS.md section 8 ===")
# La fonction renvoie les 2 octets de CRC deja dans l'ordre d'emission (swap final),
# tel qu'ils sont apposes a la trame par prepareTrame (Trame.add(crc, -2)).
verifie("crc 01 03 00 01 00 10  -> 0x15C6", 0x15C6, modbusFonctions.crc16modbus(bytes("010300010010")))
verifie("crc 01 06 00 01 01 00  -> 0xD99A", 0xD99A, modbusFonctions.crc16modbus(bytes("010600010100")))
verifie("crc FF 03 00 FF 00 01  -> 0xA1E4", 0xA1E4, modbusFonctions.crc16modbus(bytes("FF0300FF0001")))

print("")
print("=== 2. prepareTrame : commande de sondage 0x03 (16 registres) ===")
# Attendu (doc PROTOCOLE_MODBUS.md section 8) : 01 03 00 01 00 10 15 C6
#   -> quantite = 0x0010 = 16 registres.
# Corrige le 2026-07-24 : le bloc d'allocation du tampon d'ecriture ne double plus
# nbRegistres pour une trame SANS donnees (writeDataSize == 0), donc une LECTURE
# garde son vrai compte de registres. Cf. modbusFonctions.be, garde `writeDataSize > 0`.
# .tohex() renvoie des MAJUSCULES ; les attendus le sont donc aussi. La trame
# complete (CRC compris) est exactement le vecteur de la doc : 01 03 00 01 00 10 15 C6.
var sonde = {"DeviceAddress":1, "FunctionCode":3, "StartAddress":1,
             "type":"uint16", "Count":16, "Values":[]}
verifie("trame sondage 0x03 complete (doc)",
        "010300010010" + "15C6",
        modbusFonctions.prepareTrame(sonde, "Commande").tohex())

# Temoin : une 2e lecture 0x04 de 4 registres doit donner la quantite 0x0004, pas 0x0008.
# On ne compare que les 6 premiers octets (adr, fct, adresse, quantite) - CRC ignore.
var sonde4 = {"DeviceAddress":2, "FunctionCode":4, "StartAddress":1,
              "type":"uint16", "Count":4, "Values":[]}
var t4 = modbusFonctions.prepareTrame(sonde4, "Commande").tohex()
verifie("trame lecture 0x04 (quantite 0x0004, 6 premiers octets)",
        "020400010004", t4[0..11])

print("")
print("=== 3. apparieReponse : decision de la phase 1 bis ===")
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress":1, "FunctionCode":3, "StartAddress":1, "Count":16, "type":"uint16"}}
verifie("reponse conforme -> true", true,
        modbusFonctions.apparieReponse({"DeviceAddress":1, "FunctionCode":3, "Values":[0]}))
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress":1, "FunctionCode":3, "StartAddress":1, "Count":16, "type":"uint16"}}
verifie("hors-sequence (fct 6 != 3) -> false", false,
        modbusFonctions.apparieReponse({"DeviceAddress":1, "FunctionCode":6, "Values":[0]}))
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress":1, "FunctionCode":3, "StartAddress":1, "Count":16, "type":"uint16"}}
verifie("telemetrie (Automatique=true) -> false", false,
        modbusFonctions.apparieReponse({"DeviceAddress":1, "FunctionCode":3, "Automatique":true, "Values":[0]}))
modbusFonctions.etat()["enVol"] = nil
verifie("rien en vol -> false", false,
        modbusFonctions.apparieReponse({"DeviceAddress":1, "FunctionCode":3, "Values":[0]}))

print("")
import string
print("=== 4. prepareTrame : reponses d'esclave et push spontane (valeurs uint8) ===")
# Reponse 0x06 d'un esclave = echo de la commande. decrypteMSG la decode en
# Count=2, Values=[octet haut, octet bas], type absent (-> int8). Vecteur de la doc
# (PROTOCOLE_MODBUS.md section 8) : 01 06 00 01 01 00 D9 9A.
# Non-regression : deja correcte AVANT le correctif du point 1, mais par accident (la
# boucle ecrivait les 2 octets au 1er tour, puis un controle errone l'interrompait).
var rep06 = {"DeviceAddress":1, "FunctionCode":6, "StartAddress":1, "Count":2, "Values":[1, 0]}
verifie("reponse 0x06 uint8 (echo, doc)", "010600010100" + "D99A",
        essaie(def () return modbusFonctions.prepareTrame(rep06, "Reponse").tohex() end))
# En mode bit (0x01/0x02/0x0F), une valeur uint8 (0xFF/0x00) = UN BIT, empaquete
# octet par octet, bit de poids faible d'abord : c'est le format standard que le
# maitre serie (ModBusSend, code C++ de Tasmota) sait decoder.
def trameAvecCrc(hex)
  return hex + string.format("%04X", modbusFonctions.crc16modbus(bytes(hex)))
end
# Push d'un interrupteur tel que globalFonctions.be:224-243 le construit.
var push02 = {"DeviceAddress":2, "FunctionCode":0x02 | 0x80, "FunctionName":"LECTURE_ENTREES_DISCRETES",
              "StartAddress":160, "type":"uint8", "Count":1, "Values":[0xFF]}
verifie("push interrupteur 0x82 : 1 bit a 1", trameAvecCrc("02820101"),
        essaie(def () return modbusFonctions.prepareTrame(push02, "Reponse").tohex() end))
# Reponse d'un esclave a une lecture 0x02 de 3 entrees : ON, OFF, ON -> 0b101 = 0x05.
var rep02 = {"DeviceAddress":2, "FunctionCode":0x02, "StartAddress":160,
             "type":"uint8", "Count":3, "Values":[0xFF, 0x00, 0xFF]}
verifie("reponse 0x02 : 3 bits ON/OFF/ON -> 0x05", trameAvecCrc("02020105"),
        essaie(def () return modbusFonctions.prepareTrame(rep02, "Reponse").tohex() end))
# Push analogique (globalFonctions.be:412) : non-regression, la trame est deja
# bien formee au format reponse (nb octets 04 + float big-endian).
var push04 = {"DeviceAddress":2, "FunctionCode":0x04 | 0x80, "FunctionName":"LECTURE_REGISTRES_ENTREES",
              "StartAddress":1312, "type":"float", "Count":1, "Values":[21.5]}
verifie("push analogique 0x84 float 21.5", "02840441AC00000359",
        essaie(def () return modbusFonctions.prepareTrame(push04, "Reponse").tohex() end))

print("")
print("=== 5. decrypteMSG : decodage cote maitre ===")
def decode(trame)
  var p = {"T": {"Trame": trame, "Info": {}, "DeviceAddress": 0, "FunctionCode": 0, "FunctionName": "",
                 "StartAddress": 0, "Length": 0, "Count": 0, "Values": [], "CRC": 0, "Erreur": 0}}
  modbusFonctions.decrypteMSG(p, "T")
  return p["T"]
end
# Temoin : une vraie COMMANDE 0x02 du maitre se decode sans erreur.
var cmd02 = modbusFonctions.prepareTrame({"DeviceAddress":2, "FunctionCode":2, "StartAddress":160,
                                          "type":"uint8", "Count":1, "Values":[]}, "Commande")
var d = decode(cmd02)
verifie("temoin commande 0x02 : Erreur / StartAddress", "0/160", str(d["Erreur"]) + "/" + str(d["StartAddress"]))
# Ancien defaut de FORMAT, resolu le 2026-09-29 par conception (options A + B) :
# le push etait emis au format REPONSE 0x82/0x84, sans le registre, et rejete par
# decrypteMSG. L'esclave n'emet plus ce format : il pousse une ECRITURE 0x10, qui
# porte son registre (sections 8 a 10).

print("")
print("=== 6. discovery.json -> clients TCP (ImAlive) et IP UDP : vraie forme de la table ===")
# Le maitre ouvre un client TCP par esclave de SON groupe qui publie un serveur ModBus TCP.
# Table sous la forme que produisent ses ecrivains (discoveryFonctions, decouverte MQTT,
# ImAlive UDP) : {MAC: {"maitre"|"esclaveN": fiche, "lwt", "config"}}. Jusqu'au 2026-09-30 ce
# test utilisait une table a TROIS niveaux fabriquee pour le code : il etait vert alors qu'avec
# la vraie table aucun client n'etait jamais cree.
class ClientStub
  var ip, port
  def connected() return false end
  def connect(ip, port) self.ip = ip  self.port = port  return true end
end
tcpclientasync = ClientStub
import gestionFileFolder
var tableGarage = '{' +
  '"AABBCC000000": {"lwt": "Online", "config": {"dn": "Serveur"}, "maitre": {"id": 0, "groupTopic": "tasmotas/garage", "IPAddress": "192.168.0.43", "ModBus": {"id": 0, "TCP": {"IPAddress": "192.168.0.43"}}}},' +
  '"E80690112233": {"lwt": "Online", "config": {"dn": "Cuve"}, "esclave2": {"id": 2, "groupTopic": "tasmotas/garage", "IPAddress": "192.168.4.2", "ModBus": {"id": 2, "TCP": {"IPAddress": "192.168.4.2"}}}},' +
  '"E80690445566": {"esclave3": {"id": 3, "groupTopic": "tasmotas/garage", "IPAddress": "192.168.4.3", "ModBus": {"id": 3, "UDP": {"IPAddress": "192.168.4.3"}}}},' +
  '"CAFE00000002": {"esclave2": {"id": 2, "groupTopic": "tasmotas/cave", "IPAddress": "192.168.0.99", "ModBus": {"id": 2, "TCP": {"IPAddress": "192.168.0.99"}}}},' +
  '"E80690778899": {"esclave4": {"id": 4, "IPAddress": "192.168.4.4", "ModBus": {"id": 4, "TCP": {"IPAddress": "192.168.4.4"}}}}' +
  '}'
gestionFileFolder.contenu = tableGarage
var sauveDrivers = drivers
var sauveServeur = serveur
drivers = {"ModBus": {"typeComm": {"TCP":"ON"}, "environnement": {}, "id": 0}}
serveur = {"tcp": {"activation":"ON"}, "udp": {"activation":"OFF"}, "adresseMAC": "AA:BB:CC:00:00:00",
           "mqtt": {"groupTopic1": "tasmotas/garage"}}
modbusFonctions.etat()["clients"] = [nil, nil, nil, nil, nil, nil]
var r = essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "ImAlive ON", nil)
                      var c = modbusFonctions.etat()["clients"]
                      var ips = []
                      for i : 0 .. 5    ips.push(c[i] != nil ? c[i].ip : "-")    end
                      return ips.concat(" ") end)
# clients[0] : pas de client vers le maitre (lui-meme) ; [2] cuve du GARAGE, pas celle de la cave ;
# [3] sans ModBus TCP -> pas de client ; [4] fiche d'avant 'groupTopic' -> acceptee.
verifie("ImAlive : clients TCP par id (0 a 5)", "- - 192.168.4.2 - 192.168.4.4 -", r)
# Borne : un id hors du tableau (1 a 5) est journalise et ignore, sans exception.
gestionFileFolder.contenu = '{"E80690112233": {"esclave9": {"id": 9, "ModBus": {"id": 9, "TCP": {"IPAddress": "192.168.4.9"}}}}}'
modbusFonctions.etat()["clients"] = [nil, nil, nil, nil, nil, nil]
r = essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "ImAlive ON", nil)
                  var n = 0
                  for c : modbusFonctions.etat()["clients"]   if c != nil  n += 1  end   end
                  return "clients crees=" + str(n) end)
verifie("ImAlive esclave id 9 (hors 1-5) : ignore sans exception", "clients crees=0", r)
# Table absente (readFile rend false, comme le vrai module) : aucune exception, aucun client.
gestionFileFolder.contenu = false
modbusFonctions.etat()["clients"] = [nil, nil, nil, nil, nil, nil]
verifie("ImAlive, discovery.json absent : sans exception", "clients crees=0",
        essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "ImAlive ON", nil)
                      var n = 0
                      for c : modbusFonctions.etat()["clients"]   if c != nil  n += 1  end   end
                      return "clients crees=" + str(n) end))
# Recherche d'IP de l'envoi UDP (fichesModbus) : l'esclave d'id 2 du GARAGE.
gestionFileFolder.contenu = tableGarage
var ipsId2 = []
for fiche : modbusFonctions.fichesModbus()    if fiche["ModBus"]["id"] == 2    ipsId2.push(fiche["IPAddress"])    end    end
verifie("fichesModbus : id 2 = cuve du garage seule", "['192.168.4.2']", str(ipsId2))
# Temoin : sans groupe local, pas de filtre -> la cave (meme id) reapparait.
serveur["mqtt"]["groupTopic1"] = ""
ipsId2 = []
for fiche : modbusFonctions.fichesModbus()    if fiche["ModBus"]["id"] == 2    ipsId2.push(fiche["IPAddress"])    end    end
verifie("temoin sans groupTopic1 : 2 fiches d'id 2", 2, size(ipsId2))
serveur["mqtt"]["groupTopic1"] = "tasmotas/garage"
# envoiMsgModbusUDP (repli quand le serie est coupe) : ne leve plus, et la METHODE d'envoi
# est inchangee (maitre -> MultiCast via l'interface 192.168.4.1, reglee sur essais reels).
import udpFonctions as udpStub6
udpStub6.envois = []
drivers = {"ModBus": {"typeComm": {"Serial":"OFF", "UDP":"ON", "TCP":"OFF"}, "environnement": {}, "id": 0}}
serveur["udp"] = {"activation": "ON"}
verifie("envoiMsgModbusUDP (maitre) : sans exception", "OK",
        essaie(def () modbusFonctions.envoiMsgModbusUDP(bytes("0203000100011234"), "Commande") return "OK" end))
verifie("envoiMsgModbusUDP : methode inchangee", "MultiCast|192.168.4.1",
        size(udpStub6.envois) == 1 ? udpStub6.envois[0][0] + "|" + udpStub6.envois[0][1] : str(udpStub6.envois))
gestionFileFolder.contenu = "{}"
drivers = sauveDrivers
serveur = sauveServeur
modbusFonctions.etat()["clients"] = [nil, nil, nil, nil, nil, nil]

print("")
print("=== 7. log() du driver SlaveModBus : seuil de la cible slaveModbus ===")
# Depuis le 2026-10-04, la methode log du driver delegue a logFonctions.log(msg, niveau,
# "slaveModbus") ; le seuil est la cle "log" de drivers.ModBus.environnement.TasmotaSlaveModBus
# (logFonctions.lieu). Contrat : les erreurs passent toujours, le reste suit le seuil.
sauveDrivers = drivers
drivers = {"ModBus": {"environnement": {"TasmotaSlaveModBus": {"log": "erreur",
           "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"}}}}}
logFonctions.etat()["seuils"] = {}     # vide le cache des seuils : relecture du persist ci-dessus
journal = []
var slaveLog = modBus_TasmotaSlaveModBus.MODBUS_TASMOTA_SLAVE.log
slaveLog(nil, "BANC_SLAVE: info sous seuil erreur", LOG_LEVEL_INFO)
slaveLog(nil, "BANC_SLAVE: erreur sous seuil erreur", LOG_LEVEL_ERREUR)
verifie("seuil erreur : info bloquee (temoin)", false, journalise("BANC_SLAVE: info"))
verifie("seuil erreur : erreur emise", true, journalise("BANC_SLAVE: erreur"))
drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"]["log"] = "detail"
logFonctions.etat()["seuils"] = {}
slaveLog(nil, "BANC_SLAVE: detail sous seuil detail", LOG_LEVEL_DEBUG_PLUS)
verifie("seuil detail : detail emis", true, journalise("BANC_SLAVE: detail"))
drivers = sauveDrivers
logFonctions.etat()["seuils"] = {}

print("")
print("=== 8. Ecriture 0x10 standard : emission, decodage, reconversion ===")
# Format standard : [id][10][adresse 2][quantite de REGISTRES 2][nb octets 1][donnees][CRC]
var w160 = {"DeviceAddress":3, "FunctionCode":0x10, "StartAddress":160, "type":"uint16", "Count":1, "Values":[0xFF]}
verifie("0x10 interrupteur 160 = 0x00FF (1 registre)", trameAvecCrc("031000A000010200FF"),
        essaie(def () return modbusFonctions.prepareTrame(w160, "Commande").tohex() end))
var w1312 = {"DeviceAddress":2, "FunctionCode":0x10, "StartAddress":1312, "type":"float", "Count":1, "Values":[21.5]}
var t1312 = modbusFonctions.prepareTrame(w1312, "Commande")
verifie("0x10 thermometre 1312 = 21.5 (2 registres)", trameAvecCrc("021005200002" + "04" + "41AC0000"), t1312.tohex())
var w352 = {"DeviceAddress":2, "FunctionCode":0x10, "StartAddress":352, "type":"uint32", "Count":1, "Values":[123456]}
var t352 = modbusFonctions.prepareTrame(w352, "Commande")
verifie("0x10 compteur 352 = 123456 (2 registres)", trameAvecCrc("021001600002" + "04" + "0001E240"), t352.tohex())
# Reponse = echo adresse + quantite, sans donnees
verifie("0x10 reponse (echo standard)", trameAvecCrc("021005200002"),
        essaie(def () return modbusFonctions.prepareTrame(w1312, "Reponse").tohex() end))
# Le maitre relit la trame : decrypteMSG (format standard) puis motsVersValeurs
d = decode(t1312)
verifie("decode 0x10 float : Erreur / StartAddress / mots", "0/1312/[16812, 0]",
        str(d["Erreur"]) + "/" + str(d["StartAddress"]) + "/" + str(d["Values"]))
verifie("motsVersValeurs float -> 21.5", "21.5", str(modbusFonctions.motsVersValeurs(d["Values"], "float")[0]))
d = decode(t352)
verifie("decode 0x10 uint32 -> 123456", "0/352/123456",
        str(d["Erreur"]) + "/" + str(d["StartAddress"]) + "/" + str(modbusFonctions.motsVersValeurs(d["Values"], "uint32")[0]))
d = decode(modbusFonctions.prepareTrame(w160, "Commande"))
verifie("decode 0x10 interrupteur -> mot 0x00FF", "0/160/255",
        str(d["Erreur"]) + "/" + str(d["StartAddress"]) + "/" + str(modbusFonctions.motsVersValeurs(d["Values"], "uint16")[0]))

print("")
print("=== 9. pousseEtat : push esclave -> maitre (option B, UDP) ===")
import udpFonctions as udpStub
sauveDrivers = drivers
sauveServeur = serveur
drivers = {"ModBus": {"activation": "ON", "id": 3, "typeComm": {"Serial":"ON", "TCP":"OFF", "UDP":"ON"}, "environnement": {}}}
serveur = {"udp": {"activation": "ON"}, "tcp": {"activation": "OFF"}}
udpStub.envois = []
modbusFonctions.etat()["seqPush"] = 0
modbusFonctions.pousseEtat(160, "uint16", [0xFF])
verifie("push interrupteur : datagramme emis (seq 1)", "MultiCast||ModbusPushUDP 1 " + trameAvecCrc("031000A000010200FF"),
        size(udpStub.envois) == 1 ? udpStub.envois[0][0] + "|" + udpStub.envois[0][1] + "|" + udpStub.envois[0][2] : str(udpStub.envois))
# Temoins : rien ne doit partir si l'UDP ModBus est coupe, ni depuis le maitre.
udpStub.envois = []
drivers["ModBus"]["typeComm"]["UDP"] = "OFF"
verifie("temoin typeComm.UDP OFF : rien emis", "nil / 0", str(modbusFonctions.pousseEtat(160, "uint16", [0xFF])) + " / " + str(size(udpStub.envois)))
drivers["ModBus"]["typeComm"]["UDP"] = "ON"
drivers["ModBus"]["id"] = 0
verifie("temoin maitre (id 0) : rien emis", "nil / 0", str(modbusFonctions.pousseEtat(160, "uint16", [0xFF])) + " / " + str(size(udpStub.envois)))
drivers = sauveDrivers
serveur = sauveServeur

print("")
print("=== 10. Reception cote maitre : lireMsgModbus UDP + handler TasmotaSlaveModBus ===")
import json
sauveDrivers = drivers
sauveServeur = serveur
var sauveModules = modules
serveur = {"udp": {"activation": "ON"}, "tcp": {"activation": "OFF"}, "mqtt": {"topic": "garage"}}
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON", "TCP":"OFF", "UDP":"ON"},
           "environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
               "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"},
               "TasmotaSlaveModBus2": {"activation": "ON", "id": 3, "name": "rideau"}}}}}
# lireMsgModbus : la trame UDP d'un push est decodee et republiee AVEC son marqueur.
modbusFonctions.lireMsgModbus("ModbusReceivedUDP", {"Trame": bytes("031000A000010200FF" + string.format("%04X", modbusFonctions.crc16modbus(bytes("031000A000010200FF")))),
                                                    "Info": {}, "Automatique": true})
var pub = json.load(str(tasmota.publie))
pub = pub != nil ? pub["ModbusReceivedUDP"] : {}
verifie("lireMsgModbus UDP : adresse/registre/valeur/Automatique", "3/160/[255]/true",
        str(pub.find("DeviceAddress")) + "/" + str(pub.find("StartAddress")) + "/" + str(pub.find("Values")) + "/" + str(pub.find("Automatique")))

# Handler du maitre, appele comme la regle 'ModbusReceived...#DeviceAddress==<id>'
# Sous-classe du vrai driver : init() court-circuite (dependances firmware), vraies methodes.
class MaitreStub : modBus_TasmotaSlaveModBus.MODBUS_TASMOTA_SLAVE
  def init() self.dataJson = {"TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {}, "TasmotaSlaveModBus2": {}}}
             self.derniersContacts = {} self.esclavesMuets = {} end
  def log(m, l) end
end
var maitre = MaitreStub()
def appareils()
  return {"garage": {"activation": "ON", "environnement": {
    "interrupteurs": {"interrupteur1": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus2", "type": 160, "idModBus": 1, "id": 1, "etat": "OFF", "SwitchMode": 1}},
    "thermometres":  {"thermometre1":  {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus1", "type": 1312, "idModBus": 1, "id": 1, "value": 0.0, "serialNumber": "x"}}}}}
end
def recoit(adresse, voie, contenu)
  var m = {}
  m[voie] = contenu
  maitre.recupereReponseModBus(adresse, voie + "#DeviceAddress==" + str(adresse), m)
end
var inter = def () return modules["garage"]["environnement"]["interrupteurs"]["interrupteur1"]["etat"] end
# (a) push UDP d'un interrupteur du rideau -> etat ON, sans rien acquitter
modules = appareils()
modbusFonctions.etat()["enVol"] = nil
recoit(3, "ModbusReceivedUDP", {"DeviceAddress": 3, "FunctionCode": 0x10, "FunctionName": "ECRITURE_REGISTRES_HOLDER",
                                "StartAddress": 160, "Count": 1, "Values": [255], "Automatique": true})
verifie("push 0x10 interrupteur rideau -> etat maitre", "ON", inter())
# (b) push UDP du thermometre de la cuve : 2 registres -> 21.5
recoit(2, "ModbusReceivedUDP", {"DeviceAddress": 2, "FunctionCode": 0x10, "FunctionName": "ECRITURE_REGISTRES_HOLDER",
                                "StartAddress": 1312, "Count": 2, "Values": [16812, 0], "Automatique": true})
verifie("push 0x10 thermometre cuve -> valeur maitre", "21.5",
        str(modules["garage"]["environnement"]["thermometres"]["thermometre1"]["value"]))
# (c) releve serie (option A) : reponse 0x02 standard = bit empaquete 0x01 -> ON ; 0x00 -> OFF
modules = appareils()
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 3, "FunctionCode": 2, "StartAddress": 160, "Count": 1, "type": "uint8"}}
recoit(3, "ModbusReceived", {"DeviceAddress": 3, "FunctionCode": 2, "Values": [1]})
verifie("reponse serie 0x02 bit 0x01 -> ON", "ON", inter())
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 3, "FunctionCode": 2, "StartAddress": 160, "Count": 1, "type": "uint8"}}
recoit(3, "ModbusReceived", {"DeviceAddress": 3, "FunctionCode": 2, "Values": [0]})
verifie("temoin reponse serie 0x02 bit 0x00 -> OFF", "OFF", inter())
# (d) temoin : une 0x10 NON marquee (reponse a une commande WS2812) ne touche aucun etat
modules = appareils()
modbusFonctions.etat()["enVol"] = nil
recoit(3, "ModbusReceivedUDP", {"DeviceAddress": 3, "FunctionCode": 0x10, "FunctionName": "ECRITURE_REGISTRES_HOLDER",
                                "StartAddress": 160, "Count": 1, "Values": [255]})
verifie("temoin 0x10 non sollicitee sans marqueur : etat inchange", "OFF", inter())
modbusFonctions.etat()["enVol"] = nil
modules = sauveModules
drivers = sauveDrivers
serveur = sauveServeur

print("")
print("=== 11. releveEsclaves : releve periodique du maitre (option A) ===")
# Sous-classe qui court-circuite init() (dependances firmware) mais garde les vraies methodes.
class MaitreReleve : modBus_TasmotaSlaveModBus.MODBUS_TASMOTA_SLAVE
  def init() self.dataJson = {} end
  def log(m, l) end
end
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON"},
           "environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
               "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"},
               "TasmotaSlaveModBus2": {"activation": "ON", "id": 3, "name": "rideau"}}}}}
modules = appareils()
# un appareil non virtuel (ignore), un relai virtuel (lecture 0x01) et des LEDs WS2812 (non relues)
modules["garage"]["environnement"]["interrupteurs"]["interrupteur9"] = {"activation": "ON", "virtuel": "OFF", "type": 160, "id": 9}
modules["garage"]["environnement"]["relais"] = {"relai2": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus2", "type": 256, "idModBus": 1, "id": 2},
                                                "relai1": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus1", "type": 1376, "idModBus": 1, "id": 1}}
var envoyes = []
var vraiEnvoi = modbusFonctions.envoiMsgModbus
modbusFonctions.envoiMsgModbus = def (t, typeMsg, id) envoyes.push(string.format("%i/%i/%i/%s/%i", t["DeviceAddress"], t["FunctionCode"], t["StartAddress"], t["type"], t["Count"])) end
# L'ordre de parcours d'une map n'est pas garanti : on compare par presence.
def resume(l)
  return str(size(l)) + " : cuve=" + str(l.find("2/4/1312/float/1") != nil) + " rideau=" + str(l.find("3/2/160/uint8/1") != nil)
         + " relai=" + str(l.find("3/1/256/uint8/1") != nil)
end
var m = MaitreReleve()
m.releveEsclaves()
verifie("releve : 3 demandes (thermo 0x04, inter 0x02, relai 0x01)", "3 : cuve=true rideau=true relai=true", resume(envoyes))
# Temoin : esclave desactive -> aucune demande pour lui
drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus2"]["activation"] = "OFF"
envoyes = []
m.releveEsclaves()
verifie("temoin esclave rideau desactive : seule la cuve est relevee", "1 : cuve=true rideau=false relai=false", resume(envoyes))
modbusFonctions.envoiMsgModbus = vraiEnvoi
modules = sauveModules
drivers = sauveDrivers

print("")
print("=== 12. Esclave : commande 0x06 d'un relai -> Power<id>, pas Power<StartAddress> ===")
verifie("idRelai : 224/225 (Relais) -> 1/2", "1/2", essaie(def () return str(modbusFonctions.idRelai(224)) + "/" + str(modbusFonctions.idRelai(225)) end))
verifie("idRelai : 256/257 (Relais_i) -> 1/2", "1/2", essaie(def () return str(modbusFonctions.idRelai(256)) + "/" + str(modbusFonctions.idRelai(257)) end))
verifie("temoin idRelai : adressage direct 3 -> 3", 3, essaie(def () return modbusFonctions.idRelai(3) end))
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 3, "activationReponseCMD": "OFF", "typeComm": {"Serial":"ON"}, "environnement": {}}}
tasmota.cmds = []
# Commande du maitre pour relai2 (type 256, idModBus 1), etat ON -> valeur 0x01
modbusFonctions.executeCmdModbus({"DeviceAddress": 3, "FunctionCode": 6, "FunctionName": "ECRITURE_REGISTRE_UNIQUE",
                                  "StartAddress": 256, "Count": 2, "Values": [0x01, 0]})
verifie("esclave 0x06 StartAddress 256 valeur 0x01 -> Power1 OFF", "['Power1 OFF']", str(tasmota.cmds))
tasmota.cmds = []
modbusFonctions.executeCmdModbus({"DeviceAddress": 3, "FunctionCode": 6, "FunctionName": "ECRITURE_REGISTRE_UNIQUE",
                                  "StartAddress": 225, "Count": 2, "Values": [0x02, 0]})
verifie("esclave 0x06 StartAddress 225 valeur 0x02 -> Power2 ON", "['Power2 ON']", str(tasmota.cmds))
drivers = sauveDrivers

print("")
print("=== 13. Relais d'esclave : lecture 0x01, etat constate vs commande ===")
# (a) esclave : reponse 0x01 = etat reel du relai (bit 0 = Power ON)
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 3, "activationReponseCMD": "ON", "typeComm": {"Serial":"ON"}, "environnement": {}}}
var envoyesEsclave = []
vraiEnvoi = modbusFonctions.envoiMsgModbus
modbusFonctions.envoiMsgModbus = def (t, typeMsg, id) envoyesEsclave.push(modbusFonctions.prepareTrame(t, typeMsg).tohex()) end
tasmota.power = [true, false]
var lit = def (sa) return {"DeviceAddress": 3, "FunctionCode": 1, "FunctionName": "LECTURE_COILS", "StartAddress": sa, "Count": 1, "Values": []} end
modbusFonctions.executeCmdModbus(lit(256))
modbusFonctions.executeCmdModbus(lit(257))
verifie("esclave 0x01 relai 1 ON / relai 2 OFF", str([trameAvecCrc("03010101"), trameAvecCrc("03010100")]), str(envoyesEsclave))
envoyesEsclave = []
verifie("temoin esclave 0x01 relai inexistant : rien", "false / 0", str(modbusFonctions.executeCmdModbus(lit(260))) + " / " + str(size(envoyesEsclave)))
modbusFonctions.envoiMsgModbus = vraiEnvoi
# La requete 0x01 du maitre est lisible par l'esclave (decrypteMSG : Count, longueur)
d = decode(modbusFonctions.prepareTrame({"DeviceAddress":3, "FunctionCode":1, "StartAddress":256, "type":"uint8", "Count":1, "Values":0}, "Commande"))
verifie("decode requete 0x01 : Erreur / StartAddress / Count", "0/256/1", str(d["Erreur"]) + "/" + str(d["StartAddress"]) + "/" + str(d["Count"]))
drivers = sauveDrivers

# (b) maitre : etat constate, commande intact, ecart journalise
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON"},
           "environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
               "TasmotaSlaveModBus2": {"activation": "ON", "id": 3, "name": "rideau"}}}}}
modules = {"garage": {"activation": "ON", "environnement": {"relais": {
    "relai2": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus2", "type": 256, "idModBus": 1, "id": 2, "etat": "ON"},
    "relai3": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus2", "type": 224, "idModBus": 2, "id": 3, "etat": "OFF"}}}}}
var relai = def (c) return modules["garage"]["environnement"]["relais"][c] end
var lecture = def (sa, bit)
  modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 3, "FunctionCode": 1, "StartAddress": sa, "Count": 1, "type": "uint8"}}
  recoit(3, "ModbusReceived", {"DeviceAddress": 3, "FunctionCode": 1, "Values": [bit]})
end
tasmota.horloge = 1000
journal = []
lecture(256, 0)          # Relais_i commande ON : relai physique au repos -> constate ON
verifie("relai 256 bit 0 -> constate ON, etat ON, horodate", "ON/ON/1000",
        str(relai("relai2").find("etatConstate")) + "/" + relai("relai2")["etat"] + "/" + str(relai("relai2").find("constateA")))
verifie("temoin : pas d'ecart journalise", false, journalise("ECART"))
lecture(225, 1)          # Relais (224) commande OFF, constate ON -> ecart
verifie("relai 224 bit 1 -> constate ON, etat reste OFF", "ON/OFF",
        str(relai("relai3").find("etatConstate")) + "/" + relai("relai3")["etat"])
verifie("ecart commande OFF / constate ON journalise", true, journalise("commande=OFF, constate=ON"))
# (c) l'echo d'une commande 0x06 ne reecrit plus l'etat commande
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 3, "FunctionCode": 6, "StartAddress": 256, "Count": 1, "type": "uint8"}}
recoit(3, "ModbusReceived", {"DeviceAddress": 3, "FunctionCode": 6, "Values": [1, 0]})
verifie("echo 0x06 : etat commande ON conserve", "ON", relai("relai2")["etat"])
verifie("echo 0x06 : requete acquittee", nil, modbusFonctions.etat()["enVol"])
modbusFonctions.etat()["enVol"] = nil
modules = sauveModules
drivers = sauveDrivers

print("")
print("=== 14. Chien de garde : esclave muet -> etats constates 'inconnu' ===")
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON"},
           "environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
               "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"},
               "TasmotaSlaveModBus2": {"activation": "ON", "id": 3, "name": "rideau"}}}}}
modules = appareils()
modules["garage"]["environnement"]["relais"] = {"relai2": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus2", "type": 256, "idModBus": 1, "id": 2, "etat": "ON", "etatConstate": "ON"}}
maitre = MaitreStub()
var env = def (f, c) return modules["garage"]["environnement"][f][c] end
tasmota.horloge = 0
verifie("1er passage : decompte amorce, personne de muet", 0, maitre.verifieChienDeGarde())
tasmota.horloge = 60
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "Count": 1, "type": "float"}}
recoit(2, "ModbusReceived", {"DeviceAddress": 2, "FunctionCode": 4, "Values": [21.5]})     # la cuve repond a t=60
tasmota.horloge = 90
verifie("temoin t=90 (= 3 periodes) : personne de muet", 0, maitre.verifieChienDeGarde())
journal = []
tasmota.horloge = 91
verifie("t=91 : rideau muet -> ses 2 appareils 'inconnu'", 2, maitre.verifieChienDeGarde())
verifie("relai rideau : constate inconnu, commande ON intact", "inconnu/ON", env("relais", "relai2")["etatConstate"] + "/" + env("relais", "relai2")["etat"])
verifie("interrupteur rideau : constate inconnu", "inconnu", env("interrupteurs", "interrupteur1").find("etatConstate"))
verifie("temoin thermometre cuve (a repondu) : valide", "valide", env("thermometres", "thermometre1").find("etatConstate"))
verifie("erreur journalisee pour le rideau", true, journalise("TasmotaSlaveModBus2 (ID=3) muet"))
tasmota.horloge = 300
verifie("temoin : un esclave deja muet n'est pas re-signale", 0, maitre.verifieChienDeGarde() - 1)   # la cuve, elle, devient muette
# Retour du rideau : reponse appariee -> plus muet, l'appareil retrouve son constat
journal = []
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 3, "FunctionCode": 2, "StartAddress": 160, "Count": 1, "type": "uint8"}}
recoit(3, "ModbusReceived", {"DeviceAddress": 3, "FunctionCode": 2, "Values": [1]})
verifie("retour du rideau : plus muet, retour journalise", "false/true", str(maitre.esclavesMuets.find(3, false)) + "/" + str(journalise("ID=3 repond de nouveau")))
verifie("retour : interrupteur valide et ON", "valide/ON", env("interrupteurs", "interrupteur1")["etatConstate"] + "/" + env("interrupteurs", "interrupteur1")["etat"])
# Temoin : une trame hors-sequence (rejetee) n'est pas un contact
maitre = MaitreStub()
maitre.derniersContacts[3] = 0
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "Count": 1, "type": "float"}}
recoit(3, "ModbusReceived", {"DeviceAddress": 3, "FunctionCode": 2, "Values": [1]})
verifie("temoin trame hors-sequence : pas de contact note", 0, maitre.derniersContacts[3])
modbusFonctions.etat()["enVol"] = nil
modules = sauveModules
drivers = sauveDrivers

print("")
print("=== 15. Numero d'ordre seq du push (UDP) ===")
sauveDrivers = drivers
sauveServeur = serveur
drivers = {"ModBus": {"activation": "ON", "id": 3, "typeComm": {"Serial":"ON", "TCP":"OFF", "UDP":"ON"}, "environnement": {}}}
serveur = {"udp": {"activation": "ON"}, "tcp": {"activation": "OFF"}, "mqtt": {"topic": "garage"}}
udpStub.envois = []
modbusFonctions.etat()["seqPush"] = 0
modbusFonctions.pousseEtat(160, "uint16", [0xFF])
modbusFonctions.pousseEtat(160, "uint16", [0])
verifie("esclave : seq 1 puis 2", "1/2", string.split(udpStub.envois[0][2], " ")[1] + "/" + string.split(udpStub.envois[1][2], " ")[1])
udpStub.envois = []
drivers["ModBus"]["typeComm"]["UDP"] = "OFF"
modbusFonctions.pousseEtat(160, "uint16", [0xFF])
verifie("temoin : un push non emis ne consomme pas de seq", 2, modbusFonctions.etat()["seqPush"])
# Filtre cote maitre
modbusFonctions.etat()["derniersSeq"] = {}
var a = modbusFonctions.accepteSeq
verifie("1er push connu (seq 5) : accepte", true, a(3, 5))
verifie("seq 6 : accepte", true, a(3, 6))
verifie("doublon seq 6 : ecarte", false, a(3, 6))
verifie("retard seq 4 (apres 6) : ecarte", false, a(3, 4))
verifie("seq 1 apres 6 : redemarrage, accepte", true, a(3, 1))
verifie("puis seq 2 : accepte", true, a(3, 2))
verifie("temoin : doublon du seq 1 initial ecarte", false, a(2, 1) && a(2, 1))
modbusFonctions.etat()["derniersSeq"] = {3: 57}
verifie("redemarrage dont le seq 1 est perdu (seq 2 apres 57) : accepte", true, a(3, 2))
verifie("temoin : autre esclave independant", true, a(4, 1))
verifie("seq absent (ancien esclave) : accepte", true, a(3, nil))
# lireMsgModbus : un push ecarte n'est pas publie
drivers["ModBus"]["id"] = 0
modbusFonctions.etat()["derniersSeq"] = {}
var trame160 = bytes(trameAvecCrc("031000A000010200FF"))
tasmota.publie = nil
modbusFonctions.lireMsgModbus("ModbusReceivedUDP", {"Trame": trame160.copy(), "Info": {}, "Automatique": true, "Seq": 8})
verifie("lireMsgModbus push seq 8 : publie", true, tasmota.publie != nil)
tasmota.publie = nil
modbusFonctions.lireMsgModbus("ModbusReceivedUDP", {"Trame": trame160.copy(), "Info": {}, "Automatique": true, "Seq": 7})
verifie("lireMsgModbus push seq 7 en retard : non publie", nil, tasmota.publie)
tasmota.publie = nil
modbusFonctions.lireMsgModbus("ModbusReceivedUDP", {"Trame": trame160.copy(), "Info": {}, "Seq": 7})
verifie("temoin : trame non push (sans Automatique) jamais filtree", true, tasmota.publie != nil)
drivers = sauveDrivers
serveur = sauveServeur

print("")
print("=== 16. G1 : timer P4 = echeance reelle en millis(), pas un cron ===")
var sauveDiverses = diverses
diverses = {"typeESP": "ESP32P4"}
var appels = []
tasmota.ms = 1000
modbusFonctions.armeTimer(5000, def () appels.push(tasmota.ms) end, "test_g1")
tasmota.ms = 5999
essaie(def () modbusFonctions.verifieEcheances() end)
verifie("temoin t+4999 ms : pas encore declenche", 0, size(appels))
tasmota.ms = 6000
essaie(def () modbusFonctions.verifieEcheances() end)
verifie("t+5000 ms : declenche exactement une fois", "[6000]", str(appels))
essaie(def () modbusFonctions.verifieEcheances() end)
verifie("temoin : one-shot, pas de second declenchement", 1, size(appels))
# Desarmement
modbusFonctions.armeTimer(100, def () appels.push(-1) end, "test_g1b")
modbusFonctions.desarmeTimer("test_g1b")
tasmota.ms = 99999
essaie(def () modbusFonctions.verifieEcheances() end)
verifie("desarme avant echeance : jamais declenche", 1, size(appels))
# Rearmement depuis la fonction appelee (surTimeout -> pompeQueue -> armeTimer)
appels = []
tasmota.ms = 0
modbusFonctions.armeTimer(10, def () appels.push("a") modbusFonctions.armeTimer(10, def () appels.push("b") end, "test_g1") end, "test_g1")
tasmota.ms = 10
essaie(def () modbusFonctions.verifieEcheances() end)
tasmota.ms = 20
essaie(def () modbusFonctions.verifieEcheances() end)
verifie("rearmement du meme nom depuis le rappel", "['a', 'b']", str(appels))
diverses = sauveDiverses

print("")
print("=== 17. G5 : une reponse est acquittee meme si son traitement plante ===")
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON"},
           "environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
               "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"}}}}}
modules = {"garage": {"activation": "ON", "environnement": {"thermometres": {
    # appareil incomplet (pas d'idModBus) place AVANT le bon dans la meme famille
    "thermometre0": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus1", "type": 1312, "id": 9},
    # DS18B20 sans 'serialNumber'
    "thermometre1": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus1", "type": 1312, "idModBus": 1, "id": 1, "value": 0.0}}}}}
maitre = MaitreStub()
journal = []
modbusFonctions.etat()["queue"] = []
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "Count": 1, "type": "float"}}
essaie(def () recoit(2, "ModbusReceived", {"DeviceAddress": 2, "FunctionCode": 4, "Values": [21.5]}) end)
verifie("reponse acquittee malgre appareils incomplets", nil, modbusFonctions.etat()["enVol"])
verifie("valeur tout de meme appliquee (serialNumber absent)", "21.5", str(modules["garage"]["environnement"]["thermometres"]["thermometre1"]["value"]))
# Exception forcee au coeur du traitement (Values vide) : journalisee, et acquittee quand meme
journal = []
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 1312, "Count": 1, "type": "float"}}
essaie(def () recoit(2, "ModbusReceived", {"DeviceAddress": 2, "FunctionCode": 4, "Values": []}) end)
verifie("exception en traitement : acquittee et journalisee", "nil/true", str(modbusFonctions.etat()["enVol"]) + "/" + str(journalise("MODBUS_TASMOTA_SLAVE_ERREUR")))
modbusFonctions.etat()["enVol"] = nil
modules = sauveModules
drivers = sauveDrivers

print("")
print("=== 18. G3 : file du maitre dedoublonnee et plafonnee ===")
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON"}, "environnement": {}}}
# Un message en vol bloque la pompe : on observe la file seule
modbusFonctions.etat()["enVol"] = {"paramMSG": {"DeviceAddress": 1, "FunctionCode": 6, "StartAddress": 1, "Count": 1}}
modbusFonctions.etat()["queue"] = []
var q = def () return modbusFonctions.etat()["queue"] end
var lec = def (sa) return {"DeviceAddress": 3, "FunctionCode": 2, "StartAddress": sa, "Count": 1, "type": "uint8"} end
var ecr = def (v) return {"DeviceAddress": 3, "FunctionCode": 6, "StartAddress": 256, "Count": 1, "Values": [v, 0]} end
modbusFonctions.enfileMsg(lec(160), "Commande")
verifie("lecture identique deja en file : ignoree", false, modbusFonctions.enfileMsg(lec(160), "Commande"))
modbusFonctions.enfileMsg(lec(161), "Commande")
verifie("temoin : lecture d'un autre registre enfilee", 2, size(q()))
modbusFonctions.enfileMsg(ecr(1), "Commande")
modbusFonctions.enfileMsg(ecr(2), "Commande")
verifie("temoin : deux ecritures identiques gardees (ordre des commandes)", 4, size(q()))
modbusFonctions.etat()["enVol"] = {"paramMSG": lec(170)}
verifie("lecture identique a celle en vol : ignoree", false, modbusFonctions.enfileMsg(lec(170), "Commande"))
# Plafond
modbusFonctions.etat()["queue"] = []
for i: 0 .. modbusFonctions.MAX_FILE - 1    modbusFonctions.enfileMsg(lec(1000 + i), "Commande")    end
verifie("file pleine : lecture ecartee", "false/32", str(modbusFonctions.enfileMsg(lec(5000), "Commande")) + "/" + str(size(q())))
verifie("file pleine : une ecriture passe en evincant la plus ancienne lecture",
        "true/32/1001/6", str(modbusFonctions.enfileMsg(ecr(1), "Commande")) + "/" + str(size(q())) + "/" +
        str(q()[0]["paramMSG"]["StartAddress"]) + "/" + str(q()[-1]["paramMSG"]["FunctionCode"]))
modbusFonctions.etat()["queue"] = []
modbusFonctions.etat()["enVol"] = nil
drivers = sauveDrivers

# Releve : un esclave muet n'est sonde qu'une fois par cycle
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON"},
           "environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
               "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"},
               "TasmotaSlaveModBus2": {"activation": "ON", "id": 3, "name": "rideau"}}}}}
modules = appareils()
modules["garage"]["environnement"]["interrupteurs"]["interrupteur2"] = {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus2", "type": 160, "idModBus": 2, "id": 2, "etat": "OFF"}
modules["garage"]["environnement"]["relais"] = {"relai2": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus2", "type": 256, "idModBus": 1, "id": 2}}
envoyes = []
vraiEnvoi = modbusFonctions.envoiMsgModbus
modbusFonctions.envoiMsgModbus = def (t, typeMsg, id) envoyes.push(t["DeviceAddress"]) end
m = MaitreStub()
m.releveEsclaves()
verifie("temoin rideau sain : 3 demandes pour lui", 3, size(envoyes) - 1)
envoyes = []
m.esclavesMuets[3] = true
m.releveEsclaves()
verifie("rideau muet : une seule sonde, cuve inchangee", "1/1", str(envoyes.find(3) != nil ? size(envoyes) - 1 : -1) + "/" + str(size(envoyes) - 1))
modbusFonctions.envoiMsgModbus = vraiEnvoi
modules = sauveModules
drivers = sauveDrivers

print("")
print("=== 19. G7 : les appareils jamais relus ne passent pas a 'inconnu' ===")
sauveDrivers = drivers
drivers = {"ModBus": {"activation": "ON", "id": 0, "typeComm": {"Serial":"ON"},
           "environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
               "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"}}}}}
modules = appareils()
modules["garage"]["environnement"]["relais"] = {"relai1": {"activation": "ON", "virtuel": "ModBus_TasmotaSlaveModBus1", "type": 1376, "idModBus": 1, "id": 1}}
maitre = MaitreStub()
tasmota.horloge = 0
maitre.verifieChienDeGarde()
tasmota.horloge = 1000
verifie("cuve muette : seul le thermometre (relu) est marque", 1, maitre.verifieChienDeGarde())
verifie("WS2812 (jamais relue) : pas 'inconnu'", nil, modules["garage"]["environnement"]["relais"]["relai1"].find("etatConstate"))
verifie("temoin thermometre cuve : 'inconnu'", "inconnu", modules["garage"]["environnement"]["thermometres"]["thermometre1"].find("etatConstate"))
modules = sauveModules
drivers = sauveDrivers

print("")
print("=== 20. G2 : decoupage des trames RS485 cote esclave ===")
var req3 = trameAvecCrc("030200A00001")                   # maitre -> rideau : 0x02, registre 160
var req2 = trameAvecCrc("020405200002")                   # maitre -> cuve : 0x04, registre 1312
var rep16 = "010320"
for i: 1 .. 32    rep16 += "00"    end
rep16 = trameAvecCrc(rep16)                               # carte 16 relais -> maitre : 0x03, 16 registres
var decoupe = def (hex, silence)
  var r = modbusFonctions.extraitTrames(bytes(hex), silence)
  var l = []
  for t: r[0]    l.push(t.tohex())    end
  return str(l) + " reste=" + r[1].tohex()
end
verifie("deux requetes collees -> 2 trames", str([req2, req3]) + " reste=", essaie(def () return decoupe(req2 + req3, false) end))
verifie("reponse carte 16 + requete rideau -> 2 trames", str([rep16, req3]) + " reste=", essaie(def () return decoupe(rep16 + req3, false) end))
verifie("octets parasites avant la trame : ignores", str([req3]) + " reste=", essaie(def () return decoupe("00FF" + req3, false) end))
verifie("trame coupee : moitie gardee en attente", "[] reste=" + req3[0 .. 7], essaie(def () return decoupe(req3[0 .. 7], false) end))
verifie("trame coupee puis completee -> 1 trame", str([req3]) + " reste=", essaie(def () return decoupe(req3[0 .. 7] + req3[8 ..], false) end))
verifie("trame incomplete + silence : abandonnee", "[] reste=", essaie(def () return decoupe(req3[0 .. 7], true) end))
verifie("temoin : CRC faux -> aucune trame", "[] reste=", essaie(def () return decoupe(req3[0 .. 11] + "0000", true) end))

# Bout en bout : l'esclave rideau (id 3) recoit [reponse carte 16][requete pour lui] en une lecture
class SerieStub
  var donnees
  def init(h) self.donnees = bytes(h) end
  def available() return size(self.donnees) end
  def read() var d = self.donnees self.donnees = bytes() return d end
  def flush() end
  def write(b) end
end
sauveDrivers = drivers
sauveServeur = serveur
drivers = {"ModBus": {"activation": "ON", "id": 3, "typeComm": {"Serial":"ON"}, "environnement": {}}}
serveur = {"mqtt": {"topic": "rideau"}, "udp": {"activation": "OFF"}, "tcp": {"activation": "OFF"}}
modbusFonctions.etat()["tamponSerie"] = bytes()
modbusFonctions.etat()["serialModBus"] = SerieStub(rep16 + req3)
tasmota.publies = []
essaie(def () modbusFonctions.lireMsgModbus("ModbusReceived", nil) end)
var pubs = tasmota.publies
verifie("esclave : la requete qui lui est destinee est publiee", "1/3/160",
        str(size(pubs)) + "/" + (size(pubs) > 0 ? str(json.load(pubs[0])["ModbusReceived"]["DeviceAddress"]) + "/" + str(json.load(pubs[0])["ModbusReceived"]["StartAddress"]) : "-"))
# Trame arrivee en deux lectures successives
modbusFonctions.etat()["tamponSerie"] = bytes()
modbusFonctions.etat()["serialModBus"] = SerieStub(req3[0 .. 5])
tasmota.publies = []
essaie(def () modbusFonctions.lireMsgModbus("ModbusReceived", nil) end)
modbusFonctions.etat()["serialModBus"].donnees = bytes(req3[6 ..])
essaie(def () modbusFonctions.lireMsgModbus("ModbusReceived", nil) end)
verifie("esclave : trame reconstituee sur deux lectures", 1, size(tasmota.publies))
tasmota.publies = nil
modbusFonctions.etat()["serialModBus"] = nil
modbusFonctions.etat()["tamponSerie"] = bytes()
drivers = sauveDrivers
serveur = sauveServeur

print("")
print("=== 21. Test de debit carte 16 : sequence, file suspendue puis relancee ===")
sauveDrivers = drivers
drivers = {"ModBus": {"typeComm": {"Serial":"ON"}, "environnement": {}, "id": 0, "activationReponseCMD": "ON",
                      "debit": 19200, "timeoutReponse": 5000}}
diverses = {"typeESP": "ESP32P4"}
tasmota.ms = 0
tasmota.cmds = []
tasmota.regles = []
tasmota.retourCmd = {}
var etM = modbusFonctions.etat()
etM["echeances"] = {}
etM["queue"] = []
etM["enVol"] = {"paramMSG": {"DeviceAddress": 2, "FunctionCode": 4, "StartAddress": 4704, "Count": 1, "type": "uint32", "Values": 0},
                "typeMsg": "Commande", "tentatives": 0}
var lance = essaie(def () return modbusFonctions.testeDebitConn16(1, 9600) end)
verifie("lance : message en vol remis en tete, pause", "true/1/nil", str(etM["pause"]) + "/" + str(size(etM["queue"])) + "/" + str(etM["enVol"]))
verifie("regle ModbusReceived temporaire posee", "+ModbusReceived/testeDebitConn16", size(tasmota.regles) > 0 ? tasmota.regles[0] : "-")
verifie("second lancement refuse pendant le test", "test de debit deja en cours", essaie(def () return modbusFonctions.testeDebitConn16(1, 9600) end))
essaie(def () modbusFonctions.pompeQueue() end)
verifie("pause : la file n'emet rien", 0, size(tasmota.cmds))
var avance = def (jusqua)
  while tasmota.ms < jusqua    tasmota.ms += 100    modbusFonctions.verifieEcheances()    end
end
essaie(def () avance(5400) end)
verifie("rien avant que le pont ait rendu la main (5,5 s)", 0, size(tasmota.cmds))
essaie(def () avance(20000) end)
var attendues = ["ModbusBaudrate 9600",
                 "ModBusSend {\"deviceaddress\":1,\"functioncode\":3,\"startaddress\":254,\"type\":\"uint16\",\"count\":1}",
                 "ModBusSend {\"deviceaddress\":255,\"functioncode\":3,\"startaddress\":255,\"type\":\"uint16\",\"count\":1}",
                 "ModbusBaudrate 19200"]
verifie("sequence : debit, 0xFE, diffusion 0xFF, retour", str(attendues), str(tasmota.cmds[0 .. 3]))
verifie("fin : file relancee sur le message remis en tete", true,
        size(tasmota.cmds) == 5 && string.find(tasmota.cmds[4], "ModBusSend") == 0 && string.find(tasmota.cmds[4], "4704") > 0)
verifie("fin : pause levee, regle retiree", "false/-ModbusReceived/testeDebitConn16",
        str(etM["pause"]) + "/" + tasmota.regles[size(tasmota.regles) - 1])
journal = []
essaie(def () modbusFonctions.logReponseTestDebit({"ModbusReceived": {"DeviceAddress": 1, "StartAddress": 254, "Count": 1, "Values": [4]}}) end)
verifie("reponse 0xFE decodee : 4 -> 19200 bauds", true, journalise("registre debit = 4 -> 19200 bauds"))
essaie(def () modbusFonctions.logReponseTestDebit({"ModbusReceived": {"DeviceAddress": 1, "StartAddress": 255, "Count": 1, "Values": [1]}}) end)
verifie("reponse 0xFF decodee : adresse 1", true, journalise("lue par diffusion) = 1"))
verifie("refuse sur un esclave", "test reserve au maitre ModBus serie",
        essaie(def () drivers["ModBus"]["id"] = 2 return modbusFonctions.testeDebitConn16(1, 9600) end))
print("")
print("=== 22. ReglageBaudrateConn16channels : ordre enfile, debits refuses ===")
drivers["ModBus"]["id"] = 0
etM["enVol"] = nil
etM["queue"] = []
etM["pause"] = false
tasmota.cmds = []
journal = []
essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "ReglageBaudrateConn16channels 0x01 19200", nil) end)
var envoye = size(tasmota.cmds) > 0 ? tasmota.cmds[0] : "-"
verifie("19200 : un ModBusSend 0x06 registre 254 code 4", true,
        string.find(envoye, "ModBusSend ") == 0 && json.load(envoye[11 ..])["FunctionCode"] == 6 &&
        json.load(envoye[11 ..])["StartAddress"] == 254 && str(json.load(envoye[11 ..])["Values"]) == "[4]" &&
        json.load(envoye[11 ..])["DeviceAddress"] == 1)
verifie("19200 : passe par la file (en vol)", true, etM["enVol"] != nil)
verifie("19200 : journalise en clair", true, journalise("registre 0x00FE <- 4 (19200 bauds)"))
var trame19200 = essaie(def () return modbusFonctions.prepareTrame(etM["enVol"]["paramMSG"], "Commande").tohex() end)
verifie("trame bus 19200 = 010600FE0004E9F9", "010600FE0004E9F9", trame19200)
verifie("debit inconnu 38400 : refuse (plus de retour usine)", true,
        string.find(essaie(def () return modbusFonctions.reglageDebitConn16(["1 38400"]) end), "debit refuse") == 0)
verifie("'usine' : code 5 explicite", "debit de l'esclave 1 -> retour usine (9600) (code 5) envoye",
        essaie(def () return modbusFonctions.reglageDebitConn16(["1 usine"]) end))
verifie("parametre manquant : usage", true,
        string.find(essaie(def () return modbusFonctions.reglageDebitConn16(["1"]) end), "usage") == 0)
verifie("adresse 0 refusee", true,
        string.find(essaie(def () return modbusFonctions.reglageDebitConn16(["0 9600"]) end), "adresse") == 0)
etM["enVol"] = nil
etM["queue"] = []
etM["echeances"] = {}
tasmota.regles = nil
tasmota.retourCmd = nil
diverses = {}
drivers = sauveDrivers

print("")
print("=== 23. VerifieConn16channels : ID et debit de la carte vs persist, correction ===")
# Carte simulee : repond seulement au BON debit, a son ID ou a la diffusion 255 ; 0x00FE = code de
# debit enregistre, 0x00FF = ID. Hypothese du simulateur : un ID ecrit est effectif tout de suite,
# un debit ecrit seulement apres coupure (doc constructeur) -> 'debit' reste celui en service.
var carteSim = {}
def simuleCarte()
  import string
  import json
  while carteSim["vu"] < size(tasmota.cmds)
    var c = tasmota.cmds[carteSim["vu"]]
    carteSim["vu"] += 1
    if string.find(c, "ModbusBaudrate ") == 0    carteSim["bus"] = int(c[15 ..])    continue    end
    if string.find(c, "ModBusSend ") != 0 || carteSim["bus"] != carteSim["debit"]    continue    end
    var t = json.load(c[11 ..])
    var adr = t["deviceaddress"]
    if (adr != carteSim["id"] && adr != 255) || t.find("startaddress", 0) < 0xFE    continue    end
    var fc = t["functioncode"]
    var reg = t["startaddress"]
    var val = nil
    if fc == 3
      val = (reg == 0xFF) ? carteSim["id"] : carteSim["code"]
    elif fc == 6
      val = t["values"][0]
      carteSim["ecrits"].push(str(adr) + ":" + str(reg) + "=" + str(val))
      if reg == 0xFF    carteSim["id"] = val    else    carteSim["code"] = val    end
    end
    tasmota.rappels["verifieConn16"](nil, nil, {"ModbusReceived": {"DeviceAddress": adr, "FunctionCode": fc, "StartAddress": reg, "Count": 1, "Values": [val]}})
  end
end
# Prepare un scenario : persist (id, debit) et carte (id, debit en service, code enregistre)
def scenario(idPersist, idCarte, debitCarte, codeCarte)
  drivers = {"ModBus": {"typeComm": {"Serial":"ON"}, "id": 0, "activationReponseCMD": "ON", "debit": 19200, "timeoutReponse": 5000,
                        "environnement": {"pinsModBus": {"RX": {"activation": "ON", "id": 1}},
                                          "Conn16channels": {"log": "detail", "Conn16channel1": {"activation": "ON", "id": idPersist}},
                                          "TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {"activation": "ON", "id": 2}}}}}
  carteSim = {"id": idCarte, "debit": debitCarte, "code": codeCarte, "bus": 19200, "vu": 0, "ecrits": []}
  var e = modbusFonctions.etat()
  e["echeances"] = {}  e["queue"] = []  e["enVol"] = nil  e["pause"] = false
  tasmota.ms = 0  tasmota.cmds = []  tasmota.regles = []  tasmota.rappels = {}  tasmota.retourCmd = {}
  journal = []
end
def deroule(jusqua)
  while tasmota.ms < jusqua    tasmota.ms += 100    modbusFonctions.verifieEcheances()    simuleCarte()    end
end
diverses = {"typeESP": "ESP32P4"}
var etV = modbusFonctions.etat()

# a) conforme : une seule lecture, au debit du bus, a l'ID du persist
scenario(1, 1, 19200, 4)
verifie("conforme : lancement", true, string.find(essaie(def () return modbusFonctions.verifieConn16(false, nil) end), "lancee") > 0)
verifie("conforme : file suspendue", true, etV["pause"])
essaie(def () deroule(2000) end)
verifie("conforme : verdict en moins de 2 s", true, journalise("VERIFIE_CONN16: conforme au persist"))
verifie("conforme : pause levee, regle retiree", "false/-ModbusReceived/verifieConn16", str(etV["pause"]) + "/" + tasmota.regles[-1])
verifie("conforme : aucune diffusion ni ecriture", 0, size(carteSim["ecrits"]) + (string.find(str(tasmota.cmds), "\"deviceaddress\":255") >= 0 ? 1 : 0))

# b) non conforme, sans 'corrige' : trouve ID 5 a 9600 par balayage, n'ecrit rien
scenario(1, 5, 9600, 3)
essaie(def () modbusFonctions.verifieConn16(false, nil) end)
essaie(def () deroule(60000) end)
verifie("sans corrige : ecart constate", true, journalise("NON conforme, carte Conn16channel1 : ID 5 (persist 1), debit 9600 bauds (persist 19200)"))
verifie("sans corrige : rien ecrit", 0, size(carteSim["ecrits"]))
verifie("sans corrige : bus revenu a 19200", "ModbusBaudrate 19200", tasmota.cmds[-1])

# c) avec 'corrige' : ecrit le debit PUIS l'ID, a l'ID actuel ; relit a l'ID attendu
scenario(1, 5, 9600, 3)
essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "VerifieConn16channels corrige", nil) end)
essaie(def () deroule(60000) end)
verifie("corrige : debit puis ID, a l'ID actuel 5", "['5:254=4', '5:255=1']", str(carteSim["ecrits"]))
verifie("corrige : ID relu a la nouvelle adresse", true, journalise("ID 1 applique"))
verifie("corrige : coupure d'alimentation demandee", true, journalise("COUPER L'ALIMENTATION"))
verifie("corrige : pause levee", false, etV["pause"])

# d) debit deja enregistre, coupure pas faite : rien n'est reecrit
scenario(1, 1, 9600, 4)
essaie(def () modbusFonctions.verifieConn16(true, nil) end)
essaie(def () deroule(60000) end)
verifie("coupure en attente : aucune ecriture", 0, size(carteSim["ecrits"]))
verifie("coupure en attente : signalee", true, journalise("COUPER L'ALIMENTATION"))

# e) debit en service = persist, mais un autre debit enregistre (piege au prochain boot) : corrige
scenario(1, 1, 19200, 3)
essaie(def () modbusFonctions.verifieConn16(true, nil) end)
essaie(def () deroule(5000) end)
verifie("code enregistre faux : reecrit 4, sans coupure", "['1:254=4']/false", str(carteSim["ecrits"]) + "/" + str(journalise("COUPER")))

# f) carte muette a tous les debits : erreur, puis file relancee
scenario(1, 1, 38400, 4)
essaie(def () modbusFonctions.verifieConn16(true, nil) end)
essaie(def () deroule(60000) end)
verifie("muette : signalee apres le balayage", true, journalise("muette a tous les debits"))
verifie("muette : 1 lecture directe + 5 diffusions", 6, size(string.split(str(tasmota.cmds), "ModBusSend")) - 1)
verifie("muette : pause levee", false, etV["pause"])

# g) refus : ID du persist deja porte par un esclave du bus ; second lancement pendant un test
scenario(2, 2, 19200, 4)
verifie("ID 2 du persist = esclave cuve : refuse", "ID 2 deja porte par TasmotaSlaveModBus.TasmotaSlaveModBus1 : corriger le persist",
        essaie(def () return modbusFonctions.verifieConn16(true, nil) end))
scenario(1, 1, 19200, 4)
etV["pause"] = true
verifie("refuse pendant un test en cours", "test ou verification deja en cours", essaie(def () return modbusFonctions.verifieConn16(true, nil) end))

# h) deux cartes actives : pas de diffusion
scenario(1, 7, 19200, 4)
drivers["ModBus"]["environnement"]["Conn16channels"]["Conn16channel2"] = {"activation": "ON", "id": 9}
essaie(def () modbusFonctions.verifieConn16(true, "Conn16channel1") end)
essaie(def () deroule(20000) end)
verifie("deux cartes : pas de diffusion", true, string.find(str(tasmota.cmds), "\"deviceaddress\":255") < 0 && journalise("diffusion impossible"))

etV["echeances"] = {}  etV["queue"] = []  etV["enVol"] = nil  etV["pause"] = false
tasmota.regles = nil
tasmota.rappels = nil
tasmota.retourCmd = nil
diverses = {}
drivers = sauveDrivers

print("")
print("=== 24. Demarrage du maitre : verifieConn16 differee (persist reel du P4) ===")
# Constate sur le P4 le 2026-10-06 : 'type_error string + map' au boot. Le minuteur etait cree
# dans une boucle quittee par 'break', qui ne referme pas les variables capturees : il lisait
# une variable declaree apres la boucle au lieu du nom de la carte. Rejoue le vrai chemin :
# System#Boot (changementEtatDemarrage) puis l'echeance 'verifieConn16_boot'.
import json
var fP4 = open("data/garage/tasmota32p4-serveur-modbus/_persist.json", "r")
var pP4 = json.load(fP4.read())
fP4.close()
sauveDrivers = drivers
sauveServeur = serveur
drivers = pP4["drivers"]
serveur = pP4["serveur"]
diverses = {"typeESP": "ESP32P4"}                     # armeTimer -> echeances (chemin P4)
etV["echeances"] = {}  etV["queue"] = []  etV["enVol"] = nil  etV["pause"] = false
essaie(def () modbusFonctions.changementEtatDemarrage({"Boot": 1}, "System", {"System": {"Boot": 1}}) end)
var eBoot = etV["echeances"].find("verifieConn16_boot")
verifie("boot : echeance verifieConn16_boot armee", true, eBoot != nil)
verifie("boot : echeance executee sans exception", "OK",
        eBoot == nil ? "absente" : essaie(def () eBoot["f"]() return "OK" end))
verifie("boot : verification lancee (file suspendue)", true, etV["pause"])
etV["echeances"] = {}  etV["queue"] = []  etV["enVol"] = nil  etV["pause"] = false
tasmota.regles = nil
tasmota.rappels = nil
diverses = {}
drivers = sauveDrivers
serveur = sauveServeur

print("")
print("=== 25. relaiePushMQTT : copie MQTT des push esclaves, cote maitre (2026-10-10) ===")
# Les esclaves sont derriere le NAPT du maitre : leur multicast n'atteint pas le reseau maison.
# Le maitre republie le datagramme BRUT sur tele/<topic>/MODBUSPUSH, si relaisPushMQTT = ON.
# Le branchement dans udpFonctions.lireUDP est teste par test_discovery.be section 13.
import mqtt
sauveDrivers = drivers
sauveServeur = serveur
drivers = {"ModBus": {"id": 0, "relaisPushMQTT": "ON", "typeComm": {"Serial": "ON"}}}
serveur = {"mqtt": {"topic": "garage"}}
var PUSH = "ModbusPushUDP 12 031000A000010200FFE7D0"
mqtt.publies = []
verifie("ON : topic publie", "tele/garage/MODBUSPUSH", essaie(def () return modbusFonctions.relaiePushMQTT(PUSH, "192.168.4.2") end))
verifie("ON : contenu {ip, msg} non retenu", "[['tele/garage/MODBUSPUSH', '{\"ip\":\"192.168.4.2\",\"msg\":\"" + PUSH + "\"}', nil]]",
        str(mqtt.publies))
mqtt.publies = []
drivers["ModBus"]["relaisPushMQTT"] = "OFF"
verifie("temoin OFF : rien publie", "nil/0", str(modbusFonctions.relaiePushMQTT(PUSH, "192.168.4.2")) + "/" + str(size(mqtt.publies)))
drivers["ModBus"].remove("relaisPushMQTT")
verifie("temoin cle absente (defaut OFF) : rien publie", "nil/0", str(modbusFonctions.relaiePushMQTT(PUSH, "192.168.4.2")) + "/" + str(size(mqtt.publies)))
drivers["ModBus"]["relaisPushMQTT"] = "ON"
drivers["ModBus"]["id"] = 2
verifie("temoin esclave (id 2) : rien publie", "nil/0", str(modbusFonctions.relaiePushMQTT(PUSH, "192.168.4.2")) + "/" + str(size(mqtt.publies)))
drivers["ModBus"]["id"] = 0
mqtt.connecte = false
verifie("temoin broker coupe : rien publie", "nil/0", str(modbusFonctions.relaiePushMQTT(PUSH, "192.168.4.2")) + "/" + str(size(mqtt.publies)))
mqtt.connecte = true
serveur = {}
verifie("temoin sans topic : rien publie, sans exception", "nil/0", str(essaie(def () return modbusFonctions.relaiePushMQTT(PUSH, "x") end)) + "/" + str(size(mqtt.publies)))
serveur = {"mqtt": {"topic": "garage"}}
var publishOrigine = mqtt.publish
mqtt.publish = def (t, p, r) raise "io_error", "broker indisponible" end
journal = []
verifie("publication qui leve : nil, erreur journalisee", "nil/true", str(essaie(def () return modbusFonctions.relaiePushMQTT(PUSH, "192.168.4.2") end)) + "/" + str(journalise("RELAIE_PUSH_MQTT_ERREUR")))
mqtt.publish = publishOrigine

# ReglageModbus RelaisPushMQTT : ON/OFF/1/0 sauves, valeur invalide refusee, sans parametre = lecture
import persist
var nbSave = persist.nb_save
essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "RelaisPushMQTT 0", nil) end)
verifie("commande 0 -> OFF sauve", "OFF/1", drivers["ModBus"]["relaisPushMQTT"] + "/" + str(persist.nb_save - nbSave))
essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "RelaisPushMQTT on", nil) end)
verifie("commande on -> ON sauve", "ON/2", drivers["ModBus"]["relaisPushMQTT"] + "/" + str(persist.nb_save - nbSave))
essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "RelaisPushMQTT peutetre", nil) end)
verifie("temoin valeur invalide : inchange, rien sauve", "ON/2", drivers["ModBus"]["relaisPushMQTT"] + "/" + str(persist.nb_save - nbSave))
essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "RelaisPushMQTT", nil) end)
verifie("sans parametre : lecture seule", "ON/2", drivers["ModBus"]["relaisPushMQTT"] + "/" + str(persist.nb_save - nbSave))
drivers = sauveDrivers
serveur = sauveServeur

print("")
print(string.format("=== BILAN : %i tests, %i PASS, %i bug(s) connu(s), %i echec(s) inattendu(s) ===",
      total, total - echecs - bugs_connus, bugs_connus, echecs))
print(echecs == 0 ? "BANC_MODBUS: OK" : "BANC_MODBUS: ECHEC")
