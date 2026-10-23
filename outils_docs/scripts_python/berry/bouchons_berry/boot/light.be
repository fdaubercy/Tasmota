# Bouchon du module natif 'light' pour banc_boot.be : rien de materiel au banc. Une constante (nom en
# MAJUSCULES, ex. gpio.OUTPUT) vaut 0 ; toute fonction rend nil, son nom est garde dans light.appels.
var light = module("light")
light.appels = []
light.member = def (n)
    import string
    if string.toupper(n) == n    return 0    end
    return def (*a) light.appels.push(n) return nil end
end
return light
