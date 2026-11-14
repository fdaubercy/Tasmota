"""Banc de menage_lancement (lancement de l'audit, faux `claude`). Code de sortie 0 = vert. Aucun vrai claude, aucun build."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import menage_lancement as ml

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
FAUX = Path(tempfile.mkdtemp()) / "faux_claude.py"
FAUX.write_text('''
import json, os, sys, time
entree = sys.stdin.buffer.read().decode("utf-8")
mode = os.environ.get("FAUX_MODE", "ok")
trace = os.environ.get("FAUX_TRACE")
if trace:
    open(trace, "w", encoding="utf-8").write(json.dumps({"args": sys.argv[1:], "entree": entree}))
rapport = {"resume": "1", "propositions": [{"id": "M1", "categorie": "reste", "chemin": "tasks/README.md", "constat": "c", "preuve": "p",
           "action": "archiver", "casserait": "rien", "risque": "faible", "en_cours": False}]}
if mode == "ok":
    print(json.dumps({"is_error": False, "result": "Voici :\\n" + json.dumps(rapport)}))
elif mode == "invalide":
    rapport["propositions"][0]["chemin"] = "../hors"
    print(json.dumps({"is_error": False, "result": json.dumps(rapport)}))
elif mode == "pasjson":
    print(json.dumps({"is_error": False, "result": "je n'ai pas fini"}))
elif mode == "erreur":
    print(json.dumps({"is_error": True, "result": "limite atteinte"}))
elif mode == "code1":
    sys.stderr.write("boum"); sys.exit(1)
elif mode == "lent":
    time.sleep(60)
''', encoding="utf-8")
PROG = [sys.executable, str(FAUX)]


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")


def attend(audit, delai=30):
    t = time.time()
    while audit.etat()["etat"] == "en_cours" and time.time() - t < delai:
        time.sleep(0.05)
    return audit.etat()


def audit(mode, builds=lambda: [], delai=ml.DELAI, gardes=lambda: []):
    os.environ["FAUX_MODE"] = mode
    return ml.Audit(RACINE, builds, programme=PROG, delai=delai, gardes=gardes)


# 1. parametres : liste blanche
p, e = ml.parametres({})
verifie((e, p["anciennete_jours"], p["modele"]), ([], 3, "sonnet"), "parametres par defaut")
for libelle, brut in [("zone inconnue", {"zone": ["/etc"]}), ("zone vide", {"zone": []}), ("zone pas une liste", {"zone": "data"}),
                      ("categorie inconnue", {"categories": ["tout"]}), ("anciennete negative", {"anciennete_jours": -1}),
                      ("anciennete trop grande", {"anciennete_jours": 9999}), ("anciennete booleenne", {"anciennete_jours": True}),
                      ("anciennete texte", {"anciennete_jours": "3; rm -rf"}), ("modele libre", {"modele": "opus --dangerously-skip-permissions"}),
                      ("effort inconnu", {"effort": "max"})]:
    p, e = ml.parametres(brut)
    verifie((p is None, bool(e)), (True, True), f"parametres refuses : {libelle}")

# 2. succes : rapport valide, options de lecture seule, consigne avec les gardes
trace = Path(tempfile.mkdtemp()) / "trace.json"
os.environ["FAUX_TRACE"] = str(trace)
a = audit("ok", gardes=lambda: ["data/vieux.txt"])
ok, msg = a.lance({"zone": ["tasks"], "anciennete_jours": 5})
verifie(ok, True, "lancement accepte")
e = attend(a)
verifie((e["etat"], e["rapport"] and len(e["rapport"]["propositions"])), ("fini", 1), "audit fini avec 1 proposition")
t = json.loads(trace.read_text(encoding="utf-8"))
args = t["args"]
verifie(("--permission-mode" in args and args[args.index("--permission-mode") + 1] == "dontAsk"), True, "mode dontAsk")
verifie(all(x in args for x in ("--disallowed-tools", "Write", "Edit")), True, "Write et Edit refuses")
verifie("--dangerously-skip-permissions" in args or "bypassPermissions" in args, False, "jamais bypassPermissions")
verifie(args[args.index("--tools") + 1], "Read,Grep,Glob,Bash", "outils limites")
verifie(any(x.startswith("Bash(git status") for x in args) and not any(x == "Bash" for x in args), True, "Bash limite a des commandes de lecture")
verifie(("data/vieux.txt" in t["entree"], "anciennete_jours = 5" in t["entree"], "zone = tasks" in t["entree"]), (True, True, True), "consigne : gardes, anciennete, zone")
del os.environ["FAUX_TRACE"]

# 3. echecs
for mode, attendu in [("invalide", "rapport refuse"), ("pasjson", "rapport refuse"), ("erreur", "claude a rendu une erreur"),
                      ("code1", "claude a echoue")]:
    a = audit(mode)
    a.lance({})
    e = attend(a)
    verifie((e["etat"], attendu in e["message"], e["rapport"]), ("echec", True, None), f"echec propre : {mode}")

# 4. build en cours : refus, rien de lance
appels = []
a = audit("ok", builds=lambda: ["pio run -e tasmota32s3-x"])
ok, msg = a.lance({})
verifie((ok, "build" in msg, a.etat()["etat"]), (False, True, "repos"), "refus pendant un build")

# 5. double lancement et arret
a = audit("lent")
ok1, _ = a.lance({})
time.sleep(1)
ok2, msg2 = a.lance({})
verifie((ok1, ok2, "deja en cours" in msg2), (True, False, True), "refus d'un 2e audit en cours")
a.arrete()
e = attend(a, 20)
verifie((e["etat"], "arrete" in e["message"]), ("echec", True), "arret propre du processus fils")

# 6. delai
a = audit("lent", delai=2)
a.lance({})
e = attend(a, 30)
verifie((e["etat"], "delai" in e["message"]), ("echec", True), "delai depasse : abandon")

# 7. claude introuvable
a = ml.Audit(RACINE, lambda: [], programme=None)
a_shutil = ml.shutil.which
ml.shutil.which = lambda n: None
try:
    a.lance({})
    e = attend(a)
finally:
    ml.shutil.which = a_shutil
verifie((e["etat"], "introuvable" in e["message"]), ("echec", True), "claude introuvable")

# 8. mutants : la garde de build et la liste blanche doivent compter
a = ml.Audit(RACINE, lambda: [], programme=PROG)       # mutant : detection de build neutralisee
os.environ["FAUX_MODE"] = "ok"
ok, _ = a.lance({"modele": "sonnet"})
attend(a)
verifie(ok, True, "mutant sans garde de build : l'audit part (le banc 4 etait donc bien discriminant)")
sauve = ml.parametres
ml.parametres = lambda brut: (dict(brut, zone=brut.get("zone"), categories=[], anciennete_jours=0, modele=brut.get("modele"), effort="medium"), [])
a = audit("ok")
ok, _ = a.lance({"modele": "opus --x", "zone": ["x"]})
attend(a)
ml.parametres = sauve
verifie(ok, True, "mutant sans liste blanche : accepte une valeur hostile (le banc 1 etait donc discriminant)")

if ECHECS:
    print(f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1)
print("VERT : menage_lancement")
