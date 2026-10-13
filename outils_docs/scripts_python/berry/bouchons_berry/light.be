# Bouchon du module natif Tasmota 'light' pour banc_test_modbus.be (2026-10-11) et banc_leds.be
# (2026-10-13) : get() renvoie l'etat pose par le banc (light.etat), a la forme de light.get() du
# firmware (bri/sat 0-255) ; set() recopie ses cles dans cet etat et garde l'appel dans light.sets.
var light = module("light")
light.etat = nil
light.sets = []
light.get = def (canal) return light.etat end
light.set = def (m, canal)
    light.sets.push(m)
    for k: m.keys()    light.etat[k] = m[k]    end
end
return light
