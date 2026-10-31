"""Carte porteuse « cuve » (ESP32-S3 DevKitC-1 WeAct) - description et generation.

Source des broches : data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json
(blocs `environnement`, decodes par inventaire_materiel.py) :
  GPIO4 RX / GPIO5 TX  -> module RS485 (direction automatique)
  GPIO6                -> ruban WS2815 (via 74AHCT125 alimente en 5 V)
  GPIO8 SCL / GPIO9 SDA -> module ADS1115 (alimente en 3,3 V, confirme le 2026-10-11)
  GPIO18               -> DS18B20 (1-Wire, rappel 4,7 k)
  GPIO38 / GPIO39      -> LED Link / LED etat
  GPIO7 (J14 broche 3) -> bouton du ruban (bouton1, 2026-10-13) : rappel 10 k + 100 nF (v0.2)
Decisions utilisateur du 2026-10-11 : carte porteuse + modules du commerce,
entree 12 V, ruban WS2815 alimente HORS carte (2,4 A), ADS1115 en 3,3 V.

Usage (Python de KiCad) :
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" generer_carte_cuve.py
"""
import os
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
SOUS_CHEMIN = Path(".claude") / "skills" / "pcb-tasmota" / "scripts"


def _scripts():
    """Scripts de la skill : variable PCB_SCRIPTS, sinon en remontant jusqu'au depot."""
    if os.environ.get("PCB_SCRIPTS"):
        return Path(os.environ["PCB_SCRIPTS"])
    for p in (ICI, *ICI.parents):
        if (p / SOUS_CHEMIN).is_dir():
            return p / SOUS_CHEMIN
        if p.name == "pcb-tasmota" and (p / "scripts").is_dir():      # exemple range dans la skill
            return p / "scripts"
    return Path(r"C:\Users\fdaub\Documents\Github\Tasmota") / SOUS_CHEMIN


sys.path.insert(0, str(_scripts()))
SIGNATURE = _scripts().parent / "assets" / "Signature_Auteur.pretty"
from kicad_gen import Schema  # noqa: E402
from kicad_carte import Carte  # noqa: E402

PROJET = "carte_cuve"
REV = "0.3"   # v0.3 (2026-10-31) : module RS485 XY-017 reel, JP1 supprime, bornier du bouton, voies reordonnees
ECART_DEVKIT = 25.4      # entraxe des 2 rangees du DevKitC-1 : A MESURER (25,4 ou 22,86 mm)
L, H = 100.0, 100.0      # 100 x 100 mm : palier le moins cher chez JLCPCB

R_THT = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
R_DEBOUT = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"   # 5,1 x 3 mm d'emprise
C_DISC = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
C_DISC_2P5 = "Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm"    # 4,6 x 2,1 mm d'emprise
MODELE_PTC = "${PCB_TASMOTA_3D}/PTC_Bourns_MF-R_radial.step"   # KiCad 10 n'en fournit pas
BORNIER2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"
BORNIER3 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal"
PTC = "Fuse:Fuse_Bourns_MF-RHT050"

s = Schema(PROJET, "Carte porteuse cuve - ESP32-S3 ModBus", REV, "2026-10-31",
           commentaires=["Persist : data/garage/tasmota32s3-capteurs-cuve-modbus",
                         "ADS1115 en 3,3 V - ruban WS2815 alimente hors carte",
                         f"Entraxe DevKitC-1 = {ECART_DEVKIT} mm : A MESURER avant commande"])
P = {}   # placement {ref: (x, y, rotation)} dans le repere carte (mm)


def R(ref, val, pos, n1, n2, place, empreinte=R_THT):
    s.composant(ref, "Device:R", val, empreinte, pos, {"1": n1, "2": n2})
    P[ref] = place


def C(ref, val, pos, n1, n2, place, empreinte=C_DISC):
    s.composant(ref, "Device:C", val, empreinte, pos, {"1": n1, "2": n2})
    P[ref] = place


# ---------------------------------------------------------------- alimentation
s.cadre("Alimentation 12 V -> 5 V (protegee)", 15, 15, 150, 95)
s.composant("J1", "Connector:Screw_Terminal_01x02", "Entree 12 V", BORNIER2, (25.4, 40.64),
            {"1": "+12V_IN", "2": "GND"}); P["J1"] = (5.715, 15.24, 270)
s.composant("F1", "Device:Polyfuse", "PTC 0,5A MF-R050", PTC, (45.72, 30.48),
            {"1": "+12V_IN", "2": "+12V_F"}); P["F1"] = (12.0, 4.0, 0)   # v0.2 : hors trajet USB-C (~12,7 mm de haut)
s.composant("D1", "Device:D_Schottky", "1N5819 (inversion)", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
            (63.5, 30.48), {"1": "+12V", "2": "+12V_F"}); P["D1"] = (33.0, 9.6, 180)     # v0.2 : au-dessus du DevKit
s.composant("D2", "Device:D_TVS", "P6KE18CA", "Diode_THT:D_DO-15_P10.16mm_Horizontal", (78.74, 50.8),
            {"1": "+12V", "2": "GND"}); P["D2"] = (16.51, 22.86, 0)
# v0.3 : C1 en 35 V, la P6KE18CA ecrete a ~25,2 V
s.composant("C1", "Device:C_Polarized", "100uF 35V", "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", (91.44, 50.8),
            {"1": "+12V", "2": "GND"}); P["C1"] = (39.8, 53.0, 0)
# v0.2 : C3 colle sous U1 (+12V sous U1.1, GND sous U1.2) : boucle d'entree la plus courte
C("C3", "100nF 50V", (101.6, 50.8), "+12V", "GND", (32.4, 66.95, 0), empreinte=C_DISC_2P5)
s.composant("U1", "Converter_DCDC:TSR_1-2450", "TSR 1-2450", "Converter_DCDC:Converter_DCDC_TRACO_TSR-1_THT",
            (119.38, 33.02), {"1": "+12V", "2": "GND", "3": "+5V"}); P["U1"] = (32.4, 63.3, 0)
s.composant("C2", "Device:C_Polarized", "47uF 10V", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", (139.7, 50.8),
            {"1": "+5V", "2": "GND"}); P["C2"] = (43.5, 61.5, 0)
# v0.2 (2026-10-14) : U1 (TSR, ~10 mm de haut), C1, C2, C3 regroupes entre R7 et l'ADS1115. En v0.1
# U1 et D1 mordaient sur l'emprise du DevKit, et U1 et C1 barraient le trajet des cables USB-C.
s.composant("D3", "Device:D_Schottky", "1N5819 (anti-retour USB)", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
            (139.7, 30.48), {"1": "+5V_DEVKIT", "2": "+5V"}); P["D3"] = (44.45, 46.99, 0)
s.composant("F2", "Device:Polyfuse", "PTC 0,2A MF-R020 (capteurs)", PTC, (45.72, 76.2),
            {"1": "+12V", "2": "+12V_CAPT"}); P["F2"] = (11.43, 7.62, 0)
s.drapeau("+12V", (63.5, 76.2))
s.drapeau("GND", (78.74, 76.2))
s.texte("Le +12 V du ruban va DIRECTEMENT de l'alimentation au ruban (2,4 A) :\n"
        "il ne traverse pas cette carte. GND commun obligatoire.", (17, 84))

# ---------------------------------------------------------------- DevKitC-1
s.cadre("ESP32-S3 DevKitC-1 (WeAct) sur barrettes femelles", 160, 15, 300, 175)
G = {"1": "+3V3", "2": "+3V3", "3": None, "4": "RS485_RX", "5": "RS485_TX", "6": "WS_DATA_3V3",
     "7": "GPIO7", "8": "GPIO15", "9": "GPIO16", "10": "GPIO17", "11": "DS18_DQ", "12": "I2C_SCL",
     "13": None, "14": None, "15": "I2C_SDA", "16": None, "17": None, "18": None, "19": None,
     "20": None, "21": "+5V_DEVKIT", "22": "GND"}
D = {str(i): None for i in range(1, 23)}
D.update({"1": "GND", "9": "LED_ETAT", "10": "LED_LINK", "21": "GND", "22": "GND"})
# Empreinte Modules_Tasmota : 2 barrettes femelles + modele 3D du DevKit (pastilles 1-22 =
# rangee J1 du DevKit, 23-44 = rangee J3) ; memes pastilles que les 2 PinSocket d'avant.
s.composant("A1", "Connector_Generic:Conn_02x22_Top_Bottom", "ESP32-S3-DevKitC-1 (WeAct)",
            f"Modules_Tasmota:ESP32-S3-DevKitC-1_E{ECART_DEVKIT:.2f}mm", (228.6, 93.98),
            {**G, **{str(int(k) + 22): n for k, n in D.items()}})
P["A1"] = (95.25, 13.97, 270)
s.texte("A1 1-22  : 3V3 3V3 RST IO4 IO5 IO6 IO7 IO15 IO16 IO17 IO18 IO8 IO3 IO46 IO9 IO10 IO11 IO12 IO13 IO14 5V GND\n"
        "A1 23-44 : GND TX RX IO1 IO2 IO42 IO41 IO40 IO39 IO38 IO37 IO36 IO35 IO0 IO45 IO48 IO47 IO21 IO20 IO19 GND GND\n"
        "Non connectes volontairement : strapping IO0/IO3/IO45/IO46, PSRAM IO35-37, USB IO19/IO20.",
        (162, 160))

# ---------------------------------------------------------------- ADS1115
s.cadre("ADS1115 (module, VDD 3,3 V) et conditionnement des 4 voies", 15, 105, 150, 285)
s.composant("J4", "Connector_Generic:Conn_01x10", "Module ADS1115",
            "Modules_Tasmota:Module_ADS1115_1x10", (30.48, 160.02),
            {"1": "+3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "GND", "6": None,
             "7": "AIN0", "8": "AIN1", "9": "AIN2", "10": "AIN3"}); P["J4"] = (50.8, 66.04, 0)
# v0.3 : voies decalees de 10,16 mm a gauche -> coin bas droit libre sous le bornier A/B du XY-017
BORNES = {"J10": 29.21, "J11": 45.72, "J12": 62.23, "J13": 78.74}
for k, (j, x) in enumerate(BORNES.items()):
    y = 125 + k * 40
    # v0.3 : entree / 0V / +12 - un brin entre bornes voisines ne met plus 12 V sur le shunt de 0,25 W
    # (entree-0V sans danger, 0V-+12 fait declencher F2) ; relecture du 2026-10-31
    s.composant(j, "Connector:Screw_Terminal_01x03", f"Voie A{k} (entree / GND / +12V)", BORNIER3, (135, y),
                {"1": f"IN{k}", "2": "GND", "3": "+12V_CAPT"})
    P[j] = (x - 10.16, 93.98, 0)
    if k < 2:   # tension 0-10 V : pont 24 k / 10 k -> 2,94 V a pleine echelle
        R(f"R{2 * k + 1}", "24k 1%", (110, y), f"IN{k}", f"AIN{k}", (x - 5.08, 83.82, 90))
        R(f"R{2 * k + 2}", "10k 1%", (95, y + 10), "GND", f"AIN{k}", (x, 83.82, 90))
    else:       # courant 0-20 mA : shunt 150 ohm -> 3,0 V, serie 1 k (protection)
        rs, rp = ("R5", "R6") if k == 2 else ("R9", "R10")
        R(rp, "1k", (110, y), f"IN{k}", f"AIN{k}", (x - 5.08, 83.82, 90))
        R(rs, "150 1% 0,25W", (95, y + 10), "GND", f"IN{k}", (x, 83.82, 90))
    C(f"C{5 + k}", "100nF", (80, y + 10), f"AIN{k}", "GND", (x - 5.08, 69.85, 0))
s.texte("A0, A1 : 0-10 V (R1/R3 24 k, R2/R4 10 k). A2, A3 : 0-20 mA (shunts R5/R9 150 ohm,\n"
        "serie R6/R10 1 k). Voir outils_docs/Electronique/ADS1115/CABLAGE_ADS1115.md.\n"
        "Capteur 2 fils 4-20 mA : + sur borne +12V, - sur borne entree.", (17, 270))

# ---------------------------------------------------------------- peripheriques
s.cadre("RS485, ruban WS2815, DS18B20, voyants, extensions", 310, 15, 410, 285)
# v0.3 : module XY-017 reel (confirme le 2026-10-31), en 3,3 V fixe : JP1 supprime (en 5 V, son RXD
# aurait mis 5 V sur GPIO4). Debout sous le DevKit (rotation 270 : broches vers -x, corps vers +y),
# bornier A/B en bas, au-dessus du coin libre a droite de J13 : le cable du bus sort par le bord bas.
s.composant("J5", "Connector_Generic:Conn_01x04", "Module RS485 XY-017 (VCC TXD RXD GND)",
            "Modules_Tasmota:Module_RS485_Auto_XY-017", (330.2, 33.02),
            {"1": "+3V3", "2": "RS485_TX", "3": "RS485_RX", "4": "GND"}); P["J5"] = (94.5, 45.9, 270)
for u, n in ((1, {"1": "GND", "2": "WS_DATA_3V3", "3": "WS_DATA_5V"}),
             (2, {"4": "+5V", "5": "GND", "6": None}), (3, {"8": None, "9": "GND", "10": "+5V"}),
             (4, {"11": None, "12": "GND", "13": "+5V"}), (5, {"7": "GND", "14": "+5V"})):
    s.composant("U3", "74xx:74AHCT125", "74AHCT125", "Package_DIP:DIP-14_W7.62mm",
                (330.2 + (u - 1) % 3 * 25.4, 76.2 + (u - 1) // 3 * 25.4), n, unite=u)
P["U3"] = (15.24, 45.72, 0)
C("C4", "100nF", (395, 76.2), "+5V", "GND", (26.67, 45.72, 270))
# v0.3 : GPIO6 flotte tant que Tasmota ne l'a pas configure -> entree 1A de U3 tiree a 0V (pas de pixel parasite)
R("R16", "10k", (370, 101.6), "WS_DATA_3V3", "GND", (15.24, 41.15, 0), empreinte=R_DEBOUT)
R("R7", "330", (395, 101.6), "WS_DATA_5V", "RUBAN_DI", (26.67, 53.34, 270))
s.composant("J8", "Connector:Screw_Terminal_01x03", "Ruban WS2815 (DI / BI / GND)", BORNIER3, (395, 127),
            {"1": "RUBAN_DI", "2": "GND", "3": "GND"}); P["J8"] = (5.715, 48.26, 270)
s.composant("J7", "Connector:Screw_Terminal_01x03", "DS18B20 (3V3 / DQ / GND)", BORNIER3, (395, 160),
            {"1": "+3V3", "2": "DS18_DQ", "3": "GND"}); P["J7"] = (5.715, 68.58, 270)
R("R8", "4k7", (370, 160), "DS18_DQ", "+3V3", (16.51, 73.66, 0), empreinte=R_DEBOUT)   # v0.3 : debout, R1 a sa place
for i, (led, rr, net, val, couleur) in enumerate((("LED1", "R11", "LED_LINK", "180", "bleue - Link GPIO38"),
                                                    ("LED2", "R12", "LED_ETAT", "560", "verte - Led1 GPIO39"),
                                                    ("LED3", "R13", "+5V", "2k2", "rouge - 5 V present"))):
    y = 190 + i * 15
    # v0.2 : resistances DEBOUT entre les LED et l'ADS1115 (couchees, elles passaient dessous)
    R(rr, val, (330, y), net, f"{led}_A", (59.69 + 6.35 * i, 48.36, 0), empreinte=R_DEBOUT)
    s.composant(led, "Device:LED", f"LED 3 mm {couleur}", "LED_THT:LED_D3.0mm", (355, y),
                {"1": "GND", "2": f"{led}_A"})
    P[led] = (59.69 + 6.35 * i, 44.45, 0)   # sous J3, pres de GPIO38/39 ; pas de 6,35 pour les R debout
s.composant("J9", "Connector_Generic:Conn_01x04", "Extension I2C (3V3 GND SCL SDA)",
            "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", (330.2, 250),
            {"1": "+3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA"}); P["J9"] = (48.26, 5.08, 90)
s.composant("J14", "Connector_Generic:Conn_01x06", "Extension GPIO (3V3 GND 7 15 16 17)",
            "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", (375, 250),
            {"1": "+3V3", "2": "GND", "3": "BTN_RUBAN", "4": "GPIO15", "5": "GPIO16", "6": "GPIO17"})
P["J14"] = (60.96, 5.08, 90)
# Bouton du ruban sur GPIO7 (v0.2, 2026-10-14) : cable > 1 m -> rappel externe 10 k vers 3V3 (en
# plus du rappel interne ~45 k, trop faible face aux parasites) et 100 nF vers 0V, tau = 1 ms.
# Places entre J14 et le DevKit : C9 a l'aplomb de IO7 (A1 broche 7), R14 de 3V3 (A1 broche 2).
R("R14", "10k", (396.24, 203.2), "+3V3", "GPIO7", (92.71, 8.89, 180))
# R15 1 k serie (electronique_tasmota.md, entree TOR contact sec) : limite la decharge de C9 dans le
# cable (~1 A crete sans elle) et protege IO7 d'une decharge arrivant par le cable ; bas = 0,36 V.
R("R15", "1k", (375.92, 213.36), "BTN_RUBAN", "GPIO7", (66.04, 9.4, 0), empreinte=R_DEBOUT)
C("C9", "100nF", (396.24, 223.52), "GPIO7", "GND", (80.01, 8.89, 180))
# v0.3 : bornier a vis pour le bouton (contact sec, cable > 1 m), en parallele de J14 broche 3
s.composant("J15", "Connector:Screw_Terminal_01x02", "Bouton du ruban (BTN / GND)", BORNIER2, (375, 265),
            {"1": "BTN_RUBAN", "2": "GND"}); P["J15"] = (5.715, 30.48, 270)
s.texte("J15 (ou J14 broche 3, GPIO7) = bouton poussoir du ruban vers 0V.\n"
        "R14 rappel 10 k + R15 1 k serie + C9 100 nF : cable > 1 m.", (330, 232))
for i, (x, y) in enumerate(((3.81, 3.81), (96.19, 3.81), (3.81, 96.19), (96.19, 96.19))):
    s.composant(f"H{i + 1}", "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3",
                (330 + i * 12, 275), {}, bom=False)
    P[f"H{i + 1}"] = (x, y, 0)

# Masses locales routees EN PREMIER (v0.2) : sinon les signaux les enferment dans une poche des
# deux plans - cathode de LED2 (pistes RS485 / LED), et bande J14-DevKit ou C9 et J14.2 formaient
# un ilot sans lien avec la masse (le filtre du bouton n'avait plus de 0V). A1.22 = GND du DevKit.
NETS_ROUTAGE = ([("GND", 0.5, ("LED1", "LED2", "LED3")), ("GND", 0.5, ("J14", "C9", "A1.22")),
                 ("+12V_IN", 1.0), ("+12V_F", 1.0), ("+12V", 1.0), ("+5V", 0.8), ("+5V_DEVKIT", 0.8),
                 ("+3V3", 0.6), ("+12V_CAPT", 0.5)]
                + [(n, 0.35) for n in ("I2C_SCL", "I2C_SDA", "RS485_TX", "RS485_RX", "WS_DATA_3V3",
                                       "WS_DATA_5V", "RUBAN_DI", "DS18_DQ", "LED_LINK", "LED_ETAT",
                                       "LED1_A", "LED2_A", "LED3_A", "GPIO7", "BTN_RUBAN", "GPIO15", "GPIO16", "GPIO17")]
                + [(f"AIN{k}", 0.35) for k in range(4)] + [(f"IN{k}", 0.5) for k in range(4)])
# GND n'est pas route en pistes : plans de masse sur les 2 faces + vias de couture.
INTERDITS = [(96.0, 6.5, L, 46.0)]    # sous l'antenne du DevKit : ni cuivre ni plan de masse
ZONE_SIGNATURE = (44.5, 21.0, 75.5, 32.5)   # verso, sous le DevKit : pas de via de couture


def silk(c):
    t = c.texte
    t(f"CUVE - ModBus  v{REV}", 31.5, 2.6, 1.5, 0.25)
    for x, y, txt in ((13.0, 15.24, "+12V"), (12.7, 20.32, "0V"),           # J1
                      (12.7, 48.26, "DI"), (12.7, 53.34, "BI"), (12.7, 58.42, "0V"),   # J8
                      (12.7, 68.58, "3V3"), (12.7, 73.66, "DQ"), (12.7, 78.74, "0V"),   # J7
                      (13.3, 30.48, "BTN"), (12.7, 35.56, "0V")):                       # J15
        t(txt, x, y, 1.0, 0.15)
    t("ENTRÉE 12V", 6.6, 10.9, 1.0, 0.15)
    t("BOUTON", 5.9, 26.1, 1.0, 0.15)
    t("RUBAN", 5.1, 43.9, 1.0, 0.15)
    t("DS18B20", 5.6, 64.1, 1.0, 0.15)
    for k, x in enumerate(BORNES.values()):
        for dx, txt in ((-10.16, f"A{k}"), (-5.08, "0V"), (0, "+12")):
            t(txt, x + dx, 86.6, 1.0, 0.15)
        t("0-10V" if k < 2 else "4-20mA", x - 9.5, 78.74, 1.0, 0.15, rot=90)   # a gauche de la voie (repere de R entre ses 2 R)
    t("ANTENNE", 98.2, 26.0, 1.0, 0.15, rot=90)
    t("RS485 TX=GPIO5 RX=GPIO4", 81.3, 58.0, 1.0, 0.15, rot=90)
    t("ADS1115 (3,3 V)", 62.2, 62.6, 1.0, 0.15)
    for i, txt in enumerate(("LIEN", "ÉTAT", "5V")):       # remplacent les reperes LED1-3
        t(txt, 60.96 + 6.35 * i, 41.85, 1.0, 0.15)
    t("I2C : 3V3 0V SCL SDA", 52.0, 9.2, 1.0, 0.15)
    t("GPIO : 3V3 0V 7 15 16 17", 63.0, 2.0, 1.0, 0.15)
    t("7 = BOUTON RUBAN", 85.0, 4.6, 1.0, 0.15)
    t("Carte cuve - fork Tasmota", 60.0, 35.0, 1.2, 0.18, couche="B.SilkS")
    c.empreinte_libre(SIGNATURE, "Signature_Auteur_30mm_Dos", 60.0, 26.67, ref="LOGO1")
    c.reperes(masques=("J1", "J7", "J8", "J10", "J11", "J12", "J13", "J15", "J5", "H1", "H2", "H3", "H4", "LED1", "LED2", "LED3", "J4"),
              deplaces={**{f"C{5 + k}": (x + 2.4, 69.85, 0) for k, x in enumerate(BORNES.values())},
                        # v0.2 : reperes des R debout juste dessous (caches par l'ADS1115 une fois monte,
                        # lisibles au soudage) ; R7 sous son corps (a droite, il touchait U1)
                        **{f"R{11 + i}": (59.69 + 6.35 * i + 1.27, 51.4, 0) for i in range(3)},
                        "R7": (26.67, 65.8, 0), "C2": (44.5, 65.0, 0),
                        "C3": (29.6, 66.95, 0), "F2": (19.6, 8.5, 0), "R15": (67.31, 11.7, 0)})
    # DevKit, ADS1115 et RS485 XY-017 : contour et modele 3D portes par leurs empreintes Modules_Tasmota.


def main():
    s.ecrit(ICI / f"{PROJET}.kicad_sch")   # tables de bibliotheques comprises (skill en relatif)
    c = Carte(s)
    c.regles()
    c.contour(L, H)
    c.place(P)
    for ref in ("F1", "F2"):            # piege 37 : vider la liste puis ajouter
        fp = c.empreintes[ref]
        fp.Models().clear()
        m = c.pcbnew.FP_3DMODEL()
        m.m_Filename = MODELE_PTC
        fp.Add3DModel(m)
    for z in INTERDITS:
        c.interdiction(z)
    silk(c)
    if "--sans-routage" not in sys.argv:
        from routeur_grille import Routeur
        r = Routeur(c, L, H, interdits=INTERDITS)
        echecs = r.route_tout(NETS_ROUTAGE)
        if echecs:
            print("NON ROUTES :", echecs)
        # Masse en pistes APRES tous les signaux (echec tolere : le plan prend le relais)
        if not r.route_net("GND", 0.5):
            print("GND : arbre incomplet, complete par les plans de masse")
        # Masse de la boucle d'entree / sortie de U1 (U1.2, C3.2, C1-, C2-) : les plans y sont troues
        r.vias_pres("GND", [(34.94, 63.3), (34.9, 66.95), (43.3, 53.0), (45.5, 61.5)])
        r.coutures("GND", exclus=[ZONE_SIGNATURE])
    for couche in ("F.Cu", "B.Cu"):
        c.zone("GND", couche, (0, 0, L, H))
    c.enregistre(ICI / f"{PROJET}.kicad_pcb")
    print("ecrit :", ICI / f"{PROJET}.kicad_sch", "et .kicad_pcb")


if __name__ == "__main__":
    main()
