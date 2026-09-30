# Bouchon du module natif Tasmota 'mqtt' pour test_discovery.be : n'emet rien, mais
# memorise les publications [topic, payload, retain] pour que le test les rejoue.
var mqtt = module("mqtt")
mqtt.publies = []
mqtt.publish = def (topic, payload, retain) mqtt.publies.push([topic, payload, retain]) end
mqtt.subscribe = def (topic, fonction) end
return mqtt
