# Définition du module
var displayFonctions = module("/displayFonctions")

displayFonctions.definiBackground = def(page)
    #var page = lv.scr_act()

    #- Background with a gradient from black #000000 (bottom) to dark blue #0000A0 (top) -#
    page.set_style_bg_color(lv.color(0x000000), lv.PART_MAIN | lv.STATE_DEFAULT)
    page.set_style_bg_grad_color(lv.color(0x000000), lv.PART_MAIN | lv.STATE_DEFAULT)
    page.set_style_bg_grad_dir(lv.GRAD_DIR_VER, lv.PART_MAIN | lv.STATE_DEFAULT)
end

displayFonctions.definiBandeauPage = def(police)
    var stat_line
    var hres = lv.get_hor_res()
    var page = lv.scr_act()

    #- Ligne de données en haut de page -#
    stat_line = lv.label(page)
    if police != nil stat_line.set_style_text_font(police, lv.PART_MAIN | lv.STATE_DEFAULT) end
    stat_line.set_long_mode(lv.LABEL_LONG_SCROLL)                                        # auto scroll si le texte dépasse
    stat_line.set_width(hres)
    stat_line.set_align(lv.TEXT_ALIGN_LEFT)                                              # Texte aligné à gauche
    stat_line.set_style_bg_color(lv.color(0xD00000), lv.PART_MAIN | lv.STATE_DEFAULT)    # Background #000088
    stat_line.set_style_bg_opa(lv.OPA_COVER, lv.PART_MAIN | lv.STATE_DEFAULT)            # Opacité: 100% 
    stat_line.set_style_text_color(lv.color(0xFFFFFF), lv.PART_MAIN | lv.STATE_DEFAULT)  # Couleur du texte: #FFFFFF
    stat_line.set_text("Telemetrie PAC")
    stat_line.refr_size()
    stat_line.refr_pos()

    return stat_line
end

displayFonctions.creeStyleBTN = def(police)
    #- Crée le style pour les boutons -#
    var btn_style = lv.style()

    btn_style.set_radius(10)
    btn_style.set_bg_opa(lv.OPA_COVER)
    if police != nil btn_style.set_text_font(police) end
    btn_style.set_bg_color(lv.color(0x1fa3ec))      # Couleur background: #1FA3EC (Tasmota Blue)
    btn_style.set_border_color(lv.color(0x0000FF))  # Couleur des bordures: #0000FF
    btn_style.set_text_color(lv.color(0xFFFFFF))    # Couleur du texte: #FFFFFF (Blanc)

    return btn_style
end

displayFonctions.creeBTN = def(btn_style)
    var page = lv.scr_act()
    var hres = lv.get_hor_res()
    var vres = lv.get_ver_res() 

    #- Crée le bouton de gauche -#
    var prev_btn = lv.btn(page)                            # Crée le bouton sur sur le screen 1
    prev_btn.set_pos(20, vres - 60)                   # Position
    prev_btn.set_size(80, 30)                         # Taille
    prev_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)   # Style

    var prev_label = lv.label(prev_btn)                   # Label du bouton
    prev_label.set_text("<")
    prev_label.center()
end

# Affiche la page d'accueil
displayFonctions.afficheAccueil = def(btn_style)
    var page = lv.scr_act()
    var hres = lv.get_hor_res()
    var vres = lv.get_ver_res() 

    #- Crée le bouton de gauche -#
    var prev_btn = lv.btn(page)                            # Crée le bouton sur sur le screen 1
    prev_btn.set_pos(20, vres - 60)                   # Position
    prev_btn.set_size(80, 30)                         # Taille
    prev_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)   # Style

    var prev_label = lv.label(prev_btn)                   # Label du bouton
    prev_label.set_text("<")
    prev_label.center()

    #- Crée le bouton central -#
    var home_btn = lv.btn(page)
    home_btn.set_pos((hres / 2) - (80 / 2), vres - 60)
    home_btn.set_size(80, 30)
    home_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)
    
    var home_label = lv.label(home_btn)
    home_label.set_text(lv.SYMBOL_OK)                 # Icone 'Home'
    home_label.center()

    #- Crée le bouton de droite -#
    var next_btn = lv.btn(page)
    next_btn.set_pos(hres - 20 - 80, vres - 60)
    next_btn.set_size(80, 30)
    next_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)

    var next_label = lv.label(next_btn)
    next_label.set_text(">")
    next_label.center()



    # prev_btn.add_event_cb(displayFonctions.btn_clicked_cb, lv.EVENT_CLICKED, 0)
#   home_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)
#   next_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)
end

displayFonctions.buzzer_enable = def()
    tasmota.cmd("buzzerpwm 1") # use PWM on buzzer pin (GPIO21)
    tasmota.cmd("pwmfrequency 1000") # highest volume at 2700 as per datasheet of LET7525AS-3.6L-2.7-15-R
    tasmota.cmd("setoption111 1")
end

#- fonctions de Callback pour les boutons, reagi à EVENT_CLICKED -#
displayFonctions.btn_clicked_cb = def(obj, event)
    # var btn = "Unknown"
    # if   obj == prev_btn  btn = "Prev"
    # elif obj == next_btn  btn = "Next"
    # elif obj == home_btn  btn = "Home"
    # end
    # print(btn, "button pressed")
end

# Retourne le module lors de l'importation
return displayFonctions