# Bouchon de persist pour banc_humidite.be : save() compte les appels et garde leur argument (la page doit passer true).
var persist = module("persist")
persist.sauvegardes = []
persist.save = def (force) persist.sauvegardes.push(force) end
return persist
