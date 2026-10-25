"""Banc du hook .claude/hooks/garde_build.py : un `pio run` de cible d'outil n'est pas un build.

Code de sortie 0 = vert. Aucun PowerShell, aucun pio : les lignes de commande des processus sont donnees
a analyse_commandes(), la fonction pure qu'appelle builds_en_cours() ; main() est appele avec une
entree simulee et un builds_en_cours() remplace.
Lancer : "%USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe" -u test_garde_build.py

Pourquoi : une cible d'outil (annuaire, pont serie, sniffeurs, syslog, testeur UDP, synchro du fork, page de
build) vit tant que l'outil vit. Prise pour un build, elle faisait attendre sans fin la page de build et
refuser tout `pio run` de Claude. Lignes reelles constatees le 2026-10-25 :
    platformio.exe run --target annuaire --environment <env>
    python.exe ...\\scons.py -Q ... --sconstruct ...\\main.py PIOVERBOSE=0 ... BUILD_SCRIPT=... annuaire
"""

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
sys.path.insert(0, str(DEPOT / ".claude" / "hooks"))
import garde_build as gb                           # noqa: E402

ECHECS = []
PIO = r'"C:\Users\fdaub\.platformio\penv\Scripts\platformio.exe"'
PY = r'"C:\Users\fdaub\.platformio\penv\Scripts\python.exe"'
SCONS = (PY + r' "C:\Users\fdaub\.platformio\packages\tool-scons\scons.py" -Q --warn=no-no-parallel-support'
         r' --jobs 16 --sconstruct "C:\Users\fdaub\.platformio\penv\Lib\site-packages\platformio\builder\main.py"'
         r' PIOVERBOSE=0 ISATTY=0 PIOENV=tasmota32s3-garage-capteurs-cuve-modbus PIOTEST_RUNNING_NAME=x'
         r' PROJECT_CONFIG=QzpcVXNlcnM= PROGRAM_ARGS=W10= BUILD_SCRIPT=QzpcVXNlcnNcZmRh')


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def test_vrais_builds():
    """Temoins : le comportement d'avant pour un vrai build."""
    verifie(gb.analyse_commandes([PIO + " run -e tasmota32-x"]), ["tasmota32-x"], "vrai build : compilation")
    verifie(gb.analyse_commandes([PIO + " run -e tasmota32-x -t upload --upload-port COM12"]), ["tasmota32-x upload"],
            "vrai build : upload")
    verifie(gb.analyse_commandes([PIO + " -c vscode run --environment tasmota32-x --target erase_upload"]),
            ["tasmota32-x erase_upload"], "vrai build : option globale -c, cible erase_upload")
    verifie(gb.analyse_commandes([SCONS]), ["scons"], "vrai build : scons sans cible (compilation)")
    verifie(gb.analyse_commandes([SCONS + " upload"]), ["scons"], "vrai build : scons de cible upload")
    verifie(gb.analyse_commandes([SCONS + " __idedata"]), ["scons"],
            "vrai build : __idedata (reconstruction d'IntelliSense) reste un build")
    verifie(gb.analyse_commandes([PY + r" -m SCons -Q"]), ["scons"],
            "vrai build : ligne scons sans scons.py reconnaissable -> build")
    verifie(gb.analyse_commandes([PIO + " run -e x -t upload -t annuaire"]), ["x upload"],
            "vrai build : une cible d'outil melee a une vraie cible -> build")
    verifie(gb.analyse_commandes([PY + " -u annuaire_outils.py --http 7600", PIO + " home --port 8008"]), [],
            "temoin : l'outil lui-meme et pio home ne sont pas des builds")


def test_cibles_outils():
    for cible in sorted(gb.CIBLES_OUTILS):
        verifie(gb.analyse_commandes([PIO + f" run --target {cible} --environment tasmota32s3-cave-serveur-rly",
                                      SCONS + f" {cible}"]), [], f"cible d'outil ignoree : {cible} (pio run et scons)")
    verifie(gb.analyse_commandes([PIO + " run -e x -t annuaire"]), [], "cible d'outil : forme courte -t")
    verifie(gb.analyse_commandes([PIO + " run -e x --target=pont_serie"]), [], "cible d'outil : forme --target=")
    verifie(gb.analyse_commandes([PY + ' -m platformio run --target "sniffeur_mqtt" -e x']), [],
            "cible d'outil : python -m platformio, cible entre guillemets")
    verifie(gb.analyse_commandes([PIO + " run --target annuaire -e a", SCONS + " annuaire", PIO + " run -e b"]), ["b"],
            "cible d'outil + vrai build en meme temps : seul le vrai build est cite")
    verifie(gb.analyse_commandes([PIO + " run --target annuaire -e a", SCONS + " annuaire", SCONS]), ["scons"],
            "cible d'outil + scons d'un vrai build : build")


def noms_cibles():
    """NOM_CIBLE de chaque build/cible_*.py (importables hors SCons : Import n'y existe pas)."""
    noms = {}
    for chemin in sorted(ICI.glob("cible_*.py")):
        spec = importlib.util.spec_from_file_location(chemin.stem, chemin)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        noms[chemin.stem] = module.NOM_CIBLE
    return noms


def test_liste_alignee():
    noms = noms_cibles()
    verifie(len(noms) >= 8, True, f"liste : {len(noms)} cibles d'outils trouvees dans build/")
    verifie(sorted(gb.CIBLES_OUTILS), sorted(noms.values()),
            "liste : CIBLES_OUTILS de garde_build = les NOM_CIBLE des cible_*.py")


def lance_main(commande, builds):
    """(code, stderr) de main() pour une commande Bash, avec builds_en_cours() remplace."""
    vrai_builds, vrai_stdin = gb.builds_en_cours, sys.stdin
    gb.builds_en_cours = lambda: builds
    sys.stdin = io.StringIO(json.dumps({"tool_input": {"command": commande}}))
    erreur = io.StringIO()
    try:
        with contextlib.redirect_stderr(erreur):
            code = gb.main()
    finally:
        gb.builds_en_cours, sys.stdin = vrai_builds, vrai_stdin
    return code, erreur.getvalue()


def test_main_inchange():
    code, texte = lance_main("pio run -e tasmota32-x", ["tasmota32-y upload"])
    verifie((code, texte.startswith("Refuse : un build PlatformIO est deja en cours (tasmota32-y upload)")), (2, True),
            "main : vrai build en cours -> refus (code 2), message d'avant")
    verifie(lance_main("pio run -e tasmota32-x", [])[0], 0, "main : rien en cours -> autorise")
    verifie(lance_main("pio run -e tasmota32-x", None)[0], 1, "main : detection impossible -> 1, non bloquant")
    verifie(lance_main("git status", ["x"])[0], 0, "main : temoin, commande sans pio run -> autorisee")


def principal():
    for test in (test_vrais_builds, test_cibles_outils, test_liste_alignee, test_main_inchange):
        test()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
