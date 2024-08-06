# pre-load widgets so future `import` will be already in memory
# create tapp file with:
#   rm rm haspmota_widgets.tapp; zip -j -0 haspmota_widgets.tapp haspmota_widgets/*
import lv_tasmota_log
import lv_tasmota_info
import lv_wifi_graph

var scr = lv.scr_act()
var stat_line = lv.label(scr)
var f28 = lv.montserrat_font(28)  # police Montserrat 28
var hres = lv.get_hor_res()
var vres = lv.get_ver_res()

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

# var info = lv_tasmota_info(scr)
# info.set_pos(0, stat_line.get_height())
# info.set_size(hres - 80, 30)
# tasmota.add_driver(info)

# var log = lv_tasmota_log(scr)
# log.set_pos(0, stat_line.get_height())
# log.set_size(hres, vres - stat_line.get_height())
# tasmota.add_driver(log)

var ws_h = 40
var ws_w = 80
var ws = lv_wifi_graph(scr)
log.set_pos(0, stat_line.get_height())
log.set_size(hres, vres - stat_line.get_height())
tasmota.add_driver(ws)