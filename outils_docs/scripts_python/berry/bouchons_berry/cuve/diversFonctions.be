# Bouchon de diversFonctions pour banc_cuve.be : traiteAide (aide de ReglageCuve / ReglageAna) ne
# traite jamais l'aide ici ; l'aide de la cuve est testee en appelant aideReglageCuve directement.
var diversFonctions = module("diversFonctions")
diversFonctions.traiteAide = def (commande, payload, fonction, ordre) return false end
# Copie de data/fs/diversFonctions.be (audit P5.8) : la vraie fonction est testee par banc_boot.be
diversFonctions.valeurScalaire = def (value)
    while isinstance(value, map)
        if value.contains("Action")    value = value["Action"]
        elif value.size() == 1    value = value[value.keys()()]
        else    break
        end
    end
    return value
end
return diversFonctions
