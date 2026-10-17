# Bouchon du module natif 'path' du firmware (absent de berry.exe) pour test_discovery.be.
# last_modified() rend 'date' si le test l'a posee (date figee : deux ecritures dans la meme seconde),
# sinon le nombre d'ecritures du bouchon gestionFileFolder (une ecriture = une nouvelle date).
var path = module("path")
path.date = nil
path.last_modified = def (chemin) import gestionFileFolder return path.date != nil ? path.date : gestionFileFolder.ecritures end
path.exists = def (chemin) import gestionFileFolder return gestionFileFolder.fichiers.contains(chemin) end
return path
