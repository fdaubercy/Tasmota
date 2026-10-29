# Bouchon du module natif 'persist' pour banc_fsmqtt.be : find() sur une map, load() compte ses appels.
var persist = module("persist")
persist._p = {"serveur": {"mqtt": {"topic": "garage/cuve"}}, "diverses": {}, "modules": {}, "drivers": {}}
persist.chargements = 0
persist.find = def (k, d) return persist._p.find(k, d) end
persist.load = def () persist.chargements += 1 end
return persist
