# Bouchon du module display du firmware pour banc_ecran_lvgl.be : display.demarre = false simule un ecran non demarre
# (display.ini absent ou faux)
var display = module("display")
display.demarre = true
display.started = def () return display.demarre end
return display
