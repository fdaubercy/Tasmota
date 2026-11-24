"""Banc de verifie_manifeste.py : faux cenv et faux modele dans un dossier temporaire, rien n'est ecrit dans le depot.

Cas vert, un cas rouge par type d'ecart, lecture impossible (code 2), puis MUTANTS : chaque controle neutralise doit
rendre le banc rouge (preuve que la comparaison compte). Code de sortie 0 = vert.
Lancer : python outils_docs/scripts_python/outils_pc/test_verifie_manifeste.py
"""
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verifie_manifeste as vm

CENV = """[berry_commun]
socle   =   data/fs/base.be
            data/fs/srv.be
modbus  =   data/fs/mb.be
            data/fs/mb2.be
page_x  =   data/fs/px.be
            data/sd/html/px.html
mixte   =   ${berry_commun.modbus}
            data/fs/autre.be
"""
BLOCS = [
    {"id": "srv", "fichiers": ["data/fs/srv.be"], "pages": [], "solidify": [], "exclude_si_inactif": []},
    {"id": "modbus", "fichiers": ["${berry_commun.modbus}"], "pages": [], "solidify": ["${berry_commun.modbus}"],
     "exclude_si_inactif": []},
    {"id": "pagex", "fichiers": ["data/fs/px.be"], "pages": ["data/sd/html/px.html"], "solidify": [],
     "exclude_si_inactif": []},
    {"id": "autre", "fichiers": ["data/fs/autre.be"], "pages": [], "solidify": [], "exclude_si_inactif": []},
    {"id": "fsx", "fichiers": ["data/fs/srv.be"], "pages": [], "detection": {"socle": True}, "solidify": [],
     "exclude_si_inactif": []},
]
FICHIERS = ["data/fs/base.be", "data/fs/srv.be", "data/fs/mb.be", "data/fs/mb2.be", "data/fs/px.be",
            "data/sd/html/px.html", "data/fs/autre.be"]
ECHECS = []


def verifie(cond, msg):
    print(("OK    " if cond else "ECHEC ") + msg)
    if not cond:
        ECHECS.append(msg)


def depot(racine, blocs=BLOCS, cenv=CENV, fichiers=FICHIERS, modele=True):
    racine = Path(racine)
    (racine / "outils_docs/schemas").mkdir(parents=True, exist_ok=True)
    if modele:
        (racine / vm.MODELE).write_text(json.dumps({"blocs": blocs}), encoding="utf-8")
    if cenv is not None:
        (racine / "platformio_tasmota_cenv.ini").write_text(cenv, encoding="utf-8")
    for f in fichiers:
        (racine / f).parent.mkdir(parents=True, exist_ok=True)
        (racine / f).write_text("x", encoding="utf-8")


def en_essai(blocs=BLOCS, cenv=CENV, fichiers=FICHIERS):
    """Ecarts d'un depot d'essai ; un depot neuf par appel."""
    with tempfile.TemporaryDirectory() as t:
        depot(t, blocs, cenv, fichiers)
        return vm.ecarts(t)


def cas():
    """Les cas attendus ; chaque verifie() cible un type d'ecart. Rejoue sous mutant (voir main)."""
    verifie(en_essai() == [], "cas vert : manifeste et listes concordent (references developpees comprises)")
    nouveau = en_essai(cenv=CENV + "nouvelle = data/fs/zz.be\n", fichiers=FICHIERS + ["data/fs/zz.be"])
    verifie(any("liste [berry_commun].nouvelle inconnue" in e for e in nouveau), "liste inconnue du manifeste")
    sans = [dict(b, fichiers=[]) if b["id"] == "autre" else b for b in BLOCS]
    verifie(any("[berry_commun].mixte : data/fs/autre.be absent du bloc correspondant (modbus)" in e
                for e in en_essai(blocs=sans)),
            "liste a references : le fichier propre qui n'est dans aucun bloc est signale, bloc correspondant nomme")
    manque = en_essai(blocs=[dict(b, pages=[]) if b["id"] == "pagex" else b for b in BLOCS])
    verifie(any("px.html absent du bloc correspondant (pagex)" in e for e in manque),
            "fichier de liste absent du bloc : nomme le fichier et le bloc correspondant")
    verifie(any("px.html" in e for e in manque) and not any("px.be" in e for e in manque),
            "fichier de liste absent du bloc : seul le fichier manquant est signale")
    disque = en_essai(fichiers=[f for f in FICHIERS if f != "data/fs/px.be"])
    verifie(any("bloc pagex : data/fs/px.be absent du disque" in e for e in disque), "fichier de bloc absent du disque")
    verifie(any("[berry_commun].page_x : data/fs/px.be absent du disque" in e for e in disque),
            "fichier de liste absent du disque")
    socle = en_essai(blocs=[dict(b, fichiers=["data/fs/mb.be"]) if b["id"] == "fsx" else b for b in BLOCS])
    verifie(any("bloc fsx : data/fs/mb.be absent de [berry_commun].socle" in e for e in socle),
            "bloc detection socle : fichier absent de la liste socle")
    ref = en_essai(blocs=[dict(b, fichiers=["${berry_commun.fantome}"]) if b["id"] == "autre" else b for b in BLOCS])
    verifie(any("reference ${berry_commun.fantome} vers une liste inconnue" in e for e in ref),
            "reference d'un bloc vers une liste inconnue")
    ref2 = en_essai(blocs=[dict(b, solidify=["${berry_commun.fantome}"]) if b["id"] == "srv" else b for b in BLOCS])
    verifie(any("solidify : reference ${berry_commun.fantome}" in e for e in ref2), "reference inconnue dans solidify")


def cli():
    def lance(argv, racine):
        sortie, erreur = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreur):
            rc = vm.main(argv, racine)
        return rc, sortie.getvalue(), erreur.getvalue()
    with tempfile.TemporaryDirectory() as t:
        depot(t)
        rc, out, _ = lance(["--verifier"], t)
        verifie(rc == 0 and "ACCORD" in out, "main --verifier : code 0 sur un accord")
        (Path(t) / "data/fs/px.be").unlink()
        rc, out, _ = lance(["--verifier"], t)
        verifie(rc == 1 and "ECART" in out, "main --verifier : code 1 sur un ecart, sortie lisible")
        verifie(lance([], t)[0] == 2 and lance(["--ecrire"], t)[0] == 2, "main sans --verifier : code 2 (rien d'ecrit)")
        avant = {p: p.read_bytes() for p in Path(t).rglob("*") if p.is_file()}
        lance(["--verifier"], t)
        verifie(avant == {p: p.read_bytes() for p in Path(t).rglob("*") if p.is_file()}, "main : aucun fichier modifie")
    with tempfile.TemporaryDirectory() as t:
        depot(t, modele=False)
        verifie(lance(["--verifier"], t)[0] == 2, "main : modele absent -> code 2")
    with tempfile.TemporaryDirectory() as t:
        depot(t, cenv="[env:x]\nbuild_flags = -DX\n")
        verifie(lance(["--verifier"], t)[0] == 2, "main : [berry_commun] absente -> code 2")
    with tempfile.TemporaryDirectory() as t:
        depot(t, cenv="[berry_commun]\na = ${berry_commun.b}\nb = ${berry_commun.a}\n")
        verifie(lance(["--verifier"], t)[0] == 2, "main : reference circulaire -> code 2")
    with tempfile.TemporaryDirectory() as t:
        depot(t, blocs=[])
        (Path(t) / vm.MODELE).write_text("{pas du json", encoding="utf-8")
        verifie(lance(["--verifier"], t)[0] == 2, "main : modele illisible -> code 2")


def mutants():
    """Chaque controle neutralise doit faire echouer au moins un cas : sinon il n'est pas teste."""
    global ECHECS
    for nom, remplace in (("_listes_inconnues_ou_incompletes", lambda *a: []), ("_socle", lambda *a: []),
                          ("_disque", lambda *a: [])):
        original, ECHECS_avant = getattr(vm, nom), ECHECS
        ECHECS = []
        sortie = io.StringIO()
        setattr(vm, nom, remplace)
        try:
            with contextlib.redirect_stdout(sortie):
                cas()
            rouge = bool(ECHECS)
        finally:
            setattr(vm, nom, original)
            ECHECS = ECHECS_avant
        verifie(rouge, f"mutant : {nom} neutralise -> le banc devient rouge")
    original, ECHECS_avant, ECHECS = vm.fichiers_blocs, ECHECS, []
    vm.fichiers_blocs = lambda blocs, listes: ({b["id"]: [] for b in blocs}, [])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cas()
        rouge = bool(ECHECS)
    finally:
        vm.fichiers_blocs, ECHECS = original, ECHECS_avant
    verifie(rouge, "mutant : fichiers_blocs vide (le manifeste ne compte plus) -> le banc devient rouge")


cas()
cli()
mutants()
print(f"\n{len(ECHECS)} echec(s)")
sys.exit(1 if ECHECS else 0)
