"""Banc des fonctions de texte de mesure_binomes.py (sans toolchain ni carte). Code de sortie 0 = vert."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesure_binomes as mb

ECHECS = []


def verifie(cond, msg):
    print(("OK    " if cond else "ECHEC ") + msg)
    if not cond:
        ECHECS.append(msg)


SOURCE = "#- NOTES\r\n   texte\r\n-#\r\n#@ solidify:controleX\r\nvar controleX = module(\"controleX\")\r\nreturn controleX\r\n"
MESURES = [("controleX.be", 10800, 3900, 3030, 72), ("xFonctions.be", 51800, 28200, 19576, 290)]
bloc = mb.bloc_driver(MESURES)

une = mb.avec_entete(SOURCE, bloc)
deux = mb.avec_entete(une, bloc)
verifie(une != SOURCE, "le bloc est ajoute")
verifie(deux == une, "idempotence : deux ecritures, aucun diff")
verifie(mb.retire_generes(une) == SOURCE, "le texte mesure est le source sans le bloc")
verifie("\r\n" in une and "\n" not in une.replace("\r\n", ""), "fins de ligne CRLF conservees")
verifie(une.index("#@ solidify:") > une.index(mb.FIN), "bloc avant la directive #@ solidify")

# Mutant : un chiffre change -> l'en-tete attendu differe du fichier ecrit (--verifier rendrait 1)
mutant = mb.bloc_driver([("controleX.be", 10800, 3900, 3031 + 1024, 72), MESURES[1]])
verifie(mb.avec_entete(une, mutant) != une, "mutant d'une mesure : detecte comme perime")

# Sequences interdites : absentes du bloc genere, et le controle les attrape
try:
    mb.controle_interdits(bloc)
    verifie(True, "bloc genere sans -#, #@ ni module(\" hors marqueur de fin")
except ValueError as e:
    verifie(False, f"bloc genere refuse : {e}")
try:
    mb.controle_interdits(bloc.replace("total", 'module("x")'))
    verifie(False, "temoin : module(\" dans le bloc doit etre refuse")
except ValueError:
    verifie(True, "temoin : module(\" dans le bloc est refuse")

# Module : ligne de renvoi, idempotente, retiree avant mesure
renvoi = mb.ligne_renvoi("controleX.be")
m1 = mb.avec_entete("# Definition\nvar x = 1\n", renvoi)
verifie(mb.avec_entete(m1, renvoi) == m1, "ligne de renvoi idempotente")
verifie(mb.retire_generes(m1) == "# Definition\nvar x = 1\n", "ligne de renvoi retiree avant mesure")
verifie(mb.ko(51834) == "50,6 Ko", "Ko avec virgule decimale")
seul = mb.bloc_driver([("ecranSysteme.be", 20000, 9000, None, 0)])
verifie("non solid." in seul and "total" in seul, "module sans directive : « non solid. », total calcule")

print(f"\n{len(ECHECS)} echec(s)")
sys.exit(1 if ECHECS else 0)
