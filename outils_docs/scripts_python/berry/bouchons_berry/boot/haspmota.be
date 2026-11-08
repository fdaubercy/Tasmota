# Bouchon du module haspmota du firmware (envs LVGL) : start() retient la page, ne cree aucun objet
var haspmota = module("haspmota")
haspmota.page = nil
haspmota.start = def (f) haspmota.page = f end
return haspmota
