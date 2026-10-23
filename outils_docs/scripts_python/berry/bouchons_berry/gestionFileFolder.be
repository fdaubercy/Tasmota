# Bouchon du module de framework 'gestionFileFolder' pour banc_test_modbus.be et test_discovery.be.
# readFile() renvoie le fichier ecrit/pose dans 'fichiers' (chemin -> texte) s'il y est,
# sinon le texte pose dans 'contenu' (ex. un discovery.json de test), quel que soit le chemin.
# Mettre 'contenu' a false imite le vrai module pour un fichier absent (test_discovery.be).
# 'ecritures' compte les writeFile : c'est la date rendue par le bouchon path.last_modified.
# 'lectures' compte les readFile par chemin (audit P9.3 : discovery.json lu une seule fois par traitement).
var gestionFileFolder = module("gestionFileFolder")
gestionFileFolder.contenu = "{}"
gestionFileFolder.fichiers = {}
gestionFileFolder.ecritures = 0
gestionFileFolder.lectures = {}
gestionFileFolder.readFile = def (chemin)
    gestionFileFolder.lectures[chemin] = gestionFileFolder.lectures.find(chemin, 0) + 1
    return gestionFileFolder.fichiers.find(chemin, gestionFileFolder.contenu)
end
gestionFileFolder.writeFile = def (chemin, data) gestionFileFolder.fichiers[chemin] = data gestionFileFolder.ecritures += 1 end
return gestionFileFolder
