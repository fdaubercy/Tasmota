# Bouchon du module natif 'path' du firmware (absent de berry.exe) pour banc_graphiques.be, adosse au VRAI
# disque (le banc sert les vrais fichiers de data/sd et ecrit graphiques.json dans son dossier de sortie).
# Un chemin absolu du LittleFS ("/sd/js/x.js") est aussi cherche sous 'racine', comme le bouchon
# gestionFileFolder. rename n'existe pas dans le module 'os' de berry.exe : copie puis suppression.
import os
var path = module("path")
path.racine = "data"
path.renommages = []
path.existeBrut = def (chemin)
    try
        var f = open(chemin, "r")
        f.close()
        return true
    except ..
        return false
    end
end
path.exists = def (chemin)
    if (path.existeBrut(chemin))    return true    end
    return (size(chemin) > 0 && chemin[0] == "/" && path.existeBrut(path.racine + chemin))
end
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
