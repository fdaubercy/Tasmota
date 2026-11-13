"""Icones Material Design du firmware pour la page de l'atelier des ecrans (plan atelier-ecrans A15).

`charge` lit outils_docs/schemas/icones_firmware.json (genere par genere_icones_firmware.py d'apres gen.sh) ; `police` rend la
police locale materialdesignicons-webfont.ttf, dont la page dessine les glyphes (aucun CDN). Routes GET /icones et /lib/mdi.ttf."""
import json
from pathlib import Path

CATALOGUE = "outils_docs/schemas/icones_firmware.json"
TTF = "lib/libesp32_lvgl/LVGL_assets/fonts/Symbols/materialdesignicons-webfont.ttf"


def charge(racine):
    f = Path(racine) / CATALOGUE
    if not f.is_file():
        raise LookupError(f"{CATALOGUE} absent : python outils_docs/scripts_python/outils_pc/genere_icones_firmware.py")
    return json.loads(f.read_text(encoding="utf-8"))


def police(racine):
    f = Path(racine) / TTF
    if not f.is_file():
        raise LookupError("police materialdesignicons-webfont.ttf absente du depot")
    return f.read_bytes()
