# Bouchon de logFonctions pour banc_fsmqtt.be : journal [message, niveau, cible] dans le global JOURNAL.
var logFonctions = module("logFonctions")
logFonctions.log = def (m, n, c) import global global.JOURNAL.push([m, n, c]) end
logFonctions.actif = def (n, c) return true end
return logFonctions
