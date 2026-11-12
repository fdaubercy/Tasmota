# Bouchon de logFonctions pour banc_pompe_cave.be : memorise [niveau, message] dans logFonctions.journal.
var logFonctions = module("logFonctions")
logFonctions.journal = []
logFonctions.log = def (m, n, c) logFonctions.journal.push([n, str(m)]) end
logFonctions.actif = def (n, c) return false end
logFonctions.reglageLog = def (c, i, p, j) end
return logFonctions
