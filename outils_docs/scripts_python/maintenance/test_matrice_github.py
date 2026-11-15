"""Banc de matrice_github.py : faux depot en dossier temporaire.   (code de sortie 0 = vert)"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matrice_github as m
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes  # avancement reel sur la page Sondes en cours
suivi_sondes.suit()

ECHECS = []


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


def depot(exclus=None, brut=None):
    d = Path(tempfile.mkdtemp())
    (d / "platformio_tasmota_cenv.ini").write_text("[env:b]\nx=1\n[env:a]\n[env:c]\n; [env:commente]\n[autre]\n", encoding="utf-8")
    if exclus is not None or brut is not None:
        (d / m.FICHIER_EXCLUS).parent.mkdir(parents=True)
        (d / m.FICHIER_EXCLUS).write_text(brut if brut is not None else json.dumps({"exclus": exclus}), encoding="utf-8")
    return d


verifie("sans fichier : tous les envs, tries, commentaire ignore", m.matrice(depot()) == ["a", "b", "c"])
verifie("exclusion d'un env", m.matrice(depot(["b"])) == ["a", "c"])
verifie("exclu inconnu du cenv : ignore", m.matrice(depot(["zzz"])) == ["a", "b", "c"])
verifie("tout exclu : liste vide", m.matrice(depot(["a", "b", "c"])) == [])
for brut in ("{pas du json", '{"exclus": "a"}', '{"exclus": [1]}', "[]"):
    try:
        m.matrice(depot(brut=brut))
        verifie(f"fichier invalide {brut!r} : leve", False)
    except ValueError:                     # json.JSONDecodeError est un ValueError
        verifie(f"fichier invalide {brut!r} : leve", True)
vrai = m.envs_cenv()
verifie("vrai depot : 25 envs perso ou plus, sans doublon", len(vrai) >= 25 and len(vrai) == len(set(vrai)))
print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
