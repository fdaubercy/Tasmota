# Fonctions de l'ecran 7B de la cave : MODELE des valeurs affichees (plan ecran-cave-vues-commandes, A6, 2026-11-12).
# Les valeurs arrivent par MQTT (abonnements poses par controleEcranCave.be) : serveur de la cave (AM2301 et PompeVideCave du
# SENSOR, POWER1 a 5 du STATE / RESULT) et carte de la cuve (sensorsCuve.niveauCuve). Chaque valeur garde l'heure de sa reception ;
# elle est « perimee » au-dela de modules.ecranCave.peremption.<source> secondes (900 = 3 x 300 s), et tant que rien n'est recu
# de la source (broker absent). Seul un message JSON lisible rafraichit l'heure de sa source.
# Interface produite (lue par l'interface d'ecran, A7) : modele() -> {"valeurs": {cle: {"valeur", "perime"}}, "alertes": [texte],
# "broker": bool} ; perime(source) -> bool. Cles : temperature, humidite, pompe, manuel, niveauBas, niveauHaut, alerte,
# power1..power5, taux (0 a 1), volume (L). Sources : "cave", "cuve".
# Touches (A5) : touche(numero) -> "envoye" / "refuse" / "inconnu" (voir plus bas) ; reinitialise() remet seq et relances a zero.
# Compile en .bec par demarrage.compile(["ecranCaveFonctions"], "modules.ecranCave"), importe par controleEcranCave.be.
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).
var ecranCaveFonctions = module("ecranCaveFonctions")

ecranCaveFonctions.valeurs = {}      # cle -> {"v": valeur, "t": millis, "source": source}
ecranCaveFonctions.derniere = {}     # source -> millis du dernier message JSON lisible

def ecranCaveFonctions_log(msg, niveau)
    import logFonctions
    logFonctions.log(msg, niveau)
end
ecranCaveFonctions.log = ecranCaveFonctions_log

# Delai de peremption (s) d'une source : persist modules.ecranCave.peremption, 900 s par defaut
def ecranCaveFonctions_delai(source)
    import global
    var cfg = global.modules.find("ecranCave")
    var p = (type(cfg) == "instance") ? cfg.find("peremption") : nil
    return (type(p) == "instance") ? int(p.find(source, 900)) : 900
end

# true si l'heure `t` (millis) est trop ancienne pour `source` ; nil = jamais recu ; une horloge qui recule compte comme perimee
def ecranCaveFonctions_vieux(source, t)
    if (t == nil)    return true    end
    var age = tasmota.millis() - t
    return age < 0 || age > ecranCaveFonctions_delai(source) * 1000
end

def ecranCaveFonctions_perime(source)
    return ecranCaveFonctions_vieux(source, ecranCaveFonctions.derniere.find(source))
end
ecranCaveFonctions.perime = ecranCaveFonctions_perime

def ecranCaveFonctions_pose(cle, valeur, source)
    ecranCaveFonctions.valeurs[cle] = {"v": valeur, "t": tasmota.millis(), "source": source}
end

# Le serveur de la cave : SENSOR (AM2301, PompeVideCave), STATE et RESULT (POWER1 a 5). `m` = map JSON.
def ecranCaveFonctions_lisCave(m)
    if (type(m.find("StatusSNS")) == "instance")    m = m["StatusSNS"]    end        # reponse a « STATUS 10 » : un SENSOR emballe
    var th = m.find("AM2301")
    if (type(th) == "instance")
        if (th.contains("Temperature"))    ecranCaveFonctions_pose("temperature", th["Temperature"], "cave")    end
        if (th.contains("Humidity"))    ecranCaveFonctions_pose("humidite", th["Humidity"], "cave")    end
    end
    var p = m.find("PompeVideCave")
    if (type(p) == "instance")
        var cles = {"Pompe": "pompe", "Manuel": "manuel", "Alerte": "alerte"}
        for c: cles.keys()
            if (p.contains(c))    ecranCaveFonctions_pose(cles[c], p[c], "cave")    end
        end
        var niv = p.find("Niveaux")
        if (type(niv) == "instance")
            if (niv.contains("Bas"))    ecranCaveFonctions_pose("niveauBas", niv["Bas"], "cave")    end
            if (niv.contains("Haut"))    ecranCaveFonctions_pose("niveauHaut", niv["Haut"], "cave")    end
        end
    end
    for i: 1 .. 5
        var etat = m.find("POWER" + str(i))
        if (etat == "ON" || etat == "OFF")    ecranCaveFonctions_pose("power" + str(i), etat, "cave")    end
    end
end

# La cuve : SENSOR portant sensorsCuve.niveauCuve (tauxRemplissage de 0 a 1, volume en L)
def ecranCaveFonctions_lisCuve(m)
    var s = m.find("sensorsCuve")
    var n = (type(s) == "instance") ? s.find("niveauCuve") : nil
    if (type(n) != "instance")    return    end
    if (n.contains("tauxRemplissage"))    ecranCaveFonctions_pose("taux", n["tauxRemplissage"], "cuve")    end
    if (n.contains("volume"))    ecranCaveFonctions_pose("volume", n["volume"], "cuve")    end
end

# Message MQTT recu de `source` sur `topic` : JSON illisible = erreur journalisee, rien d'autre ne change
def ecranCaveFonctions_recoit(source, topic, texte)
    import json
    var m = json.load(texte)
    if (type(m) != "instance")
        ecranCaveFonctions_log("ECRAN_CAVE_ERREUR: message illisible sur " + topic + " (JSON attendu) !", LOG_LEVEL_ERREUR)
        return
    end
    ecranCaveFonctions.derniere[source] = tasmota.millis()
    try
        if (source == "cave")
            ecranCaveFonctions_lisCave(m)
        elif (source == "cuve")
            ecranCaveFonctions_lisCuve(m)
        end
    except .. as e, ms
        ecranCaveFonctions_log("ECRAN_CAVE_ERREUR: " + topic + " : " + str(e) + " - " + str(ms) + " !", LOG_LEVEL_ERREUR)
    end
end
ecranCaveFonctions.recoit = ecranCaveFonctions_recoit

# Modele lu par l'interface : valeurs avec leur peremption, alertes (celle de la pompe), etat du broker
def ecranCaveFonctions_modele()
    import mqtt
    var vals = {}
    for cle: ecranCaveFonctions.valeurs.keys()
        var e = ecranCaveFonctions.valeurs[cle]
        vals[cle] = {"valeur": e["v"], "perime": ecranCaveFonctions_vieux(e["source"], e["t"])}
    end
    var alertes = []
    var al = ecranCaveFonctions.valeurs.find("alerte")
    if (al != nil && type(al["v"]) == "string" && size(al["v"]) > 0)    alertes.push(al["v"])    end
    return {"valeurs": vals, "alertes": alertes, "broker": mqtt.connected()}
end
ecranCaveFonctions.modele = ecranCaveFonctions_modele


# ---- Touches (A5) : l'ecran pousse l'ETAT VOULU de la touche au serveur de la cave par un push ModBus 0x10 (registre 32 + numero - 1).
# Mot = (seq << 1) | (voulu == ON) ; seq de 1 a 127 propre a chaque touche, en RAM (jamais 0 : le serveur ignore une seq deja vue).
# Correspondance touche -> etat affiche : persist modules.ecranCave.touches = {"1": "power3", ..., "5": "redemarre"}.
# Relance du MEME mot (meme seq : le serveur n'agit qu'une fois) toutes les 2 s, 5 fois au plus, jusqu'a ce que l'etat recu par MQTT
# egale `voulu`. La touche « redemarre » n'est JAMAIS relancee : le serveur oublie ses seq en redemarrant, une relance le ferait boucler.
ecranCaveFonctions.seqs = {}       # numero -> derniere seq emise
ecranCaveFonctions.relances = {}   # numero -> {"mot", "cle", "voulu", "n"}

def ecranCaveFonctions_reinitialise()
    for n: ecranCaveFonctions.relances.keys()
        tasmota.remove_timer("ecran_cave_touche" + str(n))
    end
    ecranCaveFonctions.seqs = {}
    ecranCaveFonctions.relances = {}
end
ecranCaveFonctions.reinitialise = ecranCaveFonctions_reinitialise

def ecranCaveFonctions_pousse(numero, mot)
    import modbusFonctions
    return modbusFonctions.pousseEtat(32 + numero - 1, "uint16", [mot]) != nil
end

# Minuterie de relance de la touche `numero`
def ecranCaveFonctions_relance(numero)
    var r = ecranCaveFonctions.relances.find(numero)
    if (r == nil)    return    end
    var e = ecranCaveFonctions.valeurs.find(r["cle"])
    if (e != nil && e["v"] == r["voulu"])    # etat confirme par MQTT
        ecranCaveFonctions.relances.remove(numero)
        return
    end
    if (r["n"] >= 5)
        ecranCaveFonctions.relances.remove(numero)
        ecranCaveFonctions_log("ECRAN_CAVE_ERREUR: touche " + str(numero) + " sans confirmation apres 5 relances, abandon !", LOG_LEVEL_ERREUR)
        return
    end
    r["n"] += 1
    ecranCaveFonctions_log("ECRAN_CAVE: relance " + str(r["n"]) + " de la touche " + str(numero) + " !", LOG_LEVEL_DEBUG)
    ecranCaveFonctions_pousse(numero, r["mot"])
    tasmota.set_timer(2000, def () ecranCaveFonctions_relance(numero) end, "ecran_cave_touche" + str(numero))
end

# Appui sur la touche `numero` : "envoye", "refuse" (etat inconnu ou perime, ou serveur injoignable) ou "inconnu" (numero absent du persist)
def ecranCaveFonctions_touche(numero)
    import global
    var cfg = global.modules.find("ecranCave")
    var touches = (type(cfg) == "instance") ? cfg.find("touches") : nil
    var cle = (type(touches) == "instance") ? touches.find(str(numero)) : nil
    if (cle == nil)    return "inconnu"    end
    var voulu = "ON"
    var e = nil
    if (cle != "redemarre")
        e = ecranCaveFonctions.valeurs.find(cle)
        if (e == nil || ecranCaveFonctions_vieux(e["source"], e["t"]))
            ecranCaveFonctions_log("ECRAN_CAVE: touche " + str(numero) + " refusee, etat de " + cle + " inconnu ou perime !", LOG_LEVEL_DEBUG)   # refus normal (broker coupe) : l'ecran le montre deja
            return "refuse"
        end
        voulu = (e["v"] == "ON") ? "OFF" : "ON"
    end
    tasmota.remove_timer("ecran_cave_touche" + str(numero))
    ecranCaveFonctions.relances.remove(numero)
    var seq = ecranCaveFonctions.seqs.find(numero, 0) % 127 + 1
    ecranCaveFonctions.seqs[numero] = seq
    var mot = (seq << 1) | (voulu == "ON" ? 1 : 0)
    if (!ecranCaveFonctions_pousse(numero, mot))
        ecranCaveFonctions_log("ECRAN_CAVE_ERREUR: touche " + str(numero) + " non envoyee, serveur injoignable par ModBus !", LOG_LEVEL_ERREUR)
        return "refuse"
    end
    ecranCaveFonctions_log("ECRAN_CAVE: touche " + str(numero) + " (" + cle + ") -> " + voulu + " !", LOG_LEVEL_INFO)
    if (cle != "redemarre")
        ecranCaveFonctions.relances[numero] = {"mot": mot, "cle": cle, "voulu": voulu, "n": 0}
        tasmota.set_timer(2000, def () ecranCaveFonctions_relance(numero) end, "ecran_cave_touche" + str(numero))
    end
    return "envoye"
end
ecranCaveFonctions.touche = ecranCaveFonctions_touche

return ecranCaveFonctions
