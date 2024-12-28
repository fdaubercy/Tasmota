# Initialisation de LVGL et de l'écran
import global

lv.start()

hres = lv.get_hor_res()       # should be 320
vres = lv.get_ver_res()       # should be 240

var scr = lv.scr_act()            # default screean object
f20 = lv.montserrat_font(20)  # load embedded Montserrat 20

# Chargement de l'image pour le bouton
# image = lv.img_dsc_t()
# image.data = lv.img_bin_data("/paper.png")
# image.header.always_zero = 0
# image.header.w = 50  # Largeur de l'image
# image.header.h = 50  # Hauteur de l'image
# image.header.cf = lv.img.CF.TRUE_COLOR

# Création du bouton
# btn = lv.btn(lv.scr_act())  # Créer un bouton sur l'écran actuel
# btn.set_size(100, 100)      # Définir la taille du bouton
# btn.center()  # Centrer le bouton sur l'écran

# # Ajouter une image au bouton
# img = lv.img(btn)
# img.set_src("A:/paper.png")  # Associer l'image au bouton
# img.center()  # Centrer l'image sur le bouton

# var imgbtn = lv.imagebutton(btn)
# #imgbtn.set_pos(30, 30)
# imgbtn.set_state(lv.IMAGEBUTTON_STATE_RELEASED)
# imgbtn.set_src(lv.IMAGEBUTTON_STATE_RELEASED, "/paper.png", "/paper.png", "/paper.png")  # Image pour état relâché
# imgbtn.set_size(100, 100)
# imgbtn.center()  # Centrer l'image sur le bouton

# sunrise = lv.image(scr)                   # create an empty image object in the current screen
# sunrise.set_src("A:/paper.png")    # load "Sunrise320.png", the default drive letter is 'A:'
# sunrise.move_background() 


#- Background with a gradient from black #000000 (bottom) to dark blue #0000A0 (top) -#
# scr.set_style_bg_color(lv.color(0x0000A0), lv.PART_MAIN | lv.STATE_DEFAULT)
# scr.set_style_bg_grad_color(lv.color(0x000000), lv.PART_MAIN | lv.STATE_DEFAULT)
# scr.set_style_bg_grad_dir(lv.GRAD_DIR_VER, lv.PART_MAIN | lv.STATE_DEFAULT)

var btn_style = lv.style()
btn_style.set_radius(10)                        # radius of rounded corners
btn_style.set_bg_opa(lv.OPA_COVER)              # 100% background opacity
if f20 != nil btn_style.set_text_font(f20) end  # set font to Montserrat 20
# btn_style.set_bg_color(lv.color(0x1fa3ec))      # background color #1FA3EC (Tasmota Blue)
btn_style.set_border_color(lv.color(0x0000FF))  # border color #0000FF
btn_style.set_text_color(lv.color(0xFFFFFF))    # text color white #FFFFFF

# var imgbtn = lv.imagebutton(scr);
# imgbtn.set_pos(30, 30)
# imgbtn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT) 
# imgbtn.set_src(lv.IMAGEBUTTON_STATE_RELEASED, "A:/telecharger.png", "A:/middle_button.png", "A:/telecharger.png")
# imgbtn.set_state(lv.IMAGEBUTTON_STATE_RELEASED)
# imgbtn.set_size(100, 49)
# imgbtn.center()  # Centrer l'image sur le bouton

btn = lv.imagebutton(scr)
btn.add_style(btn_style, lv.PART_MAIN | lv.STATE_DEFAULT) 
btn.set_pos(30, 30)
btn.set_size(200, 200)
btn.set_src(lv.IMAGEBUTTON_STATE_RELEASED, "A:/left_button.png", "A:/middle_button.png", "A:/right_button.png")
btn.set_state(lv.IMAGEBUTTON_STATE_RELEASED)


# sunrise = lv.img(scr)                   # create an empty image object in the current screen
# sunrise.set_src("A:/Sunrise320.png")    # load "Sunrise320.png", the default drive letter is 'A:'
# sunrise.move_background() 

# Fonction callback pour le bouton
def event_cb(e)
    print("Bouton cliqué")
end

# Attacher la fonction de callback au bouton
# btn.add_event_cb(event_cb, lv.EVENT_CLICKED, None)
