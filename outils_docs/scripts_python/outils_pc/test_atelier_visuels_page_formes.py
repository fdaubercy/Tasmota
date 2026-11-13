"""Banc de l'editeur de formes de l'atelier des visuels.

Lancer : "$USERPROFILE/.platformio/penv/Scripts/python.exe" test_atelier_visuels_page_formes.py   (code de sortie 0 = vert)
(a) constantes Python presentes et sobres ; (b) logique pure executee par node (test_atelier_visuels_formes.mjs) ;
(c) chaque SVG produit passe nettoie_svg SANS perte (meme infoset).
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import atelier_visuels_fond as fond  # noqa: E402
import atelier_visuels_page_formes as pf  # noqa: E402

echecs = []


def verifie(ok, libelle):
    if not ok:
        echecs.append(libelle)
        print("KO  ", libelle)


# (a)
for nom in ("CSS_FORMES", "HTML_FORMES", "JS_FORMES"):
    v = getattr(pf, nom, None)
    verifie(isinstance(v, str) and 100 < len(v) < 60_000, f"{nom} : chaine de taille raisonnable")
for interdit in ("eval(", "</script>", "innerHTML =", "innerHTML=", "document.write", "new Function"):
    verifie(interdit not in pf.JS_FORMES, f"JS_FORMES ne contient pas {interdit!r}")
verifie("innerHTML" not in pf.JS_FORMES, "JS_FORMES : aucun innerHTML")
verifie(pf.HTML_FORMES.count("id='avf-") + pf.HTML_FORMES.count('id="avf-') >= 10, "HTML_FORMES : ids prefixes avf-")
verifie("avf-sel" in pf.HTML_FORMES and "avf-racine" in pf.HTML_FORMES, "HTML_FORMES : panneau et racine")
verifie("var(--bg" in pf.CSS_FORMES and "var(--tx" in pf.CSS_FORMES, "CSS_FORMES : variables de theme")
reste = re.sub(r"var\(--\w+, #[0-9a-fA-F]+\)", "", pf.CSS_FORMES)
verifie(not re.search(r"#[0-9a-fA-F]{3,8}", reste), "CSS_FORMES : aucune couleur d'interface en dur hors repli de variable")

# (b) + (c)
node = shutil.which("node")
verifie(node is not None, "node introuvable")
if node:
    with tempfile.TemporaryDirectory() as d:
        js, sortie = Path(d) / "formes.js", Path(d) / "svg.json"
        js.write_text(pf.JS_FORMES, encoding="utf-8")
        r = subprocess.run([node, str(ICI / "test_atelier_visuels_formes.mjs"), "--js", str(js), "--sortie", str(sortie)], capture_output=True, text=True, encoding="utf-8")
        print(r.stdout.strip(), r.stderr.strip())
        verifie(r.returncode == 0, "banc node vert")
        if sortie.exists():
            for nom, svg in json.loads(sortie.read_text(encoding="utf-8")).items():
                try:
                    net = fond.nettoie_svg(svg)
                    verifie(ET.canonicalize(svg) == ET.canonicalize(net), f"SVG {nom!r} : nettoie_svg sans perte")
                except ValueError as e:
                    verifie(False, f"SVG {nom!r} refuse par nettoie_svg : {e}")
            verifie(len(json.loads(sortie.read_text(encoding="utf-8"))) >= 4, "SVG produits")

print("VERT" if not echecs else f"{len(echecs)} echec(s)")
sys.exit(1 if echecs else 0)
