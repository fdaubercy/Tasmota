# Garde-fous de la voie MQTT maitre/esclaves (plan tasks/plans/voie-mqtt.md, A3 ; analyse outils_docs/ANALYSE_VOIE_MQTT_2026-11-16.md §6).
# Ce module ne parle PAS a MQTT : il decide s'il faut envoyer un ordre, et classe ce qui revient. Le driver
# (controleMqttLiaison, A4) fait les publish/subscribe. Le temps est passe en parametre (millisecondes, comparees par
# DIFFERENCE : le debordement 32 bits de tasmota.millis() vers 24,8 jours est sans effet) : le module ne depend ni de
# tasmota ni de mqtt, donc se teste sans carte (banc_mqtt_liaison). Cle = texte non vide, valeur = non nulle (convertie
# en texte), sinon la reponse est "invalide".
#
# Architecture A (topics natifs cmnd/stat/tele). Un « element » est identifie par une cle texte (ex. "portail/relai1").
#   demande(cle, valeur, t)  -> "envoyer" | "identique" | "attente" | "quarantaine" | "coupe"
#   recoit(cle, valeur, t)   -> "accuse" | "evenement" | "initial" | "inchange"   (un retour stat/ ou tele/ de l'esclave)
#   a_renvoyer(t)            -> {"renvoyer": [[cle, valeur]...], "echec": [cle...]}  (ordres sans accuse apres le delai)
# Garde-fous : G3 pas d'ordre si l'etat connu est deja la valeur ; G4 limiteur par element (quarantaine) ; G5 coupe-circuit
# global ; accuse = le retour attendu n'est PAS un evenement (pas d'ecriture en boucle) ; renvois en nombre borne.
# Solidifiable : aucun import ni appel tasmota au niveau fichier, constantes en membres statiques de la classe,
# instance hors du module (global.mqttLiaisonGarde), la table d'un module solidifie etant constante.
#@ solidify:mqttLiaisonFonctions
var mqttLiaisonFonctions = module("mqttLiaisonFonctions")

class GardeMqtt
    static FENETRE_MS = 10000            # fenetre glissante des comptages
    static MAX_ELEMENT = 10              # ordres emis par element dans la fenetre avant quarantaine
    static MAX_TOTAL = 60                # ordres emis au total dans la fenetre avant coupe-circuit
    static QUARANTAINE_MS = 60000        # duree de la quarantaine d'un element
    static COUPURE_MS = 300000           # duree du coupe-circuit global
    static DELAI_ACCUSE_MS = 3000        # mesure du 2026-11-17 : reponses jusqu'a 1,6 s en Wi-Fi direct
    static ESSAIS_MAX = 3                # emissions au total (la premiere comprise) avant d'abandonner un ordre
    var fenetre, max_element, max_total, quarantaine_ms, coupure_ms, delai_accuse, essais_max
    var etats, emis, quarantaine, totaux, coupe_actif, coupe_jusqua, attente

    def init(cfg)
        var c = isinstance(cfg, map) ? cfg : {}
        self.fenetre = self.entier(c, "fenetreMs", self.FENETRE_MS)
        self.max_element = self.entier(c, "maxParElement", self.MAX_ELEMENT)
        self.max_total = self.entier(c, "maxTotal", self.MAX_TOTAL)
        self.quarantaine_ms = self.entier(c, "quarantaineMs", self.QUARANTAINE_MS)
        self.coupure_ms = self.entier(c, "coupureMs", self.COUPURE_MS)
        self.delai_accuse = self.entier(c, "delaiAccuseMs", self.DELAI_ACCUSE_MS)
        self.essais_max = self.entier(c, "essaisMax", self.ESSAIS_MAX)
        self.etats = {}               # cle -> derniere valeur connue de l'esclave
        self.emis = {}                # cle -> instants des ordres emis (fenetre)
        self.quarantaine = {}         # cle -> instant de fin de quarantaine
        self.totaux = []              # instants de tous les ordres emis (fenetre)
        self.coupe_actif = false      # coupe-circuit global en cours ?
        self.coupe_jusqua = 0         # instant de fin du coupe-circuit (valable si coupe_actif)
        self.attente = {}             # cle -> {valeur, essais, t} : ordre emis, accuse attendu
    end

    # Entier strictement positif du persist, sinon la valeur par defaut
    def entier(c, cle, defaut)
        var v = c.find(cle)
        return (type(v) == "int" && v > 0) ? v : defaut
    end

    def log(msg, niveau)
        import logFonctions
        logFonctions.log(msg, niveau, "liaisonMqtt")
    end

    # Instants encore dans la fenetre, dans une NOUVELLE liste
    def recents(liste, t)
        var r = []
        for x: liste
            if t - x < self.fenetre    r.push(x)    end
        end
        return r
    end

    # Cle texte non vide et valeur non nulle ; sinon l'appel est refuse et loggue
    def valide(cle, valeur)
        if type(cle) == "string" && size(cle) > 0 && valeur != nil    return true    end
        self.log("LIAISON_MQTT_ERREUR: appel refusé, clé ou valeur invalide (" + str(cle) + ", " + str(valeur) + ") !", LOG_LEVEL_ERREUR)
        return false
    end

    # Le coupe-circuit est-il actif ? Il se referme seul a l'echeance. Les instants se comparent par DIFFERENCE
    # (t - echeance) : tasmota.millis() est un entier 32 bits qui deborde vers 24,8 jours, la difference reste juste.
    def coupee(t)
        if !self.coupe_actif    return false    end
        if t - self.coupe_jusqua >= 0
            self.coupe_actif = false
            self.totaux = []
            self.log("LIAISON_MQTT: voie rétablie après coupe-circuit !", LOG_LEVEL_INFO)
            return false
        end
        return true
    end

    # nil si l'emission est permise, sinon "coupe" ou "quarantaine" (et la mesure est prise)
    def bloque(cle, t)
        if self.coupee(t)    return "coupe"    end
        var fin = self.quarantaine.find(cle)
        if fin != nil
            if fin - t > 0    return "quarantaine"    end
            self.quarantaine.remove(cle)
        end
        self.emis[cle] = self.recents(self.emis.find(cle, []), t)
        if size(self.emis[cle]) >= self.max_element
            self.quarantaine[cle] = t + self.quarantaine_ms
            self.emis[cle] = []
            self.log("LIAISON_MQTT_ERREUR: " + str(cle) + " en quarantaine, trop d'ordres en peu de temps (boucle ?) !", LOG_LEVEL_ERREUR)
            return "quarantaine"
        end
        self.totaux = self.recents(self.totaux, t)
        if size(self.totaux) >= self.max_total
            self.coupe_actif = true
            self.coupe_jusqua = t + self.coupure_ms
            self.log("LIAISON_MQTT_ERREUR: coupe-circuit, trop d'ordres au total (boucle ?) !", LOG_LEVEL_ERREUR)
            return "coupe"
        end
        return nil
    end

    # Inscrit un ordre emis dans les comptages
    def note(cle, t)
        var l = self.emis.find(cle, [])
        l.push(t)
        self.emis[cle] = l
        self.totaux.push(t)
    end

    def demande(cle, valeur, t)
        if !self.valide(cle, valeur)    return "invalide"    end
        valeur = str(valeur)                       # 1 et "1" sont la meme valeur (un retour MQTT est toujours du texte)
        var a = self.attente.find(cle)
        if a != nil && a["valeur"] == valeur    return "attente"    end
        if a == nil && self.etats.find(cle) == valeur    return "identique"    end
        var b = self.bloque(cle, t)
        if b != nil    return b    end
        self.note(cle, t)
        self.attente[cle] = {"valeur": valeur, "essais": 1, "t": t}
        return "envoyer"
    end

    def recoit(cle, valeur, t)
        if !self.valide(cle, valeur)    return "invalide"    end
        valeur = str(valeur)
        var connu = self.etats.contains(cle)
        var ancien = self.etats.find(cle)
        self.etats[cle] = valeur
        var a = self.attente.find(cle)
        if a != nil
            if valeur == a["valeur"]
                self.attente.remove(cle)
                return "accuse"
            end
            if !connu    return "initial"    end                         # 1er etat vu, sans doute l'ancien : l'ordre reste attendu
            if ancien == valeur    return "inchange"    end              # ancien etat repete : l'ordre n'est pas encore applique
            self.attente.remove(cle)                                     # changement concurrent : l'esclave a decide autre chose
            return "evenement"
        end
        if !connu    return "initial"    end
        if ancien == valeur    return "inchange"    end
        return "evenement"
    end

    def a_renvoyer(t)
        var renvoyer = []
        var echec = []
        var cles = []
        for k: self.attente.keys()    cles.push(k)    end                # la table change pendant la boucle
        for cle: cles
            var a = self.attente[cle]
            if t - a["t"] >= self.delai_accuse
                if a["essais"] >= self.essais_max
                    self.attente.remove(cle)
                    echec.push(cle)
                    self.log("LIAISON_MQTT_ERREUR: " + str(cle) + " sans accusé après " + str(a["essais"]) + " essais !", LOG_LEVEL_ERREUR)
                elif self.bloque(cle, t) != nil
                    self.attente.remove(cle)
                    echec.push(cle)
                    self.log("LIAISON_MQTT_ERREUR: " + str(cle) + " ordre abandonné, voie bloquée (quarantaine ou coupe-circuit) !", LOG_LEVEL_ERREUR)
                else
                    self.note(cle, t)
                    a["essais"] = a["essais"] + 1
                    a["t"] = t
                    renvoyer.push([cle, a["valeur"]])
                end
            end
        end
        return {"renvoyer": renvoyer, "echec": echec}
    end

    # Leve quarantaines et coupe-circuit (commande ReglageMqttLiaison, A4)
    def rearme()
        self.quarantaine = {}
        self.emis = {}
        self.totaux = []
        self.coupe_actif = false
    end
end

mqttLiaisonFonctions.GardeMqtt = GardeMqtt

# init() : APPELEE AUTOMATIQUEMENT par 'import mqttLiaisonFonctions'. Seuils lus dans drivers.liaisonMqtt.garde du
# persist (cles absentes = valeurs par defaut) ; l'instance vit dans global.mqttLiaisonGarde.
def mqttLiaisonFonctions_init(m)
    import global
    import persist
    var cfg = persist.find("drivers", {}).find("liaisonMqtt", {}).find("garde", {})
    global.mqttLiaisonGarde = m.GardeMqtt(cfg)
    return m
end
mqttLiaisonFonctions.init = mqttLiaisonFonctions_init

return mqttLiaisonFonctions
