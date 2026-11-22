# Bouchon du module natif 'persist' pour banc_hue.be : find() sur la map du global PERSIST_BANC, posee par chaque cas
# (persist reel d'une carte lu par json.load, ou persist d'essai).
var persist = module("persist")
persist.find = def (k, d) import global return isinstance(global.PERSIST_BANC, map) ? global.PERSIST_BANC.find(k, d) : d end
return persist
