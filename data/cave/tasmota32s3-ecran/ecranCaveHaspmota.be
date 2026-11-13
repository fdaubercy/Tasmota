# Interface HASPmota de l'ecran 7B de la cave (plan ecran-cave-vues-commandes, A7, 2026-11-13) : dessine le modele de
# ecranCaveFonctions.modele() sur les objets de pages.jsonl (genere depuis outils_docs/atelier_ecrans/cartes/tasmota32s3-cave-ecran/ecran.json
# par l'atelier des ecrans), lu en /json/pages.jsonl (rangement du FS plat par gestionFileFolder). API comme ecranHaspmota.be des
# debits : demarre() -> true si l'ecran est lance ; affiche(m) chaque seconde, m = ecranCaveFonctions.modele() ; seuls les attributs
# changes partent vers LVGL. Compile en .bec par demarrage.compile, non solidifie.
# Objets : page 0 (sur toutes les pages) p0b1 menu, p0b6 horloge, p0b7 barre de l'horloge, p0b8/p0b9 broker et statut, p0b91-94 navigation,
# p0b20/21 bandeau d'alerte, p0b30-38 fenetre du menu ; page 1 accueil (tuiles p1b50/60/70/80 = touches 1 a 4) ;
# page 2 courbes p2b30 (temperature, dixiemes de degre) et p2b40 (humidite) ; page 3 cuve et vide-cave ; page 4 reglages.
# LIENS, COULEURS et BOUTONS sont la copie des cles `liaison`, `couleur_selon`, `couleurs` et `toucher` de ecran.json (le banc banc_ecran_cave les compare).
# Le chart HASPmota n'a que 2 series natives : la serie est ajoutee sur l'objet LVGL dessous (_lv_obj.add_series), comme ecranHaspmota des debits.
# Logs : charte du CLAUDE.md (ecranCaveFonctions.log, seuil `general`), jamais d'info dans affiche() (appelee chaque seconde).
var ecranCaveHaspmota = module("ecranCaveHaspmota")

ecranCaveHaspmota.PAGES = "/json/pages.jsonl"
# Boutons -> action, par une regle HASPmota (« hasp#p1b50#event », evenement « up ») : menu(0|1), demande, annule, confirme, appui(touche), ajuste(cle, pas)
ecranCaveHaspmota.BOUTONS = {
    "p0b1": ["menu", 1],
    "p0b30": ["menu", 0],
    "p0b33": ["menu", 0],
    "p0b34": ["demande"],
    "p0b36": ["confirme"],
    "p0b37": ["annule"],
    "p1b50": ["appui", 1],
    "p1b60": ["appui", 2],
    "p1b70": ["appui", 3],
    "p1b80": ["appui", 4],
    "p3b34": ["appui", 4],
    "p4b12": ["ajuste", "veille", -1],
    "p4b14": ["ajuste", "veille", 1],
    "p4b22": ["ajuste", "extinction", -5],
    "p4b24": ["ajuste", "extinction", 5],
    "p4b32": ["ajuste", "luminosite", -10],
    "p4b34": ["ajuste", "luminosite", 10]
}
# id HASPmota -> liste de [attribut, cle du modele de l'ecran, table de COULEURS ou nil, format ou nil]
ecranCaveHaspmota.LIENS = {
    "p0b6": [["text", "horloge", nil, nil]],
    "p0b7": [["opa", "horlogeBarre", nil, nil]],
    "p0b8": [["bg_color", "broker", "broker", nil]],
    "p0b9": [["text", "statut", nil, nil]],
    "p0b20": [["bg_color", "alerteEtat", "alerteFond", nil]],
    "p0b21": [["text", "alerteTexte", nil, nil], ["text_color", "alerteEtat", "alerteTexte", nil]],
    "p1b11": [["text_color", "temperatureEtat", "doux", nil]],
    "p1b12": [["text", "temperature", nil, nil], ["text_color", "temperatureEtat", "fraicheur", nil]],
    "p1b21": [["text_color", "humiditeEtat", "doux", nil]],
    "p1b22": [["text", "humidite", nil, nil], ["text_color", "humiditeEtat", "fraicheur", nil]],
    "p1b31": [["text_color", "cuveEtat", "doux", nil]],
    "p1b32": [["text", "cuveTexte", nil, nil], ["text_color", "cuveEtat", "fraicheur", nil]],
    "p1b33": [["val", "cuveTaux", nil, nil], ["bg_color10", "cuveEtat", "cuveArc", nil]],
    "p1b41": [["text_color", "videCaveEtat", "doux", nil]],
    "p1b42": [["text", "videCaveTexte", nil, nil], ["text_color", "videCaveEtat", "fraicheur", nil]],
    "p1b50": [["bg_color", "lumieresEtat", "touche", nil]],
    "p1b51": [["text_color", "lumieresEtat", "toucheTexte", nil]],
    "p1b52": [["text", "lumieresTexte", nil, nil], ["text_color", "lumieresEtat", "toucheTexte", nil]],
    "p1b53": [["text", "lumieresIcone", nil, nil], ["text_color", "lumieresEtat", "iconeAmpoule", nil]],
    "p1b60": [["bg_color", "laveLingeEtat", "touche", nil]],
    "p1b61": [["text_color", "laveLingeEtat", "toucheTexte", nil]],
    "p1b62": [["text", "laveLingeTexte", nil, nil], ["text_color", "laveLingeEtat", "toucheTexte", nil]],
    "p1b63": [["text_color", "laveLingeEtat", "icone", nil]],
    "p1b70": [["bg_color", "pompeCuveEtat", "touche", nil]],
    "p1b71": [["text_color", "pompeCuveEtat", "toucheTexte", nil]],
    "p1b72": [["text", "pompeCuveTexte", nil, nil], ["text_color", "pompeCuveEtat", "toucheTexte", nil]],
    "p1b73": [["text_color", "pompeCuveEtat", "icone", nil]],
    "p1b80": [["bg_color", "pompeVideCaveEtat", "touche", nil]],
    "p1b81": [["text_color", "pompeVideCaveEtat", "toucheTexte", nil]],
    "p1b82": [["text", "pompeVideCaveTexte", nil, nil], ["text_color", "pompeVideCaveEtat", "toucheTexte", nil]],
    "p1b83": [["text_color", "pompeVideCaveEtat", "icone", nil]],
    "p1b91": [["arc_color10", "ventilationEtat", "ventilation", nil]],
    "p1b92": [["text_color", "ventilationEtat", "ventilationTxt", nil]],
    "p1b93": [["text", "ventilationTexte", nil, nil], ["text_color", "ventilationEtat", "ventilationDoux", nil]],
    "p2b12": [["text", "temperature", nil, nil], ["text_color", "temperatureEtat", "fraicheur", nil]],
    "p2b22": [["text", "humidite", nil, nil], ["text_color", "humiditeEtat", "fraicheur", nil]],
    "p2b31": [["text", "courbeMaxT", nil, "%d °C"]],
    "p2b41": [["text", "courbeMaxHR", nil, "%d %%"]],
    "p3b12": [["val", "cuveTaux", nil, nil], ["arc_color10", "cuveEtat", "cuveArc", nil]],
    "p3b13": [["text", "cuvePct", nil, nil], ["text_color", "cuveEtat", "fraicheur", nil]],
    "p3b14": [["text", "cuveVolume", nil, nil], ["text_color", "cuveEtat", "doux", nil]],
    "p3b22": [["text", "videCaveTexte", nil, nil], ["text_color", "videCaveEtat", "fraicheur", nil]],
    "p3b23": [["val", "videCaveBarre", nil, nil]],
    "p3b24": [["bg_color", "flotteurHautEtat", "pastille", nil]],
    "p3b26": [["text", "flotteurHautTexte", nil, nil], ["text_color", "flotteurHautEtat", "flotteurDoux", nil]],
    "p3b28": [["bg_color", "flotteurBasEtat", "pastille", nil]],
    "p3b30": [["text", "flotteurBasTexte", nil, nil], ["text_color", "flotteurBasEtat", "flotteurDoux", nil]],
    "p3b33": [["text", "pompeVideCaveTexte", nil, nil], ["text_color", "pompeVideCaveEtat", "appareilDoux", nil]],
    "p3b34": [["text", "pompeBoutonTexte", nil, nil], ["bg_color", "pompeVideCaveEtat", "touche", nil], ["text_color", "pompeVideCaveEtat", "toucheTexte", nil]],
    "p4b13": [["text", "reglages.veille", nil, nil]],
    "p4b23": [["text", "reglages.extinction", nil, nil]],
    "p4b33": [["text", "reglages.luminosite", nil, nil]]
}
ecranCaveHaspmota.COULEURS = {
    "fraicheur": {"frais": "#E8EDF2", "perime": "#5B6B7C"},
    "doux": {"frais": "#9FB3C8", "perime": "#5B6B7C"},
    "touche": {"ON": "#3FA7FF", "OFF": "#1F2B38", "perime": "#18222D", "inconnu": "#18222D"},
    "toucheTexte": {"ON": "#06121F", "OFF": "#E8EDF2", "perime": "#5B6B7C", "inconnu": "#5B6B7C"},
    "ventilationTxt": {"ON": "#E8EDF2", "OFF": "#E8EDF2", "perime": "#5B6B7C", "inconnu": "#5B6B7C"},
    "ventilationDoux": {"ON": "#9FB3C8", "OFF": "#9FB3C8", "perime": "#5B6B7C", "inconnu": "#5B6B7C"},
    "appareilDoux": {"ON": "#9FB3C8", "OFF": "#9FB3C8", "perime": "#5B6B7C", "inconnu": "#5B6B7C"},
    "flotteurDoux": {"actif": "#9FB3C8", "libre": "#9FB3C8", "perime": "#5B6B7C"},
    "icone": {"ON": "#06121F", "OFF": "#9FB3C8", "perime": "#5B6B7C", "inconnu": "#5B6B7C"},
    "iconeAmpoule": {"ON": "#FFD54A", "OFF": "#9FB3C8", "perime": "#5B6B7C", "inconnu": "#5B6B7C"},
    "ventilation": {"ON": "#3FA7FF", "OFF": "#5B6B7C", "perime": "#3A4552", "inconnu": "#3A4552"},
    "alerteFond": {"aucune": "#10161E", "alerte": "#D93636"},
    "alerteTexte": {"aucune": "#10161E", "alerte": "#FFFFFF"},
    "pastille": {"actif": "#3FA7FF", "libre": "#2B3948", "perime": "#3A4552"},
    "broker": {"ok": "#3FD08A", "absent": "#FF5A5A"},
    "cuveArc": {"frais": "#3FA7FF", "perime": "#5B6B7C"}
}
ecranCaveHaspmota.COURBES = {"p2b30": "#FFA53F", "p2b40": "#3FA7FF"}      # couleur de la serie de chaque chart (ecran.json, liaison.couleurs)
ecranCaveHaspmota.NAV = {"p0b91": 1, "p0b92": 2, "p0b93": 3, "p0b94": 4}  # bouton de navigation -> page
ecranCaveHaspmota.APPAREILS = {"lumieres": ["power3", "Allumées", "Éteintes"], "laveLinge": ["power5", "En marche", "Arrêt"],
                               "pompeCuve": ["power4", "En marche", "Arrêt"], "ventilation": ["power2", "En marche", "Arrêt"]}
ecranCaveHaspmota.REFUS_MS = 3000       # affichage du refus d'une touche (« Touche refusee »)
ecranCaveHaspmota.PAS_ROTATION = 450    # ventilation : dixiemes de degre ajoutes a chaque affiche() tant que POWER2 est ON
ecranCaveHaspmota.VENTILATEUR = "p1b91" # objet de l'icone de ventilation (tourne par transform_rotation)

ecranCaveHaspmota.cache = {}       # "p1b13.text" -> valeur deja ecrite (objets neufs : cache vide)
ecranCaveHaspmota.menuEtat = 0     # 0 ferme, 1 ouvert, 2 confirmation du redemarrage
ecranCaveHaspmota.refusJusqua = 0  # millis jusqu'auquel le statut dit « Touche refusee »
ecranCaveHaspmota.angle = 0        # rotation courante de l'icone de ventilation
ecranCaveHaspmota.series = {}      # id du chart -> serie LVGL
ecranCaveHaspmota.pousses = 0      # points de ecranFonctions.histo deja pousses sur les courbes

# Ecrit l'attribut `attr` de l'objet HASPmota `id` seulement s'il a change ; objet absent : rien
def ecranCaveHaspmota_ecris(id, attr, val)
    import global
    import ecranCaveHaspmota
    var cle = id + "." + attr
    if (ecranCaveHaspmota.cache.find(cle) == val)    return    end
    var o = global.(id)
    if (o == nil)    return    end
    o.(attr) = val
    ecranCaveHaspmota.cache[cle] = val
end
ecranCaveHaspmota.ecris = ecranCaveHaspmota_ecris

# ---- Valeurs de l'ecran d'apres le modele (pur : aucun acces a LVGL) ----
# Etat d'une valeur ON/OFF : "ON" | "OFF" | "perime" | "inconnu" (jamais recue)
def ecranCaveHaspmota_etat(m, cle)
    var e = m["valeurs"].find(cle)
    if (e == nil)    return "inconnu"    end
    if (e["perime"])    return "perime"    end
    return e["valeur"] == "ON" ? "ON" : "OFF"
end
ecranCaveHaspmota.etat = ecranCaveHaspmota_etat

# "frais" si toutes les `cles` sont recues et non perimees, "perime" sinon
def ecranCaveHaspmota_fraicheur(m, cles)
    for c: cles
        var e = m["valeurs"].find(c)
        if (e == nil || e["perime"])    return "perime"    end
    end
    return "frais"
end
ecranCaveHaspmota.fraicheur = ecranCaveHaspmota_fraicheur

# 2520 -> "2 520"
def ecranCaveHaspmota_milliers(n)
    var s = str(int(n))
    var r = ""
    while (size(s) > 3)
        r = " " + s[-3 ..] + r
        s = s[0 .. -4]
    end
    return s + r
end
ecranCaveHaspmota.milliers = ecranCaveHaspmota_milliers

# 14.25 -> "14,3" (virgule decimale)
def ecranCaveHaspmota_decimal(x)
    import string
    return string.replace(string.format("%.1f", x), ".", ",")
end
ecranCaveHaspmota.decimal = ecranCaveHaspmota_decimal

# Valeur numerique d'une cle du modele (nil si jamais recue ou pas un nombre)
def ecranCaveHaspmota_nombre(m, cle)
    var e = m["valeurs"].find(cle)
    var v = e == nil ? nil : e["valeur"]
    return (type(v) == "int" || type(v) == "real") ? v : nil
end
ecranCaveHaspmota.nombre = ecranCaveHaspmota_nombre

# Cles du `modele` de ecran.json (hors historiques) calculees d'apres m = ecranCaveFonctions.modele() ; `maintenant` = millis
def ecranCaveHaspmota_valeurs(m, maintenant)
    import ecranCaveHaspmota
    var f = ecranCaveHaspmota
    var v = {}
    var vals = m["valeurs"]
    v["broker"] = m["broker"] ? "ok" : "absent"
    v["horlogeBarre"] = m["broker"] ? 0 : 255
    var perime = false
    for e: vals    if (e["perime"])    perime = true    end    end
    v["statut"] = !m["broker"] ? "broker absent" : size(vals) == 0 ? "en attente des données" : perime ? "données périmées" : "données à jour"
    if (maintenant < f.refusJusqua)    v["statut"] = "touche refusée : état inconnu"    end
    v["alerteEtat"] = size(m["alertes"]) > 0 ? "alerte" : "aucune"
    v["alerteTexte"] = m["alertes"].concat(" ; ")
    var t = f.nombre(m, "temperature")
    var h = f.nombre(m, "humidite")
    v["temperature"] = t == nil ? "-- °C" : f.decimal(t) + " °C"
    v["humidite"] = h == nil ? "-- %" : str(int(h + 0.5)) + " %"
    v["temperatureEtat"] = f.fraicheur(m, ["temperature"])
    v["humiditeEtat"] = f.fraicheur(m, ["humidite"])
    var taux = f.nombre(m, "taux")
    var vol = f.nombre(m, "volume")
    var pct = taux == nil ? 0 : int(taux * 100 + 0.5)
    if (pct > 100)    pct = 100    end
    v["cuveTaux"] = pct
    v["cuvePct"] = taux == nil ? "-- %" : str(pct) + " %"
    v["cuveVolume"] = vol == nil ? "-- L" : f.milliers(vol) + " L"
    v["cuveTexte"] = v["cuvePct"] + "  ·  " + v["cuveVolume"]
    v["cuveEtat"] = f.fraicheur(m, ["taux", "volume"])
    # vide-cave : 3 paliers d'apres les flotteurs (ON = atteint) ; haut atteint = plein, bas seul = moyen, aucun = bas
    var bas = f.etat(m, "niveauBas")
    var haut = f.etat(m, "niveauHaut")
    v["videCaveEtat"] = f.fraicheur(m, ["niveauBas", "niveauHaut"])
    var connu = v["videCaveEtat"] == "frais"
    v["videCaveBarre"] = !connu ? 0 : haut == "ON" ? 100 : bas == "ON" ? 50 : 0
    v["videCaveTexte"] = !connu ? "Inconnu" : haut == "ON" ? "Niveau haut" : bas == "ON" ? "Niveau moyen" : "Niveau bas"
    v["flotteurHautEtat"] = haut == "ON" ? "actif" : haut == "OFF" ? "libre" : "perime"
    v["flotteurBasEtat"] = bas == "ON" ? "actif" : bas == "OFF" ? "libre" : "perime"
    v["flotteurHautTexte"] = haut == "ON" ? "Atteint" : haut == "OFF" ? "Libre" : "--"
    v["flotteurBasTexte"] = bas == "ON" ? "Atteint" : bas == "OFF" ? "Libre" : "--"
    # appareils : texte d'apres l'etat de la touche ; « Périmé » / « Inconnu » sinon
    for n: f.APPAREILS.keys()
        var a = f.APPAREILS[n]
        var s = f.etat(m, a[0])
        v[n + "Etat"] = s
        v[n + "Texte"] = s == "ON" ? a[1] : s == "OFF" ? a[2] : s == "perime" ? "Périmé" : "Inconnu"
    end
    # pompe du vide-cave : touche 4 = POWER1 ; texte d'apres Pompe / Manuel du capteur
    var p = f.etat(m, "power1")
    v["pompeVideCaveEtat"] = p
    var pompe = f.etat(m, "pompe")
    var marche = pompe == "inconnu" ? p == "ON" : pompe == "ON"
    var manuel = vals.find("manuel") != nil && vals["manuel"]["valeur"] == "ON"
    v["pompeVideCaveTexte"] = p == "perime" ? "Périmé" : p == "inconnu" ? "Inconnu" : (marche ? "Marche" : "Arrêt") + " · " + (manuel ? "manuel" : "auto")
    v["pompeBoutonTexte"] = p == "ON" ? "Arrêter la marche" : "Forcer la marche"
    # glyphes Material Design de montserrat-28 (UTF-8 en \x : le lexeur Berry n'a pas de \u) : ampoule allumee U+E6E8 (lightbulb-on),
    # sinon U+E335 (lightbulb ; perime et inconnu compris)
    v["lumieresIcone"] = v["lumieresEtat"] == "ON" ? "\xEE\x9B\xA8" : "\xEE\x8C\xB5"
    return v
end
ecranCaveHaspmota.valeurs = ecranCaveHaspmota_valeurs

# ---- Reglages de l'ecran (page 4) ----
def ecranCaveHaspmota_reglages(v)
    import ecranFonctions
    for cle: ["veille", "extinction", "luminosite"]
        var n = ecranFonctions.reglage(cle)
        v["reglages." + cle] = (n == 0 && cle != "luminosite") ? "jamais" : str(n) + " " + ecranFonctions.BORNES[cle][3]
    end
end
ecranCaveHaspmota.reglages = ecranCaveHaspmota_reglages

# Bouton - / + : reglage `cle` change de `pas`, borne, ecriture du persist differee (un appui = un appel)
def ecranCaveHaspmota_ajuste(cle, pas)
    import ecranFonctions
    var b = ecranFonctions.BORNES.find(cle)
    if (b == nil)    return false    end
    var n = ecranFonctions.reglage(cle) + pas
    if (n < b[0])    n = b[0]    end
    if (n > b[1])    n = b[1]    end
    return ecranFonctions.regle(cle, n, nil, true)
end
ecranCaveHaspmota.ajuste = ecranCaveHaspmota_ajuste

# ---- Menu (page 0) : ids 30-34 ouvert, 30-33 + 35-38 en confirmation ----
def ecranCaveHaspmota_montre()
    import global
    import ecranCaveHaspmota
    var visibles = ecranCaveHaspmota.menuEtat == 1 ? [30, 31, 32, 33, 34] : ecranCaveHaspmota.menuEtat == 2 ? [30, 31, 32, 33, 35, 36, 37, 38] : []
    for i: 30 .. 38
        var o = global.("p0b" + str(i))
        if (o != nil)    o.hidden = visibles.find(i) == nil ? 1 : 0    end
    end
end
ecranCaveHaspmota.montre = ecranCaveHaspmota_montre

# menu(1) ouvre la fenetre, menu(0) la referme (et annule une confirmation)
def ecranCaveHaspmota_menu(ouvert)
    import ecranCaveHaspmota
    ecranCaveHaspmota.menuEtat = ouvert ? 1 : 0
    ecranCaveHaspmota.montre()
end
ecranCaveHaspmota.menu = ecranCaveHaspmota_menu

# « Redemarrer le serveur » : montre la confirmation, ne pousse RIEN
def ecranCaveHaspmota_demandeRedemarrage()
    import ecranCaveHaspmota
    ecranCaveHaspmota.menuEtat = 2
    ecranCaveHaspmota.montre()
end
ecranCaveHaspmota.demandeRedemarrage = ecranCaveHaspmota_demandeRedemarrage

def ecranCaveHaspmota_annuleRedemarrage()
    import ecranCaveHaspmota
    ecranCaveHaspmota.menuEtat = 1
    ecranCaveHaspmota.montre()
end
ecranCaveHaspmota.annuleRedemarrage = ecranCaveHaspmota_annuleRedemarrage

# Appui sur la touche `n` : « refuse » (etat inconnu ou perime) se voit dans le statut pendant REFUS_MS
def ecranCaveHaspmota_appui(n)
    import ecranCaveFonctions
    import ecranCaveHaspmota
    var r = ecranCaveFonctions.touche(n)
    if (r == "refuse")    ecranCaveHaspmota.refusJusqua = tasmota.millis() + ecranCaveHaspmota.REFUS_MS    end
    return r
end
ecranCaveHaspmota.appui = ecranCaveHaspmota_appui

# « Confirmer » : touche 5 (redemarrage du serveur, jamais relancee) puis fermeture du menu
def ecranCaveHaspmota_confirme()
    import ecranCaveHaspmota
    ecranCaveHaspmota.appui(5)
    ecranCaveHaspmota.menu(0)
end
ecranCaveHaspmota.confirme = ecranCaveHaspmota_confirme

# Regle d'un bouton (declencheur « hasp#p1b50#event ») : un appui relache lance l'action de BOUTONS
def ecranCaveHaspmota_bouton(valeur, declencheur)
    import string
    import ecranCaveHaspmota
    if (valeur != "up")    return    end
    var a = ecranCaveHaspmota.BOUTONS.find(string.tolower(string.split(declencheur, "#")[1]))
    if (a == nil)    return    end
    if (a[0] == "menu")    ecranCaveHaspmota.menu(a[1])
    elif (a[0] == "demande")    ecranCaveHaspmota.demandeRedemarrage()
    elif (a[0] == "annule")    ecranCaveHaspmota.annuleRedemarrage()
    elif (a[0] == "confirme")    ecranCaveHaspmota.confirme()
    elif (a[0] == "appui")    ecranCaveHaspmota.appui(a[1])
    elif (a[0] == "ajuste")    ecranCaveHaspmota.ajuste(a[1], a[2])
    end
end
ecranCaveHaspmota.bouton = ecranCaveHaspmota_bouton

# ---- Courbes (page 2) : une serie par chart, alimentee par ecranFonctions.echantillonne ----
def ecranCaveHaspmota_prepareCourbes()
    import global
    import lv
    import ecranCaveHaspmota
    ecranCaveHaspmota.series = {}
    ecranCaveHaspmota.pousses = 0
    for id: ecranCaveHaspmota.COURBES.keys()
        var c = global.(id)
        if (c == nil)    continue    end
        var o = c._lv_obj
        o.set_style_size(0, 0, lv.PART_INDICATOR)
        o.set_style_line_width(3, lv.PART_ITEMS)
        ecranCaveHaspmota.series[id] = o.add_series(c.parse_color(ecranCaveHaspmota.COURBES[id]), lv.CHART_AXIS_PRIMARY_Y)
    end
end
ecranCaveHaspmota.prepareCourbes = ecranCaveHaspmota_prepareCourbes

# Un point (temperature en dixiemes de degre, humidite en %) toutes les 30 s ; nil si la valeur est inconnue ou perimee.
# Rend les hauts d'axe : temperature 40 °C au moins, par pas de 10 ; humidite 100.
def ecranCaveHaspmota_echantillonne(m)
    import ecranFonctions
    import ecranCaveHaspmota
    var t = ecranCaveHaspmota.nombre(m, "temperature")
    var h = ecranCaveHaspmota.nombre(m, "humidite")
    if (m["valeurs"].find("temperature") != nil && m["valeurs"]["temperature"]["perime"])    t = nil    end
    if (m["valeurs"].find("humidite") != nil && m["valeurs"]["humidite"]["perime"])    h = nil    end
    ecranFonctions.echantillonne([t == nil ? nil : int(t * 10 + 0.5), h == nil ? nil : int(h + 0.5)])
    var haut = 0
    if (ecranFonctions.histo != nil)
        for x: ecranFonctions.histo[0]    if (x != nil && x > haut)    haut = x    end    end
    end
    var maxT = (haut + 99) / 100 * 10
    return [maxT < 40 ? 40 : maxT, 100]
end
ecranCaveHaspmota.echantillonne = ecranCaveHaspmota_echantillonne

# Pousse sur les courbes les points pas encore traces et regle les hauts d'axe
def ecranCaveHaspmota_trace(maxi)
    import global
    import lv
    import ecranFonctions
    import ecranCaveHaspmota
    var h = ecranFonctions.histo
    if (h == nil || size(ecranCaveHaspmota.series) == 0)    return    end
    var n = ecranFonctions.points - ecranCaveHaspmota.pousses
    if (n <= 0)    return    end
    var t = size(h[0])
    if (n > t)    n = t    end
    var ids = ["p2b30", "p2b40"]
    for i: 0 .. 1
        var s = ecranCaveHaspmota.series.find(ids[i])
        if (s == nil)    continue    end
        var o = global.(ids[i])._lv_obj
        o.set_axis_range(lv.CHART_AXIS_PRIMARY_Y, 0, i == 0 ? maxi[0] * 10 : maxi[1])
        for k: t - n .. t - 1
            var v = h[i][k]
            o.set_next_value(s, v == nil ? lv.CHART_POINT_NONE : v)
        end
    end
    ecranCaveHaspmota.pousses = ecranFonctions.points
end
ecranCaveHaspmota.trace = ecranCaveHaspmota_trace

# ---- Demarrage et affichage ----
def ecranCaveHaspmota_demarre()
    import path
    import ecranCaveHaspmota
    import ecranCaveFonctions
    if (!path.exists(ecranCaveHaspmota.PAGES))
        ecranCaveFonctions.log("ECRAN_CAVE_HASPMOTA_ERREUR: " + ecranCaveHaspmota.PAGES + " absent (pages.jsonl du dossier de la carte) : ecran vide !", LOG_LEVEL_ERREUR)
        return false
    end
    try
        import display
        if (!display.started())
            ecranCaveFonctions.log("ECRAN_CAVE_HASPMOTA_ERREUR: ecran non demarre (display.ini, preinit.be) !", LOG_LEVEL_ERREUR)
            return false
        end
        import haspmota
        haspmota.start(ecranCaveHaspmota.PAGES)
        ecranCaveHaspmota.cache = {}        # objets neufs : tout reecrire
        ecranCaveHaspmota.menuEtat = 0
        ecranCaveHaspmota.angle = 0
        ecranCaveHaspmota.prepareCourbes()
        for id: ecranCaveHaspmota.BOUTONS.keys()
            tasmota.add_rule("hasp#" + id + "#event", ecranCaveHaspmota.bouton, "ecranCaveHaspmota")
        end
        ecranCaveHaspmota.montre()
        return true
    except .. as e, m
        ecranCaveFonctions.log("ECRAN_CAVE_HASPMOTA_ERREUR: HASPmota non demarre : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    return false
end
ecranCaveHaspmota.demarre = ecranCaveHaspmota_demarre

# Ecrit le modele : liaisons, boutons de navigation actifs, horloge, ventilation qui tourne, courbes. Pages non creees : rien.
def ecranCaveHaspmota_affiche(m)
    import global
    import string
    import haspmota
    import ecranCaveHaspmota
    if (global.p1b50 == nil)    return    end
    var f = ecranCaveHaspmota
    var v = f.valeurs(m, tasmota.millis())
    var maxi = f.echantillonne(m)
    v["courbeMaxT"] = maxi[0]
    v["courbeMaxHR"] = maxi[1]
    var t = tasmota.rtc()["local"]
    v["horloge"] = t < 1700000000 ? "--:--" : tasmota.strftime("%H:%M", t)    # horloge pas encore synchronisee
    f.reglages(v)
    for id: f.LIENS.keys()
        for b: f.LIENS[id]
            var x = v.find(b[1])
            if (x == nil)    continue    end
            if (b[2] != nil)    x = f.COULEURS[b[2]].find(str(x))
            elif (b[3] != nil)    x = string.format(b[3], x)
            end
            if (x != nil)    f.ecris(id, b[0], x)    end
        end
    end
    for id: f.NAV.keys()
        var actif = haspmota.lvh_page_cur_idx == f.NAV[id]
        f.ecris(id, "bg_color", actif ? "#3FA7FF" : "#1F2B38")
        f.ecris(id, "text_color", actif ? "#06121F" : "#E8EDF2")
    end
    if (v["ventilationEtat"] == "ON")    f.angle = (f.angle + f.PAS_ROTATION) % 3600    end
    f.ecris(f.VENTILATEUR, "transform_rotation", f.angle)
    f.trace(maxi)
end
ecranCaveHaspmota.affiche = ecranCaveHaspmota_affiche

# Retourne le module lors de l'importation
return ecranCaveHaspmota
