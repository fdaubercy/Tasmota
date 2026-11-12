# Bouchon de mqtt pour banc_pompe_cave.be : broker absent par defaut (relie = false) ; relie = true -> publish enregistre dans publies.
var mqtt = module("mqtt")
mqtt.relie = false
mqtt.publies = []
mqtt.publish = def (t, p, r) mqtt.publies.push(p) end
mqtt.subscribe = def (t, f) end
mqtt.connected = def () return mqtt.relie end
return mqtt
