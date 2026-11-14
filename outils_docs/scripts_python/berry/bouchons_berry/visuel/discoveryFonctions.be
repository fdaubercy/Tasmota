# Bouchon de discoveryFonctions pour banc_visuel.be : lisTable() et etatReseau() rendent ce que le banc pose dans
# global.reseauBouchon ({"lignes": [...], "appels": n}) ; nil : module ABSENT (l'import leve).
import global
if (global.reseauBouchon == nil)    raise "import_error", "discoveryFonctions absent"    end
var m = module("discoveryFonctions")
m.lisTable = def () return {} end
m.etatReseau = def (table, rgx) global.reseauBouchon["appels"] += 1 global.reseauBouchon["rgx"] = rgx return global.reseauBouchon["lignes"] end
return m
