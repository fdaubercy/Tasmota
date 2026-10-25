# Faux firmware Tasmota pour banc_boot.be (2026-10-23) : tout ce que l'ESP32 fournit au Berry
# et que berry.exe n'a pas. Ce fichier N'EST PAS un module : banc_boot.be le compile et l'execute
# au niveau global (compile(fichier, "file")()), AVANT de charger le moindre fichier de data/.
#
# Il pose les globales suivantes :
#   LITTLEFS       le systeme de fichiers de la carte, EN MEMOIRE (rien n'est ecrit sur le disque du PC) :
#                  fichiers (chemin -> contenu) et dossiers (chemin -> true). Les bouchons 'path' et
#                  'persist' de ce dossier s'y adossent.
#   open(c, m)     remplace le open() de berry.exe (qui ecrirait sur le disque du PC, et "/json/x" = C:\json\x)
#                  par un fichier du LittleFS en memoire. Comme le firmware : io_error si le fichier a lire
#                  n'existe pas, ou si le dossier parent du fichier a ecrire n'existe pas.
#   load(c)        imite tasmota.load (lib/libesp32/berry_tasmota/src/embedded/tasmota_class.be:510) :
#                  .be prefere au .bec, exception ATTRAPEE et imprimee "BRY: failed to run compiled code",
#                  retour false. Chaque echec est garde dans BANC_BOOT.echecsLoad.
#   log(m, n)      le log du firmware : chaque ligne est gardee dans BANC_BOOT.journal ([texte, niveau]).
#   Driver         classe de base des drivers.
#   tasmota        instance de FAUX_TASMOTA (ci-dessous) : memorise regles, commandes, drivers, crons,
#                  minuteries et commandes envoyees ; tasmota.cmd() repond comme le firmware aux commandes
#                  lues au demarrage. Une methode inconnue ne plante pas : elle rend nil et son nom est
#                  garde dans tasmota.inconnus (le banc en fait un controle : toute methode doit etre imitee).
#                  Pour le banc : declenche(evenement) publie un evenement aux regles, avance(ms) fait
#                  avancer l'horloge et execute les minuteries echues, appelle() attrape les exceptions
#                  des rappels (BANC_BOOT.exceptions). Comme le firmware, add_rule/set_timer/add_cron/
#                  add_cmd refusent une METHODE (check_not_method). Reglages du cas : wifiUp, capteurs
#                  (telemetrie SENSOR rendue par read_sensors), i2cAbsents (wire_scan rend nil), mac.
#   udp (ouverture acceptee, envois gardes, rien n'est emis), tcpserver, tcpclientasync, tcpclient, serial,
#                  webclient, Leds, audio : classes natives remplacees
#                  par un OBJET_FACTICE (toute methode rend nil, appels gardes).
import global
import string
import json

# Etat partage du banc (journal, echecs de load) et imitation des modules SOLIDIFIES.
class ETAT_BANC_BOOT
    var journal, echecsLoad, verbeux
    var exceptions              # [quoi, erreur] levees par une regle, une minuterie ou un callback de driver
    var sources                 # dossier des sources (data/fs ou une copie)
    var carte                   # dossier de la carte : source d'un module solidifie absent de data/fs (banc_demarrage)
    var litDisque               # lecture d'un fichier du PC (le open() d'origine, fourni par le banc)
    var ecrisDisque             # ecriture d'un fichier du PC (enveloppes des solidifies seulement)
    var solidifies              # noms des modules solidifies dans le firmware de la carte
    var echecsSolidifies        # [nom, erreur] des modules solidifies qui n'ont pas pu etre construits
    def init() self.exceptions = [] self.journal = [] self.echecsLoad = [] self.verbeux = false self.solidifies = [] self.echecsSolidifies = [] end

    # Module SOLIDIFIE : sur la carte, 'import nom' sert la version en flash, construite a la
    # compilation du firmware par solidify_all.be (lib/libesp32/berry_custom/solidify_all.be:52-86) :
    # le fichier est execute AU NIVEAU GLOBAL, puis la globale 'nom' est figee. Le fichier n'a donc
    # pas besoin de finir par 'return' (controleGeneral.be n'en a pas : importe tel quel, il vaudrait nil).
    # Appele par les enveloppes generees pour chaque module solidifie (voir preparation_boot.be).
    def solidifie(nom)
        import global
        import os
        var chemin = self.sources + "/" + nom + ".be"
        if !os.path.exists(chemin) && self.carte != nil    chemin = self.carte + "/" + nom + ".be"    end   # ex. controleRideau
        var source = self.litDisque(chemin)
        try
            compile(source)()
        except .. as e, m
            self.echecsSolidifies.push([nom, str(e) + " - " + str(m)])
            raise e, m
        end
        return global.(nom)
    end
end
BANC_BOOT = ETAT_BANC_BOOT()

def log(msg, niveau)
    BANC_BOOT.journal.push([str(msg), niveau])
    if BANC_BOOT.verbeux    print("      log" + str(niveau) + " " + str(msg))    end
end

class Driver end

# ------------------------------------------------------------------ LittleFS en memoire
class FS_BANC
    var fichiers, dossiers
    def init() self.fichiers = {} self.dossiers = {"/": true} end
    # "x.json" -> "/x.json" (sur la carte, un chemin relatif part de la racine)
    def normalise(chemin)
        var c = str(chemin)
        if !string.startswith(c, "/")    c = "/" + c    end
        while string.find(c, "//") >= 0    c = string.replace(c, "//", "/")    end
        if size(c) > 1 && string.endswith(c, "/")    c = c[0 .. size(c) - 2]    end
        return c
    end
    def parent(chemin)
        var i = size(chemin) - 1
        while (i > 0 && chemin[i] != "/")    i -= 1    end
        return i == 0 ? "/" : chemin[0 .. i - 1]
    end
    def existe(chemin)
        var c = self.normalise(chemin)
        return self.fichiers.contains(c) || self.dossiers.contains(c)
    end
    def pose(chemin, contenu)            # ecriture directe par le banc (cree les dossiers parents)
        var c = self.normalise(chemin)
        var p = self.parent(c)
        var aCreer = []
        while !self.dossiers.contains(p)    aCreer.push(p)    p = self.parent(p)    end
        for d: aCreer    self.dossiers[d] = true    end
        self.fichiers[c] = contenu
    end
    def liste(dossier)                   # noms des enfants directs, comme path.listdir
        var d = self.normalise(dossier)
        var prefixe = (d == "/" ? "/" : d + "/")
        var noms = []
        for groupe: [self.fichiers, self.dossiers]
            for c: groupe.keys()
                if c != d && string.startswith(c, prefixe)
                    var reste = c[size(prefixe) ..]
                    if string.find(reste, "/") < 0 && noms.find(reste) == nil    noms.push(reste)    end
                end
            end
        end
        return noms
    end
end
LITTLEFS = FS_BANC()

class FICHIER_BANC
    var chemin, contenu, pos, mode
    def init(chemin, mode)
        self.chemin = LITTLEFS.normalise(chemin)
        self.mode = (mode == nil ? "r" : mode)
        self.pos = 0
        var existe = LITTLEFS.fichiers.contains(self.chemin)
        if string.find(self.mode, "r") >= 0 && string.find(self.mode, "+") < 0
            if !existe    raise "io_error", "cannot open file '" + self.chemin + "'"    end
            self.contenu = LITTLEFS.fichiers[self.chemin]
        else
            if !LITTLEFS.dossiers.contains(LITTLEFS.parent(self.chemin))
                raise "io_error", "cannot open file '" + self.chemin + "'"
            end
            self.contenu = (string.find(self.mode, "a") >= 0 && existe) ? LITTLEFS.fichiers[self.chemin] : ""
            if string.find(self.mode, "a") >= 0    self.pos = size(self.contenu)    end
            LITTLEFS.fichiers[self.chemin] = self.contenu
        end
    end
    def read()
        var r = self.contenu[self.pos ..]
        self.pos = size(self.contenu)
        return r
    end
    def readline()
        if self.pos >= size(self.contenu)    return ""    end
        var reste = self.contenu[self.pos ..]
        var i = string.find(reste, "\n")
        var ligne = (i < 0 ? reste : reste[0 .. i])
        self.pos += size(ligne)
        return ligne
    end
    def readbytes(n)
        var r = self.read()
        if n != nil && n < size(r)    r = r[0 .. n - 1]    end
        var b = bytes()
        for i: 0 .. size(r) - 1    b.add(string.byte(r[i]), 1)    end
        return b
    end
    def write(x)
        var t = (isinstance(x, bytes) ? x.asstring() : str(x))
        self.contenu = self.contenu + t
        self.pos = size(self.contenu)
        LITTLEFS.fichiers[self.chemin] = self.contenu
    end
    def size() return size(self.contenu) end
    def tell() return self.pos end
    def seek(p) self.pos = p end
    def flush() end
    def close() end
end
def open(chemin, mode) return FICHIER_BANC(chemin, mode) end

# ------------------------------------------------------------------ load() de tasmota_class.be
def load(nom)
    var c = LITTLEFS.normalise(nom)
    if string.find(c, ".") < 0    c += ".be"    end
    var bec = string.endswith(c, ".bec") ? c : c + "c"
    var source = LITTLEFS.fichiers.find(c)
    if source == nil    source = LITTLEFS.fichiers.find(bec)    end
    if source == nil    return false    end
    var code
    try
        code = compile(source)
    except .. as e, m
        print("BRY: failed to load '" + c + "' (" + str(e) + " - " + str(m) + ")")
        BANC_BOOT.echecsLoad.push([c, str(e) + " - " + str(m)])
        return false
    end
    try
        code()
        return true
    except .. as e, m
        print("BRY: failed to run compiled code (" + str(e) + " - " + str(m) + ")")
        BANC_BOOT.echecsLoad.push([c, str(e) + " - " + str(m)])
    end
    return false
end

# ------------------------------------------------------------------ objets natifs factices
class OBJET_FACTICE
    var _nom, _appels
    def init(nom) self._nom = (nom == nil ? "objet" : nom) self._appels = [] end
    def member(n)
        var s = self
        return def (*a) s._appels.push(n) return nil end
    end
end
# udp : ouverture acceptee, rien a lire ; les envois sont gardes dans 'envois', RIEN ne part sur le reseau
class udp : OBJET_FACTICE
    var remote_ip, remote_port, envois
    def init() super(self).init("udp") self.remote_ip = "" self.remote_port = 0 self.envois = [] end
    def begin(ip, port) return true end
    def begin_multicast(ip, port) return true end
    def read() return nil end
    def send(ip, port, b) self.envois.push([ip, port, b]) return true end
    def send_multicast(b) self.envois.push(["multicast", 0, b]) return true end
    def close() end
end
class tcpserver : OBJET_FACTICE        def init() super(self).init("tcpserver") end end
class tcpclientasync : OBJET_FACTICE   def init() super(self).init("tcpclientasync") end end
class tcpclient : OBJET_FACTICE        def init() super(self).init("tcpclient") end end
class serial : OBJET_FACTICE           def init() super(self).init("serial") end end
class webclient : OBJET_FACTICE        def init() super(self).init("webclient") end end
class Leds : OBJET_FACTICE             def init() super(self).init("Leds") end end
class audio : OBJET_FACTICE            def init() super(self).init("audio") end end

# Bus I2C (Wire) : un peripherique repond toujours (ecriture acceptee, lecture 0)
class FAUX_WIRE : OBJET_FACTICE
    def init() super(self).init("Wire") end
    def write(adresse, registre, valeur, taille) return true end
    def read(adresse, registre, taille) return 0 end
    def read_bytes(adresse, registre, taille) return bytes("00") end
    def detect(adresse) return true end
end

# tasmota.global : variables du firmware (devices_present...), libres en lecture et ecriture
class GLOBAL_FIRMWARE
    var _v
    def init() self._v = {"devices_present": 0} end
    def member(n) return self._v.find(n) end
    def setmember(n, v) self._v[n] = v end
end

# ------------------------------------------------------------------ faux tasmota
class FAUX_TASMOTA
    var global, cmds, reglages, regles, commandes, drivers, crons, timers, inconnus
    var horloge, wifiUp, power, mac, gabarit
    var capteurs                # ce que rend read_sensors() : la telemetrie SENSOR (compteur C1 du garage)
    var i2cAbsents              # adresses I2C sans peripherique : wire_scan rend nil (codec ES8311 absent...)
    def init()
        self.global = GLOBAL_FIRMWARE()
        self.cmds = []  self.reglages = {}  self.regles = []  self.commandes = {}  self.drivers = []
        self.crons = {}  self.timers = []  self.inconnus = []
        self.horloge = 0  self.wifiUp = true  self.power = []  self.mac = "AA:BB:CC:DD:EE:FF"
        self.gabarit = {"NAME": "", "GPIO": [], "FLAG": 0, "BASE": 1}
        self.i2cAbsents = []
        self.capteurs = {"Time": "2026-10-23T00:00:00", "COUNTER": {"C1": 0}}
    end
    def wire_scan(adresse, index) return self.i2cAbsents.find(adresse) != nil ? nil : FAUX_WIRE() end
    # Une methode non imitee : rend nil, nom garde (une fois) dans 'inconnus'
    def member(n)
        if self.inconnus.find(n) == nil    self.inconnus.push(n)    end
        return def (*a) return nil end
    end

    # Comme le firmware (tasmota_class.be:40) : une METHODE passee a add_rule, set_timer, add_cron,
    # add_cmd ou add_fast_loop leve une exception (il faut une fermeture '/ -> obj.methode()').
    def check_not_method(f)
        import introspect
        if type(f) != 'function'    raise "type_error", "BRY: argument must be a function"    end
        if introspect.ismethod(f) == true    raise "type_error", "BRY: method not allowed, use a closure like '/ args -> obj.func(args)'"    end
    end

    # Appelle f(args...) comme le firmware appelle un rappel : une exception est gardee (BANC_BOOT.exceptions)
    # et imprimee, sans arreter le banc
    def appelle(quoi, f, args)
        try
            call(f, args)
            return true
        except .. as e, m
            global.BANC_BOOT.exceptions.push([quoi, str(e) + " - " + str(m)])
            print("BRY: Exception> " + quoi + " : " + str(e) + " - " + str(m))
        end
        return false
    end

    # Publie un evenement aux regles, comme exec_rules/try_rule (tasmota_class.be:196-240) : le
    # declencheur 'A#B' cherche A puis B sans tenir compte de la casse ; la regle recoit
    # (sous-valeur, declencheur, evenement). Les declencheurs a operateur (A#B>3) ne sont pas evalues.
    def declenche(evenement)
        var n = 0
        for r: self.regles.copy()
            var v = evenement
            for morceau: string.split(r[0], "#")
                var cle = nil
                if isinstance(v, map)
                    for k: v.keys()    if string.toupper(k) == string.toupper(morceau)    cle = k    end    end
                end
                if cle == nil    v = nil    break    end
                v = v[cle]
            end
            if v != nil    self.appelle("regle " + r[0], r[1], [v, r[0], evenement])    n += 1    end
        end
        return n
    end

    # Avance l'horloge de 'ms' et execute les minuteries (set_timer) arrivees a echeance
    def avance(ms)
        self.horloge += ms
        var i = 0
        while i < size(self.timers)
            var t = self.timers[i]
            if t[0] <= self.horloge
                self.timers.remove(i)
                self.appelle("minuterie " + str(t[2]), t[1], [])
            else
                i += 1
            end
        end
    end

    # --- regles, commandes, drivers, crons, minuteries : memorises pour les controles du banc
    def add_rule(declencheur, f, id) self.check_not_method(f) self.regles.push([declencheur, f, id]) end
    def remove_rule(declencheur, id)
        var i = 0
        while i < size(self.regles)
            var r = self.regles[i]
            if r[0] == declencheur && (id == nil || r[2] == id)    self.regles.remove(i)    else    i += 1    end
        end
    end
    def regle(id)                        # la fonction de la regle d'identifiant 'id' (nil si absente)
        for r: self.regles    if r[2] == id    return r[1]    end    end
        return nil
    end
    def add_cmd(nom, f) self.check_not_method(f) self.commandes[nom] = f end
    def remove_cmd(nom) self.commandes.remove(nom) end
    def add_driver(d) if self.drivers.find(d) == nil    self.drivers.push(d)    end end
    def remove_driver(d) var i = self.drivers.find(d) if i != nil    self.drivers.remove(i)    end end
    def add_cron(motif, f, id) self.check_not_method(f) self.crons[id] = [motif, f] end
    def remove_cron(id) self.crons.remove(id) end
    def set_timer(ms, f, id) self.check_not_method(f) self.timers.push([self.horloge + ms, f, id]) end
    def remove_timer(id)
        var i = 0
        while i < size(self.timers)    if self.timers[i][2] == id    self.timers.remove(i)    else    i += 1    end    end
    end
    def add_fast_loop(f) self.check_not_method(f) end
    def remove_fast_loop(f) end

    # --- temps, reseau, relais
    def millis(d) return self.horloge + (d == nil ? 0 : d) end
    def time_reached(t) return self.horloge >= t end
    def rtc() return {"local": 1792000000 + self.horloge / 1000, "utc": 1792000000 + self.horloge / 1000, "timezone": 60, "restart": 1792000000} end
    def time_dump(t) return {"year": 2026, "month": 10, "day": 23, "hour": 0, "min": 0, "sec": 0, "weekday": 5} end
    def strftime(fmt, t) return "2026-10-23 00:00:00" end
    def yield() end
    def delay(ms) end
    def wifi() return {"up": self.wifiUp, "ip": "192.168.0.10", "mac": self.mac, "rssi": -50, "quality": 100} end
    def eth() return {"up": false} end
    def is_network_up() return self.wifiUp end
    # Un etat par relai declare (tasmota.global.devices_present, pose par configDevicesByRules), OFF par defaut
    def get_power()
        var n = self.global.devices_present
        while size(self.power) < (n == nil ? 0 : n)    self.power.push(false)    end
        return self.power
    end
    def scale_uint(v, a, b, c, d) return b == a ? c : int((v - a) * (d - c) / (b - a) + c) end
    def scale_int(v, a, b, c, d) return b == a ? c : int((v - a) * (d - c) / (b - a) + c) end
    def set_power(i, v) while size(self.power) <= i    self.power.push(false)    end self.power[i] = v return v end
    def read_sensors() return json.dump(self.capteurs) end
    def publish_rule(s) return false end
    def publish_result(s, topic) end
    def publish(topic, payload) end
    def resp_cmnd(x) end
    def resp_cmnd_done() end
    def resp_cmnd_error() end
    def resp_cmnd_str(x) end
    def loglevel(n) return true end
    def log(m, n) global.log(m, n == nil ? 2 : n) end
    def arch() return "esp32p4" end
    def memory() return {"heap_free": 200, "heap_max": 100, "frag": 10, "psram": 32768, "psram_free": 30000, "flash": 16384, "program": 4096, "program_free": 2048} end
    def gc() return 10000 end
    def get_option(n) return 0 end
    def web_send(s) end
    def web_send_decimal(s) end
    def response_append(s) end
    def hostname() return "SERVEUR-GARAGE" end

    # tasmota.compile : verifie que le .be du LittleFS compile, puis ecrit le .bec (ici : sa source)
    def compile(chemin)
        var c = LITTLEFS.normalise(chemin)
        var source = LITTLEFS.fichiers.find(c)
        if source == nil    print("BRY: failed to load '" + c + "' (io_error - absent)")    return false    end
        try
            compile(source)
        except .. as e, m
            print("BRY: failed to load '" + c + "' (" + str(e) + " - " + str(m) + ")")
            global.BANC_BOOT.echecsLoad.push([c, str(e) + " - " + str(m)])
            return false
        end
        LITTLEFS.fichiers[c + "c"] = source
        return true
    end

    # tasmota.cmd : repond comme le firmware aux commandes lues au demarrage. Lecture (sans argument) :
    # {Nom: valeur memorisee, "" par defaut} ; ecriture : la valeur est memorisee et renvoyee.
    def cmd(commande, muet)
        var c = string.tr(str(commande), "\t", " ")
        self.cmds.push(c)
        var i = string.find(c, " ")
        var nom = (i < 0 ? c : c[0 .. i - 1])
        var arg = (i < 0 ? "" : c[i + 1 ..])
        var bas = string.tolower(nom)
        if bas == "status"
            if arg == "2"    return {"StatusFWR": {"Version": "15.0.1", "BuildDateTime": "2026-10-23T00:00:00"}}    end
            if arg == "5"    return {"StatusNET": {"Hostname": "SERVEUR-GARAGE", "IPAddress": "192.168.0.10", "Mac": self.mac}}    end
            return {"Status": {"Topic": "SERVEUR-GARAGE"}}
        elif bas == "template"
            if arg == ""    return self.gabarit    end
            try self.gabarit = json.load(arg) except .. end
            return self.gabarit
        elif bas == "modules"     return {"Modules": {"0": self.gabarit.find("NAME", ""), "1": "ESP32-P4"}}
        elif bas == "module"      return {"Module": {"0": self.gabarit.find("NAME", "")}}
        elif bas == "grouptopic"  return {"GroupTopic1": self.reglages.find("GroupTopic1", ""), "GroupTopic2": "", "GroupTopic3": ""}
        elif (bas == "timestd" || bas == "timedst") && arg == ""
            return {nom: {"Hemisphere": 0, "Week": 0, "Month": 10, "Day": 1, "Hour": 3, "Offset": 60}}
        elif bas == "ufsftp" && arg == ""    return {"UfsFTP": 0}
        elif bas == "i2cscan"     return {"I2CScan": "Device(s) found at 0x48 0x20"}
        elif string.startswith(bas, "i2cdriver")    return {"I2CDriver": "7,8,9,10,11,12,13,14,15,17,18,20,24,26,29"}
        elif bas == "ledpower" && arg == ""    return {"LedPower1": "OFF"}
        elif (bas == "seriallog" || bas == "syslog") && arg == ""
            var n = str(self.reglages.find(nom, 2))
            return {nom: {n: {"Active": n}}}
        elif bas == "gpios"       return {"GPIOs1": {"0": "None", "32": "Button", "160": "Switch", "224": "Relay", "1376": "WS2812"}}
        elif ["rgxssid", "rgxpassword", "rgxaddress", "rgxsubnet"].find(bas) != nil    # ResponseRgxConfig (xdrv_58)
            if arg != ""    self.reglages[nom] = arg    end
            return {"Rgx": {"Valid": "true", "SSId": self.reglages.find("RgxSSId", ""), "Password": self.reglages.find("RgxPassword", ""),
                            "IPAddress": self.reglages.find("RgxAddress", "0.0.0.0"), "Subnetmask": self.reglages.find("RgxSubnet", "0.0.0.0")}}
        elif bas == "rgxclients"  return {"RgxClients": {}}
        elif bas == "backlog"     return {}
        elif bas == "restart"     return {"Restart": "Restarting"}
        end
        if arg == ""    return {nom: self.reglages.find(nom, "")}    end
        self.reglages[nom] = arg
        return {nom: arg}
    end

    # Commandes envoyees dont le texte commence par 'debut'
    def envoyees(debut)
        var r = []
        for c: self.cmds    if string.find(c, debut) == 0    r.push(c)    end    end
        return r
    end
end
tasmota = FAUX_TASMOTA()
