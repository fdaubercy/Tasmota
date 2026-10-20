# Bouchon du module natif 'path' du firmware pour banc_veille_drivers.be : adosse au LittleFS simule
# du bouchon gestionFileFolder (dossiers et fichiers en memoire).
var path = module("path")
path.creations = 0                  # mkdir reussis (le banc verifie qu un /json existant n est pas recree)
path.exists = def (chemin) import gestionFileFolder
    return gestionFileFolder.fichiers.contains(chemin) || gestionFileFolder.dossiers.contains(chemin)
end
path.isdir = def (chemin) import gestionFileFolder return gestionFileFolder.dossiers.contains(chemin) end
path.mkdir = def (chemin) import gestionFileFolder
    if gestionFileFolder.dossiers.contains(chemin)    return false    end
    gestionFileFolder.dossiers[chemin] = true
    path.creations += 1
    return true
end
path.remove = def (chemin) import gestionFileFolder
    if !gestionFileFolder.fichiers.contains(chemin)    return false    end
    gestionFileFolder.fichiers.remove(chemin)
    return true
end
path.rename = def (de, vers) import gestionFileFolder
    if !gestionFileFolder.fichiers.contains(de)    return false    end
    gestionFileFolder.fichiers[vers] = gestionFileFolder.fichiers[de]
    gestionFileFolder.fichiers.remove(de)
    return true
end
return path
