r"""Verifie qu'un module Berry est solidifiable — SANS lancer un build de 2h16.

UTILISATION
-----------
  python solidifie_et_compile_berry.py [chemin/du/module.be]

  Sans argument : data/fs/modbusFonctions.be.
  Chemin relatif : interprete depuis la racine du depot.

CE QU'IL FAIT
-------------
Rejoue les 3 etapes de pio-tools/gen-berry-structures.py, sur le module demande :

    1. solidification  (etape 1 du post-script)
    2. coc             (etape 2 : regenere la table des chaines)
    3. COMPILATION du .h avec le vrai compilateur croise xtensa

POURQUOI L'ETAPE 3 EXISTE
-------------------------
Elle est la raison d'etre de ce script. Le 2026-07-15/16, trois verdicts ont ete
rendus sur la seule EXISTENCE d'un .h genere, sans jamais le compiler. Les trois
etaient faux, et l'un d'eux a coute un build de 2h16 :

  - nom de module avec slash -> `error: pasting "be_native_module_" and "/"
    does not give a valid preprocessing token`
  - 15 fonctions anonymes    -> `error: redefinition of '_anonymous__closure'`

Un artefact genere ne prouve que son existence. Passer ce script AVANT tout build.

CE QU'IL NE MODIFIE PAS
-----------------------
Le module source n'est jamais touche : on travaille sur une copie dans
src/embedded/. Les dossiers embedded/ et solidify/ sont gitignores et vides a
chaque build (cleanFolder du pre-script) ; generate/ est gitignore et regenere.
Aucun etat durable n'est laisse derriere.

PREREQUIS
---------
PlatformIO installe, et un build deja passe une fois (pour que la toolchain
xtensa soit telechargee). Aucun chemin en dur : tout est deduit.
"""
import os
import subprocess
import sys
from pathlib import Path

def trouve_racine() -> Path:
    """Racine du depot, deduite de l'emplacement de ce script."""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


def trouve_platformio() -> Path:
    """Dossier ~/.platformio, quel que soit l'utilisateur."""
    for base in (Path.home(), Path(os.environ.get("USERPROFILE", ""))):
        if base and (base / ".platformio").is_dir():
            return base / ".platformio"
    sys.exit("ERREUR : ~/.platformio introuvable. PlatformIO est-il installe ?")


def trouve_python(pio: Path) -> str:
    """Le python de PlatformIO (celui qui a berry_port dans son environnement)."""
    for c in (pio / "penv" / "Scripts" / "python.exe",
              pio / "penv" / "bin" / "python3",
              pio / "python3" / "python.exe"):
        if c.exists():
            return str(c)
    return sys.executable  # repli : le python courant


def trouve_gcc(pio: Path) -> Path:
    """Le compilateur croise xtensa. Sans lui, pas de verification possible."""
    for motif in ("xtensa-esp-elf-gcc.exe", "xtensa-esp-elf-gcc"):
        for base in (pio / "packages" / "toolchain-xtensa-esp-elf" / "bin",):
            trouve = list(base.glob(motif)) if base.is_dir() else []
            if trouve:
                return trouve[0]
    sys.exit("ERREUR : xtensa-esp-elf-gcc introuvable. Lancer un build une fois "
             "pour que PlatformIO telecharge la toolchain.")


RACINE = trouve_racine()
PIO = trouve_platformio()
CUSTOM = RACINE / "lib" / "libesp32" / "berry_custom"
EMBEDDED = CUSTOM / "src" / "embedded"
SOLIDIFY = CUSTOM / "src" / "solidify"
BERRY = RACINE / "lib" / "libesp32" / "berry"
PYTHON = trouve_python(PIO)
SCRATCH = Path(__file__).parent

# Module a verifier : 1er argument, ou modbusFonctions par defaut.
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "data" / "fs" / "modbusFonctions.be"
if not SOURCE.is_absolute():
    SOURCE = RACINE / SOURCE
if not SOURCE.is_file():
    sys.exit(f"ERREUR : {SOURCE} introuvable.")

GCC = trouve_gcc(PIO)
ENV = {**os.environ, "PYTHONPATH": str(BERRY), "PYTHONUTF8": "1"}

try:
    for f in EMBEDDED.glob("*.be"):
        f.unlink()
    for h in SOLIDIFY.glob("solidified_*.h"):
        h.unlink()
    (EMBEDDED / SOURCE.name).write_bytes(SOURCE.read_bytes())

    print(f"module : {SOURCE.relative_to(RACINE) if RACINE in SOURCE.parents else SOURCE}"
          f"  ({SOURCE.stat().st_size:,} octets)\n")

    print("=== 1. SOLIDIFICATION ===")
    r = subprocess.run(
        [PYTHON, "-m", "berry_port", "-s", "-g", "solidify_all_python.be"],
        cwd=CUSTOM, capture_output=True, text=True, env=ENV)
    print("   rc =", r.returncode)
    if r.returncode != 0:
        print(((r.stdout or "") + (r.stderr or ""))[:600])
        raise SystemExit(1)
    h = SOLIDIFY / f"solidified_{SOURCE.stem}.h"
    if not h.exists():
        sys.exit(f"   AUCUN {h.name} produit -> la directive '#@ solidify:' "
                 f"manque-t-elle dans le module ?")
    txt = h.read_text(encoding="utf-8", errors="replace")
    anon = txt.count("be_local_closure(_anonymous_,")
    print(f"   {h.name} : {h.stat().st_size:,} octets, "
          f"{txt.count('be_local_closure(')} closures, {anon} anonymes")
    # 379 octets = en-tete seul : le .h est vide et personne ne le signale.
    if h.stat().st_size < 1000:
        print("   ATTENTION : .h anormalement petit -> probablement VIDE "
              "(directive '#@ solidify:' absente ?)")
    if anon > 1:
        print(f"   ATTENTION : {anon} closures anonymes -> collision C garantie "
              f"(`redefinition of '_anonymous__closure'`). Nommer les fonctions : "
              f"voir nomme_fonctions_berry.py")

    print("\n=== 2. COC (regenere la table des chaines) ===")
    # Copie conforme de gen-berry-structures.py:344
    j = os.path.join
    cmd = [PYTHON, j("tools", "coc", "coc"), "-o", "generate", "src", "default",
           j("..", "berry_tasmota", "src"),
           j("..", "berry_matter", "src", "solidify"), j("..", "berry_matter", "src"),
           j("..", "berry_custom", "src", "solidify"), j("..", "berry_custom", "src"),
           j("..", "berry_animation", "src", "solidify"), j("..", "berry_animation", "src"),
           j("..", "berry_tasmota", "src", "solidify"),
           j("..", "berry_mapping", "src"), j("..", "berry_int64", "src"),
           j("..", "..", "libesp32_lvgl", "lv_binding_berry", "src"),
           j("..", "..", "libesp32_lvgl", "lv_binding_berry", "src", "solidify"),
           j("..", "..", "libesp32_lvgl", "lv_binding_berry", "generate"),
           j("..", "..", "libesp32_lvgl", "lv_haspmota", "src", "solidify"),
           "-c", j("default", "berry_conf.h"),
           j("..", "..", "..", "tasmota", "tasmota_defines_for_berry.h")]
    r2 = subprocess.run(cmd, cwd=BERRY, capture_output=True, text=True, env=ENV)
    print("   rc =", r2.returncode)
    if r2.returncode != 0:
        print(((r2.stdout or "") + (r2.stderr or ""))[:600])
        raise SystemExit(1)
    strtab = BERRY / "generate" / "be_const_strtab_def.h"
    dedans = f"be_const_str_{SOURCE.stem}" in strtab.read_text(
        encoding="utf-8", errors="replace")
    print(f"   be_const_str_{SOURCE.stem}* dans la table : {dedans}")

    print(f"\n=== 3. COMPILATION REELLE ({GCC.name}) ===")
    test_c = CUSTOM / "src" / "_verif_solidify.c"
    test_c.write_text(f'#include "solidify/{h.name}"\n', encoding="utf-8")
    p = subprocess.run(
        [str(GCC), "-fsyntax-only",
         f"-I{CUSTOM / 'src'}", f"-I{BERRY / 'src'}", f"-I{BERRY / 'default'}",
         f"-I{BERRY / 'generate'}", f"-I{RACINE / 'tasmota'}", str(test_c)],
        capture_output=True, text=True, cwd=CUSTOM / "src")
    sortie = ((p.stdout or "") + (p.stderr or "")).strip()
    if sortie:
        for ligne in sortie.splitlines()[:18]:
            print("   ", ligne)
    print(f"\n   rc = {p.returncode}")
    print("\n   ===> LE .h COMPILE. Le build peut etre lance."
          if p.returncode == 0 else
          "\n   ===> LE .h NE COMPILE PAS. Ne pas lancer de build.")
    sys.exit(p.returncode)
finally:
    # Ne rien laisser derriere : ces dossiers sont vides par le pre-script a
    # chaque build, mais autant ne pas polluer un `git status` entre-temps.
    for f in EMBEDDED.glob("*.be"):
        f.unlink()
    for hh in SOLIDIFY.glob("solidified_*.h"):
        try:
            hh.unlink()
        except OSError:
            pass  # cpptools tient parfois le .h fraichement ecrit
    verif = CUSTOM / "src" / "_verif_solidify.c"
    if verif.exists():
        try:
            verif.unlink()
        except OSError:
            pass
