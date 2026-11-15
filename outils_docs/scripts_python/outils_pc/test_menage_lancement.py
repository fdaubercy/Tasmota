"""Banc de menage_lancement (lancement de l'audit, faux `claude`). Code de sortie 0 = vert. Aucun vrai claude, aucun build."""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()

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
a.dossier_rapports = Path(tempfile.mkdtemp()) / "rapports"
ok, msg = a.lance({"zone": ["tasks"], "anciennete_jours": 5})
verifie(ok, True, "lancement accepte")
e = attend(a)
time.sleep(0.5)
copies = list(a.dossier_rapports.glob("rapport-*.json"))
verifie((len(copies), copies and json.loads(copies[0].read_text(encoding="utf-8"))["propositions"][0]["id"]), (1, e["rapport"]["propositions"][0]["id"]),
        "rapport fini copie hors depot (la 2e passe ne le perd plus)")
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

# 7b. rouvrir un rapport sauvegarde (A4 de menage-appliquer) : liste, nom pris dans la liste seulement, revalidation, recontre-verification
DOSSIER_R = Path(tempfile.mkdtemp()) / "rapports"
a = audit("ok")
a.dossier_rapports = DOSSIER_R
a.lance({})
attend(a)
time.sleep(0.5)
b = ml.Audit(RACINE, lambda: [], programme=PROG, dossier_rapports=DOSSIER_R)      # « page redemarree » : aucun rapport en memoire
verifie(b.etat()["rapport"], None, "page redemarree : aucun rapport en memoire")
liste = b.rapports()
verifie((len(liste), liste[0]["propositions"]), (1, 1), "rapports() : le rapport sauvegarde est liste avec son nombre de propositions")
nom = liste[0]["nom"]
sauve = json.loads((DOSSIER_R / nom).read_text(encoding="utf-8"))
sauve["propositions"][0]["verif"] = {"disponible": True, "n_code": 99, "n_docs": 99}          # verdict perime, ecrit dans le fichier
(DOSSIER_R / nom).write_text(json.dumps(sauve), encoding="utf-8")
msg = b.ouvre_rapport(nom)
e = b.etat()
v = e["rapport"]["propositions"][0].get("verif", {})
verifie((e["etat"], len(e["rapport"]["propositions"]), "rouvert" in msg), ("fini", 1, True), "ouvre_rapport : la page a un rapport fini")
verifie((v.get("n_code"), v.get("n_docs")) != (99, 99) and "disponible" in v, True, "ouvre_rapport : verdict git REFAIT, le verdict ecrit dans le fichier est ecarte")
verifie(len(list(DOSSIER_R.glob("rapport-*.json"))), 1, "ouvre_rapport ne sauvegarde pas une copie de plus")
# noms hostiles : seuls les noms de la liste passent
(DOSSIER_R.parent / "hors.json").write_text(json.dumps(sauve), encoding="utf-8")
for hostile in ["../hors.json", str(DOSSIER_R.parent / "hors.json"), "rapport-inconnu.json", "", None, 5, ["x"], nom + "/..", nom.upper() + "x"]:
    try:
        b.ouvre_rapport(hostile)
        verifie("accepte", "LookupError", f"nom hostile refuse : {hostile!r}")
    except LookupError:
        pass
    except Exception as ex:
        verifie(type(ex).__name__, "LookupError", f"nom hostile refuse : {hostile!r}")
# fichier illisible ou rapport invalide : 400 cote web (ValueError), l'etat de la page ne change pas
(DOSSIER_R / "rapport-zz-illisible.json").write_text("pas du json", encoding="utf-8")
(DOSSIER_R / "rapport-zz-invalide.json").write_text(json.dumps({"propositions": [dict(sauve["propositions"][0], chemin="../hors")]}), encoding="utf-8")
avant = b.etat()["rapport"]
verifie([r["propositions"] for r in b.rapports() if r["nom"] == "rapport-zz-illisible.json"], [None], "rapport illisible : liste avec propositions None")
for nom_mauvais in ("rapport-zz-illisible.json", "rapport-zz-invalide.json"):
    try:
        b.ouvre_rapport(nom_mauvais)
        verifie("accepte", "ValueError", f"rapport refuse : {nom_mauvais}")
    except ValueError:
        pass
verifie(b.etat()["rapport"] is avant, True, "rapport refuse : l'etat de la page est inchange")
# pendant un audit : refus, rapport en place intact
b._etat["etat"] = "en_cours"
try:
    b.ouvre_rapport(nom)
    verifie("accepte", "RuntimeError", "ouverture pendant un audit refusee")
except RuntimeError:
    pass
b._etat["etat"] = "fini"
# le plus recent d'abord
os.utime(DOSSIER_R / "rapport-zz-invalide.json", (time.time() + 100, time.time() + 100))
verifie(b.rapports()[0]["nom"], "rapport-zz-invalide.json", "rapports() : le plus recent d'abord")
verifie(ml.Audit(RACINE, lambda: [], programme=PROG).rapports(), [], "sans dossier de rapports : liste vide")
# mutant : sans le controle « le nom est dans la liste », un chemin hors du dossier s'ouvrirait
rapports_vrai = ml.Audit.rapports
ml.Audit.rapports = lambda self: [{"nom": "../hors.json", "date": "", "propositions": 1}]
c = ml.Audit(RACINE, lambda: [], programme=PROG, dossier_rapports=DOSSIER_R)
c.ouvre_rapport("../hors.json")
verifie(c.etat()["etat"], "fini", "mutant : un nom qui sort du dossier s'ouvre des qu'il est dans la liste (le controle de liste est donc la garde)")
ml.Audit.rapports = rapports_vrai

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
