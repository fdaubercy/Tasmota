#!/usr/bin/env python3
"""Revue de placement KiCad 10 : rendus 3D, planche, page HTML, tableau des composants.

Usage :
  python revue_3d.py <carte.kicad_pcb> [--sortie DIR] [--rapide | --qualite]
         [--rasante] [--svg-cuivre] [--jobs N] [--largeur PX]

En UNE commande, tout ce qu'il faut pour revoir un placement avec l'utilisateur :
  1. Rendus `kicad-cli pcb render` lancés EN PARALLELE (3-4 à la fois) :
       dessus, dessous, iso (perspective, --rotate "-50,0,20"),
       dos zoomé (orientation des borniers, piège 10), et avec --rasante
       une vue rasante côté connecteurs (--side front, perspective).
  2. <carte>_planche.png : planche unique assemblant les vues, titres en
     français, nom de la carte et date (nécessite Pillow ; sans lui, la
     planche est sautée avec un avertissement, le reste est produit).
  3. <carte>_revue.html : page autonome (images en data: URI, aucune
     dépendance externe) avec les vues et le tableau des composants
     (référence, valeur, empreinte, x/y en mm, rotation, face) lu dans le
     .kicad_pcb par analyse du S-expression (pas besoin de pcbnew).
  4. Avec --svg-cuivre : SVG des couches cuivre (F.Cu, B.Cu, Edge.Cuts) par
     `kicad-cli pcb export svg` : le rendu 3D ne montre pas les pistes sous
     les modules.

Options :
  --rapide    qualité `basic` (défaut, ~20-30 s par vue).
  --qualite   qualité `high` (ombres, plus lent : à réserver à la version finale).
  --jobs N    nombre de rendus simultanés (défaut 4 ; 1 = séquentiel).
  --largeur   largeur des vues en pixels (défaut 1400 ; hauteur = largeur x 0,75).

Sortie par défaut : <dossier de la carte>/revue_3d/. Les chemins produits sont
imprimés à la fin. Code 0 = tout produit, 2 = rendu raté, kicad-cli ou fichier
manquant, image absente ou vide. La carte n'est jamais modifiée.
"""
import argparse, base64, datetime, html, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

# (clé, titre français, arguments de kicad-cli pcb render, zoom/taille particuliers)
VUES = [
    ("dessus", "Dessus (face composants)", ["--side", "top"]),
    ("dessous", "Dessous", ["--side", "bottom"]),
    ("iso", "Vue d'ensemble (perspective)", ["--rotate", "-50,0,20", "--perspective"]),
    ("dos", "De dos, zoomée (ouverture des borniers)", ["--side", "back", "--zoom", "2"]),
]
VUE_RASANTE = ("rasante", "Rasante côté connecteurs",
               ["--side", "front", "--perspective", "--zoom", "1.3"])


class ErreurRevue(Exception):
    pass


def exige(chemin):
    """Le fichier doit exister et ne pas être vide."""
    p = Path(chemin)
    if not p.is_file() or p.stat().st_size == 0:
        raise ErreurRevue("fichier attendu absent ou vide : %s" % p)
    return p


def lancer(nom, args):
    """Une commande kicad-cli ; renvoie (nom, durée s, message d'erreur ou '')."""
    t0 = time.time()
    r = subprocess.run([KICAD_CLI] + [str(a) for a in args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    erreur = ""
    if r.returncode != 0:   # messages localisés : jamais analysés, juste affichés
        erreur = "code %d : %s" % (r.returncode, (r.stdout + r.stderr).strip()[-400:])
    return nom, time.time() - t0, erreur


# --- lecture du .kicad_pcb (S-expression) -------------------------------------------
def tokens(texte):
    i, n = 0, len(texte)
    while i < n:
        c = texte[i]
        if c in " \t\r\n":
            i += 1
        elif c in "()":
            yield c
            i += 1
        elif c == '"':
            j = i + 1
            while texte[j] != '"':
                j += 2 if texte[j] == "\\" else 1
            yield ("s", texte[i + 1:j])
            i = j + 1
        else:
            j = i
            while j < n and texte[j] not in ' \t\r\n()"':
                j += 1
            yield texte[i:j]
            i = j


def sexp(texte):
    """Arbre imbriqué (listes) ; les chaînes entre guillemets sont des str."""
    pile, cour = [], []
    for t in tokens(texte):
        if t == "(":
            pile.append(cour)
            cour = []
        elif t == ")":
            fini, cour = cour, pile.pop()
            cour.append(fini)
        else:
            cour.append(t[1] if isinstance(t, tuple) else t)
    return cour[0]


def composants(pcb):
    """Liste de dicts (ref, valeur, empreinte, x, y, rot, face) triée par référence."""
    arbre = sexp(Path(pcb).read_text(encoding="utf-8", errors="replace"))
    res = []
    for fp in arbre:
        if not (isinstance(fp, list) and fp and fp[0] == "footprint"):
            continue
        d = {"ref": "?", "val": "", "fp": fp[1].split(":")[-1], "x": 0.0, "y": 0.0,
             "rot": 0.0, "face": "?"}
        for e in fp[2:]:
            if not (isinstance(e, list) and e):
                continue
            if e[0] == "layer":
                d["face"] = "dessus" if e[1] == "F.Cu" else "dessous"
            elif e[0] == "at":
                d["x"], d["y"] = float(e[1]), float(e[2])
                d["rot"] = float(e[3]) if len(e) > 3 else 0.0
            elif e[0] == "property" and e[1] == "Reference":
                d["ref"] = e[2]
            elif e[0] == "property" and e[1] == "Value":
                d["val"] = e[2]
        res.append(d)

    def cle(c):
        lettres = "".join(ch for ch in c["ref"] if not ch.isdigit())
        chiffres = "".join(ch for ch in c["ref"] if ch.isdigit())
        return (lettres, int(chiffres) if chiffres else 0)
    return sorted(res, key=cle)


# --- planche PNG --------------------------------------------------------------------
def planche(nom, vues, dest, date):
    """Assemble les vues en grille 2 colonnes ; renvoie False si Pillow manque."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    def police(taille):
        for f in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(f, taille)
            except OSError:
                pass
        return ImageFont.load_default()

    imgs = [(t, Image.open(p).convert("RGB")) for t, p in vues]
    cw = max(i.width for _, i in imgs)
    ch = max(i.height for _, i in imgs)
    cols, marge, bandeau, titre_h = 2, 24, 90, 44
    lignes = (len(imgs) + cols - 1) // cols
    W = cols * cw + (cols + 1) * marge
    H = bandeau + lignes * (ch + titre_h + marge) + marge
    pl = Image.new("RGB", (W, H), (245, 245, 242))
    dr = ImageDraw.Draw(pl)
    dr.rectangle([0, 0, W, bandeau], fill=(30, 60, 50))
    dr.text((marge, 14), "Revue de placement : %s" % nom, font=police(40), fill="white")
    dr.text((marge, 58), "Rendus KiCad 10 - %s" % date, font=police(22), fill=(200, 220, 210))
    for k, (titre, im) in enumerate(imgs):
        x = marge + (k % cols) * (cw + marge)
        y = bandeau + marge + (k // cols) * (ch + titre_h + marge)
        dr.text((x, y), titre, font=police(26), fill=(30, 30, 30))
        fond = Image.new("RGB", (cw, ch), (255, 255, 255))
        fond.paste(im, ((cw - im.width) // 2, (ch - im.height) // 2))
        pl.paste(fond, (x, y + titre_h))
    pl.save(dest)
    return True


# --- page HTML autonome ---------------------------------------------------------------
def page_html(nom, vues, comps, dest, date, svgs):
    def uri(p):
        mime = "image/svg+xml" if str(p).endswith(".svg") else "image/png"
        return "data:%s;base64,%s" % (mime, base64.b64encode(Path(p).read_bytes()).decode())
    fig = "".join('<figure><figcaption>%s</figcaption><img src="%s" alt="%s"></figure>'
                  % (html.escape(t), uri(p), html.escape(t)) for t, p in vues)
    fig_svg = "".join('<figure><figcaption>%s</figcaption><img src="%s" alt="%s"></figure>'
                      % (html.escape(t), uri(p), html.escape(t)) for t, p in svgs)
    lignes = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td class=n>%.2f</td><td class=n>%.2f</td>"
        "<td class=n>%g</td><td>%s</td></tr>" % (
            html.escape(c["ref"]), html.escape(c["val"]), html.escape(c["fp"]),
            c["x"], c["y"], c["rot"], c["face"]) for c in comps)
    doc = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revue de placement - %(nom)s</title><style>
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f5f5f2;color:#222}
header{background:#1e3c32;color:#fff;padding:16px 24px}h1{margin:0;font-size:1.6em}
header p{margin:4px 0 0;color:#c8dcd2}main{padding:16px 24px}
.grille{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}
figure{margin:0;background:#fff;border:1px solid #ddd;padding:8px}figcaption{font-weight:600;margin-bottom:6px}
img{max-width:100%%;height:auto;display:block}table{border-collapse:collapse;background:#fff;width:100%%}
th,td{border:1px solid #ddd;padding:4px 8px;text-align:left}th{background:#e6ece8}td.n{text-align:right}
</style></head><body><header><h1>Revue de placement : %(nom)s</h1>
<p>Rendus KiCad 10 - %(date)s - %(n)d composants</p></header><main>
<h2>Vues 3D</h2><div class="grille">%(fig)s</div>%(svg)s
<h2>Composants (%(n)d)</h2><table><tr><th>Réf.</th><th>Valeur</th><th>Empreinte</th>
<th>X (mm)</th><th>Y (mm)</th><th>Rotation (deg)</th><th>Face</th></tr>%(lignes)s</table>
</main></body></html>""" % {"nom": html.escape(nom), "date": date, "n": len(comps), "fig": fig,
                            "svg": ("<h2>Cuivre (SVG)</h2><div class=\"grille\">%s</div>" % fig_svg)
                            if fig_svg else "", "lignes": lignes}
    dest.write_text(doc, encoding="utf-8")


# --- programme principal ------------------------------------------------------------
def produire(args):
    pcb = Path(args.pcb).resolve()
    if not pcb.is_file():
        raise ErreurRevue("carte introuvable : %s" % pcb)
    if not Path(KICAD_CLI).is_file():
        raise ErreurRevue("kicad-cli introuvable : " + KICAD_CLI)
    sortie = Path(args.sortie).resolve() if args.sortie else pcb.parent / "revue_3d"
    sortie.mkdir(parents=True, exist_ok=True)
    nom, date = pcb.stem, datetime.date.today().strftime("%d/%m/%Y")
    qualite = "high" if args.qualite else "basic"
    larg, haut = args.largeur, int(args.largeur * 0.75)

    vues = VUES + ([VUE_RASANTE] if args.rasante else [])
    travaux = []
    for cle, titre, extra in vues:
        img = sortie / ("%s_%s.png" % (nom, cle))
        img.unlink(missing_ok=True)   # une image d'un run précédent ne doit pas masquer un échec
        travaux.append((cle, ["pcb", "render", "--width", larg, "--height", haut,
                              "--quality", qualite, "--background", "opaque"] + extra
                        + ["-o", img, pcb]))
    svg_dir = sortie / "svg_cuivre"
    if args.svg_cuivre:
        svg_dir.mkdir(exist_ok=True)
        for c in ("F.Cu", "B.Cu"):
            f = svg_dir / ("%s_%s.svg" % (nom, c.replace(".", "_")))
            f.unlink(missing_ok=True)
            travaux.append(("svg " + c, ["pcb", "export", "svg", "--mode-single",
                                         "--page-size-mode", "2", "--exclude-drawing-sheet",
                                         "-l", c + ",Edge.Cuts", "-o", f, pcb]))

    print("Rendu de %d éléments (%d en parallèle, qualité %s)..." % (
        len(travaux), max(1, args.jobs), qualite))
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        resultats = list(ex.map(lambda t: lancer(t[0], t[1]), travaux))
    total = time.time() - t0
    echecs = []
    for n, d, err in resultats:
        print("  %-10s %5.1f s %s" % (n, d, "ECHEC " + err if err else "ok"))
        if err:
            echecs.append(n)
    # Les durées individuelles gonflent en parallèle (les rendus se disputent le CPU) :
    # seule la durée réelle compte.
    print("Durée réelle : %.1f s" % total)
    if echecs:
        raise ErreurRevue("rendu en échec : " + ", ".join(echecs))

    liste = [(titre, exige(sortie / ("%s_%s.png" % (nom, cle)))) for cle, titre, _ in vues]
    svgs = []
    if args.svg_cuivre:
        for c, t in (("F.Cu", "Cuivre dessus"), ("B.Cu", "Cuivre dessous")):
            svgs.append((t, exige(svg_dir / ("%s_%s.svg" % (nom, c.replace(".", "_"))))))
    comps = composants(pcb)
    sorties = [p for _, p in liste] + [p for _, p in svgs]

    pl = sortie / (nom + "_planche.png")
    if planche(nom, liste, pl, date):
        sorties.insert(0, exige(pl))
    else:
        print("AVERTISSEMENT : Pillow absent, planche PNG sautée (pip install pillow)")
    ht = sortie / (nom + "_revue.html")
    page_html(nom, liste, comps, ht, date, svgs)
    sorties.insert(0, exige(ht))

    print("\n=== Fichiers produits (%s) ===" % sortie)
    for p in sorties:
        print("  %9d o  %s" % (p.stat().st_size, p))
    print("%d composants dans le tableau (dessus : %d, dessous : %d)" % (
        len(comps), sum(c["face"] == "dessus" for c in comps),
        sum(c["face"] == "dessous" for c in comps)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pcb", help="chemin du .kicad_pcb")
    ap.add_argument("--sortie", help="dossier de sortie (défaut : <carte>/revue_3d)")
    q = ap.add_mutually_exclusive_group()
    q.add_argument("--rapide", action="store_true", help="qualité basic (défaut)")
    q.add_argument("--qualite", action="store_true", help="qualité high (plus lent)")
    ap.add_argument("--rasante", action="store_true", help="ajoute la vue rasante côté connecteurs")
    ap.add_argument("--svg-cuivre", action="store_true", help="exporte les couches cuivre en SVG")
    ap.add_argument("--jobs", type=int, default=4, help="rendus simultanés (défaut 4, 1 = séquentiel)")
    ap.add_argument("--largeur", type=int, default=1400, help="largeur des vues en px (défaut 1400)")
    args = ap.parse_args()
    try:
        sys.exit(produire(args))
    except ErreurRevue as e:
        print("ERREUR : %s" % e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # accents lisibles meme en sortie redirigee
    main()
