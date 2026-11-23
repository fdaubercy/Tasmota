# TAILLE DU BINOME : voir le bloc en tete de controleMqttLiaison.be (genere par mesure_binomes.py, ne pas editer)
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
    static AGE_ETAT_MS = 30000           # au-dela, un etat connu n'est plus cru : l'ordre « identique » repart (le retour le confirme)
    var age_etat
    var fenetre, max_element, max_total, quarantaine_ms, coupure_ms, delai_accuse, essais_max
    var etats_t
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
        self.age_etat = self.entier(c, "ageEtatMs", self.AGE_ETAT_MS)
        self.etats_t = {}             # cle -> instant du dernier retour de l'esclave
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
        if a == nil && self.etats.find(cle) == valeur && t - self.etats_t.find(cle, t - self.age_etat - 1) <= self.age_etat    return "identique"    end
        var b = self.bloque(cle, t)
        if b != nil    return b    end
        self.note(cle, t)
        var nouvelle = {"valeur": valeur, "essais": 1, "t": t}
        if a != nil    nouvelle["avant"] = a["valeur"]    end                # ordre remplace : son retour tardif n'est pas un changement concurrent
        self.attente[cle] = nouvelle
        return "envoyer"
    end

    def recoit(cle, valeur, t)
        if !self.valide(cle, valeur)    return "invalide"    end
        valeur = str(valeur)
        var connu = self.etats.contains(cle)
        var ancien = self.etats.find(cle)
        self.etats[cle] = valeur
        self.etats_t[cle] = t
        var a = self.attente.find(cle)
        if a != nil
            if valeur == a["valeur"]
                self.attente.remove(cle)
                return "accuse"
            end
            if a.find("avant") == valeur    return "inchange"    end        # accuse tardif de l'ordre remplace : le nouvel ordre reste attendu (essai A6 du 2026-11-19)
            if !connu    return "initial"    end                         # 1er etat vu, sans doute l'ancien : l'ordre reste attendu
            if ancien == valeur    return "inchange"    end              # ancien etat repete : l'ordre n'est pas encore applique
            self.attente.remove(cle)                                     # changement concurrent : l'esclave a decide autre chose
            return "evenement"
        end
        if !connu    return "initial"    end
        if ancien == valeur    return "inchange"    end
        return "evenement"
    end

    # maxi : plafond de renvois rendus par appel (les autres restent echus pour le prochain passage) ; nil = sans plafond.
    # Chaque renvoi est un publish, et un publish lent bloque loop() : jamais une rafale dans le meme appel.
    def a_renvoyer(t, maxi)
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
                elif maxi != nil && size(renvoyer) >= maxi
                    # plafond atteint : cet ordre reste echu, il repart au prochain passage
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

    # Etat resume (commande ReglageMqttLiaison etat)
    def bilan()
        return {"coupe": self.coupe_actif, "quarantaines": size(self.quarantaine), "attentes": size(self.attente), "elements": size(self.etats)}
    end

    # Broker perdu longtemps : ordres en attente et etats connus ne valent plus rien (le prochain retour reconstruit les etats)
    def oublie()
        self.attente = {}
        self.etats = {}
        self.etats_t = {}
    end

    # Leve quarantaines et coupe-circuit (commande ReglageMqttLiaison rearme)
    def rearme()
        self.quarantaine = {}
        self.emis = {}
        self.totaux = []
        self.coupe_actif = false
    end
end

mqttLiaisonFonctions.GardeMqtt = GardeMqtt

# Surveillance du broker (plan voie-mqtt A7). Module pur : le driver lui passe « reseau et broker joignables ? » et l'instant.
#   observe(connecte, t) -> "alerte" (perdu depuis alerte_ms, UNE fois) | "retour" (revenu apres une alerte, UNE fois) | "rien"
# Une coupure plus courte que le delai ne produit ni alerte ni retour. Instants compares par difference (millis sur 32 bits).
class SurveilleBroker
    static ALERTE_MS = 120000            # perte du broker au-dela de laquelle l'alerte part (reglage alerteBrokerMs)
    var alerte_ms, perdu, alerte

    def init(cfg)
        var v = isinstance(cfg, map) ? cfg.find("alerteBrokerMs") : nil
        self.alerte_ms = (type(v) == "int" && v > 0) ? v : self.ALERTE_MS
        self.perdu = nil
        self.alerte = false
    end

    def observe(connecte, t)
        if connecte
            var etait = self.alerte
            self.perdu = nil
            self.alerte = false
            return etait ? "retour" : "rien"
        end
        if self.perdu == nil    self.perdu = t    end
        if !self.alerte && t - self.perdu >= self.alerte_ms
            self.alerte = true
            return "alerte"
        end
        return "rien"
    end
end

mqttLiaisonFonctions.SurveilleBroker = SurveilleBroker

# Journal du module et du driver : cible liaisonMqtt (seuil drivers.liaisonMqtt.log), charte des logs du depot
def mqttLiaisonFonctions_log(msg, niveau)
    import logFonctions
    logFonctions.log(msg, niveau, "liaisonMqtt")
end
mqttLiaisonFonctions.log = mqttLiaisonFonctions_log

# Aide de la commande ReglageMqttLiaison, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def mqttLiaisonFonctions_aideReglage(sujet)
    import string
    if sujet == nil
        return [["etat", "etat", "etat de la voie : coupe-circuit, quarantaines, ordres en attente"],
                ["rearme", "rearme", "leve les quarantaines et le coupe-circuit"],
                ["ordre", "ordre <esclave> <commande> <valeur>", "envoie un ordre en passant par les garde-fous (essai)"]]
    end
    var s = string.tolower(str(sujet))
    if s == "etat"      return ["Rend {coupe, quarantaines, attentes, elements}."]    end
    if s == "rearme"    return ["Vide quarantaines, comptages et coupe-circuit. Ne touche ni aux etats connus ni aux ordres en attente."]    end
    if s == "ordre"     return ["esclave = cle de drivers.liaisonMqtt.esclaves. Commandes permises : Power, Power<n> (ON, OFF, 1, 0, true, false), Dimmer et CT (entier).", "Les autres commandes (Restart, Backlog, Br, TOGGLE...) sont refusees : invalide.", "Reponse : envoyer, identique, attente, quarantaine, coupe, invalide, inconnu ou hors_ligne (reseau, broker ou esclave Offline)."]    end
    return nil
end
mqttLiaisonFonctions.aideReglage = mqttLiaisonFonctions_aideReglage

def mqttLiaisonFonctions_reglage(cmd, idx, payload, payload_json)
    import string
    import json
    import global
    import diversFonctions
    import mqttLiaisonFonctions                  # solidifie, le nom global du module n'existe pas (piege 2)
    if diversFonctions.traiteAide("ReglageMqttLiaison", payload, mqttLiaisonFonctions.aideReglage, true)    return    end
    var mots = []
    for m: string.split(payload == nil ? "" : str(payload), " ")
        if size(m) > 0    mots.push(m)    end
    end
    var sous = size(mots) > 0 ? string.tolower(mots[0]) : "etat"
    var g = global.mqttLiaisonGarde
    var rep = nil
    var c = global.mqttLiaisonDriver
    if g == nil                rep = {"erreur": "voie MQTT non chargee"}
    elif sous == "etat"
        rep = g.bilan()
        if c != nil    rep["en_ligne"] = c.en_ligne    end
    elif sous == "rearme"      g.rearme()    rep = {"rearme": true}
    elif sous == "ordre"
        if c == nil              rep = {"erreur": "driver absent (drivers.liaisonMqtt.activation a OFF ?)"}
        elif size(mots) < 4      rep = {"erreur": "syntaxe : ordre <esclave> <commande> <valeur>"}
        else                     rep = {"ordre": c.ordonne(mots[1], mots[2], mots[3])}
        end
    else                       rep = {"erreur": "sous-commande inconnue : " + sous}
    end
    tasmota.resp_cmnd(json.dump({"ReglageMqttLiaison": rep}))
end
mqttLiaisonFonctions.reglage = mqttLiaisonFonctions_reglage

# init() : APPELEE AUTOMATIQUEMENT par 'import mqttLiaisonFonctions'. Seuils lus dans drivers.liaisonMqtt.garde du
# persist (cles absentes = valeurs par defaut) ; l'instance vit dans global.mqttLiaisonGarde.
def mqttLiaisonFonctions_init(m)
    import global
    import persist
    var cfg = persist.find("drivers", {}).find("liaisonMqtt", {}).find("garde", {})
    global.mqttLiaisonGarde = m.GardeMqtt(cfg)
    global.mqttLiaisonVeille = m.SurveilleBroker(persist.find("drivers", {}).find("liaisonMqtt", {}))
    return m
end
mqttLiaisonFonctions.init = mqttLiaisonFonctions_init

return mqttLiaisonFonctions
