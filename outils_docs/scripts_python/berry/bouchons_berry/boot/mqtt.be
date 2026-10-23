# Bouchon du module natif 'mqtt' pour banc_boot.be : n'emet rien, garde les publications et abonnements.
var mqtt = module("mqtt")
mqtt.publies = []
mqtt.abonnements = []
mqtt.connecte = false                  # au demarrage, le broker n'est pas encore joint
mqtt.publish = def (topic, payload, retain) mqtt.publies.push([topic, payload, retain]) return true end
mqtt.subscribe = def (topic, fonction) mqtt.abonnements.push(topic) end
mqtt.unsubscribe = def (topic) end
mqtt.connected = def () return mqtt.connecte end
return mqtt
