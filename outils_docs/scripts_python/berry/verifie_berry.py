r"""Verifie la syntaxe des fichiers Berry de data/ avec le berry.exe du depot.

UTILISATION
-----------
  python verifie_berry.py                  tous les .be de data/ (hors *sauvegarde*)
  python verifie_berry.py f1.be f2.be      seulement ces fichiers
  python verifie_berry.py --surveille      reverifie tout a chaque modification d'un .be

  Chemin relatif : interprete depuis la racine du depot.
  Code de sortie : 0 = tout compile, 1 = erreur(s) Berry, 2 = verification invalide.

FORMAT DE SORTIE
----------------
  data/fs/udpFonctions.be:42: erreur: 'zz' undeclared (first use in this function)

C'est le format que lit le problemMatcher "berry" des taches VS Code (tasks.json du
profil) : les erreurs arrivent dans l'onglet Problemes, et Error Lens les ecrit au
bout de la ligne fautive. --surveille est la tache lancee a l'ouverture du dossier :
c'est elle qui donne la verification a l'enregistrement.

CE QUI EST VERIFIE
------------------
Chaque fichier passe par compile(source), UN seul argument : le 2e argument de
compile() est un MODE, pas un nom de chunk ; avec un mode inconnu rien n'est compile
et tout sort vert (faux vert du 2026-10-11, tasks/lessons.md).
Les globales declarees sont celles du solidifieur du build : la liste `globs` de
lib/libesp32/berry_custom/solidify_all_python.be, relue a chaque passe. Une globale
non declaree utilisee dans une fonction est donc refusee ICI comme elle le serait au
build ('logFonctions undeclared', 2026-10-04). Le code n'est jamais execute.

TEMOIN
------
Chaque passe commence par un source qui DOIT etre refuse (globale non declaree).
S'il compile, la verification ne mesure rien : message et code 2.

CE QU'IL NE TOUCHE PAS
----------------------
Lit data/ et solidify_all_python.be ; n'ecrit qu'un preambule .be dans le dossier
temporaire du systeme. N'ecrit jamais dans lib/libesp32/berry_custom : sans risque
pendant un build.
"""
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TEMOIN = "def f() return temoin_non_declare end"
MARQUE_DEBUT = "[verifie_berry] debut"
MARQUE_FIN = "[verifie_berry] fin"


def trouve_racine() -> Path:
    """Racine du depot, deduite de l'emplacement de ce script."""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


def trouve_berry(racine: Path) -> Path:
    """L'interpreteur Berry natif livre avec le depot."""
    for c in (racine / "lib" / "libesp32" / "berry" / "berry.exe",
              racine / "lib" / "libesp32" / "berry" / "berry"):
        if c.exists():
            return c
    sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/.")


def lit_globs(racine: Path) -> list:
    """Les globales declarees par le solidifieur du build (var globs = "a,b," "c,...")."""
    src = (racine / "lib" / "libesp32" / "berry_custom" / "solidify_all_python.be").read_text(encoding="utf-8")
    m = re.search(r'var globs = (.*?)\n\s*\n', src, re.S)
    if not m:
        sys.exit("ERREUR : liste 'globs' introuvable dans solidify_all_python.be.")
    noms = []
    for morceau in re.findall(r'"([^"]*)"', m.group(1)):
        noms += [n for n in morceau.split(",") if n]
    return noms


def fichiers_data(racine: Path) -> list:
    """Tous les .be de data/, hors dossiers de sauvegarde."""
    return sorted(p for p in (racine / "data").rglob("*.be")
                  if not any("sauvegarde" in part for part in p.parts))


def ecrit_preambule(globs: list) -> Path:
    """Script Berry : declare les globales, verifie le temoin, compile chaque argument."""
    lignes = ["import global"]
    lignes += [f"global.{n} = nil" for n in globs]
    lignes += [
        "class Driver end",
        "try",
        f'  compile("{TEMOIN}")',
        '  print("TEMOIN_KO")',
        "except .. as e, m",
        '  print("TEMOIN_OK")',
        "end",
        "for f: _argv[1..]",
        "  var fh = open(f)  var s = fh.read()  fh.close()",
        "  try",
        "    compile(s)",
        "  except .. as e, m",
        '    print("ERR\\t" + f + "\\t" + str(m))',
        "  end",
        "end",
    ]
    chemin = Path(tempfile.gettempdir()) / "verifie_berry_preambule.be"
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return chemin


def verifie(racine: Path, berry: Path, fichiers: list) -> int:
    """Une passe : affiche les erreurs au format fichier:ligne: erreur: message."""
    preambule = ecrit_preambule(lit_globs(racine))
    relatifs = [str(f.relative_to(racine) if f.is_relative_to(racine) else f).replace("\\", "/")
                for f in fichiers]
    r = subprocess.run([str(berry), str(preambule)] + relatifs, cwd=str(racine),
                       capture_output=True, encoding="utf-8", errors="replace")
    sortie = (r.stdout or "").splitlines()

    if "TEMOIN_OK" not in sortie:
        print(f"{relatifs[0] if relatifs else 'data'}:1: erreur: verification INVALIDE - "
              f"le temoin n'a pas ete refuse (rc={r.returncode}) {(r.stderr or '').strip()}")
        return 2

    nb_erreurs = 0
    for ligne in sortie:
        if not ligne.startswith("ERR\t"):
            continue
        _, fichier, message = ligne.split("\t", 2)
        m = re.match(r"string:(\d+):\s*(.*)", message)
        num, texte = (m.group(1), m.group(2)) if m else ("1", message)
        print(f"{fichier}:{num}: erreur: {texte}")
        nb_erreurs += 1
    print(f"{len(relatifs)} fichier(s) verifie(s), {nb_erreurs} erreur(s).")
    return 1 if nb_erreurs else 0


def empreinte(racine: Path) -> dict:
    """Date de modification de chaque .be suivi et de la liste globs."""
    suivis = fichiers_data(racine) + [racine / "lib" / "libesp32" / "berry_custom" / "solidify_all_python.be"]
    return {p: p.stat().st_mtime for p in suivis if p.exists()}


def surveille(racine: Path, berry: Path) -> None:
    """Boucle de la tache VS Code : une passe complete a chaque changement.

    Toujours TOUS les fichiers : le problemMatcher d'une tache de fond efface ses
    problemes au marqueur de debut ; une passe partielle en ferait disparaitre.
    """
    precedente = None
    while True:
        courante = empreinte(racine)
        if courante != precedente:
            print(MARQUE_DEBUT, flush=True)
            verifie(racine, berry, fichiers_data(racine))
            print(MARQUE_FIN, flush=True)
            precedente = courante
        time.sleep(1)


def main() -> int:
    sys.stdout.reconfigure(errors="replace", line_buffering=True)
    racine = trouve_racine()
    berry = trouve_berry(racine)
    args = sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if args == ["--surveille"]:
        try:
            surveille(racine, berry)
        except KeyboardInterrupt:
            return 0
    fichiers = [(racine / a).resolve() if not Path(a).is_absolute() else Path(a) for a in args]
    fichiers = [f for f in fichiers if f.suffix == ".be"] if fichiers else fichiers_data(racine)
    if not fichiers:
        print("Aucun fichier .be a verifier.")
        return 0
    return verifie(racine, berry, fichiers)


if __name__ == "__main__":
    sys.exit(main())
