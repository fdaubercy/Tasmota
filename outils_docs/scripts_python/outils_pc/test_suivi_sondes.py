"""Banc de suivi_sondes.py : de VRAIS processus enfants python impriment des lignes OK / KO / == et le fichier de suivi les reflete.

    ~/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/outils_pc/test_suivi_sondes.py    (code de sortie 0 = vert)
Les enfants ecrivent dans un dossier temporaire (OUTILS_TASMOTA_DOSSIER) ; seul le suivi de CE banc va dans le vrai dossier.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import suivi_sondes  # noqa: E402  (suivi du banc lui-meme : visible sur la page Sondes en cours)
import sondes_scan  # noqa: E402

suivi_sondes.suit()
ECHECS = []

ENFANT = """
import sys, time
sys.path.insert(0, {ici!r})
import suivi_sondes
r = suivi_sondes.suit({nom!r}, total=8)
{corps}
"""
NORMAL = """
print("== passage normal")
print("OK   un")
print("OK   deux")
print("KO   trois")
print("ECHEC quatre")
print("== temoin x")
print("KO   cinq attendu")
print("KO   temoin y non detecte")
print("OK   fin")
print("ROUGE ou VERT : pas une verification")
"""
LONG = """
print("== phase longue", flush=True)
print("KO   c", flush=True)
print("OK   a", flush=True)
print("OK   b", flush=True)
time.sleep(60)
"""


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


def enfant(dossier, corps, nom="enfant", extra_env=None, fichier="essai_enfant.py", attendre=True):
    script = Path(dossier) / fichier
    script.write_text(ENFANT.format(ici=str(ICI), nom=nom, corps=corps), encoding="utf-8")
    env = dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(dossier), PYTHONIOENCODING="utf-8", **(extra_env or {}))
    p = subprocess.Popen([sys.executable, "-u", str(script)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    if not attendre:
        return p
    sortie, erreur = p.communicate(timeout=60)
    return p.returncode, sortie, erreur


def lit_nom(dossier, nom):
    """Fichier de suivi du processus de ce nom (le python du venv PlatformIO est un lanceur : son pid n'est pas celui qui ecrit)."""
    for f in (Path(dossier) / "sondes").glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("nom") == nom:
            return d
    raise OSError("pas de fichier de suivi pour " + nom)


def attend(condition, delai=10):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        try:
            if condition():
                return True
        except (OSError, ValueError):
            pass
        time.sleep(0.1)
    return False


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    t = Path(t)

    # -- enfant qui se termine normalement ------------------------------------------------------
    p = enfant(t, NORMAL)
    code, sortie, erreur = p
    fichiers = list((t / "sondes").glob("*.json"))
    verifie("enfant normal : code 0 et un seul fichier de suivi", code == 0 and len(fichiers) == 1)
    d = json.loads(fichiers[0].read_text(encoding="utf-8"))
    verifie("sortie de l'enfant transmise INCHANGEE", sortie.splitlines()[:3] == ["== passage normal", "OK   un", "OK   deux"] and "ROUGE ou VERT" in sortie)
    verifie("faits = 7 (2 OK, KO, ECHEC, 2 KO en phase temoin, OK : toutes comptees)", d["faits"] == 7)
    verifie("echecs : KO trois, ECHEC quatre, et le verdict « KO temoin » ; le KO attendu d'un temoin n'y est pas",
            d["echecs"] == ["KO   trois", "ECHEC quatre", "KO   temoin y non detecte"])
    verifie("phase = temoin x ; dernier cas = derniere ligne vue", d["phase"] == "temoin x" and d["dernier"].startswith("ROUGE ou VERT"))
    verifie("etat termine par atexit ; total, nom, parent renseignes", d["etat"] == "termine" and d["total"] == 8 and d["nom"] == "enfant" and d["parent"] > 0)
    verifie("pas de fichier .tmp oublie", not list((t / "sondes").glob("*.tmp")))
    rel = sondes_scan.releve([], sondes_scan.lit_fichiers(t / "sondes"))
    verifie("releve : termine, verdict rouge", len(rel) == 1 and rel[0]["etat"] == "termine" and rel[0]["verdict"] == "rouge")

    # -- enfant tue brutalement -----------------------------------------------------------------
    p = enfant(t, LONG, nom="longue", attendre=False)
    ok = attend(lambda: lit_nom(t, "longue")["faits"] == 3)
    verifie("enfant en cours : la derniere ligne n'attend pas la ligne suivante (ecriture differee)", ok)
    d = lit_nom(t, "longue")
    verifie("en cours : phase, echec en direct, etat en_cours", d["etat"] == "en_cours" and d["phase"] == "phase longue" and d["echecs"] == ["KO   c"])
    rel = [s for s in sondes_scan.releve([], sondes_scan.lit_fichiers(t / "sondes")) if s["pid"] == d["pid"]]
    verifie("vivant sans scan de processus : en_cours reel (jointure par fichier)", len(rel) == 1 and rel[0]["etat"] == "en_cours" and rel[0]["verdict"] == "rouge")
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)      # CET enfant (lanceur et vrai python), jamais un autre processus
    p.wait(10)
    verifie("vivant() faux pour le processus tue", attend(lambda: not suivi_sondes.vivant(d["pid"]), 5))
    rel = [s for s in sondes_scan.releve([], sondes_scan.lit_fichiers(t / "sondes")) if s["pid"] == d["pid"]]
    verifie("enfant tue : le fichier reste en_cours mais le releve dit disparue", lit_nom(t, "longue")["etat"] == "en_cours" and rel[0]["etat"] == "disparue")

    # -- echec d'ecriture ignore ----------------------------------------------------------------
    fichier_bloquant = t / "bloque"
    fichier_bloquant.write_text("je suis un fichier, pas un dossier", encoding="utf-8")
    script = t / "bloque_enfant.py"
    script.write_text(ENFANT.format(ici=str(ICI), nom="bloque", corps=NORMAL), encoding="utf-8")
    r = subprocess.run([sys.executable, str(script)], env=dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(fichier_bloquant), PYTHONIOENCODING="utf-8"),
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    verifie("dossier de suivi impossible a creer : l'enfant finit en code 0, sortie intacte, aucune trace d'erreur",
            r.returncode == 0 and "OK   fin" in r.stdout and "Traceback" not in r.stderr)
    s = suivi_sondes.Suivi("x", None, fichier_bloquant / "sous")
    try:
        s.ligne("OK   direct")
        s.ligne("KO   direct")
        s.fin()
        ok = s.etat["faits"] == 2 and s.etat["etat"] == "termine"
    except Exception:
        ok = False
    verifie("Suivi directement sur un chemin impossible : aucune exception, comptage garde", ok)

    # -- SUIVI_SONDES=0, suit_si_script_test, idempotence, purge -------------------------------
    sous = t / "zero"
    sous.mkdir()
    code, _, _ = enfant(sous, NORMAL, extra_env={"SUIVI_SONDES": "0"})
    verifie("SUIVI_SONDES=0 : aucun fichier de suivi", code == 0 and not (sous / "sondes").exists())
    sous = t / "garde"
    sous.mkdir()
    ENFANT_BRUT = "import sys\nsys.path.insert(0, {ici!r})\nimport suivi_sondes\nprint('OK   v')\nprint('R', suivi_sondes.suit_si_script_test() is not None)\n"
    for nom_script, attendu in (("serveur_outil.py", False), ("banc_essai.py", True), ("test_essai.py", True)):
        sc = sous / nom_script
        sc.write_text(ENFANT_BRUT.format(ici=str(ICI)), encoding="utf-8")
        r = subprocess.run([sys.executable, str(sc)], env=dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(sous)), capture_output=True, text=True, timeout=60)
        verifie(f"suit_si_script_test : {nom_script} -> suivi {'actif' if attendu else 'absent'}", r.returncode == 0 and f"R {attendu}" in r.stdout)
    sc = sous / "banc_serveur.py"
    sc.write_text(ENFANT_BRUT.format(ici=str(ICI)), encoding="utf-8")
    r = subprocess.run([sys.executable, str(sc), "--serveur"], env=dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(sous)), capture_output=True, text=True, timeout=60)
    verifie("suit_si_script_test : banc lance avec --serveur (processus fils de sonde) -> pas de suivi", "R False" in r.stdout)
    verifie("suit() deux fois : la 2e ne fait rien (None)", suivi_sondes.suit() is None)
    ancien = sous / "sondes" / "1.json"
    ancien.write_text("{}", encoding="utf-8")
    vieux = time.time() - 3 * 24 * 3600
    os.utime(ancien, (vieux, vieux))
    enfant(sous, "pass")
    verifie("purge au demarrage : fichier de plus de 2 jours supprime", not ancien.exists())

    # -- vivant() ------------------------------------------------------------------------------
    verifie("vivant : ce processus oui, pid 0 et pid absurde non", suivi_sondes.vivant(os.getpid()) and not suivi_sondes.vivant(0) and not suivi_sondes.vivant(2 ** 30))

print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
