# Reception de fichiers du FS par MQTT (« MQTT pousse », A16 de la page Build 7700 ; protocole : choix 25 a 27 de
# docs/superpowers/specs/2026-10-24-page-build-televersement-design.md). SOLIDIFIE dans le socle (berry_commun.socle,
# toutes les cartes, decision du 2026-10-29) : il survit au formatage du FS. Charge par demarrage.charge(["fsMqtt"])
# dans l'autoexec : 'import' appelle fsMqtt_init(m), en pied de fichier.
#
# Topics, sous le topic MQTT du persist (serveur.mqtt.topic) :
#   fsmqtt/<topic>/ordre    (PC -> carte) JSON {"op", "id", ...}
#   fsmqtt/<topic>/morceau  (PC -> carte) 4 octets de position (gros-boutiste) + donnees
#   fsmqtt/<topic>/etat     (carte -> PC) JSON {"id", "op", "ok", ...}
#   fsmqtt/<topic>/lu       (carte -> PC) 4 octets de position + donnees (ordre "lit")
# Ordres : debut {chemin, taille, md5}, fin, abandon, lit {chemin}, recharge, berry, redemarre, efface.
# Un fichier recu s'ecrit dans /fsmqtt.tmp et ne remplace le vrai qu'apres controle de la taille et du MD5.
# Au chargement, et a chaque connexion MQTT : {"op": "pret"} sur .../etat.
# Logs : cible "general" (pas de bloc fsmqtt dans logFonctions) ; rappels de reception -> debug/detail
# seulement (charte, regle 4).
# Solidifiable : aucun import ni appel tasmota au niveau fichier (piege 2), constantes en membres statiques de la
# classe et instance hors du module (la table d'un module solidifie est constante, piege 12).
#@ solidify:fsMqtt
var fsMqtt = module("fsMqtt")

class FsMqttRecepteur
    static VERSION = 2                   # 2 : efface = formatage (path.format)
    static TEMP = "/fsmqtt.tmp"
    static MORCEAU = 1900                # MQTT_MAX_PACKET_SIZE 2048 - en-tete - topic (essai A14)
    static TAILLE_MAX = 1048576
    static LONGUEUR_MAX = 49             # UFS_FILENAME_SIZE - 1 de Tasmota
    static LOT_LU = 4                    # morceaux publies par rappel (lit) : un publish peut attendre derriere le NAPT
    var base, transfert, lecture

    def init(topic)
        self.base = "fsmqtt/" + topic + "/"
        self.transfert = nil              # {id, chemin, taille, md5, recus, hache}
        self.lecture = nil                # {id, chemin, f, hache, position}
        import mqtt
        mqtt.subscribe(self.base + "ordre", /t, i, s, b -> self.ordre(s))
        mqtt.subscribe(self.base + "morceau", /t, i, s, b -> self.morceau(b))
        tasmota.add_rule("Mqtt#Connected", /-> self.pret(), "fsmqtt_pret")
        if mqtt.connected()    self.pret()    end
    end

    def log(msg, niveau)
        import logFonctions
        logFonctions.log(msg, niveau)
    end

    def repond(id, op, ok, autres)
        var r = autres != nil ? autres : {}
        r["id"] = id
        r["op"] = op
        r["ok"] = ok
        import mqtt
        import json
        mqtt.publish(self.base + "etat", json.dump(r))
    end

    def refuse(id, op, erreur)
        self.log("FS_MQTT: " + op + " refusé : " + erreur + " !", LOG_LEVEL_ERREUR)
        self.repond(id, op, false, {"erreur": erreur})
    end

    def pret()
        import mqtt
        import json
        mqtt.publish(self.base + "etat", json.dump({"op": "pret", "version": self.VERSION}))
    end

    # Chemin du FS accepte : absolu, sans "..", court, pas le fichier temporaire. /sd/... est un dossier du LittleFS
    # (be_port.cpp n'ecrit que sur ffsp, la flash), celui de l'image : accepte comme les autres
    def chemin_valide(c)
        import string
        return type(c) == "string" && size(c) > 1 && size(c) <= self.LONGUEUR_MAX && c[0] == "/" && c[-1] != "/" &&
               string.find(c, "..") < 0 && c != self.TEMP
    end

    def ordre(s)
        import json
        var o = json.load(s)
        if !isinstance(o, map) || type(o.find("op")) != "string"
            self.log("FS_MQTT: ordre illisible : " + str(s) + " !", LOG_LEVEL_ERREUR)
            return true
        end
        var op = o["op"]
        var id = o.find("id")
        import logFonctions
        if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS)    self.log("FS_MQTT: ordre " + s, LOG_LEVEL_DEBUG_PLUS)    end
        try
            if   op == "debut"       self.debut(id, o)
            elif op == "fin"         self.fin(id)
            elif op == "abandon"     self.abandonne()  self.repond(id, op, true)
            elif op == "lit"         self.lit(id, o.find("chemin"))
            elif op == "recharge"    self.recharge(id)
            elif op == "berry"       self.repond(id, op, true)  tasmota.cmd("Backlog BrRestart")   # hors de la VM
            elif op == "redemarre"   self.repond(id, op, true)  tasmota.cmd("Backlog Restart 1")
            elif op == "efface"      self.efface(id)
            else                     self.refuse(id, op, "ordre inconnu")
            end
        except .. as e, m
            self.log("FS_MQTT_ERREUR: " + op + " : " + str(e) + " - " + str(m) + " !", LOG_LEVEL_ERREUR)
            self.repond(id, op, false, {"erreur": str(e) + " - " + str(m)})
        end
        return true
    end

    def debut(id, o)
        import path
        if self.transfert != nil    self.abandonne()    end         # un seul transfert a la fois
        var c = o.find("chemin")
        var taille = o.find("taille")
        if !self.chemin_valide(c)    return self.refuse(id, "debut", "chemin refusé : " + str(c))    end
        if type(taille) != "int" || taille < 0 || taille > self.TAILLE_MAX
            return self.refuse(id, "debut", "taille refusée : " + str(taille))
        end
        if type(o.find("md5")) != "string"    return self.refuse(id, "debut", "md5 absent")    end
        if path.isdir(c)    return self.refuse(id, "debut", "chemin d'un dossier : " + c)    end
        # dossiers du chemin, du plus haut au plus bas
        import string
        var i = string.find(c, "/", 1)
        while i > 0
            var d = c[0 .. i - 1]
            if !path.exists(d)    path.mkdir(d)    end
            if !path.isdir(d)    return self.refuse(id, "debut", "dossier impossible : " + d)    end
            i = string.find(c, "/", i + 1)
        end
        var f = open(self.TEMP, "w")
        f.close()
        import crypto
        self.transfert = {"id": id, "chemin": c, "taille": taille, "md5": string.tolower(o["md5"]), "recus": 0,
                          "hache": crypto.MD5()}
        self.log("FS_MQTT: réception de " + c + " (" + str(taille) + " o)", LOG_LEVEL_DEBUG)
        self.repond(id, "debut", true)
    end

    # Morceau = position (4 octets, gros-boutiste) + donnees. Seul celui attendu est ecrit ; l'accuse est le cumul.
    # Payload vide : le firmware ne passe pas payload_b (nil).
    def morceau(b)
        var t = self.transfert
        if t == nil || b == nil || size(b) < 4    return true    end
        var erreur = nil
        var f = nil
        try
            var position = b.get(0, -4)
            if position == t["recus"] && size(b) > 4
                var donnees = b[4 ..]
                if t["recus"] + size(donnees) > t["taille"]
                    erreur = "plus de données que la taille annoncée"
                else
                    f = open(self.TEMP, "a")
                    f.write(donnees)
                    f.close()
                    f = nil
                    t["hache"].update(donnees)
                    t["recus"] += size(donnees)
                end
            end
        except .. as e, m
            if f != nil    try f.close() except .. end    end
            erreur = "écriture impossible : " + str(e) + " - " + str(m)
        end
        if erreur != nil
            self.abandonne()
            self.refuse(t["id"], "morceau", erreur)
            return true
        end
        import mqtt
        import json
        mqtt.publish(self.base + "etat", json.dump({"id": t["id"], "op": "morceau", "ok": true, "octets": t["recus"]}))
        return true
    end

    def fin(id)
        import path
        var t = self.transfert
        if t == nil    return self.refuse(id, "fin", "aucun transfert en cours")    end
        import string
        var md5 = string.tolower(t["hache"].finish().tohex())     # comme hexdigest() du PC
        if t["recus"] != t["taille"]
            self.abandonne()
            return self.refuse(id, "fin", "reçu " + str(t["recus"]) + " o sur " + str(t["taille"]))
        end
        if md5 != t["md5"]
            self.abandonne()
            return self.refuse(id, "fin", "MD5 différent (reçu " + md5 + ")")
        end
        if path.exists(t["chemin"])    path.remove(t["chemin"])    end
        if !path.rename(self.TEMP, t["chemin"])
            self.abandonne()
            return self.refuse(id, "fin", "renommage impossible vers " + t["chemin"])
        end
        self.transfert = nil
        self.log("FS_MQTT: " + t["chemin"] + " écrit (" + str(t["recus"]) + " o)", LOG_LEVEL_DEBUG)
        self.repond(id, "fin", true, {"chemin": t["chemin"], "octets": t["recus"]})
    end

    def abandonne()
        import path
        self.transfert = nil
        if path.exists(self.TEMP)    path.remove(self.TEMP)    end
    end

    # Renvoie le fichier sur .../lu, par morceaux (position + donnees), LOT_LU par rappel, puis taille et MD5 sur .../etat
    def lit(id, c)
        import path
        import crypto
        if self.lecture != nil    return self.refuse(id, "lit", "lecture déjà en cours")    end
        if !self.chemin_valide(c) || !path.exists(c) || path.isdir(c)
            return self.refuse(id, "lit", "fichier absent : " + str(c))
        end
        self.lecture = {"id": id, "chemin": c, "f": open(c, "r"), "hache": crypto.MD5(), "position": 0}
        self.lot_lit()
    end

    def lot_lit()
        import string
        import mqtt
        var l = self.lecture
        var fini = false
        try
            var k = 0
            while k < self.LOT_LU && !fini
                var d = l["f"].readbytes(self.MORCEAU - 4)
                if size(d) == 0
                    fini = true
                else
                    var m = bytes()
                    m.add(l["position"], -4)
                    mqtt.publish(self.base + "lu", m + d)
                    l["hache"].update(d)
                    l["position"] += size(d)
                end
                k += 1
            end
        except .. as e, m
            try l["f"].close() except .. end
            self.lecture = nil
            self.log("FS_MQTT_ERREUR: lit " + l["chemin"] + " : " + str(e) + " - " + str(m) + " !", LOG_LEVEL_ERREUR)
            self.repond(l["id"], "lit", false, {"erreur": str(e) + " - " + str(m)})
            return
        end
        if !fini
            tasmota.set_timer(0, /-> self.lot_lit(), "fsmqtt_lit")
            return
        end
        l["f"].close()
        self.lecture = nil
        self.repond(l["id"], "lit", true, {"chemin": l["chemin"], "octets": l["position"],
                                           "md5": string.tolower(l["hache"].finish().tohex())})
    end

    # Comme BR_RECHARGE (build_ota_fs.py) : le persist relu remplace celui en RAM, sinon le System#Save d'un
    # redemarrage reecrirait l'ancien par-dessus le nouveau
    def recharge(id)
        import persist
        import global
        persist.load()
        for c: ["serveur", "diverses", "modules", "drivers"]    global.setmember(c, persist.find(c))    end
        self.repond(id, "recharge", true)
    end

    # Effacement TOTAL du LittleFS (/sd compris : dossier de la flash) par formatage (decision du 2026-10-29).
    # path.format(true) = LittleFS.format(), BLOQUANT : il ne coupe que le watchdog du coeur 0 ; celui de la boucle
    # (USE_ESP32_WDT, 5 s) redemarre la carte si le formatage dure plus -> FS vide, a reprendre en HTTP ou par cable.
    # Le module, solidifie, survit ; l'autoexec non : le PC envoie toute l'image juste apres.
    def efface(id)
        import path
        if self.lecture != nil    return self.refuse(id, "efface", "lecture en cours")    end
        self.abandonne()
        self.log("FS_MQTT: formatage du FS", LOG_LEVEL_DEBUG)
        if !path.format(true)    return self.refuse(id, "efface", "formatage refusé par le firmware")    end
        self.repond(id, "efface", true)
    end
end

fsMqtt.FsMqttRecepteur = FsMqttRecepteur

# init() : APPELEE AUTOMATIQUEMENT par 'import fsMqtt' (be_module.c::module_init), une fois par session Berry.
# Abonnements sous le topic du persist ; sans topic, rien n'est abonne (erreur dite). L'instance vit par ses
# rappels MQTT et dans global.fsMqttRecepteur (pas dans le module : sa table est constante une fois solidifie).
def fsMqtt_init(m)
    import global
    import persist
    import logFonctions
    var topic = persist.find("serveur", {}).find("mqtt", {}).find("topic")
    if type(topic) != "string" || size(topic) == 0
        logFonctions.log("FS_MQTT_ERREUR: pas de serveur.mqtt.topic dans le persist : réception MQTT inactive !", LOG_LEVEL_ERREUR)
        return m
    end
    global.fsMqttRecepteur = m.FsMqttRecepteur(topic)
    return m
end
fsMqtt.init = fsMqtt_init

# Rend le module a son import depuis le LittleFS (carte au firmware sans fsMqtt solidifie, piege 13)
return fsMqtt
