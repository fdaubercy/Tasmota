# Bouchon de diversFonctions pour banc_mqtt_liaison.be : seul traiteAide est utilise (aide jamais demandee ici).
var diversFonctions = module("diversFonctions")
diversFonctions.traiteAide = def (commande, payload, fnAide, verifieInconnue) return false end
return diversFonctions
