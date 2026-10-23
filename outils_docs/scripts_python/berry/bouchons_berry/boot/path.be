# Bouchon du module natif 'path' pour banc_boot.be : adosse au LittleFS EN MEMOIRE du banc
# (LITTLEFS, pose par faux_firmware.be). Rien n'est lu ni ecrit sur le disque du PC.
import global
var path = module("path")
path.exists = def (c) return global.LITTLEFS.existe(c) end
path.isdir = def (c) return global.LITTLEFS.dossiers.contains(global.LITTLEFS.normalise(c)) end
path.listdir = def (c)
    var fs = global.LITTLEFS
    if !fs.dossiers.contains(fs.normalise(c))    return nil    end
    return fs.liste(c)
end
path.mkdir = def (c)
    var fs = global.LITTLEFS
    var n = fs.normalise(c)
    if fs.existe(n) || !fs.dossiers.contains(fs.parent(n))    return false    end
    fs.dossiers[n] = true
    return true
end
path.rmdir = def (c)
    var fs = global.LITTLEFS
    var n = fs.normalise(c)
    if !fs.dossiers.contains(n) || size(fs.liste(n)) > 0    return false    end
    fs.dossiers.remove(n)
    return true
end
path.remove = def (c)
    var fs = global.LITTLEFS
    var n = fs.normalise(c)
    if !fs.fichiers.contains(n)    return false    end
    fs.fichiers.remove(n)
    return true
end
path.rename = def (de, vers)
    var fs = global.LITTLEFS
    var a = fs.normalise(de)
    if !fs.fichiers.contains(a)    return false    end
    fs.fichiers[fs.normalise(vers)] = fs.fichiers[a]
    fs.fichiers.remove(a)
    return true
end
path.last_modified = def (c) return global.LITTLEFS.existe(c) ? 1792000000 : nil end
path.format = def (c) return false end
return path
