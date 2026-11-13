# Bouchon du module haspmota pour banc_ecran_cave.be (A7) : start(fichier) cree les objets de pages.jsonl (global.creeObjets du banc) ; lvh_page_cur_idx = page courante
import global
var haspmota = module("haspmota")
haspmota.demarre = nil
haspmota.lvh_page_cur_idx = 1
haspmota.start = def (f) haspmota.demarre = f global.creeObjets() end
return haspmota
