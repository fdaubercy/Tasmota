# Bouchon du module natif 'persist' du firmware pour banc_veille_drivers.be : compte les sauvegardes.
var persist = module("persist")
persist.sauvegardes = 0
persist.save = def (force) persist.sauvegardes += 1 end
return persist
