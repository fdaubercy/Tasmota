# Bouchon de garageFonctions (data/garage/tasmota32p4-serveur-modbus) pour banc_graphiques.be :
# juste ce que CONTROLE_GARAGE.init() appelle.
var garageFonctions = module("garageFonctions")
garageFonctions.log = def (msg, niveau) end
garageFonctions.reglageGarage = def () end
# Recopie de la vraie (garageFonctions.be) : CONTROLE_GARAGE.tensionSonde l'appelle (banc_cuve_page.be)
garageFonctions.mesureEnErreur = def (device) var etat = device.find("etatConstate") return (etat == "defaillant" || etat == "inconnu") end
return garageFonctions
