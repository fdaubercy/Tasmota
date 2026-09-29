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
def log(m, l) end                      # no-op : on ne teste pas les logs
class TasmotaStub
  def yield() end
  def rtc() return {"local": 0} end
  def cmd(c, m) return "" end
  def millis() return 0 end
  def delay(ms) end
  def set_timer(a, b, c) end
  def add_rule(a, b, c) end
  def add_cron(a, b, c) end
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
bug_connu("push interrupteur 0x82 : 1 bit a 1", trameAvecCrc("02820101"),
          essaie(def () return modbusFonctions.prepareTrame(push02, "Reponse").tohex() end),
          "point 1 : Values[nb + 1] hors bornes pour 1 valeur, modbusFonctions.be:1414")
# Reponse d'un esclave a une lecture 0x02 de 3 entrees : ON, OFF, ON -> 0b101 = 0x05.
var rep02 = {"DeviceAddress":2, "FunctionCode":0x02, "StartAddress":160,
             "type":"uint8", "Count":3, "Values":[0xFF, 0x00, 0xFF]}
bug_connu("reponse 0x02 : 3 bits ON/OFF/ON -> 0x05", trameAvecCrc("02020105"),
          essaie(def () return modbusFonctions.prepareTrame(rep02, "Reponse").tohex() end),
          "point 1 : pas d'empaquetage en bits, tampon de 2 octets par valeur")
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
# Le push est emis au format REPONSE, que decrypteMSG lit au format COMMANDE :
# longueur imposee de 8 octets et StartAddress lu dans les octets 2-3. Une reponse
# ne porte d'ailleurs pas le registre : le maitre ne peut pas savoir quel capteur
# a change. Defaut de FORMAT, a trancher (voir PROTOCOLE_MODBUS.md section 9).
d = decode(modbusFonctions.prepareTrame(push04, "Reponse"))
bug_connu("push 0x84 decode par le maitre : Erreur / StartAddress", "0/1312",
          str(d["Erreur"]) + "/" + str(d["StartAddress"]),
          "format du push : decision en attente (releve 0x04 ou ecriture 0x10)")

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
bug_connu("ImAlive esclave id 2 : IP du client[2] / client[0]", "192.168.4.2 / clients[0]=nil", r,
          "point 2 : clients[id] cree avant la lecture de id, modbusFonctions.be:332")
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
bug_connu("logActivation ON : debug du persist / save()",
          "ON / save=1",
          drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"]["debug"] + " / save=" + str(persist.nb_save - nbSave),
          "point 3 : chemin TasmotaSlaveModBus x3, modBus_TasmotaSlaveModBus.be:133")
drivers = sauveDrivers

print("")
print(string.format("=== BILAN : %i tests, %i PASS, %i bug(s) connu(s), %i echec(s) inattendu(s) ===",
      total, total - echecs - bugs_connus, bugs_connus, echecs))
print(echecs == 0 ? "BANC_MODBUS: OK" : "BANC_MODBUS: ECHEC")
