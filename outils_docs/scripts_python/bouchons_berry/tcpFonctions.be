# Bouchon du module de framework 'tcpFonctions' pour banc_test_modbus.be.
# Fournit l'etat lu par reglageModbus (port du serveur TCP ModBus) et un log muet.
var tcpFonctions = module("tcpFonctions")
tcpFonctions._etat = {"port": 502, "client": nil, "serveur": nil, "connexionAsync": nil}
tcpFonctions.etat = def () return tcpFonctions._etat end
tcpFonctions.log = def (msg, niveau) end
return tcpFonctions
