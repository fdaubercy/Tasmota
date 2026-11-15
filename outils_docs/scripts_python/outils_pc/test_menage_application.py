"""Banc de menage_application (apercu d'un lot de deplacements), avec mutants. Code de sortie 0 = vert.

Faux depot git temporaire, jamais le vrai. Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> test_menage_application.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import menage_application as ma

ECHECS = []


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")


def git(racine, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=racine, capture_output=True, check=True)


def ecrit(racine, chemin, texte="x\n"):
    p = Path(racine) / chemin
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texte, encoding="utf-8")


def prop(ident, chemin, vers="archives/x.txt", action="deplacer", en_cours=False):
    return {"id": ident, "categorie": "hors_dossier", "chemin": chemin, "action": action, "risque": "faible", "en_cours": en_cours,
            "vers": vers, "constat": "c", "preuve": "p", "casserait": "rien"}


def arbre(racine):
    """Photo de l'arbre de travail ET de l'index : l'apercu ne doit rien changer."""
    fichiers = sorted(str(p.relative_to(racine)) for p in Path(racine).rglob("*") if ".git" not in p.parts)
    index = subprocess.run(["git", "ls-files", "-s"], cwd=racine, capture_output=True).stdout
    return fichiers, index


racine = Path(tempfile.mkdtemp()) / "depot"
racine.mkdir()
git(racine, "init", "-q")
ecrit(racine, "libre.txt", "rien ne me cite\n")
ecrit(racine, "-rf", "nom hostile\n")
ecrit(racine, "cite_doc.txt", "contenu\n")
ecrit(racine, "docs/lisez.md", "voir cite_doc.txt pour le detail\n")
ecrit(racine, "cite_code.py", "x = 1\n")
ecrit(racine, "config.ini", "script = cite_code.py\n")
ecrit(racine, "modifie.txt", "avant\n")
ecrit(racine, "pris.txt", "a deplacer\n")
ecrit(racine, "archives/existe.txt", "deja la\n")
ecrit(racine, "dossier/a.txt", "x\n")
ecrit(racine, "autre.txt", "autre\n")
ecrit(racine, "casse.txt", "x\n")
git(racine, "add", "-A")
git(racine, "commit", "-q", "-m", "init")
ecrit(racine, "modifie.txt", "apres\n")
ecrit(racine, "nonsuivi.txt", "pas suivi\n")

avant = arbre(racine)
PROPS = [prop("E1", "libre.txt", "archives/libre.txt"), prop("E2", "-rf", "archives/rf.txt"),
         prop("S1", "libre.txt", None, action="supprimer"), prop("C1", "libre.txt", "archives/c1.txt", en_cours=True),
         prop("V1", "libre.txt", None), prop("D1", "cite_doc.txt", "archives/cite_doc.txt"), prop("K1", "cite_code.py", "archives/cite_code.py"),
         prop("M1", "modifie.txt", "archives/modifie.txt"), prop("N1", "nonsuivi.txt", "archives/nonsuivi.txt"),
         prop("P1", "disparu.txt", "archives/disparu.txt"), prop("X1", "pris.txt", "archives/existe.txt"),
         prop("R1", "dossier", "archives/dossier"), prop("Y1", "autre.txt", "archives/libre.txt"), prop("I1", "autre.txt", "autre.txt"),
         prop("G1", "autre.txt", "../hors/depot.txt")]


def apercu(*ids, props=PROPS, rac=racine):
    return ma.previsualise(list(ids), props, rac)


def motifs(r):
    return {x["id"]: x["motif"] for x in r["refuses"]}


# 1. un deplacement eligible : commande exacte, jamais de shell, dossier a creer signale
r = apercu("E1")
verifie([(e["id"], e["commande"], e["cree_dossier"]) for e in r["eligibles"]], [("E1", "git mv -- libre.txt archives/libre.txt", None)], "eligible : commande exacte")
r = apercu("E2")
verifie([e["commande"] for e in r["eligibles"]], ["git mv -- -rf archives/rf.txt"], "nom hostile : « -- » devant les chemins, jamais pris pour une option")
r = apercu("E1")
verifie(r["eligibles"][0]["cree_dossier"], None, "dossier de destination deja la : rien a creer")
ecrit(racine, "autre_dest/placeholder.txt")
os.remove(racine / "autre_dest" / "placeholder.txt"); os.rmdir(racine / "autre_dest")
r = ma.previsualise(["E1"], [prop("E1", "libre.txt", "nouveau/dossier/libre.txt")], racine)
verifie(r["eligibles"][0]["cree_dossier"], "nouveau/dossier", "dossier de destination absent : annonce qu'il sera cree")

# 2. refus, un motif par cas
m = motifs(apercu("S1", "C1", "V1", "D1", "K1", "M1", "N1", "P1", "X1", "R1", "I1"))
verifie("S1" in m, False, "suppression sans renvoi : plus refusee (git rm autorise, decision du 2026-11-15)")
verifie("archiver" in motifs(ma.previsualise(["AR"], PROPS + [prop("AR", "libre.txt", "archives/ar.txt", action="archiver")], racine))["AR"], True, "archiver reste refuse")
verifie("en cours" in m["C1"], True, "proposition en cours refusee")
verifie("destination" in m["V1"], True, "sans destination exacte : refusee")
verifie("1 document" in m["D1"], True, "cite par un document : refusee (etape 2, pas 1)")
verifie("1 fichier(s) de code" in m["K1"], True, "cite par du code ou une config : refusee")
verifie("en cours" in m["M1"], True, "fichier modifie : refuse (devient « en cours » avant tout autre motif)")
verifie("en cours" in m["N1"], True, "fichier non suivi : refuse (idem, il est modifie pour git)")
verifie("n'existe plus" in m["P1"], True, "chemin disparu : refuse")
verifie("existe deja" in m["X1"], True, "destination deja prise : refusee")
verifie("dossier" in m["R1"], True, "un dossier ne se deplace pas d'un coup")
verifie("existe deja" in m["I1"], True, "destination identique au chemin : refusee (elle existe deja)")
verifie(apercu("G1")["eligibles"], [], "destination hors depot : jamais eligible")

# 2a. suppressions par git rm, simulees par git lui-meme (-n)
r = apercu("S1")
verifie([(e["id"], e["action"], e["vers"], e["commande"]) for e in r["eligibles"]], [("S1", "supprimer", None, "git rm -- libre.txt")], "suppression eligible : commande git rm exacte, sans destination")
verifie((r["eligibles"][0]["dry_run"]["ok"], "libre.txt" in r["eligibles"][0]["dry_run"]["sortie"]), (True, True), "dry-run reel de git : ok, sortie de git montree")
r = ma.previsualise(["E2"], [prop("E2", "-rf", None, action="supprimer")], racine)
verifie(([e["commande"] for e in r["eligibles"]], r["eligibles"][0]["dry_run"]["ok"]), (["git rm -- -rf"], True), "nom hostile -rf supprime : « -- » devant le chemin, dry-run ok")
verifie("dossier" in motifs(ma.previsualise(["R2"], [prop("R2", "dossier", None, action="supprimer")], racine))["R2"], True, "suppression d'un dossier refusee")
verifie("cite" in motifs(ma.previsualise(["K2"], [prop("K2", "cite_code.py", None, action="supprimer")], racine))["K2"], True, "suppression d'un fichier cite par du code refusee")
verifie("modifie" in motifs(ma.previsualise(["M2"], [prop("M2", "modifie.txt", None, action="supprimer")], racine))["M2"] or "en cours" in motifs(ma.previsualise(["M2"], [prop("M2", "modifie.txt", None, action="supprimer")], racine))["M2"], True, "suppression d'un fichier modifie refusee")
verifie("meme fichier" in motifs(ma.previsualise(["S1", "E1"], PROPS, racine)).get("E1", ""), True, "supprimer et deplacer le meme fichier dans un lot : le second refuse")
for argv in (ma.argv_git("supprimer", "a", None, False), ma.argv_git("deplacer", "a", "b", False)):
    verifie(("-f" in argv or "-r" in argv or "--force" in argv, "--" in argv), (False, True), f"jamais -f ni -r, « -- » present : {argv[2]}")
verifie("-n" in ma.argv_git("supprimer", "a", None, True) and "-n" in ma.argv_git("deplacer", "a", "b", True), True, "la simulation porte -n")
verifie("-n" in ma.argv_git("supprimer", "a", None, False) or "-n" in ma.argv_git("deplacer", "a", "b", False), False, "l'application reelle ne porte pas -n")
r = ma.previsualise(["E3"], [prop("E3", "libre.txt", "nouveau/dossier/libre.txt")], racine)
verifie((r["eligibles"][0]["dry_run"]["ok"], r["eligibles"][0]["cree_dossier"]), (True, "nouveau/dossier"), "dossier de destination absent : git -n accepte, le dossier a creer est annonce (A2 le creera avant git mv)")
_dry_avant = ma._dry_run
ma._dry_run = lambda rac, action, chemin, vers: (False, "fatal: destination directory does not exist")
r = ma.previsualise(["E3"], [prop("E3", "libre.txt", "nouveau/dossier/libre.txt")], racine)
ma._dry_run = _dry_avant
verifie((r["eligibles"], "git refuse" in motifs(r).get("E3", "")), ([], True), "si git refuse faute de dossier : la ligne est refusee, jamais eligible sans simulation reussie")
vrai_dry = ma._dry_run
ma._dry_run = lambda rac, action, chemin, vers: (False, "fatal: simulation")
r = apercu("S1", "E1")
verifie((r["eligibles"], "git refuse" in motifs(r).get("S1", "")), ([], True), "git refuse en simulation : la ligne quitte le lot, rien d'eligible")
ma._dry_run = vrai_dry
vrai_head = ma._head
e1 = apercu("S1")["empreinte"]
ma._head = lambda rac: "autre-commit"
verifie(apercu("S1")["empreinte"] != e1, True, "empreinte liee au HEAD : un autre commit change l'empreinte")
ma._head = vrai_head
verifie(apercu("S1")["head"] != "", True, "head rendu")

# 2b. destinations et sources protegees, collisions de lot
PP =[prop("H1", "libre.txt", ".git/hooks/pre-commit"), prop("H2", "libre.txt", ".GIT/x"), prop("H3", "libre.txt", ".claude/hooks/x.sh"),
      prop("H4", "libre.txt", ".github/workflows/x.yml"), prop("A1", "libre.txt", "archives/existe.txt"), prop("B1", "archives/existe.txt", "archives/chaine2.txt"),
      prop("Q1", "autre.txt", "archives/Casse.txt"), prop("Q2", "casse.txt", "archives/casse.txt"),
      prop("F1", "autre.txt", "libre.txt/dessous.txt"), prop("L1", "libre.txt", "archives\\barre.txt")]
for ident in ("H1", "H2", "H3", "H4"):
    verifie("protege" in motifs(ma.previsualise([ident], PP, racine)).get(ident, ""), True, f"destination protegee refusee ({ident})")
r = ma.previsualise(["Q1", "Q2"], PP, racine)
verifie(([e["id"] for e in r["eligibles"]], "meme destination" in motifs(r).get("Q2", "")), (["Q1"], True), "meme destination a la casse pres : la seconde refusee")
r = ma.previsualise(["A1", "B1"], PP, racine)
verifie(([e["id"] for e in r["eligibles"]], "existe deja" in motifs(r).get("A1", "")), (["B1"], True), "deplacements enchaines : l'amont (destination deja prise) est refuse, jamais les deux")
r = ma.previsualise(["F1"], PP, racine)
verifie(("dossier de destination est un fichier" in motifs(r).get("F1", "")), True, "parent de destination qui est un fichier : refuse, pas « dossier a creer »")
r = ma.previsualise(["L1"], PP, racine)
verifie([e["commande"] for e in r["eligibles"]], ["git mv -- libre.txt archives/barre.txt"], "chemin avec anti-slash : la commande porte la forme normalisee controlee")

# 3. lot : meme destination deux fois, identifiant repete, identifiant inconnu
r = apercu("E1", "Y1")
verifie(([e["id"] for e in r["eligibles"]], "meme destination" in motifs(r).get("Y1", "")), (["E1"], True), "deux propositions vers la meme destination : la seconde refusee")
r = apercu("E1", "E1")
verifie(len(r["eligibles"]), 1, "identifiant coche deux fois : un seul deplacement")
r = apercu("ZZ")
verifie(("inconnue" in motifs(r)["ZZ"], r["eligibles"]), (True, []), "identifiant inconnu : refuse")
for libelle, ids in [("vide", []), ("pas une liste", "E1"), ("pas des textes", [1]), ("trop long", [f"i{n}" for n in range(ma.MAX_LOT + 1)])]:
    try:
        ma.previsualise(ids, PROPS, racine)
        verifie("accepte", "refuse", f"ids invalides ({libelle})")
    except ValueError:
        pass

# 4. empreinte : stable pour le meme lot, differente si le lot change
verifie(apercu("E1", "E2")["empreinte"], apercu("E1", "E2")["empreinte"], "empreinte stable")
verifie(apercu("E1", "E2")["empreinte"] != apercu("E1")["empreinte"], True, "empreinte differente si le lot change")

# 5. l'apercu ne touche a rien (arbre de travail et index)
apercu("E1", "E2", "S1", "D1", "X1")
verifie(arbre(racine), avant, "apercu : arbre de travail et index inchanges")

# 6. depot sans git : tout refuse, rien d'eligible
sans = Path(tempfile.mkdtemp())
ecrit(sans, "libre.txt")
r = ma.previsualise(["E1"], [prop("E1", "libre.txt", "archives/libre.txt")], sans)
verifie((r["eligibles"], "indisponible" in motifs(r)["E1"]), ([], True), "depot sans git : verification indisponible, rien d'eligible")

# 7. mutants : le banc doit voir si on affaiblit un garde-fou
vrai = ma.motif_refus
ma.motif_refus = lambda p, v, r=None: None
verifie(len(apercu("K1", "M1", "N1")["eligibles"]) > 0, True, "mutant sans motif de refus : un fichier cite devient eligible (le banc 2 etait discriminant)")
ma.motif_refus = vrai
ma.motif_refus = lambda p, v, r=None: vrai(p, dict(v, n_code=0, n_docs=0), r)
verifie("K1" in [e["id"] for e in apercu("K1")["eligibles"]], True, "mutant qui ignore les renvois : K1 devient eligible (le banc le voit)")
ma.motif_refus = vrai
sauve = ma._est_dossier
ma._est_dossier = lambda rac, chemin: False
verifie("R1" in [e["id"] for e in apercu("R1")["eligibles"]], True, "mutant sans test de dossier : R1 devient eligible (le banc le voit)")
ma._est_dossier = sauve
verifie(apercu("K1")["eligibles"], [], "apres mutants : garde-fous restaures")
_p = ma._protege
ma._protege = lambda chemin, rac=None: False
verifie(ma.previsualise(["H1"], PP, racine)["eligibles"] != [], True, "mutant sans dossiers proteges : .git devient une destination (le banc le voit)")
ma._protege = _p
ma._dry_run = lambda rac, action, chemin, vers: (True, "")
verifie(apercu("S1")["eligibles"][0]["dry_run"]["ok"], True, "mutant dry-run neutre : plus aucun refus de git possible (temoin)")
ma._dry_run = lambda rac, action, chemin, vers: (False, "x")
verifie(apercu("S1")["eligibles"], [], "mutant dry-run toujours refuse : rien d'eligible (le banc voit que le dry-run decide)")
ma._dry_run = vrai_dry

# 8. application reelle, sur des depots JETABLES : recontrole, arret a la premiere erreur, rien de commite
def depot_neuf():
    rac = Path(tempfile.mkdtemp()) / "depot"
    rac.mkdir()
    git(rac, "init", "-q")
    for nom in ("libre.txt", "autre.txt", "-rf", "troisieme.txt"):
        ecrit(rac, nom, nom + "\n")
    git(rac, "add", "-A")
    git(rac, "commit", "-q", "-m", "init")
    return rac


def lot_neuf():
    return [prop("S1", "libre.txt", None, action="supprimer"), prop("E1", "autre.txt", "rangees/neuf/autre.txt"),
            prop("S2", "-rf", None, action="supprimer"), prop("E3", "troisieme.txt", "rangees/neuf/troisieme.txt")]


def suivis(rac):
    return sorted(subprocess.run(["git", "ls-files"], cwd=rac, capture_output=True).stdout.decode().split())


def lance(rac, ids, props=None, **kw):
    props = props or lot_neuf()
    ap = ma.previsualise(ids, props, rac)
    kw.setdefault("verifie_refs", lambda r: {"code": 0, "sortie": "ok"})
    kw.setdefault("builds_en_cours", lambda: [])
    return ap, ma.applique(ids, ap["empreinte"], ap["head"], props, rac, **kw)


def commits(rac):
    return subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=rac, capture_output=True).stdout.decode().strip()


d = depot_neuf()
journal = Path(tempfile.mkdtemp()) / "j" / "applications.jsonl"
ap, res = lance(d, ["S1", "E1", "S2", "E3"], journal=journal)
verifie((res["echec"], [f["id"] for f in res["faits"]], res["restants"]), (None, ["S1", "E1", "S2", "E3"], []), "application : les 4 lignes faites")
verifie(suivis(d), ["rangees/neuf/autre.txt", "rangees/neuf/troisieme.txt"], "git rm et git mv appliques dans l'index (dossier de destination cree avant git mv)")
verifie((os.path.exists(d / "libre.txt"), os.path.exists(d / "-rf"), (d / "rangees/neuf/autre.txt").is_file()), (False, False, True), "arbre de travail : supprimes, deplace")
verifie(commits(d), "1", "RIEN n'est commite par la page")
verifie(res["renvois"], {"code": 0, "sortie": "ok"}, "controle des renvois lance apres l'application")
lignes = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines()]
verifie([(x["id"], x.get("ok")) for x in lignes if "ok" in x], [("S1", True), ("E1", True), ("S2", True), ("E3", True)], "journal hors depot : une ligne par action")
verifie([x["id"] for x in lignes if x.get("intention")], ["S1", "E1", "S2", "E3"], "journal : une ligne d'intention ecrite AVANT chaque git (trace meme si le processus est tue)")
verifie([lignes[i].get("intention") for i in (0, 2, 4, 6)], [True] * 4, "journal : l'intention precede le resultat")

# annulation par git : le travail est recuperable
subprocess.run(["git", "restore", "--staged", "--worktree", "--", "libre.txt"], cwd=d, capture_output=True)
verifie(os.path.exists(d / "libre.txt"), True, "git restore --staged --worktree annule une suppression")

# apercu perime : un autre commit, un fichier modifie, un lot different
d = depot_neuf()
ap = ma.previsualise(["S1"], lot_neuf(), d)
ecrit(d, "ajout.txt")
git(d, "add", "-A")
git(d, "commit", "-q", "-m", "autre")
try:
    ma.applique(["S1"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: [], verifie_refs=lambda r: None)
    verifie("applique", "refuse", "HEAD change depuis l'apercu : refus")
except RuntimeError as e:
    verifie(("plus a jour" in str(e), os.path.exists(d / "libre.txt")), (True, True), "HEAD change : refus, rien applique")
d = depot_neuf()
ap = ma.previsualise(["S1"], lot_neuf(), d)
ecrit(d, "libre.txt", "modifie depuis l'apercu\n")
try:
    ma.applique(["S1"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: [], verifie_refs=lambda r: None)
    verifie("applique", "refuse", "fichier modifie depuis l'apercu : refus")
except (RuntimeError, ValueError):
    verifie(os.path.exists(d / "libre.txt"), True, "fichier modifie depuis l'apercu : refus, fichier intact")
for libelle, emp, hd in [("empreinte vide", "", ap["head"]), ("head vide", ap["empreinte"], ""), ("empreinte inventee", "0" * 16, ap["head"])]:
    try:
        ma.applique(["S1"], emp, hd, lot_neuf(), d, lambda: [], verifie_refs=lambda r: None)
        verifie("applique", "refuse", libelle)
    except (RuntimeError, ValueError):
        pass

# build en cours, application deja en cours, lot sans ligne eligible
d = depot_neuf()
try:
    lance(d, ["S1"], builds_en_cours=lambda: ["pio run -e x"])
    verifie("applique", "refuse", "build en cours : refus")
except RuntimeError as e:
    verifie(("build" in str(e), os.path.exists(d / "libre.txt")), (True, True), "build en cours : refus, rien applique")
ap = ma.previsualise(["S1"], lot_neuf(), d)
ma._VERROU.acquire()
try:
    ma.applique(["S1"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: [], verifie_refs=lambda r: None)
    verifie("applique", "refuse", "application deja en cours : refus")
except RuntimeError as e:
    verifie("deja en cours" in str(e), True, "application deja en cours : refus")
finally:
    ma._VERROU.release()
try:
    ma.applique(["ZZ"], "x", "y", lot_neuf(), d, lambda: [], verifie_refs=lambda r: None)
except (RuntimeError, ValueError):
    pass
verifie(ma._VERROU.acquire(blocking=False), True, "le verrou est toujours relache apres un refus")
ma._VERROU.release()

# arret a la premiere erreur : les suivantes ne sont pas lancees
d = depot_neuf()
vrai_lance = ma._lance_git
compte = {"n": 0}


def lance_qui_echoue_au_2e(racine, action, chemin, vers, simulation):
    if simulation:
        return vrai_lance(racine, action, chemin, vers, simulation)
    compte["n"] += 1
    return (False, "fatal: simule") if compte["n"] == 2 else vrai_lance(racine, action, chemin, vers, simulation)


ma._lance_git = lance_qui_echoue_au_2e
ap, res = lance(d, ["S1", "E1", "S2", "E3"])
ma._lance_git = vrai_lance
verifie(([f["id"] for f in res["faits"]], res["echec"]["id"], res["echec"]["motif"], res["restants"]), (["S1"], "E1", "fatal: simule", ["S2", "E3"]),
        "erreur de git a la 2e ligne : arret, 1 fait, la fautive nommee, 2 restantes non lancees")
verifie((os.path.exists(d / "-rf"), os.path.exists(d / "troisieme.txt"), os.path.isdir(d / "rangees")), (True, True, False),
        "lignes non lancees intactes, dossier cree pour rien retire")

# mode a blanc : meme parcours, rien de modifie, aucun git sans -n
d = depot_neuf()
sauve_arbre = arbre(d)
appels = []
vrai_lance = ma._lance_git
ma._lance_git = lambda racine, action, chemin, vers, simulation: (appels.append(simulation), vrai_lance(racine, action, chemin, vers, simulation))[1]
journal_b = Path(tempfile.mkdtemp()) / "j" / "applications.jsonl"
ap, res = lance(d, ["S1", "E1", "S2", "E3"], a_blanc=True, journal=journal_b, verifie_refs=lambda r: (_ for _ in ()).throw(AssertionError("renvois lances a blanc")))
ma._lance_git = vrai_lance
verifie((res["a_blanc"], res["echec"], [f["id"] for f in res["faits"]], res["renvois"]), (True, None, ["S1", "E1", "S2", "E3"], None), "a blanc : les 4 lignes jouees, pas de controle des renvois")
verifie(arbre(d), sauve_arbre, "a blanc : arbre de travail et index strictement inchanges, aucun dossier cree")
verifie((len(appels) >= 8, set(appels[-4:])), (True, {True}), "a blanc : les 4 git de l'execution portent -n")
verifie(all(json.loads(x)["a_blanc"] for x in journal_b.read_text(encoding="utf-8").splitlines()), True, "a blanc : le journal le note")
ap = ma.previsualise(["S1"], lot_neuf(), d)
ecrit(d, "ajout.txt")
git(d, "add", "-A")
git(d, "commit", "-q", "-m", "autre")
try:
    ma.applique(["S1"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: [], verifie_refs=lambda r: None, a_blanc=True)
    verifie("joue", "refuse", "a blanc : un apercu perime est refuse comme en reel")
except RuntimeError:
    pass
try:
    ma.applique(["S1"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: ["pio"], a_blanc=True)
    verifie("joue", "refuse", "a blanc : refuse pendant un build comme en reel")
except RuntimeError:
    pass
d = depot_neuf()
vrai_journal = ma._journalise
etat_faute = {"arme": False}


def journal_arme(journal, ligne):
    if ligne.get("intention") and ligne["id"] == "E1":
        etat_faute["arme"] = True                    # le git qui suit l'intention de E1, et lui seul, echoue
    return vrai_journal(journal, ligne)


def lance_faute_a_blanc(racine, action, chemin, vers, simulation):
    if etat_faute["arme"]:
        etat_faute["arme"] = False
        return False, "fatal: simule a blanc"
    return vrai_lance(racine, action, chemin, vers, simulation)


ma._journalise, ma._lance_git = journal_arme, lance_faute_a_blanc
ap, res = lance(d, ["S1", "E1", "S2", "E3"], a_blanc=True)
ma._journalise, ma._lance_git = vrai_journal, vrai_lance
verifie((res["echec"] is not None, [f["id"] for f in res["faits"]]), (True, ["S1"]), "a blanc : s'arrete aussi a la premiere erreur de git")
d = depot_neuf()
ma._lance_git = lambda racine, action, chemin, vers, simulation: vrai_lance(racine, action, chemin, vers, False)       # mutant : a blanc ignore -n
try:
    lance(d, ["S1"], a_blanc=True)
except RuntimeError:
    pass                                             # le mutant a deja agi pendant l'apercu : l'empreinte a change, c'est justement la preuve
ma._lance_git = vrai_lance
verifie(os.path.exists(d / "libre.txt"), False, "mutant a blanc qui n'est pas a blanc : le fichier disparait (le banc de l'arbre le voit)")

# 9. durcissements de la relecture de securite : noms Windows, collisions, build en cours de lot, GIT_*
for libelle, chemin in [("nom court 8.3", "CLAUDE~1/agents/x.md"), ("point final", ".claude./agents/x.md"), ("espace final", ".claude /agents/x.md"),
                        (".github", ".github/workflows/x.yml"), (".gitignore", ".gitignore"), (".gitattributes", ".gitattributes"), ("casse", ".CLAUDE/x"), (".vscode", ".vscode/settings.json")]:
    verifie(ma._protege(chemin), True, f"chemin protege reconnu : {libelle}")
    verifie("protege" in motifs(ma.previsualise(["P"], [prop("P", "libre.txt", chemin)], racine)).get("P", ""), True, f"destination protegee refusee a l'apercu : {libelle}")
verifie(ma._protege("docs/a.md") or ma._protege("outils_docs/x.py"), False, "un chemin ordinaire n'est pas protege")
verifie(ma.motif_refus(prop("P", "~1/x.txt", None, action="supprimer"), {"disponible": True, "suivi": True}, racine) is not None, True, "source en nom court refusee")
d = depot_neuf()
ap = ma.previsualise(["E1", "E3"], [prop("E1", "autre.txt", "rangees/n"), prop("E3", "troisieme.txt", "rangees/n/dessous.txt")], d)
verifie(("rangees/n" in [e["vers"] for e in ap["eligibles"]], len(ap["eligibles"])), (True, 1), "destination ancetre d'une autre du lot : la seconde refusee (git mv rangerait dedans)")
r = ma.previsualise(["E1", "E3"], [prop("E1", "autre.txt", "rangees/n/dessous.txt"), prop("E3", "troisieme.txt", "rangees/n")], d)
verifie(len(r["eligibles"]), 1, "destination descendante d'une autre du lot : refusee aussi")
d = depot_neuf()
ap = ma.previsualise(["E1"], lot_neuf(), d)
os.makedirs(d / "rangees" / "neuf" / "autre.txt")                      # apparu depuis l'apercu : git rangerait DEDANS
try:
    ma.applique(["E1"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: [], verifie_refs=lambda r: None)
    verifie("applique", "refuse", "destination apparue depuis l'apercu")
except (RuntimeError, ValueError):
    pass
verifie(os.path.exists(d / "autre.txt"), True, "destination apparue : rien deplace")
d = depot_neuf()
etats = iter([[], ["pio run -e x"], ["pio run -e x"], ["pio run -e x"]])
ap = ma.previsualise(["S1", "E1", "S2"], lot_neuf(), d)
res = ma.applique(["S1", "E1", "S2"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: next(etats, ["pio"]), verifie_refs=lambda r: None)
verifie(([f["id"] for f in res["faits"]], "build" in res["echec"]["motif"], os.path.exists(d / "autre.txt")), (["S1"], True, True), "un build demarre pendant le lot : arret apres la ligne deja faite")
d = depot_neuf()
os.environ["GIT_DIR"] = str(Path(tempfile.mkdtemp()) / "ailleurs")
try:
    ok, sortie = ma._lance_git(d, "supprimer", "libre.txt", None, False)      # seul git d'ECRITURE est teste ici : l'aperçu lit avec l'environnement tel quel
finally:
    del os.environ["GIT_DIR"]
verifie((ok, os.path.exists(d / "libre.txt")), (True, False), "GIT_DIR du processus ignore : git agit dans le depot voulu")
try:
    ma.applique(["S1"], "x", "y", lot_neuf(), d)
    verifie("applique", "refuse", "garde de build obligatoire")
except TypeError:
    pass

# 10. retour en arriere : ce que l'application a fait se defait, dans l'ordre inverse, sans toucher a ce qui a change depuis
d = depot_neuf()
avant = arbre(d)
ap, res = lance(d, ["S1", "E1", "S2", "E3"])
verifie(all("dossiers_crees" in f for f in res["faits"]) and res["faits"][1]["dossiers_crees"] != [], True, "application : les dossiers crees sont notes pour pouvoir etre retires")
verifie(arbre(d) != avant, True, "retour en arriere : l'application a bien change l'arbre")
jr = Path(tempfile.mkdtemp()) / "j" / "applications.jsonl"
r = ma.annule(res["faits"], ap["head"], d, lambda: [], journal=jr)
verifie((r["echec"], [x["id"] for x in r["retablis"]], r["restants"]), (None, ["E3", "S2", "E1", "S1"], []), "retour en arriere : les 4 lignes rétablies, dans l'ordre inverse")
verifie(arbre(d), avant, "retour en arriere : arbre de travail ET index identiques a ceux d'avant l'application")
verifie(os.path.isdir(d / "rangees"), False, "retour en arriere : les dossiers crees par l'application sont retires")
verifie(commits(d), "1", "retour en arriere : rien n'est commite")
lj = [json.loads(x) for x in jr.read_text(encoding="utf-8").splitlines()]
verifie(([x["id"] for x in lj if x.get("intention")], all(x.get("retour") for x in lj)), (["E3", "S2", "E1", "S1"], True), "retour en arriere : journal, intention avant chaque git")
# un commit a eu lieu depuis : refus net, rien n'est touche
d = depot_neuf()
ap, res = lance(d, ["S1"])
git(d, "commit", "-q", "-m", "l'utilisateur a commite la suppression")
apres = arbre(d)
try:
    ma.annule(res["faits"], ap["head"], d, lambda: [])
    verifie("accepte", "RuntimeError", "retour en arriere : refuse apres un commit")
except RuntimeError as e:
    verifie(("commit" in str(e), arbre(d)), (True, apres), "retour en arriere : refuse apres un commit (git revert), rien n'est touche")
# build en cours : refuse
d = depot_neuf()
ap, res = lance(d, ["S1"])
try:
    ma.annule(res["faits"], ap["head"], d, lambda: ["pio run"])
    verifie("accepte", "RuntimeError", "retour en arriere : refuse pendant un build")
except RuntimeError as e:
    verifie(("build" in str(e), os.path.exists(d / "libre.txt")), (True, False), "retour en arriere : refuse pendant un build, rien n'est touche")
# le fichier a ete recree depuis : on n'ecrase jamais le travail de l'utilisateur
ecrit(d, "libre.txt", "version de l'utilisateur\n")
r = ma.annule(res["faits"], ap["head"], d, lambda: [])
verifie((r["retablis"], r["echec"] and "recree" in r["echec"]["motif"], (d / "libre.txt").read_text(encoding="utf-8")), ([], True, "version de l'utilisateur\n"),
        "retour en arriere : un fichier recree depuis n'est jamais ecrase")
# un fichier deplace puis modifie : refuse (l'etat indexe n'est plus celui du git mv)
d = depot_neuf()
ap, res = lance(d, ["E1"])
ecrit(d, "rangees/neuf/autre.txt", "modifie\n")
git(d, "add", "-A")
r = ma.annule(res["faits"], ap["head"], d, lambda: [])
verifie((r["retablis"], r["echec"] is not None, os.path.exists(d / "rangees/neuf/autre.txt")), ([], True, True), "retour en arriere : un fichier deplace puis modifie n'est pas remis en place")
# arret a la premiere erreur : les lignes restantes sont rendues, une 2e tentative peut finir
d = depot_neuf()
ap, res = lance(d, ["S1", "S2"])
ecrit(d, "-rf", "recree\n")                        # la derniere ligne (S2) est defaite en premier : elle echoue, S1 reste
r = ma.annule(res["faits"], ap["head"], d, lambda: [])
verifie(([x["id"] for x in r["retablis"]], r["restants"], r["echec"] and r["echec"]["id"]), ([], ["S1", "S2"], "S2"), "retour en arriere : arret a la premiere erreur, les lignes non defaites sont rendues")
os.remove(d / "-rf")
r = ma.annule(res["faits"], ap["head"], d, lambda: [])
verifie(([x["id"] for x in r["retablis"]], r["echec"]), (["S2", "S1"], None), "retour en arriere : une 2e tentative, une fois l'obstacle leve, rétablit tout")
# pas de retour en arriere pendant une application
d = depot_neuf()
ap, res = lance(d, ["S1"])
ma._VERROU.acquire()
try:
    ma.annule(res["faits"], ap["head"], d, lambda: [])
    verifie("accepte", "RuntimeError", "retour en arriere : refuse pendant une application")
except RuntimeError:
    pass
finally:
    ma._VERROU.release()
# mutant : sans la garde sur le HEAD, le retour en arriere s'executerait apres un commit
d = depot_neuf()
ap, res = lance(d, ["S1"])
git(d, "commit", "-q", "-m", "commite")
vrai_head = ma._head
ma._head = lambda racine: ap["head"]
r = ma.annule(res["faits"], ap["head"], d, lambda: [])
ma._head = vrai_head
verifie((len(r["retablis"]), r["echec"] is not None), (0, True), "mutant : HEAD masque, git restore echoue de lui-meme apres le commit (la garde HEAD reste la premiere ligne de defense)")

# mutants : le banc doit voir si on affaiblit un garde-fou de l'application
d = depot_neuf()
ap = ma.previsualise(["S1"], lot_neuf(), d)
ecrit(d, "ajout.txt")
git(d, "add", "-A")
git(d, "commit", "-q", "-m", "autre")
vrai_prev = ma.previsualise
ma.previsualise = lambda ids, props, rac: dict(vrai_prev(ids, props, rac), empreinte=ap["empreinte"], head=ap["head"])
try:
    ma.applique(["S1"], ap["empreinte"], ap["head"], lot_neuf(), d, lambda: [], verifie_refs=lambda r: None)
    accepte = True
except (RuntimeError, ValueError):
    accepte = False
ma.previsualise = vrai_prev
verifie(accepte, True, "mutant sans recontrole : un apercu perime est applique (le banc voit que le recontrole decide)")
d = depot_neuf()
ma._lance_git = lambda racine, action, chemin, vers, simulation: (True, "")
ap, res = lance(d, ["S1"])
ma._lance_git = vrai_lance
verifie(os.path.exists(d / "libre.txt"), True, "mutant sans git : rien n'est applique, le banc controle bien l'arbre")

if ECHECS:
    print(f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1)
print("VERT : menage_application")
