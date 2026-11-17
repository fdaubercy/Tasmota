# Bouchon du module natif 'persist' pour banc_mqtt_liaison.be : find() sur une map ; seuils de garde-fous reduits
# pour tester la lecture du persist (drivers.liaisonMqtt.garde).
var persist = module("persist")
persist._p = {"drivers": {"liaisonMqtt": {"garde": {"maxParElement": 4, "delaiAccuseMs": 1500, "essaisMax": "x"}}}}
persist.find = def (k, d) return persist._p.find(k, d) end
return persist
