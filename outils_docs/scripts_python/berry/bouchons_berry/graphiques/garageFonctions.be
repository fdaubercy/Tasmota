# Bouchon de garageFonctions (data/garage/tasmota32p4-serveur-modbus) pour banc_graphiques.be :
# juste ce que CONTROLE_GARAGE.init() appelle.
var garageFonctions = module("garageFonctions")
garageFonctions.log = def (msg, niveau) end
garageFonctions.reglageGarage = def () end
return garageFonctions
