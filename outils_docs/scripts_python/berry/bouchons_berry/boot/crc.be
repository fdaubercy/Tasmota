# Bouchon du module natif 'crc' pour banc_boot.be : rien de materiel au banc. Une constante (nom en
# MAJUSCULES, ex. gpio.OUTPUT) vaut 0 ; toute fonction rend nil, son nom est garde dans crc.appels.
var crc = module("crc")
crc.appels = []
crc.member = def (n)
    import string
    if string.toupper(n) == n    return 0    end
    return def (*a) crc.appels.push(n) return nil end
end
return crc
