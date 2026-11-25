# Bouchon de diversFonctions pour banc_humidite.be : l'aide contextuelle ne se declenche jamais (le banc passe des valeurs).
var diversFonctions = module("diversFonctions")
diversFonctions.traiteAide = def (cmd, payload, f, b) return false end
return diversFonctions
