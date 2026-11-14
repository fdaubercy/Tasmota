"""Banc de menage_memoire (liste « a garder »), avec mutants. Code de sortie 0 = vert. Copies temporaires, jamais le vrai depot."""

import json
import os
import sys
import tempfile
from pathlib import Path

import menage_memoire as mm

ECHECS = []


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")


tmp = Path(tempfile.mkdtemp())
racine = tmp / "depot"
(racine / "tasks").mkdir(parents=True)
(racine / "tasks" / "a.md").write_text("a", encoding="utf-8")
(racine / "tasks" / "b.md").write_text("b", encoding="utf-8")
donnees = tmp / "donnees"


def neuf():
    return mm.Memoire(donnees, racine)


m = neuf()
verifie(m.charge(), [], "liste vide au depart")
verifie(m.ajoute("tasks/a.md"), (True, "ajoute"), "ajout")
verifie(m.ajoute("tasks/a.md"), (True, "deja dans la liste"), "ajout en double")
verifie(m.ajoute("tasks\\b.md"), (True, "ajoute"), "ajout avec anti-slash")
verifie(neuf().charge(), ["tasks/a.md", "tasks/b.md"], "relu par une nouvelle instance")
verifie(m.ajoute("../hors.txt")[0], False, "chemin avec .. refuse")
verifie(m.ajoute("/etc/passwd")[0], False, "chemin absolu refuse")
verifie(m.ajoute("tasks/inexistant.md")[0], False, "chemin inexistant refuse")
verifie(m.retire("tasks/a.md"), (True, "retire"), "retrait")
verifie(m.retire("tasks/a.md")[0], False, "retrait d'un absent")
verifie(neuf().charge(), ["tasks/b.md"], "apres retrait")

# sauvegarde horodatee de l'ancien contenu
verifie(len(list(donnees.glob("garde-*.json"))) >= 1, True, "copie horodatee de l'ancien fichier")

# un chemin disparu du depot est retire a la lecture, et le fichier reecrit
(racine / "tasks" / "b.md").unlink()
verifie(neuf().charge(), [], "chemin disparu retire")
verifie(json.loads((donnees / "garde.json").read_text(encoding="utf-8"))["gardes"], [], "fichier reecrit sans le disparu")

# fichier corrompu : mis de cote, liste vide, pas d'exception
(donnees / "garde.json").write_text("{pas du json", encoding="utf-8")
verifie(neuf().charge(), [], "fichier corrompu : liste vide")
verifie(len(list(donnees.glob("garde.json.corrompu-*"))), 1, "fichier corrompu mis de cote")
(donnees / "garde.json").write_text(json.dumps({"gardes": [1, 2]}), encoding="utf-8")
verifie(neuf().charge(), [], "forme inattendue : liste vide")

# ecriture interrompue : l'ancien contenu reste intact, aucun .tmp ne traine
m = neuf()
(racine / "tasks" / "b.md").write_text("b", encoding="utf-8")
m.ajoute("tasks/b.md")
avant = (donnees / "garde.json").read_text(encoding="utf-8")
vrai = mm.os.replace
mm.os.replace = lambda *a, **k: (_ for _ in ()).throw(OSError("disque plein simule"))
try:
    try:
        m.ajoute("tasks/a.md")
        leve = False
    except OSError:
        leve = True
finally:
    mm.os.replace = vrai
verifie(leve, True, "ecriture interrompue : l'erreur remonte")
verifie((donnees / "garde.json").read_text(encoding="utf-8"), avant, "ecriture interrompue : ancien contenu intact")
verifie(list(donnees.glob("*.tmp")), [], "ecriture interrompue : aucun .tmp ne traine")

# liste pleine
m = neuf()
vieux = mm.MAX_CHEMINS
mm.MAX_CHEMINS = 1
verifie(m.ajoute("tasks/a.md")[0], False, "liste pleine refusee")
mm.MAX_CHEMINS = vieux

# mutant : un fichier EXISTANT hors du depot n'est refuse que par le controle de chemin
(tmp / "hors.txt").write_text("x", encoding="utf-8")
verifie(neuf().ajoute("../hors.txt")[0], False, "fichier hors depot refuse")
sauve = mm.menage_rapport.chemin_sur
mm.menage_rapport.chemin_sur = lambda c, r: c
ok, _ = neuf().ajoute("../hors.txt")
mm.menage_rapport.chemin_sur = sauve
verifie(ok, True, "mutant sans controle de chemin : le fichier hors depot entre (le banc le voit)")
verifie(neuf().ajoute("../hors.txt")[0], False, "apres mutant : controle restaure")

if ECHECS:
    print(f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1)
print("VERT : menage_memoire")
