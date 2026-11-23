"""Variante « carte verticale » du classeur de brochage : borniers a GAUCHE et/ou a DROITE de l'image, intitules HORIZONTAUX.

Meme principe que genere_brochage_horizontal.py (une case par vis, en face d'elle, collee a l'image, bordure en pointilles), tourne de 90 degres :
lignes de 3 pt, une case d'usage fusionnee par groupe de vis (texte horizontal) et une case de nom par vis, contre l'image.
Entree de CARTES (genere_brochage_horizontal.py) : cles « gauche » et « droite » (ordonnees des vis dans l'image finale), comme « haut » et « bas ».
Usage : python genere_brochage_lateral.py <dossier env> <sortie.xlsx> <cle carte> <image>
"""
import datetime
import json
import math
import os
import sys

import win32com.client as win32

from genere_brochage_excel import COULEUR, DEPOT, FAMILLES, bgr, noms_composants, usages_persist
from genere_brochage_horizontal import CARTES, prepare_image

PT = 0.75
LIGNE = 3                 # hauteur d'une ligne de la grille (pt)
LARG_USAGE, LARG_NOM = 64, 9


def genere(dossier_env, sortie, cle, image):
    if os.path.exists(sortie):
        sys.exit(f"REFUS : {sortie} existe deja (il a pu etre complete a la main).")
    carte = CARTES[cle]
    env = os.path.basename(os.path.normpath(dossier_env))
    persist = json.load(open(os.path.join(dossier_env, "_persist.json"), encoding="utf-8"))
    usages = usages_persist(persist, noms_composants(DEPOT), carte)
    utilises = set(carte.get("places", ()))

    def texte_groupe(titre, gpio, fixe, court):
        if gpio is None:                                   # borne sans GPIO (ou plusieurs, decrits dans le texte fixe)
            return fixe, ("sys" if "non vérifi" in fixe else "entree")
        utilises.add(gpio)
        if gpio in usages:
            u = " / ".join(t for t, _ in usages[gpio])
            return (f"{titre} (GPIO{gpio}) : {u}"), usages[gpio][0][1]
        return f"{titre} (GPIO{gpio}) : libre", "libre"

    image, retouchee = prepare_image(image, carte, sortie)
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    try:
        wb = xl.Workbooks.Add()
        ws = wb.Worksheets(1)
        ws.Name = "Brochage"
        ws.Cells.Font.Name = "Arial"
        ws.Cells.Font.Size = 10
        ws.Cells.VerticalAlignment = -4108
        xl.ActiveWindow.DisplayGridlines = False
        # colonnes : A marge | B usage gauche | C nom gauche | D image | E nom droite | F usage droite
        for c, w in ((1, 2), (2, LARG_USAGE), (3, LARG_NOM), (5, LARG_NOM), (6, LARG_USAGE)):
            ws.Columns(c).ColumnWidth = w
        cible_pt = carte["largeur"] * carte["echelle"] * PT
        for w in [i / 2 for i in range(20, 400)]:
            ws.Columns(4).ColumnWidth = w
            if ws.Columns(4).Width >= cible_pt:
                break
        larg_pt = ws.Columns(4).Width
        s = larg_pt / carte["largeur"]                     # pt par pixel de l'image finale
        haut_pt = carte["hauteur"] * s
        R0 = 3
        nl = math.ceil(haut_pt / LIGNE)
        ws.Rows(1).RowHeight = 22.5
        ws.Rows(2).RowHeight = 8
        for r in range(R0, R0 + nl):
            ws.Rows(r).RowHeight = LIGNE

        def ligne(y):                                      # ordonnee image (px) -> ligne Excel
            return R0 + int(y * s / LIGNE)

        def pointilles(c):
            for b in (7, 8, 9, 10):
                c.Borders(b).LineStyle = -4118
                c.Borders(b).Color = bgr((128, 128, 128))

        t = ws.Range(ws.Cells(1, 2), ws.Cells(1, 6))
        t.Merge()
        t.Value = f"{env} — {carte['titre']} · usages tirés de _persist.json (blocs actifs)"
        t.Font.Bold = True
        t.HorizontalAlignment = -4131

        for cote, c_usage, c_nom, ha in (("gauche", 2, 3, -4152), ("droite", 6, 5, -4131)):
            for liste, titre, gpio, fixe in carte.get(cote, []):
                ys = [y for y, _ in liste]
                p = (ys[1] - ys[0]) if len(ys) > 1 else carte["pas"]
                r1, r2 = ligne(ys[0] - p / 2) + 1, ligne(ys[-1] + p / 2)   # une ligne vide en haut : separation
                texte, fam = texte_groupe(titre, gpio, fixe, len(liste) == 1)
                u = ws.Range(ws.Cells(r1, c_usage), ws.Cells(r2, c_usage))
                u.Merge()
                u.Value = texte
                u.WrapText = True
                u.HorizontalAlignment = ha                 # colle a l'image
                u.VerticalAlignment = -4108
                u.Interior.Color = bgr(COULEUR[fam])
                if fam in ("libre", "sys"):
                    u.Font.Italic = True
                    u.Font.Color = bgr((127, 127, 127))
                pointilles(u)
                for y, nom in liste:                       # nom de chaque vis, contre l'image
                    cn = ws.Range(ws.Cells(ligne(y - p / 2) + 1, c_nom), ws.Cells(ligne(y + p / 2), c_nom))
                    cn.Merge()
                    cn.Value = nom or titre
                    cn.Font.Size = 8
                    cn.HorizontalAlignment = -4108
                    cn.VerticalAlignment = -4108
                    pointilles(cn)

        pic = ws.Shapes.AddPicture(os.path.abspath(image), False, True, ws.Columns(4).Left, ws.Rows(R0).Top, larg_pt, haut_pt)
        pic.Placement = 3

        # legende (colonne B) et GPIO absents de l'image (colonnes D a F), sous l'image
        r = R0 + nl + 2
        ws.Cells(r, 2).Value = "Légende"
        ws.Cells(r, 2).Font.Bold = True
        for j, (_, lib, coul) in enumerate(FAMILLES, 1):
            c = ws.Cells(r + j, 2)
            c.Value = lib
            c.Interior.Color = bgr(coul)
            c.IndentLevel = 1
        hors = sorted(set(usages) - utilises) + sorted(g for g in carte["systeme"] if g not in usages and g not in utilises)
        ws.Cells(r, 4).Value = "GPIO hors bornier (en-tête, carte)"
        ws.Cells(r, 4).Font.Bold = True
        for j, g in enumerate(hors, 1):
            c = ws.Range(ws.Cells(r + j, 4), ws.Cells(r + j, 6))
            c.Merge()
            if g in usages:
                txt = " / ".join(t for t, _ in usages[g])
                if g in carte["systeme"]:
                    txt += "  ⚠ " + carte["systeme"][g]
                c.Interior.Color = bgr(COULEUR[usages[g][0][1]])
            else:
                txt = carte["systeme"][g]
                c.Interior.Color = bgr(COULEUR["sys"])
            c.Value = f"GPIO {g} : {txt}"
            c.IndentLevel = 1
            pointilles(c)
        fin = r + max(len(FAMILLES), len(hors)) + 2
        ws.Cells(fin, 2).Value = ("Usages générés le " + datetime.date.today().isoformat()
                                  + " : à tenir à jour à la main au fil des montages (le fichier n'est pas régénéré).")
        ws.Cells(fin, 2).Font.Size = 8
        for j, n in enumerate(carte.get("notes", []), 1):
            ws.Cells(fin + j, 2).Value = n
            ws.Cells(fin + j, 2).Font.Size = 8
        try:
            ps = ws.PageSetup
            ps.Orientation = 1
            ps.Zoom = False
            ps.FitToPagesWide = 1
            ps.FitToPagesTall = 1
        except Exception as e:
            print("mise en page ignoree :", e)
        ws.Range("A1").Select()
        wb.SaveAs(os.path.abspath(sortie), FileFormat=51)
        wb.Close(False)
    finally:
        xl.Quit()
        if retouchee and os.path.exists(image):
            os.remove(image)
    print("ecrit :", sortie)


if __name__ == "__main__":
    genere(*sys.argv[1:5])
