#- *********************************************************************************************
 * historiqueSeries.be - Choix des series de l'historique d'une carte S3/P4 (2026-10-18)
 *
 * Fichier de fonctions SANS driver, importe par historiqueFonctions.releve() (premiere releve utile,
 * 2 min apres le demarrage) : la carte trace SES capteurs sans liste ecrite a la main.
 *
 * Decouverte : toutes les feuilles NUMERIQUES (int, real) du JSON SENSOR (tasmota.read_sensors()),
 * capteurs reels (DS18B20, ADS1115, AM2301...) comme virtuels (TasmotaSlaveModBus.* du maitre ModBus,
 * valeurs publiees par les modules metier : sensorsCuve...). Sont ecartes :
 *   - les relais, les entrees, les volets et les actionneurs : ON/OFF et texte ne sont pas des nombres ;
 *     segments compares SANS tenir compte de la casse (relecture du 2026-10-19) : Switch*, Button*,
 *     Shutter*, Relay*, PWM*, Power<n> (ENERGY.Power, PowerFactor restent des mesures), relais, relays,
 *     entrees, inputs, dimmer ;
 *   - les mesures internes de la carte (ESP32.Temperature, @rssi, @heap) : seulement par 'ajouts' ;
 *   - les compteurs (segment COUNTER) sans reglage dans 'compteurs' : on ne sait pas ce qu'ils comptent ;
 *   - les cles techniques (Time, Id, TempUnit...) et les feuilles de premier niveau.
 *
 * Reglages, tous facultatifs, dans le bloc diverses.historique du persist :
 *     "exclues":   ["sensorsCuve.valeursAnalogiques"]     chemins ou debuts de chemin a ne pas tracer
 *     "ajouts":    ["ESP32.Temperature", "@rssi"]         series forcees (internes : @rssi et @heap seulement) ;
 *                                                          'exclues' l'emporte sur 'ajouts'
 *     "compteurs": {"COUNTER.C1": {"type": "energie", "impulsionsParUnite": 1000, "unite": "kWh"},
 *                   "COUNTER.C2": {"type": "debit", "impulsionsParUnite": 450, "unite": "L/min"}}
 *         energie : cumul divise par impulsionsParUnite ;
 *         debit   : (impulsions depuis la releve precedente / impulsionsParUnite) PAR MINUTE.
 *     "seriesMax": 12                                      nombre maximal de series
********************************************************************************************* -#

var historiqueSeries = module("historiqueSeries")

# Segments qui ecartent un chemin, EN MINUSCULES (le segment est compare en minuscules) : egalite exacte, puis
# debuts de segment (entrees, volets, relais, actionneurs). Power<n> est traite a part : ENERGY.Power est une mesure.
historiqueSeries.IGNORES = ["time", "tempunit", "pressureunit", "speedunit", "id", "ipaddress", "esp32",
                            "relais", "relays", "entrees", "inputs", "dimmer"]
historiqueSeries.PREFIXES_EXCLUS = ["switch", "button", "shutter", "relay", "pwm"]   # shutter<n> : etat d'un volet
historiqueSeries.INTERNES = ["@rssi", "@heap"]     # seules sources internes (lit) admises par 'ajouts'
historiqueSeries.etatCompteurs = {}     # chemin -> [impulsions, millis] de la releve precedente (debit)

# Liste d'un reglage (exclues, ajouts) ; [] si absent ou d'un autre type
def historiqueSeries_liste(config, cle)
    var v = (isinstance(config, map) ? config.find(cle) : nil)
    return (isinstance(v, list) ? v : [])
end
historiqueSeries.liste = historiqueSeries_liste

# Reglage valide d'un compteur, ou nil : type debit|energie et impulsionsParUnite > 0
def historiqueSeries_reglageCompteur(config, chemin)
    var compteurs = (isinstance(config, map) ? config.find("compteurs") : nil)
    if (!isinstance(compteurs, map))    return nil    end
    var r = compteurs.find(chemin)
    if (!isinstance(r, map))    return nil    end
    var t = r.find("type")
    var ipu = r.find("impulsionsParUnite")
    if ((t != "debit" && t != "energie") || (type(ipu) != "int" && type(ipu) != "real") || ipu <= 0)    return nil    end
    return r
end
historiqueSeries.reglageCompteur = historiqueSeries_reglageCompteur

# Segment ecarte d'office (cle technique, relais, entree, volet, actionneur) ? Sans tenir compte de la casse.
def historiqueSeries_segmentExclu(segment)
    import string
    var s = string.tolower(str(segment))
    if (historiqueSeries.IGNORES.find(s) != nil)    return true    end
    for p: historiqueSeries.PREFIXES_EXCLUS
        if (string.startswith(s, p))    return true    end
    end
    # power<n> (relais n) ; power seul, powerfactor, apparentpower... sont des mesures
    if (size(s) > 5 && string.startswith(s, "power"))
        for i: 5 .. size(s) - 1
            if (s[i] < "0" || s[i] > "9")    return false    end
        end
        return true
    end
    return false
end
historiqueSeries.segmentExclu = historiqueSeries_segmentExclu

# Un chemin peut-il etre une serie ? Les 'exclues' jamais ; puis les 'ajouts' passent (source interne : @rssi
# et @heap seulement).
def historiqueSeries_admissible(chemin, config)
    import string
    for e: historiqueSeries.liste(config, "exclues")
        if (chemin == e || string.startswith(chemin, str(e) + "."))    return false    end
    end
    if (string.startswith(chemin, "@"))
        return historiqueSeries.INTERNES.find(chemin) != nil && historiqueSeries.liste(config, "ajouts").find(chemin) != nil
    end
    if (historiqueSeries.liste(config, "ajouts").find(chemin) != nil)    return true    end

    var segments = string.split(chemin, ".")
    if (size(segments) < 2)    return false    end      # premier niveau : pas une mesure de capteur
    for s: segments
        if (historiqueSeries.segmentExclu(s))    return false    end
        if (s == "COUNTER" && historiqueSeries.reglageCompteur(config, chemin) == nil)    return false    end
    end
    return true
end
historiqueSeries.admissible = historiqueSeries_admissible

# Chemins des feuilles numeriques admissibles du JSON SENSOR, dans la limite de 'max'
def historiqueSeries_decouvre(donnees, prefixe, liste, max, config)
    for cle: donnees.keys()
        if (size(liste) >= max)    break    end
        if (historiqueSeries.segmentExclu(cle))    continue    end
        var v = donnees[cle]
        var chemin = (prefixe == "" ? cle : prefixe + "." + cle)
        if (isinstance(v, map))
            historiqueSeries.decouvre(v, chemin, liste, max, config)
        elif ((type(v) == "int" || type(v) == "real") && historiqueSeries.admissible(chemin, config))
            liste.push(chemin)
        end
        tasmota.yield()
    end
    return liste
end
historiqueSeries.decouvre = historiqueSeries_decouvre

# Series a enregistrer : decouvertes + 'anciens' encore admissibles (series deja enregistrees : une
# serie absente un instant ne disparait pas) + 'ajouts' ; triees, tronquees a seriesMax.
def historiqueSeries_choisit(donnees, config, anciens)
    import string
    import historiqueFonctions
    var chemins = historiqueSeries.decouvre(donnees, "", [], 64, config)
    var candidats = historiqueSeries.liste(config, "ajouts").copy()
    if (isinstance(anciens, list))    candidats = candidats + anciens    end
    for c: candidats
        if (type(c) == "string" && chemins.find(c) == nil && historiqueSeries.admissible(c, config))    chemins.push(c)    end
    end
    historiqueFonctions.trie(chemins)
    var max = (isinstance(config, map) ? config.find("seriesMax") : nil)
    max = ((type(max) == "int" || type(max) == "real" || type(max) == "string") ? int(max) : nil)
    if (type(max) != "int")    max = 12    end         # absent, null, liste, map : defaut
    if (max < 1)    max = 1    end
    if (size(chemins) > max)
        # Les series deja enregistrees d'abord : une nouvelle ne chasse pas une ancienne (sinon nouvel historique)
        var gardes = []
        for c: chemins    if (isinstance(anciens, list) && anciens.find(c) != nil && size(gardes) < max)    gardes.push(c)    end    end
        for c: chemins    if (gardes.find(c) == nil && size(gardes) < max)    gardes.push(c)    end    end
        if (logFonctions.actif(LOG_LEVEL_DEBUG))
            var ignorees = []
            for c: chemins    if (gardes.find(c) == nil)    ignorees.push(c)    end    end
            logFonctions.log(string.format("HISTORIQUE: %i series au-dela de seriesMax (%i) ignorees : %s !", size(ignorees), max, str(ignorees)), LOG_LEVEL_DEBUG)
        end
        chemins = historiqueFonctions.trie(gardes)
    end
    return chemins
end
historiqueSeries.choisit = historiqueSeries_choisit

# Conversion des compteurs regles, en place, avant enregistrement : energie = cumul / impulsionsParUnite ;
# debit = impulsions depuis la releve precedente, par minute. Premiere releve ou compteur remis a zero
# (redemarrage) -> nil : pas de pic de debit negatif.
def historiqueSeries_convertit(chemins, valeurs, config)
    for i: 0 .. size(chemins) - 1
        var r = historiqueSeries.reglageCompteur(config, chemins[i])
        var v = valeurs[i]
        if (r == nil || v == nil)    continue    end
        var ipu = real(r["impulsionsParUnite"])
        if (r["type"] == "energie")
            valeurs[i] = v / ipu
        else
            var maintenant = tasmota.millis()
            var avant = historiqueSeries.etatCompteurs.find(chemins[i])
            historiqueSeries.etatCompteurs[chemins[i]] = [v, maintenant]
            var minutes = (avant != nil ? (maintenant - avant[1]) / 60000.0 : 0.0)
            valeurs[i] = ((avant == nil || v < avant[0] || minutes <= 0) ? nil : (v - avant[0]) / ipu / minutes)
        end
    end
end
historiqueSeries.convertit = historiqueSeries_convertit

# Retourne le module lors de l'importation
return historiqueSeries
