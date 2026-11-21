# Driver de la voie MQTT maitre/esclaves (plan tasks/plans/voie-mqtt.md, A4). SEUL LE MAITRE le charge : un esclave
# Tasmota natif (projecteur, pompe, cuve) n'embarque rien pour cette voie. Il s'abonne aux retours (stat/<topic>/+ et
# tele/<topic>/LWT) des esclaves DECLARES dans drivers.liaisonMqtt.esclaves du persist (pas de joker sur tout le broker :
# les etats du module ne grossissent qu'avec les elements declares), les passe aux garde-fous de mqttLiaisonFonctions
# et emet les ordres cmnd/<topic>/<commande> apres accord de ces garde-fous.
#   ordonne(esclave, commande, valeur) -> "envoyer" | "identique" | "attente" | "quarantaine" | "coupe" | "invalide" | "inconnu" | "hors_ligne"
# Commandes PERMISES (liste blanche, COMMANDES) : Power, Power<n>, Dimmer, CT. Ce sont des commandes a ETAT, dont l'esclave
# renvoie la valeur (accuse attendu par les garde-fous). Restart, Backlog, Br, TOGGLE... sont refusees : non idempotentes
# ou sans retour d'etat (elles seraient renvoyees jusqu'a ESSAIS_MAX), et le maitre ne doit pas devenir un relais d'elevation
# vers des esclaves qui n'ont pas ses protections. Valeurs normalisees : ON/OFF (1, 0, true, false acceptes), entiers.
# Les retours « evenement » (changement fait par l'esclave) sont signales au niveau debug ; leur exploitation (elements
# virtuels, boutons) vient aux etapes A5 et A6. Le temps passe aux garde-fous est tasmota.millis() (comparaison par difference).
# Garde d'activation en pied de fichier (seule vraie desactivation) : drivers.liaisonMqtt.activation == "ON".
# Solidifiable : aucun import ni appel tasmota au niveau fichier ; la classe est portee par le module.
#@ solidify:controleMqttLiaison
var controleMqttLiaison = module("controleMqttLiaison")

class CONTROLE_MQTT_LIAISON : Driver
    static COMMANDES = {"POWER": 1, "DIMMER": 1, "CT": 1}
    static RENVOIS_PAR_PASSAGE = 5        # publish par seconde au plus : un publish lent bloque loop() (chien de garde 5 s)
    var esclaves          # nom -> topic Tasmota de l'esclave (declares et actifs)
    var par_topic         # topic -> nom
    var en_ligne          # nom -> true / false (LWT)
    var ligne             # ligne d'alerte de l'accueil (broker injoignable), vide sinon
    var resync            # topics dont l'etat reel est a relire apres le retour du broker
    var liens             # nom -> [[module, famille, cle, chemin]] des elements virtuels MQTT_<nom> (construit au 1er SENSOR)
    var affiches          # nom -> [[libelle, module, famille, cle]] des elements MQTT_<nom> ACTIFS, relais compris (lignes « perime »)
    var relais_lies       # "nom/POWERn" -> [id] des relais actifs du maitre qui commandent cet etat (recalage)

    def init()
        import persist
        import mqtt
        import mqttLiaisonFonctions         # cree global.mqttLiaisonGarde
        self.esclaves = {}
        self.par_topic = {}
        self.en_ligne = {}
        self.ligne = ""
        self.resync = []
        var liste = persist.find("drivers", {}).find("liaisonMqtt", {}).find("esclaves", {})
        for nom: liste.keys()
            var e = liste[nom]
            if type(e) != "instance"    continue    end
            var topic = e.find("topic")
            if e.find("activation", "OFF") != "ON"    continue    end
            if !self.declaration_valide(nom, topic)    continue    end
            self.esclaves[nom] = topic
            self.par_topic[topic] = nom
            mqtt.subscribe("stat/" + topic + "/+", /t, i, s, b -> self.recu(t, s))
            mqtt.subscribe("tele/" + topic + "/LWT", /t, i, s, b -> self.recu(t, s))
            mqtt.subscribe("tele/" + topic + "/SENSOR", /t, i, s, b -> self.recu(t, s))
        end
        mqttLiaisonFonctions.log("LIAISON_MQTT: " + str(size(self.esclaves)) + " esclave(s) déclaré(s) !", LOG_LEVEL_INFO)
        tasmota.add_cmd("ReglageMqttLiaison", / cmd, idx, payload, payload_json -> mqttLiaisonFonctions.reglage(cmd, idx, payload, payload_json))
    end

    # Nom sans « / » (la cle interne est nom/COMMANDE), topic texte non vide sans joker (+ #) et pas deja pris
    def declaration_valide(nom, topic)
        import string
        import mqttLiaisonFonctions
        var raison = nil
        if type(nom) != "string" || size(nom) == 0 || string.find(nom, "/") >= 0    raison = "nom invalide"
        elif type(topic) != "string" || size(topic) == 0                            raison = "topic absent"
        elif string.find(topic, "+") >= 0 || string.find(topic, "#") >= 0           raison = "topic avec joker"
        elif self.par_topic.contains(topic)                                         raison = "topic déjà déclaré par " + str(self.par_topic[topic])
        end
        if raison != nil
            mqttLiaisonFonctions.log("LIAISON_MQTT_ERREUR: esclave " + str(nom) + " ignoré, " + raison + " !", LOG_LEVEL_ERREUR)
            return false
        end
        return true
    end

    # Entier positif de 1 a 4 chiffres
    def chiffres(v)
        if size(v) == 0 || size(v) > 4    return false    end
        for i: 0 .. size(v) - 1
            if v[i] < "0" || v[i] > "9"    return false    end
        end
        return true
    end

    # Commande permise et valeur normalisees : [COMMANDE majuscules avec indice, valeur] ou nil
    def normalise(commande, valeur)
        import string
        if type(commande) != "string" || valeur == nil    return nil    end
        var c = string.toupper(commande)
        var n = size(c)
        while n > 0 && c[n - 1] >= "0" && c[n - 1] <= "9"    n -= 1    end
        var base = n > 0 ? c[0 .. n - 1] : ""
        var indice = n < size(c) ? c[n ..] : ""
        if !self.COMMANDES.contains(base)    return nil    end
        var v = string.tolower(str(valeur))
        if base == "POWER"
            if indice == ""    c = "POWER1"    end                         # un esclave a un seul relais repond POWER
            if indice == "0"    return nil    end
            if v == "on" || v == "1" || v == "true"        v = "ON"
            elif v == "off" || v == "0" || v == "false"    v = "OFF"
            else    return nil
            end
        else
            if indice != "" || !self.chiffres(v)    return nil    end
            v = str(int(v))
        end
        return [c, v]
    end

    # Reseau et broker prets ? Rien n'est emis avant (une socket creee avant la pile TCP/IP a deja plante une carte)
    def peut_emettre()
        import mqtt
        return tasmota.is_network_up() && mqtt.connected()
    end

    # Tout message stat/ ou tele/ recu par le maitre est l'etat d'un autre appareil, jamais une commande pour lui :
    # rendre true empeche Tasmota de le rejouer comme commande (stat/<esclave>/POWER ON -> POWER ON sur le maitre).
    # Couvre aussi un abonnement orphelin : BrRestart (xdrv_52_9_berry.ino::BerryInit) ne desabonne pas du broker,
    # les messages d'un esclave retire du persist arrivent encore sans abonne Berry. Les autres drivers recoivent
    # quand meme le message (tasmota_class.be::event poursuit la distribution de mqtt_data).
    def mqtt_data(topic, idx, data, databytes)
        import string
        return string.find(topic, "stat/") == 0 || string.find(topic, "tele/") == 0
    end

    # Retour d'un esclave : stat/<topic>/RESULT, stat/<topic>/POWERn ou tele/<topic>/LWT
    def recu(topic, s)
        import string
        var p = string.split(topic, "/")
        if size(p) < 3    return false    end
        var suffixe = p[-1]
        var tp = p[1]
        for k: 2 .. size(p) - 2    tp = tp + "/" + p[k]    end
        var nom = self.par_topic.find(tp)
        if nom == nil    return false    end
        if suffixe == "LWT"
            self.en_ligne[nom] = (s == "Online")
            import mqttLiaisonFonctions
            mqttLiaisonFonctions.log("LIAISON_MQTT: " + nom + " " + str(s) + " !", LOG_LEVEL_DEBUG)
        elif suffixe == "RESULT"
            self.resultat(nom, s)
        elif suffixe == "SENSOR"
            self.mesures(nom, s)
        elif string.find(suffixe, "POWER") == 0
            self.etat(nom, suffixe, s)
        end
        return true                 # traite : sinon Tasmota execute stat/<esclave>/POWER ON comme une commande du maitre (essai A6 du 2026-11-20)
    end

    # Elements virtuels « MQTT_<nom> » (thermometres, analogiques, compteurs) du persist, avec la cle « mqtt.chemin » du JSON SENSOR
    # (ex. « DS18B20.Temperature », « ANALOG.A1 »). Le chemin, points remplaces par #, sert de declencheur a
    # globalFonctions.changementEtatCapteur, qui choisit la famille d'apres son texte (DS18B20, AM2301#, ANALOG#A, COUNTER#C).
    def construit()
        import persist
        import string
        self.liens = {}
        self.affiches = {}
        self.relais_lies = {}
        var mods = persist.find("modules", {})
        for m: mods.keys()
            if type(mods[m]) != "instance"    continue    end
            var env = mods[m].find("environnement", {})
            if type(env) != "instance"    continue    end
            for fam: ["thermometres", "analogiques", "compteurs", "boutons", "capteurs", "interrupteurs", "relais"]
                var l = env.find(fam, {})
                if type(l) != "instance"    continue    end
                for cle: l.keys()
                    var d = l[cle]
                    if type(d) != "instance"    continue    end
                    var v = d.find("virtuel", "OFF")
                    var mq = d.find("mqtt")
                    var chemin = isinstance(mq, map) ? mq.find("chemin") : nil
                    var decl = isinstance(mq, map) ? mq.find("declencheur") : nil
                    if type(v) != "string" || string.find(v, "MQTT_") != 0    continue    end
                    var nom = v[5 ..]
                    if !self.esclaves.contains(nom)    continue    end
                    if d.find("activation") == "ON"                             # absente = inactif
                        if !self.affiches.contains(nom)    self.affiches[nom] = []    end
                        self.affiches[nom].push([str(d.find("nom", cle)), m, fam, cle])
                        var o = fam == "relais" && type(d.find("id")) == "int" ? self.normalise(isinstance(mq, map) ? mq.find("commande", "Power1") : "Power1", "ON") : nil
                        if o != nil
                            var k = nom + "/" + o[0]
                            if !self.relais_lies.contains(k)    self.relais_lies[k] = []    end
                            self.relais_lies[k].push(d["id"])
                        end
                    end
                    if type(chemin) != "string"    continue    end              # relais : ordres seulement, pas de SENSOR
                    if !self.liens.contains(nom)    self.liens[nom] = []    end
                    self.liens[nom].push([m, fam, cle, chemin, type(decl) == "string" ? decl : string.replace(chemin, ".", "#")])
                end
            end
        end
    end

    # tele/<topic>/SENSOR : un JSON mal forme est rejete (erreur), une valeur absente est ignoree
    def mesures(nom, s)
        import json
        import string
        import mqttLiaisonFonctions
        if self.liens == nil    self.construit()    end
        var l = self.liens.find(nom)
        if l == nil    return    end
        var r = json.load(s)
        if !isinstance(r, map)
            mqttLiaisonFonctions.log("LIAISON_MQTT_ERREUR: SENSOR de " + nom + " mal formé, rejeté !", LOG_LEVEL_ERREUR)
            return
        end
        for e: l
            var v = r
            for p: string.split(e[3], ".")
                v = isinstance(v, map) ? v.find(p) : nil
            end
            if v == nil || type(v) == "instance"    continue    end
            try
                import globalFonctions
                globalFonctions.changementEtatCapteur(v, e[4], r, e[0], e[2])
            except .. as erreur, message
                mqttLiaisonFonctions.log("LIAISON_MQTT_ERREUR: " + nom + "/" + e[3] + " : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
            end
        end
    end

    # Bouton ou interrupteur de l'esclave (detache de son relais, SetOption73/114) : stat/<topic>/RESULT {"Button1":{"Action":"SINGLE"}}.
    # L'element virtuel du maitre dont mqtt.chemin vaut cette cle recoit l'action, comme un bouton reel (relais lies du maitre).
    def evenement(nom, cle, v)
        import mqttLiaisonFonctions
        if self.liens == nil    self.construit()    end
        var action = v.find("Action")
        if type(action) != "string"    return    end
        for e: self.liens.find(nom, [])
            if e[3] != cle || (e[1] != "boutons" && e[1] != "capteurs" && e[1] != "interrupteurs")    continue    end
            try
                import globalFonctions
                globalFonctions.changementEtatCapteur(action, cle, v, e[0], e[2])
            except .. as erreur, message
                mqttLiaisonFonctions.log("LIAISON_MQTT_ERREUR: " + nom + "/" + cle + " : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
            end
        end
    end

    def resultat(nom, s)
        import json
        var r = json.load(s)
        if !isinstance(r, map)    return    end
        for k: r.keys()
            var v = r[k]
            if v != nil && type(v) != "instance"    self.etat(nom, k, v)
            elif isinstance(v, map)                 self.evenement(nom, k, v)    end      # Button1 / Switch1 : {"Action": ...}
        end
    end

    def etat(nom, element, valeur)
        import global
        import string
        import mqttLiaisonFonctions
        import logFonctions
        var g = global.mqttLiaisonGarde
        if g == nil    return    end
        var e = string.toupper(element)
        if e == "POWER"    e = "POWER1"    end                             # esclave a un seul relais
        var cle = nom + "/" + e
        var code = g.recoit(cle, valeur, tasmota.millis())
        if code == "evenement" && logFonctions.actif(LOG_LEVEL_DEBUG, "liaisonMqtt")
            mqttLiaisonFonctions.log("LIAISON_MQTT: " + cle + " = " + str(valeur) + " (évènement) !", LOG_LEVEL_DEBUG)
        end
        if code != "invalide" && !g.attente.contains(cle)    self.recale(cle, str(valeur))    end
    end

    # Relais du maitre lies a cet etat remis sur l'etat REEL de l'esclave (appui sur son bouton local, redemarrage) : sinon
    # le bouton du maitre affiche un etat faux. set_power relance set_power_handler, dont l'ordre est refuse « identique »
    # par G3 (etat connu et frais) : rien n'est renvoye. Jamais pendant un ordre en attente (appel ci-dessus) : un etat
    # ancien relancerait l'ordre inverse et annulerait celui de l'utilisateur.
    def recale(cle, valeur)
        if valeur != "ON" && valeur != "OFF"    return    end
        if self.liens == nil    self.construit()    end
        var on = (valeur == "ON")
        var p = tasmota.get_power()
        for id: self.relais_lies.find(cle, [])
            if id >= 1 && id <= size(p) && p[id - 1] != on    tasmota.set_power(id - 1, on)    end
        end
    end

    def ordonne(nom, commande, valeur)
        import mqtt
        import global
        import mqttLiaisonFonctions
        import logFonctions
        var topic = self.esclaves.find(nom)
        var g = global.mqttLiaisonGarde
        if topic == nil || g == nil    return "inconnu"    end
        var o = self.normalise(commande, valeur)
        if o == nil
            mqttLiaisonFonctions.log("LIAISON_MQTT_ERREUR: ordre " + nom + " " + str(commande) + " " + str(valeur) + " refusé, commande ou valeur non permise !", LOG_LEVEL_ERREUR)
            return "invalide"
        end
        if self.en_ligne.find(nom) == false || !self.peut_emettre()
            mqttLiaisonFonctions.log("LIAISON_MQTT_ERREUR: ordre " + nom + "/" + o[0] + " refusé, réseau, broker ou esclave indisponible !", LOG_LEVEL_ERREUR)
            return "hors_ligne"
        end
        var code = g.demande(nom + "/" + o[0], o[1], tasmota.millis())
        if code == "envoyer"
            mqtt.publish("cmnd/" + topic + "/" + o[0], o[1])
            if logFonctions.actif(LOG_LEVEL_DEBUG, "liaisonMqtt")
                mqttLiaisonFonctions.log("LIAISON_MQTT: ordre " + nom + "/" + o[0] + " = " + o[1] + " envoyé !", LOG_LEVEL_DEBUG)
            end
        end
        return code
    end

    # Ligne d'alerte de l'accueil, rafraichie ~2 s : chaine precalculee ; puis les lignes « perime » (decision A2 du 2026-11-20)
    def web_sensor()
        if size(self.ligne) > 0    tasmota.web_send(self.ligne)    end
        var t = self.perimes()
        if size(t) > 0    tasmota.web_send(t)    end
    end

    # Une ligne par element MQTT_<nom> actif d'un esclave injoignable : tous pendant l'alerte du broker, ceux d'un esclave
    # Offline (LWT) sinon. Mesure : derniere valeur du persist ; relais : etat reel inconnu. Chaine vide en temps normal.
    def perimes()
        import persist
        var tous = size(self.ligne) > 0
        var t = ""
        for nom: self.esclaves.keys()
            if !tous && self.en_ligne.find(nom) != false    continue    end
            if self.liens == nil    self.construit()    end
            for e: self.affiches.find(nom, [])
                var d = persist.find("modules", {}).find(e[1], {}).find("environnement", {}).find(e[2], {}).find(e[3], {})
                var v = e[2] == "relais" ? "état réel inconnu" : "dernière valeur " + str(d.find("value", "?"))
                t += "{s}<span style='font-size:70%'>" + e[0] + "</span>{m}<span style='color:#f44;font-size:70%'>" + v + " (périmé)</span>{e}"
            end
        end
        return t
    end

    # Broker perdu : alerte (log erreur + accueil), oubli des ordres en attente et des etats connus ; retour : relecture des etats reels
    def surveille()
        import global
        import mqttLiaisonFonctions
        var v = global.mqttLiaisonVeille
        var g = global.mqttLiaisonGarde
        if v == nil || g == nil    return    end
        var r = v.observe(self.peut_emettre(), tasmota.millis())
        if r == "alerte"
            g.oublie()
            self.ligne = "{s}<span style='color:#f44;font-weight:bold;font-size:70%'>&#9888; Broker MQTT injoignable</span>{m}<span style='font-size:70%'>depuis plus de " + str(v.alerte_ms / 60000) + " min : voie MQTT coupée, états des esclaves inconnus</span>{e}"
            mqttLiaisonFonctions.log("LIAISON_MQTT_ERREUR: broker injoignable depuis plus de " + str(v.alerte_ms / 1000) + " s, voie MQTT coupée !", LOG_LEVEL_ERREUR)
        elif r == "retour"
            self.ligne = ""
            self.resync = []
            for nom: self.esclaves.keys()
                self.resync.push(self.esclaves[nom])
            end
            mqttLiaisonFonctions.log("LIAISON_MQTT: broker revenu, relecture de l'état des esclaves !", LOG_LEVEL_INFO)
        end
    end

    # Ordres sans accuse : renvois bornes par les garde-fous, au plus RENVOIS_PAR_PASSAGE publish par seconde.
    # Apres le retour du broker, relit l'etat reel de chaque esclave (cmnd/<topic>/Power sans valeur = question), meme plafond.
    def every_second()
        import mqtt
        import global
        import string
        self.surveille()
        var g = global.mqttLiaisonGarde
        var reste = self.RENVOIS_PAR_PASSAGE                 # un seul plafond de publish par seconde, relectures et renvois confondus
        if size(self.resync) > 0 && self.peut_emettre()
            while reste > 0 && size(self.resync) > 0
                mqtt.publish("cmnd/" + self.resync.pop() + "/Power", "")
                reste -= 1
            end
        end
        if reste <= 0 || g == nil || size(g.attente) == 0 || !self.peut_emettre()    return    end
        var r = g.a_renvoyer(tasmota.millis(), reste)
        for e: r["renvoyer"]
            var i = string.find(e[0], "/")
            var topic = self.esclaves.find(e[0][0 .. i - 1])
            if topic != nil    mqtt.publish("cmnd/" + topic + "/" + e[0][i + 1 ..], str(e[1]))    end
        end
    end
end

controleMqttLiaison.CONTROLE_MQTT_LIAISON = CONTROLE_MQTT_LIAISON

# init() : APPELEE AUTOMATIQUEMENT par 'import controleMqttLiaison'. Garde d'activation, puis driver et instance globale
# (global.mqttLiaisonDriver, lue par la commande ReglageMqttLiaison ordre ; pas le nom du module, que import ecraserait).
def controleMqttLiaison_init(m)
    import global
    import persist
    if persist.find("drivers", {}).find("liaisonMqtt", {}).find("activation", "OFF") == "ON"
        var inst = m.CONTROLE_MQTT_LIAISON()
        global.mqttLiaisonDriver = inst
        tasmota.add_driver(inst)
    end
    return m
end
controleMqttLiaison.init = controleMqttLiaison_init

# Rend le module a son import depuis le LittleFS (carte au firmware sans module solidifie, piege 13)
return controleMqttLiaison
