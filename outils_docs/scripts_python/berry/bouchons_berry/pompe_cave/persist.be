# Bouchon de persist pour banc_pompe_cave.be : save() ne fait rien.
var persist = module("persist")
persist.save = def (force) end
return persist
