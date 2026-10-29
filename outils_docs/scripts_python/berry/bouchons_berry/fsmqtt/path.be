# Bouchon du module natif 'path' pour banc_fsmqtt.be : FS EN MEMOIRE, global FS = {"fichiers": {chemin: bytes},
# "dossiers": {chemin: true}}. Aucun fichier du PC n'est touche. listdir rend des noms, comme le firmware.
var path = module("path")
path.exists = def (c) import global return global.FS["fichiers"].contains(c) || global.FS["dossiers"].contains(c) || c == "/" end
path.isdir = def (c) import global return c == "/" || global.FS["dossiers"].contains(c) end
path.mkdir = def (c) import global global.FS["dossiers"][c] = true return true end
path.remove = def (c) import global
    if !global.FS["fichiers"].contains(c)    return false    end
    global.FS["fichiers"].remove(c)  return true
end
path.rmdir = def (c) import global
    if !global.FS["dossiers"].contains(c)    return false    end
    global.FS["dossiers"].remove(c)  return true
end
path.rename = def (a, b) import global
    if !global.FS["fichiers"].contains(a) || global.FS["fichiers"].contains(b) || global.RENOMMAGE_REFUSE    return false    end
    global.FS["fichiers"][b] = global.FS["fichiers"][a]  global.FS["fichiers"].remove(a)  return true
end
path.listdir = def (d) import global import string
    var prefixe = d == "/" ? "/" : d + "/"
    var noms = []
    for tab: [global.FS["fichiers"], global.FS["dossiers"]]
        for c: tab.keys()
            if string.find(c, prefixe) == 0 && string.find(c[size(prefixe) ..], "/") < 0    noms.push(c[size(prefixe) ..])    end
        end
    end
    return noms
end
return path
