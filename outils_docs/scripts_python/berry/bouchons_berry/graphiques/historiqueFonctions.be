# Bouchon de historiqueFonctions pour banc_graphiques.be : la configuration (diverses.historique) est
# posee par le banc ; les filtres enregistres par controleGarage sont gardes pour etre appeles.
var historiqueFonctions = module("historiqueFonctions")
historiqueFonctions.config = nil
historiqueFonctions.filtres = []
historiqueFonctions.nomsInstances = def () return ["mesures"] end
historiqueFonctions.ajouteFiltre = def (f) historiqueFonctions.filtres.push(f) end
return historiqueFonctions
