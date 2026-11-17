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

    def init()
        import persist
        import mqtt
        import mqttLiaisonFonctions         # cree global.mqttLiaisonGarde
        self.esclaves = {}
        self.par_topic = {}
        self.en_ligne = {}
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
        elif string.find(suffixe, "POWER") == 0
            self.etat(nom, suffixe, s)
        end
        return false
    end

    def resultat(nom, s)
        import json
        var r = json.load(s)
        if !isinstance(r, map)    return    end
        for k: r.keys()
            var v = r[k]
            if v != nil && type(v) != "instance"    self.etat(nom, k, v)    end      # les objets (Button1: {Action}) viennent en A6
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

    # Ordres sans accuse : renvois bornes par les garde-fous, au plus RENVOIS_PAR_PASSAGE publish par seconde
    def every_second()
        import mqtt
        import global
        import string
        var g = global.mqttLiaisonGarde
        if g == nil || size(g.attente) == 0 || !self.peut_emettre()    return    end
        var r = g.a_renvoyer(tasmota.millis(), self.RENVOIS_PAR_PASSAGE)
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
