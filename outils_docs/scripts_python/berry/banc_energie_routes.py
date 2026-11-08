r"""Banc des routes de lecture d'energieFonctions (f=description, f=mois, f=direct) : Berry puis temoins sur des copies.

    python outils_docs/scripts_python/berry/banc_energie_routes.py

Code de sortie 0 si tout est vert. Faux webserver et faux relais de fichier ; ne teste pas la vraie carte (ni tas, ni serveur).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_cuve_page import trouve_racine

RACINE = trouve_racine()
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_energie_routes.be"
MODULE = RACINE / "data/fs/energieFonctions.be"
OK = "BANC_ENERGIE_ROUTES: OK"

# Chaque mutant doit rendre le banc rouge : (nom, texte du module, remplacement)
MUTANTS = [
    ("borne 4096 ignoree", "taille > max", "false"),
    ("borne exclusive", "taille > max", "taille >= max"),
    ("413 apres lecture", "(max > 0 && taille > max) ? 413 : 200", "200"),
    ("absent rendu 200", "taille < 0 ? 404", "false ? 404"),
    ("mois non controle", 'm) == nil)', 'm) == nil && false)'),
    ("mois 13 accepte", "1[0-2]", "1[0-3]"),
    ("mois non ancre en fin", ")$\", m)", ")\", m)"),
    ("champ ENERGY perdu", '"Today", "Yesterday",', '"Today",'),
    ("champ absent mis a nil", "if (m.contains(cle))    r[cle] = m[cle]    end", "r[cle] = m.find(cle)"),
    ("p retire", '{"p": m.find("Power"),', '{"x": m.find("Power"),'),
    ("import du module oublie (solidifie)", "    import energieFonctions\n    return energieFonctions.relaie(energieFonctions.DESCRIPTION", "    return energieFonctions.relaie(energieFonctions.DESCRIPTION"),
]


def lance(dossier, module=None):
    args = [str(BERRY), BANC, str(dossier)] + ([str(module)] if module else [])
    r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return r.stdout + r.stderr


def main():
    ok = True
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "b").mkdir()
        sortie = lance(tmp / "b")
        print("\n".join(l for l in sortie.splitlines() if not l.startswith("  OK")))
        print(f"  ({sum(l.startswith('  OK') for l in sortie.splitlines())} verifications OK)")
        ok = OK in sortie
        texte = MODULE.read_text(encoding="utf-8")
        print("--- Temoins (chaque mutant doit etre rouge)")
        for i, (nom, avant, apres) in enumerate(MUTANTS):
            if avant not in texte:
                print(f"  ECHEC temoin « {nom} » : texte introuvable dans le module")
                ok = False
                continue
            d = tmp / f"m{i}"
            d.mkdir()
            copie = d / "mutant.be"
            copie.write_text(texte.replace(avant, apres), encoding="utf-8")
            rouge = OK not in lance(d, copie)
            print(f"  {'OK   ' if rouge else 'ECHEC'} {nom}")
            ok = ok and rouge
    print("BANC: " + ("VERT" if ok else "ROUGE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
