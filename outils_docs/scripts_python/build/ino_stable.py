"""tasmota.ino.cpp identique d'un build a l'autre (plan tasks/plans/temps-compilation.md, A11, 2026-11-01).

PlatformIO (`pioino.py::InoToCPPConverter._gcc_preprocess`) passe les .ino par `g++ -E` depuis un fichier de
`tempfile.mkstemp()`, au nom aleatoire, et g++ ecrit ce nom en ligne 1 de la sortie. Le fichier change donc a chaque
`pio run`, meme sans aucune modification : compilation de ses 8 Mo et edition de liens LTO refaites (~10 min), jamais de
reprise du cache objet. Mesure du 01/11 : deux generations ne different QUE par cette ligne ; `--debug=explain` :
« rebuilding tasmota.ino.cpp.o because tasmota\\tasmota.ino.cpp changed ».

La conversion garde le code de PlatformIO ; seul le nom du fichier temporaire devient fixe, le temps de son appel.
Banc : test_ino_stable.py (qui verifie aussi que pioino.py appelle toujours `tempfile.mkstemp()[1]`).
"""
import os
import tempfile


def enveloppe(convertir, nom_env):
    """`convertir(env)` avec un fichier temporaire de nom fixe pour cet env. PlatformIO ne garde que le chemin : aucun
    descripteur a ouvrir, il ecrit puis efface lui-meme ce fichier."""
    chemin = os.path.join(tempfile.gettempdir(), f"tasmota_ino_{nom_env}")

    def ConvertInoToCpp(env):
        reel = tempfile.mkstemp
        tempfile.mkstemp = lambda *a, **k: (-1, chemin)
        try:
            return convertir(env)
        finally:
            tempfile.mkstemp = reel
    return ConvertInoToCpp
