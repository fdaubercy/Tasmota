#!/usr/bin/env python3
"""Banc des deux reglages SCons du pre-script (plan temps-compilation A11) : Decider content-timestamp et implicit_cache.

Vrai SCons de PlatformIO, faux projet temporaire ; le « compilateur » recopie sa source. Montre ce qui declenche une
recompilation, et la limite connue d'implicit_cache (en-tete nouveau qui en masque un autre).
<Python de PlatformIO> outils_docs/scripts_python/build/test_scons_cache.py ; code 0 = vert.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCONS = next((Path.home() / ".platformio/packages/tool-scons").glob("scons.py"))
SCONSTRUCT = """
import shutil, SCons.Scanner.C
from pathlib import Path
DefaultEnvironment(tools=[])
env = Environment(tools=[], CPPPATH=["inc1", "inc2"])
env.Decider("content-timestamp")
SetOption("implicit_cache", 1)
def compile_(target, source, env):
    print("COMPILE")
    shutil.copy(str(source[0]), str(target[0]))
env.Append(BUILDERS={"Objet": Builder(action=compile_, source_scanner=SCons.Scanner.C.CScanner())})
env.Objet("a.o", "a.c")
if ARGUMENTS.get("genere"):                      # comme le LDF puis gen-berry-structures : date lue, puis fichier reecrit
    entete = File("inc1/genere.h")
    entete.exists()
    Path("inc1/genere.h").write_text(ARGUMENTS["genere"])
    if ARGUMENTS.get("oublie"):                  # le correctif de post_lto_parallele.py
        entete.clear_memoized_values()
"""
echecs = 0
horloge = time.time()


def ecrit(chemin, texte):
    global horloge
    horloge += 10                                # date toujours differente : le test ne depend pas de la vitesse
    Path(chemin).write_text(texte, encoding="utf-8")
    os.utime(chemin, (horloge, horloge))


def build(*args):
    time.sleep(1.1 if args else 0)               # l'en-tete genere prend la vraie date, a la seconde
    r = subprocess.run([sys.executable, str(SCONS), "-Q", "--warn=no-all", *args], capture_output=True, text=True)
    return r.returncode, "COMPILE" in r.stdout, r.stdout + r.stderr


def verifie(nom, attendu, *args):
    global echecs
    code, compile_, sortie = build(*args)
    ok = code == 0 and compile_ == attendu
    echecs += 0 if ok else 1
    print(("OK " if ok else "KO ") + f"{nom} : {'recompile' if compile_ else 'rien'}, code {code}")
    if not ok:
        print(sortie)


with tempfile.TemporaryDirectory() as d:
    os.chdir(d)
    os.makedirs("inc1")
    os.makedirs("inc2")
    Path("SConstruct").write_text(SCONSTRUCT, encoding="utf-8")
    ecrit("a.c", '#include "a.h"\n#include "c.h"\n')
    ecrit("inc1/a.h", "// a\n")
    ecrit("inc2/c.h", "// c\n")
    verifie("premier build", True)
    verifie("rien de change", False)
    ecrit("inc1/a.h", "// a\n")
    verifie("date changee, contenu identique", False)
    ecrit("inc1/a.h", "// a2\n")
    verifie("en-tete modifie", True)
    ecrit("inc1/b.h", "// b\n")
    ecrit("inc1/a.h", '#include "b.h"\n')
    verifie("nouvel include dans un en-tete", True)
    ecrit("inc1/b.h", "// b2\n")
    verifie("en-tete de second niveau modifie", True)
    ecrit("inc1/a.h", "// sans b\n")
    os.remove("inc1/b.h")
    verifie("include retire et en-tete supprime ensemble", True)
    ecrit("inc1/c.h", "// masque inc2/c.h\n")
    verifie("LIMITE : nouvel en-tete masquant un autre, non vu", False)
    ecrit("a.c", '#include "a.h"\n#include "c.h"\n// modifie\n')
    verifie("source modifiee : le masque est vu", True)
    ecrit("inc1/c.h", "// masque modifie\n")
    verifie("en-tete masquant modifie", True)
    ecrit("inc1/genere.h", "//0")
    ecrit("a.c", '#include "a.h"\n#include "c.h"\n#include "genere.h"\n')
    verifie("en-tete genere : premier build", True, "genere=//1", "oublie=1")
    verifie("en-tete genere reecrit apres lecture de sa date, sans correctif : non vu", False, "genere=//2")
    verifie("en-tete genere reecrit, avec correctif : vu", True, "genere=//3", "oublie=1")
    verifie("en-tete genere identique, avec correctif : rien", False, "genere=//3", "oublie=1")
    os.chdir(Path(__file__).parent)
print("VERT" if not echecs else f"ROUGE : {echecs} echec(s)")
sys.exit(1 if echecs else 0)
