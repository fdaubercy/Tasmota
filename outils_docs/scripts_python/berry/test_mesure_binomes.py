"""Banc des fonctions de texte de mesure_binomes.py (sans toolchain ni carte). Code de sortie 0 = vert."""
import sys
import tempfile
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

# lit_taille : lecture du bloc genere, sans toolchain (driver, module a renvoi, fichier sans bloc, renvoi qui boucle)
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    mesures = [("controleX.be", 10800, 3900, 3030, 72), ("xFonctions.be", 51800, 28200, None, 0)]
    (d / "controleX.be").write_text(mb.avec_entete(SOURCE, mb.bloc_driver(mesures)), encoding="utf-8")
    (d / "xFonctions.be").write_text(mb.avec_entete("var x = 1\n", mb.ligne_renvoi("controleX.be")), encoding="utf-8")
    (d / "libre.be").write_text("var y = 2\n", encoding="utf-8")
    (d / "boucle.be").write_text(mb.ligne_renvoi("boucle.be") + "\n", encoding="utf-8")
    (d / "vide.be").write_text(mb.ligne_renvoi("absent.be") + "\n", encoding="utf-8")
    drv = mb.lit_taille(d / "controleX.be")
    verifie(drv is not None and [f["nom"] for f in drv["fichiers"]] == ["controleX.be", "xFonctions.be"],
            "lit_taille driver : 2 fichiers, sans la ligne total")
    verifie(drv["fichiers"][0] == {"nom": "controleX.be", "be": 10.5, "bec": 3.8, "solidifie": 3.0},
            "lit_taille driver : valeurs en Ko du bloc")
    verifie(drv["fichiers"][1]["solidifie"] is None, "lit_taille driver : « non solid. » -> None")
    verifie((drv["total"], drv["chaines"]) == ({"be": 61.1, "bec": 31.3, "solidifie": 3.0}, 72),
            "lit_taille driver : total et chaines")
    verifie(mb.lit_taille(d / "xFonctions.be") == drv, "lit_taille module a renvoi : suit le driver nomme")
    verifie(mb.lit_taille(d / "libre.be") is None, "lit_taille fichier sans bloc : None")
    verifie(mb.lit_taille(d / "boucle.be") is None, "lit_taille renvoi sur soi-meme : None")
    verifie(mb.lit_taille(d / "vide.be") is None, "lit_taille renvoi vers un fichier absent : None")
    verifie(mb.lit_taille(d / "n_existe_pas.be") is None, "lit_taille fichier absent : None")
    # temoin : une valeur alteree dans le fichier change la valeur lue (la lecture suit bien le texte)
    (d / "controleX.be").write_text((d / "controleX.be").read_text(encoding="utf-8").replace("10,5 Ko", "99,9 Ko"),
                                    encoding="utf-8")
    verifie(mb.lit_taille(d / "controleX.be")["fichiers"][0]["be"] == 99.9, "lit_taille temoin : la valeur lue suit le fichier")

print(f"\n{len(ECHECS)} echec(s)")
sys.exit(1 if ECHECS else 0)
