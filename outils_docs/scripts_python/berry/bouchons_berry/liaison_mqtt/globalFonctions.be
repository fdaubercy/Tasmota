# Bouchon de globalFonctions pour banc_mqtt_liaison.be : memorise les appels de changementEtatCapteur.
var globalFonctions = module("globalFonctions")
globalFonctions.appels = []
globalFonctions.changementEtatCapteur = def (v, trig, msg, mod, cle) globalFonctions.appels.push([v, trig, mod, cle]) end
return globalFonctions
