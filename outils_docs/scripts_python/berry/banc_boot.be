# Banc de test Berry du CHEMIN DE DEMARRAGE du maitre P4 du garage (2026-10-23, audit Berry P10.3, constat B8).
# -----------------------------------------------------------------------------------------------------------
# A lancer DEPUIS LA RACINE DU DEPOT, de preference par son enveloppe (code de sortie 0/1) :
#     python outils_docs/scripts_python/berry/banc_boot.py [dossier_sources]
# ou directement (verdict = DERNIERE ligne, BANC_BOOT: OK | ECHEC (...)) :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_boot.be [dossier_sources] [--verbeux]
# dossier_sources (defaut data/fs) : pour eprouver un correctif ou une mutation sur une COPIE ENTIERE de data/fs.
# Mise au point : '--cas N' lance un seul cas ; '--trace' l'execute sans try (pile d'appel de l'exception).
#
# CE QUI TOURNE POUR DE VRAI
#   data/garage/tasmota32p4-serveur-modbus/autoexec.be EN ENTIER, et tout ce qu'il charge, sans exception :
#   configGlobal, configDevices, configModules, controleGeneral, globalFonctions, logFonctions,
#   diversFonctions, gestionFileFolder, webFonctions, modbusFonctions, les controleXxx (LedTemoin, Web, UDP,
#   Modbus, RangeExtender, VoletRoulants, Discovery, ES8311), i2c_*, modBus_*, historique*, graphiques*,
#   et les fichiers de la carte (controleGarage.be, garageFonctions.be). Les modules SOLIDIFIES dans le
#   firmware de la carte sont construits comme le fait solidify_all.be (fichier execute au niveau global,
#   puis la globale du module est prise) ; leur liste est LUE dans platformio_tasmota_cenv.ini.
#
# CE QUI EST BOUCHONNE (bouchons_berry/boot/, lire leurs en-tetes) et pourquoi
#   - faux_firmware.be : tasmota (regles, commandes, drivers, crons, minuteries, tasmota.cmd qui repond comme
#     le firmware aux commandes lues au boot), log, load, Driver, et un LittleFS EN MEMOIRE (open() remplace :
#     rien n'est ecrit sur le PC, sauf les enveloppes des solidifies dans .pio/banc_boot/, ignore par git) ;
#   - persist, path, mqtt, webserver, gpio, light, crc, crypto : modules natifs du firmware, absents de
#     berry.exe ; udp, tcpserver, serial, Wire... : objets factices, AUCUNE emission reseau ni serie ;
#   - preparation_boot.be : remplit le LittleFS comme un televersement (data/fs moins solidifies et liste
#     noire, data/json, data/sd, dossier de la carte, persist du cas).
#   Limites : pas de timing reel ni de memoire reelle (tasmota.memory est fixe), pas de bus (ModBus ; en I2C
#   tout peripherique repond), une seule carte (le P4). Les globales auxiliaires creees en construisant un
#   module solidifie (classes, fonctions xxx_init) existent au banc, pas sur la carte.
#
# LES CAS (chacun dans son PROPRE processus berry.exe : Berry garde un module importe en cache, et
# 'import controleGeneral' n'appelle init() qu'au premier import ; un 2e cas dans le meme processus
# ne redemarrerait donc rien). Sans '--cas', ce fichier lance les cas l'un apres l'autre et conclut.
#   1. persist REEL du P4 : la reference. Demarrage complet, sans exception ni log d'erreur, drivers,
#      regles, commandes, LittleFS ; puis les timers de redemarrage (correctif P5.1 du 2026-10-23) ; puis
#      les evenements de demarrage (System#Init/Boot, WIFI, MQTT, Time, HTTP) et 10 s simulees de TOUS
#      les drivers (every_50ms... every_second, minuteries, web_add_handler, web_sensor, json_append).
#   2. persist '{}' : constat B1 de l'audit (l'autoexec plante ligne 19, diverses.find sur nil).
#   3. persist reel PRIVE de serveur.wifi : constats B2/B3 (ReglageGlobal/ReglageLog jamais enregistrees,
#      modules suivants non charges), avec un TEMOIN : les controles de reference DOIVENT y echouer
#      (preuve que le banc voit un echec).
#   4. persist reel, codec ES8311 absent du bus I2C : defaut trouve par ce banc (exception a l'import de
#      controleES8311, qui arrete l'autoexec avant l'historique et controleGarage).
#
# DEFAUTS CONNUS : pourquoi un cas "rouge aujourd'hui" n'echoue pas le banc
#   Le comportement ATTENDU apres correction est ecrit des aujourd'hui (fonction connu()). Tant que le
#   drapeau du defaut vaut true dans DEFAUTS_CONNUS, un controle non satisfait s'affiche CONNU et ne compte
#   pas ; s'il devient satisfait, il s'affiche CORRIGE ? et COMPTE comme echec : on vient de corriger, il
#   faut passer le drapeau a false. A false, ces controles sont des attentes ordinaires (ok / ECHEC).
#   Ainsi le banc reste vert sur l'existant, et devient le banc de non-regression de P10.1/P10.2 sans
#   etre reecrit. Les cles de DEFAUTS_CONNUS sont les constats de l'audit (B1, B2, B3) et les defauts
#   trouves en ecrivant ce banc (MAC, ES8311).
#   Le dossier de la carte (autoexec.be...) est TOUJOURS lu dans data/garage/... : seul data/fs se remplace
#   par l'argument. Un chemin de sources avec des espaces n'est pas pris en charge (ligne de commande).
import global
import sys
import os
import string
import json

# Globales posees par les fichiers de bouchons_berry/boot (declarees ici : le banc est compile avant eux)
BANC_BOOT = nil  LITTLEFS = nil  tasmota = nil  PREPARATION_BOOT = nil  OBJET_FACTICE = nil

var DEFAUTS_CONNUS = {
    "B1": true,         # audit B1 / P10.1 : pas de garde de tete dans l'autoexec (persist vide ou sans 'diverses')
    "B2": true,         # audit B2 / P10.2 : pas de try/except par controleXxx -> un echec arrete tout l'autoexec
    "B3": true,         # audit B3 / P10.2 : ReglageGlobal/ReglageLog enregistrees APRES configGlobalByJson
    "MAC": true,        # trouve par ce banc : globalFonctions.be:87-88, adressMAC "" jamais remplacee (map.insert)
    "ES8311": true,     # trouve par ce banc : controleES8311.be, codec absent du bus I2C -> exception a l'import
}
var ENV = "tasmota32p4-garage-serveur-modbus"
var CARTE = "data/garage/tasmota32p4-serveur-modbus"
var BOUCHONS = "outils_docs/scripts_python/berry/bouchons_berry/boot"
var TRAVAIL = ".pio/banc_boot"
var CE_FICHIER = global._argv[0]

var SOURCES = "data/fs"
var CAS = nil
var TRACE = false           # --trace : autoexec SANS try, pour voir la pile d'appel d'une exception
var VERBEUX = false         # --verbeux : imprime chaque log emis
var i = 1
while i < size(global._argv)
    var a = global._argv[i]
    if a == "--cas"    CAS = int(global._argv[i + 1])    i += 1
    elif a == "--trace"    TRACE = true
    elif a == "--verbeux"    VERBEUX = true
    else    SOURCES = a
    end
    i += 1
end

# ============================================================== orchestrateur : un processus par cas
if CAS == nil
    var exe = "lib/libesp32/berry/berry.exe"
    if os.path.exists(exe)    exe = string.replace(exe, "/", string.char(92))    else    exe = "lib/libesp32/berry/berry"    end
    var options = (VERBEUX ? " --verbeux" : "")
    var rouges = []
    for n: 1 .. 4
        # Code de sortie du cas = nombre d'echecs (0 = vert) ; un cas qui plante sort aussi en non nul
        var rc = os.system(exe + " " + CE_FICHIER + " " + SOURCES + " --cas " + str(n) + options)
        if rc != 0    rouges.push("cas " + str(n) + " rc=" + str(rc))    end
    end
    print("")
    print(size(rouges) == 0 ? "BANC_BOOT: OK" : "BANC_BOOT: ECHEC (" + rouges.concat(", ") + ")")
    return
end

# ============================================================== un cas
def litDisque(chemin)               # open() d'origine : ce fichier est compile avant faux_firmware
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end
def ecrisDisque(chemin, texte)
    var f = open(chemin, "w")
    f.write(texte)
    f.close()
end

var echecs = 0
def controle(nom, condition)
    if condition    print("  ok      " + nom)
    else            print("  ECHEC   " + nom)    echecs += 1
    end
end
# Comportement attendu APRES correction du defaut 'cle' (voir l'en-tete)
def connu(cle, nom, condition, constat)
    if !DEFAUTS_CONNUS.find(cle, false)    controle(nom + " [" + cle + "]", condition)    return    end
    if condition
        print("  CORRIGE ? " + nom + " [" + cle + "] : passer DEFAUTS_CONNUS['" + cle + "'] a false")
        echecs += 1
    else
        print("  CONNU   " + nom + " [" + cle + "]" + (constat != nil ? " -- aujourd'hui : " + constat : ""))
    end
end

# --- environnement de la carte, puis demarrage
compile(BOUCHONS + "/faux_firmware.be", "file")()
compile(BOUCHONS + "/preparation_boot.be", "file")()
BANC_BOOT.verbeux = VERBEUX
BANC_BOOT.sources = SOURCES
BANC_BOOT.litDisque = litDisque
BANC_BOOT.ecrisDisque = ecrisDisque

var persistReel = json.load(litDisque(CARTE + "/_persist.json"))
var persistCas
if CAS == 1         persistCas = persistReel
elif CAS == 2       persistCas = {}
elif CAS == 3       persistCas = json.load(json.dump(persistReel))    persistCas["serveur"].remove("wifi")
else                persistCas = persistReel
end
var TITRES = {1: "persist reel du P4 (reference)", 2: "persist '{}' (constat B1)", 3: "persist reel prive de serveur.wifi (constat B3)",
              4: "persist reel, codec ES8311 absent du bus I2C (adresse 0x18)"}
print("")
print(string.format("=== Cas %i : %s -- sources %s", CAS, TITRES[CAS], SOURCES))

if CAS == 4    tasmota.i2cAbsents = [0x18]    end
var dossierSolidifies = PREPARATION_BOOT.prepare(ENV, SOURCES, CARTE, json.dump(persistCas), TRAVAIL)
sys.path().push(CARTE)                  # fichiers de la carte (garageFonctions, ...), cherches en dernier
sys.path().push(SOURCES)                # modules NON solidifies de data/fs
sys.path().push(dossierSolidifies)      # enveloppes des modules solidifies : avant leur .be
sys.path().push(BOUCHONS)               # modules natifs du firmware : cherches en premier
# Globales posees par le firmware AVANT autoexec.be (be_berry_init_code, xdrv_52_7_berry_embedded.ino)
compile("import gpio import light wire1 = OBJET_FACTICE('wire1') wire2 = OBJET_FACTICE('wire2')")()

var exception = nil
var autoexec = compile(LITTLEFS.fichiers["/autoexec.be"])
if TRACE    autoexec()    end
try
    autoexec()
except .. as e, m
    exception = str(e) + " - " + str(m)
end

# ============================================================== controles
def lignesErreur()
    var r = []
    for l: BANC_BOOT.journal
        if l[1] == 1 || string.find(l[0], "_ERREUR") >= 0    r.push(l[0])    end
    end
    return r
end
def classesDrivers()
    var r = []
    for d: tasmota.drivers    r.push(classname(d))    end
    return r
end
def compte(liste, valeur)
    var n = 0
    for x: liste    if x == valeur    n += 1    end    end
    return n
end

var DRIVERS_ATTENDUS = ["CONTROLE_GENERAL", "CONTROLE_WEB", "CONTROLE_UDP", "CONTROLE_MODBUS", "MODBUS_CONN_16CHANNEL",
                        "MODBUS_TASMOTA_SLAVE", "CONTROLE_RANGE_EXTENDER", "CONTROLE_VR", "CONTROLE_DISCOVERY", "ES8311",
                        "HISTORIQUE_WEB", "CONTROLE_GARAGE"]
var COMMANDES_ATTENDUES = ["ReglageGlobal", "ReglageLog", "ReglageModbus", "ReglageSlaveModBus", "ReglageConn16Channel",
                           "ReglageUDP", "ReglageRangeExtender", "ReglageDiscovery", "ReglageVolets", "ReglageGarage"]
var REGLES_ATTENDUES = ["controleGeneral_System", "controleGeneral_Wifi", "controleGeneral_Mqtt", "controleGeneral_Time"]

# Controles du demarrage de reference. 'v' = controle (cas 1) ou un compteur (temoin du cas 3).
def controlesReference(v)
    v("autoexec.be execute jusqu'au bout, sans exception" + (exception != nil ? " : " + exception : ""), exception == nil)
    v("aucun echec de load() ni de tasmota.compile (BRY: failed)" + (size(BANC_BOOT.echecsLoad) > 0 ? " : " + str(BANC_BOOT.echecsLoad[0]) : ""), size(BANC_BOOT.echecsLoad) == 0)
    v("tous les modules solidifies se construisent" + (size(BANC_BOOT.echecsSolidifies) > 0 ? " : " + str(BANC_BOOT.echecsSolidifies[0]) : ""), size(BANC_BOOT.echecsSolidifies) == 0)
    var erreurs = lignesErreur()
    v("aucun log d'erreur (niveau 1 ou _ERREUR)" + (size(erreurs) > 0 ? " : " + erreurs[0] : ""), size(erreurs) == 0)
    v("toute methode de tasmota appelee est imitee par le banc" + (size(tasmota.inconnus) > 0 ? " : " + str(tasmota.inconnus) : ""), size(tasmota.inconnus) == 0)

    var noms = classesDrivers()
    for c: DRIVERS_ATTENDUS    v("driver " + c + " enregistre (tasmota.add_driver)", noms.find(c) != nil)    end
    v("deux drivers CONTROLE_UDP (unicast + multicast)", compte(noms, "CONTROLE_UDP") == 2)
    var cg = global.controleGeneral
    v("global controleGeneral = l'instance du driver, init terminee (flagINIT = 1)",
      classname(cg) == "CONTROLE_GENERAL" && cg.flagINIT == 1)
    for r: REGLES_ATTENDUES    v("regle " + r + " posee (tasmota.add_rule)", tasmota.regle(r) != nil)    end
    for c: COMMANDES_ATTENDUES    v("commande " + c + " enregistree (tasmota.add_cmd)", tasmota.commandes.contains(c))    end

    var nb = (classname(cg) == "CONTROLE_GENERAL") ? cg.nbIOActivesJSON : {}
    v("relais actifs comptes par configDevicesByRules (" + str(nb.find("relais", {}).find("actives", {}).find("nb")) + ")",
      nb.find("relais", {}).find("actives", {}).find("nb", 0) > 0)
    v("/json/nbIOActives.json ecrit et a jour", LITTLEFS.fichiers.find("/json/nbIOActives.json") == json.dump(nb))
    for d: ["/json", "/sd", "/logs", "/.extensions"]    v("dossier " + d + " present (listeEtRepartitLesFichiers)", LITTLEFS.dossiers.contains(d))    end
    v("graphiques.json range de / vers /json", LITTLEFS.fichiers.contains("/json/graphiques.json") && !LITTLEFS.fichiers.contains("/graphiques.json"))
    v("garageFonctions compile en .bec et .be supprime (compileModule)", LITTLEFS.fichiers.contains("/garageFonctions.bec") && !LITTLEFS.fichiers.contains("/garageFonctions.be"))
    v("controleGarage compile en .bec (loadBerryFile)", LITTLEFS.fichiers.contains("/controleGarage.bec"))
    var veille = json.load(LITTLEFS.fichiers.find("/json/driversInactifs.json", "{}"))
    v("environnement du driver inactif 'ecran' mis en veille (hiberneDriversInactifs)",
      isinstance(veille, map) && veille.contains("ecran") && global.drivers != nil && global.drivers["ecran"]["environnement"].size() == 0)
    v("Wi-Fi, nom et MQTT appliques (Backlog SSId1, Hostname, MqttHost)",
      size(tasmota.envoyees("Backlog SSId1 ")) == 1 && size(tasmota.envoyees("Hostname SERVEUR-GARAGE")) == 1 && size(tasmota.envoyees("MqttHost ")) == 1)
    v("profil de logs 'normal' applique (MqttLog 1)", tasmota.envoyees("MqttLog ") == ["MqttLog 1"])
end

# Timers de redemarrage (correctif P5.1 du 2026-10-23) sur le driver controleGeneral demarre
def controlesTimers()
    var cg = global.controleGeneral
    print("  -- timers de redemarrage (P5.1)")
    controle("aucun cron 'timerRebootSiDeconnexionWifi' (le reboot sans Wi-Fi n'est plus un cron)",
             !tasmota.crons.contains("timerRebootSiDeconnexionWifi"))
    controle("pas de cron 'heureReboot' avant que l'heure soit reglee", !tasmota.crons.contains("heureReboot"))

    tasmota.regle("controleGeneral_Time")({"Initialized": 1792000000}, "Time", {"Time": {"Initialized": 1792000000}})
    var cron = tasmota.crons.find("heureReboot")
    controle("Time#Initialized pose le cron 'heureReboot' en '0 0 0 * * *' (heureReboot 00:00 du persist)",
             cron != nil && cron[0] == "0 0 0 * * *")
    tasmota.cmds = []
    if cron != nil    cron[1]()    end
    controle("la fonction du cron 'heureReboot' redemarre la carte (Restart 1)", tasmota.envoyees("Restart 1") == ["Restart 1"])

    # Wi-Fi : evenement de connexion, puis coupure ; every_second du VRAI driver, horloge simulee
    def secondes(n)    for k: 1 .. n    tasmota.horloge += 1000    cg.every_second()    end    end
    var regleWifi = tasmota.regle("controleGeneral_Wifi")
    regleWifi({"Connected": 1}, "Wifi", {"WIFI": {"Connected": 1}})
    controle("la regle Wifi Connected pose controleGeneral.connected", cg.connected == true)
    regleWifi({"Disconnected": 1}, "Wifi", {"WIFI": {"Disconnected": 1}})
    tasmota.wifiUp = false
    tasmota.cmds = []
    secondes(300)
    controle("Wi-Fi coupe : pas de redemarrage a 299 s (timerRebootSansWifi = 300)", size(tasmota.envoyees("Restart")) == 0)
    secondes(1)
    controle("Wi-Fi coupe : redemarrage a 300 s (Restart 1)", tasmota.envoyees("Restart 1") == ["Restart 1"])
    var erreur = false
    for l: BANC_BOOT.journal    if string.find(l[0], "CONTROLE_GENERAL_ERREUR: Reboot du module") == 0    erreur = true    end    end
    controle("le redemarrage sans Wi-Fi est logue en erreur", erreur)

    tasmota.cmds = []
    secondes(200)
    tasmota.wifiUp = true    secondes(1)    tasmota.wifiUp = false
    secondes(200)
    controle("une reconnexion remet le compte a zero (200 s + 200 s : pas de redemarrage)", size(tasmota.envoyees("Restart")) == 0)
    regleWifi({"Connected": 1}, "Wifi", {"WIFI": {"Connected": 1}})
    tasmota.cmds = []
    secondes(1000)
    controle("Wi-Fi reconnecte (regle Wifi) : pas de redemarrage", size(tasmota.envoyees("Restart")) == 0)
end

# Apres l'autoexec, le firmware publie les evenements de demarrage (xdrv_10_system_events.ino:225-270),
# demarre le serveur web, puis appelle les drivers. 10 s simulees : regles, minuteries (set_timer),
# every_50ms / every_100ms / every_250ms / every_second de CHAQUE driver, et ses callbacks web.
def controlesPremieresSecondes()
    import introspect
    import webserver
    print("  -- evenements de demarrage et 10 premieres secondes (tous les drivers)")
    tasmota.wifiUp = true
    BANC_BOOT.exceptions = []
    BANC_BOOT.journal = []          # le redemarrage sans Wi-Fi des timers a logue une erreur voulue
    var n = 0
    for ev: [{"System": {"Init": 1}}, {"WIFI": {"Connected": 1}}, {"MQTT": {"Connected": 1}},
             {"System": {"Boot": 1}}, {"Time": {"Initialized": 0}}, {"HTTP": {"Initialized": 1}}]
        n += tasmota.declenche(ev)
    end
    controle(string.format("%i regles declenchees par System#Init/Boot, WIFI, MQTT, Time, HTTP", n), n >= 5)
    var cg = global.controleGeneral
    controle("System#Boot pose controleGeneral.booted", cg.booted == true)
    connu("MAC", "System#Boot : adresse MAC (Status 5) relevee dans serveur.adressMAC", global.serveur.find("adressMAC") == tasmota.mac,
          "adressMAC reste '" + str(global.serveur.find("adressMAC")) + "' : map.insert ne remplace pas la cle vide du persist")

    for d: tasmota.drivers.copy()
        if introspect.get(d, "web_add_handler") != nil    tasmota.appelle(classname(d) + ".web_add_handler", /-> d.web_add_handler(), [])    end
    end
    controle("route /graphiques declaree au demarrage du serveur web", webserver.routes.contains("/graphiques"))

    var rythmes = [["every_50ms", 50], ["every_100ms", 100], ["every_250ms", 250], ["every_second", 1000]]
    for t: 1 .. 200                                     # 200 x 50 ms = 10 s
        tasmota.avance(50)
        for d: tasmota.drivers.copy()
            for r: rythmes
                if (t * 50) % r[1] == 0 && introspect.get(d, r[0]) != nil
                    var nom = r[0]
                    tasmota.appelle(classname(d) + "." + nom, /-> introspect.get(d, nom)(d), [])
                end
            end
        end
    end
    for d: tasmota.drivers.copy()
        for nom: ["web_add_main_button", "web_sensor", "json_append"]
            if introspect.get(d, nom) != nil    tasmota.appelle(classname(d) + "." + nom, /-> introspect.get(d, nom)(d), [])    end
        end
    end
    var ex = BANC_BOOT.exceptions
    controle("aucune exception dans les regles, minuteries et callbacks des drivers" + (size(ex) > 0 ? " : " + str(ex[0]) : ""), size(ex) == 0)
    var erreurs = lignesErreur()
    controle("aucun log d'erreur pendant ces 10 s" + (size(erreurs) > 0 ? " : " + erreurs[0] : ""), size(erreurs) == 0)
    controle("toute methode de tasmota appelee est imitee par le banc" + (size(tasmota.inconnus) > 0 ? " : " + str(tasmota.inconnus) : ""), size(tasmota.inconnus) == 0)
end

if CAS == 1
    controlesReference(controle)
    if classname(global.controleGeneral) == "CONTROLE_GENERAL"
        controlesTimers()               # d'abord : il verifie qu'aucun cron n'existe avant Time#Initialized
        controlesPremieresSecondes()
    else    controle("timers et premieres secondes : driver controleGeneral absent, non testes", false)
    end

elif CAS == 2
    var erreurs = lignesErreur()
    connu("B1", "persist {} : l'autoexec sort proprement, sans exception", exception == nil, exception)
    connu("B1", "persist {} : l'absence de parametrage est signalee (log d'erreur)", size(erreurs) > 0, "aucun log, la carte demarre muette")
    controle("persist {} : aucun driver n'est demarre sur un persist vide", size(tasmota.drivers) == 0)

elif CAS == 3
    connu("B3", "serveur.wifi absent : ReglageGlobal enregistree (reparation a distance)", tasmota.commandes.contains("ReglageGlobal"), exception)
    connu("B3", "serveur.wifi absent : ReglageLog enregistree", tasmota.commandes.contains("ReglageLog"))
    connu("B2", "serveur.wifi absent : les modules suivants sont charges (driver CONTROLE_GARAGE)", classesDrivers().find("CONTROLE_GARAGE") != nil)
    # TEMOIN : sur ce persist casse, les controles de reference DOIVENT echouer. S'ils passaient,
    # le banc ne saurait plus voir un echec (bouchon trop permissif, controle vide...).
    var nbEchecs = 0
    var premiers = []
    controlesReference(def (nom, ok) if !ok    nbEchecs += 1    if size(premiers) < 2    premiers.push(nom)    end    end end)
    controle(string.format("TEMOIN : les controles de reference voient la cle manquante (%i echec(s), dont : %s)", nbEchecs, premiers.concat(" / ")), nbEchecs > 0)

else
    connu("ES8311", "codec ES8311 absent : l'autoexec va au bout", exception == nil, exception)
    connu("ES8311", "codec ES8311 absent : les modules suivants sont charges (driver CONTROLE_GARAGE)", classesDrivers().find("CONTROLE_GARAGE") != nil)
    controle("codec ES8311 absent : les modules charges AVANT lui sont demarres (ReglageGlobal, CONTROLE_DISCOVERY)",
             tasmota.commandes.contains("ReglageGlobal") && classesDrivers().find("CONTROLE_DISCOVERY") != nil)
end

print(string.format("CAS_%i: %s", CAS, echecs == 0 ? "OK" : "ECHEC (" + str(echecs) + ")"))
os.exit(echecs > 250 ? 250 : echecs)
