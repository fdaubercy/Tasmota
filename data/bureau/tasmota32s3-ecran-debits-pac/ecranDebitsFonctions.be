# Fonctions du module metier ecranDebits : carte d'AFFICHAGE des 6 debits de la nourrice de chauffage
# (plan tasks/plans/debits-deux-cartes.md A4 et A8, spec docs/superpowers/specs/2026-11-09-debits-deux-cartes-design.md § 6).
# La mesure est faite par la carte d'acquisition (esclave ModBus id 1) : ses 7 valeurs (6 debits en centiemes de L/min,
# puis un mot d'etats) arrivent par le releve groupe ou par le push UDP et sont rangees par modBus_TasmotaSlaveModBus
# dans les 7 entrees analogiques virtuelles `modules.ecranDebits.environnement.analogiques` (value, etatConstate,
# constateA en secondes). Ce module les LIT, en tire un MODELE D'ECRAN independant de la bibliotheque graphique, garde
# l'historique de la courbe (par ecranFonctions). Le DESSIN est fait par une INTERFACE (voir l'API ci-dessous). Le GENERIQUE d'ecran
# (choix de l'interface, veille, luminosite par l'expandeur 0x24, historique circulaire) est dans ecranFonctions.be, solidifiable.
# Mot d'etats (analogique7) : bit i (0 a 5) = voie i+1 muette, bit 6+i = voie i+1 imprecise, bit 12 = groupe servi.
# Une voie est « inconnue » si sa valeur n'est pas fraiche : etatConstate different de « valide », sentinelle, ou
# constateA plus vieux que 2 fenetres (modules.ecranDebits.fenetre, a recopier a la main si on change celle de l'acquisition).
# Compile en .bec par demarrage.compile(["ecranDebitsFonctions"], "modules.ecranDebits"), importe par controleEcranDebits.be.
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).
#
# ===== API d'une INTERFACE d'ecran (ecranHaspmota.be + pages.jsonl, ou ecranLvgl.be ; une seule sur le FS) =====
# Waveshare ESP32-S3-Touch-LCD-7B, 1024 x 600, tactile GT911 ; maquettes outils_docs/ecran_debits_7B/ (modele-A, modele-D).
# controleEcranDebits charge l'interface presente sur le FS par ecranFonctions.charge(["ecranHaspmota", "ecranLvgl"]) (la
# premiere presente) et la confie a ecranDebitsFonctions.demarreEcran(module). Un module d'interface (module(...), fonctions nommees, pas de fonction anonyme) rend :
#   demarre()        -> true si l'ecran est pret, objets crees ; false sinon, erreur DEJA journalisee. Appele une fois.
#   affiche(modele)  -> ecrit le modele sur l'ecran. Appele CHAQUE SECONDE (l'age du releve change) : n'ecrire sur un objet
#                       que ce qui a change depuis la derniere fois (cache par objet et attribut), jamais tout.
# Pages : 1 « Debits » (modele A : nom, barre, debit + unite, part du total), 2 « Courbes » (modele D : puce de la couleur
# de la serie, nom, debit + unite ; courbe des 30 dernieres minutes des 6 voies), 3 « Reglages » (fenetre, veille, luminosite,
# chacun avec un bouton - et un bouton +). Commun a toutes : en-tete (titre « Débits nourrice », pastille de liaison, texte du
# releve, total a droite) et pied de page tactile « Débits » / « Courbes » / « Réglages », bouton de la page courante en bleu.
# Boutons - / + : ecranDebitsFonctions.ajuste(cle, pas) ; cle "fenetre" pas 1, "veille" pas 1, "luminosite" pas 10.
# Veille, luminosite et voile anti-clic du reveil sont faits par ecranFonctions (lv.disp().get_inactive_time()) : rien a faire
# dans l'interface.
# Modele (ecranDebitsFonctions.modele(now)), une map :
#   "voies"      : 6 maps {"nom", "debit" (texte sans unite : "4,20", "-,--", "muet"), "unite" ("L/min" ou ""),
#                  "part" ("23 %", "arrêt" ou ""), "barre" (0-100, relative a la plus forte voie), "etat"}
#                  etat : "normal", "imprecis", "muet", "arret", "inconnu" ; couleur = COULEURS[etat]
#   "total"      : texte ("Total 17,9 L/min", "Total 17,9 L/min (partiel)", "Total inconnu")
#   "age"        : secondes depuis le dernier releve ModBus (nil : jamais) ; "releve" : son texte ("relevé il y a 4 s")
#   "liaison"    : cle de COULEURS de la pastille ("vert" a moins de 2 fenetres, "muet" au-dela, "inconnu" sans releve)
#   "historique" : 6 listes de ecranFonctions.HISTO_POINTS entiers en centiemes de L/min, du plus vieux au plus recent, nil = inconnu
#                  (lv.CHART_POINT_NONE) ; un point toutes les 30 s ; couleur de la voie i = SERIES[i]
#   "points"     : nombre de points ajoutes depuis le demarrage (pousser seulement les nouveaux, set_next_value)
#   "courbeMax"  : haut de l'axe des debits, en centiemes (multiple de 2 L/min, 10 L/min au moins)
#   "reglages"   : textes {"fenetre": "10 s", "veille": "5 min" ou "jamais", "luminosite": "80 %"}
# Ressources : rendu SANS image (formes, couleurs, polices embarquees robotocondensed). Aucune image ni ressource ne s'ajoute
# sans l'accord de l'utilisateur ; si une est retenue, elle va dans /sd/<type>/ sur la carte (data/sd/<type>/ au depot), comme
# /sd/html, /sd/js, /sd/css. L'image du FS est plate : gestionFileFolder.listeEtRepartitLesFichiers range au demarrage par
# extension, et tout nom contenant ".json" part en /json/ (pages.jsonl est lu en /json/pages.jsonl).
var ecranDebitsFonctions = module("ecranDebitsFonctions")

ecranDebitsFonctions.NB_VOIES = 6
# Reglage propre aux debits (modules.ecranDebits.fenetre) : [minimum, maximum, defaut, unite] ; veille, extinction et luminosite
# sont ceux de ecranFonctions.BORNES
ecranDebitsFonctions.BORNES = {"fenetre": [2, 60, 10, "s"]}
ecranDebitsFonctions.COULEURS = {"normal": "#E8EDF2", "imprecis": "#FFA53F", "muet": "#FF5A5A", "inconnu": "#5B6B7C",
                                 "arret": "#9FB3C8", "bleu": "#3FA7FF", "vert": "#3FD08A"}
ecranDebitsFonctions.SERIES = ["#3FA7FF", "#3FD08A", "#FFA53F", "#C084FC", "#FF5A5A", "#F5D04A"]
ecranDebitsFonctions.toutesInconnues = true   # vrai au demarrage : le premier « tout inconnu » n'est pas un message
ecranDebitsFonctions.courbeMax = 1000      # haut de l'axe de la courbe, en centiemes

# Log du module sous le seuil `general` (ReglageLog general <niveau>) ; niveau = constante LOG_LEVEL_*
def ecranDebitsFonctions_log(msg, niveau)
    logFonctions.log(msg, niveau)
end
ecranDebitsFonctions.log = ecranDebitsFonctions_log

# Bornes du reglage `cle` : celles des debits (fenetre), sinon celles de ecranFonctions (veille, extinction, luminosite) ; nil si inconnu
def ecranDebitsFonctions_bornes(cle)
    import ecranFonctions
    import ecranDebitsFonctions
    var b = ecranDebitsFonctions.BORNES.find(cle)
    return b != nil ? b : ecranFonctions.BORNES.find(cle)
end
ecranDebitsFonctions.bornes = ecranDebitsFonctions_bornes

# Reglage `cle` du persist (modules.ecranDebits), valeur par defaut si absent ou illisible
def ecranDebitsFonctions_reglage(cle)
    import ecranFonctions
    import ecranDebitsFonctions
    return ecranFonctions.reglage(cle, ecranDebitsFonctions.bornes(cle))
end
ecranDebitsFonctions.reglage = ecranDebitsFonctions_reglage

# Bouton - / + de la page Reglages : valeur actuelle + pas, ramenee dans les bornes, appliquee tout de suite, persist ecrit 3 s apres le dernier appui
def ecranDebitsFonctions_ajuste(cle, pas)
    import ecranFonctions
    import ecranDebitsFonctions
    var b = ecranDebitsFonctions.bornes(cle)
    var n = ecranDebitsFonctions.reglage(cle) + pas
    return ecranFonctions.regle(cle, n < b[0] ? b[0] : (n > b[1] ? b[1] : n), b, true)
end
ecranDebitsFonctions.ajuste = ecranDebitsFonctions_ajuste

# Entree analogique virtuelle n (1 a 7) du persist, nil si absente ou inactive
def ecranDebitsFonctions_entree(n)
    var ed = modules.find("ecranDebits")
    var env = ed == nil ? nil : ed.find("environnement")
    var ana = env == nil ? nil : env.find("analogiques")
    var e = ana == nil ? nil : ana.find("analogique" + str(n))
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
    if (type(t) != "int" || t > now || now - t > 2 * ecranDebitsFonctions.reglage("fenetre"))    return nil    end
    var v = e.find("value")
    return (type(v) == "int" && v >= 0 && v != modbusFonctions.SENTINELLE_UINT32) ? v : nil
end
ecranDebitsFonctions.valeur = ecranDebitsFonctions_valeur

# Secondes depuis le plus recent releve ModBus des 7 entrees (constateA), nil si aucun
def ecranDebitsFonctions_age(now)
    import ecranDebitsFonctions
    var t = nil
    for i: 1 .. ecranDebitsFonctions.NB_VOIES + 1
        var e = ecranDebitsFonctions.entree(i)
        var c = e == nil ? nil : e.find("constateA")
        if (type(c) == "int" && c <= now && (t == nil || c > t))    t = c    end
    end
    return t == nil ? nil : now - t
end
ecranDebitsFonctions.age = ecranDebitsFonctions_age

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

# Nombre a virgule (affichage en francais) : 4.2 -> "4,20" (decimales = format, ex. "%.2f")
def ecranDebitsFonctions_virgule(q, fmt)
    import string
    return string.tr(string.format(fmt, q), ".", ",")
end
ecranDebitsFonctions.virgule = ecranDebitsFonctions_virgule

# Affichage d'une voie : {"debit", "unite", "part", "barre" (0-100, relative a la plus forte voie), "etat"}
def ecranDebitsFonctions_etatVoie(q, tot, max, muet, imprecis)
    import string
    import ecranDebitsFonctions
    if (q == nil)    return {"debit": "-,--", "unite": "L/min", "part": "", "barre": 0, "etat": "inconnu"}    end
    if (muet)    return {"debit": "muet", "unite": "", "part": "", "barre": 0, "etat": "muet"}    end
    if (q <= 0)    return {"debit": "0,00", "unite": "L/min", "part": "arrêt", "barre": 0, "etat": "arret"}    end
    var part = (tot != nil && tot > 0) ? string.format("%d %%", int(q * 100 / tot + 0.5)) : ""
    return {"debit": ecranDebitsFonctions.virgule(q, "%.2f"), "unite": "L/min", "part": part,
            "barre": max > 0 ? int(q * 100 / max + 0.5) : 0, "etat": imprecis ? "imprecis" : "normal"}
end
ecranDebitsFonctions.etatVoie = ecranDebitsFonctions_etatVoie

# Toutes les voies passent « inconnues » d'un coup alors qu'une au moins etait connue : le plus souvent la fenetre du persist
# n'est plus celle de l'acquisition (changee par ReglageDebits sans etre recopiee ici). Un message debug, une fois par transition.
def ecranDebitsFonctions_suitFenetre(d)
    import ecranDebitsFonctions
    var toutes = ecranDebitsFonctions.total(d)[1] == 0
    if (toutes && !ecranDebitsFonctions.toutesInconnues)
        ecranDebitsFonctions.log("ECRAN_DEBITS: fenetre ? les 6 voies sont devenues inconnues ensemble, la fenetre de l'acquisition est-elle bien de " +
                                 str(ecranDebitsFonctions.reglage("fenetre")) + " s (ReglageEcranDebits fenetre) ?", LOG_LEVEL_DEBUG)
    end
    ecranDebitsFonctions.toutesInconnues = toutes
end
ecranDebitsFonctions.suitFenetre = ecranDebitsFonctions_suitFenetre

# Modele d'ecran (voir l'API en tete) a l'instant `now` ; met aussi a jour l'historique et le message « fenetre ? »
def ecranDebitsFonctions_modele(now)
    import ecranFonctions
    import ecranDebitsFonctions
    import string
    var d = ecranDebitsFonctions.debits(now)
    ecranDebitsFonctions.suitFenetre(d)
    var cent = []
    for q: d    cent.push(q == nil ? nil : int(q * 100 + 0.5))    end
    if (ecranFonctions.echantillonne(cent))
        # haut de l'axe : multiple de 2 L/min, 10 L/min au moins
        var hm = ((ecranFonctions.histoMax() + 199) / 200) * 200
        ecranDebitsFonctions.courbeMax = hm < 1000 ? 1000 : hm
    end
    var w = ecranDebitsFonctions.etats(now)
    var tt = ecranDebitsFonctions.total(d)
    var tot = tt[0]
    var max = 0
    for q: d
        if (q != nil && q > max)    max = q    end
    end
    var voies = []
    for i: 0 .. ecranDebitsFonctions.NB_VOIES - 1
        var imp = w["frais"] ? w["imprecis"][i] : ecranDebitsFonctions.imprecis(d[i])
        var v = ecranDebitsFonctions.etatVoie(d[i], tot, max, w["muets"][i], imp)
        var ent = ecranDebitsFonctions.entree(i + 1)
        v["nom"] = ent == nil ? "Débit " + str(i + 1) : str(ent.find("nom", "Débit " + str(i + 1)))
        voies.push(v)
    end
    var total = "Total inconnu"
    if (tot != nil)    total = "Total " + ecranDebitsFonctions.virgule(tot, "%.1f") + " L/min" + (tt[1] < ecranDebitsFonctions.NB_VOIES ? " (partiel)" : "")    end
    var age = ecranDebitsFonctions.age(now)
    var releve = "aucun relevé"
    var liaison = "inconnu"
    if (age != nil)
        releve = age < 120 ? string.format("relevé il y a %d s", age) : string.format("relevé il y a %d min", age / 60)
        liaison = age <= 2 * ecranDebitsFonctions.reglage("fenetre") ? "vert" : "muet"
    end
    var veille = ecranDebitsFonctions.reglage("veille")
    return {"voies": voies, "total": total, "age": age, "releve": releve, "liaison": liaison,
            "historique": ecranFonctions.histo, "points": ecranFonctions.points, "courbeMax": ecranDebitsFonctions.courbeMax,
            "reglages": {"fenetre": str(ecranDebitsFonctions.reglage("fenetre")) + " s", "veille": veille == 0 ? "jamais" : str(veille) + " min",
                         "luminosite": str(ecranDebitsFonctions.reglage("luminosite")) + " %"}}
end
ecranDebitsFonctions.modele = ecranDebitsFonctions_modele

# Appelee chaque seconde par le driver : modele calcule (historique, message « fenetre ? ») meme sans ecran, puis affiche
def ecranDebitsFonctions_ecran()
    import ecranFonctions
    import ecranDebitsFonctions
    var m = ecranDebitsFonctions.modele(tasmota.rtc()["local"])
    if (ecranFonctions.interface != nil)    ecranFonctions.interface.affiche(m)    end
end
ecranDebitsFonctions.ecran = ecranDebitsFonctions_ecran

# Demarre l'interface choisie par controleEcranDebits (module ecranHaspmota ou ecranLvgl) et la remplit ; nil ou echec : pas d'ecran
def ecranDebitsFonctions_demarreEcran(itf)
    import ecranFonctions
    import ecranDebitsFonctions
    if (!ecranFonctions.demarre(itf))    return false    end
    ecranDebitsFonctions.ecran()
    return true
end
ecranDebitsFonctions.demarreEcran = ecranDebitsFonctions_demarreEcran

# Aide de la commande ReglageEcranDebits, appelee SEULEMENT par diversFonctions.traiteAide
def ecranDebitsFonctions_aideReglageEcranDebits(sujet)
    import string
    if (sujet == nil)
        return [
            ["fenetre", "fenetre <s>", "fenetre de mesure de l'acquisition, 2 a 60 s (inconnu au-dela de 2 fenetres)"],
            ["veille", "veille <min>", "ecran a 10 % apres <min> sans toucher, 0 = jamais"],
            ["extinction", "extinction <min>", "ecran eteint <min> apres la gradation, 0 = jamais"],
            ["luminosite", "luminosite <%>", "luminosite en service, 10 a 100 %"],
            ["pwmInverse", "pwmInverse ON|OFF", "sens du PWM du retroeclairage (ON : valeur haute = sombre)"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "FENETRE")
        return ["Parametre : duree en s (2 a 60), la meme que ReglageDebits fenetre sur la carte d'acquisition.",
                "Effet : une voie sans nouvelle mesure depuis plus de 2 fenetres est affichee « inconnu ». A recopier a la main.",
                "Sauvegarde : modules ecranDebits fenetre (persist.save).", "Exemple : ReglageEcranDebits fenetre 10"]
    end
    if (sujet == "VEILLE")
        return ["Parametre : minutes (0 a 120) sans toucher l'ecran avant la gradation a 10 % ; 0 = jamais.",
                "Effet : puis ecran eteint apres `extinction` minutes ; un toucher le rallume (sans actionner le bouton touche).",
                "Sauvegarde : modules ecranDebits veille (persist.save).", "Exemple : ReglageEcranDebits veille 5"]
    end
    if (sujet == "EXTINCTION")
        return ["Parametre : minutes (0 a 240) a 10 % avant d'eteindre l'ecran ; 0 = reste a 10 %.",
                "Sauvegarde : modules ecranDebits extinction (persist.save).", "Exemple : ReglageEcranDebits extinction 30"]
    end
    if (sujet == "LUMINOSITE")
        return ["Parametre : pourcentage (10 a 100), applique sans redemarrer ; aussi par la page Reglages de l'ecran.",
                "Sauvegarde : modules ecranDebits luminosite (persist.save).", "Exemple : ReglageEcranDebits luminosite 80"]
    end
    if (sujet == "PWMINVERSE")
        return ["Parametre : ON (defaut, d'apres la demo Waveshare : valeur haute du registre = ecran sombre) ou OFF.",
                "Effet : a changer si l'ecran s'assombrit quand la luminosite monte.",
                "Sauvegarde : modules ecranDebits pwmInverse (persist.save).", "Exemple : ReglageEcranDebits pwmInverse OFF"]
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
    ReglageEcranDebits fenetre 10      => une voie est « inconnue » apres 20 s sans nouvelle mesure
    ReglageEcranDebits veille 5        => ecran a 10 % apres 5 min sans toucher (0 = jamais)
    ReglageEcranDebits extinction 30   => eteint 30 min apres la gradation (0 = jamais)
    ReglageEcranDebits luminosite 80   => luminosite en service
    ReglageEcranDebits pwmInverse OFF  => sens du PWM du retroeclairage
    ReglageEcranDebits                 => reglages actuels
-#
def ecranDebitsFonctions_reglageEcranDebits(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    import ecranFonctions
    import ecranDebitsFonctions
    if diversFonctions.traiteAide("ReglageEcranDebits", payload, ecranDebitsFonctions.aideReglageEcranDebits, true)    return    end

    var texte = string.tr(str(payload), "	", " ")
    while string.find(texte, "  ") >= 0    texte = string.replace(texte, "  ", " ")    end
    var p = string.split(texte, " ", 2)
    var cle = string.tolower(p[0])
    var arg = size(p) > 1 ? p[1] : ""
    var b = ecranDebitsFonctions.bornes(cle)
    if (b != nil && !ecranFonctions.regle(cle, ecranDebitsFonctions.entier(arg), b))
        ecranDebitsFonctions.log("REGLAGE_ECRAN_DEBITS_ERREUR: " + cle + " '" + arg + "' refuse : " + str(b[0]) + " a " + str(b[1]) + " " + b[3] + " attendu !", LOG_LEVEL_ERREUR)
    elif (cle == "pwminverse")
        arg = string.toupper(arg)
        if (arg != "ON" && arg != "OFF")
            ecranDebitsFonctions.log("REGLAGE_ECRAN_DEBITS_ERREUR: pwmInverse '" + arg + "' refuse : ON ou OFF attendu !", LOG_LEVEL_ERREUR)
        else
            var bl = ecranFonctions.bloc
            if (!modules.contains(bl))    modules[bl] = {}    end
            modules[bl]["pwmInverse"] = arg
            persist.save(true)
            ecranFonctions.etatVeille = nil
        end
    end
    var r = {"pwmInverse": ecranFonctions.pwmInverse() ? "ON" : "OFF", "fenetre": ecranDebitsFonctions.reglage("fenetre")}
    for k: ecranFonctions.BORNES.keys()    r[k] = ecranDebitsFonctions.reglage(k)    end
    tasmota.resp_cmnd(json.dump({"ReglageEcranDebits": r}))
end
ecranDebitsFonctions.reglageEcranDebits = ecranDebitsFonctions_reglageEcranDebits

# Retourne le module lors de l'importation
return ecranDebitsFonctions
