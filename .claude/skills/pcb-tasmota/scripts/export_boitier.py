"""Exporte ce qu'il faut pour dessiner ou choisir le boitier d'une carte KiCad.

Usage (Python systeme ou de KiCad) :
  python export_boitier.py <carte.kicad_pcb> [--sortie DIR] [--sans-step]

Produit dans <dossier de la carte>/boitier/ (ou --sortie) :
  <carte>.step          modele 3D complet (carte + composants + modules Modules_Tasmota),
                        a ouvrir dans FreeCAD / Fusion / Onshape pour mesurer les hauteurs ;
  <carte>_contour.dxf   contour de la carte (calque CONTOUR), trous de fixation (TROUS),
                        emprise des connecteurs du bord (CONNECTEURS), en mm, origine = coin
                        bas gauche de la carte, y vers le haut (convention DAO) ;
  <carte>_cotes.md      cotes utiles : dimensions, trous (centre, diametre), connecteurs au
                        bord (cote, position, debord, sens d'ouverture des borniers).

Controle : chaque modele 3D des empreintes Modules_Tasmota doit se retrouver dans le STEP
(piege 35 : un modele introuvable est ignore SANS erreur par kicad-cli).

Codes de sortie : 0 = tout produit et verifie ; 2 = kicad-cli absent, export en echec ou
modele 3D manquant dans le STEP.
"""
import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kicad_gen import KICAD, enfants, parse  # noqa: E402

KICAD_CLI = KICAD / "bin" / "kicad-cli.exe"
PRES_DU_BORD = 3.0        # mm : un connecteur a moins de 3 mm du bord est « au bord »
# Borniers Phoenix MKDS horizontaux : ouverture des fils selon la rotation (piege 10)
OUVERTURE_MKDS = {0: "vers le bas", 90: "vers la droite", 180: "vers le haut", 270: "vers la gauche"}


def val(noeud, tete, defaut=None):
    e = enfants(noeud, tete)
    return e[0][1:] if e else defaut


def nombre(x):
    return float(x)


# ------------------------------------------------------------ lecture de la carte
def contour(pcb):
    """Elements de Edge.Cuts : ('L', p1, p2) | ('A', debut, milieu, fin) | ('C', centre, r)."""
    elems = []
    for e in pcb:
        if not (isinstance(e, list) and e and e[0] in ("gr_line", "gr_arc", "gr_rect", "gr_circle")):
            continue
        if val(e, "layer", [""])[0] != "Edge.Cuts":
            continue
        p = {k: tuple(map(nombre, val(e, k))) for k in ("start", "mid", "end", "center") if val(e, k)}
        if e[0] == "gr_line":
            elems.append(("L", p["start"], p["end"]))
        elif e[0] == "gr_arc":
            elems.append(("A", p["start"], p["mid"], p["end"]))
        elif e[0] == "gr_rect":
            (x0, y0), (x1, y1) = p["start"], p["end"]
            coins = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            elems += [("L", coins[i], coins[(i + 1) % 4]) for i in range(4)]
        else:
            c = p["center"]
            elems.append(("C", c, math.dist(c, p["end"])))
    return elems


def boite(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def transforme(at, lx, ly):
    """Point local d'une empreinte -> repere de la carte (KiCad : y vers le bas)."""
    x, y, r = at
    a = math.radians(r)
    return x + lx * math.cos(a) + ly * math.sin(a), y - lx * math.sin(a) + ly * math.cos(a)


def empreintes(pcb):
    for fp in enfants(pcb, "footprint"):
        at = list(map(nombre, val(fp, "at")))
        at = (at[0], at[1], at[2] if len(at) > 2 else 0.0)
        props = {p[1]: p[2] for p in enfants(fp, "property") if len(p) > 2}
        yield fp, str(fp[1]), at, props.get("Reference", "?"), props.get("Value", "")


def trous(pcb):
    """Trous non metallises (fixations) : (ref, x, y, diametre)."""
    res = []
    for fp, lib, at, ref, _ in empreintes(pcb):
        for pad in enfants(fp, "pad"):
            if len(pad) > 2 and pad[2] == "np_thru_hole":
                lx, ly = map(nombre, val(pad, "at")[:2])
                x, y = transforme(at, lx, ly)
                res.append((ref, x, y, nombre(val(pad, "drill")[0])))
    return res


def courtyard(fp, at):
    pts = []
    for g in fp:
        if isinstance(g, list) and g and g[0] in ("fp_line", "fp_rect", "fp_poly") \
                and val(g, "layer", [""])[0] == "F.CrtYd":
            if g[0] == "fp_poly":
                loc = [tuple(map(nombre, xy[1:3])) for xy in enfants(enfants(g, "pts")[0], "xy")]
            else:
                (x0, y0), (x1, y1) = (tuple(map(nombre, val(g, k))) for k in ("start", "end"))
                loc = [(x0, y0), (x1, y1), (x0, y1), (x1, y0)]
            pts += [transforme(at, *p) for p in loc]
    return boite(pts) if pts else None


def connecteurs_au_bord(pcb, carte):
    x0, y0, x1, y1 = carte
    res = []
    for fp, lib, at, ref, valeur in empreintes(pcb):
        if not (lib.startswith("TerminalBlock") or lib.startswith("Modules_Tasmota:ESP32")
                or "USB" in lib):
            continue
        b = courtyard(fp, at)
        if not b:
            continue
        cotes = {"gauche": b[0] - x0, "droit": x1 - b[2], "haut": b[1] - y0, "bas": y1 - b[3]}
        cote, d = min(cotes.items(), key=lambda kv: kv[1])
        if d > PRES_DU_BORD:
            continue
        sens = OUVERTURE_MKDS.get(round(at[2]) % 360, "?") if lib.startswith("TerminalBlock") \
            else ("antenne au bord " + cote + " (USB a l'oppose)" if "ESP32" in lib else "")
        res.append(dict(ref=ref, valeur=valeur, lib=lib, boite=b, cote=cote, ecart=d, sens=sens))
    return sorted(res, key=lambda c: (c["cote"], c["boite"][0], c["boite"][1]))


# ------------------------------------------------------------ DXF (R12, mm, y vers le haut)
class Dxf:
    def __init__(self, origine):
        self.ox, self.oy = origine          # coin bas gauche de la carte, repere KiCad
        self.lignes = []

    def p(self, x, y):
        return x - self.ox, self.oy - y

    def _ent(self, typ, calque, codes):
        self.lignes += ["0", typ, "8", calque] + [str(c) for c in codes]

    def ligne(self, calque, a, b):
        (xa, ya), (xb, yb) = self.p(*a), self.p(*b)
        self._ent("LINE", calque, [10, f"{xa:.4f}", 20, f"{ya:.4f}", 11, f"{xb:.4f}", 21, f"{yb:.4f}"])

    def cercle(self, calque, c, r):
        x, y = self.p(*c)
        self._ent("CIRCLE", calque, [10, f"{x:.4f}", 20, f"{y:.4f}", 40, f"{r:.4f}"])

    def arc(self, calque, debut, milieu, fin):
        (ax, ay), (bx, by), (cx, cy) = (self.p(*q) for q in (debut, milieu, fin))
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
        uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
        ang = [math.degrees(math.atan2(y - uy, x - ux)) % 360 for x, y in ((ax, ay), (bx, by), (cx, cy))]
        a0, am, a1 = ang
        if (am - a0) % 360 > (a1 - a0) % 360:   # le milieu n'est pas sur le trajet a0 -> a1 (sens direct)
            a0, a1 = a1, a0
        self._ent("ARC", calque, [10, f"{ux:.4f}", 20, f"{uy:.4f}", 40, f"{math.dist((ux, uy), (ax, ay)):.4f}",
                                  50, f"{a0:.4f}", 51, f"{a1:.4f}"])

    def rect(self, calque, b):
        x0, y0, x1, y1 = b
        coins = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for i in range(4):
            self.ligne(calque, coins[i], coins[(i + 1) % 4])

    def texte(self, calque, pos, txt, h=1.5):
        x, y = self.p(*pos)
        self._ent("TEXT", calque, [10, f"{x:.4f}", 20, f"{y:.4f}", 40, h, 1, txt])

    def ecrit(self, chemin):
        Path(chemin).write_text("\n".join(["0", "SECTION", "2", "ENTITIES"] + self.lignes
                                          + ["0", "ENDSEC", "0", "EOF"]) + "\n", encoding="ascii", errors="replace")


# ------------------------------------------------------------ STEP
def exporte_step(pcb_chemin, sortie, pcb):
    step = sortie / (pcb_chemin.stem + ".step")
    r = subprocess.run([str(KICAD_CLI), "pcb", "export", "step", "--force", "--subst-models",
                        "-o", str(step), str(pcb_chemin)], capture_output=True)
    if r.returncode != 0 or not step.exists() or step.stat().st_size == 0:
        return step, [f"export STEP en echec (code {r.returncode})"]
    texte = step.read_text(encoding="latin-1", errors="replace")
    attendus = set()
    for fp, *_ in empreintes(pcb):
        for m in enfants(fp, "model"):
            if "PCB_TASMOTA_3D" in m[1]:
                attendus.add(Path(m[1]).stem)
    manquants = [n for n in sorted(attendus) if f"PRODUCT('{n}'" not in texte]
    return step, [f"modele 3D absent du STEP : {n} (variable PCB_TASMOTA_3D du .kicad_pro ?)" for n in manquants]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pcb", type=Path)
    ap.add_argument("--sortie", type=Path)
    ap.add_argument("--sans-step", action="store_true", help="ne produit que le DXF et les cotes")
    a = ap.parse_args()
    if not a.pcb.exists():
        print(f"Carte introuvable : {a.pcb}")
        return 2
    sortie = a.sortie or a.pcb.parent / "boitier"
    sortie.mkdir(parents=True, exist_ok=True)
    pcb = parse(a.pcb.read_text(encoding="utf-8"))[0]

    elems = contour(pcb)
    pts = [p for e in elems for p in (e[1:] if e[0] != "C" else [])]
    if not pts:
        print("Aucun contour Edge.Cuts : rien a exporter")
        return 2
    carte = boite(pts)
    x0, y0, x1, y1 = carte
    les_trous = trous(pcb)
    connecteurs = connecteurs_au_bord(pcb, carte)

    dxf = Dxf((x0, y1))
    for e in elems:
        {"L": lambda e: dxf.ligne("CONTOUR", e[1], e[2]), "A": lambda e: dxf.arc("CONTOUR", *e[1:]),
         "C": lambda e: dxf.cercle("CONTOUR", e[1], e[2])}[e[0]](e)
    for ref, x, y, d in les_trous:
        dxf.cercle("TROUS", (x, y), d / 2)
    for c in connecteurs:
        dxf.rect("CONNECTEURS", c["boite"])
        dxf.texte("CONNECTEURS", (c["boite"][0], c["boite"][1] - 0.5), c["ref"])
    dxf_chemin = sortie / f"{a.pcb.stem}_contour.dxf"
    dxf.ecrit(dxf_chemin)

    loc = lambda x, y: f"({x - x0:.2f} ; {y1 - y:.2f})"      # noqa: E731 - repere DAO
    md = [f"# Cotes pour le boitier - {a.pcb.stem}", "",
          "Repère : origine au coin **bas gauche** de la carte, x vers la droite, y vers le haut (mm), "
          "comme dans le DXF.", "",
          f"- Carte : **{x1 - x0:.2f} × {y1 - y0:.2f} mm**, épaisseur 1,6 mm (FR-4 standard).",
          "- Hauteur des composants et modules : la mesurer dans le STEP (cotes des modules « à mesurer » "
          "tant qu'elles ne sont pas relevées, voir `assets/generer_modules.py`).", "",
          "## Trous de fixation", "", "| Réf. | Centre | Diamètre |", "|---|---|---|"]
    md += [f"| {r} | {loc(x, y)} | {d:.2f} |" for r, x, y, d in les_trous] or ["| - | aucun | |"]
    md += ["", f"## Connecteurs au bord (à moins de {PRES_DU_BORD:g} mm)", "",
           "| Réf. | Valeur | Côté | Emprise (coin bas gauche → haut droit) | Écart au bord | Ouverture |",
           "|---|---|---|---|---|---|"]
    for c in connecteurs:
        bx0, by0, bx1, by1 = c["boite"]
        ecart = f"{c['ecart']:.2f}" if c["ecart"] >= 0 else f"**déborde de {-c['ecart']:.2f}**"
        md.append(f"| {c['ref']} | {c['valeur']} | {c['cote']} | {loc(bx0, by1)} → {loc(bx1, by0)} | "
                  f"{ecart} | {c['sens']} |")
    md_chemin = sortie / f"{a.pcb.stem}_cotes.md"

    erreurs = []
    produits = [dxf_chemin, md_chemin]
    if not a.sans_step:
        if not KICAD_CLI.exists():
            erreurs.append(f"kicad-cli introuvable : {KICAD_CLI}")
        else:
            step, err = exporte_step(a.pcb, sortie, pcb)
            erreurs += err
            produits.insert(0, step)
    md_chemin.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print("\nProduit :")
    for p in produits:
        print(f"  {p}")
    for e in erreurs:
        print(f"ERREUR : {e}")
    return 2 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
