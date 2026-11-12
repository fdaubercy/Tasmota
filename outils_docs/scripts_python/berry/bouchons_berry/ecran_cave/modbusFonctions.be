# Bouchon de modbusFonctions pour banc_ecran_cave.be : pousseEtat memorise les pushs [registre, type, mot] ; `injoignable` = rien ne part (retour nil).
var modbusFonctions = module("modbusFonctions")
modbusFonctions.pushs = []
modbusFonctions.injoignable = false
modbusFonctions.pousseEtat = def (adresse, typeValeur, valeurs)
    if modbusFonctions.injoignable    return nil    end
    modbusFonctions.pushs.push([adresse, typeValeur, valeurs[0]])
    return bytes("00")
end
return modbusFonctions
