# Interface LVGL pur de l'ecran (module ecranLvgl), GENEREE par outils_docs/scripts_python/outils_pc/atelier_ecrans_lvgl.py
# depuis la description ecran.json de l'atelier des ecrans (outils_docs/atelier_ecrans/cartes/<env>/) : NE PAS EDITER, modifier
# la description puis regenerer. Ecran ST7262_1024x600, 5 pages, 182 objets. Interchangeable avec ecranHaspmota.be +
# pages.jsonl (custom_interface_ecran du cenv). API (en tete du module metier) : demarre() -> true si l'ecran est
# pret ; affiche(modele) chaque seconde, n'ecrit que ce qui a change (cache par objet et attribut). Objets nommes p<page>b<id>
# comme HASPmota ; page 0 sur lv.layer_top() (toutes les pages), une page n >= 1 = un ecran lv.obj(0) charge par lv.screen_load.
# Logs : charte du CLAUDE.md (logFonctions.log, seuil `general`).
var ecranLvgl = module("ecranLvgl")

# ---- Touchers : une fonction nommee par objet tactile, executee par tasmota.defer ----
def ecranLvgl_p3b22()    import ecranDebitsFonctions    ecranDebitsFonctions.ajuste("fenetre", -1)    end
def ecranLvgl_p3b24()    import ecranDebitsFonctions    ecranDebitsFonctions.ajuste("fenetre", 1)    end
def ecranLvgl_p3b32()    import ecranDebitsFonctions    ecranDebitsFonctions.ajuste("veille", -1)    end
def ecranLvgl_p3b34()    import ecranDebitsFonctions    ecranDebitsFonctions.ajuste("veille", 1)    end
def ecranLvgl_p3b42()    import ecranDebitsFonctions    ecranDebitsFonctions.ajuste("luminosite", -10)    end
def ecranLvgl_p3b44()    import ecranDebitsFonctions    ecranDebitsFonctions.ajuste("luminosite", 10)    end
def ecranLvgl_p4b120()    import ecranSysteme    ecranSysteme.appui(120)    end
def ecranLvgl_p4b121()    import ecranSysteme    ecranSysteme.appui(121)    end
def ecranLvgl_p0b201()    import ecranLvgl    ecranLvgl.montre(1)    end
def ecranLvgl_p0b202()    import ecranLvgl    ecranLvgl.montre(2)    end
def ecranLvgl_p0b203()    import ecranLvgl    ecranLvgl.montre(3)    end
def ecranLvgl_p0b204()    import ecranLvgl    ecranLvgl.montre(4)    end

# ---- Tables tirees de la description ----
ecranLvgl.DEPART = 1
ecranLvgl.COULEURS = {"etat": {"normal": 0xE8EDF2, "imprecis": 0xFFA53F, "muet": 0xFF5A5A, "inconnu": 0x5B6B7C, "arret": 0x9FB3C8, "bleu": 0x3FA7FF, "vert": 0x3FD08A}}
ecranLvgl.PAGES = [[0, []],
    [1, [["bg_color", 0x10161E], ["bg_grad_color", 0x10161E], ["text_color", 0xE8EDF2]]],
    [2, [["bg_color", 0x10161E], ["bg_grad_color", 0x10161E], ["text_color", 0xE8EDF2]]],
    [3, [["bg_color", 0x10161E], ["bg_grad_color", 0x10161E], ["text_color", 0xE8EDF2]]],
    [4, [["bg_color", 0x10161E], ["bg_grad_color", 0x10161E], ["text_color", 0xE8EDF2]]]]
# [page, id, type, x, y, l, h, [[attribut, valeur]], fonction du toucher]
ecranLvgl.OBJETS = [
    [0, 1, "label", 24, 14, 210, 40, [["text", "Débits nourrice"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-32"], ["text_color", 0xE8EDF2]], nil],
    [0, 2, "obj", 240, 30, 12, 12, [["radius", 6], ["border_width", 0], ["bg_color", 0x5B6B7C]], nil],
    [0, 3, "label", 260, 22, 300, 28, [["text", "aucun relevé"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [0, 4, "label", 580, 14, 420, 40, [["text", "Total inconnu"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-32"], ["text_color", 0x3FA7FF], ["align", 2]], nil],
    [1, 11, "label", 24, 84, 180, 36, [["text", "Débit 1"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [1, 12, "bar", 212, 89, 532, 26, [["min", 0], ["max", 100], ["radius", 13], ["bg_color", 0x1F2B38], ["radius10", 13], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [1, 13, "label", 748, 80, 112, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [1, 14, "label", 866, 94, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [1, 15, "label", 926, 92, 74, 26, [["text", ""], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8], ["align", 2]], nil],
    [1, 21, "label", 24, 154, 180, 36, [["text", "Débit 2"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [1, 22, "bar", 212, 159, 532, 26, [["min", 0], ["max", 100], ["radius", 13], ["bg_color", 0x1F2B38], ["radius10", 13], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [1, 23, "label", 748, 150, 112, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [1, 24, "label", 866, 164, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [1, 25, "label", 926, 162, 74, 26, [["text", ""], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8], ["align", 2]], nil],
    [1, 31, "label", 24, 224, 180, 36, [["text", "Débit 3"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [1, 32, "bar", 212, 229, 532, 26, [["min", 0], ["max", 100], ["radius", 13], ["bg_color", 0x1F2B38], ["radius10", 13], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [1, 33, "label", 748, 220, 112, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [1, 34, "label", 866, 234, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [1, 35, "label", 926, 232, 74, 26, [["text", ""], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8], ["align", 2]], nil],
    [1, 41, "label", 24, 294, 180, 36, [["text", "Débit 4"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [1, 42, "bar", 212, 299, 532, 26, [["min", 0], ["max", 100], ["radius", 13], ["bg_color", 0x1F2B38], ["radius10", 13], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [1, 43, "label", 748, 290, 112, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [1, 44, "label", 866, 304, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [1, 45, "label", 926, 302, 74, 26, [["text", ""], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8], ["align", 2]], nil],
    [1, 51, "label", 24, 364, 180, 36, [["text", "Débit 5"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [1, 52, "bar", 212, 369, 532, 26, [["min", 0], ["max", 100], ["radius", 13], ["bg_color", 0x1F2B38], ["radius10", 13], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [1, 53, "label", 748, 360, 112, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [1, 54, "label", 866, 374, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [1, 55, "label", 926, 372, 74, 26, [["text", ""], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8], ["align", 2]], nil],
    [1, 61, "label", 24, 434, 180, 36, [["text", "Débit 6"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [1, 62, "bar", 212, 439, 532, 26, [["min", 0], ["max", 100], ["radius", 13], ["bg_color", 0x1F2B38], ["radius10", 13], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [1, 63, "label", 748, 430, 112, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [1, 64, "label", 866, 444, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [1, 65, "label", 926, 442, 74, 26, [["text", ""], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8], ["align", 2]], nil],
    [2, 11, "obj", 24, 100, 14, 14, [["radius", 7], ["border_width", 0], ["bg_color", 0x3FA7FF]], nil],
    [2, 12, "label", 50, 90, 190, 32, [["text", "Débit 1"], ["text_font", 24], ["text_color", 0xE8EDF2]], nil],
    [2, 13, "label", 246, 84, 126, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [2, 14, "label", 378, 98, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [2, 21, "obj", 24, 172, 14, 14, [["radius", 7], ["border_width", 0], ["bg_color", 0x3FD08A]], nil],
    [2, 22, "label", 50, 162, 190, 32, [["text", "Débit 2"], ["text_font", 24], ["text_color", 0xE8EDF2]], nil],
    [2, 23, "label", 246, 156, 126, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [2, 24, "label", 378, 170, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [2, 31, "obj", 24, 244, 14, 14, [["radius", 7], ["border_width", 0], ["bg_color", 0xFFA53F]], nil],
    [2, 32, "label", 50, 234, 190, 32, [["text", "Débit 3"], ["text_font", 24], ["text_color", 0xE8EDF2]], nil],
    [2, 33, "label", 246, 228, 126, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [2, 34, "label", 378, 242, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [2, 41, "obj", 24, 316, 14, 14, [["radius", 7], ["border_width", 0], ["bg_color", 0xC084FC]], nil],
    [2, 42, "label", 50, 306, 190, 32, [["text", "Débit 4"], ["text_font", 24], ["text_color", 0xE8EDF2]], nil],
    [2, 43, "label", 246, 300, 126, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [2, 44, "label", 378, 314, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [2, 51, "obj", 24, 388, 14, 14, [["radius", 7], ["border_width", 0], ["bg_color", 0xFF5A5A]], nil],
    [2, 52, "label", 50, 378, 190, 32, [["text", "Débit 5"], ["text_font", 24], ["text_color", 0xE8EDF2]], nil],
    [2, 53, "label", 246, 372, 126, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [2, 54, "label", 378, 386, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [2, 61, "obj", 24, 460, 14, 14, [["radius", 7], ["border_width", 0], ["bg_color", 0xF5D04A]], nil],
    [2, 62, "label", 50, 450, 190, 32, [["text", "Débit 6"], ["text_font", 24], ["text_color", 0xE8EDF2]], nil],
    [2, 63, "label", 246, 444, 126, 44, [["text", "-,--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0x5B6B7C], ["align", 2]], nil],
    [2, 64, "label", 378, 458, 60, 26, [["text", "L/min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [2, 70, "chart", 448, 76, 552, 420, [["point_count", 60], ["y_min", 0], ["y_max", 1000], ["h_div_line_count", 5], ["v_div_line_count", 0], ["radius", 16], ["border_width", 0], ["bg_color", 0x17202B], ["line_color", 0x1F2B38]], nil],
    [2, 71, "label", 460, 82, 200, 22, [["text", "10 L/min"], ["text_font", 16], ["text_color", 0x9FB3C8]], nil],
    [2, 72, "label", 448, 502, 120, 22, [["text", "-30 min"], ["text_font", 16], ["text_color", 0x9FB3C8], ["align", 0]], nil],
    [2, 73, "label", 586, 502, 120, 22, [["text", "-20 min"], ["text_font", 16], ["text_color", 0x9FB3C8], ["align", 1]], nil],
    [2, 74, "label", 770, 502, 120, 22, [["text", "-10 min"], ["text_font", 16], ["text_color", 0x9FB3C8], ["align", 1]], nil],
    [2, 75, "label", 880, 502, 120, 22, [["text", "maint."], ["text_font", 16], ["text_color", 0x9FB3C8], ["align", 2]], nil],
    [3, 21, "label", 60, 104, 420, 36, [["text", "Fenêtre de mesure"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [3, 25, "label", 60, 144, 420, 26, [["text", "la même que sur la carte d'acquisition"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [3, 22, "btn", 520, 100, 96, 72, [["radius", 36], ["border_width", 0], ["text", "-"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p3b22],
    [3, 23, "label", 626, 114, 200, 44, [["text", "10 s"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0xE8EDF2], ["align", 1]], nil],
    [3, 24, "btn", 836, 100, 96, 72, [["radius", 36], ["border_width", 0], ["text", "+"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p3b24],
    [3, 31, "label", 60, 240, 420, 36, [["text", "Veille de l'écran"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [3, 35, "label", 60, 280, 420, 26, [["text", "10 % sans toucher, puis éteint"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [3, 32, "btn", 520, 236, 96, 72, [["radius", 36], ["border_width", 0], ["text", "-"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p3b32],
    [3, 33, "label", 626, 250, 200, 44, [["text", "5 min"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0xE8EDF2], ["align", 1]], nil],
    [3, 34, "btn", 836, 236, 96, 72, [["radius", 36], ["border_width", 0], ["text", "+"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p3b34],
    [3, 41, "label", 60, 376, 420, 36, [["text", "Luminosité"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-28"], ["text_color", 0xE8EDF2]], nil],
    [3, 45, "label", 60, 416, 420, 26, [["text", "en service, réveil au toucher"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["text_color", 0x9FB3C8]], nil],
    [3, 42, "btn", 520, 372, 96, 72, [["radius", 36], ["border_width", 0], ["text", "-"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p3b42],
    [3, 43, "label", 626, 386, 200, 44, [["text", "80 %"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["text_color", 0xE8EDF2], ["align", 1]], nil],
    [3, 44, "btn", 836, 372, 96, 72, [["radius", 36], ["border_width", 0], ["text", "+"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-36"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p3b44],
    [4, 180, "label", 24, 64, 314, 19, [["text", "Mémoire"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 130, "label", 24, 83, 157, 19, [["text", "RAM interne libre"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 1, "label", 181, 83, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 131, "label", 24, 102, 157, 19, [["text", "RAM libre minimale"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 2, "label", 181, 102, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 132, "label", 24, 121, 157, 19, [["text", "Fragmentation de la RAM"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 4, "bar", 181, 125, 54, 9, [["min", 0], ["max", 100], ["radius", 4], ["bg_color", 0x1F2B38], ["radius10", 4], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [4, 3, "label", 243, 121, 95, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 133, "label", 24, 140, 157, 19, [["text", "PSRAM totale"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 5, "label", 181, 140, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 134, "label", 24, 159, 157, 19, [["text", "PSRAM libre"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 7, "bar", 181, 163, 54, 9, [["min", 0], ["max", 100], ["radius", 4], ["bg_color", 0x1F2B38], ["radius10", 4], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [4, 6, "label", 243, 159, 95, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 135, "label", 24, 178, 157, 19, [["text", "RAM libre au dernier GC"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 8, "label", 181, 178, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 136, "label", 24, 197, 157, 19, [["text", "Durée du dernier GC"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 9, "label", 181, 197, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 137, "label", 24, 216, 157, 19, [["text", "Pile minimale"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 10, "label", 181, 216, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 138, "label", 24, 235, 157, 19, [["text", "IRAM libre"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 11, "label", 181, 235, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 181, "label", 24, 260, 314, 19, [["text", "Flash"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 139, "label", 24, 279, 157, 19, [["text", "Programme"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 20, "label", 181, 279, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 140, "label", 24, 298, 157, 19, [["text", "Place libre OTA"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 22, "bar", 181, 302, 54, 9, [["min", 0], ["max", 100], ["radius", 4], ["bg_color", 0x1F2B38], ["radius10", 4], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [4, 21, "label", 243, 298, 95, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 141, "label", 24, 317, 157, 19, [["text", "Mise à jour OTA"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 23, "label", 181, 317, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 142, "label", 24, 336, 157, 19, [["text", "Système de fichiers"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 24, "label", 181, 336, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 143, "label", 24, 355, 157, 19, [["text", "Système de fichiers libre"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 26, "bar", 181, 359, 54, 9, [["min", 0], ["max", 100], ["radius", 4], ["bg_color", 0x1F2B38], ["radius10", 4], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [4, 25, "label", 243, 355, 95, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 182, "label", 354, 64, 314, 19, [["text", "Charge"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 144, "label", 354, 83, 157, 19, [["text", "Charge (LoadAvg)"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 31, "bar", 511, 87, 54, 9, [["min", 0], ["max", 100], ["radius", 4], ["bg_color", 0x1F2B38], ["radius10", 4], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [4, 30, "label", 573, 83, 95, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 145, "label", 354, 102, 157, 19, [["text", "Sleep"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 32, "label", 511, 102, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 146, "label", 354, 121, 157, 19, [["text", "Température de la puce"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 33, "label", 511, 121, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 183, "label", 354, 146, 314, 19, [["text", "Redémarrages"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 147, "label", 354, 165, 157, 19, [["text", "En service depuis"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 40, "label", 511, 165, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 148, "label", 354, 184, 157, 19, [["text", "Cause du redémarrage"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 41, "label", 511, 184, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 149, "label", 354, 203, 157, 19, [["text", "Démarrages"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 42, "label", 511, 203, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 184, "label", 354, 228, 314, 19, [["text", "Réseau"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 150, "label", 354, 247, 157, 19, [["text", "Signal Wi-Fi"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 51, "bar", 511, 251, 54, 9, [["min", 0], ["max", 100], ["radius", 4], ["bg_color", 0x1F2B38], ["radius10", 4], ["bg_color10", 0x3FA7FF], ["val", 0]], nil],
    [4, 50, "label", 573, 247, 95, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 151, "label", 354, 266, 157, 19, [["text", "Point d'accès (BSSID)"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 52, "label", 511, 266, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 152, "label", 354, 285, 157, 19, [["text", "Adresse IP"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 53, "label", 511, 285, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 153, "label", 354, 304, 157, 19, [["text", "Pertes du Wi-Fi"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 54, "label", 511, 304, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 154, "label", 354, 323, 157, 19, [["text", "Durée hors ligne"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 55, "label", 511, 323, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 155, "label", 354, 342, 157, 19, [["text", "MQTT"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 56, "label", 511, 342, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 156, "label", 354, 361, 157, 19, [["text", "Reconnexions MQTT"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 57, "label", 511, 361, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 157, "label", 354, 380, 157, 19, [["text", "Heure"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 58, "label", 511, 380, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 185, "label", 684, 64, 314, 19, [["text", "ModBus"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 158, "label", 684, 83, 157, 19, [["text", "Esclaves ModBus joignables"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 70, "label", 841, 83, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 159, "label", 684, 102, 157, 19, [["text", "Délais ModBus dépassés"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 71, "label", 841, 102, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 160, "label", 684, 121, 157, 19, [["text", "Dernier contact ModBus"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 72, "label", 841, 121, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 161, "label", 684, 140, 157, 19, [["text", "Clients du point d'accès"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 73, "label", 841, 140, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 186, "label", 684, 165, 314, 19, [["text", "Écran"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 162, "label", 684, 184, 157, 19, [["text", "Luminosité de l'écran"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 80, "label", 841, 184, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 163, "label", 684, 203, 157, 19, [["text", "Veille de l'écran"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 81, "label", 841, 203, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 187, "label", 684, 228, 314, 19, [["text", "Firmware"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 164, "label", 684, 247, 157, 19, [["text", "Version du firmware"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 90, "label", 841, 247, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 165, "label", 684, 266, 157, 19, [["text", "Compilé le"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 91, "label", 841, 266, 157, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2], ["align", 2]], nil],
    [4, 188, "label", 24, 405, 976, 19, [["text", "Journal"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x3FA7FF]], nil],
    [4, 166, "label", 24, 424, 157, 19, [["text", "Dernière erreur"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 101, "label", 181, 424, 819, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2]], nil],
    [4, 167, "label", 24, 443, 157, 19, [["text", "Erreur précédente"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 102, "label", 181, 443, 819, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2]], nil],
    [4, 168, "label", 24, 462, 157, 19, [["text", "Erreur précédente"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 103, "label", 181, 462, 819, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2]], nil],
    [4, 169, "label", 24, 481, 157, 19, [["text", "Erreur précédente"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 104, "label", 181, 481, 819, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2]], nil],
    [4, 170, "label", 24, 500, 157, 19, [["text", "Erreur précédente"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0x9FB3C8]], nil],
    [4, 105, "label", 181, 500, 819, 19, [["text", "--"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["text_color", 0xE8EDF2]], nil],
    [4, 120, "btn", 684, 355, 149, 44, [["radius", 22], ["border_width", 0], ["text", "Lancer le GC"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p4b120],
    [4, 121, "btn", 849, 355, 149, 44, [["radius", 22], ["border_width", 0], ["text", "Redémarrer"], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-14"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2]], ecranLvgl_p4b121],
    [0, 201, "btn", 24, 540, 112, 46, [["radius", 23], ["border_width", 0], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2], ["text", "Débits"]], ecranLvgl_p0b201],
    [0, 202, "btn", 148, 540, 123, 46, [["radius", 23], ["border_width", 0], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2], ["text", "Courbes"]], ecranLvgl_p0b202],
    [0, 203, "btn", 283, 540, 134, 46, [["radius", 23], ["border_width", 0], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2], ["text", "Réglages"]], ecranLvgl_p0b203],
    [0, 204, "btn", 429, 540, 123, 46, [["radius", 23], ["border_width", 0], ["text_font", "A:sd/polices/RobotoCondensed-Regular.ttf-20"], ["bg_color", 0x1F2B38], ["text_color", 0xE8EDF2], ["text", "Système"]], ecranLvgl_p0b204]]
# [objet, chemin dans le modele, attribut, table de couleurs, couleurs si / sauf, sinon, format, echelle] ; une ligne par objet
ecranLvgl.LIAISONS = [
    ["p0b2", ["liaison"], "bg_color", "etat", nil, nil, nil, nil],
    ["p0b3", ["releve"], "text", nil, nil, nil, nil, nil],
    ["p0b4", ["total"], "text", nil, nil, nil, nil, nil],
    ["p1b11", ["voies", 0, "nom"], "text", nil, nil, nil, nil, nil], ["p1b11", ["voies", 0, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p1b12", ["voies", 0, "barre"], "val", nil, nil, nil, nil, nil], ["p1b12", ["voies", 0, "etat"], "bg_color10", nil, {"imprecis": 0xFFA53F}, 0x3FA7FF, nil, nil],
    ["p1b13", ["voies", 0, "debit"], "text", nil, nil, nil, nil, nil], ["p1b13", ["voies", 0, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p1b14", ["voies", 0, "unite"], "text", nil, nil, nil, nil, nil],
    ["p1b15", ["voies", 0, "part"], "text", nil, nil, nil, nil, nil],
    ["p1b21", ["voies", 1, "nom"], "text", nil, nil, nil, nil, nil], ["p1b21", ["voies", 1, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p1b22", ["voies", 1, "barre"], "val", nil, nil, nil, nil, nil], ["p1b22", ["voies", 1, "etat"], "bg_color10", nil, {"imprecis": 0xFFA53F}, 0x3FA7FF, nil, nil],
    ["p1b23", ["voies", 1, "debit"], "text", nil, nil, nil, nil, nil], ["p1b23", ["voies", 1, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p1b24", ["voies", 1, "unite"], "text", nil, nil, nil, nil, nil],
    ["p1b25", ["voies", 1, "part"], "text", nil, nil, nil, nil, nil],
    ["p1b31", ["voies", 2, "nom"], "text", nil, nil, nil, nil, nil], ["p1b31", ["voies", 2, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p1b32", ["voies", 2, "barre"], "val", nil, nil, nil, nil, nil], ["p1b32", ["voies", 2, "etat"], "bg_color10", nil, {"imprecis": 0xFFA53F}, 0x3FA7FF, nil, nil],
    ["p1b33", ["voies", 2, "debit"], "text", nil, nil, nil, nil, nil], ["p1b33", ["voies", 2, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p1b34", ["voies", 2, "unite"], "text", nil, nil, nil, nil, nil],
    ["p1b35", ["voies", 2, "part"], "text", nil, nil, nil, nil, nil],
    ["p1b41", ["voies", 3, "nom"], "text", nil, nil, nil, nil, nil], ["p1b41", ["voies", 3, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p1b42", ["voies", 3, "barre"], "val", nil, nil, nil, nil, nil], ["p1b42", ["voies", 3, "etat"], "bg_color10", nil, {"imprecis": 0xFFA53F}, 0x3FA7FF, nil, nil],
    ["p1b43", ["voies", 3, "debit"], "text", nil, nil, nil, nil, nil], ["p1b43", ["voies", 3, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p1b44", ["voies", 3, "unite"], "text", nil, nil, nil, nil, nil],
    ["p1b45", ["voies", 3, "part"], "text", nil, nil, nil, nil, nil],
    ["p1b51", ["voies", 4, "nom"], "text", nil, nil, nil, nil, nil], ["p1b51", ["voies", 4, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p1b52", ["voies", 4, "barre"], "val", nil, nil, nil, nil, nil], ["p1b52", ["voies", 4, "etat"], "bg_color10", nil, {"imprecis": 0xFFA53F}, 0x3FA7FF, nil, nil],
    ["p1b53", ["voies", 4, "debit"], "text", nil, nil, nil, nil, nil], ["p1b53", ["voies", 4, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p1b54", ["voies", 4, "unite"], "text", nil, nil, nil, nil, nil],
    ["p1b55", ["voies", 4, "part"], "text", nil, nil, nil, nil, nil],
    ["p1b61", ["voies", 5, "nom"], "text", nil, nil, nil, nil, nil], ["p1b61", ["voies", 5, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p1b62", ["voies", 5, "barre"], "val", nil, nil, nil, nil, nil], ["p1b62", ["voies", 5, "etat"], "bg_color10", nil, {"imprecis": 0xFFA53F}, 0x3FA7FF, nil, nil],
    ["p1b63", ["voies", 5, "debit"], "text", nil, nil, nil, nil, nil], ["p1b63", ["voies", 5, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p1b64", ["voies", 5, "unite"], "text", nil, nil, nil, nil, nil],
    ["p1b65", ["voies", 5, "part"], "text", nil, nil, nil, nil, nil],
    ["p2b12", ["voies", 0, "nom"], "text", nil, nil, nil, nil, nil], ["p2b12", ["voies", 0, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p2b13", ["voies", 0, "debit"], "text", nil, nil, nil, nil, nil], ["p2b13", ["voies", 0, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p2b14", ["voies", 0, "unite"], "text", nil, nil, nil, nil, nil],
    ["p2b22", ["voies", 1, "nom"], "text", nil, nil, nil, nil, nil], ["p2b22", ["voies", 1, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p2b23", ["voies", 1, "debit"], "text", nil, nil, nil, nil, nil], ["p2b23", ["voies", 1, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p2b24", ["voies", 1, "unite"], "text", nil, nil, nil, nil, nil],
    ["p2b32", ["voies", 2, "nom"], "text", nil, nil, nil, nil, nil], ["p2b32", ["voies", 2, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p2b33", ["voies", 2, "debit"], "text", nil, nil, nil, nil, nil], ["p2b33", ["voies", 2, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p2b34", ["voies", 2, "unite"], "text", nil, nil, nil, nil, nil],
    ["p2b42", ["voies", 3, "nom"], "text", nil, nil, nil, nil, nil], ["p2b42", ["voies", 3, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p2b43", ["voies", 3, "debit"], "text", nil, nil, nil, nil, nil], ["p2b43", ["voies", 3, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p2b44", ["voies", 3, "unite"], "text", nil, nil, nil, nil, nil],
    ["p2b52", ["voies", 4, "nom"], "text", nil, nil, nil, nil, nil], ["p2b52", ["voies", 4, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p2b53", ["voies", 4, "debit"], "text", nil, nil, nil, nil, nil], ["p2b53", ["voies", 4, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p2b54", ["voies", 4, "unite"], "text", nil, nil, nil, nil, nil],
    ["p2b62", ["voies", 5, "nom"], "text", nil, nil, nil, nil, nil], ["p2b62", ["voies", 5, "etat"], "text_color", "etat", {"normal": 0xE8EDF2, "arret": 0xE8EDF2}, nil, nil, nil],
    ["p2b63", ["voies", 5, "debit"], "text", nil, nil, nil, nil, nil], ["p2b63", ["voies", 5, "etat"], "text_color", "etat", nil, nil, nil, nil],
    ["p2b64", ["voies", 5, "unite"], "text", nil, nil, nil, nil, nil],
    ["p2b70", ["courbeMax"], "y_max", nil, nil, nil, nil, nil],
    ["p2b71", ["courbeMax"], "text", nil, nil, nil, "%d L/min", 100],
    ["p3b23", ["reglages", "fenetre"], "text", nil, nil, nil, nil, nil],
    ["p3b33", ["reglages", "veille"], "text", nil, nil, nil, nil, nil],
    ["p3b43", ["reglages", "luminosite"], "text", nil, nil, nil, nil, nil]]
# [bouton, page menee, {attribut: [couleur page courante, couleur sinon]}]
ecranLvgl.ACTIFS = [["p0b201", 1, {"bg_color": [0x3FA7FF, 0x1F2B38], "text_color": [0x06121F, 0xE8EDF2]}], ["p0b202", 2, {"bg_color": [0x3FA7FF, 0x1F2B38], "text_color": [0x06121F, 0xE8EDF2]}], ["p0b203", 3, {"bg_color": [0x3FA7FF, 0x1F2B38], "text_color": [0x06121F, 0xE8EDF2]}], ["p0b204", 4, {"bg_color": [0x3FA7FF, 0x1F2B38], "text_color": [0x06121F, 0xE8EDF2]}]]
# [chart, chemin des series, chemin du compteur de points, couleurs des series]
ecranLvgl.COURBE = ["p2b70", ["historique"], ["points"], [0x3FA7FF, 0x3FD08A, 0xFFA53F, 0xC084FC, 0xFF5A5A, 0xF5D04A]]

# ---- Moteur (identique pour toute description) ----
# Classe LVGL d'un type HASPmota dont le nom differe (lv_haspmota.be : lvh_btn._lv_class = lv.button ; lv.btn n'existe pas dans
# le firmware, seul lv_button est enregistre, be_lv_c_mapping.h) ; les autres types portent le nom de leur classe
ecranLvgl.CLASSES = {"btn": "button", "img": "image", "btnmatrix": "buttonmatrix", "cpicker": "colorwheel"}
ecranLvgl.cache = {}      # "p1b13" -> {"text": valeur brute deja ecrite} (aucune cle construite a chaque seconde)
ecranLvgl.objets = {}     # "p1b13" -> objet LVGL ; "p<n>b0" -> ecran de la page n
ecranLvgl.types = {}      # "p1b13" -> type de la description
ecranLvgl.textes = {}     # "p0b91" -> label qui porte le texte (l'objet lui-meme pour un label)
ecranLvgl.ecrans = {}     # n -> ecran de la page n
ecranLvgl.polices = {}    # forme de text_font -> police chargee (une seule fois)
ecranLvgl.touchers = []   # [objet LVGL, fonction] des objets tactiles
ecranLvgl.attente = nil   # [fonction, valeur] du dernier toucher, executee hors du rappel LVGL
ecranLvgl.series = nil    # series LVGL de la courbe
ecranLvgl.points = 0      # points du modele deja pousses sur la courbe
ecranLvgl.page = nil      # page affichee

# Police d'un text_font comme lv_haspmota.be::parse_font : entier = robotocondensed embarquee ; "A:<chemin>.ttf-<taille>" =
# FreeType (A: retire : lvbe_fopen ajoute le /) ; "A:<fichier>" = police binaire ; "<nom>-<taille>" = embarquee. nil si absente.
def ecranLvgl_police(f)
    import lv
    import string
    import ecranLvgl
    if (ecranLvgl.polices.contains(f))    return ecranLvgl.polices[f]    end
    var p
    try
        if (type(f) == "int")
            p = lv.font_embedded("robotocondensed", f)
        else
            var m = string.split(f, "-")
            var nom = size(m) >= 2 ? m[0 .. -2].concat("-") : f
            var taille = size(m) >= 2 ? int(m[-1]) : 0
            if (string.endswith(nom, ".ttf", true))
                p = lv.load_freetype_font(string.split(nom, ":")[-1], taille, 0)
            elif (size(string.split(f, ":", 1)) > 1)
                p = lv.load_font(f)
            else
                p = lv.font_embedded(nom, taille)
            end
        end
        if (p == nil)    raise "io_error", "chargement sans police"    end    # .ttf absent de /sd/polices : nil sans exception
    except .. as e, m
        logFonctions.log("ECRAN_LVGL_ERREUR: police " + str(f) + " absente : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    ecranLvgl.polices[f] = p
    return p
end
ecranLvgl.police = ecranLvgl_police
# Label qui porte le texte de `nom` : cree au premier texte, centre sur l'objet (lvh_obj::check_label)
def ecranLvgl_texte(nom)
    import lv
    import ecranLvgl
    var t = ecranLvgl.textes.find(nom)
    if (t == nil)
        t = lv.label(ecranLvgl.objets[nom])
        t.set_align(lv.ALIGN_CENTER)
        ecranLvgl.textes[nom] = t
    end
    return t
end
ecranLvgl.texte = ecranLvgl_texte
# Selecteur partie | etat d'un suffixe a 2 chiffres (lvh_root::digits_to_style : bg_color10 = indicateur)
def ecranLvgl_selecteur(n)
    import lv
    var parties = [lv.PART_MAIN, lv.PART_INDICATOR, lv.PART_KNOB, lv.PART_ITEMS, lv.PART_ITEMS, lv.PART_SELECTED, lv.PART_ITEMS,
                   lv.PART_CURSOR, lv.PART_SCROLLBAR, lv.PART_CUSTOM_FIRST]
    var etats = [lv.STATE_DEFAULT, lv.STATE_CHECKED, lv.STATE_PRESSED, lv.STATE_CHECKED | lv.STATE_PRESSED, lv.STATE_DISABLED,
                 lv.STATE_DISABLED | lv.STATE_PRESSED]
    if (n % 10 >= size(etats))    raise "value_error", "suffixe de style " + str(n) + " invalide"    end
    return parties[n / 10] | etats[n % 10]
end
ecranLvgl.selecteur = ecranLvgl_selecteur
# Applique l'attribut `k` (valeur brute de la description ou du modele) a l'objet `nom`, comme lvh_obj::setmember
def ecranLvgl_applique(nom, k, v)
    import lv
    import string
    import introspect
    import ecranLvgl
    var o = ecranLvgl.objets[nom]
    var t = ecranLvgl.types[nom]
    var c = ecranLvgl.cache.find(nom, {})
    if (k == "text")    var l = t == "dropdown" ? o : ecranLvgl.texte(nom)    l.set_text(str(v))    return    end    # dropdown : texte fixe
    if (k == "align")
        var a = {0: lv.TEXT_ALIGN_LEFT, 1: lv.TEXT_ALIGN_CENTER, 2: lv.TEXT_ALIGN_RIGHT, "left": lv.TEXT_ALIGN_LEFT,
                 "center": lv.TEXT_ALIGN_CENTER, "right": lv.TEXT_ALIGN_RIGHT}
        ecranLvgl.texte(nom).set_style_text_align(a.find(v, lv.TEXT_ALIGN_LEFT), 0)
        return
    end
    if (k == "text_font")
        var p = ecranLvgl.police(v)
        if (p != nil)    o.set_style_text_font(p, 0)    end
        return
    end
    if (k == "val" && t == "switch")    if (v)    o.add_state(lv.STATE_CHECKED)    else    o.remove_state(lv.STATE_CHECKED)    end    return    end
    if (k == "val" && t == "dropdown")    o.set_selected(v)    return    end
    if (k == "val" && t == "roller")    o.set_selected(v, lv.ANIM_OFF)    return    end
    if (k == "val")    if (t == "bar" || t == "slider")    o.set_value(v, lv.ANIM_OFF)    else    o.set_value(v)    end    return    end
    if (k == "options" && t == "roller")    o.set_options(v, lv.ROLLER_MODE_NORMAL)    return    end
    if (k == "src" && v == "tasmota_logo")    o.set_tasmota_logo()    return    end
    if (t == "qrcode" && k == "qr_text")    var q = str(v)    o.update(q, size(q))    return    end    # ecrit en dernier
    if (t == "qrcode" && string.startswith(k, "qr_"))    k = k[3 ..]    end
    if (k == "min")    o.set_range(v, o.get_max_value())    return    end
    if (k == "max")    o.set_range(o.get_min_value(), v)    return    end
    if (k == "y_min" || k == "y_max")
        var mini = k == "y_min" ? v : c.find("y_min", 0)
        o.set_axis_range(lv.CHART_AXIS_PRIMARY_Y, mini, k == "y_max" ? v : c.find("y_max", 100))
        return
    end
    if (k == "h_div_line_count" || k == "v_div_line_count")
        o.set_div_line_count(k == "h_div_line_count" ? v : c.find("h_div_line_count", 3),
                             k == "v_div_line_count" ? v : c.find("v_div_line_count", 5))
        return
    end
    var sel = nil
    if (string.endswith(k, "%"))    k = k[0 .. -2]    v = lv.pct(v)    end
    if (size(k) > 2 && string.find("0123456789", k[-1]) >= 0 && string.find("0123456789", k[-2]) >= 0)
        sel = ecranLvgl.selecteur(int(k[-2 ..]))
        k = k[0 .. -3]
    end
    if (string.endswith(k, "color"))    v = lv.color(v)    end
    var f = sel == nil ? introspect.get(o, "set_" + k) : nil
    if (type(f) == "function")    f(o, v)    return    end
    f = introspect.get(o, "set_style_" + k)
    if (type(f) != "function")    raise "attribute_error", "attribut " + k + " inconnu de " + nom    end
    f(o, v, sel == nil ? 0 : sel)
end
ecranLvgl.applique = ecranLvgl_applique
# Ecrit l'attribut `k` de `nom` seulement s'il a change ; valeur nil ou objet absent : rien
def ecranLvgl_ecris(nom, k, v)
    import ecranLvgl
    if (v == nil || !ecranLvgl.objets.contains(nom))    return    end
    var c = ecranLvgl.cache.find(nom)
    if (c == nil)    c = {}    ecranLvgl.cache[nom] = c    end
    if (c.find(k) == v)    return    end
    ecranLvgl.applique(nom, k, v)
    c[k] = v
end
ecranLvgl.ecris = ecranLvgl_ecris
# Valeur du modele au bout de `chemin` (["a", 0, "b"] = m["a"][0]["b"]) ; nil si un maillon manque
def ecranLvgl_valeur(m, chemin)
    var v = m
    for s: chemin
        if (v == nil)    return nil    end
        v = type(s) == "int" ? (s < size(v) ? v[s] : nil) : v.find(s)
    end
    return v
end
ecranLvgl.valeur = ecranLvgl_valeur
# Page n (PAGES : [n, [[attribut, valeur]]]) : page 0 sur lv.layer_top() transparente, fond (bg_*) sur lv.layer_bottom() ;
# sinon un ecran lv.obj(0) transparent, opaque des qu'il a un bg_color (lvh_page::init, lvh_scr::setmember)
def ecranLvgl_preparePage(p)
    import lv
    import string
    import ecranLvgl
    var n = p[0]
    var nom = "p" + str(n) + "b0"
    var e = n == 0 ? lv.layer_top() : lv.obj(0)
    e.set_style_bg_opa(0, 0)
    if (n == 0)    lv.layer_bottom().set_style_bg_opa(255, 0)    end
    ecranLvgl.ecrans[n] = e
    ecranLvgl.types[nom] = "scr"
    for a: p[1]
        ecranLvgl.objets[nom] = (n == 0 && string.startswith(a[0], "bg_")) ? lv.layer_bottom() : e
        if (n != 0 && a[0] == "bg_color")    e.set_style_bg_opa(255, 0)    end
        ecranLvgl.ecris(nom, a[0], a[1])
    end
    ecranLvgl.objets[nom] = e
end
ecranLvgl.preparePage = ecranLvgl_preparePage
# Objet d (OBJETS) cree sur l'ecran de sa page, place, attributs ecrits par le cache, toucher sur EVENT_CLICKED (VALUE_CHANGED : switch...)
def ecranLvgl_cree(d)
    import lv
    import ecranLvgl
    var nom = "p" + str(d[0]) + "b" + str(d[1])
    var o = lv.(ecranLvgl.CLASSES.find(d[2], d[2]))(ecranLvgl.ecrans[d[0]])
    o.set_pos(d[3], d[4])
    if (d[2] == "qrcode")    o.set_size(d[5])    else    o.set_size(d[5], d[6])    end    # lv_qrcode_set_size : un cote
    ecranLvgl.objets[nom] = o
    ecranLvgl.types[nom] = d[2]
    if (d[2] == "label")    ecranLvgl.textes[nom] = o    end
    if (d[2] == "chart")    o.set_update_mode(lv.CHART_UPDATE_MODE_SHIFT)    end
    for a: d[7]    ecranLvgl.ecris(nom, a[0], a[1])    end
    if (d[8] != nil)
        o.add_event_cb(ecranLvgl.evenement, ["switch", "dropdown", "roller"].find(d[2]) != nil ? lv.EVENT_VALUE_CHANGED : lv.EVENT_CLICKED, 0)
        ecranLvgl.touchers.push([o, d[8], d[2]])
    end
end
ecranLvgl.cree = ecranLvgl_cree
# Series de la courbe (COURBE), sur l'axe primaire, sans pastille de point
def ecranLvgl_prepareCourbe()
    import lv
    import ecranLvgl
    ecranLvgl.series = nil
    ecranLvgl.points = 0
    var c = ecranLvgl.COURBE
    if (c == nil || !ecranLvgl.objets.contains(c[0]))    return    end
    var o = ecranLvgl.objets[c[0]]
    o.set_style_size(0, 0, lv.PART_INDICATOR)
    o.set_style_line_width(3, lv.PART_ITEMS)
    var s = []
    for coul: c[3]    s.push(o.add_series(lv.color(coul), lv.CHART_AXIS_PRIMARY_Y))    end
    ecranLvgl.series = s
end
ecranLvgl.prepareCourbe = ecranLvgl_prepareCourbe
# Pousse sur la courbe les points du modele pas encore traces (tous au premier passage, set_next_value)
def ecranLvgl_trace(m)
    import lv
    import ecranLvgl
    var c = ecranLvgl.COURBE
    var s = ecranLvgl.series
    if (s == nil)    return    end
    var o = ecranLvgl.objets[c[0]]
    var h = ecranLvgl.valeur(m, c[1])
    var p = ecranLvgl.valeur(m, c[2])
    if (p != nil && p < ecranLvgl.points)    ecranLvgl.points = 0    end    # compteur remis a zero par le modele : on repart
    var n = (p == nil ? 0 : p) - ecranLvgl.points
    if (h == nil || size(h) == 0 || n <= 0)    return    end
    var t = size(h[0])
    if (n > t)    n = t    end
    for i: 0 .. size(s) - 1
        if (i >= size(h))    break    end
        for k: t - n .. t - 1
            var v = k < size(h[i]) ? h[i][k] : nil
            o.set_next_value(s[i], v == nil ? lv.CHART_POINT_NONE : v)
        end
    end
    ecranLvgl.points = p
end
ecranLvgl.trace = ecranLvgl_trace
# Boutons qui menent a une page : couleurs `actif` pour la page courante, les autres sinon (par le cache)
def ecranLvgl_actifs()
    import ecranLvgl
    for a: ecranLvgl.ACTIFS
        var i = ecranLvgl.page == a[1] ? 0 : 1
        for k: a[2].keys()    ecranLvgl.ecris(a[0], k, a[2][k][i])    end
    end
end
ecranLvgl.actifs = ecranLvgl_actifs
# Affiche la page n (n >= 1) et met a jour les boutons de page
def ecranLvgl_montre(n)
    import lv
    import ecranLvgl
    var e = ecranLvgl.ecrans.find(n)
    if (e == nil || n == 0)    return    end
    lv.screen_load(e)
    ecranLvgl.page = n
    ecranLvgl.actifs()
end
ecranLvgl.montre = ecranLvgl_montre
# Rappel LVGL d'un objet tactile : son action est differee hors de la boucle LVGL, avec la valeur choisie (interrupteur 1 / 0,
# index d'une liste deroulante ou d'une roue ; nil pour un simple appui)
def ecranLvgl_evenement(obj, event)
    import lv
    import ecranLvgl
    for t: ecranLvgl.touchers
        if (t[0] == obj)
            ecranLvgl.attente = [t[1], t[2] == "switch" ? (obj.has_state(lv.STATE_CHECKED) ? 1 : 0) : (t[2] == "dropdown" || t[2] == "roller") ? obj.get_selected() : nil]
            tasmota.defer(ecranLvgl.execute)
            return
        end
    end
end
ecranLvgl.evenement = ecranLvgl_evenement
# Action du dernier toucher (tasmota.defer) ; echec journalise
def ecranLvgl_execute()
    import ecranLvgl
    var f = ecranLvgl.attente
    ecranLvgl.attente = nil
    if (f == nil)    return    end
    try
        f[0](f[1])          # une fonction sans parametre ignore l'argument
    except .. as e, m
        logFonctions.log("ECRAN_LVGL_ERREUR: action du toucher en echec : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
end
ecranLvgl.execute = ecranLvgl_execute
# Demarre LVGL et cree les pages et les objets de la description ; false (erreur journalisee) si l'ecran n'est pas pret
def ecranLvgl_demarre()
    import lv
    import display
    import ecranLvgl
    try
        if (!display.started())
            logFonctions.log("ECRAN_LVGL_ERREUR: ecran non demarre (display.ini, preinit.be) !", LOG_LEVEL_ERREUR)
            return false
        end
        lv.start()
        ecranLvgl.cache = {}    ecranLvgl.objets = {}    ecranLvgl.types = {}
        ecranLvgl.textes = {}    ecranLvgl.ecrans = {}    ecranLvgl.touchers = []
        for p: ecranLvgl.PAGES    ecranLvgl.preparePage(p)    end
        for d: ecranLvgl.OBJETS    ecranLvgl.cree(d)    end
        ecranLvgl.prepareCourbe()
        ecranLvgl.montre(ecranLvgl.DEPART)
        logFonctions.log("ECRAN_LVGL: " + str(size(ecranLvgl.OBJETS)) + " objets crees sur " + str(size(ecranLvgl.PAGES)) + " pages !", LOG_LEVEL_INFO)
        return true
    except .. as e, m
        logFonctions.log("ECRAN_LVGL_ERREUR: ecran non cree : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
    return false
end
ecranLvgl.demarre = ecranLvgl_demarre
# Ecrit le modele (chaque seconde) : liaisons, couleurs selon une valeur, boutons de page, courbe ; seul ce qui change part
def ecranLvgl_affiche(m)
    import string
    import ecranLvgl
    if (size(ecranLvgl.objets) == 0)    return    end
    for l: ecranLvgl.LIAISONS
        var v = ecranLvgl.valeur(m, l[1])
        if (l[3] != nil || l[4] != nil)
            var c = (v != nil && l[4] != nil) ? l[4].find(v) : nil
            if (c == nil)    c = l[3] != nil ? (v != nil ? ecranLvgl.COULEURS[l[3]].find(v) : nil) : l[5]    end
            v = c
        end
        if (v != nil && l[7] != nil)    v = v / l[7]    end
        if (v != nil && l[6] != nil)    v = string.format(l[6], v)    end
        ecranLvgl.ecris(l[0], l[2], v)
    end
    ecranLvgl.actifs()
    ecranLvgl.trace(m)
end
ecranLvgl.affiche = ecranLvgl_affiche
# Retourne le module lors de l'importation
return ecranLvgl
