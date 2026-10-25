"""Sauvegardes horodatees et ecritures atomiques de la page « Fichiers Berry par env » (spec §9).

Chaque ecriture de la page (enregistrement, creation, suppression) passe par une `Transaction` :
  - avant d'ecrire un fichier, sa version d'origine est copiee dans
    <dossier des outils>/fichiers_berry/sauvegardes/<AAAAMMJJ-HHMMSS-micro>-<nature>/<chemin relatif>
    (hors depot ; distincte du .bak de la page build, qui ecrasait le sien) ; gardee 30 jours ;
  - si une etape echoue, tout ce qui a deja ete fait est defait, en ordre inverse (fichiers remis, dossier
    copie retire, renommage defait), puis l'exception repart : jamais de carte a moitie creee ou supprimee.
    Si une annulation echoue elle-meme (fichier tenu ouvert...), AnnulationIncomplete nomme ce qui reste a defaire.
"""

import datetime
import shutil
import time
from pathlib import Path

import acces_web

JOURS = 30


def dossier_sauvegardes():
    return acces_web.dossier_donnees() / "fichiers_berry" / "sauvegardes"


def purge(jours=JOURS):
    """Retire les sauvegardes de plus de `jours` jours ; renvoie leurs noms."""
    racine, retires = dossier_sauvegardes(), []
    if not racine.is_dir():
        return retires
    limite = time.time() - jours * 86400
    for d in racine.iterdir():
        if d.is_dir() and d.stat().st_mtime < limite:
            shutil.rmtree(d, ignore_errors=True)
            retires.append(d.name)
    return retires


class AnnulationIncomplete(Exception):
    """Une etape a echoue ET une partie de l'annulation aussi : le message dit quoi remettre a la main."""


class Transaction:
    """with Transaction(racine, "creation") as tr: tr.ecrit(...), tr.renomme(...), tr.copie_dossier(...)."""

    def __init__(self, racine, nature):
        self.racine, self.nature = Path(racine), nature
        self.dossier = None
        self._annulations = []

    def __enter__(self):
        purge()
        horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.dossier = dossier_sauvegardes() / f"{horodatage}-{self.nature}"
        return self

    def ecrit(self, rel, octets):
        chemin = self.racine / rel
        avant = chemin.read_bytes() if chemin.is_file() else None
        if avant is not None:
            copie = self.dossier / rel
            copie.parent.mkdir(parents=True, exist_ok=True)
            copie.write_bytes(avant)
        self._annulations.append((f"{rel} a remettre",
                                  lambda: chemin.write_bytes(avant) if avant is not None else chemin.unlink(missing_ok=True)))
        chemin.write_bytes(octets)

    def renomme(self, rel_src, rel_dst):
        src, dst = self.racine / rel_src, self.racine / rel_dst
        if dst.exists():
            raise FileExistsError(f"{rel_dst} existe deja")
        parent_cree = not dst.parent.exists()           # renommage vers un nouveau lieu : data/<lieu> a creer
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)

        def annule():
            dst.rename(src)
            if parent_cree and not any(dst.parent.iterdir()):
                dst.parent.rmdir()
        self._annulations.append((f"{rel_dst} a renommer en {rel_src}", annule))

    def copie_dossier(self, rel_src, rel_dst, ignore=None):
        dst = self.racine / rel_dst
        if dst.exists():
            raise FileExistsError(f"{rel_dst} existe deja")
        self._annulations.append((f"{rel_dst} a effacer",                           # copie partielle comprise
                                  lambda: shutil.rmtree(dst) if dst.exists() else None))
        shutil.copytree(self.racine / rel_src, dst, ignore=ignore)

    def __exit__(self, type_, exc, trace):
        if exc is not None:
            echecs = []
            for libelle, annule in reversed(self._annulations):
                try:
                    annule()
                except OSError as erreur:    # on continue : defaire tout ce qui peut l'etre
                    echecs.append(f"{libelle} ({erreur})")
            if echecs:
                raise AnnulationIncomplete(
                    f"{type(exc).__name__} : {exc} ; ANNULATION INCOMPLETE, a remettre a la main : " + " ; ".join(echecs)
                    + f" ; versions d'origine dans {self.dossier}") from exc
        return False
