"""Rejoue la chaine COMPLETE de gen-berry-structures.py, puis compile.

    1. solidification  (etape 1 du post-script)
    2. coc             (etape 2 : regenere la table des chaines)
    3. compilation du .h avec le vrai compilateur croise

Mon test precedent sautait l'etape 2, d'ou un faux echec
(`be_const_str_modbusFonctions_reglageModbus undeclared`) : la table datait du
build d'avant la conversion.

generate/ est gitignore et regenere a chaque build : le reecrire est sans risque.
Duree : secondes, contre 2h16 pour un build complet.
"""
import os
import subprocess
from pathlib import Path

RACINE = Path(r"C:\Users\fdaub\Documents\Github\Tasmota")
CUSTOM = RACINE / "lib" / "libesp32" / "berry_custom"
EMBEDDED = CUSTOM / "src" / "embedded"
SOLIDIFY = CUSTOM / "src" / "solidify"
BERRY = RACINE / "lib" / "libesp32" / "berry"
LVGL = RACINE / "lib" / "libesp32_lvgl"
PYTHON = r"C:\Users\fdaub\.platformio\penv\Scripts\python.exe"
SOURCE = RACINE / "data" / "fs" / "modbusFonctions.be"
SCRATCH = Path(__file__).parent
GCC = next((Path(os.environ["USERPROFILE"]) / ".platformio" / "packages" /
            "toolchain-xtensa-esp-elf" / "bin").glob("xtensa-esp-elf-gcc.exe"))
ENV = {**os.environ, "PYTHONPATH": str(BERRY), "PYTHONUTF8": "1"}

try:
    for f in EMBEDDED.glob("*.be"):
        f.unlink()
    for h in SOLIDIFY.glob("solidified_*.h"):
        h.unlink()
    (EMBEDDED / "modbusFonctions.be").write_bytes(SOURCE.read_bytes())

    print("=== 1. SOLIDIFICATION ===")
    r = subprocess.run(
        [PYTHON, "-m", "berry_port", "-s", "-g", "solidify_all_python.be"],
        cwd=CUSTOM, capture_output=True, text=True, env=ENV)
    print("   rc =", r.returncode)
    if r.returncode != 0:
        print(((r.stdout or "") + (r.stderr or ""))[:600])
        raise SystemExit(1)
    h = SOLIDIFY / "solidified_modbusFonctions.h"
    txt = h.read_text(encoding="utf-8", errors="replace")
    print(f"   {h.name} : {h.stat().st_size:,} octets, "
          f"{txt.count('be_local_closure(')} closures, "
          f"{txt.count('be_local_closure(_anonymous_,')} anonymes")

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
    dedans = "be_const_str_modbusFonctions_reglageModbus" in strtab.read_text(
        encoding="utf-8", errors="replace")
    print(f"   be_const_str_modbusFonctions_reglageModbus dans la table : {dedans}")

    print("\n=== 3. COMPILATION REELLE ===")
    test_c = SCRATCH / "compile_modbus.c"
    test_c.write_text('#include "solidify/solidified_modbusFonctions.h"\n', encoding="utf-8")
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
finally:
    for f in EMBEDDED.glob("*.be"):
        f.unlink()
    for hh in SOLIDIFY.glob("solidified_*.h"):
        try:
            hh.unlink()
        except OSError:
            pass
