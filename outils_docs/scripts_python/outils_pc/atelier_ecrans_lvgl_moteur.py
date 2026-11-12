"""Moteur Berry fixe du module ecranLvgl genere par atelier_ecrans_lvgl.py : le meme texte pour toute description, ajoute
apres les tables tirees de la description (lu dans lv_haspmota.be)."""

# Moteur fixe, le meme pour toute description (fonctions nommees, aucune fonction anonyme). Lu dans lv_haspmota.be.
MOTEUR = r'''
# ---- Moteur (identique pour toute description) ----
# Classe LVGL d'un type HASPmota dont le nom differe (lv_haspmota.be : lvh_btn._lv_class = lv.button ; lv.btn n'existe pas dans
# le firmware, seul lv_button est enregistre, be_lv_c_mapping.h) ; les autres types portent le nom de leur classe
ecranLvgl.CLASSES = {"btn": "button", "img": "image", "btnmatrix": "buttonmatrix", "cpicker": "colorwheel"}
ecranLvgl.cache = {}      # "p1b13.text" -> valeur brute deja ecrite
ecranLvgl.objets = {}     # "p1b13" -> objet LVGL ; "p<n>b0" -> ecran de la page n
ecranLvgl.types = {}      # "p1b13" -> type de la description
ecranLvgl.textes = {}     # "p0b91" -> label qui porte le texte (l'objet lui-meme pour un label)
ecranLvgl.ecrans = {}     # n -> ecran de la page n
ecranLvgl.polices = {}    # forme de text_font -> police chargee (une seule fois)
ecranLvgl.touchers = []   # [objet LVGL, fonction] des objets tactiles
ecranLvgl.attente = nil   # fonction du dernier toucher, executee hors du rappel LVGL
ecranLvgl.series = nil    # series LVGL de la courbe
ecranLvgl.points = 0      # points du modele deja pousses sur la courbe
ecranLvgl.page = nil      # page affichee

# Police d'un text_font comme lv_haspmota.be::parse_font : entier = robotocondensed embarquee ; "A:<chemin>.ttf-<taille>" =
# FreeType (A: retire : lvbe_fopen ajoute le /) ; "A:<fichier>" = police binaire ; "<nom>-<taille>" = embarquee. nil si absente.
def ecranLvgl_police(f)
    import lv
    import string
    import ecranLvgl
    if (ecranLvgl.polices.contains(f))    return ecranLvgl.polices[f]    end
    var p
    try
        if (type(f) == "int")
            p = lv.font_embedded("robotocondensed", f)
        else
            var m = string.split(f, "-")
            var nom = size(m) >= 2 ? m[0 .. -2].concat("-") : f
            var taille = size(m) >= 2 ? int(m[-1]) : 0
            if (string.endswith(nom, ".ttf", true))
                p = lv.load_freetype_font(string.split(nom, ":")[-1], taille, 0)
            elif (size(string.split(f, ":", 1)) > 1)
                p = lv.load_font(f)
            else
                p = lv.font_embedded(nom, taille)
            end
        end
    except .. as e, m
        logFonctions.log("ECRAN_LVGL_ERREUR: police " + str(f) + " absente : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    ecranLvgl.polices[f] = p
    return p
end
ecranLvgl.police = ecranLvgl_police
# Label qui porte le texte de `nom` : cree au premier texte, centre sur l'objet (lvh_obj::check_label)
def ecranLvgl_texte(nom)
    import lv
    import ecranLvgl
    var t = ecranLvgl.textes.find(nom)
    if (t == nil)
        t = lv.label(ecranLvgl.objets[nom])
        t.set_align(lv.ALIGN_CENTER)
        ecranLvgl.textes[nom] = t
    end
    return t
end
ecranLvgl.texte = ecranLvgl_texte
# Selecteur partie | etat d'un suffixe a 2 chiffres (lvh_root::digits_to_style : bg_color10 = indicateur)
def ecranLvgl_selecteur(n)
    import lv
    var parties = [lv.PART_MAIN, lv.PART_INDICATOR, lv.PART_KNOB, lv.PART_ITEMS, lv.PART_ITEMS, lv.PART_SELECTED, lv.PART_ITEMS,
                   lv.PART_CURSOR, lv.PART_SCROLLBAR, lv.PART_CUSTOM_FIRST]
    var etats = [lv.STATE_DEFAULT, lv.STATE_CHECKED, lv.STATE_PRESSED, lv.STATE_CHECKED | lv.STATE_PRESSED, lv.STATE_DISABLED,
                 lv.STATE_DISABLED | lv.STATE_PRESSED]
    if (n % 10 >= size(etats))    raise "value_error", "suffixe de style " + str(n) + " invalide"    end
    return parties[n / 10] | etats[n % 10]
end
ecranLvgl.selecteur = ecranLvgl_selecteur
# Applique l'attribut `k` (valeur brute de la description ou du modele) a l'objet `nom`, comme lvh_obj::setmember
def ecranLvgl_applique(nom, k, v)
    import lv
    import string
    import introspect
    import ecranLvgl
    var o = ecranLvgl.objets[nom]
    var t = ecranLvgl.types[nom]
    var c = ecranLvgl.cache
    if (k == "text")    ecranLvgl.texte(nom).set_text(str(v))    return    end
    if (k == "align")
        var a = {0: lv.TEXT_ALIGN_LEFT, 1: lv.TEXT_ALIGN_CENTER, 2: lv.TEXT_ALIGN_RIGHT, "left": lv.TEXT_ALIGN_LEFT,
                 "center": lv.TEXT_ALIGN_CENTER, "right": lv.TEXT_ALIGN_RIGHT}
        ecranLvgl.texte(nom).set_style_text_align(a.find(v, lv.TEXT_ALIGN_LEFT), 0)
        return
    end
    if (k == "text_font")
        var p = ecranLvgl.police(v)
        if (p != nil)    o.set_style_text_font(p, 0)    end
        return
    end
    if (k == "val")    if (t == "bar" || t == "slider")    o.set_value(v, lv.ANIM_OFF)    else    o.set_value(v)    end    return    end
    if (k == "min")    o.set_range(v, o.get_max_value())    return    end
    if (k == "max")    o.set_range(o.get_min_value(), v)    return    end
    if (k == "y_min" || k == "y_max")
        var mini = k == "y_min" ? v : c.find(nom + ".y_min", 0)
        o.set_axis_range(lv.CHART_AXIS_PRIMARY_Y, mini, k == "y_max" ? v : c.find(nom + ".y_max", 100))
        return
    end
    if (k == "h_div_line_count" || k == "v_div_line_count")
        o.set_div_line_count(k == "h_div_line_count" ? v : c.find(nom + ".h_div_line_count", 3),
                             k == "v_div_line_count" ? v : c.find(nom + ".v_div_line_count", 5))
        return
    end
    var sel = nil
    if (string.endswith(k, "%"))    k = k[0 .. -2]    v = lv.pct(v)    end
    if (size(k) > 2 && string.find("0123456789", k[-1]) >= 0 && string.find("0123456789", k[-2]) >= 0)
        sel = ecranLvgl.selecteur(int(k[-2 ..]))
        k = k[0 .. -3]
    end
    if (string.endswith(k, "color"))    v = lv.color(v)    end
    var f = sel == nil ? introspect.get(o, "set_" + k) : nil
    if (type(f) == "function")    f(o, v)    return    end
    f = introspect.get(o, "set_style_" + k)
    if (type(f) != "function")    raise "attribute_error", "attribut " + k + " inconnu de " + nom    end
    f(o, v, sel == nil ? 0 : sel)
end
ecranLvgl.applique = ecranLvgl_applique
# Ecrit l'attribut `k` de `nom` seulement s'il a change ; valeur nil ou objet absent : rien
def ecranLvgl_ecris(nom, k, v)
    import ecranLvgl
    var c = nom + "." + k
    if (v == nil || ecranLvgl.cache.find(c) == v)    return    end
    if (!ecranLvgl.objets.contains(nom))    return    end
    ecranLvgl.applique(nom, k, v)
    ecranLvgl.cache[c] = v
end
ecranLvgl.ecris = ecranLvgl_ecris
# Valeur du modele au bout de `chemin` (["a", 0, "b"] = m["a"][0]["b"]) ; nil si un maillon manque
def ecranLvgl_valeur(m, chemin)
    var v = m
    for s: chemin
        if (v == nil)    return nil    end
        v = type(s) == "int" ? (s < size(v) ? v[s] : nil) : v.find(s)
    end
    return v
end
ecranLvgl.valeur = ecranLvgl_valeur
# Page n (PAGES : [n, [[attribut, valeur]]]) : page 0 sur lv.layer_top() transparente, fond (bg_*) sur lv.layer_bottom() ;
# sinon un ecran lv.obj(0) transparent, opaque des qu'il a un bg_color (lvh_page::init, lvh_scr::setmember)
def ecranLvgl_preparePage(p)
    import lv
    import string
    import ecranLvgl
    var n = p[0]
    var nom = "p" + str(n) + "b0"
    var e = n == 0 ? lv.layer_top() : lv.obj(0)
    e.set_style_bg_opa(0, 0)
    if (n == 0)    lv.layer_bottom().set_style_bg_opa(255, 0)    end
    ecranLvgl.ecrans[n] = e
    ecranLvgl.types[nom] = "scr"
    for a: p[1]
        ecranLvgl.objets[nom] = (n == 0 && string.startswith(a[0], "bg_")) ? lv.layer_bottom() : e
        if (n != 0 && a[0] == "bg_color")    e.set_style_bg_opa(255, 0)    end
        ecranLvgl.ecris(nom, a[0], a[1])
    end
    ecranLvgl.objets[nom] = e
end
ecranLvgl.preparePage = ecranLvgl_preparePage
# Objet d (OBJETS) cree sur l'ecran de sa page, place, attributs ecrits par le cache, toucher sur EVENT_CLICKED
def ecranLvgl_cree(d)
    import lv
    import ecranLvgl
    var nom = "p" + str(d[0]) + "b" + str(d[1])
    var o = lv.(ecranLvgl.CLASSES.find(d[2], d[2]))(ecranLvgl.ecrans[d[0]])
    o.set_pos(d[3], d[4])
    o.set_size(d[5], d[6])
    ecranLvgl.objets[nom] = o
    ecranLvgl.types[nom] = d[2]
    if (d[2] == "label")    ecranLvgl.textes[nom] = o    end
    if (d[2] == "chart")    o.set_update_mode(lv.CHART_UPDATE_MODE_SHIFT)    end
    for a: d[7]    ecranLvgl.ecris(nom, a[0], a[1])    end
    if (d[8] != nil)
        o.add_event_cb(ecranLvgl.evenement, lv.EVENT_CLICKED, 0)
        ecranLvgl.touchers.push([o, d[8]])
    end
end
ecranLvgl.cree = ecranLvgl_cree
# Series de la courbe (COURBE), sur l'axe primaire, sans pastille de point
def ecranLvgl_prepareCourbe()
    import lv
    import ecranLvgl
    ecranLvgl.series = nil
    ecranLvgl.points = 0
    var c = ecranLvgl.COURBE
    if (c == nil || !ecranLvgl.objets.contains(c[0]))    return    end
    var o = ecranLvgl.objets[c[0]]
    o.set_style_size(0, 0, lv.PART_INDICATOR)
    o.set_style_line_width(3, lv.PART_ITEMS)
    var s = []
    for coul: c[3]    s.push(o.add_series(lv.color(coul), lv.CHART_AXIS_PRIMARY_Y))    end
    ecranLvgl.series = s
end
ecranLvgl.prepareCourbe = ecranLvgl_prepareCourbe
# Pousse sur la courbe les points du modele pas encore traces (tous au premier passage, set_next_value)
def ecranLvgl_trace(m)
    import lv
    import ecranLvgl
    var c = ecranLvgl.COURBE
    var s = ecranLvgl.series
    if (s == nil)    return    end
    var o = ecranLvgl.objets[c[0]]
    var h = ecranLvgl.valeur(m, c[1])
    var p = ecranLvgl.valeur(m, c[2])
    var n = (p == nil ? 0 : p) - ecranLvgl.points
    if (h == nil || size(h) == 0 || n <= 0)    return    end
    var t = size(h[0])
    if (n > t)    n = t    end
    for i: 0 .. size(s) - 1
        if (i >= size(h))    break    end
        for k: t - n .. t - 1
            var v = h[i][k]
            o.set_next_value(s[i], v == nil ? lv.CHART_POINT_NONE : v)
        end
    end
    ecranLvgl.points = p
end
ecranLvgl.trace = ecranLvgl_trace
# Boutons qui menent a une page : couleurs `actif` pour la page courante, les autres sinon (par le cache)
def ecranLvgl_actifs()
    import ecranLvgl
    for a: ecranLvgl.ACTIFS
        var i = ecranLvgl.page == a[1] ? 0 : 1
        for k: a[2].keys()    ecranLvgl.ecris(a[0], k, a[2][k][i])    end
    end
end
ecranLvgl.actifs = ecranLvgl_actifs
# Affiche la page n (n >= 1) et met a jour les boutons de page
def ecranLvgl_montre(n)
    import lv
    import ecranLvgl
    var e = ecranLvgl.ecrans.find(n)
    if (e == nil || n == 0)    return    end
    lv.screen_load(e)
    ecranLvgl.page = n
    ecranLvgl.actifs()
end
ecranLvgl.montre = ecranLvgl_montre
# Rappel LVGL d'un objet tactile (EVENT_CLICKED) : son action est differee hors de la boucle LVGL
def ecranLvgl_evenement(obj, event)
    import ecranLvgl
    for t: ecranLvgl.touchers
        if (t[0] == obj)
            ecranLvgl.attente = t[1]
            tasmota.defer(ecranLvgl.execute)
            return
        end
    end
end
ecranLvgl.evenement = ecranLvgl_evenement
# Action du dernier toucher (tasmota.defer) ; echec journalise
def ecranLvgl_execute()
    import ecranLvgl
    var f = ecranLvgl.attente
    ecranLvgl.attente = nil
    if (f == nil)    return    end
    try
        f()
    except .. as e, m
        logFonctions.log("ECRAN_LVGL_ERREUR: action du toucher en echec : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
end
ecranLvgl.execute = ecranLvgl_execute
# Demarre LVGL et cree les pages et les objets de la description ; false (erreur journalisee) si l'ecran n'est pas pret
def ecranLvgl_demarre()
    import lv
    import display
    import ecranLvgl
    try
        if (!display.started())
            logFonctions.log("ECRAN_LVGL_ERREUR: ecran non demarre (display.ini, preinit.be) !", LOG_LEVEL_ERREUR)
            return false
        end
        lv.start()
        ecranLvgl.cache = {}
        ecranLvgl.objets = {}
        ecranLvgl.types = {}
        ecranLvgl.textes = {}
        ecranLvgl.ecrans = {}
        ecranLvgl.touchers = []
        for p: ecranLvgl.PAGES    ecranLvgl.preparePage(p)    end
        for d: ecranLvgl.OBJETS    ecranLvgl.cree(d)    end
        ecranLvgl.prepareCourbe()
        ecranLvgl.montre(ecranLvgl.DEPART)
        logFonctions.log("ECRAN_LVGL: " + str(size(ecranLvgl.OBJETS)) + " objets crees sur " + str(size(ecranLvgl.PAGES)) + " pages !", LOG_LEVEL_INFO)
        return true
    except .. as e, m
        logFonctions.log("ECRAN_LVGL_ERREUR: ecran non cree : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    return false
end
ecranLvgl.demarre = ecranLvgl_demarre
# Ecrit le modele (chaque seconde) : liaisons, couleurs selon une valeur, boutons de page, courbe ; seul ce qui change part
def ecranLvgl_affiche(m)
    import string
    import ecranLvgl
    if (size(ecranLvgl.objets) == 0)    return    end
    for l: ecranLvgl.LIAISONS
        var v = ecranLvgl.valeur(m, l[1])
        if (l[3] != nil || l[4] != nil)
            var c = (v != nil && l[4] != nil) ? l[4].find(v) : nil
            if (c == nil)    c = l[3] != nil ? (v != nil ? ecranLvgl.COULEURS[l[3]].find(v) : nil) : l[5]    end
            v = c
        end
        if (v != nil && l[7] != nil)    v = v / l[7]    end
        if (v != nil && l[6] != nil)    v = string.format(l[6], v)    end
        ecranLvgl.ecris(l[0], l[2], v)
    end
    ecranLvgl.actifs()
    ecranLvgl.trace(m)
end
ecranLvgl.affiche = ecranLvgl_affiche
# Retourne le module lors de l'importation
return ecranLvgl
'''
