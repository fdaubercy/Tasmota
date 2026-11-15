"""Banc de icones_catalogue.py (usages, absentes, PNG, sources) sur un MINI-DEPOT temporaire, avec MUTANTS. Code de sortie 0 = vert.

Chaque mutant (une ligne du module changee) doit rendre le banc rouge. Aucun reseau, aucun vrai depot.
Lancer : python outils_docs/scripts_python/outils_pc/test_icones_catalogue.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import json
import struct
import sys
import tempfile
import types
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

SOURCE = (ICI / "icones_catalogue.py").read_text(encoding="utf-8")
ECHECS = []

SOURCES_MD = """# Annuaire

## 0. Deja dans le firmware

| Ou | Quoi | Comment |
|---|---|---|
| [Ignore](https://exemple.org/zero) | zero | zero |

## 1. Collections libres

| Site | Licence | Formats | Remarque |
|---|---|---|---|
| [Pictogrammers MDI](https://pictogrammers.com/library/mdi/) | Apache 2.0 | SVG | **Premier choix** : le firmware |
| [Lucide](https://lucide.dev/icons/) | ISC | SVG | trait fin |

## 2. Moteurs

| Site | Remarque |
|---|---|
| [Iconify](https://icon-sets.iconify.design/) | 200 collections |

## 3. A eviter

| Site | Pourquoi |
|---|---|
| Flaticon, Icons8 | attribution |

## Formats selon la cible

| Site | Pourquoi |
|---|---|
| [Ignore](https://exemple.org/fin) | fin |
"""


def png(largeur, hauteur):
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", largeur, hauteur) + b"\x08\x06\x00\x00\x00")


def monte(racine):
    def ecrit(rel, contenu):
        f = racine / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(contenu if isinstance(contenu, bytes) else contenu.encode("utf-8"))
    firmware = {"version": 1, "source": "x", "police": "x", "icones": [
        {"nom": "lightbulb", "mdi": "F0335", "servi": "E335"}, {"nom": "lamp", "mdi": "F06B5", "servi": "E6B5"},
        {"nom": "fan", "mdi": "F0210", "servi": "E210"}, {"nom": "power", "mdi": "F0425", "servi": "E425"}]}
    ecrit("outils_docs/schemas/icones_firmware.json", json.dumps(firmware))
    ecrit("outils_docs/atelier_ecrans/cartes/envA/ecran.json", '{"text": "\\uE335 et \\uE335", "t2": "\\uE999", "t3": "\\uf900"}')
    ecrit("outils_docs/atelier_ecrans/cartes/envA/autre.json", '{"text": "\\uE425"}')              # pas un ecran.json
    ecrit("outils_docs/atelier_ecrans/cartes/envA/ecran.json.txt", "\\uE425")
    ecrit("data/lieu/carte/ecran.be", 'var t = "\\ue335" + "\ue6b5" + "\uf8ff"')                    # minuscules, caractere brut, borne F8FF
    ecrit("data/lieu/carte/pages.jsonl", '{"text": "\\uE335"}\n')
    ecrit("data/lieu/carte/gros.be", "x" * (2 * 1024 * 1024 + 10) + "\\uE425")                      # trop gros : non lu
    for n in range(25):
        ecrit(f"data/cap/f{n:02d}.be", "\\uE210")
    ecrit("data/lieu/carte/ok.png", png(16, 32))
    ecrit("data/lieu/carte/tronque.png", png(16, 32)[:18])
    ecrit("data/lieu/carte/faux.png", b"pas un png du tout, mais assez long pour la lecture")
    ecrit("data/lieu/carte/chunk.png", png(5, 5).replace(b"IHDR", b"IDAT"))
    ecrit("outils_docs/atelier_ecrans/images/envA/logo.png", png(40, 20))
    ecrit("outils_docs/ICONES_IMAGES_SOURCES.md", SOURCES_MD)


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def controles(mod, racine):
    """Les verifications du banc sur un module (le vrai ou un mutant)."""
    try:
        r = mod.construit(racine)
    except Exception as erreur:
        verifie(repr(erreur), None, "construit() ne doit pas lever")
        return
    g = {x["nom"]: x for x in r["glyphes"]}
    verifie(sorted(g), ["fan", "lamp", "lightbulb", "power"], "glyphes du catalogue firmware")
    verifie(g["lightbulb"]["usages"], ["outils_docs/atelier_ecrans/cartes/envA/ecran.json", "data/lieu/carte/ecran.be",
                                       "data/lieu/carte/pages.jsonl"],
            "usages : \\uE335 (une fois par fichier, minuscules admises)")
    verifie(g["lamp"]["usages"], ["data/lieu/carte/ecran.be"], "usages : caractere brut U+E6B5")
    verifie(len(g["fan"]["usages"]), 20, "usages plafonnes a 20")
    verifie(g["power"]["usages"], [], "usages : autre.json, ecran.json.txt et fichier trop gros ignores")
    verifie([a["code"] for a in r["absentes"]], ["E999", "F8FF"], "absentes : codes hors catalogue (F900 hors plage)")
    verifie(r["absentes"][0]["usages"], ["outils_docs/atelier_ecrans/cartes/envA/ecran.json"], "absentes : usages de E999")
    verifie(r["pngs"], [{"chemin": "data/lieu/carte/ok.png", "largeur": 16, "hauteur": 32, "poids": len(png(16, 32))},
                        {"chemin": "outils_docs/atelier_ecrans/images/envA/logo.png", "largeur": 40, "hauteur": 20, "poids": len(png(40, 20))}],
            "PNG : lus par IHDR, tronque, faux et mauvais chunk ignores")
    verifie([(s["nom"], s["url"], s["licence"], s["categorie"][:3]) for s in r["sources"]],
            [("Pictogrammers MDI", "https://pictogrammers.com/library/mdi/", "Apache 2.0", "1. "), ("Lucide", "https://lucide.dev/icons/", "ISC", "1. "),
             ("Iconify", "https://icon-sets.iconify.design/", "", "2. "), ("Flaticon, Icons8", "", "", "3. ")],
            "sources : sections 1 a 3, url, licence (4 colonnes seulement)")
    verifie(r["sources"][0]["usage"] if r["sources"] else None, "Premier choix : le firmware", "sources : markdown retire de l'usage")


MUTANTS = [
    ("plafond 21", "MAX_USAGES = 20", "MAX_USAGES = 21"),
    ("plage F9xx", "[fF][0-8][0-9a-fA-F]{2}", "[fF][0-9][0-9a-fA-F]{2}"),
    ("plage brute", "|([\\ue000-\\uf8ff])", "|([\\ue000-\\ue6b4])"),
    ("sans upper", '(m.group(1) or format(ord(m.group(2)), "X")).upper()', '(m.group(1) or format(ord(m.group(2)), "X"))'),
    ("doublons", "if rel not in liste and len(liste)", "if len(liste)"),
    ("gros fichier lu", "f.stat().st_size > MAX_OCTETS", "False"),
    ("sans controle de longueur", "len(tete) < 24 or ", ""),
    ("sans controle IHDR", ' or tete[12:16] != b"IHDR"', ""),
    ("png de data ignores", 'racine / "data", racine / "outils_docs"', 'racine / "dataX", racine / "outils_docs"'),
    ("images ignorees", '"atelier_ecrans" / "images"', '"atelier_ecrans" / "imagesX"'),
    ("pages.jsonl ignore", 'data.rglob("pages.jsonl")', 'data.rglob("pagesX.jsonl")'),
    ("be ignores", 'data.rglob("*.be")', 'data.rglob("*.bex")'),
    ("ecran.json ignore", '"*/ecran.json"', '"*/ecranX.json"'),
    ("tout est absent", "if c not in servis", "if True"),
    ("section 0 incluse", 'if re.match(r"## [123]\\.", ligne) else None', "if True else None"),
    ("licence a 2 colonnes", "len(cases) >= 4", "len(cases) >= 2"),
    ("url perdue", "lien.group(2) if lien", "lien.group(1) if lien"),
    ("markdown garde", '.replace("**", "")', ""),
]


def charge_mutant(source):
    mod = types.ModuleType("icones_catalogue_mutant")
    exec(compile(source, "icones_catalogue_mutant", "exec"), mod.__dict__)
    return mod


def principal():
    import icones_catalogue
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
        racine = Path(t)
        monte(racine)
        print("== module reel")
        controles(icones_catalogue, racine)
        verifie(icones_catalogue.construit(racine / "absent")["glyphes"], [], "depot sans catalogue : liste vide, pas d'exception")
        print("== mutants")
        for nom, ancien, nouveau in MUTANTS:
            if SOURCE.count(ancien) != 1:
                verifie(SOURCE.count(ancien), 1, f"mutant {nom} : texte a changer introuvable ou multiple")
                continue
            avant = len(ECHECS)
            controles(charge_mutant(SOURCE.replace(ancien, nouveau)), racine)
            detecte = len(ECHECS) > avant
            del ECHECS[avant:]
            print(("OK   " if detecte else "KO   ") + f"mutant detecte : {nom}")
            if not detecte:
                ECHECS.append(f"mutant survivant : {nom}")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}") + f" ({len(MUTANTS)} mutants)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
