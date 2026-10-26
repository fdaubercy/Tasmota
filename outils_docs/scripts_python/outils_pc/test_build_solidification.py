"""Banc de build_solidification (module solidifie inscrit dans modules.h mais absent de son .h).

Code de sortie 0 = vert. Faux dossier berry_custom dans un dossier temporaire : jamais le vrai depot.
Cas reel (2026-10-26) : data/fs/demarrage.be sans `#@ solidify:demarrage` -> solidified_demarrage.h vide,
`undefined reference to be_native_module_demarrage` a l'edition des liens, apres une heure de compilation.
"""

import sys
import tempfile
from pathlib import Path

import build_solidification as bso

ECHECS = []

MODULES_H = ("#define CUSTOM_NATIVE_MODULES &be_native_module(logFonctions), &be_native_module(demarrage),\n"
             "#define CUSTOM_NATIVE_CLASSES &be_native_class(MaClasse),\n"
             "be_extern_native_module(logFonctions);\n"
             "be_extern_native_module(demarrage);\n"
             "be_extern_native_class(MaClasse);")
ENTETE = ('/* Solidification of x.h */\n#include "be_constobj.h"\n'
          "/********************************************************************/\n/* End of solidification */\n")


def verifie(obtenu, attendu, libelle):
    if obtenu == attendu:
        print(f"OK   {libelle}")
    else:
        ECHECS.append(libelle)
        print(f"KO   {libelle}\n       obtenu  : {obtenu!r}\n       attendu : {attendu!r}")


def depot(t, demarrage_plein=False, classe_pleine=True, directive=False):
    """Faux depot : berry_custom/src avec modules.h, solidify/*.h et embedded/*.be."""
    src = Path(t) / "lib" / "libesp32" / "berry_custom" / "src"
    (src / "solidify").mkdir(parents=True)
    (src / "embedded").mkdir()
    (src / "modules.h").write_text(MODULES_H, encoding="utf-8")
    (src / "solidify" / "solidified_logFonctions.h").write_text(
        ENTETE + "be_local_module(logFonctions,\n);\nBE_EXPORT_VARIABLE be_define_const_native_module(logFonctions);\n",
        encoding="utf-8")
    (src / "solidify" / "solidified_demarrage.h").write_text(
        ENTETE + ("BE_EXPORT_VARIABLE be_define_const_native_module(demarrage);\n" if demarrage_plein else ""),
        encoding="utf-8")
    (src / "solidify" / "solidified_maClasse.h").write_text(
        ENTETE + ("be_local_class(MaClasse,\n    0,\n);\n" if classe_pleine else ""), encoding="utf-8")
    (src / "embedded" / "logFonctions.be").write_text(
        '#@ solidify:logFonctions\nvar logFonctions = module("logFonctions")\n', encoding="utf-8")
    (src / "embedded" / "demarrage.be").write_text(
        ("#@ solidify:demarrage\n" if directive else "") + 'var demarrage = module("demarrage")\n', encoding="utf-8")
    return Path(t)


def test_module_vide():
    with tempfile.TemporaryDirectory() as t:
        vides = bso.vides(depot(t))
        verifie([v["nom"] for v in vides], ["demarrage"], "module_vide : demarrage signale, logFonctions non")
        verifie(vides[0]["genre"], "module", "module_vide : genre module")
        verifie("#@ solidify:demarrage" in vides[0]["cause"] and "demarrage.be" in vides[0]["cause"], True,
                "module_vide : la cause nomme la directive manquante et le fichier")


def test_tout_present():
    with tempfile.TemporaryDirectory() as t:
        verifie(bso.vides(depot(t, demarrage_plein=True)), [], "tout_present : temoin, rien a signaler")


def test_classe_vide():
    with tempfile.TemporaryDirectory() as t:
        vides = bso.vides(depot(t, demarrage_plein=True, classe_pleine=False))
        verifie([(v["nom"], v["genre"]) for v in vides], [("MaClasse", "classe")],
                "classe_vide : classe inscrite sans be_local_class signalee")


def test_directive_presente_mais_vide():
    with tempfile.TemporaryDirectory() as t:
        vides = bso.vides(depot(t, directive=True))
        verifie([v["nom"] for v in vides], ["demarrage"], "directive_presente : .h vide malgre la directive, signale")
        verifie("#@ solidify:demarrage" in vides[0]["cause"], False,
                "directive_presente : la cause ne pretend pas que la directive manque")


def test_sans_berry_custom():
    with tempfile.TemporaryDirectory() as t:
        verifie(bso.vides(Path(t)), [], "sans_berry_custom : pas de modules.h -> rien a controler")
        (Path(t) / "lib" / "libesp32" / "berry_custom" / "src").mkdir(parents=True)
        (Path(t) / "lib" / "libesp32" / "berry_custom" / "src" / "modules.h").write_text(
            "#define CUSTOM_NATIVE_MODULES\n#define CUSTOM_NATIVE_CLASSES", encoding="utf-8")
        verifie(bso.vides(Path(t)), [], "sans_berry_custom : modules.h vide (env sans solidification) -> rien")


def test_motif():
    with tempfile.TemporaryDirectory() as t:
        motif = bso.motif(bso.vides(depot(t)))
        verifie(motif.startswith("solidification vide : demarrage"), True, "motif : commence par les modules vides")


def principal():
    for test in (test_module_vide, test_tout_present, test_classe_vide, test_directive_presente_mais_vide,
                 test_sans_berry_custom, test_motif):
        test()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
