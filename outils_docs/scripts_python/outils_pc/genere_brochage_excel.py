"""Genere le classeur Excel de brochage GPIO d'un env : image de la carte au centre,
une ligne Excel par broche, usage (lu dans le _persist.json, blocs actifs) colle a l'image,
colonnes fusionnees (A:B, D:E) pour completer le branchement a la main.

Usage : python genere_brochage_excel.py <dossier data/<lieu>/<carte>> <sortie.xlsx> <cle de CARTES> <image>
Cartes a borniers (horizontales) : genere_brochage_horizontal.py. Banc (sans Excel) : test_genere_brochage.py.
Ne reecrit jamais un classeur existant (il est complete a la main ensuite).
Excel (pywin32) est pilote directement : aucune dependance a installer.
"""
import json, os, re, sys, math
import win32com.client as win32

DEPOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# ---- Cartes : ordre des broches de haut en bas, mesures de l'image (px) ----
CARTES = {
    "esp32s3-devkitc1": {
        "titre": "ESP32-S3 DevKitC-1 (N16R8)",
        "image": "Esp32-S3-DevKitC1.jpg", "largeur": 1440, "hauteur": 765,
        "y_premier": 219.5, "pas": 21.89,   # centres mesures : 219,5 -> 679,25 px, 22 broches
        "gauche": ["3V3", "3V3", "RST", "4", "5", "6", "7", "15", "16", "17", "18", "8", "3", "46",
                   "9", "10", "11", "12", "13", "14", "5V", "GND"],
        "droite": ["GND", "43", "44", "1", "2", "42", "41", "40", "39", "38", "37", "36", "35", "0",
                   "45", "48", "47", "21", "20", "19", "GND", "GND"],
        # broches de la carte elle-meme : (texte, famille)
        "systeme": {"3V3": ("Alim 3,3 V", "alim"), "5V": ("Alim 5 V", "alim"), "GND": ("Masse", "gnd"),
                    "RST": ("Reset (EN)", "sys"), "43": ("Console série USB (TX0)", "serie"),
                    "44": ("Console série USB (RX0)", "serie"), "0": ("BOOT (strapping) — éviter", "sys"),
                    "3": ("Strapping (JTAG) — éviter", "sys"), "45": ("Strapping (VSPI) — éviter", "sys"),
                    "46": ("Strapping (LOG) — éviter", "sys"), "19": ("USB D− — éviter", "sys"),
                    "20": ("USB D+ — éviter", "sys"), "35": ("Réservé PSRAM octale (N16R8)", "sys"),
                    "36": ("Réservé PSRAM octale (N16R8)", "sys"), "37": ("Réservé PSRAM octale (N16R8)", "sys")},
        # index du tableau template.GPIO -> numero de GPIO (S3 : 0..21 puis 33..48)
        "gpio_template": list(range(22)) + list(range(33, 49)),
    },
    "esp32-devkitc-v4": {
        "titre": "ESP32 DevKitC V4 (38 broches)",
        "image": "Esp32-DevKitC-V4.png", "largeur": 1777, "hauteur": 1039,
        "y_premier": 229.0, "pas": 31.92,   # centres mesures : 229 -> 803,5 px, 19 broches
        "gauche": ["3V3", "RST", "36", "39", "34", "35", "32", "33", "25", "26", "27", "14", "12", "GND",
                   "13", "9", "10", "11", "5V"],
        "droite": ["GND", "23", "22", "1", "3", "21", "GND", "19", "18", "5", "17", "16", "4", "0",
                   "2", "15", "8", "7", "6"],
        "systeme": {"3V3": ("Alim 3,3 V", "alim"), "5V": ("Alim 5 V", "alim"), "GND": ("Masse", "gnd"),
                    "RST": ("Reset (EN)", "sys"), "1": ("Console série USB (TX0)", "serie"),
                    "3": ("Console série USB (RX0)", "serie"), "0": ("BOOT (strapping) — éviter", "sys"),
                    "2": ("Strapping — éviter", "sys"), "5": ("Strapping", "sys"),
                    "12": ("Strapping (tension flash) — éviter", "sys"), "15": ("Strapping (log) — éviter", "sys"),
                    **{g: ("Flash interne — interdit", "sys") for g in ("6", "7", "8", "9", "10", "11")},
                    **{g: ("Entrée seule", "sys") for g in ("34", "35", "36", "39")}},
        # tasmota_template.h::ESP32_TEMPLATE_TO_PHY
        "gpio_template": [0, 1, 2, 3, 4, 5, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
                          26, 27, 6, 7, 8, 11, 32, 33, 34, 35, 36, 37, 38, 39],
    },
    "esp32p4-module-devkit": {
        "titre": "Waveshare ESP32-P4-Module-DEV-KIT (connecteur 40 broches)",
        "image": "ESP32-P4-Module-DEV-KIT-40broches.png", "largeur": 660, "hauteur": 755,
        "y_premier": 143.8, "pas": 23.65,   # 20 lignes, cases de 132 a 605 px
        "gauche": ["3V3", "7", "8", "23", "GND", "21", "20", "6", "3V3", "3", "2", "0", "GND", "24", "33",
                   "26", "48", "53", "47", "GND"],
        "droite": ["5V", "5V", "GND", "37", "38", "22", "GND", "5", "4", "GND", "1", "36", "32", "25", "GND",
                   "54", "GND", "46", "27", "45"],
        "systeme": {"3V3": ("Alim 3,3 V", "alim"), "5V": ("Alim 5 V", "alim"), "GND": ("Masse", "gnd"),
                    "37": ("Console série (TX0)", "serie"), "38": ("Console série (RX0)", "serie"),
                    "36": ("Strapping — éviter", "sys")},
        "gpio_template": list(range(55)),   # P4 : index = GPIO (support.ino::TemplateGpios)
    },
}

FAMILLES = [  # (cle, libelle, couleur RGB)
    ("alim", "Alimentation", (248, 203, 173)), ("gnd", "Masse", (217, 217, 217)),
    ("serie", "Port série", (198, 239, 206)), ("modbus", "ModBus / RS485", (189, 215, 238)),
    ("i2c", "Bus I2C", (221, 235, 247)), ("ecran", "Écran / SPI", (228, 223, 236)),
    ("capteur", "Capteurs / compteurs", (252, 228, 214)), ("entree", "Boutons / entrées", (226, 239, 218)),
    ("relais", "Relais / sorties", (255, 230, 153)), ("led", "LEDs", (255, 242, 204)),
    ("sys", "Système (à éviter)", (237, 237, 237)), ("libre", "Libre", (255, 255, 255)),
]
COULEUR = {k: c for k, _, c in FAMILLES}


def bgr(rgb):
    return rgb[0] + rgb[1] * 256 + rgb[2] * 65536


def noms_composants(depot):
    """Nom Tasmota de chaque code de composant (enum UserSelectablePins)."""
    src = open(os.path.join(depot, "tasmota/include/tasmota_template.h"), encoding="utf-8", errors="replace").read()
    corps = re.sub(r"//.*|^\s*#.*$", "", re.search(r"enum UserSelectablePins\s*\{(.*?)\};", src, re.S).group(1), flags=re.M)
    return [n.strip().split("=")[0].strip().replace("GPIO_", "") for n in corps.split(",") if n.strip()]


def composant(code, noms):
    if not isinstance(code, int) or code < 32:
        return None
    i = code // 32
    return f"{noms[i]} {code % 32 + 1}" if i < len(noms) else None


def famille(chemin, comp):
    t = (chemin + " " + (comp or "")).lower()
    for mots, fam in ((("modbus", "rs485"), "modbus"), (("i2c", "ads1115", "mcp23"), "i2c"),
                      (("ecran", "ili9", "xpt", "spi", "display", "sdcard", "pinssd"), "ecran"),
                      (("led", "ws2812"), "led"), (("bouton", "interrupteur", "key", "swt"), "entree"),
                      (("relai", "rel "), "relais"),
                      (("thermo", "analog", "compteur", "capteur", "cntr", "dsb", "adc", "debit"), "capteur"),
                      (("rx", "tx", "serie"), "serie")):
        if any(m in t for m in mots):
            return fam
    return "relais"


def usages_persist(persist, noms, carte):
    """{gpio: [(texte, famille)]} pour chaque broche des blocs actifs (activation != OFF, ancetres compris)."""
    res = {}

    def ajoute(pin, texte, fam):
        res.setdefault(pin, [])
        if texte not in [t for t, _ in res[pin]]:
            res[pin].append((texte, fam))

    def walk(o, chemin, nom_bloc, actif):
        if isinstance(o, dict):
            actif = actif and o.get("activation") != "OFF"
            nom_bloc = o["name"] if isinstance(o.get("name"), str) else nom_bloc
            p = o.get("pin")
            if isinstance(p, int) and p >= 0 and actif:
                comp = composant(o.get("type"), noms)
                texte = f"{nom_bloc} : {o.get('nom') or chemin[-1]}" + (f" ({comp})" if comp else "")
                ajoute(p, texte, famille("/".join(chemin), comp))
            for k, v in o.items():
                walk(v, chemin + [k], nom_bloc, actif)

    walk(persist, [], "", True)
    # shortcut: le gabarit n'est lu que pour les puces dont la table index->GPIO est connue (S3) ;
    # a etendre quand une autre carte est ajoutee a CARTES.
    gabarit = (persist.get("template") or {}).get("GPIO") or []
    for i, code in enumerate(gabarit):
        comp = composant(code, noms)
        gp = carte["gpio_template"][i] if i < len(carte["gpio_template"]) else None
        if comp and gp is not None and gp not in res:
            ajoute(gp, f"Tasmota : {comp}", famille("", comp))
    return res


def texte_broche(nom, usages, carte):
    """(texte, famille, conflit) affiche en face d'une broche."""
    sysinfo = carte["systeme"].get(nom)
    u = usages.get(int(nom)) if nom.isdigit() else None
    if u:
        texte = " / ".join(t for t, _ in u)
        if sysinfo and sysinfo[1] == "sys":
            texte += "  ⚠ " + re.split(r" \(| —", sysinfo[0])[0]   # avertissement court : « ⚠ BOOT », « ⚠ Strapping »
        return texte, u[0][1], len(u) > 1
    if sysinfo:
        return sysinfo[0], sysinfo[1], False
    return "libre", "libre", False


def genere(dossier_env, sortie, cle_carte, image):
    if os.path.exists(sortie):
        sys.exit(f"REFUS : {sortie} existe deja (il a pu etre complete a la main).")
    carte = CARTES[cle_carte]
    env = os.path.basename(os.path.normpath(dossier_env))
    persist = json.load(open(os.path.join(dossier_env, "_persist.json"), encoding="utf-8"))
    usages = usages_persist(persist, noms_composants(DEPOT), carte)

    PT = 0.75                      # 1 px = 0,75 pt a 96 ppp
    LIGNE = 16.5                   # 22 px : hauteur d'une ligne de broche
    k = 22 / carte["pas"]          # echelle de l'image pour que son pas tombe sur 22 px
    larg_img, haut_img = carte["largeur"] * k * PT, carte["hauteur"] * k * PT
    y1 = carte["y_premier"] * k * PT  # centre de la 1re broche depuis le haut de l'image (pt)
    h3 = math.ceil((y1 - LIGNE / 2 - 22.5 - LIGNE) / PT) * PT  # ligne 3 : comble jusqu'a la 1re broche

    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    try:
        wb = xl.Workbooks.Add()
        ws = wb.Worksheets(1)
        ws.Name = "Brochage"
        ws.Cells.Font.Name = "Arial"
        ws.Cells.Font.Size = 10
        ws.Cells.VerticalAlignment = -4108          # centre en hauteur
        xl.ActiveWindow.DisplayGridlines = False
        for col, w in (("A", 30), ("B", 42), ("D", 42), ("E", 30)):
            ws.Columns(col).ColumnWidth = w
        ws.Columns("C").ColumnWidth = 100
        ws.Columns("C").ColumnWidth = 100 * larg_img / ws.Columns("C").Width
        while ws.Columns("C").Width < larg_img:      # la largeur se fixe par pas : jamais plus etroite que l'image
            ws.Columns("C").ColumnWidth = ws.Columns("C").ColumnWidth + 0.5

        n = len(carte["gauche"])
        ws.Rows(1).RowHeight = 22.5
        ws.Rows(2).RowHeight = LIGNE
        ws.Rows(3).RowHeight = h3
        for r in range(4, 4 + n):
            ws.Rows(r).RowHeight = LIGNE

        ws.Range("A1").Value = env
        ws.Range("A1").Font.Bold = True
        ws.Range("A1").Font.Size = 12
        ws.Range("D1").Value = f"{carte['titre']} · usages tirés de _persist.json (blocs actifs)"
        ws.Range("D1").Font.Size = 9
        ws.Range("D1").Font.Color = bgr((89, 89, 89))
        for cel, al in (("A2:B2", -4152), ("D2:E2", -4131)):
            c = ws.Range(cel)
            c.Merge()
            c.Value = "Usage / branchement"
            c.Font.Bold = True
            c.HorizontalAlignment = al
            c.Interior.Color = bgr((242, 242, 242))

        for i, (g, d) in enumerate(zip(carte["gauche"], carte["droite"])):
            r = 4 + i
            # usage sur deux colonnes fusionnees : le texte ne deborde pas ; colle a l'image de chaque cote
            for plage, nom, al in ((f"A{r}:B{r}", g, -4152), (f"D{r}:E{r}", d, -4131)):
                texte, fam, conflit = texte_broche(nom, usages, carte)
                c = ws.Range(plage)
                c.Merge()
                c.Value = texte
                c.HorizontalAlignment = al
                c.IndentLevel = 1
                c.ShrinkToFit = True             # texte reduit plutot que coupe
                c.Interior.Color = bgr(COULEUR[fam])
                if fam in ("libre", "sys"):
                    c.Font.Italic = True
                    c.Font.Color = bgr((127, 127, 127))
                if conflit:
                    c.Font.Color = bgr((192, 0, 0))
                    c.Font.Bold = True
        # bordures en pointilles sur chaque ligne de broche (usage + destination)
        for plage in (f"A4:B{3 + n}", f"D4:E{3 + n}"):
            for bord in (7, 8, 9, 10, 11, 12):
                b = ws.Range(plage).Borders(bord)
                b.LineStyle = -4118                  # xlDot
                b.Color = bgr((128, 128, 128))

        # image : posee pour que le centre de la 1re broche tombe au milieu de la ligne 4
        r4 = ws.Rows(4)
        top = r4.Top + r4.RowHeight / 2 - y1
        pic = ws.Shapes.AddPicture(os.path.abspath(image), False, True, ws.Columns("C").Left, top, larg_img, haut_img)
        pic.Placement = 3                            # xlFreeFloating : ni deplacee ni etiree par les cellules
        pic.LockAspectRatio = True

        # controle d'alignement : 1re et derniere broche
        for i in (0, n - 1):
            ry = ws.Rows(4 + i)
            centre_ligne = ry.Top + ry.RowHeight / 2
            centre_pin = top + (carte["y_premier"] + i * carte["pas"]) * k * PT
            assert abs(centre_ligne - centre_pin) <= 1.5, f"broche {i + 1} : ecart {centre_ligne - centre_pin:.2f} pt"

        # legende sous l'image
        bas = top + haut_img
        r = 4 + n
        ws.Rows(r).RowHeight = max(LIGNE, math.ceil((bas - ws.Rows(r).Top) / PT) * PT)
        r += 1
        ws.Range(f"A{r}").Value = "Légende"
        ws.Range(f"A{r}").Font.Bold = True
        for j, (cle, lib, coul) in enumerate(FAMILLES):
            c = ws.Range(f"B{r + j}")
            c.Value = lib
            c.Interior.Color = bgr(coul)
            c.HorizontalAlignment = -4152
            c.IndentLevel = 1
        ws.Range(f"A{r + len(FAMILLES) + 1}").Value = (
            "Usages générés le " + __import__("datetime").date.today().isoformat()
            + " : à tenir à jour à la main au fil des montages (le fichier n'est pas régénéré).")
        ws.Range(f"A{r + len(FAMILLES) + 1}").Font.Size = 8

        # GPIO utilises mais absents des connecteurs (puces soudees sur la carte, autres borniers)
        presents = {int(p) for p in carte["gauche"] + carte["droite"] if p.isdigit()}
        hors = sorted(p for p in usages if p not in presents)
        if hors:
            r = r + len(FAMILLES) + 3
            ws.Range(f"D{r}").Value = "GPIO utilisés hors connecteur"
            ws.Range(f"D{r}").Font.Bold = True
            for j, p in enumerate(hors, 1):
                c = ws.Range(f"D{r + j}:E{r + j}")
                c.Merge()
                c.Value = f"GPIO {p} : " + " / ".join(t for t, _ in usages[p])
                c.HorizontalAlignment = -4131
                c.IndentLevel = 1
                c.Interior.Color = bgr(COULEUR[usages[p][0][1]])
                for bord in (7, 8, 9, 10):
                    c.Borders(bord).LineStyle = -4118
                    c.Borders(bord).Color = bgr((128, 128, 128))

        try:  # impression : paysage, une page
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
    print("ecrit :", sortie)


if __name__ == "__main__":
    genere(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
