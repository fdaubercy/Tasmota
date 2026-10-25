#!/usr/bin/env python3
"""Banc de copy_fs_image / remove_backup_data (pre_utilitaires_platformio.py), audit E6/P2.6.

copy_fs_image est accrochee DEUX fois par build (firmware.bin et littlefs.bin). Un second appel reel
ne doit ni recopier ni refaire l'inventaire des fichiers propres a la carte : avec un inventaire pris
APRES la premiere copie, les copies temporaires passeraient pour des fichiers de la carte et
resteraient dans son dossier apres le build.

Les fonctions sont extraites du source par ast puis executees dans un dossier temporaire (faux depot :
data/fs, data/json, data/sd, dossier de carte) avec un faux env. Rien du depot n'est ecrit.

    python outils_docs/scripts_python/build/test_copie_fs.py

Code de sortie 0 = vert, 1 = rouge.
"""
import ast
import os
import shutil
import sys
import tempfile

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pre_utilitaires_platformio.py")
FONCTIONS = ("list_files_recursive", "copy_fs_image", "remove_backup_data")


class SansCouleur:
    def __getattr__(self, nom):
        return ""


def charge(dossier_carte):
    """Espace de noms avec les vraies fonctions et une fausse classe Global."""
    arbre = ast.parse(open(SOURCE, encoding="utf-8").read())
    noeuds = [n for n in arbre.body if isinstance(n, ast.FunctionDef) and n.name in FONCTIONS]
    glob = next(n for n in arbre.body if isinstance(n, ast.ClassDef) and n.name == "Global")
    glob.body = [b for b in glob.body if not (isinstance(b, ast.Assign) and b.targets[0].id == "environnement")]
    module = ast.Module(body=[glob] + noeuds, type_ignores=[])
    espace = {"os": os, "sys": sys, "shutil": shutil, "Fore": SansCouleur(),
              "transform_name": lambda nom: dossier_carte,
              "modules_solidifies": lambda: set(), "modules_exclus": lambda: set(),
              "GetBuildFailures": lambda: []}
    exec(compile(module, SOURCE, "exec"), espace)
    espace["Global"].environnement = "tasmota32s3-banc"
    return espace


def ecris(chemin, texte="x"):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w") as f:
        f.write(texte)


def contenu(dossier):
    return sorted(os.path.relpath(os.path.join(r, f), dossier).replace(os.sep, "/")
                  for r, _, fs in os.walk(dossier) for f in fs)


def essai(appels):
    """Contenu du dossier de carte apres 'appels' copy_fs_image puis le nettoyage de fin de build."""
    racine = tempfile.mkdtemp()
    ici = os.getcwd()
    argv = sys.argv
    try:
        os.chdir(racine)
        ecris("data/fs/module.be")
        ecris("data/json/table.json")
        ecris("data/sd/css/main.css")
        carte = os.path.join(racine, "data", "lieu", "carte")
        ecris(os.path.join(carte, "_persist.json"))
        ecris(os.path.join(carte, "autoexec.be"))
        e = charge(carte)
        sys.argv = ["pio", "run", "-t", "upload"]
        for _ in range(appels):
            e["copy_fs_image"](None, None, None)
        pendant = contenu(carte)
        e["remove_backup_data"]("", "sortie_script", "")
        return pendant, contenu(carte)
    finally:
        sys.argv = argv
        os.chdir(ici)
        shutil.rmtree(racine, ignore_errors=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # le pre-script affiche des ✔ (cp1252 sinon)
    propres = ["_persist.json", "autoexec.be"]
    pendant_attendu = sorted(propres + ["json/table.json", "module.be", "sd/css/main.css"])
    echecs = 0
    for nom, appels in (("un accrochage (temoin : cas courant)", 1), ("deux accrochages (firmware.bin + littlefs.bin)", 2)):
        pendant, apres = essai(appels)
        ok = pendant == pendant_attendu and apres == propres
        echecs += not ok
        print("%s %s : pendant le build %s ; apres %s" % ("OK" if ok else "KO", nom, pendant, apres))
    print("VERT" if echecs == 0 else "ROUGE : %d echec(s)" % echecs)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
