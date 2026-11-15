"""Banc de taches_planifiees_gestes.py : faux schtasks, faux gh, fausse page Build, faux depot. Aucune tache, aucun workflow, aucun build.

    python outils_docs/scripts_python/outils_pc/test_taches_planifiees_gestes.py     (code de sortie 0 = vert)
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import suivi_sondes  # avancement reel sur la page Sondes en cours
suivi_sondes.suit()
import taches_planifiees_gestes as g

ECHECS = []


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


def leve(exception, f, *a, **k):
    try:
        f(*a, **k)
    except exception as e:
        return str(e) or True
    except Exception:                                   # noqa: BLE001 - une AUTRE exception = ECHEC du cas
        return False
    return False


def depot(exclus=None):
    d = Path(tempfile.mkdtemp())
    (d / "platformio_tasmota_cenv.ini").write_text("[env:a]\n[env:b]\n[env:c]\n", encoding="utf-8")
    if exclus is not None:
        (d / g.matrice.FICHIER_EXCLUS).parent.mkdir(parents=True)
        (d / g.matrice.FICHIER_EXCLUS).write_text(json.dumps({"exclus": exclus}), encoding="utf-8")
    return d


# -- envs exclus ----------------------------------------------------------------------------------------
d = depot()
verifie("env inconnu refuse (400)", "inconnu" in str(leve(ValueError, g.valide_envs, ["a", "zzz"], d)))
verifie("liste mal formee refusee", leve(ValueError, g.valide_envs, "a", d) is not False and leve(ValueError, g.valide_envs, [1], d) is not False)
verifie("valide : triee, sans doublon", g.valide_envs(["c", "a", "a"], d) == ["a", "c"])
ap = g.apercu_exclus_github(["b", "a"], d)
verifie("apercu GitHub : ajoutes, rien d'ecrit", ap["ajoutes"] == ["a", "b"] and ap["retires"] == [] and not (d / g.matrice.FICHIER_EXCLUS).exists())
r = g.ecrit_exclus_github(["b"], d)
verifie("ecriture GitHub : fichier relu par le lecteur du workflow", g.matrice.matrice(d) == ["a", "c"] and r["a_pousser"])
r = g.ecrit_exclus_github(["b"], d)
verifie("ecriture identique : inchange", r["inchange"] is True)
r = g.ecrit_exclus_github([], d)
verifie("retour a tous les envs", g.matrice.matrice(d) == ["a", "b", "c"] and r["retires"] == ["b"])


class FauxGit:
    """git injecte : aucune commande reelle. Chaque parametre force un refus."""
    def __init__(self, branche="development", ecart="0\t0", sale="", fetch=0, commit=0, push=0):
        self.appels, self.p = [], dict(branche=branche, ecart=ecart, sale=sale, fetch=fetch, commit=commit, push=push)

    def __call__(self, args, racine):
        self.appels.append(list(args))
        a = args[0]
        if a == "rev-parse":
            return (0, self.p["branche"]) if "--abbrev-ref" in args else (0, "abc123def4567890")
        if a == "fetch":
            return self.p["fetch"], "fetch ko" if self.p["fetch"] else ""
        if a == "rev-list":
            return 0, self.p["ecart"]
        if a == "status":
            return 0, self.p["sale"]
        if a == "commit":
            return self.p["commit"], "hook ko" if self.p["commit"] else "ok"
        if a == "push":
            return self.p["push"], "rejected" if self.p["push"] else "ok"
        return 1, "commande inattendue"


def ecrit_ou_non(d):
    return (d / g.matrice.FICHIER_EXCLUS).exists()


d = depot()
fg = FauxGit()
r = g.publie_exclus_github(["b"], d, fg)
verifie("publie : ecrit, commite CE fichier, pousse le sha vers development", r["publie"] is True and r["commit"] == "abc123def" and g.matrice.matrice(d) == ["a", "c"]
        and any(c[0] == "commit" and c[-2:] == ["--", "outils_docs/compilations_nuit/envs_github.json"] for c in fg.appels)
        and ["push", "origin", "abc123def4567890:development"] in fg.appels)
verifie("publie : jamais de force, jamais d'ajout global", not any(("--force" in c or "-f" in c or "--force-with-lease" in c) for c in fg.appels) and not any(c[0] == "add" for c in fg.appels))
fg = FauxGit()
r = g.publie_exclus_github(["b"], d, fg)
verifie("publie, rien a changer : aucun appel git", r["publie"] is False and fg.appels == [])
for nom, kw, mot in (("autre branche", dict(branche="chantier"), "chantier"), ("commits non pousses", dict(ecart="0\t2"), "non pousses"),
                     ("en retard sur origin", dict(ecart="1\t0"), "retard"), ("fichier deja modifie", dict(sale=" M outils_docs/x"), "deja modifie"),
                     ("fetch en echec", dict(fetch=1), "fetch")):
    d2, fg = depot(), FauxGit(**kw)
    verifie(f"publie refuse ({nom}) : rien d'ecrit, ni commit ni push", mot in str(leve(RuntimeError, g.publie_exclus_github, ["b"], d2, fg))
            and not ecrit_ou_non(d2) and not any(c[0] in ("commit", "push") for c in fg.appels))
d2, fg = depot(), FauxGit(push=1)
verifie("push refuse : commit local signale", "EN LOCAL" in str(leve(RuntimeError, g.publie_exclus_github, ["b"], d2, fg)) and ecrit_ou_non(d2))
d2, fg = depot(), FauxGit(commit=1)
verifie("commit refuse : pas de push", "commit refuse" in str(leve(RuntimeError, g.publie_exclus_github, ["b"], d2, fg)) and not any(c[0] == "push" for c in fg.appels))
verifie("publie : env inconnu refuse avant tout git", (lambda f: leve(ValueError, g.publie_exclus_github, ["zzz"], depot(), f) is not False and f.appels == [])(FauxGit()))
dossier = tempfile.mkdtemp()
Path(dossier, "config.json").write_text(json.dumps({"actif": False, "port": 7711, "envs_exclus": ["c"]}), encoding="utf-8")
r = g.ecrit_exclus_pc(["a"], dossier, d)
c = json.loads(Path(dossier, "config.json").read_text(encoding="utf-8"))
verifie("exclusion PC : garde actif et port, change la liste", c == {"actif": False, "port": 7711, "envs_exclus": ["a"]} and r["avant"] == ["c"])
verifie("exclusion PC : env inconnu refuse, fichier intact", leve(ValueError, g.ecrit_exclus_pc, ["zzz"], dossier, d) is not False
        and json.loads(Path(dossier, "config.json").read_text(encoding="utf-8"))["envs_exclus"] == ["a"])


# -- voie PC --------------------------------------------------------------------------------------------
class FauxSchtasks:
    def __init__(self, existe=True):
        self.appels, self.existe, self.statut = [], existe, "Activé"

    def __call__(self, *a):
        self.appels.append(a)
        if a[0] == "/query":
            if not self.existe:
                return 1, "introuvable"
            return 0, ('"Statut de la tâche planifiée","Prochaine exécution"\n' f'"{self.statut}","16/11/2026 02:00:00"\n')
        if a[0] == "/change" and ("/enable" in a or "/disable" in a):
            self.statut = "Activé" if "/enable" in a else "Désactivé"
        return 0, "ok"


s = FauxSchtasks()
verifie("PC desactive : /disable, etat relu", g.pc_active(False, s)["actif"] is False and any("/disable" in a for a in s.appels))
verifie("PC active : /enable", g.pc_active(True, s)["actif"] is True)
verifie("PC heure : /st sans changer l'etat", g.pc_heure("03:15", s)["actif"] is True and any("/st" in a and "03:15" in a for a in s.appels))
verifie("PC heure invalide refusee", leve(ValueError, g.pc_heure, "25:00", s) is not False)
verifie("PC tache absente : refus clair", "n'existe pas" in str(leve(RuntimeError, g.pc_active, True, FauxSchtasks(existe=False))))


def fausse_page(en_cours, arret_code=200, morte=False):
    journal = []

    def appel(port, chemin, corps=None, delai=30):
        journal.append((chemin, corps))
        if morte:
            return 0, "refuse"
        if chemin == "/execution":
            return 200, {"en_cours": en_cours, "numero": 0}
        if chemin == "/arreter":
            return arret_code, "refuse" if arret_code != 200 else {"ok": True}
        return 404, "x"
    return appel, journal


appel, j = fausse_page(True)
verifie("PC arreter : POST /arreter immediat", g.pc_arreter(7700, appel) == {"arret": "immediat"} and ("/arreter", {"immediat": True}) in j)
appel, j = fausse_page(False)
verifie("PC arreter sans serie : refus, aucun POST", leve(RuntimeError, g.pc_arreter, 7700, appel) is not False and not any(c == "/arreter" for c, _ in j))
appel, j = fausse_page(True, arret_code=409)
verifie("PC arreter refuse par la page : RuntimeError", leve(RuntimeError, g.pc_arreter, 7700, appel) is not False)
appel, j = fausse_page(True, morte=True)
verifie("PC arreter page morte : RuntimeError", "ne repond pas" in str(leve(RuntimeError, g.pc_arreter, 7700, appel)))

import os
import socket
import threading
DOSSIER_NUIT = tempfile.mkdtemp()                           # jamais le vrai dossier de donnees : aucun verrou reel lu
ETEINTE = lambda port: True                                 # jamais un vrai socket vers le port 7700 de la page Build de l'utilisateur
refuses = []
appel, j = fausse_page(True)
verifie("PC lancer pendant un build : refuse, rien demarre",
        leve(RuntimeError, g.pc_lancer, 7700, appel, lambda *a, **k: refuses.append(a), ETEINTE, DOSSIER_NUIT) is not False and not refuses)
lances = []
appel, j = fausse_page(False)
verifie("PC lancer : processus detache vers compilation_nuit.py", g.pc_lancer(7700, appel, lambda c, **k: lances.append((c, k)), ETEINTE, DOSSIER_NUIT) == {"lance": True}
        and lances[0][0][1].endswith("compilation_nuit.py") and lances[0][1]["stdin"] is not None)
appel, j = fausse_page(False, morte=True)
lances.clear()
verifie("PC lancer page eteinte : demarre quand meme (le script la lance)", g.pc_lancer(7700, appel, lambda c, **k: lances.append(c), ETEINTE, DOSSIER_NUIT) == {"lance": True} and lances)

# page LENTE (delai depasse, port ouvert) : on ne demarre pas un second build_web.py par-dessus
lances.clear()
appel, j = fausse_page(False, morte=True)
verifie("PC lancer page lente : refuse, rien demarre", "lente" in str(leve(RuntimeError, g.pc_lancer, 7700, appel, lambda c, **k: lances.append(c), lambda p: False, DOSSIER_NUIT)) and not lances)
# un compilation_nuit.py deja vivant (verrou en_cours.json) : refuse
verrou = tempfile.mkdtemp()
Path(verrou, "en_cours.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
appel, j = fausse_page(False)
verifie("PC lancer avec un script de nuit deja vivant : refuse, rien demarre, page non interrogee",
        "deja en cours" in str(leve(RuntimeError, g.pc_lancer, 7700, appel, lambda c, **k: lances.append(c), ETEINTE, verrou)) and not lances and not j)
Path(verrou, "en_cours.json").write_text(json.dumps({"pid": 99999999}), encoding="utf-8")
verifie("PC lancer avec un verrou perime : part", g.pc_lancer(7700, appel, lambda c, **k: lances.append(c), ETEINTE, verrou) == {"lance": True})
# page_eteinte : vrai socket local, port ferme = eteinte, port a l'ecoute = pas eteinte
with socket.socket() as ecoute:
    ecoute.bind(("127.0.0.1", 0))
    ecoute.listen(1)
    verifie("page_eteinte : port a l'ecoute -> False", g.page_eteinte(ecoute.getsockname()[1]) is False)
    port_ferme = ecoute.getsockname()[1]
verifie("page_eteinte : port ferme (connexion refusee) -> True", g.page_eteinte(port_ferme) is True)


# -- voie GitHub ----------------------------------------------------------------------------------------
class FauxGh:
    def __init__(self, runs=None, code=0, sortie=""):
        self.appels, self.runs, self.code, self.sortie, self.etat = [], runs or {}, code, sortie, "active"

    def __call__(self, args, delai=12):
        self.appels.append(args)
        if self.code:
            return self.code, self.sortie
        if args[:2] == ["workflow", "disable"]:
            self.etat = "disabled_manually"
        if args[:2] == ["workflow", "enable"]:
            self.etat = "active"
        if args[:2] == ["workflow", "list"]:
            return 0, json.dumps([{"name": "Build_custom", "state": self.etat}, {"name": "autre", "state": "active"}])
        if args[:2] == ["run", "list"]:
            return 0, json.dumps([{"databaseId": i} for i in self.runs.get(args[args.index("--status") + 1], [])])
        return 0, ""


f = FauxGh()
verifie("GitHub desactive : etat relu", g.github_active(False, f) == {"etat": "disabled_manually", "actif": False})
verifie("GitHub active", g.github_active(True, f)["actif"] is True)
f = FauxGh()
def gh_illisible(args, delai=0):
    if args[:2] == ["workflow", "list"]:
        return 0, "{pas du json"
    if args[:2] == ["run", "list"]:
        return 0, "<html>"
    return 0, ""


r = g.github_active(False, gh_illisible)
verifie("GitHub : liste illisible apres le geste -> avertissement, pas d'erreur", r["actif"] is None and "non relu" in r["avertissement"])
verifie("GitHub arreter : liste des runs illisible -> RuntimeError (pas un 400)", "illisible" in str(leve(RuntimeError, g.github_arreter, gh_illisible)))
verifie("GitHub lancer : workflow run sur development", g.github_lancer(f) == {"lance": True} and f.appels[0][:3] == ["workflow", "run", "Build_custom"] and "development" in f.appels[0])
f = FauxGh(runs={"in_progress": [11], "queued": [12]})
verifie("GitHub arreter : annule en cours ET en file", g.github_arreter(f) == {"annules": [11, 12]} and ["run", "cancel", "11", "-R", g.DEPOT] in f.appels)
verifie("GitHub arreter sans run : refus", "aucune compilation" in str(leve(RuntimeError, g.github_arreter, FauxGh())))
verifie("GitHub hors ligne : phrase claire, pas de trace", "injoignable" in str(leve(RuntimeError, g.github_lancer, FauxGh(code=124, sortie="delai"))))
verifie("gh absent : phrase claire", "absente" in str(leve(RuntimeError, g.github_active, True, FauxGh(code=127, sortie="x"))))

print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
