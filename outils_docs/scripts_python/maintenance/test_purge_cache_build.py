#!/usr/bin/env python3
"""Banc de purge_cache_build.py : faux cache SCons dans un dossier temporaire, dates forcees ; le vrai .cache n'est
jamais touche, la detection des builds est simulee.

    python outils_docs/scripts_python/maintenance/test_purge_cache_build.py

Code de sortie 0 = vert, 1 = rouge.
"""
import contextlib
import io
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import purge_cache_build as p                                      # noqa: E402

ECHECS = []


def verifie(ok, libelle):
    print(("OK   " if ok else "KO   ") + libelle)
    if not ok:
        ECHECS.append(libelle)


def faux_cache(racine):
    """config + ab/vieux (40 j) + ab/recent (2 j) + cd/vieux2 (31 j) ; rend les chemins."""
    maintenant = time.time()
    (racine / "ab").mkdir()
    (racine / "cd").mkdir()
    fichiers = {"config": (racine / "config", 400), "vieux": (racine / "ab" / "vieux", 40),
                "recent": (racine / "ab" / "recent", 2), "vieux2": (racine / "cd" / "vieux2", 31)}
    for chemin, age in fichiers.values():
        chemin.write_bytes(b"x" * 1000)
        os.utime(chemin, (maintenant - age * 86400,) * 2)
    return {nom: chemin for nom, (chemin, _) in fichiers.items()}


def lance(cache, arguments, builds):
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        code = p.main(arguments, cache=cache, builds_en_cours=lambda: builds)
    return code, sortie.getvalue()


def main():
    with tempfile.TemporaryDirectory() as d:
        cache = Path(d)
        f = faux_cache(cache)
        code, sortie = lance(cache, ["--dry-run"], ["build en cours"])
        verifie(code == 0 and all(c.exists() for c in f.values()), "--dry-run pendant un build : rien supprime")
        verifie("2 objet(s)" in sortie, "--dry-run compte 2 objets de plus de 30 jours (config exclu)")

        code, _ = lance(cache, [], ["pio run -e x"])
        verifie(code == 1 and all(c.exists() for c in f.values()), "build en cours : refus, rien supprime")
        code, _ = lance(cache, [], None)
        verifie(code == 1 and all(c.exists() for c in f.values()), "detection impossible : refus, rien supprime")

        code, _ = lance(cache, [], [])
        verifie(code == 0 and not f["vieux"].exists() and not f["vieux2"].exists(), "purge : objets de 40 et 31 jours supprimes")
        verifie(f["recent"].exists(), "temoin : objet de 2 jours garde")
        verifie(f["config"].exists(), "fichier config du cache garde, malgre ses 400 jours")

        code, _ = lance(cache, ["--jours", "0"], [])
        verifie(code == 1 and f["recent"].exists(), "--jours 0 refuse")
    code, _ = lance(Path(d) / "absent", [], [])
    verifie(code == 1, "cache absent : refus")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
