#!/usr/bin/env python3
"""Banc de ino_stable.py. <Python de PlatformIO> outils_docs/scripts_python/build/test_ino_stable.py ; code 0 = vert."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ino_stable  # noqa: E402

echecs = 0


def verifie(nom, ok):
    global echecs
    echecs += 0 if ok else 1
    print(("OK " if ok else "KO ") + nom)


reel = tempfile.mkstemp
vus = []
f = ino_stable.enveloppe(lambda env: vus.append(tempfile.mkstemp()[1]) or env, "essai")
verifie("le resultat de la conversion est rendu", f("e") == "e")
f("e")
verifie("meme nom fixe a chaque appel", vus[0] == vus[1] and vus[0].endswith("tasmota_ino_essai"))
verifie("mkstemp remis apres l'appel", tempfile.mkstemp is reel)
verifie("nom propre a l'env", ino_stable.enveloppe(lambda e: tempfile.mkstemp()[1], "autre")(0).endswith("tasmota_ino_autre"))


def plante(_):
    raise RuntimeError


try:
    ino_stable.enveloppe(plante, "essai")(0)
except RuntimeError:
    pass
verifie("mkstemp remis apres une exception", tempfile.mkstemp is reel)
try:
    import platformio.builder.tools as outils
    source = (Path(outils.__file__).parent / "pioino.py").read_text(encoding="utf-8")
    verifie("pioino.py n'utilise que le chemin rendu par mkstemp", "tempfile.mkstemp()[1]" in source)
except ImportError:
    verifie("platformio importable (lancer avec le Python de PlatformIO)", False)
print("VERT" if not echecs else f"ROUGE : {echecs} echec(s)")
sys.exit(1 if echecs else 0)
