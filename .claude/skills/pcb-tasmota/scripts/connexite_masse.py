"""Connexite de la masse d'un .kicad_pcb REMPLI (apres Carte.enregistre) : morceaux de plan
GND (F/B), vias, pastilles traversantes et pistes GND reunis en groupes ; affiche chaque groupe
hors du groupe principal, avec ses positions en repere carte (origine 100 ; 50).

Pourquoi : un « non connecte » Zone [GND] F.Cu | Zone [GND] B.Cu du DRC ne donne AUCUNE
position (kicad-cli, JSON comme rapport texte), et pcbnew.LoadBoard plante (piege 1).
Cuve v0.2 (2026-10-14) : a trouve C9 + J14.2 enfermes entre J9/J14 et le DevKit.

    python connexite_masse.py <carte>.kicad_pcb        (Python ordinaire, ~1-3 min)
Code de sortie : 0 = un seul groupe, 1 = masse en plusieurs morceaux.
Approximations : pastille reliee a un morceau si son bord est a moins de 0,6 mm du contour
(rayons thermiques) ; pistes reliees bout a bout. Le DRC reste la reference."""
import math
import re
import sys

t = open(sys.argv[1], encoding="utf-8").read()
OX, OY = 100.0, 50.0
TOL = 0.05


def dedans(px, py, poly):
    c, n = False, len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > py) != (y1 > py) and px < (x1 - x0) * (py - y0) / (y1 - y0) + x0:
            c = not c
    return c


def dist_seg(px, py, a, b, c, d):
    dx, dy = c - a, d - b
    l2 = dx * dx + dy * dy
    u = 0 if l2 == 0 else max(0, min(1, ((px - a) * dx + (py - b) * dy) / l2))
    return math.hypot(px - a - u * dx, py - b - u * dy)


def pres_bord(px, py, r, poly):
    n = len(poly)
    return any(dist_seg(px, py, *poly[i], *poly[(i + 1) % n]) <= r for i in range(n))


# Morceaux de plan (zone GND)
frags = []
for m in re.finditer(r'\(filled_polygon\s+\(layer "([FB])\.Cu"\)\s+\(pts(.*?)\)\s*\)', t, re.S):
    pts = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", m.group(2))]
    frags.append((m.group(1), pts))
# Vias GND
vias = [(float(m.group(1)), float(m.group(2)), float(m.group(3)) / 2) for m in
        re.finditer(r'\(via\s+\(at ([-\d.]+) ([-\d.]+)\)\s+\(size ([\d.]+)\)(?:(?!\(via ).)*?\(net (?:\d+ )?"?GND"?\)', t, re.S)]
# Pistes GND
segs = [(m.group(6)[0], float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)) / 2)
        for m in re.finditer(r'\(segment\s+\(start ([-\d.]+) ([-\d.]+)\)\s+\(end ([-\d.]+) ([-\d.]+)\)\s+\(width ([\d.]+)\)\s+'
                             r'\(layer "([FB])\.Cu"\)\s+\(net (?:\d+ )?"?GND"?\)', t)]
# Pastilles GND traversantes (position absolue, rayon)
pads = []
for fp in re.finditer(r"\n\t\(footprint .*?\n\t\)", t, re.S):
    b = fp.group(0)
    at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", b)
    x0, y0, rot = float(at.group(1)), float(at.group(2)), math.radians(float(at.group(3) or 0))
    ref = re.search(r'\(property "Reference" "([^"]+)"', b).group(1)
    for pm in re.finditer(r'\(pad "([^"]*)"(.*?)\n\t\t\)', b, re.S):
        corps = pm.group(2)
        if '"GND"' not in corps:
            continue
        a = re.search(r"\(at ([-\d.]+) ([-\d.]+)", corps)
        sz = re.search(r"\(size ([\d.]+) ([\d.]+)\)", corps)
        px, py = float(a.group(1)), float(a.group(2))
        pads.append((f"{ref}.{pm.group(1)}", x0 + px * math.cos(rot) + py * math.sin(rot),
                     y0 - px * math.sin(rot) + py * math.cos(rot), max(float(sz.group(1)), float(sz.group(2))) / 2))

# Union-find
noeuds = ([f"zone{f[0]}#{k}" for k, f in enumerate(frags)] + [f"via#{k}" for k in range(len(vias))]
          + [p[0] for p in pads] + [f"piste{s[0]}#{k}" for k, s in enumerate(segs)])
parent = {n: n for n in noeuds}


def racine(n):
    while parent[n] != n:
        parent[n] = parent[parent[n]]
        n = parent[n]
    return n


def unit(a, b):
    parent[racine(a)] = racine(b)


for k, (face, poly) in enumerate(frags):
    for i, (x, y, r) in enumerate(vias):
        if dedans(x, y, poly) or pres_bord(x, y, r + 0.6, poly):
            unit(f"zone{face}#{k}", f"via#{i}")
    for nom, x, y, r in pads:                 # rayons thermiques : le bord du trou touche la pastille
        if pres_bord(x, y, r + 0.6, poly) and not dedans(x, y, poly) or dedans(x, y, poly):
            unit(f"zone{face}#{k}", nom)
    for j, (fs, a, b, c, d, w) in enumerate(segs):
        if fs == face and (dedans(a, b, poly) or dedans(c, d, poly)):
            unit(f"zone{face}#{k}", f"piste{fs}#{j}")
for j, (fs, a, b, c, d, w) in enumerate(segs):
    for nom, x, y, r in pads:
        if min(math.hypot(x - a, y - b), math.hypot(x - c, y - d)) <= r + TOL:
            unit(nom, f"piste{fs}#{j}")
    for i, (x, y, r) in enumerate(vias):
        if min(math.hypot(x - a, y - b), math.hypot(x - c, y - d)) <= r + TOL:
            unit(f"via#{i}", f"piste{fs}#{j}")
    for i, (fs2, a2, b2, c2, d2, w2) in enumerate(segs):
        if i > j and fs2 == fs and min(math.hypot(a - a2, b - b2), math.hypot(a - c2, b - d2),
                                       math.hypot(c - a2, d - b2), math.hypot(c - c2, d - d2)) <= TOL:
            unit(f"piste{fs}#{j}", f"piste{fs2}#{i}")

groupes = {}
for n in noeuds:
    groupes.setdefault(racine(n), []).append(n)
groupes = sorted(groupes.values(), key=len, reverse=True)
print(f"{len(frags)} morceaux, {len(vias)} vias, {len(pads)} pastilles, {len(segs)} pistes GND -> {len(groupes)} groupe(s)")
for g in groupes[1:]:
    desc = []
    for n in g:
        if n.startswith("zone"):
            face, k = n[4], int(n.split("#")[1])
            xs = [p[0] - OX for p in frags[k][1]]; ys = [p[1] - OY for p in frags[k][1]]
            desc.append(f"{n} [x {min(xs):.1f}..{max(xs):.1f} y {min(ys):.1f}..{max(ys):.1f}]")
        elif n.startswith("via#"):
            x, y, r = vias[int(n[4:])]
            desc.append(f"{n} ({x - OX:.2f};{y - OY:.2f})")
        elif n.startswith("piste"):
            fs, a, b, c, d, w = segs[int(n.split("#")[1])]
            desc.append(f"{n} ({a - OX:.2f};{b - OY:.2f})->({c - OX:.2f};{d - OY:.2f})")
        else:
            desc.append(n)
    print("GROUPE ISOLE :", "; ".join(desc))
sys.exit(0 if len(groupes) == 1 else 1)
