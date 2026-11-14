"""Banc des tracés d'icones du firmware (atelier_visuels_icones_traces) : fichier present, un tracé valide par icone du catalogue,
repere 512 x 512, licence, et (Python systeme, fontTools) concordance avec la police. Code de sortie 0 = vert.

    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_visuels_icones_traces.py
    python outils_docs/scripts_python/outils_pc/test_atelier_visuels_icones_traces.py     (avec la concordance a la police)
"""
import json
import re
import sys
from pathlib import Path

import atelier_visuels_icones_traces as ict

ECHECS = []
D = re.compile(r"^M[MmLlHhVvCcSsQqTtAaZz0-9eE.,\s+-]{1,5999}$")


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def main():
    t = ict.charge()
    cat = json.loads((ict.RACINE / ict.CATALOGUE).read_text(encoding="utf-8"))["icones"]
    verifie((t["w"], t["h"], t["licence"]), (512, 512, "Apache-2.0"), "repere 512 x 512 et licence notee")
    verifie([i["nom"] for i in t["icones"]], [i["nom"] for i in cat], "un tracé par icone du catalogue, dans l'ordre")
    verifie(all(D.match(i["d"]) for i in t["icones"]), True, "chaque tracé est un chemin SVG sobre (<= 6000 caracteres, lettres de chemin et nombres)")
    verifie(any("<" in i["d"] or '"' in i["d"] for i in t["icones"]), False, "aucun caractere de balisage dans les tracés")
    for mauvais in ("M0 0<script>", 'M0 0"onload=', "L0 0", "M0 0" + "1" * 6000, ""):
        verifie(D.match(mauvais) is None, True, f"temoin negatif : tracé refuse ({mauvais[:14]!r})")
    try:
        ict.charge("/nulle/part")
        verifie("pas d'erreur", "LookupError", "fichier absent : LookupError")
    except LookupError as e:
        verifie("icones_traces.py" in str(e), True, "fichier absent : le message donne la commande")
    try:
        import fontTools  # noqa: F401
        verifie(json.loads(ict.texte(ict.genere())) == t, True, "concordance avec la police (fontTools)")
    except ImportError:
        print("INFO fontTools absent (Python de PlatformIO) : concordance a la police non verifiee ici")
    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
