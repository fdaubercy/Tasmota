"""Construit une extension Tasmota .tapp a partir d'un dossier.

Usage : gen_tapp.py <dossier> [--sortie x.tapp]

Le dossier doit contenir, A PLAT (aucun sous-dossier), `autoexec.be` et un `manifest.json`
valide dont la cle `name` est non vide. Sortie par defaut : `<dossier>.tapp` a cote du dossier.
Chaque `.be` est compile par le moteur de `verifie_berry.py` : une archive non verifiee ne part pas.
Aucune question, aucune dependance hors bibliotheque standard. Code de sortie 0 = construit,
1 = refus (motif sur stderr, rien d'ecrit, un ancien .tapp reste intact).

Format impose par le firmware (lib/libesp32/Zip-readonly-FS/src/ZipReadFS.cpp::ZipArchive::parse) :
ZIP_STORED, drapeaux a 0, taille compressee = taille d'origine, nom de 64 octets au plus ;
le firmware ignore tout ce qui suit le nom (champ supplementaire) et coupe le nom a '#'.
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verifie_berry  # noqa: E402

NOM_MAX = 64  # ZipReadFS.cpp : filename_size > 64 refuse
DATE_FIXE = (1980, 1, 1, 0, 0, 0)  # octets identiques pour une meme source
AVERTISSEMENTS = []  # avertissements de charte du dernier construit(), non bloquants (le CLI les affiche)
ENTIER = re.compile(r"^(0[xX][0-9a-fA-F]+|\d+)$")  # ce que int() de Berry lit dans read_extension_manifest
# Globales de solidify_all_python.be posees par le framework, donc absentes quand la carte compile l'extension (avant
# /autoexec.be) : un tel nom refuse la compilation, meme dans une fonction differee (be_parser.c::singlevaraux).
GLOBALES_DU_FRAMEWORK = ("drivers", "serveur", "diverses", "modules", "boolMute", "controleGeneral", "controleWeb", "controleLedTemoin",
                         "LOG_LEVEL_ERREUR", "LOG_LEVEL_INFO", "LOG_LEVEL_DEBUG", "LOG_LEVEL_DEBUG_PLUS", "logFonctions")


def _controle_nom(nom):
    try:
        octets = nom.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(f"{nom} : nom non ASCII")
    if len(octets) > NOM_MAX:
        raise ValueError(f"{nom} : nom de {len(octets)} octets, le firmware refuse plus de {NOM_MAX}")
    if "#" in nom:
        raise ValueError(f"{nom} : '#' interdit dans un nom (le firmware coupe le nom a '#')")


def _controle_manifest(chemin):
    try:
        m = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"manifest.json invalide : {e}")
    controle_manifeste(m)


def controle_manifeste(m):
    """Regles du manifeste sur l'objet deja lu ; ValueError sinon (aussi pour le formulaire de la Fabrique d'extensions)."""
    if not isinstance(m, dict):
        raise ValueError("manifest.json invalide : un objet JSON est attendu")
    if not isinstance(m.get("name"), str) or not m["name"].strip():
        raise ValueError("manifest.json : 'name' absent ou vide")
    for cle in ("version", "min_tasmota"):
        v = m.get(cle, 0)
        if isinstance(v, bool) or not (isinstance(v, int) or (isinstance(v, str) and ENTIER.match(v))):
            raise ValueError(f"manifest.json : '{cle}' doit etre un entier ou une chaine '0x...' (obtenu {v!r})")


def _controle_berry(dossier, fichiers_be):
    if not fichiers_be:
        return []
    try:
        racine = verifie_berry.trouve_racine()
        berry = verifie_berry.trouve_berry(racine)
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            rc = verifie_berry.verifie(racine, berry, fichiers_be, sans=GLOBALES_DU_FRAMEWORK)
    except SystemExit as e:
        raise ValueError(f"verification Berry impossible : {e.code}")
    lignes = sortie.getvalue().splitlines()
    if rc != 0:
        erreurs = [l for l in lignes if ": erreur:" in l] or lignes
        conseil = ("\nUn nom du framework n'existe pas encore quand la carte compile l'extension, avant /autoexec.be : "
                   "ecrire global.LOG_LEVEL_INFO, et importer logFonctions dans la fonction.") if "undeclared" in "".join(erreurs) else ""
        raise ValueError("Berry ne compile pas :\n" + "\n".join(erreurs) + conseil)
    return [l for l in lignes if ": avertissement:" in l]


def _controle_noms(dossier, noms):
    for nom in noms:
        if (dossier / nom).is_dir():
            raise ValueError(f"{nom} : sous-dossier interdit, l'archive est a plat")
        _controle_nom(nom)


def _controle_present(noms, requis):
    if requis not in noms:
        raise ValueError(f"{requis} absent du dossier")


def controle(dossier):
    """Les controles de construit sans rien ecrire, tous menes (affichage point par point de la Fabrique d'extensions).

    Rend (points, avertissements de charte) ; points = [{"point", "motif"}], motif None = bon. Comme construit, non
    reentrant (redirect_stdout, preambule partage de verifie_berry) : l'appelant concurrent tient un verrou.
    """
    dossier = Path(dossier).resolve()
    noms = sorted(e.name for e in os.scandir(dossier))
    points = []

    def essai(point, appel, *args):
        try:
            resultat = appel(*args)
        except (ValueError, OSError) as e:
            points.append({"point": point, "motif": str(e)})
            return None
        points.append({"point": point, "motif": None})
        return resultat

    def manifeste():
        _controle_present(noms, "manifest.json")
        _controle_manifest(dossier / "manifest.json")

    essai("Noms des fichiers", _controle_noms, dossier, noms)
    essai("autoexec.be", _controle_present, noms, "autoexec.be")
    essai("manifest.json", manifeste)
    avertissements = essai("Compilation Berry", _controle_berry, dossier,
                           [dossier / n for n in noms if n.endswith(".be") and (dossier / n).is_file()])
    return points, avertissements or []


def construit(dossier, sortie=None):
    """Ecrit le .tapp et rend son chemin ; ValueError (motif en francais) sinon. Rien d'imprime."""
    dossier = Path(dossier).resolve()
    if not dossier.is_dir():
        raise ValueError(f"{dossier} : dossier introuvable")
    sortie = Path(sortie).resolve() if sortie else dossier.parent / (dossier.name + ".tapp")
    if sortie.suffix != ".tapp":
        raise ValueError(f"{sortie.name} : la sortie doit se terminer par .tapp")
    if dossier in sortie.parents:
        raise ValueError(f"{sortie} : la sortie ne doit pas etre dans le dossier source")

    noms = sorted(e.name for e in os.scandir(dossier))
    _controle_noms(dossier, noms)
    _controle_present(noms, "autoexec.be")
    _controle_present(noms, "manifest.json")
    _controle_manifest(dossier / "manifest.json")
    AVERTISSEMENTS[:] = _controle_berry(dossier, [dossier / n for n in noms if n.endswith(".be")])

    # ecriture atomique : un echec laisse l'ancien .tapp et aucun temporaire
    fd, tmp = tempfile.mkstemp(suffix=".tmp", prefix=sortie.name, dir=sortie.parent)
    try:
        with os.fdopen(fd, "wb") as f, zipfile.ZipFile(f, "w", zipfile.ZIP_STORED) as z:
            for nom in noms:
                info = zipfile.ZipInfo(nom, DATE_FIXE)
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o644 << 16
                z.writestr(info, (dossier / nom).read_bytes())
        os.replace(tmp, sortie)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    return sortie


def main(argv=None):
    p = argparse.ArgumentParser(prog="gen_tapp", description=__doc__.split("\n")[0])
    p.add_argument("dossier")
    p.add_argument("--sortie", help="chemin du .tapp (defaut : <dossier>.tapp a cote du dossier)")
    a = p.parse_args(argv)
    try:
        chemin = construit(a.dossier, a.sortie)
    except (ValueError, OSError) as e:
        print(f"REFUS : {e}", file=sys.stderr)
        return 1
    with zipfile.ZipFile(chemin) as z:
        n = len(z.namelist())
    for l in AVERTISSEMENTS:
        print(l, file=sys.stderr)
    print(f"{chemin} : {n} fichier(s), {chemin.stat().st_size} octets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
