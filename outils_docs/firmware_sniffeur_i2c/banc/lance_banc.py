"""Compile et lance banc/test_machine.cpp sur le PC (code de sortie 0 = vert).

Compilateur : g++ s'il est dans le PATH, sinon cl.exe des Build Tools Visual Studio (trouve par vswhere).
Les binaires vont dans le dossier temporaire, jamais dans le depot.
Option --source <fichier.h> : compile le banc contre une autre machine (temoin mute, copie du scratchpad).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ICI, "test_machine.cpp")
VSWHERE = os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe")


def vcvars():
    if not os.path.exists(VSWHERE):
        return None
    racine = subprocess.run([VSWHERE, "-latest", "-products", "*", "-property", "installationPath"],
                            capture_output=True, text=True).stdout.strip()
    chemin = os.path.join(racine, r"VC\Auxiliary\Build\vcvars64.bat")
    return chemin if racine and os.path.exists(chemin) else None


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--source", help="machine_i2c.h de remplacement (temoin)")
    args = p.parse_args()
    dossier = tempfile.mkdtemp(prefix="banc_machine_i2c_")
    source = SOURCE
    if args.source:                     # le banc inclut "../src/machine_i2c.h" : on recree cette arborescence
        os.makedirs(os.path.join(dossier, "src"))
        os.makedirs(os.path.join(dossier, "banc"))
        shutil.copy(args.source, os.path.join(dossier, "src", "machine_i2c.h"))
        source = shutil.copy(SOURCE, os.path.join(dossier, "banc", "test_machine.cpp"))
    exe = os.path.join(dossier, "test_machine.exe")
    if shutil.which("g++"):
        compile_ = ["g++", "-std=c++17", "-Wall", "-o", exe, source]
    elif vcvars():
        compile_ = f'"{vcvars()}" >nul && cl /nologo /EHsc /std:c++17 /W3 /Fo"{dossier}\\\\" /Fe"{exe}" "{source}"'
    else:
        print("Aucun compilateur C++ (g++ ou Build Tools Visual Studio) : banc non lance.")
        return 2
    r = subprocess.run(compile_, shell=isinstance(compile_, str), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        print("ROUGE : compilation du banc en echec")
        return 1
    return subprocess.run([exe]).returncode


if __name__ == "__main__":
    sys.exit(main())
