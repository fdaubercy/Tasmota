# Définition du module
var displayFonctions = module("/displayFonctions")

# Affiche la page d'accueil
displayFonctions.afficheAccueil = def()
    #- start LVGL and init environment -#
    lv.start()

    # var scr1 = lv.obj_create(None, None);
    # var scr2  = lv.obj_create(None, None);
    # lv.scr_load(scr1);

    var hres = lv.get_hor_res()       # should be 320
    var vres = lv.get_ver_res()       # should be 240

    var scr = lv.scr_act()            # default screen object
    var f20 = lv.montserrat_font(20)  # load embedded Montserrat 20
    var f28 = lv.montserrat_font(28)  # load embedded Montserrat 28

    #- Background with a gradient from black #000000 (bottom) to dark blue #0000A0 (top) -#
    scr.set_style_bg_color(lv.color(0x000000), lv.PART_MAIN | lv.STATE_DEFAULT)
    scr.set_style_bg_grad_color(lv.color(0x000000), lv.PART_MAIN | lv.STATE_DEFAULT)
    scr.set_style_bg_grad_dir(lv.GRAD_DIR_VER, lv.PART_MAIN | lv.STATE_DEFAULT)

    #- Upper state line -#
    var stat_line = lv.label(scr)
    if f28 != nil stat_line.set_style_text_font(f28, lv.PART_MAIN | lv.STATE_DEFAULT) end
    stat_line.set_long_mode(lv.LABEL_LONG_SCROLL)                                        # auto scrolling if text does not fit
    stat_line.set_width(hres)
    stat_line.set_align(lv.TEXT_ALIGN_LEFT)                                              # align text left
    stat_line.set_style_bg_color(lv.color(0xD00000), lv.PART_MAIN | lv.STATE_DEFAULT)    # background #000088
    stat_line.set_style_bg_opa(lv.OPA_COVER, lv.PART_MAIN | lv.STATE_DEFAULT)            # 100% background opacity
    stat_line.set_style_text_color(lv.color(0xFFFFFF), lv.PART_MAIN | lv.STATE_DEFAULT)  # text color #FFFFFF
    stat_line.set_text("Telemetrie PAC")
    stat_line.refr_size()                                                                # new in LVGL8
    stat_line.refr_pos()                                                                 # new in LVGL8

    #- display wifi strength indicator icon (for professionals ;) -#
    var wifi_icon = lv_wifi_arcs_icon(stat_line)    # the widget takes care of positioning and driver stuff
    var clock_icon = lv_clock_icon(stat_line)


    #- create a style for the buttons -#
    var btn_style = lv.style()
    btn_style.set_radius(10)                        # radius of rounded corners
    btn_style.set_bg_opa(lv.OPA_COVER)              # 100% backgrond opacity
    if f20 != nil btn_style.set_text_font(f20) end  # set font to Montserrat 20
    btn_style.set_bg_color(lv.color(0x1fa3ec))      # background color #1FA3EC (Tasmota Blue)
    btn_style.set_border_color(lv.color(0x0000FF))  # border color #0000FF
    btn_style.set_text_color(lv.color(0xFFFFFF))    # text color white #FFFFFF

    #- Création des boutons -#
    var prev_btn = lv.btn(scr)                            # create button with main screen as parent
    prev_btn.set_pos(20, vres - 40)                      # position of button
    prev_btn.set_size(80, 30)                         # size of button
    prev_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)   # style of button
    var prev_label = lv.label(prev_btn)                   # create a label as sub-object
    prev_label.set_text("<")                          # set label text
    prev_label.center()

    var next_btn = lv.btn(scr)                            # right button
    next_btn.set_pos(220, vres - 40)
    next_btn.set_size(80, 30)
    next_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)
    var next_label = lv.label(next_btn)
    next_label.set_text(">")
    next_label.center()

    var home_btn = lv.btn(scr)                            # center button
    home_btn.set_pos(120, vres - 40)
    home_btn.set_size(80, 30)
    home_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)
    var home_label = lv.label(home_btn)
    home_label.set_text(lv.SYMBOL_OK)                 # set text as Home icon
    home_label.center()

    # Paramètre les fonctions de callBack des boutons
    prev_btn.add_event_cb(displayFonctions.btn_clicked_cb, lv.EVENT_CLICKED, 1)
    next_btn.add_event_cb(displayFonctions.btn_clicked_cb, lv.EVENT_CLICKED, 2)
    home_btn.add_event_cb(displayFonctions.btn_clicked_cb, lv.EVENT_CLICKED, 3)

    # Création d'un slider au centre de l'ecran
    var slider = lv.slider(scr)
    slider.set_pos(20,vres - 80) 
    slider.set_width(200)                                              # Set the width
    slider.center()                                                    # Align to the center of the parent (screen)
    # Création du label du slider
    var label = lv.label(scr)
    label.set_text("0")
    label.align_to(slider, lv.ALIGN_OUT_TOP_MID, 0, -15)               # Align below the slider

    # Paramètre les fonctions de callBack du slider
    slider.add_event_cb(displayFonctions.slider_event_cb, lv.EVENT_VALUE_CHANGED, None) # Assign an event function

    # Création d'une liste déroulante
    var modes = ['Auto', 'Boost', 'On', 'Off', 'Adv', 'Day']
    var modes_str = modes.concat('\n')
    var ddlist = lv.dropdown(scr)
    ddlist.set_options(modes_str)
    ddlist.set_pos(20, vres - 180)
    # ddlist.center()

    # Paramètre les fonctions de callBack de la liste déroulante
    ddlist.add_event_cb(displayFonctions.dropdown_changed_cb, lv.EVENT_ALL, None)
end

displayFonctions.buzzer_enable = def()
    tasmota.cmd("buzzerpwm 1") # use PWM on buzzer pin (GPIO21)
    tasmota.cmd("pwmfrequency 1000") # highest volume at 2700 as per datasheet of LET7525AS-3.6L-2.7-15-R
    tasmota.cmd("setoption111 1")
end

#- fonctions de callBack quand un bouton est clické, reagit à 'EVENT_CLICKED' -#
displayFonctions.btn_clicked_cb = def(obj, event)
    print(obj)
    # var btn = "Unknown"
    # if   obj == prev_btn  btn = "Prev"
    # elif obj == next_btn  btn = "Next"
    # elif obj == home_btn  btn = "Home"
    # end
    # print(btn, "button pressed")
    # tasmota.cmd("buzzer 1")
    # tasmota.publish("tele/tasmota232/SENSOR/Buttom",btn)
end

displayFonctions.slider_event_cb = def(obj, event)
    var slider = "Unknown"
    var value = "999"

    # if obj == slider  
	# 	slider= "SLIDER"
    # # elif obj == next_slider  
	# 	# slider= "Next"
    # # elif obj == home_btn
	# 	# slider= "Home"
    # end

    # value = obj.get_value()

    # # Refresh the text
    # # label.set_text(str(value))
    # print("slider set:", str(value))
   
    # tasmota.publish("tele/ESP32-2432S028/SENSOR/Slider", str(value))
end

displayFonctions.dropdown_changed_cb = def(obj, event)
    # var option = "Unknown"

    # var modes = ['Auto', 'Boost', 'On', 'Off', 'Adv', 'Day' ]

    # var code = event.code

    # if code == lv.EVENT_VALUE_CHANGED
    #    print("Dropdown code :", code )
    #    option = obj.get_selected()
   
    #    print("Dropdown set:", modes[option])
   
    #    tasmota.publish("tele/ESP32-2432S028/SENSOR/Dropdown", modes[option] )
    #  end
end

# Retourne le module lors de l'importation
return displayFonctions