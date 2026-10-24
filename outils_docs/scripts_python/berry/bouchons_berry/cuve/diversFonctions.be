# Bouchon de diversFonctions pour banc_cuve.be : traiteAide (aide de ReglageCuve / ReglageAna) ne
# traite jamais l'aide ici ; l'aide de la cuve est testee en appelant aideReglageCuve directement.
var diversFonctions = module("diversFonctions")
diversFonctions.traiteAide = def (commande, payload, fonction, ordre) return false end
return diversFonctions
