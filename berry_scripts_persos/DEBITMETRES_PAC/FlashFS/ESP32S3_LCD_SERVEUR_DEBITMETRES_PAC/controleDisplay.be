#-
- Pins utilisés pour l'écran ILI9488
    VCC       - 3.3V
    GND       - GND
    CS        - IO10 = SPI CS
    RESET     - IO6  = Display Rst
    DC        - IO7  = SPI DC
    SDI/MOSI  - IO11 = SPI MOSI
    SCK       - IO12 = SPI CLK
    LED       - IO4  = RétroEcl
    SDO/MISO  - None
    T_CLK     - IO12 = SPI CLK
    T_CS      - IO9  = XPT2026 CS
    T_DIN     - IO11 = SPI MOSI
    T_DO      - IO13 = SPI MISO
    T_IRQ     - TS IRQ GPIO GPIO3 (None)

- La configuration de l'écran ILI9488 est réalisé au démarrage avec le fichier 'display.ini'
- Ne necessite pas de lancer la calibration de l'ecran Tactile: cmd=DisplayCalibrate

- Pages de référence:
    * Universal Display and Universal Touch drivers:    https://tasmota.github.io/docs/Universal-Display-Driver/#descriptor-file
    * LVGL in less than 10 minutes with Tasmota:        https://tasmota.github.io/docs/LVGL_in_10_minutes/#try-a-lvgl-demo-app
    * LVGL - Internals:                                 https://tasmota.github.io/docs/LVGL_Internals/#build-system
    * LVGL Berry API Reference:                         https://tasmota.github.io/docs/LVGL_API_Reference/
    * LVGL:                                             https://tasmota.github.io/docs/LVGL/#goodies
    * LVGL Touchscreen with 3 Relays:                   https://tasmota.github.io/docs/Berry-Cookbook/#full-example
    * Site LVGL:                                        https://lvgl.io/
    * Outils LVGL (Images & Police Converter):          https://lvgl.io/tools/imageconverter

  - Outils PNG:
    * couper une image en 3 parties -> IMage Splitter : https://splitter.imageonline.co/fr/#google_vignette
    * retirer le fond d'une image: https://www.remove.bg/fr/upload
    * transformer jpeg en png: https://jpg2png.com/
    * diminuer le poids d'une image: https://imagecompressor.com/fr/ OU https://www.img2go.com/fr/compresser-image
    * changer la couleur: https://batchtools.pro/fr/changecolors/replace

-#
var controleDisplay

class CONTROLE_DISPLAY : Driver
  # Variables
  var numLedLCD
  var etatLedLCD
  var hres
  var vres
  var scr
  var scr1
  var f20
  var f28
  var btn_style

  def init()
    import displayFonctions

    # Recherche le N° du relai d'écran
    self.numLedLCD = controleGeneral.parametres["modules"]["ecran"]["environnement"]["relais"]["relai1"]["id"]
    self.etatLedLCD = controleGeneral.parametres["modules"]["ecran"]["environnement"]["relais"]["relai1"]["etat"]

    #- Démarre l'environnement LVGL -#
    lv.start()
    tasmota.cmd("DisplayDimmer 100", boolMute)

    self.hres = lv.get_hor_res()       # 480px
    self.vres = lv.get_ver_res()       # 320px

    self.scr = lv.scr_act()            # Objet screen par défaut
    self.f20 = lv.montserrat_font(20)  # police Montserrat 20
    self.f28 = lv.montserrat_font(28)  # police Montserrat 28

    var btn_style = lv.style()
    btn_style.set_radius(20)                        # radius of rounded corners
    btn_style.set_bg_opa(lv.OPA_COVER)              # 100% background opacity
    if self.f20 != nil btn_style.set_text_font(self.f20) end  # set font to Montserrat 20
    #btn_style.set_bg_color(lv.color(0x1fa3ec))      # background color #1FA3EC (Tasmota Blue)
    btn_style.set_border_color(lv.color(0x0000FF))  # border color #0000FF
    btn_style.set_text_color(lv.color(0xFFFFFF))    # text color white #FFFFFF

    var btn1 = lv.imagebutton(self.scr)
    btn1.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT) 
    btn1.set_pos(30, 30)
    btn1.set_size(100, 100)
    btn1.set_src(lv.IMAGEBUTTON_STATE_RELEASED, "A:/btn_parametres1.png", "A:/btn_parametres2.png", "A:/btn_parametres3.png")
    btn1.set_state(lv.IMAGEBUTTON_STATE_RELEASED)

    var btn2 = lv.imagebutton(self.scr)
    btn2.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT) 
    btn2.set_pos(160, 30)
    btn2.set_size(100, 100)
    btn2.set_src(lv.IMAGEBUTTON_STATE_RELEASED, "A:/btn_graphique1.png", "A:/btn_graphique2.png", "A:/btn_graphique3.png")
    btn2.set_state(lv.IMAGEBUTTON_STATE_RELEASED)
    btn2.set_zoom(4)

    # Charge l'écran de paramétrage
    # self.scr1 = lv.obj(0)
    # lv.scr_load(self.scr1)

    # Lance la 1ere page
    # displayFonctions.definiBackground(self.scr)

    # #- Affiche les indicateurs d'heure et de wifi -#
    # var stat_line = displayFonctions.definiBandeauPage(self.f28)
    # var wifi_icon = lv_wifi_arcs_icon(stat_line)
    # var clock_icon = lv_clock_icon(stat_line)

    # # Crée le style pour les boutons
    # self.btn_style = displayFonctions.creeStyleBTN(self.f20)

    # # Affiche la page d'accueil
    # displayFonctions.creeBTN(self.btn_style)
    # #displayFonctions.afficheAccueil(self.btn_style)
  end

  def every_second()
    import string

    # Eteind l'ecran si inactivite > 120s
    if (lv.display().get_inactive_time() > (controleGeneral.parametres["modules"]["ecran"].find("timerEcran", 120) * 1000))
      if (self.etatLedLCD == "ON")  
        tasmota.cmd(string.format("Power%i OFF", self.numLedLCD), boolMute) 
        self.etatLedLCD = "OFF"
      end
    else 
      if (self.etatLedLCD == "OFF")  
        tasmota.cmd(string.format("Power%i ON", self.numLedLCD), boolMute) 
        self.etatLedLCD = "ON"
      end
    end
  end
end

# Active le Driver de controle global des modules
controleDisplay = CONTROLE_DISPLAY()
tasmota.add_driver(controleDisplay)

import gestionFileFolder
#gestionFileFolder.loadBerryFile("/lv", persist.find("parametres")["modules"].find("ecran", {}).find("activation", "OFF"))
#load("/test_btn_image.be")

# def prog_origin()


#   #- Crée le bouton de gauche -#
#   prev_btn = lv.btn(scr)                            # Crée le bouton sur sur le screen 1
#   prev_btn.set_pos(20, vres - 60)                   # Position
#   prev_btn.set_size(80, 30)                         # Taille
#   prev_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)   # Style

#   prev_label = lv.label(prev_btn)                   # Label du bouton
#   prev_label.set_text("<")
#   prev_label.center()

#   #- Crée le bouton central -#
#   home_btn = lv.btn(scr)
#   home_btn.set_pos((hres / 2) - (80 / 2), vres - 60)
#   home_btn.set_size(80, 30)
#   home_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)
#   home_label = lv.label(home_btn)
#   home_label.set_text(lv.SYMBOL_OK)                 # Icone 'Home'
#   home_label.center()

#   #- Crée le bouton de droite -#
#   next_btn = lv.btn(scr)
#   next_btn.set_pos(hres - 20 - 80, vres - 60)
#   next_btn.set_size(80, 30)
#   next_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)

#   next_label = lv.label(next_btn)
#   next_label.set_text(">")
#   next_label.center()

#   #- fonctions de Callback pour les boutons, reagi à EVENT_CLICKED -#
#   def btn_clicked_cb(obj, event)
#     var btn = "Unknown"
#     if   obj == prev_btn  btn = "Prev"
#     elif obj == next_btn  btn = "Next"
#     elif obj == home_btn  btn = "Home"
#     end
#     print(btn, "button pressed")
#   end

#   prev_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)
#   home_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)
#   next_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)

#   # Crée le Slider au centre
#   label = lv.label(scr)
#   slider = lv.slider(scr)
#   slider.set_pos(20, 350) 
#   slider.set_height(10)
#   slider.set_width(300)

#   # Create a label below the slider
#   label.set_text("0%")
#   label.set_style_text_font(f20, lv.PART_MAIN | lv.STATE_DEFAULT)
#   label.set_style_text_color(lv.color(0xFFFFFF), lv.PART_MAIN | lv.STATE_DEFAULT)
#   label.align_to(slider, lv.ALIGN_OUT_TOP_MID, 0, -10)               # Align below the slider

#   #- fonctions de Callback pour slider -#
#   def slider_event_cb(obj, event)
#     var slider = "Unknown"
#     var value = "999"

#     if obj == slider  
#         slider = "Slider"
#     end

#     value = obj.get_value()

#     # Mets à jour le label
#     label.set_text(str(value) + "%")
    
#     # Publication MQTT
#     tasmota.publish("tele/ESP32-2432S028/SENSOR/Slider", str(value))
#   end

#   slider.add_event_cb(slider_event_cb, lv.EVENT_VALUE_CHANGED, None)

#   var modes = ['Auto', 'Boost', 'On', 'Off', 'Adv', 'Day']
#   var modes_str = modes.concat('\n')

#   ddlist = lv.dropdown(scr)
#   ddlist.set_options(modes_str)
#   ddlist.set_pos(20, 60)
#   ddlist.set_selected(2)
#   ddlist.set_selected_highlight(true)

#   def dropdown_changed_cb(obj, event)
#     var option = 0

#     var code = event.get_code()
#     if code == lv.EVENT_VALUE_CHANGED
#       option = obj.get_selected()
#       print("Dropdown set:", modes[option])
  
#       tasmota.publish("tele/ESP32-2432S028/SENSOR/Dropdown", modes[option])
#     end
#   end

#   ddlist.add_event_cb(dropdown_changed_cb, lv.EVENT_ALL, None)
# end