"""Tracés SVG des icones Material Design du firmware, pour le selecteur d'icones de l'atelier des visuels.

    python outils_docs/scripts_python/outils_pc/atelier_visuels_icones_traces.py [--verifier]

La carte n'embarque que des chemins SVG inline (`style.icone_*` de visuel.json), pas la police : ce script convertit chaque glyphe du catalogue
`outils_docs/schemas/icones_firmware.json` (genere par genere_icones_firmware.py) en tracé `path`, dans `outils_docs/schemas/icones_firmware_traces.json`.
Demande fontTools : PYTHON SYSTEME (absent du Python de PlatformIO). Le serveur n'a besoin que du JSON (`charge`, stdlib). Repere de chaque tracé :
0 0 512 512 (glyphe de la police, axe y retourne). Licence : Material Design Icons (Pictogrammers), Apache-2.0. `--verifier` : code 1 si le JSON
n'est plus celui du catalogue et de la police (apres une synchro du fork).
"""
import json
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
CATALOGUE = "outils_docs/schemas/icones_firmware.json"
TTF = "lib/libesp32_lvgl/LVGL_assets/fonts/Symbols/materialdesignicons-webfont.ttf"
SORTIE = "outils_docs/schemas/icones_firmware_traces.json"
LICENCE = "Apache-2.0"
TAILLE = 512


def charge(racine=RACINE):
    """Le contenu de SORTIE ; LookupError s'il manque (message = la commande qui le cree)."""
    f = Path(racine) / SORTIE
    if not f.is_file():
        raise LookupError(f"{SORTIE} absent : python outils_docs/scripts_python/outils_pc/atelier_visuels_icones_traces.py")
    return json.loads(f.read_text(encoding="utf-8"))


def genere(racine=RACINE):
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    police = TTFont(str(Path(racine) / TTF))
    cmap, glyphes = police.getBestCmap(), police.getGlyphSet()
    haut = police["hhea"].ascent                                  # 448 : le haut de la case 512 x 512
    catalogue = json.loads((Path(racine) / CATALOGUE).read_text(encoding="utf-8"))["icones"]
    icones = []
    for i in catalogue:
        nom_glyphe = cmap.get(int(i["mdi"], 16))
        if nom_glyphe is None:
            raise ValueError(f"glyphe {i['mdi']} ({i['nom']}) absent de la police")
        pen = SVGPathPen(glyphes, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        glyphes[nom_glyphe].draw(TransformPen(pen, (1, 0, 0, -1, 0, haut)))
        icones.append({"nom": i["nom"], "d": pen.getCommands()})
    return {"version": 1, "source": CATALOGUE, "police": TTF, "licence": LICENCE, "w": TAILLE, "h": TAILLE, "icones": icones}


def texte(d):
    return json.dumps(d, ensure_ascii=False, indent=1) + "\n"


def main(argv):
    f = RACINE / SORTIE
    neuf = texte(genere())
    if "--verifier" in argv:
        ok = f.is_file() and f.read_text(encoding="utf-8") == neuf
        print("OK : traces a jour" if ok else f"PERIME : relancer sans --verifier ({SORTIE})")
        return 0 if ok else 1
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(neuf, encoding="utf-8", newline="\n")
    os.replace(tmp, f)                                            # ecriture atomique
    print(f"{SORTIE} : {len(json.loads(neuf)['icones'])} icones, {len(neuf)} octets")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
