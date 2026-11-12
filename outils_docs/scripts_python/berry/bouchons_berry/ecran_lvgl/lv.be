# Bouchon du module lv (LVGL 9 de Tasmota) pour banc_ecran_lvgl.be et la variante lvgl de banc_demarrage : chaque objet
# garde son etat (type, parent, position, taille, texte, styles par "propriete:selecteur", plage, valeur, series, rappels)
# et chaque appel de methode d'objet ou de lv.screen_load est compte dans lv.appels et journalise dans lv.journal
# ([objet, methode, arguments]). lv.color(x) rend x : les couleurs se relisent en entiers. Constantes : valeurs de LVGL 9
# (lv_obj.h, lv_text.h) ; seules leurs differences comptent ici. Polices : robotocondensed embarquee en 12, 16 et 24
# seulement (tasmota_lv_conf.h), une autre taille leve value_error comme lv0_load_font_embedded.
var lv = module("lv")
lv.appels = 0
lv.journal = []
lv.objets = []          # tous les objets crees, dans l'ordre
lv.ecran = nil          # dernier ecran charge (lv.screen_load)
lv.polices = []         # [fonction, nom, taille] de chaque police chargee
lv.demarre = 0          # appels de lv.start()

lv.PART_MAIN = 0x000000
lv.PART_SCROLLBAR = 0x010000
lv.PART_INDICATOR = 0x020000
lv.PART_KNOB = 0x030000
lv.PART_SELECTED = 0x040000
lv.PART_ITEMS = 0x050000
lv.PART_CURSOR = 0x060000
lv.PART_CUSTOM_FIRST = 0x080000
lv.STATE_DEFAULT = 0x0000
lv.STATE_CHECKED = 0x0001
lv.STATE_PRESSED = 0x0020
lv.STATE_DISABLED = 0x0080
lv.TEXT_ALIGN_LEFT = 1
lv.TEXT_ALIGN_CENTER = 2
lv.TEXT_ALIGN_RIGHT = 3
lv.ALIGN_CENTER = 9
lv.ANIM_OFF = 0
lv.CHART_AXIS_PRIMARY_Y = 0
lv.CHART_AXIS_SECONDARY_Y = 1
lv.CHART_UPDATE_MODE_SHIFT = 0
lv.CHART_POINT_NONE = 0x7FFFFFFF
lv.EVENT_CLICKED = 10

class FauxObjetLv
    var type, parent, x, y, w, h, texte, styles, mini, maxi, valeur, series, points, axe, div, nbPoints, mode, rappels, aligne
    def init(t, p)
        self.type = t    self.parent = p    self.styles = {}    self.series = []    self.points = []    self.rappels = []
        self.mini = 0    self.maxi = 100
        import lv
        lv.objets.push(self)
    end
    def note(m, a)
        import lv
        lv.appels += 1
        lv.journal.push([self, m, a])
    end
    def set_pos(x, y)    self.x = x    self.y = y    self.note("set_pos", [x, y])    end
    def set_size(w, h)    self.w = w    self.h = h    self.note("set_size", [w, h])    end
    def set_text(t)    self.texte = t    self.note("set_text", [t])    end
    def set_align(a)    self.aligne = a    self.note("set_align", [a])    end
    def set_range(a, b)    self.mini = a    self.maxi = b    self.note("set_range", [a, b])    end
    def get_min_value()    return self.mini    end
    def get_max_value()    return self.maxi    end
    def set_value(v, anim)    self.valeur = v    self.note("set_value", [v, anim])    end
    def set_point_count(n)    self.nbPoints = n    self.note("set_point_count", [n])    end
    def set_axis_range(a, mn, mx)    self.axe = [a, mn, mx]    self.note("set_axis_range", [a, mn, mx])    end
    def set_div_line_count(h, v)    self.div = [h, v]    self.note("set_div_line_count", [h, v])    end
    def set_update_mode(m)    self.mode = m    self.note("set_update_mode", [m])    end
    def add_series(c, axe)    self.series.push([c, axe])    self.points.push([])    self.note("add_series", [c, axe])    return size(self.series) - 1    end
    def set_next_value(s, v)    self.points[s].push(v)    self.note("set_next_value", [s, v])    end
    def add_event_cb(f, code, d)    self.rappels.push([f, code])    self.note("add_event_cb", [code])    end
    # Tout set_style_<propriete>(valeur, selecteur) : garde dans styles["<propriete>:<selecteur>"] ; aucun autre membre
    def member(n)
        import string
        if !string.startswith(n, "set_style_")    return nil    end
        var o = self
        var p = n[10 ..]
        return def (*a)
            o.styles[p + ":" + str(a[-1])] = a[-2]
            o.note(n, [a[-2], a[-1]])
        end
    end
    # Style relu : style("bg_color", lv.PART_INDICATOR) ; selecteur absent = 0
    def style(p, sel)    return self.styles.find(p + ":" + str(sel == nil ? 0 : sel))    end
end
lv.FauxObjetLv = FauxObjetLv

lv.start = def () lv.demarre += 1 end
lv.color = def (x) return x end
lv.pct = def (v) return v end
lv.obj = def (p) return FauxObjetLv("obj", p) end
lv.label = def (p) return FauxObjetLv("label", p) end
lv.button = def (p) return FauxObjetLv("button", p) end    # pas de lv.btn : absent du firmware (be_lv_c_mapping.h)
lv.bar = def (p) return FauxObjetLv("bar", p) end
lv.chart = def (p) return FauxObjetLv("chart", p) end
lv.arc = def (p) return FauxObjetLv("arc", p) end
lv.slider = def (p) return FauxObjetLv("slider", p) end
lv.haut = nil
lv.bas = nil
lv.layer_top = def () if lv.haut == nil lv.haut = FauxObjetLv("layer_top", nil) end return lv.haut end
lv.layer_bottom = def () if lv.bas == nil lv.bas = FauxObjetLv("layer_bottom", nil) end return lv.bas end
lv.screen_load = def (e) lv.ecran = e lv.appels += 1 lv.journal.push([e, "screen_load", []]) end
lv.font_embedded = def (nom, t)
    if nom == "robotocondensed" && [12, 16, 24].find(t) == nil    raise "value_error", "unknown font size"    end
    lv.polices.push(["font_embedded", nom, t])
    return "embarquee:" + nom + "-" + str(t)
end
lv.load_freetype_font = def (nom, t, s) lv.polices.push(["load_freetype_font", nom, t]) return "ttf:" + nom + "-" + str(t) end
lv.load_font = def (nom) lv.polices.push(["load_font", nom, 0]) return "bin:" + nom end
return lv
