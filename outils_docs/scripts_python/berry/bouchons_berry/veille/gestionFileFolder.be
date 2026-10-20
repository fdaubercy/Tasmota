# Bouchon du module de framework 'gestionFileFolder' pour banc_veille_drivers.be : LittleFS simule en memoire.
# Comme le open() du firmware, writeFile leve io_error si le dossier parent n'existe pas (LittleFS neuf sans /json)
# ou si 'plein' est vrai (ecriture impossible) ; readFile leve io_error pour un fichier absent.
var gestionFileFolder = module("gestionFileFolder")
gestionFileFolder.dossiers = {"/": true}
gestionFileFolder.fichiers = {}
gestionFileFolder.plein = false

def gestionFileFolder_parent(chemin)
    import string
    var i = size(chemin) - 1
    while (i > 0 && chemin[i] != "/")    i -= 1    end
    return i == 0 ? "/" : chemin[0 .. i - 1]
end
gestionFileFolder.parent = gestionFileFolder_parent

gestionFileFolder.writeFile = def (chemin, data)
    if (gestionFileFolder.plein || !gestionFileFolder.dossiers.contains(gestionFileFolder.parent(chemin)))
        raise "io_error", "cannot open file '" + chemin + "'"
    end
    gestionFileFolder.fichiers[chemin] = data
end
gestionFileFolder.readFile = def (chemin)
    if !gestionFileFolder.fichiers.contains(chemin)    raise "io_error", "cannot open file '" + chemin + "'"    end
    return gestionFileFolder.fichiers[chemin]
end
return gestionFileFolder
