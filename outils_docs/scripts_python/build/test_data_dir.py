#!/usr/bin/env python3
"""Banc du data_dir de adapteParametresPlatformio_override (pre_utilitaires_platformio.py), 2026-10-26.

Defaut corrige : le pre-script reecrivait `data_dir` dans platformio_override.ini PENDANT le `pio run`, mais
PlatformIO avait deja lu ce fichier (builder/main.py : PROJECT_DATA_DIR = config data_dir) ; un `buildfs` lance
seul construisait donc l'image avec le dossier de l'env du lancement PRECEDENT (journal du buildfs P4 du
2026-10-26 : copy_fs_image(... p4 ..., data\\garage\\tasmota32s3-capteurs-cuve-modbus)). Le pre-script doit aussi
poser PROJECT_DATA_DIR dans l'env SCons du lancement en cours (lu par la plateforme, main.py : DataToBin).

Le pre-script ne s'importe pas hors PlatformIO : ses fonctions sont extraites du source par ast et executees avec
un faux env, sur un faux platformio_override.ini dans un dossier temporaire. Rien du depot n'est ecrit.

    python outils_docs/scripts_python/build/test_data_dir.py

Code de sortie 0 = vert, 1 = rouge.
"""
import ast
import configparser
import os
import re
import shutil
import sys
import tempfile

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pre_utilitaires_platformio.py")
CUVE = "tasmota32s3-garage-capteurs-cuve-modbus"
OVERRIDE = "[platformio]\ndata_dir = data/garage/tasmota32s3-rideau-garage-modbus\n\n[env]\n"


class FauxEnv:
    def __init__(self, racine):
        self.racine = racine
        self.remplace = {}

    def subst(self, chaine):
        return self.racine if chaine == "$PROJECT_DIR" else chaine

    def Replace(self, **valeurs):
        self.remplace.update(valeurs)


class SansCouleur:
    def __getattr__(self, nom):
        return ""


class FauxGlobal:
    environnement = CUVE


def charge(env):
    """Toutes les fonctions du pre-script (pas son code de niveau module), avec un faux env."""
    arbre = ast.parse(open(SOURCE, encoding="utf-8").read())
    fonctions = [n for n in arbre.body if isinstance(n, ast.FunctionDef)]
    espace = {"env": env, "re": re, "os": os, "shutil": shutil, "configparser": configparser, "json": __import__("json"),
              "Fore": SansCouleur(), "Global": FauxGlobal}
    exec(compile(ast.Module(body=fonctions, type_ignores=[]), SOURCE, "exec"), espace)
    return espace


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # le pre-script affiche des ✔ (cp1252 sinon)
    echecs = []

    def verifie(obtenu, attendu, libelle):
        print(("OK  " if obtenu == attendu else "KO  ") + libelle + ("" if obtenu == attendu else
              f"\n      obtenu  : {obtenu!r}\n      attendu : {attendu!r}"))
        if obtenu != attendu:
            echecs.append(libelle)

    ici = os.getcwd()
    with tempfile.TemporaryDirectory() as racine:
        os.chdir(racine)                                  # le pre-script ecrit platformio_override.ini en relatif
        try:
            with open("platformio_override.ini", "w", encoding="utf-8") as f:
                f.write(OVERRIDE)
            env = FauxEnv(racine)
            charge(env)["adapteParametresPlatformio_override"]()
            attendu = os.path.join(racine, "data", "garage", "tasmota32s3-capteurs-cuve-modbus")
            verifie(os.path.normcase(os.path.normpath(env.remplace.get("PROJECT_DATA_DIR", ""))),
                    os.path.normcase(attendu), "PROJECT_DATA_DIR du lancement en cours = dossier de l'env (pas le precedent)")
            texte = open("platformio_override.ini", encoding="utf-8").read()
            verifie(bool(re.search(r"data_dir\s*=\s*data/garage/tasmota32s3-capteurs-cuve-modbus", texte)), True,
                    "temoin : platformio_override.ini reecrit comme avant (lancements suivants, VS Code)")
            verifie(os.path.isdir(attendu), True, "temoin : dossier de l'env cree s'il manquait")
        finally:
            os.chdir(ici)
    print("VERT" if not echecs else f"ROUGE : {len(echecs)} echec(s)")
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())
