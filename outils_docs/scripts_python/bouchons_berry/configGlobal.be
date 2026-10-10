# Bouchon du module de framework 'configGlobal' pour test_discovery.be (section 14).
# rangeExtenderFonctions.configExtenderByJson l'importe en tete de fonction, meme quand le point
# d'acces est inactif. testeParam (applique un reglage Tasmota s'il differe) : rien a appliquer.
var configGlobal = module("configGlobal")
configGlobal.testeParam = def (cmd, valeur, typeValeur) return false end
return configGlobal
