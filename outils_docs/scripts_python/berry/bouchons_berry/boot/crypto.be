# Bouchon du module natif 'crypto' pour banc_boot.be : rien de materiel au banc. Une constante (nom en
# MAJUSCULES, ex. gpio.OUTPUT) vaut 0 ; toute fonction rend nil, son nom est garde dans crypto.appels.
var crypto = module("crypto")
crypto.appels = []
crypto.member = def (n)
    import string
    if string.toupper(n) == n    return 0    end
    return def (*a) crypto.appels.push(n) return nil end
end
return crypto
