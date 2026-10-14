# -*- coding: utf-8 -*-
"""Bibliotheque Modules_Tasmota : empreintes + modeles 3D STEP des modules du commerce
enfiches sur les cartes porteuses (DevKitC-1, ADS1115, RS485 auto).

Python pur (pas besoin de pcbnew) :
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" generer_modules.py

Produit a cote de ce script :
  Modules_Tasmota.pretty/<nom>.kicad_mod    empreinte (pastilles = barrette FEMELLE soudee
                                            sur la porteuse, origine = broche 1)
  Modules_Tasmota.3dshapes/<nom>.step       modele 3D (boites : barrettes, circuit, composants)

Les modeles sont references par `${PCB_TASMOTA_3D}/<nom>.step` : le projet de carte
definit cette variable (voir pieges_kicad.md). Reporter ici les mesures au pied a coulisse
puis relancer : chaque cote est un couple (valeur en mm, etat). Tant qu'un etat contient
« à mesurer », l'empreinte porte un avertissement sur Cmts.User.
"""
import math
import uuid
from pathlib import Path

ICI = Path(__file__).resolve().parent
BIBLIO = ICI / "Modules_Tasmota.pretty"
MODELES = ICI / "Modules_Tasmota.3dshapes"
VAR_3D = "${PCB_TASMOTA_3D}"
AM = "à mesurer"
ESP = "plan Espressif DXF_ESP32-S3-DevKitC-1_V1.1_20220429"

# ============================== COTES (mm) ===================================
# Hauteurs communes de l'empilement (porteuse -> module)
EMPILEMENT = {
    "barrette_femelle": (8.5, "norme PinSocket 2,54 (modele KiCad) - " + AM),
    "entretoise_male": (2.5, "plastique de barrette male standard - " + AM),
    "queue_broche": (3.0, "sous la porteuse, modele KiCad - " + AM),
}

# ESP32-S3-DevKitC-1 (WeAct, 2 x 22 broches). Repere : origine = broche J1-1 (3V3),
# antenne vers le haut (-y), J1 a gauche (x = 0), J3 a droite (x = entraxe).
DEVKIT = {
    "marge_laterale": (1.27, ESP + " (axe broche -> bord long) - " + AM + " sur la WeAct"),
    "bord_antenne": (1.565, ESP + " (axe broche 1 -> bord cote antenne) - " + AM),
    "bord_usb": (7.96, ESP + " (axe broche 22 -> bord cote USB) - " + AM),
    "epaisseur_pcb": (1.6, "valeur usuelle - " + AM),
    "debord_antenne": (6.3, ESP + " (module WROOM-1 au-dela du bord) - " + AM),
    "module_l": (18.0, "datasheet ESP32-S3-WROOM-1 (18 x 25,5 x 3,1)"),
    "module_h": (25.5, "datasheet ESP32-S3-WROOM-1"),
    "module_ep": (3.1, "datasheet ESP32-S3-WROOM-1"),
    "usb_entraxe": (13.2, ESP + " (2 prises symetriques) - " + AM),
    "usb_l": (8.94, "prise USB-C usuelle - " + AM),
    "usb_p": (7.35, "prise USB-C usuelle - " + AM),
    "usb_h": (3.2, "prise USB-C usuelle - " + AM),
    "usb_debord": (0.5, AM),
}
# Les deux variantes d'entraxe des rangees (piege : la bibliotheque Espressif et son plan
# disent 22,86 ; un utilisateur KiCad a mesure 25,4 sur sa carte, comme les clones a 28 mm).
ENTRAXES = {"22.86": (22.86, ESP + " - " + AM), "25.40": (25.40, "forum KiCad 71001, clones - " + AM)}

# Module ADS1115 bleu, 10 broches en ligne. Repere : origine = broche 1 (VDD),
# broches vers +x, carte au-dessus (-y), barrette le long du bord bas.
ADS = {
    "longueur": (28.0, "annonces courantes (Adafruit 28 x 17,8) - " + AM),
    "largeur": (17.0, "annonces courantes - " + AM),
    "marge_broches": (1.27, AM + " (axe broches -> bord le plus proche)"),
    "epaisseur_pcb": (1.6, AM),
    "puce": (3.0, "MSOP-10 3 x 3 x 1,1 (datasheet TI ADS1115)"),
}
BROCHES_ADS = ["VDD", "GND", "SCL", "SDA", "ADDR", "ALRT", "A0", "A1", "A2", "A3"]

# Module RS485 a direction automatique, modele suppose XY-017 / HW-0519 (MAX485 + CD4069,
# 3,3-5 V, 42,6 x 15,3 mm, PCB 0,8 mm, demi-trous au pas 2,54). Repere : origine = broche 1
# (VCC), broches vers +y, carte vers la droite (+x), bornier A/B au bout droit.
RS485 = {
    "longueur": (42.6, "annonce electronilab XY-017 HW-0519 - " + AM),
    "largeur": (15.3, "annonce electronilab XY-017 HW-0519 - " + AM),
    "marge_broches": (1.27, AM + " (axe broches -> petit bord)"),
    "epaisseur_pcb": (0.8, "annonces XY-017 (demi-trous, 0,8 mm) - " + AM),
    "bornier_pas": (5.08, "bornier a vis usuel - " + AM),
    "bornier_nb": (3, "suppose A+ B- GND - " + AM),
    "bornier_p": (7.6, AM), "bornier_h": (10.0, AM),
}
BROCHES_RS485 = ["VCC", "TXD", "RXD", "GND"]

J1 = ["3V3", "3V3", "RST", "IO4", "IO5", "IO6", "IO7", "IO15", "IO16", "IO17", "IO18",
      "IO8", "IO3", "IO46", "IO9", "IO10", "IO11", "IO12", "IO13", "IO14", "5V", "GND"]
J3 = ["GND", "TX", "RX", "IO1", "IO2", "IO42", "IO41", "IO40", "IO39", "IO38", "IO37",
      "IO36", "IO35", "IO0", "IO45", "IO48", "IO47", "IO21", "IO20", "IO19", "GND", "GND"]
PAS = 2.54
NOIR, OR_, BLEU, ARGENT = (0.1, 0.1, 0.12), (0.85, 0.7, 0.25), (0.1, 0.25, 0.65), (0.75, 0.75, 0.78)
VERT, ROUGE_PCB = (0.1, 0.45, 0.25), (0.15, 0.15, 0.6)


def v(cotes, cle):
    return cotes[cle][0]


def a_mesurer(*dicts):
    return sorted(k for d in dicts for k, (_, etat) in d.items() if AM in etat)


# ============================== STEP AP214 ====================================
class Step:
    """Ecrit un STEP AP214 de parallelepipedes colores (B-rep exact, une piece)."""

    def __init__(self, nom):
        self.nom, self.lignes, self.n = nom, [], 0
        self.solides = []          # (id brep, couleur)

    def e(self, txt):
        self.n += 1
        self.lignes.append(f"#{self.n}={txt};")
        return f"#{self.n}"

    def pt(self, p):
        return self.e("CARTESIAN_POINT('',(%s))" % ",".join(f"{c:.4f}" for c in p))

    def dir(self, d):
        return self.e("DIRECTION('',(%s))" % ",".join(f"{c:.6f}" for c in d))

    def boite(self, x0, y0, z0, x1, y1, z1, couleur):
        """Boite en coordonnees EMPREINTE (y vers le bas) ; le STEP a y vers le haut."""
        xa, xb = sorted((x0, x1)); ya, yb = sorted((-y0, -y1)); za, zb = sorted((z0, z1))
        P = [((xb if i & 1 else xa), (yb if i & 2 else ya), (zb if i & 4 else za)) for i in range(8)]
        vx = [self.e(f"VERTEX_POINT('',{self.pt(p)})") for p in P]
        aretes = {}

        def arete(a, b):
            k = (min(a, b), max(a, b))
            if k not in aretes:
                d = [P[k[1]][i] - P[k[0]][i] for i in range(3)]
                lg = math.sqrt(sum(c * c for c in d))
                vec = self.e(f"VECTOR('',{self.dir([c / lg for c in d])},{lg:.4f})")
                ligne = self.e(f"LINE('',{self.pt(P[k[0]])},{vec})")
                aretes[k] = self.e(f"EDGE_CURVE('',{vx[k[0]]},{vx[k[1]]},{ligne},.T.)")
            return self.e(f"ORIENTED_EDGE('',*,*,{aretes[k]},{'.T.' if a < b else '.F.'})")

        faces = []
        for boucle, n in (((0, 2, 3, 1), (0, 0, -1)), ((4, 5, 7, 6), (0, 0, 1)),
                          ((0, 4, 6, 2), (-1, 0, 0)), ((1, 3, 7, 5), (1, 0, 0)),
                          ((0, 1, 5, 4), (0, -1, 0)), ((2, 6, 7, 3), (0, 1, 0))):
            oe = [arete(boucle[i], boucle[(i + 1) % 4]) for i in range(4)]
            loop = self.e("EDGE_LOOP('',(%s))" % ",".join(oe))
            bound = self.e(f"FACE_OUTER_BOUND('',{loop},.T.)")
            a, b = P[boucle[0]], P[boucle[1]]
            ref = [b[i] - a[i] for i in range(3)]
            lg = math.sqrt(sum(c * c for c in ref))
            ax = self.e(f"AXIS2_PLACEMENT_3D('',{self.pt(a)},{self.dir(n)},"
                        f"{self.dir([c / lg for c in ref])})")
            plan = self.e(f"PLANE('',{ax})")
            faces.append(self.e(f"ADVANCED_FACE('',({bound}),{plan},.T.)"))
        coque = self.e("CLOSED_SHELL('',(%s))" % ",".join(faces))
        self.solides.append((self.e(f"MANIFOLD_SOLID_BREP('',{coque})"), couleur))

    def ecrit(self, chemin):
        lignes, self.lignes = self.lignes, []
        e = self.e
        ctx = e("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
        e(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,{ctx})")
        pc = e(f"PRODUCT_CONTEXT('',{ctx},'mechanical')")
        prod = e(f"PRODUCT('{self.nom}','{self.nom}','',({pc}))")
        e(f"PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,({prod}))")
        pdf = e(f"PRODUCT_DEFINITION_FORMATION('','',{prod})")
        pdc = e(f"PRODUCT_DEFINITION_CONTEXT('part definition',{ctx},'design')")
        pd = e(f"PRODUCT_DEFINITION('design','',{pdf},{pdc})")
        pds = e(f"PRODUCT_DEFINITION_SHAPE('','',{pd})")
        lu = e("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.))")
        au = e("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
        su = e("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT())")
        inc = e(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),{lu},'distance_accuracy_value','')")
        rc = e(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({inc}))"
               f"GLOBAL_UNIT_ASSIGNED_CONTEXT(({lu},{au},{su}))REPRESENTATION_CONTEXT('',''))")
        orig = e(f"AXIS2_PLACEMENT_3D('',{self.pt((0, 0, 0))},{self.dir((0, 0, 1))},{self.dir((1, 0, 0))})")
        rep = e("ADVANCED_BREP_SHAPE_REPRESENTATION('%s',(%s),%s)"
                % (self.nom, ",".join([orig] + [s for s, _ in self.solides]), rc))
        e(f"SHAPE_DEFINITION_REPRESENTATION({pds},{rep})")
        styles = []
        for s, (r, g, b) in self.solides:
            c = e(f"COLOUR_RGB('',{r},{g},{b})")
            fa = e(f"FILL_AREA_STYLE('',({e(f'FILL_AREA_STYLE_COLOUR({chr(39) * 2},{c})')}))")
            sss = e(f"SURFACE_SIDE_STYLE('',({e(f'SURFACE_STYLE_FILL_AREA({fa})')}))")
            psa = e(f"PRESENTATION_STYLE_ASSIGNMENT(({e(f'SURFACE_STYLE_USAGE(.BOTH.,{sss})')}))")
            styles.append(e(f"STYLED_ITEM('',({psa}),{s})"))
        e("MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',(%s),%s)" % (",".join(styles), rc))
        corps = lignes + self.lignes
        tete = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Modules_Tasmota'),'2;1');\n"
                f"FILE_NAME('{self.nom}.step','2026-10-12T00:00:00',(''),(''),'generer_modules.py',"
                "'generer_modules.py','');\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\n"
                "ENDSEC;\nDATA;\n")
        Path(chemin).write_text(tete + "\n".join(corps) + "\nENDSEC;\nEND-ISO-10303-21;\n", encoding="ascii")


# ============================== EMPREINTE .kicad_mod ===========================
class Empreinte:
    def __init__(self, nom, descr, tags):
        self.nom, self.items, self.k = nom, [], 0
        self.tete = (f'(footprint "{nom}"\n\t(version 20260206)\n\t(generator "generer_modules.py")\n'
                     f'\t(layer "F.Cu")\n\t(descr "{descr}")\n\t(tags "{tags}")\n')

    def u(self):
        self.k += 1
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"Modules_Tasmota/{self.nom}/{self.k}"))

    def ligne(self, x0, y0, x1, y1, couche, larg=0.12, style="solid"):
        self.items.append(f'\t(fp_line (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width {larg}) '
                          f'(type {style})) (layer "{couche}") (uuid "{self.u()}"))')

    def rect(self, x0, y0, x1, y1, couche, larg=0.12, style="solid"):
        for a, b, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            self.ligne(a, b, c, d, couche, larg, style)

    def texte(self, txt, x, y, couche, taille=1.0, ep=0.15, justif="", rot=0):
        j = f" (justify {justif})" if justif else ""
        self.items.append(f'\t(fp_text user "{txt}" (at {x:.3f} {y:.3f} {rot}) (layer "{couche}") (uuid "{self.u()}") '
                          f'(effects (font (size {taille} {taille}) (thickness {ep})){j}))')

    def pastille(self, num, x, y):
        forme = "rect" if num == "1" else "circle"
        self.items.append(f'\t(pad "{num}" thru_hole {forme} (at {x:.3f} {y:.3f}) (size 1.7 1.7) (drill 1) '
                          f'(layers "*.Cu" "*.Mask") (remove_unused_layers no) (uuid "{self.u()}"))')

    def interdiction(self, x0, y0, x1, y1, nom="antenne"):
        self.items.append(
            f'\t(zone (layers "F.Cu" "B.Cu") (uuid "{self.u()}") (name "{nom}") (hatch full 0.508) '
            f'(connect_pads (clearance 0)) (min_thickness 0.254) (keepout (tracks not_allowed) '
            f'(vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) '
            f'(placement (enabled no) (sheetname "")) (fill (thermal_gap 0.508) (thermal_bridge_width 0.508) '
            f'(island_removal_mode 0)) (polygon (pts (xy {x0:.3f} {y0:.3f}) (xy {x1:.3f} {y0:.3f}) '
            f'(xy {x1:.3f} {y1:.3f}) (xy {x0:.3f} {y1:.3f}))))')

    def ecrit(self, ref_xy, val_xy, attention):
        if attention:
            x, y = val_xy
            lignes = ["À MESURER (generer_modules.py) :"] + [", ".join(attention[i:i + 4])
                                                          for i in range(0, len(attention), 4)]
            # "\\n" ecrit tel quel : KiCad le lit comme saut de ligne (un vrai \n casse le fichier)
            self.texte("\\n".join(lignes), x, y + 1.2 + 0.6 * len(lignes), "Cmts.User", 0.8, 0.12)
        props = (f'\t(property "Reference" "REF**" (at {ref_xy[0]:.3f} {ref_xy[1]:.3f} 0) (layer "F.SilkS") '
                 f'(uuid "{self.u()}") (effects (font (size 1 1) (thickness 0.15))))\n'
                 f'\t(property "Value" "{self.nom}" (at {val_xy[0]:.3f} {val_xy[1]:.3f} 0) (layer "F.Fab") '
                 f'(uuid "{self.u()}") (effects (font (size 1 1) (thickness 0.15))))\n\t(attr through_hole)\n')
        modele = (f'\t(embedded_fonts no)\n\t(model "{VAR_3D}/{self.nom}.step" (offset (xyz 0 0 0)) '
                  f'(scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n)\n')
        (BIBLIO / f"{self.nom}.kicad_mod").write_text(self.tete + props + "\n".join(self.items) + "\n" + modele,
                                                       encoding="utf-8")


def contour(fp, x0, y0, x1, y1, debords=()):
    """Corps (F.Fab), contour serigraphie decale de 0,11 mm, courtyard du tout + 0,25 mm."""
    fp.rect(x0, y0, x1, y1, "F.Fab", 0.1)
    fp.rect(x0 - 0.11, y0 - 0.11, x1 + 0.11, y1 + 0.11, "F.SilkS")
    xs = [x0, x1] + [d[0] for d in debords] + [d[2] for d in debords]
    ys = [y0, y1] + [d[1] for d in debords] + [d[3] for d in debords]
    c = [round(f, 2) for f in (min(xs) - 0.25, min(ys) - 0.25, max(xs) + 0.25, max(ys) + 0.25)]
    fp.rect(*c, "F.CrtYd", 0.05)
    fp.texte("${REFERENCE}", (x0 + x1) / 2, (y0 + y1) / 2, "F.Fab", 1.0, 0.15)


def repere_broche1(fp, x, y, vers):
    """Triangle de serigraphie pointant vers la broche 1, pose a l'exterieur du contour."""
    dx, dy = vers
    px, py = -dy, dx
    b = (x - 1.0 * dx, y - 1.0 * dy)
    pts = [(x, y), (b[0] + 0.5 * px, b[1] + 0.5 * py), (b[0] - 0.5 * px, b[1] - 0.5 * py)]
    for i in range(3):
        fp.ligne(*pts[i], *pts[(i + 1) % 3], "F.SilkS")


def barrettes(st, broches, z_pcb):
    """Barrette femelle (porteuse) + entretoise de la barrette male (module) + queues."""
    hf, hm, q = (v(EMPILEMENT, k) for k in ("barrette_femelle", "entretoise_male", "queue_broche"))
    for rangee in broches:
        xs = [p[0] for p in rangee]; ys = [p[1] for p in rangee]
        st.boite(min(xs) - 1.27, min(ys) - 1.27, 0, max(xs) + 1.27, max(ys) + 1.27, hf, NOIR)
        st.boite(min(xs) - 1.27, min(ys) - 1.27, hf, max(xs) + 1.27, max(ys) + 1.27, z_pcb, NOIR)
        for x, y in rangee:
            st.boite(x - 0.32, y - 0.32, -q, x + 0.32, y + 0.32, 0, OR_)


def z_module():
    return v(EMPILEMENT, "barrette_femelle") + v(EMPILEMENT, "entretoise_male")


# ============================== LES MODULES ====================================
def devkit(cle):
    entraxe = ENTRAXES[cle][0]
    nom = f"ESP32-S3-DevKitC-1_E{cle}mm"
    d = {k: v(DEVKIT, k) for k in DEVKIT}
    fp = Empreinte(nom, f"ESP32-S3-DevKitC-1 (WeAct) enfiche sur 2 barrettes femelles 1x22, entraxe {entraxe} mm. "
                        "Pastilles 1-22 = J1 (3V3..GND), 23-44 = J3 (GND..GND) : symbole Conn_02x22_Top_Bottom",
                   "ESP32-S3 DevKitC-1 WeAct barrette femelle module Tasmota")
    n = len(J1)
    rangees = [[(0.0, k * PAS) for k in range(n)], [(entraxe, k * PAS) for k in range(n)]]
    for i, (x, y) in enumerate(rangees[0] + rangees[1]):
        fp.pastille(str(i + 1), x, y)
    for k in range(n):                       # noms des broches (F.Fab), cote interieur
        fp.texte(J1[k], 1.2, k * PAS, "F.Fab", 0.6, 0.1, "left")
        fp.texte(J3[k], entraxe - 1.2, k * PAS, "F.Fab", 0.6, 0.1, "right")
    m = d["marge_laterale"]
    x0, x1 = -m, entraxe + m
    y0, y1 = -d["bord_antenne"], (n - 1) * PAS + d["bord_usb"]
    xc = entraxe / 2
    ant = (xc - d["module_l"] / 2, y0 - d["debord_antenne"], xc + d["module_l"] / 2, y0)
    usbs = [(xc + s * d["usb_entraxe"] / 2 - d["usb_l"] / 2, y1 + d["usb_debord"] - d["usb_p"],
             xc + s * d["usb_entraxe"] / 2 + d["usb_l"] / 2, y1 + d["usb_debord"]) for s in (-1, 1)]
    contour(fp, x0, y0, x1, y1, [ant] + usbs)
    fp.rect(*ant, "F.Fab", 0.1, "dash")        # F.Fab : l'antenne deborde souvent de la porteuse
    fp.texte("ANTENNE", xc, ant[1] + d["debord_antenne"] / 2, "F.Fab", 0.8, 0.12)
    fp.interdiction(*ant)
    for u in usbs:
        fp.rect(*u, "F.Fab", 0.1)
    fp.texte("USB", xc, y1 - 1.5, "F.Fab", 0.8, 0.12)
    repere_broche1(fp, x0 - 0.4, 0.0, (1, 0))
    fp.texte("J1", -m - 1.3, 2 * PAS, "F.SilkS", 1.0, 0.15)
    fp.texte("J3", entraxe + m + 1.3, 2 * PAS, "F.SilkS", 1.0, 0.15)
    fp.ecrit((xc, ant[1] - 1.2), (xc, y1 + 1.5), a_mesurer(DEVKIT, EMPILEMENT, {"entraxe": ENTRAXES[cle]}))

    st = Step(nom)
    zb = z_module(); zt = zb + d["epaisseur_pcb"]
    barrettes(st, rangees, zb)
    st.boite(x0, y0, zb, x1, y1, zt, NOIR)                                  # circuit du DevKit
    mod = (xc - d["module_l"] / 2, ant[1], xc + d["module_l"] / 2, ant[1] + d["module_h"])
    st.boite(*mod[:2], zt, *mod[2:], zt + 0.8, BLEU)                          # circuit du WROOM-1
    st.boite(mod[0] + 0.8, ant[3] + 0.5, zt + 0.8, mod[2] - 0.8, mod[3] - 0.5,
             zt + d["module_ep"], ARGENT)                                     # capot blinde
    for u in usbs:
        st.boite(u[0], u[1], zt, u[2], u[3], zt + d["usb_h"], ARGENT)
    st.ecrit(MODELES / f"{nom}.step")
    return nom


def module_en_ligne(nom, descr, tags, cotes, broches, sens, corps, haut, couleur_pcb):
    """Module a une seule rangee : `sens` (1,0) = broches vers +x, (0,1) = vers +y.
    `corps` = (x0, y0, x1, y1) en coordonnees empreinte ; `haut` = boites posees sur le circuit
    [(x0, y0, x1, y1, hauteur, couleur)]."""
    fp = Empreinte(nom, descr, tags)
    pts = [(k * PAS * sens[0], k * PAS * sens[1]) for k in range(len(broches))]
    for i, (x, y) in enumerate(pts):
        fp.pastille(str(i + 1), x, y)
        if sens == (1, 0):
            fp.texte(broches[i], x, y - 1.4, "F.Fab", 0.6, 0.1, rot=90, justif="left")
        else:
            fp.texte(broches[i], x + 1.4, y, "F.Fab", 0.6, 0.1, "left")
    debords = [(h[0], h[1], h[2], h[3]) for h in haut]
    contour(fp, *corps, debords)
    if sens == (1, 0):
        repere_broche1(fp, corps[0] - 0.4, 0.0, (1, 0))
    else:
        repere_broche1(fp, 0.0, corps[1] - 0.4, (0, 1))
    xc = (corps[0] + corps[2]) / 2
    fp.ecrit((xc, corps[1] - 1.2), (xc, corps[3] + 1.5), a_mesurer(cotes, EMPILEMENT))
    st = Step(nom)
    zb = z_module(); zt = zb + v(cotes, "epaisseur_pcb")
    barrettes(st, [pts], zb)
    st.boite(*corps[:2], zb, *corps[2:], zt, couleur_pcb)
    for x0, y0, x1, y1, h, coul in haut:
        st.boite(x0, y0, zt, x1, y1, zt + h, coul)
    st.ecrit(MODELES / f"{nom}.step")
    return fp


def ads1115():
    nom = "Module_ADS1115_1x10"
    L, W, m, c = (v(ADS, k) for k in ("longueur", "largeur", "marge_broches", "puce"))
    xm = (len(BROCHES_ADS) - 1) * PAS / 2
    corps = (xm - L / 2, m - W, xm + L / 2, m)
    yc = (corps[1] + corps[3]) / 2
    module_en_ligne(nom, "Module ADS1115 bleu (10 broches VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3) "
                         "enfiche sur barrette femelle 1x10", "ADS1115 I2C CAN module Tasmota",
                    ADS, BROCHES_ADS, (1, 0), corps, [(xm - c / 2, yc - c / 2, xm + c / 2, yc + c / 2, 1.1, NOIR)],
                    BLEU)
    return nom


def rs485():
    nom = "Module_RS485_Auto_XY-017"
    L, W, m = (v(RS485, k) for k in ("longueur", "largeur", "marge_broches"))
    pas_b, nb, pb, hb = (v(RS485, k) for k in ("bornier_pas", "bornier_nb", "bornier_p", "bornier_h"))
    ym = (len(BROCHES_RS485) - 1) * PAS / 2
    corps = (-m, ym - W / 2, -m + L, ym + W / 2)
    xd = corps[2]
    haut = [(xd - pb, ym - nb * pas_b / 2, xd + 0.5, ym + nb * pas_b / 2, hb, VERT),       # bornier A B
            (xd / 2 - 3.0, ym - 2.5, xd / 2 + 3.0, ym + 2.5, 1.75, NOIR)]               # MAX485 (SOP-8)
    module_en_ligne(nom, "Module TTL-RS485 a direction automatique XY-017 / HW-0519 (VCC TXD RXD GND ; "
                         "bornier A B cote bus) enfiche sur barrette femelle 1x04", "RS485 MAX485 XY-017 HW-0519 "
                         "automatique module Tasmota", RS485, BROCHES_RS485, (0, 1), corps, haut, ROUGE_PCB)
    return nom


# Fusible rearmable radial Bourns MF-R (2026-10-14) : KiCad 10 n'a pas de modele 3D pour
# l'empreinte Fuse:Fuse_Bourns_MF-RHT050 (F1/F2 invisibles en revue 3D et dans le STEP du
# boitier). Corps = contour F.Fab de l'empreinte (7,4 x 3,0) ; hauteur MF-R050 = 12,7 max
# d'apres memoire de la fiche Bourns : A VERIFIER. Le generateur de carte l'affecte a F1/F2.
PTC_MF_R = {"hauteur": (12.7, "fiche Bourns MF-R050 (hauteur max) - a verifier"),
            "pied": (1.0, "pattes coudees sous le corps - a verifier")}


def ptc_radial():
    nom = "PTC_Bourns_MF-R_radial"
    st = Step(nom)
    h, pied = v(PTC_MF_R, "hauteur"), v(PTC_MF_R, "pied")
    for x, y in ((0.0, 0.0), (5.1, 1.2)):                    # pattes, a l'aplomb des pastilles
        st.boite(x - 0.3, y - 0.3, 0.0, x + 0.3, y + 0.3, pied, (0.75, 0.75, 0.75))
    st.boite(-1.15, -0.9, pied, 6.25, 2.1, h, (0.85, 0.65, 0.10))   # corps jaune
    st.ecrit(MODELES / f"{nom}.step")
    return nom


def main():
    BIBLIO.mkdir(exist_ok=True)
    MODELES.mkdir(exist_ok=True)
    noms = [devkit(k) for k in ENTRAXES] + [ads1115(), rs485()]
    for n in noms:
        print("ecrit :", BIBLIO.name + "/" + n + ".kicad_mod", "+", MODELES.name + "/" + n + ".step")
    print("ecrit :", MODELES.name + "/" + ptc_radial() + ".step (modele seul, pour l'empreinte Fuse_Bourns_MF-RHT050)")
    reste = a_mesurer(DEVKIT, ADS, RS485, EMPILEMENT)
    print(f"{len(reste)} cote(s) encore a mesurer :", ", ".join(reste))


if __name__ == "__main__":
    main()
