# TAILLE DU BINOME : voir le bloc en tete de controleHue.be (genere par mesure_binomes.py, ne pas editer)
# Emulation Hue (Alexa) : module PUR du pont Hue emule (le driver controleHue publie global.hue_bridge et regle le firmware).
# Transport NATIF (Emulation 2 : SSDP, /description.xml, /api sur le port 80, xdrv_20_hue.ino) ; ce module choisit les
# appareils exposes (liste blanche) et ecrit les reponses JSON de l'API Hue. Aucun appel tasmota : se teste sans carte
# (banc_hue). Les parametres viennent du persist :
#   serveur.emulationHue = {"activation": "ON"|"OFF", "log": "info"}
#   modules.<m>.environnement.relais.<r>.alexa = {"activation": "ON", "nom": "Projecteur du jardin", "type": "onoff"}
# Un relais n'est expose QUE s'il porte une cle alexa active. Refus fermes (journal erreur) : relais ou module inactif, id hors
# 1 a 32, relais d'un volet (Shutter : relais1 et relais1+1 de chaque VR actif de drivers.voletRoulants actif), type autre
# que onoff, nom vide ou de plus de 32 caracteres, nom ou relais deja expose.
# Solidifiable : aucun import ni appel tasmota au niveau fichier, aucun etat dans la table du module (piege 12).
#@ solidify:hueFonctions
var hueFonctions = module("hueFonctions")

def hueFonctions_log(msg, niveau)
    import logFonctions
    logFonctions.log(msg, niveau, "emulationHue")
end
hueFonctions.log = hueFonctions_log

# Id Hue du relais n (1 a 32) : formule NATIVE de xdrv_20_hue.ino::EncodeLightIdZigbee (3 octets bas de la MAC aux bits
# 4 a 27, n & 0xF, bit 28 si n > 15, relais 32 code 0) : DecodeLightId retombe sur le meme relais. mac = "AA:BB:CC:DD:EE:FF".
def hueFonctions_idHue(n, mac)
    import string
    if type(n) != "int" || n < 1 || n > 32    return nil    end
    var o = string.split(str(mac), ":")
    if size(o) != 6    return nil    end
    var id = (int("0x" + o[3]) << 20) | (int("0x" + o[4]) << 12) | (int("0x" + o[5]) << 4)
    var r = n >= 32 ? 0 : n
    if r > 15    id = id | (1 << 28)    end
    return id | (r & 0xF)
end
hueFonctions.idHue = hueFonctions_idHue

# uniqueid du relais n, comme xdrv_20_hue.ino::GetHueDeviceId(n) : le meme qu'en emulation native, Alexa ne voit pas de doublon
def hueFonctions_uniqueid(n, mac)
    import string
    return string.tolower(str(mac)) + string.format(":%02x:%02X-01", (n >> 8) & 0xFF, (n & 0xFF) ^ 0x10)
end
hueFonctions.uniqueid = hueFonctions_uniqueid

# Relais pilotes par un volet (Shutter) : jamais exposes, meme avec une cle alexa
def hueFonctions_relaisVolets(drivers)
    var r = {}
    var vr = isinstance(drivers, map) ? drivers.find("voletRoulants") : nil
    if !isinstance(vr, map) || vr.find("activation", "OFF") != "ON"    return r    end
    var env = vr.find("environnement")
    var vrs = isinstance(env, map) ? env.find("VRs") : nil
    if !isinstance(vrs, map)    return r    end
    for cle: vrs.keys()
        var v = vrs[cle]
        if !isinstance(v, map) || v.find("activation", "OFF") != "ON" || type(v.find("relais1")) != "int"    continue    end
        r[v["relais1"]] = true
        r[v["relais1"] + 1] = true
    end
    return r
end
hueFonctions.relaisVolets = hueFonctions_relaisVolets

# Raison du refus d'une sortie, nil si elle est exposable
def hueFonctions_refus(m, r, a, volets)
    var nom = a.find("nom")
    var id = r.find("id")
    if m.find("activation", "OFF") != "ON" || r.find("activation", "OFF") != "ON"    return "relais ou module inactif"    end
    if type(id) != "int" || id < 1 || id > 32                                       return "id de relais hors de 1 a 32"    end
    if volets.contains(id)                                                          return "relais de volet (Shutter), jamais expose"    end
    if a.find("type", "onoff") != "onoff"                                           return "type " + str(a.find("type")) + " non gere (onoff seulement)"    end
    if type(nom) != "string" || size(nom) == 0 || size(nom) > 32                    return "nom vide, absent ou de plus de 32 caracteres"    end
    return nil
end
hueFonctions.refus = hueFonctions_refus

# Sorties exposees, triees par relais : [{"n": id du relais, "nom": nom vocal, "cle": "module/relais"}]. Chaque refus est
# journalise en erreur. Persist absent ou invalide : liste vide, jamais d'exception.
def hueFonctions_appareils(modules, drivers)
    import string
    import hueFonctions
    var candidats = []
    if !isinstance(modules, map) || modules.find("activation", "OFF") != "ON"    return candidats    end
    var volets = hueFonctions.relaisVolets(drivers)
    for m: modules.keys()
        var mod = modules[m]
        var env = isinstance(mod, map) ? mod.find("environnement") : nil
        var relais = isinstance(env, map) ? env.find("relais") : nil
        if !isinstance(relais, map)    continue    end
        for c: relais.keys()
            var r = relais[c]
            var a = isinstance(r, map) ? r.find("alexa") : nil
            if a == nil    continue    end                                 # pas de cle alexa : jamais expose, sans bruit
            var raison = !isinstance(a, map) ? "cle alexa invalide" : nil
            if raison == nil && a.find("activation", "OFF") != "ON"    continue    end
            if raison == nil    raison = hueFonctions.refus(mod, r, a, volets)    end
            if raison != nil
                hueFonctions.log("CONTROLE_HUE_ERREUR: sortie " + m + "/" + c + " refusee, " + raison + " !", LOG_LEVEL_ERREUR)
                continue
            end
            var e = {"n": r["id"], "nom": a["nom"], "cle": m + "/" + c}
            var i = size(candidats)                                       # tri par relais puis cle : le refus des doublons ne depend pas de l'ordre des cles
            while i > 0 && (candidats[i - 1]["n"] > e["n"] || (candidats[i - 1]["n"] == e["n"] && candidats[i - 1]["cle"] > e["cle"]))    i -= 1    end
            candidats.insert(i, e)
        end
    end
    var liste = []
    var noms = {}
    var ids = {}
    for e: candidats
        var cle = string.tolower(e["nom"])
        var raison = ids.contains(e["n"]) ? "relais " + str(e["n"]) + " deja expose" : (noms.contains(cle) ? "nom deja pris par " + noms[cle] : nil)
        if raison != nil
            hueFonctions.log("CONTROLE_HUE_ERREUR: sortie " + e["cle"] + " refusee, " + raison + " !", LOG_LEVEL_ERREUR)
            continue
        end
        ids[e["n"]] = true
        noms[cle] = e["cle"]
        liste.push(e)
    end
    return liste
end
hueFonctions.appareils = hueFonctions_appareils

# Etat d'un relais, comme xdrv_20_hue.ino::HueLightStatus1 (bri impose pour un Echo de 1re generation, SetOption109)
def hueFonctions_etat(on, gen1)
    return "{\"on\":" + (on ? "true" : "false") + "," + (gen1 ? "\"bri\":254," : "") + "\"alert\":\"none\",\"effect\":\"none\",\"reachable\":true}"
end
hueFonctions.etat = hueFonctions_etat

# Fiche complete d'un appareil, comme xdrv_20_hue.ino::HueLightStatus2Generic
def hueFonctions_fiche(n, nom, on, mac, gen1)
    import json
    import hueFonctions
    return "{\"state\":" + hueFonctions.etat(on, gen1) + ",\"type\":\"Extended color light\",\"name\":" + json.dump(str(nom)) +
           ",\"modelid\":\"Tasmota\",\"manufacturername\":\"Tasmota\",\"uniqueid\":\"" + hueFonctions.uniqueid(n, mac) + "\"}"
end
hueFonctions.fiche = hueFonctions_fiche

# Reponse a une commande executee
def hueFonctions_succes(id, on)
    return "[{\"success\":{\"/lights/" + str(id) + "/state/on\":" + (on ? "true" : "false") + "}}]"
end
hueFonctions.succes = hueFonctions_succes

# Erreur de l'API Hue (type 3 : ressource absente, 6 : parametre absent, 901 : erreur interne)
def hueFonctions_erreur(id, type_erreur, description)
    import json
    return "[{\"error\":{\"type\":" + str(type_erreur) + ",\"address\":\"/lights/" + str(id) + "\",\"description\":" + json.dump(str(description)) + "}}]"
end
hueFonctions.erreur = hueFonctions_erreur

# Corps d'une commande ({"on":true,...}) -> true / false, nil si absent, invalide ou sans booleen "on"
def hueFonctions_lit(arg)
    import json
    if type(arg) != "string"    return nil    end
    var j = json.load(arg)
    var on = isinstance(j, map) ? j.find("on") : nil
    return type(on) == "bool" ? on : nil
end
hueFonctions.lit = hueFonctions_lit

# Rend le module a son import depuis le LittleFS (carte au firmware sans module solidifie)
return hueFonctions
