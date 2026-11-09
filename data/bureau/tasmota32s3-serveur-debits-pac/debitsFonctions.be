# Fonctions du module metier debits : 6 debitmetres a impulsions de la nourrice de chauffage
# (plan tasks/plans/debitmetres-chauffage.md, analyse outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md).
# Voies 1-2 : pilote FlowRateMeter (GPIO 4, 5), lues dans son JSON (cle "Débit" en firmware francais).
# Voies 3-6 : Counter1-4 (GPIO 6, 7, 15, 16), debit = impulsions / duree de la fenetre / K.
# Attention : le Rate du FlowRateMeter (voies 1-2) suit la derniere periode (moyenne exponentielle du pilote), les
# voies 3-6 sont une moyenne sur la fenetre ; a comparer sur banc (A6) si un debit pulse fausse les proportions.
# Un seul facteur K par voie (Hz par L/min, YF-B2 : F = 11 x Q), dans le persist : le calibrage du FlowRateMeter
# est force a 1000 au demarrage (controleDebits.init), sinon il y aurait deux etalonnages pour la meme voie.
# Compile en .bec par demarrage.compile(["debitsFonctions"], "modules.debits"), importe par controleDebits.be.
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).
var debitsFonctions = module("debitsFonctions")

debitsFonctions.NB_VOIES = 6
debitsFonctions.K_DEFAUT = 11.0           # YF-B2 : F (Hz) = 11 x Q (L/min)
debitsFonctions.FENETRE_DEFAUT = 10       # s entre deux mesures
debitsFonctions.VEILLE_DEFAUT = 5         # min sans toucher l'ecran avant sa mise en veille (0 = jamais)
# FlowRateMeter a calibrage 1000 : Rate = (1e6 / 60 / 2) / periode_us x 1000 = f / 0,12 (xsns_96 FlowRateMeterGetValue)
debitsFonctions.HZ_PAR_RATE = 0.12
debitsFonctions.CLE_FLOWRATE = ["Débit", "Flowrate"]    # D_FLOWRATEMETER_NAME : fr_FR.h, en_GB.h

debitsFonctions.debits = [nil, nil, nil, nil, nil, nil]   # L/min, nil = voie sans mesure
debitsFonctions.releve = nil                             # {"t": ms, "c": [4 compteurs]} de la mesure precedente
debitsFonctions.MUET_DEFAUT = 10                         # min a 0 L/min avant « capteur muet » (decision du 2026-11-08)
debitsFonctions.zero = [nil, nil, nil, nil, nil, nil]     # ms de la 1re mesure a 0 L/min de la serie en cours, par voie
debitsFonctions.muets = [false, false, false, false, false, false]
debitsFonctions.ecranMs = nil                            # ms de la derniere ecriture de l'ecran (ReglageDebits)

# Log du module sous le seuil `general` (ReglageLog general <niveau>) ; niveau = constante LOG_LEVEL_*
def debitsFonctions_log(msg, niveau)
    logFonctions.log(msg, niveau)
end
debitsFonctions.log = debitsFonctions_log

# Reglages du module, valeurs par defaut si le persist ne les porte pas encore
def debitsFonctions_fenetre()
    import debitsFonctions
    # contains d'abord : find("debits", {}) allouerait une map a chaque seconde
    return modules.contains("debits") ? modules["debits"].find("fenetre", debitsFonctions.FENETRE_DEFAUT) : debitsFonctions.FENETRE_DEFAUT
end
debitsFonctions.fenetre = debitsFonctions_fenetre

# Minutes sans toucher l'ecran avant sa mise en veille (HASPmota : 25 % puis eteint 30 s plus tard), 0 = jamais ;
# persist modules.debits.veille, valeur hors 0..120 ignoree (persist edite a la main)
def debitsFonctions_veille()
    import debitsFonctions
    var v = modules.contains("debits") ? modules["debits"].find("veille", debitsFonctions.VEILLE_DEFAUT) : debitsFonctions.VEILLE_DEFAUT
    return (type(v) == "int" && v >= 0 && v <= 120) ? v : debitsFonctions.VEILLE_DEFAUT
end
debitsFonctions.veille = debitsFonctions_veille

# Applique la veille a HASPmota (lu a chaque passage de haspmota.auto_dimming) ; rien sans ecran demarre
def debitsFonctions_appliqueVeille()
    import global
    import debitsFonctions
    if (global.p1b13 == nil)    return    end
    import haspmota
    var v = debitsFonctions.veille()
    haspmota.dimming_time = v
    # A 0, auto_dimming sort d'emblee et ne rallume plus : un ecran deja assombri resterait noir
    if (v == 0 && haspmota.dimming_state < 100)
        if (haspmota.dimmed_panel != nil)    haspmota.dimmed_panel.stop()    haspmota.dimmed_panel = nil    end
        haspmota.dimming_state = 100
        import display
        display.dimmer(display.dimmer())
    end
end
debitsFonctions.appliqueVeille = debitsFonctions_appliqueVeille

# Entree du persist qui porte la broche, le nom et le K de la voie i (0 a 5), nil si absente :
# voies 1-2 = environnement.debitmetres.debitmetre1-2 (FlowRateMeter), voies 3-6 = environnement.compteurs.compteur1-4
def debitsFonctions_entree(i)
    var env = modules.find("debits", {}).find("environnement", {})
    var e = (i < 2) ? env.find("debitmetres", {}).find("debitmetre" + str(i + 1)) : env.find("compteurs", {}).find("compteur" + str(i - 1))
    return isinstance(e, map) ? e : nil
end
debitsFonctions.entree = debitsFonctions_entree

# Voie i (0 a 5) -> {"nom", "k"}
def debitsFonctions_voie(i)
    import debitsFonctions
    var v = debitsFonctions.entree(i)
    if (v == nil)    v = {}    end
    return {"nom": v.find("nom", "Départ " + str(i + 1)), "k": real(v.find("k", debitsFonctions.K_DEFAUT))}
end
debitsFonctions.voie = debitsFonctions_voie

# Debits des 6 voies (L/min, nil = sans mesure) :
#   rates  : Rate du FlowRateMeter (liste, nombre seul si une voie configuree, ou nil)
#   avant, apres : 4 compteurs (gpio.counter_read, nil = compteur non configure) ; ms : duree entre les deux
#   ks     : facteur K des 6 voies
def debitsFonctions_calcule(rates, avant, apres, ms, ks)
    import debitsFonctions
    if (rates != nil && !isinstance(rates, list))    rates = [rates]    end
    var d = []
    for i: 0 .. 1
        var r = (rates != nil && i < size(rates)) ? rates[i] : nil
        d.push(r == nil ? nil : real(r) * debitsFonctions.HZ_PAR_RATE / ks[i])
    end
    for i: 0 .. 3
        var a = (avant != nil ? avant[i] : nil)
        var b = apres[i]
        # shortcut: un compteur remis a zero (Counter<n> 0) ou passe par 2^31 perd une fenetre, sans plus
        if (a == nil || b == nil || ms <= 0 || b < a)
            d.push(nil)
        else
            d.push(real(b - a) * 1000 / ms / ks[i + 2])
        end
    end
    return d
end
debitsFonctions.calcule = debitsFonctions_calcule

# Somme des voies mesurees (nil si aucune)
def debitsFonctions_total(d)
    var s = nil
    for q: d
        if (q != nil)    s = (s == nil ? 0.0 : s) + q    end
    end
    return s
end
debitsFonctions.total = debitsFonctions_total

# Rate du FlowRateMeter dans le JSON des capteurs (texte de tasmota.read_sensors), ou nil
def debitsFonctions_rates(texte)
    import json
    import debitsFonctions
    var j = (texte != nil ? json.load(texte) : nil)
    if (!isinstance(j, map))    return nil    end
    for cle: debitsFonctions.CLE_FLOWRATE
        if (isinstance(j.find(cle), map))    return j[cle].find("Rate")    end
    end
    return nil
end
debitsFonctions.rates = debitsFonctions_rates

# Mesure des 6 voies, appelee par controleDebits.every_second toutes les `fenetre` secondes
def debitsFonctions_mesure()
    import debitsFonctions
    var t = tasmota.millis()
    var c = []
    for i: 0 .. 3    c.push(gpio.counter_read(i))    end
    var ks = []
    for i: 0 .. debitsFonctions.NB_VOIES - 1    ks.push(debitsFonctions.voie(i)["k"])    end
    var r = debitsFonctions.releve
    var rates = debitsFonctions.rates(tasmota.read_sensors())
    # Premiere mesure : pas de releve precedent, les voies 3-6 restent sans mesure
    debitsFonctions.debits = debitsFonctions.calcule(rates, r != nil ? r["c"] : nil, c, r != nil ? t - r["t"] : 0, ks)
    debitsFonctions.releve = {"t": t, "c": c}
    debitsFonctions.suitMuets(debitsFonctions.debits, t)
    var e = tasmota.millis()
    debitsFonctions.ecran()
    debitsFonctions.ecranMs = tasmota.millis() - e    # duree d'une ecriture de l'ecran (plan A5, essai de charge A6)
    if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS)
        debitsFonctions.log("MESURE_DEBITS: rates=" + str(rates) + " compteurs=" + str(c) + " debits=" + str(debitsFonctions.debits), LOG_LEVEL_DEBUG_PLUS)
    end
end
debitsFonctions.mesure = debitsFonctions_mesure

# Capteur muet : voie mesuree a 0 L/min sans interruption depuis `muet` min (persist modules.debits.muet, defaut 10) ;
# une impulsion la remet a l'etat normal, une voie sans mesure (nil) ne change rien. Erreur journalisee au passage seulement.
# shortcut: un robinet ferme plus de 10 min est aussi signale muet ; le distinguer demanderait un capteur de temperature
def debitsFonctions_suitMuets(d, t)
    import debitsFonctions
    var m = (modules.contains("debits") ? modules["debits"].find("muet", debitsFonctions.MUET_DEFAUT) : debitsFonctions.MUET_DEFAUT)
    # persist edite a la main : 0, negatif ou texte rendrait toute voie a l'arret muette, ou ferait lever mesure()
    if ((type(m) != "int" && type(m) != "real") || m < 1)    m = debitsFonctions.MUET_DEFAUT    end
    var seuil = m * 60000
    for i: 0 .. debitsFonctions.NB_VOIES - 1
        if (d[i] == nil)    continue    end
        if (d[i] > 0)
            debitsFonctions.zero[i] = nil
        elif (debitsFonctions.zero[i] == nil)
            debitsFonctions.zero[i] = t
        end
        var muet = debitsFonctions.zero[i] != nil && t - debitsFonctions.zero[i] >= seuil
        if (muet && !debitsFonctions.muets[i])
            debitsFonctions.log("CAPTEUR_MUET_ERREUR: voie " + str(i + 1) + " (" + debitsFonctions.voie(i)["nom"] + ") sans impulsion depuis " + str(seuil / 60000) + " min : capteur, cable ou depart ferme !", LOG_LEVEL_ERREUR)
        elif (!muet && debitsFonctions.muets[i])
            debitsFonctions.log("CAPTEUR_MUET: voie " + str(i + 1) + " de nouveau mesuree !", LOG_LEVEL_DEBUG)
        end
        debitsFonctions.muets[i] = muet
    end
end
debitsFonctions.suitMuets = debitsFonctions_suitMuets

# Debit hors de la plage du capteur (YF-B2 : 1 a 25 L/min) mais non nul : valeur imprecise
def debitsFonctions_imprecis(q)
    return q != nil && q > 0 && q < 1
end
debitsFonctions.imprecis = debitsFonctions_imprecis

# Bloc DEBITS du JSON SENSOR : D1 a D6 et Total en L/min, null = voie sans mesure ;
# Imprecis = numeros des voies entre 0 et 1 L/min ; Muets = numeros des voies a 0 depuis `muet` min
def debitsFonctions_json()
    import debitsFonctions
    import string
    var d = debitsFonctions.debits
    var s = ',"DEBITS":{'
    var imprecis = []
    var muets = []
    for i: 0 .. size(d) - 1
        s += string.format('"D%d":%s,', i + 1, d[i] == nil ? "null" : string.format("%.2f", d[i]))
        if debitsFonctions.imprecis(d[i])    imprecis.push(i + 1)    end
        if debitsFonctions.muets[i]    muets.push(i + 1)    end
    end
    var tot = debitsFonctions.total(d)
    return s + '"Total":' + (tot == nil ? "null" : string.format("%.2f", tot)) + ',"Imprecis":' + str(imprecis) + ',"Muets":' + str(muets) + "}"
end
debitsFonctions.json = debitsFonctions_json

# Lignes de la page d'accueil : nom, debit, part du total (l'equilibrage se regle en proportions)
def debitsFonctions_lignesWeb()
    import debitsFonctions
    import string
    var d = debitsFonctions.debits
    var tot = debitsFonctions.total(d)
    var lignes = []
    for i: 0 .. size(d) - 1
        var q = d[i]
        var v
        if (q == nil)
            v = "-,--"
        elif debitsFonctions.muets[i]
            v = "0.00 L/min (capteur muet ?)"
        elif debitsFonctions.imprecis(q)
            v = string.format("%.2f L/min (&lt; 1 : imprécis)", q)    # sous la plage du YF-B2 (1-25 L/min)
        else
            v = string.format("%.2f L/min", q)
        end
        if (q != nil && tot != nil && tot > 0)    v += string.format(" · %d %%", int(q * 100 / tot + 0.5))    end
        # Nom saisi par ReglageDebits : echappe, sinon un '<' ou un '{m}' casserait le tableau de l'accueil
        var nom = string.replace(string.replace(string.replace(debitsFonctions.voie(i)["nom"], "&", "&amp;"), "<", "&lt;"), "{", "&#123;")
        lignes.push(string.format("{s}%s{m}%s{e}", nom, v))
    end
    lignes.push(string.format("{s}Total{m}%s{e}", tot == nil ? "-,--" : string.format("%.2f L/min", tot)))
    return lignes
end
debitsFonctions.lignesWeb = debitsFonctions_lignesWeb

# Ecran TFT (LVGL, HASPmota) : page /json/pages.jsonl du dossier de la carte (modele B de outils_docs/chauffage/ecran/),
# rangee dans /json/ au demarrage par gestionFileFolder ; voie n = objets p1b<10n+1> nom, +2 barre, +3 debit, +4 part
debitsFonctions.PAGES = "/json/pages.jsonl"
debitsFonctions.COULEURS = {"normal": "#E8EDF2", "imprecis": "#F2B84B", "arret": "#6C7A89", "absent": "#FF6B6B", "muet": "#FF6B6B"}

# Affichage d'une voie : [debit, part, barre 0-100 (relative a la plus forte voie), etat]
def debitsFonctions_etatVoie(q, tot, max, muet)
    import debitsFonctions
    import string
    if (q == nil)    return ["-,--", "absent", 0, "absent"]    end
    if (muet)    return ["0.00 L/min", "muet", 0, "muet"]    end
    if (q <= 0)    return ["0.00 L/min", "arrêt", 0, "arret"]    end
    var part = (tot != nil && tot > 0) ? string.format("%d %%", int(q * 100 / tot + 0.5)) : ""
    return [string.format("%.2f L/min", q), part, max > 0 ? int(q * 100 / max + 0.5) : 0,
            debitsFonctions.imprecis(q) ? "imprecis" : "normal"]
end
debitsFonctions.etatVoie = debitsFonctions_etatVoie

# Ecrit les 6 voies et le total sur l'ecran, apres chaque mesure ; rien si HASPmota n'est pas demarre
def debitsFonctions_ecran()
    import debitsFonctions
    import global
    import string
    if (global.p1b13 == nil)    return    end
    var d = debitsFonctions.debits
    var tot = debitsFonctions.total(d)
    var max = 0
    for q: d
        if (q != nil && q > max)    max = q    end
    end
    var c = debitsFonctions.COULEURS
    for i: 0 .. debitsFonctions.NB_VOIES - 1
        var e = debitsFonctions.etatVoie(d[i], tot, max, debitsFonctions.muets[i])
        var v = debitsFonctions.voie(i)
        var b = 10 * (i + 1)
        var nom = global.("p1b" + str(b + 1))
        nom.text = v["nom"]
        nom.text_color = c[e[3]]
        var barre = global.("p1b" + str(b + 2))
        barre.val = e[2]
        barre.bg_color10 = (e[3] == "imprecis" ? c["imprecis"] : "#3FA7FF")
        var debit = global.("p1b" + str(b + 3))
        debit.text = e[0]
        debit.text_color = c[e[3]]
        global.("p1b" + str(b + 4)).text = e[1]
        if (global.("p2b" + str(b + 1)) != nil)
            global.("p2b" + str(b + 1)).text = string.format("%d. %s : K %.1f Hz par L/min", i + 1, v["nom"], v["k"])
        end
    end
    global.p1b2.text = "Total " + (tot == nil ? "-,--" : string.format("%.2f L/min", tot))
    if (global.p2b90 != nil)    global.p2b90.text = "Mesure toutes les " + str(debitsFonctions.fenetre()) + " s"    end
end
debitsFonctions.ecran = debitsFonctions_ecran

# Demarre HASPmota sur la page de la carte (appele par controleDebits.init) ; sans ecran ou sans page, rien
def debitsFonctions_demarreEcran()
    import debitsFonctions
    import path
    if (!path.exists(debitsFonctions.PAGES))    return false    end
    try
        import display
        if (!display.started())
            debitsFonctions.log("ECRAN_DEBITS_ERREUR: ecran non demarre (display.ini, GPIO de drivers.ecran) !", LOG_LEVEL_ERREUR)
            return false
        end
        import haspmota
        haspmota.start(debitsFonctions.PAGES)
        debitsFonctions.ecran()
        debitsFonctions.appliqueVeille()
        return true
    except .. as e, m
        debitsFonctions.log("ECRAN_DEBITS_ERREUR: HASPmota non demarre : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    return false
end
debitsFonctions.demarreEcran = debitsFonctions_demarreEcran

# Aide de la commande ReglageDebits, appelee SEULEMENT par diversFonctions.traiteAide
def debitsFonctions_aideReglageDebits(sujet)
    import string
    if (sujet == nil)
        return [
            ["k", "k <voie 1-6> <Hz par L/min>", "facteur du debitmetre (YF-B2 : 11)"],
            ["nom", "nom <voie 1-6> <texte>", "nom du depart affiche"],
            ["fenetre", "fenetre <s>", "duree de mesure, 2 a 60 s"],
            ["veille", "veille <min>", "ecran mis en veille apres <min> sans toucher, 0 = jamais"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "K")
        return ["Parametre : numero de voie (1 a 6) puis K en Hz par L/min (0,1 a 1000).",
                "Effet : debit = frequence / K. Etalonnage : K corrige = K x debit affiche / debit reel.",
                "Sauvegarde : entree de la voie, environnement.debitmetres (voies 1-2) ou compteurs (3-6) (persist.save).",
                "Exemple : ReglageDebits k 3 11.4"]
    end
    if (sujet == "NOM")
        return ["Parametre : numero de voie (1 a 6) puis le nom (espaces permis, 24 caracteres au plus).",
                "Sauvegarde : entree de la voie, environnement.debitmetres (voies 1-2) ou compteurs (3-6) (persist.save).",
                "Exemple : ReglageDebits nom 1 Salon"]
    end
    if (sujet == "FENETRE")
        return ["Parametre : duree en s (2 a 60) entre deux mesures ; plus longue = plus precise aux petits debits.",
                "Sauvegarde : modules debits fenetre (persist.save).",
                "Exemple : ReglageDebits fenetre 10"]
    end
    if (sujet == "VEILLE")
        return ["Parametre : minutes (0 a 120) sans toucher l'ecran avant sa mise en veille ; 0 = jamais.",
                "Effet : luminosite a 25 %, puis ecran eteint 30 s plus tard ; un toucher le rallume. Applique sans redemarrer.",
                "Sauvegarde : modules debits veille (persist.save).",
                "Exemple : ReglageDebits veille 5"]
    end
    return nil
end
debitsFonctions.aideReglageDebits = debitsFonctions_aideReglageDebits

# Texte -> nombre reel, virgule francaise acceptee ; nil si ce n'est pas un nombre positif ("3abc", "", "1.2.3")
# (real() et int() de Berry rendent 0 ou le debut lisible d'un texte quelconque, sans erreur)
def debitsFonctions_nombre(s)
    import string
    s = string.replace(str(s), ",", ".")
    if (size(s) == 0)    return nil    end
    var point = false
    for i: 0 .. size(s) - 1
        if (s[i] == "." && !point)    point = true    continue    end
        if (s[i] < "0" || s[i] > "9")    return nil    end
    end
    return real(s)
end
debitsFonctions.nombre = debitsFonctions_nombre

# Ecrit un reglage valide dans l'entree de la voie (persist) ; refuse si la voie n'a pas d'entree
def debitsFonctions_regleVoie(i, cle, valeur)
    import debitsFonctions
    import persist
    var e = debitsFonctions.entree(i)
    if (e == nil)
        debitsFonctions.log("REGLAGE_DEBITS_ERREUR: voie " + str(i + 1) + " absente du persist (environnement.debitmetres ou compteurs) !", LOG_LEVEL_ERREUR)
        return
    end
    e[cle] = valeur
    persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien
end
debitsFonctions.regleVoie = debitsFonctions_regleVoie

#- Exemples :
    ReglageDebits k 1 11            => K de la voie 1
    ReglageDebits nom 2 Chambre 1   => nom de la voie 2
    ReglageDebits fenetre 10        => mesure toutes les 10 s
    ReglageDebits veille 5          => ecran en veille apres 5 min sans toucher (0 = jamais)
    ReglageDebits                   => reglages et debits actuels
-#
def debitsFonctions_reglageDebits(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    import debitsFonctions
    if diversFonctions.traiteAide("ReglageDebits", payload, debitsFonctions.aideReglageDebits, true)    return    end

    var texte = string.tr(str(payload), "	", " ")
    while string.find(texte, "  ") >= 0    texte = string.replace(texte, "  ", " ")    end
    var p = string.split(texte, " ", 2)
    var f = string.toupper(p[0])
    var n = (size(p) > 1 ? debitsFonctions.nombre(p[1]) : nil)
    var voie = (n != nil && n == int(n) ? int(n) - 1 : -1)
    var arg = (size(p) > 2 ? p[2] : "")
    if (f == "K" || f == "NOM")
        if (voie < 0 || voie >= debitsFonctions.NB_VOIES)
            debitsFonctions.log("REGLAGE_DEBITS_ERREUR: voie '" + (size(p) > 1 ? p[1] : "") + "' refusee : 1 a 6 attendu !", LOG_LEVEL_ERREUR)
        elif (f == "K")
            var k = debitsFonctions.nombre(arg)
            if (k == nil || k < 0.1 || k > 1000)
                debitsFonctions.log("REGLAGE_DEBITS_ERREUR: K '" + arg + "' refuse : 0,1 a 1000 Hz par L/min attendu !", LOG_LEVEL_ERREUR)
            else
                debitsFonctions.regleVoie(voie, "k", k)
            end
        elif (size(arg) == 0 || size(arg) > 24)
            debitsFonctions.log("REGLAGE_DEBITS_ERREUR: nom refuse : 1 a 24 caracteres attendus !", LOG_LEVEL_ERREUR)
        else
            debitsFonctions.regleVoie(voie, "nom", arg)
        end
    elif (f == "FENETRE")
        var s = (n != nil && n == int(n) ? int(n) : 0)
        if (s < 2 || s > 60)
            debitsFonctions.log("REGLAGE_DEBITS_ERREUR: fenetre '" + (size(p) > 1 ? p[1] : "") + "' refusee : 2 a 60 s attendu !", LOG_LEVEL_ERREUR)
        else
            if (!modules.contains("debits"))    modules["debits"] = {}    end
            modules["debits"]["fenetre"] = s
            persist.save(true)
        end
    elif (f == "VEILLE")
        var v = (n != nil && n == int(n) ? int(n) : -1)
        if (v < 0 || v > 120)
            debitsFonctions.log("REGLAGE_DEBITS_ERREUR: veille '" + (size(p) > 1 ? p[1] : "") + "' refusee : 0 a 120 min attendu !", LOG_LEVEL_ERREUR)
        else
            if (!modules.contains("debits"))    modules["debits"] = {}    end
            modules["debits"]["veille"] = v
            persist.save(true)
            debitsFonctions.appliqueVeille()
        end
    end

    var voies = []
    for n: 0 .. debitsFonctions.NB_VOIES - 1    voies.push(debitsFonctions.voie(n))    end
    tasmota.resp_cmnd(json.dump({"ReglageDebits": {"fenetre": debitsFonctions.fenetre(), "veille": debitsFonctions.veille(), "voies": voies, "debits": debitsFonctions.debits,
                                                      "muets": debitsFonctions.muets, "ecran_ms": debitsFonctions.ecranMs}}))
end
debitsFonctions.reglageDebits = debitsFonctions_reglageDebits

# Retourne le module lors de l'importation
return debitsFonctions
