#!/usr/bin/env python3
"""Banc de increment_config_holder (pre_utilitaires_platformio.py), audit E5/P2.3.

Le pre-script ne s'importe pas hors PlatformIO (Import("env"), SCons) : la fonction est
extraite du source par ast puis executee avec un faux env, sur un faux
user_config_override.h dans un dossier temporaire. Rien du depot n'est ecrit.

    python outils_docs/scripts_python/build/test_config_holder.py

Code de sortie 0 = vert, 1 = rouge.
"""
import ast
import os
import re
import sys
import tempfile

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pre_utilitaires_platformio.py")


class FauxEnv:
    def __init__(self, dossier, flags=()):
        self.dossier = dossier
        self.flags = list(flags)

    def get(self, cle):
        return self.flags if cle == "BUILD_FLAGS" else None

    def subst(self, chaine):
        return self.dossier if chaine == "$PROJECT_SRC_DIR" else chaine


class SansCouleur:
    def __getattr__(self, nom):
        return ""


def charge_fonction(env):
    arbre = ast.parse(open(SOURCE, encoding="utf-8").read())
    noeud = next(n for n in arbre.body if isinstance(n, ast.FunctionDef) and n.name == "increment_config_holder")
    module = ast.Module(body=[noeud], type_ignores=[])
    espace = {"env": env, "re": re, "os": os, "Fore": SansCouleur()}
    exec(compile(module, SOURCE, "exec"), espace)
    return espace["increment_config_holder"]


def essai(valeur):
    """Rend la valeur de CFG_HOLDER apres un appel, ou le nom de l'exception levee."""
    with tempfile.TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "user_config_override.h")
        with open(chemin, "w") as f:
            f.write("#ifndef X\n\t\t#define CFG_HOLDER \t\t%d\t\t\t// [Reset 1]\n#endif\n" % valeur)
        try:
            charge_fonction(FauxEnv(dossier))()
        except Exception as e:
            return type(e).__name__
        m = re.search(r"#define CFG_HOLDER\s+(\d+)", open(chemin).read())
        return int(m.group(1)) if m else None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # le pre-script affiche un ✔ (cp1252 sinon)
    echecs = 0
    cas = [
        ("1543 -> 1544 (temoin : cas courant)", 1543, 1544),
        ("65534 -> 65535", 65534, 65535),
        ("65535 -> 1 (rebouclage, sans exception)", 65535, 1),
    ]
    for nom, depart, attendu in cas:
        obtenu = essai(depart)
        ok = obtenu == attendu
        echecs += 0 if ok else 1
        print("%s %s : attendu %s, obtenu %s" % ("OK" if ok else "KO", nom, attendu, obtenu))
    print("VERT" if echecs == 0 else "ROUGE : %d echec(s)" % echecs)
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
