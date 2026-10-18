# Bouchon du module natif 'path' du firmware (absent de berry.exe) pour banc_historique.be : adosse au
# VRAI disque par le module 'os' de berry.exe (le banc ecrit l'historique dans son dossier de sortie).
# rename n'existe pas dans 'os' : copie puis suppression ; chaque renommage est note dans 'renommages'.
import os
var path = module("path")
path.renommages = []
path.exists = def (chemin) return os.path.exists(chemin) end
path.mkdir = def (chemin) if (!os.path.exists(chemin)) os.mkdir(chemin) end return true end
path.listdir = def (chemin) return os.listdir(chemin) end
path.remove = def (chemin) return os.remove(chemin) end
path.rename = def (de, vers)
    path.renommages.push([de, vers])
    var f = open(de, "rb")
    var contenu = f.readbytes()
    f.close()
    f = open(vers, "wb")
    f.write(contenu)
    f.close()
    os.remove(de)
    return true
end
return path
