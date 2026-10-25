"""Sauvegardes horodatees et ecritures atomiques de la page « Fichiers Berry par env » (spec §9).

Chaque ecriture de la page (enregistrement, creation, suppression) passe par une `Transaction` :
  - avant d'ecrire un fichier, sa version d'origine est copiee dans
    <dossier des outils>/fichiers_berry/sauvegardes/<AAAAMMJJ-HHMMSS-micro>-<nature>/<chemin relatif>
    (hors depot ; distincte du .bak de la page build, qui ecrasait le sien) ; gardee 30 jours ;
  - si une etape echoue, tout ce qui a deja ete fait est defait, en ordre inverse (fichiers remis, dossier
    copie retire, renommage defait), puis l'exception repart : jamais de carte a moitie creee ou supprimee.
    Si une annulation echoue elle-meme (fichier tenu ouvert...), AnnulationIncomplete nomme ce qui reste a defaire.
  - chaque fichier est ecrit par remplacement (jamais tronque) ; la marque en_cours.json de la sauvegarde liste les
    etapes et n'est retiree qu'a la fin : un processus arrete en plein vol est signale par interrompues().
"""

import datetime
import json
import os
import shutil
import time
from pathlib import Path

import acces_web

JOURS = 30
MARQUE = "en_cours.json"       # posee a l'entree, retiree a la fin : restee = operation interrompue


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
        self.dossier.mkdir(parents=True, exist_ok=True)
        self._marque = {"nature": self.nature, "debut": datetime.datetime.now().isoformat(timespec="seconds"),
                        "etapes": []}
        _remplace(self.dossier / MARQUE, json.dumps(self._marque, ensure_ascii=False, indent=1).encode("utf-8"))
        return self

    def _etape(self, libelle, annule):
        """Notee dans la marque AVANT d'etre faite : un processus arrete en plein vol laisse la liste de ce qui a pu
        etre fait (spec §9, operation interrompue)."""
        self._marque["etapes"].append(libelle)
        _remplace(self.dossier / MARQUE, json.dumps(self._marque, ensure_ascii=False, indent=1).encode("utf-8"))
        self._annulations.append((libelle, annule))

    def ecrit(self, rel, octets):
        chemin = self.racine / rel
        avant = chemin.read_bytes() if chemin.is_file() else None
        if avant is not None:
            copie = self.dossier / rel
            copie.parent.mkdir(parents=True, exist_ok=True)
            copie.write_bytes(avant)
        self._etape(f"{rel} a remettre", lambda: _remplace(chemin, avant) if avant is not None else chemin.unlink(missing_ok=True))
        _remplace(chemin, octets)

    def renomme(self, rel_src, rel_dst):
        src, dst = self.racine / rel_src, self.racine / rel_dst
        if dst.exists():
            raise FileExistsError(f"{rel_dst} existe deja")
        crees = _crees(dst.parent)                       # renommage vers un nouveau lieu : data/<lieu> a creer
        try:
            src.rename(dst)
        except OSError:
            _retire_vides(crees)
            raise
        vide = not any(src.parent.iterdir())             # dernier dossier du lieu : data/<lieu> part avec lui
        if vide:
            src.parent.rmdir()

        def annule():
            src.parent.mkdir(parents=True, exist_ok=True)
            dst.rename(src)
            _retire_vides(crees)
        self._etape(f"{rel_dst} a renommer en {rel_src}", annule)

    def copie_dossier(self, rel_src, rel_dst, ignore=None):
        dst = self.racine / rel_dst
        if dst.exists():
            raise FileExistsError(f"{rel_dst} existe deja")
        crees = _crees(dst.parent)

        def annule():                                    # copie partielle comprise
            if dst.exists():
                shutil.rmtree(dst)
            _retire_vides(crees)
        self._etape(f"{rel_dst} a effacer", annule)
        shutil.copytree(self.racine / rel_src, dst, ignore=ignore)

    def __exit__(self, type_, exc, trace):
        echecs = []
        if exc is not None:
            for libelle, annule in reversed(self._annulations):
                try:
                    annule()
                except OSError as erreur:    # on continue : defaire tout ce qui peut l'etre
                    echecs.append(f"{libelle} ({erreur})")
        if echecs:                           # la marque reste : la page le signalera au prochain chargement
            self._marque["annulation_incomplete"] = echecs
            _remplace(self.dossier / MARQUE, json.dumps(self._marque, ensure_ascii=False, indent=1).encode("utf-8"))
            raise AnnulationIncomplete(
                f"{type(exc).__name__} : {exc} ; ANNULATION INCOMPLETE, a remettre a la main : " + " ; ".join(echecs)
                + f" ; versions d'origine dans {self.dossier}") from exc
        (self.dossier / MARQUE).unlink(missing_ok=True)
        return False


def _remplace(chemin, octets):
    """Ecrit par remplacement (fichier temporaire voisin puis os.replace) : jamais de fichier tronque a moitie."""
    tmp = chemin.with_name(chemin.name + ".tmp-fichiers-berry")
    tmp.write_bytes(octets)
    os.replace(tmp, chemin)


def _crees(dossier):
    """Cree `dossier` et ses parents manquants ; renvoie ceux crees, du plus profond au plus haut."""
    manquants = [d for d in [dossier, *dossier.parents] if not d.exists()]
    dossier.mkdir(parents=True, exist_ok=True)
    return manquants


def _retire_vides(dossiers):
    for d in dossiers:
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def interrompues():
    """Operations dont la marque est restee (processus arrete, annulation incomplete) : [{nom, dossier, nature,
    debut, etapes, annulation_incomplete}], de la plus ancienne a la plus recente."""
    racine, res = dossier_sauvegardes(), []
    if not racine.is_dir():
        return res
    for d in sorted(racine.iterdir()):
        try:
            m = json.loads((d / MARQUE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        res.append({"nom": d.name, "dossier": str(d), "nature": m.get("nature", "?"), "debut": m.get("debut", ""),
                    "etapes": m.get("etapes", []), "annulation_incomplete": m.get("annulation_incomplete", [])})
    return res


def acquitte(nom):
    """Retire la marque d'une operation interrompue (les fichiers ont ete verifies) ; la sauvegarde reste. False
    si `nom` n'est pas une sauvegarde marquee (nom hors du dossier des sauvegardes compris)."""
    if not isinstance(nom, str) or not nom or nom in (".", "..") or any(c in nom for c in "/\\:"):
        return False
    marque = dossier_sauvegardes() / nom / MARQUE
    if not marque.is_file():
        return False
    marque.unlink()
    return True
