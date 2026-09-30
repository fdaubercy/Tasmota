# Bouchon du module de framework 'gestionFileFolder' pour banc_test_modbus.be et test_discovery.be.
# readFile() renvoie le fichier ecrit/pose dans 'fichiers' (chemin -> texte) s'il y est,
# sinon le texte pose dans 'contenu' (ex. un discovery.json de test), quel que soit le chemin.
# Mettre 'contenu' a false imite le vrai module pour un fichier absent (test_discovery.be).
var gestionFileFolder = module("gestionFileFolder")
gestionFileFolder.contenu = "{}"
gestionFileFolder.fichiers = {}
gestionFileFolder.readFile = def (chemin) return gestionFileFolder.fichiers.find(chemin, gestionFileFolder.contenu) end
gestionFileFolder.writeFile = def (chemin, data) gestionFileFolder.fichiers[chemin] = data end
return gestionFileFolder
