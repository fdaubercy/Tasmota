# Bouchon de mqtt pour banc_pompe_cave.be : broker absent, rien n est emis.
var mqtt = module("mqtt")
mqtt.publish = def (t, p, r) end
mqtt.subscribe = def (t, f) end
mqtt.connected = def () return false end
return mqtt
