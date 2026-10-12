#!/usr/bin/env python3
"""Export de fabrication KiCad 10 (Gerber, perçages, BOM, CPL, PDF, rendus 3D).

Usage :
  python export_fabrication.py <carte.kicad_pcb> [--sortie DIR]
         [--fabricant jlcpcb|pcbway] [--sans-controles]

Le .kicad_sch doit porter le même nom que le .kicad_pcb, dans le même dossier.

Étapes (dans l'ordre, la première erreur arrête tout) :
  1. Contrôles bloquants : ERC puis DRC (avec parité schéma/PCB, zones
     remplies en mémoire). Une erreur => résumé lisible, code de sortie 1.
     Les avertissements sont comptés par type mais ne bloquent pas.
  2. Gerber (extensions Protel : acceptées par JLCPCB comme PCBWay).
  3. Perçages Excellon PTH/NPTH séparés + carte des perçages.
  4. Zip <projet>_gerber_<fabricant>.zip, à plat (c'est lui qu'on téléverse).
  5. BOM au format du fabricant.   6. CPL (placement).
  7. PDF schéma, PDF carte, rendus 3D dessus/dessous.
  8. Résumé : fichiers, trous par diamètre, dimensions, couches cuivre.

Sortie par défaut : <dossier de la carte>/fabrication/. Code 0 = tout produit,
1 = contrôles en échec, 2 = erreur d'outil ou fichier manquant/vide.
"""
import argparse, csv, json, os, re, subprocess, sys, zipfile
from pathlib import Path

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
# Noms de couches de KiCad 10 (les anciens F.SilkS sont refusés par la CLI).
COUCHES_GERBER = ("F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,"
                  "F.Mask,B.Mask,Edge.Cuts")


class ErreurExport(Exception):
    pass

def kicad(*args):
    """Lance kicad-cli ; échec explicite si le code retour n'est pas 0."""
    cmd = [KICAD_CLI] + [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise ErreurExport("kicad-cli a échoué (code %d) : %s\n%s"
                           % (r.returncode, " ".join(args[:3]), (r.stdout + r.stderr).strip()))
    return r


def exige(chemin):
    """Le fichier doit exister et ne pas être vide."""
    p = Path(chemin)
    if not p.is_file() or p.stat().st_size == 0:
        raise ErreurExport("fichier attendu absent ou vide : %s" % p)
    return p


# --- 1. contrôles ---------------------------------------------------------
def violations(chemin_json, erc):
    """Liste (gravité, type, description, position) d'un rapport ERC/DRC."""
    d = json.loads(Path(chemin_json).read_text(encoding="utf-8"))
    if erc:
        brut = [v for f in d.get("sheets", []) for v in f.get("violations", [])]
    else:
        brut = (d.get("violations", []) + d.get("unconnected_items", [])
                + d.get("schematic_parity", []))
    res = []
    for v in brut:
        it = v.get("items") or [{}]
        pos = it[0].get("pos", {})
        lieu = "(%.2f ; %.2f)" % (pos.get("x", 0), pos.get("y", 0)) if pos else "?"
        elem = it[0].get("description", "")
        res.append((v.get("severity", "error"), v.get("type", "?"),
                    v.get("description", ""), lieu, elem))
    return res


def controles(pcb, sch, tmp):
    """ERC + DRC. Renvoie True si aucune erreur. Pas de --exit-code-violations :
    avec les avertissements inclus, il renverrait 1 aussi sans erreur ; on lit le JSON."""
    rapports = []
    erc_json, drc_json = tmp / "erc.json", tmp / "drc.json"
    kicad("sch", "erc", "--severity-error", "--severity-warning", "--format", "json",
          "-o", erc_json, sch)
    rapports.append(("ERC", violations(exige(erc_json), True)))
    kicad("pcb", "drc", "--schematic-parity", "--severity-error", "--severity-warning",
          "--refill-zones", "--format", "json", "-o", drc_json, pcb)
    rapports.append(("DRC", violations(exige(drc_json), False)))
    ok = True
    for nom, liste in rapports:
        erreurs = [v for v in liste if v[0] == "error"]
        avert = {}
        for v in liste:
            if v[0] != "error":
                avert[v[1]] = avert.get(v[1], 0) + 1
        print("%s : %d erreur(s), %d avertissement(s)" % (nom, len(erreurs), sum(avert.values())))
        for g, t, desc, lieu, elem in erreurs:
            print("  ERREUR [%s] %s %s %s" % (t, desc, lieu, elem))
        for t, n in sorted(avert.items()):
            print("  avertissement %s x%d (non bloquant)" % (t, n))
        ok = ok and not erreurs
    return ok


# --- 5/6. BOM et CPL --------------------------------------------------------
def cle_ref(ref):
    m = re.match(r"([A-Za-z_]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def lire_bom(sch, tmp):
    """BOM brut non regroupé ; écarte DNP et exclus de la BOM (PWR_FLAG, etc.)."""
    brut = tmp / "bom_brut.csv"
    kicad("sch", "export", "bom", "--fields",
          "Reference,Value,Footprint,LCSC,Manufacturer,MPN,Description,${DNP},${EXCLUDE_FROM_BOM}",
          "--labels", "Reference,Value,Footprint,LCSC,Manufacturer,MPN,Description,DNP,Excl",
          "-o", brut, sch)
    lignes = []
    with exige(brut).open(newline="", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            ref = l["Reference"]
            if l["DNP"] or l["Excl"] or ref.startswith("#"):
                continue
            l["Footprint"] = l["Footprint"].split(":")[-1]
            lignes.append(l)
    return lignes


def refs_cms(pcb, tmp):
    """Désignateurs des composants CMS (pour la colonne Type de PCBWay)."""
    brut = tmp / "pos_cms.csv"
    kicad("pcb", "export", "pos", "--format", "csv", "--smd-only", "-o", brut, pcb)
    with exige(brut).open(newline="", encoding="utf-8") as f:
        return {l["Ref"] for l in csv.DictReader(f)}


def ecrire_bom(lignes, fabricant, dest, cms=()):
    groupes = {}
    for l in lignes:
        groupes.setdefault((l["Value"], l["Footprint"], l["LCSC"]), []).append(l)
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if fabricant == "jlcpcb":
            w.writerow(["Comment", "Designator", "Footprint", "JLCPCB Part #"])
            for (val, fp, lcsc), g in sorted(groupes.items(), key=lambda x: cle_ref(x[1][0]["Reference"])):
                refs = ",".join(sorted((x["Reference"] for x in g), key=cle_ref))
                w.writerow([val, refs, fp, lcsc])
        else:
            w.writerow(["Item #", "Designator", "Qty", "Manufacturer", "Mfg Part #",
                        "Description / Value", "Package/Footprint", "Type"])
            for i, ((val, fp, lcsc), g) in enumerate(
                    sorted(groupes.items(), key=lambda x: cle_ref(x[1][0]["Reference"])), 1):
                refs = sorted((x["Reference"] for x in g), key=cle_ref)
                smd = "SMD" if all(x in cms for x in refs) else "THT"
                w.writerow([i, ",".join(refs), len(refs), g[0]["Manufacturer"], g[0]["MPN"] or lcsc,
                            val, fp, smd])
    exige(dest)
    return len(groupes), len(lignes)


def ecrire_cpl(pcb, tmp, dest):
    brut = tmp / "pos_brut.csv"
    kicad("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", brut, pcb)
    n = 0
    with exige(brut).open(newline="", encoding="utf-8") as f, \
            dest.open("w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for l in csv.DictReader(f):
            w.writerow([l["Ref"], l["PosX"] + "mm", l["PosY"] + "mm",
                        "Top" if l["Side"].lower() == "top" else "Bottom", l["Rot"]])
            n += 1
    exige(dest)
    return n


# --- 8. lecture des fichiers produits ------------------------------------------
def trous(dossier):
    """{fichier: {diamètre: nombre}} d'après les fichiers Excellon (T<n>C<diam>)."""
    res = {}
    for p in sorted(dossier.glob("*.drl")):
        outils, courant, cpt = {}, None, {}
        for l in p.read_text(errors="replace").splitlines():
            m = re.match(r"T(\d+)C([\d.]+)", l)
            if m:
                outils[m.group(1)] = float(m.group(2))
            elif re.fullmatch(r"T\d+", l.strip()):
                courant = l.strip()[1:]
            elif courant in outils and re.match(r"X-?[\d.]+Y-?[\d.]+", l):
                cpt[outils[courant]] = cpt.get(outils[courant], 0) + 1
        res[p.name] = cpt
    return res


def dimensions(dossier):
    """Boîte englobante de Edge.Cuts (.gm1), unités mm, format FSLAX46Y46."""
    p = next(dossier.glob("*Edge_Cuts.gm1"), None)
    if not p:
        return None
    t = p.read_text(errors="replace")
    fmt = re.search(r"%FSLAX(\d)(\d)Y", t)
    dec = int(fmt.group(2)) if fmt else 6
    pts = [(int(x) / 10 ** dec, int(y) / 10 ** dec)
           for x, y in re.findall(r"^X(-?\d+)Y(-?\d+)D0[123]", t, re.M)]
    if not pts:
        return None
    xs, ys = zip(*pts)
    return max(xs) - min(xs), max(ys) - min(ys)


def couches_cuivre(pcb):
    t = Path(pcb).read_text(encoding="utf-8", errors="replace")
    return len(set(re.findall(r'\(\d+\s+"([^"]+\.Cu)"\s+(?:signal|power|mixed|jumper)', t)))


# --- programme principal --------------------------------------------------------
def produire(args):
    pcb = Path(args.pcb).resolve()
    sch = pcb.with_suffix(".kicad_sch")
    if not pcb.is_file() or not sch.is_file():
        raise ErreurExport("carte ou schéma introuvable : %s / %s" % (pcb, sch))
    if not Path(KICAD_CLI).is_file():
        raise ErreurExport("kicad-cli introuvable : " + KICAD_CLI)
    sortie = Path(args.sortie).resolve() if args.sortie else pcb.parent / "fabrication"
    ger, tmp = sortie / "gerber", sortie / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    nom, fab = pcb.stem, args.fabricant

    if args.sans_controles:
        print("ATTENTION : contrôles ERC/DRC désactivés (--sans-controles)")
    elif not controles(pcb, sch, tmp):
        print("\nExport ARRÊTÉ : corriger les erreurs ci-dessus (ou --sans-controles).")
        return 1

    ger.mkdir(exist_ok=True)
    for ancien in list(ger.glob("*")):   # pas de reste d'un export précédent dans le zip
        ancien.unlink()
    # Protel gardé (défaut) ; --subtract-soldermask évite la sérigraphie sur pastilles ;
    # origine absolue = celle des perçages (on n'utilise pas l'origine de perçage des deux côtés).
    kicad("pcb", "export", "gerbers", "-o", str(ger) + os.sep, "-l", COUCHES_GERBER,
          "--subtract-soldermask", pcb)
    kicad("pcb", "export", "drill", "-o", str(ger) + os.sep, "--format", "excellon",
          "--excellon-units", "mm", "--excellon-zeros-format", "decimal",
          "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", pcb)
    fichiers = [exige(p) for p in ger.iterdir() if p.is_file()]
    if not fichiers:
        raise ErreurExport("dossier gerber vide")

    # Le plan de perçage (*-drl_map.gbr) reste à côté, hors zip : un fabricant le prendrait pour une couche.
    zip_p = sortie / ("%s_gerber_%s.zip" % (nom, fab))
    with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(fichiers):
            if "drl_map" not in p.name:
                z.write(p, p.name)
    exige(zip_p)

    lignes = lire_bom(sch, tmp)
    bom_p = sortie / ("%s_bom_%s.csv" % (nom, fab))
    nb_g, nb_c = ecrire_bom(lignes, fab, bom_p, refs_cms(pcb, tmp))
    cpl_p = sortie / ("%s_cpl_%s.csv" % (nom, fab))
    nb_pos = ecrire_cpl(pcb, tmp, cpl_p)
    print("CPL : %d composants (utile seulement pour un assemblage par le fabricant)" % nb_pos)

    docs = [sortie / (nom + "_schema.pdf"), sortie / (nom + "_pcb.pdf"),
            sortie / (nom + "_3d_dessus.png"), sortie / (nom + "_3d_dessous.png")]
    kicad("sch", "export", "pdf", "-o", docs[0], sch)
    kicad("pcb", "export", "pdf", "--mode-single", "-l",
          "F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,Edge.Cuts", "-o", docs[1], pcb)
    for cote, d in (("top", docs[2]), ("bottom", docs[3])):
        kicad("pcb", "render", "--side", cote, "--width", "1600", "--height", "1600", "-o", d, pcb)

    sorties = [zip_p, bom_p, cpl_p] + docs + sorted(fichiers)
    print("\n=== Fichiers produits (%s) ===" % sortie)
    for p in sorties:
        print("  %9d o  %s" % (exige(p).stat().st_size, p.relative_to(sortie)))
    print("\nTéléverser chez %s : %s" % (fab, zip_p.name))
    print("BOM : %d lignes groupées pour %d composants" % (nb_g, nb_c))
    for f, cpt in trous(ger).items():
        print("Trous %s : %d au total ; diamètres (mm) : %s" % (
            f, sum(cpt.values()), ", ".join("%.3f x%d" % (d, n) for d, n in sorted(cpt.items())) or "aucun"))
    dim = dimensions(ger)
    print("Dimensions carte : %s" % ("%.2f x %.2f mm" % dim if dim else "illisibles (Edge.Cuts)"))
    print("Couches cuivre : %d" % couches_cuivre(pcb))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pcb", help="chemin du .kicad_pcb")
    ap.add_argument("--sortie", help="dossier de sortie (défaut : <carte>/fabrication)")
    ap.add_argument("--fabricant", choices=("jlcpcb", "pcbway"), default="jlcpcb")
    ap.add_argument("--sans-controles", action="store_true", help="saute ERC/DRC")
    args = ap.parse_args()
    try:
        sys.exit(produire(args))
    except ErreurExport as e:
        print("ERREUR : %s" % e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # accents lisibles meme en sortie redirigee
    main()
