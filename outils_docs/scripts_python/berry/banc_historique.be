# Banc de test Berry du choix des series de l'historique (2026-10-18, A8 du plan graphiques-web) :
# data/fs/historiqueSeries.be (decouverte filtree du JSON SENSOR, exclues, ajouts, compteurs) et
# data/fs/historiqueFonctions.be (releve : premiere decouverte, redecouverte a chaque nouvelle heure,
# series du mois gardees, fichier du mois mis de cote sous un suffixe libre).
# -----------------------------------------------------------------------------------------------
# Lance par banc_graphiques.py ; ou directement, DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_historique.be <dossier_sortie> [dossier_sources]
# Les VRAIS modules sont importes depuis dossier_sources (data/fs par defaut) ; seul 'path' est bouchonne
# (bouchons_berry/historique/, adosse au disque). L'historique s'ecrit dans <dossier_sortie>/histo.
# La derniere ligne, BANC_HISTORIQUE: OK|ECHEC, est lue par l'enveloppe pour son code de sortie.
import global
import sys
import string
import json
import os

if (size(global._argv) < 2)
    print("Usage : berry.exe banc_historique.be <dossier_sortie> [dossier_sources]")
    print("BANC_HISTORIQUE: ECHEC (argument manquant)")
    return
end
var SORTIE = global._argv[1]
var SOURCES = size(global._argv) > 2 ? global._argv[2] : "data/fs"
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/historique")
sys.path().push(SOURCES)

# ---- Globaux du firmware bouchonnes -------------------------------------------------------------
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4
class Driver end
class TASMOTA_BOUCHON
    var utc, ms, capteurs, crons
    def init() self.utc = 0 self.ms = 0 self.capteurs = "{}" self.crons = [] end
    def yield() end
    def add_cron(motif, f, nom) self.crons.push(nom) end
    def add_driver() end
    def read_sensors() if (self.capteurs == "LEVE")    raise "io_error", "capteur bloque"    end return self.capteurs end
    def rtc() return {"utc": self.utc} end
    def millis() return self.ms end
    def wifi() return {"rssi": -61} end
    def get_free_heap() return 123456 end
    # Date civile UTC d'un epoch (algorithme « days from civil » inverse)
    def time_dump(t)
        var z = t / 86400 + 719468
        var era = z / 146097
        var doe = z - era * 146097
        var yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365
        var doy = doe - (365 * yoe + yoe / 4 - yoe / 100)
        var mp = (5 * doy + 2) / 153
        var m = (mp < 10 ? mp + 3 : mp - 9)
        return {"year": yoe + era * 400 + (m <= 2 ? 1 : 0), "month": m, "day": doy - (153 * mp + 2) / 5 + 1,
                "hour": (t % 86400) / 3600, "min": (t % 3600) / 60}
    end
end
tasmota = TASMOTA_BOUCHON()
var journal = []
class LOG_BOUCHON
    def log(msg, niveau, cible) journal.push([msg, niveau, cible]) end
    def actif(niveau, cible) return true end
end
logFonctions = LOG_BOUCHON()

var echecs = 0
def verifie(condition, nom)
    print((condition ? "  OK     " : "  ECHEC  ") + nom)
    if (!condition)    echecs += 1    end
end
def dernierLog(motif)
    var i = size(journal) - 1           # une plage Berry (a .. b) ne compte pas a rebours
    while (i >= 0)
        if (string.find(journal[i][0], motif) >= 0)    return journal[i]    end
        i -= 1
    end
    return nil
end

import path
import historiqueFonctions
import historiqueSeries
var DOSSIER = SORTIE + "/histo"
historiqueFonctions.DOSSIER = DOSSIER
path.mkdir(DOSSIER)
for f: os.listdir(DOSSIER)    os.remove(DOSSIER + "/" + f)    end     # banc relance sur le meme dossier

# JSON SENSOR type d'un maitre ModBus : capteurs reels, esclave ModBus, valeurs d'un module, entrees et relais
var SENSOR = {"Time": "2026-10-18T12:00:00", "TempUnit": "C",
    "ESP32": {"Temperature": 29.4},
    "DS18B20": {"Id": "C1041600F6FBFF28", "Temperature": 12.5},
    "COUNTER": {"C1": 2500},
    "Switch1": "ON", "Switch2": 1, "Button1": 0,
    "ENERGY": {"Power": 120, "Total": 3.4},
    "Relais": {"POWER1": 1},
    "sensorsCuve": {"valeursAnalogiques": {"valeurCapteurHauteur": 616},
                    "niveauCuve": {"tauxRemplissage": 0.17, "hauteurEau": 19, "volume": 1144}},
    "TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {"ANALOG": {"A1": 616}, "COUNTER": {"C1": 7},
                                                   "Switchs": {"Switch1": 1, "Switch2": "OFF"},
                                                   "Temperatures": {"DS18B20-1": {"Id": "x", "Temperature": 12.4}}}}}

# ---- 1. Admissibilite d'un chemin ---------------------------------------------------------------
print("1. Admissibilite d'un chemin (historiqueSeries.admissible)")
var C = {"compteurs": {"COUNTER.C1": {"type": "energie", "impulsionsParUnite": 1000, "unite": "kWh"},
                       "COUNTER.C2": {"type": "volume", "impulsionsParUnite": 1},
                       "COUNTER.C3": {"type": "debit", "impulsionsParUnite": 0}},
         "ajouts": ["ESP32.Temperature", "@rssi", "@power1"], "exclues": ["sensorsCuve.valeursAnalogiques"]}
var A = historiqueSeries.admissible
verifie(A("DS18B20.Temperature", {}) && A("ENERGY.Power", {}) && A("TasmotaSlaveModBus.TasmotaSlaveModBus1.ANALOG.A1", {}),
        "mesures : DS18B20.Temperature, ENERGY.Power (casse differente de POWER), ANALOG d'un esclave")
verifie(!A("Switch1", {}) && !A("x.Switch2", {}) && !A("TasmotaSlaveModBus.TasmotaSlaveModBus1.Switchs.Switch1", {})
        && !A("x.Button1", {}) && !A("Relais.POWER1", {}) && !A("relais.r1", {}), "entrees et relais refuses (Switch*, Button*, POWER*, relais)")
verifie(!A("ESP32.Temperature", {}) && !A("@rssi", {}) && !A("@heap", {}), "mesures internes refusees par defaut")
verifie(A("ESP32.Temperature", C) && A("@rssi", C), "mesures internes acceptees par 'ajouts'")
verifie(!A("@power1", C), "@power<n> refuse meme dans 'ajouts' (relais)")
verifie(!A("COUNTER.C1", {}) && A("COUNTER.C1", C), "compteur : refuse sans reglage, accepte avec")
verifie(!A("COUNTER.C2", C) && !A("COUNTER.C3", C), "compteur mal regle (type inconnu, impulsionsParUnite 0) : refuse")
verifie(!A("TasmotaSlaveModBus.TasmotaSlaveModBus1.COUNTER.C1", {}), "compteur d'un esclave sans reglage : refuse")
verifie(!A("sensorsCuve.valeursAnalogiques.valeurCapteurHauteur", C) && A("sensorsCuve.niveauCuve.volume", C)
        && A("sensorsCuve.valeursAnalogiquesX.y", C), "'exclues' : debut de chemin par segment entier")
verifie(!A("hauteurEau", {}) && !A("Time", {}), "feuille de premier niveau refusee (anciens noms d'avant la decouverte)")
verifie(!A("DS18B20.Id", {}) && !A("x.TempUnit", {}), "cles techniques refusees (Id, TempUnit)")
# Relecture A8 (2026-10-19) : le filtre ne depend pas de la casse, ni d'un nom exact
verifie(!A("Relais.R1", {}) && !A("x.Relays.r1", {}) && !A("x.relay1", {}) && !A("x.Power1", {}) && !A("x.power2", {})
        && !A("TasmotaSlaveModBus.S1.Relais.r", {}), "relais refuses quelle que soit la casse (Relais, Relays, relay1, Power1, power2)")
verifie(!A("x.Entrees.E1", {}) && !A("x.entrees.e1", {}) && !A("x.inputs.i1", {}) && !A("x.switch1", {}) && !A("x.BUTTON2", {})
        && !A("TasmotaSlaveModBus.S1.entrees.e", {}), "entrees refusees quelle que soit la casse (Entrees, inputs, switch1, BUTTON2)")
verifie(!A("PWM.PWM1", {}) && !A("A.PWM1", {}) && !A("A.Dimmer", {}) && !A("x.shutter1", {}), "actionneurs refuses (PWM, Dimmer, shutter)")
verifie(A("ENERGY.Power", {}) && A("x.PowerFactor", {}) && A("x.ApparentPower", {}) && A("x.Pressure", {}),
        "mesures dont le nom contient power ou pres de relais : acceptees (ENERGY.Power, PowerFactor, ApparentPower)")
verifie(!A("Relais.R1", {"ajouts": ["Relais.R1"], "exclues": ["Relais.R1"]}) && !A("ESP32.Temperature", {"ajouts": ["ESP32.Temperature"], "exclues": ["ESP32"]}),
        "'exclues' l'emporte sur 'ajouts'")
verifie(!A("@POWER1", {"ajouts": ["@POWER1"]}) && !A("@Power1", {"ajouts": ["@Power1"]}) && !A("@foo", {"ajouts": ["@foo"]})
        && A("@heap", {"ajouts": ["@heap"]}), "source interne : seules @rssi et @heap, meme dans 'ajouts'")
var leveMax = nil
var choixMax = nil
for v: [nil, [], {}, "abc", "x"]
    try choixMax = historiqueSeries.choisit(SENSOR, {"seriesMax": v}, nil) except .. as e, m leveMax = str(e) + " " + str(m) end
end
verifie(leveMax == nil && size(choixMax) >= 1, "seriesMax mal type (null, liste, map, texte) : pas d'exception")
verifie(size(historiqueSeries.choisit(SENSOR, {"seriesMax": nil}, nil)) == size(historiqueSeries.choisit(SENSOR, {}, nil)),
        "seriesMax null : defaut 12")

# ---- 2. Decouverte dans le JSON SENSOR ----------------------------------------------------------
print("2. Decouverte (historiqueSeries.choisit)")
var ATTENDU = ["DS18B20.Temperature", "ENERGY.Power", "ENERGY.Total",
               "TasmotaSlaveModBus.TasmotaSlaveModBus1.ANALOG.A1",
               "TasmotaSlaveModBus.TasmotaSlaveModBus1.Temperatures.DS18B20-1.Temperature",
               "sensorsCuve.niveauCuve.hauteurEau", "sensorsCuve.niveauCuve.tauxRemplissage", "sensorsCuve.niveauCuve.volume",
               "sensorsCuve.valeursAnalogiques.valeurCapteurHauteur"]
var choix = historiqueSeries.choisit(SENSOR, {}, nil)
verifie(choix == ATTENDU, "sans reglage : seules les mesures, triees -> " + str(choix))
var interdits = 0
for c: choix
    for motif: ["Switch", "Button", "POWER", "ESP32", "COUNTER", ".Id", "Time"]    if (string.find(c, motif) >= 0)    interdits += 1    end    end
end
verifie(interdits == 0, "temoin : aucune entree, aucun relais, aucun interne, aucun compteur non regle")
choix = historiqueSeries.choisit(SENSOR, C, ["vieuxNom", "TasmotaSlaveModBus.TasmotaSlaveModBus2.ANALOG.A1", "Switch1"])
verifie(choix.find("COUNTER.C1") != nil && choix.find("ESP32.Temperature") != nil && choix.find("@rssi") != nil
        && choix.find("@power1") == nil, "avec reglages : compteur regle et ajouts presents, @power1 absent")
verifie(choix.find("TasmotaSlaveModBus.TasmotaSlaveModBus2.ANALOG.A1") != nil && choix.find("vieuxNom") == nil
        && choix.find("Switch1") == nil, "anciens : chemin admissible garde meme absent du JSON, ancien nom et entree ecartes")
verifie(choix.find("sensorsCuve.valeursAnalogiques.valeurCapteurHauteur") == nil, "'exclues' appliquee a la decouverte")
var avantLog = size(journal)
choix = historiqueSeries.choisit(SENSOR, {"seriesMax": 3}, nil)
verifie(choix == ATTENDU[0 .. 2] && size(journal) == avantLog + 1 && journal[-1][1] == LOG_LEVEL_DEBUG,
        "seriesMax 3 : les 3 premieres, une ligne debug pour les series ignorees (pas d'info chaque heure)")
choix = historiqueSeries.choisit(SENSOR, {"seriesMax": 3}, ["sensorsCuve.niveauCuve.volume"])
verifie(choix == ["DS18B20.Temperature", "ENERGY.Power", "sensorsCuve.niveauCuve.volume"],
        "seriesMax 3 : une serie deja enregistree n'est pas chassee par une nouvelle qui se trie avant elle")
verifie(size(historiqueSeries.choisit(SENSOR, {"seriesMax": 0}, nil)) == 1, "seriesMax 0 (mal regle) : borne a 1 serie")
verifie(historiqueSeries.choisit({"Switch1": "ON", "Time": "x"}, {}, nil) == [], "carte sans capteur : aucune serie")
# JSON SENSOR REEL du maitre P4 (Status 10 du 2026-10-18 19:12) : volet, boutons, relais d'un esclave, compteur
var SENSOR_P4 = json.load('{"Time": "2026-10-18T19:12:15", "COUNTER": {"C1": 0}, "ESP32": {"Temperature": 27.4}, '
    '"Shutter1": {"Position": 100, "Direction": 0, "Target": 100, "Tilt": 0}, "Button2": "OFF", "Button1": "OFF", '
    '"TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {"POWER1": "OFF"}, "TasmotaSlaveModBus2": {}}, '
    '"DS18B20": {"id": "C1041600F6FBFF28", "Temperature": 0.0}, "sensorsCuve": {"valeursAnalogiques": '
    '{"valeurCapteurHauteur": 0}, "niveauCuve": {"tauxRemplissage": 0.0, "hauteurEau": 0, "volume": 0}}, "TempUnit": "C"}')
choix = historiqueSeries.choisit(SENSOR_P4, {}, nil)
verifie(choix == ["DS18B20.Temperature", "sensorsCuve.niveauCuve.hauteurEau", "sensorsCuve.niveauCuve.tauxRemplissage",
                  "sensorsCuve.niveauCuve.volume", "sensorsCuve.valeursAnalogiques.valeurCapteurHauteur"],
        "JSON reel du P4 : sonde et valeurs de la cuve ; ni volet (Shutter1), ni boutons, ni relais, ni ESP32, ni compteur")
verifie(historiqueSeries.choisit(SENSOR_P4, {"ajouts": ["Shutter1.Position"]}, nil).find("Shutter1.Position") != nil,
        "position du volet ajoutable par 'ajouts'")

# ---- 3. Compteurs -------------------------------------------------------------------------------
print("3. Conversion des compteurs (historiqueSeries.convertit)")
var CC = {"compteurs": {"COUNTER.C1": {"type": "energie", "impulsionsParUnite": 1000},
                        "COUNTER.C2": {"type": "debit", "impulsionsParUnite": 450}}}
var ch = ["COUNTER.C1", "COUNTER.C2", "DS18B20.Temperature"]
tasmota.ms = 1000000
var v = [2500, 900, 12.5]
historiqueSeries.convertit(ch, v, CC)
verifie(v[0] == 2.5 && v[1] == nil && v[2] == 12.5, "energie 2500/1000 = 2,5 ; debit : premiere releve sans valeur ; autre serie intacte")
tasmota.ms += 60000
v = [2500, 1350, 12.5]
historiqueSeries.convertit(ch, v, CC)
verifie(v[1] == 1.0, "debit : 450 impulsions en 1 min a 450/L -> 1 L/min")
tasmota.ms += 120000
v = [2500, 1800, 12.5]
historiqueSeries.convertit(ch, v, CC)
verifie(v[1] == 0.5, "debit : 450 impulsions en 2 min -> 0,5 L/min")
tasmota.ms += 60000
v = [2500, 10, 12.5]
historiqueSeries.convertit(ch, v, CC)
verifie(v[1] == nil, "debit : compteur remis a zero (redemarrage) -> pas de valeur, pas de debit negatif")
tasmota.ms += 60000
v = [nil, 460, 12.5]
historiqueSeries.convertit(ch, v, CC)
verifie(v[0] == nil && v[1] == 450.0 / 450, "valeur absente laissee nil ; le debit repart apres la remise a zero")

# ---- 4. Releve : decouverte, redecouverte horaire, fichier du mois ------------------------------
print("4. Releve (historiqueFonctions.releve)")
var T = 1792324800                      # 2026-10-18 12:00 UTC
var MOIS = DOSSIER + "/mesures-2026-10.bin"
# Fichier du mois laisse par un demarrage precedent (en-tete seul) + un -a deja mis de cote
def ecritEntete(fichier, noms)
    var b = bytes().fromstring("HST1")
    b.add(size(string.split(noms, ",")), 1)
    b.add(size(noms), 2)
    b = b + bytes().fromstring(noms)
    var f = open(fichier, "wb")
    f.write(b)
    f.close()
end
ecritEntete(MOIS, "DS18B20.Temperature,vieuxNom,TasmotaSlaveModBus.TasmotaSlaveModBus2.ANALOG.A1")
ecritEntete(DOSSIER + "/mesures-2026-10-a.bin", "autre")
var CONFIG = {"activation": "ON", "pasMinutes": 5, "dureeHeures": 1, "moisConserves": 24, "seriesMax": 20,
              "exclues": [], "ajouts": ["@rssi"], "compteurs": {"COUNTER.C1": {"type": "energie", "impulsionsParUnite": 1000}}}
historiqueFonctions.demarre(CONFIG)
verifie(tasmota.crons.find("majHistorique") != nil, "demarre : releve programmee chaque minute")
tasmota.utc = T + 60
tasmota.ms = 60000
tasmota.capteurs = json.dump(SENSOR)
historiqueFonctions.releve()
verifie(historiqueFonctions.chemins == nil && historiqueFonctions.instances.find("mesures") == nil, "avant 2 min : rien n'est decouvert")
tasmota.ms = 180000
historiqueFonctions.releve()
var h1 = historiqueFonctions.instances.find("mesures")
var chemins1 = historiqueFonctions.chemins
verifie(h1 != nil && chemins1 != nil && chemins1.find("COUNTER.C1") != nil && chemins1.find("@rssi") != nil
        && chemins1.find("TasmotaSlaveModBus.TasmotaSlaveModBus2.ANALOG.A1") != nil && chemins1.find("vieuxNom") == nil,
        "premiere decouverte : mesures + compteur regle + ajout + serie du mois deja enregistree")
verifie(dernierLog("Series enregistrees") != nil && dernierLog("Series enregistrees")[1] == LOG_LEVEL_INFO, "log info des series enregistrees")
var iC = chemins1.find("COUNTER.C1")
verifie(h1.nbPas[iC] == 1 && h1.sommePas[iC] == 2.5, "premiere mesure enregistree, compteur converti (2,5 kWh)")
# Meme heure : un capteur nouveau n'est pas encore pris
var SENSOR2 = json.load(json.dump(SENSOR))
SENSOR2["AM2301"] = {"Temperature": 18.2, "Humidity": 55.0}
tasmota.capteurs = json.dump(SENSOR2)
tasmota.utc = T + 120    tasmota.ms += 60000
historiqueFonctions.releve()
verifie(historiqueFonctions.instances["mesures"] == h1 && historiqueFonctions.chemins == chemins1, "meme heure : liste inchangee")
# Heure suivante : il s'ajoute, nouvel historique
tasmota.utc = T + 3600 + 60    tasmota.ms += 60000
historiqueFonctions.releve()
var h2 = historiqueFonctions.instances["mesures"]
verifie(h2 != h1 && historiqueFonctions.chemins.find("AM2301.Humidity") != nil && historiqueFonctions.chemins.find("AM2301.Temperature") != nil,
        "heure suivante : AM2301 ajoute, nouvel historique")
var plein = json.load(json.dump(CONFIG))
plein["seriesMax"] = size(chemins1)
verifie(historiqueSeries.choisit(SENSOR2, plein, chemins1) == chemins1,
        "liste deja a seriesMax : un capteur nouveau n'entre pas, aucune serie enregistree n'est chassee")
var l = dernierLog("Nouvelles series")
verifie(l != nil && l[1] == LOG_LEVEL_INFO && string.find(l[0], "AM2301.Humidity") > 0, "log info des series ajoutees")
verifie(size(path.renommages) == 1 && path.renommages[0][1] == DOSSIER + "/mesures-2026-10-b.bin",
        "heure close avec une autre liste : fichier du mois mis de cote en -b (le -a existant n'est pas ecrase)")
verifie(historiqueFonctions.lisEntete(MOIS) == chemins1.concat(","), "nouveau fichier du mois : en-tete = series de l'heure close")
# Heure d'apres : AM2301 ne repond plus -> il reste (trou), pas de nouvel historique
tasmota.capteurs = json.dump(SENSOR)
tasmota.utc = T + 7200 + 60    tasmota.ms += 60000
var chemins2 = historiqueFonctions.chemins
historiqueFonctions.releve()
verifie(historiqueFonctions.instances["mesures"] == h2 && historiqueFonctions.chemins == chemins2,
        "serie disparue : gardee, pas de nouvel historique")
# Exception dans un filtre de module : journalisee, la releve suivante repart
historiqueFonctions.ajouteFiltre(def (c, v) raise "value_error", "filtre casse" end)
historiqueFonctions.releve()
verifie(dernierLog("HISTORIQUE_RELEVE_ERREUR") != nil && dernierLog("HISTORIQUE_RELEVE_ERREUR")[1] == LOG_LEVEL_ERREUR,
        "exception d'un filtre : une ligne HISTORIQUE_RELEVE_ERREUR")

# ---- 5. /histo?p=jour : le pas en cours est livre (la page suit l'heure reelle) -----------------
print("5. /histo?p=jour : pas en cours (encours, tEncours)")
import webserver
def jour(nom)
    webserver.raz({"p": "jour", "n": nom})
    webserver.sortie = open(SORTIE + "/jour_" + nom + ".json", "wb")
    historiqueFonctions.page()
    webserver.sortie.close()
    var f = open(SORTIE + "/jour_" + nom + ".json", "r")
    var texte = f.read()
    f.close()
    var d = json.load(texte)
    if (d == nil)    print("    JSON illisible : " + texte[0 .. 200])    end
    return d
end
var h = historiqueFonctions.instances["mesures"]
var jj = jour("mesures")
var iT = h.series.find("DS18B20.Temperature")
var iH = h.series.find("AM2301.Humidity")
verifie(jj != nil && jj.find("tEncours") == h.pasCourant * h.pas, "tEncours = debut du pas en cours (epoch UTC)")
verifie(jj != nil && size(jj.find("encours", [])) == h.nbSeries && jj["encours"][iT] == 12.5 && jj["encours"][iH] == nil,
        "encours = moyenne du pas en cours par serie (12,5), null sans mesure (AM2301 muet)")
verifie(jj != nil && size(jj["valeurs"]) == h.nbSeries && size(jj["valeurs"][0]) == h.nbPoints,
        "valeurs des pas clos inchangees (nbPoints par serie)")
historiqueFonctions.HISTORIQUE("vierge", ["DS18B20.Temperature"], CONFIG)
var jv = jour("vierge")
verifie(jv != nil && jv.find("tEncours", 0) == nil && size(jv.find("encours", [0])) == 0 && jv["t0"] == nil,
        "historique sans mesure : tEncours null, encours vide")

# ---- 6. /histo?p=direct : valeurs actuelles (graphiques en temps reel) ---------------------------
print("6. /histo?p=direct : valeurs actuelles, lecture des capteurs en cache 4 s")
def direct()
    webserver.raz({"p": "direct", "n": "mesures"})
    webserver.sortie = open(SORTIE + "/direct.json", "wb")
    historiqueFonctions.page()
    webserver.sortie.close()
    var f = open(SORTIE + "/direct.json", "r")
    var d = json.load(f.read())
    f.close()
    return d
end
var iC2 = h.series.find("COUNTER.C1")
tasmota.capteurs = json.dump(SENSOR)
tasmota.ms += 10000
avantLog = size(journal)
var dd = direct()
verifie(dd != nil && dd["t"] == tasmota.utc && size(dd["valeurs"]) == h.nbSeries && dd["valeurs"][iT] == 12.5,
        "valeur actuelle de chaque serie, datee de l'heure UTC de la carte")
verifie(dd != nil && dd["valeurs"][iC2] == 2.5, "compteur energie converti (2500 / 1000)")
verifie(dd != nil && dd["valeurs"][iH] == nil, "capteur absent du JSON : null")
verifie(dernierLog("HISTORIQUE_DIRECT_ERREUR") != nil && size(journal) > avantLog,
        "filtre d'un module en exception : journalise, les valeurs partent quand meme")
var S3 = json.load(json.dump(SENSOR))
S3["DS18B20"]["Temperature"] = 20.0
tasmota.capteurs = json.dump(S3)
tasmota.ms += 1000
dd = direct()
verifie(dd != nil && dd["valeurs"][iT] == 12.5, "moins de 4 s apres : capteurs pas relus (cache)")
tasmota.ms += 5000
dd = direct()
verifie(dd != nil && dd["valeurs"][iT] == 20.0, "plus de 4 s apres : capteurs relus")
var S4 = json.load(json.dump(SENSOR))
S4.remove("COUNTER")
tasmota.capteurs = json.dump(S4)
tasmota.ms += 5000
dd = direct()
verifie(dd != nil && dd["valeurs"][iC2] == nil, "compteur energie absent du JSON : null (pas la moyenne du pas)")
tasmota.capteurs = "LEVE"
tasmota.ms += 5000
avantLog = size(journal)
var leveDirect = nil
try dd = direct() except .. as e, m leveDirect = str(e) + " " + str(m) end
verifie(leveDirect == nil && webserver.ferme && dd != nil && dd["valeurs"][iT] == nil && dernierLog("HISTORIQUE_DIRECT_ERREUR") != nil
        && size(journal) > avantLog, "lecture des capteurs en exception : reponse fermee, JSON complet (null), erreur journalisee")
# Nouvelles series : l'ancien historique ne doit pas rester tenu par le cache du direct (deux tampons RAM)
tasmota.capteurs = json.dump(SENSOR)
tasmota.ms += 5000
direct()
var S5 = json.load(json.dump(SENSOR))
S5["SHT3X"] = {"Temperature": 18.0, "Humidity": 60.0}
historiqueFonctions.choisitSeries(S5, historiqueFonctions.chemins)
verifie(historiqueFonctions.cacheDirect == nil, "nouvel historique : cache du direct lache (ancien tampon RAM liberable)")
# Relecture A8 (2026-10-19) : tampon du nouvel historique impossible a allouer (RAM basse) -> pas d'etat incoherent
var classeHistorique = historiqueFonctions.HISTORIQUE
historiqueFonctions.HISTORIQUE = def (nom, chemins, config) raise "memory_error", "bytes" end
var S6 = json.load(json.dump(S5))
S6["BMP280"] = {"Pressure": 1013.2}
var leveCreation = nil
var recree = nil
avantLog = size(journal)
try recree = historiqueFonctions.choisitSeries(S6, historiqueFonctions.chemins) except .. as e, m leveCreation = str(e) + " " + str(m) end
historiqueFonctions.HISTORIQUE = classeHistorique
verifie(leveCreation == nil && recree == false && historiqueFonctions.chemins == nil && dernierLog("HISTORIQUE_ERREUR") != nil,
        "creation impossible : pas d'exception, chemins remis a nil (redecouverte a la releve suivante), erreur journalisee")
tasmota.capteurs = json.dump(S6)
tasmota.ms += 60000
historiqueFonctions.releve()
verifie(historiqueFonctions.instances.find("mesures") != nil && historiqueFonctions.chemins != nil
        && historiqueFonctions.chemins.find("BMP280.Pressure") != nil, "releve suivante : historique recree avec les nouvelles series")

print(echecs == 0 ? "BANC_HISTORIQUE: OK" : "BANC_HISTORIQUE: ECHEC (" + str(echecs) + ")")
