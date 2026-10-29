# Bouchon du module natif 'mqtt' pour banc_fsmqtt.be : publications memorisees, abonnements rappelables.
var mqtt = module("mqtt")
mqtt.publies = []
mqtt.abonnes = {}
mqtt.connecte = true
mqtt.publish = def (topic, payload, retain) mqtt.publies.push([topic, payload]) end
mqtt.subscribe = def (topic, f) mqtt.abonnes[topic] = f end
mqtt.connected = def () return mqtt.connecte end
return mqtt
