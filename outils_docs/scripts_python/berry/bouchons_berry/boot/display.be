# Bouchon du module display du firmware (envs a ecran, ex. tasmota32s3-bureau-serveur-debits-pac) : ecran demarre
var display = module("display")
display.started = def () return true end
return display
