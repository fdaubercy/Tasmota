# Bouchon du module mqtt (banc_ecran_systeme) : mqtt.connected() rend global.MQTT_OK
import global
var m = module("mqtt")
m.connected = def () return global.MQTT_OK end
return m
