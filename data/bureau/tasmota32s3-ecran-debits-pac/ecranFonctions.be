# Fonctions GENERIQUES d'un ecran tactile LVGL (HASPmota ou LVGL pur), sans rien de propre aux debits : choix et chargement
# de l'interface presente sur le FS, veille par inactivite (gradation puis extinction, reveil au toucher sans actionner le
# bouton touche), luminosite par l'expandeur d'E/S I2C 0x24 du Waveshare ESP32-S3-Touch-LCD-7B (sens du PWM reglable), reglages
# bornes dans le persist, historique circulaire de N series pour une courbe. Le module metier (ecranDebitsFonctions) s'appuie dessus.
# SOLIDIFIABLE (consigne du 2026-11-11, solidification a faire plus tard, apres validation sur carte) : fonctions nommees affectees
# au module, appels par ecranFonctions.<nom>, aucun appel tasmota au niveau fichier, et l'ETAT ne vit pas dans la table du module
# (en lecture seule une fois solidifie, piege 12 de outils_docs/SOLIDIFICATION_BERRY.md) mais dans la globale cachee
# ".ecranFonctions", lue et ecrite par member/setmember. Pour l'instant dans le dossier de la carte, compile en .bec par l'autoexec.
# Reglages : bloc du persist modules.<bloc> (bloc pose par le driver, ex. "ecranDebits") : veille, extinction, luminosite, pwmInverse.
# Logs : charte du CLAUDE.md (logFonctions.log, sans cible : seuil `general`).
var ecranFonctions = module("ecranFonctions")

# Reglages generiques du persist : [minimum, maximum, defaut, unite]
ecranFonctions.BORNES = {"veille": [0, 120, 5, "min"], "extinction": [0, 240, 30, "min"], "luminosite": [10, 100, 80, "%"]}
ecranFonctions.GRADATION = 10        # % de luminosite apres `veille` minutes sans toucher
ecranFonctions.HISTO_POINTS = 60     # points par serie de l'historique (30 min a un point toutes les 30 s)
ecranFonctions.HISTO_PAS = 30000     # ms entre deux points
# Expandeur d'E/S 0x24 (fiche du 7B § 3) : registre 0x03 = sorties, 0x05 = PWM du retroeclairage. ALLUME = sorties posees par
# preinit.be ; ETEINT = les memes avec EXIO2 (bit 2, retroeclairage) a 0 : alimentation de la dalle (EXIO6) et resets intacts.
ecranFonctions.DELAI_SAUVE = 3000    # ms sans appui avant d'ecrire le persist
ecranFonctions.ID_SAUVE = "ecranFonctions_sauve"
ecranFonctions.REESSAI = 10000       # ms entre deux essais d'ecriture de la luminosite quand l'expandeur ne repond pas
ecranFonctions.EXPANDEUR = 0x24
ecranFonctions.ALLUME = 0xDF
ecranFonctions.ETEINT = 0xDB

# Etat (globale cachee) :
#   bloc       : nom du bloc modules.<bloc> du persist qui porte les reglages (nil : valeurs par defaut)
#   interface  : module d'interface demarre (nil : pas d'ecran)
#   etatVeille : luminosite appliquee : 100 allume, GRADATION, 0 eteint ; nil = a (re)ecrire
#   panne      : vrai tant que l'ecriture I2C de la luminosite echoue (une erreur au premier echec, un message debug au retablissement)
#   reessaiA   : tasmota.millis() du dernier echec I2C (nouvel essai toutes les REESSAI ms) ; nil = pas d'echec en cours
#   voile      : objet LVGL transparent qui avale le toucher du reveil
#   histo      : liste de series, chacune de HISTO_POINTS valeurs (nil = inconnu), du plus vieux au plus recent
#   histoA     : tasmota.millis() du dernier point ; points : nombre de points ajoutes depuis le demarrage
def ecranFonctions_etat()
    import global
    if !global.contains(".ecranFonctions")
        global.(".ecranFonctions") = {"bloc": nil, "interface": nil, "etatVeille": nil, "panne": false, "reessaiA": nil, "voile": nil, "histo": nil, "histoA": nil, "points": 0}
    end
    return global.(".ecranFonctions")
end
ecranFonctions.etat = ecranFonctions_etat

def ecranFonctions_member(nom)
    import undefined
    import ecranFonctions
    var etat = ecranFonctions.etat()
    return etat.contains(nom) ? etat[nom] : undefined
end
ecranFonctions.member = ecranFonctions_member

def ecranFonctions_setmember(nom, valeur)
    import ecranFonctions
    var etat = ecranFonctions.etat()
    if !etat.contains(nom)    raise "attribute_error", "ecranFonctions n'a pas de " + str(nom)    end   # nom inconnu : erreur, comme une table figee
    etat[nom] = valeur
end
ecranFonctions.setmember = ecranFonctions_setmember

# Log du module sous le seuil `general` ; niveau = constante LOG_LEVEL_*
def ecranFonctions_log(msg, niveau)
    logFonctions.log(msg, niveau)
end
ecranFonctions.log = ecranFonctions_log

# Bloc du persist des reglages (map vide si absent)
def ecranFonctions_persist()
    import ecranFonctions
    var b = ecranFonctions.bloc
    return (b != nil && modules.contains(b)) ? modules[b] : {}
end
ecranFonctions.persist = ecranFonctions_persist

# Reglage `cle` du persist, borne par `bornes` ([min, max, defaut, unite] ; nil = ecranFonctions.BORNES[cle]) ; defaut si
# absent ou illisible (persist edite a la main)
def ecranFonctions_reglage(cle, bornes)
    import ecranFonctions
    var b = bornes != nil ? bornes : ecranFonctions.BORNES[cle]
    var v = ecranFonctions.persist().find(cle, b[2])
    return (type(v) == "int" && v >= b[0] && v <= b[1]) ? v : b[2]
end
ecranFonctions.reglage = ecranFonctions_reglage

# Ecriture du persist apres DELAI_SAUVE ms sans nouvel appui (rappel du timer d'identifiant ID_SAUVE)
def ecranFonctions_sauve()
    import persist
    persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien
end
ecranFonctions.sauve = ecranFonctions_sauve

# Ecrit le reglage `cle` (bornes verifiees) ; la luminosite sera reappliquee au prochain suitVeille. false si refuse.
# differe : applique en RAM tout de suite mais n'ecrit le persist qu'apres DELAI_SAUVE ms sans nouvel appel (boutons - / +,
# un appui = un appel) ; sinon ecriture immediate (commande, geste unique).
def ecranFonctions_regle(cle, n, bornes, differe)
    import persist
    import ecranFonctions
    var b = bornes != nil ? bornes : ecranFonctions.BORNES.find(cle)
    if (b == nil || type(n) != "int" || n < b[0] || n > b[1] || ecranFonctions.bloc == nil)    return false    end
    if (!modules.contains(ecranFonctions.bloc))    modules[ecranFonctions.bloc] = {}    end
    modules[ecranFonctions.bloc][cle] = n
    if (differe)
        tasmota.remove_timer(ecranFonctions.ID_SAUVE)
        tasmota.set_timer(ecranFonctions.DELAI_SAUVE, ecranFonctions.sauve, ecranFonctions.ID_SAUVE)
    else
        persist.save(true)
    end
    ecranFonctions.etatVeille = nil
    return true
end
ecranFonctions.regle = ecranFonctions_regle

# Sens du PWM de l'expandeur : "ON" (defaut, d'apres la demo Waveshare) = valeur haute -> ecran sombre. A VERIFIER sur la carte.
def ecranFonctions_pwmInverse()
    import ecranFonctions
    return ecranFonctions.persist().find("pwmInverse", "ON") != "OFF"
end
ecranFonctions.pwmInverse = ecranFonctions_pwmInverse

# Retroeclairage par l'expandeur 0x24 : pct 0 = eteint (EXIO2 a 0), sinon PWM (registre 0x05) puis EXIO2 a 1. Le rapport
# cyclique est borne a 5..97 % comme la demo : un sens du PWM faux (pwmInverse) donne un ecran faible, jamais noir. true si ecrit.
def ecranFonctions_lumiere(pct)
    import ecranFonctions
    var x = ecranFonctions.EXPANDEUR
    var w = tasmota.wire_scan(x)
    var ok = w != nil
    if (ok && pct == 0)
        ok = w.write(x, 0x03, ecranFonctions.ETEINT, 1)
    elif (ok)
        var r = ecranFonctions.pwmInverse() ? 100 - pct : pct
        r = r < 5 ? 5 : (r > 97 ? 97 : r)
        ok = w.write(x, 0x05, r * 255 / 100, 1) && w.write(x, 0x03, ecranFonctions.ALLUME, 1)
    end
    return ok
end
ecranFonctions.lumiere = ecranFonctions_lumiere

# Temps sans toucher l'ecran (ms) d'apres LVGL : marche avec les deux interfaces. 0 sans ecran demarre (pas de veille).
def ecranFonctions_inactivite()
    import ecranFonctions
    if (ecranFonctions.interface == nil)    return 0    end
    try
        import lv
        return lv.disp().get_inactive_time()
    except ..
        return 0
    end
end
ecranFonctions.inactivite = ecranFonctions_inactivite

# Voile transparent sur toute la dalle (lv.layer_sys, comme le DimmedPanel de HASPmota) tant que l'ecran est assombri ou
# eteint : le toucher qui le reveille ne declenche pas le bouton dessous (un « - » de la page Reglages)
def ecranFonctions_poseVoile(pose)
    import ecranFonctions
    try
        import lv
        if (pose && ecranFonctions.voile == nil)
            var p = lv.obj(lv.layer_sys())
            p.set_style_radius(0, 0)
            p.set_style_border_width(0, 0)
            p.set_style_bg_opa(0, 0)
            p.set_pos(0, 0)
            p.set_width(lv.get_hor_res())
            p.set_height(lv.get_ver_res())
            p.set_clickable(true)
            ecranFonctions.voile = p
        elif (!pose && ecranFonctions.voile != nil)
            ecranFonctions.voile.del()
            ecranFonctions.voile = nil
        end
    except .. as e, m
        ecranFonctions.log("ECRAN_ERREUR: voile de veille : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
end
ecranFonctions.poseVoile = ecranFonctions_poseVoile

# Veille (appelee tous les 250 ms, callback frequent : pas de log info) : apres `veille` min sans toucher, GRADATION %, puis
# eteint `extinction` min plus tard (0 = jamais eteint) ; un toucher rend la luminosite reglee. I2C ecrit aux seuls changements ;
# en cas d'echec (expandeur muet au demarrage) l'etat reste a (re)ecrire : nouvel essai toutes les REESSAI ms, une erreur au premier echec.
def ecranFonctions_suitVeille()
    import ecranFonctions
    var v = ecranFonctions.reglage("veille") * 60000
    var x = ecranFonctions.reglage("extinction") * 60000
    var ms = ecranFonctions.inactivite()
    var cible = 100
    if (v > 0 && ms >= v)    cible = (x > 0 && ms >= v + x) ? 0 : ecranFonctions.GRADATION    end
    if (cible == ecranFonctions.etatVeille)    return    end
    var t = tasmota.millis()
    var a = ecranFonctions.reessaiA
    if (a != nil && t >= a && t - a < ecranFonctions.REESSAI)    return    end
    var pct = cible == 100 ? ecranFonctions.reglage("luminosite") : cible
    if (ecranFonctions.lumiere(pct))
        ecranFonctions.etatVeille = cible
        ecranFonctions.reessaiA = nil
        if (ecranFonctions.panne)
            ecranFonctions.panne = false
            ecranFonctions.log("ECRAN: retabli, expandeur 0x24 joint, luminosite " + str(pct) + " % appliquee !", LOG_LEVEL_DEBUG)
        end
    else
        ecranFonctions.reessaiA = t
        if (!ecranFonctions.panne)
            ecranFonctions.panne = true
            ecranFonctions.log("ECRAN_ERREUR: expandeur 0x24 absent ou sans ACK, luminosite " + str(pct) + " % non appliquee, nouvel essai toutes les 10 s !", LOG_LEVEL_ERREUR)
        end
    end
    if (ecranFonctions.interface != nil)    ecranFonctions.poseVoile(cible < 100)    end
end
ecranFonctions.suitVeille = ecranFonctions_suitVeille

# Module d'interface present sur le FS, le premier de `noms` (["ecranHaspmota", "ecranLvgl"]) dont le .bec ou le .be existe ;
# plusieurs : le premier, ligne info ; aucun : erreur, nil (la carte reste vivante, sans ecran)
def ecranFonctions_charge(noms)
    import path
    import demarrage
    import ecranFonctions
    var presents = []
    for n: noms
        if (path.exists("/" + n + ".bec") || path.exists("/" + n + ".be"))    presents.push(n)    end
    end
    if (size(presents) == 0)
        ecranFonctions.log("ECRAN_ERREUR: aucune interface d'ecran sur le FS (" + noms.concat(" ou ") + ") : ecran noir !", LOG_LEVEL_ERREUR)
        return nil
    end
    if (size(presents) > 1)
        ecranFonctions.log("ECRAN: " + presents.concat(" et ") + " presents, " + presents[0] + " retenue (custom_interface_ecran du cenv) !", LOG_LEVEL_INFO)
    end
    return demarrage.importeUn(presents[0])
end
ecranFonctions.charge = ecranFonctions_charge

# Demarre le module d'interface `itf` (sa fonction demarre()) et le retient ; nil ou echec : pas d'ecran
def ecranFonctions_demarre(itf)
    import ecranFonctions
    ecranFonctions.interface = nil
    if (itf == nil || !itf.demarre())    return false    end
    ecranFonctions.interface = itf
    return true
end
ecranFonctions.demarre = ecranFonctions_demarre

# Historique : un point par serie (valeurs : liste, nil = inconnu) toutes les HISTO_PAS ms, le premier tout de suite, le plus
# vieux retire. Cadence sur tasmota.millis() : l'heure (rtc) saute a la synchro NTP. true si un point a ete ajoute.
def ecranFonctions_echantillonne(valeurs)
    import ecranFonctions
    var t = tasmota.millis()
    var a = ecranFonctions.histoA
    if (a != nil && t >= a && t - a < ecranFonctions.HISTO_PAS)    return false    end
    ecranFonctions.histoA = t
    if (ecranFonctions.histo == nil)
        var h = []
        for i: 1 .. size(valeurs)
            var l = []
            l.resize(ecranFonctions.HISTO_POINTS)   # nil partout : courbe vide avant les premiers points
            h.push(l)
        end
        ecranFonctions.histo = h
    end
    for i: 0 .. size(valeurs) - 1
        var l = ecranFonctions.histo[i]
        l.remove(0)
        l.push(valeurs[i])
    end
    ecranFonctions.points = ecranFonctions.points + 1
    return true
end
ecranFonctions.echantillonne = ecranFonctions_echantillonne

# Plus grande valeur connue de l'historique (0 s'il est vide)
def ecranFonctions_histoMax()
    import ecranFonctions
    var max = 0
    for l: (ecranFonctions.histo == nil ? [] : ecranFonctions.histo)
        for v: l
            if (v != nil && v > max)    max = v    end
        end
    end
    return max
end
ecranFonctions.histoMax = ecranFonctions_histoMax

# Retourne le module lors de l'importation
return ecranFonctions
