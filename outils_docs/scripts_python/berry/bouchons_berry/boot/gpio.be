# Bouchon du module natif 'gpio' pour banc_boot.be : rien de materiel au banc. Une constante (nom en
# MAJUSCULES, ex. gpio.OUTPUT) vaut 0 ; toute fonction rend nil, son nom est garde dans gpio.appels.
var gpio = module("gpio")
gpio.appels = []
gpio.member = def (n)
    import string
    if string.toupper(n) == n    return 0    end
    return def (*a) gpio.appels.push(n) return nil end
end
return gpio
