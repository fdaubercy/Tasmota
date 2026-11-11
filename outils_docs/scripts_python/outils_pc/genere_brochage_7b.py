"""Classeur de brochage du Waveshare ESP32-S3-Touch-LCD-7B (carte d'affichage des debits) : pas de connecteur de broches
ni d'image exploitable (le zip constructeur ne donne que le plan de cotes), donc deux tableaux : un par GPIO de l'ESP32-S3,
un par sortie EXIO de l'expandeur 0x24. Source : WAVESHARE_ESP32-S3-Touch-LCD-7B.md (§ 2 et 3) ; usages du projet = persist
de la carte. Usage : python genere_brochage_7b.py <sortie.xlsx>. Ne reecrit jamais un classeur existant. Banc : test_genere_brochage.py.
"""
import os, sys
from genere_brochage_excel import COULEUR, FAMILLES, bgr

# (GPIO, fonction sur la carte, usage dans le projet, famille)
LCD = "Dalle RGB (display.ini)"
GPIO = [(0, "LCD G3", LCD, "ecran"), (1, "LCD R3", LCD, "ecran"), (2, "LCD R4", LCD, "ecran"), (3, "LCD VSYNC", LCD, "ecran"),
        (4, "Tactile INT (GT911)", "Tactile GT911 : INT (rendu en sortie par preinit.be le temps du reset)", "i2c"),
        (5, "LCD DE", LCD, "ecran"), (6, "Libre : connecteur GPIO (3,3 V, GND, GPIO6), ADC1", "libre (luminosité automatique possible)", "libre"),
        (7, "LCD PCLK", LCD, "ecran"), (8, "I2C SDA (tactile, expandeur, bornier I2C)", "Bus I2C", "i2c"),
        (9, "I2C SCL", "Bus I2C", "i2c"), (10, "LCD B7", LCD, "ecran"),
        (11, "Carte SD MOSI", "Carte SD non montée : pas réutilisable", "sys"), (12, "Carte SD SCK", "Carte SD non montée : pas réutilisable", "sys"),
        (13, "Carte SD MISO", "Carte SD non montée : pas réutilisable", "sys"), (14, "LCD B3", LCD, "ecran"),
        (15, "RS485 TXD (SP3485, sens automatique)", "ModBus RS485 : Série Tx, vers la carte d'acquisition", "modbus"),
        (16, "RS485 RXD", "ModBus RS485 : Série Rx, vers la carte d'acquisition", "modbus"),
        (17, "LCD B6", LCD, "ecran"), (18, "LCD B5", LCD, "ecran"),
        (19, "USB D− ou CAN RX (EXIO5)", "USB (EXIO5 = 0) : éviter", "sys"), (20, "USB D+ ou CAN TX (EXIO5)", "USB (EXIO5 = 0) : éviter", "sys"),
        (21, "LCD G7", LCD, "ecran")] + \
       [(g, "Flash interne" if g < 33 else "PSRAM octale", "Interdit", "sys") for g in range(26, 38)] + \
       [(38, "LCD B4", LCD + " (LED du persist à OFF)", "ecran"), (39, "LCD G2", LCD + " (LED du persist à OFF)", "ecran"),
        (40, "LCD R7", LCD, "ecran"), (41, "LCD R6", LCD, "ecran"), (42, "LCD R5", LCD, "ecran"),
        (43, "UART0 TX (console CH343 ou bornier UART)", "Console série", "serie"), (44, "UART0 RX", "Console série", "serie"),
        (45, "LCD G4", LCD, "ecran"), (46, "LCD HSYNC", LCD, "ecran"), (47, "LCD G6", LCD, "ecran"), (48, "LCD G5", LCD, "ecran")]
GPIO.sort()

# (EXIO, role, etat ecrit par preinit.be : 0xDF en service, 0xDD pendant le reset du tactile)
EXIO = [(0, "Libre (sortie lente)", 1), (1, "Reset du tactile GT911 (TP_RST)", 1), (2, "Rétroéclairage (DISP) : 0 = écran noir", 1),
        (3, "Reset de la dalle (LCD_RST)", 1), (4, "CS de la carte SD (actif bas)", 1), (5, "USB (0) ou CAN (1)", 0),
        (6, "Alimentation de la dalle (LCD_VDD_EN)", 1), (7, "Libre (sortie lente)", 1)]


def genere(sortie):
    import win32com.client as win32
    if os.path.exists(sortie):
        sys.exit(f"REFUS : {sortie} existe deja (il a pu etre complete a la main).")
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
        for col, w in (("A", 9), ("B", 24), ("C", 24), ("D", 36), ("E", 36), ("F", 16)):
            ws.Columns(col).ColumnWidth = w
        ws.Range("A1").Value = "tasmota32s3-ecran-debits-pac"
        ws.Range("A1").Font.Bold = True
        ws.Range("A1").Font.Size = 12
        ws.Range("D1").Value = "Waveshare ESP32-S3-Touch-LCD-7B · source : fiche WAVESHARE_ESP32-S3-Touch-LCD-7B.md"
        ws.Range("D1").Font.Size = 9
        ws.Range("D1").Font.Color = bgr((89, 89, 89))

        def pointilles(c):
            for bord in (7, 8, 9, 10, 11, 12):
                c.Borders(bord).LineStyle = -4118
                c.Borders(bord).Color = bgr((128, 128, 128))

        def entete(r, titres):
            for plage, t in zip(("A:A", "B:C", "D:E", "F:F"), titres):
                d, f = plage.split(":")
                c = ws.Range(f"{d}{r}:{f}{r}")
                c.Merge()
                c.Value = t
                c.Font.Bold = True
                c.Interior.Color = bgr((242, 242, 242))

        def ligne(r, cellules, fam, italique=False):
            for plage, v in cellules:
                c = ws.Range(plage)
                c.Merge()
                c.Value = v
                c.HorizontalAlignment = -4131
                c.IndentLevel = 1
                c.ShrinkToFit = True
                c.Interior.Color = bgr(COULEUR[fam])
                if italique:
                    c.Font.Italic = True
                    c.Font.Color = bgr((127, 127, 127))

        r = 3
        entete(r, ("GPIO", "Fonction sur la carte", "Usage dans le projet (à compléter)", "Libre ?"))
        for gp, fonc, usage, fam in GPIO:
            r += 1
            ligne(r, ((f"A{r}", gp), (f"B{r}:C{r}", fonc), (f"D{r}:E{r}", usage), (f"F{r}", "oui" if fam == "libre" else "non")),
                  fam, fam in ("libre", "sys"))
            ws.Range(f"A{r}").HorizontalAlignment = -4108
        pointilles(ws.Range(f"A4:F{r}"))

        r += 2
        ws.Range(f"A{r}").Value = "Expandeur d'E/S, adresse I2C 0x24 (registre 0x03 : 0xDF en service, 0xDD pendant le reset du tactile)"
        ws.Range(f"A{r}").Font.Bold = True
        r += 1
        entete(r, ("EXIO", "Rôle", "Usage dans le projet (à compléter)", "État écrit"))
        debut = r + 1
        for ex, role, etat in EXIO:
            r += 1
            ligne(r, ((f"A{r}", f"EXIO{ex}"), (f"B{r}:C{r}", role), (f"D{r}:E{r}", ""), (f"F{r}", f"{etat} (bit {ex})")),
                  "libre" if "Libre" in role else "relais")
        pointilles(ws.Range(f"A{debut}:F{r}"))

        r += 2
        ws.Range(f"A{r}").Value = "Légende"
        ws.Range(f"A{r}").Font.Bold = True
        for j, (cle, lib, coul) in enumerate(FAMILLES):
            c = ws.Range(f"B{r + j}")
            c.Value = lib
            c.Interior.Color = bgr(coul)
        ws.Range(f"A{r + len(FAMILLES) + 1}").Value = (
            "Généré le 2026-11-11 d'après la fiche : à tenir à jour à la main (le fichier n'est pas régénéré). "
            "Pas d'image : le zip constructeur ne contient que le plan de cotes et le STEP.")
        ws.Range(f"A{r + len(FAMILLES) + 1}").Font.Size = 8
        try:
            ws.PageSetup.Orientation = 1
            ws.PageSetup.Zoom = False
            ws.PageSetup.FitToPagesWide = 1
            ws.PageSetup.FitToPagesTall = 1
        except Exception as e:
            print("mise en page ignoree :", e)
        ws.Range("A1").Select()
        wb.SaveAs(os.path.abspath(sortie), FileFormat=51)
        wb.Close(False)
    finally:
        xl.Quit()
    print("ecrit :", sortie)


if __name__ == "__main__":
    genere(sys.argv[1])
