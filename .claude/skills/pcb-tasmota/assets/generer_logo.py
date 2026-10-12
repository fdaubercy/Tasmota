# -*- coding: utf-8 -*-
"""Genere la signature d'auteur « Frederic - Au Bonheur des Asturies » pour KiCad 10.

A lancer avec le Python de KiCad (il fournit pcbnew, utilise ici seulement pour
les operations booleennes sur polygones et la verification de fabricabilite) :

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" generer_logo.py

Produit, a cote de ce script :
  - logo_asturies.svg                       logo vectoriel source (monochrome)
  - Signature_Auteur.pretty/
      Logo_Asturies_10mm.kicad_mod           logo seul, F.SilkS
      Logo_Asturies_10mm_Dos.kicad_mod       logo seul, B.SilkS, en miroir
      Signature_Auteur_30mm.kicad_mod        logo + texte, F.SilkS
      Signature_Auteur_30mm_Dos.kicad_mod    logo + texte, B.SilkS, en miroir

Le logo : la Croix de la Victoire (Cruz de la Victoria, embleme des Asturies),
croix latine aux bras evases, avec l'alpha et l'omega suspendus aux bras comme
sur le drapeau asturien, le tout dans un anneau. Coordonnees en mm, Y vers le bas
(convention KiCad et SVG), logo centre sur l'origine, 10 mm de diametre.
"""
import math
import os
import uuid

import pcbnew

ICI = os.path.dirname(os.path.abspath(__file__))
BIBLIO = os.path.join(ICI, "Signature_Auteur.pretty")

PAS = 0.1             # pas maxi d'approximation des courbes (mm)
TRAIT_MIN = 0.20      # largeur mini d'une zone pleine verifiee (JLCPCB : 0,15)
ESPACE_MIN = 0.20     # espace mini entre zones pleines / trou mini (JLCPCB : 0,15)

# --- Dimensions du logo (mm) -------------------------------------------------
R_EXT, R_INT = 5.0, 4.35          # anneau
CENTRE_CROIX = (0.0, -1.0)        # croisillon place haut : croix latine
BRAS_HAUT, BRAS_COTE, BRAS_BAS = 2.75, 3.3, 4.7
DEMI_LARG_CENTRE, DEMI_LARG_BOUT = 0.42, 0.85
EXPOSANT_EVASEMENT = 2.5
TRAIT_LETTRE = 0.32               # trait de l'alpha et de l'omega
TRAIT_CHAINE = 0.30               # attache lettre -> bras

# --- Texte de la signature -----------------------------------------------------
LIGNE_1 = ("Frédéric", 2.0, 0.30)                  # (texte, hauteur, epaisseur)
LIGNE_2 = ("Au Bonheur des Asturies", 1.0, 0.18)   # JLCPCB : h >= 1,0 / trait >= 0,15
ECART_LOGO_TEXTE = 0.8


def iu(mm):
    return int(round(mm * 1e6))


def mm(v):
    return v / 1e6


# ------------------------------------------------------------------ primitives
def poly(points):
    """SHAPE_POLY_SET a partir d'une liste de points (mm)."""
    s = pcbnew.SHAPE_POLY_SET()
    s.NewOutline()
    for x, y in points:
        s.Append(iu(x), iu(y))
    return s


def disque(cx, cy, r):
    n = max(24, int(math.ceil(2 * math.pi * r / PAS)))
    return poly([(cx + r * math.cos(2 * math.pi * k / n),
                  cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)])


def union(*sets):
    out = pcbnew.SHAPE_POLY_SET()
    for s in sets:
        out.BooleanAdd(s)
    out.Simplify()
    return out


def trait(points, largeur):
    """Polyligne epaisse a bouts ronds (union de capsules)."""
    r = largeur / 2
    morceaux = [disque(x, y, r) for x, y in points]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        lg = math.hypot(x2 - x1, y2 - y1)
        if lg == 0:
            continue
        nx, ny = -(y2 - y1) / lg * r, (x2 - x1) / lg * r
        morceaux.append(poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                              (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]))
    return union(*morceaux)


def arc(cx, cy, r, a0, a1):
    """Points d'un arc (degres, sens trigo dans le repere Y vers le bas)."""
    n = max(4, int(math.ceil(abs(math.radians(a1 - a0)) * r / PAS)))
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


# ------------------------------------------------------------------ le logo
def bras(cx, cy, dx, dy, longueur):
    """Bras de croix evase : demi-largeur w0 + (w1-w0).t^p, bout droit."""
    nx, ny = -dy, dx
    n = int(math.ceil(longueur / PAS))
    g, d = [], []
    for k in range(n + 1):
        t = k / n
        w = DEMI_LARG_CENTRE + (DEMI_LARG_BOUT - DEMI_LARG_CENTRE) * t ** EXPOSANT_EVASEMENT
        px, py = cx + dx * longueur * t, cy + dy * longueur * t
        g.append((px + nx * w, py + ny * w))
        d.append((px - nx * w, py - ny * w))
    return poly(g + d[::-1])


def demi_largeur_bras(t):
    return DEMI_LARG_CENTRE + (DEMI_LARG_BOUT - DEMI_LARG_CENTRE) * t ** EXPOSANT_EVASEMENT


def alpha(cx, haut):
    """Alpha majuscule (A sans empattement), 2,0 mm de haut."""
    h, demi = 2.0, 0.85
    sommet, pied_g, pied_d = (cx, haut), (cx - demi, haut + h), (cx + demi, haut + h)
    yb = haut + 1.30
    xb = demi * (yb - haut) / h
    return union(trait([pied_g, sommet, pied_d], TRAIT_LETTRE),
                 trait([(cx - xb, yb), (cx + xb, yb)], TRAIT_LETTRE))


def omega(cx, haut):
    """Omega minuscule : deux boucles ouvertes vers le haut, tige centrale."""
    r, fond = 0.48, haut + 0.95          # centre des deux demi-cercles
    gauche = [(cx - 2 * r + 0.10, haut + 0.15)] + arc(cx - r, fond, r, 180, 0)
    droite = arc(cx + r, fond, r, 180, 0) + [(cx + 2 * r - 0.10, haut + 0.15)]
    return union(trait(gauche, TRAIT_LETTRE), trait(droite, TRAIT_LETTRE),
                 trait([(cx, fond), (cx, haut + 0.30)], TRAIT_LETTRE))


def logo():
    cx, cy = CENTRE_CROIX
    croix = union(bras(cx, cy, 0, -1, BRAS_HAUT), bras(cx, cy, 0, 1, BRAS_BAS),
                  bras(cx, cy, -1, 0, BRAS_COTE), bras(cx, cy, 1, 0, BRAS_COTE))
    # Lettres suspendues sous les bras (comme sur le drapeau asturien)
    xl, haut_lettre = 2.0, 0.30
    dessous_bras = cy + demi_largeur_bras(xl / BRAS_COTE) - 0.15
    a = alpha(-xl, haut_lettre)
    o = omega(xl, haut_lettre)
    chaines = union(trait([(-xl, dessous_bras), (-xl, haut_lettre)], TRAIT_CHAINE),
                    trait([(xl, dessous_bras), (xl, haut_lettre + 0.30)], TRAIT_CHAINE))
    anneau = disque(0, 0, R_EXT)
    anneau.BooleanSubtract(disque(0, 0, R_INT))
    return union(anneau, croix, a, o, chaines)


# ------------------------------------------------------------------ verification
def topologie(s):
    return s.OutlineCount(), sum(s.HoleCount(i) for i in range(s.OutlineCount()))


def verifier(s):
    """Erosion de TRAIT_MIN/2 : un col plus fin coupe ou efface une zone.
    Dilatation de ESPACE_MIN/2 : un espace ou un trou plus etroit se referme."""
    ref = topologie(s)
    ero = s.CloneDropTriangulation()
    ero.Deflate(iu(TRAIT_MIN / 2), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, iu(0.002))
    dil = s.CloneDropTriangulation()
    dil.Inflate(iu(ESPACE_MIN / 2), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, iu(0.002))
    ok = topologie(ero) == ref and topologie(dil) == ref
    print("Topologie (contours, trous) : %s ; apres erosion %.2f mm : %s ; apres dilatation %.2f mm : %s -> %s"
          % (ref, TRAIT_MIN, topologie(ero), ESPACE_MIN, topologie(dil), "OK" if ok else "ECHEC"))
    return ok


def contours(s):
    """Liste de polygones [[contour, trou, ...], ...] en mm."""
    res = []
    for i in range(s.OutlineCount()):
        anneaux = [s.COutline(i)] + [s.CHole(i, h) for h in range(s.HoleCount(i))]
        res.append([[(mm(c.CPoint(k).x), mm(c.CPoint(k).y)) for k in range(c.PointCount())]
                    for c in anneaux])
    return res


# ------------------------------------------------------------------ ecritures
def ecrire_svg(s, chemin):
    m = R_EXT + 0.5
    chemins = []
    for p in contours(s):
        d = " ".join("M " + " L ".join("%.4f %.4f" % pt for pt in a) + " Z" for a in p)
        chemins.append('  <path fill="#000" fill-rule="evenodd" d="%s"/>' % d)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!-- Au Bonheur des Asturies - Croix de la Victoire, alpha et omega.'
                ' Unites : mm. Genere par generer_logo.py -->\n'
                '<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="%g %g %g %g">\n'
                % (2 * m, 2 * m, -m, -m, 2 * m, 2 * m))
        f.write("\n".join(chemins) + "\n</svg>\n")


def u(*cle):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "signature-asturies/" + "/".join(map(str, cle))))


def n(v):
    t = ("%.6f" % (v + 0.0)).rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def police(h, ep, miroir=False, indent="\t\t"):
    j = "%s\t(justify mirror)\n" % indent if miroir else ""
    return ("%s(effects\n%s\t(font\n%s\t\t(size %s %s)\n%s\t\t(thickness %s)\n%s\t)\n%s%s)\n"
            % (indent, indent, indent, n(h), n(h), indent, n(ep), indent, j, indent))


def propriete(nom, valeur, x, y, couche, nomfp, miroir, extra=""):
    return ('\t(property "%s" "%s"\n\t\t(at %s %s 0)\n%s\t\t(layer "%s")\n\t\t(hide yes)\n'
            '\t\t(uuid "%s")\n%s\t)\n'
            % (nom, valeur, n(x), n(y), extra, couche, u(nomfp, nom),
               police(1.0 if nom in ("Reference", "Value") else 1.27, 0.15, miroir)))


def ecrire_empreinte(nomfp, descr, polys, textes, dos):
    soie = "B.SilkS" if dos else "F.SilkS"
    fab = "B.Fab" if dos else "F.Fab"
    sx = -1 if dos else 1
    o = ['(footprint "%s"\n\t(version 20260206)\n\t(generator "pcbnew")\n'
         '\t(generator_version "10.0")\n\t(layer "F.Cu")\n\t(descr "%s")\n'
         '\t(tags "logo signature auteur Asturies")\n' % (nomfp, descr)]
    o.append(propriete("Reference", "LOGO", 0, -6.5, soie, nomfp, dos))
    o.append(propriete("Value", nomfp, 0, 6.5, fab, nomfp, dos))
    o.append(propriete("Datasheet", "", 0, 0, fab, nomfp, dos, "\t\t(unlocked yes)\n"))
    o.append(propriete("Description", "", 0, 0, fab, nomfp, dos, "\t\t(unlocked yes)\n"))
    o.append("\t(attr board_only exclude_from_pos_files exclude_from_bom allow_missing_courtyard)\n"
             "\t(duplicate_pad_numbers_are_jumpers no)\n")
    for i, pts in enumerate(polys):
        lignes, ligne = [], []
        for x, y in pts:
            ligne.append("(xy %s %s)" % (n(sx * x), n(y)))
            if len(ligne) == 5:
                lignes.append(" ".join(ligne))
                ligne = []
        if ligne:
            lignes.append(" ".join(ligne))
        o.append("\t(fp_poly\n\t\t(pts\n%s\n\t\t)\n\t\t(stroke\n\t\t\t(width 0.01)\n"
                 "\t\t\t(type solid)\n\t\t)\n\t\t(fill yes)\n\t\t(layer \"%s\")\n"
                 "\t\t(uuid \"%s\")\n\t)\n"
                 % ("\n".join("\t\t\t" + l for l in lignes), soie, u(nomfp, "poly", i)))
    for i, (txt, x, y, h, ep) in enumerate(textes):
        o.append('\t(fp_text user "%s"\n\t\t(at %s %s 0)\n\t\t(layer "%s")\n\t\t(uuid "%s")\n%s\t)\n'
                 % (txt, n(sx * x), n(y), soie, u(nomfp, "texte", i), police(h, ep, dos)))
    o.append("\t(embedded_fonts no)\n)\n")
    with open(os.path.join(BIBLIO, nomfp + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(o))
    print("ecrit :", nomfp)


def largeur_texte(txt, h, ep):
    t = pcbnew.PCB_TEXT(pcbnew.BOARD())
    t.SetText(txt)
    t.SetTextSize(pcbnew.VECTOR2I(iu(h), iu(h)))
    t.SetTextThickness(iu(ep))
    return mm(t.GetBoundingBox().GetWidth())


def main():
    os.makedirs(BIBLIO, exist_ok=True)
    s = logo()
    if not verifier(s):
        raise SystemExit("Logo non fabricable : corriger les dimensions.")
    ecrire_svg(s, os.path.join(ICI, "logo_asturies.svg"))

    frac = s.CloneDropTriangulation()
    frac.Fracture()   # fp_poly n'a pas de trous : contours relies par une fente nulle
    polys = [p[0] for p in contours(frac)]

    # Signature : logo a gauche, deux lignes de texte a droite, origine au centre
    l1, l2 = largeur_texte(*LIGNE_1), largeur_texte(*LIGNE_2)
    larg_texte = max(l1, l2)
    total = 2 * R_EXT + ECART_LOGO_TEXTE + larg_texte
    dx = -total / 2 + R_EXT                          # centre du logo
    x_txt = dx + R_EXT + ECART_LOGO_TEXTE + larg_texte / 2
    print("Signature : %.2f x %.2f mm (texte %.2f mm)" % (total, 2 * R_EXT, larg_texte))
    polys_sig = [[(x + dx, y) for x, y in p] for p in polys]
    textes = [(LIGNE_1[0], x_txt, -1.5, LIGNE_1[1], LIGNE_1[2]),
              (LIGNE_2[0], x_txt, 1.6, LIGNE_2[1], LIGNE_2[2])]

    d_logo = "Logo Au Bonheur des Asturies (Croix de la Victoire), 10 mm, serigraphie"
    d_sig = "Signature d'auteur : logo + Frederic - Au Bonheur des Asturies, %.0f mm" % total
    ecrire_empreinte("Logo_Asturies_10mm", d_logo, polys, [], False)
    ecrire_empreinte("Logo_Asturies_10mm_Dos", d_logo + ", face arriere miroir", polys, [], True)
    ecrire_empreinte("Signature_Auteur_30mm", d_sig, polys_sig, textes, False)
    ecrire_empreinte("Signature_Auteur_30mm_Dos", d_sig + ", face arriere miroir", polys_sig, textes, True)


if __name__ == "__main__":
    main()
