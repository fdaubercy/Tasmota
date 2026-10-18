# Bouchon du module natif 'path' du firmware (absent de berry.exe) pour banc_graphiques.be :
# exists() regarde le VRAI disque (le banc sert les vrais fichiers de data/sd).
var path = module("path")
path.exists = def (chemin)
    try
        var f = open(chemin, "r")
        f.close()
        return true
    except ..
        return false
    end
end
return path
