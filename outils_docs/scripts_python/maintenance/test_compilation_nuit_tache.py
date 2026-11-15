"""Banc de compilation_nuit_tache.py : faux schtasks, aucune tache reelle.   (code de sortie 0 = vert)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compilation_nuit_tache as t
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes  # avancement reel sur la page Sondes en cours
suivi_sondes.suit()

ECHECS = []


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


class Faux:
    def __init__(self, existe=True, statut="Activé", refus=False):
        self.appels, self.existe, self.statut, self.refus = [], existe, statut, refus

    def __call__(self, *a):
        self.appels.append(a)
        if self.refus:
            return 1, "ERREUR : Accès refusé"
        if a[0] == "/query":
            if not self.existe:
                return 1, "ERREUR : Le fichier spécifié est introuvable"
            return 0, ('"Nom de la tâche","Prochaine exécution","Statut de la tâche planifiée","Heure de début","Dernière exécution","Résultat"\n'
                       f'"\\Tasmota-CompilationNuit","16/11/2026 02:00:00","{self.statut}","02:00:00","15/11/2026 02:00:00","0"\n')
        if a[0] == "/change":
            self.statut = "Activé" if "/enable" in a else "Désactivé"
        return 0, "ok"


f = Faux()
e = t.etat(f)
verifie("etat : existe, actif, heures lues", e["existe"] and e["actif"] and e["prochaine"].endswith("02:00:00") and e["dernier_code"] == "0")
verifie("etat : desactive reconnu", t.etat(Faux(statut="Désactivé"))["actif"] is False)
verifie("etat : absente", t.etat(Faux(existe=False)) == {"existe": False, "actif": False})
verifie("etat : en-tetes d'une langue inconnue -> pas devine « active »", (lambda e: e["existe"] and e["actif"] is False and e["statut_inconnu"] is True)(
    t.etat(lambda *a: (0, '"Foo","Bar"' + chr(10) + '"x","y"' + chr(10)))))
verifie("etat : version anglaise", t.etat(Faux(statut="Disabled"))["actif"] is False)

f = Faux()
e = t.creer("03:30", f, python="C:/py/python.exe")
creation = f.appels[0]
verifie("creer : quotidienne, a l'heure, remplace", creation[0] == "/create" and "daily" in creation and "03:30" in creation and "/f" in creation)
verifie("creer : commande entre guillemets vers compilation_nuit.py", creation[creation.index("/tr") + 1].endswith('compilation_nuit.py"') and creation[creation.index("/tr") + 1].startswith('"C:/py/python.exe"'))
verifie("creer : desactivee juste apres", f.appels[1][0] == "/change" and "/disable" in f.appels[1] and e["actif"] is False)

for mauvaise in ("25:00", "2:00", "02h00", "02:60", ""):
    try:
        t.creer(mauvaise, Faux())
        verifie(f"heure {mauvaise!r} refusee", False)
    except ValueError:
        verifie(f"heure {mauvaise!r} refusee", True)

f = Faux(statut="Désactivé")
verifie("active : /enable puis etat relu", t.active(True, f)["actif"] and "/enable" in f.appels[0])
verifie("desactive : /disable", t.active(False, f)["actif"] is False and "/disable" in f.appels[2])
try:
    t.active(True, Faux(refus=True))
    verifie("refus de schtasks : RuntimeError", False)
except RuntimeError as err:
    verifie("refus de schtasks : RuntimeError", "refuse" in str(err))
print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
