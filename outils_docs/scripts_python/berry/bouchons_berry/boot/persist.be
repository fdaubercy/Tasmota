# Bouchon du module natif 'persist' pour banc_boot.be : meme interface que le Persist du firmware
# (lib/libesp32/berry_tasmota/src/embedded/persist.be) - member/setmember sur la map _p - mais adosse au
# LittleFS EN MEMOIRE du banc (LITTLEFS, pose par faux_firmware.be). 'sauvegardes' compte les save().
# Comme le firmware, 'import persist' rend une INSTANCE (persist.serveur = ... ecrit dans _p).
import global
class PERSIST_BANC
    var _p, _dirty, sauvegardes
    def init() self._p = {} self._dirty = false self.sauvegardes = 0 self.load() end
    def member(k) return self._p.find(k) end
    def setmember(k, v) self._p[k] = v self._dirty = true end
    def zero() self._p = {} self._dirty = true end
    def dirty() self._dirty = true end
    def remove(k) self._p.remove(k) self._dirty = true end
    def contains(k) return self._p.contains(k) end
    def has(k) return self._p.contains(k) end
    def find(k, d) return self._p.find(k, d) end
    def load()
        import json
        var texte = global.LITTLEFS.fichiers.find("/_persist.json")
        if texte == nil    return    end
        var val = json.load(texte)
        if isinstance(val, map)    self._p = val    else    print("BRY: failed to load _persist.json")    end
        self._dirty = false
    end
    def save(force)
        import json
        if self._dirty || force
            global.LITTLEFS.fichiers["/_persist.json"] = json.dump(self._p)
            self.sauvegardes += 1
            self._dirty = false
        end
    end
end
return PERSIST_BANC()
