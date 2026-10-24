# Bouchon de modbusFonctions pour banc_cuve.be (audit Berry P10.4). Les deux seules fonctions que
# cuveFonctions appelle : noteMesure (fraicheur de la sentinelle ModBus) et mesureFraiche. Le banc
# programme 'fraiche' et lit 'notes' (adresses notees) et 'demandes' (adresses interrogees).
# Vit dans bouchons_berry/cuve/ et NON dans bouchons_berry/ : il masquerait le vrai module (ou le relais
# de banc_test_modbus) pour les autres bancs.
var modbusFonctions = module("modbusFonctions")
modbusFonctions.notes = []
modbusFonctions.demandes = []
modbusFonctions.fraiche = true
modbusFonctions.noteMesure = def (adresse) modbusFonctions.notes.push(adresse) end
modbusFonctions.mesureFraiche = def (adresse)
    modbusFonctions.demandes.push(adresse)
    return modbusFonctions.fraiche
end
return modbusFonctions
