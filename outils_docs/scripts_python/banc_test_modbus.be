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
  def cmd(c, m) self.cmds.push(c) return "" end
  def millis(d) return self.ms + (d == nil ? 0 : d) end
  def delay(ms) end
  def set_timer(a, b, c) end
  def remove_timer(nom) end
  def add_rule(a, b, c) end
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

# --- charge les vrais modules ---
print(">>> sources testees :", SOURCES)
var f = open(SOURCES + "/modbusFonctions.be", "r")
var src = f.read()
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
print("=== 6. reglageModbus ImAlive : un client TCP par esclave ===")
# Le maitre ouvre un client TCP par esclave trouve dans discovery.json.
class ClientStub
  var ip, port
  def connected() return false end
  def connect(ip, port) self.ip = ip  self.port = port  return true end
end
tcpclientasync = ClientStub
import gestionFileFolder
gestionFileFolder.contenu = '{"AABBCC": {"cuve": {"maitre": {"ModBus": {"id": 2, "TCP": {"IPAddress": "192.168.4.2"}}}}}}'
var sauveDrivers = drivers
var sauveServeur = serveur
drivers = {"ModBus": {"typeComm": {"TCP":"ON"}, "environnement": {}, "id": 0}}
serveur = {"tcp": {"activation":"ON"}, "udp": {"activation":"OFF"}, "adresseMAC": "AA:BB:CC"}
modbusFonctions.etat()["clients"] = [nil, nil, nil, nil, nil, nil]
var r = essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "ImAlive ON", nil)
                      var c = modbusFonctions.etat()["clients"]
                      return (c[2] != nil ? c[2].ip : "nil") + " / clients[0]=" + (c[0] == nil ? "nil" : "cree") end)
verifie("ImAlive esclave id 2 : IP du client[2] / client[0]", "192.168.4.2 / clients[0]=nil", r)
# Borne : un id hors du tableau (1 a 5) est journalise et ignore, sans exception.
gestionFileFolder.contenu = '{"AABBCC": {"x": {"maitre": {"ModBus": {"id": 9, "TCP": {"IPAddress": "192.168.4.9"}}}}}}'
modbusFonctions.etat()["clients"] = [nil, nil, nil, nil, nil, nil]
r = essaie(def () modbusFonctions.reglageModbus("ReglageModbus", 1, "ImAlive ON", nil)
                  var n = 0
                  for c : modbusFonctions.etat()["clients"]   if c != nil  n += 1  end   end
                  return "clients crees=" + str(n) end)
verifie("ImAlive esclave id 9 (hors 1-5) : ignore sans exception", "clients crees=0", r)
drivers = sauveDrivers
serveur = sauveServeur
modbusFonctions.etat()["clients"] = [nil, nil, nil, nil, nil, nil]

print("")
print("=== 7. reglageSlaveModBus logActivation : chemin du persist ===")
# log() du driver LIT drivers.ModBus.environnement.TasmotaSlaveModBus.debug
# (modBus_TasmotaSlaveModBus.be:86) : c'est la que la commande doit ECRIRE.
class SelfStub
  var DEBUG
  def log(m, l) end
end
import persist
sauveDrivers = drivers
drivers = {"ModBus": {"environnement": {"TasmotaSlaveModBus": {"debug": "OFF",
           "TasmotaSlaveModBus1": {"activation": "ON", "id": 2, "name": "cuve"}}}}}
var nbSave = persist.nb_save
essaie(def () modBus_TasmotaSlaveModBus.MODBUS_TASMOTA_SLAVE.reglageSlaveModBus(SelfStub(), "ReglageSlaveModBus", 1, "logActivation ON", nil) end)
verifie("logActivation ON : debug du persist / save()",
        "ON / save=1",
        drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"]["debug"] + " / save=" + str(persist.nb_save - nbSave))
drivers = sauveDrivers

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
print(string.format("=== BILAN : %i tests, %i PASS, %i bug(s) connu(s), %i echec(s) inattendu(s) ===",
      total, total - echecs - bugs_connus, bugs_connus, echecs))
print(echecs == 0 ? "BANC_MODBUS: OK" : "BANC_MODBUS: ECHEC")
