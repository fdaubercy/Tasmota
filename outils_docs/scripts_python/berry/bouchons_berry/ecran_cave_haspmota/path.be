# Bouchon du module path pour banc_ecran_cave.be (A7) : exists d'apres la liste global.FICHIERS_ECRAN
import global
var path = module("path")
path.exists = def (f) return global.FICHIERS_ECRAN.find(f) != nil end
return path
