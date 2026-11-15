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
    open(trace, "w", encoding="utf-8").write(json.dumps({"args": sys.argv[1:], "entree": entree, "cle": sorted(k for k in os.environ if k.startswith("ANTHROPIC_"))}))
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
elif mode == "echec_anglais":
    print(json.dumps({"type": "result", "is_error": True, "result": "Credit balance is too low"}), flush=True)
    sys.stderr.write("warning: workspace has not been trusted"); sys.exit(1)
elif mode == "lent":
    time.sleep(60)
elif mode == "flux":
    def evt(o):
        print(json.dumps(o), flush=True)
    evt({"type": "system", "subtype": "init"})
    evt({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Grep", "input": {"pattern": "ghp_" + "a" * 36, "path": "data"}}]}})
    time.sleep(2)
    evt({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "git status --porcelain"}}]}})
    time.sleep(1)
    evt({"type": "result", "subtype": "success", "is_error": False, "result": json.dumps(rapport)})
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
                      ("effort inconnu", {"effort": "extreme"}), ("budget nul", {"budget": 0}), ("budget enorme", {"budget": 500}),
                      ("budget texte", {"budget": "8; x"})]:
    p, e = ml.parametres(brut)
    verifie((p is None, bool(e)), (True, True), f"parametres refuses : {libelle}")

verifie(ml.parametres({"budget": 5})[0]["budget"], 5, "budget choisi conserve")
verifie(ml.parametres({})[0]["budget"], ml.BUDGET_DEFAUT, "budget par defaut")

# 2. succes : rapport valide, options de lecture seule, consigne avec les gardes
trace = Path(tempfile.mkdtemp()) / "trace.json"
os.environ["FAUX_TRACE"] = str(trace)
os.environ["ANTHROPIC_API_KEY"] = "valeur-factice-de-test"       # la page ne doit jamais la transmettre a claude
os.environ["ANTHROPIC_AUTH_TOKEN"] = "valeur-factice-de-test"
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
verifie(t["cle"], [], "l'audit n'herite d'aucune ANTHROPIC_* de l'environnement : abonnement claude.ai, pas la cle API")
os.environ.pop("ANTHROPIC_API_KEY"); os.environ.pop("ANTHROPIC_AUTH_TOKEN")
del os.environ["FAUX_TRACE"]

# 3. echecs
for mode, attendu in [("invalide", "rapport refuse"), ("pasjson", "rapport refuse"), ("erreur", "claude s'est arrêté avec une erreur"),
                      ("code1", "claude s'est arrêté avec une erreur (code 1)")]:
    a = audit(mode)
    a.lance({})
    e = attend(a)
    verifie((e["etat"], attendu in e["message"], e["rapport"]), ("echec", True, None), f"echec propre : {mode}")

# 3b. echecs de claude expliques en francais, avec la raison (le texte anglais brut va dans `detail`)
CAPTURE = ('Ignoring 22 permissions.allow entries from .claude/settings.json: this workspace has not been trusted. Run Claude Code interactively here once '
           'and accept the trust dialog, or set projects["C:/Users/exemple/Documents/Depot"].hasTrustDialogAccepted: true in C:\\Users\\fdaub\\.claude.json.\n'
           '⚠ claude.ai connectors are disabled because ANTHROPIC_API_KEY or another auth source is set and takes precedence over your claude.ai login · Unset it to load your organization\'s connectors')
for libelle, code, err, res, attendus in [
        ("capture de l'utilisateur", 1, CAPTURE, "", ["clé API", "ANTHROPIC_API_KEY", "dossier"]),
        ("credit epuise", 1, "", "Credit balance is too low", ["crédit", "épuisé"]),
        ("cle refusee", 1, "", "Invalid API key · Please run /login", ["refus", "connexion"]),
        ("limite d'utilisation", 1, "", "5-hour limit reached ∙ resets 3pm", ["Limite d'utilisation"]),
        ("serveur surcharge", 1, "", "API Error: 529 overloaded_error", ["surchargé"]),
        ("cause inconnue", 7, "boum", "", ["code 7"])]:
    m, d = ml.explique_echec(code, err, res)
    verifie(all(x in m for x in attendus), True, f"echec explique en francais : {libelle}")
    verifie(("not been trusted" in m or "Credit balance" in m or "Invalid API" in m), False, f"echec explique : pas d'anglais brut dans le message ({libelle})")
    verifie(isinstance(d, str) and len(d) <= 1200, True, f"echec explique : detail technique borne ({libelle})")
m, d = ml.explique_echec(1, CAPTURE, "")
verifie(("hasTrustDialogAccepted" in d, "ANTHROPIC_API_KEY" in d), (True, True), "le detail technique garde le texte d'origine")
m, d = ml.explique_echec(1, "", "Credit balance is too low" + " x" * 800)
verifie(len(d) <= 1200, True, "detail tronque")
a = audit("echec_anglais")
a.lance({})
e = attend(a)
verifie((e["etat"], "crédit" in e["message"], "Credit balance" in e.get("detail", "")), ("echec", True, True), "echec de bout en bout : message en francais, detail anglais conserve")

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

# 7b. flux : activite et progression visibles PENDANT l'audit, secrets masques
a = audit("flux")
a.lance({})
t0 = time.time()
while time.time() - t0 < 15 and not a.etat().get("activite"):
    time.sleep(0.1)
e = a.etat()
verifie((e["etat"], [x["outil"] for x in e["activite"]], e["appels"]), ("en_cours", ["Grep"], 1), "flux : l'action en cours est visible avant la fin")
verifie(0 < e["progression"] < 100, True, "flux : progression approximative entre 0 et 100 pendant l'audit")
verifie("ghp_" + "a" * 36 in json.dumps(e["activite"]), False, "flux : un secret dans une action est masque")
e = attend(a)
verifie((e["etat"], [x["outil"] for x in e["activite"]], e["progression"], e["rapport"] and len(e["rapport"]["propositions"])),
        ("fini", ["Grep", "Bash"], 100, 1), "flux : fini, 2 actions, progression 100, rapport lu dans l'evenement result")

# 7c. contre-verification : le rapport fini porte `verif` ; si elle plante, l'audit n'est pas perdu
a = audit("ok")
a.lance({})
e = attend(a)
verifie(("verif" in e["rapport"]["propositions"][0], e["rapport"]["propositions"][0]["verif"].get("disponible")), (True, True), "rapport enrichi de la contre-verification")
vrai = ml.menage_verification.enrichit
ml.menage_verification.enrichit = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("git en panne"))
try:
    a = audit("ok")
    a.lance({})
    e = attend(a)
finally:
    ml.menage_verification.enrichit = vrai
verifie((e["etat"], e["rapport"]["propositions"][0]["verif"]["disponible"], "RuntimeError" in e["rapport"]["propositions"][0]["verif"]["erreur"]),
        ("fini", False, True), "contre-verification en panne : l'audit reste valide, la page dira « indisponible »")

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
