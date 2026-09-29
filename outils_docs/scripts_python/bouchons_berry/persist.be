# Bouchon du module natif Tasmota 'persist' pour banc_test_modbus.be.
# Seul save() est appele par les fonctions testees ; le compteur permet au banc
# de verifier qu'une sauvegarde a bien ete demandee.
var persist = module("persist")
persist.nb_save = 0
persist.save = def (force) persist.nb_save += 1 end
return persist
