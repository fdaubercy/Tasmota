"""Banc de build_reparations_verrou (plan build-reparations A2) : qui tient un fichier, classement, fermeture.

UTILISATION (Python de PlatformIO, depuis la racine du depot, Windows seulement)
    python outils_docs/scripts_python/outils_pc/test_build_reparations_verrou.py
Code de sortie 0 = vert. Un processus de test (copie de python.exe renommee fauxcpp.exe) garde un fichier temporaire
ouvert en partage exclusif ; seuls ces processus de test sont fermes. Mutants : garde retiree -> banc rouge.
"""

import glob
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import build_reparations_verrou as bv

ECHECS = []
SILENCE = []
NOM_FAUX = "fauxcpp.exe"
LISTE_TEST = ("FauxCpp.exe",)  # casse differente : la comparaison doit l'ignorer

# Le processus de test : ouvre le fichier en partage 0 (exclusif), annonce son pid, attend d'etre ferme.
GARDIEN = r"""
import ctypes, os, sys, time
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.restype = ctypes.c_void_p
h = k.CreateFileW(sys.argv[1], 0x80000000, 0, None, 3, 0x80, None)
if h in (None, ctypes.c_void_p(-1).value):
    print("ERREUR", ctypes.get_last_error(), flush=True); sys.exit(1)
print(os.getpid(), flush=True)
time.sleep(120)
"""


def verifie(nom, condition):
    if not condition:
        ECHECS.append(nom)
        if not SILENCE:
            print("ECHEC :", nom)


def prepare_faux(dossier):
    """Copie l'interpreteur de base sous le nom fauxcpp.exe (avec ses DLL) ; rend la commande et l'environnement."""
    base = Path(getattr(sys, "_base_executable", sys.executable))
    shutil.copy(base, Path(dossier) / NOM_FAUX)
    for dll in glob.glob(str(base.parent / "*.dll")):
        shutil.copy(dll, dossier)
    env = dict(os.environ, PYTHONHOME=str(base.parent))
    return str(Path(dossier) / NOM_FAUX), env


class Gardien:
    """Lance un processus qui tient `chemin` en exclusif ; pid = celui qui tient vraiment le fichier."""

    def __init__(self, exe, env, chemin):
        self.p = subprocess.Popen([exe, "-c", GARDIEN, chemin], env=env, stdout=subprocess.PIPE, text=True)
        ligne = self.p.stdout.readline().strip()
        self.pid = int(ligne) if ligne.isdigit() else None

    def arrete(self):
        if self.p.poll() is None:
            self.p.kill()
        self.p.wait(10)


def passe_classe():
    moi = os.getpid()
    lb = bv.LISTE_BLANCHE
    verifie("cpptools en liste blanche par defaut", bv.classe({"pid": 11, "nom": "cpptools-srv.exe"}, None, lb) == "ferme")
    verifie("liste blanche sans casse", bv.classe({"pid": 11, "nom": "CPPTOOLS.EXE"}, None, lb) == "ferme")
    verifie("page = jamais", bv.classe({"pid": moi, "nom": "cpptools.exe"}, None, lb) == "jamais")
    verifie("pid de la serie = jamais", bv.classe({"pid": 42, "nom": "cpptools.exe"}, 42, lb) == "jamais")
    verifie("fils de la serie = jamais",
            bv.classe({"pid": 43, "nom": "cpptools.exe", "ancetres": [42, 1]}, 42, lb) == "jamais")
    verifie("claude = jamais", bv.classe({"pid": 12, "nom": "claude.exe"}, None, ("claude.exe",)) == "jamais")
    for nom in ("pio.exe", "platformio.exe", "scons", "python.exe", "pythonw.exe", "Python3.11.exe"):
        verifie("autre build = attend : " + nom, bv.classe({"pid": 13, "nom": nom}, 42, (nom,)) == "attend")
    verifie("python de la serie = jamais", bv.classe({"pid": 42, "nom": "python.exe"}, 42, lb) == "jamais")
    verifie("autre processus = demande", bv.classe({"pid": 14, "nom": "notepad.exe"}, 42, lb) == "demande")
    verifie("nom vide = demande", bv.classe({"pid": 15, "nom": ""}, None, lb) == "demande")


def passe_injecte():
    """libere avec repérage et fermeture simules : tri, processus deja mort tolere."""
    procs = [{"pid": 21, "nom": "cpptools.exe", "ligne": ""}, {"pid": 22, "nom": "pio.exe", "ligne": ""},
             {"pid": 23, "nom": "notepad.exe", "ligne": ""}, {"pid": 42, "nom": "cpptools.exe", "ligne": ""}]
    fermes = []

    def terminer(pid):
        fermes.append(pid)
        raise ProcessLookupError("deja mort")  # mort entre le reperage et la fermeture

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "libre.h"
        f.write_text("x")
        try:
            r = bv.libere(str(f), bv.LISTE_BLANCHE, 42, None, processus_du_fichier=lambda c: procs, terminer=terminer)
        except Exception as e:
            verifie("mort entre reperage et fermeture : pas d'exception (" + type(e).__name__ + ")", False)
            return
        verifie("seul le processus de la liste blanche est ferme", fermes == [21])
        verifie("ferme rapporte", [p["pid"] for p in r["ferme"]] == [21])
        verifie("attend rapporte", [p["pid"] for p in r["attend"]] == [22])
        verifie("demande rapporte", [p["pid"] for p in r["demande"]] == [23])
        verifie("fichier libre", r["libre"] is True)
        # demande acceptee : le processus est ferme aussi
        fermes.clear()
        r = bv.libere(str(f), bv.LISTE_BLANCHE, 42, lambda p: True, processus_du_fichier=lambda c: procs[2:3],
                      terminer=fermes.append)
        verifie("demande acceptee = ferme", fermes == [23] and r["demande"] == [])


def passe_reel(exe, env):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "modules.h"
        f.write_text("verrou")
        verifie("fichier libre au depart", bv.est_libre(str(f)))
        g = Gardien(exe, env, str(f))
        try:
            verifie("gardien demarre", g.pid is not None)
            verifie("fichier tenu detecte", not bv.est_libre(str(f)))
            procs = bv.processus_du_fichier(str(f))
            trouve = [p for p in procs if p["pid"] == g.pid]
            verifie("processus_du_fichier trouve le gardien par son pid", len(trouve) == 1)
            verifie("nom du gardien", trouve and trouve[0]["nom"].lower() == NOM_FAUX)
            verifie("ligne de commande du gardien", trouve and NOM_FAUX in trouve[0]["ligne"].lower())
            # hors liste blanche : demande, rien ferme
            r = bv.libere(str(f), ("cpptools.exe",), None, None)
            verifie("hors liste : demande", [p["pid"] for p in r["demande"]] == [g.pid] and not r["libre"])
            verifie("hors liste : pas ferme", g.p.poll() is None)
            # pid de la serie = le gardien : jamais ferme
            r = bv.libere(str(f), LISTE_TEST, g.pid, None)
            verifie("garde de la serie : pas ferme", g.p.poll() is None and not r["libre"] and r["ferme"] == [])
            # liste blanche de test : ferme et libre
            debut = time.monotonic()
            r = bv.libere(str(f), LISTE_TEST, None, None)
            verifie("liste blanche : ferme", [p["pid"] for p in r["ferme"]] == [g.pid])
            verifie("liste blanche : libre", r == {"libre": True, "ferme": r["ferme"], "attend": [], "demande": []})
            verifie("libere en moins de 6 s", time.monotonic() - debut < 6)
        finally:
            g.arrete()
        verifie("fichier libre : aucun processus", bv.processus_du_fichier(str(f)) == [])
        verifie("fichier absent : libre", bv.est_libre(str(Path(d) / "absent.h")))


def tout(exe, env):
    passe_classe()
    passe_injecte()
    passe_reel(exe, env)


def mutant(nom, ancien, nouveau, exe, env):
    """Recharge le module avec une garde retiree et rejoue le banc : il doit echouer."""
    global bv
    source = Path(bv.__file__).read_text(encoding="utf-8")
    verifie("mutant applicable : " + nom, ancien in source)
    avant = len(ECHECS)
    SILENCE.append(1)
    try:
        ns = {"__name__": "build_reparations_verrou_mutant", "__file__": bv.__file__}
        exec(compile(source.replace(ancien, nouveau, 1), bv.__file__, "exec"), ns)
        m = type(sys)("m")
        m.__dict__.update(ns)
        bv = m
        try:
            tout(exe, env)
        except Exception:
            ECHECS.append("exception")
    finally:
        rouge = len(ECHECS) > avant
        SILENCE.clear()
        del ECHECS[avant:]
        bv = importlib.import_module("build_reparations_verrou")
    verifie("mutant tue : " + nom, rouge)


def main():
    with tempfile.TemporaryDirectory() as d:
        exe, env = prepare_faux(d)
        tout(exe, env)
        if not ECHECS:
            mutant("liste blanche retiree", "if nom in {n.lower() for n in liste_blanche}", "if True", exe, env)
            mutant("garde du pid de la serie retiree", "if pid_serie is not None and", "if False and", exe, env)
    if ECHECS:
        print(len(ECHECS), "echec(s)")
        return 1
    print("test_build_reparations_verrou : tout est vert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
