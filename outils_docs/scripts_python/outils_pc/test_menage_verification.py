"""Banc de menage_verification (contre-verification des propositions par git, avec mutants). Code de sortie 0 = vert.

Faux depot git temporaire, jamais le vrai. Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> test_menage_verification.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import menage_verification as mv

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


def prop(chemin, action="supprimer", risque="faible", **kw):
    return {"id": "M1", "categorie": "reste", "chemin": chemin, "action": action, "risque": risque, "en_cours": False,
            "vers": kw.get("vers"), "constat": "c", "preuve": "p", "casserait": "rien"}


racine = Path(tempfile.mkdtemp()) / "depot"
racine.mkdir()
git(racine, "init", "-q")
ecrit(racine, "docs/guide_ancien.md", "un guide\n")
ecrit(racine, "docs/lisez.md", "voir docs/guide_ancien.md pour le detail\n")                 # renvoi dans un document
ecrit(racine, "outils/calculDesDebits.py", "def f(): pass\n")
ecrit(racine, "config.ini", "script = outils/calculDesDebits.py\n")                           # renvoi dans une configuration
ecrit(racine, "lib/module.be", "import calculDesDebits\n")                                    # renvoi par le nom sans extension
ecrit(racine, "maquettes/a.html", "<html></html>\n")
ecrit(racine, "maquettes/b.html", "<html></html>\n")
ecrit(racine, "choix.md", "voir maquettes/a.html\n")
ecrit(racine, "modifie.txt", "avant\n")
ecrit(racine, "inutile.bak", "reste\n")
ecrit(racine, "-rf", "nom hostile\n")
ecrit(racine, "dossier avec espaces/f.txt", "x\n")
ecrit(racine, "cible/deja.txt", "x\n")
ecrit(racine, "ref/partitions/a.csv", "x\n")                                                       # dossier au nom commun
ecrit(racine, "lib/mot.py", "# les partitions de la flash\n")                                  # mot courant, pas un renvoi
ecrit(racine, "build.ini", "dossier = ref/partitions/a.csv\n")                                     # vrai renvoi, par le chemin
ecrit(racine, "cfg.ini", "a = -rf\nb = $(echo x)\nc = *.txt\n")                       # cite les noms hostiles
git(racine, "add", "-A")
git(racine, "commit", "-q", "-m", "init")
ecrit(racine, "modifie.txt", "apres\n")                                                       # modifie, non commite
ecrit(racine, "nouveau.txt", "pas suivi\n")                                                   # non suivi


def v(p, **kw):
    r = mv.enrichit([p], racine, **kw)[0]
    return r, r.get("verif", {})


# 1. fichier propre et sans renvoi
r, ve = v(prop("inutile.bak"))
verifie((ve["existe"], ve["suivi"], ve["modifie"], ve["n_docs"], ve["n_code"], r["risque"], r["en_cours"]),
        (True, True, False, 0, 0, "faible", False), "fichier propre sans renvoi : rien a signaler")

# 2. renvoi dans un document seulement : risque moyen, risque de l'agent garde
r, ve = v(prop("docs/guide_ancien.md"))
verifie((ve["n_docs"], ve["n_code"], r["risque"], r.get("risque_agent")), (1, 0, "moyen", "faible"), "renvoi dans un document : risque moyen")
verifie(ve["renvois_docs"], ["docs/lisez.md"], "le renvoi est nomme")

# 3. renvoi dans du code ou une configuration : risque eleve, par le chemin et par le nom sans extension
r, ve = v(prop("outils/calculDesDebits.py"))
verifie((ve["n_code"], r["risque"], sorted(ve["renvois_code"])), (2, "eleve", ["config.ini", "lib/module.be"]), "renvoi dans du code ou une config : risque eleve")
r, ve = v(prop("outils/calculDesDebits.py", action="garder"))
verifie((r["risque"], "risque_agent" in r), ("faible", False), "une proposition « garder » n'est pas relevee")

# 3b. un dossier au nom commun n'est pas cherche par son seul mot (faux positifs), mais bien par son chemin
r, ve = v(prop("ref/partitions", action="deplacer", vers="archives/partitions"))
verifie(("lib/mot.py" in ve["renvois_code"], "build.ini" in ve["renvois_code"]), (False, True), "dossier au nom commun : cite par son chemin, pas par le mot seul")

# 4. le fichier ne se compte pas lui-meme
verifie("outils/calculDesDebits.py" in ve.get("renvois_code", []), False, "pas d'auto-renvoi")

# 5. dossier cite par un fichier qu'il contient hors de lui
r, ve = v(prop("maquettes", action="deplacer", vers="archives/maquettes"))
verifie((ve["existe"], ve["suivi"], ve["renvois_docs"]), (True, True, ["choix.md"]), "dossier : cite par choix.md")

# 6. modifie ou non suivi : en cours force, meme si l'agent a dit non
r, ve = v(prop("modifie.txt"))
verifie((ve["modifie"], r["en_cours"]), (True, True), "fichier modifie : en cours force")
r, ve = v(prop("nouveau.txt"))
verifie((ve["suivi"], ve["modifie"], r["en_cours"]), (False, True, True), "fichier non suivi : en cours force")

# 7. perimee : le chemin n'existe plus
r, ve = v(prop("disparu.txt"))
verifie((ve["existe"], ve["perimee"]), (False, True), "chemin absent : proposition perimee")

# 8. destination deja existante
r, ve = v(prop("inutile.bak", action="deplacer", vers="cible/deja.txt"))
verifie(ve["destination_existe"], True, "destination deja existante signalee")
r, ve = v(prop("inutile.bak", action="deplacer", vers="cible/neuf.txt"))
verifie(ve["destination_existe"], False, "destination libre")

# 9. chemins hostiles : jamais pris pour une option ni un motif, aucun shell
for chemin in ("-rf", "dossier avec espaces/f.txt", "*.txt", "a;b", "$(echo x)", "`x`"):
    r, ve = v(prop(chemin))
    verifie("disponible" in ve and ve.get("erreur") is None, True, f"chemin hostile sans erreur git : {chemin!r}")
r, ve = v(prop("-rf"))
verifie((ve["existe"], ve["suivi"]), (True, True), "un fichier nomme -rf est trouve (pas pris pour une option)")
r, ve = v(prop("*.txt"))
verifie(ve["existe"], False, "un glob n'est pas developpe (:(literal))")
for chemin in ("-rf", "$(echo x)", "*.txt"):
    r, ve = v(prop(chemin))
    verifie((ve["disponible"], ve["renvois_code"]), (True, ["cfg.ini"]), f"chemin hostile cherche tel quel dans les renvois : {chemin!r}")

# 10. depot sans git : la contre-verification est indisponible, la proposition reste intacte
sans = Path(tempfile.mkdtemp())
ecrit(sans, "a.txt")
r = mv.enrichit([prop("a.txt", risque="moyen")], sans)[0]
verifie((r["verif"]["disponible"], r["risque"], r["en_cours"]), (False, "moyen", False), "depot sans git : indisponible, proposition inchangee")

# 11. plusieurs propositions, ordre et nombre conserves
res = mv.enrichit([prop("inutile.bak"), prop("modifie.txt"), prop("disparu.txt")], racine)
verifie([x["chemin"] for x in res], ["inutile.bak", "modifie.txt", "disparu.txt"], "ordre conserve")

# 11b. une erreur de git n'est JAMAIS « aucun renvoi » : indisponible, risque inchange
vrai_git = mv._git
mv._git = lambda racine, args, *a, **k: vrai_git(racine, args, *a, **k) if args[0] == "rev-parse" else (_ for _ in ()).throw(subprocess.SubprocessError("git grep : code 128"))
r, ve = v(prop("outils/calculDesDebits.py"))
mv._git = vrai_git
verifie((ve["disponible"], "128" in ve["erreur"], r["risque"]), (False, True, "faible"), "erreur git : indisponible, pas de faux « aucun renvoi »")
corrompu = Path(tempfile.mkdtemp()) / "d"       # index illisible : git rend une erreur, jamais une liste vide
corrompu.mkdir()
git(corrompu, "init", "-q")
ecrit(corrompu, "a.txt")
git(corrompu, "add", "-A")
git(corrompu, "commit", "-q", "-m", "x")
(corrompu / ".git" / "index").write_bytes(b"pas un index")
r = mv.enrichit([prop("a.txt")], corrompu)[0]
verifie(r["verif"]["disponible"], False, "index corrompu : indisponible, pas « fichier non suivi sans renvoi »")
r = mv.enrichit([prop("inutile.bak"), prop("docs/guide_ancien.md")], racine, delai_total=0)
verifie([x["verif"]["disponible"] for x in r], [False, False], "delai global depasse : indisponible")
trace = []
vrai_run = mv.subprocess.run
mv.subprocess.run = lambda cmd, *a, **k: (trace.append(cmd), vrai_run(cmd, *a, **k))[1]
v(prop("inutile.bak"))
mv.subprocess.run = vrai_run
verifie(all("--no-optional-locks" in c for c in trace) and len(trace) >= 3, True, "toutes les commandes git sont lancees avec --no-optional-locks")

# 12. mutants : le banc doit voir si on retire le classement, le forçage ou le « -e » des motifs
vrai_git = mv._git
mv._git = lambda racine, args, delai, codes=(0,): vrai_git(racine, [a for a in args if a != "-e"], delai, codes)
r, ve = v(prop("-rf"))
mv._git = vrai_git
verifie(ve["disponible"] and ve["renvois_code"] == ["cfg.ini"], False, "mutant sans « -e » : un nom en -rf est pris pour une option (le banc des hostiles etait discriminant)")
sauve = mv.est_document
mv.est_document = lambda chemin: True                  # mutant : tout est « document »
r, ve = v(prop("outils/calculDesDebits.py"))
mv.est_document = sauve
verifie(r["risque"] != "eleve", True, "mutant sans classement code/doc : le risque eleve disparait (le banc 3 etait discriminant)")
sauve = mv.force_en_cours
mv.force_en_cours = lambda r, ve: None                 # mutant : plus de forçage
r, ve = v(prop("modifie.txt"))
mv.force_en_cours = sauve
verifie(r["en_cours"], False, "mutant sans forçage « en cours » : le fichier modifie reste propose (le banc 6 etait discriminant)")

if ECHECS:
    print(f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1)
print("VERT : menage_verification")
