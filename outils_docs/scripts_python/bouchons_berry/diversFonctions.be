# Bouchon du module 'diversFonctions' pour les bancs Berry (test_discovery.be, banc_test_modbus.be).
# Charge le VRAI data/fs/diversFonctions.be : les gestionnaires de commande l'importent pour
# l'aide contextuelle (traiteAide), qui doit etre testee telle qu'elle tourne sur la carte.
# Ses globales firmware absentes du banc sont declarees a nil (compile() refuse un nom non
# declare) ; celles que le banc definit deja (boolMute, drivers...) sont gardees.
import global
for nom: ["boolMute", "drivers", "serveur", "diverses", "modules", "persist", "log",
          "LOG_LEVEL_ERREUR", "LOG_LEVEL_INFO", "LOG_LEVEL_DEBUG", "LOG_LEVEL_DEBUG_PLUS"]
    if !global.contains(nom)    global.(nom) = nil    end
end
var dossier = global.contains("SOURCES") && global.SOURCES != nil ? global.SOURCES : "data/fs"
var f = open(dossier + "/diversFonctions.be", "r")
var src = f.read()
f.close()
return compile(src)()
