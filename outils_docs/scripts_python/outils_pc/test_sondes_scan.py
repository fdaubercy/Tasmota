"""Banc de sondes_scan.py : jointure processus / fichiers de suivi, avec un FAUX PowerShell et un faux « vivant » (aucun vrai processus n'est lu ni touche).

    ~/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/outils_pc/test_sondes_scan.py    (code de sortie 0 = vert)
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import suivi_sondes  # noqa: E402
import sondes_scan as sc  # noqa: E402

suivi_sondes.suit()
ECHECS = []
MAINT = 1_000_000.0


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


def proc(pid, parent, nom, ligne, debut=MAINT - 120):
    return {"pid": pid, "parent": parent, "nom": nom, "ligne": ligne, "debut": debut}


def fichier(pid, nom="banc", etat="en_cours", faits=3, echecs=(), maj=MAINT - 5, debut=MAINT - 100, **plus):
    return {"pid": pid, "parent": 1, "nom": nom, "script": nom + ".py", "debut": debut, "maj": maj, "total": None, "faits": faits, "echecs": list(echecs),
            "phase": "p", "dernier": "d", "etat": etat, **plus}


CHROME = 'C:\\chrome.exe --headless=new --user-data-dir=C:\\Temp\\sonde_page_ab12 --remote-debugging-port=9222 about:blank'
PROCS = [
    proc(10, 5, "chrome.exe", CHROME),
    proc(11, 10, "chrome.exe", CHROME + " --type=renderer"),                                          # sous-processus : ignore
    proc(12, 5, "chrome.exe", "C:\\chrome.exe --profil-normal-de-l-utilisateur"),                    # pas une sonde : ignore
    proc(20, 6, "python.exe", "python.exe -u C:\\x\\test_alpha.py --reel"),
    proc(21, 6, "python.exe", "python.exe C:\\x\\banc_beta.py"),
    proc(22, 20, "python.exe", "C:\\Python\\python.exe C:\\x\\test_alpha.py --reel"),                # fils du lanceur venv de 20 : seul le fils reste
    proc(30, 6, "python.exe", "python.exe C:\\x\\sondes_web.py --http 7910"),                         # le serveur n'est pas une sonde
    proc(31, 6, "powershell.exe", "powershell -Command ... sonde_ test_ banc_"),                       # PowerShell du releve lui-meme : ignore
    proc(32, 6, "node.exe", "node test_x.mjs"),
]

# -- processus() ---------------------------------------------------------------------------------
procs = sc.processus(lambda: PROCS)
verifie("processus : Chrome de sonde racine + 2 bancs python (le lanceur venv est ecarte)", sorted((p["pid"], p["nature"]) for p in procs) ==
        [(10, "chrome"), (21, "banc"), (22, "banc")])
verifie("processus : noms (script sans .py, dossier sonde_ du Chrome)", {p["pid"]: p["nom"] for p in procs} == {10: "Chrome sonde_page_ab12", 21: "banc_beta", 22: "test_alpha"})
verifie("processus : un seul objet JSON (PowerShell avec un seul resultat) accepte",
        len(sc.processus(lambda: [PROCS[3]])) == 1)
try:
    sc.processus(lambda: [{"pid": "x"}, None, {"nom": "python.exe"}])
    ok = True
except Exception:
    ok = False
verifie("processus : entrees mal formees ignorees sans exception", ok)

# -- releve() : jointure ---------------------------------------------------------------------------
vivants = {5, 6, 10, 21, 22, 40}
vivant = lambda pid: pid in vivants
fich = [fichier(22, "test_alpha", faits=12, echecs=["KO   x"]),
        fichier(40, "inconnu_vivant"),                                                                 # vivant mais ignore du scan
        fichier(50, "mort", etat="en_cours"),                                                          # mort sans avoir fini
        fichier(60, "fini_vert", etat="termine", maj=MAINT - 30),
        fichier(61, "fini_rouge", etat="termine", echecs=["KO   z"], maj=MAINT - 20),
        fichier(62, "vieux", etat="termine", maj=MAINT - 7200),                                        # plus d'une heure : garde pas
        fichier(63, "vieux_mort", etat="en_cours", maj=MAINT - 7200)]
r = {s["pid"]: s for s in sc.releve(procs, fich, vivant, MAINT)}
verifie("en cours avec fichier : avancement reel (faits, echecs), verdict rouge si echec", r[22]["etat"] == "en_cours" and r[22]["faits"] == 12 and r[22]["verdict"] == "rouge"
        and r[22]["echecs"] == ["KO   x"] and r[22]["phase"] == "p" and r[22]["dernier"] == "d")
verifie("vivant sans fichier : sans_suivi, duree seulement", r[21]["etat"] == "sans_suivi" and r[21]["faits"] == 0 and r[21]["verdict"] is None and r[21]["duree_s"] == 120)
verifie("Chrome de sonde dont le parent est vivant : sans_suivi", r[10]["etat"] == "sans_suivi" and r[10]["nature"] == "chrome")
r2 = {s["pid"]: s for s in sc.releve(procs, fich, lambda pid: pid in {10, 21, 22}, MAINT)}
verifie("Chrome de sonde dont le parent est mort : orpheline", r2[10]["etat"] == "orpheline" and r2[10]["parent"] == 5)
verifie("fichier vivant que le scan ne connait pas : en_cours quand meme", r[40]["etat"] == "en_cours")
verifie("fichier en_cours dont le pid est mort : disparue, verdict rouge", r[50]["etat"] == "disparue" and r[50]["verdict"] == "rouge")
verifie("termine : verdict vert / rouge selon les echecs", r[60]["etat"] == "termine" and r[60]["verdict"] == "vert" and r[61]["verdict"] == "rouge")
verifie("plus d'une heure : ni termine ni disparue", 62 not in r and 63 not in r)
verifie("ordre : en_cours d'abord, termines a la fin", [s["etat"] for s in sc.releve(procs, fich, vivant, MAINT)][0] in ("en_cours",) and
        sc.releve(procs, fich, vivant, MAINT)[-1]["etat"] == "termine")
nombreux = [fichier(100 + i, f"t{i}", etat="termine", maj=MAINT - i) for i in range(15)]
verifie("termines : 10 au plus", sum(1 for s in sc.releve([], nombreux, vivant, MAINT) if s["etat"] == "termine") == 10)
hostile = fichier(70, "<img src=x onerror=alert(1)>" * 20, etat="termine", echecs=["KO " + "<b>" * 500] * 40, dernier="y" * 5000)
h = sc.releve([], [hostile], vivant, MAINT)[0]
verifie("textes bornes (nom 120, libelle 300, 20 echecs) et conserves tels quels", len(h["nom"]) == 120 and len(h["echecs"]) == 20 and len(h["echecs"][0]) == 300 and len(h["dernier"]) == 300
        and h["nom"].startswith("<img"))

# -- lit_fichiers() --------------------------------------------------------------------------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    t = Path(t)
    (t / "1.json").write_text(json.dumps(fichier(1)), encoding="utf-8")
    (t / "2.json").write_text("{pas du json", encoding="utf-8")
    (t / "3.json").write_text(json.dumps({"pid": "x"}), encoding="utf-8")
    (t / "4.json").write_text("[1]", encoding="utf-8")
    (t / "5.json.tmp").write_text("{}", encoding="utf-8")
    verifie("lit_fichiers : seuls les fichiers valides, sans exception", [f["pid"] for f in sc.lit_fichiers(t)] == [1])
    verifie("lit_fichiers : dossier absent -> liste vide", sc.lit_fichiers(t / "absent") == [])

# -- lance_ps() : jamais de vrai PowerShell ici ; erreur propagee --------------------------------------
class Faux:
    returncode, stdout, stderr = 1, "", "boom"
vrai = sc.subprocess.run
sc.subprocess.run = lambda *a, **k: Faux()
try:
    sc.lance_ps()
    ok = False
except OSError as e:
    ok = "boom" in str(e)
finally:
    sc.subprocess.run = vrai
verifie("lance_ps : code non nul -> OSError avec le message (la page l'affiche, ne plante pas)", ok)

print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
