r"""Banc de la page « Systeme » construite par l'atelier, cote carte (plan atelier-ecrans A19) : banc_page_systeme.be charge le
VRAI ecranLvgl.be genere de l'ecran des debits et le VRAI data/fs/ecranSysteme.be (objets LVGL simules), puis temoins : copies
modifiees du fichier genere, chacune doit rendre le banc rouge.

    python outils_docs/scripts_python/berry/banc_page_systeme.py

Code de sortie 0 si tout est vert. Le pages.jsonl (HASPmota) est controle par outils_pc/test_atelier_ecrans_systeme.py. Ne
prouve ni le rendu sur la dalle, ni le tactile reel (essai sur carte, A20).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_page_systeme.be"
INTERFACE = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be"
VERT = "BANC_PAGE_SYSTEME: OK"

# (nom, texte du fichier genere, remplacement) : chaque mutant doit rendre le banc rouge
MUTANTS = [
    ("texte d'un champ absent (p4b1)", '    [4, 1, "label",', '    [4, 1001, "label",'),
    ("barre d'un champ absente (p4b4)", '    [4, 4, "bar",', '    [4, 1004, "bar",'),
    ("barre en label", '    [4, 4, "bar",', '    [4, 4, "label",'),
    ("bouton 121 : appui compte double", "ecranSysteme.appui(121)    end", "ecranSysteme.appui(121)    ecranSysteme.appui(121)    end"),
    ("bouton 120 : mauvais argument", "ecranSysteme.appui(120)    end", 'ecranSysteme.appui("120")    end'),
    ("bouton 120 sans toucher", "ecranLvgl_p4b120],", "nil],"),
]


def lance(dossier, interface="-"):
    try:
        r = subprocess.run([str(BERRY), BANC, str(dossier), str(interface)], cwd=RACINE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "BLOQUE : berry.exe arrete apres 120 s"
    return r.stdout + r.stderr


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "banc").mkdir()
        sortie = lance(tmp / "banc")
        print(sortie.rstrip())
        ok = VERT in sortie
        print("--- Temoins (chaque mutant du fichier genere doit etre rouge)")
        texte = INTERFACE.read_text(encoding="utf-8").replace("\r\n", "\n")
        for i, (nom, avant, apres) in enumerate(MUTANTS):
            if texte.count(avant) != 1:
                print(f"  ECHEC temoin « {nom} » : texte absent ou ambigu")
                ok = False
                continue
            d = tmp / f"mutant{i}"
            d.mkdir()
            (d / "ecranLvgl.be").write_text(texte.replace(avant, apres), encoding="utf-8")
            (d / "banc").mkdir()
            rouge = VERT not in lance(d / "banc", d / "ecranLvgl.be")
            print(f"  {'OK   ' if rouge else 'ECHEC'} {nom}")
            ok = ok and rouge
    print("BANC_PAGE_SYSTEME (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
