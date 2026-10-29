# Reception de fichiers du FS par MQTT (« MQTT pousse », A16 de la page Build 7700 ; protocole : choix 25 a 27 de
# docs/superpowers/specs/2026-10-24-page-build-televersement-design.md). NON solidifie : charge par l'autoexec
# (demarrage.charge(["fsMqtt"])) des cartes ou l'utilisateur l'a voulu.
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
import mqtt
import json

var fsMqtt = module("fsMqtt")
fsMqtt.VERSION = 1
fsMqtt.TEMP = "/fsmqtt.tmp"
fsMqtt.MORCEAU = 1900                    # MQTT_MAX_PACKET_SIZE 2048 - en-tete - topic (essai A14)
fsMqtt.TAILLE_MAX = 1048576
fsMqtt.LONGUEUR_MAX = 49                 # UFS_FILENAME_SIZE - 1 de Tasmota
fsMqtt.LOT = 20                          # entrees supprimees par rappel (efface) : jamais un long blocage
fsMqtt.LOT_LU = 4                        # morceaux publies par rappel (lit) : un publish peut attendre derriere le NAPT

class FsMqttRecepteur
    var base, transfert, efface, lecture

    def init(topic)
        self.base = "fsmqtt/" + topic + "/"
        self.transfert = nil              # {id, chemin, taille, md5, recus, hache}
        self.efface = nil                 # {id, fichiers, dossiers, n_fichiers, n_dossiers}
        self.lecture = nil                # {id, chemin, f, hache, position}
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
        mqtt.publish(self.base + "etat", json.dump(r))
    end

    def refuse(id, op, erreur)
        self.log("FS_MQTT: " + op + " refusé : " + erreur + " !", LOG_LEVEL_ERREUR)
        self.repond(id, op, false, {"erreur": erreur})
    end

    def pret()
        mqtt.publish(self.base + "etat", json.dump({"op": "pret", "version": fsMqtt.VERSION}))
    end

    # Chemin du FS accepte : absolu, sans "..", court, pas le fichier temporaire. /sd/... est un dossier du LittleFS
    # (be_port.cpp n'ecrit que sur ffsp, la flash), celui de l'image : accepte comme les autres
    def chemin_valide(c)
        import string
        return type(c) == "string" && size(c) > 1 && size(c) <= fsMqtt.LONGUEUR_MAX && c[0] == "/" && c[-1] != "/" &&
               string.find(c, "..") < 0 && c != fsMqtt.TEMP
    end

    def ordre(s)
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
            elif op == "efface"      self.commence_efface(id)
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
        if type(taille) != "int" || taille < 0 || taille > fsMqtt.TAILLE_MAX
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
        var f = open(fsMqtt.TEMP, "w")
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
                    f = open(fsMqtt.TEMP, "a")
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
        if !path.rename(fsMqtt.TEMP, t["chemin"])
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
        if path.exists(fsMqtt.TEMP)    path.remove(fsMqtt.TEMP)    end
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
        var l = self.lecture
        var fini = false
        try
            var k = 0
            while k < fsMqtt.LOT_LU && !fini
                var d = l["f"].readbytes(fsMqtt.MORCEAU - 4)
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

    # Effacement TOTAL du LittleFS (/sd compris : dossier de la flash) : inventaire d'un coup, suppression par lots
    def commence_efface(id)
        import path
        if self.efface != nil    return self.refuse(id, "efface", "effacement déjà en cours")    end
        self.abandonne()
        var fichiers = []
        var dossiers = []
        var a_voir = ["/"]
        while size(a_voir) > 0
            var d = a_voir.pop()
            for nom: path.listdir(d)
                var c = (d == "/" ? "/" : d + "/") + nom
                if path.isdir(c)    dossiers.push(c)  a_voir.push(c)    else    fichiers.push(c)    end
            end
        end
        self.efface = {"id": id, "fichiers": fichiers, "dossiers": dossiers, "n_fichiers": size(fichiers),
                       "n_dossiers": size(dossiers)}
        self.log("FS_MQTT: effacement du FS : " + str(size(fichiers)) + " fichiers, " + str(size(dossiers)) + " dossiers", LOG_LEVEL_DEBUG)
        self.lot_efface()
    end

    def lot_efface()
        import path
        var x = self.efface
        var restants = 0
        try
            var n = 0
            while n < fsMqtt.LOT && size(x["fichiers"]) > 0
                path.remove(x["fichiers"].pop())
                n += 1
            end
            while n < fsMqtt.LOT && size(x["fichiers"]) == 0 && size(x["dossiers"]) > 0
                path.rmdir(x["dossiers"].pop())      # les plus profonds d'abord (ajoutes apres leur parent)
                n += 1
            end
            restants = size(x["fichiers"]) + size(x["dossiers"])
        except .. as e, m
            self.efface = nil
            self.log("FS_MQTT_ERREUR: efface : " + str(e) + " - " + str(m) + " !", LOG_LEVEL_ERREUR)
            self.repond(x["id"], "efface", false, {"erreur": str(e) + " - " + str(m)})
            return
        end
        if restants > 0
            mqtt.publish(self.base + "etat", json.dump({"id": x["id"], "op": "efface", "ok": true, "restants": restants}))
            tasmota.set_timer(0, /-> self.lot_efface(), "fsmqtt_efface")
            return
        end
        self.efface = nil
        self.repond(x["id"], "efface", true, {"restants": 0, "fichiers": x["n_fichiers"], "dossiers": x["n_dossiers"]})
    end
end

# Demarrage : topic du persist ; sans topic, rien n'est abonne (erreur dite)
def fsMqtt_demarre()
    import persist
    var topic = persist.find("serveur", {}).find("mqtt", {}).find("topic")
    if type(topic) != "string" || size(topic) == 0
        import logFonctions
        logFonctions.log("FS_MQTT_ERREUR: pas de serveur.mqtt.topic dans le persist : réception MQTT inactive !", LOG_LEVEL_ERREUR)
        return nil
    end
    return FsMqttRecepteur(topic)
end
fsMqtt.demarre = fsMqtt_demarre
fsMqtt.recepteur = fsMqtt.demarre()

return fsMqtt
