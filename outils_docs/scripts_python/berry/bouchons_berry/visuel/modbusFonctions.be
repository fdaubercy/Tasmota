# Bouchon de modbusFonctions pour banc_visuel.be : etat() rend la table posee par le banc dans global.modbusBouchon ;
# global.modbusBouchon == nil : le module est ABSENT (l'import leve), comme sur une carte sans ModBus.
import global
if (global.modbusBouchon == nil)    raise "import_error", "modbusFonctions absent"    end
var m = module("modbusFonctions")
m.etat = def () return global.modbusBouchon end
return m
