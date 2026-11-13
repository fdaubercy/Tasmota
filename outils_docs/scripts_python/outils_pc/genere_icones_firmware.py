"""Catalogue des icones Material Design embarquees dans le firmware (atelier des ecrans, plan atelier-ecrans A15).

    python outils_docs/scripts_python/outils_pc/genere_icones_firmware.py [--verifier]

Lit les codes de lib/libesp32_lvgl/LVGL_assets/gen.sh (`'0xf0335=>0xE335'` = icone MDI F0335 servie en U+E335 dans les polices
montserrat-10/14/20/28 et icons-xx) et leurs noms dans materialdesignicons-webfont.ttf, ecrit
outils_docs/schemas/icones_firmware.json. Demande fontTools : PYTHON SYSTEME (absent du Python de PlatformIO) ; l'atelier lit
le JSON, il n'a pas besoin de fontTools. `--verifier` : code 1 si le JSON n'est plus celui de gen.sh (apres une synchro du fork).
Seule la police Material Design est cataloguee : les symboles Font Awesome de gen.sh ne le sont pas.
"""
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
GEN = "lib/libesp32_lvgl/LVGL_assets/gen.sh"
TTF = "lib/libesp32_lvgl/LVGL_assets/fonts/Symbols/materialdesignicons-webfont.ttf"
SORTIE = "outils_docs/schemas/icones_firmware.json"
PAIRE = re.compile(r"'0x([0-9a-fA-F]+)=>0x([0-9a-fA-F]+)'")


def codes(racine=RACINE):
    """[(mdi, servi)] de la police Material Design de gen.sh (ligne montserrat 28, sans doublon), en entiers, tries par code MDI."""
    for l in (Path(racine) / GEN).read_text(encoding="utf-8").splitlines():
        if "lv_font_montserrat_tasmota_28" in l:
            return sorted({(int(a, 16), int(b, 16)) for a, b in PAIRE.findall(l.split("FontAwesome5")[0])})
    raise ValueError(f"ligne montserrat 28 introuvable dans {GEN}")


def construit(racine=RACINE):
    from fontTools.ttLib import TTFont
    cmap = TTFont(str(Path(racine) / TTF)).getBestCmap()
    icones, manque = [], []
    for mdi, servi in codes(racine):
        nom = cmap.get(mdi)
        if nom is None:
            manque.append(f"{mdi:X}")
            continue
        icones.append({"nom": nom, "mdi": f"{mdi:X}", "servi": f"{servi:X}"})
    if manque:
        raise ValueError("codes absents de la police : " + ", ".join(manque))
    return {"version": 1, "source": GEN, "police": TTF, "icones": sorted(icones, key=lambda i: i["nom"])}


def texte(d):
    return json.dumps(d, ensure_ascii=False, indent=1) + "\n"


def main(argv):
    voulu = texte(construit())
    f = RACINE / SORTIE
    if "--verifier" in argv:
        ok = f.is_file() and f.read_text(encoding="utf-8") == voulu
        print("OK" if ok else f"{SORTIE} n'est plus celui de gen.sh : relancer sans --verifier")
        return 0 if ok else 1
    f.write_text(voulu, encoding="utf-8", newline="\n")
    print(f"{SORTIE} : {len(json.loads(voulu)['icones'])} icones")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
