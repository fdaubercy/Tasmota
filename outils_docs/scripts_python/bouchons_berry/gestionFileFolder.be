# Bouchon du module de framework 'gestionFileFolder' pour banc_test_modbus.be.
# readFile() renvoie le texte pose par le banc dans 'contenu' (ex. un discovery.json
# de test), quel que soit le chemin demande.
var gestionFileFolder = module("gestionFileFolder")
gestionFileFolder.contenu = "{}"
gestionFileFolder.readFile = def (chemin) return gestionFileFolder.contenu end
return gestionFileFolder
