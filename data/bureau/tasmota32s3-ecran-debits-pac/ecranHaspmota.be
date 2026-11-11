# Interface HASPmota de l'ecran des debits (Waveshare 7B, 1024 x 600) : dessine le modele d'ecran de ecranDebitsFonctions
# (API en tete de ecranDebitsFonctions.be) sur les objets de pages.jsonl, lu en /json/pages.jsonl (rangement de l'image plate
# du FS par gestionFileFolder). Choisie a la compilation : seule sur le FS (option custom_interface_ecran du cenv), sinon
# ecranLvgl.be. Compile en .bec par demarrage.compile, importe par controleEcranDebits.be. Non solidifie.
# Objets : page 0 (sur toutes les pages) p0b1 titre, p0b2 pastille, p0b3 releve, p0b4 total, p0b91-93 pied de page ;
# page 1 voie n : p1b<10n+1> nom, +2 barre, +3 debit, +4 unite, +5 part ; page 2 voie n : +1 puce, +2 nom, +3 debit, +4 unite,
# p2b70 courbe, p2b71 haut de l'axe ; page 3 : p3b<k>3 valeur, p3b<k>2 bouton -, p3b<k>4 bouton + (k = 2 fenetre, 3 veille,
# 4 luminosite). Le chart HASPmota n'a que 2 series natives (_ser1 sur l'axe primaire, seule _ser2 sur le secondaire ; lv_haspmota.be::lvh_chart::post_init, laissees vides) : les 6 courbes
# sont ajoutees sur l'objet LVGL dessous (_lv_obj.add_series). Sans image (consigne de l'en-tete de ecranDebitsFonctions).
# Logs : charte du CLAUDE.md (ecranDebitsFonctions.log, seuil `general`).
var ecranHaspmota = module("ecranHaspmota")

ecranHaspmota.PAGES = "/json/pages.jsonl"
# Boutons - / + de la page Reglages -> ecranDebitsFonctions.ajuste(cle, pas), par une regle HASPmota (evenement "up")
ecranHaspmota.BOUTONS = {"p3b22": ["fenetre", -1], "p3b24": ["fenetre", 1], "p3b32": ["veille", -1], "p3b34": ["veille", 1],
                         "p3b42": ["luminosite", -10], "p3b44": ["luminosite", 10]}
ecranHaspmota.cache = {}       # "p1b13.text" -> valeur deja ecrite (objets neufs : cache vide)
ecranHaspmota.series = nil     # 6 series LVGL de la courbe p2b70
ecranHaspmota.points = 0       # points du modele deja pousses sur la courbe
ecranHaspmota.courbeMax = nil

# Ecrit l'attribut `attr` de l'objet HASPmota `id` seulement s'il a change ; objet absent : rien
def ecranHaspmota_ecris(id, attr, val)
    import global
    import ecranHaspmota
    var cle = id + "." + attr
    if (ecranHaspmota.cache.find(cle) == val)    return    end
    var o = global.(id)
    if (o == nil)    return    end
    o.(attr) = val
    ecranHaspmota.cache[cle] = val
end
ecranHaspmota.ecris = ecranHaspmota_ecris

# Regle d'un bouton - / + (declencheur "hasp#p3b22#event") : un appui relache ajuste le reglage
def ecranHaspmota_bouton(valeur, declencheur)
    import string
    import ecranHaspmota
    import ecranDebitsFonctions
    if (valeur != "up")    return    end
    var b = ecranHaspmota.BOUTONS.find(string.tolower(string.split(declencheur, "#")[1]))
    if (b != nil)    ecranDebitsFonctions.ajuste(b[0], b[1])    end
end
ecranHaspmota.bouton = ecranHaspmota_bouton

# Les 6 series de la courbe (couleurs SERIES), points sans trait de point ; sans objet p2b70 : pas de courbe
def ecranHaspmota_prepareCourbe()
    import global
    import ecranHaspmota
    import ecranDebitsFonctions
    ecranHaspmota.series = nil
    ecranHaspmota.points = 0
    ecranHaspmota.courbeMax = nil
    var c = global.p2b70
    if (c == nil)    return    end
    import lv
    var o = c._lv_obj
    o.set_style_size(0, 0, lv.PART_INDICATOR)
    o.set_style_line_width(3, lv.PART_ITEMS)
    var s = []
    for coul: ecranDebitsFonctions.SERIES    s.push(o.add_series(c.parse_color(coul), lv.CHART_AXIS_PRIMARY_Y))    end
    ecranHaspmota.series = s
end
ecranHaspmota.prepareCourbe = ecranHaspmota_prepareCourbe

# Pousse sur la courbe les points du modele pas encore traces (tous au premier passage) et suit le haut de l'axe
def ecranHaspmota_trace(m)
    import global
    import lv
    import string
    import ecranHaspmota
    var s = ecranHaspmota.series
    if (s == nil)    return    end
    var o = global.p2b70._lv_obj
    if (m["courbeMax"] != ecranHaspmota.courbeMax)
        ecranHaspmota.courbeMax = m["courbeMax"]
        o.set_axis_range(lv.CHART_AXIS_PRIMARY_Y, 0, m["courbeMax"])
        ecranHaspmota.ecris("p2b71", "text", string.format("%d L/min", m["courbeMax"] / 100))
    end
    var h = m["historique"]
    var n = m["points"] - ecranHaspmota.points
    if (h == nil || n <= 0)    return    end
    var t = size(h[0])
    if (n > t)    n = t    end
    for i: 0 .. size(s) - 1
        for k: t - n .. t - 1
            var v = h[i][k]
            o.set_next_value(s[i], v == nil ? lv.CHART_POINT_NONE : v)
        end
    end
    ecranHaspmota.points = m["points"]
end
ecranHaspmota.trace = ecranHaspmota_trace

# Demarre HASPmota sur /json/pages.jsonl, prepare la courbe et les boutons de la page Reglages ; erreur journalisee sinon
def ecranHaspmota_demarre()
    import path
    import ecranHaspmota
    import ecranDebitsFonctions
    if (!path.exists(ecranHaspmota.PAGES))
        ecranDebitsFonctions.log("ECRAN_HASPMOTA_ERREUR: " + ecranHaspmota.PAGES + " absent (pages.jsonl du dossier de la carte) : ecran vide !", LOG_LEVEL_ERREUR)
        return false
    end
    try
        import display
        if (!display.started())
            ecranDebitsFonctions.log("ECRAN_HASPMOTA_ERREUR: ecran non demarre (display.ini, preinit.be) !", LOG_LEVEL_ERREUR)
            return false
        end
        import haspmota
        haspmota.start(ecranHaspmota.PAGES)
        ecranHaspmota.cache = {}    # objets neufs : tout reecrire
        ecranHaspmota.prepareCourbe()
        for id: ecranHaspmota.BOUTONS.keys()
            tasmota.add_rule("hasp#" + id + "#event", ecranHaspmota.bouton, "ecranHaspmota")
        end
        return true
    except .. as e, m
        ecranDebitsFonctions.log("ECRAN_HASPMOTA_ERREUR: HASPmota non demarre : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    return false
end
ecranHaspmota.demarre = ecranHaspmota_demarre

# Ecrit le modele (chaque seconde) : seuls les attributs changes partent vers LVGL. Pages non creees : rien.
def ecranHaspmota_affiche(m)
    import global
    import haspmota
    import ecranHaspmota
    import ecranDebitsFonctions
    if (global.p1b13 == nil)    return    end
    var e = ecranHaspmota.ecris
    var c = ecranDebitsFonctions.COULEURS
    e("p0b2", "bg_color", c[m["liaison"]])
    e("p0b3", "text", m["releve"])
    e("p0b4", "text", m["total"])
    for n: 1 .. 3
        var actif = haspmota.lvh_page_cur_idx == n
        e("p0b9" + str(n), "bg_color", actif ? c["bleu"] : "#1F2B38")
        e("p0b9" + str(n), "text_color", actif ? "#06121F" : c["normal"])
    end
    for i: 0 .. ecranDebitsFonctions.NB_VOIES - 1
        var v = m["voies"][i]
        var col = c[v["etat"]]
        var nom = (v["etat"] == "normal" || v["etat"] == "arret") ? c["normal"] : col
        var b = 10 * (i + 1)
        e("p1b" + str(b + 1), "text", v["nom"])
        e("p1b" + str(b + 1), "text_color", nom)
        e("p1b" + str(b + 2), "val", v["barre"])
        e("p1b" + str(b + 2), "bg_color10", v["etat"] == "imprecis" ? c["imprecis"] : c["bleu"])
        e("p1b" + str(b + 3), "text", v["debit"])
        e("p1b" + str(b + 3), "text_color", col)
        e("p1b" + str(b + 4), "text", v["unite"])
        e("p1b" + str(b + 5), "text", v["part"])
        e("p2b" + str(b + 2), "text", v["nom"])
        e("p2b" + str(b + 2), "text_color", nom)
        e("p2b" + str(b + 3), "text", v["debit"])
        e("p2b" + str(b + 3), "text_color", col)
        e("p2b" + str(b + 4), "text", v["unite"])
    end
    var r = m["reglages"]
    e("p3b23", "text", r["fenetre"])
    e("p3b33", "text", r["veille"])
    e("p3b43", "text", r["luminosite"])
    ecranHaspmota.trace(m)
end
ecranHaspmota.affiche = ecranHaspmota_affiche

# Retourne le module lors de l'importation
return ecranHaspmota
