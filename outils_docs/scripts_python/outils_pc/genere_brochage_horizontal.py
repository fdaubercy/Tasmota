"""Variante « carte horizontale » (borniers en haut et en bas de l'image) du classeur de brochage.

Colonnes Excel etroites (4 px) ; chaque borne (ou groupe de bornes d'un relais) recoit une case fusionnee
en face d'elle, texte vertical, centre, colle a l'image, bordure en pointilles.
Usage : python genere_brochage_horizontal.py <dossier env> <sortie.xlsx> <cle carte> <image>
"""
import json, math, os, sys
import win32com.client as win32
from genere_brochage_excel import (DEPOT, FAMILLES, COULEUR, bgr, noms_composants, usages_persist)
PX = 4                      # largeur d'une colonne (px)
PT = 0.75


def bornes(premier, pas, noms):
    return [(premier + pas * i, n) for i, n in enumerate(noms)]


CARTES = {
    "esp32-relay-x8": {
        "titre": "Carte « ESP32 Relay x8 » (ESP32-WROOM-32E, 7-30 V)",
        "largeur": 1556, "hauteur": 839, "echelle": 0.75, "crop": None, "pas": 57.5,
        "gpio_template": [0, 1, 2, 3, 4, 5, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
                          26, 27, 6, 7, 8, 11, 32, 33, 34, 35, 36, 37, 38, 39],
        # (bornes [(x, nom)], titre du groupe, gpio ou None, texte fixe)
        "haut": [(bornes(368, 60, ["7-30V"]), "Alim 7-30 V", None, "Alimentation 7-30 V DC"),
                 (bornes(428, 60, ["GND"]), "Masse", None, "Masse"),
                 (bornes(488, 60, ["5V"]), "5 V", None, "5 V (entrée 5 V ou sortie du régulateur)")],
        "bas": [(bornes(x0 + 3 * j * p, p, [f"NO{k}", f"COM{k}", f"NC{k}"]), f"Relais {k}", g, None)
                for (k, g), x0, p in [((k, g), 66 if k <= 4 else 857, 57.4 if k <= 4 else 57.6)
                                      for k, g in zip(range(1, 9), [32, 33, 25, 26, 27, 14, 12, 13])]
                for j in [(k - 1) % 4]],
        "systeme": {0: "BOOT (bouton de la carte)", 23: "LED d'état de la carte",
                    1: "TX (en-tête de programmation)", 3: "RX (en-tête de programmation)"},
    },
    "waveshare-s3-eth-8di-8ro": {
        "titre": "Waveshare ESP32-S3-ETH-8DI-8RO (relais par TCA9554 I2C 0x20)",
        "largeur": 690, "hauteur": 582, "echelle": 1.3, "crop": (130, 0, 820, 582), "pas": 22.5,
        "gpio_template": list(range(22)) + list(range(33, 49)),
        "haut": [(bornes(221.7 - 130 + 3 * 22.39 * (k - 1), 22.39, ["", "", ""]), f"RO{k}", f"TCA{k}", None)
                 for k in range(1, 9)],
        "bas": [(bornes(407.5 - 130, 22.5, ["COM"]), "COM", None, "COM des entrées (commun)"),
                (bornes(430.0 - 130, 22.5, ["DGND"]), "DGND", None, "Masse des entrées (DGND)")]
               + [(bornes(452.5 - 130 + 22.5 * (k - 1), 22.5, [f"DI{k}"]), f"DI{k}", 3 + k, None) for k in range(1, 9)]
               + [(bornes(642.5 - 130, 22.5, ["", ""]), "7-36V", None, "Alimentation 7-36 V DC (+ et − : voir sérigraphie)"),
                  (bornes(697.5 - 130, 22.5, ["", "", ""]), "RS485", [17, 18], "RS485 isolé A+ / B− / PE (GPIO17/18)")],
        "systeme": {0: "BOOT", 38: "LED RGB WS2812 de la carte", 46: "Buzzer", 45: "Carte TF (strapping)",
                    47: "Carte TF", 48: "Carte TF"},
    },
}


def relais_tca(persist):
    """Relais virtuels du TCA9554, dans l'ordre de declaration du persist = RO1, RO2..."""
    res = []

    def walk(o, nom_bloc, actif):
        if isinstance(o, dict):
            actif = actif and o.get("activation") != "OFF"
            nom_bloc = o["name"] if isinstance(o.get("name"), str) else nom_bloc
            if "TCA9554" in str(o.get("virtuel", "")) and actif:
                res.append((f"{nom_bloc} : {o.get('nom')}", "relais"))
            for v in o.values():
                walk(v, nom_bloc, actif)
    walk(persist, "", True)
    return res


def genere(dossier_env, sortie, cle, image):
    if os.path.exists(sortie):
        sys.exit(f"REFUS : {sortie} existe deja (il a pu etre complete a la main).")
    carte = CARTES[cle]
    env = os.path.basename(os.path.normpath(dossier_env))
    persist = json.load(open(os.path.join(dossier_env, "_persist.json"), encoding="utf-8"))
    usages = usages_persist(persist, noms_composants(DEPOT), carte)
    tca = relais_tca(persist)
    utilises = set()

    def texte_groupe(titre, gpio, fixe, court=False):
        if fixe and gpio is None:
            return fixe, "alim" if "Alim" in fixe or "5 V" in fixe else ("gnd" if "Masse" in fixe else "entree")
        if isinstance(gpio, str):                       # relais du TCA9554
            k = int(gpio[3:]) - 1
            return (f"{titre} : {tca[k][0]}", "relais") if k < len(tca) else (f"{titre} : libre", "libre")
        if isinstance(gpio, list):                      # bornier lie a plusieurs GPIO (RS485)
            utilises.update(gpio)
            u = [t for g in gpio for t, _ in usages.get(g, [])]
            return (f"{titre} : " + " / ".join(u), "modbus") if u else (fixe, "modbus")
        utilises.add(gpio)
        if gpio in usages:
            if court:                                   # case d'une seule vis : sans le nom du bloc
                return f"{titre} · GPIO{gpio} · " + " / ".join(t.split(" : ", 1)[-1] for t, _ in usages[gpio]), usages[gpio][0][1]
            return f"{titre} (GPIO{gpio}) : " + " / ".join(t for t, _ in usages[gpio]), usages[gpio][0][1]
        return (fixe or f"{titre} (GPIO{gpio}) : libre"), ("modbus" if fixe else "libre")

    if carte["crop"]:
        from PIL import Image
        tmp = os.path.join(os.path.dirname(os.path.abspath(sortie)), "_tmp_image.png")
        Image.open(image).crop(carte["crop"]).save(tmp)
        image = tmp
    k = carte["echelle"]
    larg_px, haut_px = carte["largeur"] * k, carte["hauteur"] * k
    ncol = math.ceil(larg_px / PX)
    C0 = 2                                               # l'image commence en colonne B

    def col(x):                                         # abscisse image (px d'origine) -> colonne Excel
        return C0 + int(x * k // PX)

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
        ws.Columns(1).ColumnWidth = 2
        plage_img = ws.Range(ws.Cells(1, C0), ws.Cells(1, C0 + ncol))
        for w in [i / 100 for i in range(10, 120)]:      # largeur < 1 caractere : non lineaire, on cherche 4 px
            ws.Columns(C0).ColumnWidth = w
            if ws.Columns(C0).Width >= PX * PT:
                break
        plage_img.EntireColumn.ColumnWidth = w
        largeur_col = ws.Columns(C0).Width

        def case(r1, r2, c1, c2):
            return ws.Range(ws.Cells(r1, c1), ws.Cells(r2, c2))

        HAUT_USAGE, HAUT_NOM = 230, 30
        ws.Rows(1).RowHeight = 22.5
        ws.Rows(2).RowHeight = 8
        ws.Rows(3).RowHeight = HAUT_USAGE
        ws.Rows(4).RowHeight = HAUT_NOM
        n_img = math.ceil(haut_px * PT / 15)
        for r in range(5, 5 + n_img):
            ws.Rows(r).RowHeight = 15
        rb = 5 + n_img                                   # ligne des noms de bornes du bas
        ws.Rows(rb).RowHeight = HAUT_NOM
        ws.Rows(rb + 1).RowHeight = HAUT_USAGE

        t = case(1, 1, C0, C0 + ncol)
        t.Merge()
        t.Value = f"{env} — {carte['titre']} · usages tirés de _persist.json (blocs actifs)"
        t.Font.Bold = True
        t.HorizontalAlignment = -4131

        def pointilles(c):
            for b in (7, 8, 9, 10):
                c.Borders(b).LineStyle = -4118
                c.Borders(b).Color = bgr((128, 128, 128))

        for cote, r_usage, r_nom, va in (("haut", 3, 4, -4107), ("bas", rb + 1, rb, -4160)):
            for liste, titre, gpio, fixe in carte[cote]:
                xs = [x for x, _ in liste]
                p = (xs[1] - xs[0]) if len(xs) > 1 else carte["pas"]
                c1, c2 = col(xs[0] - p / 2) + 1, col(xs[-1] + p / 2)   # une colonne vide a gauche : separation
                texte, fam = texte_groupe(titre, gpio, fixe, court=len(liste) == 1)
                u = case(r_usage, r_usage, c1, c2)
                u.Merge()
                u.Value = texte
                u.Orientation = 90                      # texte vertical
                u.VerticalAlignment = va                # colle a l'image (bas en haut, haut en bas)
                u.HorizontalAlignment = -4108
                u.WrapText = True
                u.Interior.Color = bgr(COULEUR[fam])
                if fam in ("libre", "sys"):
                    u.Font.Italic = True
                    u.Font.Color = bgr((127, 127, 127))
                pointilles(u)
                for x, nom in liste:                    # nom de chaque vis, sous/sur la case d'usage
                    cn = case(r_nom, r_nom, col(x - p / 2) + 1, col(x + p / 2))
                    cn.Merge()
                    cn.Value = nom or titre
                    cn.Orientation = 90
                    cn.Font.Size = 8
                    cn.HorizontalAlignment = -4108
                    cn.VerticalAlignment = -4108
                    pointilles(cn)

        top = ws.Rows(5).Top
        left = ws.Columns(C0).Left
        pic = ws.Shapes.AddPicture(os.path.abspath(image), False, True, left, top, larg_px * PT, haut_px * PT)
        pic.Placement = 3
        assert abs(ncol * largeur_col - larg_px * PT) <= largeur_col + 0.01, "grille et image desalignees"

        # legende + GPIO hors bornier
        r = rb + 3
        ws.Cells(r, C0).Value = "Légende"
        ws.Cells(r, C0).Font.Bold = True
        for j, (_, lib, coul) in enumerate(FAMILLES):
            c = case(r + 1 + j, r + 1 + j, C0, C0 + 40)
            c.Merge()
            c.Value = lib
            c.Interior.Color = bgr(coul)
            c.IndentLevel = 1
        hors = sorted(set(usages) - utilises) + sorted(g for g in carte["systeme"] if g not in usages and g not in utilises)
        c0 = C0 + 60
        ws.Cells(r, c0).Value = "GPIO hors bornier (en-tête, carte)"
        ws.Cells(r, c0).Font.Bold = True
        for j, g in enumerate(hors, 1):
            c = case(r + j, r + j, c0, c0 + 110)
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
            c.ShrinkToFit = True
            pointilles(c)
        fin = r + max(len(FAMILLES), len(hors)) + 2
        ws.Cells(fin, C0).Value = ("Usages générés le " + __import__("datetime").date.today().isoformat()
                                   + " : à tenir à jour à la main au fil des montages (le fichier n'est pas régénéré).")
        ws.Cells(fin, C0).Font.Size = 8
        try:
            ps = ws.PageSetup
            ps.Orientation = 2
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
        if carte["crop"] and os.path.exists(image):
            os.remove(image)
    print("ecrit :", sortie)


if __name__ == "__main__":
    genere(*sys.argv[1:5])
