"""Memoire « a garder » de la page Menage du depot : chemins que l'utilisateur a decide de ne plus se faire proposer.

Fichier `garde.json` dans le dossier de donnees de l'outil (HORS depot, %LOCALAPPDATA%\\outils_tasmota\\menage\\), jamais dans git.
Ecriture atomique (fichier temporaire puis remplacement) avec copie horodatee de l'ancien contenu ; un fichier illisible est mis de
cote (`garde.json.corrompu-<date>`) et la liste repart vide : une perte de memoire coute une proposition en trop, jamais un blocage.

    Memoire(dossier, racine).charge() -> [chemins]    les chemins disparus du depot sont retires (et le fichier reecrit)
    .ajoute(chemin) -> (ok, message)    .retire(chemin) -> (ok, message)
"""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import menage_rapport

MAX_CHEMINS = 2000
MAX_SAUVEGARDES = 20


class Memoire:
    def __init__(self, dossier, racine):
        self.dossier, self.racine = Path(dossier), Path(racine)
        self.fichier = self.dossier / "garde.json"

    def _lit(self):
        if not self.fichier.is_file():
            return []
        try:
            d = json.loads(self.fichier.read_text(encoding="utf-8"))
            liste = d["gardes"]
            if not isinstance(liste, list) or not all(isinstance(c, str) for c in liste):
                raise ValueError("forme inattendue")
            return liste
        except (OSError, ValueError, KeyError, TypeError):
            try:
                self.fichier.replace(self.dossier / f"garde.json.corrompu-{time.strftime('%Y%m%d-%H%M%S')}")
            except OSError:
                pass
            return []

    def _ecrit(self, liste):
        self.dossier.mkdir(parents=True, exist_ok=True)
        if self.fichier.is_file():
            copie = self.dossier / f"garde-{time.strftime('%Y%m%d-%H%M%S')}.json"
            shutil.copy2(self.fichier, copie)
            for vieille in sorted(self.dossier.glob("garde-*.json"))[:-MAX_SAUVEGARDES]:
                vieille.unlink(missing_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.dossier, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"gardes": sorted(set(liste))}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.fichier)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def charge(self):
        liste = self._lit()
        vivants = [c for c in liste if (self.racine / c).exists()]
        if len(vivants) != len(liste):
            self._ecrit(vivants)
        return sorted(set(vivants))

    def ajoute(self, chemin):
        propre = menage_rapport.chemin_sur(chemin, self.racine)
        if propre is None:
            return False, "chemin refuse"
        if not (self.racine / propre).exists():
            return False, "ce chemin n'existe pas dans le depot"
        liste = self._lit()
        if propre in liste:
            return True, "deja dans la liste"
        if len(liste) >= MAX_CHEMINS:
            return False, f"liste pleine ({MAX_CHEMINS})"
        self._ecrit(liste + [propre])
        return True, "ajoute"

    def retire(self, chemin):
        liste = self._lit()
        if chemin not in liste:
            return False, "pas dans la liste"
        self._ecrit([c for c in liste if c != chemin])
        return True, "retire"
