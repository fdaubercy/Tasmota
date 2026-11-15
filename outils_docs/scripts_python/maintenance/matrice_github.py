"""Matrice GitHub de la compilation de nuit : envs du cenv moins les envs decoches dans la page « Taches planifiees ».

UTILISATION
    python outils_docs/scripts_python/maintenance/matrice_github.py        (lu par le job `choix` de .github/workflows/build_custom.yml)
    Ecrit sur la sortie standard le JSON de la matrice ; ajoute `matrice=` et `nombre=` a $GITHUB_OUTPUT s'il existe.

Source : `[env:...]` de platformio_tasmota_cenv.ini (tous les envs perso), moins `exclus` de
outils_docs/compilations_nuit/envs_github.json. Un nom exclu qui n'existe plus dans le cenv est ignore ici (la page le signale).
La liste n'est plus ecrite a la main dans le workflow : elle ne peut plus prendre de retard (13 envs manquaient le 2026-11-15).

Banc : test_matrice_github.py.
"""

import json
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
FICHIER_EXCLUS = Path("outils_docs") / "compilations_nuit" / "envs_github.json"


def envs_cenv(racine=RACINE):
    texte = (Path(racine) / "platformio_tasmota_cenv.ini").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^\[env:([^\]]+)\]", texte, re.M)))


def lit_exclus(racine=RACINE):
    """Liste des envs exclus ; fichier absent = aucun. Un fichier illisible leve (mieux vaut echouer que compiler a l'aveugle)."""
    chemin = Path(racine) / FICHIER_EXCLUS
    if not chemin.exists():
        return []
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    exclus = donnees.get("exclus") if isinstance(donnees, dict) else None
    if not isinstance(exclus, list) or not all(isinstance(e, str) for e in exclus):
        raise ValueError(f"{FICHIER_EXCLUS} : {{\"exclus\": [noms d'env]}} attendu")
    return exclus


def matrice(racine=RACINE):
    exclus = set(lit_exclus(racine))
    return [e for e in envs_cenv(racine) if e not in exclus]


def main():
    liste = matrice()
    sortie = json.dumps(liste)
    print(sortie)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"matrice={sortie}\nnombre={len(liste)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
