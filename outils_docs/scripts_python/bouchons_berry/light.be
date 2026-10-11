# Bouchon du module natif Tasmota 'light' pour banc_test_modbus.be (2026-10-11) : get() renvoie
# l'etat pose par le banc (light.etat), a la forme de light.get() du firmware (bri/sat 0-255).
var light = module("light")
light.etat = nil
light.get = def (canal) return light.etat end
return light
