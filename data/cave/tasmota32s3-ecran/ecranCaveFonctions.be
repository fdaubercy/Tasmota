# Fonctions de l'ecran 7B de la cave : MODELE des valeurs affichees (plan ecran-cave-vues-commandes, A6, 2026-11-12).
# Les valeurs arrivent par MQTT (abonnements poses par controleEcranCave.be) : serveur de la cave (AM2301 et PompeVideCave du
# SENSOR, POWER1 a 5 du STATE / RESULT) et carte de la cuve (sensorsCuve.niveauCuve). Chaque valeur garde l'heure de sa reception ;
# elle est « perimee » au-dela de modules.ecranCave.peremption.<source> secondes (900 = 3 x 300 s), et tant que rien n'est recu
# de la source (broker absent). Seul un message JSON lisible rafraichit l'heure de sa source.
# Interface produite (lue par l'interface d'ecran, A7) : modele() -> {"valeurs": {cle: {"valeur", "perime"}}, "alertes": [texte],
# "broker": bool} ; perime(source) -> bool. Cles : temperature, humidite, pompe, manuel, niveauBas, niveauHaut, alerte,
# power1..power5, taux (0 a 1), volume (L). Sources : "cave", "cuve".
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

return ecranCaveFonctions
