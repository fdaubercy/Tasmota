#!/usr/bin/env python3
"""Purge du cache objet de PlatformIO (`.cache`, option `build_cache_dir` de platformio.ini), plan temps-compilation A5.

Le cache garde chaque .o compile (cle = contenu + options) : apres une purge de .pio/build (changement d'env), les
objets sont recopies au lieu d'etre recompiles. Il n'est jamais vide et grossit sans fin. SCons remet la date de
modification d'un objet a l'instant ou il le reprend (SCons/CacheDir.py::CacheRetrieveFunc, os.utime) : cette date
est donc celle de la DERNIERE UTILISATION, et un objet plus vieux que N jours n'a servi a aucun build depuis.

Seuls les fichiers des sous-dossiers de .cache sont supprimes, jamais son fichier `config` (format du cache SCons).
Supprimer un objet utile ne casse rien : il sera recompile une fois. Refus pendant un build (meme detection que la
page build : .claude/hooks/garde_build.py::builds_en_cours).

    python outils_docs/scripts_python/maintenance/purge_cache_build.py [--jours 30] [--dry-run]

--dry-run : affiche la taille du cache et ce qui serait libere, sans rien supprimer (permis pendant un build).
Code de sortie : 0 = fait, 1 = refus (build en cours, detection impossible, cache absent).
"""
import argparse
import os
import sys
import time
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[3]
CACHE = DEPOT / ".cache"


def builds_en_cours_defaut():
    """Libelles des builds en cours, [] si aucun, None si la detection a echoue."""
    sys.path.append(str(DEPOT / ".claude" / "hooks"))
    try:
        import garde_build
        return garde_build.builds_en_cours()
    except Exception:                                    # noqa: BLE001 - detection impossible = refus
        return None


def inventaire(cache, jours, maintenant=None):
    """(total_octets, [(chemin, octets)] des objets inutilises depuis plus de `jours`)."""
    limite = (maintenant or time.time()) - jours * 86400
    total, vieux = 0, []
    for sous in os.scandir(cache):
        if not sous.is_dir(follow_symlinks=False):   # le fichier `config` du cache reste
            continue
        for f in os.scandir(sous.path):
            if not f.is_file(follow_symlinks=False):
                continue
            st = f.stat()
            total += st.st_size
            if st.st_mtime < limite:
                vieux.append((f.path, st.st_size))
    return total, vieux


def mo(octets):
    return f"{octets / 1048576:.0f} Mo"


def main(arguments=None, cache=CACHE, builds_en_cours=builds_en_cours_defaut):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--jours", type=int, default=30, help="age minimal (derniere utilisation) d'un objet supprime")
    p.add_argument("--dry-run", action="store_true", help="n'affiche que ce qui serait libere")
    args = p.parse_args(arguments)
    if args.jours < 1:
        print("REFUS : --jours doit valoir au moins 1")
        return 1
    if not Path(cache).is_dir():
        print(f"REFUS : pas de cache objet dans {cache}")
        return 1
    if not args.dry_run:
        builds = builds_en_cours()
        if builds is None:
            print("REFUS : detection des builds impossible, rien n'est supprime")
            return 1
        if builds:
            print(f"REFUS : build en cours ({', '.join(builds)}), rien n'est supprime")
            return 1
    total, vieux = inventaire(cache, args.jours)
    liberable = sum(o for _, o in vieux)
    print(f"Cache {cache} : {mo(total)} ; {len(vieux)} objet(s) inutilise(s) depuis plus de {args.jours} jours : {mo(liberable)}")
    if args.dry_run:
        print("--dry-run : rien n'est supprime")
        return 0
    supprimes = 0
    for chemin, octets in vieux:
        try:
            os.remove(chemin)
            supprimes += octets
        except OSError:                              # objet pris entre-temps : il reste, sans gravite
            pass
    print(f"Libere : {mo(supprimes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
