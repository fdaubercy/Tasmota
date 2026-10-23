# Bouchon du module 'discoveryFonctions' pour les bancs Berry (test_discovery.be, banc_test_modbus.be).
# Sur la carte, le module est solidifie : 'import discoveryFonctions' (udpFonctions.reglageUDP, ImAlive,
# 2026-10-24) le trouve en flash. Au banc, test_discovery le charge par compile() dans la globale du meme
# nom : on rend cette globale telle quelle, pour que l'import et le banc voient le MEME module. Sinon
# (banc qui ne l'a pas charge), le VRAI data/fs/discoveryFonctions.be est charge, comme diversFonctions.
import global
if global.contains("discoveryFonctions") && global.discoveryFonctions != nil    return global.discoveryFonctions    end
for nom: ["boolMute", "drivers", "serveur", "diverses", "modules", "persist", "mqtt", "discoveryFonctions",
          "LOG_LEVEL_ERREUR", "LOG_LEVEL_INFO", "LOG_LEVEL_DEBUG", "LOG_LEVEL_DEBUG_PLUS"]
    if !global.contains(nom)    global.(nom) = nil    end
end
var dossier = global.contains("SOURCES") && global.SOURCES != nil ? global.SOURCES : "data/fs"
var f = open(dossier + "/discoveryFonctions.be", "r")
var src = f.read()
f.close()
compile(src)()
return global.discoveryFonctions
