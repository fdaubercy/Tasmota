# Bouchon du module de framework 'udpFonctions' pour banc_test_modbus.be.
# envoiUDP() n'emet rien : il memorise les datagrammes pour que le banc verifie
# ce qui serait parti (type d'envoi, destinataire, message).
var udpFonctions = module("udpFonctions")
udpFonctions.envois = []
udpFonctions.envoiUDP = def (typeComm, ip, message) udpFonctions.envois.push([typeComm, ip, message]) end
udpFonctions.log = def (msg, niveau) end
return udpFonctions
