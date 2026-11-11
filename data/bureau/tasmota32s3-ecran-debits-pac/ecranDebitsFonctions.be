# Fonctions du module metier ecranDebits : carte d'AFFICHAGE des 6 debits de la nourrice de chauffage
# (plan tasks/plans/debits-deux-cartes.md A4, spec docs/superpowers/specs/2026-11-09-debits-deux-cartes-design.md § 6).
# La mesure est faite par la carte d'acquisition (esclave ModBus id 1) : ses 7 valeurs (6 debits en centiemes de L/min,
# puis un mot d'etats) arrivent par le releve groupe ou par le push UDP et sont rangees par modBus_TasmotaSlaveModBus
# dans les 7 entrees analogiques virtuelles `modules.ecranDebits.environnement.analogiques` (value, etatConstate,
# constateA en secondes). Ce module ne fait que les LIRE et les montrer sur l'ecran TFT (HASPmota, pages.jsonl du dossier).
# Mot d'etats (analogique7) : bit i (0 a 5) = voie i+1 muette, bit 6+i = voie i+1 imprecise, bit 12 = groupe servi.
# Une voie est « inconnue » si sa valeur n'est pas fraiche : etatConstate different de « valide », sentinelle, ou
# constateA plus vieux que 2 fenetres (modules.ecranDebits.fenetre, a recopier a la main si on change celle de l'acquisition).
# Compile en .bec par demarrage.compile(["ecranDebitsFonctions"], "modules.ecranDebits"), importe par controleEcranDebits.be.
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).
var ecranDebitsFonctions = module("ecranDebitsFonctions")

ecranDebitsFonctions.NB_VOIES = 6
ecranDebitsFonctions.FENETRE_DEFAUT = 10   # s entre deux mesures de l'acquisition
ecranDebitsFonctions.VEILLE_DEFAUT = 5     # min sans toucher l'ecran avant sa mise en veille (0 = jamais)
ecranDebitsFonctions.PAGES = "/json/pages.jsonl"
ecranDebitsFonctions.COULEURS = {"normal": "#E8EDF2", "imprecis": "#F2B84B", "arret": "#6C7A89", "inconnu": "#FF6B6B", "muet": "#FF6B6B"}
ecranDebitsFonctions.dernier = nil         # contenu deja ecrit sur l'ecran (nil = objets neufs : tout ecrire)
ecranDebitsFonctions.toutesInconnues = true   # vrai au demarrage : le premier « tout inconnu » n'est pas un message

# Log du module sous le seuil `general` (ReglageLog general <niveau>) ; niveau = constante LOG_LEVEL_*
def ecranDebitsFonctions_log(msg, niveau)
    logFonctions.log(msg, niveau)
end
ecranDebitsFonctions.log = ecranDebitsFonctions_log

# Reglages du module, valeurs par defaut si le persist ne les porte pas (ou si la valeur est illisible)
def ecranDebitsFonctions_fenetre()
    import ecranDebitsFonctions
    var v = modules.contains("ecranDebits") ? modules["ecranDebits"].find("fenetre", ecranDebitsFonctions.FENETRE_DEFAUT) : ecranDebitsFonctions.FENETRE_DEFAUT
    return (type(v) == "int" && v >= 2 && v <= 60) ? v : ecranDebitsFonctions.FENETRE_DEFAUT
end
ecranDebitsFonctions.fenetre = ecranDebitsFonctions_fenetre

# Minutes sans toucher l'ecran avant sa mise en veille (HASPmota : 25 % puis eteint 30 s plus tard), 0 = jamais ;
# persist modules.ecranDebits.veille, valeur hors 0..120 ignoree (persist edite a la main)
def ecranDebitsFonctions_veille()
    import ecranDebitsFonctions
    var v = modules.contains("ecranDebits") ? modules["ecranDebits"].find("veille", ecranDebitsFonctions.VEILLE_DEFAUT) : ecranDebitsFonctions.VEILLE_DEFAUT
    return (type(v) == "int" && v >= 0 && v <= 120) ? v : ecranDebitsFonctions.VEILLE_DEFAUT
end
ecranDebitsFonctions.veille = ecranDebitsFonctions_veille

# Applique la veille a HASPmota (lu a chaque passage de haspmota.auto_dimming) ; rien sans ecran demarre
def ecranDebitsFonctions_appliqueVeille()
    import global
    import ecranDebitsFonctions
    if (global.p1b13 == nil)    return    end
    import haspmota
    var v = ecranDebitsFonctions.veille()
    haspmota.dimming_time = v
    # A 0, auto_dimming sort d'emblee et ne rallume plus : un ecran deja assombri resterait noir
    if (v == 0 && haspmota.dimming_state < 100)
        if (haspmota.dimmed_panel != nil)    haspmota.dimmed_panel.stop()    haspmota.dimmed_panel = nil    end
        haspmota.dimming_state = 100
        import display
        display.dimmer(display.dimmer())
        # meme evenement que la sortie de veille d'auto_dimming, pour une regle hasp#p0b0#idle
        tasmota.defer(def () tasmota.publish_rule('{"hasp":{"p0b0":{"idle":"off"}}}') end)
    end
end
ecranDebitsFonctions.appliqueVeille = ecranDebitsFonctions_appliqueVeille

# Entree analogique virtuelle n (1 a 7) du persist, nil si absente ou inactive
def ecranDebitsFonctions_entree(n)
    var ana = modules.find("ecranDebits", {}).find("environnement", {}).find("analogiques", {})
    var e = ana.find("analogique" + str(n))
    return (isinstance(e, map) && e.find("activation", "OFF") == "ON") ? e : nil
end
ecranDebitsFonctions.entree = ecranDebitsFonctions_entree

# Valeur fraiche de l'entree n (entier du registre) a l'instant `now` (secondes, tasmota.rtc()["local"]), nil si inconnue :
# etatConstate different de « valide » (defaillant, inconnu du chien de garde, jamais recu), sentinelle, ou plus de 2 fenetres
def ecranDebitsFonctions_valeur(n, now)
    import ecranDebitsFonctions
    import modbusFonctions
    var e = ecranDebitsFonctions.entree(n)
    if (e == nil || e.find("etatConstate") != "valide")    return nil    end
    var t = e.find("constateA")
    # t > now : releve sauve par un persist.save avant le redemarrage, lu avant l'heure NTP
    if (type(t) != "int" || t > now || now - t > 2 * ecranDebitsFonctions.fenetre())    return nil    end
    var v = e.find("value")
    return (type(v) == "int" && v >= 0 && v != modbusFonctions.SENTINELLE_UINT32) ? v : nil
end
ecranDebitsFonctions.valeur = ecranDebitsFonctions_valeur

# Les 6 debits en L/min (nil = inconnu)
def ecranDebitsFonctions_debits(now)
    import ecranDebitsFonctions
    var d = []
    for i: 1 .. ecranDebitsFonctions.NB_VOIES
        var v = ecranDebitsFonctions.valeur(i, now)
        d.push(v == nil ? nil : v / 100.0)
    end
    return d
end
ecranDebitsFonctions.debits = ecranDebitsFonctions_debits

# Mot d'etats (entree 7) : {"frais": bool, "muets": [6 bool], "imprecis": [6 bool]} ; non frais -> tout a false
def ecranDebitsFonctions_etats(now)
    import ecranDebitsFonctions
    var w = ecranDebitsFonctions.valeur(ecranDebitsFonctions.NB_VOIES + 1, now)
    var muets = []
    var imprecis = []
    for i: 0 .. ecranDebitsFonctions.NB_VOIES - 1
        muets.push(w != nil && (w & (1 << i)) != 0)
        imprecis.push(w != nil && (w & (1 << (6 + i))) != 0)
    end
    return {"frais": w != nil, "muets": muets, "imprecis": imprecis}
end
ecranDebitsFonctions.etats = ecranDebitsFonctions_etats

# Somme des voies connues : [somme, nombre de voies connues] (somme nil si aucune)
def ecranDebitsFonctions_total(d)
    var s = nil
    var n = 0
    for q: d
        if (q != nil)    s = (s == nil ? 0.0 : s) + q    n += 1    end
    end
    return [s, n]
end
ecranDebitsFonctions.total = ecranDebitsFonctions_total

# Moins de 1 L/min (sous la plage du YF-B2, 1-25 L/min) : meme regle que sur l'acquisition, si le mot d'etats est perime
def ecranDebitsFonctions_imprecis(q)
    return q != nil && q > 0 && q < 1
end
ecranDebitsFonctions.imprecis = ecranDebitsFonctions_imprecis

# Affichage d'une voie : [debit, part, barre 0-100 (relative a la plus forte voie), etat]
def ecranDebitsFonctions_etatVoie(q, tot, max, muet, imprecis)
    import string
    if (q == nil)    return ["inconnu", "", 0, "inconnu"]    end
    if (muet)    return ["0.00 L/min", "muet", 0, "muet"]    end
    if (q <= 0)    return ["0.00 L/min", "arrêt", 0, "arret"]    end
    var part = (tot != nil && tot > 0) ? string.format("%d %%", int(q * 100 / tot + 0.5)) : ""
    return [string.format("%.2f L/min", q), part, max > 0 ? int(q * 100 / max + 0.5) : 0, imprecis ? "imprecis" : "normal"]
end
ecranDebitsFonctions.etatVoie = ecranDebitsFonctions_etatVoie

# Toutes les voies passent « inconnues » d'un coup alors qu'une au moins etait connue : le plus souvent la fenetre du persist
# n'est plus celle de l'acquisition (changee par ReglageDebits sans etre recopiee ici). Un message debug, une fois par transition.
def ecranDebitsFonctions_suitFenetre(d)
    import ecranDebitsFonctions
    var toutes = ecranDebitsFonctions.total(d)[1] == 0
    if (toutes && !ecranDebitsFonctions.toutesInconnues)
        ecranDebitsFonctions.log("ECRAN_DEBITS: fenetre ? les 6 voies sont devenues inconnues ensemble, la fenetre de l'acquisition est-elle bien de " +
                                 str(ecranDebitsFonctions.fenetre()) + " s (ReglageEcranDebits fenetre) ?", LOG_LEVEL_DEBUG)
    end
    ecranDebitsFonctions.toutesInconnues = toutes
end
ecranDebitsFonctions.suitFenetre = ecranDebitsFonctions_suitFenetre

# Ecran TFT (LVGL, HASPmota) : page /json/pages.jsonl du dossier de la carte (modele B de outils_docs/chauffage/ecran/),
# rangee dans /json/ au demarrage par gestionFileFolder ; voie n = objets p1b<10n+1> nom, +2 barre, +3 debit, +4 part.
# Appelee chaque seconde : l'ecran n'est reecrit que si un texte a change (nom, debit, etat, total, fenetre).
def ecranDebitsFonctions_ecran()
    import ecranDebitsFonctions
    import global
    import string
    var now = tasmota.rtc()["local"]
    var d = ecranDebitsFonctions.debits(now)
    ecranDebitsFonctions.suitFenetre(d)
    if (global.p1b13 == nil)    return    end
    var w = ecranDebitsFonctions.etats(now)
    var tt = ecranDebitsFonctions.total(d)
    var tot = tt[0]
    var max = 0
    for q: d
        if (q != nil && q > max)    max = q    end
    end
    var f = ecranDebitsFonctions.fenetre()
    var voies = []
    for i: 0 .. ecranDebitsFonctions.NB_VOIES - 1
        var imp = w["frais"] ? w["imprecis"][i] : ecranDebitsFonctions.imprecis(d[i])
        var ent = ecranDebitsFonctions.entree(i + 1)
        voies.push([ent == nil ? "Départ " + str(i + 1) : str(ent.find("nom", "Départ " + str(i + 1))),
                    ecranDebitsFonctions.etatVoie(d[i], tot, max, w["muets"][i], imp)])
    end
    var total = "Total inconnu"
    if (tot != nil)    total = string.format("Total %.2f L/min", tot) + (tt[1] < ecranDebitsFonctions.NB_VOIES ? " (partiel)" : "")    end
    var bas = "Fenêtre attendue : " + str(f) + " s (inconnu au-delà de " + str(2 * f) + " s)"
    var cle = str([voies, total, bas])
    if (cle == ecranDebitsFonctions.dernier)    return    end
    ecranDebitsFonctions.dernier = cle
    var c = ecranDebitsFonctions.COULEURS
    for i: 0 .. ecranDebitsFonctions.NB_VOIES - 1
        var e = voies[i][1]
        var b = 10 * (i + 1)
        var nom = global.("p1b" + str(b + 1))
        nom.text = voies[i][0]
        nom.text_color = c[e[3]]
        var barre = global.("p1b" + str(b + 2))
        barre.val = e[2]
        barre.bg_color10 = (e[3] == "imprecis" ? c["imprecis"] : "#3FA7FF")
        var debit = global.("p1b" + str(b + 3))
        debit.text = e[0]
        debit.text_color = c[e[3]]
        global.("p1b" + str(b + 4)).text = e[1]
        if (global.("p2b" + str(b + 1)) != nil)
            global.("p2b" + str(b + 1)).text = string.format("%d. %s : %s", i + 1, voies[i][0], e[3])
        end
    end
    global.p1b2.text = total
    if (global.p2b90 != nil)    global.p2b90.text = bas    end
end
ecranDebitsFonctions.ecran = ecranDebitsFonctions_ecran

# Demarre HASPmota sur la page de la carte (appele par controleEcranDebits.init) ; sans ecran ou sans page, rien
def ecranDebitsFonctions_demarreEcran()
    import ecranDebitsFonctions
    import path
    if (!path.exists(ecranDebitsFonctions.PAGES))    return false    end
    try
        import display
        if (!display.started())
            ecranDebitsFonctions.log("ECRAN_DEBITS_ERREUR: ecran non demarre (display.ini, GPIO de drivers.ecran) !", LOG_LEVEL_ERREUR)
            return false
        end
        import haspmota
        haspmota.start(ecranDebitsFonctions.PAGES)
        ecranDebitsFonctions.dernier = nil    # objets neufs : tout reecrire
        ecranDebitsFonctions.ecran()
        ecranDebitsFonctions.appliqueVeille()
        return true
    except .. as e, m
        ecranDebitsFonctions.log("ECRAN_DEBITS_ERREUR: HASPmota non demarre : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    return false
end
ecranDebitsFonctions.demarreEcran = ecranDebitsFonctions_demarreEcran

# Aide de la commande ReglageEcranDebits, appelee SEULEMENT par diversFonctions.traiteAide
def ecranDebitsFonctions_aideReglageEcranDebits(sujet)
    import string
    if (sujet == nil)
        return [
            ["fenetre", "fenetre <s>", "fenetre de mesure de l'acquisition, 2 a 60 s (inconnu au-dela de 2 fenetres)"],
            ["veille", "veille <min>", "ecran mis en veille apres <min> sans toucher, 0 = jamais"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "FENETRE")
        return ["Parametre : duree en s (2 a 60), la meme que ReglageDebits fenetre sur la carte d'acquisition.",
                "Effet : une voie sans nouvelle mesure depuis plus de 2 fenetres est affichee « inconnu ». A recopier a la main.",
                "Sauvegarde : modules ecranDebits fenetre (persist.save).",
                "Exemple : ReglageEcranDebits fenetre 10"]
    end
    if (sujet == "VEILLE")
        return ["Parametre : minutes (0 a 120) sans toucher l'ecran avant sa mise en veille ; 0 = jamais.",
                "Effet : luminosite a 25 %, puis ecran eteint 30 s plus tard ; un toucher le rallume. Applique sans redemarrer.",
                "Sauvegarde : modules ecranDebits veille (persist.save).",
                "Exemple : ReglageEcranDebits veille 5"]
    end
    return nil
end
ecranDebitsFonctions.aideReglageEcranDebits = ecranDebitsFonctions_aideReglageEcranDebits

# Texte -> entier positif, nil si ce n'est pas un entier ("3abc", "", "2.5", "-1")
def ecranDebitsFonctions_entier(s)
    s = str(s)
    if (size(s) == 0)    return nil    end
    for i: 0 .. size(s) - 1
        if (s[i] < "0" || s[i] > "9")    return nil    end
    end
    return int(s)
end
ecranDebitsFonctions.entier = ecranDebitsFonctions_entier

#- Exemples :
    ReglageEcranDebits fenetre 10   => une voie est « inconnue » apres 20 s sans nouvelle mesure
    ReglageEcranDebits veille 5     => ecran en veille apres 5 min sans toucher (0 = jamais)
    ReglageEcranDebits              => reglages actuels
-#
def ecranDebitsFonctions_reglageEcranDebits(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    import ecranDebitsFonctions
    if diversFonctions.traiteAide("ReglageEcranDebits", payload, ecranDebitsFonctions.aideReglageEcranDebits, true)    return    end

    var texte = string.tr(str(payload), "	", " ")
    while string.find(texte, "  ") >= 0    texte = string.replace(texte, "  ", " ")    end
    var p = string.split(texte, " ", 2)
    var f = string.toupper(p[0])
    var n = (size(p) > 1 ? ecranDebitsFonctions.entier(p[1]) : nil)
    if (f == "FENETRE")
        if (n == nil || n < 2 || n > 60)
            ecranDebitsFonctions.log("REGLAGE_ECRAN_DEBITS_ERREUR: fenetre '" + (size(p) > 1 ? p[1] : "") + "' refusee : 2 a 60 s attendu !", LOG_LEVEL_ERREUR)
        else
            if (!modules.contains("ecranDebits"))    modules["ecranDebits"] = {}    end
            modules["ecranDebits"]["fenetre"] = n
            persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien
        end
    elif (f == "VEILLE")
        if (n == nil || n > 120)
            ecranDebitsFonctions.log("REGLAGE_ECRAN_DEBITS_ERREUR: veille '" + (size(p) > 1 ? p[1] : "") + "' refusee : 0 a 120 min attendu !", LOG_LEVEL_ERREUR)
        else
            if (!modules.contains("ecranDebits"))    modules["ecranDebits"] = {}    end
            modules["ecranDebits"]["veille"] = n
            persist.save(true)
            ecranDebitsFonctions.appliqueVeille()
        end
    end
    tasmota.resp_cmnd(json.dump({"ReglageEcranDebits": {"fenetre": ecranDebitsFonctions.fenetre(), "veille": ecranDebitsFonctions.veille()}}))
end
ecranDebitsFonctions.reglageEcranDebits = ecranDebitsFonctions_reglageEcranDebits

# Retourne le module lors de l'importation
return ecranDebitsFonctions
