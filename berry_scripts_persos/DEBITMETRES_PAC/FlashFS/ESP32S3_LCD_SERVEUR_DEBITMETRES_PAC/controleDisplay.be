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
-#

class CONTROLE_DISPLAY : Driver
  # Variables
  var numLedLCD
  var etatLedLCD

  def init()
    #import displayFonctions

    # Recherche le N° du relai d'écran
    self.numLedLCD = controleGeneral.parametres["modules"]["ecran"]["environnement"]["relais"]["relai1"]["id"]
    self.etatLedLCD = controleGeneral.parametres["modules"]["ecran"]["environnement"]["relais"]["relai1"]["etat"]

    # Lance la 1ere page
    # displayFonctions.afficheAccueil()   
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

#- Démarre l'environnement LVGL -#
lv.start()
tasmota.cmd("DisplayDimmer 100", boolMute)

var scr1 = lv.obj(0)
# var scr2  = lv.obj_create(None, None);
lv.scr_load(scr1);

hres = lv.get_hor_res()       # 480px
vres = lv.get_ver_res()       # 320px

var scr = lv.scr_act()            # Objet screen par défaut
f20 = lv.montserrat_font(20)  # police Montserrat 20
f28 = lv.montserrat_font(28)  # police Montserrat 28

#- Background with a gradient from black #000000 (bottom) to dark blue #0000A0 (top) -#
scr1.set_style_bg_color(lv.color(0x000000), lv.PART_MAIN | lv.STATE_DEFAULT)
scr1.set_style_bg_grad_color(lv.color(0x000000), lv.PART_MAIN | lv.STATE_DEFAULT)
scr1.set_style_bg_grad_dir(lv.GRAD_DIR_VER, lv.PART_MAIN | lv.STATE_DEFAULT)

#- Ligne de données en haut de page -#
stat_line = lv.label(scr)
if f28 != nil stat_line.set_style_text_font(f28, lv.PART_MAIN | lv.STATE_DEFAULT) end
stat_line.set_long_mode(lv.LABEL_LONG_SCROLL)                                        # auto scroll si le texte dépasse
stat_line.set_width(hres)
stat_line.set_align(lv.TEXT_ALIGN_LEFT)                                              # Texte aligné à gauche
stat_line.set_style_bg_color(lv.color(0xD00000), lv.PART_MAIN | lv.STATE_DEFAULT)    # Background #000088
stat_line.set_style_bg_opa(lv.OPA_COVER, lv.PART_MAIN | lv.STATE_DEFAULT)            # Opacité: 100% 
stat_line.set_style_text_color(lv.color(0xFFFFFF), lv.PART_MAIN | lv.STATE_DEFAULT)  # Couleur du texte: #FFFFFF
stat_line.set_text("Telemetrie PAC")
stat_line.refr_size()
stat_line.refr_pos()

#- Affiche les indicateurs d'heure et de wifi -#
wifi_icon = lv_wifi_arcs_icon(stat_line)
clock_icon = lv_clock_icon(stat_line)

#- Crée le style pour les boutons -#
btn_style = lv.style()
btn_style.set_radius(10)
btn_style.set_bg_opa(lv.OPA_COVER)
if f20 != nil btn_style.set_text_font(f20) end
btn_style.set_bg_color(lv.color(0x1fa3ec))      # Couleur background: #1FA3EC (Tasmota Blue)
btn_style.set_border_color(lv.color(0x0000FF))  # Couleur des bordures: #0000FF
btn_style.set_text_color(lv.color(0xFFFFFF))    # Couleur du texte: #FFFFFF (Blanc)

#- Crée le bouton de gauche -#
prev_btn = lv.btn(scr)                            # Crée le bouton sur sur le screen 1
prev_btn.set_pos(20, vres - 60)                   # Position
prev_btn.set_size(80, 30)                         # Taille
prev_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)   # Style

prev_label = lv.label(prev_btn)                   # Label du bouton
prev_label.set_text("<")
prev_label.center()

#- Crée le bouton central -#
home_btn = lv.btn(scr)
home_btn.set_pos((hres / 2) - (80 / 2), vres - 60)
home_btn.set_size(80, 30)
home_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)
home_label = lv.label(home_btn)
home_label.set_text(lv.SYMBOL_OK)                 # Icone 'Home'
home_label.center()

#- Crée le bouton de droite -#
next_btn = lv.btn(scr)
next_btn.set_pos(hres - 20 - 80, vres - 60)
next_btn.set_size(80, 30)
next_btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT)

next_label = lv.label(next_btn)
next_label.set_text(">")
next_label.center()

#- fonctions de Callback pour les boutons, reagi à EVENT_CLICKED -#
def btn_clicked_cb(obj, event)
  var btn = "Unknown"
  if   obj == prev_btn  btn = "Prev"
  elif obj == next_btn  btn = "Next"
  elif obj == home_btn  btn = "Home"
  end
  print(btn, "button pressed")
end

prev_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)
home_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)
next_btn.add_event_cb(btn_clicked_cb, lv.EVENT_CLICKED, 0)

# Crée le Slider au centre
label = lv.label(scr)
slider = lv.slider(scr)
slider.set_pos(20, 350) 
slider.set_height(10)
slider.set_width(300)

# Create a label below the slider
label.set_text("0%")
label.set_style_text_font(f20, lv.PART_MAIN | lv.STATE_DEFAULT)
label.set_style_text_color(lv.color(0xFFFFFF), lv.PART_MAIN | lv.STATE_DEFAULT)
label.align_to(slider, lv.ALIGN_OUT_TOP_MID, 0, -10)               # Align below the slider

#- fonctions de Callback pour slider -#
def slider_event_cb(obj, event)
  var slider = "Unknown"
  var value = "999"

  if obj == slider  
		  slider = "Slider"
  end

  value = obj.get_value()

  # Mets à jour le label
  label.set_text(str(value) + "%")
   
  # Publication MQTT
  tasmota.publish("tele/ESP32-2432S028/SENSOR/Slider", str(value))
end

slider.add_event_cb(slider_event_cb, lv.EVENT_VALUE_CHANGED, None)

var modes = ['Auto', 'Boost', 'On', 'Off', 'Adv', 'Day']
var modes_str = modes.concat('\n')

ddlist = lv.dropdown(scr)
ddlist.set_options(modes_str)
ddlist.set_pos(20, 60)
ddlist.set_selected(2)
ddlist.set_selected_highlight(true)

def dropdown_changed_cb(obj, event)
  var option = 0

  var code = event.get_code()
  if code == lv.EVENT_VALUE_CHANGED
    option = obj.get_selected()
    print("Dropdown set:", modes[option])
 
    tasmota.publish("tele/ESP32-2432S028/SENSOR/Dropdown", modes[option])
  end
end

ddlist.add_event_cb(dropdown_changed_cb, lv.EVENT_ALL, None)