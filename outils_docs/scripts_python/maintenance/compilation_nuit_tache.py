"""Tache planifiee Windows de la compilation de nuit : creer, lire, activer, desactiver, supprimer (schtasks).

UTILISATION
    python outils_docs/scripts_python/maintenance/compilation_nuit_tache.py etat|creer [HH:MM]|active|desactive|supprime
    La tache `Tasmota-CompilationNuit` lance compilation_nuit.py chaque jour. Elle est creee DESACTIVEE : l'activer
    est un geste explicite (tuile « Taches planifiees », ou `active`). Sans droits administrateur (session ouverte
    seulement), sans reveil du PC et sans rattrapage si le PC est eteint a l'heure prevue.

Banc : test_compilation_nuit_tache.py (faux schtasks, aucune tache reelle creee).
"""

import csv
import io
import re
import subprocess
import sys
from pathlib import Path

NOM = "Tasmota-CompilationNuit"
SCRIPT = Path(__file__).resolve().with_name("compilation_nuit.py")
HEURE = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def schtasks(*args):
    """Seul point d'appel a schtasks (remplace par un faux dans le banc). Rend (code, sortie)."""
    r = subprocess.run(["schtasks", *args], capture_output=True, text=True, encoding="cp850", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def etat(executeur=schtasks):
    """{existe, actif, prochaine, derniere, dernier_code, heure} ; existe False si la tache est absente."""
    code, sortie = executeur("/query", "/tn", NOM, "/fo", "csv", "/v")
    lignes = list(csv.reader(io.StringIO(sortie)))
    if code != 0 or len(lignes) < 2:
        return {"existe": False, "actif": False}
    champs = dict(zip(lignes[0], lignes[1]))

    def cle(*mots):                                         # les en-tetes dependent de la langue de Windows
        return next((v for k, v in champs.items() if any(m in k.lower() for m in mots)), "")
    statut = cle("statut de la t", "scheduled task state", "état planifié", "etat planifie")
    return {"existe": True, "statut_inconnu": not statut.strip(),   # en-tetes d'une langue non prevue : on ne devine pas « active »
            "actif": bool(statut.strip()) and "désactiv" not in statut.lower() and "disabled" not in statut.lower(),
            "prochaine": cle("prochaine", "next run"), "derniere": cle("dernière exécution", "derniere execution", "last run time"),
            "dernier_code": cle("résultat", "resultat", "last result"), "heure": cle("heure de début", "start time", "heure de debut")}


def creer(heure="02:00", executeur=schtasks, python=sys.executable):
    """Cree la tache quotidienne puis la desactive. Une tache existante est remplacee (/f)."""
    if not HEURE.fullmatch(heure):
        raise ValueError(f"heure invalide {heure!r} (HH:MM attendu)")
    commande = f'"{python}" "{SCRIPT}"'
    code, sortie = executeur("/create", "/tn", NOM, "/tr", commande, "/sc", "daily", "/st", heure, "/f")
    if code != 0:
        raise RuntimeError(f"creation refusee : {sortie.strip()}")
    return active(False, executeur)


def active(oui, executeur=schtasks):
    code, sortie = executeur("/change", "/tn", NOM, "/enable" if oui else "/disable")
    if code != 0:
        raise RuntimeError(f"changement refuse : {sortie.strip()}")
    return etat(executeur)


def change_heure(heure, executeur=schtasks):
    """Change l'heure de la tache existante SANS toucher a son etat (active ou non)."""
    if not HEURE.fullmatch(heure):
        raise ValueError(f"heure invalide {heure!r} (HH:MM attendu)")
    code, sortie = executeur("/change", "/tn", NOM, "/st", heure)
    if code != 0:
        raise RuntimeError(f"changement d'heure refuse : {sortie.strip()}")
    return etat(executeur)


def supprime(executeur=schtasks):
    code, sortie = executeur("/delete", "/tn", NOM, "/f")
    if code != 0:
        raise RuntimeError(f"suppression refusee : {sortie.strip()}")


def main(argv):
    ordre = argv[0] if argv else "etat"
    if ordre == "etat":
        resultat = etat()
    elif ordre == "creer":
        resultat = creer(argv[1] if len(argv) > 1 else "02:00")
    elif ordre in ("active", "desactive"):
        resultat = active(ordre == "active")
    elif ordre == "supprime":
        supprime()
        resultat = {"existe": False}
    else:
        print(__doc__)
        return 2
    print(resultat)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
