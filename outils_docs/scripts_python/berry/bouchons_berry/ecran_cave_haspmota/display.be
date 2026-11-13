# Bouchon du module display du firmware pour banc_ecran_cave.be (interface HASPmota, A7) : display.demarre = false simule un ecran non demarre
var display = module("display")
display.demarre = true
display.started = def () return display.demarre end
return display
