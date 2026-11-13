# Banc de l'interface LVGL pur GENEREE par l'atelier des ecrans (ecranLvgl.be, outils_pc/atelier_ecrans_lvgl.py) : objets
# LVGL simules (bouchons_berry/ecran_lvgl/lv.be, chaque appel compte), demarre() puis affiche(modele) chaque seconde.
# Lancer DEPUIS LA RACINE DU DEPOT :
#     lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_ecran_lvgl.be <dossier_vide> [interface] [mini]
# interface : le fichier ecranLvgl.be a tester ("-" = celui de la carte des debits). mini : description quelconque, seuls
# demarre(), les lignes OBJET / TEXTE et les touchers sont faits (pas de modele des debits).
# Sortie : une ligne OBJET <nom> <type> <x> <y> <l> <h> <parent> par objet, TEXTE <nom> <texte> par texte pose, CLIC <nom> <effet>
# par toucher simule, puis les verifications (mode debits) ; derniere ligne BANC_ECRAN_LVGL: OK|ECHEC.
import global
import sys
import string
import os

var SORTIE = global._argv[1]
def argument(i, defaut)    return size(global._argv) > i && global._argv[i] != "-" ? global._argv[i] : defaut    end
var INTERFACE = argument(2, "data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be")
var MINI = size(global._argv) > 3 && global._argv[3] == "mini"

def lis(chemin)
    var f = open(chemin, "r")
    var t = f.read()
    f.close()
    return t
end
def ecris(chemin, texte)
    var f = open(chemin, "w")
    f.write(texte)
    f.close()
end

# ---- Faux firmware --------------------------------------------------------------------------------------------
os.mkdir(SORTIE + "/modules")
ecris(SORTIE + "/modules/ecranLvgl.be", lis(INTERFACE))
ecris(SORTIE + "/modules/ecranDebitsFonctions.be", "import global\nvar d = module('ecranDebitsFonctions')\n" +
      "d.ajuste = def (cle, pas) global.EFFETS.push('AJUSTE ' + str(cle) + ' ' + str(pas)) end\nreturn d\n")
sys.path().push(SORTIE + "/modules")
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/ecran_lvgl")

global.JOURNAL = []
global.EFFETS = []
global.DIFFERES = []
global.LOG_LEVEL_ERREUR = 1
global.LOG_LEVEL_INFO = 2
global.LOG_LEVEL_DEBUG = 3
global.LOG_LEVEL_DEBUG_PLUS = 4
var fauxLog = module("logFonctions")
fauxLog.log = def (m, n, c) global.JOURNAL.push([m, n]) end
fauxLog.actif = def (n, c) return true end
global.logFonctions = fauxLog
var fauxTasmota = module("tasmota")
fauxTasmota.defer = def (f) global.DIFFERES.push(f) end
fauxTasmota.cmd = def (c, muet) global.EFFETS.push("CMD " + c) return {} end
global.tasmota = fauxTasmota

var ok = true
def verifie(nom, cond)
    print((cond ? "  OK    " : "  ECHEC ") + nom)
    if (!cond)    ok = false    end
end
def niveaux(n)
    var k = 0
    for l: global.JOURNAL    if (l[1] == n)    k += 1    end    end
    return k
end

import lv
import display
import ecranLvgl

# ---- Ecran non demarre : false, une erreur journalisee, aucun objet --------------------------------------------
display.demarre = false
verifie("ecran non demarre : demarre() rend false", ecranLvgl.demarre() == false)
verifie("ecran non demarre : une erreur journalisee", niveaux(global.LOG_LEVEL_ERREUR) == 1 && size(lv.objets) == 0)
global.JOURNAL = []
display.demarre = true

# ---- demarre : objets, positions, textes ----------------------------------------------------------------------
verifie("demarre() rend true", ecranLvgl.demarre() == true)
verifie("lv.start() appele", lv.demarre == 1)
verifie("demarre : aucune erreur journalisee", niveaux(global.LOG_LEVEL_ERREUR) == 0)
def parentDe(o)
    for n: ecranLvgl.ecrans.keys()    if (ecranLvgl.ecrans[n] == o.parent)    return "page" + str(n)    end    end
    return "?"
end
for nom: ecranLvgl.objets.keys()
    var o = ecranLvgl.objets[nom]
    if (string.find(nom, "b0") == size(nom) - 2)    continue    end    # reglages de page
    print(string.format("OBJET %s %s %s %s %s %s %s", nom, o.type, str(o.x), str(o.y), str(o.w), str(o.h), parentDe(o)))
end
for nom: ecranLvgl.textes.keys()    print("TEXTE " + nom + " " + str(ecranLvgl.textes[nom].texte))    end

# Simule un appui sur `nom` : rappel LVGL de l'objet, puis fonctions differees par tasmota.defer
def clic(nom)
    var o = ecranLvgl.objets[nom]
    var page = ecranLvgl.page
    global.EFFETS = []
    for r: o.rappels    if (r[1] == lv.EVENT_CLICKED || r[1] == lv.EVENT_VALUE_CHANGED)    r[0](o, nil)    end    end
    var d = global.DIFFERES
    if (size(d) != 1)    global.EFFETS.push("NON_DIFFERE")    end    # l'action part hors du rappel LVGL (tasmota.defer)
    global.DIFFERES = []
    for f: d    f()    end
    if (ecranLvgl.page != page)    global.EFFETS.push("PAGE " + str(ecranLvgl.page))    end
    print("CLIC " + nom + " " + global.EFFETS.concat(" | "))
    return global.EFFETS.concat(" | ")
end

if MINI
    # Appels LVGL des objets nommes (hors styles), dans l'ordre : APPEL <nom> <methode> <arguments> (sauts de ligne
    # ecrits \n) ; puis RAPPEL <nom> <evenement> de chaque objet tactile
    def nomDe(o)    for n: ecranLvgl.objets.keys()    if (ecranLvgl.objets[n] == o)    return n    end    end    return nil    end
    for j: lv.journal
        var n = nomDe(j[0])
        if (n != nil && !string.startswith(j[1], "set_style_"))    print("APPEL " + n + " " + j[1] + " " + string.replace(str(j[2]), "\n", "\\n"))    end
    end
    for t: ecranLvgl.touchers    for r: t[0].rappels    print("RAPPEL " + nomDe(t[0]) + " " + str(r[1]))    end    end
    for t: ecranLvgl.touchers
        for nom: ecranLvgl.objets.keys()    if (ecranLvgl.objets[nom] == t[0])    clic(nom)    end    end
    end
    print("BANC_ECRAN_LVGL: " + (ok ? "OK" : "ECHEC"))
    return
end

# ---- Mode debits ----------------------------------------------------------------------------------------------
var O = ecranLvgl.objets
var E = ecranLvgl.ecrans
verifie("5 pages (4 : Systeme, construite), page 0 sur lv.layer_top()", size(E) == 5 && E[0] == lv.layer_top())
verifie("page de demarrage = page 1 chargee", ecranLvgl.page == 1 && lv.ecran == E[1])
verifie("page 1 : fond #10161E opaque", E[1].style("bg_color") == 0x10161E && E[1].style("bg_opa") == 255)
verifie("page 0 transparente", E[0].style("bg_opa") == 0)
verifie("182 objets crees (82 + bouton 204 + 99 de la page Systeme)", size(O) - 5 == 182)
verifie("bouton : texte dans un label enfant centre", ecranLvgl.textes["p0b201"].parent == O["p0b201"] &&
        ecranLvgl.textes["p0b201"].texte == "Débits" && ecranLvgl.textes["p0b201"].aligne == lv.ALIGN_CENTER)
verifie("label : texte sur l'objet lui-meme", ecranLvgl.textes["p1b11"] == O["p1b11"])
verifie("police TTF : A: retire, sans / de tete", O["p0b1"].style("text_font") == "ttf:sd/polices/RobotoCondensed-Regular.ttf-32")
verifie("police entiere : robotocondensed embarquee", O["p2b12"].style("text_font") == "embarquee:robotocondensed-24")
var ttf = 0  var emb = 0
for p: lv.polices    if (p[0] == "load_freetype_font")    ttf += 1    else    emb += 1    end    end
verifie("chaque police chargee une seule fois (5 TTF, 2 embarquees)", ttf == 5 && emb == 2)
verifie("align 2 : texte a droite", O["p0b4"].style("text_align") == lv.TEXT_ALIGN_RIGHT)
verifie("barre : plage 0-100 puis valeur", O["p1b12"].mini == 0 && O["p1b12"].maxi == 100 && O["p1b12"].valeur == 0)
verifie("barre : rayon de l'indicateur (radius10)", O["p1b12"].style("radius", lv.PART_INDICATOR) == 13)
verifie("courbe : 60 points, divisions 5/0, mode decalage", O["p2b70"].nbPoints == 60 && O["p2b70"].div[0] == 5 &&
        O["p2b70"].div[1] == 0 && O["p2b70"].mode == lv.CHART_UPDATE_MODE_SHIFT)
var couleurs = []
for s: O["p2b70"].series    couleurs.push(s[0])    if (s[1] != lv.CHART_AXIS_PRIMARY_Y)    couleurs.push("axe")    end    end
verifie("courbe : 6 series sur l'axe primaire", couleurs == [0x3FA7FF, 0x3FD08A, 0xFFA53F, 0xC084FC, 0xFF5A5A, 0xF5D04A])
verifie("courbe : pas de pastille de point", O["p2b70"].style("size", lv.PART_INDICATOR) == 0)
verifie("boutons tactiles : 12 rappels sur EVENT_CLICKED (204, 120, 121 compris)", size(ecranLvgl.touchers) == 12)

def voie(nom, etat, barre)    return {"nom": nom, "debit": "4,20", "unite": "L/min", "part": "23 %", "barre": barre, "etat": etat}    end
def historique(n)
    var h = []
    for i: 0 .. 5
        var l = []
        for k: 0 .. 59    l.push(k >= 60 - n && !(i == 4 && k == 59) ? 100 * i + k : nil)    end    # voie 5 : dernier point inconnu
        h.push(l)
    end
    return h
end
def modele()
    return {"voies": [voie("Aller", "imprecis", 62), voie("Retour", "normal", 40), voie("V3", "muet", 0), voie("V4", "arret", 0),
                      voie("V5", "inconnu", 0), voie("V6", "normal", 100)],
            "total": "Total 17,9 L/min", "age": 4, "releve": "relevé il y a 4 s", "liaison": "vert",
            "historique": historique(3), "points": 3, "courbeMax": 1000,
            "reglages": {"fenetre": "10 s", "veille": "5 min", "luminosite": "80 %"}}
end

global.JOURNAL = []
var m = modele()
ecranLvgl.affiche(m)
verifie("affiche : aucun log info, aucune erreur", niveaux(global.LOG_LEVEL_INFO) == 0 && niveaux(global.LOG_LEVEL_ERREUR) == 0)
verifie("texte lie (total)", O["p0b4"].texte == "Total 17,9 L/min")
verifie("pastille : nom de la table des couleurs", O["p0b2"].style("bg_color") == 0x3FD08A)
verifie("voie imprecise : barre orange (indicateur)", O["p1b12"].style("bg_color", lv.PART_INDICATOR) == 0xFFA53F)
verifie("voie imprecise : nom et debit orange", O["p1b11"].style("text_color") == 0xFFA53F && O["p1b13"].style("text_color") == 0xFFA53F)
verifie("voie normale : barre bleue, nom clair", O["p1b22"].style("bg_color", lv.PART_INDICATOR) == 0x3FA7FF && O["p1b21"].style("text_color") == 0xE8EDF2)
verifie("voie muette : nom rouge", O["p1b31"].style("text_color") == 0xFF5A5A)
verifie("voie a l'arret : nom clair (sauf), debit gris", O["p1b41"].style("text_color") == 0xE8EDF2 && O["p1b43"].style("text_color") == 0x9FB3C8)
verifie("barre liee", O["p1b12"].valeur == 62 && O["p1b62"].valeur == 100)
verifie("page Courbes : nom de la voie 2", O["p2b22"].texte == "Retour")
verifie("reglages lies", O["p3b23"].texte == "10 s" && O["p3b33"].texte == "5 min" && O["p3b43"].texte == "80 %")
verifie("bouton de la page courante en bleu", O["p0b201"].style("bg_color") == 0x3FA7FF && O["p0b201"].style("text_color") == 0x06121F &&
        O["p0b202"].style("bg_color") == 0x1F2B38 && O["p0b202"].style("text_color") == 0xE8EDF2)
verifie("courbe : point inconnu pousse en CHART_POINT_NONE", O["p2b70"].points[4][-1] == lv.CHART_POINT_NONE)
verifie("courbe : 3 points connus x 6 series pousses", size(O["p2b70"].points[0]) == 3 && O["p2b70"].points[5] == [557, 558, 559])
verifie("courbe : axe 0-1000, haut de l'axe en L/min", O["p2b70"].axe == [lv.CHART_AXIS_PRIMARY_Y, 0, 1000] && O["p2b71"].texte == "10 L/min")

var avant = lv.appels
ecranLvgl.affiche(modele())
verifie("deux affiche() identiques : aucun appel au second", lv.appels == avant)
m = modele()
m["total"] = "Total 9,9 L/min"
ecranLvgl.affiche(m)
var dernier = lv.journal[-1]
verifie("une valeur changee : un seul appel", lv.appels == avant + 1 && dernier[0] == O["p0b4"] && dernier[1] == "set_text" &&
        dernier[2] == ["Total 9,9 L/min"])
m["points"] = 4
m["historique"] = historique(4)
m["courbeMax"] = 1200
avant = lv.appels
ecranLvgl.affiche(m)
verifie("un point de plus : un point par serie, axe et texte suivis", size(O["p2b70"].points[0]) == 4 &&
        O["p2b70"].axe == [lv.CHART_AXIS_PRIMARY_Y, 0, 1200] && O["p2b71"].texte == "12 L/min" && lv.appels == avant + 8)
m["voies"][0]["etat"] = "normal"
ecranLvgl.affiche(m)
verifie("voie redevenue normale : barre bleue", O["p1b12"].style("bg_color", lv.PART_INDICATOR) == 0x3FA7FF)

# ---- Touchers ---------------------------------------------------------------------------------------------------
verifie("bouton Courbes : page 2 chargee", clic("p0b202") == "PAGE 2" && lv.ecran == E[2])
verifie("bouton Courbes en bleu, Debits eteint", O["p0b202"].style("bg_color") == 0x3FA7FF && O["p0b201"].style("bg_color") == 0x1F2B38)
verifie("bouton + fenetre : ajuste(fenetre, 1)", clic("p3b24") == "AJUSTE fenetre 1")
verifie("bouton - luminosite : ajuste(luminosite, -10)", clic("p3b42") == "AJUSTE luminosite -10")
avant = lv.appels
ecranLvgl.affiche(m)
verifie("apres le changement de page : rien a reecrire", lv.appels == avant)
verifie("touchers : aucune erreur", niveaux(global.LOG_LEVEL_ERREUR) == 0)

# ---- Compteur de points remis a zero par le modele, police absente sans exception ----------------------------------
var n0 = size(O["p2b70"].points[0])
m["points"] = 2
m["historique"] = historique(2)
ecranLvgl.affiche(m)
verifie("compteur de points remis a zero : la courbe repart (2 points par serie)", size(O["p2b70"].points[0]) == n0 + 2)
var chargeTtf = lv.load_freetype_font
lv.load_freetype_font = def (nom, t, s) return nil end            # .ttf absent de /sd/polices : nil, pas d'exception
verifie("police .ttf absente (nil sans exception) : une erreur journalisee",
        ecranLvgl.police("A:sd/polices/Absente.ttf-20") == nil && niveaux(global.LOG_LEVEL_ERREUR) == 1)
lv.load_freetype_font = chargeTtf

print("BANC_ECRAN_LVGL: " + (ok ? "OK" : "ECHEC"))
